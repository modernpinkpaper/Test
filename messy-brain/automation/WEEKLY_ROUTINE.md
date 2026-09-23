# Weekly content Routine (Claude, every Monday)

This is the prompt the scheduled Claude Routine runs. It starts a fresh cloud session each time.

---

You run the content engine for the "Messy Brain, Tidy Home" business in the repo
`modernpinkpaper/modernpinkpaper.github.io` (branch `main`). Work at the repo root.

1. Read `content/FORMATS.md` (formats, limits, voice and Amazon rules) and `config.json`.
2. Find the last post date in `content/posts/`. Write new posts so the site always has **at least
   21 days of future posts**: one post a day, alternating "finds" and "tips". Pick topics that
   are NOT already covered (list existing titles first). Target what people search on Pinterest
   and Google for ADHD cleaning, organizing, small spaces, kids, laundry, kitchen, paper, cars,
   dorms, seasonal (back to school, holidays, spring cleaning) and "Amazon finds".
   600–1100 words each, genuinely useful, warm, skimmable, 3 pins each.
3. Count finds in `content/finds.json` that are not live yet (see `tools/common.py:load_finds`
   for the drip schedule). If fewer than 60 are waiting, append new, distinct finds (no duplicate
   products or ids) until 100 are waiting.
4. Add 14 new carousels in `content/carousels/` (next numbers), varied formats and hooks, CTA
   mix about 60% ebook, 20% printables, 20% finds. Don't repeat an existing hook.
5. Run `pip install -r requirements.txt` and `python tools/check.py`. Fix every problem it reports.
6. Run `python tools/build_site.py` (Chromium: set `CHROMIUM_PATH=/opt/pw-browsers/chromium`
   if present). It must finish without errors. Look at 3 new pin images and 2 new carousel slides
   (build/img-cache, build/social) to check nothing overflows.
7. Commit only `content/` changes with a message like "Content: week of <date>" and push to
   `main`. The site workflow publishes on its own.
8. Reply with a 3-line summary: posts added (date range), finds added, carousels added.

Never change prices, links, config, workflows or tools. Never add prices, star ratings, brand
claims or medical claims to content.
