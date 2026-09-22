using MppWatcher.Core.Activity;
using MppWatcher.Core.Diagnostics;
using MppWatcher.Core.Events;

namespace MppWatcher.Core.Tests;

public sealed class FakeClock : IClock
{
    public FakeClock(DateTimeOffset start) => Now = start;
    public DateTimeOffset Now { get; set; }
    public DateTimeOffset Advance(TimeSpan by) => Now += by;
}

public static class T
{
    public static readonly DateTimeOffset Start = new(2026, 9, 22, 9, 0, 0, TimeSpan.FromHours(-4));

    public static WindowSnapshot Chrome(string title, long handle = 100) =>
        new(handle, 10, "chrome", "Google Chrome", @"C:\Program Files\Google\Chrome\Application\chrome.exe", title, "Chrome_WidgetWin_1", "DISPLAY1");

    public static WindowSnapshot Photoshop(string title = "Adobe Photoshop 2025") =>
        new(200, 20, "Photoshop", "Adobe Photoshop 2025", null, title, "Photoshop", "DISPLAY2");

    public static WindowSnapshot Excel(string title = "ShopifyInventory.xlsx - Excel") =>
        new(300, 30, "EXCEL", "Microsoft Excel", null, title, "XLMAIN", "DISPLAY1");

    public static double Num(WatchEvent e, string key) => e.Metadata[key]!.GetValue<double>();
    public static string? Str(WatchEvent e, string key) => e.Metadata[key]?.GetValue<string>();
}
