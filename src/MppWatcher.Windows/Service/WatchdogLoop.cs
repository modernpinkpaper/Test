using System.Management;
using MppWatcher.Core.Configuration;
using MppWatcher.Core.Diagnostics;

namespace MppWatcher.Windows.Service;

/// <summary>
/// The watchdog's work: every 30 seconds, for each signed-in user with an active desktop, make sure
/// that user's MPP Watcher is running; if not, start it in their session. At most 5 restarts per
/// user per hour. Does nothing if the admin allows employees to exit the watcher.
/// </summary>
public sealed class WatchdogLoop
{
    private readonly string _exe;
    private readonly ConfigProvider _config;
    private readonly IDiagnosticLog _log;
    private readonly Dictionary<int, List<DateTime>> _restarts = new();

    public WatchdogLoop(string exe, ConfigProvider config, IDiagnosticLog log)
    {
        _exe = exe;
        _config = config;
        _log = log;
    }

    public static readonly TimeSpan Interval = TimeSpan.FromSeconds(30);

    public void RunOnce()
    {
        if (_config.Current.AllowUserExit) return; // employees may close it; do not fight them
        foreach (var session in SessionLauncher.ActiveUserSessions())
        {
            try
            {
                if (AgentRunningIn(session.SessionId)) continue;
                var list = _restarts.TryGetValue(session.SessionId, out var l) ? l : _restarts[session.SessionId] = new List<DateTime>();
                list.RemoveAll(t => DateTime.UtcNow - t > TimeSpan.FromHours(1));
                if (list.Count >= 5)
                {
                    _log.Warn("watchdog", $"Watcher for {session.Domain}\\{session.UserName} (session {session.SessionId}) keeps stopping; not restarting again this hour");
                    continue;
                }
                var pid = SessionLauncher.StartInSession(session.SessionId, _exe, "");
                list.Add(DateTime.UtcNow);
                _log.Info("watchdog", $"Started MPP Watcher for {session.Domain}\\{session.UserName} in session {session.SessionId} (pid {pid})");
            }
            catch (Exception e)
            {
                _log.Error("watchdog", $"Could not check/start the watcher in session {session.SessionId}", e);
            }
        }
    }

    /// <summary>The background watcher (no --viewer/--inspect/--service argument) is running in that session.</summary>
    private static bool AgentRunningIn(int sessionId)
    {
        using var searcher = new ManagementObjectSearcher($"SELECT CommandLine FROM Win32_Process WHERE Name = 'MPPWatcher.exe' AND SessionId = {sessionId}");
        foreach (var p in searcher.Get())
        {
            var cmd = p["CommandLine"]?.ToString() ?? "";
            if (!cmd.Contains("--viewer") && !cmd.Contains("--inspect") && !cmd.Contains("--service") && !cmd.Contains("--smoke-test") && !cmd.Contains("--stop"))
                return true;
        }
        return false;
    }
}
