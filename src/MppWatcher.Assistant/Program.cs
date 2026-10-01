namespace MppWatcher.Assistant;

/// <summary>
/// Entry point for the MPP live assistant. Being built in steps (see docs/LIVE_ASSISTANT_PLAN.md).
/// Step 1 (this): read NEW events, ask the provider for suggestions, write a recommendations log.
/// No pop-ups yet — the point is to let Dalia eyeball a day of real recommendations and judge quality.
///
///   MppAssistant --activity "<mpp activity person folder>" [--out <folder>] [--person Dalia]
///                [--once | --watch] [--interval 2] [--repeat-threshold 8]
///
/// Default is one pass (--once). --watch loops every --interval minutes until Ctrl+C.
/// With no API key this uses the built-in heuristic provider (a safe stand-in).
/// </summary>
internal static class Program
{
    private static async Task<int> Main(string[] args)
    {
        string? activity = null, outFolder = null, person = "";
        var watch = false;
        var intervalMinutes = 2.0;
        var repeatThreshold = 8;

        for (var i = 0; i < args.Length; i++)
        {
            string? Next() => i + 1 < args.Length ? args[++i] : null;
            switch (args[i].ToLowerInvariant())
            {
                case "--activity": activity = Next(); break;
                case "--out": outFolder = Next(); break;
                case "--person": person = Next() ?? ""; break;
                case "--once": watch = false; break;
                case "--watch": watch = true; break;
                case "--interval": if (double.TryParse(Next(), out var m)) intervalMinutes = Math.Clamp(m, 0.25, 60); break;
                case "--repeat-threshold": if (int.TryParse(Next(), out var t)) repeatThreshold = Math.Max(2, t); break;
                case "--help": case "-h": case "/?": Console.WriteLine(HelpText); return 0;
            }
        }

        if (string.IsNullOrWhiteSpace(activity))
        {
            Console.Error.WriteLine("Missing --activity <folder>. Run with --help for usage.");
            return 2;
        }

        var cfg = new AssistantConfig
        {
            ActivityFolder = activity!,
            OutputFolder = string.IsNullOrWhiteSpace(outFolder) ? activity! : outFolder!,
            Person = person,
        };
        var engine = new AssistantEngine(cfg, new HeuristicLlmProvider(repeatThreshold));

        using var cts = new CancellationTokenSource();
        Console.CancelKeyPress += (_, e) => { e.Cancel = true; cts.Cancel(); };

        do
        {
            try
            {
                var recs = await engine.TickAsync(cts.Token);
                Console.WriteLine($"{DateTime.Now:HH:mm:ss}  {recs.Count} suggestion(s).");
                foreach (var r in recs) Console.WriteLine($"  • [{r.Urgency}] {r.Title}");
            }
            catch (OperationCanceledException) { break; }
            catch (Exception ex) { Console.Error.WriteLine("Tick failed: " + ex.Message); }

            if (!watch) break;
            try { await Task.Delay(TimeSpan.FromMinutes(intervalMinutes), cts.Token); }
            catch (OperationCanceledException) { break; }
        } while (!cts.IsCancellationRequested);

        return 0;
    }

    private const string HelpText = """
        MPP live assistant (Step 1 — reader + memory + recommendations log)

          MppAssistant --activity "<mpp activity person folder>" [options]

        Options:
          --out <folder>          Where to write cursor/memory/recommendations (default: --activity)
          --person <name>         A label for who this is (e.g. Dalia)
          --once                  One pass then exit (default)
          --watch                 Keep running, checking every --interval minutes
          --interval <minutes>    Watch interval (default 2)
          --repeat-threshold <n>  Repeated-click count that triggers an "automate it?" idea (default 8)
        """;
}
