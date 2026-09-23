using System.Text.RegularExpressions;

namespace MppWatcher.Core.Files;

/// <summary>What a desktop app's window title says about the open document.</summary>
public sealed record DocumentInfo(string DocumentName, string? Extension, bool Unsaved, string App);

/// <summary>
/// Reads the open document out of window titles of business apps, e.g.
/// "MA023-main.psd @ 66.7% (Layer 1, RGB/8) *" (Photoshop),
/// "ShopifyInventory.xlsx - Excel", "PS142.indd @ 75% - Adobe InDesign".
/// Pure logic, tested with titles as the apps show them.
/// </summary>
public static class DocumentTitleParser
{
    private static readonly (string Process, string App, Regex Pattern)[] Rules =
    {
        // Adobe apps: "Name.ext @ 66.7% (details) *" optionally followed by " - Adobe Photoshop 2025"
        ("photoshop", "Photoshop", new(@"^(?<doc>.+?\.(?:psd|psb|png|jpe?g|tiff?|gif|webp|heic|pdf))(?:\s+@\s+[\d.,]+%[^*]*)?(?<dirty>\s*\*)?(?:\s+[-–]\s+Adobe Photoshop.*)?$", RegexOptions.IgnoreCase)),
        ("indesign", "InDesign", new(@"^(?:\*)?(?<doc>.+?\.(?:indd|indt|idml|indb))(?:\s+@\s+[\d.,]+%.*?)?(?<dirty>\s*\*)?(?:\s+[-–]\s+Adobe InDesign.*)?$", RegexOptions.IgnoreCase)),
        ("illustrator", "Illustrator", new(@"^(?<doc>.+?\.(?:ai|eps|svg|pdf))(?:\*)?(?:\s+@\s+[\d.,]+%.*?)?(?<dirty>\s*\*)?(?:\s+[-–]\s+Adobe Illustrator.*)?$", RegexOptions.IgnoreCase)),
        ("excel", "Excel", new(@"^(?<dirty>\*\s*)?(?<doc>.+?)(?:\s+-\s+(?:Saved|Saving|AutoSave On|AutoSave Off|Read-Only|Compatibility Mode)\S*)*\s+-\s+(?:Microsoft\s+)?Excel$", RegexOptions.IgnoreCase)),
        ("winword", "Word", new(@"^(?<dirty>\*\s*)?(?<doc>.+?)(?:\s+-\s+(?:Saved|Saving|Read-Only|Compatibility Mode)\S*)*\s+-\s+(?:Microsoft\s+)?Word$", RegexOptions.IgnoreCase)),
        ("acrobat", "Acrobat", new(@"^(?<doc>.+?\.pdf)(?:\s+-\s+Adobe Acrobat.*)?$", RegexOptions.IgnoreCase)),
        ("acrord32", "Acrobat Reader", new(@"^(?<doc>.+?\.pdf)(?:\s+-\s+Adobe Acrobat.*)?$", RegexOptions.IgnoreCase)),
        ("notepad", "Notepad", new(@"^(?<dirty>\*)?(?<doc>.+?)\s+-\s+Notepad$", RegexOptions.IgnoreCase)),
        ("code", "VS Code", new(@"^(?<dirty>●\s*)?(?<doc>[^-]+?)\s+-\s+.+?\s+-\s+Visual Studio Code$", RegexOptions.IgnoreCase)),
        ("notepad++", "Notepad++", new(@"^(?<dirty>\*)?(?<doc>.+?)\s+-\s+Notepad\+\+$", RegexOptions.IgnoreCase)),
    };

    public static DocumentInfo? Parse(string? processName, string? windowTitle)
    {
        if (string.IsNullOrWhiteSpace(processName) || string.IsNullOrWhiteSpace(windowTitle)) return null;
        var proc = processName.ToLowerInvariant();
        foreach (var (p, app, pattern) in Rules)
        {
            if (proc != p) continue;
            var m = pattern.Match(windowTitle.Trim());
            if (!m.Success) return null;
            var doc = m.Groups["doc"].Value.Trim().Trim('*').Trim();
            if (doc.Length == 0 || IsAppHomeTitle(doc)) return null;
            var ext = Path.GetExtension(doc);
            return new DocumentInfo(doc, string.IsNullOrEmpty(ext) ? null : ext.TrimStart('.').ToLowerInvariant(), m.Groups["dirty"].Success, app);
        }
        return null;
    }

    private static bool IsAppHomeTitle(string doc) =>
        Regex.IsMatch(doc, @"^(Adobe (Photoshop|InDesign|Illustrator)|Home|Start|Untitled|Book\d*|Document\d*)$", RegexOptions.IgnoreCase) && !doc.Contains('.');
}

/// <summary>Finds product codes (SKUs) in file and document names, e.g. "MA023-main.psd" → MA023.</summary>
public static class SkuFinder
{
    /// <summary>Default: 2–4 capital letters followed by 2–5 digits, e.g. MA023, PS142, ABC1234.</summary>
    public const string DefaultPattern = @"(?<![A-Za-z0-9])[A-Z]{2,4}\d{2,5}(?![0-9])";

    public static IReadOnlyList<string> Find(string? text, IEnumerable<string>? patterns = null)
    {
        if (string.IsNullOrWhiteSpace(text)) return Array.Empty<string>();
        var list = new List<string>();
        foreach (var p in patterns is null || !patterns.Any() ? new[] { DefaultPattern } : patterns)
        {
            try
            {
                foreach (Match m in Regex.Matches(text, p, RegexOptions.None, TimeSpan.FromMilliseconds(200)))
                    if (!Browser.SiteProfiles.IsAsin(m.Value) && !list.Contains(m.Value)) list.Add(m.Value);
            }
            catch (ArgumentException) { /* bad pattern in config: ignore it */ }
            catch (RegexMatchTimeoutException) { }
        }
        return list;
    }
}
