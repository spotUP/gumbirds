#!/usr/bin/env python3
# Roofline bottom-hazard drafts, round 3 (polish pass on round 2): A spikes, B fire, C water (+ lurker sprite), D lava.
# Motion comes from small physical simulations baked to a seamless loop:
#   tile 64x32 (4x2 Neo Geo tiles), 16 software frames.
# Shading: the simulated fields are smoothed, then cut into hard cel bands. No ramps, no dither, no noise.
# Deterministic, no network. Run: python3.14 -I draw_hazards_v3.py     (needs Pillow + numpy)
# Inspect one hazard only:   python3.14 -I draw_hazards_v3.py --only C --check /scratch/dir   (writes nothing here)
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
# video frames (60 Hz) per animation frame of the 16-frame loop
VFRAMES = {'A': 4, 'B': 4, 'C': 6, 'D': 8}


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


# ================================================================ A: spikes (spring-driven pistons + arc)
PA = Pal({
    'o': (12, 10, 26),     # outline / deep shadow
    'd': (58, 66, 128),    # steel shadow (cool violet)
    'm': (112, 130, 192),  # steel mid
    'l': (172, 192, 232),  # steel lit face
    'h': (228, 240, 255),  # highlight
    'w': (255, 255, 255),  # rim / arc core
    'a': (64, 224, 255),   # arc halo, inner (cyan)
    'k': (26, 18, 30),     # stripe black
    'y': (250, 200, 44),   # stripe yellow
    'Y': (198, 108, 28),   # stripe yellow shade (to orange)
    'g': (74, 68, 112),    # rail plate
    'R': (255, 62, 54),    # lamp on
    'r': (104, 22, 44),    # lamp off
    's': (255, 150, 60),   # spark
    'A': (112, 92, 255),   # arc halo, outer (violet)
})
RAIL_Y = 22
SLEEVE_Y = 17
BLADE_HW = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7]
BL = len(BLADE_HW)


def sim_piston():
    """One piston: mass on a spring chasing a square-wave target. Thrust is stiff and under-damped (overshoot and
    ring), retraction is soft and near critically damped. Integrated for 3 loops so the sampled loop is periodic."""
    n = 3200
    dt = 1.0 / n
    x, v = 0.0, 0.0
    out = None
    for loop in range(3):
        xs, vs = [], []
        for i in range(n):
            t = i * dt
            if i % (n // NF) == 0:
                xs.append(x)
                vs.append(v)
            up = t < 0.5
            om, ze = (TAU * 5.0, 0.24) if up else (TAU * 2.4, 0.85)
            acc = om * om * ((1.0 if up else 0.0) - x) - 2 * ze * om * v
            v += acc * dt
            x += v * dt
        out = (xs, vs)
    return out


def arc_path(f, gap, x0, y0, x1, y1):
    """Jagged core between two blades: straight line + sag + random kinks, re-rolled every frame."""
    rng = np.random.default_rng(1000 + f * 7 + gap)
    n = x1 - x0
    ctrl = np.concatenate([[0], rng.uniform(-3.0, 3.0, 4), [0]])
    cx = np.linspace(0, n, len(ctrl))
    pts = []
    for i in range(n + 1):
        u = i / n
        y = y0 + (y1 - y0) * u + 1.5 * sin(pi * u) + np.interp(i, cx, ctrl)
        pts.append((x0 + i, int(round(y))))
    core = []
    py = pts[0][1]
    for (x, y) in pts:
        for yy in range(min(py, y), max(py, y) + 1):
            core.append((x, yy))
        py = y
    # two forks leaving the core, one up, one down
    forks = []
    for b in range(2):
        k = int(rng.integers(2, n - 1))
        bx, by = pts[k]
        sx = 1 if rng.random() < 0.5 else -1
        sy = -1 if b == 0 else 1
        fork = []
        for s in range(int(rng.integers(3, 6))):
            by += sy
            if s % 2 == 1:
                bx += sx
            fork.append((bx, by))
        forks.append(fork)
    return core, forks


def render_spikes():
    ext, vel = sim_piston()
    frames = []
    for f in range(NF):
        idx = np.zeros((H, W), np.uint8)
        tips = []
        for i in range(4):
            c = 8 + 16 * i
            ff = (f - 4 * i) % NF
            e, v = ext[ff], vel[ff]
            ty = max(0, int(round(8 - 6 * e)))
            tips.append((c, ty, e, v))
            # shaft (chrome column with rings that travel with it)
            for y in range(ty + BL + 2, RAIL_Y):
                for j, ch in enumerate('lwhlmddo'):
                    put(idx, c - 4 + j, y, PA['d'] if (y - ty) % 4 == 1 and ch != 'o' else PA[ch])
            # collar (blade base), as wide as the blade
            for x in range(c - 7, c + 7):
                put(idx, x, ty + BL, PA['o'])
                put(idx, x, ty + BL + 1, PA['w'] if x < c - 4 else PA['h'] if x < c - 1 else PA['l'] if x < c + 2 else PA['m'] if x < c + 5 else PA['d'])
            # blade: white rim on the lit edge, lit left face, bright centre ridge, shadow right face, bright rim on the far edge
            for j, hw in enumerate(BLADE_HW):
                y = ty + j
                for x in range(c - hw, c + hw):
                    if j == 0 or x == c - hw:
                        ch = 'w'
                    elif x == c + hw - 1:
                        ch = 'h'
                    elif x == c - 1 and hw >= 3:
                        ch = 'h'
                    elif x < c:
                        ch = 'l'
                    elif x == c and hw >= 4:
                        ch = 'm'
                    else:
                        ch = 'd'
                    put(idx, x, y, PA[ch])
        # housing: one riveted sleeve block per piston, lit lip on top, then the rail
        for y in range(SLEEVE_Y, H):
            for x in range(W):
                rel = (x % 16) - 8
                if y < RAIL_Y:
                    if rel in (-8, 7):
                        c = 'o'
                    elif y == SLEEVE_Y:
                        c = 'w' if rel < -2 else 'h' if rel < 4 else 'l'
                    elif rel == -7:
                        c = 'h'
                    elif rel == 6:
                        c = 'g'
                    elif y == SLEEVE_Y + 1:
                        c = 'l' if rel < 0 else 'm'
                    else:
                        c = 'm' if rel < 0 else 'd'
                    if rel in (-5, 4) and y == SLEEVE_Y + 2:
                        c = 'w' if rel < 0 else 'l'
                    if rel in (-5, 4) and y == SLEEVE_Y + 3:
                        c = 'o'
                elif y == RAIL_Y:
                    c = 'h'
                elif y in (RAIL_Y + 1, RAIL_Y + 2):
                    c = 'g'
                elif y == RAIL_Y + 3:
                    c = 'o'
                elif y <= RAIL_Y + 7:
                    c = 'y' if ((x + (y - RAIL_Y)) // 4) % 2 == 0 else 'k'
                    if c == 'y' and y == RAIL_Y + 7:
                        c = 'Y'
                elif y == RAIL_Y + 8:
                    c = 'd'
                else:
                    c = 'o'
                idx[y, x] = PA[c]
        # lamp bars in the seams between sleeves: lit while the piston to their right is thrusting or ringing
        for i in range(4):
            c, ty, e, v = tips[i]
            on = v > 1.0 or (e > 0.9 and abs(v) > 0.6)
            for x in (c - 9, c - 8):
                for y in range(SLEEVE_Y + 1, RAIL_Y - 1):
                    put(idx, x, y, PA['R' if on else 'r'])
                put(idx, x, RAIL_Y + 1, PA['R' if on else 'r'])
                put(idx, x, RAIL_Y + 2, PA['Y' if on else 'o'])
        # electric arc between two raised neighbours: 1 px white core, cyan inner halo, violet outer halo, forks
        for i in range(4):
            c0, t0, e0, _ = tips[i]
            c1, t1, e1, _ = tips[(i + 1) % 4]
            if e0 > 0.8 and e1 > 0.8:
                core, forks = arc_path(f, i, c0 + 2, t0 + 2, c0 + 13, t1 + 2)
                free = (0,)
                for (x, y) in core:
                    for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1), (0, -2), (0, 2)):
                        put(idx, x + dx, y + dy, PA['A'], only=free)
                for fork in forks:
                    put(idx, fork[-1][0], fork[-1][1] + (1 if fork[-1][1] > fork[0][1] else -1), PA['A'], only=free)
                for (x, y) in core:
                    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                        put(idx, x + dx, y + dy, PA['a'], only=(0, PA['A']))
                for fork in forks:
                    for k, (x, y) in enumerate(fork):
                        put(idx, x, y, PA['w' if k < 2 else 'a'], only=(0, PA['A'], PA['a']))
                for (x, y) in core:
                    put(idx, x, y, PA['w'], only=(0, PA['a'], PA['A']))
        # slam sparks: thrown from the sleeve lip when a piston hits its first overshoot peak, ballistic
        for i in range(4):
            c = 8 + 16 * i
            for age_f in range(0, 4):
                ff = (f - 4 * i - age_f) % NF
                if ff != 2:
                    continue
                t = age_f / NF
                for k, (vx, vy) in enumerate(((-70, -95), (62, -110), (-110, -40), (104, -52))):
                    x = c + (-7 if vx < 0 else 7) + vx * t
                    y = SLEEVE_Y - 1 + vy * t + 0.5 * 900 * t * t
                    if y < SLEEVE_Y:
                        col = PA['w' if age_f == 0 else 's' if age_f < 3 else 'R']
                        put(idx, x, y, col, only=(0,))
                        if age_f < 2:
                            put(idx, x, y - 1, col, only=(0,))
        frames.append(idx)
    return frames, {}


# ================================================================ B: fire (advected temperature field)
PB = Pal({
    'o': (34, 6, 22),      # coal outline
    'c': (52, 18, 40),     # coal dark
    'C': (92, 40, 60),     # coal lit
    'D': (132, 14, 44),    # flame edge, deep crimson
    'r': (226, 44, 36),    # red
    'O': (252, 122, 30),   # orange
    'Y': (255, 222, 84),   # yellow
    'w': (255, 252, 222),  # white-hot
    'y': (255, 176, 46),   # spark amber
})
SPOTS = [(7, 5.4, 2, 0.00, 1.00), (19, 2.4, 3, 0.37, 0.62), (27, 3.4, 2, 0.61, 0.84),
         (41.5, 4.6, 2, 0.13, 1.00), (50, 2.2, 3, 0.55, 0.58), (58.5, 3.0, 3, 0.80, 0.74)]  # x, width, puffs/loop, phase, strength
FCOOL = 3.0
FMODES = [(1, 30, 1, 2, 10, 0.0), (2, 22, -1, 2, 13, 1.3), (3, 16, 2, 3, 11, 2.1), (5, 12, -2, 3, 8, 4.0)]
# n (x harmonics per tile), vertical wavelength px, time harmonics of the sideways drift, of the upward drift, speed px/loop, phase


def fire_source(x, t):
    s = 0.28 + 0.06 * np.sin(TAU * (3 * x / W + t))
    for (x0, wd, m, ph, st) in SPOTS:
        amp = st * (0.58 + 0.42 * sin(TAU * (m * t + ph)))
        xc = x0 + 1.5 * sin(TAU * (t + 3 * ph))
        s = np.maximum(s, amp * np.exp(-(wrapd(x, xc) / wd) ** 2))
    return s


def fire_vel(X, Y, t, T):
    ramp = np.clip((27 - Y) / 12.0, 0, 1)
    u = 0
    v = 0
    for (n, ly, m, r, A, ph) in FMODES:
        kx, ky = TAU * n / W, TAU / ly
        ax = kx * X + TAU * m * t + ph
        ay = ky * Y + TAU * r * t
        u = u + A * np.sin(ax) * np.cos(ay)
        v = v - A * (kx / ky) * np.cos(ax) * np.sin(ay)
    return u * ramp, v * ramp - (52 + 70 * T)


def sim_fire():
    S, sub = 3, 8
    gw, gh = W * S, H * S
    X, Y = np.meshgrid((np.arange(gw) + 0.5) / S, (np.arange(gh) + 0.5) / S)
    steps = NF * sub
    dt = 1.0 / steps
    T = np.zeros((gh, gw))
    src_rows = (Y > 23.0) & (Y < 28.5)
    prev = None
    for loop in range(12):
        out = []
        for i in range(steps):
            t = i * dt
            if i % sub == 0:
                out.append(T.copy())
            u, v = fire_vel(X, Y, t, blur_x(T, 1.5))
            T = advect(T, u, v, dt, X, Y, S)
            T = blur_y(blur_x(T, 0.26), 0.2)
            T = np.maximum(T - dt * (FCOOL + 5.0 * np.clip((11 - Y) / 9.0, 0, 1)), 0)   # cold air entrained higher up
            s = fire_source(X, t)
            T = np.where(src_rows, np.maximum(T, s), T)
            T[Y >= 28.5] = 0
        err = max(np.abs(a - b).max() for a, b in zip(prev, out)) if prev is not None else 1.0
        prev = out
        if err < 1e-5:
            break
    assert err < 1e-3, ('fire loop not periodic', err)
    return [o.reshape(H, S, W, S).mean((1, 3)) for o in prev]


LUMPS = [(3.0, 28.6, 3.9, 3.0), (9.6, 28.0, 3.6, 3.3), (16.2, 28.8, 4.0, 2.8), (22.4, 28.2, 3.4, 3.2), (28.6, 28.7, 3.8, 3.0),
         (35.0, 28.0, 3.6, 3.4), (41.2, 28.8, 3.7, 2.8), (47.6, 28.2, 3.9, 3.2), (54.0, 28.7, 3.6, 3.0), (60.2, 28.1, 3.5, 3.3)]
SPARKS = [(0, 0.05, 0.62, 14), (1, 0.30, 0.55, -10), (2, 0.52, 0.70, 6), (3, 0.71, 0.58, -16), (4, 0.16, 0.66, 12),
          (5, 0.88, 0.60, -6), (1, 0.80, 0.50, 18), (3, 0.22, 0.64, 8), (5, 0.44, 0.56, -14)]  # spot, birth, life, vx0


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


def render_fire():
    Ts = sim_fire()
    frames = []
    yy = np.arange(H)[:, None] + 0.5
    for f in range(NF):
        t = f / NF
        T = blur_y(blur_x(Ts[f], 0.9), 0.7)
        Tc = blur_y(blur_x(Ts[f], 1.5), 1.1)        # cores are cut from a smoother field: round shapes, no blocks
        idx = np.zeros((H, W), np.uint8)
        inside = np.ones((H, W), bool)
        for th, ch, fld in ((0.075, 'D', T), (0.21, 'r', T), (0.40, 'O', T), (0.57, 'Y', Tc), (0.76, 'w', Tc)):
            inside = smooth_mask(fld > th) & inside
            idx[inside] = PB[ch]
        idx = despeckle(idx)
        # coal bed: lumps with rims lit by the heat directly above; cracks between lumps glow with the same heat
        heat = fire_source(XS, t)
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
                    if best > 0.62 and up < 0.25:
                        c = 'Y' if hx > 0.9 else 'O' if hx > 0.72 else 'r' if hx > 0.5 else 'D'
                    elif up + 0.6 * lf < -0.15:
                        c = 'C'
                    elif best > 0.62:
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
        for (spot, t0, life, vx) in SPARKS:
            age = (t - t0) % 1.0
            if age < life:
                x, y = spark_pos(spot, t0, age)
                a = age / life
                put(idx, x, y, PB['w' if a < 0.2 else 'Y' if a < 0.5 else 'y' if a < 0.8 else 'r'], only=(0, PB['D']))
        frames.append(idx)
    return frames, {}


# ================================================================ C: water (Gerstner waves, deep-water dispersion)
PC = Pal({
    'o': (8, 8, 34),       # abyss (violet black)
    'n': (18, 26, 88),     # deep navy
    'b': (22, 66, 150),    # blue
    'B': (40, 122, 208),   # light blue
    'c': (104, 204, 240),  # cyan skin
    'f': (190, 236, 252),  # foam shade
    'w': (255, 255, 255),  # foam white
    'e': (255, 224, 64),   # lurker eye
    'E': (240, 92, 40),    # lurker eye rim
    'k': (26, 30, 52),     # fin dark
    'g': (74, 88, 120),    # fin mid
    'G': (156, 172, 200),  # fin lit edge
})
# n crests per tile, m cycles per loop, direction, amplitude px, phase.  omega^2 = g k  <=>  m = sqrt(n): (1,1) (4,2) (9,3)
WAVES = [(1, 1, +1, 3.2, 0.0), (4, 2, +1, 1.2, 1.1), (9, 3, +1, 0.3, 2.3), (1, 1, -1, 1.0, 0.6), (4, 2, -1, 0.4, 3.0)]
QS, WY0, MW = 0.6, 12.0, 1024
CAUS_R, CAUS_T, CAUS_T2 = 1.1, 1.42, 1.95     # ray refraction gain, cel thresholds of the ray density
FOAM_J = 0.74


def water_state(t):
    x0 = np.arange(MW) * W / MW
    dx = np.zeros(MW)
    y = np.zeros(MW)
    J = np.ones(MW)
    for n, m, d, a, ph in WAVES:
        k = TAU * n / W
        th = d * k * x0 - TAU * m * t + ph
        dx -= d * QS * a * np.sin(th)
        y += a * np.cos(th)
        J -= QS * a * k * np.cos(th)
    return x0 + dx, y, J


def deep_shift(t, depth):
    """Wave displacement at a depth: each component decays as exp(-k depth), so only the long swell reaches down."""
    s = np.zeros(W)
    for n, m, d, a, ph in WAVES:
        k = TAU * n / W
        s += a * np.exp(-k * depth) * np.cos(d * k * XS - TAU * m * t + ph)
    return s


def sim_water():
    sub = 8
    steps = NF * sub
    dt = 1.0 / steps
    F = np.zeros(MW)
    out = None
    for loop in range(4):
        out, peak = [], []
        for i in range(steps):
            t = i * dt
            xs, y, J = water_state(t)
            src = np.clip((FOAM_J - J) / FOAM_J, 0, 1)
            if i % sub == 0:
                out.append((xs, y, J, F.copy()))
            j = int(np.argmax(src))
            peak.append((src[j], t, xs[j] % W, WY0 - y[j]))
            F = F + dt * 30.0 * src * (1 - F) - dt * F / 0.2
            F = blur_x(F, 6.0)
    # splash events: the three strongest breaking moments of the loop, at least 0.2 loop apart
    ev = []
    for s, t, x, y in sorted(peak, reverse=True):
        if s > 0.25 and all(min(abs(t - e[0]), 1 - abs(t - e[0])) > 0.2 for e in ev):
            ev.append((t, x, y))
        if len(ev) == 2:
            break
    return out, ev


FO1, FO2, FO3 = 0.08, 0.18, 0.30
DROPS = [(14, -62, 3), (31, -78, 2), (-10, -50, 2), (-27, -70, 3), (4, -92, 2)]   # vx, vy px/loop, size px; gravity below
GRAV_W = 340.0
CROWN = [   # splash crown, three frames, bottom row sits on the surface
    ['.w...w.', 'ww.w.ww', 'fwwwwwf'],
    ['w.....w', 'w..w..w', '.w.w.w.', '.fwwwf.'],
    ['w.......w', '.........', '.w..w..w.', '..f...f..'],
]
FLOOR_Y = 30
ROCKS = [(5.0, 4.5, 4.0), (21.0, 7.0, 2.4), (36.5, 3.2, 5.6), (50.0, 8.0, 3.0), (60.0, 2.5, 2.0)]   # centre x, half width, height px
WEEDS = [(9, 7, 0.00), (33, 6, 0.35), (39, 9, 0.60), (56, 8, 0.80)]                                  # root x, length px, sway phase
BUBS = [(36.5, 0.00, 2), (37.5, 0.42, 1), (36.0, 0.71, 2), (5.0, 0.20, 2), (5.5, 0.63, 1), (50.0, 0.88, 1), (21.0, 0.50, 2)]  # vent x, birth, size


def rock_top():
    hgt = np.zeros(W)
    for (cx, hw, hh) in ROCKS:
        hgt = np.maximum(hgt, hh * np.clip(1 - (wrapd(XS, cx) / hw) ** 2, 0, 1))
    return FLOOR_Y - np.round(hgt).astype(int)


def render_water():
    states, events = sim_water()
    frames, surf = [], []
    rtop = rock_top()
    for f in range(NF):
        t = f / NF
        xs, y, J, F = states[f]
        h = blur_x(np.interp(XS, xs, y, period=W), 0.8)
        Fp = np.interp(XS, xs, F, period=W)
        slope = (np.roll(h, -1) - np.roll(h, 1)) / 2
        ysurf = WY0 - h
        top = np.floor(ysurf + 0.5).astype(int)
        tb = 1.2 + np.clip(7.0 * blur_x(slope, 1.0), 0, 3.6)
        yb2 = 20.0 - deep_shift(t, 7.0)
        # caustics: rays refracted by the surface slope, counted where they land (real ray density)
        hs = np.interp(xs % W, XS, blur_x(h, 1.6), period=W)        # smoothed height at the Lagrangian samples
        sl = np.gradient(hs) / np.gradient(np.unwrap(xs % W, period=W))
        wgt = np.gradient(np.unwrap(xs % W, period=W))
        I = np.zeros((H, W))
        for yrow in range(H):
            D = yrow + 0.5 - (WY0 - y)
            ok = D > 0
            xl = (xs + D * (0.30 + CAUS_R * sl)) % W
            I[yrow] = np.bincount(np.floor(xl[ok]).astype(int) % W, weights=wgt[ok], minlength=W)[:W]
        I = blur_y(blur_x(I, 1.3), 0.8)
        I = I / max(I[20:].mean(), 1e-6)
        idx = np.zeros((H, W), np.uint8)
        body = np.zeros((H, W), bool)
        for x in range(W):
            for yy in range(max(top[x], 0), H):
                d = yy - top[x]
                if d == 0:
                    c = 'c'
                elif d <= tb[x]:
                    c = 'B'
                elif yy + 0.5 < yb2[x]:
                    c = 'b'
                else:
                    c = 'n'
                idx[yy, x] = PC[c]
                body[yy, x] = d > tb[x] + 1
        idx = despeckle(idx)
        # caustic light shapes: where the refracted rays bunch, the water is one shade lighter (hard shapes)
        ca = smooth_mask(I > CAUS_T) & body
        cb = smooth_mask(I > CAUS_T2) & body
        idx[ca & (idx == PC['n'])] = PC['b']
        idx[ca & (idx == PC['b']) & ~cb] = PC['b']
        idx[cb & (idx == PC['b'])] = PC['B']
        idx[cb & ca & (idx == PC['n'])] = PC['b']
        idx = despeckle(idx)
        # lit wave backs: the face turned to the light (upper left) gets a second row of skin colour
        for x in range(W):
            if slope[x] < -0.22 and 0 <= top[x] + 1 < H:
                idx[top[x] + 1, x] = PC['c']
        # deep silhouettes: rocks on the floor, weed swaying with the swell that reaches down there
        water = (PC['n'], PC['b'], PC['B'])
        for x in range(W):
            for yy in range(rtop[x], H):
                idx[yy, x] = PC['o']
        sway = deep_shift(t, 14.0)
        for (wx, wl, ph) in WEEDS:
            for k in range(wl):
                yy = rtop[wx] - 1 - k
                off = (k / wl) ** 1.3 * (2.4 * sin(TAU * (t + ph) - 0.3 * k) + 1.2 * sway[wx])
                put(idx, wx + off, yy, PC['o'], only=water)
                if k < wl // 2:
                    put(idx, wx + off + 1, yy, PC['o'], only=water)
        # bubbles from the rock vents: buoyancy against drag (speed rises to terminal), wobble, gone at the surface
        for (vx, t0, sz) in BUBS:
            age = (t - t0) % 1.0
            ya = rtop[int(vx)] - 1 - 30.0 * (age - 0.18 * (1 - np.exp(-age / 0.18)))
            xa = vx + 1.4 * sin(TAU * 2 * age + vx)
            if ya > top[int(xa) % W] + 3:
                if sz == 2 and age > 0.22:
                    put(idx, xa, ya, PC['c'], only=water)
                    put(idx, xa + 1, ya, PC['B'], only=water)
                    put(idx, xa, ya + 1, PC['B'], only=water)
                    put(idx, xa + 1, ya + 1, PC['B'], only=water)
                else:
                    put(idx, xa, ya, PC['B'], only=water)
        # foam: carried by the water parcels (not by the crest), so it is left on the back of the wave and decays
        for x in range(W):
            fo = Fp[x]
            tp = top[x]
            if fo > FO1 and 0 <= tp < H:
                idx[tp, x] = PC['w' if fo > FO2 else 'f']
                if fo > FO2:
                    put(idx, x, tp + 1, PC['f'])
                if fo > FO3:
                    put(idx, x, tp - 1, PC['w'])
                    put(idx, x, tp + 1, PC['w'])
                    put(idx, x, tp + 2, PC['f'])
        # splash: a crown where the wave breaks hardest, then 2-3 px droplets on ballistic arcs
        for (t0, x0, y0) in events:
            age = (t - t0) % 1.0
            k = int(age * NF + 1e-6)
            if k < len(CROWN):
                art = CROWN[k]
                by = int(top[int(x0) % W]) - 1
                for r, row in enumerate(art):
                    for q, ch in enumerate(row):
                        if ch != '.':
                            put(idx, int(x0) - len(row) // 2 + q, by - (len(art) - 1 - r), PC[ch])
            for vx, vy, sz in DROPS:
                x = x0 + vx * age
                yd = y0 - 2 + vy * age + 0.5 * GRAV_W * age * age
                if age > 0.03 and yd + sz < ysurf[int(x) % W]:
                    hi = PC['w']
                    lo = PC['w' if vy + GRAV_W * age < 0 else 'f']
                    if sz == 2:
                        shape = ((0, 0, hi), (1, 0, hi), (0, 1, lo), (1, 1, PC['f']))
                    else:
                        shape = ((1, 0, hi), (0, 1, hi), (1, 1, hi), (2, 1, lo), (1, 2, PC['f']), (0, 2, lo))
                    for (dx, dy, c) in shape:
                        put(idx, x + dx, yd + dy, c, only=(0,))
        frames.append(idx)
        surf.append(top)
    return frames, {'surf': surf}


FIN = [(2, 3), (2, 4), (2, 5), (3, 6), (3, 7), (3, 8), (4, 9), (4, 10), (4, 11), (3, 12), (2, 13), (1, 14)]


def lurker(f, top, x0):
    """Separate sprite (not in the tile): dorsal fin riding the simulated surface, body shadow and eyes below.
    Returns [(x, y, key, mode)] in screen-strip coordinates; mode 'u' = only over open water."""
    px = []
    cols = [(x0 + i) % W for i in range(2, 13)]
    base = int(round(float(np.mean(top[cols])))) + 1
    lean = int(np.sign(int(top[(x0 + 13) % W]) - int(top[(x0 + 1) % W])))
    for i, (a, b) in enumerate(FIN):
        y = base - len(FIN) + i
        sh = lean if i < 4 else 0
        for x in range(a, b + 1):
            c = 'G' if x == a or i == 0 else 'k' if x >= b - 1 else 'g'
            if (x, i) in ((6, 6), (7, 7)):
                c = 'k'
            px.append((x0 + x + sh, y, c, 'a'))
    wake = [[(-1, 0, 'w'), (0, -1, 'w'), (0, 0, 'f'), (15, 0, 'w'), (16, 0, 'f'), (17, 1, 'w')],
            [(-2, 0, 'f'), (-1, -1, 'w'), (0, 0, 'w'), (15, -1, 'w'), (16, 0, 'w'), (18, 1, 'f')]][(f // 2) % 2]
    for (x, y, c) in wake:
        px.append((x0 + x, base + y, c, 'a'))
    cy = base + 8.5
    for y in range(base + 3, base + 15):
        for x in range(-12, 28):
            q = ((x - 7.5) / 17.0) ** 2 + ((y + 0.5 - cy) / 5.0) ** 2
            if q <= 1:
                px.append((x0 + x, y, 'o', 'u'))
    blink = f in (10, 11)
    for ex in (2, 10):
        ey = base + 7
        if blink:
            px += [(x0 + ex + i, ey + 1, 'E', 'a') for i in range(3)]
        else:
            px += [(x0 + ex, ey, 'E', 'a'), (x0 + ex + 1, ey, 'e', 'a'), (x0 + ex + 2, ey, 'e', 'a'), (x0 + ex + 3, ey, 'E', 'a'),
                   (x0 + ex, ey + 1, 'E', 'a'), (x0 + ex + 1, ey + 1, 'e', 'a'), (x0 + ex + 2, ey + 1, 'E', 'a')]
    return px


def put_lurker(im, f, top, sx, oy):
    px = im.load()
    water = {PC.d[k] for k in 'nbB'}
    for (x, y, c, mode) in lurker(f, top, sx % W):
        X, Y = x - (sx % W) + sx, oy + y
        if not (0 <= X < im.width and 0 <= Y < im.height):
            continue
        if mode == 'u' and px[X, Y][:3] not in water:
            continue
        px[X, Y] = PC.d[c] + (255,)


# ================================================================ D: lava (damped wave PDE + convection + crust conveyor)
PD = Pal({
    'o': (22, 6, 20),      # crust black
    'k': (58, 18, 36),     # crust dark
    'K': (110, 44, 50),    # crust mid
    'Q': (196, 112, 84),   # crust lit top edge
    'H': (246, 190, 140),  # crust highlight (plate end facing the light)
    'P': (92, 8, 46),      # coldest lava (maroon, hue to violet)
    'D': (150, 18, 34),    # deep red
    'r': (222, 50, 28),    # red
    'O': (250, 124, 26),   # orange
    'y': (255, 200, 56),   # yellow
    'Y': (255, 248, 190),  # white-hot
})
LY0 = 12.0
NODES = [8.0, 19.0, 43.0, 55.0, 72.0]       # upwelling, downwelling, upwelling, downwelling, (wrap)
BUB = [(8.0, 7.0, 6, 1.0), (43.0, 4.0, 13, 0.66)]   # x, max radius, burst frame, droplet scale (uneven sizes and timing)
MINI = [(30.5, 2, 2.4), (51.0, 10, 2.0), (63.0, 5, 1.6)]   # blisters: x, pop-start frame, radius
SIDE = [(30.0, 3.0, 0.62, 0.3), (62.0, 2.4, 0.5, 0.8)]      # extra floor heat (no bubble): x, width, strength, phase
LDROPS = [(-24, -60), (-10, -82), (4, -92), (13, -72), (26, -54), (-34, -42)]
GRAV_L = 400.0
CRUST_U, BODY_U, DEPTH = 7.0, 24.0, 20.0
BARE = 2.6


def lava_us(x):
    """Surface flow profile (unit amplitude): away from upwellings, into downwellings."""
    x = np.asarray(x, float)
    xm = (x - NODES[0]) % W + NODES[0]
    u = np.zeros_like(xm)
    for i in range(4):
        a, b = NODES[i], NODES[i + 1]
        m = (xm >= a) & (xm < b)
        s = np.sin(pi * (xm - a) / (b - a))
        u = np.where(m, s if i % 2 == 0 else -s, u)
    return u


def crust_tables():
    """Per pixel: crust age (travel time from the nearest upwelling's bare edge), plus per flank the travel-time
    table used to place the cracks (cracks are material lines released once per loop when the bubble bursts)."""
    fine = np.arange(0, W, 0.02)
    age = np.full(len(fine), -1.0)
    flanks = []
    for i in range(4):
        a, b = NODES[i], NODES[i + 1]
        up, dn = (a, b) if i % 2 == 0 else (b, a)
        sg = 1 if dn > up else -1
        xs = up + sg * np.arange(BARE, abs(dn - up) - 0.9, 0.02)
        sp = CRUST_U * (abs(dn - up) / 13.0) * np.abs(lava_us(xs))     # wide rolls run faster: longer plates
        tt = np.concatenate([[0], np.cumsum(0.02 / sp[:-1])])
        flanks.append((xs, tt, BUB[0 if up % W == NODES[0] else 1][2] / NF))
        age[np.round((xs % W) / 0.02).astype(int) % len(fine)] = tt
    agep = np.array([np.max(age[int(x / 0.02):int((x + 1) / 0.02)]) for x in range(W)])
    return agep, flanks


def sim_lava_surface():
    """1D damped wave equation, periodic: h_tt = c^2 h_xx - gamma h_t + mu h_xxt + bubble-burst impulses."""
    n, c, gam, mu = 256, 34.0, 5.5, 5.0
    dx = W / n
    x = (np.arange(n) + 0.5) * dx
    steps = 3200
    dt = 1.0 / steps
    h = np.zeros(n)
    v = np.zeros(n)
    prev = None
    for loop in range(8):
        out = []
        for i in range(steps):
            if i % (steps // NF) == 0:
                out.append(h.copy())
            for (bx, R, fb, sc) in BUB:
                if i == fb * (steps // NF):
                    imp = np.exp(-(wrapd(x, bx) / (0.75 * R)) ** 2)
                    v -= 7.5 * R * (imp - imp.mean())      # zero-mean: volume is conserved, so the loop closes
            lap = lambda a: (np.roll(a, 1) + np.roll(a, -1) - 2 * a) / dx ** 2
            v += dt * (c * c * lap(h) - gam * v + mu * lap(v))
            h += dt * v
        if prev is not None and loop == 7:
            err = max(np.abs(a - b).max() for a, b in zip(prev, out))
            assert err < 1e-3, ('lava surface not periodic', err)
        prev = out
    return [o.reshape(W, 4).mean(1) for o in prev]


def sim_lava_body(agep):
    """Temperature advected round the convection rolls under the surface; heat enters in pulses under the
    upwellings, leaves through the surface (faster under old crust)."""
    S, sub = 2, 4
    gw, gh = W * S, int(DEPTH) * S
    X, Dp = np.meshgrid((np.arange(gw) + 0.5) / S, (np.arange(gh) + 0.5) / S)
    def vel(t):
        # convection rolls; below the crust they sway sideways (time-periodic), so the plumes snake and shed blobs
        Xs = X - (3.6 * np.sin(TAU * (t + X / W) + Dp / 5.0) + 2.0 * np.sin(TAU * (2 * t - 2 * X / W) - Dp / 3.5 + 1.0)) * np.clip(Dp / 6.0, 0, 1)
        us = lava_us(Xs)
        dus = (lava_us(Xs + 0.05) - lava_us(Xs - 0.05)) / 0.1
        return (BODY_U * us * np.cos(pi * Dp / DEPTH),
                -BODY_U * dus * (DEPTH / pi) * np.sin(pi * Dp / DEPTH))
    cool = np.repeat(np.clip(agep, 0, 2.0), S)[None, :] * np.exp(-Dp / 2.5)
    steps = NF * sub
    dt = 1.0 / steps
    T = np.full((gh, gw), 0.3)
    prev = None
    for loop in range(40):
        out = []
        for i in range(steps):
            t = i * dt
            if i % sub == 0:
                out.append(T.copy())
            u, vd = vel(t)
            T = advect(T, u, vd, dt, X, Dp, S)
            T = blur_y(blur_x(T, 0.4), 0.3)
            T = T - dt * (0.5 * T + 1.2 * cool * T)
            s = np.zeros_like(X)
            for (bx, R, fb, sc) in BUB:
                ph = (t - fb / NF + 0.55) % 1.0             # pulse leaves the floor about half a loop before the burst
                amp = 0.70 + 0.34 * np.exp(-((ph - 0.5) / 0.16) ** 2)
                s = np.maximum(s, (0.80 + 0.20 * sc) * amp * np.exp(-(wrapd(X, bx) / (0.7 * R + 1.4)) ** 2))
            for (sx, sw, st, sph) in SIDE:
                s = np.maximum(s, st * (0.75 + 0.25 * sin(TAU * (t + sph))) * np.exp(-(wrapd(X, sx) / sw) ** 2))
            T = np.where(Dp > DEPTH - 2.5, np.maximum(T, s), T)
        if prev is not None and loop == 39:
            err = max(np.abs(a - b).max() for a, b in zip(prev, out))
            assert err < 1e-2, ('lava body not periodic', err)
        prev = out
    return [o.reshape(gh // S, S, W, S).mean((1, 3)) for o in prev]


def render_lava():
    agep, flanks = crust_tables()
    ripple = sim_lava_surface()
    body = sim_lava_body(agep)
    frames = []
    for f in range(NF):
        t = f / NF
        h = (0.9 * np.cos(TAU * (XS / W - t)) + 0.5 * np.cos(TAU * (2 * XS / W + t) + 1.0) + ripple[f])
        ysurf = LY0 - h
        top = np.floor(ysurf + 0.5).astype(int)
        T = blur_y(blur_x(body[f], 0.8), 0.6)
        idx = np.zeros((H, W), np.uint8)
        for x in range(W):
            for yy in range(max(top[x], 0), H):
                d = min(yy - top[x], T.shape[0] - 1)
                v = T[d, x]
                idx[yy, x] = PD['P' if v < 0.13 else 'D' if v < 0.27 else 'r' if v < 0.47 else 'O' if v < 0.70 else 'y' if v < 0.93 else 'Y']
        idx = despeckle(idx)
        # crack positions this frame
        cracks = []
        for (xs, tt, t0) in flanks:
            a0 = (t - t0) % 1.0
            for j in range(12):
                a = a0 + j
                if a < tt[-1]:
                    cracks.append((float(np.interp(a, tt, xs)) % W, a))
        heat = [0.5 + 0.5 * cos(TAU * (t - fb / NF)) for (bx, R, fb, sc) in BUB]
        for x in range(W):
            ag = agep[x]
            tp = top[x]
            if ag < 0:
                near_up = min(abs(wrapd(x + 0.5, b[0])) for b in BUB) < BARE + 0.5
                if near_up:                          # bare melt over the upwelling
                    put(idx, x, tp, PD['Y'])
                    put(idx, x, tp + 1, PD['y'])
                else:                                # downwelling: plates jam, pile up and tip under
                    for j, ch in enumerate('QKkokko'):
                        put(idx, x, tp - 4 + j, PD[ch])
                continue
            ck = min(cracks, key=lambda c: abs(wrapd(x + 0.5, c[0]))) if cracks else None
            dck = abs(wrapd(x + 0.5, ck[0])) if ck else 99
            wl = wrapd(x + 0.5, ck[0]) if ck else 99
            cw = 0.6 if (ck and ck[1] > 1.6) else 1.1
            if ag < 0.3:                             # fresh skin
                put(idx, x, tp, PD['y'])
                put(idx, x, tp + 1, PD['O'])
            elif dck < cw:                           # crack: the melt shows through
                put(idx, x, tp, PD['Y' if heat[0] > 0.6 and ck[1] < 1.2 else 'y'])
                put(idx, x, tp + 1, PD['O'])
            else:                                    # plate: thicker with age, lit top edge, highlight on the end facing the light
                lit = 0 < wl < 3.4
                dark = -2.2 < wl < 0
                if ag < 0.7:
                    rows, y0 = ('Qko' if lit else 'Kko'), tp - 1
                elif ag < 1.5:
                    rows, y0 = ('HQKko' if lit else 'KKkko' if dark else 'QKkko'), tp - 2
                else:
                    rows, y0 = ('HQKkko' if lit else 'KKkkko' if dark else 'QKkkko'), tp - 3
                for j, ch in enumerate(rows):
                    put(idx, x, y0 + j, PD[ch])
        # blisters: small gas bubbles that lift the crust between the big ones, at uneven places and times
        for (mx, mf, mr) in MINI:
            g = (f - mf) % NF
            xc = int(mx)
            tpc = int(top[xc])
            if g < 4:
                e = (g + 1) / 4.0
                r = mr * (0.5 + 0.5 * e)
                cy = tpc - 1 + r * (0.5 - 0.9 * e)
                for yy in range(int(cy - r) - 1, tpc + 1):
                    for x in range(int(mx - r) - 1, int(mx + r) + 2):
                        dxp, dyp = x + 0.5 - mx, yy + 0.5 - cy
                        dist = sqrt(dxp * dxp + dyp * dyp)
                        if dist <= r:
                            put(idx, x, yy, PD['Y' if dist > r - 1.1 and dxp + dyp < 0 else 'y' if dist > r - 1.1 else 'O'])
            elif g in (4, 5):
                k = g - 4
                for (dx, dy) in ((-2 - k, -4 - k), (1, -5 - 2 * k), (3 + k, -3 - k)):
                    put(idx, mx + dx, tpc + dy, PD['Y' if k == 0 else 'O'], only=(0,))
                for x in (xc - 1, xc):
                    put(idx, x, tpc - 1, PD['y' if k == 0 else 'O'])
                    put(idx, x, tpc, PD['Y' if k == 0 else 'y'])
        # bubbles: swell to a dome, burst into a crown, throw droplets
        for bi, (bx, R, fb, sc) in enumerate(BUB):
            g = (f - (fb - 6)) % NF
            xc = int(bx)
            tpc = int(top[xc])
            if g < 6:
                e = (g + 1) / 6.0
                r = R * (0.35 + 0.65 * e * e * (3 - 2 * e))
                cy = tpc + r * (0.70 - 1.0 * e)
                for yy in range(int(cy - r) - 1, tpc + 2):
                    for x in range(int(bx - r) - 1, int(bx + r) + 2):
                        dxp, dyp = x + 0.5 - bx, yy + 0.5 - cy
                        dist = sqrt(dxp * dxp + dyp * dyp)
                        if dist > r or yy > top[x % W]:
                            continue
                        nx, ny = dxp / r, dyp / r
                        if dist > r - 1.15:
                            c = 'Y' if (nx + ny < -0.25) else 'y' if ny < 0.1 or nx < 0 else 'O'
                        elif nx + 0.8 * ny > 0.55:
                            c = 'r' if e < 0.7 else 'O'
                        elif abs(nx + 0.42) < 0.2 and abs(ny + 0.42) < 0.2 and r >= 3:
                            c = 'Y'
                        else:
                            c = 'O' if e < 0.55 else 'y'
                        put(idx, x, yy, PD[c])
            elif g in (6, 7):
                k = g - 6
                hgt = int(round(R * (0.75 - 0.4 * k)))
                for side in (-1, 1):
                    for j in range(hgt):
                        xx = bx + side * (R - 0.6 + 0.35 * j + 1.2 * k)
                        put(idx, xx, tpc - 1 - j + k, PD['Y' if j >= hgt - 2 else 'y'])
                        if j < hgt - 1:
                            put(idx, xx - side, tpc - 1 - j + k, PD['y' if k == 0 else 'O'])
                if k == 0:
                    for x in range(int(bx - R) + 2, int(bx + R) - 1):
                        put(idx, x, top[x % W], PD['Y'])
                        put(idx, x, top[x % W] + 1, PD['Y'])
            age = ((f - fb) % NF) / NF
            if age <= 0.6:
                for di, (vx, vy) in enumerate(LDROPS[:6 if sc == 1.0 else 4]):
                    x = bx + sc * vx * age
                    y = LY0 - 2 + sc * vy * age + 0.5 * GRAV_L * age * age
                    if y < ysurf[int(x) % W] - 0.5 and age > 0:
                        c = PD['Y' if age < 0.1 else 'y' if age < 0.22 else 'O' if age < 0.36 else 'r']
                        put(idx, x, y, c, only=(0,))
                        if di in (1, 2, 3) and age < 0.3:
                            put(idx, x + 1, y, c, only=(0,))
                            put(idx, x, y + 1, c, only=(0,))
                            put(idx, x + 1, y + 1, PD['O' if age < 0.22 else 'r'], only=(0,))
        frames.append(idx)
    return frames, {}


# ================================================================ cast light (fire, lava) on the scene above
# Three warm colours added to the CITY palette; hard nested shapes, no ramp: a low band on the building face near the
# hazard, a rim on the building's vertical edges, a rim on the underside of the nearest islands. The level (1..3) of
# each 16 px column follows the simulated brightness of the hazard column below it; the hazard repeats every 64 px,
# so the light does too: 4 columns x 16 frames of levels per hazard.
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
    sig = np.array([[wmap[fr[:rows, c * 16:(c + 1) * 16]].sum() for c in range(4)] for fr in frames])
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
        col = (x // 16) % 4
        L = int(lev[col])
        r = x % 16
        fh = MOUND[col][r] + FACE_ADD[L]
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
HAZ = [
    ('A', 'spikes', PA, render_spikes),
    ('B', 'fire', PB, render_fire),
    ('C', 'water', PC, render_water),
    ('D', 'lava', PD, render_lava),
]
LURK_X = 118
VIEW_Y = 136          # GIF crop: 56 px of scene above the strip


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


def scene_frame(base, key, pal, frames, extra, f, masks=None, lev=None):
    s = base.copy()
    if lev is not None:
        cast_light(s, key, lev[f], masks)
    ti = pal.img(frames[f])
    for x in range(0, 320, W):
        s.alpha_composite(ti, (x, HAZ_Y))
    if key == 'C':
        put_lurker(s, f, extra['surf'][f], LURK_X, HAZ_Y)
    return s


def colours(key, pal, frames, extra):
    used = set()
    for fr in frames:
        used |= set(np.unique(fr).tolist())
    used.discard(0)
    names = {pal.keys[i - 1] for i in used}
    if key == 'C':
        for f in range(NF):
            names |= {c for (_, _, c, _) in lurker(f, extra['surf'][f], LURK_X % W)}
    assert len({pal.d[n] for n in names}) == len(names), key
    assert len(names) <= 15, (key, len(names))
    return len(names), [k for k in pal.keys if k not in names]


def save_gif(path, imgs, ms):
    imgs = [im.convert('RGB').quantize(colors=128, dither=Image.Dither.NONE) for im in imgs]
    imgs[0].save(path, save_all=True, append_images=imgs[1:], duration=ms, loop=0, disposal=1, optimize=False)


def main():
    only = sys.argv[sys.argv.index('--only') + 1] if '--only' in sys.argv else None
    check = sys.argv[sys.argv.index('--check') + 1] if '--check' in sys.argv else None
    base = base_scene()
    masks = light_masks(base)
    for key, name, pal, fn in HAZ:
        if only and key not in only:
            continue
        frames, extra = fn()
        assert len(frames) == NF and all(fr.shape == (H, W) for fr in frames)
        n, unused = colours(key, pal, frames, extra)
        lev = light_levels(key, pal, frames) if key in LIGHT_W else None
        sc = [scene_frame(base, key, pal, frames, extra, f, masks, lev) for f in range(NF)]
        df = [int((frames[i] != frames[(i + 1) % NF]).sum()) for i in range(NF)]
        frozen = int(np.all([fr == frames[0] for fr in frames], axis=0)[:20].sum())
        print('  %s changed pixels per step: seam(15->0)=%d, other steps min=%d max=%d; never-changing pixels in rows 0-19: %d of %d'
              % (key, df[-1], min(df[:-1]), max(df[:-1]), frozen, 20 * W))
        if check:
            # inspection sheets (scratch): all 16 tile frames in one row at 2x; the same in two rows at 4x over a scene crop at 6x
            bg = (10, 12, 34, 255)
            row = Image.new('RGBA', (W * NF, H), bg)
            for f in range(NF):
                row.alpha_composite(pal.img(frames[f]), (f * W, 0))
            row.convert('RGB').resize((W * NF * 2, H * 2), Image.NEAREST).save(os.path.join(check, f'row_{key}_2x.png'))
            sheet = Image.new('RGB', (2048, 256 + 8 + 2 * 88 * 3 + 8), (70, 70, 80))
            two = Image.new('RGBA', (W * 8, H * 2), bg)
            for f in range(NF):
                two.alpha_composite(pal.img(frames[f]), ((f % 8) * W, (f // 8) * H))
            sheet.paste(two.convert('RGB').resize((2048, 256), Image.NEAREST), (0, 0))
            for j, f in enumerate((2, 7, 11, 14)):
                cell = sc[f].crop((0, VIEW_Y, 320, 224)).convert('RGB').resize((960, 264), Image.NEAREST)
                sheet.paste(cell, ((j % 2) * 1000, 264 + (j // 2) * 272))
            sheet.save(os.path.join(check, f'check_{key}.png'))
            print(key, name, 'colours', n, 'unused', unused, 'check sheets written')
            continue
        vf = VFRAMES[key]
        strip = Image.new('RGBA', (W * NF, H), (0, 0, 0, 0))
        for f in range(NF):
            strip.alpha_composite(pal.img(frames[f]), (f * W, 0))
        strip.save(os.path.join(HERE, f'frames_{key}_1x.png'))
        sc[2].convert('RGB').resize((960, 672), Image.NEAREST).save(os.path.join(HERE, f'scene_{key}_3x.png'))
        crop = [s.crop((0, VIEW_Y, 320, 224)).resize((1280, (224 - VIEW_Y) * 4), Image.NEAREST) for s in sc]
        ms16 = int(round(vf * 1000 / 60 / 10)) * 10          # GIF timing is in 10 ms steps
        save_gif(os.path.join(HERE, f'anim_{key}_16f_4x.gif'), crop, ms16)
        print('%s %-6s colours=%2d (unused palette keys: %s) frames=16 tiles=%d frame=%d video frames (gif %d ms)'
              % (key, name, n, unused or 'none', 8 * 16, vf, ms16))
        if lev is not None:
            print('  light levels per frame (4 columns of 16 px):', ' '.join(''.join(str(v) for v in r) for r in lev))


if __name__ == '__main__':
    main()
