"""Trace the hair of the new, cleaner chibi reference (flat cel-shaded locks) into tone layers.

    python chibi/measure_hair2.py new_ref.png      # -> chibi/ref/measured_hair2.json

The hair is split into its 5 flat tones (k-means in Lab colour space): outline, shadow, base, light, highlight.
Each tone becomes a set of traced shapes. Drawn in order (outline silhouette, base, shadow, light, highlight)
they rebuild the locks: the gaps between the fill shapes show the outline colour as the lines between locks.

Everything is converted to the coordinates of the first reference (the face we already built), using the eye
positions of both pictures (new_to_old.json).
"""
import json
import os
import sys

import cv2
import numpy as np

from measure_face import traced

HERE = os.path.dirname(os.path.abspath(__file__))
TONES = ["outline", "shadow", "base", "light", "highlight"]     # darkest to lightest


def main(path):
    T = json.load(open(os.path.join(HERE, "ref", "new_to_old.json")))
    s, (nx, ny), (ox, oy) = T["scale"], T["new_mid"], T["old_mid"]
    to_old = lambda pts: [[round((x - nx) / s + ox, 2), round((y - ny) / s + oy, 2)] for x, y in pts]

    im = cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2RGB)
    a = im.astype(int)
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    # face (skin with the eyes etc. inside): excluded, so iris / brow browns never count as hair
    skin = ((R > 225) & (G > 160) & (B > 120) & ((R - G) < 75)).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(skin)
    face_k = lab[640, 470]
    cnts, _ = cv2.findContours((lab == face_k).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    face = np.zeros_like(skin)
    cv2.drawContours(face, [max(cnts, key=cv2.contourArea)], -1, 1, -1)
    face_d = cv2.dilate(face, np.ones((5, 5), np.uint8)).astype(bool)

    brown = ((R - B) > 28) & (R < 200) & (G < 140) & ((R - G) > 12) & ~face_d
    m = cv2.morphologyEx(brown.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    hair = lab == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))

    # 5 tones
    px = cv2.cvtColor(a[hair].astype(np.uint8).reshape(-1, 1, 3), cv2.COLOR_RGB2LAB).reshape(-1, 3).astype(np.float32)
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 0.5)
    cv2.setRNGSeed(1)
    _, lbl, cent = cv2.kmeans(px, 5, None, crit, 6, cv2.KMEANS_PP_CENTERS)
    order = np.argsort(cent[:, 0])
    rank = np.empty(5, int)
    rank[order] = np.arange(5)
    tone_img = np.full(hair.shape, -1, int)
    tone_img[hair] = rank[lbl.ravel()]
    cent_rgb = cv2.cvtColor(cent[order].reshape(-1, 1, 3).astype(np.uint8), cv2.COLOR_LAB2RGB).reshape(-1, 3)
    colours = {t: "#%02x%02x%02x" % tuple(int(v) for v in c) for t, c in zip(TONES, cent_rgb)}

    # tidy each tone: median filter on the label image removes speckle, then trace each blob
    tone_img = cv2.medianBlur((tone_img + 1).astype(np.uint8), 5).astype(int) - 1
    fill = (tone_img >= 1).astype(np.uint8)
    fill = cv2.morphologyEx(fill, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    out = {"colours": colours, "tones": {}}
    # outline silhouette: the fill grown by the outline thickness (~7 px here)
    # (+ the big darkest areas, e.g. the hair in shadow behind the neck; thin lines like arm outlines are opened away)
    dark_areas = cv2.morphologyEx(hair.astype(np.uint8), cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13)))
    sil = cv2.dilate(fill, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))) | dark_areas
    sil = cv2.morphologyEx(sil, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))) & ~face.astype(bool)
    out["silhouette"] = [to_old(p) for p in blobs(sil, 2.0, 1.0, 2000)]
    # base = all fill; then each lighter / darker tone as its own shapes on top
    out["tones"]["base"] = [to_old(p) for p in blobs(fill, 1.6, 0.9, 150)]
    for t, idx, min_area in (("shadow", 1, 120), ("light", 3, 60), ("highlight", 4, 40)):
        mt = (tone_img == idx).astype(np.uint8)
        mt = cv2.morphologyEx(mt, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        out["tones"][t] = [to_old(p) for p in blobs(mt, 1.4, 0.8, min_area)]
    # face-shaped skin area (so the face under the hair is always covered with skin)
    out["face_fill"] = to_old(traced(face.astype(bool), (0, 0), 2.0, 1.0))
    with open(os.path.join(HERE, "ref", "measured_hair2.json"), "w") as fh:
        json.dump(out, fh)
    print(colours, {k: len(v) for k, v in out["tones"].items()}, "silhouette", len(out["silhouette"]))


def blobs(mask, sigma, eps, min_area):
    """Outline of every blob in the mask bigger than min_area (holes are separate blobs of other tones)."""
    n, lab, st, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8))
    return [traced(lab == i, (0, 0), sigma, eps) for i in range(1, n) if st[i, cv2.CC_STAT_AREA] >= min_area]


if __name__ == "__main__":
    main(sys.argv[1])
