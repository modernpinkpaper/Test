using System.Text;
using MppWatcher.Core.Capture;
using MppWatcher.Core.Configuration;
using MppWatcher.Core.Diagnostics;
using MppWatcher.Core.Events;
using MppWatcher.Core.Runtime;

namespace MppWatcher.Windows.Ui;

/// <summary>
/// While a "Record Task" session is recording, saves a copy of exactly the MT Log events from that
/// session (start → stop) into the same per-session folder as its screenshots, as BOTH:
///   • session_log.jsonl — the raw events, one JSON per line (for re-analysis / the AI).
///   • session_log.txt    — a readable one-line-per-event timeline (for a person to skim).
/// This way the screenshots and the exact log slice that produced them live together.
/// </summary>
public sealed class SopSessionLog : IDisposable
{
    private readonly Func<WatcherConfig> _config;
    private readonly WatcherIdentity _identity;
    private readonly string _localFallbackFolder;
    private readonly CaptureController _capture;
    private readonly IDiagnosticLog _log;

    private readonly object _gate = new();
    private StreamWriter? _jsonl;
    private StreamWriter? _txt;
    private int _count;

    public SopSessionLog(Func<WatcherConfig> config, WatcherIdentity identity, string localFallbackFolder,
        CaptureController capture, IDiagnosticLog log)
    {
        _config = config; _identity = identity; _localFallbackFolder = localFallbackFolder; _capture = capture; _log = log;
        _capture.Started += OnStarted;
        _capture.Stopped += OnStopped;
        _capture.EventTagged += OnEventTagged;
    }

    private void OnStarted(CaptureSnapshot snap)
    {
        lock (_gate)
        {
            Close(); // never leak a writer from a previous session
            try
            {
                var folder = SopPaths.SessionFolder(_config(), _identity, _localFallbackFolder, snap);
                Directory.CreateDirectory(folder);
                _jsonl = new StreamWriter(Path.Combine(folder, "session_log.jsonl"), append: false, Encoding.UTF8) { AutoFlush = true };
                _txt = new StreamWriter(Path.Combine(folder, "session_log.txt"), append: false, Encoding.UTF8) { AutoFlush = true };
                _count = 0;
                _txt.WriteLine($"# MT Log slice for \"{snap.Label}\"  (session {snap.SessionId[..8]})");
                _txt.WriteLine($"# started {DateTime.Now:yyyy-MM-dd h:mm:ss tt}");
                _txt.WriteLine();
            }
            catch (Exception e)
            {
                _log.Warn("capture", "Could not open session log files", e);
                Close();
            }
        }
    }

    private void OnEventTagged(WatchEvent e, CaptureSnapshot snap)
    {
        lock (_gate)
        {
            if (_jsonl is null || _txt is null) return;
            try
            {
                _jsonl.WriteLine(EventJson.Serialize(e));
                _txt.WriteLine(Readable(e));
                _count++;
            }
            catch (Exception ex)
            {
                _log.Warn("capture", "Could not write a session log line", ex);
            }
        }
    }

    private void OnStopped(CaptureSnapshot snap)
    {
        lock (_gate)
        {
            try
            {
                _txt?.WriteLine();
                _txt?.WriteLine($"# stopped {DateTime.Now:yyyy-MM-dd h:mm:ss tt} — {_count} events");
            }
            catch { /* best effort */ }
            Close();
        }
    }

    /// <summary>A compact, human-readable one-liner for the .txt timeline.</summary>
    private static string Readable(WatchEvent e)
    {
        var time = !string.IsNullOrWhiteSpace(e.TimestampLocal)
            ? e.TimestampLocal
            : e.TimestampUtc.ToLocalTime().ToString("h:mm:ss tt");

        var parts = new List<string>();
        var app = e.Application ?? e.ProcessName;
        if (!string.IsNullOrWhiteSpace(app)) parts.Add(app!);
        if (!string.IsNullOrWhiteSpace(e.WindowTitle)) parts.Add($"\"{e.WindowTitle}\"");
        if (!string.IsNullOrWhiteSpace(e.Url)) parts.Add(e.Url!);

        // A few metadata fields that make an event legible (clicked control, typed value, etc.).
        foreach (var key in new[] { "control_name", "control_type", "value", "field", "document_name", "printer", "job_id" })
            if (e.Metadata.TryGetPropertyValue(key, out var v) && v is not null)
            {
                var s = v.ToString();
                if (!string.IsNullOrWhiteSpace(s)) parts.Add($"{key}={s}");
            }

        var detail = parts.Count > 0 ? "  " + string.Join("  |  ", parts) : "";
        return $"{time}  {e.EventType}{detail}";
    }

    private void Close()
    {
        try { _jsonl?.Dispose(); } catch { }
        try { _txt?.Dispose(); } catch { }
        _jsonl = null; _txt = null;
    }

    public void Dispose()
    {
        _capture.Started -= OnStarted;
        _capture.Stopped -= OnStopped;
        _capture.EventTagged -= OnEventTagged;
        lock (_gate) Close();
    }
}
