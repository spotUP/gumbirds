#!/usr/bin/env python3
# Gumbirds, Gum Trip: three candidates for the ONE moving hazard (draft art, nothing in the build reads this).
#
#   A  Skip-rope squall   48 x 48  violet storm knot with a lightning arc that swings round it like a skipping rope
#   B  Flue spinner       32 x 48  torn-off turbine roof vent, furnace-hot slots, saw fins, loose chain
#   C  Cinder flock       32 x 32  tumbling chimney coal with a ring of embers caught in its wake
#
# Motion comes from small simulations that are driven with a force of period 16 frames and run until the
# transient has died (30 to 40 periods); the last period is the loop, so frame 15 leads into frame 0.
#   A: puffs = damped springs chasing wobbling anchors; arc = 3D chain of 13 spring-linked nodes, ends pinned
#      on the flank puffs, driven by a rotating force (plus its own inertia, like a real skipping rope).
#   B: body = precessing tilt of a spun top (tilt angle = cone angle x cos of precession phase); chain = 6 spring
#      links with gravity and relative wind, hung on the moving collar.
#   C: embers = damped springs chasing points on a tilted ring (different lags and speeds 1x / 2x), relative wind
#      on the trails; coal = rigid tumble, one turn per loop.
# The arc gets per-frame jag noise on top of the simulated chain (seeded, deterministic).
#
# Reads only files inside this folder (bg_storm_1x.png and sootling_sheet_1x.png are copies of
# ../2026-11-10-backgrounds-final/scene_storm_1x.png and ../2026-11-10-sootling-final/sootling_final_sheet_1x.png).
# Run: /opt/homebrew/bin/python3.14 -I draw_moving_hazard.py     (Pillow + numpy, about 20 s)
import os
import sys
sys.dont_write_bytecode = True
import math
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
N = 16                     # frames per loop
KEY = (255, 0, 255)
TAU = 2 * math.pi
CL = np.array([[12, 5, 6, 13], [4, 0, 1, 7], [11, 3, 2, 8], [15, 10, 9, 14]]) / 16.0   # clustered-dot map


def q5(c):
    return tuple(((v >> 3) << 3) | (v >> 5) for v in c)


def grid(w, h):
    y, x = np.mgrid[0:h, 0:w]
    return x.astype(float), y.astype(float)


def cl(w, h):
    y, x = np.mgrid[0:h, 0:w]
    return CL[y % 4, x % 4]


def line_pts(x0, y0, x1, y1):
    x0, y0, x1, y1 = int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
    n = max(abs(x1 - x0), abs(y1 - y0), 1)
    return [(int(round(x0 + (x1 - x0) * i / n)), int(round(y0 + (y1 - y0) * i / n))) for i in range(n + 1)]


def put(idx, x, y, c, only_empty=False):
    h, w = idx.shape
    if 0 <= x < w and 0 <= y < h and (not only_empty or idx[y, x] == 0):
        idx[y, x] = c


def outline(idx, dark, lit=None):
    """Edge pixels facing right/down become `dark`; edge pixels facing only left/up become `lit` (if given)."""
    op = idx > 0
    p = np.pad(op, 1)
    right, down = ~p[1:-1, 2:], ~p[2:, 1:-1]
    left, up = ~p[1:-1, :-2], ~p[:-2, 1:-1]
    sh = op & (right | down)
    idx[sh] = dark
    if lit is not None:
        idx[op & ~sh & (left | up)] = lit
    return idx


# =============================================================== A  Skip-rope squall
PAL_A = [q5(c) for c in [(16, 8, 40), (49, 33, 82), (82, 57, 123), (123, 90, 165), (173, 140, 206), (222, 206, 247),
                         (57, 115, 189), (123, 206, 247), (41, 74, 165), (148, 239, 255), (255, 255, 255),
                         (255, 247, 140)]]
A_OL, A_V0, A_LITM, A_LITB, A_HALO, A_CY, A_WH, A_YE = 1, 2, 7, 8, 9, 10, 11, 12
PUFFS = [(24, 24, 11, 0.0, 3), (13, 27, 8, 1.1, 1), (35, 27, 8, 2.3, 1), (17, 17, 8, 3.0, 0), (30, 16, 7.5, 4.1, 0),
         (7, 27, 5, 5.0, 0), (41, 27, 5, 0.7, 0), (19, 31, 6.5, 1.9, 2), (29, 31, 6.5, 3.6, 2), (24, 13, 6, 5.6, -1)]
PUFFS = [(24 + (x - 24) * 0.85, 24 + (y - 24) * 0.85, r * 0.85, ph, zo) for (x, y, r, ph, zo) in PUFFS]   # leave room for the arc


def sim_squall():
    sub, loops = 16, 40
    dt = 1.0 / sub
    base = np.array([[p[0], p[1], p[2]] for p in PUFFS], float)          # x, y, r
    ph = np.array([p[3] for p in PUFFS])
    pos = base.copy()
    vel = np.zeros_like(pos)
    M, ltot = 13, 68.0
    rest = ltot / (M - 1)
    rope = np.zeros((M, 3))
    rope[:, 0] = np.linspace(4, 44, M)
    rope[:, 1] = 29 + 12 * np.sin(np.linspace(0, math.pi, M))
    rv = np.zeros_like(rope)
    out_p, out_r = [], []
    for step in range(N * sub * loops):
        t = step * dt
        w = TAU * t / N
        anc = base.copy()
        anc[:, 0] += 1.9 * np.cos(w + ph)
        anc[:, 1] += 1.3 * np.sin(w + ph * 1.7)
        anc[:, 2] += 0.9 * np.sin(2 * w + ph)
        vel += (0.10 * (anc - pos) - 0.22 * vel) * dt
        pos += vel * dt
        # rope: springs between neighbours, rotating drive, light air drag
        d = rope[1:] - rope[:-1]
        ln = np.linalg.norm(d, axis=1, keepdims=True)
        f = 5.0 * (ln - rest) * d / np.maximum(ln, 1e-6)
        acc = np.zeros_like(rope)
        acc[:-1] += f
        acc[1:] -= f
        acc[:, 1] += 1.3 * math.cos(w)
        acc[:, 2] += 1.3 * math.sin(w)
        acc -= 0.30 * rv
        rv += acc * dt
        rope += rv * dt
        rope[0] = (pos[5, 0] - 5.5, pos[1, 1] - 3, 0)
        rope[-1] = (pos[6, 0] + 5.5, pos[2, 1] - 3, 0)
        rv[0] = rv[-1] = 0
        if step >= N * sub * (loops - 2) and step % sub == 0:
            out_p.append(pos.copy())
            out_r.append(rope.copy())
    seam = float(np.abs(np.array(out_r[:N]) - np.array(out_r[N:])).max())
    return out_p[N:], out_r[N:], seam


def rope_pixels(rope, t):
    rng = np.random.default_rng(700 + t)
    nodes = rope.copy()
    nodes[1:-1, :2] += rng.normal(0, 0.8, (len(nodes) - 2, 2))
    dense = []
    for i in range(len(nodes) - 1):
        a, b = nodes[i], nodes[i + 1]
        m = (a + b) / 2
        m[:2] += rng.normal(0, 0.8, 2)
        dense += [a, m]
    dense.append(nodes[-1])
    pts = []
    for a, b in zip(dense[:-1], dense[1:]):
        for (x, y) in line_pts(a[0], a[1], b[0], b[1]):
            pts.append((x, y, (a[2] + b[2]) / 2))
    return pts


def draw_arc(idx, pts, front, C):
    h, w = idx.shape
    sel = [(x, y) for (x, y, z) in pts if (z >= 0) == front]
    for (x, y) in sel:
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                r = abs(dx) + abs(dy)
                if r == 0 or r > 2:
                    continue
                xx, yy = x + dx, y + dy
                if 0 <= xx < w and 0 <= yy < h and idx[yy, xx] in (0,):
                    if r == 1 or C[yy, xx] < 0.45:
                        idx[yy, xx] = A_HALO
    for (x, y) in sel:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            xx, yy = x + dx, y + dy
            if 0 <= xx < w and 0 <= yy < h and idx[yy, xx] != A_WH:
                idx[yy, xx] = A_CY
    for (x, y) in sel:
        put(idx, x, y, A_WH)


def render_squall(t, puffs, rope):
    W = H = 48
    X, Y = grid(W, H)
    C = cl(W, H)
    idx = np.zeros((H, W), np.uint8)
    pts = rope_pixels(rope, t)
    draw_arc(idx, pts, False, C)
    best = np.full((H, W), -1e9)
    nx = np.zeros((H, W))
    ny = np.zeros((H, W))
    nz = np.ones((H, W))
    for (px, py, pr), meta in zip(puffs, PUFFS):
        dx, dy = X - px, Y - py
        d2 = dx * dx + dy * dy
        ins = d2 < pr * pr
        hz = np.sqrt(np.maximum(pr * pr - d2, 0))
        hh = hz + meta[4]
        m = ins & (hh > best)
        best[m] = hh[m]
        nx[m], ny[m], nz[m] = dx[m] / pr, dy[m] / pr, hz[m] / pr
    mask = (best > -1e8) & (Y <= 34)
    L = np.array([-0.5, -0.62, 0.6])
    L /= np.linalg.norm(L)
    diff = nx * L[0] + ny * L[1] + nz * L[2]
    diff -= np.clip((Y - 28) / 10, 0, 1) * 0.45            # flat base sits in its own shadow
    v = np.clip((diff + 0.02) / 0.98, 0, 0.999) * 5
    band = np.clip(np.floor(v + (C - 0.5) * 0.75), 0, 4).astype(int)
    body = (A_V0 + band).astype(np.uint8)
    # arc light on the vapour
    dmin = np.full((H, W), 99.0)
    for (x, y, z) in pts:
        if z < -3:
            continue
        dmin = np.minimum(dmin, np.hypot(X - x, Y - y) + (0 if z >= 0 else 1.5))
    body[(dmin + (C - 0.5) * 2.5 < 3.6)] = A_LITM
    body[dmin < 1.6] = A_LITB
    cloud = np.zeros((H, W), np.uint8)
    cloud[mask] = body[mask]
    keep = cloud.copy()
    outline(cloud, A_OL)
    rim = (cloud == A_OL) & (keep >= A_V0 + 3) & (keep <= A_V0 + 4)      # no outline where the light hits
    cloud[rim] = keep[rim]
    idx[cloud > 0] = cloud[cloud > 0]
    draw_arc(idx, pts, True, C)
    for k, e in enumerate((rope[0], rope[-1])):
        x, y = int(round(e[0])), int(round(e[1]))
        if (t + k) % 2 == 0:
            for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1), (2, 0), (-2, 0), (0, 2), (0, -2)):
                put(idx, x + dx, y + dy, A_YE if abs(dx) + abs(dy) else A_WH)
        else:
            for dx, dy in ((0, 0), (1, 1), (-1, -1), (1, -1), (-1, 1)):
                put(idx, x + dx, y + dy, A_YE if abs(dx) + abs(dy) else A_WH)
    return idx


# =============================================================== B  Flue spinner
PAL_B = [q5(c) for c in [(16, 16, 41), (41, 49, 90), (82, 99, 148), (132, 156, 206), (197, 214, 247),
                         (255, 255, 255), (255, 214, 66), (206, 140, 33), (222, 57, 41), (255, 148, 49),
                         (255, 231, 115), (140, 66, 57)]]
B_OL, B_S0, B_WH, B_YL, B_YD, B_RED, B_OR, B_HY, B_RUST = 1, 2, 6, 7, 8, 9, 10, 11, 12
RU, RV = 11.0, 9.5
JAG = [0, 2, -1, 1, 3, 0, -2, 1, 2, -1, 0, 2]


def vent_pose(t):
    psi = TAU * t / N
    th = math.radians(13) * math.cos(psi)
    return 16 + 1.2 * math.sin(psi), 13.5 + 0.8 * math.sin(2 * psi), th


def vent_attach(t):
    cx, cy, th = vent_pose(t)
    u, v = -3.0, RV + 7.5
    return cx + u * math.cos(th) - v * math.sin(th), cy + u * math.sin(th) + v * math.cos(th)


def sim_chain():
    sub, loops, M, rest = 16, 30, 6, 2.5
    dt = 1.0 / sub
    p = np.array([[vent_attach(0)[0] + 0.5 * i, vent_attach(0)[1] + rest * i] for i in range(M)], float)
    vel = np.zeros_like(p)
    out = []
    for step in range(N * sub * loops):
        t = step * dt
        d = p[1:] - p[:-1]
        ln = np.linalg.norm(d, axis=1, keepdims=True)
        f = 14.0 * (ln - rest) * d / np.maximum(ln, 1e-6)
        acc = np.zeros_like(p)
        acc[:-1] += f
        acc[1:] -= f
        acc[:, 1] += 0.22
        acc[:, 0] += 0.10 + 0.05 * math.sin(2 * TAU * t / N)       # relative wind, gusting
        acc -= 0.9 * vel
        vel += acc * dt
        p += vel * dt
        p[0] = vent_attach(t)
        vel[0] = 0
        if step >= N * sub * (loops - 2) and step % sub == 0:
            out.append(p.copy())
    seam = float(np.abs(np.array(out[:N]) - np.array(out[N:])).max())
    return out[N:], seam


def render_vent(t, chain):
    W, H = 32, 48
    X, Y = grid(W, H)
    idx = np.zeros((H, W), np.uint8)
    cx, cy, th = vent_pose(t)
    ct, st = math.cos(th), math.sin(th)
    U = ct * (X - cx) + st * (Y - cy)
    V = -st * (X - cx) + ct * (Y - cy)
    Ls = np.array([-0.55, -0.6, 0.58])
    Ls /= np.linalg.norm(Ls)
    Lu, Lv, Lz = ct * Ls[0] + st * Ls[1], -st * Ls[0] + ct * Ls[1], Ls[2]
    spin = 3.0 * t / N
    KF, TW = 5.0, 0.35
    # finial
    idx[(np.abs(U) < 1.1) & (V > -RV - 3.6) & (V < -RV + 1)] = B_S0 + 2
    idx[(np.abs(U) < 1.6) & (V > -RV - 5.2) & (V <= -RV - 3.6)] = B_S0 + 3
    # collar with warning stripes and a torn lower edge
    ji = np.clip(np.floor(U + 6).astype(int), 0, 11)
    jag = np.array(JAG)[ji]
    col = (np.abs(U) < 5.6) & (V > RV - 2) & (V < RV + 6.5 + jag)
    stripe = (np.floor((U + V) / 3.0).astype(int) % 2) == 0
    cc = np.where(stripe, np.where(U > 1.5, B_YD, B_YL), np.where(U < -3.2, B_S0 + 1, B_S0))
    torn = col & (V > RV + 5.3 + jag)
    idx[col] = cc[col]
    idx[torn] = B_RUST
    fl = (np.abs(U) < 7.6) & (V > RV - 2.6) & (V < RV + 0.2)
    idx[fl] = np.where(V > RV - 0.9, B_S0, np.where(U < -1, B_S0 + 3, B_S0 + 2))[fl]
    # globe
    nu, nv = U / RU, V / RV
    q = nu * nu + nv * nv
    ins = q < 1
    nz = np.sqrt(np.maximum(1 - q, 0))
    diff = nu * Lu + nv * Lv + nz * Lz
    lev = np.select([diff < 0.02, diff < 0.42, diff < 0.78], [0, 1, 2], 3)
    s = np.clip(nu / np.sqrt(np.maximum(1 - nv * nv, 1e-6)), -1, 1)
    p = (np.arcsin(s) / math.pi * KF + TW * nv + spin) % 1.0
    slotted = np.abs(nv) < 0.70
    g = lev.copy()
    g = np.where(slotted & (p >= 0.24) & (p < 0.42), np.minimum(lev + 1, 3), g)
    g = np.where(slotted & (p >= 0.80), np.maximum(lev - 1, 0), g)
    g = np.where((np.abs(nv) >= 0.70) & (np.abs(nv) < 0.80), np.maximum(lev - 1, 0), g)
    gc = (B_S0 + g).astype(np.uint8)
    gc[(diff > 0.93) & ~(slotted & (p < 0.24))] = B_WH
    gc[slotted & (p >= 0.24) & (p < 0.34) & (diff > 0.6)] = B_WH
    slot = slotted & (p < 0.24)
    hot = np.select([nz > 0.88, nz > 0.55, nz > 0.25], [B_HY, B_OR, B_RED], B_OL)
    gc[slot] = hot[slot]
    idx[ins] = gc[ins]
    # cap
    cap = ((U / 5.5) ** 2 + ((V + RV - 0.6) / 2.0) ** 2) < 1
    idx[cap] = np.where(U < -1, B_S0 + 3, B_S0 + 2)[cap]
    # saw fins: a vane rib grows out of the limb as it passes the edge of the globe
    e = RU * np.sqrt(np.maximum(1 - nv * nv, 0))
    for side in (-1, 1):
        for v0, off in ((-3.5, 0.0), (3.5, 0.5)):
            pe = (side * KF / 2 + TW * v0 / RV + spin + off) % 1.0
            ln = 6.5 * max(0.0, 1 - abs(pe - 0.4) / 0.4)
            d = side * U - e
            fin = (d >= -0.5) & (d < ln * (1 - np.abs(V - v0) / 2.6)) & ~ins
            idx[fin] = np.where(V < v0, B_S0 + 3, B_S0 + 2)[fin]
    keep = idx.copy()
    outline(idx, B_OL)
    hotedge = (idx == B_OL) & np.isin(keep, (B_OR, B_HY))
    idx[hotedge] = B_RED
    # chain and hook
    for i in range(len(chain) - 1):
        a, b = chain[i], chain[i + 1]
        for k, (x, y) in enumerate(line_pts(a[0], a[1], b[0], b[1])):
            put(idx, x, y, B_S0 + 3 if (i % 2 == 0) else B_S0 + 1)
            put(idx, x + 1, y, B_OL, only_empty=True)
    hx, hy = int(round(chain[-1][0])), int(round(chain[-1][1]))
    for dx, dy, c in ((0, 0, 3), (0, 1, 3), (1, 2, 2), (1, 3, 2), (0, 4, 2), (-1, 4, 3), (-2, 3, 3), (-2, 2, 4)):
        put(idx, hx + dx, hy + dy, B_S0 + c - 1)
    return idx


# =============================================================== C  Cinder flock
PAL_C = [q5(c) for c in [(24, 16, 33), (57, 41, 66), (99, 82, 115), (90, 16, 41), (173, 33, 33), (231, 82, 24),
                         (255, 148, 24), (255, 206, 66), (255, 247, 173), (255, 255, 255)]]
C_OL, C_C1, C_C2, C_MAR, C_RED, C_ORR, C_OR, C_YE, C_PALE, C_WH = range(1, 11)
EMB = [  # ring radius, speed multiple, phase, spring k, damping, size
    (13.5, 1, 0.0, 0.10, 0.30, 2), (12.5, 1, 2.2, 0.06, 0.22, 2), (14.0, 1, 4.3, 0.16, 0.40, 1),
    (10.0, 2, 1.0, 0.20, 0.35, 1), (11.0, 2, 3.9, 0.12, 0.30, 0), (14.0, 1, 5.4, 0.08, 0.26, 0), (9.5, -1, 0.6, 0.14, 0.3, 0)]
CRACKS = [((-3.2, -1.0), (0.0, 0.5)), ((0.0, 0.5), (2.6, -2.2)), ((0.0, 0.5), (1.0, 3.6)), ((-2.2, 2.8), (-0.6, 1.0))]


def sim_embers():
    sub, loops = 8, 30
    dt = 1.0 / sub
    n = len(EMB)
    pos = np.zeros((n, 2))
    vel = np.zeros((n, 2))
    hist = []
    for step in range(N * sub * loops):
        t = step * dt
        w = TAU * t / N
        for i, (rho, m, ph, k, c, sz) in enumerate(EMB):
            a = m * w + ph
            tgt = np.array([16 + rho * math.cos(a), 16 + 0.55 * rho * math.sin(a) + 0.25 * rho * math.cos(a)])
            acc = k * 8 * (tgt - pos[i]) - c * 4 * vel[i]
            acc[0] += 0.5 * math.cos(2 * w)                  # gust
            vel[i] += acc * dt
            pos[i] += vel[i] * dt
        if step >= N * sub * (loops - 2):
            hist.append(pos.copy())
    hist = np.array(hist)
    seam = float(np.abs(hist[:N * sub] - hist[N * sub:]).max())
    return hist[N * sub:], sub, seam


def render_cinder(t, hist, sub):
    W = H = 32
    X, Y = grid(W, H)
    C = cl(W, H)
    idx = np.zeros((H, W), np.uint8)
    w = TAU * t / N
    ccx, ccy = 16 + 0.8 * math.sin(w), 16 + 0.8 * math.sin(2 * w + 1)
    now = hist[t * sub]
    total = len(hist)
    depth = [math.sin(m * w + ph) for (rho, m, ph, k, c, sz) in EMB]
    # glow field
    G = 0.85 * np.exp(-((X - ccx + 4) ** 2 + (Y - ccy - 1) ** 2) / (2 * 4.6 ** 2))
    for i, e in enumerate(EMB):
        G += (0.5 + 0.15 * e[5]) * np.exp(-((X - now[i, 0]) ** 2 + (Y - now[i, 1]) ** 2) / (2 * 1.9 ** 2))
    Gd = G + (C - 0.5) * 0.22
    idx[Gd > 0.34] = C_MAR
    idx[Gd > 0.62] = C_RED
    idx[Gd > 1.02] = C_ORR

    def ember(i):
        for j in range(10, 0, -1):                             # trail, oldest first; relative wind drags it right
            px, py = hist[(t * sub - j) % total][i]
            c = C_YE if j <= 2 else C_OR if j <= 4 else C_ORR if j <= 7 else C_RED
            if j > 6 and j % 2:
                continue
            put(idx, int(round(px + 0.35 * j)), int(round(py + 0.08 * j)), c)
        x, y = int(round(now[i, 0])), int(round(now[i, 1]))
        sz = EMB[i][5]
        if sz == 2:
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    r = dx * dx + dy * dy
                    if r <= 5:
                        put(idx, x + dx, y + dy, C_WH if r == 0 else C_PALE if r <= 1 else C_YE if r <= 2 else C_OR)
        elif sz == 1:
            for dx, dy in ((1, 1), (-1, -1), (1, -1), (-1, 1)):
                put(idx, x + dx, y + dy, C_OR)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                put(idx, x + dx, y + dy, C_YE)
            put(idx, x, y, C_WH)
        else:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                put(idx, x + dx, y + dy, C_OR)
            put(idx, x, y, C_PALE)

    for i in range(len(EMB)):
        if depth[i] < 0:
            ember(i)
    # coal: irregular lump, one turn per loop
    rot = w
    dx, dy = X - ccx, Y - ccy
    phi = np.arctan2(dy, dx)
    rr = np.hypot(dx, dy)
    rad = 6.6 + 1.0 * np.cos(3 * (phi - rot) + 0.5) + 0.6 * np.cos(5 * (phi - rot) + 2.0)
    coal = rr < rad
    a = math.cos(rot) * dx + math.sin(rot) * dy
    b = -math.sin(rot) * dx + math.cos(rot) * dy
    lit = (-0.55 * dx - 0.65 * dy) / np.maximum(rad, 1)
    facet = np.floor((a * 0.9 + b * 0.5 + 9) / 2.6).astype(int) % 2
    cc = np.where(lit + 0.25 * facet > 0.38, C_C2, np.where(lit + 0.25 * facet > -0.25, C_C1, C_OL))
    crack = np.zeros((H, W), bool)
    junction = np.hypot(a - 0.0, b - 0.5) < 1.3
    for (p0, p1) in CRACKS:
        p0, p1 = np.array(p0), np.array(p1)
        dseg = p1 - p0
        tt = np.clip(((a - p0[0]) * dseg[0] + (b - p0[1]) * dseg[1]) / dseg.dot(dseg), 0, 1)
        crack |= np.hypot(a - (p0[0] + tt * dseg[0]), b - (p0[1] + tt * dseg[1])) < 0.62
    cc = np.where(crack, np.where(junction, C_YE, C_OR), cc)
    edge = coal & (rr > rad - 1.3)
    windward = (-dx * 0.95 + dy * 0.3) / np.maximum(rr, 1e-6)
    cc = np.where(edge & (windward > 0.25), C_ORR, cc)
    cc = np.where(edge & (windward > 0.62), C_OR, cc)
    cc = np.where(edge & (windward > 0.88), C_YE, cc)
    cc = np.where(edge & (windward <= 0.25), np.where(lit > 0.3, C_C1, C_OL), cc)
    idx[coal] = cc[coal]
    for i in range(len(EMB)):
        if depth[i] >= 0:
            ember(i)
    return idx


# =============================================================== output helpers
def rgba(idx, pal):
    lut = np.zeros((len(pal) + 1, 4), np.uint8)
    for i, c in enumerate(pal):
        lut[i + 1] = (*c, 255)
    return Image.fromarray(lut[idx], 'RGBA')


def save_sheet(frames, pal, path):
    h, w = frames[0].shape
    sheet = np.concatenate(frames, axis=1)
    im = Image.fromarray(sheet, 'P')
    flat = list(KEY)
    for c in pal:
        flat += list(c)
    im.putpalette(flat + [0] * (768 - len(flat)))
    im.save(path)


def measure(frames):
    h, w = frames[0].shape
    cols = w // 16
    cols_used = set()
    worst = 0
    tiles = set()
    raw = 0
    x0 = y0 = 99
    x1 = y1 = -1
    for f in frames:
        for y in range(h):
            n = sum(1 for c in range(cols) if f[y, c * 16:(c + 1) * 16].any())
            worst = max(worst, n)
        for c in range(cols):
            if f[:, c * 16:(c + 1) * 16].any():
                cols_used.add(c)
            for r in range(h // 16):
                tl = f[r * 16:(r + 1) * 16, c * 16:(c + 1) * 16]
                if tl.any():
                    raw += 1
                    tiles.add(tl.tobytes())
        ys, xs = np.nonzero(f)
        x0, x1, y0, y1 = min(x0, xs.min()), max(x1, xs.max()), min(y0, ys.min()), max(y1, ys.max())
    colours = len(set(np.unique(np.concatenate([f.ravel() for f in frames]))) - {0})
    return dict(w=w, h=h, frames=len(frames), colours=colours, columns=len(cols_used), worst_line=worst,
                tiles_raw=raw, tiles_unique=len(tiles), bbox=(int(x0), int(y0), int(x1), int(y1)))


def soot_frames():
    im = Image.open(os.path.join(HERE, 'sootling_sheet_1x.png'))
    a = np.array(im)
    pal = im.getpalette()
    out = []
    for n in range(8):
        f = a[0:48, n * 32:(n + 1) * 32]
        lut = np.zeros((256, 4), np.uint8)
        for i in range(1, 16):
            lut[i] = (pal[i * 3], pal[i * 3 + 1], pal[i * 3 + 2], 255)
        out.append(Image.fromarray(lut[f], 'RGBA'))
    return out


def save_gif(frames, path, ms):
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=ms, loop=0, optimize=False)


def contact(frames, pal, path, bg=(28, 41, 56)):
    h, w = frames[0].shape
    im = Image.new('RGB', (8 * (w + 4) + 4, 2 * (h + 4) + 4), bg)
    for i, f in enumerate(frames):
        s = rgba(f, pal)
        im.paste(s, (4 + (i % 8) * (w + 4), 4 + (i // 8) * (h + 4)), s)
    im.resize((im.width * 4, im.height * 4), Image.NEAREST).save(path)


def scene_gif(frames, pal, path, motion, soot, bg):
    out = []
    h, w = frames[0].shape
    for g in range(32):
        im = bg.copy()
        s = soot[g % 8]
        im.paste(s, (22, 26 + int(round(3 * math.sin(TAU * g / 16)))), s)
        ox, oy = motion(g)
        spr = rgba(frames[g % N], pal)
        im.paste(spr, (int(round(104 + ox - w / 2)), int(round(48 + oy - h / 2))), spr)
        out.append(im.resize((im.width * 3, im.height * 3), Image.NEAREST))
    save_gif(out, path, 70)


def path_gif(frames, pal, path, traj, soot, bg):
    """traj: list of (x, y) screen centre per tick. One gif frame per 4 ticks at 70 ms (close to real time)."""
    out = []
    h, w = frames[0].shape
    base = Image.eval(bg, lambda v: int(v * 0.4))
    for k in range(0, len(traj), 4):
        im = base.copy()
        px = im.load()
        for y in list(range(0, 8)) + list(range(192, 224)):               # ceiling and floor kill strips
            for x in range(320):
                px[x, y] = (150, 30, 40) if ((x + k + y) // 6) % 2 == 0 else (60, 12, 24)
        for x in range(320):
            px[x, 8] = px[x, 191] = (250, 200, 44)
        for j in range(0, len(traj), 6):                                   # path, future part brighter
            x, y = traj[j]
            if 0 <= x < 319 and 0 <= y < 223:
                for ddx, ddy in ((0, 0), (1, 0), (0, 1), (1, 1)):
                    px[int(x) + ddx, int(y) + ddy] = (230, 240, 255) if j >= k else (110, 120, 140)
        s = soot[(k // 4) % 8]
        im.paste(s, (72, 84 + int(round(18 * math.sin(TAU * k / 150)))), s)
        x, y = traj[k]
        spr = rgba(frames[(k // 4) % N], pal)
        im.paste(spr, (int(round(x - w / 2)), int(round(y - h / 2))), spr)
        out.append(im)
    save_gif(out, path, 70)


def traj_a():
    return [(344 - 1.25 * t, 100 + 46 * math.sin(TAU * t / 200)) for t in range(0, 314)]


def traj_b():
    out, y, vy = [], 56.0, 0.0
    for t in range(0, 206):
        out.append((344 - 1.9 * t, y))
        vy += 0.05
        y += vy
        if y >= 150 and vy > 0:
            vy = -2.7                                   # gust kick
    return out


def traj_c():
    T = 280
    out = []
    for t in range(T):
        s = t / T
        e = s * s * (3 - 2 * s)
        out.append((344 - 1.4 * t, 176 - 140 * e + 9 * math.sin(TAU * t / 64)))
    return out


def main():
    bg = Image.open(os.path.join(HERE, 'bg_storm_1x.png')).convert('RGB')
    crop = bg.crop((80, 20, 240, 116))
    soot = soot_frames()
    puffs, ropes, seam_a = sim_squall()
    chain, seam_b = sim_chain()
    hist, sub, seam_c = sim_embers()
    FA = [render_squall(t, puffs[t], ropes[t]) for t in range(N)]
    FB = [render_vent(t, chain[t]) for t in range(N)]
    FC = [render_cinder(t, hist, sub) for t in range(N)]
    cands = [
        ('a', 'Skip-rope squall', FA, PAL_A, traj_a(), lambda g: (0, 5 * math.sin(TAU * g / 32)),
         'x 6..41, y 10..35 (36 x 26): vapour body and the inner sweep of the arc; the outer 4 px of the arc do not hurt',
         'world drift 0.25 px/frame left (1.25 on screen), sine weave 46 px amplitude, period 200 frames',
         seam_a),
        ('b', 'Flue spinner', FB, PAL_B, traj_b(), lambda g: (0, -14 + 0.22 * (g % 32 - 16) ** 2 * 0.25),
         'x 6..25, y 5..24 (20 x 20): the globe; collar and chain do not hurt',
         'world 0.9 px/frame left (1.9 on screen), gravity 0.05, gust kick to -2.7 px/frame at y 150: skipping hops 73 px high, about 108 frames apart',
         seam_b),
        ('c', 'Cinder flock', FC, PAL_C, traj_c(), lambda g: (0, 6 - 12 * (g / 32.0) if g < 32 else 0),
         'x 8..23, y 9..22 (16 x 14): the coal and its inner ring; outer embers and trails do not hurt',
         'rises off the floor strip on a thermal: world 0.4 px/frame left (1.4 on screen), 140 px climb with ease in and out, 9 px sway',
         seam_c),
    ]
    lines = ['Gum Trip moving hazard candidates. Measured by draw_moving_hazard.py from the sheets it wrote.',
             'Columns = 16 px wide sprite columns that hold an opaque pixel in any frame. Worst line = most columns',
             'with an opaque pixel on one scanline in any frame (what one instance adds to that scanline).',
             'Tiles = 16 x 16 tiles, raw = non-empty over all frames, unique = distinct among those.', '']
    html = []
    for (key, name, F, pal, traj, mot, hit, pathtxt, seam) in cands:
        save_sheet(F, pal, os.path.join(HERE, f'sheet_{key}_1x.png'))
        contact(F, pal, os.path.join(HERE, f'contact_{key}_4x.png'))
        scene_gif(F, pal, os.path.join(HERE, f'anim_{key}_3x.gif'), mot, soot, crop)
        path_gif(F, pal, os.path.join(HERE, f'path_{key}_1x.gif'), traj, soot, bg)
        m = measure(F)
        assert m['colours'] <= 15 and m['frames'] >= 12
        rows = [f"{name}",
                f"Frame size {m['w']} x {m['h']} px, {m['frames']} frames per loop, 4 ticks per frame (15 per second)",
                f"Colours {m['colours']} plus key",
                f"Sprite columns {m['columns']} (pool object width {m['w']} px)",
                f"Worst sprites per scanline added by one instance {m['worst_line']}",
                f"Tiles raw {m['tiles_raw']}, unique {m['tiles_unique']}",
                f"Opaque bounding box over all frames x {m['bbox'][0]}..{m['bbox'][2]}, y {m['bbox'][1]}..{m['bbox'][3]}",
                f"Hit box proposal {hit}",
                f"Path {pathtxt}; on screen for {len(traj)} frames",
                f"Loop seam of the simulation (largest position difference between the last two periods) {seam:.4f} px"]
        lines += rows + ['']
        html.append((key, name, rows[1:], m))
    with open(os.path.join(HERE, 'numbers.txt'), 'w') as f:
        f.write('\n'.join(lines))
    print('\n'.join(lines))
    blurb = {
        'a': 'A knot of violet storm vapour. A lightning arc is pinned to its two flanks and swings round it like a skipping rope: behind, under, in front, over.',
        'b': 'A turbine roof vent torn off its flue. The slots still glow furnace-hot, saw fins flick out at the rim as it spins, a loose chain trails in the wind.',
        'c': 'A tumbling lump of chimney coal, white-hot on the windward side, with a ring of embers caught in its wake.'}
    sec = []
    for key, name, rows, m in html:
        sec.append(f'''<section>
<h2>{name}</h2>
<p>{blurb[key]}</p>
<div class="row">
<figure><img src="anim_{key}_3x.gif" width="480" height="288" alt="{name} over the storm sky, 3x"><figcaption>3x, storm sky, Sootling for scale</figcaption></figure>
<figure><img src="path_{key}_1x.gif" width="640" height="448" alt="{name} path on the 320 x 224 screen"><figcaption>Path on the 320 x 224 screen, shown 2x. Pale dots: the way it travels on screen while the world scrolls left at 1 px per frame. Red bands: kill strips.</figcaption></figure>
</div>
<figure><img src="sheet_{key}_1x.png" width="{m['w'] * 16 * 2}" height="{m['h'] * 2}" alt="{name} sheet"><figcaption>Sheet, shown 2x (file is 1x, {m['frames']} frames in a row, magenta key)</figcaption></figure>
<ul>{''.join('<li>' + r + '</li>' for r in rows)}</ul>
</section>''')
    page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Gum Trip moving hazard: three candidates</title>
<style>
body {{ background:#17181c; color:#d6d8de; font-family:Helvetica,Arial,sans-serif; margin:0; padding:32px 40px 80px; line-height:1.5; }}
h1 {{ font-size:26px; margin:0 0 8px; color:#f2f3f6; }}
h2 {{ font-size:21px; margin:0 0 6px; color:#f2f3f6; }}
section {{ border-top:1px solid #34363e; margin-top:36px; padding-top:28px; }}
img {{ image-rendering:pixelated; display:block; background:#0c0d10; border:1px solid #34363e; max-width:none; }}
figure {{ margin:14px 24px 14px 0; overflow-x:auto; }}
figcaption {{ font-size:13px; color:#9a9da8; margin-top:6px; max-width:640px; }}
.row {{ display:flex; flex-wrap:wrap; align-items:flex-start; }}
ul {{ padding-left:20px; font-size:15px; max-width:900px; }}
p {{ max-width:900px; margin:0 0 6px; }}
</style></head><body>
<h1>Gum Trip moving hazard: three candidates</h1>
<p>Pick one. All three loop in 16 frames, hold to 15 colours, and fit a pool object (at most 3 sprite columns). View at 100 percent browser zoom. Ranking and doubts are in README.md.</p>
{''.join(sec)}
</body></html>'''
    with open(os.path.join(HERE, 'index.html'), 'w') as f:
        f.write(page)


if __name__ == '__main__':
    main()
