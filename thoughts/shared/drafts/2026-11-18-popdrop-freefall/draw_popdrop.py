#!/usr/bin/env python3
"""Pop Drop free-fall drafts (2026-11-18). DRAFT ONLY, nothing here is imported by the game.

Every sprite is a hand-typed pixel grid or a hand-typed stamp laid over one (wing, beak, lump, black eye ...).
Nothing is generated: the only computed things are WHERE stamps sit in the animations / mock-up, the H-flip
(free on Neo Geo) and palette swaps (also free). The lean frame is the fall frame with rows nudged sideways by the
hand-typed LEAN_NUDGE list. Bird body rows come from the in-game fall frame 52 (assets/flier/sootling_sheet.png)
so it is the same character at the same scale (24 x 32). Gum pickup + catch burst are the existing Gum Trip
pickup sheet (assets/trippickup), reused unchanged.
Second pass (same day): owner picks applied and five weak spots redrawn, see SECOND PASS below.
Run: python3.14 -I draw_popdrop.py
"""
import json, os
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "../../../.."))
PANEL = (58, 63, 92, 255)
CH = "123456789abcdef"

# ---- palettes (15 + transparent each)
FJ = json.load(open(f"{ROOT}/assets/flier/sootling_sheet.json"))
BIRD = [tuple(c) for c in FJ["palettes"]["player"]]            # existing player palette, unchanged
GUM = [(8, 8, 24), (107, 16, 132), (123, 24, 66), (148, 24, 148), (181, 41, 165), (222, 57, 173), (255, 82, 181),
       (255, 123, 198), (255, 165, 222), (255, 222, 247), (255, 255, 255), (82, 148, 181)]   # existing gum palette
PLAT = [(8, 8, 24), (41, 24, 49), (82, 49, 66), (132, 82, 74), (189, 132, 99), (239, 198, 148),   # 1 line, 2-6 rock/wood
        (16, 82, 66), (24, 148, 74), (123, 222, 82), (222, 255, 156),                           # 7-a grass
        (49, 57, 90), (99, 115, 148), (173, 189, 214), (255, 198, 49), (255, 255, 255)]         # b-d steel, e hazard, f white
GHOST = [(int(r * .35 + 20), int(g * .35 + 22), int(b * .45 + 50)) for r, g, b in PLAT]            # echo = palette swap


def g(text, w):
    rows = [r.strip() for r in text.strip().split("\n")]
    for r in rows: assert len(r) <= w, (len(r), r)
    return [r.ljust(w, ".") for r in rows]


def blank(w, h): return ["." * w] * h


def stamp(grid, st, x, y):
    """Lay stamp over grid. '.' = leave, '_' = clear to transparent."""
    out = [list(r) for r in grid]
    for j, row in enumerate(st):
        for i, c in enumerate(row):
            if c != "." and 0 <= y + j < len(out) and 0 <= x + i < len(out[0]):
                out[y + j][x + i] = "." if c == "_" else c
    return ["".join(r) for r in out]


def flip(grid): return [r[::-1] for r in grid]


def img(grid, pal):
    im = Image.new("RGBA", (len(grid[0]), len(grid)), (0, 0, 0, 0))
    for y, row in enumerate(grid):
        for x, c in enumerate(row):
            if c != ".": im.putpixel((x, y), pal[CH.index(c)] + (255,))
    return im


# =========================================================== 1. BIRD (24 x 32, player palette)
# Body: in-game fall frame 52 minus the wing, crest blown taller by the up-draught, beak wide open (scream).
BODY = g("""
........................
........................
........................
........................
........................
........................
..........11............
.........1651...........
.........16651..........
........16651....1e1....
........16651....1d1....
........16651.....1d1...
........1665111...1d1...
........166655411.1d1...
.......16666555441d1....
......166655555444d1....
......1666555554441c....
......1665553343341.....
......165433ff43ff21....
......15543fff4fff21....
......15443ff14ff121....
......1444336143619981..
.....14443333333227c71..
.....14433333233228871..
......14333233222211....
......1433323322221.....
......1332332222221.....
.......13232222221......
........122222211.......
.........111111.........
.........7....7.........
........89....89........
""", 24)
WING_UP = g("""
11.....
191....
1981...
.1981..
.1987..
..187..
..18771
...111.
""", 7)                       # at (1, 14): same pixels as in-game frame 52
WING_MID = g("""
..1111..
.199981.
19988771
.1187771
...1111.
""", 8)                       # at (0, 18): new in-between
WING_DOWN = g("""
....111.
...19871
..198771
.198711.
19811...
111.....
""", 8)                       # at (0, 21): same pixels as in-game frame 55
FEET_KICK = g("""
___7_____7______
___98___89______
""", 16)                      # at (6, 30)
# battered state 1: crest tip kinked over, one lump
CREST_KINK = g("""
______
__1111
_16551
""", 6)                       # at (8, 6)
LUMP1 = g("""
.11.
1ec1
1cb1
""", 4)                       # at (13, 10)
FEATHER1 = g("""
.5.
56.
5..
""", 3)
# battered state 2: crest snapped to a stump, double lump, swollen black eye, plaster, loose feathers
CREST_STUMP = g("""
______
______
______
_1111_
""", 6)                       # at (8, 6)
LUMP2 = g("""
...11.
..1ec1
.11dc1
1ec1b1
1dcb11
""", 6)                       # at (12, 8)
BLACKEYE = g("""
abba
a111
aaaa
3aa3
""", 4)                       # at (10, 18)
PLASTER = g("""
ee..
.fe.
..ee
""", 4)                       # at (9, 24)
FEATHERS2 = g("""
..5.......
.56.....6.
.5.....65.
.......5..
""", 10)                      # at (1, 1)
LEAN_NUDGE = [0] * 6 + [2] * 8 + [1] * 6 + [0] * 6 + [-1] * 6     # px per row: head leads into the turn


def fall_frame(wing, state):
    f = BODY
    if state == 1:
        f = stamp(stamp(stamp(f, CREST_KINK, 8, 6), LUMP1, 13, 10), FEATHER1, 3, 3)
    if state == 2:
        f = stamp(stamp(stamp(stamp(stamp(f, CREST_STUMP, 8, 6), LUMP2, 12, 8), BLACKEYE, 10, 18), PLASTER, 9, 24),
                  FEATHERS2, 1, 1)
    if wing == 0: f = stamp(f, WING_UP, 1, 14)
    if wing == 1: f = stamp(f, WING_MID, 0, 18)
    if wing == 2: f = stamp(stamp(f, WING_DOWN, 0, 21), FEET_KICK, 6, 30)
    return f


def lean_frame(state):
    out = []
    for row, n in zip(fall_frame(0, state), LEAN_NUDGE):
        out.append(("." * n + row)[:24] if n >= 0 else (row[-n:] + "." * -n))
    return out


BONK = g("""
........................
........................
........................
........................
........................
........................
........................
........................
........................
........................
........................
........................
........................
......111...............
.....16651..............
......16651111111.......
.....1166655554441......
....166665555554441.....
...16665533343334441....
...1655431f141f134221...
...155443f1f4f1f342221..
..18144431f141f13229981.
.19871443333333322871c..
.1987714333233322211cd..
..11111433323322221.....
......13323322222221....
.......132322222221.....
........1222222211......
.........11111111.......
........7......7........
.......89......89.......
........................
""", 24)
STARS_A = g("""
....9..........f........
...9f9.........9........
....9.......f.....9.....
............9....9f9....
.........9........9.....
........9f9.............
.........9..............
""", 24)
STARS_B = g("""
..........9.............
.........9f9......f.....
...f......9.......9.....
...9..............9.....
..9f9........9..........
...9........9f9.........
.............9..........
""", 24)
CRASH = g("""
................................
................................
................................
................................
................................
................................
...........89......89...........
............7......7............
.........11111111111111.........
......111222222222222221111.....
...11143332332333323323333411...
.1981443331f141f133344441891....
1988715544f1f4f1f35544422178891.
..111665551f141f1432299811111...
......116666555544433222871c....
........1111111111111111.cd.....
""", 32)
# deflated, torn, empty gum skin on its string (16 x 16, bird palette pinks). Sits at bird (11, -7).
RAG = [g("""
......11........
.....1dc1.11....
.....1cbc1dc1...
....1dcbbccb1...
....1cb1abcb1...
...1dcb1.1bca1..
...1cbba11cba1..
....1cbbccba1...
....1dcbbba1....
.....1cbba1.....
.....1dcb1......
......1cb1......
......1dc1......
.......1d1......
.......1d1......
......1d1.......
""", 16), g("""
.........11.....
.......11dc1....
......1dccbc1...
.....1dcb1cb1...
.....1cb1.1ba1..
....1dcba11ca1..
....1cbbbccba1..
....1dcbbbba1...
.....1cbbba1....
.....1dcba1.....
......1cb1......
......1dc1......
.......1c1......
.......1d1......
......1d1.......
......1d1.......
""", 16), g("""
....11..........
...1dc11........
...1cbcd1.1.....
..1dcbbcc1d1....
..1cb1abbcc1....
..1cb1.1bba1....
...1ca11bba1....
...1dcbbba1.....
....1cbba1......
....1dcba1......
.....1cb1.......
.....1dc1.......
......1c1.......
......1d1.......
.......1d1......
......1d1.......
""", 16)]
RAG_AT = (11, -7)

# =========================================================== 2. PLATFORMS (16 x 16 tiles, PLAT palette)
# each type: left cap, repeating middle; right cap = left cap H-flipped (no extra tile)
ROCK_L = g("""
................
......11...1.11.
....11a91.1a19a1
..11a99891a99899
.1a9988888988888
1998887887888788
1887871777877177
1771765117715651
.116655416655544
.156554435544433
..15443324433322
..14433223332221
...1332212222111
....12211.1111..
.....111........
................
""", 16)
ROCK_M = g("""
................
.11..1.11...11..
1a9111a19a11a991
99899a998998a998
8888898888888988
8788788878788788
7177717787717771
5651176511565117
5544416654455441
4433365544344336
3322254433233225
2221143322122214
111.11221..1111.
.....111........
................
................
""", 16)
GIRD_L = g("""
................
................
................
.111111111111111
1fddddddddddcddd
1dccccccccccbccc
1ce1eee1eee1eee1
1c1eee1eee1eee1e
1ceee1eee1eee1ee
1cbbbbbbbbbb2bbb
1bcdbbbbbbcdbbbb
1b2bbbb2bbb2bbbb
.111111111111111
................
................
................
""", 16)
GIRD_M = g("""
................
................
................
1111111111111111
dddddddcdddddfdd
cccccccbcccccccc
eee1eee1eee1eee1
ee1eee1eee1eee1e
e1eee1eee1eee1ee
bbbbbbb2bbbbbbbb
bbbcdbbbbbbcdbbb
bbb2bbbbb2b2bbbb
1111111111111111
................
................
................
""", 16)
PLANK_L = g("""
................
................
................
..11111111111111
.165565556555655
1654454445444544
1543343334313433
1433232223222322
.132222222222222
..11111111111111
....1d1.........
....1c1.........
....1d1.........
.....1c.........
................
................
""", 16)
PLANK_M = g("""
................
................
................
1111111111111111
5655565515655565
4544454414544454
3433313313433343
2322232212322232
2222222212222222
1111111111111111
................
................
................
................
................
................
""", 16)
# speed streak option 1: hand-dithered vertical streak tiles hung under the platform (dense, then sparse tail)
STREAK_A = g("""
f...d..f...d...f
f...d..f...d...f
f...d..f...d...f
f...d..d...d...f
d...d..d...c...f
d...c..d...c...d
d...c..d...c...d
d......d.......d
d...c..c...c...d
c......c.......d
c...c..c.......c
c......c...c...c
.......c.......c
c..............c
.......c........
c...............
""", 16)
STREAK_B = g("""
c......c.......c
................
c..............c
.......c........
................
c...............
...............c
................
.......c........
................
c...............
................
...............c
................
................
.......c........
""", 16)
WISP = g("""
........ddd.....................
.....dddfffddd......ddd.........
..dddffffffffdddddddfffdd.......
dddcccddddfffffffffddddccddd....
....cccc.cdddddddcccc...........
""", 32)
PTYPES = {"rock": (ROCK_L, ROCK_M), "girder": (GIRD_L, GIRD_M), "plank": (PLANK_L, PLANK_M)}


def platform(kind, mids, pal=PLAT):
    L, M = PTYPES[kind]
    im = Image.new("RGBA", (16 * (mids + 2), 16), (0, 0, 0, 0))
    im.paste(img(L, pal), (0, 0))
    for i in range(mids): im.paste(img(M, pal), (16 + 16 * i, 0))
    im.paste(img(flip(L), pal), (16 + 16 * mids, 0))
    return im


def platform_fast(kind, mids, mode):
    """mode 0 plain, 1 streak tiles under it, 2 ghost echoes (same tiles, dark palette, 5 and 10 px lower)."""
    w = 16 * (mids + 2)
    im = Image.new("RGBA", (w, 48), (0, 0, 0, 0))
    if mode == 1:
        for i in range(mids + 2):
            im.alpha_composite(img(STREAK_A, PLAT), (16 * i, 10))
            im.alpha_composite(img(STREAK_B, PLAT), (16 * i, 26))
    if mode == 2:
        gh = platform(kind, mids, GHOST)
        im.alpha_composite(gh, (0, 10)); im.alpha_composite(gh, (0, 5))
    im.alpha_composite(platform(kind, mids), (0, 0))
    return im


# =========================================================== 4. SHIELD BUBBLE (48 x 48, gum palette)
# one hand-typed quadrant of the rim, mirrored 4 ways (tile flips); lower half one shade darker; gloss stamps on top
QUAD = [("." * n + s).ljust(24, ".") for n, s in [
    (18, "557777"), (15, "5557999.a"), (13, "55799.a"), (12, "5799.a"), (10, "5579.a"), (9, "5799.a"), (8, "579.a"),
    (7, "579.a"), (6, "579.a"), (5, "579.a"), (4, "579"), (4, "579a"), (3, "579"), (3, "579a"), (2, "579"),
    (2, "579.a"), (2, "579"), (1, "579.a"), (1, "579"), (1, "579.a"), (1, "579"), (1, "579.a"), (0, "579"),
    (0, "579.a")]]
DARKER = str.maketrans("579a", "4579")
GLOSS = g("""
...bb
.bba.
bba..
ba...
b....
a....
""", 5)
RIMLIGHT = g("""
....a
...a.
..9a.
99a..
""", 5)
SPECK = g("""
.a.
aba
.a.
""", 3)
SHARD_T = g("""
.7997.
79..97
""", 6)
SHARD_S = g("""
.7
79
9.
9.
79
.7
""", 2)
SHARD_D = g("""
.79
79.
9..
""", 3)


def shield(frame):
    top = [r + r[::-1] for r in QUAD]
    grid = top + [r.translate(DARKER) for r in top[::-1]]
    grid = stamp(grid, GLOSS, 12 + frame, 9)
    grid = stamp(grid, RIMLIGHT, 31, 35 - frame)
    return stamp(grid, SPECK, 33 - 2 * frame, 11 + frame)


def shield_pop(k):
    """k 0: whole rim flashes white (palette swap). k 1..3: hand shards at hand-listed spots, flying out."""
    if k == 0: return [r.translate(str.maketrans("45679a", "bbbbbb")) for r in shield(0)]
    d = 3 * k
    grid = blank(64, 64)
    for st, x, y in [(SHARD_T, 29, 8 - d), ([r[::-1] for r in SHARD_T[::-1]], 29, 54 + d),
                     (SHARD_S, 8 - d, 29), (flip(SHARD_S), 54 + d, 29),
                     (SHARD_D, 14 - d, 14 - d), (flip(SHARD_D), 47 + d, 14 - d),
                     (SHARD_D[::-1], 14 - d, 47 + d), (flip(SHARD_D[::-1]), 47 + d, 47 + d),
                     (SPECK, 22 - d, 20), (SPECK, 40 + d, 41), (SPECK, 38, 18 - d)]:
        if k == 3 and st is SPECK: continue
        grid = stamp(grid, st if k < 3 else [r.translate(DARKER) for r in st], x, y)
    return grid


# =========================================================== output helpers
def up(im, n): return im.resize((im.width * n, im.height * n), Image.NEAREST)


def panel(im, pad=4, bg=PANEL):
    out = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), bg)
    out.alpha_composite(im, (pad, pad)); return out


def strip(ims, gap=4, bg=PANEL):
    h = max(i.height for i in ims)
    out = Image.new("RGBA", (sum(i.width + gap for i in ims) + gap, h + 2 * gap), bg)
    x = gap
    for i in ims: out.alpha_composite(i, (x, gap + h - i.height)); x += i.width + gap
    return out


def save(im, name, scales=(1, 3)):
    for s in scales: up(im, s).save(f"{HERE}/{name}_{s}x.png")


def gif(frames, name, ms, scale=3):
    fr = [up(f, scale).convert("RGB") for f in frames]
    fr[0].save(f"{HERE}/{name}.gif", save_all=True, append_images=fr[1:], duration=ms, loop=0, disposal=1)


def ncol(*ims):
    s = set()
    for im in ims: s |= {c[:3] for _, c in im.getcolors(99999) if c[3]}
    return len(s)


def bird_with_rag(frame, t, w=40, h=44):
    """bird at (4, 10) in a w x h cell with the gum rag above."""
    c = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    c.alpha_composite(img(RAG[(0, 1, 0, 2)[t % 4]], BIRD), (4 + RAG_AT[0], 10 + RAG_AT[1]))
    c.alpha_composite(img(frame, BIRD), (4, 10)); return c


def sheet_frames(path, rects):
    im = Image.open(path).convert("RGBA")
    return [im.crop((r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"])) for r in rects]


# =========================================================== SECOND PASS (2026-11-18): owner picks + five fixes
# Owner picks: speed look A (streak tiles), Gum Trip candy reused, bird faces its steering direction (left = H-flip),
# all three platforms kept. The first-pass grids above (BODY beak + baked string, lean_frame, CRASH, RAG) stay only
# so the old-vs-new comparison images can be rebuilt. Still nothing generated: every sprite is a typed grid or a
# typed stamp; only WHERE things sit in the animations is computed.
NOSTRING = g("""
___.
___.
____
____
____
.__.
.1_.
.._.
""", 4)                       # at (17, 9): the gum strand is no longer baked into the bird, it belongs to the rag
# fix 2: scream beak, 7 x 10 instead of 4 x 3. Bright mandibles flung apart, black throat, pink tongue.
BEAK_SCREAM = g("""
..111..
.19991.
1998881
1177771
.171111
.1711c1
.177cc1
1988871
.18771.
..111..
""", 7)                       # at (17, 19)
CREST_B = g("""
_11___
1651__
_16651
""", 6)                       # at (8, 6): crest tip whipped left, every other fall frame


def fall2(wing, state, crest=0):
    f = stamp(stamp(BODY, NOSTRING, 17, 9), BEAK_SCREAM, 17, 19)
    if state == 0 and crest: f = stamp(f, CREST_B, 8, 6)
    if state == 1: f = stamp(stamp(f, CREST_KINK, 8, 6), LUMP1, 13, 10)
    if state == 2: f = stamp(stamp(stamp(stamp(f, CREST_STUMP, 8, 6), LUMP2, 12, 8), BLACKEYE, 10, 18), PLASTER, 9, 24)
    if wing == 0: f = stamp(f, WING_UP, 1, 14)
    if wing == 1: f = stamp(f, WING_MID, 0, 18)
    if wing == 2: f = stamp(stamp(f, WING_DOWN, 0, 21), FEET_KICK, 6, 30)
    return f


# fix 3: lean pose, typed as its own frame. Head stays over the beak, belly and feet swing 6 px back, crest is
# swept 45 degrees the other way, wing is flung up behind, a tail fan opens as a rudder.
LEAN = g("""
........................
........................
........................
........................
........................
....11..................
....1661................
.....16651..............
......16651.............
.......16651............
........16651...........
.........16651..........
.........1665111........
.........166655411......
........16666555441.....
......1666555554441.....
......1666555554441.....
......1665553343341.....
......165433ff43ff21....
......15543fff4fff21....
......15443ff14ff121....
......1444336143619981..
....14443333333227c71...
....14433333233228871...
...14333233222211.......
...1433323322221........
..1332332222221.........
...13232222221..........
..122222211.............
...111111...............
..7...7.................
.89..89.................
""", 24)
WING_LEAN = [g("""
11.....
191....
1981...
.1981..
.19871.
..18771
..18771
...111.
""", 7), g("""
.......
11.....
1911...
.19811.
..19871
..18771
...1771
...111.
""", 7)]                      # at (0, 9)
TAIL_FAN = g("""
.11..
1991.
.1981
19871
.111.
""", 5)                       # at (0, 19)
FEET_LEAN_B = g("""
___7__7_
__98_98_
""", 8)                       # at (0, 30)
LEAN_KINK = g("""
______
_1111_
""", 6)                       # at (4, 5)
LEAN_STUMP = g("""
_________
_________
_________
_________
____11111
""", 9)                       # at (4, 5)


def lean2(state, k):
    f = stamp(stamp(stamp(LEAN, BEAK_SCREAM, 17, 19), WING_LEAN[k], 0, 9), TAIL_FAN, 0, 19)
    if k: f = stamp(f, FEET_LEAN_B, 0, 30)
    if state == 1: f = stamp(stamp(f, LEAN_KINK, 4, 5), LUMP1, 14, 10)
    if state == 2: f = stamp(stamp(stamp(stamp(f, LEAN_STUMP, 4, 5), LUMP2, 13, 8), BLACKEYE, 10, 18), PLASTER, 7, 24)
    return f


# fix 1: the burst gum. A torn skin stuck to the upper beak by one stretched strand, streaming up in the wind:
# a flat wavy sheet with split, uneven tatters, a notch and a torn hole; four flutter frames (whip right, up, left, up).
SKIN = [g("""
................
.........11.....
........1dc1.11.
.......1dccb1dc1
.......1ccb1dcb1
......1dccbdccb1
......1cc11ccba1
.....1dcc1.1cb1.
.....1ccb1..11..
....1dccbd1.....
....1ccccdc1....
....1bcbccdc1...
....1ab11bccb1..
.....1b1.1ccb1..
.....1bb11cba1..
.....1abccba1...
......1bccb1....
......1abcb1....
......1bca1.....
......1bc1......
......1bc1......
......1c1.......
""", 16), g("""
................
.......11.......
......1dc1.1....
......1ccb11d1..
.....1dccb1dc1..
.....1dccbdcb1..
.....1ccc1ccb1..
....1dccb11ca1..
....1dccb1.11...
...1dcccbd1.....
...1ccccccd1....
...1bccbccdc1...
...1abc11bccb1..
....1ab1.1ccb1..
....1abb11cba1..
.....1abccba1...
.....1abccb1....
......1abcb1....
......1bca1.....
.......1bc1.....
.......1bc1.....
......1c1.......
""", 16), g("""
................
..11............
.1dc1..11.......
.1ccb11dc1......
.1bccd1ccb1.....
..1bccdccb1.....
..1abc11ccb1....
...1b1.1ccb1....
...11..1dccb1...
......1dcccb1...
.....1dccccb1...
....1dccbccb1...
....1ccb11cb1...
....1cb1.1ba1...
....1bcb11b1....
....1abccba1....
.....1bccb1.....
.....1abcb1.....
......1bca1.....
......1bc1......
......1bc1......
......1c1.......
""", 16), g("""
.........1......
.....11.1d1.....
....1dc1.1......
....1ccb1.11....
....1bcc11dc1...
.....1bcddcb1...
.....1bccccb1...
....1dcc11cb1...
....1ccb1.11....
....1cccd1......
....1bcccd1.....
....1bcbccd1....
....1ab11ccb1...
.....1b1.1cb1...
.....1bb11ba1...
.....1abccb1....
......1bccb1....
......1abcb1....
......1bca1.....
......1bc1......
.......1bc1.....
......1c1.......
""", 16)]
STRAND = [g("""
......1d1.......
.......1d1......
.......1c1......
.......1d1......
......1d1.......
......1c1.......
.......1d1......
.......1d1......
........1d1.....
........1c1.....
""", 16), g("""
......1d1.......
.....1d1........
.....1c1........
......1d1.......
.......1d1......
........1d1.....
........1c1.....
.......1d1......
........1d1.....
........1c1.....
""", 16)]
RAG2 = [SKIN[i] + STRAND[i % 2] for i in range(4)]     # 16 x 32, strand foot at grid (9, 31)
RAG2_AT = (11, -12)                                    # strand foot on the upper beak, bird (20, 19)
RAG_LIMP = g("""
................
................
....11..........
...1dc11..111...
..1dccbc11cdb1..
.1cbbccbbccbba1.
1abbabbbabbabba1
.11111111111111.
""", 16)                      # after the crash the skin lies limp on the platform

# fix 4: crash. Two frames of splat (pancake, wince), then a dazed loop: flattened dome, bulging mismatched eyes
# (one X, one ring), tongue on the floor, crumpled crest, wings flat out, legs in the air twitching.
SPLAT = g("""
................................
................................
................................
................................
................................
................................
................................
................................
................................
........1111111111111111........
...11111666665555555444411111...
16655555555444444444433333322221
15544444444333333333322222222221
14433333333232322222222222222221
.11332222222222222222222222211..
...11111111111111111111111111...
""", 32)
WINCE = g("""
1..
.1.
1..
""", 3)                       # at (9, 11), flipped at (20, 11)
BEAK_FLAT = g("""
199881
111111
""", 6)                       # at (13, 12)
IMPACT = g("""
................................
......f..................f......
.......f................f.......
................................
..f..........................f..
...ff......................ff...
................................
................................
""", 32)
DAZE = g("""
................................
............11..................
...........1661.11..............
............16511651............
.........11111655165111.........
......11666665555555444411......
....116666655555555544444411....
..1166655555555555444444442211..
.166555555555444444444444433221.
.155555444444444433333333332221.
.155444444444333333333232322221.
.144444333333333333232222222221.
.144333333323232222222222222221.
..1333322222222222222222222221..
...11222222222222222222222211...
.....1111111111111111111111.....
""", 32)
EYE_X = g("""
.11111.
1fffff1
1f1f1f1
1ff1ff1
1f1f1f1
1fffff1
.11111.
""", 7)                       # at (7, 4)
EYE_RING = g("""
.11111.
1fffff1
1f111f1
1f1f1f1
1f111f1
1fffff1
.11111.
""", 7)                       # at (17, 3): sits higher, bulges over the silhouette
BEAK_DAZE = g("""
.11111.
1998871
17ccc71
.1dc1..
.1cc1..
..11...
""", 7)                       # at (12, 10)
WING_FLAT = g("""
..11..
.1981.
198771
.1111.
""", 6)                       # at (0, 9), flipped at (26, 9)
LEGS_UP = [g("""
.89.89
..7..7
..7..7
..7..7
.....7
""", 6), g("""
......
89..89
.7...7
..7..7
.....7
""", 6)]                      # at (22, 1)
STAR_BIG = g("""
..9..
.9f9.
9fff9
.9f9.
..9..
""", 5)
STAR_SMALL = g("""
.9.
9f9
.9.
""", 3)
FEATHER = g("""
..65
.654
654.
4...
""", 4)
ORBIT = [(10, 0), (7, 2), (0, 3), (-7, 2), (-10, 0), (-7, -2), (0, -3), (7, -2)]   # hand-listed halo path


def splat_frame():
    return stamp(stamp(stamp(SPLAT, WINCE, 9, 11), flip(WINCE), 20, 11), BEAK_FLAT, 13, 12)


def daze_frame(k):
    f = stamp(stamp(DAZE, WING_FLAT, 0, 9), flip(WING_FLAT), 26, 9)
    f = stamp(stamp(stamp(f, EYE_X, 7, 4), EYE_RING, 17, 3), BEAK_DAZE, 12, 10)
    return stamp(f, LEGS_UP[k], 22, 1)


def shield2(frame):
    """review fix: the dotted inner ring ran all the way round (read as a marquee). Dots now only on the lit
    upper-left arc and the reflected lower-right arc."""
    nod = lambda r: r.replace(".a", "..")
    top = [r + nod(r)[::-1] for r in QUAD]
    bot = [(nod(r) + r[::-1]).translate(DARKER) for r in QUAD][::-1]
    grid = stamp(top + bot, GLOSS, 12 + frame, 9)
    grid = stamp(grid, RIMLIGHT, 31, 35 - frame)
    return stamp(grid, SPECK, 33 - 2 * frame, 11 + frame)


GLOB = g("""
.111.
1a971
19771
17751
.111.
""", 5)
DROPLET = g("""
.1.
171
.1.
""", 3)
SPRAY = [(38, 13, 1, -2), (47, 22, 2, -1), (47, 37, 2, 1), (38, 46, 1, 2),
         (21, 46, -1, 2), (12, 37, -2, 1), (12, 22, -2, -1), (21, 13, -1, -2)]   # hand-listed: x, y, step x, step y


def shield_pop2(k):
    """review fix: frame 0 was a flat white ring; now the rim keeps its shading and only jumps brighter.
    Frames 1..3 add gum globs and droplets sprayed between the rim shards, so the burst reads as gum."""
    if k == 0: return [r.translate(str.maketrans("45679a", "679abb")) for r in shield2(0)]
    grid = shield_pop(k)
    for i, (x, y, sx, sy) in enumerate(SPRAY):
        st = GLOB if (i % 2 == 0 and k < 3) else DROPLET
        grid = stamp(grid, st, x + 2 * k * sx, y + 2 * k * sy)
    return grid


def tiles(*ims):
    """unique non-empty 16 x 16 tiles, cells padded right / down. Exact duplicates fold, flips do not."""
    seen = set()
    for im in ims:
        p = Image.new("RGBA", (-(-im.width // 16) * 16, -(-im.height // 16) * 16)); p.paste(im, (0, 0))
        for y in range(0, p.height, 16):
            for x in range(0, p.width, 16):
                t = p.crop((x, y, x + 16, y + 16))
                if t.getbbox(): seen.add(t.tobytes())
    return len(seen)


def main():
    WSEQ = (0, 1, 2, 1)
    E = lambda w, h: Image.new("RGBA", (w, h), (0, 0, 0, 0))
    # ---- bird
    falls = [[img(fall2(w, s, w == 1), BIRD) for w in range(3)] for s in range(3)]
    leans = [[img(lean2(s, k), BIRD) for k in range(2)] for s in range(3)]
    bonk, splat = img(BONK, BIRD), img(splat_frame(), BIRD)
    dazes = [img(daze_frame(k), BIRD) for k in range(2)]
    rags, limp, impact = [img(r, BIRD) for r in RAG2], img(RAG_LIMP, BIRD), img(IMPACT, BIRD)
    stars = [img(STAR_BIG, BIRD), img(STAR_SMALL, BIRD)]
    feas = [img(FEATHER, BIRD), img(flip(FEATHER), BIRD)]
    FDRIFT = [(1, 40), (33, 16)]                         # loose feathers, left behind upward at 12 px a frame

    def cell(bird, t, rag=True, state=0, left=False):
        """bird at (4, 14) in a 40 x 48 cell, rag streaming above it, loose feathers for battered states."""
        c = E(40, 48)
        for i in range(state):
            x, y = FDRIFT[i]; c.alpha_composite(feas[(t + i) % 2], (x, (y - 12 * t) % 48 * 44 // 48))
        c.alpha_composite(bird, (4, 14))
        if rag: c.alpha_composite(rags[t % 4], (4 + RAG2_AT[0], 14 + RAG2_AT[1]))
        return c.transpose(Image.FLIP_LEFT_RIGHT) if left else c

    def halo(c, cx, cy, t):
        for ph in (0, 3, 5):
            x, y = ORBIT[(t + ph) % 8]; s = stars[0 if y >= 0 else 1]
            c.alpha_composite(s, (cx + x - s.width // 2, cy + y - s.height // 2))

    def old_cell(frame, t):                              # first-pass look, for the comparisons only
        c = E(40, 48); c.alpha_composite(img(RAG[(0, 1, 0, 2)[t % 4]], BIRD), (4 + RAG_AT[0], 14 + RAG_AT[1]))
        c.alpha_composite(img(frame, BIRD), (4, 14)); return c

    gap = E(10, 8)
    save(strip([f for row in falls for f in row] + [f for row in leans for f in row] + [bonk, splat] + dazes
               + rags + [limp] + stars + feas), "bird_sheet")
    save(strip([cell(falls[s][0], 0, state=s) for s in range(3)] + dazes[:1]), "battered", (1, 4))
    # old vs new, one image per fix
    save(strip([img(r, BIRD) for r in RAG] + [old_cell(fall_frame(0, 0), 0), gap] + rags + [cell(falls[0][0], 0)]),
         "cmp_rag", (1, 4))
    save(strip([img(fall_frame(0, 0), BIRD), gap] + falls[0]), "cmp_beak", (1, 4))
    save(strip([img(lean_frame(0), BIRD), gap] + leans[0] + [leans[0][0].transpose(Image.FLIP_LEFT_RIGHT)]),
         "cmp_lean", (1, 4))
    save(strip([img(CRASH, BIRD), gap, splat] + dazes), "cmp_crash", (1, 4))
    for s in range(3):
        gif([panel(cell(falls[s][WSEQ[t % 4]], t, state=s)) for t in range(4)], f"anim_fall_state{s}", 66, 4)
    lr = [panel(cell(leans[0][t // 2 % 2], t)) for t in range(4)]
    gif(lr, "anim_lean_right", 66, 4)
    gif([i.transpose(Image.FLIP_LEFT_RIGHT) for i in lr], "anim_lean_left", 66, 4)
    bk = []
    for t in range(8):                                   # ~0.5 s: bounce up off the platform, hang, stars circle
        c = E(40, 56); dy = (0, -4, -6, -7, -7, -6, -4, -1)[t]
        c.alpha_composite(bonk, (4, 22 + dy)); c.alpha_composite(rags[t % 4], (15, 11 + dy))
        halo(c, 15, 33 + dy, t); bk.append(panel(c))
    bk += [panel(cell(falls[1][WSEQ[t % 4]], t, state=1).crop((0, -8, 40, 48))) for t in range(4)]
    gif(bk, "anim_bonk", 66, 4)
    cr = []
    FALLS = [(10, 2), (44, 8), (27, -8)]                 # feathers knocked loose, drifting down
    for t in range(12):
        c = E(64, 64); c.alpha_composite(platform("rock", 2), (0, 44))
        if t < 2:
            c.alpha_composite(splat, (16, 32))
            if t == 0: c.alpha_composite(impact, (16, 30))
        else:
            c.alpha_composite(dazes[t // 2 % 2], (16, 32)); halo(c, 31, 28, t)
        c.alpha_composite(limp, (47, 40))
        for i, (x, y) in enumerate(FALLS):
            fy = y + 4 * t
            if 0 <= fy < 42: c.alpha_composite(feas[(t + i) // 2 % 2], (x + (1, 0, -1, 0)[(t + i) % 4], fy))
        cr.append(panel(c))
    gif(cr, "anim_crash", 120, 4)
    # ---- platforms (speed look A only: streak tiles)
    kinds = [("rock", 2), ("girder", 3), ("plank", 1)]
    ptiles = [img(t, PLAT) for k in PTYPES.values() for t in k] + [img(STREAK_A, PLAT), img(STREAK_B, PLAT)]
    save(strip(ptiles), "platform_tiles")
    save(strip([platform_fast(k, m, mode) for mode in range(2) for k, m in kinds], 6), "platforms_speed", (1, 3))
    fr = []
    for t in range(12):
        c = Image.new("RGBA", (200, 120), PANEL)
        for i, (k, m) in enumerate(kinds):
            c.alpha_composite(platform_fast(k, m, 1), ((8, 84, 150)[i], 120 - (t * 14 + i * 50) % 168))
        fr.append(c)
    gif(fr, "anim_platforms_streaks", 33, 3)
    # ---- pickup (existing Gum Trip sheet, reused unchanged)
    PJ = json.load(open(f"{ROOT}/assets/trippickup/trippickup_sheet.json"))
    anims = {k: sheet_frames(f"{ROOT}/assets/trippickup/trippickup_sheet.png", v) for k, v in PJ["animations"].items()}
    idle = anims["pickup_idle"]; coll = [v for k, v in anims.items() if k != "pickup_idle"][0]
    save(strip(idle + coll), "pickup_reused", (1, 3))
    gif([panel(f, 8) for f in idle], "anim_pickup_spin", 66, 4)
    gif([panel(f, 8) for f in coll] + [panel(Image.new("RGBA", coll[0].size), 8)] * 3, "anim_pickup_catch", 66, 4)
    # ---- shield: the caught gum blows a fresh bubble, so the torn skin is hidden while the shield is up
    sh = [img(shield2(f), GUM) for f in range(2)]
    pops = [img(shield_pop2(k), GUM) for k in range(4)]
    save(strip(sh + pops), "shield_sheet")

    def shielded(t, bubble=None, rag=False, state=1):
        c = E(64, 64); c.alpha_composite(falls[state][WSEQ[t % 4]], (20, 16))
        if rag: c.alpha_composite(rags[t % 4], (20 + RAG2_AT[0], 16 + RAG2_AT[1]))
        if bubble: c.alpha_composite(bubble, ((64 - bubble.width) // 2, (64 - bubble.height) // 2))
        return c
    gif([panel(shielded(t, sh[t // 2 % 2])) for t in range(8)], "anim_shield", 66, 4)
    gif([panel(shielded(t, sh[t // 2 % 2])) for t in range(4)] + [panel(shielded(4, pops[0]))]
        + [panel(shielded(4 + k, pops[k], True)) for k in range(1, 4)]
        + [panel(shielded(t, None, True)) for t in range(4)], "anim_shield_pop", 66, 4)
    save(strip([shielded(0, sh[0]), shielded(0, pops[0])] + [shielded(k, pops[k], True) for k in range(1, 4)]),
         "shield_on_bird", (1, 4))

    # ---- mock-up, 320 x 224
    sky = Image.open(f"{HERE}/../2026-11-10-backgrounds-final/plane_dusk_sky_1x.png").convert("RGBA")
    back = Image.new("RGBA", (320, 224), PLAT[0] + (255,))
    back.paste(sky.crop((0, 0, 320, min(sky.height, 112))), (0, 0))
    low = sky.crop((0, 0, 160, min(sky.height, 112))).transpose(Image.FLIP_TOP_BOTTOM)   # sun-free left half, mirrored
    back.paste(low, (0, 112)); back.paste(low.transpose(Image.FLIP_LEFT_RIGHT), (160, 112))
    wisp = img(WISP, PLAT)
    LAYOUT = [("rock", 2, 20, 30), ("girder", 3, 200, 70), ("plank", 1, 120, 120), ("rock", 3, 232, 170),
              ("girder", 2, 30, 200), ("plank", 2, 150, 250), ("rock", 1, 96, 40)]         # kind, mids, x, y0
    GUMS = [(90, 80), (186, 20), (270, 120), (60, 150), (200, 215), (130, 190), (300, 40)]
    WISPS = [(10, 20), (250, 60), (130, 100), (40, 170), (200, 150), (280, 200), (90, 230)]
    WRAP = 288

    def mock(t, state=1, bubble=None):
        """32-frame loop: fall, steer right (lean), fall, steer left (the same lean frames H-flipped)."""
        c = back.copy()
        for x, y in WISPS: c.alpha_composite(wisp, (x, (y - t * 3) % WRAP - 32))
        for i, (x, y) in enumerate(GUMS): c.alpha_composite(idle[(t + 3 * i) % len(idle)], (x, (y - t * 9) % WRAP - 32))
        for k, m, x, y in LAYOUT: c.alpha_composite(platform_fast(k, m, 1), (x, (y - t * 9) % WRAP - 40))
        ph = t // 8 % 4
        bx = 136 + (0, 0, 24, 24)[ph] + (0, 3, 0, -3)[ph] * (t % 8)
        b = falls[state][WSEQ[t % 4]] if ph % 2 == 0 else leans[state][t // 2 % 2]
        b = cell(b, t, rag=bubble is None, state=state, left=ph == 3)
        c.alpha_composite(b, (bx - (8 if ph == 3 else 0), 36))
        if bubble: c.alpha_composite(bubble, (bx + 16 - 24, 36 + 30 - 24))
        d = ImageDraw.Draw(c)                          # placeholder head-up display, not final lettering
        c.alpha_composite(idle[0], (6, 2)); d.text((32, 8), "07", fill=(255, 255, 255))
        for i in range(3): d.rectangle((280 + i * 12, 8, 288 + i * 12, 16), fill=GUM[6] if i >= state else GUM[1], outline=PLAT[0])
        d.text((136, 8), "0412 m", fill=(255, 255, 255))
        return c
    save(mock(5), "mock_streaks", (1, 3)); save(mock(12), "mock_lean", (1, 3)); save(mock(5, 2, sh[0]), "mock_shield", (1, 3))
    gif([mock(t) for t in range(32)], "anim_mock_streaks", 33, 2)
    gif([mock(t, 2, sh[t // 2 % 2]) for t in range(32)], "anim_mock_shield", 33, 2)

    # ---- self-check: palette budgets, cell sizes, tile counts
    birds = [f for r in falls for f in r] + [f for r in leans for f in r] + [bonk]
    counts = {"bird (existing player palette)": ncol(*birds, splat, *dazes, *rags, limp, *stars, *feas, impact),
              "platforms + streaks": ncol(*ptiles, wisp),
              "shield (existing gum palette)": ncol(*sh, *pops), "pickup (existing, reused)": ncol(*idle, *coll)}
    for k, v in counts.items(): assert v <= 15, (k, v)
    assert all(len(f) == 32 and len(f[0]) == 24 for f in (BODY, BONK, LEAN)) and len(QUAD) == 24
    assert all(len(f) == 16 and len(f[0]) == 32 for f in (SPLAT, DAZE)) and all(len(r) == 32 for r in RAG2)
    tl = {"bird: 9 fall (3 wing x 3 battered), 6 lean (2 x 3), 1 hit, 24 x 32 each": tiles(*birds),
          "crash: splat + 2 dazed, 32 x 16 each": tiles(splat, *dazes),
          "torn gum skin: 4 flutter frames 16 x 32, 1 limp": tiles(*rags, limp),
          "stun stars 2, feather 2 (flip), impact dashes": tiles(*stars, feas[0], impact),
          "platforms: 3 types x (cap + middle), 2 streak tiles, 1 wisp": tiles(*ptiles, wisp),
          "shield: 2 bubble frames 48 x 48, 4 pop frames (mirror symmetric, flips not folded)": tiles(*sh, *pops),
          "gum pickup + catch: reused Gum Trip tiles": 0}
    lines = [f"{k}: {v} colours" for k, v in counts.items()] + ["", "tiles (unique non-empty 16 x 16, flips not folded):"]
    lines += [f"  {k}: {v}" for k, v in tl.items()] + [f"  TOTAL new tiles: {sum(tl.values())}"]
    open(f"{HERE}/numbers.txt", "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
