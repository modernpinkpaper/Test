using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using MppWatcher.Core.Diagnostics;
using MppWatcher.Core.Events;

namespace MppWatcher.Core.Configuration;

public sealed record ConfigLoadResult(WatcherConfig Config, string? Error, string Hash, bool FileExisted);

public static class ConfigLoader
{
    public static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = true,
        ReadCommentHandling = JsonCommentHandling.Skip,
        AllowTrailingCommas = true,
        PropertyNameCaseInsensitive = true,
        Encoder = EventJson.Options.Encoder,
    };

    /// <summary>
    /// Loads a config file. Never throws: a missing file gives defaults, a broken file gives
    /// defaults plus an error message (so the watcher keeps running and reports the problem).
    /// </summary>
    public static ConfigLoadResult Load(string path)
    {
        if (!File.Exists(path)) return new ConfigLoadResult(Validate(new WatcherConfig()), null, "defaults", false);
        try
        {
            var text = File.ReadAllText(path);
            return Parse(text) with { FileExisted = true };
        }
        catch (Exception e)
        {
            return new ConfigLoadResult(Validate(new WatcherConfig()), $"Could not read {path}: {e.Message}", "defaults", true);
        }
    }

    public static ConfigLoadResult Parse(string json)
    {
        var hash = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(json)))[..16];
        try
        {
            var cfg = JsonSerializer.Deserialize<WatcherConfig>(json, JsonOptions) ?? new WatcherConfig();
            return new ConfigLoadResult(Validate(cfg), null, hash, true);
        }
        catch (JsonException e)
        {
            return new ConfigLoadResult(Validate(new WatcherConfig()), $"Invalid config JSON: {e.Message}", hash, true);
        }
    }

    public static string ToJson(WatcherConfig config) => JsonSerializer.Serialize(config, JsonOptions);

    /// <summary>Clamps values into sane ranges so a typo cannot make the watcher spin or never fire.</summary>
    public static WatcherConfig Validate(WatcherConfig c)
    {
        c.IdleTimeoutSeconds = Math.Clamp(c.IdleTimeoutSeconds, 30, 3600);
        var a = c.Collectors.Activity;
        a.ForegroundStableMs = Math.Clamp(a.ForegroundStableMs, 0, 10_000);
        a.TitleStableMs = Math.Clamp(a.TitleStableMs, 0, 30_000);
        a.PollIntervalMs = Math.Clamp(a.PollIntervalMs, 200, 5000);
        a.GapThresholdSeconds = Math.Clamp(a.GapThresholdSeconds, 15, 3600);
        a.HeartbeatMinutes = Math.Clamp(a.HeartbeatMinutes, 0, 240);
        a.CheckpointSeconds = Math.Clamp(a.CheckpointSeconds, 5, 600);
        a.ReturnWindowMinutes = Math.Clamp(a.ReturnWindowMinutes, 0, 24 * 60);
        c.Collectors.Process.ScanIntervalSeconds = Math.Clamp(c.Collectors.Process.ScanIntervalSeconds, 5, 600);
        var u = c.Collectors.UiAutomation;
        u.MaxValueLength = Math.Clamp(u.MaxValueLength, 0, 2000);
        u.FocusedFieldPollMs = Math.Clamp(u.FocusedFieldPollMs, 200, 5000);
        u.ValueSettleSeconds = Math.Clamp(u.ValueSettleSeconds, 1, 60);
        c.Collectors.Browser.PollMs = Math.Clamp(c.Collectors.Browser.PollMs, 250, 10_000);
        c.Collectors.Browser.MaxHeadings = Math.Clamp(c.Collectors.Browser.MaxHeadings, 0, 30);
        c.Export.IntervalMinutes = Math.Clamp(c.Export.IntervalMinutes, 1, 24 * 60);
        c.Export.BatchSize = Math.Clamp(c.Export.BatchSize, 100, 50_000);
        c.Deduplication.WindowSeconds = Math.Clamp(c.Deduplication.WindowSeconds, 0, 3600);
        if (c.Privacy.BlockedMode is not ("redact" or "drop")) c.Privacy.BlockedMode = "redact";
        c.EmployeeIdByWindowsUser = new Dictionary<string, string>(c.EmployeeIdByWindowsUser ?? new(), StringComparer.OrdinalIgnoreCase);
        return c;
    }
}

/// <summary>
/// Holds the current config and reloads it when the file changes. Privacy rules and the
/// idle timeout are read on every use, so they apply without restarting. Collector
/// on/off switches apply at the next start.
/// </summary>
public sealed class ConfigProvider : IDisposable
{
    private readonly IDiagnosticLog _log;
    private FileSystemWatcher? _watcher;
    private Timer? _debounce;
    private volatile WatcherConfig _current;

    public ConfigProvider(string path, IDiagnosticLog log)
    {
        Path = path;
        _log = log;
        var result = ConfigLoader.Load(path);
        _current = result.Config;
        LastResult = result;
        if (result.Error is not null) _log.Error("config", result.Error);
    }

    /// <summary>For tests and tools that do not need a file.</summary>
    public ConfigProvider(WatcherConfig config)
    {
        Path = "";
        _log = NullDiagnosticLog.Instance;
        _current = ConfigLoader.Validate(config);
        LastResult = new ConfigLoadResult(_current, null, "in-memory", false);
    }

    public string Path { get; }
    public WatcherConfig Current => _current;
    public ConfigLoadResult LastResult { get; private set; }

    /// <summary>Raised after a successful reload (on a thread-pool thread).</summary>
    public event Action<ConfigLoadResult>? Changed;

    public void WatchForChanges()
    {
        if (string.IsNullOrEmpty(Path)) return;
        var dir = System.IO.Path.GetDirectoryName(Path);
        if (string.IsNullOrEmpty(dir) || !Directory.Exists(dir)) return;
        try
        {
            _debounce = new Timer(_ => Reload(), null, Timeout.Infinite, Timeout.Infinite);
            _watcher = new FileSystemWatcher(dir, System.IO.Path.GetFileName(Path))
            {
                NotifyFilter = NotifyFilters.LastWrite | NotifyFilters.Size | NotifyFilters.FileName | NotifyFilters.CreationTime,
            };
            FileSystemEventHandler onChange = (_, _) => _debounce.Change(750, Timeout.Infinite);
            _watcher.Changed += onChange;
            _watcher.Created += onChange;
            _watcher.Renamed += (_, _) => _debounce.Change(750, Timeout.Infinite);
            _watcher.EnableRaisingEvents = true;
        }
        catch (Exception e)
        {
            _log.Warn("config", "Config file watching unavailable; changes apply after restart", e);
        }
    }

    public void Reload()
    {
        var result = ConfigLoader.Load(Path);
        if (result.Error is not null)
        {
            // Keep the last good config rather than falling back to defaults mid-day.
            _log.Error("config", result.Error + " (keeping previous settings)");
            return;
        }
        if (result.Hash == LastResult.Hash) return;
        _current = result.Config;
        LastResult = result;
        _log.Info("config", $"Config reloaded (hash {result.Hash})");
        try { Changed?.Invoke(result); } catch (Exception e) { _log.Error("config", "Config change handler failed", e); }
    }

    public void Dispose()
    {
        _watcher?.Dispose();
        _debounce?.Dispose();
    }
}
