# MT Log — Analysis Ideas (prompt base for AI)

A running list of everything Dalia wants to learn from MT Log data. Each item = the GOAL, the DATA it
uses, and the CAVEATS. Use any of these as the base of a prompt when handing logs to AI.

Reminder of what the regular (always-on) logs contain, per event:
timestamp (UTC + local), computer/PC, employee/PC label, app, window title, domain/URL, page type,
SKUs / ASINs / listing IDs / order numbers, clicks (ui_action, with control name), finished field
values (ui_field_value), files opened/saved/downloaded, print jobs (printer, document, pages,
seconds_in_queue), chat/message text, idle chunks, app-session durations. Screenshots only during an
SOP recording.

## 1. Daily productivity report (per person)
Goal: per-person daily summary in Google Sheets — time per category, with collapsible detail rows.
Data: app sessions + durations, domains, SKUs/orders/listings, files. Caveat: "completed" left to Dalia.

## 2. Time / friction ("why did this take so long?")
Goal: explain where time went — interruptions, waiting, rework loops, help-lookups, click friction.
Data: session gaps, idle chunks, repeated reopens, ChatGPT/Google "how do I" detours, app switching.
Caveat: explains the computer half; physical work not captured.

## 3. Evergreen / ongoing-work finder
Goal: spot recurring filler tasks -> propose an "evergreen sheet" for when there's nothing to print.
Data: repeated activities across people. Caveat: "listings that don't sell" needs sales data or Dalia.

## 4. Project-step reconstruction (high level, "what to do")
Goal: rebuild the steps of a project (e.g. create KS collection) as what-to-do, not click-by-click.
Data: ordinary always-on logs (tool/site/file/order arc). Grouping by SKU/file/collection clues.
Caveat: rougher than a labeled recording; AI may mis-file a vague line.

## 5. Automation-opportunity roadmap (ranked)
Goal: "watch me do a task once -> ranked plan to automate it." Two axes: effort to build
(easy/med/hard) x automation level (full/partial/low) x time saved x path (script only vs human sets
up / stays in loop). Data: a recorded (or ordinary) run of the process. Caveat: estimates; flag steps
that can't be automated (no API, 2FA/captcha, judgment).

## 6. Staff-friction / file-issue finder
Goal: surface recurring friction (e.g. "missing clipart links -> please fix, Erika") to fix or script.
Data: recurring chat messages + rework/handoff loops. Caveat: can't inspect a file's internal state.

## 7. Work-type auto-categorization + difficulty grades
Goal: label each activity by type AND difficulty grade (e.g. listing edit G1 easy/tool, G2 manual,
G3 several fields) -> compare who does high- vs low-level work (raises, expected durations).
Data: field-change counts, tool/script use, time. Caveat: estimate; rubric tuned over time.

## 8. You vs AI/automation attribution
Goal: separate what a person did themselves from what Claude/automation did for them.
Status: needs the "who filled this field" flag (planned).

## 9. Requests / prompts log
Goal: timeline of what someone asked (ChatGPT/Claude/teammates). Data: chat/prompt field values.
Caveat: captured on focus-leave, so sometimes partial.

## 10. Print team — per-hour count + tracker auto-fill
Goal: start/end of counted printing, prints per hour, auto-fill the print log sheet.
Data: print_job / print_job_finished (printer, document, pages, seconds_in_queue). Exclude notepads and
other non-counted jobs by Dalia's rules (name/folder/printer). Count PAGES not just jobs.
Caveat: exclusion needs jobs to be distinguishable; "finished" = left the Windows queue (good proxy).

## 11. Print team — per-SKU print time + speed analysis
Goal: how long each SKU takes to print (ink-heavy vs light) and the gap before the next job (how fast
she lines up the next). Rank what makes the fast person fast. Data: print job timing + workflow.
Caveat: computer half only; physical technique inferred as hypotheses to confirm by observing.

## 12. Printer out-of-paper / errors (feature to build)
Goal: "who lets the printer run out, how often, time lost" -> restocking recommendations.
Data: printer error state via WMI (to be added).

## 13. Training doc / narrated animated video
Goal: turn a best-person recording into a training doc, or a narrated animated video.
Data: SOP recording (steps + screenshots) for the computer half + Dalia's WRITTEN physical steps.
Pipeline (downstream): AI script (narration + scene directions) -> AI voice -> AI animation.
Caveat: stylized, not her real office; physical work must be written by Dalia; separate creative tools.

## 14. Amazon Ads decision capture -> SP/SB SOP or ads app
Goal: learn her ad decision rules by campaign type, then write an SOP or spec an ads app.
Data: Decision recording (what she did) PAIRED with the real ad numbers (downloaded reports / Ads API).
Caveat: MT Log doesn't read on-screen table numbers; pair with report files for the metrics.

## 15. MPP Project Tracker auto-fill (Google Sheet)
Goal: auto-update each person's tab: time, what was done, links, steps.
Blocked on: Dalia's answers to the tracker questions (esp. matching work->project, done definition,
which links). Needs a listing-ID/ASIN -> SKU lookup (listings are identified by SKU).

## How to use this file
Pick an item, copy its Goal + Data + Caveat, add the specific logs, and tell AI: "using these MT Log
files, do [Goal]; the data available is [Data]; respect [Caveat]; output as [format]." That is the base
of the prompt.
