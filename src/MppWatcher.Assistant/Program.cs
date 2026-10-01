namespace MppWatcher.Assistant;

/// <summary>
/// Entry point for the MPP live assistant. Being built in steps (see docs/LIVE_ASSISTANT_PLAN.md):
///   Step 1 — reader + memory + recommendations log (no pop-ups)
///   Step 2 — pop-ups + basic buttons
///   Step 3 — auto model-picker
///   Step 4 — "do it for me" buttons (behind a confirm)
/// This skeleton just confirms the project builds; the real logic lands in the next commits.
/// </summary>
internal static class Program
{
    private static int Main(string[] args)
    {
        Console.WriteLine("MPP live assistant — Step 1 in progress. See docs/LIVE_ASSISTANT_PLAN.md.");
        return 0;
    }
}
