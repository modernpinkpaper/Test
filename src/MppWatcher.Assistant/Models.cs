using System.Text.Json;
using System.Text.Json.Serialization;
using MppWatcher.Core.Events;

namespace MppWatcher.Assistant;

/// <summary>Shared JSON settings for the assistant's own files (memory, cursor, recommendations).</summary>
public static class AssistantJson
{
    public static readonly JsonSerializerOptions Options = new()
    {
        WriteIndented = false,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
    };
    public static readonly JsonSerializerOptions Indented = new(Options) { WriteIndented = true };
}

/// <summary>One button the assistant can offer on a suggestion. The AI picks which to show.</summary>
public sealed class SuggestedButton
{
    [JsonPropertyName("label")] public string Label { get; set; } = "";
    /// <summary>open_url | copy | open_file | add_tracker | add_reminder | draft_message | run_script | remind | dismiss</summary>
    [JsonPropertyName("kind")] public string Kind { get; set; } = "";
    /// <summary>What the button acts on: a URL, a file path, text to copy, etc. (optional).</summary>
    [JsonPropertyName("target")] public string? Target { get; set; }

    public SuggestedButton() { }
    public SuggestedButton(string label, string kind, string? target = null) { Label = label; Kind = kind; Target = target; }
}

/// <summary>A single on-screen suggestion the assistant wants to make.</summary>
public sealed class Recommendation
{
    [JsonPropertyName("id")] public string Id { get; set; } = Guid.NewGuid().ToString("N");
    [JsonPropertyName("at_utc")] public DateTimeOffset AtUtc { get; set; } = DateTimeOffset.UtcNow;
    [JsonPropertyName("title")] public string Title { get; set; } = "";
    /// <summary>Plain-English reason/evidence behind it (for the recommendations log and review).</summary>
    [JsonPropertyName("why")] public string Why { get; set; } = "";
    /// <summary>low | normal | high — how worth interrupting for.</summary>
    [JsonPropertyName("urgency")] public string Urgency { get; set; } = "normal";
    [JsonPropertyName("buttons")] public List<SuggestedButton> Buttons { get; set; } = new();
    /// <summary>Filled in later (Step 2) when the user clicks: which button, or "dismissed".</summary>
    [JsonPropertyName("user_action")] public string? UserAction { get; set; }
}

/// <summary>Something worth remembering across the day (an open loop, a commitment, a hand-off).</summary>
public sealed class MemoryItem
{
    [JsonPropertyName("id")] public string Id { get; set; } = Guid.NewGuid().ToString("N");
    [JsonPropertyName("text")] public string Text { get; set; } = "";
    /// <summary>open_loop | commitment | friction | handoff | note</summary>
    [JsonPropertyName("kind")] public string Kind { get; set; } = "note";
    [JsonPropertyName("noted_utc")] public DateTimeOffset NotedUtc { get; set; } = DateTimeOffset.UtcNow;
    [JsonPropertyName("resolved")] public bool Resolved { get; set; }
}

/// <summary>What the model is given each tick: the new events since last check + the day memory.</summary>
public sealed class AssistantContext
{
    public IReadOnlyList<WatchEvent> NewEvents { get; }
    public AssistantMemory Memory { get; }
    public string Person { get; }
    public DateTimeOffset NowUtc { get; }
    public LearnedMemory Learned { get; }

    public AssistantContext(IReadOnlyList<WatchEvent> newEvents, AssistantMemory memory, string person, DateTimeOffset nowUtc, LearnedMemory? learned = null)
    {
        NewEvents = newEvents;
        Memory = memory;
        Person = person;
        NowUtc = nowUtc;
        Learned = learned ?? new LearnedMemory();
    }
}
