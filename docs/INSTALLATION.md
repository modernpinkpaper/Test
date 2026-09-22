# Installation

> Phase 1 uses PowerShell install scripts. The one-file `MPPWatcherSetup.exe` installer
> (with Add/Remove Programs entry and a watchdog service) is Phase 5.

## Requirements

- Windows 10 or 11, 64-bit
- Administrator rights to install
- No .NET installation needed (the exe is self-contained)

## Get the files

Either:
- GitHub → **Actions** → latest **build** run → download artifact **MPPWatcher-win-x64**
  (contains `MPPWatcher.exe`, install/uninstall scripts, README, PRIVACY), or
- build it: see [DEVELOPMENT.md](DEVELOPMENT.md).

Unzip it into a folder, e.g. `C:\Temp\MPPWatcher`.

## Install / upgrade

Open **PowerShell as Administrator**:

```powershell
cd C:\Temp\MPPWatcher
powershell -ExecutionPolicy Bypass -File .\Install-MppWatcher.ps1 -EmployeeId EMP001
```

What it does:
1. Stops a running watcher (upgrade-safe; the open session is recovered on restart).
2. Copies `MPPWatcher.exe` to `C:\Program Files\MPP Watcher`.
3. Creates `%ProgramData%\MPP Watcher\config.json` if missing. **An existing config is kept.**
4. Sets permissions: users can read the config, only admins can change it.
5. Registers the scheduled task **"MPP Watcher"**: starts at every logon for any user, in
   their own session, not elevated, no time limit, re-checked every 5 minutes (restarts it
   if it crashed; a second copy exits at once).
6. Adds Start Menu → **MPP Watcher → MPP Watcher Live Viewer**.
7. Starts it for signed-in users (skip with `-NoStart`).

For PCs shared by several people, leave `-EmployeeId` out and fill
`employee_id_by_windows_user` in the config.

## Check it works

1. Tray: a pink **M** icon, tooltip "MPP Watcher – activity logging is on".
2. Start Menu → **MPP Watcher Live Viewer**. Switch between apps; lines appear within ~2 s.
3. Right-click tray → **Status…** shows collectors "running".
4. Self-test (any time): `"C:\Program Files\MPP Watcher\MPPWatcher.exe" --smoke-test 20 --result C:\Temp\smoke.txt`
   then open `C:\Temp\smoke.txt` (last line `RESULT: PASS`).

## Uninstall

```powershell
powershell -ExecutionPolicy Bypass -File .\Uninstall-MppWatcher.ps1
# also remove config and all users' collected data (including events not yet exported!):
powershell -ExecutionPolicy Bypass -File .\Uninstall-MppWatcher.ps1 -RemoveConfig -RemoveUserData
```

## Silent install for many PCs

The install script has no prompts, so it can be pushed with Intune, GPO startup script,
PDQ, etc.: `powershell -ExecutionPolicy Bypass -File \\server\share\Install-MppWatcher.ps1 -SourceFolder \\server\share`.
