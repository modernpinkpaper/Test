using MppWatcher.Core.Collectors;
using MppWatcher.Core.Configuration;
using MppWatcher.Core.Diagnostics;
using MppWatcher.Core.Events;
using MppWatcher.Core.Pipeline;
using MppWatcher.Core.Storage;

namespace MppWatcher.Core.Tests;

public class NormalizerTests
{
    [Fact]
    public void Fills_identity_ids_and_timestamps()
    {
        var cfg = new WatcherConfig { EmployeeId = "EMP009", ComputerId = "PACKING-PC-2" };
        var n = new EventNormalizer(new WatcherIdentity("DESKTOP-1", "OFFICE\\jane", "run42"), () => cfg);
        var e = n.Normalize(new WatchEvent { EventType = "x" }, T.Start);
        Assert.NotEmpty(e.EventId);
        Assert.Equal("PACKING-PC-2", e.ComputerId);
        Assert.Equal("EMP009", e.EmployeeId);
        Assert.Equal("OFFICE\\jane", e.WindowsUsername);
        Assert.Equal("run42", e.WatcherRunId);
        Assert.Equal(TimeSpan.Zero, e.TimestampUtc.Offset);
        Assert.Equal(1, e.Sequence);
        Assert.Equal(2, n.Normalize(new WatchEvent(), T.Start).Sequence);
    }

    [Theory]
    [InlineData("OFFICE\\jane", "EMP001")]
    [InlineData("OTHERDOMAIN\\bob", "EMP002")]
    [InlineData("OFFICE\\carl", "DEFAULT")]
    public void Employee_id_mapping(string user, string expected)
    {
        var cfg = new WatcherConfig { EmployeeId = "DEFAULT" };
        cfg.EmployeeIdByWindowsUser["OFFICE\\jane"] = "EMP001";
        cfg.EmployeeIdByWindowsUser["bob"] = "EMP002";
        Assert.Equal(expected, EventNormalizer.ResolveEmployeeId(ConfigLoader.Validate(cfg), user));
    }

    [Fact]
    public void Missing_employee_id_is_obvious() =>
        Assert.Equal("unassigned-jane", EventNormalizer.ResolveEmployeeId(new WatcherConfig(), "OFFICE\\jane"));

    [Fact]
    public void Very_long_titles_are_trimmed()
    {
        var n = new EventNormalizer(new WatcherIdentity("PC", "u", "r"), () => new WatcherConfig());
        var e = n.Normalize(new WatchEvent { WindowTitle = new string('x', 5000) }, T.Start);
        Assert.True(e.WindowTitle!.Length <= EventNormalizer.MaxTextLength + 1);
    }
}

public class DuplicateSuppressorTests
{
    [Fact]
    public void Same_fingerprint_inside_window_is_dropped()
    {
        var d = new DuplicateSuppressor(() => TimeSpan.FromSeconds(10));
        var e = new WatchEvent { EventType = "ui_field_value", DedupFingerprint = "keepa|Search|stationery" };
        Assert.True(d.ShouldWrite(e, T.Start));
        Assert.False(d.ShouldWrite(e, T.Start.AddSeconds(5)));
        Assert.True(d.ShouldWrite(e, T.Start.AddSeconds(16)));
        Assert.True(d.ShouldWrite(new WatchEvent { EventType = "ui_field_value", DedupFingerprint = "other" }, T.Start.AddSeconds(16)));
        Assert.True(d.ShouldWrite(new WatchEvent { EventType = "x" }, T.Start)); // no fingerprint
        Assert.Equal(1, d.SuppressedCount);
    }
}

public class EventPipelineTests : IDisposable
{
    private readonly TempDir _dir = new();
    public void Dispose() => _dir.Dispose();

    [Fact]
    public async Task Events_flow_through_privacy_to_storage()
    {
        using var store = new SqliteEventStore(Path.Combine(_dir.Path, "e.db"), Path.Combine(_dir.Path, "fb"));
        var cfg = new ConfigProvider(new WatcherConfig { EmployeeId = "EMP1" });
        var pipeline = EventPipeline.Create(cfg, new WatcherIdentity("PC", "u", "r"), store, NullDiagnosticLog.Instance, new FakeClock(T.Start));

        pipeline.Emit(new WatchEvent { EventType = "app_session_start", ProcessName = "chrome", WindowTitle = "Keepa" });
        pipeline.Emit(new WatchEvent { EventType = "app_session_start", ProcessName = "KeePass", WindowTitle = "secrets.kdbx" });
        await pipeline.DisposeAsync();

        var rows = store.ReadAfter(0, 10);
        Assert.Equal(2, rows.Count);
        Assert.Equal("Keepa", rows[0].Event.WindowTitle);
        Assert.Equal("[excluded]", rows[1].Event.WindowTitle);
        Assert.Equal(2, pipeline.WrittenCount);
    }

    [Fact]
    public async Task Database_failure_goes_to_fallback_file()
    {
        var store = new BrokenStore(Path.Combine(_dir.Path, "fb"));
        var pipeline = EventPipeline.Create(new ConfigProvider(new WatcherConfig()), new WatcherIdentity("PC", "u", "r"), store, NullDiagnosticLog.Instance, new FakeClock(T.Start));
        pipeline.Emit(new WatchEvent { EventType = "x" });
        await pipeline.DisposeAsync();
        Assert.Equal(1, pipeline.WriteFailureCount);
        Assert.Equal(1, store.FallbackCount);
    }

    private sealed class BrokenStore : IEventStore
    {
        public BrokenStore(string _) { }
        public int FallbackCount;
        public void Append(IReadOnlyList<WatchEvent> events) => throw new IOException("disk full");
        public void WriteFallback(IReadOnlyList<WatchEvent> events) => FallbackCount += events.Count;
        public IReadOnlyList<StoredEvent> GetPending(int limit) => Array.Empty<StoredEvent>();
        public void MarkUploaded(IEnumerable<long> rowIds, DateTimeOffset when) { }
        public void MarkUploadFailed(IEnumerable<long> rowIds, DateTimeOffset when, string error) { }
        public IReadOnlyList<StoredEvent> ReadAfter(long afterRowId, int limit) => Array.Empty<StoredEvent>();
        public int DeleteUploadedBefore(DateTimeOffset cutoff) => 0;
        public StoreStats GetStats() => new(0, 0, 0, 0, null);
        public int ImportFallback() => 0;
        public void Dispose() { }
    }
}

public class CollectorHostTests
{
    private sealed class ListSink : IEventSink
    {
        public readonly List<WatchEvent> Events = new();
        public void Emit(WatchEvent e) { lock (Events) Events.Add(e); }
    }

    private sealed class GoodCollector : ICollector
    {
        public string Name => "good";
        public string Version => "1";
        public bool Running;
        public void Start(CollectorContext c) => Running = true;
        public void Stop(string reason) => Running = false;
    }

    private sealed class BadCollector : ICollector
    {
        public string Name => "bad";
        public string Version => "1";
        public int Attempts;
        public void Start(CollectorContext c) { Attempts++; throw new InvalidOperationException("UI Automation unavailable"); }
        public void Stop(string reason) { }
    }

    [Fact]
    public void One_failing_collector_does_not_stop_the_others()
    {
        var sink = new ListSink();
        var log = new MemoryDiagnosticLog();
        var host = new CollectorHost(new CollectorContext(sink, new ConfigProvider(new WatcherConfig()), log, new FakeClock(T.Start)));
        var bad = new BadCollector();
        var good = new GoodCollector();
        host.Add(bad);
        host.Add(good);

        host.StartAll();

        Assert.True(good.Running);
        Assert.Equal(1, bad.Attempts);
        Assert.Contains(host.Status, s => s.Name == "bad" && s.State == CollectorState.Failed);
        Assert.Contains(host.Status, s => s.Name == "good" && s.State == CollectorState.Running);
        Assert.Contains(sink.Events, e => e.EventType == EventTypes.CollectorStatus && e.Metadata["status"]!.GetValue<string>() == "failed");
        Assert.Contains(log.Lines, l => l.Contains("UI Automation unavailable"));

        host.StopAll("test");
        Assert.False(good.Running);
    }

    [Fact]
    public void Runtime_failure_is_reported_and_collector_is_stopped()
    {
        var sink = new ListSink();
        var host = new CollectorHost(new CollectorContext(sink, new ConfigProvider(new WatcherConfig()), NullDiagnosticLog.Instance, new FakeClock(T.Start)));
        var good = new GoodCollector();
        host.Add(good);
        host.StartAll();
        host.ReportFailure(good, new Exception("hook lost"));
        Assert.False(good.Running);
        Assert.Contains(host.Status, s => s.State == CollectorState.Failed && s.Restarts == 1);
        host.StopAll("test");
    }
}
