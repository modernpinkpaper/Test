""""Sammy invests $100 at 18" - a short money story video.

Characters and props are vector animations built with python-lottie.
Voiceover: Kokoro TTS (free, runs on CPU). Text and captions: Pillow.
No GPU and no AI image/video models. Each scene is also saved as a
Lottie .json file you can open in any Lottie player.

Setup (once):
    pip install lottie cairosvg pillow numpy imageio imageio-ffmpeg kokoro soundfile
Run:
    python demo_videos/sammy_story.py
"""
import io
import json
import math
import os
import random
import subprocess

import imageio
import imageio_ffmpeg
import numpy as np
import soundfile as sf
from lottie import Color, Point, objects
from lottie.exporters.cairo import export_png
from lottie.objects import easing
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "sammy_lottie")
W, H, FPS = 1080, 1920, 30
SR = 24000
SPEED = 1.4  # voice + animation speed (1.0 = calm, 1.4 = energetic)
GAP = 0.12  # pause between sentences (seconds)
TAIL = 0.3  # pause at the end of each scene

# ---------------------------------------------------------------- the money
RATE, MONTHLY, START, CRASH_AGE, CRASH = 0.08, 50, 100, 25, 0.30


def simulate():
    """Balance by age: $100 at 18, +$50 a month, 8% a year, -30% crash at 25."""
    bal, put_in, by_age = START, START, {18: START}
    for m in range((65 - 18) * 12):
        age = 18 + (m + 1) / 12
        bal = bal * (1 + RATE / 12) + MONTHLY
        put_in += MONTHLY
        if (m + 1) == (CRASH_AGE - 18) * 12:
            bal *= 1 - CRASH
        if (m + 1) % 12 == 0:
            by_age[round(age)] = bal
    return by_age, put_in


BY_AGE, PUT_IN = simulate()
FINAL = BY_AGE[65]
FINAL_ROUND = int(FINAL // 10000 * 10000)
PUT_IN_ROUND = int(PUT_IN // 1000 * 1000)


# ------------------------------------------------------------- lottie helpers
def C(h, a=None):
    return Color(*[int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)])


def add(parent, shape):
    """Add on top of what is already there (painter's order)."""
    parent.shapes.insert(0, shape)
    return shape


def group(parent, pos=(0, 0), anchor=(0, 0)):
    g = objects.Group()
    g.transform.position.value = Point(*pos)
    g.transform.anchor_point.value = Point(*anchor)
    return add(parent, g)


def fill(parent, shape, color, opacity=100):
    g = group(parent)
    g.shapes.insert(0, shape)
    f = objects.Fill(C(color))
    f.opacity.value = opacity
    g.shapes.insert(1, f)
    return g


def line(parent, pts, color, width, closed=False, smooth=None, trim=None):
    g = group(parent)
    bez = objects.Bezier()
    for i, p in enumerate(pts):
        if smooth and i in smooth:
            bez.add_point(Point(*p), Point(*smooth[i][0]), Point(*smooth[i][1]))
        else:
            bez.add_point(Point(*p))
    if closed:
        bez.close()
    g.shapes.insert(0, objects.Path(bez))
    idx = 1
    if trim is not None:
        g.shapes.insert(idx, trim)
        idx += 1
    st = objects.Stroke(C(color), width)
    st.line_cap = objects.LineCap.Round
    st.line_join = objects.LineJoin.Round
    g.shapes.insert(idx, st)
    g.stroke = st
    return g


def poly(parent, pts, color):
    bez = objects.Bezier()
    for p in pts:
        bez.add_point(Point(*p))
    bez.close()
    return fill(parent, objects.Path(bez), color)


def circle(parent, x, y, d, color, opacity=100):
    return fill(parent, objects.Ellipse(Point(x, y), Point(d, d)), color, opacity)


def ellipse(parent, x, y, w, h, color):
    return fill(parent, objects.Ellipse(Point(x, y), Point(w, h)), color)


def rect(parent, x, y, w, h, color, r=0, opacity=100):
    return fill(parent, objects.Rect(Point(x, y), Point(w, h), r), color, opacity)


def keys(prop, pairs, ease=True):
    for f, v in pairs:
        if isinstance(v, (tuple, list)):
            v = Point(*v)
        prop.add_keyframe(int(f), v, easing.Sigmoid() if ease else easing.Linear())


def pop_in(g, f0, dur=10):
    keys(g.transform.scale, [(0, (0, 0)), (f0, (0, 0)), (f0 + dur * 0.7, (112, 112)), (f0 + dur, (100, 100))])


def pop_out(g, f0, dur=8):
    keys(g.transform.scale, [(f0, (100, 100)), (f0 + dur * 0.4, (115, 115)), (f0 + dur, (0, 0))])


def bob(g, x, y, n, amp=6, period=36):
    keys(g.transform.position, [(f, (x, y + amp * math.sin(2 * math.pi * f / period)))
                                for f in range(0, n + 1, 6)], ease=False)


# ----------------------------------------------------------------- characters
SKIN, SKIN_DARK = "#f1c27d", "#d9a066"


def person(parent, x, y, n, top="#ff7a59", pants="#2d3a5c", hair="#3b2416", mood="happy",
           old=False, wave=None, shake=None, scale=100):
    """A flat cartoon person. Feet at (x, y). Returns the main group."""
    me = group(parent, (x, y))
    me.transform.scale.value = Point(scale, scale)
    # legs + shoes
    for sx in (-1, 1):
        line(me, [(sx * 35, -230), (sx * 45, -20)], pants, 40)
        ellipse(me, sx * 55, -10, 90, 40, "#1d1d27")
    # body
    rect(me, 0, -330, 190, 240, top, r=70)
    if not old:
        rect(me, 0, -380, 70, 20, "#ffffff", r=10, opacity=35)  # hoodie strings area
    # arms (rotate around the shoulder)
    arms = {}
    for sx in (-1, 1):
        a = group(me, (sx * 80, -415), (sx * 80, -415))
        line(a, [(sx * 80, -415), (sx * 118, -255)], top, 38)
        circle(a, sx * 120, -245, 44, SKIN)
        arms[sx] = a
    if old:  # cane in right hand
        line(me, [(150, -250), (170, -10)], "#6b4226", 14)
    # head (tilts around the neck)
    head = group(me, (0, -445), (0, -445))
    ellipse(head, 0, -588, 212, 130, "#b8b8c0" if old else hair)  # hair behind
    circle(head, 0, -530, 190, SKIN)
    circle(head, -95, -525, 36, SKIN_DARK)  # ears
    circle(head, 95, -525, 36, SKIN_DARK)
    if not old:
        poly(head, [(-90, -575), (-40, -630), (40, -628), (95, -580), (60, -600), (0, -595), (-50, -598)], hair)
    # eyes
    eyes = group(head, (0, -535), (0, -535))
    big = mood == "shocked"
    for sx in (-1, 1):
        circle(eyes, sx * 36, -535, 30 if big else 20, "#1d1d27")
        circle(eyes, sx * 36 + 5, -541, 7, "#ffffff")
    if old:
        for sx in (-1, 1):
            g = group(head)
            g.shapes.insert(0, objects.Ellipse(Point(sx * 36, -535), Point(62, 62)))
            st = objects.Stroke(C("#1d1d27"), 6)
            g.shapes.insert(1, st)
        line(head, [(-5, -535), (5, -535)], "#1d1d27", 6)
    # brows + mouth
    if big:
        for sx in (-1, 1):
            line(head, [(sx * 20, -575), (sx * 52, -585)], "#1d1d27", 7)
        ellipse(head, 0, -480, 38, 50, "#5a1a1a")
    elif mood == "calm":
        line(head, [(-22, -482), (22, -482)], "#5a1a1a", 8)
    else:
        line(head, [(-32, -490), (32, -490)], "#5a1a1a", 8,
             smooth={0: ((0, 0), (12, 22)), 1: ((-12, 22), (0, 0))})
    circle(head, -60, -500, 30, "#ff8a8a", opacity=45)  # cheeks
    circle(head, 60, -500, 30, "#ff8a8a", opacity=45)

    # blink every ~3 s
    frames = [(0, (100, 100))]
    for f in range(40, n, 95):
        frames += [(f, (100, 100)), (f + 3, (100, 10)), (f + 6, (100, 100))]
    keys(eyes.transform.scale, frames, ease=False)
    # idle bob, or shake
    if shake:
        f0, f1 = shake
        pts = [(0, (x, y)), (f0, (x, y))]
        for i, f in enumerate(range(f0, f1, 2)):
            pts.append((f, (x + (14 if i % 2 else -14), y)))
        pts.append((f1, (x, y)))
        keys(me.transform.position, pts, ease=False)
    else:
        bob(me, x, y, n, amp=5, period=40)
    keys(head.transform.rotation, [(f, 4 * math.sin(2 * math.pi * f / 70)) for f in range(0, n + 1, 10)])
    if wave:
        f0, f1 = wave
        a = arms[1]
        pts = [(0, 0), (f0, 0), (f0 + 8, -150)]
        f = f0 + 8
        while f + 8 < f1:
            pts += [(f + 6, -125), (f + 12, -155)]
            f += 12
        pts += [(f1, -150), (f1 + 8, 0)]
        keys(a.transform.rotation, pts)
    me.arms, me.head = arms, head
    return me


def coin(parent, x, y, d=90):
    g = group(parent, (x, y), (x, y))
    circle(g, x, y, d, "#e0a800")
    circle(g, x, y, d * 0.78, "#ffd23f")
    rect(g, x, y, d * 0.12, d * 0.45, "#e0a800", r=4)
    return g


def bill(parent, x, y):
    g = group(parent, (x, y), (x, y))
    rect(g, x, y, 300, 150, "#2e8b57", r=16)
    rect(g, x, y, 260, 112, "#3cb371", r=10)
    circle(g, x, y, 90, "#2e8b57")
    return g


def jar(parent, x, y, n, fill_keys):
    """Glass jar with green 'money' level. fill_keys: [(frame, 0..1)]."""
    g = group(parent, (0, 0))
    h, w = 420, 300
    rect(g, x, y - h / 2, w, h, "#ffffff", r=50, opacity=18)
    lvl = rect(g, x, y - 20, w - 40, 40, "#2ecc71", r=24, opacity=90)
    rs = lvl.shapes[0]
    keys(rs.size, [(f, (w - 40, max(20, v * (h - 40)))) for f, v in fill_keys])
    keys(rs.position, [(f, (x, y - 20 - max(20, v * (h - 40)) / 2 + 10)) for f, v in fill_keys])
    outline = group(g)
    outline.shapes.insert(0, objects.Rect(Point(x, y - h / 2), Point(w, h), 50))
    outline.shapes.insert(1, objects.Stroke(C("#dff6ff"), 10))
    rect(g, x, y - h - 20, w * 0.8, 44, "#8a5a44", r=14)  # lid
    return g


def drop_coins(parent, x, y_top, y_bottom, starts, fall=16):
    for f0 in starts:
        c = coin(parent, x, y_top, 80)
        keys(c.transform.position, [(0, (x, y_top - 300)), (f0, (x, y_top - 300)),
                                    (f0 + fall, (x, y_bottom)), (f0 + fall + 1, (x, y_bottom))], ease=False)
        keys(c.transform.opacity, [(0, 0), (f0, 0), (f0 + 1, 100), (f0 + fall, 100), (f0 + fall + 3, 0)], ease=False)


# ----------------------------------------------------------------- scenes
SCENES = [
    dict(key="meet", title="AGE 18", bg=("#1b9aaa", "#0b3c49"),
         lines=["Meet Sammy!", "He just turned eighteen... and he's got one hundred bucks!"]),
    dict(key="friends", title="WHERE $100 USUALLY GOES", bg=("#7b2ff7", "#2b0b5c"),
         lines=["His friends? They blew it on sneakers and pizza!"]),
    dict(key="plan", title="SAMMY'S PLAN", bg=("#1d4ed8", "#0b1a4a"),
         lines=["But Sammy? He threw his hundred into an index fund!",
                "And every single month, he added fifty more!"]),
    dict(key="crash", title="AGE 25: THE CRASH", bg=("#8b0000", "#1a0000"),
         lines=["Then at twenty five... BOOM! The market crashed!", "His account dropped thirty percent!"]),
    dict(key="sell", title="EVERYONE PANICKED", bg=("#334155", "#0f172a"),
         lines=["Everyone screamed: sell! Sell! SELL!", "Sammy? He didn't flinch.",
                "He kept adding fifty bucks. Every. Single. Month."]),
    dict(key="grow", title="YEARS PASS...", bg=("#15803d", "#052e16"),
         lines=["Years flew by...", "And that tiny seed? It kept on growing!"]),
    dict(key="retire", title="AGE 65", bg=("#d4a017", "#4a2c00"),
         lines=[f"At sixty five, Sammy retired with about {FINAL_ROUND:,} dollars!",
                f"And he only put in about {PUT_IN_ROUND:,}!"]),
    dict(key="end", title="THE LESSON", bg=("#111827", "#000000"),
         lines=["Start early!", "Stay patient!", "And let time do the heavy lifting!"]),
]


def build(scene, n, t):
    """Return a lottie Animation for this scene. t(sec) -> frame."""
    an = objects.Animation(n, FPS)
    an.width, an.height = W, H
    L = an.add_layer(objects.ShapeLayer())
    k = scene["key"]
    floor = 1500
    if k == "meet":
        ellipse(L, 540, floor, 520, 60, "#000000").shapes[1].opacity.value = 25
        s = person(L, 540, floor, n, wave=(t(0.3), t(2.2)))
        pop_in(s, 2, 12)
        b = bill(L, 540, 640)
        pop_in(b, t(1.6), 12)
        keys(b.transform.rotation, [(f, 6 * math.sin(f / 9)) for f in range(0, n + 1, 6)])
    elif k == "friends":
        for x, top, hair in ((300, "#ff4d6d", "#1d1d27"), (780, "#00b4d8", "#6b3e26")):
            person(L, x, floor, n, top=top, hair=hair, scale=85)
        rng = random.Random(4)
        for i in range(10):
            x0 = rng.choice((300, 780))
            f0 = t(0.3) + i * 5
            g = group(L, (x0, 1150), (x0, 1150))
            if i % 2:  # sneaker
                rect(g, x0, 1150, 150, 60, "#ffffff", r=28)
                rect(g, x0, 1178, 160, 18, "#ff4d6d", r=8)
            else:  # pizza slice
                poly(g, [(x0 - 70, 1110), (x0 + 70, 1110), (x0, 1260)], "#ffb347")
                rect(g, x0, 1108, 150, 22, "#c77d38", r=10)
                circle(g, x0 - 20, 1150, 26, "#d62828")
                circle(g, x0 + 22, 1170, 22, "#d62828")
            x1 = x0 + rng.randint(-250, 250)
            keys(g.transform.position, [(0, (x0, 1150)), (f0, (x0, 1150)), (f0 + 40, (x1, 520))])
            keys(g.transform.rotation, [(f0, 0), (f0 + 40, rng.randint(-200, 200))])
            keys(g.transform.opacity, [(0, 0), (f0, 0), (f0 + 3, 100), (f0 + 30, 100), (f0 + 40, 0)])
    elif k == "plan":
        s = person(L, 330, floor, n, wave=(t(0.2), t(1.2)))
        drops = [t(0.9)] + [t(3.4) + i * 14 for i in range(8)]
        jar(L, 770, floor, n, [(0, 0.03)] + [(f + 16, min(1, 0.06 + 0.07 * (i + 1))) for i, f in enumerate(drops)])
        drop_coins(L, 770, 650, floor - 90, drops)
    elif k == "crash":
        panel = rect(L, 540, 900, 900, 620, "#000000", r=40, opacity=40)
        pts = [(160, 1100), (260, 1040), (360, 1060), (460, 960), (560, 900), (640, 860), (700, 1130),
               (780, 1080), (900, 1110)]
        tr = objects.Trim()
        keys(tr.end, [(0, 0), (t(0.2), 0), (t(2.2), 100)], ease=False)
        ln = line(L, pts, "#2ecc71", 14, trim=tr)
        keys(ln.stroke.color, [(t(1.2), C("#2ecc71")), (t(1.4), C("#ff3b3b"))], ease=False)
        person(L, 540, floor + 250, n, mood="shocked", shake=(t(1.4), t(3.0)), scale=80)
    elif k == "sell":
        s = person(L, 540, floor, n)
        spots = [(250, 520), (820, 600), (230, 900), (850, 980)]
        for i, (x, y) in enumerate(spots):
            g = group(L, (x, y), (x, y))
            rect(g, x, y, 260, 130, "#ffffff", r=40)
            poly(g, [(x - 20, y + 60), (x + 20, y + 60), (x + (40 if x < 540 else -40), y + 110)], "#ffffff")
            f0 = t(0.1) + i * 6
            pop_in(g, f0, 10)
            pop_out(g, t(2.2) + i * 3)
        drop_coins(L, 540, 500, 1000, [t(3.2) + i * 14 for i in range(6)])
    elif k == "grow":
        rect(L, 540, floor - 60, 260, 140, "#b5651d", r=24)
        rect(L, 540, floor - 130, 300, 40, "#8b4513", r=14)
        stem_tr = objects.Trim()
        keys(stem_tr.end, [(0, 0), (t(0.3), 0), (t(2.5), 100)])
        line(L, [(540, floor - 150), (530, 1100), (560, 800), (540, 620)], "#3e7d2a", 34, trim=stem_tr)
        for i, (bx, by, ex, ey) in enumerate([(535, 1050, 380, 950), (550, 900, 720, 800), (545, 760, 400, 660)]):
            tr = objects.Trim()
            f0 = t(1.0) + i * 12
            keys(tr.end, [(0, 0), (f0, 0), (f0 + 20, 100)])
            line(L, [(bx, by), (ex, ey)], "#3e7d2a", 20, trim=tr)
        rng = random.Random(2)
        leaves = [(380, 950), (720, 800), (400, 660), (540, 600), (620, 700), (460, 820), (660, 930)]
        for i, (lx, ly) in enumerate(leaves):
            for j in range(3):
                g = group(L, (lx + rng.randint(-60, 60), ly + rng.randint(-50, 50)))
                circle(g, 0, 0, rng.randint(90, 140), rng.choice(["#22c55e", "#16a34a", "#4ade80"]))
                pop_in(g, t(1.4) + i * 5 + j * 2, 10)
        for i, (lx, ly) in enumerate(leaves):
            c = coin(L, lx, ly, 70)
            pop_in(c, t(3.2) + i * 4, 10)
    elif k == "retire":
        rng = random.Random(9)
        for i in range(70):  # confetti
            x = rng.randint(0, W)
            f0 = t(2.0) + rng.randint(0, 40)
            g = group(L, (x, -50), (x, -50))
            rect(g, x, -50, 22, 34, rng.choice(["#ff4d6d", "#ffd23f", "#4ade80", "#60a5fa", "#ffffff"]), r=4)
            keys(g.transform.position, [(0, (x, -60)), (f0, (x, -60)),
                                        (f0 + 90, (x + rng.randint(-150, 150), H + 60))], ease=False)
            keys(g.transform.rotation, [(f0, 0), (f0 + 90, rng.randint(-720, 720))], ease=False)
        person(L, 540, floor + 60, n, top="#8e44ad", pants="#34495e", old=True, wave=(t(2.0), t(4.5)))
    elif k == "end":
        person(L, 330, floor, n, wave=(t(0.2), t(2.0)), scale=85)
        person(L, 760, floor, n, top="#8e44ad", pants="#34495e", old=True, wave=(t(1.0), t(3.0)), scale=85)
    return an


# ------------------------------------------------------------ text + render
def font(w, size):
    return ImageFont.truetype(os.path.join(HERE, "fonts", f"poppins-latin-{w}-normal.woff"), size)


F_TITLE, F_CAP, F_BIG, F_MED, F_SMALL = font(800, 64), font(800, 50), font(800, 150), font(800, 64), font(400, 30)


def gradient(c1, c2):
    a = np.array([int(c1[i:i + 2], 16) for i in (1, 3, 5)], np.float32)
    b = np.array([int(c2[i:i + 2], 16) for i in (1, 3, 5)], np.float32)
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    t = np.clip(y / H + 0.15 * np.sin(x / W * math.pi), 0, 1)[..., None]
    img = a * (1 - t) + b * t
    glow = np.exp(-(((x - W / 2) / (W * 0.6)) ** 2 + ((y - H * 0.45) / (H * 0.35)) ** 2))[..., None]
    img = img + glow * 40
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert("RGBA")


def wrap(d, text, f, maxw):
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        test = (cur + " " + w_).strip()
        if d.textlength(test, font=f) > maxw and cur:
            lines.append(cur)
            cur = w_
        else:
            cur = test
    return lines + [cur]


def draw_title(d, text, alpha):
    f = F_TITLE
    tw = d.textlength(text, font=f)
    x0 = (W - tw) / 2 - 40
    d.rounded_rectangle([x0, 150, x0 + tw + 80, 260], radius=55, fill=(0, 0, 0, int(110 * alpha)))
    d.text((W / 2, 205), text, font=f, anchor="mm", fill=(255, 255, 255, int(255 * alpha)))


def draw_caption(d, text):
    lines = wrap(d, text, F_CAP, W - 160)
    y = 1690 - (len(lines) - 1) * 34
    for ln in lines:
        d.text((W / 2, y), ln, font=F_CAP, anchor="mm", fill=(255, 255, 255),
               stroke_width=6, stroke_fill=(0, 0, 0))
        y += 68


def overlay(scene, d, sec, dur):
    """Numbers and words that change over time (drawn on top of the Lottie art)."""
    k = scene["key"]
    ease = lambda a, b: max(0.0, min(1.0, (sec - a) / (b - a)))
    if k == "meet" and sec > 1.9:
        d.text((540, 640), "$100", font=F_MED, anchor="mm", fill=(255, 255, 255),
               stroke_width=4, stroke_fill=(20, 80, 50))
    if k == "friends" and sec > 1.8:
        d.text((540, 420), "$100 GONE", font=F_BIG, anchor="mm", fill=(255, 90, 110),
               stroke_width=6, stroke_fill=(0, 0, 0))
    if k == "plan" and sec > 3.2:
        d.text((770, 980), "+$50 / month", font=F_MED, anchor="mm", fill=(255, 255, 255))
    if k == "crash":
        v = BY_AGE[25] / (1 - CRASH) if sec < 1.3 else BY_AGE[25]
        d.text((540, 690), f"${v:,.0f}", font=F_MED, anchor="mm",
               fill=(46, 204, 113) if sec < 1.3 else (255, 80, 80))
        if sec > 1.4:
            d.text((540, 440), "-30%", font=F_BIG, anchor="mm", fill=(255, 60, 60),
                   stroke_width=6, stroke_fill=(0, 0, 0))
    if k == "sell":
        if 0.1 < sec < 2.6:
            for i, (x, y) in enumerate([(250, 520), (820, 600), (230, 900), (850, 980)]):
                if sec > 0.1 + i * 0.2 + 0.25:
                    d.text((x, y), "SELL!", font=F_MED, anchor="mm", fill=(220, 30, 60))
        if sec > 3.0:
            d.text((540, 400), "Keep buying.", font=F_MED, anchor="mm", fill=(255, 255, 255))
    if k == "grow":
        age = int(25 + 35 * ease(0.3, dur - 0.5))
        d.text((540, 380), f"Age {age}", font=F_MED, anchor="mm", fill=(255, 255, 255))
        d.text((540, 470), f"${BY_AGE[age]:,.0f}", font=F_MED, anchor="mm", fill=(255, 230, 120))
    if k == "retire":
        p = ease(0.2, 3.0)
        p = 1 - (1 - p) ** 3
        d.text((540, 560), f"${FINAL * p:,.0f}", font=F_BIG, anchor="mm", fill=(255, 255, 255),
               stroke_width=6, stroke_fill=(90, 60, 0))
        if sec > 3.3:
            d.text((540, 720), f"He put in: ${PUT_IN:,.0f}", font=F_MED, anchor="mm", fill=(255, 245, 200))
    if k == "end":
        for i, txt in enumerate(["Start early.", "Stay patient.", "Let time work."]):
            if sec > [0.1, 0.9, 1.8][i]:
                d.rounded_rectangle([190, 380 + i * 150, 890, 500 + i * 150], radius=60,
                                    fill=(45, 52, 70))
                d.text((540, 440 + i * 150), txt, font=F_MED, anchor="mm", fill=(255, 255, 255))
        for i, txt in enumerate(["Example only. Assumes an average 8% yearly return.", "Not financial advice."]):
            d.text((540, 1830 + i * 40), txt, font=F_SMALL, anchor="mm", fill=(170, 170, 190))


def speak(pipe, text):
    audio = [a for _, _, a in pipe(text, voice="am_michael", speed=SPEED)]
    return np.concatenate([np.asarray(a) for a in audio]).astype(np.float32)


def music(seconds):
    """Soft background pad + light beat."""
    sr, bpm = SR, 90
    n = int(sr * seconds)
    out = np.zeros(n, np.float32)
    beat = 60 / bpm
    chords = [[60, 64, 67, 71], [57, 60, 64, 67], [53, 57, 60, 64], [55, 59, 62, 67]]
    bar = beat * 4
    for i in range(int(seconds / bar) + 1):
        s = int(i * bar * sr)
        seg = np.arange(int(bar * sr))
        env = np.minimum(1, seg / (0.5 * sr)) * np.exp(-seg / (4 * sr))
        tone = sum(np.sin(2 * np.pi * 440 * 2 ** ((m - 69) / 12) * seg / sr) for m in chords[i % 4])
        e = min(n, s + len(seg))
        out[s:e] += (tone * env * 0.05)[:e - s]
    for k in range(int(seconds / beat) + 1):
        s = int(k * beat * sr)
        seg = np.arange(int(0.2 * sr))
        kick = np.sin(2 * np.pi * np.cumsum(100 * np.exp(-seg / (0.03 * sr)) + 45) / sr) * np.exp(-seg / (0.07 * sr))
        e = min(n, s + len(seg))
        out[s:e] += (kick * (0.35 if k % 2 == 0 else 0.15))[:e - s]
    out /= np.abs(out).max() + 1e-6
    t = np.arange(n) / sr
    return out * np.minimum(1, np.minimum(t / 1.5, (seconds - t) / 2)) * 0.12


def main():
    from kokoro import KPipeline
    pipe = KPipeline(lang_code="a")
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(HERE, "_story_silent.mp4")
    wav = os.path.join(HERE, "_story.wav")
    out = os.path.join(HERE, "sammy_story.mp4")
    wr = imageio.get_writer(silent, fps=FPS, codec="libx264", quality=8, macro_block_size=1)
    voice = []

    for scene in SCENES:
        # 1) voice, sentence by sentence (gives exact caption timing)
        caps, t0 = [], 0.0
        for text in scene["lines"]:
            a = speak(pipe, text)
            caps.append((t0, t0 + len(a) / SR, text))
            voice += [a, np.zeros(int(GAP * SR), np.float32)]
            t0 += len(a) / SR + GAP
        voice.append(np.zeros(int(TAIL * SR), np.float32))
        dur = t0 + TAIL
        n = int(round(dur * FPS))
        # 2) lottie animation for the scene
        an = build(scene, n, lambda s: int(s * FPS / SPEED))
        with open(os.path.join(OUT_DIR, f"{scene['key']}.json"), "w") as fh:
            json.dump(an.to_dict(), fh)
        bg = gradient(*scene["bg"])
        print(f"scene {scene['key']}: {dur:.1f}s, {n} frames")
        # 3) render frames: background + lottie + text
        for fr in range(n):
            sec = fr / FPS
            buf = io.BytesIO()
            export_png(an, buf, fr)
            art = Image.open(io.BytesIO(buf.getvalue())).convert("RGBA")
            img = bg.copy()
            img.alpha_composite(art)
            d = ImageDraw.Draw(img)
            draw_title(d, scene["title"], min(1, sec / 0.2))
            overlay(scene, d, sec * SPEED, dur * SPEED)
            cur = [c for c in caps if c[0] <= sec < c[1] + GAP]
            if cur:
                draw_caption(d, cur[0][2])
            wr.append_data(np.asarray(img.convert("RGB")))
    wr.close()

    v = np.concatenate(voice)
    bgm = music(len(v) / SR + 0.1)[:len(v)]
    mix = v + np.pad(bgm, (0, len(v) - len(bgm)))
    sf.write(wav, np.clip(mix, -1, 1), SR)
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ff, "-loglevel", "error", "-y", "-i", silent, "-i", wav, "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "160k", "-shortest", out], check=True)
    os.remove(silent)
    os.remove(wav)
    print("saved", out, f"(final ${FINAL:,.0f}, put in ${PUT_IN:,.0f})")


if __name__ == "__main__":
    main()
