namespace MppWatcher.Windows.Tests;

/// <summary>Finds MPPWatcher.exe: the published file in CI (MPPWATCHER_EXE) or the local build.</summary>
internal static class AppEndToEndTestsExe
{
    public static string Path
    {
        get
        {
            var fromEnv = Environment.GetEnvironmentVariable("MPPWATCHER_EXE");
            if (!string.IsNullOrEmpty(fromEnv)) return System.IO.Path.GetFullPath(fromEnv);
            var dir = new DirectoryInfo(AppContext.BaseDirectory);
            while (dir is not null && !Directory.Exists(System.IO.Path.Combine(dir.FullName, "src", "MppWatcher.App"))) dir = dir.Parent;
            var found = dir is null ? null : Directory.EnumerateFiles(System.IO.Path.Combine(dir.FullName, "src", "MppWatcher.App", "bin"), "MPPWatcher.exe", SearchOption.AllDirectories)
                .OrderByDescending(File.GetLastWriteTimeUtc).FirstOrDefault();
            return found ?? throw new FileNotFoundException("Build MppWatcher.App first or set MPPWATCHER_EXE");
        }
    }
}
