// MPP Watcher — helper for Tampermonkey / Violentmonkey scripts.
// Paste this into your userscript (or @require it) and call mppReport({...}) when the script does work.
//
// Your script header needs:
//   // @grant        GM_xmlhttpRequest
//   // @connect      127.0.0.1
//
// MPP_SECRET must match "local_api.shared_secret" in %ProgramData%\MPP Watcher\config.json
// (ask the admin). Events are only accepted from this PC, signed with this secret.

const MPP_SECRET = 'PUT-THE-SHARED-SECRET-HERE';
const MPP_PORT = 47821;

async function mppSign(secret, message) {
  const key = await crypto.subtle.importKey('raw', new TextEncoder().encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const sig = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(message));
  return Array.from(new Uint8Array(sig)).map(b => b.toString(16).padStart(2, '0')).join('');
}

/**
 * Report something your script did.
 * @param {object} e  { event_type: 'automation_run', script_name: 'MPP Etsy Customization Updater',
 *                      sku: 'PS142', listing_id: '123456789', asin, order_id, description, data: {...} }
 */
async function mppReport(e) {
  const body = JSON.stringify(e);
  const ts = Math.floor(Date.now() / 1000).toString();
  const signature = await mppSign(MPP_SECRET, ts + '.' + body);
  return new Promise((resolve) => {
    GM_xmlhttpRequest({
      method: 'POST',
      url: `http://127.0.0.1:${MPP_PORT}/v1/events`,
      headers: { 'Content-Type': 'application/json', 'X-MPP-Timestamp': ts, 'X-MPP-Signature': signature },
      data: body,
      timeout: 3000,
      onload: (r) => resolve(r.status === 202),
      onerror: () => resolve(false),   // watcher not running: never break the script
      ontimeout: () => resolve(false),
    });
  });
}

// Example:
// await mppReport({ event_type: 'automation_run', script_name: 'MPP Etsy Customization Updater',
//                   sku: 'PS142', listing_id: '123456789', description: 'Updated personalization fields' });
