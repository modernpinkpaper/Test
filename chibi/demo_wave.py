"""4-second wave test: her right arm rises, waves with the open hand from the hands sheet, and comes down.

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


def ease(t):
    return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, t)))


def pose_at(t):
    up = ease(t / 0.8) * (1 - ease((t - 3.1) / 0.8))                     # raise 0-0.8 s, lower 3.1-3.9 s
    wave = math.sin((t - 0.8) * 2 * math.pi * 1.6) * 22 * ease((t - 0.6) / 0.4) * (1 - ease((t - 2.9) / 0.4))
    sway = 4 * math.sin(t * 2 * math.pi * 0.5)
    return {"right": (92 * up, (68 + wave * 0.6) * up, (-5 + wave * 0.5) * up, "open" if up > 0.55 else None),
            "left": (-sway, -3 * up, 0)}


def frame_png(pose, path):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="400" height="850" viewBox="-15 150 400 850">'
           f'<defs>{CH.DEFS}</defs><rect x="-50" width="2000" height="2000" fill="#fff"/>{CH.head_svg_v2(pose=pose)}</svg>')
    cairosvg.svg2png(bytestring=svg.encode(), write_to=path)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "wave.mp4"
    with tempfile.TemporaryDirectory() as d:
        for i in range(int(SECONDS * FPS)):
            frame_png(pose_at(i / FPS), os.path.join(d, f"f{i:03d}.png"))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(d, "f%03d.png"),
                        "-pix_fmt", "yuv420p", "-c:v", "libx264", out], check=True)
    print("wrote", out)
