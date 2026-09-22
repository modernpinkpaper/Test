using System.Text;
using MppWatcher.Core.Configuration;
using MppWatcher.Core.Diagnostics;
using MppWatcher.Core.Events;
using MppWatcher.Core.Presentation;
using MppWatcher.Core.Storage;

namespace MppWatcher.App;

/// <summary>
/// Runs the real watcher (real Windows collectors) for a few seconds, then reports what was
/// captured. Used by CI on a Windows machine and by admins checking a new PC.
/// Exit code 0 = started, collected, stopped and wrote everything; 1 = something failed.
/// </summary>
internal static class SmokeTest
{
    public static int Run(string configPath, string? dataFolder, int seconds, string? resultPath, IDiagnosticLog log)
    {
        dataFolder ??= Path.Combine(Path.GetTempPath(), "MPPWatcher-smoke-" + DateTime.Now.ToString("yyyyMMdd-HHmmss"));
        var report = new StringBuilder();
        var ok = true;
        try
        {
            using var config = new ConfigProvider(configPath, log);
            var runtime = WatcherFactory.Create(config, dataFolder, log);
            runtime.Start(new Dictionary<string, object?> { ["mode"] = "smoke_test" });
            Thread.Sleep(TimeSpan.FromSeconds(seconds));
            var status = runtime.GetStatus();
            runtime.StopAsync("smoke_test_finished").Wait(TimeSpan.FromSeconds(20));

            using var store = new SqliteEventStore(runtime.Paths.DatabasePath, runtime.Paths.FallbackFolder, readOnly: true);
            var events = store.ReadAfter(0, 100_000).Select(r => r.Event).ToList();

            report.AppendLine($"MPP Watcher smoke test — ran {seconds}s");
            report.AppendLine($"Database: {runtime.Paths.DatabasePath}");
            report.AppendLine($"Memory at end: {status["memory_mb"]} MB, CPU total: {status["cpu_seconds_total"]} s");
            report.AppendLine();
            report.AppendLine("Event counts:");
            foreach (var g in events.GroupBy(e => e.EventType).OrderBy(g => g.Key)) report.AppendLine($"  {g.Key,-24} {g.Count()}");
            report.AppendLine();
            report.AppendLine("Events:");
            foreach (var e in events) report.AppendLine($"  {EventSummaryFormatter.LocalTimeText(e)}  {e.EventType,-22} {EventSummaryFormatter.Summarize(e)}");

            void Check(bool condition, string what)
            {
                report.AppendLine($"[{(condition ? "PASS" : "FAIL")}] {what}");
                ok &= condition;
            }
            report.AppendLine();
            Check(events.FirstOrDefault()?.EventType == EventTypes.WatcherStarted, "first event is watcher_started");
            Check(events.LastOrDefault()?.EventType == EventTypes.WatcherStopped, "last event is watcher_stopped");
            Check(!events.Any(e => e.EventType == EventTypes.CollectorStatus && e.Metadata["status"]?.GetValue<string>() != "running"),
                "no collector failed");
            Check(events.All(e => !string.IsNullOrEmpty(e.EventId) && !string.IsNullOrEmpty(e.ComputerId) && !string.IsNullOrEmpty(e.WindowsUsername)),
                "all events have ids and identity");
            var starts = events.Count(e => e.EventType == EventTypes.AppSessionStart);
            var ends = events.Count(e => e.EventType == EventTypes.AppSessionEnd);
            Check(starts == ends, $"every app session that started also ended ({starts} started, {ends} ended)");
            report.AppendLine(starts == 0
                ? "[INFO] No foreground window was seen (normal on a machine with no signed-in desktop, e.g. some CI runners)."
                : $"[INFO] {starts} foreground session(s) captured.");
        }
        catch (Exception e)
        {
            ok = false;
            report.AppendLine("[FAIL] smoke test crashed: " + e);
        }
        report.AppendLine(ok ? "RESULT: PASS" : "RESULT: FAIL");

        var text = report.ToString();
        resultPath ??= Path.Combine(dataFolder, "smoke-test-result.txt");
        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(resultPath))!);
            File.WriteAllText(resultPath, text);
        }
        catch { /* console output below still shows it */ }
        Program.WriteConsole(text);
        return ok ? 0 : 1;
    }
}
