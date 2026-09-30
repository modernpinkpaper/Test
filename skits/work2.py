"""'Things to say at work' v2 - 8 jokes from the comments on @careeralbert's post, each told in 4 beats:
setup (make the situation obvious) -> the line (snap zoom) -> the reaction (record scratch, head turns, looks
between coworkers, emotion symbols, a reaction line - never laughing) -> a button that closes the joke.
1080x1920, ~65 s.   python skits/work2.py out.mp4          (script: work2_lines.py, kit: beats.py)
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
import beats as B                                                       # noqa: E402
import voices                                                           # noqa: E402
from five_min import ogg, synth                                         # noqa: E402
from stick_people import LOOKS, StickPerson                             # noqa: E402
from toon import curve, ellipse, lin, poly, rgb, rrect, text            # noqa: E402
from work2_lines import BOSS, COWORKER, COWORKER2, LINES, WORKER        # noqa: E402
from work_comments import cable, inbox, mug, office, printer            # noqa: E402

W, H, FPS, SR = 1080, 1920, 24, voices.SR
FONT = os.path.join(HERE, "assets", "poppins-800.ttf")
FONT2 = os.path.join(HERE, "assets", "poppins-600.ttf")
FLOOR = 1560
CX, WX, C2X = 190, 560, 910                   # coworker (left desk), worker (middle), coworker 2 (right desk)
REST_D = ((10, -60), (10, -60))
REST = ((10, 8), (10, 8))
SHRUG = ((25, -95), (25, -95))
TXT = {k: l.split("] ", 1)[1] for k, _, l in LINES}
ease, pop, at = B.ease, B.pop, B.at
WIDE = (1.15, 540, 1060, 0)


def lerp(a, b, k):
    return a + (b - a) * k


def turn(t, t0, dur, a, b):
    return lerp(a, b, ease((t - t0) / dur))


def walk_legs(t, speed=1.0):
    s = math.sin(t * 9 * speed)
    return ((18 * s, max(0, -30 * s)), (-18 * s, max(0, 30 * s)))


def P(key, x, facing=0.0):
    return StickPerson(LOOKS[key], x=x, floor=FLOOR, facing=facing)


def desks(ctx, right=True, laptop=True, mugs=True):
    for x0, x1 in ((360, 780), (-60, 330)) + (((800, 1140),) if right else ()):
        rrect(ctx, x0, 1310, x1 - x0, 50, 12, fill="#c89a74", w=8)
        rrect(ctx, x0 + 20, 1356, x1 - x0 - 40, 600, 0, fill="#a8764f", w=8)
    if laptop:
        rrect(ctx, 450, 1150, 230, 160, 14, fill="#dfe4ee", w=7)
        ellipse(ctx, 565, 1230, 18, 16, fill="#ff8fb0", line=None)
    rrect(ctx, 40, 1180, 170, 130, 10, fill="#2a2b2c", w=6)                       # his monitor (from behind)
    rrect(ctx, 52, 1192, 146, 100, 6, fill="#3b4250", line=None)
    if right:
        rrect(ctx, 830, 1170, 170, 140, 10, fill="#2a2b2c", w=6)                  # her monitor
        rrect(ctx, 842, 1182, 146, 110, 6, fill="#3b4250", line=None)
    if mugs:
        rrect(ctx, 250, 1250, 50, 60, 10, fill="#ffffff", w=6)                    # his sad coffee
        text(ctx, "MON", 275, 1282, 16, FONT, col="#2a2b2c")


class Cast:
    """Draws people and remembers their heads, so emotion symbols go above the right person."""

    def __init__(self, ctx, t, talk):
        self.ctx, self.t, self.talk, self.heads = ctx, t, talk, {}

    def draw(self, name, person, voice, **kw):
        kw.setdefault("blink", (self.t + len(name) * .37) % 3.3 < .1)
        kw["mouth"] = max(kw.get("mouth", 0), self.talk(voice))
        xf = kw.pop("xform", None)
        if xf:
            self.ctx.save()
            xf(self.ctx)
        person.draw(self.ctx, **kw)
        if xf:
            self.ctx.restore()
        self.heads[name] = (person.head_c, person.head_r, xf)

    def emote(self, name, kind, k):
        if name in self.heads and k > .02:
            hc, R, xf = self.heads[name]
            if xf:
                self.ctx.save()
                xf(self.ctx)
            B.emote(self.ctx, kind, hc, R, k, self.t, FONT)
            if xf:
                self.ctx.restore()


# ------------------------------------------------------------------ 1. "Nearly Friday" on a Monday
def s_friday(ctx, t, m, talk):
    tick = t > at(m, "button+0.45")
    office(ctx, t, "8:46" if tick else "8:45", "MON")
    c = Cast(ctx, t, talk)
    rx = at(m, "scratch")
    # coworker: staring into his coffee -> lifts his head, looks at her, looks at coworker 2, back to her
    cf = .6 if t < at(m, "huh") else (turn(t, at(m, "huh>"), .25, .6, .7))
    clook = (0, 1.2) if t < rx else ((1, 0) if t < at(m, "huh>") or t > at(m, "monday") else (1, -.1))
    c.draw("c", P("coworker", CX, cf), COWORKER, arms=REST_D, face="sad" if t < rx else "neutral", look=clook,
           bob=turn(t, rx, .4, 30, 0))
    # coworker 2: asleep -> wakes at the record scratch -> "It's Monday." -> head back down (button)
    down = t < rx + .2 or t > at(m, "button+0.8")
    c.draw("c2", P("coworker2", C2X, -.6), COWORKER2, arms=REST_D, face="closed" if down else "annoyed",
           look=(-1, 0), bob=110 if down else turn(t, rx + .2, .3, 110, 0))
    # her: empty desk -> bursts in -> arms up
    if t > at(m, "burst"):
        k = ease((t - at(m, "burst")) / .5)
        wave = 14 * math.sin(t * 12)
        c.draw("w", P("worker", lerp(1150, WX, k), -.1), WORKER, arms=((150, 20 + wave), (150, 20 - wave)), face="happy",
               legs=walk_legs(t) if k < 1 else ((4, 0), (4, 0)))
    desks(ctx)
    c.emote("c", "gloom", 1 if t < rx else 0)
    c.emote("c2", "zzz", 1 if down else 0)
    c.emote("w", "sparkle", pop(t - at(m, "friday")) if t < at(m, "scratch") else 0)
    c.emote("c", "?", pop(t - rx - .1) if t < at(m, "button") else 0)
    c.emote("c2", "anger", pop(t - at(m, "monday")) if at(m, "monday") < t < at(m, "button+0.8") else 0)


SC_FRIDAY = dict(
    draw=s_friday,
    beats=[("act", 1.7, "setup"), ("act", .6, "burst"), ("line", "friday", .2), ("act", .45, "scratch"),
           ("line", "huh", .35), ("line", "monday", .4), ("act", 1.4, "button")],
    cams=[(0, (2.4, 905, 480, 0), "cut"), (.9, WIDE, "cut"), ("burst", (1.3, 700, 1040, 0), "cut"),
          ("friday", (1.9, WX, 990, 0), "snap"), ("scratch", (1.5, 550, 1000, 0), "whip"), ("huh", (1.9, CX, 990, 0), "cut"),
          ("monday", (1.9, C2X, 990, 0), "whip"), ("button", (3.0, 130, 470, 0), "cut"), ("button+0.7", WIDE, "cut")],
    sfx=[(0, "tick"), (.5, "tick"), (1.0, "tick"), (1.5, "tick"), ("burst", "door"), ("burst+0.2", "brightsting"),
         ("scratch", "scratch"), ("button+0.45", "tick"), ("button+0.85", "thud")],
)


# ------------------------------------------------------------------ 2. fan mail
def s_fanmail(ctx, t, m, talk):
    if t < at(m, "setup>") or at(m, "button") <= t < at(m, "button+0.7"):
        ctx.set_source_rgb(*rgb("#dfe4ee"))
        ctx.paint()
        inbox(ctx, t if t < 3 else 1.2)
        n = 340 + min(7, int(t / .22)) + (1 if t >= at(m, "button") else 0)
        rrect(ctx, 700, 465, 230, 50, 25, fill="#e0457b", line=None)
        text(ctx, f"{n} unread", 815, 490, 32, FONT, col=(1, 1, 1))
        return
    office(ctx, t)
    c = Cast(ctx, t, talk)
    shake = 25 * math.sin(t * 7) * (at(m, "react+0.6") < t < at(m, "button"))
    c.draw("c", P("coworker", CX, .6 + shake / 100), COWORKER, arms=REST_D, look=(1, -.2) if t > at(m, "react") else (0, 1),
           face="neutral", bob=-20 if t > at(m, "react") else 0)
    after = t > at(m, "button+0.7")
    c.draw("w", P("worker", WX, -.1), WORKER, arms=((10, -60), (125 + 10 * math.sin(t * 3), 60)),
           face="wink" if after else "smug", tilt=4, hair_sway=.5 * math.sin(t * 3))
    desks(ctx)
    c.emote("w", "sparkle", pop(t - at(m, "fanmail")) if t < at(m, "react") or after else 0)
    c.emote("c", "?", pop(t - at(m, "react")) if at(m, "react") < t < at(m, "react+0.6") else 0)
    c.emote("c", "...", 1 if at(m, "react+0.6") < t < at(m, "button") else 0)


SC_FANMAIL = dict(
    draw=s_fanmail,
    beats=[("act", 1.8, "setup"), ("line", "fanmail", .3), ("act", 1.4, "react"), ("act", 1.4, "button")],
    cams=[(0, (1.0, 540, 740, 0), "cut"), ("fanmail", (1.9, WX, 990, 3), "snap"), ("react", (1.9, CX, 990, 0), "whip"),
          ("button+0.7", (1.9, WX, 990, 0), "cut")],
    sfx=[(0, "notif"), (.3, "notif"), (.55, "notif"), (.8, "notif"), (1.05, "notif"), (1.3, "notif"),
         ("button", "notif"), ("react", "pop")],
)


# ------------------------------------------------------------------ 3. trips over his cable
def s_trip(ctx, t, m, talk):
    office(ctx, t)
    rrect(ctx, 990, 1470, 40, 60, 6, fill="#ffffff", w=5)                          # wall outlet
    unplug = ease((t - at(m, "react+0.7")) / .5)
    if unplug < 1:                                                                  # his charger cable across the aisle
        ctx.save()
        ctx.translate(lerp(0, -700, unplug), 0)
        cable(ctx)
        curve(ctx, [(760, FLOOR - 4), (880, FLOOR - 30), (1000, 1500)], line="#2a2b2c", w=12)
        ctx.restore()
    rrect(ctx, -60, 1310, 390, 50, 12, fill="#c89a74", w=8)                          # his desk
    rrect(ctx, -40, 1356, 350, 600, 0, fill="#a8764f", w=8)
    c = Cast(ctx, t, talk)
    c.draw("c", P("coworker", CX, .6), COWORKER, arms=REST_D if t < at(m, "react+0.6") else ((40, -100), (10, -60)),
           face="neutral" if t < at(m, "react") else "sad", look=(1, .8) if at(m, "react") < t < at(m, "react+0.5") else (1, 0))
    w0, trip = at(m, "walk"), at(m, "walk+0.75")                                # she trips, then says the line
    x = lerp(1150, 600, ease((t - w0) / (trip - w0 + .2))) if t < trip + .2 else 600
    stumble = max(0, 1 - abs(t - trip - .15) / .3)
    xf = (lambda cc, x=x, s=stumble: (cc.translate(x, FLOOR), cc.rotate(math.radians(24 * s)), cc.translate(-x, -FLOOR)))
    gone = ease((t - at(m, "button+0.2")) / .6)
    if t > w0:
        c.draw("w", P("worker", lerp(x, -200, gone), -.5 if t < trip or t > at(m, "button") else -.6), WORKER,
               arms=((70 * stumble + 20, 30), (60 * stumble + 25, -110)) if t < at(m, "trip>") else ((20, -100), (25, -110)),
               legs=walk_legs(t) if t < trip + .2 or gone > 0 else ((4, 0), (4, 0)),
               face="shock" if stumble > .3 else ("annoyed" if t < at(m, "button") else "smug"), look=(-1, 0),
               hold=lambda cc, h: mug(cc, h, 1), xform=xf)
    c.emote("w", "anger", pop(t - at(m, "trip")) if at(m, "trip") < t < at(m, "react") else 0)
    c.emote("c", "sweat", 1 if t > at(m, "react+0.3") else 0)


SC_TRIP = dict(
    draw=s_trip,
    beats=[("act", 1.0, "setup"), ("act", 1.1, "walk"), ("line", "trip", .25), ("act", 1.5, "react"), ("act", 1.1, "button")],
    cams=[(0, (2.3, 640, 1480, 0), "cut"), ("walk", (1.2, 700, 1200, -4), "cut"), ("walk+0.65", (1.6, 600, 1350, 6), "snap"),
          ("trip", (1.9, 600, 990, 0), "cut"), ("react", (1.9, CX, 990, 0), "whip"), ("react+0.7", (1.8, 500, 1450, 0), "cut"),
          ("button", WIDE, "cut")],
    sfx=[("walk", "steps"), ("walk+0.75", "whoosh"), ("walk+0.85", "thud"), ("react+0.3", "gulp"), ("react+0.8", "whoosh"),
         ("button+0.3", "slide_down")],
)


# ------------------------------------------------------------------ 4. sneezes
def s_sneeze(ctx, t, m, talk):
    office(ctx, t)
    c = Cast(ctx, t, talk)
    s0 = at(m, "sneeze")
    jerk = sum(35 * math.exp(-((t - a) / .07) ** 2) for a in (s0 + .3, s0 + .85))
    jerk += 12 * math.exp(-((t - at(m, "tiny+0.1")) / .07) ** 2)
    frozen = at(m, "sneeze_a>") < t < at(m, "tiny")
    c.draw("c", P("coworker", CX, .5), COWORKER, arms=((40, -120), (40, -120)) if s0 - .3 < t < at(m, "sneeze>") + .2 or
           at(m, "tiny") - .2 < t < at(m, "tiny>") else REST_D,
           face="closed" if s0 < t < at(m, "sneeze>") else ("sad" if t > at(m, "sneeze_a>") else "neutral"),
           bob=jerk - (15 if s0 - .3 < t < s0 + .2 else 0), tilt=jerk * .5, look=(1, 0) if frozen else (0, 0))
    side = at(m, "button") < t
    c.draw("w", P("worker", WX, .3 if side else 0), WORKER, arms=REST_D, face="annoyed" if side else "neutral",
           look=(-1.2, 0) if side else (0, 1.3))                                       # never looks up... until the button
    desks(ctx)
    c.emote("c", "...", 1 if frozen else 0)
    c.emote("c", "gloom", 1 if t > at(m, "sneeze_a>") + .3 else 0)
    c.emote("c", "sweat", 1 if side else 0)


SC_SNEEZE = dict(
    draw=s_sneeze,
    beats=[("act", .5, "setup"), ("line", "sneeze", .25), ("act", .35, "beat"), ("line", "sneeze_a", .3),
           ("act", 1.2, "react"), ("line", "tiny", .3), ("act", 1.0, "button")],
    cams=[(0, (1.8, CX, 990, 0), "cut"), ("beat", (2.0, WX, 1010, 0), "cut"), ("sneeze_a>", (1.9, CX, 990, 0), "whip"),
          ("button", (1.25, 380, 1030, 0), "cut")],
    sfx=[(0, "keys"), ("sneeze_a>+0.4", "sniff"), ("button", "pop")],
)


# ------------------------------------------------------------------ 5. Wi-Fi password
def s_wifi(ctx, t, m, talk):
    office(ctx, t)
    c = Cast(ctx, t, talk)
    q1 = at(m, "wifi>")
    silent = q1 < t < at(m, "button")
    away = ease((t - q1 - .3) / .6) if silent else 0
    c.draw("c", P("coworker", CX, lerp(.6, -.7, away)), COWORKER, arms=REST_D, look=(lerp(1, -1.3, away), 0), face="neutral")
    c.draw("c2", P("coworker2", C2X, lerp(-.6, .5, away)), COWORKER2, arms=REST_D, look=(lerp(-1, 1, away), -.3),
           face="neutral", bob=lerp(0, 120, ease((t - q1 - 1.0) / .6)) if silent else 0)       # hides behind her monitor
    stand = -70 if at(m, "wifi") - .3 < t < at(m, "button+0.3") else 0
    c.draw("w", P("worker", WX, 0), WORKER, arms=SHRUG if t < q1 + .2 else REST_D, bob=stand,
           face="neutral" if t < at(m, "secrets") - .3 else "annoyed")
    desks(ctx)
    c.emote("c", "sweat", 1 if silent and t > q1 + .8 else 0)
    c.emote("w", "...", 1 if q1 + .5 < t < at(m, "secrets") else 0)
    c.emote("w", "anger", pop(t - at(m, "secrets")) if at(m, "secrets") < t < at(m, "button") else 0)


SC_WIFI = dict(
    draw=s_wifi,
    beats=[("act", .5, "setup"), ("line", "wifi", .2), ("act", 2.3, "silence"), ("line", "secrets", .35), ("act", 1.0, "button")],
    cams=[(0, WIDE, "cut"), ("wifi", (1.8, WX, 960, 0), "snap"), ("silence", (1.9, CX, 990, 0), "whip"),
          ("silence+0.9", (1.9, C2X, 990, 0), "whip"), ("silence+1.7", (1.25, 540, 1040, 0), "cut"),
          ("secrets", (2.1, WX, 950, 0), "snap"), ("button", WIDE, "cut")],
    sfx=[(0, "keys"), ("silence", "crickets"), ("button+0.3", "squeak"), ("button+0.3", "keys")],
)


# ------------------------------------------------------------------ 6. medium bucks
def s_bucks(ctx, t, m, talk):
    office(ctx, t)
    fx0 = at(m, "fix")
    hit = fx0 + 1.0
    shake = 12 * math.sin(t * 90) * max(0, 1 - abs(t - hit) / .2)
    paper = ease((t - hit - .5) / .6) if hit + .5 < t < hit + 1.1 else 0
    jam = t < hit + .4 or t > at(m, "button")
    printer(ctx, t, x=800, jam=jam, shake=shake, paper=paper)
    c = Cast(ctx, t, talk)
    pushed = ease((t - fx0 - .6) / .3)
    jab = 20 * math.sin(t * 20) if t < fx0 + .6 else 0
    c.draw("c", P("coworker", lerp(640, 420, pushed), .6 if t < at(m, "react") else -.4), COWORKER,
           arms=((12, 8), (60 + jab, 20)) if t < fx0 + .6 else REST, face="annoyed" if t < at(m, "react") else "shock",
           look=(1, .6) if t < at(m, "react") else (1, 0), bob=6 * math.sin(t * 6) if at(m, "react+0.5") < t < at(m, "button") else 0)
    wx = lerp(-200, 610, ease((t - fx0) / .7)) if t < at(m, "button") else lerp(610, -250, ease((t - at(m, "button+0.3")) / .6))
    if t > fx0:
        arm = math.exp(-((t - hit) / .12) ** 2)
        c.draw("w", P("worker", wx, .5 if t < at(m, "bucks") else -.2), WORKER,
               arms=((12, 8), (lerp(40, 150, arm), lerp(60, 10, arm))), face="smug" if t > hit + 1 else "neutral",
               legs=walk_legs(t) if t < fx0 + .7 or t > at(m, "button+0.3") else ((4, 0), (4, 0)))
    c.emote("c", "anger", 1 if t < fx0 + .6 else 0)
    c.emote("w", "sparkle", pop(t - at(m, "bucks")) if at(m, "bucks") < t < at(m, "button") else 0)
    c.emote("c", "!", pop(t - at(m, "react")) if at(m, "react") < t < at(m, "react+0.6") else 0)
    c.emote("w", "sweat", 1 if t > at(m, "button") else 0)


SC_BUCKS = dict(
    draw=s_bucks,
    beats=[("act", .4, "setup"), ("line", "comeon", .2), ("act", 2.3, "fix"), ("line", "bucks", .3),
           ("act", 1.3, "react"), ("act", 1.1, "button")],
    cams=[(0, (1.5, 760, 1150, 0), "cut"), ("fix", (1.15, 560, 1150, 0), "cut"), ("fix+0.9", (2.0, 800, 1220, 0), "snap"),
          ("fix+1.6", (1.3, 650, 1150, 0), "cut"), ("bucks", (1.9, 610, 990, -4), "snap"), ("react", (1.9, 420, 990, 0), "whip"),
          ("button", (1.4, 700, 1100, 0), "cut")],
    sfx=[(0, "notif"), ("fix", "steps"), ("fix+1.0", "bang"), ("fix+1.5", "whirr"), ("fix+2.1", "ding"),
         ("button", "notif"), ("button+0.3", "whoosh")],
)


# ------------------------------------------------------------------ 7. I'll allow it
def s_allow(ctx, t, m, talk):
    office(ctx, t)
    c = Cast(ctx, t, talk)
    bx = lerp(1200, 800, ease(t / .6)) if t < at(m, "button+0.2") else lerp(800, 1300, ease((t - at(m, "button+0.2")) / .8))
    look_c = at(m, "react+0.4") < t < at(m, "button")
    dbl = at(m, "button+0.45") < t < at(m, "button+0.75")                           # double take on his way out
    c.draw("c", P("coworker", CX, .6), COWORKER, arms=SHRUG if at(m, "react+0.8") < t < at(m, "button") else REST_D,
           face="neutral", look=(1, 0))
    c.draw("b", P("boss", bx, -.6 if not look_c else -.9), BOSS, arms=((20, -100), (12, 8)),
           face="neutral" if t < at(m, "react") else ("shock" if dbl else "neutral"), look=(-1.3, -.2) if look_c else (-1, 0),
           legs=walk_legs(t) if t < .6 or t > at(m, "button+0.2") else ((4, 0), (4, 0)))
    squint = at(m, "stare") < t
    c.draw("w", P("worker", WX, .3), WORKER, arms=((60, 120), (10, -60)) if squint else REST_D,
           face="annoyed" if squint and t < at(m, "allow>") else ("smug" if squint else "neutral"), look=(1, 0))
    desks(ctx, right=False)
    c.emote("b", "?", pop(t - at(m, "react")) if at(m, "react") < t < at(m, "button+0.2") else 0)
    c.emote("b", "!", pop(t - at(m, "button+0.45")) if dbl else 0)


SC_ALLOW = dict(
    draw=s_allow,
    beats=[("act", .6, "setup"), ("line", "deadline", .2), ("act", 1.5, "stare"), ("line", "allow", .3),
           ("act", 1.3, "react"), ("act", 1.2, "button")],
    cams=[(0, (1.3, 720, 1050, 0), "cut"), ("stare", (2.0, WX, 990, 0), "snap"), ("stare+0.6", (2.7, WX, 960, 0), "cut"),
          ("react", (1.9, 800, 970, 0), "whip"), ("react+0.8", (1.9, CX, 990, 0), "cut"), ("button", (1.2, 700, 1060, 0), "cut")],
    sfx=[("stare", "dundun"), ("stare+0.6", "tick"), ("stare+1.0", "tick"), ("react", "pop"), ("button+0.45", "boing")],
)


# ------------------------------------------------------------------ 8. finale: "we're having fun"
def s_fun(ctx, t, m, talk):
    f0 = at(m, "freeze")
    frozen = f0 <= t < at(m, "stare")
    calm = t >= at(m, "stare")
    ft = min(t, f0) if not calm else f0                                               # chaos time stops at the freeze
    office(ctx, t)
    printer(ctx, ft, x=900, smoke=1.0 if not calm else .4)
    rng = np.random.default_rng(2)
    for i in range(14):
        px = (rng.uniform(0, W) + ft * rng.uniform(80, 220)) % (W + 200) - 100
        py = 480 + (rng.uniform(0, 900) + (ft if not calm else f0 + (t - f0) * .15) * 140) % 900
        ctx.save()
        ctx.translate(px, py)
        ctx.rotate(ft * rng.uniform(-3, 3))
        rrect(ctx, -40, -28, 80, 56, 3, fill=(1, 1, 1), w=3)
        ctx.restore()
    c = Cast(ctx, t, talk)
    stare = ease((t - at(m, "stare")) / .6)
    run = lerp(-100, 380, (ft * .45) % 1)
    c.draw("c", P("coworker", run, lerp(.6, .7, stare)), COWORKER, arms=((150, 20), (150, 20)) if not calm else REST,
           legs=walk_legs(ft, 1.8) if not calm else ((4, 0), (4, 0)), face="shock" if not calm else "neutral", look=(1, 0))
    c.draw("b", P("boss", 760, lerp(-.2, -.8, stare)), BOSS, arms=((110, 40), (110, 40)) if not calm else REST,
           face="shock" if not calm else "neutral", look=(-1, 0))
    sip = (.3 < t < at(m, "fun") - .1) or t > at(m, "button")
    c.draw("w", P("worker", WX, 0), WORKER, arms=((10, -60), (22, -118) if sip else (30, -95)),
           face="closed" if sip else "smug", hold=lambda cc, h: mug(cc, h, 1, sipping=sip), hold_on_top=sip)
    desks(ctx, right=False, laptop=False, mugs=False)
    for n in ("c", "b"):
        c.emote(n, "...", 1 if calm else 0)
    c.emote("w", "sparkle", 1 if at(m, "fun") < t < f0 else 0)
    if not calm and not frozen and int(t * 3) % 2 == 0:
        ctx.set_source_rgba(1, 0.1, 0.1, 0.18)
        ctx.paint()


SC_FUN = dict(
    draw=s_fun,
    beats=[("act", 1.8, "chaos"), ("line", "fun", .15), ("act", .7, "freeze"), ("act", 1.6, "stare"), ("act", 1.6, "button")],
    cams=[(0, (1.1, 540, 1060, -8), "cut"), ("fun", (1.9, WX, 990, 0), "snap"), ("freeze", (1.1, 560, 1060, -8), "cut"),
          ("stare", (1.25, 560, 1050, 0), "cut"), ("stare+0.8", (1.5, 700, 1000, 0), "cut"), ("button", (2.0, WX, 990, 0), "cut")],
    sfx=[(0, "alarm"), ("freeze", "scratch"), ("button+0.4", "sip")],
    freeze=("freeze", "stare"),
)

SCENES = [SC_FRIDAY, SC_FANMAIL, SC_TRIP, SC_SNEEZE, SC_WIFI, SC_BUCKS, SC_ALLOW, SC_FUN]


# ------------------------------------------------------------------ build + render
def build():
    by = {k: (who, line) for k, who, line in LINES}
    tracks = {v: np.zeros(int(150 * SR), np.float32) for v in (WORKER, COWORKER, COWORKER2, BOSS)}
    audio_cache = {}

    def line_len(key):
        who, line = by[key]
        if key not in audio_cache:
            audio_cache[key] = voices.say(who, line)
        return len(audio_cache[key]) / SR
    t, plan = 0.2, []
    for sc in SCENES:
        m = B.plan(sc["beats"], line_len)
        for key in m:
            if key in by:
                who = by[key][0]
                i = int((t + m[key][0]) * SR)
                tracks[who][i:i + len(audio_cache[key])] += audio_cache[key]
        plan.append(dict(sc, t0=t, m=m))
        t += m["end"]
    total = t + 2.6
    n = int(total * SR)
    env = {}
    for v, tr in tracks.items():
        hop = SR // FPS
        rms = np.sqrt(np.convolve(tr[:n] ** 2, np.ones(hop) / hop, "same"))[::hop]
        env[v] = np.clip(rms / (np.percentile(rms[rms > 1e-4], 90) + 1e-6), 0, 1.2) if (rms > 1e-4).any() else rms
    voice = voices.clarity(sum(tr[:n] for tr in tracks.values()))
    fx = synth("cafe", total) * .2

    def add(x, a):
        i = max(0, int(a * SR))
        fx[i:i + len(x)] += x[:max(0, n - i)].astype(np.float32)
    rng = np.random.default_rng(4)
    for p in plan:
        m = p["m"]
        for spec, name in p["sfx"]:
            T0 = p["t0"] + at(m, spec)
            if name == "steps":
                for k, s in enumerate(np.arange(0, 1.1, .28)):
                    add(ogg(f"footstep0{k % 4}", .6), T0 + s)
            elif name == "door":
                add(ogg("doorClose_2", 1.0), T0)
            elif name == "thud":
                add(ogg("impactSoft_heavy_001", .9), T0)
            elif name == "bang":
                add(ogg("impactPlate_light_001", 1.0), T0)
            elif name == "keys":
                x = np.zeros(int(1.4 * SR), np.float32)
                for s in np.arange(0, 1.3, .08):
                    i = int((s + rng.uniform(0, .03)) * SR)
                    x[i:i + 300] += rng.normal(0, 1, 300) * np.exp(-np.arange(300) / 60) * .12
                add(x, T0)
            elif name == "whirr":
                d = np.arange(int(.7 * SR)) / SR
                add(np.sin(2 * np.pi * 180 * d) * (.5 + .5 * np.sin(2 * np.pi * 14 * d)) * .08, T0)
            elif name == "alarm":
                d = np.arange(int((at(m, "freeze") + .05) * SR)) / SR
                add(np.sign(np.sin(2 * np.pi * (700 + 300 * (np.sin(2 * np.pi * 2 * d) > 0)) * d)) * .035, T0)
            elif name == "sip":
                add(synth("sip", .6) * 1.6, T0)
            else:
                add(B.sfx(name, rng), T0)
        for spec, cam, style in p["cams"]:
            if style == "whip" or style == "snap":
                add(B.sfx("whoosh", rng) * (.7 if style == "whip" else .4), p["t0"] + at(m, spec) - .12)
    mix = voice + fx
    return plan, env, (mix / max(np.abs(mix).max(), 1e-6) * .95).astype(np.float32), total


def camera(p, t):
    """(zoom, x, y, rot) for this moment + whip-blur amount. Whip: a fast slide into the new shot; snap: zoom punch."""
    m = p["m"]
    cuts = sorted(((at(m, s), cam, style) for s, cam, style in p["cams"]), key=lambda c: c[0])
    i = max([j for j, c in enumerate(cuts) if c[0] <= t] or [0])
    w0, cam, style = cuts[i]
    w1 = cuts[i + 1][0] if i + 1 < len(cuts) else m["end"]
    z, x, y, r = cam
    z *= 1 + .04 * min(1, (t - w0) / max(w1 - w0, .3))                    # slow push within the shot
    blur = 0.0
    if style == "whip" and i > 0 and t - w0 < .18:
        k = ease((t - w0) / .18)
        pz, px, py, pr = cuts[i - 1][1]
        z, x, y, r = lerp(pz, z, k), lerp(px, x, k), lerp(py, y, k), lerp(pr, r, k)
        blur = math.sin(math.pi * k)
    if style == "snap" and t - w0 < .12:
        z *= lerp(.8, 1.0, ease((t - w0) / .12))
    return (z, x, y, r), blur


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
            (z, x, y, r), blur = camera(p, t)
            ctx = cairo.Context(surf)
            ctx.translate(W / 2, 1000)
            ctx.rotate(math.radians(r))
            ctx.scale(z, z)
            ctx.translate(-x, -y)

            def talk(voice, fi=fi):
                e = env[voice]
                return float(e[min(fi, len(e) - 1)]) * .9
            p["draw"](ctx, t, p["m"], talk)
            ctx.identity_matrix()
            surf.flush()
            frame = np.frombuffer(surf.get_data(), np.uint8).reshape(H, W, 4).copy()
            frame = B.whip_blur(frame, blur)
            fz = p.get("freeze")
            if fz and at(p["m"], fz[0]) <= t < at(p["m"], fz[1]):
                frame = B.freeze_tint(frame, 1.0)
            # overlays: title, captions, end card (drawn on a fresh surface over the frame)
            ov = cairo.ImageSurface.create_for_data(memoryview(frame.reshape(-1)), cairo.FORMAT_ARGB32, W, H)
            o = cairo.Context(ov)
            rrect(o, 110, 80, W - 220, 120, 34, fill=(1, 1, 1), w=6)
            text(o, "things to say at work", W / 2, 140, 48, FONT, col="#e0457b")
            for key, (s0, s1) in p["m"].items():
                if key in TXT and s0 <= t <= s1 + .2:
                    words = TXT[key].split()
                    k = max(1, min(len(words), int(len(words) * (t - s0) / max(s1 - s0, .3)) + 1))
                    c0 = (k - 1) // 3 * 3
                    chunk = " ".join(words[c0:k]).upper()
                    size = 66 if len(chunk) < 20 else int(66 * 20 / len(chunk))
                    text(o, chunk, W / 2, 1760, size, FONT, col=(1, 1, 1), outline=(.1, .08, .1), ow=12)
            if p is plan[-1] and t > p["m"]["end"] - .3:
                kk = ease((t - p["m"]["end"] + .3) / .4)
                rrect(o, 110, 760, W - 220, 230, 40, fill="#e0457b", w=6)
                text(o, "which one are you", W / 2, 840, 56 * kk + 1, FONT, col=(1, 1, 1))
                text(o, "using on Monday?", W / 2, 915, 56 * kk + 1, FONT, col=(1, 1, 1))
            ov.flush()
            enc.stdin.write(bytes(frame))
        enc.stdin.close()
        if enc.wait():
            raise RuntimeError("ffmpeg failed")
    print("wrote", out, f"({total:.1f} s)")


if __name__ == "__main__":
    render(sys.argv[1] if len(sys.argv) > 1 else "work2.mp4")
