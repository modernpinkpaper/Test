// Run:  node hair-tryon/test/engine.test.js
const assert = require('assert');
const E = require('../engine.js');
const D = require('../data.js');

let pass = 0;
function t(name, fn) { try { fn(); pass++; console.log('  ok  ' + name); } catch (e) { console.error('FAIL  ' + name + '\n      ' + e.message); process.exitCode = 1; } }
const line = id => D.LINES.find(l => l.id === id);
const dev = (l, id) => l.devs.find(d => d.id === id);
const resp = (lineId, shade, devId, minutes, extra) => {
  const l = line(lineId);
  return E.buildResponse(Object.assign({ line: l, shade, dev: dev(l, devId || l.defaultDev), minutes: minutes || l.minutes.def }, extra));
};
const pig = (R, level) => { const L = E.levelToL(level); const o = [0, 0, 0]; E.pigResult(R, L, 8, 14, L, o); return o; };

console.log('color math');
t('Lab round trip', () => {
  const lab = [0, 0, 0], rgb = [0, 0, 0];
  E.rgbToLab(120, 80, 60, lab); E.labToRgb(lab[0], lab[1], lab[2], rgb);
  assert(Math.abs(rgb[0] - 120) < 1 && Math.abs(rgb[1] - 80) < 1 && Math.abs(rgb[2] - 60) < 1);
});
t('level <-> L* round trip', () => { for (let l = 1; l <= 12; l += 0.5) assert(Math.abs(E.levelFromL(E.levelToL(l)) - l) < 1e-6, 'level ' + l); });

console.log('developer / lift rules');
const shade6 = { level: 6, tone: 'N' };
t('permanent on level 4: 20 vol lifts more than 10 vol', () => {
  const l10 = pig(resp('wella-cc-perm', shade6, '10'), 4)[0], l20 = pig(resp('wella-cc-perm', shade6, '20'), 4)[0];
  assert(l20 > l10, `${l20} should be > ${l10}`);
});
t('permanent 10 vol on dark hair: "same depth or darker, minimal lift" — result barely lighter than natural', () => {
  const R = resp('wella-cc-perm', { level: 4, tone: 'N' }, '10');
  const lvl = E.levelFromL(pig(R, 4)[0]);
  assert(lvl > 3.7 && lvl < 4.8, 'got level ' + lvl);
});
t('permanent cannot lighten past its lift (level 8 dye on level 4 hair, 20 vol)', () => {
  const lvl = E.levelFromL(pig(resp('wella-cc-perm', { level: 8, tone: 'N' }, '20'), 4)[0]);
  assert(lvl < 6.0, 'got ' + lvl);
});
t('demi never lightens (Shades EQ level 8 on level 4)', () => {
  const lvl = E.levelFromL(pig(resp('redken-eq', { level: 8, tone: 'N' }), 4)[0]);
  assert(Math.abs(lvl - 4) < 0.15, 'got ' + lvl);
});
t('demi level-on-level changes tone, not depth', () => {
  const R = resp('redken-eq', { level: 4, tone: 'C' });
  const o = pig(R, 4);
  assert(Math.abs(E.levelFromL(o[0]) - 4) < 0.3);
  assert(o[1] > 8, 'copper should push a* up, got ' + o[1]);
});
t('darker dye deepens brown hair', () => {
  const lvl = E.levelFromL(pig(resp('wella-cc-perm', { level: 3, tone: 'N' }, '20'), 5)[0]);
  assert(lvl < 4, 'got ' + lvl);
});

console.log('gray coverage rules');
t('permanent 20 vol covers more gray than 10 vol', () => {
  assert(resp('wella-cc-perm', { level: 5, tone: 'N' }, '20').grayCov > resp('wella-cc-perm', { level: 5, tone: 'N' }, '10').grayCov + 0.2);
});
t('permanent covers more gray than demi', () => {
  assert(resp('wella-cc-perm', { level: 5, tone: 'N' }, '20').grayCov > resp('redken-eq', { level: 5, tone: 'N' }).grayCov + 0.3);
});
t('light shades (level 9) cover gray worse than level 5', () => {
  assert(resp('wella-cc-perm', { level: 5, tone: 'N' }, '20').grayCov > resp('wella-cc-perm', { level: 9, tone: 'N' }, '20').grayCov + 0.15);
});
t('natural tone covers better than ash', () => {
  assert(resp('wella-cc-perm', { level: 5, tone: 'N' }, '20').grayCov > resp('wella-cc-perm', { level: 5, tone: 'A' }, '20').grayCov);
});
t('coverage never exceeds ~98%', () => { assert(resp('wella-koleston', { level: 4, tone: 'NN' }, '6', 40, { band: 'high' }).grayCov <= 0.985); });

console.log('time');
t('20 vs 30 min is a modest difference (< 12%)', () => {
  const a = E.timeFactor(20, 20), b = E.timeFactor(30, 20);
  assert(b > a && b - a < 0.12, `${a} -> ${b}`);
});
t('half the time gives clearly less effect', () => { assert(E.timeFactor(10, 20) < 0.85); });

console.log('gray detection');
t('gray % slider is honoured (60% body / 90% edge)', () => {
  const w = 200, h = 200, n = w * h, L = new Float32Array(n), a = new Float32Array(n).fill(8), b = new Float32Array(n).fill(14);
  const alpha = new Float32Array(n).fill(1), edge = new Uint8Array(n);
  let s = 12345; const rnd = () => (s = (s * 1664525 + 1013904223) >>> 0) / 4294967296;
  for (let i = 0; i < n; i++) { L[i] = rnd() < 0.5 ? 20 + rnd() * 8 : 55 + rnd() * 20; if (i % w < 40) edge[i] = 1; }
  const r = E.grayWeights({ L, a, b, alpha, edge, pctBody: 0.6, pctEdge: 0.9 });
  let bodyG = 0, bodyN = 0, edgeG = 0, edgeN = 0;
  for (let i = 0; i < n; i++) { if (edge[i]) { edgeN++; if (r.g[i] > 0.5) edgeG++; } else { bodyN++; if (r.g[i] > 0.5) bodyG++; } }
  assert(Math.abs(bodyG / bodyN - 0.6) < 0.04, 'body ' + bodyG / bodyN);
  assert(Math.abs(edgeG / edgeN - 0.9) < 0.04, 'edge ' + edgeG / edgeN);
  assert(r.pigLevel < 4.5, 'pig level ' + r.pigLevel);
});

console.log('end-to-end render (synthetic 60% gray, level-4 brown hair)');
function synthetic(grayFrac) {
  const w = 120, h = 120, n = w * h, rgba = new Uint8ClampedArray(n * 4), L = new Float32Array(n), a = new Float32Array(n), b = new Float32Array(n);
  const alpha = new Float32Array(n).fill(1), lab = [0, 0, 0];
  let s = 99; const rnd = () => (s = (s * 1664525 + 1013904223) >>> 0) / 4294967296;
  for (let i = 0; i < n; i++) {
    const gray = rnd() < grayFrac; const rgb = gray ? [196 + rnd() * 30, 194 + rnd() * 30, 190 + rnd() * 30] : [58 + rnd() * 14, 40 + rnd() * 10, 32 + rnd() * 8];
    rgba[i * 4] = rgb[0]; rgba[i * 4 + 1] = rgb[1]; rgba[i * 4 + 2] = rgb[2]; rgba[i * 4 + 3] = 255;
    E.rgbToLab(rgb[0], rgb[1], rgb[2], lab); L[i] = lab[0]; a[i] = lab[1]; b[i] = lab[2];
  }
  const edge = new Uint8Array(n);
  const gw = E.grayWeights({ L, a, b, alpha, edge, pctBody: grayFrac, pctEdge: grayFrac });
  const loc = E.localPigMean({ L, a, b, alpha, g: gw.g, w, h }, 6);
  return { w, h, rgba, L, a, b, alpha, g: gw.g, loc, noise: E.valueNoise(w, h, 3, 7), grayRefL: gw.grayRefL, glob: { L: gw.pigL, a: 8, b: 14 }, gw };
}
const src = synthetic(0.6);
function meanOut(out, sel) { let r = 0, g = 0, b = 0, c = 0; for (let i = 0; i < src.w * src.h; i++) if (sel(i)) { r += out[i * 4]; g += out[i * 4 + 1]; b += out[i * 4 + 2]; c++; } return [r / c, g / c, b / c]; }
const lum = c => 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
t('photo detected as ~level 3-4 brown with ~60% gray', () => { assert(src.gw.pigLevel > 2.5 && src.gw.pigLevel < 5, 'level ' + src.gw.pigLevel); assert(Math.abs(src.gw.grayShare - 0.6) < 0.05); });
t('permanent 20 vol L5 N: previously-gray areas become brown (much darker than white)', () => {
  const out = E.render(src, resp('wella-cc-perm', { level: 5, tone: 'N' }, '20'));
  const gm = meanOut(out, i => src.g[i] > 0.9), gb = meanOut(src.rgba, i => src.g[i] > 0.9);
  assert(lum(gm) < lum(gb) * 0.6, `gray area lum ${lum(gm)} vs ${lum(gb)}`);
});
t('Shades EQ on the same hair leaves gray visibly lighter than permanent (sheer blend)', () => {
  const perm = E.render(src, resp('wella-cc-perm', { level: 5, tone: 'N' }, '20'));
  const eq = E.render(src, resp('redken-eq', { level: 5, tone: 'N' }));
  const sel = i => src.g[i] > 0.9;
  assert(lum(meanOut(eq, sel)) > lum(meanOut(perm, sel)) + 20);
});
t('10 vol permanent leaves more gray showing than 20 vol', () => {
  const o10 = E.render(src, resp('wella-cc-perm', { level: 5, tone: 'N' }, '10')), o20 = E.render(src, resp('wella-cc-perm', { level: 5, tone: 'N' }, '20'));
  const sel = i => src.g[i] > 0.9;
  assert(lum(meanOut(o10, sel)) > lum(meanOut(o20, sel)) + 8);
});
t('pixels outside the mask are untouched', () => {
  const s2 = Object.assign({}, src, { alpha: new Float32Array(src.w * src.h) });
  const out = E.render(s2, resp('wella-cc-perm', { level: 3, tone: 'N' }, '20'));
  for (let i = 0; i < out.length; i++) assert.strictEqual(out[i], src.rgba[i]);
});
t('Low/Expected/High bands are ordered for gray coverage', () => {
  const s = { level: 5, tone: 'N' };
  assert(resp('wella-cc-perm', s, '20', null, { band: 'low' }).grayCov < resp('wella-cc-perm', s, '20', null, { band: 'expected' }).grayCov);
  assert(resp('wella-cc-perm', s, '20', null, { band: 'expected' }).grayCov < resp('wella-cc-perm', s, '20', null, { band: 'high' }).grayCov);
});

console.log('data');
t('every line has a default developer and shades with level/tone', () => {
  D.LINES.forEach(l => { assert(l.devs.find(d => d.id === l.defaultDev), l.id); assert(l.shades.length > 5, l.id); l.shades.forEach(s => assert(s.level >= 1 && s.level <= 12 && s.tone && E.TONES[s.tone], l.id + ' ' + s.code + ' tone ' + s.tone)); });
});
t('Wella Color Charm verified list has all 52 entries (Sally page list minus the 050 additive)', () => { assert.strictEqual(line('wella-cc-perm').shades.length, 52); });
t('no developer from another brand is offered (names carry the line brand)', () => {
  assert(line('redken-eq').devs.every(d => /Shades EQ/.test(d.name)));
  assert(line('redken-fusion').devs.every(d => /Pro-Oxide/.test(d.name)));
  assert(line('wella-cc-perm').devs.every(d => /Color Charm/.test(d.name)));
});

console.log(`\n${pass} passed`);
