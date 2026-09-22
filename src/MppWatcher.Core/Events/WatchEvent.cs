using System.Text.Json.Nodes;
using System.Text.Json.Serialization;

namespace MppWatcher.Core.Events;

/// <summary>
/// One structured activity event. Collectors fill in what they know
/// (event type, application, window, metadata); the <see cref="Pipeline.EventNormalizer"/>
/// fills in identity, timestamps and ids before the event is stored.
/// Event-specific details always live in <see cref="Metadata"/>.
/// </summary>
public sealed class WatchEvent
{
    public const int CurrentSchemaVersion = 1;

    [JsonPropertyName("schema_version")] public int SchemaVersion { get; set; } = CurrentSchemaVersion;
    [JsonPropertyName("event_id")] public string EventId { get; set; } = "";
    [JsonPropertyName("timestamp_utc"), JsonConverter(typeof(UtcTimestampConverter))] public DateTimeOffset TimestampUtc { get; set; }
    [JsonPropertyName("timestamp_local")] public string TimestampLocal { get; set; } = "";
    [JsonPropertyName("computer_id")] public string ComputerId { get; set; } = "";
    [JsonPropertyName("employee_id")] public string EmployeeId { get; set; } = "";
    [JsonPropertyName("windows_username")] public string WindowsUsername { get; set; } = "";
    [JsonPropertyName("event_type")] public string EventType { get; set; } = "";
    [JsonPropertyName("application")] public string? Application { get; set; }
    [JsonPropertyName("process_name")] public string? ProcessName { get; set; }
    [JsonPropertyName("process_id")] public int? ProcessId { get; set; }
    [JsonPropertyName("window_title")] public string? WindowTitle { get; set; }
    [JsonPropertyName("domain")] public string? Domain { get; set; }
    [JsonPropertyName("url")] public string? Url { get; set; }
    [JsonPropertyName("page_title")] public string? PageTitle { get; set; }
    /// <summary>The foreground activity session this event belongs to (see app_session_start/end).</summary>
    [JsonPropertyName("session_id")] public string? SessionId { get; set; }
    /// <summary>Reserved for later analysis; the watcher leaves it empty.</summary>
    [JsonPropertyName("task_context_id")] public string? TaskContextId { get; set; }
    /// <summary>Changes every time the watcher starts. Lets analysis spot restarts and gaps.</summary>
    [JsonPropertyName("watcher_run_id")] public string WatcherRunId { get; set; } = "";
    /// <summary>Increasing number within one watcher run. Gives a stable order for events with equal timestamps.</summary>
    [JsonPropertyName("sequence")] public long Sequence { get; set; }
    [JsonPropertyName("collector")] public string Collector { get; set; } = "";
    [JsonPropertyName("collector_version")] public string CollectorVersion { get; set; } = "";
    [JsonPropertyName("metadata")] public JsonObject Metadata { get; set; } = new();

    /// <summary>
    /// Optional key used by the duplicate suppressor. Events with the same type and
    /// fingerprint inside the suppression window are dropped. Not stored.
    /// </summary>
    [JsonIgnore] public string? DedupFingerprint { get; set; }

    public WatchEvent Set(string key, JsonNode? value)
    {
        Metadata[key] = value;
        return this;
    }
}

/// <summary>Always writes UTC as "2026-09-22T13:31:20.500Z" (fixed width, sortable as text).</summary>
public sealed class UtcTimestampConverter : JsonConverter<DateTimeOffset>
{
    public override DateTimeOffset Read(ref System.Text.Json.Utf8JsonReader reader, Type typeToConvert, System.Text.Json.JsonSerializerOptions options) =>
        DateTimeOffset.Parse(reader.GetString()!, System.Globalization.CultureInfo.InvariantCulture, System.Globalization.DateTimeStyles.AssumeUniversal).ToUniversalTime();

    public override void Write(System.Text.Json.Utf8JsonWriter writer, DateTimeOffset value, System.Text.Json.JsonSerializerOptions options) =>
        writer.WriteStringValue(TimeFormat.IsoUtc(value));
}
