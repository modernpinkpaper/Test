# Architecture

## Big picture

```
 ┌──────────────────────── MTLog.exe (runs as the signed-in employee) ───────────────────────┐
 │                                                                                                 │
 │  Collectors (each isolated)            Pipeline (one path for every event)        Storage       │
 │  ┌──────────────────────────┐      ┌───────────────────────────────────────┐   ┌────────────┐ │
 │  │ activity                 │      │ 1 normalizer  (ids, times, employee)  │   │ SQLite     │ │
 │  │  • window tracker (hook) │─────▶│ 2 privacy     (block lists, URL clean)│──▶│ events.db  │ │
 │  │  • idle detector         │      │ 3 dedup       (drop repeats)          │   │ (WAL)      │ │
 │  │  • lock / sleep / logoff │      │ 4 queue → background batch writer     │   └─────┬──────┘ │
 │  ├──────────────────────────┤      └───────────────────────────────────────┘         │        │
 │  │ process                  │─────▶                     │ if DB fails                 │        │
 │  ├──────────────────────────┤                           ▼                             ▼        │
 │  │ (Phase 2+) UI Automation,│                    fallback/*.jsonl            export timer     │
 │  │ browser, files, print... │                    (re-imported)          ILogUploader (local   │
 │  └──────────────────────────┘                                            folder; Drive next)  │
 │  Tray icon · heartbeat · retention · diagnostics log                                           │
 └─────────────────────────────────────────────────────────────────────────────────────────────────┘
          ▲ started at logon by Task Scheduler              MTLog.exe --viewer reads events.db
```

## Why a per-user program and not only a Windows service

A Windows service runs in "session 0". Windows isolates session 0 from the user's
desktop, so a service **cannot** see the foreground window, read UI Automation, or
get the user's last-input time. Everything this project needs to observe only exists
inside the employee's own session. So:

- The **collector runs as a normal program in the user's session**, started at logon by
  Task Scheduler (no BAT file, no user action). It runs un-elevated as that user.
- A small Windows **service is the watchdog** (`MTLog.exe --service`, LocalSystem): every
  30 s it checks each signed-in user with an active desktop and, if their watcher is not running,
  starts it in that user's session (WTSQueryUserToken + CreateProcessAsUser). The logon task also
  re-checks every 5 minutes. The service records nothing itself.

## Why C#/.NET 8

- Direct access to Win32 (window hooks, `GetLastInputInfo`) and, for Phase 2,
  the managed UI Automation API — no bridges.
- One self-contained `MTLog.exe` (no .NET install needed on employee PCs).
- `Microsoft.Data.Sqlite` for a reliable local database.
- Most logic is plain .NET and is unit-tested on any OS.

## Projects

| Project | Runs on | Contents |
|---|---|---|
| `src/MppWatcher.Core` | any OS | event model, config, privacy, session tracker, idle detector, process tracker, pipeline, SQLite store, export, runtime wiring |
| `src/MppWatcher.Windows` | Windows | Win32 interop, `WindowsActivityCollector`, `WindowsProcessSource` |
| `src/MppWatcher.App` | Windows | `MTLog.exe`: tray agent, live viewer, smoke test |
| `tests/MppWatcher.Core.Tests` | any OS | 100+ unit tests |
| `installer/` | Windows | install / uninstall PowerShell (Phase 1) |

## The 12 components from the brief

| # | Component | Where |
|---|---|---|
| 1 | Activity collector | `Windows/WindowsActivityCollector.cs` + `Core/Activity/ActivityTracker.cs` |
| 2 | UI Automation collector | Phase 2 |
| 3 | Application/window tracker | `Windows/WindowInspector.cs`, `ProcessInfoCache.cs`, foreground hook in the activity collector |
| 4 | Browser/window context | Phase 3 (`Core/Privacy/UrlSanitizer.cs` ready) |
| 5 | File activity | Phase 4 |
| 6 | Process activity | `Core/Processes/*`, `Windows/WindowsProcessSource.cs` |
| 7 | Idle/active detector | `Core/Activity/IdleDetector.cs` |
| 8 | Event normalizer | `Core/Pipeline/EventNormalizer.cs`, `DuplicateSuppressor.cs`, `EventPipeline.cs` |
| 9 | Local storage | `Core/Storage/SqliteEventStore.cs` |
| 10 | Upload/export | `Core/Export/ILogUploader.cs`, `LocalFolderUploader.cs`, `ExportService.cs` |
| 11 | Configuration | `Core/Configuration/*` |
| 12 | Diagnostics/logging | `Core/Diagnostics/DiagnosticLog.cs`, heartbeat + `collector_status` events |

## How the activity collector works

- It runs on **its own thread with a Windows message loop**.
- A `SetWinEventHook(EVENT_SYSTEM_FOREGROUND)` hook tells it at once when the user
  switches windows. This hook fires rarely, so it costs almost nothing.
- A **light poll every 500 ms** reads: the foreground window handle, its title
  (`GetWindowText`, cheap and cannot hang), and time since last input
  (`GetLastInputInfo`). It also catches anything the hook missed.
  We deliberately do **not** hook every title/name change in the system — Chrome alone
  fires thousands of those — so CPU stays low.
- Process name/path/friendly name are looked up only when the window changes, then cached.
- Everything is handed to `ActivityTracker` (pure logic, fully unit tested), which decides:
  - a new window counts only after **1 s** in front (Alt+Tab flicker ignored);
  - a real title change that lasts **2 s** starts a new session (new browser page/tab,
    new document); cosmetic changes such as `(3) Inbox` → `(4) Inbox` or a Photoshop zoom
    level do not;
  - idle time is counted *inside* the session (`active_seconds` + `idle_seconds`);
  - lock, sleep, sign-out end the session; unlock/wake start a new one;
  - if the watcher itself did not run for over 60 s (e.g. sleep without notice), the
    session is closed at the last moment it was seen and an `activity_gap` is written;
  - returning to a window seen in the last 4 hours is marked (`returning_to_session_id`).
- Every 30 s the open session is saved to `open-session.json`. If the watcher is killed,
  the next start closes that session with `end_reason = watcher_crash_recovered`.

## Reliability rules

- `Emit()` never blocks and never throws. Writing happens on a background thread in
  batches (one transaction per batch).
- Database write fails → 4 retries with back-off → events saved to `fallback/*.jsonl`
  → imported back on the next start. Events are not lost.
- A collector that throws is stopped, reported (`collector_status` event + log), and
  restarted with back-off (max 5 per hour). Other collectors keep running.
- Export marks events "uploaded" only after the uploader succeeded. Failures increase
  `retry_count`; events stay pending (never deleted) until uploaded.
- Retention deletes only **uploaded** events older than N days.
- Single instance per user session (named mutex).

## Adding a collector (Phase 2+)

1. Implement `ICollector` (`Name`, `Version`, `Start`, `Stop`, optional `GetStats`).
2. Create events with `this.NewEvent(type, time)`, put details in `Metadata`, set
   `DedupFingerprint` for state-style events, and call `context.Sink.Emit(e)`.
3. Add an `enabled` switch under `collectors` in `WatcherConfig`.
4. Register it in `src/MppWatcher.App/WatcherFactory.cs`.
5. Document new event types in `docs/EVENT_SCHEMA.md`.
