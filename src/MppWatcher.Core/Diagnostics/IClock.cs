namespace MppWatcher.Core.Diagnostics;

/// <summary>Time source. Tests use a fake clock so session timing can be checked exactly.</summary>
public interface IClock
{
    DateTimeOffset Now { get; }
}

public sealed class SystemClock : IClock
{
    public static readonly SystemClock Instance = new();
    public DateTimeOffset Now => DateTimeOffset.Now;
}
