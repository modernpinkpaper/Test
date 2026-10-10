# Hair Color Try-On

Upload your photo, pick a brand, shade, developer and time, and see an **estimate** of the color on your own hair.
Your face and hairstyle are not changed — only the hair pixels get recolored, and your photo's own light and shadow stay.
Everything runs in your browser. The photo is never uploaded anywhere.

## How to run it

```
cd hair-tryon
python3 -m http.server 8000      # then open http://localhost:8000
```

Or build one file you can host anywhere: `node build-single.js` → `dist/hair-tryon.html`.
The first time you tap "Find my hair" it downloads a small hair-detection model (needs internet). If that fails, use **Fix hair outline** and paint your hair by hand.

Tests (no browser needed): `node test/engine.test.js`

## What you can do

- **Your hair:** set gray % for the main hair and a separate, higher gray % for the hairline and temples (defaults: 60% and 90%, like you described). Tick *show where it thinks my gray is* to check it.
- **Formula:** brand and line, shade (search by code or name), the brand's own developers only, and time on hair.
- **Low / Expected / High:** the "give or take" range.
- **Save this look** to compare formulas side by side.
- **Teach it your hair:** after you color for real, nudge *depth* and *gray coverage*. Saved on your device, applied to every formula.

## How the estimate works

Dye is see-through, so the result is *your hair + what the dye does to it*. Two kinds of strands are handled separately:

| Strand | What happens |
|---|---|
| Your brown | Developer **lifts** it a little (10 vol ≈ 0.5 level, 20 ≈ 1.5, 30 ≈ 2.5, 40 ≈ 3.5). Then the dye **deposits** depth and tone. Demi lines never lift. A shade lighter than your hair can reach barely shows on brown. |
| Gray | The dye **covers** a share of strands. Permanent + 20 vol ≈ 90%+. Permanent + 10 vol is much lower. Demi lines are a sheer blend (≈ 30–45%). Light shades (level 8+) and ash/violet tones cover less. Partial coverage = some strands take color, some stay sheer. |
| Time | Most color happens early. Going from 20 to 30 min only adds a few percent. |

The numbers come from the brands' published instructions plus general colorist rules. They are **not lab measurements.**

## Known limits (please read)

1. **Estimates only.** Porosity, past color, buildup, water, and your camera's lighting all change real results. Always do a strand test.
2. **Lighting matters.** Use even daylight, no filters. A warm or dark photo makes the app think your hair is darker or lighter. You can override the natural level.
3. **Gray detection is by brightness.** Light brown highlights can be mistaken for gray. Use the gray-map checkbox and the sliders to correct it.
4. **Shade lists:** only the Wella Color Charm Permanent list (52 shades) and 10 Redken Shades EQ names are checked against real pages. Other lines use a level × tone grid marked "approx." Use **My shade isn't listed** and type the level and tone from your box.
5. **No before/after photos are bundled.** See `RESEARCH.md` for why, and for how to get real calibration data.

See `RESEARCH.md` for every fact, its source, and how sure we are.
