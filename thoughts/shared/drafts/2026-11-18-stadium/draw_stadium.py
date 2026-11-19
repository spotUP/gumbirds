#!/usr/bin/env python3.14 -I
"""Gumbirds stadium background for the ground party events, art draft 2026-11-18 (not game code).

Every tile and crowd-bird cell below is a typed pixel grid (one character = one pixel). The script only stamps,
shifts (bob / jump in whole pixels), mirrors, palette-maps and counts those grids. Layouts, phases, flips, plumage
and umbrella seats are typed tables, no random numbers. Three things are computed and say so where they are made:
the straight edges of the floodlight cones, the far-plane haze mix of the hand-picked palettes, and the confetti
flight (gravity + drag + flutter from a typed particle table).

Reused: sky sheets of 2026-11-10-backgrounds-final (rows 0..63), turf and palettes of 2026-11-18-fling-field,
the player and rival frame 0 of assets/flier/sootling_sheet.png.

Run: /opt/homebrew/bin/python3.14 -I draw_stadium.py [--nogif]
"""
import json
import math
import os
import sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
DRAFTS = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(DRAFTS, '2026-11-18-fling-field'))
import draw_fling_field as FF  # noqa: E402  (turf(), snap(), BIRD path)

BG = os.path.join(DRAFTS, '2026-11-10-backgrounds-final')
MOODS = ('dusk', 'moon', 'storm')
MODES = ('idle', 'cheer', 'wave', 'win')
NFR = {'idle': 16, 'cheer': 64, 'wave': 64, 'win': 64}
MS = 70
MAGENTA = (255, 0, 255)


def out(n):
    return os.path.join(HERE, n)


def lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def mix(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def rows(d, w=16, h=16):
    """{row index: text} -> tuple of h rows; missing rows are empty."""
    g = tuple(d.get(j, '.' * w) for j in range(h))
    bad = [(j, r) for j, r in enumerate(g) if len(r) != w]
    assert not bad, bad
    return g


def full(lst, w=16):
    bad = [(j, r) for j, r in enumerate(lst) if len(r) != w]
    assert not bad and len(lst) in (8, 16), (bad, len(lst))
    return tuple(lst)


# ---------------------------------------------------------------- palettes (hand-picked, 15 colours + transparent)
# stand roles: K outline, a b c d concrete dark..lit, W white, y beak / lamp glow, o beak shade, L l lamp face (off at dusk)
STAND = {
    'dusk':  dict(K=(10, 4, 22), a=(52, 24, 70), b=(112, 52, 98), c=(170, 90, 104), d=(236, 156, 112), W=(255, 244, 214),
                  y=(255, 198, 90), o=(231, 90, 41), L=(112, 52, 98), l=(52, 24, 70)),
    'moon':  dict(K=(4, 4, 18), a=(26, 32, 76), b=(54, 68, 134), c=(92, 116, 180), d=(164, 192, 234), W=(236, 244, 255),
                  y=(240, 214, 120), o=(214, 96, 60), L=(255, 255, 255), l=(190, 230, 255)),
    'storm': dict(K=(4, 8, 14), a=(24, 40, 52), b=(54, 84, 98), c=(98, 136, 142), d=(172, 208, 204), W=(230, 244, 236),
                  y=(224, 208, 110), o=(196, 96, 56), L=(240, 255, 240), l=(170, 230, 220)),
}
# team roles t (dark) T (light): P1 = sootling blue, P2 = the sun yellow swap
TEAM = {
    'dusk':  [((48, 56, 140), (104, 140, 214)), ((214, 120, 40), (255, 206, 90))],
    'moon':  [((36, 64, 150), (90, 160, 230)), ((196, 136, 48), (250, 220, 104))],
    'storm': [((34, 66, 126), (84, 150, 196)), ((180, 130, 50), (236, 212, 100))],
}
# plumage roles 1 2 3 + rim light r; three plumages (plum, teal, grey), none of them a team colour
PLUM = {
    'dusk':  [((70, 20, 70), (136, 48, 100), (204, 96, 112), (255, 180, 120)),
              ((36, 48, 84), (60, 104, 108), (128, 164, 116), (255, 214, 130)),
              ((70, 44, 84), (130, 92, 116), (196, 150, 140), (255, 220, 170))],
    'moon':  [((64, 28, 84), (124, 60, 128), (188, 112, 176), (244, 200, 236)),
              ((16, 60, 76), (36, 116, 112), (96, 180, 150), (200, 244, 214)),
              ((48, 48, 84), (100, 104, 144), (164, 172, 204), (236, 240, 255))],
    'storm': [((52, 30, 70), (104, 64, 112), (160, 116, 160), (226, 214, 236)),
              ((14, 56, 62), (34, 108, 98), (90, 168, 136), (196, 240, 214)),
              ((40, 52, 68), (88, 108, 124), (150, 176, 180), (226, 244, 240))],
}
HAZE = {'dusk': (190, 90, 96), 'moon': (72, 66, 142), 'storm': (60, 90, 100)}   # far plane: palette mixed 20 percent to this
HAZE_T = 0.2
CONE = {'moon': (120, 140, 220), 'storm': (120, 160, 160)}
RAINC = (150, 190, 196)

_PAL = {}


def pal(mood, team, var, far):
    key = (mood, team, var, far)
    if key not in _PAL:
        d = dict(STAND[mood])
        d.update(zip('tT', TEAM[mood][team]))
        d.update(zip('123r', PLUM[mood][var]))
        if far:
            d = {k: (v if k in 'LlWK' else mix(v, HAZE[mood], HAZE_T)) for k, v in d.items()}
        _PAL[key] = {k: FF.snap(tuple(v)) for k, v in d.items()}
    return _PAL[key], key


# ---------------------------------------------------------------- near crowd birds, 16 x 16 cells (bird only; rows 13..15 are the ledge)
A_A = {3: '.......oy.......', 4: '.....KKoyKK.....', 5: '....K2233rrK....', 6: '...K122333rrK...',
       7: '...K1WK23WK3K...', 8: '...K1WKyyWK3K...', 9: '..oK112oo223Ko..', 10: '..oK11222223Ko..',
       11: '...KtTtTTtTtK...', 12: '...KttTTTTttK...'}
A_B = A_A | {9: '..oK112KK223Ko..', 10: '..oK112oo223Ko..'}
A_C = {5: '.......oy.......', 6: '....KKKoyKKK....', 7: '..K12223333rrK..', 8: '..K1KK2233KK3K..',
       9: '.oK1122yy2233Ko.', 10: '.oK1122oo2233Ko.', 11: '..KtTtTTtTTtTK..', 12: '..KttTTTTTTttK..'}
A_D = A_A | {7: 'yo.K1WK23WK3K.oy', 8: '.ooK1WKyyWK3Koo.', 9: '...K112KK223K...', 10: '...K112oo223K...'}
A_E = A_A | {2: '.y............y.', 3: '.oy....oy....yo.', 4: '..oo.KKoyKK.oo..', 5: '..ooK2233rrKoo..',
             9: '...K112KK223K...', 10: '...K112KK223K...'}
A_F = A_E | {2: '...y........y...', 3: '..yo...oy...oy..'}

B_A = {2: '......o.y.......', 3: '......oyy.......', 4: '.....KKKKKK.....', 5: '....K2333rrK....',
       6: '....K2233r3K....', 7: '....KWK2WK3K....', 8: '....KWK2WK3K....', 9: '....K12yy23K....',
       10: '...oK12oo23Ko...', 11: '...oKtTtTTtKo...', 12: '....KttTTttK....'}
B_B = B_A | {10: '...oK12KK23Ko...'}
B_C = {4: '......o.y.......', 5: '......oyy.......', 6: '....KKKKKKKK....', 7: '...K22333rrrK...',
       8: '...K1KK22KK3K...', 9: '...K112yy233K...', 10: '..oK112oo233Ko..', 11: '..oKtTtTTtTtKo..',
       12: '...KttTTTTttK...'}
B_D = B_A | {8: '.yo.KWK2WK3K.oy.', 9: '..ooK12yy23Koo..', 10: '....K12KK23K....', 11: '....KtTtTTtK....'}
B_E = B_A | {2: '..y...o.y....y..', 3: '..oy..oyy...yo..', 4: '...ooKKKKKKoo...', 9: '....K12KK23K....',
             10: '....K12KK23K....', 11: '....KtTtTTtK....'}
B_F = B_E | {2: '....y.o.y..y....', 3: '...yo.oyy..oy...'}

C_A = {4: '.....tTTTT......', 5: '....tTTTTTTTT...', 6: '...KKKKKKKKKK...', 7: '..K122233333rK..',
       8: '..K1WK2233WK3K..', 9: '..K1WK22yyWK3K..', 10: '.oK11222oo233Ko.', 11: '.oK1122222233Ko.',
       12: '..KtTtTTtTTtTK..'}
C_B = C_A | {10: '.oK11222KK233Ko.'}
C_C = {5: '.....tTTTT......', 6: '....tTTTTTTTT...', 7: '..KKKKKKKKKKKK..', 8: '.K12223333333rK.',
       9: '.K1KK2233KK33rK.', 10: 'oK11222yy22333Ko', 11: 'oK11222oo22333Ko', 12: '.KtTtTTtTTtTtTK.'}
C_D = C_A | {8: 'yoK1WK2233WK3Koy', 9: '.oK1WK22yyWK3Ko.', 10: '..K11222KK233K..', 11: '..K1122222233K..'}
C_E = C_A | {2: 'y..............y', 3: 'oy............yo', 4: '.oo..tTTTT...oo.', 5: '.oo.tTTTTTTTToo.',
             6: '..oKKKKKKKKKKo..', 10: '..K11222KK233K..', 11: '..K11222KK233K..'}
C_F = C_E | {2: '..y..........y..', 3: '.yo..........oy.'}

UMB = {2: '.......KK.......', 3: '....KKKTTKKK....', 4: '..KKtTTTTTTTKK..', 5: '.KttTTTTTTTTrTK.',
       6: 'KtttTTtTTTtTTrTK', 7: 'KKtKKtKKKtKKtKKK', 8: '....K22KK3rK....', 9: '...K1WK2KWK3K...',
       10: '...K112yyK23K...', 11: '...KtTtTTKTtK...', 12: '...KttTTTKttK...'}

BIRD = {t: {p: rows(g) for p, g in zip('ABCDEF', gs)} for t, gs in
        (('a', (A_A, A_B, A_C, A_D, A_E, A_F)), ('b', (B_A, B_B, B_C, B_D, B_E, B_F)), ('c', (C_A, C_B, C_C, C_D, C_E, C_F)))}
UMB = rows(UMB)

SEAT_BG = full([
    'aaaaaaaaaaaaaaaa', 'aaaaaaaaaaaaaaaa', 'aabaaaaaaaaabaaa', 'aaaaaaabaaaaaaaa',
    'abaaaaaaaaaaaaba', 'aaaabaaaaabaaaaa', 'aabaaaabaaaaabaa', 'babaabaaabaabaab',
    'abababbababbabab', 'bbabbbabbbabbbab', 'bbbbbbbbbbbbbbbb', 'bcbbbbbcbbbbcbbb',
    'bbbbbbbbbbbbbbbb', 'dddddddddddddcdd', 'ccccccdccccccccc', 'cbccccccbcccccbc'])
EMPTY = rows({6: '...KKKKKKKKKK...', 7: '...KccccccdcK...', 8: '...KcbccccccK...', 9: '...KccccccbcK...',
              10: '...KbbbbbbbbK...', 11: '....KbKKKKbK....', 12: '....Kb....bK....'})
AISLE = full([
    'KdddddddddddddcK', 'KccccccccccccccK', 'KbbbbbbbbbbbbbbK', 'KbabbbbabbbbbabK',
    'KyddddddddddddyK', 'KcccccccccccbccK', 'KbbbbbbbbbbbbbbK', 'KabbbabbbbabbbbK',
    'KdddddddddddcddK', 'KccccccccccccccK', 'KbbbbbbbbbbbbbbK', 'KbbbabbbbbbabbaK',
    'KyddddddddddddyK', 'KccbcccccccccccK', 'KbbbbbbbbbbbbbbK', 'KbabbbbbabbbbbbK'])

# ---------------------------------------------------------------- far crowd birds, 8 x 8 cells (row 7 is the ledge)
FARB = {
    'a': dict(A=['........', '...oy...', '.K233rK.', '.KW2W3K.', '.K12y3K.', '.K1223K.', '.KtTTtK.', '........'],
              B=['........', '...oy...', '.K233rK.', '.KW2W3K.', '.K1KK3K.', '.K1223K.', '.KtTTtK.', '........'],
              E=['y......y', 'o..oy..o', 'oK233rKo', '.KW2W3K.', '.K1KK3K.', '.K1223K.', '.KtTTtK.', '........'],
              F=['.y....y.', '.o.oy.o.', 'oK233rKo', '.KW2W3K.', '.K1KK3K.', '.K1223K.', '.KtTTtK.', '........']),
    'b': dict(A=['........', '........', '..tTTTT.', '.KKKKKK.', 'K2W3W3rK', 'K12yy23K', 'KtTtTTtK', '........'],
              B=['........', '........', '..tTTTT.', '.KKKKKK.', 'K2W3W3rK', 'K12KK23K', 'KtTtTTtK', '........'],
              E=['y......y', 'oo....oo', '.otTTTo.', '.KKKKKK.', 'K2W3W3rK', 'K12KK23K', 'KtTtTTtK', '........'],
              F=['........', '.y....y.', '.otTTTo.', '.KKKKKK.', 'K2W3W3rK', 'K12KK23K', 'KtTtTTtK', '........']),
}
FAR_UMB = ['..KKKK..', '.KTTTTK.', 'KtTTTTrK', 'KKtKKtKK', '.KW2W3K.', '.K12y3K.', '.KtTTtK.', '........']
FAR_BG = ['aaaaaaaa', 'aaaaaaaa', 'aaaaaaaa', 'aabaaaaa', 'aaaaabaa', 'abaaaaab', 'babababb', 'cccccdcc']
for _g in [FAR_UMB, FAR_BG] + [g for t in FARB.values() for g in t.values()]:
    assert len(_g) == 8 and all(len(r) == 8 for r in _g), _g

# ---------------------------------------------------------------- structure tiles
ROOF = full([
    'dddddddddddddddd', 'cccccccccccccccc', 'cbcccccbccccbccc', 'bbbbbbbbbbbbbbbb',
    'KKKKKKKKKKKKKKKK', 'aaaaaaaaaaaaaaaa', 'aaaaaaaaaaaaaaaa', 'aaaaaaaaaaaaaaaa',
    'KKaaaaaaaaaaaaKK', 'aKKaaaaaaaaaaKKa', 'aaaKKaaaaaaKKaaa', 'aaaaaKKaaKKaaaaa',
    'aaaaaaaKKaaaaaaa', 'aaaaaaaaaaaaaaaa', 'aaaaaaaaaaaaaaaa', 'aaaaaaaaaaaaaaaa'])
ROOF_LAMP = full(list(ROOF[:5]) + ['aaaaabdLLdbaaaaa', 'aaaaaabllbaaaaaa', 'aaaaaaabbaaaaaaa'] + list(ROOF[8:]))
FASCIA = full([
    'dddddddddddddddd', 'KaKaKaKaKaKaKaKa', 'KaKaKaKaKaKaKaKa', 'cccccccccccccccc',
    'dddddddddddddddd', 'cccccccccccccccc', 'ccbcccccccbccccc', 'bcbcbcbcbcbcbcbc',
    'bbbbbbbbbbbbbbbb', 'babbbabbbabbbabb', 'abababababababab', 'aaaaaaaaaaaaaaaa',
    'aaaaaaaaaaaaaaaa', 'aaaaaaaaaaaaaaaa', 'KKKKKKKKKKKKKKKK', 'KKKKKKKKKKKKKKKK'])
BANNER = rows({4: '.KKKKKKKKKKKKKK.', 5: '.KTTTTTTTTTTTTK.', 6: '.KTtTTWWWWTTtTK.', 7: '.KtTTWTTTTWTTtK.',
               8: '.KtTTWTTWTWTTtK.', 9: '.KttTWTTTTWTttK.', 10: '.KtttTWWWWTtttK.', 11: '..KKttttttttKK..',
               12: '....KKKKKKKK....'})
BOARD = full([
    'dddddddddddddddd', 'cccccccccccccccc', 'KKKKKKKKKKKKKKKK', 'TTTTTTTTTTTTTTTT',
    'tTtTTtTtTtTTtTtT', 'tttttttttttttttt', 'tttttttttttttttt', 'tttttttttttttttt',
    'tttttttttttttttt', 'tttttttttttttttt', 'tttttttttttttttt', 'tttttttttttttttt',
    'tttKtttttKttttKt', 'tKtKKtKtKKtKtKKt', 'KKKKKKKKKKKKKKKK', 'aKaaKaaaKaKaaKaa'])
GLYPH = {
    'G': ('.###.', '#...#', '#....', '#.###', '#...#', '#...#', '.###.'),
    'U': ('#...#', '#...#', '#...#', '#...#', '#...#', '#...#', '.###.'),
    'M': ('#...#', '##.##', '#.#.#', '#.#.#', '#...#', '#...#', '#...#'),
    '!': ('..#..', '..#..', '..#..', '..#..', '..#..', '.....', '..#..'),
    'P': ('####.', '#...#', '#...#', '####.', '#....', '#....', '#....'),
    'O': ('.###.', '#...#', '#...#', '#...#', '#...#', '#...#', '.###.'),
    'B': ('####.', '#...#', '#...#', '####.', '#...#', '#...#', '####.'),
    'L': ('#....', '#....', '#....', '#....', '#....', '#....', '#####'),
    'W': ('#...#', '#...#', '#...#', '#.#.#', '#.#.#', '##.##', '#...#'),
}
_LL = 'c' + 'LLcc' * 6 + 'LLc'       # one lamp row: seven lamps, typed fragment repeated
_Ll = _LL.replace('L', 'l')
_M4 = ['.............KcKKbK.............', '.............KccbbK.............',
       '.............KcKKbK.............', '.............KKccKK.............']
HEAD = full(['..' + 'K' * 28 + '..', '.K' + 'd' * 28 + 'K.', '.K' + _LL + 'K.', '.K' + _Ll + 'K.', '.K' + 'b' * 28 + 'K.',
             '.K' + _LL + 'K.', '.K' + _Ll + 'K.', '.K' + 'b' * 28 + 'K.', '.K' + _LL + 'K.', '.K' + _Ll + 'K.',
             '.K' + 'a' * 28 + 'K.', '..' + 'K' * 28 + '..'] + _M4, 32)
MAST = full(_M4 * 4, 32)
RAIN = full([
    '.......#........', '......#.........', '......#......#..', '.............#..',
    '..#.........#...', '..#.............', '.#..............', '.........#......',
    '.........#......', '........#.......', '...............#', '....#..........#',
    '....#.........#.', '...#............', '...........#....', '..........#.....'])
ROFF = [0, 7, 3, 11, 5, 13, 1, 9, 4, 12, 6, 14, 2, 10, 8, 15, 3, 9, 0, 6, 12, 5]      # rain tile row offset per column
# cone dither, three hand patterns (16 x 4), density falls with distance from the lamp
CONE_PAT = [('###.##.###.#.###', '#.###.###.###.#.', '##.#.###.##.####', '.###.#.###.###.#'),
            ('#.#..#.#.##.#..#', '.#.##.#..#.#.#.#', '#..#.#.#.#..#.#.', '.#.#..#.#.#.#.##'),
            ('#...#.....#..#..', '..#....#.....#..', '.....#....#....#', '.#......#....#..')]

# ---------------------------------------------------------------- typed layouts (21 tile columns = 336 px; column 10 is the centre aisle)
NT = ['cabsacebacsbacabcsabc', 'bcasbaacbesacbcaesbca', 'acbscbabcasceabacsacb']      # a b c bird type, e empty seat, s stairs
NV = ['012012201102210021120', '120201012210102120012', '201120120021021201201']      # plumage
NF = ['010011010010110100101', '101100101101001011010', '011010010110100101100']      # mirrored
NP = ['052741630427163052741', '316205274051427361630', '740316251637405216374']      # idle phase 0..7
NU = ['010000100000001000010', '000010000100100000100', '100000001000000100001']      # storm: umbrella seat
BLOCKS = {      # far tier: one 16 x 16 tile = four far birds (type, mirrored, phase)
    'A': [('a', 0, 0), ('b', 1, 3), ('b', 0, 5), ('a', 1, 2)],
    'B': [('b', 0, 6), ('a', 0, 1), ('a', 1, 4), ('a', 0, 7)],
    'C': [('a', 1, 2), ('a', 0, 6), ('b', 1, 0), ('b', 0, 3)],
    'D': [('b', 1, 4), ('b', 0, 0), ('a', 0, 3), ('e', 0, 0)],
    'E': [('a', 0, 7), ('b', 1, 2), ('e', 0, 0), ('a', 1, 5)],
}
FB = ['ABCDEASBCASEDBSACEBDA', 'CEABDCSADESBACSDBAECB']
FV = ['201102010212001120210', '120210021001220112021']
FP = ['305172640351726403517', '627304153726041536270']
FU = {(0, 1, 2), (0, 4, 0), (0, 8, 3), (0, 12, 1), (0, 16, 2), (0, 19, 0), (1, 2, 1), (1, 5, 3), (1, 9, 0), (1, 13, 2), (1, 17, 1), (1, 20, 3)}
ROOFROW = 'RRLRRRLRRRLRRRLRRRLRR'
FASROW = 'FBFFFBFFBFFFBFFBFFFBF'
BOARDROW = '-GUM!-POP!--BLOW-GUM!'
TOWERS = (40, 264)          # plane x of the two floodlight heads (32 px wide)
for _r in NT + NV + NF + NP + NU + FB + FV + FP + [ROOFROW, FASROW, BOARDROW]:
    assert len(_r) == 21, _r
assert all(r[3] == r[10] == r[17] == 's' for r in NT) and all(r[6] == r[10] == r[14] == 'S' for r in FB)

# ---------------------------------------------------------------- typed motion: (pose, dy) per step
IDLE = {'a': [('A', 0), ('A', 0), ('A', -1), ('B', -1), ('A', 0), ('B', 0), ('A', 0), ('A', 0)],
        'b': [('A', 0), ('A', -1), ('A', -1), ('A', 0), ('A', 0), ('B', 0), ('B', -1), ('A', 0)],
        'c': [('A', 0), ('B', 0), ('A', 0), ('A', 0), ('A', -1), ('A', -1), ('B', 0), ('A', 0)]}
# cheer: crouch, rise, peak with wing flutter, fall with the wings still up (follow-through), land squash, rebound
CHEER = {'a': [('C', 0), ('D', -1), ('E', -2), ('F', -2), ('E', -2), ('F', -1), ('D', 0), ('C', 0), ('A', -1), ('D', -1),
               ('E', -2), ('F', -2), ('E', -1), ('D', 0), ('C', 0), ('A', -1), ('A', 0)],
         'b': [('C', 0), ('C', 0), ('D', -1), ('E', -2), ('F', -2), ('E', -2), ('F', -2), ('E', -2), ('F', -1), ('D', 0),
               ('C', 0), ('A', -1), ('A', 0)],
         'c': [('C', 0), ('D', -1), ('E', -2), ('E', -2), ('F', -2), ('F', -1), ('D', 0), ('C', 0), ('C', 0), ('A', -1), ('A', 0)]}
WAVE = {t: [('C', 0), ('D', -1), ('E', -2), ('E', -2), ('F', -2), ('F', -1), ('D', 0), ('C', 0), ('A', 0)] for t in 'abc'}
SLUMP = [('C', 0), ('C', 0), ('C', 1), ('C', 0)]
IDLE_F = [('A', 0), ('A', 0), ('A', -1), ('B', -1), ('A', 0), ('A', 0), ('B', 0), ('A', 0)]
CHEER_F = [('A', -1), ('E', 0), ('F', 0), ('E', 0), ('F', 0), ('E', 0), ('F', 0), ('E', 0), ('A', -1), ('A', 0)]
WAVE_F = [('A', -1), ('E', 0), ('E', 0), ('F', 0), ('E', 0), ('A', -1), ('A', 0)]
CHEER_AT = (6, 36)          # cheer GIF: P1 half scores at frame 6, P2 half at frame 36
# confetti: (vx, vy, colour 0 team light / 1 white / 2 team dark, flutter phase), one burst = these 12 pieces
PARTS = [(-2.6, -3.4, 0, 0), (-1.8, -4.2, 1, 2), (-1.0, -3.0, 2, 4), (-0.4, -4.6, 0, 1), (0.3, -3.8, 1, 5), (0.9, -4.4, 0, 3),
         (1.5, -3.2, 2, 0), (2.2, -4.0, 1, 4), (2.8, -2.8, 0, 2), (-2.2, -2.4, 1, 1), (0.0, -5.0, 2, 3), (1.9, -2.2, 0, 5)]
LIFE = 28
BURSTS = {      # (start frame, screen x, y, team)
    'cheer': [(8, 44, 72, 0), (9, 104, 60, 0), (10, 132, 110, 0), (8, 72, 122, 0),
              (38, 196, 64, 1), (39, 250, 112, 1), (40, 284, 72, 1), (38, 222, 124, 1)],
    'win': [(0, 40, 70, 0), (4, 118, 62, 0), (16, 76, 116, 0), (22, 136, 104, 0), (32, 28, 110, 0), (38, 96, 66, 0),
            (48, 60, 76, 0), (54, 128, 120, 0)],
}


def near_state(mode, f, r, c):
    t, ph, team = NT[r][c], int(NP[r][c]), 0 if c < 10 else 1
    idle = IDLE[t][(f // 2 + ph) % 8]
    lag = c * 2 + (2 - r) + ph % 2          # the wave runs left to right, front row first
    if mode == 'cheer':
        q = f - CHEER_AT[team] - ph % 4
        return CHEER[t][q] if 0 <= q < len(CHEER[t]) else idle
    if mode == 'wave':
        q = f - 4 - lag
        return WAVE[t][q] if 0 <= q < len(WAVE[t]) else idle
    if mode == 'win':                       # P1 wins: its half rolls a wave every 16 frames, the P2 half slumps
        if team:
            return SLUMP[(f // 8 + ph) % 4]
        q = (f - lag) % 16
        return WAVE[t][q] if q < len(WAVE[t]) else idle
    return idle


def far_state(mode, f, row, bc, ph):
    team, bp = 0 if bc < 10 else 1, int(FP[row][bc])
    idle = IDLE_F[(f // 2 + ph + bp) % 8]
    lag = bc * 2 + 4 + (1 - row)            # all four birds of a tile move together in events (tile budget)
    if mode == 'cheer':
        q = f - CHEER_AT[team] - bp % 3
        return CHEER_F[q] if 0 <= q < len(CHEER_F) else idle
    if mode == 'wave':
        q = f - 4 - lag
        return WAVE_F[q] if 0 <= q < len(WAVE_F) else idle
    if mode == 'win':
        if team:
            return ('A', 0)
        q = (f - lag) % 16
        return WAVE_F[q] if q < len(WAVE_F) else idle
    return idle


# ---------------------------------------------------------------- assembly
_CELL, _IMG, USED = {}, {}, {}


def cell(bird, dy):
    key = (bird, dy)
    if key not in _CELL:
        g = [list(r) for r in SEAT_BG]
        for j, row in enumerate(bird):
            if 0 <= j + dy < 13:
                for i, ch in enumerate(row):
                    if ch != '.':
                        g[j + dy][i] = ch
            else:       # a slumped bird may sink behind the ledge (rows 13..15); nothing may leave the top
                assert j + dy >= 13 or set(row) == {'.'}, ('bird pixel leaves its cell', dy, j, row)
        _CELL[key] = tuple(''.join(r) for r in g)
    return _CELL[key]


def img(grid, p, flip=False):
    key = (grid, p[1], flip)
    if key not in _IMG:
        im = Image.new('RGBA', (len(grid[0]), len(grid)), (0, 0, 0, 0))
        px = im.load()
        for j, row in enumerate(grid):
            for i, ch in enumerate(row[::-1] if flip else row):
                if ch != '.':
                    px[i, j] = p[0][ch] + (255,)
        _IMG[key] = im
    return _IMG[key]


def near_grid(mood, mode, f, r, c):
    t = NT[r][c]
    if t == 's':
        return AISLE
    if t == 'e':
        return cell(EMPTY, 0)
    pose, dy = near_state(mode, f, r, c)
    if mood == 'storm' and NU[r][c] == '1':     # umbrella is pumped up on a cheer instead of the wings
        return cell(UMB, -2 if pose in 'EF' else -1 if pose == 'D' else 0)
    return cell(BIRD[t][pose], dy)


def far_grid(mood, mode, f, row, bc):
    name = FB[row][bc]
    if name == 'S':
        return AISLE
    g = [list(FAR_BG[j % 8] * 2) for j in range(16)]
    for k, (t, flip, ph) in enumerate(BLOCKS[name]):
        if t == 'e':
            continue
        if mood == 'storm' and (row, bc, k) in FU:
            b, dy = FAR_UMB, 0
        else:
            pose, dy = far_state(mode, f, row, bc, ph)
            b = FARB[t][pose]
        for j, rw in enumerate(b):
            if 0 <= j + dy < 7:
                for i, ch in enumerate(rw[::-1] if flip else rw):
                    if ch != '.':
                        g[(k // 2) * 8 + j + dy][(k % 2) * 8 + i] = ch
    return tuple(''.join(r) for r in g)


def board(ch, team):
    g = [list(r) for r in BOARD]
    if ch in GLYPH:
        for j, rw in enumerate(GLYPH[ch]):
            for i, c in enumerate(rw):
                if c == '#':
                    g[5 + j][5 + i] = 'W' if team == 0 else 'K'      # white on blue, dark on yellow
    return tuple(''.join(r) for r in g)


def over(a, b):
    return tuple(''.join(cb if cb != '.' else ca for ca, cb in zip(ra, rb)) for ra, rb in zip(a, b))


def use(mood, plane, mode, grid):
    USED.setdefault(('storm' if mood == 'storm' else 'dry', plane, mode), set()).add(min(grid, tuple(r[::-1] for r in grid)))


def far_plane(mood, mode, f):
    """336 x 96: tower heads 0..15, masts 16..31, roof 32..47, far crowd 48..79, balcony front 80..95."""
    im = Image.new('RGBA', (336, 96), (0, 0, 0, 0))
    for c in range(21):
        team = 0 if c < 10 else 1
        sp = pal(mood, team, 0, True)
        for g, y in ((ROOF_LAMP if ROOFROW[c] == 'L' else ROOF, 32), (over(FASCIA, BANNER) if FASROW[c] == 'B' else FASCIA, 80)):
            im.paste(img(g, sp), (16 * c, y))
            use(mood, 'struct', 'all', g)
        for row in range(2):
            g = far_grid(mood, mode, f, row, c)
            im.paste(img(g, pal(mood, team, int(FV[row][c]), True)), (16 * c, 48 + 16 * row))
            use(mood, 'far', mode, g)
    for x in TOWERS:
        sp = pal(mood, 0, 0, True)
        im.alpha_composite(img(HEAD, sp), (x, 0))
        im.alpha_composite(img(MAST, sp), (x, 16))
    return im


def near_plane(mood, mode, f):
    """336 x 64: three crowd rows 0..47 (screen 96..143), barrier boards 48..63 (screen 144..159)."""
    im = Image.new('RGBA', (336, 64), (0, 0, 0, 0))
    for c in range(21):
        team = 0 if c < 10 else 1
        g = board(BOARDROW[c], team)
        im.paste(img(g, pal(mood, team, 0, False)), (16 * c, 48))
        use(mood, 'struct', 'all', g)
        for r in range(3):
            g = near_grid(mood, mode, f, r, c)
            im.paste(img(g, pal(mood, team, int(NV[r][c]), False), NF[r][c] == '1' and NT[r][c] not in 's'), (16 * c, 16 * r))
            use(mood, 'near', mode, g)
    return im


def cones(mood):
    """320 x 48 overlay, one colour. Edges are straight lines from the lamp head (computed); the fill is the hand patterns."""
    im = Image.new('RGBA', (320, 48), (0, 0, 0, 0))
    if mood == 'dusk':
        return im
    px, col = im.load(), FF.snap(CONE[mood]) + (255,)
    for tx, sgn in ((TOWERS[0] - 8 + 16, 1), (TOWERS[1] - 8 + 16, -1)):
        for y in range(3, 48):
            d = y - 3
            lo, hi = sorted((tx - sgn * (13 + 0.2 * d), tx + sgn * (13 + 1.6 * d)))
            pat = CONE_PAT[0 if d < 9 else 1 if d < 22 else 2]
            for x in range(max(0, round(lo)), min(320, round(hi) + 1)):
                if pat[y % 4][x % 16] == '#':
                    px[x, y] = col
    return im


def keyed(path):
    p = Image.open(path).convert('RGBA')
    px = p.load()
    for y in range(p.height):
        for x in range(p.width):
            if px[x, y][:3] == MAGENTA:
                px[x, y] = (0, 0, 0, 0)
    return p


def pair():
    """Ground-event bird pair from the flier sheet: player frame 0 and rival (cpu) frame 0, facing each other."""
    sheet = Image.open(FF.BIRD).convert('RGBA')
    an = json.load(open(FF.BIRD.replace('.png', '.json')))['animations']
    res = []
    for k in ('player', 'cpu'):
        r = an[k][0]
        fr = sheet.crop((r['x'], r['y'], r['x'] + r['w'], r['y'] + r['h']))
        res.append(fr.crop(fr.getbbox()))
    return res[0], res[1].transpose(Image.FLIP_LEFT_RIGHT)


_STATIC = {}


def static(mood):
    if mood not in _STATIC:
        back = Image.new('RGBA', (320, 224), (0, 0, 0, 255))
        back.alpha_composite(keyed(os.path.join(BG, 'plane_%s_sky_1x.png' % mood)).crop((0, 0, 320, 64)))
        back.alpha_composite(cones(mood))
        front = Image.new('RGBA', (320, 224), (0, 0, 0, 0))
        front.alpha_composite(FF.turf(mood), (0, 160))
        a, b = pair()
        front.alpha_composite(a, (112 - a.width // 2, 161 - a.height))
        front.alpha_composite(b, (208 - b.width // 2, 161 - b.height))
        _STATIC[mood] = (back, front)
    return _STATIC[mood]


def confetti(im, mood, mode, f, n):
    px = im.load()
    for f0, x0, y0, team in BURSTS.get(mode, ()):
        t = (f - f0) % n
        if t >= LIFE:
            continue
        p = pal(mood, team, 0, False)[0]
        for vx, vy, kind, ph in PARTS:
            x, y = float(x0), float(y0)
            for s in range(t):          # baked flight: drag on vx, gravity with a terminal fall speed, sideways flutter
                vx *= 0.9
                vy = min(vy + 0.45, 1.4)
                x += vx + 0.8 * math.sin((s + ph) * 0.9)
                y += vy
            col = (p['T'], p['W'], p['t'])[kind] + (255,)
            for dx, dy in ((0, 0), (1, 0)) if (t + ph) // 2 % 2 else ((0, 0), (0, 1)):      # tumble: flat, then on edge
                if 0 <= round(x) + dx < 320 and 0 <= round(y) + dy < 160:
                    px[round(x) + dx, round(y) + dy] = col


def rain(im, f):
    t = img(RAIN, ({'#': FF.snap(RAINC)}, 'rain'))
    for c in range(22):
        for r in range(-1, 15):
            y = r * 16 + (ROFF[c] + f * 6) % 16
            if y >= 0 and (c + r) % 2 == 0:     # checkerboard of rain tiles: half density keeps the crowd readable
                im.alpha_composite(t, (c * 16 - f * 2 % 16, y))


def frame(mood, mode, f):
    back, front = static(mood)
    im = back.copy()
    im.alpha_composite(far_plane(mood, mode, f).crop((8, 0, 328, 96)))
    im.alpha_composite(near_plane(mood, mode, f).crop((8, 0, 328, 64)), (0, 96))
    im.alpha_composite(front)
    confetti(im, mood, mode, f, NFR[mode])
    if mood == 'storm':
        rain(im, f)
    return im.convert('RGB')


def big(im, k):
    return im.resize((im.width * k, im.height * k), Image.NEAREST)


def save_gif(path, frames, k=3):
    cols = set()
    for fr in frames:
        cols.update(c for _, c in fr.getcolors(200000))
    assert len(cols) <= 256, ('too many colours for one GIF palette', len(cols))
    flat = [v for c in sorted(cols) for v in c]
    p = Image.new('P', (1, 1))
    p.putpalette(flat + [0] * (768 - len(flat)))
    q = [big(fr.quantize(palette=p, dither=Image.Dither.NONE), k) for fr in frames]
    q[0].save(path, save_all=True, append_images=q[1:], duration=MS, loop=0, optimize=False)
    return len(cols)


def plane_png(im, name):
    bgm = Image.new('RGBA', im.size, MAGENTA + (255,))
    bgm.alpha_composite(im)
    assert not any(px[:3] == MAGENTA and px[3] for px in im.getdata()), 'magenta in art'
    bgm.convert('RGB').save(out(name))


def cell_sheet():
    """All hand cells at 4x on the moon palettes: near types x poses, umbrella, empty, stairs; far cells at 8x below."""
    im = Image.new('RGBA', (8 * 18 + 2, 4 * 18 + 2 + 3 * 18), (40, 40, 48, 255))
    for j, t in enumerate('abc'):
        for i, p in enumerate('ABCDEF'):
            im.paste(img(cell(BIRD[t][p], 0), pal('moon', j % 2, j, False)), (2 + 18 * i, 2 + 18 * j))
    for i, g in enumerate((cell(UMB, 0), cell(UMB, -2), cell(EMPTY, 0), AISLE, ROOF, ROOF_LAMP, FASCIA, over(FASCIA, BANNER))):
        im.paste(img(g, pal('moon', i % 2, 1, False)), (2 + 18 * i, 2 + 18 * 3))
    for j, md in enumerate(MODES[:3]):
        for i in range(8):
            im.paste(img(far_grid('moon', md, 6 + i, 0, i), pal('moon', 0, i % 3, True)), (2 + 18 * i, 2 + 18 * (4 + j)))
    big(im, 4).convert('RGB').save(out('sheet_cells_4x.png'))


def numbers():
    L = []
    w = L.append
    w('Stadium background draft 2026-11-18. All counts below come from the tile sets the script collected while it drew every')
    w('frame of every GIF (USED), mirrored twins merged (tile H flip is free on Neo Geo).')
    for wet in ('dry', 'storm'):
        w('')
        w('%s moods (%s):' % (wet, 'dusk, moon' if wet == 'dry' else 'storm, with umbrellas'))
        tot = set()
        for plane in ('struct', 'near', 'far'):
            allm = set()
            for (wk, pl, md), s in sorted(USED.items()):
                if wk == wet and pl == plane:
                    w('  %-6s %-5s %3d unique 16 x 16 tiles' % (plane, md, len(s)))
                    allm |= s
            w('  %-6s total %3d' % (plane, len(allm)))
            tot |= allm
        w('  stands total (structure + near crowd + far crowd, all animations): %d; plus towers 4 (two 32 x 16 pieces)' % len(tot))
    both = set().union(*USED.values())
    w('')
    w('all three moods in one ROM (storm set adds only the umbrella tiles): %d stand tiles + 4 tower + 1 rain + 4 confetti' % len(both))
    w('new tiles outside the stands: sky 0 (rows 0..63 of the stage sky sheets), turf 0 (fling field turf), cones 9 per mood (48 x 48 x 2, moon and storm)')
    # auto-animation: distinct 8-step idle sequences
    for wet, mood in (('dry', 'moon'), ('storm', 'storm')):
        ns = {tuple(near_grid(mood, 'idle', 2 * s, r, c) for s in range(8)) for r in range(3) for c in range(21)}
        fs = {tuple(far_grid(mood, 'idle', 2 * s, r, c) for s in range(8)) for r in range(2) for c in range(21)}
        ns = {s for s in ns if len(set(s)) > 1}
        fs = {s for s in fs if len(set(s)) > 1}
        w('idle as hardware auto-animation, %s: near %d distinct 8-frame sequences = %d ROM tile slots, far %d = %d slots'
          % (wet, len(ns), 8 * len(ns), len(fs), 8 * len(fs)))
    nb = sum(ch in 'abc' for r in NT for ch in r)
    fb = sum(ch != 'S' for r in FB for ch in r)
    w('animated cells on the 336 px planes: near %d bird cells of 63, far %d crowd tiles of 42 (%d far birds)'
      % (nb, fb, sum(t != 'e' for r in FB for ch in r if ch != 'S' for t, _, _ in BLOCKS[ch])))
    w('')
    w('palettes on screen per mood: near crowd 6 (3 plumage x 2 teams), far crowd 6 (same, hazed), structure near 2 + far 2, turf 1, cone 1, rain 1')
    w('luminance steps of the dither pairs (near / far plane), brief asks 28 or more:')
    for mood in MOODS:
        n, fa = pal(mood, 0, 0, False)[0], pal(mood, 0, 0, True)[0]
        w('  %-5s ' % mood + '  '.join('%s%s %.0f / %.0f' % (x, y, abs(lum(n[x]) - lum(n[y])), abs(lum(fa[x]) - lum(fa[y])))
                                      for x, y in ('Ka', 'ab', 'bc', 'cd', 'tT')))
    w('')
    w('sprites per scanline (limit 96), stadium planes only, before players, gum and event gear:')
    w('  lines   0..31   sky 20 + far 21 (4 if the towers are their own sprites) + cones 14 (moon, storm) + rain 11 (storm) = 41 / 55 / 66')
    w('  lines  32..95   sky 20 (to line 63) + far 21 + rain 11 + confetti up to 12 = 53 / 53 / 64')
    w('  lines  96..159  near 21 + rain 11 + confetti up to 12 = 33 / 33 / 44')
    w('  lines 160..223  turf 21 + rain 11 = 21 / 21 / 32')
    open(out('numbers.txt'), 'w').write('\n'.join(L) + '\n')
    print('\n'.join(L))


def html(sizes):
    h = ['<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Gumbirds stadium drafts</title><style>',
         'body{background:#14161c;color:#d8dce6;font:15px/1.5 system-ui,sans-serif;margin:24px}',
         'h1{font-size:22px}h2{font-size:18px;margin-top:36px;border-top:1px solid #333a48;padding-top:16px}',
         'img{image-rendering:pixelated;display:block;margin:8px 0 4px;max-width:100%;border:1px solid #333a48}',
         '.row{display:flex;flex-wrap:wrap;gap:16px}figure{margin:0}figcaption{color:#98a0b0;font-size:13px}',
         '.pl img{background:#f0f}</style></head><body>',
         '<h1>Gumbirds stadium background, drafts 2026-11-18</h1>',
         '<p>Ground party events only. Left half of the stands wears the Player 1 blue, right half the Player 2 yellow. '
         'Numbers and weak points: README.md and numbers.txt in this folder.</p>']
    cap = {'idle': 'Crowd idle: bob and chatter', 'cheer': 'Cheer burst: Player 1 side, then Player 2 side',
           'wave': 'Stadium wave, left to right', 'win': 'Win wave: Player 1 wins, Player 2 side slumps'}
    for mood in MOODS:
        h.append('<h2>%s</h2><figure><img src="scene_%s_2x.png"><figcaption>Composed scene, idle frame 0, 2x</figcaption></figure>' % (mood.capitalize(), mood))
        for md in MODES:
            n = '%s_%s_3x.gif' % (md, mood)
            if n in sizes:
                h.append('<figure><img src="%s"><figcaption>%s, %d frames at %d ms, 3x</figcaption></figure>' % (n, cap[md], NFR[md], MS))
        h.append('<div class="row pl">')
        for pl in ('sky', 'far', 'near', 'grass') + (('cones',) if mood != 'dusk' else ()):
            h.append('<figure><img src="plane_%s_%s_1x.png"><figcaption>Plane: %s, 1x (magenta is transparent)</figcaption></figure>' % (mood, pl, pl))
        h.append('</div>')
    h.append('<h2>Hand cells</h2><figure><img src="sheet_cells_4x.png"><figcaption>Rows 1 to 3: near bird types a, b, c in poses '
             'sit, beak open, squash, wings mid, wings up, wings up narrow. Row 4: umbrella, umbrella raised, empty seat, stairs, roof, '
             'roof lamp, balcony front, banner. Rows 5 to 7: far crowd tiles in idle, cheer, wave. Moon palettes, 4x.</figcaption></figure>')
    h.append('</body></html>')
    open(out('index.html'), 'w').write('\n'.join(h) + '\n')


def main():
    gifs = '--nogif' not in sys.argv
    sizes = {}
    for mood in MOODS:
        back, front = static(mood)
        plane_png(back.crop((0, 0, 320, 64)) if mood == 'dusk' else keyed(os.path.join(BG, 'plane_%s_sky_1x.png' % mood)).crop((0, 0, 320, 64)),
                  'plane_%s_sky_1x.png' % mood)
        plane_png(far_plane(mood, 'idle', 0), 'plane_%s_far_1x.png' % mood)
        plane_png(near_plane(mood, 'idle', 0), 'plane_%s_near_1x.png' % mood)
        plane_png(FF.turf(mood), 'plane_%s_grass_1x.png' % mood)
        if mood != 'dusk':
            plane_png(cones(mood), 'plane_%s_cones_1x.png' % mood)
        big(frame(mood, 'idle', 0), 2).save(out('scene_%s_2x.png' % mood))
        for md in MODES:
            frs = [frame(mood, md, f) for f in range(NFR[md])]
            if gifs:
                n = '%s_%s_3x.gif' % (md, mood)
                nc = save_gif(out(n), frs)
                sizes[n] = os.path.getsize(out(n))
                print('%-22s %2d frames %3d colours %7.1f kB' % (n, len(frs), nc, sizes[n] / 1024))
    plane_png(img(RAIN, ({'#': FF.snap(RAINC)}, 'rain')), 'plane_storm_rain_1x.png')
    cell_sheet()
    numbers()
    if gifs:
        html(sizes)
        print('GIF total %.1f MB' % (sum(sizes.values()) / 1048576))


if __name__ == '__main__':
    main()
