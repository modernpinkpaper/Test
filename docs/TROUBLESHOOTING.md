# Troubleshooting

First look at the diagnostics log: `%LOCALAPPDATA%\MPP Watcher\logs\diagnostics-YYYY-MM-DD.log`
(tray → **Open diagnostic logs**). Set `"debug_mode": true` for more detail.

| Problem | What to check |
|---|---|
| No tray icon | Task Scheduler → "MPP Watcher" → History / Last Run Result. Is `show_tray_icon` false? Is `MPPWatcher.exe` in Task Manager → Details? |
| Watcher not starting at logon | Task exists? Run `Start-ScheduledTask "MPP Watcher"`. Check the task's user group is "Users". |
| Viewer says "Watcher NOT running" | The agent is not running in *this* Windows session. Start it from the Start Menu task or sign out/in. |
| Viewer says "Waiting for database" | The watcher has not written yet, or runs with a different `data_folder`/`--data`. |
| No `app_session_*` events | Windows may be blocking foreground info (remote session without desktop, locked screen). Run `MPPWatcher.exe --smoke-test 20` and read the report. |
| Elevated (admin) apps show only a name | Normal: an un-elevated program can read the title and exe path of elevated windows, but Phase 2 UI Automation will be limited for them. |
| Store apps show as `ApplicationFrameHost` | Should be resolved automatically; if not, report the window title. |
| Sessions too short / too many | Increase `title_stable_ms`, or set `split_sessions_on_title_change` to false. |
| `activity_gap` events | The watcher was not running for > 60 s while the session was open: sleep without notice, heavy freeze, or the process was killed. |
| `end_reason: watcher_crash_recovered` | The previous run did not stop cleanly (crash, forced kill, power loss). Check the log around that time. |
| `collector_status: failed` | Error text is in the event and the log. The collector restarts automatically (max 5 times per hour). |
| Events not exported | Tray → Status: "Waiting for export". Check `export.destination_folder` exists and is writable; failed batches keep `retry_count` and retry every 15 min. |
| Config changes ignored | Log shows "Invalid config JSON"? The last good config stays active. Some settings need a restart (see CONFIGURATION.md). |
| `fallback/` folder has files | The database could not be written for a while. They are imported automatically next start. |

## Useful commands

```powershell
# self-test with a report
& "C:\Program Files\MPP Watcher\MPPWatcher.exe" --smoke-test 20 --result C:\Temp\smoke.txt

# restart the watcher for all signed-in users
Stop-ScheduledTask "MPP Watcher"; Get-Process MPPWatcher -ea 0 | Stop-Process -Force; Start-ScheduledTask "MPP Watcher"
```

The database is plain SQLite and can be opened with "DB Browser for SQLite" (read-only
while the watcher runs): `SELECT timestamp_utc, event_type, application, json FROM events ORDER BY id DESC LIMIT 100;`
