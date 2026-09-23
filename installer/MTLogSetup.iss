; MT Log installer (Inno Setup 6). Built in CI:  ISCC.exe /DAppVersion=0.1.0 installer\MTLogSetup.iss
; Install:   MTLogSetup.exe                       (wizard)
;            MTLogSetup.exe /VERYSILENT /SUPPRESSMSGBOXES /EMPLOYEEID=EMP001   (silent, for many PCs)
; Uninstall: Settings > Apps > MT Log, or "C:\Program Files\MT Log\unins000.exe" /VERYSILENT
; The real setup work (config, permissions, logon task, watchdog service, shortcut) is done by
; Install-MppWatcher.ps1, the same script that is tested on Windows in CI.

#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

[Setup]
AppId={{2F9A6D14-7C08-4B52-A1E3-9D5C4B2A8F60}
AppName=MT Log
AppVersion={#AppVersion}
AppVerName=MT Log {#AppVersion}
AppPublisher=MPP
DefaultDirName={autopf}\MT Log
DisableDirPage=yes
DisableProgramGroupPage=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\setup-output
OutputBaseFilename=MTLogSetup
Compression=lzma2
SolidCompression=yes
UninstallDisplayName=MT Log
UninstallDisplayIcon={app}\MTLog.exe
SetupLogging=yes
CloseApplications=no
WizardStyle=modern

[Messages]
WelcomeLabel2=This installs MT Log, the company activity logger.%n%nIt records which apps, pages, fields, files and print jobs are used for work. It does NOT take screenshots, record the screen, audio or keystrokes, and never records passwords or payment details.%n%nSee PRIVACY.md in the install folder for details.

[Files]
Source: "..\publish\MTLog.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "Install-MppWatcher.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "Uninstall-MppWatcher.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\docs\PRIVACY.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\docs\LOCAL_API.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\tools\mpp-watcher-client.user.js"; DestDir: "{app}"; Flags: ignoreversion

[Run]
Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\Install-MppWatcher.ps1"" -SourceFolder ""{app}"" -InstallDir ""{app}"" {code:EmployeeArg}"; \
  Flags: runhidden waituntilterminated; StatusMsg: "Setting up MT Log (settings, logon task, watchdog)..."

[UninstallRun]
Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\Uninstall-MppWatcher.ps1"" -InstallDir ""{app}"" -KeepProgramFiles"; \
  Flags: runhidden waituntilterminated; RunOnceId: "RemoveMppWatcherSetup"

[Code]
function EmployeeArg(Param: String): String;
var
  Id: String;
begin
  Id := ExpandConstant('{param:EMPLOYEEID|}');
  if Id <> '' then Result := '-EmployeeId "' + Id + '"' else Result := '';
end;

{ Upgrade: stop the watchdog and the running watcher before the program file is replaced. }
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Rc: Integer;
begin
  Exec('sc.exe', 'stop MTLogService', '', SW_HIDE, ewWaitUntilTerminated, Rc);
  if FileExists(ExpandConstant('{app}\MTLog.exe')) then
    Exec(ExpandConstant('{app}\MTLog.exe'), '--stop', '', SW_HIDE, ewWaitUntilTerminated, Rc);
  Exec('taskkill.exe', '/F /IM MTLog.exe', '', SW_HIDE, ewWaitUntilTerminated, Rc);
  Result := '';
end;
