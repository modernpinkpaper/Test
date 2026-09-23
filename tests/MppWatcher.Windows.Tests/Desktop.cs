using System.Diagnostics;
using System.Runtime.InteropServices;
using MppWatcher.Core.Collectors;
using MppWatcher.Core.Events;

namespace MppWatcher.Windows.Tests;

/// <summary>Helpers that act like a user on the real Windows desktop.</summary>
internal static class Desktop
{
    private const byte VK_MENU = 0x12;
    private const uint KEYEVENTF_KEYUP = 0x2;
    private const int SW_RESTORE = 9;
    private const uint INPUT_MOUSE = 0;
    private const uint MOUSEEVENTF_MOVE = 0x0001;

    [DllImport("user32.dll")] private static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] private static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] private static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")] private static extern void keybd_event(byte vk, byte scan, uint flags, UIntPtr extra);
    [DllImport("user32.dll", SetLastError = true)] private static extern uint SendInput(uint count, INPUT[] inputs, int size);

    [StructLayout(LayoutKind.Sequential)]
    private struct INPUT { public uint type; public MOUSEINPUT mi; }

    [StructLayout(LayoutKind.Sequential)]
    private struct MOUSEINPUT { public int dx, dy; public uint mouseData, dwFlags, time; public IntPtr dwExtraInfo; }

    /// <summary>Bring a window to the front the way a user would (Windows only allows this after an input event).</summary>
    public static bool BringToFront(IntPtr hwnd)
    {
        for (var i = 0; i < 10; i++)
        {
            keybd_event(VK_MENU, 0, 0, UIntPtr.Zero);
            keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
            ShowWindow(hwnd, SW_RESTORE);
            SetForegroundWindow(hwnd);
            Thread.Sleep(100);
            if (GetForegroundWindow() == hwnd) return true;
        }
        return false;
    }

    /// <summary>Tiny mouse move: counts as user input for idle detection.</summary>
    public static void NudgeMouse()
    {
        var inputs = new[]
        {
            new INPUT { type = INPUT_MOUSE, mi = new MOUSEINPUT { dx = 1, dwFlags = MOUSEEVENTF_MOVE } },
            new INPUT { type = INPUT_MOUSE, mi = new MOUSEINPUT { dx = -1, dwFlags = MOUSEEVENTF_MOVE } },
        };
        SendInput((uint)inputs.Length, inputs, Marshal.SizeOf<INPUT>());
    }

    private const uint KEYEVENTF_UNICODE = 0x0004;
    private const uint INPUT_KEYBOARD = 1;
    private const uint MOUSEEVENTF_LEFTDOWN = 0x0002, MOUSEEVENTF_LEFTUP = 0x0004;

    [StructLayout(LayoutKind.Sequential)]
    private struct KEYBDINPUT { public ushort wVk, wScan; public uint dwFlags, time; public IntPtr dwExtraInfo; }

    [StructLayout(LayoutKind.Explicit)]
    private struct KINPUT
    {
        [FieldOffset(0)] public uint type;
        [FieldOffset(8)] public KEYBDINPUT ki;
        [FieldOffset(8)] public MOUSEINPUT mi;
    }

    [DllImport("user32.dll", EntryPoint = "SendInput", SetLastError = true)] private static extern uint SendKInput(uint count, KINPUT[] inputs, int size);
    [DllImport("user32.dll")] private static extern bool SetCursorPos(int x, int y);

    /// <summary>Types text like a person would (used only by tests to simulate an employee).</summary>
    public static void TypeText(string text)
    {
        foreach (var ch in text)
        {
            var inputs = new[]
            {
                new KINPUT { type = INPUT_KEYBOARD, ki = new KEYBDINPUT { wScan = ch, dwFlags = KEYEVENTF_UNICODE } },
                new KINPUT { type = INPUT_KEYBOARD, ki = new KEYBDINPUT { wScan = ch, dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP } },
            };
            SendKInput(2, inputs, Marshal.SizeOf<KINPUT>());
            Thread.Sleep(15);
        }
    }

    public static void MoveMouse(Point p) => SetCursorPos(p.X, p.Y);

    public static void PressEnter()
    {
        keybd_event(0x0D, 0, 0, UIntPtr.Zero);
        keybd_event(0x0D, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
        Thread.Sleep(200);
    }

    public static void Click(Point p)
    {
        SetCursorPos(p.X, p.Y);
        Thread.Sleep(50);
        var inputs = new[]
        {
            new KINPUT { type = INPUT_MOUSE, mi = new MOUSEINPUT { dwFlags = MOUSEEVENTF_LEFTDOWN } },
            new KINPUT { type = INPUT_MOUSE, mi = new MOUSEINPUT { dwFlags = MOUSEEVENTF_LEFTUP } },
        };
        SendKInput(2, inputs, Marshal.SizeOf<KINPUT>());
        Thread.Sleep(250);
    }

    public static bool WaitUntil(Func<bool> condition, TimeSpan timeout)
    {
        var sw = Stopwatch.StartNew();
        while (sw.Elapsed < timeout)
        {
            if (condition()) return true;
            Thread.Sleep(100);
        }
        return condition();
    }
}

/// <summary>A real top-level window on its own UI thread, like any app window.</summary>
internal sealed class TestWindow : IDisposable
{
    private readonly Thread _thread;
    private Form? _form;
    private readonly ManualResetEventSlim _ready = new();

    public TestWindow(string title, Action<Form>? build = null)
    {
        _thread = new Thread(() =>
        {
            _form = new Form { Text = title, Width = 500, Height = 300, StartPosition = FormStartPosition.CenterScreen, ShowInTaskbar = true };
            build?.Invoke(_form);
            _form.Shown += (_, _) => _ready.Set();
            Application.Run(_form);
        });
        _thread.SetApartmentState(ApartmentState.STA);
        _thread.IsBackground = true;
        _thread.Start();
        if (!_ready.Wait(TimeSpan.FromSeconds(10))) throw new TimeoutException("Test window did not open");
        Handle = (IntPtr)_form!.Invoke(() => _form.Handle);
    }

    public IntPtr Handle { get; }

    public void SetTitle(string title) => _form!.Invoke(() => _form.Text = title);

    /// <summary>Screen centre of a child control, found by its Name.</summary>
    public Point CenterOf(string controlName) => (Point)_form!.Invoke(() =>
    {
        var c = _form.Controls.Find(controlName, true).Single();
        var r = c.RectangleToScreen(c.ClientRectangle);
        return new Point(r.Left + r.Width / 2, r.Top + r.Height / 2);
    });

    public void Dispose()
    {
        try { _form?.Invoke(() => _form.Close()); } catch { /* already closed */ }
        _thread.Join(TimeSpan.FromSeconds(5));
    }
}

internal sealed class ListSink : IEventSink
{
    private readonly List<WatchEvent> _events = new();

    public void Emit(WatchEvent e) { lock (_events) _events.Add(e); }

    public List<WatchEvent> All { get { lock (_events) return _events.ToList(); } }

    public List<WatchEvent> OfType(string type) => All.Where(e => e.EventType == type).ToList();

    public string Dump() => string.Join(Environment.NewLine, All.Select(e =>
        $"{e.TimestampUtc:HH:mm:ss.fff} {e.EventType} [{e.ProcessName}] \"{e.WindowTitle}\" {e.Metadata.ToJsonString()}"));
}
