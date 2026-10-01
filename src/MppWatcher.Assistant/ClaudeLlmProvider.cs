using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using Anthropic;
using Anthropic.Models.Messages;
using MppWatcher.Core.Events;

namespace MppWatcher.Assistant;

/// <summary>
/// The real brain: sends the new events + day memory to Claude and asks for suggestions as JSON.
/// Cheap by design — only the NEW events are sent each tick, never the whole day. Default model is
/// Haiku (the constant cheap watcher); a later step escalates to Opus only when something looks worth
/// deeper reasoning. Never throws into the caller: on any API/parse problem it returns no suggestions.
/// </summary>
public sealed class ClaudeLlmProvider : ILlmProvider
{
    private readonly AnthropicClient _client;
    private readonly string _model;
    private readonly int _maxEventsPerTick;

    public const string DefaultModel = "claude-haiku-4-5";

    public ClaudeLlmProvider(string? apiKey = null, string model = DefaultModel, int maxEventsPerTick = 200)
    {
        _client = new AnthropicClient { ApiKey = apiKey ?? Environment.GetEnvironmentVariable("ANTHROPIC_API_KEY") };
        _model = model;
        _maxEventsPerTick = maxEventsPerTick;
    }

    public async Task<IReadOnlyList<Recommendation>> SuggestAsync(AssistantContext ctx, CancellationToken ct = default)
    {
        try
        {
            var user = BuildUserPrompt(ctx);
            var response = await _client.Messages.Create(new MessageCreateParams
            {
                Model = _model,
                MaxTokens = 1500,
                System = SystemPrompt(ctx.Person),
                Messages = [new() { Role = Role.User, Content = user }],
            });

            var text = new StringBuilder();
            foreach (var block in response.Content.Select(b => b.Value).OfType<TextBlock>()) text.Append(block.Text);
            return ParseRecommendations(text.ToString());
        }
        catch
        {
            // No key, API error, bad JSON — stay quiet rather than break the user's work.
            return Array.Empty<Recommendation>();
        }
    }

    private static string SystemPrompt(string person) => $"""
        You are MT Log's live work assistant for {person} at a small e-commerce/print business (MPP).
        You watch their computer activity and, now and then, suggest a genuinely useful, specific next
        action — ONLY when it is clearly worth interrupting for. Most of the time you should say nothing.

        What is worth a suggestion: a hand-off you can act on (someone said something is ready), a
        repeated slow/manual task that a small script could speed up, a reminder they'd want, a problem
        to fix (e.g. a printer out of paper). Ignore personal browsing, short breaks, and routine clicks.

        Reply with ONLY a JSON array (no prose, no code fences). Each item:
        {{"title": short line, "why": one sentence of evidence, "urgency": "low"|"normal"|"high",
          "buttons": [{{"label": text, "kind": one of
          ["open_url","copy","open_file","add_tracker","add_reminder","draft_message","run_script","remind","dismiss"],
          "target": optional string the button acts on}}]}}
        Always include a "dismiss" button. If nothing is worth suggesting, reply exactly: []
        Keep it to at most 3 items. Never invent facts not supported by the activity.
        """;

    private string BuildUserPrompt(AssistantContext ctx)
    {
        var sb = new StringBuilder();
        sb.AppendLine("Day memory so far:");
        sb.AppendLine(string.IsNullOrWhiteSpace(ctx.Memory.RunningNote) ? "(none)" : ctx.Memory.RunningNote.Trim());
        var open = ctx.Memory.OpenItems.Where(i => !i.Resolved).ToList();
        if (open.Count > 0)
        {
            sb.AppendLine("Open items:");
            foreach (var i in open) sb.AppendLine($"- [{i.Kind}] {i.Text}");
        }
        sb.AppendLine();
        sb.AppendLine("New activity since last check (most recent last):");
        foreach (var e in ctx.NewEvents.TakeLast(_maxEventsPerTick)) sb.AppendLine(Compact(e));
        sb.AppendLine();
        sb.AppendLine("Return recommendations as a JSON array (or [] for nothing).");
        return sb.ToString();
    }

    /// <summary>A short one-line view of an event — enough signal, few tokens.</summary>
    private static string Compact(WatchEvent e)
    {
        var time = string.IsNullOrEmpty(e.TimestampLocal) ? e.TimestampUtc.ToString("HH:mm:ss") : e.TimestampLocal;
        var parts = new List<string> { time, e.EventType };
        if (!string.IsNullOrEmpty(e.Application)) parts.Add(e.Application!);
        var where = e.PageTitle ?? e.WindowTitle;
        if (!string.IsNullOrEmpty(where)) parts.Add(Clip(where!, 80));
        if (!string.IsNullOrEmpty(e.Domain)) parts.Add(e.Domain!);
        foreach (var key in new[] { "control_name", "action", "label", "value", "previous_value", "document_name", "printer", "reason", "script", "command", "tool" })
            if (Str(e.Metadata, key) is { } v) parts.Add($"{key}={Clip(v, 60)}");
        return "- " + string.Join(" | ", parts);
    }

    private static string Clip(string s, int max) => s.Length <= max ? s : s[..max] + "…";

    private static string? Str(JsonObject m, string key)
    {
        if (!m.TryGetPropertyValue(key, out var node) || node is null) return null;
        try { return node.GetValue<string>(); } catch { return node.ToString(); }
    }

    /// <summary>Pull the JSON array out of the model's reply (tolerating stray text/fences) and parse it.</summary>
    internal static IReadOnlyList<Recommendation> ParseRecommendations(string text)
    {
        if (string.IsNullOrWhiteSpace(text)) return Array.Empty<Recommendation>();
        var start = text.IndexOf('[');
        var end = text.LastIndexOf(']');
        if (start < 0 || end <= start) return Array.Empty<Recommendation>();
        var json = text.Substring(start, end - start + 1);
        try
        {
            var recs = JsonSerializer.Deserialize<List<Recommendation>>(json, AssistantJson.Options);
            return recs ?? (IReadOnlyList<Recommendation>)Array.Empty<Recommendation>();
        }
        catch { return Array.Empty<Recommendation>(); }
    }
}
