using MppWatcher.Core.Files;

namespace MppWatcher.Core.Tests;

public class FileActivityTests
{
    private readonly FileActivityAggregator _a = new(() => TimeSpan.FromSeconds(2));
    private DateTimeOffset _t = T.Start;
    private const string Dir = @"C:\Users\jane\Documents\Work";

    private void Raw(RawFileChange c, string name, string? old = null)
    {
        _t = _t.AddMilliseconds(100);
        _a.Add(new RawFileEvent(c, Path.Combine(Dir, name), old is null ? null : Path.Combine(Dir, old), _t));
    }

    private IReadOnlyList<FileActivity> Done() => _a.Flush(_t.AddSeconds(5));

    [Fact]
    public void Many_change_notices_are_one_save()
    {
        for (var i = 0; i < 6; i++) Raw(RawFileChange.Changed, "MA023-main.psd");
        var r = Assert.Single(Done());
        Assert.Equal(FileActivityKind.Saved, r.Kind);
        Assert.EndsWith("MA023-main.psd", r.Path);
    }

    [Fact]
    public void Excel_safe_save_is_one_save()
    {
        // Excel: write temp "3A1B2C4D", rename original to temp name, rename temp to original, delete old
        Raw(RawFileChange.Created, "3A1B2C4D");
        Raw(RawFileChange.Changed, "3A1B2C4D");
        Raw(RawFileChange.Renamed, "5E6F7A8B.tmp", "ShopifyInventory.xlsx");
        Raw(RawFileChange.Renamed, "ShopifyInventory.xlsx", "3A1B2C4D");
        Raw(RawFileChange.Deleted, "5E6F7A8B.tmp");
        Raw(RawFileChange.Created, "~$ShopifyInventory.xlsx");
        var r = Assert.Single(Done());
        Assert.Equal(FileActivityKind.Saved, r.Kind);
        Assert.EndsWith("ShopifyInventory.xlsx", r.Path);
    }

    [Fact]
    public void Browser_download_is_one_download()
    {
        Raw(RawFileChange.Created, "Unconfirmed 123.crdownload");
        Raw(RawFileChange.Changed, "Unconfirmed 123.crdownload");
        Raw(RawFileChange.Renamed, "AmazonOrders.csv.crdownload", "Unconfirmed 123.crdownload");
        Raw(RawFileChange.Renamed, "AmazonOrders.csv", "AmazonOrders.csv.crdownload");
        var r = Assert.Single(Done());
        Assert.Equal(FileActivityKind.Downloaded, r.Kind);
        Assert.EndsWith("AmazonOrders.csv", r.Path);
    }

    [Fact]
    public void Create_then_save_is_one_create()
    {
        Raw(RawFileChange.Created, "PS142.indd");
        Raw(RawFileChange.Changed, "PS142.indd");
        Raw(RawFileChange.Changed, "PS142.indd");
        Assert.Equal(FileActivityKind.Created, Assert.Single(Done()).Kind);
    }

    [Fact]
    public void Rename_and_delete()
    {
        Raw(RawFileChange.Renamed, "MA023-final.psd", "MA023-main.psd");
        Raw(RawFileChange.Deleted, "old-notes.txt");
        var r = Done();
        Assert.Contains(r, x => x.Kind == FileActivityKind.Renamed && x.Path.EndsWith("MA023-final.psd") && x.OldPath!.EndsWith("MA023-main.psd"));
        Assert.Contains(r, x => x.Kind == FileActivityKind.Deleted && x.Path.EndsWith("old-notes.txt"));
    }

    [Fact]
    public void Move_between_folders_is_one_move()
    {
        _t = _t.AddMilliseconds(100);
        _a.Add(new RawFileEvent(RawFileChange.Deleted, @"C:\Users\jane\Desktop\MA023-main.psd", null, _t));
        _a.Add(new RawFileEvent(RawFileChange.Created, @"C:\Users\jane\Documents\Done\MA023-main.psd", null, _t));
        var r = Assert.Single(Done());
        Assert.Equal(FileActivityKind.Moved, r.Kind);
        Assert.Equal(@"C:\Users\jane\Desktop\MA023-main.psd", r.OldPath);
    }

    [Fact]
    public void Temp_and_lock_files_are_ignored()
    {
        Raw(RawFileChange.Created, "~$Book1.xlsx");
        Raw(RawFileChange.Created, "~WRL0001.tmp");
        Raw(RawFileChange.Created, ".~lock.orders.csv#");
        Raw(RawFileChange.Changed, "desktop.ini");
        Assert.Empty(Done());
    }

    [Fact]
    public void Nothing_is_reported_before_the_quiet_time()
    {
        Raw(RawFileChange.Changed, "MA023-main.psd");
        Assert.Empty(_a.Flush(_t.AddMilliseconds(500)));
        Assert.Single(_a.Flush(_t.AddSeconds(3)));
    }

    [Fact]
    public void Created_and_deleted_quickly_is_noise()
    {
        Raw(RawFileChange.Created, "scratch.txt");
        Raw(RawFileChange.Deleted, "scratch.txt");
        Assert.Empty(Done());
    }
}
