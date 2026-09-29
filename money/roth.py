"""Money explainer: "Roth IRA or Traditional IRA?" (1080x1920, ~90 s).

    python money/roth.py out.mp4

One graphic per line (money/roth_lines.py). Reveals are timed to the spoken words (Whisper word timestamps), each
with a pop / ding / ka-ching. A cheat sheet at the bottom fills in as she explains, so the last frame is the whole
lesson (made to be saved). The chibi girl slides up for the hook, "the part nobody tells you" and the outro.
The camera slowly pushes in on every line and punches in on the big moments.
"""
import json
import hashlib
import math
import os
import subprocess
import sys
import tempfile

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import treats as T                              # noqa: E402  (fonts, easing, background, chibi, voices)
from roth_lines import LINES, VOICE             # noqa: E402

voices, V = T.voices, T.V
W, H, FPS, SR = T.W, T.H, T.FPS, T.SR
INK, GREEN, GOLD, PINK, CREAM, MUTED = T.INK, T.GREEN, T.GOLD, T.PINK, T.CREAM, T.MUTED
BLUE, GREY = (52, 98, 196), (120, 112, 100)
font, pop, ease = T.font, T.pop, T.ease

# words in each line that trigger a reveal (first spoken word starting with this text, after the previous trigger)
TRIGGERS = {
    "hook": ["roth", "traditional", "tipping", "thirty"],
    "one": ["now", "later"],
    "trad": ["break", "cute", "retire", "hand"],
    "roth": ["now", "later", "growth"],
    "secret": ["same", "exactly"],
    "math": ["10", "grows", "tax", "later", "keep", "either"],
    "question": ["higher", "later"],
    "roth_win": ["young", "starting", "big", "roth", "lowest"],
    "trad_win": ["most", "less", "traditional", "bracket"],
    "perks": ["take", "penalty", "growth", "forces"],
    "catch": ["earn", "150", "straight"],
    "limit": ["7500", "total"],
    "outro": ["split", "follow"],
}
CHIBI = {"hook", "secret", "outro"}
PUNCH = {"hook": 2, "math": 5, "catch": 1}              # trigger index that gets a camera punch-in
CHEAT = [   # (appears with line, trigger index, text, colour)
    ("roth", 0, "ROTH: pay tax now, tax-free later", GREEN),
    ("trad", 0, "TRAD: tax break now, taxed later", BLUE),
    ("secret", 1, "Same tax rate = same money", GOLD),
    ("roth_win", 4, "Lower tax rate now? ROTH", GREEN),
    ("trad_win", 3, "Higher tax rate now? TRAD", BLUE),
    ("perks", 0, "Roth: take out what you put in, anytime", GREEN),
    ("limit", 0, "$7,500/yr total across both (2026)", INK),
]
CHEAT_ORDER = [c[0] for c in CHEAT]


# ------------------------------------------------------------------ words + timeline + audio
_wm = None


def words_of(path):
    """Whisper word timestamps for one line (cached next to the voice cache)."""
    global _wm
    key = hashlib.md5(open(path, "rb").read()).hexdigest()
    cache = os.path.join(voices.CACHE, f"words_{key}.json")
    if not os.path.exists(cache):
        if _wm is None:
            from faster_whisper import WhisperModel
            _wm = WhisperModel("small", device="cpu", compute_type="int8")
        segs, _ = _wm.transcribe(path, word_timestamps=True)
        json.dump([(w.word.strip(), w.start, w.end) for s in segs for w in s.words], open(cache, "w"))
    return json.load(open(cache))


def clean(w):
    return "".join(ch for ch in w.lower() if ch.isalnum())


def build():
    t, plan = 0.35, []
    voice = np.zeros(int(150 * SR), np.float32)
    tmp = tempfile.mkdtemp()
    for k, (key, line) in enumerate(LINES):
        a = voices.say(VOICE, line)
        tone, text = voices.split_tag(line)
        p = os.path.join(tmp, f"{k}.wav")
        sf.write(p, a, SR)
        ws = words_of(p)
        cues = [(t + s, c) for s, c in V.mouth_cues(p, text)]
        dur = len(a) / SR
        trig, i = [], 0
        for want in TRIGGERS.get(key, []):
            j = next((n for n in range(i, len(ws)) if clean(ws[n][0]).startswith(want)), None)
            if j is None:                                   # not heard: spread evenly as a fallback
                print(f"  trigger '{want}' not found in {key}: {[w for w, _, _ in ws]}")
                trig.append(t + dur * (len(trig) + 1) / (len(TRIGGERS[key]) + 1))
            else:
                trig.append(t + ws[j][1])
                i = j + 1
        voice[int(t * SR):int(t * SR) + len(a)] += a
        plan.append(dict(key=key, tone=tone, text=text, t0=t, t1=t + dur, cues=cues, trig=trig,
                         words=[(w, t + s) for w, s, _ in ws]))
        t += dur + 0.18
    total = t + 2.2
    voice = voices.clarity(voice[:int(total * SR)])
    fx = np.zeros_like(voice)
    tt = lambda n: np.arange(int(n * SR)) / SR
    rng = np.random.default_rng(7)

    def add(x, at):
        i = max(0, int(at * SR))
        fx[i:i + len(x)] += x[:max(0, len(fx) - i)].astype(np.float32)

    def whoosh(n=.4, v=.18):
        s = rng.normal(0, 1, len(tt(n))) * np.sin(np.pi * tt(n) / n) ** 2
        return np.convolve(s, np.ones(30) / 30, "same") * v

    def blip(f0=620, f1=940, n=.09, v=.12):
        x = tt(n)
        return np.sin(2 * np.pi * (f0 + (f1 - f0) * x / n) * x) * np.exp(-x / .035) * v

    def ding(v=.08):
        x = tt(.35)
        return (np.sin(2 * np.pi * 1568 * x) + .5 * np.sin(2 * np.pi * 2352 * x)) * np.exp(-x / .12) * v

    def kaching(v=.14):
        x = tt(.5)
        c = (np.sin(2 * np.pi * 2093 * x) + .6 * np.sin(2 * np.pi * 2637 * x)) * np.exp(-x / .18) * v
        c[:200] += rng.normal(0, .3, 200) * np.exp(-np.arange(200) / 40)
        return c

    def thud(v=.45):
        return np.sin(2 * np.pi * 60 * tt(.6)) * np.exp(-tt(.6) / .18) * v

    for p in plan:
        add(whoosh(), p["t0"] - .3)
        for n, at in enumerate(p["trig"]):
            key = p["key"]
            if key in ("roth_win", "trad_win", "perks") and n < len(p["trig"]) - 1:
                add(ding(), at)
            elif PUNCH.get(key) == n:
                add(thud() if key != "math" else kaching(), at)
            else:
                add(blip(), at)
    mix = voice + fx
    return plan, (mix / max(np.abs(mix).max(), 1e-6) * .95).astype(np.float32), total


# ------------------------------------------------------------------ drawing helpers
def fit(text, size, width, bold=True):
    f = font(size, bold)
    while f.getlength(text) > width and size > 12:
        size -= 2
        f = font(size, bold)
    return f


def since(p, n, t):
    """Seconds since trigger n of line p (negative before it)."""
    return t - p["trig"][n] if n < len(p["trig"]) else -1


def check(d, x, y, s, col, ok=True):
    d.ellipse((x - s, y - s, x + s, y + s), fill=col)
    if ok:
        d.line((x - s * .45, y + s * .02, x - s * .1, y + s * .4, x + s * .5, y - s * .4), fill=CREAM, width=int(s * .28),
               joint="curve")
    else:
        for sx in (1, -1):
            d.line((x - s * .38 * sx, y - s * .38, x + s * .38 * sx, y + s * .38), fill=CREAM, width=int(s * .28))


def popt(d, xy, text, size, fill, k, bold=True, anchor="mm"):
    if k > .02:
        d.text(xy, text, font=font(size * k + 1, bold), fill=fill, anchor=anchor)


def card(d, box, col, k=1.0, r=34, outline=None):
    if k <= .02:
        return
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    x0, x1 = cx - (cx - x0) * k, cx + (x1 - cx) * k
    y0, y1 = cy - (cy - y0) * k, cy + (y1 - cy) * k
    d.rounded_rectangle((x0, y0, x1, y1), r, fill=col, outline=outline, width=6 if outline else 0)


def title(d, text, col, t, p):
    k = pop(t - p["t0"] + .3)
    popt(d, (W / 2, 370), text, 64, col, k)


# ------------------------------------------------------------------ one graphic per line
def s_hook(d, t, p, im):
    popt(d, (W / 2, 420), "ROTH", 170, GREEN, pop(since(p, 0, t) + .1))
    popt(d, (W / 2, 545), "or", 70, GREY, pop(since(p, 1, t) + .1))
    popt(d, (W / 2, 670), "TRADITIONAL?", 118, BLUE, pop(since(p, 1, t)))
    k = pop(since(p, 2, t), .3)
    if k > .02:                                         # the "tip jar" stamp
        lay = Image.new("RGBA", (900, 230), (0, 0, 0, 0))
        dl = ImageDraw.Draw(lay)
        dl.rounded_rectangle((10, 10, 890, 220), 30, fill=PINK, outline=INK, width=8)
        dl.text((450, 85), "pick wrong =", font=font(54, False), fill=CREAM, anchor="mm")
        dl.text((450, 160), "TIPPING THE IRS", font=font(84), fill=CREAM, anchor="mm")
        lay = lay.rotate(-6, expand=True, resample=Image.BICUBIC)
        lay = lay.resize((max(1, int(lay.width * k)), max(1, int(lay.height * k))))
        im.alpha_composite(lay, (int(W / 2 - lay.width / 2), int(900 - lay.height / 2)))
    popt(d, (W / 2, 1080), "for 30 years.", 64, INK, pop(since(p, 3, t)))


def s_one(d, t, p, im):
    title(d, "The whole thing in 1 sentence:", INK, t, p)
    for n, (x, col, name, big) in enumerate(((290, GREEN, "ROTH", "NOW"), (790, BLUE, "TRADITIONAL", "LATER"))):
        k = pop(since(p, n, t))
        card(d, (x - 230, 480, x + 230, 1060), col, k)
        if k > .3:
            popt(d, (x, 580), "pay the tax", 46, CREAM, k, False)
            popt(d, (x, 720), big, 110 if big == "NOW" else 92, CREAM, k)
            d.line((x - 150, 830, x + 150, 830), fill=CREAM, width=4)
            popt(d, (x, 920), name, 58 if name == "ROTH" else 50, CREAM, k)


def timeline(d, t, p, name, col, rows, bar_cut):
    """A card with TODAY and RETIREMENT rows, and a money bar the IRS takes a slice of (or doesn't)."""
    title(d, name, col, t, p)
    card(d, (80, 450, W - 80, 1150), (255, 255, 255), 1, outline=col)
    for n, (label, text, ok) in enumerate(rows):
        k = pop(since(p, rows_trig(n, p), t))
        y = 560 + n * 170
        if k > .02:
            d.text((140, y - 40), label, font=font(34, False), fill=GREY, anchor="lm")
            check(d, 180, y + 30, 38 * k, GREEN if ok else PINK, ok)
            d.text((245, y + 30), text, font=fit(text, 50 * k + 1, 700), fill=INK, anchor="lm")
    kb = ease(since(p, len(rows) - 1, t) / .6)
    if kb > 0:                                              # the money at retirement
        x0, x1, y = 140, W - 140, 960
        d.text((x0, y - 45), "your money at retirement", font=font(34, False), fill=GREY, anchor="lm")
        d.rounded_rectangle((x0, y, x1, y + 110), 22, fill=GREEN)
        d.text((x0 + 30, y + 55), "YOURS", font=font(46), fill=CREAM, anchor="lm")
        if bar_cut:
            cut = x1 - (x1 - x0) * bar_cut * kb
            d.rounded_rectangle((cut, y, x1, y + 110), 22, fill=PINK)
            if kb > .6:
                d.text(((cut + x1) / 2, y + 55), "IRS", font=font(46), fill=CREAM, anchor="mm")
        elif kb > .6:
            d.text((x1 - 30, y + 55), "100%", font=font(46), fill=CREAM, anchor="rm")


def rows_trig(n, p):
    return {"trad": (0, 2), "roth": (0, 1)}[p["key"]][n]


def s_trad(d, t, p, im):
    timeline(d, t, p, "TRADITIONAL IRA", BLUE, [("TODAY", "tax break", True), ("RETIREMENT", "taxed", False)], .28)
    k = pop(since(p, 1, t))
    if k > .02 and since(p, 2, t) < 0:                      # "Cute."
        popt(d, (800, 560), "cute.", 60, PINK, k, False)


def s_roth(d, t, p, im):
    timeline(d, t, p, "ROTH IRA", GREEN, [("TODAY", "you pay the tax", False), ("RETIREMENT", "100% tax-free", True)], 0)
    popt(d, (W / 2, 1210), "(the growth too!)", 50, GREEN, pop(since(p, 2, t)))


def s_secret(d, t, p, im):
    popt(d, (W / 2, 380), "the part nobody tells you", 54, GREY, pop(t - p["t0"] + .3), False)
    card(d, (110, 460, W - 110, 660), INK, pop(since(p, 0, t)))
    popt(d, (W / 2, 560), "SAME TAX RATE", 88, CREAM, pop(since(p, 0, t)))
    popt(d, (W / 2, 745), "=", 130, GOLD, pop(since(p, 1, t) + .15))
    card(d, (110, 830, W - 110, 1030), GOLD, pop(since(p, 1, t)))
    popt(d, (W / 2, 930), "SAME MONEY", 96, INK, pop(since(p, 1, t)))


def s_math(d, t, p, im):
    popt(d, (W / 2, 350), "$10,000 · 22% tax rate · grows 8x", 44, GREY, pop(t - p["t0"] + .3), False)
    cols = ((290, BLUE, "TRADITIONAL", ["$10,000", "x8  →  $80,000", "tax 22%", "$62,400"]),
            (790, GREEN, "ROTH", ["$10,000", "tax 22%  →  $7,800", "x8", "$62,400"]))
    steps = [0, 1, 2, 4]                                # which trigger shows each step
    for x, col, name, rows in cols:
        card(d, (x - 235, 420, x + 235, 1060), (255, 255, 255), 1, outline=col)
        d.text((x, 490), name, font=font(46), fill=col, anchor="mm")
        for n, (txt, st) in enumerate(zip(rows, steps)):
            k = pop(since(p, st, t))
            y = 600 + n * 125
            last = n == len(rows) - 1
            if k > .02:
                if last:
                    d.rounded_rectangle((x - 200, y - 50, x + 200, y + 50), 24, fill=col)
                f = fit(txt, (64 if last else 44) * k + 1, 420)
                d.text((x, y), txt, font=f, fill=CREAM if last else INK, anchor="mm")
            if n < len(rows) - 1 and pop(since(p, steps[n + 1], t)) > .02:
                d.text((x, y + 62), "↓", font=font(34, False), fill=MUTED, anchor="mm")
    k = pop(since(p, 5, t), .4)
    if k > .02:
        d.ellipse((W / 2 - 70 * k, 960 - 70 * k, W / 2 + 70 * k, 960 + 70 * k), fill=GOLD, outline=INK, width=6)
        d.text((W / 2, 958), "=", font=font(110 * k + 1), fill=INK, anchor="mm")
    popt(d, (W / 2, 1140), "example · ~7%/yr for 30 years", 36, GREY, pop(since(p, 5, t)), False)


def s_question(d, t, p, im):
    title(d, "Your tax rate is higher...", INK, t, p)
    cx, cy = W / 2, 820
    ang = math.radians(12 * math.sin((t - p["t0"]) * 2.4))       # the see-saw can't decide
    ca, sa = math.cos(ang), math.sin(ang)
    L = 400
    d.polygon([(cx, cy), (cx - 70, cy + 150), (cx + 70, cy + 150)], fill=INK)
    d.line((cx - L * ca, cy - L * sa, cx + L * ca, cy + L * sa), fill=INK, width=22)
    for sgn, label, col, n in ((-1, "NOW", GREEN, 0), (1, "LATER", BLUE, 1)):
        bx, by = cx + sgn * (L - 80) * ca, cy + sgn * (L - 80) * sa - 90
        k = pop(since(p, n, t) + .2)
        card(d, (bx - 130, by - 70, bx + 130, by + 70), col, k)
        popt(d, (bx, by), label, 60, CREAM, k)
    popt(d, (W / 2, 560), "?", 140, PINK, pop(since(p, 1, t)))


def checklist(d, t, p, head, col, items, result):
    title(d, head, col, t, p)
    for n, txt in enumerate(items):
        k = pop(since(p, n, t))
        y = 500 + n * 150
        if k > .02:
            card(d, (90, y - 60, W - 90, y + 60), (255, 255, 255), 1, outline=col)
            check(d, 170, y, 40 * k, col)
            d.text((240, y), txt, font=fit(txt, 52, 720), fill=INK, anchor="lm")
    k = pop(since(p, len(items), t) if result[1] is None else since(p, result[1], t))
    card(d, (90, 960, W - 90, 1110), col, k)
    popt(d, (W / 2, 1035), result[0], 50, CREAM, k)


def s_roth_win(d, t, p, im):
    checklist(d, t, p, "ROTH if you're...", GREEN, ["young", "just starting out", "not making big money yet"],
              ("your tax rate is LOW now", 4))
    popt(d, (W / 2, 1180), "Roth is usually your girl", 44, GREEN, pop(since(p, 3, t)), False)


def s_trad_win(d, t, p, im):
    checklist(d, t, p, "TRADITIONAL if you're...", BLUE, ["earning the most you ever will", "expecting less in retirement"],
              ("take the break while your bracket is HIGH", 3))


def s_perks(d, t, p, im):
    checklist(d, t, p, "Bonus ROTH perks", GREEN, ["take out what you put in", "anytime, no penalty"],
              ("no forced withdrawals when you're old", 3))
    popt(d, (W / 2, 820), "(just not the growth)", 44, PINK, pop(since(p, 2, t)), False)


def s_catch(d, t, p, im):
    title(d, "THE CATCH", PINK, t, p)
    k = pop(since(p, 0, t))
    popt(d, (W / 2, 500), "if you earn too much...", 54, INK, k, False)
    k = pop(since(p, 1, t), .4)
    card(d, (120, 580, W - 120, 900), PINK, k)
    popt(d, (W / 2, 690), "$153K+", 140, CREAM, k)
    popt(d, (W / 2, 830), "single  ·  $242K+ married", 46, CREAM, k, False)
    k = pop(since(p, 2, t))
    popt(d, (W / 2, 990), "no putting money straight", 50, INK, k)
    popt(d, (W / 2, 1060), "into a Roth", 50, INK, k)
    popt(d, (W / 2, 1150), "2026 limits · income phase-out starts here", 34, GREY, k, False)


def s_limit(d, t, p, im):
    title(d, "How much can you put in?", INK, t, p)
    k = ease(since(p, 0, t) / 1.1)
    if k > 0:
        card(d, (120, 470, W - 120, 800), GOLD, pop(since(p, 0, t)), outline=INK)
        d.text((W / 2, 620), f"${7500 * k:,.0f}", font=font(170), fill=INK, anchor="mm")
        d.text((W / 2, 740), "per year (2026)", font=font(44, False), fill=INK, anchor="mm")
    k = pop(since(p, 1, t))
    popt(d, (W / 2, 880), "TOTAL, across Roth + Traditional", 50, INK, k)
    popt(d, (W / 2, 960), "+$1,100 more if you're 50+", 44, GREEN, k, False)
    popt(d, (W / 2, 1060), "Traditional's tax break can shrink", 36, GREY, k, False)
    popt(d, (W / 2, 1105), "if you have a retirement plan at work", 36, GREY, k, False)


def s_outro(d, t, p, im):
    k = pop(since(p, 0, t), .4)
    if k > .02:
        r = 230 * k
        cx, cy = W / 2, 700
        d.pieslice((cx - r, cy - r, cx + r, cy + r), 90, 270, fill=GREEN)
        d.pieslice((cx - r, cy - r, cx + r, cy + r), -90, 90, fill=BLUE)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=INK, width=8)
        d.text((cx - r / 2, cy), "ROTH", font=font(48 * k + 1), fill=CREAM, anchor="mm")
        d.text((cx + r / 2, cy), "TRAD", font=font(48 * k + 1), fill=CREAM, anchor="mm")
    popt(d, (W / 2, 400), "Can't pick?", 70, INK, pop(t - p["t0"] + .3))
    popt(d, (W / 2, 1010), "DO BOTH.", 110, PINK, pop(since(p, 0, t) - .3))


SCENES = {k[2:]: v for k, v in globals().items() if k.startswith("s_")}


def cheat_sheet(im, t, plan):
    by = {p["key"]: p for p in plan}
    rows = [(txt, col) for key, n, txt, col in CHEAT if n < len(by[key]["trig"]) and t >= by[key]["trig"][n]]
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((60, 1360, W - 60, 1840), 36, fill=INK)
    d.text((W / 2, 1410), "CHEAT SHEET  ·  screenshot this", font=font(34), fill=GOLD, anchor="mm")
    for n, (txt, col) in enumerate(rows):
        y = 1470 + n * 52
        c = col if col != INK else CREAM
        d.ellipse((100, y - 11, 122, y + 11), fill=c)
        d.text((140, y), txt, font=fit(txt, 36, 820, False), fill=CREAM, anchor="lm")


def header(im, t, plan):
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((60, 70, W - 60, 250), 30, fill=INK)
    d.text((W / 2, 135), "ROTH vs TRADITIONAL IRA", font=font(58), fill=CREAM, anchor="mm")
    d.text((W / 2, 205), "how to actually pick  ·  not financial advice", font=font(36, False), fill=GOLD, anchor="mm")


def captions(im, p, t):
    said = [i for i, (_, s) in enumerate(p["words"]) if s <= t]
    if not said:
        return
    c0 = said[-1] // 4 * 4
    chunk = [w for w, _ in p["words"][c0:c0 + 4]]
    n = said[-1] - c0 + 1
    size = 58
    f = font(size)
    total = sum(f.getlength(w.upper()) for w in chunk) + 20 * (len(chunk) - 1)
    if total > 980:
        f = font(int(size * 980 / total))
        total = sum(f.getlength(w.upper()) for w in chunk) + 20 * (len(chunk) - 1)
    d = ImageDraw.Draw(im)
    x = W / 2 - total / 2
    hot = ("roth", "traditional", "irs", "tax", "now", "later", "same", "free", "penalty", "catch", "both", "cartoon")
    for i, w in enumerate(chunk):
        wd = f.getlength(w.upper())
        if i < n:
            h = any(ch.isdigit() for ch in w) or clean(w) in hot
            d.text((x, 1265), w.upper(), font=f, fill=PINK if h else (255, 255, 255), anchor="lm", stroke_width=9,
                   stroke_fill=INK)
        x += wd + 20


def camera(frame, t, p):
    """Slow push-in over each line, plus a quick punch-in on the big moment."""
    z = 1 + .035 * ease((t - p["t0"]) / max(p["t1"] - p["t0"], 1))
    n = PUNCH.get(p["key"])
    if n is not None and n < len(p["trig"]):
        s = t - p["trig"][n]
        if 0 <= s < .5:
            z += .06 * math.sin(math.pi * s / .5)
    if z <= 1.001:
        return frame
    cx, cy = W / 2, 760                                       # push toward the graphic
    return frame.transform(frame.size, Image.AFFINE, (1 / z, 0, cx - cx / z, 0, 1 / z, cy - cy / z), Image.BICUBIC)


def render(out):
    plan, audio, total = build()
    bg = T.background()
    with tempfile.TemporaryDirectory() as d:
        wav = os.path.join(d, "a.wav")
        sf.write(wav, audio, SR)
        for fi in range(int(total * FPS)):
            t = fi / FPS
            p = max((x for x in plan if x["t0"] - .3 <= t), key=lambda x: x["t0"], default=plan[0])
            im = bg.copy()
            dr = ImageDraw.Draw(im)
            if p["key"] != "hook":
                header(im, t, plan)
            SCENES[p["key"]](dr, t, p, im)
            if p["key"] in CHIBI:
                k = ease((t - (p["t0"] - .35)) / .35)
                if p["key"] != "outro":
                    k *= 1 - ease((t - (p["t1"] + .1)) / .3)
                if k < 1:
                    cheat_sheet(im, t, plan)
                if k > .01:
                    ch = T.chibi_frame(p, t, None)
                    im.alpha_composite(ch, ((W - ch.width) // 2, int(H - ch.height + 90 + (1 - k) * 800)))
            else:
                cheat_sheet(im, t, plan)
            frame = camera(im.convert("RGB"), t, p)
            if p["t0"] - .05 <= t <= p["t1"] + .25:
                captions(frame, p, t)
            if t > plan[-1]["t1"] + .2:                                 # end card
                dd = ImageDraw.Draw(frame)
                k = pop(t - plan[-1]["t1"] - .2)
                dd.rounded_rectangle((110, 1140, W - 110, 1330), 30, fill=PINK)
                dd.text((W / 2, 1200), "Roth or Traditional?", font=font(62 * k + 1), fill=CREAM, anchor="mm")
                dd.text((W / 2, 1275), "tell me which one you picked ↓", font=font(40 * k + 1, False), fill=CREAM,
                        anchor="mm")
            frame.save(os.path.join(d, f"f{fi:04d}.png"))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(d, "f%04d.png"),
                        "-i", wav, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "19", "-c:a", "aac", "-b:a", "192k",
                        "-shortest", out], check=True)
    print("wrote", out, f"({total:.1f} s)")


if __name__ == "__main__":
    render(sys.argv[1] if len(sys.argv) > 1 else "roth.mp4")
