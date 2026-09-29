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
SHOE_RIM = 15
SHOE_OUT = 15
LEG_OVERLAP = 40
FINGER_G = 146     # finger lines: orange-brown pixels in the hand darker (green channel) than this


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
    finger_lines = {}
    for side, sgn in (("right", -1), ("left", 1)):          # her right = viewer's left
        arm = skin & (sgn * (xx - mid) > 60) & (yy > shirt_top + 40)
        # base = all the skin (light + shade) as one shape, the shade drawn on top: no dark seams between them
        # dark specks inside the hand (the cores of the soft finger lines) become shade, not black outline
        arm_full = solid_fill(biggest(arm), 5)
        # the soft orange-brown lines between the fingers (and the crease above the thumb): their own layer
        a3 = im.astype(int)
        hand = arm_full & (yy > np.where(arm_full.any(1))[0][-1] - 110)
        R_, G_, B_ = a3[..., 0], a3[..., 1], a3[..., 2]
        core = hand & (R_ > 170) & (G_ > 85) & (G_ < FINGER_G) & (B_ < 150)
        core = cv2.morphologyEx(core.astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 11)))
        finger_lines[side] = centre_lines(core, to_old, s)
        parts[f"{side}_arm"] = {"skin": arm_full, "skin_shade": (arm & C["skin_shade"]) | (arm_full & ~arm)}
    crotch = int(np.where((jeans & (abs(xx - mid) < 6)).any(1))[0][0]) + 20       # first row where the legs part
    crotch = max(crotch, shirt_bottom + 60)
    near_legs = abs(xx - mid) < 125                                   # (dark hair pixels can look like denim)
    jeans = jeans & near_legs
    split_y = crotch + int(np.argmax(outline[crotch:, int(mid)]))   # where the legs really part (the dark V at the centre)
    hips = jeans & (yy <= split_y + 4)
    # details inside the jeans: light stitching / button (lighter than the denim) and dark seam lines
    hip_box = (yy >= shirt_bottom - 6) & (yy <= split_y + 4) & (abs(xx - mid) < 125)
    grey = im.astype(int).sum(2)
    light = hip_box & ~background & ((C["stitch"] | C["white"] | C["paper"]) | (grey > 330)) & ~C["skin"] & ~C["skin_shade"] & (np.abs(im[..., 2].astype(int) - im[..., 0].astype(int)) < 90)
    light &= cv2.erode((jeans | light).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    inner_dark = hip_box & outline & cv2.erode(cv2.morphologyEx((jeans | outline).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8)), np.ones((9, 9), np.uint8)).astype(bool)
    hull = cv2.morphologyEx(hips.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8)).astype(bool)
    # hips and legs are cut from ONE smoothed denim shape, so their edges line up exactly where they overlap
    hips_raw = smooth_mask(solid_fill((hips | ((light | inner_dark) & hull)), 11), 21)
    legs_raw = jeans & (yy > split_y - LEG_OVERLAP - 10)          # (not closed: that would bridge the gap between the legs)
    denim = cv2.morphologyEx((hips_raw | legs_raw).astype(np.uint8), cv2.MORPH_OPEN,
                             cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))).astype(bool)
    parts["hips"] = {"jeans": denim & (yy <= split_y + 4)}       # details are drawn as clean shapes (chibi_body)
    for side, sgn in (("right", -1), ("left", 1)):
        leg = denim & (yy > split_y - LEG_OVERLAP) & (sgn * (xx - mid) > -4)   # reaches up under the hips (no seam line)
        parts[f"{side}_leg"] = {"jeans": solid_fill(biggest(leg), 5)}           # one flat denim colour, no speckles
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
                                 "sole": open_(inner & C["white"]),
                                 "shade": open_(inner & outline)}                  # the darker patches on the upper
    hb = (C["hair"] | C["hair_light"] | outline) & (yy > shirt_top) & ~background
    hbo = cv2.morphologyEx(hb.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8)).astype(bool)
    parts["hair_behind"] = {"hair_dark": hbo & C["outline2"], "hair": hbo & C["hair"], "hair_light": hbo & C["hair_light"]}
    figure = cv2.morphologyEx((~background).astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    parts["backing"] = {"_": np.zeros_like(figure, bool)}
    body_union = np.zeros(figure.shape, np.uint8)
    for nm, lay in parts.items():
        if nm in ("backing", "hair_behind", "hair_behind_arms"):
            continue
        for m in lay.values():
            body_union |= m.astype(np.uint8)
    body_union = cv2.morphologyEx(body_union, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (61, 61)))
    body_union = cv2.dilate(body_union, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (55, 55)))
    backing_sil = figure.astype(bool) & body_union.astype(bool) & (yy > shirt_top - 10)   # gaps between / around the parts
    # the arms move: nothing dark may stay behind them, except inside the hair, where the hidden hair is painted in
    arms = parts["right_arm"]["skin"] | parts["left_arm"]["skin"]
    arms_zone = cv2.dilate(arms.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (RING + 8, RING + 8))).astype(bool)
    hair_px = (C["hair"] | C["hair_light"] | C["outline2"]) & ~background & (yy > shirt_top - 20) & ~arms_zone
    hair_px = cv2.morphologyEx(hair_px.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8)).astype(bool)
    # (for the hair's bottom edge: hair pixels right up to the arms' outline, which is ~9 px thick)
    hair_low = (C["hair"] | C["hair_light"] | C["outline2"]) & ~background & ~cv2.dilate(arms.astype(np.uint8), np.ones((19, 19), np.uint8)).astype(bool)
    hair_low = cv2.morphologyEx(hair_low.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8)).astype(bool)
    behind = np.zeros_like(arms)
    for sgn in (-1, 1):                                   # per side: inside the hair's outer edge and above its bottom
        side_hair = hair_px & (sgn * (xx - mid) > 60)
        rows = side_hair.any(1)
        out_x = np.where(rows, np.where(side_hair, sgn * xx, -10 ** 6).max(1) * sgn, 0)
        low = hair_low & (sgn * (xx - mid) > 60) & (yy > shirt_top + 40)   # hair bottom per column (below the shoulders) ...
        bottom = np.where(low.any(0), np.where(low, yy, -1).max(0), -1).astype(float)
        # ... as the lowest hair among the nearby columns (the arm hides the hair in the columns it covers)
        bottom = cv2.dilate(bottom.astype(np.float32)[None, :], np.ones((1, 81), np.uint8))[0]
        inside_row = rows[:, None] & (sgn * (xx - out_x[:, None]) <= 0) & (sgn * (xx - mid) > 0)
        behind |= inside_row & (yy <= bottom[None, :])
    # inside the hair (hidden or not): + every dark hair / shadow pixel of the reference not part of an arm's outline
    region = behind | (hbo & ~cv2.dilate(arms.astype(np.uint8), np.ones((13, 13), np.uint8)).astype(bool))
    region = cv2.dilate(region.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))).astype(bool)
    behind = region.copy()
    behind &= arms_zone
    paper = cv2.dilate((C["paper"] | C["white"]).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    behind = smooth_mask(behind & ~paper, 9)               # (the white gap between hand and hip stays white)
    backing_sil &= ~(arms_zone & ~region)                  # nothing dark left behind where an arm leaves the hair
    # the outline ring around the white gap between hand and hip, where the arm's own outline covers it at rest
    # (it would show as a dark loop when the arm lifts)
    gap = (C["paper"] | C["white"]) & ~background & cv2.dilate(arms.astype(np.uint8), np.ones((41, 41), np.uint8)).astype(bool) & (yy > shirt_bottom)
    gap_ring = cv2.dilate(gap.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3 * RING, 3 * RING))).astype(bool)
    under_arm = cv2.dilate(arms.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (RING, RING))).astype(bool)
    backing_sil &= ~(gap_ring & under_arm)
    behind &= ~(gap_ring & under_arm)
    parts["hair_behind_arms"] = {"hair_hidden": behind}
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
        if not name.endswith("_arm") and name not in ("backing", "hair_behind", "hair_behind_arms"):
            # an arm's outline belongs to the arm (it moves): not to the shirt / jeans silhouette next to it
            sil &= ~(under_arm & ~cv2.dilate(allm.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)).astype(np.uint8)
        if name.endswith("_leg"):                     # the outline must not poke out above / below the overlap
            sil &= (yy > split_y - LEG_OVERLAP + 4).astype(np.uint8)
        if name == "hips":
            sil &= (yy <= split_y).astype(np.uint8)
        entry = {"silhouette": blobs(sil, 300, to_old, only_biggest=True), "layers": {}}
        for lname, m in layers.items():
            entry["layers"][lname] = blobs(m, 12 if lname in ("stitch", "seam") else 40, to_old)
        if name == "backing":
            entry = {"silhouette": blobs(backing_sil, 300, to_old, only_biggest=True), "layers": {}}
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
    out["finger_lines"] = finger_lines
    denim_all = denim | parts["right_leg"]["jeans"] | parts["left_leg"]["jeans"]
    out["denim_outline"] = blobs(denim_all, 300, to_old, only_biggest=False)   # outer edge of all the jeans (clip)
    json.dump(out, open(os.path.join(HERE, "ref", "measured_body.json"), "w"))
    print({k: (len(v["silhouette"]), {a: len(b) for a, b in v["layers"].items()}) for k, v in out["parts"].items()})
    print(out["joints"])


def smooth_mask(mask, k):
    """Round off notches and corners: close then open with a k px disc."""
    d = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    m = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_CLOSE, d)
    return cv2.morphologyEx(m, cv2.MORPH_OPEN, d).astype(bool)


def solid_fill(mask, k):
    """Mask closed by k px, with every hole filled: one solid shape."""
    m = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))
    cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    out = np.zeros_like(m)
    cv2.drawContours(out, cnts, -1, 1, -1)
    return out.astype(bool)


def centre_lines(mask, to_old, scale, min_len=8):
    """Each thin, roughly vertical line in the mask as a centre line + its widest width (drawing units)."""
    n, lab, st, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8))
    out = []
    for i in range(1, n):
        ys, xs = np.where(lab == i)
        if ys.max() - ys.min() < min_len:
            continue
        rows = np.arange(ys.min(), ys.max() + 1)
        cx = np.array([xs[ys == y].mean() if (ys == y).any() else np.nan for y in rows])
        wd = np.array([(ys == y).sum() for y in rows], float)
        ok = ~np.isnan(cx)
        cx = np.interp(rows, rows[ok], cx[ok])
        k = np.ones(5) / 5
        cx = np.convolve(np.r_[[cx[0]] * 2, cx, [cx[-1]] * 2], k, "valid")
        step = max(1, len(rows) // 6)
        idx = list(range(0, len(rows), step))
        if idx[-1] != len(rows) - 1:
            idx.append(len(rows) - 1)
        pts = to_old([(cx[j], rows[j]) for j in idx])
        out.append({"points": pts, "width": round(float(np.percentile(wd, 50)) / scale, 2)})
    return out


def blobs(mask, min_area, to_old, only_biggest=False):
    n, lab, st, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8))
    if only_biggest and n > 1:
        k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
        return [to_old(traced(lab == k, (0, 0), SIGMA, EPS))]
    return [to_old(traced(lab == i, (0, 0), SIGMA, EPS)) for i in range(1, n) if st[i, cv2.CC_STAT_AREA] >= min_area]


if __name__ == "__main__":
    main(sys.argv[1])
