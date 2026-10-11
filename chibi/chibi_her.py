"""Chibi version of the brand character, drawn from code as separate, animation-ready parts.

    python chibi/chibi_her.py            # writes chibi_her.svg and chibi_her.png next to this file

Coordinates are in a small 336 x 456 design space (the chibi reference size); the SVG viewBox scales it
up, so the art stays sharp at any size. Every part (hair, face, eyes, brows, mouth, arms, hands, legs,
shoes) is its own group with a pivot point, ready to be turned / swapped when she is animated.
"""
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))

COLORS = {
    "outline": "#3a2419",
    "skin": "#fcdcc8",
    "skin_shadow": "#f1bfa3",
    "blush": "#f59c9c",
    "hair": "#4b2b1d",
    "hair_dark": "#2f1a11",
    "hair_shine": "#7a4b35",
    "eye": "#5a2f1a",
    "eye_dark": "#2a130a",
    "eye_light": "#9b5a32",
    "brow": "#3e2419",
    "lip": "#e0787a",
    "tee": "#1f1d22",
    "tee_shine": "#3a3740",
    "pants": "#1f1d22",
    "shoe": "#1c1b1f",
    "sole": "#ffffff",
    "white": "#ffffff",
}
LINE = 2.5      # main outline width (design units)
THIN = 1.2

# Landmarks
cx = 180
eye_y = 164
chin_y = 221
neck_y = 214
shoulder_y = 232
hem_y = 300
hands_y = 318
ankle_y = 398
ground_y = 426

# Pivots for animation (neck turns the head, shoulders turn the arms, ...)
PIVOTS = {"neck": (cx, 214), "left_shoulder": (234, 244), "right_shoulder": (126, 244),
          "left_hip": (200, 300), "right_hip": (160, 300)}


# ---------------------------------------------------------------- tiny SVG helpers
def f(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def smooth(pts, closed=True, corners=(), t=1 / 6):
    """Cubic Bezier path through points (Catmull-Rom); indices in `corners` stay sharp."""
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


def shape(pts, fill, stroke=True, width=LINE, corners=(), **kw):
    extra = "".join(f' {k.replace("_", "-")}="{v}"' for k, v in kw.items())
    st = f' stroke="{COLORS["outline"]}" stroke-width="{width}" stroke-linejoin="round"' if stroke else ""
    return f'<path d="{smooth(pts, True, corners)}" fill="{fill}"{st}{extra}/>'


def line(pts, color=None, width=THIN, **kw):
    extra = "".join(f' {k.replace("_", "-")}="{v}"' for k, v in kw.items())
    return (f'<path d="{smooth(pts, False)}" fill="none" stroke="{color or COLORS["outline"]}" '
            f'stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"{extra}/>')


def ellipse(c, rx, ry, fill, **kw):
    extra = "".join(f' {k.replace("_", "-")}="{v}"' for k, v in kw.items())
    return f'<ellipse cx="{f(c[0])}" cy="{f(c[1])}" rx="{f(rx)}" ry="{f(ry)}" fill="{fill}"{extra}/>'


def group(gid, *parts, **kw):
    extra = "".join(f' {k.replace("_", "-")}="{v}"' for k, v in kw.items())
    return f'<g id="{gid}"{extra}>' + "".join(parts) + "</g>"


def mirror(pts):
    return [(2 * cx - x, y) for x, y in pts]


def star(c, r, fill="#ffffff"):
    """4-point sparkle for the eyes."""
    x, y = c
    k = r * .28
    pts = [(x, y - r), (x + k, y - k), (x + r, y), (x + k, y + k), (x, y + r), (x - k, y + k), (x - r, y), (x - k, y - k)]
    return shape(pts, fill, stroke=False, corners=range(8))


# ---------------------------------------------------------------- parts
def hair_back():
    """Long hair behind the head and shoulders (the tee is drawn over it)."""
    back = shape([(cx + 6, 33), (232, 38), (262, 62), (276, 104), (278, 160), (276, 220), (274, 280), (268, 318),
                  (254, 336), (240, 318), (232, 296), (cx, 300), (128, 296), (118, 318), (104, 336), (90, 318),
                  (84, 280), (80, 220), (80, 160), (84, 104), (100, 62), (130, 38)], COLORS["hair"])
    shade = (line([(92, 200), (90, 260), (96, 320)], COLORS["hair_dark"], 2, opacity=".7") +
             line([(268, 200), (270, 260), (264, 320)], COLORS["hair_dark"], 2, opacity=".7") +
             line([(100, 150), (104, 230)], COLORS["hair_shine"], 3, opacity=".6") +
             line([(262, 150), (258, 230)], COLORS["hair_shine"], 3, opacity=".6") +
             line([(86, 150), (86, 230), (92, 300)], COLORS["hair_dark"], 1.1, opacity=".6") +
             line([(272, 150), (272, 230), (266, 300)], COLORS["hair_dark"], 1.1, opacity=".6") +
             line([(112, 250), (114, 300), (110, 326)], COLORS["hair_dark"], 1.1, opacity=".6") +
             line([(246, 250), (244, 300), (248, 326)], COLORS["hair_dark"], 1.1, opacity=".6"))
    return group("hair_back", back, shade)


def face():
    skin = shape([(cx, 84), (230, 88), (252, 116), (258, 158), (252, 188), (236, 207), (208, 218), (cx, chin_y),
                  (152, 218), (124, 207), (108, 188), (102, 158), (108, 116), (130, 88)], COLORS["skin"])
    blush = (ellipse((cx - 52, 192), 13, 7.5, COLORS["blush"], opacity=".45") +
             ellipse((cx + 52, 192), 13, 7.5, COLORS["blush"], opacity=".45"))
    nose = ellipse((cx, 188), 1.8, 1.2, COLORS["skin_shadow"])
    return group("face", skin, blush, nose)


def ear(side):
    s = 1 if side == "left" else -1           # her left ear = viewer's right
    pts = [(cx + s * 70, 166), (cx + s * 82, 162), (cx + s * 86, 176), (cx + s * 82, 192), (cx + s * 70, 194)]
    return group(f"{side}_ear", shape(pts, COLORS["skin"]),
                 line([(cx + s * 77, 170), (cx + s * 82, 176), (cx + s * 78, 186)], COLORS["skin_shadow"], 1.4))


def eye(side, state="open"):
    """state: open | half | closed | happy. Big round eyes with a star sparkle, like the reference."""
    s = 1 if side == "left" else -1
    ex, ey = cx + s * 38, eye_y
    gid = f"{side}_eye"
    if state == "closed":
        return group(gid, line([(ex - 19 * s, ey + 3), (ex, ey + 9), (ex + 20 * s, ey + 1)], COLORS["eye_dark"], 3))
    if state == "happy":
        return group(gid, line([(ex - 16, ey + 7), (ex, ey - 6), (ex + 16, ey + 7)], COLORS["eye_dark"], 3))
    top = -20 if state == "open" else -5
    outline = [(ex - 21 * s, ey), (ex - 12 * s, ey + top + 2), (ex + 6 * s, ey + top), (ex + 20 * s, ey - 5),
               (ex + 21 * s, ey + 9), (ex + 4 * s, ey + 20), (ex - 15 * s, ey + 14)]
    white = shape(outline, COLORS["white"], stroke=False)
    clip = f'<clipPath id="clip_{gid}"><path d="{smooth(outline)}"/></clipPath>'
    iris = (f'<g clip-path="url(#clip_{gid})">' +
            ellipse((ex + 1 * s, ey), 16.5, 20, "url(#iris)") +
            ellipse((ex + 1 * s, ey + 1), 8.5, 10, COLORS["eye_dark"]) +
            star((ex - 4 * s, ey - 6), 8.5) +
            ellipse((ex + 7 * s, ey + 9), 2.6, 2.6, COLORS["white"]) + "</g>")
    lt = ey + top
    lid = [(ex - 21 * s, ey), (ex - 12 * s, ey + top + 2), (ex + 6 * s, ey + top), (ex + 20 * s, ey - 5)]
    liner = line(lid, COLORS["eye_dark"], 4.6)
    wing = 10 if state == "open" else 5
    liner += shape([(ex + 17 * s, ey - 8), (ex + 29 * s, ey - wing - 3), (ex + 21 * s, ey - 1)], COLORS["eye_dark"],
                   stroke=False, corners=(0, 1, 2))
    lashes = "".join(shape([(ex + a * s, lt + b), (ex + (a + 4) * s, lt + b - 6), (ex + (a + 5) * s, lt + b + 2)],
                           COLORS["eye_dark"], stroke=False, corners=(0, 1, 2))
                     for a, b in [(8, 1), (13, 5)])
    lower = line([(ex - 14 * s, ey + 14), (ex + 2 * s, ey + 20), (ex + 16 * s, ey + 12)], COLORS["eye"], 1.1, opacity=".6")
    return group(gid, clip, white, iris, lower, liner, lashes)


def brow(side, lift=0):
    s = 1 if side == "left" else -1
    b = cx + s * 38
    y = 131 - lift
    pts = [(b - 19 * s, y + 3), (b - 7 * s, y - 3), (b + 9 * s, y - 3), (b + 21 * s, y + 3),
           (b + 9 * s, y + 2), (b - 6 * s, y + 3), (b - 18 * s, y + 8)]
    return group(f"{side}_eyebrow", shape(pts, COLORS["brow"], stroke=False, corners=(0, 3)))


def mouth(shape_name="smile"):
    if shape_name == "open":
        m = shape([(172, 199), (cx, 201), (188, 198), (186, 207), (cx, 210), (174, 206)], COLORS["lip"], width=1.4)
    else:
        m = shape([(174, 201), (cx, 204), (186, 201), (cx, 207.5)], COLORS["lip"], stroke=False, opacity=".8") + \
            line([(169, 198.5), (174, 202.5), (cx, 204.2), (186, 202.5), (191, 198.5)], COLORS["outline"], 1.7)
    return group("mouth", m)


def hair_front():
    """Top of the head and the side-swept bangs framing the forehead (the long hair is hair_back)."""
    top = shape([(90, 110), (104, 66), (136, 42), (190, 33), (234, 40), (262, 64), (274, 106), (272, 160),
                 (260, 154), (254, 126), (238, 102), (214, 90), (194, 82), (168, 86), (140, 100), (120, 126),
                 (110, 162), (96, 154)], COLORS["hair"], corners=(7, 16))
    part = line([(190, 35), (192, 58), (194, 80)], COLORS["hair_dark"], 1.4)
    shine = (line([(128, 66), (156, 50), (182, 44)], COLORS["hair_shine"], 3.2, opacity=".85") +
             line([(208, 46), (236, 54), (252, 72)], COLORS["hair_shine"], 3.2, opacity=".85"))
    return group("hair_front", top, part, shine)


def neck():
    return group("neck", shape([(166, 212), (194, 212), (196, 234), (164, 234)], COLORS["skin"], corners=(0, 1, 2, 3)),
                 shape([(166, 214), (194, 214), (194, 220), (cx, 223), (166, 220)], COLORS["skin_shadow"], stroke=False, opacity=".7"))


def torso():
    tee = shape([(160, 228), (cx, 236), (200, 228), (224, 228), (240, 244), (232, 262), (226, 262), (226, 296),
                 (cx, 302), (134, 296), (134, 262), (128, 262), (120, 244), (136, 228)], COLORS["tee"],
                corners=(0, 2, 5, 6, 7, 9, 10, 11))
    neckline = line([(160, 228), (cx, 238), (200, 228)], COLORS["skin_shadow"], 1.2)
    folds = line([(150, 280), (158, 290)], COLORS["tee_shine"], 1.2) + line([(210, 280), (202, 290)], COLORS["tee_shine"], 1.2)
    return group("torso", tee, neckline, folds)


def arm(side):
    """Short chibi arm hanging from the sleeve toward the clasped hands."""
    s = 1 if side == "left" else -1
    pts = [(cx + s * 50, 256), (cx + s * 58, 262), (cx + s * 44, 300), (cx + s * 14, 320), (cx + s * 6, 312),
           (cx + s * 30, 292), (cx + s * 40, 264)]
    sleeve = shape([(cx + s * 44, 240), (cx + s * 62, 250), (cx + s * 58, 266), (cx + s * 42, 264)], COLORS["tee"],
                   corners=(1, 2, 3))
    return group(f"{side}_arm", shape(pts, COLORS["skin"]), sleeve,
                 data_pivot=f"{PIVOTS[f'{side}_shoulder'][0]},{PIVOTS[f'{side}_shoulder'][1]}")


def hands():
    return group("hands",
                 ellipse((172, hands_y), 11, 9, COLORS["skin"], stroke=COLORS["outline"], stroke_width=LINE),
                 ellipse((188, hands_y + 1), 11, 9, COLORS["skin"], stroke=COLORS["outline"], stroke_width=LINE),
                 line([(183, hands_y - 5), (184, hands_y + 4)], COLORS["skin_shadow"], 1.2))


def leg(side):
    s = 1 if side == "left" else -1
    x_out, x_in = cx + s * 42, cx - s * 1
    pts = [(x_in, 296), (x_out, 296), (x_out - s * 2, ankle_y), (x_in + s * 1, ankle_y)]
    return group(f"{side}_leg", shape(pts, COLORS["pants"], corners=(0, 1, 2, 3)),
                 line([(cx + s * 30, 320), (cx + s * 30, 390)], COLORS["tee_shine"], 1.2, opacity=".6"))


def shoe(side):
    s = 1 if side == "left" else -1
    c = cx + s * 23
    upper = shape([(c - 18, ankle_y - 2), (c + 18, ankle_y - 2), (c + 24, 404), (c + 26, 413), (c - 26, 413),
                   (c - 24, 404)], COLORS["shoe"], corners=(0, 1))
    sole = shape([(c - 27, 411), (c + 27, 411), (c + 27, 418), (c + 23, 422), (c - 23, 422), (c - 27, 418)],
                 COLORS["sole"], width=1.6, corners=(0, 1))
    lace = line([(c - 7, ankle_y + 4), (c + 7, ankle_y + 4)], COLORS["white"], 1.5) + \
        line([(c - 6, ankle_y + 9), (c + 6, ankle_y + 9)], COLORS["white"], 1.5)
    return group(f"{side}_shoe", upper, sole, lace)


def svg(eyes="open", mouth_shape="smile", background="#ffffff"):
    defs = f"""<defs>
  <radialGradient id="iris" cx=".5" cy=".7" r=".7"><stop offset="0" stop-color="{COLORS['eye_light']}"/>
    <stop offset=".55" stop-color="{COLORS['eye']}"/><stop offset="1" stop-color="{COLORS['eye_dark']}"/></radialGradient>
  <radialGradient id="floor"><stop offset="0" stop-color="#000" stop-opacity=".12"/><stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient>
</defs>"""
    body = group("body", neck(), leg("right"), leg("left"), shoe("right"), shoe("left"), torso(),
                 arm("right"), arm("left"), hands())
    head = group("head", ear("right"), ear("left"), face(),
                 group("eyes", eye("right", eyes), eye("left", eyes)),
                 group("eyebrows", brow("right"), brow("left")), mouth(mouth_shape),
                 data_pivot=f"{PIVOTS['neck'][0]},{PIVOTS['neck'][1]}")
    character = group("character", hair_back(), body, head, hair_front())
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1466" viewBox="0 0 336 456">{defs}'
            f'<rect width="336" height="456" fill="{background}"/>'
            f'{ellipse((cx, ground_y + 2), 62, 7, "url(#floor)")}{character}</svg>')


if __name__ == "__main__":
    import cairosvg
    text = svg()
    with open(os.path.join(HERE, "chibi_her.svg"), "w") as fh:
        fh.write(text)
    cairosvg.svg2png(bytestring=text.encode(), write_to=os.path.join(HERE, "chibi_her.png"))
    print("saved chibi_her.svg / chibi_her.png")
