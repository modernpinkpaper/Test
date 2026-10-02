using System.Drawing;
using System.Windows.Forms;
using MppWatcher.Assistant;

namespace MppWatcher.Assistant.App;

/// <summary>
/// Runs in the system tray. Every interval it asks the engine for new suggestions and pops a card for
/// each. A right-click menu offers Pause/Resume, "Check now", and Exit. Never crashes the tray.
/// </summary>
internal sealed class AssistantTrayContext : ApplicationContext
{
    private readonly AssistantOptions _opts;
    private readonly AssistantEngine _engine;
    private readonly RecommendationLog _log;
    private readonly NotifyIcon _tray;
    private readonly System.Windows.Forms.Timer _timer;
    private readonly System.Windows.Forms.Timer _learnTimer;
    private readonly List<NotificationCard> _cards = new();
    private bool _busy;
    private bool _paused;

    public AssistantTrayContext(AssistantOptions opts)
    {
        _opts = opts;
        var outFolder = string.IsNullOrWhiteSpace(opts.Out) ? opts.Activity! : opts.Out!;
        var cfg = new AssistantConfig { ActivityFolder = opts.Activity!, OutputFolder = outFolder, Person = opts.Person };
        var provider = ProviderFactory.Create(opts.Heuristic, opts.Model, opts.RepeatThreshold);
        _log = new RecommendationLog(outFolder);
        _engine = new AssistantEngine(cfg, provider, _log);

        var menu = new ContextMenuStrip();
        var pauseItem = new ToolStripMenuItem("Pause");
        pauseItem.Click += (_, _) => { _paused = !_paused; pauseItem.Text = _paused ? "Resume" : "Pause"; };
        menu.Items.Add(pauseItem);
        var checkNow = new ToolStripMenuItem("Check now");
        checkNow.Click += async (_, _) => await TickAsync();
        menu.Items.Add(checkNow);
        var testCard = new ToolStripMenuItem("Show a test card");
        testCard.Click += (_, _) => ShowCard(SampleCard());
        menu.Items.Add(testCard);
        menu.Items.Add(new ToolStripSeparator());
        var exit = new ToolStripMenuItem("Exit");
        exit.Click += (_, _) => ExitThread();
        menu.Items.Add(exit);

        _tray = new NotifyIcon
        {
            Icon = SystemIcons.Information,
            Text = "MPP Assistant (" + ProviderFactory.Describe(provider, opts.Model) + ")",
            Visible = true,
            ContextMenuStrip = menu,
        };

        _timer = new System.Windows.Forms.Timer { Interval = Math.Max(15_000, (int)(opts.IntervalMinutes * 60_000)) };
        _timer.Tick += async (_, _) => await TickAsync();
        _timer.Start();

        // Learn recurring habits + fold in feedback, now and once an hour (off the UI thread).
        _learnTimer = new System.Windows.Forms.Timer { Interval = 60 * 60_000 };
        _learnTimer.Tick += (_, _) => RunLearn();
        _learnTimer.Start();
        RunLearn();

        _ = TickAsync(); // first suggestion pass right away
    }

    private void RunLearn() => _ = Task.Run(() => { try { _engine.Learn(); } catch { } });

    private async Task TickAsync()
    {
        if (_busy || _paused) return;
        _busy = true;
        try
        {
            var recs = await _engine.TickAsync();
            foreach (var r in recs) ShowCard(r);
        }
        catch { /* never crash the tray over one tick */ }
        finally { _busy = false; }
    }

    /// <summary>A fake suggestion for testing: proves the pop-up, the no-focus-steal behaviour, and the buttons.</summary>
    private static Recommendation SampleCard()
    {
        var rec = new Recommendation
        {
            Title = "Test card — the assistant is working",
            Why = "This is a test. Keep typing in Gmail — this card should NOT steal your cursor.",
            Urgency = "normal",
        };
        rec.Buttons.Add(new SuggestedButton("Open Google", "open_url", "https://www.google.com"));
        rec.Buttons.Add(new SuggestedButton("Copy a note", "copy", "MPP assistant test"));
        rec.Buttons.Add(new SuggestedButton("Remind me", "remind"));
        rec.Buttons.Add(new SuggestedButton("Dismiss", "dismiss"));
        return rec;
    }

    private void ShowCard(Recommendation rec)
    {
        var card = new NotificationCard(rec, _log, _opts.RemindMinutes, _cards.Count);
        card.FormClosed += (_, _) => { _cards.Remove(card); Relayout(); };
        _cards.Add(card);
        card.Show();
        Relayout();
    }

    /// <summary>Re-stack all open cards from the bottom up, so closing one never leaves an empty gap.</summary>
    private void Relayout()
    {
        var wa = Screen.PrimaryScreen?.WorkingArea ?? new Rectangle(0, 0, 1024, 768);
        var y = wa.Bottom - 12;
        foreach (var card in _cards)
        {
            y -= card.Height;
            card.SetLocation(wa.Right - card.Width - 12, y);
            y -= 10;
        }
    }

    protected override void Dispose(bool disposing)
    {
        if (disposing)
        {
            _timer?.Dispose();
            _learnTimer?.Dispose();
            if (_tray is not null) { _tray.Visible = false; _tray.Dispose(); }
        }
        base.Dispose(disposing);
    }
}
