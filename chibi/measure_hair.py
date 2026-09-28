"""Trace the hair of the chibi reference (left girl) into layers.

    python chibi/measure_hair.py sheet.webp      # -> chibi/ref/measured_hair.json

hair_back  : the whole hair silhouette (drawn behind face and body)
hair_front : the crown and the locks that frame the face (drawn over the forehead / cheeks)
strands    : darker strand lines and lighter shine streaks inside the hair
"""
import json
import os
import sys

import cv2
import numpy as np

from measure_face import traced

HERE = os.path.dirname(os.path.abspath(__file__))


def main(path):
    im = cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2RGB).astype(int)[:, :370]
    R, G, B = im[..., 0], im[..., 1], im[..., 2]
    S = R + G + B
    # hair fill only (brown, and lighter than the dark outlines that also run round the arms and face)
    brown = ((R - B) > 30) & (R < 150) & (G < 95) & (S > 118)
    hair = cv2.morphologyEx(brown.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(hair)
    hair = (lab == 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))).astype(np.uint8)
    hair = cv2.morphologyEx(hair, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    hair = cv2.dilate(hair, np.ones((5, 5), np.uint8))          # grow back over the hair's own outline
    yy, xx = np.mgrid[0:im.shape[0], 0:im.shape[1]]
    # back: the hair, filled solid from its left edge to its right edge down to the shoulders
    back = hair.copy()
    for y in range(im.shape[0]):
        xs = np.where(hair[y])[0]
        if len(xs) and y < 640:
            back[y, xs.min():xs.max() + 1] = 1
    back = cv2.morphologyEx(back, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    out = {"hair_back": traced(back, (0, 0), 3.5, 0.9)}
    # front: hair around the face (not over it), from the crown down to the jaw
    face = np.zeros_like(hair)
    fs = json.load(open(os.path.join(HERE, "ref", "measured_face.json")))["face_skin"]
    cv2.fillPoly(face, [np.array(fs, np.int32)], 1)
    face = cv2.dilate(face, np.ones((3, 3), np.uint8))
    x0, x1 = np.where(face.any(0))[0][[0, -1]]
    front = hair & (1 - face) & (yy < 520) & (xx > x0 - 34) & (xx < x1 + 34)
    front = cv2.morphologyEx(front, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(front)
    keep = [i for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] > 400]
    out["hair_front"] = [traced(lab == i, (0, 0), 3.0, 0.8) for i in keep]
    out["face_box"] = [int(x0), int(x1)]
    # strands: long thin darker lines and lighter streaks inside the hair (not along its edges)
    inner = cv2.erode(hair, np.ones((9, 9), np.uint8)).astype(bool) & ~cv2.dilate(face, np.ones((9, 9), np.uint8)).astype(bool)
    base = np.median(S[inner])
    strands = {"dark": [], "light": []}
    for kind, m in (("dark", inner & (S < base - 32)), ("light", inner & (S > base + 26))):
        m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
        n, lab, stats, _ = cv2.connectedComponentsWithStats(m)
        for i in range(1, n):
            w, h, area = stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT], stats[i, cv2.CC_STAT_AREA]
            if area >= 20 and max(w, h) >= 14 and max(w, h) / max(1, min(w, h)) >= 2.0:
                strands[kind].append(traced(lab == i, (0, 0), 1.5, 0.8))
    out["strands"] = strands
    # hairline: the top and side edges of the visible face skin, per column / row (for a smooth arch)
    skin = ((R > 225) & (G > 160) & (B > 120) & ((R - G) < 75)).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(skin)
    fk = lab[440, 186]
    fm = (lab == fk)
    top = []
    for x in range(95, 285, 5):
        ys = np.where(fm[250:420, x])[0]
        if len(ys):
            top.append([x, int(ys[0]) + 250])
    sides = []
    for y in range(300, 505, 5):
        xs = np.where(fm[y, 40:340])[0]
        if len(xs):
            sides.append([y, int(xs[0]) + 40, int(xs[-1]) + 40])
    out["hairline_top"], out["face_sides"] = top, sides
    # the two long side locks below the shoulders: outer and inner edge per row, and the lowest tip
    locks = {}
    hb = hair.astype(bool)
    for side, (xa, xb) in (("right", (0, 150)), ("left", (230, 370))):
        rows = []
        for y in range(560, im.shape[0], 4):
            xs = np.where(hb[y, xa:xb])[0]
            if len(xs) > 2:
                rows.append([y, int(xs[0]) + xa, int(xs[-1]) + xa])
        locks[side] = rows
    out["locks"] = locks
    body = (S < 700) & ~hair.astype(bool) & (yy > 505)
    tmp = {"skin": [], "clothes": []}
    for kind, m in (("skin", body & (R > 200)), ("clothes", body & (R < 120) & ((R - B) < 28))):
        m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        n, lab, stats, _ = cv2.connectedComponentsWithStats(m)
        for i in range(1, n):
            if stats[i, cv2.CC_STAT_AREA] > 150:
                tmp[kind].append(traced(lab == i, (0, 0), 1.5, 0.8))
    out["temp_body"] = tmp
    c = lambda x, y: "#%02x%02x%02x" % tuple(im[y, x])
    out["colours"] = {"base": "#%02x%02x%02x" % tuple(np.median(im[inner], 0).astype(int)),
                      "dark": "#%02x%02x%02x" % tuple(np.median(im[inner & (S < base - 50)], 0).astype(int)),
                      "light": "#%02x%02x%02x" % tuple(np.median(im[inner & (S > base + 40)], 0).astype(int)),
                      "outline": c(18, 450)}
    with open(os.path.join(HERE, "ref", "measured_hair.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    print("back pts", len(out["hair_back"]), "front pieces", [len(p) for p in out["hair_front"]],
          "strands", {k: len(v) for k, v in strands.items()}, out["colours"])


if __name__ == "__main__":
    main(sys.argv[1])
