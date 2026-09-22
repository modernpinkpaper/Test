using System.Diagnostics;
using MppWatcher.Core.Activity;
using MppWatcher.Core.Collectors;
using MppWatcher.Core.Configuration;
using MppWatcher.Core.Diagnostics;
using MppWatcher.Core.Events;
using Xunit.Abstractions;

namespace MppWatcher.Windows.Tests;

/// <summary>Runs the real activity collector against real windows on the Windows desktop.</summary>
public sealed class ActivityCollectorTests : IDisposable
{
    private readonly ITestOutputHelper _out;
    private readonly string _dir = Path.Combine(Path.GetTempPath(), "mppw-wt-" + Guid.NewGuid().ToString("N"));
    private readonly ListSink _sink = new();
    private readonly MemoryDiagnosticLog _log = new();
    private WindowsActivityCollector? _collector;

    public ActivityCollectorTests(ITestOutputHelper output)
    {
        _out = output;
        Directory.CreateDirectory(_dir);
    }

    private string CheckpointPath => Path.Combine(_dir, "open-session.json");

    private void StartCollector(int idleSeconds = 300)
    {
        var cfg = new WatcherConfig { IdleTimeoutSeconds = idleSeconds };
        cfg.Collectors.Activity.PollIntervalMs = 200;
        cfg.Collectors.Activity.ForegroundStableMs = 300;
        cfg.Collectors.Activity.TitleStableMs = 500;
        cfg.Collectors.Activity.CheckpointSeconds = 5;
        _collector = new WindowsActivityCollector("test-run", CheckpointPath);
        _collector.Start(new CollectorContext(_sink, new ConfigProvider(cfg), _log, SystemClock.Instance));
    }

    private void StopCollector()
    {
        _collector?.Stop("watcher_stopped");
        _collector = null;
    }

    public void Dispose()
    {
        StopCollector();
        _out.WriteLine("Captured events:" + Environment.NewLine + _sink.Dump());
        foreach (var line in _log.Lines) _out.WriteLine("log: " + line);
        try { Directory.Delete(_dir, true); } catch { }
    }

    private bool WaitForStart(string title, int count = 1, int seconds = 10) =>
        Desktop.WaitUntil(() => _sink.OfType(EventTypes.AppSessionStart).Count(e => e.WindowTitle == title) >= count, TimeSpan.FromSeconds(seconds));

    [Fact]
    public void Switching_between_windows_creates_sessions_with_real_window_details()
    {
        using var alpha = new TestWindow("MPP Test Alpha");
        using var bravo = new TestWindow("MPP Test Bravo");
        StartCollector();

        Assert.True(Desktop.BringToFront(alpha.Handle), "could not focus Alpha");
        Assert.True(WaitForStart("MPP Test Alpha"), "no session for Alpha");
        Thread.Sleep(1000);
        Assert.True(Desktop.BringToFront(bravo.Handle), "could not focus Bravo");
        Assert.True(WaitForStart("MPP Test Bravo"), "no session for Bravo");
        Thread.Sleep(1000);
        Assert.True(Desktop.BringToFront(alpha.Handle), "could not refocus Alpha");
        Assert.True(WaitForStart("MPP Test Alpha", count: 2), "no second session for Alpha");
        StopCollector();

        var me = Process.GetCurrentProcess();
        var alphaStart = _sink.OfType(EventTypes.AppSessionStart).First(e => e.WindowTitle == "MPP Test Alpha");
        Assert.Equal(me.ProcessName, alphaStart.ProcessName, ignoreCase: true);
        Assert.Equal(me.Id, alphaStart.ProcessId);
        Assert.False(string.IsNullOrEmpty(alphaStart.Application));
        Assert.StartsWith("WindowsForms", alphaStart.Metadata["window_class"]!.GetValue<string>());
        Assert.NotNull(alphaStart.Metadata["monitor"]);
        Assert.NotNull(alphaStart.Metadata["executable_path"]);

        var alphaEnd = _sink.OfType(EventTypes.AppSessionEnd).First(e => e.SessionId == alphaStart.SessionId);
        Assert.Equal(SessionEndReasons.ForegroundChanged, alphaEnd.Metadata["end_reason"]!.GetValue<string>());
        Assert.Equal("MPP Test Bravo", alphaEnd.Metadata["next_window_title"]!.GetValue<string>());
        Assert.True(alphaEnd.Metadata["duration_seconds"]!.GetValue<double>() >= 0.8);

        var secondAlpha = _sink.OfType(EventTypes.AppSessionStart).Where(e => e.WindowTitle == "MPP Test Alpha").ElementAt(1);
        Assert.Equal(alphaStart.SessionId, secondAlpha.Metadata["returning_to_session_id"]!.GetValue<string>());

        Assert.Equal(_sink.OfType(EventTypes.AppSessionStart).Count, _sink.OfType(EventTypes.AppSessionEnd).Count);
        Assert.Equal(SessionEndReasons.WatcherStopped, _sink.OfType(EventTypes.AppSessionEnd).Last().Metadata["end_reason"]!.GetValue<string>());
    }

    [Fact]
    public void Real_title_change_splits_but_unread_counter_does_not()
    {
        using var w = new TestWindow("(3) Inbox - MPP Test Mail");
        StartCollector();
        Assert.True(Desktop.BringToFront(w.Handle));
        Assert.True(WaitForStart("(3) Inbox - MPP Test Mail"));

        w.SetTitle("(4) Inbox - MPP Test Mail");
        Thread.Sleep(2000);
        Assert.Single(_sink.OfType(EventTypes.AppSessionStart));

        w.SetTitle("Amazon.com: MPP Test Stationery");
        Assert.True(WaitForStart("Amazon.com: MPP Test Stationery"), "title change did not start a session");
        StopCollector();

        var end = _sink.OfType(EventTypes.AppSessionEnd).First();
        Assert.Equal(SessionEndReasons.TitleChanged, end.Metadata["end_reason"]!.GetValue<string>());
        Assert.Equal("(4) Inbox - MPP Test Mail", end.WindowTitle);
    }

    [Fact]
    public void Idle_is_detected_from_real_input_timing()
    {
        using var w = new TestWindow("MPP Test Idle");
        StartCollector(idleSeconds: 30); // lowest allowed
        Assert.True(Desktop.BringToFront(w.Handle));
        Assert.True(WaitForStart("MPP Test Idle"));
        Desktop.NudgeMouse();

        Assert.True(Desktop.WaitUntil(() => _sink.OfType(EventTypes.IdleStart).Count > 0, TimeSpan.FromSeconds(45)), "idle_start not detected");
        var idleStart = _sink.OfType(EventTypes.IdleStart).Single();
        var detectedAt = DateTimeOffset.Parse(idleStart.Metadata["detected_at"]!.GetValue<string>());
        Assert.InRange((detectedAt - idleStart.TimestampUtc).TotalSeconds, 29, 33); // back-dated to last input

        Thread.Sleep(3000);
        Desktop.NudgeMouse();
        Assert.True(Desktop.WaitUntil(() => _sink.OfType(EventTypes.IdleEnd).Count > 0, TimeSpan.FromSeconds(5)), "idle_end not detected after mouse input");
        var idleEnd = _sink.OfType(EventTypes.IdleEnd).Single();
        Assert.Equal("input_resumed", idleEnd.Metadata["end_reason"]!.GetValue<string>());
        Assert.InRange(idleEnd.Metadata["idle_seconds"]!.GetValue<double>(), 31, 45);
        StopCollector();

        var end = _sink.OfType(EventTypes.AppSessionEnd).Single();
        Assert.InRange(end.Metadata["idle_seconds"]!.GetValue<double>(), 31, 45);
        Assert.True(end.Metadata["active_seconds"]!.GetValue<double>() < end.Metadata["duration_seconds"]!.GetValue<double>());
    }

    [Fact]
    public void Another_program_window_is_identified_by_its_exe()
    {
        using var notepad = Process.Start(new ProcessStartInfo("notepad.exe") { UseShellExecute = true })!;
        try
        {
            IntPtr hwnd = IntPtr.Zero;
            Assert.True(Desktop.WaitUntil(() =>
            {
                var p = Process.GetProcessesByName("notepad").FirstOrDefault(x => x.MainWindowHandle != IntPtr.Zero);
                hwnd = p?.MainWindowHandle ?? IntPtr.Zero;
                return hwnd != IntPtr.Zero;
            }, TimeSpan.FromSeconds(15)), "Notepad window did not appear");

            StartCollector();
            Assert.True(Desktop.BringToFront(hwnd), "could not focus Notepad");
            Assert.True(Desktop.WaitUntil(() => _sink.OfType(EventTypes.AppSessionStart)
                .Any(e => string.Equals(e.ProcessName, "notepad", StringComparison.OrdinalIgnoreCase)), TimeSpan.FromSeconds(10)), "no Notepad session");
            StopCollector();

            var s = _sink.OfType(EventTypes.AppSessionStart).First(e => string.Equals(e.ProcessName, "notepad", StringComparison.OrdinalIgnoreCase));
            _out.WriteLine($"Notepad seen as application='{s.Application}' title='{s.WindowTitle}' path='{s.Metadata["executable_path"]}'");
            Assert.Contains("Notepad", s.Application!, StringComparison.OrdinalIgnoreCase);
            Assert.EndsWith("notepad.exe", s.Metadata["executable_path"]!.GetValue<string>(), StringComparison.OrdinalIgnoreCase);
            Assert.Contains("Notepad", s.WindowTitle!, StringComparison.OrdinalIgnoreCase);
        }
        finally
        {
            foreach (var p in Process.GetProcessesByName("notepad")) { try { p.Kill(); } catch { } }
        }
    }

    [Fact]
    public void Open_session_is_checkpointed_and_cleared_on_clean_stop()
    {
        using var w = new TestWindow("MPP Test Checkpoint");
        StartCollector();
        Assert.True(Desktop.BringToFront(w.Handle));
        Assert.True(WaitForStart("MPP Test Checkpoint"));
        Assert.True(Desktop.WaitUntil(() => File.Exists(CheckpointPath), TimeSpan.FromSeconds(10)), "checkpoint not written");
        var cp = new CheckpointStore(CheckpointPath).Load()!;
        Assert.Equal(_sink.OfType(EventTypes.AppSessionStart).Last().SessionId, cp.SessionId);
        StopCollector();
        Assert.False(File.Exists(CheckpointPath));
    }

    [Fact]
    public void Checkpoint_left_by_a_crash_is_closed_on_start()
    {
        new CheckpointStore(CheckpointPath).Save(new SessionCheckpoint
        {
            SessionId = "crashed-session", ProcessName = "chrome", Application = "Google Chrome", WindowTitle = "Keepa",
            SessionStart = DateTimeOffset.Now.AddMinutes(-10), LastSeen = DateTimeOffset.Now.AddMinutes(-2), IdleSeconds = 30, WatcherRunId = "old",
        });
        StartCollector();
        StopCollector();
        var recovered = _sink.OfType(EventTypes.AppSessionEnd).First(e => e.SessionId == "crashed-session");
        Assert.Equal(SessionEndReasons.CrashRecovered, recovered.Metadata["end_reason"]!.GetValue<string>());
        Assert.Equal(480, recovered.Metadata["duration_seconds"]!.GetValue<double>(), 0);
    }
}
