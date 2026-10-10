/* Hair Color Try-On — color engine (pure math, no browser needed, so it can be unit tested in Node).
 *
 * THE MODEL, in plain words
 *  - Hair dye is see-through. The result = what is already on your head + what the dye does to it.
 *  - Two kinds of strands are treated separately:
 *      pigmented strands (your brown)  -> developer LIFTS them a bit, then dye DEPOSITS depth + tone
 *      gray/white strands (no pigment)  -> dye COVERS them by some amount (0..1) that depends on the
 *                                          line, developer, shade level/tone, and time. Partial coverage
 *                                          looks like some strands taking color and some staying sheer.
 *  - Light/shadow texture of your own photo is kept, so it still looks like your hair.
 *  - Numbers here are ESTIMATES from published instructions + general colorist rules, not lab data.
 */
(function (root) {
  'use strict';

  /* ---------- color space ---------- */
  var XN = 0.95047, YN = 1.0, ZN = 1.08883;
  function s2l(c) { c /= 255; return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); }
  function l2s(c) {
    c = c <= 0.0031308 ? 12.92 * c : 1.055 * Math.pow(c, 1 / 2.4) - 0.055;
    c = c * 255; return c < 0 ? 0 : c > 255 ? 255 : c;
  }
  function f(t) { return t > 216 / 24389 ? Math.cbrt(t) : (24389 / 27 * t + 16) / 116; }
  function finv(t) { var t3 = t * t * t; return t3 > 216 / 24389 ? t3 : (116 * t - 16) * 27 / 24389; }
  function rgbToLab(r, g, b, o) {
    var R = s2l(r), G = s2l(g), B = s2l(b);
    var x = (0.4124564 * R + 0.3575761 * G + 0.1804375 * B) / XN;
    var y = (0.2126729 * R + 0.7151522 * G + 0.0721750 * B) / YN;
    var z = (0.0193339 * R + 0.1191920 * G + 0.9503041 * B) / ZN;
    var fx = f(x), fy = f(y), fz = f(z);
    o[0] = 116 * fy - 16; o[1] = 500 * (fx - fy); o[2] = 200 * (fy - fz); return o;
  }
  function labToRgb(L, a, b, o) {
    var fy = (L + 16) / 116, fx = fy + a / 500, fz = fy - b / 200;
    var x = finv(fx) * XN, y = finv(fy) * YN, z = finv(fz) * ZN;
    o[0] = l2s(3.2404542 * x - 1.5371385 * y - 0.4985314 * z);
    o[1] = l2s(-0.9692660 * x + 1.8760108 * y + 0.0415560 * z);
    o[2] = l2s(0.0556434 * x - 0.2040259 * y + 1.0572252 * z);
    return o;
  }

  /* ---------- hair "levels" (the 1-10 scale colorists use) <-> lightness ---------- */
  // Approximate L* of hair at each level as it looks in a photo.
  var LEVEL_L = [0, 10, 15, 20, 26, 33, 41, 49, 58, 66, 74, 80, 85];
  function levelToL(level) {
    if (level <= 1) return LEVEL_L[1];
    if (level >= 12) return LEVEL_L[12];
    var i = Math.floor(level), t = level - i;
    return LEVEL_L[i] + (LEVEL_L[i + 1] - LEVEL_L[i]) * t;
  }
  function levelFromL(L) {
    if (L <= LEVEL_L[1]) return 1;
    if (L >= LEVEL_L[12]) return 12;
    for (var i = 1; i < 12; i++) {
      if (L <= LEVEL_L[i + 1]) return i + (L - LEVEL_L[i]) / (LEVEL_L[i + 1] - LEVEL_L[i]);
    }
    return 12;
  }

  /* ---------- tone families -> (a*, b*) at a mid level ---------- */
  var TONES = {
    N: [7, 13], NN: [9, 17], NB: [6, 12], B: [6, 11], A: [0, 4], AA: [-1, 2], AB: [2, 7],
    G: [7, 24], NG: [7, 18], GB: [8, 20], W: [11, 22], NW: [8, 16], WV: [14, 10], WR: [16, 22],
    C: [20, 26], R: [28, 15], RG: [24, 22], RV: [26, 5], V: [10, -6], BC: [13, 20], P: [0, 0]
  };
  function toneVector(key) { return TONES[key] || TONES.N; }
  function chromaScale(level) { var s = 0.6 + 0.07 * level; return s > 1.3 ? 1.3 : s; }
  function dyeLab(level, toneKey) {
    var t = toneVector(toneKey), cs = chromaScale(level);
    return [levelToL(level), t[0] * cs, t[1] * cs];
  }

  /* ---------- time ---------- */
  // Dye uptake saturates: most of the effect happens early; extra minutes add a little.
  // Normalised so the line's recommended time = 1.0.
  function timeFactor(minutes, refMinutes) {
    var tau = refMinutes * 0.45;
    var g = (1 - Math.exp(-minutes / tau)) / (1 - Math.exp(-refMinutes / tau));
    return g > 1.08 ? 1.08 : g;
  }

  /* ---------- how well a shade covers gray ---------- */
  function levelCoverFactor(level) { return level <= 7 ? 1 : Math.max(0.45, 1 - 0.13 * (level - 7)); } // Wella: level 8+ goes translucent
  function toneCoverFactor(key) {
    var f0 = 0.94;
    if (/^(N|NN|NG|NB|B|G|GB)$/.test(key)) f0 = key === 'NN' ? 1.04 : 1.0;
    else if (/A|V|P/.test(key.replace('WV', 'W').replace('RV', 'R'))) f0 = 0.88; // ash / violet / pearl = cool, less opaque
    else if (/^(R|RV|RG|C|WR)$/.test(key)) f0 = 0.93;
    return f0;
  }

  /* ---------- the formula's response ---------- */
  var BANDS = { low: { cov: 0.78, depth: -0.4, lift: 0.8 }, expected: { cov: 1, depth: 0, lift: 1 }, high: { cov: 1.12, depth: 0.4, lift: 1.15 } };

  /**
   * @param o {line, shade:{level,tone}, dev, minutes, band, calib:{grayBias,depthBias}}
   */
  function buildResponse(o) {
    var line = o.line, dev = o.dev, shade = o.shade, band = BANDS[o.band || 'expected'];
    var calib = o.calib || { grayBias: 1, depthBias: 0 };
    var demi = line.type === 'demi';
    var g = timeFactor(o.minutes, line.minutes.def);
    var lift = demi ? 0 : dev.lift * g * band.lift;
    var depositDepth = (demi ? 0.6 : 0.97) * Math.min(1.05, g);
    var lightenLeak = demi ? 0 : 0.06;
    var toneWeight = (demi ? 0.65 : 0.92) * Math.min(1.05, g);
    var cov = line.grayMax * dev.cov * levelCoverFactor(shade.level) * toneCoverFactor(shade.tone) * Math.min(1.05, g) *
      band.cov * calib.grayBias;
    if (cov > 0.985) cov = 0.985;
    var dyeLevel = shade.level + calib.depthBias + band.depth;
    return {
      demi: demi, lift: lift, depositDepth: depositDepth > 1 ? 1 : depositDepth, lightenLeak: lightenLeak,
      toneWeight: toneWeight > 1 ? 1 : toneWeight, grayCov: cov, dyeLevel: dyeLevel,
      dye: dyeLab(dyeLevel, shade.tone), tone: shade.tone, timeFactor: g
    };
  }

  /* ---------- pigmented-strand result ---------- */
  var tmp3 = [0, 0, 0];
  function pigResult(R, baseL, baseA, baseB, pixL, out) {
    var Bl = levelFromL(baseL) + (R.baseShift || 0); // baseShift = your manual "natural level" override
    var lifted = Bl + R.lift;
    var a = baseA + R.lift * 1.6, b = baseB + R.lift * 3.2; // lifting exposes warm undertone
    var Dl = R.dyeLevel, rl;
    if (Dl <= lifted) rl = lifted + (Dl - lifted) * R.depositDepth;
    else rl = lifted + (Dl - lifted) * R.lightenLeak;
    // tone is much less visible when the dye is lighter than the hair underneath
    var tv = Dl <= lifted ? 1 : Math.max(0.25, 1 - 0.18 * (Dl - lifted));
    var w = R.toneWeight * tv;
    a = a + (R.dye[1] - a) * w; b = b + (R.dye[2] - b) * w;
    var Lres = levelToL(rl) + (pixL - baseL); // keep the photo's light/shadow texture
    out[0] = Lres; out[1] = a; out[2] = b; return out;
  }

  /* ---------- gray-strand result ---------- */
  function smoothstep(e0, e1, x) { var t = (x - e0) / (e1 - e0); t = t < 0 ? 0 : t > 1 ? 1 : t; return t * t * (3 - 2 * t); }
  function grayResult(R, L, a, b, noise, grayRefL, out) {
    var cov = R.grayCov;
    // each strand takes color or stays sheer; partial coverage = a mix of both
    var sc = 0.2 * cov + 0.8 * smoothstep(noise - 0.18, noise + 0.18, cov);
    var swL = R.dye[0] + (L - grayRefL) * 0.45;
    out[0] = L + (swL - L) * sc; out[1] = a + (R.dye[1] - a) * sc; out[2] = b + (R.dye[2] - b) * sc; return out;
  }

  /* ---------- image-wide helpers ---------- */
  function boxBlur(src, w, h, r) {
    var tmp = new Float32Array(w * h), out = new Float32Array(w * h), x, y, i, acc, k;
    var d = 2 * r + 1;
    for (y = 0; y < h; y++) {
      acc = 0; var row = y * w;
      for (k = -r; k <= r; k++) acc += src[row + Math.min(w - 1, Math.max(0, k))];
      for (x = 0; x < w; x++) {
        tmp[row + x] = acc / d;
        acc += src[row + Math.min(w - 1, x + r + 1)] - src[row + Math.max(0, x - r)];
      }
    }
    for (x = 0; x < w; x++) {
      acc = 0;
      for (k = -r; k <= r; k++) acc += tmp[Math.min(h - 1, Math.max(0, k)) * w + x];
      for (y = 0; y < h; y++) {
        i = y * w + x; out[i] = acc / d;
        acc += tmp[Math.min(h - 1, y + r + 1) * w + x] - tmp[Math.max(0, y - r) * w + x];
      }
    }
    return out;
  }

  // distance (in pixels) from each pixel to the nearest "on" pixel of `src` (>0.5). Chamfer 3-4.
  function distanceTo(src, w, h) {
    var INF = 1e9, d = new Float32Array(w * h), i, x, y;
    for (i = 0; i < w * h; i++) d[i] = src[i] > 0.5 ? 0 : INF;
    for (y = 0; y < h; y++) for (x = 0; x < w; x++) {
      i = y * w + x; var v = d[i];
      if (x > 0) v = Math.min(v, d[i - 1] + 1);
      if (y > 0) { v = Math.min(v, d[i - w] + 1); if (x > 0) v = Math.min(v, d[i - w - 1] + 1.414); if (x < w - 1) v = Math.min(v, d[i - w + 1] + 1.414); }
      d[i] = v;
    }
    for (y = h - 1; y >= 0; y--) for (x = w - 1; x >= 0; x--) {
      i = y * w + x; var v2 = d[i];
      if (x < w - 1) v2 = Math.min(v2, d[i + 1] + 1);
      if (y < h - 1) { v2 = Math.min(v2, d[i + w] + 1); if (x < w - 1) v2 = Math.min(v2, d[i + w + 1] + 1.414); if (x > 0) v2 = Math.min(v2, d[i + w - 1] + 1.414); }
      d[i] = v2;
    }
    return d;
  }

  function valueNoise(w, h, scale, seed) {
    var gw = Math.ceil(w / scale) + 2, gh = Math.ceil(h / scale) + 2, grid = new Float32Array(gw * gh), s = seed >>> 0 || 1, i;
    for (i = 0; i < grid.length; i++) { s ^= s << 13; s >>>= 0; s ^= s >>> 17; s ^= s << 5; s >>>= 0; grid[i] = s / 4294967295; }
    var out = new Float32Array(w * h);
    for (var y = 0; y < h; y++) {
      var gy = y / scale, y0 = Math.floor(gy), fy = gy - y0; fy = fy * fy * (3 - 2 * fy);
      for (var x = 0; x < w; x++) {
        var gx = x / scale, x0 = Math.floor(gx), fx = gx - x0; fx = fx * fx * (3 - 2 * fx);
        var a = grid[y0 * gw + x0], b = grid[y0 * gw + x0 + 1], c = grid[(y0 + 1) * gw + x0], d2 = grid[(y0 + 1) * gw + x0 + 1];
        out[y * w + x] = (a + (b - a) * fx) * (1 - fy) + (c + (d2 - c) * fx) * fy;
      }
    }
    // value noise clusters around 0.5; stretch to roughly 0..1 so coverage fractions behave
    for (i = 0; i < out.length; i++) { var v = (out[i] - 0.5) * 2.2 + 0.5; out[i] = v < 0 ? 0 : v > 1 ? 1 : v; }
    return out;
  }

  function quantile(arr, q) {
    if (!arr.length) return 0;
    var a = Float32Array.from(arr).sort(); var i = Math.min(a.length - 1, Math.max(0, Math.round(q * (a.length - 1)))); return a[i];
  }

  /**
   * Decide which hair pixels are gray strands.
   * We score each hair pixel by how bright / colorless it is compared to the rest of the hair, then pick the
   * brightest `pctBody` share (and `pctEdge` share in the hairline/temple zone) as gray.
   * @param p {L,a,b: Float32Array, alpha: Float32Array, edge: Uint8Array (1 = hairline/temple zone), pctBody, pctEdge}
   */
  function grayWeights(p) {
    var n = p.L.length, idx = [], i;
    for (i = 0; i < n; i++) if (p.alpha[i] > 0.5) idx.push(i);
    var g = new Float32Array(n);
    if (!idx.length) return { g: g, score: new Float32Array(n), pigLevel: 4, pigL: 25, grayRefL: 60, hairPixels: 0, grayShare: 0, zoneShare: [0, 0, 0] };
    // zones: 0 = top & sides, 1 = hairline / temples, 2 = lengths. pct = max gray share per zone.
    var zone = p.zone || (p.edge ? Uint8Array.from(p.edge) : new Uint8Array(n));
    var pct = p.pct || [p.pctBody, p.pctEdge, p.pctBody];
    var sens = p.sens == null ? 14 : p.sens; // how far above your dark base a strand must be to count as gray (L* units)
    var score = new Float32Array(n), all = [], byZone = [[], [], []], Ls = [];
    idx.forEach(function (j) {
      // gray = bright AND colorless (shine on dark hair is bright too, so sens sets an absolute floor)
      var s = p.L[j] - 0.6 * Math.sqrt(p.a[j] * p.a[j] + p.b[j] * p.b[j]);
      score[j] = s; all.push(s); Ls.push(p.L[j]); byZone[zone[j]].push(s);
    });
    var floor = quantile(all, 0.25) + sens; // dark base + sensitivity
    var thr = byZone.map(function (arr, z) {
      var q = pct[z] <= 0 ? 1e9 : pct[z] >= 1 ? -1e9 : (arr.length ? quantile(arr, 1 - pct[z]) : 1e9);
      return pct[z] <= 0 ? 1e9 : Math.max(q, floor); // slider is a CAP: never call a strand gray that is not clearly lighter than your base
    });
    var w = 2.5, grayN = 0, pigL = [], grayL = [], zn = [0, 0, 0], zg = [0, 0, 0];
    idx.forEach(function (j) {
      var z = zone[j], v = smoothstep(thr[z] - w, thr[z] + w, score[j]); g[j] = v; zn[z]++;
      if (v > 0.5) { grayN++; zg[z]++; grayL.push(p.L[j]); } else pigL.push(p.L[j]);
    });
    var pigMed = quantile(pigL.length ? pigL : Ls, 0.6);
    var Lm = 0; Ls.forEach(function (v) { Lm += v; }); Lm /= Ls.length;
    return {
      g: g, score: score, pigL: pigMed, pigLevel: levelFromL(pigMed), floor: floor,
      grayRefL: grayL.length ? quantile(grayL, 0.5) : Lm + 25, hairPixels: idx.length, grayShare: grayN / idx.length,
      zoneShare: zn.map(function (c, z) { return c ? zg[z] / c : 0; })
    };
  }

  // Otsu split on the gray score -> a first guess at how much of the hair is gray
  function otsuGrayShare(L, alpha) {
    var vals = [], i; for (i = 0; i < L.length; i++) if (alpha[i] > 0.5) vals.push(L[i]);
    if (vals.length < 50) return 0;
    var hist = new Float64Array(101); vals.forEach(function (v) { hist[Math.max(0, Math.min(100, Math.round(v)))]++; });
    var total = vals.length, sum = 0; for (i = 0; i < 101; i++) sum += i * hist[i];
    var wB = 0, sB = 0, best = -1, thr = 50;
    for (i = 0; i < 101; i++) {
      wB += hist[i]; if (!wB) continue; var wF = total - wB; if (!wF) break;
      sB += i * hist[i]; var mB = sB / wB, mF = (sum - sB) / wF, v = wB * wF * (mB - mF) * (mB - mF);
      if (v > best) { best = v; thr = i; }
    }
    var above = 0; vals.forEach(function (v) { if (v > thr) above++; });
    return above / total;
  }

  // local pigmented-hair average (so the base level follows your photo's own shading)
  function localPigMean(p, radius) {
    var n = p.L.length, w = new Float32Array(n), wl = new Float32Array(n), wa = new Float32Array(n), wb = new Float32Array(n);
    for (var i = 0; i < n; i++) {
      var k = p.alpha[i] > 0.5 ? (1 - p.g[i]) * (1 - p.g[i]) : 0;
      w[i] = k; wl[i] = k * p.L[i]; wa[i] = k * p.a[i]; wb[i] = k * p.b[i];
    }
    var bw = boxBlur(w, p.w, p.h, radius), bl = boxBlur(wl, p.w, p.h, radius), ba = boxBlur(wa, p.w, p.h, radius), bb = boxBlur(wb, p.w, p.h, radius);
    return { w: bw, L: bl, a: ba, b: bb };
  }

  /**
   * Render. `src` = {w,h,rgba(Uint8ClampedArray),L,a,b,alpha,g,loc,noise,glob:{L,a,b},grayRefL}
   * Returns a new Uint8ClampedArray (RGBA) with the recolored hair.
   */
  function render(src, R) {
    var n = src.w * src.h, out = new Uint8ClampedArray(src.rgba.length);
    var P = [0, 0, 0], G = [0, 0, 0], rgb = [0, 0, 0];
    for (var i = 0; i < n; i++) {
      var al = src.alpha[i], o = i * 4;
      if (al <= 0.003) { out[o] = src.rgba[o]; out[o + 1] = src.rgba[o + 1]; out[o + 2] = src.rgba[o + 2]; out[o + 3] = src.rgba[o + 3]; continue; }
      var g = src.g[i], L = src.L[i], a = src.a[i], b = src.b[i];
      var Lf, af, bf;
      if (g < 0.995) {
        var lw = src.loc.w[i], bL, bA, bB;
        if (lw > 0.02) { bL = src.loc.L[i] / lw; bA = src.loc.a[i] / lw; bB = src.loc.b[i] / lw; } else { bL = src.glob.L; bA = src.glob.a; bB = src.glob.b; }
        pigResult(R, bL, bA, bB, L, P);
      }
      if (g > 0.005) grayResult(R, L, a, b, src.noise[i], src.grayRefL, G);
      if (g <= 0.005) { Lf = P[0]; af = P[1]; bf = P[2]; }
      else if (g >= 0.995) { Lf = G[0]; af = G[1]; bf = G[2]; }
      else { Lf = P[0] + (G[0] - P[0]) * g; af = P[1] + (G[1] - P[1]) * g; bf = P[2] + (G[2] - P[2]) * g; }
      labToRgb(Lf, af, bf, rgb);
      var k = al > 1 ? 1 : al;
      out[o] = src.rgba[o] + (rgb[0] - src.rgba[o]) * k;
      out[o + 1] = src.rgba[o + 1] + (rgb[1] - src.rgba[o + 1]) * k;
      out[o + 2] = src.rgba[o + 2] + (rgb[2] - src.rgba[o + 2]) * k;
      out[o + 3] = src.rgba[o + 3];
    }
    return out;
  }

  /* ---------- plain-English explanation of a result ---------- */
  function explain(line, shade, dev, minutes, R, hair) {
    var out = [], lvl = hair.pigLevel;
    var after = lvl + R.lift;
    if (R.demi) out.push({ kind: 'info', text: 'Demi / gloss: it cannot lighten. It adds tone and some depth on top of your hair.' });
    else out.push({ kind: 'info', text: 'Expected lift from ' + dev.name + ': about ' + R.lift.toFixed(1) + ' level(s) on your brown hair (your brown reads as ~level ' + lvl.toFixed(1) + ').' });
    if (shade.level > after + 0.5) {
      out.push({ kind: 'warn', text: 'This shade (level ' + shade.level + ') is lighter than your hair can get with this formula (~level ' + after.toFixed(1) + '). On your brown hair it will look close to your own depth with only a little tone change. Your gray strands, though, will take it.' });
    }
    if (shade.level < lvl - 0.5) out.push({ kind: 'info', text: 'This shade is darker than your hair, so your brown will deepen toward level ' + shade.level + '.' });
    var pct = Math.round(R.grayCov * 100);
    out.push({ kind: pct >= 75 ? 'good' : pct >= 50 ? 'info' : 'warn', text: 'Estimated gray coverage: about ' + pct + '%.' + (pct < 60 ? ' Expect sheer, blended gray (some strands pick up color, some stay light).' : '') });
    if (!R.demi && dev.vol <= 10) out.push({ kind: 'warn', text: '10 vol with a permanent color is easier on your hair, but several sources say it does not cover gray well. The model lowers gray coverage to match.' });
    if (shade.level >= 8) out.push({ kind: 'warn', text: 'Level 8+ shades go translucent on gray (Wella). Going 1-2 levels darker usually covers gray better.' });
    if (/A|V|P/.test(shade.tone.replace('WV', 'W').replace('RV', 'R'))) out.push({ kind: 'info', text: 'Ash / violet / pearl tones are cool and less opaque on gray; the model lowers coverage a little. Adding a natural shade at the same level helps in real life.' });
    var tf = R.timeFactor;
    if (Math.abs(minutes - line.minutes.def) >= 5) out.push({ kind: 'info', text: 'Time: ' + minutes + ' min vs the usual ' + line.minutes.def + '. Most of the color happens early, so the change is modest (about ' + Math.round((tf - 1) * 100) + '% ' + (tf >= 1 ? 'more' : 'less') + ' effect).' });
    return out;
  }

  var API = {
    rgbToLab: rgbToLab, labToRgb: labToRgb, levelToL: levelToL, levelFromL: levelFromL, TONES: TONES, toneVector: toneVector,
    dyeLab: dyeLab, timeFactor: timeFactor, buildResponse: buildResponse, pigResult: pigResult, grayResult: grayResult,
    boxBlur: boxBlur, distanceTo: distanceTo, valueNoise: valueNoise, grayWeights: grayWeights, otsuGrayShare: otsuGrayShare,
    localPigMean: localPigMean, render: render, explain: explain, smoothstep: smoothstep, BANDS: BANDS
  };
  root.HTEngine = API;
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));
