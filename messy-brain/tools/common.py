"""Shared helpers: paths, config, content loading, links and the publishing schedule."""
import datetime as dt
import json
import os
import re
from pathlib import Path
from urllib.parse import quote_plus

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
BUILD = ROOT / "build"            # scratch output, never committed
SITE_OUT = BUILD / "site"         # what gets deployed to GitHub Pages
IMG_CACHE = BUILD / "img-cache"   # rendered pin images, reused between runs


def config():
    return json.loads((ROOT / "config.json").read_text())


def today():
    """The site's 'today' (US Eastern-ish: UTC minus 5h), so posts go live in the morning US time.
    Set SITE_TODAY=YYYY-MM-DD to preview the site as it will look on another day."""
    if os.environ.get("SITE_TODAY"):
        return dt.date.fromisoformat(os.environ["SITE_TODAY"])
    return (dt.datetime.utcnow() - dt.timedelta(hours=5)).date()


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def amazon_link(search, tag):
    base = config()["amazon"]["marketplace"].rstrip("/")
    return f"{base}/s?k={quote_plus(search)}&tag={tag}"


def load_posts():
    posts = []
    for f in sorted((CONTENT / "posts").glob("*.json")):
        p = json.loads(f.read_text())
        p["date"] = dt.date.fromisoformat(p["date"])
        p["url"] = f"/{p['slug']}/"
        posts.append(p)
    posts.sort(key=lambda p: (p["date"], p["slug"]))
    return posts


def load_finds():
    """Finds with a publish date: they drip out on a ramp so a new account grows safely."""
    path = CONTENT / "finds.json"
    finds = json.loads(path.read_text()) if path.exists() else []
    sched = config().get("schedule", {})
    start = dt.date.fromisoformat(sched.get("start", "2026-09-24"))
    ramp = sched.get("finds_per_day_ramp", [[0, 3], [14, 6], [30, 10], [60, 15]])
    day, used = 0, 0
    for f in finds:
        while used >= per_day(ramp, day):
            day, used = day + 1, 0
        f.setdefault("date", (start + dt.timedelta(days=day)).isoformat())
        used += 1
    for f in finds:
        f["date"] = dt.date.fromisoformat(f["date"]) if isinstance(f["date"], str) else f["date"]
        f["url"] = f"/finds/{f['id']}/"
    return finds


def per_day(ramp, day):
    n = ramp[0][1]
    for from_day, count in ramp:
        if day >= from_day:
            n = count
    return n


def live(items, on=None):
    on = on or today()
    return [i for i in items if i["date"] <= on]


def load_carousels():
    return [json.loads(f.read_text()) for f in sorted((CONTENT / "carousels").glob("*.json"))]
