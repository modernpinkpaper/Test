"""A kawaii (cute) cat animation you can use from Python.

The cat bounces (squash and stretch), blinks, and little hearts float up.
Like stick_figure.py, the animation is saved as plain data in a .json file:

  * make the .json file         python kawaii_cat.py save kawaii_cat.json
  * turn a .json file into a GIF python kawaii_cat.py gif kawaii_cat.json kawaii_cat.gif

Only needs Pillow for the GIF part:  pip install pillow
"""

import json
import math
import sys

# Colors
BACKGROUND = (255, 240, 245)
BODY = (255, 255, 255)
OUTLINE = (90, 60, 70)
EAR_INSIDE = (255, 190, 205)
BLUSH = (255, 170, 190)
HEART = (255, 120, 160)

SCALE = 4  # draw 4x bigger, then shrink, so the edges look smooth


def cat_animation(frame_count=32):
    """Build the animation as a list of frames with a few numbers each."""
    frames = []
    for i in range(frame_count):
        t = i / frame_count
        bounce = abs(math.sin(t * 2 * math.pi))  # 0 = on the ground, 1 = top of the jump
        squash = 1 - bounce if bounce < 0.25 else 0  # flatten a bit when landing
        hearts = []
        for k in range(3):
            p = (t + k / 3) % 1  # each heart is at a different point in its trip up
            hearts.append({
                "x": round(0.5 + 0.3 * (k - 1) + 0.04 * math.sin(p * 4 * math.pi), 3),
                "y": round(0.45 - 0.35 * p, 3),
                "size": round(0.05 * math.sin(p * math.pi), 3),
            })
        frames.append({
            "lift": round(bounce * 0.08, 3),
            "stretch_x": round(1 + 0.12 * squash, 3),
            "stretch_y": round(1 - 0.12 * squash + 0.04 * bounce, 3),
            "eyes_closed": i in (20, 21, 22),  # blink
            "hearts": hearts,
        })
    return {"name": "kawaii_cat", "fps": 16, "width": 256, "height": 256, "frames": frames}


def save(animation, path):
    with open(path, "w") as f:
        json.dump(animation, f, indent=1)


def load(path):
    with open(path) as f:
        return json.load(f)


def _heart(draw, cx, cy, r, fill):
    """Two circles and a triangle make a heart."""
    draw.ellipse([cx - r, cy - r * 0.9, cx, cy + r * 0.1], fill=fill)
    draw.ellipse([cx, cy - r * 0.9, cx + r, cy + r * 0.1], fill=fill)
    draw.polygon([(cx - r * 0.97, cy - r * 0.25), (cx + r * 0.97, cy - r * 0.25), (cx, cy + r)], fill=fill)


def draw_frame(frame, width, height):
    from PIL import Image, ImageDraw

    W, H = width * SCALE, height * SCALE
    img = Image.new("RGB", (W, H), BACKGROUND)
    d = ImageDraw.Draw(img)
    line = 3 * SCALE

    # Shadow on the ground gets smaller when the cat is up high
    ground = H * 0.86
    shadow = W * (0.26 - frame["lift"])
    d.ellipse([W / 2 - shadow, ground - shadow * 0.15, W / 2 + shadow, ground + shadow * 0.15], fill=(240, 205, 215))

    # Body: a round mochi shape
    bw = W * 0.30 * frame["stretch_x"]
    bh = H * 0.26 * frame["stretch_y"]
    cx = W / 2
    bottom = ground - H * frame["lift"]
    top = bottom - 2 * bh

    # Ears (drawn first so the body covers their base)
    for side in (-1, 1):
        ex = cx + side * bw * 0.55
        outer = [(ex - side * bw * 0.35, top + bh * 0.35), (ex + side * bw * 0.25, top - bh * 0.35), (ex + side * bw * 0.35, top + bh * 0.45)]
        inner = [(ex - side * bw * 0.18, top + bh * 0.3), (ex + side * bw * 0.2, top - bh * 0.12), (ex + side * bw * 0.22, top + bh * 0.35)]
        d.polygon(outer, fill=BODY, outline=OUTLINE, width=line)
        d.polygon(inner, fill=EAR_INSIDE)

    d.ellipse([cx - bw, top, cx + bw, bottom], fill=BODY, outline=OUTLINE, width=line)

    # Face
    face_y = top + bh * 0.95
    eye_dx = bw * 0.42
    eye_r = bw * 0.11
    for side in (-1, 1):
        ex = cx + side * eye_dx
        if frame["eyes_closed"]:
            d.arc([ex - eye_r, face_y - eye_r, ex + eye_r, face_y + eye_r], 200, 340, fill=OUTLINE, width=line)
        else:
            d.ellipse([ex - eye_r, face_y - eye_r * 1.2, ex + eye_r, face_y + eye_r * 1.2], fill=OUTLINE)
            s = eye_r * 0.4  # sparkle
            d.ellipse([ex - eye_r * 0.55, face_y - eye_r * 0.85, ex - eye_r * 0.55 + 2 * s, face_y - eye_r * 0.85 + 2 * s], fill="white")
        # Blush
        bx = cx + side * bw * 0.68
        d.ellipse([bx - bw * 0.14, face_y + bh * 0.18, bx + bw * 0.14, face_y + bh * 0.32], fill=BLUSH)

    # Little "w" mouth
    m = bw * 0.07
    my = face_y + bh * 0.15
    d.arc([cx - 2 * m, my - m, cx, my + m], 0, 180, fill=OUTLINE, width=line)
    d.arc([cx, my - m, cx + 2 * m, my + m], 0, 180, fill=OUTLINE, width=line)

    # Floating hearts
    for h in frame["hearts"]:
        if h["size"] > 0.005:
            _heart(d, h["x"] * W, h["y"] * H, h["size"] * W, HEART)

    return img.resize((width, height), Image.LANCZOS)


def to_gif(animation, path):
    images = [draw_frame(f, animation["width"], animation["height"]) for f in animation["frames"]]
    images[0].save(path, save_all=True, append_images=images[1:],
                   duration=int(1000 / animation["fps"]), loop=0)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "save":
        save(cat_animation(), sys.argv[2])
    elif len(sys.argv) == 4 and sys.argv[1] == "gif":
        to_gif(load(sys.argv[2]), sys.argv[3])
    else:
        print(__doc__)
