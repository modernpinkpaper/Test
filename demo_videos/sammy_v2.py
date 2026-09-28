"""Sammy v2: a polished flat-illustration character drawn 100% by code (SVG curves, gradients, shading).

Every part is its own group, so it can be animated later (head tilt, blink, arm wave, mouth shapes).
    python demo_videos/sammy_v2.py out.png
"""
import sys

import cairosvg

SKIN, SKIN_SH, SKIN_HI = "#f2c39c", "#dfa27a", "#f9d7b8"
HAIR, HAIR_HI = "#3b2418", "#6a4331"
HOOD, HOOD_SH, HOOD_HI = "#ff7a59", "#e0573a", "#ff9c80"
INK = "#2a1a14"


def sammy(mouth="smile", blink=False):
    eyes = "" if blink else f"""
      <g id="eyes">
        <path d="M455,470 C465,448 510,446 520,468 C510,488 466,490 455,470 Z" fill="#fff"/>
        <path d="M565,468 C575,446 620,448 630,470 C619,490 575,488 565,468 Z" fill="#fff"/>
        <circle cx="489" cy="469" r="17" fill="url(#iris)"/><circle cx="597" cy="469" r="17" fill="url(#iris)"/>
        <circle cx="489" cy="470" r="8" fill="{INK}"/><circle cx="597" cy="470" r="8" fill="{INK}"/>
        <circle cx="495" cy="462" r="5" fill="#fff"/><circle cx="603" cy="462" r="5" fill="#fff"/>
        <circle cx="483" cy="476" r="2" fill="#fff" opacity=".8"/><circle cx="591" cy="476" r="2" fill="#fff" opacity=".8"/>
        <path d="M452,471 C462,444 512,440 523,467" fill="none" stroke="{INK}" stroke-width="6" stroke-linecap="round"/>
        <path d="M562,467 C573,440 623,444 633,471" fill="none" stroke="{INK}" stroke-width="6" stroke-linecap="round"/>
      </g>"""
    if blink:
        eyes = f"""<g id="eyes" fill="none" stroke="{INK}" stroke-width="6" stroke-linecap="round">
          <path d="M455,474 C470,486 506,486 520,474"/><path d="M565,474 C579,486 615,486 630,474"/></g>"""
    mouths = {
        "smile": f"""<path d="M500,566 C515,596 568,598 586,566 C565,578 520,578 500,566 Z" fill="#7a2e33"/>
                    <path d="M505,568 C525,576 562,576 581,568 L578,574 C560,580 526,580 508,574 Z" fill="#fff"/>
                    <path d="M520,588 C535,596 552,596 566,588 C552,592 535,592 520,588 Z" fill="#e0707a"/>""",
        "ah": f"""<path d="M505,560 C505,610 580,610 580,560 C560,570 525,570 505,560 Z" fill="#7a2e33"/>
                 <path d="M512,562 C530,570 556,570 574,562 L570,570 C552,576 532,576 515,570 Z" fill="#fff"/>
                 <ellipse cx="543" cy="592" rx="20" ry="9" fill="#e0707a"/>""",
        "oo": f"""<ellipse cx="543" cy="575" rx="14" ry="16" fill="#7a2e33"/>
                 <ellipse cx="543" cy="575" rx="14" ry="16" fill="none" stroke="#d68080" stroke-width="5"/>""",
    }
    return f"""
<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1350" viewBox="0 0 1080 1350">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#e8f3ff"/><stop offset="1" stop-color="#fdeee4"/></linearGradient>
    <radialGradient id="skin" cx=".45" cy=".4" r=".7">
      <stop offset="0" stop-color="{SKIN_HI}"/><stop offset=".6" stop-color="{SKIN}"/><stop offset="1" stop-color="{SKIN_SH}"/></radialGradient>
    <linearGradient id="hood" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{HOOD_HI}"/><stop offset=".5" stop-color="{HOOD}"/><stop offset="1" stop-color="{HOOD_SH}"/></linearGradient>
    <radialGradient id="iris" cx=".4" cy=".35" r=".7">
      <stop offset="0" stop-color="#8a5a3a"/><stop offset="1" stop-color="#3d2416"/></radialGradient>
    <linearGradient id="hair" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{HAIR_HI}"/><stop offset=".5" stop-color="{HAIR}"/><stop offset="1" stop-color="#26160f"/></linearGradient>
    <linearGradient id="screen" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#1d2b3a"/><stop offset="1" stop-color="#0f1822"/></linearGradient>
    <filter id="soft" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="14"/></filter>
  </defs>

  <!-- background -->
  <rect width="1080" height="1350" fill="url(#bg)"/>
  <circle cx="860" cy="260" r="190" fill="#cfe6ff" opacity=".7"/>
  <circle cx="180" cy="1050" r="230" fill="#ffd9c7" opacity=".6"/>
  <g opacity=".9">
    <circle cx="200" cy="330" r="34" fill="#ffcf4a"/><circle cx="200" cy="330" r="24" fill="#ffe08a"/>
    <text x="200" y="342" font-family="DejaVu Sans" font-weight="bold" font-size="32" fill="#e0a800" text-anchor="middle">$</text>
    <circle cx="905" cy="620" r="26" fill="#ffcf4a"/><circle cx="905" cy="620" r="18" fill="#ffe08a"/>
    <path d="M800,470 L840,430 L870,450 L920,390" fill="none" stroke="#2ecc71" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>
    <path d="M905,388 L924,386 L922,405" fill="none" stroke="#2ecc71" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>
  </g>

  <!-- soft shadow behind him -->
  <ellipse cx="545" cy="1000" rx="260" ry="330" fill="#9bb4d0" opacity=".25" filter="url(#soft)"/>

  <g transform="translate(540 0) scale(1.08 1) translate(-540 -80)">
  <g id="body">
    <!-- torso (hoodie) -->
    <path d="M300,1450 C300,960 340,800 430,748 C470,726 610,726 650,748 C740,800 780,960 780,1450 Z" fill="url(#hood)"/>
    <path d="M300,1450 C300,980 330,830 400,770 C380,860 380,1000 400,1450 Z" fill="{HOOD_SH}" opacity=".55"/>
    <!-- hood around the neck -->
    <path d="M440,742 C455,815 625,815 640,742 C660,760 662,790 640,812 C600,850 480,850 440,812 C418,790 420,760 440,742 Z" fill="{HOOD_SH}"/>
    <path d="M462,750 C480,800 600,800 618,750 C600,776 480,776 462,750 Z" fill="#c9442a"/>
    <!-- drawstrings -->
    <path d="M505,812 C502,860 506,900 500,935" fill="none" stroke="#fff" stroke-width="7" stroke-linecap="round"/>
    <path d="M575,812 C578,860 574,900 580,935" fill="none" stroke="#fff" stroke-width="7" stroke-linecap="round"/>
    <rect x="493" y="930" width="14" height="24" rx="5" fill="#d9d9d9"/><rect x="573" y="930" width="14" height="24" rx="5" fill="#d9d9d9"/>
    <!-- pocket and a couple of folds -->
    <path d="M400,1180 C470,1150 610,1150 680,1180 L700,1300 L380,1300 Z" fill="{HOOD_SH}" opacity=".5"/>
    <path d="M430,980 C450,1000 455,1030 448,1060" fill="none" stroke="{HOOD_SH}" stroke-width="6" stroke-linecap="round" opacity=".7"/>
    <path d="M665,1000 C650,1020 648,1045 655,1070" fill="none" stroke="{HOOD_SH}" stroke-width="6" stroke-linecap="round" opacity=".7"/>
  </g>

  <!-- left arm (his right), relaxed -->
  <g id="arm_r">
    <path d="M360,800 C320,860 305,1000 318,1140 C322,1170 360,1172 366,1140 C372,1020 378,900 410,820 Z" fill="url(#hood)"/>
    <path d="M318,1130 C312,1170 320,1205 342,1212 C366,1218 376,1188 370,1150 Z" fill="url(#skin)"/>
  </g>

  </g>
  <!-- neck and head -->
  <g id="head">
    <path d="M505,610 L505,670 C518,690 566,690 579,670 L579,610 Z" fill="{SKIN_SH}"/>
    <path d="M505,630 C525,650 559,650 579,630 L579,670 C566,690 518,690 505,670 Z" fill="#c98763" opacity=".55"/>
    <!-- ears -->
    <ellipse cx="397" cy="470" rx="22" ry="34" fill="{SKIN_SH}"/><ellipse cx="686" cy="470" rx="22" ry="34" fill="{SKIN_SH}"/>
    <path d="M392,452 C402,462 402,480 394,490" fill="none" stroke="#c98763" stroke-width="5" stroke-linecap="round"/>
    <path d="M691,452 C681,462 681,480 689,490" fill="none" stroke="#c98763" stroke-width="5" stroke-linecap="round"/>
    <!-- face -->
    <path d="M402,440 C400,340 460,300 542,300 C624,300 684,340 682,440 C682,540 640,618 542,640 C444,618 402,540 402,440 Z" fill="url(#skin)"/>
    <path d="M640,560 C620,610 585,630 542,640 C600,620 650,580 668,500 Z" fill="{SKIN_SH}" opacity=".45"/>
    <!-- hair -->
    <path d="M388,452 C372,340 420,246 522,236 C616,226 698,276 706,370 C709,405 702,432 692,456
             C680,412 664,380 642,362 C624,398 588,414 546,408 C578,392 594,372 600,350
             C562,386 502,400 456,388 C472,376 482,362 486,344 C450,370 420,402 404,452 Z" fill="url(#hair)"/>
    <path d="M470,262 C520,244 590,248 640,280" fill="none" stroke="{HAIR_HI}" stroke-width="10" stroke-linecap="round" opacity=".6"/>
    <path d="M430,300 C445,282 465,270 490,262" fill="none" stroke="{HAIR_HI}" stroke-width="7" stroke-linecap="round" opacity=".5"/>
    <!-- brows -->
    <path d="M448,428 C470,410 505,408 526,418 C505,418 474,424 452,436 Z" fill="{HAIR}"/>
    <path d="M636,428 C614,410 579,408 558,418 C579,418 610,424 632,436 Z" fill="{HAIR}"/>
    {eyes}
    <!-- nose -->
    <path d="M536,500 C530,528 532,544 552,548" fill="none" stroke="#c98763" stroke-width="5" stroke-linecap="round"/>
    <!-- cheeks -->
    <ellipse cx="455" cy="535" rx="30" ry="18" fill="#ff8a8a" opacity=".25"/>
    <ellipse cx="630" cy="535" rx="30" ry="18" fill="#ff8a8a" opacity=".25"/>
    <g id="mouth">{mouths[mouth]}</g>
  </g>

  <!-- right arm (his left) holding a phone -->
  <g transform="translate(540 0) scale(1.08 1) translate(-540 -80)">
  <g id="arm_l">
    <path d="M720,800 C770,860 790,960 760,1010 C740,1040 700,1030 690,1000 C700,960 700,900 680,830 Z" fill="url(#hood)"/>
    <path d="M760,1000 C730,1000 680,980 650,950 L690,920 C720,940 745,960 770,975 Z" fill="{HOOD_SH}"/>
    <g transform="rotate(-10 610 880)">
      <rect x="560" y="760" width="120" height="220" rx="18" fill="#222"/>
      <rect x="568" y="772" width="104" height="196" rx="12" fill="url(#screen)"/>
      <path d="M580,920 L605,895 L625,905 L660,850" fill="none" stroke="#2ecc71" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>
      <text x="620" y="818" font-family="DejaVu Sans" font-weight="bold" font-size="22" fill="#fff" text-anchor="middle">$100</text>
      <text x="620" y="842" font-family="DejaVu Sans" font-size="15" fill="#2ecc71" text-anchor="middle">+8% / yr</text>
    </g>
    <!-- hand wrapped around the phone -->
    <path d="M640,930 C630,960 650,985 680,985 C705,985 715,960 705,935 C700,915 670,905 650,912 Z" fill="url(#skin)"/>
    <path d="M655,915 C640,900 645,880 660,878 C672,878 676,892 672,905" fill="url(#skin)"/>
    <path d="M662,945 C672,950 684,950 694,944" fill="none" stroke="#c98763" stroke-width="3" stroke-linecap="round"/>
    <path d="M660,962 C672,968 686,968 698,960" fill="none" stroke="#c98763" stroke-width="3" stroke-linecap="round"/>
  </g>
  </g>
</svg>"""


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "sammy_v2.png"
    cairosvg.svg2png(bytestring=sammy().encode(), write_to=out)
    print("saved", out)
