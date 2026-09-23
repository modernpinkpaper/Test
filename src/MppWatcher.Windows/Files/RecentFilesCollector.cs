using System.Collections.Concurrent;
using System.Text.Json.Nodes;
using MppWatcher.Core.Activity;
using MppWatcher.Core.Collectors;
using MppWatcher.Core.Diagnostics;
using MppWatcher.Core.Events;
using MppWatcher.Core.Files;

namespace MppWatcher.Windows.Files;

/// <summary>
/// "File opened": Windows keeps a Recent Items list (%APPDATA%\Microsoft\Windows\Recent) that most
/// programs update when a file is opened through Windows (Explorer, Office, Adobe open dialogs,
/// Notepad, ...). A new or refreshed shortcut there means the file was just opened. The file
/// itself is never read.
/// </summary>
public sealed class RecentFilesCollector : ICollector
{
    private readonly ActivityContext _activity;
    private readonly ConcurrentDictionary<string, DateTimeOffset> _recentlySeen = new(StringComparer.OrdinalIgnoreCase);
    private FileSystemWatcher? _watcher;
    private CollectorContext? _ctx;
    private long _opened;

    public RecentFilesCollector(ActivityContext activity) => _activity = activity;

    public string Name => "recent_files";
    public string Version => "1.0.0";

    public void Start(CollectorContext context)
    {
        _ctx = context;
        var folder = Environment.GetFolderPath(Environment.SpecialFolder.Recent);
        if (!Directory.Exists(folder)) throw new DirectoryNotFoundException("Windows Recent Items folder not found (may be disabled by policy): " + folder);
        _watcher = new FileSystemWatcher(folder, "*.lnk") { NotifyFilter = NotifyFilters.FileName | NotifyFilters.LastWrite, IncludeSubdirectories = false };
        _watcher.Created += (_, e) => OnShortcut(e.FullPath);
        _watcher.Changed += (_, e) => OnShortcut(e.FullPath);
        _watcher.Renamed += (_, e) => OnShortcut(e.FullPath);
        _watcher.EnableRaisingEvents = true;
    }

    public void Stop(string reason) => _watcher?.Dispose();

    public IReadOnlyDictionary<string, object> GetStats() => new Dictionary<string, object> { ["files_opened"] = _opened };

    private void OnShortcut(string lnk)
    {
        var ctx = _ctx;
        if (ctx is null) return;
        try
        {
            Thread.Sleep(150); // let Windows finish writing the shortcut
            var target = ShellLinkReader.TargetOf(lnk);
            if (target is null || Directory.Exists(target)) return; // folders are not "files opened"
            var now = ctx.Clock.Now;
            // Windows touches the shortcut several times per open.
            if (_recentlySeen.TryGetValue(target, out var last) && now - last < TimeSpan.FromSeconds(5)) return;
            _recentlySeen[target] = now;
            if (_recentlySeen.Count > 500) _recentlySeen.Clear();

            var e = this.NewEvent(EventTypes.FileOpened, now);
            var name = FileActivityAggregator.NameOf(target);
            e.Metadata["path"] = target;
            e.Metadata["file_name"] = name;
            e.Metadata["folder"] = FileActivityAggregator.FolderOf(target);
            var ext = Path.GetExtension(name);
            if (!string.IsNullOrEmpty(ext)) e.Metadata["extension"] = ext.TrimStart('.').ToLowerInvariant();
            var skus = SkuFinder.Find(name, ctx.Config.Current.Collectors.Files.SkuPatterns);
            if (skus.Count > 0) e.Metadata["sku_candidates"] = new JsonArray(skus.Select(s => (JsonNode)JsonValue.Create(s)!).ToArray());
            e.Metadata["source"] = "windows_recent_items";
            if (_activity.CurrentApp is { } app)
            {
                e.Metadata["foreground_application"] = app.Application;
                e.Metadata["foreground_process"] = app.ProcessName;
                e.SessionId = app.SessionId;
            }
            e.DedupFingerprint = target;
            ctx.Sink.Emit(e);
            _opened++;
        }
        catch (Exception ex)
        {
            ctx.Log.Warn(Name, "Could not read a Recent Items shortcut", ex);
        }
    }
}
