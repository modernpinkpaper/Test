"""Brand character, drawn as clean vector art from code.

    python girl_character.py            # writes girl_character.svg, girl_character_preview.png,
                                        # character_geometry.json next to this file

Every shape is built from a few landmark points turned into smooth cubic Bezier curves
(Catmull-Rom -> Bezier), plus circles/ellipses. No image tracing, no embedded bitmaps.

Coordinates: the drawing is built in "design units" (1 unit = 1 px of the 1024x1536 reference),
then placed on the 1200x1800 canvas with one transform on the `character` group.

Sides: "left_*" / "right_*" are the CHARACTER'S own left/right (like MediaPipe, Mixamo, CMU),
so her left arm is on the viewer's right.
"""
import json
import math
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))

# ----------------------------------------------------------------------------------------------
# Colours and line weights (defined once)
# ----------------------------------------------------------------------------------------------
COLORS = {
    "outline": "#1c1411",
    "skin": "#f7b07f",
    "skin_shadow": "#dc8c5e",
    "skin_light": "#fcc9a0",
    "blush": "#f08a7a",
    "lip": "#d46b60",
    "lip_light": "#e98a78",
    "lip_line": "#9c3f3a",
    "eye_white": "#fdfbf9",
    "eye_shade": "#e7dcd6",
    "iris": "#6b3a1d",
    "iris_dark": "#3a1c0c",
    "iris_light": "#9a5b2c",
    "pupil": "#1a0c06",
    "liner": "#150d0a",
    "brow": "#3b2418",
    "hair": "#5c321c",
    "hair_dark": "#331a0f",
    "hair_highlight": "#8a5230",
    "shirt": "#262427",
    "shirt_shadow": "#141315",
    "shirt_highlight": "#3d3a3f",
    "jeans": "#2f62a0",
    "jeans_shadow": "#224d85",
    "jeans_highlight": "#4c80c2",
    "jeans_stitch": "#8fb0d8",
    "metal": "#c9ccd3",
    "shoe": "#f6f6f7",
    "shoe_shadow": "#e4e5ea",
    "shoe_line": "#9a9ca6",
    "sole": "#ffffff",
    "background": "#ffffff",
}
STROKE = {"major": 3.0, "detail": 1.7, "fine": 1.1}

# ----------------------------------------------------------------------------------------------
# Landmarks (design units, measured from the reference) -- geometry below is built from these
# ----------------------------------------------------------------------------------------------
center_x = 500          # body centre line
face_x = 490            # face centre (head turned a touch to her right)
head_top = 14
hairline_y = 72
brow_y = 124
eye_y = 157
nose_y = 198
mouth_y = 218
chin_y = 257
shoulder_y = 312
bust_y = 440
waist_y = 562
hem_y = 610             # shirt hem (tucked under the waistband)
band_top_y = 603
band_bottom_y = 642
hip_y = 750
crotch_y = 782
knee_y = 1050
calf_y = 1140
ankle_y = 1355
jeans_hem_y = 1374
sole_y = 1525

JOINTS = {
    "neck": (center_x, 300),
    "left_shoulder": (640, 388), "right_shoulder": (360, 388),
    "left_elbow": (664, 655), "right_elbow": (336, 655),
    "left_wrist": (683, 845), "right_wrist": (317, 845),
    "left_hip": (575, 770), "right_hip": (425, 770),
    "left_knee": (556, knee_y), "right_knee": (444, knee_y),
    "left_ankle": (546, ankle_y), "right_ankle": (454, ankle_y),
}

CANVAS_W, CANVAS_H = 1200, 1800
SCALE = 1.1
OFFSET_X = CANVAS_W / 2 - center_x * SCALE
OFFSET_Y = (CANVAS_H - (sole_y - head_top) * SCALE) / 2 - head_top * SCALE


def to_canvas(p):
    return (round(OFFSET_X + p[0] * SCALE, 1), round(OFFSET_Y + p[1] * SCALE, 1))


def mirror(p, axis=center_x):
    """Mirror a point (or list of points) across the vertical line x = axis."""
    if isinstance(p[0], (int, float)):
        return (2 * axis - p[0], p[1])
    return [(2 * axis - x, y) for x, y in p]


# ----------------------------------------------------------------------------------------------
# SVG node tree (keeps the points of every shape so bounding boxes can be measured)
# ----------------------------------------------------------------------------------------------
def fmt(v):
    return f"{v:.1f}".rstrip("0").rstrip(".")


class Node:
    def __init__(self, tag, attrs=None, children=None, pts=None, text=None):
        self.tag, self.attrs, self.children = tag, attrs or {}, children or []
        self.pts, self.text = pts or [], text

    def all_pts(self):
        out = list(self.pts)
        for c in self.children:
            out += c.all_pts()
        return out

    def find(self, gid):
        if self.attrs.get("id") == gid:
            return self
        for c in self.children:
            r = c.find(gid)
            if r:
                return r
        return None

    def xml(self, depth=0):
        pad = "  " * depth
        attrs = "".join(f' {k.replace("_", "-")}="{v}"' for k, v in self.attrs.items() if v is not None)
        if not self.children and self.text is None:
            return f"{pad}<{self.tag}{attrs}/>"
        inner = self.text if self.text is not None else "\n" + "\n".join(c.xml(depth + 1) for c in self.children) + f"\n{pad}"
        return f"{pad}<{self.tag}{attrs}>{inner}</{self.tag}>"


def group(gid, *children, **attrs):
    return Node("g", {"id": gid, **attrs}, [c for c in children if c is not None])


# ----------------------------------------------------------------------------------------------
# Path helpers: smooth closed/open curves through landmark points, as cubic Beziers
# ----------------------------------------------------------------------------------------------
def smooth_segments(pts, closed=True, corners=(), tension=1 / 6):
    """Catmull-Rom through `pts`, returned as cubic Bezier segments (p0, c1, c2, p3).
    Indices in `corners` get sharp corners."""
    P = [np.array(p, float) for p in pts]
    n = len(P)
    segs = []
    for i in range(n if closed else n - 1):
        j = (i + 1) % n
        p1, p2 = P[i], P[j]
        p0 = P[i - 1] if (closed or i > 0) else p1
        p3 = P[(i + 2) % n] if (closed or i + 2 < n) else p2
        c1 = p1 + (p2 - p1) / 3 if i in corners else p1 + (p2 - p0) * tension
        c2 = p2 + (p1 - p2) / 3 if j in corners else p2 - (p3 - p1) * tension
        segs.append((p1, c1, c2, p2))
    return segs


def segs_to_d(segs, closed=False):
    if not segs:
        return ""
    d, last = [], None
    for p0, c1, c2, p3 in segs:
        if last is None or np.linalg.norm(p0 - last) > 1e-6:
            d.append(f"M{fmt(p0[0])},{fmt(p0[1])}")
        d.append(f"C{fmt(c1[0])},{fmt(c1[1])} {fmt(c2[0])},{fmt(c2[1])} {fmt(p3[0])},{fmt(p3[1])}")
        last = p3
    return " ".join(d) + (" Z" if closed else "")


def bezier_samples(segs, n=12):
    out = []
    for p0, c1, c2, p3 in segs:
        for t in np.linspace(0, 1, n):
            u = 1 - t
            out.append(tuple(u ** 3 * p0 + 3 * u * u * t * c1 + 3 * u * t * t * c2 + t ** 3 * p3))
    return out


def path(segs, fill="none", stroke=None, width=None, closed=True, gid=None, **extra):
    attrs = {"id": gid, "d": segs_to_d(segs, closed), "fill": fill}
    if stroke:
        attrs.update(stroke=stroke, stroke_width=fmt(width or STROKE["major"]),
                     stroke_linejoin="round", stroke_linecap="round")
    attrs.update(extra)
    return Node("path", attrs, pts=bezier_samples(segs))


def shape(pts, fill, stroke=True, width=None, corners=(), tension=1 / 6, gid=None, **extra):
    """Closed smooth shape through landmark points, filled and (optionally) outlined."""
    return path(smooth_segments(pts, True, corners, tension), fill, COLORS["outline"] if stroke else None,
                width, True, gid, **extra)


def curve(pts, color=None, width=None, corners=(), tension=1 / 6, gid=None, **extra):
    """Open stroke through points (detail lines, creases, seams)."""
    return path(smooth_segments(pts, False, corners, tension), "none", color or COLORS["outline"],
                width or STROKE["detail"], False, gid, **extra)


def outlined(pts, fill, stroke_segments, corners=(), tension=1 / 6, width=None, gid=None):
    """Filled shape where only some edges are outlined (e.g. where a part tucks under another)."""
    segs = smooth_segments(pts, True, corners, tension)
    fill_node = path(segs, fill)
    parts = [segs[i] for i in stroke_segments]
    line = path(parts, "none", COLORS["outline"], width, closed=False)
    return group(gid, fill_node, line) if gid else Node("g", {}, [fill_node, line])


def ellipse(c, rx, ry, fill, stroke=None, width=None, gid=None, **extra):
    attrs = {"id": gid, "cx": fmt(c[0]), "cy": fmt(c[1]), "rx": fmt(rx), "ry": fmt(ry), "fill": fill}
    if stroke:
        attrs.update(stroke=stroke, stroke_width=fmt(width or STROKE["detail"]))
    attrs.update(extra)
    return Node("ellipse", attrs, pts=[(c[0] - rx, c[1] - ry), (c[0] + rx, c[1] + ry)])


def circle(c, r, fill, **kw):
    return ellipse(c, r, r, fill, **kw)


def tube(points, widths, start="round", end="round", tension=1 / 6):
    """Tapered limb/strand along points. Returns (all segments, segments without the start cap)
    so a limb can be outlined everywhere except where it tucks under its parent."""
    P = np.array(points, float)
    n = len(P)
    tang = [P[min(i + 1, n - 1)] - P[max(i - 1, 0)] for i in range(n)]
    tang = [t / (np.linalg.norm(t) + 1e-9) for t in tang]
    norm = [np.array([-t[1], t[0]]) for t in tang]
    left = [P[i] + norm[i] * widths[i] / 2 for i in range(n)]
    right = [P[i] - norm[i] * widths[i] / 2 for i in range(n)]

    def cap(i, direction):
        r, t, m = widths[i] / 2, tang[i] * direction, norm[i]
        side = 1 if direction > 0 else -1
        return [P[i] + (t * .72 + m * .72 * side) * r, P[i] + t * r, P[i] + (t * .72 - m * .72 * side) * r]

    pts, corners = list(left), set()
    if end == "round":
        pts += cap(n - 1, 1)
    else:
        corners |= {n - 1, n}
    k = len(pts)
    pts += right[::-1]
    if start == "round":
        start_cap = cap(0, -1)
        pts += start_cap
        n_start = len(start_cap) + 1
    else:
        corners |= {len(pts) - 1, 0}
        n_start = 1
    segs = smooth_segments(pts, True, corners, tension)
    return segs, segs[:-n_start], k


def limb(points, widths, fill, start="round", end="round", gid=None, stroke_start=False):
    segs, no_start, _ = tube(points, widths, start, end)
    fill_node = path(segs, fill)
    line = path(segs if stroke_start else no_start, "none", COLORS["outline"], STROKE["major"], closed=stroke_start)
    return group(gid, fill_node, line) if gid else Node("g", {}, [fill_node, line])


def strand(points, width, color, opacity=1.0):
    """Thin tapered lens shape for hair highlights / shadows."""
    n = len(points)
    widths = [max(0.6, width * math.sin(math.pi * (i + 0.5) / n) ** 0.8) for i in range(n)]
    widths[0] = widths[-1] = 0.6
    segs, _, _ = tube(points, widths)
    return path(segs, color, opacity=fmt(opacity))


def xform(origin, angle_deg, flip=False, scale=1.0):
    """Returns f(local point) -> design point: rotate, optional mirror in x, then translate."""
    a = math.radians(angle_deg)
    ca, sa = math.cos(a), math.sin(a)

    def f(p):
        x, y = p[0] * scale * (-1 if flip else 1), p[1] * scale
        return (origin[0] + x * ca - y * sa, origin[1] + x * sa + y * ca)
    return f


def mapped(f, pts):
    return [f(p) for p in pts]


# ----------------------------------------------------------------------------------------------
# Hair
# ----------------------------------------------------------------------------------------------
def lock(pts, tip, gid, fill=None):
    """A hair lock: closed smooth shape, outlined everywhere except its root (the segment from the last
    point back to the first), so it blends into the hair it grows from. `tip` = index of the pointed end."""
    return outlined(pts, fill or COLORS["hair"], range(0, len(pts) - 1), corners=(tip,), gid=gid)


def draw_hair_back():
    back = shape([
        (488, head_top), (545, 20), (578, 50), (592, 100), (602, 160), (612, 230), (624, 300),
        (632, 360), (628, 440), (620, 510), (612, 552), (596, 540), (560, 480), (470, 470),
        (420, 520), (360, 540), (300, 500), (270, 440), (275, 350), (300, 250), (322, 160),
        (350, 90), (390, 44), (435, 22)], "url(#hairBack)", gid="hair_back_mass")
    shadow = strand([(592, 120), (600, 220), (612, 320), (614, 420), (606, 520)], 14, COLORS["hair_dark"], .8)
    lights = [strand([(578, 70), (590, 150), (597, 240), (606, 320)], 7, COLORS["hair_highlight"], .7),
              strand([(612, 360), (612, 440), (606, 520)], 5, COLORS["hair_highlight"], .5)]
    return group("hair_back", back, shadow, *lights)


def wavy(center, amp, phase=0.0, freq=1.25):
    """Offset a centre line sideways by a sine wave (ends stay put), for flowing hair."""
    P = np.array(center, float)
    out = [tuple(P[0])]
    for i in range(1, len(P) - 1):
        t = P[i + 1] - P[i - 1]
        nrm = np.array([-t[1], t[0]]) / (np.linalg.norm(t) + 1e-9)
        out.append(tuple(P[i] + nrm * amp * math.sin(phase + i * freq)))
    return out + [tuple(P[-1])]


def offset_line(center, widths, k):
    """Points shifted sideways by k * local width (k in -0.5..0.5), for strands inside a lock."""
    P = np.array(center, float)
    out = []
    for i in range(len(P)):
        t = P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]
        nrm = np.array([-t[1], t[0]]) / (np.linalg.norm(t) + 1e-9)
        out.append(tuple(P[i] + nrm * widths[i] * k))
    return out


def flowing_lock(center, widths, gid, amp=6, phase=0.0):
    """A long hair lock built along a wavy centre line: tapered tube, root unoutlined, pointed tip,
    plus one highlight and one shadow strand that follow the same flow."""
    c = wavy(center, amp, phase)
    segs, no_start, _ = tube(c, widths, start="flat", end="round")
    body = path(segs, COLORS["hair"])
    line = path(no_start, "none", COLORS["outline"], STROKE["major"], closed=False)
    n = len(c)
    hi = offset_line(c[1:-1], widths[1:-1], 0.16)
    lo = offset_line(c[1:-1], widths[1:-1], -0.28)
    shine = strand(hi, max(widths) * 0.2, COLORS["hair_highlight"], .75)
    shadow = strand(lo, max(widths) * 0.13, COLORS["hair_dark"], .6)
    return group(gid, body, shadow, shine, line)


def draw_hair_front():
    L, D = COLORS["hair_highlight"], COLORS["hair_dark"]
    crown = lock([(420, 150), (360, 160), (342, 116), (358, 70), (400, 34), (450, 15), (500, 11), (538, 22),
                  (534, 34), (510, 54), (474, 76), (444, 100), (428, 124)], 7, "lock_crown")
    part_right = lock([(547, 46), (540, 22), (575, 36), (597, 80), (606, 150), (613, 220), (622, 292), (604, 252),
                       (590, 200), (579, 150), (567, 110), (556, 76)], 6, "lock_part_right")
    locks = [
        flowing_lock([(404, 62), (346, 124), (306, 200), (290, 270), (270, 340), (252, 410), (248, 470), (264, 524)],
                     [50, 66, 70, 64, 56, 46, 30, 3], "lock_outer", amp=7, phase=0.3),
        flowing_lock([(318, 290), (290, 360), (272, 420), (274, 486), (296, 550)],
                     [30, 40, 40, 30, 3], "lock_flick", amp=6, phase=1.0),
        flowing_lock([(414, 112), (374, 168), (350, 240), (336, 310), (318, 380), (308, 450), (322, 512), (350, 558)],
                     [44, 56, 58, 56, 52, 44, 30, 3], "lock_middle", amp=8, phase=1.6),
        flowing_lock([(400, 200), (372, 262), (358, 332), (346, 402), (350, 466), (374, 534)],
                     [30, 40, 42, 40, 32, 3], "lock_wave", amp=6, phase=2.4),
        flowing_lock([(414, 118), (390, 180), (386, 240), (402, 300), (420, 362), (418, 432), (408, 500), (422, 574)],
                     [34, 40, 44, 46, 46, 42, 32, 3], "lock_face_frame", amp=5, phase=0.8),
    ]
    shine = group("hair_front_highlights",
                  strand([(512, 22), (470, 30), (430, 48), (400, 80)], 9, L, .85),
                  strand([(495, 40), (460, 56), (432, 80)], 5, L, .7),
                  strand([(562, 40), (584, 90), (596, 160), (604, 230)], 5, L, .7))
    shade = group("hair_front_shadows",
                  strand([(404, 40), (380, 90), (366, 140)], 9, D, .5),
                  strand([(560, 60), (582, 120), (594, 200), (604, 270)], 7, D, .5))
    loose = group("hair_front_loose_strands",
                  curve([(338, 520), (348, 548), (366, 562)], D, STROKE["detail"]),
                  curve([(318, 150), (300, 200), (292, 250)], COLORS["outline"], STROKE["fine"]),
                  curve([(286, 300), (270, 340), (258, 372)], COLORS["outline"], STROKE["fine"]),
                  curve([(252, 440), (246, 480), (258, 512)], COLORS["outline"], STROKE["fine"]))
    return group("hair_front", crown, part_right, shade, shine, *locks, loose)


# ----------------------------------------------------------------------------------------------
# Head
# ----------------------------------------------------------------------------------------------
def draw_ear(side):
    if side == "right":          # her right ear = viewer's left
        pts = [(422, 158), (410, 150), (401, 162), (403, 186), (413, 203), (425, 206)]
        inner = [(417, 166), (409, 172), (411, 188), (418, 196)]
    else:
        pts = [(555, 150), (566, 138), (574, 148), (572, 172), (563, 190), (551, 196)]
        inner = [(560, 156), (567, 160), (565, 176), (558, 184)]
    return group(f"{side}_ear", outlined(pts, COLORS["skin"], range(0, 5)),
                 curve(inner, COLORS["skin_shadow"], STROKE["detail"]))


def draw_face():
    outline = [(424, 92), (418, 140), (420, 182), (431, 214), (451, 237), (475, 252), (497, 258),
               (519, 250), (538, 229), (551, 197), (558, 160), (559, 116), (548, 84), (495, 68), (440, 76)]
    skin = shape(outline, COLORS["skin"], gid="face_shape")
    side_shade = shape([(424, 110), (420, 160), (426, 204), (446, 234), (470, 250), (452, 226), (438, 196),
                        (432, 150), (436, 112)], COLORS["skin_shadow"], stroke=False, opacity=".35")
    hair_shadow = shape([(430, 80), (500, 66), (548, 82), (556, 104), (520, 92), (470, 94), (440, 110)],
                        COLORS["skin_shadow"], stroke=False, opacity=".45")
    blush = [ellipse((446, 195), 22, 12, "url(#blush)"), ellipse((536, 188), 20, 11, "url(#blush)")]
    return group("face", skin, side_shade, hair_shadow, *blush)


CLIP_PATHS = []   # clip paths are collected here and written once into the top-level <defs>


def draw_eye(side):
    """side = 'right' (her right, viewer left) or 'left'. Built in local units around the eye centre."""
    c = (450, eye_y + 3) if side == "right" else (523, eye_y - 3)
    f = xform(c, -4 if side == "right" else 3, flip=(side == "right"), scale=1.1)
    gid = f"{side}_eye"
    white_pts = [(-21, 4), (-11, -12), (8, -14), (22, -1), (11, 12), (-8, 14)]
    white_segs = smooth_segments(mapped(f, white_pts), True, corners=(0, 3))
    clip_id = f"clip_{gid}"
    clip = Node("clipPath", {"id": clip_id}, [path(white_segs)])
    iris_c = f((0, 1))
    iris = group(f"{gid}_iris",
                 circle(iris_c, 14.5, "url(#iris)", stroke=COLORS["iris_dark"], width=1.4),
                 circle(f((0, 1.5)), 6.2, COLORS["pupil"]),
                 circle(f((4, -3.5)), 3.4, "#ffffff"),
                 circle(f((-4, 5)), 1.6, "#ffffff", opacity=".85"),
                 clip_path=f"url(#{clip_id})")
    lid_shade = path(smooth_segments(mapped(f, [(-21, 4), (-11, -12), (8, -14), (22, -1), (8, -6), (-10, -4)]),
                                     True, corners=(0, 3)), COLORS["eye_shade"], clip_path=f"url(#{clip_id})")
    white = path(white_segs, COLORS["eye_white"])
    liner = shape(mapped(f, [(-24, 6), (-14, -17), (8, -20), (25, -5), (36, -14), (29, 1), (22, 1),
                             (8, -13), (-11, -11), (-21, 4)]), COLORS["liner"], stroke=False, corners=(0, 4, 9))
    lower = curve(mapped(f, [(-17, 10), (-4, 15), (10, 13), (21, 2)]), COLORS["iris_dark"], STROKE["fine"] + .4)
    lashes = [strand(mapped(f, [(x0, y0), (x0 + dx * .5, y0 + dy * .6), (x0 + dx, y0 + dy)]), 3.2, COLORS["liner"])
              for x0, y0, dx, dy in [(4, -17, 3, -8), (12, -14, 5, -7), (19, -10, 7, -5), (-4, -16, 0, -6)]]
    lower_lashes = [curve(mapped(f, [(x, y), (x + 3, y + 5)]), COLORS["liner"], 1.2)
                    for x, y in [(14, 10), (19, 6)]]
    crease = curve(mapped(f, [(-16, -19), (-2, -25), (14, -23), (24, -15)]), COLORS["skin_shadow"], STROKE["fine"] + .3)
    CLIP_PATHS.append(clip)
    return group(gid, white, lid_shade, iris, liner, lower, *lashes, *lower_lashes, crease)


def draw_eyebrow(side):
    if side == "right":
        pts = [(473, 118), (456, 108), (437, 107), (423, 112), (413, 124), (430, 122), (446, 121), (460, 125), (472, 131)]
    else:
        pts = [(501, 116), (518, 105), (537, 102), (552, 107), (563, 121), (547, 117), (531, 116), (515, 121), (502, 129)]
    return group(f"{side}_eyebrow", shape(pts, COLORS["brow"], stroke=False, corners=(0, 4, 8)))


def draw_nose():
    return group("nose",
                 shape([(484, 132), (478, 160), (474, 186), (476, 194), (481, 176), (486, 150)], COLORS["skin_shadow"],
                       stroke=False, opacity=".55"),
                 shape([(474, 196), (480, 203), (490, 205), (500, 202), (492, 207), (480, 207)],
                       COLORS["skin_shadow"], stroke=False, opacity=".5"),
                 curve([(474, 194), (478, 202), (486, 204), (492, 203)], COLORS["outline"], STROKE["detail"]),
                 curve([(497, 199), (502, 196)], COLORS["outline"], STROKE["fine"] + .3),
                 ellipse((490, 193), 4, 2.4, COLORS["skin_light"], opacity=".8"))


def draw_mouth():
    upper = shape([(462, 216), (474, 210), (486, 209), (491, 212), (497, 209), (508, 210), (518, 214),
                   (505, 217), (490, 218), (475, 217)], COLORS["lip"], stroke=False, corners=(0, 6))
    lower = shape([(465, 218), (490, 219), (515, 216), (508, 226), (490, 231), (472, 227)],
                  COLORS["lip_light"], stroke=False, corners=(0, 2))
    shine = ellipse((493, 224), 8, 2.4, "#ffffff", opacity=".35")
    line = curve([(460, 215), (474, 218), (490, 219), (506, 218), (520, 212)], COLORS["lip_line"], STROKE["detail"])
    corners = [curve([(457, 212), (461, 216)], COLORS["lip_line"], STROKE["fine"]),
               curve([(523, 209), (520, 213)], COLORS["lip_line"], STROKE["fine"])]
    under = curve([(482, 237), (492, 239), (500, 237)], COLORS["skin_shadow"], STROKE["fine"] + .3)
    return group("mouth", upper, lower, shine, line, *corners, under)


def draw_head():
    return group("head",
                 draw_face(),
                 draw_ear("left"), draw_ear("right"),
                 draw_nose(),
                 group("eyes", draw_eye("left"), draw_eye("right")),
                 group("eyebrows", draw_eyebrow("left"), draw_eyebrow("right")),
                 draw_mouth())


# ----------------------------------------------------------------------------------------------
# Body
# ----------------------------------------------------------------------------------------------
def draw_neck():
    skin = shape([(470, 228), (469, 272), (460, 296), (425, 308), (420, 400), (580, 400), (575, 308),
                  (542, 296), (533, 272), (532, 228)], COLORS["skin"], stroke=False, corners=(0, 9))
    shadow = shape([(470, 232), (484, 262), (500, 270), (518, 262), (532, 232)], COLORS["skin_shadow"],
                   stroke=False, opacity=".85")
    sides = [curve([(470, 236), (469, 272), (456, 298)]), curve([(532, 236), (533, 272), (546, 298)])]
    collar = [curve([(452, 322), (468, 330), (486, 334)], COLORS["skin_shadow"], STROKE["detail"]),
              curve([(548, 322), (532, 330), (514, 334)], COLORS["skin_shadow"], STROKE["detail"])]
    chest = curve([(492, 366), (498, 380), (500, 392)], COLORS["skin_shadow"], STROKE["detail"])
    return group("neck", skin, shadow, *sides, *collar, chest)


def draw_torso():
    cx = center_x
    right_side = [(398, 316), (374, 346), (372, 400), (380, 446), (394, 494), (410, 536), (416, waist_y),
                  (408, 588), (398, hem_y)]
    left_side = mirror(right_side[::-1])
    neckline = [(560, 302), (548, 340), (526, 376), (cx, 390), (474, 376), (452, 340), (440, 302)]
    pts = [(440, 302)] + right_side + [(cx, hem_y + 4)] + left_side + neckline[:-1]
    hem_r, hem_l = pts.index((398, hem_y)), pts.index(mirror((398, hem_y)))
    shirt = shape(pts, COLORS["shirt"], corners=(0, hem_r, hem_l, pts.index((560, 302))), gid="shirt")
    trim = curve(neckline, COLORS["shirt_shadow"], 5)
    underbust = shape([(396, 478), (440, 506), (500, 512), (560, 506), (606, 478), (600, 506),
                       (556, 528), (500, 534), (444, 528), (400, 506)], COLORS["shirt_shadow"], stroke=False,
                      opacity=".45")
    bust = [ellipse((452, 430), 40, 28, "url(#shirtShine)", opacity=".55"), ellipse((548, 430), 40, 28, "url(#shirtShine)", opacity=".55")]
    side_shade = shape([(600, 520), (586, waist_y), (596, 600), (574, 600), (570, waist_y), (582, 524)],
                       COLORS["shirt_shadow"], stroke=False, opacity=".6")
    folds = [curve([(430, 560), (470, 572), (500, 574)], COLORS["shirt_highlight"], STROKE["detail"], opacity=".8"),
             curve([(520, 580), (556, 574), (578, 562)], COLORS["shirt_highlight"], STROKE["detail"], opacity=".7")]
    return group("torso", shirt, underbust, *bust, side_shade, *folds, trim)


def draw_upper_arm(side):
    s = 1 if side == "left" else -1
    sh, el = JOINTS[f"{side}_shoulder"], JOINTS[f"{side}_elbow"]
    mid = (center_x + s * 148, 520)
    arm = limb([sh, mid, el], [58, 56, 50], COLORS["skin"], gid=f"{side}_upper_arm_skin")
    inner_shade = curve([(center_x + s * 125, 450), (center_x + s * 128, 540), (center_x + s * 140, 620)],
                        COLORS["skin_shadow"], 5, opacity=".45")
    sleeve_pts = [(598, 304), (640, 312), (668, 334), (683, 370), (690, 412), (656, 428), (624, 444),
                  (612, 420), (606, 360)]
    if side == "right":
        sleeve_pts = mirror(sleeve_pts)
    sleeve = outlined(sleeve_pts, COLORS["shirt"], range(0, 6), corners=(4, 6), gid=f"{side}_sleeve")
    sleeve_shade = shape([(center_x + s * (x - center_x), y) for x, y in
                          [(660, 390), (684, 400), (688, 410), (656, 424), (628, 438), (640, 416)]],
                         COLORS["shirt_highlight"], stroke=False, opacity=".5")
    return group(f"{side}_upper_arm", arm, inner_shade, sleeve, sleeve_shade)


def draw_forearm(side):
    s = 1 if side == "left" else -1
    el, wr = JOINTS[f"{side}_elbow"], JOINTS[f"{side}_wrist"]
    mid = (center_x + s * 175, 750)
    arm = limb([el, mid, wr], [50, 49, 38], COLORS["skin"], gid=f"{side}_forearm_skin")
    shade = curve([(center_x + s * 152, 690), (center_x + s * 164, 780), (center_x + s * 170, 830)],
                  COLORS["skin_shadow"], 4, opacity=".4")
    return group(f"{side}_forearm", arm, shade)


def draw_hand(side):
    """Relaxed hand hanging at the side, palm toward the thigh. Local frame: wrist at (0, 0), fingers
    point +y, the thumb side (toward her body) is -x before mirroring."""
    el, wr = JOINTS[f"{side}_elbow"], JOINTS[f"{side}_wrist"]
    ang = math.degrees(math.atan2(-(wr[0] - el[0]), wr[1] - el[1]))
    f = xform(wr, ang, flip=(side == "right"), scale=1.1)
    fingers = []
    for i, (bx, length, curl, w) in enumerate([(-9, 38, -9, 10), (-3, 44, -9, 10.5), (4, 42, -8, 10), (10, 34, -6, 9)]):
        pts = mapped(f, [(bx, 46), (bx + curl * .2, 46 + length * .55), (bx + curl, 46 + length)])
        fingers.append(limb(pts, [w, w * .95, w * .8], COLORS["skin"], start="flat", gid=f"{side}_finger_{i + 1}"))
    palm = shape(mapped(f, [(-16, -6), (-17, 18), (-14, 44), (-6, 52), (6, 52), (14, 44), (16, 18), (16, -6)]),
                 COLORS["skin"], gid=f"{side}_palm")
    knuckles = curve(mapped(f, [(-10, 50), (0, 53), (12, 50)]), COLORS["skin_shadow"], STROKE["fine"] + .4)
    thumb = limb(mapped(f, [(-13, 14), (-22, 36), (-21, 58)]), [14, 11.5, 10], COLORS["skin"], start="flat",
                 gid=f"{side}_thumb")
    nail = ellipse(f((-21, 60)), 3, 4.5, COLORS["skin_light"], stroke=COLORS["skin_shadow"], width=.8)
    return group(f"{side}_hand", *fingers[::-1], palm, knuckles, thumb, nail)


def draw_hips():
    cx = center_x
    right = [(392, band_top_y), (372, 650), (356, 700), (347, hip_y), (350, 774), (362, 800)]
    pts = right + [(cx, 800)] + mirror(right[::-1])
    body = outlined(pts, "url(#jeansHips)", list(range(0, 4)) + list(range(9, 13)), corners=(0, 5, 6, 7, 12),
                    gid="hips_shape")
    crotch_shadow = shape([(446, 722), (474, 744), (cx, 776), (526, 744), (554, 722), (528, 748), (cx, 768),
                           (472, 748)], COLORS["jeans_shadow"], stroke=False, opacity=".55")
    band_pts = [(392, band_top_y), (cx, band_top_y + 4), (608, band_top_y), (606, band_bottom_y - 2),
                (cx, band_bottom_y + 2), (394, band_bottom_y - 2)]
    band = shape(band_pts, COLORS["jeans"], corners=(0, 2, 3, 5), tension=1 / 5, gid="waistband")
    stitch = dict(stroke_dasharray="5 4")
    band_stitch = curve([(396, band_bottom_y - 7), (cx, band_bottom_y - 3), (604, band_bottom_y - 7)],
                        COLORS["jeans_stitch"], STROKE["fine"], **stitch)
    loops = [shape([(x - 5, band_top_y - 2), (x + 5, band_top_y - 2), (x + 5, band_bottom_y + 3),
                    (x - 5, band_bottom_y + 3)], COLORS["jeans"], corners=(0, 1, 2, 3), width=STROKE["detail"])
             for x in (408, 452, 548, 592)]
    button = group("button", circle((505, 622), 8.5, COLORS["metal"], stroke=COLORS["outline"], width=STROKE["detail"]),
                   circle((505, 622), 3.5, "#9ea3ad"))
    fly = curve([(507, band_bottom_y + 2), (507, 700), (504, 722), (494, 728)], COLORS["jeans_shadow"], STROKE["detail"])
    fly_stitch = curve([(519, band_bottom_y + 2), (519, 702), (514, 726), (500, 734)], COLORS["jeans_stitch"],
                       STROKE["fine"], **stitch)
    seam = curve([(494, 728), (cx, 752), (cx, crotch_y)], COLORS["jeans_shadow"], STROKE["detail"])
    pockets = []
    for s in (1, -1):
        p = [(cx - s * 48, band_bottom_y), (cx - s * 64, 668), (cx - s * 96, 688), (cx - s * 128, 690)]
        pockets += [curve(p, COLORS["outline"], STROKE["detail"]),
                    curve([(x + s * 6, y + 6) for x, y in p[:-1]] + [(p[-1][0] + s * 4, p[-1][1] + 7)],
                          COLORS["jeans_stitch"], STROKE["fine"], **stitch)]
    whiskers = [curve([(cx - s * 14, 752), (cx - s * 40, 742), (cx - s * 66, 744)], COLORS["jeans_shadow"],
                      STROKE["detail"], opacity=".8") for s in (1, -1)]
    return group("hips", body, crotch_shadow, band, band_stitch, *loops, button, fly, fly_stitch, seam, *pockets, *whiskers)


def draw_thigh(side):
    s = 1 if side == "left" else -1
    hip, knee = JOINTS[f"{side}_hip"], JOINTS[f"{side}_knee"]
    mid = (center_x + s * 66, 900)
    leg = limb([hip, mid, knee], [150, 118, 90], "url(#jeansLeg)", start="flat", end="round",
               gid=f"{side}_thigh_shape")
    shine = strand([(hip[0] - s * 30, 800), (mid[0] - s * 26, 900), (knee[0] - s * 16, 1010)], 12,
                   COLORS["jeans_highlight"], .45)
    crease = curve([(center_x + s * 8, 792), (center_x + s * 34, 800), (center_x + s * 50, 812)],
                   COLORS["jeans_shadow"], STROKE["detail"])
    return group(f"{side}_thigh", leg, shine, crease)


def draw_lower_leg(side):
    s = 1 if side == "left" else -1
    knee, ankle = JOINTS[f"{side}_knee"], JOINTS[f"{side}_ankle"]
    calf, shin = (center_x + s * 68, calf_y), (center_x + s * 57, 1240)
    skin = limb([(ankle[0], ankle_y - 10), (ankle[0], jeans_hem_y + 30)], [40, 38], COLORS["skin"])
    leg = limb([knee, calf, shin, (ankle[0], jeans_hem_y)], [92, 102, 76, 60], "url(#jeansLeg)", start="flat",
               end="flat", gid=f"{side}_lower_leg_shape")
    knee_lines = [curve([(knee[0] - 24, knee[1] + 4), (knee[0], knee[1] + 12), (knee[0] + 22, knee[1] + 2)],
                        COLORS["jeans_shadow"], STROKE["detail"]),
                  curve([(knee[0] - 16, knee[1] + 22), (knee[0] + 2, knee[1] + 28), (knee[0] + 16, knee[1] + 20)],
                        COLORS["jeans_shadow"], STROKE["fine"] + .4)]
    bunch = [curve([(ankle[0] - 28, y), (ankle[0], y + 5), (ankle[0] + 28, y - 2)], COLORS["jeans_shadow"],
                   STROKE["detail"]) for y in (1318, 1340)]
    shine = strand([(calf[0] - s * 30, 1090), (calf[0] - s * 34, 1160), (shin[0] - s * 24, 1260)], 10,
                   COLORS["jeans_highlight"], .4)
    return group(f"{side}_lower_leg", skin, leg, shine, *knee_lines, *bunch)


def draw_shoe(side):
    """White low-top sneaker seen from the front, toes turned slightly out.
    Local frame: top of the collar at (0, 0), sole bottom at y = 132."""
    ankle = JOINTS[f"{side}_ankle"]
    f = xform((ankle[0], jeans_hem_y + 18), -5 if side == "left" else 5, flip=(side == "right"))
    line = COLORS["shoe_line"]
    upper = shape(mapped(f, [(-30, 6), (-40, 30), (-50, 62), (-55, 95), (0, 104), (55, 95), (50, 62), (40, 30),
                             (30, 6)]), "url(#shoe)")
    collar = shape(mapped(f, [(-30, 6), (0, -2), (30, 6), (22, 14), (0, 10), (-22, 14)]), COLORS["shoe_shadow"],
                   width=STROKE["detail"])
    tongue = shape(mapped(f, [(-15, 6), (-13, -6), (0, -10), (13, -6), (15, 6), (14, 58), (-14, 58)]),
                   COLORS["shoe"], width=STROKE["detail"], corners=(5, 6))
    rows = [14, 24, 34, 44, 54]
    laces = []
    for i, y in enumerate(rows[:-1]):                       # criss-cross laces
        for a_, b_ in (((-20, y), (20, rows[i + 1])), ((20, y), (-20, rows[i + 1]))):
            laces.append(curve(mapped(f, [a_, b_]), line, 4.4))
            laces.append(curve(mapped(f, [a_, b_]), COLORS["sole"], 2.6))
    eyelets = [circle(f((x, y)), 2.1, line) for y in rows for x in (-21, 21)]
    toe = curve(mapped(f, [(-46, 80), (0, 72), (46, 80)]), line, STROKE["detail"])
    dots = [circle(f((x, y)), 1.3, line) for x, y in [(-14, 84), (-4, 82), (6, 82), (16, 84), (-9, 90), (1, 89), (11, 90)]]
    panels = [curve(mapped(f, [(-26 * k, 14), (-34 * k, 46), (-30 * k, 72)]), line, STROKE["fine"] + .3) for k in (1, -1)]
    sole = shape(mapped(f, [(-58, 92), (0, 98), (58, 92), (60, 112), (50, 128), (0, 132), (-50, 128), (-60, 112)]),
                 COLORS["sole"], corners=(0, 2))
    sole_line = curve(mapped(f, [(-57, 114), (0, 120), (57, 114)]), line, STROKE["fine"] + .3)
    return group(f"{side}_shoe", upper, collar, tongue, *laces, *eyelets, toe, *dots, *panels, sole, sole_line)


def draw_body():
    return group("body",
                 draw_neck(),
                 draw_torso(),
                 draw_hips(),
                 draw_thigh("left"), draw_lower_leg("left"),
                 draw_thigh("right"), draw_lower_leg("right"),
                 draw_shoe("left"), draw_shoe("right"),
                 draw_upper_arm("left"), draw_forearm("left"), draw_hand("left"),
                 draw_upper_arm("right"), draw_forearm("right"), draw_hand("right"))


# ----------------------------------------------------------------------------------------------
# Gradients
# ----------------------------------------------------------------------------------------------
def defs():
    C = COLORS

    def lin(gid, stops, x2="0", y2="1", x1="0", y1="0"):
        return (f'<linearGradient id="{gid}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">'
                + "".join(f'<stop offset="{o}" stop-color="{c}"{f" stop-opacity={chr(34)}{a}{chr(34)}" if a is not None else ""}/>'
                          for o, c, a in stops) + "</linearGradient>")

    def rad(gid, stops):
        return (f'<radialGradient id="{gid}" cx=".5" cy=".5" r=".5">'
                + "".join(f'<stop offset="{o}" stop-color="{c}" stop-opacity="{a}"/>' for o, c, a in stops)
                + "</radialGradient>")
    text = "\n    ".join([
        lin("hairBack", [(0, C["hair"], None), (1, C["hair_dark"], None)]),
        lin("jeansLeg", [(0, C["jeans_shadow"], None), (.35, C["jeans"], None), (.75, C["jeans"], None),
                         (1, C["jeans_shadow"], None)], x2="1", y2="0"),
        lin("jeansHips", [(0, C["jeans_shadow"], None), (.3, C["jeans"], None), (.7, C["jeans"], None),
                          (1, C["jeans_shadow"], None)], x2="1", y2="0"),
        lin("shoe", [(0, C["shoe"], None), (.6, C["shoe"], None), (1, C["shoe_shadow"], None)]),
        rad("blush", [(0, C["blush"], .45), (1, C["blush"], 0)]),
        rad("shirtShine", [(0, C["shirt_highlight"], .9), (1, C["shirt_highlight"], 0)]),
        '<radialGradient id="iris" cx=".5" cy=".62" r=".6"><stop offset="0" stop-color="{}"/>'
        '<stop offset=".6" stop-color="{}"/><stop offset="1" stop-color="{}"/></radialGradient>'.format(
            C["iris_light"], C["iris"], C["iris_dark"]),
    ])
    return Node("defs", {}, text=text + "\n" + "\n".join(c.xml(2) for c in CLIP_PATHS))


# ----------------------------------------------------------------------------------------------
# Build, save, measure
# ----------------------------------------------------------------------------------------------
def build():
    CLIP_PATHS.clear()
    character = group("character",
                      draw_hair_back(), draw_body(), draw_head(), draw_hair_front(),
                      transform=f"translate({fmt(OFFSET_X)} {fmt(OFFSET_Y)}) scale({SCALE})")
    root = Node("svg", {"xmlns": "http://www.w3.org/2000/svg", "version": "1.1",
                        "width": CANVAS_W, "height": CANVAS_H, "viewBox": f"0 0 {CANVAS_W} {CANVAS_H}"},
                [defs(), Node("rect", {"id": "background", "width": CANVAS_W, "height": CANVAS_H,
                                       "fill": COLORS["background"]}), character])
    return root


def bbox(node):
    pts = np.array([to_canvas(p) for p in node.all_pts()])
    x0, y0 = pts.min(0)
    x1, y1 = pts.max(0)
    return {"x": round(float(x0), 1), "y": round(float(y0), 1),
            "width": round(float(x1 - x0), 1), "height": round(float(y1 - y0), 1)}


def geometry(root):
    parts = ["character", "hair_back", "body", "neck", "torso", "left_upper_arm", "left_forearm", "left_hand",
             "right_upper_arm", "right_forearm", "right_hand", "hips", "left_thigh", "left_lower_leg",
             "right_thigh", "right_lower_leg", "left_shoe", "right_shoe", "head", "face", "left_ear",
             "right_ear", "nose", "eyes", "left_eye", "right_eye", "eyebrows", "left_eyebrow",
             "right_eyebrow", "mouth", "hair_front"]
    face = {
        "right_eye_center": (450, eye_y + 3), "left_eye_center": (523, eye_y - 3),
        "right_eyebrow_center": (443, 117), "left_eyebrow_center": (531, 113),
        "nose_tip": (488, nose_y), "mouth_center": (490, mouth_y),
        "mouth_right_corner": (460, 215), "mouth_left_corner": (520, 212),
        "chin": (497, chin_y), "right_ear": (412, 180), "left_ear": (564, 166),
        "hair_part": (540, 22), "head_top": (488, head_top),
    }
    return {
        "canvas": {"width": CANVAS_W, "height": CANVAS_H, "viewBox": f"0 0 {CANVAS_W} {CANVAS_H}"},
        "character_transform": {"translate": [round(OFFSET_X, 2), round(OFFSET_Y, 2)], "scale": SCALE,
                                "note": "design units -> canvas: canvas = translate + design * scale"},
        "sides": "left_/right_ = the character's own left/right (her left is on the viewer's right)",
        "joints": {k: to_canvas(v) for k, v in JOINTS.items()},
        "joints_design_units": JOINTS,
        "face": {k: to_canvas(v) for k, v in face.items()},
        "landmarks_y": {k: to_canvas((0, v))[1] for k, v in dict(
            head_top=head_top, eye_y=eye_y, chin_y=chin_y, shoulder_y=shoulder_y, bust_y=bust_y, waist_y=waist_y,
            hip_y=hip_y, crotch_y=crotch_y, knee_y=knee_y, ankle_y=ankle_y, sole_y=sole_y).items()},
        "bounding_boxes": {p: bbox(root.find(p)) for p in parts if root.find(p) is not None},
    }


def main():
    root = build()
    svg = '<?xml version="1.0" encoding="UTF-8"?>\n' + root.xml() + "\n"
    with open(os.path.join(HERE, "girl_character.svg"), "w") as fh:
        fh.write(svg)
    with open(os.path.join(HERE, "character_geometry.json"), "w") as fh:
        json.dump(geometry(root), fh, indent=2)
    try:
        import cairosvg
        cairosvg.svg2png(bytestring=svg.encode(), write_to=os.path.join(HERE, "girl_character_preview.png"))
    except ImportError:
        print("cairosvg not installed: skipped the PNG preview (pip install cairosvg)")
    print("wrote girl_character.svg, character_geometry.json, girl_character_preview.png")


if __name__ == "__main__":
    main()
