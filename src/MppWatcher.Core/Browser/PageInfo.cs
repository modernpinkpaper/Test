namespace MppWatcher.Core.Browser;

/// <summary>What a web page is about, worked out from its URL, title and a few visible texts.</summary>
public sealed record PageInfo
{
    /// <summary>"amazon", "seller_central", "amazon_ads", "keepa", "etsy", "shopify", "google_sheets", "google_drive", "google_docs", "gmail", "chatgpt", or "other".</summary>
    public string Site { get; init; } = "other";

    /// <summary>e.g. "product", "search", "listing_editor", "inventory", "search_query_performance", "orders".</summary>
    public string PageType { get; init; } = "page";

    /// <summary>Human name of the module/screen, e.g. "Manage All Inventory", "Search Query Performance".</summary>
    public string? Module { get; init; }

    public IReadOnlyList<string> Asins { get; init; } = Array.Empty<string>();
    public IReadOnlyList<string> Skus { get; init; } = Array.Empty<string>();
    public IReadOnlyList<string> ListingIds { get; init; } = Array.Empty<string>();
    public IReadOnlyList<string> ProductIds { get; init; } = Array.Empty<string>();
    public IReadOnlyList<string> OrderIds { get; init; } = Array.Empty<string>();
    public string? SearchTerm { get; init; }
    public string? DocumentId { get; init; }

    /// <summary>Product/listing/document title when it can be told apart from the page title.</summary>
    public string? ItemTitle { get; init; }

    /// <summary>Selected report settings found in the URL, e.g. date range, marketplace.</summary>
    public IReadOnlyDictionary<string, string> Filters { get; init; } = new Dictionary<string, string>();
}
