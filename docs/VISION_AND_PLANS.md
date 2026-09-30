# MT Log — Vision and Future Plans

This file records where MT Log is headed, in plain language, so the goal is not lost.
Nothing here is built yet. It is a plan to work from later.

## The big goal

MT Log records what a person actually does on their PC (facts only, no AI inside the app).
Later, an AI reads those logs — **in one central place, never on the employee PCs** — to do useful things:

1. **Turn a real process into an SOP.**
   Instead of writing a how-to from memory, do the task once while MT Log records it,
   then have the AI read the log and write a step-by-step SOP document. Good for training
   new team members.

2. **Learn how Dalia makes decisions, then build a tool that copies those decisions.**
   The hardest things to explain are judgement calls (especially Amazon Ads). Rather than
   explain it, let MT Log watch it. The AI reads the log, works out the decision rules, and
   writes a spec (a markdown doc) that Codex / Claude Code can use to build a web app. That
   app would connect to the Amazon Ads API and help make (or make) those decisions the same
   way Dalia does today.

Key rule kept throughout: **the AI never runs on the employee PCs.** The PCs only log facts.
All interpretation happens centrally.

## Project 1 — Link MT Log to the MPP Project Tracker (Google Sheet)

Goal: read each person's log and update their tab in the MPP Project Tracker automatically —
time spent, what was done, and the links they used — instead of relying on people to type it in.

Tracker facts already known (from the sheet "MPP Project Tracker"):
- One tab per person (e.g. Erika).
- Rows are `PROJECT` or `STEP` (a step belongs to a project via Project ID / Parent ID).
- Columns: Type, Project ID (P-004…), Parent ID, Name, Details, Linked Sheet, Status,
  Progress %, Started/Blocked, Completed, Blocked Reason, Notes, Assigned To, Deadline.
- Status is stamped with date/time, e.g. `In Progress [08/18/2026 11:53 AM]`.
- Work types: Amazon/Etsy/Shopify listings, InDesign design, SKU work, RA files, photos, FBA, research.

How it would work: central daily job → group each person's day into work blocks →
ask the AI which project each block belongs to → update matched rows (time, notes, links) →
leave "needs review" notes for blocks it cannot match confidently. It only adds notes/links;
it does not silently overwrite what a person typed.

### Open questions to answer before building (most important: 2, 3, 5)

1. **Purpose:** Progress, time measurement, accountability, planning — which matters most? Who reads it?
2. **Matching work to a project:** Do SKUs (FTY039, PS368), listing IDs, or file names map to a
   P-number? Is there a master list (SKU → project)? How to split work that touches two projects?
   What to do when nothing matches (note in tab / "needs review" / nothing)?
3. **Done / blocked:** What tells you a STEP is finished (file saved? listing published? Dalia's
   approval?)? May MT Log set "Completed", or only suggest it? How to tell blocked vs just slow?
4. **Time:** Want time-per-step? Where (Notes or a new column)? Remove idle/breaks? Active time or
   whole span?
5. **Links/files:** Which links matter (Seller Central, Etsy/Shopify URLs, Google Docs/Sheets,
   Keepa, files opened/saved)? Which column do they go in? File names/paths or only web links?
6. **Tabs/assignment:** Tab name = person's name = the MT Log employee ID? If a project is not
   assigned to them but they worked on it, add a row or just note it?
7. **Write-back safety:** Ever overwrite a person's cell, or only add beside it? If AI and person
   disagree, who wins and how is the conflict shown? Update once a day or live?
8. **Team & privacy:** Are staff OK with PC activity filling the tracker? Anything that must never
   reach it (personal sites, lunch)?
9. **Tracker quirks:** Copy the `In Progress [date time]` format exactly? Are `/`, `n/a`,
   "linked file missing" meaningful? Is Progress % a guess or steps-done ÷ total?

## Project 2 — Capture Amazon Ads decisions well enough to write an SP/SB SOP or an ads app

Goal: record how Dalia manages ads in enough detail that the AI can (a) write an SOP specific to
each campaign type, and (b) later produce a spec for an ads-management web app that connects to the
Amazon Ads API and makes the same decisions.

Important: the SOP/app must stay **specific**, not generic. E.g. "for SP campaigns on MA SKUs:
if a target is bad over 30 days, check 60 days; if still good over 60, leave the bid; if bad over
both, lower the bid; if the search term report shows irrelevant terms, pause it." SB campaigns for a
given product type and targeting strategy are treated separately — not all campaigns/ad groups are equal.

### What MT Log captures today in the Ads console
- That you were there, the page/URL and title.
- Buttons clicked (by label): Pause, Add keywords, date-range picker, etc.
- Values you finish typing into a normal field (a bid you set, a keyword you add).
- Files you download (search term reports, bulk sheets) — the file, not its contents.
- The order of actions.

### What it does NOT capture today (the gap)
- **The numbers you read on screen** — ACOS, spend, clicks, 30-day vs 60-day columns, the actual
  search terms. It does not read on-screen tables (no screenshots, no scraping). This is the "why".
- **Campaign structure/type** — SP vs SB vs SD, campaign name, ad group, specific target are not
  tagged. There is no special handling for the Ads console yet.
- **Before→after of a change** — the old bid, the target it belonged to, and the performance context.

So today the AI can describe the *workflow/path*, but cannot state the *decision rules by campaign
type*, because the data behind the decisions is missing. It would be guessing the numbers.

### Manual "Decision Capture" toggle (Dalia's design)

Always-on deep capture would be annoying and noisy. Instead, add a tray toggle:
- Right-click tray -> "Start Decision Capture". Normal facts logging keeps running; this ALSO turns on
  the extra detail needed to reverse-engineer a decision (ad screens, reports opened, fields changed),
  and tags every event in that window as part of a decision-capture session.
- Right-click tray -> "Stop Decision Capture" when done.
- The AI later reads only the tagged stretch and turns it into an SOP.

This keeps everyday logs light and only records the heavier detail when Dalia chooses. Note: even in
this mode, on-screen table numbers (ACOS, spend, etc.) still are not read — pair with report files /
the Ads API for the numbers (see below).

### How to close the gap (two pieces, not one)
1. **"What you did" — from MT Log.** Add Ads-console handling that tags each action with campaign
   type (SP/SB/SD), campaign, ad group, target, and records bid old→new, pauses, keyword adds, and
   which report/date-range was open.
2. **"The numbers you acted on" — from the data, not the screen.** Pair MT Log's actions with the
   real ad data: the report/bulk files you download (MT Log already logs those) or the Amazon Ads
   API. Exact metrics, not screen guesses.

Combine the two and the AI can line up "paused this target" with "its search terms were irrelevant
and ACOS was X over both 30 and 60 days", then write an SP-specific SOP separate from SB — and later a
spec for the ads app.

## Project 3 — "Why is this taking so long?" (time / friction analysis)

Goal: beyond how long a task took and how many items were done, explain WHERE the time went.
Strong fit for MT Log because it records the shape of the work, not just totals.

Example: an employee updating all PS-SKU Amazon listings. A report could show:
- Per-SKU time and spread (which SKUs ate the time, not just the average).
- Interruptions: time spent off-task (email, chat, personal sites) and how often.
- Waiting: idle gaps and page/save waits (e.g. Amazon slow to save).
- Rework / loops: same listing reopened, same field re-edited, back-and-forth between tools.
- Help detours: time asking ChatGPT/Google "how do I…" → flags a missing SOP or training gap.
- Click-count friction: one item taking far more steps than needed.

Honest limit: it explains slowness from switching/waiting/rework/help-lookups. It cannot tell that a
listing was genuinely complex unless the log has a clue (SKU, file) or the paired platform data.

## Done — identify each PC's logs by the PC name (no list to maintain)

MT Log captures `computer_id` (PC name) and `windows_username` on every event automatically, and the
log file name already ends with the PC name, e.g. `events_1000_1100_DALIALAPTOP.jsonl`.

Change made: when no employee id is configured, the `employee_id` field and the export folder now use
the **PC name** instead of "unassigned-<login>". One PC = one person, so the PC name identifies who,
with nothing to maintain. When an employee leaves and a new hire takes that PC, the PC name is
unchanged and the logs keep flowing under it — no roster, no per-PC edit. Setting employee_id is
optional, only if a different label than the PC name is wanted.

## Shared building block for both projects

Both need the same thing: a **central "brain" job** that reads the uploaded logs (and, for ads, the
downloaded report files or the Ads API), calls an AI to interpret them, and writes the result
(tracker rows, an SOP doc, or an app spec). Build this once; reuse it for tracker updates, SOP
generation, and ads-decision capture.

## Order of work (suggested)
1. Finish and stabilise MT Log on Dalia's own PC, then the team's PCs. (in progress)
2. Central brain: read a day of logs → produce a plain facts summary (no AI) → then AI SOP draft.
3. Project 1: tracker link (answer questions 2, 3, 5 first).
4. Project 2: Ads-console tagging + pair with report files / Ads API → SP/SB SOP → ads app spec.

## Project 4 — Daily productivity & process report, per person (Dalia's answers, 2026-09-28)

Primary purpose: DOCUMENT and IMPROVE process (many processes are figured out as we go, so capturing
what a task actually involved and how long it took helps us refine it later). Secondary: time /
productivity, eventually feeding a raise calculator. For Dalia's eyes only; she may have AI produce a
cleaned-up version to share with the team. Trust the employees — this is not for policing.

Decisions:
- Nothing is left out of the logs on purpose (keys/secrets included — do NOT add a skip rule).
- Idle is logged in chunks (already is: idle_start/idle_end with seconds) so Dalia can, if needed,
  check in with someone, or spot that they are being interrupted/distracted (more likely than slacking)
  and fix the cause (e.g. tell teammates to message on chat instead of interrupting), or leave a note
  the person can see later.
- Capture ALL identifiers: platform + URL, order numbers, SKUs, ASINs, Etsy listing IDs, file names,
  and what was being done, with details.
- Pattern-spotting across SKUs: when the same change is made to many SKUs, report it ONCE and give the
  SKU RANGE (e.g. "MS050-MS058, MS060-MS067" — split the range where there is a gap), then say what the
  change was and on which platform.
- "Completed" is left to Dalia. The report says "worked on X for Y min", never declares done.
- Separate what Dalia/employee did themselves vs what Claude/automation did for them (see near-term flag).

Presentation:
- Daily summary PER PERSON.
- Detailed but collapsible: a summary row you can click to expand the detail underneath. => Google Sheets
  is the right home (spreadsheet-ready rows + collapsible grouping). Columns roughly:
  Start | End | Min | Person | Category | Grade | Platform | IDs | What was done | Flags.
- Cadence: daily for now (may change).
- Output: Google Sheet (leaning), so it can later plug into a raise/productivity calculator.

Flags to surface (first list; refine later):
- Lots of switching (e.g. one order reopened 6+ times, or many app-switches/hour)
- Long idle chunk (gap over a threshold)
- Interruption-driven (chat/Teams repeatedly pulled them off task)
- Tool-assisted vs manual
- Stuck / help-seeking (repeated ChatGPT/Google "how do I" on one task)
- High-complexity work (good for raises)
- Took longer than usual for this task type
- Unclear / needs Dalia's input (could not match to a project)
- Personal time (shown separately, never hidden)

### Auto-categorize the TYPE of work, with difficulty GRADES
Why: later Dalia can see if employee A worked mostly on low-level tasks while employee B did high-level
work — for raises and for setting fair expected durations.

Each activity gets a category AND a difficulty grade within that category. Example for "edit/update a
listing":
- Grade 1 (easy): changed ONE field AND used a tool/script to help.
- Grade 2 (medium): changed one field but had to MANUALLY copy-paste it in.
- Grade 3 (hard): changed SEVERAL different fields in the listing.
MT Log can estimate this from how many distinct fields were touched, whether a tool/script was involved,
and time taken. The grade is a good estimate Dalia confirms/adjusts; the rubric grows over time.

Buckets/categories: TBD with Dalia (she'll get back on how to group the day). Candidates seen in real
logs: order fulfillment, listing edits, script/automation building, project-tracker upkeep, FBA
shipping, team coordination, research/help, personal.

## Near-term feature — flag who filled a field: human vs AI/automation (approved)

Today MT Log records a field's finished value but not WHO caused it, so it cannot prove Claude/cowork
filled a form vs the person typing it (seen 2026-09-28: Claude filled the TikTok developer app details
after Dalia asked it to; only the surrounding prompts imply this). Plan: mark a field change that happens
with NO human keystroke/mouse click just before it as "likely automated / AI-filled", so reports and SOPs
can separate "Dalia did X" from "Claude did X for her". Also useful for honest time accounting.

## Requests / prompts log (approved use)
Keep recording what is typed into chat/AI/prompt boxes (ChatGPT, Claude, BeeBEEP, Teams) so a report can
show a simple timeline of when Dalia asked for something. Limit: values are captured when focus leaves
the box, so a prompt may be captured partially, not always the final full wording.

## Identifier rule correction (Dalia, 2026-09-29)
- ORDERS: identify by ORDER NUMBER (already captured for Etsy/Amazon/Shopify).
- LISTINGS: Dalia identifies listings by SKU, not by URL/listing ID. Today's logs capture the Etsy
  listing ID (from the URL) and the Amazon ASIN, and a SKU only when she searches inventory by SKU.
  GAP: to report listings by SKU, add a lookup table (Etsy listing ID / Amazon ASIN -> MPP SKU), which
  Dalia likely already has in a sheet. The report/brain translates listing ID/ASIN -> SKU automatically.
- "Why a task happened" (e.g. jsx script update): MT Log captures the TYPE/reason from the request text
  and chat title (e.g. she asked Claude about a "JSON parsing error" opening the MPP orders JSON), but
  NOT the exact error text/line or what the fix changed (those live in the file + the AI reply, which
  MT Log does not read). Prompts are captured on focus-leave, so they can be partial.

## Rollout approach (Dalia, 2026-09-29): collect real data first, design later
- Install MT Log on the team PCs and let it run ~1-2 weeks, then review the real logs to decide the
  categories, grades, identifiers, and report format from actual work patterns (rather than guessing).
- Intent is patterns/help, NOT policing: Dalia does NOT care about personal Googling, short breaks,
  or minor things. Reports should surface only MEANINGFUL patterns — a problem, or a chance to help
  someone optimize (e.g. "jumps between many projects -> suggest focusing on one at a time + give tools").
  Reports should NOT nitpick benign personal activity or normal breaks.
- Disclosure timing is Dalia's decision (company-owned PCs at her workplace). Low-risk: activity
  metadata. Higher-risk: message/chat CONTENT capture -> the standard cover is a one-line
  "we may monitor activity on company devices" acceptable-use / handbook clause, added if/when she
  discloses. Not a blocker to collecting data now.
- Setup check: all team PCs run Google Drive for desktop. Confirm whether each is signed into Dalia's
  own Google account (logs reach her, but employees could open her whole Drive) vs a shared folder /
  dedicated logging account (safer). This decides where logs land.

## Confirmed features to build (Dalia, 2026-09-29)
1. Decision Capture toggle — CONFIRMED (ads decision reverse-engineering; see Project 2).
2. Weekly zip — CONFIRMED. After each finished WEEK, per PC, zip that PC's date folders into one
   weekly .zip (e.g. DALIAOFFICEPC_2026-W40.zip), then DELETE the raw .jsonl. Only touches closed
   days already synced (never the day in progress). Dalia never browses single files; she sends the
   batch to AI. Purpose is tidiness (space is fine on paid Drive). Analysis unzips to read.
3. Higher detail default — Dalia is fine on space; capture richer per-event context during the
   data-gathering phase so patterns are richer.

## "Record Task" capture mode -> super-detailed SOPs (Dalia wants: "teach a newborn baby")
One tray toggle mechanism, shared with Decision Capture:
- Start Recording -> ask for a short LABEL (e.g. "Create RA file for a KS order") and purpose
  (SOP or decision). Tag every event in the window with that label + capture_mode.
- Capture EVERY step in high fidelity: each click (control name + path), each finished field, each
  menu/tab, each page/URL, files opened/saved, in order.
- Stop -> AI reads only the tagged stretch and writes a step-by-step SOP with the real SKUs/paths used.

OPEN DECISION (reverses the original no-screenshot rule):
- (a) Text-only SOP: keeps no-screenshot rule; detailed word steps from the click/field trail.
- (b) Optional screenshots ONLY while an SOP recording is on (off the rest of the time): makes
  picture-perfect SOPs but means the tool can screen-capture during those deliberate recordings.
Dalia to choose (a) or (b). Claude's suggestion: (b) strictly scoped to SOP recordings only.

## Handling interruptions during an SOP/Task recording (Dalia, 2026-09-29)
Concern: while recording an SOP she might answer employee chats or quickly check something online.
Handling (do BOTH):
1. Auto-clean: every step is tagged with app/site + time, so the AI building the SOP drops off-task
   detours (BeeBEEP/Teams messages, unrelated Google searches) and keeps only the task's real steps.
2. Pause/Resume button in the tray: pause -> handle the interruption (no steps, no screenshots captured)
   -> resume for clean recording.
Safety net: the SOP is a DRAFT Dalia reviews; stray steps can be removed on review or a second AI pass.
Net: a few chats or a quick lookup mid-recording will NOT ruin the SOP; she can record naturally.

## Report types from ORDINARY logs (no SOP/Decision recording needed) (Dalia, 2026-09-30)
All read by the central brain over a batch of everyday logs:

1. Evergreen / ongoing-work finder: spot recurring low-value or filler tasks people repeat, suggest an
   "evergreen sheet" of work to do when there's nothing to print. Caveat: "listings that don't sell"
   needs sales data (pair with Amazon/Etsy numbers or Dalia judges); the log shows the repeated edits.
2. Reconstruct project steps for the MPP tracker from past logs (rough draft to confirm). Works via
   SKU/order/file matching; less polished than a deliberate SOP recording, good enough to auto-fill and
   tidy.
3. Automation-opportunity finder: detect repetitive mechanical sequences and rank easy->hard to
   automate ("top 5 automatable tasks, with why"), then build scripts. Strong fit.
4. Staff-friction / file-issue finder: mainly via recurring CHAT messages (e.g. "file missing clipart
   links, Erika please update") plus rework/handoff loops; flag recurring friction to fix or script.
   Limit: the log does not inspect a file's internal state (e.g. broken links) — it sees the messages
   about it and the activity pattern.
