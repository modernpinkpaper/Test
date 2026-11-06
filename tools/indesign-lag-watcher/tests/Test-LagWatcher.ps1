# Tests for LagWatcher.ps1. No Pester needed.
# The "brain" tests run anywhere; the Windows tests run only on Windows.
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$tmp = Join-Path ([IO.Path]::GetTempPath()) ("lagwatch-test-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tmp | Out-Null
. (Join-Path $here '..\LagWatcher.ps1') -NoLoop -LogFolder $tmp

$script:fails = 0
function Check([string]$name, [bool]$ok) {
    if ($ok) { Write-Host "PASS  $name" } else { Write-Host "FAIL  $name" -ForegroundColor Red; $script:fails++ }
}

# --- lag state machine ---
$t0 = [datetime]'2026-11-07T10:00:00'
$s = New-LagState
Check 'fast answer is not a lag'      ($null -eq (Step-LagState $s 15 $t0))
Check 'no answer starts a lag'        ('lag-start' -eq (Step-LagState $s -1 $t0.AddSeconds(2)))
Check 'lag start is set 1s back'      ($s.Start -eq $t0.AddSeconds(1))
Check 'still no answer: no new event' ($null -eq (Step-LagState $s -1 $t0.AddSeconds(3)))
Check 'slow (1000ms) still lagging'   ($null -eq (Step-LagState $s 1000 $t0.AddSeconds(4)))
Check 'medium answer keeps lag going' ($null -eq (Step-LagState $s 700 $t0.AddSeconds(5)))
Check 'fast answer ends the lag'      ('lag-end' -eq (Step-LagState $s 20 $t0.AddSeconds(9)))
Check 'not lagging after end'         (-not $s.Lagging)

$s = New-LagState
[void](Step-LagState $s -1 $t0)
Check 'short freeze is a hitch'       ('hitch' -eq (Step-LagState $s 10 $t0.AddMilliseconds(500)))
Check 'hitch counted'                 ($s.Hitches -eq 1)
[void](Step-LagState $s 400 $t0.AddSeconds(3))
Check 'slow answer counted'           ($s.SlowAnswers -eq 1)

# --- document name from the title bar ---
Check 'doc from title' ('Gift Message.indd' -eq (Get-DocumentFromTitle 'Adobe InDesign CC 2018 - [*Gift Message.indd @ 125%]'))
Check 'doc from tab'   ('EHS - 50 - FLAT.indd' -eq (Get-DocumentFromTitle '*EHS - 50 - FLAT.indd @ 100%'))
Check 'no doc'         ('' -eq (Get-DocumentFromTitle 'Adobe InDesign CC 2018'))

# --- plain-English verdict ---
$v = Get-LagVerdict -InDesignCorePct 95 -PcCpuMaxPct 40 -ReadMB 1 -WriteMB 0 -PrintJobs 0 -PrinterError $false -DriveRestarted $false -FreeRamMB 4000 -DiskBusyMaxPct 10 -ForegroundTitle ''
Check 'busy verdict'     ($v -match 'BUSY')
$v = Get-LagVerdict -InDesignCorePct 2 -PcCpuMaxPct 20 -ReadMB 0 -WriteMB 0 -PrintJobs 1 -PrinterError $true -DriveRestarted $false -FreeRamMB 4000 -DiskBusyMaxPct 10 -ForegroundTitle 'Print'
Check 'printer verdict'  ($v -match 'printer was showing an error' -and $v -match 'WAITING')
$v = Get-LagVerdict -InDesignCorePct 2 -PcCpuMaxPct 20 -ReadMB 0 -WriteMB 0 -PrintJobs 0 -PrinterError $false -DriveRestarted $true -FreeRamMB 600 -DiskBusyMaxPct 100 -ForegroundTitle ''
Check 'drive/ram/disk verdict' ($v -match 'Google Drive' -and $v -match 'out of memory' -and $v -match 'disk')
$v = Get-LagVerdict -InDesignCorePct 5 -PcCpuMaxPct 20 -ReadMB 150 -WriteMB 0 -PrintJobs 0 -PrinterError $false -DriveRestarted $false -FreeRamMB 4000 -DiskBusyMaxPct 10 -ForegroundTitle ''
Check 'io verdict'       ($v -match 'reading/writing')

# --- busiest other programs ---
$before = @{ 10 = @{ Name = 'a'; Cpu = 1.0 }; 11 = @{ Name = 'b'; Cpu = 5.0 }; 12 = @{ Name = 'InDesign'; Cpu = 0 } }
$after  = @{ 10 = @{ Name = 'a'; Cpu = 3.0 }; 11 = @{ Name = 'b'; Cpu = 5.5 }; 12 = @{ Name = 'InDesign'; Cpu = 9 }; 13 = @{ Name = 'new'; Cpu = 4 } }
$top = Get-TopCpu -Before $before -After $after -Seconds 2 -SkipId 12
Check 'top cpu order'     ($top.Count -eq 2 -and $top[0].Name -eq 'a')
Check 'top cpu skips InDesign' (-not ($top | Where-Object Name -eq 'InDesign'))

# --- log writing ---
Write-LagLog 'hello line' ([ordered]@{ type = 'test'; n = 1 })
$txt = Get-ChildItem $tmp -Filter 'Lag Log *.txt'
Check 'text log written'  ($txt -and (Get-Content $txt[0].FullName -Raw) -match 'hello line')
$j = Get-Content (Join-Path $tmp 'lag-events.jsonl') | Select-Object -Last 1 | ConvertFrom-Json
Check 'json log written'  ($j.type -eq 'test' -and $j.computer -eq $env:COMPUTERNAME)

# --- Windows only: real window calls ---
$onWindows = ($PSVersionTable.PSEdition -eq 'Desktop') -or ($IsWindows -eq $true)
if ($onWindows) {
    Initialize-Native
    Check 'ping no window = -2' (-2 -eq [MppLagNative]::Ping([IntPtr]::Zero, 500))
    Add-Type -AssemblyName System.Windows.Forms
    $f = New-Object System.Windows.Forms.Form
    $f.Text = 'Adobe InDesign CC 2018 - [x.indd @ 100%]'
    $f.Show(); [System.Windows.Forms.Application]::DoEvents()
    $ms = [MppLagNative]::Ping($f.Handle, 1000)
    Check "ping a live window answers ($ms ms)" ($ms -ge 0 -and $ms -lt 1000)
    Check 'window title read' ('x.indd' -eq (Get-DocumentFromTitle ([MppLagNative]::Title($f.Handle))))
    $f.Close()
    $proc = Get-Process -Id $PID
    $g = Get-GuiCounts $proc
    Check "GDI count read ($($g.Gdi))" ($g.Gdi -ge 0)
    $pr = Get-PrinterSnapshot
    Check "printer snapshot ($(@($pr.Printers).Count) printers, spooler $($pr.Spooler))" ($null -ne $pr)
    $pc = Get-PcSnapshot
    Check "pc snapshot (free RAM $($pc.FreeRamMB) MB)" ($pc.FreeRamMB -gt 0)
    Check 'own process io' ($null -ne (Get-ProcessIo $PID))

    # End to end: a fake "InDesign" window that freezes for 6 seconds.
    $fakeExe = Join-Path $tmp 'InDesignFake.exe'
    Copy-Item (Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe') $fakeExe
    $fakeScript = Join-Path $tmp 'fake.ps1'
    Set-Content -LiteralPath $fakeScript -Encoding UTF8 -Value @'
Add-Type -AssemblyName System.Windows.Forms
$f = New-Object System.Windows.Forms.Form
$f.Text = 'Adobe InDesign CC 2018 - [*Test Doc.indd @ 100%]'
$t = New-Object System.Windows.Forms.Timer
$t.Interval = 5000
$script:n = 0
# Busy loop, not Start-Sleep: a sleeping STA thread still answers sent messages.
$t.add_Tick({ $script:n++; if ($script:n -eq 1) { $end = [DateTime]::Now.AddSeconds(6); while ([DateTime]::Now -lt $end) { } } elseif ($script:n -ge 3) { $f.Close() } })
$t.Start()
[System.Windows.Forms.Application]::Run($f)
'@
    $e2eLogs = Join-Path $tmp 'e2e'
    $ps = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    $watcherScript = (Resolve-Path (Join-Path $here '..\LagWatcher.ps1')).Path
    $w = Start-Process $ps -PassThru -WindowStyle Hidden -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$watcherScript`"", '-ProcessName', 'InDesignFake', '-RunSeconds', '40', '-LogFolder', "`"$e2eLogs`"")
    Start-Sleep -Seconds 2
    # Hidden console, so the program's main window is the form (like InDesign's main window).
    $fake = Start-Process $fakeExe -PassThru -WindowStyle Hidden -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$fakeScript`"")
    $fake | Wait-Process -Timeout 60 -ErrorAction SilentlyContinue
    $w | Wait-Process -Timeout 60 -ErrorAction SilentlyContinue
    if (-not $w.HasExited) { Stop-Process -Id $w.Id -Force }
    $events = @()
    $jl = Join-Path $e2eLogs 'lag-events.jsonl'
    if (Test-Path $jl) { $events = @(Get-Content $jl | ForEach-Object { $_ | ConvertFrom-Json }) }
    Get-ChildItem $e2eLogs -Filter '*.txt' -ErrorAction SilentlyContinue | ForEach-Object { Get-Content $_.FullName | ForEach-Object { Write-Host "      | $_" } }
    $lagEvt = @($events | Where-Object { $_.type -eq 'lag' })
    Check 'e2e: watcher saw the program start' (@($events | Where-Object { $_.type -eq 'indesign_seen' }).Count -ge 1)
    Check 'e2e: one lag recorded' ($lagEvt.Count -eq 1)
    if ($lagEvt.Count -ge 1) {
        Check "e2e: lag length about 6s ($($lagEvt[0].seconds)s)" ($lagEvt[0].seconds -ge 4 -and $lagEvt[0].seconds -le 10)
        Check "e2e: document named ($($lagEvt[0].document))" ($lagEvt[0].document -eq 'Test Doc.indd')
        Check 'e2e: verdict written' ([string]$lagEvt[0].verdict -ne '')
    }
    Check 'e2e: program close recorded' (@($events | Where-Object { $_.type -eq 'indesign_closed' }).Count -ge 1)
    Check 'e2e: no watcher errors' (-not (Get-ChildItem $e2eLogs -Filter '*.txt' | Select-String 'watcher note'))
} else {
    Write-Host 'SKIP  Windows-only checks (not on Windows)'
}

Remove-Item -LiteralPath $tmp -Recurse -Force
if ($script:fails) { Write-Host "$($script:fails) test(s) failed" -ForegroundColor Red; exit 1 }
Write-Host 'All tests passed' -ForegroundColor Green
exit 0
