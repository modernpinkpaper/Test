using System.Text.Json.Nodes;
using MppWatcher.Assistant;
using MppWatcher.Core.Events;

namespace MppWatcher.Core.Tests;

public class AssistantTests
{
    private static readonly DateTimeOffset T0 = DateTimeOffset.Parse("2026-10-01T10:00:00Z");

    private static WatchEvent Ev(string type, DateTimeOffset ts, string id, long seq = 0, JsonObject? meta = null) =>
        new() { EventType = type, TimestampUtc = ts, EventId = id, Sequence = seq, Metadata = meta ?? new JsonObject() };

    private static string TempDir()
    {
        var d = Path.Combine(Path.GetTempPath(), "mpp-assistant-test-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(d);
        return d;
    }

    [Fact]
    public void SelectNew_returns_all_first_then_only_newer()
    {
        var evs = new[] { Ev("a", T0, "1"), Ev("b", T0.AddSeconds(1), "2"), Ev("c", T0.AddSeconds(2), "3") };

        var r1 = ActivityReader.SelectNew(evs, new ActivityCursor());
        Assert.Equal(3, r1.Events.Count);

        Assert.Empty(ActivityReader.SelectNew(evs, r1.NewCursor).Events); // nothing new the second time

        var withNewer = evs.Append(Ev("d", T0.AddSeconds(3), "4")).ToArray();
        var r3 = ActivityReader.SelectNew(withNewer, r1.NewCursor);
        Assert.Single(r3.Events);
        Assert.Equal("4", r3.Events[0].EventId);
    }

    [Fact]
    public void SelectNew_picks_up_a_new_event_at_the_same_last_timestamp()
    {
        var evs = new[] { Ev("a", T0, "1"), Ev("c", T0.AddSeconds(2), "3") };
        var r1 = ActivityReader.SelectNew(evs, new ActivityCursor());

        var sameTs = evs.Append(Ev("c2", T0.AddSeconds(2), "3b")).ToArray();
        var r2 = ActivityReader.SelectNew(sameTs, r1.NewCursor);
        Assert.Single(r2.Events);
        Assert.Equal("3b", r2.Events[0].EventId);
    }

    [Fact]
    public void RecommendationLog_round_trips()
    {
        var dir = TempDir();
        var log = new RecommendationLog(dir);
        var rec = new Recommendation { Title = "t", Why = "w", Urgency = "high", AtUtc = DateTimeOffset.Parse("2026-10-01T15:00:00Z") };
        rec.Buttons.Add(new SuggestedButton("Dismiss", "dismiss"));
        log.Append(rec);

        var back = log.Read(rec.AtUtc);
        Assert.Single(back);
        Assert.Equal("t", back[0].Title);
        Assert.Equal("dismiss", back[0].Buttons[0].Kind);
    }

    [Fact]
    public void Memory_add_resolve_save_load_prune()
    {
        var path = Path.Combine(TempDir(), "mem.json");
        var m = new AssistantMemory();
        var item = m.AddOpenItem("Erika said collection ready", "handoff", DateTimeOffset.UtcNow);
        Assert.NotNull(item);
        m.Save(path);

        var m2 = AssistantMemory.Load(path);
        Assert.Single(m2.OpenItems);
        Assert.True(m2.Resolve(item!.Id));
        Assert.True(m2.OpenItems[0].Resolved);

        m2.Prune(DateTimeOffset.UtcNow.AddDays(10), TimeSpan.FromDays(7));
        Assert.Empty(m2.OpenItems); // resolved + older than keep → dropped
    }

    [Fact]
    public async Task Heuristic_flags_printer_problem_but_not_a_cleared_one()
    {
        var problem = Ev("printer_problem", T0, "p1", meta: new JsonObject { ["printer"] = "MPP Test", ["reason"] = "Out of paper", ["resolved"] = false });
        var recs = await new HeuristicLlmProvider().SuggestAsync(Ctx(problem));
        Assert.Single(recs);
        Assert.Contains("Out of paper", recs[0].Title);

        var cleared = Ev("printer_problem", T0, "p2", meta: new JsonObject { ["printer"] = "X", ["reason"] = "cleared", ["resolved"] = true });
        Assert.Empty(await new HeuristicLlmProvider().SuggestAsync(Ctx(cleared)));
    }

    [Fact]
    public async Task Heuristic_suggests_automation_for_repeated_clicks()
    {
        var clicks = Enumerable.Range(0, 9)
            .Select(i => Ev("ui_action", T0.AddSeconds(i), "u" + i, meta: new JsonObject { ["control_name"] = "Paste" }))
            .ToArray();
        var recs = await new HeuristicLlmProvider(8).SuggestAsync(Ctx(clicks));
        Assert.Single(recs);
        Assert.Contains("Paste", recs[0].Title);
        Assert.Contains(recs[0].Buttons, b => b.Kind == "add_tracker");
    }

    [Fact]
    public async Task Engine_tick_writes_recs_then_nothing_new_second_time()
    {
        var dir = TempDir();
        var e = Ev("printer_problem", DateTimeOffset.UtcNow, "x1",
            meta: new JsonObject { ["printer"] = "P", ["reason"] = "Paper jam", ["resolved"] = false });
        File.WriteAllText(Path.Combine(dir, "events_1.jsonl"), EventJson.Serialize(e) + "\n");

        var cfg = new AssistantConfig { ActivityFolder = dir, OutputFolder = dir, Person = "Dalia" };
        var engine = new AssistantEngine(cfg, new HeuristicLlmProvider());

        var recs = await engine.TickAsync();
        Assert.Single(recs);
        Assert.True(File.Exists(new RecommendationLog(dir).FileFor(recs[0].AtUtc)));

        Assert.Empty(await engine.TickAsync()); // cursor advanced; no new events
    }

    [Fact]
    public void ParseRecommendations_reads_a_plain_array()
    {
        var json = """[{"title":"T","why":"W","urgency":"high","buttons":[{"label":"Dismiss","kind":"dismiss"}]}]""";
        var recs = ClaudeLlmProvider.ParseRecommendations(json);
        Assert.Single(recs);
        Assert.Equal("T", recs[0].Title);
        Assert.Equal("high", recs[0].Urgency);
        Assert.Equal("dismiss", recs[0].Buttons[0].Kind);
    }

    [Fact]
    public void ParseRecommendations_tolerates_fences_and_text()
    {
        var reply = "Sure! Here you go:\n```json\n[{\"title\":\"Add ads\",\"why\":\"Erika said ready\"}]\n```\nHope that helps.";
        var recs = ClaudeLlmProvider.ParseRecommendations(reply);
        Assert.Single(recs);
        Assert.Equal("Add ads", recs[0].Title);
    }

    [Theory]
    [InlineData("[]")]
    [InlineData("no json here")]
    [InlineData("")]
    public void ParseRecommendations_returns_empty_when_nothing(string reply) =>
        Assert.Empty(ClaudeLlmProvider.ParseRecommendations(reply));

    [Fact]
    public void AppendAction_writes_a_feedback_line()
    {
        var dir = TempDir();
        var log = new RecommendationLog(dir);
        var at = DateTimeOffset.Parse("2026-10-01T15:00:00Z");
        log.AppendAction("rec123", "add_tracker", at);

        var file = log.ActionFileFor(at);
        Assert.True(File.Exists(file));
        var text = File.ReadAllText(file);
        Assert.Contains("rec123", text);
        Assert.Contains("add_tracker", text);
    }

    [Fact]
    public void ProviderFactory_falls_back_to_heuristic_without_a_key()
    {
        // CI has no ANTHROPIC_API_KEY, and forceHeuristic guarantees the stand-in regardless.
        Assert.IsType<HeuristicLlmProvider>(ProviderFactory.Create(forceHeuristic: true));
    }

    [Fact]
    public void HabitMiner_finds_repeated_A_then_B()
    {
        // business email -> personal email, three times, plus some noise.
        var seq = new[]
        {
            "web:mail.business.com", "web:mail.personal.com",
            "web:amazon.com",
            "web:mail.business.com", "web:mail.personal.com",
            "web:keepa.com",
            "web:mail.business.com", "web:mail.personal.com",
        };
        var hits = HabitMiner.Mine(seq, minCount: 3);
        Assert.Contains(hits, h => h.A == "web:mail.business.com" && h.B == "web:mail.personal.com" && h.Count == 3);
    }

    [Fact]
    public void HabitMiner_ignores_rare_transitions()
    {
        var hits = HabitMiner.Mine(new[] { "app:A", "app:B", "app:A", "app:C" }, minCount: 3);
        Assert.Empty(hits);
    }

    [Fact]
    public void LearnedMemory_reinforce_suppress_save_load()
    {
        var path = Path.Combine(TempDir(), "learned.json");
        var m = new LearnedMemory();
        m.Reinforce("web:a", "web:b", 4, DateTimeOffset.UtcNow);
        m.Suppress("Open personal Gmail");
        m.Save(path);

        var m2 = LearnedMemory.Load(path);
        Assert.Single(m2.Patterns);
        Assert.Equal(4, m2.Patterns[0].Count);
        Assert.True(m2.IsSuppressed("open personal gmail")); // case-insensitive
    }

    [Fact]
    public void Learner_mines_habits_and_suppresses_dismissed()
    {
        var dir = TempDir();
        // Build a few days' worth of browser_page events: business -> personal, 3x.
        var lines = new List<string>();
        var t = DateTimeOffset.Parse("2026-09-28T09:00:00Z");
        for (var i = 0; i < 3; i++)
        {
            lines.Add(EventJson.Serialize(Page(t.AddMinutes(i * 10), "biz" + i, "mail.business.com")));
            lines.Add(EventJson.Serialize(Page(t.AddMinutes(i * 10 + 1), "per" + i, "mail.personal.com")));
        }
        File.WriteAllText(Path.Combine(dir, "events_1.jsonl"), string.Join("\n", lines) + "\n");

        // A recommendation the user dismissed -> should be suppressed.
        var log = new RecommendationLog(dir);
        var rec = new Recommendation { Title = "Open personal Gmail", AtUtc = DateTimeOffset.Now };
        log.Append(rec);
        log.AppendAction(rec.Id, "dismiss", DateTimeOffset.Now);

        var mem = Learner.Run(dir, Path.Combine(dir, "learned.json"), dir, minCount: 3);
        Assert.Contains(mem.Patterns, p => p.Trigger == "web:mail.business.com" && p.Then == "web:mail.personal.com");
        Assert.True(mem.IsSuppressed("Open personal Gmail"));
    }

    private static WatchEvent Page(DateTimeOffset ts, string id, string domain) => new()
    {
        EventType = "browser_page",
        TimestampUtc = ts,
        EventId = id,
        Domain = domain,
        Application = "msedge",
    };

    private static AssistantContext Ctx(params WatchEvent[] events) =>
        new(events, new AssistantMemory(), "Dalia", DateTimeOffset.UtcNow);
}
