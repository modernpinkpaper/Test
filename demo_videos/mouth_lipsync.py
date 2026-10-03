"""Mouth-replacement lip-sync ("viseme" swapping) built from clips of the character talking.

1. library: find her lips in every frame of the talking clips (MediaPipe Face Landmarker), measure how
   open / wide the mouth is, and keep the best frame for each mouth shape (closed, slight, ah, oh, oo, ee).
2. voice: Whisper finds when each word is said; misaki turns words into sounds; sounds -> mouth shapes.
3. paste: for every frame of the base clip, fit the chosen mouth to her face and blend it in.

No GPU needed. For better timing use Rhubarb Lip Sync (free) instead of Whisper for step 2:
    python demo_videos/mouth_lipsync.py base_clip.mp4 voice.wav out.mp4 --library "clips/*.mp4" [--start 0.3]
        [--rhubarb path/to/rhubarb --text "what she says"]
"""
import argparse
import glob
import json
import os
import subprocess

import cv2
import imageio
import mediapipe as mp
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.join(HERE, "models", "face_landmarker.task")
# landmark numbers in MediaPipe's face mesh
EYE_L, EYE_R, NOSE_BOTTOM = 33, 263, 2
CORNER_L, CORNER_R, LIP_TOP_IN, LIP_BOT_IN = 61, 291, 13, 14
CHEEK_L, CHEEK_R, NOSE_TIP = 234, 454, 1
# the face is warped into this square so every mouth lines up: eyes at (130,120) and (270,120)
CANON = np.float32([[130, 120], [270, 120], [200, 215]])
PATCH = (125, 165, 270, 295)     # mouth area in that square: x0, y0, x1, y1
MOUTH_OVAL = ((197, 226), (60, 46))  # blend area around the lips: center, half-width/height
SHAPES = ["closed", "slight", "eh", "ah", "oh", "oo", "ee"]
LIPS_OUTER = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269, 267, 0, 37, 39, 40, 185]


def landmarker():
    opts = mp.tasks.vision.FaceLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=MODEL),
        running_mode=mp.tasks.vision.RunningMode.VIDEO, num_faces=1)
    return mp.tasks.vision.FaceLandmarker.create_from_options(opts)


def track(path):
    """Landmarks (478x2 pixels) for every frame of a clip, or None where no face was found."""
    frames = [f for f in imageio.get_reader(path)]
    out = []
    with landmarker() as lm:
        for i, f in enumerate(frames):
            res = lm.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(f)),
                                      int(i * 1000 / 24))
            if res.face_landmarks:
                h, w = f.shape[:2]
                out.append(np.array([[p.x * w, p.y * h] for p in res.face_landmarks[0]], np.float32))
            else:
                out.append(None)
    return frames, out


def to_canon(pts):
    """Similarity transform: face -> canonical square (uses eyes and nose, which don't move when talking)."""
    src = pts[[EYE_L, EYE_R, NOSE_BOTTOM]]
    M, _ = cv2.estimateAffinePartial2D(src, CANON)
    return M


def measures(pts):
    d = lambda a, b: float(np.linalg.norm(pts[a] - pts[b]))
    mouth_w = d(CORNER_L, CORNER_R)
    return dict(open=d(LIP_TOP_IN, LIP_BOT_IN) / mouth_w,
                width=mouth_w / d(CHEEK_L, CHEEK_R),
                facing=abs((pts[NOSE_TIP][0] - pts[CHEEK_L][0]) / (pts[CHEEK_R][0] - pts[CHEEK_L][0]) - 0.5))


def build_library(paths, out_dir):
    """Pick the best frame for each mouth shape and save it as a canonical patch (PNG)."""
    rows = []
    for p in paths:
        frames, lms = track(p)
        for i, (f, pts) in enumerate(zip(frames, lms)):
            if pts is None:
                continue
            m = measures(pts)
            if m["facing"] > 0.07:           # skip frames where she looks to the side
                continue
            rows.append((p, i, m, f, pts))
        print(f"tracked {os.path.basename(p)}: {sum(1 for r in rows if r[0] == p)} usable frames")
    op = np.array([r[2]["open"] for r in rows])
    wd = np.array([r[2]["width"] for r in rows]) / np.median([r[2]["width"] for r in rows])
    q = lambda a, x: np.percentile(a, x)
    targets = {   # (open, relative width) each shape aims for
        "closed": (q(op, 3), 1.0), "slight": (0.1, 1.0), "eh": (q(op, 65), 1.02), "ah": (q(op, 85), 1.0),
        "oh": (q(op, 70), 0.85), "oo": (q(op, 40), 0.78), "ee": (q(op, 45), 1.1),
    }
    os.makedirs(out_dir, exist_ok=True)
    info = {}
    for shape, (to, tw) in targets.items():
        score = np.abs(op - to) / (q(op, 95) - q(op, 5) + 1e-6) + np.abs(wd - tw) * 2
        k = int(np.argmin(score))
        p, i, m, f, pts = rows[k]
        M = to_canon(pts)
        canon = cv2.warpAffine(f, M, (400, 400), flags=cv2.INTER_CUBIC)
        x0, y0, x1, y1 = PATCH
        cv2.imwrite(os.path.join(out_dir, f"{shape}.png"), cv2.cvtColor(canon[y0:y1, x0:x1], cv2.COLOR_RGB2BGR))
        lips = (np.c_[pts[LIPS_OUTER], np.ones(len(LIPS_OUTER))] @ M.T).round(1).tolist()
        info[shape] = dict(clip=os.path.basename(p), frame=i, open=round(m["open"], 3), width=round(float(wd[k]), 3),
                           lips=lips)
    json.dump(info, open(os.path.join(out_dir, "library.json"), "w"), indent=1)
    return info


# ------------------------------------------------------------------ voice -> mouth shapes
def sound_to_shape(ch):
    if ch in "mbp":
        return "closed"
    if ch in "uʊwO":
        return "oo" if ch in "uʊw" else "oh"
    if ch in "ɔo":
        return "oh"
    if ch in "ɑaæʌIW":
        return "ah"
    if ch in "iɪeɛAjszʃʒʧʤθðY":
        return "ee"
    if ch in "əɜɚ":
        return "slight"
    return "slight"


# Rhubarb Lip Sync's cartoon mouth set -> her mouth shapes
RHUBARB = {"A": "closed", "B": "ee", "C": "eh", "D": "ah", "E": "oh", "F": "oo", "G": "closed", "H": "slight",
           "X": "closed"}


def shapes_from_rhubarb(rhubarb, wav, text, n_frames, fps, start):
    """Mouth shape for every frame from Rhubarb Lip Sync (github.com/DanielSWolf/rhubarb-lip-sync)."""
    import tempfile
    tmp = tempfile.mkdtemp()
    w16, cues, txt = (os.path.join(tmp, n) for n in ("v.wav", "cues.json", "t.txt"))
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", wav, "-ac", "1", "-ar", "16000", w16], check=True)
    cmd = [rhubarb, "-q", "-f", "json", "--extendedShapes", "GHX", w16, "-o", cues]
    if text:
        open(txt, "w").write(text)
        cmd[1:1] = ["-d", txt]
    subprocess.run(cmd, check=True)
    seq = ["closed"] * n_frames
    for c in json.load(open(cues))["mouthCues"]:
        for f in range(max(0, int((c["start"] + start) * fps)), min(n_frames, int((c["end"] + start) * fps) + 1)):
            seq[f] = RHUBARB[c["value"]]
    return seq


def shapes_for_voice(wav, n_frames, fps, start):
    from faster_whisper import WhisperModel
    from misaki import en
    g2p = en.G2P(trf=False, british=False)
    model = WhisperModel("base.en", device="cpu", compute_type="int8")
    segs, _ = model.transcribe(wav, word_timestamps=True)
    seq = ["closed"] * n_frames
    words = []
    vowels = set("ɑaæʌɔoəɜɚɪiʊuɛeAIOWY")
    for s in segs:
        for w in s.words:
            words.append((w.start + start, w.end + start, w.word.strip()))
            ph = [c for c in (g2p(w.word.strip())[0] or "") if c.isalpha() and c not in "ˈˌː"] or ["ə"]
            # vowels take about twice as long as consonants
            weights = np.array([2.0 if c in vowels else 1.0 for c in ph])
            edges = np.concatenate([[0], np.cumsum(weights) / weights.sum()])
            f0, f1 = (w.start + start) * fps, (w.end + start) * fps
            for f in range(max(0, int(f0)), min(n_frames, int(f1) + 1)):
                pos = min(0.999, max(0.0, (f + 0.5 - f0) / max(1e-6, f1 - f0)))
                k = int(np.searchsorted(edges, pos, side="right") - 1)
                seq[f] = sound_to_shape(ph[min(k, len(ph) - 1)])
    # a consonant shape that lasts only 1 frame is dropped (vowels always stay)
    for f in range(1, n_frames - 1):
        if seq[f] in ("closed", "slight") and seq[f] != seq[f - 1] and seq[f] != seq[f + 1]:
            seq[f] = seq[f - 1]
    return seq, words


# ------------------------------------------------------------------ paste
def paste_mouth(frame, pts, patch, lib_lips):  # patch/lib_lips may be a blend of shapes
    """Warp a canonical mouth patch onto this frame's face and blend it in.
    Only the area around the lips (new mouth + old mouth, a little wider) is replaced, and the
    patch's skin is tinted to match this frame so there is no visible square."""
    M = to_canon(pts)
    Minv = cv2.invertAffineTransform(M)
    x0, y0, x1, y1 = PATCH
    h, w = frame.shape[:2]
    canvas = np.zeros((400, 400, 3), np.uint8)
    canvas[y0:y1, x0:x1] = patch
    src = cv2.warpAffine(canvas, Minv, (w, h), flags=cv2.INTER_CUBIC).astype(np.float32)
    # mask: the new lips and the old lips, grown a bit, with soft edges
    new_lips = cv2.transform(np.float32(lib_lips)[None], Minv)[0]
    old_lips = pts[LIPS_OUTER]
    mask = np.zeros((h, w), np.uint8)
    cv2.fillConvexPoly(mask, cv2.convexHull(np.int32(np.vstack([new_lips, old_lips]))), 255)
    face_w = float(np.linalg.norm(pts[CHEEK_L] - pts[CHEEK_R]))
    grow = max(3, int(face_w * 0.045))
    mask = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * grow + 1, 2 * grow + 1)))
    ring = cv2.dilate(mask, np.ones((7, 7), np.uint8)) - mask
    soft = cv2.GaussianBlur(mask, (0, 0), grow * 0.6).astype(np.float32)[..., None] / 255
    # tint the patch to this frame's skin (compare a thin ring just outside the mask)
    if ring.any():
        r = ring > 0
        gain = (frame[r].mean(0) + 1) / (src[r].mean(0) + 1)
        src = np.clip(src * np.clip(gain, 0.8, 1.25), 0, 255)
    out = src * soft + frame.astype(np.float32) * (1 - soft)
    return out.astype(np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("voice")
    ap.add_argument("out")
    ap.add_argument("--library", nargs="+", required=True, help="talking clips to build the mouth library from")
    ap.add_argument("--lib-dir", default=None)
    ap.add_argument("--start", type=float, default=0.3)
    ap.add_argument("--size", type=int, default=1080, help="output width")
    ap.add_argument("--rhubarb", default=None, help="path to the rhubarb program (better timing)")
    ap.add_argument("--text", default=None, help="what the voice says (helps Rhubarb)")
    args = ap.parse_args()
    lib_dir = args.lib_dir or os.path.join(os.path.dirname(os.path.abspath(args.out)), "mouth_library")
    paths = sorted(p for pat in args.library for p in glob.glob(pat))
    info = build_library(paths, lib_dir)
    print(json.dumps(info, indent=1))
    patches = {s: cv2.cvtColor(cv2.imread(os.path.join(lib_dir, f"{s}.png")), cv2.COLOR_BGR2RGB) for s in SHAPES}
    lips = {s: info[s]["lips"] for s in SHAPES}

    frames, lms = track(args.base)
    fps = imageio.get_reader(args.base).get_meta_data()["fps"]
    if args.rhubarb:
        seq = shapes_from_rhubarb(args.rhubarb, args.voice, args.text, len(frames), fps, args.start)
    else:
        seq, words = shapes_for_voice(args.voice, len(frames), fps, args.start)
        print("words:", [(round(a, 2), w) for a, _, w in words])
    tmp = args.out.replace(".mp4", "_silent.mp4")
    wr = imageio.get_writer(tmp, fps=fps, codec="libx264", quality=8, macro_block_size=1)
    # animator's in-between: a big jump (closed <-> wide) gets one "slight" frame first
    small, big = {"closed", "oo"}, {"ah", "eh", "oh"}
    seq = list(seq)
    for i in range(1, len(seq)):
        if (seq[i - 1] in small and seq[i] in big) or (seq[i - 1] in big and seq[i] in small):
            seq[i] = "slight"
    last = None
    for f, pts, shape in zip(frames, lms, seq):
        if pts is not None and last is not None:
            pts = last * 0.5 + pts * 0.5          # steady the face position a little
        pts = pts if pts is not None else last
        last = pts
        mix, hull = patches[shape], lips[shape]
        img = paste_mouth(f, pts, mix, hull) if pts is not None else f
        h, w = img.shape[:2]
        img = cv2.resize(img, (args.size, int(h * args.size / w) // 2 * 2), interpolation=cv2.INTER_CUBIC)
        wr.append_data(img)
    wr.close()
    ff = "ffmpeg"
    subprocess.run([ff, "-loglevel", "error", "-y", "-i", tmp, "-itsoffset", str(args.start), "-i", args.voice,
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-shortest", args.out], check=True)
    os.remove(tmp)
    print("saved", args.out)


if __name__ == "__main__":
    main()
