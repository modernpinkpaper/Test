using System.IO.Compression;
using MppWatcher.Core.Capture;
using MppWatcher.Core.Events;
using MppWatcher.Core.Export;

namespace MppWatcher.Core.Tests;

public class CaptureControllerTests
{
    [Fact]
    public void Tags_events_only_while_recording()
    {
        var c = new CaptureController();
        var e1 = new WatchEvent { EventType = EventTypes.UiAction };
        c.Tag(e1);
        Assert.Null(e1.Metadata["capture_label"]); // off by default

        c.Start(CaptureMode.Sop, "Create RA file for a KS order");
        var e2 = new WatchEvent { EventType = EventTypes.UiAction };
        c.Tag(e2);
        Assert.Equal("Create RA file for a KS order", e2.Metadata["capture_label"]!.GetValue<string>());
        Assert.Equal("sop", e2.Metadata["capture_mode"]!.GetValue<string>());
        Assert.False(string.IsNullOrEmpty(e2.Metadata["capture_session_id"]!.GetValue<string>()));

        c.Pause();
        var e3 = new WatchEvent { EventType = EventTypes.UiAction };
        c.Tag(e3);
        Assert.Null(e3.Metadata["capture_label"]); // paused = not tagged

        c.Resume();
        Assert.True(c.Current.Recording);
        Assert.True(c.Current.WantsScreenshots); // SOP mode wants screenshots

        c.Start(CaptureMode.Decision, "SP bid review");
        Assert.False(c.Current.WantsScreenshots); // decision mode: no screenshots
        c.Stop();
        var e4 = new WatchEvent { EventType = EventTypes.UiAction };
        c.Tag(e4);
        Assert.Null(e4.Metadata["capture_label"]);
    }
}

public class WeeklyArchiverTests : IDisposable
{
    private readonly TempDir _dir = new();
    public void Dispose() => _dir.Dispose();

    private void Write(string person, string date, string file)
    {
        var d = System.IO.Path.Combine(_dir.Path, person, date);
        Directory.CreateDirectory(d);
        File.WriteAllText(System.IO.Path.Combine(d, file), "{\"x\":1}\n");
    }

    [Fact]
    public void Zips_finished_weeks_and_leaves_the_current_week_alone()
    {
        var person = "DALIAOFFICEPC";
        // "today" = Wed 2026-09-30 (ISO week 40, Mon 2026-09-28)
        var today = new DateTime(2026, 9, 30);
        // Last week (W39): Mon 09-21 .. Sun 09-27
        Write(person, "2026-09-22", "events_0900_1000_DALIAOFFICEPC.jsonl");
        Write(person, "2026-09-23", "events_1000_1100_DALIAOFFICEPC.jsonl");
        // This week (W40): must NOT be touched
        Write(person, "2026-09-28", "events_0900_1000_DALIAOFFICEPC.jsonl");
        Write(person, "2026-09-30", "events_1100_1200_DALIAOFFICEPC.jsonl");

        var pf = System.IO.Path.Combine(_dir.Path, person);
        var n = WeeklyArchiver.Run(pf, person, today, deleteRaw: true);
        Assert.Equal(1, n);

        var zip = System.IO.Path.Combine(pf, "DALIAOFFICEPC_2026-W39.jsonl.zip");
        Assert.True(File.Exists(zip), "week 39 zip not created");
        using (var z = ZipFile.OpenRead(zip))
        {
            var names = z.Entries.Select(e => e.FullName).OrderBy(x => x).ToList();
            Assert.Contains("2026-09-22/events_0900_1000_DALIAOFFICEPC.jsonl", names);
            Assert.Contains("2026-09-23/events_1000_1100_DALIAOFFICEPC.jsonl", names);
        }
        // raw last-week folders deleted, current-week folders kept
        Assert.False(Directory.Exists(System.IO.Path.Combine(pf, "2026-09-22")));
        Assert.False(Directory.Exists(System.IO.Path.Combine(pf, "2026-09-23")));
        Assert.True(Directory.Exists(System.IO.Path.Combine(pf, "2026-09-28")));
        Assert.True(Directory.Exists(System.IO.Path.Combine(pf, "2026-09-30")));
    }

    [Fact]
    public void Keeps_raw_when_delete_is_off_and_is_safe_to_run_twice()
    {
        var person = "PC1";
        var today = new DateTime(2026, 9, 30);
        Write(person, "2026-09-22", "a.jsonl");
        var pf = System.IO.Path.Combine(_dir.Path, person);
        Assert.Equal(1, WeeklyArchiver.Run(pf, person, today, deleteRaw: false));
        Assert.True(Directory.Exists(System.IO.Path.Combine(pf, "2026-09-22")));
        // second run must not throw or duplicate entries
        WeeklyArchiver.Run(pf, person, today, deleteRaw: false);
        using var z = ZipFile.OpenRead(System.IO.Path.Combine(pf, "PC1_2026-W39.jsonl.zip"));
        Assert.Single(z.Entries);
    }
}
