#!/usr/bin/env python3
# Bubblegum Brawl, final hazard art set (draft; the input for the ROM build). Applies the decisions of 2026-11-10:
#   spikes  hazards v4, NO dither, unchanged (asserted pixel-identical to the v4 sheet)
#   water   palette V2 (pair step about 42), dither on the FULL band, pattern = checker thinned along ripple dashes
#   lava    palette V1 (pair step about 31), half band, crust anchored to the grid, cast light fade kept
#   fire    v6 shapes and motion; three cool flame shades re-spaced so every neighbouring pair is 31 to 35 apart;
#           checker dither between the flame bands (never on the white core); two clean-ups (remnants, white islands)
# Libraries in this directory are unchanged copies of earlier drafts (hazards_v4_base, dither_round1,
# draw_dither_s6_strong, dither_visible_base = draw_dither_visible.py); fire_v6_base = draw_fire_v6.py plus one hook.
# Run: /opt/homebrew/bin/python3.14 -I draw_hazards_final.py        (about 2 minutes; needs Pillow + numpy)
#   --scratch DIR   also writes 1x / 4x inspection crops into DIR
import os
import sys
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
from PIL import Image
import dither_visible_base as dv
import fire_v6_base as fb
v4, r1, s6 = dv.v4, dv.r1, dv.s6

NF, H = v4.NF, v4.H
MIN_STEP = dv.MIN_STEP
STILL = 2
V4DIR = os.path.join(HERE, '..', '2026-11-10-hazards-v4')
V6DIR = os.path.join(HERE, '..', '2026-11-10-hazards-v6-fire')
VIEW = (0, 136, 320, 224)         # scene crop and GIF window: full width, 56 px of scene above the strip
CELL = (72, 152, 184, 224)        # comparison cell, 112 x 72 px (three cells at 4x stay under 1400 px)

# ---------------------------------------------------------------- decisions
WATER_LEVEL, LAVA_LEVEL = 'V2', 'V1'
WATER_PATTERN = os.environ.get('HZF_WATER', 'chk')     # chk = 1 px checker thinned along the ripple dashes; brick = 2 x 1
FIRE_EXT = os.environ.get('HZF_FIRE', 'H')             # H = full band, M = half band
# fire: M, D, r re-spaced (v6: M 40, D 59, r 97 in luminance -> steps 19, 39, 53). O, y, Y, w are the v6 colours.
PB = dv.repal(fb.PB, M=(120, 12, 70), D=(196, 32, 44), r=(240, 70, 36))
FIRE_MATS = [('flame', 'MDrOyY')]                      # w (white core) is not in the ramp: it is never dithered
FLAME_ROWS = 25                                        # rows 0..24 are flame; the coal bed below stays hard


def class_map(score, cls):
    """Threshold map: at 50 percent exactly the pattern `cls`; thinner or denser in the order of `score`."""
    T = np.empty((16, 16))
    for c, lo in ((True, 0.0), (False, 0.5)):
        m = cls == c
        v = score[m]
        o = np.argsort(v, kind='stable')
        r = np.empty(len(v))
        r[o] = (np.arange(len(v)) + 0.5) / len(v)
        T[m] = lo + 0.5 * r
    return T


def water_map(style):
    y, x = np.mgrid[0:16, 0:16]
    sc = r1.MAP['water']                               # ripple dash order of the earlier rounds
    if style == 'brick':
        cell = (sc + np.roll(sc, -1, 1))[:, 0::2].repeat(2, axis=1) / 2.0     # one score per 2 x 1 cell: dashes stay whole
        return class_map(cell + 1e-4 * (x // 2 + 16 * y), (x // 2 + y) % 2 == 0)
    return class_map(sc, (x + y) % 2 == 0)


WATER_OLD = s6.TM['water']
dv.EXT['flame'] = FIRE_EXT
s6.TM['flame'] = s6.TM['melt']                         # checker, thinned in molten blobs


# ---------------------------------------------------------------- fire clean-up (runs inside render_fire, before coal and embers)
FIX_LOG = []
FLAME_HARD = {}


def comps(m):
    """8-connected components, x wraps."""
    h, w = m.shape
    seen = np.zeros_like(m)
    out = []
    for y0 in range(h):
        for x0 in range(w):
            if m[y0, x0] and not seen[y0, x0]:
                st, c = [(y0, x0)], []
                seen[y0, x0] = True
                while st:
                    a, b = st.pop()
                    c.append((a, b))
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            yy, xx = a + dy, (b + dx) % w
                            if 0 <= yy < h and m[yy, xx] and not seen[yy, xx]:
                                seen[yy, xx] = True
                                st.append((yy, xx))
                out.append(c)
    return out


def flame_fix(idx, f):
    out = idx.copy()
    for c in comps(out[:27] != 0):                     # 1: pinched-off remnants of 1 or 2 px are removed
        if len(c) <= 2:
            for p in c:
                out[p] = 0
            FIX_LOG.append('f%02d remnant removed, %d px at x %d y %d (tile %s)' % (f, len(c), c[0][1], c[0][0], 'AB'[c[0][1] // 64]))
    for c in comps(out[:27] == PB['w']):               # 2: a white core that floats free of the bed becomes yellow
        ys, xs = [p[0] for p in c], [p[1] for p in c]
        if max(ys) < 25:
            for p in c:
                out[p] = PB['Y']
            FIX_LOG.append('f%02d white island -> yellow, %d px at x %d..%d y %d..%d' % (f, len(c), min(xs), max(xs), min(ys), max(ys)))
    FLAME_HARD[f] = out.copy()
    return out


# ---------------------------------------------------------------- helpers
def strip(pal, frames):
    """Build input: 16 frames per row, one row per 64 px tile variant (row 0 = A, row 1 = B)."""
    nv = frames[0].shape[1] // 64
    im = Image.new('RGBA', (64 * NF, H * nv), (0, 0, 0, 0))
    for f in range(NF):
        ti = pal.img(frames[f])
        for v in range(nv):
            im.alpha_composite(ti.crop((v * 64, 0, v * 64 + 64, H)), (f * 64, v * H))
    return im


def unstrip(path, pal):
    """Index frames of a finished sheet (colours must all be in pal)."""
    a = np.array(Image.open(path).convert('RGBA'))
    look = {tuple(pal.lut[i]): i for i in range(1, len(pal.keys) + 1)}
    idx = np.zeros(a.shape[:2], np.uint8)
    for col in {tuple(c) for c in a.reshape(-1, 4).tolist()}:
        if col[3]:
            idx[(a == np.array(col, np.uint8)).all(-1)] = look[col]
    nv = a.shape[0] // H
    return [np.concatenate([idx[r * H:(r + 1) * H, f * 64:(f + 1) * 64] for r in range(nv)], axis=1) for f in range(NF)]


def stats(pal, hard, dith):
    return dv.pair_stats([(pal.lut[a][..., :3].astype(float), pal.lut[b][..., :3].astype(float)) for a, b in zip(hard, dith)])


def ncol(frames):
    return len(set(np.unique(np.array(frames)).tolist()) - {0})


def palette_line(pal, frames):
    used = set(np.unique(np.array(frames)).tolist()) - {0}
    return ' '.join('%s%s(%d,%d,%d)' % (k, '' if pal[k] in used else '*', *pal.d[k]) for k in pal.keys)


def outputs(name, key, sc, hard_sc, rep, zoom=False):
    sc[STILL].crop(VIEW).convert('RGB').resize((1280, (VIEW[3] - VIEW[1]) * 4), Image.NEAREST).save(os.path.join(HERE, 'scene_%s_4x.png' % name))
    v4.save_gif(os.path.join(HERE, 'anim_%s_4x.gif' % name), [dv.up(s, VIEW, 4) for s in sc], int(round(v4.VFRAMES[key] * 1000 / 60 / 10)) * 10)
    if zoom:
        d2 = (dv.rgb(sc[STILL]) != dv.rgb(hard_sc)).any(-1)
        x0, y0 = dv.zoom_window(d2, [v4.HAZ_Y])
        dv.up(sc[STILL], (x0, y0, x0 + 48, y0 + 32), 8).save(os.path.join(HERE, 'zoom_%s_8x.png' % name))
        rep.append('%-6s zoom window x %d y %d (frame %d)' % (name, x0, y0, STILL))


def main():
    scratch = sys.argv[sys.argv.index('--scratch') + 1] if '--scratch' in sys.argv else None
    rep, pals = [], {}
    base = v4.base_scene()
    masks = v4.light_masks(base)
    haz = {k: (n, p, fn) for k, n, p, fn in v4.HAZ}

    def line(name, pal, hard, dith, extra=''):
        n, med, p10 = stats(pal, hard, dith)
        opaque = int(sum((a != 0).sum() for a in hard))
        tw = hard[0].shape[1]
        rep.append('%-6s colours %2d of 15  tiles raw %3d unique %3d  dither px %5d (%4.1f%% of opaque)  pair step median %5.1f  p10 %5.1f%s'
                   % (name, ncol(dith), NF * (tw // 16) * (H // 16), v4.tile_count(dith), n, 100.0 * n / opaque, med, p10, extra))
        pals[name] = palette_line(pal, dith)
        assert len(pal.keys) <= 15 and all(((a == 0) == (b == 0)).all() for a, b in zip(hard, dith)), name
        return n, p10

    def shots(name, sc):
        if scratch:
            sc[STILL].crop((0, 176, 320, 224)).convert('RGB').save(os.path.join(scratch, '%s_1x.png' % name))
            dv.up(sc[STILL], (64, 176, 224, 224), 4).save(os.path.join(scratch, '%s_4x.png' % name))

    # ---- spikes: v4, no dither
    dv.set_level(None)
    name, pal, fn = haz['A']
    fr, extra = fn()
    old = np.array(Image.open(os.path.join(V4DIR, 'frames_A_1x.png')).convert('RGBA'))
    new = strip(pal, fr)
    assert old.shape == np.array(new).shape and (old == np.array(new)).all(), 'spikes differ from the v4 sheet'
    n, _ = line(name, pal, fr, fr, '   identical to hazards-v4/frames_A_1x.png')
    assert n == 0
    new.save(os.path.join(HERE, 'frames_%s_1x.png' % name))
    sc = [s6.scene(base, 'A', pal, fr, extra, f, masks, None, 'S0') for f in range(NF)]
    outputs(name, 'A', sc, None, rep)
    shots(name, sc)

    # ---- water: V2, full band, checker thinned along ripple dashes
    name, pal0, fn = haz['C']
    fr0, extra = fn()
    cfg = dv.LV[WATER_LEVEL]['C']
    pal, mats = cfg['pal'], cfg['mats']
    remap = np.arange(len(pal.keys) + 1)
    for a, b in cfg['merge'].items():
        remap[pal[a]] = pal[b]
    fm = [remap[a] for a in fr0]
    dv.EXT['water'], s6.TM['water'] = 'M', WATER_OLD
    fold = [dv.dither3(a, pal, mats) for a in fm]                      # before: round 3 V2 (ripple dashes, half band)
    dv.EXT['water'], s6.TM['water'] = 'H', water_map(WATER_PATTERN)
    fd = [dv.dither3(a, pal, mats) for a in fm]
    assert set(np.unique(np.array(fd)).tolist()) <= set(np.unique(np.array(fm)).tolist())
    nold = stats(pal, fm, fold)
    n, p10 = line(name, pal, fm, fd, '   pattern %s, full band; before (V2 dashes, half band) %d px' % (WATER_PATTERN, nold[0]))
    assert n and p10 >= MIN_STEP, (name, p10)
    strip(pal, fd).save(os.path.join(HERE, 'frames_%s_1x.png' % name))
    dv.set_level(None)
    c0 = s6.scene(base, 'C', pal0, fr0, extra, STILL, masks, None, 'S0')
    dv.set_level(WATER_LEVEL)
    c1 = s6.scene(base, 'C', pal, fold, extra, STILL, masks, None, 'M')
    sc = [s6.scene(base, 'C', pal, fd, extra, f, masks, None, 'M') for f in range(NF)]
    sh = [s6.scene(base, 'C', pal, fd, extra, f, masks, None, 'S0') for f in range(NF)]
    ln, lmed, lp10 = dv.pair_stats([(dv.rgb(a), dv.rgb(b)) for a, b in zip(sh, sc)])
    assert lp10 >= MIN_STEP
    rep.append('water  lurker sprite (own 8 colour palette, unchanged from round 3 V2): dither px %d per loop  pair step median %.1f  p10 %.1f' % (ln, lmed, lp10))
    hard_sc = s6.scene(base, 'C', pal, fm, extra, STILL, masks, None, 'S0')
    s6.row_sheet([('before: v4, no dither', c0), ('before: round 3 V2, dashes, half band', c1), ('after: final, checker, full band', sc[STILL])],
                 CELL, os.path.join(HERE, 'compare_%s_4x.png' % name), 4)
    outputs(name, 'C', sc, hard_sc, rep, zoom=True)
    shots(name, sc)
    if scratch:
        for st in ('chk', 'brick'):
            s6.TM['water'] = water_map(st)
            alt = [dv.dither3(a, pal, mats) for a in fm[STILL:STILL + 1]]
            s = s6.scene(base, 'C', pal, {STILL: alt[0]}, extra, STILL, masks, None, 'M')
            s.crop((0, 176, 320, 224)).convert('RGB').save(os.path.join(scratch, 'water_alt_%s_1x.png' % st))
            dv.up(s, (64, 176, 224, 224), 4).save(os.path.join(scratch, 'water_alt_%s_4x.png' % st))
        c1.crop((0, 176, 320, 224)).convert('RGB').save(os.path.join(scratch, 'water_before_1x.png'))
    dv.set_level(None)

    # ---- lava: V1, half band, grid anchor, cast light with the heavy fade
    name, pal0, fn = haz['D']
    fr0, extra = fn()
    cfg = dv.LV[LAVA_LEVEL]['D']
    pal, mats = cfg['pal'], cfg['mats']
    assert not cfg['merge'] and dv.EXT['melt'] == 'M' and dv.EXT['crust'] == 'M'
    fd = [dv.dither3(a, pal, mats) for a in fr0]                       # no coords = grid anchor
    n, p10 = line(name, pal, fr0, fd, '   crust anchor grid')
    assert n and p10 >= MIN_STEP, (name, p10)
    strip(pal, fd).save(os.path.join(HERE, 'frames_%s_1x.png' % name))
    lev = v4.light_levels('D', pal0, fr0)
    dv.set_level(LAVA_LEVEL)
    sc = [s6.scene(base, 'D', pal, fd, extra, f, masks, lev, 'H') for f in range(NF)]
    sh = [s6.scene(base, 'D', pal, fd, extra, f, masks, lev, 'S0') for f in range(NF)]
    ln, lmed, lp10 = dv.pair_stats([(dv.rgb(a), dv.rgb(b)) for a, b in zip(sh, sc)])
    assert lp10 >= MIN_STEP
    rep.append('lava   cast light (3 colours in the city palette): dither px %d per loop  pair step median %.1f  p10 %.1f' % (ln, lmed, lp10))
    outputs(name, 'D', sc, None, rep)
    shots(name, sc)

    # ---- fire: v6 + clean-up + re-spaced cool shades + checker between the bands
    name = 'fire'
    fb.FLAME_FIX = flame_fix
    hard, _ = fb.render_fire()
    v6 = unstrip(os.path.join(V6DIR, 'frames_B_1x.png'), fb.PB)
    moved = int(sum((a != b).sum() for a, b in zip(v6, hard)))
    sil = int(sum(((a != 0) != (b != 0)).sum() for a, b in zip(v6, hard)))
    fd = []
    for f in range(NF):
        d = FLAME_HARD[f].copy()
        d[:FLAME_ROWS] = dv.dither3(FLAME_HARD[f][:FLAME_ROWS], PB, FIRE_MATS)
        assert (d == PB['w']).sum() == (FLAME_HARD[f] == PB['w']).sum() and ((d == PB['w']) == (FLAME_HARD[f] == PB['w'])).all()
        fd.append(np.where(hard[f] == FLAME_HARD[f], d, hard[f]))      # coal bed and embers are drawn over the flame
    n, p10 = line(name, PB, hard, fd, '   extent %s' % FIRE_EXT)
    assert n and p10 >= MIN_STEP, (name, p10)
    for a, b in zip(hard, fd):
        assert ((a == PB['w']) == (b == PB['w'])).all()                # white core untouched
    for tag, frs in (('shapes (hard)', hard), ('as drawn (dithered)', fd), ('v6 sheet', v6)):
        ms = [fb.mask_metrics(fb.hot_mask(a)) for a in frs]
        gaps = [m[0] - m[1] for m in ms]
        rep.append('fire   gap between the two tallest tongues, %-20s min %d  per frame %s  | tallest %s'
                   % (tag + ':', min(gaps), ' '.join(map(str, gaps)), ' '.join(str(m[0]) for m in ms)))
        if tag != 'v6 sheet':
            assert min(gaps) >= 2, (tag, gaps)
    rep.append('fire   versus the v6 sheet (hard, before dither): %d px changed in 16 frames, %d of them silhouette' % (moved, sil))
    rep.extend('fire   fix: ' + s for s in FIX_LOG)
    rep.append('fire   ramp steps M D r O y Y w: ' + ' '.join('%.1f' % (dv.lum(PB.d[b]) - dv.lum(PB.d[a])) for a, b in zip('MDrOyY', 'DrOyYw')))
    strip(PB, fd).save(os.path.join(HERE, 'frames_%s_1x.png' % name))
    dv.set_level(None)
    lev0 = v4.light_levels('B', fb.PB, v6)
    c0 = s6.scene(base, 'B', fb.PB, v6, {}, STILL, masks, lev0, 'S0')
    lev = v4.light_levels('B', PB, hard)
    dv.set_level(LAVA_LEVEL)                                           # cast light colours as on lava
    c1 = s6.scene(base, 'B', PB, hard, {}, STILL, masks, lev, 'S0')
    sc = [s6.scene(base, 'B', PB, fd, {}, f, masks, lev, 'H') for f in range(NF)]
    sh = [s6.scene(base, 'B', PB, fd, {}, f, masks, lev, 'S0') for f in range(NF)]
    ln, lmed, lp10 = dv.pair_stats([(dv.rgb(a), dv.rgb(b)) for a, b in zip(sh, sc)])
    assert lp10 >= MIN_STEP
    rep.append('fire   cast light (same 3 colours as lava): dither px %d per loop  pair step median %.1f  p10 %.1f' % (ln, lmed, lp10))
    s6.row_sheet([('before: v6', c0), ('fixes + new M D r, no dither', c1), ('after: final', sc[STILL])],
                 CELL, os.path.join(HERE, 'compare_%s_4x.png' % name), 4)
    outputs(name, 'B', sc, c1, rep, zoom=True)
    shots(name, sc)
    if scratch:
        for f in (5, 12, 14):
            dv.up(sc[f], (0, 176, 128, 224), 4).save(os.path.join(scratch, 'fire_f%02d_4x.png' % f))
    dv.set_level(None)

    rep.append('')
    rep.extend('palette %-6s %s' % (k, v) for k, v in pals.items())
    rep.append('(* = palette slot not used by the tile frames)')
    for fn_ in os.listdir(HERE):
        if fn_.endswith('.png') and not fn_.startswith('frames_'):
            assert Image.open(os.path.join(HERE, fn_)).width <= 1400, fn_
    with open(os.path.join(HERE, 'numbers.txt'), 'w') as fh:
        fh.write('\n'.join(rep) + '\n')
    print('\n'.join(rep))
    write_html()


def write_html():
    names = ['spikes', 'fire', 'water', 'lava']
    note = {'spikes': 'No dither, as decided. Hazards v4, unchanged.',
            'fire': 'v6 shapes and motion. Checker between the flame bands, none on the white core.',
            'water': 'Palette V2, dither on the full band: checker that thins out along ripple dashes.',
            'lava': 'Palette V1, half band, crust anchored to the grid, cast light fade kept.'}
    h = ['<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Bubblegum Brawl: final hazard set (draft)</title>',
         '<style>body{background:#14161c;color:#d8dce6;font-family:Helvetica,Arial,sans-serif;margin:24px}'
         'img{image-rendering:pixelated;max-width:none;display:block;margin:8px 0 16px}h2{margin-top:40px}'
         'p{max-width:900px;line-height:1.4}.x{overflow-x:auto}</style></head><body>',
         '<h1>Final hazard set (draft)</h1>', '<p>View at 100 percent browser zoom. Numbers and palettes: numbers.txt and README.md.</p>']
    for n in names:
        h.append('<h2>%s</h2><p>%s</p>' % (n.capitalize(), note[n]))
        h.append('<p>Loop in the scene, 4x</p><div class="x"><img src="anim_%s_4x.gif" alt="%s loop"></div>' % (n, n))
        h.append('<p>Still (frame %d) in the scene, 4x</p><div class="x"><img src="scene_%s_4x.png" alt="%s still"></div>' % (STILL, n, n))
        if n in ('fire', 'water'):
            h.append('<p>Before and after, 4x</p><div class="x"><img src="compare_%s_4x.png" alt="%s before and after"></div>' % (n, n))
            h.append('<p>Zoom, 8x</p><img src="zoom_%s_8x.png" alt="%s zoom">' % (n, n))
        h.append('<p>Build input: all 16 frames at 1x (one row per 64 pixel tile variant)</p><div class="x"><img src="frames_%s_1x.png" alt="%s frames"></div>' % (n, n))
    h.append('</body></html>')
    with open(os.path.join(HERE, 'index.html'), 'w') as fh:
        fh.write('\n'.join(h) + '\n')


if __name__ == '__main__':
    main()
