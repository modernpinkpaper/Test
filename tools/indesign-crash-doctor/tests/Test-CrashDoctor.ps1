# Self-contained tests for InDesignCrashDoctor.ps1 (no Pester needed).
# Builds small fake crash files, reads them back, and checks the verdict and report.
# Run:  powershell -NoProfile -ExecutionPolicy Bypass -File tools\indesign-crash-doctor\tests\Test-CrashDoctor.ps1
$ErrorActionPreference = 'Stop'
if (-not $env:windir) { $env:windir = 'C:\Windows' }

. (Join-Path $PSScriptRoot '..\InDesignCrashDoctor.ps1')

$script:Failed = 0
function Assert($Condition, [string]$Message) {
    if ($Condition) { Write-Host "  ok   $Message" -ForegroundColor Green }
    else { Write-Host "  FAIL $Message" -ForegroundColor Red; $script:Failed++ }
}

$work = Join-Path ([System.IO.Path]::GetTempPath()) ('crashdoctor-test-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $work | Out-Null

# ---------- fake minidump writer (x64 layout, same structures Windows uses) ----------
function New-FakeDump([string]$Path, [int64]$Code, [uint64]$ExcAddr, [uint64[]]$Params, [uint64]$Rip, [uint64[]]$Stack, $Modules, [uint32]$Stamp) {
    $ms = New-Object System.IO.MemoryStream
    $w = New-Object System.IO.BinaryWriter($ms)
    $w.Write([byte[]]::new(32))
    $dirRva = 32
    $w.Write([byte[]]::new(12 * 4))
    $align = { while ($ms.Position % 8) { $w.Write([byte]0) } }
    $rvaSys = [uint32]$ms.Position; $w.Write([uint16]9); $w.Write([byte[]]::new(54)); & $align
    $nameRvas = @()
    foreach ($m in $Modules) {
        $nameRvas += [uint32]$ms.Position
        $b = [System.Text.Encoding]::Unicode.GetBytes($m.Path)
        $w.Write([uint32]$b.Length); $w.Write($b); $w.Write([uint16]0); & $align
    }
    $rvaMods = [uint32]$ms.Position
    $w.Write([uint32]$Modules.Count)
    for ($i = 0; $i -lt $Modules.Count; $i++) {
        $m = $Modules[$i]
        $w.Write([uint64]$m.Base); $w.Write([uint32]$m.Size); $w.Write([uint32]0); $w.Write([uint32]0); $w.Write([uint32]$nameRvas[$i])
        $w.Write([uint32]0xFEEF04BDL); $w.Write([uint32]0x10000)
        $w.Write([uint32](($m.V[0] -shl 16) -bor $m.V[1])); $w.Write([uint32](($m.V[2] -shl 16) -bor $m.V[3]))
        $w.Write([byte[]]::new(68))
    }
    $modsSize = [uint32]($ms.Position - $rvaMods); & $align
    $stackStart = [uint64]0x10000000
    $rvaStack = [uint32]$ms.Position
    foreach ($v in $Stack) { $w.Write([uint64]$v) }
    & $align
    $rvaCtx = [uint32]$ms.Position
    $ctx = [byte[]]::new(0x4d0)
    [BitConverter]::GetBytes([uint64]$stackStart).CopyTo($ctx, 0x98)
    [BitConverter]::GetBytes([uint64]$Rip).CopyTo($ctx, 0xF8)
    $w.Write($ctx)
    $rvaThreads = [uint32]$ms.Position
    $w.Write([uint32]1); $w.Write([uint32]1234); $w.Write([uint32]0); $w.Write([uint32]0); $w.Write([uint32]0); $w.Write([uint64]0)
    $w.Write([uint64]$stackStart); $w.Write([uint32]($Stack.Count * 8)); $w.Write($rvaStack)
    $w.Write([uint32]0x4d0); $w.Write($rvaCtx)
    $threadsSize = [uint32]($ms.Position - $rvaThreads); & $align
    $rvaExc = [uint32]$ms.Position
    $w.Write([uint32]1234); $w.Write([uint32]0); $w.Write([uint32]$Code); $w.Write([uint32]1); $w.Write([uint64]0); $w.Write([uint64]$ExcAddr)
    $w.Write([uint32]$Params.Count); $w.Write([uint32]0)
    for ($i = 0; $i -lt 15; $i++) { if ($i -lt $Params.Count) { $w.Write([uint64]$Params[$i]) } else { $w.Write([uint64]0) } }
    $w.Write([uint32]0x4d0); $w.Write($rvaCtx)
    $excSize = [uint32]($ms.Position - $rvaExc)
    # header + directory
    $ms.Position = 0
    $w.Write([System.Text.Encoding]::ASCII.GetBytes('MDMP')); $w.Write([uint32]0xa793); $w.Write([uint32]4); $w.Write([uint32]$dirRva); $w.Write([uint32]0); $w.Write($Stamp); $w.Write([uint64]0)
    foreach ($s in @(@(7, 56, $rvaSys), @(4, $modsSize, $rvaMods), @(3, $threadsSize, $rvaThreads), @(6, $excSize, $rvaExc))) {
        $w.Write([uint32]$s[0]); $w.Write([uint32]$s[1]); $w.Write([uint32]$s[2])
    }
    [System.IO.File]::WriteAllBytes($Path, $ms.ToArray())
}

$ID = [uint64]0x140000000; $KB = [uint64]0x7ff810000000; $UC = [uint64]0x7ff850000000
$TX = [uint64]0x7ff820000000; $CT = [uint64]0x7ff840000000; $EV = [uint64]0x7ff830000000
$mods = @(
    @{ Base = $ID; Size = 0x1000000; Path = 'C:\Program Files\Adobe\Adobe InDesign 2025\InDesign.exe'; V = @(20, 5, 0, 48) },
    @{ Base = [uint64]0x7ff800000000; Size = 0x200000; Path = 'C:\Windows\System32\ntdll.dll'; V = @(10, 0, 22621, 1) },
    @{ Base = $KB; Size = 0x400000; Path = 'C:\Windows\System32\KERNELBASE.dll'; V = @(10, 0, 22621, 1) },
    @{ Base = $UC; Size = 0x100000; Path = 'C:\Windows\System32\ucrtbase.dll'; V = @(10, 0, 22621, 1) },
    @{ Base = $TX; Size = 0x800000; Path = 'C:\Program Files\Adobe\Adobe InDesign 2025\Required\Text.rpln'; V = @(20, 5, 0, 48) },
    @{ Base = $CT; Size = 0x800000; Path = 'C:\Program Files\Adobe\Adobe InDesign 2025\CoolType.dll'; V = @(5, 14, 0, 1) },
    @{ Base = $EV; Size = 0x100000; Path = 'C:\Program Files\Adobe\Adobe InDesign 2025\Plug-Ins\Acme\AcmeImposer.pln'; V = @(3, 2, 1, 0) }
)

Write-Host 'Crash file reader'
$cppPath = Join-Path $work 'cpp.dmp'
New-FakeDump $cppPath 0xe06d7363L ($KB + 0x5000) @(0x19930520, 0x1234, ($EV + 0x9000), $EV) ($KB + 0x5000) `
    @(($KB + 0x5010), 0xdeadbeefL, ($UC + 0x3000), ($UC + 0x3000), ($EV + 0x2345), 0, ($TX + 0x1234), ($TX + 0x2000), 5, ($ID + 0x3000), ($ID + 0x10)) $mods 1790000000
$d = Read-MiniDump $cppPath
Assert ($null -ne $d) 'reads a crash file'
Assert $d.IsInDesign 'knows it is an InDesign crash'
Assert ($d.ExceptionCode -eq '0xe06d7363') "error code is read ($($d.ExceptionCode))"
Assert ($d.Module -eq 'KERNELBASE.dll') "crash place is found ($($d.Module))"
Assert ($d.ThrownBy -eq 'AcmeImposer.pln') "C++ error is traced to the module that raised it ($($d.ThrownBy))"
Assert ($d.AppVersion -eq '20.5.0.48') "InDesign version is read ($($d.AppVersion))"
$expected = 'KERNELBASE.dll,ucrtbase.dll,AcmeImposer.pln,Text.rpln,InDesign.exe'
Assert (($d.Chain -join ',') -eq $expected) "call chain is walked in order ($($d.Chain -join ','))"
Assert ($d.Time -eq ([DateTimeOffset]::FromUnixTimeSeconds(1790000000)).LocalDateTime) 'crash time is read'

$avPath = Join-Path $work 'av.dmp'
New-FakeDump $avPath 0xc0000005L ($CT + 0x4444) @(0, 0x18) ($CT + 0x4444) @(($CT + 0x5000), ($TX + 0x1234), 0x42, ($TX + 0x3000), ($ID + 0x3000)) $mods 1790100000
$a = Read-MiniDump $avPath
Assert ($a.Module -eq 'CoolType.dll') "access violation place is found ($($a.Module))"
Assert ($a.Offset -eq '0x4444') "offset is worked out ($($a.Offset))"
Assert ($a.ExceptionDetail -match 'null pointer') "null pointer is explained ($($a.ExceptionDetail))"
Assert (($a.Chain -join ',') -eq 'CoolType.dll,Text.rpln,InDesign.exe') "chain for access violation ($($a.Chain -join ','))"

$junk = Join-Path $work 'junk.dmp'
[System.IO.File]::WriteAllBytes($junk, [byte[]](1..100))
Assert ($null -eq (Read-MiniDump $junk)) 'ignores files that are not crash files'

Write-Host 'Windows Error Reporting file'
$wer = Join-Path $work 'Report.wer'
$ft = ([datetime]'2026-09-20T14:03:00Z').ToFileTimeUtc()
@(
    'Version=1', 'EventType=APPCRASH', "EventTime=$ft",
    'Sig[0].Name=Application Name', 'Sig[0].Value=InDesign.exe',
    'Sig[1].Name=Application Version', 'Sig[1].Value=20.5.0.48',
    'Sig[3].Name=Fault Module Name', 'Sig[3].Value=nvoglv64.dll',
    'Sig[4].Name=Fault Module Version', 'Sig[4].Value=31.0.15.5222',
    'Sig[6].Name=Exception Code', 'Sig[6].Value=c0000005',
    'Sig[7].Name=Exception Offset', 'Sig[7].Value=00000000001a2b3c',
    'LoadedModule[0]=C:\Program Files\Adobe\Adobe InDesign 2025\InDesign.exe',
    'LoadedModule[1]=C:\Windows\System32\DriverStore\FileRepository\nv_dispi.inf_amd64\nvoglv64.dll',
    'LoadedModule[2]=C:\Program Files\SomeRecorder\hook64.dll'
) | Set-Content -LiteralPath $wer -Encoding Unicode
$r = Read-WerReport $wer
Assert ($r.Module -eq 'nvoglv64.dll') "fault module ($($r.Module))"
Assert ($r.ExceptionCode -eq '0xc0000005') "exception code ($($r.ExceptionCode))"
Assert ($r.ModulePath -match 'nv_dispi') 'fault module path is matched from loaded modules'
Assert ($r.LoadedModules.Count -eq 3) 'loaded modules are listed'
Assert ($r.Time -eq ([datetime]'2026-09-20T14:03:00Z').ToLocalTime()) 'event time is read'

Write-Host 'Knowledge'
Assert ((Get-ModuleKnowledge 'nvoglv64.dll').Kind -eq 'GPU') 'NVIDIA driver is recognised as graphics'
Assert ((Get-ModuleKnowledge 'CoolType.dll').Area -match 'Font') 'CoolType is recognised as fonts'
Assert ((Get-ModuleKnowledge 'Text.rpln').Area -match 'Text') 'Text.rpln is recognised as text layout'
Assert ((Get-ModuleKnowledge 'AcmeImposer.pln').Kind -eq 'ThirdParty') '.pln is recognised as third-party'
Assert ((Get-ModuleKnowledge 'Preflight Panel.apln').Area -match 'Preflight') 'Preflight plug-in recognised'
Assert ((Get-ModuleKnowledge 'ntdll.dll').Kind -eq 'Generic') 'ntdll is generic'
Assert ((Get-ExceptionText 'C0000374') -match 'Heap') 'exception code without 0x is explained'

Write-Host 'Merging and blame'
$items = @(
    [pscustomobject]@{ Time = $d.Time; Kind = 'Crash'; AppVersion = '20.5.0.48'; Module = 'KERNELBASE.dll'; ModuleVersion = ''; ModulePath = ''; ExceptionCode = '0xe06d7363'; Offset = ''; Sources = @('Windows Event Log'); Files = @() },
    [pscustomobject]@{ Time = $d.Time.AddSeconds(20); Kind = 'Crash'; AppVersion = $d.AppVersion; Module = $d.Module; ModulePath = $d.ModulePath; ModuleVersion = ''; ExceptionCode = $d.ExceptionCode; ExceptionDetail = ''; Offset = $d.Offset; ThrownBy = $d.ThrownBy; ThrownByPath = $d.ThrownByPath; Chain = $d.Chain; ChainPaths = $d.ChainPaths; LoadedModules = $d.LoadedModules; Sources = @('Crash file'); Files = @($cppPath) },
    [pscustomobject]@{ Time = $a.Time; Kind = 'Crash'; AppVersion = $a.AppVersion; Module = $a.Module; ModulePath = $a.ModulePath; ModuleVersion = ''; ExceptionCode = $a.ExceptionCode; ExceptionDetail = $a.ExceptionDetail; Offset = $a.Offset; ThrownBy = ''; ThrownByPath = ''; Chain = $a.Chain; ChainPaths = $a.ChainPaths; LoadedModules = $a.LoadedModules; Sources = @('Crash file'); Files = @($avPath) },
    [pscustomobject]@{ Time = $a.Time.AddDays(1); Kind = 'Freeze'; AppVersion = '20.5.0.48'; Module = ''; ModuleVersion = ''; ModulePath = ''; ExceptionCode = ''; Offset = ''; Sources = @('Windows Event Log (not responding)'); Files = @() }
)
$crashes = @(Merge-Crashes $items)
Assert ($crashes.Count -eq 3) "event log + crash file for the same crash are merged ($($crashes.Count) found)"
Assert (($crashes[0].Sources -join ',') -eq 'Windows Event Log,Crash file') 'sources are combined'
foreach ($c in $crashes) { Set-Blame $c }
Assert ($crashes[0].Blamed -eq 'AcmeImposer.pln') "third-party plug-in is blamed over KERNELBASE ($($crashes[0].Blamed))"
Assert ($crashes[1].Blamed -eq 'CoolType.dll') "font engine is blamed for the access violation ($($crashes[1].Blamed))"

Write-Host 'Verdict and report'
$crashes[0].Document = 'Catalog Fall.indd'; $crashes[1].Document = 'Catalog Fall.indd'
$changes = @([pscustomobject]@{ Time = $d.Time.AddDays(-2); Kind = 'Font added'; What = 'FancyScript.otf' })
$v = Get-Verdict $crashes $changes @() @() @() @() $false 90
$titles = ($v.Findings | ForEach-Object { $_.Title }) -join ' | '
Assert ($titles -match 'AcmeImposer\.pln') 'finding names the third-party plug-in'
Assert ($titles -match 'same document') 'finding notices the same document'
Assert ($titles -match 'changed in the week before') 'finding lists what changed before the first crash'
Assert (($v.Steps -join ' ') -match 'IDML') 'steps include rebuilding the document'
Assert (($v.Steps -join ' ') -match 'FancyScript') 'steps suggest undoing the new font'
$routine = @([pscustomobject]@{ Time = $d.Time.AddDays(-1); Kind = 'Windows update'; What = 'Security Intelligence Update for Microsoft Defender Antivirus - KB2267602 (Version 1.453.371.0)' },
             [pscustomobject]@{ Time = $d.Time.AddDays(-1); Kind = 'Windows update'; What = '9WZDNCRFJBMP-MICROSOFT.WINDOWSSTORE' })
$vr = Get-Verdict $crashes $routine @() @() @() @() $false 90
Assert ((($vr.Findings | ForEach-Object { $_.Title }) -join ' ') -notmatch 'changed in the week before') 'daily virus-list and Store updates are not reported as causes'
$mdObj = '{"document":{"name":"HNP004 weekly planner.indd","unsaved":false}}' | ConvertFrom-Json
Assert ((Get-Prop $mdObj 'document') -eq 'HNP004 weekly planner.indd') 'MT Log document objects show their name'
$empty = Get-Verdict @() @() @() @() @() @() $false 90
Assert ((($empty.Findings | ForEach-Object { $_.Title }) -join ' ') -match 'No crash records') 'no crashes gives a clear message'

$sum = Build-TextSummary $crashes $v ([ordered]@{ Windows = 'Test' }) @() $changes @() 90
Assert ($sum -match 'Call chain') 'text summary has the call chain'
$html = Build-Html $crashes $v ([ordered]@{ Windows = 'Test' }) @() @() @() $changes @() $sum $false $true 90
Assert ($html -match '<title>InDesign Crash Report</title>') 'HTML report is built'
Assert ($html -match 'Catalog Fall\.indd') 'HTML shows the document'
Assert ($html -notmatch '<script') 'HTML has no script tags'

Remove-Item -LiteralPath $work -Recurse -Force
Write-Host ''
if ($script:Failed -gt 0) { Write-Host "$script:Failed test(s) failed" -ForegroundColor Red; exit 1 }
Write-Host 'All tests passed' -ForegroundColor Green
