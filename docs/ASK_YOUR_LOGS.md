# Ask your logs (query MT Log with Claude Code)

The exported logs are plain-text JSONL, so you can open the folder in **Claude Code** (desktop
app or CLI) and just ask questions in plain English — no special tool needed. This is separate
from the live assistant; it's on-demand Q&A over what already happened.

## Set it up (once)

Point Claude Code at your **shared `mpp activity` folder** (the Google Drive one everyone exports
into), so it can see each person's daily logs:

```
…\My Drive\Personal\mpp activity\
   <Employee>_<PC>\
      2026-09-28\
         events_0900_1000_<PC>.jsonl
         …
```

Open that folder as the working directory in Claude Code, then ask away.

## Example questions

- "When did Erika add SKU FBA_TY001 to the variation family with FTY?"
- "What did Carolina work on this morning, and how long on each thing?"
- "Show every time anyone opened the SKU MA023 listing editor this week."
- "When did the Spring Catalog.indd file get saved, and by whom?"
- "How many print jobs went to the label printer yesterday, and were there any paper-out errors?"

## What it can answer well — and the honest limits

- **Well:** when something happened, who (which PC/employee), which app/screen, which SKU/ASIN/
  listing/order, field values that were finished, clicks on named buttons, files saved/printed,
  before→after values (e.g. an ads bid change). All timestamped.
- **To ask about a coworker, their logs must be in the shared folder** (their watcher running +
  exporting). You can't query what wasn't captured.
- It answers from **captured actions**, so things like "added to the variation family" are
  **inferred** from the Seller Central variation-wizard screen + the SKUs in the fields at that
  time — not a literal logged sentence. Usually enough to pinpoint the when/who/where.
- **Not captured:** raw keystrokes, the exact text typed (only finished field values, which can be
  partial), passwords/sensitive fields (never logged). See [PRIVACY.md](PRIVACY.md).

## Make it faster/sharper (optional)

Copy the drop-in `CLAUDE.md` below into the `mpp activity` folder. Claude Code reads it
automatically and will know the log format and how to search.

```markdown
# MT Log activity logs — how to read them

These are MT Log activity events: one JSON object per line (.jsonl), under
`<Employee>_<PC>/<yyyy-MM-dd>/events_*.jsonl`. Each event has: timestamp_utc, timestamp_local,
employee_id, computer_id, event_type, application, window_title, url, domain, page_title,
session_id, and an event-specific `metadata` object. Full field reference: see the project's
docs/EVENT_SCHEMA.md.

To answer a question:
- Search by the identifier first (SKU/ASIN/listing id/order number/file name) with ripgrep across
  the .jsonl files, then read the surrounding lines for context.
- Use `metadata` for details: field values (ui_field_value: label/value/previous_value), clicks
  (ui_action: control_name), browser pages (browser_page: site/page_type/module/filters, e.g.
  Amazon Ads campaign_id/ad_program), files, print jobs, and InDesign events.
- Report the when (local time), who (employee_id/computer_id), and where (app/site/screen).
- Be honest when an action is inferred from surrounding events rather than logged literally, and
  say if the relevant logs aren't present.
```

(That `CLAUDE.md` is just guidance; it doesn't change any data.)
