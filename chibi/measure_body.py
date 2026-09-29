"""Trace the chibi body from the full-body reference into separate, animation-ready parts.

    python chibi/measure_body.py body_ref.png      # -> chibi/ref/measured_body.json

Every pixel is sorted into one of the reference's flat colours (outline, shirt, skin, skin shade, jeans,
jeans stitch, shoe white). Each part (neck, torso, arms, hips, legs, shoes) is its own mask; a part is stored as
  silhouette: the part grown by its dark outline (drawn first, in the outline colour)
  layers:     the traced shapes of each colour inside it (drawn on top)
Coordinates are converted to the head's drawing coordinates using the eyes of both pictures (body_to_old.json).
"""
import json
import os
import sys

import cv2
import numpy as np

from measure_face import traced

HERE = os.path.dirname(os.path.abspath(__file__))
PALETTE = {   # sampled from the reference (k-means)
    "outline": (31, 14, 8), "outline2": (44, 26, 18), "shirt": (42, 43, 44), "skin": (251, 205, 173),
    "skin_shade": (225, 171, 139), "jeans": (55, 79, 107), "stitch": (100, 109, 125), "white": (218, 218, 218),
    "paper": (255, 255, 255), "hair": (83, 55, 41), "hair_light": (140, 89, 62),
}
NAMES = list(PALETTE)
SIGMA, EPS, RING = 1.2, 0.7, 15
SHOE_RIM = 19
SHOE_OUT = 15


def classify(im):
    pal = np.array(list(PALETTE.values()), float)
    d = ((im[..., None, :].astype(float) - pal[None, None]) ** 2).sum(-1)
    return d.argmin(-1)


def main(path):
    T = json.load(open(os.path.join(HERE, "ref", "body_to_old.json")))
    s, (nx, ny), (ox, oy) = T["scale"], T["new_mid"], T["old_mid"]
    to_old = lambda pts: [[round((x - nx) / s + ox, 2), round((y - ny) / s + oy, 2)] for x, y in pts]
    im = cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2RGB)
    cls = cv2.medianBlur(classify(im).astype(np.uint8), 3)
    C = {n: cls == i for i, n in enumerate(NAMES)}
    outline = C["outline"] | C["outline2"]
    H, W = cls.shape
    yy, xx = np.mgrid[0:H, 0:W]
    mid = nx
    # background = paper-white connected to the image border; white inside the figure is real white (shoes, highlights)
    walls = cv2.dilate((C["outline"] | C["outline2"]).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    n, lab, st, _ = cv2.connectedComponentsWithStats(((C["paper"] | C["white"]) & ~walls).astype(np.uint8))
    border = set(np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]])) - {0}
    background = np.isin(lab, list(border))
    background = cv2.dilate(background.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    inner_white = (C["paper"] | C["white"]) & ~background
    skin = C["skin"] | C["skin_shade"]
    jeans = C["jeans"] | C["stitch"]

    def biggest(m, seed=None):
        n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8))
        if n < 2:
            return np.zeros_like(m)
        k = lab[seed[1], seed[0]] if seed is not None else 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
        return lab == k

    shirt = biggest(C["shirt"] & (yy > 570) & (yy < 830))
    shirt_top = int(np.where(shirt.any(1))[0][0])
    shirt_bottom = int(np.where(shirt.any(1))[0][-1])
    parts = {}
    parts["torso"] = {"shirt": shirt}
    neck = skin & (yy < shirt_top + 60) & (abs(xx - mid) < 90) & (yy > 520)
    neck_all = (skin | inner_white) & (yy < shirt_top + 70) & (abs(xx - mid) < 90) & (yy > 520)
    neckline_y = int(np.where(shirt[:, int(mid)])[0][0])            # lowest point of the neckline, at the centre
    parts["neck"] = {"skin": biggest(neck_all, seed=(int(mid), neckline_y - 12))}
    for side, sgn in (("right", -1), ("left", 1)):          # her right = viewer's left
        arm = skin & (sgn * (xx - mid) > 60) & (yy > shirt_top + 40)
        parts[f"{side}_arm"] = {"skin": arm & C["skin"], "skin_shade": arm & C["skin_shade"]}
    crotch = int(np.where((jeans & (abs(xx - mid) < 6)).any(1))[0][0]) + 20       # first row where the legs part
    crotch = max(crotch, shirt_bottom + 60)
    hips = jeans & (yy <= crotch + 10)
    # details inside the jeans: light stitching / button (lighter than the denim) and dark seam lines
    hip_box = (yy >= shirt_bottom - 6) & (yy <= crotch + 10) & (abs(xx - mid) < 125)
    grey = im.astype(int).sum(2)
    light = hip_box & ~background & ((C["stitch"] | C["white"] | C["paper"]) | (grey > 330)) & ~C["skin"] & ~C["skin_shade"] & (np.abs(im[..., 2].astype(int) - im[..., 0].astype(int)) < 90)
    light &= cv2.erode((jeans | light).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    inner_dark = hip_box & outline & cv2.erode(cv2.morphologyEx((jeans | outline).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8)), np.ones((9, 9), np.uint8)).astype(bool)
    solid = cv2.morphologyEx((hips | light | inner_dark).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((11, 11), np.uint8))
    cnts, _ = cv2.findContours(solid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    solid = np.zeros_like(solid)
    cv2.drawContours(solid, cnts, -1, 1, -1)                     # one solid denim shape, no holes
    parts["hips"] = {"jeans": solid.astype(bool)}               # details are drawn as clean shapes (chibi_body)
    for side, sgn in (("right", -1), ("left", 1)):
        leg = jeans & (yy > crotch - 10) & (sgn * (xx - mid) > -4)
        parts[f"{side}_leg"] = {"jeans": leg & C["jeans"], "stitch": leg & C["stitch"]}
    counts = jeans.sum(1)
    shoe_top = next(y for y in range(1000, H) if counts[y] < 50) - 4     # the jeans cuffs end where the shoes begin
    for side, sgn in (("right", -1), ("left", 1)):
        area = (yy > shoe_top) & (sgn * (xx - mid) > 0) & ~background
        sh = biggest(area & ~outline) if area.any() else area
        fill = np.zeros(area.shape, np.uint8)
        cnts, _ = cv2.findContours(cv2.morphologyEx(area.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8)),
                                   cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        cv2.drawContours(fill, cnts, -1, 1, -1)
        inner = cv2.erode(fill, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (SHOE_RIM, SHOE_RIM))).astype(bool)
        open_ = lambda m: cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)).astype(bool)
        parts[f"{side}_shoe"] = {"shoe": inner,           # solid black upper
                                 "white": open_(cv2.morphologyEx((inner & (C["paper"] | C["white"])).astype(np.uint8),
                                                                 cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8)).astype(bool) & inner),
                                 "sole": open_(inner & C["white"])}
    hb = (C["hair"] | C["hair_light"] | outline) & (yy > shirt_top) & ~background
    hbo = cv2.morphologyEx(hb.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8)).astype(bool)
    parts["hair_behind"] = {"hair_dark": hbo & C["outline2"], "hair": hbo & C["hair"], "hair_light": hbo & C["hair_light"]}
    out = {"colours": {n: "#%02x%02x%02x" % PALETTE[n] for n in NAMES}, "parts": {}}
    ring = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (RING, RING))
    for name, layers in parts.items():
        allm = np.zeros((H, W), bool)
        for m in layers.values():
            allm |= m
        allm = cv2.morphologyEx(allm.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)).astype(bool)
        r_ = ring if "shoe" not in name else cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (SHOE_OUT, SHOE_OUT))
        sil = cv2.dilate(allm.astype(np.uint8), r_).astype(bool) & (outline | allm | C["shirt"])
        sil = cv2.morphologyEx(sil.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
        entry = {"silhouette": blobs(sil, 300, to_old, only_biggest=True), "layers": {}}
        for lname, m in layers.items():
            entry["layers"][lname] = blobs(m, 12 if lname in ("stitch", "seam") else 40, to_old)
        out["parts"][name] = entry
    # joints (for animation): measured in the reference, in drawing coordinates
    def c(pt):
        return to_old([pt])[0]
    arm_r = parts["right_arm"]["skin"] | parts["right_arm"]["skin_shade"]
    arm_l = parts["left_arm"]["skin"] | parts["left_arm"]["skin_shade"]
    def top_mid(m):
        ys, xs = np.where(m)
        y0 = ys.min() + 5
        return (float(xs[ys < y0 + 10].mean()), float(y0))
    out["joints"] = {"neck": c((mid, shirt_top)), "right_shoulder": c(top_mid(arm_r)), "left_shoulder": c(top_mid(arm_l)),
                     "right_hip": c((mid - 60, crotch - 40)), "left_hip": c((mid + 60, crotch - 40))}
    json.dump(out, open(os.path.join(HERE, "ref", "measured_body.json"), "w"))
    print({k: (len(v["silhouette"]), {a: len(b) for a, b in v["layers"].items()}) for k, v in out["parts"].items()})
    print(out["joints"])


def blobs(mask, min_area, to_old, only_biggest=False):
    n, lab, st, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8))
    if only_biggest and n > 1:
        k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
        return [to_old(traced(lab == k, (0, 0), SIGMA, EPS))]
    return [to_old(traced(lab == i, (0, 0), SIGMA, EPS)) for i in range(1, n) if st[i, cv2.CC_STAT_AREA] >= min_area]


if __name__ == "__main__":
    main(sys.argv[1])
