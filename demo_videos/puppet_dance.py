"""Make the puppet copy a tracked dance and lip-sync to the song.

    python demo_videos/puppet_dance.py dance_pose.json dance.mp4 out.mp4 [--end 14.8]

dance_pose.json comes from dance_capture.py. The song is taken from dance.mp4 (or any audio/video file).
The mouth follows the loudness of the singing range of the song (about 250-3000 Hz).
"""
import argparse
import json
import math
import os
import subprocess

import imageio
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw

import puppet as P

W, H, FPS, SR = 1080, 1920, 30, 16000


def ang(a, b, w, h):
    return math.degrees(math.atan2((b[0] - a[0]) * w, (b[1] - a[1]) * h))


def mid(a, b):
    return [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]


def pose_angles(j, w, h, prev=None):
    """World angles for every puppet part from one frame of tracked joints."""
    sh, hp = mid(j["l_shoulder"], j["r_shoulder"]), mid(j["l_hip"], j["r_hip"])
    a = {}
    a["torso"] = max(-35, min(35, ang(sh, hp, w, h)))
    tilt = -math.degrees(math.atan2((j["l_hip"][1] - j["r_hip"][1]) * h, (j["l_hip"][0] - j["r_hip"][0]) * w))
    a["hips"] = max(-20, min(20, tilt))
    a["head"] = max(-20, min(20, 0.7 * (ang(j["nose"], sh, w, h) - a["torso"])))
    for side, ms in (("r", "r"), ("l", "l")):
        a[f"upper_arm_{side}"] = ang(j[f"{ms}_shoulder"], j[f"{ms}_elbow"], w, h)
        a[f"lower_arm_{side}"] = ang(j[f"{ms}_elbow"], j[f"{ms}_wrist"], w, h)
        knee_ok, ankle_ok = j[f"{ms}_knee"][1] < 0.98, j[f"{ms}_ankle"][1] < 0.98
        up = ang(j[f"{ms}_hip"], j[f"{ms}_knee"], w, h) if knee_ok else a["hips"]
        lo = ang(j[f"{ms}_knee"], j[f"{ms}_ankle"], w, h) if ankle_ok else up * 0.4
        a[f"upper_leg_{side}"] = max(-45, min(45, up))
        a[f"lower_leg_{side}"] = max(-45, min(45, lo))
    return a


def song_levels(media, n_frames, start=0.0):
    """Singing loudness (0-1) for every video frame."""
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    raw = subprocess.run([ff, "-loglevel", "error", "-ss", str(start), "-i", media, "-ac", "1", "-ar", str(SR),
                          "-f", "s16le", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    hop = SR // FPS
    lv = []
    for i in range(n_frames):
        seg = x[i * hop:i * hop + hop * 2]
        if len(seg) < 64:
            lv.append(0.0)
            continue
        spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
        f = np.fft.rfftfreq(len(seg), 1 / SR)
        lv.append(float(spec[(f > 250) & (f < 3000)].sum()))
    lv = np.array(lv)
    base = np.convolve(lv, np.ones(45) / 45, "same")          # the steady part of the music
    v = np.clip(lv - 0.7 * base, 0, None)
    return np.clip(v / (np.percentile(v, 95) + 1e-6), 0, 1)


def mouth_for(level, fr):
    if level < 0.15:
        return "closed"
    if level < 0.4:
        return "slight"
    if level < 0.7:
        return ("ee", "oh")[(fr // 4) % 2]
    return "ah"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pose")
    ap.add_argument("song")
    ap.add_argument("out")
    ap.add_argument("--end", type=float, default=None)
    args = ap.parse_args()
    d = json.load(open(args.pose))
    frames = [f for f in d["frames"] if args.end is None or f["t"] < args.end]
    vw, vh = d["width"], d["height"]
    n = len(frames)
    hips_x = np.array([mid(f["joints"]["l_hip"], f["joints"]["r_hip"])[0] if f["joints"] else np.nan for f in frames])
    hips_y = np.array([mid(f["joints"]["l_hip"], f["joints"]["r_hip"])[1] if f["joints"] else np.nan for f in frames])
    mx, my = np.nanmean(hips_x), np.nanmean(hips_y)
    levels = song_levels(args.song, n)

    pup = P.Puppet(scale=1.15)
    bg = Image.new("RGBA", (W, H))
    g = np.linspace(0, 1, H)[:, None]
    top, bot = np.array([255, 228, 240]), np.array([250, 180, 210])
    bg = Image.fromarray(np.broadcast_to((top * (1 - g) + bot * g)[:, None, :].reshape(H, 1, 3),
                                         (H, W, 3)).astype(np.uint8)).convert("RGBA")
    silent = args.out.replace(".mp4", "_silent.mp4")
    wr = imageio.get_writer(silent, fps=FPS, codec="libx264", quality=8, macro_block_size=1)
    last = dict(P.REST)
    hair, hair_v, prev_head = 0.0, 0.0, 0.0
    mouth = "closed"
    for i, f in enumerate(frames):
        a = pose_angles(f["joints"], vw, vh) if f["joints"] else last
        last = a
        # hair swings the opposite way the head moves, then settles (a spring)
        head_world = a["torso"] + a["head"]
        hair_v += -(head_world - prev_head) * 0.6 - hair * 0.15
        hair_v *= 0.8
        hair = max(-12, min(12, hair + hair_v))
        prev_head = head_world
        a = dict(a, hair=hair)
        x = 540 + ((hips_x[i] if not np.isnan(hips_x[i]) else mx) - mx) * W * 0.9
        y = 930 + ((hips_y[i] if not np.isnan(hips_y[i]) else my) - my) * H * 0.4
        if i % 2 == 0:
            mouth = mouth_for(levels[i], i)
        blink = i % 105
        eyes = "closed" if blink in (1, 2) else "half" if blink in (0, 3) else "open"
        brows = "raised" if levels[i] > 0.8 else "neutral"
        frame = bg.copy()
        ImageDraw.Draw(frame, "RGBA").ellipse([x - 170, 1690, x + 170, 1740], fill=(200, 90, 140, 40))
        pup.render(frame, (x, y), a, face=(eyes, brows, mouth))
        wr.append_data(np.asarray(frame.convert("RGB")))
        if i % 60 == 0:
            print(f"frame {i}/{n}")
    wr.close()
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ff, "-loglevel", "error", "-y", "-i", silent, "-i", args.song, "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-shortest", args.out], check=True)
    os.remove(silent)
    print("saved", args.out)


if __name__ == "__main__":
    main()
