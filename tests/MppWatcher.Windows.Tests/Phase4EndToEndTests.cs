using System.Diagnostics;
using System.Drawing.Printing;
using System.Management;
using System.Runtime.InteropServices;
using MppWatcher.Core.Events;
using MppWatcher.Core.Storage;
using Xunit.Abstractions;

namespace MppWatcher.Windows.Tests;

/// <summary>
/// Phase 4 end to end with the real MPPWatcher.exe: files, documents in app titles, files opened
/// through Windows, print jobs, and files picked for upload in a browser.
/// </summary>
public sealed class Phase4EndToEndTests : IDisposable
{
    public const string TestPrinter = "MPP Test Printer"; // created by the CI workflow (Microsoft Print To PDF, file port)

    private readonly ITestOutputHelper _out;
    private readonly string _dir = Path.Combine(Path.GetTempPath(), "mppw-p4-" + Guid.NewGuid().ToString("N"));
    private readonly List<Process> _started = new();

    public Phase4EndToEndTests(ITestOutputHelper output)
    {
        _out = output;
        Directory.CreateDirectory(Work);
        Directory.CreateDirectory(Downloads);
        string J(string s) => System.Text.Json.JsonSerializer.Serialize(s);
        File.WriteAllText(ConfigPath, $$"""
            {
              "employee_id": "EMP-TEST",
              "log_folder": {{J(Path.Combine(_dir, "logs"))}},
              "collectors": {
                "files": { "watched_folders": [ {{J(Work)}}, {{J(Downloads)}} ], "downloads_folder": {{J(Downloads)}}, "quiet_ms": 1000 }
              }
            }
            """);
    }

    private string Work => Path.Combine(_dir, "Work");
    private string Downloads => Path.Combine(_dir, "Downloads");
    private string ConfigPath => Path.Combine(_dir, "config.json");
    private string DataDir => Path.Combine(_dir, "data");

    private Process Run(string exe, params string[] args)
    {
        var psi = new ProcessStartInfo(exe) { UseShellExecute = false };
        foreach (var a in args) psi.ArgumentList.Add(a);
        var p = Process.Start(psi)!;
        _started.Add(p);
        return p;
    }

    private void StartAgent()
    {
        Run(AppEndToEndTestsExe.Path, "--config", ConfigPath, "--data", DataDir);
        Assert.True(Desktop.WaitUntil(() => Events().Count(e => e.EventType == EventTypes.CollectorStatus) >= 7, TimeSpan.FromSeconds(25)),
            "watcher did not start all collectors: " + string.Join(", ", Events().Where(e => e.EventType == EventTypes.CollectorStatus).Select(e => e.Metadata.ToJsonString())));
        Assert.DoesNotContain(Events(), e => e.EventType == EventTypes.CollectorStatus && e.Metadata["status"]?.ToString() != "running");
    }

    private List<WatchEvent> Events()
    {
        var db = Path.Combine(DataDir, "events.db");
        if (!File.Exists(db)) return new();
        try
        {
            using var store = new SqliteEventStore(db, "", readOnly: true);
            return store.ReadAfter(0, 100_000).Select(r => r.Event).ToList();
        }
        catch (Microsoft.Data.Sqlite.SqliteException) { return new(); }
    }

    private WatchEvent WaitFor(string what, Func<WatchEvent, bool> match, int seconds = 20)
    {
        WatchEvent? found = null;
        Desktop.WaitUntil(() => (found = Events().FirstOrDefault(match)) is not null, TimeSpan.FromSeconds(seconds));
        Assert.True(found is not null, $"{what} not recorded");
        _out.WriteLine($"{what}: {EventJson.Serialize(found!)}");
        return found!;
    }

    private static string? M(WatchEvent e, string k) => e.Metadata[k]?.ToString();

    public void Dispose()
    {
        try { Run(AppEndToEndTestsExe.Path, "--stop").WaitForExit(20_000); } catch { }
        foreach (var p in _started) { try { if (!p.HasExited) p.Kill(); } catch { } }
        foreach (var name in new[] { "msedge", "notepad" })
            foreach (var p in Process.GetProcessesByName(name)) { try { p.Kill(); } catch { } }
        foreach (var e in Events().Where(e => e.EventType is not (EventTypes.ProcessInventory or EventTypes.CollectorStatus)))
            _out.WriteLine($"  {e.EventType} [{e.ProcessName}] \"{e.WindowTitle}\" {e.Metadata.ToJsonString()}");
        foreach (var f in Directory.Exists(Path.Combine(_dir, "logs")) ? Directory.GetFiles(Path.Combine(_dir, "logs")) : Array.Empty<string>())
            _out.WriteLine(File.ReadAllText(f));
        try { Directory.Delete(_dir, true); } catch { }
    }

    [Fact]
    public void Files_documents_and_opened_files_are_recorded()
    {
        StartAgent();

        // Created, saved, renamed — one event each.
        var psd = Path.Combine(Work, "MA023-main.psd");
        File.WriteAllText(psd, "v1");
        WaitFor("file_created", e => e.EventType == EventTypes.FileCreated && M(e, "file_name") == "MA023-main.psd");
        Thread.Sleep(1500);
        for (var i = 0; i < 4; i++) { File.AppendAllText(psd, "more"); Thread.Sleep(30); }
        var saved = WaitFor("file_saved", e => e.EventType == EventTypes.FileSaved && M(e, "file_name") == "MA023-main.psd");
        Assert.Contains("MA023", M(saved, "sku_candidates"));
        File.Move(psd, Path.Combine(Work, "MA023-final.psd"));
        WaitFor("file_renamed", e => e.EventType == EventTypes.FileRenamed && M(e, "file_name") == "MA023-final.psd" && M(e, "old_file_name") == "MA023-main.psd");

        // Document from the app's title bar.
        var notes = Path.Combine(Work, "PS142-notes.txt");
        File.WriteAllText(notes, "customization notes");
        using var notepad = Process.Start(new ProcessStartInfo("notepad.exe", $"\"{notes}\"") { UseShellExecute = false })!;
        Desktop.WaitUntil(() => { notepad.Refresh(); return notepad.MainWindowHandle != IntPtr.Zero; }, TimeSpan.FromSeconds(15));
        Desktop.BringToFront(notepad.MainWindowHandle);
        var session = WaitFor("notepad session with document", e => e.EventType == EventTypes.AppSessionStart
            && e.Metadata["document"]?["name"]?.ToString() == "PS142-notes.txt");
        Assert.Contains("PS142", session.Metadata["document"]!.ToJsonString());

        // "File opened" through Windows' Recent Items (what Office/Adobe/Explorer do on open).
        var sheet = Path.Combine(Work, "ShopifyInventory.xlsx");
        File.WriteAllText(sheet, "not really excel");
        SHAddToRecentDocs(3 /* SHARD_PATHW */, sheet);
        var opened = WaitFor("file_opened", e => e.EventType == EventTypes.FileOpened && M(e, "file_name") == "ShopifyInventory.xlsx");
        Assert.Equal("xlsx", M(opened, "extension"));
    }

    [Fact]
    public void Print_jobs_are_recorded_with_printer_and_document()
    {
        Assert.True(PrinterSettings.InstalledPrinters.Cast<string>().Contains(TestPrinter), $"test printer '{TestPrinter}' is not installed (CI creates it)");
        StartAgent();
        SetPrinterPaused(true); // keep the job in the queue long enough for WMI to see it for sure
        try
        {
            using var doc = new PrintDocument { DocumentName = "MA023-shipping-label", PrinterSettings = { PrinterName = TestPrinter } };
            doc.PrintPage += (_, e) => { e.Graphics!.DrawString("MA023", new Font("Arial", 24), Brushes.Black, 50, 50); e.HasMorePages = false; };
            doc.Print();
            var job = WaitFor("print_job", e => e.EventType == EventTypes.PrintJob && M(e, "document_name") == "MA023-shipping-label");
            Assert.Equal(TestPrinter, M(job, "printer"));
            Assert.Contains("MA023", M(job, "sku_candidates"));
        }
        finally
        {
            SetPrinterPaused(false);
        }
        WaitFor("print_job_finished", e => e.EventType == EventTypes.PrintJobFinished && M(e, "document_name") == "MA023-shipping-label", 60);
    }

    [Fact]
    public void File_picked_for_upload_in_the_browser_is_linked_to_the_page()
    {
        using var server = new FakeWebServer(BrowserEndToEndTests.Page);
        var photo = Path.Combine(Work, "PS142-main.png");
        File.WriteAllBytes(photo, new byte[] { 0x89, 0x50, 0x4E, 0x47 });
        StartAgent();

        var edge = new[]
        {
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86), @"Microsoft\Edge\Application\msedge.exe"),
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), @"Microsoft\Edge\Application\msedge.exe"),
        }.First(File.Exists);
        Run(edge, $"--user-data-dir={Path.Combine(_dir, "edge")}", "--no-first-run", "--no-default-browser-check", "--disable-sync",
            "--ignore-certificate-errors", "--disable-quic", $"--host-resolver-rules=MAP * 127.0.0.1:{server.Port}, EXCLUDE localhost",
            "--start-maximized", "https://www.etsy.com/your/shops/me/listing-editor/edit/1234567890");
        WaitFor("etsy page", e => e.EventType == EventTypes.BrowserPage && e.Domain == "etsy.com", 40);

        // Click the page's file input: the standard Windows "Open" dialog appears.
        var uia = new MppWatcher.Windows.Ui.UiaClient();
        global::Interop.UIAutomationClient.IUIAutomationElement? input = null;
        Desktop.WaitUntil(() =>
        {
            var root = uia.Automation.ElementFromHandle(MppWatcher.Windows.Interop.NativeMethods.GetForegroundWindow());
            // Edge exposes the HTML id as the automation id (seen in earlier runs: id 'save' -> automation_id 'save').
            input = root?.FindFirst(global::Interop.UIAutomationClient.TreeScope.TreeScope_Descendants, uia.Automation.CreatePropertyCondition(30011, "photos"))
                ?? root?.FindFirst(global::Interop.UIAutomationClient.TreeScope.TreeScope_Descendants, uia.Automation.CreatePropertyCondition(30005, "Add photos"));
            return input is not null;
        }, TimeSpan.FromSeconds(20));
        if (input is null)
        {
            // Report what Edge does expose so the next attempt is based on facts.
            var root = uia.Automation.ElementFromHandle(MppWatcher.Windows.Interop.NativeMethods.GetForegroundWindow());
            var all = root?.FindAll(global::Interop.UIAutomationClient.TreeScope.TreeScope_Descendants, uia.Automation.CreateTrueCondition());
            for (var i = 0; all is not null && i < Math.Min(all.Length, 200); i++)
            {
                var el = all.GetElement(i);
                _out.WriteLine($"exposed: {MppWatcher.Windows.Ui.UiaClient.ControlTypeName(el.CurrentControlType)} name='{el.CurrentName}' id='{el.CurrentAutomationId}'");
            }
        }
        Assert.True(input is not null, "file input not exposed");
        _out.WriteLine($"file input seen as {MppWatcher.Windows.Ui.UiaClient.ControlTypeName(input!.CurrentControlType)} name='{input.CurrentName}'");
        var r = input!.CurrentBoundingRectangle;
        Desktop.Click(new Point((r.left + r.right) / 2, (r.top + r.bottom) / 2));
        Assert.True(Desktop.WaitUntil(() => MppWatcher.Windows.Interop.NativeMethods.GetWindowClass(MppWatcher.Windows.Interop.NativeMethods.GetForegroundWindow()) == "#32770",
            TimeSpan.FromSeconds(15)), "Open dialog did not appear");
        Thread.Sleep(1500); // dialog puts the cursor in its file name box
        Desktop.TypeText(photo);
        Thread.Sleep(700);
        Desktop.PressEnter();
        UiAutomationTests.SaveScreenshot("upload-after-dialog.png");

        var upload = WaitFor("upload_file_selected", e => e.EventType == EventTypes.UploadFileSelected);
        Assert.Contains("PS142-main.png", M(upload, "files"));
        Thread.Sleep(1000);
        Assert.Single(Events(), e => e.EventType == EventTypes.UploadFileSelected); // logged once, with the final name
        Assert.Equal("etsy.com", upload.Domain);
        Assert.Contains("1234567890", upload.Metadata["page"]?.ToJsonString());
        Assert.Contains("PS142", M(upload, "sku_candidates"));
    }

    private static void SetPrinterPaused(bool paused)
    {
        using var searcher = new ManagementObjectSearcher($"SELECT * FROM Win32_Printer WHERE Name = '{TestPrinter}'");
        foreach (ManagementObject p in searcher.Get()) p.InvokeMethod(paused ? "Pause" : "Resume", null);
    }

    [DllImport("shell32.dll", CharSet = CharSet.Unicode)] private static extern void SHAddToRecentDocs(uint flags, string path);
}
