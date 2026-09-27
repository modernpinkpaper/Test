# Kawaii girl animations

Made from `original_sheet.png` (six poses). The poses are cut out into
`sprites/pose1.png` ... `pose6.png` with see-through backgrounds, then moved
with Python.

| File | What it does |
|---|---|
| `idle.gif` / `idle.json` | Standing, breathing, blinks, hearts float up |
| `wave.gif` / `wave.json` | Waving, rocks side to side and hops, sparkles by the hand |
| `poses.gif` / `poses.json` | Pops through all six poses with a little bounce |

![idle](idle.gif) ![wave](wave.gif) ![poses](poses.gif)

## How to use

```bash
pip install pillow numpy scipy

python kawaii_girl.py cut original_sheet.png   # only needed if you change the drawing
python kawaii_girl.py save                     # makes idle.json, wave.json, poses.json
python kawaii_girl.py gif idle.json idle.gif   # turns one into a GIF
```

In your own Python code:

```python
from kawaii_girl import load, draw_frame

anim = load("wave.json")
for frame in anim["frames"]:
    picture = draw_frame(frame)   # a Pillow image; show it, save it, or use it in pygame
```

Each frame in a `.json` file says which pose to show and how to move it
(`dx`, `dy`, `scale_x`, `scale_y`, `angle`), plus `blink`, `hearts` and `sparkles`.
