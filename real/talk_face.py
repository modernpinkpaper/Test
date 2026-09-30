"""Talking close-up of the painted her from her 12-mouth viseme sheet, driven by the script's PHONEMES (not just
loudness): the line is turned into sounds (misaki G2P, the same one Kokoro uses), each word's sounds are spread over
the time Whisper heard that word, and every sound picks its mouth from the sheet (TH, F/V, SH, OO... all 12).
30 fps, with a 2-frame blend between mouths so it flows.

    python real/talk_face.py out.mp4 [mode]      mode: compare (default, top = lower face, bottom = whole face) |
                                                        lower | whole

Needs the aligned + upscaled tiles from real/visemes.py (VIS dir).
"""
import glob
import math
import os
import subprocess
import sys
import tempfile

import cv2
import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", "skits")]
import voices                                                  # noqa: E402

W, H, FPS, SR = 1080, 1920, 30, voices.SR
VIS = "/tmp/claude-0/-home-user-Test/6a6db2ec-de51-5be8-8073-4c5206a96107/scratchpad/real/vis"
VOICE = "af_bella"
LINE = "[sassy] Okay, real talk. Your budget isn't broken. Your Target runs are. Thank you for coming to my TED talk."
BG_TOP, BG_BOT = (255, 226, 234), (246, 196, 212)

# sheet order: 1 rest, 2 M/B/P, 3 A/AE/AH, 4 AA/AW, 5 E/EE, 6 I/IH, 7 O, 8 OO/U/W, 9 F/V, 10 L/N/D/T, 11 TH, 12 SH/CH/J/R
PHONE_TO_VIS = {}
for chars, v in (("mbp", 2), ("fv", 9), ("θð", 11), ("ʃʒʧʤɹr", 12), ("lntdɾ", 10), ("szkɡghŋjx", 6), ("w", 8),
                 ("æaʌA", 3), ("ɑɔW", 4), ("eɛ", 5), ("iɪᵊəI", 6), ("oOYɒ", 7), ("uʊ", 8), ("ɜɝ", 12)):
    for ch in chars:
        PHONE_TO_VIS[ch] = v
VOWELS = set("æaʌAɑɔWeɛiɪᵊəIoOYɒuʊɜɝ")


def phoneme_track(wav_path, text):
    """[(start, end, viseme)] for the whole line: Whisper word times x misaki phonemes."""
    from faster_whisper import WhisperModel
    from misaki import en
    g2p = en.G2P(trf=False, british=False)
    _, tokens = g2p(text)
    words = [t for t in tokens if any(ch.isalnum() for ch in t.text)]
    segs, _ = WhisperModel("small", device="cpu", compute_type="int8").transcribe(wav_path, word_timestamps=True)
    heard = [w for s in segs for w in s.words]
    track = []
    # pair script words with heard words in order (same count in practice; if not, stretch over the heard span)
    if len(heard) != len(words):
        t0, t1 = heard[0].start, heard[-1].end
        n = len(words)
        spans = [(t0 + (t1 - t0) * i / n, t0 + (t1 - t0) * (i + 1) / n) for i in range(n)]
    else:
        spans = [(w.start, w.end) for w in heard]
    for tok, (a, b) in zip(words, spans):
        ph = [ch for ch in (tok.phonemes or "") if ch in PHONE_TO_VIS]
        if not ph:
            continue
        wts = np.array([1.7 if ch in VOWELS else 1.0 for ch in ph])
        edges = a + (b - a) * np.r_[0, np.cumsum(wts)] / wts.sum()
        for ch, s, e in zip(ph, edges[:-1], edges[1:]):
            track.append((s, e, PHONE_TO_VIS[ch]))
    return track


def viseme_at(track, t):
    for s, e, v in track:
        if s <= t < e:
            return v
    return 1


def load_tiles():
    files = sorted(glob.glob(os.path.join(VIS, "v??_*.png")))
    tiles = [cv2.cvtColor(cv2.imread(f), cv2.COLOR_BGR2RGB).astype(np.float32) for f in files]
    h, w = tiles[0].shape[:2]
    return [t[:h - 100, 12:w - 12] for t in tiles]


def lower_face_versions(tiles):
    """Base face (rest) + only the lower face (nose to chin, cheeks, jaw) from each viseme, soft-blended."""
    h, w = tiles[0].shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy, rx, ry = w * .5, h * .475, w * .3, h * .16
    d = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
    mask = np.clip((1.25 - d) / .35, 0, 1)[..., None]
    base = tiles[0]
    out = []
    for t in tiles:
        ring = (mask[..., 0] > .05) & (mask[..., 0] < .5)
        t = t + (base[ring].mean(0) - t[ring].mean(0))
        out.append(base * (1 - mask) + t * mask)
    return out


def on_backdrop(img):
    """White paper -> her pink backdrop (her edges are dark hair: brightness makes a clean matte)."""
    lum = img.min(2)
    a = cv2.GaussianBlur(np.clip((250 - lum) / 22, 0, 1), (0, 0), 1.2)[..., None]
    h = img.shape[0]
    g = np.linspace(0, 1, h)[:, None, None]
    bg = (np.array(BG_TOP) * (1 - g) + np.array(BG_BOT) * g) * np.ones((1, img.shape[1], 1))
    return img * a + bg * (1 - a)


def panel(face, t, ph, pw, label=None):
    """The face in a ph x pw panel: framed from the top of her hair to her collarbones, gentle sway + breathing."""
    h, w = face.shape[:2]
    scale = ph / (h * .78) * (1 + .012 * math.sin(t * 1.6))
    ang = .7 * math.sin(t * 1.1)
    M = cv2.getRotationMatrix2D((w / 2, h * .62), ang, scale)
    M[0, 2] += pw / 2 - w / 2
    M[1, 2] += ph * .52 - h * .45
    out = cv2.warpAffine(face, M, (pw, ph), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    if label:
        cv2.rectangle(out, (20, 20), (20 + 16 * len(label) + 30, 78), (255, 255, 255), -1)
        cv2.putText(out, label, (35, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (224, 69, 123), 2, cv2.LINE_AA)
    return out


def render(out, mode="compare"):
    a = voices.say(VOICE, LINE)
    text = LINE.split("] ", 1)[1]
    with tempfile.TemporaryDirectory() as d:
        wav = os.path.join(d, "a.wav")
        lead = .5
        audio = np.concatenate([np.zeros(int(lead * SR), np.float32), a, np.zeros(int(.8 * SR), np.float32)])
        sf.write(wav, voices.clarity(audio), SR)
        sf.write(os.path.join(d, "line.wav"), a, SR)
        track = [(s + lead, e + lead, v) for s, e, v in phoneme_track(os.path.join(d, "line.wav"), text)]
        print("phonemes:", len(track), "| visemes used:", sorted({v for _, _, v in track}))
        tiles = load_tiles()
        whole = [on_backdrop(t) for t in tiles]
        lower = [on_backdrop(t) for t in lower_face_versions(tiles)]
        total = len(audio) / SR
        enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                                "-framerate", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-pix_fmt", "yuv420p",
                                "-crf", "17", "-c:a", "aac", "-b:a", "192k", "-shortest", out], stdin=subprocess.PIPE)
        prev, cur, since = 1, 1, 0.0
        for fi in range(int(total * FPS)):
            t = fi / FPS
            v = viseme_at(track, t)
            if v != cur:
                prev, cur, since = cur, v, t
            k = min(1.0, (t - since) / (2 / FPS))                       # 2-frame blend into the new mouth
            def face(set_):
                return set_[prev - 1] * (1 - k) + set_[cur - 1] * k
            if mode == "compare":
                top = panel(face(lower), t, H // 2, W, "A: lower face swap")
                bot = panel(face(whole), t, H // 2, W, "B: whole face swap")
                frame = np.vstack([top, bot])
                frame[H // 2 - 3:H // 2 + 3] = 255
            else:
                frame = panel(face(lower if mode == "lower" else whole), t, H, W)
            enc.stdin.write(np.clip(frame, 0, 255).astype(np.uint8).tobytes())
        enc.stdin.close()
        enc.wait()
    print("wrote", out)


if __name__ == "__main__":
    render(sys.argv[1] if len(sys.argv) > 1 else "talk_face.mp4", sys.argv[2] if len(sys.argv) > 2 else "compare")
