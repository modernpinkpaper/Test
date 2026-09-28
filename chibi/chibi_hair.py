"""Chibi hair, from shapes traced on the reference (see measure_hair.py). Pixels of the reference sheet.

Layers (so the hair can sway / follow the head separately later):
  hair_back  - the whole silhouette, drawn behind the face and body
  hair_front - the crown and the locks framing the face, drawn over the forehead edge
  strands    - darker strand lines and lighter shine streaks
"""
import json
import os

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


def hair_back():
    return (f'<g id="hair_back">{path(H["hair_back"], fill="url(#hairGrad)", stroke=C["outline"], stroke_width=2.6, stroke_linejoin="round")}'
            + "".join(path(p, fill=C["hair_light"], opacity=".8") for p in H["strands"]["light"])
            + "".join(path(p, fill=C["hair_dark"], opacity=".8") for p in H["strands"]["dark"]) + flow_strands() + "</g>")


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


def hair_front():
    """Front pieces: filled like the back hair; their outline only shows where they meet the face."""
    face_clip = f'<clipPath id="clip_face_skin"><path d="{smooth(CF.F["face_skin"], True)}"/></clipPath>'
    fills = "".join(path(p, fill="url(#hairGrad)") for p in H["hair_front"])
    lines = "".join(path(p, fill="none", stroke=C["outline"], stroke_width=3.2, stroke_linejoin="round") for p in H["hair_front"])
    shadow = "".join(path(p, fill="none", stroke="#c98a6c", stroke_width=10, opacity=".35") for p in H["hair_front"])
    return (f'<g id="hair_front">{face_clip}{fills}{crown_strands()}'
            f'<g clip-path="url(#clip_face_skin)">{shadow}{lines}</g></g>')


DEFS = CF.DEFS + f"""
  <linearGradient id="hairGrad" gradientUnits="userSpaceOnUse" x1="0" y1="180" x2="0" y2="720">
    <stop offset="0" stop-color="#5a3325"/><stop offset=".3" stop-color="{C['hair']}"/><stop offset="1" stop-color="#5a3222"/></linearGradient>"""


def temp_body():
    """Placeholder body traced flat from the reference, only for previews until the real body is built."""
    return ('<g id="temp_body">'
            + "".join(path(p, fill=CF.C["skin"], stroke=C["outline"], stroke_width=2.2) for p in H["temp_body"]["skin"])
            + "".join(path(p, fill="#2e2624", stroke="#1d1414", stroke_width=2) for p in H["temp_body"]["clothes"]) + "</g>")


def head_svg(mouth_shape="smile", look=(0, 0), eyes="open", body=True):
    # her right ear (viewer's left) is hidden by the hair, as in the reference
    return (hair_back() + (temp_body() if body else "") + CF.ear("left") + CF.head() + CF.blush() + CF.nose() + CF.mouth(mouth_shape)
            + E.eye("right", eyes, look) + E.eye("left", eyes, look) + E.brow("right") + E.brow("left") + hair_front())


if __name__ == "__main__":
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
