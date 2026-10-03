"""Test video for the realistic (painted) her, built from her sheets (1080x1920, ~25 s):

  A. close-up talking to camera: one base face (viseme 1) + only the mouth/chin area swapped per sound (Rhubarb),
     soft-blended, so hair and eyes never flicker; a slow push-in and a little head sway.
  B. wide shot: she walks across the screen, small, using the side-view walk frames (cut off the white paper).
  C. mid shot: the green-screen "thinking" pose (keyed) while the voice-over asks the question.
  D. back to the close-up for the last line.

    python real/test_video.py out.mp4
"""
import glob
import math
import os
import subprocess
import sys
import tempfile

import cv2
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", "skits"), os.path.join(HERE, "..", "chibi")]
import voices                                           # noqa: E402
import video_321 as V                                   # noqa: E402  (Rhubarb helpers)
from five_min import ogg                                # noqa: E402

W, H, FPS, SR = 1080, 1920, 24, voices.SR
SCR = "/tmp/claude-0/-home-user-Test/6a6db2ec-de51-5be8-8073-4c5206a96107/scratchpad"
VIS = os.path.join(SCR, "real", "vis")
UP = "/root/.claude/uploads/6a6db2ec-de51-5be8-8073-4c5206a96107"
WALK_SHEET = os.path.join(UP, "7fab9c9c-image.png")
THINK = os.path.join(UP, "4cfb2ba0-image.png")
VOICE = "af_bella"
LINES = {   # already made for the Roth video (cached)
    "A": "[sassy] Roth IRA or traditional IRA? Pick wrong and you're basically tipping the IRS. For thirty years.",
    "B": "[calm] Okay, here's the whole thing in one sentence. You pay the tax now, or you pay it later.",
    "C": "[calm] So the only real question is, will your tax rate be higher now, or later?",
    "D": "[sassy] And here's what nobody tells you. If your tax rate is the same now and later, they come out exactly the same.",
}
# Rhubarb mouth shapes -> viseme tiles (1 rest, 2 MBP, 3 A, 4 AA, 5 E, 6 I, 7 O, 8 OO, 9 FV, 10 L, 11 TH, 12 SH)
RHUBARB_TO_VIS = {"X": 1, "A": 2, "B": 6, "C": 5, "D": 3, "E": 7, "F": 8, "G": 9, "H": 10}
BG_TOP, BG_BOT = (255, 226, 234), (246, 196, 212)


def ease(t):
    return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, t)))


def backdrop(w=W, h=H):
    g = np.linspace(0, 1, h)[:, None, None]
    return (np.array(BG_TOP) * (1 - g) + np.array(BG_BOT) * g).repeat(w, 1).astype(np.float32)


# ------------------------------------------------------------------ A/D: talking close-up
def load_faces():
    files = sorted(glob.glob(os.path.join(VIS, "v??_*.png")))
    tiles = [cv2.cvtColor(cv2.imread(f), cv2.COLOR_BGR2RGB).astype(np.float32) for f in files]
    h, w = tiles[0].shape[:2]
    tiles = [t[:h - 100, 12:w - 12] for t in tiles]                       # cut off label text / grid lines
    h, w = tiles[0].shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy, rx, ry = w * 0.5, h * 0.46, w * 0.25, h * 0.12               # mouth (corners too) + chin
    d = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
    mask = np.clip((1.3 - d) / 0.3, 0, 1)[..., None]                     # soft edge
    base = tiles[0]
    faces = []
    for t in tiles:
        ring = (mask[..., 0] > 0.05) & (mask[..., 0] < 0.5)
        t = t + (base[ring].mean(0) - t[ring].mean(0))                    # match skin tone at the blend edge
        faces.append(base * (1 - mask) + t * mask)
    # white paper -> her backdrop (her edges are dark hair, so brightness is a good matte)
    out = []
    bg = None
    for f in faces:
        lum = f.min(2)
        alpha = np.clip((250 - lum) / 22, 0, 1)[..., None]
        alpha = cv2.GaussianBlur(alpha, (0, 0), 1.2)[..., None]
        if bg is None:
            bg = backdrop(f.shape[1], f.shape[0])
        out.append(np.clip(f * alpha + bg * (1 - alpha), 0, 255).astype(np.uint8))
    return out


def closeup(face, t, dur):
    h, w = face.shape[:2]
    z = 1.0 + 0.06 * ease(t / dur)                                       # slow push in
    ang = 0.8 * math.sin(t * 1.3)                                        # little head sway
    scale = H / h * 1.04 * z
    M = cv2.getRotationMatrix2D((w / 2, h * 0.62), ang, scale)
    M[0, 2] += W / 2 - w / 2
    M[1, 2] += H * 0.47 - h * 0.62 + (1 - scale) * 0 + 6 * math.sin(t * 2.1)
    return cv2.warpAffine(face, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


# ------------------------------------------------------------------ B: walk across
WALK_PICK = [2, 3, 6, 7]          # the side-view frames of the turnaround/walk sheet (0-7), in stepping order


def walk_frames(pick=True):
    a = cv2.cvtColor(cv2.imread(WALK_SHEET), cv2.COLOR_BGR2RGB)
    h = a.shape[0]
    frames = _figures(a[:h // 2]) + _figures(a[h // 2:])
    return [frames[i] for i in WALK_PICK] if pick else frames


_session = None


def matte(rgb):
    """Her cut out of the white paper with an AI matting model (keeps the white sneakers)."""
    global _session
    from rembg import new_session, remove
    if _session is None:
        _session = new_session("isnet-general-use")
    return np.array(remove(Image.fromarray(rgb), session=_session))[..., 3]


def _figures(row):
    ink = (row.min(2) < 225).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(cv2.dilate(ink, np.ones((5, 5), np.uint8)))
    big = sorted([i for i in range(1, n) if st[i, 4] > 20000], key=lambda i: st[i, 0])
    frames = []
    for i in big:
        x0, y0, w, h = st[i, :4]
        pad = 20
        xa, ya = max(0, x0 - pad), max(0, y0 - pad)
        crop = row[ya:y0 + h + pad, xa:x0 + w + pad].copy()
        region = cv2.dilate((lab[ya:y0 + h + pad, xa:x0 + w + pad] == i).astype(np.uint8), np.ones((25, 25), np.uint8))
        alpha = (matte(crop).astype(np.float32) * region).astype(np.uint8)       # only this figure, not a neighbour's foot
        ys, xs = np.nonzero(alpha > 20)
        frames.append(np.dstack([crop, alpha])[ys.min():ys.max() + 1, xs.min():xs.max() + 1])
    return frames


def street(t):
    """A soft, out-of-focus city backdrop so the painted figure sits in it (bokeh lights, sidewalk)."""
    im = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(im)
    for y in range(H):
        k = y / H
        d.line((0, y, W, y), fill=(int(250 - 60 * k), int(214 - 70 * k), int(222 - 40 * k)))
    rng = np.random.default_rng(4)
    for i in range(40):
        x = (rng.uniform(0, W * 1.6) - t * 40) % (W * 1.6) - 200
        y, r = rng.uniform(300, 1150), rng.uniform(25, 70)
        c = [(255, 236, 190), (255, 200, 220), (220, 220, 255)][i % 3]
        d.ellipse((x - r, y - r, x + r, y + r), fill=c)
    im = im.filter(ImageFilter.GaussianBlur(10))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 1420, W, H), fill=(214, 190, 200))
    d.line((0, 1420, W, 1420), fill=(190, 160, 172), width=6)
    return np.array(im).astype(np.float32)


def paste(dst, rgba, x, y, scale):
    h, w = rgba.shape[:2]
    rgba = cv2.resize(rgba, (max(1, int(w * scale)), max(1, int(h * scale))), interpolation=cv2.INTER_AREA)
    h, w = rgba.shape[:2]
    x0, y0 = int(x), int(y)
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if xa >= xb or ya >= yb:
        return
    s = rgba[ya - y0:yb - y0, xa - x0:xb - x0].astype(np.float32)
    a = s[..., 3:] / 255
    dst[ya:yb, xa:xb] = dst[ya:yb, xa:xb] * (1 - a) + s[..., :3] * a


# ------------------------------------------------------------------ C: green-screen pose
def keyed(path):
    a = cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2RGB).astype(np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    green = g - np.maximum(r, b)
    alpha = np.clip(1 - (green - 40) / 60, 0, 1)
    a[..., 1] = np.minimum(g, np.maximum(r, b) + 12)                     # remove green spill on hair edges
    return np.dstack([a, alpha * 255]).astype(np.uint8)


# ------------------------------------------------------------------ build
def render(out):
    faces = load_faces()
    walk = walk_frames()
    think = keyed(THINK)
    tmp = tempfile.mkdtemp()
    plan, t = [], 0.3
    audio = np.zeros(int(60 * SR), np.float32)
    for key in "ABCD":
        a = voices.say(VOICE, LINES[key])
        p = os.path.join(tmp, f"{key}.wav")
        sf.write(p, a, SR)
        cues = [(t + s, c) for s, c in V.mouth_cues(p, LINES[key].split("] ", 1)[1])] if key in "AD" else []
        audio[int(t * SR):int(t * SR) + len(a)] += a
        plan.append(dict(key=key, t0=t - (0.3 if key == "A" else 0), t1=t + len(a) / SR, cues=cues))
        t += len(a) / SR + (0.9 if key == "B" else 0.35)
    total = t + 0.6
    plan[-1]["t1"] = total
    for i in range(len(plan) - 1):
        plan[i]["t1"] = plan[i + 1]["t0"]
    n = int(total * SR)
    audio = voices.clarity(audio[:n])
    b = plan[1]
    for k, st in enumerate(np.arange(b["t0"] + 0.2, b["t1"], 0.36)):     # footsteps while she walks
        s = ogg(f"footstep_concrete_00{k % 4}", 0.5)
        i = int(st * SR)
        audio[i:i + len(s)] += s[:max(0, n - i)]
    audio = audio / max(1.0, np.abs(audio).max() / 0.95)
    with tempfile.TemporaryDirectory() as d:
        wav = os.path.join(d, "a.wav")
        sf.write(wav, audio, SR)
        enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                                "-framerate", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-pix_fmt", "yuv420p",
                                "-crf", "18", "-c:a", "aac", "-b:a", "192k", "-shortest", out], stdin=subprocess.PIPE)
        for fi in range(int(total * FPS)):
            T = fi / FPS
            p = next(x for x in plan if x["t0"] <= T < x["t1"] or x is plan[-1])
            t = T - p["t0"]
            if p["key"] in "AD":
                v = 1
                for s, c in p["cues"]:
                    if s <= T:
                        v = RHUBARB_TO_VIS.get(c, 1)
                frame = closeup(faces[v - 1], t, p["t1"] - p["t0"])
            elif p["key"] == "B":
                frame = street(t)
                dur = p["t1"] - p["t0"]
                fr = walk[int(t * 8) % len(walk)]
                sc = 520 / fr.shape[0]
                x = -250 + (W + 300) * t / dur
                paste(frame, fr, x - fr.shape[1] * sc / 2, 1440 - fr.shape[0] * sc, sc)
                frame = frame.astype(np.uint8)
            else:
                frame = backdrop()
                z = 1.0 + 0.05 * ease(t / (p["t1"] - p["t0"]))
                sc = H * 1.35 / think.shape[0] * z
                paste(frame, think, W / 2 - think.shape[1] * sc / 2, H * 0.06 - 40 * z, sc)
                frame = frame.astype(np.uint8)
            enc.stdin.write(np.ascontiguousarray(frame).tobytes())
        enc.stdin.close()
        enc.wait()
    print("wrote", out, f"({total:.1f} s)")


if __name__ == "__main__":
    render(sys.argv[1] if len(sys.argv) > 1 else "real_test.mp4")
