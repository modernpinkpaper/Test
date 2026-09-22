using MppWatcher.Core.Activity;

namespace MppWatcher.Core.Tests;

public class IdleDetectorTests
{
    [Fact]
    public void Detects_idle_start_backdated_and_idle_end_at_input_time()
    {
        var d = new IdleDetector(() => TimeSpan.FromMinutes(5));
        var now = T.Start;
        Assert.Null(d.Update(TimeSpan.FromMinutes(4), now));

        var started = Assert.IsType<IdleTransition.Started>(d.Update(TimeSpan.FromMinutes(5), now.AddMinutes(1)));
        Assert.Equal(now.AddMinutes(-4), started.IdleSince);
        Assert.True(d.IsIdle);

        Assert.Null(d.Update(TimeSpan.FromMinutes(20), now.AddMinutes(16))); // still idle

        var ended = Assert.IsType<IdleTransition.Ended>(d.Update(TimeSpan.FromSeconds(3), now.AddMinutes(30)));
        Assert.Equal(now.AddMinutes(30).AddSeconds(-3), ended.ActiveAgainAt);
        Assert.False(d.IsIdle);
    }

    [Fact]
    public void Threshold_changes_apply_immediately()
    {
        var threshold = TimeSpan.FromMinutes(5);
        var d = new IdleDetector(() => threshold);
        Assert.Null(d.Update(TimeSpan.FromMinutes(2), T.Start));
        threshold = TimeSpan.FromMinutes(1);
        Assert.IsType<IdleTransition.Started>(d.Update(TimeSpan.FromMinutes(2), T.Start));
    }
}
