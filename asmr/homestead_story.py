"""'The goat got out': a ~60 s cozy homestead ASMR cartoon told as two continuous tasks, no jump cuts.

Part 1 (inside, every step): she finishes her tea and sets the cup down, pushes the chair back and stands, walks
across the wood floor, takes her straw hat off the hook and puts it on, sits on the bench and pulls on one boot,
then the other, picks up her basket, lifts the latch and opens the creaky door, and steps out.
Part 2 (outside, one task): she closes the door behind her and finds the goat out of its pen. The goat bolts, she
runs after it across the grass, the hens scatter flapping and squawking, she catches up gently, walks the goat back
into the pen, swings the gate shut, drops the latch and gives the goat a pat.

Sound follows movement: every footstep, hoof, wing flap, latch, creak and clock tick is a single real recorded sound
(cut from the CC0 library) placed at the exact moment the animation makes it: a foot lands, a hoof hits the grass,
the pendulum reaches the end of its swing. Overlapping sources play together, panned to where they are on screen.

    python asmr/homestead_story.py LIB_DIR OUT.mp4
"""
import math
import os
import subprocess
import sys
import tempfile

import cairocffi as cairo
import numpy as np
import soundfile as sf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cozy_morning as K                                                       # noqa: E402
import homestead_day as HD                                                     # noqa: E402
from cozy_morning import C, SR, W, H, arc_line, caption, ease, ell, lerp, lin, line, load, onsets, paint, poly, rr  # noqa: E402

FPS = 30
DT = 1 / 600                                                                   # motion sampling step for events


# ------------------------------------------------------------------ keyframe tracks
def track(t, keys):
    """Value at time t from [(time, value), ...], eased between keys, held before the first and after the last."""
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t < t1:
            k = ease((t - t0) / max(t1 - t0, 1e-6))
            if isinstance(v0, tuple):
                return tuple(lerp(a, b, k) for a, b in zip(v0, v1))
            return lerp(v0, v1, k)
    return keys[-1][1]


def gait(xfun, t0, t1, stride):
    """Footfalls of something moving along x(t): one every `stride` pixels travelled. Returns (times, phase(t))."""
    ts = np.arange(t0, t1, DT)
    xs = np.array([xfun(t) for t in ts])
    dist = np.concatenate([[0], np.cumsum(np.abs(np.diff(xs)))])
    ph = dist / stride * math.pi
    steps = [float(ts[i]) for i in range(1, len(ts)) if int(ph[i] // math.pi) > int(ph[i - 1] // math.pi)]

    def phase(t):
        if t <= t0:
            return 0.0
        i = min(len(ts) - 1, int((t - t0) / DT))
        return float(ph[i])
    return steps, phase


# ------------------------------------------------------------------ one-shot sound pools
class Pools:
    """Single real sounds cut out of recordings: each footstep / hoof / flap / creak becomes its own clip."""

    def __init__(self, lib):
        self.lib, self.p, self.rng = lib, {}, np.random.default_rng(11)

    def _get(self, sid):
        f = os.path.join(self.lib, "sounds", sid + ".mp3")
        return load(self.lib, sid) if os.path.exists(f) else None

    def hits(self, name, ids, length=0.3, gap=0.15, thresh=0.25, n=14):
        out = []
        for sid in ids:
            a = self._get(sid)
            if a is None:
                continue
            for h in onsets(a, gap, thresh):
                i0 = max(0, int((h - 0.012) * SR))
                seg = a[i0:i0 + int(length * SR)].copy()
                if len(seg) < int(0.05 * SR):
                    continue
                fi, fo = int(0.004 * SR), int(min(0.08, length / 3) * SR)
                seg[:fi] *= np.linspace(0, 1, fi)[:, None]
                seg[-fo:] *= np.linspace(1, 0, fo)[:, None]
                pk = np.abs(seg).max()
                if pk > 1e-3:
                    out.append(seg / pk)
                if len(out) >= n:
                    break
        self.p[name] = out
        return len(out)

    def loudest(self, name, ids, length=1.2, n=3):
        """The loudest stretch of each recording (a door's creak, a bleat)."""
        out = []
        for sid in ids:
            a = self._get(sid)
            if a is None:
                continue
            m = np.abs(a).mean(1)
            L = int(length * SR)
            if len(m) <= L:
                seg = a.copy()
            else:
                c = np.cumsum(m ** 2)
                e = c[L:] - c[:-L]
                i = int(np.argmax(e))
                seg = a[i:i + L].copy()
            f = int(0.05 * SR)
            seg[:f] *= np.linspace(0, 1, f)[:, None]
            seg[-f:] *= np.linspace(1, 0, f)[:, None]
            out.append(seg / max(1e-3, np.abs(seg).max()))
            if len(out) >= n:
                break
        self.p[name] = out
        return len(out)

    def pick(self, name):
        lst = self.p.get(name) or []
        return lst[int(self.rng.integers(len(lst)))] if lst else None


class Mixer:
    def __init__(self, total):
        self.n = int((total + 1) * SR)
        self.buf = np.zeros((self.n, 2), np.float32)
        self.log = []

    def put(self, a, t, gain=1.0, pan=0.0):
        if a is None:
            return
        i = int(max(0, t) * SR)
        seg = a[:max(0, self.n - i)] * gain
        bal = np.array([1 - 0.45 * pan, 1 + 0.45 * pan], np.float32)
        self.buf[i:i + len(seg)] += seg * bal
        self.log.append((round(t, 2), round(gain, 2)))

    def bed(self, a, t0, t1, gain, fade=1.0):
        if a is None:
            return
        L = int((t1 - t0) * SR)
        reps = int(np.ceil(L / len(a))) + 1
        seg = np.concatenate([a] * reps)[:L].copy()
        f = int(fade * SR)
        seg[:f] *= np.linspace(0, 1, f)[:, None]
        seg[-f:] *= np.linspace(1, 0, f)[:, None]
        i = int(t0 * SR)
        self.buf[i:i + len(seg)] += seg[:self.n - i] * gain


def pan_of(x, cam_x):
    return max(-1.0, min(1.0, (x - cam_x) / 600))


# ------------------------------------------------------------------ props and characters
def goat(ctx, x, y, t, face=1, phase=0.0, run=0.0, bleat=0.0, s=1.0):
    """Cream goat with tan patches, side view, feet at y. phase drives the legs; run 0..1 = trot..gallop."""
    bounce = abs(math.sin(phase)) * 14 * run
    ctx.save()
    ctx.translate(x, y - bounce)
    ctx.scale(face * s, s)
    legs = [(-70, 0.0), (-40, math.pi / 2), (55, math.pi), (85, 1.5 * math.pi)]
    for lx, off in legs:                                                         # legs swing with the gait
        sw = math.sin(phase + off) * (16 + 22 * run)
        line(ctx, [(lx, -110), (lx + sw, -12)], w=22)
        line(ctx, [(lx, -110), (lx + sw, -12)], w=12, col="#f3ead8")
        ell(ctx, lx + sw, -8, 12, 9, fill="#4a3a2e", w=4)
    poly(ctx, [(-110, -175), (-140, -215), (-118, -165)], fill="#f3ead8", w=5)    # tail
    ell(ctx, 0, -150, 125, 62, fill="#f3ead8")                                    # body
    ell(ctx, -30, -165, 46, 30, fill="#d9a46a", w=0)
    ell(ctx, 50, -130, 30, 20, fill="#d9a46a", w=0)
    rr(ctx, 90, -230, 46, 80, 20, fill="#f3ead8")                                 # neck
    hx, hy = 140, -235 + 6 * math.sin(phase * 0.5) * run
    ell(ctx, hx, hy, 50, 40, fill="#f3ead8")                                      # head
    poly(ctx, [(hx - 20, hy - 30), (hx - 40, hy - 70), (hx - 4, hy - 36)], fill="#b9b3a8", w=5)   # horns
    poly(ctx, [(hx + 4, hy - 34), (hx - 6, hy - 74), (hx + 20, hy - 38)], fill="#b9b3a8", w=5)
    ell(ctx, hx - 44, hy - 4, 26, 12, fill="#d9a46a", rot=0.5)                     # ear
    poly(ctx, [(hx + 26, hy + 30), (hx + 36, hy + 66), (hx + 44, hy + 28)], fill="#f3ead8", w=5)  # beard
    arc_line(ctx, hx + 14, hy - 4, 9, math.pi * 0.15, math.pi * 0.85, w=5)        # closed happy eye
    if bleat > 0.1:
        ell(ctx, hx + 40, hy + 14, 10 * bleat, 12 * bleat, fill="#c9605a", w=4)
    else:
        arc_line(ctx, hx + 36, hy + 8, 10, 0.2, 1.4, w=4)
    ell(ctx, hx + 46, hy - 2, 4, 3, fill="#2a1d17", w=0)
    rr(ctx, 88, -205, 54, 16, 6, fill="#e04848", w=4)                             # red collar
    ctx.restore()


def hen_flap(ctx, x, y, t, col, face, flap, hop):
    HD.hen(ctx, x, y - hop, t, 1.15, col=col, peck_phase=x * 0.01, face=face)
    if flap > 0.01:
        for sg in (-1, 1):
            a = math.sin(t * 40) * 0.8 * flap
            ctx.save()
            ctx.translate(x - 5 * face, y - hop - 60)
            ctx.rotate(-1.2 * face + a * sg * 0.5)
            ell(ctx, 0, -40, 22, 50, fill=col, w=5)
            ctx.restore()


def straw_hat(ctx, x, y, s=1.0):
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ell(ctx, 0, 0, 250, 48, fill="#f2d38a")
    ctx.move_to(-140, 0)
    ctx.curve_to(-140, -150, 140, -150, 140, 0)
    ctx.close_path()
    paint(ctx, "#f2d38a")
    line(ctx, [(-136, -26), (136, -26)], w=24, col="#e04848")
    ctx.restore()


def boot(ctx, x, y):
    rr(ctx, x - 24, y - 78, 48, 80, 12, fill="#8a5232")
    ell(ctx, x + 8, y, 38, 18, fill="#8a5232")
    line(ctx, [(x - 22, y - 60), (x + 22, y - 60)], w=4, col="#b8743f")


def teacup(ctx, x, y, saucer=True):
    if saucer:
        ell(ctx, x, y, 54, 12, fill="#ffffff")
    ctx.move_to(x - 40, y - 60)
    ctx.curve_to(x - 38, y - 8, x + 38, y - 8, x + 40, y - 60)
    ctx.close_path()
    paint(ctx, "#ffffff")
    arc_line(ctx, x + 46, y - 40, 15, -math.pi / 2, math.pi / 2, w=6)
    ell(ctx, x, y - 60, 40, 9, fill="#c98a45", w=4)
    line(ctx, [(x - 34, y - 40), (x + 34, y - 40)], w=5, col="#f29fb3")


# ------------------------------------------------------------------ part 1: inside the cottage
FLOOR = 1560
NECK_STAND, NECK_TABLE, NECK_BENCH = FLOOR - 500, FLOOR - 430, FLOOR - 480
TABLE_X, HOOK_X, BENCH_X, DOOR_X = 380, 1060, 1300, 1700                        # door: hinge on its right edge
CLOCK_X, CLOCK_Y = 800, 640


class Inside:
    def __init__(self):
        # her path across the room (x) and height (sitting / standing)
        self.xk = [(0, TABLE_X), (4.6, TABLE_X), (8.8, HOOK_X - 100), (11.3, HOOK_X - 100), (12.9, BENCH_X),
                   (18.0, BENCH_X), (20.6, DOOR_X - 110), (23.4, DOOR_X - 110), (25.6, DOOR_X + 160)]
        self.yk = [(0, NECK_TABLE), (3.9, NECK_TABLE), (4.6, NECK_STAND), (12.9, NECK_STAND), (13.4, NECK_BENCH),
                   (17.4, NECK_BENCH), (18.0, NECK_STAND)]
        self.dur = 26.0
        self.walk_steps, self.walk_phase = gait(lambda t: track(t, self.xk), 0, self.dur, 92)
        self.walk_steps = [t for t in self.walk_steps if not (12.9 < t < 18.0)]
        self.cam = [(0, (1.3, 520, 1080)), (3.8, (1.3, 520, 1080)), (6.5, (1.1, 760, 1090)), (9.4, (1.45, 960, 960)),
                    (11.6, (1.45, 960, 960)), (13.2, (1.45, 1240, 1110)), (17.2, (1.45, 1240, 1110)),
                    (19.0, (1.15, 1450, 1080)), (21.2, (1.45, 1640, 1080)), (23.6, (1.3, 1700, 1060)), (26.0, (1.5, 1820, 1060))]
        self.tick_times = [k * 1.0 + 0.5 for k in range(26)]                           # pendulum ends its swing

    # moments
    CUP_DOWN, CHAIR = 3.1, 4.0
    HAT_GRAB, HAT_ON = 9.9, 11.0
    BOOT_L, BOOT_R = (14.3, 15.0), (16.0, 16.7)                                     # (pull on, stomp down)
    BASKET = 18.4
    LATCH, DOOR_OPEN = 21.5, (21.9, 23.3)

    def door_angle(self, t):
        return 75 * ease((t - self.DOOR_OPEN[0]) / (self.DOOR_OPEN[1] - self.DOOR_OPEN[0]))

    def draw(self, ctx, t):
        x, ny = track(t, self.xk), track(t, self.yk)
        # room
        ctx.rectangle(-2000, -2000, 6000, 6000)
        ctx.set_source(lin(0, 0, 0, FLOOR, [(0, "#fdebc6"), (1, "#f8dfb0")]))
        ctx.fill()
        rr(ctx, -2000, FLOOR - 260, 6000, 260, 0, fill="#e9c08a", w=6)                     # wainscot
        for k in range(-20, 60):
            line(ctx, [(k * 60, FLOOR - 255), (k * 60, FLOOR - 4)], w=3, col="#d9a96a")
        rr(ctx, -2000, FLOOR, 6000, 800, 0, fill="#d99a5b", w=6)                            # wood floor
        for k in range(-10, 40):
            line(ctx, [(k * 120, FLOOR), (k * 120 - 80, FLOOR + 400)], w=4, col="#c0824a")
        ell(ctx, 1050, FLOOR + 90, 420, 60, fill="#f2b5a8", w=6)                             # rug
        ell(ctx, 1050, FLOOR + 90, 340, 44, fill=None, w=4)
        self.window(ctx, t)
        self.clock(ctx, t)
        self.hooks(ctx, t)
        self.door(ctx, t)
        # chair behind her at the table, pushed back when she stands
        cx = TABLE_X + 30 * ease((t - self.CHAIR) / 0.5)
        for dx in (-90, 90):
            rr(ctx, cx + dx - 12, FLOOR - 470, 24, 300, 8, fill="#b9763f")
        rr(ctx, cx - 100, FLOOR - 470, 200, 26, 10, fill="#b9763f")
        rr(ctx, cx - 100, FLOOR - 400, 200, 20, 8, fill="#b9763f")
        # bench (behind her when she sits)
        rr(ctx, BENCH_X - 280, FLOOR - 150, 560, 34, 10, fill="#b9763f")
        for dx in (-260, 236):
            rr(ctx, BENCH_X + dx, FLOOR - 120, 24, 120, 6, fill="#a0652f")
        # her
        sitting_table = t < 4.3
        on_bench = 13.2 < t < 17.6
        hands, props, feet, lift, tilt, eyes, mouth = {}, {}, ["slipper", "slipper"], [0.0, 0.0], 0.0, "happy", "smile"
        ph = self.walk_phase(t)
        walking = not sitting_table and not on_bench and any(abs(t - s) < 0.6 for s in self.walk_steps)
        if t > self.BOOT_L[1] - 0.05:
            feet[0] = "boot"
        if t > self.BOOT_R[1] - 0.05:
            feet[1] = "boot"
        if sitting_table:
            sip = ease(t / 0.6) * (1 - ease((t - 2.2) / 0.6))
            down = ease((t - 2.4) / 0.6)
            hx = lerp(lerp(x + 120, x + 55, sip), x + 150, down)
            hy = lerp(lerp(FLOOR - 340, ny - 110, sip), FLOOR - 330, down)
            if t < self.CUP_DOWN:
                hands["right"] = (hx, hy)
                props["right"] = lambda c, px, py: teacup(c, px + 10, py + 46, saucer=False)
                mouth = "o" if sip > 0.6 else "smile"
            else:
                hands["right"] = (x + 150, FLOOR - 340)
            hands["left"] = (x - 110, FLOOR - 340) if t < 3.6 else (x - 120, FLOOR - 330 - 20 * ease((t - 3.6) / 0.4))
        elif on_bench:
            lift = [36 + 8 * math.sin(t * 3.1), 36 + 8 * math.sin(t * 3.1 + 1.3)]        # feet dangle off the bench
            for k, (pull, stomp) in enumerate((self.BOOT_L, self.BOOT_R)):
                if pull - 0.9 < t < stomp + 0.1:
                    side = "left" if k == 0 else "right"
                    sg = -1 if k == 0 else 1
                    u = ease((t - (pull - 0.9)) / 0.6)                            # reach for the boot under the bench
                    lift[k] = 36 + 40 * ease((t - (pull - 0.3)) / 0.3) * (1 - ease((t - stomp + 0.15) / 0.15))
                    if t > stomp - 0.05:
                        lift[k] = 0.0                                                   # heel stomped down into the boot
                    bx, by = x + sg * 46, FLOOR - 60 - lift[k]
                    hands[side] = (lerp(x + sg * 120, bx + sg * 30, u), lerp(FLOOR - 300, by - 70, u))
                    hands["left" if k else "right"] = (x - sg * 60, FLOOR - 320)
                    tilt = 10 * sg * u
                    if t < pull:
                        props[side] = lambda c, px, py: boot(c, px, py + 50)
            if t > 17.0:                                                          # reach for the basket
                hands["right"] = (lerp(x + 120, x + 150, ease((t - 17.0) / 0.4)), FLOOR - 300)
        elif self.HAT_GRAB - 0.9 < t < self.HAT_ON + 0.3:
            u = ease((t - (self.HAT_GRAB - 0.9)) / 0.8)
            v = ease((t - self.HAT_GRAB) / (self.HAT_ON - self.HAT_GRAB))
            hands["right"] = (lerp(lerp(x + 120, HOOK_X, u), x + 120, v), lerp(lerp(ny + 200, FLOOR - 560, u), ny - 140, v))
            hands["left"] = (x - 120, lerp(ny + 200, ny - 140, v))
            eyes = "open" if u > 0.3 and v < 0.6 else "happy"
        elif self.LATCH - 0.7 < t < self.DOOR_OPEN[1]:
            u = ease((t - (self.LATCH - 0.7)) / 0.6)
            hands["left"] = (lerp(x + 40, DOOR_X - 10, u), lerp(ny + 220, FLOOR - 330, u)) if t < self.DOOR_OPEN[0] + 0.2 else (x - 100, ny + 230)
            hands["right"] = (x + 110, ny + 260)
        if walking and not hands:
            sw = math.sin(ph)
            hands = {"left": (x - 110 + 30 * sw, ny + 250), "right": (x + 110 - 30 * sw, ny + 250)}
        if t > self.BASKET and "right" not in props:
            props["right"] = lambda c, px, py: HD.basket(c, px - 4, py - 10)
        if not sitting_table:
            K.girl(ctx, x, ny, t, hands=hands, props=props, eyes=eyes, mouth=mouth, tilt=tilt,
                   hat=t > self.HAT_ON, legs=True, step=ph if walking else None, feet=tuple(feet), lift=tuple(lift))
        else:
            K.girl(ctx, x, ny, t, hands=hands, props=props, eyes=eyes, mouth=mouth, tilt=tilt)
        # hat on its hook / in her hand
        if t < self.HAT_GRAB:
            straw_hat(ctx, HOOK_X, FLOOR - 600, 0.55)
        elif t < self.HAT_ON:
            v = ease((t - self.HAT_GRAB) / (self.HAT_ON - self.HAT_GRAB))
            straw_hat(ctx, lerp(HOOK_X, x, v), lerp(FLOOR - 600, ny - 315, v), lerp(0.55, 1.0, v))
        # boots waiting under the bench, basket on the bench
        if t < self.BOOT_L[0] - 0.9:
            boot(ctx, BENCH_X - 60, FLOOR + 6)
        if t < self.BOOT_R[0] - 0.9:
            boot(ctx, BENCH_X + 20, FLOOR + 6)
        if t < self.BASKET:
            HD.basket(ctx, BENCH_X + 200, FLOOR - 300)
        # the table in front of her (tablecloth hides her lap)
        rr(ctx, TABLE_X - 260, FLOOR - 340, 520, 30, 10, fill="#c98a45")
        ctx.move_to(TABLE_X - 250, FLOOR - 312)
        ctx.line_to(TABLE_X + 250, FLOOR - 312)
        ctx.line_to(TABLE_X + 270, FLOOR - 110)
        ctx.curve_to(TABLE_X + 90, FLOOR - 90, TABLE_X - 90, FLOOR - 90, TABLE_X - 270, FLOOR - 110)
        ctx.close_path()
        paint(ctx, "#fbf1dc")
        for k in range(-4, 5):
            line(ctx, [(TABLE_X + k * 56, FLOOR - 310), (TABLE_X + k * 60, FLOOR - 100)], w=10, col="#f6b6b0")
        for dx in (-230, 230):
            rr(ctx, TABLE_X + dx - 12, FLOOR - 110, 24, 110, 6, fill="#a0652f")
        if t >= self.CUP_DOWN:
            teacup(ctx, TABLE_X + 160, FLOOR - 342)
        else:
            ell(ctx, TABLE_X + 160, FLOOR - 342, 54, 12, fill="#ffffff")

    def window(self, ctx, t):
        x, y, w, h = 120, 560, 460, 470
        rr(ctx, x - 22, y - 22, w + 44, h + 44, 18, fill="#e9b46a")
        rr(ctx, x, y, w, h, 8, fill=lin(0, y, 0, y + h, [(0, "#9fd3f0"), (1, "#e3f4fb")]))
        ell(ctx, x + 120, y + h - 10, 200, 120, fill="#9fd17a", w=0)
        ell(ctx, x + 360, y + h, 220, 100, fill="#8cc78f", w=0)
        line(ctx, [(x + w / 2, y), (x + w / 2, y + h)], w=12, col="#e9b46a")
        line(ctx, [(x, y + h / 2), (x + w, y + h / 2)], w=12, col="#e9b46a")
        K.curtain(ctx, x, y, w, t)

    def clock(self, ctx, t):
        rr(ctx, CLOCK_X - 70, CLOCK_Y - 90, 140, 330, 30, fill="#b9763f")
        ell(ctx, CLOCK_X, CLOCK_Y, 56, 56, fill="#fff8ec")
        for k in range(12):
            a = k * math.pi / 6
            ell(ctx, CLOCK_X + 44 * math.cos(a), CLOCK_Y + 44 * math.sin(a), 3, 3, fill="#2a1d17", w=0)
        line(ctx, [(CLOCK_X, CLOCK_Y), (CLOCK_X, CLOCK_Y - 36)], w=5)
        line(ctx, [(CLOCK_X, CLOCK_Y), (CLOCK_X + 26, CLOCK_Y + 8)], w=5)
        a = 0.35 * math.cos(math.pi * (t - 0.5))                                   # pendulum: ends of swing at ticks
        px, py = CLOCK_X + 110 * math.sin(a), CLOCK_Y + 80 + 110 * math.cos(a)
        line(ctx, [(CLOCK_X, CLOCK_Y + 80), (px, py)], w=5)
        ell(ctx, px, py, 18, 18, fill="#ffd166", w=5)

    def hooks(self, ctx, t):
        rr(ctx, HOOK_X - 160, FLOOR - 700, 320, 28, 8, fill="#b9763f")
        for dx in (-110, 0, 110):
            ell(ctx, HOOK_X + dx, FLOOR - 660, 12, 12, fill="#8a5232", w=5)

    def door(self, ctx, t):
        x0, x1, top = DOOR_X - 20, DOOR_X + 260, FLOOR - 720
        rr(ctx, x0 - 26, top - 26, x1 - x0 + 52, FLOOR - top + 26, 10, fill="#b9763f")
        ctx.rectangle(x0, top, x1 - x0, FLOOR - top)                              # the outside, through the doorway
        ctx.set_source(lin(0, top, 0, FLOOR, [(0, "#a8dcf5"), (0.6, "#e3f4fb"), (0.61, "#9fd17a"), (1, "#8cc78f")]))
        ctx.fill()
        a = math.radians(self.door_angle(t))
        w = (x1 - x0) * math.cos(a)
        rr(ctx, x1 - w, top, max(w, 6), FLOOR - top, 6, fill="#c98a45")
        if w > 60:
            for k in (0.28, 0.72):
                rr(ctx, x1 - w + w * 0.15, top + (FLOOR - top) * k - 120, w * 0.7, 220, 10, fill="#d9a05b", w=5)
            lift = 18 if self.LATCH - 0.05 < t < self.DOOR_OPEN[0] + 0.3 else 0
            rr(ctx, x1 - w + 16, FLOOR - 340 - lift, 50, 14, 6, fill="#5a5a5a", w=4)           # latch bar
            ell(ctx, x1 - w + 40, FLOOR - 300, 12, 12, fill="#5a5a5a", w=4)
        if self.door_angle(t) > 5:                                                  # daylight spilling in
            g = cairo.LinearGradient(x0, 0, x0 - 600, 0)
            g.add_color_stop_rgba(0, 1, 0.97, 0.8, 0.45 * self.door_angle(t) / 75)
            g.add_color_stop_rgba(1, 1, 0.97, 0.8, 0)
            ctx.set_source(g)
            ctx.rectangle(x0 - 600, top, 600, FLOOR - top + 300)
            ctx.fill()

    def sounds(self, P, M, t0, camx):
        for s in self.walk_steps:                                                  # her footsteps on the wood floor
            M.put(P.pick("wood"), t0 + s, 0.55, pan_of(track(s, self.xk), camx(s)))
        for k in self.tick_times:                                                  # clock: tick at each end of the swing
            M.put(P.pick("tick"), t0 + k, 0.12, pan_of(CLOCK_X, camx(k)))
        M.put(P.pick("cup"), t0 + self.CUP_DOWN, 0.6, pan_of(TABLE_X + 160, camx(self.CUP_DOWN)))
        M.put(P.pick("chair"), t0 + self.CHAIR - 0.05, 0.6, pan_of(TABLE_X, camx(self.CHAIR)))
        M.put(P.pick("rustle"), t0 + 4.1, 0.35)                                    # standing up
        M.put(P.pick("rustle"), t0 + self.HAT_GRAB, 0.4)                           # hat off the hook
        M.put(P.pick("rustle"), t0 + self.HAT_ON - 0.1, 0.45)                      # hat on her head
        M.put(P.pick("rustle"), t0 + 13.25, 0.35)                                  # sits on the bench
        M.put(P.pick("chair"), t0 + 13.3, 0.25)                                    # bench takes her weight
        for pull, stomp in (self.BOOT_L, self.BOOT_R):
            M.put(P.pick("boot"), t0 + pull, 0.7)                                  # boot pulled on
            M.put(P.pick("wood"), t0 + stomp, 0.9)                                 # heel stomps into place
        M.put(P.pick("rustle"), t0 + 17.6, 0.35)                                   # stands up
        M.put(P.pick("basket"), t0 + self.BASKET, 0.5)
        M.put(P.pick("latch"), t0 + self.LATCH, 0.7, pan_of(DOOR_X, camx(self.LATCH)))
        M.put(P.pick("door"), t0 + self.DOOR_OPEN[0], 0.6, pan_of(DOOR_X, camx(self.DOOR_OPEN[0])))


# ------------------------------------------------------------------ part 2: outside
G = HD.GROUND
NECK_OUT = G - 360                                                              # standing outside (feet at G + 140)
FEET_Y = G + 140
HOUSE_DOOR, GATE_X, PEN_X = 180, 1620, 1900


class Outside:
    def __init__(self):
        self.dur = 34.0
        # her path: out the door, sees the goat, chases, catches up, leads it to the pen, gate, pat, a few steps back
        self.xk = [(0, HOUSE_DOOR + 60), (2.4, 470), (4.6, 470), (5.4, 620), (8.6, 1500), (12.6, 700), (15.4, 1120),
                   (16.6, 1180), (17.4, 1180), (22.0, GATE_X - 160), (23.0, GATE_X - 160), (24.8, GATE_X - 130),
                   (30.0, GATE_X - 130), (34.0, GATE_X - 420)]
        self.gk = [(0, 1000), (4.6, 1000), (5.0, 1050), (7.6, 1760), (8.0, 1760), (11.6, 760), (12.0, 760),
                   (14.4, 1280), (17.4, 1300), (22.0, GATE_X + 60), (23.6, 1800), (34.0, 1800)]
        self.run = [(0, 0.0), (4.6, 0.0), (5.2, 1.0), (14.2, 1.0), (15.4, 0.0)]          # 1 = running
        self.steps, self.phase = gait(lambda t: track(t, self.xk), 0, self.dur, 100)
        self.hooves, self.gphase = gait(lambda t: track(t, self.gk), 0, self.dur, 34)   # a hoof every 34 px
        # hens around the yard
        self.hens = [dict(x=820, col="#ffffff"), dict(x=1080, col="#c46a2e"), dict(x=1330, col="#ffffff"), dict(x=600, col="#c46a2e")]
        for h in self.hens:
            h["startle"] = []
            last = -9
            for t in np.arange(0, self.dur, 1 / 30):
                near = min(abs(track(t, self.xk) - h["x"]), abs(track(t, self.gk) - h["x"]))
                if near < 150 and track(t, self.run) > 0.5 and t - last > 2.5:
                    h["startle"].append(float(t))
                    last = t
        self.bleats = [3.2, 5.1, 9.8, 23.1, 27.0]
        self.door_shut = (0.9, 1.5)
        self.gate_close, self.gate_latch = (24.0, 25.2), 25.4
        self.cam = [(0, (1.15, 420, 1180)), (2.6, (1.0, 640, 1150)), (4.6, (0.95, 760, 1150)), (8.0, (0.85, 1150, 1170)),
                    (12.0, (0.85, 900, 1170)), (15.0, (1.0, 1180, 1160)), (19.0, (1.05, 1450, 1160)),
                    (24.0, (1.3, 1740, 1140)), (30.0, (1.3, 1720, 1140)), (34.0, (0.95, 1300, 1150))]

    def cam_at(self, t):
        """Keyframed camera, except during the chase: frame her and the goat together, zooming out as it pulls away."""
        base = track(t, self.cam)
        x, gx = track(t, self.xk), track(t, self.gk)
        d = abs(gx - x)
        dyn = (max(0.62, min(1.0, 980 / (d + 560))), (x + gx) / 2, 1150)
        w = ease((t - 4.4) / 0.8) * (1 - ease((t - 15.0) / 1.0))
        return tuple(lerp(a, b, w) for a, b in zip(base, dyn))

    def hen_state(self, h, t):
        """(x, hop, flap, face) for a hen: it scatters (hops, flaps, runs off) when the chase gets close."""
        dx, hop, flap, face = 0.0, 0.0, 0.0, 1
        for s in h["startle"]:
            u = t - s
            if 0 <= u < 0.9:
                hop = 70 * math.sin(math.pi * u / 0.9)
                flap = 1.0
            if u >= 0:
                away = 1 if h["x"] > track(s, self.xk) else -1
                dx += away * 160 * ease(u / 0.9)
                face = away
        return h["x"] + dx, hop, flap, face

    def draw(self, ctx, t):
        HD.sky(ctx, t, "day")
        HD.hills(ctx, "day")
        HD.tree(ctx, 1150, G - 10, 1.0)
        # the cottage on the left with its door
        rr(ctx, -300, G - 520, 640, 520, 6, fill="#fff3dd")
        poly(ctx, [(-340, G - 500), (20, G - 760), (380, G - 500)], fill="#e85d5d")
        rr(ctx, HOUSE_DOOR - 80, G - 330, 160, 330, 8, fill="#5a3a22")
        shut = ease((t - self.door_shut[0]) / (self.door_shut[1] - self.door_shut[0]))
        w = 160 * lerp(0.15, 1.0, shut)
        rr(ctx, HOUSE_DOOR + 80 - w, G - 330, w, 330, 8, fill="#c98a45")
        rr(ctx, -200, G - 380, 110, 100, 8, fill="#bfe3f5")
        HD.ground(ctx, "day", path=False)
        # pen with its gate
        for x in range(GATE_X + 120, 2400, 80):
            rr(ctx, x - 10, G - 30, 20, 140, 5, fill="#fff3dd", w=5)
        rr(ctx, GATE_X + 100, G + 10, 800, 16, 5, fill="#fff3dd", w=5)
        rr(ctx, GATE_X + 100, G + 60, 800, 16, 5, fill="#fff3dd", w=5)
        rr(ctx, GATE_X - 14, G - 50, 28, 170, 6, fill="#e9c08a")                    # gate post
        rr(ctx, GATE_X + 100, G - 50, 28, 170, 6, fill="#e9c08a")
        closed = ease((t - self.gate_close[0]) / (self.gate_close[1] - self.gate_close[0]))
        gw = 110 * lerp(0.2, 1.0, closed)                                          # gate swings on its post
        for gy in (G - 10, G + 50):
            rr(ctx, GATE_X, gy, gw, 16, 5, fill="#fff3dd", w=5)
        line(ctx, [(GATE_X, G + 66), (GATE_X + gw, G - 4)], w=8, col="#fff3dd")
        line(ctx, [(GATE_X, G + 66), (GATE_X + gw, G - 4)], w=3)
        lift = 14 if self.gate_latch - 0.4 < t < self.gate_latch else 0
        rr(ctx, GATE_X + 96, G + 14 - lift, 30, 10, 4, fill="#5a5a5a", w=3)
        for k in range(5):                                                          # the garden the goat raided
            ell(ctx, 960 + k * 70, G + 40 + (k % 2) * 20, 30, 24, fill="#6cc48a")
        # hens
        for h in self.hens:
            hx, hop, flap, face = self.hen_state(h, t)
            hen_flap(ctx, hx, FEET_Y + 20, t, h["col"], face, flap, hop)
        # the goat
        gx = track(t, self.gk)
        gv = track(t + 0.05, self.gk) - track(t - 0.05, self.gk)
        face = 1 if gv > 0.5 else -1 if gv < -0.5 else (-1 if t > 24.0 else 1 if t > 15 else -1)
        bl = max([math.sin(math.pi * min(1, (t - b) / 0.8)) for b in self.bleats if 0 <= t - b <= 0.8], default=0.0)
        goat(ctx, gx, FEET_Y, t, face=face, phase=self.gphase(t), run=track(t, self.run), bleat=bl, s=1.45)
        # her
        x = track(t, self.xk)
        runk = track(t, self.run)
        ph = self.phase(t)
        moving = abs(track(t + 0.05, self.xk) - track(t - 0.05, self.xk)) > 0.8
        ny = NECK_OUT - (6 * abs(math.sin(ph)) * runk if moving else 0)
        hands, props, eyes, mouth, tilt = {}, {}, "happy", "smile", 0.0
        if moving:
            sw = math.sin(ph)
            amp = lerp(30, 70, runk)
            hands = {"left": (x - 110 + amp * sw, ny + 250 - 40 * runk), "right": (x + 110 - amp * sw, ny + 250 - 40 * runk)}
            tilt = 6 * runk * (1 if track(t + 0.05, self.xk) > x else -1)
        if 2.6 < t < 5.0:
            eyes, mouth = "open", "o"
        if 0.6 < t < 1.6:                                                           # pulls the door shut behind her
            hands["left"] = (lerp(x - 120, HOUSE_DOOR + 60, ease((t - 0.6) / 0.4)), ny + 220)
        if 16.4 < t < 23.0:                                                         # hand on the goat's collar
            hands["right"] = (gx - 30, FEET_Y - 330)                                 # hand on its back, guiding
        if 23.6 < t < 25.6:                                                         # swings the gate shut
            hands["right"] = (GATE_X + 110 * lerp(0.2, 1.0, ease((t - 23.8) / 1.4)), G + 20)
        if 26.0 < t < 30.0:                                                         # pats the goat over the fence
            hands["right"] = (gx - 230 + 18 * math.sin(t * 9), FEET_Y - 360)
            eyes = "happy"
        if 30.2 < t < 31.4:                                                         # wipes her brow
            hands["left"] = (x - 40, ny - 150)
        props["left" if "left" not in hands or not (0.6 < t < 1.6) else "right"] = lambda c, px, py: HD.basket(c, px - 4, py - 10)
        K.girl(ctx, x, ny, t, hands=hands, props=props, eyes=eyes, mouth=mouth, tilt=tilt, hat=True, legs=True,
               step=ph if moving else None, feet=("boot", "boot"))
        if 2.8 < t < 4.6:                                                           # she spots the goat
            caption(ctx, "!", x + 150, ny - 380, 90 * ease((t - 2.8) / 0.25))

    def sounds(self, P, M, t0, camx):
        for s in self.steps:
            runk = track(s, self.run)
            M.put(P.pick("run" if runk > 0.5 else "grass"), t0 + s, 0.6 + 0.25 * runk, pan_of(track(s, self.xk), camx(s)))
        for s in self.hooves:
            runk = track(s, self.run)
            M.put(P.pick("hoof"), t0 + s, 0.25 + 0.3 * runk, pan_of(track(s, self.gk), camx(s)))
        for b in self.bleats:
            M.put(P.pick("bleat"), t0 + b, 0.7, pan_of(track(b, self.gk), camx(b)))
        for h in self.hens:
            for s in h["startle"]:
                p = pan_of(h["x"], camx(s))
                M.put(P.pick("squawk"), t0 + s, 0.55, p)
                for k in range(5):                                                  # wing beats while it hops
                    M.put(P.pick("wing"), t0 + s + 0.05 + k * 0.16, 0.45, p)
        M.put(P.pick("door"), t0 + self.door_shut[0], 0.35, pan_of(HOUSE_DOOR, camx(1.0)))
        M.put(P.pick("latch"), t0 + self.door_shut[1], 0.55, pan_of(HOUSE_DOOR, camx(1.5)))
        M.put(P.pick("gate"), t0 + self.gate_close[0], 0.6, pan_of(GATE_X, camx(self.gate_close[0])))
        M.put(P.pick("glatch"), t0 + self.gate_latch, 0.7, pan_of(GATE_X, camx(self.gate_latch)))
        for k in range(8):                                                          # the pat: soft rustles on its fur
            M.put(P.pick("rustle"), t0 + 26.2 + k * 0.45, 0.2)


# ------------------------------------------------------------------ render
def build_pools(lib):
    P = Pools(lib)
    n = {
        "wood": P.hits("wood", ["steps_wood_1", "steps_wood_3", "steps_wood_2"], 0.32, 0.2, 0.3),
        "grass": P.hits("grass", ["steps_grass_2", "steps_grass_1", "leaves_steps_2"], 0.32, 0.2, 0.3),
        "run": P.hits("run", ["run_grass_3", "run_grass_1", "steps_grass_3"], 0.25, 0.14, 0.3),
        "hoof": P.hits("hoof", ["hooves_1", "hooves_2", "hooves_3"], 0.16, 0.1, 0.3, n=20),
        "wing": P.hits("wing", ["wings_1", "wings_2", "wings_3"], 0.3, 0.12, 0.3),
        "squawk": P.loudest("squawk", ["squawk_1", "squawk_2", "squawk_3", "chickens_3"], 0.7),
        "bleat": P.loudest("bleat", ["goat_1", "goat_2", "goat_3"], 1.0),
        "tick": P.hits("tick", ["clock_1", "clock_2", "clock_3"], 0.12, 0.3, 0.4),
        "cup": P.hits("cup", ["teacup_2", "teacup_1"], 0.5, 0.4, 0.4, n=4),
        "chair": P.loudest("chair", ["chair_2", "chair_3", "chair_1"], 0.6),
        "rustle": P.loudest("rustle", ["rustle_2", "rustle_3", "rustle_1"], 0.5),
        "boot": P.loudest("boot", ["boots_1", "boots_2", "boots_3"], 0.7),
        "basket": P.loudest("basket", ["rustle_1"], 0.4),
        "latch": P.hits("latch", ["door_latch_1", "door_latch_3", "door_latch_2"], 0.45, 0.3, 0.35, n=4),
        "door": P.loudest("door", ["door_creak_2", "door_creak_1", "door_creak_3"], 1.4),
        "gate": P.loudest("gate", ["gate_creak_3", "gate_creak_1", "gate_creak_2"], 1.2),
        "glatch": P.hits("glatch", ["gate_latch_3", "gate_latch_1", "gate_latch_2"], 0.45, 0.3, 0.35, n=4),
    }
    if not P.p.get("boot"):
        P.p["boot"] = P.p["rustle"]                                               # no CC0 boot recording: fabric + the heel stomp
    print("one-shot sounds:", n)
    return P


def render(lib, out):
    A, B = Inside(), Outside()
    XF = 0.8                                                                         # dissolve through the doorway
    total = A.dur + B.dur - XF
    P = build_pools(lib)
    M = Mixer(total)

    def camA(t):
        return track(t, A.cam)

    A.sounds(P, M, 0.0, lambda t: camA(t)[1])
    B.sounds(P, M, A.dur - XF, lambda t: B.cam_at(t)[1])
    # ambience: soft birds through the window, louder once the door opens and outside; hens clucking in the yard
    M.bed(load(lib, "birds_2") if os.path.exists(os.path.join(lib, "sounds", "birds_2.mp3")) else None, 0, A.DOOR_OPEN[0], 0.05)
    M.bed(load(lib, "birds_1"), A.DOOR_OPEN[0] - 0.5, total, 0.22, fade=1.5)
    M.bed(load(lib, "chickens_1"), A.dur, total, 0.12, fade=2.0)
    M.bed(load(lib, "wind_leaves_2"), A.dur - 2, total, 0.05, fade=2.0)
    mix = M.buf[:int((total + 0.3) * SR)]
    mix = mix / max(1e-6, np.abs(mix).max()) * 0.9

    yy, xx = np.mgrid[0:H, 0:W]
    vig = (1 - 0.12 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) ** 1.6).clip(0.82, 1)[..., None]
    grain = np.random.default_rng(1).normal(0, 4, (H, W, 1)).astype(np.float32)
    warm = np.array([1.03, 1.0, 0.95], np.float32)
    surf = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)

    def frame(scene, cam, t):
        ctx = cairo.Context(surf)
        z, fx, fy = scene.cam_at(t) if hasattr(scene, "cam_at") else track(t, cam)
        ctx.save()
        ctx.translate(W / 2, H / 2)
        ctx.scale(z, z)
        ctx.translate(-fx, -fy)
        scene.draw(ctx, t)
        ctx.restore()
        surf.flush()
        return np.frombuffer(surf.get_data(), np.uint8).reshape(H, surf.get_stride() // 4, 4)[:, :W, 2::-1].astype(np.float32)

    with tempfile.TemporaryDirectory() as d:
        wav = os.path.join(d, "a.wav")
        sf.write(wav, mix, SR)
        enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                                "-framerate", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-pix_fmt", "yuv420p",
                                "-crf", "21", "-preset", "slow", "-c:a", "aac", "-b:a", "192k", "-shortest", out],
                               stdin=subprocess.PIPE)
        for fi in range(int(total * FPS)):
            T = fi / FPS
            if T < A.dur - XF:
                img = frame(A, A.cam, T)
            elif T < A.dur:
                k = ease((T - (A.dur - XF)) / XF)
                img = frame(A, A.cam, T) * (1 - k) + frame(B, B.cam, T - (A.dur - XF)) * k
            else:
                img = frame(B, B.cam, T - (A.dur - XF))
            img = img * vig * warm + grain
            if T < 0.8:
                img *= ease(T / 0.8)
            if T > total - 1.0:
                img *= ease((total - T) / 1.0)
            enc.stdin.write(np.clip(img, 0, 255).astype(np.uint8).tobytes())
        enc.stdin.close()
        enc.wait()
    print("wrote", out, f"({total:.1f} s), {len(M.log)} placed sounds")


if __name__ == "__main__":
    render(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "homestead_story.mp4")
