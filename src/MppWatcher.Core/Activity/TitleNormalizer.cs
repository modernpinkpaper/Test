using System.Text.RegularExpressions;

namespace MppWatcher.Core.Activity;

/// <summary>
/// Produces a comparison key for window titles so that cosmetic changes
/// (unread counters, "unsaved" markers, Photoshop zoom/layer info) do not count as a new task.
/// The real title is still recorded; this is only used to decide "is this the same thing?".
/// </summary>
public static class TitleNormalizer
{
    private static readonly Regex[] Removals =
    {
        new(@"^\s*\(\d+\+?\)\s*", RegexOptions.Compiled),                 // "(3) Inbox - Gmail"
        new(@"^\s*[●•*]\s*", RegexOptions.Compiled),                         // "● file.cs - VS Code"
        new(@"\s*[●•*]\s*$", RegexOptions.Compiled),                         // "Untitled *"
        new(@"\s*@\s*\d+(?:[.,]\d+)?%\s*(?:\([^)]*\))?\s*\*?", RegexOptions.Compiled), // "MA023.psd @ 66.7% (Layer 1, RGB/8) *"
        new(@"\s*-\s*(?:Saving|Saved|Saved to this PC|AutoSave (?:On|Off))\s*(?=-|$)", RegexOptions.Compiled | RegexOptions.IgnoreCase),
    };

    private static readonly Regex Spaces = new(@"\s+", RegexOptions.Compiled);

    public static string Normalize(string? title)
    {
        if (string.IsNullOrWhiteSpace(title)) return "";
        var t = title;
        foreach (var r in Removals) t = r.Replace(t, " ");
        return Spaces.Replace(t, " ").Trim().ToLowerInvariant();
    }
}
