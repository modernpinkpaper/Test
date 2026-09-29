"""Chibi body drawn from the traced parts (see measure_body.py). Drawing coordinates = the head's.

Parts (each its own group, so they can move separately later): neck, torso, right/left arm, hips,
right/left leg, right/left shoe. "right"/"left" = her own right/left (her right is on the viewer's left).
"""
import json
import os

import numpy as np

import chibi_eyes as E

HERE = os.path.dirname(os.path.abspath(__file__))
B = json.load(open(os.path.join(HERE, "ref", "measured_body.json")))
smooth, f = E.smooth, E.f
COL = dict(B["colours"], shoe=B["colours"]["shirt"], white="#ffffff", sole="#dadada", hair_dark=B["colours"]["outline2"], seam=B["colours"]["outline"], shade=B["colours"]["outline"])
LAYER_ORDER = ["hair_dark", "hair", "hair_light", "shirt", "skin", "skin_shade", "jeans", "seam", "stitch", "shoe", "shade", "white", "sole"]
OUTLINE = COL["outline"]


def part(name):
    p = B["parts"][name]
    g = [f'<path d="{smooth(s, True)}" fill="{OUTLINE}"/>' for s in p["silhouette"]]
    for layer in LAYER_ORDER:
        for s in p["layers"].get(layer, []):
            g.append(f'<path d="{smooth(s, True)}" fill="{COL[layer]}"/>')
    return f'<g id="{name}">' + "".join(g) + "</g>"


def neck():
    return part("backing") + part("neck")        # backing: dark fill of the whole figure, behind everything


def taper_line(pts, w, colour):
    import chibi_hair as CH
    return CH.taper(CH.sample_curve(pts, 16), w, colour)


def dashed(pts, colour, w=1.0, dash="2.6 2"):
    return (f'<path d="{smooth(pts, False)}" fill="none" stroke="{colour}" stroke-width="{w}" '
            f'stroke-dasharray="{dash}" stroke-linecap="round"/>')


def band_top(x):
    return 645 - 6 * ((x - 188) / 55) ** 2          # waistband edges: they dip in the middle, like the shirt hem


def band_bottom(x):
    return 656 - 9 * ((x - 188) / 55) ** 2


def jeans_details():
    """Waistband, belt loops, button, fly, front pockets and crotch folds, measured on the reference (clean shapes)."""
    navy, stitch = "#253a53", "#8e9bb0"
    xs = np.linspace(128, 248, 13)
    g = [taper_line([(x, band_bottom(x)) for x in xs], 1.6, navy)]                        # waistband seam
    g.append(dashed([(x, band_bottom(x) - 3.5) for x in np.linspace(132, 244, 13)], stitch, .9))
    for x in (157.5, 214.5):                                                             # belt loops (follow the curve)
        t0, t1 = band_top(x) - 1.5, band_bottom(x) + 1.5
        pts = [(x - 3, t0), (x + 3, t0), (x + 3, t1), (x - 3, t1)]
        g.append(f'<path d="{smooth(pts, True, corners=(0, 1, 2, 3))}" fill="{COL["jeans"]}" stroke="{navy}" stroke-width="1.1"/>')
    g.append(f'<circle cx="188" cy="{band_top(188) + 4.6:.1f}" r="3.4" fill="#c9cdd3" stroke="#8c919a" stroke-width=".6"/>')   # button
    g.append(taper_line([(181.8, 657), (182, 672), (182, 688), (182.5, 701)], 1.6, navy))       # fly edge
    g.append(dashed([(195.5, 658), (195.6, 676), (193, 686), (184, 689.5)], stitch, .9))        # fly stitch
    for sgn in (-1, 1):                                                                  # front pockets
        P = [(188 + sgn * dx, y) for dx, y in ((36, band_bottom(152) + .5), (39, 660), (46, 666), (55, 669.5), (64, 671))]
        g.append(taper_line(P, 1.9, navy))
        g.append(dashed([(188 + sgn * dx, y) for dx, y in ((34, 660), (38, 665), (45, 670), (54, 673), (62, 674.5))], stitch, .9))
    for pts in ([(163, 692), (174, 698), (187.5, 704.5)], [(213, 690), (201, 698), (189, 704.5)]):   # crotch folds
        g.append(taper_line(pts, 3.0, navy))
    return '<g id="jeans_details">' + "".join(g) + "</g>"


def jeans():
    """Hips + both legs: all the dark outlines first, then all the denim, so no outline slivers where they overlap."""
    names = ["right_leg", "left_leg", "hips"]
    sil = "".join(f'<path d="{smooth(s, True)}" fill="{OUTLINE}"/>' for n in names for s in B["parts"][n]["silhouette"])
    # the denim pieces overlap (no seams); all of it is trimmed to the outer edge of the jeans, so the smoothed
    # corners of the pieces never poke out; the top of the gap between the legs is a clean point like the reference
    edge = "".join(f'<path d="{smooth(s, True)}"/>' for s in B["denim_outline"])
    fill = "".join(f'<path d="{smooth(s, True)}"/>' for n in names for s in B["parts"][n]["layers"]["jeans"])
    # top of the gap between the legs: redrawn as one clean tapering shape (measured on the reference)
    tip = (f'<path d="M176,699 H200 V728 H176 Z" fill="{COL["jeans"]}"/>'
           f'<path d="{smooth([(188.2, 704), (190.2, 707), (191.3, 715), (192.2, 729), (182.4, 729), (184.8, 715), (186.4, 707)], True, corners=(0, 3, 4))}" fill="{OUTLINE}"/>')
    return (f'<g id="jeans">{sil}<clipPath id="clip_denim">{edge}</clipPath>'
            f'<g clip-path="url(#clip_denim)" fill="{COL["jeans"]}">{fill}</g>{tip}'
            f'<g clip-path="url(#clip_denim)">{jeans_details()}</g></g>')

def body():
    """Everything below the neck, back to front."""
    parts = part("right_shoe") + part("left_shoe") + jeans() + "".join(part(n) for n in ("torso", "right_arm", "left_arm"))
    return '<g id="body">' + parts + "</g>"
