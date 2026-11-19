#!/usr/bin/env python3
# Gumbirds, Gum Trip: SECOND hand pass (final3) on the draft sheets of the three moving hazards (draft art, nothing in
# the build reads this). Same frame sizes, counts, timing and hit boxes as ../2026-11-10-gum-trip-moving-hazard-final2/.
# This pass: cloud top billows redrawn by hand (FIXES table), brighter resting trail, hot rim on the vent base ring,
# coal silhouette broken by bites and a spur that are fixed to the lump and tumble with it.
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
# Run: /opt/homebrew/bin/python3.14 -I draw_moving_hazard_final3.py [--preview]
import os
import sys
sys.dont_write_bytecode = True
import json
import math
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OLD = os.path.join(HERE, '..', '2026-11-10-gum-trip-moving-hazard-final2')
OLD_REL = '../2026-11-10-gum-trip-moving-hazard-final2'
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
HAND = {'a': [0, 0], 'b': [0, 0], 'c': [0, 0]}            # per kind: pixels listed in the table, pixels it changed
CHARS = '.123456789abcdef'                                # '.' = transparent, then palette index 1..15


def art(x0, y0, rows):
    """A hand-drawn patch: one character per pixel, left end at x0, top row at y0. A space leaves the pixel alone."""
    return [(x0 + i, y0 + j, CHARS.index(ch)) for j, row in enumerate(rows) for i, ch in enumerate(row) if ch != ' ']


def R(n, t, width=33):
    """One 33 px patch row (x 8..40): n transparent pixels, the drawn pixels t, transparent to the end."""
    row = '.' * n + t
    assert len(row) <= width
    return row + '.' * (width - len(row))


# A: the top billows, drawn by hand for every frame whose top outline had a flat run of 7 px or more (frames 2, 4..9,
# 16, 17) and frame 3 between them. One small nub stays at x 23..25 from frame 4 to 9, the right hand billow rises in
# frame 2, splits in 3 and 4, sinks from 5 to 7, the left shoulder lump drifts left from 4 to 9.
_TOPS = {
    2: (4, [R(17, '1111'), R(15, '117666111'), R(14, '177665566611')]),
    3: (4, [R(16, '111'), R(15, '17661..111')]),
    4: (5, [R(16, '1111..1111'), R(9, '111...17666117666' + '1'), R(8, '1766111766556665556' + '1')]),
    5: (5, [R(15, '111....11111'), R(10, '111.17661111766661'), R(8, '117661176566666555661')]),
    6: (5, [R(15, '111.....111'), R(8, '1111..17661111176' + '61'), R(7, '1776611766566666655111')]),
    7: (5, [R(15, '111'), R(9, '1111.176611...111'), R(6, '1117666176656611176611'),
            R(5, '176643336333335666544661')]),
    8: (6, [R(8, '1111..17611..1111'), R(5, '111766611764661176661'), R(4, '17766554776343366655411')]),
    9: (6, [R(6, '1111....17661..111'), R(4, '1176661111764461176611'), R(3, '177665566776344366655611')]),
    16: (3, [R(13, '111'), R(12, '1766111'), R(11, '176656661')]),
    17: (3, [R(13, '1111'), R(11, '11766611'), R(10, '1776655661')]),
}
for _f, (_y0, _rows) in _TOPS.items():
    FIXES['a'][_f] = art(8, _y0, _rows)
# B: the flicker on the hot rim of the base ring: one yellow pixel on the lip (y 21) and, in most frames, one hot
# pixel on the underside (y 22), placed per frame so the glint never sits still and never jumps more than 3 px.
_FLICK = [(14, 16), (15, 17), (17, 15), (16, None), (13, 16), (15, 18), (18, 14), (16, 16),
          (14, 17), (17, None), (15, 15), (13, 17), (16, 14), (18, 16), (15, None), (17, 18)]
for _f, (_a, _b) in enumerate(_FLICK):
    FIXES['b'][_f] = [(_a, 21, 12)] + ([(_b, 22, 10)] if _b is not None else [])


def apply_fixes(kind, f, idx):
    for key in ('*', f):
        for (x, y, c) in FIXES[kind].get(key, ()):
            HAND[kind][0] += 1
            HAND[kind][1] += int(idx[y, x] != c)
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
        # dashes of periwinkle with a cyan head; the dash grows and more of it turns cyan as the charge builds.
        # (final2: 2 px periwinkle at rest, deep blue while charging; deep blue is darker than the moon sky.)
        if f == FS + 1:
            run, per, hot = 9, 9, 9
        elif f == FS + 2:
            run, per, hot = 5, 9, 2
        elif c > 0.75:
            run, per, hot = 6, 9, 3
        elif c > 0.45:
            run, per, hot = 5, 9, 2
        elif c > 0.2:
            run, per, hot = 4, 9, 1
        else:
            run, per, hot = 3, 9, 1                                          # rest: 3 px dashes, one cyan head each
        for j, (x, y) in enumerate(pts):
            ph = (j + 3 * f) % per
            if ph < run:
                put(idx, x, y, 10 if ph < hot else 15, only=empty)
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
    # hot rim on the base ring: the lip glows orange (rust at the shaded end), the underside red. Steel above it.
    for x in range(11, 22):
        if idx[21, x]:
            idx[21, x] = 9 if x in (11, 21) else (10 if x in (12, 19, 20) else 11)
    for x in range(13, 20):
        if idx[22, x]:
            idx[22, x] = 8 if x in (13, 19) else 9
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


# Hand breaks of the silhouette. They are fixed to the lump (body space), so the same chips tumble with it.
def _unit(v):
    v = np.array(v, float)
    return v / np.linalg.norm(v)


def _surf(dv):
    """Distance from the centre to the coal surface along the body direction dv."""
    dn = PN @ dv
    return float(np.min(PD[dn > 1e-6] / dn[dn > 1e-6]))


_k = np.arange(600) + 0.5
_cp_ = np.arccos(1 - 2 * _k / 600)
_ct_ = math.pi * (1 + 5 ** 0.5) * _k
_CAND = np.stack([np.cos(_ct_) * np.sin(_cp_), np.sin(_ct_) * np.sin(_cp_), np.cos(_cp_)], 1)
_CANDT = np.array([_surf(c_) for c_ in _CAND])


def _corner(seed, cone=0.80):
    """The corner of the lump nearest to a chosen direction: the farthest surface point inside a cone round it."""
    sel = (_CAND @ _unit(seed)) > cone
    return _CAND[sel][np.argmax(_CANDT[sel])]


COLD, HOTCAV, SPURID = NPL, NPL + 1, NPL + 2
# Positions chosen by hand from a search over the lump: with these four, every frame of the tumble shows a break.
# lumps left standing where the coal broke: (body direction, chain of (distance outside the surface, radius))
SPURS = [(_unit((0.638, 0.744, 0.198)), ((-0.5, 2.3), (1.2, 2.0), (2.4, 1.5))),     # the long spur
         (_unit((0.560, -0.717, -0.415)), ((-0.8, 2.8), (1.0, 2.2))),               # a blunt knob
         (_unit((-0.493, -0.095, 0.865)), ((-0.5, 2.4), (0.9, 1.8))),               # a short stub
         (_unit((-0.613, 0.770, -0.175)), ((-0.6, 2.6), (1.0, 2.0)))]               # a second knob
# bites beside each lump: (body direction, radius, how far the centre sits outside the surface, what the break shows)
BITES = [(_unit((0.617, 0.399, 0.678)), 4.5, 1.0, HOTCAV),                          # the one hot break
         (_unit((0.216, -0.976, -0.010)), 4.5, 1.0, COLD),
         (_unit((-0.550, -0.607, 0.574)), 4.5, 1.0, COLD),
         (_unit((-0.104, 0.886, -0.452)), 4.5, 1.0, COLD)]
CRACKX = np.zeros((NPL + 3, NPL + 3), bool)
CRACKX[:NPL, :NPL] = CRACK
CRACKX[HOTCAV, :NPL] = CRACKX[:NPL, HOTCAV] = True              # the edge of the hot break glows
CPHX = np.full((NPL + 3, NPL + 3), 1.3)
CPHX[:NPL, :NPL] = CPH


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
    inb = ok & (zf >= zb) & (zf < 1e8)
    for (dv, r, off, cid) in BITES:                         # bites taken out of the solid
        cx, cy, cz = (Rm @ dv) * (_surf(dv) + off)
        h2 = r * r - (x - cx) ** 2 - (y - cy) ** 2
        hh = np.sqrt(np.maximum(h2, 0))
        hit = inb & (h2 > 0)
        front = hit & (cz + hh >= zf) & (cz - hh < zf)
        zf = np.where(front, cz - hh, zf)
        fid = np.where(front, cid, fid)
        back = hit & ~front & (cz - hh <= zb) & (cz + hh > zb)
        zb = np.where(back, cz + hh, zb)
        inb &= zf >= zb
    for (sdir, off, r) in [(sd, o_, r_) for (sd, balls) in SPURS for (o_, r_) in balls]:    # lumps added to the solid
        cx, cy, cz = (Rm @ sdir) * (_surf(sdir) + off)
        h2 = r * r - (x - cx) ** 2 - (y - cy) ** 2
        hh = np.sqrt(np.maximum(h2, 0))
        hit = h2 > 0
        new = hit & (~inb | (cz + hh > zf))
        zb = np.where(hit & ~inb, cz - hh, zb)
        zf = np.where(new, cz + hh, zf)
        fid = np.where(new, SPURID, fid)
        inb |= hit
    mask = clean_mask(inb)
    light3 = np.array([-0.55, -0.62, 0.56])
    light3 /= np.linalg.norm(light3)
    lit = np.concatenate([n @ light3, [-1.0, -1.0, 0.45]])                   # breaks are dark, the spur is mid
    lvl = np.digitize(lit[fid], [-0.05, 0.3, 0.58, 0.82])                    # 0..4, one flat tone per facet
    idx = np.where(mask, np.array([14, 14, 2, 2, 2])[lvl], 0)                # black coal: no grey facet fill at all
    idx[mask & (fid == HOTCAV)] = 15                                         # the hot break: warm plum inside
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
        isc = both & CRACKX[a_, b_]
        view = crack[:H - sy, :W - sx]
        view |= isc
        pv = cph[:H - sy, :W - sx]
        pv[isc] = CPHX[a_, b_][isc]
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


def concavity(m):
    """Area of the convex hull of the opaque pixels minus the opaque pixel count: 0 for a convex shape."""
    ys, xs = np.nonzero(m)
    pts = set()
    for (px, py) in zip(xs.tolist(), ys.tolist()):
        pts |= {(px, py), (px + 1, py), (px, py + 1), (px + 1, py + 1)}
    pts = sorted(pts)

    def cr(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    hull = []
    for seq in (pts, pts[::-1]):
        part = []
        for p in seq:
            while len(part) >= 2 and cr(part[-2], part[-1], p) <= 0:
                part.pop()
            part.append(p)
        hull += part[:-1]
    a = sum(hull[i][0] * hull[(i + 1) % len(hull)][1] - hull[(i + 1) % len(hull)][0] * hull[i][1] for i in range(len(hull)))
    return abs(a) / 2 - int(m.sum())


def biggest(m):
    """The largest 4-connected group of opaque pixels (drops loose sparks)."""
    seen = np.zeros(m.shape, bool)
    best = np.zeros(m.shape, bool)
    for (y, x) in zip(*np.nonzero(m)):
        if seen[y, x]:
            continue
        grp, todo = [], [(int(y), int(x))]
        seen[y, x] = True
        while todo:
            cy, cx = todo.pop()
            grp.append((cy, cx))
            for (ny, nx) in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                if 0 <= ny < m.shape[0] and 0 <= nx < m.shape[1] and m[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    todo.append((ny, nx))
        if len(grp) > best.sum():
            best = np.zeros(m.shape, bool)
            for (cy, cx) in grp:
                best[cy, cx] = True
    return best


def flat_top(m, x0=9, x1=39):
    """Longest run of neighbouring columns whose top opaque pixel sits on the same row (the boxy top fault)."""
    tops = [int(np.argmax(m[:, x])) if m[:, x].any() else -1 for x in range(m.shape[1])]
    best, x = 0, x0
    while x <= x1:
        j = x
        while j + 1 <= x1 and tops[j + 1] == tops[x] and tops[x] >= 0:
            j += 1
        best = max(best, j - x + 1)
        x = j + 1
    return best


def old_idx(key, w, h, n, pal):
    fr = old_frames(key, w, h, n)
    if fr is None:
        return None
    look = {c: i + 1 for i, c in enumerate(pal)}
    out = []
    for im in fr:
        a = np.array(im)
        out.append(np.array([[look.get(tuple(px[:3]), 0) if px[3] else 0 for px in row] for row in a.tolist()]))
    return out


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
    ('A. Cloud top',
     'The top billows of frames 2 to 9, 16 and 17 are drawn by hand, pixel by pixel (table _TOPS in the script). '
     'The fault (a flat top outline of 7 to 19 px) was in frames 2, 4 to 9, 16 and 17; frame 3 is redrawn so the '
     'shapes flow through it. The right billow rises in frame 2, splits in 3 and 4 and sinks from 5 to 7; one small '
     'nub stays in place from 4 to 9; the left shoulder lump drifts left.'),
    ('A. Charge trail',
     'At rest the trail is now 3 px dashes of periwinkle with one cyan head pixel each (final2: 2 px periwinkle). While '
     'the charge builds the dash grows to 4, 5 and 6 px and 1, 2 and 3 of its pixels are cyan (final2 used deep blue '
     'there, which is darker than the moon sky). The strike frame is unchanged: white core, cyan halo, one frame.'),
    ('B. Vent base ring',
     'The lip of the base ring (row 21) glows orange with red orange ends and rust at the shaded end; its underside '
     '(row 22) is rust and deep red. One yellow glint and one red orange pixel move along it by a hand-set table, '
     'different in each of the 16 frames. Blades, collar and chain are untouched: steel, no stripes, no dither.'),
    ('C. Coal',
     'The lump is no longer convex. Four lumps stand out of it (a long spur, two knobs, a stub) and four bites are '
     'scooped out beside them; one bite is a hot break with a glowing edge. All eight are fixed to the lump, so the '
     'same breaks tumble with it. Their positions are hand-picked so that every frame shows a break in the outline.'),
    ('Kept',
     'Frame sizes, frame counts, ticks per frame, hit boxes, two palettes of 15 colours, JSON format, one strike '
     'frame per loop.'),
]
BEFORE_SUM = (203, 91, 96)


def main():
    preview = '--preview' in sys.argv
    for k in HAND:
        HAND[k] = [0, 0]
    fa, ma = zip(*[squall_frame(f) for f in range(NA)])
    fb = [vent_frame(f) for f in range(NB)]
    fc, mc = zip(*[coal_frame(f) for f in range(NC)])
    hand = {k: tuple(v) for k, v in HAND.items()}
    kinds = [
        dict(key='a', name='Skip-rope squall', frames=list(fa), pal=PAL_STORM, palname='storm', ticks=TA, hit=HIT_A,
             body=np.all(np.stack(ma), 0),
             hitnote='the cloud body only (user decision); the trail below the base and the flank sparks do not hurt'),
        dict(key='b', name='Flue spinner', frames=fb, pal=PAL_HOT, palname='hot_metal', ticks=TB, hit=HIT_B,
             body=np.all(np.stack(fb) > 0, 0),
             hitnote='the globe, 1 px inside its steel; collar and chain do not hurt'),
        dict(key='c', name='Cinder', frames=list(fc), pal=PAL_HOT, palname='hot_metal', ticks=TC, hit=HIT_C,
             body=np.any(np.stack(mc), 0),
             hitnote='the coal; sparks do not hurt'),
    ]
    out = ['Gum Trip moving hazards, second hand pass (final3). Measured by draw_moving_hazard_final3.py from the sheets it wrote.',
           'Tiles are 16 x 16. Raw = non-empty tiles over all frames; unique = distinct after removing exact duplicates;',
           'with flips = distinct when horizontal and vertical mirror copies also count as duplicates.',
           'Loop seam = pixels that differ between the last frame and frame 0, beside the same count for the other',
           'neighbouring frame pairs (mean and largest). A seam inside that range means no pop.',
           'Stray pixels = opaque pixels whose colour touches no pixel of the same colour, mean per frame.',
           'Hand-placed pixels = pixels listed one by one in the script; changed = those that differ from the drawn rule.', '']
    total_u = total_f = 0
    summary = []
    L = lum(PAL_STORM)
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
            'source': 'thoughts/shared/drafts/2026-11-10-gum-trip-moving-hazard-final3/draw_moving_hazard_final3.py '
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
        old = old_idx(kd['key'], w, h, n, pal)
        kd.update(w=w, h=h, n=n, uq=uq, old=old)
        ki = 'abc'.index(kd['key'])
        out += [kd['name'],
                f"Frame size {w} x {h} px, {n} frames in one row (sheet {im.width} x {im.height}), {kd['ticks']} ticks per frame "
                f"({60 / kd['ticks']:.0f} per second), loop {n * kd['ticks']} ticks = {n * kd['ticks'] / 60:.2f} s. Unchanged.",
                f"Palette \"{kd['palname']}\": {len(used)} of 15 colours used in this sheet, plus transparent",
                f"Sprite columns {w // 16} (16 px wide), {h // 16} tiles tall",
                f"Tiles raw {raw}, unique {uq} (final2 {BEFORE_SUM[ki]}, difference {uq - BEFORE_SUM[ki]:+d}), unique with flips {fl}",
                f"Opaque bounding box over all frames x {ob[0]}..{ob[2]}, y {ob[1]}..{ob[3]}",
                f"Hit box x {x0}..{x1}, y {y0}..{y1} ({x1 - x0 + 1} x {y1 - y0 + 1}), relative to the frame, unchanged: {kd['hitnote']}. "
                f"{cover:.0f} % of the box is covered by the body " + ('in every frame.' if kd['key'] != 'c' else 'in at least one frame of the tumble.'),
                f"Loop seam {sm[0]} px; other neighbouring frames mean {sm[1]:.0f} px, largest {sm[2]} px",
                f"Stray pixels per frame: {st_new:.1f}" + (f" (final2 {st_old:.1f})" if st_old is not None else ''),
                f"Distinct frames in the loop: {distinct} of {n}",
                f"Hand-placed pixels: {hand[kd['key']][0]} listed, {hand[kd['key']][1]} changed.",
                f"Gif frame time {ms} ms (game {kd['ticks'] * 1000 / 60:.1f} ms; gif timing has 10 ms steps)"]
        summary.append(f"{kd['key'].upper()}: {n} frames ({distinct} distinct), {len(used)} colours, tiles {raw}/{uq}/{fl}, "
                       f"seam {sm[0]} vs mean {sm[1]:.0f} max {sm[2]}, strays {st_new:.1f} (old {st_old}), hit cover {cover:.0f}%, hand {hand[kd['key']]}")
        if kd['key'] == 'a':
            br = [int(np.isin(f_, (11, 12)).sum()) for f_ in fr]                 # pale cyan and white
            cy = [int(np.isin(f_, (10, 11, 12)).sum()) for f_ in fr]             # the same plus cyan
            op = [int((f_ > 0).sum()) for f_ in fr]
            hi = [int((L[f_] > 200).sum()) for f_ in fr]                         # any pixel brighter than luma 200
            others = max(v for i, v in enumerate(br) if i != FS)
            hio = max(v for i, v in enumerate(hi) if i != FS)
            cyo = max(v for i, v in enumerate(cy) if i != FS)
            ft = [flat_top(f_ > 0) for f_ in fr]
            fto = [flat_top(o_ > 0) for o_ in old] if old else None
            tr = [int(np.isin(f_[33:], (10, 15)).sum()) for f_ in fr]
            rest = [i for i in range(NA) if i >= FS + 4 or i < 4]
            out += [f"Flash: one strike per loop, at frame {FS}, shown for {TA} ticks ({TA * 1000 / 60:.0f} ms). "
                    f"One loop is {NA * TA} ticks, so {60 / (NA * TA):.3f} flashes per second per cloud (limit asked: under 3).",
                    f"Flash size: {br[FS]} pale-cyan or white pixels in the strike frame = {100 * br[FS] / (w * h):.1f} % of the "
                    f"48 x 48 frame, {100 * br[FS] / op[FS]:.1f} % of its opaque pixels. No other frame has more than {others}. "
                    f"The frame before has {br[FS - 1]}, the frame after {br[FS + 1]}: never two bright frames in a row.",
                    f"Same check by brightness (pixels above luma 200, which also counts the cream rim): strike frame {hi[FS]} "
                    f"= {100 * hi[FS] / (w * h):.1f} % of the frame; frame before {hi[FS - 1]}, frame after {hi[FS + 1]}, "
                    f"largest other frame {hio}. No full-sprite white frame.",
                    f"Same check with cyan counted as bright (cyan, pale cyan, white; cyan has luma {L[10]:.0f}): strike frame {cy[FS]} "
                    f"= {100 * cy[FS] / (w * h):.1f} % of the frame; frame before {cy[FS - 1]}, frame after {cy[FS + 1]}, largest other "
                    f"frame {cyo}; at rest {min(cy[i] for i in rest)}..{max(cy[i] for i in rest)}.",
                    f"Trail at rest: {min(tr[i] for i in rest)}..{max(tr[i] for i in rest)} trail pixels below the base per frame (0 where the rope swings behind the cloud, frames 2 to 8) "
                    f"(cyan luma {L[10]:.0f}, periwinkle luma {L[15]:.0f}). Sky luma: "
                    + ', '.join(f"{m} {0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]:.0f}" for m, c in MOODS)
                    + f". The final2 charging trail used deep blue and blue (luma {L[8]:.0f} and {L[9]:.0f}).",
                    f"Charge: frames 4..{FS - 1} build ({(FS - 4) * TA} ticks), frame {FS} strikes, frames {FS + 1}..{FS + 3} "
                    f"fade, frames {FS + 4}..{NA - 1} and 0..3 rest (a small blue glow stays in the belly).",
                    'Several clouds on screen: start them at the same loop phase or at phases at least 8 frames (32 ticks) '
                    f"apart. With 2 clouds that is at most {2 * 60 / (NA * TA):.2f} flashes per second.",
                    'Longest flat run of the top outline per frame, x 9..39 (px): ' + ' '.join(str(v) for v in ft)
                    + (f". Final2: {' '.join(str(v) for v in fto)}." if fto else '.'),
                    f"Hand-drawn top frames: {', '.join(str(k) for k in sorted(_TOPS))}."]
            summary.append(f"   flash bright px {br[FS]} ({100 * br[FS] / (w * h):.1f}% of frame), neighbours {br[FS - 1]}/{br[FS + 1]}, "
                           f"max other {others}; luma>200: {hi[FS]} ({100 * hi[FS] / (w * h):.1f}%), neighbours {hi[FS - 1]}/{hi[FS + 1]}, max other {hio}; "
                           f"with cyan {cy[FS]} ({100 * cy[FS] / (w * h):.1f}%), neighbours {cy[FS - 1]}/{cy[FS + 1]}, max other {cyo}, rest {min(cy[i] for i in rest)}..{max(cy[i] for i in rest)}")
            summary.append(f"   flat top {ft} final2 {fto}; trail px rest {min(tr[i] for i in rest)}..{max(tr[i] for i in rest)}")
        if kd['key'] == 'b':
            hot = [int(np.isin(f_, (10, 11, 12, 13)).sum()) for f_ in fr]
            ring = [int(np.isin(f_[21:23], (9, 10, 11, 12)).sum()) for f_ in fr]
            steel = sum(int(np.isin(f_[:20], (8, 9, 10, 11, 12, 13)).sum()) for f_ in fr)
            out += [f"No flash. Hot colours (orange red to pale yellow) per frame: {min(hot)}..{max(hot)} px, on the collar edge and the rim of the base ring.",
                    f"Base ring rim: {min(ring)}..{max(ring)} warm pixels per frame on rows 21 and 22 (lip and underside), 2 px thick. "
                    f"Warm pixels on the globe above the ring (rows 0..19), all frames: {steel}.",
                    f"Spin: {KP} blade pitches per loop ({NV} blades). {KP} and 16 share no factor, so the globe shows 16 different "
                    'blade positions; the loop closes because the blades are alike.']
            summary.append(f"   ring warm px {min(ring)}..{max(ring)}, warm px rows 0..19 total {steel}")
        if kd['key'] == 'c':
            pk = [int(np.isin(f_, (12, 13)).sum()) for f_ in fr]
            grey = [int(np.isin(f_, (4, 5, 6, 7)).sum()) for f_ in fr]
            cv = [int(concavity(biggest(f_ > 0))) for f_ in fr]
            cvo = [int(concavity(biggest(o_ > 0))) for o_ in old] if old else None
            inbox = [int(m_[y0:y1 + 1, x0:x1 + 1].sum()) for m_ in mc]
            out += [f"No flash: ember cracks breathe twice per loop ({2 * 60 / (NC * TC):.2f} per second), each crack with its own "
                    f"phase; yellow or pale-yellow pixels per frame {min(pk)}..{max(pk)} of 1024 ({100 * max(pk) / 1024:.1f} % at most).",
                    f"Grey pixels (steel mid and lighter) per frame: {min(grey)}..{max(grey)}.",
                    'Broken outline, per frame: convex hull area minus coal area in px (0 = convex; the largest connected shape only, so sparks are left out): '
                    + ' '.join(str(v) for v in cv) + f" (lowest {min(cv)})."
                    + (f" Final2, same measure: {' '.join(str(v) for v in cvo)}." if cvo else ''),
                    f"Breaks: {len(SPURS)} lumps and {len(BITES)} bites, fixed to the lump. The lumps reach past the old outline, so the "
                    f"coal bounding box grows; the hit box stays inside the solid part: {min(inbox)}..{max(inbox)} of "
                    f"{(x1 - x0 + 1) * (y1 - y0 + 1)} hit box pixels are coal per frame."]
            summary.append(f"   concavity {cv} min {min(cv)}; final2 {cvo}; hit box coal px {min(inbox)}..{max(inbox)}")
        out.append('')
        if preview:
            cols = 8
            rows = (n + cols - 1) // cols
            cs = Image.new('RGB', (cols * w * 4, rows * h * 4), GIF_BG)
            for i, f_ in enumerate(fr):
                cs.paste(on_bg(f_, pal, GIF_BG, 4), ((i % cols) * w * 4, (i // cols) * h * 4))
            cs.save(os.path.join(HERE, f"preview_{kd['key']}.png"))
    bsum = sum(BEFORE_SUM)
    out += [f"Total unique tiles for the three kinds: {' + '.join(str(k['uq']) for k in kinds)} = {total_u} "
            f"(with flips {total_f}). Final2: {' + '.join(str(v) for v in BEFORE_SUM)} = {bsum}. Difference {total_u - bsum:+d}.",
            'Palettes: 2 for the three kinds, unchanged. "storm" (A) and "hot_metal" (B and C). RGB after 5-bit rounding:',
            '  storm     ' + ' '.join('%d,%d,%d' % c for c in PAL_STORM),
            '  hot_metal ' + ' '.join('%d,%d,%d' % c for c in PAL_HOT),
            'Mood colours in on_moods_2x.png: ' + ', '.join(f"{m} {c}" for m, c in MOODS) + '.',
            f"Gif background {GIF_BG}."]
    with open(os.path.join(HERE, 'numbers.txt'), 'w') as fh:
        fh.write('\n'.join(out) + '\n')
    # the cloud at rest and on its strike frame, one vent frame, one coal frame, on the three flat sky colours
    pick = [(fa[0], PAL_STORM), (fa[FS], PAL_STORM), (fb[3], PAL_HOT), (fc[5], PAL_HOT)]
    pw, ph_ = 8 + sum(p[0].shape[1] + 12 for p in pick) - 12 + 8, 64
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
    # before / after at four times size: cloud frames 3..7, the vent base ring, four coal frames
    S, pad, lab = 4, 8, 14
    rows_ = [('a', (3, 4, 5, 6, 7), (0, 0, 48, 40), 'Cloud, frames 3 to 7'),
             ('b', (0, 5, 10, 15), (4, 14, 28, 30), 'Vent base ring, frames 0, 5, 10, 15'),
             ('c', (0, 6, 12, 18), (0, 4, 28, 32), 'Coal, frames 0, 6, 12, 18')]
    bw = max(len(fs) * ((c[2] - c[0]) * S + pad) for (_, fs, c, _) in rows_) + pad
    bh = sum(2 * ((c[3] - c[1]) * S + lab + pad) for (_, _, c, _) in rows_) + pad
    ba = Image.new('RGB', (bw, bh), (20, 23, 28))
    dr = ImageDraw.Draw(ba)
    y = pad
    for (key, fs, crop, title) in rows_:
        kd = kinds['abc'.index(key)]
        of = old_frames(key, kd['w'], kd['h'], kd['n'])
        cw, ch = crop[2] - crop[0], crop[3] - crop[1]
        for which in ('before (final2)', 'after (final3)'):
            dr.text((pad, y), f"{title}: {which}", fill=(200, 205, 212))
            x = pad
            for fnum in fs:
                cell = Image.new('RGB', (kd['w'], kd['h']), GIF_BG)
                if which.startswith('before'):
                    if of is not None:
                        cell.paste(of[fnum], (0, 0), of[fnum])
                else:
                    cell = on_bg(kd['frames'][fnum], kd['pal'], GIF_BG, 1)
                ba.paste(cell.crop(crop).resize((cw * S, ch * S), Image.NEAREST), (x, y + lab))
                x += cw * S + pad
            y += ch * S + lab + pad
    ba.save(os.path.join(HERE, 'before_after_4x.png'), optimize=True)
    write_html(kinds, out)
    write_readme(kinds, hand, total_u)
    print('\n'.join(summary))
    print('total unique', total_u, 'with flips', total_f, 'final2', bsum, 'difference', total_u - bsum)
    for nm, pal in (('storm', PAL_STORM), ('hot_metal', PAL_HOT)):
        print('palette', nm, len(pal), 'colours,', len(set(pal)), 'distinct')
    for kd in kinds:
        a = np.array(Image.open(os.path.join(HERE, f"sheet_{kd['key']}_1x.png")).convert('RGBA'))
        cols_ = set(map(tuple, a[a[..., 3] > 0][:, :3].tolist()))
        print('sheet', kd['key'], a.shape[1], 'x', a.shape[0], 'multiple of 16:', a.shape[1] % 16 == 0 and a.shape[0] % 16 == 0,
              'opaque colours read back from the PNG:', len(cols_), 'all in palette:', cols_ <= set(kd['pal']),
              'alpha only 0 or 255:', set(np.unique(a[..., 3]).tolist()) <= {0, 255})


WEAK = [
    'Coal: the lumps are built from small rounded shapes, so in some frames a break reads as a bump, not a sharp '
    'chip. No coal pixel is placed by hand; only the positions of the eight breaks are hand-picked.',
    'Cloud: the hand-drawn tops cover the top 3 or 4 rows only. The shading under them is still the rule-drawn one, '
    'frames 10 and 11 keep a flat run of 6 px, and the right flank of frames 8 to 10 is still a straight wall.',
    'Vent: the hot rim is 2 px on a ring 11 px wide. It reads as a warm line, not as glowing metal, and the flicker '
    'is one or two pixels per frame.',
]


def write_readme(kinds, hand, total_u):
    bsum = sum(BEFORE_SUM)
    txt = ['# Gum Trip moving hazards: second hand pass (final3)', '',
           'Draft art only. Nothing here is wired into the game. Before: `../2026-11-10-gum-trip-moving-hazard-final2/`.',
           'Rebuild: `/opt/homebrew/bin/python3.14 -I draw_moving_hazard_final3.py`. Open `index.html` to compare.', '',
           '## What changed', '']
    txt += [f"- **{t}**: {d_}" for (t, d_) in FIXTEXT]
    txt += ['', '## Hand-placed pixels', '',
            f"- Cloud: {hand['a'][0]} pixels listed one by one for {len(_TOPS)} frames (this count includes pixels set to "
            f"transparent to cut the old flat top away); {hand['a'][1]} of them differ from what the rules drew.",
            f"- Vent: {hand['b'][0]} listed (the flicker table), {hand['b'][1]} changed.",
            f"- Coal: {hand['c'][0]}. The breaks are 8 hand-picked positions on the lump, not single pixels.", '',
            '## Tiles', '',
            f"Unique tiles {' + '.join(str(k['uq']) for k in kinds)} = {total_u}. Final2: "
            f"{' + '.join(str(v) for v in BEFORE_SUM)} = {bsum}. Difference {total_u - bsum:+d}. "
            'Frame sizes, counts, timing, hit boxes, palettes and JSON format are unchanged. All numbers: `numbers.txt`.', '',
            '## Weak points left', '']
    txt += [f"{i + 1}. {w_}" for i, w_ in enumerate(WEAK)]
    with open(os.path.join(HERE, 'README.md'), 'w') as fh:
        fh.write('\n'.join(txt) + '\n')


def write_html(kinds, numbers):
    rows = []
    for kd in kinds:
        k = kd['key']
        sw, sh = kd['w'] * kd['n'] * 2, kd['h'] * 2
        rows.append(f"""<section>
<h2>{kd['name']}</h2>
<div class="pair">
<figure><img src="{OLD_REL}/anim_{k}_3x.gif" width="{kd['w'] * 3}" height="{kd['h'] * 3}" alt="{kd['name']}, final2, animated"><figcaption>Before (final2)</figcaption></figure>
<figure><img src="anim_{k}_3x.gif" width="{kd['w'] * 3}" height="{kd['h'] * 3}" alt="{kd['name']}, final3, animated"><figcaption>After (final3), game timing, three times size</figcaption></figure>
</div>
<figure class="strip"><img src="{OLD_REL}/sheet_{k}_1x.png" width="{sw}" height="{sh}" alt="{kd['name']}, final2 sheet"><figcaption>Final2 sheet, {kd['n']} frames, two times size</figcaption></figure>
<figure class="strip"><img src="sheet_{k}_1x.png" width="{sw}" height="{sh}" alt="{kd['name']}, final3 sheet"><figcaption>Final3 sheet, {kd['n']} frames, two times size</figcaption></figure>
</section>""")
    num = []
    for line in numbers:
        if not line:
            num.append('<p class="gap"></p>')
        elif line in [k['name'] for k in kinds]:
            num.append(f'<h3>{line}</h3>')
        else:
            num.append(f'<p>{line}</p>')
    fixes = ''.join(f'<h3>{t}</h3><p>{d_}</p>' for (t, d_) in FIXTEXT)
    weak = ''.join(f'<p>{i + 1}. {w_}</p>' for i, w_ in enumerate(WEAK))
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Gum Trip moving hazards: second hand pass</title>
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
<h1>Gum Trip moving hazards: second hand pass</h1>
<p>The three sheets before (final2) and after (final3) this pass. Drafts only, nothing here is wired into the game.</p>
<section><h2>Before and after, four times size</h2>
<p>Cloud frames 3 to 7, the base ring of the vent, four frames of the coal. Upper row of each pair: final2. Lower row: final3.</p>
<figure class="wide"><img src="before_after_4x.png" alt="Final2 against final3: cloud tops, vent base ring, coal"></figure></section>
{''.join(rows)}
<section><h2>On the three sky moods</h2>
<p>Left to right: the cloud at rest, the cloud on its strike frame, the vent, the coal. Top to bottom: {', '.join(m for m, _ in MOODS)}. Two times size.</p>
<figure><img src="on_moods_2x.png" alt="The cloud at rest and striking, the vent and the coal on the three sky colours"></figure></section>
<section><h2>What changed</h2>
{fixes}
</section>
<section><h2>Weak points left</h2>
{weak}
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
