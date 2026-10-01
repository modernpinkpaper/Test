using System.Text.Json;
using System.Text.Json.Serialization;

namespace MppWatcher.Assistant;

/// <summary>A record of the user clicking a button on a recommendation.</summary>
public sealed class RecommendationAction
{
    [JsonPropertyName("rec_id")] public string RecId { get; set; } = "";
    [JsonPropertyName("action")] public string Action { get; set; } = "";
    [JsonPropertyName("at_utc")] public DateTimeOffset AtUtc { get; set; } = DateTimeOffset.UtcNow;
}

/// <summary>
/// Writes every recommendation to a per-day file (recommendations_YYYY-MM-DD.jsonl) in the person's
/// folder, so you can review what the assistant suggested and whether it helped. One JSON line each.
/// </summary>
public sealed class RecommendationLog
{
    private readonly string _folder;

    public RecommendationLog(string folder) => _folder = folder;

    public string FileFor(DateTimeOffset localDay) =>
        Path.Combine(_folder, $"recommendations_{localDay.LocalDateTime:yyyy-MM-dd}.jsonl");

    public void Append(Recommendation rec)
    {
        try
        {
            Directory.CreateDirectory(_folder);
            var line = JsonSerializer.Serialize(rec, AssistantJson.Options);
            File.AppendAllText(FileFor(rec.AtUtc), line + "\n");
        }
        catch { /* never let a logging hiccup stop the assistant */ }
    }

    public string ActionFileFor(DateTimeOffset localDay) =>
        Path.Combine(_folder, $"recommendation_actions_{localDay.LocalDateTime:yyyy-MM-dd}.jsonl");

    /// <summary>Record which button the user clicked on a recommendation (feedback + "what I did").</summary>
    public void AppendAction(string recId, string action, DateTimeOffset atUtc)
    {
        try
        {
            Directory.CreateDirectory(_folder);
            var line = JsonSerializer.Serialize(new RecommendationAction { RecId = recId, Action = action, AtUtc = atUtc }, AssistantJson.Options);
            File.AppendAllText(ActionFileFor(atUtc), line + "\n");
        }
        catch { /* never let feedback logging break the UI */ }
    }

    /// <summary>Read back a day's recommendations (for review / tests).</summary>
    public IReadOnlyList<Recommendation> Read(DateTimeOffset localDay)
    {
        var file = FileFor(localDay);
        var list = new List<Recommendation>();
        if (!File.Exists(file)) return list;
        foreach (var line in File.ReadAllLines(file))
        {
            if (string.IsNullOrWhiteSpace(line)) continue;
            try
            {
                var rec = JsonSerializer.Deserialize<Recommendation>(line, AssistantJson.Options);
                if (rec is not null) list.Add(rec);
            }
            catch { /* skip a bad line */ }
        }
        return list;
    }
}
