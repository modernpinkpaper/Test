using System.Text.Json;
using System.Text.Json.Serialization;

namespace MppWatcher.Core.Activity;

/// <summary>
/// The open foreground session, saved to disk every few seconds. If the watcher is killed
/// (crash, power loss, taskkill) the next start closes this session properly instead of losing it.
/// </summary>
public sealed class SessionCheckpoint
{
    [JsonPropertyName("session_id")] public string SessionId { get; set; } = "";
    [JsonPropertyName("process_name")] public string ProcessName { get; set; } = "";
    [JsonPropertyName("process_id")] public int ProcessId { get; set; }
    [JsonPropertyName("application")] public string? Application { get; set; }
    [JsonPropertyName("window_title")] public string? WindowTitle { get; set; }
    [JsonPropertyName("session_start")] public DateTimeOffset SessionStart { get; set; }
    [JsonPropertyName("last_seen")] public DateTimeOffset LastSeen { get; set; }
    [JsonPropertyName("idle_seconds")] public double IdleSeconds { get; set; }
    [JsonPropertyName("watcher_run_id")] public string WatcherRunId { get; set; } = "";
}

public sealed class CheckpointStore
{
    private readonly string _path;

    public CheckpointStore(string path) => _path = path;

    public void Save(SessionCheckpoint? checkpoint)
    {
        if (checkpoint is null) { Clear(); return; }
        Directory.CreateDirectory(Path.GetDirectoryName(_path)!);
        var tmp = _path + ".tmp";
        File.WriteAllText(tmp, JsonSerializer.Serialize(checkpoint));
        File.Move(tmp, _path, overwrite: true);
    }

    public SessionCheckpoint? Load()
    {
        try
        {
            return File.Exists(_path) ? JsonSerializer.Deserialize<SessionCheckpoint>(File.ReadAllText(_path)) : null;
        }
        catch (JsonException)
        {
            return null; // half-written file from a crash: nothing to recover
        }
    }

    public void Clear()
    {
        if (File.Exists(_path)) File.Delete(_path);
    }
}
