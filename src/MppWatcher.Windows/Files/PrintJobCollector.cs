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
    private ManagementEventWatcher? _created, _deleted;
    private CollectorContext? _ctx;
    private long _jobs;

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
    }

    public void Stop(string reason)
    {
        try { _created?.Stop(); _deleted?.Stop(); } catch { /* WMI already gone at shutdown */ }
        _created?.Dispose();
        _deleted?.Dispose();
    }

    public IReadOnlyDictionary<string, object> GetStats() => new Dictionary<string, object> { ["print_jobs"] = _jobs };

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

    private static void AddNumber(JsonObject m, string key, object? value)
    {
        if (value is not null && long.TryParse(value.ToString(), out var n)) m[key] = n;
    }
}
