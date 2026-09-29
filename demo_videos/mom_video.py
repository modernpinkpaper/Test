""""Skinny mom energy" - a 30-second talking video with the cut-out puppet.

Framed from the knees up. She walks in, then talks with gestures (wave, shrug, hand on hip,
arms out, hands to heart, point up). Mouth follows the voice, she blinks, hair swings.
Voice: Chatterbox copying voices/my-voice-ref.wav (see truth_bomb.voice).

    python demo_videos/mom_video.py
"""
import math
import os
import random
import subprocess

import imageio
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import puppet as P
import truth_bomb as T
from mom_script import SCRIPT

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS, SR = 1080, 1920, 30, 24000
SCALE, ROOT_Y = 1.7, 1110          # knees fall just below the bottom of the frame
GAP = 0.22
HANG = dict(upper_arm_r=-8, lower_arm_r=-4, upper_arm_l=8, lower_arm_l=4)


# ------------------------------------------------------------------ gestures
def walk_cycle(t, a, speed=2.2):
    """Front-view walk: body bobs, hips sway, arms and legs swing in turn."""
    ph = t * speed * 2 * math.pi
    s = math.sin(ph)
    a.update(upper_arm_r=-8 - 14 * s, lower_arm_r=-10 - 10 * s, upper_arm_l=8 - 14 * s, lower_arm_l=10 - 10 * s,
             upper_leg_r=6 * s, lower_leg_r=3 * s, upper_leg_l=6 * s, lower_leg_l=3 * s,
             hips=4 * s, torso=-2 * s, head=2 * s)
    return abs(math.cos(ph)) * 14   # how much she rises in the step


def gesture(name, t, dur):
    """Target angles for a gesture `t` seconds into a line of length `dur`. Returns (angles, x_shift, lift)."""
    a = dict(P.REST)
    a.update(HANG)
    x, lift = 0.0, 0.0
    if name == "walk_wave":
        walk_t = min(t, dur * 0.55)
        if t < dur * 0.55:
            lift = walk_cycle(t, a)
            k = t / (dur * 0.55)
            x = (1 - (1 - (1 - k) ** 2)) * 700      # slides in from the right, slowing down
        else:
            name, t = "wave", t - walk_t
    if name == "wave":
        a.update(upper_arm_l=150, lower_arm_l=168 + 20 * math.sin(t * 11), head=4)
    elif name == "shrug":
        a.update(upper_arm_r=-32, lower_arm_r=-88, upper_arm_l=32, lower_arm_l=88, head=8, torso=2)
        lift = 12
    elif name == "hand_hip":
        a.update(upper_arm_l=32, lower_arm_l=-38, upper_arm_r=-18, lower_arm_r=-65 - 10 * math.sin(t * 4),
                 torso=-4, head=-5, hips=6)
    elif name == "arms_out":
        b = abs(math.sin(t * 5))
        a.update(upper_arm_r=-60, lower_arm_r=-105, upper_arm_l=60, lower_arm_l=105, torso=0)
        lift = 18 * b
    elif name == "heart":
        a.update(upper_arm_r=-14, lower_arm_r=112, upper_arm_l=14, lower_arm_l=-112, head=-6)
    elif name == "walk_place":
        lift = walk_cycle(t, a, speed=1.8)
        x = -150
    elif name == "point_up":
        a.update(upper_arm_r=-168, lower_arm_r=-176, upper_arm_l=32, lower_arm_l=-38, head=-4, hips=5)
    return a, x, lift


# ------------------------------------------------------------------ scene
def room():
    """A soft, slightly blurred living-room wall."""
    img = T.gradient("#ffe9df", "#ffc9d6").convert("RGBA")
    d = ImageDraw.Draw(img, "RGBA")
    # window with daylight
    d.rounded_rectangle([90, 260, 470, 900], radius=30, fill=(255, 255, 255, 255))
    for i in range(20):
        c = (170 + i * 3, 215 + i, 245, 255)
        d.rectangle([110, 280 + i * 30, 450, 310 + i * 30], fill=c)
    d.line([(280, 280), (280, 880)], fill=(255, 255, 255), width=14)
    d.line([(110, 580), (450, 580)], fill=(255, 255, 255), width=14)
    d.polygon([(470, 260), (900, 1500), (620, 1500), (90, 900)], fill=(255, 255, 255, 40))  # light beam
    # picture frame and plant
    d.rounded_rectangle([700, 330, 960, 560], radius=14, fill=(255, 255, 255), outline=(200, 150, 140), width=10)
    d.ellipse([760, 380, 900, 510], fill=(255, 180, 200))
    T.heart(d, 830, 440, 34, (255, 255, 255))
    d.rounded_rectangle([830, 1180, 1010, 1420], radius=20, fill=(214, 140, 110))
    rng = random.Random(3)
    for _ in range(14):
        x, y = rng.randint(800, 1040), rng.randint(900, 1200)
        d.ellipse([x - 55, y - 28, x + 55, y + 28], fill=(90, 160, 110, 230))
    d.rectangle([0, 1560, W, H], fill=(235, 190, 170))   # floor (mostly below her knees)
    return img.filter(ImageFilter.GaussianBlur(4))


def checklist(prog):
    im = Image.new("RGBA", (440, 400), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i, txt in enumerate(["Drink the water", "Take the walk", "Eat real food"]):
        y = 10 + i * 130
        on = prog > (i + 0.7) / 3
        d.rounded_rectangle([0, y, 430, y + 105], radius=52, fill=(255, 255, 255), outline=T.OUT, width=6)
        d.ellipse([18, y + 20, 83, y + 85], fill=T.HOT if on else (240, 220, 230), outline=T.OUT, width=5)
        if on:
            d.line([(33, y + 52), (48, y + 68), (70, y + 36)], fill=(255, 255, 255), width=9)
        d.text((100, y + 53), txt, font=T.font(800, 40), anchor="lm", fill=T.OUT)
    return im


def main():
    pup = P.Puppet(scale=SCALE)
    bg = room()
    # voice
    lines, clips, t = [], [], 0.3
    for text, g, extra in SCRIPT:
        a = T.voice(text)
        lines.append(dict(text=text, gesture=g, extra=extra, start=t, end=t + len(a) / SR))
        clips.append((t, a))
        t += len(a) / SR + GAP
    total = t + 0.8
    n = int(total * FPS)
    vo = np.zeros(int(total * SR) + SR, np.float32)
    for st, a in clips:
        vo[int(st * SR):int(st * SR) + len(a)] += a
    hop = SR // FPS
    env = np.array([np.sqrt(np.mean(vo[i * hop:(i + 1) * hop] ** 2)) for i in range(n)])
    env = np.convolve(env / (env.max() + 1e-6), np.ones(3) / 3, "same")

    silent = os.path.join(HERE, "_mom_silent.mp4")
    wr = imageio.get_writer(silent, fps=FPS, codec="libx264", quality=8, macro_block_size=1)
    cur = dict(P.REST)
    cur.update(HANG)
    x_now, hair, hair_v, prev_head = 700.0, 0.0, 0.0, 0.0
    mouth, particles, rng = "closed", [], random.Random(5)
    for fr in range(n):
        sec = fr / FPS
        ln = max([l for l in lines if l["start"] - 0.25 <= sec] or [lines[0]], key=lambda l: l["start"])
        lt, dur = sec - ln["start"], ln["end"] - ln["start"]
        target, x_t, lift = gesture(ln["gesture"], max(0.0, lt), dur)
        # ease every joint toward the gesture (walk and wave move fast, so follow them closely)
        k = 0.55 if ln["gesture"] in ("walk_wave", "walk_place", "wave") else 0.22
        for key, v in target.items():
            cur[key] = cur.get(key, 0) + (v - cur.get(key, 0)) * k
        x_now += (x_t - x_now) * (0.5 if ln["gesture"] == "walk_wave" else 0.12)
        level = env[fr] if fr < len(env) else 0
        a = dict(cur)
        a["head"] = a.get("head", 0) + 3 * math.sin(sec * 1.7) + 4 * level
        a["torso"] = a.get("torso", 0) + 1.5 * math.sin(sec * 1.3)
        head_world = a["torso"] + a["head"]
        hair_v += -(head_world - prev_head) * 0.6 - hair * 0.15
        hair_v *= 0.8
        hair = max(-10, min(10, hair + hair_v))
        prev_head = head_world
        a["hair"] = hair
        if fr % 2 == 0:
            mouth = ("closed" if level < 0.12 else "slight" if level < 0.35 else
                     ("ee", "oh")[(fr // 4) % 2] if level < 0.65 else "ah")
        blink = fr % 97
        eyes = "closed" if blink in (1, 2) else "half" if blink in (0, 3) else "open"
        brows = "raised" if level > 0.75 else "neutral"

        img = bg.copy()
        root = (540 + x_now, ROOT_Y - lift - 10 * level)
        pup.render(img, root, a, face=(eyes, brows, mouth))

        d = ImageDraw.Draw(img, "RGBA")
        if ln["extra"] == "checklist":
            s = T.pop_scale(lt - 0.2) if lt > 0.2 else 0.01
            ck = checklist(max(0, lt) / dur)
            ck = ck.resize((max(1, int(ck.width * s)), max(1, int(ck.height * s))))
            img.alpha_composite(ck, (int(850 - ck.width / 2), int(620 - ck.height / 2)))
        if ln["gesture"] == "heart" and fr % 5 == 0:
            particles.append(["heart", rng.uniform(380, 700), 900, rng.uniform(20, 34), 0])
        if ln["gesture"] == "arms_out" and fr % 4 == 0:
            particles.append(["spark", rng.uniform(150, 930), rng.uniform(300, 900), rng.uniform(14, 26), 0])
        alive = []
        for p in particles:
            p[4] += 1
            if p[0] == "heart" and p[4] < 50:
                p[2] -= 7
                T.heart(d, p[1], p[2], p[3], (255, 90, 140, int(255 * (1 - p[4] / 50))))
                alive.append(p)
            elif p[0] == "spark" and p[4] < 16:
                T.sparkle(d, p[1], p[2], p[3] * math.sin(math.pi * p[4] / 16), (255, 255, 255, 230))
                alive.append(p)
        particles = alive

        if 0 <= lt and sec <= ln["end"] + GAP:
            words = [(w.strip("*"), w.startswith("*")) for w in ln["text"].split()]
            prog = max(0.0, min(1.0, lt / max(0.1, dur)))
            T.draw_caption(ImageDraw.Draw(img), words, max(1, math.ceil(prog * len(words))),
                           max(0.0, 1 - ((prog * len(words)) % 1) * 4))
        wr.append_data(np.asarray(img.convert("RGB")))
        if fr % 150 == 0:
            print(f"frame {fr}/{n}", flush=True)
    wr.close()

    fx = np.zeros_like(vo)
    for ln in lines:
        s = int(max(0, ln["start"] - 0.05) * SR)
        e = T.sfx_pop()
        fx[s:s + len(e)] += e[:len(fx) - s]
    m = int(total * SR)
    mix = vo[:m] + fx[:m] + T.beat(total)[:m] * 0.7
    mix = np.clip(mix / max(1.0, np.abs(mix).max() / 0.95), -1, 1)
    wav = os.path.join(HERE, "_mom.wav")
    out = os.path.join(HERE, "mom_energy.mp4")
    import soundfile as sf
    sf.write(wav, mix, SR)
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ff, "-loglevel", "error", "-y", "-i", silent, "-i", wav, "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "160k", "-shortest", out], check=True)
    os.remove(silent)
    os.remove(wav)
    print("saved", out, f"({total:.1f}s)")


if __name__ == "__main__":
    main()
