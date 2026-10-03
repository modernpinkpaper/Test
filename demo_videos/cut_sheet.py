"""Cut a character sheet (white background, poses in a grid) into see-through PNGs.

    python demo_videos/cut_sheet.py sheet.png COLS ROWS out_prefix
Example:
    python demo_videos/cut_sheet.py mouths.png 4 1 demo_videos/girl_sprites/mouth
"""
import sys

import numpy as np
from PIL import Image
from scipy import ndimage


def cut(path, cols, rows, prefix, white=232, min_px=3000):
    im = np.array(Image.open(path).convert("RGB")).astype(np.int16)
    h, w, _ = im.shape
    near_white = (im.min(axis=2) >= white) & (np.ptp(im, axis=2) < 25)
    # background = near-white pixels connected to the image border
    lab, _ = ndimage.label(near_white)
    border = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    bg = np.isin(lab, border[border > 0])
    fg = ~bg
    fg = ndimage.binary_opening(fg, iterations=1)
    parts, n = ndimage.label(fg)
    sizes = ndimage.sum(fg, parts, range(1, n + 1))
    centers = ndimage.center_of_mass(fg, parts, range(1, n + 1))
    # soft edge: fade the outermost 2 px
    alpha = ndimage.gaussian_filter(fg.astype(np.float32), 0.8)
    rgba = np.dstack([im.astype(np.uint8), (np.clip(alpha, 0, 1) * 255).astype(np.uint8)])
    out = []
    for r in range(rows):
        for c in range(cols):
            keep = np.zeros_like(fg)
            for k, (sz, (cy, cx)) in enumerate(zip(sizes, centers)):
                if sz >= min_px and c * w / cols <= cx < (c + 1) * w / cols and r * h / rows <= cy < (r + 1) * h / rows:
                    keep |= parts == k + 1
            ys, xs = np.where(keep)
            if not len(ys):
                continue
            m = ndimage.binary_dilation(keep, iterations=2)
            one = rgba.copy()
            one[..., 3] = np.where(m, one[..., 3], 0)
            y0, y1, x0, x1 = ys.min() - 3, ys.max() + 4, xs.min() - 3, xs.max() + 4
            crop = Image.fromarray(one[max(0, y0):y1, max(0, x0):x1])
            name = f"{prefix}{len(out) + 1}.png"
            crop.save(name)
            out.append((name, crop.size, (int(max(0, x0)), int(max(0, y0)))))
    return out


if __name__ == "__main__":
    for o in cut(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]):
        print(o)
