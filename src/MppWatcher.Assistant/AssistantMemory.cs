using System.Text.Json;
using System.Text.Json.Serialization;

namespace MppWatcher.Assistant;

/// <summary>
/// The assistant's day memory: a short running note plus a list of open items (things worth
/// remembering, like "Erika said the collection is ready"). Open items are carried forward until
/// they are resolved; resolved/old items are pruned so the file stays small.
/// </summary>
public sealed class AssistantMemory
{
    [JsonPropertyName("running_note")] public string RunningNote { get; set; } = "";
    [JsonPropertyName("open_items")] public List<MemoryItem> OpenItems { get; set; } = new();

    /// <summary>Max open items kept (oldest unresolved dropped beyond this).</summary>
    public const int MaxOpenItems = 100;

    public static AssistantMemory Load(string path)
    {
        try
        {
            if (File.Exists(path))
                return JsonSerializer.Deserialize<AssistantMemory>(File.ReadAllText(path), AssistantJson.Options) ?? new AssistantMemory();
        }
        catch { /* broken memory just starts empty */ }
        return new AssistantMemory();
    }

    public void Save(string path)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(path))!);
        File.WriteAllText(path, JsonSerializer.Serialize(this, AssistantJson.Indented));
    }

    /// <summary>Add an open item (ignores blank text). Returns the item added, or null.</summary>
    public MemoryItem? AddOpenItem(string text, string kind, DateTimeOffset nowUtc)
    {
        if (string.IsNullOrWhiteSpace(text)) return null;
        var item = new MemoryItem { Text = text.Trim(), Kind = kind, NotedUtc = nowUtc };
        OpenItems.Add(item);
        return item;
    }

    /// <summary>Mark an item resolved (done) by id. Returns true if found.</summary>
    public bool Resolve(string id)
    {
        var item = OpenItems.FirstOrDefault(i => i.Id == id);
        if (item is null) return false;
        item.Resolved = true;
        return true;
    }

    /// <summary>Drop resolved items older than <paramref name="keep"/>, and cap the list size.</summary>
    public void Prune(DateTimeOffset nowUtc, TimeSpan keep)
    {
        OpenItems.RemoveAll(i => i.Resolved && (nowUtc - i.NotedUtc) > keep);
        if (OpenItems.Count > MaxOpenItems)
        {
            // Keep the newest; drop the oldest unresolved beyond the cap.
            var trimmed = OpenItems.OrderByDescending(i => i.NotedUtc).Take(MaxOpenItems).ToList();
            OpenItems = trimmed.OrderBy(i => i.NotedUtc).ToList();
        }
    }
}
