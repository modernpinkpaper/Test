"""The 'skinny girl' character as a movable rig, drawn by code (SVG).

Arms and legs are "rubber hose" limbs: smooth tapered shapes drawn fresh every frame through
shoulder -> elbow -> wrist (hip -> knee -> ankle), so they bend without visible joints. Poses can come
from hand-made gestures or from motion data (MediaPipe tracking, Mixamo, CMU) mapped to these joints.

    python demo_videos/her_rig.py poses.png      # draws a sheet of example poses
"""
import math
import sys

import cairosvg
import numpy as np

SKIN, SKIN_SH, SKIN_HI, LINE = "#ecb892", "#d39a70", "#f7d4b4", "#5a3423"
HAIR, HAIR_HI, HAIR_DK = "#5b3421", "#9a6441", "#361c10"
TEE, TEE_HI = "#1d1a1f", "#403a46"
JEANS, JEANS_SH, JEANS_HI, STITCH = "#3f6aa5", "#2d4f84", "#6b95c9", "#d9a35c"
INK = "#231510"
OUT = f'stroke="{LINE}" stroke-width="3" stroke-linejoin="round"'

# rest pose (1080 x 1920 canvas)
REST = dict(
    neck=(540, 610), head_tilt=0.0,
    sh_r=(422, 668), el_r=(392, 870), wr_r=(404, 1066),
    sh_l=(658, 668), el_l=(688, 870), wr_l=(676, 1066),
    hip_r=(482, 1040), kn_r=(488, 1390), an_r=(496, 1735),
    hip_l=(598, 1040), kn_l=(592, 1390), an_l=(584, 1735),
    mouth="smile", blink=0.0, brow=0.0, look=(0.0, 0.0),
)


# ------------------------------------------------------------------ geometry helpers
def catmull(p0, p1, p2, n=24):
    """Smooth curve through three points."""
    pts = [np.array(p, float) for p in (p0, p0, p1, p2, p2)]
    out = []
    for i in range(1, 3):
        a, b, c, d = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        for t in np.linspace(0, 1, n, endpoint=(i == 2)):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * b) + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t2 + (-a + 3 * b - 3 * c + d) * t3))
    return np.array(out)


def tube(curve, w0, w1, bulge=0.0):
    """Tapered shape along a curve: width w0 at the start, w1 at the end (+ a soft bulge in the middle)."""
    n = len(curve)
    left, right = [], []
    for i in range(n):
        a = curve[max(i - 1, 0)]
        b = curve[min(i + 1, n - 1)]
        d = b - a
        d = d / (np.linalg.norm(d) + 1e-9)
        nrm = np.array([-d[1], d[0]])
        t = i / (n - 1)
        w = (w0 + (w1 - w0) * t + bulge * math.sin(math.pi * t)) / 2
        left.append(curve[i] + nrm * w)
        right.append(curve[i] - nrm * w)
    pts = left + right[::-1]
    return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + " Z"


def sub(curve, t0, t1):
    n = len(curve) - 1
    return curve[int(t0 * n):int(t1 * n) + 1]


def angle(a, b):
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))


# ------------------------------------------------------------------ parts
def hand(wr, el, side):
    """A soft hand at the wrist, pointing along the forearm."""
    ang = angle(el, wr) - 90
    s = 1 if side == "r" else -1
    return f"""<g transform="translate({wr[0]:.1f},{wr[1]:.1f}) rotate({ang:.1f}) scale(1.35)">
      <path d="M-14,-4 C-20,20 -16,46 0,54 C16,52 20,26 15,-4 Z" fill="url(#skin)" {OUT}/>
      <path d="M{-13 * s},6 C{-26 * s},16 {-28 * s},30 {-20 * s},34 C{-14 * s},30 {-12 * s},22 {-10 * s},16" fill="url(#skin)" {OUT}/>
      <path d="M-5,40 L-6,52 M3,40 L3,53 M10,38 L11,48" stroke="{SKIN_SH}" stroke-width="2" stroke-linecap="round"/>
    </g>"""


def arm(p, side):
    sh, el, wr = p[f"sh_{side}"], p[f"el_{side}"], p[f"wr_{side}"]
    c = catmull(sh, el, wr)
    skin = tube(c, 46, 28, bulge=6)
    nx, ny = p["neck"]
    d = np.array(sh, float) - np.array([nx, ny + 40], float)
    inner = np.array(sh, float) - d / (np.linalg.norm(d) + 1e-9) * 34
    sleeve = tube(sub(catmull(inner, sh, el), 0, 0.72), 78, 60)   # starts inside the shoulder, flows out of the shirt
    return f"""<g id="arm_{side}"><path d="{skin}" fill="url(#limb)" {OUT}/>
      <path d="{sleeve}" fill="url(#tee)" {OUT}/>{hand(wr, el, side)}</g>"""


def shoe(an, kn, side):
    s = 1 if side == "l" else -1
    ang = (angle(kn, an) - 90) * 0.3
    return f"""<g transform="translate({an[0]:.1f},{an[1]:.1f}) rotate({ang:.1f})">
      <path d="M{-30 * s},-8 C{-36 * s},30 {-30 * s},58 {-6 * s},64 L{58 * s},64 C{72 * s},56 {68 * s},36 {40 * s},20 C{28 * s},12 {20 * s},-2 {18 * s},-8 Z"
            fill="url(#shoe)" {OUT}/>
      <path d="M{-34 * s},50 C{-20 * s},62 {40 * s},64 {70 * s},54 L{66 * s},68 L{-10 * s},70 C{-26 * s},68 {-34 * s},60 {-34 * s},50 Z" fill="#d8d9e2" {OUT}/>
      <path d="M{-12 * s},10 L{14 * s},6 M{-12 * s},22 L{18 * s},18 M{-10 * s},34 L{22 * s},30" stroke="#c3c5d1" stroke-width="3" stroke-linecap="round"/>
    </g>"""


def leg(p, side):
    hip, kn, an = p[f"hip_{side}"], p[f"kn_{side}"], p[f"an_{side}"]
    c = catmull(hip, kn, an)
    jeans = tube(c, 128, 46, bulge=14)
    x = np.array(kn)
    return f"""<g id="leg_{side}">
      <path d="M{an[0] - 16:.1f},{an[1] - 16:.1f} L{an[0] + 16:.1f},{an[1] - 16:.1f} L{an[0] + 14:.1f},{an[1] + 8:.1f} L{an[0] - 14:.1f},{an[1] + 8:.1f} Z" fill="{SKIN_SH}"/>
      {shoe(an, kn, side)}
      <path d="{jeans}" fill="url(#jeans)" {OUT}/>
      <path d="M{x[0] - 14:.1f},{x[1] - 6:.1f} C{x[0] - 4:.1f},{x[1] + 4:.1f} {x[0] + 6:.1f},{x[1] + 4:.1f} {x[0] + 14:.1f},{x[1] - 6:.1f}"
            fill="none" stroke="{JEANS_SH}" stroke-width="3" stroke-linecap="round" opacity=".8"/>
    </g>"""


def eye(cx, cy, flip, blink, look):
    f = lambda x: cx + (x - 0) * flip
    lx, ly = look
    if blink > 0.7:
        return f"""<path d="M{f(34)},{cy + 4} C{f(18)},{cy + 18} {f(-18)},{cy + 18} {f(-34)},{cy + 2} L{f(-48)},{cy - 8}"
                   fill="none" stroke="{INK}" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round"/>"""
    lid = blink * 30
    lashes = "".join(f'<path d="M{f(x)},{cy + y} L{f(x - dx)},{cy + y - 12}" stroke="{INK}" stroke-width="2.8" stroke-linecap="round"/>'
                     for x, y, dx in ((-30, -12, 8), (-20, -20, 6), (-8, -24, 3), (5, -24, 0), (18, -20, -2)))
    return f"""
      <path d="M{f(-36)},{cy - 2} C{f(-32)},{cy - 24} {f(26)},{cy - 30} {f(36)},{cy - 4} C{f(28)},{cy + 22} {f(-24)},{cy + 26} {f(-36)},{cy - 2} Z" fill="#ffffff"/>
      <circle cx="{f(0) + lx * 8 * flip:.1f}" cy="{cy + 1 + ly * 5:.1f}" r="21" fill="url(#iris)"/>
      <circle cx="{f(0) + lx * 8 * flip:.1f}" cy="{cy + 2 + ly * 5:.1f}" r="10" fill="{INK}"/>
      <circle cx="{f(-7) + lx * 8 * flip:.1f}" cy="{cy - 7 + ly * 5:.1f}" r="6.5" fill="#fff"/>
      <circle cx="{f(8) + lx * 8 * flip:.1f}" cy="{cy + 10 + ly * 5:.1f}" r="2.8" fill="#fff" opacity=".85"/>
      <path d="M{f(-38)},{cy - 30} C{f(-20)},{cy - 30 + lid} {f(20)},{cy - 34 + lid} {f(38)},{cy - 30} L{f(38)},{cy - 4 + lid * 0.6} C{f(20)},{cy - 28 + lid} {f(-20)},{cy - 26 + lid} {f(-38)},{cy - 2 + lid * 0.4} Z" fill="url(#skin)" opacity="{min(1, blink * 3):.2f}"/>
      <path d="M{f(40)},{cy - 1 + lid * 0.6} C{f(26)},{cy - 32 + lid} {f(-24)},{cy - 30 + lid} {f(-38)},{cy - 2 + lid * 0.4} L{f(-54)},{cy - 16 + lid * 0.3}"
            fill="none" stroke="{INK}" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M{f(-30)},{cy + 14} C{f(-10)},{cy + 26} {f(18)},{cy + 24} {f(32)},{cy + 8}" fill="none" stroke="{LINE}" stroke-width="2" opacity=".6"/>
      {lashes}"""


MOUTHS = {
    "smile": """<path d="M-40,2 C-24,-10 -8,-6 0,-3 C8,-6 24,-10 40,2 C22,10 -22,10 -40,2 Z" fill="#c95f6c"/>
               <path d="M-38,3 C-24,28 24,28 38,3 C20,12 -20,12 -38,3 Z" fill="#e3868f"/>
               <path d="M-44,1 C-22,10 22,10 44,1" fill="none" stroke="#8e3a47" stroke-width="3" stroke-linecap="round"/>
               <path d="M-14,16 C-6,19 6,19 14,16" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round" opacity=".55"/>""",
    "slight": """<path d="M-36,0 C-22,-10 -8,-6 0,-3 C8,-6 22,-10 36,0 C20,24 -20,24 -36,0 Z" fill="#c95f6c"/>
                <path d="M-26,4 C-12,8 12,8 26,4 C16,14 -16,14 -26,4 Z" fill="#6c2330"/>
                <path d="M-24,4 C-10,7 10,7 24,4 L22,8 C8,10 -8,10 -22,8 Z" fill="#fff"/>""",
    "ah": """<path d="M-34,-4 C-20,-12 -8,-8 0,-6 C8,-8 20,-12 34,-4 C36,34 18,50 0,50 C-18,50 -36,34 -34,-4 Z" fill="#c95f6c"/>
             <path d="M-27,2 C-12,7 12,7 27,2 C28,28 14,40 0,40 C-14,40 -28,28 -27,2 Z" fill="#6c2330"/>
             <path d="M-26,2 C-12,8 12,8 26,2 L24,10 C10,14 -10,14 -24,10 Z" fill="#fff"/>
             <ellipse cx="0" cy="33" rx="15" ry="7" fill="#e07a88"/>""",
    "oh": """<ellipse cx="0" cy="12" rx="22" ry="26" fill="#c95f6c"/><ellipse cx="0" cy="13" rx="13" ry="17" fill="#6c2330"/>""",
    "oo": """<ellipse cx="0" cy="8" rx="16" ry="16" fill="#c95f6c"/><ellipse cx="0" cy="9" rx="7" ry="8" fill="#6c2330"/>""",
    "ee": """<path d="M-44,0 C-22,-8 22,-8 44,0 C26,20 -26,20 -44,0 Z" fill="#c95f6c"/>
             <path d="M-34,2 C-12,6 12,6 34,2 C22,14 -22,14 -34,2 Z" fill="#fff"/>""",
}


def head(p):
    nx, ny = p["neck"]
    tilt = p["head_tilt"]
    cx, cy = nx, ny - 226          # head centre
    ey = cy - 5
    brow = -p["brow"]
    return f"""
  <g id="head" transform="rotate({tilt:.1f} {nx} {ny})">
    <path d="M{cx - 28},{cy + 150} C{cx - 26},{cy + 190} {cx - 32},{cy + 210} {cx - 42},{cy + 232} L{cx + 42},{cy + 232} C{cx + 32},{cy + 210} {cx + 26},{cy + 190} {cx + 28},{cy + 150} Z" fill="{SKIN_SH}" {OUT}/>
    <path d="M{cx - 26},{cy + 160} C{cx - 8},{cy + 186} {cx + 8},{cy + 186} {cx + 26},{cy + 160} L{cx + 26},{cy + 176} C{cx + 8},{cy + 200} {cx - 8},{cy + 200} {cx - 26},{cy + 176} Z" fill="#b97a55" opacity=".45"/>
    <path d="M{cx - 118},{cy - 20} C{cx - 120},{cy - 120} {cx - 62},{cy - 168} {cx},{cy - 168} C{cx + 62},{cy - 168} {cx + 120},{cy - 120} {cx + 118},{cy - 20}
             C{cx + 116},{cy + 70} {cx + 70},{cy + 150} {cx},{cy + 168} C{cx - 70},{cy + 150} {cx - 116},{cy + 70} {cx - 118},{cy - 20} Z" fill="url(#skin)" {OUT}/>
    <path d="M{cx + 90},{cy + 70} C{cx + 70},{cy + 120} {cx + 40},{cy + 150} {cx},{cy + 168} C{cx + 60},{cy + 150} {cx + 104},{cy + 100} {cx + 112},{cy + 30} Z" fill="{SKIN_SH}" opacity=".4"/>
    <ellipse cx="{cx - 70}" cy="{ey + 66}" rx="34" ry="18" fill="#ff8f9c" opacity=".3"/>
    <ellipse cx="{cx + 70}" cy="{ey + 66}" rx="34" ry="18" fill="#ff8f9c" opacity=".3"/>
    <g transform="translate(0 {brow})">
      <path d="M{cx - 100},{ey - 50} C{cx - 84},{ey - 80} {cx - 40},{ey - 88} {cx - 16},{ey - 68} C{cx - 40},{ey - 72} {cx - 74},{ey - 64} {cx - 96},{ey - 40} Z" fill="{HAIR_DK}"/>
      <path d="M{cx + 100},{ey - 50} C{cx + 84},{ey - 80} {cx + 40},{ey - 88} {cx + 16},{ey - 68} C{cx + 40},{ey - 72} {cx + 74},{ey - 64} {cx + 96},{ey - 40} Z" fill="{HAIR_DK}"/>
    </g>
    {eye(cx - 55, ey, 1, p["blink"], p["look"])}{eye(cx + 55, ey, -1, p["blink"], p["look"])}
    <path d="M{cx - 4},{ey + 50} C{cx - 10},{ey + 76} {cx - 6},{ey + 88} {cx + 10},{ey + 90}" fill="none" stroke="{LINE}" stroke-width="3.5" stroke-linecap="round" opacity=".8"/>
    <g transform="translate({cx} {ey + 128})">{MOUTHS[p["mouth"]]}</g>
  </g>"""


def hair_back(p):
    nx, ny = p["neck"]
    cx, cy = nx, ny - 226
    return f"""
  <g id="hair_back" transform="rotate({p['head_tilt'] * 0.6:.1f} {nx} {ny})">
    <path d="M{cx},{cy - 190} C{cx - 120},{cy - 196} {cx - 176},{cy - 110} {cx - 178},{cy} C{cx - 182},{cy + 90} {cx - 214},{cy + 160} {cx - 220},{cy + 250}
             C{cx - 228},{cy + 340} {cx - 250},{cy + 400} {cx - 236},{cy + 480} C{cx - 226},{cy + 540} {cx - 246},{cy + 600} {cx - 206},{cy + 650}
             C{cx - 176},{cy + 690} {cx - 130},{cy + 700} {cx - 104},{cy + 680} C{cx - 120},{cy + 640} {cx - 128},{cy + 590} {cx - 110},{cy + 540}
             L{cx - 70},{cy + 250} L{cx + 90},{cy + 260} C{cx + 130},{cy + 250} {cx + 160},{cy + 220} {cx + 170},{cy + 170}
             C{cx + 180},{cy + 110} {cx + 160},{cy + 70} {cx + 172},{cy + 10} C{cx + 186},{cy - 60} {cx + 176},{cy - 130} {cx + 140},{cy - 162}
             C{cx + 104},{cy - 190} {cx + 56},{cy - 194} {cx},{cy - 190} Z" fill="url(#hairdk)" {OUT}/>
  </g>"""


def hair_front(p):
    nx, ny = p["neck"]
    cx, cy = nx, ny - 226
    t = p["head_tilt"]
    return f"""
  <g id="hair_front" transform="rotate({t:.1f} {nx} {ny})">
    <path d="M{cx + 50},{cy - 176} C{cx - 30},{cy - 178} {cx - 110},{cy - 140} {cx - 130},{cy - 60} C{cx - 142},{cy - 10} {cx - 138},{cy + 50} {cx - 124},{cy + 100}
             C{cx - 150},{cy + 170} {cx - 168},{cy + 250} {cx - 158},{cy + 330} C{cx - 148},{cy + 400} {cx - 178},{cy + 470} {cx - 166},{cy + 540}
             C{cx - 156},{cy + 610} {cx - 126},{cy + 660} {cx - 80},{cy + 690} C{cx - 104},{cy + 640} {cx - 112},{cy + 590} {cx - 100},{cy + 530}
             C{cx - 88},{cy + 470} {cx - 108},{cy + 400} {cx - 100},{cy + 330} C{cx - 92},{cy + 260} {cx - 96},{cy + 180} {cx - 106},{cy + 110}
             C{cx - 116},{cy + 50} {cx - 116},{cy - 10} {cx - 104},{cy - 50} C{cx - 84},{cy - 110} {cx - 20},{cy - 140} {cx + 60},{cy - 148} Z" fill="url(#hair)" {OUT}/>
    <path d="M{cx + 50},{cy - 176} C{cx + 110},{cy - 166} {cx + 146},{cy - 110} {cx + 150},{cy - 30} C{cx + 154},{cy + 30} {cx + 146},{cy + 80} {cx + 132},{cy + 120}
             C{cx + 128},{cy + 50} {cx + 118},{cy - 40} {cx + 60},{cy - 148} Z" fill="url(#hair)" {OUT}/>
    <g fill="none" stroke-linecap="round">
      <path d="M{cx - 90},{cy - 118} C{cx - 40},{cy - 150} {cx + 10},{cy - 160} {cx + 46},{cy - 162}" stroke="{HAIR_HI}" stroke-width="10" opacity=".55"/>
      <path d="M{cx - 140},{cy + 200} C{cx - 150},{cy + 280} {cx - 136},{cy + 340} {cx - 146},{cy + 420}" stroke="{HAIR_HI}" stroke-width="7" opacity=".5"/>
      <path d="M{cx - 124},{cy + 430} C{cx - 132},{cy + 500} {cx - 120},{cy + 560} {cx - 104},{cy + 620}" stroke="{HAIR_HI}" stroke-width="5" opacity=".45"/>
      <path d="M{cx + 120},{cy - 110} C{cx + 134},{cy - 60} {cx + 138},{cy - 10} {cx + 136},{cy + 40}" stroke="{HAIR_HI}" stroke-width="5" opacity=".5"/>
      <path d="M{cx - 118},{cy + 120} C{cx - 130},{cy + 200} {cx - 122},{cy + 300} {cx - 126},{cy + 380}" stroke="{HAIR_DK}" stroke-width="4" opacity=".6"/>
      <path d="M{cx - 70},{cy - 128} C{cx - 100},{cy - 90} {cx - 116},{cy - 40} {cx - 118},{cy + 10}" stroke="{HAIR_DK}" stroke-width="3" opacity=".5"/>
    </g>
  </g>"""


def torso(p):
    sr, sl, hr, hl = p["sh_r"], p["sh_l"], p["hip_r"], p["hip_l"]
    nx, ny = p["neck"]
    wy = (sr[1] + hr[1]) / 2 + 60                 # waist height
    wx = (sr[0] + sl[0]) / 2
    tee = (f"M{sr[0] + 10},{sr[1] - 14} C{nx - 50},{ny - 6} {nx - 44},{ny - 10} {nx - 40},{ny - 12} C{nx - 20},{ny + 50} {nx + 20},{ny + 50} {nx + 40},{ny - 12} "
           f"C{nx + 44},{ny - 10} {nx + 50},{ny - 6} {sl[0] - 10},{sl[1] - 14} C{sl[0] + 30},{sl[1] + 20} {sl[0] + 26},{sl[1] + 150} {wx + 78},{wy} "
           f"C{wx + 74},{wy + 40} {hl[0] + 10},{hl[1] - 60} {hl[0] + 12},{hl[1] - 30} L{hr[0] - 12},{hr[1] - 30} "
           f"C{hr[0] - 10},{hr[1] - 60} {wx - 74},{wy + 40} {wx - 78},{wy} C{sr[0] - 26},{sr[1] + 150} {sr[0] - 30},{sr[1] + 20} {sr[0] + 10},{sr[1] - 14} Z")
    hips = (f"M{hr[0] - 20},{hr[1] - 40} L{hl[0] + 20},{hl[1] - 40} C{hl[0] + 52},{hl[1] - 10} {hl[0] + 72},{hl[1] + 50} {hl[0] + 62},{hl[1] + 120} "
            f"C{(hr[0] + hl[0]) / 2 + 30},{hl[1] + 150} {(hr[0] + hl[0]) / 2 - 30},{hr[1] + 150} {hr[0] - 62},{hr[1] + 120} "
            f"C{hr[0] - 72},{hr[1] + 50} {hr[0] - 52},{hr[1] - 10} {hr[0] - 20},{hr[1] - 40} Z")
    mx = (hr[0] + hl[0]) / 2
    return f"""
  <g id="hips"><path d="{hips}" fill="url(#jeans)" {OUT}/></g>
  <!--LEGS-->
  <g id="torso">
    <path d="M{hr[0] - 18},{hr[1] - 38} L{hl[0] + 18},{hl[1] - 38} L{hl[0] + 24},{hl[1] - 8} L{hr[0] - 24},{hr[1] - 8} Z" fill="{JEANS_SH}" {OUT}/>
    <path d="M{hr[0] - 22},{hr[1] - 14} L{hl[0] + 22},{hl[1] - 14}" stroke="{STITCH}" stroke-width="2" stroke-dasharray="6 5"/>
    <circle cx="{mx}" cy="{hr[1] - 24}" r="8" fill="#cfd2dc" stroke="#8b8f9c" stroke-width="2"/>
    <path d="M{mx},{hr[1] - 8} L{mx},{hr[1] + 70} C{mx},{hr[1] + 82} {mx + 10},{hr[1] + 88} {mx + 20},{hr[1] + 80}" fill="none" stroke="{STITCH}" stroke-width="2" stroke-dasharray="6 5"/>
    <path d="M{hr[0] - 32},{hr[1] + 2} C{hr[0] - 10},{hr[1] + 36} {hr[0] + 20},{hr[1] + 44} {hr[0] + 36},{hr[1] + 38}" fill="none" stroke="{STITCH}" stroke-width="2" stroke-dasharray="6 5"/>
    <path d="M{hl[0] + 32},{hl[1] + 2} C{hl[0] + 10},{hl[1] + 36} {hl[0] - 20},{hl[1] + 44} {hl[0] - 36},{hl[1] + 38}" fill="none" stroke="{STITCH}" stroke-width="2" stroke-dasharray="6 5"/>
    <path d="{tee}" fill="url(#tee)" {OUT}/>
    <path d="M{nx - 40},{ny - 12} C{nx - 20},{ny + 50} {nx + 20},{ny + 50} {nx + 40},{ny - 12} C{nx + 20},{ny - 2} {nx - 20},{ny - 2} {nx - 40},{ny - 12} Z" fill="url(#skin)"/>
    <path d="M{nx - 40},{ny - 12} C{nx - 20},{ny + 50} {nx + 20},{ny + 50} {nx + 40},{ny - 12}" fill="none" stroke="#0d0b0e" stroke-width="6"/>
    <path d="M{nx - 34},{ny + 14} C{nx - 20},{ny + 20} {nx - 10},{ny + 22} {nx - 4},{ny + 20}" fill="none" stroke="{LINE}" stroke-width="2" opacity=".6"/>
    <path d="M{nx + 34},{ny + 14} C{nx + 20},{ny + 20} {nx + 10},{ny + 22} {nx + 4},{ny + 20}" fill="none" stroke="{LINE}" stroke-width="2" opacity=".6"/>
    <path d="M{wx - 70},{sr[1] + 120} C{wx - 40},{sr[1] + 170} {wx + 40},{sr[1] + 170} {wx + 70},{sr[1] + 120}" fill="none" stroke="#4a4452" stroke-width="5" opacity=".55" stroke-linecap="round"/>
    <path d="M{wx - 62},{wy - 20} C{wx - 58},{wy + 20} {wx - 50},{wy + 40} {wx - 54},{wy + 70}" fill="none" stroke="#4a4452" stroke-width="4" opacity=".5" stroke-linecap="round"/>
  </g>"""


DEFS = f"""<defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff0f6"/><stop offset="1" stop-color="#ffd3e4"/></linearGradient>
    <radialGradient id="skin" cx=".45" cy=".38" r=".75"><stop offset="0" stop-color="{SKIN_HI}"/><stop offset=".6" stop-color="{SKIN}"/><stop offset="1" stop-color="{SKIN_SH}"/></radialGradient>
    <linearGradient id="limb" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{SKIN_SH}"/><stop offset=".5" stop-color="{SKIN}"/><stop offset="1" stop-color="{SKIN_HI}"/></linearGradient>
    <radialGradient id="iris" cx=".4" cy=".32" r=".75"><stop offset="0" stop-color="#b07a4c"/><stop offset=".55" stop-color="#6a3f24"/><stop offset="1" stop-color="#2e170c"/></radialGradient>
    <linearGradient id="hair" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{HAIR_HI}"/><stop offset=".45" stop-color="{HAIR}"/><stop offset="1" stop-color="{HAIR_DK}"/></linearGradient>
    <linearGradient id="hairdk" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{HAIR}"/><stop offset="1" stop-color="{HAIR_DK}"/></linearGradient>
    <linearGradient id="tee" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#121014"/><stop offset=".5" stop-color="{TEE_HI}"/><stop offset="1" stop-color="#121014"/></linearGradient>
    <linearGradient id="jeans" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{JEANS_SH}"/><stop offset=".35" stop-color="{JEANS_HI}"/><stop offset=".7" stop-color="{JEANS}"/><stop offset="1" stop-color="{JEANS_SH}"/></linearGradient>
    <linearGradient id="shoe" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#e2e3ea"/></linearGradient>
    <filter id="soft" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="16"/></filter>
  </defs>"""


def svg(pose=None, background=True):
    p = dict(REST)
    p.update(pose or {})
    bg = """<rect width="1080" height="1920" fill="url(#bg)"/>
      <circle cx="870" cy="380" r="210" fill="#ffc5dc" opacity=".5"/><circle cx="170" cy="1340" r="240" fill="#ffe3ef" opacity=".85"/>
      <ellipse cx="540" cy="1810" rx="230" ry="24" fill="#d88aa9" opacity=".35" filter="url(#soft)"/>""" if background else ""
    # draw the arm that is behind the body first when it crosses over
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920" viewBox="0 0 1080 1920">{DEFS}{bg}
      {hair_back(p)}{torso(p).replace("<!--LEGS-->", leg(p, 'r') + leg(p, 'l'))}{head(p)}{hair_front(p)}{arm(p, 'r')}{arm(p, 'l')}</svg>"""


def render(pose=None, path=None, scale=1.0):
    return cairosvg.svg2png(bytestring=svg(pose).encode(), write_to=path, scale=scale)


POSES = {
    "rest": {},
    "wave": dict(el_l=(760, 560), wr_l=(740, 380), head_tilt=-4, mouth="ah", brow=6),
    "hand on hip": dict(el_l=(740, 840), wr_l=(640, 990), el_r=(360, 820), wr_r=(330, 640), head_tilt=5, mouth="ee", look=(0.6, 0)),
    "hands up": dict(el_r=(330, 520), wr_r=(360, 330), el_l=(750, 520), wr_l=(720, 330), mouth="oh", brow=8, head_tilt=-2,
                     kn_r=(470, 1380), an_r=(456, 1730), kn_l=(610, 1380), an_l=(624, 1730)),
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
