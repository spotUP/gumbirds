#!/usr/bin/env python3.14 -I
"""Gumbirds stadium background, polish pass 2026-11-18 (art draft, not game code).

Builds on ../draw_stadium.py (imported as S): same layout tables, palettes, confetti, rain, cones, sky and turf.
New here, all typed pixel grids: crowd birds with team scarves / beanies / caps / shirts, far birds with a team patch,
a roof scoreboard with lamp digits, the dusk sun + roof glow + turf shadow tiles, and taller jump tables.
Each crowd row is now its own sprite strip with one tile of head room above the seat, so a jumping bird may rise
into the row above (2 tiles per bird). The script stamps, shifts in whole pixels, mirrors, palette-maps and counts.

Run: /opt/homebrew/bin/python3.14 -I draw_polish.py [--nogif]
"""
import os
import sys
from PIL import Image, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import draw_stadium as S  # noqa: E402

S.HERE = HERE                      # S.out() now writes into polish/
MOODS, MODES, NFR, MS = S.MOODS, S.MODES, S.NFR, S.MS
GIF_MAX = 1_900_000
rows, full = S.rows, S.full

# ---------------------------------------------------------------- near crowd, 16 x 16 cells, team colour on the bird
# type a: striped scarf (rows 9..10) with a hanging tail, team shirt below
A_A = {3: '.......oy.......', 4: '.....KKoyKK.....', 5: '....K2233rrK....', 6: '...K122333rrK...',
       7: '...K1WK23WKrK...', 8: '...K1WKyyWK3K...', 9: '..oKTtTooTtTKo..', 10: '..oKTTtTTtTTKo..',
       11: '...KtttttKTtK...', 12: '...KtTTttKtTK...'}
A_B = A_A | {9: '..oKTtTKKTtTKo..', 10: '..oKTTtooTTTKo..'}
A_C = {5: '.......oy.......', 6: '....KKKoyKKK....', 7: '..K12223333rrK..', 8: '..K1KK2233KK3K..',
       9: '.oK1122yy2233Ko.', 10: '.oKTtTTooTTtTKo.', 11: '..KTTtTTTTtTTK..', 12: '..KttttttKTttK..'}
A_D = A_A | {7: 'yo.K1WK23WKrK.oy', 8: '.ooK1WKyyWK3Koo.', 9: '...KTtTKKTtTK...', 10: '...KTTtooTTTK...'}
A_E = A_A | {2: '.y............y.', 3: '.oy....oy....yo.', 4: '..oo.KKoyKK.oo..', 5: '..ooK2233rrKoo..',
             9: '...KTtTKKTtTK...', 10: '...KTTtKKTTTK...'}
A_F = A_E | {2: '...y........y...', 3: '..yo...oy...oy..'}
# type b: bobble beanie (rows 1..3), scarf row 10, shirt rows 11..12
B_A = {1: '.......TT.......', 2: '......tTTT......', 3: '.....tTtTTT.....', 4: '.....KKKKKK.....',
       5: '....K2333rrK....', 6: '....K2233r3K....', 7: '....KWK2WKrK....', 8: '....KWK2WK3K....',
       9: '....K12yy23K....', 10: '...oKTtooTtKo...', 11: '...oKtTtTTtKo...', 12: '....KttTTttK....'}
B_B = B_A | {10: '...oKTtKKTtKo...'}
B_C = {3: '.......TT.......', 4: '.....tTTTTT.....', 5: '....tTtTTtTT....', 6: '....KKKKKKKK....',
       7: '...K22333rrrK...', 8: '...K1KK22KK3K...', 9: '...K112yy233K...', 10: '..oKTTtooTtTKo..',
       11: '..oKtTtTTtTtKo..', 12: '...KttTTTTttK...'}
B_D = B_A | {8: '.yo.KWK2WK3K.oy.', 9: '..ooK12yy23Koo..', 10: '....KTtKKTtK....', 11: '....KtTtTTtK....'}
B_E = B_A | {2: '..y...tTTT...y..', 3: '..oy.tTtTTT.yo..', 4: '...ooKKKKKKoo...', 9: '....K12KK23K....',
             10: '....KTtKKTtK....', 11: '....KtTtTTtK....'}
B_F = B_E | {2: '....y.tTTT.y....', 3: '...yotTtTTToy...'}
# type c: peaked cap (rows 4..5), two-row team shirt
C_A = {4: '.....tTTTT......', 5: '....tTTTTTTTT...', 6: '...KKKKKKKKKK...', 7: '..K122233333rK..',
       8: '..K1WK2233WKrK..', 9: '..K1WK22yyWK3K..', 10: '.oK11222oo233Ko.', 11: '.oKTTtTTTTtTTKo.',
       12: '..KtTttTTttTtK..'}
C_B = C_A | {10: '.oK11222KK233Ko.'}
C_C = {5: '.....tTTTT......', 6: '....tTTTTTTTT...', 7: '..KKKKKKKKKKKK..', 8: '.K12223333333rK.',
       9: '.K1KK2233KK33rK.', 10: 'oK11222yy22333Ko', 11: 'oKTTtTTooTTtTTKo', 12: '.KtTttTTTTttTtK.'}
C_D = C_A | {8: 'yoK1WK2233WKrKoy', 9: '.oK1WK22yyWK3Ko.', 10: '..K11222KK233K..', 11: '..KTTtTTTTtTTK..'}
C_E = C_A | {2: 'y..............y', 3: 'oy............yo', 4: '.oo..tTTTT...oo.', 5: '.oo.tTTTTTTTToo.',
             6: '..oKKKKKKKKKKo..', 10: '..K11222KK233K..', 11: '..KTTtTTTTtTTK..'}
C_F = C_E | {2: '..y..........y..', 3: '.yo..........oy.'}
BIRD = {t: {p: rows(g) for p, g in zip('ABCDEF', gs)} for t, gs in
        (('a', (A_A, A_B, A_C, A_D, A_E, A_F)), ('b', (B_A, B_B, B_C, B_D, B_E, B_F)), ('c', (C_A, C_B, C_C, C_D, C_E, C_F)))}

# ---------------------------------------------------------------- far crowd, 8 x 8 cells: type a two-row shirt, type b big cap
FARB = {
    'a': dict(A=['........', '...oy...', '.K233rK.', '.KW2W3K.', '.K12y3K.', '.KTtTTK.', '.KtTTtK.', '........'],
              B=['........', '...oy...', '.K233rK.', '.KW2W3K.', '.K1KK3K.', '.KTtTTK.', '.KtTTtK.', '........'],
              E=['y......y', 'o..oy..o', 'oK233rKo', '.KW2W3K.', '.K1KK3K.', '.KTtTTK.', '.KtTTtK.', '........'],
              F=['.y....y.', '.o.oy.o.', 'oK233rKo', '.KW2W3K.', '.K1KK3K.', '.KTtTTK.', '.KtTTtK.', '........']),
    'b': dict(A=['........', '..TTTT..', '.tTTTTTt', '.KKKKKK.', 'K2W3W3rK', 'K12yy23K', 'KtTTTTtK', '........'],
              B=['........', '..TTTT..', '.tTTTTTt', '.KKKKKK.', 'K2W3W3rK', 'K12KK23K', 'KtTTTTtK', '........'],
              E=['y......y', 'o.TTTT.o', 'otTTTTTo', '.KKKKKK.', 'K2W3W3rK', 'K12KK23K', 'KtTTTTtK', '........'],
              F=['........', 'y.TTTT.y', 'otTTTTTo', '.KKKKKK.', 'K2W3W3rK', 'K12KK23K', 'KtTTTTtK', '........']),
}
for _t in FARB.values():
    for _g in _t.values():
        assert len(_g) == 8 and all(len(r) == 8 for r in _g), _g

# ---------------------------------------------------------------- roof scoreboard, 7 x 2 tiles on plane columns 7..13
HDR = full([
    '................', 'KKKKKKKKKKKKKKKK', 'dddddddddddddddd', 'cdcccccccdcccccc',
    'KKKKKKKKKKKKKKKK', 'TTTTTTTTTTTTTTTT', 'tttttttttttttttt', 'tttttttttttttttt',
    'tttttttttttttttt', 'tttttttttttttttt', 'tttttttttttttttt', 'tttttttttttttttt',
    'tttttttttttttttt', 'tTtTTtTtTtTTtTtT', 'KKKKKKKKKKKKKKKK', 'KKKKKKKKKKKKKKKK'])
MID_T = full([
    '................', 'KKKKKKKKKKKKKKKK', 'dddddddddddddddd', 'cccccdcccccccccc',
    'KKKKKKKKKKKKKKKK', 'bbbbbbbbbbbbbbbb', 'baaaaaaaaaaaaaab', 'baKKKKKKKKKKKKab',
    'baKyyKyyKyyKyyab', 'baKyoKyoKyoKyoab', 'baKKKKKKKKKKKKab', 'baaaaaaaaaaaaaab',
    'bbbbbbbbbbbbbbbb', 'cbcccccccccbcccc', 'KKKKKKKKKKKKKKKK', 'KKKKKKKKKKKKKKKK'])
MID_B = full([
    'aaaaaaaaaaaaaaaa', 'bKKKKKKKKKKKKKKb', 'bKKKKKKKKKKKKKKb', 'bKKKKKKyyKKKKKKb',
    'bKKKKKKyoKKKKKKb', 'bKKKKKKKKKKKKKKb', 'bKKKKKKKKKKKKKKb', 'bKKKKKKKKKKKKKKb',
    'bKKKKKKyyKKKKKKb', 'bKKKKKKyoKKKKKKb', 'bKKKKKKKKKKKKKKb', 'bKKKKKKKKKKKKKKb',
    'KKKKKKKKKKKKKKKK', 'cccccccdcccccccc', 'bbbbbbbbbbbbbbbb', 'KKKKKKKKKKKKKKKK'])
EDGE_T = full([
    '................', '........KKKKKKKK', '.......Kdddddddd', '.......Kdccccccc',
    '.......KdcKKKKKK', '.......KdcKbbbbb', '.......KdcKbyybb', '.......KdcKbyobb',
    '.......KdcKbbbbb', '.......KdcKbbbbb', '.......KdcKbyybb', '.......KdcKbyobb',
    '.......KdcKbbbbb', '.......KdcKbbbbb', '.......KdcKbyybb', '.......KdcKbyobb'])
EDGE_B = full([
    '.......KdcKbbbbb', '.......KdcKbbbbb', '.......KdcKbyybb', '.......KdcKbyobb',
    '.......KdcKbbbbb', '.......KdcKbbbbb', '.......KdcKbyybb', '.......KdcKbyobb',
    '.......KdcKbbbbb', '.......KdcKbbbbb', '.......KdcKbyybb', '.......KdcKbyobb',
    '.......KdcKbbbbb', '.......KdcKKKKKK', '......KKdccccccc', '......Kbbbbbbbbb'])
_O, _R, _L = '##...##', '.....##', '##.....'
DIGIT = {       # 7 x 11 lamp digits; the game swaps one 16 x 16 tile per digit
    0: ('.#####.',) + (_O,) * 9 + ('.#####.',),
    1: ('...##..', '..###..', '.####..') + ('...##..',) * 7 + ('.######',),
    2: ('.#####.', _O, _R, _R, '....##.', '...##..', '..##...', '.##....', _L, _L, '#######'),
    3: ('.#####.', _O, _R, _R, _R, '..####.', _R, _R, _R, _O, '.#####.'),
    4: ('....##.', '...###.', '..####.', '.##.##.', '##..##.', '##..##.', '#######') + ('....##.',) * 4,
    5: ('#######', _L, _L, _L, '######.', _R, _R, _R, _R, _O, '.#####.'),
    6: ('.#####.', _O, _L, _L, '######.', _O, _O, _O, _O, _O, '.#####.'),
    7: ('#######', _R, _R, '....##.', '....##.', '...##..', '...##..') + ('..##...',) * 4,
    8: ('.#####.',) + (_O,) * 4 + ('.#####.',) + (_O,) * 4 + ('.#####.',),
    9: ('.#####.',) + (_O,) * 4 + ('.######', _R, _R, _R, _O, '.#####.'),
}
assert all(len(g) == 11 and all(len(r) == 7 for r in g) for g in DIGIT.values())
GLYPH = dict(S.GLYPH)
GLYPH['1'] = ('..#..', '.##..', '..#..', '..#..', '..#..', '..#..', '.###.')
GLYPH['2'] = ('.###.', '#...#', '....#', '...#.', '..#..', '.#...', '#####')
SAMPLE = (0, 3, 0, 5)          # sample score 03 : 05


def stamp(base, glyph, x, y, ch):
    g = [list(r) for r in base]
    for j, rw in enumerate(glyph):
        for i, c in enumerate(rw):
            if c == '#':
                g[y + j][x + i] = ch
    return tuple(''.join(r) for r in g)


def digit(n):
    """Digit tile: dark lamp field rows 0..12 (digit area x 4..10, y 1..11), frame foot rows 13..15."""
    base = ('aaaaaaaaaaaaaaaa',) + ('KKKKKKKKKKKKKKKK',) * 12 + MID_B[13:]
    return stamp(base, DIGIT[n], 4, 1, 'y')


def hdr(ch, team, x):
    return stamp(HDR, GLYPH[ch], x, 6, 'W' if team == 0 else 'K')      # white on blue, dark on yellow


# ---------------------------------------------------------------- dusk light: low sun behind the roof on the right
def _sun_row(dots, halo, yy, ww):
    left = '.' * dots + halo + 'y' * yy + 'W' * ww
    assert len(left) == 24, left
    return left + left[::-1]


SUN = (     # 48 x 16 half disc on the roof line, typed left half mirrored; halo is hand-placed 'o' dither
    '.' * 48, _sun_row(21, 'o.o', 0, 0), _sun_row(18, 'o.o.oo', 0, 0), _sun_row(17, 'o.ooo', 2, 0),
    _sun_row(14, 'o.ooo', 5, 0), _sun_row(12, '.o.oo', 5, 2), _sun_row(10, 'o.ooo', 4, 5), _sun_row(9, '.o.oo', 4, 6),
    _sun_row(8, 'o.o.o', 4, 7), _sun_row(7, '.o.oo', 4, 8), _sun_row(7, 'o.o.o', 3, 9), _sun_row(6, '.o.oo', 4, 9),
    _sun_row(6, 'o.o.o', 3, 10), _sun_row(5, '.o.oo', 4, 10), _sun_row(4, 'o.o.oo', 3, 11), _sun_row(3, 'o.o.ooo', 4, 10))
_E12 = ['.' * 16] * 12
GLOW = {'1': full(_E12 + ['...o......o...o.', '.o...o.o.o..o...', 'o.oo.oo.o.oo.oo.', 'yoyoyyoyoyyoyoyy']),
        '2': full(_E12 + ['................', '....o.......o...', '.o....o..o....o.', 'o.oyo.o.oo.oyo.o']),
        '3': full(_E12 + ['................', '................', '......o.......o.', '.o.o....o.o..o..'])}
GLOWROW = '.....' + '33' + '2222' + '111' + 'SSS' + '11' + '2'      # 20 screen tiles at y 16..31; S = the sun
assert len(GLOWROW) == 20
SH = {      # long stand shadow on the turf: full mesh row, then two saw-tooth edges leaning away from the sun
    'F': full(['#.#.#.#.#.#.#.#.', '.#.#.#.#.#.#.#.#'] * 8),
    'A': full(['#.#.#.#.#.#.#.#.', '.#.#.#.#.#.#.#.#', '#.#.#.#.#.#.#.#.', '.#.#.#.#.#.#.#..', '#.#.#.#.#.#.#...',
               '.#.#.#.#.#.#....', '#.#.#.#.#.#.....', '.#.#.#.#.#......', '#.#.#.#.#.......', '.#.#.#.#........',
               '#.#.#.#.........', '.#.#.#..........', '#.#.#...........', '.#.#............', '#.#.............',
               '.#..............']),
    'B': full(['#.#.#.#.#.#.#.#.', '.#.#.#.#.#.#.#.#', '#.#.#.#.#.#.#.#.', '.#.#.#.#.#.#.#..', '#.#.#.#.#.#.....',
               '.#.#.#.#.#......', '#.#.#.#.........', '.#.#.#..........', '#.#.............', '.#..............'] + ['.' * 16] * 6),
}
RIM = {k: rows({0: r}) for k, r in (('1', '.o...o..o...o..o'), ('2', 'o.oooo.ooo.ooooo'), ('3', 'yoyyyoyyyyoyyyoy'))}
RIMROW = '111111222222233333333'     # dusk only: sun-lit top edge of roof, balcony front and boards, hotter toward the sun
assert len(RIMROW) == 21
SHROW = 'ABAABABBAABABAABBABA'
assert len(SHROW) == 20

# ---------------------------------------------------------------- overrides of the imported tables
S.NF = ['0' * 21] * 3          # no mirrored near birds: the rim light stays on the sun side in every mood
S.PLUM['dusk'] = [p[:3] + ((255, 236, 160),) for p in S.PLUM['dusk']]      # hotter low-sun rim
# jumps (pose, dy): parabola rise and fall in whole pixels; near peaks 8 / 10 / 6 px, far 4 px (was 2 and 1)
S.CHEER = {'a': [('C', 0), ('D', -2), ('E', -5), ('F', -7), ('E', -8), ('F', -8), ('E', -7), ('F', -5), ('D', -2), ('C', 0),
                 ('A', -1), ('D', -3), ('E', -6), ('F', -7), ('E', -6), ('D', -3), ('C', 0), ('A', -1), ('A', 0)],
           'b': [('C', 0), ('C', 0), ('D', -3), ('E', -6), ('F', -9), ('E', -10), ('F', -10), ('E', -9), ('F', -6), ('D', -3),
                 ('C', 0), ('A', -1), ('A', 0)],
           'c': [('C', 0), ('D', -2), ('E', -4), ('F', -6), ('E', -6), ('F', -4), ('D', -2), ('C', 0), ('C', 0), ('A', -1), ('A', 0)]}
S.WAVE = {t: [('C', 0), ('D', -2), ('E', -4), ('E', -6), ('F', -6), ('F', -5), ('D', -2), ('C', 0), ('A', 0)] for t in 'abc'}
S.CHEER_F = [('A', -1), ('E', -2), ('F', -3), ('E', -4), ('F', -4), ('E', -3), ('F', -2), ('E', -1), ('A', -1), ('A', 0)]
S.WAVE_F = [('A', -1), ('E', -2), ('E', -3), ('F', -3), ('E', -2), ('A', -1), ('A', 0)]
assert min(dy for seq in S.CHEER.values() for _, dy in seq) <= -8 and min(dy for _, dy in S.CHEER_F) <= -4

BLANK = ('.' * 16,) * 16
_C2 = {}


def cell2(bird, dy):
    """(head-room tile, seat tile) of one near bird; the bird may rise up to 16 px into the head-room tile."""
    key = (bird, dy)
    if key not in _C2:
        g = [['.'] * 16 for _ in range(16)] + [list(r) for r in S.SEAT_BG]
        for j, row in enumerate(bird):
            y = 16 + j + dy
            if y < 29:      # rows 29..31 are the ledge in front of the bird
                assert y >= 0 or set(row) == {'.'}, ('bird leaves its two tiles', dy)
                for i, ch in enumerate(row):
                    if ch != '.':
                        g[y][i] = ch
        r = [''.join(x) for x in g]
        _C2[key] = (tuple(r[:16]), tuple(r[16:]))
    return _C2[key]


def near_tiles(mood, mode, f, r, c):
    t = S.NT[r][c]
    if t == 's':
        return BLANK, S.AISLE
    if t == 'e':
        return cell2(S.EMPTY, 0)
    pose, dy = S.near_state(mode, f, r, c)
    if mood == 'storm' and S.NU[r][c] == '1':       # umbrella birds hop with the umbrella
        return cell2(S.UMB, dy)
    return cell2(BIRD[t][pose], dy)


def far_tiles(mood, mode, f, row, bc):
    name = S.FB[row][bc]
    if name == 'S':
        return BLANK, S.AISLE
    g = [['.'] * 16 for _ in range(16)] + [list(S.FAR_BG[j % 8] * 2) for j in range(16)]
    for k, (t, flip, ph) in enumerate(S.BLOCKS[name]):
        if t == 'e':
            continue
        if mood == 'storm' and (row, bc, k) in S.FU:
            b, dy = S.FAR_UMB, 0
        else:
            pose, dy = S.far_state(mode, f, row, bc, ph)
            b = FARB[t][pose]
        for j, rw in enumerate(b):
            if j + dy < 7:
                for i, ch in enumerate(rw[::-1] if flip else rw):
                    if ch != '.':
                        g[16 + (k // 2) * 8 + j + dy][(k % 2) * 8 + i] = ch
    r = [''.join(x) for x in g]
    return tuple(r[:16]), tuple(r[16:])


def scoreboard():
    """[(grid, team, flip)] for the top and the bottom tile row, plane columns 7..13."""
    d = SAMPLE
    top = [(EDGE_T, 0, False), (hdr('P', 0, 9), 0, False), (hdr('1', 0, 2), 0, False), (MID_T, 0, False),
           (hdr('P', 1, 9), 1, False), (hdr('2', 1, 2), 1, False), (EDGE_T, 1, True)]
    bot = [(EDGE_B, 0, False), (digit(d[0]), 0, False), (digit(d[1]), 0, False), (MID_B, 0, False),
           (digit(d[2]), 1, False), (digit(d[3]), 1, False), (EDGE_B, 1, True)]
    return top, bot


_STRUCT = {}


def struct_plane(mood):
    """336 x 96: towers + scoreboard 0..31, roof 32..47, balcony front 80..95 (rows 48..79 are covered by the far crowd)."""
    if mood not in _STRUCT:
        im = Image.new('RGBA', (336, 96), (0, 0, 0, 0))
        for c in range(21):
            sp = S.pal(mood, 0 if c < 10 else 1, 0, True)
            for g, y in ((S.ROOF_LAMP if S.ROOFROW[c] == 'L' else S.ROOF, 32),
                         (S.over(S.FASCIA, S.BANNER) if S.FASROW[c] == 'B' else S.FASCIA, 80)):
                if mood == 'dusk':
                    g = S.over(g, RIM[RIMROW[c]])
                im.paste(S.img(g, sp), (16 * c, y))
                S.use(mood, 'struct', 'all', g)
        for x in S.TOWERS:
            sp = S.pal(mood, 0, 0, True)
            im.alpha_composite(S.img(S.HEAD, sp), (x, 0))
            im.alpha_composite(S.img(S.MAST, sp), (x, 16))
        for y, line in zip((0, 16), scoreboard()):
            for i, (g, team, flip) in enumerate(line):
                im.alpha_composite(S.img(g, S.pal(mood, team, 0, False), flip), (16 * (7 + i), y))     # unhazed: lamps glow
                S.use(mood, 'struct', 'all', g)
        for n in range(10):
            S.use(mood, 'digit', 'all', digit(n))
        _STRUCT[mood] = im
    return _STRUCT[mood]


def far_plane(mood, mode, f):
    im = struct_plane(mood).copy()
    for row in range(2):
        for c in range(21):
            top, bot = far_tiles(mood, mode, f, row, c)
            p = S.pal(mood, 0 if c < 10 else 1, int(S.FV[row][c]), True)
            im.paste(S.img(bot, p), (16 * c, 48 + 16 * row))
            S.use(mood, 'far', mode, bot)
            if top != BLANK:
                im.alpha_composite(S.img(top, p), (16 * c, 32 + 16 * row))
                S.use(mood, 'far', mode, top)
    return im


def near_plane(mood, mode, f):
    """336 x 80: head room 0..15 (screen 80..95, over the balcony front), crowd rows 16..63, boards 64..79."""
    im = Image.new('RGBA', (336, 80), (0, 0, 0, 0))
    for c in range(21):
        team = 0 if c < 10 else 1
        g = S.board(S.BOARDROW[c], team)
        if mood == 'dusk':
            g = S.over(g, RIM[RIMROW[c]])
        im.paste(S.img(g, S.pal(mood, team, 0, False)), (16 * c, 64))
        S.use(mood, 'struct', 'all', g)
    for r in range(3):          # back row first: a jumping bird covers the row behind it
        for c in range(21):
            top, bot = near_tiles(mood, mode, f, r, c)
            p = S.pal(mood, 0 if c < 10 else 1, int(S.NV[r][c]), False)
            im.paste(S.img(bot, p), (16 * c, 16 + 16 * r))
            S.use(mood, 'near', mode, bot)
            if top != BLANK:
                im.alpha_composite(S.img(top, p), (16 * c, 16 * r))
                S.use(mood, 'near', mode, top)
    return im


def dusk_sky():
    im = Image.new('RGBA', (320, 16), (0, 0, 0, 0))
    p = S.pal('dusk', 0, 0, False)
    for c, ch in enumerate(GLOWROW):
        if ch in GLOW:
            im.alpha_composite(S.img(GLOW[ch], p), (16 * c, 0))
    im.alpha_composite(S.img(SUN, p), (16 * GLOWROW.index('S'), 0))
    return im


def dusk_shadow():
    im = Image.new('RGBA', (320, 32), (0, 0, 0, 0))
    p = ({'#': S.pal('dusk', 0, 0, False)[0]['K']}, 'shadow')
    for c, ch in enumerate(SHROW):
        im.alpha_composite(S.img(SH['F'], p), (16 * c, 0))
        im.alpha_composite(S.img(SH[ch], p), (16 * c, 16))
    return im


_STATIC = {}


def static(mood):
    if mood not in _STATIC:
        back = Image.new('RGBA', (320, 224), (0, 0, 0, 255))
        back.alpha_composite(S.keyed(os.path.join(S.BG, 'plane_%s_sky_1x.png' % mood)).crop((0, 0, 320, 64)))
        back.alpha_composite(S.cones(mood))
        front = Image.new('RGBA', (320, 224), (0, 0, 0, 0))
        front.alpha_composite(S.FF.turf(mood), (0, 160))
        if mood == 'dusk':
            back.alpha_composite(dusk_sky(), (0, 16))
            front.alpha_composite(dusk_shadow(), (0, 160))
        a, b = S.pair()
        front.alpha_composite(a, (112 - a.width // 2, 161 - a.height))
        front.alpha_composite(b, (208 - b.width // 2, 161 - b.height))
        _STATIC[mood] = (back, front)
    return _STATIC[mood]


def wrap(im, sx):
    w = Image.new('RGBA', (im.width * 3, im.height), (0, 0, 0, 0))
    for k in range(3):
        w.paste(im, (k * im.width, 0))
    return w.crop((im.width + sx, 0, im.width + sx + 320, im.height))


def frame(mood, mode, f, sx=8):
    """sx = plane x at the left screen edge (8 = centred, as in the still events)."""
    back, front = static(mood)
    im = back.copy()
    im.alpha_composite(wrap(far_plane(mood, mode, f), sx))
    im.alpha_composite(wrap(near_plane(mood, mode, f), sx), (0, 80))
    im.alpha_composite(front)
    S.confetti(im, mood, mode, f, NFR[mode])
    if mood == 'storm':
        S.rain(im, f)
    return im.convert('RGB')


def save_gif(path, frames, k=3):
    """Delta GIF: pixels equal to the previous frame are written transparent, which is what keeps the files small."""
    cols = sorted({c for fr in frames for _, c in fr.getcolors(200000)})
    assert len(cols) <= 255, len(cols)
    flat = [v for c in cols for v in c] + [0] * (768 - 3 * len(cols))
    idx = {c: i for i, c in enumerate(cols)}
    q, prev = [], None
    for fr in frames:
        im = Image.new('P', fr.size)        # exact index map: quantize() rounds close hazed colours together
        im.putpalette(flat)
        im.putdata([idx[c] for c in fr.getdata()])
        if prev is not None:
            ch = ImageChops.difference(fr, prev).split()
            mask = ImageChops.lighter(ImageChops.lighter(ch[0], ch[1]), ch[2]).point(lambda v: 255 if v else 0)
            d = Image.new('P', fr.size, 255)
            d.putpalette(flat)
            d.paste(im, mask=mask)
            im = d
        prev = fr
        q.append(S.big(im, k))
    q[0].save(path, save_all=True, append_images=q[1:], duration=MS, loop=0, transparency=255, disposal=1, optimize=False)
    chk = Image.open(path)          # self-check: the decoded last frame equals the source frame
    chk.seek(chk.n_frames - 1)
    assert chk.n_frames == len(frames) and ImageChops.difference(chk.convert('RGB'), S.big(frames[-1], k)).getbbox() is None, path


def gif(path, frames):
    """Full loop if it fits GIF_MAX, else a shorter preview loop (the animation itself keeps its frame count)."""
    for n in (len(frames), 48, 32, 24, 16):
        if n <= len(frames):
            save_gif(path, frames[:n])
            if os.path.getsize(path) <= GIF_MAX:
                return n
    raise AssertionError('GIF too large: ' + path)


def scroll_strip():
    """Gum Fling: field 512 px, field scroll 0..192, stands at 1/4, split centred at mid field. Rows: field scroll
    0, 64, 128, 192 (stand shift -24, -8, +8, +24), then raw stand shifts 64 and 128 (never reached at 1/4 speed)."""
    shifts = [(s - 96) // 4 for s in (0, 64, 128, 192)] + [64, 128]
    im = Image.new('RGB', (320, len(shifts) * 180 - 4), (255, 255, 255))
    for i, d in enumerate(shifts):
        fr = frame('moon', 'idle', 0, 8 + d).crop((0, 0, 320, 176))
        split = 160 - d
        assert 0 < split < 320, ('team split off screen', d)
        im.paste(fr, (0, i * 180))
    S.big(im, 2).save(S.out('scroll_strip_2x.png'))
    return shifts


def cell_sheet():
    im = Image.new('RGBA', (324, 11 * 18 + 2), (40, 40, 48, 255))
    for team in range(2):
        for j, t in enumerate('abc'):
            for i, p in enumerate('ABCDEF'):
                im.paste(S.img(cell2(BIRD[t][p], 0)[1], S.pal('moon', team, j, False)), (2 + 18 * (i + 6 * team), 2 + 18 * j))
    for i, (t, dy) in enumerate((('a', -8), ('b', -10), ('c', -6))):      # jump peak: head-room tile above the seat tile
        for team in range(2):
            top, bot = cell2(BIRD[t]['E'], dy)
            p = S.pal('moon', team, i, False)
            im.paste(S.img(bot, p), (2 + 18 * (2 * i + team), 2 + 18 * 4))
            im.alpha_composite(S.img(top, p), (2 + 18 * (2 * i + team), 2 + 18 * 3))
    for i in range(6):
        for j, md in enumerate(('idle', 'cheer')):
            top, bot = far_tiles('moon', md, 9 + i, 0, i + 7)
            p = S.pal('moon', 0 if i + 7 < 10 else 1, i % 3, True)
            im.paste(S.img(bot, p), (2 + 18 * (6 + i), 2 + 18 * (3 + j)))
    for y, line in zip((0, 16), scoreboard()):
        for i, (g, team, flip) in enumerate(line):
            im.alpha_composite(S.img(g, S.pal('moon', team, 0, False), flip), (2 + 16 * i, 2 + 18 * 5 + y))
    for n in range(10):
        im.paste(S.img(digit(n), S.pal('moon', 0, 0, False)), (2 + 18 * n, 2 + 18 * 7))
    im.alpha_composite(dusk_sky(), (2, 2 + 18 * 8))
    sh = Image.new('RGBA', (48, 32), S.FF.snap((70, 130, 60)) + (255,))
    for i, ch in enumerate('ABA'):
        sh.alpha_composite(S.img(SH['F'], ({'#': (10, 4, 22)}, 'sheet')), (16 * i, 0))
        sh.alpha_composite(S.img(SH[ch], ({'#': (10, 4, 22)}, 'sheet')), (16 * i, 16))
    im.paste(sh, (2, 2 + 18 * 9))
    S.big(im, 4).convert('RGB').save(S.out('sheet_cells_4x.png'))


def numbers(shifts, loops):
    L = []
    w = L.append
    w('Stadium polish 2026-11-18. Tile counts are the sets the script collected while drawing every frame (mirrored twins merged).')
    w('A bird cell is now 2 tiles (head room + seat); empty head-room tiles are the shared blank tile and not counted.')
    for wet in ('dry', 'storm'):
        w('')
        w('%s moods (%s):' % (wet, 'dusk, moon' if wet == 'dry' else 'storm, with umbrellas'))
        tot = set()
        for plane in ('struct', 'near', 'far'):
            allm = set()
            for (wk, pl, md), s in sorted(S.USED.items()):
                if wk == wet and pl == plane:
                    w('  %-6s %-5s %3d unique 16 x 16 tiles' % (plane, md, len(s)))
                    allm |= s
            w('  %-6s total %3d' % (plane, len(allm)))
            tot |= allm
        w('  stands total (structure with scoreboard + near + far, all animations): %d; plus towers 4, score digits 10' % len(tot))
    both = set().union(*(s for k, s in S.USED.items() if k[1] != 'digit'))
    w('')
    w('all three moods in one ROM: %d stand tiles + 4 tower + 10 score digits + 1 rain + 4 confetti' % len(both))
    w('scoreboard: 14 tile positions (7 x 2); %d unique frame tiles + 10 digit tiles; 4 digit positions change in game'
      % len({min(g, tuple(r[::-1] for r in g)) for line in scoreboard() for g, _, _ in line if g not in [digit(n) for n in range(10)]}))
    w('dusk light: sun 3 + roof glow 3 + turf shadow 3 = 9 tiles, plus 30 sun-rim variants of roof / balcony / board tiles (dusk only; counted in the dry struct total of 60, moon alone needs 30); no new palette')
    for wet, mood in (('dry', 'moon'), ('storm', 'storm')):
        ns = {tuple(near_tiles(mood, 'idle', 2 * s, r, c) for s in range(8)) for r in range(3) for c in range(21)}
        fs = {tuple(far_tiles(mood, 'idle', 2 * s, r, c) for s in range(8)) for r in range(2) for c in range(21)}
        ns, fs = {s for s in ns if len(set(s)) > 1}, {s for s in fs if len(set(s)) > 1}
        w('idle as hardware auto-animation, %s: near %d sequences = %d slots, far %d = %d slots (idle never enters the head-room tile)'
          % (wet, len(ns), 8 * len(ns), len(fs), 8 * len(fs)))
    w('')
    w('jump peaks: near cheer %s px, near wave %d px, far cheer %d px, far wave %d px (old: 2 / 2 / 1 / 1)'
      % (' / '.join(str(-min(dy for _, dy in S.CHEER[t])) for t in 'abc'), -min(dy for _, dy in S.WAVE['a']),
         -min(dy for _, dy in S.CHEER_F), -min(dy for _, dy in S.WAVE_F)))
    w('VRAM tile words per animation step, worst case: near 50 birds x 2 + far 36 tiles x 2 = 172 (old 86)')
    w('palettes per mood: unchanged, 19 (near crowd 6, far crowd 6, structure 2 + 2, turf, cone, rain)')
    w('')
    w('sprite strips: sky 20 (lines 0..31, the roof hides the rest), upper structure 21 (0..47: towers, scoreboard, roof),')
    w('  far row A 21 (32..63), far row B 21 (48..95, balcony front included), near rows 21 each (80..111, 96..127, 112..159 with')
    w('  the boards), turf 21, cones 14 (0..31), dusk sun + glow 20 (16..31), dusk shadow 20 (160..191), rain 11, confetti up to 12')
    w('sprites per scanline (limit 96), stadium only, dusk / moon / storm:')
    w('  lines   0..15   41 / 55 / 66')
    w('  lines  16..31   61 / 55 / 66')
    w('  lines  32..63   54 / 54 / 65   (two overlapping strips + confetti)')
    w('  lines  64..79   33 / 33 / 44')
    w('  lines  80..127  54 / 54 / 65')
    w('  lines 128..159  33 / 33 / 44')
    w('  lines 160..191  41 / 21 / 32')
    w('  lines 192..223  21 / 21 / 32')
    w('')
    w('Gum Fling scroll: field 512 px, field scroll 0..192, stands at 1/4 = 48 px of stand travel, split centred at mid field.')
    w('  stand shifts shown: %s px; team split at screen x %s' % (shifts, [160 - d for d in shifts]))
    w('  the split stays on screen for the whole travel (x 136..184). The 336 px stand is 16 px wider than the screen, so')
    w('  beyond a shift of +-8 px the repeat seam shows: up to 16 px of the other team at the screen edge at both field ends.')
    w('')
    w('GIF preview loops (frames shown of frames in the animation): '
      + (', '.join('%s %d/%d' % (k, v, NFR[k.split('_')[0]]) for k, v in sorted(loops.items()) if v != NFR[k.split('_')[0]]) or 'all full'))
    open(S.out('numbers.txt'), 'w').write('\n'.join(L) + '\n')
    print('\n'.join(L))


def html(loops, sizes):
    h = ['<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Gumbirds stadium polish</title><style>',
         'body{background:#14161c;color:#d8dce6;font:15px/1.5 system-ui,sans-serif;margin:24px}',
         'h1{font-size:22px}h2{font-size:18px;margin-top:36px;border-top:1px solid #333a48;padding-top:16px}',
         'img{image-rendering:pixelated;display:block;margin:8px 0 4px;max-width:100%;border:1px solid #333a48}',
         '.row{display:flex;flex-wrap:wrap;gap:16px}figure{margin:0 0 12px}figcaption{color:#98a0b0;font-size:13px}',
         '.pl img{background:#f0f}b{color:#fff}</style></head><body>',
         '<h1>Gumbirds stadium background, polish pass 2026-11-18</h1>',
         '<p>Left of each pair: the approved draft. Right: the polish pass (team clothes on the birds, roof scoreboard, '
         'tall cheer jumps, dusk sun light). Numbers and weak points: README.md and numbers.txt in this folder.</p>']
    cap = {'idle': 'Crowd idle', 'cheer': 'Cheer burst: Player 1 side, then Player 2 side',
           'wave': 'Stadium wave', 'win': 'Win wave: Player 1 wins, Player 2 side slumps'}
    for mood in MOODS:
        h.append('<h2>%s</h2><div class="row"><figure><img src="../scene_%s_2x.png"><figcaption>Old scene, 2x</figcaption></figure>'
                 '<figure><img src="scene_%s_2x.png"><figcaption><b>New</b> scene, idle frame 0, 2x</figcaption></figure></div>' % (mood.capitalize(), mood, mood))
        for md in MODES:
            n = '%s_%s_3x.gif' % (md, mood)
            if n in sizes:
                note = '' if loops[n[:-7]] == NFR[md] else ' (preview loop: first %d frames)' % loops[n[:-7]]
                h.append('<div class="row"><figure><img src="../%s"><figcaption>Old: %s</figcaption></figure>'
                         '<figure><img src="%s"><figcaption><b>New</b>: %s, %d frames at %d ms, 3x%s, %.1f MB</figcaption></figure></div>'
                         % (n, cap[md], n, cap[md], NFR[md], MS, note, sizes[n] / 1048576))
        h.append('<div class="row pl">')
        for pl in ('far', 'near') + (('sunglow', 'shadow') if mood == 'dusk' else ()):
            h.append('<figure><img src="plane_%s_%s_1x.png"><figcaption>New plane: %s, 1x (magenta is transparent)</figcaption></figure>' % (mood, pl, pl))
        h.append('</div>')
    h.append('<h2>Gum Fling scroll</h2><figure><img src="scroll_strip_2x.png"><figcaption>Moon, 2x, stands only. Rows 1 to 4: field scroll '
             '0, 64, 128, 192 px with the stands at 1/4 speed (stand shift -24, -8, +8, +24 px). Rows 5 and 6: raw stand shifts of 64 and 128 px, '
             'which 1/4 speed never reaches. The team split (centre stairs) stays on screen in every row. The repeat seam shows at the '
             'screen edge in rows 1, 4, 5, 6: the 336 px stand is only 16 px wider than the screen.</figcaption></figure>')
    h.append('<h2>Hand cells</h2><figure><img src="sheet_cells_4x.png"><figcaption>Rows 1 to 3: near birds a (scarf), b (beanie), c (cap) '
             'in six poses, Player 1 blue then Player 2 yellow. Rows 4 and 5: jump peaks across two tiles, far crowd tiles idle and cheer. '
             'Rows 6 and 7: scoreboard with the sample score. Row 8: the ten lamp digits. Row 9: dusk roof glow and sun. '
             'Rows 10 and 11: dusk turf shadow. Moon palettes, 4x.</figcaption></figure>')
    h.append('</body></html>')
    open(S.out('index.html'), 'w').write('\n'.join(h) + '\n')


def main():
    gifs = '--nogif' not in sys.argv
    loops, sizes = {}, {}
    for mood in MOODS:
        S.plane_png(far_plane(mood, 'idle', 0), 'plane_%s_far_1x.png' % mood)
        S.plane_png(near_plane(mood, 'idle', 0), 'plane_%s_near_1x.png' % mood)
        S.big(frame(mood, 'idle', 0), 2).save(S.out('scene_%s_2x.png' % mood))
        for md in MODES:
            frs = [frame(mood, md, f) for f in range(NFR[md])]
            if gifs:
                n = '%s_%s_3x.gif' % (md, mood)
                loops[n[:-7]] = gif(S.out(n), frs)
                sizes[n] = os.path.getsize(S.out(n))
                print('%-22s %2d of %2d frames %7.1f kB' % (n, loops[n[:-7]], len(frs), sizes[n] / 1024))
    S.plane_png(dusk_sky(), 'plane_dusk_sunglow_1x.png')
    S.plane_png(dusk_shadow(), 'plane_dusk_shadow_1x.png')
    shifts = scroll_strip()
    cell_sheet()
    numbers(shifts, loops)
    if gifs:
        html(loops, sizes)
        print('GIF total %.1f MB, largest %.2f MB' % (sum(sizes.values()) / 1048576, max(sizes.values()) / 1048576))


if __name__ == '__main__':
    main()
