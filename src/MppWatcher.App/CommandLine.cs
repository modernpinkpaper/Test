namespace MppWatcher.App;

internal enum RunMode { Agent, Viewer, SmokeTest, Stop, WriteDefaultConfig, Version, Help }

/// <summary>
/// MPPWatcher.exe                       run the background watcher (normal mode, started at logon)
/// MPPWatcher.exe --viewer              open the live test viewer
/// MPPWatcher.exe --smoke-test 20       run the watcher for 20 seconds, write a report, exit (0 = OK)
/// MPPWatcher.exe --write-default-config &lt;path&gt;   write a config.json with all defaults
/// Options: --config &lt;path&gt;  use another config file; --data &lt;folder&gt;  override data folder;
///          --result &lt;file&gt;  smoke test report path.
/// </summary>
internal sealed record CommandLine(RunMode Mode, string? ConfigPath, string? DataFolder, int Seconds, string? OutputPath)
{
    public static CommandLine Parse(string[] args)
    {
        var mode = RunMode.Agent;
        string? config = null, data = null, output = null;
        var seconds = 20;
        for (var i = 0; i < args.Length; i++)
        {
            var a = args[i].ToLowerInvariant();
            string? Next() => i + 1 < args.Length ? args[++i] : null;
            switch (a)
            {
                case "--viewer": mode = RunMode.Viewer; break;
                case "--smoke-test":
                    mode = RunMode.SmokeTest;
                    if (i + 1 < args.Length && int.TryParse(args[i + 1], out var s)) { seconds = Math.Clamp(s, 3, 3600); i++; }
                    break;
                case "--write-default-config": mode = RunMode.WriteDefaultConfig; output = Next(); break;
                case "--stop": mode = RunMode.Stop; break;
                case "--version": mode = RunMode.Version; break;
                case "--help": case "-h": case "/?": mode = RunMode.Help; break;
                case "--config": config = Next(); break;
                case "--data": data = Next(); break;
                case "--result": output = Next(); break;
            }
        }
        return new CommandLine(mode, config, data, seconds, output);
    }

    public const string HelpText = """
        MPP Watcher

          MPPWatcher.exe                          Run the background watcher (normal mode).
          MPPWatcher.exe --viewer                 Open the live test viewer.
          MPPWatcher.exe --smoke-test [seconds]   Run briefly, write a report, exit 0 if OK.
          MPPWatcher.exe --stop                   Ask the watcher in this Windows session to stop cleanly.
          MPPWatcher.exe --write-default-config <path>
          MPPWatcher.exe --version

        Options:
          --config <path>    Config file (default %ProgramData%\MPP Watcher\config.json)
          --data <folder>    Data folder override (database, checkpoint)
          --result <file>    Smoke test report file
        """;
}
