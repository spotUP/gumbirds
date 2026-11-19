#!/usr/bin/env python3
# Gumbirds, Gum Trip: DRAFT art for the floor and ceiling kill strips (nothing in the build reads this).
# The window between a ceiling band and a floor band changes height per 192 px course chunk, in 16 px steps.
# Touching a band costs gum, so the rim must read as dangerous; the fill runs from the rim to the screen edge.
#
#   A  Shard ridge   static     crimson glass shards on plum rock, lit from the upper left, ceiling REDRAWN
#   B  Live rail     8 frames   steel conduit with emitter studs, a lime arc crawling stud to stud, ceiling = V flip
#   C  Boiling gum   8 frames   hot gum melt, a damped wave surface driven by bubble pops, ceiling = V flip
#
# How it is built: one painter per variant colours a whole course (3 chunks, 576 x 224) as a pure function of
# (position along the edge, depth from the edge, edge direction, frame) plus a hand-drawn fill tile. The course is
# then cut into 16 x 16 tiles and deduplicated (horizontal and vertical flips count as the same tile, as the LSPC
# can flip any tile). The mock-ups are rebuilt FROM THAT TILE SET and checked pixel-equal to the painted course.
# Hurt line = window edge exactly: every opaque pixel lies inside the band mask (0 px into the window).
#
# Run: /opt/homebrew/bin/python3.14 -I draw_kill_strip.py
import os
import sys
sys.dont_write_bytecode = True
import math
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
H = 224
CH = 192                                   # course chunk width
CHUNKS = [(3, 11), (4, 9), (2, 10)]        # (ceiling: first window tile row, floor: first band tile row) per chunk
SKY = (22, 20, 40)                         # plain dark sky tone for the mock-ups
CAM = 32                                   # mock-up camera: chunk join 192 lands at screen x 160
L = np.array([-0.66, -0.75]); L = L / np.hypot(*L)   # toward the light (upper left), screen x, y
NF = 8                                     # frames per animated loop (one LSPC auto-animation group)


def q5(c):
    return tuple(((v >> 3) << 3) | (v >> 5) for v in c)


def hx(s):
    return q5(tuple(int(s[i:i + 2], 16) for i in (0, 2, 4)))


def luma(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


# ---------------------------------------------------------------- palettes (index 0 = transparent)
PAL = {
    'A': [None] + [hx(s) for s in [
        '0e0612',  # 1 outline, darkest
        '1e0e24',  # 2 rock deep (fill base)
        '4a2450',  # 3 rock cluster (dither pair with 2)
        '7e4470',  # 4 rock lit
        'b8709a',  # 5 crust rim light
        '3a1a5c',  # 6 back shard shade (violet, hue shift)
        '7a48b0',  # 7 back shard lit
        '4e0820',  # 8 shard deepest
        '920e30',  # 9 shard shade
        'd6243a',  # 10 shard mid
        'ff5a48',  # 11 shard lit (warm)
        'ffa070',  # 12 ridge
        'fff0dc',  # 13 glint
        '2a1030',  # 14 crust shadow
        '5a1838',  # 15 crust deep red plum
    ]],
    'B': [None] + [hx(s) for s in [
        '0a0c14',  # 1 outline, seams
        '1a2232',  # 2 steel deep, plate base
        '34405a',  # 3 steel dark
        '5e708c',  # 4 steel mid
        'a0b4c8',  # 5 steel light
        'eef4fa',  # 6 steel highlight
        '6a3c0c',  # 7 amber dark
        'f0a818',  # 8 amber
        '0e3a34',  # 9 glow deep teal
        '2c8a4a',  # 10 glow green
        '8cf03c',  # 11 arc lime
        'f0ffc0',  # 12 arc core
        '242c40',  # 13 plate shade
        '4a2a6a',  # 14 arc violet fringe
        '3a1c10',  # 15 amber shade
    ]],
    'C': [None] + [hx(s) for s in [
        '1c0626',  # 1 darkest violet
        '3a0a3c',  # 2 deep gum (fill base)
        '701a68',  # 3 gum dark
        'b02a7c',  # 4 gum mid
        'e8488e',  # 5 gum
        'ff8a9a',  # 6 gum light (warm)
        'ffd0c0',  # 7 peach surface light
        'fff6f0',  # 8 glint
        '4a1a7a',  # 9 bubble ring shade (violet)
        'ffb050',  # 10 hot glint
    ]],
}
NAMES = {'A': 'Shard ridge', 'B': 'Live rail', 'C': 'Boiling gum'}
FRAMES = {'A': 1, 'B': NF, 'C': NF}
TICKS = {'A': 0, 'B': 4, 'C': 5}
CEILING = {'A': 'redrawn (painted with the same light from the upper left; shards hang, crust underside dark)',
           'B': 'vertical flip of the floor tiles (no extra tiles; steel lit from below on the ceiling)',
           'C': 'vertical flip of the floor tiles (no extra tiles; bubbles bulge downward like forming drips)'}
DITHER = {'A': [(2, 3), (3, 4)], 'B': [(10, 0)], 'C': [(6, 5), (5, 4), (4, 3), (3, 2), (3, 4)]}

# ---------------------------------------------------------------- hand-drawn fill tiles (16 x 16, wrap vertically)
# chars map to palette indices; 'x' / 'y' / 'z' are hand-placed checker dither between two indices.
FILL_SRC = {
    'A': ("0000000000000000",
          "000xx11x00000000",
          "00x1122110000x00",
          "0x11222110000xx0",
          "0x1111111o0000x0",
          "00x11111oo000000",
          "000xooo000000000",
          "0000000000x1x000",
          "x0000000x1121x00",
          "1x00000x1122110x",
          "1x00000x111111o0",
          "x000000oo1111oo0",
          "00000000ooooo000",
          "0000x00000000000",
          "000x1x0000000000",
          "0000x00000000000"),
    'B': ("111111111111111o",
          "000000000000000o",
          "020000000000000o",
          "000000000000000o",
          "000000000000000o",
          "00o1o1o1o1o1o00o",
          "00o1o1o1o1o1o00o",
          "00o1o1o1o1o1o00o",
          "00o1o1o1o1o1o00o",
          "000000000000000o",
          "000000000000000o",
          "ssssssssssssssso",
          "000000000000000o",
          "020000000000000o",
          "ssssssssssssssso",
          "oooooooooooooooo"),
    'C': ("0000000000000000",
          "00000x0000000000",
          "0000x1x000000000",
          "00000x0000000xx0",
          "000000000000x11x",
          "x0000000000x1dd1",
          "1x00000000x1d00z",
          "x0000000000x1dd1",
          "000000000000x11x",
          "0000000000000xx0",
          "00xx000000000000",
          "0x11x00000000000",
          "0x1d1x0000000x00",
          "00x11x000000x1x0",
          "000xx00000000x00",
          "0000000000000000"),
}
FILL_MAP = {'A': {'0': 2, '1': 3, '2': 4, 'o': 1, 'x': (2, 3)},
            'B': {'0': 2, '1': 4, '2': 5, 'o': 1, 's': 13},
            'C': {'0': 2, '1': 3, 'd': 1, 'x': (2, 3), 'z': (3, 4)}}


def fill_tile(v):
    rows = FILL_SRC[v]
    assert len(rows) == 16 and all(len(r) == 16 for r in rows), v
    t = np.zeros((16, 16), np.uint8)
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            m = FILL_MAP[v][ch]
            t[y, x] = m if isinstance(m, int) else m[(x + y) % 2]
    return t


# ---------------------------------------------------------------- course geometry
def geometry(chunks):
    W = len(chunks) * CH
    cb = np.repeat([c[0] for c in chunks], CH // 16)
    ft = np.repeat([c[1] for c in chunks], CH // 16)
    Y, X = np.mgrid[0:H, 0:W]
    col = X // 16
    ceil = Y < 16 * cb[col]
    floor = Y >= 16 * ft[col]
    band = ceil | floor
    win = ~band

    def dist(dy, dx):
        d = np.full((H, W), 99, np.int32)
        for k in range(1, 18):
            ys, xs = Y + k * dy, X + k * dx
            ok = (ys >= 0) & (ys < H) & (xs >= 0) & (xs < W)
            s = np.zeros((H, W), bool)
            s[ok] = win[ys[ok], xs[ok]]
            d = np.where(s & (d == 99), k - 1, d)
        return d
    Ds = np.stack([dist(-1, 0), dist(1, 0), dist(0, -1), dist(0, 1)])   # window above, below, left, right
    DIR = np.argmin(Ds, 0)                                              # ties prefer the horizontal edge
    D = np.min(Ds, 0)
    corners = []                                                        # outer corners: (x, y, sx, sy) into band
    for c in range(1, len(ft)):
        if ft[c] < ft[c - 1]: corners.append((16 * c, 16 * ft[c], 1, 1))
        if ft[c] > ft[c - 1]: corners.append((16 * c - 1, 16 * ft[c - 1], -1, 1))
        if cb[c] > cb[c - 1]: corners.append((16 * c, 16 * cb[c] - 1, 1, -1))
        if cb[c] < cb[c - 1]: corners.append((16 * c - 1, 16 * cb[c - 1] - 1, -1, -1))
    xm = X % 32
    xm = np.where(xm < 16, xm, 31 - xm)                                 # fill mirrors every 16 px (F, flip F)
    t = np.where(ceil, 15 - Y % 16, Y % 16)                             # fill depth row, ceiling mirrored
    u64 = X % 64
    m = np.where(u64 < 32, u64, 63 - u64)                               # mirrored edge coordinate (B, C)
    return dict(W=W, X=X, Y=Y, band=band, ceil=ceil, D=D, DIR=DIR, rim=band & (D < 16), corners=corners,
                xm=xm, t=t, m=m, cb=cb, ft=ft)


def base_fill(G, v):
    return fill_tile(v)[G['t'], G['xm']]


def world_normal(nu, nd, DIR):
    # (u, d) frame normal -> screen normal per edge direction (0 up, 1 down, 2 left, 3 right)
    nx = np.select([DIR == 0, DIR == 1, DIR == 2, DIR == 3], [nu, nu, nd, -nd])
    ny = np.select([DIR == 0, DIR == 1, DIR == 2, DIR == 3], [nd, -nd, nu, nu])
    n = np.hypot(nx, ny) + 1e-9
    return (nx * L[0] + ny * L[1]) / n


# ---------------------------------------------------------------- A: shard ridge (static, natively lit)
A_CRUST = [5, 5, 4, 4, 5, 5, 6, 6, 5, 5, 5, 4, 4, 4, 5, 6, 6, 5, 5, 4, 5, 5, 5, 6, 6, 6, 5, 5, 4, 4, 5, 5,
           5, 6, 5, 5, 4, 4, 4, 5, 5, 6, 6, 5, 5, 5, 4, 5, 5, 5, 6, 6, 5, 4, 4, 5, 5, 5, 6, 5, 5, 4, 5, 5]
A_FRONT = [(5, 3.0, 1, -1.0), (12, 2.0, 2, 1.0), (19.5, 3.0, 0, 0.0), (27, 2.0, 1, -1.0), (33.5, 3.0, 1, 1.0),
           (41, 2.0, 2, 0.0), (47.5, 3.0, 0, -1.0), (55, 2.5, 1, 1.0), (60.5, 1.5, 2, 0.0)]
A_BACK = [(8.5, 2.0, 1, 0.0), (23.5, 2.0, 2, 1.0), (37.5, 2.0, 1, -1.0), (51, 2.0, 2, 0.0)]
F_CRUST = [5, 5, 4, 4, 5, 5, 5, 4, 4, 5, 5, 4, 4, 5, 5, 5]
F_FRONT = [(4.5, 2.5, 1, 0.0), (11, 2.5, 0, 1.0)]
F_BACK = [(8, 1.5, 1, 0.0)]


def paint_A(G, f):
    DIR, D, X, Y = G['DIR'], G['D'], G['X'], G['Y']
    horiz = DIR < 2
    P = np.where(horiz, 64, 16)
    u = np.where(horiz, X % 64, Y % 16) + 0.5
    d = D + 0.5
    crust = np.where(horiz, np.array(A_CRUST)[X % 64], np.array(F_CRUST)[Y % 16]) - 2   # crust top 2-4 px under the hurt line
    out = base_fill(G, 'A').copy()
    rim = G['rim']
    # crust: surface row, lit or dark by facing; deep rows dark with sparse rock dither
    face = world_normal(np.zeros(D.shape), -np.ones(D.shape), DIR)
    e = D - crust
    par = (X + Y) % 2
    cr = np.select([e == 0, e == 1, e == 2, e == 3, e == 4, e == 5],
                   [np.where(face > 0.3, 5, np.where(face > -0.3, 15, 14)),
                    np.where(face > 0.3, 4, np.where(face > -0.3, 3, 15)),
                    np.where(face > 0.3, np.where(par, 3, 4), 15),
                    np.where(par, 2, 3), 14, 2], out)
    out = np.where(rim & (e >= 0), cr, out)
    out = np.where(rim & (e < 0), 0, out)
    shard = np.zeros(D.shape, bool)
    for tables, back in (((A_BACK, F_BACK), True), ((A_FRONT, F_FRONT), False)):
        for horiz_tab, Pt in ((tables[0], 64), (tables[1], 16)):
            sel = rim & (P == Pt)
            for (uc, w, tip, lean) in horiz_tab:
                hb = crust + 4.0
                fr = (d - tip) / np.maximum(hb - tip, 1)
                cen = uc + lean * (1 - fr)
                du = ((u - cen + Pt / 2) % Pt) - Pt / 2
                hw = w * fr
                inside = sel & (fr >= 0) & (fr <= 1) & (np.abs(du) <= hw + 0.35)
                k = w / max(float(np.mean(hb)) - tip, 1)
                nu = np.where(du < 0, -1.0, 1.0)
                lum = world_normal(nu, -k * np.ones(D.shape), DIR)
                if back:
                    col = np.where(lum > 0.2, 7, 6)
                else:
                    col = np.select([lum > 0.6, lum > 0.1, lum > -0.4], [11, 10, 9], 8)
                    col = np.where((lum > 0.6) & (np.abs(du) >= hw - 0.6) & (fr < 0.55), 13, col)
                    col = np.where((np.abs(du) < 0.5) & (lum > -0.1 * 0) & (fr < 0.8),
                                   np.where(world_normal(np.zeros(D.shape), -np.ones(D.shape), DIR) > 0, 12, 10), col)
                    col = np.where((fr > 0.82) & (col >= 9), col - 1, col)
                    shard |= inside
                out = np.where(inside, col, out)
    # outline: transparent band pixels touching a shard (stays inside the band, 0 px into the window)
    op = out > 0
    nb = np.zeros(D.shape, bool)
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nb |= np.roll(np.roll(shard, dy, 0), dx, 1)
    out = np.where(rim & ~op & nb, 1, out)
    return out


# ---------------------------------------------------------------- B: live rail (arc = forced damped string)
def string_loop(seed, n=16, amp=1.9):
    rng = np.random.default_rng(seed)
    N = n + 2
    xs = np.arange(N) / (N - 1)
    modes = [(np.sin(np.pi * j * xs), rng.uniform(0.6, 1.4) / j, int(rng.integers(1, 4)), rng.uniform(0, 2 * np.pi))
             for j in range(1, 5)]
    sub, c2, gam = 40, 14.0, 1.6
    dt = 1.0 / sub
    y = np.zeros(N); v = np.zeros(N)
    rec = []
    for loop in range(30):
        for fr in range(NF):
            if loop == 29: rec.append(y.copy())
            for s in range(sub):
                tt = (fr + s * dt) / NF
                force = sum(a * sh * np.sin(2 * np.pi * q * tt + ph) for sh, a, q, ph in modes) * 30
                lap = np.zeros(N); lap[1:-1] = y[:-2] + y[2:] - 2 * y[1:-1]
                v += (c2 * lap * (N - 1) ** 2 / 50 - gam * v + force) * dt
                v[0] = v[-1] = 0
                y += v * dt
                y[0] = y[-1] = 0
    seam = float(np.abs(y - rec[0]).max())                 # state after the loop vs its start: periodic steady state
    rec = np.array(rec)
    jit = rng.normal(0, 0.45, rec.shape); jit[:, 0] = jit[:, -1] = 0
    rec = rec + jit                                        # per-frame crackle (independent per frame, loops cleanly)
    rec = rec / (np.abs(rec).max() + 1e-9) * amp
    return rec, seam


ARC = {}
ARC_SEAM = []


def arc_stencils():
    st = np.zeros((3, NF, 6, 16), np.uint8)               # arc id (top 0, top 1, face), frame, depth 0..5, s
    for a in range(3):
        rec, seam = string_loop(11 + 7 * a)
        ARC_SEAM.append(seam)
        for f in range(NF):
            dd = 2.5 + rec[f]
            pts = [int(round(min(max(dd[s + 1], 0.0), 4.4))) for s in range(16)]
            for s in range(16):
                lo = min(pts[s], pts[s - 1] if s else pts[s]); hi = max(pts[s], pts[s - 1] if s else pts[s])
                for dz in range(lo, hi + 1):
                    st[a, f, dz, s] = 3
            core = st[a, f] == 3
            for s in range(16):
                for dz in range(6):
                    if core[dz, s]: continue
                    near1 = any(core[z, s] for z in (dz - 1, dz + 1) if 0 <= z < 6)
                    near2 = any(core[z, s] for z in (dz - 2, dz + 2) if 0 <= z < 6)
                    if near1: st[a, f, dz, s] = 2
                    elif near2 and (s + dz + f) % 2 == 0: st[a, f, dz, s] = 1
            # forked spark: one short branch toward the window per frame, position from a hand table
            fs = [3, 11, 6, 13, 2, 9, 5, 12][(f + 3 * a) % NF]
            bz = pts[fs]
            if bz >= 2:
                st[a, f, bz - 1, fs + (1 if fs < 8 else -1)] = 3
                st[a, f, max(bz - 2, 0), fs + (2 if fs < 8 else -2)] = 2
    return st


def paint_B(G, f):
    if 'st' not in ARC: ARC['st'] = arc_stencils()
    st = ARC['st']
    DIR, D, X, Y = G['DIR'], G['D'], G['X'], G['Y']
    horiz = DIR < 2
    m = G['m']
    s = np.where(horiz, m % 16, Y % 16)
    a = np.where(horiz, m // 16, 2)
    out = base_fill(G, 'B').copy()
    rim = G['rim']
    fa = np.where(horiz, f, f % 4)                          # face arc: 4-frame loop (LSPC 2-bit auto-animation)
    arcv = st[a, fa, np.clip(D, 0, 5), s]
    # nearest arc depth per column, for the cast light on the rail top
    arcdeep = np.zeros(D.shape, bool)
    for dz in (3, 4, 5):
        arcdeep |= st[a, fa, dz, s] == 3
    stud = (s == 0) | (s == 15)
    flare = (s == 1) | (s == 14)
    chev = (s >= 3) & (s <= 12) & (D >= 8) & (D <= 10)
    stripe = ((s - D) // 2) % 2 == 0
    rail = np.select([D == 6, D == 7, chev & stripe, chev, D == 8, D == 9, D == 10, D == 11, D == 12, D == 13],
                     [np.where(arcdeep, 11, 6), 5, 8, 7, 4, 4, 3, 3, 1, 1], out)
    top = np.select([stud & (D == 3), stud & (D == 4), (stud | flare) & (D == 5)], [6, 5, 4], 0)
    top = np.where((top == 0) & (arcv == 3), 12, top)
    top = np.where((top == 0) & (arcv == 2), 11, top)
    top = np.where((top == 0) & (arcv == 1), 10, top)
    top = np.where((top == 0) & flare & (D == 4), 9, top)
    val = np.where(D >= 6, rail, top)
    out = np.where(rim, val, out)
    # corner post at each outer corner: emitter block 5 x 5 inside the band
    for (cx, cy, sx, sy) in G['corners']:
        ix = (X - cx) * sx; iy = (Y - cy) * sy
        blk = (ix >= 0) & (iy >= 0) & (ix <= 4) & (iy <= 4)
        mx = np.maximum(ix, iy); mn = np.minimum(ix, iy)
        pv = np.select([mx == 4, (mx <= 1), (mn == 0), (mx == 2)], [1, 12, 6, 11], 4)
        out = np.where(blk & G['band'], pv, out)
    return out


# ---------------------------------------------------------------- C: boiling gum (damped wave surface + bubbles)
# bubble: (m0, radius at full dome, phase). Life 8 frames: rel 0..3 rising in the body, 4..6 dome, 7 pop.
C_BUB = [(6, 2.6, 0), (17, 3.2, 3), (26, 2.2, 5)]
C_FACE_BULGE = [0, 0, 0, 0.5, 1.2, 1.8, 2.1, 1.7, 1.1, 0.6, 0.25, 0, 0, 0, 0, 0]


def wave_loop(n=32):
    sub, c2, gam = 30, 9.0, 1.1
    dt = 1.0 / sub
    h = np.zeros(n); v = np.zeros(n)
    rec = []
    for loop in range(60):
        for fr in range(NF):
            if loop == 59: rec.append(h.copy())
            for (m0, r, ph) in C_BUB:
                rel = (fr - ph) % NF
                if rel == 7:                                       # pop: the dome collapses, surface drops
                    v[max(m0 - 1, 0):m0 + 2] -= 9.0
                if rel in (4, 5, 6):                               # dome lifts the film around it
                    v[max(m0 - 2, 0):m0 + 3] += 1.2
            for _ in range(sub):
                hp = np.concatenate([[h[0]], h, [h[-1]]])          # reflecting ends (mirror cell)
                lap = hp[:-2] + hp[2:] - 2 * h
                v += (c2 * lap - gam * v - 0.8 * h) * dt
                h += v * dt
    seam = float(np.abs(h - rec[0]).max())
    rec = np.array(rec)
    rec = rec / (np.abs(rec).max() + 1e-9) * 1.8
    return rec, seam


WAVE = {}


def gum_body(e, par, glint):
    return np.select([e < 0, e < 1, e < 2, e < 3, e < 5, e < 6, e < 8, e < 9, e < 10.5, e < 11.5, e < 12.5],
                     [0, np.where(glint, 8, 7), 6, np.where(par, 6, 5), 5, np.where(par, 5, 4), 4,
                      np.where(par, 4, 3), 3, np.where(par, 3, 2), 2], -1)


def paint_C(G, f):
    if 'h' not in WAVE: WAVE['h'], WAVE['seam'] = wave_loop()
    hh = WAVE['h'][f]
    DIR, D, X, Y = G['DIR'], G['D'], G['X'], G['Y']
    horiz = DIR < 2
    m = G['m']
    s = Y % 16
    ds_top = np.clip(2.0 - 0.8 * hh, 0.0, 4.0)              # surface rests 2 px under the hurt line
    peak = np.zeros(32, bool)
    peak[1:-1] = (ds_top[1:-1] <= ds_top[:-2]) & (ds_top[1:-1] <= ds_top[2:])
    bul = np.array(C_FACE_BULGE)
    ds_face = np.clip(2.0 - bul[(np.arange(16) - 4 * f) % 16], 0.0, 4.0)       # film falls 4 px per frame: 4-frame loop
    dsurf = np.where(horiz, ds_top[m], ds_face[s])
    along = np.where(horiz, m, s)
    par = (along + D) % 2
    e = (D - dsurf) / np.maximum(12.0 - dsurf, 1.0) * 12.0
    glint = np.where(horiz, peak[m], ((s - 4 * f) % 16 == 6))
    body = gum_body(e, par, glint)
    # face: flowing highlight dashes moving down 2 px per frame
    dash = (~horiz) & (e >= 1) & (e < 2.2) & (((s - 4 * f + 16) % 16) < 3)
    body = np.where(dash & (body > 0), 7, body)
    out = base_fill(G, 'C').copy()
    rim = G['rim']
    out = np.where(rim & (body >= 0), body, out)
    # bubbles in the melt (top and bottom edges only; the face carries the flow)
    for (m0, r, ph) in C_BUB:
        rel = (f - ph) % NF
        dm = m - m0
        if rel <= 3:                                               # rising bubble: hollow ring
            cz = 11.0 - rel * 2.2
            rr = np.hypot(dm, D + 0.5 - cz - 0.5)
            ring = horiz & rim & (rr <= 1.6) & (rr > 0.7)
            out = np.where(ring, np.where(D + 0.5 < cz + 0.2, 7, 9), out)
            out = np.where(horiz & rim & (rr <= 0.7), 3, out)
        elif rel <= 6:                                             # dome on the surface
            rad = r * (0.55 + 0.22 * (rel - 4))
            cz = ds_top[m0] + 0.6
            rr = np.hypot(dm + 0.0, D + 0.5 - cz)
            dome = horiz & rim & (rr <= rad) & (D + 0.5 <= cz + 0.5)
            col = np.where(rr > rad - 1.0, 6, np.where(par, 5, 4))
            col = np.where((rr > rad - 1.0) & (dm < 0) & (D + 0.5 < cz - rad * 0.4), 8, col)
            col = np.where((rr <= 1.0) & (rel == 6), 10, col)
            out = np.where(dome, col, out)
        else:                                                      # pop: spray droplets above the surface
            base = int(round(ds_top[m0]))
            for (ox, oz, c) in ((-3, -2, 7), (3, -2, 7), (-2, -3, 8), (2, -3, 6), (0, -4, 7)):
                z = base + oz
                if z >= 0:
                    hit = horiz & rim & (m == m0 + ox) & (D == z)
                    out = np.where(hit, c, out)
    return out


PAINT = {'A': paint_A, 'B': paint_B, 'C': paint_C}


# ---------------------------------------------------------------- tiles
def cut(frames, G):
    """frames: (F, H, W) index images -> unique tile set (flips merged) and map, rebuilt course."""
    F = frames.shape[0]
    rows, cols = H // 16, G['W'] // 16
    keys, tiles, tmap, first = {}, [], {}, []
    noflip = set()
    for r in range(rows):
        for c in range(cols):
            t = frames[:, 16 * r:16 * r + 16, 16 * c:16 * c + 16]
            if not t.any():
                continue
            noflip.add(t.tobytes())
            best = None
            for hf in (0, 1):
                for vf in (0, 1):
                    o = t[:, ::-1 if vf else 1, ::-1 if hf else 1]
                    b = o.tobytes()
                    if best is None or b < best[0]:
                        best = (b, hf, vf, o)
            b, hf, vf, o = best
            if b not in keys:
                keys[b] = len(tiles); tiles.append(np.ascontiguousarray(o)); first.append((r, c))
            tmap[(r, c)] = (keys[b], hf, vf)
    rebuilt = np.zeros_like(frames)
    for (r, c), (i, hf, vf) in tmap.items():
        o = tiles[i][:, ::-1 if vf else 1, ::-1 if hf else 1]
        rebuilt[:, 16 * r:16 * r + 16, 16 * c:16 * c + 16] = o
    return tiles, tmap, first, rebuilt, len(noflip)


def role(G, r, c):
    sl = (slice(16 * r, 16 * r + 16), slice(16 * c, 16 * c + 16))
    band, rim, DIR = G['band'][sl], G['rim'][sl], G['DIR'][sl]
    where = 'ceiling' if r < 7 else 'floor'
    if not rim.any():
        return where + ' fill'
    if (DIR[rim] >= 2).any():
        return where + ' step'
    hts = G['cb'] if where == 'ceiling' else G['ft']
    near = [hts[k] for k in (c - 1, c, c + 1) if 0 <= k < len(hts)]
    return where + (' rim' if len(set(near)) == 1 else ' step')


def to_rgb(idx, pal, bg=SKY):
    lut = np.array([bg] + [p for p in pal[1:]] + [bg] * (16 - len(pal)), np.uint8)
    return lut[idx]


def save_scaled(arr, path, k):
    Image.fromarray(arr).resize((arr.shape[1] * k, arr.shape[0] * k), Image.NEAREST).save(path, optimize=True)


def main():
    G = geometry(CHUNKS)
    win = ~G['band']
    report = ['Gum Trip kill strips (draft). Measured by draw_kill_strip.py from the painted course and the cut tile set.',
              'Course: 3 chunks of 192 px (576 x 224). Per chunk (ceiling first window row, floor first band row): '
              + ', '.join('(%d, %d)' % c for c in CHUNKS) + ' in 16 px tile rows.',
              'Joins: x 192: floor up 2 rows (32 px), ceiling down 1 row; x 384: ceiling up 2 rows, floor down 1 row.',
              'Unique tiles: 16 x 16, horizontal and vertical flips count as the same tile (LSPC tile flip bits).',
              'ROM tile cost: static tile 1; animated tile 8 (LSPC 3-bit auto-animation, 8 consecutive tiles) or 4 when it loops every 4 frames (2-bit auto-animation bit in the sprite tile map).',
              'Mock-up camera x %d (join 192 at screen x 160), sky tone #%02x%02x%02x.' % ((CAM,) + SKY), '']
    gallery = []
    for v in 'ABC':
        pal = PAL[v]
        F = FRAMES[v]
        frames = np.stack([PAINT[v](G, f) for f in range(F)]).astype(np.uint8)
        frames[:, win] = 0
        assert not frames[:, win].any()
        tiles, tmap, first, rebuilt, noflip = cut(frames, G)
        same = bool((rebuilt == frames).all())
        anim = [i for i, t in enumerate(tiles) if F > 1 and not all((t[k] == t[0]).all() for k in range(F))]
        anim4 = [i for i in anim if all((tiles[i][k] == tiles[i][k + 4]).all() for k in range(4))]
        cost = len(tiles) - len(anim) + NF * (len(anim) - len(anim4)) + 4 * len(anim4)
        roles = {}
        rl = {}
        for (r, c), (i, hf, vf) in tmap.items():
            rl.setdefault(i, set()).add(role(G, r, c).split()[1])
        for i in range(len(tiles)):
            k = 'rim' if 'rim' in rl[i] else ('fill' if 'fill' in rl[i] else 'step')
            roles.setdefault(k, [0, 0])
            roles[k][1 if i in anim else 0] += 1
        used = sorted(set(np.unique(frames)) - {0})
        # horizontal period: rim rows of the flat first chunk repeat every P px
        P = 64
        fr0 = frames[0]
        rows_f = slice(16 * CHUNKS[0][1], 16 * CHUNKS[0][1] + 16)
        rows_c = slice(16 * CHUNKS[0][0] - 16, 16 * CHUNKS[0][0])
        per = all((fr0[rs, 0:64] == fr0[rs, 64:128]).all() and (fr0[rs, 64:128] == fr0[rs, 128:192]).all()
                  for rs in (rows_f, rows_c))
        per32 = all((fr0[rs, 0:32] == fr0[rs, 32:64]).all() for rs in (rows_f, rows_c))
        rgbf = to_rgb(fr0, pal)

        def coldiff(rs, x):
            return int((np.abs(rgbf[rs, x].astype(int) - rgbf[rs, x + 1].astype(int)).sum(1) > 0).sum())
        seam = [coldiff(rs, 63) + coldiff(rs, 127) for rs in (rows_f, rows_c)]
        inner = [np.mean([coldiff(rs, x) * 2 for x in range(64) if x % 16 != 15]) for rs in (rows_f, rows_c)]
        tseam = [np.mean([coldiff(rs, x) * 2 for x in range(15, 64, 16)]) for rs in (rows_f, rows_c)]
        # animation loop seam
        if F > 1:
            dif = [int((frames[(k + 1) % F] != frames[k]).sum()) for k in range(F)]
            loopline = 'Loop seam (frame 7 -> 0) %d px changed; other neighbouring frames mean %.0f, largest %d.' % (
                dif[-1], np.mean(dif[:-1]), max(dif[:-1]))
        # dither pairs
        dpairs = []
        for (a_, b_) in DITHER[v]:
            ca = pal[a_]; cb_ = pal[b_] if b_ else SKY
            dpairs.append('%s/%s %.0f' % ('#%02x%02x%02x' % ca, '#%02x%02x%02x' % cb_ if b_ else 'sky', abs(luma(ca) - luma(cb_))))
        # images
        mock_idx = [rebuilt[k][:, CAM:CAM + 320] for k in range(F)]
        mock = to_rgb(mock_idx[0], pal)
        save_scaled(mock, os.path.join(HERE, 'mock_%s_1x.png' % v.lower()), 1)
        save_scaled(mock, os.path.join(HERE, 'mock_%s_2x.png' % v.lower()), 2)
        save_scaled(mock, os.path.join(HERE, 'mock_%s_3x.png' % v.lower()), 3)
        # sheet: unique tiles in a row, frames downwards, 1 px gaps, 4x copy
        n = len(tiles)
        sh = np.zeros((F * 17 + 1, n * 17 + 1), np.uint8)
        for i, t in enumerate(tiles):
            for k in range(F if i in anim else 1):
                sh[1 + 17 * k:17 + 17 * k, 1 + 17 * i:17 + 17 * i] = t[k]
        shr = to_rgb(sh, pal, bg=(60, 60, 72))
        save_scaled(shr, os.path.join(HERE, 'sheet_%s_1x.png' % v.lower()), 1)
        save_scaled(shr, os.path.join(HERE, 'sheet_%s_4x.png' % v.lower()), 4)
        # parts: flat rim 64 px x 2 periods, step up (floor x 192), step down (floor x 384), ceiling steps
        parts = [fr0[16 * CHUNKS[0][1] - 4:16 * CHUNKS[0][1] + 32, 0:128],
                 fr0[16 * 9 - 4:16 * 11 + 32, 192 - 48:192 + 48],
                 fr0[16 * 9 - 4:16 * 10 + 32, 384 - 48:384 + 48],
                 fr0[0:16 * 4 + 4, 192 - 48:192 + 48],
                 fr0[0:16 * 4 + 4, 384 - 48:384 + 48]]
        ph = max(p.shape[0] for p in parts)
        strip = np.zeros((ph, sum(p.shape[1] for p in parts) + 8 * (len(parts) - 1)), np.uint8)
        x = 0
        for p in parts:
            strip[:p.shape[0], x:x + p.shape[1]] = p; x += p.shape[1] + 8
        save_scaled(to_rgb(strip, pal), os.path.join(HERE, 'parts_%s_3x.png' % v.lower()), 3)
        gif = None
        if F > 1:
            ims = []
            for g in range(16):                                    # camera scrolls 4 px per frame = 1 px per tick
                k = g % F
                cx = CAM + 4 * g
                ims.append(Image.fromarray(to_rgb(rebuilt[k][:, cx:cx + 320], pal)).resize((960, 672), Image.NEAREST))
            gif = 'anim_%s_3x.gif' % v.lower()
            ms = int(round(TICKS[v] * 1000 / 60 / 10) * 10)
            ims[0].save(os.path.join(HERE, gif), save_all=True, append_images=ims[1:], duration=ms, loop=0, optimize=True)
        # numbers
        report.append('%s  %s' % (v, NAMES[v]))
        report.append('Palette: %d of 15 colours used, plus transparent: %s' % (
            len(used), ' '.join('%d=#%02x%02x%02x' % ((i,) + pal[i]) for i in used)))
        report.append('Unique tiles (flips merged) %d: %d static + %d animated (%d of them 4-frame); ROM tile cost %d. '
                      'Without flip merging %d.' % (n, n - len(anim), len(anim), len(anim4), cost, noflip))
        report.append('By role (rim if used anywhere on a flat edge, static/animated): ' + '; '.join(
            '%s %d/%d' % (k, s_, a_) for k, (s_, a_) in sorted(roles.items())))
        report.append('Horizontal period: 64 px (4 tile columns); course repeats exactly every 64 px on the flat chunk: %s; '
                      'every 32 px: %s.' % (per, per32))
        report.append('Seam at the period (columns 63|64 and 127|128, floor rim row + ceiling rim row): %d and %d px differ; '
                      'mean of the other neighbouring column pairs inside tiles %.1f and %.1f; at tile edges %.1f and %.1f.'
                      % (seam[0], seam[1], inner[0], inner[1], tseam[0], tseam[1]))
        report.append('Mock-up rebuilt from the tile set equals the painted course: %s.' % same)
        report.append('Opaque pixels in the window: %d (hurt line = window edge; 0 px decoration past it).'
                      % int(frames[:, win].astype(bool).sum()))
        report.append('Ceiling: ' + CEILING[v])
        report.append('Step down = %s.' % ('drawn separately (lit from the upper left)' if v == 'A'
                                          else 'horizontal flip of the step-up tiles (mirror coordinates)'))
        report.append('Dither pairs (luma step): ' + ', '.join(dpairs))
        if F > 1:
            report.append('Frames %d, %d ticks per frame (%.1f per second), loop %d ticks = %.2f s. GIF %d ms per frame.'
                          % (F, TICKS[v], 60 / TICKS[v], F * TICKS[v], F * TICKS[v] / 60, ms))
            report.append(loopline)
            if v == 'B':
                report.append('Arc: forced damped string, ends pinned at the studs, 40 substeps per frame, 30 loops to '
                              'steady state; state drift over the recorded loop %s (string units, before scaling); '
                              'plus per-frame crackle jitter.' % ', '.join('%.3f' % s_ for s_ in ARC_SEAM))
            if v == 'C':
                report.append('Surface: damped wave on a 32 px mirror cell (reflecting ends), driven by 3 bubble pops '
                              'per loop, 30 substeps per frame, 60 loops to steady state; drift %.4f.' % WAVE['seam'])
        else:
            report.append('Static, no animation.')
        report.append('')
        gallery.append((v, n, cost, len(anim), gif))
        print(v, 'tiles', n, 'cost', cost, 'colours', len(used), 'period64', per, 'rebuilt', same)
    with open(os.path.join(HERE, 'numbers.txt'), 'w') as fh:
        fh.write('\n'.join(report))
    write_html(gallery)


def write_html(gallery):
    cells = []
    for v, n, cost, na, gif in gallery:
        lv = v.lower()
        anim = ('<figure><img src="%s" width="960" height="672" alt="%s animated, scrolling"><figcaption>Animated, '
                'scrolling 1 px per tick, three times size</figcaption></figure>' % (gif, v)) if gif else \
               '<p class="note">Static rim, no animation.</p>'
        cells.append('''<section class="var"><h2>%s. %s</h2>
<p>%d unique tiles (%d animated), ROM tile cost %d. Ceiling: %s</p>
<figure><img src="mock_%s_2x.png" width="640" height="448" alt="%s mock-up"><figcaption>Mock-up 320 x 224, two times size: ceiling band, floor band, join at x 160</figcaption></figure>
%s
<figure class="wide"><img src="parts_%s_3x.png" alt="%s parts"><figcaption>Parts, three times size: flat rim (two 64 px periods), floor step up, floor step down, ceiling step down, ceiling step up</figcaption></figure>
<figure class="wide"><img src="sheet_%s_4x.png" alt="%s tile sheet"><figcaption>Unique tiles, four times size; animated tiles show their 8 frames downwards</figcaption></figure>
</section>''' % (v, NAMES[v], n, na, cost, CEILING[v], lv, v, anim, lv, v, lv, v))
    html = '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Gum Trip kill strips</title>
<style>
body { background: #14171c; color: #d9dde3; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  margin: 0; padding: 24px 32px 64px; line-height: 1.45; }
h1 { font-size: 24px; margin: 0 0 4px; }
h2 { font-size: 19px; margin: 0 0 4px; color: #8fd3ff; }
.row { display: flex; gap: 32px; flex-wrap: wrap; align-items: flex-start; }
.var { border-top: 1px solid #2c323b; padding: 16px 0; max-width: 980px; }
p { margin: 2px 0 8px; max-width: 960px; }
figure { margin: 0 0 14px; }
figure.wide { overflow-x: auto; }
figcaption { font-size: 13px; color: #98a1ad; margin-top: 4px; }
img { image-rendering: pixelated; display: block; }
.side img { width: 640px; height: 448px; }
</style></head><body>
<h1>Gum Trip kill strips: three drafts</h1>
<p>Drafts only, nothing here is wired into the game. Hurt line = window edge; no pixel of any variant lies in the window. Numbers: <a href="numbers.txt" style="color:#8fd3ff">numbers.txt</a>.</p>
<h2>Side by side</h2>
<div class="row side">
''' + '\n'.join('<figure><img src="mock_%s_2x.png" alt="%s"><figcaption>%s. %s</figcaption></figure>' % (v.lower(), v, v, NAMES[v])
                for v, *_ in gallery) + '''
</div>
''' + '\n'.join(cells) + '\n</body></html>\n'
    with open(os.path.join(HERE, 'index.html'), 'w') as fh:
        fh.write(html)


if __name__ == '__main__':
    main()
