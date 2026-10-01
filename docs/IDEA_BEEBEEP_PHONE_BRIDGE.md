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

## Trade-offs vs Telegram

- ✅ No new app; uses the email I already have.
- ⏳ Slower than Telegram — email is checked every ~30–60 s (not instant). Fine for normal
  replies, not for rapid back-and-forth.
- 🔧 One-time setup: an email **app password** so the exe can read the inbox and send.

## Build order (when picked up)

1. **PC → phone** first (easy, reliable): watch BeeBEEP log → email me each message.
2. **Phone → BeeBEEP** next: read my email replies (IMAP) → send into BeeBEEP (start with UI
   automation).

## Notes / to confirm later

- Turn on BeeBEEP's "save chat automatically" so there's a file to watch (or read its history).
- Decide which email account sends/receives (a dedicated one keeps the inbox clean).
- This is separate from MT Log and the live assistant; it could reuse the same phone-delivery
  idea later, but it stands on its own.
