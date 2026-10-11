"""Drawing kit for the cartoon skits: thick-outlined round-head stick characters with big expressive faces, and
flat, softly shaded painted rooms (gradients, cel shadows). Everything is drawn with cairo, 1080x1920."""
import math

import cairocffi as cairo

OUT = (0.09, 0.08, 0.10)
W, H = 1080, 1920


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def lin(ctx, x0, y0, x1, y1, stops):
    g = cairo.LinearGradient(x0, y0, x1, y1)
    for o, c in stops:
        g.add_color_stop_rgb(o, *(rgb(c) if isinstance(c, str) else c))
    return g


def rad(ctx, cx, cy, r, stops):
    g = cairo.RadialGradient(cx, cy, 0, cx, cy, r)
    for o, c, a in stops:
        g.add_color_stop_rgba(o, *(rgb(c) if isinstance(c, str) else c), a)
    return g


def poly(ctx, pts, fill=None, line=OUT, w=6, close=True):
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    if close:
        ctx.close_path()
    _paint(ctx, fill, line, w)


def rrect(ctx, x, y, w_, h_, r, fill=None, line=OUT, w=6):
    ctx.new_sub_path()
    ctx.arc(x + w_ - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w_ - r, y + h_ - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h_ - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    ctx.close_path()
    _paint(ctx, fill, line, w)


def ellipse(ctx, cx, cy, rx, ry, fill=None, line=OUT, w=6):
    ctx.save()
    ctx.translate(cx, cy)
    ctx.scale(rx, ry)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()
    _paint(ctx, fill, line, w)


def curve(ctx, pts, line=OUT, w=6, fill=None, close=False):
    """Smooth curve through points (Catmull-Rom)."""
    P = pts + ([pts[0], pts[1], pts[2]] if close else [])
    ctx.move_to(*P[0])
    for i in range(len(P) - 1 if not close else len(pts)):
        p0 = P[i - 1] if i > 0 else P[i]
        p1, p2 = P[i], P[i + 1]
        p3 = P[i + 2] if i + 2 < len(P) else p2
        ctx.curve_to(p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6,
                     p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6, *p2)
    if close:
        ctx.close_path()
    _paint(ctx, fill, line, w)


def _paint(ctx, fill, line, w):
    if fill is not None:
        ctx.set_source(fill) if isinstance(fill, cairo.Pattern) else ctx.set_source_rgb(*(rgb(fill) if isinstance(fill, str) else fill))
        ctx.fill_preserve() if line else ctx.fill()
    if line:
        ctx.set_source_rgb(*(rgb(line) if isinstance(line, str) else line))
        ctx.set_line_width(w)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.stroke()
    ctx.new_path()


# ------------------------------------------------------------------ characters
class Toon:
    """A round-head stick character. hair: 'bun' | 'buzz' | 'none'; head colour grey-ish like the reference style."""

    def __init__(self, x, floor, facing=1, head="#c9c9cc", hair="none", hair_col="#3b2a22", scale=1.0, outfit=None):
        self.x, self.floor, self.facing, self.head, self.hair = x, floor, facing, head, hair
        self.hair_col, self.s, self.outfit = hair_col, scale, outfit

    def neck_at(self, bob=0.0):
        s = self.s
        hip = (self.x, self.floor - 2 * 150 * s * 0.98 + bob)
        return (hip[0], hip[1] - 175 * s)

    def draw(self, ctx, arms=((10, 10), (10, 10)), legs=(6, 6), face="neutral", mouth=0.0, look=(0, 0), blink=False,
             tilt=0.0, bob=0.0, squash=1.0, hold=None, socks=(False, False), inside_out=False, before_head=None):
        s = self.s
        leg = 150 * s
        hip = (self.x, self.floor - 2 * leg * 0.98 + bob)
        neck = (hip[0] + tilt * 0.4, hip[1] - 175 * s * squash)
        R = 88 * s
        hc = (neck[0] + tilt, neck[1] - R * 0.92)
        lw = 9 * s
        # legs
        for side, a in ((-1, legs[0]), (1, legs[1])):
            ang = math.radians(a) * side
            knee = (hip[0] + math.sin(ang) * leg, hip[1] + math.cos(ang) * leg)
            foot = (knee[0] + math.sin(ang * 0.3) * leg, min(knee[1] + math.cos(ang * 0.3) * leg, self.floor))
            curve(ctx, [hip, knee, foot], w=lw)
            if socks[0 if side < 0 else 1]:              # a white sock instead of a shoe
                ellipse(ctx, foot[0] + 12 * s * self.facing, foot[1] - 7 * s, 20 * s, 10 * s, fill=(0.96, 0.96, 0.96), w=4 * s)
            else:
                ellipse(ctx, foot[0] + 16 * s * self.facing, foot[1] - 6 * s, 24 * s, 11 * s, fill=OUT, line=None)
        # body: a stick, or an outfit shape (a shirt) over it
        if self.outfit:
            top, col = neck[1] + 10 * s, self.outfit
            poly(ctx, [(neck[0] - 36 * s, top), (neck[0] + 36 * s, top), (hip[0] + 30 * s, hip[1] + 8 * s),
                       (hip[0] - 30 * s, hip[1] + 8 * s)], fill=col, w=6 * s)
            if inside_out:                                 # seams on the outside and the tag sticking out
                for dx in (-1, 1):
                    curve(ctx, [(neck[0] + dx * 30 * s, top + 6 * s), (hip[0] + dx * 25 * s, hip[1])], line=(1, 1, 1), w=2.5 * s)
                rrect(ctx, neck[0] - 9 * s, top - 2 * s, 18 * s, 16 * s, 3 * s, fill=(1, 1, 1), w=3 * s)
        else:
            curve(ctx, [neck, hip], w=lw)
        # arms
        sh = (neck[0], neck[1] + 34 * s)
        hands = []
        for side, (a1, a2) in ((-1, arms[0]), (1, arms[1])):
            u = math.radians(a1) * side
            el = (sh[0] + math.sin(u) * 95 * s, sh[1] + math.cos(u) * 95 * s)
            lo = u + math.radians(a2) * side
            hd = (el[0] + math.sin(lo) * 88 * s, el[1] + math.cos(lo) * 88 * s)
            curve(ctx, [sh, el, hd], w=lw)
            ellipse(ctx, hd[0], hd[1], 17 * s, 17 * s, fill=OUT, line=None)
            hands.append(hd)
        if hold:
            hold(ctx, hands)
        if before_head:
            before_head(ctx, neck)
        # hair behind (bun)
        if self.hair == "bun":
            ellipse(ctx, hc[0] - self.facing * 20 * s, hc[1] - R * 0.95, 34 * s, 30 * s, fill=self.hair_col, w=6 * s)
        # head: grey with a soft shade on one side, thick outline
        ellipse(ctx, hc[0], hc[1], R, R * 1.04, fill=rgb(self.head), w=7 * s)
        ctx.save()
        ctx.arc(hc[0], hc[1], R - 4, 0, 2 * math.pi)
        ctx.clip()
        ellipse(ctx, hc[0] - self.facing * R * 0.55, hc[1] + R * 0.1, R * 0.8, R * 1.2, fill=(0, 0, 0), line=None) \
            if False else None
        ctx.set_source_rgba(0, 0, 0, 0.10)
        ctx.arc(hc[0] - self.facing * R * 0.95, hc[1] + R * 0.25, R * 0.95, 0, 2 * math.pi)
        ctx.fill()
        ctx.restore()
        if self.hair == "bun":
            curve(ctx, [(hc[0] - R * 0.98, hc[1] - R * 0.05), (hc[0] - R * 0.7, hc[1] - R * 0.78), (hc[0], hc[1] - R * 1.06),
                        (hc[0] + R * 0.7, hc[1] - R * 0.78), (hc[0] + R * 0.98, hc[1] - R * 0.05),
                        (hc[0] + R * 0.55, hc[1] - R * 0.55), (hc[0] - R * 0.2, hc[1] - R * 0.62)], fill=self.hair_col,
                  w=6 * s, close=True)
        elif self.hair == "buzz":
            curve(ctx, [(hc[0] - R * 0.95, hc[1] - R * 0.3), (hc[0] - R * 0.6, hc[1] - R * 0.9), (hc[0], hc[1] - R * 1.06),
                        (hc[0] + R * 0.6, hc[1] - R * 0.9), (hc[0] + R * 0.95, hc[1] - R * 0.3), (hc[0], hc[1] - R * 0.62)],
                  fill=self.hair_col, w=6 * s, close=True)
        self.face(ctx, hc, R, face, mouth, look, blink)
        self.head_c, self.head_r, self.hands = hc, R, hands
        return hc, hands

    def face(self, ctx, hc, R, face, mouth, look, blink):
        s = self.s
        fx = self.facing * R * 0.12
        ex, ey = hc[0] + fx, hc[1] - R * 0.12
        big = face in ("shock", "scared")
        for side in (-1, 1):
            cx = ex + side * R * 0.33
            if blink or face in ("happy_closed",):
                curve(ctx, [(cx - 16 * s, ey + (0 if face != "happy_closed" else 4)), (cx, ey - (0 if face != "happy_closed" else 10) * s),
                            (cx + 16 * s, ey + (0 if face != "happy_closed" else 4))], w=6 * s)
                continue
            rx, ry = (26, 30) if big else (22, 26)
            if face in ("unimpressed", "sus"):
                ry = 14
            ellipse(ctx, cx, ey, rx * s, ry * s, fill=(1, 1, 1), w=5 * s)
            pr = (9 if big else 11) * s
            ellipse(ctx, cx + look[0] * 8 * s + self.facing * 3 * s, ey + look[1] * 8 * s + (4 * s if face in ("unimpressed", "sus") else 0),
                    pr, pr, fill=OUT, line=None)
            if face in ("unimpressed", "sus"):     # heavy lids
                poly(ctx, [(cx - 25 * s, ey - 16 * s), (cx + 25 * s, ey - 16 * s), (cx + 25 * s, ey - 2 * s), (cx - 25 * s, ey - 2 * s)],
                     fill=rgb(self.head), line=None)
                curve(ctx, [(cx - 24 * s, ey - 2 * s), (cx + 24 * s, ey - 2 * s)], w=6 * s)
            # brows
            by = ey - 42 * s
            if face in ("angry",):
                curve(ctx, [(cx - side * 26 * s, by - 8 * s), (cx + side * 20 * s, by + 10 * s)], w=9 * s)
            elif face in ("worried", "scared"):
                curve(ctx, [(cx - side * 24 * s, by + 8 * s), (cx + side * 20 * s, by - 8 * s)], w=8 * s)
            elif face in ("shock",):
                curve(ctx, [(cx - 20 * s, by - 14 * s), (cx, by - 22 * s), (cx + 20 * s, by - 14 * s)], w=8 * s)
            elif face in ("sus", "unimpressed"):
                curve(ctx, [(cx - 22 * s, by + 10 * s), (cx + 22 * s, by + 6 * s)], w=8 * s)
            else:
                curve(ctx, [(cx - 20 * s, by + 2 * s), (cx, by - 6 * s), (cx + 20 * s, by + 2 * s)], w=7 * s)
        # mouth
        mx, my = hc[0] + fx * 1.2, hc[1] + R * 0.5
        o = max(mouth, {"shock": .9, "scared": .6, "angry": .45}.get(face, 0))
        if o > 0.1:
            wdt, hgt = 34 * s * (1 + .2 * o), 12 * s + 34 * s * o
            curve(ctx, [(mx - wdt, my - hgt * .25), (mx, my - hgt * .45), (mx + wdt, my - hgt * .25), (mx + wdt * .7, my + hgt * .55),
                        (mx, my + hgt * .7), (mx - wdt * .7, my + hgt * .55)], fill="#3a1216", w=6 * s, close=True)
            if face in ("angry", "scared", "shock") or o > .5:          # teeth
                ctx.save()
                curve(ctx, [(mx - wdt, my - hgt * .25), (mx, my - hgt * .45), (mx + wdt, my - hgt * .25), (mx + wdt * .7, my + hgt * .55),
                            (mx, my + hgt * .7), (mx - wdt * .7, my + hgt * .55)], line=None, close=True)
                ctx.restore()
                rrect(ctx, mx - wdt * .75, my - hgt * .38, wdt * 1.5, hgt * .28, 4 * s, fill=(1, 1, 1), line=None)
            ellipse(ctx, mx, my + hgt * .45, wdt * .45, hgt * .18, fill="#d9606a", line=None)
        elif face in ("happy", "happy_closed", "smug"):
            curve(ctx, [(mx - 30 * s, my - 6 * s), (mx + (8 if face == "smug" else 0) * s, my + 16 * s), (mx + 30 * s, my - 10 * s)], w=7 * s)
        elif face in ("worried", "sus", "unimpressed"):
            curve(ctx, [(mx - 24 * s, my + 4 * s), (mx - 8 * s, my - 2 * s), (mx + 8 * s, my + 4 * s), (mx + 24 * s, my - 2 * s)], w=7 * s)
        else:
            curve(ctx, [(mx - 22 * s, my + 2 * s), (mx + 22 * s, my + 2 * s)], w=7 * s)


# ------------------------------------------------------------------ fonts (cairocffi has no TTF loader: go via FreeType)
_FACES = {}


def font_face(path_):
    if path_ in _FACES:
        return _FACES[path_]
    import cffi
    ffi = cffi.FFI()
    ffi.cdef("""typedef void* FT_Library; typedef void* FT_Face; int FT_Init_FreeType(FT_Library*);
                int FT_New_Face(FT_Library, const char*, long, FT_Face*);
                void* cairo_ft_font_face_create_for_ft_face(FT_Face, int);""")
    ft, cft = ffi.dlopen("freetype"), ffi.dlopen("cairo")
    lib, face = ffi.new("FT_Library*"), ffi.new("FT_Face*")
    ft.FT_Init_FreeType(lib)
    ft.FT_New_Face(lib[0], path_.encode(), 0, face)
    ptr = cft.cairo_ft_font_face_create_for_ft_face(face[0], 0)
    ff = cairo.FontFace._from_pointer(cairo.ffi.cast("cairo_font_face_t *", ptr), incref=False)
    _FACES[path_] = (ff, (ffi, ft, cft, lib, face))
    return _FACES[path_]


def text(ctx, s, x, y, size, font, col=OUT, anchor="mm", outline=None, ow=8):
    ctx.save()
    ctx.set_font_face(font_face(font)[0])
    ctx.set_font_size(size)
    xb, yb, tw, th, _, _ = ctx.text_extents(s)
    dx = {"l": 0, "m": -tw / 2, "r": -tw}[anchor[0]] - xb
    dy = {"t": -yb, "m": -yb - th / 2, "b": -yb - th}[anchor[1]]
    ctx.move_to(x + dx, y + dy)
    ctx.text_path(s)
    if outline:
        ctx.set_source_rgb(*outline)
        ctx.set_line_width(ow)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.stroke_preserve()
    ctx.set_source_rgb(*(rgb(col) if isinstance(col, str) else col))
    ctx.fill()
    ctx.restore()
    return tw
