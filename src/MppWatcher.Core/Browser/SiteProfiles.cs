using System.Text.RegularExpressions;
using System.Web;

namespace MppWatcher.Core.Browser;

/// <summary>
/// Rules that turn a (sanitized) URL, page title and a few visible texts into business facts:
/// which site and screen, which ASINs / SKUs / listing ids / product ids, which search term.
/// Pure logic — tested without a browser. Add new sites here.
/// </summary>
public static class SiteProfiles
{
    // Amazon ASINs are 10 chars; product ASINs start with B0. ISBN-10 ASINs (books) are digits.
    private static readonly Regex AsinInPath = new(@"/(?:dp|gp/product|gp/aw/d|product|asin|dp/product)/([A-Z0-9]{10})(?=[/?#]|$)", RegexOptions.Compiled | RegexOptions.IgnoreCase);
    private static readonly Regex AsinAnywhere = new(@"(?<![A-Z0-9])(B0[A-Z0-9]{8})(?![A-Z0-9])", RegexOptions.Compiled);
    private static readonly Regex SkuInText = new(@"\b(?:Seller\s+)?SKU\s*[:#]?\s*([A-Za-z0-9][A-Za-z0-9._\-]{1,39})\b", RegexOptions.Compiled | RegexOptions.IgnoreCase);
    private static readonly Regex AsinInText = new(@"\bASIN\s*[:#]?\s*([A-Z0-9]{10})\b", RegexOptions.Compiled);

    private static readonly (string Prefix, string PageType, string Module)[] SellerCentralModules =
    {
        ("/brand-analytics/dashboard/query-performance", "search_query_performance", "Search Query Performance"),
        ("/brand-analytics/dashboard/search-terms", "search_terms_report", "Amazon Search Terms"),
        ("/brand-analytics", "brand_analytics", "Brand Analytics"),
        ("/business-reports", "business_reports", "Business Reports"),
        ("/reportcentral", "reports", "Report Central"),
        ("/reports", "reports", "Reports"),
        ("/myinventory/inventory", "inventory", "Manage All Inventory"),
        ("/inventory", "inventory", "Manage All Inventory"),
        ("/skucentral", "sku_central", "SKU Central"),
        ("/abis/listing/edit", "listing_editor", "Edit Listing"),
        ("/listing/edit", "listing_editor", "Edit Listing"),
        ("/abis/listing/syh", "listing_create", "Add a Product"),
        ("/product-search", "add_product", "Add a Product"),
        ("/listing/varwiz", "variation_wizard", "Variation Wizard"),
        ("/variations", "variations", "Variations"),
        ("/customization", "customization", "Customization"),
        ("/gestalt/customization", "customization", "Customization"),
        ("/imaging", "images", "Image Manager"),
        ("/orders-v3/order", "order_detail", "Order Details"),
        ("/orders-v3", "orders", "Manage Orders"),
        ("/messaging", "buyer_messages", "Buyer Messages"),
        ("/fba", "fba", "Fulfillment by Amazon"),
        ("/pricing", "pricing", "Pricing"),
        ("/performance", "account_health", "Account Health"),
        ("/payments", "payments", "Payments"),
        ("/listing/upload", "file_upload", "Add Products via Upload"),
        ("/listing/status", "upload_status", "Upload Status"),
        ("/home", "home", "Home"),
    };

    public static PageInfo Analyze(Uri url, string? pageTitle, IReadOnlyList<string>? visibleTexts = null)
    {
        var host = url.Host.ToLowerInvariant();
        var path = url.AbsolutePath;
        var q = HttpUtility.ParseQueryString(url.Query);
        var fragment = Uri.UnescapeDataString(url.Fragment.TrimStart('#'));
        var texts = visibleTexts ?? Array.Empty<string>();

        PageInfo info;
        if (IsHost(host, "sellercentral.amazon.") || host.StartsWith("sellercentral-europe.amazon.", StringComparison.Ordinal) || IsHost(host, "sellercentral-japan.amazon."))
            info = SellerCentral(path, q);
        else if (IsHost(host, "advertising.amazon."))
            info = new PageInfo { Site = "amazon_ads", PageType = path.Contains("/campaigns") ? "campaigns" : "ads", Module = "Amazon Advertising" };
        else if (IsAmazonRetail(host))
            info = AmazonRetail(path, q);
        else if (IsHost(host, "keepa.com"))
            info = Keepa(fragment, q);
        else if (IsHost(host, "etsy.com"))
            info = Etsy(path, q);
        else if (host == "admin.shopify.com" || host.EndsWith(".myshopify.com", StringComparison.Ordinal))
            info = Shopify(host, path, q);
        else if (host == "docs.google.com")
            info = GoogleDocs(path);
        else if (host == "drive.google.com")
            info = new PageInfo { Site = "google_drive", PageType = path.Contains("/folders/") ? "folder" : "drive", DocumentId = Segment(path, "folders") };
        else if (host == "mail.google.com")
            info = new PageInfo { Site = "gmail", PageType = fragment.StartsWith("search/", StringComparison.Ordinal) ? "search" : "mail" };
        else if (host is "chatgpt.com" or "chat.openai.com")
            info = new PageInfo { Site = "chatgpt", PageType = path.StartsWith("/c/", StringComparison.Ordinal) ? "conversation" : "chat", DocumentId = Segment(path, "c") };
        else
            info = new PageInfo();

        return AddFromText(info, pageTitle, texts);
    }

    private static PageInfo SellerCentral(string path, System.Collections.Specialized.NameValueCollection q)
    {
        var (type, module) = ("page", (string?)null);
        foreach (var m in SellerCentralModules)
        {
            if (path.StartsWith(m.Prefix, StringComparison.OrdinalIgnoreCase)) { type = m.PageType; module = m.Module; break; }
        }
        var skus = Values(q, "sku", "mSku", "msku", "merchantSku", "seller-sku", "sellerSku");
        var asins = Values(q, "asin", "ASIN", "asins").Concat(AsinsIn(path)).ToList();
        var search = First(q, "searchTerm", "search", "searchField", "query", "q", "keyword", "fulfilledBy") is { } s && !IsAsin(s) ? s : null;
        var filters = new Dictionary<string, string>();
        foreach (var key in new[] { "reporting-range", "reportingRange", "date-range", "dateRange", "startDate", "endDate", "weekly-week", "monthly-month", "quarterly-quarter", "viewId", "marketplace", "country", "asin-scope" })
            if (q[key] is { Length: > 0 } v) filters[key] = v;
        var orderId = type == "order_detail" ? Segment(path, "order") : null;
        return new PageInfo
        {
            Site = "seller_central", PageType = type, Module = module, Skus = skus.Distinct().ToList(), Asins = asins.Distinct().ToList(),
            SearchTerm = search, Filters = filters, OrderIds = orderId is null ? Array.Empty<string>() : new[] { orderId },
        };
    }

    private static PageInfo AmazonRetail(string path, System.Collections.Specialized.NameValueCollection q)
    {
        var asins = AsinsIn(path).ToList();
        if (asins.Count > 0) return new PageInfo { Site = "amazon", PageType = "product", Asins = asins };
        if (path.StartsWith("/s", StringComparison.Ordinal) && q["k"] is { } k) return new PageInfo { Site = "amazon", PageType = "search", SearchTerm = k };
        if (path.StartsWith("/stores/", StringComparison.Ordinal)) return new PageInfo { Site = "amazon", PageType = "storefront" };
        if (path.Contains("/product-reviews/")) return new PageInfo { Site = "amazon", PageType = "reviews", Asins = AsinsInSegment(path, "product-reviews") };
        if (path.StartsWith("/gp/cart", StringComparison.Ordinal)) return new PageInfo { Site = "amazon", PageType = "cart" };
        return new PageInfo { Site = "amazon", PageType = "page" };
    }

    private static PageInfo Keepa(string fragment, System.Collections.Specialized.NameValueCollection q)
    {
        // Keepa routes live in the #! fragment: #!product/1-B0XXXXXXXX, #!search/1-term, #!finder, #!deals, #!viewer
        var route = fragment.TrimStart('!');
        var head = route.Split('/', 2)[0].ToLowerInvariant();
        var rest = route.Contains('/') ? route[(route.IndexOf('/') + 1)..] : "";
        var afterDomain = rest.Contains('-') ? rest[(rest.IndexOf('-') + 1)..] : rest;
        return head switch
        {
            "product" => new PageInfo { Site = "keepa", PageType = "product", Module = "Product", Asins = SplitAsins(afterDomain) },
            "search" => new PageInfo { Site = "keepa", PageType = "search", Module = "Search", SearchTerm = NullIfEmpty(afterDomain) },
            "finder" => new PageInfo { Site = "keepa", PageType = "product_finder", Module = "Product Finder" },
            "deals" => new PageInfo { Site = "keepa", PageType = "deals", Module = "Deals" },
            "viewer" => new PageInfo { Site = "keepa", PageType = "product_viewer", Module = "Product Viewer" },
            "bestsellers" => new PageInfo { Site = "keepa", PageType = "best_sellers", Module = "Best Sellers" },
            "tracking" => new PageInfo { Site = "keepa", PageType = "tracking", Module = "Tracking" },
            "category" => new PageInfo { Site = "keepa", PageType = "category_tree", Module = "Category Tree" },
            "" => new PageInfo { Site = "keepa", PageType = "home" },
            _ => new PageInfo { Site = "keepa", PageType = head, Module = head },
        };
    }

    private static PageInfo Etsy(string path, System.Collections.Specialized.NameValueCollection q)
    {
        var p = path.ToLowerInvariant();
        string? listing = Segment(path, "listing") ?? Segment(path, "listings") ?? Segment(path, "edit");
        if (listing is not null && !listing.All(char.IsDigit)) listing = null;
        var type = p switch
        {
            _ when p.Contains("/listing-editor/") || (p.Contains("/tools/listings/") && listing is not null) => "listing_editor",
            _ when p.Contains("/tools/listings") => "listings_manager",
            _ when p.StartsWith("/listing/") => "listing",
            _ when p.Contains("/orders") => "orders",
            _ when p.StartsWith("/search") => "search",
            _ when p.Contains("/stats") => "stats",
            _ when p.Contains("/marketing") || p.Contains("/advertising") => "marketing",
            _ => "page",
        };
        return new PageInfo
        {
            Site = "etsy", PageType = type,
            ListingIds = listing is null ? Array.Empty<string>() : new[] { listing },
            SearchTerm = First(q, "search_query", "q"),
        };
    }

    private static PageInfo Shopify(string host, string path, System.Collections.Specialized.NameValueCollection q)
    {
        // admin.shopify.com/store/{store}/products/{id}  or  {store}.myshopify.com/admin/products/{id}
        var p = path;
        var adminIdx = p.IndexOf("/admin/", StringComparison.OrdinalIgnoreCase);
        if (host == "admin.shopify.com")
        {
            var parts = p.Split('/', StringSplitOptions.RemoveEmptyEntries);
            p = "/" + string.Join('/', parts.Skip(parts.Length > 1 && parts[0] == "store" ? 2 : 0));
        }
        else if (adminIdx >= 0) p = p[(adminIdx + 6)..];

        var product = Segment(p, "products");
        if (product is not null && !product.All(char.IsDigit)) product = null;
        var order = Segment(p, "orders");
        if (order is not null && !order.All(char.IsDigit)) order = null;
        var type = p switch
        {
            _ when p.StartsWith("/products/import", StringComparison.OrdinalIgnoreCase) || q["import"] is not null => "product_import",
            _ when product is not null => "product_editor",
            _ when p.StartsWith("/products/new", StringComparison.OrdinalIgnoreCase) => "product_create",
            _ when p.StartsWith("/products", StringComparison.OrdinalIgnoreCase) => "products",
            _ when p.StartsWith("/content/files", StringComparison.OrdinalIgnoreCase) || p.StartsWith("/files", StringComparison.OrdinalIgnoreCase) => "files",
            _ when order is not null => "order_detail",
            _ when p.StartsWith("/orders", StringComparison.OrdinalIgnoreCase) => "orders",
            _ when p.StartsWith("/collections", StringComparison.OrdinalIgnoreCase) => "collections",
            _ when p.StartsWith("/apps", StringComparison.OrdinalIgnoreCase) => "apps",
            _ => "admin",
        };
        return new PageInfo
        {
            Site = "shopify", PageType = type,
            ProductIds = product is null ? Array.Empty<string>() : new[] { product },
            OrderIds = order is null ? Array.Empty<string>() : new[] { order },
            SearchTerm = First(q, "query", "q"),
        };
    }

    private static PageInfo GoogleDocs(string path)
    {
        var kind = path.StartsWith("/spreadsheets", StringComparison.Ordinal) ? "google_sheets"
            : path.StartsWith("/document", StringComparison.Ordinal) ? "google_docs"
            : path.StartsWith("/presentation", StringComparison.Ordinal) ? "google_slides" : "google_docs";
        return new PageInfo { Site = kind, PageType = "document", DocumentId = Segment(path, "d") };
    }

    /// <summary>Adds the item title from the page title, and ASIN/SKU mentions from visible text.</summary>
    private static PageInfo AddFromText(PageInfo info, string? pageTitle, IReadOnlyList<string> texts)
    {
        var asins = info.Asins.ToList();
        var skus = info.Skus.ToList();
        foreach (var t in texts.Where(t => !string.IsNullOrWhiteSpace(t)))
        {
            foreach (Match m in AsinInText.Matches(t)) asins.Add(m.Groups[1].Value);
            foreach (Match m in SkuInText.Matches(t)) if (!IsAsin(m.Groups[1].Value)) skus.Add(m.Groups[1].Value);
        }
        return info with
        {
            Asins = asins.Distinct().ToList(),
            Skus = skus.Distinct(StringComparer.OrdinalIgnoreCase).ToList(),
            ItemTitle = info.ItemTitle ?? ItemTitleFrom(info, pageTitle),
        };
    }

    private static string? ItemTitleFrom(PageInfo info, string? title)
    {
        if (string.IsNullOrWhiteSpace(title)) return null;
        var t = title.Trim();
        switch (info.Site)
        {
            case "amazon" when info.PageType == "product":
                // "Amazon.com: Personalized Stationery Set : Office Products"
                t = Regex.Replace(t, @"^Amazon\.[a-z.]+\s*:\s*", "", RegexOptions.IgnoreCase);
                t = Regex.Replace(t, @"\s*:\s*[^:]+$", "");
                return NullIfEmpty(t);
            case "etsy" when info.PageType is "listing":
                return NullIfEmpty(Regex.Replace(t, @"\s*-\s*Etsy(\s+\w+)?$", ""));
            case "google_sheets" or "google_docs" or "google_slides":
                return NullIfEmpty(Regex.Replace(t, @"\s*-\s*Google (Sheets|Docs|Slides)$", ""));
            default:
                return null;
        }
    }

    public static bool IsAsin(string s) => s.Length == 10 && (AsinAnywhere.IsMatch(s) || s.All(char.IsDigit));

    private static bool IsHost(string host, string prefix) => host.StartsWith(prefix, StringComparison.Ordinal) || host.Contains("." + prefix, StringComparison.Ordinal);

    private static bool IsAmazonRetail(string host) =>
        Regex.IsMatch(host, @"^(www\.|smile\.)?amazon\.(com|ca|co\.uk|de|fr|it|es|com\.mx|com\.au|co\.jp|in|nl|se|pl|ae|sa|sg|com\.br|com\.tr|com\.be)$");

    private static IEnumerable<string> AsinsIn(string path)
    {
        foreach (Match m in AsinInPath.Matches(path)) yield return m.Groups[1].Value.ToUpperInvariant();
        foreach (Match m in AsinAnywhere.Matches(path)) yield return m.Groups[1].Value;
    }

    private static List<string> AsinsInSegment(string path, string name) => Segment(path, name) is { } s && IsAsin(s) ? new() { s } : new();

    private static List<string> SplitAsins(string s) =>
        s.Split(new[] { ',', ' ', '/' }, StringSplitOptions.RemoveEmptyEntries).Select(x => x.Trim().ToUpperInvariant()).Where(IsAsin).Distinct().ToList();

    /// <summary>The path segment after /name/.</summary>
    private static string? Segment(string path, string name)
    {
        var parts = path.Split('/', StringSplitOptions.RemoveEmptyEntries);
        for (var i = 0; i < parts.Length - 1; i++)
            if (parts[i].Equals(name, StringComparison.OrdinalIgnoreCase)) return Uri.UnescapeDataString(parts[i + 1]);
        return null;
    }

    private static IEnumerable<string> Values(System.Collections.Specialized.NameValueCollection q, params string[] keys) =>
        keys.SelectMany(k => q.GetValues(k) ?? Array.Empty<string>()).SelectMany(v => v.Split(',')).Select(v => v.Trim()).Where(v => v.Length > 0);

    private static string? First(System.Collections.Specialized.NameValueCollection q, params string[] keys) =>
        keys.Select(k => q[k]).FirstOrDefault(v => !string.IsNullOrWhiteSpace(v))?.Trim();

    private static string? NullIfEmpty(string? s) => string.IsNullOrWhiteSpace(s) ? null : s.Trim();
}
