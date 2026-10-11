"""After-Effects-style "puppet pin" animation on a single character image, in Python.

Pins sit on the picture (head, chest, hands, hair tips, feet). Each frame, the moving pins are
nudged a little (breathing, a slow sway, a head tilt, hair drifting behind) and the whole
picture is bent smoothly to follow them (thin-plate spline). Feet and the frame edges stay put.
The character keeps her exact look because nothing is redrawn.

    python puppet_warp/puppet_warp.py her.png idle.mp4 [seconds]
"""
import math
import sys

import cv2
import imageio.v2 as imageio
import numpy as np


def tps_fit(src, dst):
    """Thin-plate spline mapping src points -> displacement (dst - src). Returns a function."""
    src = np.asarray(src, float)
    disp = np.asarray(dst, float) - src
    n = len(src)

    def U(r2):
        with np.errstate(divide="ignore", invalid="ignore"):
            v = r2 * np.log(r2)
        return np.nan_to_num(v)

    d2 = ((src[:, None, :] - src[None, :, :]) ** 2).sum(-1)
    K = U(d2)
    P = np.hstack([np.ones((n, 1)), src])
    A = np.zeros((n + 3, n + 3))
    A[:n, :n], A[:n, n:], A[n:, :n] = K + np.eye(n) * 1e-3, P, P.T
    b = np.zeros((n + 3, 2))
    b[:n] = disp
    coef = np.linalg.solve(A, b)

    def f(pts):
        r2 = ((pts[:, None, :] - src[None, :, :]) ** 2).sum(-1)
        return U(r2) @ coef[:n] + coef[n] + pts @ coef[n + 1:]
    return f


def rotate(p, c, deg):
    a = math.radians(deg)
    x, y = p[0] - c[0], p[1] - c[1]
    return (c[0] + x * math.cos(a) - y * math.sin(a), c[1] + x * math.sin(a) + y * math.cos(a))


# Pins for the 1024x1536 reference drawing (x, y in pixels)
NECK = (500, 300)
HEAD = [(490, 60), (420, 140), (560, 140), (490, 170), (440, 230), (540, 230), (497, 255)]
HAIR_TIPS = [(275, 470), (300, 520), (345, 545), (405, 555), (605, 540)]
HAIR_MID = [(320, 300), (290, 400), (610, 300)]
CHEST = [(450, 430), (550, 430), (500, 480)]
SHOULDERS = [(380, 330), (620, 330)]
WAIST = [(420, 560), (580, 560)]
HANDS = [(310, 880), (690, 880)]
ELBOWS = [(330, 650), (665, 650)]
HIPS = [(360, 740), (640, 740)]
KNEES = [(440, 1060), (556, 1060)]
FEET = [(445, 1460), (555, 1460), (445, 1520), (555, 1520), (420, 1380), (580, 1380)]


def pins_at(t, period=4.0):
    w = 2 * math.pi * t / period
    breath = math.sin(w * 2) * 3.0                  # two breaths per loop
    sway = math.sin(w)                              # slow side-to-side weight shift
    tilt = 2.2 * math.sin(w - 0.4)                  # head tilt, a little behind the sway
    src, dst = [], []

    def add(points, fn):
        for p in points:
            src.append(p)
            dst.append(fn(p))

    add(FEET, lambda p: p)
    add(KNEES, lambda p: (p[0] + sway * 2, p[1]))
    add(HIPS, lambda p: (p[0] + sway * 5, p[1]))
    add(WAIST, lambda p: (p[0] + sway * 6, p[1] - breath * .3))
    add(CHEST, lambda p: (p[0] + sway * 6.5, p[1] - breath))
    add(SHOULDERS, lambda p: (p[0] + sway * 7, p[1] - breath * .8))
    add(ELBOWS, lambda p: (p[0] + sway * 6.5, p[1] - breath * .4))
    add(HANDS, lambda p: (p[0] + sway * 5 + math.sin(w - 1.0) * 3, p[1] - breath * .2))
    neck = (NECK[0] + sway * 7.5, NECK[1] - breath * .7)
    add([NECK], lambda p: neck)
    add(HEAD, lambda p: rotate((p[0] + sway * 7.5, p[1] - breath * .7), neck, tilt))
    add(HAIR_MID, lambda p: rotate((p[0] + sway * 8, p[1] - breath * .6), neck, tilt * .7))
    lag = math.sin(w - 1.3)                         # hair follows late, so it looks soft
    add(HAIR_TIPS, lambda p: (p[0] + lag * 9, p[1] - breath * .4 + abs(lag) * 1.5))
    return src, dst


def warp_frame(img, src, dst, step=8):
    h, w = img.shape[:2]
    edges = [(x, y) for x in np.linspace(0, w - 1, 6) for y in (0, h - 1)] + \
            [(x, y) for y in np.linspace(0, h - 1, 8) for x in (0, w - 1)]
    src = list(src) + edges
    dst = list(dst) + edges
    # inverse map: for each output pixel, where to sample in the source
    f = tps_fit(dst, src)
    gy, gx = np.mgrid[0:h:step, 0:w:step]
    grid = np.stack([gx.ravel(), gy.ravel()], 1).astype(float)
    d = f(grid).reshape(gx.shape[0], gx.shape[1], 2).astype(np.float32)
    d = cv2.resize(d, (w, h), interpolation=cv2.INTER_CUBIC)
    mx, my = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    return cv2.remap(img, mx + d[..., 0], my + d[..., 1], cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def main():
    src_path, out = sys.argv[1], sys.argv[2]
    seconds = float(sys.argv[3]) if len(sys.argv) > 3 else 8.0
    img = cv2.cvtColor(cv2.imread(src_path), cv2.COLOR_BGR2RGB)
    fps = 30
    with imageio.get_writer(out, fps=fps, codec="libx264", quality=8, macro_block_size=8) as wr:
        for i in range(int(seconds * fps)):
            s, d = pins_at(i / fps)
            wr.append_data(warp_frame(img, s, d))
    print("saved", out)


if __name__ == "__main__":
    main()
