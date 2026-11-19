#!/usr/bin/env python3
# Roofline bottom-hazard drafts, round 4 (depth pass on round 3): A spikes, B fire, C water (+ lurker sprite), D lava.
# Motion comes from small physical simulations baked to a seamless loop:
#   tile 64x32 (4x2 Neo Geo tiles), 16 software frames. Fire and lava are simulated on a 128 px periodic domain
#   and cut into two tile variants A (x 0-63) and B (x 64-127); the strip is A B A B A, seamless at every joint.
# Light: ONE key light from the upper left. Flame and melt are emissive and light what is next to them.
# Shading: the simulated fields are smoothed, then cut into hard cel bands. No ramps, no dither, no noise.
# Deterministic, no network. Run: python3.14 -I draw_hazards_v4.py     (needs Pillow + numpy)
# Inspect one hazard only:   python3.14 -I draw_hazards_v4.py --only C --check /scratch/dir   (writes nothing here)
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



def set_domain(w):
    """Width of the periodic x domain: 64 (one tile) or 128 (tile variants A + B)."""
    global W, XS
    W = w
    XS = np.arange(W) + 0.5



# ================================================================ A: spikes (spring-driven pistons + arc)
# Steel is 7 shades, hue shifted from violet-black to white: o D d m l h w. 'g' is the violet bounce light.
PA = Pal({
    'o': (12, 10, 26),     # outline / deep shadow / stripe black
    'D': (30, 34, 84),     # steel core shadow (new in v4, replaces the separate stripe black)
    'd': (58, 66, 128),    # steel shadow (cool violet)
    'm': (112, 130, 192),  # steel mid / reflected light on the shadow side
    'l': (172, 192, 232),  # steel lit face
    'h': (228, 240, 255),  # highlight
    'w': (255, 255, 255),  # rim light / arc core
    'a': (64, 224, 255),   # arc halo, inner (cyan)
    'y': (250, 200, 44),   # stripe yellow
    'Y': (198, 108, 28),   # stripe yellow shade (to orange)
    'g': (74, 68, 112),    # rail plate / violet bounce
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


SHAFT = 'hwlmdDmo'      # chrome column, left to right: lit edge, highlight, light, mid, shadow, core shadow, reflected, outline


def blade_px(j, rel, hw):
    """Blade = two bevelled faces meeting on a centre ridge. Left face is lit, right face is in shadow."""
    if j == 0 or rel == -hw:
        return 'w'                                  # tip and rim light on the lit edge
    if rel < 0:
        if rel == -1 and 2 <= j <= 8 and hw >= 3:
            return 'h'                              # glint along the ridge
        if j >= 9 and rel >= -(j - 8):
            return 'm'                              # form shadow wedge where the face turns down to the collar
        if rel <= -hw + 2 and j >= 4:
            return 'h'                              # bright band behind the rim
        return 'l'
    if rel == hw - 1:
        return 'm' if j >= 3 else 'd'               # reflected light on the far edge
    if rel == 0 and hw >= 2:
        return 'D'                                  # core shadow right behind the ridge
    if j >= 9 and rel <= j - 9:
        return 'D'                                  # core shadow wedge
    return 'd'


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
            # shaft: chrome column with rings that travel with it; the collar casts a shadow on its first rows
            for y in range(ty + BL + 2, RAIL_Y):
                ring = (y - ty) % 4 == 1
                cast = y <= ty + BL + 3
                for j, ch in enumerate(SHAFT):
                    if ch != 'o' and (ring or cast):
                        ch = {'h': 'm', 'w': 'l', 'l': 'm', 'm': 'd', 'd': 'D', 'D': 'D'}[ch] if cast else ('m' if j == 1 else 'D' if j >= 4 else 'd')
                    put(idx, c - 4 + j, y, PA[ch])
            # collar (blade base), as wide as the blade: lit lip, then its own shadow band
            for x in range(c - 7, c + 7):
                put(idx, x, ty + BL, PA['o'])
                put(idx, x, ty + BL + 1, PA['w'] if x < c - 4 else PA['h'] if x < c - 1 else PA['l'] if x < c + 1 else PA['d'] if x < c + 4 else PA['D'] if x < c + 6 else PA['m'])
            for j, hw in enumerate(BLADE_HW):
                for x in range(c - hw, c + hw):
                    put(idx, x, ty + j, PA[blade_px(j, x - c, hw)])
        # housing: one bevelled sleeve block per piston (top face, front face with a diagonal shadow, dark right side), then the rail
        for y in range(SLEEVE_Y, H):
            for x in range(W):
                rel = (x % 16) - 8
                k = y - SLEEVE_Y
                if y < RAIL_Y:
                    if rel in (-8, 7):
                        c = 'o'
                    elif k == 0:
                        c = 'w' if rel < -2 else 'h' if rel < 3 else 'm' if rel < 6 else 'l'      # top face; 'm' = shadow cast by the shaft
                    elif rel == -7:
                        c = 'h'                                                                # rim light
                    elif rel == 6:
                        c = 'g'                                                                # bounce light
                    elif k == 1:
                        c = 'l' if rel < 2 else 'm'
                    elif k == 2:
                        c = 'l' if rel < -4 else 'm' if rel < 0 else 'd'
                    elif k == 3:
                        c = 'm' if rel < -3 else 'd' if rel < 3 else 'D'
                    else:
                        c = 'd' if rel < -1 else 'D'
                    if rel in (-5, 4) and k == 2:
                        c = 'w' if rel < 0 else 'l'
                    if rel in (-5, 4) and k == 3:
                        c = 'o'
                elif y == RAIL_Y:
                    c = 'w' if -6 <= rel < -2 else 'h' if rel < 3 else 'l'
                elif y == RAIL_Y + 1:
                    c = 'g'
                elif y == RAIL_Y + 2:
                    c = 'D'
                elif y == RAIL_Y + 3:
                    c = 'o'
                elif y <= RAIL_Y + 7:
                    c = 'y' if ((x + (y - RAIL_Y)) // 4) % 2 == 0 else 'o'
                    if c == 'y' and y in (RAIL_Y + 4, RAIL_Y + 7):
                        c = 'Y'                      # rail shadow on the top row, turn-away on the bottom row
                    if c == 'o' and y == RAIL_Y + 5:
                        c = 'D'                      # gloss on the black stripe
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
                # the arc lights the two blade faces that look at it (cyan rim on the shadow steel)
                for (cc, tt, side) in ((c0, t0, 1), (c1, t1, -1)):
                    for j in range(1, 6):
                        hw = BLADE_HW[j]
                        put(idx, cc + (hw - 1 if side > 0 else -hw), tt + j, PA['a'], only=(PA['m'], PA['d'], PA['w']))
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


# ================================================================ B: fire (advected temperature field + soot)
# Simulated on a 128 px periodic domain: tile A = x 0-63, tile B = x 64-127.
PB = Pal({
    'o': (30, 6, 24),      # coal outline
    'c': (56, 20, 44),     # coal dark
    'C': (104, 44, 60),    # coal mid
    'a': (176, 104, 92),   # coal ash, lit top (new)
    'S': (40, 26, 62),     # smoke, thin (violet, new)
    's': (86, 54, 92),     # smoke, dense, lit by the flame below (new)
    'M': (96, 8, 60),      # flame cool edge (magenta, new)
    'D': (150, 16, 40),    # deep crimson
    'r': (226, 44, 36),    # red
    'O': (252, 122, 30),   # orange
    'y': (255, 176, 46),   # amber (flame band and sparks)
    'Y': (255, 222, 84),   # yellow
    'w': (255, 252, 222),  # white-hot core
})
# x, width, puffs/loop, phase, strength. Uneven spacing (gaps 12 18 10 19 17 9 17 11 15) and strength: one tall tongue in A,
# one tall but thinner in B, the rest clearly lower.
SPOTS = [(9, 5.6, 2, 0.00, 1.00), (21, 2.2, 3, 0.37, 0.46), (39, 3.8, 2, 0.61, 0.82), (49, 2.0, 3, 0.13, 0.40),
         (68, 3.2, 2, 0.80, 0.66), (85, 4.8, 3, 0.29, 0.94), (94, 2.0, 2, 0.55, 0.38), (111, 3.8, 3, 0.92, 0.76), (122, 2.2, 2, 0.45, 0.44)]
FCOOL = 3.0
FCOOL_K = (1.45, 0.9)          # cooling = FCOOL * (K0 - K1 * envelope): weak sources sit in colder air, so their tongues stay short
SOOT_DECAY = 6.0
FMODES = [(2, 30, 1, 2, 10, 0.0), (4, 22, -1, 2, 13, 1.3), (6, 16, 2, 3, 11, 2.1), (10, 12, -2, 3, 8, 4.0),
          (1, 26, 1, 2, 5, 0.7), (3, 19, -1, 3, 6, 2.9)]
# n (x harmonics per 128 px), vertical wavelength px, time harmonics of the sideways drift, of the upward drift, speed px/loop, phase
# (the first four are the v3 modes; the two odd ones make tile A and B differ)


def fire_env(x):
    e = 0
    for (x0, wd, m, ph, st) in SPOTS:
        e = np.maximum(e, st * np.exp(-(wrapd(x, x0) / (1.8 * wd + 2.0)) ** 2))
    return e


def fire_source(x, t):
    s = 0.28 + 0.06 * np.sin(TAU * (5 * x / W + t))
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
    """Temperature T and soot Q, both carried by the same velocity field. Soot is made where the flame cools out
    (the fringe above the tips), rises with the gas and decays: smoke wisps that follow the tongues."""
    S, sub = 3, 8
    gw, gh = W * S, H * S
    X, Y = np.meshgrid((np.arange(gw) + 0.5) / S, (np.arange(gh) + 0.5) / S)
    steps = NF * sub
    dt = 1.0 / steps
    T = np.zeros((gh, gw))
    Q = np.zeros((gh, gw))
    env = fire_env(X)
    cool = FCOOL * (FCOOL_K[0] - FCOOL_K[1] * env) + 5.0 * np.clip((11 - Y) / 9.0, 0, 1)   # cold air entrained higher up
    src_rows = (Y > 23.0) & (Y < 28.5)
    prev = prevq = None
    for loop in range(12):
        out, outq = [], []
        for i in range(steps):
            t = i * dt
            if i % sub == 0:
                out.append(T.copy())
                outq.append(Q.copy())
            u, v = fire_vel(X, Y, t, blur_x(T, 1.5))
            T = advect(T, u, v, dt, X, Y, S)
            Q = advect(Q, u, v, dt, X, Y, S)
            T = blur_y(blur_x(T, 0.26), 0.2)
            Q = blur_y(blur_x(Q, 0.3), 0.25) * (1 - dt * SOOT_DECAY)
            T = np.maximum(T - dt * cool, 0)
            Q = np.where((T > 0.03) & (T < 0.16) & (Y < 17), 1.0, Q)
            s = fire_source(X, t)
            T = np.where(src_rows, np.maximum(T, s), T)
            T[Y >= 28.5] = 0
        err = max(max(np.abs(a - b).max() for a, b in zip(p, o)) for p, o in ((prev, out), (prevq, outq))) if prev is not None else 1.0
        prev, prevq = out, outq
        if err < 1e-5:
            break
    assert err < 1e-3, ('fire loop not periodic', err)
    ds = lambda o: o.reshape(H, S, W, S).mean((1, 3))
    return [ds(o) for o in prev], [ds(o) for o in prevq]


LUMPS = [(3.0, 28.6, 4.4, 3.2), (10.4, 28.0, 3.2, 3.4), (16.8, 29.0, 4.6, 2.8), (24.0, 28.0, 3.0, 3.6), (29.6, 28.8, 3.8, 3.0),
         (36.4, 27.8, 4.2, 3.6), (43.0, 29.0, 3.4, 2.6), (49.0, 28.2, 4.4, 3.3), (56.4, 28.8, 3.2, 3.0), (62.0, 27.9, 3.6, 3.5),
         (68.6, 28.8, 4.4, 3.0), (75.6, 28.0, 3.4, 3.4), (81.4, 29.0, 3.6, 2.7), (88.0, 28.1, 4.6, 3.5), (95.4, 28.8, 3.2, 3.0),
         (101.2, 28.0, 3.8, 3.4), (108.2, 28.9, 4.4, 2.8), (115.2, 28.0, 3.2, 3.5), (121.6, 28.6, 4.2, 3.1)]
SPARKS = [(0, 0.05, 0.62, 14), (1, 0.30, 0.55, -10), (2, 0.52, 0.70, 6), (3, 0.71, 0.58, -16), (4, 0.16, 0.66, 12),
          (5, 0.88, 0.60, -6), (0, 0.58, 0.50, -18), (2, 0.22, 0.64, 8), (5, 0.44, 0.56, 16), (6, 0.36, 0.52, -8),
          (7, 0.02, 0.66, 10), (8, 0.67, 0.55, -12), (7, 0.49, 0.60, -16)]  # spot, birth, life, vx0


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
FRONT_BANDS = ((0.05, 'M', 0), (0.10, 'D', 0), (0.21, 'r', 0), (0.33, 'O', 0), (0.45, 'y', 1), (0.57, 'Y', 1), (0.74, 'w', 1))


def render_fire():
    set_domain(128)
    Ts, Qs = sim_fire()
    frames = []
    for f in range(NF):
        t = f / NF
        T = blur_y(blur_x(Ts[f], 0.9), 0.7)
        Tc = blur_y(blur_x(Ts[f], 1.5), 1.1)        # cores are cut from a smoother field: round shapes, no blocks
        idx = np.zeros((H, W), np.uint8)
        # 1 smoke: two hard shapes cut from the soot field (dense near the tip, thin above)
        Qm = blur_y(blur_x(Qs[f], 1.2), 1.0)
        inside = np.ones((H, W), bool)
        for th, ch in ((0.16, 'S'), (0.45, 's')):
            inside = smooth_mask(Qm > th) & inside
            idx[inside] = PB[ch]
        # 2 back row of flames: the same field, another moment and place, lower and in the cool colours only
        Tb = blur_y(blur_x(np.roll(Ts[(f + BACK_LAG) % NF], BACK_SHIFT, axis=1), 1.2), 0.9)
        Tb = np.vstack([np.zeros((BACK_DROP, W)), Tb[:-BACK_DROP]])
        inside = np.ones((H, W), bool)
        for th, ch in ((0.13, 'M'), (0.27, 'D'), (0.60, 'r')):
            inside = smooth_mask(Tb > th) & inside
            idx[inside] = PB[ch]
        # 3 front row: cool magenta edge, crimson, red body, orange, amber, yellow, white core
        inside = np.ones((H, W), bool)
        for th, ch, k in FRONT_BANDS:
            inside = smooth_mask((Tc if k else T) > th) & inside
            idx[inside] = PB[ch]
        idx = despeckle(idx)
        # coal bed: round lumps. Top rim glows with the heat right above it; the body has an ash-lit top-left cluster,
        # a mid cluster, a dark cluster and an outline-dark underside; cracks between lumps glow.
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
        soft = (0, PB['S'], PB['s'], PB['M'], PB['D'])
        for (spot, t0, life, vx) in SPARKS:
            age = (t - t0) % 1.0
            if age < life:
                x, y = spark_pos(spot, t0, age)
                a = age / life
                put(idx, x, y, PB['w' if a < 0.2 else 'Y' if a < 0.5 else 'y' if a < 0.8 else 'r'], only=soft)
        frames.append(idx)
    set_domain(64)
    return frames, {}


def tongue_report(frames):
    """Text check for point 3: the three tallest tongues (height px @ x) per frame over the 128 px domain."""
    hot = [PB[k] for k in 'rOyYw']
    for f, fr in enumerate(frames):
        m = np.isin(fr[:25], hot)
        hgt = np.where(m.any(0), 25 - m.argmax(0), 0)
        n = len(hgt)
        pk = sorted(((int(hgt[x]), x) for x in range(n)
                     if hgt[x] >= 5 and hgt[x] == max(hgt[(x + d) % n] for d in range(-5, 6)) and hgt[x] > hgt[(x - 1) % n]), reverse=True)
        print('    f%02d tongues h@x: %s' % (f, ' '.join('%d@%d' % p for p in pk[:5])))


# ================================================================ C: water (Gerstner waves, deep-water dispersion)
# Water is 7 shades, hue shifted violet-black -> navy -> indigo -> blue -> light blue -> teal -> cyan, plus two foam tones.
PC = Pal({
    'o': (8, 8, 34),       # abyss (violet black)
    'n': (18, 26, 88),     # deep navy
    'u': (30, 44, 128),    # indigo (new): wave self-shadow, upper deep band
    'b': (22, 74, 160),    # blue body
    'B': (40, 122, 208),   # light blue, translucent band
    'T': (58, 176, 204),   # teal (new): light passing through the crest
    'c': (112, 214, 240),  # cyan skin
    'f': (190, 236, 252),  # lit crest / foam shade
    'w': (255, 255, 255),  # foam white
    'p': (46, 28, 74),     # rock shadow face (new)
    'P': (112, 96, 156),   # rock lit face (new)
    'q': (188, 180, 220),  # rock top highlight (new)
    'W': (70, 206, 120),   # weed, lit (new)
    'x': (18, 112, 98),    # weed, shadow (new)
})
# the lurker is a sprite with its own palette (8 colours)
PLK = Pal({
    'o': (8, 8, 34), 'w': (255, 255, 255), 'f': (190, 236, 252),
    'e': (255, 224, 64),   # eye
    'E': (240, 92, 40),    # eye rim
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
ROCKS = [(6.0, 5.5, 6.0), (22.0, 7.5, 3.4), (37.0, 4.6, 8.0), (51.5, 8.0, 4.4), (61.0, 2.6, 3.0)]   # centre x, half width, height px
WEEDS = [(12, 9, 0.00), (29, 8, 0.35), (43, 11, 0.60), (57, 9, 0.80)]                             # root x, length px, sway phase
BUBS = [(37.0, 0.00, 2), (38.0, 0.42, 1), (36.5, 0.71, 2), (6.0, 0.20, 2), (6.5, 0.63, 1), (51.0, 0.88, 1), (22.0, 0.50, 2)]  # vent x, birth, size


def rock_top():
    hgt = np.zeros(W)
    for (cx, hw, hh) in ROCKS:
        hgt = np.maximum(hgt, hh * np.clip(1 - (wrapd(XS, cx) / hw) ** 2, 0, 1))
    return FLOOR_Y - np.round(hgt).astype(int)


def render_water():
    states, events = sim_water()
    frames, surf = [], []
    rtop = rock_top()
    rock_of = [max(ROCKS, key=lambda r: r[2] * max(0.0, 1 - (wrapd(x + 0.5, r[0]) / r[1]) ** 2)) for x in range(W)]
    for f in range(NF):
        t = f / NF
        xs, y, J, F = states[f]
        h = blur_x(np.interp(XS, xs, y, period=W), 0.8)
        Fp = np.interp(XS, xs, F, period=W)
        slope = (np.roll(h, -1) - np.roll(h, 1)) / 2
        sls = blur_x(slope, 1.0)
        ysurf = WY0 - h
        top = np.floor(ysurf + 0.5).astype(int)
        tb = 1.2 + np.clip(7.0 * sls, 0, 3.6)
        yb2 = 19.0 - deep_shift(t, 7.0)
        yb3 = 24.5 - deep_shift(t, 12.0)
        lit = sls > 0.20          # face turned to the light (upper left): the surface rises to the right
        shd = sls < -0.20         # face turned away
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
                    c = 'f' if lit[x] else 'T' if shd[x] else 'c'       # lit crest / skin / skin in shadow
                elif d == 1 and lit[x]:
                    c = 'c'
                elif d <= tb[x]:
                    c = 'B' if (shd[x] or d > 1 + tb[x] / 2) else 'T'    # translucent band: teal where the light enters
                elif shd[x] and d <= 4:
                    c = 'u'                                             # the crest's own shadow on the far face
                elif yy + 0.5 < yb2[x]:
                    c = 'b'
                elif yy + 0.5 < yb3[x]:
                    c = 'u'
                else:
                    c = 'n'
                idx[yy, x] = PC[c]
                body[yy, x] = d > tb[x] + 1
        idx = despeckle(idx)
        # caustic light shapes: where the refracted rays bunch, the water is one shade lighter (hard shapes)
        ca = smooth_mask(I > CAUS_T) & body
        cb = smooth_mask(I > CAUS_T2) & body
        src = idx.copy()
        idx[ca & (src == PC['n'])] = PC['u']
        idx[ca & (src == PC['u'])] = PC['b']
        idx[cb & (src == PC['b'])] = PC['B']
        idx[cb & (src == PC['u'])] = PC['B']
        idx = despeckle(idx)
        # sub-surface shapes: rocks with a lit top-left face, a highlight on the top edge and a shadow face; floor line
        water = (PC['n'], PC['u'], PC['b'], PC['B'], PC['T'])
        for x in range(W):
            cx, hw, hh = rock_of[x]
            lf = wrapd(x + 0.5, cx) / hw
            for yy in range(rtop[x], H):
                if yy >= FLOOR_Y:
                    c = 'p' if (yy == FLOOR_Y and rtop[x] == FLOOR_Y) else 'o'
                else:
                    up = (FLOOR_Y - yy - 0.5) / hh
                    if yy == rtop[x]:
                        c = 'q' if lf < 0.3 else 'P'
                    elif yy == rtop[x] + 1 and lf < -0.2:
                        c = 'q'
                    elif lf - 0.8 * up < -0.25:
                        c = 'P'
                    else:
                        c = 'p'
                idx[yy, x] = PC[c]
        # weed: 2 px stalks (lit left column, shadow right column) with leaves, swaying with the swell that reaches down
        sway = deep_shift(t, 14.0)
        for (wx, wl, ph) in WEEDS:
            for k in range(wl):
                yy = rtop[wx] - 1 - k
                off = (k / wl) ** 1.3 * (2.4 * sin(TAU * (t + ph) - 0.3 * k) + 1.2 * sway[wx])
                put(idx, wx + off, yy, PC['W'], only=water)
                if k < wl - 2:
                    put(idx, wx + off + 1, yy, PC['x'], only=water)
                if k % 3 == 1 and k < wl - 1:
                    if (k // 3) % 2 == 0:
                        put(idx, wx + off - 1, yy, PC['W'], only=water)
                        put(idx, wx + off - 2, yy - 1, PC['W'], only=water)
                    else:
                        put(idx, wx + off + 2, yy, PC['x'], only=water)
                        put(idx, wx + off + 3, yy - 1, PC['x'], only=water)
        # bubbles from the rock vents: buoyancy against drag (speed rises to terminal), wobble, gone at the surface
        for (vx, t0, sz) in BUBS:
            age = (t - t0) % 1.0
            ya = rtop[int(vx)] - 1 - 30.0 * (age - 0.18 * (1 - np.exp(-age / 0.18)))
            xa = vx + 1.4 * sin(TAU * 2 * age + vx)
            if ya > top[int(xa) % W] + 3:
                if sz == 2 and age > 0.22:
                    put(idx, xa, ya, PC['f'], only=water)
                    put(idx, xa + 1, ya, PC['c'], only=water)
                    put(idx, xa, ya + 1, PC['c'], only=water)
                    put(idx, xa + 1, ya + 1, PC['T'], only=water)
                else:
                    put(idx, xa, ya, PC['c'], only=water)
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
                    lo = PC['f' if vy + GRAV_W * age < 0 else 'c']
                    if sz == 2:
                        shape = ((0, 0, hi), (1, 0, lo), (0, 1, lo), (1, 1, PC['T']))
                    else:
                        shape = ((1, 0, hi), (0, 1, hi), (1, 1, PC['f']), (2, 1, lo), (1, 2, PC['T']), (0, 2, lo))
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
    water = {PC.d[k] for k in 'nubBT'}
    for (x, y, c, mode) in lurker(f, top, sx % W):
        X, Y = x - (sx % W) + sx, oy + y
        if not (0 <= X < im.width and 0 <= Y < im.height):
            continue
        if mode == 'u' and px[X, Y][:3] not in water:
            continue
        px[X, Y] = PLK.d[c] + (255,)


# ================================================================ D: lava (damped wave PDE + convection + crust conveyor)
# Simulated on a 128 px periodic domain: tile A = x 0-63, tile B = x 64-127. The big bubble lives in B only.
# Melt is 7 shades (violet-maroon to white-hot), crust is 7 (black, two browns, lit, highlight, violet bounce, under-glow).
PD = Pal({
    'o': (22, 6, 20),      # crust black
    'k': (58, 18, 36),     # crust dark
    'K': (110, 44, 50),    # crust mid (side face)
    'Q': (196, 112, 84),   # crust lit top face
    'H': (246, 190, 140),  # crust highlight (plate end facing the light)
    'V': (88, 54, 100),    # crust shadow face with cool bounce (violet, new)
    'G': (184, 60, 30),    # crust lit from below / crack wall glow (new)
    'm': (52, 4, 50),      # coldest melt, deep shadow (violet, new)
    'P': (96, 8, 46),      # cold melt (maroon)
    'D': (152, 18, 34),    # deep red
    'r': (222, 50, 28),    # red
    'O': (250, 124, 26),   # orange
    'y': (255, 200, 56),   # yellow
    'Y': (255, 248, 190),  # white-hot
})
LY0 = 12.0
NODES = [8.0, 19.0, 43.0, 55.0, 72.0, 86.0, 104.0, 121.0, 136.0]   # upwelling, downwelling, ... (last = first + 128)
# x (an upwelling), max radius, burst frame, droplet scale. Uneven sizes and timing; the big one (104) is in tile B.
BUB = [(8.0, 4.6, 3, 0.7), (43.0, 3.4, 12, 0.55), (72.0, 3.0, 9, 0.5), (104.0, 7.5, 6, 1.0)]
BUB_AT = {b[0]: b for b in BUB}
MINI = [(30.5, 2, 2.4), (51.0, 10, 2.0), (63.0, 5, 1.6), (91.5, 13, 2.2), (116.0, 7, 1.8)]   # blisters: x, pop-start frame, radius
SIDE = [(30.0, 3.0, 0.62, 0.3), (62.0, 2.4, 0.5, 0.8), (94.0, 3.2, 0.6, 0.55), (118.0, 2.2, 0.45, 0.1)]   # extra floor heat: x, width, strength, phase
LDROPS = [(-24, -60), (-10, -82), (4, -92), (13, -72), (26, -54), (-34, -42)]
GRAV_L = 400.0
CRUST_U, BODY_U, DEPTH = 10.0, 24.0, 20.0
BARE = 2.6


def lava_us(x):
    """Surface flow profile (unit amplitude): away from upwellings, into downwellings."""
    x = np.asarray(x, float)
    xm = (x - NODES[0]) % W + NODES[0]
    u = np.zeros_like(xm)
    for i in range(len(NODES) - 1):
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
    for i in range(len(NODES) - 1):
        a, b = NODES[i], NODES[i + 1]
        up, dn = (a, b) if i % 2 == 0 else (b, a)
        sg = 1 if dn > up else -1
        xs = up + sg * np.arange(BARE, abs(dn - up) - 0.9, 0.02)
        sp = CRUST_U * (abs(dn - up) / 13.0) * np.abs(lava_us(xs))     # wide rolls run faster: longer plates
        tt = np.concatenate([[0], np.cumsum(0.02 / sp[:-1])])
        flanks.append((xs, tt, BUB_AT[up % W][2] / NF))
        age[np.round((xs % W) / 0.02).astype(int) % len(fine)] = tt
    agep = np.array([np.max(age[int(x / 0.02):int((x + 1) / 0.02)]) for x in range(W)])
    return agep, flanks


def sim_lava_surface():
    """1D damped wave equation, periodic: h_tt = c^2 h_xx - gamma h_t + mu h_xxt + bubble-burst impulses."""
    n, c, gam, mu = 4 * W, 34.0, 5.5, 5.0
    dx = W / n
    x = (np.arange(n) + 0.5) * dx
    steps = 3200
    dt = 1.0 / steps
    h = np.zeros(n)
    v = np.zeros(n)
    prev = None
    err = 1.0
    for loop in range(80):       # on 128 px the longest wave is overdamped and settles slowly: loop until the cycle closes
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
        if prev is not None:
            err = max(np.abs(a - b).max() for a, b in zip(prev, out))
        prev = out
        if err < 1e-5:
            break
    assert err < 1e-3, ('lava surface not periodic', err)
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
    set_domain(128)
    agep, flanks = crust_tables()
    ripple = sim_lava_surface()
    body = sim_lava_body(agep)
    darker = np.arange(len(PD.keys) + 1)
    for a, b in (('Y', 'y'), ('y', 'O'), ('O', 'r'), ('r', 'D'), ('D', 'P'), ('P', 'm')):
        darker[PD[a]] = PD[b]
    frames = []
    for f in range(NF):
        t = f / NF
        h = (0.9 * np.cos(TAU * (2 * XS / W - t)) + 0.5 * np.cos(TAU * (4 * XS / W + t) + 1.0) + ripple[f])
        ysurf = LY0 - h
        top = np.floor(ysurf + 0.5).astype(int)
        T = blur_y(blur_x(body[f], 0.8), 0.6)
        idx = np.zeros((H, W), np.uint8)
        for x in range(W):
            for yy in range(max(top[x], 0), H):
                d = min(yy - top[x], T.shape[0] - 1)
                v = T[d, x]
                idx[yy, x] = PD['m' if v < 0.075 else 'P' if v < 0.14 else 'D' if v < 0.27 else 'r' if v < 0.47 else 'O' if v < 0.70 else 'y' if v < 0.93 else 'Y']
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
                    for j, ch in enumerate('QKkVokG'):
                        put(idx, x, tp - 4 + j, PD[ch])
                continue
            ck = min(cracks, key=lambda c: abs(wrapd(x + 0.5, c[0]))) if cracks else None
            dck = abs(wrapd(x + 0.5, ck[0])) if ck else 99
            wl = wrapd(x + 0.5, ck[0]) if ck else 99
            cw = 0.6 if (ck and ck[1] > 0.9) else 1.1
            if ag < 0.3:                             # fresh skin
                put(idx, x, tp, PD['y'])
                put(idx, x, tp + 1, PD['O'])
            elif dck < cw:                           # crack: the melt shows through at the bottom of a notch
                # the notch is shallow (2 px): below it the crack is filled with glow, hotter toward the melt
                for yy in range(tp - (0 if ag < 0.5 else 1 if ag < 1.05 else 2), tp):
                    put(idx, x, yy, PD['O' if yy < tp - 1 else 'y'])
                put(idx, x, tp, PD['Y' if heat[0] > 0.6 and ck[1] < 1.2 else 'y'])
                put(idx, x, tp + 1, PD['y'])
                put(idx, x, tp + 2, PD['O'])
            else:
                # plate = slab seen slightly from above: top face (2 rows), side face, black underside, under-glow row,
                # then its cast shadow on the melt. End facing the light: highlight. End facing away: violet shadow face.
                lit = 0 < wl < 3.4
                drk = -2.4 < wl < 0
                end = 0 < wl < 1.6                   # the 1-2 px end cap that faces the light
                # the top face is one unbroken light line per plate; only the side face changes along it
                if ag < 0.5:
                    rows, y0 = ('HQko' if end else 'QVko' if drk else 'QKko'), tp - 1
                elif ag < 1.05:
                    rows, y0 = ('HQQKoG' if end else 'HQKkoG' if lit else 'QKVVoG' if drk else 'QQKkoG'), tp - 3
                else:
                    rows, y0 = ('HQQKKoG' if end else 'HQKKkoG' if lit else 'QKVVVoG' if drk else 'QQKKkoG'), tp - 4
                if dck < cw + 1.0 and len(rows) > 4:
                    rows = rows[:2] + ''.join('G' if ch in 'KkV' else ch for ch in rows[2:])     # crack walls glow
                for j, ch in enumerate(rows):
                    put(idx, x, y0 + j, PD[ch])
                for j in (len(rows), len(rows) + 1):
                    yy = y0 + j
                    if 0 <= yy < H:
                        idx[yy, x] = darker[idx[yy, x]]
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
                            put(idx, x, yy, PD['Y' if dist > r - 1.1 and dxp + dyp < 0 else 'y' if dist > r - 1.1 and dxp < 0.5 else 'r' if dist > r - 1.1 else 'O'])
            elif g in (4, 5):
                k = g - 4
                for (dx, dy) in ((-2 - k, -4 - k), (1, -5 - 2 * k), (3 + k, -3 - k)):
                    put(idx, mx + dx, tpc + dy, PD['Y' if k == 0 else 'O'], only=(0,))
                for x in (xc - 1, xc):
                    put(idx, x, tpc - 1, PD['y' if k == 0 else 'O'])
                    put(idx, x, tpc, PD['Y' if k == 0 else 'y'])
        # bubbles: swell to a dome, burst into a crown, throw droplets. Dome shading: white rim toward the light,
        # yellow body, orange then red terminator on the far side, a dark-red contact shadow at its foot.
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
                            c = 'Y' if (nx + ny < -0.25) else 'y' if ny < 0.1 and nx < 0.45 else 'O' if nx < 0.8 else 'r'
                        elif nx + 0.8 * ny > 0.75 and r >= 4:
                            c = 'D'
                        elif nx + 0.8 * ny > 0.40:
                            c = 'r'
                        elif nx + 0.8 * ny > 0.05:
                            c = 'O'
                        elif abs(nx + 0.42) < 0.2 and abs(ny + 0.42) < 0.2 and r >= 3:
                            c = 'Y'
                        else:
                            c = 'O' if e < 0.4 else 'y'
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
    set_domain(64)
    return frames, {}



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
HAZ = [
    ('A', 'spikes', PA, render_spikes),
    ('B', 'fire', PB, render_fire),
    ('C', 'water', PC, render_water),
    ('D', 'lava', PD, render_lava),
]
V3 = os.path.join(HERE, '..', '2026-11-10-hazards-v3')
LURK_X = 118
VIEW_Y = 136          # GIF crop: 56 px of scene above the strip
BG = (10, 12, 34, 255)


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
    ti = pal.img(frames[f])                 # 64 px (one tile) or 128 px (variants A + B): the strip is A B A B A
    for x in range(0, 320, ti.width):
        s.alpha_composite(ti.crop((0, 0, min(ti.width, 320 - x), H)), (x, HAZ_Y))
    if key == 'C':
        put_lurker(s, f, extra['surf'][f], LURK_X, HAZ_Y)
    return s


def colours(key, pal, frames, extra):
    used = set()
    for fr in frames:
        used |= set(np.unique(fr).tolist())
    used.discard(0)
    names = {pal.keys[i - 1] for i in used}
    assert len({pal.d[n] for n in pal.keys}) == len(pal.keys), key
    assert len(pal.keys) <= 15, (key, len(pal.keys))
    if key == 'C':
        lk = set()
        for f in range(NF):
            lk |= {c for (_, _, c, _) in lurker(f, extra['surf'][f], LURK_X % W)}
        assert lk <= set(PLK.keys) and len(PLK.keys) <= 15
    return len(names), [k for k in pal.keys if k not in names]


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


def check_sheet(key, pal, frames, sc, base, check):
    """Scratch inspection sheet: v3 above v4 (frame 2, 4x), both at 1x, then all 16 frames of the v4 tile(s)."""
    v3 = Image.open(os.path.join(V3, f'frames_{key}_1x.png')).convert('RGBA')

    def old(f):
        s = base.copy()
        for x in range(0, 320, 64):
            s.alpha_composite(v3.crop((f * 64, 0, f * 64 + 64, H)), (x, HAZ_Y))
        return s
    tw = frames[0].shape[1]
    scale = 2 if tw == 128 else 3
    per = 1280 // (tw * scale + 4)
    nrow = -(-NF // per)
    cut = (0, 180, 320, 224)
    hh = 44 * 4
    sheet = Image.new('RGB', (1280, 2 * hh + 16 + 60 + nrow * (H * scale + 4) + 8), (70, 70, 80))
    sheet.paste(old(2).crop(cut).convert('RGB').resize((1280, hh), Image.NEAREST), (0, 0))
    sheet.paste(sc[2].crop(cut).convert('RGB').resize((1280, hh), Image.NEAREST), (0, hh + 8))
    y = 2 * hh + 16
    sheet.paste(old(2).crop(cut).convert('RGB'), (0, y))
    sheet.paste(sc[2].crop(cut).convert('RGB'), (328, y))
    sheet.paste(sc[9].crop(cut).convert('RGB'), (656, y))
    y += 60
    for f in range(NF):
        cell = Image.new('RGBA', (tw, H), BG)
        cell.alpha_composite(pal.img(frames[f]))
        sheet.paste(cell.convert('RGB').resize((tw * scale, H * scale), Image.NEAREST), ((f % per) * (tw * scale + 4), y + (f // per) * (H * scale + 4)))
    sheet.save(os.path.join(check, f'check_{key}.png'))
    sc[2].convert('RGB').save(os.path.join(check, f'scene_{key}_1x.png'))


def main():
    only = sys.argv[sys.argv.index('--only') + 1] if '--only' in sys.argv else None
    check = sys.argv[sys.argv.index('--check') + 1] if '--check' in sys.argv else None
    base = base_scene()
    masks = light_masks(base)
    for key, name, pal, fn in HAZ:
        if only and key not in only:
            continue
        frames, extra = fn()
        assert W == 64
        assert len(frames) == NF and all(fr.shape[0] == H and fr.shape[1] in (64, 128) for fr in frames)
        nv = frames[0].shape[1] // 64
        n, unused = colours(key, pal, frames, extra)
        lev = light_levels(key, pal, frames) if key in LIGHT_W else None
        sc = [scene_frame(base, key, pal, frames, extra, f, masks, lev) for f in range(NF)]
        df = [int((frames[i] != frames[(i + 1) % NF]).sum()) for i in range(NF)]
        print('  %s changed pixels per step: seam(15->0)=%d, other steps min=%d max=%d' % (key, df[-1], min(df[:-1]), max(df[:-1])))
        vf = VFRAMES[key]
        print('%s %-6s colours=%2d of %d in palette (unused keys: %s) variants=%d tiles=%d raw, %d unique; frame=%d video frames'
              % (key, name, n, len(pal.keys), unused or 'none', nv, 8 * nv * NF, tile_count(frames), vf))
        print('  palette: ' + ', '.join('%d (%d,%d,%d)' % ((i + 1,) + pal.d[k]) for i, k in enumerate(pal.keys)))
        if key == 'B':
            tongue_report(frames)
        if check:
            check_sheet(key, pal, frames, sc, base, check)
            continue
        # build input: 16 frames per row, one row per tile variant (row 0 = A, row 1 = B)
        strip = Image.new('RGBA', (64 * NF, H * nv), (0, 0, 0, 0))
        for f in range(NF):
            ti = pal.img(frames[f])
            for v in range(nv):
                strip.alpha_composite(ti.crop((v * 64, 0, v * 64 + 64, H)), (f * 64, v * H))
        strip.save(os.path.join(HERE, f'frames_{key}_1x.png'))
        sc[2].convert('RGB').resize((960, 672), Image.NEAREST).save(os.path.join(HERE, f'scene_{key}_3x.png'))
        crop = [s.crop((0, VIEW_Y, 320, 224)).resize((1280, (224 - VIEW_Y) * 4), Image.NEAREST) for s in sc]
        ms16 = int(round(vf * 1000 / 60 / 10)) * 10          # GIF timing is in 10 ms steps
        save_gif(os.path.join(HERE, f'anim_{key}_16f_4x.gif'), crop, ms16)
        if lev is not None:
            print('  light levels per frame (%d columns of 16 px):' % lev.shape[1], ' '.join(''.join(str(v) for v in r) for r in lev))


if __name__ == '__main__':
    main()
