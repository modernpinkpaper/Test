using System.Text;

namespace MppWatcher.Core.Privacy;

public sealed record SanitizedUrl(string Url, string Domain, bool WasModified);

/// <summary>
/// Cleans URLs before they are stored: removes user:password@, fragments that carry
/// tokens, and query parameters known to hold session or authentication data.
/// </summary>
public sealed class UrlSanitizer
{
    /// <summary>Built-in parameter names that are always removed (case-insensitive, exact name).</summary>
    public static readonly IReadOnlyList<string> BuiltInSensitiveParameters = new[]
    {
        "token", "access_token", "refresh_token", "id_token", "auth", "auth_token", "authtoken", "authorization",
        "code", "state", "nonce", "session", "sessionid", "session_id", "sid", "jsessionid", "phpsessid",
        "key", "api_key", "apikey", "secret", "client_secret", "password", "pwd", "pass", "signature", "sig",
        "x-amz-signature", "x-amz-credential", "x-amz-security-token", "x-goog-signature", "x-goog-credential",
        "saml", "samlresponse", "samlrequest", "ticket", "otp", "openid.assoc_handle", "openid.sig", "openid.claimed_id",
        "openid.identity", "openid.return_to", "sso", "ssotoken", "csrf", "csrf_token", "_csrf", "xsrf",
    };

    // Prefixes: any parameter starting with these is dropped (covers openid.*, oauth_*, etc.).
    private static readonly string[] SensitivePrefixes = { "openid.", "oauth_", "x-amz-", "x-goog-" };

    private readonly HashSet<string> _names;

    public UrlSanitizer(IEnumerable<string>? extraParameters = null)
    {
        _names = new HashSet<string>(BuiltInSensitiveParameters, StringComparer.OrdinalIgnoreCase);
        foreach (var p in extraParameters ?? Array.Empty<string>())
            if (!string.IsNullOrWhiteSpace(p)) _names.Add(p.Trim());
    }

    /// <summary>Returns null when the text is not an http(s) URL.</summary>
    public SanitizedUrl? Sanitize(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return null;
        var text = raw.Trim();
        // Browser address bars often hide the scheme ("keepa.com/#!product/1-B0...").
        if (!text.Contains("://", StringComparison.Ordinal) && LooksLikeHost(text)) text = "https://" + text;
        if (!Uri.TryCreate(text, UriKind.Absolute, out var uri)) return null;
        if (uri.Scheme != Uri.UriSchemeHttp && uri.Scheme != Uri.UriSchemeHttps) return null;

        var modified = !string.IsNullOrEmpty(uri.UserInfo);
        var query = FilterQuery(uri.Query, ref modified);
        var fragment = FilterFragment(uri.Fragment, ref modified);

        var sb = new StringBuilder();
        sb.Append(uri.Scheme).Append("://").Append(uri.Host);
        if (!uri.IsDefaultPort) sb.Append(':').Append(uri.Port);
        sb.Append(uri.AbsolutePath).Append(query).Append(fragment);
        return new SanitizedUrl(sb.ToString(), NormalizeDomain(uri.Host), modified);
    }

    public static string NormalizeDomain(string host)
    {
        var h = host.Trim().TrimEnd('.').ToLowerInvariant();
        return h.StartsWith("www.", StringComparison.Ordinal) ? h[4..] : h;
    }

    private string FilterQuery(string query, ref bool modified)
    {
        if (string.IsNullOrEmpty(query) || query == "?") return "";
        var kept = new List<string>();
        foreach (var part in query.TrimStart('?').Split('&', StringSplitOptions.RemoveEmptyEntries))
        {
            var name = Uri.UnescapeDataString(part.Split('=', 2)[0]);
            if (IsSensitiveName(name)) { modified = true; continue; }
            kept.Add(part);
        }
        return kept.Count == 0 ? "" : "?" + string.Join('&', kept);
    }

    private string FilterFragment(string fragment, ref bool modified)
    {
        if (string.IsNullOrEmpty(fragment)) return "";
        // OAuth implicit flow puts tokens in the fragment: #access_token=...&state=...
        if (fragment.Contains('=') && fragment.TrimStart('#').Split('&').Any(p => IsSensitiveName(Uri.UnescapeDataString(p.Split('=', 2)[0]))))
        {
            modified = true;
            return "";
        }
        return fragment;
    }

    private bool IsSensitiveName(string name) =>
        _names.Contains(name) || SensitivePrefixes.Any(p => name.StartsWith(p, StringComparison.OrdinalIgnoreCase));

    private static bool LooksLikeHost(string text)
    {
        var host = text.Split('/', 2)[0];
        return host.Contains('.') && !host.Contains(' ') && Uri.CheckHostName(host.Split(':')[0]) != UriHostNameType.Unknown;
    }
}
