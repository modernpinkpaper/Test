using System.Globalization;

namespace MppWatcher.Core.Events;

public static class TimeFormat
{
    /// <summary>ISO 8601 with milliseconds and offset, e.g. 2026-09-22T10:04:17.123-04:00.</summary>
    public static string Iso(DateTimeOffset t) => t.ToString("yyyy-MM-dd'T'HH:mm:ss.fffzzz", CultureInfo.InvariantCulture);

    public static string IsoUtc(DateTimeOffset t) => t.UtcDateTime.ToString("yyyy-MM-dd'T'HH:mm:ss.fff'Z'", CultureInfo.InvariantCulture);

    public static double Seconds(TimeSpan span) => Math.Round(Math.Max(0, span.TotalSeconds), 3);

    /// <summary>Short human form used by the live viewer, e.g. "5m 12s".</summary>
    public static string Human(TimeSpan span)
    {
        if (span < TimeSpan.Zero) span = TimeSpan.Zero;
        if (span.TotalHours >= 1) return $"{(int)span.TotalHours}h {span.Minutes}m";
        if (span.TotalMinutes >= 1) return $"{(int)span.TotalMinutes}m {span.Seconds}s";
        return $"{span.TotalSeconds:0.#}s";
    }
}
