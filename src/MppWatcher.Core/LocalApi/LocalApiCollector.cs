using System.Net;
using System.Net.Sockets;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json.Nodes;
using MppWatcher.Core.Collectors;
using MppWatcher.Core.Configuration;
using MppWatcher.Core.Diagnostics;

namespace MppWatcher.Core.LocalApi;

/// <summary>
/// Local event API for the company's own scripts and tools.
///   GET  http://127.0.0.1:47821/v1/health   → {"ok":true}
///   POST http://127.0.0.1:47821/v1/events   → signed JSON event (see docs/LOCAL_API.md)
/// Only listens on 127.0.0.1 (never the network). A tiny built-in HTTP server is used so no
/// Windows URL reservation or admin rights are needed.
/// </summary>
public sealed class LocalApiCollector : ICollector
{
    private readonly string _secretFile;
    private TcpListener? _listener;
    private CancellationTokenSource? _cts;
    private CollectorContext? _ctx;
    private ApiRequestValidator? _validator;
    private byte[] _secret = Array.Empty<byte>();
    private long _accepted, _rejected;

    public LocalApiCollector(string secretFile) => _secretFile = secretFile;

    public string Name => "local_api";
    public string Version => "1.0.0";
    public int Port { get; private set; }

    public void Start(CollectorContext context)
    {
        _ctx = context;
        var cfg = context.Config.Current.Collectors.LocalApi;
        _secret = LoadSecret(cfg);
        _validator = new ApiRequestValidator(() => _secret,
            () => TimeSpan.FromSeconds(context.Config.Current.Collectors.LocalApi.MaxClockSkewSeconds),
            () => context.Config.Current.Collectors.LocalApi.MaxEventsPerMinute);

        // Several people signed in on one PC each run a watcher: take the next free port if needed.
        Exception? last = null;
        for (var p = cfg.Port; p < cfg.Port + 10; p++)
        {
            try
            {
                var l = new TcpListener(IPAddress.Loopback, p);
                l.Start();
                _listener = l;
                Port = p;
                break;
            }
            catch (SocketException e) { last = e; }
        }
        if (_listener is null) throw new InvalidOperationException($"No free port for the local API from {cfg.Port}", last);
        if (Port != cfg.Port) context.Log.Warn(Name, $"Port {cfg.Port} busy (another user's watcher?); using {Port}");
        _cts = new CancellationTokenSource();
        _ = Task.Run(() => AcceptLoop(_cts.Token));
        context.Log.Info(Name, $"Local event API on http://127.0.0.1:{Port}/v1/events");
    }

    public void Stop(string reason)
    {
        _cts?.Cancel();
        _listener?.Stop();
    }

    public IReadOnlyDictionary<string, object> GetStats() => new Dictionary<string, object>
    {
        ["port"] = Port, ["accepted"] = _accepted, ["rejected"] = _rejected,
    };

    private byte[] LoadSecret(LocalApiConfig cfg)
    {
        if (!string.IsNullOrWhiteSpace(cfg.SharedSecret)) return Encoding.UTF8.GetBytes(cfg.SharedSecret.Trim());
        if (File.Exists(_secretFile))
        {
            var existing = File.ReadAllText(_secretFile).Trim();
            if (existing.Length >= 32) return Encoding.UTF8.GetBytes(existing);
        }
        var fresh = Convert.ToHexString(RandomNumberGenerator.GetBytes(32)).ToLowerInvariant();
        Directory.CreateDirectory(Path.GetDirectoryName(_secretFile)!);
        File.WriteAllText(_secretFile, fresh);
        return Encoding.UTF8.GetBytes(fresh);
    }

    private async Task AcceptLoop(CancellationToken ct)
    {
        while (!ct.IsCancellationRequested)
        {
            TcpClient client;
            try { client = await _listener!.AcceptTcpClientAsync(ct); }
            catch { return; }
            _ = Task.Run(() => Handle(client, ct), ct);
        }
    }

    private async Task Handle(TcpClient client, CancellationToken ct)
    {
        using var _ = client;
        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(ct);
        timeout.CancelAfter(TimeSpan.FromSeconds(10));
        var stream = client.GetStream();
        try
        {
            var (method, path, headers, body) = await ReadRequest(stream, timeout.Token);
            var (status, json) = Route(method, path, headers, body);
            await Write(stream, status, json, timeout.Token);
        }
        catch (Exception e) when (e is IOException or OperationCanceledException or InvalidDataException or SocketException)
        {
            try { await Write(stream, 400, new JsonObject { ["error"] = "bad request" }, CancellationToken.None); } catch { }
        }
    }

    private (int, JsonObject) Route(string method, string path, Dictionary<string, string> headers, string body)
    {
        var ctx = _ctx!;
        if (method == "GET" && path == "/v1/health")
            return (200, new JsonObject { ["ok"] = true, ["service"] = "MPP Watcher", ["version"] = WatcherVersion.Current });
        if (path != "/v1/events") return (404, new JsonObject { ["error"] = "not found" });
        if (method != "POST") return (405, new JsonObject { ["error"] = "use POST" });

        headers.TryGetValue("x-mpp-timestamp", out var ts);
        headers.TryGetValue("x-mpp-signature", out var sig);
        headers.TryGetValue("origin", out var origin);
        var result = _validator!.Validate(ts, sig, body, origin, ctx.Clock.Now);
        if (result.Event is null)
        {
            Interlocked.Increment(ref _rejected);
            ctx.Log.Warn(Name, $"Rejected API request: {result.Status} {result.Message}");
            return (result.Status, new JsonObject { ["error"] = result.Message });
        }
        ctx.Sink.Emit(result.Event);
        Interlocked.Increment(ref _accepted);
        return (202, new JsonObject { ["accepted"] = true, ["event_id"] = result.Event.EventId });
    }

    private static async Task<(string Method, string Path, Dictionary<string, string> Headers, string Body)> ReadRequest(NetworkStream stream, CancellationToken ct)
    {
        var buffer = new byte[ApiRequestValidator.MaxBodyBytes + 8192];
        var read = 0;
        int headerEnd;
        while ((headerEnd = IndexOf(buffer, read, "\r\n\r\n"u8)) < 0)
        {
            if (read >= 8192) throw new InvalidDataException("headers too large");
            var n = await stream.ReadAsync(buffer.AsMemory(read, buffer.Length - read), ct);
            if (n == 0) throw new InvalidDataException("connection closed");
            read += n;
        }
        var head = Encoding.ASCII.GetString(buffer, 0, headerEnd).Split("\r\n");
        var first = head[0].Split(' ');
        if (first.Length < 2) throw new InvalidDataException("bad request line");
        var headers = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        foreach (var line in head.Skip(1))
        {
            var i = line.IndexOf(':');
            if (i > 0) headers[line[..i].Trim().ToLowerInvariant()] = line[(i + 1)..].Trim();
        }
        var length = headers.TryGetValue("content-length", out var cl) && int.TryParse(cl, out var len) ? len : 0;
        if (length < 0 || length > ApiRequestValidator.MaxBodyBytes) throw new InvalidDataException("body too large");
        var bodyStart = headerEnd + 4;
        while (read - bodyStart < length)
        {
            var n = await stream.ReadAsync(buffer.AsMemory(read, buffer.Length - read), ct);
            if (n == 0) throw new InvalidDataException("connection closed");
            read += n;
        }
        var body = Encoding.UTF8.GetString(buffer, bodyStart, length);
        var path = first[1].Split('?')[0];
        return (first[0].ToUpperInvariant(), path, headers, body);
    }

    private static async Task Write(NetworkStream stream, int status, JsonObject json, CancellationToken ct)
    {
        var body = Encoding.UTF8.GetBytes(json.ToJsonString());
        var reason = status switch { 200 => "OK", 202 => "Accepted", 400 => "Bad Request", 401 => "Unauthorized", 403 => "Forbidden", 404 => "Not Found", 405 => "Method Not Allowed", 409 => "Conflict", 413 => "Payload Too Large", 429 => "Too Many Requests", _ => "Error" };
        var head = $"HTTP/1.1 {status} {reason}\r\nContent-Type: application/json\r\nContent-Length: {body.Length}\r\nConnection: close\r\n\r\n";
        await stream.WriteAsync(Encoding.ASCII.GetBytes(head), ct);
        await stream.WriteAsync(body, ct);
        await stream.FlushAsync(ct);
    }

    private static int IndexOf(byte[] data, int length, ReadOnlySpan<byte> pattern) => data.AsSpan(0, length).IndexOf(pattern);
}
