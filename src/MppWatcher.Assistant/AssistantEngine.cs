namespace MppWatcher.Assistant;

/// <summary>Where the assistant reads from and writes to, plus a few knobs.</summary>
public sealed class AssistantConfig
{
    /// <summary>Folder of exported activity .jsonl (the person's mpp activity folder).</summary>
    public string ActivityFolder { get; init; } = "";
    /// <summary>Where the cursor, memory and recommendations files are written. Defaults to ActivityFolder.</summary>
    public string OutputFolder { get; init; } = "";
    /// <summary>A label for who this is (for the context given to the model).</summary>
    public string Person { get; init; } = "";
    /// <summary>How long to keep resolved memory items before pruning.</summary>
    public TimeSpan MemoryKeep { get; init; } = TimeSpan.FromDays(7);

    public string CursorPath => Path.Combine(OutputFolder, "assistant_cursor.json");
    public string MemoryPath => Path.Combine(OutputFolder, "assistant_memory.json");
}

/// <summary>
/// One "tick" of the assistant: read the new events since last time, ask the model for suggestions,
/// write them to the recommendations log, and save memory + cursor. Only new events are ever sent to
/// the model — never the whole day again (that is the rule that keeps it cheap).
/// </summary>
public sealed class AssistantEngine
{
    private readonly AssistantConfig _cfg;
    private readonly ILlmProvider _provider;
    private readonly RecommendationLog _log;

    public AssistantEngine(AssistantConfig cfg, ILlmProvider provider, RecommendationLog? log = null)
    {
        _cfg = cfg;
        _provider = provider;
        _log = log ?? new RecommendationLog(string.IsNullOrEmpty(cfg.OutputFolder) ? cfg.ActivityFolder : cfg.OutputFolder);
    }

    public async Task<IReadOnlyList<Recommendation>> TickAsync(CancellationToken ct = default)
    {
        var all = ActivityReader.ReadJsonlFolder(_cfg.ActivityFolder);
        var cursor = ActivityCursor.Load(_cfg.CursorPath);
        var result = ActivityReader.SelectNew(all, cursor);
        if (result.Events.Count == 0) return Array.Empty<Recommendation>();

        var memory = AssistantMemory.Load(_cfg.MemoryPath);
        var ctx = new AssistantContext(result.Events, memory, _cfg.Person, DateTimeOffset.UtcNow);

        var recs = await _provider.SuggestAsync(ctx, ct);
        foreach (var r in recs) _log.Append(r);

        memory.Prune(DateTimeOffset.UtcNow, _cfg.MemoryKeep);
        memory.Save(_cfg.MemoryPath);
        result.NewCursor.Save(_cfg.CursorPath);
        return recs;
    }
}
