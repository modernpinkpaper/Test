using MppWatcher.Core.Configuration;
using MppWatcher.Core.Privacy;

namespace MppWatcher.Core.Processes;

/// <summary>One running process as seen by the operating system layer.</summary>
public sealed record ProcessInfo(
    int ProcessId,
    string Name,
    DateTimeOffset? StartTime = null,
    string? ExecutablePath = null,
    string? ApplicationName = null,
    bool HasVisibleWindow = false);

/// <summary>Supplies the current process list (Windows: processes in the user's own logon session).</summary>
public interface IProcessSource
{
    IReadOnlyList<ProcessInfo> Snapshot();
}

public abstract record ProcessChange
{
    public sealed record Started(ProcessInfo Process, int RunningInstances) : ProcessChange;
    public sealed record Exited(ProcessInfo Process, TimeSpan? Lifetime, DateTimeOffset FirstSeen) : ProcessChange;
}

/// <summary>
/// Compares successive process lists and reports starts and exits of interesting processes.
/// System noise is ignored. With collapse on, a browser's 30 helper processes count as one app:
/// "started" when the first appears, "exited" when the last one is gone.
/// </summary>
public sealed class ProcessTracker
{
    private readonly Func<ProcessCollectorConfig> _config;
    private readonly Dictionary<string, (ProcessInfo Info, DateTimeOffset FirstSeen)> _known = new();
    private bool _hasBaseline;

    public ProcessTracker(Func<ProcessCollectorConfig> config) => _config = config;

    /// <summary>
    /// First call records a baseline and returns the interesting processes already running
    /// (for the process_inventory event) with no changes. Later calls return changes.
    /// </summary>
    public (IReadOnlyList<ProcessInfo> Inventory, IReadOnlyList<ProcessChange> Changes) Update(IEnumerable<ProcessInfo> snapshot, DateTimeOffset now)
    {
        var cfg = _config();
        var current = new Dictionary<string, ProcessInfo>();
        foreach (var p in snapshot)
        {
            if (IsIgnored(p.Name, cfg)) continue;
            current[Key(p)] = p;
        }

        if (!_hasBaseline)
        {
            _hasBaseline = true;
            foreach (var (k, p) in current) _known[k] = (p, now);
            return (current.Values.OrderBy(p => p.Name, StringComparer.OrdinalIgnoreCase).ToList(), Array.Empty<ProcessChange>());
        }

        var changes = new List<ProcessChange>();
        var countsBefore = CountByName(_known.Values.Select(v => v.Info));
        var countsAfter = CountByName(current.Values);

        foreach (var (k, v) in _known.ToList())
        {
            if (current.ContainsKey(k)) continue;
            _known.Remove(k);
            if (cfg.CollapseMultiInstance && countsAfter.GetValueOrDefault(v.Info.Name) > 0) continue;
            var start = v.Info.StartTime ?? v.FirstSeen;
            changes.Add(new ProcessChange.Exited(v.Info, now - start, v.FirstSeen));
        }

        var reportedStart = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var (k, p) in current)
        {
            if (_known.ContainsKey(k)) continue;
            _known[k] = (p, now);
            if (cfg.CollapseMultiInstance)
            {
                if (countsBefore.GetValueOrDefault(p.Name) > 0 || !reportedStart.Add(p.Name)) continue;
            }
            changes.Add(new ProcessChange.Started(p, countsAfter.GetValueOrDefault(p.Name)));
        }
        return (Array.Empty<ProcessInfo>(), changes);
    }

    public int KnownCount => _known.Count;

    private static bool IsIgnored(string name, ProcessCollectorConfig cfg) =>
        WildcardMatcher.MatchesAny(name.EndsWith(".exe", StringComparison.OrdinalIgnoreCase) ? name[..^4] : name, cfg.IgnoreProcesses);

    private static string Key(ProcessInfo p) => p.ProcessId + ":" + (p.StartTime?.UtcTicks.ToString() ?? p.Name);

    private static Dictionary<string, int> CountByName(IEnumerable<ProcessInfo> list) =>
        list.GroupBy(p => p.Name, StringComparer.OrdinalIgnoreCase).ToDictionary(g => g.Key, g => g.Count(), StringComparer.OrdinalIgnoreCase);
}
