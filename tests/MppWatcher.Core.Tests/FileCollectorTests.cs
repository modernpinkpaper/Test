using MppWatcher.Core.Activity;
using MppWatcher.Core.Browser;
using MppWatcher.Core.Collectors;
using MppWatcher.Core.Configuration;
using MppWatcher.Core.Diagnostics;
using MppWatcher.Core.Events;
using MppWatcher.Core.Files;
using MppWatcher.Core.Privacy;

namespace MppWatcher.Core.Tests;

/// <summary>Uses real files in a temp folder (the OS change notifications work on any OS).</summary>
public sealed class FileCollectorTests : IDisposable
{
    private readonly TempDir _dir = new();
    private readonly ListSink _sink = new();
    private readonly ActivityContext _activity = new();
    private readonly FileActivityCollector _collector;
    private string Work => Path.Combine(_dir.Path, "Work");
    private string Downloads => Path.Combine(_dir.Path, "Downloads");

    private sealed class ListSink : IEventSink
    {
        private readonly List<WatchEvent> _e = new();
        public void Emit(WatchEvent e) { lock (_e) _e.Add(e); }
        public List<WatchEvent> All { get { lock (_e) return _e.ToList(); } }
    }

    public FileCollectorTests()
    {
        Directory.CreateDirectory(Work);
        Directory.CreateDirectory(Downloads);
        var cfg = new WatcherConfig();
        cfg.Collectors.Files.WatchedFolders = new() { Work, Downloads };
        cfg.Collectors.Files.DownloadsFolder = Downloads;
        cfg.Collectors.Files.QuietMs = 600;
        cfg.Collectors.Files.BulkThreshold = 20;
        _collector = new FileActivityCollector(_activity);
        _collector.Start(new CollectorContext(_sink, new ConfigProvider(cfg), NullDiagnosticLog.Instance, SystemClock.Instance));
    }

    public void Dispose()
    {
        _collector.Stop("test");
        _dir.Dispose();
    }

    private WatchEvent Wait(string type, string name)
    {
        WatchEvent? found = null;
        var until = DateTime.UtcNow.AddSeconds(10);
        while (DateTime.UtcNow < until && (found = _sink.All.FirstOrDefault(e => e.EventType == type && e.Metadata["file_name"]?.ToString() == name)) is null)
            Thread.Sleep(100);
        Assert.True(found is not null, $"no {type} for {name}. Got: {string.Join(", ", _sink.All.Select(e => e.EventType + ":" + e.Metadata["file_name"]))}");
        return found!;
    }

    [Fact]
    public void Create_save_rename_delete_are_reported_once_each()
    {
        var p = Path.Combine(Work, "MA023-main.psd");
        File.WriteAllText(p, "v1");
        var created = Wait(EventTypes.FileCreated, "MA023-main.psd");
        Assert.Equal("psd", created.Metadata["extension"]!.ToString());
        Assert.Contains("MA023", created.Metadata["sku_candidates"]!.ToJsonString());
        Assert.Equal(2, created.Metadata["size_bytes"]!.GetValue<long>());

        for (var i = 0; i < 5; i++) { File.AppendAllText(p, "x"); Thread.Sleep(20); }
        Wait(EventTypes.FileSaved, "MA023-main.psd");
        Assert.Single(_sink.All, e => e.EventType == EventTypes.FileSaved);

        var renamed = Path.Combine(Work, "MA023-final.psd");
        File.Move(p, renamed);
        var r = Wait(EventTypes.FileRenamed, "MA023-final.psd");
        Assert.Equal("MA023-main.psd", r.Metadata["old_file_name"]!.ToString());

        File.Delete(renamed);
        Wait(EventTypes.FileDeleted, "MA023-final.psd");
    }

    [Fact]
    public void Browser_style_download_is_linked_to_the_page()
    {
        _activity.SetPage(new BrowserPage(1, 42, "https://sellercentral.amazon.com/reportcentral/FlatFile", "sellercentral.amazon.com", "Reports",
            "Reports - Google Chrome", SiteProfiles.Analyze(new Uri("https://sellercentral.amazon.com/reportcentral/FlatFile"), "Reports"), DateTimeOffset.Now));
        var temp = Path.Combine(Downloads, "Unconfirmed 4711.crdownload");
        File.WriteAllText(temp, "order-id,sku\n");
        File.AppendAllText(temp, "112-1,MA023\n");
        File.Move(temp, Path.Combine(Downloads, "AmazonOrders.csv"));
        var d = Wait(EventTypes.FileDownloaded, "AmazonOrders.csv");
        Assert.Equal("sellercentral.amazon.com", d.Metadata["source_page"]!["domain"]!.ToString());
        Assert.Equal("seller_central", d.Metadata["source_page"]!["site"]!.ToString());
        Assert.DoesNotContain(_sink.All, e => e.Metadata["file_name"]?.ToString()?.EndsWith("crdownload") == true);
    }

    [Fact]
    public void Many_files_at_once_become_one_summary()
    {
        for (var i = 1; i <= 45; i++) File.WriteAllText(Path.Combine(Work, $"MA{i:000}-main.psd"), "x");
        var until = DateTime.UtcNow.AddSeconds(10);
        while (DateTime.UtcNow < until && !_sink.All.Any(e => e.EventType == EventTypes.FileBulkActivity)) Thread.Sleep(100);
        var bulk = Assert.Single(_sink.All, e => e.EventType == EventTypes.FileBulkActivity);
        Assert.Equal(45, bulk.Metadata["total"]!.GetValue<int>() + _sink.All.Count(e => e.EventType == EventTypes.FileCreated));
        Assert.Contains("MA001", bulk.Metadata["sku_candidates"]!.ToJsonString());
    }

    [Fact]
    public void Temp_files_and_folders_are_not_reported()
    {
        File.WriteAllText(Path.Combine(Work, "~$Book1.xlsx"), "lock");
        File.WriteAllText(Path.Combine(Work, "scratch.tmp"), "tmp");
        Directory.CreateDirectory(Path.Combine(Work, "New folder"));
        Thread.Sleep(1800);
        Assert.Empty(_sink.All);
    }

    [Fact]
    public void Files_in_blocked_folders_are_redacted_by_the_privacy_filter()
    {
        var cfg = new WatcherConfig();
        cfg.Privacy.BlockedFolders.Add(Path.Combine(Work, "Personal"));
        Directory.CreateDirectory(Path.Combine(Work, "Personal"));
        Thread.Sleep(500); // Linux adds the new subfolder's watch a moment later (Windows watches subfolders natively)
        File.WriteAllText(Path.Combine(Work, "Personal", "tax-return.pdf"), "x");
        var e = Wait(EventTypes.FileCreated, "tax-return.pdf");
        var stored = new PrivacyFilter(() => cfg).Apply(e)!;
        Assert.DoesNotContain("tax-return", EventJson.Serialize(stored));
        Assert.Equal("blocked_folder", stored.Metadata["excluded_reason"]!.ToString());
    }
}
