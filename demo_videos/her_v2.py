"""The 'skinny girl' character drawn 100% by code, same style as Sammy v2 (SVG curves, gradients, shading).

Based on the brand's character: long wavy brown hair swept to one side, big brown eyes with winged liner,
strong brows, tan skin, black scoop-neck tee, high-waisted skinny jeans, white sneakers.
Every part is its own group so it can be animated (blink, mouth shapes, arm moves).
    python demo_videos/her_v2.py out.png
"""
import sys

import cairosvg

SKIN, SKIN_SH, SKIN_HI, SKIN_LINE = "#e9b48c", "#cf946b", "#f5cda9", "#b77c58"
HAIR, HAIR_HI, HAIR_DK = "#5a3522", "#8a5a3b", "#3a2014"
TEE, TEE_HI = "#1f1c21", "#3a3540"
JEANS, JEANS_SH, JEANS_HI, STITCH = "#3f6aa3", "#2f5286", "#5b86bd", "#d9a35c"
INK = "#241612"


def eye(cx, flip=1, closed=False):
    """One eye at (cx, 405). flip=1 is the eye on the left of the picture (outer corner on the left)."""
    f = lambda x: cx + (x - 495) * flip
    if closed:
        return f"""<path d="M{f(528)},410 C{f(512)},424 {f(478)},424 {f(462)},408 L{f(449)},397" fill="none" stroke="{INK}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>"""
    lashes = "".join(f'<path d="M{f(x)},{y} L{f(x - dx)},{y - 10}" stroke="{INK}" stroke-width="2.6" stroke-linecap="round"/>'
                     for x, y, dx in ((470, 394, 6), (480, 388, 4), (492, 385, 2), (504, 385, 0), (516, 388, -2)))
    return f"""
      <path d="M{f(465)},405 C{f(475)},384 {f(517)},382 {f(528)},402 C{f(516)},421 {f(478)},423 {f(465)},405 Z" fill="#fff"/>
      <circle cx="{f(497)}" cy="404" r="15" fill="url(#iris)"/>
      <circle cx="{f(497)}" cy="405" r="7" fill="{INK}"/>
      <circle cx="{f(502)}" cy="398" r="4.5" fill="#fff"/><circle cx="{f(492)}" cy="410" r="2" fill="#fff" opacity=".8"/>
      <path d="M{f(530)},403 C{f(518)},380 {f(474)},380 {f(461)},404 L{f(446)},393" fill="none" stroke="{INK}" stroke-width="6.5" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M{f(470)},413 C{f(485)},424 {f(512)},423 {f(526)},410" fill="none" stroke="{SKIN_LINE}" stroke-width="2" opacity=".7"/>
      {lashes}"""


def mirror_path(d):
    """Mirror an 'x,y' path around x=540 (for the other arm, leg, shoe)."""
    out = []
    for tok in d.split():
        if "," in tok:
            x, y = tok.split(",")
            prefix = "".join(c for c in x if c.isalpha())
            xv = float(x.lstrip("MCLZ"))
            out.append(f"{prefix}{1080 - xv:g},{y}")
        else:
            out.append(tok)
    return " ".join(out)


def her(mouth="smile", blink=False):
    arm = "M372,742 C360,820 360,900 372,980 C378,1030 384,1060 390,1088 L416,1088 C412,1040 410,1000 408,960 C405,880 405,820 402,762 Z"
    hand = "M386,1082 C372,1112 382,1150 404,1154 C426,1156 430,1122 420,1084 Z"
    shoe = "M452,1706 C438,1750 442,1788 468,1800 L566,1800 C580,1788 576,1760 552,1734 C542,1720 538,1708 536,1706 Z"
    mouths = {
        "smile": f"""<path d="M510,500 C525,491 538,495 545,498 C552,495 565,491 580,500 C565,507 525,507 510,500 Z" fill="#c9686f"/>
                    <path d="M512,501 C526,521 564,521 578,501 C560,509 530,509 512,501 Z" fill="#e0888d"/>
                    <path d="M507,499 C525,506 565,506 583,499" fill="none" stroke="#9c4a52" stroke-width="2.6" stroke-linecap="round"/>
                    <ellipse cx="548" cy="511" rx="10" ry="3" fill="#fff" opacity=".35"/>""",
        "ah": f"""<path d="M512,496 C522,490 538,493 545,495 C552,493 568,490 578,496 C582,528 566,546 545,546 C524,546 508,528 512,496 Z" fill="#c9686f"/>
                 <path d="M517,500 C530,505 560,505 573,500 C574,524 562,538 545,538 C528,538 516,524 517,500 Z" fill="#6e2530"/>
                 <path d="M518,500 C532,506 558,506 572,500 L570,508 C556,512 534,512 520,508 Z" fill="#fff"/>
                 <ellipse cx="545" cy="530" rx="14" ry="6" fill="#e27b86"/>""",
        "oo": f"""<ellipse cx="545" cy="508" rx="17" ry="17" fill="#d0757b"/><ellipse cx="545" cy="508" rx="8" ry="9" fill="#6e2530"/>""",
    }
    return f"""
<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920" viewBox="0 0 1080 1920">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#ffeef5"/><stop offset="1" stop-color="#ffd6e6"/></linearGradient>
    <radialGradient id="skin" cx=".45" cy=".4" r=".75">
      <stop offset="0" stop-color="{SKIN_HI}"/><stop offset=".6" stop-color="{SKIN}"/><stop offset="1" stop-color="{SKIN_SH}"/></radialGradient>
    <linearGradient id="limb" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="{SKIN_SH}"/><stop offset=".45" stop-color="{SKIN}"/><stop offset="1" stop-color="{SKIN_HI}"/></linearGradient>
    <radialGradient id="iris" cx=".4" cy=".35" r=".7">
      <stop offset="0" stop-color="#9a6a45"/><stop offset="1" stop-color="#3e2215"/></radialGradient>
    <linearGradient id="hair" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{HAIR_HI}"/><stop offset=".45" stop-color="{HAIR}"/><stop offset="1" stop-color="{HAIR_DK}"/></linearGradient>
    <linearGradient id="tee" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#141216"/><stop offset=".5" stop-color="{TEE_HI}"/><stop offset="1" stop-color="#141216"/></linearGradient>
    <linearGradient id="jeans" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="{JEANS_SH}"/><stop offset=".35" stop-color="{JEANS_HI}"/><stop offset=".65" stop-color="{JEANS}"/><stop offset="1" stop-color="{JEANS_SH}"/></linearGradient>
    <linearGradient id="shoe" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#e3e3ea"/></linearGradient>
    <filter id="soft" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="16"/></filter>
  </defs>

  <rect width="1080" height="1920" fill="url(#bg)"/>
  <circle cx="860" cy="360" r="200" fill="#ffc3da" opacity=".55"/>
  <circle cx="190" cy="1300" r="240" fill="#ffe0ec" opacity=".8"/>
  <path d="M830,650 C830,630 860,630 860,650 C860,630 890,630 890,650 C890,675 860,690 860,700 C860,690 830,675 830,650 Z" fill="#ff7aa8" opacity=".8"/>
  <path d="M215,520 L225,545 L250,555 L225,565 L215,590 L205,565 L180,555 L205,545 Z" fill="#fff"/>
  <ellipse cx="545" cy="1805" rx="200" ry="22" fill="#d98aa9" opacity=".35" filter="url(#soft)"/>

  <!-- hair behind her: full and wavy, long on the left, tucked behind the shoulder on the right -->
  <g id="hair_back">
    <path d="M545,205 C432,200 364,280 360,392 C357,470 336,530 330,600 C322,660 300,700 306,780
             C312,850 296,900 316,960 C334,1016 376,1052 430,1064 C412,1030 404,990 414,950
             C426,900 412,860 418,810 L470,640 L630,650 C664,640 690,610 698,560
             C706,510 690,470 700,420 C712,360 700,300 676,262 C646,222 600,205 545,205 Z" fill="url(#hair)"/>
  </g>
  <!-- legs: jeans and shoes -->
  <g id="legs">
    <path d="M440,1000 L650,1000 C668,1060 678,1120 675,1190 C670,1320 655,1450 640,1560 C632,1620 628,1680 626,1722
             L560,1722 C562,1640 565,1560 562,1480 C558,1380 552,1290 547,1226 L543,1226 C538,1290 532,1380 528,1480
             C525,1560 528,1640 530,1722 L464,1722 C462,1680 458,1620 450,1560 C435,1450 420,1320 415,1190 C412,1120 422,1060 440,1000 Z" fill="url(#jeans)"/>
    <path d="M545,1060 L545,1226" stroke="{JEANS_SH}" stroke-width="4"/>
    <path d="M470,1130 C500,1250 505,1400 492,1560" fill="none" stroke="{JEANS_HI}" stroke-width="10" opacity=".35" stroke-linecap="round"/>
    <path d="M622,1130 C600,1250 595,1400 606,1560" fill="none" stroke="{JEANS_SH}" stroke-width="10" opacity=".35" stroke-linecap="round"/>
    <rect x="438" y="1000" width="214" height="34" rx="6" fill="{JEANS_SH}"/>
    <path d="M442,1030 L648,1030" stroke="{STITCH}" stroke-width="2" stroke-dasharray="6 5"/>
    <circle cx="545" cy="1017" r="8" fill="#c9ccd6" stroke="#8b8f9c" stroke-width="2"/>
    <path d="M545,1034 L545,1110 C545,1122 555,1128 565,1120" fill="none" stroke="{STITCH}" stroke-width="2" stroke-dasharray="6 5"/>
    <path d="M452,1045 C470,1075 500,1085 520,1080" fill="none" stroke="{STITCH}" stroke-width="2" stroke-dasharray="6 5"/>
    <path d="M638,1045 C620,1075 590,1085 570,1080" fill="none" stroke="{STITCH}" stroke-width="2" stroke-dasharray="6 5"/>
    <rect x="476" y="995" width="10" height="42" rx="3" fill="{JEANS_SH}"/><rect x="604" y="995" width="10" height="42" rx="3" fill="{JEANS_SH}"/>
    <path d="M470,1716 C478,1726 520,1726 528,1716 L530,1730 L468,1730 Z" fill="{SKIN_SH}"/>
    <path d="M{1080-528},1716 C{1080-520},1726 {1080-478},1726 {1080-470},1716 L{1080-468},1730 L{1080-530},1730 Z" fill="{SKIN_SH}"/>
    <path d="{shoe}" fill="url(#shoe)"/><path d="{mirror_path(shoe)}" fill="url(#shoe)"/>
    <path d="M442,1778 C470,1792 544,1792 578,1782 L572,1802 L468,1804 C452,1802 444,1792 442,1778 Z" fill="#cfd0da"/>
    <path d="M{1080-442},1778 C{1080-470},1792 {1080-544},1792 {1080-578},1782 L{1080-572},1802 L{1080-468},1804 C{1080-452},1802 {1080-444},1792 {1080-442},1778 Z" fill="#cfd0da"/>
    <g stroke="#c4c6d2" stroke-width="3" stroke-linecap="round">
      <path d="M478,1736 L512,1732"/><path d="M476,1748 L514,1744"/><path d="M476,1760 L516,1756"/>
      <path d="M{1080-478},1736 L{1080-512},1732"/><path d="M{1080-476},1748 L{1080-514},1744"/><path d="M{1080-476},1760 L{1080-516},1756"/>
    </g>
  </g>

  <!-- arms -->
  <g id="arm_r"><path d="{arm}" fill="url(#limb)"/><path d="{hand}" fill="url(#skin)"/>
    <path d="M398,1120 L396,1146" stroke="{SKIN_LINE}" stroke-width="2" opacity=".6"/></g>
  <g id="arm_l"><path d="{mirror_path(arm)}" fill="url(#limb)"/><path d="{mirror_path(hand)}" fill="url(#skin)"/>
    <path d="M682,1120 L684,1146" stroke="{SKIN_LINE}" stroke-width="2" opacity=".6"/></g>

  <!-- torso: fitted black tee -->
  <g id="torso">
    <path d="M450,640 C470,625 495,618 506,620 C520,652 570,652 584,620 C595,618 620,625 640,640 C690,655 715,690 720,742
             L690,762 C680,800 668,860 662,920 C656,960 652,990 650,1010 L440,1010 C438,990 434,960 428,920 C422,860 410,800 400,762
             L370,742 C375,690 400,655 450,640 Z" fill="url(#tee)"/>
    <path d="M478,626 C492,712 598,712 612,626 C590,640 500,640 478,626 Z" fill="url(#skin)"/>
    <path d="M478,626 C492,712 598,712 612,626" fill="none" stroke="#0d0b0e" stroke-width="7"/>
    <path d="M500,660 C515,668 530,670 540,668" fill="none" stroke="{SKIN_LINE}" stroke-width="2.5" stroke-linecap="round"/>
    <path d="M590,660 C575,668 560,670 550,668" fill="none" stroke="{SKIN_LINE}" stroke-width="2.5" stroke-linecap="round"/>
    <path d="M545,694 L545,706" stroke="{SKIN_LINE}" stroke-width="2.5" stroke-linecap="round"/>
    <path d="M470,780 C500,820 590,820 620,780" fill="none" stroke="#3d3844" stroke-width="5" opacity=".6" stroke-linecap="round"/>
    <path d="M455,900 C470,940 470,970 462,1000" fill="none" stroke="#3d3844" stroke-width="4" opacity=".5" stroke-linecap="round"/>
    <path d="M372,742 L400,762" stroke="#0d0b0e" stroke-width="5"/><path d="M708,742 L680,762" stroke="#0d0b0e" stroke-width="5"/>
  </g>

  <!-- head -->
  <g id="head">
    <path d="M512,530 C514,570 510,600 504,625 L586,625 C580,600 576,570 578,530 Z" fill="{SKIN_SH}"/>
    <path d="M512,540 C530,565 560,565 578,540 L578,560 C560,585 530,585 512,560 Z" fill="#b97e5a" opacity=".5"/>
    <path d="M440,380 C438,290 485,245 545,245 C605,245 652,290 650,380 C650,470 612,540 545,562 C478,540 440,470 440,380 Z" fill="url(#skin)"/>
    <path d="M620,470 C605,520 580,548 545,562 C590,545 632,505 645,440 Z" fill="{SKIN_SH}" opacity=".45"/>
    <!-- brows -->
    <path d="M456,372 C473,350 510,346 532,360 C510,358 480,364 460,382 Z" fill="{HAIR_DK}"/>
    <path d="M634,372 C617,350 580,346 558,360 C580,358 610,364 630,382 Z" fill="{HAIR_DK}"/>
    <g id="eyes">{eye(495, 1, blink)}{eye(595, -1, blink)}</g>
    <path d="M540,430 C534,456 537,468 553,470" fill="none" stroke="{SKIN_LINE}" stroke-width="4" stroke-linecap="round"/>
    <ellipse cx="478" cy="468" rx="26" ry="14" fill="#ff8a8a" opacity=".28"/>
    <ellipse cx="612" cy="468" rx="26" ry="14" fill="#ff8a8a" opacity=".28"/>
    <g id="mouth">{mouths[mouth]}</g>
  </g>

  <!-- hair in front: side part, a big wave framing the face and falling over the left shoulder -->
  <g id="hair_front">
    <path d="M592,232 C522,234 456,272 438,346 C428,392 432,440 444,482
             C424,540 408,610 416,690 C424,760 398,830 406,900 C414,968 440,1020 482,1052
             C462,1006 456,958 466,900 C476,844 458,770 466,700 C474,630 468,560 462,500
             C455,450 452,400 458,360 C470,318 520,288 600,262 Z" fill="url(#hair)"/>
    <path d="M592,232 C640,242 672,288 676,356 C680,418 670,468 656,506 C652,440 640,360 598,262 Z" fill="url(#hair)"/>
    <g fill="none" stroke="{HAIR_HI}" stroke-linecap="round" opacity=".6">
      <path d="M470,282 C512,256 562,244 596,240" stroke-width="8"/>
      <path d="M452,340 C466,308 486,288 512,272" stroke-width="5"/>
      <path d="M436,600 C428,670 438,730 428,800 C420,860 428,920 446,970" stroke-width="6"/>
      <path d="M455,520 C450,560 446,600 444,640" stroke-width="4"/>
      <path d="M652,300 C662,332 666,366 664,400" stroke-width="4"/>
      <path d="M340,640 C330,720 338,800 330,880" stroke-width="5"/>
    </g>
    <g fill="none" stroke="{HAIR_DK}" stroke-linecap="round" opacity=".55">
      <path d="M452,700 C446,780 456,860 450,940" stroke-width="4"/>
      <path d="M372,560 C356,660 352,760 360,880" stroke-width="4"/>
      <path d="M620,280 C640,330 648,380 646,440" stroke-width="3"/>
    </g>
  </g>
</svg>"""


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "her_v2.png"
    cairosvg.svg2png(bytestring=her().encode(), write_to=out)
    print("saved", out)
