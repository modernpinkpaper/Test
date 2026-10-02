using System.Drawing;
using System.Drawing.Imaging;
using MppWatcher.Core.Capture;
using MppWatcher.Core.Configuration;
using MppWatcher.Core.Diagnostics;
using MppWatcher.Core.Export;
using MppWatcher.Core.Pipeline;
using MppWatcher.Core.Runtime;
using MppWatcher.Windows.Interop;

namespace MppWatcher.Windows.Ui;

/// <summary>
/// Saves a JPEG of the active window on each step, but ONLY while an SOP "Record Task" session is
/// recording (never otherwise). Images go next to that person's logs so they sync and can sit beside
/// the step in the SOP. Throttled so rapid clicks do not spam images.
/// </summary>
public sealed class SopScreenshotter
{
    private readonly Func<WatcherConfig> _config;
    private readonly WatcherIdentity _identity;
    private readonly string _localFallbackFolder;
    private readonly CaptureController _capture;
    private readonly IDiagnosticLog _log;
    private DateTime _lastShotUtc = DateTime.MinValue;
    private int _stepNo;

    public SopScreenshotter(Func<WatcherConfig> config, WatcherIdentity identity, string localFallbackFolder,
        CaptureController capture, IDiagnosticLog log)
    {
        _config = config; _identity = identity; _localFallbackFolder = localFallbackFolder; _capture = capture; _log = log;
    }

    /// <summary>If a SOP recording is active and screenshots are enabled, save one and return its file path (else null).</summary>
    public string? MaybeCapture()
    {
        var snap = _capture.Current;
        if (!snap.WantsScreenshots) return null;
        var cfg = _config();
        if (!cfg.Capture.SopScreenshots) return null;

        var now = DateTime.UtcNow;
        if ((now - _lastShotUtc).TotalMilliseconds < Math.Max(0, cfg.Capture.ScreenshotMinGapMs)) return null;

        try
        {
            var title = NativeMethods.GetWindowTitle(NativeMethods.GetForegroundWindow());
            var step = Interlocked.Increment(ref _stepNo);
            var caption = $"Step {step:0000}    {DateTime.Now:h:mm:ss tt}" + (string.IsNullOrWhiteSpace(title) ? "" : "    —  " + title);
            using var bmp = Grab(cfg.Capture.ScreenshotActiveWindowOnly, cfg.Capture.ScreenshotMaxWidth, caption);
            if (bmp is null) return null;
            var folder = TargetFolder(snap);
            Directory.CreateDirectory(folder);
            // Self-describing filename: step number + time + the window it was taken on.
            var file = Path.Combine(folder, $"step_{step:0000}_{now.ToLocalTime():HHmmss}_{SafeName(title)}.jpg");
            Save(bmp, file, cfg.Capture.ScreenshotQuality);
            _lastShotUtc = now;
            return file;
        }
        catch (Exception e)
        {
            _log.Warn("capture", "Screenshot failed", e);
            return null;
        }
    }

    private static Bitmap? Grab(bool activeWindowOnly, int maxWidth, string caption)
    {
        Rectangle rect;
        if (activeWindowOnly && NativeMethods.GetWindowRect(NativeMethods.GetForegroundWindow(), out var r)
            && r.Right > r.Left && r.Bottom > r.Top)
            rect = new Rectangle(r.Left, r.Top, r.Right - r.Left, r.Bottom - r.Top);
        else
        {
            var b = System.Windows.Forms.Screen.PrimaryScreen?.Bounds;
            if (b is null) return null;
            rect = b.Value;
        }
        var shot = new Bitmap(rect.Width, rect.Height);
        using (var g = Graphics.FromImage(shot))
        {
            g.CopyFromScreen(rect.Location, Point.Empty, rect.Size);
            DrawCursorHighlight(g, rect); // yellow circle at the mouse so you can see what was clicked
        }

        var final = shot;
        if (maxWidth > 0 && rect.Width > maxWidth)
        {
            var h = (int)(rect.Height * (maxWidth / (double)rect.Width));
            var small = new Bitmap(maxWidth, Math.Max(1, h));
            using (var g = Graphics.FromImage(small)) { g.InterpolationMode = System.Drawing.Drawing2D.InterpolationMode.HighQualityBicubic; g.DrawImage(shot, 0, 0, maxWidth, h); }
            shot.Dispose();
            final = small;
        }

        DrawCaption(final, caption); // after resize so the text stays crisp
        return final;
    }

    /// <summary>A soft transparent-yellow circle behind the mouse, so each screenshot shows where the click was.</summary>
    private static void DrawCursorHighlight(Graphics g, Rectangle rect)
    {
        if (!NativeMethods.GetCursorPos(out var cp)) return;
        int cx = cp.X - rect.Left, cy = cp.Y - rect.Top;
        if (cx < 0 || cy < 0 || cx >= rect.Width || cy >= rect.Height) return;
        g.SmoothingMode = System.Drawing.Drawing2D.SmoothingMode.AntiAlias;
        const int radius = 26;
        using var fill = new SolidBrush(Color.FromArgb(80, 255, 215, 0));   // see-through yellow
        g.FillEllipse(fill, cx - radius, cy - radius, radius * 2, radius * 2);
        using var ring = new Pen(Color.FromArgb(210, 240, 170, 0), 3f);
        g.DrawEllipse(ring, cx - radius, cy - radius, radius * 2, radius * 2);
    }

    /// <summary>Burn a small caption bar (step #, time, window) along the bottom so the image explains itself.</summary>
    private static void DrawCaption(Bitmap bmp, string caption)
    {
        if (string.IsNullOrWhiteSpace(caption)) return;
        using var g = Graphics.FromImage(bmp);
        using var font = new Font("Segoe UI", 9.5f, FontStyle.Bold);
        var textH = (int)Math.Ceiling(g.MeasureString("Ag", font).Height);
        var barH = textH + 8;
        var y = bmp.Height - barH;
        using var bg = new SolidBrush(Color.FromArgb(175, 0, 0, 0));
        g.FillRectangle(bg, 0, y, bmp.Width, barH);
        using var fmt = new StringFormat { FormatFlags = StringFormatFlags.NoWrap, Trimming = StringTrimming.EllipsisCharacter };
        g.DrawString(caption, font, Brushes.White, new RectangleF(6, y + 3, bmp.Width - 12, barH), fmt);
    }

    /// <summary>Make a window title safe + short for a file name.</summary>
    private static string SafeName(string? s)
    {
        if (string.IsNullOrWhiteSpace(s)) return "window";
        foreach (var c in Path.GetInvalidFileNameChars()) s = s!.Replace(c, ' ');
        s = s!.Replace("  ", " ").Trim();
        if (s.Length > 50) s = s[..50].Trim();
        return s.Length == 0 ? "window" : s;
    }

    private static void Save(Bitmap bmp, string path, int quality)
    {
        var jpg = ImageCodecInfo.GetImageEncoders().First(c => c.FormatID == ImageFormat.Jpeg.Guid);
        using var p = new EncoderParameters(1);
        p.Param[0] = new EncoderParameter(Encoder.Quality, (long)Math.Clamp(quality, 1, 100));
        bmp.Save(path, jpg, p);
    }

    /// <summary>Screenshots go beside the person's logs in the export folder; falls back to the local data folder.</summary>
    private string TargetFolder(CaptureSnapshot snap)
    {
        var cfg = _config();
        var label = EventNormalizer.ResolveEmployeeId(cfg, _identity.WindowsUsername, _identity.ComputerName);
        var sub = Path.Combine(LocalFolderUploader.SafeSegment(label), "_sop_screenshots",
            LocalFolderUploader.SafeSegment(snap.Label) + "_" + snap.SessionId[..8]);
        try { return Path.Combine(ExportDestination.Resolve(WatcherPaths.ExportFolder(cfg)), sub); }
        catch { return Path.Combine(_localFallbackFolder, "sop_screenshots", sub); }
    }
}
