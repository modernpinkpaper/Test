"""Chibi body drawn from the traced parts (see measure_body.py). Drawing coordinates = the head's.

Parts (each its own group, so they can move separately later): neck, torso, right/left arm, hips,
right/left leg, right/left shoe. "right"/"left" = her own right/left (her right is on the viewer's left).
"""
import json
import os

import chibi_eyes as E

HERE = os.path.dirname(os.path.abspath(__file__))
B = json.load(open(os.path.join(HERE, "ref", "measured_body.json")))
smooth, f = E.smooth, E.f
COL = dict(B["colours"], shoe=B["colours"]["shirt"], white="#ffffff", sole="#dadada", hair_dark=B["colours"]["outline2"], seam=B["colours"]["outline"])
LAYER_ORDER = ["hair_dark", "hair", "hair_light", "shirt", "skin", "skin_shade", "jeans", "seam", "stitch", "shoe", "white", "sole"]
OUTLINE = COL["outline"]


def part(name):
    p = B["parts"][name]
    g = [f'<path d="{smooth(s, True)}" fill="{OUTLINE}"/>' for s in p["silhouette"]]
    for layer in LAYER_ORDER:
        for s in p["layers"].get(layer, []):
            g.append(f'<path d="{smooth(s, True)}" fill="{COL[layer]}"/>')
    return f'<g id="{name}">' + "".join(g) + "</g>"


def neck():
    return part("hair_behind") + part("neck")


def taper_line(pts, w, colour):
    import chibi_hair as CH
    return CH.taper(CH.sample_curve(pts, 16), w, colour)


def dashed(pts, colour, w=1.0, dash="2.6 2"):
    return (f'<path d="{smooth(pts, False)}" fill="none" stroke="{colour}" stroke-width="{w}" '
            f'stroke-dasharray="{dash}" stroke-linecap="round"/>')


def jeans_details():
    """Waistband, belt loops, button, fly and front pockets, measured on the reference (clean shapes)."""
    navy, stitch, band, loop = "#253a53", "#8e9bb0", "#3a516e", "#4c6481"
    g = [f'<path d="{smooth([(131, 641), (188, 643), (246, 640), (246, 654), (188, 656.5), (131, 655)], True, corners=(0, 2, 3, 5))}" fill="{band}"/>']
    g.append(taper_line([(131, 655.5), (160, 657), (188, 657.3), (216, 657), (246, 655)], 1.4, navy))       # waistband seam
    g.append(dashed([(133, 651.5), (160, 653), (188, 653.3), (216, 653), (244, 651)], stitch, .9))
    for x in (154.5, 211.5):                                                                             # belt loops
        g.append(f'<rect x="{x}" y="643" width="5.5" height="14" rx="1" fill="{loop}" stroke="{navy}" stroke-width="1"/>')
    g.append('<circle cx="187.6" cy="648.3" r="3.1" fill="#c9cdd3" stroke="#8c919a" stroke-width=".6"/>')      # button
    g.append(taper_line([(182, 658), (182.3, 672), (182.2, 688), (181.5, 699)], 1.5, navy))                # fly edge
    g.append(dashed([(193.5, 658), (193.8, 676), (191, 686), (183, 690)], stitch, .9))                    # fly stitch
    for sgn in (-1, 1):                                                                                # front pockets
        P = [(188 + sgn * dx, y) for dx, y in ((38, 657.5), (42, 661), (49, 665.5), (58, 668), (64, 668.5))]
        g.append(taper_line(P, 1.8, navy))
        g.append(dashed([(188 + sgn * dx, y) for dx, y in ((36, 660), (40, 664), (47, 668.5), (56, 671), (62, 671.5))],
                        stitch, .9))
    return '<g id="jeans_details">' + "".join(g) + "</g>"


def body():
    """Everything below the neck, back to front."""
    order = ["right_leg", "left_leg", "right_shoe", "left_shoe", "hips", "torso", "right_arm", "left_arm"]
    parts = "".join(part(n) + (jeans_details() if n == "hips" else "") for n in order)
    return '<g id="body">' + parts + "</g>"
