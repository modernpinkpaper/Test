using System.Text.Json.Nodes;
using MppWatcher.Core.Activity;
using MppWatcher.Core.Collectors;
using MppWatcher.Core.Configuration;
using MppWatcher.Core.Diagnostics;
using MppWatcher.Core.Events;
using MppWatcher.Core.Privacy;

namespace MppWatcher.Core.Files;

/// <summary>
/// Phase 4: meaningful file activity in work folders — created, saved, renamed, moved, deleted,
/// downloaded. Uses the operating system's change notifications (no polling of folders) and
/// never reads file contents; only name, folder, extension and size.
/// Downloads are linked to the web page that was open; other actions to the app in front.
/// </summary>
public sealed class FileActivityCollector : ICollector
{
    private readonly ActivityContext _activity;
    private readonly List<FileSystemWatcher> _watchers = new();
    private readonly object _gate = new();
    private CollectorContext? _ctx;
    private FileActivityAggregator? _aggregator;
    private Timer? _timer;
    private string _downloads = "";
    private long _raw, _reported, _bulk, _watcherErrors;

    public FileActivityCollector(ActivityContext activity) => _activity = activity;

    public string Name => "files";
    public string Version => "1.0.0";

    public IReadOnlyList<string> WatchedFolders => _watchers.Select(w => w.Path).ToList();

    public void Start(CollectorContext context)
    {
        _ctx = context;
        var cfg = context.Config.Current.Collectors.Files;
        _aggregator = new FileActivityAggregator(() => TimeSpan.FromMilliseconds(context.Config.Current.Collectors.Files.QuietMs));
        _downloads = Normalize(Environment.ExpandEnvironmentVariables(cfg.DownloadsFolder));

        foreach (var folder in cfg.WatchedFolders.Select(f => Normalize(Environment.ExpandEnvironmentVariables(f))).Distinct(StringComparer.OrdinalIgnoreCase))
        {
            if (!Directory.Exists(folder)) { context.Log.Info(Name, $"Folder not found, not watched: {folder}"); continue; }
            if (_watchers.Any(w => folder.StartsWith(w.Path + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase))) continue; // inside another watched folder
            _watchers.Add(CreateWatcher(folder));
        }
        context.Log.Info(Name, "Watching: " + string.Join("; ", _watchers.Select(w => w.Path)));
        _timer = new Timer(_ => Flush(), null, 500, 500);
    }

    public void Stop(string reason)
    {
        foreach (var w in _watchers) w.Dispose();
        _watchers.Clear();
        _timer?.Dispose();
        _timer = null;
        Flush(force: true);
    }

    public IReadOnlyDictionary<string, object> GetStats() => new Dictionary<string, object>
    {
        ["folders_watched"] = _watchers.Count, ["raw_notices"] = _raw, ["events_reported"] = _reported, ["bulk_summaries"] = _bulk, ["watcher_errors"] = _watcherErrors,
    };

    private FileSystemWatcher CreateWatcher(string folder)
    {
        var w = new FileSystemWatcher(folder)
        {
            IncludeSubdirectories = true,
            NotifyFilter = NotifyFilters.FileName | NotifyFilters.LastWrite | NotifyFilters.Size,
            InternalBufferSize = 64 * 1024,
        };
        w.Created += (_, e) => Raw(RawFileChange.Created, e.FullPath, null);
        w.Changed += (_, e) => Raw(RawFileChange.Changed, e.FullPath, null);
        w.Deleted += (_, e) => Raw(RawFileChange.Deleted, e.FullPath, null);
        w.Renamed += (_, e) => Raw(RawFileChange.Renamed, e.FullPath, e.OldFullPath);
        w.Error += (_, e) =>
        {
            _watcherErrors++;
            _ctx?.Log.Warn(Name, $"File watcher problem in {folder} (too many changes at once?); some actions may be missed", e.GetException());
        };
        w.EnableRaisingEvents = true;
        return w;
    }

    private void Raw(RawFileChange change, string path, string? oldPath)
    {
        try
        {
            if (change is RawFileChange.Created or RawFileChange.Changed && Directory.Exists(path)) return; // folders themselves are not reported
            if (IsIgnoredPath(path)) return;
            Interlocked.Increment(ref _raw);
            lock (_gate) _aggregator?.Add(new RawFileEvent(change, path, oldPath, _ctx!.Clock.Now));
        }
        catch (Exception e)
        {
            _ctx?.Log.Warn(Name, "Could not handle a file notice", e);
        }
    }

    private void Flush(bool force = false)
    {
        var ctx = _ctx;
        if (ctx is null || _aggregator is null) return;
        IReadOnlyList<FileActivity> done;
        lock (_gate) done = _aggregator.Flush(force ? DateTimeOffset.MaxValue : ctx.Clock.Now);
        if (done.Count == 0) return;
        try
        {
            if (done.Count > ctx.Config.Current.Collectors.Files.BulkThreshold) EmitBulk(done);
            else foreach (var a in done) { ctx.Sink.Emit(ToEvent(a)); Interlocked.Increment(ref _reported); }
        }
        catch (Exception e)
        {
            ctx.Log.Warn(Name, "Could not report file activity", e);
        }
    }

    private WatchEvent ToEvent(FileActivity a)
    {
        var type = a.Kind switch
        {
            FileActivityKind.Created when IsInDownloads(a.Path) => EventTypes.FileDownloaded,
            FileActivityKind.Created => EventTypes.FileCreated,
            FileActivityKind.Saved => EventTypes.FileSaved,
            FileActivityKind.Renamed => EventTypes.FileRenamed,
            FileActivityKind.Moved => EventTypes.FileMoved,
            FileActivityKind.Deleted => EventTypes.FileDeleted,
            FileActivityKind.Downloaded => EventTypes.FileDownloaded,
            _ => EventTypes.FileSaved,
        };
        var e = this.NewEvent(type, a.At);
        var name = FileActivityAggregator.NameOf(a.Path);
        var m = e.Metadata;
        m["path"] = a.Path;
        m["file_name"] = name;
        m["folder"] = FileActivityAggregator.FolderOf(a.Path);
        var ext = Path.GetExtension(name);
        if (!string.IsNullOrEmpty(ext)) m["extension"] = ext.TrimStart('.').ToLowerInvariant();
        if (a.OldPath is not null)
        {
            m["old_path"] = a.OldPath;
            m["old_file_name"] = FileActivityAggregator.NameOf(a.OldPath);
        }
        try
        {
            var info = new FileInfo(a.Path);
            if (info.Exists) m["size_bytes"] = info.Length;
        }
        catch { /* file busy or gone */ }
        var skus = SkuFinder.Find(name, _ctx!.Config.Current.Collectors.Files.SkuPatterns);
        if (skus.Count > 0) m["sku_candidates"] = new JsonArray(skus.Select(s => (JsonNode)JsonValue.Create(s)!).ToArray());

        if (type == EventTypes.FileDownloaded && _activity.LatestPage(a.At, TimeSpan.FromMinutes(3)) is { } page)
        {
            // Where it most likely came from: the page open in the browser just before.
            var src = new JsonObject { ["url"] = page.Url, ["domain"] = page.Domain, ["page_title"] = page.PageTitle, ["browser_process"] = page.ProcessId };
            foreach (var (k, v) in ActivityContext.PageJson(page.Info, compact: true)) src[k] = v?.DeepClone();
            m["source_page"] = src;
            m["source_is_inferred"] = true;
        }
        else if (_activity.CurrentApp is { } app)
        {
            // The app in front at the time — a strong hint, not proof, of which program saved the file.
            m["foreground_application"] = app.Application;
            m["foreground_process"] = app.ProcessName;
            e.SessionId = app.SessionId;
        }
        e.DedupFingerprint = type + "|" + a.Path;
        return e;
    }

    private void EmitBulk(IReadOnlyList<FileActivity> done)
    {
        _bulk++;
        var e = this.NewEvent(EventTypes.FileBulkActivity, done[0].At);
        var m = e.Metadata;
        m["total"] = done.Count;
        var counts = new JsonObject();
        foreach (var g in done.GroupBy(d => d.Kind)) counts[g.Key.ToString().ToLowerInvariant()] = g.Count();
        m["counts"] = counts;
        var folders = new JsonArray();
        foreach (var g in done.GroupBy(d => FileActivityAggregator.FolderOf(d.Path)).OrderByDescending(g => g.Count()).Take(10))
            folders.Add(new JsonObject { ["folder"] = g.Key, ["files"] = g.Count() });
        m["folders"] = folders;
        m["sample_files"] = new JsonArray(done.Take(20).Select(d => (JsonNode)JsonValue.Create(FileActivityAggregator.NameOf(d.Path))!).ToArray());
        var skus = done.SelectMany(d => SkuFinder.Find(FileActivityAggregator.NameOf(d.Path), _ctx!.Config.Current.Collectors.Files.SkuPatterns)).Distinct().Take(200).ToList();
        if (skus.Count > 0) m["sku_candidates"] = new JsonArray(skus.Select(s => (JsonNode)JsonValue.Create(s)!).ToArray());
        m["path"] = FileActivityAggregator.FolderOf(done[0].Path); // lets blocked_folders apply
        if (_activity.CurrentApp is { } app) m["foreground_application"] = app.Application;
        _ctx!.Sink.Emit(e);
    }

    private bool IsIgnoredPath(string path)
    {
        var cfg = _ctx!.Config.Current;
        return WildcardMatcher.MatchesAny(path, cfg.Collectors.Files.IgnorePaths)
               || WildcardMatcher.MatchesAny(path.Replace('/', '\\'), cfg.Collectors.Files.IgnorePaths);
    }

    private bool IsInDownloads(string path) =>
        _downloads.Length > 0 && path.StartsWith(_downloads + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase);

    private static string Normalize(string folder)
    {
        try { return Path.GetFullPath(folder).TrimEnd(Path.DirectorySeparatorChar); }
        catch { return folder; }
    }
}
