"""Cut the 12 mouth shapes out of her viseme sheet (4 x 3 grid, label under each face), line every face up with
the first one (small shifts between the drawings would make her head jump), and upscale them (Real-ESRGAN, the
sheet's faces are only ~280 px wide).

    python real/visemes.py sheet.png out_dir [esrgan.pth]

Writes out_dir/v01.png .. v12.png (same size, same face position) and out_dir/aligned_sheet.png to check by eye.
Order on the sheet: rest, M/B/P, A, AA, E, I, O, OO, F/V, L/N/D/T, TH, SH/CH.
"""
import os
import sys

import cv2
import numpy as np

NAMES = ["rest", "mbp", "a", "aa", "e", "i", "o", "oo", "fv", "l", "th", "sh"]


def cells(sheet):
    h, w = sheet.shape[:2]
    cw, ch = w / 4, h / 3
    out = []
    for r in range(3):
        for c in range(4):
            x0, y0 = int(c * cw) + 4, int(r * ch) + 4
            x1, y1 = int((c + 1) * cw) - 4, int(r * ch + ch * 0.875)            # stop above the label strip
            out.append(sheet[y0:y1, x0:x1].copy())
    hmin = min(o.shape[0] for o in out)
    wmin = min(o.shape[1] for o in out)
    return [o[:hmin, :wmin] for o in out]


def align(tiles):
    """Shift/scale/rotate each tile onto the first, matching the eyes and brows (the part that shouldn't move)."""
    ref = cv2.cvtColor(tiles[0], cv2.COLOR_BGR2GRAY).astype(np.float32) / 255
    h, w = ref.shape
    mask = np.zeros((h, w), np.uint8)
    mask[int(h * 0.22):int(h * 0.45), int(w * 0.2):int(w * 0.8)] = 1                # eyes + brows
    out, warps = [tiles[0]], [np.eye(2, 3, dtype=np.float32)]
    for t in tiles[1:]:
        g = cv2.cvtColor(t, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255
        M = np.eye(2, 3, dtype=np.float32)
        try:
            _, M = cv2.findTransformECC(ref, g, M, cv2.MOTION_AFFINE,
                                        (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6), mask, 5)
        except cv2.error:
            pass
        out.append(cv2.warpAffine(t, M, (w, h), flags=cv2.INTER_CUBIC + cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE))
        warps.append(M)
    return out, warps


def upscale(tiles, weights):
    import torch
    from spandrel import ModelLoader
    model = ModelLoader().load_from_file(weights).eval()
    out = []
    for t in tiles:
        x = torch.from_numpy(cv2.cvtColor(t, cv2.COLOR_BGR2RGB)).permute(2, 0, 1).float()[None] / 255
        with torch.no_grad():
            y = model(x)[0].clamp(0, 1).permute(1, 2, 0).numpy()
        out.append(cv2.cvtColor((y * 255).round().astype(np.uint8), cv2.COLOR_RGB2BGR))
    return out


def main(sheet_path, out_dir, weights=None):
    os.makedirs(out_dir, exist_ok=True)
    tiles, warps = align(cells(cv2.imread(sheet_path)))
    for i, M in enumerate(warps):
        print(f"{i + 1:2d} {NAMES[i]:5s} shift ({M[0, 2]:+.1f}, {M[1, 2]:+.1f}) px, scale {np.sqrt(abs(np.linalg.det(M[:, :2]))):.3f}")
    if weights:
        tiles = upscale(tiles, weights)
    for i, t in enumerate(tiles):
        cv2.imwrite(os.path.join(out_dir, f"v{i + 1:02d}_{NAMES[i]}.png"), t)
    h, w = tiles[0].shape[:2]
    s = cv2.resize(np.vstack([np.hstack(tiles[r * 4:r * 4 + 4]) for r in range(3)]), None, fx=0.5, fy=0.5)
    cv2.imwrite(os.path.join(out_dir, "aligned_sheet.png"), s)


if __name__ == "__main__":
    main(*sys.argv[1:4])
