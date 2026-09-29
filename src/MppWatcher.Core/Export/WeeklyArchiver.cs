using System.Globalization;
using System.IO.Compression;
using MppWatcher.Core.Diagnostics;

namespace MppWatcher.Core.Export;

/// <summary>
/// Keeps the export folder tidy: once a week is completely finished, this PC's date folders for that
/// week are zipped into one file and (optionally) the raw .jsonl are deleted. Only fully-past weeks are
/// touched, never the current week, so files still being appended to are never disturbed. Each PC only
/// archives its OWN folder, so PCs sharing one Drive never fight over the same files.
/// </summary>
public static class WeeklyArchiver
{
    /// <summary>
    /// Zips finished weeks under <paramref name="personFolder"/> (…/&lt;pc or employee&gt;/).
    /// Date subfolders are named yyyy-MM-dd. Returns the number of weeks archived.
    /// </summary>
    public static int Run(string personFolder, string personLabel, DateTime today, bool deleteRaw, IDiagnosticLog? log = null)
    {
        if (!Directory.Exists(personFolder)) return 0;
        var currentMonday = MondayOf(today);
        var weeks = new Dictionary<(int, int), List<string>>(); // (isoYear, isoWeek) -> date folders

        foreach (var dir in Directory.EnumerateDirectories(personFolder))
        {
            var name = Path.GetFileName(dir);
            if (!DateTime.TryParseExact(name, "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out var date))
                continue; // not a date folder (e.g. an existing .zip's siblings)
            if (date.Date >= currentMonday) continue; // this week or later: still being written
            var key = (IsoYear(date), IsoWeek(date));
            (weeks.TryGetValue(key, out var list) ? list : weeks[key] = new()).Add(dir);
        }

        var archived = 0;
        foreach (var ((isoYear, isoWeek), dirs) in weeks)
        {
            var zipName = $"{Sanitize(personLabel)}_{isoYear}-W{isoWeek:00}.jsonl.zip";
            var zipPath = Path.Combine(personFolder, zipName);
            try
            {
                var updating = File.Exists(zipPath);
                using (var zip = ZipFile.Open(zipPath, updating ? ZipArchiveMode.Update : ZipArchiveMode.Create))
                {
                    foreach (var dir in dirs.OrderBy(d => d, StringComparer.Ordinal))
                    {
                        var dayName = Path.GetFileName(dir);
                        foreach (var file in Directory.EnumerateFiles(dir, "*.jsonl", SearchOption.AllDirectories))
                        {
                            var entryName = $"{dayName}/{Path.GetFileName(file)}";
                            // GetEntry is only allowed when updating; a fresh Create-mode zip has no entries yet.
                            if (updating && zip.GetEntry(entryName) is not null) continue; // already archived earlier
                            zip.CreateEntryFromFile(file, entryName, CompressionLevel.Optimal);
                        }
                    }
                }
                if (deleteRaw)
                    foreach (var dir in dirs)
                        try { Directory.Delete(dir, recursive: true); } catch (Exception e) { log?.Warn("archive", $"Could not delete {dir} after zipping", e); }
                archived++;
                log?.Info("archive", $"Archived week {isoYear}-W{isoWeek:00} ({dirs.Count} day folders) -> {zipName}");
            }
            catch (Exception e)
            {
                log?.Warn("archive", $"Could not create {zipName}; leaving the raw files in place", e);
                // Do not delete raw if the zip failed.
            }
        }
        return archived;
    }

    private static DateTime MondayOf(DateTime d)
    {
        int diff = ((int)d.DayOfWeek + 6) % 7; // Monday = 0
        return d.Date.AddDays(-diff);
    }

    private static int IsoWeek(DateTime d) => ISOWeek.GetWeekOfYear(d);
    private static int IsoYear(DateTime d) => ISOWeek.GetYear(d);

    private static string Sanitize(string s) => LocalFolderUploader.SafeSegment(s);
}
