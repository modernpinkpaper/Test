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
    private readonly EventWaitHandle _exportSignal;
    private readonly EventWaitHandle _exportDone;
    private readonly RegisteredWaitHandle _exportWait;
    private readonly EventWaitHandle _captureSignal;
    private readonly RegisteredWaitHandle _captureWait;
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

        // "MTLog.exe --stop" signals this event; stop cleanly on the UI thread.
        _ui = SynchronizationContext.Current ?? new WindowsFormsSynchronizationContext();
        _stopSignal = new EventWaitHandle(false, EventResetMode.AutoReset, Program.StopEventName);
        _stopWait = ThreadPool.RegisterWaitForSingleObject(_stopSignal,
            (_, _) => _ui.Post(_ => Shutdown("stop_requested"), null), null, Timeout.Infinite, executeOnlyOnce: true);

        // "MTLog.exe --export-now": export, then tell the caller it is done.
        _exportSignal = new EventWaitHandle(false, EventResetMode.AutoReset, Program.ExportNowEventName);
        _exportDone = new EventWaitHandle(false, EventResetMode.AutoReset, Program.ExportDoneEventName);
        _exportWait = ThreadPool.RegisterWaitForSingleObject(_exportSignal, (_, _) => ExportOnRequest(), null, Timeout.Infinite, executeOnlyOnce: false);

        // "MTLog.exe --capture-*": read the command file and apply on the UI thread.
        _captureSignal = new EventWaitHandle(false, EventResetMode.AutoReset, Program.CaptureEventName);
        _captureWait = ThreadPool.RegisterWaitForSingleObject(_captureSignal, (_, _) => _ui.Post(_ => ApplyCaptureCommand(), null), null, Timeout.Infinite, executeOnlyOnce: false);
    }

    private void ApplyCaptureCommand()
    {
        try
        {
            var file = Path.Combine(_runtime.Paths.DataFolder, "capture-command.json");
            if (!File.Exists(file)) return;
            using var doc = System.Text.Json.JsonDocument.Parse(File.ReadAllText(file));
            var action = doc.RootElement.TryGetProperty("action", out var a) ? a.GetString() : null;
            var label = doc.RootElement.TryGetProperty("label", out var l) ? l.GetString() : null;
            switch (action)
            {
                case "start-sop": _runtime.StartCapture(MppWatcher.Core.Capture.CaptureMode.Sop, label ?? "SOP"); break;
                case "start-decision": _runtime.StartCapture(MppWatcher.Core.Capture.CaptureMode.Decision, label ?? "Decision"); break;
                case "stop": _runtime.StopCapture(); break;
                case "pause": _runtime.PauseCapture(); break;
                case "resume": _runtime.ResumeCapture(); break;
            }
            RefreshRecordMenu();
        }
        catch (Exception e) { _log.Error("capture", "Could not apply capture command", e); }
    }

    private void ExportOnRequest()
    {
        try
        {
            var r = _runtime.ExportNowAsync().GetAwaiter().GetResult();
            _log.Info("export", r.Error is null ? $"Export requested: {r.Exported} events exported" : $"Export requested: problem: {r.Error}");
        }
        catch (Exception e)
        {
            _log.Error("export", "Requested export failed", e);
        }
        finally
        {
            try { _exportDone.Set(); } catch (ObjectDisposedException) { }
        }
    }

    private NotifyIcon CreateTray()
    {
        var menu = new ContextMenuStrip();
        menu.Items.Add("Open live viewer", null, (_, _) => StartSelf("--viewer"));
        menu.Items.Add("Status…", null, (_, _) => ShowStatus());
        var exportItem = new ToolStripMenuItem("Export logs now");
        exportItem.Click += async (_, _) =>
        {
            // No pop-up bubble: the result is shown quietly in the menu item's text instead.
            exportItem.Text = "Exporting…";
            var r = await _runtime.ExportNowAsync();
            exportItem.Text = r.Error is null ? $"Export logs now (last: {r.Exported} sent)" : "Export logs now (last: problem)";
        };
        menu.Items.Add(exportItem);
        menu.Items.Add(new ToolStripSeparator());
        BuildRecordMenu(menu);
        menu.Items.Add(new ToolStripSeparator());
        menu.Items.Add("Open data folder", null, (_, _) => OpenFolder(_runtime.Paths.DataFolder));
        menu.Items.Add("Open diagnostic logs", null, (_, _) => OpenFolder(_runtime.Paths.LogFolder));
        menu.Items.Add("Open export folder", null, (_, _) =>
        {
            try
            {
                OpenFolder(_runtime.ResolveExportFolder());
            }
            catch (Exception e)
            {
                MessageBox.Show(e.Message, "MT Log");
            }
        });
        if (_config.Current.AllowUserExit)
        {
            menu.Items.Add(new ToolStripSeparator());
            menu.Items.Add("Exit MT Log", null, (_, _) => Shutdown("user_exit"));
        }

        var tray = new NotifyIcon
        {
            Icon = AppIcon.Get(),
            Text = $"MT Log – activity logging is on ({_config.Current.CompanyName})",
            ContextMenuStrip = menu,
            Visible = true,
        };
        tray.DoubleClick += (_, _) => StartSelf("--viewer");
        return tray;
    }

    private ToolStripMenuItem? _recordItem, _pauseItem, _stopItem;

    /// <summary>Tray items to record a task for an SOP or an ads decision, with pause and stop.</summary>
    private void BuildRecordMenu(ContextMenuStrip menu)
    {
        _recordItem = new ToolStripMenuItem("Record a task…");
        _recordItem.DropDownItems.Add("For an SOP (with screenshots)", null, (_, _) => StartRecording(MppWatcher.Core.Capture.CaptureMode.Sop));
        _recordItem.DropDownItems.Add("For an ads decision", null, (_, _) => StartRecording(MppWatcher.Core.Capture.CaptureMode.Decision));
        menu.Items.Add(_recordItem);

        _pauseItem = new ToolStripMenuItem("Pause recording", null, (_, _) => TogglePause()) { Visible = false };
        menu.Items.Add(_pauseItem);
        _stopItem = new ToolStripMenuItem("Stop recording", null, (_, _) => StopRecording()) { Visible = false };
        menu.Items.Add(_stopItem);
        RefreshRecordMenu();
    }

    private void StartRecording(MppWatcher.Core.Capture.CaptureMode mode)
    {
        var what = mode == MppWatcher.Core.Capture.CaptureMode.Sop ? "SOP" : "ads decision";
        var label = Prompt($"Name this {what} recording (e.g. \"Create RA file for a KS order\"):", "MT Log — Record a task");
        if (label is null) return; // cancelled
        _runtime.StartCapture(mode, label);
        RefreshRecordMenu();
    }

    private void TogglePause()
    {
        var s = _runtime.Capture.Current;
        if (!s.Active) return;
        if (s.Paused) _runtime.ResumeCapture(); else _runtime.PauseCapture();
        RefreshRecordMenu();
    }

    private void StopRecording()
    {
        _runtime.StopCapture();
        RefreshRecordMenu();
    }

    private void RefreshRecordMenu()
    {
        var s = _runtime.Capture.Current;
        if (_recordItem is not null) _recordItem.Visible = !s.Active;
        if (_pauseItem is not null)
        {
            _pauseItem.Visible = s.Active;
            _pauseItem.Text = s.Paused ? $"Resume recording: {s.Label}" : $"Pause recording: {s.Label}";
        }
        if (_stopItem is not null)
        {
            _stopItem.Visible = s.Active;
            _stopItem.Text = $"Stop recording: {s.Label}";
        }
    }

    /// <summary>A small one-line text prompt (WinForms has no built-in InputBox). Returns null if cancelled.</summary>
    private static string? Prompt(string message, string title)
    {
        using var form = new Form { Text = title, FormBorderStyle = FormBorderStyle.FixedDialog, StartPosition = FormStartPosition.CenterScreen, Width = 460, Height = 170, MinimizeBox = false, MaximizeBox = false, TopMost = true };
        var lbl = new Label { Left = 12, Top = 12, Width = 430, Height = 40, Text = message };
        var box = new TextBox { Left = 12, Top = 58, Width = 430 };
        var ok = new Button { Text = "Start", Left = 286, Top = 92, Width = 75, DialogResult = DialogResult.OK };
        var cancel = new Button { Text = "Cancel", Left = 367, Top = 92, Width = 75, DialogResult = DialogResult.Cancel };
        form.Controls.Add(lbl); form.Controls.Add(box); form.Controls.Add(ok); form.Controls.Add(cancel);
        form.AcceptButton = ok; form.CancelButton = cancel;
        return form.ShowDialog() == DialogResult.OK && box.Text.Trim().Length > 0 ? box.Text.Trim() : null;
    }

    private void ShowStatus()
    {
        var s = _runtime.GetStatus();
        var collectors = string.Join(Environment.NewLine, (s["collectors"]?.AsArray() ?? new()).Select(c =>
            $"   • {c?["name"]}: {c?["state"]}"));
        MessageBox.Show(
            $"""
            MT Log {MppWatcher.Core.Collectors.WatcherVersion.Current}
            Employee: {Core.Pipeline.EventNormalizer.ResolveEmployeeId(_config.Current, _runtime.Identity.WindowsUsername, _runtime.Identity.ComputerName)}
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
            "MT Log status", MessageBoxButtons.OK, MessageBoxIcon.Information);
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
            MessageBox.Show("Could not open: " + e.Message, "MT Log");
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
            MessageBox.Show("Could not open folder: " + e.Message, "MT Log");
        }
    }

    protected override void Dispose(bool disposing)
    {
        if (disposing)
        {
            SystemEvents.SessionEnded -= OnSessionEnded;
            _stopWait.Unregister(null);
            _stopSignal.Dispose();
            _exportWait.Unregister(null);
            _exportSignal.Dispose();
            _exportDone.Dispose();
            _captureWait.Unregister(null);
            _captureSignal.Dispose();
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
