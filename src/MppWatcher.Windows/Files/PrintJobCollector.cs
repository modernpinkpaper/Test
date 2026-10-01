using System.Collections.Concurrent;
using System.Management;
using System.Text.Json.Nodes;
using MppWatcher.Core.Activity;
using MppWatcher.Core.Collectors;
using MppWatcher.Core.Diagnostics;
using MppWatcher.Core.Events;
using MppWatcher.Core.Files;

namespace MppWatcher.Windows.Files;

/// <summary>
/// Print jobs of the signed-in user, from the Windows print spooler through WMI:
/// print_job when a job is queued (printer, document name, pages) and print_job_finished when it
/// leaves the queue. Only job information is read, never the printed content.
/// </summary>
public sealed class PrintJobCollector : ICollector
{
    private readonly ActivityContext _activity;
    private readonly ConcurrentDictionary<string, (DateTimeOffset At, string? Application)> _open = new();
    // Last known error state per printer, so we only emit when it actually changes (WMI repeats).
    private readonly ConcurrentDictionary<string, int> _printerError = new(StringComparer.OrdinalIgnoreCase);
    private ManagementEventWatcher? _created, _deleted, _printerChange;
    private CollectorContext? _ctx;
    private long _jobs, _problems;

    public PrintJobCollector(ActivityContext activity) => _activity = activity;

    public string Name => "print";
    public string Version => "1.0.0";

    public void Start(CollectorContext context)
    {
        _ctx = context;
        var scope = new ManagementScope(@"\\.\root\cimv2");
        scope.Connect();
        _created = new ManagementEventWatcher(scope, new WqlEventQuery("__InstanceCreationEvent", TimeSpan.FromSeconds(1), "TargetInstance ISA 'Win32_PrintJob'"));
        _created.EventArrived += (_, e) => Handle(e, finished: false);
        _deleted = new ManagementEventWatcher(scope, new WqlEventQuery("__InstanceDeletionEvent", TimeSpan.FromSeconds(1), "TargetInstance ISA 'Win32_PrintJob'"));
        _deleted.EventArrived += (_, e) => Handle(e, finished: true);
        _created.Start();
        _deleted.Start();
        // Printer problems (out of paper, jam, offline, door open…): watch the printer device itself.
        // Guarded on its own so that if this query is unavailable, job logging still works.
        try
        {
            _printerChange = new ManagementEventWatcher(scope, new WqlEventQuery("__InstanceModificationEvent", TimeSpan.FromSeconds(5), "TargetInstance ISA 'Win32_Printer'"));
            _printerChange.EventArrived += (_, e) => HandlePrinterChange(e);
            _printerChange.Start();
        }
        catch (Exception e)
        {
            context.Log.Warn(Name, "Printer problem detection unavailable; print jobs still logged", e);
            _printerChange = null;
        }
    }

    public void Stop(string reason)
    {
        try { _created?.Stop(); _deleted?.Stop(); _printerChange?.Stop(); } catch { /* WMI already gone at shutdown */ }
        _created?.Dispose();
        _deleted?.Dispose();
        _printerChange?.Dispose();
    }

    public IReadOnlyDictionary<string, object> GetStats() => new Dictionary<string, object> { ["print_jobs"] = _jobs, ["printer_problems"] = _problems };

    private void Handle(EventArrivedEventArgs args, bool finished)
    {
        var ctx = _ctx;
        if (ctx is null) return;
        try
        {
            if (args.NewEvent["TargetInstance"] is not ManagementBaseObject job) return;
            var owner = job["Owner"]?.ToString();
            if (owner is not null && !owner.Equals(Environment.UserName, StringComparison.OrdinalIgnoreCase)) return; // other users' jobs
            var name = job["Name"]?.ToString() ?? "";          // "Printer Name, 12"
            var comma = name.LastIndexOf(',');
            var printer = comma > 0 ? name[..comma].Trim() : name;
            var jobId = job["JobId"]?.ToString() ?? name;
            var document = job["Document"]?.ToString();
            var now = ctx.Clock.Now;

            var e = this.NewEvent(finished ? EventTypes.PrintJobFinished : EventTypes.PrintJob, now);
            var m = e.Metadata;
            m["printer"] = printer;
            m["job_id"] = jobId;
            if (document is not null)
            {
                m["document_name"] = document;
                var skus = SkuFinder.Find(document, ctx.Config.Current.Collectors.Files.SkuPatterns);
                if (skus.Count > 0) m["sku_candidates"] = new JsonArray(skus.Select(s => (JsonNode)JsonValue.Create(s)!).ToArray());
            }
            AddNumber(m, "total_pages", job["TotalPages"]);
            AddNumber(m, "pages_printed", job["PagesPrinted"]);
            AddNumber(m, "size_bytes", job["Size"]);
            if (job["Status"]?.ToString() is { Length: > 0 } status) m["status"] = status;
            if (job["JobStatus"]?.ToString() is { Length: > 0 } jobStatus) m["job_status"] = jobStatus;
            // Flag a job that is stuck on a problem (paper out, jam, offline, error, paused…).
            if (JobProblem(job["Status"]?.ToString(), job["JobStatus"]?.ToString()) is { } jobProblem) m["problem"] = jobProblem;

            var key = printer + "|" + jobId;
            if (!finished)
            {
                // The app in front when the job was queued is almost always the one that printed.
                var app = _activity.CurrentApp;
                if (app is { } a)
                {
                    m["foreground_application"] = a.Application;
                    m["foreground_process"] = a.ProcessName;
                    e.SessionId = a.SessionId;
                }
                _open[key] = (now, app?.Application);
                _jobs++;
            }
            else if (_open.TryRemove(key, out var started))
            {
                m["seconds_in_queue"] = Math.Round((now - started.At).TotalSeconds, 1);
                if (started.Application is not null) m["foreground_application"] = started.Application;
            }
            ctx.Sink.Emit(e);
        }
        catch (Exception ex)
        {
            ctx.Log.Warn(Name, "Could not read a print job notification", ex);
        }
    }

    /// <summary>
    /// A printer's condition changed. Win32_Printer.DetectedErrorState tells us if it is out of paper,
    /// jammed, offline, etc. We only emit when the state actually changes (WMI repeats modifications),
    /// and we emit a "cleared" event when it goes back to normal so a report knows how long it was down.
    /// </summary>
    private void HandlePrinterChange(EventArrivedEventArgs args)
    {
        var ctx = _ctx;
        if (ctx is null) return;
        try
        {
            if (args.NewEvent["TargetInstance"] is not ManagementBaseObject p) return;
            var printer = p["Name"]?.ToString();
            if (string.IsNullOrEmpty(printer)) return;
            var state = p["DetectedErrorState"] is { } s && int.TryParse(s.ToString(), out var n) ? n : 0;

            var previous = _printerError.TryGetValue(printer, out var prev) ? prev : 2; // 2 = No Error
            if (state == previous) return; // nothing changed
            _printerError[printer] = state;

            var reason = DescribePrinterError(state);
            var ok = state is 0 or 2; // Unknown / No Error
            if (ok && !IsProblemState(previous)) return;     // was not a real problem, ignore the clear

            var e = this.NewEvent(EventTypes.PrinterProblem, ctx.Clock.Now);
            var m = e.Metadata;
            m["printer"] = printer;
            m["resolved"] = ok;
            m["reason"] = ok ? "cleared" : reason;
            if (!ok && _activity.CurrentApp is { } a) { m["foreground_application"] = a.Application; e.SessionId = a.SessionId; }
            if (!ok) _problems++;
            ctx.Sink.Emit(e);
        }
        catch (Exception ex)
        {
            ctx.Log.Warn(Name, "Could not read a printer status change", ex);
        }
    }

    private static bool IsProblemState(int state) => state is not (0 or 2);

    /// <summary>Win32_Printer.DetectedErrorState values, in plain words.</summary>
    private static string DescribePrinterError(int state) => state switch
    {
        3 => "Low paper",
        4 => "Out of paper",
        5 => "Low toner/ink",
        6 => "Out of toner/ink",
        7 => "Door open",
        8 => "Paper jam",
        9 => "Offline",
        10 => "Service requested",
        11 => "Output bin full",
        12 => "Paper problem",
        13 => "Cannot print page",
        14 => "Needs attention",
        15 => "Out of memory",
        16 => "Server unknown",
        _ => "Problem",
    };

    /// <summary>Spot a print job that is stuck on a problem from its status text.</summary>
    private static string? JobProblem(string? status, string? jobStatus)
    {
        var text = ((status ?? "") + " " + (jobStatus ?? "")).ToLowerInvariant();
        if (text.Contains("paper out") || text.Contains("no paper") || text.Contains("out of paper")) return "Out of paper";
        if (text.Contains("jam")) return "Paper jam";
        if (text.Contains("offline")) return "Offline";
        if (text.Contains("error")) return "Error";
        if (text.Contains("paused")) return "Paused";
        if (text.Contains("user intervention")) return "Needs attention";
        return null;
    }

    private static void AddNumber(JsonObject m, string key, object? value)
    {
        if (value is not null && long.TryParse(value.ToString(), out var n)) m[key] = n;
    }
}
