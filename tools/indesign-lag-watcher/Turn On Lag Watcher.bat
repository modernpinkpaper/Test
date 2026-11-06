@echo off
rem Turns on the InDesign Lag Watcher on this PC (no admin needed).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0LagWatcher.ps1" -Install
pause
