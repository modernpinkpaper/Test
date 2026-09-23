"""Turn HTML into PDF or PNG with headless Chromium (Playwright).

    python tools/render.py pdf  input.html  output.pdf
    python tools/render.py png  input.html  output.png  1000 1500

Other scripts import html_to_pdf / html_to_png / Renderer.
"""
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

# The cloud box ships Chromium here; elsewhere Playwright uses its own download.
_CHROMIUM = os.environ.get("CHROMIUM_PATH") or ("/opt/pw-browsers/chromium" if Path("/opt/pw-browsers/chromium").exists() else None)


class Renderer:
    """One browser for many renders (much faster than one browser per file)."""

    def __enter__(self):
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(executable_path=_CHROMIUM) if _CHROMIUM else self._pw.chromium.launch()
        return self

    def __exit__(self, *exc):
        self._browser.close()
        self._pw.stop()

    def _open(self, html_path, width=None, height=None):
        page = self._browser.new_page(viewport={"width": width or 1000, "height": height or 1000}, device_scale_factor=1)
        page.goto(Path(html_path).resolve().as_uri())
        page.evaluate("document.fonts.ready")
        return page

    def pdf(self, html_path, pdf_path):
        page = self._open(html_path)
        Path(pdf_path).parent.mkdir(parents=True, exist_ok=True)
        page.pdf(path=str(pdf_path), prefer_css_page_size=True, print_background=True)
        page.close()

    def png(self, html_path, png_path, width, height):
        page = self._open(html_path, width, height)
        Path(png_path).parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(png_path), clip={"x": 0, "y": 0, "width": width, "height": height})
        page.close()


def html_to_pdf(html_path, pdf_path):
    with Renderer() as r:
        r.pdf(html_path, pdf_path)


def html_to_png(html_path, png_path, width, height):
    with Renderer() as r:
        r.png(html_path, png_path, width, height)


if __name__ == "__main__":
    kind, src, out = sys.argv[1:4]
    if kind == "pdf":
        html_to_pdf(src, out)
    else:
        html_to_png(src, out, int(sys.argv[4]), int(sys.argv[5]))
    print("wrote", out)
