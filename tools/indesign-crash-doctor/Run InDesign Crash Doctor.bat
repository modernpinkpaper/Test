@echo off
rem Double-click to find out why InDesign crashes.
rem You can also drag crash-log folders or files onto this file.
setlocal EnableDelayedExpansion
set "EXTRA="
:collect
if "%~1"=="" goto run
if defined EXTRA (set "EXTRA=!EXTRA!;%~1") else (set "EXTRA=%~1")
shift
goto collect
:run
if defined EXTRA (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0InDesignCrashDoctor.ps1" -ExtraFolder "!EXTRA!"
) else (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0InDesignCrashDoctor.ps1"
)
echo.
pause
