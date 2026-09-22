namespace MppWatcher.Core.Export;

/// <summary>Appends JSONL files under a root folder. The root can be a network share or a synced folder.</summary>
public sealed class LocalFolderUploader : ILogUploader
{
    private readonly string _root;

    public LocalFolderUploader(string root) => _root = root;

    public string Name => "local_folder";

    public async Task UploadAsync(IReadOnlyList<ExportFile> files, CancellationToken cancellationToken)
    {
        foreach (var f in files)
        {
            cancellationToken.ThrowIfCancellationRequested();
            var parts = f.RelativePath.Split('/', StringSplitOptions.RemoveEmptyEntries).Select(SafeSegment);
            var path = Path.Combine(new[] { _root }.Concat(parts).ToArray());
            Directory.CreateDirectory(Path.GetDirectoryName(path)!);
            await using var stream = new FileStream(path, FileMode.Append, FileAccess.Write, FileShare.Read);
            await using var writer = new StreamWriter(stream);
            foreach (var line in f.JsonLines) await writer.WriteLineAsync(line.AsMemory(), cancellationToken);
            await writer.FlushAsync(cancellationToken);
            stream.Flush(flushToDisk: true);
        }
    }

    /// <summary>Removes characters Windows does not allow in file/folder names (e.g. from an employee id).</summary>
    public static string SafeSegment(string segment)
    {
        var invalid = Path.GetInvalidFileNameChars().Concat(new[] { '<', '>', ':', '"', '/', '\\', '|', '?', '*' }).ToHashSet();
        var cleaned = new string(segment.Select(c => invalid.Contains(c) || char.IsControl(c) ? '_' : c).ToArray()).Trim().TrimEnd('.');
        return cleaned is "" or "." or ".." ? "_" : cleaned;
    }
}
