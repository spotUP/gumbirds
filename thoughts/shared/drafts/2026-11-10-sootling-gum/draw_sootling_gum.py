#!/opt/homebrew/bin/python3.14 -I
"""Sootling redraw with bubble gum bubbles: drafts for Bubblegum Brawl. Original art, drawn by this script.

Run: /opt/homebrew/bin/python3.14 -I draw_sootling_gum.py [--nogif] [--rebg]
  --rebg   re-render the three clean backdrops from ../2026-11-10-backgrounds-final (about 20 s); otherwise the cached
           bg_<mood>_1x.png in this directory are used (rendered on the first run).
Writes sheets, GIFs, scenes, numbers.txt and index.html next to this file. Nothing outside this directory is written.

Frame box: 16 x 32, feet on row 31, hit box columns 6..9 (same as assets/flier/sootling_sheet.json).
One palette of 15 colours + transparent per flier (soot, ember, gum together), player and computer share the tiles.
"""
import os
import sys
import math
import importlib.util
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
BGDIR = os.path.join(HERE, '..', '2026-11-10-backgrounds-final')
W, H = 16, 32
MAG = (255, 0, 255)
MOUTH = (12.0, 21.0)          # where the gum leaves the lips
LX, LY = 0.6, -0.8            # key light from the upper right


def snap5(v):
    f = round(v * 31 / 255)
    return (f << 3) | (f >> 2)


def hexc(s):
    return tuple(snap5(int(s[i:i + 2], 16)) for i in (1, 3, 5))


def lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


# keys: o outline; 1..4 soot fur dark to light; r rim light; e f g ember wing and goggle lens; A gum outline,
# B C D E gum ramp dark to pale; w hard white gloss
PAL_P = {k: hexc(v) for k, v in dict(
    o='#0a0718', **{'1': '#20204a', '2': '#30487e', '3': '#5894b8', '4': '#a0dcd8'}, r='#e8fff0',
    e='#7c1c40', f='#e45c28', g='#ffc458',
    A='#5a0c4c', B='#b02c84', C='#f05ca4', D='#ffa0c0', E='#ffd8e0', w='#ffffff').items()}
PAL_C = {k: hexc(v) for k, v in dict(
    o='#100818', **{'1': '#3a1830', '2': '#742c38', '3': '#b45a3c', '4': '#e8a060'}, r='#fff0b4',
    e='#103c64', f='#1c94b4', g='#7cf0dc',
    A='#083c38', B='#168c50', C='#54d050', D='#b0f478', E='#e8ffc4', w='#ffffff').items()}
PALS = {'player': PAL_P, 'cpu': PAL_C}
DITHER_PAIRS = [('1', '2'), ('2', '3'), ('B', 'C')]     # pairs that the art really alternates in a checker

# ---------------------------------------------------------------- Sootling body (hand placed), rows 20..31
BODY = [
    ".....o.o........",
    "....o3o4oo......",
    "...o2334444oo...",
    "..o1233oooo4ro..",
    "..o1232oggwo4ro.",
    "..o1213offgo34o.",
    "..o11212oooo33o.",
    "..o1112123332o..",
    "...o11212222o...",
    "....oooooooo....",
    "....o2o..o3o....",
    "....ooo..ooo....",
]
LENS = {'open': ["oggwo", "offgo"], 'squint': ["offfo", "ooooo"], 'wide': ["ogwwo", "oggwo"], 'shut': ["o444o", "ooooo"]}
FEET_TUCK = ["....oooooooo....", ".....oo..oo.....", "................"]
WINGS = {
    'up': (["o.....", "oo....", "ogo...", "ogfo..", "ogffo.", ".offeo", ".oeeeo", "..oooo"], 0, 17),
    'upmid': (["oo....", "ogoo..", "ogffo.", ".offeo", ".oeeo.", "..oo.."], 0, 20),
    'mid': (["ooo...", "ogffo.", ".ofeeo", "..ooo."], 0, 23),
    'dnmid': (["..ooo.", ".offeo", "ogffo.", "ogeo..", "oo...."], 0, 24),
    'down': (["...ooo", "..ofeo", ".offo.", "ogfo..", "ogo...", "oo....", "o....."], 0, 25),
}
SPLAT = [   # gum stuck on the face: list of (x, y, key) per stage, 0 = fresh and big
    [(9, 22, 'C'), (10, 22, 'D'), (11, 22, 'C'), (8, 23, 'C'), (9, 23, 'D'), (10, 23, 'E'), (11, 23, 'D'), (12, 23, 'C'),
     (13, 23, 'B'), (8, 24, 'B'), (9, 24, 'C'), (10, 24, 'w'), (11, 24, 'D'), (12, 24, 'C'), (13, 24, 'B'), (9, 25, 'B'),
     (10, 25, 'C'), (11, 25, 'C'), (12, 25, 'B'), (11, 26, 'C'), (13, 25, 'C'), (13, 26, 'B')],
    [(9, 23, 'C'), (10, 23, 'D'), (11, 23, 'D'), (12, 23, 'C'), (9, 24, 'C'), (10, 24, 'E'), (11, 24, 'C'), (12, 24, 'B'),
     (10, 25, 'C'), (11, 25, 'B'), (11, 26, 'C'), (11, 27, 'C'), (13, 24, 'C'), (13, 25, 'C'), (13, 26, 'C'), (13, 27, 'B')],
    [(10, 23, 'C'), (11, 23, 'D'), (12, 23, 'C'), (11, 24, 'C'), (12, 24, 'B'), (11, 27, 'C'), (11, 28, 'B'), (13, 27, 'C')],
    [(12, 22, 'C'), (12, 23, 'D'), (13, 23, 'C')],
]


def grid():
    return [['.'] * W for _ in range(H)]


def blit(g, rows, ox, oy):
    for j, r in enumerate(rows):
        for i, c in enumerate(r):
            if c != '.' and 0 <= oy + j < H and 0 <= ox + i < W:
                g[oy + j][ox + i] = c


def draw_body(g, wing='mid', lens='open', dy=0, tuck=False, splat=None, puff=False):
    blk, wx, wy = WINGS[wing]
    blit(g, blk, wx, wy + dy)
    rows = list(BODY)
    a, b = LENS[lens]
    rows[4] = rows[4][:7] + a + rows[4][12:]
    rows[5] = rows[5][:7] + b + rows[5][12:]
    if tuck:
        rows[9:12] = FEET_TUCK
    if puff:                                   # cheek pushed out while blowing
        rows[3] = "..o1233oooo44ro."
        rows[4] = rows[4][:12] + "44ro"
        rows[5] = rows[5][:12] + "34o."
    blit(g, rows, 0, 20 + dy)
    if splat is not None:
        for x, y, k in SPLAT[splat]:
            if g[y + dy][x] != '.' or k in 'BC':
                g[y + dy][x] = k


# ---------------------------------------------------------------- gum membrane
def field(blobs, x, y):
    ds = [math.hypot((x - cx) / rx, (y - cy) / ry) for cx, cy, rx, ry in blobs]
    if len(ds) == 1:
        return ds[0], 0, ds
    k = 7.0
    return -math.log(sum(math.exp(-k * d) for d in ds)) / k, min(range(len(ds)), key=lambda i: ds[i]), ds


def rag(ang, seed):
    return 0.55 * math.sin(3 * ang + seed) + 0.35 * math.sin(7 * ang + 2.1 * seed) + 0.25 * math.sin(11 * ang + 0.7 * seed)


def draw_gum(g, blobs, tear=None, mesh=True, crease=True):
    """blobs: list of (cx, cy, rx, ry) fused into one membrane. tear = (index, px, py, reach, seed): the membrane of blob
    `index` is gone within `reach` px of the puncture point; the retracting rim is thick and pale."""
    blobs = [b for b in blobs if b[2] > 0.45 and b[3] > 0.45]
    if not blobs:
        return
    mask = {}
    for y in range(H):
        for x in range(W):
            f, near, ds = field(blobs, x + .5, y + .5)
            if f > 1.0:
                continue
            rimd = None
            if tear and near == tear[0] and len(blobs) > tear[0]:
                _, px, py, reach, seed = tear
                dd = math.hypot(x + .5 - px, y + .5 - py)
                lim = reach + rag(math.atan2(y + .5 - py, x + .5 - px), seed)
                if dd < lim:
                    continue
                rimd = dd - lim
            mask[(x, y)] = (f, near, ds, rimd)
    for (x, y), (f, near, ds, rimd) in mask.items():
        cx, cy, rx, ry = blobs[near]
        nx, ny = (x + .5 - cx) / rx, (y + .5 - cy) / ry
        t = 0.75 * (nx * LX + ny * LY) + 0.45 * math.sqrt(max(0.0, 1 - ds[near] ** 2))   # sphere shading
        edge = any((x + dx, y + dy) not in mask for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        big = rx >= 3.2
        if rimd is not None and rimd < 1.3:
            k = 'w' if rimd < 0.6 and (x + y) % 2 == 0 else 'E'
        elif edge:
            k = 'A'
        elif t > 0.78:
            k = 'E'
        elif t > 0.50:
            k = 'D'
        elif t > -0.15:
            k = 'C'
        else:
            k = 'B'
        if not edge and rimd is None or (rimd is not None and rimd >= 1.3 and not edge):
            if -0.27 < t < -0.08 and (x + y) % 2 == 0:
                k = 'C' if k == 'B' else 'B'                       # dithered shadow edge
            if crease and len(ds) > 1:
                s2 = sorted(ds)
                if s2[1] - s2[0] < 0.16 and s2[0] > 0.45 and blobs[near][2] >= 2.5:
                    k = 'B' if (x + y) % 2 else 'C'                # crease where two lobes meet
            if mesh and big and math.hypot(nx + 0.22, ny - 0.20) < 0.36 and (x + y) % 2 == 0:
                continue                                           # checker mesh: the backdrop shows through
        g[y][x] = k
    for cx, cy, rx, ry in blobs:                                   # hard gloss and bounce light, kept clean
        if rx < 2.0:
            continue
        hx, hy = int(cx + 0.44 * rx), int(cy - 0.50 * ry)
        pts = [(hx, hy)] + ([(hx - 1, hy)] if rx >= 3.2 else []) + ([(hx + 1, hy + 1)] if rx >= 4.0 else [])
        for x, y in pts:
            if (x, y) in mask and mask[(x, y)][3] is None and g[y][x] not in ('A', '.'):
                g[y][x] = 'w'
        if rx >= 3.6:
            x, y = int(cx - 0.50 * rx), int(cy + 0.52 * ry)
            if (x, y) in mask and g[y][x] in ('B', 'C'):
                g[y][x] = 'D'


def curve(a, c, b, n=24):
    pts = []
    for i in range(n + 1):
        t = i / n
        x = (1 - t) ** 2 * a[0] + 2 * t * (1 - t) * c[0] + t * t * b[0]
        y = (1 - t) ** 2 * a[1] + 2 * t * (1 - t) * c[1] + t * t * b[1]
        p = (int(x), int(y))
        if not pts or pts[-1] != p:
            pts.append(p)
    return pts


def strand(g, a, b, sag=1.2, keys='CD', over=False):
    c = ((a[0] + b[0]) / 2 + sag, (a[1] + b[1]) / 2 + sag)
    for i, (x, y) in enumerate(curve(a, c, b)):
        if 0 <= x < W and 0 <= y < H and (over or g[y][x] == '.'):
            g[y][x] = keys[0] if i % 3 else keys[1]


# ---------------------------------------------------------------- the three bubble designs
# layout(s0, s1) -> two blobs. Bubble 0 is the one that survives the first pop, bubble 1 is blown second and pops first.
def lerp(a, b, t):
    return a + (b - a) * t


def grow(rest, s):
    """a bubble of inflation s (0..1.2) on its way from the lips to its rest place"""
    cx, cy, rx, ry = rest
    t = min(1.0, s) ** 0.8
    return (lerp(MOUTH[0] - 0.5, cx, t), lerp(MOUTH[1] - 1.0 - ry * s * 0.9, cy, t), rx * s, ry * s)


def mixb(a, b, t):
    return tuple(lerp(u, v, t) for u, v in zip(a, b))


VARIANTS = {
    'A': dict(name='Twin bubbles on gum strands', fused=False,
              one=(8.0, 9.6, 5.2, 5.5), two=((4.6, 9.4, 4.3, 4.8), (11.4, 9.0, 4.3, 4.8)),
              idea='Two separate bubbles side by side above the head, each on a chewed gum strand that runs to the lips. '
                   'Closest to the old balloon silhouette. One pops: the other swings to the middle.'),
    'B': dict(name='Double-lobed bubble from the mouth', fused=True,
              one=(8.3, 12.6, 5.7, 5.9), two=((5.0, 12.4, 4.9, 5.5), (11.0, 12.0, 4.9, 5.5)),
              idea='One membrane with two lobes and a crease, blown straight from the lips on a short neck. One lobe '
                   'pops: the rest pulls round into a single bubble.'),
    'C': dict(name='Stacked bubble (big one with a small one on top)', fused=True,
              one=(8.2, 12.8, 6.1, 5.8), two=((8.2, 13.6, 6.2, 5.4), (8.8, 5.2, 3.8, 3.6)),
              idea='A big bubble from the lips with a second, smaller bubble budded on top. The top one pops first. '
                   'Tallest shape; count reads by height, not by width.'),
}
NECK = (11.6, 19.6, 1.5, 1.9)


def layout(v, s0, s1):
    V = VARIANTS[v]
    t = max(0.0, min(1.0, s1))
    r0 = mixb(V['one'], V['two'][0], t)
    b0 = grow(r0, s0)
    b1 = grow(V['two'][1], s1) if s1 > 0 else None
    return b0, b1


def wob(b, q=0.0, dx=0.0, dy=0.0):
    """area preserving squash: ry * (1 + q), rx / (1 + q)"""
    cx, cy, rx, ry = b
    return (cx + dx, cy + dy, rx / (1 + q), ry * (1 + q))


def draw_bubbles(g, v, b0, b1, tear=None):
    V = VARIANTS[v]
    if V['fused']:
        blobs = [b for b in (b0, b1) if b]
        ti = None
        if tear:
            ti = (len(blobs) - 1,) + tear
        low = max(blobs, key=lambda b: b[1] + b[3])
        if low[2] > 2.2:                           # neck from the lips into the membrane
            blobs.append(NECK)
        draw_gum(g, blobs, tear=ti)
    else:
        if b0:
            draw_gum(g, [b0], tear=None if b1 else ((0,) + tear if tear else None))
        if b1:
            draw_gum(g, [b1], tear=(0,) + tear if tear else None)
        for b in (b0, b1):
            if b and b[2] > 1.6:
                strand(g, (b[0], b[1] + b[3]), MOUTH, sag=0.8 if b[0] < 10 else -0.8)


# ---------------------------------------------------------------- motion: damped springs driven by the flap
FLAP_WING = ['upmid', 'up', 'up', 'mid', 'down', 'down', 'dnmid', 'mid']
FLAP_DY = [0, 0, 0, 0, -1, -1, -1, 0]
FLAP_ACC = [0.0, 0.0, -0.25, 0.9, 1.0, 0.1, -0.55, -0.3]     # body acceleration seen by the bubble (up = positive)


def spring_loop(k, c, gain, loops=6, sub=4, phase=0):
    """steady state of x'' = -k x - c x' + gain * a(t) over the 8-frame flap; returns 8 samples"""
    x = vx = 0.0
    out = []
    for lp in range(loops):
        out = []
        for f in range(8):
            a = FLAP_ACC[(f + phase) % 8]
            for _ in range(sub):
                ax = -k * x - c * vx + gain * a
                vx += ax / sub
                x += vx / sub
            out.append(x)
    return out


def ring(k, c, x0, v0, n, sub=4):
    """free ringing after a shock"""
    x, vx, out = x0, v0, []
    for f in range(n):
        out.append(x)
        for _ in range(sub):
            vx += (-k * x - c * vx) / sub
            x += vx / sub
    return out


def frame_new():
    return grid()


def anim_flap(v, n):
    q0 = spring_loop(0.95, 0.30, -0.115)
    y0 = spring_loop(0.60, 0.35, 0.55)
    q1 = spring_loop(1.25, 0.28, -0.105, phase=7)
    y1 = spring_loop(0.75, 0.35, 0.50, phase=7)
    sx = spring_loop(0.80, 0.30, 0.42)
    frs = []
    for f in range(8):
        g = frame_new()
        if n == 2:
            b0, b1 = layout(v, 1, 1)
            if v == 'C':
                b0 = wob(b0, q0[f], 0, y0[f])
                b1 = wob(b1, q1[f] * 1.3, sx[f] * 0.9, y0[f] * 1.6 + y1[f] * 0.5)
            else:
                b0 = wob(b0, q0[f], -sx[f], y0[f])
                b1 = wob(b1, q1[f], sx[f], y1[f])
        else:
            b0, b1 = layout(v, 1, 0)
            b0 = wob(b0, q0[f] * 1.2, sx[f] * 0.6, y0[f])
        draw_bubbles(g, v, b0, b1)
        draw_body(g, FLAP_WING[f], 'open', FLAP_DY[f], tuck=FLAP_DY[f] < 0)
        frs.append(g)
    return frs


def particles(g, origin, f, seed, n=6):
    for i in range(n):
        a = seed * 1.7 + i * 2.39996
        sp = 1.5 + 0.9 * ((i * 37 + seed * 11) % 7) / 6
        vx, vy = sp * math.cos(a), sp * math.sin(a) - 0.6
        t = f
        x = origin[0] + vx * t * (1 - 0.07 * t)
        y = origin[1] + vy * t + 0.22 * t * t
        if f > 2 + i % 3:
            continue
        xi, yi = int(x), int(y)
        if 0 <= xi < W and 0 <= yi < H and g[yi][xi] == '.':
            g[yi][xi] = 'D' if i % 2 else 'C'
            if f <= 1 and 0 <= xi + 1 < W and g[yi][xi + 1] == '.':
                g[yi][xi + 1] = 'C'


def anim_pop(v, n):
    """12 frames. n = bubbles before the pop. Tear front runs from the puncture to the neck (membrane retracts into a
    thick rim), droplets fly on ballistic paths, strands spring back to the lips, the glob lands on the face."""
    N = 12
    V = VARIANTS[v]
    if n == 2:
        full0, full1 = layout(v, 1, 1)
        pb = full1
    else:
        full0, _ = layout(v, 1, 0)
        pb = full0
    pun = (pb[0] + 0.55 * pb[2], pb[1] - 0.75 * pb[3])                       # puncture on the upper right
    diam = 2 * max(pb[2], pb[3])
    reach = [None, 0.30, 0.62, 0.92, 1.25]
    qk = ring(1.1, 0.26, 0.0, -0.20, N)                                      # survivor shock
    sk = ring(0.7, 0.30, 0.0, 0.9, N)
    lens = ['wide', 'squint', 'squint', 'squint', 'shut', 'shut', 'shut', 'shut', 'squint', 'squint', 'open', 'open']
    wing = ['mid', 'up', 'up', 'upmid', 'mid', 'dnmid', 'down', 'dnmid', 'mid', 'upmid', 'mid', 'mid']
    splat = [None, None, None, None, None, 0, 0, 1, 1, 2, 3, None]
    ends = [(pb[0] - 0.9 * pb[2], pb[1] + 0.2 * pb[3]), (pb[0] + 0.1 * pb[2], pb[1] - 0.5 * pb[3]),
            (pb[0] + 0.9 * pb[2], pb[1] + 0.5 * pb[3])]
    frs = []
    for f in range(N):
        g = frame_new()
        merge = min(1.0, max(0.0, (f - 1) / 6.0))
        merge = merge * merge * (3 - 2 * merge)
        tear = None
        if n == 2:
            b0 = layout(v, 1, 1 - merge)[0]
            b0 = wob(b0, qk[f], sk[f] * (-0.6 if v != 'C' else 0.3), abs(qk[f]) * 2 if f else 0)
            b1 = None
            if f == 0:
                b1 = wob(full1, 0.0)
                b1 = (b1[0], b1[1], b1[2] * 1.10, b1[3] * 1.10)
            elif f < len(reach):
                sh = 1 - 0.10 * f
                b1 = (lerp(full1[0], NECK[0], 0.12 * f), lerp(full1[1], NECK[1] - 3, 0.12 * f), full1[2] * sh, full1[3] * sh)
                tear = (pun[0], pun[1], reach[f] * diam, 1.3 + f)
            if b1 is None and V['fused']:
                draw_bubbles(g, v, b0, None)
            elif V['fused']:
                draw_bubbles(g, v, b0, b1, tear)
            else:
                draw_gum(g, [b0])
                strand(g, (b0[0], b0[1] + b0[3]), MOUTH, sag=0.8 if b0[0] < 10 else -0.8)
                if b1:
                    draw_gum(g, [b1], tear=(0,) + tear if tear else None)
                    if f < 3:
                        strand(g, (b1[0], b1[1] + b1[3]), MOUTH, sag=-0.8)
        else:
            if f == 0:
                b = (full0[0], full0[1], full0[2] * 1.10, full0[3] * 1.10)
                draw_bubbles(g, v, b, None)
            elif f < len(reach):
                sh = 1 - 0.10 * f
                b = (lerp(full0[0], NECK[0], 0.12 * f), lerp(full0[1], NECK[1] - 3, 0.12 * f), full0[2] * sh, full0[3] * sh)
                draw_bubbles(g, v, b, None, (pun[0], pun[1], reach[f] * diam, 1.3 + f))
        if f == 0:
            x, y = int(pun[0]), int(pun[1])
            for dx, dy in ((0, 0), (1, -1), (-1, 1), (1, 0), (0, -1)):
                if 0 <= x + dx < W and 0 <= y + dy < H:
                    g[y + dy][x + dx] = 'w'
        if 1 <= f <= 4:
            particles(g, pun, f - 1, 3 + n)
        if 3 <= f <= 6:                                                      # strands snap back to the lips
            t = (f - 3) / 3.0
            L = math.exp(-2.2 * t) * math.cos(4.2 * t)
            for i, e in enumerate(ends):
                p = (MOUTH[0] + (e[0] - MOUTH[0]) * L, MOUTH[1] + (e[1] - MOUTH[1]) * L + 2.5 * t * t)
                strand(g, p, MOUTH, sag=(1.5 - i) * (1 + 2 * t), keys='DC')
                xi, yi = int(p[0]), int(p[1])
                if 0 <= xi < W and 0 <= yi < H:
                    g[yi][xi] = 'E'
        dy = 0
        if n == 1 and f >= 6:
            dy = 0
        draw_body(g, wing[f] if n == 2 else (wing[f] if f < 6 else ('up', 'upmid')[f % 2]), lens[f], dy, splat=splat[f])
        frs.append(g)
    return frs


def anim_inflate(v):
    """16 frames, respawn: three breaths per bubble, radius overshoots and rings, the first bubble makes room."""
    N = 16
    s0 = [0.14, 0.30, 0.46, 0.43, 0.66, 0.90, 1.10, 0.97, 1.02, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
    s1 = [0, 0, 0, 0, 0, 0, 0, 0.14, 0.30, 0.48, 0.45, 0.70, 0.94, 1.10, 0.96, 1.0]
    puff = [1, 1, 0, 0, 1, 1, 0, 1, 1, 0, 0, 1, 1, 0, 0, 0]
    q0 = [0.0] * 6 + ring(1.0, 0.30, 0.16, 0.0, N - 6)
    q1 = [0.0] * 13 + ring(1.2, 0.30, 0.16, 0.0, N - 13)
    frs = []
    for f in range(N):
        g = frame_new()
        b0, b1 = layout(v, s0[f], s1[f])
        b0 = wob(b0, q0[f])
        if b1:
            b1 = wob(b1, q1[f])
        draw_bubbles(g, v, b0, b1)
        draw_body(g, ('mid', 'upmid')[(f // 2) % 2], 'squint' if puff[f] else 'open', 0, puff=bool(puff[f]))
        frs.append(g)
    return frs


def anim_fall():
    """6 frames, no bubbles: wings streaming up and fluttering, a torn gum strand whips above the lips."""
    frs = []
    for f in range(6):
        g = frame_new()
        pts = []
        for i in range(9):
            a = 0.25 + 0.16 * i
            x = MOUTH[0] - 0.4 * i + a * i * 0.5 * math.sin(i * 0.9 - f * math.tau / 6)
            y = MOUTH[1] - 1 - i * 1.15
            pts.append((int(x), int(y)))
        n = 0
        for p0, p1 in zip(pts, pts[1:]):                 # connected strand, no loose pixels
            for x, y in curve(p0, ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2), p1, 6):
                if 0 <= x < W and 0 <= y < H:
                    g[y][x] = 'C' if n % 3 else 'D'
                    n += 1
        x, y = pts[-1]
        if 0 <= x < W and 1 <= y < H:
            g[y - 1][x] = 'E'
        draw_body(g, ('up', 'upmid', 'up', 'up', 'upmid', 'up')[f], 'wide', 0, tuck=f % 2 == 0)
        frs.append(g)
    return frs


def glide0():
    g = frame_new()
    draw_body(g, 'mid', 'wide', 0)
    g[20][12] = 'C'
    g[19][12] = 'D'
    return g


def build(v):
    A = dict(flap2=anim_flap(v, 2), flap1=anim_flap(v, 1), pop2=anim_pop(v, 2), pop1=anim_pop(v, 1),
             inflate=anim_inflate(v), fall=anim_fall())
    legacy = [A['flap2'][7], A['flap2'][1], A['flap2'][5], A['flap1'][7], A['flap1'][1], glide0(), A['fall'][0]]
    return A, legacy


ORDER = ['flap2', 'flap1', 'pop2', 'pop1', 'inflate', 'fall']
LEGACY_NAMES = ['glide2', 'up2', 'down2', 'glide1', 'up1', 'glide0', 'fall']
GIF_MS = dict(flap2=70, flap1=70, pop2=80, pop1=80, inflate=90, fall=70)


# ---------------------------------------------------------------- output
def render(g, pal, bg=None):
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0) if bg is None else bg + (255,))
    p = im.load()
    for y in range(H):
        for x in range(W):
            if g[y][x] != '.':
                p[x, y] = pal[g[y][x]] + (255,)
    return im


def up(im, k):
    return im.resize((im.width * k, im.height * k), Image.NEAREST)


def sheet_legacy(legacy):
    im = Image.new('RGB', (7 * W, 2 * H), MAG)
    for r, pal in enumerate((PAL_P, PAL_C)):
        for i, g in enumerate(legacy):
            s = render(g, pal)
            im.paste(s, (i * W, r * H), s)
    return im


def sheet_import(legacy):
    """the layout tools/import_flier_sheet.py reads: frames at x = 2 + 20 i, rows at y = 2 and 38"""
    im = Image.new('RGBA', (142, 74), (26, 29, 36, 255))
    d = ImageDraw.Draw(im)
    for r, pal in enumerate((PAL_P, PAL_C)):
        for i, g in enumerate(legacy):
            ox, oy = 2 + 20 * i, 2 + 36 * r
            d.rectangle([ox - 1, oy - 1, ox + W, oy + H], fill=(36, 40, 50, 255))
            im.alpha_composite(render(g, pal), (ox, oy))
    return im


def sheet_ext(A):
    im = Image.new('RGB', (16 * W, 2 * len(ORDER) * H), MAG)
    for r, pal in enumerate((PAL_P, PAL_C)):
        for j, name in enumerate(ORDER):
            for i, g in enumerate(A[name]):
                s = render(g, pal)
                im.paste(s, (i * W, (r * len(ORDER) + j) * H), s)
    return im


def view4(im1x, cols, rows):
    """4x presentation copy on the dark neutral page colour with a slot frame"""
    k = 4
    out = Image.new('RGB', (im1x.width * k + 8, im1x.height * k + 8), (22, 24, 30))
    px = im1x.convert('RGB').load()
    d = ImageDraw.Draw(out)
    for r in range(rows):
        for c in range(cols):
            d.rectangle([4 + c * W * k + 2, 4 + r * H * k + 2, 4 + (c + 1) * W * k - 3, 4 + (r + 1) * H * k - 3], fill=(40, 44, 56))
    for y in range(im1x.height):
        for x in range(im1x.width):
            if px[x, y] != MAG:
                d.rectangle([4 + x * k, 4 + y * k, 4 + x * k + k - 1, 4 + y * k + k - 1], fill=px[x, y])
    return out


def save_gif(path, frames, ms):
    pal_im = Image.new('P', (1, 1))
    cols = []
    for fr in frames:
        for _, c in fr.getcolors(100000):
            if c not in cols:
                cols.append(c)
    assert len(cols) <= 256, len(cols)
    flat = [v for c in cols for v in c] + [0] * (768 - 3 * len(cols))
    pal_im.putpalette(flat)
    q = [fr.quantize(palette=pal_im, dither=Image.Dither.NONE) for fr in frames]
    q[0].save(path, save_all=True, append_images=q[1:], duration=ms, loop=0, disposal=1, optimize=False)


def gif_pair(path, frs, ms, bgs):
    """player on the left, computer flier on the right, each over a flat tone sampled from a mood (so the mesh shows)"""
    out = []
    for g in frs:
        im = Image.new('RGB', (2 * 24 + 4, H + 8), (22, 24, 30))
        for i, pal in enumerate((PAL_P, PAL_C)):
            ImageDraw.Draw(im).rectangle([2 + i * 26, 2, 2 + i * 26 + 23, H + 5], fill=bgs[i])
            s = render(g, pal)
            im.paste(s, (6 + i * 26, 5), s)
        out.append(up(im, 4))
    save_gif(path, out, ms)


def load_bgs(force):
    names = ['moon', 'storm', 'dusk']
    paths = {m: os.path.join(HERE, 'bg_%s_1x.png' % m) for m in names}
    if force or not all(os.path.exists(p) for p in paths.values()):
        spec = importlib.util.spec_from_file_location('bgfinal', os.path.join(BGDIR, 'draw_backgrounds_final.py'))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for m in names:
            md = mod.Mood(m)
            md.prep()
            d = md.frame(4, actors=False)
            for x, y, w in mod.ISLANDS:
                mod.put_island(d, x, y, w)
            hz = md.haz[4 % 16]                      # hazard strip again in front of the islands (as in the game)
            hm = hz[..., 3] > 0
            d[mod.HAZ_Y:][hm] = hz[..., :3][hm]
            Image.fromarray(d, 'RGB').save(paths[m])
    return {m: Image.open(p).convert('RGB') for m, p in paths.items()}


ISLANDS = [(22, 116, 60), (126, 84, 68), (230, 124, 62)]
# (animation, frame, palette, centre x, feet y, flip)
CAST = [('flap2', 7, 'player', 50, 116, False),      # standing on the left island
        ('flap2', 4, 'cpu', 160, 62, True),
        ('flap1', 1, 'player', 262, 96, False),
        ('pop2', 2, 'cpu', 96, 172, False),
        ('inflate', 5, 'player', 158, 84, False),     # respawn on the middle island
        ('flap2', 2, 'cpu', 250, 124, True),          # standing on the right island
        ('pop1', 6, 'player', 206, 178, False),
        ('fall', 1, 'cpu', 300, 190, True),
        ('flap2', 5, 'player', 20, 60, False),
        ('flap1', 5, 'cpu', 118, 40, True)]


def scene(bg, A, cast=CAST, t=None):
    im = bg.copy().convert('RGBA')
    for name, f, pal, cx, fy, flip in cast:
        frs = A[name]
        s = render(frs[(f + t) % len(frs)] if t is not None else frs[f], PALS[pal])
        if flip:
            s = s.transpose(Image.FLIP_LEFT_RIGHT)
        im.alpha_composite(s, (cx - 8, fy - H))
    return im.convert('RGB')


def tiles_unique(frames):
    seen = set()
    raw = 0
    for g in frames:
        for ty in (0, 16):
            t = tuple(''.join(g[y]) for y in range(ty, ty + 16))
            if any(c != '.' for r in t for c in r):
                raw += 1
                seen.add(t)
    return raw, len(seen)


def keys_used(frames):
    s = set()
    for g in frames:
        for r in g:
            s |= set(r)
    s.discard('.')
    return s


def dither_count(frames):
    """pixels that sit in a checker with a diagonal twin and a different 4-neighbour pair partner"""
    n = 0
    steps = {}
    for g in frames:
        for y in range(1, H - 1):
            for x in range(1, W - 1):
                c = g[y][x]
                if c == '.':
                    continue
                nb = [g[y][x - 1], g[y][x + 1], g[y - 1][x], g[y + 1][x]]
                dg = [g[y - 1][x - 1], g[y + 1][x + 1], g[y - 1][x + 1], g[y + 1][x - 1]]
                others = [k for k in nb if k != c and k != '.']
                if len(others) >= 3 and dg.count(c) >= 2 and len(set(others)) == 1:
                    n += 1
                    steps[tuple(sorted((c, others[0])))] = steps.get(tuple(sorted((c, others[0]))), 0) + 1
    return n, steps


def main():
    out = []
    bgs = load_bgs('--rebg' in sys.argv)
    med = {}
    for m, im in bgs.items():
        ls = sorted(lum(p) for p in im.crop((0, 16, 320, 176)).get_flattened_data())
        med[m] = (ls[len(ls) // 20], ls[len(ls) // 2], ls[len(ls) * 19 // 20])
    hz = {}
    for m, im in bgs.items():
        ls = sorted(lum(p) for p in im.crop((0, 192, 320, 224)).get_flattened_data())
        hz[m] = ls[len(ls) // 2]
    out.append('Sootling with gum bubbles: numbers (script output)')
    out.append('frame box 16 x 32, feet row 31, hit box columns 6..9; one palette of 15 colours + transparent per flier')
    for pn, pal in PALS.items():
        out.append('palette %-6s: %s' % (pn, ' '.join('%s=%02x%02x%02x(%d)' % (k, *c, round(lum(c))) for k, c in pal.items())))
        assert len(set(pal.values())) == 15, pn
    for pn, pal in PALS.items():
        st = {a + '/' + b: abs(lum(pal[a]) - lum(pal[b])) for a, b in DITHER_PAIRS}
        out.append('dither pair steps %-6s: %s  minimum %.1f' % (pn, '  '.join('%s %.1f' % kv for kv in st.items()), min(st.values())))
        assert min(st.values()) >= 28, st
    out.append('backdrop luminance, play area lines 16..175 (p5 / median / p95): ' +
               '  '.join('%s %d / %d / %d' % (m, *v) for m, v in med.items()))
    out.append('hazard strip median luminance (lines 192..223): ' + '  '.join('%s %d' % kv for kv in hz.items()))
    for pn, pal in PALS.items():
        for k, label in (('o', 'soot outline'), ('A', 'gum outline'), ('4', 'lit fur'), ('D', 'gum light')):
            out.append('contrast %-6s %-12s (lum %3d) against median backdrop: ' % (pn, label, round(lum(pal[k]))) +
                       '  '.join('%s %d' % (m, round(abs(lum(pal[k]) - v[1]))) for m, v in med.items()) +
                       '   against hazard: ' + '  '.join('%s %d' % (m, round(abs(lum(pal[k]) - v))) for m, v in hz.items()))
    built = {}
    for v in VARIANTS:
        A, legacy = build(v)
        built[v] = (A, legacy)
        allf = [g for n in ORDER for g in A[n]] + [legacy[5]]
        ku = keys_used(allf)
        assert ku <= set(PAL_P), ku
        raw, uniq = tiles_unique(allf)
        lraw, luniq = tiles_unique(legacy)
        dn, dsteps = dither_count(allf)
        mesh = 0
        out.append('== variant %s: %s' % (v, VARIANTS[v]['name']))
        out.append('  frames: legacy sheet 7; extended ' + ', '.join('%s %d' % (n, len(A[n])) for n in ORDER) +
                   ' = %d' % sum(len(A[n]) for n in ORDER))
        out.append('  colours used %d of 15 (unused: %s)' % (len(ku), ' '.join(sorted(set(PAL_P) - ku)) or 'none'))
        out.append('  16 x 16 tiles: legacy sheet %d non-empty, %d unique; extended set %d non-empty, %d unique (both palettes share them)'
                   % (lraw, luniq, raw, uniq))
        out.append('  checker dither pixels over the extended set: %d; pairs %s' % (dn, ', '.join('%s/%s %d' % (a, b, c) for (a, b), c in sorted(dsteps.items()))))
        for (a, b) in dsteps:
            if abs(lum(PAL_P[a]) - lum(PAL_P[b])) < 28 or abs(lum(PAL_C[a]) - lum(PAL_C[b])) < 28:
                out.append('  [WARN] checker pair %s/%s is under 28: player %.1f computer %.1f'
                           % (a, b, abs(lum(PAL_P[a]) - lum(PAL_P[b])), abs(lum(PAL_C[a]) - lum(PAL_C[b]))))
        sl = sheet_legacy(legacy)
        sl.save(os.path.join(HERE, '%s_sheet_1x.png' % v))
        view4(sl, 7, 2).save(os.path.join(HERE, '%s_sheet_4x.png' % v))
        sheet_import(legacy).save(os.path.join(HERE, '%s_import_1x.png' % v))
        se = sheet_ext(A)
        se.save(os.path.join(HERE, '%s_ext_1x.png' % v))
        view4(se, 16, 12).save(os.path.join(HERE, '%s_ext_4x.png' % v))
        for m, bg in bgs.items():
            up(scene(bg, A), 3).save(os.path.join(HERE, '%s_scene_%s_3x.png' % (v, m)))
        if '--nogif' not in sys.argv:
            tone = [bgs['moon'].getpixel((40, 60)), bgs['dusk'].getpixel((40, 60))]
            for n in ORDER:
                gif_pair(os.path.join(HERE, '%s_anim_%s_4x.gif' % (v, n)), A[n], GIF_MS[n], tone)
            # scene animation: a crop of the moon backdrop, every flier loops its own state
            cast = [('flap2', 0, 'player', 30, 60, False), ('flap1', 3, 'cpu', 62, 50, True), ('pop2', 0, 'player', 94, 62, False),
                    ('inflate', 0, 'cpu', 126, 56, False), ('pop1', 0, 'player', 30, 108, False), ('fall', 0, 'cpu', 62, 104, True),
                    ('flap2', 4, 'cpu', 94, 108, True), ('flap1', 0, 'player', 126, 104, False)]
            crop = bgs['moon'].crop((96, 20, 256, 132))
            frs = [up(scene(crop, A, cast, t), 3) for t in range(48)]
            frs = [f.quantize(255, dither=Image.Dither.NONE).convert('RGB') for f in frs] if len(set(c for f in frs[:2] for _, c in f.getcolors(100000))) > 250 else frs
            try:
                save_gif(os.path.join(HERE, '%s_anim_scene_3x.gif' % v), frs, 80)
            except AssertionError:
                q = frs[0].quantize(255, dither=Image.Dither.NONE)
                qs = [f.quantize(palette=q, dither=Image.Dither.NONE) for f in frs]
                qs[0].save(os.path.join(HERE, '%s_anim_scene_3x.gif' % v), save_all=True, append_images=qs[1:], duration=80, loop=0)
    print('\n'.join(out))
    open(os.path.join(HERE, 'numbers.txt'), 'w').write('\n'.join(out) + '\n')
    write_html(out)


WEAK = {
    'A': ['Each bubble is only 8 px wide, so the membrane has room for three shades and one gloss tick; the mesh window is 2 to 3 pixels.',
          'The strands are 1 px lines: over bright windows and over the dusk sun they nearly vanish.',
          'The two bubbles fill the whole 16 px box; any sideways wobble over 0.5 px is clipped by the box edge.'],
    'B': ['The crease between the lobes is 2 to 3 dithered pixels; at 1x on a CRT it can read as one wide oval instead of two lobes.',
          'One lobe popping while the other survives is not how a real double bubble behaves; it is a rule read-out, not physics.',
          'The membrane touches the head tufts, so the Sootling silhouette and the bubble merge more than in A.'],
    'C': ['Bubble count reads by height (snowman against ball), which is weaker than the side-by-side count when fliers overlap.',
          'The big bubble is the same size with one or two bubbles; only the small top one changes.',
          'Uses rows 1..19: the tallest shape, it hides the most backdrop and reaches the top of the box when it stretches.'],
}


def write_html(nums):
    css = ('body{background:#16181e;color:#d4d7de;font-family:Helvetica,Arial,sans-serif;margin:24px;line-height:1.45}'
           'h1{font-size:22px}h2{font-size:18px;margin-top:36px;border-top:1px solid #333842;padding-top:18px}h3{font-size:15px;margin:18px 0 6px}'
           'img{image-rendering:pixelated;image-rendering:crisp-edges;display:block;max-width:100%}'
           '.row{display:flex;flex-wrap:wrap;gap:16px;align-items:flex-start}.cell{background:#1d2028;padding:10px;border:1px solid #2c303a}'
           '.cell p{margin:6px 0 0;font-size:13px;color:#a9aebb;max-width:420px}ul{margin:6px 0;padding-left:20px;font-size:14px}'
           'pre{background:#1d2028;padding:12px;font-size:12px;overflow-x:auto;color:#b9bdc9}p{max-width:980px;font-size:14px}')
    h = ['<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>Sootling with gum bubbles, drafts</title><style>',
         css, '</style></head><body><h1>Sootling redraw with bubble gum bubbles (drafts, three bubble designs)</h1>',
         '<p>View at 100 percent browser zoom. Drafts only, nothing here is game data. The Sootling body is the same in all three '
         'designs; only the bubbles differ. Left flier in each animation is the player palette, right is the computer palette '
         '(same tiles). Backdrops are the accepted backgrounds-final renders with placeholder islands.</p>',
         '<h2>Side by side: flap with two bubbles, flap with one, pop, last pop, respawn</h2><div class="row">']
    for v in VARIANTS:
        h.append('<div class="cell"><h3>%s: %s</h3>' % (v, VARIANTS[v]['name']))
        h.append('<div class="row">' + ''.join('<img src="%s_anim_%s_4x.gif" width="208" height="160" alt="%s %s">' % (v, n, v, n)
                                                 for n in ('flap2', 'flap1')) + '</div>')
        h.append('<div class="row" style="margin-top:8px">' + ''.join('<img src="%s_anim_%s_4x.gif" width="208" height="160" alt="%s %s">' % (v, n, v, n)
                                                                      for n in ('pop2', 'pop1')) + '</div>')
        h.append('<div class="row" style="margin-top:8px">' + ''.join('<img src="%s_anim_%s_4x.gif" width="208" height="160" alt="%s %s">' % (v, n, v, n)
                                                                      for n in ('inflate', 'fall')) + '</div>')
        h.append('<p>%s</p><p>Weak points:</p><ul>%s</ul></div>' % (VARIANTS[v]['idea'], ''.join('<li>%s</li>' % w for w in WEAK[v])))
    h.append('</div><p>The fall animation and the Sootling body are identical in all three designs. The current sheet has no walk or stand '
             'state, so none was drawn; standing on an island uses the glide frame.</p>')
    h.append('<h2>In motion over the moon backdrop (3x)</h2><div class="row">')
    for v in VARIANTS:
        h.append('<div class="cell"><img src="%s_anim_scene_3x.gif" width="480" height="336" alt="scene animation %s"><p>%s. Top row: flap with two, flap with one, pop, respawn. '
                 'Bottom row: last pop, fall, flap with two, flap with one.</p></div>' % (v, v, v))
    h.append('</div>')
    for m, label in (('moon', 'Clear night'), ('storm', 'Storm'), ('dusk', 'Ember dusk')):
        h.append('<h2>Scene, %s (3x)</h2>' % label)
        for v in VARIANTS:
            h.append('<h3>%s: %s</h3><img src="%s_scene_%s_3x.png" width="960" height="672" alt="scene %s %s">' % (v, VARIANTS[v]['name'], v, m, v, m))
    h.append('<h2>Sheets</h2><p>Build layout (7 frames: glide with two, flap up, flap down, glide with one, flap up with one, no bubble, fall; '
             'top row player, bottom row computer) and the extended sheet (rows: flap with two 8, flap with one 8, pop 12, last pop 12, '
             'respawn 16, fall 6; player block then computer block).</p>')
    for v in VARIANTS:
        h.append('<h3>%s</h3><div class="row"><div class="cell"><img src="%s_sheet_4x.png" alt="sheet %s"><p>Build layout, 4x</p></div></div>'
                 '<div class="cell" style="margin-top:10px"><img src="%s_ext_4x.png" alt="extended %s"><p>Extended sheet, 4x</p></div>' % (v, v, v, v, v))
    h.append('<h2>Numbers</h2><pre>%s</pre></body></html>' % '\n'.join(nums).replace('<', '&lt;'))
    open(os.path.join(HERE, 'index.html'), 'w').write('\n'.join(h))


if __name__ == '__main__':
    main()
