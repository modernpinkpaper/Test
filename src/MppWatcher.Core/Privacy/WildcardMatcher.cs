using System.Collections.Concurrent;
using System.Text.RegularExpressions;

namespace MppWatcher.Core.Privacy;

/// <summary>Case-insensitive * and ? wildcard matching, used by all block lists.</summary>
public static class WildcardMatcher
{
    private static readonly ConcurrentDictionary<string, Regex> Cache = new();

    public static bool IsMatch(string? text, string pattern)
    {
        if (text is null || string.IsNullOrWhiteSpace(pattern)) return false;
        var regex = Cache.GetOrAdd(pattern.Trim(), p => new Regex(
            "^" + Regex.Escape(p).Replace(@"\*", ".*").Replace(@"\?", ".") + "$",
            RegexOptions.IgnoreCase | RegexOptions.CultureInvariant | RegexOptions.Singleline));
        return regex.IsMatch(text);
    }

    public static bool MatchesAny(string? text, IEnumerable<string>? patterns) =>
        text is not null && patterns is not null && patterns.Any(p => IsMatch(text, p));
}
