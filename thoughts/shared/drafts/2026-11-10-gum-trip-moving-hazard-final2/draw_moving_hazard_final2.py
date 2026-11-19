#!/usr/bin/env python3
# Gumbirds, Gum Trip: hand clean-up pass on the FINAL draft sheets of the three moving hazards (draft art, nothing in
# the build reads this). Same frame sizes, counts, timing and hit boxes as ../2026-11-10-gum-trip-moving-hazard-final/.
#
#   A  Skip-rope squall   48 x 48  24 frames x 4 ticks  dark storm cloud, lit rim, charge glow, faint charge trail
#   B  Flue spinner       32 x 48  16 frames x 4 ticks  steel turbine globe, curved blades, readable chain
#   C  Cinder             32 x 32  24 frames x 3 ticks  black coal, glowing cracks, outlined spark trails
#
# What "hand pass" means here: no lighting is computed per pixel any more. Every shade is a cluster with a drawn
# shape (offset discs on the cloud, whole blades on the globe, whole facets on the coal) placed at half-pixel steps,
# followed by pixel rules a pixel artist applies by eye (no orphan pixels, no 1 px spurs or notches on the outline,
# light rim only on edges that face the light) and a table of per-frame corrections (FIXES) at the end.
#
# Self-contained. Reads only the old sheets (read-only) to build before_after_4x.png.
# Run: /opt/homebrew/bin/python3.14 -I draw_moving_hazard_final2.py [--preview]
import os
import sys
sys.dont_write_bytecode = True
import json
import math
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OLD = os.path.join(HERE, '..', '2026-11-10-gum-trip-moving-hazard-final')
OLD_REL = '../2026-11-10-gum-trip-moving-hazard-final'
TAU = 2 * math.pi
GIF_BG = (88, 104, 128)
MOODS = [('Dusk', (148, 55, 92)), ('Moon', (76, 60, 142)), ('Storm', (40, 86, 99))]
LDIR = (-0.66, -0.75)                                     # light comes from the upper left (screen x, y)


def q5(c):
    return tuple(((v >> 3) << 3) | (v >> 5) for v in c)


def grid(w, h):
    y, x = np.mgrid[0:h, 0:w]
    return x.astype(float), y.astype(float)


def line_pts(x0, y0, x1, y1):
    x0, y0, x1, y1 = int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
    n = max(abs(x1 - x0), abs(y1 - y0), 1)
    return [(int(round(x0 + (x1 - x0) * i / n)), int(round(y0 + (y1 - y0) * i / n))) for i in range(n + 1)]


def put(idx, x, y, c, only=None):
    h, w = idx.shape
    x, y = int(x), int(y)
    if 0 <= x < w and 0 <= y < h and (only is None or only[y, x]):
        idx[y, x] = c


def shift(m, dx, dy, fill=False):
    """m moved by (dx, dy): result[y, x] = m[y - dy, x - dx]."""
    h, w = m.shape
    out = np.full_like(m, fill)
    ys, yd = (slice(0, h - dy), slice(dy, h)) if dy >= 0 else (slice(-dy, h), slice(0, h + dy))
    xs, xd = (slice(0, w - dx), slice(dx, w)) if dx >= 0 else (slice(-dx, w), slice(0, w + dx))
    out[yd, xd] = m[ys, xs]
    return out


N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
N8 = N4 + ((1, 1), (-1, -1), (1, -1), (-1, 1))


def dilate(m):
    out = m.copy()
    for (dx, dy) in N4:
        out |= shift(m, dx, dy)
    return out


def outline(idx, col):
    op = idx > 0
    idx[dilate(op) & ~op] = col
    return idx


# ---- pixel rules of the hand pass -----------------------------------------------------------------------------
def clean_mask(m, passes=2):
    """Silhouette rule: no 1 px spurs (a pixel with fewer than 2 edge neighbours goes), no 1 px notches (a hole with
    3 or 4 edge neighbours is filled)."""
    for _ in range(passes):
        n = sum(shift(m, dx, dy).astype(int) for (dx, dy) in N4)
        m = (m & (n >= 2)) | (~m & (n >= 3))
    return m


def despeckle(idx, keep=(), passes=2):
    """Cluster rule: a pixel whose colour touches no pixel of the same colour (8 neighbours) is a stray. It takes
    the most common colour of its edge neighbours."""
    h, w = idx.shape
    for _ in range(passes):
        same = np.zeros((h, w), bool)
        for (dx, dy) in N8:
            same |= shift(idx, dx, dy, -1) == idx
        orphan = (idx > 0) & ~same
        for c in keep:
            orphan &= idx != c
        for (y, x) in np.argwhere(orphan):
            nb = [idx[y + dy, x + dx] for (dx, dy) in N4 if 0 <= y + dy < h and 0 <= x + dx < w and idx[y + dy, x + dx] > 0]
            if nb:
                idx[y, x] = max(set(nb), key=nb.count)
    return idx


def facing(mask):
    """How much the silhouette edge at each pixel faces the light, -1..1, from the outside pixels in a 5 x 5 window."""
    ox = np.zeros(mask.shape)
    oy = np.zeros(mask.shape)
    out = ~mask
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            if dx or dy:
                s = shift(out, -dx, -dy, True)             # s[y, x] = out[y + dy, x + dx]
                ox += s * dx
                oy += s * dy
    n = np.sqrt(ox * ox + oy * oy)
    n[n == 0] = 1
    return (ox * LDIR[0] + oy * LDIR[1]) / n


# Per-frame hand corrections, applied last: FIXES[kind][frame] = [(x, y, colour index), ...]; frame '*' = every frame.
FIXES = {'a': {}, 'b': {}, 'c': {}}


def apply_fixes(kind, f, idx):
    for key in ('*', f):
        for (x, y, c) in FIXES[kind].get(key, ()):
            idx[y, x] = c
    return idx


# =============================================================== A  Skip-rope squall (palette "storm")
PAL_STORM = [q5(c) for c in [
    (8, 8, 24),        # 1 outline
    (24, 24, 57),      # 2 heavy underside, cold indigo
    (49, 49, 90),      # 3 shadow
    (82, 90, 123),     # 4 body slate
    (132, 132, 148),   # 5 light, a little warmer
    (214, 198, 165),   # 6 lit rim, warm
    (255, 239, 198),   # 7 rim highlight, cream
    (33, 57, 165),     # 8 charge deep blue
    (41, 115, 222),    # 9 charge blue
    (99, 206, 247),    # 10 cyan
    (198, 247, 255),   # 11 pale cyan
    (255, 255, 255),   # 12 white core
    (255, 239, 115),   # 13 spark yellow
    (255, 148, 41),    # 14 spark orange
    (107, 140, 206),   # 15 faint trail, periwinkle
]]
NA, TA, FS = 24, 4, 17            # frames, ticks per frame, strike frame
#          x   y   r    phase dir zo
PUFFS = [(24, 21, 10.0, 0.0, 1, 3.0), (14, 24, 7.5, 1.1, -1, 1.0), (34, 24, 7.5, 2.3, 1, 1.0),
         (18, 15, 7.0, 3.0, -1, 0.0), (30, 14, 6.5, 4.1, 1, 0.0), (8, 26, 4.5, 5.0, -1, 0.0),
         (40, 26, 4.5, 0.7, 1, 0.0), (19, 28, 6.0, 1.9, -1, 2.0), (29, 28, 6.0, 3.6, 1, 2.0),
         (24, 10, 5.0, 5.6, 1, -1.0)]
PIN_L, PIN_R, PIN_Y = 5, 43, 27
HIT_A = (7, 8, 42, 32)


def charge(f):
    if 4 <= f < FS:
        return ((f - 4) / (FS - 4)) ** 1.6 * 0.9
    return {FS: 1.0, FS + 1: 0.55, FS + 2: 0.3, FS + 3: 0.12}.get(f, 0.0)


def h5(v):
    return round(v * 2) / 2


def squall_frame(f):
    W = H = 48
    w = TAU * f / NA
    X, Y = grid(W, H)
    balls = []
    for (bx, by, br, ph, dr, zo) in PUFFS:
        cx = bx + 1.1 * math.cos(w + ph) * dr
        cy = by + 0.8 * math.sin(w + ph)
        r = br + 0.6 * math.sin(w + ph * 1.7)
        balls.append((zo, cx, cy, r, 1.0))
        for k in range(2):                                  # two lumps overturn round every billow, once per loop
            psi = ph + dr * w + k * math.pi
            ox, oy = math.cos(psi), math.sin(psi)
            balls.append((zo + 0.3, cx + 0.62 * r * ox, cy + 0.62 * r * oy, 0.5 * r, ox * LDIR[0] + oy * LDIR[1]))
    balls.sort(key=lambda b: b[0])
    lv = np.zeros((H, W), int)
    for (_, cx, cy, r, lit) in balls:                       # painter order, back to front; every shade is a disc
        cx, cy, r = h5(cx), h5(cy), h5(r)
        d2 = (X - cx) ** 2 + (Y - cy) ** 2
        ins = d2 < r * r
        crease = (~ins) & (d2 < (r + 1.3) ** 2) & (lv > 3)  # the billow behind darkens where this one sits on it
        lv[crease] -= 1
        lv[ins] = 3
        lv[ins & ((X - (cx - 0.22 * r)) ** 2 + (Y - (cy - 0.26 * r)) ** 2 < (0.80 * r) ** 2)] = 4
        if lit > 0.2 and r >= 3:
            lv[ins & ((X - (cx - 0.40 * r)) ** 2 + (Y - (cy - 0.44 * r)) ** 2 < (0.48 * r) ** 2)] = 5
    base = 31.0 + 2.0 * np.abs(np.sin(X * 0.33 + 0.4))      # scalloped base, fixed in the frame
    mask = clean_mask((lv > 0) & (Y <= base))
    lv[~mask] = 0
    lv[mask & (lv == 0)] = 3
    ub = 23 + np.round(1.5 * np.sin(X * 0.45 + 1.0))        # edge of the heavy underside, fixed in the frame
    m1 = mask & (Y > ub)
    lv[m1] = np.maximum(lv[m1] - 1, 2)
    m2 = mask & (Y > ub + 4)
    lv[m2] = np.maximum(lv[m2] - 1, 2)
    idx = lv.copy()
    # lit rim: only silhouette pixels whose edge faces the light, cream on the pixels that face it squarely
    edge = mask & ~(shift(mask, 1, 0) & shift(mask, -1, 0) & shift(mask, 0, 1) & shift(mask, 0, -1))
    fc = facing(mask)
    rim = edge & (fc > 0.25) & (Y <= ub + 2)
    idx[rim] = 6
    idx[rim & (fc > 0.8) & (Y < ub - 2)] = 7
    under = shift(idx == 7, 0, 1) & mask & (idx < 6)
    idx[under] = 6
    # charge glow in the belly: seen through the dark parts only, grows with the charge, never fully out
    c = charge(f)
    cv = max(c, 0.10)
    rx, ry = 5 + 11 * cv, 2.5 + 6.5 * cv
    dn = np.sqrt(((X - 24) / rx) ** 2 + ((Y - 27) / ry) ** 2)
    chk = (X + Y) % 2 == 0
    can = mask & ((idx == 2) | (idx == 3) | ((idx == 4) & (Y > ub) & (cv > 0.6)))
    idx[can & ((dn < 1.0) | ((dn < 1.18) & chk))] = 8
    if cv > 0.25:
        idx[can & ((dn < 0.6) | ((dn < 0.72) & chk))] = 9
    if cv > 0.6:
        idx[can & (dn < 0.3)] = 10
    if c > 0.5:                                             # veins of charge: two drawn shapes that swap, a crackle
        for i, vx in enumerate((24, 17, 31) if c > 0.75 else (24,)):
            flip = 1 if (f + i) % 2 == 0 else -1
            for (ox, oy) in ((0, 0), (flip, 1), (0, 2), (flip, 3), (2 * flip, 4)):
                x, y = vx + ox, 24 + oy
                if mask[y, x] and idx[y, x] in (8, 9):
                    idx[y, x] = 10
    if f == FS:                                             # the strike lights the base rim only
        low = mask & ~shift(mask, 0, -1) & (Y > 26)
        idx[shift(low, 0, -1) & mask] = 10
        idx[low] = 11
    despeckle(idx)
    outline(idx, 1)
    solid = idx > 0
    empty = ~solid
    # the trail: hangs below the base between the two flanks, never crosses the cloud face. Its sag is deepest on
    # the strike and it is hidden behind the base half a loop later.
    M = 25
    sv = np.linspace(0, 1, M)
    th = TAU * (f - FS) / NA
    sag = 9.0 + 4.0 * math.cos(th)
    k = np.arange(M)
    jag = np.sin(math.pi * sv) * 1.25
    ax = PIN_L + (PIN_R - PIN_L) * sv + jag * np.sin(k * 2.4 + 3 * w + k * k * 0.7)
    ay = PIN_Y + sag * np.sin(math.pi * sv) ** 0.75 + jag * np.sin(k * 1.7 - 5 * w + k * k * 0.3)
    pts = []
    for i in range(M - 1):
        for p in line_pts(ax[i], ay[i], ax[i + 1], ay[i + 1])[:-1]:
            if not pts or pts[-1] != p:
                pts.append(p)
    if f == FS:
        for (x, y) in pts:
            for (ox, oy) in N4:
                put(idx, x + ox, y + oy, 10, only=empty)
        for (x, y) in pts:
            put(idx, x, y, 12, only=empty)
        for j, d in ((len(pts) // 3, -1), (2 * len(pts) // 3, 1)):          # two short forks
            x, y = pts[j]
            for s in range(1, 4):
                put(idx, x + d * (s // 2), y + s, 11, only=empty)
    else:
        if f == FS + 1:
            run, per, body, head = 9, 9, 10, 10
        elif f == FS + 2:
            run, per, body, head = 5, 9, 9, 9
        elif c > 0.75:
            run, per, body, head = 6, 9, 9, 10
        elif c > 0.45:
            run, per, body, head = 4, 9, 9, 10
        elif c > 0.2:
            run, per, body, head = 3, 9, 15, 9
        else:
            run, per, body, head = 2, 9, 15, 15                              # rest: faint 2 px dashes that travel
        for j, (x, y) in enumerate(pts):
            ph = (j + 3 * f) % per
            if ph < run:
                put(idx, x, y, head if ph == 0 else body, only=empty)
    for px in (PIN_L, PIN_R):                               # sparks where the trail leaves the flanks
        if f == FS:
            for (ox, oy, cc) in ((0, 0, 12), (1, 0, 13), (-1, 0, 13), (0, 1, 13), (0, -1, 13), (2, 0, 14), (-2, 0, 14),
                                 (0, 2, 14), (0, -2, 14), (1, 1, 14), (-1, -1, 14), (1, -1, 14), (-1, 1, 14)):
                put(idx, px + ox, PIN_Y + oy, cc)
        elif c > 0.3:
            put(idx, px, PIN_Y, 13)
            arms = N4 if f % 2 == 0 else ((1, 1), (-1, -1), (1, -1), (-1, 1))
            for (ox, oy) in arms:
                put(idx, px + ox, PIN_Y + oy, 14)
    return apply_fixes('a', f, idx), mask


# =============================================================== palette "hot_metal" (B and C)
PAL_HOT = [q5(c) for c in [
    (16, 16, 33),      # 1 outline
    (41, 41, 74),      # 2 cool dark (steel deep shadow, coal facet towards the sky)
    (74, 82, 115),     # 3 steel shadow, coal sheen
    (115, 123, 148),   # 4 steel mid
    (165, 173, 189),   # 5 steel light
    (222, 222, 214),   # 6 warm light
    (255, 255, 239),   # 7 specular
    (90, 33, 33),      # 8 deep red brown
    (165, 49, 33),     # 9 rust red
    (231, 82, 24),     # 10 hot red orange
    (255, 140, 24),    # 11 orange
    (255, 214, 57),    # 12 yellow
    (255, 247, 173),   # 13 pale yellow
    (33, 24, 41),      # 14 coal black
    (57, 33, 57),      # 15 warm dark plum
]]

# =============================================================== B  Flue spinner
NB, TB = 16, 4
NV, KP, BOW = 12, 5, 0.85            # blades, blade pitches advanced per loop (5 and 16 share no factor), blade bow
BCX, BCY, BR = 16, 13, 9.5
HIT_B = (8, 5, 24, 21)
STEEL = np.array([2, 3, 4, 5, 6, 7])
COLLAR_TEETH = {9: 2, 10: 1, 11: 2, 12: 2, 13: 1, 14: 0, 15: 1, 16: 2, 17: 2, 18: 1, 19: 2, 20: 0, 21: 1, 22: 2, 23: 1}


def vent_frame(f):
    W, H = 32, 48
    w = TAU * f / NB
    X, Y = grid(W, H)
    idx = np.zeros((H, W), int)
    dy = Y - BCY
    dx = X - BCX
    pitch = TAU / NV
    rot = pitch * KP * f / NB
    rho2 = dx * dx + dy * dy
    inside = rho2 <= BR * BR
    sl = np.clip(-dy / BR, -1, 1)
    lat = np.arcsin(sl)
    xn = np.clip(dx / (BR * np.maximum(np.sqrt(1 - sl * sl), 1e-3)), -1, 1)
    phi = np.arcsin(xn)                                     # longitude on the front of the globe: foreshortening
    bow = BOW * lat * lat                                   # each blade is bowed like a bracket
    t = (phi - rot - bow) / pitch
    kb = np.floor(t)
    u = t - kb
    xs = np.sin((kb + 0.36) * pitch + rot + bow)            # screen position of the middle of the blade, -1..1
    zone = np.digitize(xs, [-0.6, 0.0, 0.55])                               # one base tone per blade, by its place
    base = np.array([3, 3, 2, 1])[zone]
    # every blade is four drawn stripes: lit leading edge, face, shaded trailing edge, then the black slot
    tone = base + np.where(u < 0.22, 2, np.where(u < 0.5, 1, 0))
    tone = tone - np.where(dy > 3, 1, 0)                                    # lower half hangs in its own shade
    blade = u < 0.72
    col = STEEL[np.clip(tone, 0, 4)]
    col = np.where(blade, col, 14)                                          # slots: coal black
    col = np.where(~blade & (dy > 4) & (u > 0.86), 8, col)                  # a little warmth low in the slots
    spec = ((dx + 3.5) / 3.2) ** 2 + ((dy + 2.5) / 3.4) ** 2 < 1            # hard highlight, fixed to the light:
    col = np.where((u < 0.22) & spec, 7, col)                               # only the leading edges catch it
    col = np.where(xn < -0.9, 3, col)                                       # clean rim columns, no blade slivers
    col = np.where(xn > 0.9, 3, col)
    col = np.where((xn > 0.74) & (xn <= 0.9), 2, col)
    # cap and base ring: plain turned steel in flat vertical bands
    band = np.where(dx < -5, 4, np.where(dx < -3, 6, np.where(dx < -1, 5, np.where(dx < 3, 4, np.where(dx < 6, 3, 2)))))
    cap = dy <= -7
    col = np.where(cap, band, col)
    col = np.where(cap & (dx >= -4) & (dx <= -3) & (dy == -8), 7, col)
    col = np.where(dy == -6, 2, col)                                        # shadow line under the cap
    ring = dy >= 7
    col = np.where(ring, np.maximum(band - 1, 2), col)
    col = np.where(dy == 7, 2, col)
    col = np.where(dy == 8, np.where(band >= 5, 6, np.where(dx < 3, 5, 3)), col)   # lit lip of the ring
    idx[inside] = col[inside]
    for (x, y, cc) in ((16, 2, 6), (16, 3, 5), (15, 3, 6), (17, 3, 3)):     # finial
        idx[y, x] = cc
    # neck, steel collar with rivets, hot torn edge (the only heat: an accent)
    for x in range(12, 21):
        idx[23, x] = 4 if x < 14 else (2 if x > 17 else 3)
    for y in range(24, 30):
        for x in range(9, 24):
            cc = 3 if x == 9 else (5 if x < 12 else (6 if x == 12 else (4 if x < 18 else (3 if x < 21 else 2))))
            if y == 24:
                cc = 6 if x < 18 else 4                                     # top lip
            if y == 25:
                cc = 2 if x > 11 else 3                                     # shadow under the lip
            if y == 29:
                cc = 8 if x in (9, 23) else (9 if x < 12 or x > 20 else (11 if 14 <= x <= 18 else 10))
            idx[y, x] = cc
    for rx_ in (11, 16, 21):                                                # rivets: light pixel, shadow pixel below
        idx[27, rx_] = 6 if rx_ < 20 else 4
        idx[28, rx_] = 2
    idx[29, 16] = 12
    for x, hgt in COLLAR_TEETH.items():
        if hgt >= 1:
            idx[30, x] = 9 if hgt == 2 else 8
        if hgt >= 2 and x % 3 == 0:
            idx[31, x] = 8
    # chain: four links 3.5 px apart, each a pendulum that lags the link above it; swing grows down the chain
    px, py = 16.0, 30.5
    pts = [(px, py)]
    ang = []
    for i in range(4):
        th = -(0.22 + 0.10 * i) * math.sin(w - 0.6 * (i + 1)) - 0.05 * math.sin(2 * w - 0.9 * i)
        ang.append(th)
        px, py = px + 3.5 * math.sin(th), py + 3.5 * math.cos(th)
        pts.append((px, py))
    for i in (1, 3, 0, 2):                                                  # bars first, rings over them
        mx = int(round((pts[i][0] + pts[i + 1][0]) / 2))
        my = int(round((pts[i][1] + pts[i + 1][1]) / 2))
        if i % 2 == 0:                                                      # link seen face on: a ring with a hole
            for (ox, oy, cc) in ((0, -2, 6), (-1, -1, 6), (-1, 0, 5), (-1, 1, 4), (1, -1, 4), (1, 0, 3), (1, 1, 3), (0, 2, 3)):
                put(idx, mx + ox, my + oy, cc)
            for oy in (-1, 0, 1):
                put(idx, mx, my + oy, 1)
        else:                                                               # link seen edge on: a bar
            for (oy, cc) in ((-2, 5), (-1, 6), (0, 5), (1, 4), (2, 3)):
                put(idx, mx, my + oy, cc)
    hx, hy = int(round(pts[-1][0])), int(round(pts[-1][1]))
    d = 1 if ang[-1] >= 0 else -1
    for (ox, oy, cc) in ((0, 0, 5), (0, 1, 4), (-d, 2, 3), (-2 * d, 1, 9)):  # hook with a rust tip
        put(idx, hx + ox, hy + oy, cc)
    outline(idx, 1)
    return apply_fixes('b', f, idx)


# =============================================================== C  Cinder
NC, TC = 24, 3
CCX, CCY, CR = 13, 18, 9.5
HIT_C = (5, 11, 20, 25)
HOTC = np.array([9, 10, 11, 12, 13])
_rng = np.random.default_rng(11)
NPL = 16
_i = np.arange(NPL) + 0.5
_ph = np.arccos(1 - 2 * _i / NPL)
_th = math.pi * (1 + 5 ** 0.5) * _i
PN = np.stack([np.cos(_th) * np.sin(_ph), np.sin(_th) * np.sin(_ph), np.cos(_ph)], 1) + _rng.normal(0, 0.16, (NPL, 3))
PN /= np.linalg.norm(PN, axis=1, keepdims=True)
PD = CR * (0.72 + 0.28 * _rng.random(NPL))
_cr = _rng.random((NPL, NPL))
CRACK = np.triu(_cr < 0.52, 1)
CRACK = CRACK | CRACK.T
_cp = np.triu(_rng.random((NPL, NPL)) * TAU, 1)
CPH = _cp + _cp.T
HOTFACE = 3
AXIS = np.array([0.5, 0.75, 0.43])
AXIS /= np.linalg.norm(AXIS)
NSPARK = 20
SPARK = [dict(b=(k * NC / NSPARK + _rng.random() * 1.5) % NC, life=int(_rng.integers(6, 11)),
              ex=CCX + _rng.uniform(6, 9), ey=CCY + _rng.uniform(-8, 3), vx=_rng.uniform(0.6, 1.1),
              vy=_rng.uniform(-0.9, -0.25), ph=_rng.uniform(0, TAU)) for k in range(NSPARK)]


def rot_matrix(axis, a):
    x, y, z = axis
    c, s = math.cos(a), math.sin(a)
    C = 1 - c
    return np.array([[c + x * x * C, x * y * C - z * s, x * z * C + y * s],
                     [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
                     [z * x * C - y * s, z * y * C + x * s, c + z * z * C]])


def coal_frame(f):
    W = H = 32
    w = TAU * f / NC
    X, Y = grid(W, H)
    x, y = X - CCX, Y - CCY
    Rm = rot_matrix(AXIS, w)                               # one full tumble per loop
    n = PN @ Rm.T
    zf = np.full((H, W), 1e9)
    zb = np.full((H, W), -1e9)
    fid = np.zeros((H, W), int)
    ok = np.ones((H, W), bool)
    for i in range(NPL):
        nx, ny, nz = n[i]
        rest = PD[i] - nx * x - ny * y
        if nz > 1e-3:
            zi = rest / nz
            t = zi < zf
            fid = np.where(t, i, fid)
            zf = np.where(t, zi, zf)
        elif nz < -1e-3:
            zb = np.maximum(zb, rest / nz)
        else:
            ok &= rest >= 0
    mask = clean_mask(ok & (zf >= zb) & (zf < 1e8))
    light3 = np.array([-0.55, -0.62, 0.56])
    light3 /= np.linalg.norm(light3)
    lvl = np.digitize((n @ light3)[fid], [-0.05, 0.3, 0.58, 0.82])            # 0..4, one flat tone per facet
    idx = np.where(mask, np.array([14, 14, 2, 2, 2])[lvl], 0)                # black coal: no grey facet fill at all
    hotpulse = 0.5 + 0.5 * math.sin(2 * w + 1.0)
    hf = mask & (fid == HOTFACE)
    idx[hf] = 8                                                             # one ember face
    if hotpulse > 0.6:
        core = hf & shift(hf, 1, 0) & shift(hf, -1, 0) & shift(hf, 0, 1) & shift(hf, 0, -1)
        idx[core] = 9
    crack = np.zeros((H, W), bool)
    cph = np.zeros((H, W))
    for (sy, sx) in ((0, 1), (1, 0)):
        a_ = fid[:H - sy, :W - sx]
        b_ = fid[sy:, sx:]
        both = mask[:H - sy, :W - sx] & mask[sy:, sx:] & (a_ != b_)
        isc = both & CRACK[a_, b_]
        view = crack[:H - sy, :W - sx]
        view |= isc
        pv = cph[:H - sy, :W - sx]
        pv[isc] = CPH[a_, b_][isc]
        gl = both & ~isc                                                    # plain facet edge: a thin cold sheen
        lv = lvl[:H - sy, :W - sx]
        iv = idx[:H - sy, :W - sx]
        iv[gl & (lv >= 2) & (iv != 8) & (iv != 9)] = 3
        iv[gl & (lv == 4) & (iv == 3) & (sx == 1)] = 4
    p = 0.5 + 0.5 * np.sin(2 * w + cph)                                     # every crack breathes twice per loop
    near = dilate(crack) & mask & ~crack
    idx[near & np.isin(idx, (14, 2, 3, 4))] = 15                            # warm bounce beside every crack
    idx[dilate(crack & (p > 0.5)) & near] = 8
    idx[crack] = HOTC[np.minimum(4, (p * 3.2 + 1.2).astype(int))][crack]    # never below orange red
    despeckle(idx)
    outline(idx, 1)
    solid = idx > 0
    hotc = dilate(dilate(crack & (p > 0.45)))
    idx[(idx == 1) & hotc] = 8                                              # outline glows beside a hot crack
    lone = (idx == 8) & ~mask
    lone &= ~(dilate(lone & shift(lone, 1, 0)) | dilate(lone & shift(lone, 0, 1)) | shift(lone, 1, 1) | shift(lone, -1, -1)
              | shift(lone, 1, -1) | shift(lone, -1, 1))
    idx[lone] = 1                                                           # a single glowing outline pixel is a stray
    free = ~solid
    for sp in SPARK:                                                        # sparks: head, body, tail, dark keyline
        age = (f - sp['b']) % NC
        if age >= sp['life']:
            continue
        sx = int(round(sp['ex'] + sp['vx'] * age + 0.5 * math.sin(1.1 * age + sp['ph'])))
        sy = int(round(sp['ey'] + sp['vy'] * age * (1 - 0.03 * age)))
        dxy = (-1, 1) if sp['vy'] < -0.5 else (-1, 0)
        t = age / sp['life']
        if t < 0.35:
            cols = (13, 12, 10)
        elif t < 0.7:
            cols = (12, 11, 9)
        else:
            cols = (11, 9)
        cells = [(sx + dxy[0] * i, sy + dxy[1] * i) for i in range(len(cols))]
        if not all(0 <= cx_ < W and 0 <= cy_ < H and free[cy_, cx_] for (cx_, cy_) in cells):
            continue
        tx, ty = sx + dxy[0] * len(cols), sy + dxy[1] * len(cols)
        for (kx, ky) in ((tx, ty), (cells[0][0], cells[0][1] + 1), (cells[1][0], cells[1][1] + 1)):
            if 0 <= kx < W and 0 <= ky < H and idx[ky, kx] == 0:
                idx[ky, kx] = 1                                             # dark keyline behind and under the trail
        for (cx_, cy_), cc in zip(cells, cols):
            idx[cy_, cx_] = cc
    return apply_fixes('c', f, idx), mask


# =============================================================== output
def to_rgba(idx, pal):
    lut = np.zeros((16, 4), np.uint8)
    for i, c in enumerate(pal):
        lut[i + 1] = (*c, 255)
    return lut[idx]


def sheet(frames, pal):
    return Image.fromarray(np.concatenate([to_rgba(fr, pal) for fr in frames], 1), 'RGBA')


def on_bg(idx, pal, bg, scale):
    lut = np.zeros((16, 3), np.uint8)
    lut[0] = bg
    for i, c in enumerate(pal):
        lut[i + 1] = c
    im = Image.fromarray(lut[idx], 'RGB')
    return im.resize((im.width * scale, im.height * scale), Image.NEAREST)


def tiles(frames):
    raw, uniq, flip = 0, set(), set()
    for fr in frames:
        h, w = fr.shape
        for ty in range(0, h, 16):
            for tx in range(0, w, 16):
                t = fr[ty:ty + 16, tx:tx + 16].astype(np.uint8)
                if not t.any():
                    continue
                raw += 1
                uniq.add(t.tobytes())
                flip.add(min(t.tobytes(), t[:, ::-1].tobytes(), t[::-1].tobytes(), t[::-1, ::-1].tobytes()))
    return raw, len(uniq), len(flip)


def seam(frames):
    n = len(frames)
    d = [int((frames[i] != frames[(i + 1) % n]).sum()) for i in range(n)]
    return d[-1], sum(d[:-1]) / (n - 1), max(d[:-1])


def bbox(m):
    ys, xs = np.nonzero(m)
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def strays(frames):
    """Opaque pixels whose colour touches no pixel of the same colour (8 neighbours), mean per frame."""
    tot = 0
    for idx in frames:
        same = np.zeros(idx.shape, bool)
        for (dx, dy) in N8:
            same |= shift(idx, dx, dy, -1) == idx
        tot += int(((idx > 0) & ~same).sum())
    return tot / len(frames)


def lum(pal):
    return np.array([0.0] + [0.299 * r + 0.587 * g + 0.114 * b for (r, g, b) in pal])


def old_frames(key, w, h, n):
    p = os.path.join(OLD, f'sheet_{key}_1x.png')
    if not os.path.exists(p):
        return None
    im = Image.open(p).convert('RGBA')
    return [im.crop((i * w, 0, i * w + w, h)) for i in range(n)]


def old_strays(key, w, h, n):
    fr = old_frames(key, w, h, n)
    if fr is None:
        return None
    out = []
    for im in fr:
        a = np.array(im).astype(np.int64)
        out.append(np.where(a[..., 3] > 0, 1 + a[..., 0] + (a[..., 1] << 8) + (a[..., 2] << 16), 0))
    return strays(out)


FIXTEXT = [
    ('1. Banding and the rendered look',
     'No shade is computed per pixel any more. Cloud: every billow is three drawn discs (shadow, body, light) set at '
     'half-pixel steps and painted back to front, with a crease where one billow sits on another. Globe: one flat '
     'tone per blade. Coal: one flat tone per facet. Rules after that: no orphan pixels, no 1 px spurs or notches on '
     'the silhouette, rim light only on edges that face the light. Shadows run to cold indigo, lights to warm cream.'),
    ('2. Storm cloud',
     'Darker body with a heavy indigo underside (lower third), a warm lit rim on the upper left silhouette, a dark '
     'outline, and a blue charge glow in the belly that never goes fully out and grows to the strike. The rope is now '
     'a trail of faint 2 px dashes that travel along it, hangs only below the base (it no longer crosses the cloud '
     'face), thickens and turns blue as the charge builds and is a solid white bolt on the strike frame only.'),
    ('3. Vent',
     'Twelve bowed vertical blades on a sphere with true foreshortening (blades narrow toward both edges), steel '
     'greys only, a hard highlight that stays fixed to the light and only the leading edges of the blades catch, black slots. Heat is '
     'an accent: the torn bottom edge of the collar and a warm tint low in the slots. No dither. The blades advance '
     '5 pitches in 16 frames, so no globe frame repeats inside the loop. Chain: four links of 5 px (ring, bar, ring, '
     'bar) with a hole in each ring; each link lags the one above.'),
    ('4. Coal',
     'Facets are filled with coal black and cold dark only; grey is left for thin sheen lines on facet edges. More '
     'cracks, never dimmer than orange red, each with a warm plum or red border. The outline itself glows red beside '
     'a hot crack (replaces the dither halo). Sparks are 2 to 3 px trails (pale core, orange body, red tail) with a '
     'dark keyline behind and under them.'),
    ('5. Kept',
     'Frame sizes, frame counts, ticks per frame, hit boxes, two palettes of 15 colours, JSON format, one strike '
     'frame per loop.'),
]


def main():
    preview = '--preview' in sys.argv
    fa, ma = zip(*[squall_frame(f) for f in range(NA)])
    fb = [vent_frame(f) for f in range(NB)]
    fc, mc = zip(*[coal_frame(f) for f in range(NC)])
    kinds = [
        dict(key='a', name='Skip-rope squall', frames=list(fa), pal=PAL_STORM, palname='storm', ticks=TA, hit=HIT_A,
             body=np.all(np.stack(ma), 0),
             hitnote='the cloud body only (user decision); the trail below the base and the flank sparks do not hurt'),
        dict(key='b', name='Flue spinner', frames=fb, pal=PAL_HOT, palname='hot_metal', ticks=TB, hit=HIT_B,
             body=np.all(np.stack(fb) > 0, 0),
             hitnote='the globe, 1 px inside its steel; collar and chain do not hurt'),
        dict(key='c', name='Cinder', frames=list(fc), pal=PAL_HOT, palname='hot_metal', ticks=TC, hit=HIT_C,
             body=np.any(np.stack(mc), 0),
             hitnote='the coal, 2 px inside its widest tumble; sparks do not hurt'),
    ]
    out = ['Gum Trip moving hazards, hand clean-up pass. Measured by draw_moving_hazard_final2.py from the sheets it wrote.',
           'Tiles are 16 x 16. Raw = non-empty tiles over all frames; unique = distinct after removing exact duplicates;',
           'with flips = distinct when horizontal and vertical mirror copies also count as duplicates.',
           'Loop seam = pixels that differ between the last frame and frame 0, beside the same count for the other',
           'neighbouring frame pairs (mean and largest). A seam inside that range means no pop.',
           'Stray pixels = opaque pixels whose colour touches no pixel of the same colour, mean per frame.', '']
    total_u = total_f = 0
    summary = []
    for kd in kinds:
        fr, pal = kd['frames'], kd['pal']
        h, w = fr[0].shape
        n = len(fr)
        used = sorted(set(int(v) for f_ in fr for v in np.unique(f_)) - {0})
        assert max(used) <= 15 and len(pal) == 15 and len(set(pal)) == 15
        im = sheet(fr, pal)
        assert im.width % 16 == 0 and im.height % 16 == 0
        im.save(os.path.join(HERE, f"sheet_{kd['key']}_1x.png"), optimize=True)
        raw, uq, fl = tiles(fr)
        total_u += uq
        total_f += fl
        sm = seam(fr)
        ob = bbox(np.any(np.stack(fr) > 0, 0))
        x0, y0, x1, y1 = kd['hit']
        cover = 100.0 * kd['body'][y0:y1 + 1, x0:x1 + 1].mean()
        ms = round(kd['ticks'] * 1000 / 60 / 10) * 10
        gif = [on_bg(f_, pal, GIF_BG, 3) for f_ in fr]
        gif[0].save(os.path.join(HERE, f"anim_{kd['key']}_3x.gif"), save_all=True, append_images=gif[1:],
                    duration=ms, loop=0, optimize=True)
        js = {
            'source': 'thoughts/shared/drafts/2026-11-10-gum-trip-moving-hazard-final2/draw_moving_hazard_final2.py '
                      f"(draft; {kd['name']}, one looping clip, frames in one row, transparent background)",
            'animations': {kd['key']: [{'x': i * w, 'y': 0, 'w': w, 'h': h} for i in range(n)]},
            'palettes': {kd['palname']: [list(c) for c in pal]},
            'defines': {'ART_W': w, 'ART_H': h, 'FRAMES': n, 'TICK_HZ': 60, 'CLIP_COUNT': 1, 'CLIP_LOOP': 0,
                        'HIT_X0': x0, 'HIT_Y0': y0, 'HIT_X1': x1, 'HIT_Y1': y1,
                        'HIT_W': x1 - x0 + 1, 'HIT_H': y1 - y0 + 1, 'LOOP_TICKS': n * kd['ticks']},
            'tables': {'clip_first': [0], 'clip_count': [n], 'clip_loop': [1], 'frame_ticks': [kd['ticks']] * n},
            'hitbox': {'x': x0, 'y': y0, 'w': x1 - x0 + 1, 'h': y1 - y0 + 1},
        }
        with open(os.path.join(HERE, f"sheet_{kd['key']}.json"), 'w') as fh:
            json.dump(js, fh, indent=1)
        st_new, st_old = strays(fr), old_strays(kd['key'], w, h, n)
        distinct = len(set(f_.tobytes() for f_ in fr))
        kd.update(w=w, h=h, n=n, uq=uq)
        out += [kd['name'],
                f"Frame size {w} x {h} px, {n} frames in one row (sheet {im.width} x {im.height}), {kd['ticks']} ticks per frame "
                f"({60 / kd['ticks']:.0f} per second), loop {n * kd['ticks']} ticks = {n * kd['ticks'] / 60:.2f} s. Unchanged.",
                f"Palette \"{kd['palname']}\": {len(used)} of 15 colours used in this sheet, plus transparent",
                f"Sprite columns {w // 16} (16 px wide), {h // 16} tiles tall",
                f"Tiles raw {raw}, unique {uq}, unique with flips {fl}",
                f"Opaque bounding box over all frames x {ob[0]}..{ob[2]}, y {ob[1]}..{ob[3]}",
                f"Hit box x {x0}..{x1}, y {y0}..{y1} ({x1 - x0 + 1} x {y1 - y0 + 1}), relative to the frame, unchanged: {kd['hitnote']}. "
                f"{cover:.0f} % of the box is covered by the body " + ('in every frame.' if kd['key'] != 'c' else 'in at least one frame of the tumble.'),
                f"Loop seam {sm[0]} px; other neighbouring frames mean {sm[1]:.0f} px, largest {sm[2]} px",
                f"Stray pixels per frame: {st_new:.1f}" + (f" (old sheet {st_old:.1f})" if st_old is not None else ''),
                f"Distinct frames in the loop: {distinct} of {n}",
                f"Gif frame time {ms} ms (game {kd['ticks'] * 1000 / 60:.1f} ms; gif timing has 10 ms steps)"]
        summary.append(f"{kd['key'].upper()}: {n} frames ({distinct} distinct), {len(used)} colours, tiles {raw}/{uq}/{fl}, "
                       f"seam {sm[0]} vs mean {sm[1]:.0f} max {sm[2]}, strays {st_new:.1f} (old {st_old}), hit cover {cover:.0f}%")
        if kd['key'] == 'a':
            br = [int(np.isin(f_, (11, 12)).sum()) for f_ in fr]                 # pale cyan and white
            op = [int((f_ > 0).sum()) for f_ in fr]
            L = lum(pal)
            hi = [int((L[f_] > 200).sum()) for f_ in fr]                         # any pixel brighter than luma 200
            others = max(v for i, v in enumerate(br) if i != FS)
            hio = max(v for i, v in enumerate(hi) if i != FS)
            out += [f"Flash: one strike per loop, at frame {FS}, shown for {TA} ticks ({TA * 1000 / 60:.0f} ms). "
                    f"One loop is {NA * TA} ticks, so {60 / (NA * TA):.3f} flashes per second per cloud (limit asked: under 3).",
                    f"Flash size: {br[FS]} pale-cyan or white pixels in the strike frame = {100 * br[FS] / (w * h):.1f} % of the "
                    f"48 x 48 frame, {100 * br[FS] / op[FS]:.1f} % of its opaque pixels. No other frame has more than {others}. "
                    f"The frame before has {br[FS - 1]}, the frame after {br[FS + 1]}: never two bright frames in a row.",
                    f"Same check by brightness (pixels above luma 200, which also counts the cream rim): strike frame {hi[FS]} "
                    f"= {100 * hi[FS] / (w * h):.1f} % of the frame; frame before {hi[FS - 1]}, frame after {hi[FS + 1]}, "
                    f"largest other frame {hio}. No full-sprite white frame.",
                    f"Charge: frames 4..{FS - 1} build ({(FS - 4) * TA} ticks), frame {FS} strikes, frames {FS + 1}..{FS + 3} "
                    f"fade, frames {FS + 4}..{NA - 1} and 0..3 rest (a small blue glow stays in the belly).",
                    'Several clouds on screen: start them at the same loop phase or at phases at least 8 frames (32 ticks) '
                    f"apart. With 2 clouds that is at most {2 * 60 / (NA * TA):.2f} flashes per second."]
            summary.append(f"   flash bright px {br[FS]} ({100 * br[FS] / (w * h):.1f}% of frame), neighbours {br[FS - 1]}/{br[FS + 1]}, "
                           f"max other {others}; luma>200: {hi[FS]} ({100 * hi[FS] / (w * h):.1f}%), neighbours {hi[FS - 1]}/{hi[FS + 1]}, max other {hio}")
        if kd['key'] == 'b':
            hot = [int(np.isin(f_, (10, 11, 12, 13)).sum()) for f_ in fr]
            out += [f"No flash. Hot colours (orange red to pale yellow) per frame: {min(hot)}..{max(hot)} px, all on the collar edge.",
                    f"Spin: {KP} blade pitches per loop ({NV} blades). {KP} and 16 share no factor, so the globe shows 16 different "
                    'blade positions; the loop closes because the blades are alike.']
        if kd['key'] == 'c':
            pk = [int(np.isin(f_, (12, 13)).sum()) for f_ in fr]
            grey = [int(np.isin(f_, (4, 5, 6, 7)).sum()) for f_ in fr]
            out += [f"No flash: ember cracks breathe twice per loop ({2 * 60 / (NC * TC):.2f} per second), each crack with its own "
                    f"phase; yellow or pale-yellow pixels per frame {min(pk)}..{max(pk)} of 1024 ({100 * max(pk) / 1024:.1f} % at most).",
                    f"Grey pixels (steel mid and lighter) per frame: {min(grey)}..{max(grey)}."]
        out.append('')
        if preview:
            cols = 8
            rows = (n + cols - 1) // cols
            cs = Image.new('RGB', (cols * w * 4, rows * h * 4), GIF_BG)
            for i, f_ in enumerate(fr):
                cs.paste(on_bg(f_, pal, GIF_BG, 4), ((i % cols) * w * 4, (i // cols) * h * 4))
            cs.save(os.path.join(HERE, f"preview_{kd['key']}.png"))
    out += [f"Total unique tiles for the three kinds: {' + '.join(str(k['uq']) for k in kinds)} = {total_u} "
            f"(with flips {total_f}). Sheets before this pass: 212 + 90 + 96 = 398.",
            'Palettes: 2 for the three kinds. "storm" (A) and "hot_metal" (B and C). RGB after 5-bit rounding:',
            '  storm     ' + ' '.join('%d,%d,%d' % c for c in PAL_STORM),
            '  hot_metal ' + ' '.join('%d,%d,%d' % c for c in PAL_HOT),
            'Mood colours in on_moods_2x.png: ' + ', '.join(f"{m} {c}" for m, c in MOODS) + '.',
            f"Gif background {GIF_BG}."]
    with open(os.path.join(HERE, 'numbers.txt'), 'w') as fh:
        fh.write('\n'.join(out) + '\n')
    # one frame of each kind on the three flat sky colours (the cloud at rest: that was its weak frame)
    pick = [(fa[0], PAL_STORM), (fb[3], PAL_HOT), (fc[5], PAL_HOT)]
    pw, ph_ = 8 + 48 + 12 + 32 + 12 + 32 + 8, 64
    moods = Image.new('RGB', (pw * 2, ph_ * 2 * 3))
    for mi, (mname, col) in enumerate(MOODS):
        canvas = np.zeros((ph_, pw, 3), np.uint8)
        canvas[:] = col
        x = 8
        for (fr_, pal) in pick:
            h, w = fr_.shape
            y = (ph_ - h) // 2
            rgba = to_rgba(fr_, pal)
            sel = rgba[..., 3] > 0
            canvas[y:y + h, x:x + w][sel] = rgba[..., :3][sel]
            x += w + 12
        moods.paste(Image.fromarray(canvas, 'RGB').resize((pw * 2, ph_ * 2), Image.NEAREST), (0, mi * ph_ * 2))
    moods.save(os.path.join(HERE, 'on_moods_2x.png'), optimize=True)
    # before / after: two frames per kind, old left of new, four times size
    ba_frames = {'a': (0, FS), 'b': (0, 5), 'c': (5, 12)}
    S, pad, lab = 4, 8, 14
    bw = 4 * 48 * S + 5 * pad
    bh = sum(k['h'] * S + lab + pad for k in kinds) + pad
    ba = Image.new('RGB', (bw, bh), (20, 23, 28))
    dr = ImageDraw.Draw(ba)
    y = pad
    for kd in kinds:
        of = old_frames(kd['key'], kd['w'], kd['h'], kd['n'])
        x = pad
        for fnum in ba_frames[kd['key']]:
            for which in ('Before', 'After'):
                dr.text((x, y), f"{kd['name']}, frame {fnum}: {which.lower()}", fill=(200, 205, 212))
                cell = Image.new('RGB', (kd['w'], kd['h']), GIF_BG)
                if which == 'Before':
                    if of is not None:
                        cell.paste(of[fnum], (0, 0), of[fnum])
                else:
                    cell = on_bg(kd['frames'][fnum], kd['pal'], GIF_BG, 1)
                ba.paste(cell.resize((kd['w'] * S, kd['h'] * S), Image.NEAREST), (x, y + lab))
                x += 48 * S + pad
        y += kd['h'] * S + lab + pad
    ba.save(os.path.join(HERE, 'before_after_4x.png'), optimize=True)
    write_html(kinds, out)
    print('\n'.join(summary))
    print('total unique', total_u, 'with flips', total_f)
    for nm, pal in (('storm', PAL_STORM), ('hot_metal', PAL_HOT)):
        print('palette', nm, len(pal), 'colours,', len(set(pal)), 'distinct')
    for kd in kinds:
        a = np.array(Image.open(os.path.join(HERE, f"sheet_{kd['key']}_1x.png")).convert('RGBA'))
        cols_ = set(map(tuple, a[a[..., 3] > 0][:, :3].tolist()))
        print('sheet', kd['key'], a.shape[1], 'x', a.shape[0], 'multiple of 16:', a.shape[1] % 16 == 0 and a.shape[0] % 16 == 0,
              'opaque colours read back from the PNG:', len(cols_), 'all in palette:', cols_ <= set(kd['pal']),
              'alpha only 0 or 255:', set(np.unique(a[..., 3]).tolist()) <= {0, 255})


def write_html(kinds, numbers):
    rows = []
    for kd in kinds:
        k = kd['key']
        sw, sh = kd['w'] * kd['n'] * 2, kd['h'] * 2
        rows.append(f"""<section>
<h2>{kd['name']}</h2>
<div class="pair">
<figure><img src="{OLD_REL}/anim_{k}_3x.gif" width="{kd['w'] * 3}" height="{kd['h'] * 3}" alt="{kd['name']}, before, animated"><figcaption>Before the clean-up</figcaption></figure>
<figure><img src="anim_{k}_3x.gif" width="{kd['w'] * 3}" height="{kd['h'] * 3}" alt="{kd['name']}, after, animated"><figcaption>After the clean-up, game timing, three times size</figcaption></figure>
</div>
<figure class="strip"><img src="{OLD_REL}/sheet_{k}_1x.png" width="{sw}" height="{sh}" alt="{kd['name']}, sheet before"><figcaption>Sheet before, {kd['n']} frames, two times size</figcaption></figure>
<figure class="strip"><img src="sheet_{k}_1x.png" width="{sw}" height="{sh}" alt="{kd['name']}, sheet after"><figcaption>Sheet after, {kd['n']} frames, two times size</figcaption></figure>
</section>""")
    num = []
    for line in numbers:
        if not line:
            num.append('<p class="gap"></p>')
        elif line in [k['name'] for k in kinds]:
            num.append(f'<h3>{line}</h3>')
        else:
            num.append(f'<p>{line}</p>')
    fixes = ''.join(f'<h3>{t}</h3><p>{d}</p>' for (t, d) in FIXTEXT)
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Gum Trip moving hazards: hand clean-up pass</title>
<style>
body {{ background: #14171c; color: #d9dde3; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  margin: 0; padding: 24px 32px 64px; line-height: 1.45; }}
h1 {{ font-size: 24px; margin: 0 0 4px; }}
h2 {{ font-size: 19px; margin: 0 0 4px; color: #8fd3ff; }}
h3 {{ font-size: 15px; margin: 14px 0 2px; color: #8fd3ff; }}
section {{ border-top: 1px solid #2c323b; padding: 20px 0; }}
p {{ margin: 2px 0; max-width: 1000px; }}
p.gap {{ height: 6px; }}
.pair {{ display: flex; gap: 24px; flex-wrap: wrap; margin: 12px 0; }}
figure {{ margin: 0; }}
figure.strip {{ overflow-x: auto; margin: 12px 0; padding-bottom: 6px; }}
figure.strip img {{ background: #586880; display: block; }}
figure.wide {{ overflow-x: auto; }}
figcaption {{ font-size: 13px; color: #98a1ad; margin-top: 4px; }}
img {{ image-rendering: pixelated; }}
.numbers p {{ font-size: 14px; }}
</style></head><body>
<h1>Gum Trip moving hazards: hand clean-up pass</h1>
<p>The three final sheets before and after the clean-up. Drafts only, nothing here is wired into the game. Weak points and open choices: README.md in this folder.</p>
<section><h2>Before and after, four times size</h2>
<p>Two frames of each kind. Left of each pair: the sheet before. Right: after.</p>
<figure class="wide"><img src="before_after_4x.png" alt="Old against new, two frames per kind"></figure></section>
{''.join(rows)}
<section><h2>On the three sky moods</h2>
<p>One frame of each kind on a flat sky colour: dusk, moon, storm (top to bottom), two times size. The cloud is shown at rest.</p>
<figure><img src="on_moods_2x.png" alt="The three hazards on dusk, moon and storm sky colours"></figure></section>
<section><h2>What changed per fix item</h2>
{fixes}
</section>
<section class="numbers"><h2>Numbers</h2>
{''.join(num)}
</section>
</body></html>
"""
    with open(os.path.join(HERE, 'index.html'), 'w') as fh:
        fh.write(html)


if __name__ == '__main__':
    main()
