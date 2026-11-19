#!/usr/bin/env python3
# Bubblegum Brawl bottom-hazard draft, round 6: FIRE only.
# Helpers, the gas simulation and the cast-light code come from ../2026-11-10-hazards-v5-fire/draw_fire_v5.py.
# Motion is a small physical simulation baked to a seamless loop: temperature carried by a velocity field on a
# 128 px periodic domain, cut into tile variants A (x 0-63) and B (x 64-127); the strip is A B A B A.
# 16 software frames, 4 video frames each. Tile 64x32 per variant (4x2 Neo Geo tiles).
# Round 6 changes are marked "v6:" below: pointed tips (necking strain + sway + tip-keeping mask), the leader role
# moves between four sources, smoke removed. Deterministic, no network.
# Run:      /opt/homebrew/bin/python3.14 -I draw_fire_v6.py          (needs Pillow + numpy)
# Inspect:  /opt/homebrew/bin/python3.14 -I draw_fire_v6.py --check /scratch/dir   (writes nothing here)
# Numbers:  /opt/homebrew/bin/python3.14 -I draw_fire_v6.py --metrics              (prints the summary only)
# Tuning:   FIRE6='LEAD_T0=0.02;STRAIN=(22.0, 5.0, 13.0, 1.5, 0.45)' ... --metrics  (overrides module constants)
import os
import sys
from math import pi, sin, cos, sqrt
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
SCENE = os.path.join(ROOT, 'thoughts', 'shared', 'drafts', '2026-11-10-flier', 'A_v5_scene_3x.png')
W, H, NF = 64, 32, 16
HAZ_Y = 192
TAU = 2 * pi
XS = np.arange(W) + 0.5          # pixel centres




# ---------------------------------------------------------------- helpers
class Pal:
    def __init__(self, d):
        self.d = d
        self.keys = list(d)
        self.ix = {k: i + 1 for i, k in enumerate(self.keys)}
        self.lut = np.zeros((len(self.keys) + 1, 4), np.uint8)
        for k, i in self.ix.items():
            self.lut[i] = d[k] + (255,)

    def __getitem__(self, k):
        return self.ix[k]

    def img(self, idx):
        return Image.fromarray(self.lut[idx], 'RGBA')


def gk(s):
    r = max(1, int(3 * s + 0.5))
    x = np.arange(-r, r + 1)
    k = np.exp(-0.5 * (x / s) ** 2)
    return k / k.sum()


def blur_x(a, s):
    """Gaussian blur along x, periodic (the tile wraps)."""
    k = gk(s)
    r = len(k) // 2
    return sum(k[i + r] * np.roll(a, i, axis=-1) for i in range(-r, r + 1))


def blur_y(a, s):
    k = gk(s)
    r = len(k) // 2
    p = np.pad(a, ((r, r), (0, 0)), mode='edge')
    return sum(k[i] * p[i:i + a.shape[0]] for i in range(len(k)))


def despeckle(a, passes=2):
    """Remove 1-pixel islands (a pixel with no equal 4-neighbour). x wraps, y clamps."""
    for _ in range(passes):
        l, r = np.roll(a, 1, 1), np.roll(a, -1, 1)
        u, d = np.vstack([a[:1], a[:-1]]), np.vstack([a[1:], a[-1:]])
        iso = (l != a) & (r != a) & (u != a) & (d != a)
        rep = np.where(l == r, l, np.where(u == d, u, l))
        a = np.where(iso, rep, a)
    return a


def advect(T, u, v, dt, X, Y, S):
    """Semi-Lagrangian advection, bilinear, periodic in x, clamped in y. X, Y, u, v in pixels; grid spacing 1/S."""
    gh, gw = T.shape
    xb = (X - u * dt) * S - 0.5
    yb = (Y - v * dt) * S - 0.5
    x0 = np.floor(xb).astype(int)
    y0 = np.floor(yb).astype(int)
    fx, fy = xb - x0, yb - y0
    y0c, y1c = np.clip(y0, 0, gh - 1), np.clip(y0 + 1, 0, gh - 1)
    x0m, x1m = x0 % gw, (x0 + 1) % gw
    return ((T[y0c, x0m] * (1 - fx) + T[y0c, x1m] * fx) * (1 - fy)
            + (T[y1c, x0m] * (1 - fx) + T[y1c, x1m] * fx) * fy)


def wrapd(a, b):
    """Signed periodic distance a-b in (-32, 32]."""
    return (a - b + W / 2) % W - W / 2


def put(idx, x, y, c, only=None):
    x = int(np.floor(x)) % W
    y = int(np.floor(y))
    if 0 <= y < H and (only is None or idx[y, x] in only):
        idx[y, x] = c


def smooth_mask(m, passes=2):
    """3x3 majority filter on a boolean mask (x wraps, y clamps): rounds stair-steps, drops 1-pixel islands and holes."""
    for _ in range(passes):
        p = np.vstack([m[:1], m, m[-1:]]).astype(int)
        n = sum(np.roll(p[dy:dy + m.shape[0]], dx, 1) for dy in range(3) for dx in (-1, 0, 1))
        m = n >= 5
    return m



def set_domain(w):
    """Width of the periodic x domain: 64 (one tile) or 128 (tile variants A + B)."""
    global W, XS
    W = w
    XS = np.arange(W) + 0.5


# ================================================================ fire (advected temperature field)
# Simulated on a 128 px periodic domain: tile A = x 0-63, tile B = x 64-127.
PB = Pal({
    'o': (30, 6, 24),      # coal outline
    'c': (56, 20, 44),     # coal dark
    'C': (104, 44, 60),    # coal mid
    'a': (176, 104, 92),   # coal ash, lit top
    'S': (40, 26, 62),     # v6: unused (was smoke, shaded side); slot kept free
    's': (86, 54, 92),     # v6: unused (was smoke, body); slot kept free
    'M': (96, 8, 60),      # flame cool edge (magenta)
    'D': (150, 16, 40),    # deep crimson
    'r': (226, 44, 36),    # red
    'O': (252, 122, 30),   # orange
    'y': (255, 176, 46),   # amber (flame band and sparks)
    'Y': (255, 222, 84),   # yellow
    'w': (255, 252, 222),  # white-hot core
})
# x, width, puffs/loop, phase, resting strength, resting pulse depth.
# v6: no permanent leader. Every source has a resting strength; the leader role (strength 1.0, wide base, shallow
# pulse) is handed from source to source over the loop (LEAD). Resting strengths stay well under the leader, so a
# resting source never ties with it.
SPOTS = [(9, 4.6, 2, 0.00, 0.60, 0.30), (21, 2.9, 3, 0.37, 0.50, 0.40), (39, 4.6, 2, 0.61, 0.60, 0.32), (49, 2.6, 3, 0.13, 0.44, 0.42),
         (68, 3.7, 2, 0.80, 0.56, 0.36), (85, 4.6, 3, 0.29, 0.60, 0.30), (94, 2.6, 2, 0.55, 0.42, 0.42), (111, 4.4, 3, 0.92, 0.60, 0.34),
         (122, 2.9, 2, 0.45, 0.48, 0.40)]
# v6: leader schedule: (source index, time on, time off) in loop units. A (x 9) -> B (x 85) -> A (x 39) -> B (x 111).
LEAD = [(0, 0.00, 0.25), (5, 0.25, 0.50), (2, 0.50, 0.75), (7, 0.75, 1.00)]
LEAD_T0 = 0.03                 # shifts the whole schedule against the 16 sampled frames
LEAD_ST, LEAD_WD, LEAD_PD = 1.00, 6.0, 0.10
LEAD_PRE = 0.14                # the next leader's source is turned up this much before the old one is turned down: it needs the time to climb
LEAD_RAMP = 0.05               # the source strength changes over this time
LEAD_LAG = 0.07                # the air over the old leader closes this much later: its last tongue pinches off, rises and dies while the new one arrives
LEAD_AIR_RAMP = 0.04
FCOOL = 3.0
FCOOL_K = (1.45, 0.98)         # cooling = FCOOL * (K0 - K1 * envelope): weak sources sit in colder air
TOPC = (5.0, 11.0, 9.0)        # cold air entrained higher up: rate, start row, span
CEIL = (50.0, 13.0, 6.0, 4.0)  # cold-air lid per source rank: lid row = min(A * (1 - rank envelope), max row); rate, span
EDGE = (1.0, 0.0)
TOPG = (22.0, 5.0)             # v6: guard under the top edge of the strip (rate, rows): no tongue is cut flat by the tile border
CONE = (10.0, 0.9, 27.0, 2.0)  # cold air entrained from the sides: each source keeps a teardrop-shaped warm zone
BASE = (0.33, 0.06)            # low flame along the whole bed between the sources
# v6: buoyant acceleration. Hot gas speeds up as it rises, so the plume necks: air flows in toward the axis of each
# tongue (rate grows with height) and the gas on the axis is stretched upward. This strain in the VELOCITY field is
# what draws the tip out to a point; cooling terms (v5) only ate the tongue evenly and left a dome.
# rate at full height (1/loop), height where it starts, span, window half-width factor, share given back as upward speed
STRAIN = (26.0, 8.0, 11.0, 1.5, 0.45)
# v6: each tongue's axis sways, more the higher up, as a wave that travels up the tongue (the tip licks sideways).
# amplitude px at 20 px height, sways per loop, vertical wavelength px
SWAY = (3.2, 2, 34.0)
FMODES = [(2, 30, 1, 2, 10, 0.0), (4, 22, -1, 2, 13, 1.3), (6, 16, 2, 3, 11, 2.1), (10, 12, -2, 3, 8, 4.0),
          (1, 26, 1, 2, 5, 0.7), (3, 19, -1, 3, 6, 2.9)]
# n (x harmonics per 128 px), vertical wavelength px, time harmonics of the sideways drift, of the upward drift, speed px/loop, phase


def sstep(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def win(t, on, off, ramp):
    """Periodic smooth window: rises over `ramp` after `on`, falls over `ramp` after `off`."""
    a = (t - on) % 1.0
    dur = (off - on) % 1.0
    v = sstep(a / ramp) - sstep((a - dur) / ramp)
    if dur + ramp > 1.0:        # the fall of the previous period is still running
        v -= sstep((a + 1.0 - dur) / ramp) - 1.0
    return v


def spot_state(t):
    """The sources at time t: (x, width, puffs, phase, source strength, pulse depth, air strength).
    Air strength is the rank the cooling terms see; it follows the source strength but closes later (LEAD_LAG)."""
    out = []
    for i, (x0, wd, m, ph, st, pd) in enumerate(SPOTS):
        ls = la = 0.0
        for (j, on, off) in LEAD:
            if j == i:
                ls = max(ls, win(t, on + LEAD_T0 - LEAD_PRE, off + LEAD_T0, LEAD_RAMP))
                la = max(la, win(t, on + LEAD_T0 - LEAD_PRE, off + LEAD_T0 + LEAD_LAG, LEAD_AIR_RAMP))
        out.append((x0, wd + (LEAD_WD - wd) * ls, m, ph, st + (LEAD_ST - st) * ls, pd + (LEAD_PD - pd) * ls, st + (LEAD_ST - st) * la))
    return out


def fire_env(x, P, flat=False):
    e = 0
    for (x0, wd, m, ph, st, pd, sa) in P:
        if flat:   # flat-topped: a tongue may sway under its own lid without being cut
            e = np.maximum(e, sa * np.exp(-(wrapd(x, x0) / (2.0 * wd + 4.0)) ** 4))
        else:
            e = np.maximum(e, sa * np.exp(-(wrapd(x, x0) / (1.8 * wd + 2.0)) ** 2))
    return e


def fire_cone(X, Y, P):
    """0 inside the teardrop of some source, 1 in the open air beside and above it. Only above the low base flame."""
    h = np.clip(24.5 - Y, 0, None)
    out = 1.0
    for (x0, wd, m, ph, st, pd, sa) in P:
        hw = CONE[1] * wd * np.clip(1 - h / (CONE[2] * sa), 0, 1) ** 0.7 + 1.0
        out = np.minimum(out, np.clip((np.abs(wrapd(X, x0)) - hw) / CONE[3], 0, 1))
    return out * np.clip((22.0 - Y) / 3.0, 0, 1)


def fire_cool(X, Y, P):
    x1 = X[:1]
    lid = np.minimum(CEIL[0] * (1 - fire_env(x1, P, True)), CEIL[1])
    return (FCOOL * (FCOOL_K[0] - FCOOL_K[1] * fire_env(x1, P)) + TOPC[0] * np.clip((TOPC[1] - Y) / TOPC[2], 0, 1)
            + CEIL[2] * np.clip((lid - Y) / CEIL[3], 0, 1) + CONE[0] * fire_cone(X, Y, P)
            + TOPG[0] * np.clip((TOPG[1] - Y) / TOPG[1], 0, 1))


def fire_source(x, t, P):
    s = BASE[0] + BASE[1] * np.sin(TAU * (5 * x / W + t))
    for (x0, wd, m, ph, st, pd, sa) in P:
        amp = st * (1 - pd + pd * sin(TAU * (m * t + ph)))
        xc = x0 + 1.5 * sin(TAU * (t + 3 * ph))
        s = np.maximum(s, amp * np.exp(-(wrapd(x, xc) / wd) ** 2))
    return s


def fire_vel(X, Y, t, T, P=None):
    ramp = np.clip((27 - Y) / 12.0, 0, 1)
    u = 0
    v = 0
    for (n, ly, m, r, A, ph) in FMODES:
        kx, ky = TAU * n / W, TAU / ly
        ax = kx * X + TAU * m * t + ph
        ay = ky * Y + TAU * r * t
        u = u + A * np.sin(ax) * np.cos(ay)
        v = v - A * (kx / ky) * np.cos(ax) * np.sin(ay)
    u, v = u * ramp, v * ramp - (52 + 70 * T)
    if P is not None:           # v6: necking strain around each tongue axis (not applied to the embers: their paths stay as in v5)
        K, h0, hs, rf, vf = STRAIN
        h = 25.0 - Y
        k = K * np.clip((h - h0) / hs, 0, 1)
        kint = K * (np.clip(h - h0, 0, hs) ** 2 / (2 * hs) + np.clip(h - h0 - hs, 0, None))
        hh = np.clip(h, 0, None)
        for (x0, wd, m, ph, st, pd, sa) in P:
            xc = (x0 + 1.5 * sin(TAU * (t + 3 * ph))
                  + SWAY[0] * (hh / 20.0) ** 1.5 * np.sin(TAU * (SWAY[1] * t + ph - hh / SWAY[2])))
            dx = wrapd(X, xc)
            w = st * np.exp(-(dx / (rf * wd + 2.0)) ** 2)
            u = u - k * dx * w
            v = v - vf * kint * w
    return u, v


def sim_fire():
    """Temperature T carried by the velocity field, cooled by the air terms, fed at the coal line. Run until the
    16-frame loop repeats."""
    S, sub = 3, 8
    gw, gh = W * S, H * S
    X, Y = np.meshgrid((np.arange(gw) + 0.5) / S, (np.arange(gh) + 0.5) / S)
    steps = NF * sub
    dt = 1.0 / steps
    T = np.zeros((gh, gw))
    src_rows = (Y > 23.0) & (Y < 28.5)
    prev = None
    cool = None
    for loop in range(14):
        out = []
        for i in range(steps):
            t = i * dt
            if i % sub == 0:
                out.append(T.copy())
            P = spot_state(t)
            if cool is None or i % 2 == 0:
                cool = fire_cool(X, Y, P)
            u, v = fire_vel(X, Y, t, blur_x(T, 1.5), P)
            T = advect(T, u, v, dt, X, Y, S)
            T = blur_y(blur_x(T, 0.26), 0.2)
            T = np.maximum(T - dt * cool * (EDGE[0] + EDGE[1] * (1 - T)), 0)
            s = fire_source(X, t, P)
            T = np.where(src_rows, np.maximum(T, s), T)
            T[Y >= 28.5] = 0
        err = max(np.abs(a - b).max() for a, b in zip(prev, out)) if prev is not None else 1.0
        prev = out
        if err < 1e-5:
            break
    assert err < 1e-3, ('fire loop not periodic in time', err)
    ds = lambda o: o.reshape(H, S, W, S).mean((1, 3))
    return [ds(o) for o in prev]


LUMPS = [(3.0, 28.6, 4.4, 3.2), (10.4, 28.0, 3.2, 3.4), (16.8, 29.0, 4.6, 2.8), (24.0, 28.0, 3.0, 3.6), (29.6, 28.8, 3.8, 3.0),
         (36.4, 27.8, 4.2, 3.6), (43.0, 29.0, 3.4, 2.6), (49.0, 28.2, 4.4, 3.3), (56.4, 28.8, 3.2, 3.0), (62.0, 27.9, 3.6, 3.5),
         (68.6, 28.8, 4.4, 3.0), (75.6, 28.0, 3.4, 3.4), (81.4, 29.0, 3.6, 2.7), (88.0, 28.1, 4.6, 3.5), (95.4, 28.8, 3.2, 3.0),
         (101.2, 28.0, 3.8, 3.4), (108.2, 28.9, 4.4, 2.8), (115.2, 28.0, 3.2, 3.5), (121.6, 28.6, 4.2, 3.1)]
# 20 embers as in v5; they cool white, yellow, amber, orange, red, crimson as they rise.
SPARKS = [(0, 0.05, 0.62, 14), (1, 0.30, 0.55, -10), (2, 0.52, 0.70, 6), (3, 0.71, 0.58, -16), (4, 0.16, 0.66, 12),
          (5, 0.88, 0.60, -6), (0, 0.58, 0.50, -18), (2, 0.22, 0.64, 8), (5, 0.44, 0.56, 16), (6, 0.36, 0.52, -8),
          (7, 0.02, 0.66, 10), (8, 0.67, 0.55, -12), (7, 0.49, 0.60, -16), (0, 0.33, 0.68, 22), (5, 0.12, 0.70, -20),
          (2, 0.84, 0.60, -14), (4, 0.62, 0.58, -9), (7, 0.76, 0.64, 18), (1, 0.93, 0.50, 11), (8, 0.18, 0.54, 7)]  # spot, birth, life, vx0
EMBER = ((0.14, 'w'), (0.32, 'Y'), (0.50, 'y'), (0.66, 'O'), (0.84, 'r'), (1.01, 'D'))


def spark_pos(spot, t0, age):
    """Hot particle: drag toward the gas velocity plus its own buoyancy. Integrated from birth."""
    x, y = SPOTS[spot][0], 21.0
    vx, vy = SPARKS_VX[spot, t0], -70.0
    n = int(round(age * 256))
    dt = 1.0 / 256
    for i in range(n):
        t = (t0 + i * dt) % 1.0
        gu, gv = fire_vel(np.float64(x), np.float64(y), t, 0.0)
        vx += (7.0 * (gu - vx)) * dt
        vy += (7.0 * (gv - vy) - 30.0) * dt
        x += vx * dt
        y += vy * dt
    return x, y


SPARKS_VX = {(s, t0): vx for (s, t0, life, vx) in SPARKS}
BACK_SHIFT, BACK_LAG, BACK_DROP = 45, 6, 2
BACK_BANDS = ((0.20, 'M'), (0.32, 'D'), (0.60, 'r'))
FRONT_BANDS = ((0.10, 'M', 0), (0.15, 'D', 0), (0.21, 'r', 0), (0.33, 'O', 0), (0.45, 'y', 1), (0.57, 'Y', 1), (0.74, 'w', 1))
FRONT_BLUR = ((0.7, 0.6), (1.2, 1.0))   # v6: less blur than v5 (0.9/0.7 and 1.5/1.1): a narrow tip is not averaged away
TIP_GROW = 4


FLAME_FIX = None        # hazards-final: optional function (idx, frame) -> idx


def shift(m, dx, dy):
    """m sampled at (x + dx, y + dy); x wraps, outside in y is False."""
    m = np.roll(m, -dx, axis=1)
    out = np.zeros_like(m)
    if dy > 0:
        out[:-dy] = m[dy:]
    elif dy < 0:
        out[-dy:] = m[:dy]
    else:
        out = m
    return out


def tip_mask(raw):
    """v6: the 3x3 majority filter rounds stair-steps but also eats every feature under 3 px wide, which is exactly a
    flame tip. After the filter, the tip is grown back from the unfiltered field: a pixel that is hot in the raw
    mask, stands on the shape (below, or diagonally below: the tip may lean) and has no shape pixel beside it.
    Returns the mask and the grown-back tip pixels."""
    sm = smooth_mask(raw)
    tip = np.zeros_like(sm)
    for _ in range(TIP_GROW):
        below = shift(sm, 0, 1) | shift(sm, -1, 1) | shift(sm, 1, 1)
        add = raw & ~sm & below & ~shift(sm, -1, 0) & ~shift(sm, 1, 0)
        sm = sm | add
        tip = tip | add
    return sm, tip


def render_fire():
    set_domain(128)
    Ts = sim_fire()
    frames = []
    for f in range(NF):
        t = f / NF
        T = blur_y(blur_x(Ts[f], FRONT_BLUR[0][0]), FRONT_BLUR[0][1])
        Tc = blur_y(blur_x(Ts[f], FRONT_BLUR[1][0]), FRONT_BLUR[1][1])   # cores are cut from a smoother field
        idx = np.zeros((H, W), np.uint8)
        # 1 back row of flames: the same field, another moment and place, lower and in the cool colours only
        Tb = blur_y(blur_x(np.roll(Ts[(f + BACK_LAG) % NF], BACK_SHIFT, axis=1), 1.2), 0.9)
        Tb = np.vstack([np.zeros((BACK_DROP, W)), Tb[:-BACK_DROP]])
        inside = np.ones((H, W), bool)
        for th, ch in BACK_BANDS:
            inside = smooth_mask(Tb > th) & inside
            idx[inside] = PB[ch]
        # 2 front row: cool magenta edge, crimson, red body, orange, amber, yellow, white core
        inside = np.ones((H, W), bool)
        tips = np.zeros((H, W), bool)
        for th, ch, k in FRONT_BANDS:
            m, tp = tip_mask((Tc if k else T) > th)
            inside = m & inside
            tips |= tp & inside
            idx[inside] = PB[ch]
        idx = np.where(tips, idx, despeckle(idx))     # a 1-pixel tip is not a speck
        if FLAME_FIX is not None:                     # hazards-final: clean-up hook, runs before coal and embers
            idx = FLAME_FIX(idx, f)
        # coal bed: round lumps. Top rim glows with the heat right above it; the body has an ash-lit top-left cluster,
        # a mid cluster, a dark cluster and an outline-dark underside; cracks between lumps glow.
        heat = fire_source(XS, t, spot_state(t))
        for y in range(25, H):
            for x in range(W):
                best, bl = 9.0, None
                for (cx, cy, rx, ry) in LUMPS:
                    q = (wrapd(x + 0.5, cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2
                    if q < best:
                        best, bl = q, (cx, cy, rx, ry)
                hx = heat[x]
                if best < 1.0:
                    cx, cy, rx, ry = bl
                    up = (y + 0.5 - cy) / ry
                    lf = wrapd(x + 0.5, cx) / rx
                    s = up + 0.6 * lf
                    if best > 0.62 and up < 0.25:
                        c = 'Y' if hx > 0.9 else 'O' if hx > 0.72 else 'r' if hx > 0.5 else 'D'
                    elif s < -0.55:
                        c = 'a'
                    elif s < -0.05:
                        c = 'C'
                    elif best > 0.62 or s > 0.6:
                        c = 'o'
                    else:
                        c = 'c'
                elif y >= 27:
                    c = 'o' if y >= 30 else ('w' if hx > 0.9 else 'Y' if hx > 0.7 else 'O' if hx > 0.5 else 'r')
                else:
                    continue
                if y == H - 1:
                    c = 'o'
                idx[y, x] = PB[c]
        soft = (0, PB['a'], PB['M'], PB['D'])
        for (spot, t0, life, vx) in SPARKS:
            age = (t - t0) % 1.0
            if age < life:
                x, y = spark_pos(spot, t0, age)
                a = age / life
                if y < 24:
                    put(idx, x, y, PB[next(c for lim, c in EMBER if a < lim)], only=soft)
        frames.append(idx)
    set_domain(64)
    return frames, {}


# ---------------------------------------------------------------- measures (one code path for v4, v5 and v6)
HOT = 'rOyYw'


def nospark(m):
    """Drop single hot pixels with no hot neighbour (embers), so that only flame is measured. x wraps."""
    p = np.vstack([np.zeros_like(m[:1]), m, np.zeros_like(m[:1])]).astype(int)
    n = sum(np.roll(p[dy:dy + m.shape[0]], dx, 1) for dy in range(3) for dx in (-1, 0, 1)) - m
    return m & (n > 0)


def hot_mask(fr):
    return nospark(np.isin(fr[:25], [PB[k] for k in HOT]))


def sheet_masks(path):
    """Hot masks of a finished frames_B_1x.png of an earlier round (hot = red channel >= 220, opaque)."""
    im = np.array(Image.open(path).convert('RGBA')).astype(int)
    nv = im.shape[0] // H
    out = []
    for f in range(NF):
        fr = np.concatenate([im[r * H:(r + 1) * H, f * 64:(f + 1) * 64] for r in range(nv)], axis=1)
        out.append(nospark(((fr[..., 3] > 0) & (fr[..., 0] >= 220))[:25]))
    return out


def run_width(row, x):
    """Width of the hot run in this row that holds column x (or the nearest hot pixel within 4 px: a leaning tongue)."""
    n = len(row)
    if not row[x % n]:
        c = [d for d in range(-4, 5) if row[(x + d) % n]]
        if not c:
            return 0
        x += min(c, key=abs)
    l = r = 0
    while l < n and row[(x - l - 1) % n]:
        l += 1
    while r < n and row[(x + r + 1) % n]:
        r += 1
    return l + r + 1


def mask_metrics(m):
    """One frame: (tallest, second, hot pixels per 64 px, mean hot column height, peaks, taper, tip width).
    A peak is the highest hot column within 5 px to each side. Taper (the v5 measure) = width of the tallest tongue at
    70 % of its height over its width at 25 %. Tip width = its width at 90 % of the height."""
    hgt = np.where(m.any(0), 25 - m.argmax(0), 0)
    n = len(hgt)
    pk = sorted(((int(hgt[x]), x) for x in range(n)
                 if hgt[x] >= 5 and hgt[x] == max(hgt[(x + d) % n] for d in range(-5, 6)) and hgt[x] > hgt[(x - 1) % n]), reverse=True)
    h, x = pk[0]
    wid = lambda p: run_width(m[25 - max(1, int(round(p * h)))], x)
    return (h, pk[1][0] if len(pk) > 1 else 0, int(m.sum()) * 64 // n, float(hgt.mean()), pk, wid(0.70) / max(1, wid(0.25)), wid(0.90))


def summary(name, ms):
    h1, h2, px, ch = ([m[i] for m in ms] for i in range(4))
    tp, tw = [m[5] for m in ms], [m[6] for m in ms]
    print('  %-3s tallest mean %.1f min %d max %d | second mean %.1f | gap min %d, frames with gap<=1: %s | hot px per 64 px: mean %.0f min %d | hot column height mean %.2f'
          % (name, np.mean(h1), min(h1), max(h1), np.mean(h2), min(a - b for a, b in zip(h1, h2)),
             [f for f in range(NF) if h1[f] - h2[f] <= 1] or 'none', np.mean(px), min(px), np.mean(ch)))
    print('      taper (width at 70%% / width at 25%% of the tallest tongue): mean %.2f min %.2f max %.2f | width at 90%% height: mean %.1f px | leader x per frame: %s'
          % (np.mean(tp), min(tp), max(tp), np.mean(tw), ' '.join(str(m[4][0][1]) for m in ms)))




# ================================================================ cast light (fire, lava) on the scene above
# Three warm colours added to the CITY palette; hard nested shapes, no ramp: a low band on the building face near the
# hazard, a rim on the building's vertical edges, a rim on the underside of the nearest islands. The level (1..3) of
# each 16 px column follows the simulated brightness of the hazard column below it; the hazard repeats every 64 px,
# so the light does too. v4: fire and lava repeat every 128 px (tiles A + B): 8 columns x 16 frames of levels.
BLD, SKY = (10, 12, 34), (20, 26, 66)
ISLAND = [(52, 60, 110), (28, 32, 70), (90, 100, 160), (140, 156, 198)]
LIGHT_RGB = {'face': (62, 22, 54), 'dim': (170, 54, 46), 'hot': (255, 150, 62)}
LIGHT_W = {'B': {'D': 1, 'r': 2, 'O': 3, 'Y': 4, 'w': 5, 'y': 3}, 'D': {'r': 1, 'O': 2, 'y': 4, 'Y': 6}}
LIGHT_ROWS = {'B': 24, 'D': 16}
LIGHT_REF = {'B': HAZ_Y + 6, 'D': HAZ_Y + 9}       # screen row the light is measured from
MOUND = [[1, 1, 2, 3, 3, 4, 4, 4, 3, 3, 3, 2, 2, 1, 1, 1], [1, 2, 2, 2, 3, 3, 3, 4, 4, 4, 4, 3, 2, 2, 1, 1],
         [1, 1, 1, 2, 2, 3, 4, 4, 4, 3, 2, 2, 2, 2, 1, 1], [1, 2, 3, 3, 4, 4, 4, 3, 3, 2, 2, 2, 1, 1, 1, 1]]  # face band height per x, hand-placed
FACE_ADD = (0, 0, 2, 4)
RIM_HOT = (0, 3, 6, 10)
RIM_DIM = (0, 8, 13, 19)
UNDER_REACH = 44


def light_levels(key, pal, frames):
    wmap = np.zeros(len(pal.keys) + 1)
    for k, v in LIGHT_W[key].items():
        wmap[pal[k]] = v
    rows = LIGHT_ROWS[key]
    sig = np.array([[wmap[fr[:rows, c * 16:(c + 1) * 16]].sum() for c in range(fr.shape[1] // 16)] for fr in frames])
    sig = 0.5 * sig + 0.25 * (np.roll(sig, 1, 1) + np.roll(sig, -1, 1))
    sig = sig / (0.5 * sig.mean(0, keepdims=True) + 0.5 * sig.mean())
    lo, hi = np.percentile(sig, [30, 70])
    return 1 + (sig > lo).astype(int) + (sig > hi).astype(int)


def light_masks(base):
    a = np.array(base.convert('RGB'))
    eq = lambda c: (a == np.array(c, np.uint8)).all(-1)
    bld, sky = eq(BLD), eq(SKY)
    isl = np.zeros_like(bld)
    for c in ISLAND:
        isl |= eq(c)
    edge = bld & (np.roll(sky, 1, 1) | np.roll(sky, -1, 1))
    under = isl & ~np.roll(isl, -1, 0)
    return bld, edge, under


def cast_light(s, key, lev, masks):
    bld, edge, under = masks
    px = s.load()
    ref = LIGHT_REF[key]
    face, dim, hot = (LIGHT_RGB[k] + (255,) for k in ('face', 'dim', 'hot'))
    for x in range(320):
        col = (x // 16) % len(lev)
        L = int(lev[col])
        r = x % 16
        fh = MOUND[col % 4][r] + FACE_ADD[L]
        for y in range(ref - UNDER_REACH, 224):
            d = ref - y
            if d > 0 and under[y, x]:
                if L == 3 and 3 <= r <= 12:
                    px[x, y] = hot
                elif (L >= 2 and 1 <= r <= 14) or 5 <= r <= 10:
                    px[x, y] = dim
            elif d > 0 and edge[y, x] and d <= RIM_DIM[L]:
                px[x, y] = hot if d <= RIM_HOT[L] else dim
            elif bld[y, x] and d <= fh:
                px[x, y] = face



# ================================================================ output
V4 = os.path.join(HERE, '..', '2026-11-10-hazards-v4')
V5 = os.path.join(HERE, '..', '2026-11-10-hazards-v5-fire')
VIEW_Y = 136          # GIF crop: 56 px of scene above the strip
BG = (10, 12, 34, 255)
STILL = 2             # same still frame as v3, v4 and v5
VF = 4                # video frames (60 Hz) per animation frame


def base_scene():
    """Round 1 scene mock: accepted arena draft at 1x, old tag box removed, city extended behind the hazard."""
    from PIL import ImageDraw
    im = Image.open(SCENE).convert('RGBA')
    s = im.resize((320, 224), Image.NEAREST)
    d = ImageDraw.Draw(s)
    d.rectangle((276, 6, 319, 46), fill=(8, 10, 28, 255))
    band = s.crop((0, 172, 320, 180))
    for y in range(180, 224, 8):
        s.paste(band, (0, y))
    return s


def scene_frame(base, frames, f, masks, lev):
    s = base.copy()
    cast_light(s, 'B', lev[f], masks)
    ti = PB.img(frames[f])                  # 128 px (variants A + B): the strip is A B A B A
    for x in range(0, 320, ti.width):
        s.alpha_composite(ti.crop((0, 0, min(ti.width, 320 - x), H)), (x, HAZ_Y))
    return s


def tile_count(frames):
    seen = set()
    for fr in frames:
        for ty in range(0, H, 16):
            for tx in range(0, fr.shape[1], 16):
                seen.add(fr[ty:ty + 16, tx:tx + 16].tobytes())
    return len(seen)


def save_gif(path, imgs, ms):
    imgs = [im.convert('RGB').quantize(colors=128, dither=Image.Dither.NONE) for im in imgs]
    imgs[0].save(path, save_all=True, append_images=imgs[1:], duration=ms, loop=0, disposal=1, optimize=False)


def sheet16(sc, path):
    """All 16 frames in the scene at 3x, full 320 px width (A B A B A), 52 px high: the strip and 20 px above it."""
    from PIL import ImageDraw
    cw, ch, sc3 = 320, 52, 3
    sheet = Image.new('RGB', (cw * sc3 + 24, NF * (ch * sc3 + 26) + 12), (24, 24, 28))
    d = ImageDraw.Draw(sheet)
    for f in range(NF):
        y = 12 + f * (ch * sc3 + 26)
        d.text((12, y), 'frame %d' % f, fill=(200, 200, 205))
        sheet.paste(sc[f].crop((0, 224 - ch, cw, 224)).convert('RGB').resize((cw * sc3, ch * sc3), Image.NEAREST), (12, y + 14))
    sheet.save(path)


def overrides():
    """FIRE6="LEAD_T0=0.02;LEAD_LAG=0.08" sets module constants for a tuning run (numbers or Python literals)."""
    import ast
    spec = os.environ.get('FIRE6', '')
    for kv in filter(None, spec.split(';')):
        k, v = kv.split('=', 1)
        assert k in globals(), k
        globals()[k] = ast.literal_eval(v)
    return spec


def main():
    check = sys.argv[sys.argv.index('--check') + 1] if '--check' in sys.argv else None
    quick = '--metrics' in sys.argv
    spec = overrides()
    if spec:
        print('overrides:', spec)
    frames, _ = render_fire()
    assert W == 64 and len(frames) == NF and all(fr.shape == (H, 128) for fr in frames)
    ms = [mask_metrics(hot_mask(fr)) for fr in frames]
    if quick:
        print('   ', ' '.join('%d/%d' % (m[0], m[1]) for m in ms))
        summary('v6', ms)
        return
    used = set()
    for fr in frames:
        used |= set(np.unique(fr).tolist())
    used.discard(0)
    names = {PB.keys[i - 1] for i in used}
    assert len({PB.d[n] for n in PB.keys}) == len(PB.keys) and len(PB.keys) <= 15
    # seamless in time: the simulation asserts a converged periodic loop; here the wrap step must look like any other step
    df = [int((frames[i] != frames[(i + 1) % NF]).sum()) for i in range(NF)]
    assert min(df[:-1]) * 0.8 <= df[-1] <= max(df[:-1]) * 1.25, ('time seam stands out', df)
    # seamless in x: the joints B|A (x 127|0) and A|B (x 63|64) must not differ more than joints inside a tile
    st = np.stack(frames)
    jd = (st != np.roll(st, -1, axis=2)).sum((0, 1))            # jd[x] = pixels that differ between column x and x+1
    inner = np.delete(jd, [63, 127])
    assert jd[127] <= inner.max() and jd[63] <= inner.max(), ('x seam stands out', jd[63], jd[127], inner.max())
    print('fire colours=%d used of %d in palette (unused: %s) tiles=%d raw, %d unique; frame=%d video frames'
          % (len(names), len(PB.keys), [k for k in PB.keys if k not in names] or 'none', 16 * NF, tile_count(frames), VF))
    print('  time: changed pixels per step: wrap(15->0)=%d, other steps min=%d max=%d' % (df[-1], min(df[:-1]), max(df[:-1])))
    print('  x: differing pixels across joint B|A=%d, A|B=%d, inside tiles min=%d median=%d max=%d'
          % (jd[127], jd[63], inner.min(), np.median(inner), inner.max()))
    for f, m in enumerate(ms):
        print('    f%02d tallest %2d second %2d gap %2d hot/64 %3d taper %.2f tip %d | %s'
              % (f, m[0], m[1], m[0] - m[1], m[2], m[5], m[6], ' '.join('%d@%d' % p for p in m[4][:5])))
    summary('v6', ms)
    for nm, d in (('v5', V5), ('v4', V4)):
        summary(nm, [mask_metrics(m) for m in sheet_masks(os.path.join(d, 'frames_B_1x.png'))])
    base = base_scene()
    masks = light_masks(base)
    lev = light_levels('B', PB, frames)
    sc = [scene_frame(base, frames, f, masks, lev) for f in range(NF)]
    out = check or HERE
    sheet16(sc, os.path.join(out, 'frames_B_16_3x.png'))
    strip = Image.new('RGBA', (64 * NF, H * 2), (0, 0, 0, 0))   # build input: 16 frames per row, row 0 = A, row 1 = B
    for f in range(NF):
        ti = PB.img(frames[f])
        for v in range(2):
            strip.alpha_composite(ti.crop((v * 64, 0, v * 64 + 64, H)), (f * 64, v * H))
    strip.save(os.path.join(out, 'frames_B_1x.png'))
    if check:
        return
    sc[STILL].convert('RGB').resize((960, 672), Image.NEAREST).save(os.path.join(HERE, 'scene_B_3x.png'))
    crop = [s.crop((0, VIEW_Y, 320, 224)).resize((1280, (224 - VIEW_Y) * 4), Image.NEAREST) for s in sc]
    save_gif(os.path.join(HERE, 'anim_B_16f_4x.gif'), crop, int(round(VF * 1000 / 60 / 10)) * 10)


if __name__ == '__main__':
    sys.dont_write_bytecode = True
    main()
