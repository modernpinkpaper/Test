using System.Net;
using System.Net.Sockets;
using System.Text;
using MppWatcher.Core.Collectors;
using MppWatcher.Core.Configuration;
using MppWatcher.Core.Diagnostics;
using MppWatcher.Core.Events;
using MppWatcher.Core.LocalApi;

namespace MppWatcher.Core.Tests;

public class ApiRequestValidatorTests
{
    private static readonly byte[] Secret = Encoding.UTF8.GetBytes("test-secret-0123456789abcdef0123456789");
    private readonly ApiRequestValidator _v = new(() => Secret, () => TimeSpan.FromMinutes(5), () => 100);
    private static readonly DateTimeOffset Now = DateTimeOffset.FromUnixTimeSeconds(1_790_000_000);

    private ApiResult Send(string body, long? ts = null, string? sig = null, string? origin = null)
    {
        var t = (ts ?? Now.ToUnixTimeSeconds()).ToString();
        return _v.Validate(t, sig ?? ApiRequestValidator.Sign(Secret, t, body), body, origin, Now);
    }

    [Fact]
    public void Signed_automation_event_is_accepted()
    {
        var r = Send("""{"event_type":"automation_run","script_name":"MPP Etsy Customization Updater","sku":"PS142","listing_id":123456789,"description":"Updated personalization","data":{"fields_changed":3}}""");
        Assert.Equal(202, r.Status);
        var e = r.Event!;
        Assert.Equal("automation_run", e.EventType);
        Assert.Equal("local_api", e.Collector);
        Assert.Equal("MPP Etsy Customization Updater", e.Metadata["script_name"]!.ToString());
        Assert.Equal("PS142", e.Metadata["sku"]!.ToString());
        Assert.Equal("123456789", e.Metadata["listing_id"]!.ToString());
        Assert.Equal(3, e.Metadata["data"]!["fields_changed"]!.GetValue<int>());
    }

    [Fact]
    public void Wrong_or_missing_signature_is_refused()
    {
        var body = """{"event_type":"automation_run","script_name":"x"}""";
        Assert.Equal(401, Send(body, sig: new string('0', 64)).Status);
        Assert.Equal(401, _v.Validate(Now.ToUnixTimeSeconds().ToString(), null, body, null, Now).Status);
        Assert.Equal(401, _v.Validate(null, "abc", body, null, Now).Status);
        // body changed after signing
        var ts = Now.ToUnixTimeSeconds().ToString();
        var sig = ApiRequestValidator.Sign(Secret, ts, body);
        Assert.Equal(401, _v.Validate(ts, sig, body.Replace("\"x\"", "\"y\""), null, Now).Status);
    }

    [Fact]
    public void Old_and_replayed_requests_are_refused()
    {
        var body = """{"event_type":"automation_run","script_name":"x"}""";
        Assert.Equal(401, Send(body, ts: Now.AddMinutes(-10).ToUnixTimeSeconds()).Status);
        Assert.Equal(202, Send(body).Status);
        Assert.Equal(409, Send(body).Status); // exact same signed request again
    }

    [Fact]
    public void Web_pages_are_refused_but_userscript_managers_are_allowed()
    {
        var body = """{"event_type":"automation_run","script_name":"x"}""";
        Assert.Equal(403, Send(body, origin: "https://evil.example").Status);
        Assert.Equal(202, Send("""{"event_type":"automation_run","script_name":"y"}""", origin: "chrome-extension://dhdgffkkebhmkfjojejmpbldmpobfkfo").Status);
    }

    [Theory]
    [InlineData("""{"event_type":"Automation Run","script_name":"x"}""")]
    [InlineData("""{"event_type":"automation_run"}""")]
    [InlineData("""{"event_type":"automation_run","script_name":"x","password":"p"}""")]
    [InlineData("""{"event_type":"automation_run","script_name":"x","data":[1,2]}""")]
    [InlineData("""not json""")]
    public void Bad_bodies_are_refused(string body) => Assert.Equal(400, Send(body).Status);

    [Fact]
    public void Rate_limit_applies()
    {
        var v = new ApiRequestValidator(() => Secret, () => TimeSpan.FromMinutes(5), () => 2);
        string B(int i) => $$"""{"event_type":"automation_run","script_name":"s{{i}}"}""";
        var ts = Now.ToUnixTimeSeconds().ToString();
        Assert.Equal(202, v.Validate(ts, ApiRequestValidator.Sign(Secret, ts, B(1)), B(1), null, Now).Status);
        Assert.Equal(202, v.Validate(ts, ApiRequestValidator.Sign(Secret, ts, B(2)), B(2), null, Now).Status);
        Assert.Equal(429, v.Validate(ts, ApiRequestValidator.Sign(Secret, ts, B(3)), B(3), null, Now).Status);
    }
}

public sealed class LocalApiCollectorTests : IDisposable
{
    private readonly TempDir _dir = new();
    private readonly List<WatchEvent> _events = new();
    private readonly LocalApiCollector _api;
    private readonly string _secret = "company-shared-secret-for-scripts-0123456789";

    private sealed class Sink : IEventSink
    {
        private readonly List<WatchEvent> _e;
        public Sink(List<WatchEvent> e) => _e = e;
        public void Emit(WatchEvent e) { lock (_e) _e.Add(e); }
    }

    public LocalApiCollectorTests()
    {
        var cfg = new WatcherConfig();
        cfg.Collectors.LocalApi.Port = FreePort();
        cfg.Collectors.LocalApi.SharedSecret = _secret;
        _api = new LocalApiCollector(Path.Combine(_dir.Path, "api-secret.txt"));
        _api.Start(new CollectorContext(new Sink(_events), new ConfigProvider(cfg), NullDiagnosticLog.Instance, SystemClock.Instance));
    }

    public void Dispose()
    {
        _api.Stop("test");
        _dir.Dispose();
    }

    private static int FreePort()
    {
        var l = new TcpListener(IPAddress.Loopback, 0);
        l.Start();
        var p = ((IPEndPoint)l.LocalEndpoint).Port;
        l.Stop();
        return p;
    }

    [Fact]
    public async Task Real_http_calls_are_handled()
    {
        using var http = new HttpClient { BaseAddress = new Uri($"http://127.0.0.1:{_api.Port}") };
        var health = await http.GetStringAsync("/v1/health");
        Assert.Contains("\"ok\":true", health);

        var body = """{"event_type":"automation_run","script_name":"MPP Etsy Customization Updater","sku":"PS142","listing_id":"123456789"}""";
        var ts = DateTimeOffset.UtcNow.ToUnixTimeSeconds().ToString();
        var req = new HttpRequestMessage(HttpMethod.Post, "/v1/events") { Content = new StringContent(body, Encoding.UTF8, "application/json") };
        req.Headers.Add("X-MPP-Timestamp", ts);
        req.Headers.Add("X-MPP-Signature", ApiRequestValidator.Sign(Encoding.UTF8.GetBytes(_secret), ts, body));
        var resp = await http.SendAsync(req);
        Assert.Equal(HttpStatusCode.Accepted, resp.StatusCode);
        var e = Assert.Single(_events);
        Assert.Equal("automation_run", e.EventType);
        Assert.Equal("PS142", e.Metadata["sku"]!.ToString());

        var unsigned = new HttpRequestMessage(HttpMethod.Post, "/v1/events") { Content = new StringContent(body) };
        Assert.Equal(HttpStatusCode.Unauthorized, (await http.SendAsync(unsigned)).StatusCode);
        Assert.Equal(HttpStatusCode.NotFound, (await http.GetAsync("/nothing")).StatusCode);
        Assert.Single(_events);
    }

    [Fact]
    public void Per_user_secret_is_created_when_none_is_configured()
    {
        var file = Path.Combine(_dir.Path, "own-secret.txt");
        var cfg = new WatcherConfig();
        cfg.Collectors.LocalApi.Port = FreePort();
        var api = new LocalApiCollector(file);
        api.Start(new CollectorContext(new Sink(new()), new ConfigProvider(cfg), NullDiagnosticLog.Instance, SystemClock.Instance));
        api.Stop("test");
        Assert.True(File.ReadAllText(file).Length >= 64);
    }
}
