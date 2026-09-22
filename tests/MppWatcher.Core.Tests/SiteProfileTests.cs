using MppWatcher.Core.Browser;

namespace MppWatcher.Core.Tests;

public class SiteProfileTests
{
    private static PageInfo A(string url, string? title = null, params string[] texts) => SiteProfiles.Analyze(new Uri(url), title, texts);

    [Fact]
    public void Amazon_product_page_gives_asin_and_product_title()
    {
        var p = A("https://www.amazon.com/Personalized-Stationery-Set-Women/dp/B0CXYZ1234/ref=sr_1_3?keywords=stationery",
            "Amazon.com: Personalized Stationery Set for Women : Office Products");
        Assert.Equal("amazon", p.Site);
        Assert.Equal("product", p.PageType);
        Assert.Equal(new[] { "B0CXYZ1234" }, p.Asins);
        Assert.Equal("Personalized Stationery Set for Women", p.ItemTitle);
    }

    [Theory]
    [InlineData("https://www.amazon.com/gp/product/B0CXYZ1234")]
    [InlineData("https://www.amazon.co.uk/dp/B0CXYZ1234?th=1")]
    public void Other_amazon_product_url_forms(string url) => Assert.Equal(new[] { "B0CXYZ1234" }, A(url).Asins);

    [Fact]
    public void Amazon_search_gives_search_term() =>
        Assert.Equal("personalized stationery", A("https://www.amazon.com/s?k=personalized+stationery&ref=nb_sb_noss").SearchTerm);

    [Fact]
    public void Seller_central_search_query_performance_with_filters()
    {
        var p = A("https://sellercentral.amazon.com/brand-analytics/dashboard/query-performance?view-id=query-performance-asin-view&asin=B0CXYZ1234&reporting-range=weekly&weekly-week=2026-09-13&country=us");
        Assert.Equal("seller_central", p.Site);
        Assert.Equal("search_query_performance", p.PageType);
        Assert.Equal("Search Query Performance", p.Module);
        Assert.Equal(new[] { "B0CXYZ1234" }, p.Asins);
        Assert.Equal("weekly", p.Filters["reporting-range"]);
        Assert.Equal("2026-09-13", p.Filters["weekly-week"]);
    }

    [Fact]
    public void Seller_central_listing_editor_gives_sku_and_asin()
    {
        var p = A("https://sellercentral.amazon.com/abis/listing/edit?marketplaceID=ATVPDKIKX0DER&ref=xx_myiedit_cont_myifba&sku=MA023&asin=B0CXYZ1234&productType=STATIONERY");
        Assert.Equal("listing_editor", p.PageType);
        Assert.Equal(new[] { "MA023" }, p.Skus);
        Assert.Equal(new[] { "B0CXYZ1234" }, p.Asins);
    }

    [Fact]
    public void Seller_central_inventory_search_and_sku_central()
    {
        var inv = A("https://sellercentral.amazon.com/myinventory/inventory?fulfilledBy=all&page=1&pageSize=25&searchField=all&searchTerm=PS142");
        Assert.Equal("inventory", inv.PageType);
        Assert.Equal("Manage All Inventory", inv.Module);
        Assert.Equal("PS142", inv.SearchTerm);
        Assert.Equal(new[] { "MA023" }, A("https://sellercentral.amazon.com/skucentral?mSku=MA023").Skus);
    }

    [Fact]
    public void Seller_central_order_and_customization_pages()
    {
        var o = A("https://sellercentral.amazon.com/orders-v3/order/112-1234567-1234567");
        Assert.Equal("order_detail", o.PageType);
        Assert.Equal(new[] { "112-1234567-1234567" }, o.OrderIds);
        Assert.Equal("customization", A("https://sellercentral.amazon.com/customization/edit?sku=PS142").PageType);
    }

    [Fact]
    public void Keepa_hash_routes()
    {
        var product = A("https://keepa.com/#!product/1-B0CXYZ1234");
        Assert.Equal("keepa", product.Site);
        Assert.Equal("product", product.PageType);
        Assert.Equal(new[] { "B0CXYZ1234" }, product.Asins);
        Assert.Equal("personalized stationery", A("https://keepa.com/#!search/1-personalized%20stationery").SearchTerm);
        Assert.Equal("product_finder", A("https://keepa.com/#!finder").PageType);
        Assert.Equal(2, A("https://keepa.com/#!product/1-B0CXYZ1234,B0ABCDE123").Asins.Count);
    }

    [Fact]
    public void Etsy_listing_editor_and_public_listing()
    {
        var ed = A("https://www.etsy.com/your/shops/me/listing-editor/edit/1234567890");
        Assert.Equal("etsy", ed.Site);
        Assert.Equal("listing_editor", ed.PageType);
        Assert.Equal(new[] { "1234567890" }, ed.ListingIds);

        var tools = A("https://www.etsy.com/your/shops/me/tools/listings/1234567890");
        Assert.Equal("listing_editor", tools.PageType);

        var pub = A("https://www.etsy.com/listing/1234567890/personalized-stationery-set", "Personalized Stationery Set - Etsy");
        Assert.Equal("listing", pub.PageType);
        Assert.Equal(new[] { "1234567890" }, pub.ListingIds);
        Assert.Equal("Personalized Stationery Set", pub.ItemTitle);

        Assert.Equal("MA023", A("https://www.etsy.com/your/shops/me/tools/listings?search_query=MA023").SearchTerm);
    }

    [Fact]
    public void Shopify_admin_product_editor_and_import()
    {
        var p = A("https://admin.shopify.com/store/mpp-shop/products/8123456789012");
        Assert.Equal("shopify", p.Site);
        Assert.Equal("product_editor", p.PageType);
        Assert.Equal(new[] { "8123456789012" }, p.ProductIds);
        Assert.Equal("product_editor", A("https://mpp-shop.myshopify.com/admin/products/8123456789012").PageType);
        Assert.Equal("products", A("https://admin.shopify.com/store/mpp-shop/products?query=MA023").PageType);
        Assert.Equal("MA023", A("https://admin.shopify.com/store/mpp-shop/products?query=MA023").SearchTerm);
        Assert.Equal("product_import", A("https://admin.shopify.com/store/mpp-shop/products/import").PageType);
    }

    [Fact]
    public void Google_sheets_document_and_title()
    {
        var p = A("https://docs.google.com/spreadsheets/d/1AbCdEf/edit#gid=0", "ShopifyInventory - Google Sheets");
        Assert.Equal("google_sheets", p.Site);
        Assert.Equal("1AbCdEf", p.DocumentId);
        Assert.Equal("ShopifyInventory", p.ItemTitle);
    }

    [Fact]
    public void Visible_text_mentions_add_skus_and_asins()
    {
        var p = A("https://sellercentral.amazon.com/inventory", null, "Seller SKU: MA023", "ASIN: B0CXYZ1234", "SKU PS142");
        Assert.Contains("MA023", p.Skus);
        Assert.Contains("PS142", p.Skus);
        Assert.Contains("B0CXYZ1234", p.Asins);
    }

    [Fact]
    public void Unknown_sites_are_other()
    {
        var p = A("https://www.example.org/blog/post");
        Assert.Equal("other", p.Site);
        Assert.Empty(p.Asins);
    }
}
