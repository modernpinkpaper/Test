#targetengine "mppIndesignLogger"
/*
 * MT Log — InDesign activity logger (ExtendScript / .jsx)
 * -------------------------------------------------------
 * Runs INSIDE Adobe InDesign and quietly writes down what you do while you design:
 * which document you opened, which object or text box you selected (and its script
 * label, if it has one), which tool you picked, which swatch/ink colour you applied,
 * and when you edited or saved. One plain-text file per day.
 *
 * There are two ways to run it (see tools/indesign/README.md for pictures of the steps):
 *   1. Double-click it once from InDesign's Scripts panel (Window > Utilities > Scripts).
 *      It keeps logging for the rest of that InDesign session — you do NOT keep
 *      double-clicking. Running it again just restarts it cleanly.
 *   2. Drop it in InDesign's "startup scripts" folder so it starts on its own every
 *      time InDesign opens (no clicking at all). The README shows where that folder is.
 *
 * By default it ONLY writes a local file, so you can test it right now without MT Log
 * running and without any secret. When you are happy, flip SEND_TO_MT_LOG to true and
 * paste in the shared secret, and every InDesign action is also handed to MT Log through
 * its local API (so it lands in the same daily log as everything else on the PC).
 *
 * Safe by design: every handler is wrapped in try/catch, so a logging hiccup can never
 * interrupt your InDesign work or pop up an error while you design.
 */

// ====================================================================================
//  SETTINGS — the only part most people need to touch
// ====================================================================================
var CONFIG = {
    // Write a local .jsonl file (one line per action). Great for testing on its own.
    LOG_TO_FILE: true,

    // Also hand each action to MT Log via its local API (127.0.0.1). Turn this on once
    // file logging works and MT Log is installed on this PC.
    SEND_TO_MT_LOG: false,

    // Must match "local_api.shared_secret" in MT Log's config.json. Only needed when
    // SEND_TO_MT_LOG is true. Ask the admin for the value.
    SHARED_SECRET: "PUT-THE-SHARED-SECRET-HERE",
    PORT: 47821,

    // How often (ms) to check the current tool / active document / unsaved-changes flag.
    POLL_MS: 2000,

    // Don't log the same selection more than once per this many ms (stops click spam).
    SELECTION_MIN_GAP_MS: 800,

    // Leave empty to use the default folder next to MT Log's own data
    // (%LOCALAPPDATA%\MT Log\indesign). Or set a full path like "C:/MT Log/indesign".
    OUTPUT_FOLDER: ""
};

// ====================================================================================
//  Small helpers
// ====================================================================================
function pad2(n) { return (n < 10 ? "0" : "") + n; }

// Local time stamp, e.g. 2026-10-01T14:03:22 (human friendly, matches the day file).
function nowStamp() {
    var d = new Date();
    return d.getFullYear() + "-" + pad2(d.getMonth() + 1) + "-" + pad2(d.getDate()) +
        "T" + pad2(d.getHours()) + ":" + pad2(d.getMinutes()) + ":" + pad2(d.getSeconds());
}

// Date part only, for the file name.
function dayStamp() {
    var d = new Date();
    return d.getFullYear() + "-" + pad2(d.getMonth() + 1) + "-" + pad2(d.getDate());
}

// UTC ISO stamp (what MT Log's local API expects in the event's "timestamp").
function isoUtc() {
    var d = new Date();
    return d.getUTCFullYear() + "-" + pad2(d.getUTCMonth() + 1) + "-" + pad2(d.getUTCDate()) +
        "T" + pad2(d.getUTCHours()) + ":" + pad2(d.getUTCMinutes()) + ":" + pad2(d.getUTCSeconds()) + "Z";
}

// Tiny JSON writer for the simple objects we build (strings, numbers, booleans, nested).
function jsonEscape(s) {
    s = String(s);
    var out = "", i, c;
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
    for (k in o) {
        if (o.hasOwnProperty(k) && o[k] !== undefined) parts.push('"' + jsonEscape(k) + '":' + jsonValue(o[k]));
    }
    return "{" + parts.join(",") + "}";
}

// ====================================================================================
//  Where the daily file lives
// ====================================================================================
function outputFolder() {
    var f;
    if (CONFIG.OUTPUT_FOLDER && CONFIG.OUTPUT_FOLDER.length) {
        f = new Folder(CONFIG.OUTPUT_FOLDER);
    } else {
        // Folder.userData is ...\AppData\Roaming; its parent is ...\AppData, so Local is next to it.
        try {
            f = new Folder(Folder.userData.parent.fsName + "/Local/MT Log/indesign");
        } catch (e) {
            f = new Folder(Folder.myDocuments.fsName + "/MT Log/indesign");
        }
    }
    if (!f.exists) {
        try { f.create(); } catch (e2) { f = new Folder(Folder.myDocuments.fsName + "/MT Log/indesign"); if (!f.exists) f.create(); }
    }
    return f;
}

function writeLine(line) {
    if (!CONFIG.LOG_TO_FILE) return;
    try {
        var file = new File(outputFolder().fsName + "/mpp-indesign-" + dayStamp() + ".jsonl");
        file.encoding = "UTF-8";
        file.lineFeed = "Unix";
        file.open("a"); // append; keeps the whole day in one file
        file.write(line + "\n");
        file.close();
    } catch (e) { /* never interrupt design work over a log write */ }
}

// ====================================================================================
//  SHA-256 + HMAC in pure ExtendScript (only used when SEND_TO_MT_LOG is true)
//  Works on "binary strings" where each character is one byte (0..255).
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
function wordToBytes(w) {
    return String.fromCharCode((w >>> 24) & 0xFF, (w >>> 16) & 0xFF, (w >>> 8) & 0xFF, w & 0xFF);
}
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
function toHex(bin) {
    var out = "", i;
    for (i = 0; i < bin.length; i++) out += ("0" + bin.charCodeAt(i).toString(16)).slice(-2);
    return out;
}

// ====================================================================================
//  Hand an event to MT Log's local API (signed, loopback only)
// ====================================================================================
function sendToMtLog(eventType, data, description) {
    if (!CONFIG.SEND_TO_MT_LOG) return;
    try {
        var payload = {
            event_type: eventType,          // e.g. indesign_selection (lowercase + _)
            script_name: "MPP InDesign Logger",
            description: description || "",
            timestamp: isoUtc(),
            data: data                       // all InDesign specifics live here
        };
        var body = jsonObject(payload);
        var bodyBin = utf8(body);
        var ts = String(Math.floor(new Date().getTime() / 1000));
        var sig = toHex(hmacSha256(utf8(CONFIG.SHARED_SECRET), utf8(ts + "." + body)));

        var conn = new Socket();
        if (conn.open("127.0.0.1:" + CONFIG.PORT, "BINARY")) {
            var req = "POST /v1/events HTTP/1.0\r\n" +
                "Host: 127.0.0.1\r\n" +
                "Content-Type: application/json\r\n" +
                "X-MPP-Timestamp: " + ts + "\r\n" +
                "X-MPP-Signature: " + sig + "\r\n" +
                "Content-Length: " + bodyBin.length + "\r\n" +
                "Connection: close\r\n\r\n" + bodyBin;
            conn.timeout = 3; // seconds; if MT Log is down we move on fast
            conn.write(req);
            conn.read(65535);
            conn.close();
        }
    } catch (e) { /* MT Log not running or no secret: never break InDesign */ }
}

// ====================================================================================
//  Turn an InDesign action into one log entry (file line + optional MT Log event)
// ====================================================================================
function record(eventType, data, description) {
    data = data || {};
    var line = jsonObject({
        ts: nowStamp(),
        event: eventType,
        doc: data.doc || "",
        details: data
    });
    writeLine(line);
    sendToMtLog(eventType, data, description);
}

// Safely read the active document name (or "" if none).
function activeDocName() {
    try { return app.documents.length > 0 ? app.activeDocument.name : ""; } catch (e) { return ""; }
}

// Describe the current selection in a short, readable way.
function describeSelection() {
    var info = { doc: activeDocName() };
    try {
        var sel = app.selection;
        if (!sel || sel.length === 0) { info.kind = "none"; return info; }
        var item = sel[0];
        info.count = sel.length;
        // Constructor name gives the object type: TextFrame, Rectangle, Oval, Graphic, Text, etc.
        try { info.kind = item.constructor.name; } catch (e1) { info.kind = "object"; }
        // Script label: some text boxes are tagged, some are not — very useful to know which.
        try { if (item.label && item.label.length) info.script_label = item.label; } catch (e2) {}
        // Which page it sits on.
        try { if (item.parentPage && item.parentPage.name) info.page = item.parentPage.name; } catch (e3) {}
        // Applied fill / stroke swatch (the "ink colour" question).
        try { if (item.fillColor && item.fillColor.name) info.fill = item.fillColor.name; } catch (e4) {}
        try { if (item.strokeColor && item.strokeColor.name) info.stroke = item.strokeColor.name; } catch (e5) {}
        // If text is selected, note how much and the applied styles.
        try {
            if (info.kind === "Text" || info.kind === "InsertionPoint" || info.kind === "Word" ||
                info.kind === "TextStyleRange" || info.kind === "Paragraph") {
                info.chars = item.characters.length;
                try { info.para_style = item.appliedParagraphStyle.name; } catch (e6) {}
                try { info.char_style = item.appliedCharacterStyle.name; } catch (e7) {}
            }
        } catch (e8) {}
    } catch (e) { info.kind = "unknown"; }
    return info;
}

// A short signature so we don't log the exact same selection over and over.
function selectionSig(info) {
    return [info.doc, info.kind, info.script_label, info.page, info.fill, info.stroke, info.count].join("|");
}

// ====================================================================================
//  Event handlers
// ====================================================================================
function onDocOpen(ev) {
    try {
        var name = "";
        try { name = ev.target && ev.target.name ? ev.target.name : activeDocName(); } catch (e) { name = activeDocName(); }
        record("indesign_doc_open", { doc: name }, "Opened " + name);
    } catch (e) {}
}
function onDocClose(ev) {
    try {
        var name = "";
        try { name = ev.target && ev.target.name ? ev.target.name : ""; } catch (e) {}
        record("indesign_doc_close", { doc: name }, "Closed " + name);
    } catch (e) {}
}
function onDocSave(ev) {
    try {
        var name = activeDocName();
        try { if (ev.target && ev.target.name) name = ev.target.name; } catch (e) {}
        STATE.lastModified = false; // a save resets the "has unsaved edits" tracking
        record("indesign_doc_save", { doc: name }, "Saved " + name);
    } catch (e) {}
}
function onSelectionChanged(ev) {
    try {
        var info = describeSelection();
        if (info.kind === "none") return;
        var sig = selectionSig(info);
        var t = new Date().getTime();
        if (sig === STATE.lastSelSig && (t - STATE.lastSelTime) < CONFIG.SELECTION_MIN_GAP_MS) return;
        STATE.lastSelSig = sig;
        STATE.lastSelTime = t;
        record("indesign_selection", info, "Selected " + info.kind + (info.script_label ? " [" + info.script_label + "]" : ""));
    } catch (e) {}
}

// Idle poll: catches things that have no event — the chosen tool, switching between open
// documents, and the moment a document first has unsaved changes.
function onIdle(ev) {
    try {
        // Current tool (pen, type, selection, eyedropper, etc.)
        try {
            var tool = String(app.toolBoxTools.currentTool);
            if (tool !== STATE.lastTool) {
                STATE.lastTool = tool;
                record("indesign_tool", { doc: activeDocName(), tool: tool }, "Tool: " + tool);
            }
        } catch (e1) {}

        // Switched to a different open document.
        try {
            var cur = activeDocName();
            if (cur !== STATE.lastDoc) {
                STATE.lastDoc = cur;
                if (cur !== "") record("indesign_doc_active", { doc: cur }, "Working in " + cur);
            }
        } catch (e2) {}

        // First unsaved change since the last save = the user edited the document.
        try {
            if (app.documents.length > 0) {
                var mod = app.activeDocument.modified;
                if (mod && !STATE.lastModified) record("indesign_edit", { doc: activeDocName() }, "Edited (unsaved changes)");
                STATE.lastModified = mod;
            }
        } catch (e3) {}
    } catch (e) {}
    // Keep the idle task alive on the same schedule.
    try { ev.target.sleep = CONFIG.POLL_MS; } catch (e4) {}
}

// ====================================================================================
//  Start / restart cleanly (running the script again removes the old listeners first)
// ====================================================================================
var STATE = {
    lastSelSig: "", lastSelTime: 0, lastTool: "", lastDoc: "", lastModified: false,
    listeners: [], idleTask: null
};

function stopExisting() {
    // If a previous run left state in this persistent engine, tear it down.
    try {
        if ($.global.__mppIdLogger && $.global.__mppIdLogger.idleTask) {
            try { $.global.__mppIdLogger.idleTask.remove(); } catch (e) {}
        }
        if ($.global.__mppIdLogger && $.global.__mppIdLogger.listeners) {
            var ls = $.global.__mppIdLogger.listeners, i;
            for (i = 0; i < ls.length; i++) { try { ls[i].remove(); } catch (e2) {} }
        }
    } catch (e3) {}
}

function start() {
    stopExisting();

    var add = function (type, fn) {
        try { STATE.listeners.push(app.addEventListener(type, fn, false)); } catch (e) {}
    };
    add("afterOpen", onDocOpen);
    add("afterClose", onDocClose);
    add("afterSave", onDocSave);
    add("afterSaveAs", onDocSave);
    add("afterSaveACopy", onDocSave);
    add("afterSelectionChanged", onSelectionChanged);

    // Idle task for the periodic poll.
    try {
        STATE.idleTask = app.idleTasks.add({ name: "mppIndesignIdle", sleep: CONFIG.POLL_MS });
        STATE.idleTask.addEventListener("onIdle", onIdle, false);
    } catch (e) {}

    // Remember what we created so a re-run can clean it up.
    $.global.__mppIdLogger = STATE;

    record("indesign_logger_started",
        { doc: activeDocName(), file_logging: CONFIG.LOG_TO_FILE, mt_log: CONFIG.SEND_TO_MT_LOG },
        "InDesign logger started");

    // One quiet confirmation so you know it's running (only on manual double-click).
    try {
        $.writeln("MT Log InDesign logger is running. Writing to: " + outputFolder().fsName);
    } catch (e) {}
}

start();
