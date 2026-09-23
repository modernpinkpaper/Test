namespace MppWatcher.Core.Configuration;

/// <summary>Resolves the standard folders. Everything can be overridden in config.json.</summary>
public static class WatcherPaths
{
    public const string ProductFolderName = "MPP Watcher";

    /// <summary>Machine-wide config, managed by the admin / installer: %ProgramData%\MPP Watcher\config.json.</summary>
    public static string DefaultConfigPath =>
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData), ProductFolderName, "config.json");

    /// <summary>Per-user base folder: %LOCALAPPDATA%\MPP Watcher.</summary>
    public static string UserBaseFolder =>
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), ProductFolderName);

    public static string DataFolder(WatcherConfig c) => Expand(c.DataFolder, Path.Combine(UserBaseFolder, "data"));
    public static string LogFolder(WatcherConfig c) => Expand(c.LogFolder, Path.Combine(UserBaseFolder, "logs"));
    /// <summary>Where exported JSONL goes. May still contain the {GoogleDrive} token (see Export.ExportDestination).</summary>
    public static string ExportFolder(WatcherConfig c) => Expand(c.Export.DestinationFolder, Path.Combine(UserBaseFolder, "export", "MPP Activity Logs"));
    public static string DatabasePath(WatcherConfig c) => Path.Combine(DataFolder(c), "events.db");
    public static string CheckpointPath(WatcherConfig c) => Path.Combine(DataFolder(c), "open-session.json");
    public static string FallbackFolder(WatcherConfig c) => Path.Combine(DataFolder(c), "fallback");

    private static string Expand(string configured, string fallback)
    {
        if (string.IsNullOrWhiteSpace(configured)) return fallback;
        return Environment.ExpandEnvironmentVariables(configured.Trim());
    }
}
