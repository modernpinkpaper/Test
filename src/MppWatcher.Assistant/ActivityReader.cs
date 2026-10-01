using System.Text.Json;
using System.Text.Json.Serialization;
using MppWatcher.Core.Events;

namespace MppWatcher.Assistant;

/// <summary>
/// Remembers how far we've read, so each tick only sees NEW events (never the whole day again).
/// We keep the highest timestamp seen plus the event ids at exactly that timestamp, so events that
/// share the last timestamp are not missed or repeated.
/// </summary>
public sealed class ActivityCursor
{
    [JsonPropertyName("last_timestamp_utc")] public DateTimeOffset LastTimestampUtc { get; set; } = DateTimeOffset.MinValue;
    [JsonPropertyName("seen_at_last")] public List<string> SeenAtLast { get; set; } = new();

    public static ActivityCursor Load(string path)
    {
        try
        {
            if (File.Exists(path))
                return JsonSerializer.Deserialize<ActivityCursor>(File.ReadAllText(path), AssistantJson.Options) ?? new ActivityCursor();
        }
        catch { /* a missing or broken cursor just means "start fresh" */ }
        return new ActivityCursor();
    }

    public void Save(string path)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(path))!);
        File.WriteAllText(path, JsonSerializer.Serialize(this, AssistantJson.Options));
    }
}

/// <summary>The new events found this tick, and the cursor to save afterwards.</summary>
public sealed record NewEventsResult(IReadOnlyList<WatchEvent> Events, ActivityCursor NewCursor);

/// <summary>
/// Reads the activity events MT Log already exports as .jsonl, and picks out only the ones newer
/// than the cursor. Pure selection logic (SelectNew) is separated from disk reading so it is easy
/// to unit-test.
/// </summary>
public sealed class ActivityReader
{
    /// <summary>Read every event from all *.jsonl files under <paramref name="folder"/> (recursively).</summary>
    public static IReadOnlyList<WatchEvent> ReadJsonlFolder(string folder)
    {
        var events = new List<WatchEvent>();
        if (!Directory.Exists(folder)) return events;
        foreach (var file in Directory.EnumerateFiles(folder, "*.jsonl", SearchOption.AllDirectories))
        {
            // Skip our own output files so we never read our recommendations back in as activity.
            var name = Path.GetFileName(file);
            if (name.StartsWith("recommendations_", StringComparison.OrdinalIgnoreCase)) continue;
            foreach (var line in SafeReadLines(file))
            {
                if (string.IsNullOrWhiteSpace(line)) continue;
                WatchEvent? e = null;
                try { e = EventJson.Deserialize(line); } catch { /* skip a bad line */ }
                if (e is not null) events.Add(e);
            }
        }
        return events;
    }

    private static IEnumerable<string> SafeReadLines(string file)
    {
        string[] lines;
        try { lines = File.ReadAllLines(file); } catch { yield break; }
        foreach (var l in lines) yield return l;
    }

    /// <summary>
    /// From all events, return those newer than the cursor (oldest first), plus the new cursor.
    /// "Newer" = timestamp after the cursor, or the same timestamp but an id we have not emitted yet.
    /// </summary>
    public static NewEventsResult SelectNew(IEnumerable<WatchEvent> all, ActivityCursor cursor)
    {
        var seen = new HashSet<string>(cursor.SeenAtLast, StringComparer.Ordinal);
        var fresh = new List<WatchEvent>();
        foreach (var e in all)
        {
            if (e.TimestampUtc > cursor.LastTimestampUtc) fresh.Add(e);
            else if (e.TimestampUtc == cursor.LastTimestampUtc && !seen.Contains(e.EventId)) fresh.Add(e);
        }
        fresh.Sort((a, b) =>
        {
            var c = a.TimestampUtc.CompareTo(b.TimestampUtc);
            if (c != 0) return c;
            c = a.Sequence.CompareTo(b.Sequence);
            return c != 0 ? c : string.CompareOrdinal(a.EventId, b.EventId);
        });

        var next = new ActivityCursor { LastTimestampUtc = cursor.LastTimestampUtc, SeenAtLast = new List<string>(cursor.SeenAtLast) };
        if (fresh.Count > 0)
        {
            var maxTs = fresh[^1].TimestampUtc;
            if (maxTs > next.LastTimestampUtc)
            {
                next.LastTimestampUtc = maxTs;
                next.SeenAtLast = new List<string>();
            }
            // Remember every id at the top timestamp so the next read doesn't repeat them.
            var atTop = new HashSet<string>(next.SeenAtLast, StringComparer.Ordinal);
            foreach (var e in fresh)
                if (e.TimestampUtc == next.LastTimestampUtc) atTop.Add(e.EventId);
            next.SeenAtLast = atTop.ToList();
        }
        return new NewEventsResult(fresh, next);
    }
}
