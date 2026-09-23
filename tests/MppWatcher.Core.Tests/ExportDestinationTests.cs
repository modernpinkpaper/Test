using MppWatcher.Core.Configuration;
using MppWatcher.Core.Diagnostics;
using MppWatcher.Core.Events;
using MppWatcher.Core.Export;
using MppWatcher.Core.Storage;

namespace MppWatcher.Core.Tests;

public class ExportDestinationTests : IDisposable
{
    private readonly TempDir _dir = new();

    public void Dispose() => _dir.Dispose();

    /// <summary>Fake "drives": folders standing in for C:\, D:\ and the Google Drive letter.</summary>
    private string Drive(string name, bool withMyDrive)
    {
        var root = Path.Combine(_dir.Path, name);
        Directory.CreateDirectory(withMyDrive ? Path.Combine(root, "My Drive") : root);
        return root;
    }

    [Fact]
    public void Default_is_the_mpp_activity_folder_on_google_drive()
    {
        Assert.Equal(@"{GoogleDrive}\My Drive\Personal\mpp activity", new WatcherConfig().Export.DestinationFolder);
        Assert.True(ExportDestination.UsesGoogleDrive(WatcherPaths.ExportFolder(new WatcherConfig())));
    }

    [Fact]
    public void Finds_the_drive_that_has_a_My_Drive_folder()
    {
        var c = Drive("C", false);
        var e = Drive("E", true);
        var resolved = ExportDestination.Resolve("{GoogleDrive}/My Drive/Personal/mpp activity", () => new[] { c, e });
        Assert.Equal(Path.Combine(e, "My Drive/Personal/mpp activity"), resolved);
    }

    [Fact]
    public void Missing_google_drive_is_a_clear_error()
    {
        var c = Drive("C", false);
        var ex = Assert.Throws<DirectoryNotFoundException>(() => ExportDestination.Resolve(@"{GoogleDrive}\My Drive\x", () => new[] { c }));
        Assert.Contains("Google Drive", ex.Message);
    }

    [Fact]
    public void Plain_folders_are_left_alone()
    {
        Assert.Equal(@"\\server\logs", ExportDestination.Resolve(@"\\server\logs", () => throw new InvalidOperationException("not needed")));
    }

    [Fact]
    public void First_drive_with_My_Drive_wins_when_there_is_no_G()
    {
        var first = Drive("E", true);
        Assert.Equal(first, ExportDestination.FindGoogleDriveRoot(new[] { first, Drive("F", true) }));
    }

    [Fact]
    public async Task Google_Drive_closed_keeps_events_pending_then_exports_when_it_is_back()
    {
        using var store = new SqliteEventStore(Path.Combine(_dir.Path, "events.db"), Path.Combine(_dir.Path, "fb"));
        store.Append(new[]
        {
            new WatchEvent
            {
                EventId = "e1", EventType = EventTypes.IdleStart, EmployeeId = "EMP001", ComputerId = "PC-01",
                TimestampLocal = "2026-09-22T09:15:00.000-04:00", TimestampUtc = DateTimeOffset.Parse("2026-09-22T13:15:00Z"),
            },
        });
        var drives = new List<string> { Drive("C", false) };
        var uploader = new LocalFolderUploader(() => ExportDestination.Resolve(@"{GoogleDrive}\My Drive\Personal\mpp activity".Replace('\\', Path.DirectorySeparatorChar), () => drives));
        var svc = new ExportService(store, uploader, NullDiagnosticLog.Instance, new FakeClock(T.Start));

        var r1 = await svc.ExportPendingAsync(100, CancellationToken.None);
        Assert.Equal(1, r1.Failed);
        Assert.Equal(1, Assert.Single(store.GetPending(10)).RetryCount);

        var g = Drive("G", true); // Google Drive for desktop starts
        drives.Add(g);
        var r2 = await svc.ExportPendingAsync(100, CancellationToken.None);
        Assert.Equal(1, r2.Exported);
        Assert.Empty(store.GetPending(10));
        Assert.True(File.Exists(Path.Combine(g, "My Drive", "Personal", "mpp activity", "EMP001", "2026-09-22", "events_0900_1000_PC-01.jsonl")));
    }
}
