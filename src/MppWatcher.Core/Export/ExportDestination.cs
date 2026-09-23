namespace MppWatcher.Core.Export;

/// <summary>
/// Turns export.destination_folder into a real folder. The "{GoogleDrive}" token stands for the
/// drive that Google Drive for desktop creates (usually G:\). It is looked up again at every export,
/// so a changed drive letter, or Drive starting after the watcher, just works.
/// </summary>
public static class ExportDestination
{
    public const string GoogleDriveToken = "{GoogleDrive}";
    public const string MyDriveFolderName = "My Drive";

    public static bool UsesGoogleDrive(string configured) =>
        configured.Contains(GoogleDriveToken, StringComparison.OrdinalIgnoreCase);

    /// <summary>
    /// Replaces "{GoogleDrive}" with the Google Drive root. Throws <see cref="DirectoryNotFoundException"/>
    /// when Google Drive is not available, so the export fails and the events stay pending on this PC.
    /// </summary>
    public static string Resolve(string configured, Func<IEnumerable<string>>? driveRoots = null)
    {
        if (!UsesGoogleDrive(configured)) return configured;
        var root = FindGoogleDriveRoot((driveRoots ?? ReadyDriveRoots)())
            ?? throw new DirectoryNotFoundException(
                $"Google Drive not found (no drive with a '{MyDriveFolderName}' folder). " +
                "Is Google Drive for desktop running and signed in? The logs stay on this PC and are exported later.");
        var rest = configured[(configured.IndexOf(GoogleDriveToken, StringComparison.OrdinalIgnoreCase) + GoogleDriveToken.Length)..]
            .TrimStart('\\', '/');
        return Path.Combine(root, rest);
    }

    /// <summary>The first drive root that has a "My Drive" folder. G:\ is checked first because Drive uses it by default.</summary>
    public static string? FindGoogleDriveRoot(IEnumerable<string> roots) =>
        roots
            .OrderBy(r => r.StartsWith("G:", StringComparison.OrdinalIgnoreCase) ? 0 : 1)
            .FirstOrDefault(r =>
            {
                try { return Directory.Exists(Path.Combine(r, MyDriveFolderName)); }
                catch { return false; } // a drive that disappeared or refuses access
            });

    private static IEnumerable<string> ReadyDriveRoots()
    {
        foreach (var d in DriveInfo.GetDrives())
        {
            bool ready;
            try { ready = d.IsReady; } catch { ready = false; }
            if (ready) yield return d.RootDirectory.FullName;
        }
    }
}
