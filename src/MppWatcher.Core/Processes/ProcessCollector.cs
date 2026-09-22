using System.Text.Json.Nodes;
using MppWatcher.Core.Collectors;
using MppWatcher.Core.Diagnostics;
using MppWatcher.Core.Events;

namespace MppWatcher.Core.Processes;

/// <summary>
/// Background process activity: which programs (including scripts like python.exe or node.exe)
/// start and stop, and how long they ran. Command lines are NOT recorded (they can contain secrets).
/// </summary>
public sealed class ProcessCollector : ICollector
{
    private readonly IProcessSource _source;
    private CollectorContext? _ctx;
    private ProcessTracker? _tracker;
    private Timer? _timer;
    private int _scanning;
    private long _scans, _started, _exited;

    public ProcessCollector(IProcessSource source) => _source = source;

    public string Name => "process";
    public string Version => "1.0.0";

    public void Start(CollectorContext context)
    {
        _ctx = context;
        _tracker = new ProcessTracker(() => context.Config.Current.Collectors.Process);
        Scan(); // baseline + inventory now, so failures surface at start
        var interval = TimeSpan.FromSeconds(context.Config.Current.Collectors.Process.ScanIntervalSeconds);
        _timer = new Timer(_ => Scan(), null, interval, interval);
    }

    public void Stop(string reason)
    {
        _timer?.Dispose();
        _timer = null;
    }

    public IReadOnlyDictionary<string, object> GetStats() => new Dictionary<string, object>
    {
        ["scans"] = _scans, ["starts_logged"] = _started, ["exits_logged"] = _exited, ["tracked_processes"] = _tracker?.KnownCount ?? 0,
    };

    internal void Scan()
    {
        if (_ctx is null || _tracker is null) return;
        if (Interlocked.Exchange(ref _scanning, 1) == 1) return;
        try
        {
            var now = _ctx.Clock.Now;
            var (inventory, changes) = _tracker.Update(_source.Snapshot(), now);
            _scans++;
            if (inventory.Count > 0)
            {
                var e = this.NewEvent(EventTypes.ProcessInventory, now);
                var apps = new JsonArray();
                foreach (var g in inventory.GroupBy(p => p.Name, StringComparer.OrdinalIgnoreCase).OrderBy(g => g.Key))
                {
                    apps.Add(new JsonObject
                    {
                        ["process_name"] = g.Key,
                        ["application"] = g.First().ApplicationName,
                        ["instances"] = g.Count(),
                        ["has_window"] = g.Any(p => p.HasVisibleWindow),
                    });
                }
                e.Metadata["processes"] = apps;
                e.Metadata["foreground"] = false;
                _ctx.Sink.Emit(e);
            }
            foreach (var change in changes) _ctx.Sink.Emit(ToEvent(change, now));
        }
        catch (Exception ex)
        {
            _ctx.Log.Warn(Name, "Process scan failed; will retry next interval", ex);
        }
        finally
        {
            Interlocked.Exchange(ref _scanning, 0);
        }
    }

    private WatchEvent ToEvent(ProcessChange change, DateTimeOffset now)
    {
        switch (change)
        {
            case ProcessChange.Started s:
            {
                _started++;
                var e = this.NewEvent(EventTypes.ProcessStarted, s.Process.StartTime ?? now);
                Fill(e, s.Process);
                e.Metadata["running_instances"] = s.RunningInstances;
                if (s.Process.StartTime is null) e.Metadata["start_time_is_approximate"] = true;
                return e;
            }
            case ProcessChange.Exited x:
            {
                _exited++;
                var e = this.NewEvent(EventTypes.ProcessExited, now);
                Fill(e, x.Process);
                if (x.Lifetime is { } life) e.Metadata["run_seconds"] = TimeFormat.Seconds(life);
                e.Metadata["exit_time_is_approximate"] = true; // detected at the next scan
                return e;
            }
            default:
                throw new InvalidOperationException("Unknown process change");
        }
    }

    private static void Fill(WatchEvent e, ProcessInfo p)
    {
        e.ProcessName = p.Name;
        e.ProcessId = p.ProcessId;
        e.Application = string.IsNullOrWhiteSpace(p.ApplicationName) ? p.Name : p.ApplicationName;
        e.Metadata["foreground"] = false;
        e.Metadata["has_window"] = p.HasVisibleWindow;
        if (p.ExecutablePath is not null) e.Metadata["executable_path"] = p.ExecutablePath;
        if (p.StartTime is { } st) e.Metadata["process_start"] = TimeFormat.Iso(st);
    }
}
