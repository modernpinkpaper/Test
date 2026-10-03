"""Stick-figure office skit (1080x1920, ~1 min): the boss asks for the impossible, the employee calls it out
professionally ("can you put that in an email and copy HR?") and the boss is left stuck.

    python skits/stick_office.py out.mp4

Voices: employee = Chatterbox clone of her own voice sample (demo_videos/voices/my-voice-ref.wav, private);
boss = Piper "ryan" (MIT-licensed voice; downloaded into chibi/.cache/piper).
Everything is drawn with wobbly hand-drawn lines (they "boil": redrawn slightly differently every 3 frames).
"""
import math
import os
import subprocess
import sys
import tempfile

import cairocffi as cairo
import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "chibi"))
import video_321 as V          # noqa: E402  (voice cloning + cache)

W, H, FPS, SR = 1080, 1920, 24, 24000
CACHE = V.CACHE
FONT = os.path.join(CACHE, "patrick-hand.ttf")
PIPER = os.path.join(CACHE, "piper", "en_US-ryan-high.onnx")
FLOOR = 1400
INK = (0.12, 0.12, 0.14)
BOSS_C, EMP_C = (0.86, 0.26, 0.24), (0.20, 0.42, 0.78)

# who, line, boss pose, employee pose, boss face, employee face, extra
SCRIPT = [
    ("boss", "Hey! Got a minute? Great. I need the quarterly report done by five.", "explain", "idle", "smile", "neutral", ""),
    ("emp", "The quarterly report? That's not due for three weeks.", "idle", "clipboard", "smile", "puzzled", ""),
    ("boss", "Right. And now it's due at five. Also, cover Mark's clients today. He has a thing.", "explain", "clipboard", "smile", "flat", ""),
    ("emp", "Sure. Which of my projects should I pause? The Henderson launch, or the audit you gave me this morning?",
     "idle", "palm", "smile", "neutral", ""),
    ("boss", "Both are urgent. Everything is urgent. That's the job.", "shrug", "idle", "smug", "flat", ""),
    ("boss", "Oh, and let's skip lunch today. We're a family here.", "wide", "cross", "smile", "flat", ""),
    ("emp", "Got it. So the report, Mark's clients, Henderson, and the audit. All today. No lunch.",
     "idle", "count", "smile", "neutral", "count"),
    ("boss", "Exactly! See? You get it.", "point", "cross", "smile", "flat", ""),
    ("emp", "Perfect. Can you send that to me in an email? And copy HR, since it's about six hours of overtime.",
     "idle", "palm", "smile", "smile", ""),
    ("boss", "Overtime?", "freeze", "idle", "shock", "smile", "zoom"),
    ("emp", "I'm hourly. You approved my timesheet last week.", "freeze", "hips", "shock", "smile", ""),
    ("boss", "Right. Well. Let's circle back on the email.", "backoff", "hips", "worried", "smile", ""),
    ("emp", "No problem. I'll start as soon as it's in writing. Enjoy your lunch!", "backoff", "wave", "worried", "smile", "leave"),
    ("boss", "Why do I feel like I just got written up?", "chin", "gone", "worried", "neutral", "alone"),
]
START, GAP = 1.6, 0.4
BASE_ZOOM = 1.3             # the camera sits closer than the drawn set, so the figures fill the phone screen


# ------------------------------------------------------------------ voices
def boss_voice(text):
    import hashlib
    key = hashlib.md5(("piper|" + text).encode()).hexdigest()
    path = os.path.join(CACHE, f"boss_{key}.wav")
    if not os.path.exists(path):
        raw = path + ".raw.wav"
        subprocess.run([sys.executable, "-m", "piper", "-m", PIPER, "-f", raw], input=text.encode(), check=True,
                       capture_output=True)
        a, sr = sf.read(raw, dtype="float32")
        a = np.interp(np.arange(0, len(a), sr / SR), np.arange(len(a)), a).astype(np.float32)
        nz = np.where(np.abs(a) > 0.01)[0]
        sf.write(path, a[max(nz[0] - 200, 0):nz[-1] + 1200] * 0.9, SR)
        os.remove(raw)
    return sf.read(path, dtype="float32")[0]


def emp_voice(text):
    return V.voice(text)


def envelope(a):
    """Loudness per video frame (0..1), for the talking mouth."""
    n = int(SR / FPS)
    e = np.array([np.sqrt(np.mean(a[i:i + n] ** 2)) for i in range(0, len(a), n)])
    return np.clip(e / (np.percentile(e, 95) + 1e-6), 0, 1)


# ------------------------------------------------------------------ hand-drawn lines
BOIL = 0


def wob(x, y, seed=0.0, amp=2.2):
    b = BOIL + seed
    return (x + amp * math.sin(y * 0.045 + b * 1.9 + seed) + 0.8 * math.sin(x * 0.11 + b * 2.7),
            y + amp * math.sin(x * 0.05 + b * 2.3 + seed * 1.3) + 0.8 * math.sin(y * 0.13 + b * 1.1))


def path(ctx, pts, seed=0.0, closed=False, step=14.0, amp=2.2):
    pts = list(pts) + ([pts[0]] if closed else [])
    out = []
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        n = max(1, int(math.hypot(x1 - x0, y1 - y0) / step))
        out += [(x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n) for i in range(n)]
    out.append(pts[-1])
    out = [wob(x, y, seed, amp) for x, y in out]
    ctx.move_to(*out[0])
    for p in out[1:]:
        ctx.line_to(*p)
    if closed:
        ctx.close_path()


def stroke(ctx, pts, w=6.0, col=INK, seed=0.0, closed=False, fill=None, amp=2.2):
    path(ctx, pts, seed, closed, amp=amp)
    if fill:
        ctx.set_source_rgb(*fill)
        ctx.fill_preserve()
    ctx.set_source_rgb(*col)
    ctx.set_line_width(w)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()


def circle_pts(cx, cy, r, n=36, a0=0.0, a1=2 * math.pi):
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / n), cy + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def text(ctx, s, x, y, size, col=INK, anchor="mm", rot=0.0):
    ctx.save()
    face = _font_face()
    ctx.set_font_face(face)
    ctx.set_font_size(size)
    xb, yb, tw, th, _, _ = ctx.text_extents(s)
    ctx.translate(x, y)
    ctx.rotate(rot)
    dx = {"l": 0, "m": -tw / 2, "r": -tw}[anchor[0]] - xb
    dy = {"t": -yb, "m": -yb - th / 2, "b": -yb - th}[anchor[1]]
    ctx.move_to(dx, dy)
    ctx.set_source_rgb(*col)
    ctx.show_text(s)
    ctx.restore()
    return tw


_FACE = None


def _font_face():
    global _FACE
    if _FACE is None:
        import ctypes.util  # noqa: F401
        from cairocffi import FontFace  # noqa: F401
        _FACE = _ft_face(FONT)
    return _FACE


def _ft_face(path_):
    """Load a TTF into cairo through FreeType (cairocffi has no direct loader)."""
    import cffi
    ffi = cffi.FFI()
    ffi.cdef("""typedef void* FT_Library; typedef void* FT_Face; int FT_Init_FreeType(FT_Library*);
                int FT_New_Face(FT_Library, const char*, long, FT_Face*);
                void* cairo_ft_font_face_create_for_ft_face(FT_Face, int);""")
    ft = ffi.dlopen("freetype")
    cft = ffi.dlopen("cairo")
    lib = ffi.new("FT_Library*")
    ft.FT_Init_FreeType(lib)
    face = ffi.new("FT_Face*")
    ft.FT_New_Face(lib[0], path_.encode(), 0, face)
    ptr = cft.cairo_ft_font_face_create_for_ft_face(face[0], 0)
    _ft_face.keep = (ffi, ft, cft, lib, face)
    return cairo.FontFace._from_pointer(cairo.ffi.cast("cairo_font_face_t *", ptr), incref=False)


# ------------------------------------------------------------------ office
def office(ctx, t):
    stroke(ctx, [(-100, FLOOR), (W + 100, FLOOR)], 7, seed=1)
    for i, x in enumerate(range(-60, W + 100, 150)):          # floor boards in perspective
        stroke(ctx, [(x, FLOOR + 10), (x - 60, FLOOR + 170)], 3, col=(.6, .6, .62), seed=i)
    # window with blinds and a little skyline
    stroke(ctx, rect(70, 470, 420, 820), 6, seed=2, closed=True, fill=(0.93, 0.96, 1.0))
    for i, (bx, bh) in enumerate(((95, 170), (160, 250), (235, 140), (300, 210), (360, 120))):
        stroke(ctx, rect(bx, 820 - bh, bx + 55, 820), 3, col=(.55, .6, .7), seed=3 + i, closed=True)
    for i, y in enumerate(range(490, 640, 22)):
        stroke(ctx, [(75, y), (415, y)], 3, col=(.5, .5, .52), seed=10 + i)
    stroke(ctx, [(245, 470), (245, 640)], 2, seed=20)
    # wall clock (the minute hand really moves)
    stroke(ctx, circle_pts(560, 520, 52), 6, seed=4, closed=True, fill=(1, 1, 1))
    m = t / 60 * 2 * math.pi * 6 - math.pi / 2
    stroke(ctx, [(560, 520), (560 + 38 * math.cos(m), 520 + 38 * math.sin(m))], 4, seed=5)
    stroke(ctx, [(560, 520), (560 + 24 * math.cos(-math.pi / 2 + 2.6), 520 + 24 * math.sin(-math.pi / 2 + 2.6))], 5, seed=6)
    # whiteboard
    stroke(ctx, rect(650, 610, 1010, 860), 6, seed=7, closed=True, fill=(1, 1, 1))
    stroke(ctx, [(680, 830), (740, 800), (790, 815), (850, 740), (900, 760), (970, 650)], 5, col=BOSS_C, seed=8)
    stroke(ctx, [(955, 650), (972, 648), (968, 668)], 5, col=BOSS_C, seed=9)
    text(ctx, "Q3 GOALS!!", 760, 660, 46, col=INK)
    # desk, monitor, mug, papers
    stroke(ctx, [(770, 1150), (1070, 1150)], 7, seed=11)
    stroke(ctx, [(790, 1150), (790, FLOOR)], 6, seed=12)
    stroke(ctx, [(1050, 1150), (1050, FLOOR)], 6, seed=13)
    stroke(ctx, rect(820, 960, 1000, 1085), 6, seed=14, closed=True, fill=(0.95, 0.95, 0.97))
    stroke(ctx, [(910, 1085), (910, 1150)], 6, seed=15)
    stroke(ctx, [(875, 1150), (945, 1150)], 7, seed=16)
    stroke(ctx, rect(1010, 1095, 1048, 1150), 5, seed=17, closed=True, fill=(1, 1, 1))
    stroke(ctx, circle_pts(1052, 1118, 12, 12, -1.3, 1.3), 4, seed=18)
    for i in range(3):
        stroke(ctx, [(1022 + 10 * i, 1085), (1018 + 10 * i + 4 * math.sin(t * 3 + i), 1060)], 3, col=(.6, .6, .6), seed=30 + i)
    for i in range(3):
        stroke(ctx, [(800 + 4 * i, 1140 - 8 * i), (860 + 4 * i, 1138 - 8 * i)], 4, seed=40 + i)
    # plant
    stroke(ctx, [(40, FLOOR), (30, 1300), (120, 1300), (110, FLOOR)], 6, seed=19, closed=True, fill=(1, 1, 1))
    for i, (dx, h) in enumerate(((-40, 140), (-10, 190), (20, 170), (50, 130))):
        stroke(ctx, [(75, 1300), (75 + dx * .4, 1300 - h * .6), (75 + dx, 1300 - h)], 5, col=(.25, .55, .3), seed=50 + i)


# ------------------------------------------------------------------ stick figures
POSES = {   # (left arm shoulder, elbow), (right arm shoulder, elbow): degrees from straight down, + = outward
    "idle": ((12, 8), (12, 8)),
    "explain": ((12, 8), (40, 70)),
    "clipboard": ((15, -95), (15, -95)),
    "palm": ((12, 8), (35, 85)),
    "shrug": ((35, 95), (35, 95)),
    "wide": ((70, 20), (70, 20)),
    "cross": ((22, -125), (22, -125)),
    "count": ((20, -100), (38, 95)),
    "point": ((12, 8), (80, 0)),
    "freeze": ((25, 40), (25, 40)),
    "hips": ((40, -105), (40, -105)),
    "backoff": ((30, 75), (30, 75)),
    "wave": ((12, 8), (60, 110)),
    "chin": ((12, 8), (25, -150)),
    "gone": ((12, 8), (12, 8)),
}


class Figure:
    def __init__(self, x, facing, color, hair, tall=1.0):
        self.x, self.facing, self.color, self.hair, self.s = x, facing, color, hair, 1.3 * tall
        self.pose = POSES["idle"]

    def draw(self, ctx, t, pose, face, mouth=0.0, walk=0.0, blink=False, tilt=0.0, seed=0):
        s, x = self.s, self.x
        bob = abs(math.sin(walk * math.pi)) * 8 if walk else 1.5 * math.sin(t * 2.2 + seed)
        leg, thigh = 92 * s, 88 * s
        hip = (x, FLOOR - (leg + thigh) + bob - 6)
        neck = (x + tilt * 0.3, hip[1] - 150 * s)
        r = 42 * s
        head = (neck[0] + tilt, neck[1] - r - 6)
        # legs (walk swings them)
        sw = math.sin(walk * 2 * math.pi) * 28 if walk else 0
        for side, a in ((-1, 8 - sw), (1, 8 + sw)):
            ang = math.radians(a) * side
            knee = (hip[0] + math.sin(ang) * thigh, hip[1] + math.cos(ang) * thigh)
            bend = math.radians(a * .4 + (12 if walk else 0)) * side
            foot = (knee[0] + math.sin(bend) * leg, min(knee[1] + math.cos(bend) * leg, FLOOR - 2))
            stroke(ctx, [hip, knee, foot], 7, seed=seed + side)
            stroke(ctx, [foot, (foot[0] + 18 * self.facing, foot[1])], 7, seed=seed + side + 2)
        stroke(ctx, [hip, neck], 7, seed=seed + 3)
        if self.hair == "tie":                     # boss: tie
            stroke(ctx, [(neck[0], neck[1] + 8), (neck[0] - 10, neck[1] + 55), (neck[0], neck[1] + 70),
                         (neck[0] + 10, neck[1] + 55)], 4, col=self.color, closed=True, fill=self.color, seed=seed + 4)
        # arms
        sh = (neck[0], neck[1] + 22 * s)
        for side, (a1, a2) in ((-1, pose[0]), (1, pose[1])):
            u = math.radians(a1) * side
            elbow = (sh[0] + math.sin(u) * 72 * s, sh[1] + math.cos(u) * 72 * s)
            lo = u + math.radians(a2) * side
            hand = (elbow[0] + math.sin(lo) * 66 * s, elbow[1] + math.cos(lo) * 66 * s)
            stroke(ctx, [sh, elbow, hand], 7, seed=seed + 5 + side)
            stroke(ctx, circle_pts(hand[0], hand[1], 7, 10), 5, seed=seed + 7 + side, closed=True, fill=INK)
        # head (white fill hides lines behind it)
        stroke(ctx, circle_pts(head[0], head[1], r), 7, seed=seed + 9, closed=True, fill=(1, 1, 1))
        hx, hy = head
        if self.hair == "ponytail":
            stroke(ctx, circle_pts(hx, hy, r + 2, 20, math.pi * 1.05, math.pi * 1.95), 9, col=(.35, .22, .15), seed=seed + 10)
            b = hx - self.facing * (r - 4)
            swing = 6 * math.sin(t * 3 + seed)
            stroke(ctx, [(b, hy - r * .6), (b - self.facing * 30, hy - r * .1 + swing), (b - self.facing * 22, hy + r * .9)],
                   11, col=(.35, .22, .15), seed=seed + 11)
        else:
            for k in range(5):
                a = math.pi * (1.15 + .17 * k)
                stroke(ctx, [(hx + r * math.cos(a), hy + r * math.sin(a)), (hx + (r + 12) * math.cos(a), hy + (r + 12) * math.sin(a))],
                       5, seed=seed + 12 + k)
        # face: eyes look the way they face
        ex = self.facing * 10 * s
        for side in (-1, 1):
            px, py = hx + ex + side * 15 * s, hy - 6 * s
            if blink or face == "shock_blink":
                stroke(ctx, [(px - 6, py), (px + 6, py)], 4, seed=seed + 20)
            else:
                rr = 8 if face == "shock" else 5
                stroke(ctx, circle_pts(px, py, rr, 10), 4, seed=seed + 21 + side, closed=True, fill=INK if face != "shock" else (1, 1, 1))
            # brows
            if face in ("puzzled", "worried", "shock", "flat"):
                lift = {"puzzled": (-4 if side == 1 else 4), "worried": 6, "shock": 10, "flat": 0}[face]
                if face == "flat":
                    stroke(ctx, [(px - 9, py - 16), (px + 9, py - 16)], 4, seed=seed + 24 + side)
                elif face == "worried":
                    stroke(ctx, [(px - 9 * side, py - 18), (px + 9 * side, py - 12 - lift)], 4, seed=seed + 24 + side)
                else:
                    stroke(ctx, [(px - 9, py - 16 - lift), (px + 9, py - 18 - lift)], 4, seed=seed + 24 + side)
        mx, my = hx + ex, hy + 20 * s
        if mouth > 0.12:
            stroke(ctx, circle_pts(mx, my + 3, 9 + 5 * mouth, 16), 4, seed=seed + 30, closed=True, fill=(.35, .1, .1))
            ctx.save()
            ctx.scale(1, 1)
            ctx.restore()
        elif face in ("smile", "smug"):
            stroke(ctx, circle_pts(mx + (6 if face == "smug" else 0), my - 6, 14, 10, .3, math.pi - .3), 4, seed=seed + 31)
        elif face == "shock":
            stroke(ctx, circle_pts(mx, my + 2, 8, 12), 4, seed=seed + 32, closed=True)
        elif face == "worried":
            stroke(ctx, [(mx - 12, my + 4), (mx - 4, my), (mx + 4, my + 4), (mx + 12, my)], 4, seed=seed + 33)
        else:
            stroke(ctx, [(mx - 10, my), (mx + 10, my)], 4, seed=seed + 34)
        return head


# ------------------------------------------------------------------ captions / titles
def caption(ctx, who, words, t):
    shown = [w for w, st in words if st <= t]
    if not shown:
        return
    lines, cur = [], ""
    ctx.set_font_face(_font_face())
    ctx.set_font_size(66)
    for w in shown:
        trial = (cur + " " + w).strip()
        if ctx.text_extents(trial)[2] > 900 and cur:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    lines.append(cur)
    lines = lines[-2:]
    col = BOSS_C if who == "boss" else EMP_C
    y0 = 1620
    stroke(ctx, rect(60, y0 - 70, W - 60, y0 + 70 + 78 * (len(lines) - 1) + 20), 6, seed=90, closed=True, fill=(1, 1, 1), amp=1.5)
    name = "BOSS" if who == "boss" else "ME"
    stroke(ctx, rect(90, y0 - 128, 90 + (150 if who == "boss" else 90), y0 - 72), 5, col=col, seed=91, closed=True, fill=col, amp=1.2)
    text(ctx, name, 90 + (75 if who == "boss" else 45), y0 - 100, 46, col=(1, 1, 1))
    for i, ln in enumerate(lines):
        text(ctx, ln, W / 2, y0 + 5 + i * 78, 66, anchor="mm")


# ------------------------------------------------------------------ build
def plan():
    t, lines, audio = START, [], [np.zeros(int(START * SR), np.float32)]
    for who, line, *rest in SCRIPT:
        a = boss_voice(line) if who == "boss" else emp_voice(line)
        dur = len(a) / SR
        words = line.split()
        lens = np.array([len(w) + 2 for w in words], float)
        starts = t + dur * 0.92 * np.r_[0, np.cumsum(lens)[:-1]] / lens.sum()
        gap = 0.9 if rest[-1] in ("zoom",) else (1.2 if rest[-1] == "leave" else GAP)
        lines.append(dict(who=who, text=line, t0=t, t1=t + dur, env=envelope(a), words=list(zip(words, starts)),
                          bpose=rest[0], epose=rest[1], bface=rest[2], eface=rest[3], extra=rest[4]))
        audio += [a, np.zeros(int(gap * SR), np.float32)]
        t += dur + gap
    tail = 3.0
    audio.append(np.zeros(int(tail * SR), np.float32))
    return lines, np.concatenate(audio), t + tail


def lerp_pose(a, b, k):
    return tuple(tuple(x + (y - x) * k for x, y in zip(pa, pb)) for pa, pb in zip(a, b))


def sfx(kind, n):
    tt = np.arange(int(n * SR)) / SR
    rng = np.random.default_rng(7)
    if kind == "scratch":
        f = 300 + 1800 * np.abs(np.sin(tt * 18))
        return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / 0.2) * 0.25 + rng.normal(0, .05, len(tt)) * np.exp(-tt / .1)).astype(np.float32)
    if kind == "cricket":
        chirp = (np.sin(2 * np.pi * 4200 * tt) * (np.sin(2 * np.pi * 30 * tt) > 0.3) * ((tt % 0.9) < 0.25)).astype(np.float32)
        return chirp * 0.06
    if kind == "whoosh":
        s = rng.normal(0, 1, len(tt)) * np.sin(np.pi * tt / n) ** 2
        return (np.convolve(s, np.ones(40) / 40, "same") * .3).astype(np.float32)
    if kind == "step":
        return (np.sin(2 * np.pi * 120 * tt) * np.exp(-tt / .03) * .25).astype(np.float32)
    return np.zeros(len(tt), np.float32)


def render(out):
    global BOIL
    lines, audio, total = plan()

    def add(snd, at):
        i = int(at * SR)
        audio[i:i + len(snd)] += snd[:max(0, len(audio) - i)]
    for k in np.arange(0.1, 1.5, 0.35):
        add(sfx("step", .1), k)
    z = next(L for L in lines if L["extra"] == "zoom")
    add(sfx("scratch", .6), z["t0"] - .05)
    leave = next(L for L in lines if L["extra"] == "leave")
    for k in np.arange(leave["t1"] + .1, leave["t1"] + 1.2, .3):
        add(sfx("step", .1), k)
    add(sfx("cricket", 3.0), total - 3.0)

    boss = Figure(330, 1, BOSS_C, "tie", 1.08)
    emp = Figure(640, -1, EMP_C, "ponytail", 1.0)
    surf = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
    with tempfile.TemporaryDirectory() as d:
        wav = os.path.join(d, "a.wav")
        sf.write(wav, np.clip(audio, -1, 1), SR)
        prev_b, prev_e = POSES["idle"], POSES["idle"]
        cur = lines[0]
        for fi in range(int(total * FPS)):
            t = fi / FPS
            BOIL = fi // 3
            li = max([i for i, L in enumerate(lines) if L["t0"] - 0.25 <= t] or [0])
            L = lines[li]
            if L is not cur:
                prev_b = lerp_pose(prev_b, POSES[cur["bpose"]], 1)
                prev_e = lerp_pose(prev_e, POSES[cur["epose"]], 1)
                cur = L
            k = V.ease((t - (L["t0"] - 0.25)) / 0.35)
            bp = lerp_pose(POSES[lines[li - 1]["bpose"]] if li else POSES["idle"], POSES[L["bpose"]], k)
            ep = lerp_pose(POSES[lines[li - 1]["epose"]] if li else POSES["idle"], POSES[L["epose"]], k)
            ctx = cairo.Context(surf)
            ctx.set_source_rgb(1, 1, 1)
            ctx.paint()
            # camera: gentle push towards whoever talks; a snap zoom on the boss at "Overtime?"
            spk = boss if L["who"] == "boss" else emp
            zoom, fx = BASE_ZOOM, spk.x
            if L["extra"] == "zoom":
                zoom = BASE_ZOOM + .5 * V.ease((t - L["t0"] + .1) / .15)
            if L["extra"] == "alone" or t > lines[-1]["t1"]:
                zoom = BASE_ZOOM + .25 * V.ease((t - L["t0"]) / 1.5)
                fx = boss.x
            cam_x = W / 2 + (fx - W / 2) * .35
            ctx.translate(W / 2, 1180)
            ctx.scale(zoom, zoom)
            ctx.translate(-cam_x, -1120)
            office(ctx, t)
            # boss walks in at the start, backs off near the end; employee walks to her desk and away
            bwalk = 0.0
            if t < START:
                boss.x = -150 + (330 + 150) * V.ease(t / START)
                bwalk = t * 1.8
            elif L["bpose"] == "backoff":
                boss.x = 330 - 60 * V.ease((t - L["t0"]) / 1.2)
            ewalk = 0.0
            if L["extra"] == "leave" and t > L["t1"]:
                p = (t - L["t1"]) / 1.2
                emp.x = 640 + 650 * V.ease(p)
                emp.facing = 1
                ewalk = t * 1.8 if p < 1 else 0
            elif L["extra"] == "alone":
                emp.x = 1400
            mouth_b = mouth_e = 0.0
            if L["t0"] <= t <= L["t1"]:
                v = L["env"][min(int((t - L["t0"]) * FPS), len(L["env"]) - 1)]
                if L["who"] == "boss":
                    mouth_b = v
                else:
                    mouth_e = v
            blink_b = (t % 3.7) < 0.12
            blink_e = ((t + 1.3) % 4.1) < 0.12
            tilt_e = 6 if L["eface"] == "puzzled" else 0
            bhead = boss.draw(ctx, t, bp, L["bface"], mouth_b, bwalk, blink_b and L["bface"] != "shock", seed=100)
            if emp.x < 1300:
                emp.draw(ctx, t, ep, L["eface"], mouth_e, ewalk, blink_e, tilt_e, seed=200)
            if L["extra"] == "zoom" or L["bface"] == "shock":
                text(ctx, "?!", bhead[0] + 60, bhead[1] - 110, 110, col=BOSS_C, rot=.15)
            if L["bface"] == "worried":
                for j in range(2):                                   # sweat drops
                    yy = bhead[1] - 20 + ((t * 60 + j * 30) % 60)
                    stroke(ctx, [(bhead[0] - 70 - j * 18, yy - 14), (bhead[0] - 78 - j * 18, yy), (bhead[0] - 62 - j * 18, yy)],
                           4, col=(.3, .55, .9), seed=300 + j, closed=True, fill=(.75, .87, 1))
            if L["extra"] == "count" and L["t0"] <= t <= L["t1"]:
                n = min(4, 1 + int((t - L["t0"]) / ((L["t1"] - L["t0"]) / 4.5)))
                for j in range(n):
                    text(ctx, str(j + 1), emp.x - 170 + j * 55, 760, 80, col=EMP_C)
            # screen-space overlays
            ctx.identity_matrix()
            ctx.set_source_rgb(1, 1, 1)                          # clean strip behind the title
            ctx.rectangle(0, 0, W, 345)
            ctx.fill()
            stroke(ctx, [(40, 345), (W - 40, 345)], 4, col=(.75, .75, .78), seed=97, amp=1.5)
            text(ctx, "When your boss asks", W / 2, 190, 88)
            text(ctx, "for the impossible...", W / 2, 285, 88, col=BOSS_C)
            if L["t0"] - .1 <= t <= L["t1"] + .3 and t <= lines[-1]["t1"] + .3:
                caption(ctx, L["who"], L["words"], t)
            if t > lines[-1]["t1"] + .4:
                k2 = V.ease((t - lines[-1]["t1"] - .4) / .4)
                stroke(ctx, rect(140, 1560, W - 140, 1760), 7, seed=95, closed=True, fill=(1, 1, 1))
                text(ctx, "Always get it", W / 2, 1620, 78 * k2 + 1)
                text(ctx, "in writing.", W / 2, 1705, 78 * k2 + 1, col=EMP_C)
            surf.write_to_png(os.path.join(d, f"f{fi:04d}.png"))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(d, "f%04d.png"),
                        "-i", wav, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-c:a", "aac", "-b:a", "160k",
                        "-shortest", out], check=True)
    print("wrote", out, f"({total:.1f} s)")


if __name__ == "__main__":
    render(sys.argv[1] if len(sys.argv) > 1 else "stick_office.mp4")
