"""Contact sheet of the second batch of hands on her arms (see measure_hands.py --more), one pose per tile.

    python chibi/demo_hands2.py out.png

Each pose: {side: (shoulder, elbow, wrist, hand)} in degrees on the arm rig (chibi_body.arm), + head tilt and mouth.
"""
import io
import sys

import cairosvg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import chibi_body as CB
import chibi_hair as CH

VIEW = (-40, 300, 460, 560)          # upper body: the hands are what this sheet is about
SCALE = 0.75

def _rot(v, a):
    a = np.radians(a)
    return np.array([v[0] * np.cos(a) - v[1] * np.sin(a), v[0] * np.sin(a) + v[1] * np.cos(a)])


def _turn(v0, v1):
    """Clockwise-on-screen degrees that turn direction v0 onto v1."""
    return float((np.degrees(np.arctan2(v1[1], v1[0]) - np.arctan2(v0[1], v0[0])) + 540) % 360 - 180)


def reach(side, wrist_at, hand_dir, elbow_out=True, hand=None):
    """Arm angles (shoulder, elbow, wrist, hand) that put the wrist at `wrist_at` (drawing units) with the hand's
    fingers pointing along `hand_dir` (None: straight on from the forearm); elbow_out: the elbow bends away from the body (else towards it)."""
    J = CB.arm_joints(side)
    S, E0, W0 = (np.array(J[k], float) for k in ("shoulder", "elbow", "wrist"))
    a, b = np.linalg.norm(E0 - S), np.linalg.norm(W0 - E0)
    T = np.array(wrist_at, float)
    d = np.linalg.norm(T - S)
    d = min(max(d, abs(a - b) + 1e-3), a + b - 1e-3)
    ux = (T - S) / np.linalg.norm(T - S)
    along = (a * a - b * b + d * d) / (2 * d)
    perp = np.sqrt(max(a * a - along * along, 0))
    n = np.array([-ux[1], ux[0]])
    outward = -1 if side == "right" else 1                   # her right arm is on the viewer's left
    E = S + ux * along + n * perp * (1 if (n[0] * outward > 0) == elbow_out else -1)
    sh = _turn(E0 - S, E - S)
    el = _turn(_rot(W0 - E0, sh), S + ux * d - E)
    wr = 0.0 if hand_dir is None else _turn(_rot(W0 - E0, sh + el), hand_dir)
    return (sh, el, wr, hand)


# label: (arms, head tilt, mouth)
POSES = [
    ("palm_up (shrug)", {"right": (20, 85, 35, "palm_up"), "left": (-20, -85, -35, "palm_up")}, 6.0, "oh"),
    ("stop", {"left": (-30, -125, 10, "stop")}, -3.0, "open"),
    ("index_up (wait)", {"right": (30, 130, -10, "index_up")}, 4.0, "open"),
    ("finger_heart", {"left": (-35, -130, 10, "finger_heart")}, -5.0, "smile"),
    ("ok", {"right": (30, 125, -10, "ok")}, 4.0, "smile"),
    ("two", {"left": (-35, -130, 10, "two")}, -5.0, "open"),
    ("hip_flat + hip_fist", {"right": reach("right", (110, 646), (0.12, 1), hand="hip_flat"),
                             "left": reach("left", (266, 646), (-0.12, 1), hand="hip_fist")}, 0.0, "smile"),
    # (her arms are short: the upper arm crosses in front, the forearm goes straight up, the hand reaches her chin)
    ("cover_mouth", {"right": (-50, -151, 0, "cover_mouth")}, 4.0, "oh"),
    ("clap", {"right": reach("right", (168, 585), (0.25, -1), hand="clap"),
              "left": reach("left", (208, 585), (-0.25, -1), hand="clap")}, 0.0, "open"),
    ("hang (both sides)", {"right": (4, 0, 0, "hang"), "left": (-4, 0, 0, "hang")}, 0.0, "smile"),
    ("offer", {"right": (25, 70, 0, "offer")}, 4.0, "smile"),
    ("palm_down", {"left": (-40, -70, 0, "palm_down")}, -3.0, "smile"),
    ("c_grip", {"right": (30, 120, 0, "c_grip")}, 4.0, "open"),
]


def pose_svg(arms, tilt, mouth):
    x, y, w, h = VIEW
    inner = CH.head_svg_v2(mouth_shape=mouth, pose=arms, tilt=tilt)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w * SCALE:.0f}" height="{h * SCALE:.0f}" viewBox="{x} {y} {w} {h}">'
            f'<defs>{CH.DEFS}</defs><rect x="-500" y="-500" width="3000" height="3000" fill="#fff"/>{inner}</svg>')


def sheet(out, cols=5):
    tiles = []
    for label, arms, tilt, mouth in POSES:
        im = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=pose_svg(arms, tilt, mouth).encode()))).convert("RGB")
        ImageDraw.Draw(im).text((8, 6), label, fill=(0, 0, 0), font=ImageFont.load_default(16))
        tiles.append(im)
    w, h = tiles[0].size
    rows = -(-len(tiles) // cols)
    S = Image.new("RGB", (cols * w, rows * h), "white")
    for i, t in enumerate(tiles):
        S.paste(t, ((i % cols) * w, (i // cols) * h))
    S.save(out)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "hands2_demo.png"
    sheet(out)
    print("wrote", out)
