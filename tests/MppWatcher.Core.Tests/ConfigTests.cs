using MppWatcher.Core.Configuration;

namespace MppWatcher.Core.Tests;

public class ConfigTests
{
    [Fact]
    public void Missing_file_gives_defaults()
    {
        var r = ConfigLoader.Load(Path.Combine(Path.GetTempPath(), Guid.NewGuid() + ".json"));
        Assert.Null(r.Error);
        Assert.False(r.FileExisted);
        Assert.Equal(300, r.Config.IdleTimeoutSeconds);
        Assert.Contains("KeePass*", r.Config.Privacy.BlockedApplications);
    }

    [Fact]
    public void Snake_case_json_with_comments_is_read()
    {
        var r = ConfigLoader.Parse("""
            {
              // admin notes are allowed
              "employee_id": "EMP007",
              "idle_timeout_seconds": 120,
              "employee_id_by_windows_user": { "OFFICE\\jane": "EMP001" },
              "collectors": { "process": { "enabled": false } },
              "privacy": { "blocked_domains": ["*payroll*"] },
            }
            """);
        Assert.Null(r.Error);
        Assert.Equal("EMP007", r.Config.EmployeeId);
        Assert.Equal(120, r.Config.IdleTimeoutSeconds);
        Assert.False(r.Config.Collectors.Process.Enabled);
        Assert.True(r.Config.Collectors.Activity.Enabled);
        Assert.Equal(new[] { "*payroll*" }, r.Config.Privacy.BlockedDomains);
        Assert.Equal("EMP001", r.Config.EmployeeIdByWindowsUser["office\\JANE"]);
    }

    [Fact]
    public void Broken_json_gives_defaults_and_an_error()
    {
        var r = ConfigLoader.Parse("{ this is not json");
        Assert.NotNull(r.Error);
        Assert.Equal(300, r.Config.IdleTimeoutSeconds);
    }

    [Fact]
    public void Out_of_range_values_are_clamped()
    {
        var r = ConfigLoader.Parse("""{ "idle_timeout_seconds": 1, "collectors": { "activity": { "poll_interval_ms": 1 } }, "privacy": { "blocked_mode": "weird" } }""");
        Assert.Equal(30, r.Config.IdleTimeoutSeconds);
        Assert.Equal(200, r.Config.Collectors.Activity.PollIntervalMs);
        Assert.Equal("redact", r.Config.Privacy.BlockedMode);
    }

    [Fact]
    public void Default_config_round_trips()
    {
        var json = ConfigLoader.ToJson(new WatcherConfig());
        Assert.Contains("\"idle_timeout_seconds\": 300", json);
        var r = ConfigLoader.Parse(json);
        Assert.Null(r.Error);
    }

    [Fact]
    public void Provider_reloads_and_keeps_last_good_config_on_error()
    {
        var path = Path.Combine(Path.GetTempPath(), Guid.NewGuid() + ".json");
        try
        {
            File.WriteAllText(path, """{ "idle_timeout_seconds": 100 }""");
            using var p = new ConfigProvider(path, new Diagnostics.MemoryDiagnosticLog());
            Assert.Equal(100, p.Current.IdleTimeoutSeconds);
            File.WriteAllText(path, """{ "idle_timeout_seconds": 200 }""");
            p.Reload();
            Assert.Equal(200, p.Current.IdleTimeoutSeconds);
            File.WriteAllText(path, "{ broken");
            p.Reload();
            Assert.Equal(200, p.Current.IdleTimeoutSeconds);
        }
        finally { File.Delete(path); }
    }
}
