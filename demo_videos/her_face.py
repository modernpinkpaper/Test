"""Detailed face + hair for the brand character (SVG), drawn in local coordinates around the face centre.

Face: oval with cheekbones and a tapered jaw, contour shading, almond eyes lifted at the outer corner
(iris tucked under the upper lid, winged liner, crease, eyeshadow, lashes), arched tapered brows,
a small nose with nostrils, full lips with a cupid's bow and gloss. Hair: side part, layered clumps
with strand lines and tapered wavy ends.
"""

SKIN, SKIN_SH, SKIN_HI, LINE = "#edb994", "#d49a71", "#f8d6b8", "#6b3f2a"
HAIR, HAIR_HI, HAIR_DK = "#5b3421", "#a06a45", "#331a0f"
INK = "#1f120d"
LIP, LIP_DK, LIP_HI = "#c7646f", "#8e3a47", "#e89aa2"
SHADOW = "#b37755"

FACE_DEFS = f"""
    <radialGradient id="fskin" cx=".5" cy=".42" r=".62">
      <stop offset="0" stop-color="{SKIN_HI}"/><stop offset=".62" stop-color="{SKIN}"/><stop offset="1" stop-color="{SKIN_SH}"/></radialGradient>
    <radialGradient id="firis" cx=".42" cy=".3" r=".8">
      <stop offset="0" stop-color="#c08a58"/><stop offset=".45" stop-color="#7a4a2a"/><stop offset="1" stop-color="#2a150b"/></radialGradient>
    <linearGradient id="fshadow" x1="0" y1="1" x2="0" y2="0">
      <stop offset="0" stop-color="#a8664e" stop-opacity=".55"/><stop offset="1" stop-color="#a8664e" stop-opacity="0"/></linearGradient>
    <linearGradient id="flip" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{LIP}"/><stop offset="1" stop-color="#d9808a"/></linearGradient>
    <linearGradient id="fhair" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{HAIR_HI}"/><stop offset=".4" stop-color="{HAIR}"/><stop offset="1" stop-color="{HAIR_DK}"/></linearGradient>
    <linearGradient id="fhair2" x1="1" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#7d4d31"/><stop offset=".5" stop-color="{HAIR}"/><stop offset="1" stop-color="{HAIR_DK}"/></linearGradient>
    <linearGradient id="fhairback" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{HAIR_DK}"/><stop offset="1" stop-color="#28130a"/></linearGradient>  <radialGradient id="fblush"><stop offset="0" stop-color="#ff8d96" stop-opacity=".42"/><stop offset="1" stop-color="#ff8d96" stop-opacity="0"/></radialGradient>
"""

OUTLINE = f'stroke="{LINE}" stroke-width="2.4" stroke-linejoin="round"'


def _eye(side, blink=0.0, look=(0.0, 0.0)):
    """side=-1: eye on the left of the picture, +1: right. Eye centre at (57*side, -8)."""
    s = side
    X = lambda x: 57 * s + x * s          # x measured outward from the eye centre
    lx, ly = look[0] * 7, look[1] * 4
    if blink > 0.75:
        return f"""<path d="M{X(-34)},-4 C{X(-16)},10 {X(16)},10 {X(35)},-6 L{X(47)},-17" fill="none" stroke="{INK}" stroke-width="5.5"
                   stroke-linecap="round" stroke-linejoin="round"/>
                   <path d="M{X(10)},6 L{X(14)},15 M{X(20)},3 L{X(26)},11 M{X(28)},-1 L{X(35)},5" stroke="{INK}" stroke-width="2.2" stroke-linecap="round"/>"""
    white = f"M{X(-35)},-2 C{X(-28)},-26 {X(18)},-32 {X(36)},-12 C{X(30)},10 {X(-10)},18 {X(-35)},-2 Z"
    lid_drop = blink * 26
    cid = f"eyeclip{'L' if s < 0 else 'R'}"
    return f"""
      <clipPath id="{cid}"><path d="{white}"/></clipPath>
      <path d="M{X(-40)},-10 C{X(-28)},-40 {X(22)},-46 {X(44)},-18 C{X(24)},-32 {X(-20)},-30 {X(-40)},-10 Z" fill="#b8725e" opacity=".32"/>
      <path d="M{X(-34)},-24 C{X(-20)},-42 {X(20)},-46 {X(40)},-26" fill="none" stroke="{SHADOW}" stroke-width="2.2" opacity=".75"/>
      <path d="{white}" fill="#fbf7f4"/>
      <g clip-path="url(#{cid})">
        <path d="M{X(-40)},-40 L{X(44)},-40 L{X(44)},-8 C{X(20)},-24 {X(-20)},-22 {X(-40)},-6 Z" fill="#d9c7c0" opacity=".45"/>
        <circle cx="{X(2) + lx * s:.1f}" cy="{-7 + ly:.1f}" r="19.5" fill="url(#firis)"/>
        <circle cx="{X(2) + lx * s:.1f}" cy="{-7 + ly:.1f}" r="19.5" fill="none" stroke="#24110a" stroke-width="2"/>
        <circle cx="{X(2) + lx * s:.1f}" cy="{-6 + ly:.1f}" r="9" fill="{INK}"/>
        <circle cx="{X(-5) + lx * s:.1f}" cy="{-15 + ly:.1f}" r="5.5" fill="#fff"/>
        <circle cx="{X(9) + lx * s:.1f}" cy="{2 + ly:.1f}" r="2.4" fill="#fff" opacity=".8"/>
        <path d="M{X(-40)},-50 L{X(46)},-50 L{X(46)},{-50 + lid_drop * 2} L{X(-40)},{-50 + lid_drop * 2} Z" fill="url(#fskin)"/>
      </g>
      <path d="M{X(-36)},-2 C{X(-28)},{-27 + lid_drop} {X(18)},{-34 + lid_drop} {X(37)},{-13 + lid_drop * .4} L{X(50)},-24"
            fill="none" stroke="{INK}" stroke-width="6.5" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M{X(-30)},4 C{X(-10)},15 {X(18)},12 {X(34)},-8" fill="none" stroke="#6b3a28" stroke-width="2" opacity=".75"/>
      <g stroke="{INK}" stroke-width="2.4" stroke-linecap="round" fill="none">
        <path d="M{X(4)},{-31 + lid_drop} C{X(6)},{-38 + lid_drop} {X(8)},{-41 + lid_drop} {X(10)},{-44 + lid_drop}"/>
        <path d="M{X(14)},{-29 + lid_drop} C{X(18)},{-36 + lid_drop} {X(21)},{-39 + lid_drop} {X(24)},{-41 + lid_drop}"/>
        <path d="M{X(24)},{-24 + lid_drop} C{X(29)},{-30 + lid_drop} {X(33)},{-32 + lid_drop} {X(37)},{-33 + lid_drop}"/>
        <path d="M{X(31)},{-18 + lid_drop} C{X(37)},{-22 + lid_drop} {X(41)},{-23 + lid_drop} {X(45)},{-23 + lid_drop}"/>
        <path d="M{X(26)},4 L{X(29)},9" stroke-width="1.6" opacity=".7"/><path d="M{X(18)},8 L{X(20)},13" stroke-width="1.6" opacity=".7"/>
      </g>"""


def _brow(side, lift=0.0):
    s = side
    X = lambda x: x * s
    y = -62 - lift
    return f"""<path d="M{X(20)},{y + 4} C{X(28)},{y - 10} {X(56)},{y - 17} {X(77)},{y - 13} C{X(90)},{y - 9} {X(100)},{y} {X(105)},{y + 9}
                 C{X(94)},{y + 4} {X(82)},{y + 1} {X(70)},{y + 3} C{X(52)},{y + 5} {X(36)},{y + 10} {X(22)},{y + 18} Z" fill="{HAIR_DK}"/>
               <path d="M{X(30)},{y + 4} C{X(48)},{y - 4} {X(66)},{y - 6} {X(82)},{y - 4}" fill="none" stroke="#6b4030" stroke-width="1.4" opacity=".6"/>"""


MOUTHS = {
    "smile": f"""<path d="M-37,97 C-26,90 -13,85 -5,89 C-2,87 2,87 5,89 C13,85 26,90 37,97 C22,101 -22,101 -37,97 Z" fill="url(#flip)"/>
                 <path d="M-35,98 C-22,120 22,120 35,98 C18,104 -18,104 -35,98 Z" fill="#d9808a"/>
                 <path d="M-41,95 C-24,103 24,103 41,95" fill="none" stroke="{LIP_DK}" stroke-width="2.8" stroke-linecap="round"/>
                 <path d="M-41,95 C-44,93 -45,90 -44,87 M41,95 C44,93 45,90 44,87" fill="none" stroke="{LINE}" stroke-width="2" stroke-linecap="round" opacity=".7"/>
                 <path d="M-12,108 C-5,111 5,111 12,108" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round" opacity=".6"/>
                 <path d="M-6,88 C-4,86 4,86 6,88" fill="none" stroke="{LIP_HI}" stroke-width="2" opacity=".8"/>""",
    "slight": f"""<path d="M-34,95 C-24,88 -12,85 -5,88 C-2,86 2,86 5,88 C12,85 24,88 34,95 C20,122 -20,122 -34,95 Z" fill="url(#flip)"/>
                  <path d="M-25,98 C-10,102 10,102 25,98 C14,108 -14,108 -25,98 Z" fill="#5e1f2b"/>
                  <path d="M-23,98 C-10,101 10,101 23,98 L21,102 C8,104 -8,104 -21,102 Z" fill="#fff"/>
                  <path d="M-10,114 C-4,116 4,116 10,114" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" opacity=".5"/>""",
    "ah": f"""<path d="M-32,92 C-22,86 -10,83 -4,86 C-1,85 1,85 4,86 C10,83 22,86 32,92 C34,126 18,142 0,142 C-18,142 -34,126 -32,92 Z" fill="url(#flip)"/>
              <path d="M-25,97 C-10,101 10,101 25,97 C26,120 14,132 0,132 C-14,132 -26,120 -25,97 Z" fill="#5e1f2b"/>
              <path d="M-24,97 C-10,102 10,102 24,97 L22,105 C8,108 -8,108 -22,105 Z" fill="#fff"/>
              <ellipse cx="0" cy="125" rx="14" ry="6" fill="#dd7985"/>""",
    "oh": f"""<ellipse cx="0" cy="104" rx="20" ry="23" fill="url(#flip)"/><ellipse cx="0" cy="105" rx="11" ry="15" fill="#5e1f2b"/>
              <path d="M-7,120 C-3,122 3,122 7,120" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" opacity=".5"/>""",
    "oo": f"""<ellipse cx="0" cy="101" rx="15" ry="15" fill="url(#flip)"/><ellipse cx="0" cy="102" rx="6" ry="7" fill="#5e1f2b"/>""",
    "ee": f"""<path d="M-42,94 C-20,86 20,86 42,94 C24,114 -24,114 -42,94 Z" fill="url(#flip)"/>
              <path d="M-32,96 C-12,100 12,100 32,96 C20,106 -20,106 -32,96 Z" fill="#fff"/>
              <path d="M-32,96 C-12,100 12,100 32,96" fill="none" stroke="{LIP_DK}" stroke-width="2"/>""",
}


def face(mouth="smile", blink=0.0, brow=0.0, look=(0.0, 0.0)):
    """Face in local coordinates: face centre (0,0), head top y=-178, chin y=170."""
    return f"""
    <path d="M-116,-30 C-118,-132 -60,-180 0,-180 C60,-180 118,-132 116,-30 C114,34 98,84 66,124 C44,152 20,168 0,170
             C-20,168 -44,152 -66,124 C-98,84 -114,34 -116,-30 Z" fill="url(#fskin)" {OUTLINE}/>
    <path d="M-108,20 C-100,62 -84,96 -56,126 C-72,96 -82,62 -86,30 Z" fill="{SHADOW}" opacity=".28"/>
    <path d="M108,20 C100,62 84,96 56,126 C72,96 82,62 86,30 Z" fill="{SHADOW}" opacity=".35"/>
    <path d="M-30,152 C-12,166 12,166 30,152 C16,160 -16,160 -30,152 Z" fill="{SHADOW}" opacity=".25"/>
    <ellipse cx="-72" cy="48" rx="36" ry="20" fill="url(#fblush)"/>
    <ellipse cx="72" cy="48" rx="36" ry="20" fill="url(#fblush)"/>
    {_brow(-1, brow)}{_brow(1, brow)}
    {_eye(-1, blink, look)}{_eye(1, blink, look)}
    <path d="M-2,-2 C-4,18 -4,32 -6,42" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round" opacity=".28"/>
    <path d="M8,4 C10,22 12,34 14,42" fill="none" stroke="{SHADOW}" stroke-width="2.2" stroke-linecap="round" opacity=".55"/>
    <path d="M-16,50 C-18,58 -10,62 -4,60 C-1,63 1,63 4,60 C10,62 18,58 16,50" fill="none" stroke="{LINE}" stroke-width="2.4" stroke-linecap="round" opacity=".75"/>
    <path d="M-9,57 C-7,54 -4,55 -3,57 M9,57 C7,54 4,55 3,57" fill="none" stroke="#7a4430" stroke-width="2.4" stroke-linecap="round"/>
    <ellipse cx="0" cy="48" rx="8" ry="5" fill="#fff" opacity=".22"/>
    <path d="M-8,68 C-4,74 4,74 8,68" fill="none" stroke="{SHADOW}" stroke-width="1.6" opacity=".5"/>
    <g transform="translate(0 100) scale(1.15) translate(0 -100)">{MOUTHS[mouth]}</g>"""


def hair_back():
    """Behind the head and body: full, long on the picture's left, behind the shoulder on the right."""
    return f"""
    <path d="M-4,-212 C-124,-216 -176,-124 -172,-10 C-168,70 -196,140 -206,230 C-218,330 -232,410 -226,500
             C-222,560 -236,620 -214,690 C-196,748 -150,784 -104,790 C-116,740 -118,690 -108,640 L-60,170
             L40,300 C70,420 110,500 152,560 C164,540 172,520 176,500 C196,440 206,380 200,300 C196,230 180,170 176,106 C186,60 172,20 178,-30 C184,-90 176,-150 140,-184 C104,-214 50,-216 -4,-212 Z"
          fill="url(#fhairback)" {OUTLINE}/>
    <g fill="none" stroke="#5a3322" stroke-width="3" stroke-linecap="round" opacity=".7">
      <path d="M-188,300 C-196,380 -200,450 -194,540"/><path d="M-164,420 C-170,500 -170,580 -156,660"/>
      <path d="M150,20 C156,60 158,100 150,140"/><path d="M176,200 C188,280 190,360 176,450"/>
    </g>"""


def hair_front():
    """Side part at x=+38; a big sweep over the forehead to the left that falls past the cheek to the waist;
    a small curtain on the right tucked behind the ear."""
    clumps = [
        # (path, gradient)
        ("M40,-200 C-40,-204 -114,-156 -132,-66 C-140,-20 -138,40 -126,96 C-120,60 -116,10 -104,-34 C-86,-104 -30,-144 50,-156 Z", "fhair"),
        ("M-126,90 C-150,160 -166,240 -160,320 C-154,392 -178,462 -168,532 C-160,592 -134,646 -92,684"
         " C-112,634 -118,588 -110,534 C-102,478 -120,410 -112,340 C-104,270 -106,190 -106,110 Z", "fhair2"),
        ("M-110,120 C-124,200 -128,280 -118,350 C-110,420 -128,490 -116,560 C-108,610 -90,650 -66,672"
         " C-80,626 -84,582 -78,532 C-72,470 -92,400 -86,340 C-80,270 -86,200 -96,130 Z", "fhair"),
        ("M40,-200 C110,-192 146,-124 150,-40 C150,24 142,78 128,124 C124,58 116,-30 66,-156 Z", "fhair"),
        ("M-40,-168 C-86,-140 -112,-96 -122,-40 C-104,-86 -76,-122 -30,-146 Z", "fhair2"),
    ]
    # the two long strands (2nd and 3rd) hang over her shoulder, a little outward
    body = "".join(f'<path d="{d}" fill="url(#{g})" {OUTLINE}' + (' transform="translate(-52 0)"' if i in (1, 2) else "") + '/>'
                   for i, (d, g) in enumerate(clumps))
    return f"""{body}
    <g fill="none" stroke-linecap="round">
      <path d="M-92,-128 C-40,-160 0,-170 34,-172" stroke="{HAIR_HI}" stroke-width="9" opacity=".6"/>
      <path d="M-60,-140 C-90,-110 -108,-70 -114,-20" stroke="{HAIR_HI}" stroke-width="5" opacity=".5"/>
      <path d="M-198,230 C-208,300 -196,360 -204,430 C-210,490 -198,550 -180,600" stroke="{HAIR_HI}" stroke-width="6" opacity=".45"/>
      <path d="M-180,300 C-184,380 -170,440 -176,510" stroke="{HAIR_DK}" stroke-width="3" opacity=".6"/>
      <path d="M-152,360 C-152,430 -144,500 -148,570" stroke="{HAIR_HI}" stroke-width="4" opacity=".4"/>
      <path d="M118,-120 C132,-70 136,-20 134,30" stroke="{HAIR_HI}" stroke-width="5" opacity=".5"/>
      <path d="M96,-150 C112,-110 118,-60 116,0" stroke="{HAIR_DK}" stroke-width="3" opacity=".5"/>
      <path d="M-20,-164 C-60,-150 -90,-120 -104,-80" stroke="{HAIR_DK}" stroke-width="3" opacity=".45"/>
    </g>"""


def head_group(x, y, scale=0.72, tilt=0.0, **face_kw):
    """Hair back, face and hair front placed at (x, y) = face centre."""
    t = f"translate({x} {y}) rotate({tilt}) scale({scale})"
    return (f'<g id="hair_back" transform="{t}">{hair_back()}</g>',
            f'<g id="face" transform="{t}">{face(**face_kw)}{hair_front()}</g>')


if __name__ == "__main__":
    import sys
    import cairosvg
    back, front = head_group(300, 330, scale=1.2)
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="600" height="800" viewBox="0 0 600 800">
      <defs>{FACE_DEFS}</defs><rect width="600" height="800" fill="#ffeef5"/>
      <path d="M266,520 L266,600 L334,600 L334,520 Z" fill="{SKIN_SH}"/>{back}{front}</svg>"""
    cairosvg.svg2png(bytestring=svg.encode(), write_to=sys.argv[1] if len(sys.argv) > 1 else "face.png")
