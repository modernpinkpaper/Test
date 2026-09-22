using System.Threading.Channels;
using MppWatcher.Core.Collectors;
using MppWatcher.Core.Configuration;
using MppWatcher.Core.Diagnostics;
using MppWatcher.Core.Events;
using MppWatcher.Core.Privacy;
using MppWatcher.Core.Storage;

namespace MppWatcher.Core.Pipeline;

/// <summary>
/// The single path every event takes: normalize → privacy filter → duplicate check → queue → SQLite.
/// <see cref="Emit"/> never blocks and never throws, so collectors (including the UI thread)
/// stay responsive. A background task writes queued events in batches.
/// </summary>
public sealed class EventPipeline : IEventSink, IAsyncDisposable
{
    private readonly EventNormalizer _normalizer;
    private readonly PrivacyFilter _privacy;
    private readonly DuplicateSuppressor _dedup;
    private readonly IEventStore _store;
    private readonly IDiagnosticLog _log;
    private readonly IClock _clock;
    private readonly Activity.ActivityContext? _activity;
    private readonly Channel<WatchEvent> _queue = Channel.CreateUnbounded<WatchEvent>(new UnboundedChannelOptions { SingleReader = true });
    private readonly Task _writer;
    private long _written, _dropped, _failed;

    public EventPipeline(EventNormalizer normalizer, PrivacyFilter privacy, DuplicateSuppressor dedup,
        IEventStore store, IDiagnosticLog log, IClock clock, Activity.ActivityContext? activity = null)
    {
        _activity = activity;
        _normalizer = normalizer;
        _privacy = privacy;
        _dedup = dedup;
        _store = store;
        _log = log;
        _clock = clock;
        _writer = Task.Run(WriteLoopAsync);
    }

    public static EventPipeline Create(ConfigProvider config, WatcherIdentity identity, IEventStore store, IDiagnosticLog log, IClock clock,
        Activity.ActivityContext? activity = null) =>
        new(new EventNormalizer(identity, () => config.Current),
            new PrivacyFilter(() => config.Current),
            new DuplicateSuppressor(() => TimeSpan.FromSeconds(config.Current.Deduplication.WindowSeconds)),
            store, log, clock, activity);

    /// <summary>Raised on the writer thread after events are safely stored. Used by the smoke test.</summary>
    public event Action<IReadOnlyList<WatchEvent>>? Stored;

    public long WrittenCount => Interlocked.Read(ref _written);
    public long DroppedByPrivacyCount => Interlocked.Read(ref _dropped);
    public long SuppressedDuplicateCount => _dedup.SuppressedCount;
    public long WriteFailureCount => Interlocked.Read(ref _failed);
    public int QueueLength => _queue.Reader.CanCount ? _queue.Reader.Count : -1;

    public void Emit(WatchEvent e)
    {
        try
        {
            var now = _clock.Now;
            if (_activity is not null)
            {
                // Tie the event to the open session and the page it happened on, before privacy rules run.
                _activity.Enrich(e);
                _activity.Observe(e);
            }
            _normalizer.Normalize(e, now);
            if (_privacy.Apply(e) is null) { Interlocked.Increment(ref _dropped); return; }
            if (!_dedup.ShouldWrite(e, now)) return;
            _queue.Writer.TryWrite(e);
        }
        catch (Exception ex)
        {
            _log.Error("pipeline", $"Could not process {e.EventType} event", ex);
        }
    }

    private async Task WriteLoopAsync()
    {
        var reader = _queue.Reader;
        var batch = new List<WatchEvent>(256);
        while (await reader.WaitToReadAsync().ConfigureAwait(false))
        {
            batch.Clear();
            while (batch.Count < 500 && reader.TryRead(out var e)) batch.Add(e);
            await WriteBatchWithRetryAsync(batch).ConfigureAwait(false);
        }
    }

    private async Task WriteBatchWithRetryAsync(List<WatchEvent> batch)
    {
        for (var attempt = 1; ; attempt++)
        {
            try
            {
                _store.Append(batch);
                Interlocked.Add(ref _written, batch.Count);
                try { Stored?.Invoke(batch.ToList()); } catch (Exception e) { _log.Warn("pipeline", "Stored handler failed", e); }
                return;
            }
            catch (Exception ex) when (attempt < 4)
            {
                _log.Warn("pipeline", $"Database write failed (attempt {attempt}), retrying", ex);
                await Task.Delay(TimeSpan.FromMilliseconds(250 * Math.Pow(4, attempt - 1))).ConfigureAwait(false);
            }
            catch (Exception ex)
            {
                // Database unusable right now. Never lose events: park them in a JSONL file
                // that is imported back into the database on the next start.
                Interlocked.Add(ref _failed, batch.Count);
                _log.Error("pipeline", $"Database write failed; saving {batch.Count} events to fallback file", ex);
                _store.WriteFallback(batch);
                return;
            }
        }
    }

    /// <summary>Stops accepting events and waits for the queue to be written.</summary>
    public async ValueTask DisposeAsync()
    {
        _queue.Writer.TryComplete();
        try { await _writer.WaitAsync(TimeSpan.FromSeconds(15)).ConfigureAwait(false); }
        catch (Exception e) { _log.Error("pipeline", "Writer did not finish cleanly", e); }
    }
}
