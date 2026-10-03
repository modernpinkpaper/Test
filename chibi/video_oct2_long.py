"""'What did I even do today' Day 1 (Thursday Oct 2): a ~10 minute TikTok vlog (1080x1920) made from her MT Log.

    python chibi/video_oct2_long.py voice              make + cache her voice for every line (slow, run first)
    python chibi/video_oct2_long.py render OUT.mp4     build audio, render in chunks, join (a restart only loses one chunk)

Screens: oct2_screens.py (HTML rebuilds of her apps, fake data). Shot plan: oct2_long_plan.py. Lines: oct2_long_lines.py.
Her voice is sped up 12% with the pitch kept, long gaps inside lines are cut, and there is no music.
The mouse, clicks and typing follow the log; zooms punch in on what she's talking about.
"""
import json
import math
import os
import random
import re
import subprocess
import sys
import tempfile

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SKITS = os.path.join(HERE, "..", "skits")
sys.path[:0] = [HERE, SKITS]
from oct2_long_lines import LINES, VOICE                       # noqa: E402
from oct2_long_plan import SHOTS, screen_jobs                  # noqa: E402

W, H, FPS, SR = 1080, 1920, 30, 24000
WORK = os.environ.get("OCT2_WORK", os.path.join(HERE, ".cache", "oct2_long"))
SCR = os.path.join(WORK, "scr")
SPR = os.path.join(WORK, "sprites")
SFX = os.environ.get("OCT2_SFX", "")
F800 = os.path.join(SKITS, "assets", "poppins-800.ttf")
F600 = os.path.join(SKITS, "assets", "poppins-600.ttf")
PINK, INK, CREAM = (232, 84, 132), (38, 28, 44), (255, 246, 249)
SPEED = 1.12
PX, PY, PW, PH = 24, 250, 1032, 1147          # the screen panel
VW, VH = 1280, 1422                           # screen CSS size

_f = {}


def font(size, w=800):
    k = (int(size), w)
    if k not in _f:
        _f[k] = ImageFont.truetype(F800 if w == 800 else F600, max(8, int(size)))
    return _f[k]


def ease(k):
    k = min(max(k, 0.0), 1.0)
    return k * k * (3 - 2 * k)


def eout(k):
    k = min(max(k, 0.0), 1.0)
    return 1 - (1 - k) ** 3


# ------------------------------------------------------------------ audio
def tighten(a, max_gap=0.14, keep=0.09):
    """Cut pauses inside a line down to `keep` seconds, so she never sounds slow."""
    env = np.sqrt(np.convolve(a ** 2, np.ones(480) / 480, "same"))
    quiet = env < 0.02 * env.max()
    out, i, n = [], 0, len(a)
    while i < n:
        if quiet[i]:
            j = i
            while j < n and quiet[j]:
                j += 1
            if (j - i) / SR > max_gap and i > 0 and j < n:
                k = int(keep * SR)
                out.append(a[i:i + k // 2])
                out.append(a[j - k // 2:j])
            else:
                out.append(a[i:j])
            i = j
        else:
            j = i
            while j < n and not quiet[j]:
                j += 1
            out.append(a[i:j])
            i = j
    return np.concatenate(out).astype(np.float32)


def faster(a, key):
    """Speed up with the pitch kept (ffmpeg atempo), cached."""
    p = os.path.join(WORK, "lines", f"{key}.wav")
    if not os.path.exists(p):
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with tempfile.TemporaryDirectory() as d:
            sf.write(os.path.join(d, "a.wav"), a, SR)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(d, "a.wav"), "-filter:a", f"atempo={SPEED}", "-ar", str(SR), p], check=True)
    return sf.read(p, dtype="float32")[0]


def ogg(name, vol=1.0):
    a, sr = sf.read(os.path.join(SFX, name + ".ogg"), dtype="float32")
    if a.ndim > 1:
        a = a.mean(1)
    if sr != SR:
        import scipy.signal as ss
        a = ss.resample_poly(a, SR, sr).astype(np.float32)
    return a * vol


def synth(name, rng):
    if name == "key":
        n = int(0.035 * SR)
        t = np.arange(n) / SR
        click = rng.normal(0, 1, n) * np.exp(-t / 0.004)
        import scipy.signal as ss
        b, c = ss.butter(2, [1800 / (SR / 2), 6500 / (SR / 2)], "band")
        click = ss.lfilter(b, c, click)
        thump = np.sin(2 * np.pi * rng.uniform(140, 210) * t) * np.exp(-t / 0.01) * 0.5
        return ((click * 0.5 + thump) * rng.uniform(0.6, 1.0) * 0.16).astype(np.float32)
    if name == "notif":
        t = np.arange(int(0.5 * SR)) / SR
        a = np.sin(2 * np.pi * 784 * t) * np.exp(-t / 0.12) * (t < 0.14) + np.sin(2 * np.pi * 1175 * t) * np.exp(-(t - 0.12).clip(0) / 0.18) * (t >= 0.12)
        return (a * 0.12).astype(np.float32)
    if name == "send":
        t = np.arange(int(0.25 * SR)) / SR
        return (rng.normal(0, 1, len(t)) * np.sin(np.pi * t / t[-1]) ** 2 * 0.05).astype(np.float32)
    if name == "whoosh":
        t = np.arange(int(0.35 * SR)) / SR
        import scipy.signal as ss
        x = rng.normal(0, 1, len(t))
        b, c = ss.butter(2, 900 / (SR / 2))
        x = ss.lfilter(b, c, x) * np.sin(np.pi * t / t[-1]) ** 2
        return (x / np.abs(x).max() * 0.12).astype(np.float32)
    if name == "print":
        t = np.arange(int(1.6 * SR)) / SR
        motor = np.sign(np.sin(2 * np.pi * 95 * t)) * 0.3 + rng.normal(0, 1, len(t)) * 0.25
        import scipy.signal as ss
        b, c = ss.butter(2, 1400 / (SR / 2))
        motor = ss.lfilter(b, c, motor) * np.minimum(1, np.minimum(t / 0.1, (t[-1] - t) / 0.2))
        return (motor * 0.06).astype(np.float32)
    return np.zeros(10, np.float32)


SFX_MAP = {"click": ("click_002", 0.45), "error": ("error_004", 0.35), "ding": ("confirmation_001", 0.4), "success": ("confirmation_002", 0.4),
           "tada": ("confirmation_004", 0.45), "open": ("open_001", 0.4), "bee": ("pluck_001", 0.45), "pop": ("drop_002", 0.35)}


# ------------------------------------------------------------------ timing
def line_words(text):
    return re.sub(r"\[\w+\]\s*", "", text).split()


def voice_cached(line):
    import hashlib
    import voices
    tone, text = voices.split_tag(line)
    ex, cfg, _ = voices.TONES[tone]
    tag = f"cb3|{VOICE}|{tone}|{ex}|{cfg}|{text}|{os.path.getsize(voices.ref_for(VOICE))}"
    return os.path.exists(os.path.join(voices.CACHE, hashlib.md5(tag.encode()).hexdigest() + ".wav"))


def build_timeline():
    import voices
    import video_321 as V
    tl, t = [], 0.35
    prev_sec = None
    n = int(os.environ.get("LIMIT", len(LINES)))
    for i, ((sec, line), shot) in enumerate(list(zip(LINES, SHOTS))[:n]):
        tone, txt = voices.split_tag(line)
        if os.environ.get("PLACEHOLDER") and not voice_cached(line):
            a = np.zeros(int(len(txt.split()) * 0.27 * SR), np.float32)
            a[::997] = 0.001
        else:
            a = faster(tighten(voices.say(VOICE, line)), f"{i:03d}_" + __import__("hashlib").md5(line.encode()).hexdigest()[:10])
        if sec != prev_sec and i:
            t += 0.25
        prev_sec = sec
        lead = 0.0
        if shot.get("fx") in ("title",):
            lead = 0.3
        dur = len(a) / SR
        cue_p = os.path.join(WORK, "lines", f"{i:03d}.cues.json")
        if os.environ.get("PLACEHOLDER") and not voice_cached(line):
            cue_p = os.path.join(WORK, "empty.cues.json")
            json.dump([], open(cue_p, "w"))
        if not os.path.exists(cue_p):
            with tempfile.TemporaryDirectory() as d:
                p = os.path.join(d, "l.wav")
                sf.write(p, a, SR)
                json.dump(V.mouth_cues(p, txt), open(cue_p, "w"))
        cues = json.load(open(cue_p))
        words = line_words(line)
        lens = np.array([len(w) + 2 for w in words], float)
        wt = dur * 0.95 * np.r_[0, np.cumsum(lens)[:-1]] / lens.sum()
        tail = 0.12
        if shot.get("fx") in ("montage", "montage2", "timelapse", "clockpunch"):
            tail = 0.35
        if shot.get("fx") == "end" and i == len(LINES) - 1:
            tail = 2.2
        tl.append(dict(i=i, sec=sec, tone=tone, text=txt, audio=a, t0=t, vs=t + lead, ve=t + lead + dur, t1=t + lead + dur + tail,
                       cues=[(t + lead + c0, c) for c0, c in cues], words=[(w, t + lead + x) for w, x in zip(words, wt)], shot=shot))
        t += lead + dur + tail
    return tl, t + 0.3


def at_time(seg, at):
    """Resolve a plan time: word, fraction or 'Ns' -> absolute seconds."""
    if isinstance(at, (int, float)):
        return seg["vs"] + at * (seg["ve"] - seg["vs"]) if at <= 1 else seg["vs"] + at
    if isinstance(at, str) and at.endswith("s") and at[:-1].replace(".", "").isdigit():
        return seg["vs"] + float(at[:-1])
    key = at.lower().strip(".,?!")
    for w, tt in seg["words"]:
        if w.lower().strip(".,?!'") .startswith(key.strip("'")):
            return tt
    return seg["vs"]


def mix_audio(tl, total):
    n = int(total * SR) + SR
    voice = np.zeros(n, np.float32)
    fx = np.zeros(n, np.float32)
    rng = np.random.default_rng(7)

    def put(buf, x, at):
        i = max(0, int(at * SR))
        m = min(len(x), n - i)
        if m > 0:
            buf[i:i + m] += x[:m]
    for seg in tl:
        put(voice, seg["audio"], seg["vs"])
        sh = seg["shot"]
        for c in sh["clicks"]:
            put(fx, ogg(*SFX_MAP["click"]), at_time(seg, c))
        for a0, a1 in sh["keys"]:
            ta, tb = at_time(seg, a0), at_time(seg, a1)
            tt = ta
            while tt < tb:
                put(fx, synth("key", rng), tt)
                tt += rng.uniform(0.06, 0.13) + (0.25 if rng.random() < 0.06 else 0)
        for a, name in sh["sfx"]:
            x = ogg(*SFX_MAP[name]) if name in SFX_MAP else synth(name, rng)
            put(fx, x, at_time(seg, a))
        if seg["i"] and tl[seg["i"] - 1]["sec"] != seg["sec"]:
            put(fx, synth("whoosh", rng) * 0.7, seg["t0"] - 0.2)
    import voices
    v = voices.clarity(voice)
    out = v + fx
    return (out / max(1.0, np.abs(out).max() / 0.97)).astype(np.float32)


# ------------------------------------------------------------------ screens + camera
class Screens:
    def __init__(self):
        self.cache = {}
        self.boxes = {}

    def get(self, key, hi):
        k = (key, hi)
        if k not in self.cache:
            if len(self.cache) > 10:
                self.cache.pop(next(iter(self.cache)))
            im = Image.open(os.path.join(SCR, key + ".png")).convert("RGB")
            if not hi:
                im = im.resize((VW, VH), Image.LANCZOS)
            self.cache[k] = im
        return self.cache[k]

    def box(self, key, name):
        if key not in self.boxes:
            self.boxes[key] = json.load(open(os.path.join(SCR, key + ".json")))
        return self.boxes[key].get(name)


SCREENS = Screens()


def cam_target(key, tgt):
    if tgt == "full":
        c = SCREENS.box(key, "_content")
        if not c:
            return (VW / 2, VH / 2, 1.0)
        x, y, w, h = c
        return (x + w / 2, y + h / 2, min(2.2, max(1.0, min(VW / max(w, 1), VH / max(h, 1)))))
    if isinstance(tgt, tuple) and isinstance(tgt[0], str):
        b = SCREENS.box(key, tgt[0])
        if not b:
            return cam_target(key, "full")
        x, y, w, h = b
        fy = tgt[2] if len(tgt) > 2 else 0.5
        fx = tgt[3] if len(tgt) > 3 else 0.5
        return (x + w * fx, y + h * fy, tgt[1])
    if isinstance(tgt, tuple):
        return tgt
    b = SCREENS.box(key, tgt)
    if not b:
        return (VW / 2, VH / 2, 1.0)
    x, y, w, h = b
    z = min(2.6, max(1.2, 0.55 * VW / max(w, 1), 0.45 * VH / max(h, 1)))
    return (x + w / 2, y + h / 2, z)


def screen_at(seg, T):
    scr = seg["shot"]["scr"]
    if isinstance(scr, str):
        return scr
    cur = scr[0][1]
    for at, k in scr:
        if T >= at_time(seg, at) - 0.05:
            cur = k
    return cur


def camera(seg, T, key):
    keys = [(at_time(seg, a) if i else seg["t0"], cam_target(key, tg)) for i, (a, tg) in enumerate(seg["shot"]["cam"])]
    c = keys[0][1]
    for tt, tg in keys[1:]:
        k = eout((T - (tt - 0.08)) / 0.42)
        c = tuple(a + (b - a) * k for a, b in zip(c, tg))
    drift = 1 + 0.025 * ease((T - seg["t0"]) / max(seg["t1"] - seg["t0"], 0.1))
    return c[0], c[1], c[2] * drift


def view_rect(cx, cy, z, content=None):
    """The visible part of the screen: kept inside the app windows (no empty wallpaper) when zoomed in."""
    w, h = VW / z, VH / z
    bx0, by0, bx1, by1 = 0, 0, VW, VH
    if content:
        cx0, cy0, cw, ch = content
        cx0, cy0 = max(cx0, 0), max(cy0, 0)
        cx1, cy1 = min(cx0 + cw, VW), min(cy0 + ch, VH)
        if cx1 - cx0 >= w:
            bx0, bx1 = cx0, cx1
        else:
            m = (cx0 + cx1) / 2
            bx0, bx1 = m - w / 2, m + w / 2
        if cy1 - cy0 >= h:
            by0, by1 = cy0, cy1
        else:
            m = (cy0 + cy1) / 2
            by0, by1 = m - h / 2, m + h / 2
    x0 = min(max(cx - w / 2, bx0), bx1 - w)
    y0 = min(max(cy - h / 2, by0), by1 - h)
    x0 = min(max(x0, 0), VW - w)
    y0 = min(max(y0, 0), VH - h)
    return x0, y0, w, h


def draw_screen(key, cam):
    x0, y0, w, h = view_rect(*cam, SCREENS.box(key, "_content"))
    hi = cam[2] > 1.15
    im = SCREENS.get(key, hi)
    s = im.width / VW
    return im.resize((PW, PH), Image.BILINEAR, box=(x0 * s, y0 * s, (x0 + w) * s, (y0 + h) * s)), (x0, y0, w, h)


# ------------------------------------------------------------------ cursor
CURSOR = None


def cursor_img():
    global CURSOR
    if CURSOR is None:
        s = 3
        im = Image.new("RGBA", (24 * s, 34 * s), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        pts = [(1, 1), (1, 26), (7, 20), (11, 30), (15, 28), (11, 19), (19, 19)]
        d.polygon([(x * s, y * s) for x, y in pts], fill=(255, 255, 255), outline=(0, 0, 0), width=2 * s)
        CURSOR = im
    return CURSOR


def cursor_pos(seg, T, key):
    pts = []
    for a, tg in seg["shot"]["cur"]:
        if isinstance(tg, tuple):
            p = tg
        else:
            b = SCREENS.box(key, tg)
            if not b:
                continue
            p = (b[0] + b[2] / 2, b[1] + b[3] / 2)
        pts.append((at_time(seg, a) if a != 0 else seg["t0"], p))
    if not pts:
        return None
    p = pts[0][1]
    for tt, q in pts[1:]:
        k = ease((T - (tt - 0.45)) / 0.45)
        p = (p[0] + (q[0] - p[0]) * k, p[1] + (q[1] - p[1]) * k)
    return p


# ------------------------------------------------------------------ chibi
FACE_FOR_TONE = {"neutral": "neutral", "sassy": "smug", "excited": "excited", "annoyed": "annoyed", "calm": "sad", "shocked": "surprised"}
MOUTH = {"X": "smile", "A": "smile", "B": "open", "C": "open", "D": "wide", "E": "oh", "F": "oh", "G": "open", "H": "open"}
_spr = {}


def sprite(face, mouth, eyes):
    k = (face, mouth, eyes)
    if k not in _spr:
        im = Image.open(os.path.join(SPR, f"{face}_{mouth}_{eyes}.png")).convert("RGBA")
        _spr[k] = im.resize((int(im.width * 0.62), int(im.height * 0.62)), Image.LANCZOS)
    return _spr[k]


def chibi(frame, seg, T):
    face = seg["shot"].get("face") or FACE_FOR_TONE.get(seg["tone"], "neutral")
    talking = seg["vs"] <= T <= seg["ve"]
    mouth = "smile" if face not in ("annoyed", "sad", "eye_roll") else "frown"
    if talking:
        for c0, c in seg["cues"]:
            if c0 <= T:
                mouth = MOUTH[c]
        if mouth == "smile" and face in ("annoyed", "sad", "eye_roll"):
            mouth = "frown"
    eyes = "closed" if (T % 3.4) < 0.11 and face not in ("eye_roll",) else "open"
    im = sprite(face, mouth, eyes)
    bob = math.sin(T * 7) * 3 if talking else math.sin(T * 1.6) * 2
    # round badge
    cx, cy, r = 168, 1690, 138
    d = ImageDraw.Draw(frame)
    d.ellipse((cx - r - 7, cy - r - 7, cx + r + 7, cy + r + 7), fill=PINK)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 226, 236))
    mask = Image.new("L", (2 * r, 2 * r), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 2 * r, 2 * r), fill=255)
    layer = Image.new("RGBA", (2 * r, 2 * r), (0, 0, 0, 0))
    layer.alpha_composite(im, (r - im.width // 2, int(18 + bob)))
    layer.putalpha(Image.fromarray(np.minimum(np.array(layer.getchannel("A")), np.array(mask))))
    frame.alpha_composite(layer, (cx - r, cy - r))


# ------------------------------------------------------------------ overlays
def to12(hm):
    h, m = map(int, hm.split(":"))
    return h, m


def clock_at(seg, T):
    c = seg["shot"]["clock"]
    if isinstance(c, tuple):
        (h0, m0), (h1, m1) = to12(c[0]), to12(c[1])
        a = (h0 % 12 + (12 if h0 < 7 or h0 == 12 else 0)) * 60 + m0
        b = (h1 % 12 + (12 if h1 < 7 or h1 == 12 else 0)) * 60 + m1
        k = ease((T - seg["vs"]) / max(seg["t1"] - seg["vs"], 0.1))
        v = a + (b - a) * k
    else:
        h, m = to12(c)
        v = (h % 12 + (12 if h < 7 or h == 12 else 0)) * 60 + m
    return v


def fmt(v):
    h, m = int(v // 60), int(v % 60)
    ap = "AM" if h < 12 else "PM"
    return f"{(h - 1) % 12 + 1}:{m:02d}", ap


SECTION = {"hook": "", "sync": "THE COMPUTER STARTED WITHOUT ME", "checkin": "MORNING CHECK-IN", "mtlog": "NEW MT LOG", "assistant": "THE NEW ASSISTANT",
           "setup": "THE SETUP SPIRAL", "review": "REVIEW WITH THE TEAM", "shopify": "SHOPIFY + PROJECTS", "quit": "I QUIT THE ASSISTANT", "popups": "TESTING AMAZON POP-UPS",
           "win": "THE WIN OF THE DAY", "printer": "THE PRINTER", "orders": "ORDERS + TEAM", "timing": "TEAM TIMING", "wrap": "WRAP-UP MODE", "done": "DONE",
           "stats": "MY DAY IN NUMBERS", "tomorrow": "TOMORROW", "bye": ""}


def header(frame, seg, T):
    d = ImageDraw.Draw(frame)
    d.rounded_rectangle((24, 60, 250, 140), 26, fill=PINK)
    d.text((137, 100), "DAY 1", font=font(46), fill=(255, 255, 255), anchor="mm")
    d.text((272, 80), "what did I even do today?", font=font(34), fill=INK, anchor="lm")
    d.text((272, 122), "Thursday, Oct 2 · from my computer logs", font=font(24, 600), fill=(120, 100, 120), anchor="lm")
    v = clock_at(seg, T)
    hm, ap = fmt(v)
    d.rounded_rectangle((780, 156, 1056, 236), 22, fill=INK)
    d.text((1000, 196), ap, font=font(26), fill=(255, 190, 210), anchor="mm")
    d.text((900, 197), hm, font=font(50), fill=(255, 255, 255), anchor="mm")
    # day progress 8:00 -> 3:20
    k = min(max((v - 480) / (920 - 480), 0), 1)
    d.rounded_rectangle((24, 186, 760, 206), 10, fill=(245, 205, 220))
    d.rounded_rectangle((24, 186, 24 + max(20, 736 * k), 206), 10, fill=PINK)
    sec = SECTION.get(seg["sec"], "")
    if sec:
        d.text((26, 226), sec, font=font(24), fill=PINK, anchor="lm")


def panel_frame(frame):
    d = ImageDraw.Draw(frame)
    d.rounded_rectangle((PX - 6, PY - 6, PX + PW + 6, PY + PH + 6), 26, fill=INK)


def round_mask():
    m = Image.new("L", (PW, PH), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, PW, PH), 20, fill=255)
    return m


RMASK = None


def captions(frame, seg, T):
    if not (seg["vs"] - 0.05 <= T <= seg["ve"] + 0.25):
        return
    said = [i for i, (_, st) in enumerate(seg["words"]) if st <= T]
    if not said:
        return
    c0 = said[-1] // 3 * 3
    chunk = [w.upper() for w, _ in seg["words"][c0:c0 + 3]]
    cur = said[-1] - c0
    f = font(70)
    gap = 20
    tot = sum(f.getlength(w) for w in chunk) + gap * (len(chunk) - 1)
    if tot > 980:
        f = font(70 * 980 / tot)
        tot = sum(f.getlength(w) for w in chunk) + gap * (len(chunk) - 1)
    d = ImageDraw.Draw(frame)
    x = W / 2 - tot / 2
    for i, w in enumerate(chunk):
        if i <= cur:
            col = (255, 214, 64) if i == cur else (255, 255, 255)
            d.text((x, 1462), w, font=f, fill=col, anchor="lm", stroke_width=9, stroke_fill=(20, 14, 22))
        x += f.getlength(w) + gap


def now_card(frame, seg, T, key):
    """The little card next to her: which app she's in."""
    if seg["shot"].get("fx") in ("stats", "end", "title", "montage", "montage2"):
        return
    app = APP_NAMES.get(key.rstrip("0123456789_") if key not in APP_NAMES else key, None) or app_for(key)
    d = ImageDraw.Draw(frame)
    d.rounded_rectangle((330, 1580, 1056, 1660), 24, fill=(255, 255, 255), outline=(245, 205, 220), width=4)
    d.text((358, 1620), "NOW IN", font=font(22), fill=(160, 140, 160), anchor="lm")
    d.text((470, 1620), app, font=font(34), fill=INK, anchor="lm")


def app_for(key):
    for pre, name in APP_PREFIX:
        if key.startswith(pre):
            return name
    return "my computer"


APP_NAMES = {}
APP_PREFIX = [("custmsg", "Microsoft Teams"), ("wflink", "Microsoft Teams"), ("printq", "the printer queue"), ("sales", "Google Sheets"), ("teams", "Microsoft Teams"), ("player", "a screen recording"), ("rev_player", "a screen recording"),
              ("msgs", "Seller Central · messages"), ("waiting", "Seller Central · messages"), ("listing", "Amazon.com"), ("cl_", "my Claude chat"), ("typo", "my Claude chat"),
              ("env_q", "my Claude chat"), ("env_a", "my Claude chat"), ("why", "my Claude chat"), ("quit", "my Claude chat"), ("timing", "my Claude chat"),
              ("prog", "Programs and Features"), ("rein", "MT Log setup"), ("startup", "File Explorer"), ("fallbreak", "Microsoft Teams"), ("as_proj", "Apps Script"),
              ("as_new", "Apps Script"), ("as_done", "Apps Script"), ("as_plus", "Apps Script"), ("as", "the MPP Assistant"), ("model", "the MPP Assistant"),
              ("countdown", "the MPP Assistant"), ("keys", "Claude Console"), ("cost", "Claude Console"), ("env", "Environment Variables"), ("ps", "PowerShell"),
              ("gcloud", "Google Cloud"), ("saveas", "Notepad"), ("mem", "Notepad"), ("learned", "Notepad"), ("recs", "Notepad"), ("results", "Notepad"), ("cs_save", "Notepad"),
              ("tomorrow", "Notepad"), ("proofs", "File Explorer"), ("reload", "Microsoft Teams"), ("shopify", "Shopify"), ("track", "Google Sheets"), ("bee", "BeeBEEP"),
              ("cust", "Seller Central · customization"), ("pop", "Amazon.com"), ("wf", "Seller Assistant"), ("csv", "Google Sheets"), ("zip", "File Explorer"),
              ("rules", "GitHub"), ("blank", "Google Docs"), ("p49", "Google Docs"), ("p88", "Google Docs"), ("mailmsg", "Seller Central · messages"),
              ("schome", "Seller Central"), ("custmsg", "Microsoft Teams"), ("indd", "InDesign"), ("sorry", "Microsoft Teams"), ("ord", "Seller Central · order"),
              ("wflink", "Microsoft Teams"), ("gm", "Gmail"), ("spapi", "Developer Central"), ("health", "Account Health"), ("bowl", "lunch!"), ("cake", "a cake website")]


def ripple(frame, seg, T, vr, pos):
    for c in seg["shot"]["clicks"]:
        tc = at_time(seg, c)
        k = (T - tc) / 0.35
        if 0 <= k <= 1 and pos:
            x, y = to_panel(pos, vr)
            r = 14 + 46 * eout(k)
            a = int(200 * (1 - k))
            ov = Image.new("RGBA", frame.size, (0, 0, 0, 0))
            ImageDraw.Draw(ov).ellipse((x - r, y - r, x + r, y + r), outline=(255, 59, 127, a), width=7)
            frame.alpha_composite(ov)


def to_panel(p, vr):
    x0, y0, w, h = vr
    return PX + (p[0] - x0) / w * PW, PY + (p[1] - y0) / h * PH


def pressed(seg, T):
    return any(0 <= T - at_time(seg, c) < 0.12 for c in seg["shot"]["clicks"])


# ------------------------------------------------------------------ special fx
MONTAGE = ["sales_new", "teams_vid", "msgs_open", "as7", "env_k2", "proofs", "shopify", "cust2", "wf_ran", "csv", "p88_print", "schome", "indd8", "gm_arch", "health", "bowl"]
MONTAGE2 = ["as0", "as3", "as7", "keys1", "env_new", "as_new", "ps2", "gcloud", "mem", "recs", "quit_a"]


def badge(frame, text, y=290):
    d = ImageDraw.Draw(frame)
    f = font(34)
    w = f.getlength(text) + 50
    d.rounded_rectangle((W / 2 - w / 2, y, W / 2 + w / 2, y + 64), 32, fill=(20, 14, 22))
    d.text((W / 2, y + 32), text, font=f, fill=(255, 214, 64), anchor="mm")


def fx_overlay(frame, seg, T):
    fx = seg["shot"].get("fx")
    t = T - seg["t0"]
    d = ImageDraw.Draw(frame)
    if fx == "title":
        k = eout(t / 0.4)
        ov = Image.new("RGBA", (PW, PH), (255, 236, 243, int(225 * k)))
        frame.alpha_composite(ov, (PX, PY))
        s = 0.6 + 0.4 * k
        d = ImageDraw.Draw(frame)
        d.text((W / 2, 700), "DAY 1", font=font(220 * s), fill=PINK, anchor="mm", stroke_width=10, stroke_fill=(255, 255, 255))
        d.text((W / 2, 880), "what did I even", font=font(76 * s), fill=INK, anchor="mm")
        d.text((W / 2, 970), "do today?", font=font(76 * s), fill=INK, anchor="mm")
        d.text((W / 2, 1080), "Thursday · Oct 2", font=font(40 * s, 600), fill=(140, 110, 140), anchor="mm")
    elif fx in ("montage", "montage2", "timelapse"):
        badge(frame, ">>  TIME-LAPSE" if fx != "montage" else ">>  EVERY APP · EVERY CLICK")
    elif fx == "counter":
        n = int(249 * ease((T - seg["vs"]) / max(seg["ve"] - seg["vs"], 0.1)))
        d.rounded_rectangle((300, 980, 780, 1130), 30, fill=(20, 14, 22))
        d.text((540, 1030), "SOP SCREENSHOTS", font=font(30), fill=(255, 190, 210), anchor="mm")
        d.text((540, 1085), f"{n}", font=font(60), fill=(255, 255, 255), anchor="mm")
    elif fx == "mtlogpop":
        k = eout((T - seg["vs"] - 0.4) / 0.3)
        if k > 0:
            d.rounded_rectangle((120, 1000, 960, 1150), 30, fill=(255, 255, 255), outline=PINK, width=6)
            d.text((540, 1045), "MT LOG", font=font(44 * (0.7 + 0.3 * k)), fill=PINK, anchor="mm")
            d.text((540, 1105), "logs every app · click · print", font=font(32, 600), fill=INK, anchor="mm")
    elif fx == "confetti":
        rng = random.Random(3)
        for i in range(90):
            x = rng.uniform(0, W)
            sp = rng.uniform(300, 700)
            y = 250 + (T - seg["t0"]) * sp - rng.uniform(0, 600)
            if 250 < y < 1400:
                c = rng.choice([PINK, (255, 214, 64), (126, 200, 255), (139, 224, 164)])
                a = (T * 4 + i) % 6.28
                d.rectangle((x, y, x + 14 * abs(math.cos(a)) + 3, y + 9), fill=c)
    elif fx == "clockpunch":
        k = eout(t / 0.3)
        hm, ap = fmt(clock_at(seg, T))
        d.rounded_rectangle((W / 2 - 300 * k, 650, W / 2 + 300 * k, 900), 40, fill=(20, 14, 22))
        if k > 0.6:
            d.text((W / 2, 775), f"{hm} {ap}", font=font(130), fill=(255, 255, 255), anchor="mm")
    elif fx == "logoff":
        k = ease((T - at_time(seg, "logged")) / 0.6)
        if k > 0:
            ov = Image.new("RGBA", (PW, PH), (12, 18, 40, int(235 * k)))
            frame.alpha_composite(ov, (PX, PY))
            d.text((W / 2, 760), "3:20", font=font(150), fill=(255, 255, 255), anchor="mm")
            d.text((W / 2, 880), "signed out · see you tomorrow", font=font(38, 600), fill=(200, 210, 240), anchor="mm")
    elif fx == "stats":
        stats_card(frame, seg, T)
    elif fx == "end":
        k = eout(t / 0.4)
        ov = Image.new("RGBA", (PW, PH), (255, 236, 243, int(225 * k)))
        frame.alpha_composite(ov, (PX, PY))
        d.text((W / 2, 640), "that was", font=font(60, 600), fill=(140, 110, 140), anchor="mm")
        d.text((W / 2, 740), "DAY 1", font=font(170), fill=PINK, anchor="mm", stroke_width=8, stroke_fill=(255, 255, 255))
        d.rounded_rectangle((200, 880, 880, 1010), 60, fill=PINK)
        d.text((W / 2, 945), "follow for day 2", font=font(54), fill=(255, 255, 255), anchor="mm")


STATS = [("⏱", "6h 41m", "active on the computer"), ("🖱", "1,024", "clicks"), ("🌐", "241", "web pages"), ("🖨", "0 of 2", "prints actually printed"),
         ("✉", "0 of 4", "messages answered"), ("📊", "1", "very happy spreadsheet")]
STAT_WORDS = ["Okay", "seven", "thousand", "web", "prints", "messages", "spreadsheet"]


def stats_card(frame, seg, T):
    d = ImageDraw.Draw(frame)
    ov = Image.new("RGBA", (PW, PH), (255, 246, 249, 255))
    frame.alpha_composite(ov, (PX, PY))
    d.text((W / 2, PY + 90), "MY DAY IN NUMBERS", font=font(58), fill=PINK, anchor="mm")
    first = [s for s in TL if s["sec"] == "stats"]
    for j, (ic, big, small) in enumerate(STATS):
        if j < 5:
            seg2 = first[1] if len(first) > 1 else seg
            word = ["seven", "thousand", "web", "prints", "messages"][j]
            ts = at_time(seg2, word)
        else:
            ts = first[2]["vs"] if len(first) > 2 else seg["vs"]
        k = eout((T - ts + 0.1) / 0.3)
        if k <= 0:
            continue
        y = PY + 190 + j * 150
        x = PX + 60 - 40 * (1 - k)
        d.rounded_rectangle((x, y, x + PW - 120, y + 125), 28, fill=(255, 255, 255), outline=(245, 205, 220), width=4)
        d.text((x + 140, y + 62), big, font=font(58), fill=INK, anchor="mm")
        d.text((x + 260, y + 62), small, font=font(36, 600), fill=(120, 100, 120), anchor="lm")


# ------------------------------------------------------------------ frame
TL = []


def seg_at(T):
    s = TL[0]
    for x in TL:
        if x["t0"] <= T:
            s = x
    return s


BG = None


def background():
    global BG
    if BG is None:
        g = np.linspace(0, 1, H)[:, None, None]
        top, bot = np.array([255, 240, 246])[None, None], np.array([255, 214, 228])[None, None]
        BG = Image.fromarray((top * (1 - g) + bot * g).repeat(W, 1).astype(np.uint8), "RGB").convert("RGBA")
    return BG


def frame_at(T):
    global RMASK
    seg = seg_at(T)
    fr = background().copy()
    header(fr, seg, T)
    panel_frame(fr)
    fx = seg["shot"].get("fx")
    if fx in ("montage", "montage2"):
        lst = MONTAGE if fx == "montage" else MONTAGE2
        n = int((T - seg["t0"]) / 0.32) % len(lst)
        key = lst[n]
        cam = (VW / 2, VH / 2, 1.25 + 0.2 * ((T - seg["t0"]) / 0.32 % 1))
    else:
        key = screen_at(seg, T)
        cam = camera(seg, T, key)
    img, vr = draw_screen(key, cam)
    # quick fade between lines with a different screen
    if T - seg["t0"] < 0.12 and seg["i"] > 0 and not fx:
        prev = TL[seg["i"] - 1]
        pk = screen_at(prev, prev["t1"] - 0.01)
        if pk != key:
            pimg, _ = draw_screen(pk, camera(prev, prev["t1"] - 0.01, pk))
            img = Image.blend(pimg, img, (T - seg["t0"]) / 0.12)
    if RMASK is None:
        RMASK = round_mask()
    fr.paste(img, (PX, PY), RMASK)
    pos = cursor_pos(seg, T, key) if not fx else None
    if pos:
        x, y = to_panel(pos, vr)
        if PX < x < PX + PW and PY < y < PY + PH:
            c = cursor_img()
            sc = 0.85 if pressed(seg, T) else 1.0
            ci = c.resize((int(c.width * 0.75 * sc), int(c.height * 0.75 * sc)))
            fr.alpha_composite(ci, (int(x), int(y)))
    ripple(fr, seg, T, vr, pos)
    fx_overlay(fr, seg, T)
    captions(fr, seg, T)
    now_card(fr, seg, T, key)
    chibi(fr, seg, T)
    return fr.convert("RGB")


# ------------------------------------------------------------------ main
def render(out):
    global TL
    TL, total = build_timeline()
    print(f"timeline {total:.1f}s, {len(TL)} lines", flush=True)
    audio = mix_audio(TL, total)
    wav = os.path.join(WORK, "audio.wav")
    sf.write(wav, audio[:int(total * SR)], SR)
    nfr = int(total * FPS)
    chunk = int(os.environ.get("CHUNK", 60 * FPS))
    parts = []
    jobs = int(os.environ.get("JOBS", 1))
    me = int(os.environ.get("JOB", 0))
    for ci, f0 in enumerate(range(0, nfr, chunk)):
        p = os.path.join(WORK, "parts", f"part{ci:03d}.mp4")
        parts.append(p)
        if os.path.exists(p) or ci % jobs != me:
            continue
        os.makedirs(os.path.dirname(p), exist_ok=True)
        tmp = p + ".tmp.mp4"
        enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-framerate", str(FPS), "-i", "-",
                                "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
        for fi in range(f0, min(nfr, f0 + chunk)):
            enc.stdin.write(frame_at(fi / FPS).tobytes())
        enc.stdin.close()
        enc.wait()
        os.replace(tmp, p)
        print(f"part {ci} done", flush=True)
    if me != 0 or not all(os.path.exists(p) for p in parts):
        return
    lst = os.path.join(WORK, "parts.txt")
    open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-i", wav, "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", "-movflags", "+faststart", out], check=True)
    print("wrote", out, flush=True)


def still(T, out):
    global TL
    TL, total = build_timeline()
    frame_at(T).save(out)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "voice":
        import voices
        for sec, line in LINES:
            voices.say(VOICE, line)
    elif cmd == "render":
        render(sys.argv[2])
    elif cmd == "still":
        TL, total = build_timeline()
        for a in sys.argv[3:]:
            frame_at(float(a)).save(f"{sys.argv[2]}_{a}.png")


def sheet(out, cols=8):
    """Contact sheet: one frame from the middle of every line (quick framing check)."""
    global TL
    TL, total = build_timeline()
    ims = [frame_at((s["vs"] + s["ve"]) / 2 + 0.3).resize((270, 480)) for s in TL]
    rows = (len(ims) + cols - 1) // cols
    c = Image.new("RGB", (270 * cols, 480 * rows), "white")
    for i, im in enumerate(ims):
        c.paste(im, ((i % cols) * 270, (i // cols) * 480))
    c.save(out)


if __name__ == "__main__" and sys.argv[1] == "sheet":
    sheet(sys.argv[2])
