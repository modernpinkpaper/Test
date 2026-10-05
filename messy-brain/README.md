# Messy Brain, Tidy Home — automated digital business

One brand, three money paths, one engine:

| Path | How people find it | How you get paid | Runs by itself? |
|---|---|---|---|
| **A. Ebook via TikTok/Instagram** | Faceless photo carousels (2 a day) | Payhip sells *The Messy Brain Home Reset* ($9.99) | Slides are made for you; you schedule them ~10 min/week |
| **B. Printables via website + Pinterest** | Daily blog posts → RSS → Pinterest pins, plus Google search | Payhip sells *The Tidy Brain Printable Pack* ($14) and the bundle ($19) | Yes, 100% |
| **C. Amazon affiliate via Pinterest + Bluesky** | A new Amazon-find page + pin every day (ramps up), direct Amazon pins, Bluesky posts 5×/day | Amazon Associates commission | Yes; plus one 2-minute Pinterest upload a month |

To see which path wins: each path uses its own Amazon tracking ID (`config.json → amazon`), and each
product is its own Payhip listing.

## What runs on its own

| When | What | Where |
|---|---|---|
| Every day 7am ET | Site rebuilds; posts/finds whose date arrived go live; RSS feeds update → Pinterest auto-pins them | `.github/workflows/publish.yml` |
| 5× a day | One Amazon find or tip posted to Bluesky | `.github/workflows/bluesky.yml` |
| 1st of the month | Pinterest bulk-upload file for the month saved in `pinterest-uploads/` | `.github/workflows/pinterest-csv.yml` |
| Every Monday | Claude writes next week's posts, finds and carousels, checks them and pushes | Claude Routine (see `automation/WEEKLY_ROUTINE.md`) |
| Every sale | Payhip takes payment, emails the PDF instantly | Payhip |

### Posting volume (safe ramp, from `config.json → schedule`)

| | Week 1–2 | Week 3–4 | Month 2 | Month 3+ |
|---|---|---|---|---|
| Pinterest pins from RSS (auto) | 4/day | 7/day | 11/day | 16/day |
| Pinterest pins from monthly file | 4/day | 8/day | 12/day | 20/day |
| **Pinterest total** | **~8/day** | **~15/day** | **~23/day** | **~36/day** |
| Bluesky | 5/day | 5/day | 5/day | 5/day |
| TikTok + Instagram carousels | 2/day | 2/day | 2/day | 2–3/day |

New Pinterest accounts that post 100+ pins on day one get flagged as spam, so it starts slow and
ramps up. Once the account is 3+ months old and healthy, raise the numbers in `config.json`.

## Your one-time setup (about 1 hour total)

I can't create accounts for you. Every site needs a human to sign up, confirm an email or phone
number, and agree to its terms. Everything else is done. Use one email for all of them.

1. **GitHub site repo (1 min).** On github.com → New repository → name it exactly
   `modernpinkpaper.github.io` → Public → Create. Tell Claude, and Claude moves this folder into it.
   Then in that repo: Settings → Pages → Source: **GitHub Actions**.
2. **Payhip (10 min).** payhip.com → sign up (free plan). Connect PayPal and/or Stripe so you get paid.
   Add 3 products: upload `products/home-reset/The-Messy-Brain-Home-Reset.pdf` ($9.99),
   `products/printables/Tidy-Brain-Printable-Pack.pdf` ($14), and a bundle with both ($19). Use the
   `cover.png` images. Paste the 3 product links into `config.json → shop` (or send them to Claude).
3. **Amazon Associates (5 min, you already have it).** In Associates Central → Tools → Tracking ID
   Manager, add 4 IDs, for example `yourtag-site-20`, `yourtag-pin-20`, `yourtag-bsky-20`,
   `yourtag-social-20`. Put them in `config.json → amazon`. Under Account Settings → Websites and
   Mobile Apps, add the website, the Pinterest profile and the Bluesky profile (Amazon requires this).
4. **Pinterest (15 min).** Create a **business** account (pinterest.com/business/create), named
   "Messy Brain, Tidy Home". Claim the website: Settings → Claimed accounts → Claim → "Add HTML tag"
   → copy the code inside `content="..."` into `config.json → pinterest.domain_verify`, wait for
   the site to redeploy, then press Verify. Then Settings → Bulk create Pins → **Auto-publish** → add
   these 5 feeds, each to its board:
   - `https://modernpinkpaper.github.io/feeds/adhd-home-organization.xml` → ADHD Home Organization
   - `https://modernpinkpaper.github.io/feeds/amazon-home-finds.xml` → Amazon Home Finds
   - `https://modernpinkpaper.github.io/feeds/adhd-cleaning-tips.xml` → ADHD Cleaning Tips
   - `https://modernpinkpaper.github.io/feeds/small-space-organizing.xml` → Small Space Organizing
   - `https://modernpinkpaper.github.io/feeds/printable-cleaning-checklists.xml` → Printable Cleaning Checklists
5. **Bluesky (3 min).** Sign up at bsky.app as `messybraintidyhome`. Settings → Privacy and
   security → App passwords → Add. In the GitHub repo → Settings → Secrets and variables → Actions,
   add `BLUESKY_HANDLE` (for example `messybraintidyhome.bsky.social`) and `BLUESKY_APP_PASSWORD`.
6. **TikTok (5 min).** Sign up as `@messybraintidyhome`, then Settings → Account → **Switch to
   Business Account** (this gives you the bio link right away). Bio link:
   `https://modernpinkpaper.github.io/links/`
7. **Instagram (5 min).** Sign up as `@messybraintidyhome`, switch to a Professional (Creator)
   account, and use the same bio link. Link it to a Facebook Page in Meta Business Suite so you can
   schedule posts for free.

### Your weekly 10 minutes
Open `https://modernpinkpaper.github.io/studio/` (private, not linked anywhere) on your phone or
computer. Each carousel has its slides, a Copy caption button and a Download-all button. Schedule 2 a
day for the week: TikTok Studio (tiktok.com/tiktokstudio → Upload → Schedule) and Meta Business Suite
→ Planner for Instagram.

### Your monthly 2 minutes
On the 1st, open the repo's `pinterest-uploads/` folder, download the new CSV file(s), then on
Pinterest (desktop): Create → Create Pins in bulk → Upload .csv. The pins are already scheduled across
the month.

## Honest expectations
- Pinterest and Google usually take **1–3 months** to send steady traffic. TikTok can be fast if a
  carousel takes off, but that's not guaranteed.
- Amazon closes new Associates accounts with no 3 qualifying sales in 180 days. Your account
  already exists, so check its status in Associates Central.
- Costs: $0/month. Payhip keeps 5% of each sale plus PayPal/Stripe fees. Everything else is free.
- Customer messages should be rare: instant download, a help page at `/help/`, and "all sales final".

## Folder map
- `content/` — all words (posts, finds, carousels). Format rules: `content/FORMATS.md`
- `products/` — the ebook and printables (source + build scripts + PDFs)
- `site/` — website templates and pages
- `tools/` — scripts: `build_site.py`, `images.py`, `slides.py`, `pinterest_csv.py`, `bluesky.py`, `check.py`
- `state/` — what has already been posted/exported (kept by the automations)

Run locally: `pip install -r requirements.txt && python -m playwright install chromium && python tools/check.py && python tools/build_site.py`
