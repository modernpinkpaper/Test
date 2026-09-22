<#
.SYNOPSIS
  Removes MPP Watcher. By default the config and the employees' collected data are KEPT.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\Uninstall-MppWatcher.ps1
  powershell -ExecutionPolicy Bypass -File .\Uninstall-MppWatcher.ps1 -RemoveConfig -RemoveUserData
#>
[CmdletBinding()]
param(
    [string]$InstallDir = "$env:ProgramFiles\MPP Watcher",
    [switch]$RemoveConfig,
    # Deletes every user's %LOCALAPPDATA%\MPP Watcher folder (database, logs, un-exported events!).
    [switch]$RemoveUserData
)

$ErrorActionPreference = 'Stop'
$TaskName = 'MPP Watcher'

$id = [Security.Principal.WindowsIdentity]::GetCurrent()
if (-not ([Security.Principal.WindowsPrincipal]$id).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Please run this script from an Administrator PowerShell.'
}

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host 'Logon task removed.'
}
Get-Process -Name 'MPPWatcher' -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

if (Test-Path $InstallDir) { Remove-Item -Recurse -Force $InstallDir; Write-Host "Removed $InstallDir" }
$startMenu = Join-Path $env:ProgramData 'Microsoft\Windows\Start Menu\Programs\MPP Watcher'
if (Test-Path $startMenu) { Remove-Item -Recurse -Force $startMenu }

$configDir = Join-Path $env:ProgramData 'MPP Watcher'
if ($RemoveConfig -and (Test-Path $configDir)) { Remove-Item -Recurse -Force $configDir; Write-Host "Removed $configDir" }
elseif (Test-Path $configDir) { Write-Host "Config kept: $configDir" }

if ($RemoveUserData) {
    Get-ChildItem 'C:\Users' -Directory -ErrorAction SilentlyContinue | ForEach-Object {
        $p = Join-Path $_.FullName 'AppData\Local\MPP Watcher'
        if (Test-Path $p) { Remove-Item -Recurse -Force $p; Write-Host "Removed $p" }
    }
} else {
    Write-Host 'Collected data kept in each user''s %LOCALAPPDATA%\MPP Watcher (use -RemoveUserData to delete).'
}
Write-Host 'MPP Watcher uninstalled.' -ForegroundColor Green
