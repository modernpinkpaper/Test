"""Chibi hair, from shapes traced on the reference (see measure_hair.py). Pixels of the reference sheet.

Layers (so the hair can sway / follow the head separately later):
  hair_back  - the whole silhouette, drawn behind the face and body
  hair_front - the crown and the locks framing the face, drawn over the forehead edge
  strands    - darker strand lines and lighter shine streaks
"""
import json
import os

import numpy as np

import chibi_eyes as E
import chibi_face as CF

HERE = os.path.dirname(os.path.abspath(__file__))
H = json.load(open(os.path.join(HERE, "ref", "measured_hair.json")))
f, smooth = E.f, E.smooth

C = {
    "hair": H["colours"]["base"],
    "hair_dark": H["colours"]["dark"],
    "hair_light": H["colours"]["light"],
    "outline": H["colours"]["outline"],
}


def path(pts, **attrs):
    extra = "".join(f' {k.replace("_", "-")}="{v}"' for k, v in attrs.items())
    return f'<path d="{smooth(pts, True)}"{extra}/>'


def _median(v, k=5):
    v = np.array(v, float)
    return np.array([np.median(v[max(0, i - k // 2):i + k // 2 + 1]) for i in range(len(v))])


COVER_BOTTOM = 480
TIP_START = 640         # below this the two locks are rebuilt as smooth tapered tips      # the front hair frames the face down to here; below, the jaw sits over the back hair


def face_edge():
    """Visible face edge, from the left side at COVER_BOTTOM, up and over the hairline arch, down the right side.
    Measured per column / row on the reference, lightly smoothed; keeps the small peak at the side part."""
    top = np.array(H["hairline_top"], float)
    sides = np.array(H["face_sides"], float)
    sides = sides[sides[:, 0] <= COVER_BOTTOM]
    left_x, right_x = _median(sides[:, 1]), _median(sides[:, 2])
    ys = sides[:, 0]
    top_y = _median(top[:, 1], 3)
    left = [(x, y) for x, y in zip(left_x[::-1], ys[::-1]) if y > top_y[0] + 4][::2]
    arch = [(x, y) for x, y in zip(top[:, 0], top_y)][::2]
    right = [(x, y) for x, y in zip(right_x, ys) if y > top_y[-1] + 4][::2]
    return left + arch + right


def tips():
    """Both long locks below the shoulders: outer edge down to a tapered tip, then the inner edge back up."""
    out = {}
    for side, rows in H["locks"].items():
        rows = np.array([r for r in rows if r[0] >= TIP_START], float)
        ys, xo, xi = rows[:, 0], _median(rows[:, 1], 5), _median(rows[:, 2], 5)
        if side == "left":                                      # viewer's right: outer edge is the larger x
            xo, xi = xi, xo
        keep = slice(0, len(ys), 4)
        tip = ((xo[-1] * .4 + xi[-1] * .6), ys[-1] + 12)
        outer = list(zip(xo[keep], ys[keep]))
        inner = list(zip(xi[keep], ys[keep]))[::-1]
        out[side] = outer + [tip] + inner
    return out


def back_shape():
    """Whole hair silhouette: traced upper part + rebuilt tapered locks, joined behind the shoulders."""
    P = H["hair_back"]
    y_cut = TIP_START - 12
    n = len(P)
    # the contiguous stretch of the traced outline around the top of the head, above the locks' tips
    top = int(np.argmin([p[1] for p in P]))
    a = top
    while P[(a - 1) % n][1] < y_cut:
        a -= 1
    b = top
    while P[(b + 1) % n][1] < y_cut:
        b += 1
    run = [P[i % n] for i in range(a, b + 1)]
    t = tips()
    # the run ends on one side: go down that side's lock (outer edge first), across behind the body, up the other
    end_left = run[-1][0] < E.FACE_MID_X             # viewer's left = her right lock
    a, b = (t["right"], t["left"][::-1]) if end_left else (t["left"], t["right"][::-1])
    if (end_left and a[0][0] > a[-1][0]) or (not end_left and a[0][0] < a[-1][0]):
        a = a[::-1]
    return run + a + b


def hair_back():
    shape = back_shape()
    clip = f'<clipPath id="clip_hair_back"><path d="{smooth(shape, True)}"/></clipPath>'
    sheen = (f'<g clip-path="url(#clip_hair_back)">'
             f'<ellipse cx="44" cy="520" rx="22" ry="150" fill="url(#sheen)"/>'
             f'<ellipse cx="332" cy="540" rx="22" ry="150" fill="url(#sheen)"/>'
             f'<ellipse cx="186" cy="215" rx="120" ry="34" fill="url(#sheen)"/></g>')
    hole = face_hole()
    ring = smooth(shape, True) + " " + smooth(hole, True)
    ring_clip = f'<clipPath id="clip_hair_ring"><path d="{ring}" clip-rule="evenodd"/></clipPath>'
    edge_d = smooth(face_edge(), False)
    near_face = f'<g clip-path="url(#clip_hair_ring)"><path d="{edge_d}" fill="none" stroke="#2a1109" stroke-width="16" opacity=".35"/>{crown_strands()}</g>'
    return (f'<g id="hair_back">{clip}{ring_clip}<path d="{ring}" fill="url(#hairGrad)" fill-rule="evenodd" '
            f'stroke="{C["outline"]}" stroke-width="2.6" stroke-linejoin="round"/>'
            + sheen.replace('clip_hair_back', 'clip_hair_ring') + near_face
            + flow_strands().replace('<g id="hair_strands_back">', '<g id="hair_strands_back" clip-path="url(#clip_hair_ring)">') + "</g>")


def flow_strands():  # noqa: C901
    """Strand lines that follow the hair's outer edge: curves offset inward from each side of the silhouette,
    as thin tapered darker lines plus a few lighter shine streaks (like the reference's strand texture)."""
    import numpy as np
    P = np.array(H["hair_back"], float)
    mid = E.FACE_MID_X
    out = []
    for side in (-1, 1):
        edge = P[(np.sign(P[:, 0] - mid) == side) & (P[:, 1] > 230) & (P[:, 1] < 690)]
        edge = edge[np.argsort(edge[:, 1])]
        if len(edge) < 4:
            continue
        ys = np.linspace(edge[0, 1] + 10, edge[-1, 1] - 8, 9)
        xs = np.interp(ys, edge[:, 1], edge[:, 0])
        for k, (depth, colour, width, op, y_from, y_to) in enumerate([
                (8, "#2c120a", 2.2, .85, 0.1, 1.0), (17, "#7c4733", 4.0, .6, 0.2, .95),
                (27, "#2c120a", 2.0, .75, 0.3, 1.0), (38, "#7c4733", 3.0, .5, 0.45, .92),
                (50, "#2c120a", 1.8, .6, 0.55, 1.0)]):
            a, b = int(len(ys) * y_from), int(len(ys) * y_to)
            pts = [(x - side * depth * (0.6 + 0.4 * t), y) for t, (x, y) in
                   zip(np.linspace(0, 1, b - a), zip(xs[a:b], ys[a:b]))]
            if len(pts) >= 3:
                out.append(f'<path d="{smooth(pts, False)}" fill="none" stroke="{colour}" stroke-width="{width}" '
                           f'stroke-linecap="round" opacity="{op}"/>')
    return '<g id="hair_strands_back">' + "".join(out) + "</g>"


def crown_strands():
    """Part line and the strands sweeping away from the part (these sit on the front hair)."""
    out = []
    part = (226, 272)
    crown = [[part, (232, 240), (244, 205)],
             [(214, 268), (180, 236), (140, 222), (104, 238)], [(206, 270), (170, 250), (132, 250), (100, 275)],
             [(236, 268), (262, 244), (290, 236), (316, 250)]]
    for i, pts in enumerate(crown):
        colour, width, op = ("#2c120a", 2.2, .85) if i != 2 else ("#7c4733", 4.0, .6)
        out.append(f'<path d="{smooth(pts, False)}" fill="none" stroke="{colour}" stroke-width="{width}" '
                   f'stroke-linecap="round" opacity="{op}"/>')
    out.append(f'<path d="{smooth([(118, 214), (160, 196), (205, 190)], False)}" fill="none" stroke="{C["hair_light"]}" '
               f'stroke-width="6" stroke-linecap="round" opacity=".35"/>')
    return '<g id="hair_strands_front">' + "".join(out) + "</g>"


def face_hole():
    """Visible face: hairline arch and face sides (measured) down to COVER_BOTTOM, then the jaw and chin."""
    edge = face_edge()
    jaw = [p for p in CF.jaw_points() if p[1] > COVER_BOTTOM]
    return edge + sorted(jaw, key=lambda p: -p[0])


def hair_front():
    """The edge where hair meets the face: dark outline, a darker band of hair just outside it, and a soft
    shadow on the skin just inside it. (The hair itself is one piece with a face-shaped hole: hair_back.)"""
    edge = face_edge()
    (lx, ly), (rx, ry) = edge[0], edge[-1]
    edge_d = smooth([(lx, COVER_BOTTOM + 6)] + edge + [(rx, COVER_BOTTOM + 6)], False)
    hole_d = smooth(face_hole(), True)
    return (f'<g id="hair_front"><clipPath id="clip_face_vis"><path d="{hole_d}"/></clipPath>'
            f'<g clip-path="url(#clip_face_vis)"><path d="{edge_d}" fill="none" stroke="#e79a78" stroke-width="8" opacity=".22"/></g>'
            f'<path d="{edge_d}" fill="none" stroke="{C["outline"]}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></g>')


DEFS = CF.DEFS + f"""
  <linearGradient id="hairGrad" gradientUnits="userSpaceOnUse" x1="0" y1="180" x2="0" y2="720">
    <stop offset="0" stop-color="#5a3325"/><stop offset=".3" stop-color="{C['hair']}"/><stop offset="1" stop-color="#5a3222"/></linearGradient>
  <radialGradient id="sheen"><stop offset="0" stop-color="#8a5038" stop-opacity=".75"/>
    <stop offset="1" stop-color="#8a5038" stop-opacity="0"/></radialGradient>"""


def temp_body():
    """Placeholder body traced flat from the reference, only for previews until the real body is built."""
    return ('<g id="temp_body">'
            + "".join(path(p, fill=CF.C["skin"], stroke="#34110b", stroke_width=2.2) for p in H["temp_body"]["skin"])
            + "".join(path(p, fill="#2e2624", stroke="#1d1414", stroke_width=2) for p in H["temp_body"]["clothes"]) + "</g>")


def head_svg(mouth_shape="smile", look=(0, 0), eyes="open", body=True):
    # her right ear (viewer's left) is hidden by the hair, as in the reference
    face_fill = f'<path d="{smooth(face_hole(), True)}" fill="{CF.C["skin"]}"/>'
    return (CF.head() + face_fill + hair_back() + (temp_body() if body else "") + CF.blush() + CF.nose() + CF.mouth(mouth_shape)
            + E.eye("right", eyes, look) + E.eye("left", eyes, look) + E.brow("right") + E.brow("left") + hair_front()
            + CF.ear("left"))


if __name__ == "__main__" and len(__import__("sys").argv) > 3:      # v1 preview: out old_ref v1
    import sys
    import cairosvg
    from PIL import Image
    out, ref_path = sys.argv[1], sys.argv[2]
    box = (0, 170, 370, 740)
    sc = 2
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{(box[2] - box[0]) * sc}" height="{(box[3] - box[1]) * sc}" '
           f'viewBox="{box[0]} {box[1]} {box[2] - box[0]} {box[3] - box[1]}"><defs>{DEFS}</defs>'
           f'<rect x="0" y="0" width="2000" height="2000" fill="#ffffff"/>{head_svg()}</svg>')
    cairosvg.svg2png(bytestring=svg.encode(), write_to=out + ".mine.png")
    a = Image.open(ref_path).convert("RGB").crop(box).resize(((box[2] - box[0]) * sc, (box[3] - box[1]) * sc), Image.LANCZOS)
    b = Image.open(out + ".mine.png").convert("RGB")
    both = Image.new("RGB", (a.width * 2 + 12, a.height), "white")
    both.paste(a, (0, 0))
    both.paste(b, (a.width + 12, 0))
    both.save(out)


# ---------------------------------------------------------------- v2: cel-shaded hair traced from the new reference
H2_PATH = os.path.join(HERE, "ref", "measured_hair2.json")
H2 = json.load(open(H2_PATH)) if os.path.exists(H2_PATH) else None


def hair_cel():
    """Hair built from its flat tones: dark outline silhouette, then base, shadow, light and highlight shapes.
    The gaps between the fill shapes show the outline colour as the lines between the locks."""
    col = H2["colours"]
    parts = [path(p, fill=col["outline"]) for p in H2["silhouette"]]
    for tone in ("base", "shadow", "light", "highlight"):
        parts += [path(p, fill=col[tone]) for p in H2["tones"][tone]]
    return '<g id="hair">' + "".join(parts) + "</g>"


def head_svg_v2(mouth_shape="smile", look=(0, 0), eyes="open", body=True):
    face_fill = f'<path d="{smooth(H2["face_fill"], True)}" fill="{CF.C["skin"]}"/>'
    return (CF.head() + face_fill + hair_cel() + (temp_body() if body else "") + CF.blush() + CF.nose()
            + CF.mouth(mouth_shape) + E.eye("right", eyes, look) + E.eye("left", eyes, look) + E.brow("right")
            + E.brow("left") + CF.ear("left"))


def compare_v2(out, new_ref):
    import cairosvg
    from PIL import Image
    T = json.load(open(os.path.join(HERE, "ref", "new_to_old.json")))
    box = (0, 170, 370, 740)
    sc = 2
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{(box[2] - box[0]) * sc}" height="{(box[3] - box[1]) * sc}" '
           f'viewBox="{box[0]} {box[1]} {box[2] - box[0]} {box[3] - box[1]}"><defs>{DEFS}</defs>'
           f'<rect x="0" y="0" width="2000" height="2000" fill="#ffffff"/>{head_svg_v2()}</svg>')
    cairosvg.svg2png(bytestring=svg.encode(), write_to=out + ".mine.png")
    s, (nx, ny), (ox, oy) = T["scale"], T["new_mid"], T["old_mid"]
    nb = [(box[0] - ox) * s + nx, (box[1] - oy) * s + ny, (box[2] - ox) * s + nx, (box[3] - oy) * s + ny]
    a = Image.open(new_ref).convert("RGB").crop(tuple(int(v) for v in nb)).resize(((box[2] - box[0]) * sc, (box[3] - box[1]) * sc), Image.LANCZOS)
    b = Image.open(out + ".mine.png").convert("RGB")
    both = Image.new("RGB", (a.width * 2 + 12, a.height), "white")
    both.paste(a, (0, 0))
    both.paste(b, (a.width + 12, 0))
    both.save(out)


if __name__ == "__main__" and len(__import__("sys").argv) == 3:       # v2 preview: out new_ref
    import sys
    compare_v2(sys.argv[1], sys.argv[2])
