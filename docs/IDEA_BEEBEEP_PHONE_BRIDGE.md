# Separate idea — BeeBEEP → phone bridge (reply by email)

**Status:** idea only (not part of MT Log; a small standalone `.exe`).
**Goal:** when someone messages me on **BeeBEEP** (the office LAN messenger), I get it on
my **phone**, and I can **reply from my phone** — and my reply shows up back **in BeeBEEP**
for the coworker. **No Telegram** — use **email** as the pipe.

## How it works

**PC → phone**
- A small `.exe` on the PC notices a new incoming BeeBEEP message (by watching BeeBEEP's
  auto-saved chat log file, or by reading its history).
- It **emails** the message to me. On my phone it just arrives in my normal mail app — that's
  the notification. No app to install.

**Phone → back into BeeBEEP**
- I **reply to that email** from my phone.
- The exe checks my inbox (IMAP) every ~30–60 seconds, sees the reply, and **puts it into
  BeeBEEP** — so the coworker sees my answer in BeeBEEP, where they messaged me.

## The matching trick

So the exe knows which conversation a reply belongs to, it puts a hidden tag in the subject:

```
Subject: BeeBEEP from Carolina [BB#7fa2]
```

My reply keeps the tag (`Re: … [BB#7fa2]`), so the exe routes my answer to the right person.

## Two ways to send the reply into BeeBEEP

1. **UI automation** — the exe focuses the BeeBEEP window, picks the person, types the reply,
   presses Enter. Fastest to build; a little fragile if the window layout changes.
2. **Protocol client** — because BeeBEEP is open-source, a small helper can speak its network
   protocol and send directly. More work up front, sturdier after.

## Which channel to the phone? (email vs Telegram vs WhatsApp)

All three can do two-way (get the message + reply back into BeeBEEP). Pick one:

| Channel | Two-way | Allowed & safe | Setup | Speed |
|---|---|---|---|---|
| **Email** (default) | yes | yes | easy (app password) | ~30–60 s |
| **Telegram** (free bot) | yes | yes | easy | instant |
| **WhatsApp — official** (Business Cloud API) | yes | yes | heavier | instant |
| **WhatsApp — web automation** | yes | ⚠️ against ToS, ban risk | medium | instant |

**Email** — no new app, uses the email I already have; just a bit slower (polled ~30–60 s)
and needs an app password.

**Telegram** — a free bot; instant and easiest to match replies; it's "another app".

**WhatsApp (official, Business Cloud API)** — arrives on WhatsApp and I reply there. Catches:
needs a **separate business phone number** (not my personal WhatsApp on the same number), a
Meta app + webhook, and the **24-hour window rule** (after a quiet spell it must re-open with
an approved template); small per-message fees are possible.

**WhatsApp (web automation, e.g. whatsapp-web.js/Baileys)** — free and uses my real account,
but it's **against WhatsApp's terms and the number can get banned**; fragile. Not recommended
for a work number.

**Decision:** start with **email** (simplest, safe). WhatsApp is possible but only worth the
extra setup if WhatsApp specifically is a must — and then via the official Business API, not
the web hack.

## Build order (when picked up)

1. **PC → phone** first (easy, reliable): watch BeeBEEP log → email me each message.
2. **Phone → BeeBEEP** next: read my email replies (IMAP) → send into BeeBEEP (start with UI
   automation).

## Notes / to confirm later

- Turn on BeeBEEP's "save chat automatically" so there's a file to watch (or read its history).
- Decide which email account sends/receives (a dedicated one keeps the inbox clean).
- This is separate from MT Log and the live assistant; it could reuse the same phone-delivery
  idea later, but it stands on its own.
