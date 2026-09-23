using System.Diagnostics;

namespace MppWatcher.Windows.Tests;

public sealed partial class AppEndToEndTests
{
    /// <summary>
    /// Google Drive for desktop shows up as a drive letter with a "My Drive" folder. CI has no Google Drive,
    /// so a temp folder is mapped to a free drive letter with "subst". The agent uses the default
    /// export folder ({GoogleDrive}\My Drive\Personal\mpp activity) and must find that drive by itself.
    /// </summary>
    [Fact]
    public void Export_now_writes_to_the_google_drive_folder()
    {
        var fakeDrive = Path.Combine(_dir, "gdrive");
        Directory.CreateDirectory(Path.Combine(fakeDrive, "My Drive", "Personal"));
        var letter = FreeDriveLetter();
        Assert.Equal(0, Subst($"{letter}: \"{fakeDrive}\""));
        try
        {
            File.WriteAllText(ConfigPath, $$"""
                {
                  "employee_id": "EMP-TEST",
                  "log_folder": {{Json(Path.Combine(_dir, "logs"))}}
                }
                """);
            var agent = StartAgent();
            Assert.True(WaitForEvents(ev => ev.Count >= 3, 20), "agent did not start");

            var target = Path.Combine($"{letter}:\\", "My Drive", "Personal", "mpp activity", "EMP-TEST");
            string[] Files() => Directory.Exists(target) ? Directory.GetFiles(target, "*.jsonl", SearchOption.AllDirectories) : Array.Empty<string>();

            Assert.True(Desktop.WaitUntil(() =>
            {
                var export = Run("--export-now");
                Assert.True(export.WaitForExit(150_000), "--export-now did not return");
                Assert.Equal(0, export.ExitCode);
                return Files().Length > 0;
            }, TimeSpan.FromSeconds(60)), $"no files in {target}");

            var file = Files()[0];
            _out.WriteLine("Exported: " + file);
            var name = Path.GetFileName(file);
            Assert.Matches(@"^events_\d{2}00_\d{2}00_.+\.jsonl$", name);
            Assert.EndsWith("_" + Environment.MachineName + ".jsonl", name, StringComparison.OrdinalIgnoreCase);
            Assert.Equal(DateTime.Now.ToString("yyyy-MM-dd"), Path.GetFileName(Path.GetDirectoryName(file)));
            Assert.Contains("\"event_type\":\"watcher_started\"", File.ReadAllText(file));

            Assert.Equal(0, StopAgent());
            Assert.True(agent.WaitForExit(15_000), "agent did not exit after --stop");
        }
        finally
        {
            Subst($"{letter}: /d");
        }
    }

    [Fact]
    public void Export_now_says_when_the_watcher_is_not_running()
    {
        var export = Run("--export-now");
        Assert.True(export.WaitForExit(30_000));
        Assert.Equal(1, export.ExitCode);
    }

    private static char FreeDriveLetter()
    {
        var used = DriveInfo.GetDrives().Select(d => char.ToUpperInvariant(d.Name[0])).ToHashSet();
        for (var c = 'Y'; c > 'H'; c--)
            if (!used.Contains(c)) return c;
        throw new InvalidOperationException("no free drive letter");
    }

    private static int Subst(string args)
    {
        using var p = Process.Start(new ProcessStartInfo("subst.exe", args) { UseShellExecute = false, CreateNoWindow = true })!;
        p.WaitForExit(15_000);
        return p.ExitCode;
    }
}
