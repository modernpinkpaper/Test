"""Her hands from the hands sheets (see measure_hands.py): open, flat, point, fist, peace, thumbs_up (the first sheet,
ref/measured_hands.json) + palm_up, palm_down, stop, c_grip, ok, finger_heart, index_up, clap, cover_mouth, hang, two,
hip_flat, hip_fist, offer (ref/measured_hands2.json).

hand(name, mirror) gives the hand in its own frame: wrist centre at (0, 0), fingers pointing up (-y), sheet pixels.
The arm rig scales it to her wrist and turns it with her forearm (chibi_body.arm).
"""
import json
import os

import cv2
import numpy as np

import chibi_eyes as E

HERE = os.path.dirname(os.path.abspath(__file__))
H = json.load(open(os.path.join(HERE, "ref", "measured_hands.json")))
_H2 = os.path.join(HERE, "ref", "measured_hands2.json")
if os.path.exists(_H2):
    for _k, _v in json.load(open(_H2))["hands"].items():
        H["hands"].setdefault(_k, _v)          # (the first sheet's hands stay exactly as they were)
# hands drawn a little long for her: shortened along the fingers (y in the hand's frame), wrist cut unchanged
SQUASH = {"hip_flat": 0.85}
smooth = E.smooth
B = json.load(open(os.path.join(HERE, "ref", "measured_body.json")))
# her own colours (the sheet's are a shade off, which shows as a line at the wrist)
COL = dict(outline=B["colours"]["outline"], skin=B["colours"]["skin"], shade=B["colours"]["skin_shade"], crease="#c96e47")


def _path(shape, colour, holes=()):
    """A filled shape; closed gaps inside it (the ring of an OK sign) are cut out of it (see-through)."""
    inner = [q for q in holes if cv2.pointPolygonTest(np.array(shape, np.float32), tuple(map(float, np.mean(q, 0))), False) > 0]
    if not inner:
        return f'<path d="{smooth(shape, True)}" fill="{colour}"/>'
    return f'<path d="{" ".join(smooth(q, True) for q in [shape] + inner)}" fill="{colour}" fill-rule="evenodd"/>'


def hand(name, mirror=False, squash=True):
    h = H["hands"][name]
    holes = h.get("holes", [])
    g = [_path(s, COL["outline"], holes) for s in h["silhouette"]]
    for layer in ("skin", "shade", "crease", "lines"):
        g += [_path(s, COL["outline" if layer == "lines" else layer], holes) for s in h.get(layer, [])]
    # skin carried a few px past the open wrist cut (between the side outlines): no dark edge where it meets the arm
    w = h["wrist_width"] / 2
    g.insert(1 + len(h["skin"]), f'<rect x="{-w:.1f}" y="-8" width="{2 * w:.1f}" height="16" fill="{COL["skin"]}"/>')
    body = "".join(g)
    if squash and name in SQUASH:
        body = f'<g transform="scale(1,{SQUASH[name]})">{body}</g>'
    return f'<g transform="scale(-1,1)">{body}</g>' if mirror else body
