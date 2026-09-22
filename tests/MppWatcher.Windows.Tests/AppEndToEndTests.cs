using System.Diagnostics;
using System.Drawing.Imaging;
using MppWatcher.Core.Events;
using MppWatcher.Core.Storage;
using Xunit.Abstractions;

namespace MppWatcher.Windows.Tests;

/// <summary>
/// Runs the real MPPWatcher.exe (the published single file in CI, via MPPWATCHER_EXE)
/// the way Windows would start it, and checks the database it writes.
/// </summary>
public sealed class AppEndToEndTests : IDisposable
{
    private readonly ITestOutputHelper _out;
    private readonly string _dir = Path.Combine(Path.GetTempPath(), "mppw-e2e-" + Guid.NewGuid().ToString("N"));
    private readonly List<Process> _started = new();

    public AppEndToEndTests(ITestOutputHelper output)
    {
        _out = output;
        Directory.CreateDirectory(_dir);
        File.WriteAllText(ConfigPath, $$"""
            {
              "employee_id": "EMP-TEST",
              "idle_timeout_seconds": 300,
              "log_folder": {{Json(Path.Combine(_dir, "logs"))}},
              "export": { "destination_folder": {{Json(Path.Combine(_dir, "export"))}} },
              "collectors": { "activity": { "checkpoint_seconds": 5 } }
            }
            """);
    }

    private string ConfigPath => Path.Combine(_dir, "config.json");
    private string DataDir => Path.Combine(_dir, "data");
    private string DbPath => Path.Combine(DataDir, "events.db");

    private static string Json(string s) => System.Text.Json.JsonSerializer.Serialize(s);

    private static string ExePath
    {
        get
        {
            var fromEnv = Environment.GetEnvironmentVariable("MPPWATCHER_EXE");
            if (!string.IsNullOrEmpty(fromEnv)) return Path.GetFullPath(fromEnv);
            var dir = new DirectoryInfo(AppContext.BaseDirectory);
            while (dir is not null && !Directory.Exists(Path.Combine(dir.FullName, "src", "MppWatcher.App"))) dir = dir.Parent;
            var found = dir is null ? null : Directory.EnumerateFiles(Path.Combine(dir.FullName, "src", "MppWatcher.App", "bin"), "MPPWatcher.exe", SearchOption.AllDirectories)
                .OrderByDescending(File.GetLastWriteTimeUtc).FirstOrDefault();
            return found ?? throw new FileNotFoundException("Build MppWatcher.App first or set MPPWATCHER_EXE");
        }
    }

    private Process Run(params string[] args)
    {
        var psi = new ProcessStartInfo(ExePath) { UseShellExecute = false };
        foreach (var a in args) psi.ArgumentList.Add(a);
        var p = Process.Start(psi)!;
        _started.Add(p);
        return p;
    }

    private Process StartAgent() => Run("--config", ConfigPath, "--data", DataDir);

    private int StopAgent()
    {
        var stop = Run("--stop");
        Assert.True(stop.WaitForExit(30_000), "--stop did not return");
        return stop.ExitCode;
    }

    private List<WatchEvent> ReadEvents()
    {
        if (!File.Exists(DbPath)) return new();
        try
        {
            using var store = new SqliteEventStore(DbPath, "", readOnly: true);
            return store.ReadAfter(0, 100_000).Select(r => r.Event).ToList();
        }
        catch (Microsoft.Data.Sqlite.SqliteException)
        {
            return new(); // database being created at this moment
        }
    }

    private bool WaitForEvents(Func<List<WatchEvent>, bool> condition, int seconds) =>
        Desktop.WaitUntil(() => condition(ReadEvents()), TimeSpan.FromSeconds(seconds));

    private static string? Str(WatchEvent e, string key) => e.Metadata[key]?.GetValue<string>();

    public void Dispose()
    {
        foreach (var p in _started)
        {
            try { if (!p.HasExited) p.Kill(); } catch { }
            p.Dispose();
        }
        var events = ReadEvents();
        _out.WriteLine($"{events.Count} events in {DbPath}:");
        foreach (var e in events) _out.WriteLine($"  {e.TimestampLocal} {e.EventType} [{e.ProcessName}] \"{e.WindowTitle}\" {e.Metadata.ToJsonString()}");
        var logDir = Path.Combine(_dir, "logs");
        if (Directory.Exists(logDir))
            foreach (var f in Directory.GetFiles(logDir)) _out.WriteLine(File.ReadAllText(f));
        try { Directory.Delete(_dir, true); } catch { }
    }

    [Fact]
    public void Agent_starts_records_shows_viewer_and_stops_cleanly()
    {
        var agent = StartAgent();
        Assert.True(WaitForEvents(ev => ev.Count(e => e.EventType == EventTypes.CollectorStatus && Str(e, "status") == "running") >= 2, 20),
            "agent did not start both collectors");

        // A second copy in the same session must exit at once.
        var second = StartAgent();
        Assert.True(second.WaitForExit(10_000), "second copy did not exit");
        Assert.Equal(0, second.ExitCode);
        Assert.False(agent.HasExited, "first copy stopped");

        // Use the PC a little.
        using var w1 = new TestWindow("Keepa - MPP End To End");
        using var w2 = new TestWindow("MA023-main.psd - MPP End To End");
        Assert.True(Desktop.BringToFront(w1.Handle));
        Thread.Sleep(2500);
        Assert.True(Desktop.BringToFront(w2.Handle));
        Thread.Sleep(2500);
        Assert.True(WaitForEvents(ev => ev.Any(e => e.EventType == EventTypes.AppSessionStart && e.WindowTitle == "MA023-main.psd - MPP End To End"), 10),
            "agent did not record the window switch");

        // Live viewer shows the events; keep a screenshot for people to look at.
        var viewer = Run("--viewer", "--config", ConfigPath, "--data", DataDir);
        Assert.True(Desktop.WaitUntil(() => { viewer.Refresh(); return viewer.MainWindowTitle.Contains("Live Event Viewer"); }, TimeSpan.FromSeconds(20)),
            "viewer window did not open");
        Desktop.BringToFront(viewer.MainWindowHandle);
        Thread.Sleep(2500);
        SaveScreenshot("live-viewer.png");
        viewer.CloseMainWindow();
        Assert.True(viewer.WaitForExit(10_000), "viewer did not close");

        Assert.Equal(0, StopAgent());
        Assert.True(agent.WaitForExit(15_000), "agent did not exit after --stop");
        Assert.Equal(0, agent.ExitCode);

        var events = ReadEvents();
        Assert.Equal(EventTypes.WatcherStarted, events.First().EventType);
        Assert.Equal(EventTypes.WatcherStopped, events.Last().EventType);
        Assert.Equal("stop_requested", Str(events.Last(), "reason"));
        Assert.All(events, e => Assert.Equal("EMP-TEST", e.EmployeeId));
        Assert.Equal(events.Count(e => e.EventType == EventTypes.AppSessionStart), events.Count(e => e.EventType == EventTypes.AppSessionEnd));
        var keepaEnd = events.First(e => e.EventType == EventTypes.AppSessionEnd && e.WindowTitle == "Keepa - MPP End To End");
        Assert.Equal("MA023-main.psd - MPP End To End", Str(keepaEnd, "next_window_title"));
        Assert.Contains(events, e => e.EventType == EventTypes.ProcessInventory);
        Assert.False(File.Exists(Path.Combine(DataDir, "open-session.json")), "checkpoint left after clean stop");
    }

    [Fact]
    public void Killed_agent_session_is_recovered_on_next_start()
    {
        var agent = StartAgent();
        using var w = new TestWindow("MPP Crash Test Window");
        Assert.True(WaitForEvents(ev => ev.Any(e => e.EventType == EventTypes.CollectorStatus), 20), "agent did not start");
        Assert.True(Desktop.BringToFront(w.Handle));
        Assert.True(WaitForEvents(ev => ev.Any(e => e.EventType == EventTypes.AppSessionStart && e.WindowTitle == "MPP Crash Test Window"), 10));
        var checkpoint = Path.Combine(DataDir, "open-session.json");
        Assert.True(Desktop.WaitUntil(() => File.Exists(checkpoint), TimeSpan.FromSeconds(12)), "no checkpoint written");

        agent.Kill(); // like a crash or Task Manager "End task"
        Assert.True(agent.WaitForExit(10_000));

        var again = StartAgent();
        Assert.True(WaitForEvents(ev => ev.Any(e => e.EventType == EventTypes.AppSessionEnd && Str(e, "end_reason") == SessionEndReasons.CrashRecovered), 20),
            "crashed session was not recovered");
        Assert.Equal(0, StopAgent());
        Assert.True(again.WaitForExit(15_000));

        var recovered = ReadEvents().First(e => Str(e, "end_reason") == SessionEndReasons.CrashRecovered);
        Assert.Equal("MPP Crash Test Window", recovered.WindowTitle);
        Assert.Equal(2, ReadEvents().Count(e => e.EventType == EventTypes.WatcherStarted));
    }

    [Fact]
    public void Inspector_shows_what_windows_exposes_and_hides_passwords()
    {
        using var w = new TestWindow("MPP Inspector Target", f =>
        {
            // Keep clear of the inspector, which stays on top at the right of the screen.
            f.StartPosition = FormStartPosition.Manual;
            f.Left = 0;
            f.Top = 60;
            f.Width = 300;
            f.Controls.Add(new TextBox { Name = "skuBox", AccessibleName = "SKU", Text = "MA023", Left = 20, Top = 20, Width = 200 });
            f.Controls.Add(new TextBox { Name = "pwBox", AccessibleName = "Password", Text = "hunter2", UseSystemPasswordChar = true, Left = 20, Top = 70, Width = 200 });
        });
        Desktop.BringToFront(w.Handle);
        var inspector = Run("--inspect", "--config", ConfigPath);
        Assert.True(Desktop.WaitUntil(() => { inspector.Refresh(); return inspector.MainWindowTitle.Contains("Diagnostic Inspector"); }, TimeSpan.FromSeconds(20)),
            "inspector did not open");

        var uia = new MppWatcher.Windows.Ui.UiaClient();
        string ReportText()
        {
            var root = uia.Automation.ElementFromHandle(inspector.MainWindowHandle);
            var edit = root?.FindFirst(global::Interop.UIAutomationClient.TreeScope.TreeScope_Descendants,
                uia.Automation.CreatePropertyCondition(30003 /* ControlType */, 50004 /* Edit */));
            return edit is null ? "" : uia.ReadValue(edit, out _) ?? "";
        }

        Desktop.MoveMouse(w.CenterOf("skuBox"));
        Assert.True(Desktop.WaitUntil(() => ReportText().Contains("MA023"), TimeSpan.FromSeconds(10)), "inspector did not show the SKU field. Shown: " + ReportText());
        var skuReport = ReportText();
        _out.WriteLine(skuReport);
        Assert.Contains("Edit", skuReport);
        Assert.Contains("YES — value \"MA023\"", skuReport);
        UiAutomationTests.SaveScreenshot("inspector-sku.png");

        Desktop.MoveMouse(w.CenterOf("pwBox"));
        Assert.True(Desktop.WaitUntil(() => ReportText().Contains("Password"), TimeSpan.FromSeconds(10)), "inspector did not show the password field");
        var pwReport = ReportText();
        _out.WriteLine(pwReport);
        Assert.DoesNotContain("hunter2", pwReport);
        Assert.Contains("Sensitive?", pwReport);
        Assert.Contains("YES", pwReport);

        inspector.CloseMainWindow();
        Assert.True(inspector.WaitForExit(10_000), "inspector did not close");
    }

    [Fact]
    public void Stop_command_when_nothing_runs_is_harmless()
    {
        Assert.Equal(0, StopAgent());
    }

    private void SaveScreenshot(string name)
    {
        try
        {
            var folder = Environment.GetEnvironmentVariable("MPPWATCHER_SCREENSHOTS") ?? Path.Combine(AppContext.BaseDirectory, "screenshots");
            Directory.CreateDirectory(folder);
            var bounds = Screen.PrimaryScreen!.Bounds;
            using var bmp = new Bitmap(bounds.Width, bounds.Height);
            using (var g = Graphics.FromImage(bmp)) g.CopyFromScreen(bounds.Location, Point.Empty, bounds.Size);
            var path = Path.Combine(folder, name);
            bmp.Save(path, ImageFormat.Png);
            _out.WriteLine("Screenshot: " + path);
        }
        catch (Exception e)
        {
            _out.WriteLine("Screenshot failed: " + e.Message);
        }
    }
}
