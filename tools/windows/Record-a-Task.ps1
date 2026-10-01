# MT Log — "Record a Task" one-button toggle.
# Click once to START recording a task (with screenshots, for an SOP); click again to STOP.
# It just calls the MT Log watcher that is already running:  MTLog.exe --capture-sop / --capture-stop.
#
# Put this next to "Record a Task.cmd" and pin that to the taskbar (see README.md).

$ErrorActionPreference = 'SilentlyContinue'

# Find the installed MTLog.exe. Edit this list if yours lives somewhere else.
function Find-MTLog {
    $candidates = @(
        "$env:ProgramFiles\MT Log\MTLog.exe",
        "${env:ProgramFiles(x86)}\MT Log\MTLog.exe",
        "$env:LOCALAPPDATA\MT Log\MTLog.exe",
        "$env:ProgramData\MT Log\MTLog.exe"
    )
    foreach ($c in $candidates) { if (Test-Path $c) { return $c } }
    $cmd = Get-Command MTLog.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

# A small popup that closes itself after a couple of seconds (no OK needed).
function Notify($text, $title = 'MT Log') {
    try { (New-Object -ComObject WScript.Shell).Popup($text, 2, $title, 64) | Out-Null } catch {}
}

$exe = Find-MTLog
if (-not $exe) {
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show(
        "Could not find MTLog.exe. Open Record-a-Task.ps1 and edit the Find-MTLog list to point at it.",
        "MT Log") | Out-Null
    exit 1
}

# A tiny per-user flag remembers whether a recording is in progress, so one button can toggle.
$flag = Join-Path $env:LOCALAPPDATA 'MT Log\recording.flag'
New-Item -ItemType Directory -Force -Path (Split-Path $flag) | Out-Null

if (Test-Path $flag) {
    # Currently recording -> stop.
    & $exe --capture-stop | Out-Null
    Remove-Item $flag -Force
    Notify "Task recording stopped."
}
else {
    # Not recording -> ask for a short task name, then start.
    Add-Type -AssemblyName Microsoft.VisualBasic
    $label = [Microsoft.VisualBasic.Interaction]::InputBox(
        "What task are you recording? (used to name the SOP)", "Record a Task", "")
    if ([string]::IsNullOrWhiteSpace($label)) { exit 0 }   # cancelled
    & $exe --capture-sop "$label" | Out-Null
    Set-Content -Path $flag -Value $label
    Notify "Recording task: $label"
}
