"""Talk-to-camera car video: an animated woman in the driver's seat, phone held at chest height (selfie POV),
talking straight to the viewer in short, firm lines. Original script; AI voice (Kokoro "af_sky", a built-in
synthetic voice that belongs to no real person).

Everything is driven by the voice: Kokoro gives the time of every word, so captions pop in word by word,
the mouth opens with the loudness of the voice, and nods, eyebrow raises and hand beats land on the key words.
Natural movement on top: slow blinks (not too sharp), lids lowering a little now and then, small glances,
a gentle head sway, breathing and a handheld-phone drift.

    python3 talk/car_talk.py out.mp4 [ambience_library_dir]
"""
import math
import os
import re
import subprocess
import sys
import tempfile

import cairocffi as cairo
import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "asmr"))
from cozy_morning import FONT, OUT, LW, rgb, ease, lerp, paint, ell, rr, poly, line, lin, _load_font  # noqa: E402

W, H, FPS, SR = 1080, 1920, 30, 24000
VOICE, SPEED = "af_sky", 0.9

TITLE = "Build it anyway!"
# (line, pause after).  *word* = key word: blue in the captions, and she leans into it (nod, brows, hand beat)
SCRIPT = [
    ("*Build* it *anyway*.", 0.6),
    ("Nobody is coming to *approve* your idea.", 0.45),
    ("Stop waiting for the *perfect* time.", 0.4),
    ("The perfect time is a *story* we tell ourselves, so we never have to *start*.", 0.6),
    ("Stop checking who *liked* it and who didn't.", 0.35),
    ("Their opinion doesn't pay your *bills*.", 0.55),
    ("Stop *shrinking* your prices to make other people comfortable.", 0.35),
    ("You are not a *discount*.", 0.65),
    ("Think of your life like a *house* you're building.", 0.35),
    ("You pick the *walls*, the *windows*, and who gets a *key*.", 0.4),
    ("Not everybody gets a key.", 0.65),
    ("Quit carrying last year's *failures* into this year's work.", 0.45),
    ("*Build* it *anyway*.", 0.9),
]
SLOW_CLOSE = {7: "discount", 10: "key", 12: "anyway"}      # sentence -> word where she closes her eyes for a beat
GLANCE = {3: -1, 8: 1}                                     # sentence -> looks off to the side (thinking) as it starts

# hand poses per sentence: (left, right), each (pose, x, y); y > 1950 = resting below the frame
REST_L, REST_R = ("open", 240, 2080), ("open", 860, 2080)
GESTURES = [
    (REST_L, ("open", 700, 1480)),
    (("open", 330, 1450), ("open", 760, 1460)),
    (REST_L, ("flat", 650, 1420)),
    (("open", 380, 1480), ("point", 720, 1430)),
    (REST_L, ("point", 680, 1390)),
    (("flat", 400, 1520), ("flat", 700, 1520)),
    (("flat", 470, 1450), ("flat", 620, 1450)),
    (REST_L, ("chest", 610, 1300)),
    (("open", 330, 1380), ("open", 760, 1380)),
    (("open", 360, 1470), ("point", 700, 1420)),
    (REST_L, ("flat", 660, 1430)),
    (("open", 420, 1480), ("open", 680, 1480)),
    (("open", 380, 1500), ("open", 700, 1500)),
]

COL = dict(skin="#f2c6a2", skin_d="#e0a882", hair="#8e4a2b", hair_hi="#b8693d", hair_d="#6e3520",
           cardigan="#e3a93c", cardigan_d="#c98d24", tee="#fff3dd", belt="#6b6b72", lips="#d0695f",
           iris="#5b3a26", brow="#6e3520", blush="#f59a8f", gold="#e8b84a")


# ------------------------------------------------------------------ voice + word timings
def make_voice(cache):
    """Speak each line with Kokoro; returns (audio, words) where words = [(start, end, text, key, sentence)].
    Cached on disk by script + voice, so re-renders skip the speech step."""
    import hashlib
    import json
    key = hashlib.md5(json.dumps([SCRIPT, VOICE, SPEED]).encode()).hexdigest()[:12]
    path = os.path.join(cache, f"voice_{key}")
    if os.path.exists(path + ".wav"):
        return sf.read(path + ".wav", dtype="float32")[0], [tuple(w) for w in json.load(open(path + ".json"))]
    voice, words = _speak(cache)
    sf.write(path + ".wav", voice, SR)
    json.dump(words, open(path + ".json", "w"))
    return voice, words


def _speak(cache):
    from kokoro import KPipeline
    kp = KPipeline(lang_code="a")
    os.makedirs(cache, exist_ok=True)
    parts, words, t = [], [], 0.25
    parts.append(np.zeros(int(0.25 * SR), np.float32))
    for si, (raw, pause) in enumerate(SCRIPT):
        text = raw.replace("*", "")
        toks = [(w.strip(".,!?"), w.startswith("*") or "*" in w) for w in raw.split()]
        toks = [(w.replace("*", ""), k) for w, k in toks]
        audio, stamps, off = [], [], 0.0
        for r in kp(text, voice=VOICE, speed=SPEED):
            a = r.audio.numpy() if hasattr(r.audio, "numpy") else np.asarray(r.audio)
            stamps += [(off + tk.start_ts, off + tk.end_ts) for tk in r.tokens
                       if tk.start_ts is not None and any(c.isalnum() for c in tk.text)]
            audio.append(a)
            off += len(a) / SR
        a = np.concatenate(audio).astype(np.float32)
        lead = max(0.0, (stamps[0][0] if stamps else 0.0) - 0.04)            # trim Kokoro's lead-in silence
        a = a[int(lead * SR):]
        end = len(a) / SR
        while end > 0.2 and np.abs(a[int((end - 0.05) * SR):int(end * SR)]).max() < 0.01:   # and the tail silence
            end -= 0.05
        a = a[:int((end + 0.05) * SR)]
        if len(stamps) != len(toks):                                         # fall back to spreading by length
            n = sum(len(w) + 2 for w, _ in toks)
            acc, stamps = 0.0, []
            for w, _ in toks:
                d = (len(w) + 2) / n * end
                stamps.append((acc + lead, acc + d + lead))
                acc += d
        for (w, k), (s, e) in zip(toks, stamps):
            words.append((t + s - lead, t + e - lead, w, k, si))
        parts.append(a)
        parts.append(np.zeros(int(pause * SR), np.float32))
        t += len(a) / SR + pause
    return np.concatenate(parts), words


def mouth_track(voice, n):
    """How open the mouth is on each frame (0..1), from the loudness of the voice."""
    hop = SR // FPS
    rms = np.array([np.sqrt(np.mean(voice[i * hop:(i + 1) * hop] ** 2) + 1e-12) for i in range(n)])
    ref = np.percentile(rms[rms > 1e-3], 92) if (rms > 1e-3).any() else 1.0
    raw = np.clip((rms / ref - 0.12) * 1.25, 0, 1)
    out, v = np.zeros(n), 0.0
    for i, x in enumerate(raw):
        v += (x - v) * (0.65 if x > v else 0.4)                               # opens quick, closes softly
        out[i] = v
    return out


# ------------------------------------------------------------------ timing helpers
def pulse(t, t0, dur):
    u = (t - t0) / dur
    return math.sin(math.pi * u) if 0 <= u <= 1 else 0.0


class Motion:
    """All the small, natural movements, worked out ahead of time from the word timings."""

    def __init__(self, words, total):
        rng = np.random.default_rng(7)
        self.words, self.total = words, total
        self.keys = [w for w in words if w[3]]
        self.sent = {}
        for w in words:
            s = self.sent.setdefault(w[4], [w[0], w[1]])
            s[1] = w[1]
        self.slow = [w[0] for w in words if SLOW_CLOSE.get(w[4]) == w[2].lower()]
        if self.slow:                                                          # only the last of a repeated word
            by = {}
            for w in words:
                if SLOW_CLOSE.get(w[4]) == w[2].lower():
                    by[w[4]] = w[0]
            self.slow = list(by.values())
        self.blinks, t = [], 1.2
        while t < total:
            if all(abs(t - s) > 0.9 for s in self.slow):
                self.blinks.append(t)
            t += rng.uniform(2.6, 4.8)
        plain = [w for w in words if not w[3] and len(w[2]) > 3]
        self.lids = [w[0] for w in plain if rng.random() < 0.18]               # a smidge of lid lowering

    def lid(self, t):
        """1 = eyes open, 0 = closed."""
        c = 0.0
        for b in self.blinks:                                                  # blink: 0.08 down, 0.04 hold, 0.11 up
            u = t - b
            if 0 <= u < 0.08:
                c = max(c, ease(u / 0.08))
            elif 0.08 <= u < 0.12:
                c = 1.0
            elif 0.12 <= u < 0.23:
                c = max(c, 1 - ease((u - 0.12) / 0.11))
        for s in self.slow:                                                    # slow, deliberate close on a word
            u = t - s
            if -0.05 <= u < 0.75:
                c = max(c, ease((u + 0.05) / 0.2) if u < 0.15 else 1.0 if u < 0.45 else 1 - ease((u - 0.45) / 0.3))
        low = max([pulse(t, s, 0.6) for s in self.lids], default=0.0) * 0.3
        return max(0.0, 1 - max(c, low))

    def gaze(self, t):
        gx = gy = 0.0
        for si, d in GLANCE.items():
            if si in self.sent:
                p = pulse(t, self.sent[si][0] - 0.2, 1.1)
                gx += d * 9 * min(1, p * 1.6)
                gy -= 5 * min(1, p * 1.6)
        gx += 1.5 * math.sin(t * 0.9) + 1.0 * math.sin(t * 2.3)                 # tiny drift, never dead still
        return gx, gy

    def head(self, t):
        """(dx, dy, tilt deg, brow raise 0..1)"""
        tilt = 2.2 * math.sin(t * 0.55) + 1.2 * math.sin(t * 1.37 + 0.8)
        dx = 7 * math.sin(t * 0.43 + 1.0)
        dy = 4 * math.sin(t * 0.9)
        brow = 0.0
        for i, w in enumerate(self.keys):
            p = pulse(t, w[0] - 0.05, 0.45)
            dy += 11 * p
            tilt += (1.4 if i % 2 else -1.4) * p
            brow = max(brow, pulse(t, w[0] - 0.12, 0.6))
        return dx, dy, tilt, brow

    def beat(self, t):
        return max([pulse(t, w[0] - 0.08, 0.35) for w in self.keys], default=0.0)

    def hands(self, t):
        """((pose, x, y), (pose, x, y)) eased between the gesture of each sentence."""
        cur = 0
        for si, (s0, _) in sorted(self.sent.items()):
            if t >= s0 - 0.35:
                cur = si
        prev = max(0, cur - 1)
        k = ease((t - (self.sent[cur][0] - 0.35)) / 0.4) if cur in self.sent else 1.0
        out = []
        for side in (0, 1):
            a, b = GESTURES[prev][side], GESTURES[cur][side]
            x, y = lerp(a[1], b[1], k), lerp(a[2], b[2], k)
            pose = b[0] if k > 0.5 else a[0]
            if y < 1950:
                y -= 18 * self.beat(t)
                x += (6 if side else -6) * math.sin(t * 1.7 + side)
            if cur == 10 and side == 1:
                x += 22 * math.sin(t * 8) * k                                    # the little "nope" wag
            out.append((pose, x, y))
        return out


# ------------------------------------------------------------------ the car
def rpath(ctx, x, y, w_, h_, r):
    """Rounded-rect path only (for clipping)."""
    r = min(r, w_ / 2, h_ / 2)
    ctx.new_sub_path()
    ctx.arc(x + w_ - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w_ - r, y + h_ - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h_ - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    ctx.close_path()


TREES = [(-40, 640, 120), (90, 560, 90), (40, 760, 140), (1000, 600, 110), (1110, 700, 130), (960, 780, 100),
         (300, 600, 110), (430, 560, 90), (560, 590, 120), (700, 560, 100), (820, 610, 110)]


def car(ctx, t, px, py):
    """The cabin around her. px, py = small parallax shift from the handheld drift."""
    ctx.save()
    ctx.translate(px, py)
    ctx.rectangle(-80, -80, W + 160, H + 160)
    paint(ctx, "#3d3e45", w=0)
    # windows: sky and trees beyond (rear window in the middle, side windows left and right)
    for x0, y0, w_, h_ in ((-80, 380, 250, 700), (190, 470, 700, 330), (910, 380, 250, 700)):
        ctx.save()
        rpath(ctx, x0, y0, w_, h_, 40)
        ctx.clip()
        ctx.rectangle(x0, y0, w_, h_)
        paint(ctx, lin(0, y0, 0, y0 + h_, [(0, "#bfe4f7"), (1, "#e9f5f2")]), w=0)
        for k, (tx, ty, r) in enumerate(TREES):
            sw = 4 * math.sin(t * 1.3 + k)
            ell(ctx, tx + sw, ty, r, r * 0.9, fill="#79b86a" if k % 2 else "#8cc77a", w=0)
            ell(ctx, tx + sw - r * 0.3, ty - r * 0.3, r * 0.45, r * 0.4, fill="#a6d88f", w=0, alpha=0.7)
        ctx.restore()
        rr(ctx, x0, y0, w_, h_, 40, w=8)
    # roof liner + sunroof
    ctx.move_to(-80, -80)
    ctx.line_to(W + 80, -80)
    ctx.line_to(W + 80, 380)
    ctx.curve_to(820, 470, 260, 470, -80, 380)
    ctx.close_path()
    paint(ctx, lin(0, 0, 0, 470, [(0, "#cfc8bd"), (1, "#e3ddd3")]), w=0)
    rr(ctx, 230, 60, 620, 300, 46, fill="#2f3036")
    ctx.save()
    rpath(ctx, 255, 80, 570, 260, 36)
    ctx.clip()
    ctx.rectangle(255, 80, 570, 260)
    paint(ctx, lin(0, 80, 0, 340, [(0, "#a9d7f2"), (1, "#d6eef8")]), w=0)
    for k in range(4):                                                         # branches overhead through the glass
        bx = 300 + k * 150 + 6 * math.sin(t * 0.8 + k)
        line(ctx, [(bx, 70), (bx + 40, 150), (bx + 10, 230)], w=6, col="#7b8f80", alpha=0.6)
        ell(ctx, bx + 40, 150, 70, 40, fill="#9cc79a", w=0, alpha=0.45)
    ctx.move_to(300, 330)                                                      # glass shine
    ctx.line_to(420, 90)
    ctx.line_to(480, 90)
    ctx.line_to(360, 330)
    ctx.close_path()
    paint(ctx, "#ffffff", w=0, alpha=0.25)
    ctx.restore()
    rr(ctx, 255, 80, 570, 260, 36, w=6)
    rr(ctx, 470, 395, 140, 40, 14, fill="#bdb6aa", w=5)                         # dome light
    # pillars between the windows
    for x0 in (150, 880):
        poly(ctx, [(x0, 380), (x0 + 60, 380), (x0 + 50, 1100), (x0 - 10, 1100)], fill="#4a4b53", w=6)
    # seat back + headrest behind her
    rr(ctx, 130, 860, 820, 1300, 120, fill="#2c2d33")
    rr(ctx, 350, 360, 380, 400, 110, fill="#33343b")
    rr(ctx, 520, 760, 18, 120, 6, fill="#9a9aa0", w=4)
    ctx.restore()


# ------------------------------------------------------------------ her
def hand(ctx, x, y, pose, side):
    """A hand with the palm toward the camera. side: -1 her right (screen left), 1 screen right."""
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(math.radians(-12 * side if pose != "chest" else 70 * side))
    ctx.scale(1.45, 1.45)
    spread = {"open": 0.22, "flat": 0.05, "point": 0.0, "chest": 0.04}[pose]
    fingers = [(-30, 64), (-10, 76), (12, 72), (32, 58)]                    # base x, length
    for i, (bx, ln) in enumerate(fingers):
        if pose == "point" and i != (1 if side > 0 else 2):
            ln = 26                                                            # curled
        a = (i - 1.5) * spread
        ex, ey = bx + math.sin(a) * ln, -40 - math.cos(a) * ln
        line(ctx, [(bx, -30), (ex, ey)], w=34)
        line(ctx, [(bx, -30), (ex, ey)], w=22, col=COL["skin"])
        ell(ctx, ex, ey + 4, 6, 8, fill="#f7d6d6", w=0)                         # nail
    tx = -side * 46                                                            # thumb
    line(ctx, [(tx * 0.6, 10), (tx * 1.15, -30)], w=36)
    line(ctx, [(tx * 0.6, 10), (tx * 1.15, -30)], w=24, col=COL["skin"])
    ell(ctx, 0, 0, 48, 52, fill=COL["skin"])
    line(ctx, [(-20, 10), (18, -4)], w=3, col=COL["skin_d"])
    ctx.restore()


def forearm(ctx, ex, ey, hx, hy, pose, side):
    wx, wy = hx - side * 8, hy + 90
    line(ctx, [(ex, ey), (wx, wy)], w=130)
    line(ctx, [(ex, ey), (wx, wy)], w=116, col=COL["cardigan"])
    for k in (0.55, 0.75):                                                     # knit ribs
        mx, my = lerp(ex, wx, k), lerp(ey, wy, k)
        line(ctx, [(mx - 40, my + 6), (mx + 40, my - 6)], w=4, col=COL["cardigan_d"])
    ell(ctx, wx, wy, 60, 30, fill=COL["cardigan_d"])                            # cuff
    hand(ctx, hx, hy, pose, side)


def woman(ctx, t, mo, mouth_open, cam):
    hdx, hdy, tilt, brow = mo.head(t)
    breathe = 3 * math.sin(t * 1.6)
    bx = 540 + hdx * 0.35
    by = 1060 + breathe
    hx0, hy0 = 540 + hdx, 700 + hdy * 0.6 + breathe * 0.5                     # head centre
    pivot = (540 + hdx, 960 + breathe)

    def head_space():
        ctx.translate(*pivot)
        ctx.rotate(math.radians(tilt))
        ctx.translate(hx0 - pivot[0], hy0 - pivot[1] + hdy * 0.4)

    # back hair (long, past the shoulders)
    ctx.save()
    head_space()
    ctx.move_to(0, -250)
    ctx.curve_to(170, -255, 245, -150, 240, 20)
    ctx.curve_to(240, 220, 280, 400, 300, 560)
    ctx.curve_to(220, 600, 120, 580, 60, 540)
    ctx.line_to(-60, 540)
    ctx.curve_to(-120, 580, -220, 600, -300, 560)
    ctx.curve_to(-280, 400, -240, 220, -240, 20)
    ctx.curve_to(-245, -150, -170, -255, 0, -250)
    ctx.close_path()
    paint(ctx, COL["hair_d"])
    ctx.restore()
    # neck
    rr(ctx, 480 + hdx * 0.7, 870 + hdy * 0.3, 120, 220, 40, fill=COL["skin"])
    ell(ctx, 540 + hdx * 0.7, 900 + hdy * 0.3, 58, 22, fill=COL["skin_d"], w=0, alpha=0.5)
    # body: cream tee under a mustard cardigan
    ctx.move_to(bx - 470, H + 60)
    ctx.curve_to(bx - 460, by + 120, bx - 400, by + 10, bx - 200, by - 20)
    ctx.curve_to(bx - 120, by - 40, bx - 70, by - 70, bx - 60, by - 60)
    ctx.line_to(bx + 60, by - 60)
    ctx.curve_to(bx + 70, by - 70, bx + 120, by - 40, bx + 200, by - 20)
    ctx.curve_to(bx + 400, by + 10, bx + 460, by + 120, bx + 470, H + 60)
    ctx.close_path()
    paint(ctx, COL["cardigan"])
    ctx.move_to(bx - 110, by - 50)
    ctx.curve_to(bx - 60, by + 200, bx - 150, by + 600, bx - 160, H + 60)
    ctx.line_to(bx + 160, H + 60)
    ctx.curve_to(bx + 150, by + 600, bx + 60, by + 200, bx + 110, by - 50)
    ctx.curve_to(bx + 50, by + 10, bx - 50, by + 10, bx - 110, by - 50)
    ctx.close_path()
    paint(ctx, COL["tee"])
    for k in range(5):                                                         # cardigan buttons
        ell(ctx, bx - 150 - k * 4, by + 260 + k * 150, 13, 13, fill="#f7e3b5", w=4)
    for sg in (-1, 1):                                                         # knit ribbing down the fronts
        for k in range(6):
            yy = by + 120 + k * 120
            line(ctx, [(bx + sg * (250 + k * 12), yy), (bx + sg * (290 + k * 12), yy + 30)], w=4, col=COL["cardigan_d"])
    # seat belt over her shoulder
    ctx.move_to(bx + 300, by - 40)
    ctx.line_to(bx + 380, by - 10)
    ctx.line_to(bx - 160, H + 80)
    ctx.line_to(bx - 270, H + 80)
    ctx.close_path()
    paint(ctx, COL["belt"])
    for off in (14, 96):
        line(ctx, [(bx + 300 + off * 0.8, by - 40 + off * 0.3), (bx - 270 + off, H + 80)], w=2, col="#8a8a92")

    # head
    ctx.save()
    head_space()
    ell(ctx, 0, 0, 188, 232, fill=COL["skin"])
    for sg in (-1, 1):                                                         # hoops peeking out under the hair
        ctx.arc(sg * 182, 92, 20, 0, math.pi * 2)
        ctx.set_source_rgb(*rgb(COL["gold"]))
        ctx.set_line_width(5)
        ctx.stroke()
    ell(ctx, -112, 72, 40, 22, fill=COL["blush"], w=0, alpha=0.45)
    ell(ctx, 112, 72, 40, 22, fill=COL["blush"], w=0, alpha=0.45)
    # eyes
    lid = mo.lid(t)
    gx, gy = mo.gaze(t)
    for sg in (-1, 1):
        ex, ey = sg * 80, -8
        ctx.save()
        ctx.translate(ex, ey)

        def almond():
            ctx.move_to(-42, 4)
            ctx.curve_to(-26, -26, 26, -28, 44, -2)
            ctx.curve_to(26, 24, -24, 26, -42, 4)
            ctx.close_path()
        almond()
        ctx.save()
        ctx.clip()
        almond()
        paint(ctx, "#ffffff", w=0)
        ell(ctx, gx, gy + 1, 21, 22, fill=COL["iris"], w=0)
        ell(ctx, gx, gy + 1, 10, 11, fill="#2a1a10", w=0)
        ell(ctx, gx + 7, gy - 7, 6, 6, fill="#ffffff", w=0)
        top, bot = -28, 26                                                      # upper lid comes down over the eye
        ly = lerp(bot - 4, top, lid)
        ctx.rectangle(-60, -60, 120, ly + 60)
        paint(ctx, COL["skin"], w=0)
        ctx.restore()
        if lid > 0.15:
            almond()
            paint(ctx, None, w=4)
            ctx.move_to(-44, max(ly + 4, 2))                                   # lash line follows the lid
            ctx.curve_to(-20, ly - 10, 20, ly - 10, 46, max(ly, -2))
            ctx.set_source_rgb(*OUT)
            ctx.set_line_width(7)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.stroke()
        else:                                                                   # closed: a soft lash curve
            ctx.move_to(-42, 6)
            ctx.curve_to(-16, 20, 16, 20, 44, 4)
            ctx.set_source_rgb(*OUT)
            ctx.set_line_width(7)
            ctx.stroke()
        lx = 44 if sg > 0 else -42                                             # outer lashes
        lyy = (max(ly, -2) if lid > 0.15 else 4)
        line(ctx, [(lx, lyy), (lx + sg * 14, lyy - 10)], w=5)
        line(ctx, [(lx - sg * 8, lyy - 4), (lx + sg * 2, lyy - 16)], w=4)
        ctx.restore()
        # crease + brow
        ctx.move_to(ex - 36, ey - 34 + (1 - lid) * 6)
        ctx.curve_to(ex - 14, ey - 46, ex + 16, ey - 46, ex + 38, ey - 34)
        ctx.set_source_rgba(*rgb(COL["skin_d"]), 0.9)
        ctx.set_line_width(4)
        ctx.stroke()
        bry = ey - 70 - 14 * brow
        ctx.move_to(ex - sg * 40, bry + 10)
        ctx.curve_to(ex - sg * 14, bry - 8, ex + sg * 20, bry - 10, ex + sg * 46, bry + 4 - 4 * brow)
        ctx.set_source_rgb(*rgb(COL["brow"]))
        ctx.set_line_width(13)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.stroke()
    # nose
    ctx.move_to(-4, 22)
    ctx.curve_to(-10, 46, -14, 54, -2, 58)
    ctx.set_source_rgb(*rgb(COL["skin_d"]))
    ctx.set_line_width(5)
    ctx.stroke()
    # mouth
    a = mouth_open
    my = 112
    wdt = 38 - 6 * a
    if a < 0.07:
        ctx.move_to(-wdt, my)
        ctx.curve_to(-14, my + 8, 14, my + 8, wdt, my - 2)
        ctx.set_source_rgb(*rgb("#b0504a"))
        ctx.set_line_width(7)
        ctx.stroke()
        ctx.move_to(-wdt + 8, my + 6)
        ctx.curve_to(-8, my + 20, 8, my + 20, wdt - 8, my + 4)
        ctx.set_source_rgba(*rgb(COL["lips"]), 0.6)
        ctx.set_line_width(6)
        ctx.stroke()
    else:
        up, dn = my - 4 - 6 * a, my + 6 + 42 * a
        ctx.move_to(-wdt, my)
        ctx.curve_to(-wdt * 0.5, up - 4, wdt * 0.5, up - 4, wdt, my)
        ctx.curve_to(wdt * 0.6, dn, -wdt * 0.6, dn, -wdt, my)
        ctx.close_path()
        paint(ctx, "#6e2a2a", w=0)
        if a > 0.3:                                                            # top teeth
            ctx.save()
            ctx.move_to(-wdt, my)
            ctx.curve_to(-wdt * 0.5, up - 4, wdt * 0.5, up - 4, wdt, my)
            ctx.curve_to(wdt * 0.6, dn, -wdt * 0.6, dn, -wdt, my)
            ctx.clip()
            rr(ctx, -wdt, up - 8, wdt * 2, 8 + 10 * a, 4, fill="#ffffff", w=0)
            ell(ctx, 0, dn - 6, wdt * 0.5, 9 * a, fill="#d9706c", w=0)            # tongue
            ctx.restore()
        ctx.move_to(-wdt, my)
        ctx.curve_to(-wdt * 0.5, up - 4, wdt * 0.5, up - 4, wdt, my)
        ctx.curve_to(wdt * 0.6, dn, -wdt * 0.6, dn, -wdt, my)
        ctx.close_path()
        paint(ctx, None, w=7, line=rgb(COL["lips"]))
    # front hair: middle part, long side pieces framing the face
    for sg in (-1, 1):
        ctx.move_to(sg * 6, -238)
        ctx.curve_to(sg * 150, -240, sg * 220, -140, sg * 214, 20)
        ctx.curve_to(sg * 210, 160, sg * 236, 300, sg * 262, 430)
        ctx.curve_to(sg * 220, 450, sg * 190, 420, sg * 176, 380)
        ctx.curve_to(sg * 170, 250, sg * 176, 120, sg * 160, 10)
        ctx.curve_to(sg * 140, -110, sg * 80, -190, sg * 6, -206)
        ctx.close_path()
        paint(ctx, COL["hair"])
        for k in range(3):                                                     # strand lines
            ctx.move_to(sg * (60 + k * 40), -215 + k * 8)
            ctx.curve_to(sg * (150 + k * 20), -170, sg * (196 + k * 8), -40, sg * (196 + k * 10), 120 + k * 60)
            ctx.set_source_rgb(*rgb(COL["hair_hi"]))
            ctx.set_line_width(4)
            ctx.stroke()
    ctx.restore()
    # arms + hands, in front of everything
    for side, (pose, x, y) in zip((-1, 1), mo.hands(t)):
        if y < 1960:
            forearm(ctx, 540 + side * 560, 2300, x, y, pose, side)


# ------------------------------------------------------------------ captions
_face = None


def text_run(ctx, parts, y, size):
    """parts = [(word, blue?)], centered on y, white (or blue) with a thick dark outline."""
    global _face
    if _face is None:
        _face = _load_font(FONT)
    ctx.save()
    ctx.set_font_face(_face)
    ctx.set_font_size(size)
    sp = size * 0.28
    widths = [ctx.text_extents(w)[2] for w, _ in parts]
    total = sum(widths) + sp * (len(parts) - 1)
    if total > W - 80:
        ctx.restore()
        return text_run(ctx, parts, y, size * (W - 80) / total)
    x = W / 2 - total / 2
    for (w, blue), wd in zip(parts, widths):
        xb, yb, _, th, _, _ = ctx.text_extents(w)
        ctx.move_to(x - xb, y - yb - th / 2)
        ctx.text_path(w)
        ctx.set_source_rgb(0.08, 0.06, 0.06)
        ctx.set_line_width(size * 0.2)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.stroke_preserve()
        ctx.set_source_rgb(*(rgb("#7fd6f7") if blue else (1, 1, 1)))
        ctx.fill()
        x += wd + sp
    ctx.restore()


def chunks(words):
    """Group words into 1-3 word caption chunks, breaking at the end of each line."""
    out, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) == 3 or sum(len(x[2]) for x in cur) > 13 or w is words[-1] or words[words.index(w) + 1][4] != w[4]:
            out.append(cur)
            cur = []
    return out


def captions(ctx, t, groups):
    ttl = ease(t / 0.25)
    if ttl > 0:
        ctx.save()
        ctx.translate(W / 2, 250)
        ctx.scale(lerp(0.85, 1.0, ttl), lerp(0.85, 1.0, ttl))
        ctx.translate(-W / 2, -250)
        text_run(ctx, [(TITLE, False)], 250, 96)
        ctx.restore()
    for i, g in enumerate(groups):
        t0 = g[0][0] - 0.04
        t1 = groups[i + 1][0][0] - 0.04 if i + 1 < len(groups) else g[-1][1] + 0.8
        if g[-1][4] != (groups[i + 1][0][4] if i + 1 < len(groups) else -1):
            t1 = min(t1, g[-1][1] + 0.45)                                       # clears in the pause between lines
        if t0 <= t < t1:
            k = ease((t - t0) / 0.1)
            ctx.save()
            ctx.translate(W / 2, 1210)
            ctx.scale(lerp(0.8, 1.0, k), lerp(0.8, 1.0, k))
            ctx.translate(-W / 2, -1210)
            text_run(ctx, [(w[2].upper(), w[3]) for w in g], 1210, 104)
            ctx.restore()


# ------------------------------------------------------------------ sound bed
def ambience(n, lib):
    """Quiet car cabin: a low hum, plus birds outside, muffled through the glass."""
    from scipy.signal import butter, sosfilt
    rng = np.random.default_rng(3)
    hum = np.cumsum(rng.normal(0, 1, n)).astype(np.float32)
    hum = sosfilt(butter(2, [30, 220], "bandpass", fs=SR, output="sos"), hum - np.convolve(hum, np.ones(2400) / 2400, "same"))
    hum = hum / (np.abs(hum).max() + 1e-9) * 0.012
    bed = hum.astype(np.float32)
    path = os.path.join(lib or "", "sounds", "birds_1.mp3")
    if lib and os.path.exists(path):
        import librosa
        b, _ = librosa.load(path, sr=SR, mono=True)
        b = np.tile(b, n // len(b) + 1)[:n]
        b = sosfilt(butter(2, 1800, "lowpass", fs=SR, output="sos"), b)
        bed += (b / (np.abs(b).max() + 1e-9) * 0.03).astype(np.float32)
    return bed


# ------------------------------------------------------------------ render
def render(out, lib=None):
    voice, words = make_voice(os.path.join(HERE, ".cache"))
    total = len(voice) / SR + 0.3
    n = int(total * FPS)
    voice = np.concatenate([voice, np.zeros(int(0.3 * SR) + SR, np.float32)])
    mouth = mouth_track(voice, n)
    mix = voice[:int(total * SR)] / max(1e-6, np.abs(voice).max()) * 0.85
    mix = mix + ambience(len(mix), lib)
    mo = Motion(words, total)
    groups = chunks(words)

    yy, xx = np.mgrid[0:H, 0:W]
    vig = (1 - 0.14 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) ** 1.6).clip(0.8, 1)[..., None]
    grain = np.random.default_rng(1).normal(0, 3.5, (H, W, 1)).astype(np.float32)
    warm = np.array([1.03, 1.0, 0.96], np.float32)
    surf = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)

    def frame(fi):
        t = fi / FPS
        ctx = cairo.Context(surf)
        cdx = 5 * math.sin(t * 0.8) + 2 * math.sin(t * 2.3)                    # handheld phone drift
        cdy = 4 * math.sin(t * 0.6 + 2) + 2 * math.sin(t * 1.9)
        rot = 0.35 * math.sin(t * 0.5) + 0.15 * math.sin(t * 1.7)
        ctx.save()
        ctx.translate(W / 2 + cdx, H / 2 + cdy)
        ctx.rotate(math.radians(rot))
        ctx.scale(1.04, 1.04)
        ctx.translate(-W / 2, -H / 2)
        car(ctx, t, -cdx * 0.3, -cdy * 0.3)
        woman(ctx, t, mo, mouth[min(fi, n - 1)], (cdx, cdy))
        ctx.restore()
        captions(ctx, t, groups)
        surf.flush()
        return np.frombuffer(surf.get_data(), np.uint8).reshape(H, surf.get_stride() // 4, 4)[:, :W, 2::-1].astype(np.float32)

    if os.environ.get("STILLS"):
        from PIL import Image
        for s in os.environ["STILLS"].split(","):
            Image.fromarray(np.clip(frame(int(float(s) * FPS)) * vig * warm, 0, 255).astype(np.uint8)).save(f"{out}_{s}.png")
        return

    with tempfile.TemporaryDirectory() as d:
        wav = os.path.join(d, "a.wav")
        sf.write(wav, mix.astype(np.float32), SR)
        enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                                "-framerate", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-pix_fmt", "yuv420p",
                                "-crf", "23", "-preset", "slow", "-c:a", "aac", "-b:a", "192k", "-shortest", out],
                               stdin=subprocess.PIPE)
        for fi in range(n):
            img = frame(fi) * vig * warm + grain
            if fi / FPS > total - 0.35:
                img *= ease((total - fi / FPS) / 0.35)
            enc.stdin.write(np.clip(img, 0, 255).astype(np.uint8).tobytes())
        enc.stdin.close()
        enc.wait()
    print("wrote", out, f"({total:.1f} s, {len(words)} words)")


if __name__ == "__main__":
    render(sys.argv[1] if len(sys.argv) > 1 else "car_talk.mp4", sys.argv[2] if len(sys.argv) > 2 else None)
