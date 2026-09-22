namespace MppWatcher.Core.Events;

/// <summary>All event type names written by the watcher. See docs/EVENT_SCHEMA.md.</summary>
public static class EventTypes
{
    // Watcher lifecycle
    public const string WatcherStarted = "watcher_started";
    public const string WatcherStopped = "watcher_stopped";
    public const string WatcherHeartbeat = "watcher_heartbeat";
    public const string CollectorStatus = "collector_status";
    public const string ConfigChanged = "config_changed";

    // Foreground application / window sessions
    public const string AppSessionStart = "app_session_start";
    public const string AppSessionEnd = "app_session_end";
    public const string WindowTitleChanged = "window_title_changed";

    // Idle
    public const string IdleStart = "idle_start";
    public const string IdleEnd = "idle_end";

    // Workstation / power
    public const string WorkstationLocked = "workstation_locked";
    public const string WorkstationUnlocked = "workstation_unlocked";
    public const string SystemSuspend = "system_suspend";
    public const string SystemResume = "system_resume";
    public const string SessionEnding = "session_ending";
    public const string ActivityGap = "activity_gap";

    // UI Automation (Phase 2)
    public const string UiFieldValue = "ui_field_value";
    public const string UiAction = "ui_action";

    // Browser (Phase 3)
    public const string BrowserPage = "browser_page";

    // Processes
    public const string ProcessInventory = "process_inventory";
    public const string ProcessStarted = "process_started";
    public const string ProcessExited = "process_exited";
}

/// <summary>Why a foreground session ended (metadata.end_reason).</summary>
public static class SessionEndReasons
{
    public const string ForegroundChanged = "foreground_changed";
    public const string TitleChanged = "title_changed";
    public const string Locked = "workstation_locked";
    public const string Suspended = "system_suspend";
    public const string SessionEnding = "session_ending";
    public const string WatcherStopped = "watcher_stopped";
    public const string ActivityGap = "activity_gap";
    public const string CrashRecovered = "watcher_crash_recovered";
    public const string NoForegroundWindow = "no_foreground_window";
}
