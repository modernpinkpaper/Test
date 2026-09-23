# Configuration

File: `%ProgramData%\MPP Watcher\config.json` (created by the installer; employees can
read but not edit it). Full default file: [config/config.example.json](../config/config.example.json).

- Keys are `snake_case`. Missing keys use defaults. `//` comments and trailing commas are allowed.
- Numbers outside safe limits are clamped (e.g. idle timeout 30 s – 1 h).
- If the file is broken, the watcher keeps the last good settings and logs the error.
- **Applied immediately** after saving: privacy rules, idle timeout, employee id, session
  timing (stable times, title split), dedup window, retention days, export batch size.
  **Applied after restart** (sign out/in, or reboot): collectors on/off, folders, poll
  interval, heartbeat/export intervals, tray icon.

## Main settings

| Key | Default | Meaning |
|---|---|---|
| `company_name` | `"MPP"` | Shown in tray tooltip; stored in `watcher_started`. |
| `employee_id` | `""` | Employee id for this PC. |
| `employee_id_by_windows_user` | `{}` | `{"OFFICE\\jane": "EMP001", "bob": "EMP002"}` for shared PCs. Wins over `employee_id`. |
| `computer_id` | `""` | Empty = Windows computer name. |
| `idle_timeout_seconds` | `300` | No keyboard/mouse this long = idle. |
| `debug_mode` | `false` | More detail in the diagnostics log. |
| `show_tray_icon` | `true` | Tray icon telling the employee logging is on. |
| `allow_user_exit` | `false` | Show "Exit" in the tray menu. |
| `data_folder` | `""` | Empty = `%LOCALAPPDATA%\MPP Watcher\data`. Environment variables allowed. |
| `log_folder` | `""` | Empty = `%LOCALAPPDATA%\MPP Watcher\logs`. |

## `collectors.activity`

| Key | Default | Meaning |
|---|---|---|
| `enabled` | `true` | Foreground sessions, idle, lock/sleep. |
| `foreground_stable_ms` | `1000` | A window must be in front this long to count. |
| `title_stable_ms` | `2000` | A new title must stay this long to count. |
| `split_sessions_on_title_change` | `true` | New page/document = new session. `false` = one session per window with `window_title_changed` events. |
| `poll_interval_ms` | `500` | How often title and idle are checked. |
| `gap_threshold_seconds` | `60` | Watcher silent this long → close session, write `activity_gap`. |
| `return_window_minutes` | `240` | How long "returning to a previous window" is remembered. |
| `heartbeat_minutes` | `15` | Health event interval (0 = off). |
| `checkpoint_seconds` | `30` | How often the open session is saved for crash recovery. |

## `collectors.process`

| Key | Default | Meaning |
|---|---|---|
| `enabled` | `true` | Program start/exit tracking. |
| `scan_interval_seconds` | `15` | |
| `ignore_processes` | system list | Wildcards allowed. |
| `collapse_multi_instance` | `true` | Treat Chrome's many processes as one app. |

## `collectors.ui_automation` (Phase 2)

| Key | Default | Meaning |
|---|---|---|
| `enabled` | `true` | UI Automation collector (field values + clicks on named controls). |
| `capture_field_values` | `true` | Record finished field values. |
| `capture_actions` | `true` | Record clicks on buttons, links, tabs, menu items, check boxes. |
| `max_value_length` | `200` | Longer or multi-line values are not stored (length only). |
| `focused_field_poll_ms` | `500` | How often the focused field's value is re-read. |
| `value_settle_seconds` | `4` | A changed value that stays this long is recorded even if focus stays. |
| `action_keywords` | save, publish, upload, import, export, search, download, print, submit, update, apply, add, create, delete, ... | Names that mark `is_key_action`. |
| `ignore_applications` | `[]` | Apps where UI Automation is not used at all. |

## `collectors.browser` (Phase 3)

| Key | Default | Meaning |
|---|---|---|
| `enabled` | `true` | Read the page address from the front browser window. |
| `browsers` | chrome, msedge, firefox, brave, opera, vivaldi | Process names treated as browsers. |
| `poll_ms` | `1000` | How often the front browser window is checked. |
| `page_text_domains` | amazon, keepa, etsy, Shopify admin, Google Docs/Drive | Only here are page headings read. |
| `max_headings` | `8` | |

## `collectors.files` (Phase 4)

| Key | Default | Meaning |
|---|---|---|
| `enabled` | `true` | File actions in watched folders. |
| `watched_folders` | Desktop, Documents, Downloads, Pictures | With subfolders. Add e.g. `"D:\\Designs"`. |
| `downloads_folder` | `%USERPROFILE%\\Downloads` | New files here are `file_downloaded`. |
| `ignore_paths` | `*\\AppData\\*`, `.git`, `node_modules`, recycle bin | Matched against the part of the path inside a watched folder. |
| `quiet_ms` | `2000` | Wait after the last notice (one event per save). |
| `bulk_threshold` | `50` | More actions at once → one `file_bulk_activity`. |
| `track_opened_files` | `true` | `file_opened` from Windows Recent Items. |
| `sku_patterns` | `[]` (= `[A-Z]{2,4}\\d{2,5}`, e.g. MA023) | Regular expressions for product codes in file names. |

## `collectors.print` (Phase 4)

| Key | Default | Meaning |
|---|---|---|
| `enabled` | `true` | Print jobs of the signed-in user (printer, document name, pages). |

## `privacy`

See [PRIVACY.md](PRIVACY.md).

| Key | Meaning |
|---|---|
| `blocked_mode` | `"redact"` (keep time, hide details) or `"drop"` (write nothing). |
| `blocked_applications` | process names, wildcards. Default: password managers, Windows credential prompts. |
| `blocked_window_titles` | wildcard patterns. |
| `allowed_domains` | if not empty, only these websites are logged in detail (Phase 3). |
| `blocked_domains` | default includes `*bank*` and Google/Microsoft sign-in pages. |
| `blocked_urls` | default includes checkout, payment, sign-in, login, password pages. |
| `blocked_folders` | file paths (Phase 4). |
| `blocked_controls` | UI control names/ids (Phase 2). |
| `sensitive_field_terms` | extra words that make a field sensitive (added to the built-in list, which cannot be removed). |
| `sensitive_url_parameters` | extra URL parameters to strip. |

## `export`

| Key | Default | Meaning |
|---|---|---|
| `enabled` | `true` | |
| `uploader` | `"local_folder"` | `google_drive` planned. |
| `destination_folder` | `"{GoogleDrive}\\My Drive\\Personal\\mpp activity"` | `{GoogleDrive}` = the Google Drive for desktop drive, found automatically at every export (G: first). Files go to `<folder>\<employee>\<date>\events_0900_1000_<PC>.jsonl`. Can also be a plain folder or network share (`\\server\logs`). Empty = `%LOCALAPPDATA%\MPP Watcher\export\MPP Activity Logs`. If the folder is not reachable, events wait on the PC and retry. |
| `interval_minutes` | `15` | |
| `batch_size` | `2000` | |

## `retention` / `deduplication`

| Key | Default | Meaning |
|---|---|---|
| `retention.keep_uploaded_events_days` | `30` | Uploaded events older than this are deleted locally. Pending events are never deleted. |
| `retention.keep_diagnostic_logs_days` | `14` | |
| `deduplication.window_seconds` | `10` | Identical state events inside this window are written once. |
