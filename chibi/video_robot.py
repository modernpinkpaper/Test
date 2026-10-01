"""'Build day: my customer-service robot', a talk-to-camera vlog with her chibi girl (1080x1920, ~65 s).

    python chibi/video_robot.py out.mp4

Made from her real workday log (Sept 30): the 8 AM sales report her script made by itself, and the Amazon
message drafter she works on (reads a buyer message, checks the answer sheet, drafts a reply; she sends it).
Everything on screen is a mockup: no real orders, customers or code. Script: robot_lines.py (her own voice).
Rig, camera, captions and sound come from video_day.py; this file adds the office monitor, the robot, the
inbox avalanche, the answer sheet, the typed reply and the send button.
"""
import math
import os
import sys

import numpy as np
from PIL import ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, "..", "skits")]
import beats                                                      # noqa: E402
import chibi_props as P                                           # noqa: E402
import video_day as D                                             # noqa: E402
from robot_lines import LINES, VOICE                              # noqa: E402
from toon import ellipse, lin, poly, rad, rgb, rrect, text        # noqa: E402

W, H, FLOOR = D.W, D.H, D.FLOOR
F800, F600 = D.F800, D.F600
HX = 330                       # her x at the desk (the monitor and the robot are on her right)
RX, RY = 835, 1222             # robot on the desk (base centre)
MON = (600, 290, 450, 330)     # wall monitor: x, y, w, h
ease, lerp, stand, blend, moves = D.ease, D.lerp, D.stand, D.blend, D.moves

D.POSES["press"] = {"right": D._r("right", (150, 690), (0.25, 1), "point")}
D.POSES["hip"] = {"right": D._r("right", (112, 640), (0.12, 1), "hip_flat")}

MESSAGES = ["Where's my order??", "Can you change the font?", "Ship by Friday?", "Wrong name spelling!",
            "Do you do rush?", "Is it pink or PINK pink?", "Can I add a line?", "Hello???", "Gift note?",
            "Envelopes included?", "Order #? I lost it", "Can it say Mrs.?"]


# ------------------------------------------------------------------ set pieces
def office(ctx, t, screen=None, st=0.0):
    """Her office: window, shelf, a floor, and a big wall monitor showing `screen` (scr_*(ctx, t, x, y, w, h))."""
    ctx.rectangle(-3000, -3000, W + 6000, FLOOR + 3000)
    ctx.set_source(lin(ctx, 0, 0, 0, FLOOR, [(0, "#ece6fb"), (1, "#d6cdf3")]))
    ctx.fill()
    ctx.rectangle(-3000, FLOOR, W + 6000, 3000)                                          # floor
    ctx.set_source_rgb(*rgb("#c7b3e6"))
    ctx.fill()
    poly(ctx, [(-3000, FLOOR), (W + 3000, FLOOR)], w=8, close=False)
    for x in range(-600, W + 600, 160):
        poly(ctx, [(x, FLOOR), (x - 60, FLOOR + 400)], line="#b6a1d8", w=4, close=False)
    rrect(ctx, 60, 380, 380, 440, 16, fill=lin(ctx, 0, 380, 0, 820, [(0, "#8fd3ff"), (1, "#e8f7ff")]), w=10)
    for bx, bw, bh in ((80, 80, 200), (170, 110, 290), (290, 70, 170), (370, 60, 240)):
        rrect(ctx, bx, 820 - bh, bw, bh, 6, fill="#9fb0d8", line=None)
    poly(ctx, [(250, 380), (250, 820)], w=8, close=False)
    rrect(ctx, 1080, 820, 300, 22, 6, fill="#d9a47c", w=6)                                # shelf + plant, far right
    rrect(ctx, 1110, 740, 70, 80, 10, fill="#e58f6a", w=5)
    for a in (-0.6, 0, 0.6):
        ellipse(ctx, 1145 + 40 * math.sin(a), 700 - 30 * math.cos(a), 20, 36, fill="#6cc48a", w=5)
    x, y, w, h = MON
    rrect(ctx, x + w / 2 - 30, y + h, 60, 70, 6, fill="#4b4560", w=6)                    # stand
    rrect(ctx, x - 14, y - 14, w + 28, h + 28, 26, fill="#3a3550", w=8)                   # bezel
    rrect(ctx, x, y, w, h, 14, fill="#ffffff", line=None)
    ctx.save()
    ctx.rectangle(x, y, w, h)
    ctx.clip()
    (screen or scr_idle)(ctx, t - st, x, y, w, h)
    ctx.restore()


def scr_idle(ctx, t, x, y, w, h):
    rrect(ctx, x, y, w, 60, 0, fill="#c9a4ff", line=None)
    text(ctx, "ROBOT STATUS", x + w / 2, y + 30, 28, F800, col=(1, 1, 1))
    text(ctx, "drafts waiting", x + w / 2, y + 140, 32, F800, col="#2b2440")
    text(ctx, "for the boss: 3", x + w / 2, y + 185, 32, F800, col="#2b2440")
    for i in range(3):
        rrect(ctx, x + 120 + i * 75, y + 235, 55, 40, 8, fill="#ffe08a", w=4)


def scr_inbox_full(ctx, t, x, y, w, h):
    rrect(ctx, x, y, w, 60, 0, fill="#ff8fb0", line=None)
    text(ctx, "CUSTOMER INBOX", x + w / 2, y + 30, 28, F800, col=(1, 1, 1))
    for i in range(5):
        ry = y + 75 + i * 50 + (t * 120) % 50
        rrect(ctx, x + 20, ry, w - 40, 40, 8, fill="#fff0f4", w=3)
        rrect(ctx, x + 34, ry + 13, 160 + (i * 41) % 90, 14, 7, fill="#e7a3b8", line=None)
    s = 1 + 0.08 * math.sin(t * 12)
    ellipse(ctx, x + w - 60, y + 100, 52 * s, 52 * s, fill="#e53935", w=6)
    text(ctx, "99+", x + w - 60, y + 100, 34 * s, F800, col=(1, 1, 1))


def scr_memory(ctx, t, x, y, w, h):
    rrect(ctx, x, y, w, 60, 0, fill="#ffd45e", line=None)
    text(ctx, "TODAY'S UPGRADE", x + w / 2, y + 30, 28, F800, col="#2b2440")
    text(ctx, "MEMORY", x + w / 2, y + 140, 60, F800, col="#2b2440")
    k = ease((t - 0.5) / 1.5)
    rrect(ctx, x + 50, y + 205, w - 100, 40, 20, fill="#efeaf7", w=5)
    rrect(ctx, x + 54, y + 209, max(1, (w - 108) * k), 32, 16, fill="#8be0a4", line=None)
    text(ctx, "learns from every reply", x + w / 2, y + 290, 24, F600, col="#6d6680")


def scr_inbox_zero(ctx, t, x, y, w, h):
    rrect(ctx, x, y, w, 60, 0, fill="#ff8fb0", line=None)
    text(ctx, "CUSTOMER INBOX", x + w / 2, y + 30, 28, F800, col=(1, 1, 1))
    k = beats.pop(t - 0.3, 0.35)
    ellipse(ctx, x + w / 2, y + 170, 70 * k + 1, 70 * k + 1, fill="#8be0a4", w=6)
    poly(ctx, [(x + w / 2 - 34, y + 170), (x + w / 2 - 8, y + 196), (x + w / 2 + 38, y + 146)], fill=None, w=12, close=False)
    text(ctx, "0 waiting", x + w / 2, y + 285, 40, F800, col="#2b2440")


def scr_shop(ctx, t, x, y, w, h):
    ctx.rectangle(x, y, w, h)
    ctx.set_source(lin(ctx, 0, y, 0, y + h, [(0, "#ffe1ec"), (1, "#ffc2d6")]))
    ctx.fill()
    for i in range(3):                                                                  # cards on display
        cx = x + 90 + i * 135
        a = 0.12 * math.sin(t * 2 + i)
        ctx.save()
        ctx.translate(cx, y + 160)
        ctx.rotate(a)
        rrect(ctx, -50, -70, 100, 140, 8, fill=("#ffffff", "#fff6c8", "#e8f0ff")[i], w=5)
        heart(ctx, 0, -10, 0.55, "#ff6b9a")
        poly(ctx, [(-30, 35), (30, 35)], w=4, close=False)
        ctx.restore()
    text(ctx, "my little stationery shop", x + w / 2, y + 285, 30, F800, col="#c2185b")


def scr_report(ctx, t, x, y, w, h):
    rrect(ctx, x, y, w, 60, 0, fill="#7ec8ff", line=None)
    text(ctx, "SALES REPORT", x + w / 2, y + 30, 28, F800, col=(1, 1, 1))
    vals = (0.45, 0.7, 0.55, 0.9, 0.75, 1.0)
    for i, v in enumerate(vals):
        k = ease((t - 0.2 - i * 0.12) / 0.4)
        bh = 170 * v * k
        rrect(ctx, x + 40 + i * 62, y + 270 - bh, 42, bh + 1, 6, fill=("#ff8fb0", "#c9a4ff")[i % 2], w=4)
    poly(ctx, [(x + 25, y + 272), (x + w - 25, y + 272)], w=4, close=False)
    k = beats.pop(t - 1.4, 0.3)
    if k > 0.02:
        rrect(ctx, x + w - 215, y + 75, 195 * k, 56 * k, 18, fill="#8be0a4", w=5)
        if k > 0.6:
            text(ctx, "DONE 8:00", x + w - 117, y + 103, 26, F800, col="#1d4d2b")
    text(ctx, "made by my script", x + w / 2, y + 305, 22, F600, col="#6d6680")


def scr_sheet(ctx, t, x, y, w, h, pick=3):
    """The answer sheet: rows of (question, my answer); a highlight scans down and lands on `pick`."""
    rrect(ctx, x, y, w, 50, 0, fill="#34a853", line=None)
    text(ctx, "MY ANSWER BRAIN (Google Sheet)", x + w / 2, y + 25, 22, F800, col=(1, 1, 1))
    rows = 6
    rh = (h - 60) / rows
    land = 0.9 + pick * 0.18
    cur = min(pick, int(t / 0.18) % (pick + 1)) if t < land else pick
    for i in range(rows):
        ry = y + 55 + i * rh
        if i == cur:
            rrect(ctx, x + 6, ry + 2, w - 12, rh - 4, 6, fill="#ffe08a" if t >= land else "#fff3c4", line=None)
        poly(ctx, [(x, ry + rh), (x + w, ry + rh)], line="#d8d4e3", w=2, close=False)
        rrect(ctx, x + 18, ry + rh / 2 - 7, 120 + (i * 37) % 50, 14, 7, fill="#b8b2c8", line=None)
        rrect(ctx, x + 200, ry + rh / 2 - 7, 170 + (i * 53) % 60, 14, 7, fill="#cfc9dd", line=None)
    poly(ctx, [(x + 185, y + 50), (x + 185, y + h)], line="#d8d4e3", w=2, close=False)
    if t >= land:
        ry = y + 55 + pick * rh
        k = beats.pop(t - land, 0.3)
        ellipse(ctx, x + w - 32, ry + rh / 2, 20 * k + 1, 20 * k + 1, fill="#34a853", w=4)


REPLY = ["Hi Jess! Great news:", "your invitations shipped", "today. Tracking below!", "- the shop :)"]


def scr_reply(ctx, t, x, y, w, h, typed=None):
    rrect(ctx, x, y, w, 56, 0, fill="#c9a4ff", line=None)
    text(ctx, "DRAFT REPLY", x + w / 2, y + 28, 26, F800, col=(1, 1, 1))
    n = sum(len(s) for s in REPLY)
    shown = int(n * (min(1, t / 1.8) if typed is None else typed))
    left = shown
    for i, s in enumerate(REPLY):
        part = s[:max(0, left)]
        left -= len(s)
        if part:
            text(ctx, part, x + 30, y + 100 + i * 52, 30, F600, col="#2b2440", anchor="lm")
    if (t * 2.5) % 1 < 0.6 and shown < n:                                              # blinking cursor
        i = min(len(REPLY) - 1, sum(1 for k in np.cumsum([len(s) for s in REPLY]) if k <= shown))
        rrect(ctx, x + 32 + 15 * (shown - sum(len(s) for s in REPLY[:i])), y + 82 + i * 52, 4, 36, 2, fill="#2b2440", line=None)


def scr_before_after(ctx, t, x, y, w, h):
    rrect(ctx, x, y, w / 2, h, 0, fill="#ffe1e1", line=None)
    rrect(ctx, x + w / 2, y, w / 2, h, 0, fill="#e1ffe9", line=None)
    poly(ctx, [(x + w / 2, y), (x + w / 2, y + h)], w=5, close=False)
    text(ctx, "BEFORE", x + w / 4, y + 45, 32, F800, col="#c62828")
    text(ctx, "NOW", x + 3 * w / 4, y + 45, 32, F800, col="#1b7a3a")
    # before: a clock spinning fast + "hours"
    cx, cy = x + w / 4, y + 165
    ellipse(ctx, cx, cy, 62, 62, fill=(1, 1, 1), w=6)
    a = t * 9
    poly(ctx, [(cx, cy), (cx + 48 * math.sin(a), cy - 48 * math.cos(a))], w=6, close=False)
    poly(ctx, [(cx, cy), (cx + 30 * math.sin(a / 12), cy - 30 * math.cos(a / 12))], w=8, close=False)
    text(ctx, "hours of", x + w / 4, y + 262, 26, F800, col="#2b2440")
    text(ctx, "typing", x + w / 4, y + 296, 26, F800, col="#2b2440")
    # now: three clicks
    k = beats.pop(t - 0.5, 0.3)
    for i in range(3):
        kk = beats.pop(t - 0.5 - i * 0.25, 0.25)
        ellipse(ctx, x + w / 2 + 60 + i * 55, y + 165, 20 * kk + 1, 20 * kk + 1, fill="#ff8fb0", w=4)
    text(ctx, "a few", x + 3 * w / 4, y + 262, 26 * max(k, .05), F800, col="#2b2440")
    text(ctx, "clicks", x + 3 * w / 4, y + 296, 26 * max(k, .05), F800, col="#2b2440")


def heart(ctx, x, y, s, col):
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ctx.move_to(0, 22)
    ctx.curve_to(-60, -20, -30, -60, 0, -28)
    ctx.curve_to(30, -60, 60, -20, 0, 22)
    ctx.set_source_rgb(*rgb(col))
    ctx.fill()
    ctx.restore()


def desk(ctx, t, x=HX, button=0.0, pressed=False):
    """Desk with her laptop (we see its lid) in front of her; button > 0 pops a big SEND button over it."""
    rrect(ctx, x - 200, 930, 400, 300, 24, fill="#dfe4ee", w=8)
    heart(ctx, x, 1070, 1.0, "#ff8fb0")
    rrect(ctx, -60, 1220, W + 120, 60, 14, fill="#d9a47c", w=8)
    rrect(ctx, -60, 1276, W + 120, 900, 0, fill="#b98560", w=8)
    rrect(ctx, 590, 1150, 70, 70, 14, fill="#ffffff", w=6)                               # pen cup
    for i, c in enumerate(("#ff6b9a", "#7ec8ff", "#ffd45e")):
        poly(ctx, [(605 + i * 20, 1150), (600 + i * 24, 1100)], line=c, w=8, close=False)
    if button > 0.02:
        k = button
        sy = 0.85 if pressed else 1.0
        rrect(ctx, x - 150 * k, 1110 - 55 * k * sy, 300 * k, 110 * k * sy, 55 * k, fill="#ff4f8b", w=8)
        if k > 0.5:
            text(ctx, "SEND", x, 1110, 64 * k, F800, col=(1, 1, 1))


def robot(ctx, x, y, t, s=1.0, eyes="open", arms=(15, 15), screen=None, label=None, bob=True, glow=0.0,
          holding=None):
    """Her cute assistant robot standing with its wheels at (x, y). arms: (left, right) degrees out from hanging."""
    b = 6 * math.sin(t * 4) if bob else 0
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ctx.save()
    ctx.scale(1, 0.16)
    ctx.arc(0, 0, 92, 0, 2 * math.pi)
    ctx.restore()
    ctx.set_source_rgba(0, 0, 0, 0.18)
    ctx.fill()
    ctx.translate(0, -b)
    if glow > 0.02:
        ctx.set_source(rad(ctx, 0, -330, 260, [(0, "#fff3a0", .7 * glow), (1, "#fff3a0", 0)]))
        ctx.paint()
    rrect(ctx, -72, -36, 144, 36, 18, fill="#5b5470", w=6)                                # wheels
    for wx in (-40, 0, 40):
        ellipse(ctx, wx, -18, 10, 10, fill="#8d86a6", line=None)
    for side, ang in ((-1, arms[0]), (1, arms[1])):                                      # arms
        ctx.save()
        ctx.translate(side * 82, -150)
        ctx.rotate(-side * math.radians(ang))
        rrect(ctx, -15, 0, 30, 92, 15, fill="#b3a3f0", w=6)
        ellipse(ctx, 0, 100, 22, 22, fill="#ff8fb0", w=6)
        if holding and side == 1:
            ctx.save()
            ctx.translate(0, 120)
            ctx.rotate(side * math.radians(ang))
            holding(ctx)
            ctx.restore()
        ctx.restore()
    rrect(ctx, -84, -178, 168, 146, 30, fill="#c9b8ff", w=7)                              # body
    heart(ctx, 0, -100, 0.6, "#ff6b9a")
    if label:
        rrect(ctx, -70, -70, 140, 34, 10, fill="#fff6c8", w=5)
        text(ctx, label, 0, -53, 22, F800, col="#2b2440")
    rrect(ctx, -18, -196, 36, 24, 6, fill="#8d86a6", w=5)                                 # neck
    poly(ctx, [(0, -345), (0, -390)], w=6, close=False)                                   # antenna
    ellipse(ctx, 0, -398, 15, 15, fill="#ff4f8b" if (t * 2) % 1 < 0.6 else "#ffb3cb", w=5)
    rrect(ctx, -104, -345, 208, 156, 42, fill="#ffffff", w=7)                             # head
    rrect(ctx, -82, -323, 164, 112, 28, fill="#2b2440", line=None)                        # face screen
    if screen == "sheet":
        for i in range(4):
            for j in range(3):
                on = i == int(t * 6) % 4
                rrect(ctx, -66 + j * 46, -308 + i * 24, 40, 18, 4, fill="#ffe08a" if on else "#5e5680", line=None)
    else:
        blink = (t % 2.7) < 0.12
        for ex in (-36, 36):
            if eyes == "happy" or blink:
                curve_eye(ctx, ex, -262, blink)
            elif eyes == "heart":
                heart(ctx, ex, -262, 0.42, "#ff6b9a")
            elif eyes == "scan":
                rrect(ctx, ex - 20, -268, 40, 12, 6, fill="#7ef0ff", line=None)
            else:
                rrect(ctx, ex - 15, -288, 30, 42, 14, fill="#7ef0ff", line=None)
        ctx.arc(0, -238, 18, 0.2, math.pi - 0.2)
        ctx.set_source_rgb(*rgb("#7ef0ff"))
        ctx.set_line_width(5)
        ctx.stroke()
    ctx.restore()


def curve_eye(ctx, x, y, flat):
    ctx.move_to(x - 18, y + (0 if flat else 6))
    if flat:
        ctx.line_to(x + 18, y)
    else:
        ctx.curve_to(x - 10, y - 14, x + 10, y - 14, x + 18, y + 6)
    ctx.set_source_rgb(*rgb("#7ef0ff"))
    ctx.set_line_width(7)
    ctx.stroke()


def msg_card(ctx, x, y, rot, s, msg, alpha=1.0):
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(rot)
    ctx.scale(s, s)
    rrect(ctx, -150, -46, 300, 92, 20, fill="#ffffff", w=6)
    rrect(ctx, -134, -28, 64, 46, 6, fill="#ff8fb0", w=4)                                # envelope
    poly(ctx, [(-134, -28), (-102, 0), (-70, -28)], fill=None, w=4, close=False)
    text(ctx, msg, -58, -2, 21, F800, col="#2b2440", anchor="lm")
    ctx.restore()


rng = np.random.default_rng(7)
PILE = [dict(x=rng.uniform(60, 1020), delay=i * 0.045 + rng.uniform(0, 0.12), rot=rng.uniform(-0.5, 0.5),
             land=FLOOR - 40 - (i // 7) * 62 - rng.uniform(0, 25), msg=MESSAGES[i % len(MESSAGES)])
        for i in range(56)]


def pile(ctx, T):
    """The inbox avalanche T s after it starts: cards fall (gravity), land and stack up around her."""
    for c in PILE:
        tt = T - c["delay"]
        if tt <= 0:
            continue
        y = -250 + 2600 * tt * tt
        if y >= c["land"]:
            over = tt - math.sqrt((c["land"] + 250) / 2600)
            y = c["land"] - 30 * abs(math.sin(over * 14)) * math.exp(-over * 8)
        msg_card(ctx, c["x"], y, c["rot"] + (0.6 * (1 - min(1, tt * 2)) if y < c["land"] else 0), 0.9, c["msg"])


def plane(ctx, t, x0, y0):
    """The reply flying away as a paper plane."""
    if t < 0:
        return
    x, y = x0 + 1300 * t, y0 - 900 * t + 300 * t * t
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(-0.5)
    poly(ctx, [(-50, -10), (60, 0), (-50, 30), (-30, 6)], fill="#ffffff", w=5)
    poly(ctx, [(-30, 6), (60, 0)], w=4, close=False)
    ctx.restore()
    for i in range(1, 5):                                                               # speed lines
        poly(ctx, [(x - 70 - i * 40, y + 10 + i * 12), (x - 110 - i * 40, y + 18 + i * 14)], w=4, close=False)


def bulb(ctx, x, y, k, t):
    if k <= 0.02:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(k, k)
    ctx.set_source(rad(ctx, 0, 0, 160, [(0, "#fff7b0", .8), (1, "#fff7b0", 0)]))
    ctx.paint()
    ellipse(ctx, 0, 0, 48, 52, fill="#ffe45e", w=6)
    rrect(ctx, -22, 44, 44, 34, 8, fill="#c8c2d6", w=5)
    for i in range(8):
        a = i * math.pi / 4 + t
        poly(ctx, [(70 * math.cos(a), 70 * math.sin(a)), (92 * math.cos(a), 92 * math.sin(a))], w=6, close=False)
    ctx.restore()


def sparkles(ctx, t, pts, size=22):
    for i, (x, y) in enumerate(pts):
        r = size * (0.6 + 0.4 * math.sin(t * 7 + i * 1.7))
        poly(ctx, [(x, y - r * 2), (x + r * .4, y - r * .4), (x + r * 2, y), (x + r * .4, y + r * .4), (x, y + r * 2),
                   (x - r * .4, y + r * .4), (x - r * 2, y), (x - r * .4, y - r * .4)], fill="#ffd45e", w=4)


# ------------------------------------------------------------------ shots
def shots():
    S = []

    def add(key, lead, tail, scene, fg, cam0, cam1, act, sfx=()):
        S.append(dict(key=key, lead=lead, tail=tail, scene=scene, fg=fg, cam0=cam0, cam1=cam1, act=act, sfx=list(sfx)))

    def sit(face, pose="rest", look=None, props=None, steps=None, eyes=None, mouth=None, tilt=3, x=HX):
        def f(t, d, ls, le):
            arms = moves(t, steps, props) if steps else (blend(pose, pose, 1, props) if pose != "rest" else {})
            return dict(pos=stand(x, dy=-70), face=face, arms=arms, look=look, eyes=eyes, mouth=mouth, tilt=tilt)
        return f

    mug = {"right": P.mug(0.5)}

    # 1. intro: hi to the camera, her shop on the monitor
    def wave(t, d, ls, le):
        arms = blend("hip_wave", "hip_wave", 1)
        l = list(arms["left"])
        l[2] += 18 * math.sin(t * 10)
        arms["left"] = tuple(l)
        return dict(pos=stand(HX, dy=-70), face="happy" if t < ls + 1.5 else "smug", arms=arms, tilt=4 * math.sin(t * 3))
    add("intro", 0.1, 0.3, lambda c, t: office(c, t, scr_shop), lambda c, t: (desk(c, t), robot(c, RX, RY, t)),
        (1.0, 540, 950), (1.08, 540, 930), wave, [("pop", 0.1)])

    # 2. hook: at her desk with coffee, inbox zero on the monitor
    add("hook", 0.15, 0.25, lambda c, t: office(c, t, scr_inbox_zero), lambda c, t: (desk(c, t), robot(c, RX, RY, t, eyes="happy")),
        (1.15, 560, 900), (1.45, 470, 800), sit("smug", steps=[(0, "chest"), (0.6, "sip"), (1.3, "chest")], props=mug),
        [("whoosh", 0), ("sip", 0.7)])

    # 3. 8 AM: the sales report is already done (she looks over at the monitor, sipping)
    add("eight", 0.2, 0.5, lambda c, t: office(c, t, scr_report, st=0.1), lambda c, t: desk(c, t),
        (1.38, 630, 720), (1.48, 650, 700),
        sit("smug", look=(2.6, -1.0), steps=[(0, "chest"), (2.6, "sip")], props=mug, tilt=-3),
        [("whoosh", 0), ("ding", 1.55)])

    # 4. the problem: standing in the office, then the inbox avalanche
    def standing(face, pose="rest", look=None, tilt=0, x=540, eyes=None, mouth=None, dy=0.0):
        return lambda t, d, ls, le: dict(pos=stand(x, dy=dy), face=face, arms=blend(pose, pose, 1) if pose != "rest" else {},
                                         look=look, tilt=tilt, eyes=eyes, mouth=mouth)
    add("problem", 0.15, 0.55, lambda c, t: office(c, t, scr_inbox_full), lambda c, t: pile(c, t - S[3]["le"] - 0.2),
        (1.2, 540, 900), (1.3, 540, 880), standing("annoyed", "shrug", tilt=-4), [("notif", ("le", 0.2))])

    def buried(t, d, ls, le):
        k = ease(t / 0.4)
        return dict(pos=stand(540), face="surprised", arms=blend("shrug", "cheeks", k), tilt=0,
                    rot=2 * math.sin(t * 40) * max(0, 1 - t / 1.2))
    add(None, 0, 1.6, lambda c, t: office(c, t, scr_inbox_full), lambda c, t: pile(c, t + S[3]["tail"] - 0.2),
        (1.0, 540, 960), (0.95, 540, 980), buried,
        [("notif", 0.0), ("notif", 0.25), ("notif", 0.45), ("notif", 0.6), ("notif", 0.8), ("notif", 1.0), ("scratch", 1.2)])

    def pain(t, d, ls, le):
        return dict(pos=stand(540), face="annoyed", arms={}, tilt=6 * math.sin(t * 1.5), look=(0, 0))
    add("pain", 0.1, 0.4, lambda c, t: office(c, t, scr_inbox_full), lambda c, t: (pile(c, 9 + t), beats.emote(c, "sweat", (560, 600), 170, 1, t)),
        (1.35, 540, 760), (1.5, 540, 740), pain, [("notif", 1.0), ("notif", 2.2), ("notif", 3.4)])

    # 5. so I built a robot: it pops up on her desk
    def built(t, d, ls, le):
        return dict(pos=stand(HX, dy=-70), face="excited", arms=blend("rest", "yay", ease(t / .3)), tilt=-5)

    def robot_pop(c, t):
        k = beats.pop(t - 0.25, 0.4)
        desk(c, t)
        if k > 0.02:
            robot(c, RX, RY, t, s=k, eyes="happy")
        sparkles(c, t, [(700, 800), (960, 760), (900, 600)] if t > 0.4 else [])
    add("built", 0.1, 0.6, lambda c, t: office(c, t, scr_inbox_full), robot_pop, (1.1, 600, 900), (1.18, 620, 880), built, [("boing", 0.25), ("brightsting", 0.35)])

    # 6. it reads every message (scan beam)
    def reads_fg(c, t):
        desk(c, t)
        robot(c, RX, RY, t, eyes="scan", arms=(15, 60))
        k = 0.5 + 0.5 * math.sin(t * 6)
        cy = RY - 520 + 12 * math.sin(t * 3)
        c.move_to(RX, RY - 262)
        c.line_to(RX - 150, cy - 40 + 70 * k)
        c.line_to(RX + 150, cy - 40 + 70 * k)
        c.close_path()
        c.set_source_rgba(0.5, 0.95, 1.0, 0.35)
        c.fill()
        msg_card(c, RX, cy, -0.05, 1.0, "Where's my order??")
    add("reads", 0.2, 0.5, lambda c, t: office(c, t, scr_inbox_full), reads_fg, (1.45, 700, 860), (1.55, 720, 850), sit("surprised", look=(2.6, -0.8)),
        [("whoosh", 0), ("tick", 0.4), ("tick", 0.8), ("tick", 1.2)])

    # 7. checks its brain: the answer sheet on the monitor, a matching row lights up
    add("brain", 0.2, 0.5, lambda c, t: office(c, t, scr_sheet, st=0.2),
        lambda c, t: (desk(c, t), robot(c, RX, RY, t, screen="sheet", arms=(15, 140 + 10 * math.sin(t * 3)))),
        (1.22, 680, 820), (1.3, 700, 800), sit("smug", look=(2.6, -1.2), tilt=-3),
        [("whoosh", 0), ("tick", 0.4), ("tick", 0.6), ("tick", 0.8), ("tick", 1.0), ("ding", 1.65)])

    # 8. writes the reply
    def typing_robot(c, t):
        desk(c, t)
        robot(c, RX, RY, t, eyes="happy", arms=(40 + 15 * math.sin(t * 22), 40 + 15 * math.sin(t * 22 + 2)))
    add("writes", 0.2, 0.6, lambda c, t: office(c, t, scr_reply, st=0.25), typing_robot,
        (1.42, 690, 700), (1.5, 700, 680), sit("happy", look=(2.6, -1.2)), [("typing", 0)])

    # 9. I read it, I hit send, done (big button, the reply flies off as a paper plane)
    def send(t, d, ls, le):
        pressing = 1.15 < t < 1.6
        return dict(pos=stand(HX, dy=-70), face="smug" if t < 1.6 else "happy",
                    arms=moves(t, [(0, "rest"), (0.9, "rest"), (1.25, "press"), (1.75, "thumbs")]), tilt=3,
                    look=(0, 1.5) if t < 1.2 else None)

    def send_fg(c, t):
        desk(c, t, button=beats.pop(t - 0.75, 0.3) if t < 2.3 else max(0, 1 - (t - 2.3) * 4), pressed=1.25 < t < 1.6)
        robot(c, RX, RY, t, eyes="heart")
        plane(c, t - 1.45, HX + 100, 1050)
    add("send", 0.15, 0.7, lambda c, t: office(c, t, lambda *a: scr_reply(*a, typed=1.0)), send_fg,
        (1.25, 470, 880), (1.35, 470, 860), send, [("pop", 0.75), ("click", 1.3), ("whoosh", 1.45), ("ding", 1.7)])

    # 10. it even sounds like me, just nicer before coffee
    add("nicer", 0.1, 0.5, lambda c, t: office(c, t, lambda *a: scr_reply(*a, typed=1.0)),
        lambda c, t: (desk(c, t), robot(c, RX, RY, t, eyes="heart")),
        (1.5, 470, 780), (1.6, 470, 770), sit("smug", steps=[(0, "chest"), (1.6, "sip")], props=mug, eyes=None),
        [("sip", 1.7)])

    # 11. today's upgrade: a real memory (lightbulb, sent replies fly into its head)
    def memory_fg(c, t):
        desk(c, t)
        g = ease((t - 0.3) / 0.6)
        robot(c, RX, RY, t, eyes="happy", glow=g, arms=(25, 25))
        bulb(c, RX, RY - 520, beats.pop(t - 0.4, 0.35), t)
        for i in range(5):                                                               # replies flying in
            tt = (t * 0.7 + i / 5) % 1
            msg_card(c, lerp(150 + i * 60, RX, tt), lerp(400 + i * 50, RY - 280, tt), 0, 0.55 * (1 - tt * .8), "reply sent")
    add("memory", 0.2, 0.5, lambda c, t: office(c, t, scr_memory, st=0.2), memory_fg, (1.35, 760, 820), (1.5, 790, 800), sit("happy", look=(2.6, -0.5)),
        [("brightsting", 0.4)])

    # 12. I'm the boss, it's the intern
    def boss(t, d, ls, le):
        return dict(pos=stand(360), face="smug", arms=blend("hip", "hip", 1), tilt=5)

    def boss_fg(c, t):
        robot(c, 800, FLOOR, t, s=1.15, eyes="happy", arms=(15, 150 if t > 2.2 else 15), label="INTERN")
        k = beats.pop(t - 2.0, 0.3)
        if k > 0.02:
            rrect(c, 360 - 110 * k, 236, 220 * k, 76 * k, 20, fill="#ffd45e", w=6)
            if k > 0.6:
                text(c, "BOSS", 360, 274, 48, F800, col="#2b2440")
    add("boss", 0.1, 0.6, office, boss_fg, (1.0, 560, 940), (1.08, 560, 920), boss, [("pop", 2.0), ("pop", 2.3)])

    # 13. result: hours -> a few clicks
    def result(t, d, ls, le):
        hop = 260 * math.sin(math.pi * (t - 1.0) / 0.6) if 1.0 <= t <= 1.6 else 0.0
        return dict(pos=stand(HX, dy=hop), face="excited", arms=blend("rest", "yay", ease((t - 0.8) / .3)),
                    tilt=4 * math.sin(t * 5))
    add("result", 0.2, 0.7, lambda c, t: office(c, t, scr_before_after, st=0.2),
        lambda c, t: (robot(c, 830, FLOOR, t, s=1.0, eyes="heart", arms=(120, 120)), D.confetti(c, t - 1.05, 540, 800)),
        (1.05, 600, 920), (1.12, 620, 900), result, [("whoosh", 0), ("boing", 1.0), ("pop", 1.1), ("thud", 1.6)])

    # 14. call to action
    def outro(t, d, ls, le):
        return dict(pos=stand(400, dy=10 * abs(math.sin(t * 3))), face="wink", arms=blend("rest", "peace", ease(t / .35)),
                    tilt=-5)
    add("cta", 0.2, 2.0, D.outro_bg, lambda c, t: robot(c, 820, FLOOR, t, s=1.0, eyes="happy", arms=(15, 150 + 20 * math.sin(t * 8))),
        (1.0, 560, 960), (1.12, 560, 900), outro, [("chime", 0.2)])
    return S


# ------------------------------------------------------------------ sound: the day video's effects + a few more
_fx = D.fx


def fx(name, n=1.0):
    if name in ("notif", "tick", "scratch", "brightsting", "click"):
        return beats.sfx("pop" if name == "click" else name)
    return _fx(name, n)


D.fx = fx


# ------------------------------------------------------------------ overlay
def header(frame):
    d = ImageDraw.Draw(frame)
    d.rounded_rectangle((190, 80, W - 190, 200), 34, fill=(255, 255, 255), outline=(30, 24, 30), width=6)
    d.text((W / 2, 128), "BUILD DAY", font=D.font(54), fill=D.PINK, anchor="mm")
    d.text((W / 2, 176), "(a day in my business)", font=D.font(30), fill=(90, 80, 90), anchor="mm")


def overlay(frame, S, s, t, T):
    header(frame)
    D.captions(frame, s, T)
    if s is S[-1] and t > s["le"] + .1:
        d = ImageDraw.Draw(frame)
        k = min(1, (t - s["le"] - .1) / .3)
        d.rounded_rectangle((150, 1560, W - 150, 1780), 40, fill=D.PINK)
        d.text((W / 2, 1635), "comment ROBOT", font=D.font(64 * k + 1), fill=(255, 255, 255), anchor="mm")
        d.text((W / 2, 1715), "and I'll show you how it works", font=D.font(36 * k + 1), fill=(255, 255, 255), anchor="mm")


if __name__ == "__main__":
    D.render(sys.argv[1] if len(sys.argv) > 1 else "video_robot.mp4", shots(), LINES, VOICE, overlay)
