using System.Text.RegularExpressions;
using MppWatcher.Core.Configuration;
using MppWatcher.Core.Privacy;

namespace MppWatcher.Core.Ui;

public sealed record UiFieldDecision(bool Log, bool IncludeValue, string? Value, int ValueLength, bool IsSensitive, string Reason);

public sealed record UiActionDecision(bool Log, string? Action, string? ControlName, bool IsKeyAction, string Reason);

/// <summary>
/// The single place that decides what UI information may be recorded. The collector and the
/// diagnostic inspector both use it, so "would MT Log log this?" is always answered the
/// same way. Sensitive fields are refused before anything else is considered.
/// </summary>
public sealed class UiCapturePolicy
{
    public static readonly IReadOnlySet<string> FieldControlTypes = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
    {
        "Edit", "ComboBox", "Spinner",
    };

    private static readonly Dictionary<string, string> ActionByControlType = new(StringComparer.OrdinalIgnoreCase)
    {
        ["Button"] = "button_clicked",
        ["SplitButton"] = "button_clicked",
        ["MenuItem"] = "menu_item_clicked",
        ["Hyperlink"] = "link_clicked",
        ["TabItem"] = "tab_selected",
        ["ListItem"] = "item_selected",
        ["TreeItem"] = "item_selected",
        ["DataItem"] = "item_selected",
        ["CheckBox"] = "checkbox_toggled",
        ["RadioButton"] = "option_selected",
    };

    public static bool IsActionable(string controlType) => ActionByControlType.ContainsKey(controlType);

    private readonly Func<WatcherConfig> _config;
    private SensitiveFieldDetector? _detector;
    private string _detectorKey = "";
    private readonly UrlSanitizer _urls = new();

    public UiCapturePolicy(Func<WatcherConfig> config) => _config = config;

    public UiFieldDecision EvaluateField(UiElementInfo e)
    {
        var cfg = _config();
        var blocked = BlockReason(e, cfg);
        if (blocked is not null) return new(false, false, null, 0, false, blocked);

        var verdict = Detector(cfg).Evaluate(ToDescriptor(e));
        if (verdict.IsSensitive) return new(false, false, null, 0, true, "sensitive: " + verdict.Reason);

        if (!FieldControlTypes.Contains(e.ControlType)) return new(false, false, null, 0, false, $"not a text field ({e.ControlType})");
        if (!cfg.Collectors.UiAutomation.CaptureFieldValues) return new(false, false, null, 0, false, "field capture is turned off in config");

        var raw = !string.IsNullOrEmpty(e.Value) ? e.Value : e.SelectedItems;
        if (!e.HasValuePattern && string.IsNullOrEmpty(e.SelectedItems)) return new(false, false, null, 0, false, "Windows does not expose a value for this field");
        if (string.IsNullOrWhiteSpace(raw)) return new(false, false, null, 0, false, "field is empty");

        var value = raw.Trim();
        var max = cfg.Collectors.UiAutomation.MaxValueLength;
        if (value.Contains('\n') || value.Contains('\r') || value.Length > max)
            return new(true, false, null, value.Length, false, "value not stored: too long or multi-line (length only)");

        // Address bars and URL fields: remove tokens like any other URL.
        var url = _urls.Sanitize(value);
        if (url is not null && value.Contains('.') && !value.Contains(' ')) value = url.Url;

        return new(true, true, value, value.Length, false, "ok");
    }

    public UiActionDecision EvaluateAction(UiElementInfo e)
    {
        var cfg = _config();
        var blocked = BlockReason(e, cfg);
        if (blocked is not null) return new(false, null, null, false, blocked);
        if (!cfg.Collectors.UiAutomation.CaptureActions) return new(false, null, null, false, "action capture is turned off in config");
        if (!ActionByControlType.TryGetValue(e.ControlType, out var action)) return new(false, null, null, false, $"not an actionable control ({e.ControlType})");

        var name = CleanName(e.Name);
        if (string.IsNullOrEmpty(name)) return new(false, action, null, false, "control has no accessible name");

        var verdict = Detector(cfg).Evaluate(new FieldDescriptor(Name: name, AutomationId: e.AutomationId));
        if (verdict.IsSensitive) return new(false, action, null, false, "sensitive: " + verdict.Reason);

        var isKey = cfg.Collectors.UiAutomation.ActionKeywords.Any(k => ContainsWord(name, k));
        return new(true, action, name, isKey, "ok");
    }

    private string? BlockReason(UiElementInfo e, WatcherConfig cfg)
    {
        var p = cfg.Privacy;
        var proc = StripExe(e.ProcessName);
        if (WildcardMatcher.MatchesAny(proc, p.BlockedApplications.Select(x => StripExe(x)!))) return "blocked application";
        if (WildcardMatcher.MatchesAny(proc, cfg.Collectors.UiAutomation.IgnoreApplications.Select(x => StripExe(x)!))) return "application ignored for UI Automation";
        if (WildcardMatcher.MatchesAny(e.WindowTitle, p.BlockedWindowTitles)) return "blocked window title";
        foreach (var text in new[] { e.Name, e.AutomationId, e.LabeledBy })
            if (WildcardMatcher.MatchesAny(text, p.BlockedControls)) return "blocked control";
        return null;
    }

    private SensitiveFieldDetector Detector(WatcherConfig cfg)
    {
        var key = string.Join("\u001f", cfg.Privacy.SensitiveFieldTerms);
        if (_detector is null || key != _detectorKey)
        {
            _detector = new SensitiveFieldDetector(cfg.Privacy.SensitiveFieldTerms);
            _detectorKey = key;
        }
        return _detector;
    }

    public static FieldDescriptor ToDescriptor(UiElementInfo e) => new(
        Name: e.Name, AutomationId: e.AutomationId, LabelText: e.LabeledBy, ControlType: e.ControlType,
        ClassName: e.ClassName, HelpText: e.HelpText, IsPassword: e.IsPassword, Value: e.Value);

    internal static string? CleanName(string? name)
    {
        if (string.IsNullOrWhiteSpace(name)) return null;
        var n = Regex.Replace(name, @"\s+", " ").Trim();
        return n.Length > 100 ? n[..100] + "…" : n;
    }

    private static bool ContainsWord(string text, string word) =>
        !string.IsNullOrWhiteSpace(word) &&
        Regex.IsMatch(text, $@"(?<![A-Za-z]){Regex.Escape(word.Trim())}(?![A-Za-z])", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);

    private static string? StripExe(string? name) =>
        name is not null && name.EndsWith(".exe", StringComparison.OrdinalIgnoreCase) ? name[..^4] : name;
}
