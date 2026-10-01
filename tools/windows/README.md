# MT Log — "Record a Task" button

One click to **start** recording a task (with screenshots, for building an SOP), one more
click to **stop**. It just tells the MT Log watcher that's already running — the same thing as
`MTLog.exe --capture-sop "…"` and `MTLog.exe --capture-stop`, but as a button you can click.

The rest of MT Log keeps logging normally the whole time; this toggle only adds the extra
**screenshots** for the stretch you're recording.

## Files

- **`Record a Task.cmd`** — the button. Double-click it.
- **`Record-a-Task.ps1`** — the script it runs (does the actual start/stop).

## Set it up (once)

1. Copy both files to a permanent spot, e.g. `C:\MT Log\`.
2. Right-click **`Record a Task.cmd`** → **Show more options** → **Send to → Desktop (create shortcut)**.
3. (Optional) Pin it: right-click the shortcut → **Pin to taskbar**, so it's one click any time.
4. (Optional) Give it a keyboard shortcut: right-click the shortcut → **Properties** →
   click the **Shortcut key** box → press e.g. `Ctrl+Alt+R` → **OK**.

## Use it

- **First click:** a little box asks *"What task are you recording?"* — type a short name
  (used to name the SOP) and press Enter. Recording starts.
- **Second click:** recording stops.

A small popup confirms each time (it closes itself after ~2 seconds).

## Notes

- It finds `MTLog.exe` in the usual install spots automatically. If yours is elsewhere, open
  `Record-a-Task.ps1` and add the path to the `Find-MTLog` list at the top.
- The button remembers "am I recording?" with a tiny flag file in
  `%LOCALAPPDATA%\MT Log\recording.flag`. If things ever get out of sync, just click once more
  to stop, or delete that file.
- Everyday detail (before→after values, ads tagging, etc.) is captured **always** — you only
  use this button when you want the **screenshots** for a step-by-step how-to.
