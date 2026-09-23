<#
.SYNOPSIS
  Removes MT Log. By default the config and the employees' collected data are KEPT.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\Uninstall-MppWatcher.ps1
  powershell -ExecutionPolicy Bypass -File .\Uninstall-MppWatcher.ps1 -RemoveConfig -RemoveUserData
#>
[CmdletBinding()]
param(
    [string]$InstallDir = "$env:ProgramFiles\MT Log",
    [switch]$RemoveConfig,
    # Deletes every user's %LOCALAPPDATA%\MT Log folder (database, logs, un-exported events!).
    [switch]$RemoveUserData,
    # Used by MTLogSetup's uninstaller, which removes the program files itself.
    [switch]$KeepProgramFiles
)

$ErrorActionPreference = 'Stop'
$TaskName = 'MT Log'
$ServiceName = 'MTLogService'

$id = [Security.Principal.WindowsIdentity]::GetCurrent()
if (-not ([Security.Principal.WindowsPrincipal]$id).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Please run this script from an Administrator PowerShell.'
}

# The watchdog first — otherwise it would restart the watcher.
if (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue) {
    Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
    & sc.exe delete $ServiceName | Out-Null
    Write-Host 'Watchdog service removed.'
}
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host 'Logon task removed.'
}
$installedExe = Join-Path $InstallDir 'MTLog.exe'
if (Test-Path $installedExe) {
    Start-Process -FilePath $installedExe -ArgumentList '--stop' -Wait -WindowStyle Hidden -ErrorAction SilentlyContinue
}
Get-Process -Name 'MTLog' -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

if (-not $KeepProgramFiles -and (Test-Path $InstallDir)) { Remove-Item -Recurse -Force $InstallDir; Write-Host "Removed $InstallDir" }
$startMenu = Join-Path $env:ProgramData 'Microsoft\Windows\Start Menu\Programs\MT Log'
if (Test-Path $startMenu) { Remove-Item -Recurse -Force $startMenu }

$configDir = Join-Path $env:ProgramData 'MT Log'
if ($RemoveConfig -and (Test-Path $configDir)) { Remove-Item -Recurse -Force $configDir; Write-Host "Removed $configDir" }
elseif (Test-Path $configDir) { Write-Host "Config kept: $configDir" }

if ($RemoveUserData) {
    Get-ChildItem 'C:\Users' -Directory -ErrorAction SilentlyContinue | ForEach-Object {
        $p = Join-Path $_.FullName 'AppData\Local\MT Log'
        if (Test-Path $p) { Remove-Item -Recurse -Force $p; Write-Host "Removed $p" }
    }
} else {
    Write-Host 'Collected data kept in each user''s %LOCALAPPDATA%\MT Log (use -RemoveUserData to delete).'
}
Write-Host 'MT Log uninstalled.' -ForegroundColor Green
