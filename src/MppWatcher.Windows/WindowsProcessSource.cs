using System.Diagnostics;
using MppWatcher.Core.Processes;
using MppWatcher.Windows.Interop;

namespace MppWatcher.Windows;

/// <summary>Lists processes in the current user's Windows session (not other users', not services).</summary>
public sealed class WindowsProcessSource : IProcessSource
{
    private readonly ProcessInfoCache _cache = new();
    private readonly int _sessionId = Process.GetCurrentProcess().SessionId;

    public IReadOnlyList<ProcessInfo> Snapshot()
    {
        var windowPids = VisibleWindowProcessIds();
        var list = new List<ProcessInfo>();
        foreach (var p in Process.GetProcesses())
        {
            using (p)
            {
                try
                {
                    if (p.SessionId != _sessionId) continue;
                    DateTimeOffset? start = null;
                    try { start = p.StartTime; } catch { /* elevated process: start time not readable */ }
                    var info = _cache.Get(p.Id);
                    list.Add(new ProcessInfo(p.Id, p.ProcessName, start, info.Path, info.ApplicationName, windowPids.Contains(p.Id)));
                }
                catch
                {
                    // Process exited while we were looking at it.
                }
            }
        }
        return list;
    }

    private static HashSet<int> VisibleWindowProcessIds()
    {
        var pids = new HashSet<int>();
        NativeMethods.EnumWindows((hwnd, _) =>
        {
            if (NativeMethods.IsWindowVisible(hwnd) && NativeMethods.GetWindowTextLength(hwnd) > 0)
            {
                NativeMethods.GetWindowThreadProcessId(hwnd, out var pid);
                pids.Add((int)pid);
            }
            return true;
        }, IntPtr.Zero);
        return pids;
    }
}
