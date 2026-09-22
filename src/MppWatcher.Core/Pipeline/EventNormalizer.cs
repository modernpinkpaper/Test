using MppWatcher.Core.Configuration;
using MppWatcher.Core.Events;

namespace MppWatcher.Core.Pipeline;

/// <summary>Who and where: the identity values stamped on every event.</summary>
public sealed record WatcherIdentity(string ComputerName, string WindowsUsername, string WatcherRunId)
{
    public static WatcherIdentity FromEnvironment() => new(
        Environment.MachineName,
        string.IsNullOrEmpty(Environment.UserDomainName) ? Environment.UserName : $"{Environment.UserDomainName}\\{Environment.UserName}",
        Guid.NewGuid().ToString("N"));
}

/// <summary>
/// Fills in the common fields every event must have (ids, timestamps, identity, collector)
/// and trims over-long text so one odd window title cannot bloat the log.
/// </summary>
public sealed class EventNormalizer
{
    public const int MaxTextLength = 1024;

    private readonly WatcherIdentity _identity;
    private readonly Func<WatcherConfig> _config;
    private long _sequence;

    public EventNormalizer(WatcherIdentity identity, Func<WatcherConfig> config)
    {
        _identity = identity;
        _config = config;
    }

    public WatcherIdentity Identity => _identity;

    public WatchEvent Normalize(WatchEvent e, DateTimeOffset now)
    {
        var cfg = _config();
        if (string.IsNullOrEmpty(e.EventId)) e.EventId = Guid.NewGuid().ToString("N");
        if (e.TimestampUtc == default) e.TimestampUtc = now;
        var local = e.TimestampUtc.ToLocalTime();
        e.TimestampUtc = e.TimestampUtc.ToUniversalTime();
        e.TimestampLocal = TimeFormat.Iso(local);
        e.ComputerId = string.IsNullOrWhiteSpace(cfg.ComputerId) ? _identity.ComputerName : cfg.ComputerId.Trim();
        e.WindowsUsername = _identity.WindowsUsername;
        e.EmployeeId = ResolveEmployeeId(cfg, _identity.WindowsUsername);
        e.WatcherRunId = _identity.WatcherRunId;
        e.Sequence = Interlocked.Increment(ref _sequence);
        e.SchemaVersion = WatchEvent.CurrentSchemaVersion;
        e.Application = Trim(e.Application);
        e.WindowTitle = Trim(e.WindowTitle);
        e.PageTitle = Trim(e.PageTitle);
        e.Url = Trim(e.Url, 2048);
        return e;
    }

    public static string ResolveEmployeeId(WatcherConfig cfg, string windowsUsername)
    {
        if (cfg.EmployeeIdByWindowsUser.TryGetValue(windowsUsername, out var id) && !string.IsNullOrWhiteSpace(id)) return id.Trim();
        var shortName = windowsUsername.Contains('\\') ? windowsUsername[(windowsUsername.LastIndexOf('\\') + 1)..] : windowsUsername;
        if (cfg.EmployeeIdByWindowsUser.TryGetValue(shortName, out id) && !string.IsNullOrWhiteSpace(id)) return id.Trim();
        if (!string.IsNullOrWhiteSpace(cfg.EmployeeId)) return cfg.EmployeeId.Trim();
        return "unassigned-" + shortName;
    }

    private static string? Trim(string? s, int max = MaxTextLength) =>
        s is null ? null : s.Length <= max ? s : s[..max] + "…";
}
