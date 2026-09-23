# Local event API (for your own scripts and tools)

Your Tampermonkey scripts and other tools can tell MPP Watcher what they did, e.g.

```
event_type:  automation_run
script_name: MPP Etsy Customization Updater
sku:         PS142
listing_id:  123456789
```

The event is stored like every other event (same employee, computer, time fields) with
`collector: "local_api"`. No interpretation is done.

## Security

- Listens on **127.0.0.1 only** (this PC). Nothing on the network can reach it.
- Every request must be **signed** with a shared secret (HMAC-SHA256) and carry a timestamp.
  Unsigned, wrongly signed, older than 5 minutes, or repeated requests are refused.
- Requests from ordinary web pages (they send an `Origin` header) are refused. Userscript managers
  (Tampermonkey's `GM_xmlhttpRequest`) and desktop tools are accepted.
- Strict body: only the fields below; extra details go in `data`. Max 16 KB. Rate-limited.
- A program running as the same Windows user could read the secret — this stops casual spoofing,
  not a determined insider. Keep the secret in company scripts only.

The secret: set `local_api.shared_secret` in `config.json` (one secret for all PCs and scripts).
If it is empty, each user gets a random secret in `%LOCALAPPDATA%\MPP Watcher\data\api-secret.txt`.

## Request

```
POST http://127.0.0.1:47821/v1/events
Content-Type: application/json
X-MPP-Timestamp: <unix seconds>
X-MPP-Signature: hex( HMAC-SHA256( secret, "<timestamp>.<body>" ) )

{ "event_type": "automation_run",          // required, lowercase letters/digits/_
  "script_name": "MPP Etsy Customization Updater",   // required
  "sku": "PS142", "listing_id": "123456789", "asin": "B0...", "order_id": "112-...",
  "description": "Updated personalization fields",
  "timestamp": "2026-09-22T14:04:17Z",      // optional, defaults to now
  "data": { "fields_changed": 3 } }         // optional, any extra details
```

Answers: `202` accepted (with `event_id`), `400` bad body, `401` signature/timestamp,
`403` sent from a web page, `409` replay, `413` too large, `429` too many.
`GET /v1/health` answers `{"ok":true}` without a signature.

If several people are signed in to one PC at the same time, the second watcher uses the next free
port (47822, ...).

## Tampermonkey

Use [`tools/mpp-watcher-client.user.js`](../tools/mpp-watcher-client.user.js): add
`@grant GM_xmlhttpRequest` and `@connect 127.0.0.1` to your script, paste the helper, set the secret,
then call:

```js
await mppReport({ event_type: 'automation_run', script_name: 'MPP Etsy Customization Updater',
                  sku: 'PS142', listing_id: '123456789' });
```

`mppReport` never throws: if the watcher is not running, your script carries on.

## PowerShell / other tools

```powershell
$secret = 'the-shared-secret'
$body = '{"event_type":"automation_run","script_name":"Label printer batch","sku":"MA023"}'
$ts = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds().ToString()
$hmac = [System.Security.Cryptography.HMACSHA256]::new([Text.Encoding]::UTF8.GetBytes($secret))
$sig = -join ($hmac.ComputeHash([Text.Encoding]::UTF8.GetBytes("$ts.$body")) | ForEach-Object { $_.ToString('x2') })
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:47821/v1/events -Body $body -ContentType 'application/json' `
  -Headers @{ 'X-MPP-Timestamp' = $ts; 'X-MPP-Signature' = $sig }
```
