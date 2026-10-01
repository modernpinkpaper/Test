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
- **Buttons** depend on the suggestion. Examples:
  - **[Add to Google Calendar]** — opens the calendar with the event pre-filled.
  - **[Copy / install this script]** — e.g. a Tampermonkey script to speed up a task.
  - **[Open file / folder / Amazon listing]**.
  - **[Add to task list]**.
  - **[Remind me in 1 hr]** — hides it, brings it back later.
  - **[Dismiss]** — closes it.
  - **[Not helpful]** — closes it *and* teaches the assistant (feedback).
- **Two tiers of buttons:**
  - **Instant & free:** open a page, copy text, pre-fill a form — no AI, no cost.
  - **Actually does it for you** (truly creates the calendar event, posts something): needs
    that service connected with permission. Anything **outward-facing stays behind a confirm
    click** — it never sends/posts on its own.

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

## Open questions to settle before building

1. **Where the smart brain runs** — each person's PC, or one cheap always-on cloud machine
   reading everyone's logs? (Cloud is simpler to manage; PC keeps data local.)
2. **Which services get the "do it for me" buttons first** (Google Calendar is the obvious
   first; anything else?).
3. **Model roster** — start Haiku + Opus-on-call, or Haiku + Sonnet-on-call?
4. **Who gets it first** — just you to start, then Erika/Carolina?

---

## Suggested build order

1. **Reader + memory + recommendations log** (no pop-ups yet) — prove it spots good moments
   cheaply, writing suggestions to the daily log so you can judge quality.
2. **Pop-ups + basic buttons** (Open page, Copy, Remind, Dismiss, Not helpful).
3. **Auto-picker** (Haiku watch → escalate to the smart model).
4. **"Do it for me" buttons** (Calendar first), each behind a confirm.
5. Roll out to a second person.
