"""Render TikTok / Instagram carousel slides (1080x1350 PNG) plus a caption file.

Output: build/social/<carousel id>/slide-1.png ... and caption.txt
Only carousels that are not rendered yet are rendered.

    python tools/slides.py            # all carousels
    python tools/slides.py 001 002    # only these
"""
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

sys.path.insert(0, str(Path(__file__).parent))
import common  # noqa: E402
from render import Renderer  # noqa: E402

OUT = common.BUILD / "social"
COLORS = ["coral", "sage", "lilac", "butter"]
env = Environment(loader=FileSystemLoader(str(Path(__file__).parent / "templates")), autoescape=True)


def render_carousel(r, car, n):
    folder = OUT / car["id"]
    if (folder / "caption.txt").exists():
        return False
    folder.mkdir(parents=True, exist_ok=True)
    tmp = common.BUILD / "tmp-html"
    tmp.mkdir(parents=True, exist_ok=True)
    tpl = env.get_template("slide.html")
    color = COLORS[n % len(COLORS)]
    handle = common.config()["handle"]
    for i, slide in enumerate(car["slides"]):
        html = tmp / f"{car['id']}-{i}.html"
        html.write_text(tpl.render(assets=(common.ROOT / "assets").as_uri(), slide=slide, color=color,
                                   index=i, total=len(car["slides"]), handle=handle))
        r.png(html, folder / f"slide-{i + 1}.png", 1080, 1350)
    tags = " ".join("#" + t.lstrip("#") for t in car.get("hashtags", []))
    (folder / "caption.txt").write_text(f"{car['caption']}\n\n{tags}\n")
    return True


def main(only=None):
    cars = common.load_carousels()
    if only:
        cars = [c for c in cars if any(c["id"].startswith(o) for o in only)]
    done = 0
    with Renderer() as r:
        for n, car in enumerate(cars):
            done += render_carousel(r, car, n)
    print(f"slides: {done} carousels rendered -> {OUT}")


if __name__ == "__main__":
    main(sys.argv[1:])
