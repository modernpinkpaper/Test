# InDesign Lag Watcher

Notices when InDesign freezes ("lags") and writes down what was going on at
that moment. It only reads; it never changes InDesign, files or settings.

## Turn it on

1. Copy this folder to the PC (for example Kayla's).
2. Double-click **Turn On Lag Watcher.bat**. No admin needed.

It runs quietly in the background and starts again by itself after a restart.
A **Lag Watcher Logs** shortcut is put on the Desktop.

To turn it off: double-click **Turn Off Lag Watcher.bat** (logs are kept).

## How it works

Every 2 seconds it sends InDesign's window a harmless "are you there?" message
and times the answer. No answer within 1 second = a lag has started. While
the lag lasts it checks every second. When InDesign answers again, it writes
one entry with:

- start, end and how many seconds it lasted
- the document and the window that was on screen (for example the Print box)
- **why (best guess)**: InDesign BUSY working, or WAITING on something
  (a printer, a G: file, another program), low memory, a busy disk
- InDesign CPU, memory, GDI/USER objects, MB read/written during the lag
- the busiest other programs, printer status, print queue and spooler
- whether Google Drive had just restarted

Freezes under 2 seconds are only counted ("hitches"). Every 5 minutes it
writes a short health line.

## Logs

`C:\MPP Lag Watcher\Logs` (or `%LOCALAPPDATA%\MPP Lag Watcher\Logs`):

- `Lag Log <date>.txt` - easy to read
- `lag-events.jsonl` - the same details, for matching against MT Log

## Tests

`tests\Test-LagWatcher.ps1` (no Pester). On Windows it also runs a fake
"InDesign" window that freezes for 6 seconds and checks the lag is logged.
