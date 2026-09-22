using System.Diagnostics;
using MppWatcher.Core.Collectors;
using MppWatcher.Core.Configuration;
using MppWatcher.Core.Diagnostics;
using MppWatcher.Core.Events;
using MppWatcher.Core.Processes;
using Xunit.Abstractions;

namespace MppWatcher.Windows.Tests;

public sealed class ProcessCollectorTests
{
    private readonly ITestOutputHelper _out;
    public ProcessCollectorTests(ITestOutputHelper output) => _out = output;

    [Fact]
    public void Program_start_and_exit_are_detected()
    {
        var cfg = new WatcherConfig();
        cfg.Collectors.Process.ScanIntervalSeconds = 5;
        var sink = new ListSink();
        var collector = new ProcessCollector(new WindowsProcessSource());
        collector.Start(new CollectorContext(sink, new ConfigProvider(cfg), NullDiagnosticLog.Instance, SystemClock.Instance));
        try
        {
            var inventory = Assert.Single(sink.OfType(EventTypes.ProcessInventory));
            _out.WriteLine("Inventory: " + inventory.Metadata["processes"]!.ToJsonString());
            Assert.DoesNotContain("svchost", inventory.Metadata["processes"]!.ToJsonString(), StringComparison.OrdinalIgnoreCase);

            // A windowless script-like program.
            using var ping = Process.Start(new ProcessStartInfo("ping.exe", "-n 30 127.0.0.1") { CreateNoWindow = true, UseShellExecute = false })!;
            Assert.True(Desktop.WaitUntil(() => sink.OfType(EventTypes.ProcessStarted).Any(e => e.ProcessName == "PING" || e.ProcessName == "ping"),
                TimeSpan.FromSeconds(15)), "process_started not seen");
            Thread.Sleep(1000);
            ping.Kill();
            Assert.True(Desktop.WaitUntil(() => sink.OfType(EventTypes.ProcessExited).Any(e => string.Equals(e.ProcessName, "ping", StringComparison.OrdinalIgnoreCase)),
                TimeSpan.FromSeconds(15)), "process_exited not seen");

            var started = sink.OfType(EventTypes.ProcessStarted).First(e => string.Equals(e.ProcessName, "ping", StringComparison.OrdinalIgnoreCase));
            var exited = sink.OfType(EventTypes.ProcessExited).First(e => string.Equals(e.ProcessName, "ping", StringComparison.OrdinalIgnoreCase));
            Assert.EndsWith("ping.exe", started.Metadata["executable_path"]!.GetValue<string>(), StringComparison.OrdinalIgnoreCase);
            Assert.NotNull(started.Metadata["process_start"]);
            Assert.True(exited.Metadata["run_seconds"]!.GetValue<double>() > 0);
        }
        finally
        {
            collector.Stop("test");
            _out.WriteLine(sink.Dump());
        }
    }
}
