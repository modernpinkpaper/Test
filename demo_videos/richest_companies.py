"""World's most valuable companies, 2000 -> 2025, as a styled racing bar chart.

Drawn 100% by code: no GPU, no AI, no clips. Also makes its own lo-fi beat.
Numbers are rough year-end market caps for demo use only.

Run:  python demo_videos/richest_companies.py
Out:  demo_videos/richest_companies.mp4
"""
import math
import os
import random
import subprocess
import wave

import imageio
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
S = 2  # draw at 2x size, then shrink, for smooth edges
TOP_N = 8
SECONDS_PER_YEAR = 0.8
HOLD = 3.5

# Rough year-end market cap in $ billions (demo data).
DATA = {
    "Apple":      {2000: 5, 2005: 60, 2010: 295, 2015: 585, 2020: 2255, 2025: 4000},
    "Microsoft":  {2000: 231, 2005: 280, 2010: 240, 2015: 440, 2020: 1680, 2025: 3600},
    "Nvidia":     {2000: 2, 2005: 20, 2010: 9, 2015: 18, 2020: 325, 2025: 4500},
    "Alphabet":   {2000: 1, 2005: 125, 2010: 190, 2015: 530, 2020: 1185, 2025: 3800},
    "Amazon":     {2000: 5, 2005: 20, 2010: 80, 2015: 315, 2020: 1630, 2025: 2400},
    "Meta":       {2000: 1, 2005: 1, 2010: 1, 2015: 300, 2020: 780, 2025: 1700},
    "Tesla":      {2000: 1, 2005: 1, 2010: 2, 2015: 32, 2020: 670, 2025: 1400},
    "Berkshire":  {2000: 108, 2005: 135, 2010: 200, 2015: 325, 2020: 545, 2025: 1100},
    "Broadcom":   {2000: 1, 2005: 1, 2010: 7, 2015: 40, 2020: 180, 2025: 1600},
    "Walmart":    {2000: 237, 2005: 197, 2010: 195, 2015: 195, 2020: 410, 2025: 900},
    "ExxonMobil": {2000: 302, 2005: 350, 2010: 370, 2015: 325, 2020: 175, 2025: 480},
    "GE":         {2000: 475, 2005: 370, 2010: 195, 2015: 290, 2020: 95, 2025: 300},
    "Cisco":      {2000: 275, 2005: 105, 2010: 110, 2015: 138, 2020: 190, 2025: 280},
    "Pfizer":     {2000: 290, 2005: 170, 2010: 140, 2015: 200, 2020: 205, 2025: 145},
    "Citigroup":  {2000: 256, 2005: 245, 2010: 137, 2015: 155, 2020: 128, 2025: 190},
    "Intel":      {2000: 202, 2005: 150, 2010: 115, 2015: 163, 2020: 205, 2025: 170},
}
# Two-tone gradient per company (brand-ish colors, no logos).
COLORS = {
    "Apple": ("#8e9eab", "#eef2f3"), "Microsoft": ("#0078d4", "#50e6ff"),
    "Nvidia": ("#3a7d00", "#9dff3a"), "Alphabet": ("#4285f4", "#ea4335"),
    "Amazon": ("#ff6a00", "#ffd200"), "Meta": ("#0064e0", "#a24cff"),
    "Tesla": ("#b3001b", "#ff5470"), "Berkshire": ("#1f3b73", "#d4af37"),
    "Broadcom": ("#cc092f", "#ff8a65"), "Walmart": ("#0071ce", "#ffc220"),
    "ExxonMobil": ("#d41c24", "#ff7a59"), "GE": ("#005eb8", "#6ec1ff"),
    "Cisco": ("#049fd9", "#7ae1ff"), "Pfizer": ("#0093d0", "#8fd3fe"),
    "Citigroup": ("#003b70", "#ff3c3c"), "Intel": ("#0068b5", "#00c7fd"),
}
YEARS = (2000, 2025)


def font(weight, size):
    return ImageFont.truetype(os.path.join(HERE, "fonts", f"poppins-latin-{weight}-normal.woff"), size * S)


def hex_rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def value_at(name, year):
    """Smooth (log-scale) value between the 5-year data points."""
    pts = DATA[name]
    ys = sorted(pts)
    year = min(max(year, ys[0]), ys[-1])
    for a, b in zip(ys, ys[1:]):
        if a <= year <= b:
            t = (year - a) / (b - a)
            t = t * t * (3 - 2 * t)  # ease in/out
            return math.exp(math.log(pts[a]) * (1 - t) + math.log(pts[b]) * t)
    return pts[ys[-1]]


def money(v):
    return f"${v / 1000:.2f}T" if v >= 1000 else f"${v:.0f}B"


def make_background():
    """Deep purple -> black gradient with a soft glow and vignette."""
    w, h = W * S, H * S
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    top = np.array([38, 12, 70], np.float32)
    bot = np.array([5, 5, 16], np.float32)
    t = (y / h)[..., None]
    img = top * (1 - t) + bot * t
    glow = np.exp(-(((x - w * 0.8) / (w * 0.5)) ** 2 + ((y - h * 0.15) / (h * 0.25)) ** 2))[..., None]
    img += glow * np.array([90, 30, 140], np.float32) * 0.6
    vig = 1 - 0.55 * (((x - w / 2) / (w / 2)) ** 2 + ((y - h / 2) / (h / 2)) ** 2) / 2
    img *= vig[..., None]
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert("RGBA")


def gradient_bar(w, h, c1, c2):
    a = np.linspace(0, 1, max(w, 1), dtype=np.float32)[None, :, None]
    rgb = np.array(c1, np.float32) * (1 - a) + np.array(c2, np.float32) * a
    rgb = np.repeat(rgb, h, axis=0)
    bar = Image.fromarray(rgb.astype(np.uint8)).convert("RGBA")
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=h // 2, fill=255)
    bar.putalpha(mask)
    return bar


def text_center(d, cx, y, s, f, fill):
    d.text((cx - d.textlength(s, font=f) / 2, y), s, font=f, fill=fill)


def make_music(path, seconds):
    """Simple lo-fi beat: soft chords, kick, hat, vinyl crackle."""
    sr, bpm = 44100, 84
    n = int(sr * seconds)
    t = np.arange(n) / sr
    out = np.zeros(n, np.float32)
    beat = 60 / bpm
    chords = [[57, 60, 64, 67], [53, 57, 60, 64], [48, 52, 55, 59], [55, 59, 62, 65]]  # Am7 Fmaj7 Cmaj7 G7
    bar_len = beat * 4
    for i in range(int(seconds / bar_len) + 1):
        start = int(i * bar_len * sr)
        seg = np.arange(int(bar_len * sr))
        env = np.minimum(1, seg / (0.4 * sr)) * np.exp(-seg / (3.5 * sr))
        tone = sum(np.sin(2 * np.pi * 440 * 2 ** ((m - 69) / 12) * seg / sr) for m in chords[i % 4])
        piece = (tone * env * 0.06).astype(np.float32)
        end = min(n, start + len(piece))
        out[start:end] += piece[:end - start]
    rng = np.random.default_rng(1)
    for k in range(int(seconds / beat) + 1):
        s = int(k * beat * sr)
        if k % 2 == 0:  # kick
            seg = np.arange(int(0.25 * sr))
            f = 110 * np.exp(-seg / (0.03 * sr)) + 45
            kick = np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-seg / (0.08 * sr)) * 0.5
            e = min(n, s + len(kick)); out[s:e] += kick[:e - s]
        for off in (0, 0.5):  # hats
            hs = int((k + off) * beat * sr)
            seg = int(0.04 * sr)
            hat = rng.normal(0, 1, seg) * np.exp(-np.arange(seg) / (0.008 * sr)) * 0.05
            hat = np.diff(hat, prepend=0)
            e = min(n, hs + seg); out[hs:e] += hat[:e - hs]
    crackle = (rng.random(n) > 0.9993) * rng.normal(0, 0.15, n)
    out += crackle.astype(np.float32) + rng.normal(0, 0.003, n).astype(np.float32)
    fade = np.minimum(1, np.minimum(t / 1.0, (seconds - t) / 1.5))
    out = np.clip(out * fade / (np.abs(out).max() + 1e-6) * 0.8, -1, 1)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
        wf.writeframes((out * 32767).astype(np.int16).tobytes())


def main():
    bg = make_background()
    random.seed(3)
    particles = [[random.uniform(0, W * S), random.uniform(0, H * S),
                  random.uniform(1, 4) * S, random.uniform(0.3, 1.2) * S,
                  random.randint(40, 140)] for _ in range(70)]

    anim_frames = int((YEARS[1] - YEARS[0]) * SECONDS_PER_YEAR * FPS)
    total = anim_frames + int(HOLD * FPS)
    left, right = 70 * S, (W - 70) * S
    chart_top, row_h, bar_h = 450 * S, 140 * S, 80 * S
    ypos = {}  # smoothed row positions
    f_title, f_sub = font(800, 58), font(400, 32)
    f_name, f_val, f_rank = font(600, 34), font(800, 38), font(800, 40)
    f_year, f_small = font(800, 260), font(400, 24)
    f_cta = font(800, 56)

    silent = os.path.join(HERE, "_silent.mp4")
    wav = os.path.join(HERE, "_music.wav")
    out = os.path.join(HERE, "richest_companies.mp4")
    wr = imageio.get_writer(silent, fps=FPS, codec="libx264", quality=8, macro_block_size=1)

    for fr in range(total):
        year = YEARS[0] + min(fr, anim_frames) / FPS / SECONDS_PER_YEAR
        vals = sorted(((value_at(n, year), n) for n in DATA), reverse=True)
        top = vals[:TOP_N]
        vmax = top[0][0]
        rank = {n: i for i, (_, n) in enumerate(vals)}

        img = bg.copy()
        d = ImageDraw.Draw(img)
        for p in particles:  # drifting dust
            p[1] -= p[3]
            if p[1] < 0:
                p[1] = H * S
            d.ellipse([p[0] - p[2], p[1] - p[2], p[0] + p[2], p[1] + p[2]], fill=(200, 170, 255, p[4] // 3))

        # big faint year behind the chart
        yl = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(yl).text((right, 1480 * S), f"{int(year)}", font=f_year,
                                fill=(255, 255, 255, 38), anchor="rs")
        img.alpha_composite(yl)

        bars = Image.new("RGBA", img.size, (0, 0, 0, 0))
        labels = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ld = ImageDraw.Draw(labels)
        for name in DATA:
            target = chart_top + rank[name] * row_h
            y = ypos.get(name, target)
            y += (target - y) * 0.25
            ypos[name] = y
            if y > chart_top + TOP_N * row_h - row_h * 0.4:
                continue
            v = value_at(name, year)
            bw = int((right - left - 330 * S) * v / vmax)
            bw = max(bw, int(ld.textlength(name, font=f_name)) + 60 * S)  # name always fits
            x0 = left + 80 * S
            c1, c2 = (hex_rgb(c) for c in COLORS[name])
            bars.alpha_composite(gradient_bar(bw, bar_h, c1, c2), (x0, int(y)))
            lum = 0.299 * c1[0] + 0.587 * c1[1] + 0.114 * c1[2]
            ld.text((x0 + 30 * S, y + bar_h / 2), name, font=f_name,
                    fill=(15, 15, 25) if lum > 140 else (255, 255, 255), anchor="lm")
            ld.text((x0 + bw + 22 * S, y + bar_h / 2), money(v), font=f_val,
                    fill=(255, 255, 255), anchor="lm")
        for i in range(TOP_N):  # rank numbers stay in fixed slots
            ld.text((left + 30 * S, chart_top + i * row_h + bar_h / 2), f"{i + 1}", font=f_rank,
                    fill=(255, 255, 255, 170), anchor="mm")
        # neon glow: blur a small copy of the bars
        small = bars.resize((W // 4, H // 4))
        glow = small.filter(ImageFilter.GaussianBlur(6)).resize(img.size)
        img.alpha_composite(glow)
        img.alpha_composite(glow)
        img.alpha_composite(bars)
        img.alpha_composite(labels)

        d = ImageDraw.Draw(img)
        text_center(d, W * S / 2, 130 * S, "MOST VALUABLE", f_title, (255, 255, 255))
        text_center(d, W * S / 2, 205 * S, "COMPANIES ON EARTH", f_title, (190, 150, 255))
        text_center(d, W * S / 2, 300 * S, "by market cap, 2000 - 2025", f_sub, (200, 190, 230))

        # timeline
        ty = 1720 * S
        d.rounded_rectangle([left, ty, right, ty + 10 * S], radius=5 * S, fill=(255, 255, 255, 40))
        prog = (year - YEARS[0]) / (YEARS[1] - YEARS[0])
        px = left + (right - left) * prog
        d.rounded_rectangle([left, ty, px, ty + 10 * S], radius=5 * S, fill=(190, 150, 255))
        d.ellipse([px - 14 * S, ty - 9 * S, px + 14 * S, ty + 19 * S], fill=(255, 255, 255))
        for yr in range(YEARS[0], YEARS[1] + 1, 5):
            x = left + (right - left) * (yr - YEARS[0]) / (YEARS[1] - YEARS[0])
            text_center(d, x, ty + 30 * S, str(yr), f_small, (200, 190, 230))
        text_center(d, W * S / 2, 1845 * S, "Approx. year-end values. Demo data, not financial advice.",
                    f_small, (150, 140, 180))

        if fr > anim_frames + FPS * 0.5:  # end card
            a = min(1, (fr - anim_frames - FPS * 0.5) / (FPS * 0.5))
            cta = Image.new("RGBA", img.size, (0, 0, 0, 0))
            cd = ImageDraw.Draw(cta)
            cd.rounded_rectangle([left, 1580 * S, right, 1700 * S], radius=40 * S,
                                 fill=(20, 10, 40, int(220 * a)))
            text_center(cd, W * S / 2, 1603 * S, "Who's #1 in 2030?", f_cta, (255, 255, 255, int(255 * a)))
            img.alpha_composite(cta)

        wr.append_data(np.asarray(img.convert("RGB").resize((W, H), Image.LANCZOS)))
    wr.close()

    make_music(wav, total / FPS)
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ff, "-loglevel", "error", "-y", "-i", silent, "-i", wav, "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "160k", "-shortest", out], check=True)
    os.remove(silent)
    os.remove(wav)
    print("saved", out)


if __name__ == "__main__":
    main()
