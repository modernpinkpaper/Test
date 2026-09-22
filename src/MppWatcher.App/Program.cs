using System.Runtime.InteropServices;
using MppWatcher.Core.Configuration;
using MppWatcher.Core.Diagnostics;

namespace MppWatcher.App;

internal static class Program
{
    /// <summary>One watcher per Windows user session.</summary>
    public const string AgentMutexName = @"Local\MPPWatcher.Agent";

    /// <summary>Signalled by "MPPWatcher.exe --stop" (installer, tests) to stop the agent cleanly.</summary>
    public const string StopEventName = @"Local\MPPWatcher.Stop";

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
            case RunMode.Stop:
                return RequestStop();
        }

        ApplicationConfiguration.Initialize();
        var configPath = cmd.ConfigPath ?? WatcherPaths.DefaultConfigPath;

        if (cmd.Mode == RunMode.Inspect)
        {
            Application.Run(new InspectorForm(configPath));
            return 0;
        }

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

    /// <summary>Exit codes: 0 = stopped (or was not running), 2 = still running after 20 s.</summary>
    private static int RequestStop()
    {
        if (!Mutex.TryOpenExisting(AgentMutexName, out var running))
        {
            WriteConsole("MPP Watcher is not running in this session.");
            return 0;
        }
        running.Dispose();
        if (EventWaitHandle.TryOpenExisting(StopEventName, out var stop))
        {
            using (stop) stop.Set();
        }
        var deadline = DateTime.UtcNow.AddSeconds(20);
        while (DateTime.UtcNow < deadline)
        {
            if (!Mutex.TryOpenExisting(AgentMutexName, out var m)) { WriteConsole("MPP Watcher stopped."); return 0; }
            m.Dispose();
            Thread.Sleep(250);
        }
        WriteConsole("MPP Watcher did not stop within 20 seconds.");
        return 2;
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
