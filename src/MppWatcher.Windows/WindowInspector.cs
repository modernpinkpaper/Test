using MppWatcher.Core.Activity;
using MppWatcher.Windows.Interop;

namespace MppWatcher.Windows;

/// <summary>Builds a <see cref="WindowSnapshot"/> for a window handle using plain Win32 calls.</summary>
internal sealed class WindowInspector
{
    private readonly ProcessInfoCache _processes;

    public WindowInspector(ProcessInfoCache processes) => _processes = processes;

    public WindowSnapshot? Inspect(IntPtr hwnd)
    {
        if (hwnd == IntPtr.Zero || !NativeMethods.IsWindow(hwnd)) return null;
        NativeMethods.GetWindowThreadProcessId(hwnd, out var pidRaw);
        var pid = (int)pidRaw;
        if (pid == 0) return null;

        var info = _processes.Get(pid);

        // Store apps (Calculator, Photos, new Outlook...) are hosted by ApplicationFrameHost.
        // The real app is a child window owned by another process.
        if (info.Name.Equals("ApplicationFrameHost", StringComparison.OrdinalIgnoreCase))
        {
            var childPid = FindHostedAppProcess(hwnd, pid);
            if (childPid != 0)
            {
                pid = childPid;
                info = _processes.Get(pid);
            }
        }

        return new WindowSnapshot(
            Handle: hwnd.ToInt64(),
            ProcessId: pid,
            ProcessName: info.Name,
            ApplicationName: info.ApplicationName,
            ExecutablePath: info.Path,
            Title: NativeMethods.GetWindowTitle(hwnd),
            WindowClass: NativeMethods.GetWindowClass(hwnd),
            Monitor: NativeMethods.GetMonitorName(hwnd));
    }

    /// <summary>Only re-reads the title; used on every poll while the same window stays in front.</summary>
    public static WindowSnapshot Refresh(WindowSnapshot previous) =>
        previous with { Title = NativeMethods.GetWindowTitle(new IntPtr(previous.Handle)) };

    private static int FindHostedAppProcess(IntPtr frame, int framePid)
    {
        var found = 0;
        NativeMethods.EnumChildWindows(frame, (child, _) =>
        {
            NativeMethods.GetWindowThreadProcessId(child, out var childPid);
            if (childPid != 0 && childPid != framePid)
            {
                found = (int)childPid;
                return false;
            }
            return true;
        }, IntPtr.Zero);
        return found;
    }
}
