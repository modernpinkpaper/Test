"""The grazing clip, remade two ways (1080x1920): her voice line (cloned with Chatterbox from her own sample),
the chibi girl lip-syncing on her scenes, her Midjourney girl as b-roll (closed-mouth frames only), text graphics
in her colours and word-by-word captions. The quote is Liv Schmidt's (credited on the end card).

    python chibi/video_grazing.py CLIPS_DIR A out_a.mp4      # chibi leads, Midjourney girl cut in
    python chibi/video_grazing.py CLIPS_DIR B out_b.mp4      # Midjourney girl leads, chibi pops in
"""
import io
import json
import os
import subprocess
import sys
import tempfile

import cairosvg
import cv2
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw

import broll_321 as BR
import chibi_expressions as X
import chibi_hair as CH
import video_321 as V

W, H, FPS, SR = 1080, 1920, 24, V.SR
INK, DENIM, SKY, BROWN, CREAM = BR.INK, BR.DENIM, BR.SKY, BR.BROWN, BR.CREAM
LINE = "Mindlessly grazing on snacks is giving farm animal. Not sheep, cool girl. Like, babe, it's giving... it's giving farm animal."
VO = 1.3                     # voice starts here (the hook plays first)
font, ease, pop = V.font, V.ease, V.pop
HOT = {"mindlessly", "grazing", "farm", "animal.", "sheep,", "babe,"}


# ------------------------------------------------------------------ helpers
def txt(d, xy, s, size, fill=INK, weight=800, anchor="mm"):
    if size >= 4:
        d.text(xy, s, font=font(int(size), weight), fill=fill, anchor=anchor)


def pill(d, cx, cy, s, size, bg=INK, fg=CREAM, k=1.0, pad=(34, 16), angle=0):
    BR.pill(d, cx, cy, s, size, bg=bg, fg=fg, k=k, pad=pad)


def cream_bg():
    g = np.linspace(0, 1, H)[:, None, None]
    top, bot = np.array((255, 252, 247))[None, None], np.array((246, 236, 226))[None, None]
    return Image.fromarray((top * (1 - g) + bot * g).repeat(W, 1).astype(np.uint8), "RGB").convert("RGBA")


def chibi(expr, pose, tilt=0.0, bob=0.0, height=1100):
    return V.character_png(expr, pose, tilt, bob, height)


def clip_boxed(canvas, im, cx, cy, height, feather=40):
    """A clip frame scaled to `height`, centred at (cx, cy), its white background feathered into the canvas."""
    h, w = im.shape[:2]
    s = height / h
    fr = cv2.resize(im, (int(w * s), int(h * s)), interpolation=cv2.INTER_CUBIC)
    rgba = Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)).convert("RGBA")
    a = np.full(fr.shape[:2], 255, np.float32)
    for k in range(feather):
        v = 255 * k / feather
        a[k, :] = np.minimum(a[k, :], v); a[-1 - k, :] = np.minimum(a[-1 - k, :], v)
        a[:, k] = np.minimum(a[:, k], v); a[:, -1 - k] = np.minimum(a[:, -1 - k], v)
    rgba.putalpha(Image.fromarray(a.astype(np.uint8)))
    canvas.alpha_composite(rgba, (int(cx - rgba.width / 2), int(cy - rgba.height / 2)))


def white_bg(im):
    edge = np.median(np.r_[im[:, :3].reshape(-1, 3), im[:, -3:].reshape(-1, 3)], 0).astype(np.uint8)
    return Image.new("RGBA", (W, H), tuple(int(v) for v in edge[::-1]) + (255,))


# ------------------------------------------------------------------ text graphics
def hook(canvas, t):
    d = ImageDraw.Draw(canvas)
    pill(d, W // 2, 260, "STOP GRAZING.", 96, k=pop(t))
    txt(d, (W // 2, 390), "(yes, you. with the snack drawer.)", 44 * pop(t - .3), fill=BROWN, weight=600)


SNACKS = [("a handful of chips", 0.2), ("\"just one\" cookie", 0.55), ("the kids' leftovers", 0.9), ("another handful", 1.25)]


def snack_list(canvas, t, top=170):
    """The snacks pile up, each crossed out."""
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    k = pop(t, .3)
    if k > .02:
        d.rounded_rectangle((110, top, W - 110, top + 520), 44, fill=CREAM + (240,), outline=INK, width=5)
        txt(d, (W // 2, top + 80), "MINDLESS GRAZING", 70 * k)
    for i, (s, at) in enumerate(SNACKS):
        ki = pop(t - at)
        y = top + 185 + i * 88
        if ki > .05:
            txt(d, (170, y), s, 52 * ki, weight=600, anchor="lm")
            p = ease((t - at - .35) / .25)
            if p > 0:
                wd = font(52, 600).getlength(s)
                d.line((160, y + 2, 160 + (wd + 20) * p, y + 2), fill=DENIM, width=8)
    canvas.alpha_composite(layer)


def stamp(canvas, t, text="FARM ANIMAL.", cy=330, size=150, bg=INK):
    """A big word slamming in (slightly rotated)."""
    k = pop(t, .25)
    if k <= .02:
        return
    f = font(int(size * (2.2 - 1.2 * min(k, 1))))
    w = f.getlength(text)
    layer = Image.new("RGBA", (int(w + 120), int(size * 2.6)), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle((0, size * .3, w + 120, size * 2.3), 40, fill=bg + (int(255 * min(k, 1)),))
    d.text(((w + 120) / 2, size * 1.3), text, font=f, fill=CREAM, anchor="mm")
    layer = layer.rotate(-4, expand=True, resample=Image.BICUBIC)
    if layer.width > W - 40:
        s = (W - 40) / layer.width
        layer = layer.resize((int(layer.width * s), int(layer.height * s)), Image.LANCZOS)
    canvas.alpha_composite(layer, (W // 2 - layer.width // 2, int(cy - layer.height / 2)))


def not_sheep(canvas, t, cy=300):
    d = ImageDraw.Draw(canvas)
    pill(d, W // 2 - 150, cy, "NOT SHEEP", 80, bg=CREAM, fg=INK, k=pop(t))
    if t > .35:
        p = ease((t - .35) / .2)
        wd = font(80).getlength("NOT SHEEP") / 2 + 30
        d.line((W // 2 - 150 - wd, cy + 4, W // 2 - 150 - wd + 2 * wd * p, cy + 4), fill=DENIM, width=12)
    pill(d, W // 2 + 170, cy + 120, "cool girl", 72, bg=DENIM, fg=CREAM, k=pop(t - .55))


def babe(canvas, t, cy=300):
    d = ImageDraw.Draw(canvas)
    pill(d, W // 2, cy, "babe...", 110, bg=INK, fg=CREAM, k=pop(t))


def end_card(canvas, t, top=150):
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    k = pop(t, .3)
    if k > .02:
        d.rounded_rectangle((100, top, W - 100, top + 560), 44, fill=CREAM + (242,), outline=INK, width=5)
        txt(d, (W // 2, top + 90), "SKINNY LAW #1", 44 * k, fill=BROWN, weight=600)
        for i, s in enumerate(("3 real meals.", "Protein first.", "Kitchen closes", "after dinner.")):
            ki = pop(t - .25 - .2 * i)
            txt(d, (W // 2, top + 180 + i * 88), s, 66 * ki, fill=DENIM if i >= 2 else INK)
        txt(d, (W // 2, top + 520), "words: @livschmidt", 30 * pop(t - 1.0), fill=BROWN, weight=600)
    canvas.alpha_composite(layer)
    pill(ImageDraw.Draw(canvas), W // 2, top + 670, "follow for more skinny laws", 50, k=pop(t - 1.2))


# ------------------------------------------------------------------ timeline
def load_words():
    p = os.path.join(V.CACHE, "graze_words.json")
    if not os.path.exists(p):
        from faster_whisper import WhisperModel
        tmp = os.path.join(V.CACHE, "graze.wav")
        sf.write(tmp, V.voice(LINE), SR)
        segs, _ = WhisperModel("small", device="cpu", compute_type="int8").transcribe(tmp, word_timestamps=True)
        json.dump([(w.word.strip(), w.start, w.end) for s in segs for w in s.words], open(p, "w"))
    return [(w, VO + s, VO + e) for w, s, e in json.load(open(p))]


def phrase_times(words):
    """Start of each phrase: 0 'Mindlessly', 1 'farm' (first), 2 'Not', 3 'Like,', 4 second 'it's giving', 5 'farm' (2nd)."""
    starts = [w[1] for w in words]
    names = [w[0].lower().strip(".,") for w in words]
    farm = [s for s, n in zip(starts, names) if n == "farm"]
    return dict(p1=starts[0], farm1=farm[0], sheep=starts[names.index("not")], babe=starts[names.index("like")],
                farm2=farm[1] - 0.45, end=words[-1][2])


# Scenes: (name, start key, list of layers). A layer is a callable (canvas, t_in_scene, t_global) -> None.
def build(version, clips_dir):
    words = load_words()
    T = phrase_times(words)
    total = T["end"] + 2.8
    audio = np.zeros(int(total * SR), np.float32)
    v = V.voice(LINE)
    i0 = int(VO * SR)
    audio[i0:i0 + len(v)] += v
    wav = os.path.join(V.CACHE, "graze.wav")
    sf.write(wav, v, SR)
    cues = [(VO + s, c) for s, c in V.mouth_cues(wav, LINE)]

    def mouth_at(t):
        m = "smile"
        for s, c in cues:
            if s <= t:
                m = V.RHUBARB_TO_MOUTH[c]
        return m if VO <= t <= T["end"] else None

    clips = {}

    def clip(name, start, n_s):
        if name not in clips:
            clips[name] = BR.load_clip(os.path.join(clips_dir, name + ".mp4"))
        fr = clips[name]
        f0, n = int(start * FPS), int(n_s * FPS) + 2
        ok = BR.safe_mask(BR.mouth_gaps(fr))[f0:f0 + n]
        if len(fr) < f0 + n or not ok.all():
            raise SystemExit(f"{name} {start}s: not enough closed-mouth frames")
        print(f"  {name} {start:.2f}-{start + n / FPS:.2f}s: mouth closed in all {n} frames")
        return fr[f0:f0 + n]

    def chibi_layer(face, pose, tilt=0.0, x=W // 2, bottom=H - 40, height=1100, talk=True):
        def draw(canvas, ts, t):
            k = ease(ts / .35)
            arms = {s: (a * k, b * k, c * k, hand if k > .35 else None) for s, (a, b, c, hand) in pose.items()}
            ex = X.expression(face)
            m = mouth_at(t) if talk else None
            if m:
                ex["mouth_shape"] = m
            if abs(ts - .05) < .05 or abs((t % 3.3) - 2.0) < .05:
                ex["eyes"] = "closed"
            ch = chibi(ex, arms, tilt * k + 1.2 * np.sin(t * 2.8), -1.5 * k, height)
            canvas.alpha_composite(ch, (int(x - ch.width / 2), int(bottom - ch.height)))
        return draw

    def full_clip(frames, zoom, focus):
        def draw(canvas, ts, t):
            im = BR.frame_to_canvas(frames[min(int(ts * FPS), len(frames) - 1)], zoom, focus, ts)
            canvas.alpha_composite(im)
        return draw

    def boxed_clip(frames, cx, cy, height):
        def draw(canvas, ts, t):
            fr = frames[min(int(ts * FPS), len(frames) - 1)]
            canvas.alpha_composite(white_bg(fr))
            clip_boxed(canvas, fr, cx, cy, height * (1 + .02 * ts))
        return draw

    def bg(canvas, ts, t):
        canvas.alpha_composite(cream_bg())

    def at(fn, delay=0.0):
        return lambda canvas, ts, t: fn(canvas, ts - delay)

    dur = lambda a, b: T[b] - T[a] if b in T else total - T[a]
    hand_hip = {"right": (45, -100, 0, "fist")}
    shrug = {"right": (20, 85, 35, "open"), "left": (-20, -85, -35, "open")}
    point = {"right": (30, 130, -40, "point")}
    peace = {"left": (-35, -130, 12, "peace")}
    if version == "A":            # the chibi girl leads, the Midjourney girl is cut in twice
        scenes = [
            (0.0, [bg, chibi_layer("smug", hand_hip, -5, talk=False), at(hook)]),
            (T["p1"] - .1, [bg, chibi_layer("eye_roll", shrug, 5, bottom=H + 60), at(snack_list)]),
            (T["farm1"] - .05, [bg, chibi_layer("annoyed", hand_hip, -4, bottom=H + 60), at(stamp)]),
            (T["sheep"] - .1, [full_clip(clip("c02", 8.6, dur("sheep", "babe") + .2), 1.52, .3), at(not_sheep, .05)]),
            (T["babe"] - .1, [bg, chibi_layer("angry", point, 3), at(lambda c, s: babe(c, s, 280))]),
            (T["farm2"], [boxed_clip(clip("c05", 0.8, dur("farm2", "end") + .2), W // 2, 1250, 1150),
                          at(lambda c, s: stamp(c, s - .3, cy=300))]),
            (T["end"] + .15, [bg, chibi_layer("wink", peace, -5, talk=False, bottom=H + 80, height=1000), at(end_card)]),
        ]
    else:                          # the Midjourney girl leads (zoomed out / in), the chibi girl pops in
        small = dict(x=W - 210, bottom=H - 40, height=560)
        scenes = [
            (0.0, [boxed_clip(clip("c10", 0.0, T["p1"] + .2), W // 2 + 210, 1200, 1300), at(hook)]),
            (T["p1"] - .1, [full_clip(clip("c01", 2.4, dur("p1", "sheep") + .3), 1.52, .35), at(snack_list)]),
            (T["farm1"] - .05, [full_clip(clip("c01", 2.4 + T["farm1"] - T["p1"], dur("farm1", "sheep") + .2), 1.52, .35),
                                at(stamp), chibi_layer("eye_roll", shrug, 5, **small)]),
            (T["sheep"] - .1, [boxed_clip(clip("c04", 0.4, dur("sheep", "babe") + .2), W // 2, 1230, 1250),
                               at(not_sheep, .05)]),
            (T["babe"] - .1, [full_clip(clip("c12", 0.5, dur("babe", "farm2") + .2), 1.25, .3),
                              at(lambda c, s: babe(c, s, 300)), chibi_layer("angry", point, 3, **small)]),
            (T["farm2"], [full_clip(clip("c02", 8.6, dur("farm2", "end") + .2), 1.52, .3), at(lambda c, s: stamp(c, s - .3))]),
            (T["end"] + .15, [boxed_clip(clip("c14", 0.0, 2.8), W // 2 - 230, 1350, 1050), at(end_card),
                              chibi_layer("wink", peace, -5, talk=False, **small)]),
        ]
    for s, _ in scenes[1:]:                                   # a whoosh on every cut, a thud on the stamps
        sx = V.sfx(0.35, "whoosh") * .5
        j = int(max(s - .15, 0) * SR)
        audio[j:j + len(sx)] += sx[:len(audio) - j]
    for key in ("farm1", "farm2"):
        th = V.sfx(0.12, "pop") * 1.6
        j = int((T[key] + .35) * SR)
        audio[j:j + len(th)] += th
    return scenes, words, audio, total


def captions(canvas, words, t):
    ws = [(w, s) for w, s, _ in words]
    BR.captions(canvas, ws, t, HOT)


def render(clips_dir, version, out):
    scenes, words, audio, total = build(version, clips_dir)
    with tempfile.TemporaryDirectory() as d:
        wav = os.path.join(d, "a.wav")
        sf.write(wav, np.clip(audio, -1, 1), SR)
        for fi in range(int(total * FPS)):
            t = fi / FPS
            i = max(k for k in range(len(scenes)) if scenes[k][0] <= t)
            t0, layers = scenes[i]
            canvas = Image.new("RGBA", (W, H), (255, 255, 255, 255))
            for L in layers:
                L(canvas, t - t0, t)
            if i > 0 and t - t0 < .1:
                canvas = Image.blend(canvas, Image.new("RGBA", canvas.size, (255, 255, 255, 255)), (1 - (t - t0) / .1) * .5)
            if VO <= t <= words[-1][2] + .3:
                captions(canvas, words, t)
            canvas.convert("RGB").save(os.path.join(d, f"f{fi:04d}.png"))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(d, "f%04d.png"),
                        "-i", wav, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "19", "-c:a", "aac", "-b:a", "160k",
                        "-shortest", out], check=True)
    print("wrote", out, f"({total:.1f} s)")


if __name__ == "__main__":
    render(sys.argv[1], sys.argv[2].upper(), sys.argv[3])
