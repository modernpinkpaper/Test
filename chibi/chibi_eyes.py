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
    "white": "#fffdfc",
    "lid_shadow": "#ead8d8",
    "brow": "#452a1f",
}
HIGHLIGHTS = {   # measured centres (star, small shine)
    "right": dict(star=(137.5, 406.0), star_r=11.0, dot=(118.0, 428.0)),
    "left": dict(star=(260.0, 406.0), star_r=11.0, dot=(239.0, 428.0)),
}


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


def star(c, r):
    x, y = c
    k = r * .38
    pts = [(x, y - r), (x + k, y - k), (x + r, y), (x + k, y + k), (x, y + r), (x - k, y + k), (x - r, y), (x - k, y - k)]
    return f'<path d="{smooth(pts, True, range(8))}" fill="{C["white"]}"/>'


def eye(side, state="open"):
    e, h = M[f"{side}_eye"], HIGHLIGHTS[side]
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
    iris = (f'<g clip-path="url(#clip_{gid})">'
            f'<ellipse cx="{f(ix)}" cy="{f(iy)}" rx="{f(irx)}" ry="{f(iry)}" fill="url(#iris)" '
            f'stroke="{C["iris_rim"]}" stroke-width="1.6"/>'
            f'<ellipse cx="{f(ix)}" cy="{f(iy - iry * .28)}" rx="{f(irx * .78)}" ry="{f(iry * .62)}" fill="{C["iris_top"]}" opacity=".55"/>'
            + star(h["star"], h["star_r"]) +
            f'<circle cx="{f(h["dot"][0])}" cy="{f(h["dot"][1])}" r="6.5" fill="{C["white"]}" opacity=".25"/>'
            f'<circle cx="{f(h["dot"][0])}" cy="{f(h["dot"][1])}" r="3.6" fill="{C["white"]}"/>'
            # the thick lash line also covers the top of the eye, inside the circle
            f'<ellipse cx="{f(cx)}" cy="{f(cy - r)}" rx="{f(r * 1.02)}" ry="{f(r * .3)}" fill="{C["liner"]}"/></g>')
    liner = (f'<path d="{smooth(liner_pts, True, corners=sharp_points(liner_pts))}" fill="{C["liner"]}" '
             f'stroke="{C["liner"]}" stroke-width="1.2" stroke-linejoin="round"/>')
    return f'<g id="{gid}">{clip}{white}{iris}{liner}</g>'


def brow(side, lift=0.0):
    pts = [(x, y - lift) for x, y in M[f"{side}_brow"]]
    return f'<g id="{side}_eyebrow"><path d="{smooth(pts, True, corners=sharp_points(pts, 70))}" fill="{C["brow"]}" stroke="{C["brow"]}" stroke-width="1.6" stroke-linejoin="round"/></g>'


DEFS = f"""<radialGradient id="iris" cx=".5" cy=".72" r=".62"><stop offset="0" stop-color="{C['iris_low']}"/>
  <stop offset=".6" stop-color="{C['iris_mid']}"/><stop offset="1" stop-color="{C['iris_top']}"/></radialGradient>"""


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
