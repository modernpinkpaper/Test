"""Cut-out puppet built from the character sheets in puppet_sheets/ (front view).

Pieces are cut from the sheets, joined at their round joint ends, and posed by angles:
from a dance tracked with dance_capture.py, and a mouth driven by a song or voice.

    python demo_videos/puppet.py dance_pose.json song_audio.mp4 out.mp4 [--start 0 --end 14.8]
"""
import argparse
import json
import math
import os
import subprocess

import imageio
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
SHEETS = os.path.join(HERE, "puppet_sheets")
W, H, FPS = 1080, 1920, 30


# ------------------------------------------------------------------ cutting
def pieces(sheet, white=232, min_px=800):
    """Every separate drawing on a white sheet -> list of (box, RGBA image), in reading order."""
    im = np.array(Image.open(os.path.join(SHEETS, sheet)).convert("RGB")).astype(np.int16)
    near_white = (im.min(axis=2) >= white) & (np.ptp(im, axis=2) < 25)
    lab, _ = ndimage.label(near_white)
    border = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    fg = ndimage.binary_opening(~np.isin(lab, border[border > 0]), iterations=1)
    parts, _ = ndimage.label(fg)
    alpha = (np.clip(ndimage.gaussian_filter(fg.astype(np.float32), 0.8), 0, 1) * 255).astype(np.uint8)
    out = []
    for k, sl in enumerate(ndimage.find_objects(parts)):
        m = parts[sl] == k + 1
        if m.sum() < min_px:
            continue
        m = ndimage.binary_dilation(m, iterations=1)
        rgba = np.dstack([im[sl].astype(np.uint8), np.where(m, alpha[sl], 0)])
        out.append(((sl[1].start, sl[0].start, sl[1].stop, sl[0].stop), Image.fromarray(rgba)))
    out.sort(key=lambda p: (p[0][1] // 120, p[0][0]))
    return out


def load_kit():
    body = [img for _, img in pieces("01_front_parts.png", min_px=1500)]
    names = ["upper_arm_r", "head_full", "hair_front", "hair_back", "torso", "upper_arm_l",
             "lower_arm_r", "lower_arm_l", "upper_leg_r", "hips", "upper_leg_l", "lower_leg_r", "lower_leg_l"]
    kit = dict(zip(names, body))
    face = [img for _, img in pieces("03_face_kit.png", min_px=800)]
    kit["head"] = face[0]
    eyes = ["open", "half", "closed", "look_l", "look_r", "wide", "squint"]
    for i, name in enumerate(eyes):
        kit[f"eye_{name}_r"], kit[f"eye_{name}_l"] = face[1 + 2 * i], face[2 + 2 * i]
    for i, name in enumerate(["neutral", "raised", "angry", "tilt"]):
        kit[f"brow_{name}_r"], kit[f"brow_{name}_l"] = face[15 + 2 * i], face[16 + 2 * i]
    mouths = ["slight", "ah", "oh", "ee", "frown", "smirk", "laugh", "closed"]
    for i, name in enumerate(mouths):
        kit[f"mouth_{name}"] = face[23 + i]
    return kit


# ------------------------------------------------------------------ the rig
# Joint points on each piece, in sheet pixels: "pivot" is where it hangs from its parent,
# the other names are where its children attach.
RIG = {
    "hips":        dict(pivot=(139, 28), leg_r=(60, 222), leg_l=(218, 222)),
    "torso":       dict(pivot=(140, 312), neck=(140, 30), arm_r=(32, 92), arm_l=(248, 92)),
    "upper_arm_r": dict(pivot=(55, 22), end=(22, 200)),
    "upper_arm_l": dict(pivot=(33, 22), end=(68, 200)),
    "lower_arm_r": dict(pivot=(52, 14), end=(38, 290)),
    "lower_arm_l": dict(pivot=(24, 14), end=(38, 290)),
    "upper_leg_r": dict(pivot=(54, 20), end=(52, 232)),
    "upper_leg_l": dict(pivot=(54, 20), end=(52, 232)),
    "lower_leg_r": dict(pivot=(42, 38), end=(42, 250)),
    "lower_leg_l": dict(pivot=(42, 38), end=(42, 250)),
    "head":        dict(pivot=(76, 170)),
}
HEAD_SCALE, HEAD_CROP = 0.522, 350       # face-kit head -> body-sheet scale; cut the neck flare off
HAIR_FRONT_PIVOT, HAIR_BACK_PIVOT = (171, 194), (119, 200)  # hair point that sits on the neck
FACE = dict(cx=146, ex=66, ey=152, es=0.72, bx=68, by=110, bs=0.66, my=258, ms=0.55)


def rest_angle(part):
    r = RIG[part]
    if "end" not in r:
        return 0.0
    (px, py), (ex, ey) = r["pivot"], r["end"]
    return math.degrees(math.atan2(ex - px, ey - py))


def rot(v, deg):
    """Rotate a screen vector (y down) counter-clockwise as seen on screen."""
    a = math.radians(deg)
    return (v[0] * math.cos(a) + v[1] * math.sin(a), -v[0] * math.sin(a) + v[1] * math.cos(a))


def remove_skin(im, top=0.0, bottom=1.0):
    """Erase skin-coloured pixels (the round joint balls) between two heights (0-1) of a clothing piece."""
    a = np.array(im).astype(np.int16)
    h = a.shape[0]
    skin = (a[..., 0] - a[..., 2] > 35) & (a[..., 0] > 150)
    band = np.zeros_like(skin)
    band[int(top * h):int(bottom * h)] = True
    a[..., 3] = np.where(skin & band, 0, a[..., 3])
    return Image.fromarray(a.astype(np.uint8))


def soften_edges(im, px=5):
    """Shrink and feather the alpha so a face piece has no light border."""
    a = np.array(im.split()[3]).astype(np.float32) / 255
    a = ndimage.grey_erosion(a, size=(px, px))
    a = ndimage.gaussian_filter(a, px / 2.5)
    im = im.copy()
    im.putalpha(Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)))
    return im


class Puppet:
    def __init__(self, scale=1.2):
        self.kit = load_kit()
        self.s = scale
        k = self.kit
        # hide the joint balls on the clothes so pieces join cleanly
        k["torso"] = k["torso"].crop((0, 0, k["torso"].width, 345))
        k["hips"] = remove_skin(k["hips"], 0.0, 0.2)
        k["hips"] = remove_skin(k["hips"], 0.8, 1.0)
        for side in ("r", "l"):
            k[f"upper_leg_{side}"] = remove_skin(k[f"upper_leg_{side}"], 0.0, 1.0)
            k[f"lower_leg_{side}"] = remove_skin(k[f"lower_leg_{side}"], 0.0, 0.25)
        head = k["head"].crop((0, 0, k["head"].width, HEAD_CROP))
        fade = np.array(head.split()[3]).astype(np.float32)
        fade[-25:] *= np.linspace(1, 0, 25)[:, None]
        head.putalpha(Image.fromarray(fade.astype(np.uint8)))
        self.head_base = head
        self.face_parts = {n: soften_edges(im) for n, im in k.items()
                           if n.startswith(("eye_", "brow_", "mouth_"))}
        self.hair_front = soften_edges(k["hair_front"], 3)
        self.hair_back = soften_edges(k["hair_back"], 3)
        self.cache = {}

    def face(self, eyes="open", brows="neutral", mouth="closed"):
        key = (eyes, brows, mouth)
        if key not in self.cache:
            c, h = FACE, self.head_base.copy()
            for side, sx in (("r", -1), ("l", 1)):
                for kind, name, dx, y, s in (("eye", eyes, c["ex"], c["ey"], c["es"]),
                                             ("brow", brows, c["bx"], c["by"], c["bs"])):
                    im = self.face_parts[f"{kind}_{name}_{side}"]
                    im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
                    h.alpha_composite(im, (int(c["cx"] + sx * dx - im.width / 2), int(y - im.height / 2)))
            m = self.face_parts[f"mouth_{mouth}"]
            m = m.resize((int(m.width * c["ms"]), int(m.height * c["ms"])), Image.LANCZOS)
            h.alpha_composite(m, (int(c["cx"] - m.width / 2), int(c["my"] - m.height / 2)))
            h = h.resize((int(h.width * HEAD_SCALE), int(h.height * HEAD_SCALE)), Image.LANCZOS)
            self.cache[key] = h
        return self.cache[key]

    def draw_part(self, canvas, im, pivot, at, angle):
        """Paste `im` so its `pivot` sits at screen point `at`, rotated by `angle`."""
        s = self.s
        im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BILINEAR)
        px, py = pivot[0] * s, pivot[1] * s
        R = int(math.hypot(max(px, im.width - px), max(py, im.height - py))) + 2
        pad = Image.new("RGBA", (2 * R, 2 * R), (0, 0, 0, 0))
        pad.alpha_composite(im, (int(R - px), int(R - py)))
        if abs(angle) > 0.05:
            pad = pad.rotate(angle, resample=Image.BICUBIC)
        canvas.alpha_composite(pad, (int(at[0] - R), int(at[1] - R)))

    def pose_points(self, root, a):
        """Forward kinematics. root = screen point of the hips pivot. a = world angles (deg)."""
        s = self.s
        P = {}

        def child(parent_at, parent_part, parent_angle, joint):
            r = RIG[parent_part]
            v = ((r[joint][0] - r["pivot"][0]) * s, (r[joint][1] - r["pivot"][1]) * s)
            v = rot(v, parent_angle)
            return (parent_at[0] + v[0], parent_at[1] + v[1])

        P["hips"] = root
        P["torso"] = root
        for side in ("r", "l"):
            P[f"upper_leg_{side}"] = child(root, "hips", a["hips"], f"leg_{side}")
            P[f"lower_leg_{side}"] = child(P[f"upper_leg_{side}"], f"upper_leg_{side}",
                                           a[f"upper_leg_{side}"] - rest_angle(f"upper_leg_{side}"), "end")
            P[f"upper_arm_{side}"] = child(root, "torso", a["torso"], f"arm_{side}")
            P[f"lower_arm_{side}"] = child(P[f"upper_arm_{side}"], f"upper_arm_{side}",
                                           a[f"upper_arm_{side}"] - rest_angle(f"upper_arm_{side}"), "end")
        P["head"] = child(root, "torso", a["torso"], "neck")
        return P

    def render(self, canvas, root, a, face=("open", "neutral", "closed")):
        k, P = self.kit, self.pose_points(root, a)

        def part(name, angle_key=None):
            ang = a[angle_key or name] - rest_angle(name)
            self.draw_part(canvas, k[name], RIG[name]["pivot"], P[name], ang)

        head_ang = a["torso"] + a.get("head", 0)
        self.draw_part(canvas, self.hair_back, HAIR_BACK_PIVOT, P["head"], head_ang + a.get("hair", 0))
        for side in ("r", "l"):
            part(f"lower_leg_{side}")
            part(f"upper_leg_{side}")
        part("hips")
        part("torso")
        for side in ("r", "l"):
            part(f"lower_arm_{side}")
            part(f"upper_arm_{side}")
        fimg = self.face(*face)
        self.draw_part(canvas, fimg, RIG["head"]["pivot"], P["head"], head_ang)
        self.draw_part(canvas, self.hair_front, HAIR_FRONT_PIVOT, P["head"], head_ang + a.get("hair", 0) * 0.5)


REST = dict(hips=0, torso=0, head=0, hair=0,
            upper_arm_r=rest_angle("upper_arm_r"), lower_arm_r=rest_angle("lower_arm_r"),
            upper_arm_l=rest_angle("upper_arm_l"), lower_arm_l=rest_angle("lower_arm_l"),
            upper_leg_r=0, lower_leg_r=0, upper_leg_l=0, lower_leg_l=0)
