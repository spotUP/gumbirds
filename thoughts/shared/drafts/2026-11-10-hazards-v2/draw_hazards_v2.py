#!/usr/bin/env python3
# Roofline bottom-hazard drafts, round 2: A spikes, B fire, C water (+ lurker sprite), D lava.
# Motion comes from small physical simulations baked to a seamless loop:
#   tile 64x32 (4x2 Neo Geo tiles), 16 software frames (main) and an 8-frame cut (hardware auto-animation limit).
# Shading: the simulated fields are smoothed, then cut into hard cel bands. No ramps, no dither, no noise.
# Deterministic, no network. Run: python3.14 -I draw_hazards_v2.py     (needs Pillow + numpy)
# Preview one hazard only:   python3.14 -I draw_hazards_v2.py --only C --preview /path/out.png
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
# video frames (60 Hz) per animation frame of the 16-frame loop; the 8-frame cut doubles it (same loop length)
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


# ================================================================ A: spikes (spring-driven pistons + arc)
PA = Pal({
    'o': (12, 10, 26),     # outline / deep shadow
    'd': (58, 66, 128),    # steel shadow (cool violet)
    'm': (112, 130, 192),  # steel mid
    'l': (172, 192, 232),  # steel lit face
    'h': (228, 240, 255),  # highlight
    'w': (255, 255, 255),  # rim / arc core
    'a': (64, 224, 255),   # arc glow (cyan)
    'k': (26, 18, 30),     # stripe black
    'y': (250, 200, 44),   # stripe yellow
    'Y': (198, 108, 28),   # stripe yellow shade (to orange)
    'g': (74, 68, 112),    # rail plate
    'R': (255, 62, 54),    # lamp on
    'r': (104, 22, 44),    # lamp off
    's': (255, 150, 60),   # spark
})
RAIL_Y = 22
BLADE_HW = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6]


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
    rng = np.random.default_rng(1000 + f * 7 + gap)
    n = x1 - x0
    ctrl = np.concatenate([[0], rng.uniform(-3.2, 3.2, 4), [0]])
    cx = np.linspace(0, n, len(ctrl))
    pts = []
    for i in range(n + 1):
        u = i / n
        y = y0 + (y1 - y0) * u - 2.5 * sin(pi * u) + np.interp(i, cx, ctrl)
        pts.append((x0 + i, int(round(y))))
    return pts


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
            ty = int(round(13 - 9 * e))
            tips.append((c, ty, e, v))
            # shaft (chrome column with rings that travel with it)
            for y in range(ty + 14, RAIL_Y):
                for j, ch in enumerate('mhlmdo'):
                    put(idx, c - 3 + j, y, PA['d'] if (y - ty) % 4 == 1 and ch != 'o' else PA[ch])
            # collar
            for x in range(c - 5, c + 5):
                put(idx, x, ty + 12, PA['o'])
                put(idx, x, ty + 13, PA['h'] if x < c - 3 else PA['l'] if x < c + 1 else PA['m'] if x < c + 3 else PA['d'])
            # blade: lit left face, shadow right face, white rim on the lit edge, mid rim on the shadow edge
            for j, hw in enumerate(BLADE_HW):
                y = ty + j
                for x in range(c - hw, c + hw):
                    if j == 0 or x == c - hw:
                        ch = 'w'
                    elif x == c + hw - 1:
                        ch = 'm'
                    elif x == c - 1 and hw >= 3:
                        ch = 'h'
                    elif x < c:
                        ch = 'l'
                    else:
                        ch = 'd'
                    put(idx, x, y, PA[ch])
        # rail housing
        for y in range(RAIL_Y - 2, H):
            for x in range(W):
                c = None
                rel = (x % 16) - 8
                if y < RAIL_Y:                      # sleeves the pistons run in
                    if -7 <= rel < 7:
                        if y == RAIL_Y - 2:
                            c = 'w' if rel < -4 else 'h'
                        else:
                            c = 'o' if rel in (-7, 6) else 'm' if rel < 0 else 'd'
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
                if c:
                    idx[y, x] = PA[c]
        # lamps between pistons: lit while the piston to their right is thrusting or ringing
        for i in range(4):
            c, ty, e, v = tips[i]
            on = v > 1.0 or (e > 0.9 and abs(v) > 0.6)
            for x in (c - 9, c - 8):
                put(idx, x, RAIL_Y + 1, PA['R' if on else 'r'])
                put(idx, x, RAIL_Y + 2, PA['Y' if on else 'o'])
        # electric arc between the two raised neighbours; it hops along with the piston wave
        for i in range(4):
            c0, t0, e0, _ = tips[i]
            c1, t1, e1, _ = tips[(i + 1) % 4]
            if e0 > 0.8 and e1 > 0.8:
                pts = arc_path(f, i, c0, t0 - 1, c0 + 15, t1 - 1)
                py = pts[0][1]
                core = []
                for (x, y) in pts:
                    for yy in range(min(py, y), max(py, y) + 1):
                        core.append((x, yy))
                    py = y
                for (x, y) in core:
                    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                        put(idx, x + dx, y + dy, PA['a'], only=(0,))
                for (x, y) in core:
                    put(idx, x, y, PA['w'], only=(0, PA['a']))
        # slam sparks: thrown from the sleeve when a piston hits its first overshoot peak, ballistic
        for i in range(4):
            c = 8 + 16 * i
            for age_f in range(0, 4):
                ff = (f - 4 * i - age_f) % NF
                if ff != 2:
                    continue
                t = age_f / NF
                for k, (vx, vy) in enumerate(((-70, -95), (62, -110), (-110, -40), (104, -52))):
                    x = c + (-6 if vx < 0 else 6) + vx * t
                    y = RAIL_Y - 3 + vy * t + 0.5 * 900 * t * t
                    if y < RAIL_Y - 2:
                        put(idx, x, y, PA['w' if age_f == 0 else 's' if age_f < 3 else 'R'], only=(0,))
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
SPOTS = [(6, 4.6, 2, 0.00, 1.00), (17, 3.2, 3, 0.37, 0.90), (27.5, 5.0, 2, 0.61, 1.00),
         (38, 3.0, 3, 0.13, 0.88), (48.5, 4.8, 2, 0.30, 1.00), (59, 3.4, 3, 0.75, 0.92)]  # x, width, puffs/loop, phase, strength
FMODES = [(1, 30, 1, 2, 10, 0.0), (2, 22, -1, 2, 13, 1.3), (3, 16, 2, 3, 11, 2.1), (5, 12, -2, 3, 8, 4.0)]
# n (x harmonics per tile), vertical wavelength px, time harmonics of the sideways drift, of the upward drift, speed px/loop, phase


def fire_source(x, t):
    s = 0.40 + 0.08 * np.sin(TAU * (3 * x / W + t))
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
            T = np.maximum(T - dt * (1.9 + 5.0 * np.clip((11 - Y) / 9.0, 0, 1)), 0)   # cold air entrained higher up
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
        T = blur_y(blur_x(Ts[f], 0.75), 0.6)
        idx = np.zeros((H, W), np.uint8)
        for th, ch in ((0.075, 'D'), (0.21, 'r'), (0.40, 'O'), (0.61, 'Y'), (0.83, 'w')):
            idx[T > th] = PB[ch]
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
DROPS = [(14, -60), (30, -74), (-9, -48)]   # px/loop; gravity below
GRAV_W = 340.0


def render_water():
    states, events = sim_water()
    frames, surf = [], []
    for f in range(NF):
        t = f / NF
        xs, y, J, F = states[f]
        h = blur_x(np.interp(XS, xs, y, period=W), 0.8)
        Fp = np.interp(XS, xs, F, period=W)
        slope = (np.roll(h, -1) - np.roll(h, 1)) / 2
        ysurf = WY0 - h
        top = np.floor(ysurf + 0.5).astype(int)
        tb = 1.2 + np.clip(7.0 * blur_x(slope, 1.0), 0, 3.6)
        yb2 = 22.5 - deep_shift(t, 8.5)
        yb3 = 29.5 - deep_shift(t, 15.0)
        # caustics: rays refracted by the surface slope, counted where they land (real ray density)
        hs = np.interp(xs % W, XS, blur_x(h, 1.6), period=W)        # smoothed height at the Lagrangian samples
        sl = np.gradient(hs) / np.gradient(np.unwrap(xs % W, period=W))
        wgt = np.gradient(np.unwrap(xs % W, period=W))
        I = np.zeros((H, W))
        for yrow in range(H):
            D = yrow + 0.5 - (WY0 - y)
            ok = D > 0
            xl = (xs + D * (0.30 + 0.5 * sl)) % W
            I[yrow] = np.bincount(np.floor(xl[ok]).astype(int) % W, weights=wgt[ok], minlength=W)[:W]
        I = blur_y(blur_x(I, 2.0), 0.9)
        I = I / max(I[20:].mean(), 1e-6)
        idx = np.zeros((H, W), np.uint8)
        for x in range(W):
            for yy in range(max(top[x], 0), H):
                d = yy - top[x]
                if d == 0:
                    c = 'c'
                elif d <= tb[x]:
                    c = 'B'
                elif yy + 0.5 < yb2[x]:
                    c = 'b'
                elif yy + 0.5 < yb3[x]:
                    c = 'n'
                else:
                    c = 'o'
                idx[yy, x] = PC[c]
        idx = despeckle(idx)
        # lit wave backs: the face turned to the light (upper left) gets a second row of skin colour
        for x in range(W):
            if slope[x] < -0.22 and 0 <= top[x] + 1 < H:
                idx[top[x] + 1, x] = PC['c']
        # shimmer: on three depth lines that ride the orbital motion, light a dash where the refracted rays focus
        up = {PC['o']: PC['n'], PC['n']: PC['b'], PC['b']: PC['B'], PC['B']: PC['c']}
        for dd, thr in ((6.0, 1.16), (11.0, 1.2), (16.0, 1.24)):
            ys = np.floor(WY0 + dd - deep_shift(t, dd)).astype(int)
            run = I[np.clip(ys, 0, H - 1), np.arange(W)] > thr
            run = run & (np.roll(run, 1) | np.roll(run, -1))
            for x in range(W):
                if run[x] and 0 <= ys[x] < H and ys[x] > top[x] + tb[x] + 1 and idx[ys[x], x] in up:
                    idx[ys[x], x] = up[idx[ys[x], x]]
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
        # splash droplets on ballistic arcs
        for (t0, x0, y0) in events:
            age = (t - t0) % 1.0
            for vx, vy in DROPS:
                x = x0 + vx * age
                yd = y0 - 1.5 + vy * age + 0.5 * GRAV_W * age * age
                if age > 0.01 and yd < ysurf[int(x) % W] - 0.5:
                    c = PC['w' if vy + GRAV_W * age < 0 else 'f']
                    put(idx, x, yd, c, only=(0,))
                    put(idx, x + 1, yd, c, only=(0,))
                    if age < 0.12:
                        put(idx, x, yd + 1, c, only=(0,))
                        put(idx, x + 1, yd + 1, PC['f'], only=(0,))
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
    'Q': (170, 92, 70),    # crust lit top
    'P': (92, 8, 46),      # coldest lava (maroon, hue to violet)
    'D': (150, 18, 34),    # deep red
    'r': (222, 50, 28),    # red
    'O': (250, 124, 26),   # orange
    'y': (255, 200, 56),   # yellow
    'Y': (255, 248, 190),  # white-hot
})
LY0 = 12.0
NODES = [14.0, 29.5, 45.0, 61.5, 78.0]       # upwelling, downwelling, upwelling, downwelling, (wrap)
BUB = [(14.0, 6.5, 6, 1.0), (45.0, 4.6, 14, 0.72)]   # x, max radius, burst frame (even: survives the 8-frame cut), droplet scale
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
        sp = CRUST_U * np.abs(lava_us(xs))
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
        Xs = X - 4.0 * np.sin(TAU * t + Dp / 5.0) * np.clip(Dp / 6.0, 0, 1)
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
                s = np.maximum(s, amp * np.exp(-(wrapd(X, bx) / 5.0) ** 2))
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
            for j in range(4):
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
                else:                                # downwelling: plates jam and tip under
                    put(idx, x, tp, PD['o'])
                    put(idx, x, tp + 1, PD['k'])
                    put(idx, x, tp + 2, PD['o'])
                    put(idx, x, tp + 3, PD['k'])
                continue
            ck = min(cracks, key=lambda c: abs(wrapd(x + 0.5, c[0]))) if cracks else None
            dck = abs(wrapd(x + 0.5, ck[0])) if ck else 99
            cw = 0.5 if (ck and ck[1] > 1.6) else 1.0
            if ag < 0.3:                             # fresh skin
                put(idx, x, tp, PD['y'])
                put(idx, x, tp + 1, PD['O'])
            elif dck < cw:                           # crack: the melt shows through
                put(idx, x, tp - 1, 0 if True else 0)
                put(idx, x, tp, PD['Y' if heat[0] > 0.6 and ck[1] < 1.2 else 'y'])
                put(idx, x, tp + 1, PD['O'])
            else:
                th = 3 if ag < 1.0 else 4 if ag < 2.0 else 5
                lit = ck is not None and 0 < wrapd(x + 0.5, ck[0]) < 5.2   # plate end facing the light (left)
                put(idx, x, tp - 2, PD['Q' if lit else 'K'])
                put(idx, x, tp - 1, PD['K' if lit else 'k'])
                for j in range(th - 2):
                    put(idx, x, tp + j, PD['k'])
                put(idx, x, tp + th - 2, PD['o'])
                if ag < 0.7:                         # young plate: thin, still glowing dull red on top
                    put(idx, x, tp - 2, 0)
                    put(idx, x, tp - 1, PD['D'])
                    put(idx, x, tp, PD['k'])
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


# ================================================================ output
HAZ = [
    ('A', 'spikes', PA, render_spikes),
    ('B', 'fire', PB, render_fire),
    ('C', 'water', PC, render_water),
    ('D', 'lava', PD, render_lava),
]
LURK_X = 118


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


def scene_frame(base, key, pal, frames, extra, f):
    s = base.copy()
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
    return len(names)


def save_gif(path, imgs, ms):
    imgs = [im.convert('RGB').quantize(colors=128, dither=Image.Dither.NONE) for im in imgs]
    imgs[0].save(path, save_all=True, append_images=imgs[1:], duration=ms, loop=0, disposal=1, optimize=False)


def main():
    only = sys.argv[sys.argv.index('--only') + 1] if '--only' in sys.argv else None
    preview = sys.argv[sys.argv.index('--preview') + 1] if '--preview' in sys.argv else None
    base = base_scene()
    for key, name, pal, fn in HAZ:
        if only and key not in only:
            continue
        frames, extra = fn()
        assert len(frames) == NF and all(fr.shape == (H, W) for fr in frames)
        n = colours(key, pal, frames, extra)
        sc = [scene_frame(base, key, pal, frames, extra, f) for f in range(NF)]
        if preview:
            cw, chh = 144, 56
            sheet = Image.new('RGB', (cw * 4 * 3, chh * 4 * 3), (40, 40, 48))
            for f in range(NF):
                cell = sc[f].crop((88, 224 - chh, 88 + cw, 224)).convert('RGB').resize((cw * 3, chh * 3), Image.NEAREST)
                sheet.paste(cell, ((f % 4) * cw * 3, (f // 4) * chh * 3))
            sheet.save(preview.replace('.png', f'_{key}.png'))
            print(key, name, 'colours', n, 'preview written')
            continue
        vf = VFRAMES[key]
        df = [int((frames[i] != frames[(i + 1) % NF]).sum()) for i in range(NF)]
        print('  %s changed pixels per step: seam(15->0)=%d, other steps min=%d max=%d' % (key, df[-1], min(df[:-1]), max(df[:-1])))
        strip = Image.new('RGBA', (W * NF, H), (0, 0, 0, 0))
        for f in range(NF):
            strip.alpha_composite(pal.img(frames[f]), (f * W, 0))
        strip.save(os.path.join(HERE, f'frames_{key}_1x.png'))
        sc[2].convert('RGB').resize((960, 672), Image.NEAREST).save(os.path.join(HERE, f'scene_{key}_3x.png'))
        crop = [s.crop((0, 152, 320, 224)).resize((1280, 288), Image.NEAREST) for s in sc]
        ms16 = int(round(vf * 1000 / 60 / 10)) * 10          # GIF timing is in 10 ms steps
        save_gif(os.path.join(HERE, f'anim_{key}_16f_4x.gif'), crop, ms16)
        save_gif(os.path.join(HERE, f'anim_{key}_8f_4x.gif'), crop[::2], ms16 * 2)
        print('%s %-6s colours=%2d frames=16/8 tiles=%d/%d frame=%d video frames (gif %d ms)'
              % (key, name, n, 8 * 16, 8 * 8, vf, ms16))


if __name__ == '__main__':
    main()
