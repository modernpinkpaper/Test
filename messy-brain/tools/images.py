"""Render Pinterest pin images (1000x1500 PNG) for posts and finds.

Each image's file name is a hash of its design + text, so re-running only renders
what is new or changed. Images land in build/img-cache/ and the site build copies
the ones it needs.

    python tools/images.py            # render everything live today + the next 35 days
"""
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

sys.path.insert(0, str(Path(__file__).parent))
import common  # noqa: E402

COLORS = ["coral", "sage", "lilac", "butter"]
KICKERS = {"finds": "Amazon home finds", "tips": "ADHD home tips"}
_env = Environment(loader=FileSystemLoader(str(Path(__file__).parent / "templates")), autoescape=True)


def _color(key, offset=0):
    return COLORS[(int(hashlib.md5(key.encode()).hexdigest(), 16) + offset) % len(COLORS)]


def post_pin_specs(post):
    """Three designs per post (from the post's own 'pins' list)."""
    items = [f["name"] for f in post.get("finds", [])] or [s["heading"] for s in post.get("sections", [])]
    specs = []
    for i, pin in enumerate(post.get("pins", [])[:3]):
        specs.append({
            "style": pin.get("style", "list"), "title": pin["title"], "sub": pin.get("sub", ""),
            "items": [_short(x) for x in items], "kicker": KICKERS.get(post["type"], "ADHD home"),
            "color": _color(post["slug"], i), "ad": post["type"] == "finds",
            "key": f"post-{post['slug']}-{i}",
        })
    return specs


def find_pin_specs(find):
    """Two designs per find: one links to our site page, one straight to Amazon."""
    kicker = find.get("category", "home").replace("-", " ")
    base = {"title": find["hook"], "name": find["name"], "why": find["why"], "kicker": kicker, "ad": True}
    return [
        dict(base, style="find", color=_color(find["id"]), key=f"find-{find['id']}-0"),
        dict(base, style="findnote", color=_color(find["id"], 1), kicker=f"{kicker} fix", key=f"find-{find['id']}-1"),
    ]


def _short(text, n=34):
    return text if len(text) <= n else text[: n - 1].rsplit(" ", 1)[0] + "…"


def image_name(spec):
    digest = hashlib.sha1(json.dumps(spec, sort_keys=True).encode()).hexdigest()[:10]
    return f"{spec['key']}-{digest}.png"


def render_specs(specs):
    """Render any spec whose PNG is not in the cache yet. Returns {key: filename}."""
    from render import Renderer

    common.IMG_CACHE.mkdir(parents=True, exist_ok=True)
    tmp = common.BUILD / "tmp-html"
    tmp.mkdir(parents=True, exist_ok=True)
    domain = common.config()["site_url"].split("//", 1)[-1]
    todo = [s for s in specs if not (common.IMG_CACHE / image_name(s)).exists()]
    if todo:
        tpl = _env.get_template("pin.html")
        with Renderer() as r:
            for n, spec in enumerate(todo, 1):
                html = tmp / f"{spec['key']}.html"
                html.write_text(tpl.render(assets=(common.ROOT / "assets").as_uri(), domain=domain, **spec))
                r.png(html, common.IMG_CACHE / image_name(spec), 1000, 1500)
                if n % 25 == 0:
                    print(f"  rendered {n}/{len(todo)} pins")
    print(f"pins: {len(specs)} needed, {len(todo)} newly rendered")
    return {s["key"]: image_name(s) for s in specs}


def all_specs(horizon_days=35):
    until = common.today() + dt.timedelta(days=horizon_days)
    specs = []
    for p in common.live(common.load_posts(), until):
        specs += post_pin_specs(p)
    for f in common.live(common.load_finds(), until):
        specs += find_pin_specs(f)
    return specs


if __name__ == "__main__":
    render_specs(all_specs())
