#!/usr/bin/env python3
"""Final island sheets and the staggered layout proposal for Gumbirds.

Derived from thoughts/shared/drafts/2026-11-10-islands/draw_islands.py (same helpers and
measurements, new art, new box). Run make_backdrops.py once first, then this script:

    /opt/homebrew/bin/python3.14 -I make_backdrops.py
    /opt/homebrew/bin/python3.14 -I draw_islands_final.py

Every island is built from 16 px wide pieces: a left cap, a run of middle pieces taken from a
pool of five different ones, and a right cap. A piece is one tile tall (16 px, "thin") or two
tiles tall (32 px, "tall"). The standing line is sheet row 4 in every piece.
"""
import os
from math import sin, cos, pi, ceil

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SOOT = os.path.join(HERE, '..', '2026-11-10-sootling-final')
TRANSP = (255, 0, 255)
LINE = 4                      # sheet row of the standing line = collision height
WIDTHS = (64, 80, 96, 112, 48)  # 48 last: indices and sheet rows of the other widths stay
SEQ = {64: (0, 3), 80: (0, 2, 4), 96: (0, 1, 3, 4), 112: (0, 1, 2, 3, 4), 48: (0,)}
FRAMES, MS = 8, 110
KINDS = ('L', 0, 1, 2, 3, 4, 'R')

# One line per look for the gallery: the weakest point that is still in the art.
WEAK = {
    'roof': 'The thin variant shows only one brick course, so the torn underside and the lanterns shrink to a few pixels; the brick body is still close in value to the lit city windows behind it.',
    'garden': 'The soil is dark and sits near the dusk skyline in value, so the island reads mostly through its turf line and orange rim; the vines of the thin variant move in only 3 distinct frames.',
    'deck': 'The rotors are still thin two-pixel blades and read as antennae at 1x; the hull is a plain trapezoid and one palette entry (y1) is unused.',
}

LOOKS = {
    'roof': dict(mood='moon', title='A roof chunk (moon night)', rim='i2', pal=[
        ('k', (16, 8, 33)), ('s1', (49, 41, 82)), ('s2', (90, 82, 123)), ('s3', (148, 140, 165)),
        ('s4', (206, 198, 198)), ('s5', (255, 247, 222)), ('b1', (57, 16, 49)), ('b2', (99, 33, 57)),
        ('b3', (156, 57, 57)), ('b4', (206, 99, 66)), ('b5', (247, 156, 99)), ('i1', (41, 49, 74)),
        ('i2', (148, 181, 222)), ('g1', (255, 165, 41)), ('g2', (255, 247, 165))]),
    'garden': dict(mood='dusk', title='B garden slab (ember dusk)', rim='o1', pal=[
        ('k', (16, 8, 33)), ('o1', (255, 173, 82)), ('d2', (57, 24, 66)), ('d3', (107, 49, 74)),
        ('d4', (173, 99, 82)), ('t1', (165, 132, 148)), ('t2', (247, 222, 206)), ('g1', (16, 57, 57)),
        ('g2', (33, 99, 57)), ('g3', (90, 148, 49)), ('g4', (173, 206, 66)), ('g5', (247, 247, 140)),
        ('f1', (132, 222, 231)), ('f2', (239, 255, 255)), ('rt', (231, 181, 132))]),
    'deck': dict(mood='storm', title='C airship deck (storm)', rim='c3', pal=[
        ('k', (8, 8, 16)), ('m1', (24, 24, 33)), ('m2', (57, 57, 74)), ('m3', (107, 107, 115)),
        ('m4', (165, 165, 165)), ('m5', (222, 222, 214)), ('m6', (255, 255, 255)), ('y1', (140, 41, 24)),
        ('y2', (247, 115, 24)), ('y3', (255, 198, 90)), ('c1', (16, 82, 99)), ('c2', (41, 173, 181)),
        ('c3', (132, 231, 231)), ('r1', (99, 57, 41)), ('r2', (181, 115, 66))]),
}

# Proposed layout: (x, y, width, tall). Stage table today: see TABLE.
TABLE = [(0, 164, 80), (304, 164, 80), (136, 140, 112), (32, 104, 80), (280, 104, 80),
         (144, 72, 96), (0, 40, 56), (328, 40, 56)]
PROPOSAL = [(0, 148, 80, 1), (304, 164, 80, 1), (136, 128, 112, 1), (32, 92, 80, 1),
            (280, 108, 80, 1), (144, 68, 96, 1), (0, 36, 64, 1), (320, 52, 64, 1)]


# ---------------------------------------------------------------- helpers

def q5(c):
    return tuple(((v >> 3) << 3) | (v >> 5) for v in c)


def lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def up(a, s):
    return np.repeat(np.repeat(a, s, 0), s, 1)


def pal_rgb(look):
    return [q5(c) for _, c in LOOKS[look]['pal']]


def idx(look):
    return {n: i + 1 for i, (n, _) in enumerate(LOOKS[look]['pal'])}


def to_rgb(a, look):
    lut = np.array([TRANSP] + pal_rgb(look), np.uint8)
    return lut[a]


def blit(dst, a, look, x, y, wrap=False):
    """Paste a role-index sprite into an RGB array, clipped; wrap pastes a second copy across the seam."""
    h, w = a.shape
    rgb = to_rgb(a, look)
    xs = [x, x - dst.shape[1], x + dst.shape[1]] if wrap else [x]
    for px in xs:
        x0, y0, x1, y1 = max(px, 0), max(y, 0), min(px + w, dst.shape[1]), min(y + h, dst.shape[0])
        if x0 >= x1 or y0 >= y1:
            continue
        sub = a[y0 - y:y1 - y, x0 - px:x1 - px]
        dst[y0:y1, x0:x1][sub > 0] = rgb[y0 - y:y1 - y, x0 - px:x1 - px][sub > 0]


def blit_rgb(dst, src, x, y, flip=False):
    if flip:
        src = src[:, ::-1]
    h, w = src.shape[:2]
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, dst.shape[1]), min(y + h, dst.shape[0])
    if x0 >= x1 or y0 >= y1:
        return
    sub = src[y0 - y:y1 - y, x0 - x:x1 - x]
    m = ~(sub == np.array(TRANSP, np.uint8)).all(2)
    dst[y0:y1, x0:x1][m] = sub[m]


def save_png(path, rgb, scale=1):
    Image.fromarray(up(rgb, scale) if scale > 1 else rgb, 'RGB').save(os.path.join(HERE, path))


def save_gif(path, frs, ms, scale=3):
    packed = [(fr[..., 0].astype(np.uint32) << 16) | (fr[..., 1].astype(np.uint32) << 8) | fr[..., 2] for fr in frs]
    cols = np.unique(np.concatenate([np.unique(p) for p in packed]))
    assert len(cols) <= 256, len(cols)
    pal = []
    for c in cols:
        pal += [int(c >> 16) & 255, int(c >> 8) & 255, int(c) & 255]
    pal += [0] * (768 - len(pal))
    ims = []
    for p in packed:
        im = Image.fromarray(up(np.searchsorted(cols, p).astype(np.uint8), scale), 'P')
        im.putpalette(pal)
        ims.append(im)
    ims[0].save(os.path.join(HERE, path), save_all=True, append_images=ims[1:], duration=ms, loop=0, optimize=False)


class Cv:
    """A 16 px wide piece of role indices; out-of-range writes are dropped."""

    def __init__(self, look, h):
        self.a = np.zeros((h, 16), np.uint8)
        self.h = h
        self.ix = idx(look)

    def px(self, x, y, c):
        if 0 <= x < 16 and 0 <= y < self.h:
            self.a[y, x] = self.ix[c]

    def rect(self, x0, y0, x1, y1, c):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.px(x, y, c)

    def get(self, x, y):
        return self.a[y, x] if 0 <= x < 16 and 0 <= y < self.h else 0


# ---------------------------------------------------------------- lower edge profiles
# Rim row per column. Middle pieces give an offset from the base row (20 tall, 11 thin) and are 0 on
# both outer columns, so any two pieces join. Cap pieces give the rows directly.

MID = {
    'roof': [[0, 0, 0, 3, 3, 3, 3, 1, 1, 1, 1, 1, -1, -1, 0, 0],
             [0, 0, 2, 2, 2, 2, 2, 2, -2, -2, -2, -2, 0, 0, 0, 0],
             [0, 1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 0, 0, 0, 0, 0],
             [0, 0, -1, -1, -1, -1, 2, 2, 2, 2, 5, 5, 5, 1, 1, 0],
             [0, 0, 0, 0, 2, 2, 2, 2, 2, -2, -2, -2, -2, 1, 1, 0]],
    'garden': [[0, 0, 1, 1, 2, 3, 3, 2, 2, 1, 1, 2, 1, 0, 0, 0],
               [0, 1, 1, 0, 0, -1, -1, 0, 1, 2, 3, 4, 3, 1, 0, 0],
               [0, 0, -1, -1, -2, -1, 0, 0, 1, 1, 2, 2, 1, 1, 0, 0],
               [0, 1, 2, 2, 3, 5, 4, 2, 1, 0, 0, -1, -1, 0, 0, 0],
               [0, 0, 1, 2, 1, 1, 0, -1, -2, -2, -1, 0, 1, 1, 0, 0]],
    'deck': [[0, 0, 0, 0, 2, 2, 2, 2, 2, 2, 2, 2, 0, 0, 0, 0],
             [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0],
             [0, 0, 0, 0, 0, 3, 3, 3, 3, 3, 3, 0, 0, 0, 0, 0],
             [0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0],
             [0, 0, 0, 0, 0, 0, 2, 2, 2, 2, 2, 2, 2, 2, 0, 0]],
}
_DL = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 20, 20, 20, 20, 20]
_DT = [8, 8, 9, 9, 10, 10, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11]
CAP = {
    ('roof', 'L', 2): [9, 9, 12, 12, 12, 15, 15, 15, 17, 17, 17, 17, 20, 20, 20, 20],
    ('roof', 'R', 2): [20, 20, 20, 22, 22, 22, 18, 18, 18, 18, 15, 15, 12, 12, 10, 10],
    ('roof', 'L', 1): [8, 8, 9, 9, 9, 11, 11, 11, 12, 12, 12, 11, 11, 11, 11, 11],
    ('roof', 'R', 1): [11, 11, 11, 12, 12, 12, 11, 11, 10, 10, 10, 9, 9, 9, 8, 8],
    ('garden', 'L', 2): [9, 11, 13, 14, 15, 16, 17, 17, 18, 19, 19, 19, 20, 20, 20, 20],
    ('garden', 'R', 2): [20, 20, 21, 20, 20, 19, 18, 18, 18, 16, 15, 15, 13, 11, 10, 8],
    ('garden', 'L', 1): [8, 9, 10, 10, 11, 11, 11, 11, 11, 12, 12, 11, 11, 11, 11, 11],
    ('garden', 'R', 1): [11, 11, 11, 12, 12, 11, 11, 11, 11, 11, 10, 10, 10, 9, 9, 8],
    ('deck', 'L', 2): _DL, ('deck', 'R', 2): _DL[::-1],
    ('deck', 'L', 1): _DT, ('deck', 'R', 1): _DT[::-1],
}


def rim_rows(look, kind, tall):
    if kind in ('L', 'R'):
        return CAP[(look, kind, tall)]
    d = MID[look][kind]
    if tall == 2:
        return [20 + v for v in d]
    return [11 + max(-1, min(3, int(round(v / 2.0)))) for v in d]


def shell(cv, look, kind, tall, fill):
    """Body from row 6 down to the rim: fill colours, dark keyline, then the glow rim as the lowest pixel."""
    rr = rim_rows(look, kind, tall)
    for x in range(16):
        for y in range(6, rr[x] - 1):
            cv.px(x, y, fill(x, y))
        cv.px(x, rr[x] - 1, 'k')
    for x in range(16):                      # exposed step sides get the keyline too
        for y in range(7, rr[x] - 1):
            for nx in (x - 1, x + 1):
                if 0 <= nx < 16 and cv.get(nx, y) == 0:
                    cv.px(x, y, 'k')
    for x in range(16):
        cv.px(x, rr[x], LOOKS[look]['rim'])
    return rr


def swing(f, phase):
    return sin(2 * pi * f / FRAMES + phase)


# ---------------------------------------------------------------- A roof chunk

ROOF_TONE = {(0, 0, 0): 0, (0, 0, 1): 2, (0, 1, 0): 2, (1, 0, 0): 2, (1, 1, 0): 0, (2, 0, 0): 2, (2, 0, 1): 2,
             (2, 1, 0): 1, (3, 0, 0): 0, (3, 0, 1): 2, (3, 1, 0): 2, (4, 0, 0): 1, (4, 0, 1): 2, (4, 1, 0): 0,
             (0, 2, 1): 1, (2, 2, 0): 1, (3, 3, 0): 1, (4, 2, 1): 1, (1, 3, 0): 1,
             ('L', 0, 1): 2, ('L', 1, 0): 1, ('R', 2, 0): 0, ('R', 1, 0): 2}
ROOF_HOLE = {(1, 2, 1), (4, 3, 0), ('L', 2, 1)}
ROOF_JOINT = {'L': 9, 0: 5, 1: 12, 2: 3, 3: 10, 4: 7, 'R': 6}
ROOF_REBAR = {1: (9, 3), 3: (4, 2), 4: (11, 3)}
BRICK = {2: ('b5', 'b4', 'b3'), 1: ('b4', 'b3', 'b2'), 0: ('b3', 'b2', 'b2')}


def roof_piece(kind, tall, f):
    cv = Cv('roof', 16 * tall)

    def fill(x, y):
        if y == 6:
            return 's1' if x == ROOF_JOINT[kind] else 's3'
        if y == 7:
            return 'k'
        if kind == 'L' and x < 2:
            return ('s1', 's2')[x]
        if kind == 'R' and x > 13:
            return ('s3', 's4')[x - 14]
        c, ry = divmod(y - 8, 4)
        off = 4 if c % 2 else 0
        bx, slot = (x - off) % 8, ((x - off) % 16) // 8
        if ry == 3 or bx == 7:
            return 'b1'
        whole = not (c % 2 and slot == 1)
        if whole and (kind, c, slot) in ROOF_HOLE:
            return 'b1' if ry == 0 or bx == 0 else 'k'
        base = 1 if c < 2 else 0
        if kind == 'R':
            base = 2 if c == 0 else 1
        if kind == 'L':
            base = 1 if c == 0 else 0
        tone = ROOF_TONE.get((kind, c, slot), base) if whole else base
        return BRICK[tone][0] if (bx == 6 and ry > 0) else BRICK[tone][ry]

    rr = shell(cv, 'roof', kind, tall, fill)
    cv.rect(0, LINE, 15, LINE, 's5')
    cv.rect(0, LINE + 1, 15, LINE + 1, 's4')
    if kind in ROOF_REBAR:
        x, n = ROOF_REBAR[kind]
        n = n if tall == 2 else 1
        for i in range(n):
            cv.px(x, rr[x] + 1 + i, 'i2' if i == n - 1 else 'i1')
    if kind == 'L':                          # aerial: thin verticals only, nothing to stand on
        cv.rect(3, 0, 3, 3, 'i1')
        cv.px(3, 0, 'i2')
        cv.px(2, 1, 'i1')
        cv.px(4, 1, 'i1')
    if kind == 'R':                          # vent pipe
        cv.rect(12, 1, 12, 3, 's2')
        cv.rect(11, 2, 11, 3, 's1')
    if kind in ('L', 'R'):                   # lantern on a chain, a pendulum
        px = (6 if kind == 'L' else 9) if tall == 2 else (5 if kind == 'L' else 10)
        th = swing(f, 0.0 if kind == 'L' else pi / 2)
        py = rr[px] + 1
        if tall == 2:
            ang = 0.42 * th
            cx = px + int(round(7 * sin(ang)))
            top = py + int(round(5 * cos(ang)))
            n = top - py
            for i in range(n):
                cv.px(px + int(round((cx - px) * (i + 0.5) / n)), py + i, 'i2' if i % 2 == 0 else 'i1')
            cv.rect(cx - 1, top, cx + 1, top, 'i1')
            for r in (1, 2, 3):
                cv.px(cx - 2, top + r, 'i2')
                cv.px(cx + 2, top + r, 'i2')
                cv.rect(cx - 1, top + r, cx + 1, top + r, 'g1')
                cv.px(cx, top + r, 'g2')
            cv.rect(cx - 1, top + 2, cx + 1, top + 2, 'g2')
            cv.rect(cx - 1, top + 4, cx + 1, top + 4, 'g1')
        else:
            cx = px + int(round(1.3 * th))
            for y in range(py, 13):
                cv.px(px, y, 'i2')
            cv.rect(cx - 1, 13, cx + 1, 13, 'i1')
            cv.rect(cx - 1, 14, cx + 1, 14, 'g1')
            cv.px(cx, 14, 'g2')
            cv.px(cx, 15, 'g1')
    return cv.a


# ---------------------------------------------------------------- B garden slab

G_LIT = {'L': [(4, 7), (5, 7), (10, 8), (11, 8), (12, 8)],
         0: [(1, 7), (2, 7), (3, 8), (9, 7), (13, 8), (14, 8)],
         1: [(5, 7), (6, 7), (7, 7), (6, 8), (12, 8)],
         2: [(2, 8), (3, 8), (8, 7), (9, 7), (10, 7), (14, 7)],
         3: [(4, 8), (11, 7), (12, 7), (13, 8)],
         4: [(1, 8), (2, 8), (7, 7), (8, 7), (8, 8), (14, 7)],
         'R': [(3, 7), (4, 7), (9, 8), (10, 8), (13, 7), (14, 8), (14, 9), (15, 7)]}
G_BLOB = {0: [(9, 10, 12, 11, 'd3')], 1: [(1, 11, 3, 12, 'd2')],
          2: [(9, 10, 13, 11, 'd2'), (2, 12, 4, 13, 'd3')], 3: [(5, 12, 7, 13, 'd2')],
          4: [(11, 10, 14, 11, 'd3'), (1, 12, 3, 13, 'd2')], 'L': [(9, 12, 11, 13, 'd2')], 'R': [(2, 12, 5, 13, 'd3')]}
G_FLECK = {0: [(4, 15), (5, 15), (11, 16)], 1: [(2, 14), (9, 16), (10, 16)], 2: [(5, 16), (12, 14), (13, 14)],
           3: [(3, 15), (7, 17), (8, 17), (12, 16)], 4: [(4, 14), (10, 15), (11, 15)], 'L': [(12, 15), (13, 16)],
           'R': [(1, 15), (2, 16), (5, 14)]}
G_STONE = {2: {0: [(3, 10, 7, 4)], 1: [(10, 8, 3, 2), (4, 12, 4, 3)], 2: [(6, 13, 2, 2)], 3: [(9, 11, 5, 3), (2, 8, 2, 2)],
               4: [(5, 9, 3, 3), (11, 13, 3, 2)], 'L': [(9, 9, 4, 3)], 'R': [(3, 10, 3, 2)]},
           1: {0: [(4, 7, 4, 2)], 1: [(11, 7, 2, 2)], 3: [(8, 7, 3, 2)], 4: [(2, 7, 2, 2)]}}
G_ROOTLINE = [(2, 9), (3, 9), (4, 10), (5, 10), (6, 10), (7, 11), (8, 11), (9, 12)]
G_ROOT = {2: {0: (6, 3), 2: (11, 4), 3: (5, 3), 4: (9, 2), 1: (3, 2)}, 1: {0: (6, 1), 2: (11, 2), 3: (5, 1)}}
G_TURFDROP = {'L': (3, 8, 13), 0: (2, 7, 11), 1: (4, 9, 14), 2: (1, 6, 12), 3: (3, 10, 13), 4: (5, 8, 12), 'R': (2, 7, 11)}
G_BLADE = {'L': [(1, 2), (6, 3), (7, 1), (11, 1)], 0: [(2, 2), (3, 1), (9, 3), (13, 1)], 1: [(5, 1), (6, 2), (12, 1)],
           2: [(1, 1), (7, 2), (8, 3), (14, 2)], 3: [(4, 3), (10, 1), (11, 2)], 4: [(3, 1), (6, 1), (12, 3), (13, 2)],
           'R': [(4, 1), (9, 2), (10, 3), (14, 1)]}
G_BLOSSOM = {0: (9, 'f2'), 2: (8, 'f1'), 3: (4, 'f2'), 4: (12, 'f1'), 'L': (6, 'f1'), 'R': (10, 'f2')}
G_VINE = {('L', 2): [(3, 12, 0.0), (7, 10, 1.3)], ('R', 2): [(8, 9, 2.1), (12, 13, 0.7)],
          ('L', 1): [(3, 3, 0.0), (7, 2, 1.3)], ('R', 1): [(8, 2, 2.1), (12, 4, 0.7)]}


def garden_piece(kind, tall, f):
    cv = Cv('garden', 16 * tall)
    lit = set(G_LIT[kind])

    def fill(x, y):
        if y == 6:
            return 'g1' if x in G_TURFDROP[kind] else 'g2'
        if y == 7 and x in G_TURFDROP[kind]:
            return 'g2'
        if (x, y) in lit:
            return 'd4'
        if tall == 1:
            if y <= 8:
                return 'd3'
            return ('d3' if (x + y) % 2 == 0 else 'd2') if y <= 10 else 'd2'
        if y <= 9:
            return 'd3'
        if y <= 13:
            for x0, y0, x1, y1, c in G_BLOB.get(kind, []):
                if x0 <= x <= x1 and y0 <= y <= y1:
                    return c
            return 'd3' if (x + y) % 2 == 0 else 'd2'
        return 'd3' if (x, y) in G_FLECK.get(kind, []) else 'd2'

    rr = shell(cv, 'garden', kind, tall, fill)
    for x, y, w, h in G_STONE[tall].get(kind, []):
        for j in range(h):
            for i in range(w):
                corner = w >= 3 and h >= 3 and (i in (0, w - 1)) and (j in (0, h - 1))
                if corner:
                    continue
                c = 't2' if (j == 0 or (i == w - 1 and j < h - 1)) else 't1'
                cv.px(x + i, y + j, c)
        for i in range(w - 1):
            if y + h < rr[x + i] - 1:
                cv.px(x + i, y + h, 'k')
    if kind == 2 and tall == 2:
        for x, y in G_ROOTLINE:
            cv.px(x, y, 'rt')
            cv.px(x, y + 1, 'k')
    if kind in G_ROOT[tall]:
        x, n = G_ROOT[tall][kind]
        for i in range(n):
            cv.px(x + (1 if i >= 2 else 0), rr[x] + 1 + i, 'rt')
    cv.rect(0, LINE, 15, LINE, 'g5')
    cv.rect(0, LINE + 1, 15, LINE + 1, 'g4')
    for x, h in G_BLADE[kind]:               # grass: single-pixel blades, darker than the line
        for i in range(h):
            cv.px(x, LINE - 1 - i, 'g3' if i == h - 1 else 'g2')
    if kind in G_BLOSSOM:
        x, c = G_BLOSSOM[kind]
        h = dict(G_BLADE[kind])[x]
        cv.px(x, LINE - h, c)
    for x, n, ph in G_VINE.get((kind, tall), []):   # vines: fixed at the root, wave travels to the tip
        for d in range(n):
            dx = int(round(min(d / 4.0, 2.0) * sin(2 * pi * f / FRAMES - 0.6 * d + ph)))
            y = rr[x] + 1 + d
            cv.px(x + dx, y, 'g5' if d == n - 1 else ('g3' if d % 2 == 0 else 'g2'))
            if d % 3 == 1 and d < n - 1:
                cv.px(x + dx + (1 if (d // 3) % 2 == 0 else -1), y, 'g4')
    return cv.a


# ---------------------------------------------------------------- C airship deck

D_RUST = {11: (5, 8), 12: (4, 10), 13: (3, 11), 14: (4, 11), 15: (5, 9), 16: (6, 8)}


def deck_piece(kind, tall, f):
    cv = Cv('deck', 16 * tall)
    band = 3 if tall == 2 else 2

    def fill(x, y):
        if y < 6 + band:
            if (x + (y - 6)) % 8 < 4:
                return 'y3' if y == 6 else 'y2'
            return 'k'
        if kind == 'L' and x == 0:
            return 'm2'
        if kind == 'R' and x == 15:
            return 'm5'
        if tall == 2:
            if y == 9:
                return 'm1'
            if y == 10:
                return 'm4'
            return 'm3' if y <= 14 else 'm2'
        return 'm4' if y == 8 else ('m3' if y == 9 else 'm2')

    rr = shell(cv, 'deck', kind, tall, fill)
    cv.rect(0, LINE, 15, LINE, 'm6')
    cv.rect(0, LINE + 1, 15, LINE + 1, 'm5')

    def rivet(x, y):
        cv.px(x, y, 'm5')
        cv.px(x, y + 1, 'm1')

    if tall == 2:
        if kind == 0:
            for p in ((2, 12), (13, 12), (2, 16), (13, 16)):
                rivet(*p)
            cv.rect(8, 10, 8, 20, 'm1')
        if kind == 1:
            for y in range(10, 16):
                for x in range(5, 11):
                    if (x in (5, 10)) and (y in (10, 15)):
                        continue
                    edge = x in (5, 10) or y in (10, 15)
                    cv.px(x, y, 'm1' if edge else 'c2')
            cv.px(6, 14, 'c1')
            cv.px(7, 14, 'c1')
            cv.px(6, 13, 'c1')
            cv.px(9, 11, 'c3')
            cv.px(8, 11, 'c3')
        if kind == 2:
            for y, (x0, x1) in D_RUST.items():
                for x in range(x0, x1 + 1):
                    cv.px(x, y, 'r2' if (x + y) % 2 == 0 else 'r1')
            cv.px(7, 17, 'r1')
            cv.px(7, 18, 'r1')
            cv.px(9, 17, 'r1')
            rivet(13, 11)
        if kind == 3:
            for y in (11, 13, 15):
                cv.rect(4, y, 11, y, 'k')
                cv.rect(4, y + 1, 11, y + 1, 'm4')
            cv.rect(3, 10, 3, 16, 'm2')
            cv.rect(12, 10, 12, 16, 'm5')
        if kind == 4:
            for p in ((4, 12), (5, 13), (6, 12), (8, 12), (9, 13), (10, 12)):
                cv.px(p[0], p[1], 'y2')
            rivet(13, 11)
            rivet(13, 16)
            for p in ((2, 15), (2, 16), (3, 16), (3, 17)):
                cv.px(p[0], p[1], 'r1')
            cv.px(2, 14, 'r2')
        if kind == 'L':
            rivet(13, 12)
            cv.rect(11, 14, 14, 14, 'm1')
        if kind == 'R':
            rivet(2, 12)
            cv.rect(1, 14, 4, 14, 'm1')
    else:
        if kind == 0:
            cv.px(3, 9, 'm5')
            cv.px(12, 9, 'm5')
        if kind == 1:
            cv.rect(7, 9, 8, 9, 'c2')
            cv.px(8, 9, 'c3')
        if kind == 2:
            for y in (8, 9, 10):
                for x in range(5, 11):
                    if y == 10 and x in (5, 10):
                        continue
                    cv.px(x, y, 'r2' if (x + y) % 2 == 0 else 'r1')
        if kind == 3:
            cv.rect(5, 9, 10, 9, 'k')
        if kind == 4:
            cv.px(12, 9, 'm5')
            cv.px(5, 9, 'y2')
            cv.px(7, 9, 'y2')
    if kind in ('L', 'R'):                   # lamp post: one thin vertical, then the rotor pod under the cap
        x = 2 if kind == 'L' else 13
        cv.rect(x, 2, x, 3, 'm3')
        cv.px(x, 1, 'y2')
        cv.px(x, 0, 'y3')
        hx = 8 if kind == 'L' else 7
        th = f * pi / FRAMES if kind == 'L' else pi / 2 - f * pi / FRAMES
        if tall == 2:
            cy, rx, ry = 25, 6.6, 2.6
            for y in range(rr[hx] + 1, cy):
                cv.px(hx, y, 'm4')
                cv.px(hx + (1 if kind == 'L' else -1), y, 'm2')
        else:
            cy, rx, ry = 13, 6.4, 1.6
            for y in range(rr[hx] + 1, cy):
                cv.px(hx, y, 'm4')
        s = sin(th)
        ends = [(1, 'm6' if s > 0.3 else ('m3' if s < -0.3 else 'm4')),
                (-1, 'm6' if s < -0.3 else ('m3' if s > 0.3 else 'm4'))]
        ends.sort(key=lambda e: e[1] == 'm6')         # far blade first, near blade on top
        for sign, col in ends:
            for i in range(1, 15):
                t = i / 14.0
                cv.px(int(round(hx + sign * rx * cos(th) * t)), int(round(cy + sign * ry * s * t)), col)
        cv.px(hx, cy, 'm2')
        cv.px(hx, cy + 1, 'c3')
        if tall == 2:
            cv.px(hx, cy - 1, 'm5')
    return cv.a


PIECE = {'roof': roof_piece, 'garden': garden_piece, 'deck': deck_piece}
_cache = {}


def piece(look, kind, tall, f):
    key = (look, kind, tall, f)
    if key not in _cache:
        _cache[key] = PIECE[look](kind, tall, f)
    return _cache[key]


def island(look, w, tall, f=0):
    return np.hstack([piece(look, 'L', tall, f)] + [piece(look, m, tall, f) for m in SEQ[w]] + [piece(look, 'R', tall, f)])


# ---------------------------------------------------------------- measurements

def tiles_of(a):
    out = []
    for ty in range(0, a.shape[0], 16):
        for tx in range(0, a.shape[1], 16):
            t = a[ty:ty + 16, tx:tx + 16]
            if t.any():
                out.append(t.tobytes())
    return out


def tile_counts(look):
    res = {}
    for tall in (1, 2):
        static, allf = [], []
        for w in WIDTHS:
            static += tiles_of(island(look, w, tall, 0))
            for f in range(FRAMES):
                allf += tiles_of(island(look, w, tall, f))
        s, a = set(static), set(allf)
        anim_tiles = len(set(tiles_of(np.hstack([piece(look, k, tall, 0) for k in ('L', 'R')])))
                         - set.intersection(*[set(tiles_of(np.hstack([piece(look, k, tall, f) for k in ('L', 'R')])))
                                              for f in range(FRAMES)]))
        distinct = len({b''.join(tiles_of(np.hstack([piece(look, k, tall, f) for k in ('L', 'R')]))) for f in range(FRAMES)})
        res[tall] = dict(static=len(s), total=len(a), extra=len(a) - len(s), slots=anim_tiles, distinct=distinct, set=a, sset=s)
    res['all_static'] = len(res[1]['sset'] | res[2]['sset'])
    res['all_total'] = len(res[1]['set'] | res[2]['set'])
    return res


def line_load(layout):
    per = np.zeros(224, int)
    cnt = np.zeros(224, int)
    for x, y, w, tall in layout:
        y0 = y - LINE
        per[max(y0, 0):y0 + 16 * tall] += int(ceil(w / 16.0))
        cnt[max(y0, 0):y0 + 16 * tall] += 1
    return per, cnt


def runs(mask):
    out, start = [], None
    for i, v in enumerate(list(mask) + [False]):
        if v and start is None:
            start = i
        if not v and start is not None:
            out.append('%d..%d' % (start, i - 1))
            start = None
    return ', '.join(out) if out else 'none'


def edge_stats(look, a, bg, x, top):
    """(lower edge pixels, of them under 24, standing line pixels, of them under 24) against the backdrop."""
    prgb = pal_rgb(look)
    n = bad = ln = lbad = 0
    for cx in range(a.shape[1]):
        col = a[:, cx]
        ys = np.nonzero(col)[0]
        ax = (x + cx) % bg.shape[1]
        yb = top + ys[-1] + 1
        if 0 <= yb < bg.shape[0]:
            n += 1
            bad += abs(lum(prgb[col[ys[-1]] - 1]) - lum(bg[yb, ax])) < 24
        if col[LINE - 1] == 0 and top + LINE - 1 >= 0:
            ln += 1
            lbad += abs(lum(prgb[col[LINE] - 1]) - lum(bg[top + LINE - 1, ax])) < 24
    return n, bad, ln, lbad


def pct(b, n):
    return 100.0 * b / max(n, 1)


# ---------------------------------------------------------------- pictures

def load_soot(name):
    im = np.array(Image.open(os.path.join(SOOT, name)).convert('RGB'))
    return lambda n: im[(n // 8) * 48:(n // 8) * 48 + 48, (n % 8) * 32:(n % 8) * 32 + 32]


def scene(look, bg, layout, f=0, birds=True):
    out = bg.copy()
    for x, y, w, tall in layout:
        blit(out, island(look, w, tall, f), look, x, y - LINE, wrap=True)
    if birds:
        p, c = load_soot('sootling_final_sheet_1x.png'), load_soot('sootling_final_sheet_cpu_1x.png')
        stand = lambda isl, dx=0: (isl[0] + isl[2] // 2 - 16 + dx, isl[1] - 48)
        blit_rgb(out, p(62), *stand(layout[2], -20))
        blit_rgb(out, c(62), *stand(layout[7]), flip=True)
        blit_rgb(out, c(62), *stand(layout[3], 10))
        blit_rgb(out, c(3), 250, 60, flip=True)
    return out


def sheet(look):
    out = np.zeros((48 * len(WIDTHS), 112, 3), np.uint8)
    out[:] = TRANSP
    for i, w in enumerate(WIDTHS):
        blit(out, island(look, w, 2), look, 0, 48 * i)
        blit(out, island(look, w, 1), look, 0, 48 * i + 32)
    return out


def tileset(look, tc):
    order, seen = [], set()
    for f in range(FRAMES):
        for tall in (1, 2):
            for w in WIDTHS:
                for t in tiles_of(island(look, w, tall, f)):
                    if t not in seen:
                        seen.add(t)
                        order.append(t)
    rows = int(ceil(len(order) / 16.0))
    out = np.zeros((rows * 16, 256, 3), np.uint8)
    out[:] = TRANSP
    for i, t in enumerate(order):
        blit(out, np.frombuffer(t, np.uint8).reshape(16, 16), look, (i % 16) * 16, (i // 16) * 16)
    return out


def preview(look, bg):
    out = bg[36:36 + 140, 60:60 + 264].copy()
    for w, tall, x, y in ((112, 2, 8, 10), (96, 2, 136, 10), (80, 2, 8, 52), (64, 2, 104, 52), (64, 1, 184, 52),
                          (112, 1, 8, 96), (96, 1, 136, 96), (80, 1, 8, 118)):
        blit(out, island(look, w, tall), look, x, y)
    return out


def contact(look, bg):
    flat = np.median(bg[30:170].reshape(-1, 3), 0).astype(np.uint8)
    out = np.zeros((2 * 56, 4 * 72, 3), np.uint8)
    out[:] = flat
    for f in range(FRAMES):
        ox, oy = (f % 4) * 72, (f // 4) * 56
        blit(out, island(look, 64, 2, f), look, ox + 4, oy + 4)
        blit(out, island(look, 64, 1, f), look, ox + 4, oy + 38)
    return out


def anim(look, bg):
    frs = []
    for f in range(FRAMES):
        fr = bg[60:60 + 72, 128:128 + 128].copy()
        blit(fr, island(look, 112, 2, f), look, 8, 6)
        blit(fr, island(look, 64, 1, f), look, 32, 50)
        frs.append(fr)
    return frs


# ---------------------------------------------------------------- report files

def write_numbers(tc, loads, edges):
    L = []
    L.append('Gumbirds island sheets, final. All numbers are measured by draw_islands_final.py.')
    L.append('')
    L.append('Box: pieces are 16 px wide. Thin island = 16 px tall, tall island = 32 px tall.')
    L.append('Standing line (collision height) = sheet row %d in every piece; the sprite top is stage y - %d.' % (LINE, LINE))
    L.append('Rows 0..%d hold decoration above the line; rows %d and %d are the bright line.' % (LINE - 1, LINE, LINE + 1))
    L.append('Middle pieces used per width: ' + '; '.join('%d = %s' % (w, ' '.join('m%d' % m for m in SEQ[w])) for w in WIDTHS))
    L.append('Animation: %d frames at %d ms, tile swaps in the two cap pieces only.' % (FRAMES, MS))
    L.append('')
    for look, d in LOOKS.items():
        L.append('%s' % d['title'])
        L.append('  palette (15 colours, 5 bits per channel, index 0 is transparent 255,0,255):')
        for i, (n, _) in enumerate(d['pal']):
            c = pal_rgb(look)[i]
            L.append('    %2d %-3s %3d,%3d,%3d  luminance %3d' % (i + 1, n, c[0], c[1], c[2], round(lum(c))))
        used = set()
        for tall in (1, 2):
            for f in range(FRAMES):
                used |= set(np.unique(island(look, 112, tall, f)).tolist())
        L.append('  palette entries used: %d of 15' % (len(used - {0})))
        t = tc[look]
        for tall, name in ((1, 'thin (one tile tall)'), (2, 'tall (two tiles tall)')):
            v = t[tall]
            L.append('  %s: %d unique 16x16 tiles for all four widths, static; %d with all animation frames '
                     '(%d extra); %d distinct frames; %d tile positions swap'
                     % (name, v['static'], v['total'], v['extra'], v['distinct'], v['slots']))
        L.append('  both variants together: %d static, %d with animation (no tile flips counted)' % (t['all_static'], t['all_total']))
        e = edges[look]
        L.append('  lower edge under 24 luminance steps from the %s backdrop: proposal layout %.1f%% of %d edge pixels '
                 '(8 frames); sweep over the whole play area %.1f%% of %d' % (d['mood'], pct(e[1], e[0]), e[0], pct(e[5], e[4]), e[4]))
        L.append('  standing line under 24 steps from the backdrop pixel above it: proposal layout %.1f%% of %d; sweep %.1f%% of %d'
                 % (pct(e[3], e[2]), e[2], pct(e[7], e[6]), e[6]))
        L.append('')
    L.append('Sprite load per scanline (platform strips only, one strip per 16 px of width, every island counted')
    L.append('whether or not it is on screen):')
    for name, (lay, per, cnt) in loads.items():
        L.append('  %s: worst line %d strips (lines %s); lines shared by two or more islands: %s'
                 % (name, per.max(), runs(per == per.max()), runs(cnt > 1)))
    L.append('')
    L.append('Proposed layout (x, y, width, tiles tall) against the stage table (x, y, width):')
    for p, t in zip(PROPOSAL, TABLE):
        diff = [n for n, a, b in (('x', p[0], t[0]), ('y', p[1], t[1]), ('width', p[2], t[2])) if a != b]
        L.append('  (%3d, %3d, %3d, %d)   table (%3d, %3d, %3d)   sprite lines %3d..%3d   differs in: %s'
                 % (p + t + (p[1] - LINE, p[1] - LINE + 16 * p[3] - 1, ', '.join(diff) or 'nothing')))
    per = loads['proposal'][1]
    L.append('  strips per line: ' + ', '.join('%s: %d' % (r, v) for v in sorted(set(per.tolist())) for r in [runs(per == v)]))
    open(os.path.join(HERE, 'numbers.txt'), 'w').write('\n'.join(L) + '\n')
    return L


def write_html(tc, loads, edges):
    H = ['<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Gumbirds islands, final sheets</title><style>',
         'body{background:#14161c;color:#d8dbe2;font-family:Helvetica,Arial,sans-serif;margin:28px;line-height:1.45}',
         'h1{font-size:24px;margin:0 0 6px}h2{font-size:19px;margin:34px 0 8px;color:#fff;border-bottom:2px solid #3a4152;padding-bottom:4px}',
         'h3{font-size:14px;margin:16px 0 6px;color:#aab2c5}img{image-rendering:pixelated;display:block;margin:6px 0 14px;border:1px solid #2b303c}',
         'p{max-width:900px;margin:6px 0}.weak{border-left:4px solid #c8553d;padding:6px 10px;background:#1d2029;max-width:880px}',
         'table{border-collapse:collapse;margin:8px 0}td,th{border:1px solid #333a49;padding:4px 10px;text-align:right}th{background:#1d2029}',
         '.diff{color:#ffb454;font-weight:bold}</style></head><body>',
         '<h1>Gumbirds islands, final sheets and layout proposal</h1>',
         '<p>Three looks, one per mood. Every image is drawn at 1x and enlarged without smoothing. '
         'The standing line is sheet row %d; the collision height is that row. Numbers: numbers.txt.</p>' % LINE]
    for look, d in LOOKS.items():
        t, e = tc[look], edges[look]
        H.append('<h2>%s</h2>' % d['title'])
        H.append('<p>Tiles: thin %d, tall %d, both %d static; with animation %d. Animation: %d distinct frames, '
                 '%d extra tiles thin, %d extra tiles tall. Lower edge under 24 luminance steps from the backdrop: '
                 '%.1f%% in the proposed layout, %.1f%% in a sweep of the play area.</p>'
                 % (t[1]['static'], t[2]['static'], t['all_static'], t['all_total'], t[2]['distinct'], t[1]['extra'],
                    t[2]['extra'], pct(e[1], e[0]), pct(e[5], e[4])))
        H.append('<p class="weak">Weak point: %s</p>' % WEAK[look])
        H.append('<h3>All widths, tall and thin, 3x</h3><img src="preview_%s_1x.png" width="792" height="420" alt="">' % look)
        H.append('<h3>Animation, 3x</h3><img src="anim_%s_3x.gif" alt="">' % look)
        H.append('<h3>Proposed layout in the 384 px arena, 2x</h3><img src="scene_%s_384_2x.png" alt="">' % d['mood'])
        H.append('<h3>Proposed layout, 1x</h3><img src="scene_%s_384_1x.png" alt="">' % d['mood'])
        H.append('<h3>Sheet (magenta is transparent), 3x</h3><img src="sheet_%s_1x.png" width="336" height="576" alt="">' % look)
        H.append('<h3>Unique tiles with all animation frames, 2x</h3><img src="tiles_%s_1x.png" width="512" alt="">' % look)
    H.append('<h2>Layout proposal</h2><p>Values in orange differ from the stage table in src/core/stage.c. '
             'They are a proposal, not a decision.</p>')
    H.append('<table><tr><th>x</th><th>y</th><th>width</th><th>tiles tall</th><th>sprite lines</th><th>table x</th><th>table y</th><th>table width</th></tr>')
    for p, t in zip(PROPOSAL, TABLE):
        cell = lambda a, b: '<td class="diff">%d</td>' % a if a != b else '<td>%d</td>' % a
        H.append('<tr>%s%s%s<td>%d</td><td>%d..%d</td><td>%d</td><td>%d</td><td>%d</td></tr>'
                 % (cell(p[0], t[0]), cell(p[1], t[1]), cell(p[2], t[2]), p[3], p[1] - LINE, p[1] - LINE + 16 * p[3] - 1, t[0], t[1], t[2]))
    H.append('</table><table><tr><th>layout</th><th>worst line, strips</th><th>worst lines</th><th>lines shared by two or more islands</th></tr>')
    for name, (lay, per, cnt) in loads.items():
        H.append('<tr><td>%s</td><td>%d</td><td>%s</td><td>%s</td></tr>' % (name, per.max(), runs(per == per.max()), runs(cnt > 1)))
    H.append('</table></body></html>')
    open(os.path.join(HERE, 'index.html'), 'w').write('\n'.join(H) + '\n')


def main():
    tc = {look: tile_counts(look) for look in LOOKS}
    loads = {}
    for name, lay in (('stage table today, all tall', [(x, y, w, 2) for x, y, w in TABLE]),
                      ('stage table today, all thin', [(x, y, w, 1) for x, y, w in TABLE]),
                      ('proposal', PROPOSAL)):
        per, cnt = line_load(lay)
        loads[name] = (lay, per, cnt)
    edges = {}
    for look, d in LOOKS.items():
        bg = np.array(Image.open(os.path.join(HERE, 'backdrop_%s_384_1x.png' % d['mood'])).convert('RGB'))
        e = [0] * 8
        for f in range(FRAMES):
            for x, y, w, tall in PROPOSAL:
                r = edge_stats(look, island(look, w, tall, f), bg, x, y - LINE)
                for i in range(4):
                    e[i] += r[i]
        for w, tall in ((112, 1), (64, 1), (112, 2), (64, 2)):
            for top in range(28, 161, 8):
                for x in range(0, 384, 16):
                    r = edge_stats(look, island(look, w, tall, 0), bg, x, top)
                    for i in range(4):
                        e[4 + i] += r[i]
        edges[look] = e
        save_png('sheet_%s_1x.png' % look, sheet(look))
        save_png('tiles_%s_1x.png' % look, tileset(look, tc[look]))
        save_png('preview_%s_1x.png' % look, preview(look, bg))
        save_png('preview_%s_3x.png' % look, preview(look, bg), 3)
        save_png('contact_%s_4x.png' % look, contact(look, bg), 4)
        sc = scene(look, bg, PROPOSAL)
        save_png('scene_%s_384_1x.png' % d['mood'], sc)
        save_png('scene_%s_384_2x.png' % d['mood'], sc, 2)
        save_gif('anim_%s_3x.gif' % look, anim(look, bg), MS, 3)
    for line in write_numbers(tc, loads, edges):
        print(line)
    write_html(tc, loads, edges)


if __name__ == '__main__':
    main()
