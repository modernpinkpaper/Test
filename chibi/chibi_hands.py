"""Her hands from the hands sheet (see measure_hands.py): open, flat, point, fist, peace, thumbs_up.

hand(name, mirror) gives the hand in its own frame: wrist centre at (0, 0), fingers pointing up (-y), sheet pixels.
The arm rig scales it to her wrist and turns it with her forearm (chibi_body.arm).
"""
import json
import os

import chibi_eyes as E

HERE = os.path.dirname(os.path.abspath(__file__))
H = json.load(open(os.path.join(HERE, "ref", "measured_hands.json")))
smooth = E.smooth
B = json.load(open(os.path.join(HERE, "ref", "measured_body.json")))
# her own colours (the sheet's are a shade off, which shows as a line at the wrist)
COL = dict(outline=B["colours"]["outline"], skin=B["colours"]["skin"], shade=B["colours"]["skin_shade"], crease="#c96e47")


def hand(name, mirror=False):
    h = H["hands"][name]
    g = [f'<path d="{smooth(s, True)}" fill="{COL["outline"]}"/>' for s in h["silhouette"]]
    for layer in ("skin", "shade", "crease", "lines"):
        g += [f'<path d="{smooth(s, True)}" fill="{COL["outline" if layer == "lines" else layer]}"/>' for s in h.get(layer, [])]
    # skin carried a few px past the open wrist cut (between the side outlines): no dark edge where it meets the arm
    w = h["wrist_width"] / 2
    g.insert(1 + len(h["skin"]), f'<rect x="{-w:.1f}" y="-8" width="{2 * w:.1f}" height="16" fill="{COL["skin"]}"/>')
    body = "".join(g)
    return f'<g transform="scale(-1,1)">{body}</g>' if mirror else body
