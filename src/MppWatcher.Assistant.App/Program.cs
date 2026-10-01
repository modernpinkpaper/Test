using System.Windows.Forms;

namespace MppWatcher.Assistant.App;

/// <summary>
/// The Windows pop-up assistant. Lives in the tray, checks the activity log every few minutes, and
/// shows a sticky card for each suggestion. The thinking is in the cross-platform MppWatcher.Assistant.
///
///   MppAssistantApp --activity "&lt;mpp activity person folder&gt;" [--out ...] [--person Dalia]
///                   [--model ...] [--heuristic] [--interval 2] [--remind 60]
/// </summary>
internal static class Program
{
    [STAThread]
    private static void Main(string[] args)
    {
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);

        var opts = AssistantOptions.Parse(args);
        if (string.IsNullOrWhiteSpace(opts.Activity))
        {
            MessageBox.Show("Missing --activity <folder>. See docs/LIVE_ASSISTANT_PLAN.md.", "MPP Assistant");
            return;
        }
        Application.Run(new AssistantTrayContext(opts));
    }
}
