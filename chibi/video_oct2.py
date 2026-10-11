"""'What did I even do today' (Oct 2): a talk-to-myself productivity vlog with her chibi girl (1080x1920).

    python chibi/video_oct2.py out.mp4        (PREVIEW=1 for framing stills without the voice step)

Made from her MT Log for Oct 2 (see oct2_lines.py). Everything on the monitor is a mockup: no real orders, names,
keys or numbers. Rig, captions and sound come from video_day.py; the office, desk and monitor from video_robot.py.
"""
import math
import os
import sys

from PIL import ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, "..", "skits")]
import beats                                                      # noqa: E402
import chibi_props as P                                           # noqa: E402
import video_day as D                                             # noqa: E402
import video_robot as R                                           # noqa: E402
from oct2_lines import LINES, VOICE                               # noqa: E402
from toon import ellipse, poly, rgb, rrect, text                  # noqa: E402

W, H = D.W, D.H
F800, F600 = D.F800, D.F600
HX = R.HX
ease, lerp, stand, blend = D.ease, D.lerp, D.stand, D.blend
GREEN, RED, INK, SOFT = "#1b7a3a", "#c62828", "#2b2440", "#6d6680"


# ------------------------------------------------------------------ monitor screens (x, y, w, h = the wall monitor)
def bar(ctx, x, y, w, title, col, ink=(1, 1, 1)):
    rrect(ctx, x, y, w, 60, 0, fill=col, line=None)
    text(ctx, title, x + w / 2, y + 30, 28, F800, col=ink)


def scr_title(ctx, t, x, y, w, h):
    bar(ctx, x, y, w, "OCT 2", "#ff8fb0")
    text(ctx, "what did I", x + w / 2, y + 140, 44, F800, col=INK)
    text(ctx, "even do today?", x + w / 2, y + 200, 44, F800, col=INK)
    for i in range(3):
        if (t * 2) % 4 > i:
            ellipse(ctx, x + w / 2 - 40 + i * 40, y + 270, 10, 10, fill=SOFT, line=None)


def scr_install(ctx, t, x, y, w, h):
    bar(ctx, x, y, w, "MT LOG  (new version)", "#7ec8ff")
    k = ease((t - 0.3) / 2.2)
    rrect(ctx, x + 40, y + 110, w - 80, 40, 20, fill="#efeaf7", w=5)
    rrect(ctx, x + 44, y + 114, max(1, (w - 88) * k), 32, 16, fill="#8be0a4", line=None)
    text(ctx, "installing..." if k < 1 else "logging is ON", x + w / 2, y + 190, 30, F800, col=GREEN if k >= 1 else INK)
    R._pop_row(ctx, t, 2.9, x, y + 240, w, "InDesign logger", "startup", good=True)


def scr_cards(ctx, t, x, y, w, h):
    bar(ctx, x, y, w, "MPP ASSISTANT", "#c9a4ff")
    n = 0
    for i in range(6):
        k = beats.pop(t - 0.3 - i * 0.35, 0.25)
        if k <= 0.02:
            continue
        n += 1
        cx, cy = x + 30 + (i % 3) * 135, y + 85 + (i // 3) * 115
        rrect(ctx, cx, cy, 120 * k, 95 * k, 12, fill=("#fff3c4", "#e1ffe9", "#ffe1ec")[i % 3], w=4)
        if k > 0.6:
            rrect(ctx, cx + 14, cy + 20, 80, 12, 6, fill="#b8b2c8", line=None)
            rrect(ctx, cx + 14, cy + 44, 60, 12, 6, fill="#cfc9dd", line=None)
    text(ctx, f"{n} tips already?!", x + w / 2, y + 305, 26, F800, col=INK)


def scr_shortcut(ctx, t, x, y, w, h):
    bar(ctx, x, y, w, "MPP ASSISTANT", "#c9a4ff")
    rrect(ctx, x + 40, y + 90, w - 80, 120, 16, fill="#e1ffe9", w=4)
    text(ctx, "Nice job using", x + w / 2, y + 128, 28, F800, col=INK)
    text(ctx, "that shortcut!", x + w / 2, y + 170, 28, F800, col=INK)
    k = beats.pop(t - 2.6, 0.3)
    if k > 0.02:
        text(ctx, "...I did?", x + w / 2, y + 270, 46 * k, F800, col=RED)


SETUP = ["API key", "environment variable", "Apps Script", "PowerShell", "Google Cloud??"]


def scr_setup(ctx, t, x, y, w, h, marks=None):
    bar(ctx, x, y, w, "SETUP...", "#ffd45e", ink=INK)
    marks = marks or [0.3 + i * 0.7 for i in range(len(SETUP))]
    for i, (s, at) in enumerate(zip(SETUP, marks)):
        k = beats.pop(t - at, 0.25)
        if k <= 0.02:
            continue
        ry = y + 72 + i * 50
        rrect(ctx, x + 30, ry, (w - 60) * k, 42, 10, fill="#ffe1e1" if i == 4 else "#f4f0fb", w=3)
        if k > 0.6:
            text(ctx, s, x + 50, ry + 21, 24, F800, col=RED if i == 4 else INK, anchor="lm")
            if i == 4:
                text(ctx, "NO", x + w - 60, ry + 21, 26, F800, col=RED)


def scr_chat(ctx, t, x, y, w, h):
    bar(ctx, x, y, w, "MY CLAUDE CHAT", "#ff9f43")
    rrect(ctx, x + w - 330, y + 85, 300, 80, 18, fill="#ffe1ec", w=4)
    text(ctx, "what did I do", x + w - 180, y + 112, 24, F800, col=INK)
    text(ctx, "today?", x + w - 180, y + 142, 24, F800, col=INK)
    k = beats.pop(t - 1.2, 0.3)
    if k > 0.02:
        rrect(ctx, x + 30, y + 185, 330 * k, 100, 18, fill="#f4f0fb", w=4)
        if k > 0.6:
            for j in range(3):
                rrect(ctx, x + 52, y + 207 + j * 24, 200 + (j * 61) % 80, 12, 6, fill="#b8b2c8", line=None)
    text(ctx, "connected to my logs", x + w / 2, y + 310, 20, F600, col=SOFT)


def scr_recording(ctx, t, x, y, w, h):
    rrect(ctx, x, y, w, h, 0, fill="#2b2440", line=None)
    for i in range(4):                                                           # the orders list in the video
        rrect(ctx, x + 30, y + 40 + i * 52, w - 60, 40, 8, fill="#4a4266", line=None)
        rrect(ctx, x + 46, y + 53 + i * 52, 150 + (i * 47) % 90, 14, 7, fill="#8d84aa", line=None)
    ellipse(ctx, x + w / 2, y + 150, 46, 46, fill=(1, 1, 1), line=None)
    poly(ctx, [(x + w / 2 - 14, y + 128), (x + w / 2 - 14, y + 172), (x + w / 2 + 22, y + 150)], fill="#2b2440", line=None)
    k = (t / 9) % 1
    rrect(ctx, x + 20, y + h - 40, w - 40, 10, 5, fill="#4a4266", line=None)
    rrect(ctx, x + 20, y + h - 40, max(2, (w - 40) * k), 10, 5, fill="#ff8fb0", line=None)
    text(ctx, "orders screen recording", x + w / 2, y + h - 70, 22, F800, col=(1, 1, 1))


def scr_workflow(ctx, t, x, y, w, h, run=1.5, csv=2.4):
    bar(ctx, x, y, w, "AMAZON WORKFLOW", "#ff9f43")
    text(ctx, "unshipped orders", x + w / 2, y + 90, 26, F800, col=INK)
    text(ctx, "+ customizations", x + w / 2, y + 122, 26, F800, col=INK)
    if t < csv:
        pressed = run <= t < run + 0.25
        rrect(ctx, x + w / 2 - 110, y + 165 + (6 if pressed else 0), 220, 80, 40, fill="#ff4f8b", w=6)
        text(ctx, "RUN NOW", x + w / 2, y + 205 + (6 if pressed else 0), 34, F800, col=(1, 1, 1))
        return
    for i in range(4):                                                           # the spreadsheet comes back
        k = beats.pop(t - csv - i * 0.2, 0.25)
        if k <= 0.02:
            continue
        ry = y + 152 + i * 40
        rrect(ctx, x + 30, ry, (w - 60) * k, 34, 6, fill="#e1ffe9", w=3)
        if k > 0.6:
            rrect(ctx, x + 44, ry + 11, 90, 12, 6, fill="#8fcf9f", line=None)
            rrect(ctx, x + 160, ry + 11, 150 + (i * 37) % 60, 12, 6, fill="#b6dfc0", line=None)
            text(ctx, "✓", x + w - 52, ry + 17, 22, F800, col=GREEN)


def scr_match(ctx, t, x, y, w, h):
    bar(ctx, x, y, w, "DOES THE NAME MATCH?", "#7ec8ff")
    text(ctx, "on the invite", x + 120, y + 100, 22, F600, col=SOFT)
    text(ctx, "ship to", x + w - 120, y + 100, 22, F600, col=SOFT)
    rrect(ctx, x + 30, y + 120, 180, 50, 10, fill="#f4f0fb", w=3)
    rrect(ctx, x + w - 210, y + 120, 180, 50, 10, fill="#f4f0fb", w=3)
    for bx in (x + 50, x + w - 190):
        rrect(ctx, bx, y + 138, 120, 14, 7, fill="#b8b2c8", line=None)
    k = ease((t - 1.0) / 1.8)
    rrect(ctx, x + 40, y + 215, w - 80, 36, 18, fill="#efeaf7", w=4)
    rrect(ctx, x + 44, y + 219, max(1, (w - 88) * 0.8 * k), 28, 14, fill="#8be0a4" if k > 0.95 else "#ffd45e", line=None)
    text(ctx, f"{int(80 * k)}%", x + w / 2, y + 290, 34, F800, col=GREEN if k > 0.95 else INK)


def scr_mail(ctx, t, x, y, w, h):
    bar(ctx, x, y, w, "HER GUEST LIST", "#ff8fb0")
    n = min(18, int(t * 6))
    for i in range(n):                                                           # envelopes piling up
        ex, ey = x + 40 + (i % 6) * 64, y + 85 + (i // 6) * 62
        rrect(ctx, ex, ey, 54, 38, 4, fill="#fff6e8", w=3)
        poly(ctx, [(ex, ey), (ex + 27, ey + 20), (ex + 54, ey)], w=3, close=False)
    k = beats.pop(t - 3.6, 0.3)
    if k > 0.02:
        text(ctx, "mail each one??", x + w / 2, y + 300, 34 * k, F800, col=RED)


def scr_timing(ctx, t, x, y, w, h):
    bar(ctx, x, y, w, "TEAM TIMING", "#c9a4ff")
    vals = (0.8, 0.65, 0.9, 0.35, 0.75, 0.85)
    for i, v in enumerate(vals):
        k = ease((t - 0.2 - i * 0.12) / 0.4)
        bh = 160 * v * k
        rrect(ctx, x + 40 + i * 64, y + 260 - bh, 44, bh + 1, 6, fill=("#7ec8ff", "#ff8fb0")[i >= 3], w=4)
    poly(ctx, [(x + 25, y + 262), (x + w - 25, y + 262)], w=4, close=False)
    text(ctx, "before break      after", x + w / 2, y + 295, 22, F800, col=SOFT)


def scr_printer(ctx, t, x, y, w, h):
    bar(ctx, x, y, w, "PRINTER", "#9fb0d8")
    cx, cy = x + w / 2, y + 175
    rrect(ctx, cx - 120, cy - 40, 240, 100, 16, fill="#dfe4ee", w=6)
    rrect(ctx, cx - 80, cy - 90, 160, 55, 6, fill=(1, 1, 1), w=5)
    rrect(ctx, cx - 70, cy + 40, 140, 16, 4, fill="#2b2440", line=None)
    if (t * 2) % 1 < 0.6:
        rrect(ctx, cx - 95, cy + 75, 190, 50, 12, fill="#ffe1e1", w=4)
        text(ctx, "PAUSED", cx, cy + 100, 30, F800, col=RED)


def scr_todo(ctx, t, x, y, w, h):
    bar(ctx, x, y, w, "TOMORROW", "#8be0a4", ink=INK)
    for j, s in enumerate(("printer", "my emails", "Amazon workflow")):
        R._pop_row(ctx, t, 0.4 + j * 0.6, x, y + 90 + j * 70, w, f"{j + 1}.", s)


# ------------------------------------------------------------------ shots
def shots():
    S = []

    def add(key, lead, tail, screen, cam0, cam1, act, sfx=(), fg=None):
        S.append(dict(key=key, lead=lead, tail=tail, scene=lambda c, t, s=screen: R.office(c, t, s), sfx=list(sfx),
                      fg=fg or (lambda c, t: R.desk(c, t)), cam0=cam0, cam1=cam1, act=act))

    def wt(i, word, default=1.0):
        for w, tt in S[i].get("words", []):
            if word in w.lower():
                return tt - S[i]["t0"]
        return default

    def sit(face, pose="rest", look=None, tilt=3, steps=None, wiggle=0.0, props=None, eyes=None, after=None):
        """Seated at her desk. steps: [(time or word, pose)]; after: (word, face) switches her face on a word."""
        def f(t, d, ls, le, i=len(S)):
            if steps:
                st = [(wt(i, w, 99) if isinstance(w, str) else w, p) for w, p in steps]
                arms = D.moves(t, st, props)
            else:
                arms = blend(pose, pose, 1, props) if pose != "rest" else {}
            fc = face
            if after and t > wt(i, after[0], 99):
                fc = after[1]
            return dict(pos=stand(HX, dy=-15), face=fc, arms=arms, look=look, eyes=eyes,
                        tilt=tilt + wiggle * math.sin(t * 3))
        return f

    face_cam = lambda z, dy=0: (z, HX + 40, 760 + dy)                         # noqa: E731
    wide, mon = (1.0, 540, 950), (1.25, 700, 760)
    mug = {"right": P.mug(0.5)}

    # 1. hook: close on her, mug in hand, thinking (eyes up), the monitor asks the question
    add("hook", 0.2, 0.4, scr_title, face_cam(1.8), face_cam(1.95, -10),
        sit("neutral", "rest", look=(0.5, -3.5), tilt=-4), [("whoosh", 0.05)])
    # 2. reinstall MT Log + the InDesign logger
    add("install", 0.1, 0.3, scr_install, wide, mon, sit("neutral", "press", look=(2.5, -0.6)), [("click", 0.3), ("ding", 2.6)])
    # 3. the assistant floods her with tips
    add("cards", 0.1, 0.3, scr_cards, mon, (1.4, 720, 740),
        sit("surprised", steps=[(0, "rest"), ("tons", "cheeks")], look=(2.6, -0.8), after=("how", "surprised")),
        [("notif", 0.4), ("notif", 0.75), ("notif", 1.1), ("notif", 1.45), ("notif", 1.8), ("notif", 2.15)])
    S[-1]["fg"] = lambda c, t, i=len(S) - 1: (R.desk(c, t), beats.emote(c, "?!", (360, 520), 170, beats.pop(t - wt(i, "how"), .3), t, font=F800))
    # 4. "nice job using this shortcut" ... "I did no such thing"
    add("shortcut", 0.1, 0.45, scr_shortcut, face_cam(1.9), (1.3, 640, 760),
        sit("eye_roll", "shrug", after=("didn't", "smug"), wiggle=2), [("scratch", ("ls", 2.0))])
    # 5. the setup pile: API key, env variable, Apps Script, PowerShell, Google Cloud?? (each pops on its word)
    add("setup", 0.1, 0.35,
        lambda c, t, x, y, w, h, i=len(S): scr_setup(c, t, x, y, w, h, [wt(i, k) for k in ("api", "environment", "apps", "powershell", "cloud")]),
        (1.1, 560, 900), (1.25, 640, 820), sit("annoyed", "shrug", look=(2.4, -0.5), wiggle=3))
    S[-1]["fg"] = lambda c, t: (R.desk(c, t), beats.emote(c, "anger", (360, 520), 170, 1, t, font=F800))
    S[-1]["sfx_words"] = [("tick", "api"), ("tick", "environment"), ("tick", "apps"), ("tick", "powershell"), ("buzz", "cloud")]
    # 6. honestly? I don't even like it. I'd rather ask my Claude chat.
    add("honest", 0.1, 0.5, scr_chat, face_cam(2.0), face_cam(2.2, -10),
        sit("calm", "rest", tilt=-6, after=("rather", "smug")), [("slide_down", ("ls", 0.4))])
    # 7. the morning with the team: screen recording, auto proofs, the new Shopify script
    add("team", 0.1, 0.3, scr_recording, (1.15, 640, 830), (1.05, 600, 880), sit("neutral", "rest", look=(2.5, -0.6)),
        [("typing", 0)])
    # 8. THE WIN: Amazon workflow, Run Now, a spreadsheet with the customizations
    add("workflow", 0.1, 0.6,
        lambda c, t, x, y, w, h, i=len(S): scr_workflow(c, t, x, y, w, h, run=wt(i, "run"), csv=wt(i, "spreadsheet")),
        (1.2, 680, 780), (1.0, 540, 950),
        sit("excited", steps=[(0, "rest"), ("run", "press"), ("spreadsheet", "yay")], look=(2.4, -0.6), after=("happy", "happy")))
    S[-1]["fg"] = lambda c, t, i=len(S) - 1: (R.desk(c, t), D.confetti(c, t - wt(i, "happy"), 540, 700),
                                             R.sparkles(c, t, [(700, 800), (960, 760), (900, 600)] if t > wt(i, "spreadsheet") else []))
    S[-1]["sfx_words"] = [("click", "run"), ("brightsting", "spreadsheet"), ("chime", "happy")]
    # 9. next: does the invite name ~match the ship-to name (80%)
    add("match", 0.1, 0.4, scr_match, mon, (1.35, 700, 760), sit("smug", "chest", look=(2.5, -0.6)))
    # 10. the customer who thought we'd mail every invitation
    add("mail", 0.1, 0.5, scr_mail, face_cam(1.8), face_cam(2.05),
        sit("eye_roll", "cheeks", after=("no.", "annoyed")), [("dundun", ("le", -0.4))])
    # 11. the timing look, and the apology
    add("sorry", 0.15, 0.6, scr_timing, (1.15, 600, 850), face_cam(2.1),
        sit("sad", "chest", look=(0, 0.8), tilt=-5, after=("me.", "calm")))
    # 12. the printer was paused all day
    add("printer", 0.1, 0.45, scr_printer, mon, (1.3, 700, 770),
        sit("annoyed", "shrug", look=(2.5, -0.6), after=("cool", "smug")), [("slide_down", ("le", -0.3))])
    # 13. anyway. tomorrow. bye.
    add("bye", 0.2, 1.4, scr_todo, (1.05, 560, 930), face_cam(1.9, 20),
        sit("smug", steps=[(0, "rest"), ("bye", "peace")], after=("bye", "wink")), [("chime", ("le", 0.1))])
    return S


# ------------------------------------------------------------------ overlay
def header(frame):
    d = ImageDraw.Draw(frame)
    d.rounded_rectangle((170, 80, W - 170, 200), 34, fill=(255, 255, 255), outline=(30, 24, 30), width=6)
    d.text((W / 2, 128), "TALKING IT OUT", font=D.font(52), fill=D.PINK, anchor="mm")
    d.text((W / 2, 176), "what I did today (Oct 2)", font=D.font(30), fill=(90, 80, 90), anchor="mm")


def overlay(frame, S, s, t, T):
    header(frame)
    D.captions(frame, s, T)


def preview(out):
    """Stills of every shot (end camera) without the voice step."""
    import cairocffi as cairo
    S = shots()
    for i, s in enumerate(S):
        s.update(t0=0, d=4.0, ls=0.1, le=3.5, cues=[], words=[], who="her")
        t = 3.0
        cam = s["cam1"]
        bg = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
        ctx = cairo.Context(bg)
        D.cam_ctx(ctx, cam)
        s["scene"](ctx, t)
        bg.flush()
        from PIL import Image
        fr = Image.frombuffer("RGBA", (W, H), bytes(bg.get_data()), "raw", "BGRA", bg.get_stride(), 1).convert("RGBA")
        D.character(fr, s["act"](t, 4.0, 0.1, 3.5), cam, t, s, t)
        fg = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
        ctx = cairo.Context(fg)
        D.cam_ctx(ctx, cam)
        s["fg"](ctx, t)
        fg.flush()
        fr.alpha_composite(D.surface_rgba(fg))
        header(fr)
        fr.convert("RGB").resize((360, 640)).save(f"{out}_{i:02d}.png")


if __name__ == "__main__":
    if os.environ.get("PREVIEW"):
        preview(sys.argv[1])
        sys.exit()
    S = shots()
    D.build(S, LINES, VOICE)            # first pass: voice + word timings (cached voice, so the second pass is quick)
    R.word_sfx(S)
    D.render(sys.argv[1] if len(sys.argv) > 1 else "video_oct2.mp4", S, LINES, VOICE, overlay)
