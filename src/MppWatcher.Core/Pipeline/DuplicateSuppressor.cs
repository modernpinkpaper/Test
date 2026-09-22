using MppWatcher.Core.Events;

namespace MppWatcher.Core.Pipeline;

/// <summary>
/// Drops an event when an identical one (same type + fingerprint) was already written
/// within the time window. Events without a fingerprint always pass.
/// </summary>
public sealed class DuplicateSuppressor
{
    private readonly Func<TimeSpan> _window;
    private readonly Dictionary<string, DateTimeOffset> _lastSeen = new();
    private readonly object _gate = new();
    private DateTimeOffset _lastCleanup = DateTimeOffset.MinValue;

    public DuplicateSuppressor(Func<TimeSpan> window) => _window = window;

    public long SuppressedCount { get; private set; }

    public bool ShouldWrite(WatchEvent e, DateTimeOffset now)
    {
        if (string.IsNullOrEmpty(e.DedupFingerprint)) return true;
        var window = _window();
        if (window <= TimeSpan.Zero) return true;
        var key = e.EventType + "\u001f" + e.DedupFingerprint;
        lock (_gate)
        {
            Cleanup(now, window);
            if (_lastSeen.TryGetValue(key, out var last) && now - last < window)
            {
                SuppressedCount++;
                return false;
            }
            _lastSeen[key] = now;
            return true;
        }
    }

    private void Cleanup(DateTimeOffset now, TimeSpan window)
    {
        if (now - _lastCleanup < TimeSpan.FromMinutes(1)) return;
        _lastCleanup = now;
        foreach (var k in _lastSeen.Where(kv => now - kv.Value >= window).Select(kv => kv.Key).ToList()) _lastSeen.Remove(k);
    }
}
