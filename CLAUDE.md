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
   stock/SKU codes (e.g. FTY018, HGC012, MS049) and driver docs. **The DYMO label printer is NOT a
   production printer — never count it toward card output.** But it is gold as a cross-check and activity
   signal: each DYMO label ≈ one order SHIPPED (Amazon order page -> Buy Shipping -> label prints), so the
   DYMO count independently confirms the real order count, and DYMO activity explains "quiet card printer"
   stretches (she's buying/printing shipping labels, not idle). For Kayla, notepads are a separate job —
   count her regular orders only from ~9am on.
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

Worked examples of this done right live in `docs/ANALYSIS_IDEAS.md` (e.g. reprint-vs-edit-vs-cleaning
detection, per-order dwell time, clicks-per-order, cross-person diffs).

## Build / verify
- No `dotnet` in the cloud env — C# changes are verified via CI (GitHub Actions `build.yml`).
- One known-flaky test: `AppEndToEndTests.Export_now_writes_to_the_google_drive_folder` — a red ✗ from
  that alone is not a real failure.
- Never put a model identifier in commits, PRs, or any repo artifact.
