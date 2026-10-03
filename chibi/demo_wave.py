"""4-second wave test: she lifts her right forearm (elbow low, by her chest, like her pose sheet), waves with the open hand from the
hands sheet beside her head, says "hi" (open mouth), blinks, tilts her head and bobs a little, then lowers the arm.

    python chibi/demo_wave.py out.mp4          (needs ffmpeg)
"""
import math
import os
import subprocess
import sys
import tempfile

import cairosvg

import chibi_hair as CH

FPS, SECONDS = 24, 4.0
VIEW = (-40, 150, 450, 860)          # x, y, w, h: wide enough that a raised hand never leaves the frame


def ease(t):
    return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, t)))


def ramp(t, a, b):
    return ease((t - a) / (b - a))


def state_at(t):
    up = ramp(t, 0.0, 0.8) * (1 - ramp(t, 3.1, 3.9))                      # raise 0-0.8 s, lower 3.1-3.9 s
    waving = ramp(t, 0.7, 1.0) * (1 - ramp(t, 2.8, 3.1))
    w = math.sin((t - 0.9) * 2 * math.pi * 1.7)                           # 1.7 waves per second
    swing = waving * (w * 8 - 6)                                           # rocks at the elbow, mostly outward
    # chibi arms are short: the upper arm only lifts ~35 deg (elbow stays low, by the chest) and the forearm
    # folds up to put the hand beside the cheek (as in her ChatGPT pose sheet)
    shoulder = 35 * up
    elbow = 130 * up + swing
    wrist = -12 * up + waving * w * 8
    hand = "open" if up > 0.55 else None       # swapped in one frame, mid-swing (a fade shows two hands at once)
    sway = math.sin(t * 2 * math.pi * 0.5)
    return dict(
        pose={"right": (shoulder, elbow, wrist, hand), "left": (-2 * sway - 3 * up, -4 * up, 0)},
        tilt=4 * waving * (0.7 + 0.3 * w) + 1.5 * sway,                      # head leans towards the waving hand
        bob=-2.0 * up + 1.2 * math.sin(t * 2 * math.pi * 1.7) * waving,      # a small lift and bounce with the wave
        mouth="open" if 1.0 <= t < 2.4 else "smile",                         # "hi!"
        eyes="closed" if 2.55 <= t < 2.66 else "open",                       # one blink
    )


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
    out = sys.argv[1] if len(sys.argv) > 1 else "wave.mp4"
    render(out, sys.argv[2] if len(sys.argv) > 2 else None)
    print("wrote", out)
