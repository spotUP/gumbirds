#!/opt/homebrew/bin/python3.14 -I
"""Background drafts, final pass for Bubblegum Brawl (five fixes on v3): sky tile plane + 6 city depth planes, three moods.

Run:  /opt/homebrew/bin/python3.14 -I draw_backgrounds_final.py [--nogif] [--only moon,storm,dusk]
Writes scene_*, planes_*, compare_*, anim_* files, index.html and numbers.txt next to this script.
Draft only: nothing here is game data. The city planes are drawn once as role-index art; a mood is a palette set
(plus its own sky plane and one mood extra). Hazard strips are read from the accepted dither drafts.
"""
import os
import sys
import random
from math import sin, cos, pi, sqrt, ceil
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
HAZDIR = os.path.join(HERE, '..', '2026-11-10-dither-s6-strong')
V1DIR = os.path.join(HERE, '..', '2026-11-10-backgrounds-v1')
V2DIR = os.path.join(HERE, '..', '2026-11-10-backgrounds-v2')
V3DIR = os.path.join(HERE, '..', '2026-11-10-backgrounds-v3')
TRANSP = (255, 0, 255)      # transparent colour of the per-plane build sheets
W, H = 320, 224
PW, OFF = 336, 8            # swaying planes are 21 tiles wide; screen x = plane x - OFF + sway
HAZ_Y = 192
NFR = {'moon': 80, 'dusk': 80, 'storm': 64}     # GIF frames per loop (multiples of 16 hazard steps), sized to stay under 3 MB
TAU = 2 * pi
RING_DX = 0                 # endless: x shift of the wrap copy being drawn (0 = home position)
FAR_LIT_FROM = 'right'      # relit: lit side of every far tower, moon, dusk and storm (see building())


def lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def mix(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def setlum(c, L):
    """Colour with the hue of c and luminance L (scaled; blended toward white where a channel would clip)."""
    k = L / max(lum(c), 1e-6)
    if max(c) * k <= 255:
        return tuple(int(round(v * k)) for v in c)
    s = [v * 255.0 / max(c) for v in c]
    t = (L - lum(s)) / max(255 - lum(s), 1e-6)
    return tuple(int(round(v + (255 - v) * min(max(t, 0), 1))) for v in s)


def lum_ramp(anchors, targets):
    """Colours at the target luminances on the hue-shifted path through the anchor colours."""
    ls = [lum(a) for a in anchors]
    out = []
    for L in targets:
        i = 0
        while i < len(ls) - 2 and L > ls[i + 1]:
            i += 1
        t = (L - ls[i]) / (ls[i + 1] - ls[i])
        out.append(mix(anchors[i], anchors[i + 1], min(max(t, 0), 1)))
    return out


# ---------------------------------------------------------------- roles (index art) and canvas
ROLES = ['.']
RID = {}


def rid(n):
    if n not in RID:
        RID[n] = len(ROLES)
        ROLES.append(n)
    return RID[n]


class Rl:
    def __init__(s, p):
        s.p = p

    def __getattr__(s, k):
        return rid(s.p + '.' + k)


ORDER = [0, 4, 2, 6, 1, 5, 3, 7]


def streak_map(h, w, seed, lens=(2, 3, 3, 4, 4, 5, 6), wrap=False):
    """Threshold map made of horizontal dashes of uneven length (hand-cluster look), 8 levels."""
    rng = random.Random(seed)
    T = np.zeros((h, w))
    k = rng.randrange(8)
    for y in range(h):
        x = 0 if wrap else -rng.randrange(4)
        k += rng.choice((1, 2, 3))
        while x < w:
            L = rng.choice(lens)
            if wrap and w - (x + L) < 2:
                L = w - x
            T[y, max(x, 0):x + L] = (ORDER[(k * 3) % 8] + 0.5) / 8
            k += 1
            x += L
    return T


CL16 = streak_map(16, 16, 7, lens=(2, 2, 3, 3, 4), wrap=True)     # period 16: tile-safe on city planes


class Cv:
    def __init__(s, h, w):
        s.a = np.zeros((h, w), np.uint8)
        s.da = np.zeros((h, w), np.uint8)       # dither pair marks (role ids), 0 = not a dither pixel
        s.db = np.zeros((h, w), np.uint8)
        s.h, s.w = h, w

    def rect(s, x0, y0, x1, y1, c):
        x0, y0, x1, y1 = max(int(x0), 0), max(int(y0), 0), min(int(x1), s.w), min(int(y1), s.h)
        if x1 > x0 and y1 > y0:
            s.a[y0:y1, x0:x1] = c
            s.da[y0:y1, x0:x1] = 0

    def px(s, x, y, c):
        x, y = int(x), int(y)
        if 0 <= x < s.w and 0 <= y < s.h:
            s.a[y, x] = c
            s.da[y, x] = 0

    def setm(s, m, c):
        s.a[m] = c
        s.da[m] = 0

    def disc(s, cx, cy, r, c):
        yy, xx = np.mgrid[0:s.h, 0:s.w]
        s.setm((xx - cx) ** 2 + (yy - cy) ** 2 <= r * r, c)

    def dith(s, m, dens, ca, cb, T=None, steps=8):
        """Inside mask m: mix ca (dens 0) and cb (dens 1), density quantised to `steps` levels."""
        if T is None:
            T = np.tile(CL16, (s.h // 16 + 1, s.w // 16 + 1))[:s.h, :s.w]
        q = np.round(np.clip(dens, 0, 1) * steps) / steps
        on = q > T
        s.a[m & on] = cb
        s.a[m & ~on] = ca
        z = m & (q > 0) & (q < 1)
        s.da[m] = 0
        s.da[z] = ca
        s.db[z] = cb

    def box(s, y0, y1):
        return np.zeros((s.h, s.w), bool)


def grid(h, w):
    return np.mgrid[0:h, 0:w]


# ---------------------------------------------------------------- roof furniture (shared by city planes)
def antenna(cv, R, x, base, h, ph, f):
    cv.rect(x, base - h, x + 1, base, R.w3)
    for q in (h // 3, 2 * h // 3):
        cv.rect(x - 1, base - q, x + 2, base - q + 1, R.w1)
    cv.px(x, base - h - 1, R.bk if (f - ph) % 8 in (0, 1) else R.bd)


def tank(cv, R, x, base, k):
    tw, th, lg, rf = 5 + 3 * k, 4 + 2 * k, 2 + 2 * k, 2 + k
    ty = base - lg - th
    for lx in (x + 1, x + tw // 2, x + tw - 2):
        cv.rect(lx, base - lg, lx + 1, base, R.w0)
    cv.rect(x + 1, base - lg // 2 - 1, x + tw - 1, base - lg // 2, R.w1)
    for i in range(tw):
        p = i / (tw - 1)
        c = R.w0 if p < 0.06 else R.w1 if p < 0.34 else R.w2 if p < 0.62 else R.w3 if p < 0.8 else R.w4 if p < 0.9 else R.w3 if p < 0.97 else R.w1
        cv.rect(x + i, ty, x + i + 1, ty + th, c)
    for hy in range(ty + 2, ty + th - 1, 3 if k < 3 else 4):
        cv.rect(x + 1, hy, x + tw - 1, hy + 1, R.w1)
        cv.px(x + int(tw * 0.84), hy, R.w3)
    cv.rect(x, ty + th, x + tw, ty + th + 1, R.w0)
    for j in range(rf):
        hw = int((j + 1) * (tw / 2 + 1) / rf)
        cx = x + tw // 2
        cv.rect(cx - hw, ty - rf + j, cx, ty - rf + j + 1, R.w1)
        cv.rect(cx, ty - rf + j, cx + hw, ty - rf + j + 1, R.w3)
        cv.px(cx + hw - 1, ty - rf + j, R.w4)
    cv.px(x + tw // 2, ty - rf - 1, R.w4)


def plume(cv, R, cx, cy, f, rise, spread, rmax, ymin):
    yy, xx = grid(cv.h, cv.w)
    for i in range(4):
        age = (f / 8 + i / 4) % 1
        px_ = cx + spread * age + sin(age * 7 + i * 2.1) * 1.2
        py_ = cy - rise * age - 1
        r = 1.2 + rmax * age ** 0.7
        d = np.sqrt((xx - px_) ** 2 + ((yy - py_) * 1.15) ** 2)
        ok = yy >= ymin
        if age < 0.3:
            cv.setm((d <= r) & ok, R.s2)
            cv.setm((d <= r * 0.55) & (xx >= px_ - 0.5) & ok, R.s1)
        elif age < 0.7:
            cv.setm((d <= r) & (((xx + yy) & 1) == 0) & ok, R.s2)            # checker mesh
            cv.setm((d <= r * 0.5) & ok, R.s2)
        else:
            cv.setm((d <= r) & ((xx & 1) == 0) & (((yy + xx // 2) & 1) == 0) & ok, R.s2)   # quarter mesh


def chimney(cv, R, x, base, w, h, f, rise, ymin):
    cv.rect(x, base - h, x + w, base, R.w1)
    cv.rect(x + w - max(1, w // 3), base - h, x + w, base, R.w3)
    cv.rect(x - 1, base - h - 1, x + w + 1, base - h, R.w4)
    cv.rect(x - 1, base - h, x + w + 1, base - h + 1, R.w0)
    plume(cv, R, x + w / 2, base - h - 1, f, rise, rise * 0.45, 1.5 + rise * 0.22, ymin)


def billboard(cv, R, x, base, k, f):
    bw, bh, lg = 10 + 8 * k, 5 + 4 * k, 2 + k
    by = base - lg - bh
    for lx in (x + 2, x + bw - 3):
        cv.rect(lx, base - lg, lx + 1, base, R.w0)
    cv.rect(x, by, x + bw, by + bh, R.w0)
    cv.rect(x, by - 1, x + bw, by, R.w4)
    cv.rect(x + 1, by + 1, x + bw - 1, by + bh - 1, R.n3)
    cyc = by + bh // 2
    r = bh // 2 - 2
    yy, xx = grid(cv.h, cv.w)
    d = np.sqrt((xx - (x + bw // 2)) ** 2 + (yy - cyc) ** 2)
    cv.setm(d <= r, R.n2)
    cv.setm((d <= r) & (xx - yy < x + bw // 2 - cyc), R.n1)
    cv.px(x + bw // 2 - r // 2, cyc - r // 2, R.l3)
    i = 0                                               # chasing bulbs on the frame
    for bx in range(x + 1, x + bw - 1, 2):
        for byy in (by + 1, by + bh - 2):
            cv.px(bx, byy, R.l3 if (i + f) % 4 == 0 else R.l2)
            i += 1


def chevrons(cv, R, x, top, f):
    cv.rect(x, top, x + 9, top + 23, R.w0)
    cv.rect(x, top, x + 9, top + 1, R.w3)
    for j in range(3):
        c = R.c1 if (f % 4 == j or f % 4 == 3) else R.c2
        y = top + 3 + j * 6
        for i in range(4):
            cv.px(x + 1 + i, y + i, c)
            cv.px(x + 7 - i, y + i, c)
            cv.px(x + 1 + i, y + i + 1, c)
            cv.px(x + 7 - i, y + i + 1, c)


def flag(cv, R, x, base, h, f):
    cv.rect(x, base - h, x + 1, base, R.w3)
    cv.px(x, base - h - 1, R.w4)
    for i in range(9):
        dy = int(round(1.2 * sin(i * 0.9 - f * pi / 2)))
        for j in range(5):
            cv.px(x + 1 + i, base - h + j + dy, R.fl1 if (j < 2 or (i + f) % 4 > 1) and j < 4 else R.fl2)


def fan(cv, R, x, base, f):
    cv.rect(x, base - 9, x + 13, base, R.w1)
    cv.rect(x, base - 10, x + 13, base - 9, R.w4)
    cv.rect(x + 11, base - 9, x + 13, base, R.w3)
    cv.rect(x, base - 1, x + 13, base, R.uh)
    cx, cy = x + 5, base - 5
    yy, xx = grid(cv.h, cv.w)
    cv.setm((xx - cx) ** 2 + (yy - cy) ** 2 <= 12, R.w0)
    th = f * pi / 8
    for t in (-3, -2, -1, 1, 2, 3):
        cv.px(cx + round(t * cos(th)), cy + round(t * sin(th)), R.w4 if t > 0 else R.w3)
        cv.px(cx - round(t * sin(th)), cy + round(t * cos(th)), R.w3 if t > 0 else R.w2)
    cv.px(cx, cy, R.w4)


# ---------------------------------------------------------------- generic building
class St:
    def __init__(s, **k):
        s.__dict__.update(k)


def window(cv, R, st, wx, wy, state, f, ph):
    gx, gy, ww, wh = st.grid
    if state == 4:
        state = 1 if (f + ph) % 8 < 4 else 0
    if state == 0:
        cv.rect(wx, wy, wx + ww, wy + wh, R.wo)
        if wh >= 4:
            cv.rect(wx, wy + wh, wx + ww, wy + wh + 1, R.w3)
    elif state in (1, 2):
        cv.rect(wx, wy, wx + ww, wy + wh, R.l1 if state == 1 else R.l2)
        if wh >= 3:
            cv.rect(wx, wy, wx + ww, wy + 1, R.l2 if state == 1 else R.wo)
        if wh >= 4:
            if state == 1:
                cv.px(wx, wy + 1, R.l3)
            cv.rect(wx, wy + wh, wx + ww, wy + wh + 1, R.w0)
    else:
        cv.rect(wx, wy, wx + ww, wy + wh, (R.t1, R.t2, R.t1, R.wo)[(f + ph) % 4])
        if wh >= 3:
            cv.rect(wx, wy + wh - 1, wx + ww, wy + wh, R.t2)


# hand-set lit patterns of the facade types ('#' warm lit, '+' dim lit, '.' dark)
OFFICE_LIT = [("##..#...", "........", "..###..#", "#.......", "....+##.", "........", ".#....#+"),
              ("....##..", "#+......", "........", "..#..###", ".....+..", "##......")]
DECO_LIT = [("#..", ".#.", ".#.", "..+", "#..", "...", ".##"), ("..#", "..#", "+..", ".#.", "...", "#.#")]
WARE_LIT = ["#..", "...", ".#.", "..#", "..."]
WARE_RUNS = [(1, 5), (8, 3), (2, 7), (11, 4), (0, 3), (6, 6)]
GLASS_LIT = [[(1, 2), (2, 2), (0, 5), (3, 7), (1, 9)], [(0, 1), (2, 4), (1, 6), (2, 6), (0, 10)]]


def facade(cv, R, st, x, w, top, bot, seed, f, ft, kind):
    """Hand-designed facade types other than the apartment grid: office ribbons, deco piers, brick warehouse, curtain glass."""
    gx, gy, ww, wh = st.grid
    k = st.k
    x1 = x + w
    xl, xr = x + 2, x1 - st.side - 1
    dk = R.w0 if st.far else R.wo               # final: far openings in the darkest wall colour, readable on both faces
    if st.far:
        bot = min(bot, FARLIM)
    y = top + (3 if k < 2 else 6)
    if ft == 'office':
        pat = OFFICE_LIT[seed % 2]
        rh = 2 if st.far else wh                # final: far office = bold ribbon bands, 2 px, pitch 5
        row = 0
        if st.far:
            xl, xr = x + 1, x1 - 1
        while y + rh + 1 < bot:
            cv.rect(xl, y, xr, y + rh, dk)
            for sg, sx in enumerate(range(xl, xr - 1, gx)):
                ch = pat[row % len(pat)][sg % 8]
                e = min(sx + gx - 1, xr)
                if ch != '.':
                    cv.rect(sx, y, e, y + rh, R.l1 if ch == '#' else R.l2)
                    if rh >= 3:
                        cv.rect(sx, y, e, y + 1, R.l2)
            if rh >= 3:
                cv.rect(xl, y + rh, xr, y + rh + 1, R.w3)
            y += gy + (1 if st.far else 0)
            row += 1
        if kind == 'flat' and not st.far:                       # roof sign: lit letter blocks, one chasing
            n = 5
            sx0 = x + w // 2 - n * (2 + k) // 2
            for i in range(n):
                sx = sx0 + i * (2 + k)
                cv.rect(sx, top - 3 - k, sx + 1 + k, top - 1, R.l3 if (i + f // 2) % n == 0 else R.l2)
            cv.rect(sx0 - 1, top - 1, sx0 + n * (2 + k), top, R.w0)
    elif ft == 'deco':
        pat = DECO_LIT[seed % 2]
        if not st.far:
            for dx in range(x + 1, x1 - 1, 2):
                cv.px(dx, top + 2 + (k >= 2), R.w1)             # dentils under the cornice
        y += 1
        col = 0
        for px_ in range(xl, xr - ww + 1, gx):
            if not st.far and px_ + ww < xr:
                cv.rect(px_ + ww, y, px_ + ww + 1, bot, R.w3)   # pier with a lit edge
            yq, fl = y, 0
            while yq + gy - 1 < bot:
                ch = pat[fl % len(pat)][col % 3]
                cv.rect(px_, yq, px_ + ww, yq + gy - (0 if st.far and ch == '.' else 1),      # final: far deco = unbroken slits
                        R.l1 if ch == '#' else R.l2 if ch == '+' else dk)
                if ch == '#' and gy >= 5:
                    cv.rect(px_, yq, px_ + ww, yq + 1, R.l2)
                yq += gy
                fl += 1
            col += 1
        if not st.far:                                          # neon blade sign, blocks chase
            bx = xr - 2 - k
            cv.rect(bx, y + gy - 1, xr, y + 4 * gy, R.n3)
            for j in range(3):
                yb = y + gy + j * gy
                cv.rect(bx + 1, yb, xr - 1, yb + gy - 2, R.n1 if (j + f // 2) % 3 else R.n2)
        if kind == 'flat':
            cv.rect(x + w // 2, top - 3 - 2 * k, x + w // 2 + 1, top, R.w3)
    elif ft == 'ware':
        bw = 2 * ww + 1
        n = max(1, (xr - xl) // (bw + gx))
        sp = (xr - xl - n * bw) // (n + 1)
        y += 1
        fl = 0
        while y + wh + 2 < bot:
            if not st.far:
                o, L = WARE_RUNS[(fl + seed) % len(WARE_RUNS)]
                cv.rect(min(xl + o * ww, xr - 2), y - 2, min(xl + (o + L) * ww, xr), y - 1, R.w1)      # a run of mortar
            if fl == 1 and not st.far:                          # painted wall sign with block letters
                cv.rect(xl + 1, y - 1, xr - 1, y + wh + 2, R.n3)
                cv.rect(xl + 2, y, xr - 2, y + 1, R.n2)
                for i, sx in enumerate(range(xl + 3, xr - 3 - k, 2 + k)):
                    cv.rect(sx, y + 2, sx + k, y + wh + 1, R.n1 if i % 3 == 0 else R.n2)
            else:
                for i in range(n):
                    wx = xl + sp + i * (bw + sp)
                    lit = WARE_LIT[(seed + fl) % len(WARE_LIT)][i % 3] == '#'
                    cv.rect(wx, y, wx + bw, y + wh + 1, R.l1 if lit else dk)
                    if lit:
                        cv.rect(wx, y, wx + bw, y + 1, R.l2)
                        cv.rect(wx + ww, y, wx + ww + 1, y + wh + 1, R.l2)
                    if not st.far:
                        cv.rect(wx - 1, y + wh + 1, wx + bw + 1, y + wh + 2, R.w3)
                        cv.rect(wx - 1, y - 1, wx + bw + 1, y, R.w0)
            y += gy + wh + 1
            fl += 1
        if not st.far:
            for dx in range(x + 1, x1 - 2, 4):
                cv.rect(dx, top - 1, dx + 2, top, R.w3)         # crenels
    else:                                                       # curtain glass: flat reflection bands, mullion grid
        for yq in range(top + 2, bot):
            for b in (0, 1):
                xs = xr - 4 - (yq - top) // 2 + b * (w // 2 + 3)
                cv.rect(max(xs, xl), yq, max(min(xs + 2 + k, xr), xl), yq + 1, R.w3)
        for yq in range(y + gy - 1, bot, gy):
            cv.rect(xl, yq, xr, yq + 1, R.w1)
        if not st.far:
            for xq in range(xl + gx - 1, xr, gx):
                cv.rect(xq, top + 2, xq + 1, bot, R.w1)
        for c, r in GLASS_LIT[seed % 2]:
            wx, wy = xl + c * gx, y + r * gy
            if wx + gx - 1 <= xr and wy + gy - 1 < bot:
                cv.rect(wx, wy, wx + gx - 1, wy + gy - 1, R.l2)


# final mid plane walls: drawn material, no dither, sized to read at 1x. Hand-set tables.
FARLIM = 118                                                          # far facade openings stop here (haze and mid planes below)
SHSTEP = [0, 2, -1, 3, 1, -2, 2, 0]                                   # start height of the canyon shadow per building
DRIPS = [(3, 6), (9, 4), (15, 8), (22, 5), (29, 7), (36, 4)]          # stain drips under the cornice: (x offset, length)
PATCHES = [(0.30, 10, 7, 4), (0.72, 23, 8, 5), (0.26, 36, 6, 4)]      # exposed brick: (x share, y offset, half width, half height)
PIPEX = [11, 4, 9, 13, 6]                                             # drain pipe position in sixteenths of the width


def material(cv, R, st, x, x1, top, bot, seed, ft):
    """Mid plane wall: flat wall colour, a flat street-canyon shadow below a clean stepped edge, a flat form shadow on
    the left. Material is drawn counterchanged: dark line on the lit wall, light line on the shadow wall, so it reads
    over the whole facade. Few, large features: brick courses 4 or 5 px, panel seams, stone blocks, wide stains."""
    k = st.k
    w = x1 - x
    xa, xb = max(x, 0), min(x1, cv.w)
    if xb <= xa:
        return
    gx, gy, ww, wh = st.grid
    cap = st.haze[0] + 10
    ys = top + st.g0 + 3 + SHSTEP[seed % 8]
    for xq in range(xa, xb):
        e = max(min(ys + (xq - x) // 3, cap), top + 1)
        cv.rect(xq, e, xq + 1, bot, R.w1)
    cv.rect(x, top, x + 1 + k, bot, R.w1)
    w1, w2, w3 = R.w1, R.w2, R.w3

    def ink(x0, y0, xe, ye, c=w1):
        x0, y0, xe, ye = max(x0, xa + 1 + k), max(y0, top + 2), min(xe, xb - st.side), min(ye, bot, cv.h)
        if xe > x0 and ye > y0:
            sl = cv.a[y0:ye, x0:xe]
            lit, sh = sl == w2, sl == w1
            sl[lit] = c
            if c == w1:
                sl[sh] = w2

    bl, bh = (8, 4) if k == 1 else (10, 5)

    def brick(x0, y0, xe, ye):
        for yq in range(y0, ye):
            if (yq - top) % bh == 0:
                ink(x0, yq, xe, yq + 1)
            else:
                o = bl // 2 if ((yq - top) // bh) % 2 else 0
                for bx in range(x + o + 1, xe, bl):
                    if bx >= x0:
                        ink(bx, yq, bx + 1, yq + 1)

    if ft == 'ware':
        brick(x + 1, top + 3, x1, bot)
        for i, (fx, oy, hw, hh) in enumerate(PATCHES):          # a few lit bricks
            bx = x + 2 + (int(w * fx) // bl) * bl + (bl // 2 if ((oy + 3 * i) // bh) % 2 else 0)
            by = top + ((oy + 3 * i) // bh) * bh + 1
            ink(bx, by, bx + bl - 1, by + bh - 1, w3)
    elif ft == 'apt':
        for i, (fx, oy, hw, hh) in enumerate(PATCHES):          # render fallen off: brick shows in stepped patches
            if (i + seed) % 3 == 2:
                continue
            cx_, cy_ = x + int(w * fx), top + oy * (k + 1) // 3 + 3
            for dy in range(-hh, hh + 1):
                half = hw + 1 - abs(dy) + SHSTEP[(dy + seed + i) % 8] // 2
                brick(cx_ - half, cy_ + dy, cx_ + half + 1, cy_ + dy + 1)
    elif ft == 'office':
        for sx in range(x + 1 + 3 * gx, x1 - st.side - 2, 3 * gx):
            ink(sx + 1, top + 3, sx + 2, bot, w3)               # lit seam edge
            ink(sx, top + 3, sx + 1, bot)                       # panel seam
    elif ft == 'deco':
        for j, yq in enumerate(range(top + 5, bot, 4 * k + 2)):  # stone joints
            ink(x + 1, yq, x1, yq + 1)
            for bx in range(x + 2 + (4 if j % 2 else 0), x1, 8 + 2 * k):
                ink(bx, yq + 1, bx + 1, yq + 4 * k + 2)
    if ft in ('apt', 'office'):
        for i, (dx, n) in enumerate(DRIPS):
            if (i + seed) % 3 == 0 and dx < w - 4:
                ink(x + dx, top + 2, x + dx + 2, top + 2 + n + 3 * (k - 1))
                ink(x + dx + 2, top + 2, x + dx + 3, top + n - 1)


def pipe(cv, R, st, x, x1, top, bot, seed, ft):
    """Drain pipe in front of the facade (mid planes only): 2 px lit pipe, hopper head, wide wall brackets."""
    if not st.glen or ft in ('glass', 'deco') or x1 - x < 20 or bot - top < 20:
        return
    k = st.k
    px_ = x + PIPEX[seed % len(PIPEX)] * (x1 - x) // 16
    cv.rect(px_, top + 3, px_ + 2, bot, R.w3)
    cv.rect(px_ - 1, top + 3, px_ + 3, top + 5 + k, R.w3)
    cv.rect(px_ - 1, top + 5 + k, px_ + 3, top + 6 + k, R.w1)
    for by in range(top + 10, bot, 9 if k == 1 else 12):
        cv.rect(px_ - 1, by, px_ + 3, by + 1, R.w1)


def building(cv, R, st, x, w, top, bot, seed, f, wins=True, ft='apt', kind=None):
    rng = random.Random(seed)
    x1 = x + w
    cv.rect(x, top, x1, bot, R.w2)
    if st.glen:
        material(cv, R, st, x, x1, top, bot, seed, ft)
    # relit: every far tower is lit from one fixed side. The plane scrolls and loops, so a side picked from the home x
    # turned towers away from the light once they scrolled past it. Light from the right in all three moods: the moon
    # (x 250) and the sun (x 238) sit in the right part of the 320 px sky, so most of the screen is left of the source;
    # storm has no source, and its midA, midB and near walls carry the form shadow on the left (lit from the right).
    # The far role-index art is shared by the moods (only the palette differs), so one side serves all three.
    flip = st.far and FAR_LIT_FROM == 'left'
    if st.far:                                           # form shading: flat shadow face, lit face, rim light
        fw = max(2, w * 2 // 5)
        if flip:
            cv.rect(x1 - fw, top, x1, bot, R.w1)
        else:
            cv.rect(x, top, x + fw, bot, R.w1)
    if flip:
        cv.rect(x, top, x + st.side, bot, R.w3)
        cv.rect(x1 - 1, top, x1, bot, R.w0)
    else:
        cv.rect(x1 - st.side, top, x1, bot, R.w3)
        cv.rect(x, top, x + 1, bot, R.w0)
    if st.far:
        rx = x if flip else x1 - 1
        cv.rect(rx, top, rx + 1, top + 9, R.w4)
        for j in range(9, 17, 2):
            cv.px(rx, top + j, R.w4)
    cv.rect(x - 1, top, x1 + 1, top + 1, R.w4)
    if st.k >= 2:
        cv.rect(x - 1, top + 1, x1 + 1, top + 2, R.w3)
        cv.rect(x, top + 2, x1, top + 3, R.w0)
    if not wins:
        return
    if ft != 'apt':
        facade(cv, R, st, x, w, top, bot, seed, f, ft, kind)
        pipe(cv, R, st, x, x1, top, bot, seed, ft)
        return
    gx, gy, ww, wh = st.grid
    inner = w - st.side - 3
    cols = inner // gx
    xs = x + 2 + (inner - cols * gx + (gx - ww)) // 2
    y = top + (3 if st.k < 2 else 6)
    fl = 0
    lit = rng.random() < st.lit
    while y + wh + 1 < bot and cols > 0:
        mode = rng.choice(('mix', 'mix', 'mix', 'dark', 'dark', 'lit'))
        for c in range(cols):
            if rng.random() < 0.4:
                lit = rng.random() < st.lit * 1.6
            r1, r2, r3 = rng.random(), rng.random(), rng.randrange(8)
            on = lit if mode == 'mix' else (r1 < 0.08) if mode == 'dark' else (r1 < 0.85)
            state = 0
            if on:
                state = 1 if r2 < 0.6 else 2
                if r2 > 0.955:
                    state = 3
                elif r2 < 0.03:
                    state = 4
            if st.k < 1.5 and ww == 1:
                if on:
                    cv.rect(xs + c * gx, y, xs + c * gx + ww, y + wh, R.l2 if r2 < 0.7 else R.l1)
            else:
                window(cv, R, st, xs + c * gx, y, state, f, r3)
        y += gy
        fl += 1
        if st.band and fl % st.band == 0 and y + 2 < bot:
            cv.rect(x + 1, y - 2, x1 - st.side, y - 1, R.w3)
            cv.rect(x + 1, y - 1, x1 - st.side, y, R.w1)        # final: ledge = lit line and a shadow line under it
            y += 1
    pipe(cv, R, st, x, x1, top, bot, seed, ft)


def furnish(cv, R, st, x, w, top, kind, seed, f, y0, ft='apt'):
    k = st.k
    if kind == 'flat':
        cv.rect(x + 3, top - 2 - k, x + 6 + 2 * k, top, R.w1)
        cv.rect(x + 3, top - 3 - k, x + 6 + 2 * k, top - 2 - k, R.w3)
        if seed % 2:
            antenna(cv, R, x + w - 5, top, 6 + 3 * k, seed % 8, f)
    elif kind == 'step':
        h = 6 + 5 * k
        building(cv, R, st, x + w // 5, w * 3 // 5, top - h, top + 1, seed + 50, f, ft=ft)
        if st.far:
            antenna(cv, R, x + w // 2, top - h, 7, seed % 8, f)
    elif kind == 'spire':
        h1, h2 = 5 + 3 * k, 4 + 3 * k
        building(cv, R, st, x + w // 4, w // 2, top - h1, top + 1, seed + 50, f, ft=ft)
        building(cv, R, st, x + w * 3 // 8, max(w // 4, 3), top - h1 - h2, top - h1 + 1, seed + 51, f, wins=False)
        antenna(cv, R, x + w // 2, top - h1 - h2, 6 + 4 * k, seed % 8, f)
    elif kind == 'dome':
        r = w // 2 - 2
        for j in range(int(r * 0.8) + 1):
            hw = int(r * sqrt(max(0, 1 - (j / (r * 0.8)) ** 2)))
            y = top - 1 - j
            cx = x + w // 2
            cv.rect(cx - hw, y, cx + hw + 1, y + 1, R.w2)
            cv.rect(cx - hw, y, cx - hw // 2, y + 1, R.w1)
            cv.rect(cx + hw // 3, y, cx + hw + 1, y + 1, R.w3)
            cv.px(cx + hw, y, R.w4)
        antenna(cv, R, x + w // 2, top - int(r * 0.8) - 1, 5, seed % 8, f)
    elif kind == 'tank':
        tank(cv, R, x + w // 2 - 2 - k, top, k)
        cv.rect(x + 3, top - 2 - k, x + 5 + k, top, R.w1)
    elif kind == 'chim':
        chimney(cv, R, x + w // 3, top, 2 + k, 4 + 3 * k, f, 12 if k > 1 else 10, y0)
        antenna(cv, R, x + w - 5, top, 5 + 2 * k, seed % 8, f)
    elif kind == 'bill':
        billboard(cv, R, x + (w - 10 - 8 * k) // 2, top, k, f)
    elif kind == 'wedge':                                       # far glass tower: slanted roof
        hh = min(w // 2, 9)
        for dx in range(w):
            h_ = 1 + hh * (dx if seed % 2 else w - 1 - dx) // (w - 1)
            cv.rect(x + dx, top - h_, x + dx + 1, top, R.w1 if dx < w * 2 // 5 else R.w2)
            cv.px(x + dx, top - h_, R.w4)
    elif kind == 'slab':                                        # far office: neck and an overhanging roof slab, two masts
        cv.rect(x + 3, top - 2, x + w - 3, top, R.w1)
        cv.rect(x - 2, top - 5, x + w + 2, top - 2, R.w2)
        cv.rect(x - 2, top - 5, x + w * 2 // 5, top - 2, R.w1)
        cv.rect(x - 2, top - 6, x + w + 2, top - 5, R.w4)
        antenna(cv, R, x + 2, top - 6, 5, seed % 8, f)
        antenna(cv, R, x + w - 3, top - 6, 7, (seed + 3) % 8, f)
    elif kind == 'saw':                                         # far warehouse: sawtooth roof and a stack
        for tx in range(x + 1, x + w - 8, 6):
            for dx in range(6):
                cv.rect(tx + dx, top - (6 - dx), tx + dx + 1, top, R.w3 if dx == 0 else R.w1 if dx < 3 else R.w2)
        cv.rect(x + w - 5, top - 10, x + w - 2, top, R.w1)
        cv.rect(x + w - 5, top - 11, x + w - 2, top - 10, R.w4)
    elif kind == 'sign':
        cv.rect(x + 4, top - 3, x + 12, top, R.w1)
        cv.rect(x + 4, top - 4, x + 12, top - 3, R.w3)


# (x, width, roof line, roof kind, facade type): the facade types are placed by hand so that neighbours differ
# final: on the far plane the roof kind follows the facade type, so a type reads by silhouette at 1x:
# apartment flat or stepped, glass slanted wedge, office overhanging slab with masts, deco spire or dome, warehouse sawtooth
FAR = [(0, 20, 92, 'flat', 'apt'), (18, 16, 80, 'wedge', 'glass'), (34, 24, 98, 'slab', 'office'), (56, 16, 78, 'spire', 'deco'),
       (72, 28, 88, 'step', 'apt'), (98, 18, 102, 'saw', 'ware'), (114, 20, 84, 'dome', 'deco'), (134, 26, 94, 'slab', 'office'),
       (158, 14, 76, 'wedge', 'glass'), (172, 24, 86, 'step', 'apt'), (194, 22, 100, 'saw', 'ware'), (214, 18, 74, 'spire', 'deco'),
       (232, 28, 92, 'wedge', 'glass'), (258, 14, 80, 'step', 'apt'), (272, 24, 104, 'slab', 'office'), (294, 18, 82, 'wedge', 'glass'),
       (310, 26, 96, 'flat', 'apt')]
MIDA = [(-4, 30, 112, 'flat', 'office'), (24, 22, 102, 'tank', 'apt'), (46, 34, 120, 'flat', 'ware'), (78, 20, 100, 'step', 'deco'),
        (98, 28, 114, 'bill', 'apt'), (126, 20, 106, 'flat', 'glass'), (144, 36, 122, 'chim', 'ware'), (178, 24, 100, 'step', 'apt'),
        (200, 30, 116, 'tank', 'office'), (230, 22, 108, 'flat', 'deco'), (250, 34, 121, 'chim', 'apt'), (284, 22, 101, 'step', 'office'),
        (304, 36, 114, 'bill', 'ware')]
MIDB = [(0, 40, 134, 'flat', 'apt'), (38, 26, 132, 'tank', 'deco'), (62, 46, 144, 'chim', 'ware'), (106, 30, 128, 'sign', 'office'),
        (134, 40, 140, 'bill', 'apt'), (172, 26, 130, 'step', 'deco'), (196, 48, 144, 'tank', 'office'), (242, 30, 128, 'flat', 'ware'),
        (270, 36, 142, 'chim', 'apt'), (304, 32, 132, 'step', 'office')]
SPEC = {
    'F': St(name='far skyline', tab=FAR, y0=48, y1=128, opq=112, k=1, far=True, grid=(3, 4, 1, 2), lit=0.10, side=2, glen=0, g0=0,
            band=0, sway=6, haze=(72, 118, 0.9), hz_on=('w1', 'w2')),
    'A': St(name='mid skyline A', tab=MIDA, y0=88, y1=144, opq=128, k=1, far=False, grid=(4, 5, 2, 3), lit=0.26, side=2, glen=22, g0=5,
            band=4, sway=4, haze=(108, 132, 0.88), hz_on=('w1',)),
    'B': St(name='mid skyline B', tab=MIDB, y0=112, y1=176, opq=147, k=2, far=False, grid=(6, 8, 3, 4), lit=0.3, side=3, glen=26, g0=8,
            band=3, sway=2, haze=(136, 160, 0.75), hz_on=('w1',)),
}


def city_plane(key, f):
    st = SPEC[key]
    R = Rl(key)
    cv = Cv(H, PW)
    cv.rect(0, st.opq - 3, PW, st.y1, R.w2)
    order = sorted(range(len(st.tab)), key=lambda i: -st.tab[i][2] if key != 'F' else st.tab[i][2] * 0 + (i * 7) % 5)
    for i in order:
        x, w, top, kind, ft = st.tab[i]
        seed = ord(key) * 100 + i
        furnish(cv, R, st, x, w, top, kind, seed, f, st.y0, ft)
        building(cv, R, st, x, w, top, st.y1, seed, f, ft=ft, kind=kind)
        if kind == 'sign':
            chevrons(cv, R, x + w - 12, top + 6, f)
    ya, yb, mx = st.haze
    yy, xx = grid(H, PW)
    for b in st.hz_on:
        base = rid(key + '.' + b)
        t = np.clip((yy - ya) / (yb - ya), 0, 1)
        if key == 'F':        # far haze: flat haze colour at the base, one hand-drawn cluster edge above it, clean wall higher up
            clus(cv, cv.a == base, band(t, 0.25, 0.5), base, R.hz, 3)
        else:
            clus(cv, cv.a == base, band(t, 0.3, 0.45), base, R.hz, 1 if key == 'A' else 6)     # v3: hand cluster edge, no streak dither
    cv.a[:st.y0] = 0
    cv.a[st.y1:] = 0
    assert (cv.a[st.opq:st.y1] > 0).all(), key
    return cv


# ---------------------------------------------------------------- near rooftops (still plane, takes the cast light)
NB = [(0, 58, 160, 11, 'brick'), (62, 146, 152, 12, 'panel'), (150, 234, 166, 13, 'metal'), (238, 320, 150, 14, 'pier')]
NWIN = {'block': (15, 17, 7, 8), 'brick': (13, 14, 5, 6), 'panel': (16, 13, 9, 6), 'metal': (14, 24, 6, 4), 'pier': (10, 15, 5, 9)}     # pitch x, pitch y, window w, h
GLYPH = {'G': (".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".###."),
         'U': ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
         'M': ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#")}
# hand-set wobble of the cast-light bands in lines, one entry per 4 px, so that no band edge is a ruled line
WOB = [0, 1, 1, 2, 3, 3, 2, 1, 0, 0, -1, -2, -2, -1, 0, 1, 2, 2, 1, 0,
       -1, -1, 0, 1, 3, 4, 3, 2, 1, 1, 0, -1, -2, -3, -2, -1, 0, 0, 1, 2,
       2, 1, 0, -1, 0, 1, 2, 3, 2, 1, 0, -1, -2, -1, 0, 1, 1, 2, 1, 0,
       -1, -2, -3, -2, -1, 0, 1, 2, 3, 2, 1, 0, 0, -1, -1, 0, 1, 2, 1, 0]
STAINS = [(0, 0, 4), (2, 0, 6), (3, 1, 3), (1, 1, 5), (2, 2, 4), (0, 2, 3)]      # (window column, window row, drip length)


DASH = {5: (16, 15, 0), 6: (16, 13, 5), 8: (16, 11, 11), 10: (16, 8, 2), 12: (24, 11, 14), 15: (24, 8, 5), 18: (24, 6, 17),
        22: (32, 7, 9), 27: (32, 5, 22), 33: (48, 5, 13), 40: (48, 3, 31)}


DASHB = [(4, {5: (16, 12, 3), 7: (16, 9, 10), 9: (24, 13, 1), 12: (16, 6, 7), 16: (24, 8, 15), 21: (32, 7, 4), 28: (32, 4, 20),
              36: (48, 4, 9)}),
         (6, {6: (16, 14, 8), 8: (24, 17, 2), 11: (16, 9, 13), 13: (24, 10, 6), 17: (32, 12, 21), 20: (24, 5, 11), 25: (32, 6, 2),
              31: (48, 6, 30), 38: (48, 3, 12)}),
         (5, {5: (24, 20, 5), 7: (16, 10, 0), 10: (24, 12, 16), 14: (32, 14, 7), 19: (24, 6, 19), 24: (48, 9, 26), 30: (32, 4, 3),
              39: (48, 4, 40)}),
         (5, {6: (16, 13, 11), 9: (16, 10, 4), 11: (24, 9, 18), 15: (24, 10, 9), 18: (32, 8, 0), 23: (32, 6, 14), 27: (48, 7, 33),
              34: (48, 4, 21), 41: (48, 3, 5)}),
         (5, {5: (16, 11, 6), 8: (24, 15, 9), 10: (16, 7, 2), 13: (24, 9, 17), 16: (32, 10, 5), 21: (32, 6, 23), 26: (48, 7, 12),
              32: (48, 4, 37), 39: (48, 3, 20)})]      # endless: hand table of the fifth (block) roof
# endless: the near loop is 384 wide; a fifth roof of ashlar block fills 324..380 and leaves a 4 px alley at the join
NB5 = NB + [(324, 380, 158, 15, 'block')]
BLOCKLIT = [(0, 1), (2, 2), (1, 4), (2, 5), (0, 7), (1, 8)]     # (block phase of 3, course): lit top edge on that block


def und(R, y):
    """Underside role by height: full bounce light low on the wall, half higher up, none near the roofs."""
    return R.u if y >= 170 else R.uh if y >= 150 else R.w0


def near_window(cv, R, wx, y, ww, wh, r1, r3, f):
    if r1 < 0.13:
        cv.rect(wx, y, wx + ww, y + wh, R.l2)
        cv.rect(wx, y + 1, wx + ww, y + wh - 2, R.l1)
        cv.px(wx, y + 1, R.l3)
        cv.rect(wx + ww // 2, y, wx + ww // 2 + 1, y + wh, R.w0)
    elif r1 > 0.975:
        cv.rect(wx, y, wx + ww, y + wh, (R.t1, R.t2, R.t1, R.gl)[(f + r3) % 4])
    else:
        cv.rect(wx, y, wx + ww, y + wh, R.gl)
        cv.rect(wx, y, wx + ww, y + 1, R.w0)                       # shadow under the lintel
        cv.px(wx + ww - 2, y + 2, R.w3)                            # glint
        cv.px(wx + ww - 3, y + 3, R.w3)
    cv.rect(wx, y - 1, wx + ww, y, und(R, y))                      # lintel underside takes the bounce light
    cv.rect(wx - 1, y + wh, wx + ww + 1, y + wh + 1, R.w3)         # sill


def near_plane(f, nb=None, nw=None, cvc=None):
    nb = nb or NB
    nw = nw or W
    cv = (cvc or Cv)(H, nw)
    R = Rl('N')
    yy, xx = grid(H, nw)
    cv.rect(0, 176, nw, H, R.w1)
    # things that stand behind the roof lines
    cv.rect(158, 160, 228, 161, R.w3)
    cv.rect(158, 161, 228, 163, R.w2)
    cv.rect(158, 163, 228, 164, R.uh)
    for fx in range(164, 228, 16):
        cv.rect(fx, 159, fx + 2, 165, R.w3)
    tank(cv, R, 74, 152, 3)
    chimney(cv, R, 124, 152, 5, 8, f, 10, 128)
    antenna(cv, R, 48, 160, 26, 3, f)
    flag(cv, R, 12, 160, 20, f // 2)
    fan(cv, R, 26, 160, f)
    fan(cv, R, 168, 166, f + 1)
    fan(cv, R, 200, 166, f + 2)
    fan(cv, R, 104, 152, f + 3)
    if len(nb) > 4:                                                     # endless: furniture of the block roof
        tank(cv, R, 360, 158, 2)
        antenna(cv, R, 334, 158, 19, 5, f)
        fan(cv, R, 344, 158, f + 5)
    for (x0, x1, top, seed, mat) in nb:
        rng = random.Random(seed)
        gx, gy, ww, wh = NWIN[mat]
        cv.rect(x0, top, x1, H, R.w2)
        if mat == 'pier':
            wxs = [bx + o for bx in range(x0 + 2, x1 - 20, 20) for o in (5, 12)]
        else:
            cols = (x1 - x0 - 10) // gx
            xs = x0 + 5 + ((x1 - x0 - 10) - cols * gx + gx - ww) // 2
            wxs = [xs + c * gx for c in range(cols)]
        rows = list(range(top + 10, H, gy))
        # material: flat wall colour with drawn courses, seams, rivets and stains; no noise dither
        if mat == 'brick':
            for r, y in enumerate(rows):
                ya = y + wh + 2
                cv.rect(x0 + 1, ya, x1 - 3, ya + 1, R.w1)
                cv.rect(x0 + 1, ya + 4, x1 - 3, ya + 5, R.w1)
                for bx in range(x0 + 3 + (4 if r % 2 else 0), x1 - 4, 8):
                    cv.rect(bx, ya + 1, bx + 1, ya + 4, R.w1)
        elif mat == 'panel':
            for c in range(len(wxs) + 1):
                sx = wxs[0] + c * gx - 4
                cv.rect(sx, top + 4, sx + 1, H, R.w1)
            for y in rows:
                cv.rect(x0 + 1, y + wh + 3, x1 - 3, y + wh + 4, R.w1)
                for c in range(len(wxs) + 1):
                    cv.px(wxs[0] + c * gx - 4, y + wh + 3, R.w0)        # bolt at the seam crossing
            for c, r, n in STAINS:
                if c < len(wxs) and r < len(rows):
                    sx, sy = wxs[c] + 2 + 3 * (r % 2), rows[r] + wh + 1
                    cv.rect(sx, sy, sx + 1, sy + n, R.w1)
                    cv.rect(sx + 2, sy, sx + 3, sy + n - 2, R.w1)
        elif mat == 'metal':
            for j, yl in enumerate(range(top + 8, H, 12)):
                cv.rect(x0 + 1, yl, x1 - 3, yl + 1, R.w1)
                for bx in range(x0 + 4 + (12 if j % 2 else 0), x1 - 4, 24):
                    cv.rect(bx, yl + 1, bx + 1, yl + 12, R.w1)
                for bx in range(x0 + 6, x1 - 5, 6):
                    cv.px(bx, yl + 3, R.w3)                             # rivet and its shadow
                    cv.px(bx, yl + 4, R.w1)
        elif mat == 'block':                                            # ashlar: 8 px courses, joints staggered by half a block
            for j, yl in enumerate(range(top + 8, H, 8)):
                cv.rect(x0 + 1, yl, x1 - 3, yl + 1, R.w1)
                for q, bx in enumerate(range(x0 + 4 + (8 if j % 2 else 0), x1 - 4, 16)):
                    cv.rect(bx, yl + 1, bx + 1, yl + 8, R.w1)
                    if (q % 3, j % 9) in BLOCKLIT:
                        cv.rect(bx + 1, yl + 1, min(bx + 16, x1 - 4), yl + 2, R.w3)
        else:
            for bx in range(x0 + 2, x1 - 6, 20):
                cv.rect(bx, top + 4, bx + 2, H, R.w3)                   # brick pier: lit face and shadow line
                cv.rect(bx + 2, top + 4, bx + 3, H, R.w1)
            for y in rows:
                cv.rect(x0 + 1, y + wh + 3, x1 - 3, y + wh + 4, R.w1)
        cv.rect(x0, top + 4, x1 - 3, top + 7, R.w1)                     # cast shadow of the cornice, flat
        cv.rect(x0 + 1, top + 4, x0 + 3, H, R.w1)                       # form shadow at the left edge, flat
        cv.rect(x1 - 3, top, x1, top + 22, R.w3)
        cv.rect(x1 - 3, top + 22, x1, H, R.e)
        cv.rect(x0, top, x0 + 1, H, R.w0)
        cv.rect(x0 - 1, top, x1 + 1, top + 1, R.w4)
        cv.rect(x0 - 1, top + 1, x1 + 1, top + 3, R.w3)
        cv.rect(x0, top + 3, x1, top + 4, und(R, top + 3))
        for cx in range(x0 + 5, x1 - 4, 12):                            # parapet blocks
            cv.rect(cx, top - 2, cx + 6, top, R.w3)
            cv.rect(cx, top - 3, cx + 6, top - 2, R.w4)
            cv.rect(cx, top - 2, cx + 1, top, R.w1)
        for y in rows:
            for c, wx in enumerate(wxs):
                r1, r3 = rng.random(), rng.randrange(8)
                if mat == 'metal' and c % 3 == 1:                       # louvre vent in place of a window
                    for j in range(wh + 1):
                        cv.rect(wx, y + j, wx + ww, y + j + 1, R.w0 if j % 2 == 0 else R.w3)
                else:
                    near_window(cv, R, wx, y, ww, wh, r1, r3, f)
                if mat == 'block':                                      # flat arch with a keystone
                    cv.rect(wx - 1, y - 3, wx + ww + 1, y - 2, R.w3)
                    cv.rect(wx - 1, y - 2, wx + ww + 1, y - 1, R.w1)
                    cv.rect(wx + ww // 2 - 1, y - 4, wx + ww // 2 + 1, y - 1, R.w4)
                    cv.rect(wx + ww // 2 - 1, y - 1, wx + ww // 2 + 1, y, R.w1)
        px_ = x1 - 8 if mat == 'block' else x0 + (x1 - x0) * 2 // 3 + 1                               # drain pipe with brackets
        cv.rect(px_, top + 4, px_ + 1, H, R.w3)
        cv.rect(px_ + 1, top + 4, px_ + 2, H, R.w0)
        for by in range(top + 12, H, 16):
            cv.rect(px_ - 1, by, px_ + 3, by + 1, R.w0)
    # hazard cast light: role g is the wall colour in the neutral palette and the lit wall colour in the lit palettes.
    # The fade is drawn in the tiles as ordered meshes (full, 3/4, 1/2, 1/4, 1/8, 1/16), each a subset of the one below,
    # with hand-wobbled band edges. The palette level is one per 16 px column for the whole height: no step across tile rows.
    h = 192 - yy + np.array(WOB)[(xx // 4) % len(WOB)]
    wall = (cv.a == R.w2) & (yy >= 140)
    # v3: no checker meshes. A solid lit foot, then broken horizontal light streaks that thin out upward (hand table DASH:
    # height above the hazard -> period, lit length, offset). Reads as lapping light, not as a pattern.
    # final: every near building has its own hand table (foot height, streak rows, lengths, offsets) and wobble phase
    pat = np.zeros((H, nw), bool)
    z = np.zeros((H, nw), bool)
    for b, (x0, x1, top, seed, mat) in enumerate(nb):
        col = (xx >= x0 - 2) & (xx < x1 + 2)
        hb = 192 - yy + np.array(WOB)[(xx // 4 + 17 * b) % len(WOB)]
        foot, tab = DASHB[b]
        pb = hb < foot
        for hv, (per, onl, off) in tab.items():
            pb |= (hb == hv) & (((xx + off) % per) < onl)
        pat |= col & pb
        z |= col & (hb >= foot) & (hb <= max(tab))
    cv.a[wall & pat] = R.g
    z &= wall
    cv.da[z] = R.w2
    cv.db[z] = R.g
    # GUM sign
    bx0, by0 = 244, 129
    cv.rect(bx0, by0, bx0 + 64, by0 + 18, R.w0)
    cv.rect(bx0, by0, bx0 + 64, by0 + 1, R.w4)
    cv.rect(bx0 + 63, by0, bx0 + 64, by0 + 18, R.w3)
    for lx in (252, 298):
        cv.rect(lx, by0 + 18, lx + 2, 150, R.w1)
    tube = np.zeros((H, nw), bool)
    dim = np.zeros((H, nw), bool)
    for li, ch in enumerate('GUM'):
        for j, row in enumerate(GLYPH[ch]):
            for i, c in enumerate(row):
                if c == '#':
                    x, y = bx0 + 4 + li * 12 + i * 2, by0 + 2 + j * 2
                    tube[y:y + 2, x:x + 2] = True
                    if ch == 'U' and f == 5:
                        dim[y:y + 2, x:x + 2] = True
    glow = tube.copy()
    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        glow |= np.roll(tube, (dy, dx), (0, 1))
    cv.setm(glow & ~tube & (((xx + yy) & 1) == 0), R.n3)
    cv.setm(tube, R.n1)
    cv.setm(tube & (xx % 2 == 0) & (yy % 2 == 1), R.nh)
    cv.setm(dim, R.n2)
    bcx, bcy = bx0 + 51, by0 + 9
    r = (2, 3, 4, 5, 6, 7, 0, 0)[f]
    d = np.sqrt((xx - bcx) ** 2 + (yy - bcy) ** 2)
    if r:
        cv.setm(np.abs(d - r) < 0.6, R.c1)
        cv.setm((d < r - 0.6) & (((xx + yy) & 1) == 0) & (xx - bcx + yy - bcy > 1), R.c2)
        cv.px(bcx - r // 2, bcy - r // 2, R.l3)
    elif f == 6:
        for t in range(8):
            for q in (6, 7):
                cv.px(bcx + round(q * cos(t * pi / 4)), bcy + round(q * sin(t * pi / 4)), R.c1)
    else:
        cv.px(bcx, bcy, R.c2)
    # lamp cable from a pole on roof 2 to the sign
    cv.rect(144, 142, 145, 152, R.w3)
    for i in range(101):
        t = i / 100
        x, y = 144 + i, round(142 + (133 - 142) * t + 46 * t * (1 - t))
        cv.px(x, y, R.w0)
        if i % 10 == 5:
            b = (i // 10 + f // 2) % 2 == 0
            cv.px(x, y + 1, R.l3 if b else R.l2)
            cv.px(x, y + 2, R.l1 if b else R.l2)
    cv.a[:128] = 0
    assert (cv.a[176:] > 0).all()
    return cv


# ---------------------------------------------------------------- sky planes (one per mood)
SKYH = 128


def _strip(w, rows):
    a = np.zeros((len(rows), w), bool)
    for r, (kind, runs) in enumerate(rows):
        if kind == 'D':
            a[r] = True
        for x, n in runs:
            a[r, x:x + n] = (kind == 'L')
    return a


# Hand-authored cluster strips for the sky band edges. A strip is the edge between a darker colour (above) and a lighter
# colour (below), top row first. 'L' rows list the light clusters (x, length) set into the dark colour; 'D' rows list the
# dark gaps left in the light colour. Three characters: A cumulus tops, B stratus streaks, C big lumps with flecks.
STRIPS = {
    'A': _strip(80, [
        ('L', [(37, 3), (70, 2)]),
        ('L', [(5, 2), (35, 6), (59, 1), (69, 4)]),
        ('L', [(3, 5), (22, 2), (34, 8), (57, 3), (68, 6)]),
        ('L', [(2, 7), (20, 5), (33, 10), (48, 2), (56, 5), (67, 8)]),
        ('D', [(0, 2), (10, 9), (26, 6), (44, 3), (51, 4), (62, 4), (76, 4)]),
        ('D', [(12, 6), (27, 3), (45, 2), (52, 2), (63, 2), (77, 3)]),
        ('D', [(13, 4), (22, 3), (38, 4), (52, 2), (78, 2)]),
        ('D', [(14, 2), (23, 2), (39, 3), (60, 3)]),
        ('D', [(8, 2), (40, 2), (61, 2)]),
        ('D', [(9, 1), (30, 2), (62, 1)]),
        ('D', [(31, 1), (72, 2)])]),
    'B': _strip(64, [
        ('L', [(12, 5), (44, 7)]),
        ('L', [(3, 9), (27, 4), (40, 14)]),
        ('L', [(0, 6), (10, 12), (30, 10), (47, 3), (54, 8)]),
        ('D', [(6, 4), (22, 7), (40, 6), (61, 3)]),
        ('D', [(9, 5), (27, 3), (49, 8)]),
        ('D', [(0, 3), (30, 6), (55, 4)]),
        ('D', [(14, 4), (44, 3)]),
        ('D', [(16, 2), (36, 5)]),
        ('D', [(58, 3)])]),
    'C': _strip(96, [
        ('L', [(20, 2), (63, 1)]),
        ('L', [(18, 6), (50, 1), (61, 5), (88, 2)]),
        ('L', [(15, 12), (40, 2), (58, 11), (86, 5)]),
        ('L', [(13, 17), (38, 6), (56, 15), (78, 1), (84, 9)]),
        ('L', [(0, 3), (11, 21), (36, 10), (54, 19), (76, 4), (83, 12)]),
        ('D', [(4, 6), (33, 2), (47, 6), (74, 1), (81, 1)]),
        ('D', [(5, 4), (20, 5), (48, 4), (62, 6)]),
        ('D', [(6, 2), (21, 3), (49, 2), (63, 4), (88, 3)]),
        ('D', [(22, 1), (38, 3), (64, 2), (89, 2)]),
        ('D', [(8, 1), (39, 2), (76, 3)]),
        ('D', [(28, 2), (77, 1)]),
        ('D', [(52, 1)])]),
}
# which strips run along each band edge, left to right (lower case = mirrored), and the start offset in px: placed by hand
# so that no two edges show the same clusters above each other
BANDSEQ = [('AcBaCb', 0), ('CbAcBa', 23), ('BaCbAc', 51), ('cAbCaB', 9), ('aCBcbA', 37), ('bCAcaB', 64), ('CaBbAc', 17), ('AbCcBa', 44)]
NQ = 24


def band_pattern(b, wid=PW):
    seq, off = BANDSEQ[b % len(BANDSEQ)]
    cols, wd, i = [], 0, 0
    while wd < wid + off:
        ch = seq[i % len(seq)]
        st_ = STRIPS[ch.upper()]
        if ch.islower():
            st_ = st_[:, ::-1]
        cols.append(st_[(np.arange(NQ) * st_.shape[0]) // NQ])
        wd += st_.shape[1]
        i += 1
    return np.concatenate(cols, 1)[:, off:off + wid]


BANDPAT = [band_pattern(b) for b in range(len(BANDSEQ))]


# v3: five more hand-authored strips. D shelf with towers, E scattered small puffs, F windswept diagonal streaks,
# G two uneven mounds with notches, H calm thin lines with flecks.
STRIPS.update({
    'D': _strip(112, [
        ('L', [(18, 2)]),
        ('L', [(16, 5), (84, 1)]),
        ('L', [(15, 7), (47, 2), (82, 4)]),
        ('L', [(13, 10), (44, 6), (63, 1), (80, 8), (104, 2)]),
        ('L', [(4, 3), (11, 14), (41, 11), (60, 5), (77, 13), (101, 6)]),
        ('L', [(1, 27), (38, 31), (74, 19), (98, 11)]),
        ('D', [(29, 8), (70, 3), (94, 3), (110, 2)]),
        ('D', [(30, 6), (52, 2), (71, 1), (95, 2)]),
        ('D', [(8, 2), (31, 4), (52, 3)]),
        ('D', [(32, 2), (53, 1), (88, 3)]),
        ('D', [(20, 2), (89, 1)]),
        ('D', [(66, 2)])]),
    'E': _strip(72, [
        ('L', [(9, 1), (51, 2)]),
        ('L', [(8, 3), (30, 1), (50, 4)]),
        ('L', [(6, 6), (28, 4), (49, 7), (66, 2)]),
        ('L', [(5, 8), (19, 2), (27, 7), (41, 1), (47, 10), (64, 5)]),
        ('L', [(3, 12), (18, 5), (26, 10), (39, 4), (46, 13), (62, 9)]),
        ('D', [(0, 2), (15, 3), (24, 1), (36, 3), (44, 1), (59, 3), (71, 1)]),
        ('D', [(10, 2), (16, 1), (36, 2), (52, 3), (60, 1)]),
        ('D', [(11, 1), (31, 3), (53, 2)]),
        ('D', [(32, 1), (68, 2)]),
        ('D', [(22, 2)])]),
    'F': _strip(88, [
        ('L', [(40, 6)]),
        ('L', [(8, 10), (36, 14), (70, 5)]),
        ('L', [(2, 22), (30, 26), (62, 18)]),
        ('L', [(0, 30), (33, 50)]),
        ('D', [(26, 9), (58, 6), (84, 4)]),
        ('D', [(20, 11), (52, 9), (80, 3)]),
        ('D', [(14, 10), (47, 8), (74, 5)]),
        ('D', [(10, 7), (43, 5), (68, 6)]),
        ('D', [(6, 5), (64, 4)]),
        ('D', [(3, 3), (38, 3)])]),
    'G': _strip(104, [
        ('L', [(30, 3)]),
        ('L', [(27, 8), (78, 2)]),
        ('L', [(24, 13), (75, 7)]),
        ('L', [(8, 2), (21, 19), (58, 2), (72, 12)]),
        ('L', [(6, 6), (19, 24), (55, 7), (70, 17), (96, 3)]),
        ('L', [(4, 10), (17, 29), (52, 12), (67, 23), (94, 7)]),
        ('L', [(2, 46), (50, 42), (93, 10)]),
        ('D', [(0, 3), (28, 2), (47, 4), (90, 4)]),
        ('D', [(28, 3), (48, 2), (72, 2), (91, 2)]),
        ('D', [(12, 2), (29, 1), (72, 3)]),
        ('D', [(13, 1), (60, 2), (73, 1)]),
        ('D', [(61, 1)])]),
    'H': _strip(56, [
        ('L', [(22, 4)]),
        ('L', [(4, 7), (18, 12), (44, 5)]),
        ('L', [(0, 34), (40, 14)]),
        ('D', [(10, 6), (34, 6), (54, 2)]),
        ('D', [(12, 3), (27, 4), (48, 3)]),
        ('D', [(2, 2), (28, 2)]),
        ('D', [(40, 3)]),
        ('D', [(18, 2), (41, 1)])]),
})
# v3 sky edges: every edge is a hand-set order of all eight strips (lower case = mirrored), each strip once, so one edge
# has no strip twice inside 672 px (screen 320). The far and mid haze keep the v2 patterns (BANDPAT).
# final: two calm strips for the top band edge (long low clusters, no towers), so the edge reads as one drawn cluster line
STRIPS.update({
    'T': _strip(120, [
        ('L', [(10, 18)]),
        ('L', [(4, 30), (62, 26)]),
        ('L', [(0, 41), (45, 14), (61, 33), (98, 20)]),
        ('D', [(41, 4), (94, 4), (118, 2)]),
        ('D', [(22, 12), (56, 3), (80, 9)]),
        ('D', [(26, 5), (84, 3)])]),
    'U': _strip(100, [
        ('L', [(50, 16)]),
        ('L', [(42, 34)]),
        ('L', [(0, 18), (24, 54), (82, 18)]),
        ('D', [(18, 6), (78, 4)]),
        ('D', [(8, 14), (38, 8), (66, 5)]),
        ('D', [(12, 6), (41, 3), (92, 4)]),
        ('D', [(60, 2)])]),
})
SKYSEQ = [('TUtu', 0), ('gBfChAdE', 37), ('EhAfDbGc', 71), ('CfbHdEaG', 18), ('hDcGaFeB', 55), ('FAgBEhCd', 9),
          ('bEGdCfHA', 83), ('AGhFcBDe', 29), ('dCHeGAbF', 46)]
# final: one hand-set rise and fall per band edge (15 values) with its own spacing in px, so no two edges run parallel
EDGEWOBS = [([1, 2, 0, -2, -3, -1, 1, 3, 2, 0, -2, -1, 1, 3, 1], 28),
            ([0, 3, 5, 2, -2, -5, -3, 1, 4, 6, 2, -1, -4, -2, 0], 24),
            ([-3, -5, -2, 2, 5, 6, 3, -1, -4, -6, -3, 0, 3, 1, -3], 21),
            ([4, 2, -1, -2, 0, 3, 5, 2, -3, -5, -2, 1, 2, 4, 4], 32),
            ([-1, 2, 4, 5, 2, -2, -5, -4, 0, 3, 1, -2, -3, 0, -1], 26),
            ([1, -2, -4, -1, 3, 5, 2, -1, 0, 2, 4, 1, -3, -4, 1], 22)]
HALO_W = 2.5         # half width in px of the cluster edge of a halo ring


def edge_disp(D):
    """Vertical displacement of the sky gradient: every band edge has its own wobble table; between two edges the
    displacement is blended by height."""
    ys, ls = D['ys'], D['ls']
    ks = [k for k in range(D['n'] - 1) if ls[0] < k + 0.5 < ls[-1]]
    yk = [float(np.interp(k + 0.5, ls, ys)) for k in ks]
    xs = np.arange(W)
    wk = np.array([np.interp(xs, np.arange(15) * EDGEWOBS[k % 6][1], EDGEWOBS[k % 6][0]) for k in ks])
    yv = np.arange(SKYH)
    disp = np.zeros((SKYH, W))
    for x in range(W):
        disp[:, x] = np.interp(yv, yk, wk[:, x])
    return disp
EDGE_H = 11          # height of a cluster edge in px, the same wherever the sky gradient is slow


def sky_pattern(seq, off):
    assert len(set(seq)) == len(seq)
    cols, wd, i = [], 0, 0
    while wd < PW + off:
        ch = seq[i % len(seq)]
        st_ = STRIPS[ch.upper()]
        if ch.islower():
            st_ = st_[:, ::-1]
        cols.append(st_[(np.arange(NQ) * st_.shape[0]) // NQ])
        wd += st_.shape[1]
        i += 1
    return np.concatenate(cols, 1)[:, off:off + PW]


SKYPAT = [sky_pattern(*sq) for sq in SKYSEQ]
HALOPAT = [sky_pattern('HbTfUe', 12), sky_pattern('uEhBtF', 47)]      # cluster strips along the two halo rings (by arc length)


def sky_edges(L, n):
    """Band index and cluster position q (0 dark colour, 1 light colour). q follows the pixel distance to the band edge:
    the strips are EDGE_H px tall where the gradient is slow (v2 stretched them into teeth there) and never wider than
    the middle third of a ramp step where it is steep (wisps)."""
    gy, gx = np.gradient(L)
    g = np.sqrt(gx * gx + gy * gy)
    for ax in (0, 1):
        g = sum(np.roll(g, sh, ax) for sh in (-2, -1, 0, 1, 2)) / 5.0
    i0 = np.clip(np.floor(L).astype(int), 0, n - 2)
    fr = L - i0
    sc = np.maximum(1.0 / np.maximum(g * EDGE_H, 1e-6), 1 / 0.34)
    return i0, np.clip(0.5 + (fr - 0.5) * sc, 0, 1)


def edge_e(ells, floor):
    """Lower edge of a cloud layer made of hand-placed ellipses (cx, cy, rx, ry)."""
    xs = np.arange(W)
    e = np.full(W, float(floor))
    for cx, cy, rx, ry in ells:
        t = 1 - ((xs - cx) / rx) ** 2
        e = np.maximum(e, np.where(t > 0, cy + ry * np.sqrt(np.maximum(t, 0)), -99))
    return e


def clus(cv, m, q, ca, cb, b, pats=None):
    """Inside mask m: colour ca where q <= 0, cb where q >= 1; between, the hand-authored cluster strips of band edge b.
    The strip row follows q, so the clusters bend along the wisps and the halo."""
    yy, xx = grid(cv.h, cv.w)
    r = np.clip((q * NQ).astype(int), 0, NQ - 1)
    on = np.where(q >= 1, True, np.where(q <= 0, False, (pats or BANDPAT)[b % len(pats or BANDPAT)][r, xx]))
    cv.a[m & on] = cb
    cv.a[m & ~on] = ca
    z = m & (q > 0) & (q < 1)
    cv.da[m] = 0
    cv.da[z] = ca
    cv.db[z] = cb


SKYDEF = {
    'moon': dict(n=5, ys=[0, 10, 22, 66, 108, 128], ls=[0.15, 0.33, 1.0, 2.0, 3.0, 3.6], wk=1.3, rings=(6, 16), starlim=2.1,
                 wisps=[(60, 40, 46, 7, .55), (150, 62, 60, 6, .5), (250, 86, 70, 8, .6), (20, 78, 40, 6, .5), (110, 26, 34, 5, .4),
                        (196, 28, 30, 4, -.3), (300, 58, 36, 6, .45), (90, 98, 56, 7, .5), (180, 104, 50, 6, -.4)]),
    'storm': dict(n=5, ys=[0, 56, 96, 128], ls=[0.5, 1.4, 2.6, 3.6], wk=1.3,
                  wisps=[(50, 78, 60, 7, .5), (170, 88, 70, 6, .5), (280, 74, 50, 6, .45), (110, 104, 60, 6, -.4), (230, 110, 60, 7, .5)]),
    'dusk': dict(n=6, ys=[0, 30, 72, 110, 128], ls=[0, 0.7, 2.1, 3.5, 4.2], wk=1.6, cap=4.25, rings=(7, 19), starlim=1.1,
                 wisps=[(70, 28, 60, 5, .5), (210, 20, 70, 4, .45), (140, 52, 80, 6, .6), (286, 44, 50, 5, .5), (40, 80, 70, 6, .6),
                        (160, 92, 90, 5, .5), (100, 10, 40, 3, .3)]),
}
BIGSTARS = [(22, 14, 0), (70, 8, 2), (118, 34, 1), (150, 12, 3), (196, 44, 2), (300, 12, 1), (44, 46, 3), (176, 30, 0), (96, 56, 2), (8, 60, 1)]
DECK1 = [(-6, 30, 30), (34, 36, 26), (74, 28, 34), (118, 40, 24), (150, 30, 30), (192, 38, 30), (232, 30, 26), (268, 42, 26), (306, 32, 30)]
DECK2 = [(10, 12, 26), (56, 6, 30), (100, 14, 24), (140, 4, 30), (184, 12, 26), (226, 6, 28), (270, 14, 26), (314, 8, 26)]
MOON = (250, 38, 20)
SUN = (238, 84, 30)
# v3 storm deck: three layers of hand-placed ellipses with uneven widths and depths (broad shelves next to deep bellies),
# and the black mass above the play area. (cx, cy, rx, ry)
DECKA = [(-8, 40, 30, 22), (30, 46, 22, 10), (66, 38, 34, 34), (112, 50, 18, 6), (138, 44, 30, 24), (186, 52, 26, 8),
         (214, 40, 22, 32), (252, 48, 36, 18), (296, 42, 20, 26), (326, 50, 18, 12)]
DECKB = [(14, 24, 36, 20), (64, 30, 20, 9), (98, 22, 40, 26), (150, 32, 24, 8), (182, 24, 28, 22), (236, 30, 34, 12),
         (280, 22, 26, 25), (318, 30, 22, 10)]
DECKC = [(-4, 8, 28, 14), (40, 12, 30, 6), (84, 6, 22, 17), (124, 12, 36, 8), (176, 8, 26, 15), (214, 12, 20, 6),
         (250, 6, 34, 19), (300, 10, 28, 11)]
VOID = [(20, 0, 40, 13), (76, 0, 24, 19), (130, 0, 50, 12), (190, 0, 22, 18), (236, 0, 44, 14), (292, 0, 30, 20)]


# final storm deck. BASE: dark ceiling. MASSES: (ellipses, belly brightness, depth scale px, rim light), back to front.
BASE = [(-10, 32, 50, 14), (62, 30, 34, 8), (118, 34, 44, 16), (176, 30, 30, 6), (228, 32, 46, 18), (290, 30, 40, 12)]
MASSES = [([(60, 22, 30, 6)], 1.3, 5.0, False),
          ([(232, 24, 28, 7), (254, 26, 14, 5)], 1.35, 5.0, False),
          ([(112, 32, 22, 9), (130, 35, 14, 6)], 1.6, 6.0, False),
          ([(142, 42, 26, 12)], 1.5, 6.0, False),
          ([(292, 38, 34, 14), (320, 42, 18, 10)], 1.9, 7.0, False),
          ([(40, 44, 46, 18), (8, 40, 26, 14), (76, 48, 24, 10)], 2.3, 9.0, True),
          ([(196, 50, 54, 21), (158, 46, 24, 12), (238, 54, 26, 12)], 2.45, 10.0, True),
          ([(98, 63, 20, 5), (112, 65, 12, 4)], 2.0, 4.0, False),
          ([(272, 66, 24, 6), (252, 64, 10, 4)], 2.2, 5.0, True)]
SKIRT = [(8, 4, 30, 14), (52, 2, 30, 22), (100, 4, 34, 18), (150, 2, 40, 17), (204, 4, 30, 21), (256, 2, 40, 20), (310, 4, 26, 22)]


def top_e(ells):
    """Upper edge of a closed cloud mass made of ellipses (flatter than the lower edge)."""
    xs = np.arange(W)
    e = np.full(W, 999.0)
    for cx, cy, rx, ry in ells:
        t = 1 - ((xs - cx) / rx) ** 2
        e = np.minimum(e, np.where(t > 0, cy - 0.75 * ry * np.sqrt(np.maximum(t, 0)), 999))
    return e


def fringe(cv, edge, colour, pat, hgt):
    """Paint `colour` above the edge line; the last hgt px above the line are broken into hand cluster strips that let
    the colour underneath show. Marks the pair for the dither statistics."""
    yy, xx = grid(cv.h, cv.w)
    q = (edge[None, :] - yy) / float(hgt)
    z = (q > 0) & (q < 1)
    keep = z & pat[np.clip(((1 - q) * NQ).astype(int), 0, NQ - 1), xx]
    under = cv.a.copy()
    cv.setm((q > 0) & ~keep, colour)
    zz = z & (under != colour)
    cv.da[zz] = colour
    cv.db[zz] = under[zz]


def edge_y(circ, floor):
    xs = np.arange(W)
    e = np.full(W, float(floor))
    for cx, cy, r in circ:
        d = r * r - (xs - cx) ** 2
        e = np.maximum(e, np.where(d > 0, cy + np.sqrt(np.maximum(d, 0)), -99))
    return e


def band(t, a=0.33, b=0.34):
    """Leave flat colour at both ends of a ramp step, so that the clusters sit in bands and not everywhere."""
    return np.clip((t - a) / b, 0, 1)


def sky_plane(mood, f):
    D = SKYDEF[mood]
    S = Rl('S')
    cv = Cv(H, W)
    yy, xx = grid(SKYH, W)
    n = D['n']
    # v3: the band edges do not run level: a hand-set slow rise and fall (px), so no edge is a straight row of bumps
    L = np.interp(yy + edge_disp(D), D['ys'], D['ls'])
    for cx, cy, rx, ry, amp in D['wisps']:
        ryv = np.where(yy > cy, ry * 0.5, ry)                       # flat bottom, round top
        L = L + amp * D['wk'] * np.clip(1 - ((xx - cx) / rx) ** 2 - ((yy - cy) / ryv) ** 2, 0, 1) ** 0.6
    L = np.clip(np.minimum(L, D.get('cap', n - 1)), 0, n - 1)
    hs = np.zeros((SKYH, W), int)                                    # v3 halo: clean flat rings, one ramp step each
    disc = None
    halo = []
    if mood in ('moon', 'dusk'):
        cx, cy, r = MOON if mood == 'moon' else SUN
        rr = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        disc = rr <= r + 0.3
        for j, dr in enumerate(D['rings']):     # final: ring edge broken into hand clusters that run along the arc
            rad = r + dr
            circ = int(round(TAU * rad))
            u = ((np.arctan2(yy - cy, xx - cx) + pi) / TAU * circ).astype(int) % circ
            qh = np.clip((rad + HALO_W - rr) / (2.0 * HALO_W), 0, 1)
            row = np.clip((qh * NQ).astype(int), 0, NQ - 1)
            inside = np.where(qh >= 1, True, np.where(qh <= 0, False, HALOPAT[j][row, u]))
            halo.append(((qh > 0) & (qh < 1), inside.astype(int)))
            hs += inside
    i0, q = sky_edges(L, n)
    ramp = np.array([rid('S.s%d' % i) for i in range(n)])
    r_ = np.clip((q * NQ).astype(int), 0, NQ - 1)
    on = q >= 1
    for i in range(n - 1):
        on = np.where((i0 == i) & (q > 0) & (q < 1), SKYPAT[i][r_, xx], on)
    lo, hi = np.minimum(i0 + hs, n - 1), np.minimum(i0 + hs + 1, n - 1)
    sub = Cv(SKYH, W)
    sub.a[:] = np.where(on, ramp[hi], ramp[lo])
    z = (q > 0) & (q < 1) & (hi != lo)
    sub.da[z] = ramp[lo][z]
    sub.db[z] = ramp[hi][z]
    for zone, inside in halo:
        wo = i0 + on.astype(int) + hs - inside
        a_, b_ = ramp[np.minimum(wo, n - 1)], ramp[np.minimum(wo + 1, n - 1)]
        zz = zone & (a_ != b_)
        sub.da[zz] = a_[zz]
        sub.db[zz] = b_[zz]
    Lt = L + hs
    if mood == 'storm':
        kr = [S.k0, S.k1, S.k2, S.k3]
        wob = np.array(WOB)[(xx // 3) % len(WOB)]

        def layer(m, d, peak, sc, j, rim):
            Lk = np.clip(peak - d / sc, 0, 3)                      # lit belly at the lower edge, heavy dark body above
            k0 = np.minimum(np.floor(Lk).astype(int), 2)
            for i in range(3):
                clus(sub, m & (k0 == i), band(Lk - i, 0.2, 0.6), kr[i], kr[i + 1], 3 + (2 * j + i) % 6, SKYPAT)
            if rim:
                sub.setm(m & (d < 1.2) & (wob > 0), S.k3)           # broken rim light

        # final: no layers. A dark ceiling with an uneven lower edge, then separate cloud masses of different size, height,
        # depth and brightness, drawn back to front so that they overlap.
        d = edge_e(BASE, 30)[None, :] - yy
        layer(d > 0, d, 1.25, 7.0, 0, False)
        for j, (ells, peak, sc, rim) in enumerate(MASSES, 1):
            d = edge_e(ells, -99)[None, :] - yy
            layer((d > 0) & (yy >= top_e(ells)[None, :]), d, peak, sc, j, rim)
        # black mass above the play area (v3 shape). final: a skirt of the darkest deck colour under it as the
        # intermediate shade, and both edges broken into hand clusters
        void = edge_e(VOID, 9)
        skirt = np.maximum(edge_e(SKIRT, 15), void + 6)
        fringe(sub, skirt, S.k0, SKYPAT[7], 5)
        fringe(sub, void, ramp[0], SKYPAT[2], 5)
    if mood == 'moon':                                              # cel-shaded disc: flat light, shade crescent, craters
        cx, cy, r = MOON
        sub.setm(disc, S.m3)
        sub.setm(disc & ((xx - (cx + 6)) ** 2 + (yy - (cy - 5)) ** 2 > (r - 1.5) ** 2), S.m2)
        sub.setm(disc & ((xx - (cx + 12)) ** 2 + (yy - (cy - 10)) ** 2 > (r + 4.5) ** 2), S.m1)
        for ex, ey, erx, ery in ((244, 32, 5, 3), (256, 41, 4, 5), (240, 45, 6, 3), (253, 27, 3, 2), (262, 33, 2, 3)):
            e = ((xx - ex) / erx) ** 2 + ((yy - ey) / ery) ** 2
            sub.setm(disc & (e <= 1) & (sub.a == S.m3), S.m2)
            sub.setm(disc & (e <= 1) & (yy < ey) & (xx < ex + 1) & (e > 0.35), S.m1)       # shaded inner rim
        for qx, qy in ((259, 50), (247, 24), (236, 38)):
            sub.px(qx, qy, S.m1)
            sub.px(qx + 1, qy + 1, S.m3)
    if mood == 'dusk':          # v3 sun: big, warm, flat. Orange body, dimmed red core and lower half, thin gold limb, cloud slits
        cx, cy, r = SUN
        t = (yy - (cy - r)) / (2.0 * r)
        sub.setm(disc, S.u2)
        core = (xx - cx) ** 2 + ((yy - (cy + 4)) * 1.15) ** 2 < (r * 0.6) ** 2
        sub.setm(disc & (core | (t > 0.56 + 0.03 * np.sin(xx / 4.0 + 1))), S.u3)
        sub.setm(disc & (rr > r - 2.2) & (yy < cy + 2), S.u1)
        for sy, sh in ((cy + 5, 1), (cy + 10, 1), (cy + 15, 2), (cy + 20, 2), (cy + 25, 3)):
            sub.setm(disc & (yy >= sy) & (yy < sy + sh), ramp[2])
    if mood != 'storm':
        rng = random.Random(5)
        lim = D['starlim']
        k = 0
        while k < (80 if mood == 'moon' else 26):
            x, y = rng.randrange(W), rng.randrange(SKYH)
            if Lt[y, x] < lim and not disc[y, x]:
                sub.px(x, y, S.t2 if rng.random() < 0.25 else S.t1)
                k += 1
        for x, y, ph in BIGSTARS:
            if Lt[y, x] < lim:
                v = (f + ph) % 4
                sub.px(x, y, S.t2 if v == 2 else S.t3)
                if v != 2:
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        sub.px(x + dx, y + dy, S.t2 if v == 0 else S.t1)
    cv.a[:SKYH], cv.da[:SKYH], cv.db[:SKYH] = sub.a, sub.da, sub.db
    return cv


# ---------------------------------------------------------------- clouds, airship, beams, rain
CLOUDS = {'front': (320, [(44, [(30, 9), (44, 13), (62, 10), (77, 7)]), (36, [(190, 8), (204, 12), (222, 15), (244, 11), (261, 8)])]),
          'back': (160, [(72, [(20, 4), (29, 6), (40, 4)]), (66, [(100, 4), (109, 6), (121, 7), (133, 4)])])}


def cloud_strip(which, f):
    per, groups = CLOUDS[which]
    C = Rl('C')
    cv = Cv(H, per)
    yy, xx = grid(H, per)
    for base, bumps in groups:
        m = np.zeros((H, per), bool)
        for cx, r in bumps:
            m |= ((xx - cx) ** 2 + ((yy - (base - r * 0.5)) * 1.25) ** 2 <= r * r)
        x0, x1 = bumps[0][0] - bumps[0][1] - 4, bumps[-1][0] + bumps[-1][1] + 4
        m |= (yy >= base - 3) & (yy < base) & (xx >= x0 + 4) & (xx < x1 - 4)
        m &= yy < base
        depth = np.zeros((H, per))
        cur = m.copy()
        for k in range(1, 7):
            cur &= np.roll(m, (k, -k), (0, 1))
            depth += cur
        cv.setm(m, C.c2)
        cv.dith(m & (depth < 5), np.clip(1 - depth / 4.5, 0, 1), C.c2, C.c3)
        cv.dith(m & (yy >= base - 6) & (depth >= 2), np.clip((yy - (base - 7)) / 6, 0, 1), C.c2, C.c1)
        cv.setm(m & ~np.roll(m, (1, -1), (0, 1)), C.c4)
        for j in range(3):                                           # trailing wisps, 4-frame loop
            y = base - 1 - 2 * j
            xa = x0 - 2 * j - (0, 1, 2, 1)[(f + j) % 4]
            cv.rect(xa, y, xa + 5 - j, y + 1, C.c2)
            xb = x1 - 6 + 2 * j + (0, 1, 2, 1)[(f + j + 2) % 4]
            cv.rect(xb, y, xb + 4 - j, y + 1, C.c1 if j == 0 else C.c2)
    return cv


def airship(f):
    Z = Rl('Z')
    cv = Cv(32, 64)
    yy, xx = grid(32, 64)
    cx, cy, rx, ry = 33, 11, 28, 10
    e = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
    for sgn in (-1, 1):                                            # tail fins
        for j in range(8):
            y = cy + sgn * (3 + j)
            cv.rect(2 + j // 2, y, 13 - j // 3, y + 1, Z.z2 if sgn < 0 else Z.z1)
        cv.rect(2, cy + sgn * 10, 10, cy + sgn * 10 + 1, Z.z4 if sgn < 0 else Z.z0)
    env = e <= 1
    v = (yy - (cy - ry)) / (2 * ry) + 0.12 * ((xx - cx) / rx)        # light from the upper right
    cv.setm(env, Z.z2)
    cv.dith(env & (v < 0.5), np.clip((0.5 - v) / 0.34, 0, 1), Z.z2, Z.z3)
    cv.dith(env & (v >= 0.52), np.clip((v - 0.52) / 0.36, 0, 1), Z.z2, Z.z1)
    for sx in (-20, -10, 0, 10, 20):
        for y in range(cy - ry, cy + ry + 1):
            q = 1 - ((y - cy) / ry) ** 2
            if q > 0:
                x = int(round(cx + sx * sqrt(q)))
                if env[y, x]:
                    cv.px(x, y, Z.z1 if y > cy - 5 else Z.z2)
    cv.rect(38, 5, 45, 10, Z.zp)
    cv.rect(38, 5, 45, 6, Z.z4)
    for qx in (38, 40, 42, 44):
        cv.px(qx, 10, Z.z0)
    cv.setm(env & ~np.roll(env, 1, 0), Z.z4)
    cv.setm(env & ~np.roll(env, -1, 0), Z.z0)
    cv.rect(24, 22, 44, 27, Z.z1)
    cv.rect(24, 22, 44, 23, Z.z3)
    cv.rect(24, 26, 44, 27, Z.z0)
    for wx in (28, 33, 38):
        cv.rect(wx, 24, wx + 2, 26, Z.l1)
    for sx in (27, 41):
        cv.rect(sx, 20, sx + 1, 22, Z.z0)
    ln = (5, 3, 1, 3)[f % 4]
    cv.rect(22, 25 - ln // 2, 23, 25 - ln // 2 + ln, Z.z4)
    cv.px(58, 16, Z.bk if f % 8 < 2 else Z.bd)
    return cv


BEAMS = [(223, 80, -1.92, 0.05), (66, 80, -1.22, -0.05)]


def beam_plane(f):
    X = Rl('X')
    cv = Cv(H, W)
    yy, xx = grid(H, W)
    tri = (0, 1, 2, 3, 4, 3, 2, 1)[f]
    for ox, oy, th0, dth in BEAMS:
        th = th0 + dth * tri
        dx, dy = xx - ox, yy - oy
        along = dx * cos(th) + dy * sin(th)
        across = np.abs(-dx * sin(th) + dy * cos(th))
        hw = 1.5 + along * 0.09
        m = (along > 0) & (along < 96) & (across < hw) & (yy < 80)
        cv.setm(m & (((xx + yy) & 1) == 0), X.bm)
        cv.setm(m & (across < hw * 0.35) & (along < 50), X.bm)
    return cv


RAIN_FULL = [1, 14]                          # full-height columns (kept clear of the GUM sign)
RAIN_SPLIT = [4, 6, 8, 11, 16, 19]             # columns with a gap
RAIN_GAP = (5, 9)                            # tile rows 5..8 (lines 80..143) stay free in the split columns
RAIN_SEEDS = [(3, 1), (11, 5), (6, 9), (14, 13), (9, 2)]


def rain_on(c, ty):
    return c in RAIN_FULL or (c in RAIN_SPLIT and not RAIN_GAP[0] <= ty < RAIN_GAP[1])


def rain_tile(f):
    X = Rl('X')
    t = np.zeros((16, 16), np.uint8)
    for sx, sy in RAIN_SEEDS:
        for j in range(5):
            t[(sy + 4 * f + j) % 16, (sx - 2 * f - j // 2) % 16] = X.rn1 if j >= 3 else X.rn2
    return t


def rain_plane(f):
    cv = Cv(H, W)
    t = rain_tile(f)
    for c in range(20):
        for ty in range(14):
            if rain_on(c, ty):
                cv.a[ty * 16:ty * 16 + 16, c * 16:c * 16 + 16] = np.roll(t, c * 5, 0)
    return cv


# ---------------------------------------------------------------- moods = palette sets
MOODS = {
    'moon': dict(
        title='Clear night, moon', hazard='water', ms=100, light=(60, 190, 210), lbase=1, lpc=(40, 80),
        sky=[(4, 4, 18), (26, 30, 84), (74, 58, 140), (136, 100, 180)],
        stars=[(96, 104, 160), (180, 190, 230), (255, 255, 255)], moon=[(120, 124, 176), (190, 196, 226), (246, 248, 255)],
        F=[(22, 20, 64), (30, 26, 80), (58, 56, 128), (84, 80, 160), (140, 136, 214)], Fhz=(98, 84, 172),
        A=[(10, 10, 40), (18, 20, 62), (40, 52, 112), (60, 80, 150), (120, 150, 220)], Ahz=(72, 66, 142),
        B=[(5, 6, 26), (10, 12, 40), (30, 42, 96), (48, 72, 136), (110, 160, 224)], Bhz=(52, 52, 118),
        N=[(2, 2, 10), (6, 7, 24), (24, 38, 84), (46, 76, 132), (120, 180, 230)],
        win=[(255, 246, 190), (255, 206, 104), (206, 124, 60)], tv=[(140, 224, 255), (64, 120, 214)],
        cloud=[(16, 18, 56), (44, 50, 112), (88, 100, 170), (176, 190, 240)],
        ship=[(10, 8, 30), (30, 22, 60), (78, 56, 104), (140, 104, 140), (220, 190, 200), (150, 70, 80)]),
    'storm': dict(
        title='Storm, rain and search beams', hazard='spikes', ms=70, light=(150, 210, 255), lbase=0, lpc=(55, 88),
        sky=[(6, 10, 18), (24, 48, 62), (48, 104, 116), (132, 176, 150)],
        deck=[(8, 12, 22), (34, 50, 66), (88, 112, 120)],
        F=[(16, 28, 38), (22, 38, 50), (50, 76, 88), (70, 104, 112), (140, 180, 180)], Fhz=(88, 124, 128),
        A=[(8, 14, 24), (14, 24, 36), (38, 60, 76), (58, 90, 104), (130, 180, 190)], Ahz=(60, 90, 100),
        B=[(4, 8, 14), (8, 14, 24), (28, 48, 64), (46, 78, 96), (140, 200, 210)], Bhz=(44, 68, 82),
        N=[(2, 3, 6), (5, 8, 14), (24, 42, 56), (44, 74, 90), (170, 220, 225)],
        win=[(240, 255, 220), (210, 236, 150), (120, 160, 90)], tv=[(150, 240, 255), (60, 130, 170)],
        cloud=[(8, 12, 22), (34, 50, 66), (88, 112, 120), (150, 180, 180)],
        ship=[(4, 8, 14), (14, 24, 36), (50, 76, 88), (100, 130, 130), (190, 220, 220), (120, 70, 60)]),
    'dusk': dict(
        title='Ember dusk, low sun', hazard='lava', ms=130, light=(255, 150, 62), lbase=1, lpc=(35, 75),
        sky=[(34, 16, 66), (112, 36, 100), (220, 92, 76), (255, 196, 112)],
        stars=[(150, 90, 150), (220, 170, 200), (255, 255, 255)], sun=[(255, 214, 110), (255, 138, 56), (232, 76, 84)],
        F=[(96, 34, 84), (112, 40, 92), (170, 70, 96), (214, 110, 100), (255, 190, 120)], Fhz=(236, 136, 96),
        A=[(52, 18, 66), (70, 24, 80), (126, 48, 98), (176, 80, 100), (255, 170, 110)], Ahz=(190, 90, 96),
        B=[(28, 10, 48), (40, 16, 62), (92, 36, 92), (140, 60, 100), (255, 160, 100)], Bhz=(140, 60, 96),
        N=[(10, 4, 22), (20, 8, 38), (64, 26, 78), (110, 48, 92), (255, 150, 90)],
        win=[(255, 250, 200), (255, 220, 120), (220, 130, 70)], tv=[(120, 230, 230), (50, 130, 160)],
        cloud=[(70, 24, 84), (150, 56, 100), (240, 120, 90), (255, 214, 150)],
        ship=[(20, 8, 36), (50, 20, 60), (112, 44, 84), (190, 90, 90), (255, 200, 130), (60, 90, 120)]),
}
# v2 value design. The v1 colours stay as hue anchors; luminances are set here.
#   skyl: luminance of each sky ramp colour (neighbours about 30 apart: that is the pair step of the cluster bands)
#   val:  luminance of wall roles w0..w3 per plane. Large shapes are kept above 24 so that dark fliers read
#         (lifted darks, haze); only outlines and small details go darker.
MOODS['moon'].update(sky=MOODS['moon']['sky'] + [(172, 132, 210)], skyl=[14, 44, 74, 104, 134], Fhzl=104,
                     val=dict(F=[28, 42, 72, 96], A=[14, 32, 62, 88], B=[8, 26.5, 55.5, 82], N=[4, 26.5, 45.5, 72]))
MOODS['storm'].update(skyl=[5, 44, 74, 104, 134], deck=MOODS['storm']['deck'] + [(124, 150, 150)], deckl=[39, 68, 97, 126],
                      val=dict(F=[28, 42, 72, 96], A=[14, 32, 62, 88], B=[8, 26.5, 55.5, 82], N=[4, 26.5, 45.5, 72]))
MOODS['dusk'].update(rimcap='N', skyl=[27.2, 57, 87, 117, 147, 177], Fhzl=138, sunl=[190, 148, 118], cloudl=[None, None, 142, None],
                     val=dict(F=[58, 72, 104, 136], A=[34, 46, 77, 108], B=[20, 29, 59, 87], N=[8, 26.5, 46, 72]))
GSTEP = (0, 30, 42, 54)          # luminance step of the cast-light pair (wall, lit wall) per palette level
UMIX = (0, 0.4, 0.65, 0.85)


def palette(mood, level=0, flash=0.0):
    M = MOODS[mood]
    P = {}
    sk = lum_ramp(M['sky'], M['skyl'])
    for i in range(6):
        P['S.s%d' % i] = sk[min(i, len(sk) - 1)]
    for i, c in enumerate(M.get('stars', [(0, 0, 0)] * 3)):
        P['S.t%d' % (i + 1)] = c
    for i, c in enumerate(M.get('moon', [(0, 0, 0)] * 3)):
        P['S.m%d' % (i + 1)] = c
    dk = lum_ramp(M['deck'], M['deckl']) if 'deck' in M else [(0, 0, 0)] * 4
    for i in range(4):
        P['S.k%d' % i] = dk[i]
    for i, c in enumerate(M.get('sun', [(0, 0, 0)] * 3)):
        P['S.u%d' % (i + 1)] = setlum(c, M['sunl'][i]) if 'sunl' in M else c
    for i, c in enumerate(M['cloud']):
        L = M.get('cloudl', [None] * 4)[i]
        P['C.c%d' % (i + 1)] = setlum(c, L) if L else c
    for n, c in zip(('z0', 'z1', 'z2', 'z3', 'z4', 'zp'), M['ship']):
        P['Z.' + n] = c
    P['Z.l1'] = M['win'][1]
    P['Z.bk'] = (255, 70, 70)
    P['Z.bd'] = mix(M['ship'][1], (200, 40, 50), 0.4)
    P['X.bm'] = setlum(mix(M['sky'][3], (255, 255, 255), 0.35), 147)      # under 150: beams do not hide a bubble
    P['X.rn1'] = mix(M['sky'][3], (255, 255, 255), 0.3)
    P['X.rn2'] = mix(M['sky'][2], M['sky'][3], 0.4)
    P['X.bird'] = M['N'][1]
    for pl in 'FABN':
        w = [setlum(c, L) for c, L in zip(M[pl][:4], M['val'][pl])] + [M[pl][4]]
        if pl in M.get('rimcap', ''):                 # near rim light just under 150, so that roof edges do not hide a bubble
            w[4] = setlum(w[4], 148)
        far = {'F': 0.45, 'A': 0.15, 'B': 0, 'N': 0}[pl]
        for i in range(5):
            P['%s.w%d' % (pl, i)] = w[i]
        hz = M.get(pl + 'hz', w[2])
        P[pl + '.hz'] = setlum(hz, M[pl + 'hzl']) if pl + 'hzl' in M else hz
        P[pl + '.wo'] = setlum(w[1], max(25.5, lum(w[1]) - 6))          # unlit glass: lifted, never a black hole
        P[pl + '.gl'] = setlum(mix(w[1], M['tv'][1], 0.3), 29)
        P[pl + '.l3'] = mix(M['win'][0], w[2], far)
        P[pl + '.l1'] = mix(M['win'][1], w[2], far)
        P[pl + '.l2'] = mix(M['win'][2], w[2], far)
        P[pl + '.t1'] = mix(M['tv'][0], w[2], far)
        P[pl + '.t2'] = mix(M['tv'][1], w[2], far)
        P[pl + '.bk'] = mix((255, 70, 70), w[2], far * 0.5)
        P[pl + '.bd'] = mix(w[1], (200, 40, 50), 0.4)
        P[pl + '.s1'] = mix(w[4], (255, 255, 255), 0.3)
        P[pl + '.s2'] = mix(w[3], w[4], 0.45)
        P[pl + '.n1'] = mix((255, 120, 200), w[2], far)
        P[pl + '.nh'] = (255, 226, 244)
        P[pl + '.n2'] = mix((180, 50, 140), w[2], far)
        P[pl + '.n3'] = mix((84, 24, 84), w[1], far)
        P[pl + '.c1'] = (100, 240, 255)
        P[pl + '.c2'] = (30, 130, 180)
        P[pl + '.fl1'] = (224, 60, 84)
        P[pl + '.fl2'] = (128, 28, 70)
        gm = GSTEP[level] / (lum(M['light']) - lum(w[2]))
        P[pl + '.u'] = mix(w[0], M['light'], UMIX[level])
        P[pl + '.uh'] = mix(w[0], M['light'], UMIX[level] * 0.5)
        P[pl + '.g'] = mix(w[2], M['light'], gm)
        P[pl + '.e'] = mix(w[2], M['light'], gm)
    if flash:
        for k in list(P):
            if k[0] in 'SFC' or k.startswith('A.w') or k.startswith('A.hz'):
                P[k] = mix(P[k], (214, 240, 255), flash if k[0] == 'S' else flash * 0.6)
    lut = np.zeros((256, 3), np.uint8)
    for i, n in enumerate(ROLES[1:], 1):
        lut[i] = P[n]
    return lut


# ---------------------------------------------------------------- hazard strips and cast-light levels
def load_hazard(name):
    fn = {'water': 'frames_M_water_1x.png', 'lava': 'frames_M_lava_1x.png', 'spikes': 'frames_H_spikes_1x.png'}[name]
    im = np.array(Image.open(os.path.join(HAZDIR, fn)).convert('RGBA'))
    nv = im.shape[0] // 32
    out = []
    for f in range(16):
        s = np.zeros((32, W, 4), np.uint8)
        for i in range(5):
            v = i % nv
            s[:, i * 64:i * 64 + 64] = im[v * 32:v * 32 + 32, f * 64:f * 64 + 64]
        out.append(s)
    return out


def light_levels(strips, base, pc):
    sig = np.array([[(lum(s[:24, c * 16:c * 16 + 16, :3].reshape(-1, 3).T.astype(float)) * (s[:24, c * 16:c * 16 + 16, 3].reshape(-1) > 0)).mean()
                     for c in range(20)] for s in strips])
    sig = 0.5 * sig + 0.25 * (np.roll(sig, 1, 1) + np.roll(sig, -1, 1))
    lo, hi = np.percentile(sig, pc)
    return base + (sig > lo).astype(int) + (sig > hi).astype(int)


def level_map(lev):
    """Cast-light palette level per pixel: one level per 16 px column over the whole near plane.
    The falloff with height is drawn in the tiles, so no level step crosses a tile row."""
    m = np.zeros((H, W), np.int64)
    for c in range(20):
        m[:, c * 16:c * 16 + 16] = max(0, min(3, int(lev[c])))
    return m


# ---------------------------------------------------------------- placeholders (not background art)
ISL = [(140, 156, 198), (90, 100, 160), (52, 60, 110), (28, 32, 70)]
ISLANDS = [(22, 116, 60), (126, 84, 68), (230, 124, 62)]
FLIERS = [(52, 78), (158, 40), (262, 92), (104, 150), (206, 168)]


def put_island(d, x, y, w):
    d[y, x:x + w] = ISL[0]
    d[y + 1:y + 4, x:x + w] = ISL[1]
    d[y + 1:y + 4, x + w - 3:x + w] = ISL[0]
    d[y + 4:y + 7, x + 3:x + w - 3] = ISL[2]
    d[y + 7:y + 9, x + 8:x + w - 8] = ISL[3]
    for i, rx in enumerate(range(x + 12, x + w - 10, 9)):
        d[y + 9:y + 11 + (i * 3) % 5, rx] = ISL[3]


def put_flier(d, x, y):
    for j in range(-7, 8):
        for i in range(-7, 8):
            r = sqrt(i * i + j * j)
            if r <= 6.6:
                c = (110, 34, 90) if r > 5.6 else (214, 104, 160) if i + j > 4 else (255, 176, 206)
                d[y + j, x + i] = c
    d[y - 3:y - 1, x - 3:x - 1] = (255, 255, 255)
    d[y + 7:y + 10, x] = (200, 200, 224)
    for j in range(8):
        hw = (2, 4, 5, 5, 5, 5, 4, 2)[j]
        d[y + 10 + j, x - hw:x + hw + 1] = (14, 10, 22)
    d[y + 10, x - 1:x + 3] = (58, 48, 84)
    d[y + 11, x + 3:x + 5] = (58, 48, 84)
    d[y + 13, x - 2] = d[y + 13, x + 2] = (255, 255, 255)


# ---------------------------------------------------------------- compose
def over(dst, idx, lut, ox=0, oy=0):
    h, w = idx.shape
    xa, xb = max(ox, 0), min(ox + w, W)
    ya, yb = max(oy, 0), min(oy + h, H)
    if xb <= xa or yb <= ya:
        return
    sub = idx[ya - oy:yb - oy, xa - ox:xb - ox]
    m = sub > 0
    dst[ya:yb, xa:xb][m] = lut[sub[m]]


def wrap_strip(idx, shift):
    per = idx.shape[1]
    return np.roll(np.tile(idx, (1, ceil(W / per) + 1)), shift % per, 1)[:, :W]


BIRDS = [(0, 0, 0), (9, 4, 1), (16, -3, 2), (25, 6, 3), (31, 0, 1)]
FLASH = {40: 0.5, 41: 0.22, 44: 0.4, 45: 0.12}
BOLT = [(204, 60), (200, 68), (205, 74), (198, 82), (201, 90), (195, 97), (197, 104)]


class Mood:
    def __init__(s, mood):
        s.mood = mood
        s.M = MOODS[mood]
        s.nfr = NFR[mood]
        s.sky = [sky_plane(mood, f) for f in range(4)]
        s.city = {k: [city_plane(k, f) for f in range(8)] for k in 'FAB'}
        s.near = [near_plane(f) for f in range(8)]
        s.cf = [cloud_strip('front', f) for f in range(4)]
        s.cb = [cloud_strip('back', f) for f in range(4)]
        s.ship = [airship(f) for f in range(8)]
        s.beam = [beam_plane(f) for f in range(8)]
        s.rain = [rain_plane(f) for f in range(8)]
        s.haz = load_hazard(s.M['hazard'])
        s.lev = light_levels(s.haz, s.M['lbase'], s.M['lpc'])
        s.luts = None

    def prep(s):
        s.luts = np.stack([palette(s.mood, k) for k in range(4)])
        s.flut = {v: palette(s.mood, 0, v) for v in set(FLASH.values())}

    def frame(s, g, actors=True):
        mood = s.mood
        f8, f4 = (g // 2) % 8, (g // 2) % 4
        lut = s.luts[0]
        if mood == 'storm' and g in FLASH:
            lut = s.flut[FLASH[g]]
        d = np.zeros((H, W, 3), np.uint8)
        d[:] = lut[rid('N.w1')]
        over(d, s.sky[f4].a, lut)
        ph = sin(TAU * g / s.nfr)
        if mood == 'storm':
            over(d, s.beam[f8].a, lut)
            if g in (40, 41, 44):
                for (xa, ya), (xb, yb) in zip(BOLT, BOLT[1:]):
                    for t in range(9):
                        x, y = round(xa + (xb - xa) * t / 8), round(ya + (yb - ya) * t / 8)
                        d[y, x:x + (2 if g != 41 else 1)] = (240, 250, 255)
        else:
            over(d, wrap_strip(s.cb[f4].a, round(160 * g / s.nfr)), lut)
            over(d, wrap_strip(s.cf[f4].a, round(320 * g / s.nfr)), lut)
        over(d, s.city['F'][f8].a, lut, -OFF + round(6 * ph))
        if mood != 'storm':
            ax = -70 + round((W + 90) * g / s.nfr)
            over(d, s.ship[f8].a, lut, ax, 54 + round(2 * sin(2 * TAU * g / s.nfr)))
        if mood == 'dusk':
            bx = -40 + round((W + 80) * ((g / s.nfr * 2) % 1))
            for ox, oy, bp in BIRDS:
                wv = (0, 1, 2, 1)[(g // 2 + bp) % 4]
                x, y = bx + ox, 40 + oy + round(3 * sin(TAU * g / s.nfr * 4 + ox))
                for i in range(1, 4):
                    for xx_ in (x - i, x + i):
                        if 0 <= xx_ < W:
                            d[y - (i * wv) // 2 + (1 if wv == 0 and i == 3 else 0), xx_] = lut[rid('X.bird')]
                if 0 <= x < W:
                    d[y, x] = lut[rid('X.bird')]
        over(d, s.city['A'][f8].a, lut, -OFF + round(4 * ph))
        over(d, s.city['B'][f8].a, lut, -OFF + round(2 * ph))
        n = s.near[f8].a
        lm = level_map(s.lev[g % 16])
        m = n > 0
        nl = s.luts.copy()
        if mood == 'storm' and g in FLASH:
            nl[0] = lut
        d[m] = nl[lm[m], n[m]]
        if actors:
            for x, y, w in ISLANDS:
                put_island(d, x, y, w)
            for x, y in FLIERS:
                put_flier(d, x, y)
        hz = s.haz[g % 16]
        hm = hz[..., 3] > 0
        d[HAZ_Y:][hm] = hz[..., :3][hm]
        if mood == 'storm':
            over(d, s.rain[g % 8].a, lut)
        return d


# ---------------------------------------------------------------- numbers
def tiles_of(frames, y0, y1):
    """Unique non-empty 16x16 tiles over all frames, animated tile positions, distinct frames."""
    seen, anim = set(), 0
    w = frames[0].shape[1]
    for ty in range(y0 // 16, ceil(y1 / 16)):
        for tx in range(w // 16):
            ts = [fr[ty * 16:ty * 16 + 16, tx * 16:tx * 16 + 16].tobytes() for fr in frames]
            if len(set(ts)) > 1:
                anim += 1
            for t in ts:
                if any(t):
                    seen.add(t)
    return len(seen), anim, len({fr.tobytes() for fr in frames})


def pack_palettes(frames, lut):
    """Greedy packing of tiles into 15-colour palettes (each tile uses one palette)."""
    sets = set()
    w = frames[0].shape[1]
    for fr in frames:
        for ty in range(fr.shape[0] // 16):
            for tx in range(w // 16):
                t = fr[ty * 16:ty * 16 + 16, tx * 16:tx * 16 + 16]
                cs = frozenset(tuple(lut[i]) for i in np.unique(t) if i)
                if cs:
                    sets.add(cs)
    assert all(len(c) <= 15 for c in sets), 'a tile needs more than 15 colours: %d' % max(len(c) for c in sets)
    pals = []
    for cs in sorted(sets, key=lambda c: -len(c)):
        for p in pals:
            if len(p | cs) <= 15:
                p |= cs
                break
        else:
            pals.append(set(cs))
    allc = set().union(*sets) if sets else set()
    return len(pals), [len(p) for p in pals], len(allc)


def dither_stats(cv, lut):
    ok = (cv.da > 0) & ((cv.a == cv.da) | (cv.a == cv.db))
    if not ok.any():
        return 0, 0.0, 0.0
    la = lut[cv.da[ok]].astype(float) @ np.array([0.299, 0.587, 0.114])
    lb = lut[cv.db[ok]].astype(float) @ np.array([0.299, 0.587, 0.114])
    st = np.abs(la - lb)
    return int(ok.sum()), float(np.median(st)), float(st.min())


def cols_used(frames, y0, y1):
    out = {}
    for ty in range(y0 // 16, ceil(y1 / 16)):
        u = np.zeros(frames[0].shape[1] // 16, bool)
        for fr in frames:
            u |= fr[ty * 16:ty * 16 + 16].reshape(16, -1, 16).any((0, 2))
        out[ty] = int(u.sum())
    return out


PLANES = [('S', 0, 128), ('F', 48, 128), ('A', 80, 144), ('B', 112, 176), ('N', 128, 224)]     # key, tile grid origin, end line


def crop(cvs, y0, y1):
    return [c.a[y0:y1] for c in cvs]


def sprite_lines(md):
    """Scenery sprites per scanline with every column sprite trimmed to its visible tiles.
    A tile is needed when any of its pixels shows in any frame of the loop (sway and animation included)."""
    need = {k: np.zeros((ceil((y1 - y0) / 16), (PW if k in 'FAB' else W) // 16), bool) for k, y0, y1 in PLANES}
    org = {k: y0 for k, y0, y1 in PLANES}
    for g in range(md.nfr):
        f8, f4 = (g // 2) % 8, (g // 2) % 4
        ph = sin(TAU * g / md.nfr)
        lay = [('S', md.sky[f4].a, 0), ('F', md.city['F'][f8].a, -OFF + round(6 * ph)), ('A', md.city['A'][f8].a, -OFF + round(4 * ph)),
               ('B', md.city['B'][f8].a, -OFF + round(2 * ph)), ('N', md.near[f8].a, 0)]
        cover = np.zeros((H, W), bool)
        for k, a, ox in reversed(lay):
            xa, xb = max(ox, 0), min(ox + a.shape[1], W)
            m = np.zeros((H, W), bool)
            m[:, xa:xb] = a[:, xa - ox:xb - ox] > 0
            ys, xs = np.nonzero(m & ~cover)
            nr, nc = need[k].shape
            ok = (ys >= org[k]) & (ys < org[k] + nr * 16)
            tid = ((ys[ok] - org[k]) // 16) * nc + (xs[ok] - ox) // 16
            need[k] |= (np.bincount(tid, minlength=nr * nc) > 0).reshape(nr, nc)
            cover |= m
    line = np.zeros(H, int)
    for k, y0, y1 in PLANES:
        for c in range(need[k].shape[1]):
            r = np.nonzero(need[k][:, c])[0]
            if len(r):
                line[y0 + r[0] * 16:min(y0 + (r[-1] + 1) * 16, H)] += 1
    return line


def extra_lines(md):
    """Mood extras per scanline: clouds, airship, birds or beams, rain. Second value: the rain part alone."""
    line = np.zeros(H, int)
    rain = np.zeros(H, int)
    if md.mood == 'storm':
        for ty, n in cols_used([c.a for c in md.beam], 0, 96).items():
            line[ty * 16:ty * 16 + 16] += n
        for c in range(20):
            for ty in range(14):
                if rain_on(c, ty):
                    rain[ty * 16:ty * 16 + 16] += 1
    else:
        for strip, sp in ((md.cf, 2), (md.cb, 1)):
            per = strip[0].a.shape[1]
            for ty, n in cols_used([c.a for c in strip], 0, 96).items():
                if n:
                    line[ty * 16:ty * 16 + 16] += ceil(n * W / per) + 1
        line[52:88] += 5
        if md.mood == 'dusk':
            line[32:56] += 4
    return line + rain, rain


def shares(bg, y0, y1):
    l = bg[y0:y1].astype(float) @ np.array([0.299, 0.587, 0.114])
    return 100 * (l < 24).mean(), 100 * (l > 150).mean(), np.percentile(l, 5), np.median(l), np.percentile(l, 95)


_V1 = []


def v1_frame(mood):
    """Frame 0 of v1 without actors, rendered by the v1 script itself (for the play-area numbers on equal terms)."""
    if not _V1:
        import importlib.util
        sys.dont_write_bytecode = True               # leave no __pycache__ in the v1 directory
        sp = importlib.util.spec_from_file_location('bg_v1', os.path.join(V1DIR, 'draw_backgrounds_v1.py'))
        mod = importlib.util.module_from_spec(sp)
        sp.loader.exec_module(mod)
        _V1.append(mod)
    md = _V1[0].Mood(mood)
    md.prep()
    return md.frame(0, actors=False)


def report(md, out):
    mood = md.mood
    lut = md.luts[0]
    P = lambda *a: out.append(' '.join(str(x) for x in a))
    P('== mood %s: %s (hazard %s, %d ms per hazard step in the GIF)' % (mood, md.M['title'], md.M['hazard'], md.M['ms']))
    planes = [('sky', crop(md.sky, 0, 128), md.sky[0], lut, lut),
              ('far', crop(md.city['F'], 48, 128), md.city['F'][0], lut, lut),
              ('midA', crop(md.city['A'], 80, 144), md.city['A'][0], lut, lut),
              ('midB', crop(md.city['B'], 112, 176), md.city['B'][0], lut, lut),
              ('near', crop(md.near, 128, 224), md.near[0], md.luts[1], md.luts[3])]
    if mood == 'storm':
        planes += [('beams', crop(md.beam, 0, 96), md.beam[0], lut, lut)]
    else:
        planes += [('clouds front', crop(md.cf, 16, 48), md.cf[0], lut, lut), ('clouds back', crop(md.cb, 48, 80), md.cb[0], lut, lut),
                   ('airship', crop(md.ship, 0, 32), md.ship[0], lut, lut)]
    tp = tt = ta = 0
    for name, frs, cv, dl, pl in planes:
        try:
            npal, sizes, ncol = pack_palettes(frs, pl)
        except AssertionError as e:
            raise AssertionError('%s %s: %s' % (mood, name, e))
        ut, an, nf = tiles_of(frs, 0, frs[0].shape[0])
        dn, dmed, dmin = dither_stats(cv, dl)
        tp += npal
        tt += ut
        ta += an
        P('  %-13s palettes %d (colours %s; %d distinct)  unique tiles %4d  animated tile positions %3d  loop frames %d  |  dither px %6d  median lum step %5.1f  min %5.1f'
          % (name, npal, sizes, ncol, ut, an, nf, dn, dmed, dmin))
        assert dn == 0 or dmin >= 28, (mood, name, dmin)
    if mood == 'storm':
        ns = len(RAIN_FULL) + 2 * len(RAIN_SPLIT)
        P('  rain          palettes 1 (colours [2])  unique tiles 8 (1 tile x 8 frames)  %d sprites (%d full columns, %d split around lines %d..%d), at most %d per line; mesh, not counted as dither'
          % (ns, len(RAIN_FULL), len(RAIN_SPLIT), RAIN_GAP[0] * 16, RAIN_GAP[1] * 16 - 1, len(RAIN_FULL) + len(RAIN_SPLIT)))
        tp += 1
        tt += 8
    steps = [dither_stats(md.near[0], md.luts[k])[1] for k in (1, 2, 3)]
    P('  near plane: packed with the level 3 lit palette (all roles distinct); 3 lit copies of each near palette, one level per 16 px column;')
    P('  near cast-light pair step at level 1 / 2 / 3: %.1f / %.1f / %.1f; at level 0 the light role equals the wall colour (no dither shown)' % tuple(steps))
    P('  totals: %d palettes (+ lit copies), %d unique tiles, %d animated tile positions' % (tp, tt, ta))
    ex, rain = extra_lines(md)
    line = sprite_lines(md) + ex
    worst = int(line.max())
    ys = np.where(line == worst)[0]
    P('  scenery sprites per scanline, column sprites trimmed to their visible tiles (hazard strip and gameplay not counted): worst %d at lines %d..%d (rain there: %d)'
      % (worst, ys[0], ys[-1], int(rain[ys[0]])))
    flat = np.zeros(H, int)
    flat[0:112] += 20
    flat[48:128] += 21
    flat[80:144] += 21
    flat[112:176] += 21
    flat[128:224] += 20
    flat += ex
    P('  same count with the v1 method (every plane counted full width over its whole height): worst %d at lines %d..%d' % (int(flat.max()), np.where(flat == flat.max())[0][0], np.where(flat == flat.max())[0][-1]))
    P('  per 16 lines, trimmed count: ' + ' '.join('%d' % line[y:y + 16].max() for y in range(0, H, 16)))
    assert worst <= (60 if mood == 'storm' else 58), (mood, worst)
    assert int(flat.max()) <= (65 if mood == 'storm' else 67), (mood, int(flat.max()))
    bg = md.frame(0, actors=False)
    for (y0, y1) in ((16, 176), (16, 192)):
        d, b, p5, med, p95 = shares(bg, y0, y1)
        P('  play area lines %d..%d: darker than 24: %.1f%%  brighter than 150: %.1f%%  (p5 %.0f median %.0f p95 %.0f)' % (y0, y1 - 1, d, b, p5, med, p95))
        if os.path.exists(os.path.join(V1DIR, 'draw_backgrounds_v1.py')) and '--nov1' not in sys.argv:
            if mood not in V1BG:
                V1BG[mood] = v1_frame(mood)
            d1, b1, q5, qm, q95 = shares(V1BG[mood], y0, y1)
            P('     v1, same lines:     darker than 24: %.1f%%  brighter than 150: %.1f%%  (p5 %.0f median %.0f p95 %.0f)' % (d1, b1, q5, qm, q95))
    d, b = shares(bg, 16, 176)[:2]
    assert d < 8 and b < 8, (mood, d, b)


V1BG = {}


# ---------------------------------------------------------------- output
def up(a, k):
    return np.repeat(np.repeat(a, k, 0), k, 1)


def save_gif(path, frs, ms, scale=3):
    packed = [(f[..., 0].astype(np.uint32) << 16) | (f[..., 1].astype(np.uint32) << 8) | f[..., 2] for f in frs]
    cols = np.unique(np.concatenate([np.unique(p) for p in packed]))
    if len(cols) <= 255:
        idx = [np.searchsorted(cols, p).astype(np.uint8) for p in packed]
        pal = [int(v) for c in cols for v in ((c >> 16) & 255, (c >> 8) & 255, c & 255)]
    else:
        mosaic = Image.fromarray(np.concatenate(frs[::max(1, len(frs) // 12)], 0), 'RGB').quantize(colors=255, dither=Image.Dither.NONE)
        idx = [np.array(Image.fromarray(f, 'RGB').quantize(palette=mosaic, dither=Image.Dither.NONE)) for f in frs]
        pal = mosaic.getpalette()[:255 * 3]
    pal = pal + [0] * (768 - len(pal))
    ims, prev = [], None
    for q in idx:
        dlt = q.copy()
        if prev is not None:
            dlt[q == prev] = 255                      # unchanged pixels stay transparent: small file
        prev = q
        im = Image.fromarray(up(dlt, scale), 'P')
        im.putpalette(pal)
        ims.append(im)
    ims[0].save(path, save_all=True, append_images=ims[1:], duration=ms, loop=0, disposal=1, transparency=255, optimize=False)
    return len(cols)


def plane_sheet(md, path):
    lut = md.luts[0]
    rows = [('sky plane, tiles, rows 0..127 (still)', md.sky[0].a[:128]),
            ('far skyline, rows 48..127, sway 6 px', md.city['F'][0].a[48:128]),
            ('mid skyline A, rows 88..143, sway 4 px', md.city['A'][0].a[88:144]),
            ('mid skyline B, rows 112..175, sway 2 px', md.city['B'][0].a[112:176]),
            ('near rooftops, rows 128..223, still, neutral palette', md.near[0].a[128:])]
    if md.mood == 'storm':
        rows.insert(1, ('search beams (checker mesh), behind the far skyline, 8 frames', md.beam[2].a[:88]))
        rows.append(('rain mesh tile, 8 frames (one 16 x 16 tile)', np.concatenate([rain_tile(f) for f in range(8)], 1)))
    else:
        rows.insert(1, ('cloud strips: front (period 320) and back (period 160), drift',
                        np.concatenate([md.cf[0].a[20:46], np.tile(md.cb[0].a[56:74], (1, 2))], 0)))
        rows.insert(3, ('airship, drifts (4 propeller frames, beacon)', np.concatenate([md.ship[f].a for f in range(4)], 1)))
    hh = sum(r[1].shape[0] * 2 + 20 for r in rows) + 2 * 96 + 20 + 8
    sheet = Image.new('RGB', (PW * 2 + 16, hh), (46, 46, 54))
    dr = ImageDraw.Draw(sheet)
    y = 4
    for label, a in rows:
        dr.text((8, y), label, fill=(230, 230, 236))
        y += 14
        rgb = np.zeros(a.shape + (3,), np.uint8)
        rgb[:] = (70, 70, 82)
        rgb[a > 0] = lut[a[a > 0]]
        sheet.paste(Image.fromarray(up(rgb, 2), 'RGB'), (8, y))
        y += a.shape[0] * 2 + 6
    dr.text((8, y), 'near rooftops with the cast-light palettes of hazard step 2 (one level per 16 px column; the fade is drawn in the tiles)', fill=(230, 230, 236))
    y += 14
    n = md.near[0].a
    lm = level_map(md.lev[2])
    rgb = np.zeros((H, W, 3), np.uint8)
    rgb[:] = (70, 70, 82)
    m = n > 0
    rgb[m] = md.luts[lm[m], n[m]]
    sheet.paste(Image.fromarray(up(rgb[128:], 2), 'RGB'), (8, y))
    sheet.save(path)


def compare_sheet(mood, still, path):
    """v3 still (left) and final still (right) at 2x, labelled."""
    sheet = Image.new('RGB', (W * 4 + 24, H * 2 + 30), (24, 25, 31))
    dr = ImageDraw.Draw(sheet)
    p2 = os.path.join(V3DIR, 'scene_%s_1x.png' % mood)
    if os.path.exists(p2):
        sheet.paste(Image.fromarray(up(np.array(Image.open(p2).convert('RGB')), 2), 'RGB'), (8, 22))
    sheet.paste(Image.fromarray(up(still, 2), 'RGB'), (W * 2 + 16, 22))
    dr.text((8, 6), 'v3  %s  (2x)' % mood, fill=(230, 230, 236))
    dr.text((W * 2 + 16, 6), 'final  %s  (2x)' % mood, fill=(230, 230, 236))
    sheet.save(path)


mds_by = {}


def plane_list(md):
    """Build input planes: (name, role-index art on its tile grid, palette level)."""
    ls = [('sky', md.sky[0].a[:128], 0), ('far', md.city['F'][0].a[48:128], 0), ('midA', md.city['A'][0].a[80:144], 0),
          ('midB', md.city['B'][0].a[112:176], 0), ('near', md.near[0].a[128:], 3)]
    if md.mood == 'storm':
        ls.append(('beams', md.beam[2].a[:88], 0))
    else:
        ls += [('cloudsfront', md.cf[0].a[16:48], 0), ('cloudsback', md.cb[0].a[48:80], 0),
               ('airship', np.concatenate([md.ship[f].a for f in range(4)], 1), 0)]
    return ls


def plane_pngs(md):
    out = []
    for name, a, lv in plane_list(md):
        rgb = np.zeros(a.shape + (3,), np.uint8)
        rgb[:] = TRANSP
        rgb[a > 0] = md.luts[lv][a[a > 0]]
        assert not ((rgb == TRANSP).all(2) & (a > 0)).any()
        Image.fromarray(rgb, 'RGB').save(os.path.join(HERE, 'plane_%s_%s_1x.png' % (md.mood, name)))
        out.append('%s %dx%d' % (name, a.shape[1], a.shape[0]))
    return '  build sheets (1x, transparent colour 255,0,255): ' + ', '.join(out)


def write_html(moods):
    h = ['<!doctype html><html><head><meta charset="utf-8"><title>Backgrounds final</title><style>',
         'body{background:#15161b;color:#d8d9df;font-family:Helvetica,Arial,sans-serif;margin:24px}',
         'img{image-rendering:pixelated;max-width:none;display:block;margin:8px 0 20px 0}',
         'h2{margin-top:40px;border-top:1px solid #3a3c46;padding-top:16px}p{max-width:960px;line-height:1.4}</style></head><body>',
         '<h1>Bubblegum Brawl backgrounds, final pass (five fixes on v3)</h1>',
         '<p>View at 100 percent browser zoom. Drafts only. Islands and fliers are placeholders; the hazard strips are the accepted dither drafts.</p>',
         '<h2>v3 against final</h2>']
    for m in moods:
        h.append('<p>%s: v3 left, final right, 2x</p><img src="compare_%s_2x.png" width="%d" height="%d" alt="compare %s">' % (MOODS[m]['title'], m, W * 4 + 24, H * 2 + 30, m))
    h.append('<h2>Animation</h2><p>3x: sway, drift, tile loops and cast light. The drift is faster than in the game so that the loop closes.</p>')
    for m in moods:
        h.append('<p>%s</p><img src="anim_%s_3x.gif" width="960" height="672" alt="animation %s">' % (MOODS[m]['title'], m, m))
    h.append('<h2>Scenes</h2>')
    for m in moods:
        h += ['<p>%s, still at 3x</p><img src="scene_%s_3x.png" width="960" height="672" alt="scene %s 3x">' % (MOODS[m]['title'], m, m),
              '<p>%s, still at true size</p><img src="scene_%s_1x.png" width="320" height="224" alt="scene %s 1x">' % (MOODS[m]['title'], m, m)]
    h.append('<h2>Planes</h2>')
    for m in moods:
        h.append('<p>%s: planes, each alone, at 2x</p><img src="planes_%s_2x.png" alt="planes %s">' % (MOODS[m]['title'], m, m))
    h.append('<h2>Build input sheets</h2><p>One sheet per plane and mood at true size, full tiling width. Transparent colour: magenta 255, 0, 255. '
             'The near sheet uses the level 3 lit palette so that the cast-light role is a colour of its own.</p>')
    for m in moods:
        for name, a, lv in plane_list(mds_by[m]):
            h.append('<p>%s: %s, %d x %d</p><img src="plane_%s_%s_1x.png" width="%d" height="%d" alt="plane %s %s">'
                     % (MOODS[m]['title'], name, a.shape[1], a.shape[0], m, name, a.shape[1], a.shape[0], m, name))
    h.append('</body></html>')
    open(os.path.join(HERE, 'index.html'), 'w').write('\n'.join(h) + '\n')


def main():
    only = sys.argv[sys.argv.index('--only') + 1].split(',') if '--only' in sys.argv else list(MOODS)
    out = []
    mds = [Mood(m) for m in only]
    for md in mds:
        md.prep()
        m = md.mood
        still = md.frame(4)
        Image.fromarray(still, 'RGB').save(os.path.join(HERE, 'scene_%s_1x.png' % m))
        Image.fromarray(up(still, 3), 'RGB').save(os.path.join(HERE, 'scene_%s_3x.png' % m))
        compare_sheet(m, still, os.path.join(HERE, 'compare_%s_2x.png' % m))
        plane_sheet(md, os.path.join(HERE, 'planes_%s_2x.png' % m))
        report(md, out)
        mds_by[m] = md
        out.append(plane_pngs(md))
        if '--nogif' not in sys.argv:
            frs = [md.frame(g) for g in range(md.nfr)]
            p = os.path.join(HERE, 'anim_%s_3x.gif' % m)
            nc = save_gif(p, frs, md.M['ms'])
            chk = Image.open(p)
            bad = 0
            for g in (0, 1, 41, md.nfr - 1):
                chk.seek(g)
                bad += int((np.array(chk.convert('RGB'))[::3, ::3] != frs[g]).any()) if nc <= 255 else 0
            out.append('  gif: %d frames, %d colours%s, %.2f MB, decode check on 4 frames: %s'
                       % (md.nfr, nc, '' if nc <= 255 else ' (reduced to 255)', os.path.getsize(p) / 1e6, 'equal' if not bad else '%d DIFFER' % bad))
    print('\n'.join(out))
    if len(only) == len(MOODS):
        open(os.path.join(HERE, 'numbers.txt'), 'w').write('\n'.join(out) + '\n')
        write_html(only)


# ================================================================ endless planes (Gum Trip): loop versions of the final set
# Every plane is drawn as a ring: each building is drawn at home and at +-P (P = plane width), so whatever crosses the
# join continues on the other side. The haze cluster strips are cut to P and repeated. Loop periods: far 336, midA 352,
# midB 368, near 384. Only the buildings that close the loop are new; everything else is the approved final art.
APPROVED = os.path.join(HERE, '..', '2026-11-10-backgrounds-final')
RING_PW = {'F': 336, 'A': 352, 'B': 368, 'N': 384}
RING_TAB = {
    'F': FAR,                                                               # 310 + 26 = 336: the last tower already ends on P
    'A': MIDA + [(338, 14, 100, 'step', 'glass')],                          # narrow glass tower, right edge on the join
    'B': MIDB + [(336, 32, 138, 'chim', 'deco')],                           # deco block with chimneys, right edge on the join
}
RING_K = {'F': 4, 'A': 8, 'B': 12, 'N': 16}                                 # parallax factor in sixteenths (tools/import_bg_sheet.py)
RING_ROWS = {'F': (48, 128), 'A': (80, 144), 'B': (112, 176), 'N': (128, 224)}
RING_NAME = {'F': 'far', 'A': 'midA', 'B': 'midB', 'N': 'near'}
RING_PAD = 64
BANDPAT_W = [band_pattern(b, 448) for b in range(len(BANDSEQ))]


def periodic_pats(pw, cw):
    """The haze cluster strips cut to the loop width and repeated, so the haze edge continues across the join."""
    return [np.tile(p[:, :pw], (1, ceil(cw / pw)))[:, :cw] for p in BANDPAT_W]


def ring_city(key, f):
    """city_plane drawn as a ring: canvas P + 96 wide, each building at dx 0, +P, -P. Returns the full canvas;
    the plane is canvas[:, :P], and canvas[:, P:P + 64] must equal canvas[:, 0:64] (continuation proof)."""
    global RING_DX
    st, pw = SPEC[key], RING_PW[key]
    tab = RING_TAB[key]
    R = Rl(key)
    cw = pw + RING_PAD + 32
    cv = Cv(H, cw)
    cv.rect(0, st.opq - 3, cw, st.y1, R.w2)
    order = sorted(range(len(tab)), key=lambda i: -tab[i][2] if key != 'F' else (i * 7) % 5)
    for i in order:
        x0, w, top, kind, ft = tab[i]
        seed = ord(key) * 100 + i
        for dx in (0, pw, -pw):
            RING_DX = dx
            x = x0 + dx
            furnish(cv, R, st, x, w, top, kind, seed, f, st.y0, ft)
            building(cv, R, st, x, w, top, st.y1, seed, f, ft=ft, kind=kind)
            if kind == 'sign':
                chevrons(cv, R, x + w - 12, top + 6, f)
    RING_DX = 0
    ya, yb, mx = st.haze
    yy, xx = grid(H, cw)
    pats = periodic_pats(pw, cw)
    for b in st.hz_on:
        base = rid(key + '.' + b)
        t = np.clip((yy - ya) / (yb - ya), 0, 1)
        if key == 'F':
            clus(cv, cv.a == base, band(t, 0.25, 0.5), base, R.hz, 3, pats)
        else:
            clus(cv, cv.a == base, band(t, 0.3, 0.45), base, R.hz, 1 if key == 'A' else 6, pats)
    cv.a[:st.y0] = 0
    cv.a[st.y1:] = 0
    assert (cv.a[st.opq:st.y1] > 0).all(), key
    return cv


class WrapCv(Cv):
    """Canvas that wraps in x: a rect or pixel past either edge lands on the other side (near ring)."""

    def rect(s, x0, y0, x1, y1, c):
        x0, x1 = int(x0), int(x1)
        if x1 - x0 >= s.w:
            Cv.rect(s, 0, y0, s.w, y1, c)
            return
        a = x0 % s.w
        b = a + (x1 - x0)
        Cv.rect(s, a, y0, min(b, s.w), y1, c)
        if b > s.w:
            Cv.rect(s, 0, y0, b - s.w, y1, c)

    def px(s, x, y, c):
        Cv.px(s, int(x) % s.w, y, c)


def snap_lut(lut):
    """Snap a palette to the 5-bit grid exactly as tools/import_bg_sheet.py snap5 does (round half to even)."""
    q = np.array([[round(int(v) * 31 / 255) for v in c] for c in lut], np.int64)
    return ((q << 3) | (q >> 2)).astype(np.uint8)


def off_grid(rgbs):
    q = np.round(rgbs.astype(np.int64) * 31 / 255).astype(np.int64)
    return int(((((q << 3) | (q >> 2)) != rgbs)).any(1).sum())


def to_rgb(a, lut):
    rgb = np.zeros(a.shape + (3,), np.uint8)
    rgb[:] = TRANSP
    rgb[a > 0] = lut[a[a > 0]]
    return rgb


def seam_rows(rgb):
    """(rows where the last column differs from the first, rows where opacity differs = building cut, interior median)."""
    op = ~(rgb == TRANSP).all(2)
    dif = int((rgb[:, -1] != rgb[:, 0]).any(1).sum())
    cut = int((op[:, -1] != op[:, 0]).sum())
    inner = (rgb[:, 1:] != rgb[:, :-1]).any(2).sum(0)
    return dif, cut, int(np.median(inner))


def tiles(arrs):
    s = set()
    for a in arrs:
        for ty in range(0, a.shape[0], 16):
            for tx in range(0, a.shape[1], 16):
                t = a[ty:ty + 16, tx:tx + 16]
                if t.any():
                    s.add(t.tobytes())
    return len(s)


def ranges(cols):
    out = []
    for c in sorted(cols):
        if not out or c != out[-1][1] + 1:
            out.append([c, c])
        else:
            out[-1][1] = c
    return [tuple(r) for r in out]


def ring_planes():
    rp, proof = {}, {}
    for key in 'FAB':
        cvs = [ring_city(key, f) for f in range(8)]
        pw = RING_PW[key]
        proof[key] = sum(int((c.a[:, pw:pw + RING_PAD] != c.a[:, :RING_PAD]).any(0).sum()) for c in cvs)
        rp[key] = [c.a[:, :pw].copy() for c in cvs]
    rp['N'] = [near_plane(f, NB5, RING_PW['N'], WrapCv).a for f in range(8)]
    return rp, proof


def slide(a, off):
    return np.take(a, (np.arange(W) + off) % a.shape[1], axis=1)


def ring_scene(md, rp, s, g, near=True, actors=False, haz=True):
    """One screen at camera px s: plane screen x = plane x - s * k / 16, wrapped at the loop width."""
    mood = md.mood
    f8, f4 = (g // 2) % 8, (g // 2) % 4
    lut = md.luts[0]
    d = np.zeros((H, W, 3), np.uint8)
    d[:] = lut[rid('N.w1')]
    over(d, md.sky[f4].a, lut)
    if mood == 'storm':
        over(d, md.beam[f8].a, lut)
    else:
        over(d, wrap_strip(md.cb[f4].a, round(160 * g / md.nfr)), lut)
        over(d, wrap_strip(md.cf[f4].a, round(320 * g / md.nfr)), lut)
    over(d, slide(rp['F'][f8], (s * 4) >> 4), lut)
    if mood != 'storm':
        over(d, md.ship[f8].a, lut, 150, 54)
    over(d, slide(rp['A'][f8], (s * 8) >> 4), lut)
    over(d, slide(rp['B'][f8], (s * 12) >> 4), lut)
    if near:
        n = slide(rp['N'][f8], s)
        lm = level_map(md.lev[g % 16])
        m = n > 0
        d[m] = md.luts[lm[m], n[m]]
        if actors:
            for x, y, w in ISLANDS:
                put_island(d, x, y, w)
        if haz:
            hz = md.haz[g % 16]
            hm = hz[..., 3] > 0
            d[HAZ_Y:][hm] = hz[..., :3][hm]
    return d


def join_x(s):
    return {RING_NAME[k]: (-((s * RING_K[k]) >> 4)) % RING_PW[k] for k in 'FABN'}


def centred_s():
    best = None
    for s in range(0, 400000):
        j = join_x(s)
        e = max(abs(j[n] - 160) for n in ('far', 'midA', 'midB', 'near'))
        if best is None or e < best[0]:
            best = (e, s)
        if e <= 2:
            break
    return best[1]


def endless_main():
    out = ['Endless planes, final set as loops. Generated by draw_endless_planes_final.py. Colours are snapped to the 5-bit grid',
           'exactly as tools/import_bg_sheet.py snap5 does. Seam = wrapping column W-1 next to column 0: rows (of the sheet height)',
           'whose pixels differ / rows where opacity differs (a building cut). Interior median = same count between neighbouring',
           'columns inside the plane. Tiles = unique non-empty 16x16 tiles of the loop, union over its 8 animation frames.',
           'Approved = the role-index art of the final set, drawn by the same code in this run (and checked against the PNGs on disk).', '']
    rp, proof = ring_planes()
    out.append('Continuation proof (ring canvas drawn 64 px past the loop end equals columns 0..63, columns that differ over 8 frames):')
    out.append('  ' + ', '.join('%s %d of 64' % (RING_NAME[k], proof[k]) for k in 'FAB')
               + '; near is drawn on a canvas that wraps in x (no element crosses the join except the wrapped cornice overhang).')
    j_s = centred_s()
    out.append('Mock-up camera positions: 0, 96, and %d (all four joins near screen x 160: %s)' % (j_s, join_x(j_s)))
    out.append('')
    summary, html_data = [], {}
    for m in MOODS:
        md = Mood(m)
        md.prep()
        appr = {'F': md.city['F'], 'A': md.city['A'], 'B': md.city['B'], 'N': md.near}
        # 1. the copied code still draws the approved PNGs (frame 0, unsnapped palette)
        rep = []
        for name, a, lv in plane_list(md):
            disk = np.array(Image.open(os.path.join(APPROVED, 'plane_%s_%s_1x.png' % (m, name))).convert('RGB'))
            rep.append('%s %s' % (name, 'equal' if disk.shape == to_rgb(a, md.luts[lv]).shape and (disk == to_rgb(a, md.luts[lv])).all() else 'DIFFERS'))
        cnt0 = {name: len(np.unique(to_rgb(a, md.luts[lv]).reshape(-1, 3), axis=0)) for name, a, lv in plane_list(md)}
        md.luts = np.stack([snap_lut(l) for l in md.luts])
        md.flut = {k: snap_lut(v) for k, v in md.flut.items()}
        out.append('== %s ==' % MOODS[m]['title'])
        out.append('  copied code against the approved sheets on disk: ' + ', '.join(rep))
        # 2. sheets
        sheets = {'sky': (md.sky[0].a[:128], 0), 'far': (rp['F'][0][48:128], 0), 'midA': (rp['A'][0][80:144], 0),
                  'midB': (rp['B'][0][112:176], 0), 'near': (rp['N'][0][128:], 3)}
        for name, a, lv in plane_list(md)[5:]:
            sheets[name] = (a, lv)
        merged = []
        for name, (a, lv) in sheets.items():
            rgb = to_rgb(a, md.luts[lv])
            Image.fromarray(rgb, 'RGB').save(os.path.join(HERE, 'plane_%s_%s_1x.png' % (m, name)))
            n1 = len(np.unique(rgb.reshape(-1, 3), axis=0))
            if name in ('sky', 'cloudsfront', 'cloudsback', 'airship', 'beams') and n1 != cnt0[name]:
                merged.append('%s %d -> %d' % (name, cnt0[name], n1))
        out.append('  sheets written: ' + ', '.join('%s %dx%d' % (n, a.shape[1], a.shape[0]) for n, (a, lv) in sheets.items())
                   + '; unchanged planes are the approved art, snapped' + ('; colour merges from the snap: ' + ', '.join(merged) if merged else
                                                                              ', no colours merge'))
        # 3. per plane and frame
        for k in 'FABN':
            y0, y1 = RING_ROWS[k]
            lv = 3 if k == 'N' else 0
            pw = RING_PW[k]
            aw = appr[k][0].a.shape[1]
            chg = set()
            for f in range(8):
                ra, aa = rp[k][f][y0:y1, :aw], appr[k][f].a[y0:y1]
                chg |= set(np.nonzero((ra != aa).any(0))[0].tolist())
            red = ranges(chg | set(range(aw, pw)))
            outside = 0
            rows = []
            for f in range(8):
                ra, aa = rp[k][f][y0:y1, :aw], appr[k][f].a[y0:y1]
                dcols = np.nonzero((ra != aa).any(0))[0]
                inside = np.zeros(aw, bool)
                for a_, b_ in red:
                    inside[a_:min(b_, aw - 1) + 1] = True
                outside += int(((ra != aa) & ~inside[None, :]).sum())
                rgb = to_rgb(rp[k][f][y0:y1], md.luts[lv])
                cols = np.unique(rgb[~(rgb == TRANSP).all(2)], axis=0)
                dif, cut, med = seam_rows(rgb)
                adif, acut, amed = seam_rows(to_rgb(appr[k][f].a[y0:y1], md.luts[lv]))
                rows.append('    frame %d: seam %d/%d rows (approved %d/%d), interior median %d, colours %d, off grid %d, changed columns %d'
                            % (f, dif, cut, adif, acut, med, len(cols), off_grid(cols), len(dcols)))
            nt = tiles([rp[k][f][y0:y1] for f in range(8)])
            at = tiles([appr[k][f].a[y0:y1] for f in range(8)])
            ncol = len(np.unique(np.concatenate([to_rgb(rp[k][f][y0:y1], md.luts[lv]).reshape(-1, 3) for f in range(8)]), axis=0)) - 1
            out.append('  %s: width %d (approved %d), unique tiles %d (approved %d), colours over 8 frames %d, redrawn ranges %s, '
                       'differences outside the redrawn ranges %d' % (RING_NAME[k], pw, aw, nt, at, ncol,
                                                                       ' '.join('%d..%d' % r for r in red), outside))
            out += rows
            summary.append((MOODS[m]['title'], RING_NAME[k], pw, red, seam_rows(to_rgb(rp[k][0][y0:y1], md.luts[lv]))[:2], nt, ncol, outside))
        # 4. pictures
        html_data[m] = ring_pictures(md, rp, j_s)
        out.append('')
    open(os.path.join(HERE, 'numbers.txt'), 'w').write('\n'.join(out) + '\n')
    ring_html(html_data, j_s)
    print('\n'.join(out))
    print('SUMMARY')
    for r in summary:
        print(r)


def ring_pictures(md, rp, j_s):
    m = md.mood
    bg = np.array((46, 46, 54), np.uint8)
    for k in 'FABN':
        y0, y1 = RING_ROWS[k]
        rgb = to_rgb(rp[k][0][y0:y1], md.luts[3 if k == 'N' else 0])
        rgb[(rgb == TRANSP).all(2)] = bg
        Image.fromarray(up(np.concatenate([rgb, rgb], 1), 2), 'RGB').save(os.path.join(HERE, 'strip_%s_%s_2x.png' % (m, RING_NAME[k])))
    for tag, s in (('start', 0), ('between', 96), ('join', j_s)):
        Image.fromarray(up(ring_scene(md, rp, s, 4), 2), 'RGB').save(os.path.join(HERE, 'mock_%s_%s_2x.png' % (m, tag)))
    # GIF: camera 1 px per frame (near speed); far, midA and midB at their parallax speeds over the sky, the joins pass the
    # centre in the middle. Animation steps from elapsed time at 20 ms per GIF frame against the mood's step time.
    n = 192
    frs = []
    for i in range(n):
        g = (i * 20) // md.M['ms']
        frs.append(ring_scene(md, rp, j_s - n // 2 + i, g, near=False)[40:176])
    p = os.path.join(HERE, 'scroll_%s_1x.gif' % m)
    save_gif(p, frs, 20, scale=1)
    return [(t, s, join_x(s)) for t, s in (('start', 0), ('between', 96), ('join', j_s))]


def ring_html(data, j_s):
    h = ['<!doctype html><html><head><meta charset="utf-8"><title>Endless planes final</title><style>',
         'body{background:#17181c;color:#d8d9df;font-family:Helvetica,Arial,sans-serif;margin:24px}',
         'img{image-rendering:pixelated;display:block;max-width:none}',
         '.wrap{position:relative;padding-top:22px;margin:6px 0 22px 0;overflow-x:auto}',
         '.tick{position:absolute;top:0;width:2px;height:20px;background:#ffd34a}',
         '.lab{position:absolute;top:2px;font-size:12px;color:#ffd34a;white-space:nowrap}',
         'h2{margin-top:40px;border-top:1px solid #3a3c46;padding-top:16px}p{max-width:980px;line-height:1.4}</style></head><body>',
         '<h1>Gumbirds endless planes: the final background set as loops</h1>',
         '<p>Drafts only. Loop widths: far 336, middle A 352, middle B 368, near 384 pixels. The yellow ticks above the pictures '
         'mark the join; they are not part of the art. See README.md and numbers.txt.</p>']
    for m, scenes in data.items():
        t = MOODS[m]['title']
        h.append('<h2>%s</h2><h3>Each plane tiled twice, 2x</h3>' % t)
        for k in 'FABN':
            pw = RING_PW[k]
            y0, y1 = RING_ROWS[k]
            h.append('<p>%s plane, loop width %d pixels</p><div class="wrap" style="width:%dpx">' % (
                {'F': 'Far', 'A': 'Middle A', 'B': 'Middle B', 'N': 'Near'}[k], pw, pw * 4))
            for x in (0, pw * 2):
                h.append('<div class="tick" style="left:%dpx"></div><div class="lab" style="left:%dpx">Join</div>' % (max(x - 1, 0), x + 5))
            h.append('<img src="strip_%s_%s_2x.png" width="%d" height="%d" alt="%s %s plane tiled twice"></div>' % (
                m, RING_NAME[k], pw * 4, (y1 - y0) * 2, t, RING_NAME[k]))
        h.append('<h3>Full scene at three camera positions, 2x (islands and fliers left out so the joins stay visible)</h3>')
        for tag, s, jx in scenes:
            h.append('<p>Camera at %d pixels%s</p><div class="wrap" style="width:640px;padding-top:%dpx">' % (
                s, ', every join near the centre' if tag == 'join' else '', 22 * 4))
            for i, k in enumerate(('far', 'midA', 'midB', 'near')):
                if jx[k] < W:
                    h.append('<div class="tick" style="left:%dpx;top:%dpx"></div><div class="lab" style="left:%dpx;top:%dpx">%s join</div>' % (
                        jx[k] * 2 - 1, i * 22, jx[k] * 2 + 5, i * 22 + 2,
                        {'far': 'Far', 'midA': 'Middle A', 'midB': 'Middle B', 'near': 'Near'}[k]))
            h.append('<img src="mock_%s_%s_2x.png" width="640" height="448" alt="%s scene, camera %d"></div>' % (m, tag, t, s))
        h.append('<h3>Scrolling through the joins, 2x display of a 1x GIF</h3><p>Camera moves 1 pixel per frame at 20 milliseconds per frame. '
                 'Far, middle A and middle B move at their parallax speeds (quarter, half and three quarters) over the sky; '
                 'all three joins pass the centre halfway through.</p>')
        h.append('<img src="scroll_%s_1x.gif" width="640" height="272" alt="%s scrolling through the joins">' % (m, t))
    h.append('<h2>Build input sheets, true size</h2><p>Transparent colour magenta 255, 0, 255. Colours on the 5-bit grid.</p>')
    for m in data:
        for name in ('sky', 'far', 'midA', 'midB', 'near'):
            h.append('<p>%s, %s</p><img src="plane_%s_%s_1x.png" alt="%s %s sheet">' % (MOODS[m]['title'], name, m, name, m, name))
    h.append('</body></html>')
    open(os.path.join(HERE, 'index.html'), 'w').write('\n'.join(h) + '\n')


if __name__ == '__main__':
    endless_main() if '--final' not in sys.argv else main()
