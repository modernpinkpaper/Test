<#
.SYNOPSIS
  InDesign Lag Watcher. Notices when InDesign freezes ("lags") and writes
  down what was going on at that moment.

.DESCRIPTION
  Every 2 seconds it sends InDesign's main window a harmless "are you there?"
  message (WM_NULL) and times the answer. If InDesign does not answer within
  1 second, a lag has started. While the lag lasts it samples, every second:
    - how hard InDesign is working (CPU) and how much memory it uses
    - how busy the whole PC is (CPU, free memory, disk)
  When InDesign answers again it writes one entry to the log with:
    - start, end and how long the lag lasted
    - the document in InDesign's title bar and the window that was on screen
    - whether InDesign was BUSY working or WAITING for something
    - how much InDesign read from / wrote to disk during the lag
    - the busiest other programs during the lag
    - printer status, print jobs in the queue, and the print spooler
    - whether Google Drive had just restarted
  Every 5 minutes it also writes a short health line (memory, GDI/USER
  objects, handles, free RAM, days since the PC was restarted).

  It only reads. It never changes InDesign, files or settings.

  Logs go to C:\MPP Lag Watcher\Logs (or %LOCALAPPDATA%\MPP Lag Watcher\Logs
  if C:\ can't be written to):
    Lag Log <date>.txt   easy to read
    lag-events.jsonl     the same details, one JSON line per event

.PARAMETER Install
  Copy this script to the install folder, make it start at log-on (Startup
  folder shortcut, no admin needed), put a "Lag Watcher Logs" shortcut on
  the Desktop, and start it now in the background.

.PARAMETER Uninstall
  Stop it and remove the Startup and Desktop shortcuts. Logs are kept.

.PARAMETER LogFolder
  Write logs here instead of the default.

.PARAMETER NoLoop
  Load the functions only (used by the tests).

.PARAMETER ProcessName
  Program to watch (default InDesign). Used by the tests.

.PARAMETER RunSeconds
  Stop after this many seconds (default: run forever). Used by the tests.
#>
[CmdletBinding()]
param(
    [switch]$Install,
    [switch]$Uninstall,
    [string]$LogFolder,
    [switch]$NoLoop,
    [string]$ProcessName = 'InDesign',
    [double]$RunSeconds = 0
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'

$script:Version        = '1.0.0'
$script:PollSeconds    = 2      # normal check interval
$script:LagTimeoutMs   = 1000   # no answer within this = lagging
$script:RecoveredMs    = 500    # answers faster than this = lag over
$script:MinLagSeconds  = 2      # shorter freezes are counted as "hitches" only
$script:HealthMinutes  = 5
$script:ProcessName    = $ProcessName

# ---------------------------------------------------------------- folders --

function Get-InstallFolder {
    $preferred = 'C:\MPP Lag Watcher'
    try {
        if (-not (Test-Path -LiteralPath $preferred)) {
            New-Item -ItemType Directory -Path $preferred -Force | Out-Null
        }
        $probe = Join-Path $preferred '.write-test'
        Set-Content -LiteralPath $probe -Value 'ok' -Encoding ASCII
        Remove-Item -LiteralPath $probe -Force
        return $preferred
    } catch {
        $fallback = Join-Path $env:LOCALAPPDATA 'MPP Lag Watcher'
        New-Item -ItemType Directory -Path $fallback -Force | Out-Null
        return $fallback
    }
}

function Get-LogFolder {
    if ($LogFolder) { $f = $LogFolder } else { $f = Join-Path (Get-InstallFolder) 'Logs' }
    if (-not (Test-Path -LiteralPath $f)) { New-Item -ItemType Directory -Path $f -Force | Out-Null }
    return $f
}

# ---------------------------------------------------------- Windows calls --

$script:NativeLoaded = $false
function Initialize-Native {
    if ($script:NativeLoaded) { return }
    if (-not ('MppLagNative' -as [type])) {
        Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Diagnostics;
using System.Runtime.InteropServices;
public static class MppLagNative {
    [DllImport("user32.dll", SetLastError = true)]
    static extern IntPtr SendMessageTimeout(IntPtr hWnd, uint msg, UIntPtr wParam, IntPtr lParam,
                                            uint flags, uint timeout, out UIntPtr result);
    [DllImport("user32.dll")] public static extern bool IsHungAppWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool IsWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int max);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    static extern int GetClassName(IntPtr hWnd, StringBuilder text, int max);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint pid);
    [DllImport("user32.dll")] public static extern uint GetGuiResources(IntPtr hProcess, uint flags);

    // Milliseconds the window took to answer, or -1 if it did not answer in time.
    public static int Ping(IntPtr hWnd, uint timeoutMs) {
        if (hWnd == IntPtr.Zero || !IsWindow(hWnd)) return -2;
        Stopwatch sw = Stopwatch.StartNew();
        UIntPtr r;
        // WM_NULL = 0, SMTO_ABORTIFHUNG = 0x2
        IntPtr ok = SendMessageTimeout(hWnd, 0, UIntPtr.Zero, IntPtr.Zero, 0x2, timeoutMs, out r);
        sw.Stop();
        if (ok == IntPtr.Zero) return -1;
        return (int)sw.ElapsedMilliseconds;
    }
    public static string Title(IntPtr hWnd) {
        StringBuilder sb = new StringBuilder(512); GetWindowText(hWnd, sb, 512); return sb.ToString();
    }
    public static string ClassOf(IntPtr hWnd) {
        StringBuilder sb = new StringBuilder(256); GetClassName(hWnd, sb, 256); return sb.ToString();
    }
    public static int ProcessOf(IntPtr hWnd) {
        uint pid; GetWindowThreadProcessId(hWnd, out pid); return (int)pid;
    }
}
'@
    }
    $script:NativeLoaded = $true
}

# -------------------------------------------------------- the lag "brain" --
# Kept free of Windows calls so it can be tested anywhere.

function New-LagState {
    [pscustomobject]@{
        Lagging     = $false
        Start       = $null
        LastBad     = $null
        Hitches     = 0      # freezes shorter than MinLagSeconds
        SlowAnswers = 0      # answered, but took 300-1000 ms
    }
}

# Feed one check result in. $PingMs: answer time in ms, -1 = no answer.
# Returns 'lag-start', 'lag-end', 'hitch' or $null.
function Step-LagState {
    param($State, [int]$PingMs, [datetime]$Now)
    $bad = ($PingMs -lt 0) -or ($PingMs -ge $script:LagTimeoutMs)
    if ($bad) {
        $State.LastBad = $Now
        if (-not $State.Lagging) {
            $State.Lagging = $true
            # It went silent at least LagTimeoutMs before we gave up waiting.
            $State.Start = $Now.AddMilliseconds(-1 * $script:LagTimeoutMs)
            return 'lag-start'
        }
        return $null
    }
    if ($PingMs -ge 300) { $State.SlowAnswers++ }
    if ($State.Lagging -and $PingMs -lt $script:RecoveredMs) {
        $State.Lagging = $false
        $seconds = ($Now - $State.Start).TotalSeconds
        if ($seconds -lt $script:MinLagSeconds) {
            $State.Hitches++
            return 'hitch'
        }
        return 'lag-end'
    }
    return $null
}

# Plain-English reading of what InDesign was doing.
function Get-LagVerdict {
    param([double]$InDesignCorePct, [double]$PcCpuMaxPct, [double]$ReadMB,
          [double]$WriteMB, [int]$PrintJobs, [bool]$PrinterError,
          [bool]$DriveRestarted, [double]$FreeRamMB, [double]$DiskBusyMaxPct,
          [string]$ForegroundTitle)
    $why = New-Object System.Collections.Generic.List[string]
    if ($DriveRestarted) { $why.Add('Google Drive restarted just before this - InDesign may have been waiting on a G: file or link.') }
    if ($PrintJobs -gt 0 -or $ForegroundTitle -match '(?i)\bprint') {
        if ($PrinterError) { $why.Add('Printing was going on and a printer was showing an error - InDesign often freezes while it waits on a printer.') }
        else { $why.Add('Printing was going on at the time.') }
    } elseif ($PrinterError) {
        $why.Add('A printer was showing an error (not printing at that moment).')
    }
    if ($FreeRamMB -gt 0 -and $FreeRamMB -lt 1024) { $why.Add(('The PC was almost out of memory ({0:N0} MB free).' -f $FreeRamMB)) }
    if ($InDesignCorePct -ge 60) {
        $why.Add(('InDesign was BUSY working (about {0:N0}% of one CPU core) - something in the document or a script was heavy.' -f $InDesignCorePct))
    } elseif (($ReadMB + $WriteMB) -ge 20) {
        $why.Add(('InDesign was reading/writing a lot ({0:N0} MB) - loading images, fonts or saving.' -f ($ReadMB + $WriteMB)))
    } else {
        $why.Add('InDesign was WAITING, not working (low CPU) - usually a printer, a network/G: file, a font or another program.')
    }
    if ($PcCpuMaxPct -ge 90 -and $InDesignCorePct -lt 60) { $why.Add('The whole PC was very busy with other programs.') }
    if ($DiskBusyMaxPct -ge 90) { $why.Add('The disk was 100% busy.') }
    return ($why -join ' ')
}

# ------------------------------------------------------------ measurements --

function Get-SafeCim {
    param([string]$Class, [string]$Filter, [int]$Timeout = 5)
    try {
        if ($Filter) { return @(Get-CimInstance -ClassName $Class -Filter $Filter -OperationTimeoutSec $Timeout -ErrorAction Stop) }
        return @(Get-CimInstance -ClassName $Class -OperationTimeoutSec $Timeout -ErrorAction Stop)
    } catch { return @() }
}

function Get-PcSnapshot {
    $o = [ordered]@{ CpuPct = -1; FreeRamMB = -1; DiskBusyPct = -1 }
    $cpu = Get-SafeCim 'Win32_PerfFormattedData_PerfOS_Processor' "Name='_Total'" 3
    if ($cpu) { $o.CpuPct = [double]$cpu[0].PercentProcessorTime }
    $mem = Get-SafeCim 'Win32_PerfFormattedData_PerfOS_Memory' $null 3
    if ($mem) { $o.FreeRamMB = [double]$mem[0].AvailableMBytes }
    $disk = Get-SafeCim 'Win32_PerfFormattedData_PerfDisk_PhysicalDisk' "Name='_Total'" 3
    if ($disk) { $o.DiskBusyPct = [math]::Min(100, [double]$disk[0].PercentDiskTime) }
    [pscustomobject]$o
}

function Get-ProcessIo {
    param([int]$ProcessId)
    $p = Get-SafeCim 'Win32_Process' "ProcessId=$ProcessId" 3
    if (-not $p) { return $null }
    [pscustomobject]@{ Read = [double]$p[0].ReadTransferCount; Write = [double]$p[0].WriteTransferCount }
}

function Get-CpuTimes {
    $h = @{}
    foreach ($p in Get-Process -ErrorAction SilentlyContinue) {
        try { $h[$p.Id] = @{ Name = $p.ProcessName; Cpu = $p.TotalProcessorTime.TotalSeconds } } catch { }
    }
    return $h
}

function Get-TopCpu {
    param($Before, $After, [double]$Seconds, [int]$SkipId, [int]$Count = 5)
    $cores = [Environment]::ProcessorCount
    $rows = foreach ($id in $After.Keys) {
        if ($id -eq $SkipId -or $id -eq $PID -or $id -eq 0) { continue }
        if (-not $Before.ContainsKey($id)) { continue }
        $d = $After[$id].Cpu - $Before[$id].Cpu
        if ($d -le 0) { continue }
        [pscustomobject]@{ Name = $After[$id].Name; Pct = [math]::Round(100 * $d / [math]::Max(0.5, $Seconds) / $cores, 1) }
    }
    @($rows | Sort-Object Pct -Descending | Select-Object -First $Count)
}

function Get-PrinterSnapshot {
    $printers = foreach ($p in (Get-SafeCim 'Win32_Printer' $null 5)) {
        $state = 'OK'
        $err = [int]$p.DetectedErrorState
        $errNames = @{ 0='OK';1='Other';2='OK';3='Low paper';4='No paper';5='Low toner';6='No toner';7='Door open';8='Jammed';9='Offline';10='Service requested';11='Output bin full' }
        if ($p.WorkOffline) { $state = 'Offline' }
        elseif ($err -gt 2 -and $errNames.ContainsKey($err)) { $state = $errNames[$err] }
        elseif ([int]$p.PrinterStatus -eq 7) { $state = 'Offline' }
        [pscustomobject]@{ Name = [string]$p.Name; State = $state; Error = ($state -ne 'OK') }
    }
    $jobs = @(Get-SafeCim 'Win32_PrintJob' $null 5)
    $spooler = 'unknown'
    try { $spooler = [string](Get-Service -Name Spooler -ErrorAction Stop).Status } catch { }
    [pscustomobject]@{
        Printers = @($printers)
        Jobs     = @($jobs | ForEach-Object { [pscustomobject]@{ Printer = ([string]$_.Name -split ',')[0]; Document = [string]$_.Document; Status = [string]$_.JobStatus } })
        Spooler  = $spooler
    }
}

function Test-DriveJustRestarted {
    param([datetime]$Since)
    foreach ($p in Get-Process -Name GoogleDriveFS -ErrorAction SilentlyContinue) {
        try { if ($p.StartTime -ge $Since) { return $true } } catch { }
    }
    return $false
}

function Get-GuiCounts {
    param($Process)
    try {
        $h = $Process.Handle
        return [pscustomobject]@{ Gdi = [int][MppLagNative]::GetGuiResources($h, 0); User = [int][MppLagNative]::GetGuiResources($h, 1) }
    } catch { return [pscustomobject]@{ Gdi = -1; User = -1 } }
}

function Get-ForegroundInfo {
    try {
        $fg = [MppLagNative]::GetForegroundWindow()
        $fgPid = [MppLagNative]::ProcessOf($fg)
        $name = ''
        try { $name = (Get-Process -Id $fgPid -ErrorAction Stop).ProcessName } catch { }
        [pscustomobject]@{ Title = [MppLagNative]::Title($fg); Class = [MppLagNative]::ClassOf($fg); Process = $name }
    } catch { [pscustomobject]@{ Title = ''; Class = ''; Process = '' } }
}

function Get-DocumentFromTitle {
    param([string]$Title)
    if (-not $Title) { return '' }
    $m = [regex]::Match($Title, '([^\\/\[\]]+?\.(?:indd|indt|idml))(?:\s*@\s*\d+%)?', 'IgnoreCase')
    if ($m.Success) { return $m.Groups[1].Value.TrimStart('*') }
    return ''
}

# ----------------------------------------------------------------- logging --

function Write-LagLog {
    param([string]$Text, $Json)
    $folder = Get-LogFolder
    $day = (Get-Date).ToString('yyyy-MM-dd')
    $txt = Join-Path $folder ("Lag Log $day.txt")
    try { Add-Content -LiteralPath $txt -Value $Text -Encoding UTF8 } catch { }
    if ($Json) {
        $Json['computer'] = $env:COMPUTERNAME
        $Json['watcher_version'] = $script:Version
        $line = ($Json | ConvertTo-Json -Depth 6 -Compress)
        try { Add-Content -LiteralPath (Join-Path $folder 'lag-events.jsonl') -Value $line -Encoding UTF8 } catch { }
    }
}

function Format-Mb([double]$bytes) { '{0:N0}' -f ($bytes / 1MB) }

function Get-UptimeDays {
    $os = Get-SafeCim 'Win32_OperatingSystem' $null 3
    if (-not $os) { return -1 }
    return [math]::Round(((Get-Date) - $os[0].LastBootUpTime).TotalDays, 1)
}

# ---------------------------------------------------------------- the loop --

function Invoke-LagWatcher {
    Initialize-Native
    $mutex = New-Object System.Threading.Mutex($false, 'Local\MppInDesignLagWatcher')
    if (-not $mutex.WaitOne(0)) { return }   # already running

    $now = Get-Date
    Write-LagLog ("[{0}] Lag Watcher {1} started on {2}. PC last restarted {3} days ago." -f $now.ToString('HH:mm:ss'), $script:Version, $env:COMPUTERNAME, (Get-UptimeDays)) @{ type = 'watcher_started'; time = $now.ToString('o') }

    $state = New-LagState
    $currentPid = 0; $procStart = $null
    $nextHealth = Get-Date
    $lag = $null
    $lastHwnd = [IntPtr]::Zero

    $watchStart = Get-Date
    while ($true) {
        $loopStart = Get-Date
        if ($RunSeconds -gt 0 -and ($loopStart - $watchStart).TotalSeconds -ge $RunSeconds) { break }
        try {
            $p = Get-Process -Name $script:ProcessName -ErrorAction SilentlyContinue | Sort-Object StartTime | Select-Object -First 1
            if (-not $p) {
                if ($currentPid) {
                    $mins = 0; if ($procStart) { $mins = [math]::Round(((Get-Date) - $procStart).TotalMinutes) }
                    $wer = @(Get-Process -Name WerFault -ErrorAction SilentlyContinue).Count -gt 0
                    $how = 'closed'; if ($wer) { $how = 'closed (Windows error reporting was running - probably a crash)' }
                    Write-LagLog ("[{0}] InDesign {1} after {2} min. Freezes today so far are listed above." -f (Get-Date).ToString('HH:mm:ss'), $how, $mins) @{ type = 'indesign_closed'; time = (Get-Date).ToString('o'); minutes = $mins; werfault = $wer; was_lagging = $state.Lagging }
                    $currentPid = 0; $state = New-LagState; $lag = $null
                }
                Start-Sleep -Seconds 5
                continue
            }
            if ($p.Id -ne $currentPid) {
                $currentPid = $p.Id
                $lastHwnd = [IntPtr]::Zero
                try { $procStart = $p.StartTime } catch { $procStart = Get-Date }
                $state = New-LagState; $lag = $null
                Write-LagLog ("[{0}] InDesign is running (started {1})." -f (Get-Date).ToString('HH:mm:ss'), $procStart.ToString('HH:mm:ss')) @{ type = 'indesign_seen'; time = (Get-Date).ToString('o'); process_start = $procStart.ToString('o') }
                $nextHealth = (Get-Date).AddMinutes(1)
            }

            # When InDesign hangs, Windows swaps in a "ghost" window and InDesign's
            # main window can disappear from MainWindowHandle. Keep using the last one.
            $hwnd = $p.MainWindowHandle
            if ($hwnd -eq [IntPtr]::Zero -and $lastHwnd -ne [IntPtr]::Zero -and [MppLagNative]::IsWindow($lastHwnd)) { $hwnd = $lastHwnd }
            if ($hwnd -ne [IntPtr]::Zero) { $lastHwnd = $hwnd }
            $ms = [MppLagNative]::Ping($hwnd, [uint32]$script:LagTimeoutMs)
            if ($ms -eq -2) { Start-Sleep -Seconds $script:PollSeconds; continue }  # no main window yet (splash/loading)
            $now = Get-Date
            $evt = Step-LagState -State $state -PingMs $ms -Now $now

            if ($evt -eq 'lag-start') {
                $fg = Get-ForegroundInfo
                $lag = [ordered]@{
                    Start = $state.Start; Title = [MppLagNative]::Title($hwnd); Foreground = $fg
                    CpuBefore = Get-CpuTimes; IoBefore = Get-ProcessIo $p.Id
                    IdCpuStart = $p.TotalProcessorTime.TotalSeconds; IdCpuSamples = New-Object System.Collections.Generic.List[double]
                    LastIdCpu = $p.TotalProcessorTime.TotalSeconds; LastSample = $now
                    PcCpuMax = 0; FreeRamMin = [double]::MaxValue; DiskMax = 0; PrivMaxMB = 0
                    Printers = Get-PrinterSnapshot
                    DriveRestart = Test-DriveJustRestarted -Since $state.Start.AddMinutes(-2)
                    Gui = Get-GuiCounts $p
                }
            }

            if ($state.Lagging -and $lag) {
                try {
                    $p.Refresh()
                    $nowCpu = $p.TotalProcessorTime.TotalSeconds
                    $dt = ($now - $lag.LastSample).TotalSeconds
                    if ($dt -gt 0.2) { $lag.IdCpuSamples.Add(100 * ($nowCpu - $lag.LastIdCpu) / $dt) }
                    $lag.LastIdCpu = $nowCpu; $lag.LastSample = $now
                    $lag.PrivMaxMB = [math]::Max($lag.PrivMaxMB, $p.PrivateMemorySize64 / 1MB)
                } catch { }
                $pc = Get-PcSnapshot
                if ($pc.CpuPct -ge 0) { $lag.PcCpuMax = [math]::Max($lag.PcCpuMax, $pc.CpuPct) }
                if ($pc.FreeRamMB -ge 0) { $lag.FreeRamMin = [math]::Min($lag.FreeRamMin, $pc.FreeRamMB) }
                if ($pc.DiskBusyPct -ge 0) { $lag.DiskMax = [math]::Max($lag.DiskMax, $pc.DiskBusyPct) }
            }

            if ($evt -eq 'lag-end' -and $lag) {
                $end = $now
                $secs = [math]::Round(($end - $lag.Start).TotalSeconds, 1)
                $p.Refresh()
                $idAvg = 0
                $wall = ($end - $lag.Start).TotalSeconds
                if ($wall -gt 0) { $idAvg = [math]::Round(100 * ($p.TotalProcessorTime.TotalSeconds - $lag.IdCpuStart) / $wall, 0) }
                $idMax = 0; if ($lag.IdCpuSamples.Count) { $idMax = [math]::Round(($lag.IdCpuSamples | Measure-Object -Maximum).Maximum, 0) }
                $ioAfter = Get-ProcessIo $p.Id
                $readMB = 0; $writeMB = 0
                if ($lag.IoBefore -and $ioAfter) { $readMB = ($ioAfter.Read - $lag.IoBefore.Read) / 1MB; $writeMB = ($ioAfter.Write - $lag.IoBefore.Write) / 1MB }
                $top = Get-TopCpu -Before $lag.CpuBefore -After (Get-CpuTimes) -Seconds $wall -SkipId $p.Id
                $freeMin = $lag.FreeRamMin; if ($freeMin -eq [double]::MaxValue) { $freeMin = -1 }
                $prnErr = @($lag.Printers.Printers | Where-Object { $_.Error }).Count -gt 0
                $doc = Get-DocumentFromTitle $lag.Title
                $verdict = Get-LagVerdict -InDesignCorePct $idAvg -PcCpuMaxPct $lag.PcCpuMax -ReadMB $readMB -WriteMB $writeMB `
                    -PrintJobs $lag.Printers.Jobs.Count -PrinterError $prnErr -DriveRestarted $lag.DriveRestart `
                    -FreeRamMB $freeMin -DiskBusyMaxPct $lag.DiskMax -ForegroundTitle $lag.Foreground.Title

                $sb = New-Object System.Text.StringBuilder
                [void]$sb.AppendLine('')
                [void]$sb.AppendLine(("[{0}] LAG {1} seconds  ({2} to {3})" -f $end.ToString('HH:mm:ss'), $secs, $lag.Start.ToString('HH:mm:ss'), $end.ToString('HH:mm:ss')))
                if ($doc) { [void]$sb.AppendLine("  Document:   $doc") } else { [void]$sb.AppendLine("  InDesign title: $($lag.Title)") }
                [void]$sb.AppendLine(("  On screen:  ""{0}"" ({1})" -f $lag.Foreground.Title, $lag.Foreground.Process))
                [void]$sb.AppendLine("  Why (best guess): $verdict")
                [void]$sb.AppendLine(("  InDesign:   CPU avg {0}% / max {1}% of one core, memory up to {2:N0} MB, GDI objects {3}, USER objects {4}" -f $idAvg, $idMax, $lag.PrivMaxMB, $lag.Gui.Gdi, $lag.Gui.User))
                [void]$sb.AppendLine(("  InDesign read {0:N1} MB and wrote {1:N1} MB during the lag" -f $readMB, $writeMB))
                [void]$sb.AppendLine(("  Whole PC:   CPU max {0:N0}%, free memory min {1:N0} MB, disk busy max {2:N0}%" -f $lag.PcCpuMax, $freeMin, $lag.DiskMax))
                if ($top.Count) { [void]$sb.AppendLine("  Busiest other programs: " + (($top | ForEach-Object { "$($_.Name) $($_.Pct)%" }) -join ', ')) }
                $pr = ($lag.Printers.Printers | ForEach-Object { "$($_.Name) = $($_.State)" }) -join '; '
                [void]$sb.AppendLine("  Printers:   $pr")
                [void]$sb.AppendLine(("  Print queue: {0} job(s); print spooler {1}" -f $lag.Printers.Jobs.Count, $lag.Printers.Spooler))
                if ($lag.DriveRestart) { [void]$sb.AppendLine('  Google Drive: RESTARTED within 2 minutes before this lag') }

                Write-LagLog $sb.ToString().TrimEnd() ([ordered]@{
                    type = 'lag'; start = $lag.Start.ToString('o'); end = $end.ToString('o'); seconds = $secs
                    document = $doc; indesign_title = $lag.Title
                    foreground = @{ title = $lag.Foreground.Title; class = $lag.Foreground.Class; process = $lag.Foreground.Process }
                    indesign_cpu_avg_core_pct = $idAvg; indesign_cpu_max_core_pct = $idMax
                    indesign_private_mb_max = [math]::Round($lag.PrivMaxMB); gdi = $lag.Gui.Gdi; user_objects = $lag.Gui.User
                    read_mb = [math]::Round($readMB, 1); write_mb = [math]::Round($writeMB, 1)
                    pc_cpu_max_pct = $lag.PcCpuMax; free_ram_min_mb = $freeMin; disk_busy_max_pct = $lag.DiskMax
                    top_processes = @($top); printers = @($lag.Printers.Printers); print_jobs = @($lag.Printers.Jobs)
                    spooler = $lag.Printers.Spooler; drive_restarted = $lag.DriveRestart; verdict = $verdict
                })
                $lag = $null
            } elseif ($evt -eq 'hitch') {
                $lag = $null
            }

            if (-not $state.Lagging -and (Get-Date) -ge $nextHealth) {
                $p.Refresh()
                $gui = Get-GuiCounts $p
                $pc = Get-PcSnapshot
                $title = [MppLagNative]::Title($hwnd)
                $line = ("[{0}] health: InDesign memory {1:N0} MB, GDI {2}, USER {3}, handles {4}, threads {5} | PC free memory {6:N0} MB, CPU {7:N0}% | short hitches (<{8}s) since last line: {9}, slow answers: {10} | {11}" -f `
                    (Get-Date).ToString('HH:mm:ss'), ($p.PrivateMemorySize64 / 1MB), $gui.Gdi, $gui.User, $p.HandleCount, $p.Threads.Count,
                    $pc.FreeRamMB, $pc.CpuPct, $script:MinLagSeconds, $state.Hitches, $state.SlowAnswers, (Get-DocumentFromTitle $title))
                Write-LagLog $line ([ordered]@{
                    type = 'health'; time = (Get-Date).ToString('o'); private_mb = [math]::Round($p.PrivateMemorySize64 / 1MB)
                    gdi = $gui.Gdi; user_objects = $gui.User; handles = $p.HandleCount; threads = $p.Threads.Count
                    free_ram_mb = $pc.FreeRamMB; pc_cpu_pct = $pc.CpuPct; hitches = $state.Hitches; slow_answers = $state.SlowAnswers
                    document = (Get-DocumentFromTitle $title)
                })
                $state.Hitches = 0; $state.SlowAnswers = 0
                $nextHealth = (Get-Date).AddMinutes($script:HealthMinutes)
            }
        } catch {
            try { Write-LagLog ("[{0}] (watcher note: {1})" -f (Get-Date).ToString('HH:mm:ss'), $_.Exception.Message) $null } catch { }
            Start-Sleep -Seconds 5
        }

        # While lagging, check every second; otherwise every PollSeconds.
        $interval = $script:PollSeconds; if ($state.Lagging) { $interval = 1 }
        $left = $interval - ((Get-Date) - $loopStart).TotalSeconds
        if ($left -gt 0) { Start-Sleep -Milliseconds ([int]($left * 1000)) }
    }
}

# ------------------------------------------------------- install / remove --

function Stop-OtherWatchers {
    foreach ($proc in (Get-SafeCim 'Win32_Process' "Name='powershell.exe' OR Name='pwsh.exe'" 5)) {
        if ($proc.ProcessId -ne $PID -and [string]$proc.CommandLine -match 'LagWatcher\.ps1' -and [string]$proc.CommandLine -notmatch '-(Install|Uninstall)') {
            try { Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop } catch { }
        }
    }
}

function Get-ShortcutPaths {
    [pscustomobject]@{
        Startup = Join-Path ([Environment]::GetFolderPath('Startup')) 'MPP InDesign Lag Watcher.lnk'
        Desktop = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Lag Watcher Logs.lnk'
    }
}

function Install-LagWatcher {
    $dest = Get-InstallFolder
    $target = Join-Path $dest 'LagWatcher.ps1'
    if ($PSCommandPath -and ((Resolve-Path -LiteralPath $PSCommandPath).Path -ne $target)) {
        Copy-Item -LiteralPath $PSCommandPath -Destination $target -Force
    }
    $logs = Join-Path $dest 'Logs'
    New-Item -ItemType Directory -Path $logs -Force | Out-Null

    Stop-OtherWatchers
    $ps = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    $psArgs = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$target`""
    $sh = New-Object -ComObject WScript.Shell
    $paths = Get-ShortcutPaths
    $lnk = $sh.CreateShortcut($paths.Startup)
    $lnk.TargetPath = $ps; $lnk.Arguments = $psArgs; $lnk.WorkingDirectory = $dest
    $lnk.WindowStyle = 7; $lnk.Description = 'Watches for InDesign freezes'
    $lnk.Save()
    $lnk2 = $sh.CreateShortcut($paths.Desktop)
    $lnk2.TargetPath = $logs; $lnk2.Description = 'InDesign Lag Watcher logs'
    $lnk2.Save()

    Start-Process -FilePath $ps -ArgumentList $psArgs -WindowStyle Hidden -WorkingDirectory $dest
    Write-Host ''
    Write-Host 'InDesign Lag Watcher is ON.' -ForegroundColor Green
    Write-Host '  It runs quietly in the background and starts again by itself after a restart.'
    Write-Host "  Logs: $logs"
    Write-Host '  A "Lag Watcher Logs" shortcut is on the Desktop.'
    Write-Host ''
}

function Uninstall-LagWatcher {
    Stop-OtherWatchers
    $paths = Get-ShortcutPaths
    foreach ($f in @($paths.Startup, $paths.Desktop)) { if (Test-Path -LiteralPath $f) { Remove-Item -LiteralPath $f -Force } }
    Write-Host ''
    Write-Host 'InDesign Lag Watcher is OFF. The logs were kept.' -ForegroundColor Yellow
    Write-Host ''
}

# -------------------------------------------------------------------- main --

if ($NoLoop) { return }
if ($Install)   { Install-LagWatcher; return }
if ($Uninstall) { Uninstall-LagWatcher; return }
Invoke-LagWatcher
