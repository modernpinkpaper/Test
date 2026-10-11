"""Comedy beats for the stick-people skits: emotion symbols over heads, head turns and double takes, camera moves
(snap zoom, whip pan, freeze frame) and the sounds that sell a joke. Used by work2.py; meant for every skit.

Timeline: a scene is a list of beats; `plan(beats, line_len)` turns them into named times, e.g.
    [("act", 1.2, "setup"), ("line", "friday", .2), ("act", .8, "react"), ("line", "huh", .3), ("act", 1.0, "button")]
gives marks["setup"] = (0, 1.2), marks["friday"] = (1.2, 1.2 + its length), ...
"""
import math

import numpy as np

from toon import curve, ellipse, poly, rgb, rrect, text

SR = 24000


def ease(t):
    return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, t)))


def pop(t, d=0.25):
    """0 -> 1 with a little overshoot (for things that pop in)."""
    if t <= 0:
        return 0.0
    t = min(1.0, t / d)
    return 1 - (1 - t) ** 3 * math.cos(t * 4.5)


def plan(beats, line_len):
    m, s = {}, 0.0
    for b in beats:
        if b[0] == "act":
            if len(b) > 2:
                m[b[2]] = (s, s + b[1])
            s += b[1]
        else:
            n = line_len(b[1])
            m[b[1]] = (s, s + n)
            s += n + b[2]
    m["end"] = s
    return m


def at(m, spec):
    """'key' = start of key, 'key>' = its end, 'key+0.4' / 'key>+0.4' = plus an offset; numbers pass through."""
    if not isinstance(spec, str):
        return spec
    key, off = spec, 0.0
    if "+" in spec:
        key, o = spec.split("+")
        off = float(o)
    end = key.endswith(">")
    key = key.rstrip(">")
    return (m[key][1] if end else m[key][0]) + off


def between(t, m, a, b):
    return at(m, a) <= t < at(m, b)


# ------------------------------------------------------------------ emotion symbols
FONT = None


def emote(ctx, kind, head, R, k, t=0.0, font=None):
    """Draw an emotion symbol above-right of a head (head centre, radius), popping in with k (0..1)."""
    if k <= 0.02:
        return
    x, y = head[0] + R * 0.85, head[1] - R * 1.15
    s = k
    if kind in ("?", "!", "?!"):
        text(ctx, kind, x, y + 10 * math.sin(t * 6), 110 * s, font, col="#ffffff", outline=(0.1, 0.08, 0.1), ow=12)
    elif kind == "...":
        for i in range(3):
            if (t * 3) % 4 > i:
                ellipse(ctx, x - 40 + i * 40, y + 20, 13 * s, 13 * s, fill=(0.1, 0.08, 0.1), line=None)
    elif kind == "sweat":
        cx, cy = head[0] - R * 0.95, head[1] - R * 0.45 + 30 * ((t * 1.2) % 1)
        ctx.move_to(cx, cy - 40 * s)
        ctx.curve_to(cx + 26 * s, cy, cx + 20 * s, cy + 22 * s, cx, cy + 22 * s)
        ctx.curve_to(cx - 20 * s, cy + 22 * s, cx - 26 * s, cy, cx, cy - 40 * s)
        ctx.set_source_rgb(*rgb("#8fd3ff"))
        ctx.fill_preserve()
        ctx.set_source_rgb(0.1, 0.08, 0.1)
        ctx.set_line_width(5)
        ctx.stroke()
    elif kind == "anger":                                            # the red "vein" cross
        cx, cy = head[0] + R * 0.55, head[1] - R * 0.75
        for a in (0, 1, 2, 3):
            ang = a * math.pi / 2 + math.pi / 4
            ctx.move_to(cx + 10 * s * math.cos(ang), cy + 10 * s * math.sin(ang))
            ctx.curve_to(cx + 30 * s * math.cos(ang + .5), cy + 30 * s * math.sin(ang + .5),
                         cx + 30 * s * math.cos(ang - .5), cy + 30 * s * math.sin(ang - .5),
                         cx + 10 * s * math.cos(ang + .8), cy + 10 * s * math.sin(ang + .8))
        ctx.set_source_rgb(*rgb("#e53935"))
        ctx.set_line_width(9 * s)
        ctx.stroke()
    elif kind == "zzz":
        for i in range(3):
            ph = (t * .8 + i / 3) % 1
            text(ctx, "z", x - 40 + ph * 70, y + 40 - ph * 90, (40 + 30 * ph) * s, font, col="#ffffff",
                 outline=(0.1, 0.08, 0.1), ow=8)
    elif kind == "sparkle":
        for i, (dx, dy) in enumerate(((-50, 0), (30, -40), (60, 30))):
            r = (18 + 10 * math.sin(t * 8 + i)) * s
            cx, cy = x + dx, y + dy
            poly(ctx, [(cx, cy - r * 2), (cx + r * .4, cy - r * .4), (cx + r * 2, cy), (cx + r * .4, cy + r * .4),
                       (cx, cy + r * 2), (cx - r * .4, cy + r * .4), (cx - r * 2, cy), (cx - r * .4, cy - r * .4)],
                 fill="#ffd45e", w=4)
    elif kind == "gloom":                                            # blue lines of doom under the brow
        for i in range(4):
            poly(ctx, [(head[0] - R * .6 + i * R * .4, head[1] - R * .95), (head[0] - R * .6 + i * R * .4, head[1] - R * .4)],
                 line="#5b6bbf", w=6 * s, close=False)


# ------------------------------------------------------------------ camera helpers
def whip_blur(frame_bgra, amount):
    """Horizontal motion blur for a whip pan (numpy BGRA frame, amount 0..1)."""
    if amount <= 0.02:
        return frame_bgra
    n = int(6 + 40 * amount)
    f = frame_bgra.astype(np.float32)
    acc = np.zeros_like(f)
    for i in range(n):
        acc += np.roll(f, int((i - n / 2) * 4), axis=1)
    return (acc / n).astype(np.uint8)


def freeze_tint(frame_bgra, k):
    """Freeze frame look: desaturate + slight warm tint."""
    if k <= 0:
        return frame_bgra
    f = frame_bgra.astype(np.float32)
    g = f[..., :3].mean(2, keepdims=True)
    f[..., :3] = f[..., :3] * (1 - .75 * k) + g * .75 * k
    f[..., 2] = np.clip(f[..., 2] + 18 * k, 0, 255)
    return f.astype(np.uint8)


# ------------------------------------------------------------------ sounds
def _t(d):
    return np.arange(int(d * SR)) / SR


def sfx(name, rng=None):
    rng = rng or np.random.default_rng(1)
    if name == "scratch":                                            # record scratch
        d = _t(.45)
        f = 700 + 900 * np.sin(2 * np.pi * 6 * d)
        return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-d / .3) * .12 +
                rng.normal(0, 1, len(d)) * .05 * np.exp(-d / .2)).astype(np.float32)
    if name == "whoosh":
        d = _t(.3)
        s = rng.normal(0, 1, len(d)) * np.sin(np.pi * d / .3) ** 2
        return (np.convolve(s, np.ones(18) / 18, "same") * .35).astype(np.float32)
    if name == "pop":
        d = _t(.12)
        return (np.sin(2 * np.pi * (500 + 2500 * d) * d) * np.exp(-d / .03) * .25).astype(np.float32)
    if name == "boing":
        d = _t(.45)
        return (np.sin(2 * np.pi * (180 * d + 700 * d * d)) * np.exp(-d / .2) * .2).astype(np.float32)
    if name == "dundun":                                            # dramatic "dun dun"
        out = np.zeros(int(1.2 * SR), np.float32)
        for i, (f, st) in enumerate(((110, 0), (98, .45))):
            d = _t(.7)
            s = (np.sin(2 * np.pi * f * d) + .5 * np.sin(2 * np.pi * 2 * f * d) + .3 * np.sign(np.sin(2 * np.pi * f * d)))
            seg = (s * np.exp(-d / .35) * .16).astype(np.float32)
            j = int(st * SR)
            out[j:j + len(seg)] += seg[:len(out) - j]
        return out
    if name == "brightsting":                                       # cheerful ta-da
        out = np.zeros(int(.9 * SR), np.float32)
        for f, st in ((523, 0), (659, .08), (784, .16), (1046, .24)):
            d = _t(.6)
            seg = (np.sin(2 * np.pi * f * d) * np.exp(-d / .25) * .07).astype(np.float32)
            j = int(st * SR)
            out[j:j + len(seg)] += seg[:len(out) - j]
        return out
    if name == "gulp":
        d = _t(.25)
        return (np.sin(2 * np.pi * (300 - 500 * d) * d) * np.sin(np.pi * d / .25) * .25).astype(np.float32)
    if name == "squeak":                                            # office chair
        d = _t(.3)
        return (np.sin(2 * np.pi * (900 + 400 * np.sin(2 * np.pi * 8 * d)) * d) * np.sin(np.pi * d / .3) * .05).astype(np.float32)
    if name == "ding":
        d = _t(.5)
        return ((np.sin(2 * np.pi * 1568 * d) + .5 * np.sin(2 * np.pi * 2352 * d)) * np.exp(-d / .15) * .08).astype(np.float32)
    if name == "crickets":
        d = _t(2.0)
        return (np.sin(2 * np.pi * 4200 * d) * (((d * 14) % 1) < .35) * (((d / .9) % 1) < .5) * .05).astype(np.float32)
    if name == "tick":
        d = _t(.05)
        return (rng.normal(0, 1, len(d)) * np.exp(-d / .006) * .3).astype(np.float32)
    if name == "sniff":
        d = _t(.35)
        return (rng.normal(0, 1, len(d)) * np.sin(np.pi * d / .35) ** 2 * .06).astype(np.float32)
    if name == "slide_down":                                        # slide whistle down (sad)
        d = _t(.8)
        return (np.sin(2 * np.pi * np.cumsum(1400 - 1100 * d / .8) / SR) * np.sin(np.pi * d / .8) * .08).astype(np.float32)
    if name == "notif":
        d = _t(.25)
        return ((np.sin(2 * np.pi * 1318 * d) * (d < .1) + np.sin(2 * np.pi * 1760 * d) * (d >= .1)) * np.exp(-d / .12) * .07).astype(np.float32)
    raise KeyError(name)
