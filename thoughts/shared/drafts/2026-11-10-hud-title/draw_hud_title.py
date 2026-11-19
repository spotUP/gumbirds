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


if __name__ == '__main__':
    main()
