"""Chibi eyes and eyebrows, measured from the reference picture (336 x 456 px, same coordinates).

Each eye is a circle (the eye white) with a tall oval iris inside it, clipped to the circle, a thick
lash line hugging the top of the circle, a few outer lashes, a star sparkle and a small round shine.
Brows are one smooth arch each, fitted to the measured outline.
"""
import math

import numpy as np

C = {
    "liner": "#2b1510",
    "iris_top": "#3b1d12",
    "iris_mid": "#5b2e1d",
    "iris_low": "#8a4a31",
    "pupil": "#2a130b",
    "white": "#ffffff",
    "lid_shadow": "#e9d6d0",
    "lower_line": "#8a5a48",
    "brow": "#3a2016",
}

# Measured from the reference (centre, radius of the eye circle; iris centre and radii)
EYES = {
    "right": dict(c=(137.5, 166.0), r=20.0, iris=(141.5, 164.5), irx=16.0, iry=19.5, outer=-1,
                  star=(144.0, 162.5), star_r=7.8, dot=(134.5, 176.0)),
    "left": dict(c=(208.0, 165.0), r=19.5, iris=(209.0, 162.5), irx=16.0, iry=19.0, outer=1,
                 star=(212.5, 157.5), star_r=7.2, dot=(201.0, 171.0)),
}
BROWS = {   # outline points, measured: top edge from outer tail to inner end, then back along the bottom
    "right": [(111.5, 139), (118, 133.2), (129, 130.6), (142, 130.8), (151, 133.2), (156.6, 136.6),
              (158.2, 140), (156, 142.8), (151.5, 141.4), (141, 138.6), (129, 138), (118.5, 139.4), (113, 141.2)],
    "left": [(233, 133.5), (224, 126.6), (212, 125.4), (200, 126.8), (190, 129.8), (184, 133.2),
             (182, 137.4), (184, 141.6), (189, 139.8), (200, 134.8), (212, 132.4), (223, 132.2), (230, 135.2)],
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


def arc_pts(c, r, a0, a1, n=9):
    """Points on a circle from angle a0 to a1 (degrees; 0 = right, -90 = top)."""
    return [(c[0] + r * math.cos(math.radians(a)), c[1] + r * math.sin(math.radians(a)))
            for a in np.linspace(a0, a1, n)]


def star(c, r):
    x, y = c
    k = r * .33
    pts = [(x, y - r), (x + k, y - k), (x + r, y), (x + k, y + k), (x, y + r), (x - k, y + k), (x - r, y), (x - k, y - k)]
    return f'<path d="{smooth(pts, True, range(8))}" fill="{C["white"]}"/>'


def eye(side, state="open"):
    e = EYES[side]
    (cx, cy), r, o = e["c"], e["r"], e["outer"]
    gid = f"{side}_eye"
    if state == "closed":
        pts = arc_pts((cx, cy - r * .55), r * 1.05, 160 if o < 0 else 20, 20 if o < 0 else 160, 7)
        return f'<g id="{gid}"><path d="{smooth(pts, False)}" fill="none" stroke="{C["liner"]}" stroke-width="4" stroke-linecap="round"/></g>'
    # eye white = circle; iris = tall oval clipped to it
    clip = f'<clipPath id="clip_{gid}"><circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}"/></clipPath>'
    white = f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" fill="{C["white"]}"/>'
    ix, iy = e["iris"]
    iris = (f'<g clip-path="url(#clip_{gid})">'
            f'<ellipse cx="{f(cx)}" cy="{f(cy - r * .75)}" rx="{f(r)}" ry="{f(r * .45)}" fill="{C["lid_shadow"]}"/>'
            f'<ellipse cx="{f(ix)}" cy="{f(iy)}" rx="{f(e["irx"])}" ry="{f(e["iry"])}" fill="url(#iris)" '
            f'stroke="{C["pupil"]}" stroke-width="1.6"/>'
            f'<ellipse cx="{f(ix)}" cy="{f(iy - 1)}" rx="{f(e["irx"] * .55)}" ry="{f(e["iry"] * .55)}" fill="{C["pupil"]}" opacity=".55"/>'
            + star(e["star"], e["star_r"]) +
            f'<circle cx="{f(e["dot"][0])}" cy="{f(e["dot"][1])}" r="2.6" fill="{C["white"]}"/>'
            f'<circle cx="{f(e["dot"][0])}" cy="{f(e["dot"][1])}" r="4.6" fill="{C["white"]}" opacity=".25"/></g>')
    # lash line: thick band hugging the top of the circle, thicker toward the outer corner
    a_in, a_out = (-20, -172) if o < 0 else (-160, -8)
    outer_edge = [(cx + (r + 1.6 + 3.4 * t) * math.cos(math.radians(a)), cy + (r + 1.6 + 3.4 * t) * math.sin(math.radians(a)))
                  for a, t in zip(np.linspace(a_in, a_out, 11), np.linspace(0, 1, 11) ** .7)]
    inner_edge = arc_pts((cx, cy), r - 2.2, a_out, a_in, 11)
    tip = (cx + o * (r + 7), cy - 3)
    liner = f'<path d="{smooth(outer_edge + [tip] + inner_edge, True, corners=(11,))}" fill="{C["liner"]}"/>'
    # outer lashes: little curved spikes flicking outward
    lashes = ""
    for ang, length, bend in ((-138, 6.5, .75), (-158, 7.5, .7)) if o < 0 else ((-42, 6.5, .75), (-22, 7.5, .7)):
        a = math.radians(ang)
        rr = r + 3.5
        bx, by = cx + rr * math.cos(a), cy + rr * math.sin(a)
        ta = a + o * bend                      # tip swept upward, away from the eye
        tx, ty = bx + length * math.cos(ta), by + length * math.sin(ta)
        nx, ny = -math.sin(a) * 2.4, math.cos(a) * 2.4
        mx, my = (bx + tx) / 2 + math.cos(a) * 1.2, (by + ty) / 2 + math.sin(a) * 1.2
        lashes += (f'<path d="{smooth([(bx + nx, by + ny), (mx, my), (tx, ty), (bx - nx, by - ny)], True, (0, 2, 3))}" '
                   f'fill="{C["liner"]}"/>')
    lower = arc_pts((cx, cy), r - .3, 140 if o < 0 else 40, 40 if o < 0 else 140, 9)
    lower_line = (f'<path d="{smooth(lower, False)}" fill="none" stroke="{C["lower_line"]}" stroke-width="1.1" '
                  f'stroke-linecap="round" opacity=".35"/>')
    return f'<g id="{gid}">{clip}{white}{iris}{lower_line}{liner}{lashes}</g>'


def brow(side, lift=0.0):
    pts = [(x, y - lift) for x, y in BROWS[side]]
    return f'<g id="{side}_eyebrow"><path d="{smooth(pts, True, corners=())}" fill="{C["brow"]}"/></g>'


DEFS = f"""<radialGradient id="iris" cx=".5" cy=".78" r=".75"><stop offset="0" stop-color="{C['iris_low']}"/>
  <stop offset=".55" stop-color="{C['iris_mid']}"/><stop offset="1" stop-color="{C['iris_top']}"/></radialGradient>"""


if __name__ == "__main__":
    import sys
    import cairosvg
    from PIL import Image
    out = sys.argv[1] if len(sys.argv) > 1 else "eyes_compare.png"
    ref_path = sys.argv[2]
    box = (95, 110, 255, 210)
    sc = 6
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{(box[2] - box[0]) * sc}" height="{(box[3] - box[1]) * sc}" '
           f'viewBox="{box[0]} {box[1]} {box[2] - box[0]} {box[3] - box[1]}"><defs>{DEFS}</defs>'
           f'<rect x="0" y="0" width="336" height="456" fill="#fdd5bd"/>'
           + eye("right") + eye("left") + brow("right") + brow("left") + "</svg>")
    cairosvg.svg2png(bytestring=svg.encode(), write_to=out + ".mine.png")
    ref = Image.open(ref_path).convert("RGB").crop(box).resize(((box[2] - box[0]) * sc, (box[3] - box[1]) * sc), Image.LANCZOS)
    mine = Image.open(out + ".mine.png").convert("RGB")
    both = Image.new("RGB", (ref.width, ref.height * 2 + 10), "white")
    both.paste(ref, (0, 0))
    both.paste(mine, (0, ref.height + 10))
    both.save(out)
