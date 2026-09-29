"""Money data reveal: "your little treats vs. your retirement" (1080x1920, ~70 s).

    python money/treats.py out.mp4

A countdown leaderboard: 10 everyday habits, each monthly amount invested at 7%/yr (compounded monthly) for
30 years instead. #1 stays hidden ("???") until the end. Her chibi girl narrates at the bottom in her cloned
voice (lip-synced with Rhubarb), with a face and gesture per line. Sound: whooshes, a "ka-ching" as each number
lands, a drum roll before #1. Amounts are examples (shown on screen); maths is exact.
"""
import io
import math
import os
import subprocess
import sys
import tempfile

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path[:0] = [os.path.join(ROOT, "skits"), os.path.join(ROOT, "chibi")]
import voices                                   # noqa: E402
import chibi_expressions as X                   # noqa: E402
import video_321 as V                           # noqa: E402  (chibi renderer + Rhubarb helpers)
from treats_lines import HOOK, ITEMS, OUTRO, SETUP   # noqa: E402

W, H, FPS, SR = 1080, 1920, 24, voices.SR
RATE, YEARS = 0.07, 30
F800 = os.path.join(ROOT, "skits", "assets", "poppins-800.ttf")
F600 = os.path.join(ROOT, "skits", "assets", "poppins-600.ttf")
INK, GREEN, GOLD, PINK, CREAM = (30, 32, 36), (27, 122, 84), (231, 172, 39), (225, 72, 112), (255, 250, 242)
MUTED = (170, 164, 156)


def fv(monthly):
    r, n = RATE / 12, YEARS * 12
    return monthly * ((1 + r) ** n - 1) / r


def ease(t):
    return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, t)))


def pop(t, d=0.35):
    t = max(0.0, min(1.0, t / d))
    return 1 - (1 - t) ** 3 * math.cos(t * 4.5) if t < 1 else 1.0


_fonts = {}


def font(size, bold=True):
    k = (int(size), bold)
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(F800 if bold else F600, max(4, int(size)))
    return _fonts[k]


def money(v):
    return f"${v / 1000:,.0f}K" if v < 1e6 else f"${v / 1e6:.2f}M"


# ------------------------------------------------------------------ timeline + audio
def build():
    lines = [("hook", HOOK), ("setup", SETUP)] + [(f"item{i}", q) for i, (_, _, q) in enumerate(ITEMS)] + [("outro", OUTRO)]
    t, plan = 0.3, []
    voice = np.zeros(int(120 * SR), np.float32)
    tmp = tempfile.mkdtemp()
    for k, (key, line) in enumerate(lines):
        if key == "item9":
            t += 1.3                                       # drum roll before #1
        a = voices.room(voices.gate(voices.say("her", line)))
        text = line.split("] ", 1)[-1]
        p = os.path.join(tmp, f"{k}.wav")
        sf.write(p, a, SR)
        cues = [(t + s, c) for s, c in V.mouth_cues(p, text)]
        words = text.split()
        lens = np.array([len(w) + 2 for w in words], float)
        dur = len(a) / SR
        starts = t + dur * 0.93 * np.r_[0, np.cumsum(lens)[:-1]] / lens.sum()
        voice[int(t * SR):int(t * SR) + len(a)] += a
        plan.append(dict(key=key, text=text, tone=line[1:line.index("]")], t0=t, t1=t + dur, cues=cues,
                         words=list(zip(words, starts))))
        t += dur + (0.45 if key.startswith("item") else 0.35)
    total = t + 1.8
    voice = voices.clarity(voice[:int(total * SR)])
    fx = np.zeros_like(voice)

    def add(x, at):
        i = int(at * SR)
        fx[i:i + len(x)] += x[:max(0, len(fx) - i)]
    tt = lambda n: np.arange(int(n * SR)) / SR
    rng = np.random.default_rng(5)
    for p in plan:
        if p["key"].startswith("item"):
            n = .45
            s = rng.normal(0, 1, len(tt(n))) * np.sin(np.pi * tt(n) / n) ** 2
            add((np.convolve(s, np.ones(30) / 30, "same") * .25).astype(np.float32), p["t0"] - .2)      # whoosh
            x = tt(.5)                                                                                   # ka-ching
            ching = (np.sin(2 * np.pi * 2093 * x) + .6 * np.sin(2 * np.pi * 2637 * x)) * np.exp(-x / .18) * .14
            ching[:200] += rng.normal(0, .3, 200) * np.exp(-np.arange(200) / 40)
            add(ching.astype(np.float32), count_end(p) + .02)
        if p["key"] == "item9":                                                                          # drum roll
            n = 1.25
            x = tt(n)
            hits = np.zeros(len(x), np.float32)
            k, rate = 0.0, 9.0
            while k < n:
                i = int(k * SR)
                m = min(len(x) - i, 1200)
                hits[i:i + m] += rng.normal(0, 1, m) * np.exp(-np.arange(m) / 250) * (.15 + .25 * k / n)
                rate *= 1.06
                k += 1 / rate
            add(hits, p["t0"] - 1.3)
            boom = np.sin(2 * np.pi * 55 * tt(.9)) * np.exp(-tt(.9) / .3) * .5
            add(boom.astype(np.float32), p["t0"] + 1.6)
    mix = voice + fx
    return plan, mix / max(np.abs(mix).max(), 1e-6) * .95, total


def count_end(p):
    return p["t0"] + min(2.2, (p["t1"] - p["t0"]) * .8)


# ------------------------------------------------------------------ drawing
def background():
    g = np.linspace(0, 1, H)[:, None, None]
    top, bot = np.array((255, 251, 244))[None, None], np.array((243, 232, 214))[None, None]
    im = Image.fromarray((top * (1 - g) + bot * g).repeat(W, 1).astype(np.uint8), "RGB").convert("RGBA")
    d = ImageDraw.Draw(im)
    for y in range(0, H, 60):
        d.line((0, y, W, y), fill=(236, 226, 210), width=1)
    return im


def header(im, t, plan):
    d = ImageDraw.Draw(im)
    hook = plan[0]
    if t < plan[1]["t0"] - .1:                                        # the hook, big
        k = pop(t - hook["t0"])
        d.rounded_rectangle((80, 180, W - 80, 330), 30, fill=INK)
        d.text((W / 2, 255), "You're not broke.", font=font(76 * k + 1), fill=CREAM, anchor="mm")
        k2 = pop(t - (hook["t0"] + 1.3))
        if k2 > .02:
            d.rounded_rectangle((140, 360, W - 140, 480), 28, fill=PINK)
            d.text((W / 2, 420), "you're just generous...", font=font(56 * k2 + 1), fill=CREAM, anchor="mm")
        k3 = pop(t - (hook["t0"] + 2.6))
        if k3 > .02:
            d.text((W / 2, 560), "to DoorDash.", font=font(96 * k3 + 1), fill=INK, anchor="mm")
        return False
    d.rounded_rectangle((60, 70, W - 60, 250), 30, fill=INK)
    d.text((W / 2, 130), "Your \"little treats\"", font=font(62), fill=CREAM, anchor="mm")
    d.text((W / 2, 200), "invested for 30 years instead", font=font(44, False), fill=GOLD, anchor="mm")
    d.text((W / 2, 285), "example monthly amounts  ·  7%/yr avg return  ·  not financial advice", font=font(26, False),
           fill=(120, 112, 100), anchor="mm")
    return True


def leaderboard(im, t, plan):
    """Rows #1 (top) .. #10 (bottom). A row appears when its line starts; its bar grows and the value counts up."""
    d = ImageDraw.Draw(im)
    top, rowh = 330, 86
    vmax = fv(ITEMS[-1][1])
    for rank in range(1, 11):
        i = 10 - rank                                   # ITEMS index (rank 10 first)
        label, monthly, _ = ITEMS[i]
        p = plan[2 + i]
        y = top + (rank - 1) * rowh
        shown = t >= p["t0"] - .15
        cur = shown and t <= p["t1"] + .4
        if cur:
            d.rounded_rectangle((34, y - 6, W - 34, y + rowh - 12), 22, fill=(255, 255, 255), outline=PINK, width=5)
        circ = GOLD if rank == 1 and shown else (GREEN if shown else MUTED)
        d.ellipse((50, y + 8, 110, y + 68), fill=circ)
        d.text((80, y + 38), str(rank), font=font(34), fill=CREAM, anchor="mm")
        if not shown:
            txt = "???"
            if rank == 1:                                   # the big secret: a blurred, shimmering bar
                sh = int(40 + 30 * math.sin(t * 4))
                d.rounded_rectangle((130, y + 44, 130 + 760, y + 70), 12, fill=(220 - sh // 3, 205, 170))
            d.text((130, y + 22), txt, font=font(34), fill=MUTED, anchor="lm")
            continue
        k = ease((t - p["t0"]) / max(count_end(p) - p["t0"], .3))
        val = fv(monthly) * k
        d.text((130, y + 20), label, font=font(32), fill=INK, anchor="lm")
        d.text((W - 60, y + 20), f"${monthly}/mo", font=font(28, False), fill=(120, 112, 100), anchor="rm")
        bw = 760 * fv(monthly) / vmax * k
        col = GOLD if rank == 1 else (GREEN if rank <= 3 else (86, 160, 120))
        if bw > 4:
            d.rounded_rectangle((130, y + 44, 130 + max(bw, 24), y + 72), 12, fill=col)
        tx = 130 + max(bw, 24) + 14
        anchor = "lm"
        if tx > W - 200:
            tx, anchor = 130 + bw - 14, "rm"
        d.text((tx, y + 58), money(val), font=font(30), fill=INK if anchor == "lm" else CREAM, anchor=anchor)


def big_reveal(im, t, p):
    """#1: flash + a huge number card over the chart."""
    k = pop(t - (p["t0"] + 1.3), .4)
    if k <= .02:
        return
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    a = int(255 * min(1, (p["t1"] + .8 - t) / .5)) if t > p["t1"] + .3 else 255
    if a <= 0:
        return
    d.rounded_rectangle((70, 560, W - 70, 1000), 40, fill=GOLD + (a,), outline=INK + (a,), width=8)
    d.text((W / 2, 650), "YOUR CAR PAYMENT", font=font(58 * k + 1), fill=INK + (a,), anchor="mm")
    d.text((W / 2, 790), money(fv(ITEMS[-1][1])), font=font(150 * k + 1), fill=INK + (a,), anchor="mm")
    d.text((W / 2, 925), "\"you're driving a house\"", font=font(46 * k + 1, False), fill=INK + (a,), anchor="mm")
    im.alpha_composite(lay)


def captions(im, p, t):
    said = [i for i, (_, s) in enumerate(p["words"]) if s <= t]
    if not said:
        return
    c0 = said[-1] // 4 * 4
    chunk = p["words"][c0:c0 + 4]
    n = said[-1] - c0 + 1
    f = font(58)
    widths = [f.getlength(w.upper()) for w, _ in chunk]
    total = sum(widths) + 20 * (len(chunk) - 1)
    size = 58 if total < 980 else int(58 * 980 / total)
    f = font(size)
    widths = [f.getlength(w.upper()) for w, _ in chunk]
    total = sum(widths) + 20 * (len(chunk) - 1)
    d = ImageDraw.Draw(im)
    x, y = W / 2 - total / 2, 1250
    for i, ((w, _), wd) in enumerate(zip(chunk, widths)):
        if i < n:
            hot = any(ch.isdigit() for ch in w) or w.strip(".,!?'").lower() in (
                "broke", "doordash", "thousand", "thousand.", "house", "hurt?", "one...", "car")
            d.text((x, y), w.upper(), font=f, fill=PINK if hot else (255, 255, 255), anchor="lm", stroke_width=9,
                   stroke_fill=INK)
        x += wd + 20


POSES = {   # chibi arms: side -> (shoulder, elbow, wrist, hand)
    "hip": {"right": (45, -100, 0, "fist")},
    "point": {"left": (-30, -130, 40, "point")},
    "shrug": {"right": (20, 85, 35, "open"), "left": (-20, -85, -35, "open")},
    "hands_up": {"right": (30, 110, 0, "open"), "left": (-30, -110, 0, "open")},
    "peace": {"left": (-35, -130, 12, "peace")},
    "wave": {"right": (35, 130, -12, "open")},
    "rest": {},
}
FACE_POSE = {"hook": ("smug", "hip"), "setup": ("neutral", "point"), "outro": ("wink", "peace")}
TONE_FACE = {"sassy": ("smug", "hip"), "annoyed": ("eye_roll", "shrug"), "excited": ("excited", "wave"),
             "shocked": ("surprised", "hands_up"), "neutral": ("neutral", "rest")}


CHIBI_KEYS = {"hook": 1, "setup": 1, "item9": 1, "outro": 1}


def running_total(im, t, plan):
    """What skipping every habit revealed so far adds up to (counts up with each reveal)."""
    tot = 0.0
    for i, (_, monthly, _) in enumerate(ITEMS):
        p = plan[2 + i]
        if t >= p["t0"] - .15:
            tot += fv(monthly) * ease((t - p["t0"]) / max(count_end(p) - p["t0"], .3))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((90, 1400, W - 90, 1760), 40, fill=INK)
    d.text((W / 2, 1480), "skip ALL of them =", font=font(48, False), fill=CREAM, anchor="mm")
    d.text((W / 2, 1600), f"${tot:,.0f}", font=font(118), fill=GOLD, anchor="mm")
    d.text((W / 2, 1705), "by retirement", font=font(40, False), fill=(200, 194, 184), anchor="mm")


def chibi_frame(p, t, prev_pose):
    face, pose_name = FACE_POSE.get(p["key"]) or TONE_FACE.get(p["tone"], ("neutral", "rest"))
    if p["key"].startswith("item") and p["tone"] == "sassy" and int(p["key"][4:]) % 2:
        face, pose_name = "eye_roll", "shrug"
    k = ease((t - (p["t0"] - .3)) / .4)
    arms = {}
    for side in ("left", "right"):
        a = POSES[pose_name].get(side, (0, 0, 0, None))
        arms[side] = (a[0] * k, a[1] * k, a[2] * k, a[3] if k > .4 else None)
    ex = X.expression(face)
    m = None
    if p["t0"] <= t <= p["t1"]:
        m = "smile"
        for s, c in p["cues"]:
            if s <= t:
                m = V.RHUBARB_TO_MOUTH[c]
    if m:
        ex["mouth_shape"] = m
    if (t % 3.4) < .1:
        ex["eyes"] = "closed"
    tilt = (4 if face in ("smug", "eye_roll") else 0) * k + 1.2 * math.sin(t * 2.5)
    return V.character_png(ex, arms, tilt, -1.5 * k, height=760)


def render(out):
    plan, audio, total = build()
    bg = background()
    with tempfile.TemporaryDirectory() as d:
        wav = os.path.join(d, "a.wav")
        sf.write(wav, audio, SR)
        for fi in range(int(total * FPS)):
            t = fi / FPS
            p = max((x for x in plan if x["t0"] - .35 <= t), key=lambda x: x["t0"], default=plan[0])
            im = bg.copy()
            if header(im, t, plan):
                leaderboard(im, t, plan)
            if p["key"] == "item9":
                big_reveal(im, t, p)
            show = CHIBI_KEYS.get(p["key"])
            if show:                                                    # she slides up for the big moments only
                k = ease((t - (p["t0"] - .35)) / .35) * (1 - ease((t - (p["t1"] + .15)) / .3)) if p["key"] != "outro" else \
                    ease((t - (p["t0"] - .35)) / .35)
                if k > .01:
                    ch = chibi_frame(p, t, None)
                    im.alpha_composite(ch, ((W - ch.width) // 2, int(H - ch.height + 70 + (1 - k) * 800)))
            else:
                running_total(im, t, plan)
            if p["t0"] - .05 <= t <= p["t1"] + .25:
                captions(im, p, t)
            if t > plan[-1]["t1"] + .2:                               # end card: comment prompt
                dd = ImageDraw.Draw(im)
                k = pop(t - plan[-1]["t1"] - .2)
                dd.rounded_rectangle((120, 1140, W - 120, 1330), 30, fill=PINK)
                dd.text((W / 2, 1200), "Which one hurt?", font=font(64 * k + 1), fill=CREAM, anchor="mm")
                dd.text((W / 2, 1275), "comment your number ↓", font=font(40 * k + 1, False), fill=CREAM, anchor="mm")
            shake = 0
            if plan[11]["t0"] + 1.5 < t < plan[11]["t0"] + 1.9:
                shake = int(12 * math.sin(t * 90))
            frame = im.convert("RGB")
            if shake:
                frame = frame.transform(frame.size, Image.AFFINE, (1, 0, shake, 0, 1, 0), fillcolor=(255, 250, 242))
            frame.save(os.path.join(d, f"f{fi:04d}.png"))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(d, "f%04d.png"),
                        "-i", wav, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "19", "-c:a", "aac", "-b:a", "192k",
                        "-shortest", out], check=True)
    print("wrote", out, f"({total:.1f} s)")


if __name__ == "__main__":
    render(sys.argv[1] if len(sys.argv) > 1 else "treats.mp4")
