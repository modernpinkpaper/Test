; MPP Watcher installer (Inno Setup 6). Built in CI:  ISCC.exe /DAppVersion=0.1.0 installer\MPPWatcherSetup.iss
; Install:   MPPWatcherSetup.exe                       (wizard)
;            MPPWatcherSetup.exe /VERYSILENT /SUPPRESSMSGBOXES /EMPLOYEEID=EMP001   (silent, for many PCs)
; Uninstall: Settings > Apps > MPP Watcher, or "C:\Program Files\MPP Watcher\unins000.exe" /VERYSILENT
; The real setup work (config, permissions, logon task, watchdog service, shortcut) is done by
; Install-MppWatcher.ps1, the same script that is tested on Windows in CI.

#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

[Setup]
AppId={{8C1F2E7A-5B3D-4E91-9A64-3F2D7C0B1E55}
AppName=MPP Watcher
AppVersion={#AppVersion}
AppVerName=MPP Watcher {#AppVersion}
AppPublisher=MPP
DefaultDirName={autopf}\MPP Watcher
DisableDirPage=yes
DisableProgramGroupPage=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\setup-output
OutputBaseFilename=MPPWatcherSetup
Compression=lzma2
SolidCompression=yes
UninstallDisplayName=MPP Watcher
UninstallDisplayIcon={app}\MPPWatcher.exe
SetupLogging=yes
CloseApplications=no
WizardStyle=modern

[Messages]
WelcomeLabel2=This installs MPP Watcher, the company activity logger.%n%nIt records which apps, pages, fields, files and print jobs are used for work. It does NOT take screenshots, record the screen, audio or keystrokes, and never records passwords or payment details.%n%nSee PRIVACY.md in the install folder for details.

[Files]
Source: "..\publish\MPPWatcher.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "Install-MppWatcher.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "Uninstall-MppWatcher.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\docs\PRIVACY.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\docs\LOCAL_API.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\tools\mpp-watcher-client.user.js"; DestDir: "{app}"; Flags: ignoreversion

[Run]
Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\Install-MppWatcher.ps1"" -SourceFolder ""{app}"" -InstallDir ""{app}"" {code:EmployeeArg}"; \
  Flags: runhidden waituntilterminated; StatusMsg: "Setting up MPP Watcher (settings, logon task, watchdog)..."

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
  Exec('sc.exe', 'stop MPPWatcherService', '', SW_HIDE, ewWaitUntilTerminated, Rc);
  if FileExists(ExpandConstant('{app}\MPPWatcher.exe')) then
    Exec(ExpandConstant('{app}\MPPWatcher.exe'), '--stop', '', SW_HIDE, ewWaitUntilTerminated, Rc);
  Exec('taskkill.exe', '/F /IM MPPWatcher.exe', '', SW_HIDE, ewWaitUntilTerminated, Rc);
  Result := '';
end;
