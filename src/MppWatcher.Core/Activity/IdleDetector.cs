namespace MppWatcher.Core.Activity;

public abstract record IdleTransition
{
    /// <summary>The user stopped using keyboard/mouse at <paramref name="IdleSince"/>; noticed at <paramref name="DetectedAt"/>.</summary>
    public sealed record Started(DateTimeOffset IdleSince, DateTimeOffset DetectedAt) : IdleTransition;

    /// <summary>Input came back at <paramref name="ActiveAgainAt"/>.</summary>
    public sealed record Ended(DateTimeOffset IdleSince, DateTimeOffset ActiveAgainAt) : IdleTransition;
}

/// <summary>
/// Turns "milliseconds since last keyboard/mouse input" samples into idle start/end
/// transitions. Only the time of the last input is used; no keys or positions.
/// Idle start is back-dated to the last input, so the threshold wait is counted as idle.
/// </summary>
public sealed class IdleDetector
{
    private static readonly TimeSpan Tolerance = TimeSpan.FromSeconds(1);
    private readonly Func<TimeSpan> _threshold;

    public IdleDetector(Func<TimeSpan> threshold) => _threshold = threshold;

    public bool IsIdle => IdleSince is not null;
    public DateTimeOffset? IdleSince { get; private set; }
    public DateTimeOffset? LastInput { get; private set; }

    public IdleTransition? Update(TimeSpan timeSinceLastInput, DateTimeOffset now)
    {
        if (timeSinceLastInput < TimeSpan.Zero) timeSinceLastInput = TimeSpan.Zero;
        var lastInput = now - timeSinceLastInput;
        LastInput = lastInput;

        if (IdleSince is null)
        {
            if (timeSinceLastInput < _threshold()) return null;
            IdleSince = lastInput;
            return new IdleTransition.Started(lastInput, now);
        }

        if (lastInput > IdleSince.Value + Tolerance)
        {
            var since = IdleSince.Value;
            IdleSince = null;
            return new IdleTransition.Ended(since, lastInput);
        }
        return null;
    }

    /// <summary>Forget idle state (after lock/sleep, where idle is not meaningful).</summary>
    public void Reset() => IdleSince = null;
}
