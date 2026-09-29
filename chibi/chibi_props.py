"""Things she can hold: drawn in a sheet hand's own frame (wrist at (0, 0), fingers up = -y, sheet pixels), so they
move and turn with her hand. Each returns (behind, in_front) SVG for chibi_body.arm(..., prop=...).

The C grip's gap (between fingers and thumb) is centred near (105, -150), opening towards +x.
"""
import itertools

from chibi_hands import COL

OUT = COL["outline"]
LW = 13                                           # outline width, like the hands' outlines
_ids = itertools.count()


def mug(steam=0.0):
    """Pink coffee mug held in the C grip (the fingers wrap its side)."""
    s = (f'<rect x="60" y="-235" width="190" height="175" rx="26" fill="#f4a6c0" stroke="{OUT}" stroke-width="{LW}"/>'
         f'<rect x="60" y="-235" width="190" height="36" rx="18" fill="#6b3f2a" stroke="{OUT}" stroke-width="{LW}"/>'
         f'<path d="M 120 -140 q 35 -30 70 0 q -35 30 -70 0 z" fill="#ffffff" opacity="0.85"/>')
    if steam > 0:
        for i, x in enumerate((110, 160, 205)):
            y = -270 - 30 * ((steam + i * .33) % 1)
            s += (f'<path d="M {x} {y + 40} q -18 -25 0 -50 q 18 -25 0 -50" fill="none" stroke="#ffffff" '
                  f'stroke-width="12" stroke-linecap="round" opacity="{0.8 * (1 - (steam + i * .33) % 1):.2f}"/>')
    return s, ""


def donut(bites=0):
    """Pink-frosted donut in the C grip; bites = 0..3 chunks taken out of its top edge."""
    i = next(_ids)
    cx, cy, r = 205, -160, 115
    holes = "".join(f'<circle cx="{cx + dx}" cy="{cy + dy}" r="46" fill="black"/>'
                    for dx, dy in ((-40, -105), (30, -112), (95, -75))[:bites])
    m = (f'<mask id="bite{i}" maskUnits="userSpaceOnUse" x="0" y="-400" width="500" height="500">'
         f'<rect x="0" y="-400" width="500" height="500" fill="white"/>{holes}</mask>')
    sprinkles = "".join(f'<rect x="{cx + dx}" y="{cy + dy}" width="26" height="9" rx="4" fill="{c}" '
                        f'transform="rotate({a} {cx + dx} {cy + dy})"/>'
                        for dx, dy, a, c in ((-60, -40, 30, "#ffffff"), (40, -70, -20, "#7ec8ff"), (60, 20, 60, "#fff27a"),
                                             (-30, 50, -40, "#7ec8ff"), (-75, 10, 80, "#fff27a"), (10, -85, 10, "#ffffff")))
    body = (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#e7b073" stroke="{OUT}" stroke-width="{LW}"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r - 22}" fill="#ff8fb8"/>{sprinkles}'
            f'<circle cx="{cx}" cy="{cy}" r="34" fill="#e7b073" stroke="{OUT}" stroke-width="{LW}"/>')
    return f'<defs>{m}</defs><g mask="url(#bite{i})">{body}</g>', ""


def phone(lit=True):
    """Phone in the C grip, long side along the hand's +x (turn the wrist to hold it to her cheek)."""
    screen = "#bfe6ff" if lit else "#2b2f38"
    return (f'<rect x="40" y="-215" width="330" height="150" rx="30" fill="#2b2f38" stroke="{OUT}" stroke-width="{LW}"/>'
            f'<rect x="72" y="-195" width="266" height="110" rx="16" fill="{screen}"/>', "")


def toothbrush(foam=False):
    s = (f'<rect x="30" y="-175" width="360" height="42" rx="20" fill="#7ec8ff" stroke="{OUT}" stroke-width="{LW}"/>'
         f'<rect x="300" y="-215" width="80" height="45" rx="10" fill="#ffffff" stroke="{OUT}" stroke-width="{LW}"/>')
    if foam:
        s += "".join(f'<circle cx="{x}" cy="-230" r="22" fill="#ffffff" stroke="#dfe8f0" stroke-width="4"/>'
                     for x in (310, 340, 370))
    return s, ""
