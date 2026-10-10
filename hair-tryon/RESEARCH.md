# Research notes (searched 2026-10-10)

How sure we are: **checked** = seen on the brand's own page or a retailer listing. **partial** = some seen, some assumed. Nothing here is lab data.

## Developers, ratios, times, gray claims

| Line | Developer(s) | Mix | Time | Gray | Confidence |
|---|---|---|---|---|---|
| Wella Color Charm Permanent Liquid | Color Charm Cream Developer 10 / 20 / 30 / 40 vol | 1 : 2 | 15+15 min lighter-than-natural, 30+15 darker-than-natural, 35–45 for 50–100% gray | Best on level 8 or darker; Natural/Gold cover best; over 50% gray add a Natural shade of the same level | checked (Sally page) |
| Wella Color Charm Demi-Permanent | 10 vol only | 1 : 2 | not found | blends gray | partial (guide PDF unreadable) |
| Wella Koleston Perfect | Welloxon Perfect 6% (20 vol) | 1 : 1 | 30–40 (15–25 with heat) | up to 100% claim | checked (Wella Pro blog) |
| Redken Shades EQ Gloss | Shades EQ Processing Solution **only** | 1 : 1 | 20 (resistant gray: 15 under heat + 5 cool) | subtle blending, no lift. Heavier gray → Redken points to Shades ALK (up to 75%) | checked (Redken Pro) |
| Redken Color Fusion | Pro-Oxide Cream 10 / 20 / 30 / 40 (no substitutes) | 1 : 1 | 35–45 | – | checked (Redken Pro) |
| Matrix SoColor (permanent) | Matrix Cream Developer | 1 : 1 | Extra Coverage: 20 vol, 45 min, >50% gray. Blended: 10–40 vol, 35–45 | – | checked (Sally UK) |
| Matrix SoColor Sync | 10 vol | 1 : 1 | ~20 | not a gray product; "Super Sync" relaunch may change this | partial |
| Schwarzkopf Igora Royal | Igora Royal developer, 6% (20 vol) for gray | 1 : 1 | 30–45 | – | checked |
| Schwarzkopf Igora Vibrance | 1.9% (6 vol) activator | 1 : 1 | 5–20 | white blending: up to 70% (Natural-Extra), 50% (others) | checked (technical manual) |
| Clairol Soy4Plex | Clairol Professional Developer | 1 : 1 | assumed 30–45 | >30% gray needs at least 20 vol | partial |
| ion Color Brilliance | ion Creme Developer | 1 : 1 | 25–45 | 100% claim | checked (Sally listings) |

## General rules used by the model

- **10 vol:** opens the cuticle only a little. "Minimal lift." Several sources say it does not cover gray well. (Red Seal study guide disagrees, so the model uses ~62% of normal coverage, not zero.)
- **20 vol:** the standard for gray, about 1–2 levels of lift.
- **Demi / gloss:** deposits only, never lifts. Patents say demi cannot effectively color mostly gray or white hair. One retailer says semi-permanent blends ~20% of gray.
- Going slightly **darker** than the target gives better gray coverage. Going lighter looks brighter but covers less (Redken).
- 50%+ gray: mixing a Natural shade into a fashion shade helps (Wella Color Charm).

## Shade lists

- **Verified:** all 52 Wella Color Charm Permanent shades on the Sally page (the 050 additive is left out). 10 Redken Shades EQ names (03N, 03NB, 03RV, 04N, 04NB, 04ABn, 05N, 05RV, 06N, 07N).
- **Not verified:** everything else is a level × tone grid. The "5BC" you mentioned could not be matched to an official Redken or Wella shade — **Matrix SoColor uses BC (Brown Copper)**, so it is under Matrix. Confirm against the box.

## Before / after photos — what I could and could not do

- I searched for before/after results on gray hair for Shades EQ, Wella and others. The searches only return **text pages** (retailer listings, brand guides, mirror sites). They did not return usable photo sets with known formulas.
- Even when a photo exists, it is someone's copyrighted work with unknown lighting, camera settings and starting hair, so it cannot be used as measured data. I did not download or bundle any.
- **What would work as real calibration data:**
  1. Your own: take a "before" photo in the same spot and light, color with a known formula, take an "after" photo, then use the *Teach it your hair* sliders until the preview matches.
  2. A shared set from your stylist or salon: same lighting, formula written on each photo.
  3. Brand shade books/charts photographed on gray swatches (Redken and Wella education sites sometimes publish them).
- A good next step is a small **calibration page** where you load a before and an after photo, enter the formula, and the app fits its numbers automatically. Not built yet.

## Your own history (from you, 2026-10-10)

Real data points to calibrate against. Results/timing/developer are still missing — see "what I need" below.

| Line | Shade | What you said |
|---|---|---|
| Redken Shades EQ (demi) | 04NB, 05NB, a little 04ABn, a little 05N | used before |
| Wella Color Charm Demi | 5N | used, "not in a while" |

Your photos show a very dark brown base (the app reads about level 2–2.5), heavy gray at the hairline, part and temples, and mostly dark lengths. Both product lines you used are demi (deposit only, no lift), so on your dark base they mostly add tone/shine and blend the gray.

**What would make these usable calibration points:** a before photo and an after photo in the same light, plus for each: the exact shade(s) and ratio, developer, minutes, and which part of the head (hairline vs lengths).

## Sources

- Wella Pro — gray coverage tips: https://us.wella.professionalstore.com/en-US/blog/hair-color/trouble-with-gray-coverage-five-professional-tips
- Sally Beauty — Color Charm Permanent Liquid: https://www.sallybeauty.com/wella-color-charm-permanent-liquid-hair-color/WELLA14.html
- Wella colorcharm Demi user guide: https://wella.com/professional/m/pdf/Wella_colorcharm_Demi-Permanent_User_Guide.pdf
- Redken Pro — covering gray: https://www.redkenpro.com/the-break-room/haircolor-techniques/how-to-cover-gray-hair-tips
- Redken Pro — Pro-Oxide 20 vol: https://www.redkenpro.com/products/haircolor/pro-oxide-developer-20-volume
- Shades EQ mini chart: https://www.slideshare.net/CMoran2/shades-eq-gloss-mini-shade-chartpdf
- Matrix SoColor Sync: https://www.saloncentric.com/matrix-socolor-sync-prebonded-alkaline-toner.html
- Igora Vibrance technical manual: https://dm.henkel-dam.com/is/content/henkel/ENGLISH_IGORA_Vibrance_0124_TechnicalManual
- Sally Beauty — ion Color Brilliance: https://www.sallybeauty.com/hair/hair-color/permanent-hair-color/permanent-creme-hair-color/ION87.html
