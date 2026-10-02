using System.Text.Json.Nodes;
using MppWatcher.Core.Events;

namespace MppWatcher.Assistant;

/// <summary>
/// Turns the new events + memory into suggestions. The real version (later step) calls Claude/OpenAI;
/// this interface keeps the model swappable and lets everything else be tested without an API key.
/// </summary>
public interface ILlmProvider
{
    Task<IReadOnlyList<Recommendation>> SuggestAsync(AssistantContext ctx, CancellationToken ct = default);

    /// <summary>Answer a plain-English question about the activity ("when did X happen?"). Returns a short answer.</summary>
    Task<string> AnswerAsync(string question, IReadOnlyList<WatchEvent> events, string person, CancellationToken ct = default);
}

/// <summary>
/// A no-API-key stand-in used for building and testing the pipeline (and as a safe fallback when no
/// key is set). It uses a few simple rules so the pieces can be proven end to end. The real judgment
/// ("is this worth saying?", hand-offs, cross-time links) comes from the LLM provider in a later step.
/// </summary>
public sealed class HeuristicLlmProvider : ILlmProvider
{
    private readonly int _repeatThreshold;

    public HeuristicLlmProvider(int repeatThreshold = 8) => _repeatThreshold = repeatThreshold;

    public Task<IReadOnlyList<Recommendation>> SuggestAsync(AssistantContext ctx, CancellationToken ct = default)
    {
        var recs = new List<Recommendation>();

        // 1) A printer that needs attention (not a "cleared" event).
        foreach (var e in ctx.NewEvents.Where(e => e.EventType == "printer_problem"))
        {
            if (Bool(e.Metadata, "resolved")) continue;
            var printer = Str(e.Metadata, "printer") ?? "A printer";
            var reason = Str(e.Metadata, "reason") ?? "needs attention";
            recs.Add(new Recommendation
            {
                Title = $"{printer}: {reason}",
                Why = $"The watcher reported '{reason}' on {printer}.",
                Urgency = "high",
                Buttons = { new SuggestedButton("Remind me in 1 hr", "remind"), new SuggestedButton("Dismiss", "dismiss") },
            });
        }

        // 2) The same control clicked many times — a candidate to automate with a small script.
        // Skip navigation / window-switch / taskbar junk so we don't suggest "automate New Tab".
        var repeats = ctx.NewEvents
            .Where(e => e.EventType == "ui_action")
            .Select(e => Str(e.Metadata, "control_name"))
            .Where(n => !string.IsNullOrWhiteSpace(n) && IsAutomatable(n!))
            .Select(n => n!)
            .GroupBy(n => n, StringComparer.OrdinalIgnoreCase)
            .Where(g => g.Count() >= _repeatThreshold)
            .ToList();
        foreach (var g in repeats)
        {
            var idea = $"Automate the repeated '{g.Key}' step with a script";
            recs.Add(new Recommendation
            {
                Title = $"Repeated '{g.Key}' {g.Count()}× — automate it?",
                Why = $"You used '{g.Key}' {g.Count()} times in a short span. A small script could do this much faster.",
                Urgency = "normal",
                Buttons =
                {
                    new SuggestedButton("Add to Project Tracker", "add_tracker", idea),
                    new SuggestedButton("Remind me in 1 hr", "remind"),
                    new SuggestedButton("Dismiss", "dismiss"),
                },
            });
        }

        return Task.FromResult<IReadOnlyList<Recommendation>>(recs);
    }

    public Task<string> AnswerAsync(string question, IReadOnlyList<WatchEvent> events, string person, CancellationToken ct = default) =>
        Task.FromResult("Asking questions needs the Claude brain. Set ANTHROPIC_API_KEY, then run the --ask command again.");

    // Control names that are just navigation / window-switching / taskbar noise — never "automate" targets.
    private static readonly string[] JunkContains =
    {
        "running window", "memory usage", "- google chrome", "new tab", "tab flyout", "file explorer",
        "search box", "bypass", "font size", "close find", "date and time", "address and search",
        "minimize", "maximize", "google chrome", "- etsy", "- amazon",
    };
    private static readonly HashSet<string> JunkExact = new(StringComparer.OrdinalIgnoreCase)
    {
        "amazon", "etsy", "back", "close", "new tab", "orders", "you", "messages", "home", "menu",
    };

    private static bool IsAutomatable(string name)
    {
        var n = name.Trim();
        if (n.Length < 3 || JunkExact.Contains(n)) return false;
        var low = n.ToLowerInvariant();
        return !JunkContains.Any(j => low.Contains(j));
    }

    private static string? Str(JsonObject m, string key)
    {
        if (!m.TryGetPropertyValue(key, out var node) || node is null) return null;
        try { return node.GetValue<string>(); } catch { return node.ToString(); }
    }

    private static bool Bool(JsonObject m, string key)
    {
        if (m.TryGetPropertyValue(key, out var node) && node is not null)
        {
            try { return node.GetValue<bool>(); } catch { return false; }
        }
        return false;
    }
}
