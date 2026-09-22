using System.Diagnostics;
using Microsoft.Win32;
using MppWatcher.Core.Configuration;
using MppWatcher.Core.Diagnostics;
using MppWatcher.Core.Events;
using MppWatcher.Core.Runtime;

namespace MppWatcher.App;

/// <summary>
/// Normal mode: no main window, runs the watcher and (by default) shows a tray icon so the
/// employee can see that activity logging is on. Exit is only offered if the admin allows it.
/// </summary>
internal sealed class AgentContext : ApplicationContext
{
    private readonly ConfigProvider _config;
    private readonly IDiagnosticLog _log;
    private readonly WatcherRuntime _runtime;
    private readonly NotifyIcon? _tray;
    private readonly EventWaitHandle _stopSignal;
    private readonly RegisteredWaitHandle _stopWait;
    private readonly SynchronizationContext _ui;
    private int _stopping;

    public AgentContext(string configPath, string? dataFolderOverride, IDiagnosticLog log)
    {
        _log = log;
        _config = new ConfigProvider(configPath, log);
        _config.WatchForChanges();
        _runtime = WatcherFactory.Create(_config, dataFolderOverride, log);
        _runtime.Start(new Dictionary<string, object?> { ["mode"] = "agent" });

        // Windows is signing out / shutting down: flush quickly (Windows allows only a few seconds).
        SystemEvents.SessionEnded += OnSessionEnded;

        if (_config.Current.ShowTrayIcon) _tray = CreateTray();

        // "MPPWatcher.exe --stop" signals this event; stop cleanly on the UI thread.
        _ui = SynchronizationContext.Current ?? new WindowsFormsSynchronizationContext();
        _stopSignal = new EventWaitHandle(false, EventResetMode.AutoReset, Program.StopEventName);
        _stopWait = ThreadPool.RegisterWaitForSingleObject(_stopSignal,
            (_, _) => _ui.Post(_ => Shutdown("stop_requested"), null), null, Timeout.Infinite, executeOnlyOnce: true);
    }

    private NotifyIcon CreateTray()
    {
        var menu = new ContextMenuStrip();
        menu.Items.Add("Open live viewer", null, (_, _) => StartSelf("--viewer"));
        menu.Items.Add("Status…", null, (_, _) => ShowStatus());
        menu.Items.Add("Export logs now", null, async (_, _) =>
        {
            var r = await _runtime.ExportNowAsync();
            _tray?.ShowBalloonTip(3000, "MPP Watcher", r.Error is null ? $"Exported {r.Exported} events." : $"Export problem: {r.Error}", ToolTipIcon.Info);
        });
        menu.Items.Add(new ToolStripSeparator());
        menu.Items.Add("Open data folder", null, (_, _) => OpenFolder(_runtime.Paths.DataFolder));
        menu.Items.Add("Open diagnostic logs", null, (_, _) => OpenFolder(_runtime.Paths.LogFolder));
        menu.Items.Add("Open export folder", null, (_, _) => OpenFolder(_runtime.Paths.ExportFolder));
        if (_config.Current.AllowUserExit)
        {
            menu.Items.Add(new ToolStripSeparator());
            menu.Items.Add("Exit MPP Watcher", null, (_, _) => Shutdown("user_exit"));
        }

        var tray = new NotifyIcon
        {
            Icon = AppIcon.Get(),
            Text = $"MPP Watcher – activity logging is on ({_config.Current.CompanyName})",
            ContextMenuStrip = menu,
            Visible = true,
        };
        tray.DoubleClick += (_, _) => StartSelf("--viewer");
        return tray;
    }

    private void ShowStatus()
    {
        var s = _runtime.GetStatus();
        var collectors = string.Join(Environment.NewLine, (s["collectors"]?.AsArray() ?? new()).Select(c =>
            $"   • {c?["name"]}: {c?["state"]}"));
        MessageBox.Show(
            $"""
            MPP Watcher {MppWatcher.Core.Collectors.WatcherVersion.Current}
            Employee: {Core.Pipeline.EventNormalizer.ResolveEmployeeId(_config.Current, _runtime.Identity.WindowsUsername)}
            Windows user: {_runtime.Identity.WindowsUsername}

            Running for: {TimeFormat.Human(TimeSpan.FromSeconds(s["uptime_seconds"]!.GetValue<double>()))}
            Events written: {s["events_written"]}
            Waiting for export: {s["events_pending_upload"]}
            Memory: {s["memory_mb"]} MB

            Collectors:
            {collectors}

            Config: {_config.Path}
            Database: {_runtime.Paths.DatabasePath}
            """,
            "MPP Watcher status", MessageBoxButtons.OK, MessageBoxIcon.Information);
    }

    private void OnSessionEnded(object? sender, SessionEndedEventArgs e) =>
        StopRuntime(e.Reason == Microsoft.Win32.SessionEndReasons.SystemShutdown ? "system_shutdown" : "logoff");

    private void Shutdown(string reason)
    {
        StopRuntime(reason);
        ExitThread();
    }

    private void StopRuntime(string reason)
    {
        if (Interlocked.Exchange(ref _stopping, 1) == 1) return;
        try
        {
            _runtime.StopAsync(reason).Wait(TimeSpan.FromSeconds(8));
        }
        catch (Exception e)
        {
            _log.Error("app", "Error while stopping", e);
        }
    }

    private static void StartSelf(string args)
    {
        try
        {
            Process.Start(new ProcessStartInfo(Environment.ProcessPath!, args) { UseShellExecute = false });
        }
        catch (Exception e)
        {
            MessageBox.Show("Could not open: " + e.Message, "MPP Watcher");
        }
    }

    private static void OpenFolder(string path)
    {
        try
        {
            Directory.CreateDirectory(path);
            Process.Start(new ProcessStartInfo("explorer.exe", $"\"{path}\"") { UseShellExecute = true });
        }
        catch (Exception e)
        {
            MessageBox.Show("Could not open folder: " + e.Message, "MPP Watcher");
        }
    }

    protected override void Dispose(bool disposing)
    {
        if (disposing)
        {
            SystemEvents.SessionEnded -= OnSessionEnded;
            _stopWait.Unregister(null);
            _stopSignal.Dispose();
            StopRuntime("watcher_stopped");
            if (_tray is not null)
            {
                _tray.Visible = false;
                _tray.Dispose();
            }
            _config.Dispose();
        }
        base.Dispose(disposing);
    }
}
