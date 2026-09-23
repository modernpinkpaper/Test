<#
.SYNOPSIS
    InDesign Crash Doctor - finds out why Adobe InDesign keeps crashing on this PC.

.DESCRIPTION
    Reads every crash record Windows and Adobe keep for InDesign, works out which part
    of InDesign (or which outside add-on) was running when it crashed, looks for things
    that changed on the PC just before the crashes started, and writes an easy report.

    It only reads. It changes nothing, except when you ask for -EnableCrashDumps
    (turns on detailed crash capture for InDesign.exe) or -DisableCrashDumps.

.PARAMETER Days
    How many days back to look. Default 90.

.PARAMETER ExtraFolder
    Extra folders with crash files to read (for example a temp folder you found yourself).
    You can also drag folders onto "Run InDesign Crash Doctor.bat".

.PARAMETER MtLogFolder
    Folder with MT Log .jsonl exports. Used to show which document was open and what was
    done just before each crash. Found automatically in the usual places.

.PARAMETER EnableCrashDumps
    Turn on Windows crash capture for InDesign.exe (needs admin; asks for it).
    After the next crash, run the tool again to get the detailed "call chain".

.PARAMETER DisableCrashDumps
    Turn crash capture off again.

.PARAMETER UseDebugger
    If the Windows debugger (cdb.exe / WinDbg) is installed, also run its automatic
    analysis on each crash file. Slower (it downloads Microsoft symbols).

.PARAMETER OutFolder
    Where to save the report. Default: Desktop\InDesign Crash Report.

.PARAMETER NoOpen
    Do not open the report when done.
#>
[CmdletBinding()]
param(
    [int]$Days = 90,
    [string[]]$ExtraFolder = @(),
    [string]$MtLogFolder = '',
    [switch]$EnableCrashDumps,
    [switch]$DisableCrashDumps,
    [switch]$UseDebugger,
    [string]$OutFolder = '',
    [switch]$NoOpen
)

Set-StrictMode -Version 2
$ErrorActionPreference = 'Continue'
$script:ToolVersion = '1.0.0'
$script:Notes = New-Object System.Collections.Generic.List[string]
$script:RamGB = $null
$script:FreeDiskGB = $null
$script:FontCount = $null

function Write-Step([string]$Text) { Write-Host "  - $Text" -ForegroundColor Cyan }
function Add-Note([string]$Text) { $script:Notes.Add($Text) | Out-Null }

# ---------------------------------------------------------------------------------------
# Knowledge: what each part of InDesign / Windows does, in plain English
# ---------------------------------------------------------------------------------------

# Checked top to bottom; first match wins. Pattern is matched against the lower-case file name.
$script:ModuleKnowledge = @(
    @{ P = '^(nvoglv64|nvwgf2umx|nvd3dumx|nvldumdx|nvcuda|nvapi64|nvumdshimx|nvgpucomp64|nvrtum64)'; Area = 'Graphics card driver (NVIDIA)'; Kind = 'GPU'
       Meaning = 'The crash happened inside the NVIDIA graphics card driver. InDesign uses the graphics card to draw pages (GPU Performance).'
       Fix = @('In InDesign: Edit > Preferences > GPU Performance > untick "GPU Performance", restart InDesign, and see if the crashes stop.',
               'Update the NVIDIA driver from nvidia.com (choose the "Studio" driver), or roll it back if the crashes started after a driver update.') }
    @{ P = '^(atio6axx|atidxx64|atiumd|amdxx64|aticfx64|amdihk64|atiadlxx|amdvlk64|amdenc64|atig6pxx)'; Area = 'Graphics card driver (AMD)'; Kind = 'GPU'
       Meaning = 'The crash happened inside the AMD graphics card driver. InDesign uses the graphics card to draw pages (GPU Performance).'
       Fix = @('In InDesign: Edit > Preferences > GPU Performance > untick "GPU Performance", restart InDesign, and see if the crashes stop.',
               'Update the AMD graphics driver from amd.com, or roll it back if the crashes started after a driver update.') }
    @{ P = '^(ig\w*64|igd\w+|igc64|igdgmm64|igdml64|igdusc64|intelocl64|igvk64)'; Area = 'Graphics card driver (Intel)'; Kind = 'GPU'
       Meaning = 'The crash happened inside the Intel graphics driver. InDesign uses the graphics chip to draw pages (GPU Performance).'
       Fix = @('In InDesign: Edit > Preferences > GPU Performance > untick "GPU Performance", restart InDesign, and see if the crashes stop.',
               'Update the Intel graphics driver (Intel Driver & Support Assistant, or the PC maker''s website).') }
    @{ P = '^(d3d11|d3d12|dxgi|d3d10warp|opengl32|opencl|dxcore|d3d9)\.dll$'; Area = 'Windows graphics system'; Kind = 'GPU'
       Meaning = 'The crash happened in the Windows graphics system (DirectX/OpenGL). This almost always points to the graphics card driver.'
       Fix = @('In InDesign: Edit > Preferences > GPU Performance > untick "GPU Performance", restart InDesign.',
               'Update (or roll back) the graphics card driver.') }
    @{ P = '^cooltype\.dll$'; Area = 'Fonts (font engine)'; Kind = 'Specific'
       Meaning = 'The crash happened in CoolType, the part of InDesign that reads and draws fonts. The usual cause is a damaged or badly made font.'
       Fix = @('Find the damaged font: note which fonts the crashing document uses (Type > Find/Replace Font). Try the document with those fonts removed or replaced.',
               'Delete the InDesign font cache: close InDesign, delete the files named "FNTCACHE*" / the "Font Cache" folders under %APPDATA%\Adobe and %LOCALAPPDATA%\Adobe, then restart.',
               'Remove any fonts installed just before the crashes started (see "What changed").') }
    @{ P = '(font|fontmanager|atm|ctfont)'; Area = 'Fonts'; Kind = 'Specific'
       Meaning = 'The crash happened in the part of InDesign that manages fonts. The usual cause is a damaged or badly made font, or a big font collection.'
       Fix = @('Remove fonts installed just before the crashes started (see "What changed"). Deactivate fonts from font managers you do not need.',
               'Delete the InDesign font cache (close InDesign, delete "FNTCACHE*" files / "Font Cache" folders in %APPDATA%\Adobe), then restart.') }
    @{ P = '^(text|textwalker|textwrap|texteditor|textpanel|storyeditor|composition|paragraph|singleline|worldready|linebreak|glyph|story|findchange|tables?|cjk|footnote|endnote|bullets|span)'; Area = 'Text and text layout'; Kind = 'Specific'
       Meaning = 'The crash happened while InDesign was laying out text (line breaks, text frames, tables, wrapping). The usual cause is damaged text in one document, or a font.'
       Fix = @('Save the document as IDML (File > Save As > InDesign Markup (IDML)), open the IDML, and save it as a new .indd. This rebuilds the document and removes most hidden damage.',
               'If it only happens on one page or story, copy that text into a new text frame, or re-type the problem paragraph.',
               'Check for overset text, very long paragraphs, or tables with many merged cells.') }
    @{ P = '^(hyphen|proximity|hunspell|duden|lilo|spell|dictionar|linguist|dynamicspelling|autocorrect)'; Area = 'Spelling and hyphenation'; Kind = 'Specific'
       Meaning = 'The crash happened in spell check or hyphenation (dictionaries).'
       Fix = @('Edit > Preferences > Spelling: untick "Enable Dynamic Spelling". Edit > Preferences > Autocorrect: untick "Enable Autocorrect".',
               'Check the paragraph language (Character panel > Language). Setting it to "[No Language]" on the problem text is a quick test.') }
    @{ P = '^agm\.dll$'; Area = 'Drawing / graphics engine (AGM)'; Kind = 'Specific'
       Meaning = 'The crash happened in AGM, the engine that draws pages, images, transparency and effects on screen.'
       Fix = @('View > Display Performance > Fast Display, then test. If the crash stops, a placed image or effect is the cause.',
               'Turn off GPU Performance (Edit > Preferences > GPU Performance).',
               'Look for one placed image (PSD, AI, PDF, TIFF) that is very large or damaged; re-save it or replace it.') }
    @{ P = '^(ace|acecore)\.dll$'; Area = 'Colour management (ACE)'; Kind = 'Specific'
       Meaning = 'The crash happened in colour management. Usually a damaged colour profile (ICC) in an image, the document or Windows.'
       Fix = @('Edit > Color Settings: pick "North America General Purpose 2" (or your region default) and test again.',
               'Re-save images that have odd colour profiles, or remove profiles installed just before the crashes started.') }
    @{ P = '^(pdfl|pdfport|pdfexport|pdf|pdfimport|pdfplace|pdfcore|pdfsettings|epdf|axe8sharedexpat)'; Area = 'PDF (export or placed PDF)'; Kind = 'Specific'
       Meaning = 'The crash happened in PDF code - while exporting a PDF, or while showing a PDF that is placed in the document.'
       Fix = @('If it crashes when exporting: File > Export with a different PDF preset, or turn off "Create Tagged PDF" / "Interactive" options; try "Export as Print PDF" to a local folder (not a cloud folder).',
               'If a placed PDF/AI file is the cause: open it in Acrobat, save a new copy (or print to PDF), and relink.',
               'Turn off background export: Edit > Preferences > ... (or use File > Export and wait before doing anything else).') }
    @{ P = '^(image|imageimport|jpeg|png|tiff|psimport|psd|photoshop|placepi|imagefilter|graphics|epsimport|eps|svg|webp|heic|bmp|gif|placeimage|imgutil)'; Area = 'Placed images'; Kind = 'Specific'
       Meaning = 'The crash happened while reading or drawing a placed image (JPG, PNG, TIFF, PSD, EPS...). A damaged or unusual image file is the usual cause.'
       Fix = @('Open the Links panel and look for the image that was being placed or updated. Re-save it in Photoshop (or export a fresh JPG/PNG) and relink.',
               'View > Display Performance > Fast Display, then open the document; if it stops crashing, one of the images is the cause.') }
    @{ P = '^(links?|linkmanager|linkinfo|datalinks|assetlinks)'; Area = 'Links (placed files)'; Kind = 'Specific'
       Meaning = 'The crash happened while InDesign was checking or updating linked files. This is common when links point to cloud or network folders (Google Drive, OneDrive, Dropbox, server).'
       Fix = @('Copy the document and its linked files to a local folder (for example Desktop), relink, and test. Cloud folders that are still syncing cause many link crashes.',
               'In the Links panel, look for missing or modified links and fix them one by one.') }
    @{ P = '^(preflight)'; Area = 'Live Preflight'; Kind = 'Specific'
       Meaning = 'The crash happened in Live Preflight, which checks the document in the background.'
       Fix = @('Turn off Live Preflight: Window > Output > Preflight, untick "On" (and in the panel menu, untick "Enable Preflight for All Documents").') }
    @{ P = '^(scripting|scriptingsupport|sccore|extendscript|script|jsx|appleevents|vbscript|scriptpanel|scriptui)'; Area = 'Scripts'; Kind = 'Specific'
       Meaning = 'The crash happened while a script was running (a .jsx or startup script).'
       Fix = @('Look in the Scripts panel and in the "startup scripts" folders (listed in this report) for scripts added recently; move them out and test.') }
    @{ P = '^(cep|csxs|plugplug|uxp|uxpcore|htmlengine|cef|libcef|chrome_elf|webview|embeddedbrowser)'; Area = 'Extension panels (CEP / UXP / web panels)'; Kind = 'Specific'
       Meaning = 'The crash happened in the system that runs extension panels (the HTML-based panels, including third-party panels, CC Libraries, Learn, Adobe Stock).'
       Fix = @('Close all extension panels (Window > Extensions / Plugins) and test. Remove third-party extensions listed in this report one by one.') }
    @{ P = '^(library|ccl|cclibraries|libraries|assets|creativecloudlibraries|stock)'; Area = 'CC Libraries'; Kind = 'Specific'
       Meaning = 'The crash happened in Creative Cloud Libraries (the Libraries panel / synced assets).'
       Fix = @('Close the CC Libraries panel. Sign out and in again in the Creative Cloud app. Test with the panel closed.') }
    @{ P = '^(print|printing|printui|package|output|separations|flattener|transparency|trapping)'; Area = 'Print / Package / Output'; Kind = 'Specific'
       Meaning = 'The crash happened while printing, packaging or preparing output (transparency flattening, separations).'
       Fix = @('Try printing to a different printer or "Adobe PDF". Update the printer driver.',
               'If it crashes when packaging, package to a local folder (not a cloud folder).') }
    @{ P = '^(idml|inx|snippet|xml|importexport|export|epub|html|fxl|publishonline|interactive|swf|rtf|word|docx|excel|txt|tagged)'; Area = 'Import / Export'; Kind = 'Specific'
       Meaning = 'The crash happened while importing or exporting (Word/Excel/RTF import, EPUB, HTML, IDML, Publish Online).'
       Fix = @('If you were placing a Word/Excel file: save it as a new .docx/.xlsx (or plain text) and place again.',
               'If it was an export: try exporting to a local folder and with fewer options.') }
    @{ P = '^(open|save|filemanager|docframework|document|dochistory|recovery|autosave|filehandler|versioncue|sync|cloudstorage|coresync)'; Area = 'Opening / saving documents'; Kind = 'Specific'
       Meaning = 'The crash happened while opening, saving or auto-recovering a document.'
       Fix = @('Save to a local folder, not a cloud/network folder, and test.',
               'Save the document as IDML and rebuild it (open the IDML, save as new .indd).',
               'If it crashes on start-up: the auto-recovery file may be damaged (see the Recovery folder note in this report).') }
    @{ P = '^(shell32|windows\.storage|explorerframe|comdlg32|propsys|thumbcache|shcore|windowscodecs|photometadatahandler|ntshrui|cscui|drprov)\.dll$'; Area = 'Windows Open/Save dialog and file icons'; Kind = 'Windows'
       Meaning = 'The crash happened in the Windows Open/Save dialog or file thumbnails. This is very often caused by an add-on that plugs into File Explorer (cloud drive, archive tool, image preview, antivirus menu).'
       Fix = @('See "Outside programs loaded into InDesign" below: File Explorer add-ons (cloud drives, 7-Zip, WinRAR, preview handlers) are suspects. Use the free tool "ShellExView" to turn them off one at a time.',
               'Use File > Open with the InDesign dialog: Edit > Preferences > File Handling / Interface: tick "Use Adobe Dialog" if available.') }
    @{ P = '^(combase|ole32|oleaut32|rpcrt4|clipchamp|windows\.applicationmodel|twinapi)'; Area = 'Windows clipboard / drag and drop / COM'; Kind = 'Windows'
       Meaning = 'The crash happened in the Windows system for copy/paste, drag-and-drop and program-to-program communication. Clipboard tools and other programs that watch the clipboard can cause this.'
       Fix = @('Close clipboard managers, screenshot tools and remote-desktop tools and test. Try Edit > Paste without formatting (Ctrl+Shift+V).',
               'In InDesign: Edit > Preferences > Clipboard Handling: untick "Prefer PDF When Pasting" / "Copy PDF to Clipboard" and test.') }
    @{ P = '^(clr|coreclr|mscorwks|clrjit)\.dll$'; Area = '.NET code (usually an add-on)'; Kind = 'Windows'
       Meaning = 'The crash happened in Microsoft .NET code. InDesign itself does not use .NET much, so this usually points to a third-party plug-in or tool.'
       Fix = @('Check the third-party plug-ins and outside programs listed in this report.') }
    @{ P = '^(tbbmalloc|tbb|tbb12|tbbmalloc_proxy)\.dll$'; Area = 'Memory manager'; Kind = 'Core'
       Meaning = 'The crash happened in the memory manager. This almost always means memory was damaged earlier by something else (a plug-in, a driver, or damaged document data) - look at the "call chain" for the real culprit.'
       Fix = @('Check the call chain in the details table.', 'Test with third-party plug-ins removed and GPU Performance off.') }
    @{ P = '^ntdll\.dll$'; Area = 'Windows core (ntdll)'; Kind = 'Generic'
       Meaning = 'The crash was caught in the Windows core. This is where many crashes END, not where they start. The error code and the call chain tell more.'
       Fix = @() }
    @{ P = '^(kernelbase|kernel32)\.dll$'; Area = 'Windows core (error raised on purpose)'; Kind = 'Generic'
       Meaning = 'InDesign (or an add-on) raised an error on purpose and nothing handled it. The call chain / "thrown by" part shows who raised it.'
       Fix = @() }
    @{ P = '^(ucrtbase|msvcp140|vcruntime140|vcruntime140_1|msvcrt|msvcp140_1|msvcp140_2|concrt140)\.dll$'; Area = 'Microsoft Visual C++ runtime'; Kind = 'Generic'
       Meaning = 'The crash was in the Microsoft C++ runtime, shared by many programs. It usually means InDesign stopped itself on purpose after something went wrong (often damaged data, or out of memory).'
       Fix = @('Repair the "Microsoft Visual C++ 2015-2022 Redistributable (x64)": Settings > Apps > find it > Modify > Repair.') }
    @{ P = '^(publiclib|bib|bibutils|dvacore|dvaui|asneu|aslfoundation|adobeowl|adobexmp|adobexmpfiles|icu\w*|widgetbin|appframework|applicationui|ui|actions|menus|kbsc|workspace|panels?|dialogs?|tool\w*|selection|layout|layoutui|spread|pages|master|parent)'; Area = 'InDesign core'; Kind = 'Core'
       Meaning = 'The crash happened in a core part of InDesign that is used by almost everything. The call chain shows what InDesign was doing.'
       Fix = @() }
    @{ P = '^indesign\.exe$'; Area = 'InDesign main program'; Kind = 'Core'
       Meaning = 'The crash happened in the main InDesign program. The call chain shows what it was doing.'
       Fix = @() }
)

$script:GenericModules = @('ntdll.dll', 'kernelbase.dll', 'kernel32.dll', 'ucrtbase.dll', 'msvcp140.dll', 'vcruntime140.dll',
                           'vcruntime140_1.dll', 'msvcrt.dll', 'msvcp140_1.dll', 'msvcp140_2.dll', 'wow64.dll', 'unknown', '')

$script:ExceptionKnowledge = @{
    'c0000005' = 'Access violation - the program tried to use memory that was not there. Usually damaged data (in the document, a font or an image) or a bug in a plug-in/driver.'
    'c0000374' = 'Heap corruption - memory was damaged earlier by some code. The crash place is only where it was noticed; plug-ins and drivers are the usual cause.'
    'c0000409' = 'Stopped on purpose (fast fail / stack protection). The program found something badly wrong and closed itself to be safe.'
    'e06d7363' = 'C++ error nobody handled - InDesign or an add-on raised an error and nothing caught it.'
    '80000003' = 'Breakpoint / assert - the program stopped itself on purpose after a check failed.'
    'c00000fd' = 'Stack overflow - the program went round in a loop too deep (often a damaged document, very complex nesting, or a script).'
    'c0000017' = 'Out of memory.'
    'c000041d' = 'Crash inside a Windows callback (often a UI add-on or a driver hooking into windows).'
    'c0000602' = 'Stopped on purpose after a serious internal error.'
    'c0000420' = 'Assertion failure - the program stopped itself after a check failed.'
    'c000001d' = 'Illegal instruction - often a bad driver/plug-in or a damaged program install.'
    'c0000006' = 'In-page error - a file the program was reading could not be read (disk, network or cloud folder problem).'
    'c0000142' = 'The program failed to start (a DLL failed to load).'
    'c0000135' = 'A required DLL is missing (damaged install).'
    'cfffffff' = 'Hang - InDesign stopped responding and was closed.'
}

$script:FastFailKnowledge = @{
    2 = 'stack buffer check failed (memory overwritten)'
    3 = 'corrupt internal list (memory damaged)'
    5 = 'invalid parameter passed to the C runtime'
    7 = 'the program called abort() - it gave up after an unhandled error'
    10 = 'control-flow guard check failed (bad pointer, memory damaged)'
}

function Get-LeafName([string]$Path) {
    # File name from a Windows path (works the same whichever system reads the crash file).
    if (-not $Path) { return '' }
    return ($Path -split '[\\/]')[-1]
}

function Get-ModuleKnowledge([string]$Name) {
    $n = ''
    if ($Name) { $n = (Get-LeafName $Name).ToLowerInvariant() }
    if (-not $n) {
        return @{ Area = 'Unknown place'; Kind = 'Generic'; Fix = @()
                  Meaning = 'The crash address was not inside any known file. This usually means memory was damaged (by a plug-in, driver or damaged data), so the program jumped somewhere invalid.' }
    }
    foreach ($k in $script:ModuleKnowledge) {
        if ($n -match $k.P) { return $k }
    }
    if ($n -match '\.(apln|rpln)$') {
        return @{ Area = 'InDesign plug-in "' + ($n -replace '\.[^.]*$', '') + '"'; Kind = 'Specific'; Fix = @()
                  Meaning = 'The crash happened in the InDesign plug-in "' + ($n -replace '\.[^.]*$', '') + '" (part of InDesign itself). The name tells which feature was in use.' }
    }
    if ($n -match '\.pln$') {
        return @{ Area = 'Third-party InDesign plug-in'; Kind = 'ThirdParty'
                  Meaning = 'The crash happened in a plug-in that is not made by Adobe (.pln file).'
                  Fix = @('Update or remove this plug-in (move it out of the InDesign "Plug-Ins" folder) and test.') }
    }
    return @{ Area = $n; Kind = 'Other'; Fix = @(); Meaning = '' }
}

function Get-ExceptionText([string]$Code) {
    if (-not $Code) { return '' }
    $c = $Code.ToLowerInvariant() -replace '^0x', ''
    $c = $c.PadLeft(8, '0')
    if ($script:ExceptionKnowledge.ContainsKey($c)) { return $script:ExceptionKnowledge[$c] }
    return ''
}

function Format-Code([string]$Code) {
    if (-not $Code) { return '' }
    $c = $Code.ToLowerInvariant() -replace '^0x', ''
    return '0x' + $c.PadLeft(8, '0')
}

# ---------------------------------------------------------------------------------------
# Who made a file (digital signature)
# ---------------------------------------------------------------------------------------
$script:SignerCache = @{}
function Get-FileMaker([string]$Path) {
    if (-not $Path) { return 'Unknown' }
    if ($script:SignerCache.ContainsKey($Path)) { return $script:SignerCache[$Path] }
    $maker = 'Unknown'
    try {
        if (Test-Path -LiteralPath $Path -PathType Leaf) {
            $sig = Get-AuthenticodeSignature -LiteralPath $Path -ErrorAction Stop
            if ($sig -and $sig.SignerCertificate) {
                $subject = $sig.SignerCertificate.Subject
                if ($subject -match 'O="?([^",]+)') { $maker = $Matches[1] }
                elseif ($subject -match 'CN="?([^",]+)') { $maker = $Matches[1] }
                else { $maker = $subject }
            } else {
                $info = (Get-Item -LiteralPath $Path -ErrorAction Stop).VersionInfo
                if ($info.CompanyName) { $maker = $info.CompanyName.Trim() + ' (not signed)' } else { $maker = 'Not signed' }
            }
        } else {
            $maker = 'File not on this PC any more'
        }
    } catch { $maker = 'Unknown' }
    $script:SignerCache[$Path] = $maker
    return $maker
}

function Test-IsAdobeOrWindowsPath([string]$Path) {
    if (-not $Path) { return $true }
    $p = $Path.ToLowerInvariant()
    $win = ($env:windir + '\').ToLowerInvariant()
    if ($p.StartsWith($win) -or $p -match '^[a-z]:\\windows\\') { return $true }
    if ($p -match '\\adobe\\' -or $p -match '\\common files\\adobe') { return $true }
    if ($p -match '\\windowsapps\\microsoft\.') { return $true }
    return $false
}

function Get-ModuleClass([string]$Name, [string]$Path) {
    # Returns 'ThirdParty', 'GPU', 'Adobe', 'Windows' or 'Generic'
    $k = Get-ModuleKnowledge $Name
    if ($k.Kind -eq 'GPU') { return 'GPU' }
    if ($k.Kind -eq 'Generic') { return 'Generic' }
    $n = ''
    if ($Name) { $n = (Get-LeafName $Name).ToLowerInvariant() }
    if ($n -match '\.pln$') { return 'ThirdParty' }
    if ($Path) {
        if (-not (Test-IsAdobeOrWindowsPath $Path)) {
            $maker = Get-FileMaker $Path
            if ($maker -notmatch 'Adobe|Microsoft') { return 'ThirdParty' }
        }
        $pl = $Path.ToLowerInvariant()
        if ($pl.StartsWith(($env:windir + '\').ToLowerInvariant()) -or $pl -match '^[a-z]:\\windows\\') { return 'Windows' }
    }
    if ($k.Kind -eq 'Windows') { return 'Windows' }
    return 'Adobe'
}

function Get-ModuleScore([string]$Name, [string]$Path) {
    # How much a module tells us about the real cause. Higher = more specific.
    $k = Get-ModuleKnowledge $Name
    $class = Get-ModuleClass $Name $Path
    if ($class -eq 'ThirdParty' -or $class -eq 'GPU') { return 4 }
    if ($k.Kind -eq 'Specific') { return 3 }
    if ($k.Kind -eq 'Windows') { return 2 }
    if ($k.Kind -eq 'Other') { return 2 }
    if ($k.Kind -eq 'Core') { return 1 }
    return 0
}

# ---------------------------------------------------------------------------------------
# Source 1: Windows Event Log (Application Error 1000, Application Hang 1002)
# ---------------------------------------------------------------------------------------
function Get-EventLogCrashes([datetime]$Since) {
    $list = @()
    try {
        $events = Get-WinEvent -FilterHashtable @{ LogName = 'Application'; Id = 1000, 1002; StartTime = $Since } -ErrorAction Stop
    } catch {
        if ($_.Exception.Message -notmatch 'No events were found') { Add-Note ('Could not read the Windows Event Log: ' + $_.Exception.Message) }
        return @()
    }
    foreach ($e in $events) {
        $p = $e.Properties
        if ($p.Count -lt 1) { continue }
        $app = [string]$p[0].Value
        if ($app -notmatch '^InDesign') { continue }
        if ($e.Id -eq 1000) {
            $modPath = ''
            if ($p.Count -gt 11) { $modPath = [string]$p[11].Value }
            $list += [pscustomobject]@{
                Time = $e.TimeCreated; Kind = 'Crash'; AppVersion = [string]$p[1].Value
                Module = [string]$p[3].Value; ModuleVersion = [string]$p[4].Value; ModulePath = $modPath
                ExceptionCode = (Format-Code ([string]$p[6].Value)); Offset = ('0x' + [string]$p[7].Value)
                Sources = @('Windows Event Log'); Files = @()
            }
        } else {
            $list += [pscustomobject]@{
                Time = $e.TimeCreated; Kind = 'Freeze'; AppVersion = [string]$p[1].Value
                Module = ''; ModuleVersion = ''; ModulePath = ''; ExceptionCode = ''; Offset = ''
                Sources = @('Windows Event Log (not responding)'); Files = @()
            }
        }
    }
    return $list
}

# ---------------------------------------------------------------------------------------
# Source 2: Windows Error Reporting folders (Report.wer)
# ---------------------------------------------------------------------------------------
function Read-WerReport([string]$Path) {
    $map = @{}
    $loaded = New-Object System.Collections.Generic.List[string]
    $sig = @{}
    foreach ($line in (Get-Content -LiteralPath $Path -ErrorAction Stop)) {
        $i = $line.IndexOf('=')
        if ($i -lt 1) { continue }
        $key = $line.Substring(0, $i); $val = $line.Substring($i + 1)
        if ($key -match '^LoadedModule\[\d+\]$') { $loaded.Add($val) | Out-Null; continue }
        if ($key -match '^Sig\[(\d+)\]\.Name$') { if (-not $sig.ContainsKey($Matches[1])) { $sig[$Matches[1]] = @{} }; $sig[$Matches[1]].Name = $val; continue }
        if ($key -match '^Sig\[(\d+)\]\.Value$') { if (-not $sig.ContainsKey($Matches[1])) { $sig[$Matches[1]] = @{} }; $sig[$Matches[1]].Value = $val; continue }
        $map[$key] = $val
    }
    $s = @{}
    foreach ($k in $sig.Keys) { if ($sig[$k].ContainsKey('Name')) { $s[$sig[$k].Name] = $sig[$k].Value } }
    $time = $null
    if ($map.ContainsKey('EventTime')) {
        try { $time = [DateTime]::FromFileTimeUtc([int64]$map['EventTime']).ToLocalTime() } catch { }
    }
    if (-not $time) { $time = (Get-Item -LiteralPath $Path).LastWriteTime }
    $eventType = ''
    if ($map.ContainsKey('EventType')) { $eventType = $map['EventType'] }
    $kind = 'Crash'
    if ($eventType -match 'Hang') { $kind = 'Freeze' }
    $get = { param($names) foreach ($n in $names) { if ($s.ContainsKey($n)) { return $s[$n] } }; return '' }
    $appName = & $get @('Application Name', 'AppName')
    $modPath = ''
    $modName = & $get @('Fault Module Name', 'FaultModuleName')
    if ($modName) {
        foreach ($m in $loaded) { if ((Get-LeafName $m) -ieq $modName) { $modPath = $m; break } }
    }
    return [pscustomobject]@{
        Time = $time; Kind = $kind; AppName = $appName
        AppVersion = (& $get @('Application Version', 'AppVersion'))
        Module = $modName; ModuleVersion = (& $get @('Fault Module Version'))
        ModulePath = $modPath
        ExceptionCode = (Format-Code (& $get @('Exception Code')))
        Offset = (& $get @('Exception Offset', 'Fault Offset'))
        LoadedModules = @($loaded)
        EventType = $eventType
    }
}

function Get-WerCrashes([datetime]$Since) {
    $roots = @()
    foreach ($base in @($env:LOCALAPPDATA, $env:ProgramData)) {
        if (-not $base) { continue }
        foreach ($sub in @('ReportArchive', 'ReportQueue')) {
            $r = Join-Path $base "Microsoft\Windows\WER\$sub"
            if (Test-Path -LiteralPath $r) { $roots += $r }
        }
    }
    $list = @()
    foreach ($r in $roots) {
        $dirs = Get-ChildItem -LiteralPath $r -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -match 'InDesign' -and $_.LastWriteTime -ge $Since }
        foreach ($d in $dirs) {
            $wer = Join-Path $d.FullName 'Report.wer'
            if (-not (Test-Path -LiteralPath $wer)) { continue }
            try {
                $rep = Read-WerReport $wer
                if ($rep.AppName -and $rep.AppName -notmatch '^InDesign') { continue }
                $files = @($wer)
                $dumps = Get-ChildItem -LiteralPath $d.FullName -File -ErrorAction SilentlyContinue | Where-Object { $_.Extension -match '^\.(mdmp|dmp)$' }
                foreach ($x in $dumps) { $files += $x.FullName }
                $list += [pscustomobject]@{
                    Time = $rep.Time; Kind = $rep.Kind; AppVersion = $rep.AppVersion
                    Module = $rep.Module; ModuleVersion = $rep.ModuleVersion; ModulePath = $rep.ModulePath
                    ExceptionCode = $rep.ExceptionCode; Offset = $rep.Offset
                    LoadedModules = $rep.LoadedModules
                    Sources = @('Windows Error Reporting'); Files = $files
                }
            } catch { Add-Note ("Could not read $wer : " + $_.Exception.Message) }
        }
    }
    return $list
}

# ---------------------------------------------------------------------------------------
# Source 3: crash dump files (.dmp / .mdmp) - read directly, no debugger needed
# ---------------------------------------------------------------------------------------
function Read-MiniDump([string]$Path, [int]$MaxStackBytes = 262144) {
    $fs = $null
    try {
        $fs = [System.IO.File]::Open($Path, 'Open', 'Read', 'ReadWrite')
        $br = New-Object System.IO.BinaryReader($fs)
        if ($fs.Length -lt 32) { return $null }
        $sigBytes = $br.ReadBytes(4)
        if ([System.Text.Encoding]::ASCII.GetString($sigBytes) -ne 'MDMP') { return $null }
        [void]$br.ReadUInt32()                       # version
        $streamCount = $br.ReadUInt32()
        $dirRva = $br.ReadUInt32()
        [void]$br.ReadUInt32()                       # checksum
        $timeStamp = $br.ReadUInt32()
        $dumpTime = $null
        if ($timeStamp -gt 0) { $dumpTime = ([DateTimeOffset]::FromUnixTimeSeconds([int64]$timeStamp)).LocalDateTime }

        $streams = @{}
        $fs.Position = $dirRva
        for ($i = 0; $i -lt $streamCount; $i++) {
            $type = $br.ReadUInt32(); $size = $br.ReadUInt32(); $rva = $br.ReadUInt32()
            if (-not $streams.ContainsKey([int]$type)) { $streams[[int]$type] = @{ Size = $size; Rva = $rva } }
        }

        $readString = {
            param([uint32]$rva)
            if ($rva -eq 0 -or $rva -ge $fs.Length) { return '' }
            $fs.Position = $rva
            $len = $br.ReadUInt32()
            if ($len -gt 4096) { return '' }
            return [System.Text.Encoding]::Unicode.GetString($br.ReadBytes([int]$len))
        }

        # System info (7): processor architecture. 9 = x64.
        $arch = 9
        if ($streams.ContainsKey(7)) { $fs.Position = $streams[7].Rva; $arch = $br.ReadUInt16() }

        # Module list (4)
        $modules = New-Object System.Collections.Generic.List[object]
        if ($streams.ContainsKey(4)) {
            $fs.Position = $streams[4].Rva
            $count = $br.ReadUInt32()
            $raw = @()
            for ($i = 0; $i -lt $count; $i++) {
                $base = $br.ReadUInt64(); $size = $br.ReadUInt32(); [void]$br.ReadUInt32(); [void]$br.ReadUInt32()
                $nameRva = $br.ReadUInt32()
                [void]$br.ReadUInt32(); [void]$br.ReadUInt32()       # signature, struc version
                $verMS = $br.ReadUInt32(); $verLS = $br.ReadUInt32()
                [void]$br.ReadBytes(108 - 40)
                $raw += ,@($base, $size, $nameRva, $verMS, $verLS)
            }
            foreach ($r in $raw) {
                $path = & $readString $r[2]
                $ver = ''
                if ($r[3] -ne 0 -or $r[4] -ne 0) { $ver = '{0}.{1}.{2}.{3}' -f ($r[3] -shr 16), ($r[3] -band 0xFFFF), ($r[4] -shr 16), ($r[4] -band 0xFFFF) }
                $modules.Add([pscustomobject]@{ Base = [uint64]$r[0]; Size = [uint64]$r[1]; Path = $path; Name = (Get-LeafName $path); Version = $ver }) | Out-Null
            }
        }
        $sorted = @($modules | Sort-Object Base)
        $findModule = {
            param([uint64]$addr)
            $lo = 0; $hi = $sorted.Count - 1
            while ($lo -le $hi) {
                $mid = [int][Math]::Floor(($lo + $hi) / 2)
                $m = $sorted[$mid]
                if ($addr -lt $m.Base) { $hi = $mid - 1 }
                elseif ($addr -ge ($m.Base + $m.Size)) { $lo = $mid + 1 }
                else { return $m }
            }
            return $null
        }

        # Memory ranges we can read (for the crashing thread's stack)
        $ranges = New-Object System.Collections.Generic.List[object]
        $threads = @{}
        if ($streams.ContainsKey(3)) {
            $fs.Position = $streams[3].Rva
            $tc = $br.ReadUInt32()
            for ($i = 0; $i -lt $tc; $i++) {
                $tid = $br.ReadUInt32(); [void]$br.ReadBytes(12); [void]$br.ReadUInt64()
                $stackStart = $br.ReadUInt64(); $stackSize = $br.ReadUInt32(); $stackRva = $br.ReadUInt32()
                $ctxSize = $br.ReadUInt32(); $ctxRva = $br.ReadUInt32()
                $threads[[uint32]$tid] = @{ CtxRva = $ctxRva; CtxSize = $ctxSize }
                if ($stackSize -gt 0 -and $stackRva -gt 0) { $ranges.Add(@{ Start = $stackStart; Size = [uint64]$stackSize; Rva = [uint64]$stackRva }) | Out-Null }
            }
        }
        if ($streams.ContainsKey(5)) {
            $fs.Position = $streams[5].Rva
            $mc = $br.ReadUInt32()
            for ($i = 0; $i -lt $mc; $i++) {
                $st = $br.ReadUInt64(); $sz = $br.ReadUInt32(); $rv = $br.ReadUInt32()
                $ranges.Add(@{ Start = $st; Size = [uint64]$sz; Rva = [uint64]$rv }) | Out-Null
            }
        }
        if ($streams.ContainsKey(9)) {
            $fs.Position = $streams[9].Rva
            $mc = $br.ReadUInt64(); $baseRva = $br.ReadUInt64()
            $off = $baseRva
            for ($i = 0; $i -lt $mc; $i++) {
                $st = $br.ReadUInt64(); $sz = $br.ReadUInt64()
                $ranges.Add(@{ Start = $st; Size = $sz; Rva = $off }) | Out-Null
                $off += $sz
            }
        }

        # Exception (6)
        $excCode = ''; $excAddr = [uint64]0; $params = @(); $excThread = 0; $ctxRva = 0; $ctxSize = 0
        $hasException = $streams.ContainsKey(6)
        if ($hasException) {
            $fs.Position = $streams[6].Rva
            $excThread = $br.ReadUInt32(); [void]$br.ReadUInt32()
            $excCode = '0x{0:x8}' -f $br.ReadUInt32()
            [void]$br.ReadUInt32(); [void]$br.ReadUInt64()
            $excAddr = $br.ReadUInt64()
            $np = $br.ReadUInt32(); [void]$br.ReadUInt32()
            for ($i = 0; $i -lt 15; $i++) { $params += $br.ReadUInt64() }
            $params = @($params[0..([Math]::Max(0, [Math]::Min(14, [int]$np - 1)))])
            if ($np -eq 0) { $params = @() }
            $ctxSize = $br.ReadUInt32(); $ctxRva = $br.ReadUInt32()
        }

        $faultModule = $null
        if ($hasException) { $faultModule = & $findModule $excAddr }

        # C++ exception: parameter 3 is the base address of the module that threw it
        $thrower = $null
        if ($excCode -eq '0xe06d7363' -and $params.Count -ge 4) {
            foreach ($m in $sorted) { if ($m.Base -eq $params[3]) { $thrower = $m; break } }
        }

        # Walk the crashing thread's stack memory and note which modules the return addresses fall in.
        $chain = New-Object System.Collections.Generic.List[string]
        $chainPaths = @{}
        if ($hasException -and $arch -eq 9 -and $ctxRva -gt 0 -and $ctxSize -ge 0x100) {
            $fs.Position = $ctxRva + 0x98; $rsp = $br.ReadUInt64()
            $fs.Position = $ctxRva + 0xF8; $rip = $br.ReadUInt64()
            $ripMod = & $findModule $rip
            if ($ripMod) { $chain.Add($ripMod.Name) | Out-Null; $chainPaths[$ripMod.Name] = $ripMod.Path }
            $range = $null
            foreach ($r in $ranges) { if ($rsp -ge $r.Start -and $rsp -lt ($r.Start + $r.Size)) { $range = $r; break } }
            if ($range) {
                $offset = $rsp - $range.Start
                $len = [uint64][Math]::Min([double]($range.Size - $offset), [double]$MaxStackBytes)
                $fs.Position = [int64]($range.Rva + $offset)
                $bytes = $br.ReadBytes([int]$len)
                $last = ''
                if ($chain.Count -gt 0) { $last = $chain[0] }
                for ($o = 0; $o -le $bytes.Length - 8; $o += 8) {
                    $v = [BitConverter]::ToUInt64($bytes, $o)
                    if ($v -lt 0x10000) { continue }
                    $m = & $findModule $v
                    if (-not $m) { continue }
                    if (($v - $m.Base) -lt 0x1000) { continue }     # header area, not code
                    if ($m.Name -ne $last) {
                        $chain.Add($m.Name) | Out-Null
                        $chainPaths[$m.Name] = $m.Path
                        $last = $m.Name
                        if ($chain.Count -ge 40) { break }
                    }
                }
            }
        }

        $extra = ''
        if ($excCode -eq '0xc0000005' -and $params.Count -ge 2) {
            $op = 'read'
            if ($params[0] -eq 1) { $op = 'write' } elseif ($params[0] -eq 8) { $op = 'run code at' }
            $extra = "tried to $op address 0x{0:x}" -f $params[1]
            if ($params[1] -lt 0x10000) { $extra += ' (an empty/missing object - "null pointer")' }
        }
        if ($excCode -eq '0xc0000409' -and $params.Count -ge 1) {
            $ff = [int]$params[0]
            if ($script:FastFailKnowledge.ContainsKey($ff)) { $extra = "reason: " + $script:FastFailKnowledge[$ff] } else { $extra = "fast-fail code $ff" }
        }

        $faultName = ''; $faultPath = ''; $faultVer = ''; $offset = ''
        if ($faultModule) { $faultName = $faultModule.Name; $faultPath = $faultModule.Path; $faultVer = $faultModule.Version; $offset = '0x{0:x}' -f ($excAddr - $faultModule.Base) }
        elseif ($hasException) { $faultName = 'unknown'; $offset = '0x{0:x}' -f $excAddr }

        $appVer = ''
        foreach ($m in $sorted) { if ($m.Name -match '^InDesign\.exe$') { $appVer = $m.Version } }
        $isInDesign = $false
        foreach ($m in $sorted) { if ($m.Name -match '^InDesign\.exe$') { $isInDesign = $true } }

        return [pscustomobject]@{
            Path = $Path; Time = $dumpTime; IsInDesign = $isInDesign; HasException = $hasException
            ExceptionCode = $excCode; ExceptionDetail = $extra
            Module = $faultName; ModulePath = $faultPath; ModuleVersion = $faultVer; Offset = $offset
            ThrownBy = $(if ($thrower) { $thrower.Name } else { '' }); ThrownByPath = $(if ($thrower) { $thrower.Path } else { '' })
            Chain = @($chain); ChainPaths = $chainPaths
            LoadedModules = @($sorted | ForEach-Object { $_.Path })
            AppVersion = $appVer
        }
    } catch {
        Add-Note ("Could not read crash file $Path : " + $_.Exception.Message)
        return $null
    } finally {
        if ($fs) { $fs.Dispose() }
    }
}

function Find-CrashFiles([datetime]$Since, [string[]]$Extra) {
    $folders = New-Object System.Collections.Generic.List[string]
    $add = { param($f) if ($f -and (Test-Path -LiteralPath $f) -and -not $folders.Contains($f)) { $folders.Add($f) | Out-Null } }
    & $add (Join-Path $env:LOCALAPPDATA 'CrashDumps')
    & $add (Join-Path $env:APPDATA 'Adobe\CRLogs')
    & $add (Join-Path $env:LOCALAPPDATA 'Adobe\CRLogs')
    & $add (Join-Path $env:LOCALAPPDATA 'Adobe\CrashReporter')
    & $add (Join-Path $env:APPDATA 'Adobe\CrashReporter')
    & $add (Join-Path $env:LOCALAPPDATA 'Temp\Adobe\CrashReporter')
    $files = @()
    foreach ($x in $Extra) {
        # A dropped file is read as it is (any date); a dropped folder is searched.
        if ($x -and (Test-Path -LiteralPath $x -PathType Leaf)) { $files += Get-Item -LiteralPath $x }
        else { & $add $x }
    }

    foreach ($f in $folders) {
        $files += Get-ChildItem -LiteralPath $f -File -Recurse -ErrorAction SilentlyContinue |
            Where-Object { $_.LastWriteTime -ge $Since -and $_.Extension -match '^\.(dmp|mdmp|txt|log|xml|json|crash|ips)$' -and $_.Length -gt 0 }
    }
    # The temp folder is big: only look at the top two levels, and only at files that look like crash files.
    if ($env:TEMP -and (Test-Path -LiteralPath $env:TEMP)) {
        $files += Get-ChildItem -LiteralPath $env:TEMP -File -Recurse -Depth 2 -ErrorAction SilentlyContinue |
            Where-Object { $_.LastWriteTime -ge $Since -and $_.Name -match 'indesign|crash|\.dmp$|\.mdmp$' -and $_.Name -notmatch '^InDesignCrashDoctor' -and $_.Length -gt 0 }
    }
    return @($files | Sort-Object FullName -Unique)
}

function Read-TextCrashLog([string]$Path) {
    # Adobe / other text crash logs: pull out the time, error code and the file names they mention, in order.
    try {
        $info = Get-Item -LiteralPath $Path
        if ($info.Length -gt 20MB) { return $null }
        $text = [System.IO.File]::ReadAllText($Path)
    } catch { return $null }
    if ($text -notmatch '(?i)indesign') { return $null }
    $mods = New-Object System.Collections.Generic.List[string]
    foreach ($m in [regex]::Matches($text, '(?i)([A-Za-z0-9_\-\. ]{2,60}\.(dll|apln|rpln|pln|aip|exe))\b')) {
        $n = $m.Groups[1].Value.Trim()
        $n = (Get-LeafName $n) -replace '^\d+\s+', ''
        if ($mods.Count -eq 0 -or $mods[$mods.Count - 1] -ne $n) { $mods.Add($n) | Out-Null }
        if ($mods.Count -ge 60) { break }
    }
    $code = ''
    $cm = [regex]::Match($text, '(?i)(?:exception|code)[^\r\n]{0,40}?(0x[0-9a-f]{8}|[ce][0-9a-f]{7})')
    if ($cm.Success) { $code = Format-Code $cm.Groups[1].Value }
    $crashLine = ''
    $lm = [regex]::Match($text, '(?im)^.*(crashed thread|exception|faulting|fault module|crash reason|stack).*$')
    if ($lm.Success) { $crashLine = $lm.Value.Trim() }
    if ($crashLine.Length -gt 200) { $crashLine = $crashLine.Substring(0, 200) }
    return [pscustomobject]@{ Path = $Path; Time = $info.LastWriteTime; Modules = @($mods); ExceptionCode = $code; KeyLine = $crashLine }
}

function Invoke-Debugger([string]$DumpPath) {
    $cdb = $null
    $candidates = @(
        "${env:ProgramFiles(x86)}\Windows Kits\10\Debuggers\x64\cdb.exe",
        "$env:ProgramFiles\Windows Kits\10\Debuggers\x64\cdb.exe"
    )
    foreach ($c in $candidates) { if ($c -and (Test-Path -LiteralPath $c)) { $cdb = $c; break } }
    if (-not $cdb) {
        $app = Get-ChildItem -Path "$env:ProgramFiles\WindowsApps" -Filter 'Microsoft.WinDbg*' -Directory -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($app) { $x = Join-Path $app.FullName 'amd64\cdb.exe'; if (Test-Path -LiteralPath $x) { $cdb = $x } }
    }
    if (-not $cdb) { return $null }
    $sym = Join-Path $env:LOCALAPPDATA 'InDesignCrashDoctor\symbols'
    New-Item -ItemType Directory -Path $sym -Force | Out-Null
    $out = & $cdb -z $DumpPath -y "srv*$sym*https://msdl.microsoft.com/download/symbols" -c '.ecxr; kn 40; !analyze -v; q' 2>&1 | Out-String
    return $out
}

# ---------------------------------------------------------------------------------------
# Combine everything into one list of crashes
# ---------------------------------------------------------------------------------------
function Merge-Crashes($Items) {
    $merged = New-Object System.Collections.Generic.List[object]
    foreach ($c in ($Items | Where-Object { $_.Time } | Sort-Object Time)) {
        $match = $null
        foreach ($m in $merged) {
            if ([Math]::Abs(($m.Time - $c.Time).TotalSeconds) -le 180 -and $m.Kind -eq $c.Kind) { $match = $m; break }
        }
        if (-not $match) {
            $merged.Add([pscustomobject]@{
                Time = $c.Time; Kind = $c.Kind; AppVersion = ''; Module = ''; ModulePath = ''; ModuleVersion = ''
                ExceptionCode = ''; ExceptionDetail = ''; Offset = ''; ThrownBy = ''; ThrownByPath = ''
                Chain = @(); ChainPaths = @{}; LoadedModules = @(); Sources = @(); Files = @()
                Blamed = ''; BlamedPath = ''; Document = ''; LastActions = @(); DebuggerOutput = ''
            }) | Out-Null
            $match = $merged[$merged.Count - 1]
        }
        foreach ($f in @('AppVersion', 'ModulePath', 'ModuleVersion', 'ExceptionCode', 'ExceptionDetail', 'Offset', 'ThrownBy', 'ThrownByPath', 'DebuggerOutput')) {
            if ($c.PSObject.Properties[$f] -and $c.$f -and -not $match.$f) { $match.$f = $c.$f }
        }
        # A real module name beats "unknown"
        if ($c.PSObject.Properties['Module'] -and $c.Module -and (-not $match.Module -or $match.Module -eq 'unknown')) { $match.Module = $c.Module }
        if ($c.PSObject.Properties['Chain'] -and @($c.Chain).Count -gt @($match.Chain).Count) { $match.Chain = @($c.Chain); $match.ChainPaths = $c.ChainPaths }
        if ($c.PSObject.Properties['LoadedModules'] -and @($c.LoadedModules).Count -gt @($match.LoadedModules).Count) { $match.LoadedModules = @($c.LoadedModules) }
        if ($c.PSObject.Properties['Sources']) { $match.Sources = @($match.Sources + $c.Sources | Select-Object -Unique) }
        if ($c.PSObject.Properties['Files']) { $match.Files = @($match.Files + $c.Files | Select-Object -Unique) }
    }
    return $merged
}

function Set-Blame($Crash) {
    # Decide which module most likely CAUSED this crash (not just where it ended).
    $best = $Crash.Module; $bestPath = $Crash.ModulePath
    $bestScore = Get-ModuleScore $Crash.Module $Crash.ModulePath
    if ($Crash.ThrownBy) {
        $s = Get-ModuleScore $Crash.ThrownBy $Crash.ThrownByPath
        if ($s -ge $bestScore) { $best = $Crash.ThrownBy; $bestPath = $Crash.ThrownByPath; $bestScore = $s }
    }
    if ($bestScore -lt 3) {
        $i = 0
        foreach ($n in $Crash.Chain) {
            $i++
            if ($i -gt 15) { break }
            $p = ''
            if ($Crash.ChainPaths -and $Crash.ChainPaths.ContainsKey($n)) { $p = $Crash.ChainPaths[$n] }
            $s = Get-ModuleScore $n $p
            if ($s -ge 3) { $best = $n; $bestPath = $p; break }
        }
    }
    if (-not $best -and $Crash.Kind -eq 'Freeze') { $best = '(freeze - no crash place)' }
    $Crash.Blamed = $best
    $Crash.BlamedPath = $bestPath
}

# ---------------------------------------------------------------------------------------
# PC information and what changed
# ---------------------------------------------------------------------------------------
function Get-InDesignInstalls {
    $list = @()
    $roots = @($env:ProgramFiles)
    foreach ($r in $roots) {
        $dirs = Get-ChildItem -LiteralPath (Join-Path $r 'Adobe') -Directory -Filter 'Adobe InDesign*' -ErrorAction SilentlyContinue
        foreach ($d in $dirs) {
            $exe = Join-Path $d.FullName 'InDesign.exe'
            if (-not (Test-Path -LiteralPath $exe)) { continue }
            $ver = (Get-Item -LiteralPath $exe).VersionInfo.ProductVersion
            $plugDir = Join-Path $d.FullName 'Plug-Ins'
            $third = @()
            if (Test-Path -LiteralPath $plugDir) {
                $plugs = Get-ChildItem -LiteralPath $plugDir -Recurse -File -ErrorAction SilentlyContinue | Where-Object { $_.Extension -match '^\.(pln|apln|rpln|aip|dll)$' }
                foreach ($p in $plugs) {
                    $isThird = $false
                    if ($p.Extension -eq '.pln') { $isThird = $true }
                    elseif ([string]$p.VersionInfo.CompanyName -notmatch 'Adobe') {
                        # Only check the signature when the file does not say it is Adobe's (much faster)
                        $maker = Get-FileMaker $p.FullName
                        if ($maker -notmatch 'Adobe') { $isThird = $true }
                    }
                    if ($isThird) { $third += [pscustomobject]@{ Name = $p.Name; Path = $p.FullName; Maker = (Get-FileMaker $p.FullName); Added = $p.CreationTime } }
                }
            }
            $list += [pscustomobject]@{ Folder = $d.FullName; Version = $ver; ThirdPartyPlugins = $third }
        }
    }
    return $list
}

function Get-Extensions {
    $list = @()
    $folders = @()
    foreach ($pair in @(@($env:APPDATA, 'Adobe\CEP\extensions'), @(${env:ProgramFiles(x86)}, 'Common Files\Adobe\CEP\extensions'),
                        @($env:ProgramFiles, 'Common Files\Adobe\CEP\extensions'), @($env:ProgramFiles, 'Common Files\Adobe\UXP\extensions'),
                        @($env:APPDATA, 'Adobe\UXP\Plugins\External'))) {
        if ($pair[0]) { $folders += (Join-Path $pair[0] $pair[1]) }
    }
    foreach ($f in $folders) {
        if (-not $f -or -not (Test-Path -LiteralPath $f)) { continue }
        foreach ($d in (Get-ChildItem -LiteralPath $f -Directory -ErrorAction SilentlyContinue)) {
            if ($d.Name -match '^com\.adobe\.') { continue }
            $list += [pscustomobject]@{ Name = $d.Name; Path = $d.FullName; Added = $d.CreationTime }
        }
    }
    return $list
}

function Get-StartupScripts {
    $list = @()
    $roots = @()
    $roots += Get-ChildItem -Path (Join-Path $env:APPDATA 'Adobe\InDesign') -Directory -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName }
    $roots += Get-ChildItem -Path (Join-Path $env:ProgramFiles 'Adobe') -Directory -Filter 'Adobe InDesign*' -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName }
    foreach ($r in $roots) {
        $dirs = Get-ChildItem -LiteralPath $r -Directory -Recurse -Depth 4 -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^startup scripts$' }
        foreach ($d in $dirs) {
            foreach ($f in (Get-ChildItem -LiteralPath $d.FullName -File -Recurse -ErrorAction SilentlyContinue)) {
                $list += [pscustomobject]@{ Name = $f.Name; Path = $f.FullName; Added = $f.CreationTime }
            }
        }
    }
    return $list
}

function Get-SystemFacts {
    $facts = [ordered]@{}
    try {
        $os = Get-CimInstance Win32_OperatingSystem -ErrorAction Stop
        $facts['Windows'] = "$($os.Caption) (build $($os.BuildNumber))"
        $facts['Memory (RAM)'] = '{0:N1} GB total, {1:N1} GB free now' -f ($os.TotalVisibleMemorySize / 1MB), ($os.FreePhysicalMemory / 1MB)
        $script:RamGB = $os.TotalVisibleMemorySize / 1MB
    } catch { }
    try {
        $cs = Get-CimInstance Win32_ComputerSystem -ErrorAction Stop
        $facts['Computer'] = "$($cs.Manufacturer) $($cs.Model)"
    } catch { }
    try {
        $cpu = Get-CimInstance Win32_Processor -ErrorAction Stop | Select-Object -First 1
        $facts['Processor'] = $cpu.Name.Trim()
    } catch { }
    try {
        $gpus = @(Get-CimInstance Win32_VideoController -ErrorAction Stop)
        $i = 1
        foreach ($g in $gpus) {
            $date = ''
            if ($g.DriverDate) { $date = ([datetime]$g.DriverDate).ToString('yyyy-MM-dd') }
            $facts["Graphics $i"] = "$($g.Name) - driver $($g.DriverVersion) ($date)"
            $i++
        }
    } catch { }
    try {
        $sys = Get-PSDrive -Name ($env:SystemDrive.TrimEnd(':')) -ErrorAction Stop
        $facts['Free disk space'] = '{0:N1} GB free on {1}' -f ($sys.Free / 1GB), $env:SystemDrive
        $script:FreeDiskGB = $sys.Free / 1GB
    } catch { }
    try {
        $fonts = @(Get-ChildItem -LiteralPath (Join-Path $env:windir 'Fonts') -File -ErrorAction SilentlyContinue).Count
        $userFonts = @(Get-ChildItem -LiteralPath (Join-Path $env:LOCALAPPDATA 'Microsoft\Windows\Fonts') -File -ErrorAction SilentlyContinue).Count
        $facts['Fonts installed'] = "$fonts for all users, $userFonts for this user"
        $script:FontCount = $fonts + $userFonts
    } catch { }
    return $facts
}

function Get-Changes([datetime]$From) {
    $changes = New-Object System.Collections.Generic.List[object]
    $add = { param($t, $kind, $what) if ($t -and $t -ge $From) { $changes.Add([pscustomobject]@{ Time = $t; Kind = $kind; What = $what }) | Out-Null } }

    # Windows updates (including driver updates delivered by Windows Update)
    try {
        $wu = Get-WinEvent -FilterHashtable @{ LogName = 'System'; ProviderName = 'Microsoft-Windows-WindowsUpdateClient'; Id = 19; StartTime = $From } -ErrorAction Stop
        foreach ($e in $wu) {
            $title = ''
            if ($e.Properties.Count -gt 0) { $title = [string]$e.Properties[0].Value }
            $kind = 'Windows update'
            if ($title -match '(?i)display|graphics|nvidia|amd|intel.*(graphics|display)|radeon') { $kind = 'Graphics driver update' }
            & $add $e.TimeCreated $kind $title
        }
    } catch { }
    # Drivers installed outside Windows Update
    try {
        $drv = Get-WinEvent -FilterHashtable @{ LogName = 'System'; ProviderName = 'Microsoft-Windows-UserPnp'; Id = 20001; StartTime = $From } -ErrorAction Stop
        foreach ($e in $drv) {
            $msg = ($e.Message -split "`r?`n")[0]
            $kind = 'Driver installed'
            if ($msg -match '(?i)display|graphics|nvidia|amd|radeon|intel\(r\) (uhd|iris|hd) graphics') { $kind = 'Graphics driver update' }
            & $add $e.TimeCreated $kind $msg
        }
    } catch { }
    # Programs installed
    $keys = @('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
              'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*',
              'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*')
    foreach ($k in $keys) {
        foreach ($p in (Get-ItemProperty -Path $k -ErrorAction SilentlyContinue)) {
            if (-not $p.PSObject.Properties['DisplayName'] -or -not $p.DisplayName) { continue }
            if (-not $p.PSObject.Properties['InstallDate'] -or -not $p.InstallDate) { continue }
            try {
                $d = [datetime]::ParseExact([string]$p.InstallDate, 'yyyyMMdd', [Globalization.CultureInfo]::InvariantCulture)
                $ver = ''
                if ($p.PSObject.Properties['DisplayVersion']) { $ver = ' ' + $p.DisplayVersion }
                & $add $d 'Program installed/updated' ($p.DisplayName + $ver)
            } catch { }
        }
    }
    # Fonts
    $fontDirs = @((Join-Path $env:windir 'Fonts'), (Join-Path $env:LOCALAPPDATA 'Microsoft\Windows\Fonts'),
                  (Join-Path $env:APPDATA 'Adobe\CoreSync\plugins\livetype\r'))
    foreach ($fd in $fontDirs) {
        foreach ($f in (Get-ChildItem -LiteralPath $fd -File -Recurse -ErrorAction SilentlyContinue | Where-Object { $_.CreationTime -ge $From })) {
            $kind = 'Font added'
            if ($fd -match 'livetype') { $kind = 'Adobe Font activated' }
            & $add $f.CreationTime $kind $f.Name
        }
    }
    return $changes
}

# ---------------------------------------------------------------------------------------
# MT Log: which document was open and what was done just before the crash
# ---------------------------------------------------------------------------------------
function Get-Prop($Object, [string]$Name) {
    if ($null -eq $Object) { return '' }
    $p = $Object.PSObject.Properties[$Name]
    if ($p -and $null -ne $p.Value) { return [string]$p.Value }
    return ''
}

function Get-MtLogFolders([string]$Given) {
    $list = @()
    if ($Given -and (Test-Path -LiteralPath $Given)) { $list += $Given }
    $local = Join-Path $env:LOCALAPPDATA 'MT Log\export'
    if (Test-Path -LiteralPath $local) { $list += $local }
    foreach ($letter in [char[]]([int][char]'D'..[int][char]'Z')) {
        $p = "${letter}:\My Drive\Personal\mpp activity"
        if (Test-Path -LiteralPath $p -ErrorAction SilentlyContinue) { $list += $p }
    }
    return $list
}

function Add-MtLogContext($Crashes, [string[]]$Folders) {
    if (-not $Folders -or $Folders.Count -eq 0 -or $Crashes.Count -eq 0) { return $false }
    $found = $false
    $byDay = $Crashes | Group-Object { $_.Time.ToString('yyyy-MM-dd') }
    foreach ($g in $byDay) {
        $day = $g.Group[0].Time.Date
        $files = @()
        foreach ($f in $Folders) {
            $files += Get-ChildItem -LiteralPath $f -Recurse -File -Filter '*.jsonl' -ErrorAction SilentlyContinue |
                Where-Object { $_.LastWriteTime -ge $day.AddHours(-2) -and $_.LastWriteTime -le $day.AddDays(1).AddHours(6) }
        }
        if ($files.Count -eq 0) { continue }
        $events = @()
        foreach ($file in $files) {
            foreach ($line in [System.IO.File]::ReadLines($file.FullName)) {
                if ($line -notmatch '(?i)indesign') { continue }
                try { $e = $line | ConvertFrom-Json } catch { continue }
                if ((Get-Prop $e 'process_name') -notmatch '(?i)^indesign' -and (Get-Prop $e 'application') -notmatch '(?i)indesign') { continue }
                try { $t = [datetime]::Parse((Get-Prop $e 'timestamp_local'), [Globalization.CultureInfo]::InvariantCulture, [Globalization.DateTimeStyles]::RoundtripKind).ToLocalTime() } catch { continue }
                $events += [pscustomobject]@{ Time = $t; Event = $e }
            }
        }
        if ($events.Count -eq 0) { continue }
        $events = @($events | Sort-Object Time)
        foreach ($c in $g.Group) {
            $before = @($events | Where-Object { $_.Time -le $c.Time.AddSeconds(30) -and $_.Time -ge $c.Time.AddMinutes(-20) })
            if ($before.Count -eq 0) { continue }
            $found = $true
            $lastTitle = ''
            foreach ($b in $before) { $wt = Get-Prop $b.Event 'window_title'; if ($wt) { $lastTitle = $wt } }
            $doc = $lastTitle -replace '^Adobe InDesign( \d{4})?\s*-\s*', '' -replace '\s*@\s*\d+%.*$', ''
            $c.Document = $doc
            $actions = @()
            foreach ($b in ($before | Select-Object -Last 6)) {
                $ev = $b.Event
                $txt = Get-Prop $ev 'event_type'
                $md = $null
                if ($ev.PSObject.Properties['metadata']) { $md = $ev.metadata }
                if ($md -and (Get-Prop $md 'control_name')) { $txt += ' "' + (Get-Prop $md 'control_name') + '"' }
                elseif ($md -and (Get-Prop $md 'document')) { $txt += ' ' + (Get-Prop $md 'document') }
                $actions += ('{0:HH:mm:ss} {1}' -f $b.Time, $txt)
            }
            $c.LastActions = $actions
        }
    }
    return $found
}

# ---------------------------------------------------------------------------------------
# Crash capture switch (LocalDumps)
# ---------------------------------------------------------------------------------------
function Test-IsAdmin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    return (New-Object Security.Principal.WindowsPrincipal($id)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Set-CrashCapture([bool]$On) {
    $key = 'HKLM:\SOFTWARE\Microsoft\Windows\Windows Error Reporting\LocalDumps\InDesign.exe'
    if (-not (Test-IsAdmin)) {
        $arg = '-NoProfile -ExecutionPolicy Bypass -File "' + $PSCommandPath + '" ' + $(if ($On) { '-EnableCrashDumps' } else { '-DisableCrashDumps' })
        Write-Host 'Asking Windows for admin permission...' -ForegroundColor Yellow
        try { Start-Process -FilePath 'powershell.exe' -ArgumentList $arg -Verb RunAs -Wait } catch { Write-Host 'Admin permission was not given. Nothing changed.' -ForegroundColor Red }
        return
    }
    if ($On) {
        New-Item -Path $key -Force | Out-Null
        New-ItemProperty -Path $key -Name 'DumpType' -Value 1 -PropertyType DWord -Force | Out-Null
        New-ItemProperty -Path $key -Name 'DumpCount' -Value 10 -PropertyType DWord -Force | Out-Null
        Write-Host ''
        Write-Host 'Detailed crash capture is ON for InDesign.' -ForegroundColor Green
        Write-Host 'Next time InDesign crashes, Windows saves a small crash file (a few MB) in'
        Write-Host '  %LOCALAPPDATA%\CrashDumps'
        Write-Host 'Then run "Run InDesign Crash Doctor" again to read it.'
    } else {
        Remove-Item -Path $key -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host 'Detailed crash capture is OFF.' -ForegroundColor Green
    }
    Start-Sleep -Seconds 4
}

function Get-CrashCaptureOn {
    return (Test-Path -LiteralPath 'HKLM:\SOFTWARE\Microsoft\Windows\Windows Error Reporting\LocalDumps\InDesign.exe')
}

# ---------------------------------------------------------------------------------------
# The verdict
# ---------------------------------------------------------------------------------------
function Get-Verdict($Crashes, $Changes, $Installs, $Extensions, $Scripts, $TextLogs, [bool]$CaptureOn, [int]$DaysBack) {
    $findings = New-Object System.Collections.Generic.List[object]
    $steps = New-Object System.Collections.Generic.List[string]
    $addStep = { param($s) if ($s -and -not $steps.Contains($s)) { $steps.Add($s) | Out-Null } }
    $addFinding = { param($strength, $title, $text) $findings.Add([pscustomobject]@{ Strength = $strength; Title = $title; Text = $text }) | Out-Null }

    $realCrashes = @($Crashes | Where-Object { $_.Kind -eq 'Crash' })
    $freezes = @($Crashes | Where-Object { $_.Kind -eq 'Freeze' })

    if ($Crashes.Count -eq 0) {
        $t = "Windows has no record of InDesign crashing in the last $DaysBack days."
        if ($TextLogs.Count -gt 0) { $t += " But $($TextLogs.Count) crash log file(s) were found and are listed below." }
        & $addFinding 'Info' 'No crash records found' ($t + ' Adobe''s own crash reporter may have caught the crashes before Windows saw them.')
        if (-not $CaptureOn) { & $addStep 'Turn on detailed crash capture (double-click "Turn On Crash Capture.bat"), use InDesign until it crashes again, then run this tool again.' }
        & $addStep 'If you know the folder with the crash logs you found before, drag that folder onto "Run InDesign Crash Doctor.bat".'
    }

    # Group crashes by the blamed module
    $groups = @($realCrashes | Where-Object { $_.Blamed } | Group-Object { $_.Blamed.ToLowerInvariant() } | Sort-Object Count -Descending)
    $topName = ''
    if ($groups.Count -gt 0) {
        $top = $groups[0]
        $name = $top.Group[0].Blamed
        $path = $top.Group[0].BlamedPath
        $k = Get-ModuleKnowledge $name
        $class = Get-ModuleClass $name $path
        $topName = $name
        $share = [int](100 * $top.Count / [Math]::Max(1, $realCrashes.Count))
        $strength = 'Possible'
        if ($top.Count -ge 2 -and $share -ge 50) { $strength = 'Strong' }
        if ($realCrashes.Count -eq 1) { $strength = 'Possible' }
        $title = "$($top.Count) of $($realCrashes.Count) crashes point to: $name"
        $text = "Area: $($k.Area). "
        if ($k.Meaning) { $text += $k.Meaning + ' ' }
        if ($class -eq 'ThirdParty') {
            $maker = Get-FileMaker $path
            $text += "This file is NOT made by Adobe (maker: $maker; file: $path). Add-ons like this are one of the most common reasons InDesign crashes."
            & $addStep "Update or remove ""$name"" (maker: $maker). If it is an InDesign plug-in, move it out of the Plug-Ins folder; if it belongs to another program, update or uninstall that program. Then test."
            $strength = 'Strong'
        }
        & $addFinding $strength $title $text
        if ($class -ne 'ThirdParty') { foreach ($s in $k.Fix) { & $addStep $s } }

        if ($k.Kind -eq 'Generic' -or $k.Kind -eq 'Core') {
            & $addFinding 'Info' 'The crash place is general, not specific' 'The crash ended in a general-purpose part of Windows/InDesign, and the crash records do not show a more specific cause. Turn on detailed crash capture to get the full call chain next time.'
            if (-not $CaptureOn) { & $addStep 'Turn on detailed crash capture (double-click "Turn On Crash Capture.bat"). After the next crash, run this tool again: it will read the call chain and name the part of InDesign that started the problem.' }
        }
        if ($groups.Count -gt 1) {
            $others = ($groups | Select-Object -Skip 1 | ForEach-Object { "$($_.Group[0].Blamed) ($($_.Count)x)" }) -join ', '
            & $addFinding 'Info' 'Other crash places' "Other crashes pointed to: $others. Different places usually mean the real cause is something shared (a damaged document, a font, memory damaged by an add-on or driver, or low memory), not one bug."
        }
    }

    # Third-party code involved in any crash chain
    $thirdSeen = @{}
    foreach ($c in $realCrashes) {
        $names = @($c.Chain) + @($c.ThrownBy) + @($c.Module)
        foreach ($n in $names) {
            if (-not $n) { continue }
            $p = ''
            if ($c.ChainPaths -and $c.ChainPaths.ContainsKey($n)) { $p = $c.ChainPaths[$n] }
            elseif ($n -eq $c.Module) { $p = $c.ModulePath }
            elseif ($n -eq $c.ThrownBy) { $p = $c.ThrownByPath }
            $cls = Get-ModuleClass $n $p
            if ($cls -eq 'ThirdParty' -or $cls -eq 'GPU') {
                if (-not $thirdSeen.ContainsKey($n)) { $thirdSeen[$n] = @{ Hits = 0; Path = $p; Class = $cls } }
                $thirdSeen[$n].Hits++
            }
        }
    }
    foreach ($n in $thirdSeen.Keys) {
        if ($n -eq $topName) { continue }      # already the main finding
        $info = $thirdSeen[$n]
        $who = 'graphics card driver'
        if ($info.Class -eq 'ThirdParty') { $who = 'non-Adobe add-on (maker: ' + (Get-FileMaker $info.Path) + ')' }
        & $addFinding 'Strong' "Outside code was running when InDesign crashed: $n" "$n is a $who. It was part of what InDesign was doing at the moment of $($info.Hits) crash(es). File: $($info.Path)"
        if ($info.Class -eq 'GPU') {
            & $addStep 'In InDesign: Edit > Preferences > GPU Performance > untick "GPU Performance", restart InDesign, and see if the crashes stop.'
        } else {
            & $addStep "Update or remove ""$n"" and test."
        }
    }

    # Same document every time (from MT Log)
    $withDoc = @($Crashes | Where-Object { $_.Document })
    if ($withDoc.Count -ge 2) {
        $docGroups = @($withDoc | Group-Object Document | Sort-Object Count -Descending)
        $d = $docGroups[0]
        if ($d.Count -ge 2 -and $d.Count -ge [Math]::Ceiling($withDoc.Count / 2)) {
            & $addFinding 'Strong' "Most crashes happened with the same document open: $($d.Name)" "$($d.Count) of $($withDoc.Count) crashes (where MT Log knew the document) happened with ""$($d.Name)"" open. A damaged document is a very common cause."
            & $addStep "Rebuild ""$($d.Name)"": File > Save As > InDesign Markup (IDML), then open the .idml and save it as a new .indd. Use the new file from now on."
        }
    }

    # Things that changed just before the first crash
    if ($realCrashes.Count -gt 0) {
        $first = ($realCrashes | Sort-Object Time | Select-Object -First 1).Time
        $near = @($Changes | Where-Object { $_.Time -le $first -and $_.Time -ge $first.AddDays(-7) } | Sort-Object Time -Descending)
        $susp = @($near | Where-Object { $_.Kind -match 'Graphics|Font|Adobe Font' -or $_.What -match '(?i)indesign|adobe|creative cloud|font|extensis|suitcase|fontbase|nexusfont|plug-?in|nvidia|amd|radeon|intel.*graphics|onedrive|dropbox|google drive|antivirus|defender|norton|mcafee|avast|avg|bitdefender|kaspersky|eset|malwarebytes' })
        if ($near.Count -gt 0) {
            $list = ($susp + ($near | Where-Object { $susp -notcontains $_ }) | Select-Object -First 8 | ForEach-Object { '{0:yyyy-MM-dd}: {1} - {2}' -f $_.Time, $_.Kind, $_.What }) -join '; '
            $strength = 'Possible'
            & $addFinding $strength 'Things that changed in the week before the first crash' ("The first crash in this report was on {0:yyyy-MM-dd HH:mm}. In the 7 days before it: {1}. If one of these is the cause, undoing it should stop the crashes." -f $first, $list)
            if ($susp.Count -gt 0) { & $addStep ("Undo the change that fits best (for example: remove the new font, roll back the driver, uninstall the new program): " + (($susp | Select-Object -First 3 | ForEach-Object { $_.What }) -join '; ') + '.') }
        }
        if ($first -le (Get-Date).AddDays(-$DaysBack + 2)) {
            & $addFinding 'Info' 'The crashes may have started earlier' "The first crash found is right at the start of the $DaysBack days searched, so they may have started earlier. Run the tool with a bigger number of days to look further back."
        }
    }

    # InDesign version change
    $versions = @($realCrashes | Where-Object { $_.AppVersion } | Select-Object -ExpandProperty AppVersion -Unique)
    if ($versions.Count -gt 1) {
        & $addFinding 'Info' 'InDesign was updated during this time' ("Crashes happened on more than one InDesign version: " + ($versions -join ', ') + '. If crashes started or became more frequent after an update, try the other version (Creative Cloud app > InDesign > ... > Other versions).')
    }

    # Third-party plug-ins, extensions and startup scripts installed
    $allThird = @()
    foreach ($i in $Installs) { $allThird += $i.ThirdPartyPlugins }
    if ($allThird.Count -gt 0) {
        & $addFinding 'Possible' "$($allThird.Count) non-Adobe plug-in file(s) are installed in InDesign" (($allThird | ForEach-Object { "$($_.Name) (maker: $($_.Maker))" }) -join ', ')
        & $addStep 'Test without non-Adobe plug-ins: move them out of the InDesign "Plug-Ins" folder (to the Desktop), restart InDesign, and work normally for a day.'
    }
    if ($Extensions.Count -gt 0) {
        & $addFinding 'Info' "$($Extensions.Count) non-Adobe extension panel(s) installed" (($Extensions | ForEach-Object { $_.Name }) -join ', ')
    }
    if ($Scripts.Count -gt 0) {
        & $addFinding 'Possible' "$($Scripts.Count) startup script(s) run every time InDesign starts" (($Scripts | ForEach-Object { $_.Path }) -join '; ')
        & $addStep 'Move the startup scripts listed in this report out of their folder and test.'
    }

    # Outside programs whose DLLs were loaded into InDesign in (almost) every crash
    $counts = @{}
    $withMods = @($realCrashes | Where-Object { @($_.LoadedModules).Count -gt 0 })
    foreach ($c in $withMods) {
        foreach ($m in (@($c.LoadedModules) | Select-Object -Unique)) {
            if (Test-IsAdobeOrWindowsPath $m) { continue }
            if (-not $counts.ContainsKey($m)) { $counts[$m] = 0 }
            $counts[$m]++
        }
    }
    $injected = @($counts.Keys | Where-Object { $counts[$_] -ge [Math]::Max(1, [Math]::Ceiling($withMods.Count * 0.6)) } | Where-Object { (Get-FileMaker $_) -notmatch 'Adobe|Microsoft' })
    if ($injected.Count -gt 0) {
        $txt = ($injected | ForEach-Object { (Get-LeafName $_) + ' (maker: ' + (Get-FileMaker $_) + ')' }) -join ', '
        & $addFinding 'Possible' 'Outside programs loaded into InDesign' "These files from other programs were loaded inside InDesign when it crashed: $txt. Programs like antivirus, screen recorders, cloud drives, mouse/keyboard tools, overlays and clipboard managers do this. They are not always the cause, but they can be."
        & $addStep 'Test with the outside programs listed under "Outside programs loaded into InDesign" closed or paused (one at a time).'
    }

    if ($freezes.Count -gt 0) {
        & $addFinding 'Info' "InDesign froze (stopped responding) $($freezes.Count) time(s)" 'Freezes usually come from very big documents or images, links on slow network/cloud folders, fonts, or low memory. They are counted separately from crashes.'
    }
    if ($script:RamGB -and $script:RamGB -lt 8) {
        & $addFinding 'Possible' ('This PC has only {0:N0} GB of memory' -f $script:RamGB) 'Adobe recommends 16 GB for InDesign. Low memory causes crashes with big documents or images.'
        & $addStep 'Close other programs (especially browsers with many tabs) while using InDesign.'
    }
    if ($script:FreeDiskGB -and $script:FreeDiskGB -lt 10) {
        & $addFinding 'Strong' ('Very little free disk space ({0:N1} GB)' -f $script:FreeDiskGB) 'InDesign needs free disk space for its recovery and temp files. Low disk space causes crashes, especially while saving.'
        & $addStep 'Free up disk space on the C: drive (at least 20 GB free).'
    }
    if ($script:FontCount -and $script:FontCount -gt 3000) {
        & $addFinding 'Possible' "Very many fonts installed ($($script:FontCount))" 'Thousands of active fonts slow InDesign down and make a damaged font more likely. Use a font manager to keep only the fonts you need active.'
    }

    # General steps if nothing above solves it
    $general = @(
        'Reset InDesign preferences: close InDesign, then hold Ctrl+Alt+Shift while starting it and answer Yes to "Delete InDesign preference files?". (This resets your settings to default.)',
        'Test with a brand-new document: if a new document never crashes but one old document does, rebuild the old one through IDML.',
        'Turn off GPU Performance (Edit > Preferences > GPU Performance) as a test.',
        'Keep documents and their linked files on a local drive while working (not directly in Google Drive, OneDrive or Dropbox).',
        'Update InDesign to the latest version (Creative Cloud app), or if crashes started after an update, go back one version.'
    )
    foreach ($g in $general) { & $addStep $g }

    return [pscustomobject]@{ Findings = $findings; Steps = $steps }
}

# ---------------------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------------------
function HtmlEncode([string]$s) { return [System.Net.WebUtility]::HtmlEncode($s) }

function Get-ChainText($c, [int]$Max = 12) {
    $chain = @($c.Chain | Where-Object { $_ } | Select-Object -First $Max)
    if ($chain.Count -eq 0) { return '' }
    return ($chain -join ' <- ')
}

function Build-TextSummary($Crashes, $Verdict, $Facts, $Installs, $Changes, $TextLogs, [int]$DaysBack) {
    $sb = New-Object System.Text.StringBuilder
    [void]$sb.AppendLine("InDesign Crash Doctor $script:ToolVersion - report made $(Get-Date -Format 'yyyy-MM-dd HH:mm')")
    [void]$sb.AppendLine("Looked back $DaysBack days.")
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('== PC ==')
    foreach ($k in $Facts.Keys) { [void]$sb.AppendLine("$k : $($Facts[$k])") }
    foreach ($i in $Installs) { [void]$sb.AppendLine("InDesign $($i.Version) in $($i.Folder)") }
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('== Findings ==')
    foreach ($f in $Verdict.Findings) { [void]$sb.AppendLine("[$($f.Strength)] $($f.Title)"); [void]$sb.AppendLine("    $($f.Text)") }
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine("== Crashes ($($Crashes.Count)) ==")
    foreach ($c in ($Crashes | Sort-Object Time -Descending)) {
        [void]$sb.AppendLine(('{0:yyyy-MM-dd HH:mm:ss}  {1}  InDesign {2}' -f $c.Time, $c.Kind, $c.AppVersion))
        if ($c.Module) { [void]$sb.AppendLine("    Crashed in: $($c.Module) $($c.ModuleVersion) at offset $($c.Offset)  [$($c.ModulePath)]") }
        if ($c.ExceptionCode) { [void]$sb.AppendLine("    Error: $($c.ExceptionCode) - $(Get-ExceptionText $c.ExceptionCode) $($c.ExceptionDetail)") }
        if ($c.ThrownBy) { [void]$sb.AppendLine("    Error raised by: $($c.ThrownBy)") }
        if ($c.Blamed) { [void]$sb.AppendLine("    Most likely cause area: $($c.Blamed)") }
        $chain = Get-ChainText $c 25
        if ($chain) { [void]$sb.AppendLine("    Call chain (newest first): $chain") }
        if ($c.Document) { [void]$sb.AppendLine("    Document open: $($c.Document)") }
        foreach ($a in $c.LastActions) { [void]$sb.AppendLine("    Before crash: $a") }
        [void]$sb.AppendLine("    From: $(($c.Sources) -join ', ')")
    }
    if ($TextLogs.Count -gt 0) {
        [void]$sb.AppendLine('')
        [void]$sb.AppendLine('== Crash log files (text) ==')
        foreach ($t in $TextLogs) {
            [void]$sb.AppendLine(('{0:yyyy-MM-dd HH:mm}  {1}' -f $t.Time, $t.Path))
            if ($t.ExceptionCode) { [void]$sb.AppendLine("    Error code: $($t.ExceptionCode)") }
            if ($t.KeyLine) { [void]$sb.AppendLine("    Key line: $($t.KeyLine)") }
            if ($t.Modules.Count -gt 0) { [void]$sb.AppendLine("    Files named in it (in order): " + (($t.Modules | Select-Object -First 25) -join ', ')) }
        }
    }
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('== Changes on this PC ==')
    foreach ($ch in ($Changes | Sort-Object Time -Descending | Select-Object -First 80)) { [void]$sb.AppendLine(('{0:yyyy-MM-dd}  {1}: {2}' -f $ch.Time, $ch.Kind, $ch.What)) }
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('== Steps to try ==')
    $n = 1
    foreach ($s in $Verdict.Steps) { [void]$sb.AppendLine("$n. $s"); $n++ }
    return $sb.ToString()
}

function Build-Html($Crashes, $Verdict, $Facts, $Installs, $Extensions, $Scripts, $Changes, $TextLogs, [string]$TextSummary, [bool]$CaptureOn, [bool]$MtLogUsed, [int]$DaysBack) {
    $e = { param($s) HtmlEncode ([string]$s) }
    $crashCount = @($Crashes | Where-Object { $_.Kind -eq 'Crash' }).Count
    $freezeCount = @($Crashes | Where-Object { $_.Kind -eq 'Freeze' }).Count
    $sb = New-Object System.Text.StringBuilder
    [void]$sb.Append(@'
<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>InDesign Crash Report</title>
<style>
:root{--bg:#f6f6f4;--card:#fff;--text:#1d1d1f;--muted:#5f6368;--line:#e2e2de;--strong:#b3261e;--strongbg:#fdecea;--possible:#8a5a00;--possiblebg:#fff4e0;--info:#1a5fb4;--infobg:#e8f0fb;--code:#f1f1ee}
@media (prefers-color-scheme: dark){:root{--bg:#161617;--card:#212123;--text:#ececec;--muted:#a0a0a5;--line:#333336;--strong:#ff8a80;--strongbg:#3a1d1b;--possible:#ffcc80;--possiblebg:#3a2d14;--info:#90b8f8;--infobg:#1b2a40;--code:#2a2a2d}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.55 "Segoe UI",system-ui,sans-serif}
main{max-width:1040px;margin:0 auto;padding:24px 16px 64px}
h1{font-size:26px;margin:0 0 4px}h2{font-size:19px;margin:32px 0 10px}.muted{color:var(--muted)}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:10px 0}
.stats{display:flex;gap:10px;flex-wrap:wrap;margin:16px 0}.stat{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 16px;min-width:140px}
.stat b{display:block;font-size:24px}
.tag{display:inline-block;font-size:12px;font-weight:600;border-radius:99px;padding:2px 9px;margin-right:8px;vertical-align:1px}
.Strong .tag{background:var(--strongbg);color:var(--strong)}.Possible .tag{background:var(--possiblebg);color:var(--possible)}.Info .tag{background:var(--infobg);color:var(--info)}
.Strong{border-left:4px solid var(--strong)}.Possible{border-left:4px solid var(--possible)}.Info{border-left:4px solid var(--info)}
ol li{margin:6px 0}
.tablewrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13.5px;background:var(--card)}
th,td{border-bottom:1px solid var(--line);padding:7px 8px;text-align:left;vertical-align:top}th{font-weight:600}
code,.mono{font-family:Consolas,"Cascadia Mono",monospace;font-size:12.5px}
.chain{color:var(--muted);word-break:break-word}
textarea{width:100%;height:260px;font-family:Consolas,monospace;font-size:12px;background:var(--code);color:var(--text);border:1px solid var(--line);border-radius:8px;padding:10px}
button{font:inherit;padding:6px 14px;border-radius:8px;border:1px solid var(--line);background:var(--card);color:var(--text);cursor:pointer}
details{margin:8px 0}summary{cursor:pointer;font-weight:600}
</style></head><body><main>
'@)
    [void]$sb.Append('<h1>Why InDesign keeps crashing</h1>')
    [void]$sb.Append('<div class="muted">Made by InDesign Crash Doctor on ' + (& $e (Get-Date -Format 'dddd d MMMM yyyy, HH:mm')) + " - looked back $DaysBack days</div>")
    [void]$sb.Append('<div class="stats">')
    [void]$sb.Append("<div class=""stat""><b>$crashCount</b>crashes</div><div class=""stat""><b>$freezeCount</b>freezes</div>")
    [void]$sb.Append('<div class="stat"><b>' + $TextLogs.Count + '</b>crash log files</div>')
    $cap = 'OFF'; if ($CaptureOn) { $cap = 'ON' }
    [void]$sb.Append("<div class=""stat""><b>$cap</b>detailed crash capture</div></div>")

    [void]$sb.Append('<h2>What the crash records say</h2>')
    [void]$sb.Append('<p class="muted"><b>Strong</b> = clear evidence. <b>Possible</b> = worth testing. <b>Info</b> = background.</p>')
    foreach ($f in ($Verdict.Findings | Sort-Object @{ Expression = { switch ($_.Strength) { 'Strong' { 0 } 'Possible' { 1 } default { 2 } } } })) {
        [void]$sb.Append('<div class="card ' + $f.Strength + '"><span class="tag">' + $f.Strength + '</span><b>' + (& $e $f.Title) + '</b><div>' + (& $e $f.Text) + '</div></div>')
    }

    [void]$sb.Append('<h2>What to try, in this order</h2><div class="card"><ol>')
    foreach ($s in $Verdict.Steps) { [void]$sb.Append('<li>' + (& $e $s) + '</li>') }
    [void]$sb.Append('</ol><div class="muted">Change one thing at a time and use InDesign normally for a while. If the crashes stop, the last thing you changed was the cause.</div></div>')

    [void]$sb.Append('<h2>Every crash</h2>')
    if ($Crashes.Count -eq 0) {
        [void]$sb.Append('<div class="card">No crash records were found.</div>')
    } else {
        [void]$sb.Append('<div class="tablewrap"><table><tr><th>When</th><th>What</th><th>Crashed in</th><th>Error</th><th>Most likely area</th>')
        if ($MtLogUsed) { [void]$sb.Append('<th>Document / last actions (MT Log)</th>') }
        [void]$sb.Append('</tr>')
        foreach ($c in ($Crashes | Sort-Object Time -Descending)) {
            $k = Get-ModuleKnowledge $c.Blamed
            $err = ''
            if ($c.ExceptionCode) { $err = '<code>' + (& $e $c.ExceptionCode) + '</code><br>' + (& $e (Get-ExceptionText $c.ExceptionCode)) }
            if ($c.ExceptionDetail) { $err += '<br><span class="muted">' + (& $e $c.ExceptionDetail) + '</span>' }
            if ($c.ThrownBy) { $err += '<br>Raised by <code>' + (& $e $c.ThrownBy) + '</code>' }
            $crashedIn = '<code>' + (& $e $c.Module) + '</code>'
            if ($c.ModuleVersion) { $crashedIn += ' <span class="muted">' + (& $e $c.ModuleVersion) + '</span>' }
            $chain = Get-ChainText $c 12
            if ($chain) { $crashedIn += '<div class="chain mono">chain: ' + (& $e $chain) + '</div>' }
            $area = '<b>' + (& $e $c.Blamed) + '</b><br>' + (& $e $k.Area)
            if ($c.Kind -eq 'Freeze') { $area = '<span class="muted">Freeze - no crash place is recorded</span>' }
            [void]$sb.Append('<tr><td>' + (& $e ('{0:yyyy-MM-dd HH:mm}' -f $c.Time)) + '<br><span class="muted">InDesign ' + (& $e $c.AppVersion) + '</span></td>')
            [void]$sb.Append('<td>' + (& $e $c.Kind) + '<br><span class="muted">' + (& $e (($c.Sources) -join ', ')) + '</span></td>')
            [void]$sb.Append("<td>$crashedIn</td><td>$err</td><td>$area</td>")
            if ($MtLogUsed) {
                $doc = (& $e $c.Document)
                if ($c.LastActions.Count -gt 0) { $doc += '<div class="chain mono">' + (($c.LastActions | ForEach-Object { & $e $_ }) -join '<br>') + '</div>' }
                [void]$sb.Append("<td>$doc</td>")
            }
            [void]$sb.Append('</tr>')
        }
        [void]$sb.Append('</table></div>')
        [void]$sb.Append('<p class="muted">"Chain" is the list of InDesign parts that were active on the crashing thread, newest first. It is read directly from the crash file, so it shows what InDesign was in the middle of doing. It only appears when a crash file (.dmp) exists - turn on detailed crash capture to get it.</p>')
    }

    if ($TextLogs.Count -gt 0) {
        [void]$sb.Append('<h2>Crash log files found</h2><div class="tablewrap"><table><tr><th>File</th><th>Error</th><th>Files named in it (in order)</th></tr>')
        foreach ($t in $TextLogs) {
            [void]$sb.Append('<tr><td class="mono">' + (& $e $t.Path) + '<br><span class="muted">' + (& $e ('{0:yyyy-MM-dd HH:mm}' -f $t.Time)) + '</span></td><td>' + (& $e $t.ExceptionCode) + '<br><span class="muted">' + (& $e $t.KeyLine) + '</span></td><td class="mono chain">' + (& $e (($t.Modules | Select-Object -First 25) -join ', ')) + '</td></tr>')
        }
        [void]$sb.Append('</table></div>')
    }

    [void]$sb.Append('<h2>What changed on this PC</h2>')
    if ($Changes.Count -eq 0) { [void]$sb.Append('<div class="card">No changes found.</div>') }
    else {
        $timeline = @()
        foreach ($ch in $Changes) { $timeline += [pscustomobject]@{ Time = $ch.Time; Kind = $ch.Kind; What = $ch.What; IsCrash = $false } }
        foreach ($c in $Crashes) { $timeline += [pscustomobject]@{ Time = $c.Time; Kind = 'InDesign ' + $c.Kind.ToLower(); What = $c.Blamed; IsCrash = $true } }
        [void]$sb.Append('<details open><summary>Timeline (crashes and changes, newest first)</summary><div class="tablewrap"><table><tr><th>Date</th><th>What</th><th>Details</th></tr>')
        foreach ($t in ($timeline | Sort-Object Time -Descending | Select-Object -First 300)) {
            $style = ''
            if ($t.IsCrash) { $style = ' style="color:var(--strong);font-weight:600"' }
            [void]$sb.Append("<tr$style><td>" + (& $e ('{0:yyyy-MM-dd HH:mm}' -f $t.Time)) + '</td><td>' + (& $e $t.Kind) + '</td><td>' + (& $e $t.What) + '</td></tr>')
        }
        [void]$sb.Append('</table></div></details>')
    }

    [void]$sb.Append('<h2>This PC</h2><div class="card"><table>')
    foreach ($k in $Facts.Keys) { [void]$sb.Append('<tr><th>' + (& $e $k) + '</th><td>' + (& $e $Facts[$k]) + '</td></tr>') }
    foreach ($i in $Installs) { [void]$sb.Append('<tr><th>InDesign</th><td>' + (& $e "$($i.Version) - $($i.Folder)") + '</td></tr>') }
    [void]$sb.Append('</table></div>')

    $third = @(); foreach ($i in $Installs) { $third += $i.ThirdPartyPlugins }
    if ($third.Count -gt 0 -or $Extensions.Count -gt 0 -or $Scripts.Count -gt 0) {
        [void]$sb.Append('<h2>Add-ons in InDesign</h2><div class="tablewrap"><table><tr><th>Type</th><th>Name</th><th>Maker / location</th><th>Added</th></tr>')
        foreach ($p in $third) { [void]$sb.Append('<tr><td>Plug-in</td><td>' + (& $e $p.Name) + '</td><td>' + (& $e $p.Maker) + '<br><span class="mono muted">' + (& $e $p.Path) + '</span></td><td>' + (& $e ('{0:yyyy-MM-dd}' -f $p.Added)) + '</td></tr>') }
        foreach ($p in $Extensions) { [void]$sb.Append('<tr><td>Extension panel</td><td>' + (& $e $p.Name) + '</td><td class="mono muted">' + (& $e $p.Path) + '</td><td>' + (& $e ('{0:yyyy-MM-dd}' -f $p.Added)) + '</td></tr>') }
        foreach ($p in $Scripts) { [void]$sb.Append('<tr><td>Startup script</td><td>' + (& $e $p.Name) + '</td><td class="mono muted">' + (& $e $p.Path) + '</td><td>' + (& $e ('{0:yyyy-MM-dd}' -f $p.Added)) + '</td></tr>') }
        [void]$sb.Append('</table></div>')
    }

    if ($script:Notes.Count -gt 0) {
        [void]$sb.Append('<details><summary>Notes from the tool</summary><ul>')
        foreach ($n in $script:Notes) { [void]$sb.Append('<li>' + (& $e $n) + '</li>') }
        [void]$sb.Append('</ul></details>')
    }

    [void]$sb.Append('<h2>Copy this for Adobe support or an AI helper</h2>')
    [void]$sb.Append('<div class="card"><p>Everything above as plain text. Click the button, then paste it into a chat or support ticket.</p>')
    [void]$sb.Append('<p><button onclick="var t=document.getElementById(''sum'');t.select();document.execCommand(''copy'');this.textContent=''Copied''">Copy all</button></p>')
    [void]$sb.Append('<textarea id="sum" readonly>' + (& $e $TextSummary) + '</textarea></div>')
    [void]$sb.Append('</main></body></html>')
    return $sb.ToString()
}

# ---------------------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------------------
function Invoke-CrashDoctor {
    Write-Host ''
    Write-Host 'InDesign Crash Doctor' -ForegroundColor White
    Write-Host '=====================' -ForegroundColor White

    if ($EnableCrashDumps) { Set-CrashCapture $true; return }
    if ($DisableCrashDumps) { Set-CrashCapture $false; return }

    # The .bat launcher passes several dropped folders as one text, separated by ;
    $ExtraFolder = @($ExtraFolder | ForEach-Object { $_ -split ';' } | ForEach-Object { $_.Trim().Trim('"') } | Where-Object { $_ })
    foreach ($x in $ExtraFolder) { if (-not (Test-Path -LiteralPath $x)) { Add-Note "Could not find the folder you gave: $x" } }
    $since = (Get-Date).AddDays(-$Days)
    $all = @()

    Write-Step 'Reading the Windows Event Log...'
    $all += Get-EventLogCrashes $since

    Write-Step 'Reading Windows Error Reporting files...'
    $werCrashes = @(Get-WerCrashes $since)
    $all += $werCrashes

    Write-Step 'Looking for crash files (.dmp) and crash logs...'
    $files = @(Find-CrashFiles $since $ExtraFolder)
    foreach ($w in $werCrashes) { foreach ($f in $w.Files) { if ($f -match '\.(dmp|mdmp)$') { $files += Get-Item -LiteralPath $f -ErrorAction SilentlyContinue } } }
    $files = @($files | Where-Object { $_ } | Sort-Object FullName -Unique)
    $textLogs = @()
    $dumpCount = 0
    foreach ($f in $files) {
        if ($f.Extension -match '^\.(dmp|mdmp)$') {
            Write-Step "Reading crash file $($f.Name) ..."
            $d = Read-MiniDump $f.FullName
            if (-not $d -or -not $d.IsInDesign) { continue }
            $dumpCount++
            $t = $d.Time
            if (-not $t) { $t = $f.LastWriteTime }
            $dbg = ''
            if ($UseDebugger) { Write-Step 'Running the Windows debugger (this can take a few minutes the first time)...'; $dbg = Invoke-Debugger $f.FullName }
            $all += [pscustomobject]@{
                Time = $t; Kind = 'Crash'; AppVersion = $d.AppVersion; Module = $d.Module; ModulePath = $d.ModulePath; ModuleVersion = $d.ModuleVersion
                ExceptionCode = $d.ExceptionCode; ExceptionDetail = $d.ExceptionDetail; Offset = $d.Offset; ThrownBy = $d.ThrownBy; ThrownByPath = $d.ThrownByPath
                Chain = $d.Chain; ChainPaths = $d.ChainPaths; LoadedModules = $d.LoadedModules; DebuggerOutput = $dbg
                Sources = @('Crash file'); Files = @($f.FullName)
            }
        } else {
            $t = Read-TextCrashLog $f.FullName
            if ($t) { $textLogs += $t }
        }
    }

    $crashes = @(Merge-Crashes $all)
    foreach ($c in $crashes) { Set-Blame $c }

    Write-Step 'Checking MT Log for the document that was open...'
    $mtUsed = Add-MtLogContext $crashes (Get-MtLogFolders $MtLogFolder)

    Write-Step 'Checking this PC (InDesign, plug-ins, graphics card, memory, fonts)...'
    $facts = Get-SystemFacts
    $installs = @(Get-InDesignInstalls)
    if ($installs.Count -eq 0) { Add-Note 'InDesign was not found in Program Files\Adobe.' }
    $extensions = @(Get-Extensions)
    $scripts = @(Get-StartupScripts)

    Write-Step 'Looking for things that changed on this PC...'
    $changes = @(Get-Changes $since.AddDays(-14))

    $captureOn = Get-CrashCaptureOn
    if ($captureOn -and $dumpCount -eq 0) { Add-Note 'Crash capture is on, but no InDesign crash files were found yet. Adobe''s own crash reporter may be catching the crashes first; in that case its files are in the Adobe CRLogs folder or your temp folder.' }

    $verdict = Get-Verdict $crashes $changes $installs $extensions $scripts $textLogs $captureOn $Days
    $summary = Build-TextSummary $crashes $verdict $facts $installs $changes $textLogs $Days
    foreach ($c in $crashes) { if ($c.DebuggerOutput) { $summary += "`r`n== Debugger output for crash at $($c.Time) ==`r`n" + $c.DebuggerOutput } }
    $html = Build-Html $crashes $verdict $facts $installs $extensions $scripts $changes $textLogs $summary $captureOn $mtUsed $Days

    if (-not $OutFolder) { $OutFolder = Join-Path ([Environment]::GetFolderPath('Desktop')) 'InDesign Crash Report' }
    New-Item -ItemType Directory -Path $OutFolder -Force | Out-Null
    $stamp = Get-Date -Format 'yyyy-MM-dd_HHmm'
    $htmlPath = Join-Path $OutFolder "InDesign Crash Report $stamp.html"
    $txtPath = Join-Path $OutFolder "InDesign Crash Report $stamp.txt"
    $jsonPath = Join-Path $OutFolder "InDesign Crash Report $stamp.json"
    [System.IO.File]::WriteAllText($htmlPath, $html, (New-Object System.Text.UTF8Encoding($true)))
    [System.IO.File]::WriteAllText($txtPath, $summary, (New-Object System.Text.UTF8Encoding($true)))
    $raw = [ordered]@{ tool_version = $script:ToolVersion; made = (Get-Date).ToString('o'); days = $Days
                       crashes = @($crashes | Select-Object Time, Kind, AppVersion, Module, ModuleVersion, ModulePath, ExceptionCode, ExceptionDetail, Offset, ThrownBy, Blamed, BlamedPath, Chain, Document, LastActions, Sources, Files)
                       text_logs = $textLogs; changes = $changes; findings = $verdict.Findings; steps = $verdict.Steps; notes = $script:Notes }
    ($raw | ConvertTo-Json -Depth 6) | Out-File -LiteralPath $jsonPath -Encoding utf8

    Write-Host ''
    Write-Host "Found $(@($crashes | Where-Object { $_.Kind -eq 'Crash' }).Count) crash(es), $(@($crashes | Where-Object { $_.Kind -eq 'Freeze' }).Count) freeze(s), $($textLogs.Count) crash log file(s)." -ForegroundColor Green
    $topFinding = $verdict.Findings | Where-Object { $_.Strength -eq 'Strong' } | Select-Object -First 1
    if ($topFinding) { Write-Host ('Main finding: ' + $topFinding.Title) -ForegroundColor Yellow }
    Write-Host "Report saved to: $htmlPath"
    if (-not $NoOpen) { Start-Process -FilePath $htmlPath }
}

# Run unless the file is being dot-sourced (the tests load the functions without running).
if ($MyInvocation.InvocationName -ne '.') { Invoke-CrashDoctor }
