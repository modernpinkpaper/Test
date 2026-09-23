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

## Phase 2 — UI Automation ✅
Field values (finished values only), clicks on named controls, sensitive-field refusal,
diagnostic inspector (`MPPWatcher.exe --inspect`). Windows-verified cases:
WinForms fields/buttons/check box, password and card fields never recorded, settled value
while typing stops, Microsoft Edge web page fields + button, inspector report incl. hidden
password.

## Phase 3 — browser context ✅
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

## Phase 4 — files and business apps ✅
Files created/saved/renamed/moved/deleted/downloaded in watched folders (one event per action,
Office "safe save" and browser downloads recognised, bulk summaries), downloads linked to the page
they came from, document names + SKUs from app title bars, files opened (Windows Recent Items),
print jobs (printer, document, pages), files picked for upload in a browser with the page.
Windows-verified including a real test printer and an upload in Edge on a look-alike Etsy page.

Found and fixed thanks to the real runs: the default "*\AppData\*" ignore rule also swallowed
watched folders that live under AppData; Edge shows file dialogs from a helper process.

## Phase 5 — integration and deployment ✅ (except Google Drive)
- Local event API for scripts (signed, localhost only) — see [LOCAL_API.md](LOCAL_API.md).
- Watchdog Windows service (restarts a stopped watcher within ~30 s) — verified by killing the
  watcher on the test machine.
- `MPPWatcherSetup.exe` (Inno Setup): wizard or silent install, Add/Remove Programs, upgrade keeps
  config, clean uninstall — verified by silent install → upgrade → uninstall on the test machine.

### Google Drive (done: Google Drive for desktop)
- Default export folder: `{GoogleDrive}\My Drive\Personal\mpp activity`. The watcher finds the
  Google Drive letter by itself at every export (the drive with a `My Drive` folder, G: first).
  If Drive is closed or signed out, events stay pending on the PC and are exported later.
- `MPPWatcher.exe --export-now` exports right away (also in the tray menu).
- Verified on the test machine with a `subst` drive that looks like Google Drive.
- Not built: direct Drive API upload (needs a Google Cloud service-account key).

### Before a wide rollout
- **Code-sign** `MPPWatcher.exe` and `MPPWatcherSetup.exe` (needs a code-signing certificate) so
  SmartScreen and antivirus trust them.
- Try the inspector on your real logged-in pages (Keepa, Seller Central, Etsy editor, Shopify) and
  in Photoshop/InDesign/Excel.

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
- **After a crash** the watchdog restarts the watcher within ~30 s; the open session is recovered
  from its checkpoint (≤ 30 s approximate end time).
- **Remote Desktop / Fast User Switching**: each signed-in user gets their own watcher.
  Disconnect is treated like lock. Not yet tested.
- **Export is at-least-once**; a crash exactly between writing a file and marking events
  uploaded can duplicate lines. De-duplicate by `event_id`.
- **An employee with local admin rights could stop or remove the watcher.** Standard users cannot
  stop the watchdog service or change the config.
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
- **Files picked in Open dialogs** also show up as `file_opened` (Windows adds them to Recent Items).
- **Print jobs** are seen through the print queue; a job that enters and leaves the queue within
  about a second (very fast virtual printers) can be missed.
- **Memory**: about 140 MB with all collectors on the test machine (target < 200 MB).
