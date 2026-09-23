using System.Drawing.Drawing2D;

namespace MppWatcher.App;

/// <summary>Draws the tray / window icon at runtime (a medium-grey arrow), so no binary icon file is needed.</summary>
internal static class AppIcon
{
    private static Icon? _icon;

    // Medium grey, so the icon is plain and not tied to any brand colour.
    private static readonly Color ArrowColor = Color.FromArgb(128, 128, 128);

    public static Icon Get()
    {
        if (_icon is not null) return _icon;
        using var bmp = new Bitmap(32, 32);
        using (var g = Graphics.FromImage(bmp))
        {
            g.SmoothingMode = SmoothingMode.AntiAlias;
            using var pen = new Pen(ArrowColor, 4f) { StartCap = LineCap.Round, EndCap = LineCap.Round, LineJoin = LineJoin.Round };

            // A diagonal arrow pointing up and to the right: shaft plus a two-line head at the tip.
            var tail = new PointF(7, 25);
            var tip = new PointF(24, 8);
            g.DrawLine(pen, tail, tip);
            g.DrawLines(pen, new[] { new PointF(14, 8), tip, new PointF(24, 18) });
        }
        _icon = Icon.FromHandle(bmp.GetHicon());
        return _icon;
    }
}
