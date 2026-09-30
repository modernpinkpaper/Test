"""Stylized stick people (cairo) for skits: big expressive faces, hair styles, outfits, slim tapered limbs (thick at
the joint, thin at the tip) instead of plain lines.

    boss = StickPerson(LOOKS["boss"], x=300, floor=1560)
    boss.draw(ctx, arms=((20, 30), (20, 30)), legs=((4, 0), (4, 0)), face="smug", mouth=0.0, look=(0, 0))

arms: ((shoulder, elbow), (shoulder, elbow)) in degrees for her right / left arm (0 = hanging down, + = outwards);
legs: ((hip, knee), ...) likewise. face: neutral | happy | smug | annoyed | shock | sad | wink | closed.
"""
import math

from toon import curve, ellipse, poly, rgb

COL = dict(outline="#1f0e08", skin="#fbcdad", skin_shade="#e1ab8b", shirt="#2a2b2c", shirt_hi="#3a3b3d",
           jeans="#374f6b", jeans_hi="#46618a", hair="#513527", hair_dark="#382117", hair_light="#8c593e",
           hair_hi="#a8704f", iris="#6b3a1e", iris_dark="#3a1c0c", blush="#febcaa", lips="#f07f8c", shoe="#ffffff",
           sole="#dadada")
OUT = rgb(COL["outline"])


def _catmull(pts, n=8):
    """Points along a smooth curve through pts."""
    P = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2 +
                                    (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1)))
    out.append(pts[-1])
    return out


def taper(ctx, pts, w0, w1, fill, line=OUT, lw=5.0, cap=True):
    """A limb: a smooth band along pts, w0 wide at the start and w1 at the end, round ends, outlined."""
    c = _catmull(pts)
    n = len(c)
    left, right = [], []
    for i, p in enumerate(c):
        a = c[max(i - 1, 0)]
        b = c[min(i + 1, n - 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1
        nx, ny = -dy / L, dx / L
        w = (w0 + (w1 - w0) * i / (n - 1)) / 2
        left.append((p[0] + nx * w, p[1] + ny * w))
        right.append((p[0] - nx * w, p[1] - ny * w))
    ctx.move_to(*left[0])
    for p in left[1:]:
        ctx.line_to(*p)
    e = c[-1]
    ang = math.atan2(right[-1][1] - e[1], right[-1][0] - e[0])
    ctx.arc_negative(e[0], e[1], w1 / 2, ang + math.pi, ang) if cap else ctx.line_to(*right[-1])
    for p in reversed(right):
        ctx.line_to(*p)
    s = c[0]
    ang0 = math.atan2(left[0][1] - s[1], left[0][0] - s[0])
    ctx.arc_negative(s[0], s[1], w0 / 2, ang0 + math.pi, ang0) if cap else None
    ctx.close_path()
    ctx.set_source_rgb(*rgb(fill))
    ctx.fill_preserve()
    ctx.set_source_rgb(*line)
    ctx.set_line_width(lw)
    ctx.set_line_join(1)
    ctx.stroke()


LOOKS = {
    # hairdo: long | bob | short | bald ; build: f | m
    "candidate": dict(hairdo="bob", hair="#e8b04a", hair_dark="#b9822a", hair_hi="#ffd98a", hair_light="#f3c569", skin="#f6c7a4",
                      shirt="#ffffff", jacket="#f27ca8", pants="#2f3a55", shoes="#1f1a1a", lashes=True, cheeks=True,
                      build="f", glasses=False, tie=None, brow="#8a5a2a", iris="#2f6fb0", iris_dark="#1d3f6a"),
    "worker": dict(hairdo="bob", hair="#3b2320", hair_dark="#24140f", hair_hi="#7a4a3a", hair_light="#5a342a",
                   skin="#f3c09c", shirt="#ffffff", jacket="#4fa384", pants="#2f3a55", shoes="#1f1a1a", lashes=True,
                   cheeks=True, build="f", glasses=False, tie=None, brow="#3b2320", iris="#5a3a22", iris_dark="#2a180c"),
    "coworker": dict(hairdo="short", hair="#1f1a1a", hair_dark="#111111", hair_hi="#4a4a4a", hair_light="#333333",
                     skin="#c98e6a", shirt="#4a7bd0", jacket=None, pants="#b89a6e", shoes="#3a2a20", lashes=False,
                     cheeks=False, build="m", glasses=False, tie=None, brow="#1f1a1a", iris="#3a2414", iris_dark="#1a0f08"),
    "boss": dict(hairdo="bald", hair="#6b6b6b", hair_dark="#4a4a4a", hair_hi="#9a9a9a", hair_light="#8a8a8a", skin="#e9b28f",
                 shirt="#e9eef6", jacket="#4b5563", pants="#3b4250", shoes="#1f1a1a", lashes=False, cheeks=False,
                 build="m", glasses=True, tie="#c0392b", brow="#4a4a4a", iris="#5a3a22", iris_dark="#2a180c",
                 mustache=True),
}


class StickPerson:
    def __init__(self, look, x=540, floor=1560, scale=1.0, facing=0.0):
        self.L = dict(COL, pants=COL["jeans"], shoes=COL["shoe"], lashes=True, cheeks=True, build="f", hairdo="long", glasses=False,
                      tie=None, jacket=None, brow="#3a2216", mustache=False)
        self.L.update(look)
        self.x, self.floor, self.s, self.facing = x, floor, scale, facing     # facing: -1 left .. 0 front .. 1 right

    # ---------------------------------------------------------------- body
    def draw(self, ctx, arms=((12, 10), (12, 10)), legs=((4, 0), (4, 0)), face="neutral", mouth=0.0, look=(0, 0),
             tilt=0.0, bob=0.0, blink=False, hold=None, hair_sway=0.0, hold_on_top=False):
        s = self.s
        leg = 138 * s
        hip = (self.x, self.floor - 2 * leg * 0.97 - 22 * s + bob)
        neck = (hip[0] + tilt * 0.3, hip[1] - 185 * s)
        R = 104 * s
        hc = (neck[0] + tilt * 0.8, neck[1] - R * 0.95)
        self._hair_back(ctx, hc, R, hair_sway)
        # legs (jeans), sneakers
        feet = []
        for side, (a, k) in ((-1, legs[0]), (1, legs[1])):
            h = (hip[0] + side * 16 * s, hip[1])
            u = math.radians(a) * side
            knee = (h[0] + math.sin(u) * leg, h[1] + math.cos(u) * leg)
            lo = u - math.radians(k) * side
            foot = (knee[0] + math.sin(lo) * leg, min(knee[1] + math.cos(lo) * leg, self.floor - 16 * s))
            taper(ctx, [h, knee, foot], 34 * s, 20 * s, self.L["pants"], lw=5 * s)
            feet.append((side, foot))
        for side, f in feet:
            fx = f[0] + side * 8 * s + self.facing * 10 * s
            ellipse(ctx, fx, f[1] + 8 * s, 28 * s, 15 * s, fill=self.L["shoes"], w=5 * s)
            curve(ctx, [(fx - 26 * s, f[1] + 14 * s), (fx + 26 * s, f[1] + 14 * s)], line=rgb(self.L["sole"]), w=4 * s)
        # torso: fitted black tee (a soft hourglass), neck
        top = neck[1] + 14 * s
        tw, ww, hw = (54 * s, 36 * s, 52 * s) if self.L["build"] == "f" else (64 * s, 54 * s, 52 * s)
        mid = (top + hip[1]) / 2 + 10 * s
        ctx.move_to(neck[0] - tw, top + 8 * s)
        ctx.curve_to(neck[0] - tw * .6, top - 4 * s, neck[0] + tw * .6, top - 4 * s, neck[0] + tw, top + 8 * s)
        ctx.curve_to(neck[0] + tw * .95, mid - 40 * s, hip[0] + ww, mid, hip[0] + hw, hip[1] + 12 * s)
        ctx.line_to(hip[0] - hw, hip[1] + 12 * s)
        ctx.curve_to(hip[0] - ww, mid, neck[0] - tw * .95, mid - 40 * s, neck[0] - tw, top + 8 * s)
        ctx.close_path()
        ctx.set_source_rgb(*rgb(self.L["shirt"]))
        ctx.fill_preserve()
        ctx.set_source_rgb(*OUT)
        ctx.set_line_width(5 * s)
        ctx.stroke()
        poly(ctx, [(hip[0] - hw, hip[1] + 6 * s), (hip[0] + hw, hip[1] + 6 * s), (hip[0] + hw, hip[1] + 26 * s),
                   (hip[0] - hw, hip[1] + 26 * s)], fill=self.L["pants"], w=5 * s)                    # waistband
        ellipse(ctx, hip[0], hip[1] + 16 * s, 5 * s, 5 * s, fill="#d8d8d8", w=2 * s)
        taper(ctx, [(neck[0], neck[1] - 30 * s), (neck[0], top + 6 * s)], 26 * s, 24 * s, self.L["skin"], lw=5 * s, cap=False)
        ctx.move_to(neck[0] - 22 * s, top + 2 * s)                                                  # crew neck
        ctx.curve_to(neck[0] - 12 * s, top + 22 * s, neck[0] + 12 * s, top + 22 * s, neck[0] + 22 * s, top + 2 * s)
        ctx.set_source_rgb(*OUT)
        ctx.set_line_width(4 * s)
        ctx.stroke()
        if self.L["tie"]:
            poly(ctx, [(neck[0] - 9 * s, top + 14 * s), (neck[0] + 9 * s, top + 14 * s), (neck[0] + 13 * s, mid + 30 * s),
                       (neck[0], mid + 48 * s), (neck[0] - 13 * s, mid + 30 * s)], fill=self.L["tie"], w=4 * s)
        if self.L["jacket"]:                                           # open blazer: two panels, lapels
            for side in (-1, 1):
                poly(ctx, [(neck[0] + side * 18 * s, top + 2 * s), (neck[0] + side * tw, top + 8 * s),
                           (hip[0] + side * (hw + 4 * s), hip[1] + 18 * s), (hip[0] + side * 16 * s, hip[1] + 18 * s),
                           (neck[0] + side * 24 * s, mid - 10 * s)], fill=self.L["jacket"], w=5 * s)
                poly(ctx, [(neck[0] + side * 18 * s, top + 2 * s), (neck[0] + side * 34 * s, top + 30 * s),
                           (neck[0] + side * 24 * s, mid - 10 * s)], fill=self.L["jacket"], w=4 * s)
        # arms: short sleeve (or blazer sleeve), tapered skin, round hand
        sh_y = top + 18 * s
        hands = []
        for side, (a1, a2) in ((-1, arms[0]), (1, arms[1])):
            sh = (neck[0] + side * (tw - 8 * s), sh_y)
            u = math.radians(a1) * side
            el = (sh[0] + math.sin(u) * 92 * s, sh[1] + math.cos(u) * 92 * s)
            lo = u + math.radians(a2) * side
            hd = (el[0] + math.sin(lo) * 84 * s, el[1] + math.cos(lo) * 84 * s)
            if self.L["jacket"]:                                        # long sleeve to the wrist
                taper(ctx, [sh, el, hd], 30 * s, 22 * s, self.L["jacket"], lw=5 * s)
                ellipse(ctx, sh[0], sh[1], 17 * s, 17 * s, fill=self.L["jacket"], line=None)
            else:
                taper(ctx, [sh, el, hd], 24 * s, 15 * s, self.L["skin"], lw=5 * s)
                sl = (sh[0] + math.sin(u) * 34 * s, sh[1] + math.cos(u) * 34 * s)                      # sleeve
                taper(ctx, [sh, sl], 30 * s, 28 * s, self.L["shirt"], lw=5 * s, cap=False)
                ellipse(ctx, sh[0], sh[1], 15 * s, 15 * s, fill=self.L["shirt"], line=None)
            ellipse(ctx, hd[0], hd[1], 15 * s, 15 * s, fill=self.L["skin"], w=5 * s)
            hands.append(hd)
        if hold and not hold_on_top:
            hold(ctx, hands)
        self._head(ctx, hc, R, face, mouth, look, blink)
        self._hair_front(ctx, hc, R)
        if hold and hold_on_top:                       # a cup at her mouth goes in front of the face (straw and all)
            hold(ctx, hands)
        self.head_c, self.head_r, self.hands = hc, R, hands
        return hc, hands

    # ---------------------------------------------------------------- hair
    def _hair_back(self, ctx, hc, R, sway):
        """Long hair behind her: from the crown down past her shoulders, wavy ends, a lighter streak."""
        s = self.s
        x, y = hc
        sw = sway * 20 * s
        if self.L["hairdo"] == "bob":
            curve(ctx, [(x - R * 1.08, y - R * 0.3), (x - R * 1.2, y + R * 0.5), (x - R * 1.1 + sw, y + R * 1.05),
                        (x, y + R * 0.9), (x + R * 1.1 + sw, y + R * 1.05), (x + R * 1.2, y + R * 0.5),
                        (x + R * 1.08, y - R * 0.3), (x, y - R * 1.15)], fill=self.L["hair"], line=OUT, w=6 * s, close=True)
            return
        if self.L["hairdo"] != "long":
            return
        pts = [(x - R * 1.05, y - R * 0.2), (x - R * 1.25, y + R * 0.9), (x - R * 1.2 + sw, y + R * 2.1),
               (x - R * 1.35 + sw, y + R * 3.0), (x - R * 0.9 + sw, y + R * 3.35), (x - R * 0.6 + sw, y + R * 3.05),
               (x, y + R * 1.6), (x + R * 0.6 + sw, y + R * 3.05), (x + R * 0.95 + sw, y + R * 3.3),
               (x + R * 1.35 + sw, y + R * 2.95), (x + R * 1.2 + sw, y + R * 2.0), (x + R * 1.25, y + R * 0.9),
               (x + R * 1.05, y - R * 0.2), (x, y - R * 1.12)]
        curve(ctx, pts, fill=self.L["hair"], line=OUT, w=6 * s, close=True)
        for dx in (-1, 1):                                                              # soft streaks
            curve(ctx, [(x + dx * R * 1.0, y + R * 0.4), (x + dx * R * 1.1 + sw * .6, y + R * 1.5),
                        (x + dx * R * 1.05 + sw, y + R * 2.6)], line=rgb(self.L["hair_light"]), w=9 * s)

    def _hair_front(self, ctx, hc, R):
        """Side part on her left, bangs sweeping across the forehead, face-framing locks."""
        s = self.s
        x, y = hc
        if self.L["hairdo"] == "bald":                                   # side tufts + a shiny head
            for side in (-1, 1):
                curve(ctx, [(x + side * R * 0.8, y - R * 0.45), (x + side * R * 1.06, y - R * 0.1), (x + side * R * 1.0, y + R * 0.3),
                            (x + side * R * 0.9, y - R * 0.1)], fill=self.L["hair"], line=OUT, w=5 * s, close=True)
            ellipse(ctx, x - R * 0.35, y - R * 0.72, R * 0.2, R * 0.09, fill=(1, 1, 1), line=None)
            return
        if self.L["hairdo"] == "short":
            curve(ctx, [(x - R * 1.0, y - R * 0.1), (x - R * 0.85, y - R * 0.8), (x, y - R * 1.12), (x + R * 0.85, y - R * 0.8),
                        (x + R * 1.0, y - R * 0.1), (x + R * 0.6, y - R * 0.55), (x - R * 0.4, y - R * 0.6)],
                  fill=self.L["hair"], line=OUT, w=6 * s, close=True)
            return
        part = x + R * 0.28
        # the big sweep from the part to her right temple
        curve(ctx, [(part, y - R * 1.08), (x - R * 0.35, y - R * 0.98), (x - R * 0.9, y - R * 0.55),
                    (x - R * 1.02, y + R * 0.1), (x - R * 0.95, y + R * 0.55), (x - R * 0.8, y + R * 0.05),
                    (x - R * 0.55, y - R * 0.45), (x - R * 0.05, y - R * 0.62), (part - R * 0.05, y - R * 0.9)],
              fill=self.L["hair"], line=OUT, w=6 * s, close=True)
        # the smaller side
        curve(ctx, [(part, y - R * 1.08), (x + R * 0.8, y - R * 0.8), (x + R * 1.03, y - R * 0.1),
                    (x + R * 0.98, y + R * 0.6), (x + R * 0.85, y + R * 0.0), (x + R * 0.62, y - R * 0.55),
                    (part + R * 0.06, y - R * 0.88)], fill=self.L["hair"], line=OUT, w=6 * s, close=True)
        # shine
        curve(ctx, [(x - R * 0.15, y - R * 0.9), (x - R * 0.55, y - R * 0.72), (x - R * 0.78, y - R * 0.35)],
              line=rgb(self.L["hair_hi"]), w=8 * s)
        curve(ctx, [(x + R * 0.45, y - R * 0.92), (x + R * 0.78, y - R * 0.55)], line=rgb(self.L["hair_light"]), w=7 * s)

    # ---------------------------------------------------------------- face
    def _head(self, ctx, hc, R, face, mouth, look, blink):
        s = self.s
        x, y = hc
        f = self.facing * R * 0.12
        # soft rounded face, slightly narrower chin
        curve(ctx, [(x - R * 0.98, y - R * 0.15), (x - R * 0.9, y + R * 0.45), (x - R * 0.55, y + R * 0.85),
                    (x + f, y + R * 1.0), (x + R * 0.55, y + R * 0.85), (x + R * 0.9, y + R * 0.45),
                    (x + R * 0.98, y - R * 0.15), (x + R * 0.7, y - R * 0.85), (x, y - R * 1.02),
                    (x - R * 0.7, y - R * 0.85)], fill=self.L["skin"], line=OUT, w=6 * s, close=True)
        for side in (-1, 1):                                                              # ears peek out
            ellipse(ctx, x + side * R * 0.97, y + R * 0.12, 12 * s, 18 * s, fill=self.L["skin"], w=4 * s)
        if self.L["cheeks"]:
            for side in (-1, 1):
                ellipse(ctx, x + f + side * R * 0.5, y + R * 0.4, 20 * s, 12 * s, fill=self.L["blush"], line=None)
        ellipse(ctx, x + f, y + R * 0.33, 4 * s, 3 * s, fill="#e8977a", line=None)          # nose
        ey = y + R * 0.08
        for side in (-1, 1):
            cx = x + f + side * R * 0.36
            closed = blink or face == "closed" or (face == "wink" and side == 1) or face == "happy"
            if closed:
                ctx.move_to(cx - 22 * s, ey + 2 * s)
                ctx.curve_to(cx - 10 * s, ey + (12 if face == "happy" else 8) * s * (-1 if face == "happy" else 1),
                             cx + 10 * s, ey + (12 if face == "happy" else 8) * s * (-1 if face == "happy" else 1), cx + 22 * s, ey + 2 * s)
                ctx.set_source_rgb(*OUT)
                ctx.set_line_width(6 * s)
                ctx.stroke()
            else:
                ry = 33 * s if face != "annoyed" else 20 * s
                if face == "shock":
                    ry = 37 * s
                ellipse(ctx, cx, ey, 26 * s, ry, fill=(1, 1, 1), w=4 * s)
                ix, iy = cx + look[0] * 6 * s, ey + look[1] * 6 * s + (6 * s if face == "annoyed" else 0)
                ctx.save()
                ctx.translate(cx, ey)
                ctx.scale(26 * s, ry)
                ctx.arc(0, 0, 0.95, 0, 2 * math.pi)
                ctx.restore()
                ctx.clip()
                ellipse(ctx, ix, iy + 2 * s, 21 * s, 27 * s, fill=self.L["iris"], line=None)
                ellipse(ctx, ix, iy + 5 * s, 13 * s, 16 * s, fill=self.L["iris_dark"], line=None)
                ellipse(ctx, ix - 7 * s, iy - 9 * s, 7 * s, 7 * s, fill=(1, 1, 1), line=None)   # sparkles
                ellipse(ctx, ix + 7 * s, iy + 10 * s, 3.5 * s, 3.5 * s, fill=(1, 1, 1), line=None)
                ctx.reset_clip()
                # upper lid line + lashes on the outer corner
                ctx.move_to(cx - 28 * s, ey - ry * 0.15)
                ctx.curve_to(cx - 16 * s, ey - ry * 1.08, cx + 16 * s, ey - ry * 1.08, cx + 28 * s, ey - ry * 0.15)
                ctx.set_source_rgb(*OUT)
                ctx.set_line_width(9 * s)
                ctx.stroke()
                ox = cx + side * 26 * s
                for k in range(2 if self.L["lashes"] else 0):                          # two lash flicks
                    ctx.move_to(ox - side * k * 8 * s, ey - ry * 0.3 - k * 9 * s)
                    ctx.line_to(ox + side * (12 - k * 3) * s, ey - ry * 0.55 - k * 12 * s)
                    ctx.set_line_width(5 * s)
                    ctx.stroke()
                if face == "annoyed":                                              # heavy lid
                    poly(ctx, [(cx - 26 * s, ey - ry - 4 * s), (cx + 26 * s, ey - ry - 4 * s), (cx + 26 * s, ey - 2 * s),
                               (cx - 26 * s, ey - 2 * s)], fill=self.L["skin"], line=None)
                    curve(ctx, [(cx - 25 * s, ey - 2 * s), (cx + 25 * s, ey - 2 * s)], w=6 * s)
            # thick brows (her thing)
            by = ey - 50 * s
            lift = {"shock": -12, "sad": -4, "annoyed": 8, "smug": 0}.get(face, 0) * s
            tilt_b = {"annoyed": 9, "sad": -9, "smug": 4 if side == 1 else -2}.get(face, 0) * s
            inner, outer = cx - side * 22 * s, cx + side * 24 * s
            ctx.move_to(inner, by + lift + tilt_b)
            ctx.curve_to(cx - side * 6 * s, by + lift - 10 * s, cx + side * 12 * s, by + lift - 10 * s, outer, by + lift + 2 * s)
            ctx.set_source_rgb(*rgb(self.L["brow"]))
            ctx.set_line_width(11 * s)
            ctx.set_line_cap(1)
            ctx.stroke()
        if self.L["glasses"]:
            for side in (-1, 1):
                ellipse(ctx, x + f + side * R * 0.36, ey, 36 * s, 36 * s, fill=None, line=OUT, w=6 * s)
            curve(ctx, [(x + f - R * 0.36 + 36 * s, ey - 4 * s), (x + f, ey - 10 * s), (x + f + R * 0.36 - 36 * s, ey - 4 * s)], w=6 * s)
        # mouth
        mx, my = x + f, y + R * 0.62
        if self.L["mustache"]:
            curve(ctx, [(mx - 30 * s, my - 4 * s), (mx - 14 * s, my - 22 * s), (mx, my - 14 * s), (mx + 14 * s, my - 22 * s),
                        (mx + 30 * s, my - 4 * s), (mx, my - 8 * s)], fill=self.L["hair"], line=OUT, w=4 * s, close=True)
        o = max(mouth, {"shock": 0.8}.get(face, 0))
        if o > 0.1:
            wd, hg = 18 * s * (1 + 0.3 * o), 6 * s + 26 * s * o
            curve(ctx, [(mx - wd, my - hg * .2), (mx, my - hg * .35), (mx + wd, my - hg * .2), (mx + wd * .7, my + hg * .6),
                        (mx, my + hg * .75), (mx - wd * .7, my + hg * .6)], fill="#7a1f2a", w=5 * s, close=True)
            ellipse(ctx, mx, my + hg * .45, wd * .5, hg * .2, fill=self.L["lips"], line=None)
        elif face in ("happy", "wink"):
            curve(ctx, [(mx - 20 * s, my - 4 * s), (mx - 8 * s, my + 12 * s), (mx + 8 * s, my + 12 * s), (mx + 20 * s, my - 4 * s)],
                  fill="#7a1f2a", w=5 * s, close=True)
        elif face == "smug":
            curve(ctx, [(mx - 16 * s, my + 2 * s), (mx + 4 * s, my + 8 * s), (mx + 20 * s, my - 6 * s)], line=rgb(self.L["lips"]), w=7 * s)
        elif face in ("annoyed", "sad"):
            curve(ctx, [(mx - 16 * s, my + 6 * s), (mx, my + 1 * s), (mx + 16 * s, my + 6 * s)], line=rgb(self.L["lips"]), w=7 * s)
        else:
            curve(ctx, [(mx - 16 * s, my), (mx, my + 7 * s), (mx + 16 * s, my)], line=rgb(self.L["lips"]), w=7 * s)
