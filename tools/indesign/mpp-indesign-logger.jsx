#targetengine "mppIndesignLogger"
/*
 * MT Log — InDesign activity logger (ExtendScript / .jsx)   —   v2
 * ---------------------------------------------------------------
 * Runs INSIDE Adobe InDesign and quietly writes down what you do while you design:
 * which document you opened, which object or text box you selected (and its script
 * label, even while you are typing in it), which tool you picked, which swatch/ink
 * colour is applied, which menu commands and menu-scripts you ran, and when you
 * edited or saved. One local backup file per day, and (optionally) sent live to MT Log.
 *
 * Two ways to run it (see tools/indesign/README.md):
 *   1. Double-click it once from InDesign's Scripts panel (Window > Utilities > Scripts).
 *      It then logs for the rest of that InDesign session — no need to click again.
 *   2. Drop it in InDesign's "startup scripts" folder so it starts on its own every
 *      time InDesign opens.
 *
 * Safe by design: every handler is wrapped in try/catch, so a logging hiccup can never
 * interrupt your InDesign work or pop up an error while you design.
 *
 * WHAT IT CANNOT SEE (limits of InDesign scripting, not bugs):
 *   - Raw keyboard keys / shortcuts  (InDesign never exposes the keyboard to scripts;
 *     the RESULT is still caught, e.g. the tool changing).
 *   - The actual letters you typed    (only lengths/structure, to keep the log small
 *     and avoid copying customer text into the log).
 *   - Scripts you DOUBLE-CLICK in the Scripts panel (InDesign fires no event for those;
 *     menu commands and menu-scripts ARE caught — see below).
 *   - A panel being clicked/opened (Swatches, Stroke, …). InDesign fires no "panel"
 *     event — BUT v3 watches the RESULT of using those panels: which swatch you edited
 *     and to what colour, what the stroke/fill/weight/opacity became, which style, font
 *     or size you applied. That is the useful part.
 */

// ====================================================================================
//  SETTINGS — the only part most people need to touch
// ====================================================================================
var CONFIG = {
    // Hand each action LIVE to MT Log via its local API (127.0.0.1). MT Log then stamps
    // it with this PC's name + the employee + the date and files it in that person's day.
    SEND_TO_MT_LOG: true,

    // The secret that lets this script talk to MT Log. LEAVE THIS BLANK — the script now
    // reads it automatically from MT Log's own file (api-secret.txt) on this PC, so there
    // is nothing to paste and a MT Log reinstall can't break it. Only set a value here if
    // you deliberately run a custom secret (then it must match MT Log's config).
    SHARED_SECRET: "",
    PORT: 47821,

    // Keep a local .jsonl copy of the day's InDesign actions on this PC, as a backup and an
    // easy way to confirm logging is working (even if the live link to MT Log is down). MT
    // Log is still the main destination; this is just a safety net. Set false to turn off.
    LOG_TO_FILE: true,

    // How often (ms) to check tool / active doc / swatch edits / stroke & style changes.
    POLL_MS: 2000,

    // Don't log the same selection more than once per this many ms (stops click spam).
    SELECTION_MIN_GAP_MS: 800,

    // Watch for SWATCH edits: a swatch added, removed, renamed, or recoloured (and to what).
    WATCH_SWATCHES: true,

    // Watch the selected object for CHANGES: position (x/y) & how far it moved, size,
    // rotation, stroke colour/weight/style, fill, opacity, and (for text) font, size,
    // paragraph/character style — reporting what changed to what.
    WATCH_ATTRS: true,

    // Also log menu COMMANDS (Export, Print, Place, …) and menu-scripts you run.
    LOG_COMMANDS: true,

    // Only used if LOG_TO_FILE is true.
    KEEP_BACKUP_DAYS: 30,
    OUTPUT_FOLDER: ""
};

// Menu commands we care about (normalised: lower-case, no "..."/"$ID/"). You asked to
// drop Package, Table and Data Merge, and to ignore View/Window noise — done.
var WANTED_COMMANDS = {
    // File / output
    "new document": 1, "open": 1, "close": 1, "save": 1, "save as": 1, "save a copy": 1,
    "place": 1, "export": 1, "print": 1, "print booklet": 1, "document setup": 1,
    // Edit (undo/redo handled separately because their names change)
    "cut": 1, "copy": 1, "paste": 1, "paste in place": 1, "paste into": 1,
    "find/change": 1, "check spelling": 1, "preferences": 1,
    // Type
    "create outlines": 1, "fill with placeholder text": 1, "find font": 1,
    // Object
    "group": 1, "ungroup": 1, "lock": 1, "unlock all on spread": 1,
    "bring to front": 1, "bring forward": 1, "send backward": 1, "send to back": 1,
    "fit content to frame": 1, "fit frame to content": 1, "fit content proportionally": 1,
    "fill frame proportionally": 1, "center content": 1, "corner options": 1,
    "clipping path": 1, "convert shape": 1,
    // Layout
    "margins and columns": 1, "numbering & section options": 1, "create guides": 1,
    "insert pages": 1, "delete pages": 1, "add page": 1,
    // Production
    "update link": 1, "relink": 1, "edit original": 1, "update all links": 1
};

// ====================================================================================
//  Small helpers
// ====================================================================================
function pad2(n) { return (n < 10 ? "0" : "") + n; }

function nowStamp() {
    var d = new Date();
    return d.getFullYear() + "-" + pad2(d.getMonth() + 1) + "-" + pad2(d.getDate()) +
        "T" + pad2(d.getHours()) + ":" + pad2(d.getMinutes()) + ":" + pad2(d.getSeconds());
}
function dayStamp() {
    var d = new Date();
    return d.getFullYear() + "-" + pad2(d.getMonth() + 1) + "-" + pad2(d.getDate());
}
function isoUtc() {
    var d = new Date();
    return d.getUTCFullYear() + "-" + pad2(d.getUTCMonth() + 1) + "-" + pad2(d.getUTCDate()) +
        "T" + pad2(d.getUTCHours()) + ":" + pad2(d.getUTCMinutes()) + ":" + pad2(d.getUTCSeconds()) + "Z";
}

// This PC's name, cleaned for a file name (so the backup matches MT Log's per-PC filing).
function pcName() {
    var n = "";
    try { n = $.getenv("COMPUTERNAME") || ""; } catch (e) {}
    if (!n) { try { n = $.getenv("HOSTNAME") || ""; } catch (e2) {} }
    if (!n) n = "PC";
    return String(n).replace(/[^A-Za-z0-9_\-]+/g, "_");
}

// Clean a document/window name: drop the trailing " @ 125%" zoom that windows add.
function cleanDocName(name) {
    if (!name) return "";
    return String(name).replace(/\s*@\s*\d+%\s*$/, "");
}
// Does this look like a real InDesign document (not "Adobe InDesign" etc.)?
function looksLikeDoc(name) {
    return /\.(indd|indt)$/i.test(cleanDocName(name));
}

// Normalise a menu/command name for matching: lower-case, strip "$ID/", trailing dots.
function normCmd(name) {
    return String(name).replace(/^\$ID\//, "").toLowerCase()
        .replace(/…/g, "").replace(/\.+$/, "").replace(/\s+/g, " ")
        .replace(/^\s+|\s+$/g, "");
}

// Tiny JSON writer for the simple objects we build.
function jsonEscape(s) {
    s = String(s); var out = "", i, c;
    for (i = 0; i < s.length; i++) {
        c = s.charAt(i);
        if (c === '"') out += '\\"';
        else if (c === '\\') out += '\\\\';
        else if (c === '\n') out += '\\n';
        else if (c === '\r') out += '\\r';
        else if (c === '\t') out += '\\t';
        else if (c.charCodeAt(0) < 32) out += '\\u' + ('0000' + c.charCodeAt(0).toString(16)).slice(-4);
        else out += c;
    }
    return out;
}
function jsonValue(v) {
    if (v === null || v === undefined) return "null";
    var t = typeof v;
    if (t === "number") return isFinite(v) ? String(v) : "null";
    if (t === "boolean") return v ? "true" : "false";
    if (t === "object") return jsonObject(v);
    return '"' + jsonEscape(v) + '"';
}
function jsonObject(o) {
    var parts = [], k;
    for (k in o) if (o.hasOwnProperty(k) && o[k] !== undefined) parts.push('"' + jsonEscape(k) + '":' + jsonValue(o[k]));
    return "{" + parts.join(",") + "}";
}

// ====================================================================================
//  The shared secret — read automatically from MT Log's own file (api-secret.txt)
//  so there is nothing to paste and a MT Log reinstall can't break it.
// ====================================================================================
var _secretCache = null;      // resolved secret string ("" = none found)
var _secretCheckedMs = 0;     // last time we looked, so we can re-read if it rotates

function mtLogDataFolder() {
    // MT Log keeps its data (incl. api-secret.txt) in %LocalAppData%\MT Log\data.
    try { return new Folder(Folder.userData.parent.fsName + "/Local/MT Log/data"); }
    catch (e) { return null; }
}

function resolveSecret() {
    // A secret deliberately set in CONFIG always wins.
    if (CONFIG.SHARED_SECRET && CONFIG.SHARED_SECRET.length &&
        CONFIG.SHARED_SECRET !== "PUT-THE-SHARED-SECRET-HERE") return CONFIG.SHARED_SECRET;
    // Otherwise read MT Log's api-secret.txt. Re-check at most every 60s (cheap, and picks
    // up a new secret after a reinstall without needing InDesign restarted).
    var now = new Date().getTime();
    if (_secretCache !== null && (now - _secretCheckedMs) < 60000) return _secretCache;
    _secretCheckedMs = now;
    _secretCache = "";
    try {
        var dir = mtLogDataFolder();
        if (dir) {
            var f = new File(dir.fsName + "/api-secret.txt");
            if (f.exists && f.open("r")) {
                var s = f.read(); f.close();
                if (s) _secretCache = String(s).replace(/^\s+|\s+$/g, "");
            }
        }
    } catch (e) { _secretCache = ""; }
    return _secretCache;
}

// ====================================================================================
//  Where the daily backup file lives
// ====================================================================================
function outputFolder() {
    var f;
    if (CONFIG.OUTPUT_FOLDER && CONFIG.OUTPUT_FOLDER.length) {
        f = new Folder(CONFIG.OUTPUT_FOLDER);
    } else {
        try { f = new Folder(Folder.userData.parent.fsName + "/Local/MT Log/indesign"); }
        catch (e) { f = new Folder(Folder.myDocuments.fsName + "/MT Log/indesign"); }
    }
    if (!f.exists) {
        try { f.create(); } catch (e2) { f = new Folder(Folder.myDocuments.fsName + "/MT Log/indesign"); if (!f.exists) f.create(); }
    }
    return f;
}
// File name you asked for: mpp-indesign-<PC>-<date>.jsonl
function dayFile() {
    return new File(outputFolder().fsName + "/mpp-indesign-" + pcName() + "-" + dayStamp() + ".jsonl");
}

function writeLine(line) {
    if (!CONFIG.LOG_TO_FILE) return;
    try {
        var file = dayFile();
        file.encoding = "UTF-8"; file.lineFeed = "Unix";
        file.open("a"); file.write(line + "\n"); file.close();
    } catch (e) {}
}

// Delete backup files older than KEEP_BACKUP_DAYS (keeps the folder from growing forever).
function cleanupOldBackups() {
    try {
        var keepMs = CONFIG.KEEP_BACKUP_DAYS * 24 * 60 * 60 * 1000;
        var now = new Date().getTime();
        var files = outputFolder().getFiles("mpp-indesign-*.jsonl");
        for (var i = 0; i < files.length; i++) {
            try {
                if (files[i] instanceof File && files[i].modified && (now - files[i].modified.getTime()) > keepMs) files[i].remove();
            } catch (e1) {}
        }
    } catch (e) {}
}

// ====================================================================================
//  SHA-256 + HMAC in pure ExtendScript (only used when SEND_TO_MT_LOG is true)
// ====================================================================================
function utf8(str) {
    var out = "", i, c;
    for (i = 0; i < str.length; i++) {
        c = str.charCodeAt(i);
        if (c < 0x80) out += String.fromCharCode(c);
        else if (c < 0x800) out += String.fromCharCode(0xC0 | (c >> 6), 0x80 | (c & 0x3F));
        else out += String.fromCharCode(0xE0 | (c >> 12), 0x80 | ((c >> 6) & 0x3F), 0x80 | (c & 0x3F));
    }
    return out;
}
function wordToBytes(w) { return String.fromCharCode((w >>> 24) & 0xFF, (w >>> 16) & 0xFF, (w >>> 8) & 0xFF, w & 0xFF); }
var SHA256_K = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
];
function sha256bin(message) {
    function rotr(n, x) { return (x >>> n) | (x << (32 - n)); }
    var H = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19];
    var l = message.length;
    var msg = message + String.fromCharCode(0x80);
    while (msg.length % 64 !== 56) msg += String.fromCharCode(0);
    var bits = l * 8;
    msg += wordToBytes(Math.floor(bits / 0x100000000)) + wordToBytes(bits >>> 0);
    var w = [], i, j;
    for (j = 0; j < msg.length; j += 64) {
        for (i = 0; i < 16; i++) {
            w[i] = (msg.charCodeAt(j + i * 4) << 24) | (msg.charCodeAt(j + i * 4 + 1) << 16) |
                (msg.charCodeAt(j + i * 4 + 2) << 8) | (msg.charCodeAt(j + i * 4 + 3));
        }
        for (i = 16; i < 64; i++) {
            var s0 = rotr(7, w[i - 15]) ^ rotr(18, w[i - 15]) ^ (w[i - 15] >>> 3);
            var s1 = rotr(17, w[i - 2]) ^ rotr(19, w[i - 2]) ^ (w[i - 2] >>> 10);
            w[i] = (w[i - 16] + s0 + w[i - 7] + s1) >>> 0;
        }
        var a = H[0], b = H[1], c = H[2], d = H[3], e = H[4], f = H[5], g = H[6], h = H[7];
        for (i = 0; i < 64; i++) {
            var S1 = rotr(6, e) ^ rotr(11, e) ^ rotr(25, e);
            var ch = (e & f) ^ (~e & g);
            var t1 = (h + S1 + ch + SHA256_K[i] + w[i]) >>> 0;
            var S0 = rotr(2, a) ^ rotr(13, a) ^ rotr(22, a);
            var maj = (a & b) ^ (a & c) ^ (b & c);
            var t2 = (S0 + maj) >>> 0;
            h = g; g = f; f = e; e = (d + t1) >>> 0; d = c; c = b; b = a; a = (t1 + t2) >>> 0;
        }
        H[0] = (H[0] + a) >>> 0; H[1] = (H[1] + b) >>> 0; H[2] = (H[2] + c) >>> 0; H[3] = (H[3] + d) >>> 0;
        H[4] = (H[4] + e) >>> 0; H[5] = (H[5] + f) >>> 0; H[6] = (H[6] + g) >>> 0; H[7] = (H[7] + h) >>> 0;
    }
    var out = "";
    for (i = 0; i < 8; i++) out += wordToBytes(H[i]);
    return out;
}
function hmacSha256(keyBin, msgBin) {
    var block = 64, i;
    if (keyBin.length > block) keyBin = sha256bin(keyBin);
    while (keyBin.length < block) keyBin += String.fromCharCode(0);
    var oPad = "", iPad = "";
    for (i = 0; i < block; i++) {
        var k = keyBin.charCodeAt(i);
        oPad += String.fromCharCode(k ^ 0x5c);
        iPad += String.fromCharCode(k ^ 0x36);
    }
    return sha256bin(oPad + sha256bin(iPad + msgBin));
}
function toHex(bin) { var out = "", i; for (i = 0; i < bin.length; i++) out += ("0" + bin.charCodeAt(i).toString(16)).slice(-2); return out; }

// ====================================================================================
//  Hand an event to MT Log's local API (signed, loopback only)
// ====================================================================================
function sendToMtLog(eventType, data, description) {
    if (!CONFIG.SEND_TO_MT_LOG) return;
    try {
        var secret = resolveSecret();
        if (!secret) return; // no secret found yet — the local backup file still records it
        var payload = {
            event_type: eventType, script_name: "MPP InDesign Logger",
            description: description || "", timestamp: isoUtc(), data: data
        };
        var body = jsonObject(payload);
        var bodyBin = utf8(body);
        var ts = String(Math.floor(new Date().getTime() / 1000));
        var sig = toHex(hmacSha256(utf8(secret), utf8(ts + "." + body)));
        var conn = new Socket();
        if (conn.open("127.0.0.1:" + CONFIG.PORT, "BINARY")) {
            var req = "POST /v1/events HTTP/1.0\r\n" +
                "Host: 127.0.0.1\r\n" + "Content-Type: application/json\r\n" +
                "X-MPP-Timestamp: " + ts + "\r\n" + "X-MPP-Signature: " + sig + "\r\n" +
                "Content-Length: " + bodyBin.length + "\r\n" + "Connection: close\r\n\r\n" + bodyBin;
            conn.timeout = 3;
            conn.write(req); conn.read(65535); conn.close();
        }
    } catch (e) {}
}

// One log entry = one backup line + optional live send.
function record(eventType, data, description) {
    data = data || {};
    writeLine(jsonObject({ ts: nowStamp(), event: eventType, doc: data.doc || "", details: data }));
    sendToMtLog(eventType, data, description);
}

function activeDocName() {
    try { return app.documents.length > 0 ? cleanDocName(app.activeDocument.name) : ""; } catch (e) { return ""; }
}

// Is this selection a bit of text (so the script label lives on its parent frame)?
function isTextish(kind) {
    return kind === "Text" || kind === "InsertionPoint" || kind === "Word" || kind === "Character" ||
        kind === "TextStyleRange" || kind === "Paragraph" || kind === "Line";
}

// Describe the current selection in a short, readable way.
function describeSelection() {
    var info = { doc: activeDocName() };
    try {
        var sel = app.selection;
        if (!sel || sel.length === 0) { info.kind = "none"; return info; }
        var item = sel[0];
        info.count = sel.length;
        try { info.kind = item.constructor.name; } catch (e1) { info.kind = "object"; }

        if (isTextish(info.kind)) {
            // Script label + page live on the TEXT BOX, not on the cursor — climb up to it.
            try {
                var frames = item.parentTextFrames;
                if (frames && frames.length) {
                    try { if (frames[0].label && frames[0].label.length) info.script_label = frames[0].label; } catch (eL) {}
                    try { if (frames[0].parentPage && frames[0].parentPage.name) info.page = frames[0].parentPage.name; } catch (eP) {}
                }
            } catch (eF) {}
            try { info.chars = item.characters.length; } catch (eC) {}
            try { info.para_style = item.appliedParagraphStyle.name; } catch (e6) {}
            try { info.char_style = item.appliedCharacterStyle.name; } catch (e7) {}
            try { if (item.fillColor && item.fillColor.name) info.fill = item.fillColor.name; } catch (e4) {}
        } else {
            try { if (item.label && item.label.length) info.script_label = item.label; } catch (e2) {}
            try { if (item.parentPage && item.parentPage.name) info.page = item.parentPage.name; } catch (e3) {}
            try { if (item.fillColor && item.fillColor.name) info.fill = item.fillColor.name; } catch (e4b) {}
            try { if (item.strokeColor && item.strokeColor.name) info.stroke = item.strokeColor.name; } catch (e5) {}
        }
    } catch (e) { info.kind = "unknown"; }
    return info;
}
function selectionSig(info) {
    return [info.doc, info.kind, info.script_label, info.page, info.fill, info.stroke, info.count, info.chars].join("|");
}

// --- Swatch watching: spot a colour being edited and say what it became -------------
// A readable colour string for a swatch, e.g. "CMYK(0,100,100,0)" or "RGB(255,0,0)".
function colorSig(sw) {
    try {
        var v = sw.colorValue;                       // throws for gradients / mixed ink / [None]
        if (!v || v.length === 0) return "";
        var sp = "";
        try { sp = String(sw.space); } catch (e) {}
        if (!sp || /^\d+$/.test(sp)) sp = (v.length === 4 ? "CMYK" : v.length === 3 ? "RGB" : "");
        var parts = [];
        for (var i = 0; i < v.length; i++) parts.push(Math.round(v[i] * 10) / 10);
        return sp + "(" + parts.join(",") + ")";
    } catch (e) { return ""; }
}
// Snapshot the active document's swatches as { id: {name, sig} } (skips gradients/none).
function snapshotSwatches(doc) {
    var map = {};
    try {
        var sws = doc.swatches, i, sw, sig;
        for (i = 0; i < sws.length; i++) {
            sw = sws[i];
            try {
                sig = colorSig(sw);
                if (sig === "") continue;
                map[sw.id] = { name: sw.name, sig: sig };
            } catch (e) {}
        }
    } catch (e2) {}
    return map;
}
// Compare old vs new swatch snapshots and log any add / remove / rename / recolour.
function diffSwatches(docName, oldMap, newMap) {
    var id;
    for (id in newMap) {
        if (!newMap.hasOwnProperty(id)) continue;
        if (!oldMap[id]) { record("indesign_swatch_added", { doc: docName, swatch: newMap[id].name, color: newMap[id].sig }, "Swatch added: " + newMap[id].name + " = " + newMap[id].sig); continue; }
        if (oldMap[id].name !== newMap[id].name) record("indesign_swatch_renamed", { doc: docName, from: oldMap[id].name, to: newMap[id].name }, "Swatch renamed: " + oldMap[id].name + " -> " + newMap[id].name);
        if (oldMap[id].sig !== newMap[id].sig) record("indesign_swatch_changed", { doc: docName, swatch: newMap[id].name, from: oldMap[id].sig, to: newMap[id].sig }, "Swatch recoloured: " + newMap[id].name + " " + oldMap[id].sig + " -> " + newMap[id].sig);
    }
    for (id in oldMap) {
        if (oldMap.hasOwnProperty(id) && !newMap[id]) record("indesign_swatch_removed", { doc: docName, swatch: oldMap[id].name }, "Swatch removed: " + oldMap[id].name);
    }
}

// The ruler unit label (in / mm / cm / pt / pc / px) for position & size figures.
function unitLabel() {
    try {
        var u = String(app.activeDocument.viewPreferences.horizontalMeasurementUnits).toLowerCase();
        if (u.indexOf("inch") >= 0) return "in";
        if (u.indexOf("millim") >= 0) return "mm";
        if (u.indexOf("centim") >= 0) return "cm";
        if (u.indexOf("point") >= 0) return "pt";
        if (u.indexOf("pica") >= 0) return "pc";
        if (u.indexOf("pixel") >= 0) return "px";
    } catch (e) {}
    return "units";
}

// --- Selected-object watching: spot stroke/fill/style/font/size changes --------------
// Grab the watched attributes of the single selected object (or null).
function snapshotAttrs() {
    try {
        var sel = app.selection;
        if (!sel || sel.length !== 1) return null;
        var item = sel[0], id = null, a = {};
        try { id = item.id; } catch (e0) {}
        try { if (item.fillColor && item.fillColor.name !== undefined) a.fill = item.fillColor.name; } catch (e1) {}
        try { if (item.strokeColor && item.strokeColor.name !== undefined) a.stroke = item.strokeColor.name; } catch (e2) {}
        try { a.stroke_weight = Math.round(item.strokeWeight * 100) / 100; } catch (e3) {}
        try { if (item.strokeStyle && item.strokeStyle.name) a.stroke_style = item.strokeStyle.name; } catch (e4) {}
        try { a.opacity = Math.round(item.transparencySettings.blendingSettings.opacity * 10) / 10; } catch (e5) {}
        // Position & size, from geometricBounds [y1, x1, y2, x2] in the ruler's units.
        try {
            var gb = item.geometricBounds;
            if (gb && gb.length === 4) {
                a.x = Math.round(gb[1] * 100) / 100; a.y = Math.round(gb[0] * 100) / 100;
                a.w = Math.round((gb[3] - gb[1]) * 100) / 100; a.h = Math.round((gb[2] - gb[0]) * 100) / 100;
            }
        } catch (eg) {}
        try { a.rotation = Math.round(item.rotationAngle * 100) / 100; } catch (er) {}
        try { if (item.pointSize !== undefined) a.size = item.pointSize; } catch (e6) {}
        try { if (item.appliedFont) a.font = (item.appliedFont.name !== undefined ? item.appliedFont.name : String(item.appliedFont)); } catch (e7) {}
        try { if (item.appliedParagraphStyle) a.para_style = item.appliedParagraphStyle.name; } catch (e8) {}
        try { if (item.appliedCharacterStyle) a.char_style = item.appliedCharacterStyle.name; } catch (e9) {}
        return { id: id, attrs: a };
    } catch (e) { return null; }
}

// ====================================================================================
//  Event handlers
// ====================================================================================
function onDocOpen(ev) {
    try {
        var name = "";
        try { name = ev.target && ev.target.name ? ev.target.name : activeDocName(); } catch (e) { name = activeDocName(); }
        name = cleanDocName(name);
        if (!looksLikeDoc(name)) return;                       // skip non-document targets
        var t = new Date().getTime();
        if (name === STATE.lastOpenName && (t - STATE.lastOpenTime) < 4000) return; // de-dupe the "@125%" twin
        STATE.lastOpenName = name; STATE.lastOpenTime = t;
        record("indesign_doc_open", { doc: name }, "Opened " + name);
    } catch (e) {}
}
function onDocClose(ev) {
    try {
        var name = "";
        try { name = ev.target && ev.target.name ? ev.target.name : ""; } catch (e) {}
        name = cleanDocName(name);
        if (!looksLikeDoc(name)) return;                       // ignore the "Adobe InDesign" startup noise
        record("indesign_doc_close", { doc: name }, "Closed " + name);
    } catch (e) {}
}
function onDocSave(ev) {
    try {
        var name = activeDocName();
        try { if (ev.target && ev.target.name) name = cleanDocName(ev.target.name); } catch (e) {}
        STATE.lastModified = false;
        record("indesign_doc_save", { doc: name }, "Saved " + name);
    } catch (e) {}
}
function onSelectionChanged(ev) {
    try {
        var info = describeSelection();
        if (info.kind === "none" || info.kind === "unknown" || info.doc === "") return; // skip startup noise
        var sig = selectionSig(info);
        var t = new Date().getTime();
        if (sig === STATE.lastSelSig && (t - STATE.lastSelTime) < CONFIG.SELECTION_MIN_GAP_MS) return;
        STATE.lastSelSig = sig; STATE.lastSelTime = t;
        record("indesign_selection", info, "Selected " + info.kind + (info.script_label ? " [" + info.script_label + "]" : ""));
    } catch (e) {}
}
function onCommand(ev) {
    try {
        var name = ev.target && ev.target.name ? ev.target.name : "";
        if (!name) return;
        record("indesign_command", { doc: activeDocName(), command: cleanDocName(name) }, "Command: " + name);
    } catch (e) {}
}
function onScriptRun(ev) {
    try {
        var name = ev.target && ev.target.name ? ev.target.name : "";
        if (!name) return;
        record("indesign_script_run", { doc: activeDocName(), script: name }, "Ran script: " + name);
    } catch (e) {}
}

// Idle poll: tool changes, switching documents, and the first unsaved edit.
function onIdle(ev) {
    try {
        try {
            var tool = String(app.toolBoxTools.currentTool);
            if (tool !== STATE.lastTool) { STATE.lastTool = tool; record("indesign_tool", { doc: activeDocName(), tool: tool }, "Tool: " + tool); }
        } catch (e1) {}
        try {
            var cur = activeDocName();
            if (cur !== STATE.lastDoc) { STATE.lastDoc = cur; if (cur !== "") record("indesign_doc_active", { doc: cur }, "Working in " + cur); }
        } catch (e2) {}
        try {
            if (app.documents.length > 0) {
                var mod = app.activeDocument.modified;
                if (mod && !STATE.lastModified) record("indesign_edit", { doc: activeDocName() }, "Edited (unsaved changes)");
                STATE.lastModified = mod;
            }
        } catch (e3) {}

        // Swatch edits (checked a little less often — swatch lists can be long).
        if (CONFIG.WATCH_SWATCHES && app.documents.length > 0) {
            try {
                STATE.swatchTick = (STATE.swatchTick + 1) % 3;
                if (STATE.swatchTick === 0) {
                    var doc = app.activeDocument, dn = cleanDocName(doc.name);
                    var fresh = snapshotSwatches(doc);
                    if (STATE.swatchSnap && STATE.swatchSnapDoc === dn) diffSwatches(dn, STATE.swatchSnap, fresh);
                    STATE.swatchSnap = fresh; STATE.swatchSnapDoc = dn;
                }
            } catch (eS) {}
        }

        // Stroke / fill / style / font / size changes on the selected object.
        if (CONFIG.WATCH_ATTRS) {
            try {
                var snap = snapshotAttrs();
                if (snap && snap.id !== null) {
                    var prev = STATE.attrSnap;
                    if (prev && prev.id === snap.id) {
                        var p = prev.attrs, n = snap.attrs, dn = activeDocName(), unit = unitLabel();
                        // Moved: report before/after x,y and how far (dx,dy).
                        if (p.x !== undefined && n.x !== undefined && (p.x !== n.x || p.y !== n.y)) {
                            var dx = Math.round((n.x - p.x) * 100) / 100, dy = Math.round((n.y - p.y) * 100) / 100;
                            record("indesign_moved", { doc: dn, from: { x: p.x, y: p.y }, to: { x: n.x, y: n.y }, dx: dx, dy: dy, unit: unit },
                                "Moved " + dx + "," + dy + " " + unit + " -> (" + n.x + "," + n.y + ")");
                        }
                        // Resized: report before/after width,height.
                        if (p.w !== undefined && n.w !== undefined && (p.w !== n.w || p.h !== n.h)) {
                            record("indesign_resized", { doc: dn, from: { w: p.w, h: p.h }, to: { w: n.w, h: n.h }, unit: unit },
                                "Resized " + p.w + "x" + p.h + " -> " + n.w + "x" + n.h + " " + unit);
                        }
                        // Rotated.
                        if (p.rotation !== undefined && n.rotation !== undefined && p.rotation !== n.rotation) {
                            record("indesign_rotated", { doc: dn, from: p.rotation, to: n.rotation },
                                "Rotated " + p.rotation + " -> " + n.rotation + " deg");
                        }
                        // Everything else (stroke/fill/style/font/size/opacity) stays generic.
                        for (var k in n) {
                            if (!n.hasOwnProperty(k)) continue;
                            if (k === "x" || k === "y" || k === "w" || k === "h" || k === "rotation") continue;
                            if (p[k] !== undefined && String(p[k]) !== String(n[k])) {
                                record("indesign_attr_changed",
                                    { doc: dn, attr: k, from: p[k], to: n[k] },
                                    "Changed " + k + ": " + p[k] + " -> " + n[k]);
                            }
                        }
                    }
                    STATE.attrSnap = snap;
                } else { STATE.attrSnap = null; }
            } catch (eA) {}
        }
    } catch (e) {}
    try { ev.target.sleep = CONFIG.POLL_MS; } catch (e4) {}
}

// ====================================================================================
//  Start / restart cleanly
// ====================================================================================
var STATE = {
    lastSelSig: "", lastSelTime: 0, lastTool: "", lastDoc: "", lastModified: false,
    lastOpenName: "", lastOpenTime: 0, listeners: [], idleTask: null,
    swatchSnap: null, swatchSnapDoc: "", swatchTick: 0, attrSnap: null
};

function stopExisting() {
    try {
        var prev = $.global.__mppIdLogger;
        if (prev) {
            if (prev.idleTask) { try { prev.idleTask.remove(); } catch (e) {} }
            if (prev.listeners) for (var i = 0; i < prev.listeners.length; i++) { try { prev.listeners[i].remove(); } catch (e2) {} }
        }
    } catch (e3) {}
}

// Attach "afterInvoke" listeners only to the menu commands we want (resolved by name once).
function wireCommands() {
    if (!CONFIG.LOG_COMMANDS) return;
    try {
        var actions = app.menuActions, i, a, n;
        for (i = 0; i < actions.length; i++) {
            try {
                a = actions[i]; n = normCmd(a.name);
                var want = WANTED_COMMANDS[n] || n.indexOf("undo") === 0 || n.indexOf("redo") === 0;
                if (want) STATE.listeners.push(a.addEventListener("afterInvoke", onCommand, false));
            } catch (eA) {}
        }
    } catch (e) {}
    // Menu-scripts (scripts exposed on a menu). Panel double-clicks still can't be caught.
    try {
        var sma = app.scriptMenuActions, j;
        for (j = 0; j < sma.length; j++) { try { STATE.listeners.push(sma[j].addEventListener("afterInvoke", onScriptRun, false)); } catch (eS) {} }
    } catch (e2) {}
}

function start() {
    stopExisting();
    if (CONFIG.LOG_TO_FILE) cleanupOldBackups();

    var add = function (type, fn) { try { STATE.listeners.push(app.addEventListener(type, fn, false)); } catch (e) {} };
    add("afterOpen", onDocOpen);
    add("afterClose", onDocClose);
    add("afterSave", onDocSave);
    add("afterSaveAs", onDocSave);
    add("afterSaveACopy", onDocSave);
    add("afterSelectionChanged", onSelectionChanged);
    wireCommands();

    try {
        STATE.idleTask = app.idleTasks.add({ name: "mppIndesignIdle", sleep: CONFIG.POLL_MS });
        STATE.idleTask.addEventListener("onIdle", onIdle, false);
    } catch (e) {}

    $.global.__mppIdLogger = STATE;

    record("indesign_logger_started",
        { doc: activeDocName(), version: "4", mt_log: CONFIG.SEND_TO_MT_LOG, file_logging: CONFIG.LOG_TO_FILE,
          commands: CONFIG.LOG_COMMANDS, swatches: CONFIG.WATCH_SWATCHES, attrs: CONFIG.WATCH_ATTRS },
        "InDesign logger started");

    try { $.writeln("MT Log InDesign logger v4 running. Sending to MT Log: " + CONFIG.SEND_TO_MT_LOG); } catch (e) {}
}

start();
