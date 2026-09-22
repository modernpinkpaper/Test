using MppWatcher.Core.Activity;
using MppWatcher.Core.Events;
using static MppWatcher.Core.Tests.T;

namespace MppWatcher.Core.Tests;

public class ActivityTrackerTests
{
    private readonly List<WatchEvent> _events = new();
    private readonly FakeClock _clock = new(Start);
    private readonly ActivityTrackerOptions _options = new()
    {
        ForegroundStable = TimeSpan.FromSeconds(1),
        TitleStable = TimeSpan.FromSeconds(2),
        SplitOnTitleChange = true,
        GapThreshold = TimeSpan.FromSeconds(60),
        ReturnWindow = TimeSpan.FromHours(4),
    };
    private TimeSpan _idleThreshold = TimeSpan.FromMinutes(5);
    private readonly ActivityTracker _tracker;

    public ActivityTrackerTests()
    {
        _tracker = new ActivityTracker(() => _options, () => _idleThreshold, _events.Add, "activity", "1.0.0");
    }

    /// <summary>Simulates the poll loop: every 500 ms report the window and "user is typing".</summary>
    private void Run(WindowSnapshot w, TimeSpan duration, bool userActive = true, DateTimeOffset? lastInput = null)
    {
        var end = _clock.Now + duration;
        var input = lastInput ?? _clock.Now;
        while (_clock.Now < end)
        {
            _clock.Advance(TimeSpan.FromMilliseconds(500));
            if (userActive) input = _clock.Now;
            _tracker.Tick(_clock.Now);
            _tracker.ObserveForeground(w, _clock.Now);
            _tracker.ObserveInput(_clock.Now - input, _clock.Now);
        }
    }

    private List<WatchEvent> OfType(string type) => _events.Where(e => e.EventType == type).ToList();

    [Fact]
    public void First_window_starts_a_session_after_it_is_stable()
    {
        Run(Chrome("Keepa - Amazon Price Tracker"), TimeSpan.FromMilliseconds(500));
        Assert.Empty(OfType(EventTypes.AppSessionStart));

        Run(Chrome("Keepa - Amazon Price Tracker"), TimeSpan.FromSeconds(2));
        var start = Assert.Single(OfType(EventTypes.AppSessionStart));
        Assert.Equal("Google Chrome", start.Application);
        Assert.Equal("chrome", start.ProcessName);
        Assert.Equal("Keepa - Amazon Price Tracker", start.WindowTitle);
        Assert.Equal(Start.AddMilliseconds(500), start.TimestampUtc); // back-dated to when it first appeared
        Assert.Equal("DISPLAY1", Str(start, "monitor"));
        Assert.NotNull(start.SessionId);
    }

    [Fact]
    public void Switching_apps_ends_the_session_with_durations_and_next_app()
    {
        Run(Chrome("Keepa"), TimeSpan.FromSeconds(60));
        Run(Photoshop("MA023-main.psd @ 50% (RGB/8)"), TimeSpan.FromSeconds(30));

        var end = Assert.Single(OfType(EventTypes.AppSessionEnd));
        Assert.Equal("chrome", end.ProcessName);
        Assert.Equal(SessionEndReasons.ForegroundChanged, Str(end, "end_reason"));
        Assert.Equal("Adobe Photoshop 2025", Str(end, "next_application"));
        Assert.Equal(60, Num(end, "duration_seconds"), 1);
        Assert.Equal(60, Num(end, "active_seconds"), 1);
        Assert.Equal(0, Num(end, "idle_seconds"));

        var starts = OfType(EventTypes.AppSessionStart);
        Assert.Equal(2, starts.Count);
        Assert.Equal(end.SessionId, starts[0].SessionId);
        Assert.Equal(end.SessionId, Str(starts[1], "previous_session_id"));
    }

    [Fact]
    public void Alt_tab_flicker_shorter_than_stable_time_is_ignored()
    {
        Run(Chrome("Keepa"), TimeSpan.FromSeconds(10));
        Run(Excel(), TimeSpan.FromMilliseconds(500)); // passes by during Alt+Tab
        Run(Chrome("Keepa"), TimeSpan.FromSeconds(10));

        Assert.Single(OfType(EventTypes.AppSessionStart));
        Assert.Empty(OfType(EventTypes.AppSessionEnd));
    }

    [Fact]
    public void Real_title_change_splits_session_but_cosmetic_change_does_not()
    {
        Run(Chrome("(3) Inbox - Gmail"), TimeSpan.FromSeconds(10));
        Run(Chrome("(4) Inbox - Gmail"), TimeSpan.FromSeconds(10));   // unread counter only
        Assert.Single(OfType(EventTypes.AppSessionStart));

        Run(Chrome("Amazon.com: Personalized Stationery Set"), TimeSpan.FromSeconds(10));
        var end = Assert.Single(OfType(EventTypes.AppSessionEnd));
        Assert.Equal(SessionEndReasons.TitleChanged, Str(end, "end_reason"));
        Assert.Equal("Amazon.com: Personalized Stationery Set", Str(end, "next_window_title"));
        Assert.Equal("(4) Inbox - Gmail", end.WindowTitle); // latest real text is kept
        Assert.Equal(2, OfType(EventTypes.AppSessionStart).Count);
    }

    [Fact]
    public void Title_that_changes_back_quickly_does_not_split()
    {
        Run(Chrome("Keepa"), TimeSpan.FromSeconds(10));
        Run(Chrome("Loading..."), TimeSpan.FromSeconds(1));
        Run(Chrome("Keepa"), TimeSpan.FromSeconds(10));
        Assert.Single(OfType(EventTypes.AppSessionStart));
    }

    [Fact]
    public void Without_split_a_title_change_is_logged_inside_the_session()
    {
        _options.SplitOnTitleChange = false;
        Run(Chrome("Keepa"), TimeSpan.FromSeconds(10));
        Run(Chrome("Seller Central - Inventory"), TimeSpan.FromSeconds(10));
        Run(Excel(), TimeSpan.FromSeconds(5));

        Assert.Single(OfType(EventTypes.WindowTitleChanged));
        var end = Assert.Single(OfType(EventTypes.AppSessionEnd));
        Assert.Equal(1, end.Metadata["title_changes"]!.GetValue<int>());
    }

    [Fact]
    public void Idle_time_is_counted_inside_the_session_and_backdated_to_last_input()
    {
        _idleThreshold = TimeSpan.FromMinutes(5);
        Run(Chrome("Keepa"), TimeSpan.FromMinutes(1));
        var lastInput = _clock.Now;
        Run(Chrome("Keepa"), TimeSpan.FromMinutes(10), userActive: false, lastInput: lastInput);

        var idleStart = Assert.Single(OfType(EventTypes.IdleStart));
        Assert.Equal(lastInput, idleStart.TimestampUtc);
        Assert.Equal(idleStart.SessionId, OfType(EventTypes.AppSessionStart)[0].SessionId);

        Run(Chrome("Keepa"), TimeSpan.FromMinutes(1)); // user returns
        var idleEnd = Assert.Single(OfType(EventTypes.IdleEnd));
        Assert.Equal(10, Num(idleEnd, "idle_seconds") / 60, 1);

        Run(Excel(), TimeSpan.FromSeconds(5));
        var end = Assert.Single(OfType(EventTypes.AppSessionEnd));
        Assert.Equal(12 * 60, Num(end, "duration_seconds"), 0);
        Assert.Equal(10 * 60, Num(end, "idle_seconds"), 0);
        Assert.Equal(2 * 60, Num(end, "active_seconds"), 0);
    }

    [Fact]
    public void Lock_ends_session_and_unlock_starts_a_new_one()
    {
        Run(Chrome("Keepa"), TimeSpan.FromSeconds(30));
        _tracker.OnLocked(_clock.Now);
        _clock.Advance(TimeSpan.FromMinutes(20));
        _tracker.OnUnlocked(_clock.Now);
        Run(Chrome("Keepa"), TimeSpan.FromSeconds(5));

        var end = Assert.Single(OfType(EventTypes.AppSessionEnd));
        Assert.Equal(SessionEndReasons.Locked, Str(end, "end_reason"));
        Assert.Single(OfType(EventTypes.WorkstationLocked));
        var unlocked = Assert.Single(OfType(EventTypes.WorkstationUnlocked));
        Assert.Equal(20 * 60, Num(unlocked, "locked_seconds"));
        Assert.Empty(OfType(EventTypes.ActivityGap)); // locked time is not a gap
        var starts = OfType(EventTypes.AppSessionStart);
        Assert.Equal(2, starts.Count);
        Assert.NotNull(Str(starts[1], "returning_to_session_id"));
    }

    [Fact]
    public void Lock_while_idle_closes_the_idle_period()
    {
        _idleThreshold = TimeSpan.FromMinutes(5);
        Run(Chrome("Keepa"), TimeSpan.FromSeconds(10));
        Run(Chrome("Keepa"), TimeSpan.FromMinutes(6), userActive: false, lastInput: _clock.Now);
        _tracker.OnLocked(_clock.Now);

        var idleEnd = Assert.Single(OfType(EventTypes.IdleEnd));
        Assert.Equal(SessionEndReasons.Locked, Str(idleEnd, "end_reason"));
        var end = Assert.Single(OfType(EventTypes.AppSessionEnd));
        Assert.Equal(6 * 60, Num(end, "idle_seconds"), 0);
    }

    [Fact]
    public void Sleep_while_locked_stays_paused_until_unlock()
    {
        Run(Chrome("Keepa"), TimeSpan.FromSeconds(10));
        _tracker.OnLocked(_clock.Now);
        _tracker.OnSuspend(_clock.Now);
        _clock.Advance(TimeSpan.FromHours(8));
        _tracker.OnResume(_clock.Now);
        Assert.True(_tracker.IsPaused); // still locked
        Run(Chrome("Keepa"), TimeSpan.FromSeconds(5));
        Assert.Single(OfType(EventTypes.AppSessionStart));

        _tracker.OnUnlocked(_clock.Now);
        Run(Chrome("Keepa"), TimeSpan.FromSeconds(5));
        Assert.Equal(2, OfType(EventTypes.AppSessionStart).Count);
        Assert.Single(OfType(EventTypes.AppSessionEnd));
    }

    [Fact]
    public void Missed_ticks_close_the_session_at_the_last_tick()
    {
        Run(Chrome("Keepa"), TimeSpan.FromSeconds(30));
        var lastTick = _clock.Now;
        _clock.Advance(TimeSpan.FromMinutes(45)); // sleep without a notification
        Run(Chrome("Keepa"), TimeSpan.FromSeconds(5));

        var end = Assert.Single(OfType(EventTypes.AppSessionEnd));
        Assert.Equal(SessionEndReasons.ActivityGap, Str(end, "end_reason"));
        Assert.Equal(lastTick, end.TimestampUtc);
        var gap = Assert.Single(OfType(EventTypes.ActivityGap));
        Assert.Equal(45 * 60 + 0.5, Num(gap, "gap_seconds"), 0);
        Assert.Equal(2, OfType(EventTypes.AppSessionStart).Count);
    }

    [Fact]
    public void Returning_to_a_previous_window_is_marked()
    {
        Run(Chrome("Keepa"), TimeSpan.FromSeconds(30));
        Run(Photoshop(), TimeSpan.FromSeconds(30));
        Run(Chrome("Keepa"), TimeSpan.FromSeconds(5));

        var starts = OfType(EventTypes.AppSessionStart);
        Assert.Equal(3, starts.Count);
        Assert.Null(starts[1].Metadata["returning_to_session_id"]);
        Assert.Equal(starts[0].SessionId, Str(starts[2], "returning_to_session_id"));
        Assert.Equal(30, Num(starts[2], "seconds_since_last_visit"), 0);
    }

    [Fact]
    public void Stop_closes_the_open_session()
    {
        Run(Chrome("Keepa"), TimeSpan.FromSeconds(30));
        _tracker.Stop(_clock.Now);
        var end = Assert.Single(OfType(EventTypes.AppSessionEnd));
        Assert.Equal(SessionEndReasons.WatcherStopped, Str(end, "end_reason"));
    }

    [Fact]
    public void Checkpoint_can_be_turned_into_a_recovered_session_end()
    {
        Run(Chrome("Keepa"), TimeSpan.FromSeconds(30));
        var cp = _tracker.CreateCheckpoint(_clock.Now, "run1")!;
        Assert.Equal(_tracker.CurrentSessionId, cp.SessionId);

        var other = new List<WatchEvent>();
        var next = new ActivityTracker(() => _options, () => _idleThreshold, other.Add, "activity", "1.0.0");
        next.EmitRecoveredSessionEnd(cp);
        var end = Assert.Single(other);
        Assert.Equal(EventTypes.AppSessionEnd, end.EventType);
        Assert.Equal(cp.SessionId, end.SessionId);
        Assert.Equal(SessionEndReasons.CrashRecovered, Str(end, "end_reason"));
        Assert.Equal(29.5, Num(end, "duration_seconds"), 1);
    }

    [Fact]
    public void Null_foreground_window_is_ignored()
    {
        Run(Chrome("Keepa"), TimeSpan.FromSeconds(5));
        _tracker.ObserveForeground(null, _clock.Now);
        Run(Chrome("Keepa"), TimeSpan.FromSeconds(5));
        Assert.Single(OfType(EventTypes.AppSessionStart));
    }
}
