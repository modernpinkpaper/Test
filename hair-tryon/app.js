/* Hair Color Try-On — browser UI. Uses HTData (data.js) and HTEngine (engine.js). Everything runs on this device. */
(function () {
  'use strict';
  var E = window.HTEngine, D = window.HTData;
  var MP_BASE = 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14';
  var MODEL_URL = 'https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_multiclass_256x256/float32/latest/selfie_multiclass_256x256.tflite';
  var MAX_SIDE = 1000;

  function $(id) { return document.getElementById(id); }
  var el = {};
  ['file', 'btnAuto', 'status', 'stage', 'empty', 'cvAfter', 'cvBefore', 'beforeWrap', 'cvOver', 'divider', 'knob', 'tagBefore', 'tagAfter',
    'viewChips', 'btnSave', 'btnDownload', 'chkGray', 'btnEdit', 'brushTools', 'bAdd', 'bErase', 'brushSize', 'btnDone', 'looksCard', 'looks',
    'pBody', 'pEdge', 'zone', 'level', 'btnAutoLevel', 'vBody', 'vEdge', 'vZone', 'vLevel', 'hairNote', 'line', 'lineMeta', 'shadeSearch', 'shade',
    'cLevel', 'cTone', 'btnCustom', 'dev', 'devNote', 'time', 'vTime', 'timeNote', 'explain', 'lineFacts', 'calDepth', 'calCov', 'vDepth', 'vCovCal', 'btnCalReset'
  ].forEach(function (id) { el[id] = $(id); });

  /* ---------------- state ---------------- */
  var S = {
    w: 0, h: 0, rgba: null, L: null, a: null, b: null, alpha: null, face: null, edge: null,
    gw: null, loc: null, noise: null, g: null, manualLevel: null,
    line: null, shade: null, dev: null, minutes: 20, band: 'expected',
    calib: { grayBias: 1, depthBias: 0 }, edit: false, brush: 'add', split: 0.5, looks: [], hasPhoto: false, seg: null
  };
  var segBusy = false;

  function setStatus(t) { el.status.textContent = t; }

  /* ---------------- photo ---------------- */
  el.file.addEventListener('change', function () {
    var f = el.file.files && el.file.files[0]; if (!f) return;
    loadPhoto(f);
  });

  function loadPhoto(file) {
    setStatus('Loading photo…');
    var p = (window.createImageBitmap ? createImageBitmap(file, { imageOrientation: 'from-image' }) : Promise.reject()).catch(function () {
      return new Promise(function (res, rej) {
        var im = new Image(); im.onload = function () { res(im); }; im.onerror = rej; im.src = URL.createObjectURL(file);
      });
    });
    p.then(function (img) {
      var iw = img.width, ih = img.height, sc = Math.min(1, MAX_SIDE / Math.max(iw, ih));
      var w = Math.round(iw * sc), h = Math.round(ih * sc);
      [el.cvBefore, el.cvAfter, el.cvOver].forEach(function (c) { c.width = w; c.height = h; });
      var ctx = el.cvBefore.getContext('2d', { willReadFrequently: true });
      ctx.drawImage(img, 0, 0, w, h);
      var id = ctx.getImageData(0, 0, w, h);
      S.w = w; S.h = h; S.rgba = id.data;
      var n = w * h; S.L = new Float32Array(n); S.a = new Float32Array(n); S.b = new Float32Array(n);
      var lab = [0, 0, 0];
      for (var i = 0; i < n; i++) { E.rgbToLab(S.rgba[i * 4], S.rgba[i * 4 + 1], S.rgba[i * 4 + 2], lab); S.L[i] = lab[0]; S.a[i] = lab[1]; S.b[i] = lab[2]; }
      S.alpha = new Float32Array(n); S.face = new Float32Array(n); S.edge = new Uint8Array(n);
      S.noise = E.valueNoise(w, h, 3, 20240611);
      S.hasPhoto = true; S.g = null; S.gw = null; S.loc = null;
      el.empty.hidden = true;
      ['cvAfter', 'beforeWrap', 'divider', 'knob', 'tagBefore', 'tagAfter'].forEach(function (k) { el[k].hidden = false; });
      el.cvAfter.getContext('2d').drawImage(el.cvBefore, 0, 0);
      el.btnAuto.disabled = false; el.btnEdit.disabled = false; el.btnDownload.disabled = false; el.btnSave.disabled = false;
      setSplit(0.5);
      autoDetect();
    }).catch(function () { setStatus('Could not open that photo. Try a JPG or PNG.'); });
  }

  /* ---------------- hair detection ---------------- */
  el.btnAuto.addEventListener('click', autoDetect);

  function autoDetect() {
    if (!S.hasPhoto || segBusy) return;
    segBusy = true; el.btnAuto.disabled = true; setStatus('Finding your hair… (first time downloads a small model, ~16 MB)');
    getSegmenter().then(function (seg) {
      var res = seg.segment(el.cvBefore);
      var masks = res.confidenceMasks;
      var hair = masks[1].getAsFloat32Array(), face = masks[3].getAsFloat32Array();
      var mw = masks[1].width, mh = masks[1].height;
      fillMask(S.alpha, hair, mw, mh, true); fillMask(S.face, face, mw, mh, false);
      try { if (res.close) res.close(); else masks.forEach(function (m) { m.close(); }); } catch (e) { /* ignore */ }
      var cnt = 0; for (var i = 0; i < S.alpha.length; i++) if (S.alpha[i] > 0.5) cnt++;
      if (cnt < S.alpha.length * 0.01) setStatus('I could not find much hair. Tap "Fix hair outline" and paint over your hair.');
      else setStatus('Hair found. Check the outline with "Fix hair outline" if needed, then pick a formula.');
      afterMaskChange();
    }).catch(function (err) {
      console.error(err);
      setStatus('Automatic hair finding did not load (needs internet). Use "Fix hair outline" and paint over your hair with the brush instead.');
    }).then(function () { segBusy = false; el.btnAuto.disabled = false; });
  }

  function getSegmenter() {
    if (S.seg) return Promise.resolve(S.seg);
    return import(MP_BASE + '/vision_bundle.mjs').then(function (mod) {
      return mod.FilesetResolver.forVisionTasks(MP_BASE + '/wasm').then(function (fs) {
        return mod.ImageSegmenter.createFromOptions(fs, {
          baseOptions: { modelAssetPath: MODEL_URL }, runningMode: 'IMAGE', outputConfidenceMasks: true, outputCategoryMask: false
        });
      });
    }).then(function (seg) { S.seg = seg; return seg; });
  }

  // copy a (possibly different sized) model mask into the full-size array
  function fillMask(dst, src, mw, mh, sharpen) {
    var w = S.w, h = S.h;
    for (var y = 0; y < h; y++) {
      var fy = (y + 0.5) * mh / h - 0.5, y0 = Math.max(0, Math.min(mh - 1, Math.floor(fy))), y1 = Math.min(mh - 1, y0 + 1), ty = Math.max(0, fy - y0);
      for (var x = 0; x < w; x++) {
        var fx = (x + 0.5) * mw / w - 0.5, x0 = Math.max(0, Math.min(mw - 1, Math.floor(fx))), x1 = Math.min(mw - 1, x0 + 1), tx = Math.max(0, fx - x0);
        var v = (src[y0 * mw + x0] * (1 - tx) + src[y0 * mw + x1] * tx) * (1 - ty) + (src[y1 * mw + x0] * (1 - tx) + src[y1 * mw + x1] * tx) * ty;
        dst[y * w + x] = sharpen ? E.smoothstep(0.3, 0.7, v) : v;
      }
    }
  }

  /* ---------------- pipeline stages ---------------- */
  var tGray = null;
  function afterMaskChange() { computeEdge(); scheduleGray(); }

  function computeEdge() {
    var n = S.w * S.h, minX = S.w, maxX = 0, i, x;
    for (i = 0; i < n; i++) if (S.alpha[i] > 0.5) { x = i % S.w; if (x < minX) minX = x; if (x > maxX) maxX = x; }
    var zonePx = (maxX > minX ? (maxX - minX) : S.w) * (+el.zone.value / 100);
    var hasFace = false; for (i = 0; i < n; i += 7) if (S.face[i] > 0.5) { hasFace = true; break; }
    S.edge = new Uint8Array(n);
    if (hasFace) {
      var d = E.distanceTo(S.face, S.w, S.h);
      for (i = 0; i < n; i++) S.edge[i] = (S.alpha[i] > 0.5 && d[i] < zonePx) ? 1 : 0;
    }
  }

  function scheduleGray() { clearTimeout(tGray); tGray = setTimeout(computeGray, 90); }

  function computeGray() {
    if (!S.hasPhoto) return;
    var gw = E.grayWeights({ L: S.L, a: S.a, b: S.b, alpha: S.alpha, edge: S.edge, pctBody: +el.pBody.value / 100, pctEdge: +el.pEdge.value / 100 });
    S.gw = gw; S.g = gw.g;
    S.loc = E.localPigMean({ L: S.L, a: S.a, b: S.b, alpha: S.alpha, g: S.g, w: S.w, h: S.h }, Math.max(6, Math.round(S.w / 80)));
    var cnt = 0, sa = 0, sb = 0;
    for (var i = 0; i < S.g.length; i++) if (S.alpha[i] > 0.5 && S.g[i] < 0.2) { sa += S.a[i]; sb += S.b[i]; cnt++; }
    S.glob = { L: gw.pigL, a: cnt ? sa / cnt : 8, b: cnt ? sb / cnt : 14 };
    updateHairNote(); drawOverlay(); renderNow();
  }

  function effectiveLevel() { return S.manualLevel != null ? S.manualLevel : (S.gw ? S.gw.pigLevel : 4); }

  function updateHairNote() {
    if (!S.gw || !S.gw.hairPixels) { el.hairNote.textContent = 'No hair marked yet.'; return; }
    var guess = Math.round(E.otsuGrayShare(S.L, S.alpha) * 100);
    el.hairNote.textContent = 'Your brown reads as about level ' + S.gw.pigLevel.toFixed(1) + (S.manualLevel != null ? ' (you set ' + S.manualLevel + ')' : '') +
      '. Marked ' + Math.round(S.gw.grayShare * 100) + '% of hair as gray. A quick brightness split of the photo alone suggests ~' + guess +
      '%. Tick "show where it thinks my gray is" and move the sliders until it matches what you see.';
    if (S.manualLevel == null) { el.level.value = Math.round(S.gw.pigLevel * 2) / 2; el.vLevel.textContent = 'auto (' + S.gw.pigLevel.toFixed(1) + ')'; }
  }

  /* ---------------- rendering ---------------- */
  var tRender = null;
  function renderNow() { clearTimeout(tRender); tRender = setTimeout(doRender, 30); }

  function currentResponse(band) {
    if (!S.line || !S.shade || !S.dev) return null;
    var R = E.buildResponse({ line: S.line, shade: S.shade, dev: S.dev, minutes: S.minutes, band: band || S.band, calib: S.calib });
    R.baseShift = S.manualLevel != null && S.gw ? S.manualLevel - S.gw.pigLevel : 0;
    return R;
  }

  function doRender() {
    if (!S.hasPhoto) return;
    var R = currentResponse();
    renderExplain(R);
    if (!R || !S.g) return;
    var src = { w: S.w, h: S.h, rgba: S.rgba, L: S.L, a: S.a, b: S.b, alpha: S.alpha, g: S.g, loc: S.loc, noise: S.noise, grayRefL: S.gw.grayRefL, glob: S.glob };
    var out = E.render(src, R);
    el.cvAfter.getContext('2d').putImageData(new ImageData(out, S.w, S.h), 0, 0);
  }

  function renderExplain(R) {
    var box = el.explain; box.innerHTML = '';
    if (!R) { box.innerHTML = '<span class="note">Pick a formula.</span>'; return; }
    var rgb = E.labToRgb(R.dye[0], R.dye[1], R.dye[2], [0, 0, 0]);
    var head = document.createElement('div');
    head.innerHTML = '<span class="swatch" style="background:rgb(' + rgb.map(Math.round).join(',') + ')"></span><b>' + esc(S.line.brand + ' ' + S.line.name) + '</b> — ' +
      esc(S.shade.code + ' ' + (S.shade.name || '')) + '<br><span class="note">' + esc(S.dev.name) + ' · ' + esc(S.line.ratio) + ' · ' + S.minutes + ' min</span>';
    box.appendChild(head);
    var hair = { pigLevel: effectiveLevel() };
    E.explain(S.line, S.shade, S.dev, S.minutes, R, hair).forEach(function (m) {
      var d = document.createElement('div'); d.className = 'msg ' + m.kind; d.textContent = m.text; box.appendChild(d);
    });
    if (!S.line.shadesVerified && !S.shade.verified) {
      var d2 = document.createElement('div'); d2.className = 'msg warn';
      d2.textContent = 'This shade list is a level/tone grid, not the brand\'s official chart. The code and swatch are approximate — match the level and tone letters to your real box.';
      box.appendChild(d2);
    }
  }

  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

  /* ---------------- overlay (gray map + hair outline) ---------------- */
  function drawOverlay() {
    var c = el.cvOver, ctx = c.getContext('2d');
    ctx.clearRect(0, 0, c.width, c.height);
    var show = S.edit || el.chkGray.checked;
    c.hidden = !show; if (!show || !S.hasPhoto) return;
    var id = ctx.createImageData(S.w, S.h), d = id.data, n = S.w * S.h;
    for (var i = 0; i < n; i++) {
      var o = i * 4;
      if (S.edit) { var a = S.alpha[i]; if (a > 0.02) { d[o] = 255; d[o + 1] = 40; d[o + 2] = 120; d[o + 3] = Math.round(a * 110); } }
      else if (S.g && S.alpha[i] > 0.5 && S.g[i] > 0.5) { d[o] = 0; d[o + 1] = 230; d[o + 2] = 255; d[o + 3] = 170; }
    }
    ctx.putImageData(id, 0, 0);
  }
  el.chkGray.addEventListener('change', drawOverlay);

  /* ---------------- before / after slider ---------------- */
  function setSplit(p) {
    S.split = Math.max(0, Math.min(1, p));
    el.beforeWrap.style.clipPath = S.edit ? 'none' : 'inset(0 ' + (100 - S.split * 100) + '% 0 0)';
    el.divider.style.left = el.knob.style.left = (S.split * 100) + '%';
  }
  var dragging = false;
  el.stage.addEventListener('pointerdown', function (e) {
    if (!S.hasPhoto) return;
    if (S.edit) { paintStart(e); return; }
    dragging = true; el.stage.setPointerCapture(e.pointerId); moveSplit(e);
  });
  el.stage.addEventListener('pointermove', function (e) { if (S.edit) paintMove(e); else if (dragging) moveSplit(e); });
  el.stage.addEventListener('pointerup', function (e) { if (S.edit) paintEnd(); dragging = false; });
  el.stage.addEventListener('pointercancel', function () { if (S.edit) paintEnd(); dragging = false; });
  function moveSplit(e) { var r = el.stage.getBoundingClientRect(); setSplit((e.clientX - r.left) / r.width); }

  /* ---------------- hair outline brush ---------------- */
  var painting = false;
  el.btnEdit.addEventListener('click', function () { S.edit = true; el.brushTools.hidden = false; el.btnEdit.hidden = true; el.cvAfter.style.visibility = 'hidden'; el.divider.hidden = el.knob.hidden = true; el.tagAfter.hidden = true; setSplit(S.split); drawOverlay(); });
  el.btnDone.addEventListener('click', function () { S.edit = false; el.brushTools.hidden = true; el.btnEdit.hidden = false; el.cvAfter.style.visibility = 'visible'; el.divider.hidden = el.knob.hidden = false; el.tagAfter.hidden = false; setSplit(S.split); afterMaskChange(); });
  el.bAdd.addEventListener('click', function () { S.brush = 'add'; el.bAdd.classList.add('on'); el.bErase.classList.remove('on'); });
  el.bErase.addEventListener('click', function () { S.brush = 'erase'; el.bErase.classList.add('on'); el.bAdd.classList.remove('on'); });
  var lastPt = null;
  function paintStart(e) { painting = true; el.stage.setPointerCapture(e.pointerId); lastPt = null; paintMove(e); }
  function paintEnd() { painting = false; lastPt = null; }
  function paintMove(e) {
    if (!painting) return;
    var r = el.stage.getBoundingClientRect(), sc = S.w / r.width;
    var x = (e.clientX - r.left) * sc, y = (e.clientY - r.top) * sc, rad = (+el.brushSize.value) * sc;
    var from = lastPt || { x: x, y: y }, dist = Math.hypot(x - from.x, y - from.y), steps = Math.max(1, Math.ceil(dist / (rad * 0.4)));
    for (var s = 1; s <= steps; s++) stamp(from.x + (x - from.x) * s / steps, from.y + (y - from.y) * s / steps, rad);
    lastPt = { x: x, y: y }; drawOverlay();
  }
  function stamp(cx, cy, rad) {
    var x0 = Math.max(0, Math.floor(cx - rad - 1)), x1 = Math.min(S.w - 1, Math.ceil(cx + rad + 1)), y0 = Math.max(0, Math.floor(cy - rad - 1)), y1 = Math.min(S.h - 1, Math.ceil(cy + rad + 1));
    for (var y = y0; y <= y1; y++) for (var x = x0; x <= x1; x++) {
      var d = Math.hypot(x - cx, y - cy); if (d > rad + 1) continue;
      var k = Math.max(0, Math.min(1, rad + 1 - d)), i = y * S.w + x;
      if (S.brush === 'add') S.alpha[i] = Math.max(S.alpha[i], k); else S.alpha[i] = Math.min(S.alpha[i], 1 - k);
    }
  }

  /* ---------------- controls: hair ---------------- */
  function bindRange(input, label, fmt, after) {
    input.addEventListener('input', function () { label.textContent = fmt(+input.value); after(); });
  }
  bindRange(el.pBody, el.vBody, function (v) { return v + '%'; }, scheduleGray);
  bindRange(el.pEdge, el.vEdge, function (v) { return v + '%'; }, scheduleGray);
  bindRange(el.zone, el.vZone, function (v) { return v + '%'; }, function () { if (S.hasPhoto) { computeEdge(); scheduleGray(); } });
  el.level.addEventListener('input', function () { S.manualLevel = +el.level.value; el.vLevel.textContent = el.level.value; updateHairNote(); renderNow(); });
  el.btnAutoLevel.addEventListener('click', function () { S.manualLevel = null; updateHairNote(); renderNow(); });

  /* ---------------- controls: formula ---------------- */
  (function buildLines() {
    var brands = {}, order = [];
    D.LINES.forEach(function (l) { if (!brands[l.brand]) { brands[l.brand] = []; order.push(l.brand); } brands[l.brand].push(l); });
    order.forEach(function (b) {
      var g = document.createElement('optgroup'); g.label = b;
      brands[b].forEach(function (l) { var o = document.createElement('option'); o.value = l.id; o.textContent = l.name + (l.type === 'demi' ? '' : ''); g.appendChild(o); });
      el.line.appendChild(g);
    });
    for (var i = 1; i <= 12; i++) { var o = document.createElement('option'); o.value = i; o.textContent = 'Level ' + i + ' ' + D.LEVEL_NAMES[i]; el.cLevel.appendChild(o); }
    Object.keys(D.TONE_NAMES).forEach(function (k) { var o = document.createElement('option'); o.value = k; o.textContent = k + ' — ' + D.TONE_NAMES[k]; el.cTone.appendChild(o); });
    el.cLevel.value = 5; el.cTone.value = 'BC';
  })();

  el.line.addEventListener('change', function () { selectLine(el.line.value); });

  function selectLine(id) {
    S.line = D.LINES.filter(function (l) { return l.id === id; })[0];
    var l = S.line;
    el.lineMeta.innerHTML = esc(l.type === 'demi' ? 'Demi-permanent / gloss — deposits, does not lighten.' : 'Permanent — can lift and covers gray.') +
      ' Mix ' + esc(l.ratio) + '.<span class="badge ' + l.confidence + '">' + (l.confidence === 'checked' ? 'instructions checked' : l.confidence === 'partial' ? 'partly checked' : 'unverified') + '</span>';
    el.dev.innerHTML = '';
    l.devs.forEach(function (d) { var o = document.createElement('option'); o.value = d.id; o.textContent = d.name; el.dev.appendChild(o); });
    el.dev.value = l.defaultDev; S.dev = l.devs.filter(function (d) { return d.id === l.defaultDev; })[0];
    el.devNote.textContent = S.dev.note;
    var tmin = 5, tmax = 60;
    el.time.min = tmin; el.time.max = tmax; S.minutes = Math.round(l.minutes.def / 5) * 5; el.time.value = S.minutes; el.vTime.textContent = S.minutes + ' min';
    el.timeNote.textContent = 'Usual for this line: ' + l.minutes.min + '–' + l.minutes.max + ' min. Check the box for your exact shade.';
    el.shadeSearch.value = ''; fillShades(); renderFacts();
  }

  function fillShades() {
    var q = el.shadeSearch.value.trim().toLowerCase(), keep = S.shade && S.shade.code, sel = null;
    el.shade.innerHTML = '';
    S.line.shades.forEach(function (s, idx) {
      if (q && (s.label.toLowerCase().indexOf(q) < 0)) return;
      var o = document.createElement('option'); o.value = idx; o.textContent = s.label + (s.verified ? '' : '  (approx.)');
      var rgb = E.labToRgb.apply(null, E.dyeLab(s.level, s.tone).concat([[0, 0, 0]]));
      o.style.borderLeft = '14px solid rgb(' + rgb.map(Math.round).join(',') + ')'; o.style.paddingLeft = '6px';
      el.shade.appendChild(o); if (keep && s.code === keep && !sel) sel = o;
    });
    if (!el.shade.options.length) { S.shade = null; renderNow(); return; }
    if (!sel) { // sensible default: a natural level-5 brown if the list has one
      for (var k = 0; k < el.shade.options.length; k++) {
        var cand = S.line.shades[+el.shade.options[k].value];
        if (cand.level === 5 && /^(N|NB)$/.test(cand.tone)) { sel = el.shade.options[k]; break; }
      }
    }
    if (!sel) sel = el.shade.options[0];
    sel.selected = true; S.shade = S.line.shades[+sel.value]; renderNow();
  }
  el.shadeSearch.addEventListener('input', fillShades);
  el.shade.addEventListener('change', function () { S.shade = S.line.shades[+el.shade.value]; renderNow(); });
  el.btnCustom.addEventListener('click', function () {
    var lv = +el.cLevel.value, tn = el.cTone.value;
    S.shade = { code: lv + tn, name: 'Custom ' + D.LEVEL_NAMES[lv] + ' ' + D.TONE_NAMES[tn], level: lv, tone: tn, verified: true, label: 'Custom' }; renderNow();
  });
  el.dev.addEventListener('change', function () { S.dev = S.line.devs.filter(function (d) { return d.id === el.dev.value; })[0]; el.devNote.textContent = S.dev.note; renderNow(); });
  el.time.addEventListener('input', function () { S.minutes = +el.time.value; el.vTime.textContent = S.minutes + ' min'; renderNow(); });

  function renderFacts() {
    var l = S.line, h = '<ul class="facts">' + l.facts.map(function (f) { return '<li>' + esc(f) + '</li>'; }).join('') + '</ul>';
    if (l.assumed && l.assumed.length) h += '<p class="note"><b>Assumed / not confirmed:</b></p><ul class="facts">' + l.assumed.map(function (f) { return '<li>' + esc(f) + '</li>'; }).join('') + '</ul>';
    h += '<p class="note"><b>Sources:</b> ' + l.sources.map(function (s) { return '<a href="' + esc(s.url) + '" target="_blank" rel="noopener">' + esc(s.label) + '</a>'; }).join(' · ') + '</p>';
    el.lineFacts.innerHTML = h;
  }

  /* ---------------- low / expected / high ---------------- */
  el.viewChips.addEventListener('click', function (e) {
    var b = e.target.closest('button[data-view]'); if (!b) return;
    S.band = b.getAttribute('data-view');
    Array.prototype.forEach.call(el.viewChips.querySelectorAll('button'), function (x) { x.classList.toggle('on', x === b); });
    renderNow();
  });

  /* ---------------- calibration ---------------- */
  function loadCalib() {
    try { var v = JSON.parse(localStorage.getItem('ht-calib') || 'null'); if (v) { el.calDepth.value = Math.round(v.depthBias * 10); el.calCov.value = Math.round(v.grayBias * 100); } } catch (e) { /* ignore */ }
    applyCalib(false);
  }
  function applyCalib(save) {
    S.calib = { depthBias: +el.calDepth.value / 10, grayBias: +el.calCov.value / 100 };
    el.vDepth.textContent = (S.calib.depthBias > 0 ? '+' : '') + S.calib.depthBias.toFixed(1) + ' level';
    el.vCovCal.textContent = Math.round(S.calib.grayBias * 100) + '%';
    if (save) { try { localStorage.setItem('ht-calib', JSON.stringify(S.calib)); } catch (e) { /* ignore */ } }
    renderNow();
  }
  el.calDepth.addEventListener('input', function () { applyCalib(true); });
  el.calCov.addEventListener('input', function () { applyCalib(true); });
  el.btnCalReset.addEventListener('click', function () { el.calDepth.value = 0; el.calCov.value = 100; applyCalib(true); });

  /* ---------------- save / download ---------------- */
  el.btnDownload.addEventListener('click', function () {
    el.cvAfter.toBlob(function (b) { var a = document.createElement('a'); a.href = URL.createObjectURL(b); a.download = 'hair-tryon.png'; a.click(); }, 'image/png');
  });
  el.btnSave.addEventListener('click', function () {
    if (!S.hasPhoto || !S.shade) return;
    var t = document.createElement('canvas'), k = 240 / S.w; t.width = 240; t.height = Math.round(S.h * k);
    t.getContext('2d').drawImage(el.cvAfter, 0, 0, t.width, t.height);
    var label = S.line.brand + ' ' + S.shade.code + ' · ' + S.dev.name.replace(/.*?(\d+ vol).*/, '$1').replace(/^[^0-9]*$/, 'std') + ' · ' + S.minutes + 'm · ' + S.band;
    var d = document.createElement('div'); d.className = 'look';
    d.innerHTML = '<img alt=""><div></div>'; d.firstChild.src = t.toDataURL('image/jpeg', 0.85); d.lastChild.textContent = label;
    el.looks.appendChild(d); el.looksCard.hidden = false;
  });

  /* ---------------- start ---------------- */
  el.line.value = 'wella-cc-perm';
  selectLine('wella-cc-perm');
  loadCalib();
  window.HTApp = { S: S, E: E, D: D, loadPhoto: loadPhoto, computeGray: computeGray, afterMaskChange: afterMaskChange, doRender: doRender };
})();
