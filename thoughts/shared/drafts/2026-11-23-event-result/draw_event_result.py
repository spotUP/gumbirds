#!/usr/bin/env python3.14
"""Shared Gum Games event result screen, three layout drafts (A jumbotron, B podium, C pennants). DRAFT ONLY, not imported.

Run: python3.14 -I draw_event_result.py
Backdrop: the 2026-11-18 stadium draft (draw_stadium.py frame parts). Fix-layer text: the real fix font sheet
(assets/font/fix_font_sheet.png). New art below is typed pixel grids (16 x 16 tiles, typed rows, typed palettes).
Honest notes: chunky digit fill uses one typed 22-row shade band table for all ten digits (fix font house style),
the digit outline is a 1 px ring added by code, digit 9 is digit 6 turned 180 degrees.
"""
import json
import math
import os
import sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
DRAFTS = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(DRAFTS, '2026-11-18-stadium'))
import draw_stadium as DS  # noqa: E402

snap = DS.FF.snap
DS.FF.BIRD = os.path.join(ROOT, 'assets/flier/sootling_sheet.png')   # the fling draft points at a removed worktree
K = (4, 4, 18)

# ---------------------------------------------------------------- fix layer (real font sheet, 8 x 8 cells, 40 x 28 grid)
FJ = json.load(open(os.path.join(ROOT, 'assets/font/fix_font.json')))
FSHEET = Image.open(os.path.join(ROOT, 'assets/font/fix_font_sheet.png'))
_FT = {}


def ftile(name, pal):
    if (name, pal) not in _FT:
        n = FJ['tiles'][name]
        src = FSHEET.crop((n % 16 * 8, n // 16 * 8, n % 16 * 8 + 8, n // 16 * 8 + 8))
        t = Image.new('RGBA', (8, 8), (0, 0, 0, 0))
        for y in range(8):
            for x in range(8):
                i = src.getpixel((x, y))
                if i:
                    t.putpixel((x, y), tuple(FJ['palettes'][pal][i - 1]) + (255,))
        _FT[(name, pal)] = t
    return _FT[(name, pal)]


def text(im, col, row, s, pal='white', plate=False):
    """Fix-layer line. plate: navy plate tiles with end caps one cell outside the text."""
    if plate:
        im.alpha_composite(ftile('s:capL', pal), (col * 8 - 8, row * 8))
        im.alpha_composite(ftile('s:capR', pal), (col * 8 + len(s) * 8, row * 8))
    for i, ch in enumerate(s):
        if ch == ' ':
            if plate:
                im.alpha_composite(ftile('s:fill', pal), ((col + i) * 8, row * 8))
            continue
        im.alpha_composite(ftile(('b:' if plate else 'p:') + ch, pal), ((col + i) * 8, row * 8))


def ctext(im, row, s, pal='white', plate=False):
    text(im, (40 - len(s)) // 2, row, s, pal, plate)


def bigdigits(im, col, row, s, pal='white', plate=False):
    for i, ch in enumerate(s):
        for h in (0, 1):
            im.alpha_composite(ftile('%s:%s:%d' % ('bt' if plate else 'pt', ch, h), pal), ((col + i) * 8, (row + h) * 8))


# ---------------------------------------------------------------- sprite helpers
SPR = []        # (x, y, w, h) of every sprite object this draft adds, for the per-line estimate


def tile(rows_, pal, w=16):
    assert all(len(r) == w for r in rows_), [r for r in rows_ if len(r) != w]
    t = Image.new('RGBA', (w, len(rows_)), (0, 0, 0, 0))
    for y, r in enumerate(rows_):
        for x, ch in enumerate(r):
            if ch != '.':
                t.putpixel((x, y), snap(pal[ch]) + (255,))
    return t


def put(im, t, x, y):
    im.alpha_composite(t, (x, y))
    SPR.append((x, y, t.width, t.height))


def flip(t):
    return t.transpose(Image.FLIP_LEFT_RIGHT)


def per_line():
    worst = (0, 0)
    for y in range(224):
        n = sum(math.ceil(w / 16) for (x, sy, w, h) in SPR if sy <= y < sy + h)
        worst = max(worst, (n, y))
    return worst


# ---------------------------------------------------------------- crown (winner mark, one 16 x 16 sprite)
GOLD = dict(K=(49, 16, 16), W=(255, 255, 214), y=(255, 222, 99), o=(222, 123, 24), r=(231, 49, 66))
CROWN = [
    '................', '................', '.K.....KK.....K.', 'KyK...KWyK...KyK',
    'KyyK.KWyyoK.KyoK', 'KWyyKWyyyyoKyyoK', 'KWyyyyyyyyyyyyoK', 'KWyyyyryyryyyyoK',
    'KWyyyyyyyyyyyyoK', 'KKKKKKKKKKKKKKKK', 'KWWyyyyyyyyyyooK', 'KyyoyoyoyoyoyooK',
    'KKKKKKKKKKKKKKKK', '................', '................', '................']

# ---------------------------------------------------------------- A: hanging jumbotron, lamp digits
BOARDP = {'K': K, '1': (16, 18, 50), '2': (34, 40, 92), '3': (58, 72, 140), '4': (104, 132, 196), '5': (196, 222, 248),
          'r': (150, 64, 104)}
A_TL = ['....KKKKKKKKKKKK', '..KK555555555555', '.K54444444444444', '.K54333333333333', 'K543333333333333',
        'K5433r3222222222', 'K5433K3222222222', 'K543322KKKKKKKKK', 'K543322K11111111', 'K543322K11111111',
        'K543322K11121111', 'K543322K11111111', 'K543322K11111111', 'K543322K11111211', 'K543322K11111111',
        'K543322K11111111']
A_T = ['KKKKKKKKKKKKKKKK', '5555555555555555', '4444444444444444', '3333333333333333', '3333433333333343',
       '2222222r22222222', '2222222K22222222', 'KKKKKKKKKKKKKKKK', '1111111111111111', '1111111111111111',
       '1111211111111111', '1111111111111111', '1111111111111111', '1111111111211111', '1111111111111111',
       '1111111111111111']
A_L = ['K543322K11111111', 'K543322K11111111', 'K543322K11111111', 'K543322K11211111', 'K543322K11111111',
       'K543322K11111111', 'K543322K11111111', 'K5433r2K11111111', 'K5433K2K11111111', 'K543322K11111111',
       'K543322K11111111', 'K543322K11111111', 'K543322K11111121', 'K543322K11111111', 'K543322K11111111',
       'K543322K11111111']
A_F = ['1111111111111111', '1111111111111111', '1111111211111111', '1111111111111111', '1111111111111111',
       '1111111111111111', '1211111111111111', '1111111111111111', '1111111111111111', '1111111111112111',
       '1111111111111111', '1111111111111111', '1111111111111111', '1111121111111111', '1111111111111111',
       '1111111111111111']
A_BL = A_L[:8] + ['K543322KKKKKKKKK', 'K5433r3333333333', 'K5433K3333333333', 'K543322222222222', '.K32222222222222',
                  '.K21212121212121', '..KK111111111111', '....KKKKKKKKKKKK']
A_B = A_F[:8] + ['KKKKKKKKKKKKKKKK', '3333333333333333', '3333333r33333333', '2222222K22222222', '2222222222222222',
                 '1212121212121212', '1111111111111111', 'KKKKKKKKKKKKKKKK']
A_CABLE = ['......K43K......', '......K32K......'] * 8
LAMP_OFF = {'f': (8, 8, 26), 'u': (24, 22, 58)}
LAMPS = [dict(W=(236, 250, 255), c=(110, 214, 255), b=(50, 120, 230)), dict(W=(255, 255, 214), c=(255, 214, 90), b=(240, 140, 40))]
LCELL = ('Wc.', 'cb.', '...')       # one lit lamp on a 3 px pitch
UCELL = ('uu.', 'uu.', '...')
G57 = {
    '0': ('.###.', '#...#', '#...#', '#...#', '#...#', '#...#', '.###.'), '1': ('..#..', '.##..', '..#..', '..#..', '..#..', '..#..', '.###.'),
    '2': ('.###.', '#...#', '....#', '...#.', '..#..', '.#...', '#####'), '3': ('.###.', '#...#', '....#', '..##.', '....#', '#...#', '.###.'),
    '4': ('...#.', '..##.', '.#.#.', '#..#.', '#####', '...#.', '...#.'), '5': ('#####', '#....', '####.', '....#', '....#', '#...#', '.###.'),
    '6': ('.###.', '#....', '#....', '####.', '#...#', '#...#', '.###.'), '7': ('#####', '....#', '...#.', '..#..', '..#..', '..#..', '..#..'),
    '8': ('.###.', '#...#', '#...#', '.###.', '#...#', '#...#', '.###.'), '9': ('.###.', '#...#', '#...#', '.####', '....#', '....#', '.###.'),
    ' ': ('.....',) * 7}


def lamp_field(im, x, y, s, team):
    """29 x 7 lamps (five digits, one lamp column between), 2 px dark margin. Digits right-aligned."""
    s = s.rjust(5)
    cols = ['.'.join(G57[ch][r] for ch in s) for r in range(7)]
    p = {**LAMP_OFF, **LAMPS[team]}
    f = Image.new('RGBA', (29 * 3 + 3, 7 * 3 + 3), snap(p['f']) + (255,))
    for r in range(7):
        for c in range(29):
            cell = LCELL if cols[r][c] == '#' else UCELL
            for dy in range(2):
                for dx in range(2):
                    f.putpixel((2 + c * 3 + dx, 2 + r * 3 + dy), snap(p[cell[dy][dx]]) + (255,))
    im.alpha_composite(f, (x, y))
    for i in range(5):                      # real build: one 16 px sprite per digit over the unlit field
        SPR.append((x + i * 18, y, 16, 24))


def layout_a(im, v):
    bx, by = 64, 16
    for c in (2, 9):
        put(im, tile(A_CABLE, BOARDP), bx + c * 16, 0)
    for r in range(6):
        for c in range(12):
            g = (A_TL if c in (0, 11) else A_T) if r == 0 else (A_BL if c in (0, 11) else A_B) if r == 5 else (A_L if c in (0, 11) else A_F)
            t = tile(g, BOARDP)
            im.alpha_composite(flip(t) if c == 11 else t, (bx + c * 16, by + r * 16))
    SPR.append((bx, by, 192, 96))
    ctext(im, 3, v['event'], 'gold')
    for i in (0, 1):
        row = 5 + i * 4
        win = v['winner'] == i
        text(im, 10, row, v['names'][i], 'gold' if win else 'dim')
        if win:
            text(im, 9, row, '>', 'gold')
        lamp_field(im, 152, 34 + i * 32, str(v['scores'][i]), i)
    if v['record']:
        ctext(im, 12, v['record'], 'lime' if v['record'].startswith('NEW') else 'white')
    birds(im, v, 112, 161, 208, 161)
    ctext(im, 23, v['banner'], 'gold', plate=True)


# ---------------------------------------------------------------- B: podium on the turf, chunky sprite digits
_T1, _T2, _T3, _C4 = '...########...', '..##########..', '.############.', '.####....####.'
_S, _L, _R, _F = '####......####', '####..........', '..........####', '##############'
_SIX = [_T1, _T2, _T3, _C4, _S] + [_L] * 3 + ['###########...', '############..', '#############.'] + [_S] * 7 + [_C4, _T3, _T2, _T1]
CHUNK = {
    '0': [_T1, _T2, _T3, _C4] + [_S] * 14 + [_C4, _T3, _T2, _T1],
    '1': ['.....####.....', '....#####.....', '...######.....', '..#######.....', '..#######.....'] + ['.....####.....'] * 14 + ['..##########..'] * 3,
    '2': [_T1, _T2, _T3, _C4, _S, _S, _R, _R, '.........####.', '........####..', '.......####...', '......####....', '.....####.....',
          '....####......', '...####.......', '..####........', '.####.........', _L, _L, _F, _F, _F],
    '3': [_T1, _T2, _T3, _C4, _S, _R, _R, _R, '.........####.', '....#########.', '....########..', '....#########.', '.........####.',
          _R, _R, _R, _R, _S, _C4, _T3, _T2, _T1],
    '4': ['.........####.', '........#####.', '.......######.', '......#######.', '.....###.####.', '....###..####.', '...###...####.',
          '..###....####.', '.###.....####.', '###......####.', '###......####.', _F, _F, _F] + ['.........####.'] * 8,
    '5': [_F, _F, _F, _L, _L, _L, _L, '##########....', '############..', '#############.'] + [_R] * 7 + [_S, _C4, _T3, _T2, _T1],
    '6': _SIX,
    '7': [_F, _F, _F, _R, _R, '.........####.', '.........####.', '........####..', '........####..', '.......####...', '.......####...',
          '......####....', '......####....'] + ['.....####.....'] * 9,
    '8': [_T1, _T2, _T3, _C4] + [_S] * 5 + [_C4, _T2, _C4] + [_S] * 6 + [_C4, _T3, _T2, _T1],
    '9': [r[::-1] for r in _SIX[::-1]],
}
# typed shade band per fill row: one role, or two roles for a checker dither row
BANDS = ['W', 'W', '1', '1', '1', '1', '12', '2', '2', '2', '3', 'W', '1', '1', '12', '2', '2', '23', '3', '3', '34', '4']
CHP = [{'K': (16, 8, 41), 'W': (255, 255, 214), '1': (255, 231, 115), '2': (255, 181, 49), '3': (214, 107, 24), '4': (132, 40, 60)},
       {'K': (16, 8, 41), 'W': (236, 244, 255), '1': (165, 181, 239), '2': (107, 115, 198), '3': (70, 66, 130), '4': (48, 30, 84)}]


def chunk(ch, p):
    g = CHUNK[ch]
    assert len(g) == 22 and all(len(r) == 14 for r in g), ch
    t = Image.new('RGBA', (16, 24), (0, 0, 0, 0))
    on = {(x + 1, y + 1) for y in range(22) for x in range(14) if g[y][x] == '#'}
    for (x, y) in on:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                t.putpixel((x + dx, y + dy), snap(p['K']) + (255,))
    for (x, y) in on:
        b = BANDS[y - 1]
        t.putpixel((x, y), snap(p[b[(x + y) % len(b)]]) + (255,))
    return t


def chunky(im, cx, y, s, p):
    for i, ch in enumerate(s):
        put(im, chunk(ch, p), cx - len(s) * 8 + i * 16, y)


STONE = {'K': K, 'r': (40, 24, 70), '1': (58, 52, 110), '2': (92, 88, 150), '3': (136, 140, 190), '4': (190, 200, 230), '5': (244, 248, 255)}
P_TL = ['.KKKKKKKKKKKKKKK', 'K555555555555555', 'K544444444444444', 'K444434444444344', 'KKKKKKKKKKKKKKKK', 'K4TTTTTTTTTTTTTT',
        'K4TtTTTTTTTTtTTT', 'K3tttttttttttttt', 'K3KKKKKKKKKKKKKK', 'K433333333333333', 'K433333333333333', 'K432323333333333',
        'K332222222222222', 'K322222222222222', 'K322212222222122', 'K221212121212121']
P_TM = ['KKKKKKKKKKKKKKKK', '5555555555555555', '4444444444444444', '4443444444434444', 'KKKKKKKKKKKKKKKK', 'TTTTTTTTTTTTTTTT',
        'TTTtTTTTTTTTtTTT', 'tttttttttttttttt', 'KKKKKKKKKKKKKKKK', '3333333333333333', '3333333333333333', '3333333323333333',
        '2222222222222222', '2222222222222222', '2221222222212222', '2121212121212121']
P_BL = ['K211111111111111', 'K212111111111111', 'K211111111111111', 'K211111111111111', 'K211111111111111', 'K211111111111111',
        'K211111111r11111', 'K211111111111111', 'K211111111111111', 'K211111111111111', 'K211111111111111', 'K21r1r1r1r1r1r1r',
        'K2rrrrrrrrrrrrrr', 'K1rrrrrrrrrrrrrr', 'K1rrrKrrrrrrKrrr', 'KKKKKKKKKKKKKKKK']
P_BM = [r[2:] + r[2:4] for r in P_BL]


def block(im, x, top, tall, team, mood):
    p = dict(STONE, t=DS.TEAM[mood][team][0], T=DS.TEAM[mood][team][1])
    for r, (le, mid) in enumerate(((P_TL, P_TM), (P_BL, P_BM))[:2 if tall else 1]):
        for c in range(3):
            t = tile(mid if c == 1 else le, p)
            im.alpha_composite(flip(t) if c == 2 else t, (x + c * 16, top + r * 16))
    SPR.append((x, top, 48, 32 if tall else 16))


def layout_b(im, v):
    w = v['winner']
    tops = [168 if w == i else 184 for i in (0, 1)]
    for i in (0, 1):
        block(im, 112 + i * 48, tops[i], w == i, i, v['mood'])
    birds(im, v, 136, tops[0] + 1, 184, tops[1] + 1)
    ctext(im, 1, v['event'], 'white', plate=True)
    ctext(im, 3, v['banner'], 'gold', plate=True)
    for i in (0, 1):
        cx = 56 + i * 208
        text(im, 3 + i * 26, 21, v['names'][i], 'gold' if w == i else 'dim', plate=True)
        chunky(im, cx, 180, str(v['scores'][i]), CHP[0 if w == i else 1])
    if v['record']:
        ctext(im, 26, v['record'], 'lime' if v['record'].startswith('NEW') else 'white', plate=True)


# ---------------------------------------------------------------- C: two team pennants, fix-layer scores
ROD = {'K': K, '5': (236, 244, 255), '4': (164, 192, 234), '3': (92, 116, 180), 'y': (255, 222, 99), 'o': (222, 123, 24)}
CLOTH = [dict(h=(170, 214, 250), s=(22, 30, 96)), dict(h=(255, 246, 190), s=(140, 70, 44))]      # + team T t from the stadium
_c0, _c1, _c2, _c3 = 'hTTTTTTtTTTTttst', 'hTTTTTtTTTTTtsst', 'TTTTTTTtTTTTttst', 'hTTTTTTTtTTTtsts'
C_CLOTH = [_c0, _c0, _c1, _c0, _c2, _c0, _c0, _c3, _c0, _c1, _c0, _c0, _c2, _c0, _c3, _c0]
C_ROD = ['................', 'KKKKKKKKKKKKKKKK', '5555555555555555', '4444454444444544', '3333333333333333', 'KKKKKKKKKKKKKKKK',
         'ssssssssssssssss', 'tststttttststttt'] + C_CLOTH[:8]
C_END = C_CLOTH[:10] + ['ssssssssssssssss', 'KKKKKKKKKKKKKKKK', 'yoyoyoyoyoyoyoyo', 'yoyoyoyoyoyoyoyo', 'o.o.o.o.o.o.o.o.', '................']


def pennant(im, x, y, mid_rows, team, mood):
    p = dict(ROD, **CLOTH[team], t=DS.TEAM[mood][team][0], T=DS.TEAM[mood][team][1])
    grids = [C_ROD] + [C_CLOTH] * mid_rows + [C_END]
    for r, g in enumerate(grids):
        for c in range(6):
            rows_ = [('K' + q[1:] if c == 0 and q[0] not in '.o' else q[:-1] + 'K' if c == 5 and q[-1] != '.' else q) for q in g]
            im.alpha_composite(tile(rows_, p), (x + c * 16, y + r * 16))
    SPR.append((x, y, 96, len(grids) * 16))


def layout_c(im, v):
    w = v['winner']
    ctext(im, 1, v['event'], 'white', plate=True)
    for i in (0, 1):
        pennant(im, 22 + i * 180, 24, 4 if w == i else 2, i, v['mood'])
        text(im, 5 + i * 22, 5, v['names'][i], 'gold' if w == i else 'white', plate=True)
        s = str(v['scores'][i]).rjust(5)
        bigdigits(im, 6 + i * 23, 7, s.replace(' ', ''), 'gold' if w == i else 'white', plate=True) if ' ' not in s else \
            bigdigits(im, 6 + i * 23 + s.count(' '), 7, s.strip(), 'gold' if w == i else 'white', plate=True)
        if w == i:
            text(im, 6 + i * 22, 10, 'WINNER', 'gold', plate=True)
    birds(im, v, 112, 161, 208, 161)
    ctext(im, 23, v['banner'], 'gold', plate=True)
    if v['record']:
        ctext(im, 25, v['record'], 'lime' if v['record'].startswith('NEW') else 'white', plate=True)


# ---------------------------------------------------------------- shared scene
def backdrop(mood, mode, f):
    back, _ = DS.static(mood)
    im = back.copy()
    im.alpha_composite(DS.far_plane(mood, mode, f).crop((8, 0, 328, 96)))
    im.alpha_composite(DS.near_plane(mood, mode, f).crop((8, 0, 328, 64)), (0, 96))
    im.alpha_composite(DS.FF.turf(mood), (0, 160))
    DS.confetti(im, mood, mode, f, DS.NFR[mode])
    if mood == 'storm':
        DS.rain(im, f)
    return im


def birds(im, v, x1, y1, x2, y2):
    a, b = DS.pair()
    put(im, a, x1 - a.width // 2, y1 - a.height)
    put(im, b, x2 - b.width // 2, y2 - b.height)
    wx, wy, wb = (x1, y1, a) if v['winner'] == 0 else (x2, y2, b)
    put(im, tile(CROWN, GOLD), wx - 8, wy - wb.height - 15)


VARIANTS = {
    '1p_win': dict(event='GUM FLING', names=('PLAYER 1', 'COMPUTER'), scores=(12500, 8300), winner=0, banner='PLAYER 1 WINS',
                   record='NEW RECORD', crowd=('win', 20)),
    '1p_computer': dict(event='POOP THE MAN', names=('PLAYER 1', 'COMPUTER'), scores=(6200, 9100), winner=1, banner='THE COMPUTER WINS',
                        record='', crowd=('cheer', 44)),
    '2p': dict(event='POP DROP', names=('PLAYER 1', 'PLAYER 2'), scores=(7400, 10250), winner=1, banner='PLAYER 2 WINS',
               record='RECORD 12500', crowd=('cheer', 44)),
}
LAYOUTS = {'A': layout_a, 'B': layout_b, 'C': layout_c}


def main():
    for mood in DS.MOODS:
        for ln, fn in LAYOUTS.items():
            for vn, v in VARIANTS.items():
                SPR.clear()
                im = backdrop(mood, *v['crowd'])
                fn(im, dict(v, mood=mood))
                im = im.convert('RGB')
                assert im.size == (320, 224)
                im.save(os.path.join(HERE, '%s_%s_%s_1x.png' % (ln, vn, mood)))
                DS.big(im, 3).save(os.path.join(HERE, '%s_%s_%s_3x.png' % (ln, vn, mood)))
                if mood == 'moon':
                    n, y = per_line()
                    print('%s %-12s added sprites per line: worst %2d at y=%d, colours %d' % (ln, vn, n, y, len(im.getcolors(99999))))


if __name__ == '__main__':
    main()
