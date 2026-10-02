using MppWatcher.Core.Capture;
using MppWatcher.Core.Configuration;
using MppWatcher.Core.Export;
using MppWatcher.Core.Pipeline;
using MppWatcher.Core.Runtime;

namespace MppWatcher.Windows.Ui;

/// <summary>One source of truth for where a "Record Task" session's files live (screenshots AND the log
/// slice), so the screenshotter and the session-log writer always point at the same folder.</summary>
internal static class SopPaths
{
    /// <summary>Per-session folder: &lt;employee&gt;/_sop_screenshots/&lt;label&gt;_&lt;sid8&gt;, beside the person's logs
    /// in the export folder; falls back to the local data folder if the export folder can't be resolved.</summary>
    public static string SessionFolder(WatcherConfig cfg, WatcherIdentity identity, string localFallbackFolder, CaptureSnapshot snap)
    {
        var label = EventNormalizer.ResolveEmployeeId(cfg, identity.WindowsUsername, identity.ComputerName);
        var sub = Path.Combine(LocalFolderUploader.SafeSegment(label), "_sop_screenshots",
            LocalFolderUploader.SafeSegment(snap.Label) + "_" + snap.SessionId[..8]);
        try { return Path.Combine(ExportDestination.Resolve(WatcherPaths.ExportFolder(cfg)), sub); }
        catch { return Path.Combine(localFallbackFolder, "sop_screenshots", sub); }
    }
}
