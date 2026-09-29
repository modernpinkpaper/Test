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
            using var bmp = Grab(cfg.Capture.ScreenshotActiveWindowOnly, cfg.Capture.ScreenshotMaxWidth);
            if (bmp is null) return null;
            var folder = TargetFolder(snap);
            Directory.CreateDirectory(folder);
            var file = Path.Combine(folder, $"step_{Interlocked.Increment(ref _stepNo):0000}_{now:HHmmss_fff}.jpg");
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

    private static Bitmap? Grab(bool activeWindowOnly, int maxWidth)
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
        using (var g = Graphics.FromImage(shot)) g.CopyFromScreen(rect.Location, Point.Empty, rect.Size);
        if (maxWidth > 0 && rect.Width > maxWidth)
        {
            var h = (int)(rect.Height * (maxWidth / (double)rect.Width));
            var small = new Bitmap(maxWidth, Math.Max(1, h));
            using (var g = Graphics.FromImage(small)) { g.InterpolationMode = System.Drawing.Drawing2D.InterpolationMode.HighQualityBicubic; g.DrawImage(shot, 0, 0, maxWidth, h); }
            shot.Dispose();
            return small;
        }
        return shot;
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
