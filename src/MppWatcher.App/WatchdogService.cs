using System.ServiceProcess;
using MppWatcher.Core.Configuration;
using MppWatcher.Core.Diagnostics;
using MppWatcher.Windows.Service;

namespace MppWatcher.App;

/// <summary>
/// "MPP Watcher (watchdog)" Windows service. It records nothing itself: it only makes sure every
/// signed-in user's watcher is running, and restarts it in their session if it stopped.
/// Logs to %ProgramData%\MPP Watcher\logs\.
/// </summary>
internal sealed class WatchdogService : ServiceBase
{
    public const string Name = "MPPWatcherService";

    private readonly string _configPath;
    private ConfigProvider? _config;
    private FileDiagnosticLog? _log;
    private System.Threading.Timer? _timer;
    private int _running;

    public WatchdogService(string configPath)
    {
        _configPath = configPath;
        ServiceName = Name;
        CanStop = true;
    }

    protected override void OnStart(string[] args)
    {
        var logFolder = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData), WatcherPaths.ProductFolderName, "logs");
        _log = new FileDiagnosticLog(logFolder, () => false);
        _config = new ConfigProvider(_configPath, _log);
        _config.WatchForChanges();
        var loop = new WatchdogLoop(Environment.ProcessPath!, _config, _log);
        _log.Info("watchdog", "Watchdog service started");
        _timer = new System.Threading.Timer(_ =>
        {
            if (Interlocked.Exchange(ref _running, 1) == 1) return;
            try { loop.RunOnce(); }
            catch (Exception e) { _log.Error("watchdog", "Check failed", e); }
            finally { Interlocked.Exchange(ref _running, 0); }
        }, null, TimeSpan.FromSeconds(10), WatchdogLoop.Interval);
    }

    protected override void OnStop()
    {
        _timer?.Dispose();
        _config?.Dispose();
        _log?.Info("watchdog", "Watchdog service stopped");
    }
}
