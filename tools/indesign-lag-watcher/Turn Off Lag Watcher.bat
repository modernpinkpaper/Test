@echo off
rem Turns off the InDesign Lag Watcher. Logs are kept.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0LagWatcher.ps1" -Uninstall
pause
