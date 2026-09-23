# InDesign Crash Doctor

A small Windows tool that works out **why Adobe InDesign keeps crashing** on a PC.
It reads every crash record on the computer, finds which part of InDesign (or which
outside add-on) was running when it crashed, checks what changed on the PC just
before the crashes started, and writes an easy report with steps to try.

It only **reads**. It does not change InDesign or your files.
Nothing is sent anywhere. The report stays on your PC.

## How to use it

1. Copy the whole `indesign-crash-doctor` folder to the PC (for example to the Desktop).
2. Double-click **`Run InDesign Crash Doctor.bat`**.
3. Wait about a minute. The report opens in your web browser. It is also saved in
   **Desktop → InDesign Crash Report** (as `.html`, `.txt` and `.json`).

**Did you (or an AI) find a folder with crash logs before?** Drag that folder (or the
log file) onto `Run InDesign Crash Doctor.bat`. The tool reads it too.

## For the most exact answer: turn on crash capture

Windows normally keeps only a short note about each crash ("it crashed in file X").
That is often not enough, because many crashes *end* in a general Windows file
(like `ntdll.dll` or `KERNELBASE.dll`) while the real cause is somewhere else.

1. Double-click **`Turn On Crash Capture.bat`** and click **Yes** when Windows asks for
   permission.
2. Use InDesign as normal until it crashes again.
3. Run **`Run InDesign Crash Doctor.bat`** again.

Now each crash has a small crash file (a few MB). The tool reads it directly and shows
the **call chain**: the list of InDesign parts that were active at the moment of the
crash, newest first. For example:

```
KERNELBASE.dll <- ucrtbase.dll <- AcmeImposer.pln <- Text.rpln <- InDesign.exe
```

This means: InDesign was laying out text (`Text.rpln`), called the add-on
`AcmeImposer.pln`, and that add-on raised the error that crashed InDesign.
For C++ errors it also shows exactly which file **raised** the error.

To stop saving crash files later, double-click **`Turn Off Crash Capture.bat`**.

## What the tool looks at

| Where | What it gives |
|---|---|
| Windows Event Log | Time, InDesign version, the file it crashed in, error code, freezes |
| Windows Error Reporting (`Report.wer`) | Same, plus every outside program loaded inside InDesign |
| Crash files (`.dmp`) | Crash place, error details, who raised the error, the call chain |
| Adobe crash logs and your temp folder | Error codes and the file names they mention |
| InDesign folder | Version, non-Adobe plug-ins, extension panels, startup scripts |
| Windows | Updates, driver updates, new programs and new fonts (with dates) |
| This PC | Graphics card and driver, memory, free disk space, number of fonts |
| MT Log (if installed) | Which document was open and the last actions before each crash |

## How to read the report

- **Strong** = clear evidence. Start here.
- **Possible** = worth testing.
- **Info** = background.

"What to try, in this order" lists the steps. Change **one thing at a time** and use
InDesign normally for a while. If the crashes stop, the last thing you changed was
the cause.

At the bottom there is a **Copy all** button: it copies the whole report as plain text,
ready to paste into a chat with an AI helper or an Adobe support ticket.

## Options (for advanced use)

Run from PowerShell:

```powershell
.\InDesignCrashDoctor.ps1 -Days 180                   # look further back (default 90 days)
.\InDesignCrashDoctor.ps1 -ExtraFolder 'C:\Logs\ID'   # also read this folder
.\InDesignCrashDoctor.ps1 -MtLogFolder 'G:\My Drive\Personal\mpp activity'
.\InDesignCrashDoctor.ps1 -UseDebugger                # also run WinDbg's !analyze, if installed
.\InDesignCrashDoctor.ps1 -OutFolder 'C:\Reports' -NoOpen
```

## Limits

- It points to the most likely cause from the evidence. It cannot see inside Adobe's
  own code by function name (Adobe does not publish that), but the file names are enough
  to tell which feature, add-on, font system or driver was involved.
- If Adobe's own crash reporter catches a crash first, Windows may not save a crash file.
  The tool then uses the Adobe log files it can find (drag the folder onto the `.bat` if
  it is somewhere unusual).

## Tests

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\indesign-crash-doctor\tests\Test-CrashDoctor.ps1
```

The tests build small fake crash files and check that they are read correctly.
They run on every push (see `.github/workflows/build.yml`).
