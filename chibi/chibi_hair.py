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
  <linearGradient id="earWedge" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f8ac82"/>
    <stop offset="1" stop-color="#f39668"/></linearGradient>
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
    face_d = smooth(H2["face_fill"], True)
    # the hair never covers the face (the trace also caught one eye's browns as "hair")
    return (f'<clipPath id="clip_hair_not_face"><path d="M-500,-500 H1000 V1500 H-500 Z {face_d}" clip-rule="evenodd"/>'
            f'</clipPath>' + not_eyes_clip() +
            f'<g id="hair" clip-path="url(#clip_hair_not_face)"><g clip-path="url(#clip_hair_not_eyes)">'
            + "".join(parts) + "</g></g>")


def not_eyes_clip():
    """Everything except the two eyes (+ their lashes): the hair trace caught one eye's browns as hair."""
    holes = ""
    for side in ("right", "left"):
        (cx, cy, r), _, _ = E.master_eye(side)
        R = r + 12
        holes += f" M{f(cx - R)},{f(cy)} a{f(R)},{f(R)} 0 1,0 {f(2 * R)},0 a{f(R)},{f(R)} 0 1,0 {f(-2 * R)},0 Z"
    return (f'<clipPath id="clip_hair_not_eyes"><path d="M-500,-500 H1000 V1500 H-500 Z{holes}" clip-rule="evenodd"/>'
            f'</clipPath>')


# crown and hairline, redrawn cleanly (old-reference px, measured on the new reference's crown)
CROWN_REGION = [(104, 330), (112, 268), (140, 244), (180, 236), (226, 236), (270, 240), (300, 256), (312, 330)]
PART_SPIKE = [(221, 283), (232.5, 267.5), (228.5, 283.5)]
CROWN_STRANDS = [   # dark lines between the locks around the side part: (points from the hairline end, max width)
    ([(221, 282), (219, 268), (208, 257), (188, 252), (165, 254), (146, 264), (133, 282)], 3.6),
    ([(199, 281), (196, 270), (184, 263), (168, 264), (157, 273)], 2.6),
    ([(234, 282), (238, 266), (252, 255), (274, 252), (295, 258), (305, 270)], 3.6),
    ([(240, 281), (252, 272), (272, 271), (290, 280)], 2.6),
    ([(214, 247), (190, 238), (158, 240), (130, 254)], 2.2),
]
HAIRLINE_SPIKES = [   # small skin-coloured points reaching up into the hair from the hairline: (base-l, tip, base-r)
    [(149, 287), (151.5, 280.5), (156, 286)], [(181, 282.5), (182.5, 276.5), (187.5, 282.5)],
    [(194, 282.5), (196, 277), (200, 282.5)], [(255, 290), (264, 284.5), (262, 292)],
]
HAIRLINE = [(110, 326), (114, 312), (122, 301), (133, 292), (147, 286), (165, 282), (190, 280), (220, 281),
            (242, 284), (259, 290), (272, 299), (281, 310), (286, 326)]     # measured on the new reference, one smooth arch
TEMPLE_SHADOW = [(121, 294), (128.5, 291.5), (123.5, 310), (115, 331), (112, 318)]


def taper(points, wmax, colour):
    """A line that is widest in the middle and tapers to fine points (like an inked hair line)."""
    P = np.array(points, float)
    n = len(P)
    left, right = [], []
    for i in range(n):
        d = P[min(i + 1, n - 1)] - P[max(i - 1, 0)]
        d /= np.linalg.norm(d) + 1e-9
        nrm = np.array([-d[1], d[0]])
        w = wmax * (0.35 + 0.65 * np.sin(np.pi * i / (n - 1))) / 2
        left.append(tuple(P[i] + nrm * w))
        right.append(tuple(P[i] - nrm * w))
    pts = left + right[::-1]
    return f'<path d="{smooth(pts, True, corners=(n - 1, n))}" fill="{colour}"/>'


def crown_clean():
    """Clean crown over the traced hair: flat base colour around the hairline (no blotchy tone patches),
    strand lines sweeping away from the side part, the skin-coloured part spike, small hair points on the
    forehead and a thin orange shadow under the hair at the temple."""
    col = H2["colours"]
    face_d = smooth(H2["face_fill"], True)
    region_d = smooth(CROWN_REGION, True)
    strands = "".join(taper(p, w, col["outline"]) for p, w in CROWN_STRANDS)
    # lighter brown on the rounded tops of the locks (their volume), under the strand lines
    sheen = "".join(f'<path d="{smooth(p, False)}" fill="none" stroke="{col["light"]}" stroke-width="7" '
                    f'stroke-linecap="round" opacity=".55"/>' for p in (
                        [(210, 266), (190, 259), (168, 260), (150, 270)], [(242, 268), (258, 260), (282, 259), (298, 266)]))
    tufts = "".join(f'<path d="{smooth(t, True, corners=(0, 1, 2))}" fill="{CF.C["skin"]}"/>' for t in HAIRLINE_SPIKES)
    return (f'<g id="hair_crown"><clipPath id="clip_crown"><path d="{region_d}"/></clipPath>'
            f'<clipPath id="clip_not_face"><path d="M-500,-500 H1000 V1500 H-500 Z {face_d}" clip-rule="evenodd"/></clipPath>'
            f'<clipPath id="clip_face2"><path d="{face_d}"/></clipPath>'
            f'<g clip-path="url(#clip_crown)"><g clip-path="url(#clip_not_face)">'
            f'<path d="{region_d}" fill="{col["base"]}"/>{sheen}{strands}</g>'
            f'<path d="{face_d}" fill="none" stroke="{col["outline"]}" stroke-width="3.4"/></g>'

            + hairline_arch() +
            f'<path d="{smooth(PART_SPIKE, True, corners=(0, 1, 2))}" fill="{CF.C["skin"]}"/>{tufts}</g>')


def hairline_arch():
    """Forehead top as one smooth arch (the traced edge was bumpy): skin below it, dark hair edge on it, and a
    thin orange shadow under the hair at both temples."""
    col = H2["colours"]
    arch = smooth(HAIRLINE, False)
    skin = smooth(HAIRLINE + [(287, 338), (109, 338)], True, corners=(len(HAIRLINE) - 1, len(HAIRLINE), len(HAIRLINE) + 1, 0))
    # thin orange shadow just under the hair edge at both temples, following the arch
    P = np.array(HAIRLINE, float)
    temples = ""
    for idx in (range(0, 5), range(len(P) - 5, len(P))):
        seg = P[list(idx)]
        inner = seg + [0, 5.5] + np.where(seg[:, :1] < 200, [[4.5, 0]], [[-4.5, 0]])
        pts = [tuple(p) for p in seg] + [tuple(p) for p in inner[::-1]]
        temples += f'<path d="{smooth(pts, True, corners=(0, len(seg) - 1, len(seg), len(pts) - 1))}" fill="#f4a47c"/>'
    return (f'<path d="{skin}" fill="{CF.C["skin"]}"/>{temples}'
            f'<path d="{arch}" fill="none" stroke="{col["outline"]}" stroke-width="3.4" stroke-linecap="round"/>')


def ears_cel():
    """Ears traced from the new reference: skin shape with a dark outline and the orange inner fold.
    Drawn on top of the hair (in the reference the ears sit between the locks)."""
    col, out = H2["ear_colours"], []
    out.append(ear_left_clean() + ear_left_gap())
    out.append(ear_right_clean())
    for side, e in ():
        g = [path(p, fill=col["skin"], stroke=col["outline"], stroke_width=2.2, stroke_linejoin="round") for p in e["skin"]]
        # an ear with no traced skin (only its orange inside peeks out between the locks) gets an outline too
        edge = {} if e["skin"] else dict(stroke=col["outline"], stroke_width=2.2, stroke_linejoin="round")
        g += [path(p, fill=col["fold"], **edge) for p in e["fold"]]
        out.append(f'<g id="{side}_ear">' + "".join(g) + "</g>")
    return "".join(out)


_T = json.load(open(os.path.join(HERE, "ref", "new_to_old.json")))


def from_new(pts):
    """Points measured in pixels of the new reference -> drawing coordinates."""
    s, (nx, ny), (ox, oy) = _T["scale"], _T["new_mid"], _T["old_mid"]
    return [((x - nx) / s + ox, (y - ny) / s + oy) for x, y in pts]


def ear_right_clean():
    """Her right ear (viewer's left): only a small orange wedge peeks out between two locks. Measured on the
    new reference: pointed top, rounded outer side, straight inner edge; dark hair outline all round."""
    col = H2["ear_colours"]
    pts = from_new([(241, 613), (234, 624), (226, 636), (222, 645), (226, 656), (235, 667), (246, 675), (256, 679),
                    (252, 668), (250, 655), (250, 642), (247, 628)])
    return (f'<g id="right_ear"><path d="{smooth(pts, True, corners=(0, 7))}" fill="url(#earWedge)" '
            f'stroke="{H2["colours"]["outline"]}" stroke-width="2.6" stroke-linejoin="round"/></g>')


def ear_left_gap():
    """What sits between her left ear and her face in the reference: a medium-brown lock running down from the
    top to a point (so the ear never touches the face there), and below it the orange crease where the ear's
    lower edge meets the cheek."""
    lock = from_new([(697, 540), (714, 540), (713, 566), (706, 592), (699, 616), (693, 641), (690, 646), (691, 624),
                     (693, 596), (695, 568)])
    crease = from_new([(700, 624), (707, 632), (702, 650), (695, 664), (689, 674), (684, 675), (686, 662), (692, 644)])
    # below the lock's tip the ear's lower edge joins the cheek: skin there, no outline
    join = from_new([(683, 636), (692, 640), (700, 627), (706, 634), (699, 658), (690, 674), (681, 683), (674, 684),
                     (677, 662)])
    return (f'<path d="{smooth(join, True)}" fill="{H2["ear_colours"]["skin"]}"/>'
            f'<path d="{smooth(crease, True, corners=(4, 5))}" fill="#f5996d"/>'
            f'<path d="{smooth(lock, True, corners=(6,))}" fill="#452a1f"/>'
            f'<path d="{smooth(lock[:7], False)}" fill="none" stroke="{H2["colours"]["outline"]}" stroke-width="1.6"/>')


# her left ear (viewer's right), fitted to the traced ear: centre, half-axes, tilt (degrees)
EAR_L = dict(cx=316.8, cy=433.0, rx=16.0, ry=27.0, tilt=26)


def ear_left_clean():
    """Tilted oval ear with the reference's thick, even dark rim, an orange inner rim along the top-right,
    and the curled inner fold (thin at the top, thicker comma lower down)."""
    col, e = H2["ear_colours"], EAR_L
    t = f'translate({e["cx"]} {e["cy"]}) rotate({e["tilt"]})'
    rx, ry = e["rx"], e["ry"]
    # inner fold: thin arc under the top rim, curling down into a thicker comma
    fold = smooth([(10, -16), (1, -16.5), (-6.5, -12), (-10.5, -3), (-10.5, 8), (-6, 12), (-3.5, 5), (-3.5, -3),
                   (0, -9.5), (5, -12.5), (10.5, -13)], True)
    band = f'<ellipse rx="{rx + 4.4}" ry="{ry + 4.4}" fill="{H2["colours"]["outline"]}"/>'
    # the dark rim runs round the top, the outer side and the bottom; at the lower inner side the ear meets the
    # cheek with no line, just a soft orange crease
    import math
    wedge_pts = [(0, 0)] + [(60 * math.cos(math.radians(a)), 60 * math.sin(math.radians(a))) for a in range(136, 186, 8)]
    wedge = "M" + " L".join(f"{f(x)},{f(y)}" for x, y in wedge_pts) + " Z"
    rim_keep = "M-80,-80 L80,-80 L80,80 L-80,80 Z " + wedge
    crease = smooth([(-rx + 1.5, 4), (-rx + 3.5, 14), (-rx + 7.5, 23), (-rx + 6, 13), (-rx + 3.8, 3)], True)
    return (f'<g id="left_ear" transform="{t}">'
            f'<clipPath id="clip_ear_l"><ellipse rx="{rx}" ry="{ry}"/></clipPath>'
            f'<clipPath id="clip_ear_rim"><path d="{rim_keep}" clip-rule="evenodd"/></clipPath>'
            f'<clipPath id="clip_ear_gap"><path d="{wedge}"/></clipPath>'
            f'<g clip-path="url(#clip_ear_rim)">{band}</g>'
            f'<g clip-path="url(#clip_ear_gap)"><ellipse cx="-2" rx="{rx + 3}" ry="{ry + 3}" fill="{col["skin"]}"/></g>'
            f'<g clip-path="url(#clip_ear_l)"><ellipse rx="{rx}" ry="{ry}" fill="#f7a67c"/>'
            f'<ellipse cx="-2.4" cy="2" rx="{rx}" ry="{ry}" fill="{col["skin"]}"/>'
            f'<path d="{crease}" fill="#f39a70"/>'
            f'<path d="{fold}" fill="{col["fold"]}"/></g></g>')


def head_svg_v2(mouth_shape="smile", look=(0, 0), eyes="open", body=True):
    backing = "".join(f'<ellipse cx="{f(x)}" cy="{f(y)}" rx="9" ry="9" fill="{H2["colours"]["outline"]}"/>'
                      for x, y in from_new([(686, 684), (262, 684)]))   # dark behind the ear bottoms (no white specks)
    face_fill = backing + not_eyes_clip().replace("clip_hair_not_eyes", "clip_ff_not_eyes") + (
                 f'<path d="{smooth(H2["face_fill"], True)}" fill="{CF.C["skin"]}" stroke="{H2["colours"]["outline"]}" '
                 f'stroke-width="14" stroke-linejoin="round" clip-path="url(#clip_ff_not_eyes)"/>'
                 f'<path d="{smooth(H2["face_fill"], True)}" fill="{CF.C["skin"]}"/>')
    blush = "".join(f'<ellipse cx="{x}" cy="459.5" rx="18.5" ry="13.5" fill="#febdaa" opacity=".5"/>'
                    f'<ellipse cx="{x}" cy="459.5" rx="17" ry="12.2" fill="#febdaa"/>' for x in (111, 266.5))
    eye_skin = "".join(f'<circle cx="{f(c[0])}" cy="{f(c[1])}" r="{f(c[2] + 9)}" fill="{CF.C["skin"]}"/>'
                       for c in (E.master_eye("right")[0], E.master_eye("left")[0]))
    return (face_fill + hair_cel() + crown_clean() + (temp_body() if body else "") + eye_skin + blush + CF.nose()
            + CF.mouth(mouth_shape) + E.eye("right", eyes, look) + E.eye("left", eyes, look) + E.brow("right")
            + E.brow("left") + ears_cel())


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
