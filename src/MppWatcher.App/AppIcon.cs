using System.Drawing.Drawing2D;

namespace MppWatcher.App;

/// <summary>Draws the tray / window icon at runtime (a rounded "M" badge), so no binary icon file is needed.</summary>
internal static class AppIcon
{
    private static Icon? _icon;

    public static Icon Get()
    {
        if (_icon is not null) return _icon;
        using var bmp = new Bitmap(32, 32);
        using (var g = Graphics.FromImage(bmp))
        {
            g.SmoothingMode = SmoothingMode.AntiAlias;
            g.TextRenderingHint = System.Drawing.Text.TextRenderingHint.AntiAliasGridFit;
            using var path = new GraphicsPath();
            path.AddArc(0, 0, 12, 12, 180, 90);
            path.AddArc(19, 0, 12, 12, 270, 90);
            path.AddArc(19, 19, 12, 12, 0, 90);
            path.AddArc(0, 19, 12, 12, 90, 90);
            path.CloseFigure();
            using var fill = new SolidBrush(Color.FromArgb(214, 51, 132));
            g.FillPath(fill, path);
            using var font = new Font("Segoe UI", 16, FontStyle.Bold, GraphicsUnit.Pixel);
            var size = g.MeasureString("M", font);
            g.DrawString("M", font, Brushes.White, (32 - size.Width) / 2, (32 - size.Height) / 2);
        }
        _icon = Icon.FromHandle(bmp.GetHicon());
        return _icon;
    }
}
