using System.Collections.Concurrent;
using System.Diagnostics;
using MppWatcher.Windows.Interop;

namespace MppWatcher.Windows;

/// <summary>
/// Looks up process name, exe path and friendly application name ("Google Chrome",
/// "Adobe Photoshop 2025") and caches them, so the 500 ms poll stays cheap.
/// </summary>
internal sealed class ProcessInfoCache
{
    public sealed record Entry(string Name, string? Path, string? ApplicationName, DateTime CachedAtUtc);

    private readonly ConcurrentDictionary<int, Entry> _byPid = new();
    private readonly ConcurrentDictionary<string, string?> _appNameByPath = new(StringComparer.OrdinalIgnoreCase);

    public Entry Get(int pid)
    {
        if (_byPid.TryGetValue(pid, out var cached) && DateTime.UtcNow - cached.CachedAtUtc < TimeSpan.FromMinutes(10))
        {
            return cached;
        }
        var entry = Lookup(pid);
        _byPid[pid] = entry;
        if (_byPid.Count > 2000) _byPid.Clear();
        return entry;
    }

    /// <summary>Call when a process is known to have exited (its pid may be reused).</summary>
    public void Forget(int pid) => _byPid.TryRemove(pid, out _);

    public string? ApplicationNameFor(string? path)
    {
        if (string.IsNullOrEmpty(path)) return null;
        return _appNameByPath.GetOrAdd(path, p =>
        {
            try
            {
                var v = FileVersionInfo.GetVersionInfo(p);
                var name = !string.IsNullOrWhiteSpace(v.FileDescription) ? v.FileDescription : v.ProductName;
                return string.IsNullOrWhiteSpace(name) ? null : name.Trim();
            }
            catch
            {
                return null;
            }
        });
    }

    private Entry Lookup(int pid)
    {
        string name;
        try
        {
            using var p = Process.GetProcessById(pid);
            name = p.ProcessName;
        }
        catch
        {
            name = "pid-" + pid;
        }
        var path = NativeMethods.GetProcessPath(pid);
        if (name.StartsWith("pid-", StringComparison.Ordinal) && path is not null) name = System.IO.Path.GetFileNameWithoutExtension(path);
        return new Entry(name, path, ApplicationNameFor(path), DateTime.UtcNow);
    }
}
