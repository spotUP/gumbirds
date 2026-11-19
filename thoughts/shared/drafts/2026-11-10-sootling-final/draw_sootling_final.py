#!/opt/homebrew/bin/python3.14 -I
"""Sootling, final art pass (32 x 48, 63 frames). Art files only, no game code.

Run:  /opt/homebrew/bin/python3.14 -I draw_sootling_final.py [--nogif]

Reuses the draft generator ../2026-11-10-sootling-b-32x48/draw_sootling_b.py (palette helpers, wing, springs, lobe
layout, neck chain, tile and contrast statistics, GIF writer) and replaces what the verdict changed:
  - body: five hand-authored poses (squash, in-between, rest, in-between, stretch), two white eyes, no cap, no goggle;
    animation fix pass: no row is doubled or deleted, every frame steps between two neighbouring poses, the wing is
    eight hand stamps, eyes, tufts and feet follow late (see README, section Animation fix pass)
  - gum: solid candy, full dark keyline, smooth bands, rim light, fixed specular stamp; no checker anywhere on gum
  - pops: outlined gum ropes instead of loose strand pixels, fragments under 5 px removed, droplets at least 2 px
  - fall: 10 frames
Writes only into this directory.
"""
import os
import sys
import math
import json
import importlib.util

sys.dont_write_bytecode = True
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
DRAFT = os.path.join(HERE, '..', '2026-11-10-sootling-b-32x48', 'draw_sootling_b.py')
BGDIR = os.path.join(HERE, '..', '2026-11-10-backgrounds-final')
_spec = importlib.util.spec_from_file_location('sootling_draft', DRAFT)
D = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(D)

W, H = D.W, D.H
LX, LY = D.LX, D.LY
KEYS = D.KEYS
lum = D.lum

# ---------------------------------------------------------------- palette (draft ramps; gum deep line A lifted so that
# every colour that sits right inside the keyline is at least 28 above the darkest sky, luminance 21)
D.PAL_P['A'] = D.hexc('#6c1080')
D.PAL_C['A'] = D.hexc('#085040')
D.PAL_C['e'] = (16, 66, 107)        # computer ember dark (index 7): lifted so the inner-line step on dusk is at least 28
PAL_P, PAL_C = D.PAL_P, D.PAL_C
PALS = D.PALS

# ---------------------------------------------------------------- gum rest shapes (cx, cy, rx, ry). The single bubble
# is only 12 percent larger in area than one lobe: a pop lets air out, the survivor must not swell.
D.REST_ONE = (16.0, 14.4, 8.0, 8.4)
D.REST_TWO = ((9.9, 14.6, 7.2, 8.3), (22.0, 14.0, 7.2, 8.3))
ANCHOR = (21.5, 21.0)

# ================================================================ body: hand-authored poses
# The fur ball is five separate hand-drawn maps. Bottom keyline sits on frame row 45 in every pose, so the feet never
# leave row 47. S and T are the keys, S1 and T1 are drawn in-betweens (not computed), R is the rest pose.
#   S  squash key   26 x 17      S1 in-between 25 x 18      R rest 24 x 19      T1 in-between 23 x 20      T stretch key 22 x 21
# Volume is kept: what the height loses, the width gains. No pose is made by deleting or doubling a row of another.
# (frame column of map column 0, rows)
POSES = dict(
    S=(3, (
        ".......ooooooooooooo......",
        "....ooo2332344444444oo....",
        "..oo2222233344444444rroo..",
        ".o222212333334444444444ro.",
        ".o2222223333333444444433ro",
        "o22222223333333334444433ro",
        ".o22222222333333333333332o",
        "o212222222233333333333322o",
        ".o21122222222233333333222o",
        "o221112222222222333333222o",
        ".o21111222222222223332222o",
        ".o2211111222222222222222o.",
        "..o22111111122222222222o..",
        "...o222111111112222222o...",
        "....oo22222111122222oo....",
        "......ooo22222222ooo......",
        ".........oooooooo.........",
    )),
    S1=(4, (
        "........oooooooooooo.....",
        "....oooo233234444444oo...",
        "..oo2222233344444444rroo.",
        ".o222212333334444444443ro",
        "o2222223333333444444433ro",
        ".o222222233333333344433ro",
        "o21222222233333333333332o",
        ".o2112222222233333333322o",
        "o22111222222222333333222o",
        ".o2111122222222223332222o",
        ".o2211112222222222222222o",
        ".o221111122222222222222o.",
        "..o2211111112222222222o..",
        "..o222111111112222222o...",
        "...o2222111111222222o....",
        "....oo2222211112222oo....",
        "......ooo22222222ooo.....",
        ".........oooooooo........",
    )),
    R=(4, (
        "........ooooooooooo.....",
        "....oooo23323444444oo...",
        "...o222223334444444rro..",
        "..o22212333344444444rro.",
        ".o2222233333444444443ro.",
        ".o22222333333344444433ro",
        "o222222333333333444433ro",
        ".o222222233333333333332o",
        "o2122222223333333333322o",
        ".o211222222233333333322o",
        "o2211122222222333333222o",
        ".o211112222222223332222o",
        ".o22111112222222222222o.",
        "..o2211111122222222222o.",
        "..o222111111122222222o..",
        "...o2221111111222222o...",
        "....o22222111122222o....",
        ".....ooo222222222oo.....",
        "........ooooooooo.......",
    )),
    T1=(4, (
        "........oooooooooo.....",
        ".....ooo2332344444oo...",
        "...oo2222233344444rro..",
        "..o2221233334444444rro.",
        ".o222222333344444444ro.",
        ".o2222223333344444443ro",
        "o22222233333334444433ro",
        ".o2222223333333334443ro",
        "o222222223333333333332o",
        ".o21222222333333333322o",
        "o211222222233333333322o",
        ".o21112222222233333222o",
        "o221111222222222332222o",
        ".o2211111222222222222o.",
        ".o2221111112222222222o.",
        "..o22211111112222222o..",
        "..o2222111111122222o...",
        "...oo2222211112222oo...",
        ".....ooo22222222ooo....",
        "........oooooooo.......",
    )),
    T=(5, (
        ".......ooooooooo......",
        "....ooo233234444ooo...",
        "...o2222233444444rro..",
        "..o222123334444444rro.",
        ".o22222233334444444ro.",
        ".o222222333334444443ro",
        "o2222222333333444443ro",
        ".o222222333333334443ro",
        "o22222223333333333332o",
        ".o2122222333333333322o",
        "o21122222233333333322o",
        ".o2111222222333333222o",
        "o22111122222223332222o",
        ".o2211112222222222222o",
        ".o222111112222222222o.",
        ".o222111111222222222o.",
        "..o2221111111222222o..",
        "..o2222111111122222o..",
        "...oo222221111222oo...",
        ".....ooo2222222ooo....",
        "........ooooooo.......",
    )),
)
POSE_ORDER = ('S', 'S1', 'R', 'T1', 'T')
EYE_DY = dict(S=1, S1=0, R=0, T1=0, T=-1)       # where the eyes sit in a pose; the exposure sheets let them lag a frame


def _check_pose(name):
    xoff, rows = POSES[name]
    w = len(rows[0])
    for r in rows:
        assert len(r) == w, (name, r, len(r), w)
    for j, r in enumerate(rows):
        for i, k in enumerate(r):
            if k in '.o':
                continue
            nb = [(i + a, j + b) for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))]
            for x, y in nb:                                     # the keyline is closed: no fur pixel touches air
                assert 0 <= x < w and 0 <= y < len(rows) and rows[y][x] != '.', (name, j, i)
            if k == '1':                                        # deepest fur never sits right inside the keyline
                assert all(rows[y][x] != 'o' for x, y in nb), (name, j, i)
    return sum(1 for r in rows for k in r if k != '.')


POSE_AREA = {n: _check_pose(n) for n in POSE_ORDER}
for _n in POSE_ORDER:                                           # volume: every pose within 4 percent of rest
    assert abs(POSE_AREA[_n] - POSE_AREA['R']) <= 0.04 * POSE_AREA['R'], (_n, POSE_AREA)

# fur ticks drawn on the rest pose (x, row from the bottom keyline, key). In the other poses each tick keeps its place
# in the mass (scaled with the pose), so the clusters slide a fraction of the silhouette change: sub-pixel feel.
TICKS = (
    (8, 14, '3'), (7, 13, '3'), (9, 11, '3'), (8, 10, '3'), (11, 9, '3'), (10, 8, '3'),
    (14, 7, '3'), (13, 6, '3'), (17, 6, '3'), (16, 5, '3'),
    (4, 12, '3'), (3, 11, '3'), (5, 14, '3'),
    (9, 7, '1'), (8, 6, '2'), (11, 5, '2'), (10, 4, '2'), (7, 4, '2'), (6, 3, '1'),
    (15, 4, '1'), (14, 3, '1'),
    (3, 8, '2'), (4, 6, '2'), (5, 5, '2'),
    (14, 15, '3'), (13, 14, '4'), (12, 13, '4'), (19, 11, '4'), (18, 10, '4'),
    (20, 5, '3'), (19, 4, '3'), (18, 3, '3'), (17, 2, '3'),
)


def pose_rows(name):
    xoff, rows = POSES[name]
    rows = [list(r) for r in rows]
    n, w = len(rows), len(rows[0])
    pc = xoff + (w - 1) / 2.0
    for x, rb, k in TICKS:
        j = n - 1 - int(rb * (n - 1) / 18.0 + 0.5)
        i = int(pc + (4 + x - 15.5) * w / 24.0 + 0.5) - xoff
        if 0 < j < n - 1 and 0 < i < w - 1 and rows[j][i] in '234' and 'o' not in (rows[j][i - 1], rows[j][i + 1], rows[j - 1][i], rows[j + 1][i]):
            rows[j][i] = k
    return xoff, rows


# fur tufts, five hand shapes (L = dark side, H = lit side); the bottom row replaces the top keyline of the ball
TUFTS = dict(
    U=("..o.", ".oHo", "oLHo"),                                 # up, rest
    UL=(".o..", "oHo.", "oLHo"),                                # tip dragged back
    F=(".oo.", "oLHo"),                                         # pressed flat while the body rises
    TA=("..o.", ".oHo", ".oHo", "oLHo"),                        # streaming up while the body drops
    TL=(".o..", "oHo.", ".oHo", "oLHo"),                        # streaming up, tip whipping back
    TB=("..o.", ".oHo", "oHo.", "oLHo"),                        # streaming up, the wave is in the middle
)
# ember wing, eight hand poses: (rows, root column, root row). The root is pinned to frame (11, 36).
WINGS = (
    ((".oo....", "oggo...", "ogffo..", ".ogffo.", ".ogffeo", "..offeo", "..ofeeo", "...oeeo", "....oo."), 5, 8),   # 0 up high
    ((".ooo.....", "oggfoo...", ".ogfffoo.", "..offffeo", "...ofeeeo", "....ooeeo", "......oo."), 7, 6),         # 1 up
    (("..ooooooo.", "oogggfffeo", "ogfffffeeo", ".oofffeeo.", "...ooooo.."), 8, 2),                                # 2 level, spread
    (("......oo.", "....ooeeo", "...ogfeeo", "..ogfffeo", ".ogfffoo.", "ogffoo...", ".ooo....."), 7, 0),         # 3 down
    (("....oo.", "...ogeo", "..ogfeo", "..ogfeo", ".ogffeo", ".ogffo.", "ogffo..", "offo...", ".oo...."), 5, 0),   # 4 down low
    (("..oooo", ".ogfeo", "ogffeo", "offeo.", ".ooo.."), 5, 1),                                                   # 5 folded, low
    ((".ooo..", "ogfeo.", "ogffeo", ".offeo", "..oooo"), 5, 3),                                                   # 6 folded, level
    (("..oo...", ".oggo..", ".ogffo.", ".ogffo.", ".ogffeo", "..offeo", "..ofeeo", "...oeeo", "....oo."), 5, 8),   # 7 up high, tip over
)
# one foot, 6 wide, rows 45..47: (column shift, rows)
FEET = dict(
    REST=(0, (".oeo..", "offgoo", "oooooo")),
    BACK=(-1, (".oeo..", "offgoo", "oooooo")),                   # near foot spread out under a squashed ball
    FWD=(1, (".oeo..", "offgoo", "oooooo")),                     # far foot spread out
    TOE=(0, (".oeo..", ".ofgo.", ".oooo.")),                     # hanging, toes down
    TUCK=(0, (".oo...", "ofgo..", ".oo...")),                    # pulled in
)
# eyes: near eye at frame column 14, far eye at frame column 20 (they share one keyline column); row offset from row 30.
# The far eye is 5 wide: white on both sides of the pupil, so it no longer reads as a letter C.
NEAR = dict(
    open=(0, (".ooooo.", "o4444ro", "orrrrro", "orrroro", "orrooro", "orrooro", "o4rrrro", ".ooooo.")),
    wide=(-1, (".ooooo.", "orrrrro", "orrrrro", "orrrrro", "orrroro", "orrooro", "orrrrro", "o4rrrro", ".ooooo.")),
    squint=(3, ("ooooooo", "orrrooo", "o4rrooo", ".ooooo.")),
    shut=(3, (".33333.", "ooooooo", ".o...o.")),
)
FAR = dict(
    open=(1, (".ooo.", "o44ro", "orrro", "ororo", "ororo", "orrro", ".ooo.")),
    wide=(0, (".ooo.", "orrro", "orrro", "orrro", "ororo", "ororo", "orrro", ".ooo.")),
    squint=(3, ("ooooo", "orroo", "o4roo", ".ooo.")),
    shut=(4, ("ooooo",)),
)
for _rows, _ax, _ay in WINGS:
    assert len({len(r) for r in _rows}) == 1 and _rows[_ay][_ax] != '.', _rows


def stamp(g, x0, y0, rows, only=None, sub=None):
    for j, row in enumerate(rows):
        for i, k in enumerate(row):
            if k != '.':
                D.put(g, x0 + i, y0 + j, sub.get(k, k) if sub else k, only)


def body_geom(T=None, dy=0, sq=0.0, puff=False):
    """centre, radii and the lips of the rest pose. The lips stay on row 38 in every pose."""
    return 15.5, 35.5, 11.5, 10.0, (27.6, 38.5)


def declump(g, keys, passes=2):
    """hand-clean rule: in a band-shaded area a pixel that matches none of its four neighbours is noise; it takes the
    colour most of its neighbours have"""
    for _ in range(passes):
        ch = []
        for y in range(1, H - 1):
            for x in range(1, W - 1):
                c = g[y][x]
                if c not in keys:
                    continue
                nb = [g[y][x - 1], g[y][x + 1], g[y - 1][x], g[y + 1][x]]
                if c in nb:
                    continue
                cand = [k for k in nb if k in keys]
                if len(cand) >= 3:
                    ch.append((x, y, max(set(cand), key=cand.count)))
        for x, y, k in ch:
            g[y][x] = k


BODY_LAYERS = []                                                # body-only copy of every frame, for the motion numbers


def draw_body(g, pose='R', wing=6, lens='open', eye=None, tl='U', tr='U', fn='REST', ff='REST', splat=None, gumbit=False):
    b = D.grid()
    xoff, rows = pose_rows(pose)
    top = 45 - (len(rows) - 1)
    stamp(b, xoff, top, ["".join(r) for r in rows])
    # ---- tufts (follow-through is set per frame in the exposure sheets)
    for x, name, lo, hi in ((10, tl, '2', '3'), (15, tr, '3', '4')):
        st = TUFTS[name]
        stamp(b, x, top - (len(st) - 1), st, sub=dict(L=lo, H=hi))
    # ---- wing, in front of the flank
    wr, ax, ay = WINGS[wing]
    stamp(b, 11 - ax, 36 - ay, wr)
    # ---- eyes
    ey = 30 + (EYE_DY[pose] if eye is None else eye)
    o, rws = NEAR[lens]
    stamp(b, 14, ey + o, rws)
    o, rws = FAR[lens]
    stamp(b, 20, ey + o, rws)
    # ---- lips (the gum leaves here): on the right keyline of row 38
    ly = 38
    lx = max(x for x in range(W) if b[ly][x] != '.') - 1
    for x, y, k in ((lx - 1, ly, 'e'), (lx, ly, 'f'), (lx - 1, ly + 1, 'o'), (lx, ly + 1, 'e'), (lx - 2, ly, 'o')):
        D.put(b, x, y, k, '1234ro')
    if gumbit:
        for x, y, k in ((lx + 1, ly, 'D'), (lx + 2, ly, 'o'), (lx + 1, ly - 1, 'o'), (lx + 1, ly + 1, 'C'), (lx + 2, ly + 1, 'o'),
                        (lx + 1, ly + 2, 'o')):
            D.put(b, x, y, k)
    # ---- feet, each on its own timing
    for x, name in ((9, fn), (17, ff)):
        dx, fr = FEET[name]
        stamp(b, x + dx, 45, fr)
    # ---- gum stuck on the face after a pop
    if splat is not None:
        r = (3.9, 3.2, 2.3, 1.3)[splat]
        fx, fy2 = 23.0, 36.5
        for y in range(int(fy2 - r - 1), int(fy2 + r + 2)):
            for x in range(int(fx - r - 1), int(fx + r + 2)):
                px, py = x + .5 - fx, y + .5 - fy2
                d = math.hypot(px, py * 1.15)
                if d > r or not (0 <= x < W and 0 <= y < H) or b[y][x] == '.':
                    continue
                v = px * LX + py * LY
                b[y][x] = 'A' if d > r - 0.9 else ('E' if v > 0.45 * r else ('D' if v > 0.0 else 'C'))
        if splat == 0:
            D.put(b, int(fx + 0.3 * r), int(fy2 - 0.4 * r), 'w')
        n = (3, 5, 4, 0)[splat]
        for i in range(n):                                      # drip: solid, dark tip
            D.put(b, int(fx + 1), int(fy2 + r) + i, 'D' if i < n - 1 else 'B', '1234ro')
    for y in range(H):
        for x in range(W):
            if b[y][x] != '.':
                g[y][x] = b[y][x]
    BODY_LAYERS.append(b)


# ================================================================ gum membrane: solid candy, no checker
GLOSS_BIG = ("www.", ".www", "...w")
GLOSS_SMALL = ("ww", ".w")


def draw_gum(g, lobes, neck, style=None, tear=None):
    lobes = [b for b in lobes if b and b[2] > 0.5 and b[3] > 0.5]
    if not lobes:
        return
    blobs = lobes + list(neck)
    nl = len(lobes)
    K = 7.0
    mask = {}
    for y in range(H):
        for x in range(W):
            px, py = x + .5, y + .5
            ds = [math.hypot((px - cx) / rx, (py - cy) / ry) for cx, cy, rx, ry in blobs]
            f = ds[0] if len(ds) == 1 else -math.log(sum(math.exp(-K * d) for d in ds)) / K
            if f > 1.0:
                continue
            near = min(range(len(ds)), key=lambda i: ds[i])
            rimd = None
            own = [i for i in range(nl) if i != near and ds[i] <= 1.0] if tear and near == tear[0] else []
            if own:                                             # inside the surviving lobe's own ellipse: it stays,
                near = min(own, key=lambda i: ds[i])            # so the survivor keeps a round outline (no flat cut)
            elif tear and near == tear[0]:
                _, tx, ty, reach, seed = tear
                dd = math.hypot(px - tx, py - ty)
                lim = reach + D.rag(math.atan2(py - ty, px - tx), seed)
                if dd < lim:
                    continue
                rimd = dd - lim
            mask[(x, y)] = (near, ds, rimd)
    if any(x in (0, W - 1) or y == 0 for (x, y) in mask):
        D.STATS['edge'] += 1
    dp = D.depths(mask)
    layer = D.grid()
    for (x, y), (near, ds, rimd) in mask.items():
        cx, cy, rx, ry = blobs[near]
        nx, ny = (x + .5 - cx) / rx, (y + .5 - cy) / ry
        d = ds[near]
        lit = nx * LX + ny * LY
        p = dp[(x, y)]
        if p == 1:
            k = 'o'                                             # full dark keyline, neck included
        elif near >= nl or rx < 2.8:                            # neck and bubbles that are still tiny
            k = 'E' if lit > 0.55 else ('D' if lit > 0.05 else 'C')
        else:
            if p == 2:                                          # inner line: rim light on the lit side, deep on the far side
                k = 'E' if lit > 0.55 else ('C' if lit > 0.10 else ('B' if lit > -0.40 else 'A'))
            else:                                               # bands = distance from the hot spot, sphere style
                s = math.hypot(nx - 0.30, ny + 0.42)
                k = 'E' if s < 0.36 else ('D' if s < 0.78 else ('C' if s < 1.16 else 'B'))
                if k == 'B' and d > 0.70 and lit < -0.50:
                    k = 'C'                                     # reflected light inside the shadow edge
            if p > 1 and nl == 2 and lobes[0][2] >= 3 and lobes[1][2] >= 3 and max(ds[0], ds[1]) < 1.3:
                dd = abs(ds[0] - ds[1])                         # crease where the two lobes meet
                if dd < 0.075:
                    k = 'A' if p == 2 else 'B'
                elif dd < 0.19 and ds[1] < ds[0] and k in ('C', 'B') and p > 2 and ny < 0.3:
                    k = 'D'
            if rimd is not None and rimd < 2.2 and p > 1:
                k = 'w' if rimd < 0.9 else 'E'                  # retracting rim: thick and pale, solid
        layer[y][x] = k
    declump(layer, 'ABCDE')
    for i in range(nl):                                         # specular: one fixed hand shape per size class
        cx, cy, rx, ry = lobes[i]
        if rx < 2.8:
            continue
        rows, ox, oy = (GLOSS_BIG, 0.14, -0.66) if rx > 5 else (GLOSS_SMALL, 0.10, -0.55)
        x0, y0 = round(cx + ox * rx), round(cy + oy * ry)
        for j, row in enumerate(rows):
            for ii, k in enumerate(row):
                q = (x0 + ii, y0 + j)
                if k == 'w' and q in mask and mask[q][0] == i and mask[q][2] is None and dp[q] >= 3:
                    layer[q[1]][q[0]] = 'w'
    for (x, y) in mask:
        g[y][x] = layer[y][x]


def line(a, b):
    n = int(max(abs(b[0] - a[0]), abs(b[1] - a[1])) * 2) + 1
    out = []
    for i in range(n + 1):
        p = (int(a[0] + (b[0] - a[0]) * i / n), int(a[1] + (b[1] - a[1]) * i / n))
        if not out or out[-1] != p:
            out.append(p)
    return out


def rope(g, pts):
    """gum rope: one connected core line from pts[0] (fixed end) to pts[-1] (free end, 2 x 2 bead), dark keyline all
    round. Only empty cells are painted, so it never cuts into a bubble or its keyline."""
    core = []
    for a, b in zip(pts, pts[1:]):
        for q in line(a, b):
            if q not in core:
                core.append(q)
    fx, fy = core[-1]
    cells = [(x, y, 'D') for x, y in core] + [(fx, fy, 'E'), (fx + 1, fy, 'D'), (fx, fy - 1, 'D'), (fx + 1, fy - 1, 'C')]
    done = []
    for x, y, k in cells:
        if 1 <= x < W - 1 and 1 <= y < H - 1 and (g[y][x] == '.' or (x, y) in done):
            g[y][x] = k
            done.append((x, y))
    for x, y in done:
        for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if g[y + b][x + a] == '.':
                g[y + b][x + a] = 'o'


def despeckle(g, least=5):
    """remove loose fragments: 8-connected groups of fewer than `least` pixels"""
    seen = set()
    for y in range(H):
        for x in range(W):
            if g[y][x] == '.' or (x, y) in seen:
                continue
            comp, todo = [], [(x, y)]
            seen.add((x, y))
            while todo:
                cx, cy = todo.pop()
                comp.append((cx, cy))
                for a in (-1, 0, 1):
                    for b in (-1, 0, 1):
                        q = (cx + a, cy + b)
                        if 0 <= q[0] < W and 0 <= q[1] < H and q not in seen and g[q[1]][q[0]] != '.':
                            seen.add(q)
                            todo.append(q)
            if len(comp) < least:
                for cx, cy in comp:
                    g[cy][cx] = '.'


def strip_bare(g):
    """a keyline pixel with no fill pixel next to it (8 neighbours) outlines nothing: remove it"""
    kill = []
    for y in range(H):
        for x in range(W):
            if g[y][x] != 'o':
                continue
            if not any(0 <= x + a < W and 0 <= y + b < H and g[y + b][x + a] not in '.o'
                       for a in (-1, 0, 1) for b in (-1, 0, 1)):
                kill.append((x, y))
    for x, y in kill:
        g[y][x] = '.'


def droplets(g, origin, f, seed, n=4):
    """gum droplets on ballistic paths with drag (draft physics); every droplet is at least 2 px with a dark side"""
    for i in range(n):
        a = -math.pi / 2 + (i - (n - 1) / 2) * 0.62 + 0.20 * math.sin(seed + i * 1.7)
        sp = 2.3 + 1.5 * ((i * 37 + seed * 11) % 7) / 6
        life = 3 + i % 3
        vx, vy = sp * math.cos(a), sp * math.sin(a)

        def pos(t):
            return origin[0] + vx * t * (1 - 0.06 * t), origin[1] + vy * t + 0.30 * t * t
        for _ in range(10):
            if all(2 <= pos(t)[0] <= W - 4 and 2 <= pos(t)[1] <= H - 5 for t in range(life + 1)):
                break
            vx, vy = vx * 0.8, vy * 0.8
        else:
            D.STATS['clipped'] += 1
        if f > life:
            continue
        x, y = (int(v) for v in pos(f))
        if f <= 2:
            cells = ((0, 0, 'E'), (1, 0, 'D'), (0, 1, 'C'), (1, 1, 'B'))
        else:
            cells = ((0, 0, 'D'), (0, 1, 'C'))                  # falling, stretched
        foot = [(x + a, y + b) for a in range(-1, 3) for b in range(-1, 3)]
        if all(0 <= u < W and 0 <= v < H and g[v][u] == '.' for u, v in foot):
            for a, b, k in cells:
                g[y + b][x + a] = k
            for a, b, _ in cells:                               # bead keyline
                for u, v in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    if g[y + b + v][x + a + u] == '.':
                        g[y + b + v][x + a + u] = 'o'


# ================================================================ animations
D.body_geom = body_geom
D.draw_body = draw_body
D.draw_gum = draw_gum
T = dict(membrane='candy')
POSE_H = {n: len(POSES[n][1]) for n in POSE_ORDER}
FOOT_OF = dict(S=('BACK', 'FWD'), S1=('REST', 'REST'), R=('REST', 'REST'), T1=('TOE', 'TOE'), T=('TUCK', 'TUCK'))


def follow(poses, loop):
    """Exposure sheet of everything that hangs on the fur ball, derived from the body poses so that nothing moves in
    the same frame as the mass that drives it:
      eyes       sit where the pose of the frame before put them (one frame late)
      left tuft  streams up while the top of the ball drops, lies flat while it rises, never changes by more than
                 one row per frame; the right tuft does the same one frame later
      near foot  shows the pose of the frame before (dangle, tuck, spread), the far foot the pose two frames before
    Every body step must be between two neighbouring hand poses (asserted)."""
    n = len(poses)
    idx = [POSE_ORDER.index(p) for p in poses]
    for a, b in list(zip(idx, idx[1:])) + ([(idx[-1], idx[0])] if loop else []):
        assert abs(a - b) <= 1, poses

    def at(f):
        return poses[f % n] if loop else poses[max(0, f)]
    eyes = [EYE_DY[at(f - 1)] for f in range(n)]
    v = [POSE_H[at(f)] - POSE_H[at(f - 1)] for f in range(n)]   # > 0: the top of the ball moves up
    h, hs = 3, []
    for _ in range(3 if loop else 1):
        hs = []
        for f in range(n):
            target = 4 if v[f] < 0 else (2 if v[f] > 0 else 3)
            h += (target > h) - (target < h)
            hs.append(h)
    names = []
    for f in range(n):
        prev = hs[f - 1] if (loop or f) else 3
        names.append('F' if hs[f] == 2 else (('U' if v[f] == 0 else 'UL') if hs[f] == 3 else ('TL' if prev == 4 else 'TA')))
    tr = [names[f - 1] if (loop or f) else 'U' for f in range(n)]
    fn = [FOOT_OF[at(f - 1)][0] for f in range(n)]
    ff = [FOOT_OF[at(f - 2)][1] for f in range(n)]
    return eyes, names, tr, fn, ff


def body(g, poses, ex, f, wing, lens, **kw):
    draw_body(g, poses[f], wing, lens, ex[0][f], ex[1][f], ex[2][f], ex[3][f], ex[4][f], **kw)


# flap: the ball gathers (squash) while the wing is high, the down stroke lifts it, it is longest one frame after the
# wing is lowest, and settles through the rest pose. Triangle through the five hand poses: one pose step per frame.
FLAP_POSE = ['S1', 'S', 'S1', 'R', 'T1', 'T', 'T1', 'R']
FLAP_WING = [0, 1, 2, 3, 4, 5, 6, 7]                           # down stroke 5 frames (spread), up stroke 3 (folded)


def anim_flap(n):
    q0 = D.peak(D.spring_loop(0.95, 0.30, -0.115), 0.10)        # bubble springs of the draft, driven by FLAP_ACC
    y0 = D.peak(D.spring_loop(0.60, 0.35, 0.80), 1.3)
    q1 = D.peak(D.spring_loop(1.25, 0.28, -0.105, phase=7), 0.10)
    y1 = D.peak(D.spring_loop(0.75, 0.35, 0.72, phase=7), 1.2)
    sx = D.peak(D.spring_loop(0.80, 0.30, 0.50), 0.9)
    ex = follow(FLAP_POSE, True)
    frs = []
    for f in range(8):
        g = D.grid()
        if n == 2:
            b0, b1 = D.layout(T, 1, 1)
            b0 = D.wob(b0, q0[f], -sx[f], y0[f])
            b1 = D.wob(b1, q1[f], sx[f], y1[f])
        else:
            b0, b1 = D.layout(T, 1, 0)
            b0 = D.wob(b0, q0[f] * 0.8, sx[f] * 0.8, y0[f])
        D.draw_bubbles(g, T, b0, b1, sway=sx[f] * 1.6)
        body(g, FLAP_POSE, ex, f, FLAP_WING[f], 'open')
        frs.append(g)
    return frs


POP_POSE = {12: ['R', 'S1', 'S', 'S1', 'R', 'T1', 'R', 'S1', 'R', 'R', 'R', 'R'],      # flinch, recoil, settle
            10: ['R', 'S1', 'S', 'S1', 'R', 'T1', 'R', 'R', 'T1', 'T']}                # ends long: the fall follows
POP_WING = [6, 1, 0, 1, 2, 3, 4, 5, 6, 1, 6, 6]
POP_PANIC = [1, 0, 7, 0]                                        # last pop: the wing beats high before the fall


def anim_pop(n, N):
    """n = lobes before the pop. Frame 0 swells with a flash at the puncture; the tear front runs across the lobe and
    the membrane retracts into a thick pale rim; droplets fly on ballistic paths; two gum ropes snap back (damped
    spring) to the surviving bubble (n = 2) or to the lips (n = 1); a glob lands on the face and drips off. With
    n = 2 the survivor pulls round into one bubble and rings."""
    m = D.mouth_of(T)
    if n == 2:
        full0, full1 = D.layout(T, 1, 1)
        pb = full1
    else:
        full0, _ = D.layout(T, 1, 0)
        pb = full0
    pun = (pb[0] + 0.30 * pb[2], pb[1] - 0.82 * pb[3])
    diam = 2 * max(pb[2], pb[3])
    reach = [None, 0.30, 0.62, 0.92, 1.25]
    qk = D.ring(1.1, 0.26, 0.0, -0.20, N)
    sk = D.ring(0.7, 0.30, 0.0, 1.5, N)
    home = (ANCHOR[0] + 1.5, ANCHOR[1] + 1.0) if n == 2 else (m[0] + 0.5, m[1] - 1.0)
    ends = [(pb[0] - 0.5 * pb[2], pb[1] - 0.1 * pb[3]), (pb[0] + 0.75 * pb[2], pb[1] + 0.35 * pb[3])]
    if N == 12:
        lens = D.POP_LENS
        spl = D.POP_SPLAT
    else:
        lens = ['wide', 'squint', 'squint', 'squint', 'shut', 'shut', 'shut', 'squint', 'open', 'wide']
        spl = [None, None, None, None, None, 0, 0, 1, 2, 3]
    poses = POP_POSE[N]
    ex = follow(poses, False)
    frs = []
    for f in range(N):
        g = D.grid()
        merge = min(1.0, max(0.0, (f - 1) / 6.0))
        merge = merge * merge * (3 - 2 * merge)
        if n == 2:
            b0 = D.layout(T, 1, 1 - merge)[0]
            b0 = D.wob(b0, qk[f], -0.6 * sk[f], abs(qk[f]) * 3 if f else 0)
            b1, tear = None, None
            if f == 0:
                b1 = (full1[0], full1[1], full1[2] * 1.08, full1[3] * 1.08)
            elif f < len(reach):
                sh = 1 - 0.10 * f
                b1 = (D.lerp(full1[0], ANCHOR[0], 0.12 * f), D.lerp(full1[1], ANCHOR[1], 0.12 * f), full1[2] * sh, full1[3] * sh)
                tear = (pun[0], pun[1], reach[f] * diam, 1.3 + f)
            D.draw_bubbles(g, T, b0, b1, tear, sway=sk[f])
        else:
            if f == 0:
                D.draw_bubbles(g, T, (full0[0], full0[1], full0[2] * 1.06, full0[3] * 1.06), None)
            elif f < len(reach):
                sh = 1 - 0.10 * f
                b = (D.lerp(full0[0], ANCHOR[0], 0.12 * f), D.lerp(full0[1], ANCHOR[1], 0.12 * f), full0[2] * sh, full0[3] * sh)
                D.draw_bubbles(g, T, b, None, (pun[0], pun[1], reach[f] * diam, 1.3 + f), neck=f < 3)
        despeckle(g, 6)
        strip_bare(g)
        despeckle(g, 6)
        if f == 0:                                                         # puncture flash: one connected star
            x, y = int(pun[0]), int(pun[1])
            for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1), (2, 0), (-2, 0), (0, -2), (0, 2)):
                D.put(g, x + dx, y + dy, 'w')
        if 3 <= f <= 7:                                                    # ropes snap back, damped spring
            t = (f - 3) / 4.0
            L = math.exp(-2.2 * t) * math.cos(4.2 * t)
            for i, e in enumerate(ends[1:]):
                p = (home[0] + (e[0] - home[0]) * L, home[1] + (e[1] - home[1]) * L + 2.5 * t * t)
                p = (min(W - 4, max(2, p[0])), max(3, p[1]))
                sag = (1.0 - 2 * i) * (1.2 + 2.0 * t)
                c = ((home[0] + p[0]) / 2 + sag, (home[1] + p[1]) / 2 + abs(sag))
                pts = [((1 - u) ** 2 * home[0] + 2 * u * (1 - u) * c[0] + u * u * p[0],
                        (1 - u) ** 2 * home[1] + 2 * u * (1 - u) * c[1] + u * u * p[1]) for u in (0, .2, .4, .6, .8, 1)]
                rope(g, pts)
        if 1 <= f <= 6:
            droplets(g, pun, f - 1, 3 + n)
        wing = POP_WING[f] if (n == 2 or f < 6) else POP_PANIC[f - 6]
        body(g, poses, ex, f, wing, lens[f], splat=spl[f], gumbit=(n == 1 and f >= 5))
        frs.append(g)
    return frs


# respawn: blow (the ball is wide, eyes pressed), breathe in (the ball is tall), blow again. Every step is one pose.
INFL_POSE = ['S1', 'S1', 'R', 'T1', 'R', 'S1', 'S', 'S1', 'R', 'T1', 'R', 'S1', 'R', 'R']
INFL_WING = [6, 6, 6, 1, 6, 6, 5, 6, 6, 1, 6, 6, 6, 1]


def bud(b0, s):
    """the second lobe swells out of the flank of the first bubble (it does not start as a small ball at the lips,
    which read as a bow next to the neck)"""
    cx, cy, rx, ry = D.REST_TWO[1]
    t = min(1.0, s) ** 0.8
    return (D.lerp(b0[0] + 0.62 * b0[2], cx, t), D.lerp(b0[1] + 0.05 * b0[3], cy, t), rx * s, ry * s)


def anim_inflate():
    """14 frames, respawn: two breaths per lobe, the radius overshoots and rings, the first lobe makes room."""
    N = 14
    s0 = [0.14, 0.32, 0.50, 0.46, 0.74, 1.00, 1.08, 0.97, 1.01, 1.0, 1.0, 1.0, 1.0, 1.0]
    s1 = [0, 0, 0, 0, 0, 0, 0.34, 0.50, 0.66, 0.62, 0.84, 1.05, 0.97, 1.0]
    q0 = [0.0] * 5 + D.ring(1.0, 0.34, 0.12, 0.0, N - 5)
    q1 = [0.0] * 11 + [0.10, -0.05, 0.0]
    q0[-1] = 0.0
    ex = follow(INFL_POSE, False)
    frs = []
    for f in range(N):
        g = D.grid()
        b0, b1 = D.layout(T, s0[f], s1[f])
        b0 = D.wob(b0, q0[f])
        if b1:
            b1 = D.wob(bud(b0, s1[f]), q1[f])
        D.draw_bubbles(g, T, b0, b1)
        body(g, INFL_POSE, ex, f, INFL_WING[f], 'squint' if INFL_POSE[f] in ('S', 'S1') else 'open')
        frs.append(g)
    return frs


# fall: the ball holds the long pose (no body step at all); the motion is spread over every frame instead:
# a wave runs up each tuft (left and right out of phase), the wing flutters high, the feet kick in turn.
FALL_TUFT = ['TA', 'TB', 'TL', 'TL', 'TA']
FALL_FOOT = ['TOE', 'TUCK', 'TOE', 'REST', 'TOE']
FALL_WING = [0, 7, 0, 1, 0, 7, 0, 7, 0, 1]


def anim_fall():
    """10 frames, loop, no bubble: body long, wing streaming up, fur tufts streaming, feet kicking in turn, a torn gum
    rope whips above the lips (travelling wave, amplitude grows toward the free end)."""
    N = 10
    m = (26.6, 38.5)
    frs = []
    for f in range(N):
        g = D.grid()
        ph = math.tau * f / N
        pts = []
        for i in range(8):
            amp = 0.3 + 0.27 * i
            x = m[0] + 0.4 - 0.30 * i + amp * math.sin(i * 0.85 - ph)
            pts.append((min(W - 4, max(3, x)), m[1] - 1.0 - i * 2.0))
        rope(g, pts)
        draw_body(g, 'T', FALL_WING[f], 'wide', EYE_DY['T'], FALL_TUFT[f % 5], FALL_TUFT[(f + 3) % 5],
                  FALL_FOOT[f % 5], FALL_FOOT[(f + 2) % 5])
        frs.append(g)
    return frs


def idle():
    g = D.grid()
    draw_body(g, 'R', 6, 'open', gumbit=True)
    return g


# (name, loop, ticks per frame at 60 Hz)
ANIMS = [
    ('flap2', True, [4] * 8),
    ('flap1', True, [4] * 8),
    ('pop2', False, [3, 3, 3, 4, 4, 5, 5, 5, 5, 6, 6, 6]),
    ('pop1', False, [3, 3, 3, 4, 4, 5, 5, 5, 6, 6]),
    ('inflate', False, [5] * 14),
    ('fall', True, [4] * 10),
    ('idle', True, [60]),
]
LABEL = dict(flap2='flap, two lobes', flap1='flap, one lobe', pop2='first pop, pull-round into one bubble',
             pop1='last pop', inflate='respawn blow-up', fall='fall', idle='no gum, standing (single frame)')

# hand corrections after the frame-by-frame check: (animation, frame) -> [(x, y, key)]; '.' erases
FIX = {}


def build():
    del BODY_LAYERS[:]
    A = dict(flap2=anim_flap(2), flap1=anim_flap(1), pop2=anim_pop(2, 12), pop1=anim_pop(1, 10),
             inflate=anim_inflate(), fall=anim_fall(), idle=[idle()])
    for (name, f), edits in FIX.items():
        for x, y, k in edits:
            A[name][f][y][x] = k
    for name, _, ticks in ANIMS:
        assert len(A[name]) == len(ticks), name
    return A


# ================================================================ motion check (body layer only: fur, eyes, wing, feet)
# numbers of the version the verdict was about, measured the same way on the old generator before this pass:
# animation -> (largest silhouette change, frame pair, largest recolour count, whole-body displacements over 1 px)
BEFORE = dict(flap2=(90, '6>7', 300, '6>7 by 2 px'), flap1=(90, '6>7', 300, '6>7 by 2 px'), pop2=(56, '4>5', 266, 'none'),
              pop1=(60, '4>5', 270, 'none'), inflate=(34, '1>2', 191, 'none'), fall=(24, '2>3', 64, 'none'))
BEFORE_PAIRS = dict(
    flap2='0>1 1, 1>2 32, 2>3 31, 3>4 40, 4>5 35, 5>6 33, 6>7 90, 7>0 2',
    flap1='0>1 1, 1>2 32, 2>3 31, 3>4 40, 4>5 35, 5>6 33, 6>7 90, 7>0 2',
    pop2='0>1 30, 1>2 0, 2>3 33, 3>4 30, 4>5 56, 5>6 34, 6>7 2, 7>8 3, 8>9 3, 9>10 2, 10>11 1',
    pop1='0>1 30, 1>2 0, 2>3 33, 3>4 30, 4>5 60, 5>6 36, 6>7 2, 7>8 2, 8>9 2',
    inflate='0>1 1, 1>2 34, 2>3 0, 3>4 33, 4>5 1, 5>6 0, 6>7 0, 7>8 1, 8>9 33, 9>10 34, 10>11 0, 11>12 34, 12>13 1',
    fall='0>1 2, 1>2 0, 2>3 24, 3>4 0, 4>5 24, 5>6 2, 6>7 0, 7>8 24, 8>9 0, 9>0 24')


def motion():
    """per animation: [(pair, silhouette pixels changed, pixels recoloured, best whole-body shift or None)]"""
    out, i = {}, 0
    for name, loop, ticks in ANIMS:
        L = BODY_LAYERS[i:i + len(ticks)]
        i += len(ticks)
        if name == 'idle':
            continue
        rows = []
        n = len(L)
        for f in range(n if loop else n - 1):
            a, b = L[f], L[(f + 1) % n]
            sil = sum((a[y][x] == '.') != (b[y][x] == '.') for y in range(H) for x in range(W))
            chg = sum(a[y][x] != b[y][x] for y in range(H) for x in range(W))
            ma = {(x, y) for y in range(45) for x in range(W) if a[y][x] != '.'}
            mb = {(x, y) for y in range(45) for x in range(W) if b[y][x] != '.'}
            best, bx = (0, 0), len(ma ^ mb)
            zero = bx
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    c = len({(x + dx, y + dy) for x, y in ma} ^ mb)
                    if c < bx:
                        best, bx = (dx, dy), c
            shift = best if (best != (0, 0) and bx <= 0.5 * zero) else None
            rows.append(('%d>%d' % (f, (f + 1) % n), sil, chg, shift))
        out[name] = rows
    return out


# ================================================================ output
COLS = 8


def all_frames(A):
    return [g for name, _, _ in ANIMS for g in A[name]]


def sheet_indexed(frames, pal):
    rows = (len(frames) + COLS - 1) // COLS
    im = Image.new('P', (COLS * W, rows * H), 0)
    flat = list(D.MAG)
    for k in KEYS:
        flat += list(pal[k])
    im.putpalette(flat + [0] * (768 - len(flat)))
    px = im.load()
    for n, g in enumerate(frames):
        ox, oy = (n % COLS) * W, (n // COLS) * H
        for y in range(H):
            for x in range(W):
                if g[y][x] != '.':
                    px[ox + x, oy + y] = 1 + KEYS.index(g[y][x])
    return im


def contact(frs, pal, k=4, wrap=8):
    rows = (len(frs) + wrap - 1) // wrap
    im = Image.new('RGB', (min(len(frs), wrap) * (W + 1) + 1, rows * (H + 1) + 1), (22, 24, 30))
    d = ImageDraw.Draw(im)
    for n, g in enumerate(frs):
        ox, oy = 1 + (n % wrap) * (W + 1), 1 + (n // wrap) * (H + 1)
        d.rectangle([ox, oy, ox + W - 1, oy + H - 1], fill=(52, 58, 76))
        s = D.render(g, pal)
        im.paste(s, (ox, oy), s)
    return D.up(im, k)


def load_bgs():
    return {m: Image.open(os.path.join(BGDIR, 'scene_%s_1x.png' % m)).convert('RGB') for m in ('dusk', 'moon', 'storm')}


# (animation, frame, palette, centre x, feet y, flip): 8 fliers
D.CAST = [('flap2', 7, 'player', 50, 116, False),
          ('flap2', 4, 'cpu', 160, 56, True),
          ('flap1', 1, 'player', 250, 86, False),
          ('pop2', 3, 'cpu', 96, 176, False),
          ('inflate', 5, 'player', 158, 120, False),
          ('flap2', 2, 'cpu', 262, 150, True),
          ('pop1', 3, 'player', 204, 190, False),
          ('fall', 1, 'cpu', 300, 200, True)]


def ring_stats(frames):
    """pixels that touch transparency (edge) and pixels right inside a keyline edge pixel (inner line), by key"""
    edge, inner = {}, {}
    for g in frames:
        e = set()
        for y in range(H):
            for x in range(W):
                if g[y][x] == '.':
                    continue
                if any(not (0 <= x + a < W and 0 <= y + b < H) or g[y + b][x + a] == '.' for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    e.add((x, y))
                    edge[g[y][x]] = edge.get(g[y][x], 0) + 1
        for y in range(H):
            for x in range(W):
                if g[y][x] in '.o' or (x, y) in e:
                    continue
                if any((x + a, y + b) in e and g[y + b][x + a] == 'o' for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    inner[g[y][x]] = inner.get(g[y][x], 0) + 1
    return edge, inner


WEAK = [
    'The body has five hand-drawn poses. A step between two poses still moves 40 to 58 silhouette pixels; it is now '
    'the same size on every frame, but at 32 x 48 it is not sub-pixel smooth.',
    'Flap is still 8 frames (4 ticks each). A slower, softer beat needs more frames, and the sheet has no free slot.',
    'Fall holds one body pose; only the tufts, the wing and the feet move. It can read as stiff.',
    'Fur ticks are placed by scaling the rest-pose ticks into each pose, then cleaned by rule; they are not redrawn per pose.',
    'The bubble outline and bands are still produced by rules (smooth union of ellipses, bands by distance from the '
    'hot spot) and then cleaned by a single-pixel rule. They are checker-free and stable, but not drawn pixel by pixel.',
    'Pop frame 1 (first pop): the survivor now keeps a round outline, but the torn lobe next to it is still a ragged rule-made shape.',
    'Respawn: frames 0 and 1 show the same body. The second lobe now grows out of the flank of the first; the pair reads as one lumpy bubble until frame 10.',
    'The GIFs were not judged in motion by a person in this pass; only contact sheets and numbers were checked.',
    'Tile cost is high: almost every frame has its own tiles (see numbers).',
    'The dark keyline (luminance 10) cannot stand out against the darkest sky patches; there the colour right inside '
    'the keyline carries the edge (smallest step in numbers).',
    'The blue player body is close in hue to the moon-mood buildings; the pale rim and eyes carry it there.',
]

CHOPPY = [
    ('flap, both versions', 'Frames 1>2, 2>3, 4>5, 5>6 and 6>7: one row in the lower body was doubled or deleted, so everything '
     'above that row jumped 1 px while the belly and feet stood still (the cut through the body). Frames 4 to 6 also '
     'lifted the whole sprite 1 px; together that gave a 2 px drop of the head at 6>7. Frames 0>1 and 7>0 did not move '
     'at all. The wing jumped 60 degrees at 3>4.',
     'Five hand-drawn body poses (squash, in-between, rest, in-between, stretch), one pose step on every frame, bottom '
     'edge fixed. No whole-sprite lift. Eight hand-drawn wing poses. Eyes, tufts and feet follow one or two frames late.'),
    ('first pop and last pop', 'Frames 0>1, 2>3, 3>4, 4>5, 5>6: the same row trick; frames 6 onward frozen.',
     'Flinch, recoil and settle through the hand poses; the wing and eyelids move on the frames between.'),
    ('respawn blow-up', 'Frames 1>2, 3>4, 8>9, 9>10, 11>12: the puff toggled one row on and off; the frames between were frozen.',
     'Blow (wide pose) and breathe in (tall pose) through the hand poses, one step per frame.'),
    ('fall', 'Frames 2>3, 4>5, 7>8, 9>0: tuft and feet switched between two states; the frames between were frozen.',
     'Body holds the long pose. A wave runs up each tuft, the wing flutters, the feet kick in turn; something moves on every frame.'),
]


def main():
    out = []
    A = build()
    frames = all_frames(A)
    assert len(frames) == 63, len(frames)
    bgs = load_bgs()
    # ---- sheets
    sheet_indexed(frames, PAL_P).save(os.path.join(HERE, 'sootling_final_sheet_1x.png'))
    sheet_indexed(frames, PAL_C).save(os.path.join(HERE, 'sootling_final_sheet_cpu_1x.png'))
    big = Image.new('RGB', (COLS * W, 16 * H), D.MAG)
    for r, pal in enumerate((PAL_P, PAL_C)):
        big.paste(sheet_indexed(frames, pal).convert('RGB'), (0, r * 8 * H))
    D.view(big, COLS, 16, 3).save(os.path.join(HERE, 'sheet_both_3x.png'))
    for name, _, _ in ANIMS:
        if name != 'idle':
            contact(A[name], PAL_P).save(os.path.join(HERE, 'contact_%s_4x.png' % name))
    # ---- frames.json
    first, anims = 0, []
    for name, loop, ticks in ANIMS:
        anims.append(dict(name=name, label=LABEL[name], first=first, count=len(ticks), ticks=ticks, loop=loop))
        first += len(ticks)
    js = dict(sheet='sootling_final_sheet_1x.png', frame_w=W, frame_h=H, sheet_cols=COLS, sheet_rows=8,
              grid_order='row-major: frame n sits at column n % 8, row n // 8; slot 63 is empty',
              transparent=[255, 0, 255], feet_row=47, hit_box_columns=[14, 17], tick_hz=60,
              palette_index_keys=dict((str(i + 1), k) for i, k in enumerate(KEYS)),
              palette_player=[list(PAL_P[k]) for k in KEYS], palette_cpu=[list(PAL_C[k]) for k in KEYS],
              palette_note='index 0 = transparent; lists hold indices 1..15; every channel is a 5-bit value '
                           'expanded to 8 bits ((v5 << 3) | (v5 >> 2))',
              animations=anims)
    with open(os.path.join(HERE, 'frames.json'), 'w') as fh:
        json.dump(js, fh, indent=1)
    # ---- scenes and GIFs
    for mood, bg in bgs.items():
        D.up(D.scene(bg, A), 2).save(os.path.join(HERE, 'scene_%s_2x.png' % mood))
    if '--nogif' not in sys.argv:
        for name, _, ticks in ANIMS:
            if name != 'idle':
                D.gif_panels(os.path.join(HERE, 'anim_%s_4x.gif' % name), A[name], [round(t * 100 / 60) * 10 for t in ticks], bgs)
    # ---- numbers
    out.append('Sootling final, 32 x 48: numbers (script output)')
    out.append('frames: 63 = ' + ', '.join('%s %d' % (a['name'], a['count']) for a in anims) +
               '; sheet grid 8 columns x 8 rows, row-major, slot 63 empty')
    out.append('frame box 32 x 48, feet row 47, hit box columns 14..17')
    out.append('palette index order 1..15: ' + ' '.join(KEYS) + '   (0 = transparent, magenta 255,0,255 in the sheet)')
    for pn, pal in PALS.items():
        for k in KEYS:
            assert all(v == D.snap5(v) for v in pal[k]), (pn, k)
        assert len(set(pal.values())) == 15, pn
        out.append('palette %-6s RGB: %s' % (pn, ' '.join('%d=(%d,%d,%d)' % (i + 1, *pal[k]) for i, k in enumerate(KEYS))))
        out.append('palette %-6s luminance: %s' % (pn, ' '.join('%s=%d' % (k, round(lum(pal[k]))) for k in KEYS)))
    diff = [i + 1 for i, k in enumerate(KEYS) if PAL_P[k] != PAL_C[k]]
    out.append('palette swap player (pink gum) -> computer (lime gum): same tiles; indices that change colour: %s; '
               'keyline 1, soot fur 2..5, rim and eye white 6, ember 7..9, gum 10..14 (10 = deep line), 15 white unchanged'
               % ' '.join(map(str, diff)))
    used = D.keys_used(frames)
    out.append('colours used: %d of 15 (unused: %s)' % (len(used), ' '.join(k for k in KEYS if k not in used) or 'none'))
    raw, uq, uqf = D.tiles_unique(frames)
    out.append('16 x 16 tiles over the 63 frames: %d non-empty of %d, %d unique without flips, %d unique with flips' % (raw, 63 * 6, uq, uqf))
    n, steps = D.dither_count(frames)
    gum = {p: c for p, c in steps.items() if set(p) & set('ABCDEw')}
    fur = {p: c for p, c in steps.items() if not set(p) & set('ABCDEw')}

    def stp(p):
        return min(abs(lum(pal[p[0]]) - lum(pal[p[1]])) for pal in PALS.values())
    out.append('checker pixels on gum (colours 10..15): %d %s' % (sum(gum.values()), gum or ''))
    out.append('checker pixels on fur and eyes: %d; pairs (count, smaller luminance step of the two palettes): %s' %
               (sum(fur.values()), ', '.join('%s/%s %d step %d' % (p[0], p[1], c, stp(p)) for p, c in sorted(fur.items())) or 'none'))
    furpairs = [(a, b) for a, b in (('1', '2'), ('2', '3'), ('3', '4'), ('4', 'r'))]
    out.append('fur ramp neighbour steps (fur ticks and dither use these pairs), smaller of the two palettes: ' +
               ', '.join('%s/%s %d' % (a, b, stp((a, b))) for a, b in furpairs[:3]) + ' (rule: at least 28)')
    out.append('droplets cut by the frame box: %d; frames where the membrane touches columns 0, 31 or row 0: %d' %
               (D.STATS['clipped'], D.STATS['edge']))
    g0 = D.grid()
    stamp(g0, POSES['R'][0], 45 - (len(POSES['R'][1]) - 1), POSES['R'][1])
    xs = [x for y in range(H) for x in range(W) if g0[y][x] != '.']
    ys = [y for y in range(H) for x in range(W) if g0[y][x] != '.']
    out.append('body size: fur ball %d x %d px (columns %d..%d, rows %d..%d), with feet %d x %d (rows to 47); draft was about 20 x 17'
               % (max(xs) - min(xs) + 1, max(ys) - min(ys) + 1, min(xs), max(xs), min(ys), max(ys), max(xs) - min(xs) + 1, 47 - min(ys) + 1))
    tops = [min(y for y in range(H) for x in range(W) if g[y][x] != '.') for g in frames]
    lefts = [min(x for y in range(H) for x in range(W) if g[y][x] != '.') for g in frames]
    rights = [max(x for y in range(H) for x in range(W) if g[y][x] != '.') for g in frames]
    out.append('art extent over all frames: top row %d, columns %d..%d (box is rows 0..47, columns 0..31)' % (min(tops), min(lefts), max(rights)))
    edge, inner = ring_stats(frames)
    te = sum(edge.values())
    out.append('silhouette edge pixels by colour: ' + ', '.join('%s %.1f%%' % (k, 100.0 * c / te) for k, c in sorted(edge.items(), key=lambda kv: -kv[1])))
    ti = sum(inner.values())
    out.append('inner line (pixels right inside the keyline) by colour: ' + ', '.join('%s %.1f%%' % (k, 100.0 * c / ti) for k, c in sorted(inner.items(), key=lambda kv: -kv[1])))
    for pn, pal in PALS.items():
        lo = min(inner, key=lambda k: lum(pal[k]))
        out.append('  %s: darkest inner-line colour %s luminance %d; keyline luminance %d' % (pn, lo, round(lum(pal[lo])), round(lum(pal['o']))))
    for m, im in bgs.items():
        ls = sorted(lum(p) for p in im.crop((0, 16, 320, 176)).get_flattened_data())
        p5, md, p95 = ls[len(ls) // 20], ls[len(ls) // 2], ls[len(ls) * 19 // 20]
        out.append('mood %s: sky luminance p5 / median / p95 = %d / %d / %d (darkest %d)' % (m, p5, md, p95, ls[0]))
        for pn, pal in PALS.items():
            lo = min(lum(pal[k]) for k in inner)
            ko = lum(pal['o'])
            parts = []
            for nm in ('flap2', 'flap1', 'fall'):
                mean, p10, u24 = D.outline_contrast(im, A[nm][0], pal, range(16, 128, 14), gum_rows=H)
                parts.append('%s mean %d p10 %d under24 %d%%' % (nm, mean, p10, u24))
            out.append('  %s outline luminance step: keyline against median %d, against p5 %d, against darkest %d; '
                       'darkest inner line against p5 %d, against darkest %d; measured edge pixel against backdrop pixel: %s'
                       % (pn, abs(ko - md), abs(ko - p5), abs(ko - ls[0]), abs(lo - p5), abs(lo - ls[0]), '; '.join(parts)))
    out.append('motion of the body layer (fur, eyes, wing, feet; gum excluded), silhouette pixels changed per frame pair:')
    for name, rows in motion().items():
        big = max(rows, key=lambda r: r[1])
        small = min(r[1] for r in rows)
        sh = ', '.join('%s by (%d,%d)' % (r[0], *r[3]) for r in rows if r[3] and max(abs(r[3][0]), abs(r[3][1])) > 1) or 'none'
        b = BEFORE[name]
        out.append('  %-8s before: largest %d at %s, recolour max %d, whole-body displacement over 1 px: %s' % (name, b[0], b[1], b[2], b[3]))
        out.append('  %-8s after:  largest %d at %s, smallest %d, recolour max %d, whole-body displacement over 1 px: %s'
                   % ('', big[1], big[0], small, max(r[2] for r in rows), sh))
        out.append('  %-8s before pairs: %s' % ('', BEFORE_PAIRS[name]))
        out.append('  %-8s after pairs:  %s' % ('', ', '.join('%s %d' % (r[0], r[1]) for r in rows)))
    out.append('body poses (area in pixels): ' + ', '.join('%s %d x %d = %d' % (n, len(POSES[n][1][0]), len(POSES[n][1]), POSE_AREA[n]) for n in POSE_ORDER))
    with open(os.path.join(HERE, 'numbers.txt'), 'w') as fh:
        fh.write('\n'.join(out) + '\n')
    print('\n'.join(out))
    write_html(anims)


def write_html(anims):
    h = ['<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Sootling final</title><style>',
         'body{background:#14161c;color:#d8dce6;font:15px/1.5 system-ui,sans-serif;margin:24px;max-width:1400px}',
         'h1,h2{color:#fff;font-weight:600}h2{margin-top:36px;border-bottom:1px solid #333a48;padding-bottom:4px}',
         'img{image-rendering:pixelated;image-rendering:crisp-edges;display:block;margin:8px 0;max-width:none}',
         'table{border-collapse:collapse}td,th{border:1px solid #333a48;padding:4px 10px;text-align:left}',
         '.row{display:flex;flex-wrap:wrap;gap:16px}pre{background:#1c1f28;padding:12px;overflow:auto;white-space:pre-wrap}',
         '</style></head><body>',
         '<h1>Sootling final: animation fix pass</h1>',
         '<p>Drafts folder, art only. 63 frames, 32 x 48 px, one palette of 15 colours plus transparent. '
         'Player pink and computer lime are the same tiles with a palette swap. View at 100 percent zoom.</p>',
         '<h2>Body animations: what was choppy and what changed</h2>',
         '<p>The verdict was that the animations cut in the middle of the body look choppy. The cause was not a tile '
         'seam. The old body was one map, and squash and stretch were made by doubling or deleting one row low in the '
         'body. Each GIF shows 4x: player on dusk, computer on storm, player on moon, computer on dusk.</p>',
         '<table><tr><th>Animation</th><th>What was choppy</th><th>What changed</th></tr>']
    for c in CHOPPY:
        h.append('<tr><td>%s</td><td>%s</td><td>%s</td></tr>' % c)
    h.append('</table>')
    for a in anims:
        if a['name'] != 'idle':
            h.append('<h3>%s</h3><img src="anim_%s_4x.gif" alt="%s"><img src="contact_%s_4x.png" alt="%s frames">' %
                     (a['label'], a['name'], a['name'], a['name'], a['name']))
    h += ['<h2>Known weak points</h2><ul>'] + ['<li>%s</li>' % w for w in WEAK] + ['</ul>',
         '<h2>Sheet, player rows then computer rows (3x)</h2>',
         '<p>Grid order of <code>sootling_final_sheet_1x.png</code>: 8 columns, row-major. Slot 63 is empty. '
         'Frame counts per animation are unchanged.</p>',
         '<table><tr><th>Animation</th><th>First frame</th><th>Frames</th><th>Ticks per frame (60 Hz)</th><th>Loop</th></tr>']
    for a in anims:
        h.append('<tr><td>%s (%s)</td><td>%d</td><td>%d</td><td>%s</td><td>%s</td></tr>' %
                 (a['name'], a['label'], a['first'], a['count'], ' '.join(map(str, a['ticks'])), 'yes' if a['loop'] else 'no'))
    h.append('</table><img src="sheet_both_3x.png" alt="sheet">')
    h.append('<h2>Scenes with 8 fliers (2x)</h2>')
    for m in ('dusk', 'moon', 'storm'):
        h.append('<h3>%s</h3><img src="scene_%s_2x.png" alt="%s">' % (m, m, m))
    h.append('<h2>Numbers</h2><pre>%s</pre>' % open(os.path.join(HERE, 'numbers.txt')).read().replace('<', '&lt;'))
    h.append('</body></html>')
    with open(os.path.join(HERE, 'index.html'), 'w') as fh:
        fh.write('\n'.join(h))


if __name__ == '__main__':
    main()
