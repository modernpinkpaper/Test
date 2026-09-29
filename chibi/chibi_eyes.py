"""Chibi eyes and eyebrows, built from shapes measured on the reference sheet (see measure_face.py).

Coordinates are pixels of the reference sheet (left girl). Each eye:
  - eye white = the fitted circle
  - iris = tall oval, clipped to the circle; darker at the top, warm brown lower down
  - lash line (with its lashes) = the traced outline, drawn as smooth curves with sharp lash tips
  - star sparkle + small round shine
Each brow = its traced outline as one smooth closed curve.
"""
import json
import math
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
M = json.load(open(os.path.join(HERE, "ref", "measured_eyes.json")))
FACE_MID_X = (M["right_eye"]["circle"][0] + M["left_eye"]["circle"][0]) / 2
MAX_LOOK = (7.0, 3.0)
IRIS_INWARD = 7.5          # iris shift toward the nose (old-reference px)      # how far the irises can move inside the eye (x, y) when she glances around


def master_eye(side):
    """Both eyes come from the cleanly traced one (her left eye = viewer's right); her right eye is its mirror."""
    e = M["left_eye"]
    cx, cy, r = e["circle"]
    ix, iy, irx, iry = e["iris"]
    # as in the reference: a big iris that nearly fills the eye, sitting a little toward the nose,
    # so the white shows as a crescent on the outer side
    irx, iry, iy = 24.5, 29.5, cy + 5.5
    ix = ix - IRIS_INWARD
    liner = e["liner"]
    if side == "right":
        cx, ix = 2 * FACE_MID_X - cx, 2 * FACE_MID_X - ix
        liner = [(2 * FACE_MID_X - x, y) for x, y in liner[::-1]]
    return (cx, cy, r), (ix, iy, irx, iry), liner

C = {   # sampled from the reference
    "liner": "#3d180d",
    "iris_top": "#3a160e",
    "iris_mid": "#5a2c22",
    "iris_low": "#74402b",
    "iris_rim": "#1f0a04",
    "iris_band": "#7a4431",
    "pupil": "#240b05",
    "shine_ring": "#d9a89b",
    "white": "#fffdfc",
    "lid_shadow": "#ead8d8",
    "brow": "#452a1f",
}
# measured on the reference, relative to the iris centre: star sparkle, small shine, darker pupil
STAR_OFFSET, STAR_RX, STAR_RY = (9.3, -4.2), 9.8, 11.6
DOT_OFFSET = (-10.1, 18.1)
PUPIL_OFFSET, PUPIL_R = (-0.5, 7.6), 9.5


def f(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def smooth(pts, closed=True, corners=(), t=1 / 6):
    P = [np.array(p, float) for p in pts]
    n = len(P)
    d = [f"M{f(P[0][0])},{f(P[0][1])}"]
    for i in range(n if closed else n - 1):
        j = (i + 1) % n
        p0 = P[i - 1] if (closed or i > 0) else P[i]
        p3 = P[(i + 2) % n] if (closed or i + 2 < n) else P[j]
        c1 = P[i] + (P[j] - P[i]) / 3 if i in corners else P[i] + (P[j] - p0) * t
        c2 = P[j] + (P[i] - P[j]) / 3 if j in corners else P[j] - (p3 - P[i]) * t
        d.append(f"C{f(c1[0])},{f(c1[1])} {f(c2[0])},{f(c2[1])} {f(P[j][0])},{f(P[j][1])}")
    return " ".join(d) + (" Z" if closed else "")


def sharp_points(pts, max_angle=95):
    """Indices where the outline turns sharply (lash tips, brow tail) -> keep them as corners."""
    P = np.array(pts, float)
    out = []
    for i in range(len(P)):
        a, b = P[i - 1] - P[i], P[(i + 1) % len(P)] - P[i]
        cosang = a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9)
        if math.degrees(math.acos(np.clip(cosang, -1, 1))) < max_angle:
            out.append(i)
    return out


def star(c, rx, ry=None):
    """Chunky 4-point sparkle: concave sides (quadratic curves pulled toward the centre), rounded tips."""
    x, y = c
    ry = ry or rx
    tips = [(x, y - ry), (x + rx, y), (x, y + ry), (x - rx, y)]
    k = .33
    d = []
    for i in range(4):
        a, b = tips[i], tips[(i + 1) % 4]
        ctrl = (x + (a[0] + b[0] - 2 * x) * k, y + (a[1] + b[1] - 2 * y) * k)
        d.append((a, ctrl, b))
    path = f"M{f(d[0][0][0])},{f(d[0][0][1])} " + " ".join(f"Q{f(cx)},{f(cy)} {f(bx)},{f(by)}" for _, (cx, cy), (bx, by) in d) + " Z"
    return (f'<path d="{path}" fill="{C["white"]}" stroke="{C["white"]}" stroke-width="3.4" '
            f'stroke-linejoin="round"/>')


# measured on the reference (white and iris edges, row by row): eye-white circle and iris per eye.
# Both irises sit toward the viewer's right (she glances slightly that way), so the white shows on the left.
LINER_FIT = {"right": (-1.0, -3.0, 1.0), "left": (1.0, -1.5, 1.04)}   # lash line shift x, y and scale (fitted)
EYE_MEASURED = {
    "right": dict(globe=(126.0, 414.0, 32.2), iris=(131.4, 413.0, 24.7, 33.5), tilt=4.0),
    "left": dict(globe=(250.2, 414.5, 32.6), iris=(251.4, 413.0, 25.1, 35.5), tilt=4.0),
}


def _taper(pts, wmax, colour, n=24, power=0.6):
    """A stroke that is widest in the middle and ends in fine points."""
    P = np.array(pts, float)
    seg = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    t = np.linspace(0, seg[-1], n)
    Q = np.stack([np.interp(t, seg, P[:, 0]), np.interp(t, seg, P[:, 1])], 1)
    w = wmax * np.sin(np.linspace(0, np.pi, n)) ** power
    d = np.gradient(Q, axis=0)
    nrm = np.stack([-d[:, 1], d[:, 0]], 1) / (np.linalg.norm(d, axis=1, keepdims=True) + 1e-9)
    ring = np.vstack([Q + nrm * w[:, None] / 2, (Q - nrm * w[:, None] / 2)[::-1]])
    return f'<path d="{smooth([tuple(p) for p in ring], True)}" fill="{colour}"/>'


def closed_eye(side, cx, cy, r, happy=False):
    """Closed eye as in her expressions sheet: a thick lash line (a U for calm, an arch for happy) whose outer end
    flicks up into two lashes."""
    o = 1 if side == "left" else -1                    # outer side of this eye (her left eye's outer side is +x)
    bend = -0.42 if happy else 0.30                    # arch (happy) or a downward curve (calm)
    base = cy + (r * 0.18 if happy else 0.0)
    xs = np.linspace(-1.02, 1.02, 9)
    line = [(cx + x * r, base + bend * r * (1 - x * x)) for x in xs]
    line = line if o > 0 else line[::-1]               # run from the inner end to the outer end
    ex, ey = line[-1]
    g = _taper(line + [(ex + o * 6, ey - 4)], 6.2, C["liner"], power=0.35)
    for dx, dy, w in ((o * 13, -9, 3.6), (o * 12, -1, 3.2)):   # two lashes flicking out at the outer end
        g += _taper([(ex - o * 3, ey + 1), (ex + dx * .55, ey + dy * .6), (ex + dx, ey + dy)], w, C["liner"])
    return g


LID_SKIN = "#fecdab"      # her face skin (chibi_face.C["skin"])


def half_lid(side, cx, cy, r):
    """Half-closed (smug / unimpressed) lid: skin down to a flat lid line across the top of the eye, with the lash
    line along it and a small wing at the outer end."""
    o = 1 if side == "left" else -1
    y = cy - r * 0.12
    skin = LID_SKIN
    cover = (f'<clipPath id="lid_{side}"><circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r + 1)}"/></clipPath>'
             f'<rect x="{f(cx - r - 6)}" y="{f(cy - r - 12)}" width="{f(2 * r + 12)}" height="{f(y - (cy - r - 12))}" '
             f'fill="{skin}" clip-path="url(#lid_{side})"/>')
    w = math.sqrt(max(r * r - (y - cy) ** 2, 0))
    line = [(cx - o * (w + 2), y + 3), (cx - o * w * .4, y + 0.5), (cx + o * w * .4, y + 0.5), (cx + o * (w + 3), y + 2),
            (cx + o * (w + 12), y - 6)]
    ex, ey = line[-2]
    lashes = "".join(_taper([(ex - o * 3, ey), (ex + o * dx * .55, ey + dy * .6), (ex + o * dx, ey + dy)], w, C["liner"])
                     for dx, dy, w in ((13, -10, 3.6), (14, -2, 3.2)))
    return cover + _taper(line, 6.0, C["liner"], power=0.3) + lashes


def eye(side, state="open", look=(0.0, 0.0)):
    """state: open | half | closed | happy.  look: (-1..1, -1..1) moves both irises together (left/right, up/down);
    look y down to about -4 rolls the eyes up."""
    (ocx, ocy, orr), _, liner_pts = master_eye(side)
    m = EYE_MEASURED[side]
    (cx, cy, r), (ix, iy, irx, iry) = m["globe"], m["iris"]
    tilt = m.get("tilt", 0.0)
    # lash line: traced around the old eye circle -> moved and scaled onto the measured one
    k = r / orr
    ldx, ldy, lk = LINER_FIT[side]
    liner_pts = [(cx + (x - ocx) * k * lk + ldx, cy + (y - ocy) * k * lk + ldy) for x, y in liner_pts]
    ix, iy = ix + look[0] * MAX_LOOK[0], iy + look[1] * MAX_LOOK[1]
    gid = f"{side}_eye"
    if state in ("closed", "happy"):
        return f'<g id="{gid}">{closed_eye(side, cx, cy, r, happy=state == "happy")}</g>'
    clip = f'<clipPath id="clip_{gid}"><circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}"/></clipPath>'
    white = f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" fill="{C["white"]}"/>'
    star_c = (ix + STAR_OFFSET[0], iy + STAR_OFFSET[1])
    dot = (ix + DOT_OFFSET[0], iy + DOT_OFFSET[1])
    iris_clip = f'<clipPath id="iclip_{gid}"><ellipse cx="{f(ix)}" cy="{f(iy)}" rx="{f(irx)}" ry="{f(iry)}" transform="rotate({f(tilt)} {f(ix)} {f(iy)})"/></clipPath>'
    iris = (f'<g clip-path="url(#clip_{gid})">'
            f'<ellipse cx="{f(ix)}" cy="{f(iy)}" rx="{f(irx)}" ry="{f(iry)}" transform="rotate({f(tilt)} {f(ix)} {f(iy)})" fill="url(#iris)"/>'
            # soft lighter-brown band along the bottom of the iris, a darker pupil, then the rim
            f'<g clip-path="url(#iclip_{gid})">'
            f'<ellipse cx="{f(ix + 1)}" cy="{f(iy + iry * .78)}" rx="{f(irx * 1.05)}" ry="{f(iry * .5)}" fill="url(#irisBand)"/>'
            f'<circle cx="{f(ix + PUPIL_OFFSET[0])}" cy="{f(iy + PUPIL_OFFSET[1])}" r="{f(PUPIL_R * 1.35)}" fill="url(#pupil)"/></g>'
            f'<ellipse cx="{f(ix)}" cy="{f(iy)}" rx="{f(irx)}" ry="{f(iry)}" transform="rotate({f(tilt)} {f(ix)} {f(iy)})" fill="none" stroke="{C["iris_rim"]}" stroke-width="2.8"/>'
            + star(star_c, STAR_RX, STAR_RY) +
            f'<circle cx="{f(dot[0])}" cy="{f(dot[1])}" r="6" fill="{C["shine_ring"]}" opacity=".55"/>'
            f'<circle cx="{f(dot[0])}" cy="{f(dot[1])}" r="3.2" fill="{C["white"]}"/>'
            # the thick lash line also covers the top of the eye, inside the circle
            f'<ellipse cx="{f(cx)}" cy="{f(cy - r)}" rx="{f(r * 1.02)}" ry="{f(r * .3)}" fill="{C["liner"]}"/></g>')
    liner = (f'<path d="{smooth(liner_pts, True, corners=sharp_points(liner_pts))}" fill="{C["liner"]}" '
             f'stroke="{C["liner"]}" stroke-width="1.2" stroke-linejoin="round"/>')
    # the lash line sits on the top half of the eye only (the trace also caught a bit of the lower outline)
    top_clip = (f'<clipPath id="tclip_{gid}"><rect x="{f(cx - r * 2)}" y="{f(cy - r * 3)}" width="{f(r * 4)}" '
                f'height="{f(r * 3.1)}"/></clipPath>')
    # the top of the white circle hides under the lash line (no white sliver above it)
    a0, a1 = math.radians(200), math.radians(335)
    top_arc = (f'<path d="M{f(cx + r * math.cos(a0))},{f(cy + r * math.sin(a0))} A{f(r)},{f(r)} 0 0,1 '
               f'{f(cx + r * math.cos(a1))},{f(cy + r * math.sin(a1))}" fill="none" stroke="{C["liner"]}" stroke-width="3"/>')
    if state == "half":         # the lid (with its own lash line) replaces the upper lash line
        return f'<g id="{gid}">{clip}{iris_clip}{white}{iris}{half_lid(side, cx, cy, r)}</g>'
    return (f'<g id="{gid}">{clip}{iris_clip}{top_clip}{white}{iris}'
            f'<g clip-path="url(#tclip_{gid})">{top_arc}{liner}</g></g>')


def brow(side, lift=0.0, angle=0.0):
    """Both brows use the traced shape of her left brow (viewer's right); the other side is its mirror.
    lift: up (+) / down; angle: degrees the inner end goes down (+, angry) or up (-, sad / worried)."""
    src = M["left_brow"]
    pts = src if side == "left" else [(2 * FACE_MID_X - x, y) for x, y in src[::-1]]
    P = np.array(pts, float)
    c = P.mean(0)
    a = math.radians(angle) * (1 if side == "right" else -1)     # her right brow's inner end is at +x
    R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    pts = [(x, y - lift) for x, y in (P - c) @ R.T + c]
    return f'<g id="{side}_eyebrow"><path d="{smooth(pts, True, corners=sharp_points(pts, 70))}" fill="{C["brow"]}" stroke="{C["brow"]}" stroke-width="1.6" stroke-linejoin="round"/></g>'


DEFS = f"""<linearGradient id="iris" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{C['iris_top']}"/>
  <stop offset="1" stop-color="#4a2116"/></linearGradient>
  <radialGradient id="irisBand"><stop offset=".35" stop-color="{C['iris_band']}" stop-opacity=".95"/>
    <stop offset="1" stop-color="{C['iris_band']}" stop-opacity="0"/></radialGradient>
  <radialGradient id="pupil"><stop offset=".45" stop-color="{C['pupil']}" stop-opacity=".9"/>
    <stop offset="1" stop-color="{C['pupil']}" stop-opacity="0"/></radialGradient>"""


def demo_strip(path):
    """Four small frames: straight ahead, glance left, glance right, blink."""
    import cairosvg
    box = (70, 330, 320, 460)
    frames = [dict(), dict(look=(-1, 0)), dict(look=(1, 0)), dict(state="closed")]
    w, h = box[2] - box[0], box[3] - box[1]
    gap = 12
    body = "".join(f'<g transform="translate({i * (w + gap)} 0)"><rect x="{box[0]}" y="{box[1]}" width="{w}" height="{h}" fill="#fecdab"/>'
                   + eye("right", **fr) + eye("left", **fr) + brow("right") + brow("left") + "</g>"
                   for i, fr in enumerate(frames))
    W = w * 4 + gap * 3
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W * 2}" height="{h * 2}" '
           f'viewBox="{box[0]} {box[1]} {W} {h}"><defs>{DEFS}</defs><rect x="{box[0]}" y="{box[1]}" width="{W}" '
           f'height="{h}" fill="#ffffff"/>{body}</svg>')
    cairosvg.svg2png(bytestring=svg.encode(), write_to=path)


if __name__ == "__main__":
    import sys
    import cairosvg
    from PIL import Image
    out, ref_path = sys.argv[1], sys.argv[2]
    box = (70, 320, 320, 470)
    sc = 4
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{(box[2] - box[0]) * sc}" height="{(box[3] - box[1]) * sc}" '
           f'viewBox="{box[0]} {box[1]} {box[2] - box[0]} {box[3] - box[1]}"><defs>{DEFS}</defs>'
           f'<rect x="0" y="0" width="2000" height="2000" fill="#fecdab"/>'
           + eye("right") + eye("left") + brow("right") + brow("left") + "</svg>")
    cairosvg.svg2png(bytestring=svg.encode(), write_to=out + ".mine.png")
    ref = Image.open(ref_path).convert("RGB").crop(box).resize(((box[2] - box[0]) * sc, (box[3] - box[1]) * sc), Image.LANCZOS)
    mine = Image.open(out + ".mine.png").convert("RGB")
    both = Image.new("RGB", (ref.width, ref.height * 2 + 10), "white")
    both.paste(ref, (0, 0))
    both.paste(mine, (0, ref.height + 10))
    both.save(out)
    demo_strip(out.replace(".png", "_looks.png"))
