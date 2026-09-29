"""'A day in my life (as a cartoon)': her chibi girl in every shot, doing normal day stuff (1080x1920, ~70 s).

    python chibi/video_day.py out.mp4

She wakes up in bed (lying down), jumps out, stretches, sips coffee, eats a donut (bites come out of it), answers a
phone call, jumps for joy, hop-walks down the street waving, sits at her laptop, reacts, lies in bed on her phone and
ends with a wink. The rig does the arms (IK to her mouth / ear), hands from the hands sheets hold props
(chibi_props.py), and the whole character is moved, turned and squashed per frame (lying down, jumping).
Scenes are drawn with the skits' cairo kit; the camera cuts between wide shots, close-ups and inserts.
Script: day_lines.py. Sound: her voice (VOICE), the caller through a phone filter, Kenney CC0 + synth effects.
"""
import math
import os
import subprocess
import sys
import tempfile

import cairocffi as cairo
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SKITS = os.path.join(HERE, "..", "skits")
sys.path[:0] = [HERE, SKITS]
import chibi_expressions as X                            # noqa: E402
import chibi_props as P                                  # noqa: E402
import video_321 as V                                    # noqa: E402
import voices                                            # noqa: E402
from day_lines import CALLER, LINES, VOICE               # noqa: E402
from demo_hands2 import reach                            # noqa: E402
from five_min import ogg, synth                          # noqa: E402
from toon import OUT, ellipse, lin, poly, rad, rgb, rrect, text   # noqa: E402

W, H, FPS, SR = 1080, 1920, 24, voices.SR
FLOOR = 1560
UNIT = 1.45                     # world pixels per drawing unit of her rig (she is ~1100 px tall)
PIV = (188.1, 600.0)            # the rig point she is moved / turned around (her chest)
FEET = 970.0                    # rig y of her soles
F800 = os.path.join(SKITS, "assets", "poppins-800.ttf")
F600 = os.path.join(SKITS, "assets", "poppins-600.ttf")
PINK = (232, 84, 132)


def ease(t):
    return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, t)))


def lerp(a, b, k):
    return a + (b - a) * k


# ------------------------------------------------------------------ poses (arm angles; IK where a hand must land somewhere)
def _r(side, at, d, hand):
    return reach(side, at, d, hand=hand)[:4]


POSES = {
    "rest": {},
    "stretch": {"right": (100, 15, 0, "fist"), "left": (-100, -15, 0, "fist")},
    "chest": {"right": _r("right", (120, 610), (0.35, -1), "c_grip")},          # holding something at her chest
    "sip": {"right": _r("right", (110, 530), (0.2, -1), "c_grip")},             # mug at her lips
    "bite": {"right": _r("right", (125, 520), (0.0, -1), "c_grip")},            # donut at her mouth
    "ear": {"right": _r("right", (135, 505), (-1, -0.4), "c_grip")},            # phone at her ear
    "ear_wait": {"right": _r("right", (135, 505), (-1, -0.4), "c_grip"), "left": (-30, -130, -10, "index_up")},
    "yay": {"right": (120, 40, 0, "open"), "left": (-120, -40, 0, "open")},
    "hip_wave": {"right": _r("right", (112, 640), (0.12, 1), "hip_flat"), "left": (-35, -130, 12, "open")},
    "thumbs": {"right": (30, 120, 70, "thumbs_up")},
    "cheeks": {"right": _r("right", (115, 500), (0.1, -1), "cover_mouth"),
               "left": _r("left", (261, 500), (-0.1, -1), "cover_mouth")},
    "shrug": {"right": (20, 85, 35, "palm_up"), "left": (-20, -85, -35, "palm_up")},
    "peace": {"left": (-35, -130, 10, "two")},
    "look_phone": {"left": _r("left", (290, 480), (1, 0.3), "c_grip")},
}


def blend(a, b, k, props=None):
    """Arms between pose a and pose b (k: 0..1). props: {side: prop} for whichever hand ends up holding it."""
    out = {}
    for side in ("right", "left"):
        pa, pb = POSES[a].get(side, (0, 0, 0, None)), POSES[b].get(side, (0, 0, 0, None))
        ang = [lerp(x, y, k) for x, y in zip(pa[:3], pb[:3])]
        hand = pb[3] if (k > 0.5 or pa[3] is None) and (k > 0.25 or pb[3] is None) else pa[3]
        if pb[3] is None and k > 0.75:
            hand = None
        prop = (props or {}).get(side) if hand in ("c_grip",) else None
        out[side] = tuple(ang) + (hand, prop)
    return out


def moves(t, steps, props=None):
    """steps: [(time, pose), ...]: hold each pose, move to the next over 0.35 s before its time."""
    cur = steps[0][1]
    for (t0, p0), (t1, p1) in zip(steps, steps[1:]):
        if t >= t1:
            cur = p1
            continue
        k = ease((t - (t1 - 0.35)) / 0.35)
        return blend(p0, p1, k, props)
    return blend(cur, cur, 1, props)


# ------------------------------------------------------------------ scenes (world coordinates, cairo)
def bedroom(ctx, t, night=False, ring=False, clock="7:00"):
    ctx.rectangle(-3000, -3000, W + 6000, FLOOR + 3000)
    ctx.set_source(lin(ctx, 0, 0, 0, FLOOR, [(0, "#27305f"), (1, "#3b3f7a")] if night else [(0, "#ffe6d6"), (1, "#ffc8c4")]))
    ctx.fill()
    ctx.rectangle(-3000, FLOOR, W + 6000, 3000)
    ctx.set_source_rgb(*rgb("#40385a" if night else "#d9a47c"))
    ctx.fill()
    for x in range(-600, W + 600, 160):
        poly(ctx, [(x, FLOOR), (x - 60, FLOOR + 400)], line="#352e4c" if night else "#c48f69", w=4, close=False)
    sky = [(0, "#0e1233"), (1, "#2c336e")] if night else [(0, "#8fd3ff"), (1, "#e8f7ff")]
    rrect(ctx, 580, 380, 360, 420, 18, fill=lin(ctx, 0, 380, 0, 800, sky), w=10)
    if night:
        ellipse(ctx, 830, 480, 46, 46, fill="#f5f1c8", line=None)
        ellipse(ctx, 850, 466, 42, 42, fill="#161c4a", line=None)
        for sx, sy in ((640, 450), (700, 560), (880, 640), (620, 700)):
            ellipse(ctx, sx, sy, 5, 5, fill="#fff6c8", line=None)
    else:
        ellipse(ctx, 840, 480, 58, 58, fill="#ffd45e", w=6)
        for cx, cy in ((680, 620), (760, 640)):
            ellipse(ctx, cx, cy, 70, 34, fill=(1, 1, 1), line=None)
    poly(ctx, [(760, 380), (760, 800)], w=8, close=False)
    poly(ctx, [(580, 590), (940, 590)], w=8, close=False)
    rrect(ctx, 90, 470, 230, 290, 10, fill="#2f2a44" if night else "#ff9fbf", w=8)            # poster
    text(ctx, "GOOD", 205, 570, 44, F800, col=(1, 1, 1))
    text(ctx, "VIBES", 205, 630, 44, F800, col=(1, 1, 1))
    rrect(ctx, 250, 1020, 70, 540, 16, fill="#5b4a8a" if night else "#b06a8a", w=8)          # headboard
    rrect(ctx, 270, 1300, 820, 130, 26, fill="#e9e6f2" if night else "#fbf6f0", w=8)          # mattress
    rrect(ctx, 270, 1420, 820, 140, 10, fill="#6a58a0" if night else "#e58fa8", w=8)          # frame
    ellipse(ctx, 420, 1286, 150, 56, fill=(1, 1, 1), w=7)                                     # pillow
    rrect(ctx, 40, 1330, 190, 230, 10, fill="#7b62a8" if night else "#c98f6e", w=8)          # nightstand
    alarm_clock(ctx, 135, 1270, t, ring, clock, night)


def alarm_clock(ctx, x, y, t, ring, clock, night):
    if ring:
        x += 7 * math.sin(t * 80)
        for k in (-1, 1):                                                             # ring lines
            for i in range(3):
                a = math.radians(-60 + 60 * i) if k > 0 else math.radians(-120 - 60 * i)
                poly(ctx, [(x + 95 * math.cos(a), y - 40 + 95 * math.sin(a)),
                           (x + 125 * math.cos(a), y - 40 + 125 * math.sin(a))], w=6, close=False)
    for bx in (-42, 42):
        ellipse(ctx, x + bx, y - 62, 20, 16, fill="#ffd45e", w=5)
    rrect(ctx, x - 70, y - 58, 140, 110, 30, fill="#ff8fb0", w=7)
    rrect(ctx, x - 52, y - 40, 104, 70, 12, fill="#23262e", w=5)
    text(ctx, clock, x, y - 5, 36, F800, col="#ff6b6b")
    for lx in (-40, 40):
        poly(ctx, [(x + lx, y + 50), (x + lx * 1.3, y + 64)], w=7, close=False)


def blanket(ctx, t, night=False, off=0.0):
    """Over her legs while she lies in bed. off: 0 = on, 1 = thrown off to the right."""
    x0 = 640 + 500 * off
    ctx.save()
    ctx.translate(x0, 1180)
    ctx.rotate(0.25 * off)
    rrect(ctx, 0, 0, 500, 270, 70, fill="#5d6fc4" if night else "#8fd0f5", w=8)
    for i in range(4):
        for j in range(2):
            ellipse(ctx, 70 + i * 110, 70 + j * 110, 16, 16, fill="#8594e0" if night else "#ffffff", line=None)
    ctx.restore()


def kitchen(ctx, t):
    ctx.rectangle(-3000, -3000, W + 6000, FLOOR + 3000)
    ctx.set_source(lin(ctx, 0, 0, 0, FLOOR, [(0, "#dff6ee"), (1, "#bfe8dc")]))
    ctx.fill()
    for y in range(860, 1180, 60):                                                   # backsplash tiles
        poly(ctx, [(-400, y), (W + 400, y)], line="#a9d9cb", w=3, close=False)
    for x in range(-400, W + 400, 90):
        for y in range(860, 1180, 120):
            poly(ctx, [(x, y), (x, y + 60)], line="#a9d9cb", w=3, close=False)
            poly(ctx, [(x + 45, y + 60), (x + 45, y + 120)], line="#a9d9cb", w=3, close=False)
    for i in range(3):                                                               # upper cabinets
        rrect(ctx, -60 + i * 200, 300, 190, 330, 14, fill="#f7c9d8", w=8)
        ellipse(ctx, 100 + i * 200, 590, 10, 10, fill="#ffffff", w=4)
    rrect(ctx, 640, 360, 360, 360, 18, fill=lin(ctx, 0, 360, 0, 720, [(0, "#8fd3ff"), (1, "#e8f7ff")]), w=10)
    ellipse(ctx, 900, 450, 50, 50, fill="#ffd45e", w=6)
    poly(ctx, [(820, 360), (820, 720)], w=8, close=False)
    rrect(ctx, 700, 660, 90, 70, 10, fill="#e58f6a", w=6)                                  # plant on the sill
    for a in (-0.6, 0, 0.6):
        ellipse(ctx, 745 + 45 * math.sin(a), 620 - 30 * math.cos(a), 22, 38, fill="#6cc48a", w=5)


def counter(ctx, t, phone=None):
    """Kitchen counter in front of her (hides her legs). phone: None, "buzz" or "still" = phone lying on it."""
    rrect(ctx, 840, 990, 150, 190, 18, fill="#3a3f4a", w=8)                              # coffee maker
    rrect(ctx, 870, 1080, 90, 70, 8, fill="#23262e", w=5)
    ellipse(ctx, 915, 1030, 16, 16, fill="#ff6b6b", line=None)
    rrect(ctx, -60, 1170, W + 120, 64, 18, fill="#f6f1ea", w=8)
    rrect(ctx, -60, 1230, W + 120, 900, 0, fill="#f4a6c0", w=8)
    for i in range(6):
        rrect(ctx, -40 + i * 200, 1270, 180, 260, 14, fill="#f7b6cb", w=6)
        ellipse(ctx, 110 + i * 200, 1300, 9, 9, fill="#ffffff", w=4)
    if phone:
        dx = 5 * math.sin(t * 90) if phone == "buzz" else 0
        rrect(ctx, 700 + dx, 1150, 170, 34, 10, fill="#2b2f38", w=6)
        if phone == "buzz":
            for s in (-1, 1):
                poly(ctx, [(785 + s * 110, 1150), (785 + s * 135, 1120)], w=6, close=False)


def street(ctx, t, scroll=0.0):
    ctx.rectangle(-3000, -3000, W + 6000, 1480 + 3000)
    ctx.set_source(lin(ctx, 0, 0, 0, 1480, [(0, "#7cc8ff"), (1, "#dff3ff")]))
    ctx.fill()
    for i in range(-1, 5):                                                            # clouds
        cx = (i * 420 - scroll * .1) % 2100 - 300
        for dx, r in ((0, 60), (60, 46), (-60, 42)):
            ellipse(ctx, cx + dx, 380 + (i % 2) * 90, r * 1.4, r, fill=(1, 1, 1), line=None)
    cols = ("#ffc7d9", "#c9b8ff", "#ffe29a", "#a8e6cf")
    for i in range(-2, 14):                                                           # buildings
        bx = (i * 240 - scroll * .5) % 3360 - 600
        bh = 380 + (i * 97 % 5) * 90
        rrect(ctx, bx, 1480 - bh, 220, bh + 20, 10, fill=cols[i % 4], w=7)
        for wy in range(1480 - bh + 50, 1400, 110):
            for wx in (35, 125):
                rrect(ctx, bx + wx, wy, 60, 60, 8, fill="#ffffff", w=5)
    ctx.rectangle(-3000, 1480, W + 6000, 3000)
    ctx.set_source_rgb(*rgb("#c7c3d6"))
    ctx.fill()
    poly(ctx, [(-3000, 1480), (W + 3000, 1480)], w=8, close=False)
    for i in range(-2, 10):
        x = (i * 200 - scroll) % 2000 - 400
        poly(ctx, [(x, 1480), (x - 90, 1920)], line="#aaa6bb", w=5, close=False)
    for i in range(-1, 4):                                                            # trees
        x = (i * 560 - scroll * .95) % 2240 - 300
        rrect(ctx, x - 16, 1200, 32, 280, 8, fill="#9b6d4c", w=6)
        ellipse(ctx, x, 1150, 110, 100, fill="#6cc48a", w=7)


def office(ctx, t):
    ctx.rectangle(-3000, -3000, W + 6000, FLOOR + 3000)
    ctx.set_source(lin(ctx, 0, 0, 0, FLOOR, [(0, "#ece6fb"), (1, "#d6cdf3")]))
    ctx.fill()
    rrect(ctx, 60, 380, 380, 440, 16, fill=lin(ctx, 0, 380, 0, 820, [(0, "#8fd3ff"), (1, "#e8f7ff")]), w=10)
    for bx, bw, bh in ((80, 80, 200), (170, 110, 290), (290, 70, 170), (370, 60, 240)):
        rrect(ctx, bx, 820 - bh, bw, bh, 6, fill="#9fb0d8", line=None)
    poly(ctx, [(250, 380), (250, 820)], w=8, close=False)
    ellipse(ctx, 860, 480, 90, 90, fill=(1, 1, 1), w=8)                                 # wall clock
    a = t * 0.8
    poly(ctx, [(860, 480), (860 + 55 * math.sin(a), 480 - 55 * math.cos(a))], w=7, close=False)
    poly(ctx, [(860, 480), (860, 430)], w=8, close=False)
    rrect(ctx, 820, 880, 110, 130, 12, fill="#e58f6a", w=6)                              # plant
    for a in (-0.7, -0.2, 0.3, 0.8):
        ellipse(ctx, 875 + 70 * math.sin(a), 820 - 60 * math.cos(a), 30, 60, fill="#6cc48a", w=5)


def desk(ctx, t):
    """Desk + open laptop (we see its lid): she sits behind it, hands on the keys out of sight."""
    rrect(ctx, 330, 930, 420, 300, 24, fill="#dfe4ee", w=8)
    ctx.save()
    ctx.translate(540, 1070)
    ctx.move_to(0, 22)
    ctx.curve_to(-60, -20, -30, -60, 0, -28)
    ctx.curve_to(30, -60, 60, -20, 0, 22)
    ctx.set_source_rgb(*rgb("#ff8fb0"))
    ctx.fill()
    ctx.restore()
    rrect(ctx, -60, 1220, W + 120, 60, 14, fill="#d9a47c", w=8)
    rrect(ctx, -60, 1276, W + 120, 900, 0, fill="#b98560", w=8)
    rrect(ctx, 820, 1120, 110, 110, 18, fill="#ffffff", w=7)                             # mug on the desk
    rrect(ctx, 120, 1170, 160, 50, 6, fill="#ffffff", w=6)                               # papers
    rrect(ctx, 110, 1140, 160, 40, 6, fill="#fff6c8", w=6)


def outro_bg(ctx, t):
    ctx.rectangle(-3000, -3000, W + 6000, 8000)
    ctx.set_source(lin(ctx, 0, 0, 0, H, [(0, "#ffe1ec"), (1, "#ffb3cb")]))
    ctx.fill()
    for i in range(14):
        x, y = (i * 311) % W, 300 + (i * 173) % 1100
        s = 12 + 10 * (0.5 + 0.5 * math.sin(t * 3 + i))
        poly(ctx, [(x, y - s * 2), (x + s * .5, y - s * .5), (x + s * 2, y), (x + s * .5, y + s * .5), (x, y + s * 2),
                   (x - s * .5, y + s * .5), (x - s * 2, y), (x - s * .5, y - s * .5)], fill="#ffffff", line=None)
    ellipse(ctx, 540, FLOOR + 10, 300, 40, fill="#f28fb0", line=None)


def confetti(ctx, t, x0=540, y0=900):
    if t < 0:
        return
    rng = np.random.default_rng(3)
    cols = ("#ff6b9a", "#ffd45e", "#7ec8ff", "#8be0a4", "#c9a4ff")
    for i in range(70):
        vx, vy = rng.uniform(-700, 700), rng.uniform(-1500, -600)
        x, y = x0 + vx * t, y0 + vy * t + 1600 * t * t
        a = rng.uniform(0, 6) + t * rng.uniform(4, 12)
        ctx.save()
        ctx.translate(x, y)
        ctx.rotate(a)
        ctx.rectangle(-14, -7, 28, 14)
        ctx.set_source_rgb(*rgb(cols[i % 5]))
        ctx.fill()
        ctx.restore()


# ------------------------------------------------------------------ shots
def stand(x, dy=0.0, scale=1.0, sy=1.0):
    """World position of her pivot when her feet are on the floor at x (dy: lift off the floor)."""
    return (x, FLOOR - dy - (FEET - PIV[1]) * UNIT * scale * sy)


LYING = dict(pos=(700, 1250), rot=90, scale=0.7)


def shots():
    """(line key or None, lead s, dur s (beats) / tail s (lines), scene, foreground, cam0, cam1, act, sfx)
    act(t, d, ls, le) -> her state; cam = (zoom, focus x, focus y); sfx = [(name, time in shot or ("le", s))]."""
    S = []

    def add(key, lead, tail, scene, fg, cam0, cam1, act, sfx=()):
        S.append(dict(key=key, lead=lead, tail=tail, scene=scene, fg=fg, cam0=cam0, cam1=cam1, act=act, sfx=list(sfx)))

    def lying(face, eyes=None, arms=None, look=None):
        return lambda t, d, ls, le: dict(LYING, face=face, eyes=eyes, look=look, arms=arms or {}, tilt=0)

    # 1. alarm
    add(None, 0, 1.7, lambda c, t: bedroom(c, t, ring=True), lambda c, t: blanket(c, t),
        (1.0, 560, 1000), (1.12, 540, 1100), lying("calm", eyes="closed"), [("alarm", 0), ("whoosh", 0)])
    add("wake", 0, .25, lambda c, t: bedroom(c, t, ring=True), lambda c, t: blanket(c, t),
        (1.9, 520, 1230), (2.15, 510, 1235), lying("annoyed"), [("alarm", 0)])

    # 2. jump out of bed
    def jump_out(t, d, ls, le):
        k = ease(t / d)
        end = stand(760)
        return dict(pos=(lerp(700, end[0], k), lerp(1250, end[1], k) - 330 * math.sin(math.pi * min(1, t / d))),
                    rot=90 * (1 - k), scale=lerp(0.7, 1.0, k), face="surprised", arms=blend("rest", "yay", math.sin(math.pi * k)),
                    tilt=0)
    add(None, 0, 1.0, bedroom, lambda c, t: blanket(c, t, off=ease(t / .5)), (1.0, 580, 1000), (1.0, 600, 1000),
        jump_out, [("boing", 0), ("cloth", 0.05), ("thud", 0.95)])

    def stretch(t, d, ls, le):
        on = ls + 0.35 <= t <= ls + 1.9
        arms = moves(t, [(0, "rest"), (ls + 0.5, "stretch"), (ls + 1.95, "rest")])
        return dict(pos=stand(760, dy=18 * ease((t - ls - .2) / .4) * (t < ls + 1.9)), face="calm" if on else "smug",
                    mouth="oh" if on and t < ls + 1.2 else None, arms=arms, tilt=-4 if on else 3)
    add("stretch", 0.2, 0.3, bedroom, None, (1.3, 720, 930), (1.4, 730, 900), stretch, [("cloth", 0.5)])

    # 3. kitchen: coffee
    props_mug = lambda t: {"right": P.mug(t * 0.7)}

    def coffee(t, d, ls, le):
        arms = moves(t, [(0, "chest"), (0.5, "sip"), (1.25, "chest")], props_mug(t))
        sipping = 0.45 < t < 1.25
        return dict(pos=stand(540), face="calm" if sipping else "smug", eyes="closed" if sipping else None,
                    mouth="smile" if sipping else None, arms=arms, tilt=-4 if sipping else 4)
    add("coffee", 1.5, 0.3, kitchen, counter, (1.3, 540, 930), (1.45, 540, 880), coffee, [("sip", 0.55)])

    # 4. donut
    def donut(t, d, ls, le):
        bites = 1 + (t > 0.5) + (t > le + 0.5)
        props = {"right": P.donut(bites - 1)}
        arms = moves(t, [(0, "chest"), (0.45, "bite"), (1.0, "chest"), (le + 0.45, "bite"), (le + 0.9, "chest")], props)
        near = 0.3 < t < 0.8 or le + 0.3 < t < le + 0.8
        chew = (not near) and not (ls <= t <= le)
        return dict(pos=stand(540), face="happy" if t > le else "smug", arms=arms, tilt=-3 if near else 3,
                    mouth=("open" if near else ("smile" if (chew and int(t * 7) % 2) else None)))
    add("donut", 1.05, 1.0, kitchen, counter, (1.75, 560, 800), (1.85, 560, 790), donut,
        [("crunch", 0.45), ("crunch", ("le", 0.45))])

    # 5. phone call
    add(None, 0, 1.2, kitchen, lambda c, t: counter(c, t, "buzz"), (1.2, 620, 950), (1.25, 640, 950),
        lambda t, d, ls, le: dict(pos=stand(540), face="surprised", look=(2.5, 2.0), arms={}, tilt=-5), [("buzz", 0)])

    def pick_up(t, d, ls, le):
        k = ease(t / 0.45)
        arms = blend("rest", "ear", k, {"right": P.phone()})
        return dict(pos=stand(540), face="neutral" if t < ls + 1.0 else "surprised", mouth="smile", arms=arms, tilt=-6,
                    look=(-1.5, 0))
    add("caller", 0.5, 0.2, kitchen, lambda c, t: counter(c, t, "still" if t < 0.3 else None), (1.45, 560, 860),
        (1.6, 540, 830), pick_up, [("cloth", 0.1)])

    def wait(t, d, ls, le):
        arms = moves(t, [(0, "ear"), (0.3, "ear_wait")], {"right": P.phone()})
        return dict(pos=stand(540), face="surprised", arms=arms, tilt=-6)
    add("wait", 0.15, 0.25, kitchen, counter, (1.95, 540, 760), (2.1, 540, 750), wait, [("sting", 0.1)])

    def payday(t, d, ls, le):
        hop = lambda s, h, n: (h * math.sin(math.pi * (t - s) / n) if s <= t <= s + n else 0.0)
        dy = hop(0.25, 330, 0.7) + hop(1.15, 160, 0.5)
        crouch = 1 - 0.1 * (math.exp(-((t - 0.18) / 0.07) ** 2) + math.exp(-((t - 0.97) / 0.07) ** 2) +
                            math.exp(-((t - 1.67) / 0.07) ** 2))
        return dict(pos=stand(540, dy=dy, sy=crouch), sy=crouch, sx=2 - crouch, face="excited",
                    arms=blend("rest", "yay", ease(t / .3)), tilt=5 * math.sin(t * 6))
    add("payday", 0.2, 1.0, kitchen, lambda c, t: (counter(c, t), confetti(c, t - 0.3)), (1.0, 540, 950),
        (1.05, 540, 940), payday, [("boing", 0.2), ("pop", 0.3), ("thud", 0.95), ("boing", 1.1), ("thud", 1.66)])

    # 6. walking to work
    def walk(t, d, ls, le):
        step = (t / 0.34) % 1
        arms = blend("hip_wave", "hip_wave", 1)
        l = list(arms["left"])
        l[2] += 18 * math.sin(t * 11)
        arms["left"] = tuple(l)
        return dict(pos=stand(540, dy=38 * math.sin(math.pi * step)), face="smug", arms=arms,
                    tilt=4 * math.sin(math.pi * t / 0.34), rot=2.5 * math.sin(math.pi * t / 0.34))
    add("walk", 0.6, 0.7, lambda c, t: street(c, t, scroll=t * 520), None, (1.15, 540, 980), (1.25, 540, 960), walk,
        [("steps", 0)])

    # 7. office
    def at_desk(face, pose="rest", eyes=None, mouth=None, sting=False):
        def f(t, d, ls, le):
            typing = t < ls
            return dict(pos=stand(540, dy=-70 + (3 * math.sin(t * 40) if typing else 0)), face=face if t >= ls - .1 else "neutral",
                        arms=moves(t, [(0, "rest"), (ls + 0.1, pose)]) if pose != "rest" else {}, eyes=eyes, mouth=mouth,
                        tilt=-3 if face == "eye_roll" else 3, look=(0, 1.5) if typing else None)
        return f
    add("meeting", 0.9, 0.3, office, desk, (1.3, 540, 900), (1.4, 540, 880), at_desk("eye_roll"), [("typing", 0)])
    add("love", 0.1, 0.4, office, desk, (1.6, 560, 800), (1.7, 560, 790), at_desk("happy", "thumbs"), [("ding", 0.3)])

    def where(t, d, ls, le):
        return dict(pos=stand(540, dy=-70), face="surprised", arms=blend("rest", "cheeks", ease(t / .3)), tilt=0,
                    rot=1.5 * math.sin(t * 50) * max(0, 1 - t / .5))
    add("where", 0.1, 0.3, office, desk, (2.0, 540, 760), (2.1, 540, 760), where, [("sting", 0.05)])

    def target(t, d, ls, le):
        return dict(pos=stand(540, dy=-70), face="smug", arms=blend("rest", "shrug", ease((t - ls - .5) / .4)), tilt=6)
    add("target", 0.1, 0.5, office, desk, (1.3, 540, 900), (1.35, 540, 900), target)

    # 8. night
    night_arms = lambda t, d, ls, le: dict(LYING, face="neutral", look=(2.5, 0), tilt=0,
                                           arms=blend("look_phone", "look_phone", 1, {"left": P.phone()}))
    add("bed", 0.8, 0.3, lambda c, t: bedroom(c, t, night=True, clock="10:00"),
        lambda c, t: (blanket(c, t, night=True), phone_glow(c)), (1.45, 540, 1170), (1.55, 540, 1180), night_arms,
        [("crickets", 0)])
    add(None, 0, 1.3, lambda c, t: bedroom(c, t, night=True, clock="2:00"),
        lambda c, t: (blanket(c, t, night=True), phone_glow(c)), (1.2, 400, 1150), (3.4, 135, 1255),
        night_arms, [("sting", 0.7), ("crickets", 0)])
    add("twoam", 0.1, 0.4, lambda c, t: bedroom(c, t, night=True, clock="2:00"),
        lambda c, t: (blanket(c, t, night=True), phone_glow(c)), (2.0, 500, 1230), (2.2, 500, 1235),
        lambda t, d, ls, le: dict(LYING, face="sad", eyes=None, look=(0, 0), tilt=0,
                                  arms=blend("look_phone", "look_phone", 1, {"left": P.phone()})), [("crickets", 0)])

    # 9. outro
    def outro(t, d, ls, le):
        return dict(pos=stand(540, dy=10 * abs(math.sin(t * 3))), face="wink", arms=blend("rest", "peace", ease(t / .35)),
                    tilt=-5)
    add("outro", 0.2, 1.8, outro_bg, None, (1.15, 540, 960), (1.3, 540, 900), outro, [("chime", 0.2)])
    return S


def phone_glow(ctx):
    ctx.set_source(rad(ctx, 560, 1120, 260, [(0, "#bfe6ff", .35), (1, "#bfe6ff", 0)]))
    ctx.paint()


# ------------------------------------------------------------------ audio
def phone_filter(a):
    import scipy.signal as ss
    b, c = ss.butter(3, [350 / (SR / 2), 3400 / (SR / 2)], "band")
    return (np.tanh(ss.lfilter(b, c, a) * 2.2) * 0.55).astype(np.float32)


def fx(name, n=1.0):
    t = np.arange(int(n * SR)) / SR
    rng = np.random.default_rng(hash(name) % 1000)
    if name == "alarm":
        beep = (np.sin(2 * np.pi * 2100 * t) > 0) * (((t * 8) % 1) < .5) * (((t / 1.0) % 1) < .6)
        return (beep * 0.05).astype(np.float32)
    if name == "boing":
        t = t[:int(.45 * SR)]
        return (np.sin(2 * np.pi * (180 * t + 900 * t * t)) * np.exp(-t / .2) * .22).astype(np.float32)
    if name == "crunch":
        out = np.zeros(int(.45 * SR), np.float32)
        for k in range(7):
            i = int(rng.uniform(0, .35) * SR)
            m = int(.03 * SR)
            out[i:i + m] += rng.normal(0, 1, m) * np.exp(-np.arange(m) / 250) * .25
        return out
    if name == "buzz":
        on = ((t % .5) < .32)
        return (np.sign(np.sin(2 * np.pi * 150 * t)) * on * .05).astype(np.float32)
    if name == "pop":
        out = np.zeros(int(1.2 * SR), np.float32)
        for k in range(14):
            i = int(rng.uniform(0, 1.0) * SR)
            m = int(.02 * SR)
            out[i:i + m] += rng.normal(0, 1, m) * np.exp(-np.arange(m) / 90) * .18
        return out
    if name == "typing":
        out = np.zeros(int(n * SR), np.float32)
        for tt in np.arange(0, n - .05, .09):
            i = int((tt + rng.uniform(0, .03)) * SR)
            m = int(.012 * SR)
            out[i:i + m] += rng.normal(0, 1, m) * np.exp(-np.arange(m) / 60) * .12
        return out
    if name == "ding":
        t = t[:int(.6 * SR)]
        return ((np.sin(2 * np.pi * 1568 * t) + .5 * np.sin(2 * np.pi * 2352 * t)) * np.exp(-t / .2) * .08).astype(np.float32)
    if name == "crickets":
        chirp = np.sin(2 * np.pi * 4200 * t) * (((t * 14) % 1) < .35) * (((t / 1.3) % 1) < .45)
        return (chirp * .012).astype(np.float32)
    return np.zeros(len(t), np.float32)


def build():
    S = shots()
    lines = {k: (who, line) for k, who, line in LINES}
    t = 0.2
    voice = np.zeros(int(160 * SR), np.float32)
    caller = np.zeros_like(voice)
    tmp = tempfile.mkdtemp()
    for i, s in enumerate(S):
        s["t0"] = t
        if s["key"]:
            who, line = lines[s["key"]]
            spk = VOICE if who == "her" else who
            a = voices.say(spk, line)
            tone, txt = voices.split_tag(line)
            at = t + s["lead"]
            if who == "her":
                p = os.path.join(tmp, f"{i}.wav")
                sf.write(p, a, SR)
                s["cues"] = [(at + c0, c) for c0, c in V.mouth_cues(p, txt)]
                voice[int(at * SR):int(at * SR) + len(a)] += a
            else:
                s["cues"] = []
                caller[int(at * SR):int(at * SR) + len(a)] += a
            words = txt.split()
            lens = np.array([len(w) + 2 for w in words], float)
            dur = len(a) / SR
            s["words"] = list(zip(words, at + dur * 0.93 * np.r_[0, np.cumsum(lens)[:-1]] / lens.sum()))
            s["ls"], s["le"], s["who"] = s["lead"], s["lead"] + dur, who
            s["d"] = s["lead"] + dur + s["tail"]
        else:
            s["d"], s["ls"], s["le"], s["cues"], s["words"], s["who"] = s["tail"], 99, 99, [], [], None
        t += s["d"]
    total = t + 0.2
    n = int(total * SR)
    mix = voices.clarity(voice[:n]) + phone_filter(caller[:n]) * 1.3
    fxt = np.zeros(n, np.float32)

    def put(x, at):
        i = max(0, int(at * SR))
        fxt[i:i + len(x)] += x[:max(0, n - i)]
    for s in S:
        for name, at in s["sfx"]:
            at = s["t0"] + (s[at[0]] + at[1] if isinstance(at, tuple) else at)     # ("le", 0.4): 0.4 s after the line
            if name in ("alarm", "crickets", "typing"):
                put(fx(name, (s["d"] if name != "typing" else s["ls"])), s["t0"])
            elif name == "steps":
                for k, tt in enumerate(np.arange(0.1, s["d"], 0.34)):
                    put(ogg(f"footstep_concrete_00{k % 4}", .7), s["t0"] + tt)
            elif name == "thud":
                put(ogg("impactSoft_heavy_001", .8), at)
            elif name == "cloth":
                put(ogg("cloth3", .9), at)
            elif name in ("sip", "whoosh", "sting", "chime"):
                put(synth(name, .6 if name == "sip" else (.5 if name == "whoosh" else 1.0)), at)
            else:
                put(fx(name, 1.2), at)
    mix = mix + fxt
    return S, (mix / max(np.abs(mix).max(), 1e-6) * .95).astype(np.float32), total


# ------------------------------------------------------------------ frame
_fonts = {}


def font(size):
    size = max(8, int(size))
    if size not in _fonts:
        _fonts[size] = ImageFont.truetype(F800, size)
    return _fonts[size]


def cam_ctx(ctx, cam, shake=0.0):
    zoom, fx_, fy = cam
    ctx.translate(W / 2 + shake, 1000)
    ctx.scale(zoom, zoom)
    ctx.translate(-fx_, -fy)


def surface_rgba(surf):
    a = np.frombuffer(surf.get_data(), np.uint8).reshape(H, surf.get_stride() // 4, 4)[:, :W].astype(np.float32)
    al = a[..., 3:4]
    rgbv = np.where(al > 0, a[..., [2, 1, 0]] * 255 / np.maximum(al, 1), 0)
    return Image.fromarray(np.concatenate([rgbv, al], 2).clip(0, 255).astype(np.uint8), "RGBA")


def character(frame, st, cam, T, s, t):
    zoom, fx_, fy = cam
    scale, sx, sy, rot = st.get("scale", 1.0), st.get("sx", 1.0), st.get("sy", 1.0), st.get("rot", 0.0)
    expr = X.expression(st["face"])
    if st.get("eyes"):
        expr["eyes"] = st["eyes"]
    if st.get("look") is not None:
        expr["look"] = st["look"]
    speaking = s["who"] == "her" and s["ls"] <= t <= s["le"]
    mouth = st.get("mouth")
    if speaking:
        mouth = "smile"
        for c0, c in s["cues"]:
            if c0 <= T:
                mouth = V.RHUBARB_TO_MOUTH[c]
    if mouth:
        expr["mouth_shape"] = mouth
    if expr["eyes"] == "open" and (T % 3.3) < 0.1:
        expr["eyes"] = "closed"
    k = min(UNIT * scale * zoom * max(sx, sy), 4.5)                  # rendered pixels per rig unit
    png = V.character_png(expr, st.get("arms") or {}, st.get("tilt", 0.0), 0, height=int(860 * k))
    kk = png.height / 860
    th = math.radians(rot)
    R = np.array([[math.cos(th), math.sin(th)], [-math.sin(th), math.cos(th)]])
    M = zoom * UNIT * scale / kk * R @ np.diag([sx, sy])
    o = np.array([-40.0, 150.0])
    c = (zoom * (np.array(st["pos"]) - [fx_, fy]) + [W / 2, 1000]
         + zoom * UNIT * scale * R @ np.diag([sx, sy]) @ (o - np.array(PIV)))
    Mi = np.linalg.inv(M)
    b = -Mi @ c
    layer = png.transform((W, H), Image.AFFINE, (Mi[0, 0], Mi[0, 1], b[0], Mi[1, 0], Mi[1, 1], b[1]), Image.BICUBIC)
    frame.alpha_composite(layer)


def captions(frame, s, T):
    said = [i for i, (_, st) in enumerate(s["words"]) if st <= T]
    if not said or not (s["t0"] + s["ls"] - .05 <= T <= s["t0"] + s["le"] + .3):
        return
    c0 = said[-1] // 3 * 3
    chunk = [w.upper() for w, _ in s["words"][c0:c0 + 3]]
    n = said[-1] - c0 + 1
    f = font(76)
    tot = sum(f.getlength(w) for w in chunk) + 22 * (len(chunk) - 1)
    if tot > 980:
        f = font(76 * 980 / tot)
        tot = sum(f.getlength(w) for w in chunk) + 22 * (len(chunk) - 1)
    d = ImageDraw.Draw(frame)
    x = W / 2 - tot / 2
    col = (126, 200, 255) if s["who"] != "her" else (255, 255, 255)
    for i, w in enumerate(chunk):
        if i < n:
            d.text((x, 1700), w, font=f, fill=col, anchor="lm", stroke_width=10, stroke_fill=(30, 24, 30))
        x += f.getlength(w) + 22
    if s["who"] != "her":
        d.text((W / 2, 1610), "BESTIE (on the phone)", font=font(38), fill=(126, 200, 255), anchor="mm",
               stroke_width=6, stroke_fill=(30, 24, 30))


def header(frame):
    d = ImageDraw.Draw(frame)
    d.rounded_rectangle((170, 80, W - 170, 200), 34, fill=(255, 255, 255), outline=(30, 24, 30), width=6)
    d.text((W / 2, 128), "A DAY IN MY LIFE", font=font(52), fill=PINK, anchor="mm")
    d.text((W / 2, 176), "(as a cartoon)", font=font(30), fill=(90, 80, 90), anchor="mm")


def render(out):
    S, audio, total = build()
    bg = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
    fg = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    with tempfile.TemporaryDirectory() as d:
        wav = os.path.join(d, "a.wav")
        sf.write(wav, audio, SR)
        for fi in range(int(total * FPS)):
            T = fi / FPS
            s = max((x for x in S if x["t0"] <= T), key=lambda x: x["t0"], default=S[0])
            t = T - s["t0"]
            k = ease(t / s["d"])
            cam = tuple(lerp(a, b, k) for a, b in zip(s["cam0"], s["cam1"]))
            ctx = cairo.Context(bg)
            cam_ctx(ctx, cam)
            s["scene"](ctx, t)
            bg.flush()
            frame = Image.frombuffer("RGBA", (W, H), bytes(bg.get_data()), "raw", "BGRA", bg.get_stride(), 1).convert("RGB")
            frame = frame.convert("RGBA")
            st = s["act"](t, s["d"], s["ls"], s["le"])
            character(frame, st, cam, T, s, t)
            if s["fg"]:
                ctx = cairo.Context(fg)
                ctx.set_operator(cairo.OPERATOR_CLEAR)
                ctx.paint()
                ctx.set_operator(cairo.OPERATOR_OVER)
                cam_ctx(ctx, cam)
                s["fg"](ctx, t)
                fg.flush()
                frame.alpha_composite(surface_rgba(fg))
            header(frame)
            captions(frame, s, T)
            if s is S[-1] and t > s["le"] + .1:
                dd = ImageDraw.Draw(frame)
                kk = min(1, (t - s["le"] - .1) / .3)
                dd.rounded_rectangle((150, 1560, W - 150, 1780), 40, fill=PINK)
                dd.text((W / 2, 1635), "follow for part 2", font=font(60 * kk + 1), fill=(255, 255, 255), anchor="mm")
                dd.text((W / 2, 1715), "what should she do next?", font=font(38 * kk + 1), fill=(255, 255, 255), anchor="mm")
            frame.convert("RGB").save(os.path.join(d, f"f{fi:04d}.png"))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(d, "f%04d.png"),
                        "-i", wav, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "19", "-c:a", "aac", "-b:a", "192k",
                        "-shortest", out], check=True)
    print("wrote", out, f"({total:.1f} s)")


if __name__ == "__main__":
    render(sys.argv[1] if len(sys.argv) > 1 else "video_day.mp4")
