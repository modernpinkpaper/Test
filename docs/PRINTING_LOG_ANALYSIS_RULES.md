# Printing Team — MT Log Analysis Rules

A plain-English reference of the rules we built for reading the printing team's MT logs.

> **Where the "real" version lives:** The rules Claude actually follows are in **`CLAUDE.md`**
> (the "How to analyze MT Log data" section) at the top of the repo. This file is a readable copy
> so you can review and mark it up. If you change a rule here and want Claude to follow it, either
> edit the matching rule in `CLAUDE.md` too, or just tell Claude "update the log rules" and point at
> the change.

---

## The core standard (always do this)

1. **Trace the actual event timeline — not just totals.** Read what happened between events, in what
   order, with what gaps. Counts (clicks, prints) are a starting point, never the answer.
2. **Test a theory against the raw events.** Form a guess, then find the specific events that prove or
   kill it. Show times, docs, gaps.
3. **List ALL differences when comparing people**, even small/uncertain ones, and flag confidence —
   Dalia decides what matters.
4. **Take the time** — write real scripts over the raw JSONL. One day is a lead, not proof; prefer
   trends over several days.
5. **Account for role/training before calling something a "gap"** (e.g. notepads, or a trainee's
   learning curve). Confirm with Dalia first.
6. **A "why" from the logs is a GUESS, not a fact.** A long/slow block is often physical, not slacking.
7. **Anything physically checkable → give the exact person + time window and say "check the camera."**
   Dalia decides if it's worth it.

## Printer timing (the big one)

8. **"Printer running" = from when the job is SENT to when it finishes.** Pair the `print_job` (submit)
   with its `print_job_finished` by (printer, job_id). Fall back to `[finished − seconds_in_queue,
   finished]` only if there's no matching submit.
9. **Never measure idle as the gap between submit events** — that invents idle time that isn't real.
10. **For "was the person actually away," use the `idle_start`/`idle_end` markers** (`idle_seconds`) —
    that's ground truth, not printer gaps. (Markers only fire after ~5 min of no input.)
11. **Count ALL printers, including the DYMO label printer** for activity — but **never count DYMO
    toward card output** (not a production printer). Each DYMO label ≈ one order shipped, so it's a
    great cross-check and explains "quiet card printer" stretches.
12. Page counts (`total_pages`/`pages_printed`) are unreliable — trust `seconds_in_queue` for timing.

## Counting orders & cards

13. **One order = multiple files** (card, return-address envelope, thank-you, back pieces). Merge all
    pieces per customer before counting, or you massively overcount.
14. **Exclude driver junk** ("Status Inquiry", "Maintenance", "Roller Cleaning" = physical cleaning,
    "about_blank") and stock/SKU codes (e.g. FTY018, HGC012, MS049).
15. **Card quantity = the number in the doc name** ("Name - 130 - FLAT"). Sum each order's quantity
    **once**, not per job (one order prints over several passes).
16. **Link order → print by the customer name** (order numbers 112-xxx appear in claim buttons and zip
    names; printed docs are named by customer).
17. Point at the whole `mpp activity` folder (not one person) to answer "who did X."

## The two lenses (keep separate)

18. **Output lens (printer speed):** signal = printer idle. The person being busy is irrelevant here.
19. **Productivity lens (is the person working):** signal = the computer not moving (no clicks/typing/
    navigation). Print jobs running do **not** count as the person being active.

## Recoverable time & the engagement table

20. **Recoverable idle = no computer input AND no printer running.** A printer running through a break
    is NOT waste.
21. **Always produce the 4-state engagement table** (% + minutes):
    - 🟢 **Both engaged** — a printer printing AND person working the computer (the goal).
    - 🖨️ **Machine-only** — a printer printing but person off the keyboard (tending/feeding/away).
    - 💻 **Person-only** — person working but NO printer printing (deskwork while machines idle). **The
      main opportunity.**
    - ⚫ **Idle on all fronts** — no printer printing AND off the keyboard = true dead time.
22. **Person-only time is the main opportunity** → fix is "work ahead": prep jobs while printers are
    already running, so the next job fires the instant one finishes.
23. **The smart gap-fill:** move deskwork (verify/claim/research) INTO the windows where the printer
    runs itself, so the printer never stops for it.
24. **"Printer running + person idle" is always an opportunity flag** (could be a hidden physical
    problem like a kraft-feed jam, legit prep, or true idle) — surface each one with its camera window.

## Reporting format (every time)

25. For any time category, give: **each instance's exact duration (min + sec), its exact window
    (start→end local), what she was actually doing, list every instance, and the day total** — and
    mark the biggest chunks so a single big block doesn't hide inside a total made of tiny gaps.

## Print speed & SKU facts (from Dalia)

26. **All printers are the same model** — never blame the printer model for slower per-card.
27. **Ink drives speed:** invites/folded/framed cards are ink-heavy = slower AND need more verifying;
    flat cards are faster and need less verifying.
28. **Annie trains on invites**, so her slower seconds-per-card and bigger verify time are mostly
    product mix, not inefficiency. **Compare print speed like-SKU only** (flat-to-flat).
29. **Printers have "personalities"** — a specific printer struggling with thick/kraft envelopes is a
    likely physical feed problem to confirm on camera, not operator slowness.
30. **"borders2" folder is UNCONFIRMED** — never infer meaning from a folder/file name; ask Dalia.

## Daily report extras

35b. **Flag systems / script changes for the master systems doc (every daily analysis).** End each daily
   report with a short **"Systems-doc updates"** section (or "none noticed"). Flag: a new or renamed/
   version-bumped script/extension/code, a new site/app/tool in the workflow, a new Google Sheet / Firestore
   / tab / file, a changed or dropped step, or a new printer/device. For each: what it is (the name seen),
   who/which PC, when first seen, and what it seems to replace/add. Caveats: the logs see the name + that
   it's used, not the internals — say "pull the script's code to confirm the wiring"; and never infer meaning
   from a name — list it as "noticed, confirm with Dalia," don't assert what it does.

35c. **Surface listing changes — tests + bulk — every daily analysis.** Scan the WHOLE activity folder
   (everyone who edits listings — Dalia, Carolina, Erika, Arantza), not one PC. Detect notable listing
   create/updates (listing edit page + Save/Publish + field changes + SKU/ASIN) and BULK changes (same action
   across many SKUs, or many SKUs in one sitting). Sort into two buckets: **(a) Possible tests** → need
   follow-up: date/time, who, listing SKU/ASIN + title, what changed, platform, suggested +30-day check-back,
   plus a "tests due for follow-up" list; **(b) Bulk / SKU-wide changes** → no reminder, just a dated line
   ("Apr 3 — added XYZ add-on to ~40 wedding-invite listings") so you can answer "when did we do X" later.
   Each is a CANDIDATE you confirm (Type = Test | SKU-wide change) — the logs see the action + fields, not
   the hypothesis. Output = a document you can get emailed (auto-email is a separate scheduled-job + Gmail
   build; until then the analysis produces the document).

## Things NOT to do / blind spots

31. **Don't use "did they open InDesign on this order" as a metric** — everyone's ~100%, it produces a
    false gap.
32. **Throughput gap is usually capacity (printer count / parallelism), not slackness** — check printer
    count before calling someone slower.
33. **MPP never runs out of queued orders** — "nothing to print yet" is never a valid excuse; any
    non-break idle printer is a real missed chance.
34. **Printer count only affects "≥2 running at once"** — it does NOT excuse a low "≥1 running" number.
35. **Blind spots the logs can't see:** text typed inside the InDesign canvas, object moves without the
    InDesign add-on, incoming chat (only what the person types), data inside Firestore/Sheet cells,
    anything spoken. Name the real source instead of guessing.

---

*Worked examples of this analysis done right live in `docs/ANALYSIS_IDEAS.md`.*
