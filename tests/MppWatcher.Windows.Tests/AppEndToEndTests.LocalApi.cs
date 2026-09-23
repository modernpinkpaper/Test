using System.Diagnostics;
using MppWatcher.Core.Events;

namespace MppWatcher.Windows.Tests;

public sealed partial class AppEndToEndTests
{
    [Fact]
    public void Scripts_can_report_events_through_the_local_api()
    {
        const string secret = "company-secret-for-tests-0123456789abcdef";
        var cfg = System.Text.Json.Nodes.JsonNode.Parse(File.ReadAllText(ConfigPath))!.AsObject();
        cfg["collectors"]!["local_api"] = new System.Text.Json.Nodes.JsonObject { ["shared_secret"] = secret };
        File.WriteAllText(ConfigPath, cfg.ToJsonString());
        var agent = StartAgent();
        Assert.True(WaitForEvents(ev => ev.Any(e => e.EventType == EventTypes.CollectorStatus && Str(e, "collector_name") == "local_api" && Str(e, "status") == "running"), 20),
            "local_api collector did not start");

        // Exactly what the PowerShell example in docs/LOCAL_API.md does.
        var lines = new[]
        {
            $"$secret = '{secret}'",
            "$body = '{\"event_type\":\"automation_run\",\"script_name\":\"MPP Etsy Customization Updater\",\"sku\":\"PS142\",\"listing_id\":\"123456789\"}'",
            "$ts = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds().ToString()",
            "$hmac = [System.Security.Cryptography.HMACSHA256]::new([Text.Encoding]::UTF8.GetBytes($secret))",
            "$sig = -join ($hmac.ComputeHash([Text.Encoding]::UTF8.GetBytes(\"$ts.$body\")) | ForEach-Object { $_.ToString('x2') })",
            "$r = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:47821/v1/events -Body $body -ContentType 'application/json' -Headers @{ 'X-MPP-Timestamp' = $ts; 'X-MPP-Signature' = $sig }",
            "if (-not $r.accepted) { exit 1 }",
        };
        var script = Path.Combine(_dir, "report.ps1");
        File.WriteAllLines(script, lines);
        var p = Process.Start(new ProcessStartInfo("powershell.exe", $"-NoProfile -ExecutionPolicy Bypass -File \"{script}\"")
            { UseShellExecute = false, RedirectStandardError = true })!;
        Assert.True(p.WaitForExit(30_000));
        Assert.True(p.ExitCode == 0, "PowerShell call failed: " + p.StandardError.ReadToEnd());

        Assert.True(WaitForEvents(ev => ev.Any(e => e.EventType == "automation_run"), 10), "automation_run not stored");
        var run = ReadEvents().First(e => e.EventType == "automation_run");
        Assert.Equal("MPP Etsy Customization Updater", Str(run, "script_name"));
        Assert.Equal("PS142", Str(run, "sku"));
        Assert.Equal("EMP-TEST", run.EmployeeId);
        Assert.Equal(0, StopAgent());
        Assert.True(agent.WaitForExit(15_000));
    }
}
