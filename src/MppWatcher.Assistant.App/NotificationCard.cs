using System.Drawing;
using System.Windows.Forms;
using MppWatcher.Assistant;

namespace MppWatcher.Assistant.App;

/// <summary>
/// A small sticky card in the bottom-right corner showing one suggestion (title + why) and its buttons.
/// It stays until the user clicks something. Each click is recorded to the recommendations feedback log.
/// </summary>
internal sealed class NotificationCard : Form
{
    private readonly Recommendation _rec;
    private readonly RecommendationLog _log;
    private readonly double _remindMinutes;

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
        Width = 380;
        Height = 190;
        BackColor = Color.White;

        var title = new Label
        {
            Text = rec.Title,
            Font = new Font(Font.FontFamily, 10f, FontStyle.Bold),
            Dock = DockStyle.Top,
            Height = 46,
            Padding = new Padding(10, 8, 10, 0),
        };
        var why = new Label
        {
            Text = rec.Why,
            Dock = DockStyle.Top,
            Height = 66,
            Padding = new Padding(10, 0, 10, 0),
            ForeColor = Color.DimGray,
        };
        var buttons = new FlowLayoutPanel
        {
            Dock = DockStyle.Bottom,
            Height = 70,
            Padding = new Padding(6),
            WrapContents = true,
            FlowDirection = FlowDirection.LeftToRight,
        };

        var defs = rec.Buttons.Count > 0 ? rec.Buttons : new List<SuggestedButton> { new("Dismiss", "dismiss") };
        foreach (var b in defs)
        {
            var captured = b;
            var button = new Button { Text = b.Label, AutoSize = true, Margin = new Padding(4) };
            button.Click += (_, _) => OnButton(captured);
            buttons.Controls.Add(button);
        }

        Controls.Add(buttons);
        Controls.Add(why);
        Controls.Add(title);

        PositionBottomRight(stackIndex);
    }

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
