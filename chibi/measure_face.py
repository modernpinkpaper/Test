"""Measure the chibi reference (girl on the left of the 4-mouth sheet) and save the face geometry.

    python chibi/measure_face.py sheet.webp            # -> chibi/ref/measured_eyes.json

Eye globes are circles fitted to the lower outline; lash lines and brows are traced outlines (lightly
smoothed, then simplified to a few dozen points), so the drawing follows the reference exactly.
Coordinates are pixels of the reference sheet.
"""
import json
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DARK = 330          # r+g+b below this = liner / iris / brow


def fit_circle(pts):
    x, y = pts[:, 0].astype(float), pts[:, 1].astype(float)
    cx, cy, c = np.linalg.lstsq(np.c_[2 * x, 2 * y, np.ones(len(x))], x ** 2 + y ** 2, rcond=None)[0]
    return cx, cy, float(np.sqrt(c + cx ** 2 + cy ** 2))


def traced(mask, offset, sigma, eps):
    """Outline of the biggest blob in mask, smoothed along its length and simplified."""
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8))
    k = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    cnts, _ = cv2.findContours((lab == k).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cnts, key=cv2.contourArea)[:, 0, :].astype(float)
    if sigma:
        r = int(3 * sigma)
        w = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
        w /= w.sum()
        c = np.stack([np.convolve(np.r_[c[-r:, i], c[:, i], c[:r, i]], w, "valid") for i in (0, 1)], 1)
    c = cv2.approxPolyDP(c.astype(np.float32).reshape(-1, 1, 2), eps, True)[:, 0, :]
    return [[round(float(x) + offset[0], 1), round(float(y) + offset[1], 1)] for x, y in c]


def main(path):
    im = cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2RGB).astype(int)
    S = im.sum(2)
    out = {}
    for name, (x0, x1) in {"right": (80, 165), "left": (212, 305)}.items():      # her right eye = viewer's left
        y0, y1 = 360, 455
        rgb, sub = im[y0:y1, x0:x1], S[y0:y1, x0:x1]
        white, dark = rgb.min(2) > 215, sub < DARK
        globe = cv2.morphologyEx((white | dark).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        cnts, _ = cv2.findContours(globe, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        c = max(cnts, key=cv2.contourArea)[:, 0, :] + [x0, y0]
        ymid = c[:, 1].min() + (c[:, 1].max() - c[:, 1].min()) * .4
        ecx, ecy, er = fit_circle(c[c[:, 1] > ymid])
        # iris: rows in the lower half, where only iris (no liner) is dark -> half-widths -> ellipse
        rows = []
        for y in range(int(ecy) + 7, int(ecy + er) - 2):
            xs = np.arange(x0, x1)
            d = np.where((S[y, x0:x1] < DARK) & ((xs - ecx) ** 2 + (y - ecy) ** 2 < (er - 2) ** 2))[0]
            if len(d):
                rows.append((y, d.min() + x0, d.max() + x0))
        rows = np.array(rows, float)
        bottom = rows[-1, 0] + 2
        icx = float(np.median((rows[:, 1] + rows[:, 2]) / 2))
        irx = float(rows[:3, 2].mean() - rows[:3, 1].mean()) / 2
        iry = 32.0 * er / 34.5
        icy = bottom - iry
        yy, xx = np.mgrid[y0:y1, x0:x1]
        outside = (xx - ecx) ** 2 + (yy - ecy) ** 2 > (er - 3) ** 2
        liner = traced(dark & outside & (yy < ecy + er * .2), (x0, y0), 0.7, 0.45)
        out[f"{name}_eye"] = dict(circle=[round(ecx, 1), round(ecy, 1), round(er, 1)],
                                  iris=[round(icx, 1), round(icy, 1), round(irx, 1), round(iry, 1)],
                                  liner=liner)
    for name, (x0, x1) in {"right": (89, 170), "left": (205, 300)}.items():
        y0, y1 = 344, 375
        out[f"{name}_brow"] = traced(S[y0:y1, x0:x1] < DARK, (x0, y0), 1.2, 0.5)
    os.makedirs(os.path.join(HERE, "ref"), exist_ok=True)
    with open(os.path.join(HERE, "ref", "measured_eyes.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    print(json.dumps({k: (v if "brow" in k else {a: b for a, b in v.items() if a != "liner"}) for k, v in out.items()}))


if __name__ == "__main__":
    main(sys.argv[1])
