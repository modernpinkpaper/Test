"""Copy a dance from a video: track the body with MediaPipe Pose, frame by frame.

Output:
  <name>_pose.json      joint positions (0-1 of the frame) and 2D joint angles for every frame
  <name>_skeleton.mp4   the video with the tracked skeleton drawn on top (to check the tracking)

Setup (once):
    pip install mediapipe opencv-python-headless "numpy<2"
    models/pose_landmarker_full.task from
    https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task
Run:
    python demo_videos/dance_capture.py my_dance.mp4 [--heavy] [--person right] [--end 16]
    --person left|right|biggest  which person to follow when there are several (default: biggest)
    --end SECONDS                stop early (for example before an app logo screen)
"""
import argparse
import json
import math
import os

import cv2
import mediapipe as mp
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))

# MediaPipe's 33 points; these are the ones a 2D puppet needs
J = dict(nose=0, l_shoulder=11, r_shoulder=12, l_elbow=13, r_elbow=14, l_wrist=15, r_wrist=16,
         l_hip=23, r_hip=24, l_knee=25, r_knee=26, l_ankle=27, r_ankle=28)
BONES = [("l_shoulder", "r_shoulder"), ("l_hip", "r_hip"), ("l_shoulder", "l_hip"), ("r_shoulder", "r_hip"),
         ("l_shoulder", "l_elbow"), ("l_elbow", "l_wrist"), ("r_shoulder", "r_elbow"), ("r_elbow", "r_wrist"),
         ("l_hip", "l_knee"), ("l_knee", "l_ankle"), ("r_hip", "r_knee"), ("r_knee", "r_ankle")]
# puppet part -> (from joint, to joint): its angle is the direction of that bone
PARTS = {"upper_arm_l": ("l_shoulder", "l_elbow"), "lower_arm_l": ("l_elbow", "l_wrist"),
         "upper_arm_r": ("r_shoulder", "r_elbow"), "lower_arm_r": ("r_elbow", "r_wrist"),
         "upper_leg_l": ("l_hip", "l_knee"), "lower_leg_l": ("l_knee", "l_ankle"),
         "upper_leg_r": ("r_hip", "r_knee"), "lower_leg_r": ("r_knee", "r_ankle")}


def angle(a, b, w, h):
    """Bone direction in degrees, 0 = straight down, positive = counter-clockwise on screen."""
    dx, dy = (b[0] - a[0]) * w, (b[1] - a[1]) * h
    return math.degrees(math.atan2(dx, dy))


def cx(p):
    return (p[J["l_hip"]].x + p[J["r_hip"]].x) / 2


def pick(poses, how, last=None):
    """Choose one person: the biggest (most of the frame), or the left-most / right-most.
    After the first frame, stay with the person nearest to where she was (or none if she's gone)."""
    if last is not None:
        near = min(poses, key=lambda p: abs(cx(p) - last))
        return near if abs(cx(near) - last) < 0.12 else None
    def size(p):
        ys = [p[J[k]].y for k in ("nose", "l_ankle", "r_ankle")]
        return max(ys) - min(ys)
    if how == "left":
        return min(poses, key=cx)
    if how == "right":
        return max(poses, key=cx)
    return max(poses, key=size)


def smooth(frames, k=5):
    """Moving average over time so the puppet doesn't jitter."""
    if not frames:
        return frames
    had = [bool(f["joints"]) for f in frames]
    for key in J:
        xs = np.array([f["joints"][key][0] if h else np.nan for f, h in zip(frames, had)])
        ys = np.array([f["joints"][key][1] if h else np.nan for f, h in zip(frames, had)])
        for arr in (xs, ys):
            ok = ~np.isnan(arr)
            if ok.sum() > 1:
                arr[~ok] = np.interp(np.flatnonzero(~ok), np.flatnonzero(ok), arr[ok])
        pad = k // 2
        xs = np.convolve(np.pad(xs, pad, mode="edge"), np.ones(k) / k, "valid")
        ys = np.convolve(np.pad(ys, pad, mode="edge"), np.ones(k) / k, "valid")
        for f, x, y in zip(frames, xs, ys):
            f["joints"][key] = [round(float(x), 4), round(float(y), 4)]
    return frames


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--heavy", action="store_true", help="slower but more accurate model")
    ap.add_argument("--person", default="biggest", choices=["biggest", "left", "right"])
    ap.add_argument("--end", type=float, default=None)
    args = ap.parse_args()
    model = os.path.join(HERE, "models", f"pose_landmarker_{'heavy' if args.heavy else 'full'}.task")
    base = os.path.splitext(args.video)[0]

    cap = cv2.VideoCapture(args.video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    opts = mp.tasks.vision.PoseLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=model),
        running_mode=mp.tasks.vision.RunningMode.VIDEO, num_poses=3)
    out = cv2.VideoWriter(base + "_skeleton.mp4", cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    frames, i, found, last = [], 0, 0, None
    with mp.tasks.vision.PoseLandmarker.create_from_options(opts) as lm:
        while True:
            ok, img = cap.read()
            if not ok or (args.end and i / fps >= args.end):
                break
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            res = lm.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), int(i * 1000 / fps))
            joints = {}
            p = pick(res.pose_landmarks, args.person, last) if res.pose_landmarks else None
            if p is not None:
                found += 1
                last = cx(p)
                joints = {k: [p[v].x, p[v].y] for k, v in J.items()}
            frames.append({"t": round(i / fps, 3), "joints": joints})
            i += 1
            # draw raw tracking on the preview
            if joints:
                for a, b in BONES:
                    pa = (int(joints[a][0] * w), int(joints[a][1] * h))
                    pb = (int(joints[b][0] * w), int(joints[b][1] * h))
                    cv2.line(img, pa, pb, (80, 255, 120), max(2, w // 200))
                for x, y in joints.values():
                    cv2.circle(img, (int(x * w), int(y * h)), max(3, w // 120), (255, 80, 200), -1)
            out.write(img)
    out.release()
    frames = smooth([f for f in frames]) if found else frames
    for f in frames:
        if f["joints"]:
            f["angles"] = {part: round(angle(f["joints"][a], f["joints"][b], w, h), 1)
                           for part, (a, b) in PARTS.items()}
    json.dump({"fps": fps, "width": w, "height": h, "frames": frames}, open(base + "_pose.json", "w"))
    print(f"{i} frames, body found in {found} ({found * 100 // max(1, i)}%)")
    print("saved", base + "_pose.json", "and", base + "_skeleton.mp4")


if __name__ == "__main__":
    main()
