#!/usr/bin/env python3
"""Leaking gum bubble, round 3: the escaping AIR redrawn (2026-11-17). DRAFT ONLY, nothing here is imported by the game.

Owner verdict on round 2 (../2026-11-17-gum-leak-hole/): "the air blowing out looks more like a fuse burning than air
blowing out". The holes D, E, F stay (stamps, rim-follow anchor and double-speed wobble are imported from round 2).
Only the air is new: no white streak at the hole, no dark puff outline, no lone bright specks. A dithered cone base
at the hole, dim blue-grey speed dashes on the cone edges, and rounded puffs that grow, slow down and dissolve in
dither. Every shape is a hand-typed stamp; only WHERE a stamp sits per frame is simulated (round-1 puff_xy: drag 0.62,
rise 0.22 per leak frame). The hole is drawn over the air, so the lip and F's tongue stay whole.
Stamp letters = gum palette entries: a pale pink, b white, c blue-grey rim light.
Run: python3.14 -I draw_gum_leak_air.py
"""
import os, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "../2026-11-17-gum-leak-hole"))
import draw_gum_leak_hole as r2
r1, v1, v4, g, row, col = r2.r1, r2.v1, r2.v4, r2.g, r2.row, r2.col
TICK = r2.TICK
MOODS = {m: Image.open(os.path.join(HERE, "../2026-11-10-backgrounds-final/scene_%s_1x.png" % m)).convert("RGBA") for m in ("dusk", "moon", "storm")}

# ---- cone base at the hole: a dithered fan, two phases, apex lower left at tile (7, 10), opening up and right. No white,
# blue-grey near the hole, pale pink further out. Placed at tile (7, 5). A fan, not a stem: round 3 take 1 had a 45 degree
# stem with a ball on it and still read as a fuse.
JET_A = g("""
..a.a.
.a.a.a
..c.a.
.c.c.a
..c.c.
c.....
""")
JET_B = g("""
.a...a
..a.a.
.c.a.a
..c.a.
.c.c..
......
""")
# ---- puff, by age: dither wisp -> round -> full -> holes open -> checker -> sparse, dim
A0 = g("""
.a.
c.a
.c.
""")
A1 = g("""
.a.a
a.ac
.aca
c.c.
""")
A2 = g("""
.bbb.
bbbba
bbbac
abaac
.acc.
""")
A3 = g("""
.bb.b.
bbbbab
.bbba.
bab.ac
.a.ac.
..c.c.
""")
A4 = g("""
..b.b.
.b.b.a
b.b.a.
.b.a.c
..a.c.
""")
A5 = g("""
..a...
....a.
.a....
...c.c
.c....
""")
B1 = g("""
.bb
bba
.ac
""")
B2 = g("""
.b.b
b.ba
.b.c
a.c.
""")
B3 = g("""
a..
..c
.c.
""")
# ---- 32 x 16 variant only: wider fan (placed at tile (7, 5)), larger late puff stages, longer curved speed lines
JW_A = g("""
....a.a...
...a.a.a.a
..c.a.a.a.
.c.c.a.a..
..c.c.a.a.
c..c.c....
""")
JW_B = g("""
.....a....
....a.a.a.
.c.a.a.a.a
..c.c.a.a.
.c.c.a.a..
..c.c.....
""")
C3 = g("""
..bb.b.
.bbbbbb
bbbbbba
abbbaac
.abaacc
..ac.c.
""")
C4 = g("""
..b.bb..
.b.bb.b.
b.bbbb.a
.bbb.ba.
a.b.a.ac
.a.a.ac.
..c.c.c.
""")
C5 = g("""
...b.b..
..b...a.
.b.b.a..
....a..c
.a.a..c.
......c.
...c....
""")
C6 = g("""
..a....
.....a.
.a.....
....c..
..c...c
""")
LONG = [A0, A1, A2, C3, C4, C5, C6]
LINE = [g("...cc\nccc.."), g("...ca\ncc..."), g(".c\nc."), g("c")]
DIAG = [g("..c\n.c.\n.c.\nc.."), g(".c\nc."), g("c")]
# ---- speed dashes on the cone edges, blue-grey only: steep (upper edge) and shallow (lower edge)
UP = [g(".c\n.c\nc."), g(".c\nc."), g("c")]
RT = [g("..c\ncc."), g(".c\nc."), g("c")]
BIG, SMALL = [A0, A1, A2, A3, A4, A5], [A0, B1, B2, B3]
H = r2.VAR
dashes = lambda fs: [(f, 74 if f % 2 else 16, 3.0, UP if f % 2 else RT) for f in fs]
# emits: (frame, angle deg above horizontal, speed px per leak frame, stamp list by age)
VAR = {
    "D": dict(title="D: round puncture, steady blow", w=16, n=12, at=H["D"]["at"], hole=H["D"]["hole"], jet=lambda f: (JET_A, JET_B)[f % 2],
              emits=[(0, 30, 2.4, BIG), (2, 72, 2.3, SMALL), (4, 60, 2.4, BIG), (6, 20, 2.2, SMALL), (8, 45, 2.5, BIG), (10, 54, 2.2, SMALL)]
                    + dashes(range(12))),
    "E": dict(title="E: jagged split, two gusts", w=16, n=8, at=H["E"]["at"], hole=H["E"]["hole"], jet=lambda f: {0: JET_A, 1: JET_B, 5: JET_A, 6: JET_B}.get(f),
              emits=[(0, 60, 2.4, BIG), (1, 24, 2.3, SMALL), (5, 32, 2.4, BIG), (6, 68, 2.2, SMALL)] + dashes((0, 1, 5, 6))),
    "F": dict(title="F: puncture plus torn tongue, thin stream", w=16, n=12, at=H["F"]["at"], hole=lambda f: H["F"]["hole"](f % 6), jet=lambda f: (JET_B, JET_A)[f % 2],
              emits=[(0, 24, 2.4, BIG), (3, 44, 2.3, SMALL), (6, 34, 2.4, BIG), (9, 14, 2.3, SMALL)] + [(f, 16 if f % 4 else 50, 3.0, RT if f % 4 else UP) for f in range(0, 12, 2)]),
    # W: D's hole, air in a 32 x 16 tile pair (2 tiles per frame, 2 sprites: a Neo Geo sprite is 16 px wide). Jet aimed shallower, 3x the reach.
    "W": dict(title="W: D's puncture, air in 32 x 16 (2 tiles per frame)", w=32, n=12, at=H["D"]["at"], hole=H["D"]["hole"], jet=lambda f: (JW_A, JW_B)[f % 2],
              emits=[(0, 18, 5.5, LONG), (2, 38, 4.5, SMALL), (4, 4, 6.5, LONG), (6, 26, 4.5, SMALL), (8, 11, 6.0, LONG), (10, 0, 5.0, SMALL)]
                    + [(f, 40 if f % 2 else 10, 5.0 if f % 2 else 7.0, DIAG if f % 2 else LINE) for f in range(12)]),
}


def stamp(t, st, x, y):
    for j, r in enumerate(st):
        for i, c in enumerate(r):
            if c == ".": continue
            assert 0 <= x + i < len(t[0]) and 0 <= y + j < 16, ("stamp leaves the tile", x + i, y + j)
            t[y + j][x + i] = c


def tile(var, f, hole_only=False):
    """One 16 x 16 (W: 32 x 16) leak tile: cone base, simulated air stamps (oldest first), then the hole on top."""
    v = VAR[var]; t = [["."] * v["w"] for _ in range(16)]
    if not hole_only:
        if v["jet"](f): stamp(t, v["jet"](f), 7, 5)
        live = [((f - e[0]) % v["n"], e) for e in v["emits"]]
        for age, (_, ang, spd, kind) in sorted((l for l in live if l[0] < len(l[1][3])), key=lambda l: -l[0]):
            st = kind[age]; x, y = r1.puff_xy(ang, spd, age)
            stamp(t, st, round(x - len(st[0]) / 2), round(y - len(st) / 2))
    stamp(t, v["hole"](f), *v["at"])
    return tuple("".join(r) for r in t)


def leak_bubble(level, wob, grid, pal="p1"):
    """r2.leak_bubble with room for a 32 px tile: rim pixel at tile (6, 11) on every wobble frame."""
    b = v1.bubble(level, wob, "p1"); rx, ry = r2.rim(b, r2.SHOWN[16 - level])
    out = Image.new("RGBA", (b.width + 32, b.height + r2.PAD), (0, 0, 0, 0))
    out.alpha_composite(b, (0, r2.PAD)); out.alpha_composite(r1.paint(grid), (rx - 6, r2.PAD + ry - 11))
    return r2.recolour(out, pal), b.width


def frame(var, i, pal="p1"):
    """Bird + holed bubble with the round-3 air (same layout as r2.frame, which draws the round-2 air)."""
    j = i // 2; out = Image.new("RGBA", (v4.W + 16, v4.H), (0, 0, 0, 0))
    lb, bw = leak_bubble(10 + v4.LV[j % 6], i, tile(var, i % VAR[var]["n"]), pal)    # wobble index = leak frame: double speed
    out.alpha_composite(lb, (v4.CX + v4.GX - bw // 2, v4.CY + v4.GRIP[1] + 2 - lb.height))
    out.alpha_composite(v4.frame(v4.T, v4.BL[j % 6], 0, 0, pal))
    return out


def on(mood, im, scale):
    """Flat draft background, or the brightest window of a mood scene (worst case for pale air)."""
    if mood == "flat": return v1.on_bg(im, scale)
    s = MOODS[mood]; L = s.convert("L")
    _, x, y = max((sum(L.crop((x, y, x + im.width, y + im.height)).resize((8, 8)).get_flattened_data()), x, y)
                  for y in range(0, s.height - im.height + 1, 8) for x in range(0, s.width - im.width + 1, 8))
    b = s.crop((x, y, x + im.width, y + im.height)); b.alpha_composite(im)
    return b.resize((im.width * scale, im.height * scale), Image.NEAREST).convert("RGB")


def cue(im, name):
    """Warm / hot cue palette swap of the gum entries (assets/gum/gum_sheet.json cue_palettes)."""
    C = v1.GD["cue_palettes"]; m = {v1.GUMPAL[e - 1]: tuple(c) for e, c in zip(C["entries"], C[name])}
    im = im.copy(); im.putdata([(m.get(q[:3], q[:3]) + (255,)) if q[3] else q for q in im.get_flattened_data()]); return im


def main():
    out = lambda n: os.path.join(HERE, n)
    num, cards = [], []
    for var, v in VAR.items():
        n = v["n"]; grids = [tile(var, f) for f in range(n)]; o = "D" if var == "W" else var; old = [r2.tile(o, f % H[o]["n"]) for f in range(n)]
        uniq = len(set(grids)); used = sorted({c for gr in grids for r in gr for c in r} - {"."})
        assert set(used) <= set(r1.GCH)
        air = sorted({gr[y][x] for f, gr in enumerate(grids) for y in range(16) for x in range(v["w"]) if gr[y][x] not in (".", tile(var, f, True)[y][x])})
        assert set(air) <= set("abc"), air                      # self-check: the air uses the pale entries only
        def cell(gr, f):
            c = Image.new("RGBA", (52, 36), (0, 0, 0, 0)); c.alpha_composite(leak_bubble(10, f, gr)[0], (2, 2)); return c
        sh = col([row([cell(gs[f], f) for f in range(k, min(k + 6, n))]) for k in range(0, n, 6) for gs in (old, grids)])   # 6 per row: fits the 320 px scenes
        for mood in ("flat", "dusk", "moon", "storm"):
            for s in (1, 3):
                on(mood, sh, s).save(out("%s_frames_%s_%dx.png" % (var, mood, s)))
                ims = [on(mood, row([r2.frame(o, i), frame(var, i)]), s) for i in range(24)]
                ims[0].save(out("%s_%s_%dx.gif" % (var, mood, s)), save_all=True, append_images=ims[1:], duration=TICK * 1000 // 60, loop=0, disposal=1)
        v1.on_bg(row([r1.paint(gr) for gr in grids]), 6).save(out("%s_tiles_6x.png" % var))
        k = v["w"] // 16
        num.append("%s  %-52s frames %2d  tick %d game frames  loop %.2f s  %d tile(s) per frame  tiles %2d (unique %2d)  extra sprites %d (16 px wide each)  gum palette entries: %s  (air: %s)"
                   % (var, v["title"], n, TICK, n * TICK / 60, k, n * k, uniq * k, k, " ".join(used), " ".join(air)))
        cards.append((var, v["title"], n, k, " ".join(air)))
    c0 = row([frame(x, f) for x in "DEF" for f in (3, 7)])
    v1.on_bg(col([c0, cue(c0, "warm"), cue(c0, "hot")]), 3).save(out("cue_3x.png"))
    head = ("Round 3: air only. Holes, rim-follow table and wobble as round 2 (../2026-11-17-gum-leak-hole/numbers.txt).\n"
            "Puff simulation: drag %.2f, rise %.2f px per leak frame (round-1 puff_xy). Round-2 tile counts: D 12, E 8, F 6.\n\n" % (r1.DRAG, r1.RISE))
    open(out("numbers.txt"), "w").write(head + "\n".join(num) + "\n"); print(head + "\n".join(num))
    h = ["<!doctype html><meta charset=utf-8><title>Gumbirds: leaking gum bubble, air drafts</title>",
         "<style>body{background:#1b2030;color:#e6e9f2;font:15px/1.5 system-ui,sans-serif;margin:24px;max-width:1500px}"
         "img{image-rendering:pixelated;display:block;margin:6px 0 14px;border:1px solid #3a4260;max-width:100%}"
         "h1{font-size:24px}h2{font-size:19px;border-top:2px solid #ff52b5;padding-top:14px;margin-top:34px}"
         ".r{display:flex;gap:18px;flex-wrap:wrap}.r div{flex:0 0 auto}b{color:#ffa5de}</style>",
         "<h1>Leaking gum bubble, round 3: the air (2026-11-17)</h1>",
         "<p>Draft only. The holes are unchanged from round 2. Every picture: <b>round-2 air left (or top), round-3 air right (or bottom)</b>. "
         "New air: no white streak at the hole, no dark puff outline. A dithered cone base, dim speed dashes on the cone edges, "
         "rounded puffs that grow, slow down and dissolve in dither. D, E, F: still one extra 16 x 16 sprite, 1 tile per frame, gum palette only. W (last section) is D with the air in a 32 x 16 tile pair, to show what more room buys.</p>"]
    for var, title, n, k, air in cards:
        h += ["<h2>%s</h2><p>Frames: <b>%d</b> (%d game frames each, loop %.2f s). Cost: <b>%d tiles</b> (%d per frame), <b>%d</b> extra sprite(s) per holed bubble. Air uses gum entries %s.</p><div class=r>"
              % (title, n, TICK, n * TICK / 60, n * k, k, k, air)]
        h += ["<div>%s, 3x<img src=%s_%s_3x.gif>1x<img src=%s_%s_1x.gif></div>" % (lab, var, m, var, m)
              for m, lab in (("flat", "Flat"), ("dusk", "Dusk"), ("moon", "Moon"), ("storm", "Storm"))]
        h += ["</div>"] + ["Frames on %s (rows alternate: round 2, then round 3, six frames per row), 3x and 1x<img src=%s_frames_%s_3x.png><img src=%s_frames_%s_1x.png>" % (m, var, m, var, m)
                           for m in ("flat", "dusk", "moon", "storm")]
        h += ["Round-3 tiles alone, 6x<img src=%s_tiles_6x.png>" % var]
    h += ["<h2>Warm and hot cue palettes</h2><p>D, E, F at two moments. Rows: normal, warm, hot. Entries a and c change in the cue palettes, so the air turns tan, then orange.</p><img src=cue_3x.png>"]
    open(out("index.html"), "w").write("\n".join(h) + "\n")


if __name__ == "__main__":
    main()
