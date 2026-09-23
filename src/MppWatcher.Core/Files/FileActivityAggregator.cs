using System.Text.RegularExpressions;

namespace MppWatcher.Core.Files;

public enum RawFileChange { Created, Changed, Deleted, Renamed }

public sealed record RawFileEvent(RawFileChange Change, string Path, string? OldPath, DateTimeOffset At);

public enum FileActivityKind { Created, Saved, Renamed, Moved, Deleted, Downloaded }

public sealed record FileActivity(FileActivityKind Kind, string Path, string? OldPath, DateTimeOffset At);

/// <summary>
/// Turns the noisy stream of file-system notifications into one event per real action.
/// Examples it handles:
///  - one save = many "changed" notices → one Saved
///  - Office/Adobe "safe save" (write temp, delete/rename original, rename temp) → one Saved
///  - Chrome/Edge/Firefox downloads (.crdownload/.part renamed to the real name) → one Downloaded
///  - Explorer move between watched folders (delete + create, same name) → one Moved
///  - temp and lock files (~$Book.xlsx, *.tmp, .~lock#) → ignored
/// Pure logic; the Windows layer feeds it FileSystemWatcher notices.
/// </summary>
public sealed class FileActivityAggregator
{
    private static readonly Regex IgnoredName = new(
        @"^(~\$.*|~.*\.tmp|.*\.(tmp|temp|crdownload|part|partial|download|swp|lock)|\.~lock\..*#|desktop\.ini|thumbs\.db|\.ds_store|[0-9A-F]{8}|~WRL\d+\.tmp|ps\w+\.tmp)$",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    private static readonly Regex DownloadTemp = new(@"\.(crdownload|part|partial|download)$", RegexOptions.IgnoreCase | RegexOptions.Compiled);

    private readonly Func<TimeSpan> _quiet;
    private readonly Dictionary<string, State> _states = new(StringComparer.OrdinalIgnoreCase);

    public FileActivityAggregator(Func<TimeSpan> quiet) => _quiet = quiet;

    private sealed class State
    {
        public bool Created, Changed, Deleted, Downloaded;
        public string? RenamedFrom;
        public DateTimeOffset Last;
    }

    public static bool IsIgnored(string path) => IgnoredName.IsMatch(NameOf(path));

    public int Pending => _states.Count;

    // Windows paths, handled the same on any OS (tests run on Linux too).
    public static string NameOf(string path) => path[(path.LastIndexOfAny(new[] { '\\', '/' }) + 1)..];
    public static string FolderOf(string path) { var i = path.LastIndexOfAny(new[] { '\\', '/' }); return i < 0 ? "" : path[..i]; }

    public void Add(RawFileEvent e)
    {
        switch (e.Change)
        {
            case RawFileChange.Created:
                if (IsIgnored(e.Path)) return;
                Get(e.Path, e.At).Created = true;
                break;

            case RawFileChange.Changed:
                if (IsIgnored(e.Path)) return;
                var c = Get(e.Path, e.At);
                if (!c.Created) c.Changed = true;
                break;

            case RawFileChange.Deleted:
                if (IsIgnored(e.Path)) return;
                if (_states.TryGetValue(e.Path, out var d) && d.Created && !d.Deleted)
                {
                    _states.Remove(e.Path); // created and deleted again quickly: noise
                    return;
                }
                var del = Get(e.Path, e.At);
                del.Deleted = true;
                del.Changed = false;
                break;

            case RawFileChange.Renamed when e.OldPath is not null:
                OnRenamed(e.OldPath, e.Path, e.At);
                break;
        }
    }

    private void OnRenamed(string oldPath, string newPath, DateTimeOffset at)
    {
        var oldIgnored = IsIgnored(oldPath);
        var newIgnored = IsIgnored(newPath);
        if (oldIgnored && newIgnored) return;

        if (!oldIgnored && newIgnored)
        {
            // Original moved aside to a temp/backup name during a "safe save": treat as replaced for now.
            var s = Get(oldPath, at);
            s.Deleted = true;
            return;
        }

        if (oldIgnored)
        {
            // Temp file became the real file.
            var s = Get(newPath, at);
            if (s.Deleted)
            {
                s.Deleted = false;          // the original was replaced: that is a save
                s.Changed = true;
            }
            else if (DownloadTemp.IsMatch(oldPath))
            {
                s.Downloaded = true;
            }
            else if (!s.Changed)
            {
                s.Created = true;
            }
            return;
        }

        // Real rename.
        var from = _states.TryGetValue(oldPath, out var old) ? old : null;
        _states.Remove(oldPath);
        var n = Get(newPath, at);
        if (from is { Created: true }) n.Created = true;
        else if (from is { Downloaded: true }) n.Downloaded = true;
        else n.RenamedFrom = from?.RenamedFrom ?? oldPath;
    }

    /// <summary>Returns actions whose notices have been quiet long enough.</summary>
    public IReadOnlyList<FileActivity> Flush(DateTimeOffset now)
    {
        var quiet = _quiet();
        var result = new List<FileActivity>();
        foreach (var (path, s) in _states.ToList())
        {
            if (!_states.ContainsKey(path) || now - s.Last < quiet) continue;

            if (s.Deleted)
            {
                // A move shows up as delete + create of the same file name in another folder.
                var name = NameOf(path);
                var partner = _states.FirstOrDefault(kv => kv.Value.Created && !kv.Value.Deleted
                    && string.Equals(NameOf(kv.Key), name, StringComparison.OrdinalIgnoreCase)
                    && !string.Equals(kv.Key, path, StringComparison.OrdinalIgnoreCase));
                if (partner.Key is not null)
                {
                    if (now - partner.Value.Last < quiet) continue; // wait for the other half
                    result.Add(new FileActivity(FileActivityKind.Moved, partner.Key, path, partner.Value.Last));
                    _states.Remove(partner.Key);
                }
                else
                {
                    result.Add(new FileActivity(FileActivityKind.Deleted, path, null, s.Last));
                }
            }
            else if (s.Downloaded) result.Add(new FileActivity(FileActivityKind.Downloaded, path, null, s.Last));
            else if (s.Created) result.Add(new FileActivity(FileActivityKind.Created, path, null, s.Last));
            else if (s.RenamedFrom is not null)
            {
                var sameFolder = string.Equals(FolderOf(s.RenamedFrom), FolderOf(path), StringComparison.OrdinalIgnoreCase);
                result.Add(new FileActivity(sameFolder ? FileActivityKind.Renamed : FileActivityKind.Moved, path, s.RenamedFrom, s.Last));
            }
            else if (s.Changed) result.Add(new FileActivity(FileActivityKind.Saved, path, null, s.Last));
            _states.Remove(path);
        }
        return result.OrderBy(r => r.At).ToList();
    }

    private State Get(string path, DateTimeOffset at)
    {
        if (!_states.TryGetValue(path, out var s)) _states[path] = s = new State();
        s.Last = at;
        return s;
    }
}
