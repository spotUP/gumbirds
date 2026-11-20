#!/usr/bin/env python3.14
"""Pop Drop fun extras, DRAFTS 2026-11-20: brake hop, feather loss + half bald bird, bubble parachute (2 takes),
gum on eyes, bandaged ghost bird (2 takes), bump squawk.
Same 24 x 32 bird box, bird palette and outline as assets/popdrop/popdrop_sheet.json (terror take A is the base).
Every pixel is a hand-typed grid or stamp; only WHERE a stamp sits is listed by hand. No game code, no import.
Run: python3.14 -I draw_fun.py
"""
import os, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "../2026-11-20-popdrop-terror"))
import draw_terror as t  # noqa: E402
d = t.d
d.HERE = HERE
g, stamp, img, flip, blank = d.g, d.stamp, d.img, d.flip, d.blank
PLAYER, CPU = t.PLAYER, t.CPU
GUM_A = d.GUM                                             # take A: the in-game gum palette, unchanged
GUM_B = [(8, 8, 24), (107, 16, 132), (156, 33, 74), (198, 49, 90), (231, 82, 115), (247, 115, 140), (255, 148, 165),
         (255, 181, 189), (255, 206, 206), (255, 231, 222), (255, 255, 255), (140, 214, 255)]   # take B: candy pink
SPIRIT = [(41, 49, 107), (74, 90, 165), (107, 132, 206), (148, 181, 231), (198, 222, 247), (239, 247, 255),
          (90, 74, 148), (165, 148, 214), (222, 214, 247), (165, 41, 57), (231, 90, 74), (255, 156, 123),
          (255, 82, 181), (255, 165, 222), (255, 255, 255)]                                     # ghost take A palette swap


def gx(text):
    """strict grid: every row typed to full width"""
    rows = [r.strip() for r in text.strip().split("\n")]
    assert len({len(r) for r in rows}) == 1, [(i, len(r)) for i, r in enumerate(rows)]
    return rows


def many(f, lst):
    for st, x, y in lst: f = stamp(f, st, x, y)
    return f


# ================================================================== 1. BRAKE HOP (4 frames)
WING_PUMP = g("""
...11111.
..1998871
.19888771
198877711
19877171.
1987171..
198171...
1811.....
11.......
""", 9)                       # at (0, 20): wing slammed down, three feather fingers splayed
FAR_PUMP = g("""
111..
18811
.1881
..171
...1.
""", 5)                       # at (19, 25)
AIR = g("""
6.....
f6..6.
.f6.f6
""", 6)                       # at (0, 29): air kicked down by the stroke
EYES_HOPE = g("""
....111....
..11f1f11..
.1f1f1f1f1.
1ff1f1f1ff1
1ffff1ffff1
1ffff1ffff1
16fff1fff61
.166616661.
..11131112.
....33..22.
""", 11)                      # at (8, 12): terror eyes, pupils rolled up (looks at its wings / the bubble)
EYES_SHUT = g("""
....111....
..1161611..
.166615661.
16666166661
16665166651
11551111551
15115151151
.144414441.
..11131112.
....33..22.
""", 11)                      # at (8, 12): same eye bulges, lids squeezed shut (strain, blowing)


def hop(k, state=0):
    f = t.base(0, state, t.CREST_FAN)
    if k < 2: f = stamp(stamp(f, EYES_SHUT, 8, 12), t.BEAK_C[k], 17, 20)          # strain, eyes screwed shut
    else: f = stamp(stamp(f, t.EYES_A if k == 2 else EYES_HOPE, 8, 12), t.BEAK_B[k % 2], 17, 19)
    if k == 0: f = many(f, [(d.WING_DOWN, 0, 21), (t.FEET_TUCK, 8, 30)])
    if k == 1: f = many(f, [(t.WING_HI, 0, 6), (t.FAR_HI, 18, 8), (t.FEET_TUCK, 8, 30)])
    if k == 2: f = many(f, [(WING_PUMP, 0, 20), (FAR_PUMP, 19, 25), (d.FEET_KICK, 6, 30), (AIR, 0, 29)])
    if k == 3: f = many(f, [(d.WING_MID, 0, 18), (t.FAR_MID, 19, 13), (t.DROP, 2, 9)])
    return f


# ================================================================== 2. FEATHER LOSS
F_A = g("""
....11.
...1651
..16541
.16541.
165411.
1411...
.1.....
""", 7)
F_B = g("""
..11111.
.1666551
16555441
.11111..
""", 8)
F_D = g("""
.11.
1651
1651
1651
1541
1541
.14.
.1..
""", 4)
FEA = {"A": F_A, "B": F_B, "C": flip(F_A), "D": F_D}
ROT = "ABCD"
FLUFF = g("""
.6.
6f6
.6.
""", 3)
DOT = ["6"]
PUFF0 = g("""
....1.....1...
.1.161...161..
161.1ff1ff1.1.
.1.1ffffff6161
..1ff6fffff61.
.1ffffff6ff61.
..16ff6ffff1..
.1.1666f661.1.
161.116611.161
.1....11....1.
""", 14)
PUFF1 = g("""
...6..6...
.6......6.
....ff....
6..f66f..6
....ff....
.6......6.
...6..6...
""", 10)
# six feathers, each a hand-listed path (frame 1..5) in a 44 x 44 cell; the quill turns one step a frame
PATHS = [("A", [(24, 10), (28, 7), (30, 4), (31, 1)]), ("B", [(27, 18), (31, 17), (33, 14), (34, 10), (33, 6)]),
         ("C", [(24, 24), (28, 25), (30, 23), (31, 19), (30, 15)]), ("D", [(15, 27), (14, 30), (12, 29), (11, 26), (12, 22)]),
         ("A", [(7, 22), (3, 23), (1, 21), (0, 17), (1, 13)]), ("C", [(8, 10), (4, 8), (2, 5), (1, 1)])]
FLUFFS = {1: [(18, 12), (27, 23), (12, 19)], 2: [(16, 8), (30, 26), (8, 17), (22, 31)], 3: [(15, 4), (33, 28), (5, 14)],
          4: [(14, 1), (36, 29)], 5: [(20, 3)]}


def burst(k):
    f = blank(44, 44)
    if k == 0: return stamp(f, PUFF0, 15, 17)
    if k == 1: f = stamp(f, PUFF1, 17, 19)
    for start, path in PATHS:
        if k - 1 < len(path):
            x, y = path[k - 1]
            f = stamp(f, FEA[ROT[(ROT.index(start) + k - 1) % 4]], x + 2, y + 2)
    for x, y in FLUFFS[k]: f = stamp(f, FLUFF if k < 3 else DOT, x + 2, y + 2)
    return f


BALD = gx("""
........................
........................
........................
........................
........................
............1...........
...........1....1.......
..........1....1........
..........1...1.........
........1111111.........
.......1feeeecb1........
......1effeeeecb1.......
......1eefeeeeeccb1.....
......1eeccccccccb1.....
......1ecccccccccc1.....
......1ecccccccccccc....
......1cccccccccccc.....
......1cccccccccccc.....
......1bccccccccccc.....
......1ecccccccccccb1...
......1eecccceeccbb1....
.....1eeccccccefecb1....
.....1ecacccccceecb1....
.....1cccccccccaebb1....
......1cccccccceccb1....
......1cacccceecbba1....
......15c5c4c4c3c21.....
.......15454433321......
........144332211.......
.........111111.........
..........7..7..........
.........89..89.........
""")                          # v2: bald pink dome with a shine and two last hairs, bare chest and belly (skin c, light e,
                              # shade b, stubble a), feathers left only as ragged shorts; knees together
                              # v3: lit skin moved to gum pink e with white f glints (hue and value away from the wing
                              # orange 8/9); salmon c is now the half shade only
EYES_SHY = g("""
....111....
..1161611..
.166615661.
16666166661
16665166651
11551111551
15115151151
.1ed414de1.
..111.111..
""", 11)                      # at (8, 12): same big lids as the in-game shut eyes, squeezed, hot blush under each
# wings: the in-game folded wing twice, far one at (8, 21) under the near one at (4, 20), hugging the chest
PEEK = g("""
1111
11ff
ffff
""", 4)                       # at (14, 16): the front eye half opens, pupil slides back to see who is looking
HAIR = g("""
.1.....
1....1.
1...1..
.1..1..
""", 7)                       # at (10, 5): the two hairs droop the other way on the peek frame


def bald(k):
    f = many(BALD, [(EYES_SHY, 8, 12), (flip(d.WING_MID), 8, 21), (d.WING_MID, 4 - k, 20), (t.BEAK_C[k], 17, 20)])
    if k: f = many(f, [(["_______"] * 4, 10, 5), (HAIR, 9, 5), (PEEK, 14, 16), (t.DROP, 2, 13),
                       (t.SPECK, 20, 10)])
    return f


# ================================================================== 3. BUBBLE PARACHUTE (gum palette)
BUB = [gx("""
..3333..
.389983.
38ab9873
39b98873
38988763
38877653
.376653.
..3333..
"""), gx("""
....3333....
..33899833..
.3899a99873.
.39abb98873.
389ab9988763
39a998887763
398988877663
388887776653
.3878776653.
.3777666553.
..33665533..
....3333....
"""), gx("""
......333333......
....3389999833....
...389999999873...
..39a9a999988873..
.39abba9999888873.
.3abbba9998888773.
39abba999888887763
39aba9998888877663
39a999988888777663
399998988887777663
398989888878777653
388888888787776653
.3888878777776653.
.3878777777666553.
..37777767666553..
...376766665553...
....3366655533....
......333333......
"""), gx("""
........33333333........
......338999999833......
....3389999999998833....
...38999a9a9999988873...
..399a9aaba99999888873..
..39aaabbbba9999888873..
.39aabbbbaa999988888773.
.3aabbbaa99999888888773.
39abbba99999988888877663
39abba999999888888877663
39aba9999998988888777663
39aa99999989888888777663
399999998988888887777653
399998989888888787777653
398989888888887877776653
389888888888787777766553
.3888888888787777766553.
.3888888787777776766553.
..38878777777767666553..
..37877777776766665543..
...377777676666655543...
....3376766666555433....
......336666555533......
........33333333........
""")]                         # four sizes 8 / 12 / 18 / 24: light upper left, dithered turn, deep lower right
WIN_S = g("""
bb
bb
""", 2)
WIN_M = g("""
bb.b
bb.b
....
bb.b
""", 4)
WIN_L = g("""
.bb.bb
bbb.bb
bbb.bb
......
bbb.bb
.bb.b.
""", 6)
CY = g("""
...c
..c.
cc..
""", 4)
CY_L = g("""
.....c
....cc
...cc.
.ccc..
""", 6)
SHINE_A = [[], [], [(d.RIMLIGHT, 10, 11)], [(d.SPECK, 16, 3), (d.RIMLIGHT, 15, 16)]]          # soft crescent, sparkle
SHINE_B = [[(["b"], 2, 2)], [(WIN_S, 3, 3)], [(WIN_M, 4, 4), (CY, 11, 11)], [(WIN_L, 5, 5), (CY_L, 15, 15)]]
FLAT = str.maketrans("ab", "99")
STRAND = g("""
.73
.73
.73
73.
73.
73.
.73
.73
.73
.73
73.
73.
73.
.73
.73
.73
.73
.73
""", 3)
BUB_AT = [(19, 12), (17, 8), (12, -6), (8, -22)]          # bubble top-left in bird coordinates
GUMPAL = {"a": GUM_A, "b": GUM_B}


def bubble(size, take):
    grid = BUB[size] if take == "a" else [r.translate(FLAT) for r in BUB[size]]
    return many(grid, (SHINE_A if take == "a" else SHINE_B)[size])


S_TL = g("""
..378
.379.
379..
37...
""", 5)
TAT = g("""
3773..
.39873
..33..
""", 6)
SPK_V = ["b", "a", "9"]
SPK_H = ["9ab"]
SPK_D = g("""
b.
.a
""", 2)
BRIGHT = str.maketrans("56789a", "789abb")


# ---- v2 pop: the skin tears into thick shreds that fly out, slow, sag and drop; strands stretch, thin and snap;
# ---- the core glob falls onto the bird's face (gum on eyes follows). Stamps hand-typed, places hand-listed per frame.
ARC = g("""
.....3333.
...33a9983
..3ab99833
.3ab9983..
.3a9983...
3a9983....
399873....
39883.....
3873......
.33.......
""", 10)                      # quarter of the burst skin, 3 px thick
ARC_S = g("""
...333.
..3a983
.3a983.
3a983..
3983...
383....
.3.....
""", 7)                       # the same shred curled smaller
FLAP = g("""
..3333..
.3a9983.
3ab99873
.3998763
..38873.
...333..
""", 8)
CORE = g("""
...3.....
..383..3.
.3a983383
3ab998873
.39988763
..388763.
.3873.33.
..33.....
""", 9)                       # ragged middle of the skin, becomes the falling glob
GLOB_T = g("""
..3..
..3..
.383.
.383.
3a983
39873
38763
.333.
""", 5)                       # falling glob with its tail pulled up
DIAG = g("""
98......
.87.....
..87....
...7....
....7...
.....7..
......87
.......8
""", 8)
DIAG_L = g("""
9...........
.8..........
..8.........
...7........
....7.......
.....7......
......7.....
.......7....
........7...
.........8..
..........8.
...........9
""", 12)
SAG = g("""
9........9
.88....88.
...7777...
""", 10)
SAG_L = g("""
8..............8
.87..........78.
...77......77...
.....777777.....
""", 16)
SNAP = g("""
8....
.7...
..7..
...73
...33
""", 5)                       # snapped strand end with its bead
WEB = g("""
a98.....
98987...
.98877..
..8877..
...8777.
....877.
.....78.
......7.
""", 8)                       # v3: thick membrane still holding one quarter, tapers toward the core
KINK = g("""
98.......
.887.....
...87....
....7....
....7....
.....78..
.......89
""", 9)                       # v3: strand with a kink, thick at both ends
CURL = g("""
.3333.
3a9983
39833.
3983..
38763.
.3333.
""", 6)                       # v3: shred curled into a C
RIBBON = g("""
.33..
3a93.
3983.
.3983
..383
.3873
3a83.
3983.
.33..
""", 5)                       # v3: twisting ribbon of skin, falling
TEAR = g("""
.3..
.3..
.83.
3983
3a83
3873
.33.
""", 4)                       # v3: fat drop with its tail pulled up
DIM = str.maketrans("ab9876", "998765")
V = lambda s: s[::-1]                                     # noqa: E731
dim = lambda s: [r.translate(DIM) for r in s]             # noqa: E731  shadow side shreds (lower right)
POPS = [
    # 1 tear: four quarters and two flaps still near the 24 px ring, short strands to the core
    # v3: no X. Core hangs low left; a thick web holds the upper left quarter, a kinked thread the upper right,
    # the lower left has snapped to a stub, the lower right is one thin thread. Quarters sit at uneven distances.
    [(WEB, 14, 14), (flip(KINK), 27, 14), (flip(SNAP), 13, 29), (DIAG, 27, 28),
     (ARC, 9, 9), (flip(ARC), 31, 6), (V(ARC), 6, 30), (dim(V(flip(ARC))), 30, 32), (FLAP, 17, 3), (dim(V(FLAP)), 24, 38),
     (TAT, 3, 20), (flip(TAT), 40, 25), (CORE, 18, 22)],
    # 2 fly: fast outward (right side a little further), strands pulled long and thin
    [(DIAG_L, 11, 13), (flip(DIAG_L), 26, 11), (SAG_L, 10, 38), (SAG, 26, 3), (SAG, 11, 4),
     (ARC, 4, 5), (flip(ARC), 36, 3), (V(ARC), 2, 33), (dim(V(flip(ARC))), 36, 36), (FLAP, 19, 0), (dim(V(FLAP)), 23, 42),
     (FLAP, 0, 21), (dim(flip(FLAP)), 40, 24), (GLOB_T, 21, 23)],
    # 3 slow: top shreds at their peak still strung together, lower ones curl and drop, the long strands snap
    [(SAG_L, 9, 4), (SAG_L, 25, 3), (SNAP, 11, 13), (flip(SNAP), 32, 12), (STRAND[-9:], 19, 22),
     "D17,21", "D29,20", "D18,43", "D8,36", "D38,37",
     (ARC, 1, 3), (flip(ARC), 38, 1), (V(ARC_S), 0, 39), (dim(V(flip(ARC_S))), 41, 42), (V(FLAP), 20, 0),
     (V(FLAP), -2, 23), (dim(FLAP), 42, 27), (GLOB_T, 19, 31)],
    # 4 drop: shreds curled small and falling with gum strings trailing above them, beads everywhere
    # v3: more mass. A broken ring of seven chunky shreds (curls, ribbons), two fat drops inside it
    [(STRAND[-6:], 3, 0), (STRAND[-6:], 43, 2), (SNAP, 11, 7), (flip(SNAP), 33, 6), (STRAND[-5:], 17, 32),
     "D15,27", "D31,26", "D27,12", "D9,36", "D39,24",
     (ARC_S, 0, 6), (flip(ARC_S), 41, 8), (CURL, 20, 1), (RIBBON, 1, 26), (dim(flip(RIBBON)), 42, 30),
     (V(CURL), 5, 41), (dim(flip(V(CURL))), 36, 42), (TEAR, 12, 19), (dim(flip(TEAR)), 33, 17),
     (GLOB_T, 17, 37)],
    # 5 rain: last curls and beads, the glob lands on the face
    # v3: the same shreds a step lower and smaller (fat drops, dim curl, short ribbons), not only beads
    [(SNAP, 5, 14), (flip(SNAP), 38, 13), (dim(CURL), 21, 8), (TEAR, 1, 18), (dim(flip(TEAR)), 43, 20),
     (TEAR, 11, 28), (dim(flip(TEAR)), 33, 27), (dim(RIBBON), 2, 36), (dim(flip(RIBBON)), 41, 38),
     "D21,2", "D26,20", "D8,25", "D37,34", "D30,42", "D24,33", "G15,42"]]


def pop(k, take):
    f = blank(48, 48)
    if k == 0:
        f = stamp(f, [r.translate(BRIGHT) for r in bubble(3, take)], 12, 12)
        return many(f, [(SPK_V, 23, 6), (V(SPK_V), 24, 39), (flip(SPK_H), 6, 23), (SPK_H, 39, 24),
                        (SPK_D, 11, 11), (flip(SPK_D), 35, 11), (V(SPK_D), 11, 35), (V(flip(SPK_D)), 35, 35)])
    for it in POPS[k - 1]:
        if isinstance(it, str):                           # "D x,y" droplet / "G x,y" glob: place only
            x, y = map(int, it[1:].split(","))
            it = (d.DROPLET if it[0] == "D" else d.GLOB, x, y)
        f = stamp(f, *it)
    return f


def hang(k):
    """0, 1: blowing, eyes shut. 2, 3: hanging under the bubble by the beak, eyes rolled up at it."""
    f = t.base(0, 0)
    if k < 2: return many(f, [(EYES_SHUT, 8, 12), (t.BEAK_C[k], 17, 20), (d.WING_MID, 0, 18)])
    f = many(f, [(EYES_HOPE, 8, 12), (t.BEAK_C[0], 17, 20), (d.WING_DOWN, 0, 21)])
    return stamp(f, t.FEET_A[0], 8, 30) if k == 3 else f


def shock():
    return many(t.base(0, 0), [(t.EYES_A, 8, 12), (t.BEAK_A[0], 17, 19), (t.WING_HI, 0, 6), (t.FAR_HI, 18, 8)])


GUMFACE = g("""
...1111111...
.11deeeedd11.
1deefeedddd71
1defeedddddd1
1deeedddddd71
1ddddddd7dd71
.1dddd7dd7771
.17dd7177d71.
..1d713317d1.
..1d1333.1d1.
...1.33..21..
""", 13)                      # at (7, 11): gum slapped over both eyes, two drips (bird palette pink d / e, shade 7)
GSTR = g("""
.1.
1e1
1d1
.1.
""", 3)                       # gum fleck flung off


def gumflail(k):
    f = many(t.base(0, 0, t.CREST_FAN), [(t.EYES_A, 8, 12), (GUMFACE, 7, 11), (t.BEAK_A[k], 17, 19)])
    if k == 0: return many(f, [(t.WING_HI, 0, 6), (t.FAR_HI, 18, 8), (t.FEET_A[0], 8, 30), (GSTR, 3, 1)])
    return many(f, [(d.WING_DOWN, 0, 21), (t.FAR_MID, 19, 13), (t.FEET_A[2], 8, 30), (GSTR, 19, 4), (t.SPECK, 2, 12)])


# ================================================================== 4. TWO PLAYER EXTRAS
GHOST = gx("""
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
.........111111.........
.......11ffffff11.......
......1fffff66ff651.....
......1f4466ffff651.11..
.....1ff6ff4466ff6511f61
.....16fffff6ff446511f1.
......1555443343341..1..
......165431f141f121....
......15543f1f4f1f21....
......154431f141f121....
......1444333343339981..
.....14443333333227c71..
.....14433333233228871..
......14333233222211....
......1433323322221.....
.....1433323322221......
....1433233222221.......
...143323222221.........
.1543323222 1...........
165433211...............
.1111111................
""".replace(" ", "2"))        # head bandage with a loose end, crossed-out eyes, body trails off into a wisp
TAILS = [None, gx("""
....14332322221.........
...1543323221...........
..165433211.............
...111111...............
"""), gx("""
....14332322221.........
....154332321...........
....16543311............
.....11111..............
""")]                         # rows 28..31: the wisp tip swings in over three frames
HAND_N = g("""
.11..
1981.
19871
18771
.171.
..1..
""", 5)                       # at (3, 21): little wings held out in front, ghost style
HAND_F = g("""
.111.
19871
18771
.171.
""", 5)                       # at (17, 24)
HALO = g("""
..111111..
.19999981.
1981111891
.18888881.
..111111..
""", 10)                      # at (7, 5), take B
FADE = g("""
....................
_..._..._..._..._...
.._..._..._..._..._.
_._._._._._._._._._.
._._._._._._._._._._
__.___.___.___.___._
.___.___.___.___.___
""", 20)                      # at (0, 25), take B: hand-typed dither, the body thins out to nothing


def ghost(k, take):
    f = GHOST
    if TAILS[k]: f = f[:28] + TAILS[k]
    f = many(f, [(HAND_N, 3, 21 + (k == 2)), (HAND_F, 17, 24 + (k == 2)), (d.PLASTER, 9, 23)])
    if take == "b": f = many(f, [(FADE, 0, 25), (HALO, 7, 5)])
    return f


SQUAWK = g("""
....11.
...1f1.
..1f1..
.......
111111.
1ffff1.
111111.
.......
..1f1..
...1f1.
....11.
""", 7)                       # shout lines, drawn right of the beak
MINI = [[(PUFF1, 5, 6)], [(F_A, 12, 2), (flip(F_A), 1, 3), (F_D, 8, 12), (FLUFF, 9, 7)],
        [(F_B, 12, 0), (F_D, 0, 1), (F_A, 8, 14), (DOT, 10, 8)]]


def squawk(k):
    f = many(t.base(0, 0, t.CREST_FAN), [(t.EYES_A, 8, 12), (t.BEAK_A[k], 17, 19), (t.WING_STIFF[k], 1, 14),
                                         (t.FAR_STIFF, 19, 13), (t.FEET_STIFF, 8, 31)])
    return t.shift(f, 1) if k else f


def mini(k): return many(blank(20, 20), MINI[k])


# ================================================================== output
def main():
    sky = Image.open(f"{HERE}/../2026-11-20-popdrop-sky-v3/b_postcard_sky_1x.png").convert("RGBA")
    AZ = sky.getpixel((160, 110))
    for f in [hop(k) for k in range(4)] + [bald(0), bald(1), hang(0), hang(3), shock(), gumflail(0), gumflail(1),
                                           squawk(0), squawk(1)] + [ghost(k, tk) for k in range(3) for tk in "ab"]:
        assert len(f) == 32 and all(len(r) == 24 for r in f)
    P = lambda grid, pal=PLAYER: img(grid, pal)

    def cell(parts, w, h):
        c = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        for L, x, y in parts: c.paste(L, (x, y), L)
        return c

    def sheet(name, rs, gap=4):
        w = max(sum(i.width + gap for i in r) for r in rs) + gap
        out = Image.new("RGBA", (w, sum(max(i.height for i in r) + gap for r in rs) + gap), AZ); y = gap
        for r in rs:
            x = gap
            for i in r: out.paste(i, (x, y), i); x += i.width + gap
            y += max(i.height for i in r) + gap
        d.save(out, name, (1, 3))

    def scene(parts, w=128, h=108, sx=150, sy=70):
        im = sky.crop((sx, sy, sx + w, sy + h)).copy()
        for L, x, y in parts: im.paste(L, (x, y), L)
        return im

    RX, NX, BY = 12, 76, 62

    def rag(i, x, y, pal=PLAYER): return (P(d.RAG2[i % 4], pal), x + 11, y - 12)

    def ref(i): return [rag(i, RX, BY), (P(t.take_a(0, 0, i % 3)), RX, BY)]

    def birdbub(grid, size, take, pal=PLAYER, x=0, y=0):
        """bird, then strand, then bubble, as scene parts at (x, y)"""
        ps = [(P(grid, pal), x, y)]
        bx, by = BUB_AT[size]
        if size >= 2:
            n = 18 if size == 3 else 8
            ps.append((img(STRAND[-n:], GUMPAL[take]), x + 19, y + 20 - n))
        ps.append((img(bubble(size, take), GUMPAL[take]), x + bx, y + by))
        return ps

    # ---- sheets (row 1 player palette, row 2 computer palette)
    sheet("brake_hop_sheet", [[P(hop(k), p) for k in range(4)] for p in (PLAYER, CPU)])
    sheet("feather_burst_sheet", [[P(burst(k), p) for k in range(6)] for p in (PLAYER, CPU)])
    sheet("half_bald_sheet", [[P(bald(k), p) for k in range(2)] for p in (PLAYER, CPU)])
    for tk in "ab":
        sheet(f"bubble_{tk}_sheet", [
            [cell(birdbub(hang(min(s, 3)), s, tk, x=8, y=24), 44, 58) for s in range(4)],
            [img(pop(k, tk), GUMPAL[tk]) for k in range(6)]])
        sheet(f"ghost_{tk}_sheet", [[P(ghost(k, tk), SPIRIT if tk == "a" else p) for k in range(3)]
                                    for p in ((PLAYER,) if tk == "a" else (PLAYER, CPU))])
    sheet("gum_on_eyes_sheet", [[P(gumflail(k), p) for k in range(2)] for p in (PLAYER, CPU)])
    sheet("bump_squawk_sheet", [[P(squawk(k), p) for k in range(2)] + [P(SQUAWK, p)] + [P(mini(k), p) for k in range(3)]
                                for p in (PLAYER, CPU)])

    # ---- animations at game timing (133 ms a frame), existing terror bird on the left for scale
    seq = [("f", 0, 0), ("f", 1, 0), ("f", 2, 0), ("h", 0, 1), ("h", 1, 2), ("h", 2, -2), ("h", 3, -6),
           ("f", 0, -7), ("f", 1, -5), ("f", 2, -2)]
    d.gif([scene(ref(i) + [rag(i, NX, BY + dy), (P(hop(k) if a == "h" else t.take_a(0, 0, k)), NX, BY + dy)])
           for i, (a, k, dy) in enumerate(seq)], "brake_hop", 133)
    fr = []
    for i in range(16):
        ps = ref(i) + [rag(i, NX, BY)]
        if i < 2: ps.append((P(t.take_a(0, 0, i)), NX, BY))
        elif i < 8: ps += [(P(t.take_a(0, 1, i % 3)), NX, BY), (P(burst(i - 2)), NX - 10, BY - 4)]
        else: ps.append((P(bald((i // 2) % 2)), NX, BY))
        fr.append(scene(ps))
    d.gif(fr, "feather_loss", 133)
    d.gif([scene(ref(i) + [rag(i, NX, BY), (P(bald((i // 2) % 2)), NX, BY)]) for i in range(12)], "half_bald", 133)
    rise = [0, 0, -1, -3, -5, -7, -8, -8, -8, -8, -8, -8, -7, -5, -2, 0, 0]   # hangs in the air while the gum bursts
    for tk in "ab":
        fr = []
        for i, dy in enumerate(rise):
            y = BY + dy
            if i < 3: ps = birdbub(hang(i), i, tk, x=NX, y=y)
            elif i < 7: ps = birdbub(hang(2 + i % 2), 3, tk, x=NX, y=y)
            elif i < 13: ps = [(P(shock() if i < 12 else gumflail(0)), NX, y), (img(pop(i - 7, tk), GUMPAL[tk]), NX - 4, BY - 42)]
            else: ps = [(P(gumflail(i % 2)), NX, y)]
            fr.append(scene(ref(i) + ps))
        d.gif(fr, f"bubble_{tk}", 133)
        d.gif([scene(ref(i) + [(P(ghost(k, tk), SPIRIT if tk == "a" else PLAYER), NX, BY - k)])
               for i, k in enumerate([0, 0, 1, 1, 2, 2, 1, 1])], f"ghost_{tk}", 133)
    d.gif([scene(ref(i) + [(P(gumflail(i % 2)), NX, BY)]) for i in range(6)], "gum_on_eyes", 133)
    BX = 100
    bump = [(-36, None, 0), (-28, None, 0), (-21, 0, 2), (-25, 1, 4), (-29, 0, 5), (-31, None, 5)]
    fr = []
    for i, (cx, k, px) in enumerate(bump):
        ps = ref(i) + [rag(i, BX + px, BY)]
        ps.append((P(t.take_a(0, 0, i % 3), CPU), BX + cx, BY))
        ps.append((P(squawk(k) if k is not None else t.take_a(0, 0, i % 3)), BX + px, BY))
        if k is not None: ps += [(P(SQUAWK), BX + px + 25, BY + 19), (P(mini(i - 2)), BX - 12, BY + 6)]
        if i == 4: ps.append((P(mini(2)), BX - 12, BY + 5))
        fr.append(scene(ps, w=150))
    d.gif(fr, "bump_squawk", 133)

    # ---- one screen at real size
    m = sky.crop((0, 0, 320, 224)).copy()
    pl = d.platform("plank", 3)
    m.paste(pl, (130, 180), pl)
    items = ref(0) + [rag(1, 70, 40), (P(hop(2)), 70, 40), rag(2, 130, 50), (P(bald(1)), 130, 50), (P(burst(2)), 176, 96),
                      (P(t.take_a(0, 1, 1)), 186, 100), (P(gumflail(0)), 250, 150), (P(ghost(0, "a"), SPIRIT), 20, 140),
                      (P(ghost(1, "b")), 64, 150), (P(squawk(0)), 120, 120), (P(SQUAWK), 145, 139),
                      (P(flip(t.take_a(0, 0, 1)), CPU), 99, 120), (P(mini(1)), 108, 126)]
    items += birdbub(hang(3), 3, "a", x=196, y=36) + birdbub(hang(2), 3, "b", x=262, y=60)
    for L, x, y in items: m.paste(L, (x, y), L)
    d.save(m, "screen_mock", (1, 3))

    S = [("1. Brake hop", "Weak flap from the falling pose, 4 frames: gather, wind up, pump, lift. The bird rises about 7 pixels, then falls again.",
          ["brake_hop.gif", "brake_hop_sheet_3x.png"]),
         ("2. Feather loss: puff burst and half bald bird", "Burst 6 frames (puff, then six feathers that turn a quarter each frame and drift). After two hits (v2): bald pink dome with two hairs, bare chest and belly, feathers left only as ragged shorts, wings clamped over the chest, eyes squeezed shut with a blush, then the front eye peeks (2 frame loop).",
          ["feather_loss.gif", "half_bald.gif", "feather_burst_sheet_3x.png", "half_bald_sheet_3x.png"]),
         ("3. Bubble parachute, take A: in-game gum pink, soft shine", "Uses the existing gum palette. Four sizes 8, 12, 18, 24 pixels, six pop frames (v2: flash, tear, fly, slow, drop, rain), then gum on the eyes.",
          ["bubble_a.gif", "bubble_a_sheet_3x.png"]),
         ("3. Bubble parachute, take B: candy pink, window shine", "New lighter palette (12 colours) with a hard four-pane glint and a blue sky reflection low right.",
          ["bubble_b.gif", "bubble_b_sheet_3x.png"]),
         ("3. Gum on eyes flail loop", "2 frames, gum in the bird palette pinks (computer bird gets its own gum colour).",
          ["gum_on_eyes.gif", "gum_on_eyes_sheet_3x.png"]),
         ("4. Ghost bird, take A: pale spirit", "Palette swap to a cold blue-white set, solid wisp tail, head bandage, plaster, crossed-out eyes. 3 frame bob.",
          ["ghost_a.gif", "ghost_a_sheet_3x.png"]),
         ("4. Ghost bird, take B: bandaged angel in player colours", "Keeps the player palette (no extra palette), halo, body thins out through a hand-typed dither.",
          ["ghost_b.gif", "ghost_b_sheet_3x.png"]),
         ("4. Bump squawk with small feather puff", "2 squawk frames, shout lines, 3 frame small puff at the contact side.",
          ["bump_squawk.gif", "bump_squawk_sheet_3x.png"])]
    h = ["""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Pop Drop fun extras - drafts</title>
<style>
body{background:#1c1f2b;color:#e6e8f0;font:15px/1.5 system-ui,sans-serif;margin:24px;max-width:1900px}
h1{font-size:22px}h2{font-size:18px;margin-top:40px;border-top:1px solid #3a3f5c;padding-top:20px}
img{image-rendering:pixelated;display:block;background:#000}
.row{display:flex;gap:16px;flex-wrap:wrap;margin-top:12px;align-items:flex-start}figure{margin:0}
figcaption{color:#a9afc6;font-size:13px;margin-top:4px}
</style></head><body>
<h1>Pop Drop: fun extras, drafts for owner picks (2026-11-20)</h1>
<p>Drafts only, nothing imported. In every animation the bird on the left is the existing in-game terror bird (take A, screaming flail)
at the same scale; the new item is on the right. Sky is summer sky v3 take B. Animations play at game timing, shown at 3 times size.
Sheets: top row player palette, bottom row computer palette. Every file also exists at 1 times size (same name ending _1x.png).</p>
<h2>All items on one screen (320 x 224, shown at 3 times size)</h2>
<div class="row"><figure><img src="screen_mock_3x.png"><figcaption>Left to right, top: terror bird (existing), brake hop pump frame, half bald bird, bubble take A, bubble take B.
Lower: ghost take A, ghost take B, bump squawk with computer bird, feather burst on a hit bird, gum on eyes.</figcaption></figure></div>"""]
    h.append("""<h2>v3 polish: v2 (left) against v3 (right)</h2>
<p>Three fixes: the tear frame strands no longer form an X, pop frames 5 and 6 carry more gum, and the bare skin of the half bald bird is gum pink with white glints instead of salmon (away from the wing orange). Take B uses the same pop frames.</p>
<div class="row">
<figure><img src="v2_bubble_a.gif"><figcaption>V2 bubble pop, take A</figcaption></figure>
<figure><img src="bubble_a.gif"><figcaption>V3 bubble pop, take A</figcaption></figure>
</div><div class="row">
<figure><img src="v2_bubble_a_sheet_3x.png"><img src="v2_bubble_a_sheet_1x.png" style="margin-top:8px"><figcaption>V2 frames, 3 times and real size</figcaption></figure>
<figure><img src="bubble_a_sheet_3x.png"><img src="bubble_a_sheet_1x.png" style="margin-top:8px"><figcaption>V3 frames, 3 times and real size (pop frames 2, 5, 6 changed)</figcaption></figure>
</div><div class="row">
<figure><img src="v2_half_bald.gif"><figcaption>V2 half bald</figcaption></figure>
<figure><img src="half_bald.gif"><figcaption>V3 half bald</figcaption></figure>
<figure><img src="v2_half_bald_sheet_3x.png"><img src="v2_half_bald_sheet_1x.png" style="margin-top:8px"><figcaption>V2 frames, 3 times and real size</figcaption></figure>
<figure><img src="half_bald_sheet_3x.png"><img src="half_bald_sheet_1x.png" style="margin-top:8px"><figcaption>V3 frames, 3 times and real size</figcaption></figure>
</div>""")
    h.append("""<h2>v2 redraw: old (left) against new (right)</h2>
<p>Half bald bird and the take A bubble pop redrawn. Each pair: old first, new second. The left bird in every animation is the in-game terror bird.</p>
<div class="row">
<figure><img src="v1_half_bald.gif"><figcaption>OLD half bald</figcaption></figure>
<figure><img src="half_bald.gif"><figcaption>NEW half bald</figcaption></figure>
<figure><img src="v1_half_bald_sheet_3x.png"><img src="v1_half_bald_sheet_1x.png" style="margin-top:8px"><figcaption>OLD frames, 3 times and real size</figcaption></figure>
<figure><img src="half_bald_sheet_3x.png"><img src="half_bald_sheet_1x.png" style="margin-top:8px"><figcaption>NEW frames, 3 times and real size</figcaption></figure>
</div><div class="row">
<figure><img src="v1_bubble_a.gif"><figcaption>OLD bubble pop, take A</figcaption></figure>
<figure><img src="bubble_a.gif"><figcaption>NEW bubble pop, take A (bird hangs while the gum bursts, glob lands on the face)</figcaption></figure>
</div><div class="row">
<figure><img src="v1_bubble_a_sheet_3x.png"><img src="v1_bubble_a_sheet_1x.png" style="margin-top:8px"><figcaption>OLD frames: 3 pop frames</figcaption></figure>
<figure><img src="bubble_a_sheet_3x.png"><img src="bubble_a_sheet_1x.png" style="margin-top:8px"><figcaption>NEW frames: 6 pop frames</figcaption></figure>
</div>""")
    for title, desc, files in S:
        h.append(f"<h2>{title}</h2><p>{desc}</p><div class=\"row\">")
        for f in files:
            assert os.path.exists(f"{HERE}/{f}"), f
            cap = "Animation, 3 times size" if f.endswith(".gif") else "Frames, 3 times size"
            h.append(f"<figure><img src=\"{f}\"><figcaption>{cap} ({f})</figcaption></figure>")
        h.append("</div>")
    h.append("</body></html>")
    open(f"{HERE}/index.html", "w").write("\n".join(h) + "\n")
    print("ok")


if __name__ == "__main__":
    main()
