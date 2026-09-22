using MppWatcher.Core.Configuration;
using MppWatcher.Core.Diagnostics;
using MppWatcher.Core.Events;
using MppWatcher.Core.Presentation;
using MppWatcher.Core.Storage;
using MppWatcher.Core.Runtime;

namespace MppWatcher.App;

/// <summary>
/// Live test viewer: shows events as the watcher writes them, e.g.
///   10:04:17  app_session_start  Google Chrome — "Keepa - Amazon Price Tracker"
/// It only READS the database; closing it does not affect the watcher.
/// </summary>
internal sealed class ViewerForm : Form
{
    private const int MaxRows = 5000;

    private readonly string _dbPath;
    private readonly ListView _list = new();
    private readonly TextBox _details = new();
    private readonly TextBox _filter = new();
    private readonly CheckBox _pause = new() { Text = "Pause", AutoSize = true };
    private readonly CheckBox _hideNoise = new() { Text = "Hide heartbeats && process events", AutoSize = true, Checked = false };
    private readonly CheckBox _autoScroll = new() { Text = "Auto-scroll", AutoSize = true, Checked = true };
    private readonly Label _status = new() { AutoSize = true, Padding = new Padding(0, 6, 0, 0) };
    private readonly System.Windows.Forms.Timer _timer = new() { Interval = 1000 };
    private readonly List<WatchEvent> _all = new();
    private SqliteEventStore? _store;
    private long _lastRowId;

    public ViewerForm(string configPath, string? dataFolderOverride)
    {
        var config = ConfigLoader.Load(configPath).Config;
        _dbPath = RuntimePaths.From(config, dataFolderOverride).DatabasePath;

        Text = "MPP Watcher – Live Event Viewer";
        Icon = AppIcon.Get();
        Width = 1200;
        Height = 760;
        StartPosition = FormStartPosition.CenterScreen;

        var toolbar = new FlowLayoutPanel { Dock = DockStyle.Top, Height = 36, Padding = new Padding(6, 4, 6, 0), WrapContents = false };
        toolbar.Controls.Add(new Label { Text = "Filter:", AutoSize = true, Padding = new Padding(0, 6, 0, 0) });
        _filter.Width = 260;
        _filter.PlaceholderText = "text, app, event type…";
        toolbar.Controls.Add(_filter);
        toolbar.Controls.Add(_hideNoise);
        toolbar.Controls.Add(_autoScroll);
        toolbar.Controls.Add(_pause);
        var clear = new Button { Text = "Clear view", AutoSize = true };
        clear.Click += (_, _) => { _all.Clear(); _list.Items.Clear(); };
        toolbar.Controls.Add(clear);
        toolbar.Controls.Add(_status);

        _list.Dock = DockStyle.Fill;
        _list.View = View.Details;
        _list.FullRowSelect = true;
        _list.HideSelection = false;
        _list.Font = new Font("Segoe UI", 9.5f);
        _list.Columns.Add("Time", 75);
        _list.Columns.Add("Event", 150);
        _list.Columns.Add("Application", 170);
        _list.Columns.Add("What happened", 760);
        _list.SelectedIndexChanged += (_, _) => ShowDetails();

        _details.Dock = DockStyle.Fill;
        _details.Multiline = true;
        _details.ReadOnly = true;
        _details.ScrollBars = ScrollBars.Both;
        _details.WordWrap = false;
        _details.Font = new Font("Consolas", 9.5f);

        var split = new SplitContainer { Dock = DockStyle.Fill, Orientation = Orientation.Horizontal, SplitterDistance = 470 };
        split.Panel1.Controls.Add(_list);
        split.Panel2.Controls.Add(_details);
        Controls.Add(split);
        Controls.Add(toolbar);

        _filter.TextChanged += (_, _) => Rebuild();
        _hideNoise.CheckedChanged += (_, _) => Rebuild();
        _timer.Tick += (_, _) => Poll();
        Load += (_, _) => { Poll(initial: true); _timer.Start(); };
        FormClosed += (_, _) => { _timer.Stop(); _store?.Dispose(); };
    }

    private void Poll(bool initial = false)
    {
        if (_pause.Checked) return;
        try
        {
            if (_store is null)
            {
                if (!File.Exists(_dbPath))
                {
                    _status.Text = $"Waiting for database: {_dbPath}";
                    return;
                }
                _store = new SqliteEventStore(_dbPath, "", readOnly: true);
            }
            var rows = initial ? _store.ReadLatest(500) : _store.ReadAfter(_lastRowId, 1000);
            if (rows.Count > 0)
            {
                _lastRowId = rows[^1].RowId;
                _list.BeginUpdate();
                foreach (var r in rows)
                {
                    _all.Add(r.Event);
                    if (IsShown(r.Event)) _list.Items.Add(ToItem(r.Event));
                }
                Trim();
                _list.EndUpdate();
                if (_autoScroll.Checked && _list.Items.Count > 0) _list.EnsureVisible(_list.Items.Count - 1);
            }
            var agentRunning = Mutex.TryOpenExisting(Program.AgentMutexName, out var m);
            m?.Dispose();
            _status.Text = $"{(agentRunning ? "Watcher running" : "Watcher NOT running")} · {_all.Count} events shown · {Path.GetFileName(_dbPath)}";
        }
        catch (Exception e)
        {
            _status.Text = "Read error: " + e.Message;
            _store?.Dispose();
            _store = null;
        }
    }

    private bool IsShown(WatchEvent e)
    {
        if (_hideNoise.Checked && e.EventType is EventTypes.WatcherHeartbeat or EventTypes.ProcessStarted or EventTypes.ProcessExited or EventTypes.ProcessInventory)
            return false;
        var f = _filter.Text.Trim();
        if (f.Length == 0) return true;
        return (e.EventType + " " + e.Application + " " + e.WindowTitle + " " + e.Domain + " " + EventSummaryFormatter.Summarize(e))
            .Contains(f, StringComparison.OrdinalIgnoreCase);
    }

    private static ListViewItem ToItem(WatchEvent e)
    {
        var item = new ListViewItem(new[] { EventSummaryFormatter.LocalTimeText(e), e.EventType, e.Application ?? "", EventSummaryFormatter.Summarize(e) })
        {
            Tag = e,
        };
        item.ForeColor = e.EventType switch
        {
            EventTypes.AppSessionStart => Color.FromArgb(0, 90, 170),
            EventTypes.IdleStart or EventTypes.IdleEnd => Color.DarkOrange,
            EventTypes.WorkstationLocked or EventTypes.WorkstationUnlocked or EventTypes.SystemSuspend or EventTypes.SystemResume => Color.Purple,
            EventTypes.CollectorStatus or EventTypes.ActivityGap => Color.Firebrick,
            EventTypes.WatcherHeartbeat or EventTypes.ProcessInventory or EventTypes.ProcessStarted or EventTypes.ProcessExited => Color.Gray,
            _ => SystemColors.WindowText,
        };
        if (e.Metadata["excluded"] is not null) item.BackColor = Color.FromArgb(245, 245, 245);
        return item;
    }

    private void Rebuild()
    {
        _list.BeginUpdate();
        _list.Items.Clear();
        foreach (var e in _all.Where(IsShown)) _list.Items.Add(ToItem(e));
        _list.EndUpdate();
    }

    private void Trim()
    {
        if (_all.Count > MaxRows) _all.RemoveRange(0, _all.Count - MaxRows);
        while (_list.Items.Count > MaxRows) _list.Items.RemoveAt(0);
    }

    private void ShowDetails()
    {
        if (_list.SelectedItems.Count == 0 || _list.SelectedItems[0].Tag is not WatchEvent e) return;
        _details.Text = EventJson.SerializeIndented(e).Replace("\n", Environment.NewLine);
    }
}
