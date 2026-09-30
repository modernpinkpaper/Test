"""Book review with her chibi girl holding the actual book (cover from Open Library), ~70 s, 1080x1920.

    python chibi/video_book.py out.mp4          # script: book_lines.py

She peeks over the book for the hook, then holds it at her chest and counts the lessons on her other hand while a
card for each lesson pops in above her. Reuses the day video's renderer (video_day.render) with its own shots,
scene (a cozy reading corner) and overlay (lesson cards + captions).
"""
import math
import os
import sys
import urllib.request

from PIL import ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import chibi_props as P                                    # noqa: E402
import video_day as D                                      # noqa: E402
from book_lines import AUTHOR, CARDS, COVER_ISBN, LINES, TITLE, VOICE   # noqa: E402
from toon import ellipse, lin, poly, rgb, rrect, text      # noqa: E402

W, H, FLOOR = D.W, D.H, D.FLOOR
INK, PINK, CREAM, GOLD, GREEN = (30, 24, 30), D.PINK, (255, 250, 242), (231, 172, 39), (27, 122, 84)


def cover_path(isbn):
    """The book's cover (Open Library covers API), cached; not committed."""
    path = os.path.join(HERE, ".cache", "covers", f"{isbn}.jpg")
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        urllib.request.urlretrieve(f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg", path)
    return path


COVER = cover_path(COVER_ISBN)
R = lambda at, d: D.reach("right", at, d, hand="c_grip")[:4]
D.POSES.update({
    "book": {"right": R((105, 610), (0, -1))},                                   # book at her chest
    "book_peek": {"right": R((105, 560), (0, -1))},                              # peeking over it
    "book_tilt": {"right": R((110, 615), (0.25, -1))},
    "c1": {"right": R((105, 610), (0, -1)), "left": (-30, -130, -10, "index_up")},
    "c2": {"right": R((105, 610), (0, -1)), "left": (-35, -130, 10, "two")},
    "c3": {"right": R((105, 610), (0, -1)), "left": (-30, -125, 0, "point")},
    "c4": {"right": R((105, 610), (0, -1)), "left": (-20, -85, -35, "palm_up")},
    "c5": {"right": R((105, 610), (0, -1)), "left": (-35, -120, 10, "stop")},
    "c_thumb": {"right": R((110, 615), (0.25, -1)), "left": (-30, -120, -70, "thumbs_up")},
    "c_peace": {"right": R((110, 615), (0.25, -1)), "left": (-35, -130, 10, "two")},
})


def reading_corner(ctx, t):
    ctx.rectangle(-3000, -3000, W + 6000, FLOOR + 3000)
    ctx.set_source(lin(ctx, 0, 0, 0, FLOOR, [(0, "#fbe9dc"), (1, "#f3cfc0")]))
    ctx.fill()
    ctx.rectangle(-3000, FLOOR, W + 6000, 3000)
    ctx.set_source_rgb(*rgb("#c98f6e"))
    ctx.fill()
    ellipse(ctx, 540, FLOOR + 60, 520, 90, fill="#f7b6cb", w=7)                       # rug
    cols = ("#e58f6a", "#6cc48a", "#7ec8ff", "#f4c542", "#c9a4ff", "#ff8fb0", "#8fd0f5")
    for bx in (-40, 760):                                                             # two bookshelves
        rrect(ctx, bx, 520, 360, 1040, 16, fill="#b98560", w=8)
        for r in range(4):
            y = 560 + r * 250
            rrect(ctx, bx + 20, y, 320, 220, 6, fill="#8a5a44", w=5)
            x = bx + 30
            i = r * 5 + (bx > 0) * 11
            while x < bx + 320:
                bw = 26 + (i * 7) % 18
                bh = 150 + (i * 13) % 55
                if (i * 5) % 9 == 0:                                                   # a leaning book
                    poly(ctx, [(x, y + 220), (x + bw, y + 220), (x + bw + 40, y + 220 - bh), (x + 40, y + 220 - bh)],
                         fill=cols[i % 7], w=4)
                    x += bw + 45
                else:
                    rrect(ctx, x, y + 220 - bh, bw, bh, 4, fill=cols[i % 7], w=4)
                    x += bw + 3
                i += 1
    poly(ctx, [(470, 250), (610, 250), (650, 380), (430, 380)], fill="#fff2c9", w=7)       # hanging lamp
    poly(ctx, [(540, -200), (540, 250)], w=5, close=False)
    ctx.set_source(D.rad(ctx, 540, 420, 420, [(0, "#fff3c4", .35), (1, "#fff3c4", 0)]))
    ctx.paint()


def act(pose_at, face="neutral", tilt=3, mouth=None, eyes=None):
    """pose_at: [(time, pose), ...]  ('ls' / 'le' strings = line start / end)."""
    def f(t, d, ls, le):
        steps = [(ls if a == "ls" else (le if a == "le" else a), p) for a, p in pose_at]
        arms = D.moves(t, steps, {"right": P.book(COVER)})
        return dict(pos=D.stand(540, dy=6 * abs(math.sin(t * 2.2))), face=face, arms=arms,
                    tilt=tilt + 1.5 * math.sin(t * 1.7), mouth=mouth, eyes=eyes)
    return f


def shots():
    S = []

    def add(key, lead, tail, cam0, cam1, fn, sfx=()):
        S.append(dict(key=key, lead=lead, tail=tail, scene=reading_corner, fg=None, cam0=cam0, cam1=cam1, act=fn,
                      sfx=list(sfx)))
    wide, close = (1.15, 540, 820), (1.75, 545, 700)
    add("hook", 0.3, 0.3, (1.9, 545, 690), (2.05, 545, 690), act([(0, "book_peek")], "annoyed", 0), [("whoosh", 0)])
    add("intro", 0.1, 0.4, wide, (1.2, 540, 810), act([(0, "book_peek"), (0.4, "book_tilt")], "happy", 4), [("ding", 0.5)])
    add("l1", 0.1, 0.3, (1.15, 540, 820), (1.22, 540, 810), act([(0, "book"), (0.2, "c1")], "calm", -3), [("ding", 0.1)])
    add("l2", 0.1, 0.3, close, (1.9, 545, 690), act([(0, "c1"), (0.2, "c2")], "surprised", 0), [("ding", 0.1), ("sting", 1.0)])
    add("l3", 0.1, 0.3, (1.15, 540, 820), (1.22, 540, 810), act([(0, "c2"), (0.2, "c3")], "smug", 5), [("ding", 0.1)])
    add("l4", 0.1, 0.3, (1.3, 540, 760), (1.4, 540, 750), act([(0, "c3"), (0.2, "c4")], "eye_roll", -4), [("ding", 0.1)])
    add("l5", 0.1, 0.3, (1.15, 540, 820), (1.22, 540, 810), act([(0, "c4"), (0.2, "c5")], "excited", 3), [("ding", 0.1)])
    add("verdict", 0.2, 0.5, close, (1.85, 545, 695), act([(0, "book"), (0.3, "c_thumb")], "smug", 5), [("chime", 0.8)])
    add("bonus", 0.1, 0.3, (1.3, 540, 780), (1.4, 540, 770), act([(0, "c_thumb"), (0.3, "book_tilt")], "calm", 3))
    add("outro", 0.1, 1.9, wide, (1.25, 540, 800), act([(0, "c_thumb"), (0.3, "c_peace")], "wink", -4))
    return S


def _wrap(d, s, f, width):
    lines, cur = [], ""
    for w in s.split():
        if cur and d.textlength(cur + " " + w, font=f) > width:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    return lines + [cur]


def overlay(frame, S, s, t, T):
    d = ImageDraw.Draw(frame)
    key = s["key"]
    k = D.ease((t - 0.1) / 0.35)
    if key == "hook":
        d.rounded_rectangle((90, 150, W - 90, 430), 36, fill=INK)
        d.text((W / 2, 225), "this book made me feel", font=D.font(52), fill=CREAM, anchor="mm")
        d.text((W / 2, 320), "PERSONALLY ATTACKED", font=D.font(int(20 + 50 * k)), fill=PINK, anchor="mm")
        d.text((W / 2, 395), "(in a good way)", font=D.font(34), fill=(200, 190, 190), anchor="mm")
    else:
        d.rounded_rectangle((170, 70, W - 170, 180), 30, fill=(255, 255, 255), outline=INK, width=5)
        d.text((W / 2, 110), "BOOK REVIEW", font=D.font(46), fill=PINK, anchor="mm")
        d.text((W / 2, 155), f"{TITLE} · {AUTHOR}", font=D.font(24), fill=(90, 80, 90), anchor="mm")
    card = CARDS.get(key)
    if card and k > 0.02:
        big, title, small = card
        y0 = 215
        d.rounded_rectangle((70, y0, W - 70, y0 + 330), 36, fill=CREAM, outline=INK, width=6)
        r = 62 * k
        if len(big) <= 2:
            d.ellipse((150 - r, y0 + 110 - r, 150 + r, y0 + 110 + r), fill=PINK)
            d.text((150, y0 + 110), big, font=D.font(70 * k + 1), fill=(255, 255, 255), anchor="mm")
            tx, tw = 240, W - 330
        else:
            d.text((W / 2, y0 + 80), big, font=D.font(96 * k + 1), fill=GOLD, anchor="mm", stroke_width=4, stroke_fill=INK)
            tx, tw = 120, W - 240
        f = D.font(50 if len(big) <= 2 else 44)
        rows = _wrap(d, title, f, tw)
        ty = y0 + (70 if len(big) <= 2 else 170)
        for i, row in enumerate(rows[:3]):
            d.text((tx if len(big) <= 2 else W / 2, ty + i * 62), row, font=f, fill=INK, anchor="lm" if len(big) <= 2 else "mm")
        if small:
            d.text((W / 2, y0 + 290), small, font=D.font(32), fill=GREEN, anchor="mm")
    D.captions(frame, s, T)
    if s is S[-1] and t > s["le"] + .1:
        kk = min(1, (t - s["le"] - .1) / .3)
        d.rounded_rectangle((120, 1560, W - 120, 1780), 40, fill=PINK)
        d.text((W / 2, 1635), "what should I read next?", font=D.font(54 * kk + 1), fill=(255, 255, 255), anchor="mm")
        d.text((W / 2, 1715), "comment a book", font=D.font(38 * kk + 1), fill=(255, 255, 255), anchor="mm")


if __name__ == "__main__":
    D.render(sys.argv[1] if len(sys.argv) > 1 else "video_book.mp4", shots(), LINES and [(k, w, l) for k, w, l in LINES],
             VOICE, overlay)
