using System.Text.RegularExpressions;
using Interop.UIAutomationClient;
using MppWatcher.Core.Activity;
using MppWatcher.Core.Browser;
using MppWatcher.Core.Collectors;
using MppWatcher.Core.Diagnostics;
using MppWatcher.Core.Events;
using MppWatcher.Core.Privacy;
using MppWatcher.Windows.Interop;

namespace MppWatcher.Windows.Ui;

/// <summary>
/// Phase 3: which web page is open in the front browser window — without a browser extension.
/// Reads the browser's address bar through Windows UI Automation (only when the person is not
/// typing in it), sanitizes the URL, works out site facts (ASIN, SKU, listing id, ...) with
/// <see cref="SiteProfiles"/>, and on business sites also reads the page's headings.
/// Emits browser_page when the page changes and shares the page with <see cref="ActivityContext"/>
/// so other events get url/domain/page facts too.
/// </summary>
public sealed class BrowserContextCollector : ICollector
{
    private const int PropName = 30005, PropControlType = 30003, PropClassName = 30012, PropAutomationId = 30011, PropHeadingLevel = 30173;
    private const int ControlEdit = 50004, ControlDocument = 50030, HeadingNone = 80050;

    private readonly ActivityContext _activity;
    private readonly ProcessInfoCache _processes = new();
    private readonly Dictionary<long, IUIAutomationElement> _addressBars = new();
    private readonly UrlSanitizer _defaultSanitizer = new();
    private CollectorContext? _ctx;
    private UiaClient? _uia;
    private Thread? _thread;
    private CancellationTokenSource? _cts;
    private (long Hwnd, string Title, string? Url, DateTimeOffset At) _last;
    private long _pagesLogged, _reads, _noAddressBar, _errors;

    public BrowserContextCollector(ActivityContext activity) => _activity = activity;

    public string Name => "browser";
    public string Version => "1.0.0";

    public void Start(CollectorContext context)
    {
        _ctx = context;
        _cts = new CancellationTokenSource();
        var ready = new ManualResetEventSlim();
        Exception? error = null;
        _thread = new Thread(() =>
        {
            try { _uia = new UiaClient(_processes); }
            catch (Exception e) { error = e; }
            ready.Set();
            if (error is null) Loop(_cts.Token);
        })
        { Name = "MPP browser context", IsBackground = true };
        _thread.SetApartmentState(ApartmentState.MTA);
        _thread.Start();
        ready.Wait(TimeSpan.FromSeconds(15));
        if (error is not null) throw new InvalidOperationException("UI Automation is not available", error);
    }

    public void Stop(string reason)
    {
        _cts?.Cancel();
        _thread?.Join(TimeSpan.FromSeconds(5));
    }

    public IReadOnlyDictionary<string, object> GetStats() => new Dictionary<string, object>
    {
        ["pages_logged"] = _pagesLogged, ["address_bar_reads"] = _reads, ["address_bar_not_found"] = _noAddressBar, ["errors"] = _errors,
    };

    private void Loop(CancellationToken ct)
    {
        while (!ct.IsCancellationRequested)
        {
            try { Check(); }
            catch (Exception e)
            {
                if (Interlocked.Increment(ref _errors) <= 5) _ctx!.Log.Warn(Name, "Browser check failed", e);
            }
            ct.WaitHandle.WaitOne(_ctx!.Config.Current.Collectors.Browser.PollMs);
        }
    }

    private void Check()
    {
        var cfg = _ctx!.Config.Current;
        var hwnd = NativeMethods.GetForegroundWindow();
        if (hwnd == IntPtr.Zero) return;
        NativeMethods.GetWindowThreadProcessId(hwnd, out var pidRaw);
        var pid = (int)pidRaw;
        var proc = _processes.Get(pid);
        if (!cfg.Collectors.Browser.Browsers.Any(b => string.Equals(b, proc.Name, StringComparison.OrdinalIgnoreCase))) return;

        var title = NativeMethods.GetWindowTitle(hwnd);
        var now = _ctx.Clock.Now;
        // Re-read when the window or title changed, and every 15 s anyway (some pages keep their title).
        if (_last.Hwnd == hwnd.ToInt64() && _last.Title == title && now - _last.At < TimeSpan.FromSeconds(15)) return;

        var bar = AddressBar(hwnd, proc.Name);
        if (bar is null) { _noAddressBar++; _last = (hwnd.ToInt64(), title, _last.Url, now); return; }
        if (Try(() => bar.CurrentHasKeyboardFocus) != 0) return; // person is typing in it: that text is not a page yet

        _reads++;
        var raw = _uia!.ReadValue(bar, out var gone);
        if (gone) { _addressBars.Remove(hwnd.ToInt64()); return; }
        var sanitizer = cfg.Privacy.SensitiveUrlParameters.Count == 0 ? _defaultSanitizer : new UrlSanitizer(cfg.Privacy.SensitiveUrlParameters);
        var clean = sanitizer.Sanitize(raw);
        if (clean is null) { _last = (hwnd.ToInt64(), title, null, now); return; } // new tab, settings page, file:// ...

        var sameAsBefore = _last.Hwnd == hwnd.ToInt64() && _last.Url == clean.Url && _last.Title == title;
        _last = (hwnd.ToInt64(), title, clean.Url, now);
        if (sameAsBefore) return;

        var readText = cfg.Collectors.Browser.PageTextDomains.Any(d => WildcardMatcher.IsMatch(clean.Domain, d));
        var document = Document(hwnd);
        // The page's own title as the browser exposes it; fall back to trimming the window title.
        var pageTitle = document is not null && Try(() => document.CurrentName) is { Length: > 0 } docName ? docName : BrowserTitle.PageTitle(title);
        var headings = readText && document is not null ? Headings(document, cfg.Collectors.Browser.MaxHeadings) : new List<string>();
        var info = SiteProfiles.Analyze(new Uri(clean.Url), pageTitle, headings);
        _activity.SetPage(new BrowserPage(hwnd.ToInt64(), pid, clean.Url, clean.Domain, pageTitle, title, info, now));

        var e = this.NewEvent(EventTypes.BrowserPage, now);
        e.Application = proc.ApplicationName ?? proc.Name;
        e.ProcessName = proc.Name;
        e.ProcessId = pid;
        e.WindowTitle = title;
        e.Url = clean.Url;
        e.Domain = clean.Domain;
        e.PageTitle = pageTitle;
        e.Metadata["browser"] = proc.Name;
        foreach (var (k, v) in ActivityContext.PageJson(info, compact: false)) e.Metadata[k] = v?.DeepClone();
        if (headings.Count > 0) e.Metadata["headings"] = new System.Text.Json.Nodes.JsonArray(headings.Select(h => (System.Text.Json.Nodes.JsonNode)System.Text.Json.Nodes.JsonValue.Create(h)!).ToArray());
        if (clean.WasModified) e.Metadata["url_sanitized"] = true;
        e.DedupFingerprint = hwnd.ToInt64() + "|" + clean.Url + "|" + title;
        _ctx.Sink.Emit(e);
        _pagesLogged++;
    }

    /// <summary>Finds (once per window, then cached) the address bar: Chromium omnibox or Firefox urlbar.</summary>
    private IUIAutomationElement? AddressBar(IntPtr hwnd, string browser)
    {
        var key = hwnd.ToInt64();
        if (_addressBars.TryGetValue(key, out var cached) && Try(() => cached.CurrentControlType) == ControlEdit) return cached;
        _addressBars.Remove(key);
        var uia = _uia!.Automation;
        var root = Try(() => uia.ElementFromHandle(hwnd));
        if (root is null) return null;
        var condition = browser.Equals("firefox", StringComparison.OrdinalIgnoreCase)
            ? uia.CreatePropertyCondition(PropAutomationId, "urlbar-input")
            : uia.CreateAndCondition(uia.CreatePropertyCondition(PropControlType, ControlEdit), uia.CreatePropertyCondition(PropClassName, "OmniboxViewViews"));
        var bar = Try(() => root.FindFirst(TreeScope.TreeScope_Descendants, condition));
        if (bar is not null)
        {
            if (_addressBars.Count > 20) _addressBars.Clear();
            _addressBars[key] = bar;
        }
        return bar;
    }

    /// <summary>Up to N headings (h1–h3 style) from the page content. Only called on business sites.</summary>
    private IUIAutomationElement? Document(IntPtr hwnd)
    {
        var uia = _uia!.Automation;
        var root = Try(() => uia.ElementFromHandle(hwnd));
        return root is null ? null : Try(() => root.FindFirst(TreeScope.TreeScope_Descendants, uia.CreatePropertyCondition(PropControlType, ControlDocument)));
    }

    private List<string> Headings(IUIAutomationElement doc, int max)
    {
        var list = new List<string>();
        if (max <= 0) return list;
        var uia = _uia!.Automation;
        var cond = uia.CreateNotCondition(uia.CreatePropertyCondition(PropHeadingLevel, HeadingNone));
        var found = Try(() => doc.FindAll(TreeScope.TreeScope_Descendants, cond));
        if (found is null) return list;
        var n = Try(() => found.Length);
        for (var i = 0; i < n && list.Count < max; i++)
        {
            var text = Try(() => found.GetElement(i).CurrentName);
            if (string.IsNullOrWhiteSpace(text)) continue;
            text = Regex.Replace(text, @"\s+", " ").Trim();
            if (text.Length > 150) text = text[..150] + "…";
            if (!list.Contains(text)) list.Add(text);
        }
        return list;
    }

    private static T? Try<T>(Func<T> f)
    {
        try { return f(); }
        catch (System.Runtime.InteropServices.COMException) { return default; }
        catch (InvalidCastException) { return default; }
        catch (UnauthorizedAccessException) { return default; }
    }
}
