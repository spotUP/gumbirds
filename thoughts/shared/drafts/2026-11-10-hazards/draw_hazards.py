#!/usr/bin/env python3
# Roofline bottom-hazard drafts: A spikes, B fire, C water (+ lurker sprite), D lava.
# Each hazard: one seamless 32x32 tile (2x2 Neo Geo 16x16 tiles), 4 loop frames, one palette (<= 15 colours).
# Explicit pixel placement only: hand-chosen shapes, hard cel steps, no ramps, no dither fields.
# Deterministic, no network. Run: python3.14 -I draw_hazards.py   (needs Pillow)
import os
from math import sin, pi, floor
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
SCENE = os.path.join(ROOT, 'thoughts', 'shared', 'drafts', '2026-11-10-flier', 'A_v5_scene_3x.png')
TW, TH, NF = 32, 32, 4
HAZ_Y = 192            # hazard tile top row in the 320x224 screen
BG = (20, 26, 66)      # building colour of the accepted scene, used behind sheet art


class Tile:
    def __init__(self):
        self.g = [[None] * TW for _ in range(TH)]

    def p(self, x, y, c):
        if 0 <= y < TH:
            self.g[y][x % TW] = c

    def get(self, x, y):
        return self.g[y][x % TW] if 0 <= y < TH else None


# ---------------------------------------------------------------- A: spikes
PAL_A = {
    'o': (12, 10, 26),    # outline
    'd': (62, 70, 128),   # steel shadow (cool)
    'm': (116, 132, 190), # steel mid
    'l': (170, 188, 228), # steel lit face
    'h': (236, 244, 255), # ridge highlight
    'w': (255, 255, 255), # glint
    'k': (26, 18, 30),    # stripe black
    'y': (248, 196, 40),  # stripe yellow
    'Y': (196, 108, 26),  # stripe yellow shade (hue shift to orange)
    'g': (78, 70, 110),   # rail top
    'b': (232, 150, 80),  # bolt
}
SPIKES = [(0, 14), (8, 9), (16, 14), (24, 9)]   # (left x, height); base row 21
# stepped cone, centre column 3, light from the upper left: widths per row from the tip down
SPIKE_W = {14: [1, 1, 1, 3, 3, 3, 3, 5, 5, 5, 5, 7, 7, 7],
           9: [1, 1, 3, 3, 3, 5, 5, 7, 7]}
SPIKE_ROW = {1: 'h', 3: 'lhm', 5: 'llhmd', 7: 'ollhmdo'}


def draw_spikes(f):
    t = Tile()
    for i, (x0, hh) in enumerate(SPIKES):
        top = 22 - hh
        widths = SPIKE_W[hh]
        for r, w in enumerate(widths):
            for k, c in enumerate(SPIKE_ROW[w]):
                t.p(x0 + 3 - w // 2 + k, top + r, c)
        # hand nicks on the lit face, a little wear
        t.p(x0 + 2, top + hh - 3, 'm')
        if i == f:   # travelling glint: 4-point star on this tip, ridge flashes
            gx = x0 + 3
            for (dx, dy) in ((0, 0), (0, -1), (-1, 1), (1, 1)):
                t.p(gx + dx, top + dy, 'w')
            for r in range(2, 6):
                t.p(gx, top + r, 'w')
        if i == (f + 3) % 4:   # fading after-glint one spike back
            t.p(x0 + 3, top, 'w')
    for x in range(TW):
        t.p(x, 22, 'o')
        t.p(x, 23, 'g')
        for y in range(24, 29):
            yel = ((x + y) // 4) % 2 == 0
            t.p(x, y, ('Y' if y == 28 else 'y') if yel else 'k')
        t.p(x, 29, 'o')
        t.p(x, 30, 'k')
        t.p(x, 31, 'o')
    for bx in (5, 21):
        t.p(bx, 30, 'b')
    return t


# ---------------------------------------------------------------- B: fire
PAL_B = {
    'o': (44, 8, 22),      # coal outline
    'D': (124, 16, 38),    # deep red flame edge
    'r': (218, 42, 40),    # red
    'O': (248, 116, 34),   # orange
    'Y': (255, 230, 104),  # yellow
    'w': (255, 252, 226),  # white-hot core
    'y': (255, 184, 50),   # spark
    'c': (30, 20, 36),     # coal dark
    'C': (70, 40, 56),     # coal mid
    'L': (122, 70, 74),    # coal lit top
}
FLAMES = [  # per frame: (centre x, height, base half width, tip lean)
    [(4, 22, 5, 2), (14, 15, 4, -2), (23, 26, 5, -1), (30, 12, 3, 1)],
    [(5, 25, 5, -1), (13, 19, 4, 1), (23, 20, 5, 2), (30, 16, 3, -1)],
    [(4, 18, 5, -2), (14, 24, 4, -1), (24, 23, 5, 1), (30, 13, 3, 2)],
    [(3, 24, 5, 1), (14, 17, 4, 2), (23, 25, 5, -2), (29, 15, 3, 0)],
]
WISPS = [[(14, 7)], [(22, 3), (30, 9)], [(5, 7)], [(14, 6), (29, 10)]]
SPARKS = [[(9, 6), (19, 1)], [(10, 3), (27, 7)], [(11, 1), (27, 4), (18, 10)], [(28, 1), (17, 7)]]
COALS = [(3, 29, 5, 3), (12, 28, 5, 3.5), (21, 29, 6, 3), (29, 28.5, 4, 3)]
CRACKS = [(4, 30), (5, 30), (6, 29), (13, 29), (14, 30), (22, 30), (23, 30), (24, 29), (29, 30), (30, 30), (10, 31), (18, 31)]
FBASE = 27


def tongue(cx, h, bw, lean, sh, sw):
    m = set()
    hh = h * sh
    if hh < 1:
        return m
    for y in range(FBASE - int(hh), FBASE + 1):
        t = (FBASE - y) / hh
        hw = bw * sw * sin(pi * (0.3 + 0.7 * t)) / 1.0
        xc = cx + lean * t * t
        for x in range(floor(xc - hw + 0.5), floor(xc + hw + 0.5)):
            m.add((x % TW, y))
    return m


def draw_fire(f):
    t = Tile()
    L = [set(), set(), set(), set()]
    for (cx, h, bw, lean) in FLAMES[f]:
        L[0] |= tongue(cx, h, bw, lean, 1.0, 1.0)
        L[1] |= tongue(cx, h, bw, lean * 0.8, 0.72, 0.62)
        L[2] |= tongue(cx, h, bw, lean * 0.5, 0.42, 0.38)
        L[3] |= tongue(cx, h, bw, 0, 0.16, 0.22)
    for (x, y) in L[0]:
        edge = any(((x + dx) % TW, y + dy) not in L[0] for dx, dy in ((1, 0), (-1, 0), (0, -1)))
        t.p(x, y, 'D' if edge else 'r')
    for (x, y) in L[1]:
        t.p(x, y, 'O')
    for (x, y) in L[2]:
        t.p(x, y, 'Y')
    for (x, y) in L[3]:
        t.p(x, y, 'w')
    for (x, y) in WISPS[f]:   # detached flame lick: 2x2 cluster, hot centre
        t.p(x, y, 'O'); t.p(x + 1, y, 'r'); t.p(x, y + 1, 'r'); t.p(x + 1, y + 1, 'D'); t.p(x, y - 1, 'D')
    for (x, y) in SPARKS[f]:
        t.p(x, y, 'y')
    # coal bed, drawn over the flame roots
    for x in range(TW):
        for y in (30, 31):
            t.p(x, y, 'c')
    for (cx, cy, rx, ry) in COALS:
        m = set()
        for y in range(24, 32):
            for xx in range(int(cx - rx) - 1, int(cx + rx) + 2):
                if ((xx + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2 <= 1:
                    m.add((xx, y))
        for (xx, y) in m:
            top = (xx, y - 1) not in m
            if top:
                c = 'o'
            elif (xx, y - 2) not in m and xx < cx + rx * 0.4:
                c = 'L'
            elif y >= cy + 1:
                c = 'c'
            else:
                c = 'C'
            t.p(xx, y, c)
    for i, (x, y) in enumerate(CRACKS):
        t.p(x, y, 'OrD'[(i + f) % 3])
    return t


# ---------------------------------------------------------------- C: water
PAL_C = {
    'o': (6, 10, 30),      # abyss
    'n': (12, 28, 74),     # deep navy
    'b': (20, 62, 136),    # blue
    'B': (36, 110, 192),   # light blue
    'c': (86, 182, 232),   # cyan skin
    'f': (196, 238, 252),  # foam
    'w': (252, 255, 255),  # foam white
    'e': (255, 220, 60),   # lurker eye
    'E': (240, 92, 40),    # lurker eye rim
    'k': (22, 30, 44),     # fin dark
    'g': (70, 84, 108),    # fin mid
    'G': (142, 158, 184),  # fin lit edge
}
SURF = [10, 10, 9, 9, 8, 8, 7, 6, 5, 4, 3, 3, 3, 4, 6, 8, 9, 10, 10, 10, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 10]
BTHK = [3, 3, 4, 4, 3, 2, 2, 3, 4, 5, 5, 4, 3, 3, 2, 2, 3, 3, 4, 4, 3, 3, 2, 2, 3, 4, 4, 3, 3, 2, 3, 3]
D2 = [19, 19, 20, 20, 21, 21, 20, 19, 19, 18, 18, 19, 20, 21, 22, 22, 21, 20, 20, 19, 19, 20, 21, 21, 20, 19, 18, 18, 19, 20, 20, 19]
D3 = [27, 27, 26, 26, 27, 28, 28, 27, 26, 26, 27, 28, 29, 29, 28, 27, 27, 28, 28, 27, 26, 26, 27, 28, 28, 27, 27, 26, 26, 27, 28, 28]
CURL = [(11, 2, 'f'), (12, 2, 'w'), (13, 2, 'w'), (14, 3, 'w'), (14, 4, 'f')]   # lip over the steep face
BACKFOAM = [(3, 1), (6, 2), (7, 2), (9, 1), (20, 1), (25, 2), (26, 2)]           # (u, depth under skin)
SHIMMER = [[(4, 16, 3, 'B'), (19, 14, 4, 'B'), (10, 24, 3, 'b'), (26, 23, 2, 'b')],
           [(6, 17, 2, 'B'), (21, 15, 3, 'B'), (12, 23, 4, 'b'), (28, 24, 3, 'b')]]


def draw_water(f):
    t = Tile()
    sh = 8 * f
    for x in range(TW):
        u = (x - sh) % TW
        s = SURF[u]
        d1 = s + 2 + BTHK[u]
        for y in range(s, TH):
            if y == s:
                c = 'w' if s <= 5 else 'f'
            elif y == s + 1:
                c = 'f' if s <= 5 else 'c'
            elif y <= d1:
                c = 'B'
            elif y <= D2[x]:
                c = 'b'
            elif y <= D3[x]:
                c = 'n'
            else:
                c = 'o'
            t.p(x, y, c)
        for (bu, dd) in BACKFOAM:
            if bu == u:
                t.p(x, s + dd, 'f')
    for (u, y, c) in CURL:
        t.p(u + sh, y, c)
    for (x, y, n, c) in SHIMMER[f % 2]:
        for i in range(n):
            if t.get(x + i, y) in ('b', 'n'):
                t.p(x + i, y, c)
    return t


def lurker(f):
    """Separate sprite (not tiled): fin cuts the surface, two eyes glow below. Coordinates relative to
    (fin left, rest water line). Same palette as the water tile."""
    px = {}
    bob = [0, -1, -1, 0][f]
    ext = [(2, 2), (2, 3), (2, 4), (3, 5), (3, 6), (3, 7), (3, 8), (2, 9), (1, 10), (0, 11), (0, 11)]
    for i, (a, b) in enumerate(ext):
        y = -9 + i + bob
        for x in range(a, b + 1):
            if x in (a, b) or i == 0:
                c = 'o'
            elif x == a + 1:
                c = 'G'
            elif x == b - 1:
                c = 'k'
            else:
                c = 'g'
            px[(x, y)] = c
    # foam wake at the waterline, alternating
    wake = [[(-2, 0, 'w'), (-1, -1, 'f'), (12, 0, 'f'), (13, 0, 'w')],
            [(-3, 0, 'f'), (-1, 0, 'w'), (12, -1, 'w'), (14, 0, 'f')]][f % 2]
    for (x, y, c) in wake:
        px[(x, y + bob)] = c
    # body shadow and eyes deep below
    for y in range(4, 14):
        for x in range(-8, 22):
            if ((x - 6) / 14) ** 2 + ((y - 8.5) / 4.6) ** 2 <= 1:
                px[(x, y)] = 'o'
    eye = 'e' if f != 3 else 'E'
    for ex in (1, 9):
        px[(ex, 7)] = 'E'; px[(ex + 1, 7)] = eye; px[(ex + 2, 7)] = 'E'
        px[(ex + 1, 8)] = 'E'
    return px


# ---------------------------------------------------------------- D: lava
PAL_D = {
    'o': (26, 8, 18),      # crust black
    'k': (64, 20, 32),     # crust dark
    'K': (108, 42, 44),    # crust mid
    'Q': (156, 78, 62),    # crust lit top (warm)
    'D': (126, 14, 32),    # deep lava
    'r': (208, 38, 30),    # red
    'O': (248, 110, 28),   # orange
    'y': (255, 192, 52),   # yellow
    'Y': (255, 246, 176),  # white-hot
}
LSURF = [0, 0, 1, 1, 1, 0, 0, -1, -1, -1, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0, -1, -1, -1, -1, 0, 0, 0, 1, 1, 0, 0]
O1 = [2, 2, 3, 3, 3, 2, 2, 3, 4, 4, 3, 3, 2, 2, 2, 3, 3, 4, 4, 3, 2, 2, 2, 3, 3, 4, 4, 3, 2, 2, 2, 2]
O2 = [17, 17, 18, 19, 19, 18, 17, 16, 16, 17, 18, 19, 20, 20, 19, 18, 18, 17, 16, 16, 17, 18, 19, 19, 18, 17, 17, 18, 19, 19, 18, 17]
STREAKS = [(2, 15, 5), (13, 18, 4), (22, 14, 6), (27, 21, 3), (6, 22, 4), (17, 25, 3), (0, 27, 3), (25, 28, 4)]
VEINS = [(9, 24, 5), (20, 21, 4), (29, 25, 4), (3, 29, 6), (14, 29, 5)]
PLATES = [(12, 21, 15, 2), (29, 33, 31, 1)]   # crust rafts: x from, x to, glowing crack x, rows above the surface
BUBBLES = [(8, 0), (24, 2)]   # (x, phase offset)
BUB = [
    [(-1, -1, 'O'), (0, -1, 'y'), (1, -1, 'O'), (0, 0, 'Y')],
    [(-1, -4, 'r'), (0, -4, 'r'), (1, -4, 'r'),
     (-2, -3, 'r'), (-1, -3, 'Y'), (0, -3, 'O'), (1, -3, 'O'), (2, -3, 'r'),
     (-3, -2, 'r'), (-2, -2, 'O'), (-1, -2, 'y'), (0, -2, 'O'), (1, -2, 'O'), (2, -2, 'O'), (3, -2, 'r'),
     (-3, -1, 'r'), (-2, -1, 'O'), (-1, -1, 'O'), (0, -1, 'O'), (1, -1, 'O'), (2, -1, 'O'), (3, -1, 'r'),
     (-1, 0, 'Y'), (0, 0, 'Y'), (1, 0, 'Y')],
    [(-3, -1, 'y'), (3, -1, 'y'), (-2, -1, 'O'), (2, -1, 'O'), (0, 0, 'Y'),
     (-2, -4, 'y'), (2, -5, 'y'), (0, -6, 'O'), (-3, -3, 'O'), (3, -3, 'O')],
    [(-4, 0, 'y'), (4, 0, 'y'), (-3, -7, 'O'), (3, -6, 'r'), (0, -9, 'r'), (-1, 0, 'Y'), (1, 0, 'Y')],
]
EMBERS = [[(12, 3), (30, 6)], [(12, 1), (31, 4), (19, 7)], [(19, 5), (3, 6)], [(19, 3), (3, 4), (12, 8)]]


def draw_lava(f):
    t = Tile()
    base = 10
    bob = [0, 0, 1, 1][f]
    for x in range(TW):
        s = base + LSURF[x] + (bob if 12 <= x <= 22 else 0)
        for y in range(s, TH):
            d = y - s
            if d == 0:
                c = 'y' if LSURF[x] <= 0 else 'O'
            elif d <= O1[x]:
                c = 'O'
            elif y <= O2[x]:
                c = 'r'
            else:
                c = 'D'
            t.p(x, y, c)
    hot = f % 2
    for i, (x, y, n) in enumerate(STREAKS):   # molten streaks, pulse between two states
        for k in range(n):
            mid = 0 < k < n - 1
            if (i + hot) % 2:
                c = 'Y' if mid else 'y'
            else:
                c = 'y' if mid else 'O'
            t.p(x + k, y, c)
    for (x, y, n) in VEINS:   # cooler veins in the deep
        for k in range(n):
            t.p(x + k, y + (k // 3), 'k' if 0 < k < n - 1 else 'D')
    # floating crust rafts: dark slabs with a lit top and one glowing crack, drift with the surface bob
    for (a, b, cr, hi) in PLATES:
        for x in range(a, b + 1):
            s = base + LSURF[x % TW] + bob
            edge = x in (a, b)
            if hi == 2 and a + 1 < x < b - 2:   # lumpy top, not a box
                t.p(x, s - 2, 'o')
            elif hi == 2 and not edge:
                t.p(x, s - 2, None)
            t.p(x, s - 1, 'o' if edge else 'Q')
            t.p(x, s, 'o' if edge else ('y' if x == cr else 'K'))
            t.p(x, s + 1, 'o' if edge else ('O' if x == cr else 'k'))
            if a < x < b:
                t.p(x, s + 2, 'o' if x != cr else 'r')
    for (bx, off) in BUBBLES:
        ph = (f + off) % 4
        s = base + LSURF[bx]
        for (dx, dy, c) in BUB[ph]:
            t.p(bx + dx, s + dy, c)
    for (x, y) in EMBERS[f]:
        t.p(x, y, 'y' if (x + f) % 2 else 'O')
    return t


# ---------------------------------------------------------------- render
OPTIONS = [
    ('A', 'SPIKES', PAL_A, draw_spikes),
    ('B', 'FIRE', PAL_B, draw_fire),
    ('C', 'WATER', PAL_C, draw_water),
    ('D', 'LAVA', PAL_D, draw_lava),
]


def tile_img(t, pal):
    im = Image.new('RGBA', (TW, TH), (0, 0, 0, 0))
    px = im.load()
    for y in range(TH):
        for x in range(TW):
            c = t.g[y][x]
            if c:
                px[x, y] = pal[c] + (255,)
    return im


def colours_used(frames, extra=()):
    used = set()
    for t in frames:
        for row in t.g:
            used |= {c for c in row if c}
    for d in extra:
        used |= set(d.values())
    return used


def put_lurker(im, ox, oy, f, pal):
    px = im.load()
    for (x, y), c in lurker(f).items():
        X, Y = ox + x, oy + y
        if not (0 <= X < im.width and 0 <= Y < im.height):
            continue
        if c == 'o' and y > 2:   # body shadow: only darkens water, never sky or foam
            if px[X, Y][:3] in (PAL_C['b'], PAL_C['n'], PAL_C['B']):
                px[X, Y] = pal['o'] + (255,)
            continue
        px[X, Y] = pal[c] + (255,)


def base_scene():
    im = Image.open(SCENE).convert('RGBA')
    s = im.resize((320, 224), Image.NEAREST)
    d = ImageDraw.Draw(s)
    d.rectangle((276, 6, 319, 46), fill=(8, 10, 28, 255))   # drop the old version tag box
    band = s.crop((0, 172, 320, 180))                         # building bodies below the islands
    for y in range(180, 224, 8):                              # extend the city down behind the hazard
        s.paste(band, (0, y))
    return s


def scene_frame(base, key, pal, fn, f):
    s = base.copy()
    ti = tile_img(fn(f), pal)
    for x in range(0, 320, TW):
        s.alpha_composite(ti, (x, HAZ_Y))
    if key == 'C':
        put_lurker(s, 112, HAZ_Y + 10, f, pal)
    return s


def main():
    try:
        font = ImageFont.load_default(size=9)
    except TypeError:
        font = ImageFont.load_default()
    base = base_scene()
    rows = []
    report = []
    for key, name, pal, fn in OPTIONS:
        frames = [fn(f) for f in range(NF)]
        extra = [lurker(f) for f in range(NF)] if key == 'C' else []
        used = colours_used(frames, extra)
        assert len(used) <= 15, (key, len(used))
        assert len({pal[c] for c in used}) == len(used), key
        report.append((key, name, len(used)))
        rows.append((key, name, pal, frames, len(used)))
        sc = scene_frame(base, key, pal, fn, 1)
        sc.convert('RGB').resize((960, 672), Image.NEAREST).save(os.path.join(HERE, f'scene_{key}_3x.png'))
        gif = []
        for f in range(NF):
            fr = scene_frame(base, key, pal, fn, f).crop((0, 150, 160, 224)).convert('RGB')
            gif.append(fr.resize((640, 296), Image.NEAREST))
        gif[0].save(os.path.join(HERE, f'anim_{key}_4x.gif'), save_all=True, append_images=gif[1:],
                    duration=125, loop=0, disposal=1, optimize=False)
    # sheet: per option one row; each frame shown as two tile repeats (64 px) so the seam is visible
    LW, GAP, LH, RH = 8, 8, 12, 32 + 12 + 10
    W = LW + NF * (64 + GAP) + 4 * (24 + 4) + 24
    H = 6 + len(rows) * RH
    sheet = Image.new('RGBA', (W, H), (34, 34, 40, 255))
    d = ImageDraw.Draw(sheet)
    for i, (key, name, pal, frames, n) in enumerate(rows):
        y0 = 6 + i * RH
        d.text((LW, y0), f'{key}  {name}   {n} colours, {NF} frames, 32x32 tile (2x2 of 16x16)', fill=(230, 230, 230), font=font)
        for f, t in enumerate(frames):
            x0 = LW + f * (64 + GAP)
            d.rectangle((x0, y0 + LH, x0 + 63, y0 + LH + 31), fill=BG + (255,))
            ti = tile_img(t, pal)
            sheet.alpha_composite(ti, (x0, y0 + LH))
            sheet.alpha_composite(ti, (x0 + 32, y0 + LH))
            d.text((x0, y0 + LH + 33), f'frame {f}', fill=(170, 170, 170), font=font)
        if key == 'C':
            lx = LW + NF * (64 + GAP) + 4
            d.text((lx, y0 + LH + 33), 'lurker sprite', fill=(170, 170, 170), font=font)
            for f in range(NF):
                cell = Image.new('RGBA', (24, 32), BG + (255,))
                cp = cell.load()
                for yy in range(14, 32):
                    for xx in range(24):
                        cp[xx, yy] = PAL_C['b'] + (255,) if yy < 26 else PAL_C['n'] + (255,)
                put_lurker(cell, 6, 14, f, PAL_C)
                sheet.alpha_composite(cell, (lx + f * 28, y0 + LH))
    sheet.save(os.path.join(HERE, 'hazards_sheet_1x.png'))
    sheet.resize((W * 4, H * 4), Image.NEAREST).save(os.path.join(HERE, 'hazards_sheet_4x.png'))
    for r in report:
        print('%s %-7s colours=%d' % r)


if __name__ == '__main__':
    main()
