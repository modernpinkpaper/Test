using System.Text.RegularExpressions;

namespace MppWatcher.Core.Browser;

public static class BrowserTitle
{
    // " - Google Chrome", " - Personal - Microsoft​ Edge", " — Mozilla Firefox".
    // Only Edge adds a profile name, and profile names are short (1–2 words: "Personal", "Work", "Profile 1").
    private static readonly Regex Suffix = new(
        @"\s+[-–—]\s+(?:(?:\S+(?:\s\S+)?\s+[-–—]\s+)?Microsoft\W{0,3}Edge|Google Chrome|Mozilla Firefox|Brave|Opera|Vivaldi)\s*$",
        RegexOptions.Compiled);

    /// <summary>The web page's own title, without the browser/profile suffix.</summary>
    public static string? PageTitle(string? windowTitle)
    {
        if (string.IsNullOrWhiteSpace(windowTitle)) return null;
        var t = Suffix.Replace(windowTitle, "").Trim();
        return t.Length == 0 ? null : t;
    }

    private static readonly HashSet<string> Placeholders = new(StringComparer.OrdinalIgnoreCase)
    {
        "Untitled", "New Tab", "New tab", "Loading", "Loading...", "Loading…", "about:blank",
    };

    /// <summary>True for titles browsers show while a page is still loading or empty.</summary>
    public static bool IsPlaceholder(string? pageTitle) => string.IsNullOrWhiteSpace(pageTitle) || Placeholders.Contains(pageTitle.Trim());
}
