using MppWatcher.Core.Configuration;
using MppWatcher.Core.Diagnostics;
using MppWatcher.Core.Events;
using MppWatcher.Core.Export;
using MppWatcher.Core.Pipeline;
using MppWatcher.Core.Storage;

namespace MppWatcher.Core.Tests;

public sealed class TempDir : IDisposable
{
    public TempDir() => Directory.CreateDirectory(Path);
    public string Path { get; } = System.IO.Path.Combine(System.IO.Path.GetTempPath(), "mppw-" + Guid.NewGuid().ToString("N"));
    public void Dispose() { try { Directory.Delete(Path, true); } catch { } }
}

public class SqliteEventStoreTests : IDisposable
{
    private readonly TempDir _dir = new();
    private readonly SqliteEventStore _store;
    private readonly EventNormalizer _normalizer;

    public SqliteEventStoreTests()
    {
        _store = new SqliteEventStore(Path.Combine(_dir.Path, "events.db"), Path.Combine(_dir.Path, "fallback"));
        _normalizer = new EventNormalizer(new WatcherIdentity("PC1", "OFFICE\\jane", "run1"), () => new WatcherConfig { EmployeeId = "EMP001" });
    }

    public void Dispose() { _store.Dispose(); _dir.Dispose(); }

    private WatchEvent Make(string type, DateTimeOffset at) =>
        _normalizer.Normalize(new WatchEvent { EventType = type, Application = "Chrome", TimestampUtc = at, Collector = "test" }, at);

    [Fact]
    public void Append_and_read_back_round_trips_all_fields()
    {
        var e = Make(EventTypes.AppSessionStart, T.Start).Set("value", "personalized stationery");
        _store.Append(new[] { e });
        var back = Assert.Single(_store.ReadAfter(0, 10)).Event;
        Assert.Equal(e.EventId, back.EventId);
        Assert.Equal("EMP001", back.EmployeeId);
        Assert.Equal("personalized stationery", back.Metadata["value"]!.GetValue<string>());
        Assert.Equal(T.Start.ToUniversalTime(), back.TimestampUtc);
    }

    [Fact]
    public void Duplicate_event_ids_are_stored_once()
    {
        var e = Make(EventTypes.IdleStart, T.Start);
        _store.Append(new[] { e });
        _store.Append(new[] { e });
        Assert.Equal(1, _store.GetStats().Total);
    }

    [Fact]
    public void Upload_tracking_marks_and_counts()
    {
        _store.Append(Enumerable.Range(0, 5).Select(i => Make(EventTypes.IdleStart, T.Start.AddMinutes(i))).ToList());
        var pending = _store.GetPending(3);
        Assert.Equal(3, pending.Count);

        _store.MarkUploadFailed(pending.Select(p => p.RowId), T.Start, "network down");
        Assert.Equal(1, _store.GetPending(1)[0].RetryCount);
        Assert.Equal(3, _store.GetStats().Failed);

        _store.MarkUploaded(pending.Select(p => p.RowId), T.Start);
        var stats = _store.GetStats();
        Assert.Equal(2, stats.Pending);
        Assert.Equal(3, stats.Uploaded);
    }

    [Fact]
    public void Retention_deletes_only_uploaded_old_events()
    {
        _store.Append(new[] { Make(EventTypes.IdleStart, T.Start.AddDays(-40)), Make(EventTypes.IdleEnd, T.Start.AddDays(-40)), Make(EventTypes.IdleStart, T.Start) });
        var all = _store.GetPending(10);
        _store.MarkUploaded(new[] { all[0].RowId, all[2].RowId }, T.Start);

        Assert.Equal(1, _store.DeleteUploadedBefore(T.Start.AddDays(-30)));
        var stats = _store.GetStats();
        Assert.Equal(2, stats.Total);
        Assert.Equal(1, stats.Pending); // the old but never-uploaded event is kept
    }

    [Fact]
    public void Fallback_file_is_imported_back()
    {
        var e = Make(EventTypes.IdleStart, T.Start);
        _store.WriteFallback(new[] { e });
        Assert.Equal(0, _store.GetStats().Total);
        Assert.Equal(1, _store.ImportFallback());
        Assert.Equal(1, _store.GetStats().Total);
        Assert.Equal(0, _store.ImportFallback());
    }

    [Fact]
    public void Viewer_can_read_while_watcher_writes()
    {
        _store.Append(new[] { Make(EventTypes.IdleStart, T.Start) });
        using var reader = new SqliteEventStore(_store.DatabasePath, "", readOnly: true);
        var first = Assert.Single(reader.ReadLatest(10));
        _store.Append(new[] { Make(EventTypes.IdleEnd, T.Start) });
        Assert.Equal(EventTypes.IdleEnd, Assert.Single(reader.ReadAfter(first.RowId, 10)).Event.EventType);
    }
}

public class ExportTests : IDisposable
{
    private readonly TempDir _dir = new();
    public void Dispose() => _dir.Dispose();

    private static WatchEvent At(string local, string employee = "EMP001", string computer = "PC-01") => new()
    {
        EventId = Guid.NewGuid().ToString("N"),
        ComputerId = computer,
        EventType = EventTypes.IdleStart,
        EmployeeId = employee,
        TimestampLocal = local,
        TimestampUtc = DateTimeOffset.Parse(local).ToUniversalTime(),
    };

    [Fact]
    public void Files_are_grouped_by_employee_date_and_hour()
    {
        var files = ExportService.BuildFiles(new[]
        {
            At("2026-09-22T09:15:00.000-04:00"), At("2026-09-22T09:59:59.000-04:00"),
            At("2026-09-22T10:00:00.000-04:00"), At("2026-09-22T23:30:00.000-04:00"),
            At("2026-09-22T09:10:00.000-04:00", "EMP/002"),
        });
        var paths = files.Select(f => f.RelativePath).ToList();
        Assert.Contains("EMP001/2026-09-22/events_0900_1000_PC-01.jsonl", paths);
        Assert.Contains("EMP001/2026-09-22/events_1000_1100_PC-01.jsonl", paths);
        Assert.Contains("EMP001/2026-09-22/events_2300_0000_PC-01.jsonl", paths);
        Assert.Contains("EMP_002/2026-09-22/events_0900_1000_PC-01.jsonl", paths);
        Assert.Equal(2, files.Single(f => f.RelativePath == "EMP001/2026-09-22/events_0900_1000_PC-01.jsonl").JsonLines.Count);
    }

    [Fact]
    public void Each_computer_gets_its_own_file_so_synced_folders_never_conflict()
    {
        var files = ExportService.BuildFiles(new[]
        {
            At("2026-09-22T09:15:00.000-04:00", computer: "FRONT-DESK"),
            At("2026-09-22T09:20:00.000-04:00", computer: "WAREHOUSE:2"),
            At("2026-09-22T09:25:00.000-04:00", computer: ""),
        });
        Assert.Equal(new[]
        {
            "EMP001/2026-09-22/events_0900_1000.jsonl",
            "EMP001/2026-09-22/events_0900_1000_FRONT-DESK.jsonl",
            "EMP001/2026-09-22/events_0900_1000_WAREHOUSE_2.jsonl",
        }, files.Select(f => f.RelativePath));
    }

    [Fact]
    public async Task Export_writes_files_and_marks_uploaded()
    {
        using var store = new SqliteEventStore(Path.Combine(_dir.Path, "events.db"), Path.Combine(_dir.Path, "fb"));
        store.Append(new[] { At("2026-09-22T09:15:00.000-04:00"), At("2026-09-22T09:16:00.000-04:00") });
        var root = Path.Combine(_dir.Path, "out");
        var svc = new ExportService(store, new LocalFolderUploader(root), NullDiagnosticLog.Instance, new FakeClock(T.Start));

        var r = await svc.ExportPendingAsync(1, CancellationToken.None); // batch size 1 → loops
        Assert.Equal(2, r.Exported);
        var file = Path.Combine(root, "EMP001", "2026-09-22", "events_0900_1000_PC-01.jsonl");
        Assert.Equal(2, File.ReadAllLines(file).Length);
        Assert.Equal(0, store.GetStats().Pending);
        Assert.Contains("\"event_type\":\"idle_start\"", File.ReadAllText(file));
    }

    [Fact]
    public async Task Failed_upload_keeps_events_pending_with_retry_count()
    {
        using var store = new SqliteEventStore(Path.Combine(_dir.Path, "events.db"), Path.Combine(_dir.Path, "fb"));
        store.Append(new[] { At("2026-09-22T09:15:00.000-04:00") });
        var svc = new ExportService(store, new FailingUploader(), NullDiagnosticLog.Instance, new FakeClock(T.Start));

        var r = await svc.ExportPendingAsync(100, CancellationToken.None);
        Assert.Equal(1, r.Failed);
        var p = Assert.Single(store.GetPending(10));
        Assert.Equal(1, p.RetryCount);
    }

    private sealed class FailingUploader : ILogUploader
    {
        public string Name => "failing";
        public Task UploadAsync(IReadOnlyList<ExportFile> files, CancellationToken ct) => throw new IOException("network path not found");
    }
}
