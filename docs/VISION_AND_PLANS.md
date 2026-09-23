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
