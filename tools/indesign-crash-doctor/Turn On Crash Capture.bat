@echo off
rem Makes Windows save a small crash file every time InDesign crashes (asks for admin).
rem After the next crash, run "Run InDesign Crash Doctor.bat" again.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0InDesignCrashDoctor.ps1" -EnableCrashDumps
pause
