#!/usr/bin/env python3
"""Leaking gum bubble drafts (2026-11-17). DRAFT ONLY, nothing here is imported by the game.

The leak is ONE extra 16 x 16 sprite (1 tile per frame) drawn over the unchanged in-game bubble cell
(assets/gum/gum_sheet.png), in the bubble's own palette. Every shape is a hand-typed pixel stamp (tear, patch,
puffs). The only computed thing is WHERE each puff stamp sits per frame: spurt velocity, drag, rise, age picks the
stamp (fresh -> round -> hollow -> specks). Emit lists (frame, angle, speed, kind) are typed by hand.
Bird + healthy bubble come from ../2026-11-16-gum-mouth-v4/draw_gum_mouth_v4.py (frame), helpers from v1.
Stamp letters = gum palette entries 1..c (1 outline, 2 4 dark purple, 3 maroon rim, 5..9 pink ramp, a pale pink,
b white, c blue rim light).
Run: python3.14 -I draw_gum_leak.py
"""
import math, os, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "../2026-11-16-gum-mouth-v4"))
import draw_gum_mouth_v4 as v4
v1 = v4.v1
GCH = "123456789abc"
SHOWN = v1.GD["tables"]["level_shown_w"]          # index 0 = level 16
TICK = 3                                          # game frames per leak frame (20 fps)
NOZ = (7.0, 10.5)                                 # nozzle in the 16 x 16 leak tile
DRAG, RISE = 0.62, 0.22                           # per leak frame: velocity keeps 62 %, puffs gain 0.22 px/frame upward


def g(text): return [r.strip() for r in text.strip().split("\n")]


# ---- hand-typed stamps. Tear / patch stamps sit at tile (0, 8); the bubble rim runs diagonally through them.
TEAR_1 = g("""
......1..
.....191.
...b.181.
..b1122..
...421...
....4....
""")
TEAR_2 = g("""
.........
......11.
...b.1891
..b11221.
...421...
....4....
""")
PATCH_SHUT = g("""
.........
.1111....
.1aa91...
.1a9961..
.199661..
.196661..
..1111...
""")
PATCH_HALF = g("""
......1..
.11111a1.
.1aa912..
.1a9961..
.199661..
.196661..
..1111...
""")
PATCH_LIFT = g("""
.....11..
.1111ba1.
.1aa912..
.1a9961..
.199661..
.196661..
..1111...
""")
J0 = g("""
.b
b.
""")
J1 = g("""
..b
.b.
c..
""")
P1 = g("""
.bb
bbc
.c.
""")
P2 = g("""
.bb.
bbbc
babc
.cc.
""")
P3 = g("""
.bb..
b.abc
ba..c
.b.c.
..c..
""")
P4 = g("""
.b.b.
b...c
.....
b...c
.c.c.
""")
P5 = g("""
b..
...
..c
""")
P6 = g("""
c
""")
S1 = g("""
bb
bc
""")
S2 = g("""
b.
.c
""")
BIG = [J1, P1, P2, P3, P4, P5, P6]
SMALL = [J0, S1, S2, P5, P6]
HISS = [J0, P6]

# ---- variants: frames, patch stamp per frame, emits (frame, angle deg above horizontal, speed px/frame, kind)
VAR = {
    "A": dict(title="A: side tear, steady puffs", n=8,
              patch=lambda f: TEAR_1 if f % 4 < 2 else TEAR_2,
              emits=[(0, 52, 2.8, BIG), (2, 40, 2.3, SMALL), (4, 61, 2.9, BIG), (6, 46, 2.5, SMALL)]),
    "B": dict(title="B: gum patch, bursts", n=16,
              patch=lambda f: PATCH_LIFT if f in (0, 1, 2, 3, 9, 10) else PATCH_HALF if f in (4, 11) else PATCH_SHUT,
              emits=[(0, 50, 3.1, BIG), (1, 38, 2.7, BIG), (2, 63, 2.6, SMALL), (3, 46, 2.1, SMALL),
                     (9, 57, 2.6, BIG), (10, 42, 2.2, SMALL)]),
    "C": dict(title="C: half-peeled patch, thin hiss + sputter", n=12,
              patch=lambda f: PATCH_LIFT if f in (0, 1, 9, 10) else PATCH_HALF,
              emits=[(0, 55, 3.0, BIG), (3, 44, 2.3, SMALL), (6, 65, 2.5, SMALL), (9, 48, 2.8, BIG)]
                    + [(f, [50, 58, 44, 54][f % 4], 2.0, HISS) for f in range(12)]),
}


def stamp(tile, st, x, y):
    for j, r in enumerate(st):
        for i, c in enumerate(r):
            if c == ".": continue
            assert 0 <= x + i < 16 and 0 <= y + j < 16, ("stamp leaves the 16 x 16 tile", x + i, y + j)
            tile[y + j][x + i] = c


def puff_xy(angle, speed, age):
    a = math.radians(angle); vx, vy = speed * math.cos(a), -speed * math.sin(a)
    x, y = NOZ[0] + vx / 2, NOZ[1] + vy / 2
    for _ in range(age):
        x += vx; y += vy; vx *= DRAG; vy = vy * DRAG - RISE
    return x, y


def tile(var, f):
    """One 16 x 16 leak tile as rows of palette letters."""
    v, t = VAR[var], [["."] * 16 for _ in range(16)]
    stamp(t, v["patch"](f), 0, 8)
    live = [((f - e[0]) % v["n"], e) for e in v["emits"]]
    for age, (_, ang, spd, kind) in sorted((l for l in live if l[0] < len(l[1][3])), key=lambda l: -l[0]):   # oldest first
        st = kind[age]; x, y = puff_xy(ang, spd, age)
        stamp(t, st, round(x - len(st[0]) / 2), round(y - len(st) / 2))
    return tuple("".join(r) for r in t)


def paint(grid):
    im = Image.new("RGBA", (len(grid[0]), len(grid)), (0, 0, 0, 0))
    for y, r in enumerate(grid):
        for x, c in enumerate(r):
            if c != ".": im.putpixel((x, y), v1.GUMPAL[GCH.index(c)] + (255,))
    return im


PAD = 12


def leak_bubble(level, wob, grid, pal="p1"):
    """In-game bubble cell + the leak tile on its upper right rim. Returns the picture; the bubble sits at (0, PAD)."""
    b = v1.bubble(level, wob, "p1"); s = SHOWN[16 - level]; k = round(0.7 * s / 2)
    out = Image.new("RGBA", (b.width + 16, b.height + PAD), (0, 0, 0, 0))
    out.alpha_composite(b, (0, PAD))
    out.alpha_composite(paint(grid), (b.width // 2 + k - 6, PAD + s // 2 - k - 11))
    if pal != "p1":   # shortcut: same mock-up recolour as v1.bubble (copied map, it is not exposed there); in game the gum palette is shared
        P = v1.PAL[pal]
        m = dict(zip(v1.GUMPAL, [P[0], P[9], P[9], P[9], P[10], P[10], P[11], P[11], P[12], P[13], P[14], P[3]]))
        out.putdata([(m.get(p[:3], p[:3]) + (255,)) if p[3] else p for p in out.get_flattened_data()])
    return out, b.width


def frame(var, i, pal="p1", level=None, name=None):
    """Bird + leaking bubble at leak frame i (bird breath as v4 a_idle, one bird frame per 2 leak frames)."""
    j = i // 2
    name = name or v4.BL[j % 6]; level = level or 10 + v4.LV[j % 6]
    out = Image.new("RGBA", (v4.W, v4.H), (0, 0, 0, 0))
    lb, bw = leak_bubble(level, i, tile(var, i % VAR[var]["n"]), pal)     # wobble at double speed = the extra wobble
    out.alpha_composite(lb, (v4.CX + v4.GX - bw // 2, v4.CY + v4.GRIP[1] + 2 - lb.height))
    out.alpha_composite(v4.frame(v4.T, name, 0, 0, pal))
    return out


def healthy(i, pal="p1"):
    j = i // 2
    return v4.frame(v4.T, v4.BL[j % 6], 10 + v4.LV[j % 6], j, pal)


def row(ims):
    s = Image.new("RGBA", (sum(im.width for im in ims), max(im.height for im in ims)), (0, 0, 0, 0)); x = 0
    for im in ims: s.alpha_composite(im, (x, 0)); x += im.width
    return s


def col(ims):
    s = Image.new("RGBA", (max(im.width for im in ims), sum(im.height for im in ims)), (0, 0, 0, 0)); y = 0
    for im in ims: s.alpha_composite(im, (0, y)); y += im.height
    return s


def main():
    out = lambda n: os.path.join(HERE, n)
    num, cards = [], []
    # the level 10 bubble cell is 32 x 32 with the bubble at x 7..24, y 11..31: the leak tile lands on x 16..31, y 3..18
    b = v1.GIM.crop((0, 243, 32, 275)).getbbox(); s = SHOWN[6]; k = round(0.7 * s / 2)
    ox, oy = b[0] + (b[2] - b[0]) // 2 + k - 6, b[1] + s // 2 - k - 11
    assert 0 <= ox and ox + 16 <= 32 and 0 <= oy and oy + 16 <= 32, (ox, oy)
    for var, v in VAR.items():
        n = v["n"]; grids = [tile(var, f) for f in range(n)]
        uniq = len(set(grids)); used = sorted({c for gr in grids for r in gr for c in r} - {"."})
        assert set(used) <= set(GCH)
        def cell(f):
            c = Image.new("RGBA", (40, 36), (0, 0, 0, 0)); c.alpha_composite(leak_bubble(10, f, grids[f])[0], (2, 2)); return c
        sh = row([cell(f) for f in range(n)])
        v1.on_bg(sh, 1).save(out("%s_frames_1x.png" % var)); v1.on_bg(sh, 4).save(out("%s_frames_4x.png" % var))
        tl = row([paint(gr) for gr in grids])
        v1.on_bg(tl, 1).save(out("%s_tiles_1x.png" % var)); v1.on_bg(tl, 6).save(out("%s_tiles_6x.png" % var))
        for pal in ("p1", "p2", "cpu"):
            ims = [v1.on_bg(row([healthy(i, pal), frame(var, i, pal)]), 4) for i in range(48)]
            ims[0].save(out("%s_%s_4x.gif" % (var, pal)), save_all=True, append_images=ims[1:], duration=TICK * 1000 // 60, loop=0, disposal=1)
        num.append("%s  %-42s frames %2d  tick %d game frames  loop %.2f s  tile 16x16 = 1 per frame  unique tiles %2d  extra sprites 1  gum palette entries used: %s"
                   % (var, v["title"], n, TICK, n * TICK / 60, uniq, " ".join(used)))
        cards.append((var, v["title"], n, uniq, " ".join(used)))
    # in-game compare: healthy, A, B, C for the three palettes (leak frame 3: puffs well out), and other bubble sizes
    v1.on_bg(col([row([v4.frame(v4.T, "rest", 10, 0, p)] + [frame(x, 3, p, 10, "rest") for x in VAR]) for p in ("p1", "p2", "cpu")]), 6).save(out("compare_ingame_6x.png"))
    v1.on_bg(col([row([frame(x, 3, "p1", lv, "rest") for lv in (5, 7, 10, 12, 16)]) for x in VAR]), 4).save(out("compare_sizes_4x.png"))
    head = ("Leak overlay tile lands on x %d..%d, y %d..%d of the 32 x 32 level 10 bubble cell (inside the box).\n"
            "Baked alternative (leak drawn into the bubble frames): 16 levels x 6 wobble x leak frames x up to 4 tiles: not drawn.\n" % (ox, ox + 15, oy, oy + 15))
    open(out("numbers.txt"), "w").write(head + "\n".join(num) + "\n")
    print(head + "\n".join(num))
    h = ["<!doctype html><meta charset=utf-8><title>Gumbirds: leaking gum bubble drafts</title>",
         "<style>body{background:#1b2030;color:#e6e9f2;font:15px/1.5 system-ui,sans-serif;margin:24px;max-width:1500px}"
         "img{image-rendering:pixelated;display:block;margin:6px 0 14px;border:1px solid #3a4260;max-width:100%}"
         "h1{font-size:24px}h2{font-size:19px;border-top:2px solid #ff52b5;padding-top:14px;margin-top:34px}"
         ".r{display:flex;gap:18px;flex-wrap:wrap}.r div{flex:0 0 auto}b{color:#ffa5de}</style>",
         "<h1>Leaking gum bubble: drafts (2026-11-17)</h1>",
         "<p>Shown when a bird is damaged. Draft only. Every clip: <b>healthy v4 bubble left, leaking bubble right</b>. "
         "The leak is one extra 16 x 16 sprite on top of the unchanged bubble, in the bubble's own palette (no new colour). "
         "The leaking bubble also plays its wobble at double speed (no extra tiles).</p>",
         "<h2>In game, all three palettes</h2><p>Columns: healthy, A, B, C. Rows: player, player 2, computer.</p><img src=compare_ingame_6x.png>"]
    for var, title, n, uniq, used in cards:
        h += ["<h2>%s</h2><p>Frames: <b>%d</b> (%d game frames each, loop %.2f s). Extra tile cost: <b>%d tiles</b> (1 tile per frame, %d unique) and 1 extra sprite per leaking bird. Gum palette entries used: %s.</p>"
              % (title, n, TICK, n * TICK / 60, uniq, uniq, used), "<div class=r>"]
        h += ["<div>%s<img src=%s_%s_4x.gif></div>" % (lab, var, p) for p, lab in (("p1", "Player"), ("p2", "Player 2"), ("cpu", "Computer"))]
        h += ["</div>Frame sheet (level 10 bubble + leak), 4x and 1x<img src=%s_frames_4x.png><img src=%s_frames_1x.png>Leak tiles alone, 6x<img src=%s_tiles_6x.png>" % (var, var, var)]
    h += ["<h2>Other bubble sizes</h2><p>The same leak tiles on bubble levels 5, 7, 10, 12, 16. Rows: A, B, C.</p><img src=compare_sizes_4x.png>"]
    open(out("index.html"), "w").write("\n".join(h) + "\n")


if __name__ == "__main__":
    main()
