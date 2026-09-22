using MppWatcher.Core.Events;
using MppWatcher.Core.Presentation;

namespace MppWatcher.Core.Tests;

public class FormatterTests
{
    [Fact]
    public void Session_end_reads_naturally()
    {
        var e = new WatchEvent { EventType = EventTypes.AppSessionEnd, Application = "Google Chrome" }
            .Set("duration_seconds", 312.0).Set("active_seconds", 290.0).Set("idle_seconds", 22.0)
            .Set("end_reason", "foreground_changed").Set("next_application", "Adobe Photoshop 2025");
        Assert.Equal("Google Chrome ended after 5m 12s (active 4m 50s, idle 22s) — switched to Adobe Photoshop 2025", EventSummaryFormatter.Summarize(e));
    }

    [Fact]
    public void Session_start_shows_domain_when_known()
    {
        var e = new WatchEvent { EventType = EventTypes.AppSessionStart, Application = "Google Chrome", Domain = "keepa.com", WindowTitle = "Keepa" };
        Assert.Equal("Google Chrome → keepa.com — \"Keepa\"", EventSummaryFormatter.Summarize(e));
    }

    [Fact]
    public void Round_trip_through_json_still_formats()
    {
        var e = new WatchEvent { EventType = EventTypes.IdleEnd, TimestampLocal = "2026-09-22T10:04:17.000-04:00" }.Set("idle_seconds", 723.0);
        var back = EventJson.Deserialize(EventJson.Serialize(e));
        Assert.Equal("Active again after 12m 3s idle", EventSummaryFormatter.Summarize(back));
        Assert.Equal("10:04:17", EventSummaryFormatter.LocalTimeText(back));
    }

    [Fact]
    public void Idle_closed_by_lock_or_stop_is_not_called_activity()
    {
        var e = new WatchEvent { EventType = EventTypes.IdleEnd }.Set("idle_seconds", 300.0).Set("end_reason", "watcher_stopped");
        Assert.Equal("Idle period of 5m 0s closed — watcher stopped", EventSummaryFormatter.Summarize(e));
    }

    [Fact]
    public void Utc_timestamp_has_fixed_format_and_round_trips()
    {
        var e = new WatchEvent { TimestampUtc = new DateTimeOffset(2026, 9, 22, 9, 31, 20, 500, TimeSpan.FromHours(-4)) };
        var json = EventJson.Serialize(e);
        Assert.Contains("\"timestamp_utc\":\"2026-09-22T13:31:20.500Z\"", json);
        Assert.Equal(e.TimestampUtc, EventJson.Deserialize(json).TimestampUtc);
    }
}
