using MppWatcher.Core.Activity;
using MppWatcher.Core.Browser;
using MppWatcher.Core.Events;
using MppWatcher.Core.Presentation;

namespace MppWatcher.Core.Tests;

public class BrowserContextTests
{
    [Theory]
    [InlineData("Keepa - Amazon Price Tracker - Google Chrome", "Keepa - Amazon Price Tracker")]
    [InlineData("Edit listing - Etsy - Personal - Microsoft​ Edge", "Edit listing - Etsy")]
    [InlineData("Search Query Performance | Amazon Seller Central - Work - Microsoft Edge", "Search Query Performance | Amazon Seller Central")]
    [InlineData("Google Sheets — Mozilla Firefox", "Google Sheets")]
    [InlineData("Untitled - Notepad", "Untitled - Notepad")]
    public void Browser_suffix_is_removed(string window, string page) => Assert.Equal(page, BrowserTitle.PageTitle(window));

    private static BrowserPage KeepaPage(string windowTitle) => new(0x40A2E, 8812, "https://keepa.com/#!product/1-B0CXYZ1234", "keepa.com", "Keepa",
        windowTitle, SiteProfiles.Analyze(new Uri("https://keepa.com/#!product/1-B0CXYZ1234"), "Keepa"), T.Start);

    [Fact]
    public void Events_from_the_same_page_get_url_domain_and_page_facts()
    {
        var ctx = new ActivityContext();
        ctx.SetPage(KeepaPage("Keepa - Google Chrome"));
        var field = new WatchEvent { EventType = EventTypes.UiFieldValue, ProcessId = 8812, WindowTitle = "Keepa - Google Chrome" };
        ctx.Enrich(field);
        Assert.Equal("keepa.com", field.Domain);
        Assert.Equal("https://keepa.com/#!product/1-B0CXYZ1234", field.Url);
        Assert.Equal("Keepa", field.PageTitle);
        Assert.Contains("B0CXYZ1234", field.Metadata["page"]!.ToJsonString());
    }

    [Fact]
    public void Old_page_is_not_attached_when_the_title_changed()
    {
        var ctx = new ActivityContext();
        ctx.SetPage(KeepaPage("Keepa - Google Chrome"));
        var e = new WatchEvent { EventType = EventTypes.UiAction, ProcessId = 8812, WindowTitle = "Etsy - Google Chrome" };
        ctx.Enrich(e);
        Assert.Null(e.Domain);
        Assert.Null(e.Metadata["page"]);
    }

    [Fact]
    public void Events_get_the_open_session_id()
    {
        var ctx = new ActivityContext();
        ctx.Observe(new WatchEvent { EventType = EventTypes.AppSessionStart, SessionId = "s1", ProcessId = 8812 }.Set("window_handle", "0x40A2E"));
        var click = new WatchEvent { EventType = EventTypes.UiAction, ProcessId = 8812 };
        ctx.Enrich(click);
        Assert.Equal("s1", click.SessionId);

        ctx.Observe(new WatchEvent { EventType = EventTypes.AppSessionEnd, SessionId = "s1" });
        var later = new WatchEvent { EventType = EventTypes.UiAction, ProcessId = 8812 };
        ctx.Enrich(later);
        Assert.Null(later.SessionId);
    }

    [Fact]
    public void Blocked_domain_found_by_enrichment_is_redacted()
    {
        var cfg = new MppWatcher.Core.Configuration.WatcherConfig();
        var ctx = new ActivityContext();
        var bank = new BrowserPage(1, 5, "https://www.mybank.com/accounts", "mybank.com", "Accounts", "Accounts - Google Chrome",
            SiteProfiles.Analyze(new Uri("https://www.mybank.com/accounts"), "Accounts"), T.Start);
        ctx.SetPage(bank);
        var session = new WatchEvent { EventType = EventTypes.AppSessionStart, ProcessId = 5, ProcessName = "chrome", WindowTitle = "Accounts - Google Chrome" };
        ctx.Enrich(session);
        var stored = new MppWatcher.Core.Privacy.PrivacyFilter(() => cfg).Apply(session)!;
        Assert.Equal("[excluded]", stored.WindowTitle);
        Assert.Null(stored.Url);
        Assert.Equal("blocked_domain", stored.Metadata["excluded_reason"]!.GetValue<string>());
    }

    [Fact]
    public void Browser_page_summary_for_the_viewer()
    {
        var info = SiteProfiles.Analyze(new Uri("https://sellercentral.amazon.com/abis/listing/edit?sku=MA023&asin=B0CXYZ1234"), "Edit Product Info");
        var e = new WatchEvent { EventType = EventTypes.BrowserPage, Application = "Microsoft Edge", Domain = "sellercentral.amazon.com", PageTitle = "Edit Product Info" };
        foreach (var (k, v) in ActivityContext.PageJson(info, compact: false)) e.Metadata[k] = v?.DeepClone();
        Assert.Equal("Microsoft Edge → sellercentral.amazon.com: seller central Edit Listing · ASIN B0CXYZ1234 · SKU MA023 — \"Edit Product Info\"",
            EventSummaryFormatter.Summarize(e));
    }
}

public class BrowserTitleExtraTests
{
    [Theory]
    [InlineData("Keepa - Amazon Price Tracker - Microsoft​ Edge", "Keepa - Amazon Price Tracker")]
    [InlineData("Orders - Profile 1 - Microsoft Edge", "Orders")]
    public void Edge_profiles_versus_page_title_parts(string window, string page) => Assert.Equal(page, BrowserTitle.PageTitle(window));

    [Theory]
    [InlineData("Untitled - Profile 1 - Microsoft\u200B Edge", true)]   // seen on real Edge while a page loads
    [InlineData("New Tab - Google Chrome", true)]
    [InlineData("Keepa - Google Chrome", false)]
    public void Loading_titles_are_recognised(string window, bool placeholder) =>
        Assert.Equal(placeholder, BrowserTitle.IsPlaceholder(BrowserTitle.PageTitle(window)));
}
