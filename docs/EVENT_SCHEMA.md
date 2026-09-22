# Event schema (schema_version 1)

Every event is one JSON object. In the database it is stored as JSON; exports are
JSON Lines (one event per line).

## Common fields (every event)

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | int | Format version. Currently `1`. |
| `event_id` | string | Unique id (32 hex chars). Use it to remove duplicates. |
| `timestamp_utc` | string | When it happened, UTC, fixed format `2026-09-22T13:31:20.500Z`. |
| `timestamp_local` | string | Same moment in the PC's local time with offset, `2026-09-22T09:31:20.500-04:00`. |
| `computer_id` | string | `computer_id` from config, else the Windows computer name. |
| `employee_id` | string | From config (per Windows user map, else default). `unassigned-<user>` if not set. |
| `windows_username` | string | `DOMAIN\user`. |
| `event_type` | string | See below. |
| `application` | string? | Friendly app name from the exe ("Google Chrome", "Adobe Photoshop 2025"). |
| `process_name` | string? | Process name without `.exe` ("chrome", "Photoshop"). |
| `process_id` | int? | Windows process id. |
| `window_title` | string? | Window title text. |
| `domain` | string? | Website domain (Phase 3). |
| `url` | string? | Sanitized URL (Phase 3). |
| `page_title` | string? | Web page title (Phase 3). |
| `session_id` | string? | The foreground session this event belongs to. |
| `task_context_id` | string? | Reserved for later analysis. Always empty for now. |
| `watcher_run_id` | string | New value each time the watcher starts. |
| `sequence` | int | Increasing counter within one run. Tie-breaker for equal timestamps. |
| `collector` | string | Which part produced it: `activity`, `process`, `watcher`. |
| `collector_version` | string | Version of that collector. |
| `metadata` | object | Event-specific details (below). |

Timestamps can be **back-dated**: e.g. a session start is the moment the window came
to the front, not the moment the watcher confirmed it; an idle start is the time of
the last input. Always sort by `timestamp_utc`, then `sequence`.

## Foreground sessions

### `app_session_start`
A window came to the front (and stayed ≥ 1 s), or its title changed meaningfully (≥ 2 s).

| metadata | |
|---|---|
| `session_start` | local ISO time |
| `foreground` | `true` |
| `executable_path` | full exe path |
| `window_class` | Win32 class name (e.g. `Chrome_WidgetWin_1`, `XLMAIN`) |
| `window_handle` | hex handle, e.g. `0x40A2E` (tells two windows of the same app apart) |
| `monitor` | e.g. `DISPLAY1 (primary)` |
| `previous_session_id` | the session that ended just before |
| `returning_to_session_id` | set if the same app + title was seen in the last 4 h |
| `seconds_since_last_visit` | with the above |

### `app_session_end`
| metadata | |
|---|---|
| `session_start`, `session_end` | local ISO times |
| `duration_seconds` | total |
| `active_seconds` | duration minus idle |
| `idle_seconds` | idle time inside this session |
| `end_reason` | `foreground_changed`, `title_changed`, `workstation_locked`, `system_suspend`, `session_ending`, `watcher_stopped`, `activity_gap`, `watcher_crash_recovered`, `collector_failed` |
| `next_application`, `next_process_name` | what came next (if known) |
| `next_window_title` | new title when the same app continued (e.g. next page) |
| `title_changes` | only if `split_sessions_on_title_change` is off |
| `recovered_from_run_id`, `end_time_is_approximate` | only for `watcher_crash_recovered` |

### `window_title_changed`
Only when `split_sessions_on_title_change` is `false`. `metadata.previous_title`.

## Idle

- `idle_start` — timestamp = last input. `metadata.idle_start`, `detected_at`, `idle_threshold_seconds`.
- `idle_end` — timestamp = first new input. `metadata.idle_start`, `idle_end`, `idle_seconds`, `end_reason` (`input_resumed`, `workstation_locked`, ...).

Only the **time** of the last keyboard/mouse input is used. No keys, no mouse positions.

## Workstation and power

| Type | metadata |
|---|---|
| `workstation_locked` | – |
| `workstation_unlocked` | `locked_seconds` |
| `system_suspend` | – |
| `system_resume` | `suspended_seconds` |
| `session_ending` | `kind`: `logoff` or `shutdown` |
| `activity_gap` | `gap_start`, `gap_end`, `gap_seconds`, `explanation` |

## Processes (background activity)

| Type | metadata |
|---|---|
| `process_inventory` | at start: `processes` = list of `{process_name, application, instances, has_window}` |
| `process_started` | `has_window`, `executable_path`, `process_start`, `running_instances`, `foreground: false` |
| `process_exited` | `run_seconds`, `exit_time_is_approximate` (found at the next 15 s scan) |

Noise such as `svchost` is ignored (configurable). Apps with many helper processes
(Chrome, Adobe) are collapsed: one start when the first appears, one exit when the last goes.
**Command lines are not recorded.**

## Watcher health

| Type | metadata |
|---|---|
| `watcher_started` | `watcher_version`, `os_version`, `config_path`, `config_hash`, `config_error`, `collectors_enabled`, `database_path`, `fallback_events_imported`, `mode` |
| `watcher_stopped` | `reason`, `uptime_seconds`, `events_written` |
| `watcher_heartbeat` | every 15 min: `memory_mb`, `cpu_seconds_total`, `events_written`, `events_pending_upload`, `queue_length`, `collectors[]` |
| `collector_status` | `collector_name`, `status` (`running`, `failed`, `disabled_after_repeated_failures`), `error` |
| `config_changed` | `config_hash` |

## Privacy markers

If a block rule matched, the event is kept for timing but details are removed:
`application`/`window_title`/... become `"[excluded]"`, and `metadata.excluded = true`,
`metadata.excluded_reason` = `blocked_application` / `blocked_window_title` /
`blocked_domain` / `domain_not_in_allowed_list` / `blocked_url`.
`metadata.url_sanitized = true` means tokens were removed from the URL.

## Planned (Phase 2–5)

`ui_field_value`, `ui_action` (`button_clicked` etc.), `ui_focus`, `browser_page`,
`file_opened` / `file_saved` / `file_renamed` / `file_deleted`, `document_context`,
`print_job`, `download_detected`, `upload_context`, `automation_run` (local API).
These will be added to this document when built.

## Example

A full simulated morning is in [examples/simulated-morning.jsonl](examples/simulated-morning.jsonl)
with the viewer text in [examples/simulated-morning.txt](examples/simulated-morning.txt).

```json
{"schema_version":1,"event_id":"3f85fcedc26044bd9669ea3d38fd947c",
 "timestamp_utc":"2026-09-22T13:31:20.500Z","timestamp_local":"2026-09-22T09:31:20.500-04:00",
 "computer_id":"MPP-DESK-03","employee_id":"EMP001","windows_username":"MPP\\jane",
 "event_type":"app_session_end","application":"Adobe Photoshop 2025","process_name":"Photoshop",
 "process_id":10244,"window_title":"MA024-main.psd @ 66.7% (RGB/8)","domain":null,"url":null,
 "page_title":null,"session_id":"7ce77ba6d29e4cdfbca44cf4844ef107","task_context_id":null,
 "watcher_run_id":"3f6c0d2a9b8e4d1f8a7c6b5e4d3c2b1a","sequence":12,
 "collector":"activity","collector_version":"1.0.0",
 "metadata":{"session_start":"2026-09-22T09:19:20.500-04:00","session_end":"2026-09-22T09:31:20.500-04:00",
   "duration_seconds":720,"active_seconds":179.5,"idle_seconds":540.5,
   "end_reason":"foreground_changed","foreground":true,
   "next_process_name":"chrome","next_application":"Google Chrome"}}
```

## Export files

`<export root>/MPP Activity Logs/<employee_id>/<yyyy-MM-dd>/events_HH00_HH00.jsonl`,
using each event's local time. Files are appended to. Delivery is *at least once*:
de-duplicate by `event_id` when reading.
