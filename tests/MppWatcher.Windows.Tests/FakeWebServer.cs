using System.Net;
using System.Net.Security;
using System.Net.Sockets;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text;

namespace MppWatcher.Windows.Tests;

/// <summary>
/// Tiny HTTPS server on 127.0.0.1 that answers for ANY host name. Edge is started with
/// --host-resolver-rules pointing amazon.com, keepa.com, etsy.com, ... here, so the watcher sees
/// the real site addresses while the pages are simple local look-alikes. No internet needed.
/// </summary>
internal sealed class FakeWebServer : IDisposable
{
    private readonly TcpListener _listener = new(IPAddress.Loopback, 0);
    private readonly X509Certificate2 _cert;
    private readonly Func<string, string, string> _page; // (host, pathAndQuery) -> html
    private readonly CancellationTokenSource _cts = new();

    public FakeWebServer(Func<string, string, string> page)
    {
        _page = page;
        using var rsa = RSA.Create(2048);
        var req = new CertificateRequest("CN=mpp-test", rsa, HashAlgorithmName.SHA256, RSASignaturePadding.Pkcs1);
        var san = new SubjectAlternativeNameBuilder();
        san.AddDnsName("*.amazon.com"); san.AddDnsName("keepa.com"); san.AddDnsName("*.etsy.com"); san.AddDnsName("admin.shopify.com");
        req.CertificateExtensions.Add(san.Build());
        using var temp = req.CreateSelfSigned(DateTimeOffset.Now.AddDays(-1), DateTimeOffset.Now.AddDays(1));
        _cert = new X509Certificate2(temp.Export(X509ContentType.Pfx)); // exportable key for SslStream on Windows
        _listener.Start();
        _ = Task.Run(AcceptLoop);
    }

    public int Port => ((IPEndPoint)_listener.LocalEndpoint).Port;
    public List<string> Requests { get; } = new();

    private async Task AcceptLoop()
    {
        while (!_cts.IsCancellationRequested)
        {
            TcpClient client;
            try { client = await _listener.AcceptTcpClientAsync(_cts.Token); }
            catch { return; }
            _ = Task.Run(() => Handle(client));
        }
    }

    private async Task Handle(TcpClient client)
    {
        using (client)
        {
            try
            {
                using var ssl = new SslStream(client.GetStream(), false);
                await ssl.AuthenticateAsServerAsync(_cert);
                using var reader = new StreamReader(ssl, Encoding.ASCII, false, 8192, leaveOpen: true);
                var requestLine = await reader.ReadLineAsync() ?? "";
                string? host = null;
                string? line;
                while (!string.IsNullOrEmpty(line = await reader.ReadLineAsync()))
                    if (line.StartsWith("Host:", StringComparison.OrdinalIgnoreCase)) host = line[5..].Trim().Split(':')[0];
                var path = requestLine.Split(' ').ElementAtOrDefault(1) ?? "/";
                lock (Requests) Requests.Add($"{host}{path}");
                var body = path.StartsWith("/favicon", StringComparison.Ordinal) ? "" : _page(host ?? "", path);
                var bytes = Encoding.UTF8.GetBytes(body);
                var head = $"HTTP/1.1 {(body.Length == 0 ? "404 Not Found" : "200 OK")}\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: {bytes.Length}\r\nConnection: close\r\n\r\n";
                await ssl.WriteAsync(Encoding.ASCII.GetBytes(head));
                await ssl.WriteAsync(bytes);
                await ssl.FlushAsync();
            }
            catch
            {
                // browsers open speculative connections that close early; ignore
            }
        }
    }

    public void Dispose()
    {
        _cts.Cancel();
        _listener.Stop();
        _cert.Dispose();
    }
}
