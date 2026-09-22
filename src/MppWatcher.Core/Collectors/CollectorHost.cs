using MppWatcher.Core.Configuration;
using MppWatcher.Core.Diagnostics;
using MppWatcher.Core.Events;

namespace MppWatcher.Core.Collectors;

public enum CollectorState { NotStarted, Running, Failed, Stopped }

/// <summary>
/// Starts and stops collectors and keeps them apart: an exception in one collector is
/// logged and reported as a collector_status event, and the others keep running.
/// A collector can report a runtime failure through <see cref="ReportFailure"/>; the host
/// then restarts it with a growing delay (up to <see cref="MaxRestarts"/> times per hour).
/// </summary>
public sealed class CollectorHost
{
    public const string HostName = "watcher";
    public const int MaxRestarts = 5;

    private readonly List<Entry> _entries = new();
    private readonly CollectorContext _context;
    private readonly object _gate = new();
    private bool _stopping;

    public CollectorHost(CollectorContext context) => _context = context with { ReportFailure = ReportFailure };

    public void Add(ICollector collector) => _entries.Add(new Entry(collector));

    public IReadOnlyList<(string Name, CollectorState State, int Restarts)> Status
    {
        get { lock (_gate) return _entries.Select(e => (e.Collector.Name, e.State, e.RestartTimes.Count)).ToList(); }
    }

    public IEnumerable<ICollector> Collectors => _entries.Select(e => e.Collector);

    public void StartAll()
    {
        foreach (var entry in _entries) StartOne(entry);
    }

    public void StopAll(string reason)
    {
        lock (_gate) _stopping = true;
        // Stop in reverse order so the activity collector (added first) closes its session last.
        foreach (var entry in Enumerable.Reverse(_entries))
        {
            if (entry.State != CollectorState.Running) continue;
            try
            {
                entry.Collector.Stop(reason);
                entry.State = CollectorState.Stopped;
            }
            catch (Exception e)
            {
                _context.Log.Error(entry.Collector.Name, "Collector failed while stopping", e);
            }
        }
    }

    /// <summary>
    /// Called by a collector (from any thread) when it hits an error it cannot recover from itself.
    /// </summary>
    public void ReportFailure(ICollector collector, Exception error)
    {
        var entry = _entries.FirstOrDefault(e => ReferenceEquals(e.Collector, collector));
        if (entry is null) return;
        lock (_gate)
        {
            if (_stopping || entry.State != CollectorState.Running) return;
            entry.State = CollectorState.Failed;
        }
        _context.Log.Error(collector.Name, "Collector failed at runtime", error);
        EmitStatus(collector, "failed", error.Message);
        try { collector.Stop("collector_failed"); } catch (Exception e) { _context.Log.Warn(collector.Name, "Stop after failure also failed", e); }
        ScheduleRestart(entry);
    }

    private void StartOne(Entry entry)
    {
        var c = entry.Collector;
        try
        {
            c.Start(_context);
            lock (_gate) entry.State = CollectorState.Running;
            _context.Log.Info(c.Name, $"Collector started (v{c.Version})");
            EmitStatus(c, "running", null);
        }
        catch (Exception e)
        {
            lock (_gate) entry.State = CollectorState.Failed;
            _context.Log.Error(c.Name, "Collector failed to start", e);
            EmitStatus(c, "failed", e.Message);
            ScheduleRestart(entry);
        }
    }

    private void ScheduleRestart(Entry entry)
    {
        var now = _context.Clock.Now;
        lock (_gate)
        {
            entry.RestartTimes.RemoveAll(t => now - t > TimeSpan.FromHours(1));
            if (_stopping) return;
            if (entry.RestartTimes.Count >= MaxRestarts)
            {
                _context.Log.Error(entry.Collector.Name, $"Collector failed {MaxRestarts} times in an hour; leaving it off until the watcher restarts");
                EmitStatus(entry.Collector, "disabled_after_repeated_failures", null);
                return;
            }
            entry.RestartTimes.Add(now);
        }
        var delay = TimeSpan.FromSeconds(Math.Min(300, 5 * Math.Pow(2, entry.RestartTimes.Count - 1)));
        _ = Task.Delay(delay).ContinueWith(_ =>
        {
            lock (_gate) if (_stopping) return;
            _context.Log.Info(entry.Collector.Name, "Restarting collector");
            StartOne(entry);
        }, TaskScheduler.Default);
    }

    private void EmitStatus(ICollector c, string status, string? error)
    {
        var e = new WatchEvent
        {
            EventType = EventTypes.CollectorStatus,
            TimestampUtc = _context.Clock.Now,
            Collector = HostName,
            CollectorVersion = WatcherVersion.Current,
        };
        e.Metadata["collector_name"] = c.Name;
        e.Metadata["collector_version"] = c.Version;
        e.Metadata["status"] = status;
        if (error is not null) e.Metadata["error"] = error;
        _context.Sink.Emit(e);
    }

    private sealed class Entry
    {
        public Entry(ICollector c) => Collector = c;
        public ICollector Collector { get; }
        public CollectorState State { get; set; } = CollectorState.NotStarted;
        public List<DateTimeOffset> RestartTimes { get; } = new();
    }
}

public static class WatcherVersion
{
    public static string Current { get; } =
        typeof(WatcherVersion).Assembly.GetName().Version?.ToString(3) ?? "0.0.0";
}
