#!/usr/bin/env python3
# Bubblegum Brawl, fire tile variant C (draft). The fire row becomes A B C (repeat distance 192 px... 96 px in tiles of 2).
# A and B are the accepted tiles of ../2026-11-10-hazards-final (copied from its sheet, asserted pixel-identical).
# C is NOT derived from A or B: it is its own run of the same simulation (fire_v6_base) with its own sources,
# its own leader schedule and its own turbulence phases, on a 192 px periodic domain laid out A B C:
#   - the A and B regions of that domain are overwritten every sub-step with the ORIGINAL 128 px simulation
#     (re-run here, bit-identical: it reproduces the accepted sheet), so C grows against its real neighbours;
#   - a narrow zone at C's left edge follows A's left edge (what follows B in the accepted row) and a zone at C's
#     right edge follows B's right edge (what precedes A), so both seams continue the baked neighbour pixels;
#   - C's sources stay below the leaders of A and B (lower lids), so C never ties with the tallest tongue.
# Same palette (hazards-final PB), same clean-up (flame_fix rules), same dither (dither3, FIRE_MATS), 16 frames.
# Run: /opt/homebrew/bin/python3.14 -I draw_fire_c.py [--cache DIR] [--scratch DIR]      (needs Pillow + numpy)
#   --cache DIR    keeps the re-run of the original simulation between runs (about 19 MB)
#   --scratch DIR  also writes frame sheets for inspection
import os
import sys
from math import pi, sin
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
FINAL = os.path.join(HERE, '..', '2026-11-10-hazards-final')
sys.path.insert(0, FINAL)
import numpy as np
from PIL import Image, ImageDraw
import draw_hazards_final as hf
fb, dv, v4, s6 = hf.fb, hf.dv, hf.v4, hf.s6

PB = hf.PB
NF, H = hf.NF, hf.H
TAU = 2 * pi
WD = 192                       # domain: A = 0..63, B = 64..127, C = 128..191
C0 = 128
SHEET = os.path.join(FINAL, 'frames_fire_1x.png')
VIEW = hf.VIEW
STILL = 2
GIF_MS = 70                    # 4 video frames per step, as the accepted GIFs

# ---------------------------------------------------------------- tile C: its own emitters
# x (global), width, puffs/loop, phase, resting strength, resting pulse depth   (same fields as fb.SPOTS)
SPOTS_C = [(141, 4.4, 3, 0.70, 0.56, 0.36), (153, 2.7, 2, 0.18, 0.48, 0.42), (170, 4.8, 3, 0.52, 0.60, 0.30),
           (186, 2.9, 2, 0.45, 0.48, 0.40)]      # the last one is the twin of B's source at x 122 (seam to A needs it)
# C's own "minor leaders": (source index, on, off, strength, width, pulse depth). Strength under 1.0 keeps the lid low.
LEAD_C = [(9, 0.12, 0.37, 0.80, 5.4, 0.14), (11, 0.62, 0.87, 0.82, 5.6, 0.12)]
NC = {2: 1, 4: 2, 6: 3, 10: 5, 1: 1, 3: 2}       # harmonics per 64 px inside C (integer, so both ends meet A's phase)
DPH = [2.1, 4.4, 1.0, 3.3, 5.2, 0.6]             # extra phase of each turbulence mode inside C (0 at both edges)
BASE_C = 3                                       # low base flame: waves per 64 px inside C (A B: 2.5)
CLAMP_L = 5.0                  # C's left edge follows A's left edge over this many px (weight 1 -> 0)
CLAMP_R = (54.0, 61.0)         # C's right edge follows B's right edge from / fully at (local x)
BACK_L = (8.0, 18.0)           # back row: A's back row until / gone at (the back flame that straddles the seam)
BACK_R = (48.0, 56.0)          # back row: B's back row from / fully at
BACK_MID = (27, 10)            # back row in between: C's own field, shifted px (local wrap), frames later
LUMPS_C = [(131.0, 28.6, 4.4, 3.2),              # copy of A's first lump: its left sliver is baked into B's last column
           (138.6, 28.1, 3.4, 3.5), (145.2, 28.9, 4.2, 2.8), (152.4, 28.0, 3.6, 3.4), (158.8, 28.7, 3.0, 3.1),
           (165.0, 28.1, 4.4, 3.5), (172.4, 28.9, 3.6, 2.7), (178.6, 28.0, 3.4, 3.5), (185.6, 28.7, 4.4, 3.0)]
SPARKS_C = [(9, 0.08, 0.60, 10), (10, 0.27, 0.55, -8), (11, 0.55, 0.66, 7), (12, 0.74, 0.52, -12), (9, 0.41, 0.58, -14),
            (11, 0.90, 0.62, 12), (10, 0.63, 0.50, 6), (11, 0.20, 0.64, -16), (9, 0.80, 0.56, 16), (12, 0.35, 0.50, -6)]


def overrides():
    """FIREC="LEAD_C=[...];CLAMP_L=4.0" sets module constants for a tuning run."""
    import ast
    spec = os.environ.get('FIREC', '')
    for kv in filter(None, spec.split(';')):
        k, v = kv.split('=', 1)
        assert k in globals(), k
        globals()[k] = ast.literal_eval(v)
    return spec


def nsstep(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


# ---------------------------------------------------------------- the same physics on the 192 px domain
def spot_state_c(t):
    """fb.spot_state plus leader entries that carry their own strength / width / pulse depth."""
    out = []
    for i, (x0, wd, m, ph, st, pd) in enumerate(fb.SPOTS):
        ls = la = 0.0
        lst, lwd, lpd = fb.LEAD_ST, fb.LEAD_WD, fb.LEAD_PD
        for e in list(fb.LEAD) + LEAD_C:
            if e[0] == i:
                on, off = e[1], e[2]
                ls = max(ls, fb.win(t, on + fb.LEAD_T0 - fb.LEAD_PRE, off + fb.LEAD_T0, fb.LEAD_RAMP))
                la = max(la, fb.win(t, on + fb.LEAD_T0 - fb.LEAD_PRE, off + fb.LEAD_T0 + fb.LEAD_LAG, fb.LEAD_AIR_RAMP))
                if len(e) > 3:
                    lst, lwd, lpd = e[3:6]
        out.append((x0, wd + (lwd - wd) * ls, m, ph, st + (lst - st) * ls, pd + (lpd - pd) * ls, st + (lst - st) * la))
    return out


def fire_source_c(x, t, P):
    xm = np.mod(x, float(WD))
    s = fb.BASE[0] + fb.BASE[1] * np.sin(TAU * (np.where(xm >= C0, BASE_C * (xm - C0) / 64.0, 5 * xm / 128.0) + t))
    for (x0, wd, m, ph, st, pd, sa) in P:
        amp = st * (1 - pd + pd * sin(TAU * (m * t + ph)))
        xc = x0 + 1.5 * sin(TAU * (t + 3 * ph))
        s = np.maximum(s, amp * np.exp(-(fb.wrapd(x, xc) / wd) ** 2))
    return s


def fire_vel_c(X, Y, t, T, P=None):
    """fb.fire_vel with the turbulence phase laid out per tile: A and B exactly as on the 128 px domain; inside C an
    integer number of waves per 64 px plus a phase offset that is zero at both edges."""
    ramp = np.clip((27 - Y) / 12.0, 0, 1)
    xm = np.mod(X, float(WD))
    inc = xm >= C0
    xl = xm - C0
    bump = nsstep(xl / 14.0) * nsstep((64.0 - xl) / 14.0)
    u = 0
    v = 0
    for j, (n, ly, m, r, A, ph) in enumerate(fb.FMODES):
        kxa, kxc, ky = TAU * n / 128.0, TAU * NC[n] / 64.0, TAU / ly
        kx = np.where(inc, kxc, kxa)
        ax = np.where(inc, kxc * xl + DPH[j] * bump, kxa * xm) + TAU * m * t + ph
        ay = ky * Y + TAU * r * t
        u = u + A * np.sin(ax) * np.cos(ay)
        v = v - A * (kx / ky) * np.cos(ax) * np.sin(ay)
    u, v = u * ramp, v * ramp - (52 + 70 * T)
    if P is not None:
        K, h0, hs, rf, vf = fb.STRAIN
        h = 25.0 - Y
        k = K * np.clip((h - h0) / hs, 0, 1)
        kint = K * (np.clip(h - h0, 0, hs) ** 2 / (2 * hs) + np.clip(h - h0 - hs, 0, None))
        hh = np.clip(h, 0, None)
        for (x0, wd, m, ph, st, pd, sa) in P:
            xc = (x0 + 1.5 * sin(TAU * (t + 3 * ph))
                  + fb.SWAY[0] * (hh / 20.0) ** 1.5 * np.sin(TAU * (fb.SWAY[1] * t + ph - hh / fb.SWAY[2])))
            dx = fb.wrapd(X, xc)
            w = st * np.exp(-(dx / (rf * wd + 2.0)) ** 2)
            u = u - k * dx * w
            v = v - vf * kint * w
    return u, v


def sim(clamp=None):
    """fb.sim_fire, same operations in the same order. clamp=None: plain run that also records the state after
    every sub-step. clamp=recorded states of the 128 px run: the A and B regions are overwritten with them after
    every sub-step and C's two edge zones are pulled toward them."""
    S, sub = 3, 8
    W = fb.W
    gw, gh = W * S, H * S
    X, Y = np.meshgrid((np.arange(gw) + 0.5) / S, (np.arange(gh) + 0.5) / S)
    steps = NF * sub
    dt = 1.0 / steps
    T = np.zeros((gh, gw))
    if clamp is not None:
        xl = (np.arange(64 * S) + 0.5) / S
        wl = 1 - nsstep(xl / CLAMP_L)
        wr = nsstep((xl - CLAMP_R[0]) / (CLAMP_R[1] - CLAMP_R[0]))

        def pin(T, R):
            T[:, :128 * S] = R
            T[:, 128 * S:] = T[:, 128 * S:] * (1 - wl - wr) + wl * R[:, :64 * S] + wr * R[:, 64 * S:]
            return T
        T = pin(T, clamp[-1])
    src_rows = (Y > 23.0) & (Y < 28.5)
    prev = None
    cool = None
    rec = []
    for loop in range(14):
        out, rec = [], []
        for i in range(steps):
            t = i * dt
            if i % sub == 0:
                out.append(T.copy())
            P = fb.spot_state(t)
            if cool is None or i % 2 == 0:
                cool = fb.fire_cool(X, Y, P)
            u, v = fb.fire_vel(X, Y, t, fb.blur_x(T, 1.5), P)
            T = fb.advect(T, u, v, dt, X, Y, S)
            T = fb.blur_y(fb.blur_x(T, 0.26), 0.2)
            T = np.maximum(T - dt * cool * (fb.EDGE[0] + fb.EDGE[1] * (1 - T)), 0)
            s = fb.fire_source(X, t, P)
            T = np.where(src_rows, np.maximum(T, s), T)
            T[Y >= 28.5] = 0
            if clamp is not None:
                T = pin(T, clamp[i])
            else:
                rec.append(T.astype(np.float32))
        err = max(np.abs(a - b).max() for a, b in zip(prev, out)) if prev is not None else 1.0
        prev = out
        if err < 1e-5:
            break
    assert err < 1e-3, ('fire loop not periodic in time', err)
    ds = lambda o: o.reshape(H, S, W, S).mean((1, 3))
    return [ds(o) for o in prev], rec, loop + 1, err


# ---------------------------------------------------------------- render (fb.render_fire, C columns only for coal and embers)
FIX_LOG = []
FLAME_HARD = {}


def flame_fix_c(idx, f):
    """hf.flame_fix, same two rules; logs only what lies in tile C."""
    out = idx.copy()
    for c in hf.comps(out[:27] != 0):
        if len(c) <= 2:
            for p in c:
                out[p] = 0
            if c[0][1] >= C0:
                FIX_LOG.append('f%02d remnant removed, %d px at x %d y %d (tile C)' % (f, len(c), c[0][1] - C0, c[0][0]))
    for c in hf.comps(out[:27] == PB['w']):
        ys, xs = [p[0] for p in c], [p[1] for p in c]
        if max(ys) < 25:
            for p in c:
                out[p] = PB['Y']
            if min(xs) >= C0:
                FIX_LOG.append('f%02d white island -> yellow, %d px at x %d..%d y %d..%d (tile C)'
                               % (f, len(c), min(xs) - C0, max(xs) - C0, min(ys), max(ys)))
    FLAME_HARD[f] = out.copy()
    return out


def render_c(Ts, Tt):
    """Ts: 16 frames of the 192 px field. Tt: 16 frames of the original 128 px field. Returns hard 192 px frames
    (A and B regions are close to, but not, the accepted tiles: only the C columns are used)."""
    xl = np.arange(64) + 0.5
    wl = 1 - nsstep((xl - BACK_L[0]) / (BACK_L[1] - BACK_L[0]))
    wr = nsstep((xl - BACK_R[0]) / (BACK_R[1] - BACK_R[0]))
    frames, clipped = [], 0
    W = WD
    for f in range(NF):
        t = f / NF
        T = fb.blur_y(fb.blur_x(Ts[f], fb.FRONT_BLUR[0][0]), fb.FRONT_BLUR[0][1])
        Tc = fb.blur_y(fb.blur_x(Ts[f], fb.FRONT_BLUR[1][0]), fb.FRONT_BLUR[1][1])
        idx = np.zeros((H, W), np.uint8)
        # back row. A and B: as accepted (the 128 px field, 45 px along, 6 frames later). C: A's back row at its left
        # edge and B's at its right edge (one back flame straddles each seam), C's own field in between.
        back = np.roll(Tt[(f + fb.BACK_LAG) % NF], fb.BACK_SHIFT, axis=1)
        mid = np.roll(Ts[(f + BACK_MID[1]) % NF][:, C0:], BACK_MID[0], axis=1)
        g = wl * back[:, :64] + wr * back[:, 64:] + (1 - wl - wr) * mid
        Tb = fb.blur_y(fb.blur_x(np.concatenate([back, g], axis=1), 1.2), 0.9)
        Tb = np.vstack([np.zeros((fb.BACK_DROP, W)), Tb[:-fb.BACK_DROP]])
        inside = np.ones((H, W), bool)
        for th, ch in fb.BACK_BANDS:
            inside = fb.smooth_mask(Tb > th) & inside
            idx[inside] = PB[ch]
        inside = np.ones((H, W), bool)
        tips = np.zeros((H, W), bool)
        for th, ch, k in fb.FRONT_BANDS:
            m, tp = fb.tip_mask((Tc if k else T) > th)
            inside = m & inside
            tips |= tp & inside
            idx[inside] = PB[ch]
        idx = np.where(tips, idx, fb.despeckle(idx))
        idx = flame_fix_c(idx, f)
        heat = fb.fire_source(fb.XS, t, fb.spot_state(t))
        for y in range(25, H):
            for x in range(C0, W):
                best, bl = 9.0, None
                for (cx, cy, rx, ry) in fb.LUMPS:
                    q = (fb.wrapd(x + 0.5, cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2
                    if q < best:
                        best, bl = q, (cx, cy, rx, ry)
                hx = heat[x]
                if best < 1.0:
                    cx, cy, rx, ry = bl
                    up = (y + 0.5 - cy) / ry
                    lf = fb.wrapd(x + 0.5, cx) / rx
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
        for (spot, t0, life, vx) in SPARKS_C:
            age = (t - t0) % 1.0
            if age < life:
                x, y = fb.spark_pos(spot, t0, age)
                a = age / life
                if y < 24:
                    if C0 <= x < W:         # an ember of C is only drawn inside C (the neighbours are baked)
                        fb.put(idx, x, y, PB[next(c for lim, c in fb.EMBER if a < lim)], only=soft)
                    elif y >= 0:
                        clipped += 1
        frames.append(idx)
    return frames, clipped


# ---------------------------------------------------------------- measures
def gaps(frs):
    ms = [fb.mask_metrics(fb.hot_mask(a)) for a in frs]
    return [m[0] - m[1] for m in ms], [m[0] for m in ms], ms


def sil_h(fr):
    m = fb.nospark(fr[:25] != 0)
    return np.where(m.any(0), 25 - m.argmax(0), 0)


def gapline(tag, frs):
    g, tall, _ = gaps(frs)
    return ('gap between the two tallest tongues, %-34s min %d  per frame %s  | tallest %s'
            % (tag + ':', min(g), ' '.join(map(str, g)), ' '.join(map(str, tall)))), min(g)


def sheets(sc, path, k=3):
    for part in range(2):
        sh = Image.new('RGB', (320 * k + 24, 8 * (48 * k + 22) + 12), (24, 24, 28))
        d = ImageDraw.Draw(sh)
        for i in range(8):
            f = part * 8 + i
            y = 12 + i * (48 * k + 22)
            d.text((12, y), 'frame %d' % f, fill=(200, 200, 205))
            sh.paste(dv.up(sc[f], (0, 176, 320, 224), k), (12, y + 12))
        sh.save(path % part)


def main():
    spec = overrides()
    cache = sys.argv[sys.argv.index('--cache') + 1] if '--cache' in sys.argv else None
    scratch = sys.argv[sys.argv.index('--scratch') + 1] if '--scratch' in sys.argv else None
    rep = []
    ab = hf.unstrip(SHEET, PB)                                  # the accepted A B frames, 32 x 128 each

    # ---- 1 the original 128 px simulation, re-run with every sub-step recorded
    fr_p, rec_p = (os.path.join(cache, n) for n in ('true_frames.npy', 'true_rec.npy')) if cache else (None, None)
    if cache and os.path.exists(fr_p) and os.path.exists(rec_p):
        Tt, rec = list(np.load(fr_p)), np.load(rec_p)
        note = 'cached'
    else:
        fb.set_domain(128)
        Tt, rec, loops, err = sim()
        rec = np.array(rec)
        note = '%d loops, residual %.1e' % (loops, err)
        if cache:
            os.makedirs(cache, exist_ok=True)
            np.save(fr_p, np.array(Tt))
            np.save(rec_p, rec)
    # proof that the re-run IS the accepted fire: render it through the accepted pipeline, compare with the sheet
    fb.sim_fire = lambda: Tt
    fb.FLAME_FIX = hf.flame_fix
    hard_ab, _ = fb.render_fire()
    fd_ab = []
    for f in range(NF):
        d = hf.FLAME_HARD[f].copy()
        d[:hf.FLAME_ROWS] = dv.dither3(hf.FLAME_HARD[f][:hf.FLAME_ROWS], PB, hf.FIRE_MATS)
        fd_ab.append(np.where(hard_ab[f] == hf.FLAME_HARD[f], d, hard_ab[f]))
    same = all((a == b).all() for a, b in zip(fd_ab, ab))
    assert same, 'the re-run of the 128 px simulation does not reproduce the accepted sheet'
    rep.append('A B    re-run of the original simulation (%s) rendered through the accepted pipeline: pixel-identical to hazards-final frames_fire_1x.png' % note)

    # ---- 2 tile C: the 192 px domain, A and B pinned to the original run
    fb.set_domain(WD)
    fb.SPOTS = list(fb.SPOTS) + SPOTS_C
    fb.LUMPS = list(fb.LUMPS) + LUMPS_C
    fb.SPARKS_VX = {(s, t0): vx for (s, t0, life, vx) in SPARKS_C}
    fb.spot_state, fb.fire_source, fb.fire_vel = spot_state_c, fire_source_c, fire_vel_c
    Ts, _, loops, err = sim(clamp=rec)
    rep.append('C      simulation on 192 px, A and B pinned: %d loops, loop residual %.1e (frame 15 -> frame 0 is the same time step as any other)' % (loops, err))
    hard, clipped = render_c(Ts, Tt)
    fd = []
    for f in range(NF):
        d = FLAME_HARD[f].copy()
        d[:hf.FLAME_ROWS] = dv.dither3(FLAME_HARD[f][:hf.FLAME_ROWS], PB, hf.FIRE_MATS)
        assert ((d == PB['w']) == (FLAME_HARD[f] == PB['w'])).all()           # white core untouched
        fd.append(np.where(hard[f] == FLAME_HARD[f], d, hard[f]))
    hc = [a[:, C0:] for a in hard]
    c = [a[:, C0:] for a in fd]
    abc = [np.concatenate([a, b], axis=1) for a, b in zip(ab, c)]             # A B from the SHEET, C new
    aba = [np.concatenate([a, a[:, :64]], axis=1) for a in ab]

    # ---- 3 checks and numbers
    out_sheet = hf.strip(PB, abc)
    chk = hf.unstrip(SHEET, PB)
    assert all((x[:, :128] == y).all() for x, y in zip(abc, chk))
    sa = np.array(out_sheet)
    assert (sa[:2 * H] == np.array(Image.open(SHEET).convert('RGBA'))).all()
    rep.append('A B    rows 0 and 1 of frames_fire_abc_1x.png are pixel-identical to hazards-final frames_fire_1x.png (asserted)')
    used_ab = set(np.unique(np.array(ab)).tolist()) - {0}
    used_c = set(np.unique(np.array(c)).tolist()) - {0}
    assert used_c <= used_ab, used_c - used_ab
    rep.append('palette  A B uses %d colours, C uses %d, A B C uses %d; C adds no colour (asserted)' % (len(used_ab), len(used_c), len(used_ab | used_c)))
    rgb = lambda fr: PB.lut[fr][..., :3].astype(float)
    n, med, p10 = dv.pair_stats([(rgb(a), rgb(b)) for a, b in zip(hc, c)])
    opaque = int(sum((a != 0).sum() for a in hc))
    assert all(((a == 0) == (b == 0)).all() for a, b in zip(hc, c))
    rep.append('C      dither px %d (%.1f%% of opaque)  pair step median %.1f  p10 %.1f   (rule: at least %.0f; A B: 4208 px, 13.4%%, 33.4, 31.5)'
               % (n, 100.0 * n / opaque, med, p10, hf.MIN_STEP))
    ok_d = p10 >= hf.MIN_STEP
    rep.append('tiles  C raw %d unique %d | A B raw 256 unique %d | A B C raw 384 unique %d'
               % (NF * 8, fb.tile_count(c), fb.tile_count(ab), fb.tile_count(abc)))
    l0, g0 = gapline('A B, 128 px wrapped (reference)', ab)
    l1, g1 = gapline('A B C, 192 px wrapped', abc)
    l2, g2 = gapline('C alone, 64 px wrapped', c)
    l3, g3 = gapline('A B C, hard shapes of C', [np.concatenate([a, b], axis=1) for a, b in zip(ab, hc)])
    rep.extend(['fire   ' + l for l in (l0, l1, l3, l2)])
    assert g0 == 2
    _, _, ms = gaps(abc)
    rep.append('fire   A B C: tile that holds the tallest tongue, per frame: ' + ' '.join('ABC'[m[4][0][1] // 64] for m in ms)
               + ' | second: ' + ' '.join('ABC'[m[4][1][1] // 64] for m in ms))
    ctall = [max([p[0] for p in m[4] if p[1] >= C0] or [0]) for m in ms]
    rep.append('fire   tallest hot tongue inside C, per frame: ' + ' '.join(map(str, ctall)))
    # seams: jump of the silhouette height between the two columns at a seam (embers dropped)
    hs = [sil_h(a) for a in abc]
    h2 = [sil_h(a) for a in ab]
    j = lambda hh, a, b: ' '.join('%d' % abs(int(x[a]) - int(x[b])) for x in hh)
    rep.append('seam   silhouette jump per frame  A|B (accepted): ' + j(hs, 63, 64))
    rep.append('seam   silhouette jump per frame  B|A (accepted, A B row): ' + j(h2, 127, 0))
    rep.append('seam   silhouette jump per frame  B|C (new): ' + j(hs, 127, 128))
    rep.append('seam   silhouette jump per frame  C|A (new): ' + j(hs, 191, 0))
    inner = np.concatenate([np.abs(np.diff(x.astype(int))) for x in hs])
    rep.append('seam   for scale, jump between any two neighbouring columns of the A B C row: median %d  p90 %d  p99 %d  max %d'
               % (np.median(inner), np.percentile(inner, 90), np.percentile(inner, 99), inner.max()))
    # loop: changed pixels per step, per tile
    for nm, sl in (('A', slice(0, 64)), ('B', slice(64, 128)), ('C', slice(128, 192))):
        ch = [int((abc[f][:, sl] != abc[(f + 1) % NF][:, sl]).sum()) for f in range(NF)]
        rep.append('loop   %s changed px per step (last = frame 15 -> 0): %s | mean %.0f, 15->0 %d' % (nm, ' '.join(map(str, ch)), np.mean(ch), ch[-1]))
    # likeness: best pixel agreement of C's flame rows with A or B over every x shift and frame shift
    best = (0, None)
    cz = np.array(c)[:, :25]
    for nm, sl in (('A', slice(0, 64)), ('B', slice(64, 128))):
        o = np.array(ab)[:, :25, sl]
        for p in range(NF):
            op = np.roll(o, p, axis=0)
            for s in range(64):
                q = float((np.roll(op, s, axis=2) == cz).mean())
                if q > best[0]:
                    best = (q, (nm, s, p))
    ownab = max(float((np.roll(np.array(ab)[:, :25, 64:], s, axis=2) == np.array(ab)[:, :25, :64]).mean()) for s in range(64))
    rep.append('like   best pixel agreement of C (flame rows) with A or B over all 64 x shifts and 16 frame shifts: %.1f%% (tile %s, shift %d, frames %d); A against B, same frame, best shift: %.1f%%'
               % (100 * best[0], *best[1], 100 * ownab))
    for nm, a, b in (('left 8 px of C against left 8 px of A', slice(128, 136), slice(0, 8)), ('right 8 px of C against right 8 px of B', slice(184, 192), slice(120, 128))):
        rep.append('like   %s, same frame: %.1f%% equal pixels' % (nm, 100 * float((np.array(abc)[:, :25, a] == np.array(abc)[:, :25, b]).mean())))
    rep.append('embers C has %d (A B: 20); ember-frames not drawn because the ember left tile C: %d' % (len(SPARKS_C), clipped))
    rep.extend('fire   fix in C: ' + s for s in FIX_LOG)
    rep.append('C      sources (local x, width, puffs, phase, strength, pulse): ' + ' '.join('(%d, %.1f, %d, %.2f, %.2f, %.2f)' % (s[0] - C0, *s[1:]) for s in SPOTS_C))
    rep.append('C      minor leaders (source, on, off, strength, width, pulse): ' + ' '.join(str(e) for e in LEAD_C))
    if spec:
        rep.append('overrides: ' + spec)
    verdict = 'PASS' if g1 >= 2 and ok_d else 'FAIL'
    rep.append('RULES  gap >= 2 on A B C: %s (min %d) | dither p10 >= 28: %s | palette: PASS | A B identical: PASS  => %s'
               % ('PASS' if g1 >= 2 else 'FAIL', g1, 'PASS' if ok_d else 'FAIL', verdict))

    # ---- 4 pictures
    out_sheet.save(os.path.join(HERE, 'frames_fire_abc_1x.png'))
    base = v4.base_scene()
    masks = v4.light_masks(base)
    dv.set_level(hf.LAVA_LEVEL)
    sc = {}
    for nm, frs in (('abc', abc), ('ab', ab)):
        lev = v4.light_levels('B', PB, frs)
        sc[nm] = [s6.scene(base, 'B', PB, frs, {}, f, masks, lev, 'H') for f in range(NF)]
        v4.save_gif(os.path.join(HERE, 'anim_%s_3x.gif' % nm), [dv.up(s, VIEW, 3) for s in sc[nm]], GIF_MS)
    dv.up(sc['abc'][STILL], VIEW, 3).save(os.path.join(HERE, 'strip_abc_3x.png'))
    lab = Image.new('RGB', (64 * 3 * 4 + 24, 3 * (32 * 4 + 20) + 8), (16, 16, 20))
    d = ImageDraw.Draw(lab)
    for r, nm in enumerate('ABC'):
        d.text((12, 6 + r * 148), 'tile %s, frames 0 4 8 12, 4x' % nm, fill=(200, 200, 205))
        for i, f in enumerate((0, 4, 8, 12)):
            ti = PB.img(abc[f][:, r * 64:(r + 1) * 64]).resize((256, 128), Image.NEAREST)
            bg = Image.new('RGBA', ti.size, (10, 12, 34, 255))
            bg.alpha_composite(ti)
            lab.paste(bg.convert('RGB'), (12 + i * 192 if False else 12 + i * 258 - i * 66, 18 + r * 148))
    lab.save(os.path.join(HERE, 'tiles_abc_4x.png'))
    if scratch:
        os.makedirs(scratch, exist_ok=True)
        sheets(sc['abc'], os.path.join(scratch, 'sheet_abc_%d.png'))
    with open(os.path.join(HERE, 'numbers.txt'), 'w') as fh:
        fh.write('\n'.join(rep) + '\n')
    print('\n'.join(rep))


if __name__ == '__main__':
    main()
