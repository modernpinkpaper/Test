using System.Runtime.InteropServices;
using MppWatcher.Core.Configuration;
using MppWatcher.Core.Diagnostics;

namespace MppWatcher.App;

internal static class Program
{
    /// <summary>One watcher per Windows user session.</summary>
    public const string AgentMutexName = @"Local\MPPWatcher.Agent";

    [STAThread]
    private static int Main(string[] args)
    {
        var cmd = CommandLine.Parse(args);
        switch (cmd.Mode)
        {
            case RunMode.Help:
                WriteConsole(CommandLine.HelpText);
                return 0;
            case RunMode.Version:
                WriteConsole("MPP Watcher " + MppWatcher.Core.Collectors.WatcherVersion.Current);
                return 0;
            case RunMode.WriteDefaultConfig:
                return WriteDefaultConfig(cmd.OutputPath);
        }

        ApplicationConfiguration.Initialize();
        var configPath = cmd.ConfigPath ?? WatcherPaths.DefaultConfigPath;

        if (cmd.Mode == RunMode.Viewer)
        {
            Application.Run(new ViewerForm(configPath, cmd.DataFolder));
            return 0;
        }

        using var provider = new ConfigProvider(configPath, NullDiagnosticLog.Instance);
        var log = new FileDiagnosticLog(WatcherPaths.LogFolder(provider.Current), () => provider.Current.DebugMode);
        InstallCrashHandlers(log);

        if (cmd.Mode == RunMode.SmokeTest)
        {
            return SmokeTest.Run(configPath, cmd.DataFolder, cmd.Seconds, cmd.OutputPath, log);
        }

        using var mutex = new Mutex(initiallyOwned: true, AgentMutexName, out var createdNew);
        if (!createdNew)
        {
            log.Info("app", "Another MPP Watcher is already running in this session; exiting");
            return 0;
        }

        try
        {
            using var agent = new AgentContext(configPath, cmd.DataFolder, log);
            Application.Run(agent);
            return 0;
        }
        catch (Exception e)
        {
            log.Error("app", "Watcher crashed during start", e);
            return 1; // non-zero so Task Scheduler's "restart on failure" kicks in
        }
    }

    private static void InstallCrashHandlers(IDiagnosticLog log)
    {
        Application.SetUnhandledExceptionMode(UnhandledExceptionMode.CatchException);
        Application.ThreadException += (_, e) => log.Error("app", "Unhandled UI-thread exception (watcher keeps running)", e.Exception);
        AppDomain.CurrentDomain.UnhandledException += (_, e) =>
            log.Error("app", $"Fatal unhandled exception (terminating={e.IsTerminating})", e.ExceptionObject as Exception);
        TaskScheduler.UnobservedTaskException += (_, e) =>
        {
            log.Warn("app", "Unobserved background task exception", e.Exception);
            e.SetObserved();
        };
    }

    private static int WriteDefaultConfig(string? path)
    {
        path ??= WatcherPaths.DefaultConfigPath;
        if (File.Exists(path))
        {
            WriteConsole($"Config already exists, not overwritten: {path}");
            return 0;
        }
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(path))!);
        File.WriteAllText(path, ConfigLoader.ToJson(new WatcherConfig()));
        WriteConsole($"Wrote default config: {path}");
        return 0;
    }

    /// <summary>WinExe has no console of its own; attach to the caller's console when there is one.</summary>
    internal static void WriteConsole(string text)
    {
        try
        {
            if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows)) AttachConsole(-1);
            Console.WriteLine(text);
        }
        catch
        {
            // No console available: fine.
        }
    }

    [DllImport("kernel32.dll")] private static extern bool AttachConsole(int processId);
}
