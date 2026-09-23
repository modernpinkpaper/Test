"""Build The Tidy Brain Printable Pack.

    python products/printables/build.py            # PDF + page PNGs + cover + previews
    python products/printables/build.py --pdf-only

Writes (next to this file):
    Tidy-Brain-Printable-Pack.pdf   the product (US Letter, one design per page)
    cover.png                       1600x2000 sales-page cover
    preview-1.png .. preview-3.png  1600x2000 flat-lay collages
    build/                          intermediate HTML + one PNG per page (for QA and mockups)

Fails loudly if any page's content overflows its box or the PDF page count
is not exactly one page per design.
"""
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]                       # messy-brain/
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(HERE))

from render import Renderer                  # noqa: E402
from content import ICONS, PAGES, TOC_ORDER  # noqa: E402

BUILD = HERE / "build"
PDF = HERE / "Tidy-Brain-Printable-Pack.pdf"
BRAND_CSS = ROOT / "assets" / "brand.css"


def env():
    e = Environment(loader=FileSystemLoader(str(HERE / "templates")), autoescape=False)
    e.globals["ICONS"] = ICONS
    return e


def context():
    cfg = json.loads((ROOT / "config.json").read_text())
    pn = {p["id"]: i + 1 for i, p in enumerate(PAGES)}
    groups = {g: [] for g in TOC_ORDER}
    for i, p in enumerate(PAGES):
        if p.get("toc"):
            groups[p["toc"]].append((p.get("toc_title") or p["title"], i + 1))
    return dict(
        pages=PAGES, pn=pn, total=len(PAGES),
        toc=[(g, items) for g, items in groups.items() if items],
        days=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
        site=cfg["site_url"].replace("https://", "").rstrip("/"), handle=cfg["handle"], year=date.today().year,
    )


def write_pack_html(e, ctx):
    BUILD.mkdir(exist_ok=True)
    out = BUILD / "pack.html"
    html = e.get_template("pack.html.j2").render(brand_css=os.path.relpath(BRAND_CSS, BUILD), **ctx)
    out.write_text(html)
    return out


def check_and_snap(r, html_path, snap=True):
    """Check every page for overflow and save a 2x PNG of each one."""
    page = r._browser.new_page(viewport={"width": 816, "height": 1056}, device_scale_factor=2)
    page.goto(html_path.resolve().as_uri())
    page.evaluate("document.fonts.ready")
    problems = page.evaluate("""() => {
      const out = [];
      document.querySelectorAll('section.page').forEach(s => {
        const r = s.getBoundingClientRect();
        if (Math.round(r.width) !== 816 || Math.round(r.height) !== 1056) out.push(`page ${s.dataset.n}: size ${r.width}x${r.height}`);
        const pb = s.querySelector('.pb');
        if (pb && pb.scrollHeight > pb.clientHeight + 1) out.push(`page ${s.dataset.n} (${s.dataset.id}): body overflows by ${pb.scrollHeight - pb.clientHeight}px`);
        // any element sticking out of the page or out of a clipping card
        const pr = pb ? pb.getBoundingClientRect() : r;
        s.querySelectorAll('.pb *').forEach(el => {
          const b = el.getBoundingClientRect();
          if (b.width && (b.bottom > pr.bottom + 1 || b.right > pr.right + 1))
            out.push(`page ${s.dataset.n} (${s.dataset.id}): <${el.tagName.toLowerCase()} class="${el.className.baseVal ?? el.className}"> outside margins`);
        });
      });
      return out;
    }""")
    if snap:
        (BUILD / "pages").mkdir(exist_ok=True)
        for i, el in enumerate(page.query_selector_all("section.page"), 1):
            el.screenshot(path=str(BUILD / "pages" / f"page-{i:02d}.png"))
    page.close()
    return problems


def pdf_page_count(path):
    data = Path(path).read_bytes()
    return len(re.findall(rb"/Type\s*/Page(?!s)", data))


def build_mockups(r, e, ctx):
    shots = {p["id"]: f"pages/page-{i:02d}.png" for i, p in enumerate(PAGES, 1)}
    jobs = [
        ("cover", "cover.html.j2", {}),
        ("preview-1", "preview.html.j2", dict(
            tag="Daily rhythm", title="Routines that don't <em>fight</em> your brain",
            sub="Daily 3, morning & evening resets, 15-minute emergency reset",
            cards=[("daily3", 80, 600, -4, 1), ("morning", 860, 570, 4, 2), ("emergency", 120, 1200, 3, 3), ("evening", 840, 1170, -3, 4)])),
        ("preview-2", "preview.html.j2", dict(
            tag="Room by room", title="Every room, one <em>small</em> step",
            sub="8 zone checklists, energy menus, monthly calendar, meal planning",
            cards=[("kitchen", 80, 600, -4, 1), ("low", 860, 570, 5, 2), ("calendar", 120, 1200, 2, 3), ("mealplan", 840, 1170, -4, 4)])),
        ("preview-3", "preview.html.j2", dict(
            tag="Declutter & family", title="Declutter without the <em>overwhelm</em>",
            sub="5-bin decision flow, doom pile sorter, 30-day challenge, chore chart",
            cards=[("flowchart", 80, 600, -4, 1), ("challenge", 860, 570, 4, 2), ("doompile", 120, 1200, 3, 3), ("chores", 840, 1170, -3, 4)])),
    ]
    for name, tpl, extra in jobs:
        html = e.get_template(tpl).render(brand_css=os.path.relpath(BRAND_CSS, BUILD), shots=shots, **ctx, **extra)
        src = BUILD / f"{name}.html"
        src.write_text(html)
        r.png(src, HERE / f"{name}.png", 1600, 2000)
        print("wrote", HERE / f"{name}.png")


def main():
    e = env()
    ctx = context()
    html = write_pack_html(e, ctx)
    with Renderer() as r:
        problems = check_and_snap(r, html, snap="--pdf-only" not in sys.argv)
        r.pdf(html, PDF)
        count = pdf_page_count(PDF)
        if count != len(PAGES):
            problems.append(f"PDF has {count} pages, expected {len(PAGES)}")
        if "--pdf-only" not in sys.argv:
            build_mockups(r, e, ctx)
    print(f"wrote {PDF} ({count} pages, {PDF.stat().st_size // 1024} KB)")
    if problems:
        print("\nLAYOUT PROBLEMS:")
        for pr in problems:
            print("  -", pr)
        sys.exit(1)
    print("layout check: all pages fit on one page")


if __name__ == "__main__":
    main()
