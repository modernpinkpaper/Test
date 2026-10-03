"""The 3-2-1 rule as a b-roll TikTok (1080x1920): her Midjourney clips cut into segments, the cloned voice as a
voice-over (no lip-sync), and text graphics in her colours (black tee, denim, warm brown, cream). No emoji.

    python chibi/broll_321.py CLIPS_DIR out.mp4

CLIPS_DIR holds c01.mp4 ... c15.mp4 (her Midjourney clips; not in the repo). Every segment is checked with the
MediaPipe face landmarker: a frame is only used if her lips are closed (mouth gap < MOUTH_MAX of the face height),
with MOUTH_MARGIN seconds of safety around any frame where they part.
"""
import math
import os
import subprocess
import sys
import tempfile

import cv2
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw

import video_321 as V

W, H, FPS, SR = V.W, V.H, 24, V.SR
MOUTH_MAX, MOUTH_MARGIN = 0.012, 0.3
INK, DENIM, SKY, BROWN = (24, 22, 24), (47, 84, 140), (160, 184, 220), (138, 84, 55)
CREAM = (255, 251, 245)
LINES = [b[0] for b in V.BEATS]
HOT = [b[5] for b in V.BEATS]
KINDS = ["stop", "title", "protein", "water", "walk", "streak"]
# per line: clip, start (s), zoom (1 = whole height, white sides), vertical focus (0 top .. 1 bottom)
SHOTS = [("c10", 0.0, 1.0, 0.5),       # standing, hand to pocket
         ("c04", 0.4, 1.0, 0.5),       # turns around
         ("c01", 2.4, 1.52, 0.35),     # sits down on the couch
         ("c05", 0.8, 1.0, 0.5),       # turns, looks over her shoulder
         ("c12", 0.0, 1.0, 0.45),      # walks towards you
         ("c02", 8.6, 1.52, 0.3)]      # close-up, turns to you


# ------------------------------------------------------------------ mouth check
_det = None


def mouth_gaps(frames):
    """Lip gap / face height per frame (None when no face is seen, e.g. from behind)."""
    global _det
    import mediapipe as mp
    from mediapipe.tasks import python as mpt
    from mediapipe.tasks.python import vision
    model = os.path.join(os.path.dirname(__file__), "..", "demo_videos", "models", "face_landmarker.task")
    det = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
        base_options=mpt.BaseOptions(model_asset_path=model), running_mode=vision.RunningMode.VIDEO, num_faces=1))
    out = []
    for i, im in enumerate(frames):
        r = det.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(im, cv2.COLOR_BGR2RGB)),
                                 int(i * 1000 / FPS))
        if r.face_landmarks:
            L = r.face_landmarks[0]
            out.append(abs(L[13].y - L[14].y) / max(abs(L[10].y - L[152].y), 1e-6))
        else:
            out.append(None)
    return out


def load_clip(path):
    cap, frames = cv2.VideoCapture(path), []
    while True:
        ok, im = cap.read()
        if not ok:
            return frames
        frames.append(im)


def safe_mask(gaps):
    bad = np.array([g is not None and g > MOUTH_MAX for g in gaps])
    m = int(MOUTH_MARGIN * FPS)
    grown = np.convolve(bad.astype(int), np.ones(2 * m + 1, int), "same") > 0
    return ~grown


# ------------------------------------------------------------------ framing
def frame_to_canvas(im, zoom, focus, t_rel):
    """Scale a clip frame into 1080x1920: zoom 1 fits her height (sides padded with the clip's own white), more zoom
    fills and crops. A slow push-in keeps it alive."""
    h, w = im.shape[:2]
    z = zoom * (1 + 0.025 * t_rel)
    s = H / h * z
    big = cv2.resize(im, (int(w * s), int(h * s)), interpolation=cv2.INTER_CUBIC)
    edge = np.median(np.r_[im[:, :3].reshape(-1, 3), im[:, -3:].reshape(-1, 3)], 0).astype(np.uint8)
    canvas = np.empty((H, W, 3), np.uint8)
    canvas[:] = edge
    bh, bw = big.shape[:2]
    y0 = int(max(0, (bh - H) * focus))
    x0 = (bw - W) // 2
    if x0 >= 0:
        canvas[:] = big[y0:y0 + H, x0:x0 + W][:H]
    else:                              # narrower than the screen: centre it, soften the seam into the padding
        crop = big[y0:y0 + H]
        xs = -x0
        canvas[:crop.shape[0], xs:xs + bw] = crop
        for k in range(24):
            a = k / 24
            for x in (xs + k, xs + bw - 1 - k):
                canvas[:, x] = (canvas[:, x] * a + edge * (1 - a)).astype(np.uint8)
    return Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)).convert("RGBA")


# ------------------------------------------------------------------ text graphics
font, ease, pop = V.font, V.ease, V.pop


def txt(d, xy, s, size, fill=INK, weight=800, anchor="mm"):
    if size >= 4:
        d.text(xy, s, font=font(int(size), weight), fill=fill, anchor=anchor)


def pill(d, cx, cy, s, size, bg=INK, fg=CREAM, k=1.0, pad=(34, 16)):
    if k <= 0.02:
        return
    f = font(int(size * k))
    w = f.getlength(s)
    d.rounded_rectangle((cx - w / 2 - pad[0] * k, cy - size * k * .62 - pad[1] * k, cx + w / 2 + pad[0] * k,
                         cy + size * k * .62 + pad[1] * k), int(40 * k), fill=bg)
    d.text((cx, cy), s, font=f, fill=fg, anchor="mm")


def card(layer, box, k):
    if k <= 0.02:
        return
    x0, y0, x1, y1 = box
    cy = (y0 + y1) / 2
    hh = (y1 - y0) / 2 * min(k, 1.08)
    ImageDraw.Draw(layer).rounded_rectangle((x0, cy - hh, x1, cy + hh), 44, fill=CREAM + (238,), outline=INK, width=5)


def numeral(d, cx, cy, n, k):
    r = 70 * k
    if r > 2:
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=DENIM)
        txt(d, (cx, cy + 4), n, 92 * k, fill=CREAM)


def check(d, cx, cy, k, size=34):
    d.rounded_rectangle((cx - size, cy - size, cx + size, cy + size), 12, outline=INK, width=5)
    if k > 0:
        pts = [(cx - 18, cy + 2), (cx - 4, cy + 17), (cx + 22, cy - 18)]
        seg = min(k * 2, 1)
        d.line([pts[0], (pts[0][0] + (pts[1][0] - pts[0][0]) * seg, pts[0][1] + (pts[1][1] - pts[0][1]) * seg)],
               fill=DENIM, width=9)
        if k > .5:
            s2 = (k - .5) * 2
            d.line([pts[1], (pts[1][0] + (pts[2][0] - pts[1][0]) * s2, pts[1][1] + (pts[2][1] - pts[1][1]) * s2)],
                   fill=DENIM, width=9)


def graphic(canvas, kind, t, dur):
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx = W // 2
    if kind == "stop":
        k = pop(t)
        pill(d, cx, 1240, "STOP", 150, k=k)
        k2 = pop(t - .35)
        pill(d, cx, 1420, "starving yourself", 72, bg=CREAM, fg=INK, k=k2)
        if t > .8:                                       # a line striking through "starving yourself"
            p = ease((t - .8) / .35)
            wd = font(72).getlength("starving yourself") / 2 + 20
            d.line((cx - wd, 1422, cx - wd + 2 * wd * p, 1422), fill=DENIM, width=12)
    elif kind == "title":
        txt(d, (cx, 1150), "THE", 64 * pop(t), fill=INK, weight=600)
        for i, n in enumerate("321"):
            ki = pop(t - .2 - .2 * i)
            x = cx + (i - 1) * 230
            if ki > .02:
                d.rounded_rectangle((x - 95 * ki, 1320 - 110 * ki, x + 95 * ki, 1320 + 110 * ki), 36,
                                    fill=INK if i != 1 else DENIM)
                txt(d, (x, 1325), n, 170 * ki, fill=CREAM)
        pill(d, cx, 1530, "RULE", 84, bg=CREAM, fg=INK, k=pop(t - .9))
    elif kind == "protein":
        card(layer, (100, 1080, W - 100, 1640), pop(t, .3))
        numeral(d, 230, 1175, "3", pop(t - .15))
        txt(d, (330, 1150), "PROTEIN", 80 * pop(t - .25), anchor="lm")
        txt(d, (334, 1222), "at every meal", 44 * pop(t - .35), fill=BROWN, weight=600, anchor="lm")
        for i, meal in enumerate(("BREAKFAST", "LUNCH", "DINNER")):
            ki = pop(t - .8 - .45 * i)
            y = 1340 + i * 100
            if ki > .05:
                txt(d, (200, y), meal, 58 * ki, weight=600, anchor="lm")
                check(d, W - 220, y, ease((t - 1.1 - .45 * i) / .35))
    elif kind == "water":
        card(layer, (100, 1080, W - 100, 1640), pop(t, .3))
        numeral(d, 230, 1175, "2", pop(t - .15))
        txt(d, (330, 1150), "BOTTLES", 80 * pop(t - .25), anchor="lm")
        txt(d, (334, 1222), "of water a day", 44 * pop(t - .35), fill=BROWN, weight=600, anchor="lm")
        for i in range(2):
            x = cx + (i - .5) * 280
            top, bot = 1330, 1590
            fill = ease((t - .7 - .6 * i) / 1.1)
            d.rounded_rectangle((x - 60, top, x + 60, bot), 30, outline=INK, width=6, fill=(255, 255, 255))
            d.rounded_rectangle((x - 24, top - 30, x + 24, top + 2), 8, fill=INK)
            if fill > .02:
                lv = bot - 8 - fill * (bot - top - 26)
                d.rounded_rectangle((x - 52, lv, x + 52, bot - 8), 24, fill=SKY)
                d.rectangle((x - 52, lv, x + 52, min(lv + 10, bot - 8)), fill=DENIM)
    elif kind == "walk":
        card(layer, (100, 1080, W - 100, 1640), pop(t, .3))
        numeral(d, 230, 1175, "1", pop(t - .15))
        txt(d, (330, 1150), "WALK", 80 * pop(t - .25), anchor="lm")
        txt(d, (334, 1222), "every single day", 44 * pop(t - .35), fill=BROWN, weight=600, anchor="lm")
        p = ease((t - .5) / max(dur - .9, .5))
        r, ry = 150 * pop(t - .3), 1440
        if r < 20:
            canvas.alpha_composite(layer)
            return
        d.ellipse((cx - r, ry - r, cx + r, ry + r), outline=(228, 224, 218), width=30)
        if p > .005:
            d.arc((cx - r, ry - r, cx + r, ry + r), -90, -90 + 360 * p, fill=DENIM, width=30)
        txt(d, (cx, ry - 12), f"{int(round(30 * p))}", 110, fill=INK)
        txt(d, (cx, ry + 62), "MINUTES", 34, fill=BROWN, weight=600)
    elif kind == "streak":
        card(layer, (100, 1060, W - 100, 1660), pop(t, .3))
        txt(d, (cx, 1140), "SMALL HABITS.", 70 * pop(t - .15), fill=INK)
        txt(d, (cx, 1220), "BIG RESULTS.", 70 * pop(t - .35), fill=DENIM)
        for i in range(7):
            ki = ease((t - .6 - .15 * i) / .35)
            h = (60 + 30 * i) * ki
            x = 225 + i * 105
            if h > 1:
                d.rounded_rectangle((x - 34, 1560 - h, x + 34, 1560), 14, fill=DENIM if i == 6 else SKY)
            txt(d, (x, 1600), "MTWTFSS"[i], 32, fill=BROWN, weight=600)
    canvas.alpha_composite(layer)


def captions(canvas, words, t, hot):
    """Word-by-word captions in a black band: 3 words at a time, key words in denim blue on cream."""
    said = [i for i, (_, st) in enumerate(words) if st <= t]
    if not said:
        return
    c0 = said[-1] // 3 * 3
    chunk = words[c0:c0 + 3]
    n = said[-1] - c0 + 1
    size = 64
    f = font(size)
    widths = [f.getlength(w.upper()) for w, _ in chunk]
    gap = 22
    total = sum(widths) + gap * (len(chunk) - 1)
    while total > 900:
        size -= 4
        f = font(size)
        widths = [f.getlength(w.upper()) for w, _ in chunk]
        total = sum(widths) + gap * (len(chunk) - 1)
    d = ImageDraw.Draw(canvas)
    y = 1760
    x = W / 2 - total / 2
    for i, ((w, _), wd) in enumerate(zip(chunk, widths)):
        if i < n:
            key = w.lower() in hot
            d.rounded_rectangle((x - 14, y - size * .66, x + wd + 14, y + size * .66), 18, fill=CREAM if key else INK)
            d.text((x, y), w.upper(), font=f, fill=DENIM if key else CREAM, anchor="lm")
        x += wd + gap


# ------------------------------------------------------------------ build
def plan():
    t, beats, audio = 0.4, [], [np.zeros(int(0.4 * SR), np.float32)]
    for line, hot in zip(LINES, HOT):
        a = V.voice(line)
        dur = len(a) / SR
        words = line.split()
        lens = np.array([len(w) + 2 for w in words], float)
        starts = t + dur * 0.92 * np.r_[0, np.cumsum(lens)[:-1]] / lens.sum()
        beats.append(dict(t0=t, t1=t + dur, words=list(zip(words, starts)), hot={w.lower() for w in hot}))
        audio += [a, np.zeros(int(V.GAP * SR), np.float32)]
        t += dur + V.GAP
    audio.append(np.zeros(int(0.7 * SR), np.float32))
    return beats, np.concatenate(audio), t + 0.7


def render(clips_dir, out):
    beats, audio, total = plan()
    # shot i runs from (line i start - 0.3) to (line i+1 start - 0.3)
    bounds = [0.0] + [b["t0"] - 0.3 for b in beats[1:]] + [total]
    shots = []
    for i, (clip, start, zoom, focus) in enumerate(SHOTS):
        frames = load_clip(os.path.join(clips_dir, clip + ".mp4"))
        n = int(round((bounds[i + 1] - bounds[i]) * FPS)) + 2
        f0 = int(start * FPS)
        use = frames[f0:f0 + n]
        if len(use) < n:
            raise SystemExit(f"{clip}: only {len(use)} frames from {start}s, need {n}")
        ok = safe_mask(mouth_gaps(frames))[f0:f0 + n]
        if not ok.all():
            raise SystemExit(f"{clip} {start}s: her mouth opens in this segment (frames {np.where(~ok)[0] + f0})")
        shots.append((use, zoom, focus))
        print(f"shot {i + 1}: {clip} {start:.2f}-{start + n / FPS:.2f}s  mouth closed in all {n} frames")
    for b in beats:
        s = V.sfx(0.35, "whoosh") * 0.6
        j = int(max(b["t0"] - 0.35, 0) * SR)
        audio[j:j + len(s)] += s[:len(audio) - j]
    with tempfile.TemporaryDirectory() as d:
        wav = os.path.join(d, "a.wav")
        sf.write(wav, np.clip(audio, -1, 1), SR)
        for fi in range(int(total * FPS)):
            t = fi / FPS
            i = max(k for k in range(len(SHOTS)) if bounds[k] <= t)
            frames, zoom, focus = shots[i]
            rel = t - bounds[i]
            canvas = frame_to_canvas(frames[min(int(rel * FPS), len(frames) - 1)], zoom, focus, rel)
            if i > 0 and rel < 0.12:                  # a quick dip through white between shots
                a = 1 - rel / 0.12
                canvas = Image.blend(canvas, Image.new("RGBA", canvas.size, (255, 255, 255, 255)), a * .55)
            b = beats[i]
            graphic(canvas, KINDS[i], t - (b["t0"] - 0.15), b["t1"] - b["t0"])
            if b["t0"] <= t <= b["t1"] + 0.3:
                captions(canvas, b["words"], t, b["hot"])
            canvas.convert("RGB").save(os.path.join(d, f"f{fi:04d}.png"))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(d, "f%04d.png"),
                        "-i", wav, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "19", "-c:a", "aac", "-b:a", "160k",
                        "-shortest", out], check=True)
    print("wrote", out, f"({total:.1f} s)")


if __name__ == "__main__":
    render(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "broll_321.mp4")
