#!/usr/bin/env python3
"""Leaking gum bubble, round 2: a HOLE, no patch (2026-11-17). DRAFT ONLY, nothing here is imported by the game.

Built on round 1 (../2026-11-17-gum-leak/draw_gum_leak.py): same puff stamps, puff simulation (drag 0.62, rise 0.22),
palettes, sheet helpers. New here: hand-typed hole stamps, a rim-follow anchor (the tile tracks the bubble rim per
wobble frame), an optional puff outline, the dusk background compare, one baked see-through picture.
Stamp letters = gum palette entries 1..c. In BAKED, x = erased pixel (true transparency).
Run: python3.14 -I draw_gum_leak_hole.py
"""
import os, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "../2026-11-17-gum-leak"))
import draw_gum_leak as r1
v1, v4, g, row, col = r1.v1, r1.v4, r1.g, r1.row, r1.col
TICK, PAD, SHOWN = r1.TICK, r1.PAD, r1.SHOWN
DUSK = Image.open(os.path.join(HERE, "../2026-11-10-backgrounds-final/scene_dusk_1x.png")).convert("RGBA")
OUTLINE = "2"            # puff outline entry (dark purple) on the lower / right side of every puff pixel; None = round-1 plain puffs

# ---- hole stamps. Level 10 rim under the 9 x 7 stamp at tile (0, 8): outline at (4,1) (5,2) (6,3) (7,4) (7,5) (8,6).
# 1 / 2 = dark inside, b a = lit rolled lip (light from upper left), 9 6 5 = lip in shade, pixels right of the rim = lip torn outward.
D_HOLE = g("""
....11...
..bba91..
.b11111..
.a12221a1
.a112261.
..91165..
...966...
""")
E_OPEN = g("""
......1..
...bba1..
..b11111.
.b112211.
a1122661.
.11266...
..165....
""")
E_MID = g("""
.....11..
...bb9a1.
..b1111a1
.b11221..
a112266..
.1126....
..65.....
""")
E_SLIT = g("""
.........
....b91..
...b11a1.
..b1126..
.a1166...
.116.....
..5......
""")
# F: D's hole without the upper lip nub; a torn gum tongue hangs on the upper lip and streams in the jet. 11 x 9 at tile (0, 6).
F_UP = g("""
.......b1..
......a1...
....11a1...
..bba91....
.b11111....
.a12221a1..
.a112261...
..91165....
...966.....
""")
F_MID = g("""
........b1.
.......a1..
....11a1...
..bba91....
.b11111....
.a12221a1..
.a112261...
..91165....
...966.....
""")
F_LOW = g("""
...........
...........
....11.ab1.
..bba9a11..
.b11111....
.a12221a1..
.a112261...
..91165....
...966.....
""")
BAKED = g("""
....11...
..bba91..
.b1xxx...
.a1xxxxa1
.a11xx61.
..91165..
...966...
""")
BIG, SMALL, HISS = r1.BIG, r1.SMALL, r1.HISS
VAR = {
    "D": dict(title="D: round puncture, rolled lip, steady hiss + sputter", n=12, at=(0, 8), hole=lambda f: D_HOLE,
              emits=r1.VAR["C"]["emits"]),
    "E": dict(title="E: jagged split, lip flutters, air in gusts", n=8, at=(0, 8),
              hole=lambda f: [E_OPEN, E_OPEN, E_MID, E_SLIT, E_MID, E_OPEN, E_MID, E_SLIT][f],
              emits=[(0, 52, 3.0, BIG), (1, 40, 2.4, SMALL), (5, 62, 2.7, BIG), (6, 46, 2.2, SMALL)]
                    + [(f, [50, 58, 44, 54][f % 4], 2.0, HISS) for f in (0, 1, 2, 4, 5, 6)]),
    "F": dict(title="F: puncture with a torn gum tongue whipping in the hiss", n=6, at=(0, 6),
              hole=lambda f: [F_MID, F_UP, F_MID, F_LOW, F_MID, F_LOW][f],
              emits=[(0, 40, 2.6, SMALL), (3, 30, 2.4, SMALL)] + [(f, [34, 42, 28][f % 3], 2.2, HISS) for f in range(6)]),
}


def tile(var, f, outline=OUTLINE):
    """One 16 x 16 leak tile: hole stamp, then the simulated puffs (oldest first), then the puff outline on empty pixels."""
    v, t, p = VAR[var], [["."] * 16 for _ in range(16)], [["."] * 16 for _ in range(16)]
    r1.stamp(t, v["hole"](f), *v["at"])
    live = [((f - e[0]) % v["n"], e) for e in v["emits"]]
    for age, (_, ang, spd, kind) in sorted((l for l in live if l[0] < len(l[1][3])), key=lambda l: -l[0]):
        st = kind[age]; x, y = r1.puff_xy(ang, spd, age)
        r1.stamp(p, st, round(x - len(st[0]) / 2), round(y - len(st) / 2))
    for y in range(16):
        for x in range(16):
            if p[y][x] != ".": t[y][x] = p[y][x]
            elif outline and t[y][x] == "." and ((y and p[y - 1][x] != ".") or (x and p[y][x - 1] != ".")): t[y][x] = outline
    return tuple("".join(r) for r in t)


def rim(b, s):
    """Rim-follow anchor: walk the 45 degree ray from the bubble centre up-right; the last gum pixel is the rim."""
    cx, cy, t = b.width // 2, s // 2, 0
    while cx + t + 1 < b.width and cy - t - 1 >= 0 and b.getpixel((cx + t + 1, cy - t - 1))[3]: t += 1
    return cx + t, cy - t


def recolour(im, pal):
    if pal == "p1": return im
    P = v1.PAL[pal]   # shortcut: same mock-up recolour as v1.bubble / round 1 (map not exposed there); in game the gum palette is shared
    m = dict(zip(v1.GUMPAL, [P[0], P[9], P[9], P[9], P[10], P[10], P[11], P[11], P[12], P[13], P[14], P[3]]))
    im.putdata([(m.get(q[:3], q[:3]) + (255,)) if q[3] else q for q in im.get_flattened_data()]); return im


def leak_bubble(level, wob, grid, pal="p1"):
    """Bubble cell + leak tile; the tile origin puts the rim pixel at tile (6, 11) on every wobble frame."""
    b = v1.bubble(level, wob, "p1"); rx, ry = rim(b, SHOWN[16 - level])
    out = Image.new("RGBA", (b.width + 16, b.height + PAD), (0, 0, 0, 0))
    out.alpha_composite(b, (0, PAD)); out.alpha_composite(r1.paint(grid), (rx - 6, PAD + ry - 11))
    return recolour(out, pal), b.width


def frame(var, i, pal="p1", level=None, name=None, outline=OUTLINE):
    j = i // 2; name = name or v4.BL[j % 6]; level = level or 10 + v4.LV[j % 6]
    out = Image.new("RGBA", (v4.W, v4.H), (0, 0, 0, 0))
    lb, bw = leak_bubble(level, i, tile(var, i % VAR[var]["n"], outline), pal)    # wobble index = leak frame: double speed
    out.alpha_composite(lb, (v4.CX + v4.GX - bw // 2, v4.CY + v4.GRIP[1] + 2 - lb.height))
    out.alpha_composite(v4.frame(v4.T, name, 0, 0, pal))
    return out


def baked(pal="p1"):
    """Optional compare: the hole cut into the bubble frame itself (true see-through), level 10 wobble 0, rest pose."""
    b = v1.bubble(10, 0, "p1"); rx, ry = rim(b, SHOWN[6])
    for j, r in enumerate(BAKED):
        for i, c in enumerate(r):
            if c != ".": b.putpixel((rx - 6 + i, ry - 3 + j), (0, 0, 0, 0) if c == "x" else v1.GUMPAL[r1.GCH.index(c)] + (255,))
    out = Image.new("RGBA", (v4.W, v4.H), (0, 0, 0, 0))
    out.alpha_composite(recolour(b, pal), (v4.CX + v4.GX - b.width // 2, v4.CY + v4.GRIP[1] + 2 - b.height))
    out.alpha_composite(v4.frame(v4.T, "rest", 0, 0, pal))
    return out


def lum(c): return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def dusk_xy(w, h):
    """Brightest w x h window of the dusk scene (worst case for white puffs)."""
    small = DUSK.convert("L"); best = None
    for y in range(0, DUSK.height - h + 1, 8):
        for x in range(0, DUSK.width - w + 1, 8):
            m = sum(small.crop((x, y, x + w, y + h)).resize((8, 8)).get_flattened_data())
            if not best or m > best[0]: best = (m, x, y)
    return best[1], best[2]


def on_dusk(im, scale):
    x, y = dusk_xy(*im.size); b = DUSK.crop((x, y, x + im.width, y + im.height)); b.alpha_composite(im)
    return b.resize((im.width * scale, im.height * scale), Image.NEAREST).convert("RGB")


def main():
    out = lambda n: os.path.join(HERE, n)
    num, cards = [], []
    for var, v in VAR.items():
        n = v["n"]; grids = [tile(var, f) for f in range(n)]
        uniq = len(set(grids)); used = sorted({c for gr in grids for r in gr for c in r} - {"."})
        assert set(used) <= set(r1.GCH)
        def cell(f):
            c = Image.new("RGBA", (40, 36), (0, 0, 0, 0)); c.alpha_composite(leak_bubble(10, f, grids[f])[0], (2, 2)); return c
        sh = row([cell(f) for f in range(n)]); tl = row([r1.paint(gr) for gr in grids])
        v1.on_bg(sh, 1).save(out("%s_frames_1x.png" % var)); v1.on_bg(sh, 4).save(out("%s_frames_4x.png" % var))
        v1.on_bg(tl, 1).save(out("%s_tiles_1x.png" % var)); v1.on_bg(tl, 6).save(out("%s_tiles_6x.png" % var))
        for pal in ("p1", "p2", "cpu", "dusk"):
            bg = on_dusk if pal == "dusk" else v1.on_bg; p = "p1" if pal == "dusk" else pal
            ims = [bg(row([r1.healthy(i, p), frame(var, i, p)]), 4) for i in range(48)]
            ims[0].save(out("%s_%s_4x.gif" % (var, pal)), save_all=True, append_images=ims[1:], duration=TICK * 1000 // 60, loop=0, disposal=1)
        num.append("%s  %-58s frames %2d  tick %d game frames  loop %.2f s  1 tile per frame  unique tiles %2d  extra sprites 1  gum palette entries: %s"
                   % (var, v["title"], n, TICK, n * TICK / 60, uniq, " ".join(used)))
        cards.append((var, v["title"], n, uniq, " ".join(used)))
    # in-game compare: healthy, D, E, F (leak frame 3) x player, player 2, computer; flat and dusk, 1x and 3x
    cmp_ = col([row([v4.frame(v4.T, "rest", 10, 0, p)] + [frame(x, 3, p, 10, "rest") for x in VAR]) for p in ("p1", "p2", "cpu")])
    for s in (1, 3):
        v1.on_bg(cmp_, s).save(out("compare_flat_%dx.png" % s)); on_dusk(cmp_, s).save(out("compare_dusk_%dx.png" % s))
    # puff outline check on dusk: plain puffs (round 1) above, outlined below
    on_dusk(col([row([frame(x, f, "p1", 10, "rest", o) for x in VAR for f in (3, 5)]) for o in (None, OUTLINE)]), 3).save(out("outline_dusk_3x.png"))
    v1.on_bg(col([row([frame(x, 3, "p1", lv, "rest") for lv in (5, 7, 10, 12, 16)]) for x in VAR]), 4).save(out("compare_sizes_4x.png"))
    bk = row([v4.frame(v4.T, "rest", 10, 0, "p1"), frame("D", 3, "p1", 10, "rest"), baked()])
    on_dusk(bk, 1).save(out("baked_dusk_1x.png")); on_dusk(bk, 4).save(out("baked_dusk_4x.png")); v1.on_bg(bk, 4).save(out("baked_flat_4x.png"))
    # rim-follow table: tile origin in the bubble's sheet cell per level and wobble frame, and the shift against wobble 0
    T = v1.GD["tables"]; tab = []; cost = 0
    for lv in range(16, 0, -1):
        cost += (T["level_w"][16 - lv] // 16) * (T["level_h"][16 - lv] // 16) * 6; o = []
        for w in range(6):
            f = v1.GD["animations"]["level%d" % lv][w]; c = v1.GIM.crop((f["x"], f["y"], f["x"] + f["w"], f["y"] + f["h"])); bb = c.getbbox()
            rx, ry = rim(c.crop(bb), SHOWN[16 - lv]); o.append((bb[0] + rx - 6, bb[1] + ry - 11))
        tab.append("level %2d  " % lv + "  ".join("(%3d,%3d)" % p for p in o) + "   shift vs wobble 0: " + " ".join("(%+d,%+d)" % (p[0] - o[0][0], p[1] - o[0][1]) for p in o))
    px = sorted({q[:3] for q in DUSK.crop(dusk_xy(*cmp_.size) + tuple(a + b for a, b in zip(dusk_xy(*cmp_.size), cmp_.size))).get_flattened_data()}, key=lum)
    head = ("Rim-follow anchor: leak tile origin (x, y) in the bubble's sheet cell, wobble frames 0..5 (rim pixel on the 45 degree ray -> tile (6, 11)).\n"
            + "\n".join(tab) + "\n\nDusk window used for the compare: x %d y %d; sky luminance there %d..%d of 255 (white puff = 255, outline entry 2 = %d).\n"
            % (dusk_xy(*cmp_.size) + (lum(px[0]), lum(px[-1]), lum(v1.GUMPAL[1])))
            + "Baked see-through hole (hole cut into the bubble frames, static, puffs still the overlay sprite): a second copy of all "
              "16 levels x 6 wobble = %d tiles, plus the same puff tiles.\n\n" % cost)
    open(out("numbers.txt"), "w").write(head + "\n".join(num) + "\n"); print(head + "\n".join(num))
    h = ["<!doctype html><meta charset=utf-8><title>Gumbirds: leaking gum bubble, hole drafts</title>",
         "<style>body{background:#1b2030;color:#e6e9f2;font:15px/1.5 system-ui,sans-serif;margin:24px;max-width:1500px}"
         "img{image-rendering:pixelated;display:block;margin:6px 0 14px;border:1px solid #3a4260;max-width:100%}"
         "h1{font-size:24px}h2{font-size:19px;border-top:2px solid #ff52b5;padding-top:14px;margin-top:34px}"
         ".r{display:flex;gap:18px;flex-wrap:wrap}.r div{flex:0 0 auto}b{color:#ffa5de}</style>",
         "<h1>Leaking gum bubble, round 2: a hole (2026-11-17)</h1>",
         "<p>No patch. The damage is a hole the air hisses out of. Draft only. Every clip: <b>healthy bubble left, holed bubble right</b>. "
         "The hole is one extra 16 x 16 sprite on the unchanged bubble, gum palette only; it follows the bubble rim on every wobble frame; "
         "the holed bubble wobbles at double speed. Puffs carry a dark purple edge so they read on the bright dusk sky.</p>",
         "<h2>In game, all three palettes</h2><p>Columns: healthy, D, E, F. Rows: player, player 2, computer. Flat draft background and dusk sky, 3x then 1x.</p>",
         "<div class=r><div><img src=compare_flat_3x.png></div><div><img src=compare_dusk_3x.png></div></div>",
         "<div class=r><div><img src=compare_flat_1x.png></div><div><img src=compare_dusk_1x.png></div></div>"]
    for var, title, n, uniq, used in cards:
        h += ["<h2>%s</h2><p>Frames: <b>%d</b> (%d game frames each, loop %.2f s). Extra tile cost: <b>%d tiles</b> (1 tile per frame, %d unique) and 1 extra sprite per holed bubble. Gum palette entries used: %s.</p>"
              % (title, n, TICK, n * TICK / 60, uniq, uniq, used), "<div class=r>"]
        h += ["<div>%s<img src=%s_%s_4x.gif></div>" % (lab, var, p) for p, lab in (("p1", "Player"), ("p2", "Player 2"), ("cpu", "Computer"), ("dusk", "Player on dusk sky"))]
        h += ["</div>Frame sheet (level 10 bubble + hole), 4x and 1x<img src=%s_frames_4x.png><img src=%s_frames_1x.png>Hole tiles alone, 6x and 1x<img src=%s_tiles_6x.png><img src=%s_tiles_1x.png>" % (var, var, var, var)]
    h += ["<h2>Puff edge on the dusk sky</h2><p>Top row: plain white puffs (round 1). Bottom row: with the dark purple edge (used everywhere on this page). D, E, F at two moments each.</p><img src=outline_dusk_3x.png>",
          "<h2>Other bubble sizes</h2><p>The same hole tiles on bubble levels 5, 7, 10, 12, 16. Rows: D, E, F.</p><img src=compare_sizes_4x.png>",
          "<h2>For comparison: a true see-through hole baked into the bubble</h2><p>Healthy, D (overlay sprite, dark inside), baked (sky shows through). "
          "Baked cost: a second copy of every bubble frame = <b>%d tiles</b>, static hole, against %d tiles for D.</p>" % (cost, cards[0][3]),
          "<div class=r><div><img src=baked_dusk_4x.png></div><div><img src=baked_flat_4x.png></div><div><img src=baked_dusk_1x.png></div></div>"]
    open(out("index.html"), "w").write("\n".join(h) + "\n")


if __name__ == "__main__":
    main()
