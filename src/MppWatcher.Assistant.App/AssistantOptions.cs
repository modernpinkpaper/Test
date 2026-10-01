namespace MppWatcher.Assistant.App;

/// <summary>Command-line options for the pop-up app (mirrors the console assistant, plus --remind).</summary>
internal sealed class AssistantOptions
{
    public string? Activity;
    public string? Out;
    public string Person = "";
    public string? Model;
    public bool Heuristic;
    public double IntervalMinutes = 2;
    public int RepeatThreshold = 8;
    public double RemindMinutes = 60;

    public static AssistantOptions Parse(string[] args)
    {
        var o = new AssistantOptions();
        for (var i = 0; i < args.Length; i++)
        {
            string? Next() => i + 1 < args.Length ? args[++i] : null;
            switch (args[i].ToLowerInvariant())
            {
                case "--activity": o.Activity = Next(); break;
                case "--out": o.Out = Next(); break;
                case "--person": o.Person = Next() ?? ""; break;
                case "--model": o.Model = Next(); break;
                case "--heuristic": o.Heuristic = true; break;
                case "--interval": if (double.TryParse(Next(), out var m)) o.IntervalMinutes = Math.Clamp(m, 0.25, 60); break;
                case "--repeat-threshold": if (int.TryParse(Next(), out var t)) o.RepeatThreshold = Math.Max(2, t); break;
                case "--remind": if (double.TryParse(Next(), out var r)) o.RemindMinutes = Math.Clamp(r, 1, 1440); break;
            }
        }
        return o;
    }
}
