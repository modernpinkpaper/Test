# Roadmap, Phase 1 test checklist, and known limitations

## How each phase is verified

Every push runs the **build** workflow. The Windows job runs on a real Windows 11 desktop
(GitHub-hosted runner) and:

1. runs 130+ Core unit tests,
2. publishes `MPPWatcher.exe`,
3. runs the **Windows tests**, which act like an employee: open windows, switch between them,
   change titles, stay idle, start/stop programs, type into fields (including a fake password
   and card number), click buttons, use Microsoft Edge on a test listing-editor page, open the
   live viewer and the inspector, kill the watcher to test crash recovery,
4. runs a 15-second smoke test of the exe,
5. installs, upgrades and uninstalls with the PowerShell scripts,
6. uploads screenshots (`windows-test-output`) and the package (`MPPWatcher-win-x64`).

A phase is only called done when all of this is green.

## Phase 1 — done ✅
Foreground sessions, idle, lock/sleep, processes, SQLite, export, viewer, installer, crash
recovery. Verified on Windows (see above).

## Phase 2 — UI Automation
Field values (finished values only), clicks on named controls, sensitive-field refusal,
diagnostic inspector (`MPPWatcher.exe --inspect`). Windows-verified cases:
WinForms fields/buttons/check box, password and card fields never recorded, settled value
while typing stops, Microsoft Edge web page fields + button, inspector report incl. hidden
password.

## Phase 3 — browser context
Address bar through UI Automation (not while typing), URL sanitizing, page title from the
page itself, site rules (Amazon, Seller Central incl. Search Query Performance, Keepa, Etsy,
Shopify, Google Docs/Sheets/Drive, Gmail, ChatGPT), headings on business sites, and page
context on sessions, field values and clicks. Windows-verified with Microsoft Edge visiting
look-alike pages served under the real addresses (amazon.com, sellercentral.amazon.com,
keepa.com, etsy.com, admin.shopify.com) on the test machine.

Found and fixed thanks to the real runs: pages read while still "Untitled"; Amazon's
`session-id` not removed; Edge's "and N more pages" splitting sessions.

### Still worth checking on your own PCs
Nothing here needs you before the next phase, but these can only be seen with your accounts:
Keepa search box, Seller Central SKU/search fields, Etsy listing editor, Shopify product
editor, Photoshop/InDesign/Excel. Open `MPPWatcher.exe --inspect`, point at the field, and
press **Save report…** if something looks wrong.

## Known limitations

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
- **UI Automation depends on the app.** Chrome/Edge, WinForms, WPF, Office expose a lot;
  some apps (games, older custom-drawn apps, parts of Adobe apps) expose little or nothing.
  Use the inspector to see. Chromium builds its accessibility tree only once a UI Automation
  client asks, which costs the browser a little extra memory/CPU.
- **Keyboard-only actions** (pressing Enter on a button, keyboard shortcuts like Ctrl+S) are not
  recorded as `ui_action`; the resulting field values and page/title changes still are.
- **Clicks are looked up after the click**; if the button disappears instantly (closing
  dialog), the control may not be identified and nothing is recorded.
- **Not code-signed yet.** SmartScreen/antivirus may warn about an unsigned exe that uses
  window hooks. Plan a code-signing certificate before wide rollout.

## Next phases

**Phase 3 – remaining ideas** (not needed to call Phase 3 done)
- Seller Central report settings that live only in the page (date pickers, ASIN scope) rather
  than the URL: read the selected values of those controls when the report page is shown.
- Keepa mode tabs and "products being compared" from the page, not only the `#!` route.
- Firefox is supported by design (address bar `urlbar-input`) but only Edge is tested in CI.
- Check with real logged-in pages using `MPPWatcher.exe --inspect` (see above).

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
