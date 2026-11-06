@echo off
rem Stops saving InDesign crash files (asks for admin).
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0InDesignCrashDoctor.ps1" -DisableCrashDumps
pause
