using System.Collections.Concurrent;
using System.Runtime.InteropServices;
using Interop.UIAutomationClient;
using MppWatcher.Core.Collectors;
using MppWatcher.Core.Diagnostics;
using MppWatcher.Core.Ui;
using MppWatcher.Windows.Interop;

namespace MppWatcher.Windows.Ui;

/// <summary>
/// Phase 2 collector: records finished field values (ui_field_value) and clicks on named
/// controls (ui_action) using Windows UI Automation — no keystrokes, no coordinates, no tree dumps.
///
/// - Focus changes come from a UI Automation focus event (event-driven).
/// - While a text field has focus its value is re-read every ~500 ms (one property read).
/// - A click is only used to ask "which control is at this point?".
/// - Every value goes through <see cref="UiCapturePolicy"/>; password fields are never read.
/// All UI Automation calls happen on one background worker thread.
/// </summary>
public sealed class UiAutomationCollector : ICollector
{
    private readonly BlockingCollection<Action> _work = new(new ConcurrentQueue<Action>(), 1000);
    private readonly int _ownPid;
    private CollectorContext? _ctx;
    private UiCapturePolicy? _policy;
    private FocusedFieldTracker? _tracker;
    private UiaClient? _uia;
    private FocusHandler? _focusHandler;
    private MouseClickListener? _clicks;
    private Thread? _worker;
    private CancellationTokenSource? _cts;
    private IUIAutomationElement? _trackedElement;
    private (string? RuntimeId, DateTimeOffset At) _lastAction;
    private string? _lastFocusRuntimeId;
    private DateTimeOffset _lastFocusCheck;
    private long _focusEvents, _clicksSeen, _fieldsLogged, _actionsLogged, _refusedSensitive, _errors, _dropped;

    public UiAutomationCollector() : this(ignoreOwnProcess: true) { }

    /// <summary>Tests host their sample windows in the test process, so they turn the self-filter off.</summary>
    internal UiAutomationCollector(bool ignoreOwnProcess) => _ownPid = ignoreOwnProcess ? Environment.ProcessId : -1;

    public string Name => UiEventFactory.CollectorName;
    public string Version => UiEventFactory.CollectorVersion;

    public void Start(CollectorContext context)
    {
        _ctx = context;
        _policy = new UiCapturePolicy(() => context.Config.Current);
        _tracker = new FocusedFieldTracker(() => TimeSpan.FromSeconds(context.Config.Current.Collectors.UiAutomation.ValueSettleSeconds));
        _cts = new CancellationTokenSource();

        var started = new ManualResetEventSlim();
        Exception? startError = null;
        _worker = new Thread(() =>
        {
            try
            {
                _uia = new UiaClient();
                _focusHandler = new FocusHandler(el => Enqueue(() => OnFocus(el)));
                _uia.Automation.AddFocusChangedEventHandler(null!, _focusHandler);
            }
            catch (Exception e)
            {
                startError = e;
            }
            started.Set();
            if (startError is null) WorkLoop(_cts.Token);
        })
        { Name = "MPP UI Automation worker", IsBackground = true };
        _worker.SetApartmentState(ApartmentState.MTA);
        _worker.Start();
        started.Wait(TimeSpan.FromSeconds(15));
        if (startError is not null) throw new InvalidOperationException("UI Automation is not available", startError);

        if (context.Config.Current.Collectors.UiAutomation.CaptureActions)
        {
            _clicks = new MouseClickListener((x, y) => Enqueue(() => OnClick(x, y)));
            if (!_clicks.Start()) context.Log.Warn(Name, "Mouse click listener unavailable; ui_action events will not be recorded");
        }
    }

    public void Stop(string reason)
    {
        _clicks?.Dispose();
        _clicks = null;
        var done = new ManualResetEventSlim();
        Enqueue(() =>
        {
            try
            {
                RefreshTrackedValue(_ctx!.Clock.Now);
                Commit(_tracker?.Flush());
                if (_focusHandler is not null) _uia?.Automation.RemoveFocusChangedEventHandler(_focusHandler);
            }
            catch (Exception e) { _ctx?.Log.Warn(Name, "Error while removing UI Automation handler", e); }
            finally { done.Set(); }
        });
        done.Wait(TimeSpan.FromSeconds(5));
        _cts?.Cancel();
        _worker?.Join(TimeSpan.FromSeconds(5));
    }

    public IReadOnlyDictionary<string, object> GetStats() => new Dictionary<string, object>
    {
        ["focus_events"] = _focusEvents, ["clicks_seen"] = _clicksSeen, ["fields_logged"] = _fieldsLogged,
        ["actions_logged"] = _actionsLogged, ["sensitive_refused"] = _refusedSensitive, ["errors"] = _errors, ["queue_dropped"] = _dropped,
    };

    private void Enqueue(Action a)
    {
        if (!_work.TryAdd(a)) Interlocked.Increment(ref _dropped); // never block Windows' callback threads
    }

    private void WorkLoop(CancellationToken ct)
    {
        while (!ct.IsCancellationRequested)
        {
            var poll = _ctx!.Config.Current.Collectors.UiAutomation.FocusedFieldPollMs;
            try
            {
                if (_work.TryTake(out var item, poll, ct)) item();
                PollTrackedField();
                CheckFocusDirectly();
            }
            catch (OperationCanceledException) { break; }
            catch (Exception e)
            {
                if (Interlocked.Increment(ref _errors) <= 5) _ctx.Log.Warn(Name, "UI Automation work item failed", e);
            }
        }
        // Drain remaining work (e.g. the Stop item).
        while (_work.TryTake(out var rest)) { try { rest(); } catch { } }
    }

    private void OnFocus(IUIAutomationElement element) => OnFocus(element, announced: true);

    private void OnFocus(IUIAutomationElement element, bool announced)
    {
        _focusEvents++;
        var uia = _uia!;
        var pid = uia.ProcessIdOf(element);
        if (pid == _ownPid) return;
        var now = _ctx!.Clock.Now;
        RefreshTrackedValue(now); // the user may have typed the last letters a moment ago

        var info = uia.Read(element, readValue: false, detailed: false, NativeMethods.GetForegroundWindow());
        _lastFocusRuntimeId = info.RuntimeId;
        UiElementInfo? trackable = null;
        if (UiCapturePolicy.FieldControlTypes.Contains(info.ControlType))
        {
            var pre = _policy!.EvaluateField(info with { Value = "x", HasValuePattern = true });
            if (pre.Log) trackable = info with { Value = uia.ReadValue(element, out _) };
            else if (pre.IsSensitive) _refusedSensitive++;
        }
        Commit(_tracker!.OnFocus(trackable, now, initialValueKnown: announced));
        _trackedElement = trackable is null ? null : element;
    }

    /// <summary>
    /// Windows does not always announce focus (e.g. a window opens with the cursor already in
    /// its first field). Twice a second, ask which element has focus and treat a change as a
    /// focus event. Two cheap calls.
    /// </summary>
    private void CheckFocusDirectly()
    {
        var now = _ctx!.Clock.Now;
        if (now - _lastFocusCheck < TimeSpan.FromMilliseconds(500)) return;
        _lastFocusCheck = now;
        var focused = _uia!.FocusedElement();
        if (focused is null) return;
        var id = _uia.RuntimeIdOf(focused);
        if (id is null || id == _lastFocusRuntimeId) return;
        _lastFocusRuntimeId = id; // remember even if OnFocus decides to skip it (e.g. our own window)
        OnFocus(focused, announced: false);
    }

    private void PollTrackedField()
    {
        var tracked = _trackedElement;
        if (tracked is null || _tracker?.Current is null) return;
        var now = _ctx!.Clock.Now;
        var value = _uia!.ReadValue(tracked, out var gone);
        if (gone)
        {
            // The page changed under the field (e.g. search submitted): commit the last value seen.
            Commit(_tracker.Flush());
            _trackedElement = null;
            return;
        }
        _tracker.OnValue(value, now);
        Commit(_tracker.OnTick(now));
    }

    private void RefreshTrackedValue(DateTimeOffset now)
    {
        if (_trackedElement is null || _tracker?.Current is null) return;
        var value = _uia!.ReadValue(_trackedElement, out var gone);
        if (!gone) _tracker.OnValue(value, now);
    }

    private void Commit(FieldCommit? commit)
    {
        if (commit is null) return;
        var decision = _policy!.EvaluateField(commit.Element);
        if (!decision.Log)
        {
            if (decision.IsSensitive) _refusedSensitive++;
            return;
        }
        _ctx!.Sink.Emit(UiEventFactory.FieldValue(commit.Element, decision, commit.Trigger, commit.Edited, _ctx.Clock.Now));
        _fieldsLogged++;
    }

    private void OnClick(int x, int y)
    {
        _clicksSeen++;
        var uia = _uia!;
        var hit = uia.ElementFromPoint(x, y);
        if (hit is null) return;
        var target = uia.FindActionable(hit);
        if (target is null || uia.ProcessIdOf(target) == _ownPid) return;

        var type = uia.ControlTypeOf(target);
        if (type is "CheckBox" or "RadioButton") Thread.Sleep(150); // let the app apply the new state first

        var info = uia.Read(target, readValue: false, detailed: false, NativeMethods.RootWindowFromPoint(x, y));
        var now = _ctx!.Clock.Now;
        if (info.RuntimeId is not null && info.RuntimeId == _lastAction.RuntimeId && now - _lastAction.At < TimeSpan.FromSeconds(1)) return; // double click
        _lastAction = (info.RuntimeId, now);

        var decision = _policy!.EvaluateAction(info);
        if (!decision.Log) return;
        _ctx.Sink.Emit(UiEventFactory.Action(info, decision, "click", now));
        _actionsLogged++;
    }

    /// <summary>COM callback object for UI Automation focus events. Must return quickly.</summary>
    [ComVisible(true)]
    private sealed class FocusHandler : IUIAutomationFocusChangedEventHandler
    {
        private readonly Action<IUIAutomationElement> _onFocus;
        public FocusHandler(Action<IUIAutomationElement> onFocus) => _onFocus = onFocus;
        public void HandleFocusChangedEvent(IUIAutomationElement sender) => _onFocus(sender);
    }
}
