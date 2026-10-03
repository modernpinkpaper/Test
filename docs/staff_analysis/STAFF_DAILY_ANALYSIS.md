# Staff daily analysis from MT Log: what it must include

This is the recipe for the "one person's workday" page made from their MT Log. It covers how to read the
logs, what sections the page has, and the rules to follow. Copy this folder into any repo that needs it.

Files in this folder:
- `STAFF_DAILY_ANALYSIS.md`: this file.
- `build_timeline.py`: turns one PC's JSONL logs into a readable timeline (`python build_timeline.py <folder> <PCID> tl.txt`).

---

## 1. The golden rule: trace events, never summarize counts

- **Do not answer from summary counts.** "42 print jobs" or "3 hours in Chrome" is not an answer.
- **Read the whole timeline in order:** what happened, what happened next, and how long the gap was.
- **Test every theory against the specific events.** If you think an order was skipped, find its order page,
  its prints and its label, or show they are missing.
- **Check other PCs when it matters.** Team members use each other's PCs (clocking in or out on Wi-Fi trouble
  is normal). Before calling something odd, look at the other person's log for the same minutes.
- **Say what the log can't see.** MT Log was off, a click wasn't captured, only chat previews were logged.
  Say "the log can't prove this" instead of guessing.

## 2. How to read the logs

**Main event types**
- `app_session_end`: which window was used, from `session_start`, with `active_seconds`.
- `browser_page`: `page_type`, `order_ids`, `headings`, the URL.
- `ui_action` (clicks) and `ui_field_value` (what was typed or picked).
- `print_job` and `print_job_finished`: `document_name`, `printer`, `pages_printed`, `status`.
- `file_*`, `idle_*`, `watcher_*` (MT Log starting and stopping), lock and unlock.

**Cleaning the timeline**
- Make a short copy that drops noise: "Tab Flyout", "Memory usage", Rundll32, and app sessions under 4 seconds.
- Keep the full copy for checking details.

**Following one order from start to finish**
1. The order detail page opens.
2. The card prints, then the RA (envelope) prints.
3. The buy-shipping page opens, or "Buy Shipping" is clicked.
4. A DYMO label prints within about 45 seconds.
- Some clicks are not captured. A DYMO print seconds after the shipping page counts as a label bought.

**Batches:** count orders per batch from the traced orders, not from print totals.

## 3. Page sections, in this order

1. **Header:** name, date, clock in and out, active hours.
2. **The big result:** what they actually finished (orders shipped, listings made, a project moved forward).
   Use numbers from traced events.
3. **Where the time went:** time per app or task, plus the longest stretches and breaks.
4. **At a glance:** a few short facts (lunch or no lunch, printers used, people they helped).
5. **The day, in order:** time blocks with a short title and plain-English steps. Mention order names or
   SKUs only where they help find the item.
6. **Problems to resolve or look into.** This is the most important part. See section 4.
7. **Master systems document updates (new).** See section 5.

## 4. Problems to resolve or look into

Every item must point to specific events (time, order, file, click). Group them:

- **Look into first:** things that could hurt a customer or cost money. Examples: a note pasted on the
  wrong order, a name typo on a printed card, a buyer message with no reply, a label bought before a fix.
- **Check with them:** habits that may be fine but should be confirmed. Examples: clicking "Bypass" on a
  warning, loading tools from an old "archive" folder, many reprints of the same envelope.
- **Equipment and tech:** printer paused or degraded, deep cleans, Wi-Fi drops, Drive not synced, error files
  made by a script.
- **Good to know:** not problems, but useful. Examples: no lunch break logged, duplicate copies of order files
  open, a normal team habit explained.
- **Unfinished, no follow-up, not documented:** work started but not finished, questions asked with no answer,
  things that should have been written in a note or sheet but weren't.

Write each item as: **short title**, then what the log shows, then the next step. Give each a checkbox
(saved in the browser with `localStorage`, wrapped in try/catch).

Before calling something a problem, check whether it is normal practice. Known normal practices:
- Pasting the obituary used to check a customization into the seller notes.
- Clocking in or out on another team member's PC when Wi-Fi is down.

## 5. Master systems document updates (new)

List anything in the day's log that means the **master systems document** may need an update. For each one,
write what changed, where it was seen (time, file, app), and which part of the master doc it likely affects.

Look for:
- **Scripts and code:** a new or edited script (Apps Script, PowerShell, InDesign startup scripts, browser
  extensions, Python), a new version installed, a script run from a new folder, a script that made an error file.
- **New tools or settings:** a new app or extension installed or uninstalled, new environment variables,
  new API keys or web-app links, new scheduled jobs or workflows (for example an Amazon Seller Assistant workflow).
- **Changed steps:** a new order of steps, a new sheet tab or column (for example an "Ink Choice" column),
  a new folder or file name pattern, a new template, a new printer or printer setting.
- **Rules said in chat:** a new rule or "from now on" message in Teams or BeeBEEP.
- **Workarounds:** someone repeating a manual fix many times, which means the documented step doesn't work.

If nothing changed, say "No system changes seen today." Never paste keys, passwords or PINs. Name the
item and where it lives instead.

## 6. Privacy and safety rules

- Hide time-clock PINs, API keys and passwords.
- Leave out personal chats (relationships, health, family) unless they affect the work.
- Customer names only where needed to find an order. Never share the page outside the team.
- Keep the person's raw logs out of git.

## 7. Style

- Simple English, short sentences, plain words.
- Times in 12-hour format (8:15 AM).
- Light and dark mode, readable on a phone.
