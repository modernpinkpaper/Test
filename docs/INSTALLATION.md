# Installation

## Requirements

- Windows 10 or 11, 64-bit
- Administrator rights to install
- No .NET installation needed (the exe is self-contained)

## Install with MTLogSetup.exe (recommended)

1. GitHub → **Actions** → latest green **build** run → download **MTLog-win-x64** → unzip.
2. Double-click **`MTLogSetup.exe`** and follow the wizard (needs admin rights).

Silent install for many PCs (Intune, GPO, PDQ, ...):

```
MTLogSetup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /EMPLOYEEID=EMP001
```

`/EMPLOYEEID` only fills a **new** config. For shared PCs leave it out and fill
`employee_id_by_windows_user` in the config.

What setup does:
1. Stops the watchdog and any running watcher (upgrade-safe).
2. Installs to `C:\Program Files\MT Log` and adds **MT Log** to *Add or remove programs*.
3. Creates `%ProgramData%\MT Log\config.json` if missing (**an existing config is kept**);
   users can read it, only admins can change it.
4. Registers the logon task **"MT Log"** (starts the watcher for every user at sign-in,
   in their own session, not elevated; re-checked every 5 minutes).
5. Installs the **"MT Log (watchdog)"** Windows service: every 30 s it checks each signed-in
   user and restarts their watcher if it stopped (max 5 times per hour). It records nothing itself.
6. Adds Start Menu → **MT Log → MT Log Live Viewer** and starts the watcher.

## Google Drive (where the logs go)

By default the logs go to **`G:\My Drive\Personal\mpp activity`** through Google Drive for desktop.

1. Install **Google Drive for desktop** on the PC and sign in to the Google account that should
   receive the logs. Keep the default "stream files" mode (it shows up as drive `G:`).
2. That's all. The watcher finds the Drive letter itself. The `mpp activity` folder is created
   on the first export (every 15 minutes, or run `MTLog.exe --export-now`).
3. If Drive is closed or signed out, logs wait safely on the PC and are sent later.

Tip: a Google account used only for these logs is safer than a personal account, because every
person at that PC can open the whole Drive.

An upgrade keeps the old config.json. If it still has `"destination_folder": ""`, change it to
`"{GoogleDrive}\\My Drive\\Personal\\mpp activity"` to use Google Drive.

## Uninstall

**Settings → Apps → MT Log → Uninstall**, or silently:
`"C:\Program Files\MT Log\unins000.exe" /VERYSILENT /SUPPRESSMSGBOXES`.
The config and each user's collected data are kept. To remove them as well:

```powershell
powershell -ExecutionPolicy Bypass -File .\Uninstall-MppWatcher.ps1 -RemoveConfig -RemoveUserData
```

## Alternative: PowerShell scripts

The same steps without the setup exe (Administrator PowerShell, in the unzipped folder):

```powershell
powershell -ExecutionPolicy Bypass -File .\Install-MppWatcher.ps1 -EmployeeId EMP001
powershell -ExecutionPolicy Bypass -File .\Uninstall-MppWatcher.ps1
```

## Check it works

1. Tray: a pink **M** icon, tooltip "MT Log – activity logging is on".
2. Start Menu → **MT Log Live Viewer**. Switch between apps; lines appear within ~2 s.
3. Right-click tray → **Status…** shows collectors "running".
4. Self-test (any time): `"C:\Program Files\MT Log\MTLog.exe" --smoke-test 20 --result C:\Temp\smoke.txt`
   then open `C:\Temp\smoke.txt` (last line `RESULT: PASS`).
