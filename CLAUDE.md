# MT Log — project & working standard for Claude

This repo is "MT Log": a Windows activity watcher (C#/.NET 8) that logs what people do on their
work PCs to JSONL, plus a live on-PC assistant and offline analysis of those logs. The owner (Dalia)
runs an e-commerce/print business (MPP) with coworkers. Replies to her should be in **simple English**.

## How to analyze MT Log data (READ THIS BEFORE ANSWERING ANY LOG QUESTION)

Dalia's logs are rich — thousands of events per person per day, each stamped with person/PC, time, app,
window, URL, clicks, field values, files, print jobs, and messages. Treat them as a goldmine and do the
work. Do NOT answer log questions from summary counts alone.

**The standard — every time:**
1. **Trace the actual event sequence, not just totals.** Read the timeline: what happened between two
   events, in what order, with what gaps. Aggregate counts (how many clicks, how many prints) are a
   starting point, never the answer.
2. **Test hypotheses against the raw events.** If asked "why is X slow / what's different," form a
   theory and then go find the specific events that confirm or kill it. Show the evidence (times, docs,
   gaps).
3. **Enumerate ALL differences, including uncertain ones.** When comparing people, list even the odd/
   small differences and flag your confidence — let Dalia judge what's meaningful. Don't pre-filter to
   the "clean" answer.
4. **Watch for data traps.** Printer driver jobs ("Status Inquiry", "Maintenance", "about_blank") are
   NOT customer documents. "Roller Cleaning"/"Maintenance" print jobs = physical printer cleaning.
   Order numbers (112-xxxxxxx-xxxxxxx) appear in claim buttons and downloaded zip names; printed docs
   are named by customer, so link order→print via the customer name. Each person's folder is one PC, so
   point at the whole `mpp activity` folder (not one person) to answer "who did X".
   **PRINTER IDLE/BUSY — critical:** a printer stays BUSY long after a job is submitted. Do NOT measure
   idle as the gap between consecutive `print_job` (submit) events — that is wrong and will invent idle
   time that doesn't exist (one real job held a printer 867s/14min). Use `seconds_in_queue` on the
   `print_job_finished` event to build each job's busy interval [finished - seconds_in_queue, finished],
   merge intervals across printers, and only the gaps between merged busy blocks are true idle. Page
   counts (`total_pages`/`pages_printed`) are unreliable (often 0/1); trust `seconds_in_queue` for timing.
   **CANONICAL definition of "printer running" (Dalia's): from when the job is SENT to when it finishes —
   pair the `print_job` (submit) event with its `print_job_finished` by (printer, job_id); the busy
   interval is [submit_time, finished_time].** Fall back to [finished - seconds_in_queue, finished] only
   for an unpaired finished event. This is the true "printer engaged" window; use it for all utilization
   questions. (Do NOT measure idle as gaps between submit events — see above.) Measured with this method:
   Annie's two printers both-running 31% / both-running-and-working 26%; Kayla's two busiest 29% / 26% —
   essentially IDENTICAL, so on two printers Annie matches Kayla; the output gap is Kayla's 3rd printer.
   Key insight: "both printers running at once" tops out ~30% even for the best operator because ONE person
   can only feed two machines so fast — usually one is between jobs while she feeds the other. The human
   feed rate is the real limit on simultaneous two-printer running, not effort.
   (A separate "feed-gaps-merged" view counting <90s between-job gaps as continuous use gives ~44-50%;
   note which definition you're using, but prefer the submit→finished one.)
   **Count ALL printers, including the DYMO label printer** — printing shipping labels IS productive
   work; excluding the DYMO makes label/shipping stretches look falsely idle.
   **For "was the person actually away", use the explicit `idle_start`/`idle_end` events (`idle_seconds`)
   — that is the ground truth, not printer gaps.** A card printer can be quiet while the person is busy
   printing labels or processing orders. Real example: a 59-min card-printer gap was NOT a 59-min break —
   the idle marker showed one ~29-min lunch (idle_seconds 1756), and the rest was DYMO labels + orders.
   Also: more printers / longer queues can keep printing through a break and MASK away-time, so never rank
   people by raw printer-busy % without checking idle markers and printer count.
   **Counting ORDERS (not files):** ONE order prints MULTIPLE files — the card ("Name - 60 - FLD"), the
   return-address envelope ("RA - Name - 60 - KRAFT"), sometimes a thank-you ("TY - Name") and back
   pieces. Merge all pieces per customer (strip "RA -"/"TY -"/"back of", the "- qty - MATERIAL" suffix,
   and "(1)/(2)") before counting, or you massively overcount (59 files were really ~35 orders). Exclude
   stock/SKU codes (e.g. FTY018, HGC012, MS049) and driver docs. **CARD QUANTITY:** the number in the doc
   name ("Name - 130 - FLAT") is the order's card count. For total cards on a printer/day, sum each ORDER's
   quantity ONCE (not per job — one order prints over several passes, so per-job summing massively
   overcounts). total_pages/pages_printed are unreliable and there is no copies field, so the name's "- NN -"
   is the best volume signal. Example: Kayla's 3rd (LEFT SIDE) printer = ~19 orders ≈ 780 cards in a day,
   which accounts for ~20 of the ~25-order Kayla-vs-Annie gap (concrete proof the gap is the 3rd printer). **The DYMO label printer is NOT a
   production printer — never count it toward card output.** But it is gold as a cross-check and activity
   signal: each DYMO label ≈ one order SHIPPED (Amazon order page -> Buy Shipping -> label prints), so the
   DYMO count independently confirms the real order count, and DYMO activity explains "quiet card printer"
   stretches (she's buying/printing shipping labels, not idle). For Kayla, notepads are a separate job —
   count her regular orders only from ~9am on.
   **RECOVERABLE idle (the only "opportunity" worth flagging) = no computer input AND no printer running.**
   A printer running through a break is NOT waste — the machine is producing (printing through lunch = fine).
   So only flag downtime as recoverable when the `idle_start`/`idle_end` (no input) period OVERLAPS a
   stretch where NO printer (card OR DYMO) is active. Time where printers run while the person is away, or
   where printers are idle but the person is actively working (research, labels, orders), is NOT recoverable.
   Measured example: Annie's recoverable idle was ~11 min/day; the rest of her "idle" was lunch or shipping.
   **Do NOT use "did they open InDesign on this order" as a metric.** You MUST open InDesign to print every
   order, so everyone is ~100%; a window-title match undercounts (batch opens, InDesign already in front,
   file name != order name) and produces a false "only 57%" gap. That metric is invalid — don't report it.
   **Throughput gap is usually CAPACITY (printer count / parallelism), not slack.** Two people can log the
   same printer-busy minutes but one completes more orders because more printers run in parallel. Check
   printer count and parallel-run time before concluding someone is "slower".
   **TWO SEPARATE LENSES — keep them distinct:**
   - **Output lens (printer speed):** signal = printer idle (no printer running). Question: how to fill it
     so the machines produce more. Person activity is irrelevant here; a person can be busy while a
     printer sits idle.
   - **Productivity lens (is the person working):** signal = the computer not moving — NO person-driven
     input (clicks/typing/navigation), regardless of printers. Print jobs running do NOT count as person
     activity. A ~30-min no-input stretch while printers run = a break (they left it printing). SHORTER,
     scattered no-input chunks (not a clean long block) = not clicking around = likely chatting / bathroom
     / away from desk → a productivity flag → give Dalia the time window and say check the Ring camera.
     Note: the idle_start/idle_end markers only fire after ~5 min of no input, so for shorter chunks infer
     "hands off" from gaps between person-driven events (ui_action, ui_field_value, browser_page, file_*),
     NOT from print_job events.
   **THE SMART GAP-FILL — cross-reference BOTH timelines (printer busy/idle × person active/idle).**
   To find how someone could be faster, split the day into four quadrants:
   (a) printer running + person working = ideal; (b) printer idle + person idle = break/dead;
   (c) **printer IDLE + person doing desk work** (verify/research/claim) = lost PRINTER time — they stopped
   the printer to do deskwork; (d) **printer RUNNING + person idle** = the fill-able slot (printer runs
   itself while they wait/watch). The optimization: move the deskwork from (c) INTO the (d) windows, so the
   person does verifying/claiming/research WHILE the printer runs, and the printer never stops for it.
   Measured example (Annie, 1 day): both-busy 264m, printer-running/person-idle 46m (fill-able),
   printer-idle/person-working 110m (movable), break 48m. Proven pattern difference: Kayla did 92% of her
   verification while a printer was running; Annie only 52% (she front-loads a verify batch with printers
   idle). Mechanism (measured): avg printers running WHILE she verifies — Kayla 1.9, Annie 0.6; both switch
   windows at the same ~2s cadence, so the edge is NOT multitasking skill, it is keeping printers in flight
   as a buffer so the (inevitable) multitasking rides on top of production that never stops. That resolves
   the batch-vs-flow tension: multitasking's switch cost is real, but you don't pay it in lost PRINTING if a
   machine is always running underneath.
   **The "printer running + person idle" windows (quadrant d) are an OPPORTUNITY FLAG, never a caveat to
   dismiss.** ALWAYS surface each one to Dalia with its camera time-window, because it reveals either: (1) a
   hidden physical PROBLEM (e.g., struggling to feed kraft envelopes) the person may not speak up about —
   Dalia can fix it (talk to them / switch the printer); (2) legit physical prep (feeding/collecting); or
   (3) true idle. And the broader rule: **batching prep — digital OR physical (verifying, envelope prep) —
   while printers sit idle at other times is itself the inefficiency. The fix is to SCATTER that prep so it
   overlaps printing and fills printer-idle gaps.** Flag batched prep that coincides with idle printers.
   **REPORTING FORMAT for any time category (idle, gaps, dead time, etc.) — always:**
   1) Give each instance's duration precisely (minutes AND seconds, e.g. "4 min 12 s"), 2) with its exact
   window (from HH:MM:SS to HH:MM:SS, local), 3) **the DETAILS of that instance — what she was actually
   doing** (foreground window/app, the order/customer/doc involved, which printers were running, and a
   camera-window flag when it is physically verifiable), 4) list every instance (don't just give a total),
   and 5) give the DAY TOTAL for that category. Reason: a 7-min total made of many 30s–1min scattered gaps
   is NOT usable recoverable time, but a single 7-min block is — Dalia needs the per-instance breakdown AND
   the details to tell the difference, judge whether each block is real opportunity vs physical work vs a
   problem, and spot any one big chunk hiding inside a total. Sort or mark the largest instances so big
   chunks stand out.
   **STANDARD ENGAGEMENT TABLE (produce this for any productivity look — Dalia likes it).** Classify every
   moment of the day into exactly one of four states and report each as % AND minutes, per person:
   - 🟢 **Both engaged** — ≥1 printer printing AND person working the computer (the goal).
   - 🖨️ **Machine-only** — ≥1 printer printing but person OFF the keyboard (tending/feeding the printer,
     hand-prepping, or away/slacking). NOT "idle on all fronts" — product is still being made; camera says which.
   - 💻 **Person-only** — person working the computer but NO printer printing (deskwork while machines idle).
     THIS IS THE PRIMARY OPPORTUNITY. The fix (Dalia's): WORK AHEAD — do this prep EARLIER, while printers
     are already printing (during Both-engaged / Machine-only time), so you build a BUFFER of ready-to-print
     jobs. Then the instant a print finishes you fire the next already-prepped job and the printer never waits.
     Goal: shrink Person-only toward a small unavoidable floor (grabbing envelopes, physical bits), not big
     batches of verifying done in dead printer time. Measure success as Person-only % going DOWN over time.
   - ⚫ **Idle on all fronts (Neither)** — no printer printing AND off the keyboard = true dead time
     (break, lunch, away). This is the real "idle everywhere" state.
   "Printer printing" uses the canonical submit→finished definition above; "working" = a person-driven event
   (click/type/navigate) within ~45s. Measured example (same day): Annie 56/9/23/10% vs Kayla 74/5/13/5% —
   the actionable gap is Person-only (Annie 110m vs Kayla 54m, ~56m more deskwork with printers idle).
   ALWAYS SHOW, every productivity output: (1) this four-state table, AND (2) the instance-by-instance
   breakdown of Idle-on-all-fronts (per the reporting format), AND (3) a breakdown of Person-only time BY
   ACTIVITY (InDesign / Google-verify / Amazon / Etsy / chat / files / etc.) with the big blocks and their
   times — separate the unavoidable edges (morning build before files exist, end-of-day, clock-in/out) from
   the recoverable MIDDAY deskwork done while printers sit idle (the work-ahead target). Dalia decides what
   to act on. (Blind spot: without the InDesign add-on / screenshots you cannot see INSIDE the InDesign or
   verify work — say so; it may or may not be reducible.)
   **PRINT SPEED PER CARD matters (Dalia): some cards print slower, so you physically make fewer.** Report
   seconds-per-card per person = sum of card-job durations (submit→finished machine-seconds) ÷ total cards
   (qty once per order). Measured: Annie 29.7 s/card vs Kayla 23.4 s/card (~27% slower). This is a SEPARATE
   factor from printer count and compounds with it. Caveat heavily: the number blends true print speed +
   card-type mix (folded/kraft print slower than flat) + reprints (inflate seconds without adding a card) +
   queue wait — so a high s/card is a lead to investigate, not proof of slowness by itself.
   **FACTS FROM DALIA (apply before blaming print speed):** (1) ALL printers are the SAME model — the printer
   model is NEVER the cause of slower per-card. (2) Per-card print time is driven by the SKU/product: more ink
   on the page = slower. INVITES and FOLDED cards are ink-heavy (slower) AND carry more info to verify; FLAT
   cards are faster and need less verifying. (3) Annie is TRAINING ON INVITES, so her slower s/card AND her
   larger verify time are largely her PRODUCT MIX, not inefficiency — confirmed: ~33% of Annie's cards were
   invite/folded vs Kayla ~93% flat (no invites). Compare print speed LIKE-SKU only (flat-to-flat); never
   rank people on blended s/card across different product mixes. (4) Printers are heavily used and have
   "personalities" — a given printer can struggle to feed thicker/certain-color envelopes (the kraft-feed
   issue); treat recurring Machine-only stalls on a specific printer/stock as a likely physical feed problem
   to confirm on camera, not operator slowness.
   **FRAMED designs (borders) are another slow-SKU factor like invites (Dalia):** a frame prints slower
   (ink top-to-bottom of the border) AND takes time to center, often causing a nudge-to-center → reprint
   loop. DETECTING a frame: (1) POSSIBLE but UNCONFIRMED — logs show a Desktop folder `...\borders2` opened/
   searched with .indd files ps067/fs002/ml004/ks249 ("... RIGHT.indd") (Kayla 51 accesses/day, Annie 0). I
   ASSUMED from the name this is border/frame art; Dalia has NOT confirmed what this folder or those codes
   are — do NOT treat "borders2 access = framed order" as fact until she says so. LESSON: never infer meaning
   from a folder/file name alone; ask Dalia. (2) The InDesign add-on as-is only shows "an object moved", not that it's a
   frame. (3) ENHANCE the add-on to log, per touched object: type (rectangle/graphic/text), whether it
   holds a placed image + that file's name (a border file ⇒ the frame), its bounds (near page size ⇒ likely
   the frame), and its script label (if frame objects are labeled, that's the direct tag). Then you can tag
   "adjusted the FRAME (border file X) → reprint" and count the centering-reprint loop. Treat framed orders
   like invites when judging s/card — compare like-SKU.
   CONFOUNDS to state every time: (1) a full-day window (setup+lunch) drags the % vs a 9am-on window —
   normalize before ranking. (2) Printer count matters ONLY for "≥2/both running at once" (parallel
   capacity) — it does NOT affect "≥1 running": anyone with one printer and queued work can keep one going,
   so never excuse a low "≥1 printer + working" number by saying the other person has more printers (wrong).
   For a low "≥1 running" number, the real causes are the window and time spent working-while-no-printer-runs
   (Person-only). NOTE (Dalia, business fact): MPP NEVER runs out of queued orders — there is always
   something that could be printing. So "nothing left to print yet" is NOT a valid explanation, ever. Any
   printer-idle moment that is not a break is a real missed opportunity — the person could always have had a
   printer running. Treat ALL non-break Person-only / idle-printer time as recoverable (minus the small
   unavoidable physical floor: grabbing envelopes, collecting prints).
5. **Account for role/training before calling something a "gap".** A difference may be a different job
   the person isn't trained on (e.g. notepads), or normal learning-curve slowness for a trainee — not a
   flaw. Confirm with Dalia before recommending a process change.
6. **Know the blind spots and say them.** The logs do NOT capture: text typed inside InDesign canvas,
   object moves/resizes without the InDesign `.jsx` add-on, incoming chat messages (only what the
   person types), actual data inside Firestore/Sheet cells, or anything spoken. For those, name the real
   source (the script's code, the actual sheet, the add-on) instead of guessing.
7. **Take the time.** Write and run real analysis scripts over the raw JSONL. One day of data is a lead,
   not proof — prefer trends over multiple days when judging a person.
8. **A "why" from the logs is a HYPOTHESIS, not a fact — and a long/slow block is often PHYSICAL, not
   inefficiency.** The logs show WHAT happened on screen, rarely WHY. Do not state a motive as fact
   ("she's taking too long deciding", "she's not cleaning enough"). Real example: a 7-minute "dwell" on
   an order page looked like slow verifying — the camera showed she was hand-feeding thick KRAFT
   envelopes (a known printer feed problem). The digital time was real; the cause was physical.
9. **Any guess that is physically verifiable → ALWAYS tell Dalia to check the cameras, and let HER
   decide if it's worth it.** Whenever an inference could be confirmed by what was physically happening
   (a long dwell, reprints with no edits, a stall, a gap between prints, a printer error, anything where
   the cause is off-screen), state it as a guess AND hand Dalia the exact **person/PC + precise time
   window (start→end, local time)** and say "check the camera for this window." Do NOT pre-judge whether
   it's worth digging into — surface it every time; Dalia decides. The logs + cameras together turn a
   guess into a confirmed root cause (and sometimes a solution, like "kraft envelopes need a different
   printer/feeder").
10. **FLAG SYSTEMS / SCRIPT CHANGES for Dalia's master systems document (every daily analysis).** As you
   read the day, watch for any sign the tools/systems changed, and end the report with a short
   **"Systems-doc updates"** section listing them (or "none noticed"). Flag: a NEW or renamed/version-bumped
   script, extension, or code (e.g. `mpp-CLAIM-BUTTONS-v3.2` → `v3.3`, a new Tampermonkey userscript, a new
   `.jsx`), a new site/app/tool showing up in the workflow, a new Google Sheet / Firestore / tab / file in
   use, a changed step order or a step that disappeared, or a new printer/device. For each, give: what it is
   (by the name seen in the logs), who/which PC, the date/time first seen, and what it seems to replace or
   add. CAVEATS: the logs see the NAME and that it was used, not the internals — say "pull the script's code
   to confirm the wiring" (see ANALYSIS_IDEAS #20); and NEVER infer meaning from a name alone — list it as
   "noticed, confirm with Dalia", don't assert what it does. This keeps Dalia's master systems doc current.

Worked examples of this done right live in `docs/ANALYSIS_IDEAS.md` (e.g. reprint-vs-edit-vs-cleaning
detection, per-order dwell time, clicks-per-order, cross-person diffs).

## Build / verify
- No `dotnet` in the cloud env — C# changes are verified via CI (GitHub Actions `build.yml`).
- One known-flaky test: `AppEndToEndTests.Export_now_writes_to_the_google_drive_folder` — a red ✗ from
  that alone is not a real failure.
- Never put a model identifier in commits, PRs, or any repo artifact.
