using MppWatcher.Core.Collectors;
using MppWatcher.Core.Configuration;
using MppWatcher.Core.Diagnostics;
using MppWatcher.Core.Events;
using MppWatcher.Core.Pipeline;
using MppWatcher.Core.Runtime;
using MppWatcher.Core.Storage;

namespace MppWatcher.Core.Tests;

public class WatcherRuntimeTests : IDisposable
{
    private readonly TempDir _dir = new();
    public void Dispose() => _dir.Dispose();

    private sealed class FakeCollector : ICollector
    {
        public string Name => "fake";
        public string Version => "9.9.9";
        private CollectorContext? _ctx;
        public void Start(CollectorContext c)
        {
            _ctx = c;
            c.Sink.Emit(this.NewEvent(EventTypes.AppSessionStart, c.Clock.Now));
        }
        public void Stop(string reason) => _ctx!.Sink.Emit(this.NewEvent(EventTypes.AppSessionEnd, _ctx.Clock.Now).Set("end_reason", reason));
        public IReadOnlyDictionary<string, object> GetStats() => new Dictionary<string, object> { ["ticks"] = 5L, ["is_idle"] = false, ["count"] = 3 };
    }

    [Fact]
    public async Task Start_and_stop_write_lifecycle_events_in_order_and_export()
    {
        var cfg = new WatcherConfig { EmployeeId = "EMP1", DataFolder = Path.Combine(_dir.Path, "data") };
        cfg.Export.DestinationFolder = Path.Combine(_dir.Path, "export");
        var provider = new ConfigProvider(cfg);
        var paths = RuntimePaths.From(provider.Current);
        var runtime = new WatcherRuntime(provider, new MemoryDiagnosticLog(), SystemClock.Instance,
            new WatcherIdentity("PC", "OFFICE\\jane", "run1"), paths, _ => new ICollector[] { new FakeCollector() });

        runtime.Start();
        var status = runtime.GetStatus();
        Assert.Equal("running", status["collectors"]![0]!["state"]!.GetValue<string>());
        Assert.Equal(5L, status["collectors"]![0]!["ticks"]!.GetValue<long>());
        var heartbeat = new WatchEvent();
        foreach (var (k, v) in status) heartbeat.Metadata[k] = v?.DeepClone();
        Assert.Contains("\"is_idle\":false", EventJson.Serialize(heartbeat)); // stats serialize cleanly
        await Task.Delay(300); // let the writer flush
        var export = await runtime.ExportNowAsync();
        Assert.True(export.Exported >= 3, $"exported {export.Exported}");
        await runtime.StopAsync("test_stop");

        using var store = new SqliteEventStore(paths.DatabasePath, paths.FallbackFolder);
        var types = store.ReadAfter(0, 100).Select(r => r.Event.EventType).ToList();
        Assert.Equal(EventTypes.WatcherStarted, types[0]);
        Assert.Contains(EventTypes.CollectorStatus, types);
        Assert.Contains(EventTypes.AppSessionStart, types);
        Assert.Equal(EventTypes.AppSessionEnd, types[^2]);   // collector closed its session first
        Assert.Equal(EventTypes.WatcherStopped, types[^1]);
        Assert.All(store.ReadAfter(0, 100), r => Assert.Equal("EMP1", r.Event.EmployeeId));
        Assert.True(Directory.EnumerateFiles(Path.Combine(_dir.Path, "export"), "*.jsonl", SearchOption.AllDirectories).Any());
    }
}
