using System.Diagnostics;
using MppWatcher.Core.Events;
using MppWatcher.Core.Storage;
using Xunit.Abstractions;

namespace MppWatcher.Windows.Tests;

/// <summary>
/// Phase 3 end to end: the real MPPWatcher.exe watches Microsoft Edge while it visits look-alike
/// pages served under the real business site addresses (amazon.com, Seller Central, Keepa, Etsy, Shopify).
/// </summary>
public sealed class BrowserEndToEndTests : IDisposable
{
    private readonly ITestOutputHelper _out;
    private readonly string _dir = Path.Combine(Path.GetTempPath(), "mppw-browser-" + Guid.NewGuid().ToString("N"));
    private readonly List<Process> _started = new();
    private readonly FakeWebServer _server;
    private string? _edge;

    public BrowserEndToEndTests(ITestOutputHelper output)
    {
        _out = output;
        Directory.CreateDirectory(_dir);
        File.WriteAllText(ConfigPath, $$"""
            {
              "employee_id": "EMP-TEST",
              "log_folder": {{System.Text.Json.JsonSerializer.Serialize(Path.Combine(_dir, "logs"))}},
              "collectors": { "ui_automation": { "value_settle_seconds": 3 } }
            }
            """);
        _server = new FakeWebServer(Page);
    }

    private string ConfigPath => Path.Combine(_dir, "config.json");
    private string DataDir => Path.Combine(_dir, "data");

    /// <summary>Simple look-alike pages. Structure (labels, headings, buttons) mirrors the real sites.</summary>
    private static string Page(string host, string path)
    {
        static string Html(string title, string body) =>
            $"<!doctype html><html><head><meta charset='utf-8'><title>{title}</title></head><body style='font-family:Segoe UI;padding:20px'>{body}</body></html>";
        return host switch
        {
            "www.amazon.com" => Html("Amazon.com: Personalized Stationery Set for Women : Office Products",
                "<h1 id='title'><span id='productTitle'>Personalized Stationery Set for Women</span></h1><p>Visit the MPP Store</p><h2>About this item</h2><button>Add to Cart</button>"),
            "sellercentral.amazon.com" when path.StartsWith("/abis/listing/edit") => Html("Edit Product Info | Amazon Seller Central",
                "<h1>Edit Product Info</h1><h2>Product details</h2><p>Seller SKU: MA023</p>" +
                "<p><label for='t'>Item Name</label><br><input id='t' style='width:400px;font-size:18px'></p>" +
                "<p><button id='save' style='font-size:18px'>Save and finish</button></p>"),
            "sellercentral.amazon.com" => Html("Search Query Performance | Amazon Seller Central",
                "<h1>Search Query Performance</h1><h2>ASIN View</h2><p>Search Query</p>"),
            "keepa.com" => Html("Keepa - Amazon Price Tracker", "<h1>Keepa</h1><h2>Product</h2>"),
            "www.etsy.com" => Html("Edit listing - Etsy", "<h1>Edit listing</h1><h2>Personalization</h2><h2>Photos</h2><button>Publish</button>"),
            "admin.shopify.com" => Html("Personalized Stationery Set · Products · MPP Shop · Shopify", "<h1>Personalized Stationery Set</h1><h2>Media</h2><h2>Inventory</h2><button>Save</button>"),
            _ => "",
        };
    }

    private Process Run(string exe, params string[] args)
    {
        var psi = new ProcessStartInfo(exe) { UseShellExecute = false };
        foreach (var a in args) psi.ArgumentList.Add(a);
        var p = Process.Start(psi)!;
        _started.Add(p);
        return p;
    }

    private void OpenInEdge(string url)
    {
        _edge ??= new[]
        {
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86), @"Microsoft\Edge\Application\msedge.exe"),
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), @"Microsoft\Edge\Application\msedge.exe"),
        }.First(File.Exists);
        Run(_edge, $"--user-data-dir={Path.Combine(_dir, "edge")}", "--no-first-run", "--no-default-browser-check", "--disable-sync",
            "--ignore-certificate-errors", "--disable-quic", $"--host-resolver-rules=MAP * 127.0.0.1:{_server.Port}, EXCLUDE localhost",
            "--start-maximized", url);
    }

    private List<WatchEvent> Events()
    {
        var db = Path.Combine(DataDir, "events.db");
        if (!File.Exists(db)) return new();
        try
        {
            using var store = new SqliteEventStore(db, "", readOnly: true);
            return store.ReadAfter(0, 100_000).Select(r => r.Event).ToList();
        }
        catch (Microsoft.Data.Sqlite.SqliteException) { return new(); }
    }

    private WatchEvent WaitForPage(string domain, int seconds = 25)
    {
        WatchEvent? found = null;
        Desktop.WaitUntil(() => (found = Events().LastOrDefault(e => e.EventType == EventTypes.BrowserPage && e.Domain == domain)) is not null,
            TimeSpan.FromSeconds(seconds));
        Assert.True(found is not null, $"no browser_page for {domain}. Server saw: {string.Join(", ", _server.Requests.TakeLast(10))}");
        _out.WriteLine($"browser_page {domain}: url={found!.Url} title={found.PageTitle} {found.Metadata.ToJsonString()}");
        return found;
    }

    private static string? M(WatchEvent e, string k) => e.Metadata[k]?.ToString();

    public void Dispose()
    {
        try { Run(AppEndToEndTestsExe.Path, "--stop").WaitForExit(20_000); } catch { }
        foreach (var p in _started) { try { if (!p.HasExited) p.Kill(); } catch { } }
        foreach (var p in Process.GetProcessesByName("msedge")) { try { p.Kill(); } catch { } }
        _server.Dispose();
        foreach (var e in Events()) _out.WriteLine($"  {e.EventType} [{e.ProcessName}] {e.Domain} \"{e.WindowTitle}\" {e.Metadata.ToJsonString()}");
        try { Directory.Delete(_dir, true); } catch { }
    }

    [Fact]
    public void Business_pages_are_recognised_from_the_address_bar()
    {
        Run(AppEndToEndTestsExe.Path, "--config", ConfigPath, "--data", DataDir);
        Assert.True(Desktop.WaitUntil(() => Events().Count(e => e.EventType == EventTypes.CollectorStatus) >= 4, TimeSpan.FromSeconds(20)), "watcher did not start");

        OpenInEdge("https://www.amazon.com/Personalized-Stationery-Set/dp/B0CXYZ1234/ref=sr_1_1?keywords=stationery&session-id=123-456");
        var amazon = WaitForPage("amazon.com", 40);
        Assert.Equal("amazon", M(amazon, "site"));
        Assert.Equal("product", M(amazon, "page_type"));
        Assert.Contains("B0CXYZ1234", M(amazon, "asins"));
        Assert.Equal("Personalized Stationery Set for Women", M(amazon, "item_title"));
        Assert.DoesNotContain("session-id", amazon.Url);
        Assert.Contains("Personalized Stationery Set for Women", M(amazon, "headings"));

        OpenInEdge("https://sellercentral.amazon.com/brand-analytics/dashboard/query-performance?view-id=query-performance-asin-view&asin=B0CXYZ1234&reporting-range=weekly");
        var sqp = WaitForPage("sellercentral.amazon.com");
        Assert.Equal("search_query_performance", M(sqp, "page_type"));
        Assert.Equal("Search Query Performance", M(sqp, "module"));
        Assert.Contains("weekly", M(sqp, "filters"));

        OpenInEdge("https://sellercentral.amazon.com/abis/listing/edit?sku=MA023&asin=B0CXYZ1234");
        Assert.True(Desktop.WaitUntil(() => Events().Any(e => e.EventType == EventTypes.BrowserPage && M(e, "page_type") == "listing_editor"), TimeSpan.FromSeconds(25)),
            "listing editor page not recognised");
        var editor = Events().Last(e => e.EventType == EventTypes.BrowserPage && M(e, "page_type") == "listing_editor");
        Assert.Contains("MA023", M(editor, "skus"));

        // Type a new item name and save: the field and the click must carry the page facts.
        var uia = new MppWatcher.Windows.Ui.UiaClient();
        global::Interop.UIAutomationClient.IUIAutomationElement? Find(string name)
        {
            global::Interop.UIAutomationClient.IUIAutomationElement? el = null;
            Desktop.WaitUntil(() =>
            {
                var hwnd = MppWatcher.Windows.Interop.NativeMethods.GetForegroundWindow();
                el = uia.Automation.ElementFromHandle(hwnd)?.FindFirst(global::Interop.UIAutomationClient.TreeScope.TreeScope_Descendants,
                    uia.Automation.CreatePropertyCondition(30005, name));
                return el is not null;
            }, TimeSpan.FromSeconds(20));
            return el;
        }
        Point Center(global::Interop.UIAutomationClient.IUIAutomationElement el)
        {
            var r = el.CurrentBoundingRectangle;
            return new Point((r.left + r.right) / 2, (r.top + r.bottom) / 2);
        }
        Desktop.Click(Center(Find("Item Name") ?? throw new Exception("Item Name field not exposed")));
        Desktop.TypeText("Personalized Stationery Set - Floral");
        Desktop.Click(Center(Find("Save and finish") ?? throw new Exception("Save button not exposed")));
        Assert.True(Desktop.WaitUntil(() => Events().Any(e => e.EventType == EventTypes.UiAction && M(e, "control_name") == "Save and finish"), TimeSpan.FromSeconds(15)),
            "Save and finish click not recorded");
        UiAutomationTests.SaveScreenshot("seller-central-listing-editor.png");
        var field = Events().Last(e => e.EventType == EventTypes.UiFieldValue && M(e, "value") == "Personalized Stationery Set - Floral");
        Assert.Equal("sellercentral.amazon.com", field.Domain);
        Assert.Contains("MA023", field.Metadata["page"]?.ToJsonString());
        var save = Events().Last(e => e.EventType == EventTypes.UiAction && M(e, "control_name") == "Save and finish");
        Assert.Equal("sellercentral.amazon.com", save.Domain);
        Assert.Equal("true", M(save, "is_key_action"));

        OpenInEdge("https://keepa.com/#!product/1-B0CXYZ1234");
        var keepa = WaitForPage("keepa.com");
        Assert.Equal("product", M(keepa, "page_type"));
        Assert.Contains("B0CXYZ1234", M(keepa, "asins"));

        OpenInEdge("https://www.etsy.com/your/shops/me/listing-editor/edit/1234567890");
        var etsy = WaitForPage("etsy.com");
        Assert.Equal("listing_editor", M(etsy, "page_type"));
        Assert.Contains("1234567890", M(etsy, "listing_ids"));
        Assert.Contains("Personalization", M(etsy, "headings"));

        OpenInEdge("https://admin.shopify.com/store/mpp-shop/products/8123456789012");
        var shopify = WaitForPage("admin.shopify.com");
        Assert.Equal("product_editor", M(shopify, "page_type"));
        Assert.Contains("8123456789012", M(shopify, "product_ids"));

        // Foreground sessions in the browser carry the page too.
        Assert.Contains(Events(), e => e.EventType == EventTypes.AppSessionStart && e.Domain == "keepa.com" || e.EventType == EventTypes.AppSessionEnd && e.Domain == "keepa.com");

        var viewer = Run(AppEndToEndTestsExe.Path, "--viewer", "--config", ConfigPath, "--data", DataDir);
        Desktop.WaitUntil(() => { viewer.Refresh(); return viewer.MainWindowTitle.Contains("Live Event Viewer"); }, TimeSpan.FromSeconds(20));
        Desktop.BringToFront(viewer.MainWindowHandle);
        Thread.Sleep(2500);
        UiAutomationTests.SaveScreenshot("live-viewer-browser.png");
        viewer.CloseMainWindow();
    }
}
