using System.Text.Json;
using System.Text.Json.Serialization;
using MppWatcher.Core.Events;

namespace MppWatcher.Assistant;

/// <summary>A recurring habit: after <see cref="Trigger"/> the person usually does <see cref="Then"/>.</summary>
public sealed class LearnedPattern
{
    [JsonPropertyName("trigger")] public string Trigger { get; set; } = "";
    [JsonPropertyName("then")] public string Then { get; set; } = "";
    [JsonPropertyName("count")] public int Count { get; set; }
    [JsonPropertyName("last_seen_utc")] public DateTimeOffset LastSeenUtc { get; set; } = DateTimeOffset.UtcNow;
}

/// <summary>
/// What the assistant has LEARNED over time: recurring habits (A usually followed by B) to suggest
/// proactively, and a "don't suggest this again" list built from what the person dismissed / marked
/// not helpful. Persisted as its own small file and fed to the brain each tick.
/// </summary>
public sealed class LearnedMemory
{
    [JsonPropertyName("patterns")] public List<LearnedPattern> Patterns { get; set; } = new();
    [JsonPropertyName("suppressed")] public List<string> Suppressed { get; set; } = new();

    public const int MaxSuppressed = 200;

    public static LearnedMemory Load(string path)
    {
        try
        {
            if (File.Exists(path))
                return JsonSerializer.Deserialize<LearnedMemory>(File.ReadAllText(path), AssistantJson.Options) ?? new LearnedMemory();
        }
        catch { }
        return new LearnedMemory();
    }

    public void Save(string path)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(path))!);
        File.WriteAllText(path, JsonSerializer.Serialize(this, AssistantJson.Indented));
    }

    /// <summary>Record/refresh a habit's count (recomputed from full history each learn pass).</summary>
    public void Reinforce(string trigger, string then, int count, DateTimeOffset nowUtc)
    {
        var p = Patterns.FirstOrDefault(x => x.Trigger == trigger && x.Then == then);
        if (p is null) { p = new LearnedPattern { Trigger = trigger, Then = then }; Patterns.Add(p); }
        p.Count = count;
        p.LastSeenUtc = nowUtc;
    }

    public void Suppress(string signature)
    {
        var s = (signature ?? "").Trim().ToLowerInvariant();
        if (s.Length == 0 || Suppressed.Contains(s)) return;
        Suppressed.Add(s);
        if (Suppressed.Count > MaxSuppressed) Suppressed.RemoveRange(0, Suppressed.Count - MaxSuppressed);
    }

    public bool IsSuppressed(string signature) => Suppressed.Contains((signature ?? "").Trim().ToLowerInvariant());
}

/// <summary>Finds recurring "A then B" transitions in a time-ordered sequence of place labels. Pure/tested.</summary>
public static class HabitMiner
{
    public static List<(string A, string B, int Count)> Mine(IEnumerable<string> orderedLabels, int minCount = 3)
    {
        // Collapse runs of the same place so "A A A B" counts as one A -> B.
        var labels = new List<string>();
        foreach (var l in orderedLabels)
        {
            if (string.IsNullOrWhiteSpace(l)) continue;
            if (labels.Count == 0 || labels[^1] != l) labels.Add(l);
        }
        var counts = new Dictionary<string, int>(StringComparer.Ordinal);
        for (var i = 0; i + 1 < labels.Count; i++)
        {
            if (labels[i] == labels[i + 1]) continue;
            var key = labels[i] + "\n" + labels[i + 1];
            counts[key] = counts.GetValueOrDefault(key) + 1;
        }
        var result = new List<(string, string, int)>();
        foreach (var kv in counts)
        {
            if (kv.Value < minCount) continue;
            var parts = kv.Key.Split('\n', 2);
            result.Add((parts[0], parts[1], kv.Value));
        }
        return result.OrderByDescending(r => r.Item3).ToList();
    }
}

/// <summary>
/// The learn pass: mine habits from the activity history and fold in the person's feedback (dismiss /
/// not helpful) into the "don't suggest again" list. Run occasionally (e.g. hourly / daily), not every tick.
/// </summary>
public static class Learner
{
    public static LearnedMemory Run(string activityFolder, string memoryPath, string? recsFolder = null, int minCount = 3, int feedbackDays = 7)
    {
        var mem = LearnedMemory.Load(memoryPath);

        var ordered = ActivityReader.ReadJsonlFolder(activityFolder)
            .Where(e => e.EventType is "app_session_start" or "browser_page")
            .OrderBy(e => e.TimestampUtc).ThenBy(e => e.Sequence)
            .ToList();
        foreach (var (a, b, c) in HabitMiner.Mine(ordered.Select(LabelOf), minCount))
            mem.Reinforce(a, b, c, DateTimeOffset.UtcNow);

        if (recsFolder is not null)
        {
            var log = new RecommendationLog(recsFolder);
            for (var d = 0; d < feedbackDays; d++)
            {
                var day = DateTimeOffset.Now.AddDays(-d);
                var actions = log.ReadActions(day);
                if (actions.Count == 0) continue;
                var byId = new Dictionary<string, Recommendation>(StringComparer.Ordinal);
                foreach (var r in log.Read(day)) byId[r.Id] = r;
                foreach (var a in actions)
                    if ((a.Action == "dismiss" || a.Action == "not_helpful") && byId.TryGetValue(a.RecId, out var rec))
                        mem.Suppress(rec.Title);
            }
        }

        mem.Save(memoryPath);
        return mem;
    }

    /// <summary>A short, stable label for "where the person was" — as specific as the logs allow.</summary>
    internal static string LabelOf(WatchEvent e)
    {
        if (!string.IsNullOrEmpty(e.Domain)) return "web:" + e.Domain;
        if (!string.IsNullOrEmpty(e.Application)) return "app:" + e.Application;
        if (!string.IsNullOrEmpty(e.ProcessName)) return "app:" + e.ProcessName;
        return "";
    }
}
