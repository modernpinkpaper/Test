using System.Collections.Concurrent;
using System.Text.Json.Nodes;
using MppWatcher.Core.Browser;
using MppWatcher.Core.Events;

namespace MppWatcher.Core.Activity;

/// <summary>A web page as last read from a browser window.</summary>
public sealed record BrowserPage(long WindowHandle, int ProcessId, string Url, string Domain, string? PageTitle, string WindowTitle, PageInfo Info, DateTimeOffset ReadAt);

/// <summary>
/// Shared, thread-safe "what is on screen right now": the current foreground session and
/// the page open in each browser window. The pipeline uses it to add session_id, url, domain,
/// page_title and page facts (ASIN, SKU, ...) to events from other collectors, so a field value
/// or a button click is always tied to the page it happened on.
/// </summary>
public sealed class ActivityContext
{
    private readonly ConcurrentDictionary<long, BrowserPage> _pages = new();
    private volatile SessionRef? _session;

    private sealed record SessionRef(string SessionId, long WindowHandle, int ProcessId);

    public string? CurrentSessionId => _session?.SessionId;

    /// <summary>Called for every event before it is stored; keeps track of the open session.</summary>
    public void Observe(WatchEvent e)
    {
        if (e.EventType == EventTypes.AppSessionStart && e.SessionId is not null)
            _session = new SessionRef(e.SessionId, ParseHandle(e.Metadata["window_handle"]?.ToString()), e.ProcessId ?? 0);
        else if (e.EventType == EventTypes.AppSessionEnd && _session?.SessionId == e.SessionId)
            _session = null;
    }

    public void SetPage(BrowserPage page)
    {
        _pages[page.WindowHandle] = page;
        if (_pages.Count > 50)
            foreach (var old in _pages.Values.OrderBy(p => p.ReadAt).Take(_pages.Count - 50)) _pages.TryRemove(old.WindowHandle, out _);
    }

    public BrowserPage? PageFor(long windowHandle) => _pages.TryGetValue(windowHandle, out var p) ? p : null;

    /// <summary>
    /// Fills in missing session/page context. Page facts are only attached when the event's window
    /// title still matches the title the page was read with — so an old URL is never attached to a new page.
    /// </summary>
    public void Enrich(WatchEvent e)
    {
        var s = _session;
        if (e.SessionId is null && s is not null && e.ProcessId == s.ProcessId && e.EventType != EventTypes.AppSessionEnd)
            e.SessionId = s.SessionId;
        if (e.Url is not null || e.WindowTitle is null || e.ProcessId is null) return;

        var key = TitleNormalizer.Normalize(e.WindowTitle);
        var page = _pages.Values.FirstOrDefault(p => p.ProcessId == e.ProcessId && TitleNormalizer.Normalize(p.WindowTitle) == key);
        if (page is null) return;
        e.Url = page.Url;
        e.Domain = page.Domain;
        e.PageTitle ??= page.PageTitle;
        if (e.EventType is EventTypes.AppSessionStart or EventTypes.AppSessionEnd or EventTypes.UiFieldValue or EventTypes.UiAction)
        {
            var info = PageJson(page.Info, compact: true);
            if (info.Count > 0) e.Metadata["page"] = info;
        }
    }

    /// <summary>PageInfo as JSON; empty lists/values are left out.</summary>
    public static JsonObject PageJson(PageInfo p, bool compact)
    {
        var o = new JsonObject();
        if (p.Site != "other" || !compact) o["site"] = p.Site;
        if (p.Site != "other" || !compact) o["page_type"] = p.PageType;
        void Add(string key, string? v) { if (!string.IsNullOrEmpty(v)) o[key] = v; }
        void AddList(string key, IReadOnlyList<string> v) { if (v.Count > 0) o[key] = new JsonArray(v.Select(x => (JsonNode)JsonValue.Create(x)!).ToArray()); }
        Add("module", p.Module);
        AddList("asins", p.Asins);
        AddList("skus", p.Skus);
        AddList("listing_ids", p.ListingIds);
        AddList("product_ids", p.ProductIds);
        AddList("order_ids", p.OrderIds);
        Add("search_term", p.SearchTerm);
        Add("document_id", p.DocumentId);
        Add("item_title", p.ItemTitle);
        if (p.Filters.Count > 0)
        {
            var f = new JsonObject();
            foreach (var (k, v) in p.Filters) f[k] = v;
            o["filters"] = f;
        }
        return o;
    }

    private static long ParseHandle(string? hex) =>
        hex is not null && hex.StartsWith("0x", StringComparison.OrdinalIgnoreCase) && long.TryParse(hex[2..], System.Globalization.NumberStyles.HexNumber, null, out var h) ? h : 0;
}
