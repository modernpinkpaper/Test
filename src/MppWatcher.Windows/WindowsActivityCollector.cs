using Microsoft.Win32;
using MppWatcher.Core.Activity;
using MppWatcher.Core.Collectors;
using MppWatcher.Core.Diagnostics;
using MppWatcher.Core.Events;
using MppWatcher.Windows.Interop;
using WinFormsTimer = System.Windows.Forms.Timer;

namespace MppWatcher.Windows;

/// <summary>
/// Activity collector = application/window tracker + idle detector + lock/sleep monitor.
///
/// Runs on its own thread with a Windows message loop. It uses a foreground-change hook
/// (instant notice of app switches) plus a light poll every ~500 ms (window title, time since
/// last input, and a safety check in case a hook was missed). Everything is fed into the
/// platform-independent <see cref="ActivityTracker"/>, which decides what is a session.
///
/// It never reads keystrokes: only "how long since the last input" from GetLastInputInfo.
/// </summary>
public sealed class WindowsActivityCollector : ICollector
{
    private const int MaxConsecutiveErrors = 50;

    private readonly string _watcherRunId;
    private readonly CheckpointStore _checkpoints;
    private readonly ProcessInfoCache _processes = new();
    private readonly WindowInspector _inspector;

    private CollectorContext? _ctx;
    private ActivityTracker? _tracker;
    private Thread? _thread;
    private System.Windows.Forms.WindowsFormsSynchronizationContext? _sync;
    private readonly ManualResetEventSlim _started = new();
    private IntPtr _hook;
    private NativeMethods.WinEventDelegate? _hookDelegate; // must stay referenced or the GC frees it
    private WinFormsTimer? _timer;
    private WindowSnapshot? _lastSnapshot;
    private DateTimeOffset _lastCheckpoint;
    private int _consecutiveErrors;
    private long _ticks, _hookEvents, _errors;
    private Exception? _startError;

    // Each Start() gets a new generation. A message-loop thread whose generation is no longer current
    // (Start gave up waiting for it) must stop, so two threads never feed the same tracker.
    private readonly object _startLock = new();
    private int _generation;

    /// <summary>Tests shorten this and slow the start down to recreate a start that times out.</summary>
    internal TimeSpan StartTimeout { get; set; } = TimeSpan.FromSeconds(30);
    internal TimeSpan SlowStartForTests { get; set; }

    public WindowsActivityCollector(string watcherRunId, string checkpointPath)
    {
        _watcherRunId = watcherRunId;
        _checkpoints = new CheckpointStore(checkpointPath);
        _inspector = new WindowInspector(_processes);
    }

    public string Name => "activity";
    public string Version => "1.0.0";

    public void Start(CollectorContext context)
    {
        _ctx = context;
        _startError = null;
        _started.Reset();
        int gen;
        lock (_startLock) gen = ++_generation;
        _thread = new Thread(() => ThreadMain(gen)) { Name = "MPP activity collector", IsBackground = true };
        _thread.SetApartmentState(ApartmentState.STA);
        _thread.Start();
        if (!_started.Wait(StartTimeout))
        {
            // Retire this thread: if it starts late it sees a newer generation and exits on its own.
            lock (_startLock) _generation++;
            throw new TimeoutException("Activity collector thread did not start");
        }
        if (_startError is not null) throw new InvalidOperationException("Activity collector failed to start", _startError);

        // Subscribe from a thread-pool thread so Windows gives SystemEvents its own message thread
        // (keeps lock/sleep notices working even while our thread is busy or restarting).
        Task.Run(() =>
        {
            SystemEvents.SessionSwitch += OnSessionSwitch;
            SystemEvents.PowerModeChanged += OnPowerModeChanged;
            SystemEvents.SessionEnding += OnSessionEnding;
        }).Wait();
    }

    public void Stop(string reason)
    {
        SystemEvents.SessionSwitch -= OnSessionSwitch;
        SystemEvents.PowerModeChanged -= OnPowerModeChanged;
        SystemEvents.SessionEnding -= OnSessionEnding;

        var sync = _sync;
        if (sync is null || _thread is null) return;
        var done = new ManualResetEventSlim();
        sync.Post(_ =>
        {
            try
            {
                _timer?.Stop();
                if (_hook != IntPtr.Zero) NativeMethods.UnhookWinEvent(_hook);
                _hook = IntPtr.Zero;
                // The open session is closed properly here, so the crash checkpoint is no longer needed.
                _tracker?.Stop(_ctx!.Clock.Now, reason);
                SafeClearCheckpoint();
            }
            catch (Exception e)
            {
                _ctx?.Log.Error(Name, "Error while stopping", e);
            }
            finally
            {
                System.Windows.Forms.Application.ExitThread();
                done.Set();
            }
        }, null);
        done.Wait(TimeSpan.FromSeconds(5));
        _thread.Join(TimeSpan.FromSeconds(5));
        _thread = null;
        _sync = null;
    }

    public IReadOnlyDictionary<string, object> GetStats() => new Dictionary<string, object>
    {
        ["ticks"] = _ticks,
        ["hook_events"] = _hookEvents,
        ["errors"] = _errors,
        ["sessions_started"] = _tracker?.SessionsStarted ?? 0,
        ["is_idle"] = _tracker?.IsIdle ?? false,
    };

    private void ThreadMain(int gen)
    {
        IntPtr hook;
        NativeMethods.WinEventDelegate hookDelegate = (_, _, _, _, _, _, _) =>
        {
            _hookEvents++;
            Poll(gen, fromHook: true);
        };
        WinFormsTimer timer;
        lock (_startLock)
        {
            if (gen != _generation) return; // Start() already gave up on this thread
            try
            {
                SetUpLoop(gen, hookDelegate, out hook, out timer);
            }
            catch (Exception e)
            {
                _startError = e;
                _started.Set();
                return;
            }
            _started.Set(); // inside the lock, so a retired thread never signals a newer Start()
        }
        System.Windows.Forms.Application.Run(); // message loop until Stop() (or a newer generation) calls ExitThread
        if (hook != IntPtr.Zero) NativeMethods.UnhookWinEvent(hook);
        timer.Dispose();
        GC.KeepAlive(hookDelegate);
    }

    private void SetUpLoop(int gen, NativeMethods.WinEventDelegate hookDelegate, out IntPtr hook, out WinFormsTimer timer)
    {
        if (SlowStartForTests > TimeSpan.Zero) Thread.Sleep(SlowStartForTests);
        {
            _sync = new System.Windows.Forms.WindowsFormsSynchronizationContext();
            SynchronizationContext.SetSynchronizationContext(_sync);

            var cfg = _ctx!.Config;
            _tracker = new ActivityTracker(
                () =>
                {
                    var a = cfg.Current.Collectors.Activity;
                    return new ActivityTrackerOptions
                    {
                        ForegroundStable = TimeSpan.FromMilliseconds(a.ForegroundStableMs),
                        TitleStable = TimeSpan.FromMilliseconds(a.TitleStableMs),
                        SplitOnTitleChange = a.SplitSessionsOnTitleChange,
                        GapThreshold = TimeSpan.FromSeconds(a.GapThresholdSeconds),
                        ReturnWindow = TimeSpan.FromMinutes(a.ReturnWindowMinutes),
                    };
                },
                () => TimeSpan.FromSeconds(cfg.Current.IdleTimeoutSeconds),
                _ctx.Sink.Emit, Name, Version);

            RecoverCheckpoint();

            _hookDelegate = hookDelegate;
            _hook = hook = NativeMethods.SetWinEventHook(NativeMethods.EVENT_SYSTEM_FOREGROUND, NativeMethods.EVENT_SYSTEM_FOREGROUND,
                IntPtr.Zero, hookDelegate, 0, 0, NativeMethods.WINEVENT_OUTOFCONTEXT | NativeMethods.WINEVENT_SKIPOWNPROCESS);
            if (hook == IntPtr.Zero) _ctx.Log.Warn(Name, "Foreground hook unavailable; using polling only");

            _timer = timer = new WinFormsTimer { Interval = cfg.Current.Collectors.Activity.PollIntervalMs };
            timer.Tick += (_, _) => Poll(gen, fromHook: false);
            timer.Start();
            Poll(gen, fromHook: false);
        }
    }

    private void Poll(int gen, bool fromHook)
    {
        if (gen != Volatile.Read(ref _generation))
        {
            // A newer start owns the collector now: leave the shared tracker alone and end this thread.
            System.Windows.Forms.Application.ExitThread();
            return;
        }
        var ctx = _ctx;
        var tracker = _tracker;
        if (ctx is null || tracker is null) return;
        try
        {
            var now = ctx.Clock.Now;
            if (!fromHook)
            {
                _ticks++;
                tracker.Tick(now);
            }

            var hwnd = NativeMethods.GetForegroundWindow();
            WindowSnapshot? snapshot;
            if (_lastSnapshot is not null && _lastSnapshot.Handle == hwnd.ToInt64())
            {
                snapshot = WindowInspector.Refresh(_lastSnapshot);
            }
            else
            {
                snapshot = _inspector.Inspect(hwnd);
            }
            _lastSnapshot = snapshot;
            // The lock/sign-in screen is not work; lock events arrive separately via SystemEvents.
            if (snapshot is not null && IsLockScreen(snapshot.ProcessName)) snapshot = null;
            tracker.ObserveForeground(snapshot, now);

            if (!fromHook)
            {
                tracker.ObserveInput(NativeMethods.TimeSinceLastInput(), now);
                SaveCheckpointIfDue(now);
            }
            _consecutiveErrors = 0;
        }
        catch (Exception e)
        {
            _errors++;
            if (++_consecutiveErrors == 1) ctx.Log.Warn(Name, "Poll failed", e);
            if (_consecutiveErrors >= MaxConsecutiveErrors)
            {
                _consecutiveErrors = 0;
                // Let the host restart us from a clean state.
                ThreadPool.QueueUserWorkItem(_ => ctx.ReportFailure(this, e));
            }
        }
    }

    private static bool IsLockScreen(string processName) =>
        processName.Equals("LockApp", StringComparison.OrdinalIgnoreCase) || processName.Equals("LogonUI", StringComparison.OrdinalIgnoreCase);

    private void SaveCheckpointIfDue(DateTimeOffset now)
    {
        var interval = TimeSpan.FromSeconds(_ctx!.Config.Current.Collectors.Activity.CheckpointSeconds);
        if (now - _lastCheckpoint < interval) return;
        _lastCheckpoint = now;
        try
        {
            _checkpoints.Save(_tracker!.CreateCheckpoint(now, _watcherRunId));
        }
        catch (Exception e)
        {
            _ctx.Log.Warn(Name, "Could not save session checkpoint", e);
        }
    }

    private void RecoverCheckpoint()
    {
        try
        {
            var cp = _checkpoints.Load();
            if (cp is null) return;
            _tracker!.EmitRecoveredSessionEnd(cp);
            _checkpoints.Clear();
            _ctx!.Log.Warn(Name, $"Closed session {cp.SessionId} left open by a previous run that did not stop cleanly");
        }
        catch (Exception e)
        {
            _ctx!.Log.Warn(Name, "Could not read session checkpoint", e);
        }
    }

    private void SafeClearCheckpoint()
    {
        try { _checkpoints.Clear(); } catch (Exception e) { _ctx?.Log.Warn(Name, "Could not delete checkpoint", e); }
    }

    // ---- Windows session / power notifications (arrive on the SystemEvents thread) ----

    private void OnSessionSwitch(object? sender, SessionSwitchEventArgs e)
    {
        Post(now =>
        {
            switch (e.Reason)
            {
                case SessionSwitchReason.SessionLock:
                case SessionSwitchReason.ConsoleDisconnect:
                case SessionSwitchReason.RemoteDisconnect:
                    _tracker!.OnLocked(now);
                    break;
                case SessionSwitchReason.SessionUnlock:
                case SessionSwitchReason.ConsoleConnect:
                case SessionSwitchReason.RemoteConnect:
                    if (_tracker!.IsPaused) _tracker.OnUnlocked(now);
                    break;
            }
        });
    }

    private void OnPowerModeChanged(object? sender, PowerModeChangedEventArgs e)
    {
        if (e.Mode == PowerModes.Suspend)
        {
            // Must finish before the PC sleeps: run synchronously and save a fresh checkpoint.
            Send(now =>
            {
                _tracker!.OnSuspend(now);
                SafeClearCheckpoint();
            });
        }
        else if (e.Mode == PowerModes.Resume)
        {
            Post(now => _tracker!.OnResume(now));
        }
    }

    private void OnSessionEnding(object? sender, SessionEndingEventArgs e)
    {
        var kind = e.Reason == Microsoft.Win32.SessionEndReasons.SystemShutdown ? "shutdown" : "logoff";
        Send(now => _tracker!.OnSessionEnding(now, kind));
    }

    private void Post(Action<DateTimeOffset> action) => _sync?.Post(_ => Guarded(action), null);

    private void Send(Action<DateTimeOffset> action)
    {
        var sync = _sync;
        if (sync is null) return;
        var done = new ManualResetEventSlim();
        sync.Post(_ => { try { Guarded(action); } finally { done.Set(); } }, null);
        done.Wait(TimeSpan.FromSeconds(3));
    }

    private void Guarded(Action<DateTimeOffset> action)
    {
        try
        {
            if (_tracker is not null && _ctx is not null) action(_ctx.Clock.Now);
        }
        catch (Exception ex)
        {
            _ctx?.Log.Error(Name, "Session/power event handling failed", ex);
        }
    }
}
