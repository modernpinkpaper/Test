"""The brand character, v3: detailed face (her_face.py) on a fashion-proportioned, poseable body.

Hourglass figure (shoulders, bust, defined waist, curvy hips), slender "rubber hose" arms and legs with
a real shape (thigh > knee > calf > ankle, upper arm > elbow > forearm > wrist) drawn through the joints
every frame, so any pose (hand-made or from MediaPipe / Mixamo / CMU motion) bends with no puppet joints.

    python demo_videos/her_rig2.py poses.png
"""
import math
import sys

import cairosvg
import numpy as np

import her_face as F

SKIN, SKIN_SH, SKIN_HI, LINE = F.SKIN, F.SKIN_SH, F.SKIN_HI, F.LINE
JEANS, JEANS_SH, JEANS_HI, STITCH = "#3f6aa5", "#2c4d82", "#6e98cc", "#d9a35c"
OUT = f'stroke="{LINE}" stroke-width="2.4" stroke-linejoin="round"'

REST = dict(
    neck=(540, 560), head_tilt=0.0, head=(540, 378), body_x=0.0,
    sh_r=(400, 612), el_r=(378, 800), wr_r=(392, 985),
    sh_l=(680, 612), el_l=(702, 800), wr_l=(688, 985),
    hip_r=(480, 1030), kn_r=(488, 1385), an_r=(500, 1730),
    hip_l=(600, 1030), kn_l=(592, 1385), an_l=(580, 1730),
    mouth="smile", blink=0.0, brow=0.0, look=(0.0, 0.0),
)
ARM = [(0, 42), (0.2, 40), (0.47, 27), (0.6, 31), (0.85, 24), (1, 21)]
LEG = [(0, 140), (0.22, 124), (0.48, 66), (0.6, 74), (0.78, 56), (1, 42)]


def catmull(p0, p1, p2, n=40):
    pts = [np.array(p, float) for p in (p0, p0, p1, p2, p2)]
    out = []
    for i in range(1, 3):
        a, b, c, d = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        for t in np.linspace(0, 1, n, endpoint=(i == 2)):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * b) + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t2 + (-a + 3 * b - 3 * c + d) * t3))
    return np.array(out)


def tube(curve, profile):
    """Shape along a curve; profile = [(t, width), ...] from start (0) to end (1)."""
    n = len(curve)
    ts, ws = zip(*profile)
    left, right = [], []
    for i in range(n):
        a, b = curve[max(i - 1, 0)], curve[min(i + 1, n - 1)]
        d = (b - a) / (np.linalg.norm(b - a) + 1e-9)
        nrm = np.array([-d[1], d[0]])
        w = np.interp(i / (n - 1), ts, ws) / 2
        left.append(curve[i] + nrm * w)
        right.append(curve[i] - nrm * w)
    pts = left + right[::-1]
    return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + " Z"


def angle(a, b):
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))


def hand(wr, el, side):
    ang = angle(el, wr) - 90
    s = 1 if side == "r" else -1
    return f"""<g transform="translate({wr[0]:.1f},{wr[1]:.1f}) rotate({ang:.1f}) scale(1.4)">
      <path d="M{-12 * s},-6 C{-16 * s},14 {-14 * s},34 {-6 * s},48 C{-2 * s},56 {4 * s},60 {8 * s},58 C{14 * s},52 {15 * s},34 {13 * s},-6 Z" fill="url(#limb)" {OUT}/>
      <path d="M{-4 * s},44 C{-4 * s},54 {-2 * s},62 {1 * s},66 M{3 * s},44 C{4 * s},54 {5 * s},62 {7 * s},64 M{9 * s},40 C{11 * s},48 {12 * s},54 {12 * s},58"
            fill="none" stroke="{SKIN_SH}" stroke-width="2" stroke-linecap="round"/>
      <path d="M{-11 * s},10 C{-20 * s},18 {-22 * s},30 {-17 * s},36 C{-12 * s},34 {-10 * s},26 {-8 * s},20" fill="url(#limb)" {OUT}/>
      <path d="M{-2 * s},62 L{-1 * s},67 M{6 * s},62 L{7 * s},66" stroke="#f5d3c6" stroke-width="3" stroke-linecap="round"/>
    </g>"""


def arm(p, side):
    sh, el, wr = p[f"sh_{side}"], p[f"el_{side}"], p[f"wr_{side}"]
    c = catmull(sh, el, wr)
    nx, ny = p["neck"]
    d = np.array(sh, float) - np.array([nx, ny + 60], float)
    inner = np.array(sh, float) - d / (np.linalg.norm(d) + 1e-9) * 30
    sc = catmull(inner, sh, el)
    k = int(len(sc) * 0.72)
    sleeve = tube(sc[:k], [(0, 74), (0.5, 66), (1, 56)])
    hem, before = sc[k - 1], sc[k - 3]
    dv = (hem - before) / (np.linalg.norm(hem - before) + 1e-9)
    nv = np.array([-dv[1], dv[0]]) * 28
    hem_line = f"M{hem[0] + nv[0]:.1f},{hem[1] + nv[1]:.1f} L{hem[0] - nv[0]:.1f},{hem[1] - nv[1]:.1f}"
    return f"""<g id="arm_{side}"><path d="{tube(c, ARM)}" fill="url(#limb)" {OUT}/>
      <circle cx="{sh[0]}" cy="{sh[1] + 4}" r="30" fill="url(#tee)"/><path d="{sleeve}" fill="url(#tee)"/>
      <path d="{hem_line}" stroke="{LINE}" stroke-width="2.4" stroke-linecap="round"/>{hand(wr, el, side)}</g>"""


def shoe(an, side):
    s = 1 if side == "l" else -1
    return f"""<g transform="translate({an[0]:.1f},{an[1]:.1f})">
      <path d="M{-22 * s},-14 C{-30 * s},20 {-28 * s},50 {-4 * s},58 L{50 * s},58 C{66 * s},52 {64 * s},32 {40 * s},16 C{26 * s},6 {20 * s},-6 {18 * s},-14 Z" fill="url(#shoe)" {OUT}/>
      <path d="M{-30 * s},44 C{-18 * s},56 {36 * s},58 {64 * s},48 L{62 * s},62 L{-6 * s},64 C{-22 * s},62 {-30 * s},54 {-30 * s},44 Z" fill="#d6d7e0" {OUT}/>
      <path d="M{-10 * s},0 L{12 * s},-3 M{-10 * s},11 L{16 * s},8 M{-8 * s},22 L{20 * s},19" stroke="#c0c2cf" stroke-width="2.6" stroke-linecap="round"/>
      <path d="M{-18 * s},-12 L{16 * s},-12" stroke="{SKIN_SH}" stroke-width="10"/>
    </g>"""


def leg(p, side):
    """Returns (shoe, jeans shape, details) so the hips and both legs can share one outline."""
    hip, kn, an = p[f"hip_{side}"], p[f"kn_{side}"], p[f"an_{side}"]
    c = catmull(hip, kn, an)
    k = c[int(len(c) * 0.48)]
    s = 1 if side == "l" else -1
    details = f"""
      <path d="M{k[0] - 14:.1f},{k[1] - 4:.1f} C{k[0] - 6:.1f},{k[1] + 5:.1f} {k[0] + 6:.1f},{k[1] + 5:.1f} {k[0] + 14:.1f},{k[1] - 4:.1f}"
            fill="none" stroke="{JEANS_SH}" stroke-width="2.4" stroke-linecap="round" opacity=".8"/>
      <path d="M{an[0] - 19:.1f},{an[1] - 30:.1f} L{an[0] + 19:.1f},{an[1] - 30:.1f}" stroke="{JEANS_SH}" stroke-width="3" opacity=".6"/>
      <path d="M{hip[0] + s * 26:.1f},{hip[1] + 40:.1f} C{hip[0] + s * 24:.1f},{hip[1] + 140:.1f} {k[0] + s * 16:.1f},{k[1] - 120:.1f} {k[0] + s * 12:.1f},{k[1] - 20:.1f}"
            fill="none" stroke="{JEANS_HI}" stroke-width="9" opacity=".25" stroke-linecap="round"/>"""
    return shoe(an, side), tube(c, LEG), details


def pants(p, jeans_d, seam):
    """Hips + both legs as one shape: an outline layer under a fill layer, so there are no joins."""
    (sr, lr, dr), (sl, ll, dl) = leg(p, "r"), leg(p, "l")
    shapes = [jeans_d, lr, ll]
    outline = "".join(f'<path d="{d}"/>' for d in shapes)
    fill = "".join(f'<path d="{d}"/>' for d in shapes[1:] + shapes[:1])  # hips last: hide the leg tops
    cx = (p["hip_r"][0] + p["hip_l"][0]) / 2
    # one gradient in page space for hips and legs, so no seam where they meet
    grad = (f'<linearGradient id="jeansU" gradientUnits="userSpaceOnUse" x1="{cx - 145}" y1="0" x2="{cx + 145}" y2="0">'
            f'<stop offset="0" stop-color="{JEANS_SH}"/><stop offset=".26" stop-color="{JEANS_HI}"/><stop offset=".5" stop-color="{JEANS}"/>'
            f'<stop offset=".66" stop-color="{JEANS_HI}"/><stop offset="1" stop-color="{JEANS_SH}"/></linearGradient>')
    return (f'{grad}{sr}{sl}<g fill="{LINE}" stroke="{LINE}" stroke-width="5" stroke-linejoin="round">{outline}</g>'
            f'<g fill="url(#jeansU)">{fill}</g>{dr}{dl}{seam}')


def body(p):
    """Tee (bust, waist) and high-waisted jeans (hips), built around the shoulders and hips."""
    sr, sl, hr, hl = p["sh_r"], p["sh_l"], p["hip_r"], p["hip_l"]
    nx, ny = p["neck"]
    cx = (sr[0] + sl[0]) / 2
    top = sr[1]
    wy, hemy, hipy = top + 250, top + 300, hr[1] - 10
    tee = (f"M{sr[0] + 6},{top - 14} C{nx - 60},{ny + 12} {nx - 52},{ny + 6} {nx - 46},{ny + 4} "
           f"C{nx - 30},{ny + 78} {nx + 30},{ny + 78} {nx + 46},{ny + 4} C{nx + 52},{ny + 6} {nx + 60},{ny + 12} {sl[0] - 6},{top - 14} "
           f"C{sl[0] + 22},{top + 10} {sl[0] + 16},{top + 70} {sl[0] - 4},{top + 96} "            # right armpit
           f"C{sl[0] + 4},{top + 140} {cx + 104},{top + 190} {cx + 82},{wy} "                     # bust side -> waist
           f"C{cx + 86},{wy + 24} {cx + 92},{hemy - 16} {cx + 94},{hemy} L{cx - 94},{hemy} "
           f"C{cx - 92},{hemy - 16} {cx - 86},{wy + 24} {cx - 82},{wy} "
           f"C{cx - 104},{top + 190} {sr[0] - 4},{top + 140} {sr[0] + 4},{top + 96} "
           f"C{sr[0] - 16},{top + 70} {sr[0] - 22},{top + 10} {sr[0] + 6},{top - 14} Z")
    side = lambda k: (f"C{cx + k * 100},{hemy + 20} {cx + k * 134},{hipy - 60} {cx + k * 138},{hipy + 10} "
                      f"C{cx + k * 140},{hipy + 50} {cx + k * 132},{hipy + 84} {cx + k * 122},{hipy + 124}")
    jeans = (f"M{cx - 90},{hemy - 22} L{cx + 90},{hemy - 22} {side(1)} "
             f"C{cx + 80},{hipy + 116} {cx + 20},{hipy + 118} {cx},{hipy + 124} C{cx - 20},{hipy + 118} {cx - 80},{hipy + 116} {cx - 122},{hipy + 124} "
             f"C{cx - 132},{hipy + 84} {cx - 140},{hipy + 50} {cx - 138},{hipy + 10} C{cx - 134},{hipy - 60} {cx - 100},{hemy + 20} {cx - 90},{hemy - 22} Z")
    return f"""
  <g id="pants">{pants(p, jeans, f'''<g>
    <path d="M{cx},{hemy + 90} C{cx},{hipy + 40} {cx - 2},{hipy + 100} {cx - 8},{hipy + 126}" fill="none" stroke="{JEANS_SH}" stroke-width="3" opacity=".8"/></g>''')}</g>
  <g id="waist">
    <path d="M{cx - 92},{hemy - 22} L{cx + 92},{hemy - 22} L{cx + 96},{hemy + 8} L{cx - 96},{hemy + 8} Z" fill="{JEANS_SH}" {OUT}/>
    <path d="M{cx - 94},{hemy + 1} L{cx + 94},{hemy + 1}" stroke="{STITCH}" stroke-width="2" stroke-dasharray="6 5"/>
    <rect x="{cx - 64}" y="{hemy - 26}" width="9" height="38" rx="3" fill="{JEANS_SH}" {OUT}/><rect x="{cx + 55}" y="{hemy - 26}" width="9" height="38" rx="3" fill="{JEANS_SH}" {OUT}/>
    <circle cx="{cx}" cy="{hemy - 7}" r="8" fill="#d2d5de" stroke="#858a98" stroke-width="2"/>
    <path d="M{cx},{hemy + 8} L{cx},{hemy + 78} C{cx},{hemy + 90} {cx + 12},{hemy + 96} {cx + 22},{hemy + 86}" fill="none" stroke="{STITCH}" stroke-width="2" stroke-dasharray="6 5"/>
    <path d="M{cx - 124},{hemy + 16} C{cx - 104},{hemy + 52} {cx - 76},{hemy + 60} {cx - 58},{hemy + 54}" fill="none" stroke="{STITCH}" stroke-width="2" stroke-dasharray="6 5"/>
    <path d="M{cx + 124},{hemy + 16} C{cx + 104},{hemy + 52} {cx + 76},{hemy + 60} {cx + 58},{hemy + 54}" fill="none" stroke="{STITCH}" stroke-width="2" stroke-dasharray="6 5"/>
  </g>
  <g id="tee">
    <path d="M{nx - 34},{ny - 4} L{nx - 34},{ny + 30} L{nx + 34},{ny + 30} L{nx + 34},{ny - 4} Z" fill="{SKIN_SH}"/>
    <path d="{tee}" fill="url(#tee)" {OUT}/>
    <path d="M{nx - 46},{ny + 4} C{nx - 30},{ny + 78} {nx + 30},{ny + 78} {nx + 46},{ny + 4} C{nx + 20},{ny + 16} {nx - 20},{ny + 16} {nx - 46},{ny + 4} Z" fill="url(#chest)"/>
    <path d="M{nx - 46},{ny + 4} C{nx - 30},{ny + 78} {nx + 30},{ny + 78} {nx + 46},{ny + 4}" fill="none" stroke="#0c0a0d" stroke-width="6"/>
    <path d="M{nx - 40},{ny + 24} C{nx - 26},{ny + 30} {nx - 12},{ny + 32} {nx - 4},{ny + 29}" fill="none" stroke="{LINE}" stroke-width="2" opacity=".55"/>
    <path d="M{nx + 40},{ny + 24} C{nx + 26},{ny + 30} {nx + 12},{ny + 32} {nx + 4},{ny + 29}" fill="none" stroke="{LINE}" stroke-width="2" opacity=".55"/>
    <path d="M{nx - 6},{ny + 58} C{nx - 2},{ny + 64} {nx + 2},{ny + 64} {nx + 6},{ny + 58}" fill="none" stroke="{LINE}" stroke-width="2" opacity=".5"/>
    <path d="M{cx - 78},{top + 150} C{cx - 60},{top + 178} {cx - 30},{top + 184} {cx - 12},{top + 176}" fill="none" stroke="#0d0b0f" stroke-width="4" opacity=".3" stroke-linecap="round"/>
    <path d="M{cx + 78},{top + 150} C{cx + 60},{top + 178} {cx + 30},{top + 184} {cx + 12},{top + 176}" fill="none" stroke="#0d0b0f" stroke-width="4" opacity=".3" stroke-linecap="round"/>

    <path d="M{cx - 70},{wy - 30} C{cx - 66},{wy} {cx - 64},{wy + 20} {cx - 68},{hemy - 30}" fill="none" stroke="#4b4553" stroke-width="3" opacity=".45" stroke-linecap="round"/>
    <path d="M{cx + 36},{top + 200} C{cx + 50},{top + 220} {cx + 56},{top + 240} {cx + 54},{top + 262}" fill="none" stroke="#4b4553" stroke-width="3" opacity=".4" stroke-linecap="round"/>
  </g>"""


DEFS = f"""<defs>{F.FACE_DEFS}
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff1f6"/><stop offset="1" stop-color="#ffd2e3"/></linearGradient>
    <linearGradient id="limb" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{SKIN_SH}"/><stop offset=".5" stop-color="{SKIN}"/><stop offset="1" stop-color="{SKIN_HI}"/></linearGradient>
    <radialGradient id="chest" cx=".5" cy=".2" r=".9"><stop offset="0" stop-color="{SKIN_HI}"/><stop offset="1" stop-color="{SKIN}"/></radialGradient>
    <linearGradient id="tee" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#121014"/><stop offset=".48" stop-color="#433c4a"/><stop offset="1" stop-color="#121014"/></linearGradient>
    <linearGradient id="jeans" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{JEANS_SH}"/><stop offset=".38" stop-color="{JEANS_HI}"/><stop offset=".7" stop-color="{JEANS}"/><stop offset="1" stop-color="{JEANS_SH}"/></linearGradient>
    <linearGradient id="shoe" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#e1e2ea"/></linearGradient>
    <filter id="soft" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="16"/></filter>
  </defs>"""


def svg(pose=None, background=True):
    p = dict(REST)
    p.update(pose or {})
    hx, hy = p["head"]
    back, front = F.head_group(hx, hy, 0.72, p["head_tilt"], mouth=p["mouth"], blink=p["blink"], brow=p["brow"], look=p["look"])
    nx, ny = p["neck"]
    neck = (f'<path d="M{nx - 26},{ny - 70} C{nx - 24},{ny - 30} {nx - 30},{ny - 6} {nx - 40},{ny + 14} L{nx + 40},{ny + 14} '
            f'C{nx + 30},{ny - 6} {nx + 24},{ny - 30} {nx + 26},{ny - 70} Z" fill="url(#limb)" {OUT}/>'
            f'<path d="M{nx - 26},{ny - 62} C{nx - 8},{ny - 40} {nx + 8},{ny - 40} {nx + 26},{ny - 62} L{nx + 26},{ny - 46} '
            f'C{nx + 8},{ny - 24} {nx - 8},{ny - 24} {nx - 26},{ny - 46} Z" fill="#b57a58" opacity=".45"/>')
    bg = """<rect width="1080" height="1920" fill="url(#bg)"/>
      <circle cx="880" cy="360" r="210" fill="#ffc6dc" opacity=".5"/><circle cx="170" cy="1330" r="240" fill="#ffe4f0" opacity=".85"/>
      <ellipse cx="540" cy="1800" rx="220" ry="22" fill="#d88aa9" opacity=".35" filter="url(#soft)"/>""" if background else ""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920" viewBox="0 0 1080 1920">{DEFS}{bg}
      {back}{neck}{body(p)}{arm(p, 'r')}{arm(p, 'l')}{front}</svg>"""


def render(pose=None, path=None, scale=1.0):
    return cairosvg.svg2png(bytestring=svg(pose).encode(), write_to=path, scale=scale)


POSES = {
    "rest": {},
    "wave": dict(el_l=(790, 560), wr_l=(770, 380), head_tilt=-4, mouth="ah", brow=6),
    "hand on hip": dict(el_l=(770, 820), wr_l=(648, 930), el_r=(330, 780), wr_r=(318, 620), head_tilt=5, mouth="ee", look=(0.6, 0)),
    "pointing up": dict(el_r=(350, 470), wr_r=(360, 300), head_tilt=-3, mouth="slight", brow=5, look=(-0.5, -0.8),
                        kn_r=(470, 1380), an_r=(458, 1726)),
}

if __name__ == "__main__":
    from io import BytesIO
    from PIL import Image
    out = sys.argv[1] if len(sys.argv) > 1 else "poses.png"
    tiles = [Image.open(BytesIO(render(p, scale=0.5))) for p in POSES.values()]
    sheet = Image.new("RGB", (540 * len(tiles), 960), "white")
    for i, t in enumerate(tiles):
        sheet.paste(t, (540 * i, 0))
    sheet.save(out)
    render({}, out.replace(".png", "_full.png"))
    print("saved", out)
