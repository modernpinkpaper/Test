"""Trace the hands sheet (6 hands) into vector hands that attach to her wrists.

    python chibi/measure_hands.py hands_ref.png      # -> chibi/ref/measured_hands.json

For each hand: the silhouette (drawn in the outline colour), the skin on top (the dark lines between the fingers are
gaps in it), the soft shade and the orange-brown creases. The wrist is where the skin runs off the drawing with no
outline (the open cut at the bottom). Every hand is stored in its own frame: wrist centre at (0, 0), fingers pointing
up (-y), sheet pixels, with the width of the wrist cut, so it can be scaled to her wrist and turned with her forearm.
"""
import json
import os
import sys

import cv2
import numpy as np

from measure_face import traced

HERE = os.path.dirname(os.path.abspath(__file__))
# (name, a point inside the hand on the sheet, which hand it shows: "L" = a left hand, "R" = a right hand)
HANDS = [("flat", (285, 302), "R"), ("open", (728, 296), "L"), ("point", (1167, 327), "R"),
         ("fist", (288, 804), "R"), ("peace", (730, 772), "R"), ("thumbs_up", (1172, 789), "R")]
UP = 4                      # traced on a 4x upsampled mask: thin gaps between fingers keep their shape


def classify(a):
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    s = a.sum(2)
    outline = s < 330
    paper = (s > 720) & (np.abs(R - B) < 40)
    crease = ~outline & ~paper & (G < 175) & (R > 150)
    skin = ~outline & ~paper & ~crease
    shade = skin & (G < 196)
    return outline, paper, skin, shade, crease


def up_mask(m):
    return cv2.resize(cv2.GaussianBlur(m.astype(np.float32), (0, 0), 0.8), None, fx=UP, fy=UP,
                      interpolation=cv2.INTER_LINEAR) > 0.5


def shapes(m, sigma, eps, min_area, to_local):
    n, lab, st, _ = cv2.connectedComponentsWithStats(up_mask(m).astype(np.uint8))
    return [to_local(traced(lab == i, (0, 0), sigma, eps)) for i in range(1, n) if st[i, cv2.CC_STAT_AREA] >= min_area * UP ** 2]


def crease_lines(a, inside, to_local, min_area=10):
    """The orange-brown lines (palm creases, curled fingers): traced from how dark each pixel is (a soft value, blurred
    and upsampled), so a thin, broken-looking painted line comes out as one continuous tapered shape."""
    G = a[..., 1].astype(np.float32)
    dark = np.clip((196 - G) / 70, 0, 1) * inside
    m = cv2.resize(cv2.GaussianBlur(dark, (0, 0), 0.9), None, fx=UP, fy=UP, interpolation=cv2.INTER_CUBIC) > 0.28
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    return [to_local(traced(lab == i, (0, 0), 2.0, 0.8)) for i in range(1, n) if st[i, cv2.CC_STAT_AREA] >= min_area * UP ** 2]


def main(path):
    a = cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2RGB).astype(int)
    outline, paper, skin, shade, crease = classify(a)
    ink = ~paper
    n, lab, st, _ = cv2.connectedComponentsWithStats(cv2.morphologyEx(ink.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)))
    out = {"hands": {}, "colours": {}}
    for name, seed, which in HANDS:
        k = lab[seed[1], seed[0]]
        blob = lab == k
        cnts, _ = cv2.findContours(blob.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        sil = np.zeros(blob.shape, np.uint8)
        cv2.drawContours(sil, [max(cnts, key=cv2.contourArea)], -1, 1, -1)
        sil = sil.astype(bool)
        # wrist cut: the part of the hand's edge with no outline along it
        edge = sil & ~cv2.erode(sil.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
        cut = edge & ~cv2.dilate(outline.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
        n2, lab2, st2, _ = cv2.connectedComponentsWithStats(cv2.dilate(cut.astype(np.uint8), np.ones((5, 5), np.uint8)))
        kk = 1 + int(np.argmax(st2[1:, cv2.CC_STAT_AREA]))
        ys, xs = np.where((lab2 == kk) & cut)
        P = np.stack([xs, ys], 1).astype(float)
        c = P.mean(0)
        # the cut is a straight line: its direction by PCA; "up" = across it, towards the middle of the hand
        u, s_, vt = np.linalg.svd(P - c)
        along = vt[0]
        across = np.array([-along[1], along[0]])
        hy, hx = np.where(sil)
        centre = np.array([hx.mean(), hy.mean()])
        if np.dot(centre - c, across) < 0:
            across = -across
        width = float(np.ptp(P @ along))
        ang = np.arctan2(across[1], across[0]) - np.arctan2(-1, 0)          # turn "across" onto (0, -1)
        ca, sa = np.cos(-ang), np.sin(-ang)

        def to_local(pts, c=c, ca=ca, sa=sa):
            q = np.array(pts, float) / UP - c
            return [[round(float(x * ca - y * sa), 2), round(float(x * sa + y * ca), 2)] for x, y in q]

        inside = sil & ~outline
        out["hands"][name] = {
            "which": which,
            "wrist_width": round(width, 2),
            "silhouette": [to_local(traced(up_mask(sil), (0, 0), 2.0, 1.0))],
            "skin": shapes(inside, 1.5, 0.8, 30, to_local),
            "shade": shapes(shade & sil, 1.5, 0.8, 25, to_local),
            # (creases right at the wrist cut are the sheet's blurred edge, not real lines)
            "crease": [c for c in crease_lines(a, sil & ~outline, to_local) if np.mean([p[1] for p in c]) < -18],
            # dark lines inside the hand (curled fingers, thumb): outline pixels away from the outer rim
            "lines": shapes(outline & cv2.erode(sil.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))).astype(bool),
                            1.2, 0.6, 8, to_local),
        }
        print(name, "wrist", c.round(1), "width", round(width, 1), "up", across.round(2),
              {k2: len(v) for k2, v in out["hands"][name].items() if isinstance(v, list)})
    pick = lambda m: "#%02x%02x%02x" % tuple(int(v) for v in np.median(a[m], 0))
    out["colours"] = {"outline": pick(outline & ink), "skin": pick(skin & ~shade), "shade": pick(shade), "crease": pick(crease)}
    json.dump(out, open(os.path.join(HERE, "ref", "measured_hands.json"), "w"))
    print(out["colours"])


if __name__ == "__main__":
    main(sys.argv[1])
