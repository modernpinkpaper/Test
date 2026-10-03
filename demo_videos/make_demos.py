"""Two short sample videos, drawn 100% by code (no GPU, no clips).

1. ball_battle.mp4   - "bouncing ball battle": two balls fight inside a ring.
2. compound.mp4      - finance: animated compound-interest growth chart.
"""
import math
import os
import random

import imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 720, 1280, 30
OUT = os.path.dirname(os.path.abspath(__file__))
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def font(size):
    try:
        return ImageFont.truetype(FONT, size)
    except OSError:
        return ImageFont.load_default()


def center_text(d, y, text, size, fill):
    f = font(size)
    w = d.textlength(text, font=f)
    d.text(((W - w) / 2, y), text, font=f, fill=fill)


def writer(name):
    return imageio.get_writer(f"{OUT}/{name}", fps=FPS, codec="libx264",
                              quality=8, macro_block_size=1)


# ---------------------------------------------------------------- ball battle
def ball_battle():
    random.seed(7)
    cx, cy, R = W / 2, H / 2 + 60, 300
    balls = [
        dict(name="SAVINGS", color=(46, 204, 113), x=cx - 120, y=cy, vx=7, vy=-5, hp=100),
        dict(name="INFLATION", color=(231, 76, 60), x=cx + 120, y=cy, vx=-6, vy=6, hp=100),
    ]
    r = 45
    g = 0.25
    w = writer("ball_battle.mp4")
    flash = 0
    winner = None
    end_at = None
    for frame in range(FPS * 40):
        if winner and end_at is None:
            end_at = frame + FPS * 2
        if end_at and frame >= end_at:
            break
        if winner is None:
            for b in balls:
                b["vy"] += g
                b["x"] += b["vx"]
                b["y"] += b["vy"]
                dx, dy = b["x"] - cx, b["y"] - cy
                dist = math.hypot(dx, dy)
                if dist > R - r:  # bounce off the ring
                    nx, ny = dx / dist, dy / dist
                    dot = b["vx"] * nx + b["vy"] * ny
                    b["vx"] -= 2 * dot * nx
                    b["vy"] -= 2 * dot * ny
                    b["vx"] *= 1.01
                    b["vy"] *= 1.01
                    b["x"], b["y"] = cx + nx * (R - r), cy + ny * (R - r)
            a, b = balls
            dx, dy = b["x"] - a["x"], b["y"] - a["y"]
            dist = math.hypot(dx, dy)
            if dist < 2 * r:  # balls hit each other
                nx, ny = dx / dist, dy / dist
                rel = (a["vx"] - b["vx"]) * nx + (a["vy"] - b["vy"]) * ny
                if rel > 0:
                    a["vx"] -= rel * nx; a["vy"] -= rel * ny
                    b["vx"] += rel * nx; b["vy"] += rel * ny
                    # faster ball deals the damage
                    sa, sb = math.hypot(a["vx"], a["vy"]), math.hypot(b["vx"], b["vy"])
                    hit = random.randint(12, 25)
                    (b if sa > sb else a)["hp"] -= hit
                    flash = 6
                overlap = 2 * r - dist
                a["x"] -= nx * overlap / 2; a["y"] -= ny * overlap / 2
                b["x"] += nx * overlap / 2; b["y"] += ny * overlap / 2
            for x in balls:
                if x["hp"] <= 0:
                    x["hp"] = 0
                    winner = [y for y in balls if y is not x][0]

        img = Image.new("RGB", (W, H), (15, 17, 26))
        d = ImageDraw.Draw(img)
        center_text(d, 70, "SAVINGS vs INFLATION", 44, (255, 255, 255))
        center_text(d, 125, "Who wins?", 34, (180, 180, 200))
        # health bars
        for i, x in enumerate(balls):
            bx = 60 if i == 0 else W / 2 + 20
            d.text((bx, 200), x["name"], font=font(26), fill=x["color"])
            d.rectangle([bx, 240, bx + 280, 265], fill=(50, 50, 60))
            d.rectangle([bx, 240, bx + 280 * x["hp"] / 100, 265], fill=x["color"])
        ring = (255, 255, 255) if flash == 0 else (255, 220, 80)
        d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=ring, width=8)
        for x in balls:
            d.ellipse([x["x"] - r, x["y"] - r, x["x"] + r, x["y"] + r], fill=x["color"])
            f = font(20)
            label = x["name"][:4]
            d.text((x["x"] - d.textlength(label, font=f) / 2, x["y"] - 12), label,
                   font=f, fill=(255, 255, 255))
        if winner:
            center_text(d, cy + R + 60, f"{winner['name']} WINS!", 60, winner["color"])
        flash = max(0, flash - 1)
        w.append_data(np.asarray(img))
    w.close()


# ---------------------------------------------------------- compound interest
def compound():
    monthly, rate, years = 200, 0.08, 40
    values, invested = [0.0], [0.0]
    for m in range(years * 12):
        values.append(values[-1] * (1 + rate / 12) + monthly)
        invested.append(invested[-1] + monthly)
    top = values[-1]
    left, right, top_y, bot_y = 90, W - 50, 380, 1050
    w = writer("compound.mp4")
    total_frames = FPS * 12
    for frame in range(total_frames + FPS * 2):
        t = min(1, frame / total_frames)
        n = max(1, int(t * len(values)) - 1)
        img = Image.new("RGB", (W, H), (12, 20, 18))
        d = ImageDraw.Draw(img)
        center_text(d, 80, "$200 a month at 8%", 46, (255, 255, 255))
        center_text(d, 140, "for 40 years becomes...", 34, (170, 200, 190))
        # axes
        d.line([left, bot_y, right, bot_y], fill=(80, 100, 95), width=3)
        d.line([left, top_y, left, bot_y], fill=(80, 100, 95), width=3)

        def pt(i, v):
            return (left + (right - left) * i / (len(values) - 1),
                    bot_y - (bot_y - top_y) * v / top)

        d.line([pt(i, invested[i]) for i in range(n + 1)], fill=(120, 140, 255), width=6)
        d.line([pt(i, values[i]) for i in range(n + 1)], fill=(46, 204, 113), width=8)
        x, y = pt(n, values[n])
        d.ellipse([x - 12, y - 12, x + 12, y + 12], fill=(46, 204, 113))
        yr = n / 12
        center_text(d, 1090, f"Year {yr:.0f}", 36, (200, 220, 210))
        center_text(d, 1140, f"${values[n]:,.0f}", 80, (46, 204, 113))
        d.text((left, 1250 - 20), f"You put in: ${invested[n]:,.0f}",
               font=font(28), fill=(120, 140, 255))
        w.append_data(np.asarray(img))
    w.close()


if __name__ == "__main__":
    import os
    os.makedirs(OUT, exist_ok=True)
    ball_battle()
    compound()
    print("done")
