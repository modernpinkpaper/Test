using System.Text.Json.Serialization;

namespace MppWatcher.Core.Configuration;

/// <summary>
/// Settings read from config.json (snake_case keys). Every value has a safe default,
/// so a missing or partial file still works. See docs/CONFIGURATION section in README.
/// </summary>
public sealed class WatcherConfig
{
    [JsonPropertyName("company_name")] public string CompanyName { get; set; } = "MPP";

    /// <summary>Default employee id for this PC. Overridden per Windows user by <see cref="EmployeeIdByWindowsUser"/>.</summary>
    [JsonPropertyName("employee_id")] public string EmployeeId { get; set; } = "";

    /// <summary>Map "DOMAIN\\user" or "user" to an employee id, for PCs shared by several people.</summary>
    [JsonPropertyName("employee_id_by_windows_user")]
    public Dictionary<string, string> EmployeeIdByWindowsUser { get; set; } = new(StringComparer.OrdinalIgnoreCase);

    /// <summary>Empty means "use the Windows computer name".</summary>
    [JsonPropertyName("computer_id")] public string ComputerId { get; set; } = "";

    [JsonPropertyName("idle_timeout_seconds")] public int IdleTimeoutSeconds { get; set; } = 300;
    [JsonPropertyName("debug_mode")] public bool DebugMode { get; set; }
    [JsonPropertyName("show_tray_icon")] public bool ShowTrayIcon { get; set; } = true;
    [JsonPropertyName("allow_user_exit")] public bool AllowUserExit { get; set; }

    /// <summary>Where the SQLite database lives. Empty = %LOCALAPPDATA%\MPP Watcher\data.</summary>
    [JsonPropertyName("data_folder")] public string DataFolder { get; set; } = "";

    /// <summary>Where diagnostic (troubleshooting) logs go. Empty = %LOCALAPPDATA%\MPP Watcher\logs.</summary>
    [JsonPropertyName("log_folder")] public string LogFolder { get; set; } = "";

    [JsonPropertyName("collectors")] public CollectorsConfig Collectors { get; set; } = new();
    [JsonPropertyName("privacy")] public PrivacyConfig Privacy { get; set; } = new();
    [JsonPropertyName("export")] public ExportConfig Export { get; set; } = new();
    [JsonPropertyName("retention")] public RetentionConfig Retention { get; set; } = new();
    [JsonPropertyName("deduplication")] public DeduplicationConfig Deduplication { get; set; } = new();
}

public sealed class CollectorsConfig
{
    [JsonPropertyName("activity")] public ActivityCollectorConfig Activity { get; set; } = new();
    [JsonPropertyName("process")] public ProcessCollectorConfig Process { get; set; } = new();
    [JsonPropertyName("ui_automation")] public UiAutomationCollectorConfig UiAutomation { get; set; } = new();
}

public sealed class UiAutomationCollectorConfig
{
    [JsonPropertyName("enabled")] public bool Enabled { get; set; } = true;

    /// <summary>Record the finished value of text fields/drop-downs (never keystrokes; sensitive fields are always skipped).</summary>
    [JsonPropertyName("capture_field_values")] public bool CaptureFieldValues { get; set; } = true;

    /// <summary>Record clicks on named buttons, links, tabs, menu items, check boxes (never click coordinates).</summary>
    [JsonPropertyName("capture_actions")] public bool CaptureActions { get; set; } = true;

    /// <summary>Longer or multi-line values are not stored (only their length). Keeps email bodies etc. out of the log.</summary>
    [JsonPropertyName("max_value_length")] public int MaxValueLength { get; set; } = 200;

    /// <summary>How often the value of the field that has focus is re-read.</summary>
    [JsonPropertyName("focused_field_poll_ms")] public int FocusedFieldPollMs { get; set; } = 500;

    /// <summary>A changed value that stays the same this long is recorded even if the field keeps focus (e.g. a search typed then Enter).</summary>
    [JsonPropertyName("value_settle_seconds")] public int ValueSettleSeconds { get; set; } = 4;

    /// <summary>Button/link names that count as key business actions (is_key_action = true). Whole words, case-insensitive.</summary>
    [JsonPropertyName("action_keywords")]
    public List<string> ActionKeywords { get; set; } = new()
    {
        "save", "publish", "upload", "import", "export", "search", "download", "print", "submit", "update", "apply",
        "add", "create", "delete", "remove", "duplicate", "copy", "send", "confirm", "done", "run", "sync", "generate",
        "renew", "relist", "archive", "activate", "deactivate", "approve", "ship", "refund", "edit", "preview",
    };

    /// <summary>Apps where UI Automation is not used at all (e.g. games, very heavy apps). Wildcards allowed.</summary>
    [JsonPropertyName("ignore_applications")] public List<string> IgnoreApplications { get; set; } = new();
}

public sealed class ActivityCollectorConfig
{
    [JsonPropertyName("enabled")] public bool Enabled { get; set; } = true;

    /// <summary>A new foreground window must stay in front this long before it counts (filters Alt+Tab flicker).</summary>
    [JsonPropertyName("foreground_stable_ms")] public int ForegroundStableMs { get; set; } = 1000;

    /// <summary>A changed window title must stay the same this long before it counts.</summary>
    [JsonPropertyName("title_stable_ms")] public int TitleStableMs { get; set; } = 2000;

    /// <summary>When true a meaningful title change (e.g. new browser tab/page) starts a new session.</summary>
    [JsonPropertyName("split_sessions_on_title_change")] public bool SplitSessionsOnTitleChange { get; set; } = true;

    /// <summary>How often the foreground window and idle state are checked.</summary>
    [JsonPropertyName("poll_interval_ms")] public int PollIntervalMs { get; set; } = 500;

    /// <summary>If the watcher sees no tick for this long (sleep, hang), the session is closed at the last tick.</summary>
    [JsonPropertyName("gap_threshold_seconds")] public int GapThresholdSeconds { get; set; } = 60;

    /// <summary>How long a "return to a previous window" is remembered.</summary>
    [JsonPropertyName("return_window_minutes")] public int ReturnWindowMinutes { get; set; } = 240;

    [JsonPropertyName("heartbeat_minutes")] public int HeartbeatMinutes { get; set; } = 15;

    /// <summary>How often the open session is saved to disk so it can be closed properly after a crash.</summary>
    [JsonPropertyName("checkpoint_seconds")] public int CheckpointSeconds { get; set; } = 30;
}

public sealed class ProcessCollectorConfig
{
    [JsonPropertyName("enabled")] public bool Enabled { get; set; } = true;
    [JsonPropertyName("scan_interval_seconds")] public int ScanIntervalSeconds { get; set; } = 15;

    /// <summary>Background system processes that would only add noise. Wildcards allowed.</summary>
    [JsonPropertyName("ignore_processes")]
    public List<string> IgnoreProcesses { get; set; } = new()
    {
        "svchost", "RuntimeBroker", "conhost", "dllhost", "backgroundTaskHost", "taskhostw", "sihost",
        "SearchProtocolHost", "SearchFilterHost", "SearchIndexer", "SearchHost", "SearchApp", "StartMenuExperienceHost",
        "ShellExperienceHost", "TextInputHost", "ctfmon", "smartscreen", "WmiPrvSE", "audiodg", "fontdrvhost",
        "dwm", "csrss", "winlogon", "wininit", "lsass", "services", "smss", "System", "Idle", "Registry",
        "MoUsoCoreWorker", "TiWorker", "TrustedInstaller", "CompPkgSrv", "WidgetService", "Widgets",
        "LockApp", "UserOOBEBroker", "SecurityHealthSystray", "SecurityHealthService", "MsMpEng", "NisSrv",
        "crashpad_handler", "msedgewebview2", "identity_helper", "GoogleCrashHandler*", "MicrosoftEdgeUpdate",
        "OneDrive.Sync.Service", "FileCoAuth", "CrossDeviceResume", "PhoneExperienceHost", "AggregatorHost",
        "MPPWatcher",
    };

    /// <summary>
    /// Browsers and Adobe apps start many helper processes with the same name.
    /// When true, only the first instance start and the last instance exit are logged.
    /// </summary>
    [JsonPropertyName("collapse_multi_instance")] public bool CollapseMultiInstance { get; set; } = true;
}

public sealed class PrivacyConfig
{
    /// <summary>
    /// What to do with activity that matches a block rule:
    /// "redact" (default) keeps the time spent but hides app/title/URL details;
    /// "drop" writes nothing at all.
    /// </summary>
    [JsonPropertyName("blocked_mode")] public string BlockedMode { get; set; } = "redact";

    /// <summary>Process names (with or without .exe). Wildcards * and ? allowed.</summary>
    [JsonPropertyName("blocked_applications")]
    public List<string> BlockedApplications { get; set; } = new()
    {
        "KeePass*", "1Password*", "Bitwarden*", "LastPass*", "Dashlane*", "NordPass*", "RoboForm*",
        "CredentialUIBroker", "LogonUI", "consent",
    };

    [JsonPropertyName("blocked_window_titles")] public List<string> BlockedWindowTitles { get; set; } = new()
    {
        "*Windows Security*", "*Credential Manager*",
    };

    /// <summary>If not empty, only these domains are logged in detail; all others are redacted.</summary>
    [JsonPropertyName("allowed_domains")] public List<string> AllowedDomains { get; set; } = new();

    [JsonPropertyName("blocked_domains")] public List<string> BlockedDomains { get; set; } = new()
    {
        "*bank*", "accounts.google.com", "login.microsoftonline.com", "login.live.com",
    };

    /// <summary>URL wildcard patterns, e.g. "*://*/checkout*".</summary>
    [JsonPropertyName("blocked_urls")] public List<string> BlockedUrls { get; set; } = new()
    {
        "*/checkout*", "*/payment*", "*/signin*", "*/login*", "*/ap/signin*", "*/password*",
    };

    /// <summary>File folders never logged (used from Phase 4). Wildcards allowed.</summary>
    [JsonPropertyName("blocked_folders")] public List<string> BlockedFolders { get; set; } = new();

    /// <summary>UI control names/automation ids never logged (used from Phase 2). Wildcards allowed.</summary>
    [JsonPropertyName("blocked_controls")] public List<string> BlockedControls { get; set; } = new();

    /// <summary>
    /// Extra words that mark a field as sensitive. These are ADDED to the built-in list
    /// (password, PIN, CVV, card number, SSN, ...), which can never be turned off.
    /// </summary>
    [JsonPropertyName("sensitive_field_terms")] public List<string> SensitiveFieldTerms { get; set; } = new();

    /// <summary>Extra URL query parameter names to strip. Added to the built-in token list.</summary>
    [JsonPropertyName("sensitive_url_parameters")] public List<string> SensitiveUrlParameters { get; set; } = new();
}

public sealed class ExportConfig
{
    [JsonPropertyName("enabled")] public bool Enabled { get; set; } = true;

    /// <summary>"local_folder" for now. "google_drive" is planned.</summary>
    [JsonPropertyName("uploader")] public string Uploader { get; set; } = "local_folder";

    /// <summary>Root folder; files go to &lt;root&gt;\MPP Activity Logs\&lt;employee&gt;\&lt;date&gt;\. Empty = %LOCALAPPDATA%\MPP Watcher\export.</summary>
    [JsonPropertyName("destination_folder")] public string DestinationFolder { get; set; } = "";

    [JsonPropertyName("interval_minutes")] public int IntervalMinutes { get; set; } = 15;
    [JsonPropertyName("batch_size")] public int BatchSize { get; set; } = 2000;
}

public sealed class RetentionConfig
{
    /// <summary>Uploaded events are deleted from the local database after this many days. 0 = keep forever.</summary>
    [JsonPropertyName("keep_uploaded_events_days")] public int KeepUploadedEventsDays { get; set; } = 30;
    [JsonPropertyName("keep_diagnostic_logs_days")] public int KeepDiagnosticLogsDays { get; set; } = 14;
}

public sealed class DeduplicationConfig
{
    /// <summary>Identical events (same type + fingerprint) within this many seconds are written once.</summary>
    [JsonPropertyName("window_seconds")] public int WindowSeconds { get; set; } = 10;
}
