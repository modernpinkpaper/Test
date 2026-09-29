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
COL = dict(B["colours"], shoe=B["colours"]["shirt"], white="#ffffff", sole="#dadada", hair_dark=B["colours"]["outline2"], seam=B["colours"]["outline"], shade=B["colours"]["outline"], hair_hidden="#3d261a")
LAYER_ORDER = ["hair_hidden", "hair_dark", "hair", "hair_light", "shirt", "skin", "skin_shade", "jeans", "seam", "stitch", "shoe", "shade", "white", "sole"]
OUTLINE = COL["outline"]


def part(name):
    p = B["parts"][name]
    g = [f'<path d="{smooth(s, True)}" fill="{OUTLINE}"/>' for s in p["silhouette"]]
    for layer in LAYER_ORDER:
        for s in p["layers"].get(layer, []):
            g.append(f'<path d="{smooth(s, True)}" fill="{COL[layer]}"/>')
    return f'<g id="{name}">' + "".join(g) + "</g>"


def neck():
    """backing: dark fill of the figure behind everything (not behind the arms: they move); the hair hidden behind
    the arms, painted in a shadow tone so a raised arm shows hair, not a hole; then the neck."""
    hidden = "".join(f'<path d="{smooth(s, True)}" fill="{COL["hair_hidden"]}"/>'
                     for s in B["parts"].get("hair_behind_arms", {}).get("layers", {}).get("hair_hidden", []))
    return part("backing") + f'<g id="hair_hidden">{hidden}{hidden_locks()}</g>' + part("neck")


def hidden_locks(step=10.0):
    """Dark lines between locks across the hidden hair (it would otherwise be one flat patch when an arm lifts):
    gently tapered, falling outwards like the visible locks next to them."""
    shapes = B["parts"].get("hair_behind_arms", {}).get("layers", {}).get("hair_hidden", [])
    if not shapes:
        return ""
    clip = "".join(f'<path d="{smooth(s, True)}"/>' for s in shapes)
    g = []
    for s in shapes:
        P = np.array(s)
        x0, y0, x1, y1 = P[:, 0].min(), P[:, 1].min(), P[:, 0].max(), P[:, 1].max()
        out = -1 if P[:, 0].mean() < 188.1 else 1               # which way the hair falls (away from the body)
        for i, x in enumerate(np.arange(x0 - 20, x1 + 20, step)):
            top, bot = y0 - 5, y1 + 5
            pts = [(x, top), (x + out * 4, (top * 2 + bot) / 3), (x + out * 10, (top + 2 * bot) / 3), (x + out * 18, bot)]
            g.append(taper_line(pts, 2.6 if i % 2 else 1.8, COL["hair_dark"]))
    return f'<clipPath id="clip_hidden_hair">{clip}</clipPath><g clip-path="url(#clip_hidden_hair)">{"".join(g)}</g>'


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

FINGER_CORE, FINGER_SOFT = "#c96e47", "#eb9f78"


def pointed_line(pts, wmax, colour, extend=4.0):
    """A line that starts at a fine point (top) and reaches full width by its middle; the bottom end is carried on
    `extend` units so it runs into the outline (the line is clipped to the skin)."""
    import chibi_hair as CH
    P = np.array(pts, float)
    d = P[-1] - P[-2]
    P = np.vstack([P, P[-1] + d / (np.linalg.norm(d) + 1e-9) * extend])
    C = np.array(CH.sample_curve([tuple(p) for p in P], 12), float)
    t = np.linspace(0, 1, len(C))
    w = wmax * np.clip(t / 0.5, 0, 1) ** 0.7
    tang = np.gradient(C, axis=0)
    nrm = np.stack([-tang[:, 1], tang[:, 0]], 1) / (np.linalg.norm(tang, axis=1, keepdims=True) + 1e-9)
    L, R = C + nrm * w[:, None] / 2, C - nrm * w[:, None] / 2
    ring = [tuple(p) for p in L] + [tuple(p) for p in R[::-1]]
    return f'<path d="M{" L".join(f"{x:.2f},{y:.2f}" for x, y in ring)} Z" fill="{colour}"/>'


def finger_lines(side):
    """The lines between the fingers and the crease above the thumb, measured on the reference: thin strokes with a
    pointed top (soft wide edge + darker core), clipped to the hand's skin."""
    lines = B.get("finger_lines", {}).get(side, [])
    skin = "".join(f'<path d="{smooth(s, True)}"/>' for s in B["parts"][f"{side}_arm"]["layers"]["skin"])
    g = "".join(pointed_line(ln["points"], ln["width"] * 1.7, FINGER_SOFT) + pointed_line(ln["points"], ln["width"] * .95, FINGER_CORE)
                for ln in lines)
    return f'<clipPath id="clip_skin_{side}">{skin}</clipPath><g clip-path="url(#clip_skin_{side})">{g}</g>'


# ---------------------------------------------------------------- arm rig: shoulder -> elbow -> wrist
# Each arm is cut into sleeve + upper arm, forearm and hand. A segment is the whole arm drawing clipped to its
# region; the regions overlap a little (no seams) and every joint has a round disc, so a bent joint shows a round
# knob instead of a gap. The segments are nested groups: turning the shoulder carries the forearm and hand along.
SLEEVE_CREASE = {"right": [(137.5, 530), (137, 552), (135.5, 566), (135, 580), (135.5, 610)]}   # measured
SLEEVE_CREASE["left"] = [(2 * 188.1 - x, y) for x, y in SLEEVE_CREASE["right"]]
SHOULDER_R, OVERLAP = 14, 3
SHOULDER_PIVOT = (3, 549)      # the arm turns around this point: units out from the sleeve crease, y


def arm_joints(side):
    """Shoulder, elbow and wrist of one arm, measured from the arm's skin shape (drawing units) + joint radii.
    wrist = narrowest row of the lower arm; elbow = halfway between the top of the arm and the wrist."""
    import cv2
    k = 4
    m = np.zeros((1000 * k, 400 * k), np.uint8)
    for sh in B["parts"][f"{side}_arm"]["layers"]["skin"]:
        cv2.fillPoly(m, [np.round(np.array(sh) * k).astype(np.int32)], 1)
    rows = {}
    for y in range(560, 760):
        xs = np.where(m[y * k])[0]
        if len(xs):
            rows[y] = (xs.min() / k, xs.max() / k)
    top = min(y for y, (a, b) in rows.items() if b - a > 20)
    wrist_y = min((y for y in rows if 670 <= y <= 700), key=lambda y: rows[y][1] - rows[y][0])
    elbow_y = round((top + wrist_y) / 2)
    c = lambda y: ((rows[y][0] + rows[y][1]) / 2, y)
    w = lambda y: (rows[y][1] - rows[y][0]) / 2
    crease = SLEEVE_CREASE[side]
    sgn = -1 if side == "right" else 1
    shoulder = (crease[2][0] + sgn * SHOULDER_PIVOT[0], SHOULDER_PIVOT[1])
    return {"shoulder": shoulder, "elbow": c(elbow_y), "wrist": c(wrist_y), "elbow_r": w(elbow_y) + 3,
            "wrist_r": w(wrist_y) + 3, "top": c(top)}


def _halfplane(p, d, keep_before, shift=0.0, L=400):
    """Polygon covering the side of the line through p (perpendicular to direction d) before or after it."""
    d = np.array(d, float) / np.linalg.norm(d)
    n = np.array([-d[1], d[0]])
    p = np.array(p, float) + d * (shift if keep_before else -shift)
    far = -d * L if keep_before else d * L
    return [p + n * L, p - n * L, p - n * L + far, p + n * L + far]


def _disc(c, r, n=48):
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return list(zip(c[0] + r * np.cos(t), c[1] + r * np.sin(t)))


def _clip(cid, polys):
    """clipPath = union of polygons. All are wound the same way: overlapping shapes add up instead of cancelling."""
    out = []
    for P in polys:
        P = np.array(P, float)
        area = np.sum(P[:, 0] * np.roll(P[:, 1], -1) - np.roll(P[:, 0], -1) * P[:, 1])
        if area < 0:
            P = P[::-1]
        out.append("M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in P) + " Z")
    return f'<clipPath id="{cid}"><path d="{" ".join(out)}"/></clipPath>'


def _clipped(cid, content):
    """content clipped by clip path cid with a hard cut (cairo takes the clip's anti-aliasing from the parent)."""
    return f'<g shape-rendering="crispEdges"><g clip-path="url(#{cid})" shape-rendering="auto">{content}</g></g>'


def _rot(angle, c):
    return f' transform="rotate({angle:.2f} {c[0]:.2f} {c[1]:.2f})"' if angle else ""


def sleeve_region(side, outward=0.0):
    """Everything on the arm's side of the sleeve crease (moved `outward` units further out)."""
    sgn = -1 if side == "right" else 1
    cr = [(x + sgn * outward, y) for x, y in SLEEVE_CREASE[side]]
    edge = 400 if side == "left" else -20
    return cr + [(edge, cr[-1][1]), (edge, cr[0][1])]


def torso():
    """The shirt without its sleeves (they move with the upper arms), + a round shoulder under each sleeve."""
    band = ([(x - OVERLAP, y) for x, y in SLEEVE_CREASE["right"]]
            + [(x + OVERLAP, y) for x, y in SLEEVE_CREASE["left"]][::-1])
    y0, y1 = SLEEVE_CREASE["right"][0][1] + 4, SLEEVE_CREASE["right"][-1][1] - 4
    xr, xl = SLEEVE_CREASE["right"][0][0] - OVERLAP, SLEEVE_CREASE["left"][0][0] + OVERLAP
    top = [(xr, 0), (xl, 0), (xl, y0), (xr, y0)]              # above the creases, between them (not the sleeve tops)
    below = [(-20, y1), (420, y1), (420, 1000), (-20, 1000)]
    # a round, outlined shoulder under the shirt: when the sleeve turns away it fills in (no notch, no raw cut)
    caps = shoulder_cap("right") + shoulder_cap("left")
    return caps + _clip("clip_torso", [band, top, below]) + _clipped("clip_torso", part("torso"))


SHOULDER_CAP = (1.5, -3.0, 14.5)    # round shoulder under each sleeve: shift inwards / down from the pivot, radius


def shoulder_cap(side):
    """A round, outlined shirt shoulder at the shoulder pivot: when the sleeve turns away, this shows instead of a gap."""
    x, y = arm_joints(side)["shoulder"]
    dx, dy, r = SHOULDER_CAP
    x += dx if side == "right" else -dx
    return (f'<circle cx="{x:.2f}" cy="{y + dy:.2f}" r="{r}" fill="{COL["shirt"]}" stroke="{OUTLINE}" '
            f'stroke-width="{JOINT_LINE}"/>')


JOINT_LINE = 3.5     # outline width around a bent joint's round knob


def _ring(c, r):
    return f'<circle cx="{c[0]:.2f}" cy="{c[1]:.2f}" r="{r:.2f}" fill="{OUTLINE}"/>'


HAND_INSET = 4.0     # a swapped-in hand's wrist cut sits this far inside the end of the forearm (hidden joint)


def swapped_hand(side, name, J, d_lower):
    """A hand from the hands sheet at the wrist: scaled to her wrist, fingers along the forearm, flipped for the other
    side when the sheet shows the opposite hand."""
    import chibi_hands as CHd
    h = CHd.H["hands"][name]
    scale = 2 * (J["wrist_r"] - 3) / (h["wrist_width"] + 9)          # (the cut excludes ~4.5 px of skin at each side)
    d = np.array(d_lower, float) / np.linalg.norm(d_lower)
    at = np.array(J["wrist"]) - d * HAND_INSET
    ang = np.degrees(np.arctan2(d[1], d[0]) - np.arctan2(-1, 0))
    mirror = (h["which"] == "L") == (side == "right")
    return (f'<g id="{side}_hand_{name}" transform="translate({at[0]:.2f},{at[1]:.2f}) rotate({ang:.2f}) '
            f'scale({scale:.4f})">{CHd.hand(name, mirror)}</g>')


def arm(side, shoulder=0.0, elbow=0.0, wrist=0.0, hand=None):
    """One arm as nested groups; angles in degrees (positive = clockwise on screen). hand: None = her own relaxed
    hand, or a hand from the hands sheet ("open", "flat", "point", "fist", "peace", "thumbs_up")."""
    J = arm_joints(side)
    drawing = part(f"{side}_arm")[:-4] + finger_lines(side) + "</g>"
    d_upper = np.subtract(J["elbow"], J["top"])
    d_lower = np.subtract(J["wrist"], J["elbow"])
    cid = f"clip_{side}"
    # joints: each side's round end is skin of radius r - JOINT_LINE over a dark disc of radius r, so a bent joint
    # shows a round knob with an outline; the dark disc is inside the arm's outline, so a straight arm hides it
    re_, rw = J["elbow_r"] - JOINT_LINE, J["wrist_r"] - JOINT_LINE
    wrist_end = ([_halfplane(J["wrist"], d_lower, True)] if hand else          # swapped hand: forearm ends at the wrist
                 [_halfplane(J["wrist"], d_lower, True), _disc(J["wrist"], rw)])
    clips = (_clip(cid + "_upper", [_halfplane(J["elbow"], d_upper, True), _disc(J["elbow"], re_)])
             + _clip(cid + "_fore", [_halfplane(J["elbow"], d_upper, False, OVERLAP), _disc(J["elbow"], re_)])
             + _clip(cid + "_fore2", wrist_end)
             + _clip(cid + "_hand", [_halfplane(J["wrist"], d_lower, False, OVERLAP), _disc(J["wrist"], rw)])
             + _clip(cid + "_sleeve", [sleeve_region(side)]))
    # (hard cuts: a soft cut through the stacked layers of a drawing leaves a faint seam line)
    forearm = _clipped(cid + "_fore", _clipped(cid + "_fore2", drawing))
    if isinstance(hand, (tuple, list)):     # (name, mix): cross-fade from her own hand to a sheet hand (no pop)
        name, mix = hand
        own = _clipped(cid + "_hand", drawing)
        hand_g = (f'<g id="{side}_hand"{_rot(wrist, J["wrist"])}>'
                  f'<g opacity="{1 - mix:.3f}">{own}</g><g opacity="{mix:.3f}">{swapped_hand(side, name, J, d_lower)}</g></g>')
        fore = f'<g id="{side}_forearm"{_rot(elbow, J["elbow"])}>{forearm}{hand_g}</g>'
    elif hand:        # the sheet hand goes over the end of the forearm (its open wrist cut hides inside the forearm)
        hand_g = f'<g id="{side}_hand"{_rot(wrist, J["wrist"])}>{swapped_hand(side, hand, J, d_lower)}</g>'
        fore = f'<g id="{side}_forearm"{_rot(elbow, J["elbow"])}>{forearm}{hand_g}</g>'
    else:
        hand_g = f'<g id="{side}_hand"{_rot(wrist, J["wrist"])}>{_clipped(cid + "_hand", drawing)}</g>'
        ring = _ring(J["wrist"], J["wrist_r"])
        fore = f'<g id="{side}_forearm"{_rot(elbow, J["elbow"])}>{ring}{hand_g}{forearm}</g>'
    upper = _clipped(cid + "_upper", drawing)
    sleeve = _clipped(cid + "_sleeve", part("torso"))
    return clips + (f'<g id="{side}_arm"{_rot(shoulder, J["shoulder"])}>{_ring(J["elbow"], J["elbow_r"])}'
                    f'{upper}{sleeve}{fore}</g>')      # forearm in front: a folded elbow shows no line across it


def body(pose=None, arms=True):
    """Everything below the neck, back to front. pose: {"right": (shoulder, elbow, wrist[, hand]), "left": (...)}
    in degrees. arms=False leaves the arms out (they are then drawn last, over the face, with arms_front)."""
    parts = part("right_shoe") + part("left_shoe") + jeans() + torso() + (arms_front(pose) if arms else "")
    return '<g id="body">' + parts + "</g>"


def arms_front(pose=None):
    pose = pose or {}
    return arm("right", *pose.get("right", ())) + arm("left", *pose.get("left", ()))
