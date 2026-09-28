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

C = {   # sampled from the reference
    "liner": "#3d180d",
    "iris_top": "#3a160e",
    "iris_mid": "#5a2c22",
    "iris_low": "#74402b",
    "iris_rim": "#250900",
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


def eye(side, state="open"):
    e = M[f"{side}_eye"]
    cx, cy, r = e["circle"]
    ix, iy, irx, iry = e["iris"]
    if side == "right":
        ix += 2.0          # the fitted centre sits ~2 px left of the drawn one (white crescent is wider in the reference)
    gid = f"{side}_eye"
    liner_pts = e["liner"]
    if state == "closed":
        o = -1 if side == "right" else 1
        pts = [(cx - r * 1.05, cy + 2), (cx - r * .5, cy + r * .28), (cx, cy + r * .36), (cx + r * .5, cy + r * .28),
               (cx + r * 1.05, cy + 2)]
        tail = (cx + o * (r + 9), cy - 6)
        pts = pts + [tail] if o > 0 else [tail] + pts
        return (f'<g id="{gid}"><path d="{smooth(pts, False)}" fill="none" stroke="{C["liner"]}" stroke-width="5" '
                f'stroke-linecap="round" stroke-linejoin="round"/></g>')
    clip = f'<clipPath id="clip_{gid}"><circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}"/></clipPath>'
    white = f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" fill="{C["white"]}"/>'
    star_c = (ix + STAR_OFFSET[0], iy + STAR_OFFSET[1])
    dot = (ix + DOT_OFFSET[0], iy + DOT_OFFSET[1])
    iris_clip = f'<clipPath id="iclip_{gid}"><ellipse cx="{f(ix)}" cy="{f(iy)}" rx="{f(irx)}" ry="{f(iry)}"/></clipPath>'
    iris = (f'<g clip-path="url(#clip_{gid})">'
            f'<ellipse cx="{f(ix)}" cy="{f(iy)}" rx="{f(irx)}" ry="{f(iry)}" fill="url(#iris)"/>'
            # soft lighter-brown band along the bottom of the iris, a darker pupil, then the rim
            f'<g clip-path="url(#iclip_{gid})">'
            f'<ellipse cx="{f(ix + 1)}" cy="{f(iy + iry * .78)}" rx="{f(irx * 1.05)}" ry="{f(iry * .5)}" fill="url(#irisBand)"/>'
            f'<circle cx="{f(ix + PUPIL_OFFSET[0])}" cy="{f(iy + PUPIL_OFFSET[1])}" r="{f(PUPIL_R * 1.35)}" fill="url(#pupil)"/></g>'
            f'<ellipse cx="{f(ix)}" cy="{f(iy)}" rx="{f(irx)}" ry="{f(iry)}" fill="none" stroke="{C["iris_rim"]}" stroke-width="1.8"/>'
            + star(star_c, STAR_RX, STAR_RY) +
            f'<circle cx="{f(dot[0])}" cy="{f(dot[1])}" r="6" fill="{C["shine_ring"]}" opacity=".55"/>'
            f'<circle cx="{f(dot[0])}" cy="{f(dot[1])}" r="3.2" fill="{C["white"]}"/>'
            # the thick lash line also covers the top of the eye, inside the circle
            f'<ellipse cx="{f(cx)}" cy="{f(cy - r)}" rx="{f(r * 1.02)}" ry="{f(r * .3)}" fill="{C["liner"]}"/></g>')
    liner = (f'<path d="{smooth(liner_pts, True, corners=sharp_points(liner_pts))}" fill="{C["liner"]}" '
             f'stroke="{C["liner"]}" stroke-width="1.2" stroke-linejoin="round"/>')
    return f'<g id="{gid}">{clip}{iris_clip}{white}{iris}{liner}</g>'


FACE_MID_X = (M["right_eye"]["circle"][0] + M["left_eye"]["circle"][0]) / 2


def brow(side, lift=0.0):
    """Both brows use the traced shape of her left brow (viewer's right); the other side is its mirror."""
    src = M["left_brow"]
    pts = src if side == "left" else [(2 * FACE_MID_X - x, y) for x, y in src[::-1]]
    pts = [(x, y - lift) for x, y in pts]
    return f'<g id="{side}_eyebrow"><path d="{smooth(pts, True, corners=sharp_points(pts, 70))}" fill="{C["brow"]}" stroke="{C["brow"]}" stroke-width="1.6" stroke-linejoin="round"/></g>'


DEFS = f"""<linearGradient id="iris" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{C['iris_top']}"/>
  <stop offset="1" stop-color="#4a2116"/></linearGradient>
  <radialGradient id="irisBand"><stop offset=".35" stop-color="{C['iris_band']}" stop-opacity=".95"/>
    <stop offset="1" stop-color="{C['iris_band']}" stop-opacity="0"/></radialGradient>
  <radialGradient id="pupil"><stop offset=".45" stop-color="{C['pupil']}" stop-opacity=".9"/>
    <stop offset="1" stop-color="{C['pupil']}" stop-opacity="0"/></radialGradient>"""


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
