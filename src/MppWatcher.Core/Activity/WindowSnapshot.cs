namespace MppWatcher.Core.Activity;

/// <summary>What the Windows layer knows about the current foreground window.</summary>
public sealed record WindowSnapshot(
    long Handle,
    int ProcessId,
    string ProcessName,
    string? ApplicationName = null,
    string? ExecutablePath = null,
    string? Title = null,
    string? WindowClass = null,
    string? Monitor = null)
{
    public bool IsSameWindow(WindowSnapshot? other) =>
        other is not null && other.Handle == Handle && other.ProcessId == ProcessId;

    /// <summary>Friendly name for display: "Google Chrome" rather than "chrome".</summary>
    public string DisplayApplication => string.IsNullOrWhiteSpace(ApplicationName) ? ProcessName : ApplicationName!;
}
