#!/usr/bin/env python3
# Bubblegum Brawl dither test: six pixel-artist dithering styles on the SAME hazards v4 art (C water, D lava, A spikes)
# and on the night sky of the draft scene. Fire is left out on purpose (owned elsewhere).
#
# How it works: hazards_v4_base.py (an unchanged copy of draw_hazards_v4.py) renders the v4 index frames. Shapes,
# physics, animation and palettes stay as they are. This script only redraws the TRANSITION between two neighbouring
# shades of one material ramp. For each such pair it measures, per pixel, the distance to the boundary between the
# two shades (so the dither zone follows the form the v4 cel bands already follow) and lets the chosen style decide
# which of the two shades the pixel gets. Nothing else changes: no new colours, outlines, rim lights and
# non-neighbouring shade steps stay hard.
#
# Anchoring: all patterns have a period that divides 16 and are anchored to the 16 px tile grid (water, melt, crust,
# sky, sleeves, rail), so a pattern pixel never slides; only the zone it shows through moves. The spike blades and
# shafts move in y, so their pattern is anchored to the piston tip (y - tip row): the dither travels with the blade.
#
# Deterministic, no network. Run: /opt/homebrew/bin/python3.14 -I draw_dither_variants.py   (needs Pillow + numpy)
#   --check DIR   writes only the comparison sheets into DIR (inspection, nothing written here)
import os
import sys
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
from PIL import Image, ImageDraw
import hazards_v4_base as v4

NF, H = v4.NF, v4.H
STYLES = [
    (0, 'Reference', 'Hazards v4, no dither', 'Clean cel bands, best tile reuse.', 'Reads flat next to 16-bit era art.'),
    (1, 'Sparse transition', 'Broken one to two pixel edge where two shades meet',
     'Keeps sprites crisp, cheapest in tiles, closest to Capcom and SNK sprite work.', 'Too quiet to soften large areas such as the sky.'),
    (2, 'Checker blend bands', 'Half and half checker zone between neighbouring shades',
     'Blends to a new in-between shade on a CRT; strong on glow and liquid.', 'On a sharp screen the checker reads as a texture, heavy on small steel parts.'),
    (3, 'Graded pattern', 'Quarter, half and three quarter ordered steps',
     'Smoothest gradient; best on sky and other large calm surfaces.', 'Regular dot grid looks mechanical on small shapes and costs the most tiles.'),
    (4, 'Clustered by material', 'Hand cluster maps: ripple dashes, melt blobs, crust stipple, brushed steel',
     'Dither doubles as surface texture, least regular look.', 'Busiest style; texture can fight the animation on fast water.'),
    (5, 'Line and hatch', 'Horizontal lines on sky, water and melt, diagonal hatch on steel and crust',
     'Reads as scanline haze and brushed metal, calm in motion.', 'Horizontal lines fight curved wave shapes; hatch on steel looks drawn.'),
    (6, 'Mixed by material', 'Sparse on steel, crust and rock; ripple dashes on water; checker on melt; graded on sky',
     'Each material gets the style that suits it, as a production artist would combine them.', 'Needs a short rule sheet so all later art stays consistent.'),
]

# ---------------------------------------------------------------- materials: (kind, ramp dark -> light) per hazard
MATS = {
    'C': [('water', 'onubBTc'), ('foam', 'cf'), ('rock', 'pPq')],
    'D': [('melt', 'mPDrOyY'), ('crust', 'okKQH')],
    'A': [('steel', 'Ddmlh')],
}
PALS = {'A': v4.PA, 'C': v4.PC, 'D': v4.PD}
NAMES = {'A': 'spikes', 'C': 'water', 'D': 'lava', 'sky': 'sky'}
MIX = {'sky': 3, 'water': 4, 'foam': 0, 'rock': 1, 'melt': 2, 'crust': 1, 'steel': 1}    # style 6
BIG = ('water', 'melt', 'sky')
WK2 = {'sky': 3}                         # style 2: checker half width in px (default 2 on big kinds, 1 on small)
ST3 = {'sky': 3}                         # style 3: rows per step (default 1)
WZ = {'sky': 6, 'water': 2.5, 'melt': 2.5}    # styles 4, 5: half width of the tone zone (default 1.5)


def rank(a):
    """Turn any 16x16 score map into evenly spread thresholds in (0, 1)."""
    o = np.argsort(a.ravel(), kind='stable')
    r = np.empty(a.size)
    r[o] = (np.arange(a.size) + 0.5) / a.size
    return r.reshape(a.shape)


def blobs(centres, sx=1.0):
    """Hand-placed cluster centres on a 16x16 torus: threshold rises with the distance to the nearest centre."""
    y, x = np.mgrid[0:16, 0:16]
    d = np.full((16, 16), 99.0)
    for i, (cx, cy) in enumerate(centres):
        dx = (x - cx + 8) % 16 - 8
        dy = (y - cy + 8) % 16 - 8
        d = np.minimum(d, np.hypot(dx / sx, dy) + 0.13 * (i % 3))
    return rank(d)


def _maps():
    y, x = np.mgrid[0:16, 0:16]
    bay = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]])
    m = {'bayer': (np.tile(bay, (4, 4)) + 0.5) / 16}
    # ripple dashes: every row is a train of short dashes, rows staggered by hand so no column lines up
    dash = np.array([0.0, 0.0, 0.25, 0.6, 1.0, 1.0, 0.7, 0.3])
    off = np.array([0, 5, 2, 7, 3, 6, 1, 4, 6, 2, 5, 0, 7, 3, 4, 1])
    rowr = np.array([0.1, 0.7, 0.4, 0.9, 0.25, 0.8, 0.5, 0.0, 0.65, 0.3, 0.95, 0.15, 0.55, 0.85, 0.2, 0.45])
    m['water'] = rank(0.55 * rowr[y] + 0.45 * dash[(x + off[y]) % 8])
    m['foam'] = m['water']
    m['sky'] = blobs([(3, 2), (11, 5), (6, 9), (14, 12), (1, 14), (9, 15)], sx=2.4)       # long soft streaks
    m['melt'] = blobs([(2, 3), (10, 1), (6, 8), (13, 6), (1, 11), (9, 13), (14, 12), (5, 14)])   # molten blobs
    stip = [(1, 1), (5, 0), (9, 2), (13, 1), (3, 4), (7, 5), (11, 4), (15, 6), (0, 8), (4, 9), (8, 8), (12, 10),
            (2, 12), (6, 13), (10, 12), (14, 14)]
    m['crust'] = blobs(stip)                                                                # grit stipple
    m['rock'] = m['crust']
    col = np.array([0.2, 0.8, 0.45, 0.95, 0.1, 0.7, 0.35, 0.6])
    m['steel'] = rank(col[x % 8] + np.array([0.0, 0.3, 0.1, 0.2])[y % 4])                   # brushed, vertical grain
    ln = np.array([0.125, 0.625, 0.375, 0.875])
    m['hline'] = ln[y % 4] + 0 * x
    m['diag'] = ln[(x + y) % 4]
    m['anti'] = ln[(x - y) % 4]
    brk = ['###.##..####.#.#', '##.###.#..###.##', '.####..###.#.###', '###..###.####..#', '#.###.##..##.###', '##..####.###.#.#',
           '.###.#.###..####', '###.###..#.###.#', '#..###.####.##.#', '##.#.###..###.##', '####..#.###.#.##', '.##.###.##..####',
           '###.#..####.##.#', '#.###.##.#.###.#', '##.##.###..#.###', '.###..#.####.###']
    m['brk'] = np.array([[c == '#' for c in r] for r in brk])
    return m


MAP = _maps()
LINE = {'sky': 'hline', 'water': 'hline', 'foam': 'hline', 'melt': 'hline', 'steel': 'diag', 'crust': 'anti', 'rock': 'anti'}


def decide(style, kind, s, X, Y):
    """True where the pixel takes the LIGHT shade of the pair. s = signed distance to the pair boundary in px
    (+ on the light side, half-integer steps). X, Y = pattern coordinates (tile grid or shape anchored)."""
    if style == 6:
        style = MIX[kind]
    side = s > 0
    if style == 0:
        return side
    d = np.ceil(np.abs(s)).astype(int)
    big = kind in BIG
    xm, ym = X % 16, Y % 16
    chk = (X + Y) % 2 == 0
    if style == 1:
        r = side | (~side & (d == 1) & chk & MAP['brk'][ym, xm])
        if big:
            r |= ~side & (d == 2) & ((X + Y) % 4 == 1) & (Y % 2 == 0) & MAP['brk'][(ym + 5) % 16, (xm + 3) % 16]
        return r
    if style == 2:
        return np.where(d <= WK2.get(kind, 2 if big else 1), chk, side)
    if style == 3:
        st = ST3.get(kind, 1)
        lev = np.where(side, np.where(d <= st, 0.75, 1.0), np.where(d <= st, 0.5, np.where(d <= 2 * st, 0.25, 0.0)))
        return lev > MAP['bayer'][ym, xm]
    wz = WZ.get(kind, 1.5) + (1.0 if style == 4 and kind in ('water', 'melt') else 0.0)   # cluster maps need room to read
    t = np.clip(0.5 + s / (2 * wz), 0, 1)
    T = MAP[kind if style == 4 else LINE[kind]][ym, xm]
    return np.where(np.abs(s) <= wz, t > T, side)


# ---------------------------------------------------------------- index frames
def dist(mask, maxd=7):
    """City-block distance to the mask (x wraps, y does not), capped at maxd + 1."""
    d = np.full(mask.shape, maxd + 1, int)
    cur = mask.copy()
    d[cur] = 0
    for k in range(1, maxd + 1):
        up = np.zeros_like(cur)
        up[1:] = cur[:-1]
        dn = np.zeros_like(cur)
        dn[:-1] = cur[1:]
        nxt = cur | np.roll(cur, 1, 1) | np.roll(cur, -1, 1) | up | dn
        d[nxt & ~cur] = k
        cur = nxt
    return d


def thick(m):
    """Largest inner depth of the region within 2 px: small shapes (caustics, glints, cracks) are left alone."""
    ds = dist(~m)
    p = np.vstack([ds[:1], ds[:1], ds, ds[-1:], ds[-1:]])
    return np.max([np.roll(p[dy:dy + m.shape[0]], dx, 1) for dy in range(5) for dx in range(-2, 3)], axis=0)


def dither(idx, key, style, Y=None):
    if style == 0:
        return idx.copy()
    pal = PALS[key]
    h, w = idx.shape
    yy, X = np.mgrid[0:h, 0:w]
    if Y is None:
        Y = yy
    out = idx.copy()
    best = np.full(idx.shape, 99.0)
    for kind, ramp in MATS[key]:
        for ka, kb in zip(ramp, ramp[1:]):
            ia, ib = pal[ka], pal[kb]
            A, B = idx == ia, idx == ib
            if not A.any() or not B.any():
                continue
            d = np.where(B, dist(A), dist(B))
            s = np.where(B, d - 0.5, -(d - 0.5))
            th = np.where(B, thick(B), thick(A))
            ok = (A | B) & (d <= 7) & (dist(~(A | B)) >= 2 * d) & (th >= 2) & (d <= np.maximum(1, th - 1))
            new = np.where(decide(style, kind, s, X, Y), ib, ia)
            ch = ok & (new != idx) & (np.abs(s) < best)
            out[ch] = new[ch]
            best[ch] = np.abs(s)[ch]
    return out


def spike_y(f, w):
    """Pattern y for the spikes: rows above the sleeve ride with the piston tip of their 16 px column."""
    ext, _ = v4.sim_piston()
    yy, xx = np.mgrid[0:H, 0:w]
    ty = np.array([max(0, int(round(8 - 6 * ext[(f - 4 * i) % NF]))) for i in range(4)])
    return np.where(yy < v4.SLEEVE_Y, yy - ty[(xx // 16) % 4], yy)


# ---------------------------------------------------------------- sky (scene backdrop, RGB, three flat bands in v4)
SKYC = [(8, 10, 28), (12, 16, 44), (20, 26, 66)]         # top, middle, low: existing scene colours only
SKY_Y = [60, 120]
# hand-set lift of each band edge, one value per 16 px column (haze banks, not a ruler line)
SKY_OFF = [[0, 1, 3, 4, 2, 0, -2, -3, -1, 1, 2, 0, -1, -3, -4, -2, 0, 2, 3, 1, 0],
           [2, 0, -2, -3, -1, 1, 3, 2, 0, -1, -3, -2, 0, 2, 4, 3, 1, -1, -2, 0, 1]]


def dither_sky(base, style):
    if style == 0:
        return base.copy()
    a = np.array(base.convert('RGB'))
    sky = np.zeros(a.shape[:2], bool)
    for c in SKYC:
        sky |= (a == np.array(c, np.uint8)).all(-1)
    Y, X = np.mgrid[0:224, 0:320]
    best = np.full(sky.shape, 1e9)
    out = a.copy()
    for k, yb in enumerate(SKY_Y):
        off = np.round(np.interp(np.arange(320), np.arange(21) * 16, SKY_OFF[k])).astype(int)
        s = (Y + 0.5) - (yb + off[None, :])
        light = decide(style, 'sky', s, X, Y)
        m = sky & (np.abs(s) < best)
        out[m] = np.where(light[m][:, None], np.array(SKYC[k + 1], np.uint8), np.array(SKYC[k], np.uint8))
        best[m] = np.abs(s)[m]
    return Image.fromarray(out, 'RGB').convert('RGBA')


# ---------------------------------------------------------------- output
CROP = (64, 112, 192, 224)        # GIF window, 128 x 112 px: tile B + tile A, sky edge at y 120 in view
CELL = (64, 160, 214, 224)        # comparison cell, 150 x 64 px
SKYCELL = (0, 44, 150, 140)
PAGE = (20, 22, 28)


def label(d, xy, text, fill=(216, 220, 230)):
    d.text(xy, text, fill=fill)


def sheet(cells, cut, path, title):
    """2 columns x 4 rows at 3x: reference + six styles, last cell = all seven at 1x (cabinet size)."""
    cw, ch = (cut[2] - cut[0]), (cut[3] - cut[1])
    W3, H3 = cw * 3, ch * 3
    im = Image.new('RGB', (2 * W3 + 24, 4 * (H3 + 22) + 8), PAGE)
    d = ImageDraw.Draw(im)
    for i, (st, c) in enumerate(cells):
        x, y = 8 + (i % 2) * (W3 + 8), 4 + (i // 2) * (H3 + 22)
        label(d, (x, y + 2), ('Style %d: %s' % (st[0], st[1])) if st[0] else 'Reference: hazards v4, no dither')
        im.paste(c.crop(cut).convert('RGB').resize((W3, H3), Image.NEAREST), (x, y + 16))
    x, y = 8 + W3 + 8, 4 + 3 * (H3 + 22)
    label(d, (x, y + 2), '%s at 1x, real cabinet size: reference, then styles 1 to 6' % title)
    n = W3 // (cw // 2 + 4)
    for i, (st, c) in enumerate(cells):
        half = c.crop((cut[0], cut[1], cut[0] + cw // 2, cut[3])).convert('RGB')
        im.paste(half, (x + (i % n) * (cw // 2 + 4), y + 16 + (i // n) * (ch + 4)))
    im.save(path)


def main():
    check = sys.argv[sys.argv.index('--check') + 1] if '--check' in sys.argv else None
    out = check or HERE
    base0 = v4.base_scene()
    masks = v4.light_masks(base0)
    base_cols = set(map(tuple, np.array(base0.convert('RGB')).reshape(-1, 3).tolist()))
    bases = {}
    for st in STYLES:
        bases[st[0]] = dither_sky(base0, st[0])
        assert set(map(tuple, np.array(bases[st[0]].convert('RGB')).reshape(-1, 3).tolist())) <= base_cols, 'sky adds colours'
    sheet([(st, bases[st[0]]) for st in STYLES], SKYCELL, os.path.join(out, 'compare_sky_3x.png'), 'Sky')
    counts = {}
    for key, name, pal, fn in v4.HAZ:
        if key not in MATS:
            continue
        frames0, extra = fn()
        assert v4.W == 64 and len(frames0) == NF
        tw = frames0[0].shape[1]
        used0 = set(np.unique(np.array(frames0)).tolist())
        lev = v4.light_levels(key, pal, frames0) if key in v4.LIGHT_W else None       # scene light stays the v4 light
        ys = [spike_y(f, tw) if key == 'A' else None for f in range(NF)]
        cells = []
        for st in STYLES:
            S = st[0]
            frames = [dither(frames0[f], key, S, ys[f]) for f in range(NF)]
            # no new colours, still at most 15 per palette
            assert set(np.unique(np.array(frames)).tolist()) <= used0 and len(pal.keys) <= 15, (key, S)
            # dither never touches transparency or the silhouette
            assert all(((a == 0) == (b == 0)).all() for a, b in zip(frames, frames0)), (key, S)
            # seamless in x: the tile dithered alone equals the tile dithered inside a doubled strip (wrap + pattern period)
            for f in (0, 5, 11):
                dbl = dither(np.hstack([frames0[f]] * 2), key, S, None if ys[f] is None else np.hstack([ys[f]] * 2))
                assert (dbl[:, :tw] == frames[f]).all() and (dbl[:, tw:] == frames[f]).all(), (key, S, f)
            if key != 'A':   # grid anchored: shifting the art by one tile shifts the result by one tile
                assert (dither(np.roll(frames0[3], 16, 1), key, S) == np.roll(frames[3], 16, 1)).all(), (key, S)
            # seamless in time: each frame depends on its own v4 frame only, and the wrap step is an ordinary step
            df = [int((frames[i] != frames[(i + 1) % NF]).sum()) for i in range(NF)]
            assert df[-1] <= 1.25 * max(df[:-1]) + 8, (key, S, df)
            tc = v4.tile_count(frames)
            counts[(key, S)] = tc
            sc = [v4.scene_frame(bases[S], key, pal, frames, extra, f, masks, lev) for f in range(NF)]
            cells.append((st, sc[2]))
            print('%s %-6s style %d %-22s unique tiles %4d (v4 %4d, %+5.1f%%)  changed px per step: wrap %d, others %d-%d'
                  % (key, name, S, st[1], tc, counts[(key, 0)], 100.0 * (tc - counts[(key, 0)]) / counts[(key, 0)], df[-1], min(df[:-1]), max(df[:-1])))
            if check:
                continue
            nv = tw // 64
            strip = Image.new('RGBA', (64 * NF, H * nv), (0, 0, 0, 0))
            for f in range(NF):
                ti = pal.img(frames[f])
                for vv in range(nv):
                    strip.alpha_composite(ti.crop((vv * 64, 0, vv * 64 + 64, H)), (f * 64, vv * H))
            strip.save(os.path.join(HERE, 'frames_S%d_%s_1x.png' % (S, key)))
            sc[2].convert('RGB').resize((960, 672), Image.NEAREST).save(os.path.join(HERE, 'scene_S%d_%s_3x.png' % (S, key)))
            crop = [s.crop(CROP).resize(((CROP[2] - CROP[0]) * 4, (CROP[3] - CROP[1]) * 4), Image.NEAREST) for s in sc]
            v4.save_gif(os.path.join(HERE, 'anim_S%d_%s_4x.gif' % (S, key)), crop, int(round(v4.VFRAMES[key] * 1000 / 60 / 10)) * 10)
        sheet(cells, CELL, os.path.join(out, 'compare_%s_3x.png' % key), name.capitalize())
    if not check:
        write_html(counts)


def write_html(counts):
    def figs(key):
        o = []
        for st in STYLES:
            S = st[0]
            head = 'Reference: hazards v4' if S == 0 else 'Style %d: %s' % (S, st[1])
            tc = counts[(key, S)]
            tiles = '%d unique tiles' % tc if S == 0 else '%d unique tiles (%+.0f percent against v4)' % (tc, 100.0 * (tc - counts[(key, 0)]) / counts[(key, 0)])
            o.append('<figure><figcaption><strong>%s</strong><span>%s. %s</span></figcaption>'
                     '<img src="anim_S%d_%s_4x.gif" width="512" height="448" alt="%s %s">'
                     '<p class="pro">Strength: %s</p><p class="con">Weakness: %s</p>'
                     '<p class="more"><a href="scene_S%d_%s_3x.png">Full screen at 3x</a> &middot; <a href="frames_S%d_%s_1x.png">Frame strip at 1x</a></p></figure>'
                     % (head, st[2], tiles, S, key, NAMES[key], st[1], st[3], st[4], S, key, S, key))
        return '\n'.join(o)
    sec = []
    for key, intro in (('C', 'Seven water shades from abyss to cyan skin, plus rocks. Patterns stay fixed to the tile grid while the waves pass through them.'),
                       ('D', 'Seven melt shades and five crust shades. Melt patterns are fixed to the tile grid; the scene light on the buildings is the v4 light.'),
                       ('A', 'Five steel shades between outline and rim light. On the blades and shafts the pattern rides with the piston, so it does not flicker when a spike thrusts.')):
        sec.append('<h2>%s</h2>\n<p>%s</p>\n<img class="sheet" src="compare_%s_3x.png" alt="%s comparison sheet">\n<div class="row">\n%s\n</div>'
                   % (NAMES[key].capitalize(), intro, key, NAMES[key], figs(key)))
    html = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Dither variants on hazards v4</title>
<style>
  body { margin: 0; padding: 28px 32px 60px; background: #14161c; color: #d8dce6;
         font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; font-size: 15px; line-height: 1.5; }
  h1 { font-size: 26px; font-weight: 700; margin: 0 0 6px; color: #ffffff; }
  h2 { font-size: 20px; font-weight: 700; margin: 44px 0 4px; color: #ffffff; border-top: 2px solid #2e3340; padding-top: 22px; }
  p { margin: 4px 0 14px; max-width: 1100px; }
  .note { color: #9aa2b4; }
  .row { display: flex; flex-wrap: wrap; gap: 20px 16px; margin-top: 18px; }
  figure { margin: 0; width: 512px; }
  figcaption { min-height: 66px; margin-bottom: 6px; }
  figcaption strong { display: block; font-size: 15px; color: #8fd0ff; }
  figcaption span { display: block; font-size: 13px; color: #b9c0cf; }
  img { image-rendering: pixelated; display: block; background: #0a0c22; border: 1px solid #2e3340; }
  img.sheet { max-width: none; margin-top: 10px; }
  .pro, .con, .more { font-size: 13px; margin: 6px 0 0; }
  .pro { color: #a9e5b4; } .con { color: #f0b9a4; }
  a { color: #8fd0ff; }
</style>
</head>
<body>
<h1>Dither variants on hazards v4</h1>
<p class="note">Same art, same animation, same palettes as hazards v4. Only the transition between neighbouring shades is redrawn, six ways.
No style adds a colour. Every image is shown at a whole-number scale; keep the browser zoom at 100 percent, or the dither will blur.
Each comparison sheet shows the reference and the six styles at 3x, and all seven at 1x (real cabinet size) in the last cell.</p>

<h2>Sky and city backdrop</h2>
<p>The v4 scene sky is three flat bands. Each style redraws the two band edges; the edges are lifted by hand into uneven haze banks, so the dither does not sit on a ruler line.</p>
<img class="sheet" src="compare_sky_3x.png" alt="sky comparison sheet">

%s
</body>
</html>
''' % '\n\n'.join(sec)
    with open(os.path.join(HERE, 'index.html'), 'w') as fh:
        fh.write(html)


if __name__ == '__main__':
    main()
