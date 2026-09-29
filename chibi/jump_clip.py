"""Jump clip from a pose sheet: cut out each pose, line them up and play them with a real jump arc.

    python chibi/jump_clip.py sheet.png out.mp4 [loops]

The sheet: 8 poses on white in 2 rows (stand, crouch, take-off, rising, peak, wink, falling, landing). Each pose is
cut out (the white paper around it made see-through), anchored on her shirt (so the body doesn't jitter between
drawings) and placed on a jump curve; a shadow shrinks as she rises, with a squash on landing and a boing / thud.
"""
import os
import subprocess
import sys
import tempfile

import cv2
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw

W, H, FPS, SR = 1080, 1920, 24, 24000
FLOOR = 1500
SCALE = 2.2
# (pose index, frames, lift px, squash) - lift = how high her feet are off the floor
TIMELINE = [(0, 10, 0, 1.0), (1, 5, 0, 1.0), (2, 3, 70, 1.0), (3, 3, 230, 1.0), (4, 6, 380, 1.0), (5, 5, 360, 1.0),
            (6, 3, 200, 1.0), (7, 2, 0, 0.93), (7, 3, 0, 1.0), (0, 8, 0, 1.0)]


def poses(path):
    a = cv2.imread(path)
    ink = (a.astype(int).sum(2) < 690).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(cv2.dilate(ink, np.ones((15, 15), np.uint8)))
    ids = sorted([i for i in range(1, n) if st[i, 4] > 5000], key=lambda i: st[i, 4], reverse=True)[:8]
    ids.sort(key=lambda i: (st[i, 1] > a.shape[0] / 2, st[i, 0]))                  # row by row, left to right
    out = []
    for i in ids:
        x, y, w, h = st[i, :4]
        crop = a[y:y + h, x:x + w]
        region = (lab[y:y + h, x:x + w] == i)
        # paper = near-white connected to the crop border; everything else is her
        white = (crop.astype(int).min(2) > 225).astype(np.uint8)
        ff = white.copy()
        mask = np.zeros((h + 2, w + 2), np.uint8)
        for px, py in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
            if ff[py, px]:
                cv2.floodFill(ff, mask, (px, py), 2)
        alpha = ((ff != 2) & region).astype(np.float32)
        alpha = cv2.GaussianBlur(alpha, (0, 0), 0.8)
        rgba = np.dstack([cv2.cvtColor(crop, cv2.COLOR_BGR2RGB), (alpha * 255).astype(np.uint8)])
        shirt = (crop.astype(int).max(2) < 70) & (alpha > .5)                      # her black tee
        ys, xs = np.nonzero(shirt)
        feet = np.nonzero(alpha.max(1) > .5)[0].max()
        out.append(dict(img=Image.fromarray(rgba, "RGBA"), anchor=(xs.mean(), ys.mean()), feet=feet))
    return out


def background():
    g = np.linspace(0, 1, H)[:, None, None]
    top, bot = np.array((255, 228, 238))[None, None], np.array((255, 190, 212))[None, None]
    im = Image.fromarray((top * (1 - g) + bot * g).repeat(W, 1).astype(np.uint8), "RGB").convert("RGBA")
    d = ImageDraw.Draw(im)
    d.rectangle((0, FLOOR + 40, W, H), fill=(245, 170, 196))
    return im


def sound(total, events):
    t = np.arange(int(total * SR)) / SR
    out = np.zeros(len(t), np.float32)
    for kind, at in events:
        i = int(at * SR)
        x = np.arange(int(.5 * SR)) / SR
        if kind == "boing":
            s = np.sin(2 * np.pi * (180 * x + 900 * x * x)) * np.exp(-x / .2) * .35
        else:
            s = np.sin(2 * np.pi * 70 * x) * np.exp(-x / .08) * .6 + np.random.default_rng(1).normal(0, 1, len(x)) * np.exp(-x / .02) * .1
        out[i:i + len(s)] += s[:len(out) - i].astype(np.float32)
    return out


def render(sheet, out, loops=3):
    P = poses(sheet)
    feet_to_shirt = np.median([p["feet"] - p["anchor"][1] for p in (P[0], P[1], P[7])])   # on-floor poses
    bg = background()
    frames, events, T = [], [], 0.0
    for _ in range(loops):
        for idx, n, lift, squash in TIMELINE:
            if idx == 2:
                events.append(("boing", T))
            if idx == 7 and squash < 1:
                events.append(("thud", T))
            frames += [(idx, lift, squash)] * n
            T += n / FPS
    total = len(frames) / FPS
    with tempfile.TemporaryDirectory() as d:
        wav = os.path.join(d, "a.wav")
        sf.write(wav, sound(total, events), SR)
        enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                                "-framerate", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-pix_fmt", "yuv420p",
                                "-crf", "18", "-c:a", "aac", "-shortest", out], stdin=subprocess.PIPE)
        for idx, lift, squash in frames:
            p = P[idx]
            im = bg.copy()
            d = ImageDraw.Draw(im)
            k = max(0.35, 1 - lift / 520)                                       # shadow shrinks as she rises
            d.ellipse((W / 2 - 170 * k, FLOOR + 10 - 26 * k, W / 2 + 170 * k, FLOOR + 10 + 26 * k), fill=(226, 140, 172))
            w, h = p["img"].size
            sw, sh = int(w * SCALE / squash ** .5), int(h * SCALE * squash)
            spr = p["img"].resize((sw, sh), Image.LANCZOS)
            ax, ay = p["anchor"][0] * sw / w, p["anchor"][1] * sh / h
            if lift == 0:                                                        # on the ground: feet on the floor
                top = FLOOR - p["feet"] * sh / h
            else:                                                                # in the air: her body follows the arc
                top = FLOOR - lift - feet_to_shirt * SCALE * squash - ay
            im.alpha_composite(spr, (int(W / 2 - ax), int(top)))
            enc.stdin.write(im.convert("RGB").tobytes())
        enc.stdin.close()
        enc.wait()
    print("wrote", out, f"({total:.1f} s)")


if __name__ == "__main__":
    render(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 3)
