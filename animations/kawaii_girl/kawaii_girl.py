"""Animate the kawaii girl drawing (original_sheet.png, six poses).

Steps:

  1. Cut the six poses out of the sheet (see-through background):
        python kawaii_girl.py cut original_sheet.png
     This writes sprites/pose1.png ... sprites/pose6.png

  2. Save the animations as data (.json):
        python kawaii_girl.py save
     This writes idle.json, wave.json, poses.json

  3. Turn a .json into a GIF:
        python kawaii_girl.py gif idle.json idle.gif

Needs:  pip install pillow numpy scipy   (numpy/scipy only for step 1)

Pose numbers (from the sheet, left to right, top row then bottom row):
  1 standing, hands together   2 waving        3 finger heart
  4 walking                    5 sitting, wink 6 sitting, side view
"""

import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SPRITES = os.path.join(HERE, "sprites")

BACKGROUND = (255, 240, 245)
HEART = (255, 120, 160)
SPARKLE = (255, 200, 90)
SHADOW = (240, 212, 222)

# Where the eyes are in sprites/pose1.png, used to draw a blink.
# (left, top, right, bottom) in pixels.
POSE1_EYES = [(68, 184, 151, 257), (197, 177, 281, 252)]
POSE1_SKIN_AT = (172, 215)  # a skin pixel between the eyes, to paint over open eyes
LASH = (58, 32, 28)

CANVAS = (560, 760)  # every pose fits in this, feet at the bottom middle
FEET_Y = 720


# ---------------------------------------------------------------- 1. cut ----

def cut(sheet_path):
    """Find each pose on the white sheet and save it with a clear background."""
    import numpy as np
    from PIL import Image, ImageFilter
    from scipy import ndimage as nd

    src = Image.open(sheet_path).convert("RGB")
    a = np.asarray(src).astype(int)
    near_white = a.min(2) > 235
    white_parts, _ = nd.label(near_white)
    sizes = nd.sum(near_white, white_parts, range(white_parts.max() + 1))
    # Background = the white around the edges, plus any big white hole
    # (like the gap between the legs when walking). Small white bits
    # (eye sparkles, shoes) stay.
    background = (white_parts == white_parts[0, 0]) | (near_white & (sizes[white_parts] > 3000))
    figures, count = nd.label(~background)
    fig_sizes = nd.sum(~background, figures, range(1, count + 1))
    boxes = nd.find_objects(figures)
    keep = [i + 1 for i, s in enumerate(fig_sizes) if s > 100000]
    # top row first, then left to right
    keep.sort(key=lambda k: (boxes[k - 1][0].start > a.shape[0] / 2, boxes[k - 1][1].start))

    os.makedirs(SPRITES, exist_ok=True)
    for n, k in enumerate(keep, 1):
        ys, xs = boxes[k - 1]
        pad = 4
        x0, y0, x1, y1 = xs.start - pad, ys.start - pad, xs.stop + pad, ys.stop + pad
        mask = (figures[y0:y1, x0:x1] == k).astype("uint8") * 255
        alpha = Image.fromarray(mask).filter(ImageFilter.GaussianBlur(0.7))
        sprite = src.crop((x0, y0, x1, y1)).convert("RGBA")
        sprite.putalpha(alpha)
        sprite.save(os.path.join(SPRITES, f"pose{n}.png"))
        print(f"saved pose{n}.png {sprite.size}")


# --------------------------------------------------- 2. animations as data ----

def _hearts(t, count=3, spread=0.42):
    """Little hearts that float up and fade in/out. t goes 0..1 over the loop."""
    hearts = []
    for k in range(count):
        p = (t + k / count) % 1
        side = -1 if k % 2 == 0 else 1
        hearts.append({
            "x": round(0.5 + side * spread * (0.8 + 0.2 * k / count) + 0.03 * math.sin(p * 4 * math.pi), 3),
            "y": round(0.55 - 0.45 * p, 3),
            "size": round(0.035 * math.sin(p * math.pi), 3),
        })
    return hearts


def _frame(pose, **kw):
    f = {"pose": pose, "dx": 0, "dy": 0, "scale_x": 1, "scale_y": 1, "angle": 0,
         "blink": False, "hearts": [], "sparkles": []}
    f.update(kw)
    return f


def idle_animation(frame_count=40):
    """Pose 1: gentle breathing, a blink, hearts floating."""
    frames = []
    for i in range(frame_count):
        t = i / frame_count
        breath = math.sin(t * 2 * math.pi)
        frames.append(_frame(
            1,
            scale_y=round(1 + 0.012 * breath, 4),
            scale_x=round(1 - 0.006 * breath, 4),
            blink=i in (26, 27, 28),
            hearts=_hearts(t),
        ))
    return {"name": "idle", "fps": 16, "frames": frames}


def wave_animation(frame_count=32):
    """Pose 2: rocks side to side from the foot, with sparkles by the hand."""
    frames = []
    for i in range(frame_count):
        t = i / frame_count
        rock = math.sin(t * 2 * math.pi)
        hop = max(0, math.sin(t * 4 * math.pi))
        on = (i // 4) % 2 == 0  # sparkles flicker
        frames.append(_frame(
            2,
            angle=round(4 * rock, 3),
            dy=round(-10 * hop, 2),
            sparkles=[{"x": 0.13, "y": 0.33, "size": 0.028}, {"x": 0.19, "y": 0.26, "size": 0.018}] if on else
                     [{"x": 0.11, "y": 0.27, "size": 0.02}, {"x": 0.2, "y": 0.35, "size": 0.024}],
            hearts=_hearts(t, count=2),
        ))
    return {"name": "wave", "fps": 16, "frames": frames}


def poses_animation(frames_per_pose=12, order=(1, 2, 3, 4, 5, 6)):
    """Pops from one pose to the next with a little squash and bounce."""
    frames = []
    total = frames_per_pose * len(order)
    for n, pose in enumerate(order):
        for i in range(frames_per_pose):
            p = i / frames_per_pose
            # squash at the start of each pose, then settle with a small bounce
            squash = math.exp(-6 * p) * math.cos(p * 3 * math.pi)
            frames.append(_frame(
                pose,
                scale_x=round(1 + 0.08 * squash, 4),
                scale_y=round(1 - 0.08 * squash, 4),
                dy=round(-18 * math.sin(p * math.pi) * (1 - p), 2),
                hearts=_hearts((n * frames_per_pose + i) / total, count=4),
            ))
    return {"name": "poses", "fps": 14, "frames": frames}


ANIMATIONS = {"idle": idle_animation, "wave": wave_animation, "poses": poses_animation}


def save(animation, path):
    with open(path, "w") as f:
        json.dump(animation, f, indent=1)


def load(path):
    with open(path) as f:
        return json.load(f)


# -------------------------------------------------------------- 3. render ----

_sprite_cache = {}


def sprite(pose, blink=False):
    from PIL import Image

    key = (pose, blink)
    if key not in _sprite_cache:
        img = Image.open(os.path.join(SPRITES, f"pose{pose}.png")).convert("RGBA")
        if blink and pose == 1:
            img = _close_eyes(img)
        _sprite_cache[key] = img
    return _sprite_cache[key]


def _close_eyes(img):
    """Paint skin over the open eyes and draw a closed-eye lash line."""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFilter
    from scipy import ndimage as nd

    a = np.asarray(img).astype(float)
    skin = np.array(img.getpixel(POSE1_SKIN_AT)[:3], float)
    for x0, y0, x1, y1 in POSE1_EYES:
        box = a[y0:y1, x0:x1, :3]
        not_skin = np.abs(box - skin).sum(2) > 45
        # the eye = the non-skin blob in the middle of the box (so the face
        # outline at the edge is left alone), grown a little
        parts, _ = nd.label(not_skin)
        eye = parts == parts[(y1 - y0) // 2, (x1 - x0) // 2]
        eye = nd.binary_dilation(eye, iterations=3)
        # fill with the nearest real skin pixel, so the shading matches
        _, (iy, ix) = nd.distance_transform_edt(not_skin | eye, return_indices=True)
        filled = nd.gaussian_filter(box[iy, ix], (3, 3, 0))
        blend = nd.gaussian_filter(eye.astype(float), 1.2)[..., None]
        blend = np.maximum(blend, eye[..., None] * 1.0)
        box[:] = box * (1 - blend) + filled * blend
    img = Image.fromarray(a.astype("uint8"), "RGBA")

    big = 4
    lines = Image.new("RGBA", (img.width * big, img.height * big), (0, 0, 0, 0))
    d = ImageDraw.Draw(lines)
    for n, (x0, y0, x1, y1) in enumerate(POSE1_EYES):
        x0, y0, x1, y1 = (v * big for v in (x0, y0, x1, y1))
        w, h = x1 - x0, y1 - y0
        mid = y0 + h * 0.55
        # soft down-curved line, like a sleeping kawaii eye
        d.arc([x0 + w * 0.12, mid - h * 0.3, x1 - w * 0.12, mid + h * 0.3], 15, 165, fill=LASH, width=6 * big)
        # little lash flick at the outer corner
        cx, flick = (x0 + w * 0.15, -1) if n == 0 else (x1 - w * 0.15, 1)
        d.line([(cx, mid + h * 0.1), (cx + flick * w * 0.1, mid - h * 0.02)], fill=LASH, width=5 * big)
    lines = lines.resize(img.size, Image.LANCZOS)
    img.alpha_composite(lines)
    return img


def _draw_heart(draw, cx, cy, r, fill):
    draw.ellipse([cx - r, cy - r * 0.9, cx, cy + r * 0.1], fill=fill)
    draw.ellipse([cx, cy - r * 0.9, cx + r, cy + r * 0.1], fill=fill)
    draw.polygon([(cx - r * 0.97, cy - r * 0.25), (cx + r * 0.97, cy - r * 0.25), (cx, cy + r)], fill=fill)


def _draw_sparkle(draw, cx, cy, r, fill):
    k = r * 0.25
    draw.polygon([(cx, cy - r), (cx + k, cy - k), (cx + r, cy), (cx + k, cy + k),
                  (cx, cy + r), (cx - k, cy + k), (cx - r, cy), (cx - k, cy - k)], fill=fill)


def draw_frame(frame, out_scale=1.0):
    from PIL import Image, ImageDraw

    W, H = CANVAS
    canvas = Image.new("RGBA", (W, H), BACKGROUND + (255,))
    d = ImageDraw.Draw(canvas)

    body = sprite(frame["pose"], frame["blink"])
    sw, sh = body.size
    body = body.resize((max(1, round(sw * frame["scale_x"])), max(1, round(sh * frame["scale_y"]))), Image.LANCZOS)
    if frame["angle"]:
        # turn around the feet: pad so the feet are in the middle, then rotate
        bw, bh = body.size
        padded = Image.new("RGBA", (bw, bh * 2), (0, 0, 0, 0))
        padded.paste(body, (0, 0))
        body = padded.rotate(frame["angle"], resample=Image.BICUBIC, expand=True)
        feet = (body.size[0] / 2, body.size[1] / 2)
    else:
        feet = (body.size[0] / 2, body.size[1])

    lift = -frame["dy"]
    shadow_w = sw * 0.36 * (1 - min(lift, 40) / 100)
    d.ellipse([W / 2 - shadow_w, FEET_Y - 10, W / 2 + shadow_w, FEET_Y + 10], fill=SHADOW)

    x = round(W / 2 - feet[0] + frame["dx"])
    y = round(FEET_Y - feet[1] + frame["dy"])
    canvas.paste(body, (x, y), body)

    for h in frame["hearts"]:
        if h["size"] > 0.004:
            _draw_heart(d, h["x"] * W, h["y"] * H, h["size"] * W, HEART)
    for s in frame["sparkles"]:
        _draw_sparkle(d, s["x"] * W, s["y"] * H, s["size"] * W, SPARKLE)

    img = canvas.convert("RGB")
    if out_scale != 1:
        img = img.resize((round(W * out_scale), round(H * out_scale)), Image.LANCZOS)
    return img


def to_gif(animation, path, out_scale=0.6):
    images = [draw_frame(f, out_scale) for f in animation["frames"]]
    images[0].save(path, save_all=True, append_images=images[1:],
                   duration=int(1000 / animation["fps"]), loop=0, optimize=True)


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) == 2 and args[0] == "cut":
        cut(args[1])
    elif args == ["save"]:
        for name, make in ANIMATIONS.items():
            save(make(), os.path.join(HERE, f"{name}.json"))
            print(f"saved {name}.json")
    elif len(args) == 3 and args[0] == "gif":
        to_gif(load(args[1]), args[2])
    else:
        print(__doc__)
