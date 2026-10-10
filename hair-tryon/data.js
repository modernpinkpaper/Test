/* Hair Color Try-On — brand / line / developer / shade data.
 *
 * Every line has a `confidence` tag and `sources`. Facts came from web research on 2026-10-10:
 *   "checked"    = ratio / developer / time seen on the brand's own page or a retailer listing
 *   "partial"    = some facts seen, others assumed (see `assumed`)
 *   "unverified" = from general industry knowledge only; confirm on the box
 * Shade lists marked `shadesVerified:false` are a level x tone grid, NOT the brand's official chart.
 * The "Custom shade" box in the app lets you type any level + tone you read off a real box.
 */
(function (root) {
  'use strict';

  var LEVEL_NAMES = {
    1: 'Black', 2: 'Darkest Brown', 3: 'Dark Brown', 4: 'Medium Brown', 5: 'Light Brown',
    6: 'Dark Blonde', 7: 'Medium Blonde', 8: 'Light Blonde', 9: 'Very Light Blonde',
    10: 'Lightest Blonde', 11: 'High-Lift Blonde', 12: 'Ultra High-Lift Blonde'
  };

  var TONE_NAMES = {
    N: 'Natural', NN: 'Intense Natural', NB: 'Natural Brown', B: 'Brown', A: 'Ash', AA: 'Ultra Ash',
    AB: 'Ash Brown', G: 'Gold', NG: 'Natural Gold', GB: 'Gold Brown', W: 'Warm', NW: 'Natural Warm',
    WV: 'Warm Violet', WR: 'Warm Red', C: 'Copper', R: 'Red', RG: 'Red Gold', RV: 'Red Violet',
    V: 'Violet', BC: 'Brown Copper', P: 'Pearl'
  };

  // Shades that are real (names seen on retailer / brand pages) -> [code, name]
  var COLOR_CHARM_PERM = [
    '12A|Frosty Ash', '12AA|Nordic Blonde', '12C|Ultra Light Blonde', '10N|Satin Blonde', '10A|Palest Ash Blonde',
    '9NG|Sand Blonde', '9N|Very Light Blonde', '9A|Pale Ash Blonde', '9NN|Intense Very Light Blonde', '9G|Soft Pure Gold Blonde',
    '8NG|Light Beige Blonde', '8N|Light Blonde', '8A|Light Ash Blonde', '8NN|Intense Light Blonde', '8G|Light Golden Blonde',
    '7N|Medium Blonde', '7A|Medium Smokey Ash Blonde', '7NW|Medium Natural Warm Blonde', '7NN|Intense Medium Blonde',
    '7G|Sunlight Blonde Brown', '7W|Caramel', '7WR|Tan Blonde', '7WV|Nutmeg', '7R|Red', '8RG|Titian Red Blonde',
    '6R|Red Terra Cotta', '6RV|Cyclamen', '6RG|Light Copper', '6N|Dark Blonde', '6A|Dark Ash Blonde',
    '6NW|Dark Natural Warm Blonde', '6NN|Intense Dark Blonde', '5N|Light Brown', '5A|Light Ash Brown',
    '5NW|Light Natural Warm Brown', '5NN|Intense Light Brown', '5G|Light Golden Brown', '5WV|Cinnamon',
    '5RG|Light Auburn', '5RV|Burgundy', '4RG|Dark Auburn', '4R|Cinnamon Brown', '4N|Medium Brown', '4A|Medium Ash Brown',
    '4NW|Medium Natural Warm Brown', '4NN|Intense Medium Brown', '3NW|Dark Natural Warm Brown', '3N|Dark Brown',
    '3A|Dark Ash Brown', '3RV|Black Cherry', '2N|Very Dark Brown', '1N|Black'
  ];

  // Redken Shades EQ names seen on a retailer listing + Redken's "top 10" page (code format: 2-digit level + tone)
  var SHADES_EQ = [
    '03N|Espresso', '03NB|Mocha Java', '03RV|Merlot', '04N|Chicory', '04NB|Maple', '04ABn|Dark Roast',
    '05N|Walnut', '05NB|(code used by you; name not checked)', '05RV|Sangria', '06N|Moroccan Sand', '07N|Mirage'
  ];

  function parseCode(code) {
    var m = /^0?(\d{1,2})([A-Za-z]*)$/.exec(code);
    if (!m) return null;
    return { level: parseInt(m[1], 10), tone: m[2].toUpperCase().replace('ABN', 'AB') };
  }

  function fromList(list, prefix, verified) {
    return list.map(function (s) {
      var p = s.split('|'); var c = parseCode(p[0]);
      return { code: p[0], name: p[1], level: c.level, tone: c.tone, verified: verified, label: (prefix || '') + p[0] + ' ' + p[1] };
    });
  }

  // level x tone grid used where we do not have an official list
  function grid(levels, tones, codeFn) {
    var out = [];
    levels.forEach(function (lv) {
      tones.forEach(function (t) {
        var code = codeFn(lv, t);
        out.push({
          code: code, name: LEVEL_NAMES[lv] + ' ' + (TONE_NAMES[t] || t), level: lv, tone: t, verified: false,
          label: code + ' ' + LEVEL_NAMES[lv] + ' ' + (TONE_NAMES[t] || t)
        });
      });
    });
    return out;
  }

  var PERM_DEV = function (names, sourceNote) {
    // lift in LEVELS, cov = gray-coverage multiplier vs the line's best case.
    // 10 vol: "minimal lift", "won't give much gray coverage" (several sources).  20 vol: standard for gray, 1-2 levels.
    // 30/40: more lift; gray coverage no better than 20 (extra lift just shifts warm).
    return [
      { id: '10', name: names[0], vol: 10, lift: 0.5, cov: 0.62, note: 'Gentlest. Deposit-style: little lift, weaker gray coverage.' },
      { id: '20', name: names[1], vol: 20, lift: 1.5, cov: 1.0, note: 'Standard for gray coverage. About 1-2 levels of lift.' },
      { id: '30', name: names[2], vol: 30, lift: 2.5, cov: 1.0, note: 'More lift (2-3 levels). Not needed for gray.' },
      { id: '40', name: names[3], vol: 40, lift: 3.5, cov: 1.0, note: 'Most lift (3-4 levels). Harder on hair.' }
    ];
  };

  var LINES = [
    /* ---------------------------------------------------------------- WELLA */
    {
      id: 'wella-cc-perm', brand: 'Wella', name: 'Color Charm Permanent Liquid', type: 'permanent',
      ratio: '1 color : 2 developer', minutes: { min: 30, max: 45, def: 35 }, grayMax: 0.93,
      devs: PERM_DEV(['Color Charm Cream Developer 10 vol', 'Color Charm Cream Developer 20 vol', 'Color Charm Cream Developer 30 vol', 'Color Charm Cream Developer 40 vol']),
      defaultDev: '20',
      confidence: 'checked',
      facts: [
        'Mix 1 part color to 2 parts developer (Sally Beauty product page).',
        'Sally page: "10 volume developer for same depth or darker. Offers minimal lift."',
        'Lighter-than-natural: develop 15 min, check, up to +15 more. Darker-than-natural: 30 min, check, up to +15 more (Sally page).',
        'Best gray coverage on level 8 or darker; lighter shades go translucent. Natural and Gold families cover best. Over 50% gray: mix a Red-family shade 1:1 with a Natural/Gold shade of the same level (Sally page).',
        'Retailer instructions: 50-100% gray = half your shade + half a Natural shade, 35-45 min without heat.'
      ],
      assumed: ['40 vol listing is the least confirmed of the four developers.'],
      sources: [
        { label: 'Sally Beauty — Color Charm Permanent Liquid', url: 'https://www.sallybeauty.com/wella-color-charm-permanent-liquid-hair-color/WELLA14.html' }
      ],
      shadesVerified: true,
      shades: fromList(COLOR_CHARM_PERM, '', true)
    },
    {
      id: 'wella-cc-demi', brand: 'Wella', name: 'Color Charm Demi-Permanent', type: 'demi',
      ratio: '1 color : 2 developer', minutes: { min: 20, max: 30, def: 20 }, grayMax: 0.38,
      devs: [{ id: '10', name: 'Color Charm Cream Developer 10 vol', vol: 10, lift: 0, cov: 1.0, note: 'The only developer this demi line is designed for. No lift.' }],
      defaultDev: '10',
      confidence: 'partial',
      facts: [
        "Wella's demi user guide: 1 part color to 2 parts 10 volume developer (found via search; the PDF itself could not be read).",
        'Demi color deposits and blends gray; it does not lift natural pigment.'
      ],
      assumed: ['Processing time (20 min) is an assumption — the guide text was not readable.', 'Gray blending (~38%) is a model estimate, not a Wella claim.', 'Official shade list not retrieved; a level/tone grid is used.'],
      sources: [{ label: 'Wella colorcharm Demi-Permanent User Guide (PDF)', url: 'https://wella.com/professional/m/pdf/Wella_colorcharm_Demi-Permanent_User_Guide.pdf' }],
      shadesVerified: false,
      shades: grid([3, 4, 5, 6, 7, 8, 9], ['N', 'A', 'G', 'C', 'R', 'V', 'BC'], function (lv, t) { return lv + t; })
    },
    {
      id: 'wella-koleston', brand: 'Wella', name: 'Koleston Perfect (professional permanent)', type: 'permanent',
      ratio: '1 color : 1 developer', minutes: { min: 30, max: 40, def: 35 }, grayMax: 0.97,
      devs: [
        { id: '6', name: 'Welloxon Perfect 6% (20 vol)', vol: 20, lift: 1.5, cov: 1.0, note: "Wella's recommended developer for gray coverage." },
        { id: '9', name: 'Welloxon Perfect 9% (30 vol)', vol: 30, lift: 2.5, cov: 1.0, note: 'More lift.' },
        { id: '3', name: 'Welloxon Perfect 3% (10 vol)', vol: 10, lift: 0.5, cov: 0.62, note: 'Gentler, little lift, weaker gray coverage.' }
      ],
      defaultDev: '6', confidence: 'checked',
      facts: [
        "Wella's blog: 1:1 with Welloxon Perfect Creme Developer 6% (20 vol); up to 100% gray coverage; 30-40 min without heat, 15-25 min with heat.",
        'Wella says include the gray-coverage (natural) family in the formula for proper saturation.'
      ],
      assumed: ['3% and 9% developers are standard Welloxon strengths, not confirmed in this research.', 'Shade list is a level/tone grid.'],
      sources: [{ label: 'Wella Pro — five tips for gray coverage', url: 'https://us.wella.professionalstore.com/en-US/blog/hair-color/trouble-with-gray-coverage-five-professional-tips' }],
      shadesVerified: false,
      shades: grid([3, 4, 5, 6, 7, 8], ['N', 'NN', 'A', 'G', 'C', 'R', 'V', 'BC'], function (lv, t) { return lv + '/' + t; })
    },

    /* --------------------------------------------------------------- REDKEN */
    {
      id: 'redken-eq', brand: 'Redken', name: 'Shades EQ Gloss (demi)', type: 'demi',
      ratio: '1 color : 1 Processing Solution', minutes: { min: 20, max: 40, def: 20 }, grayMax: 0.4,
      devs: [{ id: 'ps', name: 'Shades EQ Processing Solution (only)', vol: 0, lift: 0, cov: 1.0, note: 'Redken: mix only with Shades EQ Processing Solution (or Gloss-to-Gel solution). No lift.' }],
      defaultDev: 'ps', confidence: 'checked',
      facts: [
        "Redken Pro: Shades EQ Gloss is 1:1, mixed only with Shades EQ Processing Solution; 20 minutes; for subtle gray blending with no lift.",
        "Redken's own guidance: heavier or more consistent gray points to Shades ALK (up to 75% gray, up to 1 level lift) — not Shades EQ.",
        'Going slightly darker gives better tone saturation and more opaque gray coverage; lighter adds brightness but covers less (Redken FAQ).',
        'Retailer pages: ideal for blending ~50% gray; up to ~75% claimed on some retailer pages (not from Redken).',
        'Chart text: resistant gray — 15 min under a pre-heated dryer with a cap, then cool 5 min.',
        "Shades EQ works best on hair at or lighter than the shade's level (it cannot lighten)."
      ],
      assumed: ['The model uses ~40% gray coverage for Shades EQ — a blend, not cover. Your 60-90% gray will look sheer/blended with this line.'],
      sources: [
        { label: 'Redken Pro — how to cover gray', url: 'https://www.redkenpro.com/the-break-room/haircolor-techniques/how-to-cover-gray-hair-tips' },
        { label: 'Redken Pro — top 10 Shades EQ shades', url: 'https://www.redkenpro.com/the-break-room/haircolor-techniques/the-top-10-shades-eq-shades-and-how-to-use-them' },
        { label: 'Shades EQ mini chart (SlideShare)', url: 'https://www.slideshare.net/CMoran2/shades-eq-gloss-mini-shade-chartpdf' }
      ],
      shadesVerified: false, // only 10 names verified; rest is a grid
      shades: fromList(SHADES_EQ, '', true).concat(
        grid([3, 4, 5, 6, 7, 8, 9], ['N', 'NB', 'AB', 'GB', 'RV', 'BC'], function (lv, t) { return (lv < 10 ? '0' : '') + lv + t; })
          .filter(function (g) { return !SHADES_EQ.some(function (s) { return s.split('|')[0].toUpperCase() === g.code.toUpperCase(); }); })
      )
    },
    {
      id: 'redken-fusion', brand: 'Redken', name: 'Color Fusion (permanent)', type: 'permanent',
      ratio: '1 color : 1 developer', minutes: { min: 35, max: 45, def: 35 }, grayMax: 0.93,
      devs: PERM_DEV(['Pro-Oxide Cream Developer 10 vol', 'Pro-Oxide Cream Developer 20 vol', 'Pro-Oxide Cream Developer 30 vol', 'Pro-Oxide Cream Developer 40 vol']),
      defaultDev: '20', confidence: 'checked',
      facts: [
        'Redken Pro: Color Fusion mixes 1:1 with Pro-Oxide Cream Developer 10, 20, 30 or 40 vol.',
        'Redken: no other developer may be substituted for Pro-Oxide.',
        '20 vol page: process 35-45 minutes at room temperature.'
      ],
      assumed: ['Shade list is a level/tone grid; Redken uses its own codes.'],
      sources: [{ label: 'Redken Pro — Pro-Oxide 20 vol', url: 'https://www.redkenpro.com/products/haircolor/pro-oxide-developer-20-volume' }],
      shadesVerified: false,
      shades: grid([3, 4, 5, 6, 7, 8], ['N', 'A', 'G', 'C', 'R', 'V', 'BC'], function (lv, t) { return lv + t; })
    },

    /* -------------------------------------------------------------- MATRIX */
    {
      id: 'matrix-socolor', brand: 'Matrix', name: 'SoColor (permanent)', type: 'permanent',
      ratio: '1 color : 1 developer', minutes: { min: 35, max: 45, def: 45 }, grayMax: 0.93,
      devs: PERM_DEV(['Matrix Cream Developer 10 vol', 'Matrix Cream Developer 20 vol', 'Matrix Cream Developer 30 vol', 'Matrix Cream Developer 40 vol']),
      defaultDev: '20', confidence: 'checked',
      facts: [
        'Extra Coverage line (e.g. 5G, 8BC): 1:1 with Matrix Cream Developer 20 vol, 45 minutes; for over 50% gray.',
        'Blended collection: 1:1 with 10/20/30/40 vol, 35-45 minutes.',
        'BC = Brown Copper family (the "5BC" you mentioned) — confirm the exact name on the box.'
      ],
      assumed: ['Shade list is a level/tone grid, not the official chart.'],
      sources: [
        { label: 'Sally Beauty UK — SoColor Extra Coverage 508BC', url: 'https://www.sallybeauty.co.uk/matrix-socolor-pre-bonded-permanent-hair-colour%2C-extra-coverage---508bc-90ml/814665.html' }
      ],
      shadesVerified: false,
      shades: grid([3, 4, 5, 6, 7, 8, 9], ['N', 'A', 'G', 'C', 'R', 'V', 'BC'], function (lv, t) { return lv + t; })
    },
    {
      id: 'matrix-sync', brand: 'Matrix', name: 'SoColor Sync (demi / toner)', type: 'demi',
      ratio: '1 color : 1 developer', minutes: { min: 5, max: 20, def: 20 }, grayMax: 0.3,
      devs: [{ id: '10', name: 'Matrix Cream Developer 10 vol', vol: 10, lift: 0, cov: 1.0, note: 'Sync is mixed with 10 vol. No lift (about half a level possible).' }],
      defaultDev: '10', confidence: 'partial',
      facts: [
        'Sources: 1:1 with 10 vol; about 20 minutes at room temperature; tone-on-tone, possible half-level shift.',
        'Not marketed as a gray-coverage product.'
      ],
      assumed: ['One UK retailer says Sync was relaunched as "Super Sync" — details may have changed. Check the current Matrix guide.'],
      sources: [{ label: 'SalonCentric — SoColor Sync', url: 'https://www.saloncentric.com/matrix-socolor-sync-prebonded-alkaline-toner.html' }],
      shadesVerified: false,
      shades: grid([3, 4, 5, 6, 7, 8, 9], ['N', 'A', 'G', 'C', 'R', 'V', 'BC'], function (lv, t) { return lv + t; })
    },

    /* ----------------------------------------------------------- SCHWARZKOPF */
    {
      id: 'igora-royal', brand: 'Schwarzkopf', name: 'Igora Royal (permanent)', type: 'permanent',
      ratio: '1 color : 1 developer', minutes: { min: 30, max: 45, def: 35 }, grayMax: 0.95,
      devs: PERM_DEV(['Igora Royal Developer 3% (10 vol)', 'Igora Royal Developer 6% (20 vol)', 'Igora Royal Developer 9% (30 vol)', 'Igora Royal Developer 12% (40 vol)']),
      defaultDev: '20', confidence: 'checked',
      facts: ['1:1 mix; 20 vol (6%) developer for gray coverage; 30-45 min; apply to dry hair for best gray coverage.'],
      assumed: ['Shade list is a level/tone grid.'],
      sources: [{ label: 'Cosmetic World — how to mix Igora Royal', url: 'https://cosmeticworld.ca/blogs/tutorials/how-to-mix-schwarzkopf-igora-royal' }],
      shadesVerified: false,
      shades: grid([3, 4, 5, 6, 7, 8], ['N', 'A', 'G', 'C', 'R', 'V', 'BC'], function (lv, t) { return lv + '-' + t; })
    },
    {
      id: 'igora-vibrance', brand: 'Schwarzkopf', name: 'Igora Vibrance (demi)', type: 'demi',
      ratio: '1 color : 1 activator', minutes: { min: 5, max: 20, def: 20 }, grayMax: 0.45,
      devs: [{ id: '19', name: 'Igora Vibrance Activator 1.9% (6 vol)', vol: 6, lift: 0, cov: 1.0, note: 'Designed activator for the Vibrance line. No lift.' }],
      defaultDev: '19', confidence: 'checked',
      facts: ["Schwarzkopf's technical manual: 1:1 for all shades with 1.9% (6 vol) activator; white blending up to 70% on Natural-Extra, up to 50% on Natural and Fashion shades."],
      assumed: ['Development time range is from one retailer listing.'],
      sources: [{ label: 'Igora Vibrance technical manual', url: 'https://dm.henkel-dam.com/is/content/henkel/ENGLISH_IGORA_Vibrance_0124_TechnicalManual' }],
      shadesVerified: false,
      shades: grid([3, 4, 5, 6, 7, 8, 9], ['N', 'A', 'G', 'C', 'R', 'V', 'BC'], function (lv, t) { return lv + '-' + t; })
    },

    /* --------------------------------------------------------- OTHER (SALLY) */
    {
      id: 'clairol-soy4plex', brand: 'Clairol Professional', name: 'Soy4Plex LiquiColor (permanent)', type: 'permanent',
      ratio: '1 color : 1 developer', minutes: { min: 30, max: 45, def: 35 }, grayMax: 0.93,
      devs: PERM_DEV(['Clairol Professional Developer 10 vol', 'Clairol Professional Developer 20 vol', 'Clairol Professional Developer 30 vol', 'Clairol Professional Developer 40 vol']),
      defaultDev: '20', confidence: 'partial',
      facts: ['Retailer listings: 2 oz color + 2 oz Clairol Professional Developer (1:1). High-lift blondes use 1:2 with 40 vol.', 'Clairol guidance (via search): more than 30% gray needs at least 20 vol.'],
      assumed: ['Processing time (30-45 min) is an assumption; check the box.'],
      sources: [{ label: 'Beauty Plus Salon — Soy4Plex listing', url: 'https://www.beautyplussalon.com/clairol-soy4plex-6n-dark-neutral-blonde-liquicolor-permanent-hair-color' }],
      shadesVerified: false,
      shades: grid([3, 4, 5, 6, 7, 8], ['N', 'A', 'G', 'R', 'V'], function (lv, t) { return lv + t; })
    },
    {
      id: 'ion-brilliance', brand: 'ion', name: 'Color Brilliance Permanent Creme', type: 'permanent',
      ratio: '1 color : 1 developer', minutes: { min: 25, max: 45, def: 35 }, grayMax: 0.93,
      devs: PERM_DEV(['ion Creme Developer 10 vol', 'ion Creme Developer 20 vol', 'ion Creme Developer 30 vol', 'ion Creme Developer 40 vol']),
      defaultDev: '20', confidence: 'checked',
      facts: ['Sally Beauty listings: 1:1 with ion Sensitive Scalp Creme Developer; 25-45 min; claims 100% gray coverage (manufacturer claim). High-lift shades are 1:2.'],
      assumed: ['Developer strength options are assumed standard 10/20/30/40.'],
      sources: [{ label: 'Sally Beauty — ion Color Brilliance', url: 'https://www.sallybeauty.com/hair/hair-color/permanent-hair-color/permanent-creme-hair-color/ION87.html' }],
      shadesVerified: false,
      shades: grid([3, 4, 5, 6, 7, 8], ['N', 'NN', 'A', 'G', 'C', 'R', 'V'], function (lv, t) { return lv + t; })
    }
  ];

  root.HTData = { LINES: LINES, LEVEL_NAMES: LEVEL_NAMES, TONE_NAMES: TONE_NAMES };
  if (typeof module !== 'undefined' && module.exports) module.exports = root.HTData;
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));
