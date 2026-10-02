using System.Drawing;
using System.Windows.Forms;
using MppWatcher.Assistant;

namespace MppWatcher.Assistant.App;

/// <summary>
/// A small sticky card in the bottom-right corner showing one suggestion (title + why) and its buttons.
/// It auto-sizes its height to the text (so nothing is cut off), stays until the user clicks something,
/// and never steals focus. The tray re-stacks the remaining cards when one closes.
/// </summary>
internal sealed class NotificationCard : Form
{
    private readonly Recommendation _rec;
    private readonly RecommendationLog _log;
    private readonly double _remindMinutes;

    // Show the card WITHOUT stealing focus: you can keep typing in Gmail and click it when ready.
    protected override bool ShowWithoutActivation => true;

    protected override CreateParams CreateParams
    {
        get
        {
            const int WS_EX_NOACTIVATE = 0x08000000;
            const int WS_EX_TOPMOST = 0x00000008;
            var cp = base.CreateParams;
            cp.ExStyle |= WS_EX_NOACTIVATE | WS_EX_TOPMOST;
            return cp;
        }
    }

    public NotificationCard(Recommendation rec, RecommendationLog log, double remindMinutes, int stackIndex)
    {
        _rec = rec;
        _log = log;
        _remindMinutes = remindMinutes;

        FormBorderStyle = FormBorderStyle.FixedToolWindow;
        Text = "MPP Assistant";
        ShowInTaskbar = false;
        TopMost = true;
        StartPosition = FormStartPosition.Manual;
        BackColor = Color.White;
        Width = 380;

        const int pad = 12;
        var contentWidth = Width - pad * 2;

        // Title and body auto-size and WRAP to the full text (no truncation — you can read everything).
        var title = new Label
        {
            Text = rec.Title,
            Font = new Font(Font.FontFamily, 10f, FontStyle.Bold),
            AutoSize = true,
            MaximumSize = new Size(contentWidth, 0),
            Location = new Point(pad, pad),
        };
        Controls.Add(title);

        var why = new Label
        {
            Text = string.IsNullOrWhiteSpace(rec.Why) ? "" : rec.Why,
            AutoSize = true,
            MaximumSize = new Size(contentWidth, 0),
            ForeColor = Color.DimGray,
            Location = new Point(pad, title.Bottom + 6),
        };
        Controls.Add(why);

        var buttons = new FlowLayoutPanel
        {
            Location = new Point(pad - 3, why.Bottom + 8),
            Width = contentWidth + 6,
            AutoSize = true,
            WrapContents = true,
            FlowDirection = FlowDirection.LeftToRight,
        };
        var defs = rec.Buttons.Count > 0 ? rec.Buttons : new List<SuggestedButton> { new("Dismiss", "dismiss") };
        foreach (var b in defs)
        {
            var captured = b;
            var button = new Button { Text = b.Label, AutoSize = true, Margin = new Padding(3) };
            button.Click += (_, _) => OnButton(captured);
            buttons.Controls.Add(button);
        }
        Controls.Add(buttons);

        // Fit the card to its content so long suggestions aren't cut off.
        Height = buttons.Bottom + pad + 6;

        PositionBottomRight(stackIndex);
    }

    /// <summary>Lets the tray re-stack this card after another one closes (no empty gaps).</summary>
    public void SetLocation(int x, int y) => Location = new Point(x, y);

    private void OnButton(SuggestedButton b)
    {
        try { _log.AppendAction(_rec.Id, b.Kind, DateTimeOffset.UtcNow); } catch { }

        if (b.Kind == "remind")
        {
            ScheduleRemind();
            Close();
            return;
        }
        try { ActionRunner.Run(b, _rec); } catch { /* opening/clipboard can fail; ignore */ }
        Close();
    }

    private void ScheduleRemind()
    {
        var t = new System.Windows.Forms.Timer { Interval = Math.Max(60_000, (int)(_remindMinutes * 60_000)) };
        var rec = _rec;
        var log = _log;
        var remind = _remindMinutes;
        t.Tick += (_, _) =>
        {
            t.Stop();
            t.Dispose();
            new NotificationCard(rec, log, remind, 0).Show();
        };
        t.Start();
    }

    private void PositionBottomRight(int stackIndex)
    {
        var wa = Screen.PrimaryScreen?.WorkingArea ?? new Rectangle(0, 0, 1024, 768);
        var x = wa.Right - Width - 12;
        var y = wa.Bottom - Height - 12 - stackIndex * (Height + 10);
        if (y < wa.Top + 10) y = wa.Top + 10;
        Location = new Point(x, y);
    }
}
