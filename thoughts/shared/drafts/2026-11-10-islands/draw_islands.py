#!/opt/homebrew/bin/python3.14 -I
"""
Gumbirds island drafts (2026-11-10): three options for the platforms the fliers stand on.

  roof    A  torn-off brick roof chunk with a stone coping and a swinging lantern
  garden  B  floating planter slab: turf, soil, root ball, swaying vines and grass
  deck    C  airship deck plate on a truss, held up by two rotor pods

Run:  /opt/homebrew/bin/python3.14 -I draw_islands.py
Writes sheets, scene mock-ups, zoom sheets, GIFs, numbers.txt and index.html next to this file.
Conventions copied from draw_backgrounds_wide.py (role-index canvases, lum, up, save_gif, magenta build sheets).
Nothing is imported from the other draft scripts; the backdrop and Sootling PNGs are only read.

Platform box: w x 32 px. Row 8 is the standing line (stage y). Rows 0..7 hold what stands above the line,
rows 8..15 are the 8 px collision body (STAGE_PLATFORM_H), rows 16..31 the underside.
Light comes from the upper right (moon and sun sit at the right of the sky).
"""
import os
from math import sin, cos, pi, ceil
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
BGDIR = os.path.join(HERE, '..', '2026-11-10-backgrounds-final')
SOOTDIR = os.path.join(HERE, '..', '2026-11-10-sootling-final')
TRANSP = (255, 0, 255)
W, H = 320, 224
ARENA_W = 384
CAM = 32                       # camera x of the mock-ups: both seam islands are in view
BOX_H = 32
TOP = 8                        # standing line inside the box
NF = 8                         # animation frames
TAU = 2 * pi
MOODS = ('moon', 'dusk', 'storm')
MOODNAME = {'moon': 'Clear night, moon', 'dusk': 'Ember dusk', 'storm': 'Storm'}
# src/core/stage.c stage_platforms: x, y, w (world pixels; h = 8)
STAGE = [(0, 164, 80), (304, 164, 80), (136, 140, 112), (32, 104, 80), (280, 104, 80), (144, 72, 96), (0, 40, 56), (328, 40, 56)]


def lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def q5(c):
    """Neo Geo colour grid: 5 bits per channel."""
    return tuple(((v >> 3) << 3) | (v >> 5) for v in c)


def up(a, k):
    return np.repeat(np.repeat(a, k, 0), k, 1)


class Cv:
    """Role-index canvas. s marks solid structure (gets the keyline); soft things (grass, vines) do not."""

    def __init__(self, h, w):
        self.h, self.w = h, w
        self.a = np.zeros((h, w), np.uint8)
        self.s = np.zeros((h, w), bool)

    def px(self, x, y, r, solid=True):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.a[y, x] = r
            self.s[y, x] = solid

    def rect(self, x0, y0, x1, y1, r, solid=True):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.px(x, y, r, solid)

    def get(self, x, y):
        return self.a[y, x] if 0 <= x < self.w and 0 <= y < self.h else 0

    def keyline(self, k):
        """Dark line round the solid mass: outside it where there is room, on the end columns where there is none.
        The standing line keeps its bright top: nothing is drawn on row TOP-1 above the surface."""
        s = self.s
        out = np.zeros_like(s)
        out[:, 1:] |= s[:, :-1]
        out[:, :-1] |= s[:, 1:]
        out[1:, :] |= s[:-1, :]
        below = np.zeros_like(s)
        below[:-1, :] = s[1:, :]
        below[TOP - 1, :] = False
        out |= below
        out &= (self.a == 0)
        self.a[out] = k
        for x in (0, self.w - 1):
            for y in range(TOP + 1, self.h):
                if s[y, x]:
                    self.a[y, x] = k


def roles(names):
    return {n: i + 1 for i, n in enumerate(names.split())}


# --------------------------------------------------------------------------------------------------------------
# Option A: roof chunk
# --------------------------------------------------------------------------------------------------------------
RA = roles('k s1 s2 s3 s4 s5 b1 b2 b3 b4 b5 i1 i2 g1 g2')
PAL_A = {
    'moon': [(16, 8, 33), (49, 41, 82), (90, 82, 123), (148, 140, 165), (206, 198, 198), (255, 247, 222),
             (57, 16, 49), (99, 33, 57), (156, 57, 57), (206, 99, 66), (247, 156, 99),
             (41, 49, 74), (123, 140, 165), (255, 165, 41), (255, 247, 165)],
    'dusk': [(24, 8, 33), (66, 33, 74), (123, 66, 90), (189, 115, 107), (247, 181, 132), (255, 247, 206),
             (16, 33, 66), (24, 66, 99), (41, 115, 132), (82, 165, 156), (165, 222, 189),
             (33, 33, 66), (132, 132, 156), (255, 222, 90), (255, 255, 214)],
    'storm': [(8, 16, 24), (33, 49, 66), (74, 99, 115), (132, 156, 165), (198, 214, 214), (255, 255, 247),
              (49, 24, 33), (99, 57, 49), (156, 99, 57), (206, 148, 82), (247, 206, 132),
              (33, 41, 49), (115, 132, 140), (255, 148, 41), (255, 239, 156)],
}
# masonry depth in brick courses (3 px each, first course at row 12) per 4 px column
A_MID = [4, 5, 5, 6, 5, 4, 6, 5]              # period 32
A_CAPL = [2, 3, 3, 4]
A_CAPR = [4, 3, 2, 2]
# hand-placed brick states: (course, brick number in the 32 px period) -> 'L' lit, 'D' dark, 'C' chipped, 'H' hole
A_VAR = {(0, 1): 'D', (1, 0): 'L', (1, 2): 'C', (1, 3): 'L', (2, 1): 'L', (2, 2): 'D', (3, 0): 'D', (3, 3): 'L',
         (4, 1): 'H', (4, 2): 'L', (5, 0): 'D', (5, 3): 'C'}
A_VARL = {(0, 0): 'D', (1, 0): 'D', (1, 1): 'L', (2, 1): 'C', (3, 1): 'D'}
A_VARR = {(0, 1): 'L', (1, 0): 'L', (1, 1): 'L', (2, 0): 'C', (3, 0): 'D'}
A_JOINT = (6, 21)                              # coping joints, phase in the 32 px period
A_CHIP = {12: 1, 13: 1, 27: 2}                 # coping chips: phase -> rows lost from the top highlight
A_REBAR = [(9, 4, 0), (22, 3, 1), (29, 2, 0)]  # (phase, length, bend)


def roof(w, f):
    cv = Cv(BOX_H, w)
    R = RA

    def zone(x):
        if x < 16:
            return 'L', x
        if x >= w - 16:
            return 'R', x - (w - 16)
        return 'M', (x - 16) % 32

    def courses(x):
        z, p = zone(x)
        return {'L': A_CAPL, 'R': A_CAPR, 'M': A_MID}[z][p // 4]

    # brick body
    for x in range(1, w - 1):
        z, p = zone(x)
        n = courses(x)
        for c in range(n):
            y0 = 12 + 3 * c
            off = 4 if c & 1 else 0
            bx = p + off
            pos = bx % 8
            var = {'L': A_VARL, 'R': A_VARR, 'M': A_VAR}[z].get((c, (bx // 8) % 4), '')
            # light falls off with depth: under the coping lip, lit face, then the underside in shadow
            lv = (2, 4, 4, 3, 2, 2)[c]
            if z == 'L' and p < 6:
                lv -= 1
            if z == 'R' and p > 9:
                lv += 1
            if var == 'L':
                lv += 1
            if var == 'D':
                lv -= 1
            lv = min(max(lv, 2), 5)
            hi, lo = R['b%d' % lv], R['b%d' % (lv - 1)]
            mortar = R['b1'] if lv > 2 else R['k']
            if var == 'H':                       # a brick knocked out: dark socket
                cv.px(x, y0, R['k'])
                cv.px(x, y0 + 1, R['b1'])
            elif pos == 7:
                cv.px(x, y0, mortar)
                cv.px(x, y0 + 1, mortar)
            else:
                cv.px(x, y0, hi)
                cv.px(x, y0 + 1, lo)
                if pos == 6 and lv >= 3:           # lit right corner of the brick
                    cv.px(x, y0, R['b%d' % min(lv + 1, 5)])
                if pos == 0:                       # shaded left end
                    cv.px(x, y0 + 1, R['b%d' % max(lv - 2, 1)])
                if var == 'C' and pos in (0, 1):   # chipped corner
                    cv.px(x, y0, lo)
                    if pos == 0:
                        cv.px(x, y0, mortar)
            if c < n - 1:
                cv.px(x, y0 + 2, mortar)
            else:                                  # broken lower edge: ragged last row
                if (p * 7 + c * 3) % 5 < 3:
                    cv.px(x, y0 + 2, R['b1'])
        if n and cv.get(x, 12):                    # cast shadow of the coping on the first brick row
            if cv.a[12, x] != R['k']:
                cv.a[12, x] = R['b2'] if cv.a[12, x] in (R['b3'], R['b4'], R['b5']) else R['b1']
    # rebar stubs out of the torn underside
    for x in range(16, w - 16):
        p = (x - 16) % 32
        for ph, ln, bend in A_REBAR:
            if p == ph:
                y0 = 12 + 3 * courses(x)
                for i in range(ln):
                    xx = x + (bend if i >= ln - 1 else 0)
                    cv.px(xx, y0 + i, R['i2'] if i < ln - 1 else R['i1'])
    # coping stone, rows 8..11, full width
    for x in range(w):
        z, p = zone(x)
        col = [R['s5'], R['s4'], R['s3'], R['s1']]
        if z == 'M' and p in A_JOINT or (z == 'L' and p == 9) or (z == 'R' and p == 5):
            col = [R['s4'], R['s2'], R['s2'], R['s1']]
        if z == 'M' and (p - 1) in A_JOINT:        # lit edge right of a joint
            col = [R['s5'], R['s5'], R['s3'], R['s1']]
        if z == 'M' and p in A_CHIP:
            col = [R['s3'], R['s4'], R['s3'], R['s1']] if A_CHIP[p] == 1 else [R['s2'], R['s3'], R['s3'], R['s1']]
        if z == 'M' and p in (3, 4, 16, 17, 18, 25):   # worn patches on the face
            col[2] = R['s2']
        if z == 'M' and p in (9, 10, 23):
            col[1] = R['s5']
        if x == w - 2:                             # lit end face
            col = [R['s5'], R['s5'], R['s4'], R['s2']]
        if x == 1:
            col = [R['s4'], R['s3'], R['s2'], R['s1']]
        if x in (0, w - 1):
            col = [R['s4'] if x == 0 else R['s5'], R['s2'], R['s2'], R['s1']]
        for i, c in enumerate(col):
            cv.px(x, 8 + i, c)
    # iron bracket and lantern under the right cap; a pendulum, the lantern body lags behind the chain
    px0, py0 = w - 16 + 9, 20
    cv.rect(px0 - 2, 18, px0 + 2, 18, R['i2'])
    cv.rect(px0 - 1, 19, px0 + 1, 19, R['i1'])
    th = 0.44 * sin(TAU * f / NF)
    vel = cos(TAU * f / NF)
    for d in range(0, 5):
        cv.px(px0 + int(round(d * sin(th))), py0 + int(round(d * cos(th))), R['i2'] if d % 2 == 0 else R['i1'])
    lx, ly = px0 + int(round(7.2 * sin(th))), py0 + int(round(7.2 * cos(th)))
    lag = -1 if vel > 0.5 else (1 if vel < -0.5 else 0)   # the body trails the swing by one pixel at full speed
    cv.rect(lx - 1, ly - 3, lx + 1, ly - 3, R['i2'])
    cv.rect(lx - 2, ly - 2, lx + 2, ly - 2, R['i1'])
    for i, yy in enumerate((ly - 1, ly, ly + 1)):
        o = lag if i == 2 else 0
        cv.rect(lx - 2 + o, yy, lx + 2 + o, yy, R['g1'])
        cv.px(lx + o, yy, R['g2'])
        cv.px(lx + 1 + o, yy, R['g2'] if i < 2 else R['g1'])
        cv.px(lx - 2 + o, yy, R['i1'])
    cv.rect(lx - 1 + lag, ly + 2, lx + 1 + lag, ly + 2, R['i1'])
    cv.keyline(R['k'])
    return cv.a


# --------------------------------------------------------------------------------------------------------------
# Option B: garden slab
# --------------------------------------------------------------------------------------------------------------
RB = roles('k d1 d2 d3 d4 t1 t2 g1 g2 g3 g4 g5 f1 f2 rt')
PAL_B = {
    'moon': [(8, 16, 33), (33, 16, 41), (82, 41, 57), (132, 74, 66), (189, 123, 90), (140, 140, 173), (222, 222, 239),
             (8, 57, 66), (16, 99, 74), (49, 148, 66), (132, 206, 74), (222, 247, 132),
             (255, 198, 74), (255, 255, 214), (214, 173, 132)],
    'dusk': [(16, 8, 33), (24, 8, 41), (74, 33, 74), (123, 66, 82), (181, 115, 99), (165, 132, 148), (247, 222, 206),
             (16, 57, 57), (33, 99, 57), (90, 148, 49), (173, 206, 66), (247, 247, 140),
             (132, 222, 231), (239, 255, 255), (231, 181, 132)],
    'storm': [(8, 16, 24), (24, 16, 41), (66, 57, 74), (107, 90, 90), (156, 140, 123), (140, 156, 173), (231, 239, 247),
              (8, 49, 57), (24, 90, 82), (57, 140, 99), (132, 198, 132), (214, 247, 198),
              (255, 214, 90), (255, 255, 222), (198, 181, 156)],
}
B_TURF = ["5555455555545555" "5545555555555455",      # row 8: standing line
          "4454344544434454" "4344544443445443",      # row 9
          "3343233433323343" "3233433332334332"]      # row 10
B_LOBE = [1, 2, 3, 2, 1, 1, 2, 2, 1, 0, 1, 2, 3, 3, 2, 1, 1, 2, 1, 0, 1, 2, 2, 3, 2, 1, 0, 1, 2, 2, 1, 1]   # turf overhang, rows below 10
B_BOT = [26, 27, 28, 28, 29, 29, 28, 27, 25, 26, 27, 28, 28, 27, 26, 25]     # soil bottom row per 2 px column, period 32
B_BOTL = [15, 18, 20, 22, 23, 24, 25, 25]
B_BOTR = [25, 25, 24, 23, 21, 19, 17, 14]
B_E1 = [0, 0, 1, 1, 2, 2, 1, 0, 0, -1, -1, 0, 1, 2, 2, 1, 1, 0, 0, 1, 2, 3, 2, 1, 0, 0, -1, 0, 1, 1, 0, 0]  # lit soil boundary
B_E2 = [1, 1, 0, 0, 1, 2, 2, 1, 0, 0, 1, 1, 2, 1, 0, 0, 1, 2, 2, 1, 1, 0, 0, 1, 1, 0, 1, 2, 1, 0, 0, 1]     # deep shadow boundary
B_LIT = [(3, 14, 3, 2), (10, 13, 2, 1), (19, 15, 4, 2), (27, 13, 3, 2), (14, 16, 2, 1)]     # d4 clumps: phase, row, w, h
B_STONE = [(6, 17, 5, 3), (22, 20, 4, 3), (29, 16, 3, 2)]                                   # phase, row, w, h
B_ROOT = [(4, 5, (0, 0, 1, 1, 1)), (13, 4, (0, -1, -1, -1)), (20, 6, (0, 0, 0, 1, 1, 2)), (26, 3, (0, 1, 1))]
B_TUFT = [(2, 3, 0, 0), (5, 4, 1, 0), (6, 2, 0, 0), (11, 5, -1, 1), (14, 3, 1, 0), (18, 2, 0, 0), (21, 4, 1, 0),
          (22, 3, -1, 0), (27, 5, 0, 1), (30, 3, 1, 0)]                                     # phase, height, lean, blossom
B_TUFTL = [(3, 4, -1, 0), (6, 5, 0, 1), (10, 3, 1, 0), (13, 4, 0, 0)]
B_TUFTR = [(2, 3, 0, 0), (5, 5, 1, 1), (9, 4, 0, 0), (12, 3, -1, 0)]
DITHER_B = [('d3', 'd4'), ('d2', 'd3'), ('d1', 'd2')]


def garden(w, f):
    cv = Cv(BOX_H, w)
    R = RB

    def zone(x):
        if x < 16:
            return 'L', x
        if x >= w - 16:
            return 'R', x - (w - 16)
        return 'M', (x - 16) % 32

    def bot(x):
        z, p = zone(x)
        return {'L': B_BOTL, 'R': B_BOTR, 'M': B_BOT}[z][p // 2]

    # soil and root ball
    for x in range(1, w - 1):
        z, p = zone(x)
        b = bot(x)
        e2 = b - 3 - B_E2[p % 32]
        e1 = min(15 + B_E1[p % 32] + (2 if z == 'R' and p > 6 else 0) - (2 if z == 'L' and p < 8 else 0), e2 - 2)
        for y in range(11, b + 1):
            if y <= e1:
                c = R['d3']
            elif y == e1 + 1:
                c = R['d3'] if (x + y) & 1 else R['d2']        # one row of teeth, soft soil only
            elif y <= e2:
                c = R['d2']
            elif y == e2 + 1:
                c = R['d2'] if (x + y) & 1 else R['d1']
            else:
                c = R['d1']
            cv.px(x, y, c)
        if z == 'M':
            for ph, ry, rw, rh in B_LIT:               # lit clumps with a dithered lower lip
                if ph <= p < ph + rw:
                    for i in range(rh):
                        if ry + i <= e1:
                            cv.px(x, ry + i, R['d4'])
                    if ry + rh <= e1 and (x + ry + rh) & 1:
                        cv.px(x, ry + rh, R['d4'])
            for ph, ry, rw, rh in B_STONE:             # buried stones: hard edges, no dither
                if ph <= p < ph + rw and ry + rh < b:
                    i = p - ph
                    for j in range(rh):
                        if (i in (0, rw - 1)) and j in (0, rh - 1) and rw > 3:
                            continue
                        cv.px(x, ry + j, R['t2'] if j == 0 or (i == rw - 1 and j < rh - 1) else R['t1'])
                    cv.px(x, ry + rh, R['d1'] if cv.get(x, ry + rh) else 0)
        if z == 'R' and 3 <= p <= 9:                    # lit flank toward the light
            for y in range(13, min(e1, 15) + 1):
                cv.px(x, y, R['d4'] if (p + y) % 3 else R['d3'])
        if z == 'L' and p in (5, 6, 7) and b > 20:
            cv.px(x, 17 + (p & 1), R['t1'])
            cv.px(x, 16 + (p & 1), R['t2'])
    # roots under the mid tiles
    for x in range(16, w - 16):
        p = (x - 16) % 32
        for ph, ln, wig in B_ROOT:
            if p == ph:
                for i in range(ln):
                    cv.px(x + wig[i], bot(x) + 1 + i, R['rt'] if i < ln - 2 else R['d3'], solid=False)
    cv.keyline(R['k'])
    # turf: bright standing line, leafy body, lobes hanging over the soil
    for x in range(w):
        z, p = zone(x)
        ph = p if z == 'M' else (p + (11 if z == 'L' else 21)) % 32
        for i in range(3):
            cv.px(x, 8 + i, R['g' + B_TURF[i][ph]])
        n = B_LOBE[ph]
        for i in range(n):
            cv.px(x, 11 + i, R['g2'] if i < n - 1 else R['g1'])
        if n == 0:
            cv.px(x, 10, R['g1'])
        elif cv.get(x, 11 + n) not in (0, R['k']):
            cv.px(x, 11 + n, R['d2'])                  # shadow of the overhang on the soil
    cv.px(0, 8, R['g4']); cv.px(0, 9, R['g2']); cv.px(0, 10, R['g1'])
    cv.px(w - 1, 9, R['g3']); cv.px(w - 1, 10, R['g1'])

    # grass blades: cantilever bend, the gust runs left to right; only the caps move (tile cost)
    def tuft(x0, hgt, lean, blossom, moving):
        sway = 1.5 * sin(TAU * (f / NF - (x0 if x0 < 16 else x0 - (w - 16) + 16) / 48.0)) if moving else 0.0
        tip = None
        for i in range(hgt):
            t = (i + 1) / hgt
            xx = x0 + int(round((lean * 1.2 + sway) * t * t))
            c = R['g3'] if i == 0 else (R['g5'] if i == hgt - 1 else R['g4'])
            cv.px(xx, 7 - i, c, solid=False)
            tip = (xx, 7 - i)
        if blossom:
            xx, yy = tip
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                cv.px(xx + dx, yy + dy, R['f1'], solid=False)
            cv.px(xx, yy, R['f2'], solid=False)

    for x in range(16, w - 16):
        for ph, hgt, lean, bl in B_TUFT:
            if (x - 16) % 32 == ph:
                tuft(x, hgt, lean, bl, False)
    for ph, hgt, lean, bl in B_TUFTL:
        tuft(ph, hgt, lean, bl, True)
    for ph, hgt, lean, bl in B_TUFTR:
        tuft(w - 16 + ph, hgt, lean, bl, True)

    # hanging vines: travelling wave down the stem, amplitude grows toward the free end
    def vine(x0, y0, ln, amp, ph, lo, hi):
        for t in range(ln):
            u = t / (ln - 1)
            xx = x0 + int(round(amp * u ** 1.6 * sin(TAU * f / NF - 1.9 * u + ph)))
            xx = min(max(xx, lo + 1), hi - 1)
            cv.px(xx, y0 + t, R['g3'] if t % 3 else R['g2'], solid=False)
            if t % 4 == 2 and t < ln - 1:
                s = 1 if (t // 4) & 1 else -1
                cv.px(xx + s, y0 + t, R['g4'], solid=False)
                cv.px(xx + s, y0 + t + 1, R['g5'], solid=False)
                cv.px(xx - s, y0 + t, R['g1'], solid=False)
        cv.px(xx, y0 + ln - 1, R['g5'], solid=False)

    vine(4, 11, 17, 2.6, 0.0, 0, 15)
    vine(9, 12, 9, 1.4, 0.9, 0, 15)
    vine(w - 5, 11, 19, 2.8, 0.5, w - 16, w - 1)
    vine(w - 11, 12, 10, 1.5, 1.6, w - 16, w - 1)
    return cv.a


# --------------------------------------------------------------------------------------------------------------
# Option C: airship deck
# --------------------------------------------------------------------------------------------------------------
RC = roles('k m1 m2 m3 m4 m5 m6 y1 y2 y3 c1 c2 c3 r1 r2')
PAL_C = {
    'moon': [(8, 8, 24), (24, 24, 49), (49, 57, 90), (90, 107, 140), (140, 165, 189), (198, 222, 231), (255, 255, 255),
             (156, 82, 24), (247, 173, 24), (255, 231, 107), (16, 82, 99), (33, 165, 173), (140, 247, 231),
             (99, 49, 49), (181, 99, 57)],
    'dusk': [(16, 8, 33), (16, 24, 57), (33, 57, 90), (57, 107, 132), (107, 165, 165), (181, 222, 206), (255, 255, 239),
             (132, 82, 99), (255, 222, 165), (255, 247, 206), (16, 74, 107), (24, 156, 189), (156, 247, 255),
             (107, 41, 33), (206, 107, 49)],
    'storm': [(8, 8, 16), (24, 24, 33), (57, 57, 74), (107, 107, 115), (165, 165, 165), (222, 222, 214), (255, 255, 255),
              (140, 41, 24), (247, 115, 24), (255, 198, 90), (16, 82, 99), (41, 173, 181), (165, 255, 239),
              (99, 57, 41), (181, 115, 66)],
}
C_RUST = [(5, 17, ["#.", "##", ".#"]), (20, 16, [".#.", "###", "#.#", ".#."]), (28, 17, ["#", "#", "#"])]   # blooms: phase, row, shape
C_PLATE = (0, 15, 16)          # deck plate seams (phase)
C_WEAR = {4: 5, 5: 5, 6: 4, 11: 6, 12: 6, 22: 4, 23: 5, 27: 6, 28: 6, 29: 6}     # row 9 clusters: phase -> shade
DITHER_C = [('r1', 'r2')]


def deck(w, f):
    cv = Cv(BOX_H, w)
    R = RC
    for x in range(w):
        mid = 16 <= x < w - 16
        p = (x - 16) % 32 if mid else (x if x < 16 else x - (w - 16))
        loc = (x - 16) % 16
        # deck plate: specular top line, lit plate, seam
        cv.px(x, 8, R['m6'] if not (mid and p in C_PLATE) else R['m4'])
        cv.px(x, 9, R['m%d' % C_WEAR.get(p, 5)] if mid else R['m5'])
        cv.px(x, 10, R['m4'] if (not mid or p % 8) else R['m2'])
        cv.px(x, 11, R['m1'])
        # hazard band on the collision body
        for y in range(12, 16):
            on = ((x + (y - 12)) // 4) % 2 == 0
            c = (R['y3'] if y == 12 else (R['y1'] if y == 15 else R['y2'])) if on else (R['m2'] if y == 12 else R['m1'])
            cv.px(x, y, c)
        if mid:
            # girder web with rivets
            cv.px(x, 16, R['m4'])
            cv.px(x, 17, R['m3'])
            cv.px(x, 18, R['m3'])
            cv.px(x, 19, R['m2'])
            cv.px(x, 20, R['m1'])
            if p % 8 == 3:
                cv.px(x, 17, R['m6'] if p % 16 == 3 else R['m5'])
                cv.px(x, 18, R['m1'])
            if p % 8 == 4:
                cv.px(x, 18, R['m2'])
            if p in (9, 10):                                  # status lamp, tile B only differs here and in the rust
                cv.px(x, 17, R['c3'] if p == 10 else R['c2'])
                cv.px(x, 18, R['c2'] if p == 10 else R['c1'])
            for ph, ry, shape in C_RUST:
                for j, row in enumerate(shape):
                    i = p - ph
                    if 0 <= i < len(row) and row[i] == '#':
                        cv.px(x, ry + j, R['r2'] if (x + ry + j) & 1 else R['r1'])
            # open truss: a V per tile, bottom chord
            if loc < 8:
                cv.px(x, 21 + loc, R['m3'])
                cv.px(x, 22 + loc, R['m2'])
            else:
                cv.px(x, 21 + (15 - loc), R['m5'])
                cv.px(x, 22 + (15 - loc), R['m4'])
            cv.px(x, 28, R['m4'])
            cv.px(x, 29, R['m2'])
            if loc in (7, 8):
                cv.px(x, 27, R['m5'])
                cv.px(x, 28, R['m6'] if loc == 8 else R['m5'])
            if loc in (0, 15):
                cv.px(x, 21, R['m4'])
                cv.px(x, 22, R['m3'])
    for left in (True, False):
        x0 = 0 if left else w - 16

        def X(lx):
            return x0 + (lx if left else 15 - lx)
        # end post joining the truss chord
        for lx in (14, 15):
            for y in range(16, 30):
                cv.px(X(lx), y, R['m4'] if (X(lx) - x0) % 2 == (0 if left else 1) else R['m2'])
            cv.px(X(lx), 16, R['m5'])
        # rotor pod: rounded nacelle
        for y in range(16, 27):
            inset = 2 if y in (16, 26) else (1 if y in (17, 25) else 0)
            for lx in range(2 + inset, 13 - inset):
                xx = X(lx)
                rel = xx - x0
                c = R['m3']
                if y <= 17:
                    c = R['m5'] if y == 16 else R['m4']
                if rel >= 10:
                    c = R['m5'] if y < 23 else R['m4']
                if rel == 11 and 18 <= y <= 21:
                    c = R['m6']
                if rel <= 4:
                    c = R['m2']
                if y >= 24:
                    c = R['m2'] if rel < 10 else R['m3']
                if y == 26:
                    c = R['m1']
                cv.px(xx, y, c)
        for lx, y, c in ((6, 20, 'c1'), (7, 20, 'c1'), (8, 20, 'c1'), (6, 21, 'c1'), (7, 21, 'c2'), (8, 21, 'c3'), (6, 22, 'c1'),
                         (7, 22, 'c2'), (8, 22, 'c2'), (6, 23, 'c1'), (7, 23, 'c1'), (8, 23, 'c1'), (4, 18, 'm5'), (10, 18, 'm5')):
            cv.px(x0 + lx, y, R[c])
        # bollard with a lamp above the deck end
        bx = X(2)
        cv.rect(min(bx, X(4)), 5, max(bx, X(4)), 7, R['m3'])
        cv.px(x0 + (4 if left else 13), 5, R['m5']); cv.px(x0 + (4 if left else 13), 6, R['m5'])
        cv.px(x0 + (2 if left else 11), 6, R['m2']); cv.px(x0 + (2 if left else 11), 7, R['m2'])
        cv.px(x0 + (3 if left else 12), 4, R['c3'])
        cv.px(x0 + (3 if left else 12), 3, R['c2'])
        # shaft and rotor: two blades turning about the vertical axis, seen from the side.
        # Blade length on screen = radius x |cos|; the near blade is bright and thick, the far blade thin and dark.
        cx = x0 + 7
        cv.rect(cx, 27, cx + 1, 28, R['m2'])
        cv.px(cx + 1, 27, R['m4'])
        th = pi * f / NF * (1 if left else -1)
        ext = 6.6 * cos(th)
        n = int(round(abs(ext)))
        sgn = 1 if ext >= 0 else -1
        for i in range(1, n + 1):                           # far blade first
            cv.px(cx + (1 if sgn < 0 else 0) - sgn * i * 1 + (0), 29, R['m3'] if i < n else R['m2'])
        for i in range(1, n + 1):                           # near blade
            xx = cx + (1 if sgn > 0 else 0) + sgn * i
            cv.px(xx, 29, R['m6'] if i > n - 2 else R['m5'])
            cv.px(xx, 30, R['m4'] if i < n else R['m5'])
        cv.rect(cx, 29, cx + 1, 30, R['m5'])
        cv.px(cx, 30, R['m3'])
        if n == 0:                                          # blades edge-on: seen as a short bright stub
            cv.px(cx - 1, 29, R['m4']); cv.px(cx + 2, 29, R['m6'])
    cv.keyline(R['k'])
    return cv.a


OPTS = [
    ('roof', 'A  Roof chunk', roof, RA, PAL_A, [],
     'A brick roof fragment torn loose, stone coping on top, torn brickwork and rebar below, a lantern on a chain under the right end.'),
    ('garden', 'B  Garden slab', garden, RB, PAL_B, DITHER_B,
     'A floating planter: bright turf line, soil with buried stones, a root ball, vines and grass that move in the wind.'),
    ('deck', 'C  Airship deck', deck, RC, PAL_C, DITHER_C,
     'A steel deck plate with a hazard band on a see-through truss, held up by a rotor pod under each end.'),
]
WEAK = {}      # filled from weak.txt style dict at the end of the file (own review notes)


# --------------------------------------------------------------------------------------------------------------
# output helpers
# --------------------------------------------------------------------------------------------------------------
def pal_q(pal):
    return [q5(c) for c in pal]


def to_rgb(a, pal):
    lut = np.array([TRANSP] + pal_q(pal), np.uint8)
    return lut[a]


def blit(dst, a, pal, x, y):
    """Paste a role-index sprite into an RGB array, clipped."""
    h, w = a.shape
    rgb = to_rgb(a, pal)
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, dst.shape[1]), min(y + h, dst.shape[0])
    if x0 >= x1 or y0 >= y1:
        return
    sub = a[y0 - y:y1 - y, x0 - x:x1 - x]
    reg = dst[y0:y1, x0:x1]
    reg[sub > 0] = rgb[y0 - y:y1 - y, x0 - x:x1 - x][sub > 0]


def blit_rgb(dst, src, x, y, flip=False):
    """Paste an RGB sprite with magenta as transparent, clipped."""
    if flip:
        src = src[:, ::-1]
    h, w = src.shape[:2]
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, dst.shape[1]), min(y + h, dst.shape[0])
    if x0 >= x1 or y0 >= y1:
        return
    sub = src[y0 - y:y1 - y, x0 - x:x1 - x]
    m = ~(sub == np.array(TRANSP, np.uint8)).all(2)
    dst[y0:y1, x0:x1][m] = sub[m]


def screen_x(wx):
    sx = (wx - CAM) % ARENA_W
    return sx - ARENA_W if sx >= W else sx


def load_soot():
    out = {}
    for who, fn in (('player', 'sootling_final_sheet_1x.png'), ('cpu', 'sootling_final_sheet_cpu_1x.png')):
        a = np.array(Image.open(os.path.join(SOOTDIR, fn)).convert('RGB'))
        out[who] = lambda n, a=a: a[(n // 8) * 48:(n // 8) * 48 + 48, (n % 8) * 32:(n % 8) * 32 + 32]
    return out


def scene(bg, draw, pal, f, soot):
    """Screen at camera CAM: backdrop (camera 0 art, a mock), the eight stage platforms, two Sootlings."""
    fr = bg.copy()
    for wx, wy, ww in STAGE:
        a = draw(ww, f)
        for sx in (screen_x(wx), screen_x(wx) + ARENA_W, screen_x(wx) - ARENA_W):
            blit(fr, a, pal, sx, wy - TOP)
    # player stands on the centre island (idle, frame 62); computer flier in mid flap (flap2 frame f)
    blit_rgb(fr, soot['player'](62), screen_x(136) + 30, 140 - 48)
    blit_rgb(fr, soot['cpu'](f % 8), 214, 30, flip=True)
    return fr


def save_gif(path, frs, ms, scale=3):
    packed = [(fr[..., 0].astype(np.uint32) << 16) | (fr[..., 1].astype(np.uint32) << 8) | fr[..., 2] for fr in frs]
    cols = np.unique(np.concatenate([np.unique(p) for p in packed]))
    assert len(cols) <= 255, len(cols)
    pal = []
    for c in cols:
        pal += [int(c >> 16) & 255, int(c >> 8) & 255, int(c) & 255]
    pal += [0] * (768 - len(pal))
    ims, prev = [], None
    for p in packed:
        qd = np.searchsorted(cols, p).astype(np.uint8)
        dlt = qd.copy()
        if prev is not None:
            dlt[qd == prev] = 255
        prev = qd
        im = Image.fromarray(up(dlt, scale), 'P')
        im.putpalette(pal)
        ims.append(im)
    ims[0].save(path, save_all=True, append_images=ims[1:], duration=ms, loop=0, disposal=1, transparency=255, optimize=False)


def tiles_of(a):
    """16 x 16 tiles of a platform render cut on the sprite grid from its left edge; empty tiles dropped."""
    h, w = a.shape
    pad = np.zeros((h, int(ceil(w / 16.0)) * 16), np.uint8)
    pad[:, :w] = a
    out = []
    for ty in range(0, h, 16):
        for tx in range(0, pad.shape[1], 16):
            t = pad[ty:ty + 16, tx:tx + 16]
            if t.any():
                out.append(t)
    return out


def uniq(tiles, flips):
    seen = set()
    for t in tiles:
        keys = [t.tobytes()]
        if flips:
            keys += [t[:, ::-1].tobytes(), t[::-1].tobytes(), t[::-1, ::-1].tobytes()]
        if not any(k in seen for k in keys):
            seen.add(keys[0])
    return len(seen)


def line_load(box_h, anchor, skip=()):
    """Platform sprites per scanline: every 16 px strip of every island counts on each line its tile rows cover
    (the hardware counts by Y overlap, whatever the X). Returns (worst count, first line, last line)."""
    cnt = [0] * H
    for i, (wx, wy, ww) in enumerate(STAGE):
        hh = 16 if i in skip else box_h
        for y in range(wy - anchor, wy - anchor + hh):
            if 0 <= y < H:
                cnt[y] += int(ceil(ww / 16.0))
    m = max(cnt)
    ys = [y for y in range(H) if cnt[y] == m]
    return m, ys[0], ys[-1]


def contrast(bg, draw, pal, mood):
    """Luminance step of the standing line against the backdrop pixel right above it, and of the lowest
    opaque pixel of each column against the backdrop pixel right below it."""
    L = (0.299 * bg[..., 0] + 0.587 * bg[..., 1] + 0.114 * bg[..., 2])
    top, und = [], []
    pq = pal_q(pal)
    for wx, wy, ww in STAGE:
        a = draw(ww, 0)
        sx = screen_x(wx)
        for x in range(ww):
            if not 0 <= sx + x < W:
                continue
            top.append(abs(lum(pq[a[TOP, x] - 1]) - L[wy - 1, sx + x]))
            col = np.nonzero(a[TOP:, x])[0]
            yb = TOP + col[-1]
            if wy - TOP + yb + 1 < H:
                und.append(abs(lum(pq[a[yb, x] - 1]) - L[wy - TOP + yb + 1, sx + x]))
    top, und = np.array(top), np.array(und)
    return ('%s: standing line against the backdrop above it: mean %d, p10 %d, under 24: %d%%; lower edge against the backdrop below: '
            'mean %d, p10 %d, under 24: %d%%' % (mood, top.mean(), np.percentile(top, 10), 100 * (top < 24).mean(),
                                                und.mean(), np.percentile(und, 10), 100 * (und < 24).mean()))


def main():
    bgs = {m: np.array(Image.open(os.path.join(BGDIR, 'scene_%s_1x.png' % m)).convert('RGB')) for m in MOODS}
    soot = load_soot()
    num = ['Gumbirds islands, draft round 1: numbers (script output)',
           'box: width x 32 px; standing line at row 8 (stage y); rows 0..7 above the line, 8..15 collision body, 16..31 underside',
           'stage widths (src/core/stage.c): 80, 80, 112, 80, 80, 96, 56, 56; 16 px strips: 5, 5, 7, 5, 5, 6, 4, 4 = 41 sprites in all',
           'animation: %d frames, shown at 110 ms a frame in the GIFs' % NF, '']
    m2, a2, b2 = line_load(32, TOP)
    m1, a1, b1 = line_load(32, TOP, skip=(2,))
    m0, a0, b0 = line_load(16, 0)
    num += ['sprites per scanline, platforms only (same for all three options; gameplay reserve SB_GAMEPLAY_PER_LINE = 24):',
            '  every island two tiles tall (box rows 0..31 = stage y-8 .. y+23): worst line %d sprites, lines %d..%d' % (m2, a2, b2),
            '    (the y 140 island, 7 strips, overlaps the two y 164 islands, 10 strips, because 164 - 140 = 24 < 32)',
            '  centre island (y 140) one tile tall, others two: worst line %d, lines %d..%d' % (m1, a1, b1),
            '  every island one tile tall (no underside, rows 8..23 only): worst line %d, lines %d..%d' % (m0, a0, b0),
            '  8 two-column Sootlings on one line are 16 sprites: 16 + %d = %d of 24 in the layout as it is, 16 + %d = %d with the centre island thin or moved 8 px up'
            % (m2, 16 + m2, m1, 16 + m1), '']
    html_opts = []
    for key, title, draw, R, PAL, dith, blurb in OPTS:
        names = sorted(R, key=R.get)
        num.append('=== %s (%s)' % (title, key))
        num.append('palettes: 1 on screen (15 colours + transparent), 3 in ROM as mood swaps of the same tiles; role order 1..15: ' + ' '.join(names))
        used = set()
        stat, anim = [], []
        for ww in sorted(set(s[2] for s in STAGE)):
            fr0 = draw(ww, 0)
            stat += tiles_of(fr0)
            for f in range(NF):
                a = draw(ww, f)
                used |= set(np.unique(a).tolist())
                anim += tiles_of(a)
        n16 = []
        for ww in (80, 96, 112):
            for f in range(NF):
                n16 += tiles_of(draw(ww, f))
        num.append('colours used: %d of 15' % (len(used - {0})))
        num.append('unique 16x16 tiles, all four stage widths (56, 80, 96, 112), all %d frames: %d without flips, %d with flips; frame 0 alone: %d'
                   % (NF, uniq(anim, False), uniq(anim, True), uniq(stat, False)))
        num.append('  of these the 56 px islands (3.5 tiles, right cap off the tile grid) cost %d tiles; widths 80, 96, 112 alone: %d'
                   % (uniq(anim, False) - uniq(n16, False), uniq(n16, False)))
        for mood in MOODS:
            pq = pal_q(PAL[mood])
            assert len(set(pq)) == 15, (key, mood)
            num.append('palette %s RGB: ' % mood + ' '.join('%s=(%d,%d,%d)' % ((n,) + pq[R[n] - 1]) for n in names))
            num.append('palette %s luminance: ' % mood + ' '.join('%s=%d' % (n, lum(pq[R[n] - 1])) for n in names))
        if dith:
            for a_, b_ in dith:
                steps = [abs(lum(pal_q(PAL[m])[R[a_] - 1]) - lum(pal_q(PAL[m])[R[b_] - 1])) for m in MOODS]
                assert min(steps) >= 28, (key, a_, b_, steps)
                num.append('dither pair %s/%s luminance step: moon %d, dusk %d, storm %d (rule: at least 28)' % ((a_, b_) + tuple(steps)))
        else:
            num.append('dither: none (stone, brick and iron only)')
        for mood in MOODS:
            num.append('contrast ' + contrast(bgs[mood], draw, PAL[mood], mood))
        num.append('')
        # sheets
        for mood in MOODS:
            sh = np.zeros((96, 128), np.uint8)
            p64 = draw(64, 0)
            sh[0:32, 0:64] = p64
            for f in range(NF):
                a = draw(64, f)
                sh[32:64, f * 16:f * 16 + 16] = a[:, 0:16]
                sh[64:96, f * 16:f * 16 + 16] = a[:, 48:64]
            Image.fromarray(to_rgb(sh, PAL[mood]), 'RGB').save(os.path.join(HERE, 'sheet_%s_%s_1x.png' % (key, mood)))
            fr = scene(bgs[mood], draw, PAL[mood], 2, soot)
            Image.fromarray(up(fr, 3), 'RGB').save(os.path.join(HERE, 'scene_%s_%s_3x.png' % (key, mood)))
        # zoom: the centre island on each backdrop, 6x
        zs = []
        for mood in MOODS:
            fr = scene(bgs[mood], draw, PAL[mood], 2, soot)
            zs.append(up(fr[124:176, 96:224], 6))
        Image.fromarray(np.concatenate(zs, 0), 'RGB').save(os.path.join(HERE, 'zoom_%s_6x.png' % key))
        # 1x strip of the three moods for the honest small view
        Image.fromarray(np.concatenate([scene(bgs[m], draw, PAL[m], 2, soot) for m in MOODS], 1), 'RGB').save(
            os.path.join(HERE, 'moods_%s_1x.png' % key))
        save_gif(os.path.join(HERE, 'anim_%s_3x.gif' % key), [scene(bgs['moon'], draw, PAL['moon'], f, soot) for f in range(NF)], 110)
        html_opts.append((key, title, blurb, uniq(anim, False), m2))
    with open(os.path.join(HERE, 'numbers.txt'), 'w') as fh:
        fh.write('\n'.join(num) + '\n')
    write_html(html_opts)
    print('\n'.join(l for l in num if l.startswith(('===', 'unique', '  of these', 'colours', 'dither', 'contrast', '  every', '  centre'))))


WEAK = {
    'roof': 'Weak point: the torn lower edge is an even sawtooth and the brick face reads flat at true size; only the right end has motion.',
    'garden': 'Weak point: the buried stones and blossoms repeat every 32 px and show as a pattern; it costs the most tiles, and the storm soil sits close to the building greys.',
    'deck': 'Weak point: the backdrop shows through the open truss, so the lower half reads less solid, and it is the option closest in material to the city scenery; the rotors are small at true size.',
}


def write_html(opts):
    h = ['<!doctype html><html><head><meta charset="utf-8"><title>Gumbirds islands, draft round 1</title><style>',
         'body{background:#15161b;color:#d8d9df;font-family:Helvetica,Arial,sans-serif;margin:24px}',
         'img{image-rendering:pixelated;max-width:none;display:block;margin:8px 0 16px 0}',
         'h2{margin-top:40px;border-top:1px solid #3a3c46;padding-top:16px}p{max-width:940px;line-height:1.4}',
         '.row{display:flex;gap:24px;align-items:flex-start}.col{flex:0 0 auto}.weak{color:#ffb86b}',
         '</style></head><body>',
         '<h1>Gumbirds islands, draft round 1</h1>',
         '<p>View at 100 percent browser zoom. Drafts only, nothing is in the game. Three options for the platforms, each drawn at the '
         'eight positions and widths of the stage table in the code, camera at 32 px so both seam islands show. The backdrop is the '
         'camera 0 picture of the final background pass, so the parallax offset is not exact. A player Sootling stands on the centre '
         'island, a computer Sootling flies above it. Numbers are in <a href="numbers.txt" style="color:#8ecbff">numbers.txt</a>, '
         'own choices in <a href="README.md" style="color:#8ecbff">README.md</a>.</p>',
         '<h2>Side by side, 1x (true size), all three moods</h2><div class="row">']
    for key, title, blurb, nt, wl in opts:
        h.append('<div class="col"><h3>%s</h3><p style="max-width:300px">%s</p><p class="weak" style="max-width:300px">%s</p>' % (title, blurb, WEAK[key]))
        h.append('<img src="moods_%s_1x.png" width="320" height="75" style="width:320px;height:auto" alt="%s three moods small">' % (key, key))
        h.append('<p style="max-width:300px">%d unique tiles, 1 palette on screen, %d platform sprites on the worst line.</p></div>' % (nt, wl))
    h.append('</div>')
    h.append('<h2>Close view, centre island, 6x: moon, dusk, storm</h2><div class="row">')
    for key, title, blurb, nt, wl in opts:
        h.append('<div class="col"><h3>%s</h3><img src="zoom_%s_6x.png" width="384" height="468" alt="%s zoom"></div>' % (title, key, key))
    h.append('</div><p>Shown at half of the 6x file so the three fit side by side.</p>')
    h.append('<h2>Motion, moon, 3x</h2>')
    for key, title, blurb, nt, wl in opts:
        h.append('<h3>%s</h3><img src="anim_%s_3x.gif" width="960" height="672" alt="%s animation">' % (title, key, key))
    for mood in MOODS:
        h.append('<h2>%s, 3x</h2>' % MOODNAME[mood])
        for key, title, blurb, nt, wl in opts:
            h.append('<h3>%s</h3><img src="scene_%s_%s_3x.png" width="960" height="672" alt="%s %s">' % (title, key, mood, key, mood))
    h.append('<h2>Build sheets, shown at 4x (files are 1x, transparent colour magenta 255, 0, 255)</h2>'
             '<p>Row 1: left cap, middle A, middle B, right cap. Row 2: the eight frames of the left cap. Row 3: the eight frames of the right cap.</p>')
    for key, title, blurb, nt, wl in opts:
        h.append('<h3>%s</h3><div class="row">' % title)
        for mood in MOODS:
            h.append('<div class="col"><p>%s</p><img src="sheet_%s_%s_1x.png" width="512" height="384" alt="sheet %s %s"></div>' % (mood, key, mood, key, mood))
        h.append('</div>')
    h.append('</body></html>')
    with open(os.path.join(HERE, 'index.html'), 'w') as fh:
        fh.write('\n'.join(h) + '\n')


if __name__ == '__main__':
    main()
