# Content formats

Every piece of content is a plain JSON file. Scripts in `tools/` turn these files
into the website, the Pinterest pins, the Bluesky posts and the TikTok/Instagram
slides. The daily/weekly Claude tasks add new files in exactly these formats.

Brand: **Messy Brain, Tidy Home** — ADHD-friendly home organizing. Warm, funny,
zero shame, practical. Reader is usually a woman 25–45 with ADHD (diagnosed or
suspected), busy, overwhelmed by her house, tired of advice written for tidy people.

Voice rules
- Short sentences. Talk like a friend who has ADHD too ("we", "our brains").
- No shame words ("lazy", "should have", "just"). No medical claims or promises.
  Never say a product "treats" or "helps ADHD symptoms"; say it makes a task easier.
- Every tip must be doable in under 15 minutes or with low energy.
- Amazon: never write prices, star ratings, or "best seller" claims (they change and
  Amazon forbids stale prices). Never use Amazon's photos. Always disclose.
- No affiliate links inside the PDFs (Amazon forbids links in e-books). PDFs may point
  to the website's "tools" page instead.

## 1. Amazon finds — `content/finds.json`

One array of single products. Each becomes 1–2 direct Pinterest pins and Bluesky posts.

```json
{
  "id": "fridge-bins",                         // unique, kebab-case
  "name": "Clear stackable fridge bins",       // generic product name, no brand names
  "search": "clear stackable fridge organizer bins with handles",  // Amazon search words
  "category": "kitchen",                       // kitchen|laundry|bathroom|entryway|bedroom|closet|cleaning|paper|kids|time|desk|car
  "hook": "The fridge fix my ADHD brain needed", // pin headline, max 48 chars
  "why": "If you can't see it, it doesn't exist. Clear bins keep food in sight so it gets eaten, not forgotten.", // 1–2 sentences, max 170 chars
  "board": "Amazon Home Finds"                 // one of the boards in config.json
}
```

Link built by scripts: `https://www.amazon.com/s?k=<search>&tag=<tag>`.

## 2. Website posts — `content/posts/<date>-<slug>.json`

A post only goes live on the site (and into the RSS feed → Pinterest) when its
`date` is today or earlier. So future-dated posts drip out one by one on their own.

```json
{
  "slug": "adhd-laundry-system",                // unique, kebab-case, also the URL
  "date": "2026-09-25",                         // publish date YYYY-MM-DD
  "type": "finds",                              // "finds" (Amazon roundup) or "tips"
  "title": "The Laundry System for People Who Forget Laundry in the Washer",
  "description": "A 3-step ADHD-friendly laundry loop plus 6 Amazon finds that make it stick.", // max 155 chars (SEO + pin description)
  "board": "ADHD Cleaning Tips",
  "keywords": ["adhd laundry", "laundry routine", "laundry organization"],
  "intro": "Markdown. 2–4 short paragraphs. Relatable, then the promise.",
  "sections": [ { "heading": "Step 1: ...", "body": "Markdown" } ],
  "finds": [                                    // required for "finds", optional for "tips"
    { "name": "...", "search": "...", "why": "..." }
  ],
  "outro": "Markdown. Short wrap-up. May mention the printables pack or ebook.",
  "pins": [                                     // 3 different pin designs for this post
    { "title": "ADHD laundry system that actually works", "sub": "3 steps + 6 Amazon finds", "style": "list" },
    { "title": "Stop re-washing forgotten laundry", "sub": "The laundry loop for busy brains", "style": "bold" },
    { "title": "6 laundry finds for ADHD brains", "sub": "Amazon finds that make it easy", "style": "note" }
  ]
}
```

Pin `title` max 48 characters, `sub` max 44. Styles: `list`, `bold`, `note`.

## 3. TikTok / Instagram carousels — `content/carousels/<nnn>-<slug>.json`

```json
{
  "id": "001-doom-piles",
  "cta": "ebook",                               // ebook | printables | finds
  "slides": [
    { "kind": "hook",  "title": "Big scroll-stopping line", "sub": "optional small line" },
    { "kind": "point", "num": 1, "title": "Short point", "body": "1–3 short sentences." },
    { "kind": "list",  "title": "Heading", "items": ["short", "short", "short"] },
    { "kind": "quote", "title": "A line people want to screenshot or share" },
    { "kind": "cta",   "title": "Want the whole system?", "body": "It's in The Messy Brain Home Reset — link in bio." }
  ],
  "caption": "Caption text, 1–3 short lines, ends with a question to drive comments.",
  "hashtags": ["adhd", "adhdtiktok", "cleaningmotivation", "adhdhome"]
}
```

6–9 slides each. Hook slide title max 70 characters; point titles max 50;
point body max 180 characters; list items max 45 characters, max 6 items.
