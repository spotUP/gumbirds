#!/usr/bin/env python3.14 -I
"""Toss Gum poses, wing pass (2026-11-18): the raised / extended wing redrawn as a broad feathered wing.
Run: python3.14 -I draw_toss_poses2.py   (Pillow). Reuses ../poses/draw_toss_poses.py (body rows, palettes, loops, field).
Every wing row below is typed by hand. The script only swaps rows, mirrors, palette-maps, assembles sheets and checks."""
import importlib.util, os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OLDDIR = os.path.join(os.path.dirname(HERE), 'poses')
spec = importlib.util.spec_from_file_location('tp', os.path.join(OLDDIR, 'draw_toss_poses.py'))
tp = importlib.util.module_from_spec(spec); spec.loader.exec_module(tp)
tg, big = tp.tg, tp.big
OLD = dict(tp.POSE)

# name: (first row, typed wing rows, index of the first old row kept as is, wing-tip anchor for the gum knot)
# Wing letters: Z lit edge and feather tips, Y feather body, X slits and underside, K outline. Light from upper left.
WING = {
    'throw0': (6, [                                # carry: blade up and back, three feather steps on the trailing edge
        "..KK............................",
        ".KZZK...........................",
        ".KZZYK..........................",
        "KKZYYXK.........................",
        "KZZXYYK.........................",
        "KZYYXYXK..KKK...................",
        ".KKYYXYK.KeedKK.................",
        ".KZZXYYXK.KKeedK................",
        ".KZYYXYXK...KeedKKK.............",
        "..KKYYXXK..KKeeeddcKK...........",
        "..KZZXYXK.KeeeeedddccK..........",
        "...KZYYXKKeeeedddddcccK.........",
        "....KYYXKKeeedddbbcbbcK.........",
    ], 10, (3, 7)),
    'throw1': (11, [                               # windup B: fan cocked back, three primaries splayed up, back and down
        "..........KK....................",
        ".........KedK...................",
        "..........KeedK.................",
        ".KK........KeedK................",
        "KZZKK.......KeedKKK.............",
        "KZYZZKK...KKKeeeddccKK..........",
        ".KXYYZZKKKeeeeeeddddccK.........",
        ".KKKXYYZKeeeeedddddccccK........",
        "KZZZXYYKdeeeddddddcccccaK.......",
        "KZYYYXYXKeddcbbbbbcbbaaaK.......",
        ".KKKXYYXXKKccbbWWKcWWKbaK.......",
        "..KZZZXYXXXKcbbWWKcWWKbaK..5....",
        "..KZYYYXXXXKbbbbeecbeeaKK.34....",
        "...KKKKKKKKbbbbbbbabbaaZZY2.....",
    ], 14, (1, 15)),
    'throw2': (3, [                                # release A: blade whipped up and forward
        ".................KK.............",
        "................KZZK............",
        "...............KZZYK............",
        ".............KKZYYXK............",
        "............KZZXYYXK............",
        "............KZYYXYXK............",
        "............KKYYYXK.............",
        "...........KZZXYYXK.............",
        "...........KZYYXYXK.............",
        "......KKKK.KKYYYXK..............",
        ".....KeedKKZZXYXK...............",
    ], 9, (17, 4)),
    'throw3': (9, [                                # release B: wing flat forward over the head, primaries past the brow
        ".................KKKKKKK........",
        "..............KKKZZZZZZZKKK.....",
        ".............KZZZYYYYYYYZZZKK...",
        "..........KKKKYZYYYXYYXYZYYZZK..",
        ".........KeedKXYXYXXYXXYXYYYYZK.",
        "..........KKedKKKKKXXXXYYXYKKK..",
        ".............KKeeedKKKKXZZYYK...",
        "............KeeeeedddccKXYKK....",
        "...........KeeeedddddcccKK......",
    ], 7, None),
    'catch0': (5, [                                # reach A: blade up, a little forward
        "...............KK...............",
        "..............KZZK..............",
        ".............KZZYK..............",
        "...........KKZYYXK..............",
        "..........KZZXYYXK..............",
        "..........KZYYXYXK..............",
        "..........KKYYYXK...............",
        ".......KKKKZZXYXK...............",
        "......KeedKZYYXXK...............",
    ], 6, (15, 6)),
    'catch1': (0, [                                # reach B: full stretch, tallest blade
        "...............KK...............",
        "..............KZZK..............",
        ".............KZZYK..............",
        ".............KZYYXK.............",
        "...........KKZYYYXK.............",
        "..........KZZXYYYXK.............",
        "..........KZYYXYXXK.............",
        "..........KKYYYXYXK.............",
        ".........KZZXYYXXK..............",
        ".........KZYYXYXXK..............",
        ".........KKYYYXXK...............",
        "..........KZZXYXK...............",
        "......KKK.KZYYXK................",
    ], 9, (15, 1)),
    'catch2': (12, [                               # absorb: wing folded over the head, one row deeper, tips at the brow
        "..........KKKKKKK...............",
        "........KKZZZZZZZKKK............",
        ".......KZZYYYZYYYZZZKK..........",
        "......KZYYYYYYXYYXYYZZK.........",
        "......KZYYXXXXXXXXXYXYYK........",
        "......KYXXKKKKKKKKKKKKKK........",
    ], 5, (13, 12)),
    'catch3': (5, [                                # recoil: same blade as the carry, one row higher over the squash
        "..KK............................",
        ".KZZK...........................",
        ".KZZYK..........................",
        "KKZYYXK.........................",
        "KZZXYYK.........................",
        "KZYYXYXK........................",
        ".KKYYXYK..KK....................",
        ".KZZXYYK.KedK...................",
        ".KZYYXYXK.KeedK.................",
        "..KKYYXXK..KeedK................",
        "..KZZXYXK...KeedKKK.............",
        "...KZYYXXKKKKeeeddccKK..........",
        "....KYYXXKeeeeeeddddccK.........",
        ".....KYXKeeeeedddddccccK........",
    ], 10, (3, 6)),
}

def grid(top, rows):                              # 32 full rows, blank above
    return ['.' * 32] * top + list(rows)

NEW = {}
for n, (top, typed, keep, anc) in WING.items():
    rows = typed + OLD[n][1][keep:]
    assert top + len(rows) == 32, (n, top, len(rows))
    BODY = set('abcdeW12345')
    for y, (a, b) in enumerate(zip(grid(OLD[n][0], OLD[n][1]), grid(top, rows))):
        assert len(b) == 32 and set(b) <= set(tp.CH + '.'), (n, y, b)
        for x in range(32):                       # self-check: body, head, eyes and gum pixels are untouched
            assert (a[x] in BODY) == (b[x] in BODY) and (a[x] not in BODY or a[x] == b[x]), (n, y, x, a, b)
    NEW[n] = (top, rows, anc)

def wing_width(P):                                # widest run of wing pixels (X Y Z) in the wing rows, for the README
    return {n: max(max((len(s) for s in ''.join(c if c in 'XYZ' else ' ' for c in r[:-6]).split()), default=0)
                   for r in P[n][1][:-8]) for n in P}

def use(P):
    tp.POSE.clear(); tp.POSE.update(P); tp._pose.clear()

def backdrop_cells(name, city, grass):
    """old | new on grass (1P palette), old | new over the city backdrop (CPU1 palette)."""
    out = Image.new('RGBA', (4 * 34 + 2, 36), (20, 22, 26, 255))
    for i, (P, bg, pal) in enumerate(((OLD, grass, 'p1'), (NEW, grass, 'p1'), (OLD, city, 'cpu1'), (NEW, city, 'cpu1'))):
        use(P)
        c = bg.copy(); c.alpha_composite(tp.pose(name, pal))
        out.alpha_composite(c, (2 + 34 * i, 2))
    return out

def sheet():
    rows = (('p1', False), ('p2', True), ('cpu1', False), ('cpu2', True))
    sh = Image.new('RGBA', (33 * 9 - 1, 33 * 4 - 1), (20, 22, 26, 255))
    for r, (pal, flip) in enumerate(rows):
        cell = Image.new('RGBA', (32, 32), tp.BG + (255,)); cell.alpha_composite(tg.bird(tg.CLIP['idle'], pal, flip), (4, 0))
        sh.alpha_composite(cell, (0, 33 * r))
        for i, name in enumerate(tp.ORDER):
            cell = Image.new('RGBA', (32, 32), tp.BG + (255,)); cell.alpha_composite(tp.pose(name, pal, flip))
            sh.alpha_composite(cell, (33 * (i + 1), 33 * r))
    sh.convert('RGB').save(os.path.join(HERE, 'poses2_sheet_1x.png'))
    big(sh, 3).convert('RGB').save(os.path.join(HERE, 'poses2_sheet_3x.png'))

def main():
    f, _ = tp.field()
    bx, by = tp.SEATS[0]                          # back seat: the bird stands in front of the busiest part of the backdrop
    city = f.crop((bx - 16, by - 31, bx + 16, by + 1)); fx, fy = tp.SEATS[2]
    grass = f.crop((fx - 16, fy - 31, fx + 16, fy + 1))
    strip = Image.new('RGBA', (138, 8 * 36), (20, 22, 26, 255))
    for i, name in enumerate(tp.ORDER):
        c = backdrop_cells(name, city, grass)
        big(c, 6).convert('RGB').save(os.path.join(HERE, 'cmp_%s_6x.png' % name))
        strip.alpha_composite(c, (0, 36 * i))
    strip.convert('RGB').save(os.path.join(HERE, 'cmp_all_1x.png'))
    use(NEW); tp.HERE = HERE
    sheet()
    n_throw, n_catch = tp.loops()                 # same timing as before; writes throw_3x.gif and catch_3x.gif here
    n_toss = tp.toss()                            # the toss in the scene with the new wings
    ow, nw = wing_width(OLD), wing_width(NEW)
    lines = ['throw loop frames %d, catch loop frames %d, toss frames %d (timing unchanged)' % (n_throw, n_catch, n_toss),
             'widest wing run in px (X Y Z letters, wing rows), old -> new:']
    lines += ['  %-7s %2d -> %2d' % (n, ow[n], nw[n]) for n in tp.ORDER]
    open(os.path.join(HERE, 'numbers.txt'), 'w').write('\n'.join(lines) + '\n')
    print('\n'.join(lines))

if __name__ == '__main__':
    main()
