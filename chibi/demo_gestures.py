"""Gesture sampler: point at you, thumbs up, shrug, hand on hip, peace sign; with idle sway, blinks and expressions.

    python chibi/demo_gestures.py out.mp4 [frames_dir]      (needs ffmpeg)

Every gesture is a set of joint angles (shoulder, elbow, wrist in degrees, + a hand from the hands sheet) that the
rig blends in from the rest pose, holds with a little motion, and blends back out. Chibi arms are short: elbows stay
low and near the body, the forearms do most of the moving (as in her ChatGPT pose sheet).
"""
import math
import os
import subprocess
import sys
import tempfile

import cairosvg

import chibi_hair as CH

FPS = 24
VIEW = (-40, 150, 450, 860)
IN, OUT = 0.4, 0.4            # seconds to move into / out of a gesture

# name: (arms {side: (shoulder, elbow, wrist, hand)}, head tilt, mouth while holding, seconds held)
GESTURES = [
    ("point", {"right": (30, 130, -40, "point")}, 3.0, "open", 1.6),
    ("thumbs_up", {"left": (-25, -110, -50, "thumbs_up")}, -3.0, "smile", 1.4),
    ("shrug", {"right": (20, 85, 35, "open"), "left": (-20, -85, -35, "open")}, 6.0, "oh", 1.5),
    ("hand_on_hip", {"right": (45, -100, 0, "fist")}, -5.0, "smile", 1.4),
    ("peace", {"left": (-35, -130, 12, "peace")}, -5.0, "open", 1.6),
]
LEAD = 0.5                      # standing still at the start


def ease(t):
    return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, t)))


def timeline():
    t, out = LEAD, []
    for g in GESTURES:
        hold = g[4]
        out.append((t, t + IN, t + IN + hold, t + IN + hold + OUT, g))
        t += IN + hold + OUT + 0.15
    return out, t + 0.4


TL, SECONDS = timeline()


def state_at(t):
    sway = math.sin(t * 2 * math.pi * 0.45)
    arms = {"right": [0.0, 0.0, 0.0, None], "left": [0.0, 0.0, 0.0, None]}
    tilt, mouth, bob = 1.2 * sway, "smile", 0.0
    for t0, t1, t2, t3, (name, pose, g_tilt, g_mouth, _) in TL:
        if not t0 <= t < t3:
            continue
        k = ease((t - t0) / (t1 - t0)) if t < t1 else (1 - ease((t - t2) / (t3 - t2)) if t >= t2 else 1.0)
        holding = t1 <= t < t2
        pulse = math.sin((t - t1) * 2 * math.pi * 2.0) if holding else 0.0       # a little life while holding
        for side, (sh, el, wr, hand) in pose.items():
            extra = {"point": (0, 4 * pulse, 5 * pulse), "thumbs_up": (0, 5 * pulse, 0),
                     "shrug": (4 * pulse * (1 if side == "right" else -1), 0, 0), "peace": (0, 4 * pulse, 6 * pulse),
                     "hand_on_hip": (0, 0, 0)}[name]
            ke = ease(min(1.0, k * 1.7))        # the elbow leads: the hand comes up close to the body, not
            ks = ease(max(0.0, k * 1.4 - 0.4))  # swung out on a straight arm (the shoulder follows)
            arms[side] = [sh * ks + extra[0] * k, el * ke + extra[1] * k, wr * k + extra[2] * k,
                          hand if k > 0.35 else None]
        tilt += g_tilt * k
        bob = -1.5 * k + (0.8 * pulse * k if name in ("point", "peace", "thumbs_up") else 0)
        if holding and (t - t1) > 0.1:
            mouth = g_mouth
    left_idle = -2 * sway
    if arms["left"][3] is None and arms["left"][1] == 0:
        arms["left"][0] = left_idle
    blink = any(abs(t - b) < 0.055 for b in (1.2, 3.6, 5.9, 8.3, 10.0))
    return dict(pose={s: tuple(v) for s, v in arms.items()}, tilt=tilt, bob=bob, mouth=mouth,
                eyes="closed" if blink else "open")


def frame_svg(st):
    x, y, w, h = VIEW
    inner = CH.head_svg_v2(mouth_shape=st["mouth"], eyes=st["eyes"], pose=st["pose"], tilt=st["tilt"])
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
    out = sys.argv[1] if len(sys.argv) > 1 else "gestures.mp4"
    render(out, sys.argv[2] if len(sys.argv) > 2 else None)
    print("wrote", out, f"({SECONDS:.1f} s)")
