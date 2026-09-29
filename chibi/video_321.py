"""TikTok video (1080x1920): she explains the 3-2-1 rule for weight loss in the cloned voice, lip-synced, with an
expression and a gesture per line, word-by-word captions and animated graphics (emoji, cards, a streak chart).

    python chibi/video_321.py out.mp4

Needs: ffmpeg; chatterbox-tts (voice clone, CPU is fine); Rhubarb Lip Sync (RHUBARB env var or on PATH);
the voice sample demo_videos/voices/narrator-ref.wav (private, not in the repo); a Poppins TTF (FONT_DIR);
Twemoji SVGs (downloaded once into chibi/.cache; Twemoji by Twitter, CC-BY 4.0).
"""
import hashlib
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request

import cairosvg
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont

import chibi_expressions as X
import chibi_hair as CH

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, ".cache")
VOICE_REF = os.path.join(HERE, "..", "demo_videos", "voices", "narrator-ref.wav")
FONT_DIR = os.environ.get("FONT_DIR", CACHE)
RHUBARB = os.environ.get("RHUBARB", shutil.which("rhubarb") or "rhubarb")
W, H, FPS, SR = 1080, 1920, 24, 24000
GAP = 0.35                                  # silence between lines (s)
PINK_TOP, PINK_BOT = (255, 232, 238), (255, 205, 220)
ACCENT, INK = (233, 61, 120), (45, 20, 30)

# line, expression, arms (shoulder, elbow, wrist, hand per side), head tilt, graphic, highlighted words
BEATS = [
    ("Stop starving yourself to lose weight.", "angry", {"right": (30, 130, -40, "point")}, 3, "stop", {"stop", "starving"}),
    ("Try the three, two, one rule instead.", "happy", {"left": (-25, -110, -50, "thumbs_up")}, -3, "title", {"three,", "two,", "one"}),
    ("Three. Eat protein at every meal. It keeps you full.", "smug", {"right": (45, -100, 0, "fist")}, -5, "protein", {"protein", "full."}),
    ("Two. Drink two big bottles of water a day.", "happy", {"left": (-35, -130, 12, "peace")}, -5, "water", {"two", "water"}),
    ("One. Walk thirty minutes, every single day.", "excited", {"right": (30, 130, -40, "point")}, 3, "walk", {"walk", "thirty"}),
    ("Small habits. Big results. Follow for more!", "wink", {"right": (35, 130, -12, "open")}, 4, "streak", {"big", "results.", "follow"}),
]
EMOJI = {"stop": "1f6ab", "plate": "1f37d", "meat": "1f357", "egg": "1f95a", "drop": "1f4a7", "shoe": "1f45f",
         "fire": "1f525", "check": "2705", "spark": "2728", "muscle": "1f4aa"}


# ------------------------------------------------------------------ voice + lip sync
def spoken(text):
    from num2words import num2words
    return re.sub(r"\d+", lambda m: num2words(int(m.group())), text)


_tts = None


def voice(text):
    """The line in the cloned voice (Chatterbox), cached on disk."""
    global _tts
    os.makedirs(CACHE, exist_ok=True)
    key = hashlib.md5(f"{text}|{os.path.getsize(VOICE_REF)}".encode()).hexdigest()
    path = os.path.join(CACHE, f"voice_{key}.wav")
    if not os.path.exists(path):
        if _tts is None:
            import torch
            from chatterbox.tts import ChatterboxTTS
            _tts = ChatterboxTTS.from_pretrained(device="cuda" if torch.cuda.is_available() else "cpu")
        import torchaudio
        w = _tts.generate(spoken(text), audio_prompt_path=VOICE_REF, exaggeration=0.6, cfg_weight=0.5)
        w = torchaudio.functional.resample(w, _tts.sr, SR).squeeze(0).numpy().astype(np.float32)
        nz = np.where(np.abs(w) > 0.01)[0]
        w = w[max(nz[0] - 200, 0):nz[-1] + 1200] if len(nz) else w
        sf.write(path, w, SR)
    return sf.read(path, dtype="float32")[0]


def mouth_cues(wav_path, text):
    """Rhubarb mouth shapes (A-H, X) with start times."""
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
        fh.write(text)
    out = subprocess.run([RHUBARB, "-f", "json", "-d", fh.name, "--machineReadable", wav_path, "-q"],
                         capture_output=True, text=True, check=True).stdout
    return [(c["start"], c["value"]) for c in json.loads(out)["mouthCues"]]


RHUBARB_TO_MOUTH = {"X": "smile", "A": "smile", "B": "open", "C": "open", "D": "wide", "E": "oh", "F": "oh",
                    "G": "open", "H": "open"}


# ------------------------------------------------------------------ assets
def font(size, weight=800):
    return ImageFont.truetype(os.path.join(FONT_DIR, f"poppins-{weight}.ttf"), size)


_emoji = {}


def emoji(name, size):
    key = (name, size)
    if key not in _emoji:
        code = EMOJI[name]
        path = os.path.join(CACHE, "emoji", code + ".svg")
        if not os.path.exists(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            urllib.request.urlretrieve(f"https://cdn.jsdelivr.net/gh/jdecked/twemoji@15.1.0/assets/svg/{code}.svg", path)
        png = cairosvg.svg2png(url=path, output_width=size, output_height=size)
        _emoji[key] = Image.open(io.BytesIO(png)).convert("RGBA")
    return _emoji[key]


# ------------------------------------------------------------------ motion helpers
def ease(t):
    return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, t)))


def pop(t, d=0.35):
    """0 -> 1 with a little overshoot (for things popping in)."""
    t = max(0.0, min(1.0, t / d))
    return 1 - (1 - t) ** 3 * math.cos(t * 4.5) if t < 1 else 1.0


def paste(canvas, im, cx, cy, scale=1.0, alpha=1.0):
    if scale <= 0.01 or alpha <= 0.01:
        return
    if scale != 1.0:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS)
    if alpha < 1:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    canvas.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


def card(canvas, box, radius=46, fill=(255, 255, 255, 235), outline=ACCENT, width=6):
    ImageDraw.Draw(canvas).rounded_rectangle(box, radius, fill=fill, outline=outline, width=width)


def text_c(canvas, xy, s, size, fill=INK, weight=800, stroke=0, stroke_fill=(255, 255, 255)):
    d = ImageDraw.Draw(canvas)
    f = font(size, weight)
    d.text(xy, s, font=f, fill=fill, anchor="mm", stroke_width=stroke, stroke_fill=stroke_fill)


# ------------------------------------------------------------------ graphics per beat (top area, y 130-760)
def graphic(canvas, kind, t, dur):
    k = pop(t)
    cx, cy = W // 2, 430
    if kind == "stop":
        paste(canvas, emoji("stop", 300), cx, cy - 20, k)
        text_c(canvas, (cx, cy + 210), "STOP STARVING", int(92 * max(k, .01)), fill=ACCENT, stroke=8)
    elif kind == "title":
        for i, n in enumerate("321"):
            ki = pop(t - 0.25 * i)
            x = cx + (i - 1) * 250
            card(canvas, (x - 105, cy - 150, x + 105, cy + 60), fill=(255, 255, 255, int(235 * min(ki, 1))))
            if ki > .05:
                text_c(canvas, (x, cy - 45), n, int(190 * ki), fill=ACCENT)
        text_c(canvas, (cx, cy + 150), "RULE", int(110 * pop(t - .7)), fill=INK, stroke=8)
        for i, (sx, sy) in enumerate(((cx - 380, cy - 190), (cx + 390, cy - 150), (cx + 330, cy + 150))):
            s = 0.8 + 0.2 * math.sin(t * 6 + i)
            paste(canvas, emoji("spark", 90), sx, sy, pop(t - .5 - .15 * i) * s)
    elif kind == "protein":
        card(canvas, (90, 150, W - 90, 740))
        text_c(canvas, (cx, 245), "3  PROTEIN", 88, fill=ACCENT)
        text_c(canvas, (cx, 330), "at every meal", 54, fill=INK, weight=600)
        for i, name in enumerate(("Breakfast", "Lunch", "Dinner")):
            ki = pop(t - 0.9 - 0.45 * i)
            y = 440 + i * 100
            paste(canvas, emoji("meat" if i != 0 else "egg", 80), 230, y, ki)
            if ki > .05:
                ImageDraw.Draw(canvas).text((300, y), name, font=font(58, 600), fill=INK, anchor="lm")
            paste(canvas, emoji("check", 76), W - 230, y, pop(t - 1.3 - 0.45 * i))
    elif kind == "water":
        card(canvas, (90, 150, W - 90, 740))
        text_c(canvas, (cx, 245), "2  BOTTLES", 88, fill=ACCENT)
        text_c(canvas, (cx, 330), "of water a day", 54, fill=INK, weight=600)
        d = ImageDraw.Draw(canvas)
        for i in range(2):
            x = cx + (i - .5) * 300
            fill = ease((t - 0.8 - 0.7 * i) / 1.2)
            top, bot = 400, 700
            d.rounded_rectangle((x - 70, top, x + 70, bot), 36, outline=(90, 160, 220), width=8, fill=(240, 248, 255))
            d.rectangle((x - 28, top - 34, x + 28, top), fill=(90, 160, 220))
            level = bot - 10 - fill * (bot - top - 30)
            if fill > 0:
                d.rounded_rectangle((x - 60, level, x + 60, bot - 10), 28, fill=(120, 190, 245))
            paste(canvas, emoji("drop", 80), x, top - 90, pop(t - 1.7 - .7 * i))
    elif kind == "walk":
        card(canvas, (90, 150, W - 90, 740))
        text_c(canvas, (cx, 245), "1  WALK", 88, fill=ACCENT)
        d = ImageDraw.Draw(canvas)
        p = ease((t - 0.5) / max(dur - 1.0, 0.5))
        r = 190
        d.ellipse((cx - r, 520 - r + 30, cx + r, 520 + r + 30), outline=(245, 215, 225), width=34)
        d.arc((cx - r, 520 - r + 30, cx + r, 520 + r + 30), -90, -90 + 360 * p, fill=ACCENT, width=34)
        mins = int(round(30 * p))
        text_c(canvas, (cx, 520), f"{mins}:00", 96, fill=INK)
        text_c(canvas, (cx, 610), "min / day", 44, fill=INK, weight=600)
        paste(canvas, emoji("shoe", 110), cx + 250 + 12 * math.sin(t * 9), 370 + 6 * abs(math.sin(t * 9)), pop(t - .3))
    elif kind == "streak":
        card(canvas, (90, 150, W - 90, 740))
        text_c(canvas, (cx, 240), "SMALL HABITS", 78, fill=INK)
        text_c(canvas, (cx, 320), "BIG RESULTS", 78, fill=ACCENT)
        d = ImageDraw.Draw(canvas)
        for i in range(7):
            ki = ease((t - 0.6 - 0.18 * i) / 0.4)
            h = (90 + 35 * i) * ki
            x = 200 + i * 113
            d.rounded_rectangle((x - 38, 690 - h, x + 38, 690), 16, fill=ACCENT if i == 6 else (247, 160, 190))
            d.text((x, 715), "MTWTFSS"[i], font=font(34, 600), fill=INK, anchor="mm")
        paste(canvas, emoji("fire", 110), 200 + 6 * 113, 690 - 300 - 70, pop(t - 1.9))


def captions(canvas, words, t, hot):
    """Word-by-word captions: the words said so far in the current line, 3-4 per row, key words in the accent colour."""
    shown = [(w, st) for w, st in words if st <= t]
    if not shown:
        return
    rows, row = [], []
    for w, _ in shown[-8:]:
        row.append(w)
        if len(row) == 4:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows = rows[-2:]
    f = font(78)
    for ri, r in enumerate(rows):
        y = 850 + ri * 100
        widths = [f.getlength(w + " ") for w in r]
        x = W / 2 - sum(widths) / 2
        for w, wd in zip(r, widths):
            col = ACCENT if w.lower() in hot else (255, 255, 255)
            ImageDraw.Draw(canvas).text((x, y), w.upper(), font=f, fill=col, anchor="lm", stroke_width=9,
                                        stroke_fill=INK)
            x += wd


# ------------------------------------------------------------------ character
def character_png(expr, pose, tilt, bob, height=1060):
    vx, vy, vw, vh = -40, 150, 450, 860
    inner = CH.head_svg_v2(**expr, pose=pose, tilt=tilt)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{int(vw * height / vh)}" height="{height}" '
           f'viewBox="{vx} {vy} {vw} {vh}"><defs>{CH.DEFS}</defs>'
           f'<g transform="translate(0,{bob:.2f})">{inner}</g></svg>')
    return Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode()))).convert("RGBA")


def background():
    g = np.linspace(0, 1, H)[:, None, None]
    top, bot = np.array(PINK_TOP)[None, None], np.array(PINK_BOT)[None, None]
    arr = (top * (1 - g) + bot * g).repeat(W, 1).astype(np.uint8)
    im = Image.fromarray(arr, "RGB").convert("RGBA")
    d = ImageDraw.Draw(im)
    d.ellipse((W / 2 - 360, 1850, W / 2 + 360, 1930), fill=(240, 170, 195, 255))       # floor shadow
    return im


# ------------------------------------------------------------------ build
def plan():
    """Voice per line, laid out one after another; per line: start, end, mouth cues and word start times."""
    t, beats, audio = 0.5, [], [np.zeros(int(0.5 * SR), np.float32)]
    tmp = tempfile.mkdtemp()
    for i, (line, expr, arms, tilt, kind, hot) in enumerate(BEATS):
        a = voice(line)
        p = os.path.join(tmp, f"l{i}.wav")
        sf.write(p, a, SR)
        cues = [(t + s, v) for s, v in mouth_cues(p, spoken(line))]
        dur = len(a) / SR
        words = line.split()
        lens = np.array([len(w) + 2 for w in words], float)
        starts = t + dur * 0.92 * np.r_[0, np.cumsum(lens)[:-1]] / lens.sum()
        beats.append(dict(t0=t, t1=t + dur, line=line, expr=expr, arms=arms, tilt=tilt, kind=kind, hot=hot,
                          cues=cues, words=list(zip(words, starts))))
        audio += [a, np.zeros(int(GAP * SR), np.float32)]
        t += dur + GAP
    audio.append(np.zeros(int(0.8 * SR), np.float32))
    return beats, np.concatenate(audio), t + 0.8


def state(beats, t):
    b = max((x for x in beats if x["t0"] - GAP <= t), key=lambda x: x["t0"], default=beats[0])
    nxt = next((x for x in beats if x["t0"] > b["t0"]), None)
    arrive = ease((t - (b["t0"] - 0.3)) / 0.4)
    leave = 1 - ease((t - (nxt["t0"] - 0.35)) / 0.3) if nxt else 1.0
    k = arrive * leave
    sway = math.sin(t * 2 * math.pi * 0.45)
    arms = {"right": [0.0, 0.0, 0.0, None], "left": [-2 * sway, 0.0, 0.0, None]}
    pulse = math.sin(t * 2 * math.pi * 1.6) if b["t0"] <= t <= b["t1"] else 0.0
    if b["kind"] == "streak":          # the last line waves
        pulse = math.sin(t * 2 * math.pi * 1.7) * 2.2
    for side, (sh, el, wr, hand) in b["arms"].items():
        ke, ks = ease(min(1.0, k * 1.7)), ease(max(0.0, k * 1.4 - 0.4))
        arms[side] = [sh * ks, el * ke + 4 * pulse * k * (1 if el > 0 else -1), wr * k + 3 * pulse * k,
                      hand if k > 0.35 else None]
    expr = X.expression(b["expr"] if k > 0.3 else "neutral")
    mouth = "smile"
    for s, v in b["cues"]:
        if s <= t:
            mouth = RHUBARB_TO_MOUTH[v]
    if not (b["t0"] <= t <= b["t1"] + 0.1):
        mouth = expr["mouth_shape"] if expr["mouth_shape"] in ("smile", "frown") else "smile"
    expr["mouth_shape"] = mouth
    if any(abs(t - (x["t0"] - 0.2)) < 0.055 for x in beats) or abs((t % 3.7) - 1.8) < 0.05:
        expr["eyes"] = "closed"                                      # blinks (also hide face changes)
    return b, dict(expr=expr, pose={s: tuple(v) for s, v in arms.items()}, tilt=b["tilt"] * k + 1.2 * sway,
                   bob=-1.5 * k + 0.8 * pulse * k)


def sfx(n, kind):
    t = np.arange(int(n * SR)) / SR
    if kind == "pop":
        return (np.sin(2 * np.pi * (900 - 3000 * t) * t) * np.exp(-t / 0.03) * 0.25).astype(np.float32)
    rng = np.random.default_rng(5)
    s = rng.normal(0, 1, len(t)) * np.sin(np.pi * t / n) ** 2
    return (np.convolve(s, np.ones(40) / 40, "same") * 0.35).astype(np.float32)


def render(out):
    beats, audio, total = plan()
    for b in beats:                                                  # a whoosh as each graphic comes in, pops after
        for at, kind in ((b["t0"] - 0.1, "whoosh"), (b["t0"] + 0.25, "pop")):
            s = sfx(0.35 if kind == "whoosh" else 0.12, kind)
            i = int(max(at, 0) * SR)
            audio[i:i + len(s)] += s[:len(audio) - i]
    bg = background()
    with tempfile.TemporaryDirectory() as d:
        wav = os.path.join(d, "a.wav")
        sf.write(wav, np.clip(audio, -1, 1), SR)
        for i in range(int(total * FPS)):
            t = i / FPS
            b, st = state(beats, t)
            canvas = bg.copy()
            graphic(canvas, b["kind"], t - (b["t0"] - 0.1), b["t1"] - b["t0"])
            ch = character_png(**st)
            canvas.alpha_composite(ch, ((W - ch.width) // 2, H - ch.height - 40))
            if b["t0"] <= t <= b["t1"] + 0.3:
                captions(canvas, b["words"], t, {w.lower() for w in b["hot"]})
            canvas.convert("RGB").save(os.path.join(d, f"f{i:04d}.png"))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(d, "f%04d.png"),
                        "-i", wav, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-c:a", "aac", "-b:a", "160k",
                        "-shortest", out], check=True)
    print("wrote", out, f"({total:.1f} s)")


if __name__ == "__main__":
    render(sys.argv[1] if len(sys.argv) > 1 else "video_321.mp4")
