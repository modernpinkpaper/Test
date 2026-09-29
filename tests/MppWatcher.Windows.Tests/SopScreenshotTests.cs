using MppWatcher.Core.Capture;
using MppWatcher.Core.Collectors;
using MppWatcher.Core.Configuration;
using MppWatcher.Core.Diagnostics;
using MppWatcher.Core.Events;
using MppWatcher.Core.Pipeline;
using MppWatcher.Windows.Ui;
using Xunit.Abstractions;

namespace MppWatcher.Windows.Tests;

/// <summary>Real Windows: an SOP recording should snap a screenshot of the active window on each click.</summary>
public sealed class SopScreenshotTests : IDisposable
{
    private readonly ITestOutputHelper _out;
    private readonly string _dir = Path.Combine(Path.GetTempPath(), "mppw-sop-" + Guid.NewGuid().ToString("N"));
    private readonly ListSink _sink = new();
    private readonly MemoryDiagnosticLog _log = new();
    private UiAutomationCollector? _collector;

    public SopScreenshotTests(ITestOutputHelper output) { _out = output; Directory.CreateDirectory(_dir); }

    public void Dispose()
    {
        try { _collector?.Stop("test"); } catch { }
        _out.WriteLine(_sink.Dump());
        foreach (var l in _log.Lines) _out.WriteLine("log: " + l);
        try { Directory.Delete(_dir, true); } catch { }
    }

    [Fact]
    public void Screenshots_are_taken_on_clicks_only_while_recording_an_sop()
    {
        var cfg = new WatcherConfig();
        cfg.Export.DestinationFolder = Path.Combine(_dir, "export"); // plain folder, no Google Drive token
        cfg.Capture.ScreenshotMinGapMs = 0; // no throttle in the test
        var capture = new CaptureController();
        var identity = new WatcherIdentity("SOPPC", "SOPPC\\user", "run1");
        var sop = new SopScreenshotter(() => cfg, identity, Path.Combine(_dir, "data"), capture, _log);
        _collector = new UiAutomationCollector(ignoreOwnProcess: false, activity: null, sop: sop);
        _collector.Start(new CollectorContext(_sink, new ConfigProvider(cfg), _log, SystemClock.Instance));

        using var w = new TestWindow("MPP SOP Test", f =>
        {
            f.Width = 300; f.Height = 200;
            f.Controls.Add(new System.Windows.Forms.Button { Name = "goButton", Text = "Go", Left = 90, Top = 60, Width = 120, Height = 36 });
        });
        Assert.True(Desktop.BringToFront(w.Handle));
        Thread.Sleep(500);

        // Not recording yet: a click should NOT produce a screenshot.
        Desktop.Click(w.CenterOf("goButton"));
        Thread.Sleep(800);
        Assert.Empty(_sink.OfType(EventTypes.SopScreenshot));

        // Start SOP recording: clicks should now snap the active window.
        capture.Start(CaptureMode.Sop, "Test SOP");
        Assert.True(Desktop.WaitUntil(() =>
        {
            Desktop.Click(w.CenterOf("goButton"));
            Thread.Sleep(400);
            return _sink.OfType(EventTypes.SopScreenshot).Count > 0;
        }, TimeSpan.FromSeconds(15)), "no sop_screenshot event while recording");

        var shot = _sink.OfType(EventTypes.SopScreenshot)[0];
        var file = shot.Metadata["screenshot_file"]!.GetValue<string>();
        _out.WriteLine("screenshot: " + file);
        Assert.True(File.Exists(file), "screenshot file was not written: " + file);
        Assert.True(new FileInfo(file).Length > 1000, "screenshot looks empty");
        Assert.EndsWith(".jpg", file);

        // Pause: no new screenshots.
        capture.Pause();
        var before = _sink.OfType(EventTypes.SopScreenshot).Count;
        Desktop.Click(w.CenterOf("goButton"));
        Thread.Sleep(800);
        Assert.Equal(before, _sink.OfType(EventTypes.SopScreenshot).Count);
    }
}
