# Midjourney prompts for the character clips

## Step 1: make 2 starting pictures (stills)
Upload her picture to Midjourney and use it as the **Omni Reference** (drag it into the prompt bar and pick "Omni Reference"). This keeps her face and outfit the same every time. Replace `<her picture>` with that link.

**A. Talking picture (knees up)**, used for talking clips and LivePortrait:
```
a young woman with long wavy brown hair, fitted black t-shirt, high-waisted blue jeans, facing the camera, friendly relaxed expression, mouth closed, eyes open looking at the camera, arms relaxed at her sides, framed from the knees up, centered, soft even lighting, plain solid light pink background, stylized 3D cartoon illustration, no text --ar 9:16 --oref <her picture> --ow 400 --v 7
```

**B. Full-body picture**, used for walking and turning:
```
a young woman with long wavy brown hair, fitted black t-shirt, high-waisted blue jeans, white sneakers, standing facing the camera, friendly smile, full body from head to feet, centered with space around her, soft even lighting, plain solid light pink background, stylized 3D cartoon illustration, no text --ar 9:16 --oref <her picture> --ow 400 --v 7
```

Pick the best result of each and keep using **the same two pictures** for every clip below.

## Step 2: animate
Open the picture, press **Animate > Manual**, paste the motion prompt, and choose the settings shown. Each clip is 5 seconds. Download each clip and name it as shown.

| # | File name | Start picture | Motion | Loop | Motion prompt |
|---|---|---|---|---|---|
| 1 | `talk.mp4` | A | Low | On | she talks to the camera naturally with small head movements and blinks, small hand gestures, friendly expression, camera static, plain pink background |
| 2 | `wave.mp4` | A | Low | On | she smiles and waves at the camera with one hand, then lowers it, camera static, plain pink background |
| 3 | `shrug.mp4` | A | Low | Off | she shrugs with both palms up and a playful "whatever" face, camera static, plain pink background |
| 4 | `point.mp4` | A | Low | Off | she points at the camera with a confident smirk, camera static, plain pink background |
| 5 | `heart.mp4` | A | Low | Off | she places both hands on her heart and smiles warmly, camera static, plain pink background |
| 6 | `hip.mp4` | A | Low | Off | she puts one hand on her hip and raises one eyebrow, sassy expression, camera static, plain pink background |
| 7 | `arms_crossed.mp4` | A | Low | Off | she crosses her arms and rolls her eyes playfully, camera static, plain pink background |
| 8 | `laugh.mp4` | A | Low | Off | she laughs and tilts her head back a little, camera static, plain pink background |
| 9 | `water.mp4` | A | Low | Off | she lifts a clear water bottle, takes a sip, and smiles at the camera, camera static, plain pink background |
| 10 | `walk_in.mp4` | B | High | Off | she walks toward the camera confidently and stops, smiling, camera static, plain pink background |
| 11 | `walk_across.mp4` | B | High | Off | she walks from the left side to the right side of the frame, natural walk, camera static, plain pink background |
| 12 | `turn.mp4` | B | High | Off | she slowly turns around in a full circle and faces the camera again, camera static, plain pink background |

## Tips
- Always keep "camera static" and "plain pink background" in the motion prompt. A still camera and a plain background make the clips easy to join and to cut her out of.
- If a clip looks wrong (extra fingers, a face change), press **Animate** again. It's usually right within 1-3 tries.
- Use **Extend** only if you need a longer version of a move.
- Start with 1, 2, 3 and 10 to test before making all 12.

## Mouth library (for the lip-sync tool)
"Half-body shot" = head down to the knees. "Close-up" = head and shoulders. Close-ups make the mouth big and sharp.

**C. Close-up picture** (Omni Reference with her picture):
```
close-up portrait of a young woman with long wavy brown hair and a fitted black t-shirt, head and shoulders, facing the camera, looking straight into the lens, mouth closed, relaxed friendly expression, soft even front lighting, plain solid light pink background, stylized 3D cartoon illustration, no text --ar 9:16 --oref <her picture> --ow 400 --v 7
```

Animate picture C with **Manual, Low motion, Loop off**. End every prompt with: *camera static, she keeps facing the camera, plain pink background*. Midjourney gives 4 videos per prompt; keep all of them. Name them like `mouth_04_ah_1.mp4`.

| # | For | Motion prompt |
|---|---|---|
| 1 | normal talking | she talks naturally to the camera, saying different words, mouth clearly visible |
| 2 | excited talking | she talks excitedly and fast to the camera, very expressive mouth |
| 3 | calm talking | she talks slowly and calmly to the camera, gentle expression |
| 4 | "ah" | she says "aah" opening her mouth wide, then closes it, then says it again |
| 5 | "ee" | she smiles wide showing her teeth, saying "cheese", then relaxes, then smiles again |
| 6 | "oh" | she says "oh!" with round open lips, surprised, then says it again |
| 7 | "oo" | she pushes her lips forward into a small round "oo" shape, then relaxes, then again |
| 8 | M / B / P | she presses her lips together saying "mmm", then opens them, repeating a few times |
| 9 | F / V | she gently rests her top teeth on her lower lip like saying "fff", then relaxes, then again |
| 10 | laughing | she laughs happily with her mouth open, then smiles |

Download in HD. For the body clips above, start the talking-type moves (wave, shrug, point, heart, hip, arms crossed, laugh, water) from the half-body picture A; walking and turning stay on the full-body picture B.
