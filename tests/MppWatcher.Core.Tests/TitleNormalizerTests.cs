using MppWatcher.Core.Activity;

namespace MppWatcher.Core.Tests;

public class TitleNormalizerTests
{
    [Theory]
    [InlineData("(3) Inbox - Gmail", "(12) Inbox - Gmail")]
    [InlineData("● app.cs - VS Code", "app.cs - VS Code")]
    [InlineData("MA023-main.psd @ 66.7% (Layer 1, RGB/8) *", "MA023-main.psd @ 100% (Layer 2, RGB/8)")]
    [InlineData("Book1.xlsx - Saved - Excel", "Book1.xlsx - Excel")]
    public void Cosmetic_differences_normalize_equal(string a, string b) =>
        Assert.Equal(TitleNormalizer.Normalize(a), TitleNormalizer.Normalize(b));

    [Theory]
    [InlineData("MA023-main.psd @ 50%", "MA024-main.psd @ 50%")]
    [InlineData("Amazon.com: Stationery", "Keepa - Amazon Price Tracker")]
    public void Real_differences_stay_different(string a, string b) =>
        Assert.NotEqual(TitleNormalizer.Normalize(a), TitleNormalizer.Normalize(b));
}
