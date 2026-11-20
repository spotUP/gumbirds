#!/usr/bin/env python3.11
"""Pop Drop terror faces, 2026-11-20. Owner: "the birds look happy when they fall they should look terrified".
Three takes on the SAME frame box (24 x 32), frame list (fall0..2 = 3 frames each, lean0..2 = 2 each) and bird
palette as assets/popdrop/popdrop_sheet.json, so a pick drops in with no code change.
Everything is a hand-typed grid or stamp laid over the 2026-11-18 body grids; only WHERE a stamp sits is computed.
Run: python3.11 draw_terror.py
"""
import os, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "../2026-11-18-popdrop-freefall"))
import draw_popdrop as d  # noqa: E402
d.HERE = HERE                                            # d.save / d.gif write next to this file
g, stamp, img = d.g, d.stamp, d.img
PLAYER, CPU = d.BIRD, [tuple(c) for c in d.FJ["palettes"]["cpu"]]

# ------------------------------------------------------------------ shared stamps
DROP = g("""
.1.
1f1
161
.1.
""", 3)                       # sweat / tear bead, left behind upward by the fall
SPECK = g("""
f
6
""", 1)
CREST_FAN = g("""
.....1.....
.1..161..1.
.11.161.11.
.161165161.
..1666551..
...166551..
...16651...
""", 11)                      # at (5, 3): crest feathers standing on end, three spikes
FEET_A = [g("""
.....89.
.....__.
""", 8), None, g("""
89......
__......
""", 8)]                      # at (8, 30): pedalling, one leg pulled up per frame

# ------------------------------------------------------------------ take A: screaming flail
EYES_A = g("""
....111....
..11f1f11..
.1fff1fff1.
1ffff1ffff1
1ffff1ffff1
1ff1f1f1ff1
16fff1fff61
.166616661.
..11131112.
....33..22.
""", 11)                      # at (8, 12): pop eyes, lids peaked in the middle (worried), pinprick pupils look down
BEAK_A = [g("""
..111..
.19981.
1998871
1877771
.171111
.1711b1
.171bc1
.171cc1
.177c71
1988871
.18771.
..111..
""", 7), g("""
..111..
.19981.
1998871
1877771
.171111
.17bc11
.171cb1
.1711c1
.177c71
1988871
.18771.
..111..
""", 7)]                      # at (17, 19): scream 12 tall (was 10), tongue whips between frames
SWOLLEN_A = g("""
..111.
.1abb1
1abbb1
1bbbb1
111111
1aaaa1
.1aaa1
""", 6)                       # at (8, 13): battered state 2, near eye swollen shut, the other still popping
WING_HI = g("""
11.1...
1911...
19891..
.1981..
.19871.
..1987.
..18771
...1877
...1871
....11.
""", 7)                       # at (0, 6): wing thrown straight up
FAR_HI = g("""
...1.1
..1818
..1881
.1871.
.1871.
1771..
.11...
""", 6)                       # at (18, 8): far wing flung up behind the head
FAR_MID = g("""
.111.
17881
.111.
""", 5)                       # at (19, 13)
SWEAT_A = [[(DROP, 17, 4), (SPECK, 3, 3)],
           [(DROP, 18, 1), (DROP, 1, 10), (SPECK, 20, 5)],
           [(DROP, 1, 6), (SPECK, 17, 7), (SPECK, 3, 1)]]

# ------------------------------------------------------------------ take B: frozen stiff
EYES_B = g("""
.1111.1111.
1ffff1ffff1
1ffff1ffff1
1f1ff1f1ff1
1ffff1ffff1
16fff16fff1
.1111.1111.
...333.332.
....33..22.
""", 11)                      # at (8, 13): round saucer eyes, pinprick pupils, thousand-yard stare
BEAK_B = [g("""
..111.
.19991
198881
1ff1f1
1f1ff1
188771
.1111.
""", 6), g("""
..111.
.19991
198881
1f1ff1
1ff1f1
188771
.1111.
""", 6)]                      # at (17, 19): beak clenched, teeth bared; the two frames make them chatter
SWOLLEN_B = g("""
..111.
.1abb1
1abbb1
111111
1aaaa1
1aaaa1
""", 6)                       # at (8, 13)
WING_STIFF = [g("""
11....
1911..
.19811
198771
1911..
11....
""", 6), g("""
1.....
1911..
.19811
198771
1911..
1.....
""", 6)]                      # at (1, 14): wing locked straight out, feather tips splayed
FAR_STIFF = g("""
..11
1191
7891
1191
..11
""", 4)                       # at (19, 13)
FEET_STIFF = g("""
898..898
""", 8)                       # at (8, 31): toes splayed
SWEAT_B = [[(DROP, 15, 7)], [(DROP, 15, 4), (DROP, 3, 8)], [(DROP, 15, 1), (DROP, 3, 5), (SPECK, 19, 8)]]

# ------------------------------------------------------------------ take C: eyes shut, clutching its head
FACE_C = g("""
11.....11
.11...11.
..11.11..
.11...11.
11.33..11
..333.332
..333.322
...33..22
""", 9)                       # at (9, 14): eyes screwed shut  > <
ARMS_C = g("""
........11..........
.......1651.........
.....1111651111.....
....199988178881....
...19988771778881...
..1987111111117881..
.1981..........1781.
1981............1781
19871...........1771
.1877...........171.
..11.............1..
""", 20)                      # at (2, 5): both wings clamped over the head, crest tuft squeezed out between them
LEAN_CLEAR = g("""
__....
____..
.__...
""", 6)                       # at (4, 5): the swept lean crest is under the wings too
BEAK_C = [g("""
.1111.
199981
188871
171711
187771
.1111.
""", 6), g("""
.1111.
199981
188871
117171
187771
.1111.
""", 6)]                      # at (17, 20): beak clamped shut, wobbling whimper line
SHINER_C = g("""
.aaaa.
a11bba
ab11ba
abb11a
ab11ba
a11bba
.aaaa.
""", 6)                       # at (8, 13)
FEET_TUCK = g("""
89...89.
__...__.
""", 8)                       # at (8, 30): legs pulled up
TEARS_C = [[(DROP, 3, 2), (SPECK, 19, 2)], [(DROP, 19, 1), (SPECK, 2, 0), (SPECK, 6, 3)],
           [(DROP, 1, 4), (DROP, 20, 3), (SPECK, 16, 0)]]


def base(lean, state, crest=None):
    """2026-11-18 body with its battered-state overlays (kink / stump crest, lumps, plaster) unchanged."""
    f = d.LEAN if lean else stamp(d.BODY, d.NOSTRING, 17, 9)
    x = 1 if lean else 0
    if state == 0 and crest and not lean: f = stamp(f, crest, 5, 3)
    if state == 1: f = stamp(stamp(f, d.LEAN_KINK, 4, 5) if lean else stamp(f, d.CREST_KINK, 8, 6), d.LUMP1, 13 + x, 10)
    if state == 2:
        f = stamp(f, d.LEAN_STUMP, 4, 5) if lean else stamp(f, d.CREST_STUMP, 8, 6)
        f = stamp(stamp(f, d.LUMP2, 12 + x, 8), d.PLASTER, 7 if lean else 9, 24)
    return f


def extras(f, lst):
    for st, x, y in lst: f = stamp(f, st, x, y)
    return f


def shift(f, dx): return [("." * dx + r)[:24] for r in f]     # 1 px shiver


def take_a(lean, state, k):
    f = stamp(stamp(base(lean, state, CREST_FAN), EYES_A, 8, 12), BEAK_A[k % 2], 17, 19)
    if state == 2: f = stamp(f, SWOLLEN_A, 8, 13)
    if lean:
        f = stamp(stamp(f, d.WING_LEAN[k], 0, 9), d.TAIL_FAN, 0, 19)
        f = stamp(f, d.FEET_LEAN_B, 0, 30) if k else stamp(f, FAR_HI, 18, 8)
        return extras(f, SWEAT_A[k * 2][:2])
    f = stamp(f, *[(WING_HI, 0, 6), (d.WING_MID, 0, 18), (d.WING_DOWN, 0, 21)][k])
    if k == 1: f = stamp(f, FAR_HI, 18, 8)
    if k == 2: f = stamp(f, FAR_MID, 19, 13)
    if FEET_A[k]: f = stamp(f, FEET_A[k], 8, 30)
    return extras(f, SWEAT_A[k] if state == 0 else SWEAT_A[k][:1])


def take_b(lean, state, k):
    f = stamp(stamp(base(lean, state), EYES_B, 8, 13), BEAK_B[k % 2], 17, 19)
    if state == 2: f = stamp(f, SWOLLEN_B, 8, 13)
    if lean:
        f = stamp(stamp(f, d.WING_LEAN[0], 1, 9), d.TAIL_FAN, 1, 19)
    else:
        f = stamp(stamp(f, WING_STIFF[k % 2], 1, 14), FEET_STIFF, 8, 31)
    f = extras(stamp(f, FAR_STIFF, 19, 13), SWEAT_B[k])
    return shift(f, 1) if k == 1 else f


def take_c(lean, state, k):
    x = 1 if lean else 0
    f = stamp(base(lean, state), FACE_C, 9, 14)
    if lean: f = stamp(stamp(f, LEAN_CLEAR, 4, 5), d.TAIL_FAN, 0, 19)
    f = stamp(stamp(f, ARMS_C, 2 + x, 5), BEAK_C[k % 2], 17, 20)
    if state == 1: f = stamp(f, d.LUMP1, 13 + x, 10)
    if state == 2: f = stamp(stamp(f, d.LUMP2, 12 + x, 8), SHINER_C, 8, 13)
    if not lean: f = stamp(f, FEET_TUCK, 8, 30)
    f = extras(f, TEARS_C[k])
    return shift(f, 1) if k == 1 and not lean else f


TAKES = {"a": ("A screaming flail", take_a), "b": ("B frozen stiff", take_b), "c": ("C eyes shut, clutching", take_c)}


def ntiles(grids):
    s = set()
    for f in grids:
        c = Image.new("RGBA", (32, 32)); c.paste(img(f, PLAYER), (0, 0))
        for ty in (0, 16):
            for tx in (0, 16):
                t = c.crop((tx, ty, tx + 16, ty + 16)).tobytes()
                if any(t[3::4]): s.add(t)
    return len(s)


def main():
    sky = Image.open(f"{HERE}/../2026-11-20-popdrop-sky/a_noon_sky_1x.png").convert("RGBA")
    AZ = sky.getpixel((sky.width // 2, min(sky.height - 1, 60)))
    E = lambda w, h, c=(0, 0, 0, 0): Image.new("RGBA", (w, h), c)

    def cell(grid, pal, t, left=False, rag=True, bg=None):
        """bird at (4, 14) in a 40 x 48 cell, gum rag above it as in game."""
        c = E(40, 48)
        c.alpha_composite(img(grid, pal), (4, 14))
        if rag: c.alpha_composite(img(d.RAG2[t % 4], pal), (4 + d.RAG2_AT[0], 14 + d.RAG2_AT[1]))
        if left: c = c.transpose(Image.FLIP_LEFT_RIGHT)
        if bg:
            b = E(40, 48, bg); b.alpha_composite(c); c = b
        return c

    def rows(rs, bg=AZ, gap=3):
        w = max(sum(i.width + gap for i in r) for r in rs) + gap
        out = E(w, sum(max(i.height for i in r) + gap for r in rs) + gap, bg); y = gap
        for r in rs:
            x = gap
            for i in r: out.alpha_composite(i, (x, y)); x += i.width + gap
            y += max(i.height for i in r) + gap
        return out

    def frames15(fn): return [fn(0, s, k) for s in range(3) for k in range(3)] + [fn(1, s, k) for s in range(3) for k in range(2)]

    cur = [d.fall2(w, s, w == 1) for s in range(3) for w in range(3)] + [d.lean2(s, k) for s in range(3) for k in range(2)]
    num = [f"current: 15 fall/lean frames, {ntiles(cur)} unique 16 x 16 tiles, {d.ncol(*[img(f, PLAYER) for f in cur])} colours"]
    plat = d.platform("plank", 3)
    gird = d.platform("girder", 4)
    for key, (name, fn) in TAKES.items():
        fr = frames15(fn)
        for f in fr: assert len(f) == 32 and all(len(r) == 24 for r in f), name
        num.append(f"{name}: 15 frames, {ntiles(fr)} unique tiles, {d.ncol(*[img(f, PLAYER) for f in fr])} colours")
        d.save(rows([[img(f, p) for f in fr] for p in (PLAYER, CPU)]), f"{key}_sheet", (1, 4))
        d.save(rows([[img(f, PLAYER) for f in cur[:3] + cur[9:11]], [img(f, PLAYER) for f in fr[:3] + fr[9:11]]]),
               f"{key}_vs_current", (1, 4))
        # game timing: frame >> 3 = 133 ms a frame, frames in order 0 1 2 (fall) / 0 1 (lean)
        d.gif([rows([[cell(fn(0, s, t % 3), p, t) for s in range(3)] for p in (PLAYER, CPU)]) for t in range(12)],
              f"{key}_fall", 133, 4)
        d.gif([rows([[cell(fn(1, 0, t % 2), p, t, left=l) for l in (False, True)] for p in (PLAYER, CPU)]) for t in range(4)],
              f"{key}_lean", 133, 4)
        m = sky.crop((0, 0, 320, 224)).copy()
        m.alpha_composite(gird, (28, 14)); m.alpha_composite(plat, (150, 160))
        m.alpha_composite(cell(fn(0, 0, 0), PLAYER, 0), (140, 30))
        m.alpha_composite(cell(fn(1, 1, 0), CPU, 1, left=True), (196, 88))
        m.alpha_composite(cell(fn(0, 2, 1), PLAYER, 2), (60, 96))
        d.save(m, f"{key}_mock", (1, 3))
    open(f"{HERE}/numbers.txt", "w").write("\n".join(num) + "\n")
    print("\n".join(num))


if __name__ == "__main__":
    main()
