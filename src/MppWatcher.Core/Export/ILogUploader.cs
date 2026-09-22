namespace MppWatcher.Core.Export;

/// <summary>
/// One output file's worth of new lines. <see cref="RelativePath"/> uses forward slashes, e.g.
/// "MPP Activity Logs/EMP001/2026-09-22/events_0900_1000.jsonl".
/// Meaning: append these JSON lines to that file (create it if missing).
/// </summary>
public sealed record ExportFile(string RelativePath, IReadOnlyList<string> JsonLines);

/// <summary>
/// Sends exported log files somewhere (local/network folder now, Google Drive next).
/// Must throw if anything failed, so the events stay "not uploaded" and are retried.
/// Delivery is at-least-once: after a crash between upload and marking, lines can repeat,
/// so consumers should de-duplicate by event_id.
/// </summary>
public interface ILogUploader
{
    string Name { get; }
    Task UploadAsync(IReadOnlyList<ExportFile> files, CancellationToken cancellationToken);
}
