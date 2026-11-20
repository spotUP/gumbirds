#!/usr/bin/env python3.14
"""Pop Drop art batch 2, DRAFTS 2026-11-20: odd fallers (bathtub bird, armchair, snail on umbrella), finish pool,
three flop poses, splash in three sizes, score-card crowd.
Helpers, bird palettes and bird stamps come from batch 1 (../2026-11-20-popdrop-fun/draw_fun.py), unchanged.
Every shape is a hand-typed grid. Computed: WHERE stamps sit, H/V flips (free on Neo Geo), palette swaps, and the
splash droplet positions (ballistic arcs from hand-picked launch speeds; owner wants physics motion for fluids).
No game code, nothing imported by the game.
Run: python3.14 -I draw_batch2.py
"""
import math, os, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "../2026-11-20-popdrop-fun"))
import draw_fun as b1  # noqa: E402
t, d = b1.t, b1.d
d.HERE = HERE                                              # d.save / d.gif write here
stamp, img, flip, blank, many = d.stamp, d.img, d.flip, d.blank, b1.many
PLAYER, CPU = b1.PLAYER, b1.CPU
P2 = [tuple(c) for c in d.FJ["palettes"].get("p2", d.FJ["palettes"]["cpu"])]

# two new palettes, 15 colours each (index 0 transparent)
POOL = [(8, 8, 24), (28, 44, 120), (28, 102, 188), (50, 154, 224), (76, 214, 216), (150, 244, 250),   # 1 line, 2-6 water
        (214, 250, 255), (255, 255, 255), (112, 96, 156), (188, 180, 220), (70, 206, 120),            # 7-8 foam, 9-a tile shade
        (236, 228, 240), (255, 198, 49), (231, 90, 41), (60, 50, 100)]                                # c tile, d-e brass, f grout
GAG = [(8, 8, 24), (74, 16, 41), (140, 24, 49), (206, 49, 49), (247, 107, 74), (255, 181, 132),       # 1 line, 2-6 reds
       (66, 41, 33), (132, 82, 49), (206, 148, 82), (33, 90, 74), (49, 165, 99), (165, 231, 115),     # 7-9 wood, a-c green
       (255, 222, 90), (148, 156, 189), (255, 255, 255)]                                              # d yellow, e grey, f white
assert len(POOL) == 15 and len(GAG) == 15
BAD = []


def G(name, w, text):
    """strict typed grid; a ragged row is reported and padded so one run shows every miscount"""
    rows = [r.strip() for r in text.strip().split("\n")]
    for i, r in enumerate(rows):
        if len(r) != w: BAD.append(f"{name} row {i}: {len(r)} not {w}")
    return [r.ljust(w, ".")[:w] for r in rows]


V = lambda s: s[::-1]                                     # noqa: E731  vertical flip

# ================================================================== 1a. BIRD IN A BATHTUB
TUB = G("tub", 36, """
.1111111111111111111111111111111111.
1888888888888888888888888cccccaaa991
1ccc8888ccccccccccccccccccaaaaaa99f1
.19999999999999fffffffffffffffffff1.
..1888cccccccccccccccccaaaaaa999f1..
..188ccccccccccccccccacaaaaaa999f1..
..18ccccccccccccccacacaaaaaaa999f1..
..1cccccccccccccacacaaaaaaa9a999f1..
...1cccccccccacacaaaaaa9a9a999ff1...
...1cccccacacaaaaaaa9a9a99999fff1...
....1aaaaaaaa9a9a99999999ffffff1....
.....19999999999f9f9ffffffffff1.....
......111111111111111111111111......
.....1dd1..................1dd1.....
....1dde1..................1edd1....
....1de11..................11ed1....
....111......................111....
""")
FOAM = [G("foam_a", 36, """
......11..........111.........11....
..11.1881.11.....18781..111..1881.1.
.1881877618781..1877781187781877611.
187778776787778118777778877778777681
.1766777677666766776677767766676671.
"""), G("foam_b", 36, """
...11.........11.........111........
..1881..111..1881.11....18781.11.11.
.18778118781187781881.1.187778188187
187777877778777787778181877777877781
.1676677767666776677676677766766771.
""")]
DUCK = G("duck", 8, """
.111....
1ddd1...
1d1dee1.
1ddd11.1
1dddddd1
.111111.
""")
TUB_DROPS = [[(5, 12), (33, 8), (20, 1)], [(4, 9), (34, 5), (9, 14)], [(4, 6), (35, 2), (8, 11), (30, 13)],
             [(5, 3), (7, 8), (31, 10), (21, 4)]]          # beads left behind upward by the fall


def tub(k, pal=PLAYER):
    """40 x 40 cell, two sprites: bird head (bird palette) behind tub + foam + duck (POOL palette)"""
    c = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
    b = t.base(0, 0)
    if k in (1, 2): b = stamp(b, b1.EYES_SHUT, 8, 12)
    head = img(b[6:24], pal)
    dy = [0, 1, 1, 0][k]
    c.paste(head, (6, 2 + dy), head)
    f = stamp(blank(40, 40), DUCK, 28, 15 + [0, 0, 1, 1][k])
    f = stamp(stamp(f, TUB, 2, 22), FOAM[k % 2], 2, 18)
    for x, y in TUB_DROPS[k]: f = stamp(f, ["6"], x, y)
    L = img(f, POOL)
    c.paste(L, (0, 0), L)
    return c


# ================================================================== 1b. ARMCHAIR (front + profile, flips give the tumble)
CHAIR_A = G("chair_a", 28, """
......1111111111111111......
....11655555555555554311....
...1665555555555555544331...
..165555554444444444544331..
..165554444444444444454331..
..1655444d4444444d44444331..
..165444434444444344443331..
..165444444444444444434331..
..15444444444d444444434331..
..154444444443444444334331..
..154443444444444434343331..
.11111444444444434343311111.
1655541343434343434331655431
1655441665555555555541554431
1554441655555555555441544331
1544431555555444444431544331
1544431544444444444331443331
1444331111111111111111443321
1444331444444444433331433321
1343331434343434333331333221
1333321333333333333221332221
1323221323232323222221322221
.11111111111111111111111111.
.1981..................1981.
.1871..................1871.
.1871..................1871.
.111....................111.
""")
CHAIR_B = G("chair_b", 28, """
...11111....................
..1655431...................
..16554431..................
..165544331.................
...16544331.................
...165443321................
...165443321................
....165443321...............
....165443321...............
....1654433321..............
.....165443321..............
.....1654433211111111111....
.....16544331665555555431...
......16544316554444444331..
......16544315544444443331..
......16544315443434343331..
......16544314434343433321..
......16543314343333333221..
......16443313333333322221..
......15433313323232322221..
......14333212222222222221..
......111111111111111111111.
.......1981..........1981...
.......1871..........1871...
......1871............1871..
......111..............111..
""")


def chair(k):
    f = [CHAIR_A, CHAIR_B, V(flip(CHAIR_A)), V(flip(CHAIR_B))][k]
    return stamp(blank(30, 30), f, 1, 1 + (k % 2))


# ================================================================== 1c. SNAIL ON AN UMBRELLA
CANOPY = G("canopy", 31, """
...............1...............
..............171..............
...........1111d1111...........
........11154dd6dd45311........
......155544dd66ddd444331......
....1655544dd666ddd94444331....
..16dd555444dd66dddd94444339 1..
.16dd9554443ddd6dddd9444333d91.
16ddd9544433dddddd999443332d991
191.1443331.1dd999991.1433321.1
.1...11111...1111111...11111...
""".replace(" ", ""))
SHAFT = G("shaft", 7, """
..181..
..191..
..181..
..181..
..191..
..181..
..181..
..181..
1.181..
181981.
189981.
.1111..
""")
SNAIL = G("snail", 16, """
..........11.11.
.........1f11f1.
...11111..19191.
..1ccbbb1.19191.
.1cb111bba119991
1cb1cbb1bba19691
1cb1b11bbaa19991
1bb1bbbbbaa19981
1abb1111baa19881
.1aabbbaaa199881
1699999999988881
.11111111111111.
""")
STALK_B = ["..........__....", ".........___....", ".........1f1...."]     # near eye stalk droops (blink of sorts)


def snail(k):
    f = stamp(blank(34, 36), CANOPY, 1 + [0, 1, 0, 0][k], 10)
    f = stamp(f, SHAFT, 13 + [0, 0, 0, 1][k], 20)
    s = stamp(SNAIL, STALK_B, 0, 0) if k == 2 else SNAIL
    return stamp(f, s, 8 + [0, 1, 0, 0][k], [0, 0, 0, 0][k])


# ================================================================== 2. FINISH POOL
SURF = [G("surf0", 32, """
................................
......88................8.......
...887778.........8...8878...8..
88776667788888887887887667788787
76665556667777776776766556677676
65554445556666665665655445566565
54445444455555554554544444455454
44434444444454444444434444444444
"""), G("surf1", 32, """
................................
..............88................
..8........8878778.......88.....
87888788887766667788878888778888
76777677776655556677767777667777
65666566665544445566656666556666
54555455554444444455545555445555
44444444444443444444444454444344
"""), G("surf2", 32, """
................................
......................88........
.88......8.........8877788....8.
78878878888888788877666677888878
67767767777777677766555566777767
56656656666666566655444455666656
45545545555555455544444444555545
44444434444444444444434444444444
"""), G("surf3", 32, """
................................
8..............................8
778....88.........8.........8878
66778888788878888788888887887766
55667777677767777677777776776655
44556666566656666566666665665544
44445555455545555455555554554444
43444444444444434444444444444444
""")]
WATER = G("water", 32, """
44444444445544444444444444444444
44443444444455444444444344444444
44433344444444444554444333444444
44444444444444445445444444444454
45544444443444444444444444444544
54454444433344444443444444445444
44444444444444444433344444444444
44434444444444554444444444434444
43444344444445445444434444343444
44434443444444444444343444434344
34344434344434444344434344343434
43434343434343434343434343434343
34343433343434343433343434343334
33433343334333433343334333433343
33333433333334333333343333333433
33333333333333333333333333333333
""")
DEEPER = str.maketrans("345", "233")
EDGE_TOP = G("edge_top", 24, """
111111111111111111111111
8888888a8888888a88888881
88c8888a8c88888a8888cc81
8ccc88ca88ccc8ca88cccca1
cccccccacccccccacccaaa91
aaaaaaaaaaaaaaaaaaaaa9f1
111111111111111111199ff1
aaaaaaafaaaaaaafaaaa1...
a9aaaaafa9aaaaafa9aa1...
aaaa9aafaaaa9aafaa9a1...
a9a9a9afa9a9a9afa9a91...
9a999a9f9a999a9f9a991...
ffffffffffffffffffff1...
aaafaaaaaaafaaaaaaaf1...
9aafa9aaaaafa9aaa9af1...
a9afaaa9a9afaaa9aaaf1...
""")
EDGE_LOW = G("edge_low", 24, """
a9afa9a9a9afa9a9a9af1...
999f9a999a9f9a99999f1...
ffffffffffffffffffff1...
9999999f9999999f99991...
9a99999f9a99999f9a991...
9999a99f9999a99f99991...
9f999f9f9f999f9f9f991...
ffffffffffffffffffff1...
999f9999999f9999999f1...
9f9f99f99f9f99f99f9f1...
f99ff9f9f99ff9f9f99f1...
ffffffffffffffffffff1...
f9f9f9fff9f9f9fff9f91...
ffffffffffffffffffff1...
ffffffffffffffffffff1...
ffffffffffffffffffff1...
""")
LADDER = G("ladder", 10, """
.11....11.
1dd1..1dd1
1de1..1de1
1de1..1de1
1de1111de1
1deddddde1
1de1111de1
1de1..1de1
1de1..1de1
1de1111de1
1deddddde1
1de1111de1
1de1..1de1
.11....11.
""")

# ================================================================== 3. FLOP POSES (24 x 32, bird palette)
BELLY_V1 = G("belly_v1", 24, """
........................
........................
........................
........................
........................
........................
........................
..........11............
.........1981...........
........19871...........
.......198771...........
.......198771...........
......11987711111.......
....1166198771666611....
...16666611166665554111.
...16665555555554444161.
...166555555555444431651
11.155555555444444331651
891155444111111111331511
987154441ffff1ffff1211..
111144431ffff1ffff121...
...144331ff1f1f1ff121...
...143331ff1f1f1ff121...
....133316ff616ff611....
.....12211119981111.....
......1111.19871........
............1871........
.............11.........
........................
........................
........................
........................
""")                          # face down, wing flung up, feet trailing left, crest leading right
# v2 belly flop: the bird lies flat along the water, belly down, head to the right with the face tipped down
# (big forehead, eyes at the lower edge looking down), crest pointing forward, feet trailing, near wing spread
# toward the viewer over the flank, far wing spread away behind the back. Flat underside on row 23.
FLOP_BODY = G("flop_body", 12, """
..1111111111
.14454444333
144544433333
144444333333
144433333322
134333332322
133333323222
133332322222
.13232222222
..1222222222
...111111111
""")                          # at (2, 13)
FLOP_HEAD = G("flop_head", 10, """
..111111..
.16666661.
1666666651
1665666551
1611116111
11ffff1ff1
11ffff1ff1
11ff1f1f11
.1ffff1ff1
..1111.11.
""")                          # at (10, 13): round eyes low on the face, pupils at the bottom looking at the water
FLOP_CREST = G("flop_crest", 5, """
...11
.1161
16661
1661.
16661
1651.
16561
.1111
""")                          # at (19, 9): the crest comb lies forward off the forehead, top spike bent up by the air
FLOP_BEAK = G("flop_beak", 5, """
11...
1991.
19881
.1771
..11.
""")                          # at (19, 20)
FLOP_NEAR = G("flop_near", 9, """
..111111.
.19999981
199989871
198988771
189878711
18718711.
.11.11...
""")                          # at (3, 18): near wing fanned out toward the viewer, feather tips below the belly line
FLOP_FAR = G("flop_far", 7, """
.1..1..
181181.
1871871
1878771
.187771
.187771
..18771
...1111
""")                          # at (4, 6): far wing spread away behind the back, dimmer
FLOP_FEET = ["9.", "87", "..", "..", "9.", "87"]          # at (0, 15): legs straight back, toes kicked up
HUG = G("hug", 24, """
....11111111111111......
...15554444444444311....
..15544444444433333 11...
..15444433344333331891..
..11433333333333119871..
....1111111111111.111...
""".replace(" ", ""))            # at rows 22..27: both wings wrapped round the pulled-up knees, toes poke out
STREAK = ["6", "6", "f", "6", ".", "6"]


def flop(kind):
    if kind == "belly_v1": return BELLY_V1
    if kind == "belly":
        return many(blank(24, 32), [(FLOP_FAR, 4, 6), (FLOP_FEET, 0, 15), (FLOP_BODY, 2, 13), (FLOP_HEAD, 10, 13),
                                    (FLOP_CREST, 19, 9), (FLOP_BEAK, 18, 20), (FLOP_NEAR, 3, 18),
                                    (t.DROP, 14, 7), (t.SPECK, 2, 10)])
    if kind == "cannon":
        f = stamp(t.base(0, 0, t.CREST_FAN), b1.EYES_SHUT, 8, 12)
        return stamp(stamp(f, HUG, 0, 22), ["_" * 24] * 2, 0, 30)
    f = V(t.take_a(0, 0, 1))                              # face first: the in-game wings-up terror frame, V flipped
    return many(f, [(STREAK, 3, 0), (STREAK, 21, 2)])


# ================================================================== 4. SPLASH (crown stages typed, droplets on arcs)
CROWN_S = [G("s0", 16, """
......8..8......
...8.8778778.8..
..87877666677878
.876665555566678
"""), G("s1", 16, """
..8..........8..
.878........878.
.8768......8678.
..8768....8678..
..87668..86678..
...8766886678...
..876665566678..
.876665555566678
"""), G("s2", 16, """
.8............8.
...8........8...
.87..........78.
.876........678.
..876......678..
..8768....8678..
...876....678...
...8766..6678...
....87688678....
...8766556678...
..876655556678..
"""), G("s3", 16, """
...7........7...
..876..88..678..
...76.8778.67...
..8.68766786.8..
.876676666766778
8766655555566678
"""), G("s4", 16, """
....8......8....
.88777888877788.
8776666776666778
"""), G("s5", 16, """
88....8..8....88
7788778778877877
""")]
CROWN_M = [G("m0", 28, """
..........8......8..........
.....8..8.878..878.8..8.....
...8.878877768867778878.8...
..878776666667766666677878..
.87766655555566555555666778.
"""), G("m1", 28, """
...8....................8...
..878..................878..
..8768................8678..
...8768..8........8..8678...
...87668.87......78.86678...
....8766887......7886678....
....87666768....86766678....
.....876666768867666678.....
....87666655666655666678....
...8766655555665555566678...
"""), G("m2", 28, """
..8......................8..
.878.....................878
.876..8...............8..678
..876.87.............78.678.
..8768876...........6788678.
...876.876.........678.678..
...87667668.......86676678..
....876.6768.....8676.678...
....8766.6768...8676.6678...
.....87667668...86676678....
.....876676768.867676678....
......87667668866766678.....
.....876666676676666678.....
....87666655666655666678....
...8766655555665555566678...
"""), G("m3", 28, """
.7........................7.
..8......................8..
.87..7................7..78.
..76.8................8.67..
...6.87..............78.6...
..87..76............67..78..
...86.876....88....678.68...
....7.8676..8778..6768.7....
....86.8676.8778.6768.68....
.....76.876887788678.67.....
.....876.8767667678.678.....
....87667676666667676678....
....87666655666655666678....
...8766655555665555566678...
"""), G("m4", 28, """
.............88.............
............8778............
............8768............
.............87.............
.............878............
............8768............
............87668...........
...........876668...........
..8.......87666678.......8..
.878.8...8766556678...8.878.
8767787887665555667887877678
7666667766655555566677666667
"""), G("m5", 28, """
.............88.............
.............87.............
............................
.............8..............
............878.............
............8768............
8..8.......876678.......8..8
7877878888876666788888787787
"""), G("m6", 28, """
............88..............
...8.......8778.......8.....
88787888.88766788.88878788.8
7767677787766667787776767787
"""), G("m7", 28, """
..88......8..8......88......
8877887787788788778778877887
""")]
SHEET = [G("l0", 18, """
...8..............
..878..8..........
..8768.878........
...8766876688.....
....876667666788..
.....8766655566678
"""), G("l1", 18, """
.8................
878...............
8768.8............
.876.87...........
.8766876..........
..876.8768........
..8766.8766.......
...8766.87668.....
....87668.87668...
.....876668876678.
......876666666678
.......87665556667
"""), G("l2", 18, """
7.................
.8................
87...7............
.76..8............
..6.87............
.87..76..8........
..86.876.87.......
...7..8676.76.....
...86..8676.876...
....76..87668.76..
.....876.87667678.
......876676666678
"""), G("l3", 18, """
...7...8..........
.....8..87..8.....
.......8768.878.88
""")]
DROPS = [["6"], ["8"], ["87", "65"], [".8.", "876", ".6."], [".87.", "8766", "7665", ".65."]]
STREAK_V = ["8.", "87", "76", "65", ".5"]                 # fast and steep: head up, tail below (V flipped when falling)
STREAK_D = ["..87", ".876", ".65.", "5..."]               # fast up-right; H flip for left, V flip when falling
RINGLET = [[".88.", "8..8"], ["8....8"]]                  # where a drop lands
# (birth frame, x from centre, vx, vy, drop size) -- launch speeds picked by hand, px per frame
SPL = {
    "s": dict(w=32, h=32, sy=27, n=16, g=1.0, crown=[0, 1, 2, 2, 3, 3, 4, 4, 5, 5], set=CROWN_S, sheets=[],
              drops=[(1, -4, -1.2, -5.5, 2), (1, 4, 1.4, -5.0, 2), (1, -2, -.5, -6.2, 3), (1, 3, .6, -5.8, 1),
                     (1, -6, -2.2, -3.8, 0), (1, 6, 2.0, -4.2, 2), (3, 0, .2, -4.5, 1), (3, -1, -.8, -3.5, 0)]),
    "m": dict(w=56, h=48, sy=42, n=20, g=1.2, crown=[0, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7], set=CROWN_M, sheets=[],
              drops=[(1, -8, -2.0, -7.0, 3), (1, 8, 2.2, -6.6, 4), (1, -5, -1.0, -7.6, 4), (1, 5, .8, -7.3, 3),
                     (1, -10, -3.0, -5.2, 2), (1, 10, 2.8, -5.6, 2), (1, -3, -.4, -7.8, 2), (1, 2, .3, -7.5, 1),
                     (2, -9, -2.5, -6.0, 0), (2, 9, 2.4, -6.3, 3), (2, -6, -1.5, -6.9, 1), (2, 6, 1.7, -6.6, 2),
                     (8, 0, .3, -5.5, 3), (8, 0, -.5, -4.2, 0)]),
    "l": dict(w=88, h=72, sy=64, n=23, g=1.2, crown=[0, 1, 2, 2, 3, 3, 4, 4, 4, 5, 5, 6, 6, 7, 7, 7], set=CROWN_M,
              sheets=[0, 1, 1, 2, 2, 3, 3],
              drops=[(1, -12, -2.6, -9.6, 4), (1, 12, 2.8, -9.2, 4), (1, -7, -1.2, -10.0, 4), (1, 7, 1.0, -9.8, 4),
                     (1, -16, -3.6, -7.4, 3), (1, 16, 3.4, -7.8, 3), (1, -3, -.5, -10.2, 3), (1, 3, .4, -9.9, 2),
                     (1, -20, -4.2, -5.6, 2), (1, 20, 4.0, -5.9, 2), (2, -14, -3.0, -8.6, 1), (2, 14, 3.1, -8.3, 3),
                     (2, -9, -1.8, -9.3, 2), (2, 9, 1.9, -9.0, 1), (2, -18, -3.9, -6.6, 0), (2, 18, 3.7, -6.9, 2),
                     (3, -5, -.8, -8.8, 0), (3, 5, .9, -8.5, 3), (3, -11, -2.3, -7.9, 2), (3, 11, 2.2, -8.1, 0),
                     (4, -22, -3.2, -4.4, 1), (4, 22, 3.3, -4.1, 0), (9, 0, .4, -7.0, 4), (9, 0, -.6, -5.6, 2),
                     (9, 1, 1.1, -4.6, 0)]),
}


def splash(size, k):
    s = SPL[size]
    f, cx, sy, g = blank(s["w"], s["h"]), s["w"] // 2, s["sy"], s["g"]
    for i, sh in enumerate(s["sheets"]):                  # big only: low side sheets thrown outward
        if i == k:
            L = SHEET[sh]
            f = stamp(stamp(f, L, cx - 14 - 18, sy + 1 - len(L)), flip(L), cx + 14, sy + 1 - len(L))
    if k < len(s["crown"]):
        c = s["set"][s["crown"][k]]
        f = stamp(f, c, cx - len(c[0]) // 2, sy + 1 - len(c))
    for t0, x0, vx, vy, kind in s["drops"]:
        j = k - t0
        if j < 0: continue
        pos = lambda q: (cx + x0 + vx * q, sy - 2 + vy * q + g / 2 * q * q)   # noqa: E731
        land = next(q for q in range(1, 99) if pos(q)[1] > sy)
        if j >= land:
            if j - land < 2: f = stamp(f, RINGLET[j - land], round(pos(land)[0]) - 2 - (j - land), sy - 1 + (j - land))
            continue
        x, y = pos(j)
        vyj = vy + g * j
        st = DROPS[kind]
        if kind >= 2 and math.hypot(vx, vyj) > 4.5:
            st = STREAK_V if abs(vx) < 1 else (STREAK_D if vx > 0 else flip(STREAK_D))
            if vyj > 0: st = V(st)
        f = stamp(f, st, round(x) - len(st[0]) // 2, round(y) - len(st) // 2)
    return f


# ================================================================== 5. SCORE-CARD CROWD
CARD = G("card", 14, """
.111111111111.
1ffffffffffff1
1fffffffffffe1
1fffffffffffe1
1fffffffffffe1
1fffffffffffe1
1fffffffffffe1
1fffffffffffe1
1fffffffffffe1
1fffffffffffe1
1ffffffffffee1
1feeeeeeeeeee1
.111111111111.
""")
STICK = ["181", "191", "181", "181", "191"]
DIG = {c: G("dig" + c, 5, s) for c, s in {
    "1": "..1..\n.11..\n..1..\n..1..\n..1..\n..1..\n.111.", "2": ".111.\n1...1\n....1\n...1.\n..1..\n.1...\n11111",
    "3": "1111.\n....1\n....1\n.111.\n....1\n....1\n1111.", "4": "...1.\n..11.\n.1.1.\n1..1.\n11111\n...1.\n...1.",
    "5": "11111\n1....\n1111.\n....1\n....1\n1...1\n.111.", "6": ".111.\n1....\n1....\n1111.\n1...1\n1...1\n.111.",
    "7": "11111\n....1\n...1.\n..1..\n..1..\n.1...\n.1...", "8": ".111.\n1...1\n1...1\n.111.\n1...1\n1...1\n.111.",
    "9": ".111.\n1...1\n1...1\n.1111\n....1\n....1\n.111.", "0": ".111.\n1...1\n1...1\n1...1\n1...1\n1...1\n.111."}.items()}
RED = str.maketrans("1", "4")


def card(n):
    f = stamp(blank(14, 18), STICK, 5, 13)
    f = stamp(f, CARD, 0, 0)
    if n == 10: return many(f, [([r.translate(RED) for r in DIG["1"]], 1, 3), ([r.translate(RED) for r in DIG["0"]], 7, 3)])
    return stamp(f, DIG[str(n)], 4, 3)


def fan(k):
    """crowd bird = the in-game bird, wing up for the card; frame 1 looks up and shouts"""
    f = stamp(t.base(0, 0), t.WING_HI, 0, 6)
    if k: f = stamp(stamp(f, b1.EYES_HOPE, 8, 12), t.BEAK_B[0], 17, 19)
    return f


def fancell(k, n, pal, mirror=False):
    """30 x 44 cell, two sprites: card (GAG palette) and bird (a bird palette)"""
    c = Image.new("RGBA", (30, 44), (0, 0, 0, 0))
    dy = -2 if k else 0
    B, C = img(fan(k), pal), img(card(n), GAG)
    if mirror: B = B.transpose(Image.FLIP_LEFT_RIGHT)    # only the bird flips, the number stays readable
    c.paste(B, (1 if mirror else 5, 12 + dy), B)
    c.paste(C, (16 if mirror else 0, dy + 2), C)
    return c


# ================================================================== output
def main():
    for b in BAD: print("RAGGED", b)
    sky = Image.open(f"{HERE}/../2026-11-20-popdrop-sky-v3/b_postcard_sky_1x.png").convert("RGBA")
    AZ = sky.getpixel((160, 110))
    for kd in ("belly", "cannon", "face"):
        f = flop(kd)
        assert len(f) == 32 and all(len(r) == 24 for r in f), kd
    P = lambda grid, pal=PLAYER: img(grid, pal)          # noqa: E731
    W = lambda grid: img(grid, POOL)                     # noqa: E731

    def put(im, L, x, y): im.paste(L, (x, y), L)

    def sheet(name, rs, gap=4):
        w = max(sum(i.width + gap for i in r) for r in rs) + gap
        out = Image.new("RGBA", (w, sum(max(i.height for i in r) + gap for r in rs) + gap), AZ); y = gap
        for r in rs:
            x = gap
            for i in r: out.paste(i, (x, y), i); x += i.width + gap
            y += max(i.height for i in r) + gap
        d.save(out, name, (1, 3))

    def ref(i, x=12, y=62): return [(P(d.RAG2[i % 4]), x + 11, y - 12), (P(t.take_a(0, 0, i % 3)), x, y)]

    def pool(w, h, k, x0, tiles, sx=0, sy=0):
        """sky crop with deck, pool edges, ladder and water; returns (image, waterline y)"""
        im = sky.crop((sx, sy, sx + w, sy + h)).copy()
        dk, x1 = h - 48, x0 + 32 * tiles
        put(im, W(LADDER), x0 + 5, dk - 7)
        for i in range(tiles):
            put(im, W(SURF[k % 4]), x0 + 32 * i, dk + 3)
            for j, y in enumerate(range(dk + 11, h, 16)):
                put(im, W([r.translate(DEEPER) for r in WATER] if j else WATER), x0 + 32 * i, y)
        deck = [[r[:16] for r in gr] for gr in (EDGE_TOP, EDGE_LOW, EDGE_LOW)]
        for j, gr in enumerate((EDGE_TOP, EDGE_LOW, EDGE_LOW)):
            put(im, W(gr), x0 - 21, dk + 16 * j)
            put(im, W(flip(gr)), x1 - 3, dk + 16 * j)
            for x in range(x0 - 21 - 16, -16, -16): put(im, W(deck[j]), x, dk + 16 * j)
            for x in range(x1 + 21, w, 16): put(im, W(deck[j]), x, dk + 16 * j)
        return im, dk + 6

    # ---- sheets
    sheet("fallers_sheet", [[tub(k) for k in range(4)], [img(chair(k), GAG) for k in range(4)],
                            [img(snail(k), GAG) for k in range(4)]])
    sheet("pool_sheet", [[W(s) for s in SURF], [W(WATER), W([r.translate(DEEPER) for r in WATER]), W(EDGE_TOP),
                                                 W(EDGE_LOW), W(LADDER)]])
    sheet("flop_sheet", [[P(t.take_a(0, 0, 0), p)] + [P(flop(kd), p) for kd in ("belly", "cannon", "face")]
                         for p in (PLAYER, CPU)])
    for z in "sml": sheet(f"splash_{z}_sheet", [[W(splash(z, k)) for k in range(a, min(a + 7, SPL[z]["n"]))]
                                                for a in range(0, SPL[z]["n"], 7)])
    sheet("crowd_sheet", [[fancell(k, n, p) for k, n, p in ((0, 7, CPU), (1, 7, CPU), (0, 9, P2), (1, 9, P2))],
                          [img(card(n), GAG) for n in range(1, 11)]])

    # ---- animations, existing terror bird on the left for scale
    fr = []
    for i in range(12):
        im = sky.crop((150, 70, 150 + 200, 70 + 108)).copy()
        for L, x, y in ref(i): put(im, L, x, y)
        put(im, tub(i % 4), 48, 52 + [0, 0, -1, -1][i % 4])
        put(im, img(chair((i // 2) % 4), GAG), 104, 14)
        put(im, img(snail(i % 4), GAG), 152, 56)
        fr.append(im)
    d.gif(fr, "fallers", 133)
    d.gif([pool(320, 80, i, 96, 4)[0] for i in range(4)], "pool", 166)
    for z, kd in (("s", "face"), ("m", "cannon"), ("l", "belly")):
        s, fr = SPL[z], []
        for i in range(-3, s["n"] + 3):
            im, wl = pool(176, 136, max(i, 0) // 2, 40, 3, sx=70, sy=40)
            cx = 40 + 48
            if i < 0: put(im, P(flop(kd)), cx - 12, wl - 30 + i * 24 + 12)
            elif i < s["n"]: put(im, W(splash(z, i)), cx - s["w"] // 2, wl - s["sy"])
            for L, x, y in ref(i, 4, 20): put(im, L, x, y)
            fr.append(im)
        d.gif(fr, f"splash_{z}", 66)
    fr = []
    for i in range(10):
        im, wl = pool(176, 110, i // 2, 104, 2, sx=0, sy=60)
        for j, (p, n) in enumerate(((CPU, 6), (P2, 9), (CPU, 10))):
            put(im, fancell((i + j) // 2 % 2, n, p), 4 + 26 * j, 110 - 48 - 44)
        fr.append(im)
    d.gif(fr, "crowd", 133)

    # ---- one screen at real size
    m, wl = pool(320, 224, 1, 96, 4)
    for j, (p, n, mir) in enumerate(((CPU, 8, 0), (P2, 10, 0), (P2, 7, 1), (CPU, 9, 1))):
        put(m, fancell(j % 2, n, p, bool(mir)), (2, 36, 252, 286)[j], 224 - 48 - 44)
    put(m, W(splash("l", 5)), 160 - 44, wl - 64)
    put(m, tub(1), 30, 30); put(m, img(chair(1), GAG), 250, 20); put(m, img(snail(0), GAG), 200, 70)
    for L, x, y in ref(0, 100, 20): put(m, L, x, y)
    for i, kd in enumerate(("belly", "cannon", "face")): put(m, P(flop(kd)), 110 + 34 * i, 88)
    d.save(m, "screen_mock", (1, 3))

    S = [("1. Odd fallers (background gags, no collision)", "Bird in a clawfoot bathtub with a rubber duck (4 frames: bob, eyes shut, foam shifts, beads trail upward). Armchair: two drawings, front and profile, the other two tumble frames are flips. Snail riding on top of an open umbrella (4 frames: canopy and handle sway, eye stalk droops).",
          ["fallers.gif", "fallers_sheet_3x.png", "fallers_sheet_1x.png"]),
         ("2. Finish pool", "Water surface 32 pixels wide, 4 ripple frames, water body tile (second row is a darker palette-index swap), tiled pool edge with coping, brass ladder.",
          ["pool.gif", "pool_sheet_3x.png", "pool_sheet_1x.png"]),
         ("3. Flop poses (24 x 32)", "Left to right: in-game terror bird for comparison, belly flop (v2: lying flat along the water, belly down, head to the right looking down, near wing spread toward the viewer, far wing behind the back, feet trailing), cannonball (wings hug the knees, eyes shut), face first (the in-game wings-up frame flipped upside down, costs no new tiles). Top row player palette, bottom computer palette.",
          ["flop_sheet_3x.png", "flop_sheet_1x.png"]),
         ("4. Splash, small (16 frames, 32 x 32)", "Shown with the face-first entry. Crown stages are typed; droplets fly on ballistic arcs and leave a ringlet where they land. Animation slowed to 66 ms a frame (game: 50 ms).",
          ["splash_s.gif", "splash_s_sheet_3x.png"]),
         ("4. Splash, medium (20 frames, 56 x 48)", "Shown with the cannonball. Crown rises, tears into strings, a rebound jet pinches off a bead.",
          ["splash_m.gif", "splash_m_sheet_3x.png"]),
         ("4. Splash, big (23 frames, 88 x 72)", "Shown with the belly flop. Medium crown plus low side sheets and 25 droplets.",
          ["splash_l.gif", "splash_l_sheet_3x.png"]),
         ("5. Score-card crowd", "Crowd birds are the in-game bird in the computer and second-player palettes, wing up holding a card; second frame hops and shouts. Cards 1 to 10 below (10 in red).",
          ["crowd.gif", "crowd_sheet_3x.png", "crowd_sheet_1x.png"])]
    h = ["""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Pop Drop batch 2 - drafts</title>
<style>
body{background:#1c1f2b;color:#e6e8f0;font:15px/1.5 system-ui,sans-serif;margin:24px;max-width:1900px}
h1{font-size:22px}h2{font-size:18px;margin-top:40px;border-top:1px solid #3a3f5c;padding-top:20px}
img{image-rendering:pixelated;display:block;background:#000}
.row{display:flex;gap:16px;flex-wrap:wrap;margin-top:12px;align-items:flex-start}figure{margin:0}
figcaption{color:#a9afc6;font-size:13px;margin-top:4px}
</style></head><body>
<h1>Pop Drop: art batch 2, drafts for owner picks (2026-11-20)</h1>
<p>Drafts only, nothing imported. The bird with the gum rag in the animations is the existing in-game terror bird at the same scale.
Sky is summer sky v3 take B. Two new sprite palettes of 15 colours (pool and water; gag objects and cards); birds use the existing bird palettes.</p>
<h2>All items on one screen (320 x 224, shown at 3 times size, then real size)</h2>
<div class="row"><figure><img src="screen_mock_3x.png"><figcaption>Sky: bathtub bird, in-game bird, snail on umbrella, armchair; the three flop poses in a row.
Bottom: pool with the big splash, crowd with score cards on the deck.</figcaption></figure>
<figure><img src="screen_mock_1x.png"><figcaption>Real size</figcaption></figure></div>"""]
    for title, desc, files in S:
        h.append(f"<h2>{title}</h2><p>{desc}</p><div class=\"row\">")
        for f in files:
            assert os.path.exists(f"{HERE}/{f}"), f
            cap = "Animation, 3 times size" if f.endswith(".gif") else ("Frames, real size" if "_1x" in f else "Frames, 3 times size")
            h.append(f"<figure><img src=\"{f}\"><figcaption>{cap} ({f})</figcaption></figure>")
        h.append("</div>")
    h.append("""<h2>Belly flop v2: old (left) against new (right)</h2>
<p>The old belly flop read as a squashed wide bird with low eyes. The new one lies flat in side view. Cannonball and face first are unchanged.</p>
<div class="row">
<figure><img src="v1_flop_sheet_3x.png"><img src="v1_flop_sheet_1x.png" style="margin-top:8px"><figcaption>V1 flop sheet, 3 times and real size</figcaption></figure>
<figure><img src="flop_sheet_3x.png"><img src="flop_sheet_1x.png" style="margin-top:8px"><figcaption>V2 flop sheet, 3 times and real size</figcaption></figure>
<figure><img src="v1_splash_l.gif"><figcaption>V1 large splash (belly flop)</figcaption></figure>
<figure><img src="splash_l.gif"><figcaption>V2 large splash (belly flop)</figcaption></figure>
</div>""")
    h.append("</body></html>")
    open(f"{HERE}/index.html", "w").write("\n".join(h) + "\n")
    print("ok" if not BAD else f"{len(BAD)} ragged rows")


if __name__ == "__main__":
    main()
