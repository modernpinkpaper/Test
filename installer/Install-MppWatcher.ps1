<#
.SYNOPSIS
  Installs or upgrades MPP Watcher on this PC (Phase 1 installer script; MPPWatcherSetup.exe comes in Phase 5).

.DESCRIPTION
  - Copies MPPWatcher.exe to "C:\Program Files\MPP Watcher"
  - Creates %ProgramData%\MPP Watcher\config.json (an existing config is KEPT on upgrade)
  - Lets employees read the config but not change it
  - Registers a Scheduled Task that starts the watcher at every user logon, in that user's
    session, and restarts it if it fails
  - Adds a Start Menu shortcut for the live viewer
  Run from an elevated (Administrator) PowerShell.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\Install-MppWatcher.ps1 -EmployeeId EMP001
#>
[CmdletBinding()]
param(
    # Folder that contains MPPWatcher.exe (default: the folder this script is in).
    [string]$SourceFolder = $PSScriptRoot,
    [string]$InstallDir = "$env:ProgramFiles\MPP Watcher",
    # Optional: set employee_id in a NEWLY created config.
    [string]$EmployeeId = "",
    # Start the watcher right away for signed-in users.
    [switch]$NoStart
)

$ErrorActionPreference = 'Stop'
$TaskName = 'MPP Watcher'
$ConfigDir = Join-Path $env:ProgramData 'MPP Watcher'
$ConfigPath = Join-Path $ConfigDir 'config.json'

function Assert-Admin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    if (-not ([Security.Principal.WindowsPrincipal]$id).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Please run this script from an Administrator PowerShell.'
    }
}

Assert-Admin
$exeSource = Join-Path $SourceFolder 'MPPWatcher.exe'
if (-not (Test-Path $exeSource)) { throw "MPPWatcher.exe not found in $SourceFolder" }

Write-Host '1/6 Stopping any running MPP Watcher...'
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
}
$installedExe = Join-Path $InstallDir 'MPPWatcher.exe'
if (Test-Path $installedExe) {
    # Clean stop for the admin's own session (writes watcher_stopped and closes the open session).
    Start-Process -FilePath $installedExe -ArgumentList '--stop' -Wait -WindowStyle Hidden -ErrorAction SilentlyContinue
}
# Other users' sessions: a forced stop is still safe, the open session is recovered from its checkpoint.
Get-Process -Name 'MPPWatcher' -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

Write-Host "2/6 Copying program files to $InstallDir ..."
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Copy-Item -Path $exeSource -Destination $InstallDir -Force
foreach ($doc in @('README.md', 'PRIVACY.md')) {
    $p = Join-Path $SourceFolder $doc
    if (Test-Path $p) { Copy-Item $p $InstallDir -Force }
}
$exe = Join-Path $InstallDir 'MPPWatcher.exe'

Write-Host "3/6 Preparing configuration in $ConfigDir ..."
New-Item -ItemType Directory -Force -Path $ConfigDir | Out-Null
if (Test-Path $ConfigPath) {
    Write-Host '    Existing config.json kept (upgrade).'
} else {
    Start-Process -FilePath $exe -ArgumentList @('--write-default-config', "`"$ConfigPath`"") -Wait -WindowStyle Hidden
    if (-not (Test-Path $ConfigPath)) { throw "Could not create $ConfigPath" }
    if ($EmployeeId) {
        $json = Get-Content $ConfigPath -Raw | ConvertFrom-Json
        $json.employee_id = $EmployeeId
        $json | ConvertTo-Json -Depth 10 | Set-Content -Path $ConfigPath -Encoding UTF8
    }
    Write-Host '    New config.json created.'
}
# Employees (Users) may read the config; only Administrators/SYSTEM may change it.
& icacls $ConfigDir /inheritance:r /grant:r '*S-1-5-32-544:(OI)(CI)F' '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-545:(OI)(CI)RX' | Out-Null

Write-Host '4/6 Registering logon task...'
$action = New-ScheduledTaskAction -Execute $exe -WorkingDirectory $InstallDir
$trigger = New-ScheduledTaskTrigger -AtLogOn
# Also re-check every 5 minutes: if the watcher crashed it is started again
# (a second copy exits immediately, so this never creates duplicates).
$trigger.Repetition = (New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 5)).Repetition
# Group principal = runs for whichever user signs in, inside their own desktop session, not elevated.
$principal = New-ScheduledTaskPrincipal -GroupId 'S-1-5-32-545' -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable `
    -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
    -MultipleInstances IgnoreNew -Hidden
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings `
    -Description 'MPP Watcher company activity logging (starts at logon).' -Force | Out-Null

Write-Host '5/6 Adding Start Menu shortcut...'
$startMenu = Join-Path $env:ProgramData 'Microsoft\Windows\Start Menu\Programs\MPP Watcher'
New-Item -ItemType Directory -Force -Path $startMenu | Out-Null
$shell = New-Object -ComObject WScript.Shell
$lnk = $shell.CreateShortcut((Join-Path $startMenu 'MPP Watcher Live Viewer.lnk'))
$lnk.TargetPath = $exe
$lnk.Arguments = '--viewer'
$lnk.WorkingDirectory = $InstallDir
$lnk.Save()

if (-not $NoStart) {
    Write-Host '6/6 Starting MPP Watcher for signed-in users...'
    Start-ScheduledTask -TaskName $TaskName
} else {
    Write-Host '6/6 Not started (-NoStart). It will start at next logon.'
}

Write-Host ''
Write-Host 'MPP Watcher installed.' -ForegroundColor Green
Write-Host "  Program : $exe"
Write-Host "  Config  : $ConfigPath"
Write-Host '  Data    : %LOCALAPPDATA%\MPP Watcher\data\events.db (per user)'
Write-Host '  Viewer  : Start Menu > MPP Watcher > MPP Watcher Live Viewer'
