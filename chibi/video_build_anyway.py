"""'Build it anyway': her chibi girl talking straight to camera from the driver's seat (phone POV), 1080x1920.

    python chibi/video_build_anyway.py out.mp4 [ambience_library_dir]

Format studied from a talk-to-camera car video (short firm "Stop..." lines, one metaphor, one closing command),
with an original script on her own topic. Voice: "af_sky" (a built-in synthetic voice that belongs to no real
person) through the same emotion controls as her other videos. Rig, captions and lip-sync come from video_day.py.
"""
import math
import os
import subprocess
import sys

from PIL import ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, "..", "skits")]
import video_day as D                                             # noqa: E402
from toon import ellipse, lin, poly, rgb, rrect                   # noqa: E402

W, H = D.W, D.H
VOICE = "af_sky"
X0 = 560                                    # her x in the seat
ease, lerp, stand, blend = D.ease, D.lerp, D.stand, D.blend

LINES = [
    ("build", "her", "[calm] Build it anyway."),
    ("nobody", "her", "[calm] Nobody is coming to approve your idea."),
    ("waiting", "her", "[annoyed] Stop waiting for the perfect time."),
    ("story", "her", "[calm] The perfect time is a story we tell ourselves, so we never have to start."),
    ("liked", "her", "[sassy] Stop checking who liked it, and who didn't."),
    ("bills", "her", "[sassy] Their opinion doesn't pay your bills."),
    ("prices", "her", "[annoyed] Stop shrinking your prices to make other people comfortable."),
    ("discount", "her", "[calm] You are not a discount."),
    ("house", "her", "[calm] Think of your life like a house you're building."),
    ("key", "her", "[neutral] You pick the walls, the windows, and who gets a key."),
    ("everybody", "her", "[sassy] Not everybody gets a key."),
    ("failures", "her", "[calm] Quit carrying last year's failures into this year's work."),
    ("end", "her", "[excited] Build it anyway."),
]

# her left hand talks; the phone is the camera (on the dash), so the right arm rests
D.POSES.update({
    "selfie": {},
    "s_point": {"left": (-30, -130, -10, "index_up")},
    "s_palm": {"left": (-20, -85, -35, "palm_up")},
    "s_stop": {"left": (-35, -130, 12, "open")},
    "s_peace": {"left": (-35, -130, 10, "two")},
})


# ------------------------------------------------------------------ the car (world coordinates)
TREES = [(-60, 560, 120), (90, 500, 90), (40, 660, 130), (960, 520, 110), (1110, 600, 120), (1000, 690, 90),
         (300, 520, 100), (420, 480, 80), (560, 500, 110), (700, 480, 90), (820, 520, 100)]


def rpath(ctx, x, y, w_, h_, r):
    """Rounded-rect path only (to clip to)."""
    ctx.new_sub_path()
    ctx.arc(x + w_ - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w_ - r, y + h_ - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h_ - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    ctx.close_path()


def car(ctx, t):
    ctx.rectangle(-600, -600, W + 1200, 2800)
    ctx.set_source_rgb(*rgb("#3d3e48"))
    ctx.fill()
    for x0, y0, w_, h_ in ((-200, 300, 380, 700), (230, 380, 640, 300), (920, 300, 380, 700)):   # windows
        ctx.save()
        rpath(ctx, x0, y0, w_, h_, 40)
        ctx.clip()
        ctx.rectangle(x0, y0, w_, h_)
        ctx.set_source(lin(ctx, 0, y0, 0, y0 + h_, [(0, "#bfe4f7"), (1, "#f2e9f7")]))
        ctx.fill()
        for k, (tx, ty, r) in enumerate(TREES):
            sw = 4 * math.sin(t * 1.3 + k)
            ellipse(ctx, tx + sw, ty, r, r * 0.9, fill="#8fcf8a" if k % 2 else "#a4d99a", line=None, w=0)
        ctx.restore()
        rrect(ctx, x0, y0, w_, h_, 40, w=8)
    # roof liner and sunroof
    poly(ctx, [(-600, -600), (W + 600, -600), (W + 600, 300), (820, 380), (260, 380), (-600, 300)],
         fill=lin(ctx, 0, 0, 0, 380, [(0, "#d9cfe6"), (1, "#ebe3f3")]), line=None, w=0)
    rrect(ctx, 300, 40, 480, 250, 40, fill="#2f3038", w=8)
    ctx.save()
    rpath(ctx, 322, 60, 436, 210, 30)
    ctx.clip()
    ctx.rectangle(322, 60, 436, 210)
    ctx.set_source(lin(ctx, 0, 60, 0, 270, [(0, "#9fd6f5"), (1, "#dcf0fa")]))
    ctx.fill()
    poly(ctx, [(360, 270), (460, 60), (510, 60), (410, 270)], fill=(1, 1, 1), line=None, w=0)
    ctx.restore()
    for x0 in (180, 870):                                                    # pillars
        poly(ctx, [(x0, 300), (x0 + 50, 300), (x0 + 40, 1100), (x0 - 10, 1100)], fill="#4b4c58", w=6)
    rrect(ctx, 300, 820, 520, 900, 120, fill="#2c2d36", w=8)                  # seat back
    rrect(ctx, 400, 360, 320, 330, 100, fill="#363744", w=8)                  # headrest
    for x in (520, 600):
        rrect(ctx, x - 8, 680, 16, 70, 6, fill="#9a9aa6", w=4)


def seatbelt(ctx, t):
    """Over her shoulder, across her chest (foreground)."""
    poly(ctx, [(690, 915), (728, 932), (470, 1500), (432, 1483)], fill="#6b6b78", w=6)
    poly(ctx, [(700, 922), (446, 1490)], line="#8a8a98", w=2, close=False)


# ------------------------------------------------------------------ shots
def shots():
    S = []

    def add(key, lead, tail, cam0, cam1, act, sfx=()):
        S.append(dict(key=key, lead=lead, tail=tail, scene=car, fg=seatbelt, cam0=cam0, cam1=cam1, act=act,
                      sfx=list(sfx)))

    def talk(face, pose, eyes_at=None, wag=False, end_face=None, end_pose=None):
        """Handheld-phone sway; she nods into the line; optional slow eye-close near the end."""
        def f(t, d, ls, le):
            sway = 5 * math.sin(t * 2.1)
            nod = 6 * math.sin(min(1, max(0, (t - ls) / 0.5)) * math.pi)
            p = pose
            if end_pose and t > le - 0.2:
                p = end_pose
            arms = blend(pose, p, ease((t - (le - 0.2)) / 0.3)) if p != pose else blend(pose, pose, 1)
            if wag and "left" in arms:
                l = list(arms["left"])
                l[2] += 14 * math.sin(t * 9)
                arms["left"] = tuple(l)
            fc = end_face if end_face and t > le - 0.1 else face
            eyes = "closed" if eyes_at is not None and le - eyes_at <= t <= le + 0.35 else None
            return dict(pos=(X0 + sway, stand(X0)[1] + 6 * math.sin(t * 3.1) + nod), rot=1.2 * math.sin(t * 1.7),
                        face=fc, arms=arms, look=(0, 0), tilt=-3 + 2 * math.sin(t * 1.1), eyes=eyes)
        return f

    near, mid, close = (1.6, 548, 860), (1.75, 548, 845), (2.05, 550, 815)
    add("build", 0.15, 0.45, mid, close, talk("smug", "s_point"), [("whoosh", 0.05)])
    add("nobody", 0.1, 0.35, near, near, talk("neutral", "s_palm"))
    add("waiting", 0.1, 0.3, near, mid, talk("annoyed", "s_stop"))
    add("story", 0.1, 0.5, mid, mid, talk("neutral", "s_palm", end_face="smug"))
    add("liked", 0.1, 0.3, near, near, talk("smug", "s_point"))
    add("bills", 0.1, 0.5, mid, close, talk("smug", "s_palm"), [("pop", ("le", 0.0))])
    add("prices", 0.1, 0.3, near, near, talk("annoyed", "s_stop"))
    add("discount", 0.1, 0.7, close, close, talk("calm", "selfie", eyes_at=0.6))
    add("house", 0.1, 0.3, near, mid, talk("happy", "s_stop"))
    add("key", 0.1, 0.4, mid, mid, talk("neutral", "s_point"))
    add("everybody", 0.1, 0.7, mid, close, talk("smug", "s_point", wag=True, end_face="wink"))
    add("failures", 0.1, 0.45, near, near, talk("annoyed", "s_palm"))
    add("end", 0.15, 1.2, mid, close, talk("excited", "s_point", end_pose="s_peace", end_face="happy"),
        [("chime", ("le", 0.1))])
    return S


# ------------------------------------------------------------------ overlay
def header(frame):
    d = ImageDraw.Draw(frame)
    d.rounded_rectangle((170, 80, W - 170, 200), 34, fill=(255, 255, 255), outline=(30, 24, 30), width=6)
    d.text((W / 2, 140), "BUILD IT ANYWAY", font=D.font(58), fill=D.PINK, anchor="mm")


def overlay(frame, S, s, t, T):
    header(frame)
    D.captions(frame, s, T)


def preview(out, times=(0.5, 1.5)):
    """Stills without the voice step: check the framing and the car."""
    from PIL import Image
    import cairocffi as cairo
    S = shots()
    for i, s in enumerate(S[:len(times)]):
        s.update(t0=0, d=2.0, ls=0.1, le=1.5, cues=[], words=[], who="her")
        bg = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
        ctx = cairo.Context(bg)
        D.cam_ctx(ctx, s["cam1"])
        car(ctx, 1.0)
        bg.flush()
        fr = Image.frombuffer("RGBA", (W, H), bytes(bg.get_data()), "raw", "BGRA", bg.get_stride(), 1).convert("RGBA")
        D.character(fr, s["act"](1.0, 2.0, 0.1, 1.5), s["cam1"], 1.0, s, 1.0)
        fg = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
        ctx = cairo.Context(fg)
        D.cam_ctx(ctx, s["cam1"])
        seatbelt(ctx, 1.0)
        fg.flush()
        fr.alpha_composite(D.surface_rgba(fg))
        header(fr)
        fr.convert("RGB").save(f"{out}_{i}.png")


def add_ambience(path, lib):
    """Quiet car cabin under the voice: low hum + birds outside, muffled through the glass."""
    birds = os.path.join(lib or "", "sounds", "birds_1.mp3")
    tmp = path.replace(".mp4", "_amb.mp4")
    inputs = ["-i", path, "-f", "lavfi", "-i", "anoisesrc=color=brown:amplitude=0.02"]
    chain = "[1:a]lowpass=f=180,volume=0.5[h]"
    mixin = "[0:a][h]"
    n = 2
    if lib and os.path.exists(birds):
        inputs += ["-stream_loop", "-1", "-i", birds]
        chain += ";[2:a]lowpass=f=1800,volume=0.06[b]"
        mixin += "[b]"
        n = 3
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex",
                    f"{chain};{mixin}amix=inputs={n}:duration=first:normalize=0[a]", "-map", "0:v", "-map", "[a]",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", tmp], check=True)
    os.replace(tmp, path)


if __name__ == "__main__":
    if os.environ.get("PREVIEW"):
        preview(sys.argv[1], times=(0, 1, 2, 7))
        sys.exit()
    out = sys.argv[1] if len(sys.argv) > 1 else "build_it_anyway_chibi.mp4"
    D.render(out, shots(), LINES, VOICE, overlay)
    add_ambience(out, sys.argv[2] if len(sys.argv) > 2 else None)
