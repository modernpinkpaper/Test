using System.Drawing;
using System.Windows.Forms;
using MppWatcher.Assistant;

namespace MppWatcher.Assistant.App;

/// <summary>
/// Runs in the system tray. Every interval it asks the engine for new suggestions and pops a card for
/// each. The right-click menu shows live status (current stage, countdown to next check, last suggestion,
/// count this session) plus Pause/Resume, "Check now", "Show a test card", and Exit. Never crashes the tray.
/// </summary>
internal sealed class AssistantTrayContext : ApplicationContext
{
    private readonly AssistantOptions _opts;
    private readonly AssistantEngine _engine;
    private readonly RecommendationLog _log;
    private readonly NotifyIcon _tray;
    private readonly System.Windows.Forms.Timer _timer;
    private readonly System.Windows.Forms.Timer _learnTimer;
    private readonly System.Windows.Forms.Timer _statusTimer;
    private readonly List<NotificationCard> _cards = new();
    private readonly int _intervalMs;
    private bool _busy;
    private bool _paused;

    // Live status shown in the right-click menu.
    private readonly ToolStripMenuItem _statusItem = Info("● Starting…");
    private readonly ToolStripMenuItem _nextItem = Info("Next check: soon");
    private readonly ToolStripMenuItem _lastItem = Info("Last suggestion: none yet");
    private readonly ToolStripMenuItem _countItem = Info("Suggestions this session: 0");
    private DateTime _nextCheckUtc;
    private string _lastText = "none yet";
    private int _count;
    private bool _checking;

    private static ToolStripMenuItem Info(string text) => new(text) { Enabled = false };

    public AssistantTrayContext(AssistantOptions opts)
    {
        _opts = opts;
        var outFolder = string.IsNullOrWhiteSpace(opts.Out) ? opts.Activity! : opts.Out!;
        var cfg = new AssistantConfig { ActivityFolder = opts.Activity!, OutputFolder = outFolder, Person = opts.Person };
        var provider = ProviderFactory.Create(opts.Heuristic, opts.Model, opts.RepeatThreshold);
        _log = new RecommendationLog(outFolder);
        _engine = new AssistantEngine(cfg, provider, _log);

        _intervalMs = Math.Max(15_000, (int)(opts.IntervalMinutes * 60_000));
        _nextCheckUtc = DateTime.UtcNow.AddMilliseconds(_intervalMs);

        var menu = new ContextMenuStrip();
        menu.Items.Add(_statusItem);
        menu.Items.Add(_nextItem);
        menu.Items.Add(_lastItem);
        menu.Items.Add(_countItem);
        menu.Items.Add(new ToolStripSeparator());

        var pauseItem = new ToolStripMenuItem("Pause");
        pauseItem.Click += (_, _) => { _paused = !_paused; pauseItem.Text = _paused ? "Resume" : "Pause"; UpdateStatus(); };
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

        _timer = new System.Windows.Forms.Timer { Interval = _intervalMs };
        _timer.Tick += async (_, _) => await TickAsync();
        _timer.Start();

        // Refresh the countdown / status text once a second so the menu is live when opened.
        _statusTimer = new System.Windows.Forms.Timer { Interval = 1000 };
        _statusTimer.Tick += (_, _) => UpdateStatus();
        _statusTimer.Start();

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
        _checking = true;
        UpdateStatus();
        try
        {
            var recs = await _engine.TickAsync();
            foreach (var r in recs) ShowCard(r);
        }
        catch { /* never crash the tray over one tick */ }
        finally
        {
            _busy = false;
            _checking = false;
            _nextCheckUtc = DateTime.UtcNow.AddMilliseconds(_intervalMs);
            UpdateStatus();
        }
    }

    /// <summary>Refresh the live status lines in the menu (safe to call every second).</summary>
    private void UpdateStatus()
    {
        _statusItem.Text = _paused ? "● Paused" : _checking ? "● Checking your logs…" : "● Watching (idle)";
        if (_paused)
            _nextItem.Text = "Next check: paused";
        else if (_checking)
            _nextItem.Text = "Next check: now";
        else
        {
            var secs = Math.Max(0, (int)(_nextCheckUtc - DateTime.UtcNow).TotalSeconds);
            _nextItem.Text = $"Next check in {secs / 60}:{secs % 60:00}";
        }
        _lastItem.Text = "Last suggestion: " + _lastText;
        _countItem.Text = $"Suggestions this session: {_count}";
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

        _count++;
        var title = rec.Title.Length > 40 ? rec.Title[..40] + "…" : rec.Title;
        _lastText = $"{DateTime.Now:h:mm tt} — {title}";
        UpdateStatus();
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
            _statusTimer?.Dispose();
            if (_tray is not null) { _tray.Visible = false; _tray.Dispose(); }
        }
        base.Dispose(disposing);
    }
}
