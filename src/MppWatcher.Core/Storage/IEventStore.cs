using MppWatcher.Core.Events;

namespace MppWatcher.Core.Storage;

public sealed record StoredEvent(long RowId, WatchEvent Event, int RetryCount);

public sealed record StoreStats(long Total, long Pending, long Uploaded, long Failed, string? OldestPendingUtc);

/// <summary>Local event storage. Events stay here until an uploader confirms them.</summary>
public interface IEventStore : IDisposable
{
    void Append(IReadOnlyList<WatchEvent> events);

    /// <summary>Oldest events that are not uploaded yet.</summary>
    IReadOnlyList<StoredEvent> GetPending(int limit);

    void MarkUploaded(IEnumerable<long> rowIds, DateTimeOffset when);
    void MarkUploadFailed(IEnumerable<long> rowIds, DateTimeOffset when, string error);

    /// <summary>Rows after <paramref name="afterRowId"/>, oldest first. Used by the live viewer.</summary>
    IReadOnlyList<StoredEvent> ReadAfter(long afterRowId, int limit);

    /// <summary>Deletes uploaded events older than the cutoff. Never deletes pending events.</summary>
    int DeleteUploadedBefore(DateTimeOffset cutoff);

    StoreStats GetStats();

    /// <summary>Last resort when the database cannot be written: park events in a JSONL file.</summary>
    void WriteFallback(IReadOnlyList<WatchEvent> events);

    /// <summary>Moves parked fallback events back into the database. Returns how many.</summary>
    int ImportFallback();
}
