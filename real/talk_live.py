"""Full-screen talking close-up of the painted her, the smooth version of talk_face.py:

  * mouths MORPH into each other (optical flow slides the lips/teeth/jaw from one sheet shape to the next,
    then a short blend), instead of cutting or cross-fading
  * each sound's mouth is reached at the middle of the sound and eased in/out (no snapping)
  * blinks: the upper lid slides down over the eye (made from her own lid skin, no extra art)
  * head motion: slow drift + tilt + a slight turn, plus small nods on the loud (stressed) beats of the voice
  * 60 fps

    python real/talk_live.py out.mp4
"""
import math
import os
import subprocess
import sys
import tempfile

import cv2
import numpy as np
import soundfile as sf

from talk_face import BG_BOT, BG_TOP, LINE, VOICE, edge_fade, load_tiles, on_backdrop, phoneme_track, voices

W, H, FPS, SR = 1080, 1920, 60, voices.SR

# tile coordinates (tiles from talk_face.load_tiles: 1028 x 1516)
MOUTH_BOX = (150, 580, 880, 1060)                     # x0, y0, x1, y1: the only area that changes when she talks
# per eye: centre x, half width, lid top, upper lash line (centre, corner drop), lower lash line (centre, corner rise)
EYES = [dict(xc=467, hw=82, top=508, up=545, up_drop=32, lo=612, lo_rise=30),
        dict(xc=722, hw=78, top=496, up=528, up_drop=38, lo=598, lo_rise=26)]


def smooth(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


# ------------------------------------------------------------------ mouths
def mouth_versions(tiles):
    """Rest face everywhere except nose-to-chin: eyes and brows never change, so blinks and the face stay steady."""
    h, w = tiles[0].shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt(((xx - w * .5) / (w * .3)) ** 2 + ((yy - h * .54) / (h * .11)) ** 2)
    mask = np.clip((1.25 - d) / .35, 0, 1)[..., None]
    base = tiles[0]
    ring = (mask[..., 0] > .05) & (mask[..., 0] < .5)
    return [base * (1 - mask) + (t + (base[ring].mean(0) - t[ring].mean(0))) * mask for t in tiles]


class Morpher:
    """In-between mouths: warp A toward B and B toward A along the optical flow, then blend."""

    def __init__(self, faces):
        x0, y0, x1, y1 = MOUTH_BOX
        self.crops = [f[y0:y1, x0:x1] for f in faces]
        self.gray = [cv2.cvtColor(np.clip(c, 0, 255).astype(np.uint8), cv2.COLOR_RGB2GRAY) for c in self.crops]
        self.dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
        h, w = self.gray[0].shape
        self.gx, self.gy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
        self.flows = {}

    def flow(self, a, b):                              # f with  crop_b(p) ~ crop_a(p + f(p))
        if (a, b) not in self.flows:
            f = self.dis.calc(self.gray[b], self.gray[a], None)
            self.flows[(a, b)] = cv2.GaussianBlur(f, (0, 0), 14)      # smooth field: the face bends, never tears
        return self.flows[(a, b)]

    def mid(self, a, b, k):
        if a == b or k <= 0:
            return self.crops[a]
        if k >= 1:
            return self.crops[b]
        fa, fb = self.flow(a, b), self.flow(b, a)
        wa = cv2.remap(self.crops[a], self.gx + k * fa[..., 0], self.gy + k * fa[..., 1], cv2.INTER_LINEAR,
                       borderMode=cv2.BORDER_REPLICATE)
        wb = cv2.remap(self.crops[b], self.gx + (1 - k) * fb[..., 0], self.gy + (1 - k) * fb[..., 1],
                       cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        return wa * (1 - k) + wb * k


def mouth_keys(track, total):
    """[(t, viseme)] keys: every sound's mouth at the middle of that sound, rest mouth in pauses."""
    keys, last_end = [(0.0, 0)], 0.0
    for s, e, v in track:
        if s - last_end > .14:                         # a real pause: close to rest in between
            keys.append((last_end + .06, 0))
            keys.append((s - .06, 0))
        keys.append(((s + e) / 2, v - 1))
        last_end = e
    keys += [(last_end + .08, 0), (total + 1, 0)]
    return keys


def mouth_at(keys, bounds, t):
    """(a, b, k): between key i and i+1 the change happens in a <=110 ms eased window around the sound boundary."""
    i = max(0, min(len(keys) - 2, np.searchsorted([k[0] for k in keys], t) - 1))
    (ta, a), (tb, b) = keys[i], keys[i + 1]
    edge = bounds.get(i, (ta + tb) / 2)
    T = min(tb - ta, .11)
    lo = min(max(edge - T / 2, ta), tb - T)
    return int(a), int(b), float(smooth(float((t - lo) / max(T, 1e-3))))


# ------------------------------------------------------------------ blinks
def blink_amount(t, times):
    for b in times:
        dt = t - b
        if 0 <= dt < .08:
            return smooth(dt / .08)
        if .08 <= dt < .11:
            return 1.0
        if .11 <= dt < .27:
            return 1 - smooth((dt - .11) / .16)
    return 0.0


def blink(img, amount):
    """Close each eye by `amount` (0..1): a lid in her own skin tone comes down from the upper lash line over the
    eye, with a dark lash line on its edge (and a few lashes at the outer end once it's nearly shut)."""
    if amount <= .01:
        return img
    out = img.copy()
    for side, e in enumerate(EYES):
        x0, x1 = e["xc"] - e["hw"] - 10, e["xc"] + e["hw"] + 10
        y0, y1 = e["up"] - 12, e["lo"] + 30
        box = out[y0:y1, x0:x1]
        xs = np.arange(x0, x1, dtype=np.float32)
        u = (xs - e["xc"]) / e["hw"]
        up = e["up"] + e["up_drop"] * u ** 2 - 1
        lo = e["lo"] - e["lo_rise"] * u ** 2 + 3
        open_ = np.maximum(lo - up, 0)
        L = up + amount * open_                                        # lid edge now
        ys = np.arange(y0, y1, dtype=np.float32)[:, None]
        # lid: soft mask between the old lash line and the lid edge
        m = np.clip(np.minimum(ys - up[None, :] + 1.5, L[None, :] - ys + 1.5) / 3, 0, 1) * (open_ > 0)[None, :]
        skin = np.median(img[555:600, 585:620].reshape(-1, 3), 0)          # nose bridge: clean lit skin
        v = np.clip((ys - up[None, :]) / np.maximum(L - up, 8)[None, :], 0, 1)[..., None]   # 0 top of lid .. 1 edge
        shadow = np.array([150, 100, 85], np.float32)                  # her warm brown eyeshadow
        lid = shadow * (1 - v) ** 1.6 * .75 + skin * (1 - .75 * (1 - v) ** 1.6)
        lid = lid * (.9 + .1 * np.sin(np.pi * v))                     # rounded: a hint of light across the middle
        m = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 1.2)
        box = box * (1 - m[..., None]) + lid * m[..., None]
        # lash line on the lid edge
        ink = np.zeros(box.shape[:2], np.uint8)
        pts = np.stack([xs - x0, L - y0], 1)[open_ > 0]
        if len(pts) > 2:
            cv2.polylines(ink, [np.round(pts * 4).astype(np.int32)], False, 255, 5, cv2.LINE_AA, shift=2)
            if amount > .75:                                           # a few lashes at the outer corner
                outer = 1 if side == 1 else -1
                for j, uu in enumerate((.55, .72, .88)):
                    px = e["xc"] + outer * uu * e["hw"] - x0
                    py = e["up"] + e["up_drop"] * uu ** 2 + amount * (e["lo"] - e["lo_rise"] * uu ** 2 - e["up"] - e["up_drop"] * uu ** 2) - y0
                    cv2.line(ink, (int(px * 4), int(py * 4)), (int((px + outer * (10 + 4 * j)) * 4), int((py + 9 + 2 * j) * 4)),
                             255, 2, cv2.LINE_AA, shift=2)
        a = (ink.astype(np.float32) / 255 * smooth(amount / .35))[..., None]
        box = box * (1 - a) + np.array([48, 28, 26], np.float32) * a
        out[y0:y1, x0:x1] = box
    return out


# ------------------------------------------------------------------ head motion
def loud_beats(audio, lead, min_gap=.55, n_max=8):
    """Times of the strongest syllable onsets in the voice: where a speaker naturally nods."""
    hop = SR // 100
    rms = np.sqrt(np.convolve(audio ** 2, np.ones(hop * 4) / (hop * 4), "same")[::hop])
    rise = np.maximum(0, np.diff(rms, prepend=rms[0]))
    rise = np.convolve(rise, np.ones(5) / 5, "same")
    order = np.argsort(rise)[::-1]
    picked = []
    for i in order:
        if rise[i] < rise[order[0]] * .25 or len(picked) >= n_max:
            break
        if all(abs(i - p) > min_gap * 100 for p in picked):
            picked.append(i)
    return sorted(lead + p / 100 for p in picked)


def head_pose(t, nods):
    """(dx, dy, roll deg, yaw, scale): slow organic drift (sum of unrelated sines) + nods that dip and settle."""
    dx = 9 * math.sin(t * .63 + 1) + 4 * math.sin(t * 1.37)
    dy = 3 * math.sin(t * .9 + 2)
    roll = 1.1 * math.sin(t * .55) + .5 * math.sin(t * 1.23 + .4)
    yaw = .012 * math.sin(t * .47 + .8) + .005 * math.sin(t * 1.1)
    for n in nods:
        d = t - n
        if -.05 < d < .65:                                      # quick dip, slower settle
            x = (d + .05) / .7
            k = math.sin(math.pi * x ** .6)
            dy += 7 * k
            roll += .5 * k
    scale = 1 + .008 * math.sin(t * 1.5)                       # breathing
    return dx, dy, roll, yaw, scale


def frame_matrix(t, nods, h, w):
    dx, dy, roll, yaw, scale = head_pose(t, nods)
    s = H / (h * .70) * scale
    piv = (w / 2, h * .76)                                      # neck: the head swings, shoulders barely move
    R = np.vstack([cv2.getRotationMatrix2D(piv, roll, 1.0), [0, 0, 1]])
    # slight turn: one side of the face a hair taller than the other (perspective)
    Y = np.array([[1, 0, 0], [0, 1, 0], [yaw / w * 2, 0, 1]])
    C = np.array([[1, 0, -w / 2], [0, 1, -h * .45], [0, 0, 1]])
    S = np.array([[s, 0, W / 2 + dx], [0, s, H * .46 + dy], [0, 0, 1]])
    return S @ Y @ C @ R


def render(out):
    a = voices.say(VOICE, LINE)
    text = LINE.split("] ", 1)[1]
    lead = .5
    audio = np.concatenate([np.zeros(int(lead * SR), np.float32), a, np.zeros(int(.8 * SR), np.float32)])
    total = len(audio) / SR
    with tempfile.TemporaryDirectory() as d:
        wav = os.path.join(d, "a.wav")
        sf.write(wav, voices.clarity(audio), SR)
        sf.write(os.path.join(d, "line.wav"), a, SR)
        track = [(s + lead, e + lead, v) for s, e, v in phoneme_track(os.path.join(d, "line.wav"), text)]
        keys = mouth_keys(track, total)
        bounds = {}                                             # key i -> the time the sound actually changes
        nods = loud_beats(audio, 0)
        blinks = [.9, 3.35, 5.9] + ([8.3] if total > 8.6 else [])
        print(f"sounds {len(track)} | keys {len(keys)} | nods {[round(n, 2) for n in nods]} | blinks {blinks}")

        faces = [on_backdrop(f) for f in mouth_versions(load_tiles())]
        base = faces[0].copy()
        morph = Morpher(faces)
        h, w = base.shape[:2]
        x0, y0, x1, y1 = MOUTH_BOX
        fade = edge_fade(h, w)
        g = np.linspace(0, 1, H)[:, None, None]
        bg = (np.array(BG_TOP) * (1 - g) + np.array(BG_BOT) * g) * np.ones((1, W, 1))

        enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                                "-framerate", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-pix_fmt", "yuv420p",
                                "-crf", "17", "-c:a", "aac", "-b:a", "192k", "-shortest", out], stdin=subprocess.PIPE)
        for fi in range(int(total * FPS)):
            t = fi / FPS
            ma, mb, k = mouth_at(keys, bounds, t)
            face = base.copy()
            face[y0:y1, x0:x1] = morph.mid(ma, mb, k)
            face = blink(face, blink_amount(t, blinks))
            M = frame_matrix(t, nods, h, w)
            img = cv2.warpPerspective(face, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT)
            al = cv2.warpPerspective(fade, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)[..., None]
            frame = img * al + bg * (1 - al)
            enc.stdin.write(np.clip(frame, 0, 255).astype(np.uint8).tobytes())
        enc.stdin.close()
        enc.wait()
    print("wrote", out)


if __name__ == "__main__":
    render(sys.argv[1] if len(sys.argv) > 1 else "talk_live.mp4")
