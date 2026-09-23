using MppWatcher.Core.Files;

namespace MppWatcher.Core.Tests;

public class DocumentTitleTests
{
    [Theory]
    [InlineData("Photoshop", "MA023-main.psd @ 66.7% (Layer 1, RGB/8) *", "MA023-main.psd", true)]
    [InlineData("Photoshop", "MA023-main.psd @ 100% (RGB/8)", "MA023-main.psd", false)]
    [InlineData("Photoshop", "MA024-alt.jpg @ 50% (RGB/8#) - Adobe Photoshop 2025", "MA024-alt.jpg", false)]
    [InlineData("InDesign", "PS142.indd @ 75%", "PS142.indd", false)]
    [InlineData("InDesign", "*PS142.indd @ 75% - Adobe InDesign 2025", "PS142.indd", false)]
    [InlineData("EXCEL", "ShopifyInventory.xlsx - Excel", "ShopifyInventory.xlsx", false)]
    [InlineData("EXCEL", "ShopifyInventory.xlsx - Saved - Excel", "ShopifyInventory.xlsx", false)]
    [InlineData("EXCEL", "AmazonOrders.csv - Read-Only - Excel", "AmazonOrders.csv", false)]
    [InlineData("WINWORD", "Customization notes.docx - Word", "Customization notes.docx", false)]
    [InlineData("notepad", "*AmazonOrders.json - Notepad", "AmazonOrders.json", true)]
    [InlineData("Acrobat", "PS142-proof.pdf - Adobe Acrobat Pro", "PS142-proof.pdf", false)]
    [InlineData("Code", "● updater.user.js - mpp-scripts - Visual Studio Code", "updater.user.js", true)]
    public void Document_is_read_from_window_titles(string process, string title, string doc, bool unsaved)
    {
        var d = DocumentTitleParser.Parse(process, title)!;
        Assert.Equal(doc, d.DocumentName);
        Assert.Equal(unsaved, d.Unsaved);
    }

    [Theory]
    [InlineData("Photoshop", "Adobe Photoshop 2025")]
    [InlineData("chrome", "Keepa - Google Chrome")]
    [InlineData("EXCEL", "Excel")]
    public void No_document_when_the_title_has_none(string process, string title) => Assert.Null(DocumentTitleParser.Parse(process, title));

    [Theory]
    [InlineData("MA023-main.psd", new[] { "MA023" })]
    [InlineData("PS142_proof_v2.indd", new[] { "PS142" })]
    [InlineData("ShopifyInventory.xlsx", new string[0])]
    [InlineData("B0CXYZ1234 listing.png", new string[0])]  // ASINs are not SKUs
    [InlineData("MA001 MA002 set.psd", new[] { "MA001", "MA002" })]
    public void Skus_are_found_in_names(string name, string[] expected) => Assert.Equal(expected, SkuFinder.Find(name));

    [Fact]
    public void Custom_sku_pattern_from_config()
    {
        Assert.Equal(new[] { "MPP-7781" }, SkuFinder.Find("label MPP-7781.pdf", new[] { @"MPP-\d{4}" }));
        Assert.Empty(SkuFinder.Find("x", new[] { "([" })); // broken pattern is ignored, not a crash
    }
}
