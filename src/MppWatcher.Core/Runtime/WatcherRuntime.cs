using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text.Json.Nodes;
using MppWatcher.Core.Collectors;
using MppWatcher.Core.Configuration;
using MppWatcher.Core.Diagnostics;
using MppWatcher.Core.Events;
using MppWatcher.Core.Export;
using MppWatcher.Core.Pipeline;
using MppWatcher.Core.Storage;

namespace MppWatcher.Core.Runtime;

/// <summary>Resolved folders for one run.</summary>
public sealed record RuntimePaths(string DataFolder, string LogFolder, string DatabasePath, string CheckpointPath, string FallbackFolder, string ExportFolder)
{
    public static RuntimePaths From(WatcherConfig c, string? dataFolderOverride = null)
    {
        var data = string.IsNullOrWhiteSpace(dataFolderOverride) ? WatcherPaths.DataFolder(c) : dataFolderOverride;
        return new RuntimePaths(data, WatcherPaths.LogFolder(c), Path.Combine(data, "events.db"), Path.Combine(data, "open-session.json"),
            Path.Combine(data, "fallback"), WatcherPaths.ExportFolder(c));
    }
}

/// <summary>
/// Wires the watcher together and runs it: storage → pipeline → collectors, plus the
/// heartbeat, export and retention timers. The Windows app creates one of these and
/// supplies the Windows collectors; tests supply fake ones.
/// </summary>
public sealed class WatcherRuntime : IAsyncDisposable
{
    private readonly ConfigProvider _config;
    private readonly IDiagnosticLog _log;
    private readonly IClock _clock;
    private readonly Func<RuntimeServices, IEnumerable<ICollector>> _collectorFactory;
    private readonly Stopwatch _uptime = new();
    private readonly CancellationTokenSource _cts = new();
    private readonly object _stopGate = new();
    private SqliteEventStore? _store;
    private EventPipeline? _pipeline;
    private CollectorHost? _host;
    private ExportService? _export;
    private Timer? _heartbeatTimer, _exportTimer, _retentionTimer;
    private bool _stopped;

    public WatcherRuntime(ConfigProvider config, IDiagnosticLog log, IClock clock, WatcherIdentity identity, RuntimePaths paths,
        Func<RuntimeServices, IEnumerable<ICollector>> collectorFactory)
    {
        _config = config;
        _log = log;
        _clock = clock;
        Identity = identity;
        Paths = paths;
        _collectorFactory = collectorFactory;
        Activity = new Activity.ActivityContext(() => config.Current.Collectors.Files.SkuPatterns);
    }

    public WatcherIdentity Identity { get; }

    /// <summary>Shared current session / browser page, used to add context to every event.</summary>
    public Activity.ActivityContext Activity { get; }
    public RuntimePaths Paths { get; }
    public EventPipeline? Pipeline => _pipeline;
    public CollectorHost? Host => _host;
    public IEventStore? Store => _store;

    public void Start(IDictionary<string, object?>? extraStartInfo = null)
    {
        _uptime.Start();
        Directory.CreateDirectory(Paths.DataFolder);
        _store = new SqliteEventStore(Paths.DatabasePath, Paths.FallbackFolder);
        var imported = SafeImportFallback();
        _pipeline = EventPipeline.Create(_config, Identity, _store, _log, _clock, Activity);

        var context = new CollectorContext(_pipeline, _config, _log, _clock);
        _host = new CollectorHost(context);
        var services = new RuntimeServices(Identity, Paths, _config, _log, _clock, Activity);
        foreach (var c in _collectorFactory(services)) _host.Add(c);

        EmitStarted(imported, extraStartInfo);
        _config.Changed += OnConfigChanged;
        _host.StartAll();

        var cfg = _config.Current;
        var hb = TimeSpan.FromMinutes(cfg.Collectors.Activity.HeartbeatMinutes);
        if (hb > TimeSpan.Zero) _heartbeatTimer = new Timer(_ => EmitHeartbeat(), null, hb, hb);

        if (cfg.Export.Enabled)
        {
            _export = new ExportService(_store, CreateUploader(cfg), _log, _clock);
            var every = TimeSpan.FromMinutes(cfg.Export.IntervalMinutes);
            _exportTimer = new Timer(_ => _ = ExportNowAsync(), null, TimeSpan.FromMinutes(1), every);
        }
        _retentionTimer = new Timer(_ => RunRetention(), null, TimeSpan.FromMinutes(2), TimeSpan.FromHours(6));
        _log.Info("runtime", $"Watcher started. Database: {Paths.DatabasePath}");
    }

    /// <summary>Stops collectors (closing open sessions), writes watcher_stopped and flushes everything to disk.</summary>
    public async Task StopAsync(string reason)
    {
        lock (_stopGate)
        {
            if (_stopped) return;
            _stopped = true;
        }
        _log.Info("runtime", $"Stopping watcher ({reason})");
        _config.Changed -= OnConfigChanged;
        _cts.Cancel();
        _heartbeatTimer?.Dispose();
        _exportTimer?.Dispose();
        _retentionTimer?.Dispose();
        _host?.StopAll(reason);

        if (_pipeline is not null)
        {
            var e = NewWatcherEvent(EventTypes.WatcherStopped);
            e.Metadata["reason"] = reason;
            e.Metadata["uptime_seconds"] = TimeFormat.Seconds(_uptime.Elapsed);
            e.Metadata["events_written"] = _pipeline.WrittenCount + 1;
            _pipeline.Emit(e);
            await _pipeline.DisposeAsync().ConfigureAwait(false);
        }
        _store?.Dispose();
        _log.Info("runtime", "Watcher stopped");
    }

    /// <summary>The export folder with {GoogleDrive} replaced. Throws when Google Drive is not available.</summary>
    public string ResolveExportFolder() => ExportDestination.Resolve(Paths.ExportFolder);

    public async Task<ExportResult> ExportNowAsync()
    {
        if (_export is null) return new ExportResult(0, 0, "export disabled");
        try
        {
            return await _export.ExportPendingAsync(_config.Current.Export.BatchSize, _cts.Token).ConfigureAwait(false);
        }
        catch (OperationCanceledException)
        {
            return new ExportResult(0, 0, "cancelled");
        }
        catch (Exception e)
        {
            _log.Error("export", "Export failed", e);
            return new ExportResult(0, 0, e.Message);
        }
    }

    public ValueTask DisposeAsync() => new(StopAsync("disposed"));

    /// <summary>Numbers for the tray status window and the heartbeat event.</summary>
    public JsonObject GetStatus()
    {
        using var proc = Process.GetCurrentProcess();
        var o = new JsonObject
        {
            ["uptime_seconds"] = TimeFormat.Seconds(_uptime.Elapsed),
            ["memory_mb"] = Math.Round(proc.WorkingSet64 / 1048576.0, 1),
            ["private_memory_mb"] = Math.Round(proc.PrivateMemorySize64 / 1048576.0, 1),
            ["cpu_seconds_total"] = Math.Round(proc.TotalProcessorTime.TotalSeconds, 2),
            ["events_written"] = _pipeline?.WrittenCount ?? 0,
            ["events_dropped_by_privacy"] = _pipeline?.DroppedByPrivacyCount ?? 0,
            ["duplicates_suppressed"] = _pipeline?.SuppressedDuplicateCount ?? 0,
            ["write_failures"] = _pipeline?.WriteFailureCount ?? 0,
            ["queue_length"] = _pipeline?.QueueLength ?? 0,
        };
        try
        {
            var stats = _store?.GetStats();
            if (stats is not null)
            {
                o["events_pending_upload"] = stats.Pending;
                o["events_upload_retrying"] = stats.Failed;
                o["oldest_pending_utc"] = stats.OldestPendingUtc;
            }
        }
        catch (Exception e)
        {
            o["store_error"] = e.Message;
        }
        var collectors = new JsonArray();
        foreach (var (name, state, restarts) in _host?.Status ?? Array.Empty<(string, CollectorState, int)>())
        {
            var c = new JsonObject { ["name"] = name, ["state"] = state.ToString().ToLowerInvariant(), ["restarts_last_hour"] = restarts };
            var collector = _host!.Collectors.FirstOrDefault(x => x.Name == name);
            try
            {
                foreach (var (k, v) in collector?.GetStats() ?? new Dictionary<string, object>()) c[k] = ToJson(v);
            }
            catch { /* stats are best effort */ }
            collectors.Add(c);
        }
        o["collectors"] = collectors;
        return o;
    }

    private ILogUploader CreateUploader(WatcherConfig cfg)
    {
        if (!string.Equals(cfg.Export.Uploader, "local_folder", StringComparison.OrdinalIgnoreCase))
        {
            _log.Warn("export", $"Uploader '{cfg.Export.Uploader}' is not available yet; using local_folder");
        }
        return new LocalFolderUploader(ResolveExportFolder);
    }

    private void EmitStarted(int importedFallback, IDictionary<string, object?>? extra)
    {
        var cfg = _config.Current;
        var result = _config.LastResult;
        var e = NewWatcherEvent(EventTypes.WatcherStarted);
        e.Metadata["watcher_version"] = WatcherVersion.Current;
        e.Metadata["os_version"] = RuntimeInformation.OSDescription;
        e.Metadata["dotnet_version"] = RuntimeInformation.FrameworkDescription;
        e.Metadata["process_id"] = Environment.ProcessId;
        e.Metadata["config_path"] = _config.Path;
        e.Metadata["config_file_found"] = result.FileExisted;
        e.Metadata["config_hash"] = result.Hash;
        if (result.Error is not null) e.Metadata["config_error"] = result.Error;
        e.Metadata["company_name"] = cfg.CompanyName;
        e.Metadata["idle_timeout_seconds"] = cfg.IdleTimeoutSeconds;
        e.Metadata["collectors_enabled"] = new JsonArray(_host!.Collectors.Select(c => (JsonNode)JsonValue.Create(c.Name)!).ToArray());
        e.Metadata["database_path"] = Paths.DatabasePath;
        if (importedFallback > 0) e.Metadata["fallback_events_imported"] = importedFallback;
        foreach (var (k, v) in extra ?? new Dictionary<string, object?>()) e.Metadata[k] = ToJson(v);
        _pipeline!.Emit(e);
    }

    private void EmitHeartbeat()
    {
        try
        {
            var e = NewWatcherEvent(EventTypes.WatcherHeartbeat);
            foreach (var (k, v) in GetStatus()) e.Metadata[k] = v?.DeepClone();
            _pipeline?.Emit(e);
        }
        catch (Exception ex)
        {
            _log.Warn("runtime", "Heartbeat failed", ex);
        }
    }

    private void OnConfigChanged(ConfigLoadResult result)
    {
        var e = NewWatcherEvent(EventTypes.ConfigChanged);
        e.Metadata["config_hash"] = result.Hash;
        e.Metadata["note"] = "Privacy rules and idle timeout apply now; collector on/off and folders apply after restart.";
        _pipeline?.Emit(e);
    }

    private void RunRetention()
    {
        try
        {
            var r = _config.Current.Retention;
            if (r.KeepUploadedEventsDays > 0 && _store is not null)
            {
                var deleted = _store.DeleteUploadedBefore(_clock.Now.AddDays(-r.KeepUploadedEventsDays));
                if (deleted > 0) _log.Info("retention", $"Deleted {deleted} uploaded events older than {r.KeepUploadedEventsDays} days");
            }
            (_log as FileDiagnosticLog)?.DeleteOlderThan(r.KeepDiagnosticLogsDays);
        }
        catch (Exception e)
        {
            _log.Warn("retention", "Retention cleanup failed", e);
        }
    }

    private int SafeImportFallback()
    {
        try
        {
            var n = _store!.ImportFallback();
            if (n > 0) _log.Warn("runtime", $"Imported {n} events saved to the fallback file during an earlier database problem");
            return n;
        }
        catch (Exception e)
        {
            _log.Error("runtime", "Could not import fallback events (they stay in the fallback folder)", e);
            return 0;
        }
    }

    /// <summary>Stats arrive as boxed values; store them with their real JSON type.</summary>
    internal static JsonNode? ToJson(object? v) => v switch
    {
        null => null,
        JsonNode n => n.DeepClone(),
        bool b => JsonValue.Create(b),
        int i => JsonValue.Create(i),
        long l => JsonValue.Create(l),
        double d => JsonValue.Create(d),
        float f => JsonValue.Create(f),
        decimal m => JsonValue.Create(m),
        DateTimeOffset t => JsonValue.Create(TimeFormat.Iso(t)),
        _ => JsonValue.Create(v.ToString()),
    };

    private WatchEvent NewWatcherEvent(string type) => new()
    {
        EventType = type,
        TimestampUtc = _clock.Now,
        Collector = CollectorHost.HostName,
        CollectorVersion = WatcherVersion.Current,
    };
}

/// <summary>What a collector factory may use when constructing collectors.</summary>
public sealed record RuntimeServices(WatcherIdentity Identity, RuntimePaths Paths, ConfigProvider Config, IDiagnosticLog Log, IClock Clock,
    Activity.ActivityContext Activity);
