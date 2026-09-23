using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;
using MppWatcher.Core.Events;

namespace MppWatcher.Core.LocalApi;

public sealed record ApiResult(int Status, string Message, WatchEvent? Event = null);

/// <summary>
/// Checks a request to the local event API and turns it into an event. Pure logic (tested):
/// signature, timestamp window, replay, rate limit, and a strict shape for the body.
///
/// Signature: header X-MPP-Timestamp = unix seconds, header X-MPP-Signature = hex(HMAC-SHA256(secret, timestamp + "." + body)).
/// </summary>
public sealed class ApiRequestValidator
{
    public const int MaxBodyBytes = 16 * 1024;
    private static readonly Regex EventTypePattern = new("^[a-z][a-z0-9_]{1,49}$", RegexOptions.Compiled);
    private static readonly HashSet<string> KnownFields = new(StringComparer.Ordinal)
    {
        "event_type", "script_name", "sku", "listing_id", "asin", "order_id", "description", "timestamp", "data",
    };

    private readonly Func<byte[]> _secret;
    private readonly Func<TimeSpan> _maxSkew;
    private readonly Func<int> _perMinute;
    private readonly Queue<DateTimeOffset> _recent = new();
    private readonly Dictionary<string, DateTimeOffset> _seenSignatures = new();
    private readonly object _gate = new();

    public ApiRequestValidator(Func<byte[]> secret, Func<TimeSpan> maxSkew, Func<int> perMinute)
    {
        _secret = secret;
        _maxSkew = maxSkew;
        _perMinute = perMinute;
    }

    public static string Sign(byte[] secret, string timestamp, string body)
    {
        using var hmac = new HMACSHA256(secret);
        return Convert.ToHexString(hmac.ComputeHash(Encoding.UTF8.GetBytes(timestamp + "." + body))).ToLowerInvariant();
    }

    public ApiResult Validate(string? timestampHeader, string? signatureHeader, string body, string? origin, DateTimeOffset now)
    {
        // Web pages can send requests to localhost; only scripts with the secret (and no page origin) are accepted.
        if (!string.IsNullOrEmpty(origin) && !origin.StartsWith("chrome-extension://", StringComparison.Ordinal)
            && !origin.StartsWith("moz-extension://", StringComparison.Ordinal) && origin != "null")
            return new ApiResult(403, "requests from web pages are not accepted; use GM_xmlhttpRequest");
        if (Encoding.UTF8.GetByteCount(body) > MaxBodyBytes) return new ApiResult(413, "body too large");
        if (!long.TryParse(timestampHeader, out var unix)) return new ApiResult(401, "missing X-MPP-Timestamp");
        if (string.IsNullOrEmpty(signatureHeader)) return new ApiResult(401, "missing X-MPP-Signature");

        var sentAt = DateTimeOffset.FromUnixTimeSeconds(unix);
        if ((now - sentAt).Duration() > _maxSkew()) return new ApiResult(401, "timestamp too old or in the future");

        var expected = Sign(_secret(), timestampHeader!, body);
        if (!CryptographicOperations.FixedTimeEquals(Encoding.ASCII.GetBytes(expected), Encoding.ASCII.GetBytes(signatureHeader.Trim().ToLowerInvariant())))
            return new ApiResult(401, "bad signature");

        lock (_gate)
        {
            foreach (var old in _seenSignatures.Where(kv => now - kv.Value > _maxSkew() * 2).Select(kv => kv.Key).ToList()) _seenSignatures.Remove(old);
            if (!_seenSignatures.TryAdd(expected, now)) return new ApiResult(409, "duplicate request (replay)");
            while (_recent.Count > 0 && now - _recent.Peek() > TimeSpan.FromMinutes(1)) _recent.Dequeue();
            if (_recent.Count >= _perMinute()) return new ApiResult(429, "too many events");
            _recent.Enqueue(now);
        }

        JsonObject obj;
        try
        {
            obj = JsonNode.Parse(body) as JsonObject ?? throw new JsonException("not an object");
        }
        catch (JsonException ex)
        {
            return new ApiResult(400, "invalid JSON: " + ex.Message);
        }

        var unknown = obj.Select(kv => kv.Key).Where(k => !KnownFields.Contains(k)).ToList();
        if (unknown.Count > 0) return new ApiResult(400, "unknown fields: " + string.Join(", ", unknown) + " (put extra details in \"data\")");

        var type = Str(obj, "event_type");
        if (type is null || !EventTypePattern.IsMatch(type)) return new ApiResult(400, "event_type must be lowercase letters, digits, _ (e.g. automation_run)");
        var script = Str(obj, "script_name");
        if (string.IsNullOrWhiteSpace(script)) return new ApiResult(400, "script_name is required");
        if (obj["data"] is not null and not JsonObject) return new ApiResult(400, "data must be an object");

        var at = now;
        if (Str(obj, "timestamp") is { } ts)
        {
            if (!DateTimeOffset.TryParse(ts, out at)) return new ApiResult(400, "timestamp must be ISO 8601");
            if ((now - at).Duration() > TimeSpan.FromDays(1)) return new ApiResult(400, "timestamp must be within a day of now");
        }

        var e = new WatchEvent
        {
            EventType = type,
            TimestampUtc = at,
            Collector = "local_api",
            CollectorVersion = "1.0.0",
        };
        e.Metadata["script_name"] = Clip(script, 120);
        foreach (var key in new[] { "sku", "listing_id", "asin", "order_id" })
            if (Str(obj, key) is { } v) e.Metadata[key] = Clip(v, 80);
        if (Str(obj, "description") is { } d) e.Metadata["description"] = Clip(d, 1000);
        if (obj["data"] is JsonObject data) e.Metadata["data"] = data.DeepClone();
        e.Metadata["source"] = "local_api";
        return new ApiResult(202, "accepted", e);
    }

    private static string? Str(JsonObject o, string key) =>
        o[key] is JsonValue v && v.TryGetValue<string>(out var s) ? s : o[key] is JsonValue n ? n.ToJsonString() : null;

    private static string Clip(string s, int max) => s.Length <= max ? s : s[..max];
}
