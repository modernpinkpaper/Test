"""'A rainy morning': a 1-minute cozy ASMR cartoon (1080x1920, 30 fps) in a kawaii coloring-book look (thick dark
outlines, flat warm colors, closed happy eyes). Only real recorded sounds from the kept sound library (CC0); the
knife, egg cracks and other hits are timed to the actual sounds in the recordings.

    python asmr/cozy_morning.py LIB_DIR OUT.mp4        (LIB_DIR = the collected library: sounds/*.mp3 + library.json)
"""
import math
import os
import subprocess
import sys
import tempfile

import cairocffi as cairo
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS, SR = 1080, 1920, 30, 44100
FONT = os.path.join(HERE, "assets", "Fredoka-600.ttf")
OUT = (0.13, 0.09, 0.08)          # outline: warm near-black
LW = 7

C = dict(wall="#fdebc6", wall2="#f8dfb0", wood="#e9b46a", wood_d="#c98a45", mint="#9fd8c2", mint_d="#7cc2a8",
         floor="#e8953f", skin="#ffe3cc", blush="#ff9b9b", hair="#8a5232", hair_hi="#b06e44", sweater="#f4978e",
         sweater_d="#e07f76", apron="#fff3dd", sky="#9fbcd3", sky2="#d9e6ee", cat="#f6b26b", cat_d="#e08f45",
         cream="#fff8ec", yolk="#ffcc33", red="#e85d5d", jar1="#7fc8a9", jar2="#f7c873", jar3="#f29fb3", duck="#ffd84d")


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def lerp(a, b, k):
    return a + (b - a) * k


# ------------------------------------------------------------------ drawing helpers
def paint(ctx, fill=None, w=LW, line=OUT, alpha=1.0):
    if fill is not None:
        if isinstance(fill, str):
            r, g, b = rgb(fill)
            ctx.set_source_rgba(r, g, b, alpha)
        else:
            ctx.set_source(fill)
        ctx.fill_preserve()
    if w:
        ctx.set_source_rgb(*line)
        ctx.set_line_width(w)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.stroke()
    else:
        ctx.new_path()


def ell(ctx, x, y, rx, ry, fill=None, w=LW, rot=0.0, alpha=1.0):
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(rot)
    ctx.scale(max(rx, 0.01), max(ry, 0.01))
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()
    paint(ctx, fill, w, alpha=alpha)


def rr(ctx, x, y, w_, h_, r, fill=None, w=LW):
    r = min(r, w_ / 2, h_ / 2)
    ctx.new_sub_path()
    ctx.arc(x + w_ - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w_ - r, y + h_ - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h_ - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    ctx.close_path()
    paint(ctx, fill, w)


def poly(ctx, pts, fill=None, w=LW, close=True):
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    if close:
        ctx.close_path()
    paint(ctx, fill, w)


def line(ctx, pts, w=LW, col=None, alpha=1.0):
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.set_source_rgba(*(rgb(col) if col else OUT), alpha)
    ctx.set_line_width(w)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()


def arc_line(ctx, x, y, r, a0, a1, w=LW, col=None):
    ctx.new_sub_path()
    ctx.arc(x, y, r, a0, a1)
    ctx.set_source_rgb(*(rgb(col) if col else OUT))
    ctx.set_line_width(w)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()


def lin(x0, y0, x1, y1, stops):
    g = cairo.LinearGradient(x0, y0, x1, y1)
    for o, c in stops:
        g.add_color_stop_rgb(o, *rgb(c))
    return g


_face = None


def caption(ctx, s, x, y, size, alpha=1.0):
    global _face
    if _face is None:
        import ctypes  # noqa: F401  (cairocffi font loading below)
        from cairocffi import ToyFontFace  # noqa: F401
        _face = _load_font(FONT)
    ctx.save()
    ctx.set_font_face(_face)
    ctx.set_font_size(size)
    xb, yb, tw, th, _, _ = ctx.text_extents(s)
    ctx.move_to(x - tw / 2 - xb, y - yb - th / 2)
    ctx.text_path(s)
    ctx.set_source_rgba(*OUT, alpha)
    ctx.set_line_width(size * 0.16)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke_preserve()
    ctx.set_source_rgba(1, 0.98, 0.94, alpha)
    ctx.fill()
    ctx.restore()


def _load_font(path):
    sys.path.insert(0, os.path.join(HERE, "..", "skits"))
    from toon import font_face
    return font_face(path)[0]


# ------------------------------------------------------------------ rain outside a window
RNG = np.random.default_rng(5)
DROPS = RNG.uniform(0, 1, (90, 3))            # x, phase, length
BEADS = RNG.uniform(0, 1, (26, 3))            # drops on the glass


def window(ctx, x, y, w, h, t, night=False, rain=True):
    rr(ctx, x - 22, y - 22, w + 44, h + 44, 18, fill=C["wood"], w=LW)
    sky = [(0, "#1d2747"), (1, "#3a4a77")] if night else [(0, C["sky"]), (1, C["sky2"])]
    rr(ctx, x, y, w, h, 8, fill=lin(0, y, 0, y + h, sky), w=LW)
    ctx.save()
    ctx.rectangle(x, y, w, h)
    ctx.clip()
    if night:
        ell(ctx, x + w * 0.72, y + h * 0.25, 46, 46, fill="#fff3c4", w=0)
        ell(ctx, x + w * 0.72 + 20, y + h * 0.25 - 10, 40, 40, fill="#2a375f", w=0)
        for i in range(12):
            sx, sy = x + (i * 97) % w, y + (i * 53) % (h * 0.6)
            ell(ctx, sx, sy, 3, 3, fill="#fff8d0", w=0, alpha=0.5 + 0.5 * math.sin(t * 2 + i))
    else:
        for k, (bx, bh) in enumerate(((0.05, 0.35), (0.3, 0.5), (0.62, 0.3), (0.8, 0.45))):   # far hills / trees
            ell(ctx, x + w * bx + 60, y + h * 0.95, 140, h * bh, fill="#8fb39c", w=0, alpha=0.7)
        if rain:
            for dx, ph, ln in DROPS:
                yy = y + ((ph + t * 1.6) % 1) * (h + 80) - 40
                xx = x + dx * w + (yy - y) * 0.12
                line(ctx, [(xx, yy), (xx + 4, yy + 26 + 18 * ln)], w=3, col="#ffffff", alpha=0.55)
            for bx, by, bs in BEADS:                                          # drops sliding down the glass
                yy = y + ((by + t * 0.05 * (0.5 + bs)) % 1) * h
                ell(ctx, x + bx * w, yy, 5 + 4 * bs, 7 + 5 * bs, fill="#eaf4fb", w=2, alpha=0.8)
    ctx.restore()
    line(ctx, [(x + w / 2, y), (x + w / 2, y + h)], w=12, col=C["wood"])     # muntins
    line(ctx, [(x, y + h / 2), (x + w, y + h / 2)], w=12, col=C["wood"])
    line(ctx, [(x + w / 2, y), (x + w / 2, y + h)], w=3)
    line(ctx, [(x, y + h / 2), (x + w, y + h / 2)], w=3)


def curtain(ctx, x, y, w, t):
    """Cafe curtain across the top of a window: gingham with a scalloped hem, swaying a little."""
    s = 4 * math.sin(t * 1.2)
    ctx.move_to(x - 30, y - 30)
    ctx.line_to(x + w + 30, y - 30)
    ctx.line_to(x + w + 30, y + 90)
    n = 7
    for i in range(n, 0, -1):
        x0 = x - 30 + (w + 60) * i / n
        x1 = x - 30 + (w + 60) * (i - 1) / n
        ctx.curve_to(x0, y + 120 + s, x1, y + 120 + s, x1, y + 90)
    ctx.close_path()
    paint(ctx, "#f6b6b0", w=LW)
    for i in range(1, 9):
        line(ctx, [(x - 30 + (w + 60) * i / 9, y - 28), (x - 30 + (w + 60) * i / 9, y + 95)], w=6, col="#fbd5d1")


# ------------------------------------------------------------------ the girl
def ik(sx, sy, tx, ty, a, b):
    dx, dy = tx - sx, ty - sy
    d = max(abs(a - b) + 1, min(a + b - 1, math.hypot(dx, dy)))
    th = math.atan2(dy, dx)
    ph = math.acos(max(-1, min(1, (a * a + d * d - b * b) / (2 * a * d))))
    c1 = (sx + a * math.cos(th + ph), sy + a * math.sin(th + ph))
    c2 = (sx + a * math.cos(th - ph), sy + a * math.sin(th - ph))
    e = c1 if c1[1] > c2[1] else c2                        # elbows hang down
    hx, hy = sx + d * math.cos(th), sy + d * math.sin(th)
    return e, (hx, hy)


def arm(ctx, s, e, h, hand_prop=None):
    ctx.move_to(*s)
    ctx.line_to(*e)
    ctx.line_to(*h)
    ctx.set_source_rgb(*OUT)
    ctx.set_line_width(58)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()
    line(ctx, [s, e], w=44, col=C["sweater"])
    line(ctx, [e, h], w=40, col=C["sweater"])
    ell(ctx, h[0], h[1], 25, 23, fill=C["skin"], w=LW)
    if hand_prop:
        hand_prop(ctx, h[0], h[1])


def girl(ctx, x, y, t, hands=None, eyes="happy", mouth="smile", tilt=0.0, props=None, back_arms=False):
    """x, y = base of her neck. hands = {"left": (x, y) | None, "right": ...} world targets for her hands."""
    hands = hands or {}
    props = props or {}
    bob = 3 * math.sin(t * 2.1)
    y = y + bob
    sh = {"left": (x - 92, y + 46), "right": (x + 92, y + 46)}
    arms = {}
    for side in ("left", "right"):
        tgt = hands.get(side) or (sh[side][0] + (-30 if side == "left" else 30), sh[side][1] + 200)
        arms[side] = ik(*sh[side], *tgt, 125, 115)
    if back_arms:
        for side in ("left", "right"):
            arm(ctx, sh[side], *arms[side], props.get(side))
    # back hair (the bob)
    ctx.save()
    ctx.translate(x, y - 165)
    ctx.rotate(math.radians(tilt))
    rr(ctx, -205, -185, 410, 300, 150, fill=C["hair"], w=LW)
    ctx.restore()
    # body: sweater + apron
    ctx.move_to(x - 95, y + 30)
    ctx.curve_to(x - 120, y + 120, x - 135, y + 260, x - 140, y + 420)
    ctx.line_to(x + 140, y + 420)
    ctx.curve_to(x + 135, y + 260, x + 120, y + 120, x + 95, y + 30)
    ctx.curve_to(x + 40, y + 10, x - 40, y + 10, x - 95, y + 30)
    paint(ctx, C["sweater"])
    ctx.move_to(x - 70, y + 120)
    ctx.line_to(x + 70, y + 120)
    ctx.curve_to(x + 90, y + 260, x + 100, y + 340, x + 105, y + 420)
    ctx.line_to(x - 105, y + 420)
    ctx.curve_to(x - 100, y + 340, x - 90, y + 260, x - 70, y + 120)
    paint(ctx, C["apron"])
    line(ctx, [(x - 70, y + 120), (x - 95, y + 32)], w=10, col=C["apron"])
    line(ctx, [(x + 70, y + 120), (x + 95, y + 32)], w=10, col=C["apron"])
    rr(ctx, x - 34, y + 180, 68, 56, 12, fill=C["apron"], w=5)                       # pocket
    ctx.save()                                                                         # little heart on it
    ctx.translate(x, y + 206)
    ctx.scale(0.32, 0.32)
    ctx.move_to(0, 22)
    ctx.curve_to(-60, -20, -30, -60, 0, -28)
    ctx.curve_to(30, -60, 60, -20, 0, 22)
    ctx.restore()
    paint(ctx, C["red"], w=0)
    # head
    ctx.save()
    ctx.translate(x, y - 165)
    ctx.rotate(math.radians(tilt))
    ell(ctx, 0, 0, 168, 158, fill=C["skin"])
    # bangs
    ctx.new_sub_path()
    ctx.arc(0, 8, 176, math.pi * 1.02, math.pi * 1.98)
    pts = [(170, -30), (120, -62), (64, -40), (0, -70), (-64, -40), (-120, -62), (-170, -30)]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        ctx.curve_to(x0 - 10, y0 + 30, x1 + 10, y1 + 30, x1, y1)
    ctx.close_path()
    paint(ctx, C["hair"])
    for hx in (-90, 40):                                                              # hair shine
        arc_line(ctx, hx, -40, 90, math.pi * 1.32, math.pi * 1.5, w=7, col=C["hair_hi"])
    # side locks over the cheeks
    for sgn in (-1, 1):
        ctx.move_to(sgn * 160, -60)
        ctx.curve_to(sgn * 185, 20, sgn * 175, 90, sgn * 140, 140)
        ctx.curve_to(sgn * 150, 70, sgn * 140, 10, sgn * 120, -40)
        ctx.close_path()
        paint(ctx, C["hair"])
    # bow
    for sgn in (-1, 1):
        ell(ctx, 120 + sgn * 26, -150, 26, 18, fill=C["cream"], rot=sgn * 0.4)
    ell(ctx, 120, -150, 11, 11, fill=C["cream"])
    # face
    if eyes in ("happy", "sleep"):
        for ex in (-62, 62):
            arc_line(ctx, ex, 4 if eyes == "happy" else 10, 26, math.pi * 0.15, math.pi * 0.85, w=7)
            line(ctx, [(ex + (24 if ex > 0 else -24), 14), (ex + (32 if ex > 0 else -32), 6)], w=5)
    else:
        for ex in (-62, 62):
            ell(ctx, ex, 20, 17, 22, fill="#3a2418", w=0)
            ell(ctx, ex + 6, 12, 6, 7, fill="#ffffff", w=0)
    ell(ctx, -100, 62, 32, 19, fill=C["blush"], w=0, alpha=0.7)
    ell(ctx, 100, 62, 32, 19, fill=C["blush"], w=0, alpha=0.7)
    ell(ctx, 0, 50, 4, 3, fill="#e7a98b", w=0)
    if mouth == "o":
        ell(ctx, 0, 84, 10, 12, fill="#c9605a", w=5)
    elif mouth == "open":
        ctx.move_to(-20, 74)
        ctx.curve_to(-14, 104, 14, 104, 20, 74)
        ctx.close_path()
        paint(ctx, "#c9605a", w=5)
    else:
        arc_line(ctx, 0, 66, 18, math.pi * 0.2, math.pi * 0.8, w=6)
    ctx.restore()
    if not back_arms:
        for side in ("left", "right"):
            arm(ctx, sh[side], *arms[side], props.get(side))
    return {s: arms[s][1] for s in arms}


# ------------------------------------------------------------------ the cat and friends
def cat_sitting(ctx, x, y, t, s=1.0, purr=0.0):
    """Ginger cat sitting, base at (x, y), eyes closed, tail curling."""
    v = purr * 1.5 * math.sin(t * 60)
    ctx.save()
    ctx.translate(x + v, y)
    ctx.scale(s, s)
    sw = math.sin(t * 1.6)
    ctx.move_to(70, -20)                                                    # tail
    ctx.curve_to(150, -30, 150 + 20 * sw, -130, 110 + 30 * sw, -150)
    ctx.set_source_rgb(*OUT)
    ctx.set_line_width(36)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke_preserve()
    ctx.set_source_rgb(*rgb(C["cat"]))
    ctx.set_line_width(22)
    ctx.stroke()
    ell(ctx, 0, -80, 95, 85, fill=C["cat"])                                # body
    ell(ctx, 0, -60, 50, 55, fill=C["cream"], w=0)                          # chest
    for sx in (-35, 35):                                                    # paws
        ell(ctx, sx, -6, 28, 16, fill=C["cream"])
    ell(ctx, 0, -190, 82, 70, fill=C["cat"])                                # head
    for sg in (-1, 1):                                                      # ears
        poly(ctx, [(sg * 70, -220), (sg * 62, -290), (sg * 20, -250)], fill=C["cat"])
        poly(ctx, [(sg * 58, -232), (sg * 56, -268), (sg * 32, -248)], fill="#ffb3a7", w=0)
    for k in (-1, 0, 1):                                                    # stripes
        line(ctx, [(k * 22, -258), (k * 18, -232)], w=6, col=C["cat_d"])
    for ex in (-30, 30):
        arc_line(ctx, ex, -195, 14, math.pi * 0.15, math.pi * 0.85, w=6)
    ctx.move_to(-12, -168)                                                  # "w" mouth
    ctx.curve_to(-8, -158, -2, -158, 0, -166)
    ctx.curve_to(2, -158, 8, -158, 12, -168)
    ctx.set_source_rgb(*OUT)
    ctx.set_line_width(5)
    ctx.stroke()
    ell(ctx, 0, -175, 6, 4, fill="#ff9b9b", w=0)
    for sg in (-1, 1):                                                      # whiskers
        line(ctx, [(sg * 40, -170), (sg * 85, -176)], w=3)
        line(ctx, [(sg * 40, -162), (sg * 82, -156)], w=3)
    ctx.restore()


def cat_curled(ctx, x, y, t, s=1.0, purr=0.0):
    """Ginger cat curled up asleep, base at (x, y)."""
    v = purr * 1.2 * math.sin(t * 60)
    br = 1 + 0.03 * math.sin(t * 2.4)
    ctx.save()
    ctx.translate(x + v, y)
    ctx.scale(s, s * br)
    ell(ctx, 0, -55, 120, 60, fill=C["cat"])
    for k in (-1, 0, 1):
        arc_line(ctx, k * 40, -60, 50, math.pi * 1.2, math.pi * 1.45, w=6, col=C["cat_d"])
    ctx.move_to(-110, -20)                                                  # tail wrapped around
    ctx.curve_to(-60, 10, 60, 10, 100, -10)
    ctx.set_source_rgb(*OUT)
    ctx.set_line_width(34)
    ctx.stroke_preserve()
    ctx.set_source_rgb(*rgb(C["cat"]))
    ctx.set_line_width(20)
    ctx.stroke()
    ell(ctx, -95, -70, 58, 48, fill=C["cat"])                               # head
    for sg in (-1, 1):
        poly(ctx, [(-95 + sg * 45, -95), (-95 + sg * 42, -140), (-95 + sg * 12, -112)], fill=C["cat"])
    for ex in (-115, -75):
        arc_line(ctx, ex, -72, 11, math.pi * 0.15, math.pi * 0.85, w=5)
    ell(ctx, -95, -56, 5, 3, fill="#ff9b9b", w=0)
    ctx.restore()


def duck(ctx, x, y, s=0.8):
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ell(ctx, 0, -40, 60, 40, fill=C["duck"])
    ell(ctx, 30, -95, 36, 34, fill=C["duck"])
    poly(ctx, [(58, -95), (88, -88), (58, -80)], fill="#ff9a3c")
    ell(ctx, 38, -102, 5, 6, fill=OUT and "#2a1d17", w=0)
    ctx.restore()


def zzz(ctx, x, y, t):
    for i in range(3):
        ph = (t * 0.5 + i / 3) % 1
        caption(ctx, "z", x + 50 * ph + i * 10, y - 120 * ph, 34 + 26 * ph, alpha=1 - ph)


def steam(ctx, x, y, t, n=3, h=160, alpha=0.7):
    for i in range(n):
        ph = (t * 0.6 + i / n) % 1
        xx = x + (i - (n - 1) / 2) * 34 + 12 * math.sin(t * 2 + i + ph * 5)
        yy = y - ph * h
        ell(ctx, xx, yy, 14 + 18 * ph, 14 + 18 * ph, fill="#ffffff", w=0, alpha=alpha * (1 - ph))


# ------------------------------------------------------------------ the kitchen
STOVE_X, PAN_X, POT_X, BOWL_X = 690, 770, 925, 430
TOP = 1180                                                                   # counter top


def kitchen_back(ctx, t):
    ctx.rectangle(-2000, -2000, W + 4000, H + 4000)
    ctx.set_source(lin(0, 0, 0, TOP, [(0, C["wall"]), (1, C["wall2"])]))
    ctx.fill()
    for i in range(-10, 30):                                                  # faint wallpaper dots
        for j in range(0, 14):
            ell(ctx, i * 90 + (45 if j % 2 else 0), j * 90 + 40, 5, 5, fill="#f5d39b", w=0, alpha=0.7)
    window(ctx, 600, 300, 380, 430, t)
    curtain(ctx, 600, 300, 380, t)
    rr(ctx, 570, 742, 440, 34, 8, fill=C["wood"])                            # sill
    duck(ctx, 660, 744, 0.7)
    rr(ctx, 860, 690, 60, 54, 10, fill="#e58f6a")                            # little plant
    for a in (-0.6, 0, 0.6):
        ell(ctx, 890 + 30 * math.sin(a), 660 - 20 * math.cos(a), 16, 30, fill="#6cc48a", rot=a)
    for sy in (430, 690):                                                     # shelves with jars
        rr(ctx, 30, sy, 430, 26, 6, fill=C["wood"])
    jars = [(70, 430, 60, 90, C["jar1"]), (150, 430, 70, 70, C["jar2"]), (240, 430, 56, 100, C["jar3"]),
            (320, 430, 80, 60, "#c9b3f2"), (410, 430, 50, 80, C["jar1"]),
            (80, 690, 80, 70, C["jar3"]), (180, 690, 60, 100, C["jar2"]), (270, 690, 70, 80, "#9cc8f2"),
            (360, 690, 64, 66, C["jar2"])]
    for jx, jy, jw, jh, col in jars:
        rr(ctx, jx - jw / 2, jy - jh, jw, jh, 12, fill=col)
        rr(ctx, jx - jw / 2 - 4, jy - jh - 16, jw + 8, 18, 6, fill="#ffffff")
        rr(ctx, jx - jw / 2 + 8, jy - jh * 0.65, jw - 16, jh * 0.35, 4, fill=C["cream"], w=4)


def counter(ctx, t, sink=False):
    rr(ctx, -60, TOP - 6, W + 120, 52, 12, fill=C["wood"])
    rr(ctx, -60, TOP + 40, W + 120, 900, 0, fill=C["mint"])
    for i in range(6):
        rr(ctx, -30 + i * 190, TOP + 80, 170, 300, 16, fill=C["mint"], w=5)
        ell(ctx, 55 + i * 190, TOP + 110, 9, 9, fill="#ffffff", w=4)
    rr(ctx, -60, 1690, W + 120, 400, 0, fill=C["floor"])
    for i in range(-2, 12):
        line(ctx, [(i * 130, 1690), (i * 130 - 60, 1920)], w=4, col="#c97a2c")


def stove(ctx, t, pan=None, pot=True, lid_rattle=0.0):
    """A little stove on the counter: pan on the left burner, soup pot on the right."""
    rr(ctx, STOVE_X - 40, TOP - 40, 380, 46, 10, fill="#f4f1ea")
    for bx in (PAN_X, POT_X):
        ell(ctx, bx, TOP - 40, 60, 10, fill="#3b3b3b", w=4)
        for k in range(6):                                                    # little blue flame
            a = k / 6 * math.pi * 2
            ell(ctx, bx + 52 * math.cos(a), TOP - 36 + 4 * math.sin(a), 6, 9 + 3 * math.sin(t * 20 + k),
                fill="#6fb7ff", w=0, alpha=0.8)
    if pan is not None:
        pan(ctx)
    if pot:
        rat = lid_rattle * 3 * math.sin(t * 38)
        rr(ctx, POT_X - 85, TOP - 150, 170, 112, 26, fill=C["red"])
        for sg in (-1, 1):
            rr(ctx, POT_X + sg * 100 - 14, TOP - 128, 28, 18, 8, fill=C["red"])
        ell(ctx, POT_X + rat * 0.4, TOP - 152 - abs(rat), 92, 18, fill="#d64545")
        ell(ctx, POT_X + rat * 0.4, TOP - 170 - abs(rat), 16, 10, fill="#2a1d17", w=4)
        ell(ctx, POT_X - 40, TOP - 110, 20, 12, fill="#ffffff", w=0, alpha=0.6)     # dots on the enamel
        ell(ctx, POT_X + 30, TOP - 90, 14, 9, fill="#ffffff", w=0, alpha=0.6)
        steam(ctx, POT_X + 40, TOP - 180, t, n=3, h=150, alpha=0.6 + 0.3 * lid_rattle)


def bowl(ctx, x, y, fill=None, swirl=0.0, t=0.0, tilt=0.0):
    """Ceramic bowl standing at (x, y) (its base)."""
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(tilt)
    ctx.move_to(-100, -95)
    ctx.curve_to(-96, -20, -60, 0, 0, 0)
    ctx.curve_to(60, 0, 96, -20, 100, -95)
    ctx.close_path()
    paint(ctx, "#ffffff")
    line(ctx, [(-92, -60), (92, -60)], w=8, col="#7fb6e0")
    ell(ctx, 0, -95, 100, 22, fill="#f3efe8")
    if fill:
        ell(ctx, 0, -92, 86, 16, fill=fill, w=4)
        if swirl:
            for k in range(3):
                a = t * 9 + k * 2.1
                arc_line(ctx, 0, -92, 30 + k * 16, a, a + 1.4, w=4, col="#ffe28a")
    ctx.restore()


# ------------------------------------------------------------------ the dining nook
def nook(ctx, t, night=False):
    wall = [(0, "#2c2a45"), (1, "#3d3858")] if night else [(0, C["wall"]), (1, C["wall2"])]
    ctx.rectangle(-2000, -2000, W + 4000, H + 4000)
    ctx.set_source(lin(0, 0, 0, 1300, wall))
    ctx.fill()
    window(ctx, 170, 260, 740, 640, t, night=night, rain=not night)
    curtain(ctx, 170, 260, 740, t)
    for i in range(3):                                                         # string of little lights
        x0 = 150 + i * 260
        ctx.move_to(x0, 210)
        ctx.curve_to(x0 + 80, 250, x0 + 180, 250, x0 + 260, 210)
        ctx.set_source_rgb(*OUT)
        ctx.set_line_width(3)
        ctx.stroke()
        for k in range(4):
            u = (k + 0.5) / 4
            ell(ctx, x0 + 260 * u, 210 + 34 * math.sin(math.pi * u), 9, 9,
                fill=("#ffd45e" if (k + i) % 2 else "#ff9b9b"), w=3, alpha=1.0 if night else 0.9)
            if night:
                ell(ctx, x0 + 260 * u, 210 + 34 * math.sin(math.pi * u), 26, 26, fill="#ffe7a0", w=0, alpha=0.25)


def table(ctx, t, night=False):
    rr(ctx, -60, 1240, W + 120, 54, 14, fill="#d9a05b" if not night else "#a8763f")
    rr(ctx, -60, 1290, W + 120, 900, 0, fill="#f0c9a0" if not night else "#6a5576")
    for i in range(-2, 14):                                                    # tablecloth checks
        line(ctx, [(i * 90, 1290), (i * 90, 1920)], w=10, col="#f6dbbd" if not night else "#7a6486")


def plate(ctx, x, y, omelet=True):
    ell(ctx, x, y, 120, 26, fill="#ffffff")
    ell(ctx, x, y - 4, 86, 16, fill="#f2eee6", w=3)
    if omelet:
        ctx.move_to(x - 75, y - 6)
        ctx.curve_to(x - 70, y - 50, x + 70, y - 50, x + 75, y - 6)
        ctx.close_path()
        paint(ctx, C["yolk"])
        for dx in (-30, 5, 35):
            ell(ctx, x + dx, y - 22, 7, 5, fill="#ff9a3c", w=0)
            ell(ctx, x + dx + 12, y - 28, 5, 4, fill="#6cc48a", w=0)


def teacup(ctx, x, y, t, steaming=True):
    ell(ctx, x, y, 62, 14, fill="#ffffff")                                    # saucer
    ctx.move_to(x - 46, y - 70)
    ctx.curve_to(x - 44, y - 10, x + 44, y - 10, x + 46, y - 70)
    ctx.close_path()
    paint(ctx, "#ffffff")
    arc_line(ctx, x + 52, y - 46, 18, -math.pi / 2, math.pi / 2, w=LW)
    ell(ctx, x, y - 70, 46, 10, fill="#c98a45", w=4)
    line(ctx, [(x - 40, y - 46), (x + 40, y - 46)], w=6, col="#f29fb3")
    if steaming:
        steam(ctx, x, y - 90, t, n=2, h=120, alpha=0.65)


# ------------------------------------------------------------------ sound
def load(lib, sid):
    out = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", os.path.join(lib, "sounds", sid + ".mp3"),
                          "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    return np.frombuffer(out, np.float32).reshape(-1, 2).copy()


def onsets(a, min_gap=0.14, thresh=0.35):
    """Times of the hits in a recording (knife on the board, shell on the rim)."""
    m = np.abs(a).mean(1)
    hop = SR // 200
    env = np.sqrt(np.convolve(m ** 2, np.ones(hop) / hop, "same")[::hop])
    rise = np.maximum(0, np.diff(env, prepend=env[0]))
    rise /= rise.max() + 1e-9
    out, last = [], -9
    for i in np.argsort(rise)[::-1]:
        if rise[i] < thresh:
            break
        if all(abs(i - j) > min_gap * 200 for j in out):
            out.append(i)
    return sorted(i / 200 for i in out)


# ------------------------------------------------------------------ shots
def build_shots(lib):
    egg = load(lib, "egg_1")
    chop = load(lib, "chop_3")
    egg_hits = [t for t in onsets(egg, 0.5, 0.45) if 0.6 < t < 5.4][:3] or [1.2, 3.4]
    chop_hits = [t for t in onsets(chop, 0.16, 0.12) if 0.4 < t < 7.6] or list(np.arange(0.6, 7.6, 0.45))
    print("egg hits", [round(x, 2) for x in egg_hits], "| chop hits", len(chop_hits))
    S = []

    def add(dur, draw, cam0, cam1, sounds=(), cap=None):
        S.append(dict(dur=dur, draw=draw, cam0=cam0, cam1=cam1, sounds=list(sounds), cap=cap))

    GX, GY = BOWL_X, 905                                                       # her neck when at the bowl

    # 1. rain on the window
    def s1(ctx, t):
        kitchen_back(ctx, t)
        counter(ctx, t)
    add(5.0, s1, (2.1, 790, 520), (1.8, 790, 560), [("birds_2", 0, 0, 5.0, 0.25)], cap="a rainy morning")

    # 2. the kitchen, she sways, the cat's tail swishes
    def s2(ctx, t):
        kitchen_back(ctx, t)
        girl(ctx, GX, GY, t, hands={"left": (GX - 70, TOP - 30), "right": (GX + 70, TOP - 30)}, tilt=4 * math.sin(t * 1.3))
        counter(ctx, t)
        stove(ctx, t)
        cat_sitting(ctx, 120, TOP + 4, t, 0.9)
        bowl(ctx, GX, TOP + 2)
    add(4.5, s2, (1.0, 540, 960), (1.08, 540, 940), [("purr_2", 0, 0, 4.5, 0.35)])

    # 3. cracking eggs (her hand taps the rim exactly on each crack in the recording)
    def s3(ctx, t):
        kitchen_back(ctx, t)
        r, eggs_in, halves, drop = None, 0, None, None
        for i, c in enumerate(egg_hits):
            if t >= c + 0.6:
                eggs_in = i + 1
        cur = next((c for c in egg_hits if t < c + 0.6), None)
        if cur is not None and t > cur - 1.1:
            if t < cur:                                                       # bring the egg to the rim, tap
                k = ease((t - (cur - 1.1)) / 0.8)
                r = (lerp(GX + 140, GX + 70, k), lerp(TOP - 200, TOP - 112, k) + (12 if t > cur - 0.08 else 0))
            else:                                                             # open it over the bowl
                k = ease((t - cur) / 0.3)
                halves = 26 * k
                r = (GX + 34 + halves, TOP - 150)
                if t > cur + 0.25:
                    drop = lerp(TOP - 140, TOP - 92, ease((t - cur - 0.25) / 0.3))
        else:
            r = (GX + 150, TOP - 40)
        l = (GX - 34 - (halves or 0), TOP - 150) if halves is not None else (GX - 105, TOP - 70)

        def egg_r(c, x, y):
            if halves is None:
                ell(c, x + 4, y - 30, 30, 38, fill=C["cream"])
            else:
                c.move_to(x - 24, y - 26)
                c.curve_to(x - 24, y - 70, x + 24, y - 70, x + 24, y - 26)
                c.close_path()
                paint(c, C["cream"])

        def egg_l(c, x, y):
            if halves is not None:
                c.move_to(x - 24, y - 26)
                c.curve_to(x - 24, y + 14, x + 24, y + 14, x + 24, y - 26)
                c.close_path()
                paint(c, C["cream"])
        girl(ctx, GX, GY, t, hands={"left": l, "right": r}, props={"left": egg_l, "right": egg_r},
             eyes="happy", mouth="o" if halves else "smile", tilt=-3)
        counter(ctx, t)
        bowl(ctx, GX, TOP + 2, fill=C["yolk"] if eggs_in else None)
        for i in range(eggs_in):
            ell(ctx, GX - 30 + i * 40, TOP - 92, 18, 9, fill="#ffb21a", w=3)
        if drop is not None:
            ell(ctx, GX, drop, 16, 20, fill="#ffb21a", w=3)
    add(5.6, s3, (1.85, GX + 20, 925), (1.95, GX + 20, 915), [("egg_1", 0, 0, 5.6, 1.0)])

    # 4. whisking
    def s4(ctx, t):
        kitchen_back(ctx, t)
        a = t * 15
        hx, hy = GX + 30 + 34 * math.cos(a), TOP - 150 + 10 * math.sin(a)

        def whisk(c, x, y):
            line(c, [(x, y), (x - 6, y + 50)], w=14, col=C["wood_d"])
            for k in (-1, 0, 1):
                c.move_to(x - 6, y + 50)
                c.curve_to(x - 6 + k * 34, y + 70, x - 6 + k * 20, y + 110, x - 6, y + 112)
                c.set_source_rgb(0.6, 0.6, 0.62)
                c.set_line_width(5)
                c.stroke()
        girl(ctx, GX, GY, t, hands={"left": (GX - 105, TOP - 70), "right": (hx, hy)}, props={"right": whisk}, tilt=-4)
        counter(ctx, t)
        bowl(ctx, GX, TOP + 2, fill=C["yolk"], swirl=1.0, t=t)
    add(4.8, s4, (1.95, GX + 10, 930), (1.8, GX + 10, 945), [("whisk_1", 0, 0.5, 4.8, 1.0)])

    # 5. chopping a carrot (knife comes down on every hit of the knife in the recording)
    def s5(ctx, t):
        kitchen_back(ctx, t)
        done = sum(1 for c in chop_hits if c <= t)
        nxt = next((c for c in chop_hits if c > t), None)
        prev = max([c for c in chop_hits if c <= t], default=-1)
        lift = 0.0
        if nxt is not None:
            span = min(0.5, nxt - prev) if prev >= 0 else 0.5
            lift = ease(1 - (nxt - t) / span) if nxt - t < span else 1.0
            lift = math.sin(math.pi * min(1, (t - prev) / max(0.05, (nxt - prev)))) if prev >= 0 else lift
        left_end = GX - 70 + done * 9
        kx = left_end - 6
        ky = TOP - 52 - 70 * lift

        def knife(c, x, y):
            rr(c, x - 12, y - 46, 24, 56, 8, fill=C["wood_d"], w=5)
            c.move_to(x - 14, y + 8)
            c.line_to(x + 10, y + 8)
            c.line_to(x + 8, y + 92)
            c.curve_to(x - 4, y + 96, x - 14, y + 80, x - 14, y + 60)
            c.close_path()
            paint(c, "#dfe3ea", w=5)
        girl(ctx, GX, GY, t, hands={"left": (GX + 110, TOP - 88), "right": (kx + 10, ky - 40)}, props={"right": knife}, tilt=-5)
        counter(ctx, t)
        rr(ctx, GX - 190, TOP - 30, 380, 34, 10, fill="#f0c48a")                  # board
        ell(ctx, GX + 175, TOP - 14, 9, 9, fill=C["wood_d"], w=4)
        if left_end < GX + 120:                                                     # the carrot
            ctx.move_to(left_end, TOP - 58)
            ctx.line_to(GX + 120, TOP - 64)
            ctx.curve_to(GX + 150, TOP - 62, GX + 150, TOP - 36, GX + 120, TOP - 34)
            ctx.line_to(left_end, TOP - 38)
            ctx.close_path()
            paint(ctx, "#ff9a3c")
            for k in range(3):
                ell(ctx, GX + 160 + k * 10, TOP - 60 - k * 14, 14, 26, fill="#6cc48a", rot=0.6 + k * 0.3, w=5)
        for i in range(done):                                                       # pile of slices
            ell(ctx, GX - 170 + (i % 6) * 15, TOP - 36 - (i // 6) * 9, 14, 9, fill="#ff9a3c", w=4)
    add(7.6, s5, (1.7, GX + 10, 950), (1.8, GX + 10, 945), [("chop_3", 0, 0, 7.6, 1.0)])

    # 6. eggs sizzling in the pan, carrot bits on top, she nudges them with a spatula
    def pan_with_eggs(t):
        def p(ctx):
            rr(ctx, PAN_X - 95, TOP - 82, 190, 40, 18, fill="#3b3b3b")
            line(ctx, [(PAN_X - 95, TOP - 64), (PAN_X - 200, TOP - 80)], w=22, col="#3b3b3b")
            ell(ctx, PAN_X, TOP - 82, 92, 16, fill="#4a4a4a", w=5)
            ell(ctx, PAN_X, TOP - 84, 74, 11, fill=C["yolk"], w=4)
            for k in range(8):
                ph = (t * 1.7 + k * 0.37) % 1
                ell(ctx, PAN_X - 60 + (k * 37) % 120, TOP - 86 - 3 * ph, 4 * (1 - ph), 3 * (1 - ph), fill="#ffffff", w=0)
            for dx in (-40, -5, 30, 52):
                ell(ctx, PAN_X + dx, TOP - 86, 6, 4, fill="#ff9a3c", w=0)
            steam(ctx, PAN_X, TOP - 110, t, n=3, h=140, alpha=0.5)
        return p

    def s6(ctx, t):
        kitchen_back(ctx, t)
        sx = PAN_X + 20 * math.sin(t * 3.0)

        def spatula(c, x, y):
            line(c, [(x, y), (x + 20, y + 70)], w=14, col=C["wood_d"])
            rr(c, x + 6, y + 66, 34, 30, 8, fill=C["wood"], w=5)
        girl(ctx, PAN_X - 120, GY, t, hands={"left": (PAN_X - 240, TOP - 86), "right": (sx - 20, TOP - 190)},
             props={"right": spatula}, tilt=-4)
        counter(ctx, t)
        stove(ctx, t, pan=pan_with_eggs(t))
    add(6.4, s6, (1.75, PAN_X + 40, 940), (1.9, PAN_X + 40, 950), [("fry_egg_2", 0, 1.0, 6.4, 0.9)])

    # 7. the soup pot simmering, lid rattling
    def s7(ctx, t):
        kitchen_back(ctx, t)
        girl(ctx, PAN_X - 120, GY, t, hands={"left": (PAN_X - 230, TOP - 60), "right": (PAN_X - 20, TOP - 60)}, tilt=6)
        counter(ctx, t)
        stove(ctx, t, pan=pan_with_eggs(t + 6.4), lid_rattle=0.6 + 0.4 * math.sin(t * 1.5))
    add(4.2, s7, (2.2, POT_X - 40, 1000), (2.0, POT_X - 60, 980), [("simmer_1", 0, 2.0, 4.2, 0.9)])

    # 8. ta-da: the omelet on a plate, set down with a clink
    def s8(ctx, t):
        kitchen_back(ctx, t)
        up = ease(t / 0.6) * (1 - ease((t - 2.4) / 0.5))
        py = lerp(TOP - 20, TOP - 230, up)

        def hold(c, x, y):
            pass
        girl(ctx, GX, GY, t, hands={"left": (GX - 110, py - 10), "right": (GX + 110, py - 10)},
             eyes="happy", mouth="open" if up > 0.5 else "smile", tilt=5 * math.sin(t * 2))
        plate(ctx, GX, py)
        counter(ctx, t)
        stove(ctx, t)
        cat_sitting(ctx, 120, TOP + 4, t, 0.9)
        if up > 0.6:
            for i, (dx, dy) in enumerate(((-170, -120), (160, -150), (190, -40))):
                r = (14 + 6 * math.sin(t * 8 + i)) * up
                cx, cy = GX + dx, py + dy
                poly(ctx, [(cx, cy - r * 2), (cx + r * .4, cy - r * .4), (cx + r * 2, cy), (cx + r * .4, cy + r * .4),
                           (cx, cy + r * 2), (cx - r * .4, cy + r * .4), (cx - r * 2, cy), (cx - r * .4, cy - r * .4)],
                     fill="#ffd45e", w=4)
    add(4.0, s8, (1.15, GX + 40, 900), (1.25, GX + 40, 900), [("teacup_2", 2.55, 0.0, 1.4, 0.8)])

    # 9. washing up in the sink, bubbles
    def s9(ctx, t):
        kitchen_back(ctx, t)
        a = t * 6
        px, py = GX + 10 * math.cos(a * 0.5), TOP - 70
        sx_, sy_ = GX + 40 + 40 * math.cos(a), TOP - 100 + 16 * math.sin(a)

        def sponge(c, x, y):
            rr(c, x - 26, y - 18, 52, 34, 8, fill="#ffd84d", w=5)
            rr(c, x - 26, y - 18, 52, 12, 6, fill="#7fc8a9", w=5)
        girl(ctx, GX, GY, t, hands={"left": (GX - 70, TOP - 80), "right": (sx_, sy_)}, props={"right": sponge}, tilt=-4)
        counter(ctx, t)
        rr(ctx, GX - 170, TOP - 10, 340, 30, 10, fill="#cfd8de")                    # sink rim
        ell(ctx, px, py, 92, 20, fill="#ffffff")                                     # plate held up in the sink
        for i in range(14):                                                          # soap bubbles
            ph = (t * 0.4 + i * 0.13) % 1
            bx = GX - 150 + (i * 61) % 300
            ell(ctx, bx + 6 * math.sin(t * 3 + i), TOP - 14 - 160 * ph, 10 + 8 * (i % 3), 10 + 8 * (i % 3),
                fill="#e9f6ff", w=3, alpha=0.9 * (1 - ph))
    add(5.0, s9, (1.9, GX, 925), (1.8, GX, 940), [("dishes_2", 0, 2.0, 5.0, 0.9)])

    # 10. breakfast and tea by the rainy window, the cat purring next to her
    def s10(ctx, t):
        nook(ctx, t)
        sip = ease((t - 2.2) / 0.7) * (1 - ease((t - 5.0) / 0.7))
        cx, cy = lerp(620, 520, sip), lerp(1236, 1010, sip)

        def cup(c, x, y):
            if sip > 0.05:
                teacup(c, x + 10, y + 50, t, steaming=sip < 0.7)
        nx = 400
        girl(ctx, nx, 1040, t, hands={"left": (nx - 80, 1230), "right": (cx - 30, cy - 20) if sip > 0.05 else (nx + 100, 1225)},
             props={"right": cup}, eyes="happy", mouth="o" if 0.6 < sip else "smile", tilt=-6 * sip + 3)
        table(ctx, t)
        plate(ctx, nx, 1262)
        if sip <= 0.05:
            teacup(ctx, 620, 1262, t)
        else:
            ell(ctx, 620, 1262, 62, 14, fill="#ffffff")                              # empty saucer
        cat_curled(ctx, 860, 1262, t, 0.9, purr=1.0)
    add(8.0, s10, (1.1, 540, 900), (1.2, 560, 960),
        [("teacup_1", 5.6, 0.0, 1.6, 0.8), ("purr_1", 0, 0, 8.0, 0.55)], cap="slow mornings")

    # 11. night: rain has stopped, crickets, both asleep
    def s11(ctx, t):
        nook(ctx, t, night=True)
        nx = 400
        girl(ctx, nx, 1100, t * 0.4, hands={"left": (nx - 40, 1215), "right": (nx + 60, 1215)}, eyes="sleep",
             mouth="smile", tilt=14)
        table(ctx, t, night=True)
        teacup(ctx, 640, 1262, t, steaming=False)
        rr(ctx, 860, 1110, 34, 130, 8, fill="#c9a77c")                              # little lamp
        ctx.move_to(800, 1120)
        ctx.line_to(925, 1120)
        ctx.line_to(895, 1040)
        ctx.line_to(830, 1040)
        ctx.close_path()
        paint(ctx, "#ffd99a")
        g = cairo.RadialGradient(862, 1100, 10, 862, 1100, 420)
        g.add_color_stop_rgba(0, 1, 0.85, 0.55, 0.45)
        g.add_color_stop_rgba(1, 1, 0.85, 0.55, 0)
        ctx.set_source(g)
        ctx.paint()
        cat_curled(ctx, 680, 1262, t, 0.8)
        zzz(ctx, nx + 150, 820, t)
    add(6.5, s11, (1.15, 540, 940), (1.3, 520, 980), [("crickets_1", 0, 0, 6.5, 0.7), ("fireplace_1", 0, 0, 6.5, 0.25)],
        cap="goodnight")
    return S


# ------------------------------------------------------------------ render
def render(lib, out):
    S = build_shots(lib)
    t0 = 0.0
    for s in S:
        s["t0"] = t0
        t0 += s["dur"]
    total = t0
    n = int(total * SR) + SR
    mix = np.zeros((n, 2), np.float32)
    cache = {}

    def put(a, at, gain, fade=0.35):
        a = a.copy() * gain
        f = int(fade * SR)
        if len(a) > 2 * f:
            ramp = np.linspace(0, 1, f)[:, None]
            a[:f] *= ramp
            a[-f:] *= ramp[::-1]
        i = int(at * SR)
        mix[i:i + len(a)] += a[:max(0, n - i)]
    for s in S:
        for sid, start, off, ln, gain in s["sounds"]:
            if sid not in cache:
                cache[sid] = load(lib, sid)
            a = cache[sid][int(off * SR):int((off + ln + 0.4) * SR)]
            put(a, s["t0"] + start, gain)
    # rain bed through the whole morning (two clips crossfaded so it never loops audibly), out before night
    rain = np.concatenate([load(lib, "rain_roof_2"), load(lib, "rain_roof_3")])
    night = S[-1]["t0"]
    bed = np.zeros_like(mix)
    L = min(len(rain), int((night + 1.0) * SR))
    bed[:L] = rain[:L]
    k = np.ones(n, np.float32)
    ramp = np.clip((np.arange(n) / SR - (night - 0.5)) / 1.5, 0, 1)
    k *= 1 - ramp
    close = np.zeros(n, np.float32)                                            # softer under the close-ups
    for s in S[2:9]:
        close[int(s["t0"] * SR):int((s["t0"] + s["dur"]) * SR)] = 1
    close = np.convolve(close, np.ones(SR // 2) / (SR // 2), "same")
    mix += bed * (0.32 - 0.14 * close)[:, None] * k[:, None]
    mix = mix[:int((total + 0.3) * SR)]
    mix = mix / max(1e-6, np.abs(mix).max()) * 0.9

    # grain + vignette (cozy film look), computed once
    yy, xx = np.mgrid[0:H, 0:W]
    vig = (1 - 0.12 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) ** 1.6).clip(0.82, 1)[..., None]
    grain = np.random.default_rng(1).normal(0, 6, (4, H, W, 1)).astype(np.float32)
    warm = np.array([1.03, 1.0, 0.95], np.float32)

    surf = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
    with tempfile.TemporaryDirectory() as d:
        wav = os.path.join(d, "a.wav")
        import soundfile as sf
        sf.write(wav, mix, SR)
        enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                                "-s", f"{W}x{H}", "-framerate", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264",
                                "-pix_fmt", "yuv420p", "-crf", "18", "-c:a", "aac", "-b:a", "192k", "-shortest", out],
                               stdin=subprocess.PIPE)

        def frame_of(s, t):
            ctx = cairo.Context(surf)
            k = ease(t / s["dur"])
            z, fx, fy = (lerp(a, b, k) for a, b in zip(s["cam0"], s["cam1"]))
            ctx.save()
            ctx.translate(W / 2, H / 2)
            ctx.scale(z, z)
            ctx.translate(-fx, -fy)
            s["draw"](ctx, t)
            ctx.restore()
            if s["cap"]:
                a = ease(t / 0.6) * (1 - ease((t - s["dur"] + 1.0) / 0.6))
                caption(ctx, s["cap"], W / 2, 250, 84, alpha=a)
            surf.flush()
            buf = np.frombuffer(surf.get_data(), np.uint8).reshape(H, surf.get_stride() // 4, 4)[:, :W, 2::-1]
            return buf.astype(np.float32)

        XF = 0.45                                                                     # crossfade between shots
        for fi in range(int(total * FPS)):
            T = fi / FPS
            i = max(j for j, s in enumerate(S) if s["t0"] <= T)
            s = S[i]
            img = frame_of(s, T - s["t0"])
            if i > 0 and T - s["t0"] < XF:
                p = S[i - 1]
                prev = frame_of(p, T - p["t0"])
                k = ease((T - s["t0"]) / XF)
                img = prev * (1 - k) + img * k
            img = img * vig * warm + grain[fi % 4]
            if T < 0.6:
                img *= ease(T / 0.6)
            if T > total - 0.8:
                img *= ease((total - T) / 0.8)
            enc.stdin.write(np.clip(img, 0, 255).astype(np.uint8).tobytes())
        enc.stdin.close()
        enc.wait()
    print("wrote", out, f"({total:.1f} s)")


if __name__ == "__main__":
    render(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "cozy_morning.mp4")
