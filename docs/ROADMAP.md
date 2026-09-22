# Roadmap, Phase 1 test checklist, and known limitations

## Phase 1 — status: built, needs a real-PC test

**Verified automatically**
- 100+ unit tests: session rules (debounce, title split, cosmetic titles, idle inside
  sessions, lock/sleep/gap, returns, crash recovery), idle detector, privacy filter,
  sensitive-field detector, URL sanitizer, config loading, normalizer, dedup, SQLite
  store (upload status, retries, retention, fallback, reader while writing), export
  file layout, process tracking, collector isolation, full runtime start/stop/export.
- All projects compile, and `MPPWatcher.exe` publishes as one self-contained file.
- CI (Windows job) runs the real exe for 15 s as a smoke test.

**Not yet verified — needs you on a real Windows PC.** This code was written and
tested on a build server; nothing here assumes more than what plain Win32 gives.
Please go through this list and report what you see:

| # | Test | Expected |
|---|---|---|
| 1 | Install with the script, sign out and in | Tray icon appears without doing anything |
| 2 | Open the live viewer, switch Chrome → Excel → Photoshop | One `app_session_start` per switch within ~1–2 s; `app_session_end` shows duration and "switched to …" |
| 3 | Alt+Tab quickly through several windows | No sessions for windows passed through for < 1 s |
| 4 | In Chrome, open Keepa, then an Amazon product page, then switch tabs | New session per page/tab; product title visible in `window_title` |
| 5 | Gmail with changing unread count | No new session just because `(3)` became `(4)` |
| 6 | Leave the PC for 6 minutes (idle timeout 5) | `idle_start` back-dated to your last input; `idle_end` when you return; session `idle_seconds` ≈ 6 min |
| 7 | Win+L, wait, unlock | `app_session_end` (workstation_locked), `workstation_locked`, `workstation_unlocked` with `locked_seconds` |
| 8 | Sleep and wake the PC | `system_suspend`, `system_resume` (or `activity_gap` if Windows gave no notice) |
| 9 | Open KeePass (or add Notepad to `blocked_applications`) | Session shows `[excluded]`; previous session says "switched to [excluded]" |
| 10 | Run `python some_script.py` in a terminal | `process_started` / `process_exited` for python |
| 11 | Multiple monitors: move a window between screens | `monitor` in `app_session_start` names the screen |
| 12 | Kill `MPPWatcher.exe` in Task Manager, wait ≤ 5 min | Watcher restarts; the killed session ends with `watcher_crash_recovered` |
| 13 | Run as a standard (non-admin) employee account | Everything above works the same |
| 14 | A full workday | Task Manager: memory well under 200 MB, CPU ~0% while idle; heartbeat `memory_mb` confirms |
| 15 | Tray → Export logs now | Hourly `.jsonl` files under the export folder |

## Phase 1 known limitations

- **Browser URLs are not captured yet.** In Phase 1 only the window title
  (= current tab's page title) is recorded. URL/domain via UI Automation is Phase 3.
- **Titles are what the app shows.** Photoshop, InDesign and Excel sometimes show the
  document in the title and sometimes not (depends on version/settings). Document
  context via UI Automation is Phase 2/4.
- **Background tabs/windows are not tracked** — only the foreground window. Background
  programs are seen only as processes.
- **Process start/exit is found by a scan every 15 s**, so exit times are up to 15 s late
  and very short-lived programs (< 15 s) can be missed. No command lines.
- **Idle starts are back-dated to the last input.** If the foreground window changed on its
  own during that time (a pop-up), the previous session's idle share can be slightly
  under-counted.
- **Crash restart relies on the scheduled task's 5-minute re-check** until the Phase 5
  watchdog service. A crash can therefore lose up to 5 minutes of tracking (the open
  session itself is recovered from the checkpoint, ≤ 30 s approximate end time).
- **Remote Desktop / Fast User Switching**: each signed-in user gets their own watcher.
  Disconnect is treated like lock. Not yet tested.
- **Export is at-least-once**; a crash exactly between writing a file and marking events
  uploaded can duplicate lines. De-duplicate by `event_id`.
- **An employee with local admin rights could stop or remove the watcher.** Tamper
  resistance (service watchdog, protected folders) is a Phase 5 topic.
- **Not code-signed yet.** SmartScreen/antivirus may warn about an unsigned exe that uses
  window hooks. Plan a code-signing certificate before wide rollout.

## Next phases

**Phase 2 – UI Automation**
- UI Automation collector using focus-changed and invoke/selection/value-changed events
  (event-driven, no tree dumps), with per-app throttling.
- `ui_field_value`, `ui_action` (Save/Publish/Upload/Import/Export/Search/Download/Print),
  `ui_focus` events; `blocked_controls`; sensitive-field filter (already built) on every value.
- **Diagnostic inspector** (`MPPWatcher.exe --inspect`): hover/select any element and see
  app, process, control type, name, value, automation id, patterns, "sensitive?" and
  "would MPP Watcher log it?".
- Report what Windows really exposes in Chrome, Edge, Photoshop, InDesign and Excel before
  enabling broadly.

**Phase 3 – Browser context** (no extension)
- Address bar value via UI Automation → sanitized URL, domain, page title.
- Site profiles for amazon.com, Seller Central (incl. Search Query Performance),
  Keepa, Etsy, Shopify admin, Google Sheets/Drive, Gmail, ChatGPT: ASIN / SKU / listing ID
  extraction from URL + visible text, page type, editor section, Save/Publish.

**Phase 4 – Files and business apps**
- File system watcher on configured work folders (created/saved/renamed/moved/deleted),
  associated app when known, `blocked_folders`.
- Photoshop / InDesign / Excel document context; print jobs (Windows print spooler events);
  downloads (browser download folder + Seller Central export context).

**Phase 5 – Integration and deployment**
- Local authenticated event API for Tampermonkey/scripts (`automation_run` etc.), e.g.
  `http://127.0.0.1:<port>` with a per-install secret and HMAC.
- `GoogleDriveUploader` behind `ILogUploader`.
- `MPPWatcherSetup.exe` (Inno Setup or WiX): install/upgrade/uninstall, Add/Remove Programs,
  config preserved, watchdog Windows service, code signing.
