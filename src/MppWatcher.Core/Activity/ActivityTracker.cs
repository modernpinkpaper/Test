using MppWatcher.Core.Events;

namespace MppWatcher.Core.Activity;

public sealed class ActivityTrackerOptions
{
    public TimeSpan ForegroundStable { get; set; } = TimeSpan.FromSeconds(1);
    public TimeSpan TitleStable { get; set; } = TimeSpan.FromSeconds(2);
    public bool SplitOnTitleChange { get; set; } = true;
    public TimeSpan GapThreshold { get; set; } = TimeSpan.FromSeconds(60);
    public TimeSpan ReturnWindow { get; set; } = TimeSpan.FromHours(4);
}

/// <summary>
/// Turns a stream of observations (foreground window, time since last input, lock/sleep)
/// into clean sessions: app_session_start / app_session_end, idle_start / idle_end,
/// window_title_changed, and lock/sleep events.
///
/// Rules:
/// - A new foreground window only counts after it stays in front for ForegroundStable
///   (Alt+Tab flicker is ignored). Its session is back-dated to when it came to the front.
/// - A real title change (not an unread counter etc.) that stays for TitleStable starts a new
///   session when SplitOnTitleChange is on (e.g. a new Amazon product page in the same Chrome window).
/// - Idle time inside a session is counted; the session is NOT split by idle.
/// - Lock, sleep and sign-out end the session. After unlock/wake a new session starts.
/// - If the watcher misses ticks for longer than GapThreshold (sleep without a notification,
///   frozen PC), the session is closed at the last tick seen.
///
/// Not thread-safe: call it from one thread (the Windows app uses its UI thread).
/// </summary>
public sealed class ActivityTracker
{
    private readonly Func<ActivityTrackerOptions> _options;
    private readonly IdleDetector _idle;
    private readonly Func<TimeSpan> _idleThreshold;
    private readonly Action<WatchEvent> _emit;
    private readonly string _collector;
    private readonly string _collectorVersion;
    private readonly Dictionary<string, (string SessionId, DateTimeOffset EndedAt)> _recent = new();

    private OpenSession? _session;
    private (WindowSnapshot Window, DateTimeOffset Since)? _pendingWindow;
    private (string Title, DateTimeOffset Since)? _pendingTitle;
    private DateTimeOffset? _lastTick;
    private string? _lastEndedSessionId;
    private bool _locked, _suspended, _ending;
    private DateTimeOffset? _lockedAt, _suspendedAt, _endingAt;

    /// <summary>If Windows said "signing out" but we are still running after this, the sign-out was cancelled.</summary>
    public static readonly TimeSpan CancelledSessionEndAfter = TimeSpan.FromMinutes(2);

    public ActivityTracker(Func<ActivityTrackerOptions> options, Func<TimeSpan> idleThreshold, Action<WatchEvent> emit,
        string collector, string collectorVersion)
    {
        _options = options;
        _idleThreshold = idleThreshold;
        _idle = new IdleDetector(idleThreshold);
        _emit = emit;
        _collector = collector;
        _collectorVersion = collectorVersion;
    }

    public string? CurrentSessionId => _session?.Id;
    public WindowSnapshot? CurrentWindow => _session?.Window;
    public bool IsIdle => _idle.IsIdle;
    public bool IsPaused => _locked || _suspended || _ending;
    public int SessionsStarted { get; private set; }

    // ---------------- Observations ----------------

    /// <summary>Report the current foreground window (null if none). Call on every poll and on foreground hooks.</summary>
    public void ObserveForeground(WindowSnapshot? window, DateTimeOffset now)
    {
        if (IsPaused || window is null) return;

        if (_session is not null && _session.Window.IsSameWindow(window))
        {
            _pendingWindow = null;
            ObserveTitle(window, now);
        }
        else if (_pendingWindow is { } p && p.Window.IsSameWindow(window))
        {
            _pendingWindow = (window, p.Since); // keep the time it first came to the front, refresh the title
        }
        else
        {
            _pendingWindow = (window, now);
        }
        TryCommit(now);
    }

    /// <summary>Report how long ago the last keyboard/mouse input happened.</summary>
    public void ObserveInput(TimeSpan timeSinceLastInput, DateTimeOffset now)
    {
        if (IsPaused) return;
        switch (_idle.Update(timeSinceLastInput, now))
        {
            case IdleTransition.Started s:
                if (_session is not null) _session.IdleSince = Max(s.IdleSince, _session.Start);
                var start = NewEvent(EventTypes.IdleStart, s.IdleSince, _session?.Window);
                start.Metadata["idle_start"] = TimeFormat.Iso(s.IdleSince);
                start.Metadata["detected_at"] = TimeFormat.Iso(s.DetectedAt);
                start.Metadata["idle_threshold_seconds"] = _idleThreshold().TotalSeconds;
                _emit(start);
                break;
            case IdleTransition.Ended e:
                CloseIdle(e.IdleSince, e.ActiveAgainAt, "input_resumed");
                break;
        }
    }

    /// <summary>Call on a timer (every poll). Commits pending changes and detects gaps.</summary>
    public void Tick(DateTimeOffset now)
    {
        var o = _options();
        if (_ending && _endingAt is { } endingAt && now - endingAt > CancelledSessionEndAfter)
        {
            _ending = false;
            _endingAt = null;
            AfterResume(now);
        }
        if (_lastTick is { } last && now - last > o.GapThreshold)
        {
            HandleGap(last, now);
        }
        _lastTick = now;
        TryCommit(now);
    }

    public void OnLocked(DateTimeOffset now)
    {
        var e = NewEvent(EventTypes.WorkstationLocked, now, _session?.Window);
        PauseActivity(now, SessionEndReasons.Locked);
        _emit(e);
        _locked = true;
        _lockedAt = now;
    }

    public void OnUnlocked(DateTimeOffset now)
    {
        var e = NewEvent(EventTypes.WorkstationUnlocked, now, null);
        if (_lockedAt is { } at) e.Metadata["locked_seconds"] = TimeFormat.Seconds(now - at);
        _emit(e);
        _locked = false;
        _lockedAt = null;
        AfterResume(now);
    }

    public void OnSuspend(DateTimeOffset now)
    {
        var e = NewEvent(EventTypes.SystemSuspend, now, _session?.Window);
        PauseActivity(now, SessionEndReasons.Suspended);
        _emit(e);
        _suspended = true;
        _suspendedAt = now;
    }

    public void OnResume(DateTimeOffset now)
    {
        var e = NewEvent(EventTypes.SystemResume, now, null);
        if (_suspendedAt is { } at) e.Metadata["suspended_seconds"] = TimeFormat.Seconds(now - at);
        _emit(e);
        _suspended = false;
        _suspendedAt = null;
        AfterResume(now);
    }

    /// <summary>Windows is signing out or shutting down.</summary>
    public void OnSessionEnding(DateTimeOffset now, string kind)
    {
        var e = NewEvent(EventTypes.SessionEnding, now, _session?.Window);
        e.Metadata["kind"] = kind;
        PauseActivity(now, SessionEndReasons.SessionEnding);
        _emit(e);
        _ending = true;
        _endingAt = now;
    }

    /// <summary>The watcher is stopping: close everything that is open.</summary>
    public void Stop(DateTimeOffset now, string reason = SessionEndReasons.WatcherStopped) => PauseActivity(now, reason);

    // ---------------- Crash recovery ----------------

    public SessionCheckpoint? CreateCheckpoint(DateTimeOffset now, string watcherRunId)
    {
        if (_session is null) return null;
        return new SessionCheckpoint
        {
            SessionId = _session.Id,
            ProcessName = _session.Window.ProcessName,
            ProcessId = _session.Window.ProcessId,
            Application = _session.Window.DisplayApplication,
            WindowTitle = _session.Window.Title,
            SessionStart = _session.Start,
            LastSeen = now,
            IdleSeconds = TimeFormat.Seconds(_session.IdleSoFar(now)),
            WatcherRunId = watcherRunId,
        };
    }

    /// <summary>Closes a session left open by a previous run that did not stop cleanly.</summary>
    public void EmitRecoveredSessionEnd(SessionCheckpoint cp)
    {
        var e = new WatchEvent
        {
            EventType = EventTypes.AppSessionEnd,
            TimestampUtc = cp.LastSeen,
            Collector = _collector,
            CollectorVersion = _collectorVersion,
            SessionId = cp.SessionId,
            Application = cp.Application,
            ProcessName = cp.ProcessName,
            ProcessId = cp.ProcessId,
            WindowTitle = cp.WindowTitle,
        };
        var duration = cp.LastSeen - cp.SessionStart;
        e.Metadata["session_start"] = TimeFormat.Iso(cp.SessionStart);
        e.Metadata["session_end"] = TimeFormat.Iso(cp.LastSeen);
        e.Metadata["duration_seconds"] = TimeFormat.Seconds(duration);
        e.Metadata["idle_seconds"] = cp.IdleSeconds;
        e.Metadata["active_seconds"] = Math.Max(0, TimeFormat.Seconds(duration) - cp.IdleSeconds);
        e.Metadata["end_reason"] = SessionEndReasons.CrashRecovered;
        e.Metadata["foreground"] = true;
        e.Metadata["recovered_from_run_id"] = cp.WatcherRunId;
        e.Metadata["end_time_is_approximate"] = true;
        _emit(e);
    }

    // ---------------- Internals ----------------

    private void ObserveTitle(WindowSnapshot window, DateTimeOffset now)
    {
        var s = _session!;
        var title = window.Title ?? "";
        if (title == (s.Window.Title ?? ""))
        {
            _pendingTitle = null;
            return;
        }
        if (Browser.BrowserTitle.IsPlaceholder(Browser.BrowserTitle.PageTitle(title)))
        {
            // Browser "Untitled"/"New Tab" while a page loads: wait for the real title.
            _pendingTitle = null;
            return;
        }
        if (TitleNormalizer.Normalize(title) == s.NormalizedTitle)
        {
            // Cosmetic change only (unread counter, zoom level...): keep the session, remember the latest text.
            s.Window = s.Window with { Title = title };
            _pendingTitle = null;
            return;
        }
        if (_pendingTitle?.Title != title) _pendingTitle = (title, now);
    }

    private void TryCommit(DateTimeOffset now)
    {
        var o = _options();
        if (_pendingWindow is { } pw && now - pw.Since >= o.ForegroundStable)
        {
            _pendingWindow = null;
            _pendingTitle = null;
            EndSession(pw.Since, SessionEndReasons.ForegroundChanged, pw.Window);
            StartSession(pw.Window, pw.Since);
        }

        if (_session is not null && _pendingTitle is { } pt && now - pt.Since >= o.TitleStable)
        {
            _pendingTitle = null;
            var newWindow = _session.Window with { Title = pt.Title };
            if (o.SplitOnTitleChange)
            {
                EndSession(pt.Since, SessionEndReasons.TitleChanged, newWindow);
                StartSession(newWindow, pt.Since);
            }
            else
            {
                var e = NewEvent(EventTypes.WindowTitleChanged, pt.Since, newWindow);
                e.Metadata["previous_title"] = _session.Window.Title;
                _session.Window = newWindow;
                _session.NormalizedTitle = TitleNormalizer.Normalize(pt.Title);
                _session.TitleChanges++;
                _emit(e);
            }
        }
    }

    private void StartSession(WindowSnapshot w, DateTimeOffset at)
    {
        var s = new OpenSession(Guid.NewGuid().ToString("N"), w, at) { NormalizedTitle = TitleNormalizer.Normalize(w.Title) };
        if (_idle.IsIdle) s.IdleSince = at;
        _session = s;
        SessionsStarted++;

        var e = NewEvent(EventTypes.AppSessionStart, at, w);
        e.Metadata["session_start"] = TimeFormat.Iso(at);
        e.Metadata["foreground"] = true;
        AddWindowDetails(e, w);
        if (_lastEndedSessionId is not null) e.Metadata["previous_session_id"] = _lastEndedSessionId;

        PruneRecent(at);
        if (_recent.TryGetValue(RecentKey(w), out var prior))
        {
            e.Metadata["returning_to_session_id"] = prior.SessionId;
            e.Metadata["seconds_since_last_visit"] = TimeFormat.Seconds(at - prior.EndedAt);
        }
        _emit(e);
    }

    private void EndSession(DateTimeOffset at, string reason, WindowSnapshot? next = null)
    {
        var s = _session;
        if (s is null) return;
        _session = null;
        at = Max(at, s.Start);
        var idle = s.IdleSoFar(at);
        var duration = at - s.Start;

        var e = NewEvent(EventTypes.AppSessionEnd, at, s.Window, s.Id);
        e.Metadata["session_start"] = TimeFormat.Iso(s.Start);
        e.Metadata["session_end"] = TimeFormat.Iso(at);
        e.Metadata["duration_seconds"] = TimeFormat.Seconds(duration);
        e.Metadata["active_seconds"] = TimeFormat.Seconds(duration - idle);
        e.Metadata["idle_seconds"] = TimeFormat.Seconds(idle);
        e.Metadata["end_reason"] = reason;
        e.Metadata["foreground"] = true;
        if (s.TitleChanges > 0) e.Metadata["title_changes"] = s.TitleChanges;
        if (next is not null)
        {
            e.Metadata["next_process_name"] = next.ProcessName;
            e.Metadata["next_application"] = next.DisplayApplication;
            if (next.ProcessId == s.Window.ProcessId) e.Metadata["next_window_title"] = next.Title;
        }
        _emit(e);

        _recent[RecentKey(s.Window)] = (s.Id, at);
        _lastEndedSessionId = s.Id;
    }

    private void CloseIdle(DateTimeOffset idleSince, DateTimeOffset endedAt, string reason)
    {
        if (_session?.IdleSince is { } sessionIdleStart)
        {
            _session.IdleSeconds += Max(TimeSpan.Zero, endedAt - sessionIdleStart);
            _session.IdleSince = null;
        }
        var e = NewEvent(EventTypes.IdleEnd, endedAt, _session?.Window);
        e.Metadata["idle_start"] = TimeFormat.Iso(idleSince);
        e.Metadata["idle_end"] = TimeFormat.Iso(endedAt);
        e.Metadata["idle_seconds"] = TimeFormat.Seconds(endedAt - idleSince);
        e.Metadata["end_reason"] = reason;
        _emit(e);
    }

    /// <summary>End session and idle period at <paramref name="at"/> (lock, sleep, stop, gap).</summary>
    private void PauseActivity(DateTimeOffset at, string reason)
    {
        if (IsPaused) return;
        _pendingWindow = null;
        _pendingTitle = null;
        // Close the session first so its idle share is computed, then the idle period.
        var idleSince = _idle.IdleSince;
        EndSession(at, reason);
        if (idleSince is { } since)
        {
            CloseIdle(since, Max(at, since), reason);
            _idle.Reset();
        }
    }

    private void AfterResume(DateTimeOffset now)
    {
        if (IsPaused) return;
        _idle.Reset();
        _lastTick = now; // the paused time is not a "gap"
    }

    private void HandleGap(DateTimeOffset lastTick, DateTimeOffset now)
    {
        var gap = NewEvent(EventTypes.ActivityGap, lastTick, _session?.Window);
        gap.Metadata["gap_start"] = TimeFormat.Iso(lastTick);
        gap.Metadata["gap_end"] = TimeFormat.Iso(now);
        gap.Metadata["gap_seconds"] = TimeFormat.Seconds(now - lastTick);
        gap.Metadata["explanation"] = "The watcher did not run during this time (sleep, hibernate, or the PC was frozen).";
        if (IsPaused)
        {
            _emit(gap);
            return;
        }
        PauseActivity(lastTick, SessionEndReasons.ActivityGap);
        _emit(gap);
        _idle.Reset();
    }

    private void PruneRecent(DateTimeOffset now)
    {
        var window = _options().ReturnWindow;
        foreach (var k in _recent.Where(kv => now - kv.Value.EndedAt > window).Select(kv => kv.Key).ToList()) _recent.Remove(k);
    }

    private static string RecentKey(WindowSnapshot w) => w.ProcessName.ToLowerInvariant() + "|" + TitleNormalizer.Normalize(w.Title);

    private WatchEvent NewEvent(string type, DateTimeOffset at, WindowSnapshot? w, string? sessionId = null)
    {
        var e = new WatchEvent
        {
            EventType = type,
            TimestampUtc = at,
            Collector = _collector,
            CollectorVersion = _collectorVersion,
            SessionId = sessionId ?? _session?.Id,
        };
        if (w is not null)
        {
            e.Application = w.DisplayApplication;
            e.ProcessName = w.ProcessName;
            e.ProcessId = w.ProcessId;
            e.WindowTitle = w.Title;
        }
        return e;
    }

    private static void AddWindowDetails(WatchEvent e, WindowSnapshot w)
    {
        if (w.ExecutablePath is not null) e.Metadata["executable_path"] = w.ExecutablePath;
        if (w.WindowClass is not null) e.Metadata["window_class"] = w.WindowClass;
        if (w.Monitor is not null) e.Metadata["monitor"] = w.Monitor;
        e.Metadata["window_handle"] = "0x" + w.Handle.ToString("X");
    }

    private static DateTimeOffset Max(DateTimeOffset a, DateTimeOffset b) => a > b ? a : b;
    private static TimeSpan Max(TimeSpan a, TimeSpan b) => a > b ? a : b;

    private sealed class OpenSession
    {
        public OpenSession(string id, WindowSnapshot window, DateTimeOffset start)
        {
            Id = id;
            Window = window;
            Start = start;
        }

        public string Id { get; }
        public WindowSnapshot Window { get; set; }
        public string NormalizedTitle { get; set; } = "";
        public DateTimeOffset Start { get; }
        public TimeSpan IdleSeconds { get; set; }
        public DateTimeOffset? IdleSince { get; set; }
        public int TitleChanges { get; set; }

        public TimeSpan IdleSoFar(DateTimeOffset at) =>
            IdleSeconds + (IdleSince is { } s && at > s ? at - s : TimeSpan.Zero);
    }
}
