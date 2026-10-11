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




def girl_offsets(im):
    """x/y offset of each of the 4 girls relative to the first, by matching the eye area."""
    g = cv2.cvtColor(im.astype(np.uint8), cv2.COLOR_RGB2GRAY)
    tpl = g[360:450, 80:300]
    offs = []
    for x0 in (0, 360, 720, 1080):
        area = g[330:480, max(x0 + 40, 0):x0 + 340]
        _, _, _, loc = cv2.minMaxLoc(cv2.matchTemplate(area, tpl, cv2.TM_CCOEFF_NORMED))
        offs.append((loc[0] + max(x0 + 40, 0) - 80, loc[1] + 330 - 360))
    return offs


def measure_face(path):
    im = cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2RGB).astype(int)
    R, G, B = im[..., 0], im[..., 1], im[..., 2]
    out = {"girl_offsets": girl_offsets(im)}
    # face skin: connected skin-coloured area around the nose (girl 1)
    skin = (R > 225) & (G > 160) & (G < 225) & (B > 120) & (B < 200) & ((R - G) < 75)
    sub = skin[250:540, 60:330].astype(np.uint8)
    sub = cv2.morphologyEx(sub, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(sub)
    k = lab[440 - 250, 186 - 60]
    out["face_skin"] = traced(lab == k, (60, 250), 2.0, 0.8)
    # ears: the separate skin patches either side of the face
    ears = {}
    for side, (ex, ey) in (("right", (72, 455)), ("left", (318, 428))):
        box = (ex - 30, ey - 45, ex + 30, ey + 45)
        m = skin[box[1]:box[3], box[0]:box[2]] | (((R - G) > 40) & (R > 220))[box[1]:box[3], box[0]:box[2]]
        m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        n2, lab2, _, _ = cv2.connectedComponentsWithStats(m)
        kk = lab2[ey - box[1], ex - box[0]]
        if kk:
            ears[side] = traced(lab2 == kk, (box[0], box[1]), 1.2, 0.6)
    out["ears"] = ears
    c = lambda x, y: "#%02x%02x%02x" % tuple(im[y, x])
    out["colours"] = {"skin": c(186, 400), "jaw_line": c(186, 503), "nose": c(184, 442), "blush": c(106, 457),
                      "rim": c(186 - 30 + out["girl_offsets"][1][0], 458), "tongue": c(186 + out["girl_offsets"][1][0], 466),
                      "smile": c(186, 470)}
    # mouths (one per girl): reddish = R - G > 75; tongue = the lighter pink inside
    mouths = {}
    for name, (dx, dy) in zip(("smile", "open", "wide", "oh"), out["girl_offsets"]):
        x0, y0 = 150 + dx, 445 + dy
        r, g_, b = R[y0:y0 + 55, x0:x0 + 80], G[y0:y0 + 55, x0:x0 + 80], B[y0:y0 + 55, x0:x0 + 80]
        red = (r - g_) > 75
        m = {"outline": traced(red, (x0 - dx, y0 - dy), 0.8, 0.5)}
        tongue = (red & (r > 232) & (g_ > 118) & (b > 128)).astype(np.uint8)
        tongue = cv2.morphologyEx(tongue, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        if name != "smile" and tongue.sum() > 30:
            ys, xs = np.where(tongue > 0)
            (ex, ey), (ea, eb), ang = cv2.fitEllipse(np.c_[xs, ys].astype(np.float32))
            m["tongue"] = [round(ex + x0 - dx, 1), round(ey + y0 - dy, 1), round(ea / 2, 1), round(eb / 2, 1), round(ang, 1)]
        mouths[name] = m
    out["mouths"] = mouths
    # nose dot and blush (girl 1)
    ys, xs = np.where(((R - G) > 58)[430:455, 170:200] & (G[430:455, 170:200] < 190))
    out["nose"] = [round(float(xs.mean()) + 170, 1), round(float(ys.mean()) + 430, 1), round(float(np.sqrt(len(xs) / np.pi)), 1)]
    blush = []
    for bx0, bx1 in ((85, 135), (240, 295)):
        ys, xs = np.where(((R - G) > 62)[430:485, bx0:bx1] & (R[430:485, bx0:bx1] > 230))
        blush.append([round(float(xs.mean()) + bx0, 1), round(float(ys.mean()) + 430, 1),
                      round(float(xs.std()) * 2.2, 1), round(float(ys.std()) * 2.2, 1)])
    out["blush"] = blush
    with open(os.path.join(HERE, "ref", "measured_face.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    print({k: v for k, v in out.items() if k not in ("face_skin", "mouths")}, "face pts", len(out["face_skin"]))


if __name__ == "__main__":
    main(sys.argv[1])
    measure_face(sys.argv[1])
