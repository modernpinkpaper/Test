using System.Runtime.InteropServices;
using MppWatcher.Core.Configuration;
using MppWatcher.Core.Ui;
using MppWatcher.Windows.Interop;
using MppWatcher.Windows.Ui;

namespace MppWatcher.App;

/// <summary>
/// Diagnostic inspector: "What does Windows currently expose?"
/// Point the mouse at anything (or click into a field with "Focused element" on) and see the
/// control type, name, value, automation id, patterns, whether it is sensitive, and whether
/// MPP Watcher would log it. F8 freezes the display so you can move the mouse away.
/// Sensitive values are never shown.
/// </summary>
internal sealed class InspectorForm : Form
{
    private const int HotkeyId = 0x4D50;
    private const int WM_HOTKEY = 0x0312;
    private const uint VK_F8 = 0x77;

    private readonly ConfigProvider _config;
    private readonly UiCapturePolicy _policy;
    private readonly TextBox _report = new();
    private readonly CheckBox _focused = new() { Text = "Focused element (instead of mouse)", AutoSize = true };
    private readonly Label _state = new() { AutoSize = true, Padding = new Padding(0, 6, 0, 0) };
    private readonly System.Windows.Forms.Timer _timer = new() { Interval = 400 };
    private readonly Thread _worker;
    private readonly AutoResetEvent _request = new(false);
    private volatile bool _frozen, _closing;
    private (int X, int Y) _point;
    private string _lastKey = "";

    public InspectorForm(string configPath)
    {
        _config = new ConfigProvider(configPath, MppWatcher.Core.Diagnostics.NullDiagnosticLog.Instance);
        _policy = new UiCapturePolicy(() => _config.Current);

        Text = "MPP Watcher – Diagnostic Inspector";
        Icon = AppIcon.Get();
        Width = 640;
        Height = 720;
        TopMost = true;
        StartPosition = FormStartPosition.Manual;
        var area = Screen.PrimaryScreen!.WorkingArea;
        Location = new Point(area.Right - Width - 20, area.Top + 20);

        var bar = new FlowLayoutPanel { Dock = DockStyle.Top, Height = 38, Padding = new Padding(6, 4, 6, 0), WrapContents = false };
        var freeze = new Button { Text = "Freeze (F8)", AutoSize = true };
        freeze.Click += (_, _) => ToggleFreeze();
        var copy = new Button { Text = "Copy report", AutoSize = true };
        copy.Click += (_, _) => { if (_report.TextLength > 0) Clipboard.SetText(_report.Text); };
        var save = new Button { Text = "Save report…", AutoSize = true };
        save.Click += (_, _) => SaveReport();
        bar.Controls.AddRange(new Control[] { freeze, copy, save, _focused, _state });

        _report.Dock = DockStyle.Fill;
        _report.Multiline = true;
        _report.ReadOnly = true;
        _report.ScrollBars = ScrollBars.Both;
        _report.WordWrap = false;
        _report.Font = new Font("Consolas", 10f);
        _report.Text = "Point at any control in any application…";
        Controls.Add(_report);
        Controls.Add(bar);

        _worker = new Thread(WorkerLoop) { IsBackground = true, Name = "Inspector UI Automation" };
        _worker.SetApartmentState(ApartmentState.MTA); // UI Automation must not run on this window's thread
        _worker.Start();

        _timer.Tick += (_, _) => RequestRead();
        Load += (_, _) => { RegisterHotKey(Handle, HotkeyId, 0, VK_F8); _timer.Start(); UpdateState(); };
        FormClosing += (_, _) => { _closing = true; _timer.Stop(); UnregisterHotKey(Handle, HotkeyId); _request.Set(); };
    }

    private void RequestRead()
    {
        if (_frozen) return;
        if (!NativeMethods.GetCursorPos(out var p)) return;
        _point = (p.X, p.Y);
        _request.Set();
    }

    private void WorkerLoop()
    {
        UiaClient uia;
        try { uia = new UiaClient(); }
        catch (Exception e) { Show("UI Automation is not available on this PC: " + e.Message); return; }

        while (!_closing)
        {
            _request.WaitOne();
            if (_closing) break;
            try
            {
                var (x, y) = _point;
                var root = NativeMethods.RootWindowFromPoint(x, y);
                var element = _focused.Checked ? uia.FocusedElement() : uia.ElementFromPoint(x, y);
                if (element is null) { Show("(nothing exposed here)"); continue; }
                if (uia.ProcessIdOf(element) == Environment.ProcessId) continue; // pointing at the inspector itself
                if (_focused.Checked) root = NativeMethods.GetForegroundWindow();

                // Decide on the name/type first; only read the value if it is not sensitive.
                var info = uia.Read(element, readValue: false, detailed: true, root);
                var pre = _policy.EvaluateField(info with { Value = "x", HasValuePattern = true });
                if (!pre.IsSensitive) info = uia.Read(element, readValue: true, detailed: true, root);
                var field = _policy.EvaluateField(info);
                var action = _policy.EvaluateAction(info);
                var actionable = uia.FindActionable(element);
                var report = UiEventFactory.InspectionReport(info, field, action);
                if (actionable is not null && !ReferenceEquals(actionable, element) && uia.ControlTypeOf(actionable) != info.ControlType)
                {
                    var parent = uia.Read(actionable, readValue: false, detailed: false, root);
                    var parentAction = _policy.EvaluateAction(parent);
                    report += Environment.NewLine + $"A click here counts as: {(parentAction.Log ? $"{parentAction.Action} \"{parentAction.ControlName}\"" : "nothing — " + parentAction.Reason)} (parent {parent.ControlType})";
                }
                var key = info.RuntimeId + "|" + info.Value + "|" + info.ToggleState;
                if (key == _lastKey) continue;
                _lastKey = key;
                Show(report);
            }
            catch (Exception e)
            {
                Show("Could not read this element: " + e.Message);
            }
        }
    }

    private void Show(string text)
    {
        if (_closing || !IsHandleCreated) return;
        try { BeginInvoke(() => _report.Text = text.Replace("\n", Environment.NewLine).Replace("\r\r", "\r")); } catch (InvalidOperationException) { }
    }

    private void ToggleFreeze()
    {
        _frozen = !_frozen;
        UpdateState();
    }

    private void UpdateState() => _state.Text = _frozen ? "FROZEN — press F8 to continue" : "Live — press F8 to freeze";

    private void SaveReport()
    {
        using var dlg = new SaveFileDialog { FileName = $"mpp-inspect-{DateTime.Now:yyyyMMdd-HHmmss}.txt", Filter = "Text|*.txt" };
        if (dlg.ShowDialog(this) == DialogResult.OK) File.WriteAllText(dlg.FileName, _report.Text);
    }

    protected override void WndProc(ref Message m)
    {
        if (m.Msg == WM_HOTKEY && m.WParam == (IntPtr)HotkeyId) ToggleFreeze();
        base.WndProc(ref m);
    }

    [DllImport("user32.dll")] private static extern bool RegisterHotKey(IntPtr hWnd, int id, uint modifiers, uint vk);
    [DllImport("user32.dll")] private static extern bool UnregisterHotKey(IntPtr hWnd, int id);
}
