"""Expressions demo: each emotion from chibi_expressions paired with a gesture. The face changes during a blink (so
it never snaps), the arms blend in with the elbow leading, and she sways and bobs a little the whole time.

    python chibi/demo_expressions.py out.mp4 [frames_dir]      (needs ffmpeg)
"""
import math
import os
import subprocess
import sys
import tempfile

import cairosvg

import chibi_expressions as X
import chibi_hair as CH

FPS = 24
VIEW = (-40, 150, 450, 860)
IN, OUT, BLINK = 0.4, 0.4, 0.11

# (expression, arms {side: (shoulder, elbow, wrist, hand)}, head tilt, seconds held)
BEATS = [
    ("happy", {"right": (35, 130, -12, "open")}, 4, 1.4),                                    # hi!
    ("smug", {"right": (45, -100, 0, "fist")}, -6, 1.4),                                     # hand on hip
    ("eye_roll", {"right": (20, 85, 35, "open"), "left": (-20, -85, -35, "open")}, 5, 1.5),  # whatever...
    ("angry", {"right": (30, 130, -40, "point")}, 3, 1.4),                                   # you!
    ("surprised", {"right": (30, 110, 0, "open"), "left": (-30, -110, 0, "open")}, 0, 1.3),  # oh!
    ("sad", {}, -4, 1.2),
    ("happy", {"right": (0, -165, 15, "open"), "left": (0, 165, -15, "open")}, -3, 1.3),     # aww (hands on chest)
    ("wink", {"left": (-35, -130, 12, "peace")}, -6, 1.5),                                   # peace!
    ("calm", {}, 2, 1.0),
]
LEAD = 0.4


def ease(t):
    return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, t)))


def timeline():
    t, out = LEAD, []
    for b in BEATS:
        out.append((t, t + IN, t + IN + b[3], t + IN + b[3] + OUT, b))
        t += IN + b[3] + OUT + 0.1
    return out, t + 0.3


TL, SECONDS = timeline()


def state_at(t):
    sway = math.sin(t * 2 * math.pi * 0.45)
    arms = {"right": [0.0, 0.0, 0.0, None], "left": [-2 * sway, 0.0, 0.0, None]}
    tilt, bob, face, blink = 1.2 * sway, 0.0, "neutral", False
    for t0, t1, t2, t3, (name, pose, g_tilt, _) in TL:
        if abs(t - t0) < BLINK / 2 or abs(t - t2 - 0.1) < BLINK / 2:
            blink = True                                   # the face changes behind a blink
        if not t0 <= t < t3:
            continue
        k = ease((t - t0) / (t1 - t0)) if t < t1 else (1 - ease((t - t2) / (t3 - t2)) if t >= t2 else 1.0)
        pulse = math.sin((t - t1) * 2 * math.pi * 2.0) if t1 <= t < t2 else 0.0
        if t < t2 + 0.1:
            face = name
        for side, (sh, el, wr, hand) in pose.items():
            ke, ks = ease(min(1.0, k * 1.7)), ease(max(0.0, k * 1.4 - 0.4))   # the elbow leads
            arms[side] = [sh * ks, el * ke + 4 * pulse * k * (1 if el > 0 else -1), wr * k, hand if k > 0.35 else None]
        tilt += g_tilt * k
        bob = -1.5 * k + 0.7 * pulse * k
    st = X.expression(face)
    if blink:
        st["eyes"] = "closed"
    return dict(expr=st, pose={s: tuple(v) for s, v in arms.items()}, tilt=tilt, bob=bob)


def frame_svg(st):
    x, y, w, h = VIEW
    inner = CH.head_svg_v2(**st["expr"], pose=st["pose"], tilt=st["tilt"])
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="{x} {y} {w} {h}">'
            f'<defs>{CH.DEFS}</defs><rect x="-500" y="-500" width="3000" height="3000" fill="#fff"/>'
            f'<g transform="translate(0,{st["bob"]:.2f})">{inner}</g></svg>')


def render(out, frames_dir=None):
    with tempfile.TemporaryDirectory() as d:
        d = frames_dir or d
        for i in range(int(SECONDS * FPS)):
            cairosvg.svg2png(bytestring=frame_svg(state_at(i / FPS)).encode(), write_to=os.path.join(d, f"f{i:03d}.png"))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(d, "f%03d.png"),
                        "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2:color=white", "-pix_fmt", "yuv420p", "-c:v", "libx264", out],
                       check=True)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "expressions.mp4"
    render(out, sys.argv[2] if len(sys.argv) > 2 else None)
    print("wrote", out, f"({SECONDS:.1f} s)")
