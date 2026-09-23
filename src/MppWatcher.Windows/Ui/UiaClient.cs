using System.Runtime.InteropServices;
using Interop.UIAutomationClient;
using MppWatcher.Core.Ui;
using MppWatcher.Windows.Interop;

namespace MppWatcher.Windows.Ui;

/// <summary>
/// Thin, defensive wrapper around Windows UI Automation (UIA 3, COM).
/// Every call can fail (element gone, app busy): failures return null instead of throwing.
/// Use from a background (MTA) thread, never from a UI thread of this process.
/// </summary>
public sealed class UiaClient
{
    private const int PatternInvoke = 10000, PatternSelection = 10001, PatternValue = 10002, PatternExpandCollapse = 10005,
        PatternSelectionItem = 10010, PatternText = 10014, PatternToggle = 10015, PatternLegacy = 10018;

    private static readonly (int Id, string Name)[] PatternNames =
    {
        (PatternInvoke, "Invoke"), (PatternValue, "Value"), (PatternToggle, "Toggle"), (PatternSelection, "Selection"),
        (PatternSelectionItem, "SelectionItem"), (PatternExpandCollapse, "ExpandCollapse"), (PatternText, "Text"), (PatternLegacy, "LegacyIAccessible"),
    };

    private static readonly Dictionary<int, string> ControlTypes = new()
    {
        [50000] = "Button", [50001] = "Calendar", [50002] = "CheckBox", [50003] = "ComboBox", [50004] = "Edit", [50005] = "Hyperlink",
        [50006] = "Image", [50007] = "ListItem", [50008] = "List", [50009] = "Menu", [50010] = "MenuBar", [50011] = "MenuItem",
        [50012] = "ProgressBar", [50013] = "RadioButton", [50014] = "ScrollBar", [50015] = "Slider", [50016] = "Spinner",
        [50017] = "StatusBar", [50018] = "Tab", [50019] = "TabItem", [50020] = "Text", [50021] = "ToolBar", [50022] = "ToolTip",
        [50023] = "Tree", [50024] = "TreeItem", [50025] = "Custom", [50026] = "Group", [50027] = "Thumb", [50028] = "DataGrid",
        [50029] = "DataItem", [50030] = "Document", [50031] = "SplitButton", [50032] = "Window", [50033] = "Pane", [50034] = "Header",
        [50035] = "HeaderItem", [50036] = "Table", [50037] = "TitleBar", [50038] = "Separator", [50039] = "SemanticZoom", [50040] = "AppBar",
    };

    private readonly IUIAutomation2 _uia;
    private readonly IUIAutomationTreeWalker _walker;
    private readonly ProcessInfoCache _processes;

    public UiaClient() : this(new ProcessInfoCache()) { }

    internal UiaClient(ProcessInfoCache processes)
    {
        _processes = processes;
        _uia = (IUIAutomation2)new CUIAutomation8();
        // Do not hang on a frozen application.
        _uia.ConnectionTimeout = 2000;
        _uia.TransactionTimeout = 2000;
        _walker = _uia.ControlViewWalker;
    }

    internal IUIAutomation2 Automation => _uia;

    public static string ControlTypeName(int id) => ControlTypes.TryGetValue(id, out var n) ? n : "Unknown(" + id + ")";

    public IUIAutomationElement? ElementFromPoint(int x, int y) => Try(() => _uia.ElementFromPoint(new tagPOINT { x = x, y = y }));

    public IUIAutomationElement? FocusedElement() => Try(() => _uia.GetFocusedElement());

    public int ProcessIdOf(IUIAutomationElement el) => Try(() => el.CurrentProcessId);

    public string ControlTypeOf(IUIAutomationElement el) => ControlTypeName(Try(() => el.CurrentControlType));

    /// <summary>Just enough to decide whether a field may be read: type, name, id, password flag (4 calls).</summary>
    public UiElementInfo QuickIdentity(IUIAutomationElement el) => new()
    {
        ControlType = ControlTypeName(Try(() => el.CurrentControlType)),
        Name = Try(() => el.CurrentName),
        AutomationId = Try(() => el.CurrentAutomationId),
        IsPassword = Try(() => el.CurrentIsPassword) != 0,
    };

    public string? RuntimeIdOf(IUIAutomationElement el) => Try(() => string.Join(".", el.GetRuntimeId()));

    /// <summary>Walks up from e.g. the text inside a button to the button itself.</summary>
    public IUIAutomationElement? FindActionable(IUIAutomationElement el, int maxLevelsUp = 3)
    {
        var current = el;
        for (var i = 0; i <= maxLevelsUp && current is not null; i++)
        {
            if (UiCapturePolicy.IsActionable(ControlTypeOf(current))) return current;
            current = Try(() => _walker.GetParentElement(current));
        }
        return null;
    }

    /// <summary>
    /// Reads an element. The value is only read when <paramref name="readValue"/> is true, and
    /// never for password fields — the secret is not even fetched.
    /// </summary>
    public UiElementInfo Read(IUIAutomationElement el, bool readValue, bool detailed, IntPtr topWindow)
    {
        var controlType = ControlTypeName(Try(() => el.CurrentControlType));
        var pid = Try(() => el.CurrentProcessId);
        var proc = pid != 0 ? _processes.Get(pid) : null;
        var isPassword = Try(() => el.CurrentIsPassword) != 0;

        var valuePattern = Try(() => el.GetCurrentPattern(PatternValue) as IUIAutomationValuePattern);
        string? value = null;
        var readOnly = false;
        if (valuePattern is not null)
        {
            readOnly = Try(() => valuePattern.CurrentIsReadOnly) != 0;
            if (readValue && !isPassword) value = Try(() => valuePattern.CurrentValue);
        }

        string? toggle = null;
        if (controlType is "CheckBox" or "RadioButton" or "Button" or "MenuItem")
        {
            var tp = Try(() => el.GetCurrentPattern(PatternToggle) as IUIAutomationTogglePattern);
            if (tp is not null) toggle = Try(() => tp.CurrentToggleState) switch { ToggleState.ToggleState_On => "On", ToggleState.ToggleState_Off => "Off", _ => "Indeterminate" };
            if (controlType == "RadioButton")
            {
                var sel = Try(() => el.GetCurrentPattern(PatternSelectionItem) as IUIAutomationSelectionItemPattern);
                if (sel is not null) toggle = Try(() => sel.CurrentIsSelected) != 0 ? "Selected" : "Not selected";
            }
        }

        string? selected = null;
        if (readValue && !isPassword && controlType is "ComboBox" or "List" or "Tab")
        {
            var sp = Try(() => el.GetCurrentPattern(PatternSelection) as IUIAutomationSelectionPattern);
            var arr = sp is null ? null : Try(() => sp.GetCurrentSelection());
            if (arr is not null)
            {
                var names = new List<string>();
                for (var i = 0; i < Math.Min(Try(() => arr.Length), 10); i++)
                {
                    var n = Try(() => arr.GetElement(i).CurrentName);
                    if (!string.IsNullOrWhiteSpace(n)) names.Add(n);
                }
                if (names.Count > 0) selected = string.Join(", ", names);
            }
        }

        var patterns = new List<string>();
        if (detailed)
            foreach (var (id, name) in PatternNames)
                if (Try(() => el.GetCurrentPattern(id)) is not null) patterns.Add(name);

        return new UiElementInfo
        {
            ControlType = controlType,
            LocalizedControlType = detailed ? Try(() => el.CurrentLocalizedControlType) : null,
            Name = Try(() => el.CurrentName),
            AutomationId = Try(() => el.CurrentAutomationId),
            ClassName = Try(() => el.CurrentClassName),
            FrameworkId = Try(() => el.CurrentFrameworkId),
            HelpText = Try(() => el.CurrentHelpText),
            LabeledBy = Try(() => el.CurrentLabeledBy?.CurrentName),
            AriaRole = detailed ? Try(() => el.CurrentAriaRole) : null,
            IsPassword = isPassword,
            IsEnabled = Try(() => el.CurrentIsEnabled) != 0,
            IsOffscreen = Try(() => el.CurrentIsOffscreen) != 0,
            HasKeyboardFocus = Try(() => el.CurrentHasKeyboardFocus) != 0,
            HasValuePattern = valuePattern is not null,
            Value = value,
            IsReadOnly = readOnly,
            ToggleState = toggle,
            SelectedItems = selected,
            Patterns = patterns,
            AncestorPath = Ancestors(el),
            ProcessId = pid,
            ProcessName = proc?.Name,
            ApplicationName = proc?.ApplicationName ?? proc?.Name,
            WindowTitle = topWindow == IntPtr.Zero ? null : NativeMethods.GetWindowTitle(topWindow),
            RuntimeId = Try(() => string.Join(".", el.GetRuntimeId())),
        };
    }

    /// <summary>Re-reads only the value (cheap; used while a field has focus).</summary>
    public string? ReadValue(IUIAutomationElement el, out bool gone)
    {
        gone = false;
        try
        {
            if (el.CurrentIsPassword != 0) return null;
            var vp = el.GetCurrentPattern(PatternValue) as IUIAutomationValuePattern;
            if (vp is not null) return vp.CurrentValue;
            var sp = el.GetCurrentPattern(PatternSelection) as IUIAutomationSelectionPattern;
            var arr = sp?.GetCurrentSelection();
            return arr is { Length: > 0 } ? arr.GetElement(0).CurrentName : null;
        }
        catch (COMException)
        {
            gone = true; // element no longer available
            return null;
        }
    }

    /// <summary>Meaningful ancestors (named, or documents/windows), closest first, max 4.</summary>
    private IReadOnlyList<string> Ancestors(IUIAutomationElement el)
    {
        var list = new List<string>();
        var current = el;
        for (var depth = 0; depth < 10 && list.Count < 4; depth++)
        {
            current = Try(() => _walker.GetParentElement(current));
            if (current is null) break;
            var type = ControlTypeName(Try(() => current.CurrentControlType));
            var name = Try(() => current.CurrentName);
            if (!string.IsNullOrWhiteSpace(name) || type is "Document" or "Dialog")
                list.Add(UiEventFactory.Describe(type, name));
            if (type == "Window") break;
        }
        return list;
    }

    private static T? Try<T>(Func<T> f)
    {
        try { return f(); }
        catch (COMException) { return default; }
        catch (InvalidCastException) { return default; }
        catch (UnauthorizedAccessException) { return default; }
        catch (TimeoutException) { return default; }
    }
}
