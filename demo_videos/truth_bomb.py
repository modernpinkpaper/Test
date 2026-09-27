""""Your metabolism isn't broken" - a snarky hard-truth short with the kawaii girl.

The girl is six cut-out poses (girl_sprites/). Code makes her move: pose pops with
squash and stretch, a talking bounce that follows the voice, a walk-in, screen
shake, zoom punches, hearts and sparkles, props, and word-by-word captions.
Voice: Chatterbox copying voices/narrator-ref.wav (emotion 0.6). No GPU needed.

Setup (once):
    pip install pillow numpy imageio imageio-ffmpeg soundfile num2words chatterbox-tts "setuptools<81"
Run:
    python demo_videos/truth_bomb.py
"""
import hashlib
import math
import os
import random
import re
import subprocess

import imageio
import imageio_ffmpeg
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS, SR = 1080, 1920, 30, 24000
VOICE_REF = os.path.join(HERE, "voices", "narrator-ref.wav")
EMOTION, VOICE_SPEED = 0.6, 1.12
GAP = 0.18
CACHE = os.path.join(HERE, "_voice_cache")

# text: *word* = highlighted in the captions.  pose: 1-6 or b1-b8 (girl_sprites/), or "talk" (lip-sync)
# fx: shake, dark, zoom, walk, hearts, anger
SCRIPT = [
    dict(text="Your *metabolism* isn't broken.", pose=6, fx={"zoom"}, big="YOUR METABOLISM\nISN'T BROKEN"),
    dict(text="Your *excuses* are.", pose="b1", fx={"shake", "dark", "anger"}, big="YOUR EXCUSES ARE."),
    dict(text="That one little bite of your kid's *fries?* It *counts.*", pose="b6", prop="fries"),
    dict(text="That latte with whipped cream? That's *dessert,* babe. Not coffee.", pose="b2", prop="latte"),
    dict(text="You're not hungry at 9 PM. You're *bored.*", pose="b4", prop="clock"),
    dict(text="And *I'll start Monday* has been the plan since 2019.", pose="b5", prop="calendar"),
    dict(text="Skinny girls aren't *lucky.*", pose=4, fx={"walk"}),
    dict(text="They just say *no* to what you keep saying *yes* to.", pose="talk", fx={"zoom"}),
    dict(text="Nobody is coming to *save* you.", pose="talk", fx={"dark", "shake"}),
    dict(text="Close the *kitchen.* Drink the *water.* Go to *bed.*", pose="b7", prop="checklist"),
    dict(text="Mad? *Good.* Now prove me *wrong.*", pose="b3", fx={"zoom", "anger"}),
    dict(text="Follow for more truth you didn't ask for.", pose="talk", fx={"hearts"}),
]

PINK = ("#ffe3ef", "#ffb6d3")
DARK = ("#2a0a1c", "#0d0208")
HOT = (255, 64, 129)
GOLD = (255, 214, 64)


def font(w, size):
    return ImageFont.truetype(os.path.join(HERE, "fonts", f"poppins-latin-{w}-normal.woff"), size)


F_CAP, F_BIG, F_PROP, F_SMALL = font(800, 76), font(800, 92), font(800, 54), font(600, 34)


# ------------------------------------------------------------------- voice
def say_numbers(text):
    from num2words import num2words
    text = text.replace("9 PM", "nine P M")
    return re.sub(r"\d+", lambda m: num2words(int(m.group()), to="year") if len(m.group()) == 4
                  else num2words(int(m.group())), text)


def spoken(text):
    return say_numbers(text.replace("*", ""))


def trim(a, thr=0.01, keep=0.04):
    loud = np.where(np.abs(a) > thr)[0]
    return a if not len(loud) else a[max(loud[0] - int(keep * SR), 0):loud[-1] + int(keep * SR)]


def stretch(a, speed):
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    i, o = os.path.join(CACHE, "_i.wav"), os.path.join(CACHE, "_o.wav")
    sf.write(i, a, SR)
    subprocess.run([ff, "-loglevel", "error", "-y", "-i", i, "-filter:a", f"atempo={speed:.3f}", o], check=True)
    b, _ = sf.read(o, dtype="float32")
    return b


_tts = None


def voice(text):
    """Chatterbox line, cached on disk so re-renders are fast."""
    global _tts
    os.makedirs(CACHE, exist_ok=True)
    key = hashlib.md5(f"{spoken(text)}|{EMOTION}|{VOICE_SPEED}|{os.path.getsize(VOICE_REF)}".encode()).hexdigest()
    path = os.path.join(CACHE, key + ".wav")
    if os.path.exists(path):
        return sf.read(path, dtype="float32")[0]
    if _tts is None:
        import torch
        from chatterbox.tts import ChatterboxTTS
        _tts = ChatterboxTTS.from_pretrained(device="cuda" if torch.cuda.is_available() else "cpu")
    import torchaudio
    w = _tts.generate(spoken(text), audio_prompt_path=VOICE_REF, exaggeration=EMOTION, cfg_weight=0.5)
    if _tts.sr != SR:
        w = torchaudio.functional.resample(w, _tts.sr, SR)
    a = stretch(trim(w.squeeze(0).cpu().numpy().astype(np.float32)), VOICE_SPEED)
    sf.write(path, a, SR)
    return a


# ------------------------------------------------------------------ sounds
def sfx_pop(n=0.12):
    t = np.arange(int(n * SR)) / SR
    return (np.sin(2 * np.pi * (900 - 3000 * t) * t) * np.exp(-t / 0.03) * 0.35).astype(np.float32)


def sfx_boom(n=0.6):
    t = np.arange(int(n * SR)) / SR
    rng = np.random.default_rng(3)
    s = np.sin(2 * np.pi * np.cumsum(60 + 80 * np.exp(-t / 0.05)) / SR) * np.exp(-t / 0.18)
    s += rng.normal(0, 1, len(t)) * np.exp(-t / 0.04) * 0.3
    return (s * 0.6).astype(np.float32)


def sfx_whoosh(n=0.4):
    t = np.arange(int(n * SR)) / SR
    rng = np.random.default_rng(5)
    s = rng.normal(0, 1, len(t))
    s = np.convolve(s, np.ones(30) / 30, "same") * np.sin(np.pi * t / n) ** 2
    return (s * 0.5).astype(np.float32)


def beat(seconds):
    """Light trap-ish beat under the voice."""
    n = int(SR * seconds)
    out = np.zeros(n, np.float32)
    b = 60 / 100
    rng = np.random.default_rng(1)
    for k in range(int(seconds / b * 2) + 1):
        s = int(k * b / 2 * SR)
        seg = int(0.03 * SR)
        hat = np.diff(rng.normal(0, 1, seg) * np.exp(-np.arange(seg) / (0.006 * SR)), prepend=0) * 0.08
        e = min(n, s + seg)
        out[s:e] += hat[:e - s]
        if k % 4 == 0:
            seg = int(0.3 * SR)
            t = np.arange(seg) / SR
            kick = np.sin(2 * np.pi * np.cumsum(50 + 90 * np.exp(-t / 0.04)) / SR) * np.exp(-t / 0.15)
            e = min(n, s + seg)
            out[s:e] += kick[:e - s] * 0.5
    chords = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]
    bar = b * 4
    for i in range(int(seconds / bar) + 1):
        s = int(i * bar * SR)
        t = np.arange(int(bar * SR)) / SR
        pad = sum(np.sin(2 * np.pi * 440 * 2 ** ((m - 69) / 12) * t) for m in chords[i % 4])
        env = np.minimum(1, t / 0.3) * np.exp(-t / 2.5)
        e = min(n, s + len(t))
        out[s:e] += (pad * env * 0.035)[:e - s]
    return out * 0.5


# ------------------------------------------------------------------ drawing
def gradient(c1, c2):
    a = np.array([int(c1[i:i + 2], 16) for i in (1, 3, 5)], np.float32)
    b = np.array([int(c2[i:i + 2], 16) for i in (1, 3, 5)], np.float32)
    t = (np.arange(H, dtype=np.float32) / H)[:, None, None]
    img = np.broadcast_to(a * (1 - t) + b * t, (H, W, 3))
    return Image.fromarray(img.astype(np.uint8)).convert("RGBA")


SKIN, LASH = (254, 204, 171), (70, 35, 28)
EYES = [(68, 193, 162, 278), (195, 193, 287, 278)]  # eye boxes on mouth1.png (for blinking)
MOUTH_BOX = (138, 272, 218, 334)                    # mouth area that changes between mouth1-4


def talker_frames():
    """Standing pose with 4 mouths x (eyes open, eyes closed), all from mouth1-4.png.
    Only the mouth area is swapped, so hair and body never flicker."""
    sp = os.path.join(HERE, "girl_sprites")
    base = Image.open(os.path.join(sp, "mouth1.png")).convert("RGBA")
    mask = Image.new("L", base.size, 0)
    ImageDraw.Draw(mask).ellipse(MOUTH_BOX, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(4))
    out = {}
    for k in range(1, 5):
        m = Image.open(os.path.join(sp, f"mouth{k}.png")).convert("RGBA").crop((0, 0) + base.size)
        face = base.copy()
        face.paste(m, (0, 0), mask)
        out[(k, False)] = face
        shut = face.copy()
        d = ImageDraw.Draw(shut)
        for x0, y0, x1, y1 in EYES:
            d.ellipse([x0, y0, x1, y1], fill=SKIN)
            d.arc([x0 + 4, y0 + 14, x1 - 4, y1 - 4], start=20, end=160, fill=LASH, width=6)
            ox = x0 + 6 if x0 < 150 else x1 - 6
            d.line([(ox, y0 + 48), (ox + (-12 if x0 < 150 else 12), y0 + 40)], fill=LASH, width=5)
        out[(k, True)] = shut
    return out


def fit(im, height):
    im = im.crop(im.getbbox())
    s = height / im.height
    return im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)


def load_poses(height=930):
    """Keys: 1-6 (first sheet), "b1"-"b8" (second sheet), ("talk", mouth, eyes_closed)."""
    sp = os.path.join(HERE, "girl_sprites")
    poses = {}
    for i in range(1, 7):
        im = Image.open(os.path.join(sp, f"pose{i}.png")).convert("RGBA")
        poses[i] = fit(im, height if i not in (5, 6) else height * 0.82)
    for i in range(1, 9):
        poses[f"b{i}"] = fit(Image.open(os.path.join(sp, f"pose_b{i}.png")).convert("RGBA"), height)
    for (k, shut), im in talker_frames().items():
        poses[("talk", k, shut)] = fit(im, height)
    return poses


def mouth_for(level, fr):
    """Pick a mouth shape from voice loudness (0-1)."""
    if level < 0.12:
        return 1
    if level < 0.35:
        return 2
    return 4 if (fr // 3) % 4 == 0 else 3


def heart(d, x, y, s, color):
    d.ellipse([x - s, y - s * 0.6, x, y + s * 0.4], fill=color)
    d.ellipse([x, y - s * 0.6, x + s, y + s * 0.4], fill=color)
    d.polygon([(x - s * 0.97, y), (x + s * 0.97, y), (x, y + s * 1.1)], fill=color)


def sparkle(d, x, y, s, color):
    d.polygon([(x, y - s), (x + s * 0.25, y - s * 0.25), (x + s, y), (x + s * 0.25, y + s * 0.25),
               (x, y + s), (x - s * 0.25, y + s * 0.25), (x - s, y), (x - s * 0.25, y - s * 0.25)], fill=color)


def anger(d, x, y, s):
    for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        d.arc([x + dx * s * 0.5 - s * 0.45, y + dy * s * 0.5 - s * 0.45,
               x + dx * s * 0.5 + s * 0.45, y + dy * s * 0.5 + s * 0.45],
              start={(-1, -1): 0, (1, -1): 90, (-1, 1): 270, (1, 1): 180}[(dx, dy)],
              end={(-1, -1): 90, (1, -1): 180, (-1, 1): 360, (1, 1): 270}[(dx, dy)],
              fill=(235, 40, 60), width=int(s * 0.22))


OUT = (60, 30, 30)


def draw_prop(kind, sec, cap_progress):
    """Returns an RGBA image (about 520x440) of the prop."""
    im = Image.new("RGBA", (560, 460), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx = 280
    if kind == "fries":
        for i, x in enumerate(range(180, 390, 30)):
            h = 150 + (i * 37) % 60
            d.rounded_rectangle([x, 260 - h, x + 26, 300], radius=8, fill=(255, 210, 70), outline=OUT, width=5)
        d.polygon([(150, 230), (410, 230), (380, 430), (180, 430)], fill=(235, 50, 60), outline=OUT)
        d.line([(150, 230), (410, 230), (380, 430), (180, 430), (150, 230)], fill=OUT, width=7, joint="curve")
        heart(d, 280, 320, 34, (255, 255, 255))
    elif kind == "latte":
        d.polygon([(170, 170), (390, 170), (360, 430), (200, 430)], fill=(250, 244, 235))
        d.line([(170, 170), (390, 170), (360, 430), (200, 430), (170, 170)], fill=OUT, width=7, joint="curve")
        d.rectangle([185, 260, 375, 330], fill=(170, 110, 80))
        for x, y, r in ((210, 150, 45), (270, 125, 55), (340, 150, 45), (240, 95, 40), (300, 80, 38)):
            d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255), outline=OUT, width=5)
        d.line([(330, 60), (360, 0)], fill=HOT, width=16)
        d.text((cx, 300), "DESSERT", font=F_SMALL, anchor="mm", fill=(255, 255, 255))
    elif kind == "clock":
        d.ellipse([130, 60, 430, 360], fill=(255, 255, 255), outline=OUT, width=10)
        for k in range(12):
            a = k / 12 * 2 * math.pi
            d.line([(280 + 120 * math.sin(a), 210 - 120 * math.cos(a)),
                    (280 + 135 * math.sin(a), 210 - 135 * math.cos(a))], fill=OUT, width=6)
        wig = 6 * math.sin(sec * 20) if sec < 1 else 0
        a = math.radians(270 + wig)
        d.line([(280, 210), (280 + 80 * math.cos(a), 210 + 80 * math.sin(a))], fill=OUT, width=12)
        d.line([(280, 210), (280, 100)], fill=OUT, width=8)
        d.ellipse([266, 196, 294, 224], fill=HOT)
        d.rounded_rectangle([190, 370, 370, 445], radius=30, fill=(40, 20, 60))
        d.text((cx, 408), "9 PM", font=F_PROP, anchor="mm", fill=GOLD)
    elif kind == "calendar":
        d.rounded_rectangle([120, 80, 440, 420], radius=30, fill=(255, 255, 255), outline=OUT, width=8)
        d.rounded_rectangle([120, 80, 440, 180], radius=30, fill=HOT, outline=OUT, width=8)
        d.rectangle([124, 150, 436, 178], fill=HOT)
        for x in (190, 370):
            d.rounded_rectangle([x - 12, 50, x + 12, 110], radius=10, fill=OUT)
        d.text((cx, 132), "MONDAY", font=F_PROP, anchor="mm", fill=(255, 255, 255))
        d.text((cx, 250), "since", font=F_SMALL, anchor="mm", fill=OUT)
        d.text((cx, 330), "2019", font=font(800, 96), anchor="mm", fill=OUT)
    elif kind == "checklist":
        items = ["Close the kitchen", "Drink the water", "Go to bed"]
        for i, txt in enumerate(items):
            y = 40 + i * 140
            on = cap_progress > (i + 0.6) / 3
            d.rounded_rectangle([20, y, 540, y + 115], radius=55, fill=(255, 255, 255), outline=OUT, width=6)
            d.ellipse([40, y + 22, 110, y + 92], fill=HOT if on else (240, 220, 230), outline=OUT, width=5)
            if on:
                d.line([(57, y + 57), (72, y + 74), (96, y + 40)], fill=(255, 255, 255), width=10)
            d.text((130, y + 58), txt, font=font(800, 44), anchor="lm", fill=OUT)
    return im


def pop_scale(t, dur=0.35):
    """0 -> overshoot -> 1 (back-out easing)."""
    if t >= dur:
        return 1.0
    x = t / dur
    c = 2.2
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def draw_caption(d, words, n_shown, bounce):
    """Word-by-word caption. words: [(word, highlight)]; the newest word pops."""
    shown = words[:n_shown]
    lines, cur, maxw = [], [], W - 140
    for w, hl in shown:
        test = " ".join(x for x, _ in cur + [(w, hl)])
        if d.textlength(test, font=F_CAP) > maxw and cur:
            lines.append(cur)
            cur = []
        cur.append((w, hl))
    if cur:
        lines.append(cur)
    lines = lines[-2:]
    y = 1690 - (len(lines) - 1) * 92
    for li, line in enumerate(lines):
        total = sum(d.textlength(w, font=F_CAP) for w, _ in line) + d.textlength("  ", font=F_CAP) * 0.75 * (len(line) - 1)
        x = (W - total) / 2
        for wi, (w, hl) in enumerate(line):
            last = li == len(lines) - 1 and wi == len(line) - 1
            f = font(800, int(76 * (1 + 0.12 * bounce))) if last and bounce > 0 else F_CAP
            ww = d.textlength(w, font=F_CAP)
            d.text((x + ww / 2, y), w, font=f, anchor="mm", fill=GOLD if hl else (255, 255, 255),
                   stroke_width=9, stroke_fill=(20, 5, 15))
            x += ww + d.textlength("  ", font=F_CAP) * 0.75
        y += 92


def main():
    poses = load_poses()
    bg_pink, bg_dark = gradient(*PINK), gradient(*DARK)
    rng = random.Random(7)
    dots = [[rng.uniform(0, W), rng.uniform(0, H), rng.uniform(8, 30), rng.uniform(0.3, 1.2)] for _ in range(40)]

    # 1) voice for every line
    clips, lines = [], []
    t = 0.4
    for i, ln in enumerate(SCRIPT):
        print(f"voice {i + 1}/{len(SCRIPT)}: {ln['text']}")
        a = voice(ln["text"])
        lines.append(dict(ln, start=t, end=t + len(a) / SR))
        clips.append((t, a))
        t += len(a) / SR + GAP
    total = t + 1.2
    n_frames = int(total * FPS)
    vo = np.zeros(int(total * SR) + SR, np.float32)
    for st, a in clips:
        s = int(st * SR)
        vo[s:s + len(a)] += a
    # loudness per frame drives the talking bounce
    hop = SR // FPS
    env = np.array([np.sqrt(np.mean(vo[i * hop:(i + 1) * hop] ** 2)) for i in range(n_frames)])
    env = np.convolve(env / (env.max() + 1e-6), np.ones(3) / 3, "same")

    # sound effects
    fx = np.zeros_like(vo)
    for ln in lines:
        s = int(max(0, ln["start"] - 0.05) * SR)
        e = sfx_boom() if "shake" in ln.get("fx", ()) else sfx_whoosh() if "walk" in ln.get("fx", ()) else sfx_pop()
        fx[s:s + len(e)] += e[:len(fx) - s]

    silent = os.path.join(HERE, "_tb_silent.mp4")
    wr = imageio.get_writer(silent, fps=FPS, codec="libx264", quality=8, macro_block_size=1)
    particles = []
    mouth = 1
    for fr in range(n_frames):
        sec = fr / FPS
        cur = max([l for l in lines if l["start"] - 0.05 <= sec] or [lines[0]], key=lambda l: l["start"])
        lt = sec - cur["start"]
        effects = cur.get("fx", set())
        dark = "dark" in effects
        img = (bg_dark if dark else bg_pink).copy()
        d = ImageDraw.Draw(img, "RGBA")
        for p in dots:  # floating bokeh
            p[1] -= p[3]
            if p[1] < -40:
                p[1] = H + 40
            col = (255, 80, 120, 40) if dark else (255, 255, 255, 90)
            d.ellipse([p[0] - p[2], p[1] - p[2], p[0] + p[2], p[1] + p[2]], fill=col)

        # caption progress for this line
        words = [(w.strip("*"), w.startswith("*")) for w in cur["text"].split()]
        prog = max(0.0, min(1.0, lt / max(0.1, cur["end"] - cur["start"])))
        n_shown = max(1, math.ceil(prog * len(words))) if lt >= 0 else 0
        word_t = (prog * len(words)) % 1

        # big hook text or prop at the top
        if cur.get("big"):
            s = pop_scale(lt)
            layer = Image.new("RGBA", (W, 520), (0, 0, 0, 0))
            ld = ImageDraw.Draw(layer)
            for k, row in enumerate(cur["big"].split("\n")):
                ld.text((W / 2, 170 + k * 120), row, font=F_BIG, anchor="mm",
                        fill=HOT if dark else (255, 255, 255), stroke_width=10, stroke_fill=(20, 5, 15))
            if s != 1:
                layer = layer.resize((max(1, int(W * s)), max(1, int(520 * s))))
            img.alpha_composite(layer, (int((W - layer.width) / 2), int(80 + (520 - layer.height) / 2)))
        elif cur.get("prop"):
            prop = draw_prop(cur["prop"], lt, prog)
            if cur["prop"] == "checklist":
                prop = prop.resize((int(prop.width * 1.2), int(prop.height * 1.2)), Image.LANCZOS)
            s = pop_scale(lt - 0.1) if lt > 0.1 else 0.01
            prop = prop.rotate(4 * math.sin(sec * 3), resample=Image.BICUBIC)
            prop = prop.resize((max(1, int(prop.width * s)), max(1, int(prop.height * s))))
            img.alpha_composite(prop, (int(W / 2 - prop.width / 2), int(320 - prop.height / 2 + 14 * math.sin(sec * 2))))

        # the girl
        if cur["pose"] == "talk":
            if fr % 2 == 0 or fr == 0:
                mouth = mouth_for(env[fr] if fr < len(env) else 0, fr)
            blink = (fr % 96) in (0, 1, 2)
            girl = poses[("talk", mouth, blink)]
        else:
            girl = poses[cur["pose"]]
        talk = env[fr] if fr < len(env) else 0
        sx = 1 - 0.02 * talk
        sy = 1 + 0.035 * talk
        ps = pop_scale(lt, 0.3)
        sx *= ps
        sy *= 2 - ps if lt < 0.3 else 1  # squash while she pops in
        g = girl.resize((max(1, int(girl.width * sx)), max(1, int(girl.height * sy))), Image.BILINEAR)
        rot = 2.5 * math.sin(sec * 2.4)
        g = g.rotate(rot, resample=Image.BICUBIC, expand=True)
        cx, feet = W / 2, 1560
        if "walk" in effects:
            k = min(1, lt / 0.9)
            cx = -300 + (W / 2 + 300) * (1 - (1 - k) ** 3)
            feet -= abs(math.sin(lt * 12)) * 25 * (1 - k)
        feet -= 10 * talk
        shadow_w = g.width * 0.55
        d = ImageDraw.Draw(img, "RGBA")
        d.ellipse([cx - shadow_w / 2, 1538, cx + shadow_w / 2, 1572], fill=(90, 20, 50, 40))
        img.alpha_composite(g, (int(cx - g.width / 2), int(feet - g.height)))

        # particles
        if "hearts" in effects and fr % 5 == 0:
            particles.append(["heart", rng.choice((rng.uniform(120, 290), rng.uniform(790, 960))), 1300, rng.uniform(22, 40), 0])
        if "anger" in effects and fr % 12 == 0 and lt < 1.5:
            particles.append(["anger", rng.choice((330, 750)), rng.uniform(650, 800), 45, 0])
        if lt < 0.05 and fr > 0:
            for k in range(10):
                a = k / 10 * 2 * math.pi
                particles.append(["spark", cx + math.cos(a) * 60, 1100 + math.sin(a) * 60, 22, 0, a])
        alive = []
        for p in particles:
            p[4] += 1
            age = p[4]
            if p[0] == "heart":
                p[2] -= 6
                p[1] += math.sin(age / 6) * 3
                if age < 60:
                    heart(d, p[1], p[2], p[3], (255, 90, 140, int(255 * (1 - age / 60))))
                    alive.append(p)
            elif p[0] == "anger":
                if age < 20:
                    anger(d, p[1], p[2], p[3] * pop_scale(age / FPS, 0.2))
                    alive.append(p)
            elif p[0] == "spark":
                r = 60 + age * 22
                if age < 14:
                    sparkle(d, cx + math.cos(p[5]) * r, 1100 + math.sin(p[5]) * r, p[3] * (1 - age / 14),
                            (255, 230, 120, 230) if dark else (255, 255, 255, 240))
                    alive.append(p)
        particles = alive

        if lt >= 0 and sec <= cur["end"] + GAP:
            draw_caption(ImageDraw.Draw(img), words, n_shown, max(0.0, 1 - word_t * 4))

        # camera: zoom punch, shake, red flash
        frame = img
        if "zoom" in effects and lt < 0.4:
            z = 1 + 0.08 * (1 - lt / 0.4) ** 2
            frame = frame.resize((int(W * z), int(H * z)), Image.BILINEAR)
            frame = frame.crop(((frame.width - W) // 2, (frame.height - H) // 2,
                                (frame.width - W) // 2 + W, (frame.height - H) // 2 + H))
        if "shake" in effects and lt < 0.45:
            a = 22 * (1 - lt / 0.45)
            frame = frame.transform((W, H), Image.AFFINE,
                                    (1, 0, rng.uniform(-a, a), 0, 1, rng.uniform(-a, a)), fillcolor=(0, 0, 0, 255))
        if dark and lt < 0.25:
            flash = Image.new("RGBA", (W, H), (255, 30, 60, int(120 * (1 - lt / 0.25))))
            frame = frame.copy()
            frame.alpha_composite(flash)
        wr.append_data(np.asarray(frame.convert("RGB")))
        if fr % 150 == 0:
            print(f"frame {fr}/{n_frames}")
    wr.close()

    mix = vo[:int(total * SR)] + fx[:int(total * SR)] + beat(total)[:int(total * SR)]
    mix = np.clip(mix / max(1.0, np.abs(mix).max() / 0.95), -1, 1)
    wav = os.path.join(HERE, "_tb.wav")
    out = os.path.join(HERE, "truth_bomb.mp4")
    sf.write(wav, mix, SR)
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ff, "-loglevel", "error", "-y", "-i", silent, "-i", wav, "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "160k", "-shortest", out], check=True)
    os.remove(silent)
    os.remove(wav)
    print("saved", out)


if __name__ == "__main__":
    main()
