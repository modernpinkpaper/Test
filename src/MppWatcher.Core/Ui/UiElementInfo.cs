namespace MppWatcher.Core.Ui;

/// <summary>
/// Plain snapshot of one UI element as Windows UI Automation exposes it.
/// Filled by the Windows layer; all decisions about it are made in Core (testable).
/// </summary>
public sealed record UiElementInfo
{
    public string ControlType { get; init; } = "";         // "Edit", "Button", ...
    public string? LocalizedControlType { get; init; }
    public string? Name { get; init; }                     // accessible name
    public string? AutomationId { get; init; }
    public string? ClassName { get; init; }
    public string? FrameworkId { get; init; }              // "Win32", "WinForm", "WPF", "Chrome", "XAML", ...
    public string? HelpText { get; init; }
    public string? LabeledBy { get; init; }                // name of the label element, if any
    public string? AriaRole { get; init; }
    public bool IsPassword { get; init; }
    public bool IsEnabled { get; init; } = true;
    public bool IsOffscreen { get; init; }
    public bool HasKeyboardFocus { get; init; }

    public bool HasValuePattern { get; init; }
    public string? Value { get; init; }                    // raw value; NEVER logged without the policy
    public bool IsReadOnly { get; init; }
    public string? ToggleState { get; init; }              // "On" / "Off" / "Indeterminate"
    public string? SelectedItems { get; init; }            // selection pattern text, e.g. combo box choice
    public IReadOnlyList<string> Patterns { get; init; } = Array.Empty<string>();

    /// <summary>Nearest ancestors, closest first, e.g. ["Group 'Personalization'", "Document 'Etsy'"].</summary>
    public IReadOnlyList<string> AncestorPath { get; init; } = Array.Empty<string>();

    public int ProcessId { get; init; }
    public string? ProcessName { get; init; }
    public string? ApplicationName { get; init; }
    public string? WindowTitle { get; init; }

    /// <summary>Stable id of the element while it exists (UI Automation runtime id).</summary>
    public string? RuntimeId { get; init; }
}
