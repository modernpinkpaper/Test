"""Build "The Messy Brain Home Reset" ebook.

    python build.py            # PDF + cover.png + preview-1..3.png

Writes:
  The-Messy-Brain-Home-Reset.pdf   (US Letter)
  cover.png, preview-1.png .. preview-3.png  (1600 x 2000, for the sales page)
  build/*.html                     (intermediate HTML, safe to delete)

Content lives in content.md. Each "# Title" line starts a chapter, followed by a
<!--meta ... --> block (id, kind, color, kicker, tagline, one). Custom syntax:
  :::brain / :::try / :::min / :::one / :::script / :::note / :::win [label]  ... :::   -> callout boxes
  :::calendar  (one line per day)  :::                                                  -> 30-day grid
  - [ ] item                                                                            -> checkbox
  {{p:chapter-id}}                                                                      -> page number of that chapter
  ## Heading {.day} / {.sys} / {.printable}                                             -> starts a new page
Page numbers are found by rendering each chapter on its own and counting pages
(every chapter starts on a fresh page, so the counts add up exactly).
"""
import html
import os
import re
import sys
from pathlib import Path

import jinja2
import markdown

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from render import Renderer  # noqa: E402

BUILD = HERE / "build"
PDF_OUT = HERE / "The-Messy-Brain-Home-Reset.pdf"
TITLE = "The Messy Brain Home Reset"
SUBTITLE = "A shame-free, ADHD-friendly system to get your home under control in 7 days — and keep it there."

BOX_LABELS = {
    "brain": "Brain note", "try": "Try this now", "min": "Minimum version",
    "one": "If you only read one thing", "script": "Say it like this",
    "note": "Good to know", "win": "You did it",
}
FRONT_PAGES = 3  # cover, copyright, contents (each exactly one page)


# ---------------------------------------------------------------- parsing
def parse_chapters(text):
    chapters = []
    for block in re.split(r"(?m)^# ", text)[1:]:
        title, _, rest = block.partition("\n")
        meta = {}
        m = re.match(r"\s*<!--meta\n(.*?)-->", rest, re.S)
        if m:
            for line in m.group(1).strip().splitlines():
                k, _, v = line.partition(":")
                meta[k.strip()] = v.strip()
            rest = rest[m.end():]
        meta.setdefault("kind", "chapter")
        meta.setdefault("color", "lilac")
        chapters.append({"title": title.strip(), "meta": meta, "md": rest.strip() + "\n"})
    n = 0
    for ch in chapters:
        if ch["meta"]["kind"] == "chapter":
            n += 1
            ch["num"] = n
        else:
            ch["num"] = None
    return chapters


def md(text):
    return markdown.markdown(text, extensions=["tables", "attr_list", "md_in_html"], output_format="html5")


def inline_md(text):
    return re.sub(r"^<p>(.*)</p>$", r"\1", md(text).strip(), flags=re.S)


def preprocess(src):
    out, stack = [], []
    lines = src.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^:::(\w+)\s*(.*)$", line)
        if m and m.group(1) == "calendar":
            days = []
            i += 1
            while lines[i].strip() != ":::":
                if lines[i].strip():
                    days.append(lines[i].strip())
                i += 1
            out.append(calendar_html(days))
        elif m:
            kind, label = m.group(1), m.group(2).strip() or BOX_LABELS.get(m.group(1), "")
            out.append(f'<div class="box {kind}" markdown="1">\n<div class="box-label">{html.escape(label)}</div>\n')
            stack.append(kind)
        elif line.strip() == ":::" and stack:
            stack.pop()
            out.append("\n</div>\n")
        else:
            out.append(line)
        i += 1
    return "\n".join(out)


def calendar_html(days):
    groups = [(8, "g1", "The 7-Day Reset (+ kit day)"), (14, "g2", "Daily 3 + systems"),
              (21, "g3", "Declutter rounds"), (30, "g4", "Lock it in")]
    cells = []
    for idx, text in enumerate(days, start=1):
        g = next(cls for last, cls, _ in groups if idx <= last)
        cells.append(f'<div class="cal-day {g}"><span class="cal-n">{idx}</span>'
                     f'<span class="cal-t">{html.escape(text)}</span><span class="cb"></span></div>')
    key = "".join(f'<span><i class="cal-day {cls}"></i>Days {first}&ndash;{last}: {label}</span>'
                  for (last, cls, label), first in zip(groups, [1, 9, 15, 22]))
    return '<div class="cal">' + "".join(cells) + '</div>\n<div class="cal-key">' + key + "</div>"


def postprocess(h):
    # checkboxes
    h = re.sub(r"<li>\s*\[ \]\s*", '<li class="task"><span class="cb"></span>', h)
    h = re.sub(r"<ul>(\s*<li class=\"task\">)", r'<ul class="checklist">\1', h)
    h = re.sub(r'(<li class="task"><span class="cb"></span>)(.*?)</li>', r'\1<span class="tt">\2</span></li>', h, flags=re.S)
    # "Day 1: The Kitchen" -> label + title
    def split_heading(m):
        attrs, text = m.group(1), m.group(2)
        if re.match(r"(?:Day|System) \d+:", text):
            lab, rest = text.split(":", 1)
            text = f'<span class="h-lab">{lab}</span>{rest.strip()}'
        return f"<h2{attrs}>{text}</h2>"
    h = re.sub(r"<h2([^>]*)>(.*?)</h2>", split_heading, h, flags=re.S)
    # wrap page-starting sections (.day / .sys / .printable) so they can break + be extracted
    parts = re.split(r'(?=<h2 class="(?:day|sys|printable)")', h)
    if len(parts) > 1:
        body = [parts[0]]
        for p in parts[1:]:
            cls = re.match(r'<h2 class="(\w+)"', p).group(1)
            sid = re.search(r'id="([^"]+)"', p)
            sid = f' data-unit="{sid.group(1)}"' if sid else ""
            body.append(f'<section class="unit u-{cls}"{sid}>{p}</section>')
        h = "".join(body)
    # Day pages: minimum version (+ bonus) and the checklist sit side by side so each day fits one page.
    box = r'<div class="box (?:brain|try|min|note)">\s*<div class="box-label">.*?</div>.*?</div>'
    h = re.sub(r'((?:%s\s*)+)(<h3[^>]*>Day \d checklist</h3>\s*<ul class="checklist">.*?</ul>)' % box,
               r'<div class="day-foot"><div class="df-left">\1</div><div class="day-check">\2</div></div>', h, flags=re.S)
    return h


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", html.unescape(s).lower()).strip("-")


def render_chapters(chapters):
    for ch in chapters:
        body = postprocess(md(preprocess(ch["md"])))
        # h2 ids for sub-unit extraction
        body = re.sub(r"<section class=\"unit ([^\"]+)\"><h2([^>]*)>(.*?)</h2>",
                      lambda m: f'<section class="unit {m.group(1)}" data-unit="{slug(re.sub("<[^>]+>", " ", m.group(3)))}"><h2{m.group(2)}>{m.group(3)}</h2>',
                      body, flags=re.S)
        ch["html"] = body
        ch["sections"] = [re.sub(r"<[^>]+>", " ", s).replace("  ", " ").strip()
                          for s in re.findall(r"<h2[^>]*>(.*?)</h2>", body, re.S)]
        ch["sections"] = [re.sub(r"^((?:Day|System) \d+) ", r"\1: ", re.sub(r"\s+", " ", s)) for s in ch["sections"]]
        meta = ch["meta"]
        ch["one_html"] = inline_md(meta["one"]) if meta.get("one") else ""


def fill_pages(s, pages):
    return re.sub(r"\{\{p:([\w-]+)\}\}", lambda m: str(pages.get(m.group(1), "00")), s)


# ---------------------------------------------------------------- rendering
def unit_html(chapter_html, key):
    """One page-starting section (a Day, System or printable) out of a chapter, for the sales images."""
    m = re.search(r'<section class="unit[^"]*" data-unit="%s">.*?</section>' % re.escape(key), chapter_html, re.S)
    if not m:
        raise KeyError(key)
    return f'<section class="chapter-body">{m.group(0)}</section>'


def body_html(ch):
    t = env().from_string("{% import 'macros.html' as m %}{{ m.chapter_body(ch) }}")
    return t.render(ch=ch)


def env():
    e = jinja2.Environment(loader=jinja2.FileSystemLoader(str(HERE)), autoescape=False)
    e.filters["unit_html"] = unit_html
    e.filters["body"] = body_html
    return e


def css_href():
    return os.path.relpath(ROOT / "assets" / "brand.css", BUILD)


def book_html(chapters, pages, only=None, front=True):
    t = env().get_template("template.html")
    chs = chapters if only is None else [only]
    out = t.render(title=TITLE, subtitle=SUBTITLE, brand_css=css_href(), book_css="../book.css",
                   chapters=chs, all_chapters=chapters, pages=pages, front=front, mode="book")
    return fill_pages(out, pages)


def count_pages(pdf_path):
    return len(re.findall(rb"/Type\s*/Page\b", Path(pdf_path).read_bytes()))


def write_pdf(r, html_path, pdf_path):
    page = r._open(html_path)
    page.pdf(path=str(pdf_path), prefer_css_page_size=True, print_background=True, outline=True, tagged=True)
    page.close()


def main():
    BUILD.mkdir(exist_ok=True)
    chapters = parse_chapters((HERE / "content.md").read_text(encoding="utf-8"))
    render_chapters(chapters)

    with Renderer() as r:
        # Pass 1: measure each chapter on its own.
        pages, start = {}, FRONT_PAGES + 1
        for ch in chapters:
            tmp = BUILD / f"_measure-{ch['meta']['id']}.html"
            tmp.write_text(book_html(chapters, {}, only=ch, front=False), encoding="utf-8")
            write_pdf(r, tmp, BUILD / "_measure.pdf")
            n = count_pages(BUILD / "_measure.pdf")
            ch["page"], ch["pages"] = start, n
            pages[ch["meta"]["id"]] = start
            start += n
            tmp.unlink()
        (BUILD / "_measure.pdf").unlink()
        expected = start - 1

        # Pass 2: the whole book.
        book = BUILD / "book.html"
        book.write_text(book_html(chapters, pages), encoding="utf-8")
        write_pdf(r, book, PDF_OUT)
        total = count_pages(PDF_OUT)
        print(f"PDF: {PDF_OUT.name}  pages={total}  (expected {expected})")
        for ch in chapters:
            print(f"  p{ch['page']:>3}  +{ch['pages']:<2} {ch['title']}")
        if total != expected:
            print("WARNING: page count mismatch, contents page numbers may be off")

        # Sales images.
        t = env().get_template("promo.html")
        by_id = {c["meta"]["id"]: c for c in chapters}
        for name in ["cover", "preview-1", "preview-2", "preview-3"]:
            p = BUILD / f"{name}.html"
            p.write_text(fill_pages(t.render(which=name, title=TITLE, subtitle=SUBTITLE, brand_css=css_href(),
                                             book_css="../book.css", ch=by_id, all_chapters=chapters,
                                             pages=pages, mode="promo"), pages), encoding="utf-8")
            r.png(p, HERE / f"{name}.png", 1600, 2000)
            print("wrote", f"{name}.png")


if __name__ == "__main__":
    main()
