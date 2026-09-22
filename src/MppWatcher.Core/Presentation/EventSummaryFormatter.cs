using System.Globalization;
using System.Text.Json.Nodes;
using MppWatcher.Core.Events;

namespace MppWatcher.Core.Presentation;

/// <summary>
/// One readable line per event for the live test viewer, e.g.
/// "Google Chrome → keepa.com — Keepa - Amazon Price Tracker".
/// </summary>
public static class EventSummaryFormatter
{
    public static string LocalTimeText(WatchEvent e) =>
        DateTimeOffset.TryParse(e.TimestampLocal, CultureInfo.InvariantCulture, DateTimeStyles.None, out var t)
            ? t.ToString("HH:mm:ss", CultureInfo.InvariantCulture)
            : e.TimestampUtc.ToLocalTime().ToString("HH:mm:ss", CultureInfo.InvariantCulture);

    public static string Summarize(WatchEvent e)
    {
        var m = e.Metadata;
        var app = e.Application ?? e.ProcessName ?? "?";
        var where = string.IsNullOrEmpty(e.Domain) ? app : $"{app} → {e.Domain}";
        var excluded = Bool(m, "excluded") ? $" (excluded: {Str(m, "excluded_reason")})" : "";

        return e.EventType switch
        {
            EventTypes.AppSessionStart => $"{where} — \"{e.PageTitle ?? e.WindowTitle}\"{Returning(m)}{excluded}",
            EventTypes.AppSessionEnd =>
                $"{app} ended after {Dur(m, "duration_seconds")} (active {Dur(m, "active_seconds")}, idle {Dur(m, "idle_seconds")}) — {Reason(m)}{excluded}",
            EventTypes.WindowTitleChanged => $"{where} title → \"{e.WindowTitle}\"",
            EventTypes.IdleStart => $"Idle — no keyboard/mouse since {ShortTime(Str(m, "idle_start"))}",
            EventTypes.IdleEnd => Str(m, "end_reason") is null or "input_resumed"
                ? $"Active again after {Dur(m, "idle_seconds")} idle"
                : $"Idle period of {Dur(m, "idle_seconds")} closed — {Str(m, "end_reason")!.Replace('_', ' ')}",
            EventTypes.WorkstationLocked => "Workstation locked",
            EventTypes.WorkstationUnlocked => $"Workstation unlocked (locked {Dur(m, "locked_seconds")})",
            EventTypes.SystemSuspend => "PC going to sleep",
            EventTypes.SystemResume => $"PC woke up (slept {Dur(m, "suspended_seconds")})",
            EventTypes.SessionEnding => $"Windows {Str(m, "kind") ?? "session"} ending",
            EventTypes.ActivityGap => $"Gap of {Dur(m, "gap_seconds")} with no watcher activity",
            EventTypes.UiFieldValue => Bool(m, "value_omitted")
                ? $"{where}: field \"{Str(m, "label") ?? Str(m, "name") ?? Str(m, "control_type")}\" edited (value not stored, {Num(m, "value_length")} chars){excluded}"
                : $"{where}: field \"{Str(m, "label") ?? Str(m, "name") ?? Str(m, "control_type")}\" = \"{Str(m, "value")}\"{excluded}",
            EventTypes.UiAction => $"{where}: {Str(m, "action")?.Replace('_', ' ')} \"{Str(m, "control_name")}\"{(Bool(m, "is_key_action") ? " ★" : "")}{(Str(m, "state_after") is { } st ? $" → {st}" : "")}{excluded}",
            EventTypes.BrowserPage => $"{where}: {PageSummary(m)} — \"{e.PageTitle}\"",
            EventTypes.ProcessStarted => $"Started {app}{(Bool(m, "has_window") ? "" : " (no window)")}",
            EventTypes.ProcessExited => $"Exited {app} after {Dur(m, "run_seconds")}",
            EventTypes.ProcessInventory => $"Running programs: {Inventory(m)}",
            EventTypes.WatcherStarted => $"MPP Watcher {Str(m, "watcher_version")} started",
            EventTypes.WatcherStopped => $"MPP Watcher stopped ({Str(m, "reason")})",
            EventTypes.WatcherHeartbeat => $"Heartbeat — {Num(m, "events_written")} events written, {Num(m, "memory_mb")} MB RAM",
            EventTypes.CollectorStatus => $"Collector {Str(m, "collector_name")}: {Str(m, "status")}{(Str(m, "error") is { } err ? " — " + err : "")}",
            EventTypes.ConfigChanged => "Configuration reloaded",
            _ => $"{e.EventType} {where}",
        };
    }

    private static string Reason(JsonObject m)
    {
        var reason = Str(m, "end_reason") ?? "ended";
        return reason switch
        {
            SessionEndReasons.ForegroundChanged => $"switched to {Str(m, "next_application") ?? "another app"}",
            SessionEndReasons.TitleChanged => $"moved to \"{Str(m, "next_window_title") ?? "another page"}\"",
            _ => reason.Replace('_', ' '),
        };
    }

    private static string PageSummary(JsonObject m)
    {
        var parts = new List<string>();
        var site = Str(m, "site");
        if (site is not null && site != "other") parts.Add(site.Replace('_', ' ') + " " + (Str(m, "module") ?? Str(m, "page_type")?.Replace('_', ' ')));
        foreach (var (key, label) in new[] { ("asins", "ASIN"), ("skus", "SKU"), ("listing_ids", "listing"), ("product_ids", "product"), ("order_ids", "order") })
            if (m[key] is JsonArray a && a.Count > 0) parts.Add($"{label} {string.Join(", ", a.Select(x => x?.ToString()))}");
        if (Str(m, "search_term") is { } q) parts.Add($"search \"{q}\"");
        return parts.Count == 0 ? "page" : string.Join(" · ", parts);
    }

    private static string Returning(JsonObject m) =>
        m["returning_to_session_id"] is null ? "" : $" (returned after {Dur(m, "seconds_since_last_visit")})";

    private static string Inventory(JsonObject m)
    {
        if (m["processes"] is not JsonArray arr) return "";
        var names = arr.Select(n => n?["process_name"]?.GetValue<string>()).Where(n => n is not null).Take(12).ToList();
        return string.Join(", ", names) + (arr.Count > names.Count ? $" (+{arr.Count - names.Count} more)" : "");
    }

    private static string? Str(JsonObject m, string key) => m[key] is JsonValue v && v.TryGetValue<string>(out var s) ? s : m[key]?.ToString();
    private static bool Bool(JsonObject m, string key) => m[key] is JsonValue v && v.TryGetValue<bool>(out var b) && b;
    private static string Num(JsonObject m, string key) => m[key]?.ToString() ?? "?";

    private static string Dur(JsonObject m, string key) =>
        m[key] is JsonValue v && v.TryGetValue<double>(out var s) ? TimeFormat.Human(TimeSpan.FromSeconds(s)) : "?";

    private static string ShortTime(string? iso) =>
        iso is not null && DateTimeOffset.TryParse(iso, CultureInfo.InvariantCulture, DateTimeStyles.None, out var t)
            ? t.ToString("HH:mm:ss", CultureInfo.InvariantCulture) : "?";
}
