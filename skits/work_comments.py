"""'Things to say at work (from the comments)' - 10 short office scenes (each under 10 s): something happens -> the
line -> a deadpan reaction (no laughing). Stylized stick people, props, and a different camera
angle for each beat (wide, close-ups, inserts, low angle, dutch tilt, push-ins). ~65 s, 1080x1920.

    python skits/work_comments.py out.mp4          # script: work_lines.py
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
import voices                                                        # noqa: E402
from five_min import ogg, synth                                      # noqa: E402
from stick_people import LOOKS, StickPerson                          # noqa: E402
from toon import OUT, curve, ellipse, lin, poly, rad, rgb, rrect, text   # noqa: E402
from work_lines import BOSS, COWORKER, LINES, WORKER                 # noqa: E402

W, H, FPS, SR = 1080, 1920, 24, voices.SR
FONT = os.path.join(HERE, "assets", "poppins-800.ttf")
FONT2 = os.path.join(HERE, "assets", "poppins-600.ttf")
FLOOR = 1560
WX, CX, BX = 560, 210, 900                 # worker (at her desk), coworker (his desk, left), boss (comes in, right)
REST_D = ((10, -60), (10, -60))            # forearms on the desk
REST = ((10, 8), (10, 8))                  # arms hanging
TXT = {k: l.split("] ", 1)[1] for k, _, l in LINES}


def ease(t):
    return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, t)))


def lerp(a, b, k):
    return a + (b - a) * k


def walk_legs(t, speed=1.0):
    s = math.sin(t * 9 * speed)
    return ((18 * s, max(0, -30 * s)), (-18 * s, max(0, 30 * s)))


# ------------------------------------------------------------------ the set
def office(ctx, t, clock="8:45", cal="MON", sunset=0.0, dark=0.0):
    top = [(0, "#e9eef8"), (1, "#d3dcec")] if sunset < .5 else [(0, "#ffd9b8"), (1, "#f7b9a0")]
    ctx.rectangle(-3000, -3000, W + 6000, FLOOR + 3000)
    ctx.set_source(lin(ctx, 0, 0, 0, FLOOR, top))
    ctx.fill()
    ctx.rectangle(-3000, FLOOR, W + 6000, 3000)
    ctx.set_source_rgb(*rgb("#8a93a6"))
    ctx.fill()
    for x in range(-600, W + 600, 180):                                              # carpet tiles
        poly(ctx, [(x, FLOOR), (x - 80, FLOOR + 400)], line="#7c8598", w=4, close=False)
    sky = [(0, "#8fd3ff"), (1, "#e8f7ff")] if sunset < .5 else [(0, "#ff9a6b"), (1, "#ffd28a")]
    rrect(ctx, 330, 330, 420, 380, 16, fill=lin(ctx, 0, 330, 0, 710, sky), w=10)     # window + city
    for bx, bw, bh in ((350, 70, 200), (430, 100, 290), (540, 60, 160), (610, 90, 250), (700, 40, 190)):
        rrect(ctx, bx, 710 - bh, bw, bh, 6, fill="#9fb0d8" if sunset < .5 else "#b9788a", line=None)
    poly(ctx, [(540, 330), (540, 710)], w=8, close=False)
    ellipse(ctx, 130, 470, 72, 72, fill=(1, 1, 1), w=7)                              # clock
    hh, mm = (int(x) for x in clock.split(":"))
    for ang, L_, lw in ((math.radians((hh % 12 + mm / 60) * 30), 38, 8), (math.radians(mm * 6), 55, 6)):
        poly(ctx, [(130, 470), (130 + L_ * math.sin(ang), 470 - L_ * math.cos(ang))], w=lw, close=False)
    rrect(ctx, 820, 380, 170, 190, 10, fill=(1, 1, 1), w=7)                          # wall calendar
    rrect(ctx, 820, 380, 170, 55, 10, fill="#e0457b", w=7)
    text(ctx, cal, 905, 500, 64, FONT, col="#2a2b2c")
    rrect(ctx, 820, 1010, 190, 22, 6, fill="#c89a74", w=6)                           # shelf + plant
    rrect(ctx, 870, 890, 90, 120, 12, fill="#e58f6a", w=6)
    for a in (-0.7, -0.2, 0.3, 0.8):
        ellipse(ctx, 915 + 60 * math.sin(a), 835 - 50 * math.cos(a), 26, 52, fill="#6cc48a", w=5)


def desks(ctx, t, laptop=True, mug=True):
    """Her desk (centre, hides her legs: she's seated) and the coworker's (left)."""
    for x0, x1 in ((360, 780), (-60, 330)):
        rrect(ctx, x0, 1310, x1 - x0, 50, 12, fill="#c89a74", w=8)
        rrect(ctx, x0 + 20, 1356, x1 - x0 - 40, 600, 0, fill="#a8764f", w=8)
    if laptop:
        rrect(ctx, 450, 1150, 230, 160, 14, fill="#dfe4ee", w=7)                        # laptop (its lid)
        ellipse(ctx, 565, 1230, 18, 16, fill="#ff8fb0", line=None)
    if mug:
        rrect(ctx, 700, 1240, 56, 70, 10, fill="#ffffff", w=6)
        curve(ctx, [(756, 1255), (776, 1270), (756, 1290)], w=6)
    rrect(ctx, 40, 1180, 170, 130, 10, fill="#2a2b2c", w=6)                             # his monitor
    rrect(ctx, 52, 1192, 146, 100, 6, fill="#7ec8ff", line=None)


def printer(ctx, t, x=860, jam=False, shake=0.0, paper=0.0, smoke=0.0):
    x += shake
    rrect(ctx, x - 40, 1330, 250, 230, 8, fill="#b9c3cc", w=7)                         # stand
    rrect(ctx, x - 70, 1150, 310, 190, 20, fill="#e9eef6", w=8)
    rrect(ctx, x - 40, 1180, 250, 40, 8, fill="#2a2b2c", w=5)
    if jam and int(t * 4) % 2 == 0:
        ellipse(ctx, x + 190, 1290, 14, 14, fill="#ff4d4d", line=None)
        text(ctx, "JAM", x + 150, 1290, 26, FONT, col="#ff4d4d")
    if paper > 0:                                                                      # sheet shooting out
        px = x + 80 - 260 * paper
        ctx.save()
        ctx.translate(px, 1230 - 60 * math.sin(math.pi * paper))
        ctx.rotate(-0.6 * paper)
        rrect(ctx, -60, -40, 120, 80, 4, fill=(1, 1, 1), w=4)
        ctx.restore()
    for k in range(int(smoke * 6)):
        ellipse(ctx, x + 60 + 30 * math.sin(t * 2 + k), 1120 - k * 70 - (t * 60) % 70, 50 + k * 12, 40 + k * 10,
                fill="#9aa0aa", line=None)


def cable(ctx):
    curve(ctx, [(300, FLOOR - 4), (420, FLOOR - 16), (520, FLOOR - 2), (640, FLOOR - 14), (760, FLOOR - 4)],
          line="#2a2b2c", w=12)


def inbox(ctx, t):
    """Insert: her laptop screen, 347 unread."""
    rrect(ctx, 90, 420, 900, 620, 30, fill="#2a2b2c", w=10)
    rrect(ctx, 120, 450, 840, 560, 12, fill="#ffffff", line=None)
    rrect(ctx, 120, 450, 840, 80, 12, fill="#2f6fb0", line=None)
    text(ctx, "Inbox", 250, 490, 40, FONT, col=(1, 1, 1))
    n = 340 + int(min(7, t * 6))
    rrect(ctx, 700, 465, 230, 50, 25, fill="#e0457b", line=None)
    text(ctx, f"{n} unread", 815, 490, 32, FONT, col=(1, 1, 1))
    for i in range(6):
        y = 560 + i * 72
        ellipse(ctx, 170, y + 20, 22, 22, fill=["#6cc48a", "#ffd45e", "#7ec8ff", "#ff8fb0", "#c9a4ff", "#e58f6a"][i], line=None)
        rrect(ctx, 210, y + 5, 400 - (i % 3) * 60, 16, 8, fill="#2a2b2c", line=None)
        rrect(ctx, 210, y + 30, 600 - (i % 2) * 120, 12, 6, fill="#b9c3cc", line=None)


def clipboard(ctx, hands, i=1):
    x, y = hands[i]
    rrect(ctx, x - 55, y - 110, 110, 150, 10, fill="#c89a74", w=6)
    rrect(ctx, x - 44, y - 92, 88, 122, 4, fill=(1, 1, 1), w=3)
    rrect(ctx, x - 20, y - 120, 40, 22, 6, fill="#b9c3cc", w=4)
    for k in range(4):
        poly(ctx, [(x - 32, y - 70 + k * 22), (x + 30, y - 70 + k * 22)], line="#b9c3cc", w=3, close=False)


def pen(ctx, hands, i=0):
    x, y = hands[i]
    poly(ctx, [(x, y), (x + 10, y - 60)], line="#2f6fb0", w=9, close=False)


def mug(ctx, hands, i=1, sipping=False):
    x, y = hands[i]
    rrect(ctx, x - 30, y - 80, 60, 80, 10, fill="#ffffff", w=6)
    curve(ctx, [(x + 30, y - 66), (x + 50, y - 50), (x + 30, y - 30)], w=6)
    if not sipping:
        for k in range(3):
            curve(ctx, [(x - 12 + k * 12, y - 90), (x - 18 + k * 12, y - 110), (x - 10 + k * 12, y - 130)],
                  line=(1, 1, 1), w=5)


# ------------------------------------------------------------------ scenes
def person(key, x, floor=FLOOR, facing=0.0, scale=1.0):
    return StickPerson(LOOKS[key], x=x, floor=floor, scale=scale, facing=facing)


def draw_people(ctx, t, m, talk, cast):
    """cast: [(StickPerson, voice, dict(draw kwargs))]. talk(voice) -> mouth 0..1."""
    for p, voice, kw in cast:
        kw = dict(kw)
        kw.setdefault("blink", (t + hash(voice) % 7 * .37) % 3.4 < .1)
        kw["mouth"] = max(kw.get("mouth", 0), talk(voice))
        extra = kw.pop("xform", None)
        if extra:
            ctx.save()
            extra(ctx)
        p.draw(ctx, **kw)
        if extra:
            ctx.restore()


def sc_friday(ctx, t, m, talk):
    office(ctx, t, "8:45", "MON")
    k = ease((t - m["friday"][0] + .3) / .3)
    wave = 15 * math.sin(t * 12) * (m["friday"][0] < t < m["friday"][1])
    draw_people(ctx, t, m, talk, [
        (person("coworker", CX, facing=.5), COWORKER, dict(arms=REST_D, face="annoyed" if t > m["friday"][0] + .5 else "neutral",
                                                             look=(1, 0))),
        (person("worker", WX, facing=-.2), WORKER, dict(arms=((lerp(10, 150, k), lerp(-60, 20 + wave, k)), (lerp(10, 150, k), lerp(-60, 20 - wave, k))),
                                                        face="happy", look=(0, 0))),
    ])
    desks(ctx, t)


def sc_fanmail(ctx, t, m, talk):
    if t < m["fanmail"][0] - .1:
        ctx.set_source_rgb(*rgb("#dfe4ee"))
        ctx.paint()
        inbox(ctx, t)
        return
    office(ctx, t)
    tt = t - m["fanmail"][0]
    draw_people(ctx, t, m, talk, [
        (person("worker", WX, facing=-.1), WORKER, dict(arms=((10, -60), (120 + 10 * math.sin(tt * 3), 60)), face="smug",
                                                        look=(0, 0), tilt=4, hair_sway=.5 * math.sin(tt * 3))),
    ])
    desks(ctx, t)


def sc_sign(ctx, t, m, talk):
    office(ctx, t)
    walk = ease(t / 1.2)
    cx = lerp(-150, WX - 250, walk)
    walking = t < 1.2
    signing = m["sign_a"][0] - .6 < t < m["sign_a"][0] + .1
    after = t > m["sign_a"][1]
    wiggle = 25 * math.sin(t * 30) if signing else 0
    draw_people(ctx, t, m, talk, [
        (person("coworker", cx, facing=.6), COWORKER, dict(arms=((12, 8), (35, -110)), legs=walk_legs(t) if walking else ((4, 0), (4, 0)),
                                                             face="annoyed" if after else "neutral",
                                                             look=(0, -1.4) if after else (1, 0), hold=clipboard)),
        (person("worker", WX, facing=-.3), WORKER, dict(arms=((50 + wiggle * .3, -100 + wiggle), (10, -60)), face="smug",
                                                        look=(-1, .6) if signing else (-.6, 0), hold=pen)),
    ])
    desks(ctx, t, laptop=False)


def sc_trip(ctx, t, m, talk):
    office(ctx, t)
    cable(ctx)
    x = lerp(150, 700, ease(t / 1.6)) if t < 1.6 else 700
    trip = max(0, 1 - abs(t - 1.0) / .35)                             # stumble at the cable
    after = t > m["trip"][1]
    rot = -22 * trip
    xf = (lambda c: (c.translate(x, FLOOR), c.rotate(math.radians(rot)), c.translate(-x, -FLOOR)))
    cast = [(person("worker", x, facing=.4 if t < 1.6 else 0), WORKER,
             dict(arms=((60 * trip + 10, 20), (80 * trip + 10, 30)) if t < 1.6 else ((40, 110), (10, 8)),
                  legs=walk_legs(t) if t < 1.6 else ((4, 0), (4, 0)),
                  face="shock" if trip > .3 else "annoyed", look=(0, 0), xform=xf))]
    if after:                                                             # the coworker sheepishly picks the cable up
        k = ease((t - m["trip"][1]) / .5)
        cast.append((person("coworker", lerp(-150, 330, k), facing=.3), COWORKER,
                     dict(arms=((60, 40), (60, 40)), legs=((4, 0), (4, 0)), face="sad", look=(1, .8))))
    draw_people(ctx, t, m, talk, cast)


def sc_sneeze(ctx, t, m, talk):
    office(ctx, t)
    s0, s1 = m["sneeze"]
    jerk = 0
    for at in (s0 + .35, s0 + .95):
        jerk += 30 * math.exp(-((t - at) / .08) ** 2)
    after = t > m["sneeze_a"][1]
    draw_people(ctx, t, m, talk, [
        (person("coworker", CX, facing=.3), COWORKER, dict(arms=((40, -120), (40, -120)) if s0 < t < s1 + .2 else REST_D,
                                                             face="sad" if after else ("closed" if s0 < t < s1 else "neutral"),
                                                             bob=jerk, tilt=jerk * .4, look=(1, 0))),
        (person("worker", WX, facing=0), WORKER, dict(arms=REST_D, face="neutral", look=(0, 1.2))),     # doesn't look up
    ])
    desks(ctx, t)


def sc_wifi(ctx, t, m, talk):
    office(ctx, t)
    q0, q1 = m["wifi"]
    silent = q1 < t < m["secrets"][0]
    draw_people(ctx, t, m, talk, [
        (person("coworker", CX, facing=-.4), COWORKER, dict(arms=REST_D, face="neutral", look=(-1.2, -.6) if silent else (1, 0))),
        (person("boss", BX, facing=.4), BOSS, dict(arms=((20, -110), (12, 8)), face="neutral", look=(1.3, -.8) if silent else (-1, 0))),
        (person("worker", WX, facing=0), WORKER, dict(arms=((40, 100), (10, -60)) if t < q1 else REST_D,
                                                      face="annoyed" if t > m["secrets"][0] - .2 else "neutral", look=(0, 0))),
    ])
    desks(ctx, t)


def sc_bucks(ctx, t, m, talk):
    office(ctx, t)
    hit = [1.0, 1.6]
    shake = sum(12 * math.sin(t * 90) * max(0, 1 - abs(t - h) / .2) for h in hit)
    paper = ease((t - 2.0) / .6) if 2.0 < t < 2.8 else 0
    printer(ctx, t, jam=t < 2.0, shake=shake, paper=paper)
    arm = max(math.exp(-((t - h) / .12) ** 2) for h in hit)
    after = t > m["bucks"][1] - .3
    draw_people(ctx, t, m, talk, [
        (person("coworker", 150, facing=.4), COWORKER, dict(arms=REST, face="neutral", look=(1, 0), bob=10 * math.sin(t * 5) if after else 0)),
        (person("worker", 600, facing=.5 if t < 2.4 else -.1), WORKER,
         dict(arms=((12, 8), (lerp(40, 150, arm), lerp(60, 10, arm))), face="annoyed" if t < 2.4 else "smug", look=(1, 0) if t < 2.4 else (0, 0))),
    ])


def sc_deadline(ctx, t, m, talk):
    office(ctx, t)
    a0, a1 = m["allow"]
    after = t > a1
    draw_people(ctx, t, m, talk, [
        (person("boss", BX - 20, facing=-.5), BOSS, dict(arms=((20, -100), (12, 8)), face="neutral",
                                                        look=(-1, 0) if not after else (-1.3, -.3), tilt=-6 if after else 0)),
        (person("worker", WX, facing=.2), WORKER, dict(arms=((60, 120), (10, -60)) if a0 - .8 < t else REST_D,
                                                       face="annoyed" if t < a0 + .8 else "smug", look=(1, 0))),
    ])
    desks(ctx, t)


def sc_fun(ctx, t, m, talk):
    office(ctx, t)
    f0, f1 = m["fun"]
    frozen = t > f1 + .1
    fly = t if not frozen else f1 + .1
    printer(ctx, fly, smoke=1.0, x=900)
    rng = np.random.default_rng(2)
    for i in range(14):                                                   # papers flying
        px = (rng.uniform(0, W) + fly * rng.uniform(80, 220)) % (W + 200) - 100
        py = 500 + (rng.uniform(0, 900) + fly * 140) % 900
        ctx.save()
        ctx.translate(px, py)
        ctx.rotate(fly * rng.uniform(-3, 3))
        rrect(ctx, -40, -28, 80, 56, 3, fill=(1, 1, 1), w=3)
        ctx.restore()
    run = lerp(-100, 380, (fly * .45) % 1) if not frozen else 300
    sipping = .3 < t < f0 - .15                                          # a calm sip while everything burns
    draw_people(ctx, t, m, talk, [
        (person("coworker", run, facing=.6), COWORKER, dict(arms=((150, 20), (150, 20)), legs=walk_legs(fly, 1.8) if not frozen else ((20, 20), (-20, 0)),
                                                             face="shock" if not frozen else "annoyed", look=(1, 0))),
        (person("boss", BX - 140, facing=-.4), BOSS, dict(arms=((110, 40), (110, 40)) if not frozen else REST, face="shock" if not frozen else "annoyed",
                                                          look=(-1, 0))),
        (person("worker", WX, facing=0), WORKER, dict(arms=((10, -60), (22, -118) if sipping else (30, -95)),
                                                      face="closed" if sipping else ("smug" if t > f1 else "neutral"), look=(0, 0),
                                                      hold=lambda c, h: mug(c, h, 1, sipping=sipping), hold_on_top=sipping)),
    ])
    desks(ctx, t, laptop=False, mug=False)
    if not frozen and int(t * 3) % 2 == 0:                              # alarm light
        ctx.set_source_rgba(1, 0.1, 0.1, 0.18)
        ctx.paint()


def sc_thanks(ctx, t, m, talk):
    office(ctx, t, "5:00", "FRI", sunset=1.0)
    k0, k1 = m["thanks"]
    dark = t > k1 + .5
    draw_people(ctx, t, m, talk, [
        (person("coworker", CX, facing=.4), COWORKER, dict(arms=REST, face="annoyed", look=(1, 0))),
        (person("boss", BX, facing=-.4), BOSS, dict(arms=REST, face="annoyed", look=(-1, 0))),
        (person("worker", WX, facing=0), WORKER, dict(arms=((120, 40), (120, 40)) if t > k0 - .2 else REST, face="happy",
                                                      legs=((4, 0), (4, 0)))),
    ])
    if dark:                                                            # lights off
        ctx.set_source_rgba(0, 0, 0.05, min(.85, (t - k1 - .5) * 3))
        ctx.paint()


def cooler(ctx, t, x=930, glug=0.0):
    rrect(ctx, x - 70, 1215, 140, 345, 12, fill="#dfe4ee", w=7)                       # base
    ctx.save()
    ctx.rectangle(x - 60, 960, 120, 255)
    ctx.clip()
    ellipse(ctx, x, 1090, 62, 125, fill="#bfe6ff", w=7)                               # the big bottle
    for k in range(int(glug * 4)):                                                    # bubbles going up
        ellipse(ctx, x - 10 + 14 * math.sin(k * 2 + t * 6), 1190 - ((t * 200 + k * 60) % 180), 10, 10, fill=(1, 1, 1), w=3)
    ctx.restore()
    rrect(ctx, x - 55, 1262, 30, 22, 5, fill="#4a7bd0", w=4)                          # taps
    rrect(ctx, x + 25, 1262, 30, 22, 5, fill="#e0457b", w=4)


def tumbler(ctx, hands, i=1, level=1.0, grip_top=False):
    """Pink tumbler with lid + straw; grip_top: held by the rim (cup hangs below the hand, e.g. under a tap)."""
    x, y = hands[i]
    if grip_top:
        y += 105
    poly(ctx, [(x - 28, y - 100), (x + 28, y - 100), (x + 22, y + 10), (x - 22, y + 10)], fill="#f7b6cb", w=5)
    if level > 0:
        poly(ctx, [(x - 25, y - 100 + 100 * (1 - level)), (x + 25, y - 100 + 100 * (1 - level)), (x + 21, y + 6), (x - 21, y + 6)],
             fill="#bfe6ff", line=None)
    if not grip_top:                                                                  # lid + straw once it's full
        rrect(ctx, x - 32, y - 116, 64, 20, 6, fill="#e0457b", w=5)
        poly(ctx, [(x + 10, y - 116), (x + 22, y - 160)], line="#2a2b2c", w=7, close=False)


def sc_water(ctx, t, m, talk):
    office(ctx, t)
    w0, w1 = m["water"]
    filling = t < 1.7
    fill = min(1.0, t / 1.6)
    cooler(ctx, t, x=950, glug=1.0 if filling else 0.0)                               # behind her
    if filling:                                                                       # water running into her cup
        poly(ctx, [(975, 1284), (975, 1300)], line="#7ec8ff", w=8, close=False)
    draw_people(ctx, t, m, talk, [
        (person("coworker", 330, facing=.5), COWORKER, dict(arms=((12, 8), (40, -110)), face="neutral" if t < w1 else "annoyed",
                                                             look=(1, 0), hold=lambda c, h: tumbler(c, h, 1, 0.0))),
        (person("worker", 800, facing=.5 if filling else -.3), WORKER,
         dict(arms=((12, 8), (65, 0) if filling else (30, -110)), face="calm" if filling else "smug",
              look=(1, .6) if filling else (0, 0), hold=lambda c, h: tumbler(c, h, 1, fill, grip_top=filling))),
    ])


def sc_first(ctx, t, m, talk):
    office(ctx, t)
    f0, f1 = m["first"]
    spill = ease((t - .5) / .5)
    draw_people(ctx, t, m, talk, [
        (person("boss", BX - 60, facing=-.5), BOSS, dict(arms=((40, -100), (40, -100)), face="shock" if t < f0 else "annoyed",
                                                        look=(-1, 0) if t < f1 + .6 or t > f1 + 1.6 else (-1, 1.2),
                                                        hold=lambda c, h: report(c, h, spill))),
        (person("worker", WX, facing=.3), WORKER, dict(arms=((10, -60), (lerp(30, 80, spill), lerp(-100, -60, spill))),
                                                       face="sad" if t > .9 else "neutral", look=(1, 0),
                                                       hold=lambda c, h: mug(c, h, 1, sipping=False))),
    ])
    desks(ctx, t, mug=False)
    plaque(ctx)


def report(ctx, hands, spill):
    x, y = (hands[0][0] + hands[1][0]) / 2, (hands[0][1] + hands[1][1]) / 2
    rrect(ctx, x - 80, y - 100, 160, 120, 4, fill=(1, 1, 1), w=4)
    text(ctx, "Q3 REPORT", x, y - 70, 24, FONT, col="#2a2b2c")
    if spill > 0:
        ellipse(ctx, x - 10, y - 20, 60 * spill, 40 * spill, fill="#8a5a3a", line=None)
        ellipse(ctx, x + 30, y + 5, 25 * spill, 18 * spill, fill="#8a5a3a", line=None)


def plaque(ctx):
    rrect(ctx, 380, 1225, 110, 85, 8, fill="#e7ac27", w=6)
    rrect(ctx, 392, 1237, 86, 61, 4, fill="#fff2c9", w=3)
    text(ctx, "5", 435, 1258, 30, FONT, col="#2a2b2c")
    text(ctx, "YEARS", 435, 1285, 18, FONT, col="#2a2b2c")


# scenes: (draw, beats, camera cuts, sfx). beats: ("act", s) | ("line", key, pause after). cameras: (time or
# "key" / "key+" (after the line), (zoom, fx, fy, rot)) - each holds until the next; zoom drifts in slowly.
WIDE = (1.15, 540, 1060, 0)
SCENES = [
    (sc_friday, [("act", .8), ("line", "friday", 1.3)],
     [(0, (2.4, 905, 480, 0)), (.8, WIDE), ("friday+", (1.9, CX, 980, 0))], [("tick", 0)]),
    (sc_fanmail, [("act", 1.4), ("line", "fanmail", .9)],
     [(0, (1.0, 540, 740, 0)), ("fanmail", (1.8, WX, 980, 3))], [("keys", 0)]),
    (sc_water, [("act", 1.9), ("line", "water", 1.2)],
     [(0, (1.8, 900, 1220, 0)), (1.0, (1.2, 640, 1060, 0)), ("water", (1.9, 800, 990, 0)), ("water+", (1.9, 330, 990, 0))],
     [("glug", 0)]),
    (sc_sign, [("act", 1.3), ("line", "sign_q", .6), ("line", "sign_a", 1.2)],
     [(0, WIDE), ("sign_q", (1.5, 380, 1000, 0)), ("sign_a", (1.9, WX, 980, 0)), ("sign_a+", (2.0, WX - 250, 960, -3))],
     [("steps", 0), ("scribble", "sign_a-")]),
    (sc_trip, [("act", 1.7), ("line", "trip", 1.4)],
     [(0, (1.1, 420, 1250, 0)), (.75, (1.9, 560, 1420, -6)), (1.7, (1.7, 700, 1000, 0)), ("trip+", WIDE)],
     [("steps", 0), ("thud", 1.0)]),
    (sc_sneeze, [("act", .3), ("line", "sneeze", .4), ("line", "sneeze_a", 1.0)],
     [(0, (1.8, CX, 990, 0)), ("sneeze_a", (1.9, WX, 990, 0)), ("sneeze_a+", (1.9, CX, 990, 0))], []),
    (sc_wifi, [("act", .3), ("line", "wifi", 2.0), ("line", "secrets", .9)],
     [(0, (1.6, WX, 990, 0)), ("wifi+", WIDE), ("secrets", (1.3, WX, 1000, 0))], [("crickets", "wifi+")]),
    (sc_bucks, [("act", 2.6), ("line", "bucks", 1.1)],
     [(0, (1.9, 880, 1230, 0)), (2.1, (1.2, 560, 1150, 0)), ("bucks", (1.9, 600, 980, -3)), ("bucks+", (1.6, 150, 990, 0))],
     [("bang", 1.0), ("bang", 1.6), ("whirr", 2.0)]),
    (sc_deadline, [("act", .3), ("line", "deadline", 1.2), ("line", "allow", 1.0)],
     [(0, (1.4, 760, 1000, 0)), ("deadline+", (1.2, WX, 1000, 0)), ("allow", (2.1, WX, 970, 0)), ("allow+", (2.0, BX - 20, 960, 4))],
     [("sting", "deadline+")]),
    (sc_fun, [("act", 1.4), ("line", "fun", 1.6)],
     [(0, (1.1, 540, 1060, -8)), ("fun", (1.9, WX, 990, 0)), ("fun+", (1.05, 540, 1060, 0))], [("alarm", 0), ("scratch", "fun+")]),
    (sc_first, [("act", 1.0), ("line", "first", 2.2)],
     [(0, (1.3, 740, 1060, 0)), ("first", (1.9, WX, 990, 0)), ("first+", (2.8, 435, 1260, 0)), ("first+1.1", (1.9, BX - 60, 960, 0))],
     [("splash", .6)]),
    (sc_thanks, [("act", .5), ("line", "thanks", 2.0)],
     [(0, WIDE), ("thanks", (1.6, WX, 1000, 0)), ("thanks+", WIDE)], [("switch", "thanks+")]),
]


# ------------------------------------------------------------------ build
def build():
    by = {k: (who, line) for k, who, line in LINES}
    tracks = {v: np.zeros(int(150 * SR), np.float32) for v in (WORKER, COWORKER, BOSS)}
    t, plan = 0.2, []
    for draw, beats, cams, sfx in SCENES:
        m, s = {}, 0.0
        for b in beats:
            if b[0] == "act":
                s += b[1]
                continue
            key, pause = b[1], b[2]
            who, line = by[key]
            a = voices.say(who, line)
            tracks[who][int((t + s) * SR):int((t + s) * SR) + len(a)] += a
            m[key] = (s, s + len(a) / SR)
            s += len(a) / SR + pause
        m["end"] = s
        plan.append(dict(draw=draw, t0=t, m=m, cams=cams, sfx=sfx))
        t += s
    total = t + 2.8
    n = int(total * SR)
    env = {}
    for v, tr in tracks.items():
        hop = SR // FPS
        rms = np.sqrt(np.convolve(tr[:n] ** 2, np.ones(hop) / hop, "same"))[::hop]
        env[v] = np.clip(rms / (np.percentile(rms[rms > 1e-4], 90) + 1e-6), 0, 1.2) if (rms > 1e-4).any() else rms
    voice = voices.clarity(sum(tr[:n] for tr in tracks.values()))
    fx = synth("cafe", total) * .22                                        # office room tone

    def add(x, at):
        i = max(0, int(at * SR))
        fx[i:i + len(x)] += x[:max(0, n - i)].astype(np.float32)
    tt = lambda d: np.arange(int(d * SR)) / SR
    rng = np.random.default_rng(3)
    for p in plan:
        for name, at in p["sfx"]:
            if isinstance(at, str):
                key = at.rstrip("+-")
                at = p["m"][key][1] + .1 if at.endswith("+") else (p["m"][key][0] - .6 if at.endswith("-") else p["m"][key][0])
            T0 = p["t0"] + at
            if name == "steps":
                for k, s in enumerate(np.arange(0, 1.4, .3)):
                    add(ogg(f"footstep0{k % 4}", .6), T0 + s)
            elif name == "thud":
                add(ogg("impactSoft_heavy_001", .9), T0)
            elif name == "bang":
                add(ogg("impactPlate_light_001", 1.0), T0)
            elif name == "tick":
                for s in np.arange(0, .8, .4):
                    add(ogg("tick_001", .6), T0 + s)
            elif name == "keys":
                x = np.zeros(int(1.3 * SR), np.float32)
                for s in np.arange(0, 1.2, .08):
                    i = int((s + rng.uniform(0, .03)) * SR)
                    x[i:i + 300] += rng.normal(0, 1, 300) * np.exp(-np.arange(300) / 60) * .12
                add(x, T0)
            elif name == "scribble":
                add(synth("brush", .7) * 1.2, T0)
            elif name == "whirr":
                d = tt(.8)
                add((np.sin(2 * np.pi * 180 * d) * (0.5 + 0.5 * np.sin(2 * np.pi * 14 * d)) * .08), T0)
            elif name == "crickets":
                d = tt(1.8)
                add(np.sin(2 * np.pi * 4200 * d) * (((d * 14) % 1) < .35) * (((d / .9) % 1) < .5) * .05, T0)
            elif name == "alarm":
                d = tt(p["m"]["fun"][1] + .1)
                add((np.sign(np.sin(2 * np.pi * (700 + 300 * (np.sin(2 * np.pi * 2 * d) > 0)) * d)) * .035), T0)
            elif name == "scratch":
                d = tt(.35)
                add(np.sin(2 * np.pi * (900 - 2400 * d) * d) * .14, T0)
            elif name == "sting":
                add(synth("sting", .8), T0)
            elif name == "glug":
                d = tt(1.6)
                add(np.sin(2 * np.pi * (200 + 120 * np.sin(2 * np.pi * 5 * d)) * d) * (np.sin(2 * np.pi * 5 * d) > 0) * .06, T0)
            elif name == "splash":
                add(synth("brush", .4) * 1.6, T0)
            elif name == "switch":
                add(ogg("tick_001", 1.2), T0 + .4)
    mix = voice + fx
    return plan, env, (mix / max(np.abs(mix).max(), 1e-6) * .95).astype(np.float32), total


def cam_at(p, t):
    cuts = []
    for when, cam in p["cams"]:
        if isinstance(when, str):                                          # "key" start, "key+" end, "key+1.1" end + 1.1 s
            key, plus, off = when.partition("+")
            when = p["m"][key][1] + .05 + float(off or 0) if plus else p["m"][key][0] - .15
        cuts.append((when, cam))
    cuts.sort(key=lambda c: c[0])
    i = max(j for j, (w, _) in enumerate(cuts) if w <= t) if any(w <= t for w, _ in cuts) else 0
    w0, cam = cuts[i]
    w1 = cuts[i + 1][0] if i + 1 < len(cuts) else p["m"]["end"]
    k = (t - w0) / max(w1 - w0, .3)
    z, x, y, r = cam
    return z * (1 + .05 * k), x, y, r                                    # slow push-in within each shot


def render(out):
    plan, env, audio, total = build()
    surf = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
    with tempfile.TemporaryDirectory() as d:
        wav = os.path.join(d, "a.wav")
        sf.write(wav, audio, SR)
        enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}",
                                "-framerate", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-pix_fmt", "yuv420p",
                                "-crf", "19", "-c:a", "aac", "-b:a", "192k", "-shortest", out], stdin=subprocess.PIPE)
        for fi in range(int(total * FPS)):
            T = fi / FPS
            p = max((x for x in plan if x["t0"] <= T), key=lambda x: x["t0"], default=plan[0])
            t = T - p["t0"]
            if p is plan[-1] and t > p["m"]["end"]:
                t = p["m"]["end"] + (t - p["m"]["end"])
            z, fx_, fy, rot = cam_at(p, t)
            ctx = cairo.Context(surf)
            ctx.translate(W / 2, 1000)
            ctx.rotate(math.radians(rot))
            ctx.scale(z, z)
            ctx.translate(-fx_, -fy)

            def talk(voice, fi=fi):
                e = env[voice]
                return float(e[min(fi, len(e) - 1)]) * .9
            p["draw"](ctx, t, p["m"], talk)
            ctx.identity_matrix()
            rrect(ctx, 110, 80, W - 220, 120, 34, fill=(1, 1, 1), w=6)                    # title
            text(ctx, "things to say at work", W / 2, 140, 48, FONT, col="#e0457b")
            line_keys = [k for k in p["m"] if k != "end"]
            for key in line_keys:
                s0, s1 = p["m"][key]
                if s0 <= t <= s1 + .25:                                                    # spoken captions
                    words = TXT[key].split()
                    n = max(1, min(len(words), int(len(words) * (t - s0) / max(s1 - s0, .3)) + 1))
                    c0 = (n - 1) // 3 * 3
                    chunk = " ".join(words[c0:n]).upper()
                    size = 66 if len(chunk) < 20 else int(66 * 20 / len(chunk))
                    text(ctx, chunk, W / 2, 1760, size, FONT, col=(1, 1, 1), outline=(.1, .08, .1), ow=12)
            if p is plan[-1] and t > p["m"]["end"] - .2:
                kk = ease((t - p["m"]["end"] + .2) / .4)
                rrect(ctx, 110, 760, W - 220, 300, 40, fill="#e0457b", w=6)
                text(ctx, "which one are you", W / 2, 860, 56 * kk + 1, FONT, col=(1, 1, 1))
                text(ctx, "using on Monday?", W / 2, 940, 56 * kk + 1, FONT, col=(1, 1, 1))
            surf.flush()
            enc.stdin.write(bytes(surf.get_data()))
        enc.stdin.close()
        if enc.wait():
            raise RuntimeError("ffmpeg failed")
    print("wrote", out, f"({total:.1f} s)")


if __name__ == "__main__":
    render(sys.argv[1] if len(sys.argv) > 1 else "work_comments.mp4")
