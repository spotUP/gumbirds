#!/usr/bin/env python3
"""Draft round: title logo, fix font and HUD for Gumbirds (Neo Geo MVS, 320x224).

Run: /opt/homebrew/bin/python3.14 -I draw_hud_title.py
Writes PNG sheets (1x, transparent colour 255,0,255), 3x mock-ups, GIFs, numbers.txt and index.html next to itself.
Draft art only: nothing here is read by the build.

Conventions copied from the other draft scripts (draw_islands.py): q5 colour grid, up(), colour-keyed blits,
palettes of at most 15 colours plus transparent, tile counting with flips for sprites.
Backdrops are mock-ups taken from earlier draft renders (islands scene for the match, camera sheet for the title).
"""
import os
from math import sin, cos, pi, radians
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
DR = os.path.join(HERE, '..')
W, H = 320, 224
TR = (255, 0, 255)
MOODS = ('moon', 'dusk', 'storm')
MOODNAME = {'moon': 'CLEAR NIGHT', 'dusk': 'EMBER DUSK', 'storm': 'STORM'}
TAU = 2 * pi


def lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def q5(c):
    """Neo Geo colour grid: 5 bits per channel."""
    return tuple(((v >> 3) << 3) | (v >> 5) for v in c)


def P(*cols):
    """Palette: index 0 is transparent."""
    return [TR] + [q5(c) for c in cols]


def up(a, k):
    return np.repeat(np.repeat(a, k, 0), k, 1)


def new(h, w):
    a = np.empty((h, w, 3), np.uint8)
    a[:] = TR
    return a


def opaque(a):
    return ~((a[..., 0] == 255) & (a[..., 1] == 0) & (a[..., 2] == 255))


def over(dst, src, x=0, y=0):
    h, w = src.shape[:2]
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, dst.shape[1]), min(y + h, dst.shape[0])
    if x1 <= x0 or y1 <= y0:
        return
    s = src[y0 - y:y1 - y, x0 - x:x1 - x]
    m = opaque(s)
    dst[y0:y1, x0:x1][m] = s[m]


def rgb_of(idx, pal):
    return np.array(pal, np.uint8)[idx]


def blit(dst, idx, pal, x, y):
    over(dst, rgb_of(idx, pal), x, y)


def rect(c, x0, y0, x1, y1, col):
    c[max(y0, 0):y1, max(x0, 0):x1] = col


def save(path, a, k=1):
    Image.fromarray(up(a, k) if k > 1 else a).save(os.path.join(HERE, path), optimize=True)


def save_gif(path, frs, ms, scale=3):
    packed = [(fr[..., 0].astype(np.uint32) << 16) | (fr[..., 1].astype(np.uint32) << 8) | fr[..., 2] for fr in frs]
    cols = np.unique(np.concatenate([np.unique(p) for p in packed]))
    if len(cols) > 255:      # backdrop too rich: one shared adaptive palette, no dither
        strip = Image.fromarray(np.concatenate(frs, 1)).quantize(255, dither=Image.Dither.NONE)
        frs = [np.asarray(Image.fromarray(fr).quantize(palette=strip, dither=Image.Dither.NONE).convert('RGB')) for fr in frs]
        return save_gif(path, frs, ms, scale)
    pal = []
    for c in cols:
        pal += [int(c >> 16) & 255, int(c >> 8) & 255, int(c) & 255]
    pal += [0] * (768 - len(pal))
    ims, prev = [], None
    for p in packed:
        qd = np.searchsorted(cols, p).astype(np.uint8)
        dlt = qd.copy()
        if prev is not None:
            dlt[qd == prev] = 255
        prev = qd
        im = Image.fromarray(up(dlt, scale), 'P')
        im.putpalette(pal)
        ims.append(im)
    ims[0].save(os.path.join(HERE, path), save_all=True, append_images=ims[1:], duration=ms, loop=0, disposal=1,
                transparency=255, optimize=False)


# ------------------------------------------------------------------ backdrops (mock, from earlier drafts)
def bg_match(mood):
    a = np.asarray(Image.open(os.path.join(DR, '2026-11-10-islands', 'scene_roof_%s_3x.png' % mood)).convert('RGB'))
    return a[::3, ::3].copy()


def bg_plain(mood):
    a = np.asarray(Image.open(os.path.join(DR, '2026-11-10-backgrounds-wide', 'cams_%s_2x.png' % mood)).convert('RGB'))
    return a[20:468:2, 8:648:2].copy()


def load_soot():
    out = {}
    for who, fn in (('player', 'sootling_final_sheet_1x.png'), ('cpu', 'sootling_final_sheet_cpu_1x.png')):
        a = np.array(Image.open(os.path.join(DR, '2026-11-10-sootling-final', fn)).convert('RGB'))
        out[who] = lambda n, a=a: a[(n // 8) * 48:(n // 8) * 48 + 48, (n % 8) * 32:(n % 8) * 32 + 32]
    return out


# ------------------------------------------------------------------ fix fonts
# Font palette layout (one fix palette per text colour; icons keep their slots in every palette):
# 1..4 face light to deep, 5 shadow, 6..8 heart, 9..11 gum, 12 white, 13 soot navy, 14 soot blue, 15 ember
ICON = [(132, 16, 49), (231, 49, 66), (255, 148, 148), (181, 41, 165), (255, 82, 181), (255, 165, 222), (255, 255, 255),
        (24, 24, 74), (82, 148, 181), (255, 198, 90)]
FPAL = {
    'white': P((255, 255, 255), (222, 231, 255), (165, 181, 239), (107, 115, 198), (16, 8, 41), *ICON),
    'pink': P((255, 239, 247), (255, 181, 222), (255, 115, 189), (214, 57, 148), (41, 8, 41), *ICON),
    'lime': P((247, 255, 222), (189, 247, 132), (107, 222, 82), (33, 156, 74), (8, 33, 33), *ICON),
    'gold': P((255, 255, 214), (255, 231, 115), (255, 181, 49), (214, 107, 24), (49, 16, 16), *ICON),
    'dim': P((156, 165, 206), (123, 132, 181), (90, 99, 148), (66, 66, 115), (16, 8, 41), *ICON),
}
FPAL['lime'][9:12] = [q5(c) for c in ((16, 140, 74), (82, 214, 74), (173, 247, 123))]   # player 2 gum icon is lime

GA = {  # font A "Gumdrop": 7x7, two pixel stems, rounded
    'A': '..###../.##.##./##...##/##...##/#######/##...##/##...##', 'B': '######./##...##/##...##/######./##...##/##...##/######.',
    'C': '.#####./##...##/##...../##...../##...../##...##/.#####.', 'D': '#####../##..##./##...##/##...##/##...##/##..##./#####..',
    'E': '#######/##...../##...../#####../##...../##...../#######', 'F': '#######/##...../##...../#####../##...../##...../##.....',
    'G': '.#####./##...##/##...../##.####/##...##/##...##/.#####.', 'H': '##...##/##...##/##...##/#######/##...##/##...##/##...##',
    'I': '.####../..##.../..##.../..##.../..##.../..##.../.####..', 'J': '...####/....##./....##./....##./##..##./##..##./.####..',
    'K': '##...##/##..##./##.##../####.../##.##../##..##./##...##', 'L': '##...../##...../##...../##...../##...../##...../#######',
    'M': '##...##/###.###/#######/##.#.##/##...##/##...##/##...##', 'N': '##...##/###..##/####.##/##.####/##..###/##...##/##...##',
    'O': '.#####./##...##/##...##/##...##/##...##/##...##/.#####.', 'P': '######./##...##/##...##/######./##...../##...../##.....',
    'Q': '.#####./##...##/##...##/##...##/##.#.##/##..##./.###.##', 'R': '######./##...##/##...##/######./##.##../##..##./##...##',
    'S': '.#####./##...##/##...../.#####./.....##/##...##/.#####.', 'T': '######./..##.../..##.../..##.../..##.../..##.../..##...',
    'U': '##...##/##...##/##...##/##...##/##...##/##...##/.#####.', 'V': '##...##/##...##/##...##/##...##/.##.##./..###../...#...',
    'W': '##...##/##...##/##...##/##.#.##/#######/###.###/##...##', 'X': '##...##/.##.##./..###../..###../..###../.##.##./##...##',
    'Y': '##..##./##..##./.####../..##.../..##.../..##.../..##...', 'Z': '#######/....##./...##../..##.../.##..../##...../#######',
    '0': '.#####./##...##/##..###/##.#.##/###..##/##...##/.#####.', '1': '..##.../.###.../..##.../..##.../..##.../..##.../######.',
    '2': '.#####./##...##/.....##/...###./.###.../##...../#######', '3': '.#####./##...##/.....##/..####./.....##/##...##/.#####.',
    '4': '...###./..####./.##.##./##..##./#######/....##./....##.', '5': '#######/##...../######./.....##/.....##/##...##/.#####.',
    '6': '.#####./##...../##...../######./##...##/##...##/.#####.', '7': '#######/.....##/....##./...##../..##.../..##.../..##...',
    '8': '.#####./##...##/##...##/.#####./##...##/##...##/.#####.', '9': '.#####./##...##/##...##/.######/.....##/.....##/.#####.',
    '.': '......./......./......./......./......./.##..../.##....', ',': '......./......./......./......./.##..../.##..../.#.....',
    ':': '......./.##..../.##..../......./.##..../.##..../.......', '!': '..##.../..##.../..##.../..##.../......./..##.../..##...',
    '?': '.#####./##...##/.....##/...###./...##../......./...##..', '-': '......./......./......./.#####./......./......./.......',
    "'": '..##.../..##.../.#...../......./......./......./.......', '/': '......#/.....##/....##./...##../..##.../.##..../##.....',
    '<': '....##./...##../..##.../.##..../..##.../...##../....##.', '>': '.##..../..##.../...##../....##./...##../..##.../.##....',
}
GB = {  # font B "Signwriter": 6x7, heavy left stem, thin right stem, side extrusion
    'A': '.####./##...#/##...#/##...#/######/##...#/##...#', 'B': '#####./##...#/##...#/#####./##...#/##...#/#####.',
    'C': '.#####/##..../##..../##..../##..../##..../.#####', 'D': '#####./##...#/##...#/##...#/##...#/##...#/#####.',
    'E': '######/##..../##..../####../##..../##..../######', 'F': '######/##..../##..../####../##..../##..../##....',
    'G': '.#####/##..../##..../##.###/##...#/##...#/.#####', 'H': '##...#/##...#/##...#/######/##...#/##...#/##...#',
    'I': '####../.##.../.##.../.##.../.##.../.##.../####..', 'J': '..####/....##/....##/....##/....##/#...##/.####.',
    'K': '##...#/##..#./##.#../###.../##.#../##..#./##...#', 'L': '##..../##..../##..../##..../##..../##..../######',
    'M': '##...#/###.##/##.#.#/##...#/##...#/##...#/##...#', 'N': '##...#/###..#/##.#.#/##.#.#/##..##/##...#/##...#',
    'O': '.####./##...#/##...#/##...#/##...#/##...#/.####.', 'P': '#####./##...#/##...#/#####./##..../##..../##....',
    'Q': '.####./##...#/##...#/##...#/##.#.#/##..#./.###.#', 'R': '#####./##...#/##...#/#####./##.#../##..#./##...#',
    'S': '.#####/##..../##..../.####./....##/....##/#####.', 'T': '######/..##../..##../..##../..##../..##../..##..',
    'U': '##...#/##...#/##...#/##...#/##...#/##...#/.####.', 'V': '##...#/##...#/##...#/##...#/.##.#./.###../..#...',
    'W': '##...#/##...#/##...#/##.#.#/##.#.#/###.##/##...#', 'X': '##...#/.##.#./..##../..##../.#.##./#...##/#...##',
    'Y': '##...#/##...#/.##.#./..##../..##../..##../..##..', 'Z': '######/....##/...##./..##../.##.../##..../######',
    '0': '.####./##...#/##..##/##.#.#/###..#/##...#/.####.', '1': '..##../.###../..##../..##../..##../..##../.####.',
    '2': '.####./#...##/....##/...##./.##.../##..../######', '3': '#####./....##/....##/.####./....##/....##/#####.',
    '4': '...##./..###./.#.##./#..##./######/...##./...##.', '5': '######/##..../#####./....##/....##/#...##/.####.',
    '6': '.####./##..../##..../#####./##...#/##...#/.####.', '7': '######/....##/...##./..##../..##../..##../..##..',
    '8': '.####./##...#/##...#/.####./##...#/##...#/.####.', '9': '.####./#...##/#...##/.#####/....##/....##/.####.',
    '.': '....../....../....../....../....../.##.../.##...', ',': '....../....../....../....../.##.../.##.../.#....',
    ':': '....../.##.../.##.../....../.##.../.##.../......', '!': '.##.../.##.../.##.../.##.../....../.##.../.##...',
    '?': '.####./#...##/....##/..###./..##../....../..##..', '-': '....../....../....../.####./....../....../......',
    "'": '.##.../.##.../.#..../....../....../....../......', '/': '.....#/....##/...##./..##../.##.../##..../#.....',
    '<': '...##./..##../.##.../##..../.##.../..##../...##.', '>': '##..../.##.../..##../...##./..##../.##.../##....',
}
ICONS = {  # '{' heart, '}' gum bubble with knot, '~' Sootling face (life icon)
    '{': '.78.77../7887777./7877777./7777776./.77766../..766.../...6..../........',
    '}': '..bbb.../.bccbb../bcbbbba./bbbbbba./.bbbaa../..aaa.../...9..../........',
    '~': '..d.d.../.ddddd../deeeeed./dcdecdd./deeffed./deeeeed./.ddddd../........',
}
TALLG = {  # 7x15 score digits for font A
    '0': '..###../.#####./##...##/##...##/##...##/##..###/##.#.##/###..##/##...##/##...##/##...##/##...##/##...##/.#####./..###..',
    '1': '...##../..###../.####../...##../...##../...##../...##../...##../...##../...##../...##../...##../...##../.######/.######',
    '2': '..###../.#####./##...##/##...##/.....##/.....##/....##./...##../..##.../.##..../##...../##...../##...../#######/#######',
    '3': '..###../.#####./##...##/.....##/.....##/.....##/..####./..####./.....##/.....##/.....##/.....##/##...##/.#####./..###..',
    '4': '....##./...###./...###./..####./..#.##./.##.##./.#..##./##..##./##..##./#######/#######/....##./....##./....##./....##.',
    '5': '#######/#######/##...../##...../##...../#####../######./.....##/.....##/.....##/.....##/.....##/##...##/.#####./..###..',
    '6': '..###../.#####./##...##/##...../##...../##...../#####../######./##...##/##...##/##...##/##...##/##...##/.#####./..###..',
    '7': '#######/#######/.....##/.....##/....##./....##./...##../...##../...##../..##.../..##.../..##.../..##.../..##.../..##...',
    '8': '..###../.#####./##...##/##...##/##...##/##...##/.#####./.#####./##...##/##...##/##...##/##...##/##...##/.#####./..###..',
    '9': '..###../.#####./##...##/##...##/##...##/##...##/##...##/.######/..#####/.....##/.....##/.....##/##...##/.#####./..###..',
}
TALLROWS = [1, 1, 1, 2, 2, 2, 2, 3, 4, 4, 3, 3, 2, 2, 3]


def parse(s, w, h=7):
    rows = s.split('/')
    assert len(rows) == h and all(len(r) == w for r in rows), s
    return np.array([[ch == '#' for ch in r] for r in rows])


def shade_rows(m, rows, th):
    hh, ww = m.shape
    t = np.zeros((th, 8), np.uint8)
    for y in range(hh):
        for x in range(ww):
            if m[y, x]:
                s = rows[y]
                if y > 0 and not m[y - 1, x] and s > 1:
                    s -= 1          # top edge of every stroke catches the light
                t[y, x] = s
    return t


def drop(t, m, offs, val):
    hh, ww = m.shape
    for y in range(hh):
        for x in range(ww):
            if m[y, x]:
                for dy, dx in offs:
                    if y + dy < t.shape[0] and x + dx < 8 and t[y + dy, x + dx] == 0:
                        t[y + dy, x + dx] = val


def tile_a(s):
    m = parse(s, 7)
    t = shade_rows(m, [1, 1, 2, 2, 3, 3, 4], 8)
    drop(t, m, [(1, 1)], 5)
    return t


def tile_b(s):
    m = parse(s, 6)
    t = shade_rows(m, [1, 1, 1, 1, 3, 3, 4], 8)     # hard two-tone split, like sign paint
    drop(t, m, [(0, 1)], 4)                 # side extrusion in the deep face colour
    drop(t, m, [(1, 1), (1, 0)], 5)
    return t


def tile_icon(s):
    rows = s.split('/')
    t = np.array([[0 if ch == '.' else int(ch, 16) for ch in r] for r in rows], np.uint8)
    m = t > 0
    drop(t, m, [(1, 1)], 5)
    return t


def tile_tall(s):
    m = parse(s, 7, 15)
    t = shade_rows(m, TALLROWS, 16)
    drop(t, m, [(1, 1)], 5)
    return t


FONT_A = {k: tile_a(v) for k, v in GA.items()}
FONT_B = {k: tile_b(v) for k, v in GB.items()}
for _k, _v in ICONS.items():
    FONT_A[_k] = FONT_B[_k] = tile_icon(_v)
TALL = {k: tile_tall(v) for k, v in TALLG.items()}
FONTS = {'a': FONT_A, 'b': FONT_B}
FONTNAME = {'a': 'Font A, Gumdrop', 'b': 'Font B, Signwriter'}


def text(c, col, row, s, font, pal='white'):
    for i, ch in enumerate(s):
        if ch != ' ':
            blit(c, font[ch], FPAL[pal], (col + i) * 8, row * 8)


def ctext(c, row, s, font, pal='white'):
    text(c, (40 - len(s)) // 2, row, s, font, pal)


def rtext(c, col_end, row, s, font, pal='white'):
    text(c, col_end - len(s) + 1, row, s, font, pal)


def tall(c, col, row, s, pal='white'):
    for i, ch in enumerate(s):
        blit(c, TALL[ch], FPAL[pal], (col + i) * 8, row * 8)


# ------------------------------------------------------------------ big letters (own skeletons, three brushes)
WF = {'G': .78, 'U': .72, 'M': .95, 'B': .68, 'I': 0.0, 'R': .72, 'D': .76, 'S': .68}


def arc(cx, cy, rx, ry, a0, a1, step):
    n = max(2, int(round(abs(a1 - a0) / step)) + 1)
    return [(cx + rx * cos(radians(a)), cy - ry * sin(radians(a))) for a in np.linspace(a0, a1, n)]


def skel(ch, st):
    A = lambda *a: arc(*a, st)
    if ch == 'G':
        return [A(.5, .5, .5, .5, 48, 360) + [(.52, .5)]]
    if ch == 'U':
        return [[(0, 0)] + A(.5, .6, .5, .4, 180, 360) + [(1, 0)]]
    if ch == 'M':
        return [[(0, 1), (0, 0), (.5, .62), (1, 0), (1, 1)]]
    if ch == 'B':
        return [[(0, 0), (0, 1)], [(0, 0), (.5, 0)] + A(.5, .25, .42, .25, 90, -90) + [(0, .5)],
                [(0, .5), (.55, .5)] + A(.55, .75, .45, .25, 90, -90) + [(0, 1)]]
    if ch == 'I':
        return [[(.5, 0), (.5, 1)]]
    if ch == 'R':
        return [[(0, 0), (0, 1)], [(0, 0), (.5, 0)] + A(.5, .27, .5, .27, 90, -90) + [(0, .54)], [(.4, .54), (1, 1)]]
    if ch == 'D':
        return [[(0, 0), (0, 1)], [(0, 0), (.35, 0)] + A(.35, .5, .65, .5, 90, -90) + [(0, 1)]]
    if ch == 'S':
        return [A(.5, .26, .5, .26, 25, 270) + A(.5, .76, .5, .24, 90, -155)]
    raise KeyError(ch)


def poly_pts(poly, step=.35):
    out = []
    for (x0, y0), (x1, y1) in zip(poly, poly[1:]):
        n = max(1, int(np.hypot(x1 - x0, y1 - y0) / step))
        for k in range(n + 1):
            t = k / n
            out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
    return np.array(out)


def raster(h, w, pts, brush):
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    m = np.zeros((h, w), bool)
    for i in range(0, len(pts), 64):
        p = pts[i:i + 64]
        dx = xx[..., None] - p[:, 0]
        dy = yy[..., None] - p[:, 1]
        if brush[0] == 'round':
            d = (dx * dx + dy * dy) <= brush[1] ** 2
        elif brush[0] == 'square':
            d = (np.abs(dx) <= brush[1]) & (np.abs(dy) <= brush[1])
        else:
            _, ra, rb, ang = brush
            ca, sa = cos(ang), sin(ang)
            d = ((dx * ca + dy * sa) / ra) ** 2 + ((-dx * sa + dy * ca) / rb) ** 2 <= 1
        m |= d.any(-1)
    return m


def crop(m):
    ys, xs = np.nonzero(m)
    return m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def letter(ch, hgt, brush, step, wf=1.0):
    pad = int(np.ceil(max(brush[1:3] if brush[0] == 'nib' else brush[1:2]))) + 2
    w = WF[ch] * hgt * wf
    pts = np.concatenate([poly_pts([(x * w + pad, y * hgt + pad) for x, y in p]) for p in skel(ch, step)])
    return crop(raster(int(hgt + 2 * pad + 1), int(w + 2 * pad + 1), pts, brush))


def blur(a, r):
    p = np.pad(a, r, mode='constant')
    out = np.zeros_like(a, float)
    for dy in range(2 * r + 1):
        for dx in range(2 * r + 1):
            out += p[dy:dy + a.shape[0], dx:dx + a.shape[1]]
    return out / ((2 * r + 1) ** 2)


def dil(m, eight=False):
    p = np.pad(m, 1)
    o = p[1:-1, 1:-1] | p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]
    if eight:
        o |= p[:-2, :-2] | p[:-2, 2:] | p[2:, :-2] | p[2:, 2:]
    return o


def ero(m):
    return ~dil(~m)


def shift(m, dx, dy):
    o = np.zeros_like(m)
    h, w = m.shape
    o[max(dy, 0):h + min(dy, 0), max(dx, 0):w + min(dx, 0)] = m[max(-dy, 0):h + min(-dy, 0), max(-dx, 0):w + min(-dx, 0)]
    return o


def light(mask, r=2, it=3, k=5.0, L=(-.50, -.68, .53)):
    """Pillow height from the mask, lit from the upper left. Returns intensity; hard thresholds make the clusters."""
    h = mask.astype(float)
    for _ in range(it):
        h = blur(h, r)
    gy, gx = np.gradient(h)
    nx, ny, nz = -gx * k, -gy * k, np.ones_like(h)
    n = np.sqrt(nx * nx + ny * ny + nz * nz)
    return (nx * L[0] + ny * L[1] + nz * L[2]) / n


def disc(m, cx, cy, r):
    yy, xx = np.mgrid[0:m.shape[0], 0:m.shape[1]]
    m |= (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r


# gum material: hard clusters only, no dither, no checker
GUMP = P((107, 16, 132), (181, 41, 165), (255, 82, 181), (255, 165, 222), (255, 222, 247), (255, 255, 255), (33, 8, 66), (8, 8, 24))
LIMEP = P((8, 82, 66), (16, 140, 74), (82, 214, 74), (173, 247, 123), (231, 255, 198), (255, 255, 255), (8, 33, 49), (8, 8, 24))


def gum(M, shadow=True, thr=(.36, .62, .80, .93)):
    """Mask -> indices: 1 keyline, 2..5 gum deep to pale, 6 specular, 7 drop shadow, 8 outer line."""
    I = light(M)
    idx = np.zeros(M.shape, np.uint8)
    idx[M] = (2 + np.digitize(I, thr))[M]
    idx[(idx == 6) & ~ero(M)] = 5                    # specular never sits on the outline
    idx[(idx == 2) & ~ero(M) & (I > .2)] = 3
    r1 = dil(M, True) & ~M
    idx[r1] = 1
    body = M | r1
    r2 = dil(body) & ~body
    idx[r2] = 8
    if shadow:
        sh = shift(body | r2, 2, 3) & (idx == 0)
        idx[sh] = 7
    return idx


def sprite_stats(frames, tw=16):
    """Unique 16x16 tiles (flips reused) over all frames, and the most strips on one scanline."""
    uniq, most = set(), 0
    for L in frames:
        hh, ww = L.shape[:2]
        for ty in range(0, hh, tw):
            n = 0
            for tx in range(0, ww, tw):
                t = L[ty:ty + tw, tx:tx + tw]
                if t.shape[:2] != (tw, tw):
                    q = new(tw, tw)
                    q[:t.shape[0], :t.shape[1]] = t
                    t = q
                if opaque(t).any():
                    n += 1
                    uniq.add(min(t.tobytes(), t[:, ::-1].tobytes(), t[::-1].tobytes(), t[::-1, ::-1].tobytes()))
            most = max(most, n)
    return len(uniq), most


def fix_stats(L):
    uniq, cells = set(), 0
    for ty in range(0, L.shape[0], 8):
        for tx in range(0, L.shape[1], 8):
            t = L[ty:ty + 8, tx:tx + 8]
            if opaque(t).any():
                cells += 1
                uniq.add(t.tobytes())
    return len(uniq), cells


def ncol(L):
    m = opaque(L)
    return len(np.unique(L[m].reshape(-1, 3), axis=0))


# ------------------------------------------------------------------ logo A: stretched bubble gum (sprites)
A_W, A_H, A_X, A_Y = 304, 128, 8, 10
A_OFF = [2, -2, 1, -3, 0, -2, 2, -1]
A_BUB = [3, 5, 7, 9, 10.5, 12, -1, -2, 0, 2]              # radius per frame; -1, -2 = pop shreds
A_DRIP = [3, 4, 6, 8, 11, 14, (5, 19), (3, 28), (2, 41), 2]    # strand length; (strand, drop offset) once the drop is free
A_STATIC = (8, 7)


def logo_a(f=None):
    rb, dr = A_STATIC if f is None else (A_BUB[f], A_DRIP[f])
    M = np.zeros((A_H, A_W), bool)
    x, top, hgt, r = 5, 44, 36, 5
    pos = {}
    for i, ch in enumerate('GUMBIRDS'):
        m = letter(ch, hgt, ('round', r), 12)
        y = top - r + A_OFF[i]
        M[y:y + m.shape[0], x:x + m.shape[1]] |= m
        pos[ch] = (x, y, m.shape[1], m.shape[0])
        x += m.shape[1] + 3
    # thin strands where two letters pull apart (hand placed)
    for a, b, ya, sag in (('G', 'U', 18, 3), ('D', 'S', 30, 2)):
        xa = pos[a][0] + pos[a][2] - 3
        xb = pos[b][0] + 3
        y0 = pos[a][1] + ya
        for xx in range(xa, xb + 1):
            t = (xx - xa) / max(1, xb - xa)
            disc(M, xx, y0 + sag * 4 * t * (1 - t), 1.1)
    # bubble blown from the top of the I
    ix, iy = pos['I'][0] + pos['I'][2] // 2, pos['I'][1]
    if rb > 0:
        cy = iy - rb * .8 + 2
        disc(M, ix - .35 * rb, cy, rb * .82)
        disc(M, ix + .40 * rb, cy - .12 * rb, rb * .78)
        disc(M, ix, iy + 1, 2.2)
    elif rb < 0:
        d = 15 if rb == -1 else 21
        for k in range(7):
            a = TAU * (k + .3) / 7
            disc(M, ix + d * cos(a), iy - 9 - d * .8 * sin(a) + (0 if rb == -1 else 3), 2.0 if rb == -1 else 1.3)
        disc(M, ix, iy - 1, 3.0 if rb == -1 else 2.4)        # the torn rim left on the letter
    # drip under the U
    ux, ub = pos['U'][0] + pos['U'][2] // 2 + 1, pos['U'][1] + pos['U'][3] - 2
    strand, drop_at = (dr, None) if not isinstance(dr, tuple) else dr
    for k in range(int(strand) + 1):
        disc(M, ux, ub + k, 2.4 - 1.2 * min(1, k / max(1, strand - 3)) if k < strand - 2 else 1.3)
    if drop_at is None:
        disc(M, ux, ub + strand + 1, 2.6)
    else:
        disc(M, ux, ub + drop_at, 2.6)
        disc(M, ux, ub + drop_at - 3, 1.4)
    return rgb_of(gum(M), GUMP)


# ------------------------------------------------------------------ logo B: enamel sign (fix tiles, palette-cycled bulbs)
SIGNP = P((8, 49, 66), (16, 90, 99), (49, 140, 132), (8, 33, 49), (255, 239, 198), (222, 181, 132), (255, 255, 255),
          (222, 57, 41), (132, 24, 41), (148, 82, 41), (82, 41, 33), (255, 239, 123), (231, 148, 49), (115, 57, 41), (8, 8, 24))
B_X0, B_Y0, B_X1, B_Y1 = 48, 32, 272, 88
B_CHIPS = [(B_X0 + 1, B_Y1 - 9, ['#..', '##.', '###', '###', '####', '#####', '######', '########']),
           (B_X1 - 6, B_Y0 + 1, ['#####', '.####', '..###', '...##', '....#']),
           (B_X0 + 118, B_Y1 - 4, ['.##..', '####.', '#####']), (B_X0 + 61, B_Y0 + 1, ['####', '.##.']),
           (B_X1 - 4, B_Y0 + 30, ['..#', '.##', '.##', '###', '.##', '..#'])]
B_CHAIN = ['..6665..', '.6....a.', '.6....a.', '.6....a.', '..6aaa..', '...6a...', '...6a...', '...6a...']


def logo_b(f=0):
    c = np.zeros((H, W), np.uint8)
    x0, y0, x1, y1 = B_X0, B_Y0, B_X1, B_Y1
    yy, xx = np.mgrid[0:H, 0:W]
    plate = (xx >= x0) & (xx < x1) & (yy >= y0) & (yy < y1)
    for cx, cy in ((x0, y0), (x1 - 1, y0), (x0, y1 - 1), (x1 - 1, y1 - 1)):
        plate &= (np.abs(xx - cx) + np.abs(yy - cy)) >= 3           # chamfered corners
    inner = ero(plate)
    c[plate] = 15
    c[inner] = 2
    u = (xx - x0) + (yy - y0) * .9
    c[inner & (u > 196)] = 1                                         # the lower right falls into shade
    c[inner & (((u >= 38) & (u < 58)) | ((u >= 64) & (u < 68)) | ((u >= 150) & (u < 155)))] = 3   # hard gloss bands
    edge = inner & ~ero(inner)
    c[edge & ((yy == y0 + 1) | (xx == x0 + 1))] = 3
    c[edge & ((yy == y1 - 2) | (xx == x1 - 2))] = 4
    # cream inset line carrying the bulbs
    line = (((yy == y0 + 5) | (yy == y1 - 6)) & (xx >= x0 + 6) & (xx < x1 - 6)) | (((xx == x0 + 5) | (xx == x1 - 6)) & (yy >= y0 + 6) & (yy < y1 - 6))
    c[line] = 6
    bulbs = [(x, y0 + 5) for x in range(x0 + 10, x1 - 8, 12)] + [(x1 - 6, y) for y in range(y0 + 16, y1 - 12, 12)]
    bulbs += [(x, y1 - 6) for x in range(x1 - 14, x0 + 8, -12)] + [(x0 + 5, y) for y in range(y1 - 20, y0 + 12, -12)]
    for k, (bx, by) in enumerate(bulbs):
        b = 12 + k % 3
        c[by - 1:by + 2, bx - 1:bx + 2] = b
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            c[by + dy, bx + dx] = 15 if c[by + dy, bx + dx] != 6 else 6
        c[by - 1, bx - 1] = 7
    # letters: octagonal block capitals with a red drop shade
    ms = [letter(ch, 26, ('square', 2), 45) for ch in 'GUMBIRDS']
    tot = sum(m.shape[1] for m in ms) + 4 * 7
    lx, ly = x0 + (x1 - x0 - tot) // 2, y0 + 13
    face = np.zeros((H, W), bool)
    for m in ms:
        face[ly:ly + m.shape[0], lx:lx + m.shape[1]] |= m
        lx += m.shape[1] + 4
    c[shift(face, 3, 3) & inner] = 9
    c[(shift(face, 1, 1) | shift(face, 2, 2)) & inner] = 8
    c[face] = 5
    c[face & ~shift(face, 0, 1)] = 7
    c[face & ~shift(face, 0, -1)] = 6
    # bolts, rust streaks, chips
    for bx, by in ((x0 + 2, y0 + 2), (x1 - 4, y0 + 2), (x0 + 2, y1 - 4), (x1 - 4, y1 - 4)):
        c[by:by + 2, bx:bx + 2] = 10
        c[by, bx] = 6
    for bx, by, ln in ((x0 + 3, y0 + 4, 7), (x1 - 3, y0 + 4, 11)):
        c[by:by + ln, bx] = 10
        c[by + ln:by + ln + 2, bx] = 11
    for cx, cy, rows in B_CHIPS:
        for j, row in enumerate(rows):
            for i, ch in enumerate(row):
                if ch == '#' and plate[cy + j, cx + i]:
                    c[cy + j, cx + i] = 11
    chip = c == 11
    c[dil(chip) & ~chip & inner & (c != 5) & (c != 7) & (c != 6)] = 10
    # chains up to the top of the screen
    link = np.array([[0 if ch == '.' else int(ch, 16) for ch in r] for r in B_CHAIN], np.uint8)
    for cx in (x0 + 24, x1 - 32):
        for cy in range(0, y0, 8):
            c[cy:cy + 8, cx:cx + 8] = link
    pal = list(SIGNP)
    rot = [SIGNP[12], SIGNP[13], SIGNP[14]]
    for k in range(3):
        pal[12 + k] = rot[(k - f) % 3]
    return rgb_of(c, pal)


# ------------------------------------------------------------------ logo C: soot letters under their own bubbles (sprites)
SOOTP = P((8, 8, 24), (24, 24, 74), (41, 66, 132), (82, 148, 181), (156, 222, 214), (231, 255, 239), (123, 24, 66),
          (231, 90, 41), (255, 198, 90))
C_X, C_Y, C_PITCH, C_NF = 24, 30, 34, 12
C_GUM = [GUMP, LIMEP, GUMP, GUMP, LIMEP, GUMP, LIMEP, GUMP]


def hsh(x, y):
    return (x * 73856093 ^ y * 19349663 ^ (x * y) * 83492791) & 0xffff


def soot_letter(ch):
    m0 = letter(ch, 23, ('nib', 3.6, 1.7, radians(-38)), 12, wf=.72 if ch == 'M' else .9)
    m = np.pad(m0, 3)
    # ragged soot edge: tufts pushed out and nicks cut in (fixed pattern, not noise per frame)
    edge_out = dil(m) & ~m
    edge_in = m & ~ero(m)
    ys, xs = np.nonzero(edge_out)
    for y, x in zip(ys, xs):
        if hsh(x + ord(ch), y) % 9 < 2:
            m[y, x] = True
    ys, xs = np.nonzero(edge_in)
    for y, x in zip(ys, xs):
        if hsh(x, y + ord(ch)) % 11 == 0:
            m[y, x] = False
    I = light(m, r=1, it=3, k=4.0)
    idx = np.zeros(m.shape, np.uint8)
    idx[m] = (2 + np.digitize(I, (.42, .74, .93)))[m]
    ring = dil(m, True) & ~m
    outside = np.zeros_like(m)
    outside[0, :] = outside[-1, :] = outside[:, 0] = outside[:, -1] = True
    for _ in range(80):
        outside = (dil(outside) | outside) & ~m
    ring &= dil(outside, True)                                    # closed counters stay open, no rim inside them
    warm = ring & (shift(m, 1, 0) | shift(m, 0, 1) | shift(m, 1, 1)) & ~shift(m, -1, 0) & ~shift(m, 0, -1)
    idx[ring] = 5
    idx[ring & (shift(m, 1, 0) | shift(m, 0, 1))] = 8             # ember light from below right
    idx[warm] = 9
    body = m | ring
    idx[dil(body) & ~body] = 1
    return idx


def bubble_c():
    M = np.zeros((20, 28), bool)
    disc(M, 9.5, 9.5, 7.2)
    disc(M, 17.5, 8.5, 6.8)
    return gum(M, shadow=False)


def logo_c_units(f=0):
    """Eight sprite units of 32x64: bubble, gum string, letter. Returns (units, dx, dy) per letter."""
    out = []
    bub = bubble_c()
    for i, ch in enumerate('GUMBIRDS'):
        u = new(64, 32)
        gp = C_GUM[i]
        L = soot_letter(ch)
        assert L.shape[1] <= 32, (ch, L.shape)
        lx = (32 - L.shape[1]) // 2
        sway = int(round(1.4 * sin(TAU * (f / C_NF + i * .23))))
        blit(u, bub, gp, 2 + sway, 0)
        # gum string from the knot to the letter
        kx = 15 + sway
        for k in range(8):
            xk = int(round(kx + (16 - kx) * k / 7))
            u[18 + k, xk] = gp[5]
            u[18 + k, xk - 1] = gp[1]
        u[17:19, kx - 1:kx + 2] = gp[2]
        blit(u, L, SOOTP, lx, 22)
        dy = int(round(3.2 * sin(TAU * (f / C_NF + i * .17))))
        out.append((u, C_X + i * C_PITCH, C_Y + dy))
    return out


def logo_c(f=0):
    c = new(H, W)
    for u, x, y in logo_c_units(f):
        over(c, u, x, y)
    return c


# ------------------------------------------------------------------ title screen
def title(mood, which, f, soot, font=FONT_A):
    c = bg_plain(mood)
    if which == 'a':
        over(c, logo_a(None if f is None else f % 10), A_X, A_Y)
    elif which == 'b':
        over(c, logo_b(0 if f is None else f))
    else:
        over(c, logo_c(0 if f is None else f))
    ff = 0 if f is None else f
    s = soot['player'](ff % 8)
    over(c, s, 44, 112 + int(round(2 * sin(TAU * ff / 8))))
    s = soot['cpu']((ff + 3) % 8)[:, ::-1]
    over(c, s, 244, 120 + int(round(2 * sin(TAU * (ff + 3) / 8))))
    o = new(H, W)
    text(o, 11, 1, 'HIGH SCORE', font, 'gold')
    text(o, 22, 1, '052300', font, 'white')
    if f is None or (f // 2) % 2 == 0:
        ctext(o, 20, 'PRESS START', font, 'gold')
    ctext(o, 23, '1 OR 2 PLAYERS', font, 'white')
    rtext(o, 37, 26, 'CREDITS 2', font, 'white')
    over(c, o)
    return c


# ------------------------------------------------------------------ HUD layouts
BAND = [q5(v) for v in ((8, 8, 24), (16, 16, 49), (24, 24, 74), (57, 57, 115), (115, 123, 198), (181, 41, 165))]
DATA = dict(p1='004200', p2='001500', hi='052300', rnd=3, cr=2, g1=3, g2=1)


def hud1(mood, font, p2=True):
    """Roof strip: opaque band over fix rows 0 and 1 (above the y = 16 ceiling), one text line at the bottom."""
    o = new(H, W)
    rect(o, 0, 0, W, 16, BAND[1])
    rect(o, 0, 0, W, 1, BAND[0])
    rect(o, 0, 1, W, 2, BAND[2])
    rect(o, 0, 13, W, 14, BAND[3])
    rect(o, 0, 14, W, 15, BAND[4])
    rect(o, 0, 15, W, 16, BAND[0])
    for x in (108, 210):
        rect(o, x, 2, x + 1, 13, BAND[0])
        rect(o, x + 1, 2, x + 2, 13, BAND[3])
    for x in range(4, W, 40):                      # rivets on the lower rail
        o[13, x] = BAND[4]
        o[14, x] = BAND[0]
    text(o, 2, 0, 'PLAYER 1', font, 'pink')
    text(o, 2, 1, DATA['p1'], font, 'white')
    text(o, 9, 1, '}', font, 'white')
    text(o, 10, 1, str(DATA['g1']), font, 'pink')
    text(o, 15, 0, 'HIGH SCORE', font, 'gold')
    text(o, 17, 1, DATA['hi'], font, 'white')
    if p2:
        text(o, 30, 0, 'PLAYER 2', font, 'lime')
        text(o, 32, 1, DATA['p2'], font, 'white')
        text(o, 28, 1, '}', font, 'lime')
        text(o, 29, 1, str(DATA['g2']), font, 'lime')
    else:
        text(o, 30, 0, 'PLAYER 2', font, 'dim')
        text(o, 27, 1, 'PRESS START', font, 'lime')
    text(o, 2, 27, 'ROUND %d - %s' % (DATA['rnd'], MOODNAME[mood]), font, 'white')
    rtext(o, 37, 27, 'CREDITS %d' % DATA['cr'], font, 'white')
    text(o, 0, 12, '<', font, 'pink')              # off screen marker the game already draws at the edge
    return o


def hud2(mood, font, p2=True):
    """Corner tags: no band, 8x16 score digits in the corners, everything else on the bottom line."""
    o = new(H, W)
    tall(o, 2, 0, DATA['p1'], 'white')
    text(o, 9, 0, 'PLAYER 1', font, 'pink')
    text(o, 9, 1, '}' * DATA['g1'], font, 'white')
    if p2:
        tall(o, 32, 0, DATA['p2'], 'white')
        text(o, 23, 0, 'PLAYER 2', font, 'lime')
        rtext(o, 30, 1, '}' * DATA['g2'], font, 'lime')
    else:
        text(o, 30, 0, 'PLAYER 2', font, 'dim')
        text(o, 27, 1, 'PRESS START', font, 'lime')
    text(o, 2, 27, 'HIGH SCORE', font, 'gold')
    text(o, 13, 27, DATA['hi'], font, 'white')
    text(o, 21, 27, 'ROUND %d' % DATA['rnd'], font, 'white')
    rtext(o, 37, 27, 'CREDITS %d' % DATA['cr'], font, 'white')
    text(o, 0, 12, '<', font, 'pink')
    return o


HUDS = {'1': hud1, '2': hud2}
HUDNAME = {'1': 'Layout 1, Roof strip', '2': 'Layout 2, Corner tags'}


def panel(o, col, row, cols, rows, head=3):
    x0, y0, x1, y1 = col * 8, row * 8, (col + cols) * 8, (row + rows) * 8
    rect(o, x0, y0, x1, y1, BAND[0])
    rect(o, x0 + 1, y0 + 1, x1 - 1, y1 - 1, BAND[3])
    rect(o, x0 + 1, y0 + 1, x1 - 2, y0 + 2, BAND[4])
    rect(o, x0 + 1, y0 + 1, x0 + 2, y1 - 2, BAND[4])
    rect(o, x0 + 2, y0 + 2, x1 - 2, y1 - 2, BAND[0])
    rect(o, x0 + 3, y0 + 3, x1 - 3, y1 - 3, BAND[1])
    if head:
        rect(o, x0 + 3, y0 + 3, x1 - 3, y0 + head * 8, BAND[2])
        rect(o, x0 + 3, y0 + head * 8, x1 - 3, y0 + head * 8 + 1, BAND[5])
        rect(o, x0 + 3, y0 + head * 8 + 1, x1 - 3, y0 + head * 8 + 2, BAND[0])
    for cx, cy in ((x0, y0), (x1 - 1, y0), (x0, y1 - 1), (x1 - 1, y1 - 1)):
        o[cy, cx] = TR


def results(mood, font):
    """Placeholder numbers: the design fixes 'points for stomps and wins' but no values yet."""
    o = hud2(mood, font)
    panel(o, 5, 4, 30, 20)
    ctext(o, 5, 'ROUND %d CLEAR' % DATA['rnd'], font, 'gold')
    text(o, 17, 8, 'PLAYER 1', font, 'pink')
    text(o, 26, 8, 'PLAYER 2', font, 'lime')
    rows = [(10, 'STOMPS', '3', '1', 'white'), (11, 'STOMP POINTS', '1500', '500', 'dim'), (13, 'ROUND WIN', '2000', '0', 'white'),
            (15, 'GUM LEFT', '}}', '-', 'white'), (16, 'GUM BONUS', '500', '0', 'dim')]
    for y, lab, a, b, pal in rows:
        text(o, 7, y, lab, font, pal)
        rtext(o, 24, y, a, font, 'white')
        rtext(o, 33, y, b, font, 'white')
    rect(o, 7 * 8, 17 * 8 + 3, 34 * 8 - 4, 17 * 8 + 4, BAND[3])
    text(o, 7, 19, 'TOTAL', font, 'gold')
    tall(o, 19, 18, '004000', 'pink')
    tall(o, 28, 18, '000500', 'lime')
    ctext(o, 21, 'PLAYER 1 WINS THE ROUND!', font, 'gold')
    ctext(o, 22, 'NEXT ROUND IN 5', font, 'dim')
    return o


TABLE = [('GUM', '052300'), ('SOT', '047750'), ('???', '004000'), ('PIP', '003900'), ('ASH', '002250')]


def entry(mood, font):
    o = new(H, W)
    panel(o, 4, 2, 32, 24)
    ctext(o, 3, 'NEW HIGH SCORE!', font, 'gold')
    text(o, 6, 6, 'PLAYER 1', font, 'pink')
    tall(o, 6, 7, '004000', 'white')
    text(o, 16, 8, 'RANK 3 OF 10', font, 'dim')
    text(o, 22, 6, 'TIME', font, 'white')
    tall(o, 27, 5, '17', 'gold')
    ctext(o, 10, 'ENTER YOUR NAME', font, 'white')
    # three letter wheels: neighbours dimmed above and below, the live slot framed
    name, cur = 'BI', 2
    for i in range(3):
        cx = 15 + i * 4
        x0, y0 = cx * 8 - 8, 14 * 8 - 4
        live = i == cur
        rect(o, x0, y0, x0 + 24, y0 + 16, BAND[4] if live else BAND[3])
        rect(o, x0 + 1, y0 + 1, x0 + 23, y0 + 15, BAND[0])
        rect(o, x0 + 2, y0 + 2, x0 + 22, y0 + 14, BAND[2] if live else BAND[1])
        ch = name[i] if i < len(name) else 'R'
        text(o, cx, 14, ch, font, 'pink' if live else 'white')
        if live:
            text(o, cx, 12, chr(ord(ch) - 1), font, 'dim')
            text(o, cx, 16, chr(ord(ch) + 1), font, 'dim')
            for k in range(3):                       # small gum arrows drawn from rects: up and down
                rect(o, x0 + 11 - k, y0 - 4 + k - 14, x0 + 13 + k, y0 - 3 + k - 14, FPAL['pink'][3])
                rect(o, x0 + 11 - k, y0 + 33 - k, x0 + 13 + k, y0 + 34 - k, FPAL['pink'][3])
    ctext(o, 18, 'STICK: LETTER   A: NEXT', font, 'dim')
    for j, (nm, sc) in enumerate(TABLE):
        pal = 'pink' if j == 2 else 'white'
        text(o, 10, 20 + j, '%d.' % (j + 1), font, pal)
        text(o, 14, 20 + j, 'BI ' if j == 2 else nm, font, pal)
        text(o, 20, 20 + j, sc, font, pal)
        if j == 2:
            text(o, 27, 20 + j, '<', font, 'gold')
    return o


def compose(bg, o):
    c = bg.copy()
    over(c, o)
    return c


def contrast(bg, o, rows):
    """Worst text cell: smallest gap between the light face colour and the mean backdrop under the cell."""
    worst, weak = 999, 0
    for row in rows:
        for col in range(40):
            cell = o[row * 8:row * 8 + 8, col * 8:col * 8 + 8]
            m = opaque(cell)
            if not m.any():
                continue
            face = max(lum(px) for px in cell[m])
            back = np.mean([lum(px) for px in bg[row * 8:row * 8 + 8, col * 8:col * 8 + 8].reshape(-1, 3)])
            g = face - back
            worst = min(worst, g)
            weak += g < 70
    return worst, weak


# ------------------------------------------------------------------ specimen
ORDER = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,:!?-\'/<>{}~'


def font_sheet(font):
    n = len(ORDER)
    c = new(8 * ((n + 15) // 16), 128)
    for i, ch in enumerate(ORDER):
        blit(c, font[ch], FPAL['white'], (i % 16) * 8, (i // 16) * 8)
    return c


def tall_sheet():
    c = new(16, 80)
    for i, ch in enumerate('0123456789'):
        blit(c, TALL[ch], FPAL['white'], i * 8, 0)
    return c


def specimen():
    rows = 44
    c = np.empty((rows * 8, W, 3), np.uint8)
    c[:] = q5((24, 24, 41))
    r = 1
    for key in ('a', 'b'):
        f = FONTS[key]
        text(c, 1, r, FONTNAME[key].upper().replace(',', ' -'), f, 'gold')
        text(c, 1, r + 2, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', f, 'white')
        text(c, 1, r + 4, "0123456789 . , : ! ? - ' / < > { } ~", f, 'white')
        text(c, 1, r + 6, 'PLAYER 1', f, 'pink')
        text(c, 11, r + 6, 'PLAYER 2', f, 'lime')
        text(c, 21, r + 6, 'HIGH SCORE', f, 'gold')
        text(c, 32, r + 6, 'CREDITS', f, 'dim')
        text(c, 1, r + 8, "DON'T POP! WHO'S NEXT? 12/34 <OK>", f, 'white')
        r += 11
    text(c, 1, r, 'TALL DIGITS 8X16 - FONT A', FONT_A, 'gold')
    tall(c, 1, r + 2, '0123456789', 'white')
    tall(c, 13, r + 2, '004200', 'pink')
    tall(c, 21, r + 2, '001500', 'lime')
    tall(c, 29, r + 2, '052300', 'gold')
    r += 6
    for mood in MOODS:
        bg = bg_match(mood)
        for key in ('a', 'b'):
            strip = bg[48:64].copy()
            text(strip, 1, 0, 'PLAYER 1 004200 }}} HIGH SCORE 052300', FONTS[key], 'white')
            text(strip, 1, 1, 'ROUND 3 - %s  CREDITS 2' % MOODNAME[mood], FONTS[key], 'pink' if key == 'a' else 'gold')
            c[r * 8:r * 8 + 16] = strip
            r += 2
    return c[:r * 8 + 8]


# ------------------------------------------------------------------ output
WEAK = {
    'a': 'Weak point: the most expensive option, and pink gum on the pink ember dusk sky keeps its shape only through the dark keyline.',
    'b': 'Weak point: a flat rectangle that hides a 28 by 9 cell block of sky; the least gum-like of the three and its only motion is the bulb chase.',
    'c': 'Weak point: the letters are small (23 px) and the ragged soot edge reads as noise at 1x; the least legible from across a room.',
    'fa': 'Weak point: two pixel stems leave tight counters, so 0, O and D, and M and W, are close at 1x.',
    'fb': 'Weak point: a close relative of font A; the one pixel right stem is weaker over bright sky and it has no tall digits.',
    'h1': 'Weak point: the band needs 20 sprites (or 49 more tiles) and the bottom line sits unbacked on the hazard strip.',
    'h2': 'Weak point: the bottom line is hard to read on the storm hazard stripes, and tall digits can sit on the bright moon or clouds.',
}


def write_index(cost):
    def img(fn, w=None):
        st = ' style="width:%dpx"' % w if w else ''
        return '<a href="%s"><img src="%s" alt="%s"%s></a>' % (fn, fn, fn, st)

    def col(head, body):
        return '<div class="col"><h3>%s</h3>%s</div>' % (head, body)

    h = ['<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>Gumbirds: title logo, font and HUD drafts</title><style>',
         'body{background:#14151b;color:#d9dce6;font:15px/1.5 -apple-system,"Helvetica Neue",Arial,sans-serif;margin:24px}',
         'h1{font-size:24px;margin:0 0 4px}h2{font-size:19px;margin:36px 0 10px;border-bottom:2px solid #c93aa0;padding-bottom:4px}',
         'h3{font-size:15px;margin:0 0 6px;color:#fff}p{margin:6px 0;max-width:70em}',
         'img{image-rendering:pixelated;max-width:100%;display:block;margin:6px 0;border:1px solid #2c2e3a;background:#30323e}',
         '.row{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}.row.two{grid-template-columns:repeat(2,1fr)}',
         '.col{background:#1c1e27;padding:10px;border-radius:4px}.weak{color:#ffb35c}.cost{color:#9fd8ff}a{color:#ff9ad5}',
         '</style></head><body>',
         '<h1>Gumbirds: title logo, fix font and HUD drafts</h1>',
         '<p>Draft round, 10 November 2026. Every image is 320 x 224 game pixels shown at 3x unless marked 1x; click an image for full size. '
         'Backdrops are earlier draft renders. Costs are in <a href="numbers.txt">numbers.txt</a>, choices in <a href="README.md">README.md</a>.</p>',
         '<h2>Title logo: three options</h2><div class="row">']
    names = {'a': 'A. Stretched gum (sprites)', 'b': 'B. Enamel rooftop sign (fix tiles)', 'c': 'C. Floating soot letters (sprites)'}
    sheets = {'a': 'logo_a_gum_1x.png', 'b': 'logo_b_sign_1x.png', 'c': 'logo_c_float_1x.png'}
    for k in 'abc':
        body = img('anim_logo_%s_3x.gif' % k) + '<p class="cost">%s</p><p class="weak">%s</p>' % (cost[k], WEAK[k])
        body += ''.join(img('title_%s_%s_3x.png' % (k, m)) for m in MOODS) + '<p>Sheet at 1x:</p>' + img(sheets[k])
        h.append(col(names[k], body))
    h.append('</div><h2>Fix font: two options</h2>' + img('specimen_3x.png') + '<div class="row two">')
    h.append(col('Font A, Gumdrop', '<p class="cost">%s</p><p class="weak">%s</p>' % (cost['fa'], WEAK['fa']) + '<p>Sheets at 1x and at 4x:</p>'
                 + img('font_a_gumdrop_1x.png') + img('font_a_gumdrop_1x.png', 512) + img('font_a_tall_digits_1x.png') + img('font_a_tall_digits_1x.png', 320)))
    h.append(col('Font B, Signwriter', '<p class="cost">%s</p><p class="weak">%s</p>' % (cost['fb'], WEAK['fb']) + '<p>Sheets at 1x and at 4x:</p>'
                 + img('font_b_signwriter_1x.png') + img('font_b_signwriter_1x.png', 512)))
    h.append('</div><h2>HUD: two layouts</h2><p>Storm shows the one player case with the join prompt. Both layouts keep to fix rows 0, 1 and 27; '
             'the play ceiling is y = 16.</p><div class="row two">')
    for lay in '12':
        body = '<p class="cost">%s</p><p class="weak">%s</p>' % (cost['h' + lay], WEAK['h' + lay])
        for m in MOODS:
            body += '<p>%s, font A, 3x and 1x:</p>' % MOODNAME[m].capitalize() + img('hud%s_fonta_%s_3x.png' % (lay, m)) + img('hud%s_fonta_%s_1x.png' % (lay, m))
        body += '<p>Same layout in font B:</p>' + ''.join(img('hud%s_fontb_%s_3x.png' % (lay, m)) for m in MOODS)
        body += '<p>Fix layer alone, 1x:</p>' + img('hud%s_layer_1x.png' % lay)
        h.append(col(HUDNAME[lay], body))
    h.append('</div><h2>Results and name entry (layout 2, font A)</h2><p>Score values are placeholders.</p><div class="row two">')
    h.append(col('Round results', img('results_moon_3x.png') + img('results_dusk_3x.png')))
    h.append(col('Three letter name entry', img('entry_moon_3x.png') + img('entry_dusk_3x.png')))
    h.append('</div></body></html>')
    with open(os.path.join(HERE, 'index.html'), 'w') as fh:
        fh.write('\n'.join(h) + '\n')


def main():
    soot = load_soot()
    num = []
    # logos, 1x sheets
    la = logo_a()
    lb_full = logo_b(0)
    lb = lb_full[0:B_Y1 + 4, B_X0 - 4:B_X1 + 4]
    lc_full = logo_c(0)
    lc = lc_full[C_Y - 4:C_Y + 68, C_X:C_X + 8 * C_PITCH]
    save('logo_a_gum_1x.png', la)
    save('logo_b_sign_1x.png', lb)
    save('logo_c_float_1x.png', lc)
    ta, sa = sprite_stats([logo_a()])
    ta_all, sa_all = sprite_stats([logo_a(f) for f in range(10)])
    tb, cb = fix_stats(lb_full)
    units = [u for u, _, _ in logo_c_units(0)]
    tc, _ = sprite_stats(units)
    units_all = [u for f in range(C_NF) for u, _, _ in logo_c_units(f)]
    tc_all, _ = sprite_stats(units_all)
    num += ['LOGOS', '',
            'A stretched gum   : sprites. layer %dx%d, %d colours in 1 sprite palette, %d unique 16x16 tiles for the still, '
            '%d over the 10 animation frames, at most %d sprites on a scanline (hardware limit 96, title has no gameplay sprites '
            'except two Sootlings = 4 more).' % (A_W, A_H, ncol(la), ta, ta_all, sa_all),
            'B enamel sign     : fix tiles. %d cells used, %d unique 8x8 tiles, %d colours in 1 fix palette, 0 sprites. '
            'Bulb chase = rotating 3 palette entries, 0 extra tiles.' % (cb, tb, ncol(lb_full)),
            'C floating letters: sprites. 8 units of 32x64 (2 strips each) = 16 sprites, 16 on a scanline at most; '
            '%d unique 16x16 tiles for the still, %d if the bubble sway is drawn as tiles (the bob itself is sprite y, 0 tiles); '
            'palettes: soot letters %d colours, pink gum %d, lime gum %d (3 sprite palettes; the gum ones are the Sootling gum ramps).'
            % (tc, tc_all, len(SOOTP) - 1, len(GUMP) - 1, len(LIMEP) - 1), '']
    for name, pal in (('gum (logo A, bubbles)', GUMP), ('lime gum', LIMEP), ('enamel sign', SIGNP), ('soot letters', SOOTP)):
        num.append('palette %-22s: %s' % (name, ' '.join('%d,%d,%d' % c for c in pal[1:])))
    # title mock-ups and GIFs
    for which in 'abc':
        for mood in MOODS:
            save('title_%s_%s_3x.png' % (which, mood), title(mood, which, None, soot), 3)
    save_gif('anim_logo_a_3x.gif', [title('moon', 'a', f, soot) for f in range(10)], 110)
    save_gif('anim_logo_b_3x.gif', [title('storm', 'b', f, soot) for f in range(6)], 150)
    save_gif('anim_logo_c_3x.gif', [title('dusk', 'c', f, soot) for f in range(C_NF)], 90)
    # fonts
    save('font_a_gumdrop_1x.png', font_sheet(FONT_A))
    save('font_b_signwriter_1x.png', font_sheet(FONT_B))
    save('font_a_tall_digits_1x.png', tall_sheet())
    save('specimen_3x.png', specimen(), 3)
    num += ['', 'FONTS', '',
            'font A Gumdrop    : %d fix tiles (26 letters, 10 digits, 10 punctuation, 3 icons) + 20 tiles for the 8x16 digits = %d'
            % (len(ORDER), len(ORDER) + 20),
            'font B Signwriter : %d fix tiles (same set); it has no tall digits of its own' % len(ORDER),
            'fix palettes      : 1 per text colour (white, pink, lime, gold, dim = 5 of the 16), 15 colours each: 4 face shades, '
            '1 shadow, 10 fixed icon colours', '']
    for k, pal in FPAL.items():
        num.append('palette text %-6s: %s' % (k, ' '.join('%d,%d,%d' % c for c in pal[1:])))
    # HUD
    num += ['', 'HUD', '']
    for lay in '12':
        for key in 'ab':
            for mood in MOODS:
                bg = bg_match(mood)
                o = HUDS[lay](mood, FONTS[key], p2=(mood != 'storm'))
                c = compose(bg, o)
                save('hud%s_font%s_%s_3x.png' % (lay, key, mood), c, 3)
                if key == 'a':
                    save('hud%s_font%s_%s_1x.png' % (lay, key, mood), c)
                    rows = (27,) if lay == '1' else (0, 1, 27)
                    worst, weak = contrast(bg, o, rows)
                    num.append('%s, font A, %-5s: unbacked text rows %s; worst cell gap %d luminance (face minus backdrop mean), '
                               '%d cells under 70' % (HUDNAME[lay], mood, rows, worst, weak))
            if key == 'a':
                o = HUDS[lay]('dusk', FONTS[key])
                save('hud%s_layer_1x.png' % lay, o)
                t, cells = fix_stats(o)
                num.append('%s: %d fix cells drawn, covers %d of 224 scanlines of backdrop%s' % (
                    HUDNAME[lay], cells, 24 if lay == '1' else 24,
                    '; the band is opaque: either 20 sprites of one dark 16x16 tile on lines 0..15 behind the glyphs, '
                    'or a second copy of the font with a filled background (+%d tiles)' % len(ORDER) if lay == '1' else
                    '; no band, glyph shadow only'))
    for mood in ('moon', 'dusk'):
        save('results_%s_3x.png' % mood, compose(bg_match(mood), results(mood, FONT_A)), 3)
        save('entry_%s_3x.png' % mood, compose(bg_plain(mood), entry(mood, FONT_A)), 3)
    num += ['', 'results and name entry panels: fix tiles, 9 frame tiles + 3 fill tiles, drawn in the white text palette slots; '
            'score values on the results screen are placeholders (the design fixes "points for stomps and wins", no values).',
            'fix layer facts used: 8x8 tiles, 40x28 visible cells, 15 colours + transparent per palette, in front of all sprites, '
            'no flip, no scaling, no scroll. Play ceiling is y = 16, so fix rows 0 and 1 cover no play area.']
    write_index({
        'a': 'Sprites: %d unique 16x16 tiles still, %d with the 10 frame animation; at most %d sprites on a scanline; 1 palette of %d colours.' % (ta, ta_all, sa_all, ncol(la)),
        'b': 'Fix tiles: %d unique 8x8 tiles in %d cells; 0 sprites; 1 fix palette of %d colours; the bulb chase is a 3 entry palette rotation.' % (tb, cb, ncol(lb_full)),
        'c': 'Sprites: 16 (8 units of 32x64), 16 on a scanline; %d unique 16x16 tiles still, %d with bubble sway frames; 3 palettes, 2 shared with the Sootling gum.' % (tc, tc_all),
        'fa': '%d fix tiles plus 20 for the 8x16 digits; 5 text palettes of 15 colours.' % len(ORDER),
        'fb': '%d fix tiles; same 5 palettes.' % len(ORDER),
        'h1': 'Fix rows 0, 1 and 27; opaque band on rows 0 and 1 from 20 sprites of one dark tile, or %d more filled-background tiles.' % len(ORDER),
        'h2': 'Fix rows 0, 1 and 27; no band, 0 sprites; uses the 20 tall digit tiles.',
    })
    with open(os.path.join(HERE, 'numbers.txt'), 'w') as fh:
        fh.write('\n'.join(num) + '\n')
    print('\n'.join(num))


# ====================================================================== FINAL ROUND (10 November 2026)
# Everything above this line is the draft round, kept as the "before" reference. Everything below builds the
# final sheets for the chosen options: logo A, font A with tall digits, HUD layout 2.
LW = np.array([.299, .587, .114])
HAZ = ('spikes', 'water', 'lava', 'fire')


def q5s(c):
    return '%d,%d,%d (5-bit %d,%d,%d)' % (c[0], c[1], c[2], c[0] >> 3, c[1] >> 3, c[2] >> 3)


# ------------------------------------------------------------------ backdrops for the row 27 measurement
def bg_scene(mood):
    """Background without islands or hazard (backgrounds-final render); falls back to the islands scene."""
    p = os.path.join(DR, '2026-11-10-backgrounds-final', 'scene_%s_1x.png' % mood)
    if os.path.exists(p):
        a = np.asarray(Image.open(p).convert('RGB'))
        if a.shape[:2] == (H, W):
            return a.copy()
    return bg_match(mood)


def haz_frames(kind):
    a = np.asarray(Image.open(os.path.join(DR, '2026-11-10-hazards-final', 'frames_%s_1x.png' % kind)).convert('RGBA'))
    rows = a.shape[0] // 32
    return [[a[r * 32:(r + 1) * 32, f * 64:(f + 1) * 64] for r in range(rows)] for f in range(16)]


def bg_hazard(base, tiles):
    """Hazard strip on y 192..223: 64 px tiles, tile A and tile B alternate where the hazard has two."""
    c = base.copy()
    for i in range(5):
        t = tiles[i % len(tiles)]
        m = t[..., 3] > 0
        c[192:224, i * 64:(i + 1) * 64][m] = t[..., :3][m]
    return c


# ------------------------------------------------------------------ font A final
GA2 = dict(GA)
GA2.update({
    '0': '.####../##..##./##.###./###.##./##..##./##..##./.####..',      # narrow and slashed; O stays wide and open
    'M': '##...##/###.###/#######/##.#.##/##...##/##...##/##...##',
    'W': '##...##/##...##/##.#.##/##.#.##/#######/.##.##./.##.##.',      # split, inset feet; M keeps full width legs
    'I': '######./..##.../..##.../..##.../..##.../..##.../######.',      # wide serifs
    '1': '..##.../.###.../####.../..##.../..##.../..##.../..##...',      # flag, no foot
    '5': '#######/##...../######./.....##/.....##/##...##/.#####.',      # flat top, high bar, deep bowl
    'S': '.#####./##...##/###..../.#####./....###/##...##/.#####.',
    '8': '..###../.##.##./.##.##./.#####./##...##/##...##/.#####.',      # small head, wide belly
    'Z': '#######/.....##/....##./.#####./.##..../##...../#######',      # cross bar
    '6': '..####./.##..../##...../######./##...##/##...##/.#####.',
    '9': '.#####./##...##/##...##/.######/.....##/....##./.####..',
    '^': '...#.../..###../.#####./#######/......./......./.......',
    'v': '......./......./......./#######/.#####./..###../...#...',
})
ICONS2 = {'{': ICONS['{'], '}': ICONS['}']}
# Sootling icon, 16x8 = two fix tiles: soot navy outline (d), blue body (e), white goggle eyes (c), ember beak (f)
SOOT16 = ['....d..dd..d....',
          '..dddddddddddd..',
          '.ddcccddddcccdd.',
          '.decdceeeecdced.',
          '.deccceffeccced.',
          '.ddeeeffffeeedd.',
          '..dddddddddddd..',
          '................']
ORDER2 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,:!?-'/<>^v{}"
ICONCH = ('{', '}', '~L', '~R')


def back(t):
    """Backed copy of a glyph tile: filled plate (index 13, soot navy), glyph one pixel lower so the plate shows above it."""
    b = np.full_like(t, 13)
    s = t[:-1]
    b[1:][s > 0] = s[s > 0]
    return b


def soot_tiles():
    t = np.array([[0 if ch == '.' else int(ch, 16) for ch in r] for r in SOOT16], np.uint8)
    m = t > 0
    for y in range(7):
        for x in range(15):
            if m[y, x] and t[y + 1, x + 1] == 0:
                t[y + 1, x + 1] = 5
    return t[:, :8], t[:, 8:]


def frame_tile(name):
    t = np.full((8, 8), 13, np.uint8)
    sfx = name[2:]
    top, bot, lef, rig = 't' in sfx, 'b' in sfx, 'l' in sfx, 'r' in sfx
    if top:
        t[1, :] = 3
    if lef:
        t[:, 1] = 3
    if bot:
        t[6, :] = 4
    if rig:
        t[:, 6] = 4
    if top:
        t[0, :] = 5
    if bot:
        t[7, :] = 5
    if lef:
        t[:, 0] = 5
    if rig:
        t[:, 7] = 5
    if top and lef:
        t[0, 0] = 0
    if top and rig:
        t[0, 7] = 0
    if bot and lef:
        t[7, 0] = 0
    if bot and rig:
        t[7, 7] = 0
    return t


SPECIALS = ['capL', 'capR', 'joint', 'fill', 'f_tl', 'f_t', 'f_tr', 'f_l', 'f_r', 'f_bl', 'f_b', 'f_br']


def build_tiles():
    T, IDX = {}, {}
    for i, ch in enumerate(ORDER2):
        t = tile_icon(ICONS2[ch]) if ch in ICONS2 else tile_a(GA2[ch])
        T[('p', ch)] = t
        IDX[('p', ch)] = i
    sl, sr = soot_tiles()
    T[('p', '~L')], T[('p', '~R')] = sl, sr
    IDX[('p', '~L')], IDX[('p', '~R')] = 50, 51
    capl = np.zeros((8, 8), np.uint8)
    capl[:, 6:] = 13
    capl[1:7, 5] = 13
    capr = capl[:, ::-1].copy()
    sp = {'capL': capl, 'capR': capr, 'joint': capr | capl, 'fill': np.full((8, 8), 13, np.uint8)}
    for n in SPECIALS[4:]:
        sp[n] = frame_tile(n)
    for i, n in enumerate(SPECIALS):
        T[('s', n)] = sp[n]
        IDX[('s', n)] = 52 + i
    rule = np.full((8, 8), 13, np.uint8)
    rule[3, :] = 4
    rule[4, :] = 5
    T[('s', 'rule')] = rule
    IDX[('s', 'rule')] = 74
    for d in '0123456789':
        t16 = tile_tall(TALLG[d])
        b16 = back(t16)
        for k in (0, 1):
            T[('pt', d, k)] = t16[k * 8:k * 8 + 8]
            IDX[('pt', d, k)] = 64 + int(d) + 16 * k
            T[('bt', d, k)] = b16[k * 8:k * 8 + 8]
            IDX[('bt', d, k)] = 160 + int(d) + 16 * k
    for (kind, ch), i in list(IDX.items())[:52] if False else [(k, v) for k, v in IDX.items() if k[0] == 'p']:
        T[('b', ch)] = back(T[('p', ch)])
        IDX[('b', ch)] = 96 + i
    return T, IDX


TILE, TIDX = build_tiles()
assert len(set(TIDX.values())) == len(TIDX) == len(TILE)


def txt(c, col, row, s, pal='white', backed=False):
    """Free text on any canvas (specimens); screens go through the Fix class."""
    kind = 'b' if backed else 'p'
    for i, ch in enumerate(s):
        if ch == ' ':
            if backed:
                blit(c, TILE[('s', 'fill')], FPAL[pal], (col + i) * 8, row * 8)
        elif ch == '~':
            blit(c, TILE[(kind, '~L')], FPAL[pal], (col + i) * 8, row * 8)
            blit(c, TILE[(kind, '~R')], FPAL[pal], (col + i + 1) * 8, row * 8)
        else:
            blit(c, TILE[(kind, ch)], FPAL[pal], (col + i) * 8, row * 8)


def txtall(c, col, row, s, pal='white', backed=False):
    for i, ch in enumerate(s):
        for k in (0, 1):
            blit(c, TILE[('bt' if backed else 'pt', ch, k)], FPAL[pal], (col + i) * 8, (row + k) * 8)


class Fix:
    """A 40x28 fix layer: one tile and one palette per cell, nothing else. Text over a plate or a panel picks the backed glyph."""

    def __init__(s):
        s.c, s.solid = {}, set()

    def put(s, col, row, key, pal='white'):
        assert 0 <= col < 40 and 0 <= row < 28, (col, row, key)
        assert key in TILE, key
        s.c[(col, row)] = (key, pal)

    def text(s, col, row, st, pal='white'):
        for i, ch in enumerate(st):
            if ch == ' ':
                continue
            kind = 'b' if (col + i, row) in s.solid else 'p'
            if ch == '~':
                s.put(col + i, row, (kind, '~L'), pal)
                s.put(col + i + 1, row, (kind, '~R'), pal)
            else:
                s.put(col + i, row, (kind, ch), pal)

    def ctext(s, row, st, pal='white'):
        s.text((40 - len(st)) // 2, row, st, pal)

    def rtext(s, col_end, row, st, pal='white'):
        s.text(col_end - len(st) + 1, row, st, pal)

    def tall(s, col, row, st, pal='white'):
        for i, ch in enumerate(st):
            kind = 'bt' if (col + i, row) in s.solid else 'pt'
            s.put(col + i, row, (kind, ch, 0), pal)
            s.put(col + i, row + 1, (kind, ch, 1), pal)

    def plate(s, row, c0, c1, pal='white'):
        s.put(c0 - 1, row, ('s', 'capL'), pal)
        s.put(c1 + 1, row, ('s', 'capR'), pal)
        for c in range(c0, c1 + 1):
            s.put(c, row, ('s', 'fill'), pal)
            s.solid.add((c, row))

    def joint(s, col, row, pal='white'):
        s.put(col, row, ('s', 'joint'), pal)

    def panel(s, col, row, cols, rows, pal='white'):
        for r in range(rows):
            for c in range(cols):
                sfx = ('t' if r == 0 else 'b' if r == rows - 1 else '') + ('l' if c == 0 else 'r' if c == cols - 1 else '')
                s.put(col + c, row + r, ('s', 'f_' + sfx if sfx else 'fill'), pal)
                if not sfx:
                    s.solid.add((col + c, row + r))

    def rule(s, row, c0, c1, pal='white'):
        for c in range(c0, c1 + 1):
            s.put(c, row, ('s', 'rule'), pal)

    def render(s):
        o = new(H, W)
        for (col, row), (key, pal) in s.c.items():
            blit(o, TILE[key], FPAL[pal], col * 8, row * 8)
        return o

    def face(s, skip_dim=True):
        m = np.zeros((H, W), bool)
        for (col, row), (key, pal) in s.c.items():
            if key[0] in ('p', 'b', 'pt', 'bt') and key[1] not in ICONCH and not (skip_dim and pal == 'dim'):
                t = TILE[key]
                m[row * 8:row * 8 + 8, col * 8:col * 8 + 8] = (t >= 1) & (t <= 4)
        return m

    def name(s, col, row):
        k = s.c.get((col, row))
        return '?' if k is None else '%s (%s)' % (k[0][1], k[1])


def fix_sheet():
    c = new(96, 128)
    for key, i in TIDX.items():
        blit(c, TILE[key], FPAL['white'], (i % 16) * 8, (i // 16) * 8)
    return c


def glyph_pairs(G):
    """Every pair of 7x7 glyph bitmaps with the number of differing pixels, closest first."""
    ks = [k for k in G if k.isalnum() and k not in ('v',)]
    out = []
    for i, a in enumerate(ks):
        for b in ks[i + 1:]:
            out.append((int((parse(G[a], 7) != parse(G[b], 7)).sum()), a, b))
    return sorted(out)


# ------------------------------------------------------------------ HUD layout 2 final, results, name entry
def row27(f, backed=True):
    if backed:
        f.plate(27, 2, 18)
        f.plate(27, 20, 26)
        f.plate(27, 28, 36)
        f.joint(19, 27)
        f.joint(27, 27)
    f.text(2, 27, 'HIGH SCORE', 'gold')
    f.text(13, 27, DATA['hi'], 'white')
    f.text(20, 27, 'ROUND %d' % DATA['rnd'], 'white')
    f.text(28, 27, 'CREDITS %d' % DATA['cr'], 'white')


def hud_final(p2=True, backed=True):
    f = Fix()
    f.tall(2, 0, DATA['p1'], 'white')
    f.text(9, 0, 'PLAYER 1', 'pink')
    f.text(9, 1, '}' * DATA['g1'], 'white')
    if p2:
        f.tall(32, 0, DATA['p2'], 'white')
        f.text(23, 0, 'PLAYER 2', 'lime')
        f.rtext(30, 1, '}' * DATA['g2'], 'lime')
    else:
        f.text(30, 0, 'PLAYER 2', 'dim')
        f.text(27, 1, 'PRESS START', 'lime')
    row27(f, backed)
    return f


def results_final():
    f = hud_final()
    f.panel(5, 3, 30, 22)
    f.ctext(4, 'ROUND %d CLEAR' % DATA['rnd'], 'gold')
    f.text(17, 6, 'PLAYER 1', 'pink')
    f.text(26, 6, 'PLAYER 2', 'lime')
    rows = [(8, 'STOMPS', '3', '1', 'white'), (10, 'STOMP POINTS', '1500', '500', 'dim'), (12, 'ROUND WIN', '2000', '0', 'white'),
            (14, 'GUM LEFT', '}}', '-', 'white'), (16, 'GUM BONUS', '500', '0', 'dim')]
    for y, lab, a, b, pal in rows:
        f.text(7, y, lab, pal)
        f.rtext(24, y, a, 'white')
        f.rtext(33, y, b, 'white')
    f.rule(17, 7, 33, 'pink')
    f.text(7, 19, 'TOTAL', 'gold')
    f.tall(19, 18, '004000', 'pink')
    f.tall(28, 18, '000500', 'lime')
    f.ctext(21, 'PLAYER 1 WINS THE ROUND!', 'gold')
    f.ctext(23, 'NEXT ROUND IN 5', 'dim')
    return f


def entry_final():
    f = Fix()
    f.panel(4, 2, 32, 24)
    f.ctext(3, 'NEW HIGH SCORE!', 'gold')
    f.text(6, 6, '~', 'white')
    f.text(9, 6, 'PLAYER 1', 'pink')
    f.tall(6, 7, '004000', 'white')
    f.text(16, 8, 'RANK 3 OF 10', 'dim')
    f.text(22, 6, 'TIME', 'white')
    f.tall(27, 5, '17', 'gold')
    f.ctext(10, 'ENTER YOUR NAME', 'white')
    name, cur = 'BI', 2
    for i in range(3):
        cx = 15 + i * 4
        ch = name[i] if i < len(name) else 'R'
        if i == cur:
            f.text(cx, 12, '^', 'pink')
            f.text(cx, 13, chr(ord(ch) - 1), 'dim')
            f.text(cx, 14, ch, 'pink')
            f.text(cx, 15, chr(ord(ch) + 1), 'dim')
            f.text(cx, 16, 'v', 'pink')
        else:
            f.text(cx, 14, ch, 'white')
            f.text(cx, 15, '-', 'dim')
    f.ctext(18, 'STICK: LETTER   A: NEXT', 'dim')
    for j, (nm, sc) in enumerate(TABLE):
        pal = 'pink' if j == 2 else 'white'
        f.text(10, 20 + j, '%d.' % (j + 1), pal)
        f.text(14, 20 + j, 'BI ' if j == 2 else nm, pal)
        f.text(20, 20 + j, sc, pal)
        if j == 2:
            f.text(27, 20 + j, '<', 'gold')
    return f


def cell_gaps(comp, face, rows):
    """Per glyph cell: mean luminance of the face pixels minus the 90th percentile luminance of every other pixel
    in the same 8x8 cell of the finished picture (shadow, plate or backdrop). Negative = backdrop brighter than the glyph."""
    L = comp.astype(float) @ LW
    out = []
    for row in rows:
        for col in range(40):
            sl = np.s_[row * 8:row * 8 + 8, col * 8:col * 8 + 8]
            fm = face[sl]
            if fm.sum() < 4:
                continue
            out.append((float(L[sl][fm].mean() - np.percentile(L[sl][~fm], 90)), row, col))
    return out


def draft_face(o):
    sh = np.zeros(o.shape[:2], bool)
    for p in FPAL.values():
        sh |= (o == np.array(p[5], np.uint8)).all(-1)
    return opaque(o) & ~sh


# ------------------------------------------------------------------ logo A final
# 1 keyline plum, 2..4 gum deep to light, 5 warm cream highlight (second hue), 6 specular, 7 under shadow, 8 outer line,
# 9 cool rim light (bounce from the lower right), 10 violet step between rim and deep gum. Hard clusters only, no dither.
GUM2 = P((90, 16, 115), (165, 33, 156), (255, 82, 181), (255, 156, 214), (255, 231, 189), (255, 255, 255), (24, 8, 49), (8, 8, 24),
         (99, 222, 255), (115, 90, 231))
PADC = 16
RIM_T = (.74, .84, .80)


def ell(M, cx, cy, rx, ry):
    yy, xx = np.mgrid[0:M.shape[0], 0:M.shape[1]]
    M |= ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1


def gum2(M, shadow=True, thin=False):
    I = light(M)
    idx = np.zeros(M.shape, np.uint8)
    idx[M] = (2 + np.digitize(I, (.36, .62, .80, .93)))[M]
    inner = ero(M)
    e1 = M & ~inner
    e2 = inner & ~ero(inner)
    idx[(idx == 6) & e1] = 5
    idx[(idx == 2) & e1 & (I > .2)] = 3
    I2 = light(M, L=(.58, .62, .42))            # bounce light from the lower right
    pre = idx.copy()
    idx[e1 & (I2 > RIM_T[0])] = 10
    idx[e1 & (I2 > RIM_T[1])] = 9
    idx[e2 & (I2 > RIM_T[2]) & (idx <= 3)] = 10
    rim = idx >= 9                              # no beading: a rim pixel needs two rim neighbours, else it goes back to gum
    for _ in range(3):
        n = sum(np.roll(np.roll(rim, dy, 0), dx, 1).astype(int) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dx or dy)
        bad = rim & (n < 2)
        idx[bad] = pre[bad]
        rim &= ~bad
    r1 = dil(M, True) & ~M
    idx[r1] = 1
    body = M | r1
    r2 = dil(body) & ~body
    idx[r2] = 8
    if not thin:
        b2 = body | r2
        r3 = dil(b2) & ~b2
        idx[r3] = 8
        if shadow:
            idx[shift(b2 | r3, 3, 4) & (idx == 0)] = 7
    return idx


def piece(fn, thin):
    m = np.zeros((16, 16), bool)
    fn(m)
    return gum2(m, shadow=False, thin=thin)


def _diag(r):
    def fn(m):
        disc(m, 8 - r * .55, 8 + r * .55, r)
        disc(m, 8 + r * .55, 8 - r * .55, r)
    return fn


FRAG = {(0, 0): piece(_diag(2.0), True), (0, 1): piece(lambda m: ell(m, 8, 8, 2.9, 1.8), True),
        (1, 0): piece(_diag(1.4), True), (1, 1): piece(lambda m: ell(m, 8, 8, 2.1, 1.4), True),
        (2, 0): piece(lambda m: disc(m, 8, 8, 1.1), True), (2, 1): piece(lambda m: disc(m, 8, 8, 1.1), True)}


def _tear(m):
    disc(m, 8, 10, 2.6)
    disc(m, 8, 7, 1.6)
    disc(m, 8, 5, 1.0)


DROP = {'tear': piece(_tear, False), 'ball': piece(lambda m: ell(m, 8, 8, 2.3, 3.1), False)}

# bubble on the I: ('b', radius, x stretch, y stretch) | ('pop', step) | ('nub',)
BUB2 = [('b', 3.0, 1.25, .75),      # 0 anticipation: the nub squashes flat
        ('b', 4.5, .88, 1.18),      # 1 shoots up, stretched tall
        ('b', 7.0, .95, 1.08),      # 2
        ('b', 9.5, 1.0, 1.0),       # 3
        ('b', 12.5, 1.08, .93),     # 4 overshoot: too big and wide
        ('b', 11.5, .96, 1.05),     # 5 settles back, thin and pale
        ('pop', 0), ('pop', 1), ('pop', 2),     # 6..8 burst, shreds fly and fall, torn rim flares then snaps flat
        ('nub',)]                   # 9
# drip under the U: (strand length, bulb radius, neck radius, free drop (offset below the U, tile) or None)
DRIP2 = [(3, 2.4, 1.6, None), (4, 2.6, 1.5, None), (6, 2.8, 1.4, None), (9, 2.9, 1.2, None), (12, 3.0, 1.0, None),
         (16, 3.0, .8, None),                       # 5 neck one pixel thin
         (1.5, 1.5, 1.4, (20, 'tear')),             # 6 snap: the stub recoils shorter than rest, the drop leaves with a tail
         (4.5, 2.0, 1.3, (27, 'ball')),             # 7 stub rebounds long; the drop falls 7, 11, 15 px per frame
         (2.5, 2.1, 1.5, (38, 'ball')),
         (3, 2.3, 1.6, (53, 'ball'))]
STILL_F = 3
_BASE = None


def logo_base():
    global _BASE
    if _BASE is None:
        M = np.zeros((A_H + 2 * PADC, A_W + 2 * PADC), bool)
        x, top, hgt, r = 5 + PADC, 44 + PADC, 36, 5
        pos = {}
        for i, ch in enumerate('GUMBIRDS'):
            m = letter(ch, hgt, ('round', r), 12)
            m = np.pad(m, 2)
            m = dil(~dil(~m, True), True)                # open with a 3x3 square: no one-pixel bumps on the edge
            m = (~dil(~dil(m, True), True))[2:-2, 2:-2]  # close: no one-pixel notches
            y = top - r + A_OFF[i]
            M[y:y + m.shape[0], x:x + m.shape[1]] |= m
            pos[ch] = (x, y, m.shape[1], m.shape[0])
            x += m.shape[1] + 3
        for a, b, ya, sag in (('G', 'U', 18, 3), ('D', 'S', 30, 2)):
            xa = pos[a][0] + pos[a][2] - 3
            xb = pos[b][0] + 3
            y0 = pos[a][1] + ya
            for xx in range(xa, xb + 1):
                t = (xx - xa) / max(1, xb - xa)
                disc(M, xx, y0 + sag * 4 * t * (1 - t), 1.5)
        _BASE = (M, pos)
    return _BASE[0].copy(), _BASE[1]


def logo_frame(f):
    """Returns (index canvas of the body layer, list of free pieces (16x16 index tile, x, y)) in canvas coordinates."""
    M, pos = logo_base()
    ix, iy = pos['I'][0] + pos['I'][2] // 2, pos['I'][1]
    pieces, marks = [], None
    b = BUB2[f]
    if b[0] == 'b':
        _, rb, sx, sy = b
        cy = iy - rb * sy + 3
        ell(M, ix, cy, rb * sx, rb * sy)
        disc(M, ix, iy + 1, 2.4)
        marks = (ix, cy, rb, sx, sy)
    elif b[0] == 'pop':
        k = b[1]
        d, g = (15, 21, 26)[k], (0, 3, 9)[k]
        for j in range(7):
            if k == 2 and j % 2:
                continue
            a = TAU * (j + .3) / 7
            t = FRAG[(k, j % 2)]
            if cos(a) < 0:
                t = t[:, ::-1]
            pieces.append((t, int(round(ix + d * cos(a))) - 8, int(round(iy - 8.5 - d * .85 * sin(a) + g)) - 8))
        if k == 0:
            ell(M, ix, iy - 1, 4.4, 2.6)
            disc(M, ix - 3.5, iy - 4, 1.4)
            disc(M, ix + 3.5, iy - 3.5, 1.4)
        elif k == 1:
            ell(M, ix, iy, 3.4, 2.2)
            disc(M, ix - 2.5, iy - 2, 1.2)
            disc(M, ix + 2.5, iy - 2, 1.2)
        else:
            ell(M, ix, iy + 1.5, 3.9, 1.6)
    else:
        ell(M, ix, iy, 2.6, 2.0)
    ux, ub = pos['U'][0] + pos['U'][2] // 2 + 1, pos['U'][1] + pos['U'][3] - 2
    s, bulb, neck, free = DRIP2[f]
    for k in range(int(round(s)) + 1):
        disc(M, ux, ub + k, neck + (2.4 - neck) * max(0, 1 - k / 4))
    disc(M, ux, ub + s + 1, bulb)
    if free:
        pieces.append((DROP[free[1]], ux - 8, int(ub + free[0]) - 8))
    idx = gum2(M)
    if marks and marks[2] >= 4.5:
        ix, cy, rb, sx, sy = marks
        yy, xx = np.mgrid[0:M.shape[0], 0:M.shape[1]]
        inside = ((xx - ix) / (rb * sx - 2.5)) ** 2 + ((yy - cy) / (rb * sy - 2.5)) ** 2 <= 1
        if rb >= 9:                                  # stretched membrane is thinner and paler
            idx[inside & (idx == 3)] = 4
        if rb >= 11:
            idx[inside & (idx == 2)] = 3
        spec = ((xx - (ix - .40 * rb * sx)) / max(1.2, .20 * rb)) ** 2 + ((yy - (cy - .40 * rb * sy)) / max(1.0, .14 * rb)) ** 2 <= 1
        idx[spec & inside] = 6
        if rb >= 9:
            glow = ((xx - (ix - .40 * rb * sx)) / (.20 * rb + 2)) ** 2 + ((yy - (cy - .40 * rb * sy)) / (.14 * rb + 2)) ** 2 <= 1
            idx[glow & inside & (idx != 6)] = 5
    return idx, pieces


_FR = None


def frames():
    global _FR
    if _FR is None:
        _FR = [logo_frame(f) for f in range(10)]
    return _FR


def logo_draw(c, f, x0=A_X, y0=A_Y):
    idx, pieces = frames()[f]
    over(c, rgb_of(idx, GUM2), x0 - PADC, y0 - PADC)
    for t, px, py in pieces:
        over(c, rgb_of(t, GUM2), x0 - PADC + px, y0 - PADC + py)


def shifted(canvas, ox, oy):
    hh, ww = canvas.shape
    L = np.zeros((hh + 16, ww + 16), canvas.dtype)
    L[oy:oy + hh, ox:ox + ww] = canvas
    return L


def tiles_idx(L, uniq, flips=True):
    for ty in range(0, L.shape[0], 16):
        for tx in range(0, L.shape[1], 16):
            t = L[ty:ty + 16, tx:tx + 16]
            if t.any():
                uniq.add(min(t.tobytes(), t[:, ::-1].tobytes(), t[::-1].tobytes(), t[::-1, ::-1].tobytes()) if flips else t.tobytes())


def best_offset():
    body = [idx for idx, _ in frames()]
    best = None
    for oy in range(16):
        for ox in range(16):
            u = set()
            for b in body:
                tiles_idx(shifted(b, ox, oy), u, False)
            if best is None or len(u) < best[0]:
                best = (len(u), ox, oy)
    return best


def strip_layout(layers):
    ext = {}
    for L in layers:
        for tx in range(0, L.shape[1], 16):
            for ty in range(0, L.shape[0], 16):
                if L[ty:ty + 16, tx:tx + 16].any():
                    a, b = ext.get(tx // 16, (99, -1))
                    ext[tx // 16] = (min(a, ty // 16), max(b, ty // 16))
    return ext


def edge_sep(layer, bg, darks):
    """Colour distance between the outermost gum pixels (those touching the line) and the backdrop they sit on."""
    dark = np.zeros(layer.shape[:2], bool)
    for c in darks:
        dark |= (layer == np.array(c, np.uint8)).all(-1)
    ring = opaque(layer) & ~dark & dil(dark, True)
    d = np.sqrt(((layer[ring].astype(float) - bg[ring].astype(float)) ** 2).sum(-1))
    return float(d.mean()), float(np.percentile(d, 10)), float((d < 80).mean() * 100)


def title_final(mood, f, soot):
    c = bg_plain(mood)
    logo_draw(c, STILL_F if f is None else f)
    ff = 0 if f is None else f
    over(c, soot['player'](ff % 8), 14, 112 + int(round(2 * sin(TAU * ff / 8))))
    over(c, soot['cpu']((ff + 3) % 8)[:, ::-1], 250, 118 + int(round(2 * sin(TAU * (ff + 3) / 8))))
    fx = Fix()
    fx.text(11, 1, 'HIGH SCORE', 'gold')
    fx.text(22, 1, DATA['hi'], 'white')
    if f is None or f % 5 < 3:
        fx.plate(20, 14, 24)
        fx.ctext(20, 'PRESS START', 'gold')
    fx.plate(23, 13, 26)
    fx.ctext(23, '1 OR 2 PLAYERS', 'white')
    fx.plate(27, 28, 36)
    fx.text(28, 27, 'CREDITS %d' % DATA['cr'], 'white')
    over(c, fx.render())
    return c, fx


WEAK2 = {
    'logo': 'Weak point: the still grew from 79 to 82 tiles because the line and the shadow are thicker. The measured colour distance of the outermost gum pixels did not improve; the gain is the wider dark line and the darker shadow. The warm cream highlight covers few pixels and reads as white at 1x. Over the storm sky the cool rim light is close to the sky colour, so there only the dark line separates the logo.',
    'anim': 'Weak point: ten frames still step visibly, and the pop lasts only three frames. The shreds are one-tile sprites with a 1 px line and nearly vanish at 1x over the lit city windows. The tile cut is modest (155 to 130); the bubble and the drip still cost about 40 tiles on top of the still.',
    'font': 'Weak point: G/O, I/T and M/N still differ by only 4 pixels (shapes unchanged; they differ in silhouette, not in pixel count). Z/2 fell from 14 to 9 because the Z gained a cross bar. The backed copies double the glyph tiles; row 27 alone needs only 26 of them.',
    'icon': 'Weak point: at 1x the icon is two white eyes and an ember beak. Over a dark sky the navy outline disappears and only eyes and beak remain. It does not show the player colour.',
    'hud': 'Weak point: the plates hide 8 px of hazard along the bottom row, columns 1 to 37. Rows 0 and 1 stay unbacked, so the pink PLAYER 1 label over the storm sky is the weakest text on screen. Cabinet overscan for rows 0, 1 and 27 and the outer columns is not checked.',
    'mock': 'Weak point: backdrops are earlier draft renders, the results score values are placeholders, the name entry letters are only 8 px tall, and the GIFs are reduced to 255 colours.',
}


def write_index2(info):
    def img(fn, w=None):
        st = ' style="width:%dpx"' % w if w else ''
        return '<a href="%s"><img src="%s" alt="%s"%s></a>' % (fn, fn, fn, st)

    def col(head, body):
        return '<div class="col"><h3>%s</h3>%s</div>' % (head, body)

    def pair(a, b, wa=None, wb=None):
        return '<div class="row two">' + col('Before (draft round)', img(a, wa)) + col('After (final)', img(b, wb)) + '</div>'

    h = ['<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>Gumbirds: final title logo, font and HUD sheets</title><style>',
         'body{background:#101218;color:#d5d9e4;font:15px/1.5 -apple-system,"Helvetica Neue",Arial,sans-serif;margin:24px}',
         'h1{font-size:24px;margin:0 0 4px}h2{font-size:19px;margin:40px 0 10px;border-left:6px solid #37c6e8;padding-left:10px}',
         'h3{font-size:15px;margin:0 0 6px;color:#fff}p{margin:6px 0;max-width:70em}',
         'img{image-rendering:pixelated;max-width:100%;display:block;margin:6px 0;border:1px solid #2a2d3a;background:#2b2e3b}',
         '.row{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:10px 0}.row.two{grid-template-columns:repeat(2,1fr)}',
         '.col{background:#191c26;padding:10px;border-radius:3px}.weak{color:#ffb35c}.cost{color:#8fe0ff}a{color:#8fe0ff}',
         '</style></head><body>',
         '<h1>Gumbirds: final title logo, fix font and HUD sheets</h1>',
         '<p>Final round, 10 November 2026: logo A (stretched gum), font A (Gumdrop) with tall digits, HUD layout 2 (corner tags). '
         'Mock-ups are 320 x 224 game pixels at 3x unless marked 1x; click an image for full size. Backdrops are earlier draft renders. '
         'All numbers are in <a href="numbers.txt">numbers.txt</a>, the reasoning in <a href="README.md">README.md</a>.</p>',
         '<h2>Fix 1: logo separation over the ember dusk sky</h2>',
         pair('logo_before_dusk_3x.png', 'logo_after_dusk_3x.png'), pair('logo_before_dusk_1x.png', 'logo_after_dusk_1x.png'),
         '<p class="cost">%s</p><p class="weak">%s</p>' % (info['logo'], WEAK2['logo']),
         '<p>Final logo over the three moods, 3x and 1x:</p>', img('logo_moods_3x.png'), img('logo_moods_1x.png'),
         '<h2>Fix 2: logo animation, 10 frames</h2>',
         '<div class="row">' + ''.join(col(MOODNAME[m].capitalize(), img('anim_title_%s_3x.gif' % m)) for m in MOODS) + '</div>',
         '<p>Before (draft animation) and after, every frame, 2x:</p>', pair('logo_contact_before_2x.png', 'logo_contact_2x.png'),
         '<p class="cost">%s</p><p class="weak">%s</p>' % (info['anim'], WEAK2['anim']),
         '<p>Import sheets at 1x: the still, the ten body frames, the free pieces (shreds and drop):</p>',
         img('logo_a_still_1x.png'), img('logo_a_frames_1x.png', 352), img('logo_a_pieces_1x.png', 512),
         '<h2>Fix 3: font look-alikes</h2>',
         pair('font_pairs_before_1x.png', 'font_pairs_after_1x.png'), pair('font_pairs_before_1x.png', 'font_pairs_after_1x.png', 600, 600),
         '<p class="cost">%s</p><p class="weak">%s</p>' % (info['font'], WEAK2['font']),
         '<p>Specimen, 3x and 1x:</p>', img('font_specimen_3x.png'), img('font_specimen_1x.png'),
         '<p>The fix tile sheet (import file), 1x and 4x. Tile order is in numbers.txt.</p>', img('fix_sheet_1x.png'), img('fix_sheet_1x.png', 512),
         '<h2>Fix 4: Sootling icon</h2>', pair('icon_before_8x.png', 'icon_after_8x.png'), pair('icon_before_1x.png', 'icon_after_1x.png'),
         '<p class="weak">%s</p>' % WEAK2['icon'],
         '<h2>Fix 5: row 27 over the hazard strip</h2>',
         '<p>Bottom 32 lines of the screen, every mood with every hazard kind (frame 0), 2x. Left: draft, unbacked. Right: final, plates.</p>',
         pair('row27_before_2x.png', 'row27_after_2x.png'), pair('row27_before_1x.png', 'row27_after_1x.png'),
         '<p class="cost">%s</p><p class="weak">%s</p>' % (info['hud'], WEAK2['hud']),
         '<h2>Final mock-ups</h2><p class="weak">%s</p>' % WEAK2['mock']]
    for key, name in (('title', 'Title screen'), ('hud1p', 'Match HUD, one player'), ('hud2p', 'Match HUD, two players'),
                      ('results', 'Round results'), ('entry', 'High score name entry')):
        h.append('<h3>%s</h3><div class="row">' % name)
        for m in MOODS:
            h.append(col(MOODNAME[m].capitalize(), img('%s_%s_3x.png' % (key, m)) + img('%s_%s_1x.png' % (key, m))))
        h.append('</div>')
    h.append('<p>Fix layer alone (two players), 1x:</p>' + img('hud_layer_1x.png'))
    h.append('</body></html>')
    with open(os.path.join(HERE, 'index.html'), 'w') as fh:
        fh.write('\n'.join(h) + '\n')


def final_main():
    soot = load_soot()
    num = []
    info = {}

    # ---------------------------------------------------------- logo
    fr = frames()
    body = [idx for idx, _ in fr]
    nbest, ox, oy = best_offset()
    layers = [shifted(b, ox, oy) for b in body]
    u_still, u_body, u_piece = set(), set(), set()
    tiles_idx(layers[STILL_F], u_still)
    for L in layers:
        tiles_idx(L, u_body)
    for _, pcs in fr:
        for t, _, _ in pcs:
            tiles_idx(t, u_piece)
    u0 = set()
    for b in body:
        tiles_idx(shifted(b, 0, 0), u0)
    ext = strip_layout(layers)
    lx0, ly0 = A_X - PADC - ox, A_Y - PADC - oy            # screen position of the layer's top left corner
    most, most_at = 0, None
    for f, (_, pcs) in enumerate(fr):
        for y in range(layers[0].shape[0]):
            n = sum(1 for a, b in ext.values() if a * 16 <= y < (b + 1) * 16)
            n += sum(1 for _, px, py in pcs if py + oy <= y < py + oy + 16)
            if n > most:
                most, most_at = n, (f, y + ly0)
    static_most = max(sum(1 for a, b in ext.values() if a * 16 <= y < (b + 1) * 16) for y in range(layers[0].shape[0]))
    total = len(u_body | u_piece)
    hh = max(b for _, b in ext.values()) * 16 + 16
    ww = max(ext) * 16 + 16
    save('logo_a_still_1x.png', rgb_of(layers[STILL_F][:hh, :ww], GUM2))
    save('logo_a_frames_1x.png', np.concatenate([rgb_of(L[:hh, :ww], GUM2) for L in layers], 0))
    ptiles = []
    for _, pcs in fr:
        for t, _, _ in pcs:
            if not any((t == q).all() or (t[:, ::-1] == q).all() for q in ptiles):
                ptiles.append(t)
    save('logo_a_pieces_1x.png', np.concatenate([rgb_of(t, GUM2) for t in ptiles], 1))

    seps = {}
    for mood in MOODS:
        bg = bg_plain(mood)
        b0 = new(H, W)
        over(b0, logo_a(), A_X, A_Y)
        a0 = new(H, W)
        logo_draw(a0, STILL_F)
        seps[mood] = (edge_sep(b0, bg, (GUMP[1], GUMP[7], GUMP[8])), edge_sep(a0, bg, (GUM2[1], GUM2[7], GUM2[8])))
    bg = bg_plain('dusk')
    b = bg.copy()
    over(b, logo_a(), A_X, A_Y)
    a = bg.copy()
    logo_draw(a, STILL_F)
    for k in (1, 3):
        save('logo_before_dusk_%dx.png' % k, b[:112], k)
        save('logo_after_dusk_%dx.png' % k, a[:112], k)
    strips = []
    for mood in MOODS:
        c = bg_plain(mood)
        logo_draw(c, STILL_F)
        strips.append(c[:108])
    for k in (1, 3):
        save('logo_moods_%dx.png' % k, np.concatenate(strips, 0), k)
    cells_a, cells_b = [], []
    for f in range(10):
        c = bg.copy()
        logo_draw(c, f)
        cells_a.append(c[:160])
        c = bg.copy()
        over(c, logo_a(f), A_X, A_Y)
        cells_b.append(c[:160])
    for nm, cells in (('logo_contact_2x.png', cells_a), ('logo_contact_before_2x.png', cells_b)):
        rows = [np.concatenate(cells[i:i + 2], 1) for i in range(0, 10, 2)]
        save(nm, np.concatenate(rows, 0), 2)
    for mood in MOODS:
        save_gif('anim_title_%s_3x.gif' % mood, [title_final(mood, f, soot)[0] for f in range(10)],
                 [110, 110, 110, 110, 110, 260, 90, 90, 110, 200])

    num += ['LOGO A, stretched gum (sprites, 1 palette, no dither)', '']
    num.append('palette logo (index: RGB, 5-bit steps):')
    names = ['keyline plum', 'gum deep', 'gum mid', 'gum light', 'warm cream highlight', 'specular white', 'under shadow', 'outer line',
             'cool rim light', 'violet rim step']
    for i, c in enumerate(GUM2[1:]):
        num.append('  %2d %-20s %s' % (i + 1, names[i], q5s(c)))
    num.append('colours used: %d of 15' % len(np.unique(np.concatenate([b.ravel() for b in body] + [t.ravel() for t in ptiles]))[1:]))
    num.append('unique 16x16 tiles, flips reused: still (frame %d) %d; body layer over all 10 frames %d; free pieces %d; total %d'
               % (STILL_F, len(u_still), len(u_body), len(u_piece), total))
    num.append('draft round: 79 still, 155 over 10 frames. Grid offset search: %d tiles at offset 0,0 -> %d at offset x %d, y %d (body, flips reused).'
               % (len(u0), len(u_body), ox, oy))
    num.append('sprites: %d strips of 16 px for the body; at most %d of them on one scanline; worst scanline with free pieces: %d (frame %d, screen y %d). '
               'The title also shows two Sootlings (4 strips). Hardware limit 96 per scanline.' % (len(ext), static_most, most, most_at[0], most_at[1]))
    num.append('layer top left on screen: x %d, y %d. Strips (index: screen x, screen y of first tile, tiles tall):' % (lx0, ly0))
    line = []
    for sx in sorted(ext):
        a_, b_ = ext[sx]
        line.append('%d: x %d y %d h %d' % (sx, lx0 + sx * 16, ly0 + a_ * 16, b_ - a_ + 1))
    for i in range(0, len(line), 5):
        num.append('  ' + ' | '.join(line[i:i + 5]))
    num.append('free pieces per frame (screen x, y of the 16x16 tile): ')
    for f, (_, pcs) in enumerate(fr):
        if pcs:
            num.append('  frame %d: ' % f + ' '.join('(%d,%d)' % (A_X - PADC + px, A_Y - PADC + py) for _, px, py in pcs))
    num.append('frame times in the GIF (ms): 110 110 110 110 110 260 90 90 110 200')
    num.append('separation, outermost gum pixels against the sky they cover (RGB distance: mean, 10th percentile, share under 80):')
    for mood in MOODS:
        (m0, p0, s0), (m1, p1, s1) = seps[mood]
        num.append('  %-5s before %5.1f %5.1f %4.1f%%   after %5.1f %5.1f %4.1f%%' % (mood, m0, p0, s0, m1, p1, s1))
    num.append('dark envelope: keyline 1 px + outer line 1 px before; keyline 1 px + outer line 2 px after; under shadow offset 2,3 -> 3,4 and darker.')
    info['logo'] = ('Outer gum pixels against the dusk sky, RGB distance mean %.0f before, %.0f after; share of edge pixels closer than 80: %.0f%% before, %.0f%% after. '
                    'Line 2 px before, 3 px after; 10 colours in one palette.' % (seps['dusk'][0][0], seps['dusk'][1][0], seps['dusk'][0][2], seps['dusk'][1][2]))
    info['anim'] = ('Unique 16x16 tiles: %d still, %d with all frames and pieces (draft: 79 and 155). %d body strips, at most %d sprites on a scanline.'
                    % (len(u_still), total, len(ext), most))

    # ---------------------------------------------------------- font
    save('fix_sheet_1x.png', fix_sheet())
    pb, pa = glyph_pairs(GA), glyph_pairs(GA2)
    dist_b = {(a_, b_): d for d, a_, b_ in pb}
    dist_a = {(a_, b_): d for d, a_, b_ in pa}
    PAIRS = [('O', '0'), ('M', 'W'), ('I', '1'), ('S', '5'), ('B', '8'), ('Z', '2'), ('G', '6'), ('D', 'O'), ('C', 'G'), ('O', 'Q')]

    def dd(tab, a_, b_):
        return tab.get((a_, b_), tab.get((b_, a_)))

    dark = q5((24, 24, 41))
    for tag, font in (('before', None), ('after', TILE)):
        c = np.empty((40, 240, 3), np.uint8)
        c[:] = dark
        c[20:] = bg_match('dusk')[40:60, :240]
        for r in (0, 3):
            for i, (a_, b_) in enumerate(PAIRS[:7]):
                for j, ch in enumerate((a_, b_)):
                    x, y = 4 + i * 24 + j * 8, 4 + r * 8 - (4 if r else 0)
                    if font is None:
                        blit(c, FONT_A[ch], FPAL['white'], x, y)
                    else:
                        blit(c, TILE[('p', ch)], FPAL['white'], x, y)
            x = 4 + 7 * 24
            if font is None:
                blit(c, FONT_A['~'], FPAL['white'], x, 4 + r * 8 - (4 if r else 0))
            else:
                txt(c, 0, 0, '', 'white')
                blit(c, TILE[('p', '~L')], FPAL['white'], x, 4 + r * 8 - (4 if r else 0))
                blit(c, TILE[('p', '~R')], FPAL['white'], x + 8, 4 + r * 8 - (4 if r else 0))
        save('font_pairs_%s_1x.png' % tag, c)
    for tag, tl in (('before', [FONT_A['~']]), ('after', [TILE[('p', '~L')], TILE[('p', '~R')]])):
        c = np.empty((16, 56, 3), np.uint8)
        c[:] = dark
        c[:, 28:] = bg_match('storm')[30:46, 100:128]
        for x0 in (4, 32):
            for j, t in enumerate(tl):
                blit(c, t, FPAL['white'], x0 + j * 8, 4)
        save('icon_%s_1x.png' % tag, c)
        save('icon_%s_8x.png' % tag, c, 8)
    sp = np.empty((38 * 8, W, 3), np.uint8)
    sp[:] = dark
    txt(sp, 1, 1, 'FONT A - GUMDROP - FINAL', 'gold')
    txt(sp, 1, 3, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    txt(sp, 1, 5, "0123456789 . , : ! ? - ' / < > ^ v { } ~")
    txt(sp, 1, 7, 'PLAYER 1', 'pink')
    txt(sp, 11, 7, 'PLAYER 2', 'lime')
    txt(sp, 21, 7, 'HIGH SCORE', 'gold')
    txt(sp, 32, 7, 'CREDITS', 'dim')
    txt(sp, 1, 9, "DON'T POP! WHO'S NEXT? 12/34 <OK>")
    txt(sp, 1, 11, 'O0 MW I1 S5 B8 Z2 G6 9 DOQ UV 7/ 3 4')
    txtall(sp, 1, 13, '0123456789')
    txtall(sp, 13, 13, '004200', 'pink')
    txtall(sp, 21, 13, '001500', 'lime')
    txtall(sp, 29, 13, '052300', 'gold')
    txt(sp, 1, 16, 'BACKED COPIES - PLATE AND PANEL', 'gold')
    txt(sp, 1, 18, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'white', True)
    txt(sp, 1, 19, "0123456789 . , : ! ? - ' / < > ^ v { } ~", 'white', True)
    txt(sp, 1, 21, 'PLAYER 1 ', 'pink', True)
    txt(sp, 10, 21, ' PLAYER 2 ', 'lime', True)
    txt(sp, 20, 21, ' HIGH SCORE ', 'gold', True)
    txt(sp, 32, 21, 'CREDITS', 'dim', True)
    txtall(sp, 1, 23, '0123456789', 'white', True)
    txtall(sp, 13, 23, '004200', 'pink', True)
    r = 26
    for mood in MOODS:
        strip = bg_match(mood)[0:16].copy()
        txt(strip, 1, 0, 'PLAYER 1 004200 }}} HIGH SCORE 052300')
        txt(strip, 1, 1, 'ROUND 3 - %s  ~ CREDITS 2' % MOODNAME[mood], 'pink')
        sp[r * 8:r * 8 + 16] = strip
        strip = bg_match(mood)[208:224].copy()
        txt(strip, 1, 0, ' HIGH SCORE 052300 ', 'gold', True)
        txt(strip, 21, 0, ' ROUND 3  ~ ', 'white', True)
        txt(strip, 1, 1, ' 0O MW 1I 5S 8B 2Z ', 'white', True)
        sp[r * 8 + 16:r * 8 + 32] = strip
        r += 4
    save('font_specimen_1x.png', sp)
    save('font_specimen_3x.png', sp, 3)

    num += ['', 'FONT A, Gumdrop (fix tiles, 8x8, 15 colours + transparent per palette)', '']
    n_plain = sum(1 for k in TILE if k[0] == 'p')
    num.append('tiles: %d plain glyph tiles (26 letters, 10 digits, 12 punctuation and arrows, heart, gum, Sootling icon = 2 tiles) + 20 tall digit tiles '
               '+ %d backed copies of both + %d plate, panel and rule tiles = %d' % (n_plain, sum(1 for k in TILE if k[0] in ('b', 'bt')),
                                                                                   sum(1 for k in TILE if k[0] == 's'), len(TILE)))
    num.append('minimum for HUD row 27 alone: 12 letters (HIGSCOREUNDT) + 10 digits backed + 4 plate tiles = 26 extra tiles instead of 72.')
    num.append('sheet fix_sheet_1x.png: 128 x 96 px, 16 tiles per row, tile index = row * 16 + column, drawn in the white palette, transparent = 255,0,255.')
    num.append('rule: backed copy of a tile = its index + 96 (letters, digits, punctuation, icons, tall digits). Tall digit: top tile at 64 + digit, bottom tile at 80 + digit.')
    num.append('character map (tile index: character):')
    inv = {i: k for k, i in TIDX.items()}
    line = []
    for i in sorted(inv):
        k = inv[i]
        if k[0] in ('b', 'bt'):
            continue
        nm = {'~L': 'Sootling left', '~R': 'Sootling right', '{': 'heart', '}': 'gum bubble', '^': 'arrow up', 'v': 'arrow down'}.get(k[1], k[1]) \
            if k[0] == 'p' else (k[1] if k[0] == 's' else 'tall %s %s' % (k[1], 'top' if k[2] == 0 else 'bottom'))
        line.append('%3d: %s' % (i, nm))
    for i in range(0, len(line), 8):
        num.append('  ' + '   '.join(line[i:i + 8]))
    num.append('  96..147: backed copies of 0..51; 160..169 and 176..185: backed tall digits; 148..159, 75..79, 90..95, 170..175, 186..191 unused.')
    num.append('palette slots: 1..4 face light to deep, 5 shadow, 6..8 heart, 9..11 gum, 12 white, 13 soot navy (also plate and panel fill), 14 soot blue, 15 ember')
    for nm, p in FPAL.items():
        num.append('palette text %-5s: ' % nm + ' '.join('%d,%d,%d' % c for c in p[1:]))
    num.append('  5-bit steps: every channel value above is v5 * 8 + v5 / 4 (integer), v5 = value >> 3; for example white palette: '
               + ' '.join('%d,%d,%d' % (c[0] >> 3, c[1] >> 3, c[2] >> 3) for c in FPAL['white'][1:]))
    num.append('look-alike check, differing pixels between the two 7x7 bitmaps (before -> after):')
    num.append('  ' + '   '.join('%s/%s %d -> %d' % (a_, b_, dd(dist_b, a_, b_), dd(dist_a, a_, b_)) for a_, b_ in PAIRS))
    num.append('  closest pairs after: ' + '  '.join('%s/%s %d' % (a_, b_, d) for d, a_, b_ in pa[:12]))
    num.append('  closest pairs before: ' + '  '.join('%s/%s %d' % (a_, b_, d) for d, a_, b_ in pb[:12]))
    num.append('  there is no lower case, so 1, I and l reduce to 1 and I.')
    info['font'] = ('Differing pixels, before to after: ' + ', '.join('%s/%s %d to %d' % (a_, b_, dd(dist_b, a_, b_), dd(dist_a, a_, b_)) for a_, b_ in PAIRS[:7])
                    + '. Closest pair left: %s/%s with %d. %d fix tiles in all.' % (pa[0][1], pa[0][2], pa[0][0], len(TILE)))

    # ---------------------------------------------------------- HUD row 27
    hz = {k: haz_frames(k) for k in HAZ}
    fx2, fx1 = hud_final(True), hud_final(False)
    o2, o1 = fx2.render(), fx1.render()
    face2, face1 = fx2.face(), fx1.face()
    res_b, res_a = [], []
    before_rows, after_rows = [], []
    for mood in MOODS:
        base = bg_scene(mood)
        ob = hud2(mood, FONT_A)
        fb = draft_face(ob)
        for kind in HAZ:
            for fi in range(16):
                bgz = bg_hazard(base, hz[kind][fi])
                for g, row, colx in cell_gaps(compose(bgz, ob), fb, (27,)):
                    res_b.append((g, mood, kind, fi, row, colx))
                for g, row, colx in cell_gaps(compose(bgz, o2), face2, (27,)):
                    res_a.append((g, mood, kind, fi, row, colx))
                if fi == 0:
                    before_rows.append(compose(bgz, ob)[192:224])
                    after_rows.append(compose(bgz, o2)[192:224])
    gapc = np.zeros((2, 320, 3), np.uint8)
    for nm, rows_ in (('before', before_rows), ('after', after_rows)):
        parts = []
        for r_ in rows_:
            parts += [r_, gapc]
        for k in (1, 2):
            save('row27_%s_%dx.png' % (nm, k), np.concatenate(parts[:-1], 0), k)
    top = []
    for mood in MOODS:
        for nm, bgx in (('islands scene', bg_match(mood)), ('background scene', bg_scene(mood))):
            for tag, o, fc, fxx in (('two players', o2, face2, fx2), ('one player', o1, face1, fx1)):
                for g, row, colx in cell_gaps(compose(bgx, o), fc, (0, 1)):
                    top.append((g, mood, nm, tag, row, colx, fxx.name(colx, row)))
    num += ['', 'HUD layout 2, Corner tags (fix rows 0, 1 and 27 only, no band, no sprites)', '']
    num.append('gap = mean luminance of the glyph face pixels minus the 90th percentile luminance of all other pixels in the same 8x8 cell of the finished picture')
    num.append('(shadow, plate or backdrop). Negative means the backdrop is brighter than the glyph. Luminance = 0.299 R + 0.587 G + 0.114 B, 0..255.')
    num.append('row 27 was measured over 3 moods x 4 hazard kinds (spikes, water, lava, fire from hazards-final) x 16 frames = 192 backdrops.')
    num.append('row 27 worst cell per mood and hazard, before (draft, unbacked) -> after (plates):')
    for mood in MOODS:
        for kind in HAZ:
            wb = min(x for x in res_b if x[1] == mood and x[2] == kind)
            wa = min(x for x in res_a if x[1] == mood and x[2] == kind)
            num.append('  %-5s %-6s before %6.1f (column %2d, frame %2d)   after %6.1f (column %2d, %s)'
                       % (mood, kind, wb[0], wb[5], wb[3], wa[0], wa[5], fx2.name(wa[5], 27)))
    wb, wa = min(res_b), min(res_a)
    num.append('row 27 worst cell overall: before %.1f (%s, %s, frame %d, column %d); after %.1f (%s, %s, frame %d, column %d, %s). Cells under 70: before %d of %d, after %d of %d.'
               % (wb[0], wb[1], wb[2], wb[3], wb[5], wa[0], wa[1], wa[2], wa[3], wa[5], fx2.name(wa[5], 27),
                  sum(x[0] < 70 for x in res_b), len(res_b), sum(x[0] < 70 for x in res_a), len(res_a)))
    num.append('rows 0 and 1 stay unbacked (sky open). Worst cell per mood (dim PLAYER 2 label left out):')
    for mood in MOODS:
        w = min(x for x in top if x[1] == mood)
        num.append('  %-5s %6.1f  row %d column %2d, %s, %s, %s' % (mood, w[0], w[4], w[5], w[6], w[2], w[3]))
    wt = min(top)
    num.append('rows 0 and 1 cells under 70 per mood: ' + ', '.join('%s %d' % (m, sum(x[0] < 70 for x in top if x[1] == m)) for m in MOODS))
    num.append('rows 0 and 1 cells under 70: %d of %d' % (sum(x[0] < 70 for x in top), len(top)))
    num.append('fix cells drawn: two players %d, one player %d; unique tiles used by the two player HUD: %d' % (len(fx2.c), len(fx1.c), len({k for k, _ in fx2.c.values()})))
    info['hud'] = ('Worst row 27 cell over 192 backdrops: %.0f before (%s, %s), %.0f after (%s, %s, %s). Worst unbacked cell on rows 0 and 1: %.0f (%s, %s); %d of %d such cells are under 70.'
                   % (wb[0], wb[1], wb[2], wa[0], wa[1], wa[2], fx2.name(wa[5], 27), wt[0], wt[1], wt[6], sum(x[0] < 70 for x in top), len(top)))

    # ---------------------------------------------------------- mock-ups
    save('hud_layer_1x.png', o2)
    fr_, fe_ = results_final(), entry_final()
    used = set()
    for mood in MOODS:
        t, fxt = title_final(mood, None, soot)
        shots = {'title': t, 'hud1p': compose(bg_match(mood), o1), 'hud2p': compose(bg_match(mood), o2),
                 'results': compose(bg_match(mood), fr_.render()), 'entry': compose(bg_plain(mood), fe_.render())}
        for key, im in shots.items():
            save('%s_%s_1x.png' % (key, mood), im)
            save('%s_%s_3x.png' % (key, mood), im, 3)
        used |= {k for k, _ in fxt.c.values()}
    for fq in (fx1, fx2, fr_, fe_):
        used |= {k for k, _ in fq.c.values()}
    num += ['', 'MOCK-UPS', '']
    num.append('every screen is built as a 40x28 grid with one tile and one palette per cell; %d of the %d tiles are used by the five screens.' % (len(used), len(TILE)))
    num.append('fix cells: title %d, results %d, name entry %d.' % (len(title_final('moon', None, soot)[1].c), len(fr_.c), len(fe_.c)))
    num.append('title sprites: logo body %d strips + up to 7 free pieces + 2 Sootlings (4 strips).' % len(ext))
    num.append('score values on the results screen are placeholders (the design fixes "points for stomps and wins", no values).')
    num.append('fix layer facts used: 8x8 tiles, 40x28 visible cells, 15 colours + transparent per palette, in front of all sprites, no flip, no scaling, no scroll.')
    with open(os.path.join(HERE, 'numbers.txt'), 'w') as fh:
        fh.write('\n'.join(num) + '\n')
    write_index2(info)
    print('\n'.join(num))


if __name__ == '__main__':
    final_main()
