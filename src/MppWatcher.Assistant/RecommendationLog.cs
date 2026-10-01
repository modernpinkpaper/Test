using System.Text.Json;

namespace MppWatcher.Assistant;

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
