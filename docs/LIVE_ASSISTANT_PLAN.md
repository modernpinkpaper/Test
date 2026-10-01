# Live Assistant — plan (how it works + what it costs)

**Status:** plan, agreed in chat 2026-10-01. Not built yet. This is the design to confirm
before building. It is **separate from the MT Log watcher** (its own app), but it reads the
same logs the watcher already makes.

## What it is (in one line)

A quiet helper that watches your work **as it happens** and, now and then, pops a small
suggestion on your screen with one-click buttons — e.g. *"Erika said the new collection is
ready — add the Amazon ads to your calendar?"* with an **[Add to Calendar]** button.

## What it does

- Reads the MT Log activity **live** (every 1–2 minutes).
- Notices useful moments (a hand-off, a repeated slow task, a reminder you'd want).
- Shows a **sticky pop-up** (stays until you act) with helpful **buttons**.
- Keeps a **memory** of the day so it can connect a morning thing to an afternoon thing.
- Writes down every suggestion it made and what you did with it.

It is **opt-in** and **help-first** — it is not for policing. It only speaks up when there's
something genuinely useful.

---

## How it reads the logs cheaply (important)

The golden rule: **only send the NEW events since the last check — never the whole day over
and over.** Re-reading the whole growing day every few minutes is what makes an AI assistant
expensive ($50–200/day). Sending only what's new keeps it cheap **and** just as fast.

- **Checks every 1–2 minutes** → suggestions arrive well within your 5-minute goal.
- Each check sends: a short, reused instruction (cached, nearly free) + a tiny running
  summary of the day + the handful of new events since last time.

---

## Memory — how far back, and where it lives

- **The recommendations LOG** (the written record of suggestions) is **kept forever**, one file
  per day — look back days/weeks/months.
- **The working MEMORY** it thinks with is mostly **today**, PLUS **still-open items carried
  forward** from recent days (e.g. "still waiting on Carolina"), AND it can **look back several
  days** when a new event connects to an older one. The look-back window is adjustable. It does
  NOT re-read weeks of history every time (slow + costly).
- **Where it saves:** same home as MT Log's data (`%LOCALAPPDATA%\MT Log\`), and it rides along
  in the existing Google Drive export so it's backed up. (If the brain later runs in the cloud,
  memory can live there instead.)

## Memory — how it decides what to keep

No list of priorities from you — it works out what matters on its own, using simple rules
plus judgment. It keeps things likely to **matter later**:

- **Open loops / pending things** — "Erika said the collection is ready", "waiting on Carolina".
- **Decisions & commitments** — "using the new template for holiday cards".
- **Repeating friction** — "jumped between 500 tabs again", "copy-pasted the same thing 15×".
- **Hand-offs between people** — who said what's ready for whom.

It **throws away routine noise** (clicked a text box, switched tools) — those become short
counts, not kept word-for-word. When a later event **closes** an open loop (you upload the
ads), it marks that memory **done** so it stops nagging.

The day's memory is a short running note. This is already included in the cost below.

---

## Which model reads it — the auto-picker

Two layers, and it **switches on its own** (you set it up once; no choosing each time):

- **Layer 1 — the cheap watcher** (runs every 1–2 min): a cheap model (**Haiku**) — or plain
  rules for the obvious stuff like copy-paste repetition — reads the new events. Most checks
  it finds nothing and says nothing → almost no cost. It also **judges** "is this routine, or
  does it need the smart model?"
- **Layer 2 — the smart brain** (only when Layer 1 flags something): it "calls in" a stronger
  model (**Sonnet** or **Opus**) to write a good suggestion. This happens only a few times a
  day, so the premium model barely affects the bill.

You pick the roster once (which cheap model, which smart model); the moment-to-moment choice
is automatic.

---

## The pop-ups and buttons

- **Sticky:** the pop-up **stays open until you click something** — nothing auto-vanishes.
- **The AI chooses which buttons to show** for each suggestion, from a **toolbox** of actions the
  app knows how to do. (A "copy-paste 15×" suggestion shows [Copy the script]; a "collection
  ready" one shows [Add reminder].)
- **The toolbox of actions:**
  - **Open a page** (Amazon listing, a doc, a sheet).
  - **Copy text** (a script, a drafted message) to the clipboard.
  - **Open a file / folder**.
  - **Add to my Project Tracker** → appends the recommendation to the **"AI MT LOG RECS"** tab of
    Dalia's personal tracker, to review later and promote the good ones to real projects.
    Sheet: https://docs.google.com/spreadsheets/d/1nGa74uHh2yhcNdsSgtldylfhL2d7yxhzzYlwvEGPfvw/edit?gid=1731051855
  - **Add a reminder** — **Dalia:** her Google Calendar (personal only). **Team:** NOT her
    calendar — target their **Chrome reminder extension** instead.
  - **Run a saved script / automation** (e.g. a Tampermonkey helper, a .bat).
  - **Draft a message / reply** (put a draft somewhere — never send).
  - **Remind me in 1 hr** / **Dismiss** / **Not helpful** (the last teaches it).
- **Two tiers of buttons:**
  - **Instant & free:** open a page, copy text, pre-fill a form — no AI, no cost.
  - **Actually does it for you** (adds the calendar/reminder, writes to the sheet, posts
    something): needs that service connected with permission. Anything **outward-facing stays
    behind a confirm click** — it never sends/posts on its own.
- **Light "Tab to accept" option** (idea from the Violoop device): for small suggestions, a tiny
  hint by the cursor you accept with one key, instead of a full pop-up.

---

## The recommendations log (kept, per day)

Every suggestion is written to its own daily record:

```
recommendation: "Add Amazon ads to calendar"
why:            Erika messaged 9:12am "collection ready"; you opened Amazon 2:40pm
you did:        clicked "Add to Calendar"
time:           2026-10-01 14:41
```

Good for two things: you can **review what it suggested and whether it helped**, and that
feedback is what makes it **smarter over time**.

---

## More than one person

Each person's PC runs its own copy (or a cheap always-on cloud machine reads each person's
logs). It reads **your** logs and helps **you**; it reads **Erika's** and helps **Erika** —
separately, each on their own screen.

---

## What it costs (per person)

Prices today, per 1 million "tokens" (≈ ¾ of a word): read / say —
**Haiku $1 / $5**, **Sonnet $2 / $10**, **Opus $4 / $20**.

Assuming one busy person (~6 active hours), checking every ~2 min, **new events only**,
rounded up to ~500,000 read + ~10,000 said per day:

| Model | Per day | Per month (22 workdays) |
|---|---|---|
| **Haiku** | ~$0.55 | ~**$12** |
| **Sonnet** | ~$1.10 | ~**$24** |
| **Opus** | ~$2.20 | ~**$48** |

With caching (reusing the instructions cheaply) it's usually **30–40% lower**. Because the
auto-picker keeps Haiku doing the constant watching and only calls the smart model a few times
a day, the real bill sits **close to the Haiku row (~$8–12/person/month)**.

- **Memory** adds almost nothing — it's a short note, already counted above.
- **Buttons** are basically free (opening a page/copying text uses no AI).
- **The trap to avoid:** re-sending the whole day each check → tens of millions of tokens/day
  → $50–200/day. The design above never does this.

---

## Privacy & safety

- Opt-in; help-first, not policing (ignores personal Googling, short breaks, minor things).
- Sensitive values are never read (same rules the watcher already follows).
- Nothing is sent/posted outward without a confirm click.
- The assistant's suggestions and memory stay on the same PC / the company's own storage.

---

## Which AI provider (Anthropic vs OpenAI)

Both are capable for this (reading activity, judging what's worth saying), and both have a cheap
small model + a strong big one — what the cheap-watch/escalate design needs. Lean **Claude** to
start (strong at the "only speak up when useful" judgment and clean structured output for the
buttons/sheet; Haiku→Opus tiering fits). Not locked in: the model is **swappable**, and the real
decision is a cheap **A/B test on one real day of logs**.

## Where it runs — PC vs cloud (open question #1)

- **On the PC:** reads/thinks/shows on your own machine. 👍 data stays local, simplest start.
  👎 install/update per PC; can't message a PC that's off (no after-hours notes).
- **In the cloud:** one small always-on machine reads each person's exported logs and sends
  suggestions back. 👍 one place to manage, always on (after-hours notes work), easier for a team.
  👎 logs leave the PC; small monthly rent; needs a way to push pop-ups back.
- **Suggested:** start on **your PC**; move to a cheap **cloud box** when rolling out to the team.

## Decisions captured

- **Calendar is personal (Dalia only).** The team will NOT use Dalia's Google Calendar; their
  "add reminder" button targets their **Chrome reminder extension** instead.
- **Project Tracker button** writes to the **"AI MT LOG RECS"** tab of Dalia's tracker (link above).
- **AI chooses the buttons** per suggestion from the toolbox.

## Open questions still to settle

1. **Where the smart brain runs** — PC first, cloud later? (suggested above — confirm)
2. **Model roster** — Haiku + Opus-on-call, or Haiku + Sonnet-on-call? (or decide after the A/B test)
3. **Who gets it first** — just you to start, then Erika/Carolina?

---

## Suggested build order

1. **Reader + memory + recommendations log** (no pop-ups yet) — prove it spots good moments
   cheaply, writing suggestions to the daily log so you can judge quality.
2. **Pop-ups + basic buttons** (Open page, Copy, Remind, Dismiss, Not helpful).
3. **Auto-picker** (Haiku watch → escalate to the smart model).
4. **"Do it for me" buttons** (Calendar first), each behind a confirm.
5. Roll out to a second person.
