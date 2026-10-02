namespace MppWatcher.Core.Capture;

/// <summary>SOP = build a step-by-step how-to; Decision = reverse-engineer an ads decision.</summary>
public enum CaptureMode { Sop, Decision }

/// <summary>A read-only snapshot of the capture state, safe to pass to other threads.</summary>
public sealed record CaptureSnapshot(bool Active, bool Paused, CaptureMode Mode, string Label, string SessionId)
{
    /// <summary>Recording right now (started and not paused).</summary>
    public bool Recording => Active && !Paused;
    public bool WantsScreenshots => Recording && Mode == CaptureMode.Sop;
}

/// <summary>
/// Holds the current "Record Task" capture session. Thread-safe. Nothing here takes screenshots or
/// touches Windows; it only tracks state so the pipeline can tag events and the screenshot service
/// (Windows) can ask whether it should capture.
/// </summary>
public sealed class CaptureController
{
    private readonly object _gate = new();
    private bool _active, _paused;
    private CaptureMode _mode;
    private string _label = "";
    private string _sessionId = "";

    /// <summary>Raised when a session starts, carrying the new (recording) snapshot.</summary>
    public event Action<CaptureSnapshot>? Started;
    /// <summary>Raised when a session stops, carrying the snapshot it had just before stopping.</summary>
    public event Action<CaptureSnapshot>? Stopped;
    /// <summary>Raised for every event tagged while a session is recording (event + its snapshot).</summary>
    public event Action<Events.WatchEvent, CaptureSnapshot>? EventTagged;

    public CaptureSnapshot Current
    {
        get { lock (_gate) return new CaptureSnapshot(_active, _paused, _mode, _label, _sessionId); }
    }

    /// <summary>Starts a session (replacing any current one). Returns the new snapshot.</summary>
    public CaptureSnapshot Start(CaptureMode mode, string label)
    {
        CaptureSnapshot snap;
        lock (_gate)
        {
            _active = true; _paused = false; _mode = mode;
            _label = string.IsNullOrWhiteSpace(label) ? (mode == CaptureMode.Sop ? "SOP" : "Decision") : label.Trim();
            _sessionId = Guid.NewGuid().ToString("N");
            snap = new CaptureSnapshot(_active, _paused, _mode, _label, _sessionId);
        }
        Started?.Invoke(snap); // fire outside the lock so handlers can do file IO safely
        return snap;
    }

    /// <summary>Stops the session. Returns the snapshot it had just before stopping (Active may be false).</summary>
    public CaptureSnapshot Stop()
    {
        CaptureSnapshot was;
        lock (_gate)
        {
            was = new CaptureSnapshot(_active, _paused, _mode, _label, _sessionId);
            _active = false; _paused = false;
        }
        Stopped?.Invoke(was); // fire outside the lock
        return was;
    }

    public CaptureSnapshot Pause() { lock (_gate) { if (_active) _paused = true; return new CaptureSnapshot(_active, _paused, _mode, _label, _sessionId); } }
    public CaptureSnapshot Resume() { lock (_gate) { if (_active) _paused = false; return new CaptureSnapshot(_active, _paused, _mode, _label, _sessionId); } }

    /// <summary>Adds capture tags to an event when a session is recording. Called for every event.</summary>
    public void Tag(Events.WatchEvent e)
    {
        CaptureSnapshot s;
        lock (_gate) { if (!_active || _paused) return; s = new CaptureSnapshot(_active, _paused, _mode, _label, _sessionId); }
        e.Metadata["capture_mode"] = s.Mode == CaptureMode.Sop ? "sop" : "decision";
        e.Metadata["capture_label"] = s.Label;
        e.Metadata["capture_session_id"] = s.SessionId;
        EventTagged?.Invoke(e, s); // fire outside the lock so the session-log writer can save it to disk
    }
}
