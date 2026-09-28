"""Chibi face: head shape, ears, nose, blush and the 4 mouth shapes, from shapes traced on the reference
sheet (see measure_face.py). Coordinates are pixels of the reference (left girl).

Mouth shapes (for talking / lip sync): smile, open, wide, oh.
"""
import json
import os

import numpy as np

import chibi_eyes as E

HERE = os.path.dirname(os.path.abspath(__file__))
F = json.load(open(os.path.join(HERE, "ref", "measured_face.json")))
f, smooth = E.f, E.smooth

C = {   # sampled from the reference
    "skin": "#fecdab",
    "ear": "#fbbd98",
    "ear_inner": "#f3a684",
    "jaw_line": "#8d472e",
    "nose": "#f5a47f",
    "blush": "#ff9f95",
    "smile": "#e26968",
    "rim": "#d03e44",
    "mouth_dark": "#a82a35",
    "tongue": "#fc8b93",
}


def jaw_points():
    """The traced face outline below the eyes (ear to chin to ear), ordered left to right."""
    P = F["face_skin"]
    n = len(P)
    low = [i for i in range(n) if P[i][1] > 450]
    # rotate so the run of low points is contiguous
    start = next(i for i in low if P[(i - 1) % n][1] <= 450)
    run = []
    i = start
    while P[i % n][1] > 450:
        run.append(P[i % n])
        i += 1
    run = sorted(run, key=lambda p: p[0])
    # symmetric: keep the clean half (viewer's left) and mirror it
    mid = E.FACE_MID_X
    half = [p for p in run if p[0] < mid - 1]
    return half + [(mid, max(p[1] for p in run))] + [(2 * mid - x, y) for x, y in half[::-1]]


def head():
    """Face skin: the traced jaw and chin, closed with a smooth dome under the hair."""
    jaw = jaw_points()
    (lx, ly), (rx, ry) = jaw[0], jaw[-1]
    dome = [(rx + 2, 400), (rx - 4, 340), (272, 292), (186, 270), (100, 292), (lx + 4, 340), (lx - 2, 400)]
    pts = jaw + dome
    skin = f'<path d="{smooth(pts, True)}" fill="{C["skin"]}"/>'
    line = f'<path d="{smooth(jaw, False)}" fill="none" stroke="{C["jaw_line"]}" stroke-width="1.8" stroke-linecap="round"/>'
    return f'<g id="face">{skin}{line}</g>'


# her left ear (viewer's right), from the traced outer edge: top ~405, bottom ~458, sticks out to x ~334
EAR_LEFT = [(286, 410), (298, 404), (312, 401), (324, 404), (331.5, 413), (333, 426), (328.5, 440), (318, 451),
            (303, 458), (286, 458)]


def ear(side):
    """Clean ear shape sized from the trace; her right ear is the mirror of her left."""
    pts = EAR_LEFT if side == "left" else [(2 * E.FACE_MID_X - x, y) for x, y in EAR_LEFT[::-1]]
    s = 1 if side == "left" else -1
    ex = E.FACE_MID_X + s * 128
    inner = [(ex + s * 0, 413), (ex + s * 6, 420), (ex + s * 7, 432), (ex + s * 2, 444)]
    return (f'<g id="{side}_ear"><path d="{smooth(pts, True, corners=(0, len(pts) - 1))}" fill="{C["ear"]}" stroke="{C["jaw_line"]}" stroke-width="1.6"/>'
            f'<path d="{smooth(inner, False)}" fill="none" stroke="{C["ear_inner"]}" stroke-width="3" stroke-linecap="round"/></g>')


def nose():
    x, y, r = F["nose"]
    return f'<g id="nose"><ellipse cx="{f(x)}" cy="{f(y)}" rx="{f(r)}" ry="{f(r * .85)}" fill="{C["nose"]}"/></g>'


def blush():
    return '<g id="blush">' + "".join(
        f'<ellipse cx="{f(x)}" cy="{f(y)}" rx="{f(rx * 1.15)}" ry="{f(ry * 1.15)}" fill="url(#blushGrad)"/>'
        for x, y, rx, ry in [F["blush"][1], [2 * E.FACE_MID_X - F["blush"][1][0]] + F["blush"][1][1:]]) + "</g>"


def mouth_box(shape):
    P = np.array(F["mouths"][shape]["outline"])
    return P[:, 0].min(), P[:, 0].max(), P[:, 1].min(), P[:, 1].max()


def mouth(shape="smile", open_amount=None):
    """Clean shapes sized from the traced mouths:
    smile = a thick curved line; open / wide = a "D" (flat top, round bottom); oh = an oval.
    Each open mouth: red rim, darker back of the mouth at the top, pink tongue sitting on the bottom."""
    x0, x1, y0, y1 = mouth_box(shape)
    cx = (x0 + x1) / 2
    if shape == "smile":
        # a true circular arc through both corners and the lowest point, drawn as a thick round-capped line
        (ax, ay), (bx, by), (mx, my) = (x0 + 3, y0 + 3), (x1 - 3, y0 + 3), (cx, y1 - 2.4)
        half = (bx - ax) / 2
        sag = my - ay
        R = (half ** 2 + sag ** 2) / (2 * sag)
        return (f'<g id="mouth"><path d="M{f(ax)},{f(ay)} A{f(R)},{f(R)} 0 0,0 {f(bx)},{f(by)}" fill="none" '
                f'stroke="url(#smileGrad)" stroke-width="4.8" stroke-linecap="round"/></g>')
    if shape == "oh":
        outline = (f'M{f(cx)},{f(y0)} a{f((x1 - x0) / 2)},{f((y1 - y0) / 2)} 0 1,0 0.01,0 Z')
    else:
        w, h, r = x1 - x0, y1 - y0, 3.0
        outline = (f"M{f(x0 + r)},{f(y0)} L{f(x1 - r)},{f(y0)} Q{f(x1)},{f(y0)} {f(x1)},{f(y0 + r)} "
                   f"C{f(x1 - w * .02)},{f(y0 + h * .62)} {f(cx + w * .28)},{f(y1)} {f(cx)},{f(y1)} "
                   f"C{f(cx - w * .28)},{f(y1)} {f(x0 + w * .02)},{f(y0 + h * .62)} {f(x0)},{f(y0 + r)} "
                   f"Q{f(x0)},{f(y0)} {f(x0 + r)},{f(y0)} Z")
    # tongue, as in the reference: ~70% of the mouth wide, ~65% tall, resting just above the bottom rim
    trx, try_ = (x1 - x0) * .36, (y1 - y0) * .36
    tcy = y1 - 2.4 - try_
    clip = f'<clipPath id="clip_mouth_{shape}"><path d="{outline}"/></clipPath>'
    return (f'<g id="mouth">{clip}<path d="{outline}" fill="url(#mouthGrad)"/>'
            f'<g clip-path="url(#clip_mouth_{shape})">'
            f'<ellipse cx="{f(cx)}" cy="{f(tcy)}" rx="{f(trx)}" ry="{f(try_)}" fill="{C["tongue"]}"/>'
            f'<ellipse cx="{f(cx)}" cy="{f(tcy - try_ * .3)}" rx="{f(trx * .55)}" ry="{f(try_ * .35)}" fill="#ffffff" opacity=".12"/></g>'
            f'<path d="{outline}" fill="none" stroke="{C["mouth_dark"]}" stroke-width=".9" opacity=".6"/></g>')


DEFS = E.DEFS + f"""
  <radialGradient id="blushGrad"><stop offset=".35" stop-color="{C['blush']}" stop-opacity=".95"/>
    <stop offset="1" stop-color="{C['blush']}" stop-opacity="0"/></radialGradient>
  <linearGradient id="smileGrad" gradientUnits="userSpaceOnUse" x1="164" y1="0" x2="210" y2="0"><stop offset="0" stop-color="#d7555e"/>
    <stop offset=".5" stop-color="{C['smile']}"/><stop offset="1" stop-color="#d7555e"/></linearGradient>
  <linearGradient id="mouthGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#bf3440"/>
    <stop offset=".5" stop-color="{C['rim']}"/><stop offset="1" stop-color="#d94a54"/></linearGradient>"""


def face_svg(mouth_shape="smile", look=(0, 0), eyes="open"):
    """Everything on the face, in drawing order (ears, skin, blush, nose, mouth, eyes, brows)."""
    return (ear("right") + ear("left") + head() + blush() + nose() + mouth(mouth_shape)
            + E.eye("right", eyes, look) + E.eye("left", eyes, look) + E.brow("right") + E.brow("left"))


if __name__ == "__main__":
    import sys
    import cairosvg
    from PIL import Image
    out, ref_path = sys.argv[1], sys.argv[2]
    ref = Image.open(ref_path).convert("RGB")
    box = (40, 240, 340, 540)
    sc = 2
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{(box[2] - box[0]) * sc}" height="{(box[3] - box[1]) * sc}" '
           f'viewBox="{box[0]} {box[1]} {box[2] - box[0]} {box[3] - box[1]}"><defs>{DEFS}</defs>'
           f'<rect x="0" y="0" width="2000" height="2000" fill="#ffffff"/>{face_svg()}</svg>')
    cairosvg.svg2png(bytestring=svg.encode(), write_to=out + ".mine.png")
    a = ref.crop(box).resize(((box[2] - box[0]) * sc, (box[3] - box[1]) * sc), Image.LANCZOS)
    b = Image.open(out + ".mine.png").convert("RGB")
    both = Image.new("RGB", (a.width * 2 + 12, a.height), "white")
    both.paste(a, (0, 0))
    both.paste(b, (a.width + 12, 0))
    both.save(out)
    # the four mouths: reference (top) and mine (bottom)
    tiles = []
    for (name, (dx, dy)) in zip(("smile", "open", "wide", "oh"), F["girl_offsets"]):
        mb = (150, 445, 230, 500)
        r_tile = ref.crop((mb[0] + dx, mb[1] + dy, mb[2] + dx, mb[3] + dy)).resize((320, 220), Image.LANCZOS)
        s = (f'<svg xmlns="http://www.w3.org/2000/svg" width="320" height="220" viewBox="{mb[0]} {mb[1]} 80 55">'
             f'<defs>{DEFS}</defs><rect x="0" y="0" width="2000" height="2000" fill="{C["skin"]}"/>{mouth(name)}</svg>')
        cairosvg.svg2png(bytestring=s.encode(), write_to=out + ".m.png")
        m_tile = Image.open(out + ".m.png").convert("RGB")
        t = Image.new("RGB", (320, 450), "white")
        t.paste(r_tile, (0, 0))
        t.paste(m_tile, (0, 230))
        tiles.append(t)
    sheet = Image.new("RGB", (4 * 330, 450), "white")
    for i, t in enumerate(tiles):
        sheet.paste(t, (i * 330, 0))
    sheet.save(out.replace(".png", "_mouths.png"))
