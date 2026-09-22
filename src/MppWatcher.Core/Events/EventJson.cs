using System.Text.Encodings.Web;
using System.Text.Json;

namespace MppWatcher.Core.Events;

/// <summary>Shared JSON settings so every component writes events identically.</summary>
public static class EventJson
{
    public static readonly JsonSerializerOptions Options = new()
    {
        WriteIndented = false,
        // Keep non-ASCII product titles readable in the files (still valid JSON).
        Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
        DefaultIgnoreCondition = System.Text.Json.Serialization.JsonIgnoreCondition.Never,
    };

    public static readonly JsonSerializerOptions IndentedOptions = new(Options) { WriteIndented = true };

    public static string Serialize(WatchEvent e) => JsonSerializer.Serialize(e, Options);

    public static string SerializeIndented(WatchEvent e) => JsonSerializer.Serialize(e, IndentedOptions);

    public static WatchEvent Deserialize(string json) =>
        JsonSerializer.Deserialize<WatchEvent>(json, Options) ?? throw new JsonException("Empty event JSON");
}
