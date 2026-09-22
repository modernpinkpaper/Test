using MppWatcher.Core.Collectors;
using MppWatcher.Core.Configuration;
using MppWatcher.Core.Diagnostics;
using MppWatcher.Core.Events;
using MppWatcher.Core.Processes;

namespace MppWatcher.Core.Tests;

public class ProcessTrackerTests
{
    private readonly ProcessCollectorConfig _cfg = new();

    private static ProcessInfo P(int pid, string name, bool window = true) => new(pid, name, T.Start.AddHours(-1), null, name, window);

    [Fact]
    public void Baseline_returns_inventory_without_changes_and_ignores_noise()
    {
        var t = new ProcessTracker(() => _cfg);
        var (inv, changes) = t.Update(new[] { P(1, "chrome"), P(2, "svchost"), P(3, "EXCEL") }, T.Start);
        Assert.Equal(new[] { "chrome", "EXCEL" }, inv.Select(p => p.Name));
        Assert.Empty(changes);
    }

    [Fact]
    public void Reports_starts_and_exits_with_run_time()
    {
        var t = new ProcessTracker(() => _cfg);
        t.Update(new[] { P(1, "chrome") }, T.Start);
        var (_, c1) = t.Update(new[] { P(1, "chrome"), P(5, "python", window: false) }, T.Start.AddMinutes(1));
        var started = Assert.IsType<ProcessChange.Started>(Assert.Single(c1));
        Assert.Equal("python", started.Process.Name);

        var (_, c2) = t.Update(new[] { P(1, "chrome") }, T.Start.AddMinutes(2));
        var exited = Assert.IsType<ProcessChange.Exited>(Assert.Single(c2));
        Assert.Equal("python", exited.Process.Name);
        Assert.Equal(TimeSpan.FromMinutes(62), exited.Lifetime);
    }

    [Fact]
    public void Multi_instance_apps_are_collapsed()
    {
        var t = new ProcessTracker(() => _cfg);
        t.Update(Array.Empty<ProcessInfo>(), T.Start);
        var (_, c1) = t.Update(new[] { P(1, "chrome"), P(2, "chrome"), P(3, "chrome") }, T.Start);
        Assert.Single(c1);
        var (_, c2) = t.Update(new[] { P(1, "chrome") }, T.Start); // helpers closed
        Assert.Empty(c2);
        var (_, c3) = t.Update(Array.Empty<ProcessInfo>(), T.Start);
        Assert.IsType<ProcessChange.Exited>(Assert.Single(c3));
    }

    [Fact]
    public void Pid_reuse_is_seen_as_a_new_process()
    {
        _cfg.CollapseMultiInstance = false;
        var t = new ProcessTracker(() => _cfg);
        t.Update(new[] { P(7, "node") }, T.Start);
        var (_, changes) = t.Update(new[] { new ProcessInfo(7, "node", T.Start.AddMinutes(1)) }, T.Start.AddMinutes(2));
        Assert.Equal(2, changes.Count);
    }

    private sealed class FakeSource : IProcessSource
    {
        public List<ProcessInfo> Current = new();
        public IReadOnlyList<ProcessInfo> Snapshot() => Current.ToList();
    }

    private sealed class ListSink : IEventSink
    {
        public readonly List<WatchEvent> Events = new();
        public void Emit(WatchEvent e) => Events.Add(e);
    }

    [Fact]
    public void Collector_emits_inventory_then_changes()
    {
        var src = new FakeSource { Current = { P(1, "chrome") } };
        var sink = new ListSink();
        var c = new ProcessCollector(src);
        c.Start(new CollectorContext(sink, new ConfigProvider(new WatcherConfig()), NullDiagnosticLog.Instance, new FakeClock(T.Start)));
        src.Current.Add(P(9, "Photoshop"));
        c.Scan();
        c.Stop("test");

        Assert.Equal(EventTypes.ProcessInventory, sink.Events[0].EventType);
        Assert.Equal(EventTypes.ProcessStarted, sink.Events[1].EventType);
        Assert.Equal("Photoshop", sink.Events[1].ProcessName);
        Assert.False(sink.Events[1].Metadata["foreground"]!.GetValue<bool>());
    }
}
