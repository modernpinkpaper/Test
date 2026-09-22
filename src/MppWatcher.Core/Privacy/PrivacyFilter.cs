using MppWatcher.Core.Configuration;
using MppWatcher.Core.Events;

namespace MppWatcher.Core.Privacy;

public enum PrivacyAction { Keep, Redact, Drop }

public sealed record PrivacyDecision(PrivacyAction Action, string? Reason)
{
    public static readonly PrivacyDecision Keep = new(PrivacyAction.Keep, null);
}

/// <summary>
/// Applies the admin's block lists to every event before it is stored.
/// "Redact" keeps the timing (so the day still adds up) but removes what was on screen.
/// Reads the config on every call so edits to config.json apply without a restart.
/// </summary>
public sealed class PrivacyFilter
{
    public const string RedactedText = "[excluded]";

    private readonly Func<WatcherConfig> _config;
    private readonly UrlSanitizer _defaultSanitizer = new();

    public PrivacyFilter(Func<WatcherConfig> config) => _config = config;

    public PrivacyDecision Decide(WatchEvent e)
    {
        var p = _config().Privacy;
        string? reason = null;

        if (WildcardMatcher.MatchesAny(StripExe(e.ProcessName), p.BlockedApplications.Select(StripExeName)))
            reason = "blocked_application";
        else if (WildcardMatcher.MatchesAny(e.WindowTitle, p.BlockedWindowTitles) || WildcardMatcher.MatchesAny(e.PageTitle, p.BlockedWindowTitles))
            reason = "blocked_window_title";
        else if (!string.IsNullOrEmpty(e.Domain))
        {
            if (WildcardMatcher.MatchesAny(e.Domain, p.BlockedDomains)) reason = "blocked_domain";
            else if (p.AllowedDomains.Count > 0 && !IsAllowedDomain(e.Domain, p.AllowedDomains)) reason = "domain_not_in_allowed_list";
        }
        if (reason is null && !string.IsNullOrEmpty(e.Url) && WildcardMatcher.MatchesAny(e.Url, p.BlockedUrls))
            reason = "blocked_url";

        if (reason is null) return PrivacyDecision.Keep;
        return new(p.BlockedMode == "drop" ? PrivacyAction.Drop : PrivacyAction.Redact, reason);
    }

    /// <summary>
    /// Returns the event to store, or null if it must be dropped. Redaction clears every
    /// field that could describe what was on screen, including all metadata except timing.
    /// </summary>
    public WatchEvent? Apply(WatchEvent e)
    {
        SanitizeUrl(e);
        var decision = Decide(e);
        switch (decision.Action)
        {
            case PrivacyAction.Keep:
                RedactLinkedApplication(e);
                return e;
            case PrivacyAction.Drop:
                return null;
            default:
                Redact(e, decision.Reason!);
                return e;
        }
    }

    /// <summary>A kept event may name another app (e.g. "switched to KeePass"); hide it if that app is blocked.</summary>
    private void RedactLinkedApplication(WatchEvent e)
    {
        var p = _config().Privacy;
        var nextProcess = e.Metadata["next_process_name"]?.GetValue<string>();
        var nextTitle = e.Metadata["next_window_title"]?.GetValue<string>();
        if (nextProcess is null && nextTitle is null) return;
        if (WildcardMatcher.MatchesAny(StripExe(nextProcess), p.BlockedApplications.Select(StripExeName))
            || WildcardMatcher.MatchesAny(nextTitle, p.BlockedWindowTitles))
        {
            e.Metadata["next_process_name"] = RedactedText;
            e.Metadata["next_application"] = RedactedText;
            e.Metadata.Remove("next_window_title");
        }
    }

    private void SanitizeUrl(WatchEvent e)
    {
        if (string.IsNullOrEmpty(e.Url)) return;
        var extra = _config().Privacy.SensitiveUrlParameters;
        var sanitizer = extra.Count == 0 ? _defaultSanitizer : new UrlSanitizer(extra);
        var clean = sanitizer.Sanitize(e.Url);
        if (clean is null) { e.Url = null; return; }
        e.Url = clean.Url;
        e.Domain ??= clean.Domain;
        if (clean.WasModified) e.Metadata["url_sanitized"] = true;
    }

    private static readonly HashSet<string> TimingKeys = new(StringComparer.Ordinal)
    {
        "session_start", "session_end", "duration_seconds", "active_seconds", "idle_seconds", "end_reason",
        "idle_start", "idle_end", "idle_seconds_total", "foreground", "detected_at", "monitor",
    };

    private static void Redact(WatchEvent e, string reason)
    {
        e.Application = RedactedText;
        e.ProcessName = e.ProcessName is null ? null : RedactedText;
        e.ProcessId = null;
        e.WindowTitle = e.WindowTitle is null ? null : RedactedText;
        e.PageTitle = e.PageTitle is null ? null : RedactedText;
        e.Url = null;
        e.Domain = e.Domain is null ? null : RedactedText;
        foreach (var key in e.Metadata.Select(kv => kv.Key).ToList())
        {
            if (!TimingKeys.Contains(key)) e.Metadata.Remove(key);
        }
        e.Metadata["excluded"] = true;
        e.Metadata["excluded_reason"] = reason;
        e.DedupFingerprint = null;
    }

    private static bool IsAllowedDomain(string domain, IEnumerable<string> allowed) =>
        allowed.Any(a => WildcardMatcher.IsMatch(domain, a) || domain.EndsWith("." + a.TrimStart('*', '.'), StringComparison.OrdinalIgnoreCase));

    private static string StripExeName(string name) => StripExe(name)!;

    private static string? StripExe(string? name) =>
        name is not null && name.EndsWith(".exe", StringComparison.OrdinalIgnoreCase) ? name[..^4] : name;
}
