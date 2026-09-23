using System.Globalization;
using MppWatcher.Core.Diagnostics;
using MppWatcher.Core.Events;
using MppWatcher.Core.Storage;

namespace MppWatcher.Core.Export;

public sealed record ExportResult(int Exported, int Failed, string? Error);

/// <summary>
/// Moves pending events from SQLite to an <see cref="ILogUploader"/>, grouped into hourly
/// files by employee and local date. Only marks events uploaded after the uploader succeeded.
/// </summary>
public sealed class ExportService
{
    private readonly IEventStore _store;
    private readonly ILogUploader _uploader;
    private readonly IDiagnosticLog _log;
    private readonly IClock _clock;
    private readonly SemaphoreSlim _running = new(1, 1);

    public ExportService(IEventStore store, ILogUploader uploader, IDiagnosticLog log, IClock clock)
    {
        _store = store;
        _uploader = uploader;
        _log = log;
        _clock = clock;
    }

    /// <summary>Exports everything pending, in batches. Safe to call from a timer; overlapping calls are skipped.</summary>
    public async Task<ExportResult> ExportPendingAsync(int batchSize, CancellationToken ct)
    {
        if (!await _running.WaitAsync(0, ct).ConfigureAwait(false)) return new ExportResult(0, 0, "export already running");
        var exported = 0;
        try
        {
            while (!ct.IsCancellationRequested)
            {
                var pending = _store.GetPending(batchSize);
                if (pending.Count == 0) break;
                var files = BuildFiles(pending.Select(p => p.Event));
                try
                {
                    await _uploader.UploadAsync(files, ct).ConfigureAwait(false);
                }
                catch (Exception e) when (e is not OperationCanceledException)
                {
                    _store.MarkUploadFailed(pending.Select(p => p.RowId), _clock.Now, e.Message);
                    _log.Warn("export", $"Upload via {_uploader.Name} failed for {pending.Count} events; will retry", e);
                    return new ExportResult(exported, pending.Count, e.Message);
                }
                _store.MarkUploaded(pending.Select(p => p.RowId), _clock.Now);
                exported += pending.Count;
                if (pending.Count < batchSize) break;
            }
            if (exported > 0) _log.Info("export", $"Exported {exported} events via {_uploader.Name}");
            return new ExportResult(exported, 0, null);
        }
        finally
        {
            _running.Release();
        }
    }

    /// <summary>
    /// Groups events into "{employee}/{yyyy-MM-dd}/events_HH00_HH00_{computer}.jsonl"
    /// using each event's own local time, ordered by time within each file.
    /// The computer name keeps files from two PCs apart, so a synced folder never has two writers per file.
    /// </summary>
    public static IReadOnlyList<ExportFile> BuildFiles(IEnumerable<WatchEvent> events)
    {
        return events
            .GroupBy(e => RelativePathFor(e))
            .OrderBy(g => g.Key, StringComparer.Ordinal)
            .Select(g => new ExportFile(g.Key, g.OrderBy(e => e.TimestampUtc).ThenBy(e => e.Sequence).Select(EventJson.Serialize).ToList()))
            .ToList();
    }

    public static string RelativePathFor(WatchEvent e)
    {
        var local = LocalTime(e);
        var employee = LocalFolderUploader.SafeSegment(string.IsNullOrWhiteSpace(e.EmployeeId) ? "unassigned" : e.EmployeeId);
        var next = (local.Hour + 1) % 24;
        var computer = string.IsNullOrWhiteSpace(e.ComputerId) ? "" : "_" + LocalFolderUploader.SafeSegment(e.ComputerId.Trim());
        return $"{employee}/{local:yyyy-MM-dd}/events_{local.Hour:00}00_{next:00}00{computer}.jsonl";
    }

    private static DateTimeOffset LocalTime(WatchEvent e) =>
        DateTimeOffset.TryParse(e.TimestampLocal, CultureInfo.InvariantCulture, DateTimeStyles.None, out var t)
            ? t
            : e.TimestampUtc.ToLocalTime();
}
