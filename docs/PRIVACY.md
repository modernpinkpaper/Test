# Privacy and security

MPP Watcher is for **company-owned PCs** to understand business work. It is built to
record *what kind of work* happened, not private content.

## Never collected (by design, not by setting)

- Screenshots, screen video, webcam, microphone or any audio
- Keystrokes. There is no keyboard hook. Idle detection only asks Windows
  *"how long since the last input?"* (`GetLastInputInfo`)
- Mouse positions or click coordinates
- Passwords, PINs, card numbers, CVV, bank details, SSNs, one-time codes, API keys
- Browser cookies, saved passwords, session tokens
- Clipboard contents
- Program command lines (they can contain secrets)
- File contents (no reading or hashing of files)

## What is collected (Phases 1–2)

- Which app/window is in front, its **window title**, and for how long
- Active vs idle time (no keyboard/mouse for 5 minutes by default)
- Lock/unlock, sleep/wake, sign-out
- Which programs start and stop (name, exe path, run time)
- Watcher health information
- Finished values of changed, non-sensitive form fields (e.g. Search, SKU) and the names of
  buttons/links/tabs clicked (e.g. Save, Publish)

Window titles can contain document names, web page titles and email subjects. If a
title must not be logged, block it (below).

## Field values and clicks (Phase 2)

- Only the **finished** value of a field is read from Windows, when the person leaves the
  field or stops typing for a few seconds. Keystrokes are never seen or stored.
- Only fields that were **changed** are recorded.
- Values longer than 200 characters or with line breaks (e.g. an email body or a message
  to a customer) are **not stored**; only their length is.
- For a click, Windows is asked which control is under the mouse. The **click position is
  used once and discarded**, never stored. Only clicks on *named* buttons, links, tabs,
  menu items and check boxes are recorded.
- The watcher never records anything about its own windows (viewer, inspector).

## Sensitive fields

A field is **always** skipped if:

- Windows marks it as a password/protected field, or
- its name, automation id, label, help text or class contains a sensitive term:
  password, passcode, PIN, secret, CVV/CVC, card number, expiry, SSN/social security,
  tax id, passport, bank/account/routing number, IBAN, SWIFT, OTP/verification/auth/2FA code,
  token, API key, private key, credential, date of birth…, or
- its value *looks like* a card number (passes the Luhn check), an SSN, or a long token/JWT.

For password fields the value is **not even read** from Windows. For the other cases the
decision is made before anything is written. This built-in list **cannot be turned off**. Admins can only add terms
(`privacy.sensitive_field_terms`). The matching is word-based, so "Shipping address"
is not confused with "PIN".

## URLs (Phase 3 onward, sanitizer already built)

Before any URL is stored: `user:password@` is removed; query parameters such as
`token`, `access_token`, `code`, `state`, `session_id`, `sid`, `key`, `signature`,
`X-Amz-Signature`, `oauth_*`, `openid.*` are removed; OAuth tokens in `#fragment`s are
removed. Only `http`/`https` URLs are kept. Admins can add parameter names.

## Exclusions

Admin-controlled in `config.json` → `privacy`:

| Rule | Example |
|---|---|
| `blocked_applications` | `"KeePass*"`, `"WhatsApp"` |
| `blocked_window_titles` | `"*Payroll*"`, `"*Private*"` |
| `blocked_domains` | `"*bank*"`, `"mail.google.com"` |
| `allowed_domains` | if set, only these sites are logged in detail |
| `blocked_urls` | `"*/checkout*"` |
| `blocked_folders` | `"C:\\Users\\*\\Documents\\Personal*"` (Phase 4) |
| `blocked_controls` | `"*Notes*"` (Phase 2) |

`blocked_mode`:
- `redact` (default): time is still counted ("20 s in an excluded app"), but app name,
  title, URL and all details are replaced with `[excluded]`. Also, if a session ends by
  switching *to* a blocked app, that app's name is hidden in the previous session's
  `next_application`.
- `drop`: nothing is written for that activity.

Defaults block password managers (KeePass, 1Password, Bitwarden, LastPass, Dashlane,
NordPass, RoboForm), the Windows credential prompt, sign-in screens, banking domains,
and checkout/payment/login URLs.

## Where data lives and who can see it

- Each Windows user's events are stored under their own `%LOCALAPPDATA%\MPP Watcher`
  (normal Windows file permissions).
- The config in `%ProgramData%\MPP Watcher` is readable by users, writable only by admins.
- Exports go only where the admin configures. No data leaves the PC otherwise.
  There is no network code in Phases 1–2.

## Transparency

By default a tray icon says *"MPP Watcher – activity logging is on"*. We recommend
telling employees in writing what is collected (this document can be shared) and
checking local law on workplace monitoring and notice.
