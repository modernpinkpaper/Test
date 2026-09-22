using System.Diagnostics;
using Interop.UIAutomationClient;
using MppWatcher.Core.Collectors;
using MppWatcher.Core.Configuration;
using MppWatcher.Core.Diagnostics;
using MppWatcher.Core.Events;
using MppWatcher.Windows.Ui;
using Xunit.Abstractions;

namespace MppWatcher.Windows.Tests;

/// <summary>Phase 2: the UI Automation collector against real controls, typed into like an employee would.</summary>
public sealed class UiAutomationTests : IDisposable
{
    private readonly ITestOutputHelper _out;
    private readonly ListSink _sink = new();
    private readonly MemoryDiagnosticLog _log = new();
    private UiAutomationCollector? _collector;

    public UiAutomationTests(ITestOutputHelper output) => _out = output;

    private void StartCollector()
    {
        var cfg = new WatcherConfig();
        cfg.Collectors.UiAutomation.ValueSettleSeconds = 3;
        cfg.Collectors.UiAutomation.FocusedFieldPollMs = 250;
        _collector = new UiAutomationCollector(ignoreOwnProcess: false); // sample windows live in this test process
        _collector.Start(new CollectorContext(_sink, new ConfigProvider(cfg), _log, SystemClock.Instance));
        Thread.Sleep(500);
    }

    private void StopCollector()
    {
        _collector?.Stop("test");
        _collector = null;
    }

    public void Dispose()
    {
        StopCollector();
        _out.WriteLine("Captured events:" + Environment.NewLine + _sink.Dump());
        foreach (var l in _log.Lines) _out.WriteLine("log: " + l);
    }

    private static TestWindow Form() => new("MPP UI Test Form", f =>
    {
        f.Width = 520;
        f.Height = 420;
        var y = 15;
        TextBox Box(string name, string accessible, bool password = false)
        {
            f.Controls.Add(new Label { Text = accessible, Left = 15, Top = y, AutoSize = true });
            var t = new TextBox { Name = name, AccessibleName = accessible, Left = 150, Top = y, Width = 300, UseSystemPasswordChar = password };
            f.Controls.Add(t);
            y += 40;
            return t;
        }
        Box("searchBox", "Search");
        Box("skuBox", "SKU");
        Box("passwordBox", "Password", password: true);
        Box("cardBox", "Card number");
        f.Controls.Add(new CheckBox { Name = "giftWrap", Text = "Gift wrap", Left = 150, Top = y, AutoSize = true });
        y += 40;
        f.Controls.Add(new Button { Name = "saveButton", Text = "Save", Left = 150, Top = y, Width = 120, Height = 32 });
    });

    private List<WatchEvent> Fields => _sink.OfType(EventTypes.UiFieldValue);
    private List<WatchEvent> Actions => _sink.OfType(EventTypes.UiAction);
    private static string? M(WatchEvent e, string k) => e.Metadata[k]?.ToString();

    [Fact]
    public void Field_values_buttons_and_checkboxes_are_captured_and_secrets_are_not()
    {
        using var w = Form();
        StartCollector();
        Assert.True(Desktop.BringToFront(w.Handle));

        Desktop.Click(w.CenterOf("searchBox"));
        Desktop.TypeText("personalized stationery");
        Desktop.Click(w.CenterOf("skuBox"));           // leaving the field commits its value
        Desktop.TypeText("MA023");
        Desktop.Click(w.CenterOf("passwordBox"));
        Desktop.TypeText("hunter2");
        Desktop.Click(w.CenterOf("cardBox"));
        Desktop.TypeText("4111 1111 1111 1111");
        Desktop.Click(w.CenterOf("giftWrap"));
        Desktop.Click(w.CenterOf("saveButton"));

        Assert.True(Desktop.WaitUntil(() => Actions.Any(a => M(a, "control_name") == "Save"), TimeSpan.FromSeconds(10)), "Save click not captured");
        Assert.True(Desktop.WaitUntil(() => Fields.Any(f => M(f, "value") == "MA023"), TimeSpan.FromSeconds(10)), "SKU value not captured");
        StopCollector();

        var search = Fields.Single(f => M(f, "value") == "personalized stationery");
        Assert.Equal("Search", M(search, "label"));
        Assert.Equal("Edit", M(search, "control_type"));
        Assert.Equal("focus_left", M(search, "trigger"));
        Assert.Equal("MPP UI Test Form", search.WindowTitle);
        Assert.Equal("searchBox", M(search, "automation_id"));

        var save = Actions.Single(a => M(a, "control_name") == "Save");
        Assert.Equal("button_clicked", M(save, "action"));
        Assert.Equal("true", M(save, "is_key_action"));

        var gift = Actions.Single(a => M(a, "control_name") == "Gift wrap");
        Assert.Equal("checkbox_toggled", M(gift, "action"));
        Assert.Equal("On", M(gift, "state_after"));

        var everything = string.Join("\n", _sink.All.Select(EventJson.Serialize));
        Assert.DoesNotContain("hunter2", everything);
        Assert.DoesNotContain("4111", everything);
        Assert.DoesNotContain(Fields, f => M(f, "label") is "Password" or "Card number");
        Assert.DoesNotContain("\"x\":", everything);   // no coordinates anywhere
    }

    [Fact]
    public void Value_is_captured_when_typing_stops_even_if_focus_stays()
    {
        using var w = Form();
        StartCollector();
        Assert.True(Desktop.BringToFront(w.Handle));
        Desktop.Click(w.CenterOf("searchBox"));
        Desktop.TypeText("notebooks");
        Assert.True(Desktop.WaitUntil(() => Fields.Any(f => M(f, "value") == "notebooks"), TimeSpan.FromSeconds(8)), "settled value not captured");
        Assert.Equal("value_settled", M(Fields.Single(), "trigger"));
        StopCollector();
    }

    [Fact]
    public void Browser_page_fields_and_buttons_are_captured_in_Edge()
    {
        var edge = new[]
        {
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86), @"Microsoft\Edge\Application\msedge.exe"),
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), @"Microsoft\Edge\Application\msedge.exe"),
        }.FirstOrDefault(File.Exists);
        Assert.True(edge is not null, "Microsoft Edge is not installed on this machine");

        var page = new Uri(Path.Combine(AppContext.BaseDirectory, "fixtures", "listing-editor.html")).AbsoluteUri;
        var profile = Path.Combine(Path.GetTempPath(), "mppw-edge-" + Guid.NewGuid().ToString("N"));
        var psi = new ProcessStartInfo(edge!) { UseShellExecute = false };
        foreach (var a in new[] { $"--user-data-dir={profile}", "--no-first-run", "--no-default-browser-check", "--disable-sync", "--new-window", "--start-maximized", page })
            psi.ArgumentList.Add(a);
        using var browser = Process.Start(psi)!;
        try
        {
            var uia = new UiaClient();
            IUIAutomationElement? Find(string name)
            {
                IUIAutomationElement? found = null;
                Desktop.WaitUntil(() =>
                {
                    var hwnd = Process.GetProcessesByName("msedge").Select(p => p.MainWindowHandle)
                        .FirstOrDefault(h => h != IntPtr.Zero && MppWatcher.Windows.Interop.NativeMethods.GetWindowTitle(h).Contains("MPP Browser Test"));
                    if (hwnd == IntPtr.Zero) return false;
                    var root = uia.Automation.ElementFromHandle(hwnd);
                    found = root.FindFirst(TreeScope.TreeScope_Descendants, uia.Automation.CreatePropertyCondition(30005 /* Name */, name));
                    return found is not null;
                }, TimeSpan.FromSeconds(30));
                return found;
            }
            Point CenterOf(IUIAutomationElement el)
            {
                var r = el.CurrentBoundingRectangle;
                return new Point((r.left + r.right) / 2, (r.top + r.bottom) / 2);
            }

            var search = Find("Search products");
            Assert.True(search is not null, "Edge did not expose the 'Search products' field through UI Automation");
            StartCollector();

            Desktop.Click(CenterOf(search!));
            Desktop.TypeText("personalized stationery");
            Desktop.Click(CenterOf(Find("SKU")!));
            Desktop.TypeText("PS142");
            Desktop.Click(CenterOf(Find("Password")!));
            Desktop.TypeText("hunter2");
            Desktop.Click(CenterOf(Find("Save listing")!));

            Assert.True(Desktop.WaitUntil(() => Actions.Any(a => M(a, "control_name") == "Save listing"), TimeSpan.FromSeconds(10)), "Save listing click not captured in Edge");
            Assert.True(Desktop.WaitUntil(() => Fields.Any(f => M(f, "value") == "PS142"), TimeSpan.FromSeconds(10)), "SKU value not captured in Edge");
            SaveScreenshot("edge-listing-editor.png");
            StopCollector();

            var q = Fields.Single(f => M(f, "value") == "personalized stationery");
            _out.WriteLine("Edge search field as seen: " + q.Metadata.ToJsonString());
            Assert.Equal("Search products", M(q, "label"));
            Assert.Contains("MPP Browser Test", q.WindowTitle);
            Assert.DoesNotContain("hunter2", string.Join("\n", _sink.All.Select(EventJson.Serialize)));
        }
        finally
        {
            foreach (var p in Process.GetProcessesByName("msedge")) { try { p.Kill(); } catch { } }
            try { Directory.Delete(profile, true); } catch { }
        }
    }

    internal static void SaveScreenshot(string name)
    {
        try
        {
            var folder = Environment.GetEnvironmentVariable("MPPWATCHER_SCREENSHOTS") ?? Path.Combine(AppContext.BaseDirectory, "screenshots");
            Directory.CreateDirectory(folder);
            var b = Screen.PrimaryScreen!.Bounds;
            using var bmp = new Bitmap(b.Width, b.Height);
            using (var g = Graphics.FromImage(bmp)) g.CopyFromScreen(b.Location, Point.Empty, b.Size);
            bmp.Save(Path.Combine(folder, name), System.Drawing.Imaging.ImageFormat.Png);
        }
        catch { /* screenshots are only a convenience for people reviewing the test run */ }
    }
}
