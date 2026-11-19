#!/opt/homebrew/bin/python3.14 -I
"""Background drafts v2 for Bubblegum Brawl (fix pass on v1): sky tile plane + 6 city depth planes, three moods.

Run:  /opt/homebrew/bin/python3.14 -I draw_backgrounds_v2.py [--nogif] [--only moon,storm,dusk]
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
W, H = 320, 224
PW, OFF = 336, 8            # swaying planes are 21 tiles wide; screen x = plane x - OFF + sway
HAZ_Y = 192
NFR = {'moon': 80, 'dusk': 80, 'storm': 64}     # GIF frames per loop (multiples of 16 hazard steps), sized to stay under 3 MB
TAU = 2 * pi


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
    dk = R.w1 if st.far else R.wo
    y = top + (3 if k < 2 else 6)
    if ft == 'office':
        pat = OFFICE_LIT[seed % 2]
        rh = 1 if st.far else wh
        row = 0
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
            y += gy
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
                cv.rect(px_, yq, px_ + ww, yq + gy - 1, R.l1 if ch == '#' else R.l2 if ch == '+' else dk)
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


def building(cv, R, st, x, w, top, bot, seed, f, wins=True, ft='apt', kind=None):
    rng = random.Random(seed)
    x1 = x + w
    cv.rect(x, top, x1, bot, R.w2)
    if st.glen:
        yy, xx = grid(cv.h, cv.w)
        m = (xx >= x) & (xx < x1) & (yy >= top) & (yy < bot)
        dens = np.clip((yy - (top + st.g0)) / st.glen, 0, 1)
        dens = np.maximum(dens, np.clip(1 - (xx - x) / 6, 0, 1) * 0.75)        # form shadow on the left
        cv.dith(m, dens, R.w2, R.w1)
    flip = st.far and x + w / 2 > 262                    # far towers right of the moon / sun are lit from the left
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
            y += 1


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
    elif kind == 'sign':
        cv.rect(x + 4, top - 3, x + 12, top, R.w1)
        cv.rect(x + 4, top - 4, x + 12, top - 3, R.w3)


# (x, width, roof line, roof kind, facade type): the facade types are placed by hand so that neighbours differ
FAR = [(0, 20, 92, 'flat', 'apt'), (18, 16, 80, 'step', 'glass'), (34, 24, 98, 'flat', 'office'), (56, 16, 78, 'spire', 'deco'),
       (72, 28, 88, 'step', 'apt'), (98, 18, 102, 'flat', 'ware'), (114, 20, 84, 'dome', 'deco'), (134, 26, 94, 'flat', 'office'),
       (158, 14, 76, 'spire', 'glass'), (172, 24, 86, 'step', 'apt'), (194, 22, 100, 'flat', 'ware'), (214, 18, 74, 'step', 'deco'),
       (232, 28, 92, 'flat', 'glass'), (258, 14, 80, 'spire', 'apt'), (272, 24, 104, 'flat', 'office'), (294, 18, 82, 'step', 'glass'),
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
            cv.dith(cv.a == base, t * mx, base, R.hz)
    cv.a[:st.y0] = 0
    cv.a[st.y1:] = 0
    assert (cv.a[st.opq:st.y1] > 0).all(), key
    return cv


# ---------------------------------------------------------------- near rooftops (still plane, takes the cast light)
NB = [(0, 58, 160, 11, 'brick'), (62, 146, 152, 12, 'panel'), (150, 234, 166, 13, 'metal'), (238, 320, 150, 14, 'pier')]
NWIN = {'brick': (13, 14, 5, 6), 'panel': (16, 13, 9, 6), 'metal': (14, 24, 6, 4), 'pier': (10, 15, 5, 9)}     # pitch x, pitch y, window w, h
GLYPH = {'G': (".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".###."),
         'U': ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
         'M': ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#")}
# hand-set wobble of the cast-light bands in lines, one entry per 4 px, so that no band edge is a ruled line
WOB = [0, 1, 1, 2, 3, 3, 2, 1, 0, 0, -1, -2, -2, -1, 0, 1, 2, 2, 1, 0,
       -1, -1, 0, 1, 3, 4, 3, 2, 1, 1, 0, -1, -2, -3, -2, -1, 0, 0, 1, 2,
       2, 1, 0, -1, 0, 1, 2, 3, 2, 1, 0, -1, -2, -1, 0, 1, 1, 2, 1, 0,
       -1, -2, -3, -2, -1, 0, 1, 2, 3, 2, 1, 0, 0, -1, -1, 0, 1, 2, 1, 0]
STAINS = [(0, 0, 4), (2, 0, 6), (3, 1, 3), (1, 1, 5), (2, 2, 4), (0, 2, 3)]      # (window column, window row, drip length)


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


def near_plane(f):
    cv = Cv(H, W)
    R = Rl('N')
    yy, xx = grid(H, W)
    cv.rect(0, 176, W, H, R.w1)
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
    for (x0, x1, top, seed, mat) in NB:
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
        px_ = x0 + (x1 - x0) * 2 // 3 + 1                               # drain pipe with brackets
        cv.rect(px_, top + 4, px_ + 1, H, R.w3)
        cv.rect(px_ + 1, top + 4, px_ + 2, H, R.w0)
        for by in range(top + 12, H, 16):
            cv.rect(px_ - 1, by, px_ + 3, by + 1, R.w0)
    # hazard cast light: role g is the wall colour in the neutral palette and the lit wall colour in the lit palettes.
    # The fade is drawn in the tiles as ordered meshes (full, 3/4, 1/2, 1/4, 1/8, 1/16), each a subset of the one below,
    # with hand-wobbled band edges. The palette level is one per 16 px column for the whole height: no step across tile rows.
    h = 192 - yy + np.array(WOB)[(xx // 4) % len(WOB)]
    wall = (cv.a == R.w2) & (yy >= 140)
    e2 = (xx % 2 == 1) & (yy % 2 == 1)
    pat = np.select([h < 5, h < 11, h < 20, h < 30, h < 40, h < 48],
                    [np.ones((H, W), bool), ~((xx % 2 == 0) & (yy % 2 == 0)), (xx + yy) % 2 == 0, e2,
                     e2 & ((xx // 2 + yy // 2) % 2 == 0), (xx % 4 == 1) & (yy % 4 == 1)], False)
    cv.a[wall & pat] = R.g
    z = wall & (h >= 5) & (h < 48)
    cv.da[z] = R.w2
    cv.db[z] = R.g
    # GUM sign
    bx0, by0 = 244, 129
    cv.rect(bx0, by0, bx0 + 64, by0 + 18, R.w0)
    cv.rect(bx0, by0, bx0 + 64, by0 + 1, R.w4)
    cv.rect(bx0 + 63, by0, bx0 + 64, by0 + 18, R.w3)
    for lx in (252, 298):
        cv.rect(lx, by0 + 18, lx + 2, 150, R.w1)
    tube = np.zeros((H, W), bool)
    dim = np.zeros((H, W), bool)
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


def band_pattern(b):
    seq, off = BANDSEQ[b % len(BANDSEQ)]
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


BANDPAT = [band_pattern(b) for b in range(len(BANDSEQ))]


def clus(cv, m, q, ca, cb, b):
    """Inside mask m: colour ca where q <= 0, cb where q >= 1; between, the hand-authored cluster strips of band edge b.
    The strip row follows q, so the clusters bend along the wisps and the halo."""
    yy, xx = grid(cv.h, cv.w)
    r = np.clip((q * NQ).astype(int), 0, NQ - 1)
    on = np.where(q >= 1, True, np.where(q <= 0, False, BANDPAT[b][r, xx]))
    cv.a[m & on] = cb
    cv.a[m & ~on] = ca
    z = m & (q > 0) & (q < 1)
    cv.da[m] = 0
    cv.da[z] = ca
    cv.db[z] = cb


SKYDEF = {
    'moon': dict(n=5, ys=[0, 10, 22, 66, 108, 128], ls=[0.15, 0.33, 1.0, 2.0, 3.0, 3.6], wk=1.3, halo=(1.3, 34), starlim=2.1,
                 wisps=[(60, 40, 46, 7, .55), (150, 62, 60, 6, .5), (250, 86, 70, 8, .6), (20, 78, 40, 6, .5), (110, 26, 34, 5, .4),
                        (196, 28, 30, 4, -.3), (300, 58, 36, 6, .45), (90, 98, 56, 7, .5), (180, 104, 50, 6, -.4)]),
    'storm': dict(n=5, ys=[0, 56, 96, 128], ls=[0.5, 1.4, 2.6, 3.6], wk=1.3,
                  wisps=[(50, 78, 60, 7, .5), (170, 88, 70, 6, .5), (280, 74, 50, 6, .45), (110, 104, 60, 6, -.4), (230, 110, 60, 7, .5)]),
    'dusk': dict(n=6, ys=[0, 30, 72, 110, 128], ls=[0, 0.7, 2.1, 3.5, 4.2], wk=1.6, cap=4.25, halo=(1.4, 28), starlim=1.1,
                 wisps=[(70, 28, 60, 5, .5), (210, 20, 70, 4, .45), (140, 52, 80, 6, .6), (286, 44, 50, 5, .5), (40, 80, 70, 6, .6),
                        (160, 92, 90, 5, .5), (100, 10, 40, 3, .3)]),
}
BIGSTARS = [(22, 14, 0), (70, 8, 2), (118, 34, 1), (150, 12, 3), (196, 44, 2), (300, 12, 1), (44, 46, 3), (176, 30, 0), (96, 56, 2), (8, 60, 1)]
DECK1 = [(-6, 30, 30), (34, 36, 26), (74, 28, 34), (118, 40, 24), (150, 30, 30), (192, 38, 30), (232, 30, 26), (268, 42, 26), (306, 32, 30)]
DECK2 = [(10, 12, 26), (56, 6, 30), (100, 14, 24), (140, 4, 30), (184, 12, 26), (226, 6, 28), (270, 14, 26), (314, 8, 26)]
MOON = (250, 38, 20)
SUN = (238, 82, 22)


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
    L = np.interp(yy, D['ys'], D['ls'])
    for cx, cy, rx, ry, amp in D['wisps']:
        ryv = np.where(yy > cy, ry * 0.5, ry)                       # flat bottom, round top
        L = L + amp * D['wk'] * np.clip(1 - ((xx - cx) / rx) ** 2 - ((yy - cy) / ryv) ** 2, 0, 1) ** 0.6
    L = np.minimum(L, D.get('cap', n - 1))
    disc = None
    if mood in ('moon', 'dusk'):
        cx, cy, r = MOON if mood == 'moon' else SUN
        rr = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        L = L + D['halo'][0] * np.clip(1 - (rr - r) / D['halo'][1], 0, 1) ** 1.5
        disc = rr <= r + 0.3
    L = np.clip(L, 0, n - 1)
    i0 = np.minimum(np.floor(L).astype(int), n - 2)
    ramp = [rid('S.s%d' % i) for i in range(n)]
    sub = Cv(SKYH, W)
    for i in range(n - 1):
        clus(sub, i0 == i, band(L - i), ramp[i], ramp[i + 1], i)
    if mood == 'storm':
        e1, e2 = edge_y(DECK1, 26), edge_y(DECK2, 6)
        d1, d2 = e1[None, :] - yy, e2[None, :] - yy
        Lk = np.where(d2 > 0, np.clip(2.3 - d2 / 9, 0, 3), np.clip(3.0 - d1 / 10, 0, 3))
        Lk = np.clip(Lk + 0.35 * np.sin(xx / 9.0 + yy / 5.0), 0, 3)
        deck = d1 > 0
        k0 = np.minimum(np.floor(Lk).astype(int), 2)
        kr = [S.k0, S.k1, S.k2, S.k3]
        for i in range(3):
            clus(sub, deck & (k0 == i), band(Lk - i, 0.2, 0.6), kr[i], kr[i + 1], 5 + i)
        sub.setm(deck & (np.abs(d1) < 1), S.k3)
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
    if mood == 'dusk':                                              # flat banded sun with sunset slits, no dither
        cx, cy, r = SUN
        t = (yy - (cy - r)) / (2.0 * r)
        sub.setm(disc, S.u1)
        sub.setm(disc & (t > 0.36 + 0.03 * np.sin(xx / 3.0)), S.u2)
        sub.setm(disc & (t > 0.66 + 0.03 * np.sin(xx / 4.0 + 1)), S.u3)
        for sy, sh in ((cy + 3, 1), (cy + 8, 1), (cy + 12, 2), (cy + 17, 2), (cy + 21, 3)):
            sub.setm(disc & (yy >= sy) & (yy < sy + sh), ramp[n - 2])
    if mood != 'storm':
        rng = random.Random(5)
        lim = D['starlim']
        k = 0
        while k < (80 if mood == 'moon' else 26):
            x, y = rng.randrange(W), rng.randrange(SKYH)
            if L[y, x] < lim and not disc[y, x]:
                sub.px(x, y, S.t2 if rng.random() < 0.25 else S.t1)
                k += 1
        for x, y, ph in BIGSTARS:
            if L[y, x] < lim:
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
        sky=[(6, 10, 18), (24, 48, 62), (66, 100, 108), (124, 160, 156)],
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
        stars=[(150, 90, 150), (220, 170, 200), (255, 255, 255)], sun=[(255, 244, 190), (255, 206, 120), (246, 140, 84)],
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
MOODS['storm'].update(skyl=[14, 44, 74, 104, 134], deck=MOODS['storm']['deck'] + [(124, 150, 150)], deckl=[26, 56, 86, 116],
                      val=dict(F=[28, 42, 72, 96], A=[14, 32, 62, 88], B=[8, 26.5, 55.5, 82], N=[4, 26.5, 45.5, 72]))
MOODS['dusk'].update(rimcap='N', skyl=[27.2, 57, 87, 117, 147, 177], Fhzl=138, sunl=[214, 180, 148], cloudl=[None, None, 142, None],
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
    assert worst <= (60 if mood == 'storm' else 66), (mood, worst)
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
    """v1 still (left) and v2 still (right) at 2x, labelled."""
    sheet = Image.new('RGB', (W * 4 + 24, H * 2 + 30), (24, 25, 31))
    dr = ImageDraw.Draw(sheet)
    p1 = os.path.join(V1DIR, 'scene_%s_1x.png' % mood)
    if os.path.exists(p1):
        sheet.paste(Image.fromarray(up(np.array(Image.open(p1).convert('RGB')), 2), 'RGB'), (8, 22))
    sheet.paste(Image.fromarray(up(still, 2), 'RGB'), (W * 2 + 16, 22))
    dr.text((8, 6), 'v1  %s  (2x)' % mood, fill=(230, 230, 236))
    dr.text((W * 2 + 16, 6), 'v2  %s  (2x)' % mood, fill=(230, 230, 236))
    sheet.save(path)


def write_html(moods):
    h = ['<!doctype html><html><head><meta charset="utf-8"><title>Backgrounds v2</title><style>',
         'body{background:#15161b;color:#d8d9df;font-family:Helvetica,Arial,sans-serif;margin:24px}',
         'img{image-rendering:pixelated;max-width:none;display:block;margin:8px 0 20px 0}',
         'h2{margin-top:40px;border-top:1px solid #3a3c46;padding-top:16px}p{max-width:960px;line-height:1.4}</style></head><body>',
         '<h1>Bubblegum Brawl backgrounds, draft round 2 (fix pass)</h1>',
         '<p>View at 100 percent browser zoom. Drafts only. Islands and fliers are placeholders; the hazard strips are the accepted dither drafts.</p>',
         '<h2>v1 against v2</h2>']
    for m in moods:
        h.append('<p>%s: v1 left, v2 right, 2x</p><img src="compare_%s_2x.png" width="%d" height="%d" alt="compare %s">' % (MOODS[m]['title'], m, W * 4 + 24, H * 2 + 30, m))
    for m in moods:
        M = MOODS[m]
        h += ['<h2>%s</h2>' % M['title'],
              '<p>Animation at 3x: sway, drift, tile loops and cast light. The drift is faster than in the game so that the loop closes.</p>',
              '<img src="anim_%s_3x.gif" width="960" height="672" alt="animation %s">' % (m, m),
              '<p>Still at 3x</p><img src="scene_%s_3x.png" width="960" height="672" alt="scene %s 3x">' % (m, m),
              '<p>Still at true size</p><img src="scene_%s_1x.png" width="320" height="224" alt="scene %s 1x">' % (m, m),
              '<p>Planes, each alone, at 2x</p><img src="planes_%s_2x.png" alt="planes %s">' % (m, m)]
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


if __name__ == '__main__':
    main()
