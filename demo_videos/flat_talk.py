"""Talking head from ONE flat cartoon picture: drawn mouth shapes, blinks, brow lifts, a tiny head sway.

Her face features are found once with MediaPipe; her own mouth is erased and new mouths are drawn in her
style for each sound (timing from Rhubarb Lip Sync). When she is quiet her original smile is shown.
No GPU, no AI video.

    python demo_videos/flat_talk.py her.png voice.wav out.mp4 --rhubarb path/to/rhubarb --text "what she says"
"""
import argparse
import json
import math
import os
import random
import subprocess
import tempfile

import cv2
import imageio
import mediapipe as mp
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
LIPS = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269, 267, 0, 37, 39, 40, 185]
EYES = {"l": (33, 133), "r": (263, 362)}
BROWS = {"l": [70, 63, 105, 66, 107, 55, 65, 52, 53, 46], "r": [300, 293, 334, 296, 336, 285, 295, 282, 283, 276]}
LINE = (58, 32, 26)
UPPER_INNER = [78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308]


def landmarks(img):
    opts = mp.tasks.vision.FaceLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=os.path.join(HERE, "models", "face_landmarker.task")),
        running_mode=mp.tasks.vision.RunningMode.IMAGE, num_faces=1)
    with mp.tasks.vision.FaceLandmarker.create_from_options(opts) as lm:
        r = lm.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=img))
    h, w = img.shape[:2]
    return np.array([[p.x * w, p.y * h] for p in r.face_landmarks[0]], np.float32)


def skin_color(img, pts):
    """Median colour of the cheeks."""
    samples = [img[int(pts[i][1]), int(pts[i][0])] for i in (205, 425, 50, 280, 187, 411)]
    return np.median(np.array(samples), 0)


def feature_mask(img, center, box, skin, thr=80):
    """Pixels around `center` that are clearly not skin (the drawn eye or brow)."""
    x0, y0, x1, y1 = box
    reg = img[y0:y1, x0:x1].astype(int)
    m = np.abs(reg - skin).sum(2) > thr
    lab, n = ndimage.label(ndimage.binary_closing(m, iterations=2))
    cy, cx = int(center[1]) - y0, int(center[0]) - x0
    k = lab[min(max(cy, 0), lab.shape[0] - 1), min(max(cx, 0), lab.shape[1] - 1)]
    if k == 0 and n:
        k = int(np.argmax(ndimage.sum(m, lab, range(1, n + 1)))) + 1
    full = np.zeros(img.shape[:2], bool)
    full[y0:y1, x0:x1] = ndimage.binary_fill_holes(lab == k)
    return full


class Face:
    def __init__(self, img):
        self.img = img
        pts = self.pts = landmarks(img)
        self.skin = skin_color(img, pts)
        # mouth geometry
        self.m_left, self.m_right = pts[61], pts[291]
        self.m_center = (pts[0] + pts[17]) / 2
        self.m_width = float(np.linalg.norm(self.m_right - self.m_left))
        self.m_angle = math.degrees(math.atan2(self.m_right[1] - self.m_left[1], self.m_right[0] - self.m_left[0]))
        lip_mask = np.zeros(img.shape[:2], np.uint8)
        cv2.fillConvexPoly(lip_mask, cv2.convexHull(pts[LIPS].astype(np.int32)), 255)
        lip_mask = cv2.dilate(lip_mask, np.ones((9, 9), np.uint8))
        self.no_mouth = cv2.inpaint(img, lip_mask, 7, cv2.INPAINT_TELEA)
        # eyes: an oval from the eye corners down to just under the drawn eye
        self.eyes = {}
        for side, (a, b) in EYES.items():
            ew = float(np.linalg.norm(pts[a] - pts[b]))
            brow_bottom = pts[BROWS[side]][:, 1].max()
            low = pts[145 if side == "l" else 374][1] + ew * 0.42
            xs = sorted([pts[a][0], pts[b][0]])
            self.eyes[side] = dict(box=(xs[0] - ew * 0.2, brow_bottom + 3, xs[1] + ew * 0.2, low))
        # her own lips, split into an upper and a lower lip at the dark line where they meet
        hull = cv2.convexHull(pts[LIPS].astype(np.int32))
        lips = np.zeros(img.shape[:2], np.uint8)
        cv2.fillConvexPoly(lips, hull, 255)
        lips = cv2.dilate(lips, np.ones((3, 3), np.uint8)) > 0
        dark = img.astype(int).sum(2)
        ys_all, xs_all = np.where(lips)
        line_y = np.full(img.shape[1], np.nan)
        for x in range(xs_all.min(), xs_all.max() + 1):
            col = np.where(lips[:, x])[0]
            if len(col):
                line_y[x] = col[np.argmin(dark[col, x])]
        ok = ~np.isnan(line_y)
        xs_ok = np.flatnonzero(ok)
        line_y[ok] = np.convolve(np.pad(line_y[ok], 3, mode="edge"), np.ones(7) / 7, "valid")
        yy = np.arange(img.shape[0])[:, None]
        above = (yy < line_y[None, :] - 1.5) & ok[None, :]
        below = (yy > line_y[None, :] + 1.5) & ok[None, :]

        def soft(mask):
            a = cv2.GaussianBlur(ndimage.binary_erosion(mask).astype(np.float32), (0, 0), 0.8)
            return (np.clip(a, 0, 1) * 255).astype(np.uint8)
        self.upper = np.dstack([img, soft(lips & above)])
        self.lower = np.dstack([img, soft(lips & below)])
        self.split_y = float(np.nanmean(line_y[xs_ok]))
        # eyelid colour: skin sampled in a ring around each eye (dark lashes/brows left out)
        for side, e in self.eyes.items():
            x0, y0, x1, y1 = e["box"]
            c, ax = (int((x0 + x1) / 2), int((y0 + y1) / 2)), (int((x1 - x0) / 2), int((y1 - y0) / 2))
            inner, outer = np.zeros(img.shape[:2], np.uint8), np.zeros(img.shape[:2], np.uint8)
            cv2.ellipse(inner, c, (ax[0] + 6, ax[1] + 6), 0, 0, 360, 255, -1)
            cv2.ellipse(outer, c, (ax[0] + 16, ax[1] + 16), 0, 0, 360, 255, -1)
            ring = (outer > 0) & (inner == 0) & (np.abs(img.astype(int) - self.skin).sum(2) < 60)
            e["lid"] = np.median(img[ring], 0) if ring.any() else self.skin
        # brows: the dark pixels inside each brow's area
        self.brows = {}
        dark = img.astype(int).sum(2)
        for side, idx in BROWS.items():
            p = pts[idx]
            m = np.zeros(img.shape[:2], np.uint8)
            cv2.fillConvexPoly(m, cv2.convexHull(p.astype(np.int32)), 255)
            m = cv2.dilate(m, np.ones((11, 11), np.uint8)) > 0
            self.brows[side] = m & (dark < 260)
        # brow lift = a gentle upward stretch centred on each brow (no cutting, no traces)
        wgt = np.zeros(img.shape[:2], np.float32)
        for m in self.brows.values():
            wgt = np.maximum(wgt, m.astype(np.float32))
        wgt = cv2.GaussianBlur(cv2.dilate(wgt, np.ones((9, 9), np.uint8)), (0, 0), 7)
        self.brow_weight = np.clip(wgt / (wgt.max() + 1e-6) * 1.3, 0, 1)
        brow_any = (self.brows["l"] | self.brows["r"]).astype(np.uint8) * 255
        self.no_brows = cv2.inpaint(img, cv2.dilate(brow_any, np.ones((9, 9), np.uint8)), 7, cv2.INPAINT_TELEA)
        self.brows = {k: ndimage.binary_dilation(v, iterations=2) for k, v in self.brows.items()}

    def frame(self, mouth="rest", blink=0.0, brow_up=0.0):
        """blink 0 (open) .. 1 (closed); brow_up in pixels."""
        base = self.img if mouth == "rest" else self.no_mouth
        out = base.copy()
        if brow_up > 0.2:
            h, w = out.shape[:2]
            gx, gy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
            out = cv2.remap(out, gx, gy + brow_up * self.brow_weight, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        if blink > 0.05:
            out = self.close_eyes(out, blink)
        if mouth != "rest":
            out = self.draw_mouth(out, mouth)
        return out

    def close_eyes(self, out, amount):
        """Her own (cleaned) skin comes down over an oval eye area; when closed, a curved lash line."""
        s = 4
        out = out.copy()
        for side, e in self.eyes.items():
            x0, y0, x1, y1 = e["box"]
            m = np.zeros(out.shape[:2], np.float32)
            cv2.ellipse(m, (int((x0 + x1) / 2), int((y0 + y1) / 2)), (int((x1 - x0) / 2) + 5, int((y1 - y0) / 2) + 3),
                        0, 0, 360, 1.0, -1)
            cut = int(y0 - 3 + (y1 - y0 + 6) * min(1.0, amount))
            m[cut:] = 0
            m = cv2.GaussianBlur(m, (0, 0), 1.3)[..., None]
            lid = np.empty_like(out)
            lid[:] = e["lid"]
            out = (lid * m + out * (1 - m)).astype(np.uint8)
        pil = Image.fromarray(out)
        for side, e in self.eyes.items():
            x0, y0, x1, y1 = e["box"]
            bw, bh = (x1 - x0) * s, (y1 - y0) * s
            layer = Image.new("RGBA", (int(bw + 16 * s), int(bh + 16 * s)), (0, 0, 0, 0))
            d = ImageDraw.Draw(layer)
            if amount > 0.6:
                ly = 8 * s + bh * 0.55
                d.arc([8 * s, ly - bh * 0.3, 8 * s + bw, ly + bh * 0.16], 12, 168, fill=LINE + (255,), width=int(2.8 * s))
                ox = 8 * s + (bw * 0.97 if side == "l" else bw * 0.03)
                d.line([(ox, ly - bh * 0.05), (ox + (1 if side == "l" else -1) * 6 * s, ly - bh * 0.22)],
                       fill=LINE + (255,), width=int(2.2 * s))
            else:
                cut = 8 * s + bh * min(1.0, amount)
                d.arc([8 * s + bw * 0.08, cut - bh * 0.25, 8 * s + bw * 0.92, cut + bh * 0.25], 195, 345,
                      fill=LINE + (255,), width=int(2.6 * s))
            layer = layer.resize((layer.width // s, layer.height // s), Image.LANCZOS)
            pil.paste(layer, (int(x0) - 8, int(y0) - 8), layer)
        return np.array(pil)

    def draw_mouth(self, out, shape):
        """Open her own lips: the lower lip moves down, the upper lip up a little, the inside is drawn."""
        w = self.m_width
        # (width factor, opening as a share of mouth width, teeth, tongue)
        spec = {"A": (1.0, 0.0, False, False), "B": (1.0, 0.1, True, False), "C": (0.97, 0.2, True, False),
                "D": (0.95, 0.34, True, True), "E": (0.8, 0.28, False, True), "F": (0.66, 0.16, False, False),
                "G": (1.0, 0.07, True, False), "H": (0.95, 0.22, True, True)}[shape]
        wf, op, teeth, tongue = spec
        gap = w * op
        cx = float(self.m_center[0])
        pil = Image.fromarray(out)

        def lip(rgba, dy):
            im = Image.fromarray(rgba)
            ys, xs = np.where(rgba[..., 3] > 0)
            box = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
            part = im.crop(box)
            nw = max(1, int(part.width * wf))
            nh = int(part.height * (1.12 if wf < 0.85 else 1.0))
            part = part.resize((nw, nh), Image.LANCZOS)
            return part, (int(cx - nw / 2 + (box[0] + box[2]) / 2 - cx), int(box[1] + dy))

        up, up_at = lip(self.upper, -gap * 0.25)
        lo, lo_at = lip(self.lower, gap * 0.75)
        if gap > 0.5:
            s = 4
            iw, ih = w * wf * 0.86, gap + w * 0.06
            inside = Image.new("RGBA", (int(iw * s), int(ih * s)), (0, 0, 0, 0))
            m = Image.new("L", inside.size, 0)
            ImageDraw.Draw(m).ellipse([0, 0, inside.width - 1, inside.height - 1], fill=255)
            fill = Image.new("RGBA", inside.size, (92, 30, 40, 255))
            fd = ImageDraw.Draw(fill)
            if tongue:
                fd.ellipse([inside.width * 0.2, inside.height * 0.55, inside.width * 0.8, inside.height * 1.4],
                           fill=(214, 100, 110, 255))
            if teeth:
                fd.rectangle([0, 0, inside.width, inside.height * 0.38], fill=(250, 248, 244, 255))
            inside.paste(fill, (0, 0), m)
            inside = inside.resize((int(iw), int(ih)), Image.LANCZOS)
            pil.paste(inside, (int(cx - iw / 2), int(self.split_y - gap * 0.25 - w * 0.03)), inside)
        pil.paste(lo, lo_at, lo)
        pil.paste(up, up_at, up)
        return np.array(pil)


def rhubarb_cues(rhubarb, wav, text):
    tmp = tempfile.mkdtemp()
    w16, cues, txt = (os.path.join(tmp, n) for n in ("v.wav", "c.json", "t.txt"))
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", wav, "-ac", "1", "-ar", "16000", w16], check=True)
    cmd = [rhubarb, "-q", "-f", "json", "--extendedShapes", "GHX", w16, "-o", cues]
    if text:
        open(txt, "w").write(text)
        cmd[1:1] = ["-d", txt]
    subprocess.run(cmd, check=True)
    return json.load(open(cues))["mouthCues"]


def add_caption(frame, text, t, dur):
    """Word-by-word captions; words are timed by their length across the voice."""
    import truth_bomb as T
    words = text.split()
    if t < 0 or t > dur + 0.3:
        return frame
    lens = np.cumsum([len(w) + 2 for w in words]) / sum(len(w) + 2 for w in words)
    shown = int(np.searchsorted(lens, min(1.0, t / dur), side="right")) + 1
    sentence_start = max([i for i, w in enumerate(words[:shown]) if i == 0 or words[i - 1][-1] in ".!?"])
    pil = Image.fromarray(frame)
    T.draw_caption(ImageDraw.Draw(pil), [(w, False) for w in words[sentence_start:shown]],
                   shown - sentence_start, 0.0)
    return np.array(pil)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("voice")
    ap.add_argument("out")
    ap.add_argument("--rhubarb", required=True)
    ap.add_argument("--text", default=None)
    ap.add_argument("--start", type=float, default=0.5)
    ap.add_argument("--captions", action="store_true", help="word-by-word captions (needs --text)")
    args = ap.parse_args()

    img = cv2.cvtColor(cv2.imread(args.image), cv2.COLOR_BGR2RGB)
    face = Face(img)
    cues = rhubarb_cues(args.rhubarb, args.voice, args.text)
    import soundfile as sf
    a, sr = sf.read(args.voice)
    total = args.start + len(a) / sr + 0.8
    n = int(total * FPS)
    shapes = ["rest"] * n
    for c in cues:
        for f in range(int((c["start"] + args.start) * FPS), min(n, int((c["end"] + args.start) * FPS) + 1)):
            shapes[f] = "rest" if c["value"] in ("X",) else c["value"]
    # brow lift on wide-open sounds, eased
    lift = np.array([1.0 if s in ("D", "E") else 0.0 for s in shapes])
    lift = np.convolve(lift, np.ones(9) / 9, "same") * 4
    # blinks every 2.5-4.5 s
    rng = random.Random(4)
    blink = np.zeros(n)
    t = rng.uniform(1.0, 2.0)
    while t < total:
        f = int(t * FPS)
        for k, v in enumerate((0.5, 1.0, 1.0, 0.5)):
            if f + k < n:
                blink[f + k] = v
        t += rng.uniform(2.5, 4.5)

    # place her: fill the frame width, bottom of the picture at the bottom of the frame
    h0, w0 = img.shape[:2]
    scale = 2.2
    pw, ph = int(w0 * scale), int(h0 * scale)
    top = H - ph
    bg = np.zeros((H, W, 3), np.uint8)
    g = np.linspace(0, 1, H)[:, None]
    bg[:] = (np.array([255, 236, 244]) * (1 - g) + np.array([250, 196, 220]) * g)[:, None, :].astype(np.uint8)
    # her background is white: make it see-through so she sits on the pink
    near_white = (img.min(2) > 238)
    lab, _ = ndimage.label(near_white)
    border = np.unique(np.concatenate([lab[0], lab[:, 0], lab[:, -1]]))
    alpha = (~np.isin(lab, border[border > 0])).astype(np.float32)
    alpha = cv2.GaussianBlur(alpha, (0, 0), 1.2)
    alpha_big = cv2.resize(alpha, (pw, ph))[..., None]

    tmp = args.out.replace(".mp4", "_silent.mp4")
    wr = imageio.get_writer(tmp, fps=FPS, codec="libx264", quality=8, macro_block_size=1)
    for f in range(n):
        sec = f / FPS
        pic = face.frame(shapes[f], blink[f], lift[f])
        pic = cv2.resize(pic, (pw, ph), interpolation=cv2.INTER_CUBIC)
        # tiny sway and breathing around the chest
        ang = 0.8 * math.sin(sec * 1.3) + 0.4 * math.sin(sec * 2.9)
        sc = 1 + 0.004 * math.sin(sec * 2.2)
        M = cv2.getRotationMatrix2D((pw / 2, ph * 0.95), ang, sc)
        M[1, 2] += 3 * math.sin(sec * 2.2)
        pic = cv2.warpAffine(pic, M, (pw, ph), borderMode=cv2.BORDER_REPLICATE)
        al = cv2.warpAffine(alpha_big, M, (pw, ph))[..., None]
        frame = bg.copy().astype(np.float32)
        x0 = (W - pw) // 2
        sx0, sx1 = max(0, -x0), min(pw, W - x0)
        region = frame[top:top + ph, x0 + sx0:x0 + sx1]
        region[:] = pic[:, sx0:sx1] * al[:, sx0:sx1] + region * (1 - al[:, sx0:sx1])
        frame = frame.astype(np.uint8)
        if args.captions and args.text:
            frame = add_caption(frame, args.text, sec - args.start, len(a) / sr)
        wr.append_data(frame)
    wr.close()
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", tmp, "-itsoffset", str(args.start), "-i", args.voice,
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", args.out], check=True)
    os.remove(tmp)
    print("saved", args.out)


if __name__ == "__main__":
    main()
