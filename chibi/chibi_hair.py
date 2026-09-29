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


HAIR_SPLIT_Y = 490   # below this y the hair comes from the full-body picture (chibi_body hair_behind)
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
  <radialGradient id="earGlow"><stop offset=".3" stop-color="#f79e74"/><stop offset="1" stop-color="#f79e74" stop-opacity="0"/></radialGradient>
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
    parts += [path(p, fill=col["outline"]) for p in H2["tones"].get("lines", [])]
    face_d = smooth(H2["face_fill"], True)
    # the hair never covers the face (the trace also caught one eye's browns as "hair")
    return (f'<clipPath id="clip_hair_not_face"><path d="M-500,-500 H1000 V1500 H-500 Z {face_d}" clip-rule="evenodd"/>'
            f'</clipPath>' + not_eyes_clip() +
            f'<clipPath id="clip_hair_top"><rect x="-100" y="-100" width="600" height="{HAIR_SPLIT_Y + HAIR_FADE + 100}"/></clipPath>'
            f'<g id="hair" clip-path="url(#clip_hair_not_face)"><g clip-path="url(#clip_hair_not_eyes)"><g clip-path="url(#clip_hair_top)">'
            + "".join(parts) + "</g></g></g>")


HB_GROW = 3
HAIR_FADE = 45       # the two hair tracings cross-fade over this distance around HAIR_SPLIT_Y
HB_PATH = os.path.join(HERE, "ref", "measured_hair_body.json")
HB = json.load(open(HB_PATH)) if os.path.exists(HB_PATH) else None


def hair_body_lower():
    """Hair below HAIR_SPLIT_Y, traced tone by tone from the full-body picture (it matches the body there)."""
    if HB is None or HAIR_SPLIT_Y >= 1000:
        return ""
    col = HB["colours"]
    parts = [path(p, fill=col["outline"], stroke=col["outline"], stroke_width=HB_GROW, stroke_linejoin="round")
             for p in HB["silhouette"]]
    for tone in ("base", "shadow", "light", "highlight"):
        parts += [path(p, fill=col[tone]) for p in HB["tones"][tone]]
    parts += [path(p, fill=col["outline"]) for p in HB["tones"].get("lines", [])]
    y0, y1 = HAIR_SPLIT_Y - HAIR_FADE, HAIR_SPLIT_Y + HAIR_FADE
    return (f'<linearGradient id="hairFade" gradientUnits="userSpaceOnUse" x1="0" y1="{y0}" x2="0" y2="{y1}">'
            f'<stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#fff" stop-opacity="1"/></linearGradient>'
            f'<mask id="mask_hair_low" maskUnits="userSpaceOnUse" x="-100" y="-100" width="700" height="2200">'
            f'<rect x="-100" y="{y0}" width="700" height="2200" fill="url(#hairFade)"/></mask>'
            f'<g id="hair_lower" mask="url(#mask_hair_low)">' + "".join(parts) + "</g>")


def not_eyes_clip():
    """Everything except the two eyes (+ their lashes): the hair trace caught one eye's browns as hair."""
    holes = ""
    for side in ("right", "left"):
        (cx, cy, r), _, _ = E.master_eye(side)
        R = r + 9          # same size as the skin disc drawn under each eye (no ring between them)
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
HAIRLINE = [(113.0, 324.0), (117.0, 310.0), (124.0, 299.0), (135.0, 291.0), (148.0, 285.0), (166.0, 282.0), (190.0, 280.0), (219.0, 281.0), (240.0, 283.0), (256.0, 289.0), (268.0, 297.0), (277.0, 308.0), (282.0, 324.0)]     # measured on the new reference, one smooth arch
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
        w = wmax * max(0.04, np.sin(np.pi * i / (n - 1)) ** 0.6) / 2      # full width in the middle, points at the ends
        left.append(tuple(P[i] + nrm * w))
        right.append(tuple(P[i] - nrm * w))
    pts = left + right[::-1]
    return f'<path d="{smooth(pts, True, corners=(n - 1, n))}" fill="{colour}"/>'


def sample_curve(pts, n):
    """Evenly spaced points along a smooth curve through pts (so a tapered line follows the same curve)."""
    P = np.array(pts, float)
    seg = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    t = np.linspace(0, seg[-1], n)
    return list(zip(np.interp(t, seg, P[:, 0]), np.interp(t, seg, P[:, 1])))


def crown_clean():
    """Over the traced hair: the smooth measured hairline (arch, dark edge, orange temple shadows) and the
    skin-coloured point at the side part. (The lock lines themselves come from the trace.)"""
    return (f'<g id="hair_crown">' + hairline_arch() +
            f'<path d="{smooth(PART_SPIKE, True, corners=(0, 1, 2))}" fill="{CF.C["skin"]}"/></g>')


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
            + taper(sample_curve(HAIRLINE, 24), 4.2, col["outline"]))


def ears_cel():
    """Ears traced from the new reference: skin shape with a dark outline and the orange inner fold.
    Drawn on top of the hair (in the reference the ears sit between the locks)."""
    col, out = H2["ear_colours"], []
    out.append(ear_left_param())
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
    """Her right ear (viewer's left): only a small orange wedge peeks out between two locks (traced)."""
    return f'<g id="right_ear">{ear_traced("right")}</g>'


GAP_SHIFT = (0.0, -2.0)      # fitted shift (drawing units) of the lock / crease between the big ear and the cheek


def from_new_shift(dx, dy, pts):
    return [(x + dx, y + dy) for x, y in from_new(pts)]


def ear_left_gap(lock_only=False):
    """What sits between her left ear and her face in the reference: a medium-brown lock running down from the
    top to a point (so the ear never touches the face there), and below it the orange crease where the ear's
    lower edge meets the cheek."""
    gdx, gdy = GAP_SHIFT
    # the lock stops at the ear's middle (in the reference it ends well above the ear's bottom)
    lock = from_new_shift(gdx, gdy, [(697, 540), (714, 540), (713, 566), (708, 588), (702, 606), (699, 612), (698, 596),
                                     (696, 568)])
    crease = from_new_shift(gdx, gdy, [(702, 618), (708, 628), (704, 648), (697, 663), (690, 672), (686, 672), (689, 660),
                                       (695, 642)])
    # below the lock the ear's lower part joins the cheek: one skin area from the face edge to the ear, no line
    join = from_new_shift(gdx, gdy, [(680, 610), (702, 606), (716, 620), (722, 650), (716, 674), (700, 684), (682, 686),
                                     (672, 668), (674, 640)])
    lock_svg = (f'<path d="{smooth(lock, True, corners=(5,))}" fill="#452a1f"/>'
                f'<path d="{smooth(lock[:6], False)}" fill="none" stroke="{H2["colours"]["outline"]}" stroke-width="1.6"/>')
    if lock_only:
        # thin orange crease where the ear's inner edge meets the cheek (follows the traced ear edge)
        P = [p for p in H2["ears_fit"]["left"]["inner"] if p[0] < 311 and 432 < p[1] < 454]
        P = sorted(P, key=lambda p: p[1])
        crease_line = (f'<path d="{smooth(P, False)}" fill="none" stroke="#f0976b" stroke-width="1.5" opacity=".85" '
                       f'stroke-linecap="round"/>') if len(P) >= 2 else ""
        return lock_svg + crease_line
    return (f'<path d="{smooth(join, True)}" fill="{H2["ear_colours"]["skin"]}"/>'
            f'<path d="{smooth(crease, True, corners=(4, 5))}" fill="#f5996d"/>'
            f'<path d="{smooth(lock, True, corners=(5,))}" fill="#452a1f"/>'
            f'<path d="{smooth(lock[:6], False)}" fill="none" stroke="{H2["colours"]["outline"]}" stroke-width="1.6"/>')


# her left ear (viewer's right), fitted to the traced ear: centre, half-axes, tilt (degrees)
EAR_L = dict(cx=316.8, cy=433.0, rx=16.0, ry=27.0, tilt=26)


FOLD_FIT = (4.0, -2.0, 1.35, -15.0)     # fitted: shift x, shift y, scale, extra turn (degrees) of the inner fold
RIM_FIT = (-2.0, 5.0)                # fitted: offset of the skin inside the ear (leaves the orange inner rim)


def ear_traced(side):
    """Ear inside: the traced outline of the reference's ear skin; orange inner rim along the top/outer edge
    and the curled fold drawn as clean shapes, positioned and sized by fitting to the reference."""
    e = H2["ears_fit"][side]
    col = H2["ear_colours"]
    inner = smooth(e["inner"], True)
    if side == "right":          # only the orange wedge shows between the locks
        return (f'<path d="{inner}" fill="none" stroke="{H2["colours"]["outline"]}" stroke-width="5" stroke-linejoin="round"/>'
                f'<path d="{inner}" fill="{col["fold"]}"/>')
    L = EAR_L
    t = f'translate({L["cx"]} {L["cy"]}) rotate({L["tilt"]})'
    fdx, fdy, fk, frot = FOLD_FIT
    fold = smooth([(10, -16), (1, -16.5), (-6.5, -12), (-10.5, -3), (-10.5, 8), (-6, 12), (-3.5, 5), (-3.5, -3),
                   (0, -9.5), (5, -12.5), (10.5, -13)], True)
    rdx, rdy = RIM_FIT
    return (f'<clipPath id="clip_ear_in_{side}"><path d="{inner}"/></clipPath>'
            f'<path d="{inner}" fill="#f7a67c"/>'
            f'<g clip-path="url(#clip_ear_in_{side})"><path d="{inner}" fill="{col["skin"]}" transform="translate({rdx} {rdy})"/>'
            + "".join(f'<path d="{smooth(p, True)}" fill="#ec8b62"/>' for p in e["orange_smooth"]) + '</g>')


EAR_P = dict(   # her left ear (viewer's right): every number fitted to the reference by the overlap score
    cx=315.8, cy=433.0, rx=16.0, ry=26.5, tilt=26.0, rim=3.5, open0=80.0, open1=205.0, rdx=0, rdy=0, fa0=-150.0,
    fa1=-40.0, fr=11.0, fw=3.0, ccx=-5.0, ccy=4.0, crx=5.0, cry=9.0, gx=-9.0, gy=12.0, grx=7.0, gry=14.0,
    lx0=314.75, ly0=381.5, lx1=296.75, ly1=446.0, lw=10.0, gapk=1.45, gapx=-6.0,
)


def ear_left_param(P=None):
    """Her left ear from clean shapes (oval with a dark rim that opens into the cheek, orange inner rim, fold arc and
    curl, soft glow, the hair lock beside it). All numbers in EAR_P are fitted to the reference."""
    import math
    p = dict(EAR_P, **(P or {}))
    rx, ry = p["rx"], p["ry"]
    t = f'translate({f(p["cx"])} {f(p["cy"])}) rotate({f(p["tilt"])})'
    wedge = [(0, 0)] + [(80 * math.cos(math.radians(a)), 80 * math.sin(math.radians(a)))
                        for a in np.linspace(p["open0"], p["open1"], 8)]
    wedge_d = "M" + " L".join(f"{f(x)},{f(y)}" for x, y in wedge) + " Z"
    fold = []
    for a in np.linspace(p["fa0"], p["fa1"], 7):
        fold.append((p["fr"] * math.cos(math.radians(a)), p["fr"] * 1.4 * math.sin(math.radians(a))))
    ear = f'<ellipse rx="{f(rx)}" ry="{f(ry)}"/>'
    lock = taper([(p["lx0"], p["ly0"]), ((p["lx0"] + p["lx1"]) / 2 + 1, (p["ly0"] + p["ly1"]) / 2), (p["lx1"], p["ly1"])],
                 p["lw"], "#452a1f")
    return (f'<g id="left_ear"><g transform="{t}">'
            f'<clipPath id="ce_ear">{ear}</clipPath>'
            f'<clipPath id="ce_rim"><path d="M-99,-99 H99 V99 H-99 Z {wedge_d}" clip-rule="evenodd"/></clipPath>'
            f'<clipPath id="ce_gap"><path d="{wedge_d}"/></clipPath>'
            f'<g clip-path="url(#ce_rim)"><ellipse rx="{f(rx + p["rim"])}" ry="{f(ry + p["rim"])}" fill="{H2["colours"]["outline"]}"/></g>'
            f'<g clip-path="url(#ce_gap)"><ellipse cx="{f(p.get("gapx", 0))}" rx="{f(rx + p["rim"] * p.get("gapk", 1))}" '
            f'ry="{f(ry + p["rim"] * p.get("gapk", 1))}" fill="{CF.C["skin"]}"/></g>'
            f'<g clip-path="url(#ce_ear)"><ellipse rx="{f(rx)}" ry="{f(ry)}" fill="#f7a67c"/>'
            f'<ellipse cx="{f(p["rdx"])}" cy="{f(p["rdy"])}" rx="{f(rx)}" ry="{f(ry)}" fill="{CF.C["skin"]}"/>'
            f'</g></g>'
            # orange shading traced from the reference (soft glow, then the deeper fold), clipped to the ear
            f'<g>'
            + "".join(f'<path d="{smooth(q, True)}" fill="#f9ae86"/>' for q in H2["ear_left_orange"]["glow"])
            + "".join(f'<path d="{smooth(q, True)}" fill="#ee8c60"/>' for q in H2["ear_left_orange"]["fold"])
            + f'</g>{lock}</g>')


def ear_left_cel():
    """Her left ear (viewer's right) traced colour by colour from the reference, the same way as the hair:
    dark outline, the hair lock beside it, skin, and all its orange shading (inner rim, fold, lower crease)."""
    e = H2["ear_left_cel"]
    col = e["colours"]
    region = smooth(e["region"], True)
    g = [f'<clipPath id="clip_ear_l_region"><path d="{region}"/></clipPath>',
         f'<g id="left_ear" clip-path="url(#clip_ear_l_region)">',
         f'<path d="{region}" fill="{col["outline"]}"/>']
    for name in ("hair", "skin", "orange", "fold"):
        g += [f'<path d="{smooth(p, True)}" fill="{col[name]}"/>' for p in e["layers"][name]]
    return "".join(g) + "</g>"


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
    wedge_pts = [(0, 0)] + [(60 * math.cos(math.radians(a)), 60 * math.sin(math.radians(a))) for a in range(80, 196, 8)]
    wedge = "M" + " L".join(f"{f(x)},{f(y)}" for x, y in wedge_pts) + " Z"
    rim_keep = "M-80,-80 L80,-80 L80,80 L-80,80 Z " + wedge
    crease = smooth([(-rx + 1.5, 4), (-rx + 3.5, 14), (-rx + 7.5, 23), (-rx + 6, 13), (-rx + 3.8, 3)], True)
    return (f'<g id="left_ear" transform="{t}">'
            f'<clipPath id="clip_ear_l"><ellipse rx="{rx}" ry="{ry}"/></clipPath>'
            f'<clipPath id="clip_ear_rim"><path d="{rim_keep}" clip-rule="evenodd"/></clipPath>'
            f'<clipPath id="clip_ear_gap"><path d="{wedge}"/></clipPath>'
            f'<g clip-path="url(#clip_ear_rim)">{band}</g>'
            f'<g clip-path="url(#clip_ear_gap)"><ellipse cx="-2" rx="{rx + 3}" ry="{ry + 3}" fill="{col["skin"]}"/></g>'
            f'</g>' + ear_traced("left"))


HEAD_S, HEAD_DX, HEAD_DY = 0.915, -6.25, -0.75   # head size / shift fitted to the full-body picture (head region overlap)
HEAD_PIVOT = (188.1, 469.5)                    # middle of the chin: the head scales around this point


def head_tf(svg):
    """The parts drawn from the head picture, scaled to the head size of the full-body picture."""
    px, py = HEAD_PIVOT
    return (f'<g transform="translate({f(px + HEAD_DX)},{f(py + HEAD_DY)}) scale({HEAD_S}) '
            f'translate({f(-px)},{f(-py)})">' + svg + "</g>")


def head_svg_v2(mouth_shape="smile", look=(0, 0), eyes="open", body=True):
    backing = "".join(f'<ellipse cx="{f(x)}" cy="{f(y)}" rx="9" ry="9" fill="{H2["colours"]["outline"]}"/>'
                      for x, y in from_new([(686, 684), (262, 684)]))   # dark behind the ear bottoms (no white specks)
    hb_under = ("".join(path(p, fill=HB["colours"]["outline"]) for p in HB["silhouette"])     # dark behind the head,
                + path(HB["face_fill"], fill=HB["colours"]["outline"])                          # so no white gaps anywhere
                + f'<rect x="135" y="490" width="110" height="40" fill="{HB["colours"]["outline"]}"/>') if HB else ""
    under = ("".join(path(p, fill=H2["colours"]["outline"]) for p in H2["silhouette"])     # no gaps at the face edge
             + f'<path d="{smooth(H2["face_fill"], True)}" fill="#f4a47c" stroke="#f4a47c" stroke-width="30" '
               f'stroke-linejoin="round" clip-path="url(#clip_ff_not_eyes2)"/>'
             + not_eyes_clip().replace("clip_hair_not_eyes", "clip_ff_not_eyes2"))
    face_fill = under + backing + not_eyes_clip().replace("clip_hair_not_eyes", "clip_ff_not_eyes") + (
                 f'<path d="{smooth(H2["face_fill"], True)}" fill="{CF.C["skin"]}" stroke="{H2["colours"]["outline"]}" '
                 f'stroke-width="14" stroke-linejoin="round" clip-path="url(#clip_ff_not_eyes)"/>'
                 f'<path d="{smooth(H2["face_fill"], True)}" fill="{CF.C["skin"]}"/>')
    blush = "".join(f'<ellipse cx="{x}" cy="459.5" rx="18.5" ry="13.5" fill="#febdaa" opacity=".5"/>'
                    f'<ellipse cx="{x}" cy="459.5" rx="17" ry="12.2" fill="#febdaa"/>' for x in (111, 266.5))
    eye_skin = "".join(f'<circle cx="{f(c[0])}" cy="{f(c[1])}" r="{f(c[2] + 9)}" fill="{CF.C["skin"]}"/>'
                       for c in (E.master_eye("right")[0], E.master_eye("left")[0]))
    import chibi_body as CB
    # the lower hair and the body come from the full-body picture (already the right size): not scaled
    neck_hole = smooth([(x, 495 if y < 508 else y) for x, y in CB.B["parts"]["neck"]["layers"]["skin"][0]], True)
    no_neck = (f'<clipPath id="clip_hair_not_neck"><path d="M-500,-500 H1000 V1500 H-500 Z {neck_hole}" '
               f'clip-rule="evenodd"/></clipPath>')   # the head picture's hair behind the neck: the body picture's neck wins
    return (hb_under + head_tf(face_fill) + CB.neck() + no_neck + '<g clip-path="url(#clip_hair_not_neck)">'
            + head_tf(hair_cel()) + "</g>" + hair_body_lower() + head_tf(crown_clean())
            + (CB.body() if body else "")
            + '<g id="face">' + head_tf(eye_skin + blush + CF.nose() + CF.mouth(mouth_shape) + E.eye("right", eyes, look)
                                        + E.eye("left", eyes, look) + E.brow("right") + E.brow("left") + ears_cel()) + "</g>")


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
