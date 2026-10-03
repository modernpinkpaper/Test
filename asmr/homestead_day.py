"""'A day on the homestead': a ~65 s cozy outdoor ASMR cartoon in the same coloring-book look as cozy_morning.py
(same girl, now in a straw sun hat). Dawn and the rooster, a walk down the path, collecting eggs, splitting wood,
lighting the campfire, water from the stream, eggs in a cast-iron skillet and stew over the fire, dinner on a log,
then night with frogs and crickets. Only real recordings from the kept sound library; footsteps, axe chops and egg
cracks are timed to the hits in the recordings.

    python asmr/homestead_day.py LIB_DIR OUT.mp4
"""
import math
import os
import sys

import cairocffi as cairo
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cozy_morning as K                                                    # noqa: E402
from cozy_morning import (C, SR, W, arc_line, caption, cat_curled, ease, ell, lerp, lin, line, load,  # noqa: E402
                          onsets, paint, poly, rr, steam, zzz)

GROUND = 1500
SKIES = {"dawn": [(0, "#f9c6a3"), (0.55, "#fde3c2"), (1, "#cfe8f0")],
         "day": [(0, "#8fcdf0"), (1, "#e3f4fb")],
         "dusk": [(0, "#5b5a9e"), (0.6, "#f2a07a"), (1, "#ffd59e")],
         "night": [(0, "#141c3d"), (1, "#2c3a6e")]}


# ------------------------------------------------------------------ the land
def sky(ctx, t, tod):
    ctx.rectangle(-2000, -2000, W + 4000, 6000)
    ctx.set_source(lin(0, 0, 0, GROUND, SKIES[tod]))
    ctx.fill()
    if tod == "dawn":
        g = cairo.RadialGradient(780, 1060, 20, 780, 1060, 500)
        g.add_color_stop_rgba(0, 1, 0.9, 0.6, 0.8)
        g.add_color_stop_rgba(1, 1, 0.9, 0.6, 0)
        ctx.set_source(g)
        ctx.paint()
        ell(ctx, 780, 1060 - 40 * ease(t / 5), 90, 90, fill="#ffd166", w=0)
    if tod == "day":
        ell(ctx, 880, 300, 70, 70, fill="#ffe27a", w=0)
    if tod in ("night", "dusk"):
        for i in range(40):
            sx, sy = (i * 137) % (W + 400) - 200, (i * 89) % 900
            a = (0.4 + 0.6 * abs(math.sin(t * 1.5 + i))) * (1 if tod == "night" else 0.3)
            ell(ctx, sx, sy, 3, 3, fill="#fff6d0", w=0, alpha=a)
        if tod == "night":
            ell(ctx, 820, 330, 54, 54, fill="#fff3c4", w=0)
            ell(ctx, 844, 318, 48, 48, fill="#1b2449", w=0)
    for i in range(3):                                                      # clouds drifting
        cx = (i * 430 + t * 12) % (W + 600) - 300
        a = 0.25 if tod == "night" else 0.9
        for dx, r in ((0, 60), (60, 46), (-60, 42)):
            ell(ctx, cx + dx, 260 + i * 120, r * 1.5, r, fill="#ffffff", w=0, alpha=a)


def hills(ctx, tod):
    far, near = {"night": ("#2f4a5c", "#355c4a"), "dusk": ("#6f8a7a", "#7d9c6a")}.get(tod, ("#a9d3b0", "#8cc78f"))
    ell(ctx, 200, GROUND - 120, 700, 260, fill=far, w=5)
    ell(ctx, 1000, GROUND - 100, 650, 240, fill=far, w=5)
    ell(ctx, 540, GROUND + 60, 1100, 260, fill=near, w=6)


def ground(ctx, tod, path=True):
    g = {"night": "#3d6146", "dusk": "#7fae63"}.get(tod, "#9fd17a")
    rr(ctx, -2000, GROUND, W + 4000, 2000, 0, fill=g, w=6)
    if path:
        ctx.move_to(380, GROUND)
        ctx.curve_to(420, GROUND + 160, 300, GROUND + 300, 240, 2000)
        ctx.line_to(760, 2000)
        ctx.curve_to(640, GROUND + 300, 600, GROUND + 160, 560, GROUND)
        ctx.close_path()
        paint(ctx, "#e9cf9a" if tod != "night" else "#7a6e5a", w=5)
    for i in range(30):                                                     # grass tufts
        gx, gy = (i * 173) % (W + 200) - 100, GROUND + 60 + (i * 97) % 380
        for a in (-0.4, 0, 0.4):
            line(ctx, [(gx, gy), (gx + 22 * math.sin(a), gy - 30)], w=5, col="#5fa85a" if tod != "night" else "#2d4d36")


def tree(ctx, x, y, s=1.0, tod="day"):
    rr(ctx, x - 22 * s, y - 220 * s, 44 * s, 230 * s, 12, fill="#a86a3c")
    col = {"night": "#2f5a43", "dusk": "#5f8f52"}.get(tod, "#6cc48a")
    for dx, dy, r in ((0, -300, 120), (-80, -240, 90), (80, -240, 90), (0, -200, 100)):
        ell(ctx, x + dx * s, y + dy * s, r * s, r * 0.9 * s, fill=col)


def farmhouse(ctx, x, y, t, tod="day"):
    lit = tod in ("night", "dusk")
    rr(ctx, x - 170, y - 230, 340, 230, 6, fill="#fff3dd")
    poly(ctx, [(x - 200, y - 220), (x, y - 380), (x + 200, y - 220)], fill="#e85d5d")
    rr(ctx, x + 80, y - 360, 40, 80, 4, fill="#b0705c")
    for i in range(3):                                                      # chimney smoke
        ph = (t * 0.25 + i / 3) % 1
        ell(ctx, x + 100 + 30 * ph + 10 * math.sin(t + i), y - 380 - 160 * ph, 18 + 26 * ph, 18 + 26 * ph,
            fill="#ffffff", w=0, alpha=0.7 * (1 - ph))
    rr(ctx, x - 30, y - 120, 60, 120, 8, fill="#c98a45")
    for wx in (-115, 75):
        rr(ctx, x + wx, y - 170, 60, 60, 6, fill="#ffd77a" if lit else "#bfe3f5")
        line(ctx, [(x + wx + 30, y - 170), (x + wx + 30, y - 110)], w=4)


def fence(ctx, x0, x1, y):
    for x in range(int(x0), int(x1), 70):
        rr(ctx, x - 8, y - 90, 16, 100, 4, fill="#fff3dd", w=5)
    rr(ctx, x0 - 20, y - 70, x1 - x0, 14, 4, fill="#fff3dd", w=5)
    rr(ctx, x0 - 20, y - 36, x1 - x0, 14, 4, fill="#fff3dd", w=5)


def hen(ctx, x, y, t, s=1.0, col="#ffffff", peck_phase=0.0, face=1):
    peck = max(0.0, math.sin(t * 3 + peck_phase)) ** 6
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s * face, s)
    poly(ctx, [(-60, -60), (-100, -110), (-90, -50)], fill=col)                     # tail
    ell(ctx, 0, -50, 70, 50, fill=col)
    arc_line(ctx, -10, -55, 34, 0.3, 2.4, w=5, col="#d9d2c4" if col == "#ffffff" else "#a0642e")   # wing
    hx, hy = 52, -110 + 50 * peck
    ell(ctx, hx, hy, 30, 30, fill=col)
    for k in range(3):
        ell(ctx, hx - 12 + k * 12, hy - 30, 9, 11, fill="#e04848", w=4)            # comb
    poly(ctx, [(hx + 26, hy - 4), (hx + 46, hy + 4), (hx + 26, hy + 10)], fill="#ffb02e", w=4)
    ell(ctx, hx + 26, hy + 18, 6, 9, fill="#e04848", w=3)
    ell(ctx, hx + 8, hy - 6, 4, 5, fill="#2a1d17", w=0)
    for k in (-1, 1):
        line(ctx, [(k * 18, -6), (k * 18, 18)], w=6, col="#ffb02e")
    ctx.restore()


def coop(ctx, x, y):
    rr(ctx, x - 160, y - 260, 320, 260, 8, fill="#d99a5b")
    for k in range(1, 6):
        line(ctx, [(x - 160, y - 260 + k * 44), (x + 160, y - 260 + k * 44)], w=3, col="#b97a3f")
    poly(ctx, [(x - 190, y - 250), (x, y - 360), (x + 190, y - 250)], fill="#6aa5c9")
    rr(ctx, x - 90, y - 210, 180, 90, 10, fill="#5a3a22")                          # nest box opening
    ell(ctx, x, y - 130, 80, 20, fill="#f2d38a", w=4)                              # straw
    poly(ctx, [(x + 120, y), (x + 260, y + 40), (x + 260, y + 60), (x + 120, y + 20)], fill="#c98a45", w=5)


def basket(ctx, x, y, eggs=0):
    """Wicker basket held at (x, y) (its handle top)."""
    arc_line(ctx, x, y + 70, 62, math.pi, 2 * math.pi, w=16, col="#c98a45")
    arc_line(ctx, x, y + 70, 62, math.pi, 2 * math.pi, w=4)
    for i in range(eggs):
        ell(ctx, x - 40 + i * 26, y + 66 - (i % 2) * 6, 16, 20, fill=C["cream"], w=5)
    ctx.move_to(x - 80, y + 70)
    ctx.line_to(x + 80, y + 70)
    ctx.line_to(x + 64, y + 150)
    ctx.line_to(x - 64, y + 150)
    ctx.close_path()
    paint(ctx, "#e0a964")
    for k in range(1, 4):
        line(ctx, [(x - 78 + k * 3, y + 70 + k * 20), (x + 78 - k * 3, y + 70 + k * 20)], w=4, col="#b97a3f")


def campfire(ctx, x, y, t, size=1.0, glow=True):
    if glow and size > 0.05:
        g = cairo.RadialGradient(x, y - 60, 10, x, y - 60, 520 * size)
        g.add_color_stop_rgba(0, 1, 0.75, 0.35, 0.45)
        g.add_color_stop_rgba(1, 1, 0.75, 0.35, 0)
        ctx.set_source(g)
        ctx.paint()
    for a in (-0.5, 0.5):                                                             # logs
        ctx.save()
        ctx.translate(x, y - 10)
        ctx.rotate(a)
        rr(ctx, -110, -18, 220, 36, 16, fill="#8a5232")
        ctx.restore()
    if size > 0.02:
        for k, (col, sc) in enumerate((("#e85d3a", 1.0), ("#ff9a3c", 0.72), ("#ffd166", 0.45))):
            for j in (-1, 0, 1):
                f = math.sin(t * 9 + j * 2 + k) * 0.12 + math.sin(t * 13.7 + j) * 0.08
                hgt = (170 - abs(j) * 50) * sc * size * (1 + f)
                bx = x + j * 44 * sc
                ctx.move_to(bx - 40 * sc * size, y - 20)
                ctx.curve_to(bx - 50 * sc * size, y - 20 - hgt * 0.5, bx + 10 * f * 100, y - 20 - hgt * 0.8, bx, y - 20 - hgt)
                ctx.curve_to(bx + 30 * sc * size, y - 20 - hgt * 0.6, bx + 50 * sc * size, y - 40, bx + 40 * sc * size, y - 20)
                ctx.close_path()
                paint(ctx, col, w=5 if k == 0 else 0)
        for i in range(6):                                                            # sparks
            ph = (t * 0.7 + i / 6) % 1
            ell(ctx, x + 60 * math.sin(i * 2.3 + t), y - 120 - 260 * ph * size, 4, 4, fill="#ffd166", w=0, alpha=1 - ph)
    for k in range(9):                                                                # stone ring
        a = math.pi * (0.05 + 0.9 * k / 8)
        ell(ctx, x - 150 * math.cos(a), y + 10 + 18 * math.sin(a), 34, 22, fill="#b9b3a8", w=5)


def log_seat(ctx, x, y, w=420):
    rr(ctx, x - w / 2, y - 80, w, 90, 40, fill="#a86a3c")
    ell(ctx, x + w / 2 - 30, y - 35, 34, 44, fill="#e0b27a", w=6)
    arc_line(ctx, x + w / 2 - 30, y - 35, 16, 0, 2 * math.pi, w=4, col="#b97a3f")


def fireflies(ctx, t, n=10):
    for i in range(n):
        fx = (i * 211 + 40 * math.sin(t * 0.6 + i)) % W
        fy = 900 + (i * 97) % 500 + 30 * math.sin(t * 0.9 + i * 1.7)
        a = 0.5 + 0.5 * math.sin(t * 3 + i * 2)
        ell(ctx, fx, fy, 16, 16, fill="#fff1a0", w=0, alpha=0.25 * a)
        ell(ctx, fx, fy, 5, 5, fill="#fff6c0", w=0, alpha=a)


# ------------------------------------------------------------------ timing helpers
def step_phase(t, hits):
    """Walking phase: each footstep in the recording is a foot landing (phase advances by pi per step)."""
    if not hits:
        return t * math.pi * 2
    if t <= hits[0]:
        return math.pi * (t - hits[0]) / 0.45
    for i in range(len(hits) - 1):
        if hits[i] <= t < hits[i + 1]:
            return math.pi * (i + (t - hits[i]) / (hits[i + 1] - hits[i]))
    return math.pi * (len(hits) - 1 + (t - hits[-1]) / 0.45)


def swing(t, hits, up=0.45):
    """0 = resting/struck, 1 = raised: rises before each hit and slams down exactly on it."""
    nxt = next((h for h in hits if h >= t), None)
    if nxt is None:
        return 0.0
    d = nxt - t
    return ease(1 - d / up) if d < up else 1.0 if d < up + 0.35 else ease((up + 0.7 - d) / 0.35) if d < up + 0.7 else 0.0


# ------------------------------------------------------------------ shots
def build(lib):
    steps = load(lib, "gravel_1")
    axe = load(lib, "axe_2")
    egg = load(lib, "egg_1")
    step_hits = [t for t in onsets(steps, 0.3, 0.25) if 0.2 < t < 6.0] or list(np.arange(0.4, 6.0, 0.5))
    axe_hits = [t for t in onsets(axe, 1.0, 0.35) if 1.0 < t < 6.8][:4] or [1.6, 3.4, 5.2]
    egg_hits = [t for t in onsets(egg, 0.5, 0.45) if 0.6 < t < 4.0][:2] or [1.2, 2.6]
    print("steps", len(step_hits), "| axe", [round(x, 2) for x in axe_hits], "| eggs", [round(x, 2) for x in egg_hits])
    S = []

    def add(dur, draw, cam0, cam1, sounds=(), cap=None, tod="day"):
        S.append(dict(dur=dur, draw=draw, cam0=cam0, cam1=cam1, sounds=list(sounds), cap=cap, tod=tod))

    GN = GROUND - 520                                                               # her neck when standing

    def land(ctx, t, tod, house=True, path=True):
        sky(ctx, t, tod)
        hills(ctx, tod)
        if house:
            farmhouse(ctx, 800, GROUND - 40, t, tod)
            fence(ctx, 560, 1080, GROUND)
        tree(ctx, 120, GROUND - 10, 1.1, tod)
        ground(ctx, tod, path)

    # 1. dawn over the homestead, the rooster crows
    def s1(ctx, t):
        land(ctx, t, "dawn")
        hen(ctx, 330, GROUND + 140, t, 1.0, col="#c46a2e", face=1)
    add(5.5, s1, (1.0, 540, 1050), (1.12, 560, 1060), [("rooster_3", 0.4, 0, 5.0, 0.9), ("birds_2", 0, 0, 5.5, 0.5)],
        cap="a day on the homestead", tod="dawn")

    # 2. walking out along the path with her basket (every footstep in the recording is a foot landing)
    def s2(ctx, t):
        land(ctx, t, "day")
        x = lerp(160, 760, t / 6.0)
        ph = step_phase(t, step_hits)
        K.girl(ctx, x, GN + 160, t, hands={"left": (x - 120, GN + 330), "right": (x + 110, GN + 360)},
               props={"right": lambda c, hx, hy: basket(c, hx - 4, hy - 10)}, hat=True, legs=True, step=ph,
               tilt=3 * math.sin(ph))
    add(6.0, s2, (0.95, 540, 1080), (0.95, 540, 1080), [("gravel_1", 0, 0, 6.0, 0.9), ("birds_3", 0, 0, 6.0, 0.35)])

    # 3. the chicken coop: hens pecking, she collects eggs into the basket
    def s3(ctx, t):
        sky(ctx, t, "day")
        hills(ctx, "day")
        ground(ctx, "day", path=False)
        coop(ctx, 720, GROUND + 40)
        eggs = min(4, int(max(0, t - 1.0) / 1.2) + (1 if t > 1.0 else 0))
        reach = (math.sin(max(0, t - 1.0) / 1.2 * math.pi * 2 - math.pi / 2) + 1) / 2
        hx, hy = lerp(560, 690, reach), lerp(GN + 340, GN + 300, reach)
        K.girl(ctx, 430, GN + 170, t, hands={"left": (330, GN + 360), "right": (hx, hy)},
               props={"left": lambda c, x_, y_: basket(c, x_ + 10, y_ - 10, eggs)}, hat=True, legs=True, tilt=8 * reach)
        for i, (hx_, col, ph, fc) in enumerate(((250, "#ffffff", 0.0, 1), (560, "#c46a2e", 1.7, -1), (880, "#ffffff", 3.1, -1))):
            hen(ctx, hx_, GROUND + 150 + (i % 2) * 60, t, 0.9, col=col, peck_phase=ph, face=fc)
    add(7.0, s3, (1.05, 560, 1180), (1.15, 560, 1150), [("chickens_1", 0, 0, 7.0, 0.9)])

    # 4. splitting firewood: the axe lands on every chop in the recording
    def s4(ctx, t):
        sky(ctx, t, "day")
        hills(ctx, "day")
        tree(ctx, 900, GROUND - 10, 1.0)
        ground(ctx, "day", path=False)
        done = sum(1 for h in axe_hits if h <= t)
        for i in range(done):                                                          # split pile
            rr(ctx, 700 + (i % 3) * 70, GROUND + 160 - (i // 3) * 40, 60, 36, 10, fill="#d9a05b")
        u = swing(t, axe_hits)
        cx = 440
        hx, hy = lerp(cx + 30, cx + 10, u), lerp(GROUND + 60, GN - 70, u)

        def axe_prop(c, x, y):
            ang = lerp(0.15, -2.6, u)
            c.save()
            c.translate(x, y)
            c.rotate(ang)
            rr(c, -10, -10, 20, 200, 8, fill="#c98a45", w=5)
            c.move_to(-10, 150)
            c.line_to(-70, 140)
            c.curve_to(-90, 170, -90, 200, -70, 220)
            c.line_to(-10, 205)
            c.close_path()
            paint(c, "#c9ced6", w=5)
            c.restore()
        K.girl(ctx, cx - 120, GN + 170, t, hands={"left": (hx - 14, hy + 10), "right": (hx, hy)},
               props={"right": axe_prop}, hat=True, legs=True, tilt=-6 * u, mouth="o" if u < 0.1 and done else "smile")
        rr(ctx, cx - 60, GROUND + 120, 150, 110, 20, fill="#a86a3c")                     # stump
        ell(ctx, cx + 15, GROUND + 120, 75, 18, fill="#e0b27a", w=6)
        nxt = next((h for h in axe_hits if h >= t), None)
        if nxt is not None or t < axe_hits[-1] + 0.3:                                    # log on the stump
            split = min(1.0, (t - max([h for h in axe_hits if h <= t], default=-9)) / 0.3)
            if split < 1:
                for sg in (-1, 1):
                    rr(ctx, cx + 15 + sg * (14 + 60 * split) - 28, GROUND + 30 - 30 * split, 56, 90, 14, fill="#d9a05b")
            else:
                rr(ctx, cx + 15 - 40, GROUND + 30, 80, 90, 18, fill="#d9a05b")
                ell(ctx, cx + 15, GROUND + 30, 40, 12, fill="#f0c48a", w=5)
    add(7.0, s4, (1.05, 520, 1150), (1.12, 520, 1140), [("axe_2", 0, 0, 7.0, 1.0)])

    # 5. lighting the campfire: kindling first, then the fire takes
    def s5(ctx, t):
        sky(ctx, t, "day")
        hills(ctx, "day")
        ground(ctx, "day", path=False)
        feed = (math.sin(t * 1.6 - 1.2) + 1) / 2                                           # tossing twigs in
        hx, hy = lerp(470, 520, feed), lerp(GN + 330, GN + 460, feed)

        def twig(c, x, y):
            if feed < 0.85:
                line(c, [(x - 10, y - 30), (x + 40, y + 40)], w=12, col="#8a5232")
        K.girl(ctx, 360, GN + 230, t, hands={"left": (270, GN + 380), "right": (hx, hy)}, props={"right": twig},
               hat=True, tilt=8 * feed)
        log_seat(ctx, 300, GROUND + 140, 380)
        campfire(ctx, 600, GROUND + 260, t, size=ease((t - 0.6) / 3.5) * 1.0)
    add(6.0, s5, (1.15, 500, 1330), (1.22, 520, 1340), [("campfire_3", 0, 0, 3.5, 0.9), ("campfire_1", 2.8, 2.0, 3.2, 0.9)])

    # 6. water from the stream
    def s6(ctx, t):
        sky(ctx, t, "day")
        hills(ctx, "day")
        ground(ctx, "day", path=False)
        dip = math.sin(min(1, t / 4.5) * math.pi)
        hy = lerp(GN + 470, GN + 640, dip)
        hands = K.girl(ctx, 440, GN + 380, t, hands={"left": (400, hy), "right": (500, hy)}, hat=True, tilt=12 * dip)
        rr(ctx, -200, GROUND + 70, 1500, 140, 40, fill="#8cc78f", w=6)                     # her bank
        for i in range(14):
            gx = i * 85
            for a in (-0.4, 0, 0.4):
                line(ctx, [(gx, GROUND + 80), (gx + 22 * math.sin(a), GROUND + 48)], w=5, col="#5fa85a")
        ctx.move_to(-200, GROUND + 160)                                                   # the stream in front
        ctx.curve_to(300, GROUND + 140, 700, GROUND + 200, 1300, GROUND + 160)
        ctx.line_to(1300, GROUND + 520)
        ctx.curve_to(700, GROUND + 560, 300, GROUND + 480, -200, GROUND + 520)
        ctx.close_path()
        paint(ctx, "#7cc6e8")
        bx, by = (hands["left"][0] + hands["right"][0]) / 2, hands["right"][1]           # the bucket, dipped in
        rr(ctx, bx - 60, by - 10, 120, 100, 16, fill="#9aa5ad")
        arc_line(ctx, bx, by - 10, 56, math.pi, 2 * math.pi, w=6)
        if dip > 0.5:
            ctx.save()
            ctx.rectangle(-200, GROUND + 175, 1500, 400)
            ctx.clip()
            rr(ctx, bx - 60, by - 10, 120, 100, 16, fill="#6fb8dc")                         # under the water line
            ctx.restore()
            for k in range(3):
                ell(ctx, bx, GROUND + 182, 70 + 30 * k + 10 * math.sin(t * 6), 10 + 4 * k, fill=None, w=3, alpha=0.6)
        for i in range(10):
            ph = (t * 0.5 + i / 10) % 1
            wx = -100 + ph * 1300
            line(ctx, [(wx, GROUND + 250 + (i % 3) * 60), (wx + 60, GROUND + 248 + (i % 3) * 60)], w=5, col="#ffffff", alpha=0.8)
        for k, rx in enumerate((150, 780, 960)):                                         # stones
            ell(ctx, rx, GROUND + 210 + k * 70, 60, 34, fill="#b9b3a8", w=5)
    add(6.0, s6, (1.1, 520, 1300), (1.2, 520, 1290), [("stream_1", 0, 0, 6.0, 0.85), ("bucket_3", 4.4, 0.0, 1.6, 0.6)])

    # 7. eggs into the cast-iron skillet over the fire
    def skillet(ctx, t, eggs_in):
        rr(ctx, 380, GROUND + 60, 360, 14, 6, fill="#5a5a5a", w=5)                         # grate
        for gx in (400, 720):
            line(ctx, [(gx, GROUND + 70), (gx, GROUND + 200)], w=8, col="#5a5a5a")
        rr(ctx, 440, GROUND + 10, 240, 52, 22, fill="#2f2f2f")
        line(ctx, [(680, GROUND + 30), (800, GROUND + 6)], w=20, col="#2f2f2f")
        ell(ctx, 560, GROUND + 12, 116, 18, fill="#3d3d3d", w=5)
        for i in range(eggs_in):
            ell(ctx, 520 + i * 80, GROUND + 12, 44, 12, fill="#ffffff", w=4)
            ell(ctx, 520 + i * 80, GROUND + 8, 15, 9, fill="#ffb21a", w=3)
        if eggs_in:
            steam(ctx, 560, GROUND - 20, t, n=3, h=140, alpha=0.5)

    def s7(ctx, t):
        sky(ctx, t, "day")
        hills(ctx, "day")
        ground(ctx, "day", path=False)
        eggs_in = sum(1 for h in egg_hits if t >= h + 0.4)
        cur = next((h for h in egg_hits if t < h + 0.4), None)
        r = (650, GN + 330)
        if cur is not None and t > cur - 0.9:
            r = (lerp(660, 600, ease((t - cur + 0.9) / 0.7)), GN + 360 + (10 if abs(t - cur) < 0.08 else 0))
        K.girl(ctx, 470, GN + 200, t, hands={"left": (360, GN + 360), "right": r},
               props={"right": lambda c, x, y: ell(c, x, y - 30, 26, 32, fill=C["cream"]) if cur is not None and t < cur + 0.2 else None},
               hat=True, tilt=-5)
        campfire(ctx, 560, GROUND + 230, t, size=0.75)
        skillet(ctx, t, eggs_in)
    add(6.5, s7, (1.5, 560, 1330), (1.6, 560, 1320), [("egg_1", 0, 0, 4.0, 1.0), ("fry_egg_2", 3.0, 1.0, 3.5, 0.9),
                                                       ("campfire_1", 0, 5.0, 6.5, 0.35)])

    # 8. stew in a pot hanging from a tripod, stirred with a wooden spoon
    def s8(ctx, t):
        sky(ctx, t, "dusk")
        hills(ctx, "dusk")
        ground(ctx, "dusk", path=False)
        a = t * 3.2
        sx, sy = 600 + 40 * math.cos(a), GN + 330 + 12 * math.sin(a)

        def spoon(c, x, y):
            line(c, [(x, y), (x - 20, y + 150)], w=14, col="#c98a45")
            ell(c, x - 22, y + 158, 18, 12, fill="#c98a45", w=5)
        K.girl(ctx, 420, GN + 200, t, hands={"left": (330, GN + 380), "right": (sx, sy)}, props={"right": spoon}, hat=True, tilt=-6)
        for x0, x1 in ((420, 600), (800, 600), (600, 620)):                                 # tripod
            line(ctx, [(x0, GROUND + 230), (x1, GROUND - 230)], w=14, col="#8a5232")
        line(ctx, [(600, GROUND - 230), (600, GROUND - 60)], w=5, col="#5a5a5a")
        campfire(ctx, 600, GROUND + 230, t, size=0.6)
        ctx.move_to(500, GROUND - 60)                                                       # the pot
        ctx.curve_to(500, GROUND + 70, 700, GROUND + 70, 700, GROUND - 60)
        ctx.close_path()
        paint(ctx, "#2f2f2f")
        ell(ctx, 600, GROUND - 60, 100, 20, fill="#c8743a", w=6)
        for k in range(4):
            ph = (t * 1.5 + k * 0.3) % 1
            ell(ctx, 560 + k * 26, GROUND - 60, 8 * (1 - ph), 5 * (1 - ph), fill="#e89a5a", w=0)
        steam(ctx, 600, GROUND - 90, t, n=3, h=180, alpha=0.6)
    add(6.5, s8, (1.35, 580, 1260), (1.45, 590, 1250), [("simmer_1", 0, 3.0, 6.5, 0.8), ("stir_3", 0, 0, 6.5, 0.45),
                                                         ("campfire_1", 0, 9.0, 6.5, 0.35)], tod="dusk")

    # 9. dinner on a log by the fire, the cat curled up, wind in the trees
    def s9(ctx, t):
        sky(ctx, t, "dusk")
        hills(ctx, "dusk")
        tree(ctx, 920, GROUND - 10, 1.1, "dusk")
        ground(ctx, "dusk", path=False)
        sip = ease((t - 2.0) / 0.6) * (1 - ease((t - 4.5) / 0.6))
        by = lerp(GN + 420, GN + 300, sip)

        def bowl(c, x, y):
            c.move_to(x - 70, y)
            c.curve_to(x - 66, y + 60, x + 66, y + 60, x + 70, y)
            c.close_path()
            paint(c, "#f3efe8")
            ell(c, x, y, 70, 14, fill="#c8743a", w=5)
            steam(c, x, y - 20, t, n=2, h=110, alpha=0.6)
        K.girl(ctx, 330, GN + 260, t, hands={"left": (270, by + 30), "right": (390, by + 30)},
               props={"right": lambda c, x, y: bowl(c, x - 60, y - 16)}, hat=True, mouth="o" if sip > 0.6 else "smile",
               tilt=-4 + 6 * sip)
        log_seat(ctx, 330, GROUND + 160, 440)
        campfire(ctx, 700, GROUND + 260, t, size=0.85)
        cat_curled(ctx, 900, GROUND + 300, t, 0.8, purr=0.6)
    add(7.5, s9, (1.0, 540, 1180), (1.08, 540, 1170), [("campfire_1", 0, 12.0, 7.5, 0.8), ("wind_leaves_2", 0, 0, 7.5, 0.35)],
        cap="slow evenings", tod="dusk")

    # 10. night: stars, fireflies, frogs and crickets
    def s10(ctx, t):
        sky(ctx, t, "night")
        hills(ctx, "night")
        farmhouse(ctx, 820, GROUND - 40, t, "night")
        tree(ctx, 120, GROUND - 10, 1.1, "night")
        ground(ctx, "night", path=False)
        K.girl(ctx, 380, GN + 300, t * 0.4, hands={"left": (330, GN + 470), "right": (430, GN + 470)}, eyes="sleep",
               hat=True, tilt=12)
        log_seat(ctx, 380, GROUND + 200, 440)
        campfire(ctx, 760, GROUND + 300, t, size=0.35)
        cat_curled(ctx, 560, GROUND + 330, t, 0.75)
        fireflies(ctx, t)
        zzz(ctx, 520, GN + 60, t)
    add(6.5, s10, (1.0, 540, 1150), (1.1, 560, 1170), [("frogs_2", 0, 0, 6.5, 0.6), ("crickets_1", 0, 0, 6.5, 0.6),
                                                        ("campfire_1", 0, 15.0, 4.6, 0.25)], cap="goodnight", tod="night")
    return S


def ambience(lib, S, n):
    """Birds through the day (two recordings back to back), fading out at dusk."""
    birds = np.concatenate([load(lib, "birds_1"), load(lib, "birds_3"), load(lib, "birds_1")])
    bed = np.zeros((n, 2), np.float32)
    L = min(len(birds), n)
    bed[:L] = birds[:L]
    dusk = S[7]["t0"]
    k = 1 - np.clip((np.arange(n) / SR - dusk) / 3.0, 0, 1)
    return bed * (0.18 * k)[:, None]


if __name__ == "__main__":
    lib = sys.argv[1]
    K.render(lib, sys.argv[2] if len(sys.argv) > 2 else "homestead_day.mp4", build(lib), ambience)
