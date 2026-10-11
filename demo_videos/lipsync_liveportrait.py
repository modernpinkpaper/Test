"""Lip-sync a character video to a voice with LivePortrait (works on a normal CPU, faster on a GPU).

Keeps all of the clip's own movement and only opens/closes her mouth with the voice loudness.
The clip is enlarged to 1080 wide and cropped to 9:16 (top part, so the face is bigger).

Setup: clone https://github.com/KwaiVGI/LivePortrait, install its requirements and weights.
    python demo_videos/lipsync_liveportrait.py --lp path/to/LivePortrait clip.mp4 voice.wav out.mp4 --start 1.2
"""
import argparse
import os
import subprocess
import sys

import cv2
import imageio
import numpy as np
import soundfile as sf


def voice_levels(wav, fps, n_frames, start):
    a, sr = sf.read(wav, dtype="float32")
    if a.ndim > 1:
        a = a.mean(axis=1)
    hop = sr / fps
    lv = np.zeros(n_frames)
    for i in range(n_frames):
        t0 = int((i / fps - start) * sr)
        if t0 < 0 or t0 >= len(a):
            continue
        seg = a[t0:t0 + int(hop)]
        lv[i] = np.sqrt(np.mean(seg ** 2)) if len(seg) else 0
    lv = np.convolve(lv, np.ones(3) / 3, "same")
    return np.clip(lv / (np.percentile(lv[lv > 0], 95) if (lv > 0).any() else 1), 0, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lp", required=True, help="folder of the LivePortrait code")
    ap.add_argument("clip")
    ap.add_argument("voice")
    ap.add_argument("out")
    ap.add_argument("--start", type=float, default=0.5, help="when the voice starts (seconds)")
    ap.add_argument("--open", type=float, default=0.55, help="how wide the mouth opens on loud words")
    ap.add_argument("--cpu", action="store_true")
    args = ap.parse_args()

    sys.path.insert(0, args.lp)
    from src.config.crop_config import CropConfig
    from src.config.inference_config import InferenceConfig
    from src.live_portrait_wrapper import LivePortraitWrapper
    from src.utils.crop import paste_back, prepare_paste_back
    from src.utils.cropper import Cropper
    import torch

    inf = InferenceConfig(flag_force_cpu=args.cpu, flag_use_half_precision=not args.cpu)
    crop_cfg = CropConfig(flag_force_cpu=args.cpu)
    lp = LivePortraitWrapper(inference_cfg=inf)
    cropper = Cropper(crop_cfg=crop_cfg, flag_force_cpu=args.cpu)

    rd = imageio.get_reader(args.clip)
    fps = rd.get_meta_data()["fps"]
    frames = [f for f in rd]
    n = len(frames)
    levels = voice_levels(args.voice, fps, n, args.start)
    tmp = args.out.replace(".mp4", "_silent.mp4")
    wr = imageio.get_writer(tmp, fps=fps, codec="libx264", quality=8, macro_block_size=1)
    W, H = 1080, 1920
    for i, fr in enumerate(frames):
        h, w = fr.shape[:2]
        big = cv2.resize(fr, (W, int(h * W / w)), interpolation=cv2.INTER_CUBIC)[:H]
        big = np.ascontiguousarray(big[:big.shape[0] // 2 * 2])                        # encoder needs an even height
        if levels[i] > 0.04:
            info = cropper.crop_source_image(big, crop_cfg)
            if info is not None:
                I_s = lp.prepare_source(info["img_crop_256x256"])
                kp = lp.get_kp_info(I_s)
                f_s = lp.extract_feature_3d(I_s)
                x_s = lp.transform_keypoint(kp)
                target = [[0.02 + args.open * float(levels[i])]]
                ratio = lp.calc_combined_lip_ratio(target, info["lmk_crop"])
                x_d = x_s + lp.retarget_lip(x_s, ratio)
                x_d = lp.stitching(x_s, x_d)
                with torch.no_grad():
                    out = lp.parse_output(lp.warp_decode(f_s, x_s, x_d)["out"])[0]
                mask = prepare_paste_back(inf.mask_crop, info["M_c2o"], dsize=(W, big.shape[0]))
                big = paste_back(out, info["M_c2o"], big, mask)
        wr.append_data(big)
        if i % 24 == 0:
            print(f"frame {i}/{n}", flush=True)
    wr.close()
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", tmp, "-itsoffset", str(args.start), "-i", args.voice,
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", args.out], check=True)
    os.remove(tmp)
    print("saved", args.out)


if __name__ == "__main__":
    main()
