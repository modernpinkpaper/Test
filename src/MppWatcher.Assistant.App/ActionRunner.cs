using System.Diagnostics;
using System.Windows.Forms;
using MppWatcher.Assistant;

namespace MppWatcher.Assistant.App;

/// <summary>
/// Runs a button's action on the PC. The account-dependent ones (add_tracker / add_reminder) degrade
/// gracefully for now — they open the target page or copy the text — until the Google integration
/// (Step 4) is wired with the user's login. remind / dismiss / not_helpful are handled by the card.
/// </summary>
internal static class ActionRunner
{
    public static void Run(SuggestedButton b, Recommendation rec)
    {
        switch (b.Kind)
        {
            case "open_url":
            case "open_file":
                OpenTarget(b.Target);
                break;

            case "copy":
            case "draft_message":
                Copy(string.IsNullOrWhiteSpace(b.Target) ? rec.Title : b.Target!);
                break;

            case "copy_build_prompt":
                // The AI puts a full Claude Code prompt (steps/data + "confirm the plan first") in Target.
                Copy(string.IsNullOrWhiteSpace(b.Target) ? rec.Why : b.Target!);
                break;

            case "add_tracker":
                // Try the real Google Sheets write; if no login/creds or it fails, fall back.
                if (!GoogleActions.TryAddToTracker(rec)) FallbackOpenOrCopy(b, rec);
                break;

            case "add_reminder":
                if (!GoogleActions.TryAddReminder(rec)) FallbackOpenOrCopy(b, rec);
                break;
        }
    }

    private static void FallbackOpenOrCopy(SuggestedButton b, Recommendation rec)
    {
        if (!string.IsNullOrWhiteSpace(b.Target) && b.Target!.StartsWith("http", StringComparison.OrdinalIgnoreCase))
            OpenTarget(b.Target);
        else
            Copy(string.IsNullOrWhiteSpace(b.Target) ? rec.Title : b.Target!);
    }

    private static void OpenTarget(string? target)
    {
        if (string.IsNullOrWhiteSpace(target)) return;
        Process.Start(new ProcessStartInfo(target) { UseShellExecute = true });
    }

    private static void Copy(string text)
    {
        if (string.IsNullOrEmpty(text)) return;
        Clipboard.SetText(text);
    }
}
