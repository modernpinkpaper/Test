using System.Text;
using System.Text.Json.Nodes;
using MppWatcher.Core.Events;

namespace MppWatcher.Core.Ui;

/// <summary>Builds ui_field_value / ui_action events from an element and a policy decision.</summary>
public static class UiEventFactory
{
    public const string CollectorName = "ui_automation";
    public const string CollectorVersion = "1.0.0";

    public static WatchEvent FieldValue(UiElementInfo e, UiFieldDecision d, string trigger, bool edited, DateTimeOffset at)
    {
        var ev = Base(EventTypes.UiFieldValue, e, at);
        var m = ev.Metadata;
        m["label"] = UiCapturePolicy.CleanName(e.LabeledBy) ?? UiCapturePolicy.CleanName(e.Name);
        if (d.IncludeValue) m["value"] = d.Value;
        else
        {
            m["value_omitted"] = true;
            m["value_omitted_reason"] = d.Reason;
        }
        m["value_length"] = d.ValueLength;
        m["trigger"] = trigger;         // focus_left | value_settled
        m["edited"] = edited;
        ev.DedupFingerprint = $"{e.ProcessName}|{e.AutomationId}|{e.Name}|{d.Value}";
        return ev;
    }

    public static WatchEvent Action(UiElementInfo e, UiActionDecision d, string trigger, DateTimeOffset at)
    {
        var ev = Base(EventTypes.UiAction, e, at);
        var m = ev.Metadata;
        m["action"] = d.Action;
        m["control_name"] = d.ControlName;
        m["is_key_action"] = d.IsKeyAction;
        if (e.ToggleState is not null) m["state_after"] = e.ToggleState;
        m["trigger"] = trigger;         // click
        return ev;
    }

    private static WatchEvent Base(string type, UiElementInfo e, DateTimeOffset at)
    {
        var ev = new WatchEvent
        {
            EventType = type,
            TimestampUtc = at,
            Collector = CollectorName,
            CollectorVersion = CollectorVersion,
            Application = string.IsNullOrWhiteSpace(e.ApplicationName) ? e.ProcessName : e.ApplicationName,
            ProcessName = e.ProcessName,
            ProcessId = e.ProcessId == 0 ? null : e.ProcessId,
            WindowTitle = e.WindowTitle,
        };
        var m = ev.Metadata;
        m["control_type"] = e.ControlType;
        m["name"] = UiCapturePolicy.CleanName(e.Name);
        if (!string.IsNullOrEmpty(e.AutomationId)) m["automation_id"] = Short(e.AutomationId, 120);
        if (!string.IsNullOrEmpty(e.ClassName)) m["class_name"] = Short(e.ClassName, 80);
        if (!string.IsNullOrEmpty(e.FrameworkId)) m["framework"] = e.FrameworkId;
        if (e.AncestorPath.Count > 0) m["context_path"] = new JsonArray(e.AncestorPath.Select(a => (JsonNode)JsonValue.Create(a)!).ToArray());
        return ev;
    }

    /// <summary>"Group 'Personalization'" style description used in ancestor paths.</summary>
    public static string Describe(string controlType, string? name) =>
        string.IsNullOrWhiteSpace(name) ? controlType : $"{controlType} '{Short(UiCapturePolicy.CleanName(name)!, 50)}'";

    private static string Short(string s, int max) => s.Length <= max ? s : s[..max] + "…";

    /// <summary>
    /// Human-readable report for the diagnostic inspector: what Windows exposes about the
    /// element and what MPP Watcher would do with it. Sensitive values are never shown.
    /// </summary>
    public static string InspectionReport(UiElementInfo e, UiFieldDecision field, UiActionDecision action)
    {
        var sb = new StringBuilder();
        void Line(string k, object? v) => sb.Append(k.PadRight(22)).AppendLine(v?.ToString() ?? "");
        Line("Application", $"{e.ApplicationName} ({e.ProcessName}, pid {e.ProcessId})");
        Line("Window", e.WindowTitle);
        sb.AppendLine();
        Line("Control type", e.ControlType + (e.LocalizedControlType is { } l && !l.Equals(e.ControlType, StringComparison.OrdinalIgnoreCase) ? $"  ({l})" : ""));
        Line("Accessible name", e.Name);
        Line("Label (labeled-by)", e.LabeledBy);
        Line("Automation ID", e.AutomationId);
        Line("Class name", e.ClassName);
        Line("Framework", e.FrameworkId);
        Line("ARIA role", e.AriaRole);
        Line("Help text", e.HelpText);
        Line("Patterns", string.Join(", ", e.Patterns));
        Line("Is password", e.IsPassword);
        Line("Enabled / focused", $"{e.IsEnabled} / {e.HasKeyboardFocus}");
        if (e.ToggleState is not null) Line("Toggle state", e.ToggleState);
        if (!string.IsNullOrEmpty(e.SelectedItems)) Line("Selected", field.IsSensitive ? "(hidden: sensitive)" : e.SelectedItems);
        Line("Value", !e.HasValuePattern ? "(no value exposed)" : field.IsSensitive ? "(hidden: sensitive)" : Short(e.Value ?? "", 300));
        Line("Context", string.Join("  ›  ", e.AncestorPath));
        sb.AppendLine();
        Line("Sensitive?", field.IsSensitive ? "YES — " + field.Reason : "no");
        Line("Log field value?", field.Log ? (field.IncludeValue ? $"YES — value \"{field.Value}\"" : "YES, without value — " + field.Reason) : "no — " + field.Reason);
        Line("Log as action?", action.Log ? $"YES — {action.Action} \"{action.ControlName}\"{(action.IsKeyAction ? " (key action)" : "")}" : "no — " + action.Reason);
        return sb.ToString();
    }
}
