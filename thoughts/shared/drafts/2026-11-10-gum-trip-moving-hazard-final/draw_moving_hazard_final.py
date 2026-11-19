#!/usr/bin/env python3
# Gumbirds, Gum Trip: FINAL draft sheets for the three moving hazards (draft art, nothing in the build reads this).
#
#   A  Skip-rope squall   48 x 48  24 frames x 4 ticks  slate storm cloud, billows overturn, charge builds, one strike
#   B  Flue spinner       32 x 48  16 frames x 4 ticks  turbine roof vent, helical vanes, hot slots, chain pendulum
#   C  Cinder             32 x 32  24 frames x 3 ticks  tumbling faceted coal, pulsing ember cracks, trailing sparks
#
# Two palettes for all three kinds: "storm" (A) and "hot_metal" (B and C share it). 15 colours each plus transparent.
# Every motion is a closed-form periodic function of the frame number (integer harmonics of the loop only), so the
# last frame leads into frame 0 by construction. The script measures the seam and prints it.
#
# Self-contained: reads no file outside this folder, imports nothing from other draft folders.
# Run: /opt/homebrew/bin/python3.14 -I draw_moving_hazard_final.py [--preview]     (Pillow + numpy, a few seconds)
import os
import sys
sys.dont_write_bytecode = True
import json
import math
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
TAU = 2 * math.pi
CLMAP = np.array([[12, 5, 6, 13], [4, 0, 1, 7], [11, 3, 2, 8], [15, 10, 9, 14]]) / 16.0   # clustered-dot map
LIGHT = np.array([-0.55, -0.62, 0.56])
LIGHT = LIGHT / np.linalg.norm(LIGHT)                    # upper left, towards the viewer
GIF_BG = (88, 104, 128)                                  # mid grey-blue
# Flat sky colours: the most common colour of the middle band (row 64 of 128) of plane_<mood>_sky_1x.png in
# ../2026-11-10-backgrounds-final/, measured once and copied here (the low band is lighter, the top band darker).
MOODS = [('Dusk', (148, 55, 92)), ('Moon', (76, 60, 142)), ('Storm', (40, 86, 99))]


def q5(c):
    return tuple(((v >> 3) << 3) | (v >> 5) for v in c)


def grid(w, h):
    y, x = np.mgrid[0:h, 0:w]
    return x.astype(float), y.astype(float)


def clmap(w, h):
    y, x = np.mgrid[0:h, 0:w]
    return CLMAP[y % 4, x % 4]


def line_pts(x0, y0, x1, y1):
    x0, y0, x1, y1 = int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
    n = max(abs(x1 - x0), abs(y1 - y0), 1)
    return [(int(round(x0 + (x1 - x0) * i / n)), int(round(y0 + (y1 - y0) * i / n))) for i in range(n + 1)]


def put(idx, x, y, c, only=None):
    h, w = idx.shape
    x, y = int(x), int(y)
    if 0 <= x < w and 0 <= y < h and (only is None or only[y, x]):
        idx[y, x] = c


def dilate(m):
    p = np.pad(m, 1)
    return m | p[1:-1, 2:] | p[1:-1, :-2] | p[2:, 1:-1] | p[:-2, 1:-1]


def outline(idx, col):
    op = idx > 0
    idx[dilate(op) & ~op] = col
    return idx


# =============================================================== A  Skip-rope squall (palette "storm")
PAL_STORM = [q5(c) for c in [
    (12, 12, 33),      # 1 outline
    (33, 33, 66),      # 2 deep shadow, indigo
    (57, 62, 99),      # 3 shadow
    (90, 99, 132),     # 4 mid slate
    (132, 140, 165),   # 5 mid light
    (181, 185, 198),   # 6 light
    (231, 226, 214),   # 7 pale warm
    (255, 247, 222),   # 8 warm top light
    (33, 66, 165),     # 9 charge deep blue
    (49, 123, 214),    # 10 charge blue
    (115, 206, 247),   # 11 cyan
    (198, 247, 255),   # 12 pale cyan
    (255, 255, 255),   # 13 white core
    (255, 239, 115),   # 14 spark yellow
    (255, 156, 49),    # 15 spark orange
]]
NA, TA, FS = 24, 4, 17            # frames, ticks per frame, strike frame
#          x   y   r    phase dir zo
PUFFS = [(24, 21, 10.0, 0.0, 1, 3.0), (14, 24, 7.5, 1.1, -1, 1.0), (34, 24, 7.5, 2.3, 1, 1.0),
         (18, 15, 7.0, 3.0, -1, 0.0), (30, 14, 6.5, 4.1, 1, 0.0), (8, 26, 4.5, 5.0, -1, 0.0),
         (40, 26, 4.5, 0.7, 1, 0.0), (19, 28, 6.0, 1.9, -1, 2.0), (29, 28, 6.0, 3.6, 1, 2.0),
         (24, 10, 5.0, 5.6, 1, -1.0)]
PIN_L, PIN_R, PIN_Y = 5, 43, 27


def charge(f):
    """Charge 0..1: builds from frame 4 to the strike, then falls away in four frames."""
    if 4 <= f < FS:
        return ((f - 4) / (FS - 4)) ** 1.6 * 0.9
    return {FS: 1.0, FS + 1: 0.55, FS + 2: 0.3, FS + 3: 0.12}.get(f, 0.0)


def squall_frame(f):
    W = H = 48
    w = TAU * f / NA
    X, Y = grid(W, H)
    D = clmap(W, H)
    best = np.full((H, W), -1e9)
    second = np.full((H, W), -1e9)
    nrm = np.zeros((H, W, 3))
    balls = []
    for (bx, by, br, ph, dr, zo) in PUFFS:
        cx = bx + 1.1 * math.cos(w + ph) * dr
        cy = by + 0.8 * math.sin(w + ph)
        r = br + 0.6 * math.sin(w + ph * 1.7)
        balls.append((cx, cy, r, zo))
        for k in range(2):                                  # two lumps overturn round every billow, once per loop
            psi = ph + dr * w + k * math.pi
            balls.append((cx + 0.62 * r * math.cos(psi), cy + 0.62 * r * math.sin(psi), 0.5 * r, zo + 0.32 * r))
    for (cx, cy, r, zo) in balls:
        d2 = (X - cx) ** 2 + (Y - cy) ** 2
        ins = d2 < r * r
        z = np.where(ins, np.sqrt(np.maximum(r * r - d2, 0)) + zo, -1e9)
        top = z > best
        second = np.where(top, best, np.maximum(second, z))
        nrm[top] = np.stack([(X - cx) / r, (Y - cy) / r, np.sqrt(np.maximum(1 - d2 / (r * r), 0))], -1)[top]
        best = np.where(top, z, best)
    base = 32.5 + 1.0 * np.sin(X * 0.55 + w) + 0.6 * np.sin(X * 0.21 - w)
    mask = (best > -1e8) & (Y <= base)
    s = 0.5 + 0.5 * (nrm @ LIGHT)
    s -= 0.24 * np.clip(1 - (best - second) / 2.5, 0, 1)                    # creases between billows
    s -= 0.34 * np.clip((Y - (base - 8)) / 8, 0, 1)                         # heavy underside
    lv = np.clip(np.floor(s * 6.4 - 1.25 + (D - 0.5) * 0.6), 0, 5).astype(int)
    idx = np.where(mask, lv + 2, 0)
    idx[mask & (s > 0.93)] = 8
    c = charge(f)
    # charge glow in the belly: the shadow side turns blue from inside as the charge builds (dither: soft material)
    g = c * np.exp(-((X - 24) / 13.0) ** 2) * np.clip((Y - 19) / 9.0, 0, 1)
    gl = np.floor(g * 3.5 + (D - 0.5) * 0.9)
    belly = mask & (lv <= 3)
    idx[belly & (gl >= 1)] = 9
    idx[belly & (gl >= 2)] = 10
    idx[belly & (gl >= 3)] = 11
    if f == FS:
        idx[mask & (Y > base - 2)] = 12                                      # the strike lights the base rim only
    rng = np.random.default_rng(1000 + f)
    for _ in range(int(c * 5.5)):                                            # small filaments inside the belly
        x, y = rng.integers(13, 36), rng.integers(23, 30)
        for _ in range(int(rng.integers(3, 6))):
            put(idx, x, y, 12 if c > 0.7 else 11, only=mask)
            x += int(rng.integers(-1, 2))
            y += int(rng.integers(0, 2))
    outline(idx, 1)
    solid = idx > 0
    # the arc: a rope pinned on both flanks, swung round the cloud once per loop; the middle lags the ends
    M = 25
    sv = np.linspace(0, 1, M)
    th = TAU * (f - FS) / NA - 0.55 * np.sin(math.pi * sv)
    a = 11.5 * np.sin(math.pi * sv) ** 0.75
    k = np.arange(M)
    jag = np.sin(math.pi * sv) * 1.25
    ax = PIN_L + (PIN_R - PIN_L) * sv + jag * np.sin(k * 2.4 + 3 * w + k * k * 0.7)
    ay = PIN_Y + a * np.cos(th) + jag * np.sin(k * 1.7 - 5 * w + k * k * 0.3)
    az = a * np.sin(th)
    if f == FS:
        core, halo = 13, 11
    elif f == FS + 1:
        core, halo = 12, 10
    elif f == FS + 2:
        core, halo = 11, 0
    elif c > 0.55:
        core, halo = 11, 0
    elif c > 0.2:
        core, halo = 10, 0
    else:
        core, halo = 9, 0
    pts = []
    for i in range(M - 1):
        seg = line_pts(ax[i], ay[i], ax[i + 1], ay[i + 1])
        for j, (x, y) in enumerate(seg):
            pts.append((x, y, az[i] + (az[i + 1] - az[i]) * j / max(len(seg) - 1, 1)))
    empty = ~solid
    if halo:
        for (x, y, z) in pts:
            for (ox, oy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                put(idx, x + ox, y + oy, halo, only=empty)                   # halo never covers the cloud
    for (x, y, z) in pts:
        put(idx, x, y, core, only=None if z > -0.5 else empty)
    if c > 0.55 and f != FS:
        for i in range(2, M - 2, 4):                                         # hot knots on the charged rope
            if az[i] > -0.5:
                put(idx, round(ax[i]), round(ay[i]), 12)
    for px in (PIN_L, PIN_R):                                                # sparks where the rope is pinned
        if f == FS:
            for (ox, oy, cc) in ((0, 0, 13), (1, 0, 14), (-1, 0, 14), (0, 1, 14), (0, -1, 14), (2, 0, 15), (-2, 0, 15),
                                 (0, 2, 15), (0, -2, 15), (1, 1, 15), (-1, -1, 15), (1, -1, 15), (-1, 1, 15)):
                put(idx, px + ox, PIN_Y + oy, cc)
        elif c > 0.3:
            put(idx, px, PIN_Y, 14)
            arms = ((1, 0), (-1, 0), (0, 1), (0, -1)) if f % 2 == 0 else ((1, 1), (-1, -1), (1, -1), (-1, 1))
            for (ox, oy) in arms:
                put(idx, px + ox, PIN_Y + oy, 15)
        else:
            put(idx, px, PIN_Y, 14 if f % 2 == 0 else 15)
    return idx, mask


# =============================================================== palette "hot_metal" (B and C)
PAL_HOT = [q5(c) for c in [
    (16, 16, 33),      # 1 outline
    (41, 41, 74),      # 2 cool dark (steel shadow, coal shadow)
    (74, 82, 115),     # 3 steel shadow
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
    (189, 132, 33),    # 14 ochre (stripe in shadow)
    (57, 33, 57),      # 15 warm dark plum (coal)
]]

# =============================================================== B  Flue spinner
NB, TB = 16, 4
NV, KP, SLANT = 10, 2, 1.2          # vanes, vane pitches advanced per loop, helix slant (rad of longitude per rad of latitude)
BCX, BCY, BR = 16, 13, 9.5
STEEL = [2, 3, 4, 5, 6]


def vent_frame(f):
    W, H = 32, 48
    w = TAU * f / NB
    X, Y = grid(W, H)
    idx = np.zeros((H, W), int)
    tilt = 0.075 * math.sin(w)                           # the body rocks, the chain answers
    dy = Y - BCY
    dx = X - BCX - tilt * dy
    pitch = TAU / NV
    rot = pitch * KP * f / NB
    rho2 = dx * dx + dy * dy
    inside = rho2 <= BR * BR
    sl = np.clip(-dy / BR, -1, 1)
    lat = np.arcsin(sl)
    cl_ = np.sqrt(1 - sl * sl)
    phi = np.arcsin(np.clip(dx / (BR * np.maximum(cl_, 1e-3)), -1, 1))
    u = ((phi + rot + SLANT * lat) / pitch) % 1.0
    z = np.sqrt(np.maximum(BR * BR - rho2, 0))
    s = (dx * LIGHT[0] + dy * LIGHT[1] + z * LIGHT[2]) / BR
    base = np.digitize(s, [-0.15, 0.2, 0.5, 0.78])        # 0..4
    blade = u < 0.6
    lvl = base + np.where(u < 0.14, 1, 0) - np.where((u > 0.44) & blade, 1, 0)
    lvl = np.clip(lvl, 0, 4)
    col = np.array(STEEL)[lvl]
    col = np.where(blade & (s > 0.88) & (u >= 0.14) & (u <= 0.44), 7, col)
    us = (u - 0.6) / 0.4
    heat = (z / BR) * (1 - np.abs(us - 0.5) * 1.3) * (1 - 0.45 * np.abs(lat) / 1.2)
    hot = np.array([8, 9, 10, 11, 12, 13])[np.digitize(heat, [0.15, 0.3, 0.45, 0.6, 0.75])]
    col = np.where(blade, col, hot)
    cap = dy < -BR * 0.7
    ring = dy > BR * 0.74
    plain = np.array(STEEL)[np.clip(base, 0, 4)]
    col = np.where(cap, plain, col)
    col = np.where(cap & (s > 0.9), 7, col)
    col = np.where(cap & (dy >= -BR * 0.7 - 1), 2, col)
    col = np.where(ring, np.array(STEEL)[np.clip(base - 1, 0, 4)], col)
    col = np.where(ring & (dy < BR * 0.74 + 1), 2, col)
    idx[inside] = col[inside]
    # saw fins: the vane edges stand proud of the globe; they travel down the silhouette like a barber pole
    R2 = BR + 1.7
    fin = (~inside) & (rho2 <= R2 * R2)
    lat2 = np.arcsin(np.clip(-dy / R2, -1, 1))
    u2 = ((np.sign(dx) * math.pi / 2 + rot + SLANT * lat2) / pitch) % 1.0
    tooth = fin & (u2 < 0.42) & (np.abs(lat2) < 0.8)
    idx[tooth & (u2 < 0.2)] = 6
    idx[tooth & (u2 >= 0.2)] = 4
    idx[tooth & (dx > 0) & (u2 >= 0.2)] = 3
    topx = BCX + tilt * (-BR - 1)
    put(idx, round(topx), BCY - 10, 5)
    put(idx, round(topx), BCY - 11, 6)
    # neck, striped collar, torn rust edge
    for y in range(22, 32):
        ox = int(round(tilt * (y - BCY)))
        if y < 24:
            for x in range(12, 21):
                put(idx, x + ox, y, 3 if x < 14 else (2 if x > 17 else 4))
        elif y < 30:
            for x in range(9, 24):
                stripe = ((x + y) // 3) % 2 == 0
                if stripe:
                    cc = 13 if x < 11 else (14 if x > 19 else 12)
                else:
                    cc = 3 if x < 11 else 2
                if y == 24:
                    cc = 6 if x < 19 else 4                                  # top lip
                put(idx, x + ox, y, cc)
        else:
            for x in range(9, 24):
                hgt = (x * 7 + 3) % 5
                if y == 30 and hgt >= 1:
                    put(idx, x + ox, y, 9 if hgt >= 3 else 8)
                if y == 31 and hgt >= 4:
                    put(idx, x + ox, y, 8)
    # chain: five links, each a pendulum that lags the link above it; swing grows down the chain
    px, py = BCX + tilt * (30 - BCY) * 1.0, 30.0
    pts = [(px, py)]
    ang = []
    for i in range(5):
        th = -(0.20 + 0.085 * i) * math.sin(w - 0.55 * (i + 1)) - 0.05 * math.sin(2 * w - 0.9 * i)
        ang.append(th)
        px, py = px + 2.7 * math.sin(th), py + 2.7 * math.cos(th)
        pts.append((px, py))
    for i in range(5):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        if i % 2 == 0:                                                       # link seen face on: a ring
            for (ox, oy, cc) in ((0, -1.5, 5), (-1, -0.5, 6), (-1, 0.5, 5), (1, -0.5, 4), (1, 0.5, 3), (0, 1.5, 3)):
                put(idx, round(mx + ox), round(my + oy), cc)
        else:                                                                # link seen edge on: a bar
            seg = line_pts(x0, y0 - 0.5, x1, y1 + 0.5)
            for j, (x, y) in enumerate(seg):
                put(idx, x, y, 6 if j == 0 else (5 if j < len(seg) - 1 else 3))
    hx, hy = pts[-1]
    d = 1 if ang[-1] >= 0 else -1
    for (ox, oy, cc) in ((0, 0, 5), (0, 1, 5), (0, 2, 4), (-d, 3, 3), (-2 * d, 2, 9)):
        put(idx, round(hx + ox), round(hy + oy), cc)
    outline(idx, 1)
    return idx


# =============================================================== C  Cinder
NC, TC = 24, 3
CCX, CCY, CR = 13, 18, 9.5
COAL = [2, 15, 3, 4, 5, 6]
HOTC = [9, 10, 11, 12, 13]
_rng = np.random.default_rng(11)
NPL = 16
_i = np.arange(NPL) + 0.5
_ph = np.arccos(1 - 2 * _i / NPL)
_th = math.pi * (1 + 5 ** 0.5) * _i
PN = np.stack([np.cos(_th) * np.sin(_ph), np.sin(_th) * np.sin(_ph), np.cos(_ph)], 1) + _rng.normal(0, 0.16, (NPL, 3))
PN /= np.linalg.norm(PN, axis=1, keepdims=True)
PD = CR * (0.72 + 0.28 * _rng.random(NPL))
_cr = _rng.random((NPL, NPL))
CRACK = np.triu(_cr < 0.42, 1)
CRACK = CRACK | CRACK.T
_cp = np.triu(_rng.random((NPL, NPL)) * TAU, 1)
CPH = _cp + _cp.T
HOTFACE = 3
AXIS = np.array([0.5, 0.75, 0.43])
AXIS /= np.linalg.norm(AXIS)
NSPARK = 20
SPARK = [dict(b=(k * NC / NSPARK + _rng.random() * 1.5) % NC, life=int(_rng.integers(6, 11)),
              ex=CCX + _rng.uniform(4, 8), ey=CCY + _rng.uniform(-8, 3), vx=_rng.uniform(0.6, 1.1),
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
    mask = ok & (zf >= zb) & (zf < 1e8)
    sfac = n @ LIGHT
    lvl = np.digitize(sfac[fid], [-0.05, 0.3, 0.58, 0.82])                    # 0..4
    pb = np.stack([x, y, np.where(mask, zf, 0)], -1) @ Rm                   # surface point in body space
    cell = np.floor(pb / 2.3).astype(np.int64)
    hsh = ((cell[..., 0] * 73856093) ^ (cell[..., 1] * 19349663) ^ (cell[..., 2] * 83492791)) % 100
    lvl = np.clip(lvl - (hsh < 17), 0, 4)                                   # pits that ride with the surface
    idx = np.where(mask, np.array(COAL)[lvl], 0)
    hotpulse = 0.5 + 0.5 * math.sin(2 * w + 1.0)
    hf = mask & (fid == HOTFACE)
    idx[hf] = np.where(hsh[hf] < 17, 15, 9 if hotpulse > 0.6 else 8)
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
        gl = both & ~isc                                                    # plain facet edge: a glint on lit facets
        lv = lvl[:H - sy, :W - sx]
        iv = idx[:H - sy, :W - sx]
        up = gl & (lv >= 2) & (iv != 8) & (iv != 9)
        iv[up] = np.array(COAL)[np.clip(lv + 1, 0, 5)][up]
    p = 0.5 + 0.5 * np.sin(2 * w + cph)                                     # every crack breathes twice per loop
    spill = dilate(crack & (p > 0.55)) & mask & ~crack & (lvl <= 1)
    idx[spill] = 8
    idx[crack] = np.array(HOTC)[np.minimum(4, (p * 4.3 + 0.35).astype(int))][crack]
    outline(idx, 1)
    solid = idx > 0
    glow = 0.5 + 0.5 * math.sin(2 * w)
    hotc = crack & (p > 0.45)                                               # soft glow where a hot crack meets the rim
    near = dilate(dilate(dilate(hotc)))
    r1 = dilate(solid) & ~solid & near                                      # dither allowed here: glow is soft
    r2 = dilate(solid | r1) & ~solid & ~r1 & dilate(near)
    idx[r1 & ((X + Y) % 2 == 0)] = 9
    idx[r2 & ((X + Y) % 2 == 0) & (glow > 0.3)] = 8
    free = ~solid
    for sp in SPARK:                                                        # sparks shed into the wake, rising
        age = (f - sp['b']) % NC
        if age >= sp['life']:
            continue
        def pos(a):
            return (sp['ex'] + sp['vx'] * a + 0.5 * math.sin(1.1 * a + sp['ph']),
                    sp['ey'] + sp['vy'] * a * (1 - 0.03 * a))
        t = age / sp['life']
        ci = min(4, int(t * 5))
        heat = [13, 12, 11, 10, 9]
        for back, drop in ((2, 2), (1, 1)):
            if age - back >= 0 and ci + drop <= 4 and t < 0.7:
                bx, by = pos(age - back)
                put(idx, round(bx), round(by), heat[ci + drop], only=free)
        sx, sy = pos(age)
        put(idx, round(sx), round(sy), heat[ci], only=free)
    return idx, mask


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


def main():
    preview = '--preview' in sys.argv
    fa, ma = zip(*[squall_frame(f) for f in range(NA)])
    fb = [vent_frame(f) for f in range(NB)]
    fc, mc = zip(*[coal_frame(f) for f in range(NC)])
    ca = bbox(np.any(ma, 0))
    cc = bbox(np.any(mc, 0))
    kinds = [
        dict(key='a', name='Skip-rope squall', frames=list(fa), pal=PAL_STORM, palname='storm', ticks=TA,
             hit=(ca[0] + 4, ca[1] + 4, ca[2] - 4, ca[3] - 2),
             hitnote='the cloud body, 4 px inside its edge; the arc below the base and the pin sparks do not hurt'),
        dict(key='b', name='Flue spinner', frames=fb, pal=PAL_HOT, palname='hot_metal', ticks=TB,
             hit=(8, 5, 24, 21), hitnote='the globe, 1 px inside its steel; fins, collar and chain do not hurt'),
        dict(key='c', name='Cinder', frames=list(fc), pal=PAL_HOT, palname='hot_metal', ticks=TC,
             hit=(cc[0] + 2, cc[1] + 2, cc[2] - 2, cc[3] - 2),
             hitnote='the coal, 2 px inside its widest tumble; glow and sparks do not hurt'),
    ]
    out = ['Gum Trip moving hazards, final draft sheets. Measured by draw_moving_hazard_final.py from the sheets it wrote.',
           'Tiles are 16 x 16. Raw = non-empty tiles over all frames; unique = distinct after removing exact duplicates;',
           'with flips = distinct when horizontal and vertical mirror copies also count as duplicates.',
           'Loop seam = pixels that differ between the last frame and frame 0, beside the same count for the other',
           'neighbouring frame pairs (mean and largest). A seam inside that range means no pop.', '']
    total_u = total_f = 0
    summary = []
    for kd in kinds:
        fr, pal = kd['frames'], kd['pal']
        h, w = fr[0].shape
        n = len(fr)
        used = sorted(set(int(v) for f_ in fr for v in np.unique(f_)) - {0})
        assert max(used) <= 15 and len(pal) == 15
        im = sheet(fr, pal)
        assert im.width % 16 == 0 and im.height % 16 == 0
        im.save(os.path.join(HERE, f"sheet_{kd['key']}_1x.png"), optimize=True)
        raw, uq, fl = tiles(fr)
        total_u += uq
        total_f += fl
        sm = seam(fr)
        ob = bbox(np.any(np.stack(fr) > 0, 0))
        x0, y0, x1, y1 = kd['hit']
        ms = round(kd['ticks'] * 1000 / 60 / 10) * 10
        gif = [on_bg(f_, pal, GIF_BG, 3) for f_ in fr]
        gif[0].save(os.path.join(HERE, f"anim_{kd['key']}_3x.gif"), save_all=True, append_images=gif[1:],
                    duration=ms, loop=0, optimize=True)
        js = {
            'source': 'thoughts/shared/drafts/2026-11-10-gum-trip-moving-hazard-final/draw_moving_hazard_final.py '
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
        kd.update(w=w, h=h, n=n, uq=uq)
        out += [kd['name'],
                f"Frame size {w} x {h} px, {n} frames in one row (sheet {im.width} x {im.height}), {kd['ticks']} ticks per frame "
                f"({60 / kd['ticks']:.0f} per second), loop {n * kd['ticks']} ticks = {n * kd['ticks'] / 60:.2f} s",
                f"Palette \"{kd['palname']}\": {len(used)} of 15 colours used in this sheet (indices {used[0]}..{used[-1]}), plus transparent",
                f"Sprite columns {w // 16} (16 px wide), {h // 16} tiles tall",
                f"Tiles raw {raw}, unique {uq}, unique with flips {fl}",
                f"Opaque bounding box over all frames x {ob[0]}..{ob[2]}, y {ob[1]}..{ob[3]}",
                f"Hit box x {x0}..{x1}, y {y0}..{y1} ({x1 - x0 + 1} x {y1 - y0 + 1}), relative to the frame: {kd['hitnote']}",
                f"Loop seam {sm[0]} px; other neighbouring frames mean {sm[1]:.0f} px, largest {sm[2]} px",
                f"Gif frame time {ms} ms (game {kd['ticks'] * 1000 / 60:.1f} ms; gif timing has 10 ms steps)"]
        summary.append(f"{kd['key'].upper()}: {n} frames, {len(used)} colours, tiles {raw}/{uq}/{fl}, seam {sm[0]} vs mean {sm[1]:.0f} max {sm[2]}")
        if kd['key'] == 'a':
            br = [int(np.isin(f_, (12, 13)).sum()) for f_ in fr]                 # pale cyan and white
            op = [int((f_ > 0).sum()) for f_ in fr]
            others = max(v for i, v in enumerate(br) if i != FS)
            out += [f"Flash: one strike per loop, at frame {FS}, shown for {TA} ticks ({TA * 1000 / 60:.0f} ms). "
                    f"One loop is {NA * TA} ticks, so {60 / (NA * TA):.3f} flashes per second per cloud (limit asked: under 3).",
                    f"Flash size: {br[FS]} pale-cyan or white pixels in the strike frame = {100 * br[FS] / (w * h):.1f} % of the "
                    f"48 x 48 frame, {100 * br[FS] / op[FS]:.1f} % of its opaque pixels. No other frame has more than {others}. "
                    f"The frame before has {br[FS - 1]}, the frame after {br[FS + 1]}: never two bright frames in a row.",
                    f"Charge: frames 4..{FS - 1} build ({(FS - 4) * TA} ticks), frame {FS} strikes, frames {FS + 1}..{FS + 3} "
                    f"fade, frames {FS + 4}..{NA - 1} and 0..3 rest.",
                    'Several clouds on screen: start them at the same loop phase or at phases at least 8 frames (32 ticks) '
                    'apart, so that strikes of different clouds never land on consecutive frames. With 2 clouds that is at '
                    f"most {2 * 60 / (NA * TA):.2f} flashes per second."]
            summary.append(f"   flash bright px {br[FS]} ({100 * br[FS] / (w * h):.1f}% of frame), neighbours {br[FS - 1]}/{br[FS + 1]}, max other {others}")
        if kd['key'] == 'b':
            out += ['No flash: the slots glow steadily; brightness moves with the vanes only.',
                    f"Spin: {KP} vane pitches per loop ({NV} vanes), so the globe art repeats after {NB // KP} frames; the rocking "
                    'body and the chain repeat after 16.']
        if kd['key'] == 'c':
            pk = [int(np.isin(f_, (12, 13)).sum()) for f_ in fr]
            out += [f"No flash: ember cracks breathe twice per loop ({2 * 60 / (NC * TC):.2f} per second), each crack with its own "
                    f"phase; yellow or pale-yellow pixels per frame {min(pk)}..{max(pk)} of 1024 ({100 * max(pk) / 1024:.1f} % at most)."]
        out.append('')
        if preview:
            cols = 8
            rows = (n + cols - 1) // cols
            cs = Image.new('RGB', (cols * w * 4, rows * h * 4), GIF_BG)
            for i, f_ in enumerate(fr):
                cs.paste(on_bg(f_, pal, GIF_BG, 4), ((i % cols) * w * 4, (i // cols) * h * 4))
            cs.save(os.path.join(HERE, f"preview_{kd['key']}.png"))
    out += [f"Total unique tiles for the three kinds: {' + '.join(str(k['uq']) for k in kinds)} = {total_u} "
            f"(with flips {total_f}). First drafts: 139 + 96 + 64 = 299.",
            'Palettes: 2 for the three kinds. "storm" (A) and "hot_metal" (B and C). RGB after 5-bit rounding:',
            '  storm     ' + ' '.join('%d,%d,%d' % c for c in PAL_STORM),
            '  hot_metal ' + ' '.join('%d,%d,%d' % c for c in PAL_HOT),
            'Mood colours in on_moods_2x.png: ' + ', '.join(f"{m} {c}" for m, c in MOODS) +
            ' = most common colour of the middle band of plane_<mood>_sky_1x.png in ../2026-11-10-backgrounds-final/.',
            f"Gif background {GIF_BG}."]
    with open(os.path.join(HERE, 'numbers.txt'), 'w') as fh:
        fh.write('\n'.join(out) + '\n')
    # one frame of each kind on the three flat sky colours
    pick = [(fa[FS - 2], PAL_STORM), (fb[3], PAL_HOT), (fc[5], PAL_HOT)]
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
        im = Image.fromarray(canvas, 'RGB').resize((pw * 2, ph_ * 2), Image.NEAREST)
        moods.paste(im, (0, mi * ph_ * 2))
    moods.save(os.path.join(HERE, 'on_moods_2x.png'), optimize=True)
    write_html(kinds, out)
    print('\n'.join(summary))
    print('total unique', total_u, 'with flips', total_f)
    for nm, pal in (('storm', PAL_STORM), ('hot_metal', PAL_HOT)):
        print('palette', nm, len(pal), 'colours,', len(set(pal)), 'distinct')
    for kd in kinds:
        im = Image.open(os.path.join(HERE, f"sheet_{kd['key']}_1x.png"))
        cols_ = set(c[:3] for c in im.convert('RGBA').get_flattened_data() if c[3]) if hasattr(im, 'get_flattened_data') \
            else set(c[:3] for c in im.convert('RGBA').getdata() if c[3])
        print('sheet', kd['key'], im.size, 'opaque colours read back from the PNG:', len(cols_),
              'all in palette:', cols_ <= set(kd['pal']), 'hit', kd['hit'])


def write_html(kinds, numbers):
    old = '../2026-11-10-gum-trip-moving-hazard'
    desc = {'a': 'Storm cloud. Billows overturn, the belly charges blue, the rope strikes once per loop under the base.',
            'b': 'Turbine roof vent. Helical vanes turn, furnace slots glow, the chain swings below with lag.',
            'c': 'Tumbling coal. Facets keep their place, ember cracks breathe, sparks trail into the wake.'}
    rows = []
    for kd in kinds:
        k = kd['key']
        sw, sh = kd['w'] * kd['n'] * 2, kd['h'] * 2
        rows.append(f"""<section>
<h2>{kd['name']}</h2>
<p>{desc[k]}</p>
<div class="pair">
<figure><img src="anim_{k}_3x.gif" width="{kd['w'] * 3}" height="{kd['h'] * 3}" alt="{kd['name']}, final, animated"><figcaption>Final, game timing, three times size</figcaption></figure>
<figure><img src="{old}/anim_{k}_3x.gif" alt="{kd['name']}, first draft, animated" height="{kd['h'] * 3}"><figcaption>First draft animation</figcaption></figure>
</div>
<figure class="strip"><img class="px" src="{old}/sheet_{k}_1x.png" height="{sh}" alt="{kd['name']}, first draft sheet"><figcaption>First draft sheet, 16 frames, two times size</figcaption></figure>
<figure class="strip"><img class="px" src="sheet_{k}_1x.png" width="{sw}" height="{sh}" alt="{kd['name']}, final sheet"><figcaption>Final sheet, {kd['n']} frames, two times size</figcaption></figure>
</section>""")
    num = []
    for line in numbers:
        if not line:
            num.append('<p class="gap"></p>')
        elif line in [k['name'] for k in kinds]:
            num.append(f'<h3>{line}</h3>')
        else:
            num.append(f'<p>{line}</p>')
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Gum Trip moving hazards: final sheets</title>
<style>
body {{ background: #14171c; color: #d9dde3; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  margin: 0; padding: 24px 32px 64px; line-height: 1.45; }}
h1 {{ font-size: 24px; margin: 0 0 4px; }}
h2 {{ font-size: 19px; margin: 0 0 4px; color: #ffd27a; }}
h3 {{ font-size: 15px; margin: 14px 0 2px; color: #ffd27a; }}
section {{ border-top: 1px solid #2c323b; padding: 20px 0; }}
p {{ margin: 2px 0; max-width: 1000px; }}
p.gap {{ height: 6px; }}
.pair {{ display: flex; gap: 24px; flex-wrap: wrap; margin: 12px 0; }}
figure {{ margin: 0; }}
figure.strip {{ overflow-x: auto; margin: 12px 0; padding-bottom: 6px; }}
figure.strip img {{ background: #586880; display: block; }}
figcaption {{ font-size: 13px; color: #98a1ad; margin-top: 4px; }}
img {{ image-rendering: pixelated; }}
.numbers p {{ font-size: 14px; }}
</style></head><body>
<h1>Gum Trip moving hazards: final sheets</h1>
<p>Three hazards, two palettes. First drafts beside the final pass. Nothing here is wired into the game.</p>
{''.join(rows)}
<section><h2>On the three sky moods</h2>
<p>One frame of each kind on a flat sky colour: dusk, moon, storm (top to bottom), two times size.</p>
<figure><img src="on_moods_2x.png" alt="The three hazards on dusk, moon and storm sky colours"></figure></section>
<section class="numbers"><h2>Numbers</h2>
{''.join(num)}
</section>
</body></html>
"""
    with open(os.path.join(HERE, 'index.html'), 'w') as fh:
        fh.write(html)


if __name__ == '__main__':
    main()
