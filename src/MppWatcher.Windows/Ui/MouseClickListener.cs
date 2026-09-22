using System.Runtime.InteropServices;
using MppWatcher.Windows.Interop;

namespace MppWatcher.Windows.Ui;

/// <summary>
/// Tells the UI Automation collector that a left click finished at a screen point, so it can
/// ask Windows which control is there. The point is used once and discarded; it is never logged.
/// Runs its own message-loop thread (required for low-level hooks) and does no work in the hook.
/// </summary>
internal sealed class MouseClickListener : IDisposable
{
    private readonly Action<int, int> _onClick;
    private readonly NativeMethods.LowLevelMouseProc _proc; // kept alive for the hook's lifetime
    private Thread? _thread;
    private IntPtr _hook;
    private uint _threadId;
    private readonly ManualResetEventSlim _ready = new();

    public MouseClickListener(Action<int, int> onClick)
    {
        _onClick = onClick;
        _proc = HookProc;
    }

    public bool Start()
    {
        _thread = new Thread(() =>
        {
            _threadId = GetCurrentThreadId();
            _hook = NativeMethods.SetWindowsHookEx(NativeMethods.WH_MOUSE_LL, _proc, NativeMethods.GetModuleHandle(null), 0);
            _ready.Set();
            if (_hook == IntPtr.Zero) return;
            Application.Run(); // message loop keeps the hook alive
            NativeMethods.UnhookWindowsHookEx(_hook);
            _hook = IntPtr.Zero;
        })
        { Name = "MPP click listener", IsBackground = true };
        _thread.SetApartmentState(ApartmentState.STA);
        _thread.Start();
        _ready.Wait(TimeSpan.FromSeconds(5));
        return _hook != IntPtr.Zero;
    }

    private IntPtr HookProc(int nCode, IntPtr wParam, IntPtr lParam)
    {
        if (nCode >= 0 && wParam == (IntPtr)NativeMethods.WM_LBUTTONUP)
        {
            var data = Marshal.PtrToStructure<NativeMethods.MSLLHOOKSTRUCT>(lParam);
            try { _onClick(data.pt.X, data.pt.Y); } catch { /* never block or break the user's mouse */ }
        }
        return NativeMethods.CallNextHookEx(_hook, nCode, wParam, lParam);
    }

    public void Dispose()
    {
        if (_threadId != 0) PostThreadMessage(_threadId, 0x0012 /* WM_QUIT */, IntPtr.Zero, IntPtr.Zero);
        _thread?.Join(TimeSpan.FromSeconds(3));
    }

    [DllImport("kernel32.dll")] private static extern uint GetCurrentThreadId();
    [DllImport("user32.dll")] private static extern bool PostThreadMessage(uint threadId, uint msg, IntPtr wParam, IntPtr lParam);
}
