using MppWatcher.Core.Collectors;
using MppWatcher.Core.Configuration;
using MppWatcher.Core.Diagnostics;
using MppWatcher.Core.Pipeline;
using MppWatcher.Core.Processes;
using MppWatcher.Core.Runtime;
using MppWatcher.Windows;

namespace MppWatcher.App;

/// <summary>
/// The list of collectors. To add a collector (UI Automation, files, print jobs, ...):
/// create it, give it an "enabled" switch in config, and add it here.
/// </summary>
internal static class WatcherFactory
{
    public static WatcherRuntime Create(ConfigProvider config, string? dataFolderOverride, IDiagnosticLog log)
    {
        var identity = WatcherIdentity.FromEnvironment();
        var paths = RuntimePaths.From(config.Current, dataFolderOverride);
        return new WatcherRuntime(config, log, SystemClock.Instance, identity, paths, Collectors);
    }

    private static IEnumerable<ICollector> Collectors(RuntimeServices s)
    {
        var c = s.Config.Current.Collectors;
        // Activity first: it is stopped last, so its final session closes after the others stop.
        if (c.Activity.Enabled) yield return new WindowsActivityCollector(s.Identity.WatcherRunId, s.Paths.CheckpointPath);
        if (c.Process.Enabled) yield return new ProcessCollector(new WindowsProcessSource());
        if (c.UiAutomation.Enabled) yield return new MppWatcher.Windows.Ui.UiAutomationCollector(s.Activity);
        if (c.Browser.Enabled) yield return new MppWatcher.Windows.Ui.BrowserContextCollector(s.Activity);
        if (c.Files.Enabled) yield return new MppWatcher.Core.Files.FileActivityCollector(s.Activity);
        if (c.Files.Enabled && c.Files.TrackOpenedFiles) yield return new MppWatcher.Windows.Files.RecentFilesCollector(s.Activity);
        if (c.Print.Enabled) yield return new MppWatcher.Windows.Files.PrintJobCollector(s.Activity);
    }
}
