using MppWatcher.Core.Configuration;
using MppWatcher.Core.Diagnostics;
using MppWatcher.Core.Events;

namespace MppWatcher.Core.Collectors;

/// <summary>Where collectors send events. Implementations must be thread-safe and must not block.</summary>
public interface IEventSink
{
    void Emit(WatchEvent e);
}

/// <summary>Everything a collector may use. Collectors never touch storage directly.</summary>
public sealed record CollectorContext(IEventSink Sink, ConfigProvider Config, IDiagnosticLog Log, IClock Clock);

/// <summary>
/// A source of activity events (foreground windows, processes, UI Automation, files, ...).
/// To add a new collector: implement this, register it in the app's collector list,
/// and give it an "enabled" switch in config. See docs/ARCHITECTURE.md.
/// </summary>
public interface ICollector
{
    /// <summary>Short stable name, written into every event's "collector" field.</summary>
    string Name { get; }
    string Version { get; }

    /// <summary>Start collecting. Should return quickly; do long work on timers/threads.</summary>
    void Start(CollectorContext context);

    /// <summary>Stop and flush. <paramref name="reason"/> is e.g. "watcher_stopped".</summary>
    void Stop(string reason);

    /// <summary>Optional extra numbers for the heartbeat event.</summary>
    IReadOnlyDictionary<string, object> GetStats() => new Dictionary<string, object>();
}

public static class CollectorExtensions
{
    /// <summary>Creates an event pre-filled with this collector's name and version.</summary>
    public static WatchEvent NewEvent(this ICollector collector, string eventType, DateTimeOffset timestamp) => new()
    {
        EventType = eventType,
        TimestampUtc = timestamp,
        Collector = collector.Name,
        CollectorVersion = collector.Version,
    };
}
