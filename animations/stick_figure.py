"""A small stick figure animation you can use from Python.

The animation is saved as plain data (a list of frames with joint angles)
in a .json file. This script can:

  * make the .json file         python stick_figure.py save wave.json
  * turn a .json file into a GIF python stick_figure.py gif wave.json wave.gif

Only needs Pillow for the GIF part:  pip install pillow
"""

import json
import math
import sys

# Length of each body part, in pixels.
BONES = {"body": 60, "upper_arm": 30, "lower_arm": 28, "upper_leg": 35, "lower_leg": 35}
HEAD_RADIUS = 14


def wave_animation(frame_count=24):
    """Build the 'wave hello' animation: right arm waves, body bobs a little."""
    frames = []
    for i in range(frame_count):
        t = i / frame_count * 2 * math.pi
        frames.append({
            # Angles in degrees. 0 = pointing straight down, positive = toward the viewer's right.
            "bob": round(2 * math.sin(2 * t), 2),
            "left_upper_arm": -20,
            "left_lower_arm": -10,
            "right_upper_arm": 115,
            "right_lower_arm": round(165 + 35 * math.sin(t), 2),
            "left_upper_leg": -12,
            "left_lower_leg": -5,
            "right_upper_leg": 12,
            "right_lower_leg": 5,
        })
    return {"name": "wave", "fps": 12, "width": 200, "height": 220, "frames": frames}


def save(animation, path):
    with open(path, "w") as f:
        json.dump(animation, f, indent=1)


def load(path):
    with open(path) as f:
        return json.load(f)


def _point(start, angle, length):
    rad = math.radians(angle)
    return (start[0] + length * math.sin(rad), start[1] + length * math.cos(rad))


def pose_lines(frame, width, height):
    """Turn one frame of angles into line segments and a head circle."""
    hip = (width / 2, height * 0.6 + frame["bob"])
    neck = (hip[0], hip[1] - BONES["body"])
    shoulder = (neck[0], neck[1] + 10)
    lines = [(hip, neck)]
    for side in ("left", "right"):
        elbow = _point(shoulder, frame[f"{side}_upper_arm"], BONES["upper_arm"])
        hand = _point(elbow, frame[f"{side}_lower_arm"], BONES["lower_arm"])
        knee = _point(hip, frame[f"{side}_upper_leg"], BONES["upper_leg"])
        foot = _point(knee, frame[f"{side}_lower_leg"], BONES["lower_leg"])
        lines += [(shoulder, elbow), (elbow, hand), (hip, knee), (knee, foot)]
    head = (neck[0], neck[1] - HEAD_RADIUS)
    return lines, head


def to_gif(animation, path):
    from PIL import Image, ImageDraw

    w, h = animation["width"], animation["height"]
    images = []
    for frame in animation["frames"]:
        img = Image.new("RGB", (w, h), "white")
        draw = ImageDraw.Draw(img)
        lines, head = pose_lines(frame, w, h)
        for a, b in lines:
            draw.line([a, b], fill="black", width=4)
        draw.ellipse([head[0] - HEAD_RADIUS, head[1] - HEAD_RADIUS,
                      head[0] + HEAD_RADIUS, head[1] + HEAD_RADIUS], outline="black", width=4)
        images.append(img)
    images[0].save(path, save_all=True, append_images=images[1:],
                   duration=int(1000 / animation["fps"]), loop=0)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "save":
        save(wave_animation(), sys.argv[2])
    elif len(sys.argv) == 4 and sys.argv[1] == "gif":
        to_gif(load(sys.argv[2]), sys.argv[3])
    else:
        print(__doc__)
