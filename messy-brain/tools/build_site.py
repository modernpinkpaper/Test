"""Build the whole website into build/site/ (deployed to GitHub Pages).

Only posts/finds dated today or earlier are published, so the site, the RSS feeds
(and therefore Pinterest) grow by themselves every day with no one touching them.

    python tools/build_site.py
"""
import datetime as dt
import json
import shutil
import sys
from collections import OrderedDict
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape

import markdown
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup

sys.path.insert(0, str(Path(__file__).parent))
import common  # noqa: E402
import images  # noqa: E402

SITE_SRC = common.ROOT / "site"
OUT = common.SITE_OUT
env = Environment(loader=FileSystemLoader(str(SITE_SRC / "templates")), autoescape=True)


def md(text):
    return Markup(markdown.markdown(text or "", extensions=["sane_lists"]))


def main():
    cfg = common.config()
    site = cfg["site_url"].rstrip("/")
    tags = cfg["amazon"]
    now = common.today()

    posts = list(reversed(common.live(common.load_posts(), now)))
    finds = list(reversed(common.live(common.load_finds(), now)))

    # ---- images (render only what is missing) ----
    # Also images for the next 35 days: the monthly Pinterest CSV points at them before their pages go live.
    names = images.render_specs(images.all_specs(35))

    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "pins").mkdir(parents=True)
    for name in names.values():
        shutil.copy(common.IMG_CACHE / name, OUT / "pins" / name)
    shutil.copytree(common.ROOT / "assets", OUT / "assets", dirs_exist_ok=True)
    shutil.copytree(SITE_SRC / "static", OUT, dirs_exist_ok=True)

    shop_img = OUT / "shop-img"
    shop_img.mkdir()
    has = {}
    previews = []
    for key, folder in (("ebook", "home-reset"), ("printables", "printables")):
        src = common.ROOT / "products" / folder
        if (src / "cover.png").exists():
            shutil.copy(src / "cover.png", shop_img / f"{key}-cover.png")
            has[key] = True
        for i in (1, 2, 3):
            if (src / f"preview-{i}.png").exists():
                shutil.copy(src / f"preview-{i}.png", shop_img / f"{key}-preview-{i}.png")
                previews.append(f"/shop-img/{key}-preview-{i}.png")

    # ---- enrich content for templates ----
    for p in posts:
        p["img"] = "/pins/" + names["post-%s-0" % p["slug"]] if p.get("pins") else ""
        p["intro_html"], p["outro_html"] = md(p.get("intro")), md(p.get("outro"))
        for s in p.get("sections", []):
            s["body_html"] = md(s["body"])
        for f in p.get("finds", []):
            f["link"] = common.amazon_link(f["search"], tags["tag_site"])
    for f in finds:
        f["img"] = "/pins/" + names["find-%s-0" % f["id"]]
        f["link"] = common.amazon_link(f["search"], tags["tag_site"])

    base = dict(cfg=cfg, site=site, has_ebook=has.get("ebook"), has_printables=has.get("printables"))
    pages = []  # (path, lastmod) for the sitemap

    def write(path, template, **ctx):
        target = OUT / path.strip("/") / "index.html" if path != "/" else OUT / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(env.get_template(template).render(path=path, **base, **ctx))
        if path != "/studio/":  # unlisted: keep it out of the sitemap
            pages.append((path, ctx.get("lastmod", now)))

    write("/", "index.html", page_title=f"{cfg['brand']} — ADHD-friendly home organizing",
          page_description=cfg["tagline"], posts=posts, finds=finds, og_image=posts[0]["img"] if posts else None)
    write("/blog/", "blog.html", page_title=f"Tips — {cfg['brand']}", page_description="ADHD-friendly cleaning and organizing tips.", posts=posts)

    for i, p in enumerate(posts):
        related = [q for q in posts if q is not p][:4]
        write(p["url"], "post.html", page_title=p["title"], page_description=p["description"], post=p,
              related=related, og_image=p["img"], og_type="article", loop_index=i, lastmod=p["date"])

    groups = OrderedDict()
    for f in sorted(finds, key=lambda f: f.get("category", "home")):
        groups.setdefault(f.get("category", "home"), []).append(f)
    write("/finds/", "finds.html", page_title=f"Amazon finds for ADHD homes — {cfg['brand']}",
          page_description="Amazon finds that make home tasks easier to see, start and finish.", groups=list(groups.items()))
    for f in finds:
        related = [g for g in groups[f.get("category", "home")] if g is not f][:4]
        write(f["url"], "find.html", page_title=f"{f['hook']} — {f['name']}", page_description=f["why"], find=f,
              related=related, og_image=f["img"], lastmod=f["date"])

    write("/shop/", "shop.html", page_title=f"Shop — {cfg['brand']}", page_description="The Messy Brain Home Reset ebook and the Tidy Brain Printable Pack.",
          previews=previews, og_image="/shop-img/ebook-cover.png" if has.get("ebook") else None)
    write("/links/", "links.html", page_title=cfg["brand"], page_description=cfg["tagline"])
    for mdfile in sorted((SITE_SRC / "pages").glob("*.md")):
        head, body = mdfile.read_text().split("---\n", 1)
        meta = dict(line.split(": ", 1) for line in head.strip().splitlines())
        write(f"/{mdfile.stem}/", "page.html", page_title=meta["title"], page_description=meta["description"], body=md(body))
    # /tools is the name the PDFs use for the finds page
    (OUT / "tools").mkdir(exist_ok=True)
    (OUT / "tools" / "index.html").write_text('<!doctype html><meta http-equiv="refresh" content="0; url=/finds/"><link rel="canonical" href="/finds/">')
    (OUT / "404.html").write_text((OUT / "links" / "index.html").read_text())

    write_studio(cfg, write)
    write_feeds(cfg, site, posts, finds)
    write_sitemap(site, pages)
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nDisallow: /studio/\nSitemap: {site}/sitemap.xml\n")
    (OUT / ".nojekyll").write_text("")
    print(f"site: {len(posts)} posts, {len(finds)} finds, {len(pages)} pages -> {OUT}")


def write_studio(cfg, write):
    """Unlisted page with the TikTok/Instagram carousels, ready to save on a phone and post."""
    import zipfile

    import slides

    slides.main()
    cars = common.load_carousels()
    per_day = cfg["schedule"].get("carousels_per_day", 2)
    start = dt.date.fromisoformat(cfg["schedule"]["start"])
    for n, c in enumerate(cars):
        src = slides.OUT / c["id"]
        dst = OUT / "studio" / c["id"]
        dst.mkdir(parents=True, exist_ok=True)
        pngs = sorted(src.glob("slide-*.png"), key=lambda f: int(f.stem.split("-")[1]))
        for f in pngs:
            shutil.copy(f, dst / f.name)
        with zipfile.ZipFile(dst / f"{c['id']}.zip", "w") as z:
            for f in pngs:
                z.write(f, f.name)
            z.write(src / "caption.txt", "caption.txt")
        c["images"] = [f"/studio/{c['id']}/{f.name}" for f in pngs]
        c["zip"] = f"/studio/{c['id']}/{c['id']}.zip"
        c["caption_text"] = (src / "caption.txt").read_text()
        c["suggested"] = (start + dt.timedelta(days=n // per_day)).strftime("%a %b %d")
    write("/studio/", "studio.html", page_title="Studio", page_description="Ready-to-post slides.", carousels=cars, per_day=per_day)


def rss_item(site, title, url, description, img, date):
    pub = format_datetime(dt.datetime.combine(date, dt.time(13, 0), tzinfo=dt.timezone.utc))
    full = f"{site}{url}"
    image = f"{site}{img}"
    desc = f'<img src="{escape(image)}" alt=""/><p>{escape(description)}</p>'
    return (f"<item><title>{escape(title)}</title><link>{escape(full)}</link><guid isPermaLink=\"true\">{escape(full)}</guid>"
            f"<pubDate>{pub}</pubDate><description>{escape(desc)}</description>"
            f"<enclosure url=\"{escape(image)}\" length=\"0\" type=\"image/png\"/>"
            f"<media:content url=\"{escape(image)}\" medium=\"image\" type=\"image/png\"/></item>")


def write_feeds(cfg, site, posts, finds):
    """feed.xml has everything; feeds/<board>.xml has one board each (Pinterest maps one feed to one board)."""
    items = []  # (board, date, xml)
    for p in posts:
        if p["img"]:
            items.append((p.get("board"), p["date"], rss_item(site, p["title"], p["url"], p["description"], p["img"], p["date"])))
    for f in finds:
        desc = f"{f['why']} #ad {f['name']} — Amazon find for ADHD-friendly homes."
        items.append((f.get("board", "Amazon Home Finds"), f["date"], rss_item(site, f["hook"], f["url"], desc, f["img"], f["date"])))
    items.sort(key=lambda x: x[1], reverse=True)

    def feed(title, chosen):
        body = "".join(x[2] for x in chosen[:100])
        return ('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">'
                f"<channel><title>{escape(title)}</title><link>{site}/</link><description>{escape(cfg['tagline'])}</description>"
                f"<language>en-us</language>{body}</channel></rss>\n")

    (OUT / "feed.xml").write_text(feed(cfg["brand"], items))
    (OUT / "feeds").mkdir(exist_ok=True)
    for board in cfg["pinterest"]["boards"]:
        chosen = [x for x in items if x[0] == board]
        (OUT / "feeds" / f"{common.slugify(board)}.xml").write_text(feed(f"{cfg['brand']} — {board}", chosen))


def write_sitemap(site, pages):
    urls = "".join(f"<url><loc>{site}{p}</loc><lastmod>{d.isoformat()}</lastmod></url>" for p, d in pages)
    (OUT / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n')


if __name__ == "__main__":
    main()
