"""'The most honest job interview ever' - stylized stick-people skit (1080x1920, ~60 s). Original script
(interview_lines.py) in the popular stick-figure job-interview format.

    python skits/interview.py out.mp4

A hiring manager and a very honest candidate across a desk (the desk hides their legs: they look seated). Mouths
move with each voice's loudness; faces and gestures change per line; the camera cuts between a two-shot and close-ups,
with punch-ins and a shake on the big moments. Sound: both voices (Chatterbox, built from Kokoro voices), office room
tone, paper shuffle, a sting and a record scratch.
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
sys.path.insert(0, HERE)
import voices                                                   # noqa: E402
from five_min import ogg, synth                                 # noqa: E402
from interview_lines import BOSS, GIRL, LINES                   # noqa: E402
from stick_people import LOOKS, StickPerson                     # noqa: E402
from toon import ellipse, lin, poly, rad, rgb, rrect, text      # noqa: E402

W, H, FPS, SR = 1080, 1920, 24, voices.SR
FONT = os.path.join(HERE, "assets", "poppins-800.ttf")
FONT2 = os.path.join(HERE, "assets", "poppins-600.ttf")
FLOOR = 1560
BX, GX = 290, 800                  # where the manager and the candidate sit


def ease(t):
    return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, t)))


# tone -> face; per line: (manager arms, candidate arms, listener face)
TONE_FACE = {"neutral": "neutral", "annoyed": "annoyed", "shocked": "shock", "calm": "neutral", "sassy": "smug",
             "excited": "happy", "fake": "happy", "sheepish": "sad"}
REST = ((10, -60), (10, -60))                       # forearms on the desk
GEST = {
    "q1": (((30, 80), (10, -60)), REST, "neutral"),
    "a1": (REST, ((40, 110), (10, -60)), "annoyed"),
    "q2": (((10, -60), (40, 120)), REST, "neutral"),
    "a2": (REST, ((70, 120), (10, -60)), "annoyed"),
    "q3": (((30, 90), (30, 90)), REST, "neutral"),
    "a3": (REST, ((150, 30), (10, -60)), "shock"),
    "q3b": (((110, 40), (110, 40)), ((20, 60), (20, 60)), "sad"),
    "a3b": (((60, 110), (60, 110)), ((150, 20), (150, 20)), "annoyed"),
    "q4": (((30, 80), (10, -60)), REST, "neutral"),
    "a4": (REST, ((60, 120), (60, 120)), "sus"),
    "q5": (((40, 100), (10, -60)), REST, "neutral"),
    "a5": (REST, ((150, 20), (150, 20)), "annoyed"),
    "q6": (((20, 60), (20, 60)), REST, "shock"),
    "a6": (REST, ((100, 60), (100, 60)), "smug"),
    "q7": (((80, 60), (10, -60)), REST, "annoyed"),
    "a7": (REST, ((60, 120), (10, -60)), "smug"),
    "q8": (((110, 30), (110, 30)), REST, "shock"),
    "a8": (REST, ((60, 120), (60, 120)), "sad"),
    "q9": (((30, 80), (10, -60)), REST, "neutral"),
    "a9": (REST, ((40, 110), (10, -60)), "shock"),
}
# camera per line: (zoom, focus x, focus y) at start and end; None = auto (close on the speaker)
WIDE = (1.2, 540, 1090)
CAMS = {"q1": (WIDE, (1.28, 540, 1070)), "q3b": ((2.0, BX, 960), (2.2, BX, 950)), "a6": ((1.7, GX, 980), (2.3, GX, 960)),
        "q7": ((1.7, BX, 980), (2.1, BX, 970)), "q8": (WIDE, (1.3, 540, 1080)), "a9": ((1.5, 540, 1040), (2.0, GX, 970))}


def office(ctx, t):
    ctx.rectangle(-3000, -3000, W + 6000, FLOOR + 3000)
    ctx.set_source(lin(ctx, 0, 0, 0, FLOOR, [(0, "#e7eef7"), (1, "#cdd9ea")]))
    ctx.fill()
    ctx.rectangle(-3000, FLOOR, W + 6000, 3000)
    ctx.set_source_rgb(*rgb("#8a93a6"))
    ctx.fill()
    rrect(ctx, 360, 330, 360, 360, 16, fill=lin(ctx, 0, 330, 0, 690, [(0, "#8fd3ff"), (1, "#e8f7ff")]), w=10)
    for bx, bw, bh in ((380, 70, 200), (460, 90, 280), (560, 60, 160), (630, 80, 240)):
        rrect(ctx, bx, 690 - bh, bw, bh, 6, fill="#9fb0d8", line=None)
    poly(ctx, [(540, 330), (540, 690)], w=8, close=False)
    rrect(ctx, 790, 380, 220, 170, 10, fill="#ffffff", w=7)                       # motivational poster
    text(ctx, "TEAMWORK", 900, 445, 32, FONT, col="#4b5563")
    text(ctx, "makes the", 900, 480, 24, FONT2, col="#4b5563")
    text(ctx, "dream work", 900, 512, 24, FONT2, col="#4b5563")
    ellipse(ctx, 160, 460, 70, 70, fill=(1, 1, 1), w=7)                            # clock
    a = t * 0.6
    poly(ctx, [(160, 460), (160 + 45 * math.sin(a), 460 - 45 * math.cos(a))], w=6, close=False)
    poly(ctx, [(160, 460), (160, 420)], w=7, close=False)
    rrect(ctx, 880, 1020, 190, 22, 6, fill="#c89a74", w=6)                          # shelf
    rrect(ctx, 930, 900, 100, 120, 12, fill="#e58f6a", w=6)                        # plant
    for a in (-0.7, -0.2, 0.3, 0.8):
        ellipse(ctx, 980 + 65 * math.sin(a), 840 - 55 * math.cos(a), 28, 56, fill="#6cc48a", w=5)


def desk(ctx, t):
    rrect(ctx, -60, 1310, W + 120, 60, 14, fill="#c89a74", w=8)
    rrect(ctx, -60, 1365, W + 120, 900, 0, fill="#a8764f", w=8)
    rrect(ctx, 380, 1420, 320, 200, 12, fill="#b98560", w=6)                         # desk front panel
    rrect(ctx, 60, 1245, 200, 70, 10, fill="#e9eef6", w=6)                           # nameplate
    text(ctx, "HIRING MGR", 160, 1282, 26, FONT, col="#4b5563")
    rrect(ctx, 430, 1265, 110, 46, 6, fill="#ffffff", w=5)                           # resume
    for i in range(3):
        poly(ctx, [(445, 1277 + i * 10), (525, 1277 + i * 10)], line="#b9c3cc", w=3, close=False)
    rrect(ctx, 960, 1225, 70, 85, 12, fill="#ffffff", w=6)                           # coffee
    ctx.set_source(rad(ctx, 995, 1205, 60, [(0, "#ffffff", .5), (1, "#ffffff", 0)]))
    ctx.paint()


def build():
    t, plan = 0.6, []
    tracks = {BOSS: np.zeros(int(120 * SR), np.float32), GIRL: np.zeros(int(120 * SR), np.float32)}
    for key, who, line in LINES:
        a = voices.say(who, line)
        tone, txt = voices.split_tag(line)
        tracks[who][int(t * SR):int(t * SR) + len(a)] += a
        words = txt.split()
        lens = np.array([len(w) + 2 for w in words], float)
        dur = len(a) / SR
        plan.append(dict(key=key, who=who, tone=tone, text=txt, t0=t, t1=t + dur,
                         words=list(zip(words, t + dur * 0.93 * np.r_[0, np.cumsum(lens)[:-1]] / lens.sum()))))
        gap = 0.2 if key.startswith("q") else 0.3
        if key in ("a3", "a5", "a7"):
            gap = 0.45                                                   # beat before the manager's comeback
        t += dur + gap
    total = t + 2.4
    n = int(total * SR)
    env = {}
    for who, tr in tracks.items():                                       # mouth opening per frame from loudness
        tr = tr[:n]
        hop = SR // FPS
        rms = np.sqrt(np.convolve(tr ** 2, np.ones(hop) / hop, "same"))[::hop]
        env[who] = np.clip(rms / (np.percentile(rms[rms > 1e-4], 90) + 1e-6), 0, 1.2)
    voice = voices.clarity(tracks[BOSS][:n] + tracks[GIRL][:n])
    fx = synth("cafe", total) * 0.25                                     # quiet office room tone

    def add(x, at):
        i = int(at * SR)
        fx[i:i + len(x)] += x[:max(0, n - i)]
    add(ogg("cloth3", .8), 0.1)                                          # paper shuffle
    by = {p["key"]: p for p in plan}
    add(synth("sting", .8), by["q3b"]["t0"] - .1)
    add(synth("sting", .8), by["a6"]["t0"] + .3)
    scratch = np.sin(2 * np.pi * (900 - 2400 * np.arange(int(.35 * SR)) / SR) * np.arange(int(.35 * SR)) / SR) * .12
    add(scratch.astype(np.float32), by["q8"]["t1"] + .05)                # record scratch after "family"
    mix = voice + fx
    return plan, env, (mix / max(np.abs(mix).max(), 1e-6) * .95).astype(np.float32), total


def state(plan, T):
    p = max((x for x in plan if x["t0"] - .25 <= T), key=lambda x: x["t0"], default=plan[0])
    return p


def cam_for(p, t):
    c = CAMS.get(p["key"])
    if c is None:
        x = BX if p["who"] == BOSS else GX
        c = ((1.6, x, 990), (1.7, x, 980))
    k = ease(t / max(p["t1"] - p["t0"] + .3, .5))
    return tuple(a + (b - a) * k for a, b in zip(*c))


def blend_arms(a, b, k):
    return tuple(tuple(x + (y - x) * k for x, y in zip(sa, sb)) for sa, sb in zip(a, b))


def render(out):
    plan, env, audio, total = build()
    boss = StickPerson(LOOKS["boss"], x=BX, floor=FLOOR, scale=1.0, facing=0.5)
    girl = StickPerson(LOOKS["candidate"], x=GX, floor=FLOOR, scale=0.95, facing=-0.5)
    surf = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
    with tempfile.TemporaryDirectory() as d:
        wav = os.path.join(d, "a.wav")
        sf.write(wav, audio, SR)
        enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}",
                                "-framerate", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-pix_fmt", "yuv420p",
                                "-crf", "19", "-c:a", "aac", "-b:a", "192k", "-shortest", out], stdin=subprocess.PIPE)
        prev = {BOSS: REST, GIRL: REST}
        for fi in range(int(total * FPS)):
            T = fi / FPS
            p = state(plan, T)
            i = plan.index(p)
            t = T - p["t0"]
            ctx = cairo.Context(surf)
            cam = cam_for(p, t)
            shake = 14 * math.sin(T * 70) * max(0, 1 - (T - plan[i]["t1"]) / .5) if p["key"] == "q8" and T > p["t1"] else 0
            ctx.translate(W / 2 + shake, 1000)
            ctx.scale(cam[0], cam[0])
            ctx.translate(-cam[1], -cam[2])
            office(ctx, T)
            ga, gb, listen = GEST[p["key"]]
            last = GEST[plan[i - 1]["key"]] if i else (REST, REST, "neutral")
            k = ease((t + .25) / .35)
            arms = {BOSS: blend_arms(last[0], ga, k), GIRL: blend_arms(last[1], gb, k)}
            for who, person, x in ((BOSS, boss, BX), (GIRL, girl, GX)):
                speaking = p["who"] == who
                face = TONE_FACE.get(p["tone"], "neutral") if speaking else listen
                if p["key"] == "a4" and who == GIRL:
                    face = "sad"
                e = env[who]
                m = float(e[min(fi, len(e) - 1)]) if speaking and p["t0"] <= T <= p["t1"] + .05 else 0.0
                blink = (T + (0.9 if who == GIRL else 0)) % 3.6 < 0.1
                look = (0.8, 0) if who == BOSS else (-0.8, 0)
                bob = 3 * math.sin(T * 2.2 + (1 if who == GIRL else 0))
                person.draw(ctx, arms=arms[who], legs=((4, 0), (4, 0)), face=face, mouth=min(1, m * 0.9), look=look,
                            tilt=(4 if who == BOSS else -4) * (1 if speaking else 0.3), bob=bob, blink=blink)
            desk(ctx, T)
            ctx.identity_matrix()
            # title + captions
            rrect(ctx, 130, 80, W - 260, 120, 34, fill=(1, 1, 1), w=6)
            text(ctx, "the most HONEST job interview", W / 2, 140, 44, FONT, col="#e0457b")
            said = [j for j, (_, st) in enumerate(p["words"]) if st <= T]
            if said and T <= p["t1"] + .3:
                c0 = said[-1] // 3 * 3
                chunk = " ".join(w for w, _ in p["words"][c0:said[-1] + 1]).upper()
                col = (0.62, 0.84, 1.0) if p["who"] == BOSS else (1, 0.62, 0.78)
                size = 70 if len(chunk) < 22 else int(70 * 22 / len(chunk))
                text(ctx, chunk, W / 2, 1740, size, FONT, col=col, outline=(0.1, 0.08, 0.1), ow=12)
                text(ctx, "MANAGER" if p["who"] == BOSS else "CANDIDATE", W / 2, 1650, 32, FONT, col=col,
                     outline=(0.1, 0.08, 0.1), ow=8)
            if T > plan[-1]["t1"] + .4:
                kk = ease((T - plan[-1]["t1"] - .4) / .3)
                rrect(ctx, 140, 1560, W - 280, 230, 40, fill="#e0457b", w=6)
                text(ctx, "part 2: her first day?", W / 2, 1640, 54 * kk + 1, FONT, col=(1, 1, 1))
                text(ctx, "follow so you don't miss it", W / 2, 1715, 36 * kk + 1, FONT2, col=(1, 1, 1))
            surf.flush()
            enc.stdin.write(bytes(surf.get_data()))
        enc.stdin.close()
        if enc.wait():
            raise RuntimeError("ffmpeg failed")
    print("wrote", out, f"({total:.1f} s)")


if __name__ == "__main__":
    render(sys.argv[1] if len(sys.argv) > 1 else "interview.mp4")
