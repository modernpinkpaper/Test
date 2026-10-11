"""'I'm 5 minutes away' - cartoon skit (1080x1920, ~1 min). Original script (five_min_lines.py).

    python skits/five_min.py out.mp4

She waits at a cafe; Jay swears he's five minutes away (he's in bed, then brushing his teeth, then running down
the street in one shoe). Cuts between wide shots, close-ups, an insert of the fan, a low angle, a tracking shot
down the street and a tilt from his face to his sock. Sound: her cloned voice, Jay's voice, a room sound per scene
(cafe murmur, bedroom fan, street), and effects (phone ring, sip, thud, toothbrush, door + bell, footsteps, cloth).
Sound effects: Kenney (CC0) in assets/sfx; fonts: Poppins (OFL) in assets.
"""
import math
import os
import subprocess
import sys
import tempfile

import cairocffi as cairo
import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import voices                                # noqa: E402
from five_min_lines import LINES             # noqa: E402
from toon import (OUT, W, H, Toon, curve, ellipse, lin, poly, rad, rgb, rrect, text)   # noqa: E402

FPS, SR = 24, voices.SR
FONT = os.path.join(HERE, "assets", "poppins-800.ttf")
FONT2 = os.path.join(HERE, "assets", "poppins-600.ttf")
SFX = os.path.join(HERE, "assets", "sfx")
CAFE_FLOOR, ROOM_FLOOR = 1560, 1560


def ease(t):
    return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, t)))


# ------------------------------------------------------------------ arm poses by hand target (2-bone IK)
def ik(side, dx, dy, s=1.0, out=1):
    """Toon arm angles (shoulder, elbow) so the hand lands at (dx, dy) from the shoulder (units of s).
    out=1 bends the elbow away from the body."""
    L1, L2 = 95 * s, 88 * s
    d = max(min(math.hypot(dx, dy), L1 + L2 - 1), abs(L1 - L2) + 1)
    th = math.atan2(dx, dy)
    a = math.acos((L1 * L1 + d * d - L2 * L2) / (2 * L1 * d))
    u = th + a * out * (1 if dx * side >= 0 else -1) * side
    ex, ey = math.sin(u) * L1, math.cos(u) * L1
    lo = math.atan2(dx - ex, dy - ey)
    return (math.degrees(u) * side, math.degrees(lo - u) * side)


def arms_to(t_left, t_right, s=1.0):
    """Hand targets relative to the shoulder (None = hanging relaxed)."""
    return (ik(-1, *t_left, s) if t_left else (10, 10), ik(1, *t_right, s) if t_right else (10, 10))


PHONE_R = (95, -115)          # right hand at the right ear
PHONE_L = (-95, -115)


# ------------------------------------------------------------------ props
def phone(ctx, p, s=1.0):
    x, y = p
    rrect(ctx, x - 16 * s, y - 34 * s, 32 * s, 60 * s, 8 * s, fill="#2b2d3a", w=5 * s)
    rrect(ctx, x - 11 * s, y - 28 * s, 22 * s, 42 * s, 4 * s, fill="#7fb3ff", line=None)


def cup(ctx, x, y, s=1.0, tipped=False, steam=0.0):
    ctx.save()
    ctx.translate(x, y)
    if tipped:
        ctx.rotate(1.35)
    rrect(ctx, -34 * s, -70 * s, 68 * s, 70 * s, 10 * s, fill="#f4efe6", w=6 * s)
    rrect(ctx, -34 * s, -52 * s, 68 * s, 22 * s, 0, fill="#c2753e", line=None)
    curve(ctx, [(30 * s, -55 * s), (52 * s, -45 * s), (50 * s, -22 * s), (30 * s, -18 * s)], w=6 * s)
    ctx.restore()
    if steam and not tipped:
        for i in range(3):
            ph = steam * 3 + i * 1.3
            curve(ctx, [(x - 16 + i * 16, y - 80), (x - 8 + i * 16 + 8 * math.sin(ph), y - 110),
                        (x - 16 + i * 16 + 8 * math.sin(ph + 1), y - 140)], line=(1, 1, 1), w=4)


def toothbrush(ctx, p, t):
    x, y = p
    wig = 10 * math.sin(t * 30)
    rrect(ctx, x - 6 + wig, y - 70, 12, 70, 5, fill="#5ec2c9", w=4)
    rrect(ctx, x - 8 + wig, y - 92, 16, 24, 4, fill=(1, 1, 1), w=4)


def foam(ctx, c, R, s=1.0, t=0.0):
    x, y = c[0], c[1] + R * .55
    for i, (dx, dy, r) in enumerate(((-26, 8, 12), (-8, 16, 14), (12, 10, 12), (28, 18, 10), (0, 30, 9))):
        ellipse(ctx, x + dx * s, y + dy * s + 2 * math.sin(t * 5 + i), r * s, r * s, fill=(1, 1, 1), w=3 * s)


def sleep_mask(ctx, c, R):
    rrect(ctx, c[0] - R * .95, c[1] - R * .78, R * 1.9, R * .38, R * .18, fill="#e58fb5", w=6)


def drips(ctx, c, R, t):
    for i in range(3):
        y = (t * 180 + i * 60) % 120
        x = c[0] + (i - 1) * R * .6
        ellipse(ctx, x, c[1] - R * .2 + y, 7, 11, fill="#8fd0ff", w=3)


# ------------------------------------------------------------------ scenes (world = 1080x1920)
def cafe(ctx, t, table=True):
    ctx.rectangle(-900, -900, W + 1800, CAFE_FLOOR + 900)
    ctx.set_source(lin(ctx, 0, 0, 0, CAFE_FLOOR, [(0, "#f6b98a"), (1, "#e98a6b")]))
    ctx.fill()
    ctx.rectangle(-900, CAFE_FLOOR, W + 1800, H - CAFE_FLOOR + 900)
    ctx.set_source(lin(ctx, 0, CAFE_FLOOR, 0, H, [(0, "#8a5a44"), (1, "#5a3a2c")]))
    ctx.fill()
    for i in range(10):                                        # checker floor in perspective
        poly(ctx, [(i * 130 - 60, CAFE_FLOOR), (i * 130 + 10, CAFE_FLOOR), (i * 170 - 120, H), (i * 170 - 210, H)],
             fill="#7a4e3b" if i % 2 else "#94634c", line=None)
    # big window, sunset street outside
    rrect(ctx, 520, 360, 500, 560, 20, fill=lin(ctx, 0, 360, 0, 920, [(0, "#ffcf8a"), (1, "#ff8a7a")]), w=10)
    for bx, bw, bh in ((540, 90, 260), (640, 120, 330), (770, 80, 220), (860, 140, 300)):
        rrect(ctx, bx, 920 - bh, bw, bh, 6, fill="#c96e7e", line=None)
    ellipse(ctx, 700, 520, 60, 60, fill="#fff2c9", line=None)
    poly(ctx, [(770, 360), (770, 920)], w=8, close=False)
    poly(ctx, [(520, 640), (1020, 640)], w=8, close=False)
    # menu board + pendant lamps
    rrect(ctx, 70, 380, 380, 300, 14, fill="#2f3b36", w=10)
    for i, (w_, y) in enumerate(((260, 450), (200, 500), (240, 550), (180, 600))):
        rrect(ctx, 110, y, w_, 14, 7, fill="#dfe8d8", line=None)
    text(ctx, "MENU", 260, 415, 40, FONT, col="#f4d79a")
    for lx in (230, 800):
        poly(ctx, [(lx, 0), (lx, 220)], w=5, close=False)
        ctx.set_source(rad(ctx, lx, 260, 260, [(0, "#fff3c4", .45), (1, "#fff3c4", 0)]))
        ctx.paint()
        poly(ctx, [(lx - 60, 280), (lx + 60, 280), (lx + 30, 215), (lx - 30, 215)], fill="#2d5d57", w=7)
    # counter at the back
    rrect(ctx, -20, 1080, 420, 60, 8, fill="#c79a6f", w=8)
    rrect(ctx, 0, 1140, 380, 420, 0, fill="#9b6d4c", w=8)
    rrect(ctx, 120, 990, 110, 90, 10, fill="#b9c3cc", w=7)      # espresso machine
    ellipse(ctx, 175, 1030, 22, 22, fill="#3b4148", w=5)


def cafe_table(ctx, x=640, y=1390, cup_state=None, t=0.0):
    """Round table in front of her (hides her legs: she looks seated)."""
    poly(ctx, [(x - 250, y), (x + 250, y), (x + 270, 1600), (x - 270, 1600)], fill="#f7f1e8", w=8)
    for i in range(6):                                                           # scalloped cloth hem
        ellipse(ctx, x - 225 + i * 90, 1600, 46, 22, fill="#f7f1e8", line=None)
    curve(ctx, [(x - 270, 1600), (x - 180, 1618), (x - 90, 1600), (x, 1618), (x + 90, 1600), (x + 180, 1618),
                (x + 270, 1600)], w=8)
    ellipse(ctx, x, y, 260, 44, fill="#fbf7f0", w=8)
    if cup_state:
        cup(ctx, x - 130, y + 6, tipped=cup_state == "empty", steam=t if cup_state == "full" else 0)


def bedroom(ctx, t, fan=True):
    ctx.rectangle(-900, -900, W + 1800, ROOM_FLOOR + 900)
    ctx.set_source(lin(ctx, 0, 0, 0, ROOM_FLOOR, [(0, "#1d2250"), (1, "#3a3f7e")]))
    ctx.fill()
    ctx.rectangle(-900, ROOM_FLOOR, W + 1800, H - ROOM_FLOOR + 900)
    ctx.set_source(lin(ctx, 0, ROOM_FLOOR, 0, H, [(0, "#2f2a4a"), (1, "#1c1830")]))
    ctx.fill()
    rrect(ctx, 80, 420, 340, 420, 16, fill=lin(ctx, 0, 420, 0, 840, [(0, "#0e1233"), (1, "#343a7c")]), w=10)
    ellipse(ctx, 300, 540, 52, 52, fill="#f5f1c8", line=None)
    ellipse(ctx, 322, 526, 48, 48, fill="#141a42", line=None)
    poly(ctx, [(250, 420), (250, 840)], w=8, close=False)
    for i in range(4):                                                            # poster + clock
        pass
    rrect(ctx, 520, 470, 200, 250, 8, fill="#e27a8a", w=8)
    text(ctx, "MON", 620, 560, 46, FONT, col=(1, 1, 1))
    text(ctx, "DAY", 620, 620, 46, FONT, col=(1, 1, 1))
    # bed
    rrect(ctx, 400, 1050, 70, 520, 14, fill="#5b4a8a", w=8)                      # headboard post
    rrect(ctx, 420, 1260, 660, 170, 22, fill="#f1eee8", w=8)                     # mattress
    rrect(ctx, 420, 1420, 660, 150, 8, fill="#6a58a0", w=8)                      # bed frame
    ellipse(ctx, 540, 1250, 90, 44, fill=(1, 1, 1), w=7)                          # pillow
    # nightstand with the (very loud) fan
    rrect(ctx, 0, 1300, 170, 260, 8, fill="#8a6fb0", w=8)
    if fan:
        draw_fan(ctx, 85, 1170, 0.9, t)


def draw_fan(ctx, x, y, s, t):
    poly(ctx, [(x - 10 * s, y + 20 * s), (x + 10 * s, y + 20 * s), (x + 22 * s, y + 130 * s), (x - 22 * s, y + 130 * s)],
         fill="#c8ccd8", w=6 * s)
    ellipse(ctx, x, y, 95 * s, 95 * s, fill="#dfe3ec", w=7 * s)
    for k in range(3):
        a = t * 25 + k * 2 * math.pi / 3
        curve(ctx, [(x, y), (x + 70 * s * math.cos(a - .35), y + 70 * s * math.sin(a - .35)),
                    (x + 78 * s * math.cos(a + .15), y + 78 * s * math.sin(a + .15))], fill="#a9b6d8", w=5 * s, close=True)
    ellipse(ctx, x, y, 16 * s, 16 * s, fill="#7b86a8", w=5 * s)
    for k in range(10):                                                            # the cage
        a = k * math.pi / 5
        poly(ctx, [(x, y), (x + 95 * s * math.cos(a), y + 95 * s * math.sin(a))], line="#9aa0b4", w=3 * s, close=False)


def bathroom(ctx, t):
    ctx.rectangle(-900, -900, W + 1800, ROOM_FLOOR + 900)
    ctx.set_source(lin(ctx, 0, 0, 0, ROOM_FLOOR, [(0, "#8fd3cf"), (1, "#5fb3b6")]))
    ctx.fill()
    for y in range(300, ROOM_FLOOR, 90):
        poly(ctx, [(0, y), (W, y)], line="#7cc2bf", w=3, close=False)
    for x in range(0, W, 90):
        poly(ctx, [(x, 300), (x, ROOM_FLOOR)], line="#7cc2bf", w=3, close=False)
    ctx.rectangle(-900, ROOM_FLOOR, W + 1800, H - ROOM_FLOOR + 900)
    ctx.set_source_rgb(*rgb("#dfe7ea"))
    ctx.fill()
    rrect(ctx, 600, 520, 380, 460, 30, fill=lin(ctx, 600, 520, 980, 980, [(0, "#eaf6ff"), (1, "#b8d6ea")]), w=10)
    poly(ctx, [(660, 600), (740, 540)], line=(1, 1, 1), w=10, close=False)
    rrect(ctx, 560, 1150, 470, 90, 16, fill="#f7f7f7", w=8)                     # sink counter
    rrect(ctx, 600, 1240, 390, 320, 8, fill="#e8e0d4", w=8)
    rrect(ctx, 760, 1090, 20, 60, 8, fill="#b8c0c8", w=5)                       # tap


def street(ctx, t, scroll=0.0):
    ctx.rectangle(-900, -900, W + 1800, 2380)
    ctx.set_source(lin(ctx, 0, 0, 0, 1480, [(0, "#5a4b9c"), (0.6, "#e88fa0"), (1, "#ffc38a")]))
    ctx.fill()
    for layer, (col, spd, base) in enumerate((("#6d5a9e", .25, 1100), ("#503f7e", .6, 1250))):
        for i in range(-2, 12):
            bx = (i * 230 - scroll * spd) % 2760 - 460
            bh = 260 + ((i * 97 + layer * 53) % 5) * 70
            rrect(ctx, bx, base - bh + 200, 190, bh + 300, 8, fill=col, line=None)
            for wy in range(int(base - bh + 240), base + 160, 70):
                for wx in (30, 110):
                    rrect(ctx, bx + wx, wy, 40, 36, 4, fill="#ffd98a" if (i + wy // 70 + wx) % 3 else "#3d3066", line=None)
    ctx.rectangle(-900, 1480, W + 1800, H - 1480 + 900)
    ctx.set_source_rgb(*rgb("#8e8aa0"))
    ctx.fill()
    poly(ctx, [(0, 1480), (W, 1480)], w=8, close=False)
    for i in range(-1, 8):
        x = (i * 200 - scroll) % 1600 - 200
        poly(ctx, [(x, 1480), (x - 70, H)], line="#7c788e", w=5, close=False)
    for i in range(-1, 4):                                                        # street lamps
        x = (i * 520 - scroll * .9) % 2080 - 260
        poly(ctx, [(x, 1480), (x, 900)], w=10, close=False)
        ctx.set_source(rad(ctx, x + 40, 900, 200, [(0, "#fff0b8", .5), (1, "#fff0b8", 0)]))
        ctx.paint()
        rrect(ctx, x - 10, 880, 90, 30, 12, fill="#3a3355", w=7)


def cafe_door(ctx, t, open_=0.0):
    cafe(ctx, t)
    rrect(ctx, 30, 900, 400, 660, 10, fill="#3b2a24", w=10)                     # door frame
    ctx.rectangle(40, 910, 380, 640)
    ctx.set_source(lin(ctx, 0, 900, 0, 1560, [(0, "#ffcf8a"), (1, "#ff8a7a")]))
    ctx.fill()
    w_ = 380 * (1 - .85 * open_)
    rrect(ctx, 40, 910, w_, 640, 6, fill="#6fb1a8", w=8)
    if w_ > 80:
        rrect(ctx, 40 + w_ * .12, 960, w_ * .76, 280, 8, fill="#cfeef0", w=6)
    ellipse(ctx, 400, 880, 22, 22, fill="#f4c542", w=5)                          # the door bell


# ------------------------------------------------------------------ characters
def her(x=640, floor=1570):
    return Toon(x, floor, facing=-1, head="#cfcfd2", hair="bun", hair_col="#4a2c1f", scale=1.0, outfit="#1d1d22")


def jay(x=300, floor=1560, shirt="#3a6ea5"):
    return Toon(x, floor, facing=1, head="#c4c4c8", hair="buzz", hair_col="#2a2522", scale=1.05, outfit=shirt)


# ------------------------------------------------------------------ audio
def ogg(name, gain=1.0):
    a, sr = sf.read(os.path.join(SFX, name + ".ogg"), dtype="float32")
    if a.ndim > 1:
        a = a.mean(1)
    if sr != SR:
        a = np.interp(np.arange(0, len(a), sr / SR), np.arange(len(a)), a).astype(np.float32)
    return a * gain


def synth(kind, n, seed=0):
    t = np.arange(int(n * SR)) / SR
    rng = np.random.default_rng(seed)
    noise = rng.normal(0, 1, len(t)).astype(np.float32)
    import scipy.signal as ss

    def band(x, lo, hi):
        b, a = ss.butter(2, [lo / (SR / 2), hi / (SR / 2)], "band")
        return ss.lfilter(b, a, x).astype(np.float32)
    if kind == "ring":            # phone ringing on the other end, heard in her ear
        on = ((t % 3.0) < 1.6).astype(np.float32)
        return (np.sin(2 * np.pi * 440 * t) + np.sin(2 * np.pi * 480 * t)) * on * 0.05
    if kind == "sip":
        return band(noise, 900, 3000) * np.sin(np.pi * t / n) ** 2 * (0.6 + 0.4 * np.sin(2 * np.pi * 9 * t)) * 0.12
    if kind == "fan":
        return band(noise, 150, 1400) * (0.8 + 0.2 * np.sin(2 * np.pi * 7 * t)) * 0.05
    if kind == "brush":
        return band(noise, 2500, 7000) * (np.sin(2 * np.pi * 5 * t) > -.2) * 0.07
    if kind == "cafe":            # distant murmur + the odd cup clink
        m = band(noise, 250, 1600) * (0.7 + 0.3 * np.sin(2 * np.pi * 0.7 * t) * np.sin(2 * np.pi * 1.9 * t)) * 0.022
        return m
    if kind == "street":
        return band(noise, 60, 700) * 0.04
    if kind == "chime":
        return (np.sin(2 * np.pi * 1318 * t) * np.exp(-t / .5) + np.sin(2 * np.pi * 1760 * np.clip(t - .18, 0, None)) *
                np.exp(-np.clip(t - .18, 0, None) / .6) * (t > .18)) * 0.12
    if kind == "whoosh":
        return band(noise, 300, 4000) * np.sin(np.pi * t / n) ** 2 * 0.08
    if kind == "sting":           # dramatic zoom sting
        return (np.sin(2 * np.pi * (220 + 400 * t) * t) * np.exp(-t / .4) * 0.12).astype(np.float32)
    return np.zeros(len(t), np.float32)


# ------------------------------------------------------------------ the shot list
# ("beat", seconds, shot) or ("line", index, shot); shot = (draw function, camera start, camera end)
# camera = (zoom, focus x, focus y, rotation deg); a shot's draw(ctx, t, T, mouth_her, mouth_jay) draws the world.
def shots():
    def S_cafe_wide(ctx, t, T, mh, mj, cup_state="full", slump=False):
        cafe(ctx, T)
        h = her()
        arms = arms_to((-60, 150), (-120, 70)) if not slump else arms_to((-150, 60), PHONE_R)
        if cup_state == "sip" or (cup_state == "full" and 0.5 < t < 1.3):
            arms = arms_to((-60, 150), (-140, -40))
        h.draw(ctx, arms=arms, face="neutral" if not slump else "unimpressed", mouth=mh, blink=(T % 3.3) < .12,
               tilt=-8 if slump else 0, hold=(lambda c, hs: phone(c, hs[1])) if slump else None)
        cafe_table(ctx, cup_state="empty" if slump else "full", t=T)

    def S_her_cu(face, arms=None, holdphone=True, tilt=0.0):
        def f(ctx, t, T, mh, mj):
            cafe(ctx, T)
            h = her()
            h.draw(ctx, arms=arms or arms_to((-60, 150), PHONE_R), face=face, mouth=mh, look=(-.4, 0),
                   blink=(T % 3.1) < .12, tilt=tilt, hold=(lambda c, hs: phone(c, hs[1])) if holdphone else None)
            cafe_table(ctx, cup_state="full", t=T)
        return f

    def S_bed(face, stand=0.0, fall=0.0):
        def f(ctx, t, T, mh, mj):
            bedroom(ctx, T)
            if stand <= 0:
                j = jay(x=640, floor=1610)
                j.draw(ctx, arms=arms_to((80, 120), PHONE_R, 1.05), face=face, mouth=mj, blink=(T % 2.9) < .12,
                       hold=lambda c, hs: phone(c, hs[1], 1.05), before_head=None)
                sleep_mask(ctx, j.head_c, j.head_r)
                poly(ctx, [(430, 1290), (1070, 1290), (1070, 1440), (430, 1440)], fill="#8f7fd0", w=8)   # blanket
                curve(ctx, [(470, 1330), (620, 1310), (800, 1340), (1000, 1315)], line="#7a6ab9", w=5)
            else:
                ctx.save()
                j = jay(x=330, floor=ROOM_FLOOR)
                if fall > 0:
                    ctx.translate(330, ROOM_FLOOR)
                    ctx.rotate(1.4 * ease(fall))
                    ctx.translate(-330, -ROOM_FLOOR)
                run = math.sin(T * 14) * 25 * (1 - ease(fall))
                j.draw(ctx, arms=arms_to((-90, 40), PHONE_R, 1.05), legs=(run, run), face=face, mouth=mj,
                       hold=lambda c, hs: phone(c, hs[1], 1.05))
                sleep_mask(ctx, j.head_c, j.head_r)
                ctx.restore()
        return f

    def S_fan(ctx, t, T, mh, mj):
        bedroom(ctx, T)

    def S_bath(face, brushing=True):
        def f(ctx, t, T, mh, mj):
            bathroom(ctx, T)
            j = jay(x=380, floor=1600)
            j.draw(ctx, arms=arms_to((60, -40) if brushing else (-60, 120), PHONE_R, 1.05), face=face,
                   mouth=mj if not brushing else .3, blink=(T % 2.7) < .12,
                   hold=lambda c, hs: (phone(c, hs[1], 1.05), toothbrush(c, hs[0], T if brushing else 0)))
            foam(ctx, j.head_c, j.head_r, 1.05, T)
        return f

    def S_card(txt1, txt2):
        def f(ctx, t, T, mh, mj):
            ctx.set_source(lin(ctx, 0, 0, 0, H, [(0, "#2a2140"), (1, "#15101f")]))
            ctx.paint()
            ellipse(ctx, 540, 900, 170, 170, fill="#f6efe2", w=12)
            for k in range(12):
                a = k * math.pi / 6
                poly(ctx, [(540 + 140 * math.cos(a), 900 + 140 * math.sin(a)), (540 + 155 * math.cos(a), 900 + 155 * math.sin(a))],
                     w=6, close=False)
            a = -math.pi / 2 + T * 3
            poly(ctx, [(540, 900), (540 + 120 * math.cos(a), 900 + 120 * math.sin(a))], w=9, close=False)
            poly(ctx, [(540, 900), (540 + 80 * math.cos(a / 12), 900 + 80 * math.sin(a / 12))], w=12, close=False)
            text(ctx, txt1, 540, 1200, 92, FONT, col=(1, 1, 1))
            text(ctx, txt2, 540, 1300, 62, FONT2, col="#f4b6c2")
        return f

    def S_run(ctx, t, T, mh, mj):
        street(ctx, T, scroll=T * 700)
        j = jay(x=540, floor=1480)
        run = math.sin(T * 16) * 35
        j.draw(ctx, arms=arms_to((-60 - 40 * math.sin(T * 16), 90), PHONE_R, 1.05), legs=(run, run), face="shock",
               mouth=mj, bob=-abs(math.sin(T * 16)) * 14, socks=(False, True), inside_out=True,
               hold=lambda c, hs: phone(c, hs[1], 1.05))
        drips(ctx, j.head_c, j.head_r, T)

    def S_door(open_t, panting=False, face="shock", arms=None, pat=False):
        def f(ctx, t, T, mh, mj):
            cafe_door(ctx, T, open_=ease(open_t(t)))
            j = jay(x=230, floor=CAFE_FLOOR, shirt="#3a6ea5")
            if open_t(t) > .3:
                pant = math.sin(T * 12) * 6 if panting else 0
                a = arms or arms_to((-40, 120), (40, 120), 1.05)
                if pat:
                    k = math.sin(T * 10)
                    a = arms_to((-35, 150 + 12 * k), (35, 150 - 12 * k), 1.05)
                j.draw(ctx, arms=a, face=face, mouth=mj, bob=pant, socks=(False, True), inside_out=True,
                       blink=(T % 2.6) < .12)
                drips(ctx, j.head_c, j.head_r, T)
            h = her(x=790)
            h.draw(ctx, arms=arms_to((-60, 150), (60, 150)), face="unimpressed" if not pat else "angry", mouth=mh,
                   look=(-1, 0), blink=(T % 3.1) < .12)
            cafe_table(ctx, x=790, cup_state="empty", t=T)
        return f

    def S_both(face_h, face_j, point=False, pat=False):
        return S_door(lambda t: 1.0, face=face_j, pat=pat,
                      arms=arms_to((-40, 120), (40, 120), 1.05)) if not point else S_point(face_h, face_j)

    def S_point(face_h, face_j):
        def f(ctx, t, T, mh, mj):
            cafe_door(ctx, T, open_=1.0)
            j = jay(x=230, floor=CAFE_FLOOR)
            j.draw(ctx, arms=arms_to((-30, 130), (30, 130), 1.05), face=face_j, mouth=mj, socks=(False, True),
                   inside_out=True, blink=(T % 2.6) < .12)
            h = her(x=790)
            h.draw(ctx, arms=arms_to((-170, 10), (60, 150)), face=face_h, mouth=mh, look=(-1, 0))
            cafe_table(ctx, x=790, cup_state="empty", t=T)
        return f

    HEAD_HER = (640, 1020)
    wide = (1.0, 540, 960, 0)
    return [
        ("beat", 2.2, (S_cafe_wide, (1.05, 560, 1000, 0), (1.0, 540, 960, 0)), [("sip", .7), ("cafe", 0)]),
        ("beat", 1.6, (S_her_cu("neutral"), (2.2, 640, 1080, 0), (2.3, 640, 1060, 0)), [("ring", 0)]),
        ("line", 0, (S_her_cu("sus"), (2.3, 640, 1060, 0), (2.6, 640, 1040, 0)), []),
        ("line", 1, (S_bed("happy"), (1.35, 640, 1000, 0), (1.5, 640, 980, 0)), [("fan", 0)]),
        ("line", 2, (S_her_cu("sus", tilt=-6), (2.4, 640, 1040, -4), (2.9, 640, 1030, -6)), []),
        ("beat", 0.9, (S_fan, (3.2, 85, 1170, 0), (3.6, 85, 1170, 3)), [("fan", 0), ("whoosh", 0)]),
        ("line", 3, (S_bed("worried", stand=1), (1.5, 300, 1150, 0), (1.3, 330, 1150, 0)), [("fan", 0)]),
        ("beat", 1.0, (S_bed("shock", stand=1, fall=1), (1.3, 330, 1250, 0), (1.25, 330, 1250, 0)),
         [("fan", 0), ("thud", .35)]),
        ("beat", 1.0, (S_bath("happy_closed"), (1.6, 470, 1000, 0), (1.7, 470, 990, 0)), [("brush", 0)]),
        ("line", 4, (S_her_cu("angry"), (2.4, 640, 1040, 0), (2.7, 640, 1030, 0)), [("brush_far", 0)]),
        ("line", 5, (S_bath("sheepish" if False else "worried", brushing=False), (2.3, 400, 980, 0), (2.5, 400, 970, 0)), []),
        ("beat", 1.8, (S_card("25 minutes", "later..."), (1.0, 540, 960, 0), (1.05, 540, 960, 0)), [("tick", 0)]),
        ("line", 6, (lambda ctx, t, T, mh, mj: S_cafe_wide(ctx, t, T, mh, mj, slump=True), (1.6, 640, 1150, 0),
                     (1.8, 640, 1100, 0)), [("cafe", 0)]),
        ("line", 7, (S_run, (1.25, 540, 1000, 0), (1.35, 540, 980, 0)), [("steps_fast", 0), ("street", 0)]),
        ("line", 8, (S_her_cu("unimpressed"), (2.5, 640, 1040, 0), (2.8, 640, 1030, 0)), []),
        ("beat", 1.3, (S_door(lambda t: t / .5, panting=True), (1.0, 540, 1000, 0), (1.1, 400, 1050, 0)),
         [("door", 0), ("chime", .05), ("steps", .3)]),
        ("line", 9, (S_door(lambda t: 1.0, panting=True, arms=arms_to((-120, -20), (120, -20), 1.05)),
                     (1.8, 250, 1000, 0), (2.0, 250, 1000, 0)), []),
        ("line", 10, (S_door(lambda t: 1.0, face="worried"), (2.6, 230, 960, 0), (2.4, 230, 1520, 0)), []),   # tilt down
        ("line", 11, (S_door(lambda t: 1.0, face="worried", arms=arms_to((-60, 60), (60, 60), 1.05)),
                      (2.4, 230, 980, 3), (2.6, 230, 980, 5)), []),
        ("line", 12, (S_point("angry", "worried"), (1.25, 520, 1080, 0), (1.3, 520, 1080, 0)), []),
        ("line", 13, (S_door(lambda t: 1.0, face="worried", pat=True), (1.4, 400, 1050, 0), (1.5, 380, 1050, 0)),
         [("cloth", 0), ("cloth", .6)]),
        ("line", 14, (S_her_cu("shock", arms=arms_to((-60, 150), (60, 150)), holdphone=False), (2.4, 790 - 150, 1040, 0),
                      (3.4, 640, 1030, 0)), [("sting", 0)]),
        ("beat", 2.0, (S_point("angry", "worried"), (1.0, 540, 960, 0), (1.0, 540, 960, 0)), []),
    ]


def render(out):
    plan, t = [], 0.0
    voice = np.zeros(int(90 * SR), np.float32)
    for kind, v, shot, fx in shots():
        if kind == "beat":
            dur, line = v, None
        else:
            who, txt = LINES[v]
            a = voices.room(voices.gate(voices.say(who, txt)))
            dur = len(a) / SR + 0.28
            i = int((t + 0.08) * SR)
            voice[i:i + len(a)] += a
            line = (who, txt, t + 0.08, t + 0.08 + len(a) / SR, a)
        plan.append((t, dur, shot, fx, line))
        t += dur
    total = t
    voice = voices.clarity(voice[:int(total * SR)])
    fxtrack = np.zeros_like(voice)

    def add(x, at):
        i = int(at * SR)
        fxtrack[i:i + len(x)] += x[:max(0, len(fxtrack) - i)]
    for t0, dur, shot, fx, line in plan:
        for name, at in fx:
            if name == "ring":
                add(synth("ring", 1.6), t0)
            elif name == "sip":
                add(synth("sip", .6), t0 + at)
            elif name in ("cafe", "street", "fan"):
                add(synth(name, dur + .2, seed=int(t0 * 10)), t0)
            elif name == "brush":
                add(synth("brush", dur), t0)
            elif name == "brush_far":
                add(synth("brush", dur) * .35, t0)
            elif name == "thud":
                add(ogg("impactSoft_heavy_001", 1.0), t0 + at)
            elif name == "tick":
                for k in np.arange(0, dur, .5):
                    add(ogg("tick_001", .6), t0 + k)
            elif name == "whoosh":
                add(synth("whoosh", .5), t0)
            elif name == "steps_fast":
                for k, tt in enumerate(np.arange(0, dur, .2)):
                    add(ogg(f"footstep_concrete_00{k % 4}", .8), t0 + tt)
            elif name == "steps":
                for k, tt in enumerate(np.arange(at, dur, .28)):
                    add(ogg(f"footstep0{k % 4}", .7), t0 + tt)
            elif name == "door":
                add(ogg("doorOpen_1", .9), t0 + at)
            elif name == "chime":
                add(synth("chime", 1.2), t0 + at)
            elif name == "cloth":
                add(ogg("cloth3", .8), t0 + at)
            elif name == "sting":
                add(synth("sting", .8), t0 + at)
        if shot[0].__name__ in ("f", "S_cafe_wide") and line and "cafe" not in [n for n, _ in fx]:
            pass
    # quiet room sound under every cafe shot where she talks
    for t0, dur, shot, fx, line in plan:
        if line and line[0] == "her":
            add(synth("cafe", dur, seed=int(t0 * 7)) * .8, t0)
    mix = voice + fxtrack
    mix = mix / max(np.abs(mix).max(), 1e-6) * 0.95

    surf = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
    with tempfile.TemporaryDirectory() as d:
        wav = os.path.join(d, "a.wav")
        sf.write(wav, mix, SR)
        for fi in range(int(total * FPS)):
            T = fi / FPS
            idx = max(i for i, p in enumerate(plan) if p[0] <= T)
            t0, dur, (draw, c0, c1), fx, line = plan[idx]
            t = T - t0
            k = ease(t / dur)
            zoom, fxp, fyp, rot = [a + (b - a) * k for a, b in zip(c0, c1)]
            mh = mj = 0.0
            if line and line[2] <= T <= line[3]:
                a = line[4]
                i = int((T - line[2]) * SR)
                seg = a[max(i - 400, 0):i + 400]
                lvl = min(1.0, float(np.sqrt(np.mean(seg ** 2))) * 9) if len(seg) else 0
                if line[0] == "her":
                    mh = lvl
                else:
                    mj = lvl
            ctx = cairo.Context(surf)
            ctx.set_source_rgb(1, 1, 1)
            ctx.paint()
            ctx.save()
            shake = 0
            if line and line[1].endswith("Oh my God!"):
                shake = 10 * math.sin(T * 60) * max(0, 1 - t / .6)
            ctx.translate(W / 2 + shake, 1000)
            ctx.rotate(math.radians(rot))
            ctx.scale(zoom, zoom)
            ctx.translate(-fxp, -fyp)
            draw(ctx, t, T, mh, mj)
            ctx.restore()
            # title box like the reference, and a small subtitle
            rrect(ctx, 70, 120, 940, 170, 22, fill=(1, 1, 1), line=None)
            text(ctx, "Pov: your friend is", 540, 175, 58, FONT2)
            text(ctx, "“5 minutes away”", 540, 245, 62, FONT)
            if line and line[2] - .05 <= T <= line[3] + .2:
                who, txt = line[0], line[1].split("] ", 1)[-1]
                col = (1, 1, 1)
                words, rows, cur = txt.split(), [], ""
                for wd in words:
                    trial = (cur + " " + wd).strip()
                    if len(trial) > 24 and cur:
                        rows.append(cur)
                        cur = wd
                    else:
                        cur = trial
                rows.append(cur)
                for r, row in enumerate(rows[:3]):
                    text(ctx, row, 540, 1690 + r * 64 - 32 * (min(len(rows), 3) - 1), 54, FONT, col=col,
                         outline=(0.08, 0.07, 0.1), ow=12)
            if idx == 0:
                rrect(ctx, 60, 1640, 230, 80, 16, fill=(0, 0, 0), line=None)
                text(ctx, "7:00 PM", 175, 1680, 44, FONT, col=(1, 1, 1))
            if idx == len(plan) - 1:
                a = ease(t / .4)
                rrect(ctx, 90, 1560, 900, 220, 24, fill=(1, 1, 1), line=None)
                text(ctx, "Tag your", 540, 1625, 60 * a + 1, FONT2)
                text(ctx, "“5 minutes away” friend", 540, 1705, 58 * a + 1, FONT, col="#d9406a")
            surf.write_to_png(os.path.join(d, f"f{fi:04d}.png"))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(d, "f%04d.png"),
                        "-i", wav, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "19", "-c:a", "aac", "-b:a", "192k",
                        "-shortest", out], check=True)
    print("wrote", out, f"({total:.1f} s)")


if __name__ == "__main__":
    render(sys.argv[1] if len(sys.argv) > 1 else "five_min.mp4")
