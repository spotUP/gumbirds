#!/usr/bin/env python3
# Bubblegum Brawl dither test, round 3: VISIBLE dither.
# Rounds 1 and 2 dithered between shades 11 to 20 luminance apart; at that step a checker blends into a flat tone.
# Here every ramp is rebuilt with fewer, further-apart shades and the dither supplies the in-between tones.
#   H-old = round 2 level H, unchanged (draw_dither_s6_strong.py, library copy)
#   V1    = neighbouring shades of every dithered ramp at least about 30 apart in luminance
#   V2    = at least about 40 apart; water, melt and sky lose one shade each (merged into a neighbour)
# Style "mixed by material": stipple on steel, crust, rock; ripple dashes on water; checker on melt and cast light;
# sky in irregular clusters with cloud-shaped band edges. Extent: full band on sky and steel, half band on water, lava.
# Shapes, physics and timing are hazards v4 (hazards_v4_base.py, library copy). Fire is left out.
# Run: /opt/homebrew/bin/python3.14 -I draw_dither_visible.py        (about a minute; needs Pillow + numpy)
#   --scratch DIR   also writes 1x / 4x inspection crops into DIR
import os
import sys
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
from PIL import Image
import hazards_v4_base as v4
import dither_round1 as r1
import draw_dither_s6_strong as s6

NF, H = v4.NF, v4.H
MIN_STEP = 28.0
LUMW = np.array([0.299, 0.587, 0.114])
NAMES = {'A': 'spikes', 'C': 'water', 'D': 'lava'}
LABEL = {'H': 'H-old: round 2 heavy', 'V1': 'V1: pair step about 30', 'V2': 'V2: pair step about 42'}
EXT = {'steel': 'H', 'water': 'M', 'rock': 'M', 'melt': 'M', 'crust': 'M'}     # H = full band, M = half band


def lum(c):
    return float(np.dot(np.array(c[:3], float), LUMW))


def repal(base, **chg):
    d = dict(base.d)
    d.update(chg)
    return v4.Pal(d)


# ---------------------------------------------------------------- palettes (15 colours + transparent at most)
# merge = {dropped shade: neighbour that takes its pixels}; mats = (kind, ramp dark -> light) after the merge
LV = {
    'V1': {
        'A': dict(pal=repal(v4.PA, D=(26, 30, 80)), merge={}, mats=[('steel', 'Ddmlh')]),
        'C': dict(pal=repal(v4.PC, o=(6, 6, 30), n=(22, 36, 104), u=(44, 66, 164), b=(28, 120, 198), B=(48, 156, 224),
                            T=(66, 204, 212), c=(118, 228, 244), f=(200, 244, 255)),
                  merge={}, mats=[('water', 'onubBTc'), ('foam', 'cf'), ('rock', 'pPq')]),
        'D': dict(pal=repal(v4.PD, m=(36, 0, 44), P=(110, 12, 58), D=(184, 32, 36), r=(232, 62, 28), O=(250, 116, 24),
                            y=(255, 186, 48), Y=(255, 246, 184), o=(18, 4, 18), k=(74, 24, 42), K=(128, 52, 54)),
                  merge={}, mats=[('melt', 'mPDrOyY'), ('crust', 'okKQH')]),
        'sky': [(4, 4, 18), (26, 30, 88), (66, 50, 138), (116, 70, 170)],          # zenith to violet horizon
        'sky_y': [40, 92, 144],
        'light': {'face': (86, 26, 58), 'dim': (170, 54, 46), 'hot': (255, 150, 62)},
    },
    'V2': {
        'A': dict(pal=repal(v4.PA, D=(22, 24, 72), d=(60, 70, 138), m=(116, 136, 200), l=(178, 200, 238), h=(232, 244, 255)),
                  merge={}, mats=[('steel', 'Ddmlh')]),
        'C': dict(pal=repal(v4.PC, o=(4, 4, 26), n=(28, 44, 120), b=(28, 102, 188), B=(50, 154, 224), T=(76, 214, 216),
                            c=(150, 244, 250), f=(214, 250, 255)),
                  merge={'u': 'n'}, mats=[('water', 'onbBTc'), ('foam', 'cf'), ('rock', 'pPq')]),
        'D': dict(pal=repal(v4.PD, m=(40, 0, 48), D=(146, 18, 44), r=(224, 52, 28), O=(250, 116, 24), y=(255, 190, 50),
                            Y=(255, 248, 190), o=(16, 2, 16), k=(86, 28, 44), K=(146, 66, 58), Q=(204, 120, 88), H=(250, 200, 150)),
                  merge={'P': 'm'}, mats=[('melt', 'mDrOyY'), ('crust', 'okKQH')]),
        'sky': [(4, 4, 18), (38, 42, 110), (108, 68, 166)],
        'sky_y': [60, 130],
        'light': {'face': (108, 30, 60), 'dim': (200, 64, 46), 'hot': (255, 150, 62)},
    },
}
OLD = {'A': dict(pal=v4.PA, mats=r1.MATS['A']), 'C': dict(pal=v4.PC, mats=r1.MATS['C']), 'D': dict(pal=v4.PD, mats=r1.MATS['D'])}
ORIG = dict(PC=v4.PC, PLK=v4.PLK, LIGHT_RGB=v4.LIGHT_RGB)


def set_level(L):
    """The lurker sprite and the cast light read their colours from module globals of the v4 library."""
    if L is None:
        v4.PC, v4.PLK, v4.LIGHT_RGB = ORIG['PC'], ORIG['PLK'], ORIG['LIGHT_RGB']
        return
    pc = LV[L]['C']['pal']
    v4.PC = pc
    v4.PLK = repal(ORIG['PLK'], o=pc.d['o'], f=pc.d['f'])
    v4.LIGHT_RGB = LV[L]['light']


# ---------------------------------------------------------------- hazard dither (round 2 method, ramps as parameter)
def dither3(idx, pal, mats, coords=None):
    h, w = idx.shape
    yy, xx = np.mgrid[0:h, 0:w]
    out = idx.copy()
    best = np.full(idx.shape, 99)
    for kind, ramp in mats:
        if kind == 'foam':
            continue                                 # foam stays hard
        L = EXT[kind]
        q = 4 if L == 'M' else 8
        X, Y = (coords or {}).get(kind, (xx, yy))
        T = s6.TM[kind][Y % 16, X % 16]
        small = kind in s6.SMALL
        rule = s6.SOLID[L].get(kind, ())
        for ka, kb in zip(ramp, ramp[1:]):
            ia, ib = pal[ka], pal[kb]
            A, B = idx == ia, idx == ib
            if not A.any() or not B.any():
                continue
            As, Bs = (s6.solid(A), s6.solid(B)) if small else (A, B)
            sa, sb = (As, Bs) if 'src' in rule else (A, B)
            d = np.where(B, r1.dist(sa), r1.dist(sb))
            th = np.where(B, r1.thick(B), r1.thick(A))
            if small:
                own = (As | Bs) if 'own' in rule else (A | B)
                rows = np.clip(th, 1, 2) if L == 'M' else np.clip(th, 1, 4)
            else:
                own = (A | B) & (th >= 2)            # caustics, glints, crack glow are left alone
                rows = np.maximum(1, np.round(th / 2.0).astype(int)) if L == 'M' else np.maximum(1, th)
            ok = own & (d <= rows) & (d <= 7) & (r1.dist(~(A | B)) >= d)
            dens = 0.5 * (1.0 - (d - 1.0) / rows)                    # share of the OTHER shade: 50 percent at the edge
            if kind == 'steel':                                      # blades are 14 px: hold the half tone, then stipple
                dens = np.where(d <= np.ceil(rows / 2.0), 0.5, 0.25)
            dens = np.maximum(1.0 / q, np.round(dens * q) / q)
            t = np.where(B, 1.0 - dens, dens)
            new = np.where(t > T, ib, ia)
            ch = ok & (new != idx) & (d < best)
            out[ch] = new[ch]
            best[ch] = d[ch]
    return out


# ---------------------------------------------------------------- sky: clustered checker, cloud-shaped band edges
def sky_fields():
    """T: 64 x 64 threshold map. 50 percent is a checker; below it the checker survives only in streak-shaped
    clusters, above it the gaps close in the same clusters. CL: wisps that push the band edges up and down.
    Both come from a fixed seed (a stand-in for hand placement; same picture on every run)."""
    rng = np.random.default_rng(7)
    y, x = np.mgrid[0:64, 0:64]
    sc = np.zeros((64, 64))
    for _ in range(46):
        cx, cy = rng.uniform(0, 64, 2)
        rx, ry, a = rng.uniform(4, 10), rng.uniform(1.2, 2.6), rng.uniform(0.5, 1.0)
        dx, dy = (x - cx + 32) % 64 - 32, (y - cy + 32) % 64 - 32
        sc += a * np.exp(-(dx / rx) ** 2 - (dy / ry) ** 2)
    chk = (x + y) % 2 == 0
    T = np.empty((64, 64))
    for cls, lo in ((True, 0.0), (False, 0.5)):
        m = chk == cls
        v = -sc[m]
        o = np.argsort(v, kind='stable')
        r = np.empty(len(v))
        r[o] = (np.arange(len(v)) + 0.5) / len(v)
        T[m] = lo + 0.5 * r
    Y, X = np.mgrid[0:224, 0:320]
    cl = np.zeros((224, 320))
    for _ in range(30):
        cx, cy = rng.uniform(-20, 340), rng.uniform(0, 200)
        rx, ry = rng.uniform(16, 52), rng.uniform(2.5, 7.0)
        a = rng.choice([-1.0, 1.0]) * rng.uniform(0.5, 1.0)
        cl += a * np.exp(-((X - cx) / rx) ** 2 - ((Y - cy) / ry) ** 2)
    return T, cl


SKY_T, SKY_CL = sky_fields()


def sky3(base, L, dith=True):
    cols, edges = LV[L]['sky'], LV[L]['sky_y']
    a = np.array(base.convert('RGB'))
    sky = np.zeros(a.shape[:2], bool)
    for c in r1.SKYC:
        sky |= (a == np.array(c, np.uint8)).all(-1)
    Y, X = np.mgrid[0:224, 0:320]
    Tm = SKY_T[Y % 64, X % 64]
    best = np.full(sky.shape, 1e9)
    out = a.copy()
    for k, yb in enumerate(edges):
        sp = min(abs(yb - e) for e in edges if e != yb)
        z = 0.42 * sp                                # zones nearly meet: a thin flat band is left between them
        off = np.round(np.interp(np.arange(320), np.arange(21) * 16, s6.SKY_OFF[k % 4])).astype(int)
        s = (Y + 0.5) - (yb + off[None, :]) + 9.0 * SKY_CL
        t = np.clip(0.5 + s / (2 * z), 0, 1)
        t = np.where(t < 0.06, 0.0, np.where(t > 0.94, 1.0, t))      # no lone pixels far out in the flat band
        light = (t > Tm) if dith else (s > 0)
        m = sky & (np.abs(s) < best)
        out[m] = np.where(light[m][:, None], np.array(cols[k + 1], np.uint8), np.array(cols[k], np.uint8))
        best[m] = np.abs(s)[m]
    return Image.fromarray(out, 'RGB').convert('RGBA')


# ---------------------------------------------------------------- numbers
def rgb(im):
    return np.array(im.convert('RGB')).astype(float)


def pair_stats(pairs):
    """pairs: [(hard rgb array, dithered rgb array)]. A dither pixel differs from the hard-edged picture drawn with
    the same palette; its pair step is the luminance difference between the two shades."""
    steps = []
    for a, b in pairs:
        m = (a != b).any(-1)
        steps.append(np.abs((a[m] - b[m]) @ LUMW))
    st = np.concatenate(steps) if steps else np.zeros(0)
    if len(st) == 0:
        return 0, 0.0, 0.0
    return len(st), float(np.median(st)), float(np.percentile(st, 10))


def ramp_steps(pal, mats):
    return '; '.join('%s %s' % (kind, ' '.join('%.0f' % (lum(pal.d[b]) - lum(pal.d[a])) for a, b in zip(ramp, ramp[1:])))
                     for kind, ramp in mats if kind != 'foam')


def sky_tiles(im):
    a = np.array(im.convert('RGB'))
    return len({a[y:y + 16, x:x + 16].tobytes() for y in range(0, 224, 16) for x in range(0, 320, 16)})


def zoom_window(diff, ys):
    best, at = -1, (0, ys[0])
    for y0 in ys:
        for x0 in range(0, 320 - 48 + 1, 4):
            n = int(diff[y0:y0 + 32, x0:x0 + 48].sum())
            if n > best:
                best, at = n, (x0, y0)
    return at


def up(im, box, k):
    return im.crop(box).convert('RGB').resize(((box[2] - box[0]) * k, (box[3] - box[1]) * k), Image.NEAREST)


CROP = (64, 112, 192, 224)        # GIF window, 128 x 112 px
CELL = (72, 152, 184, 224)        # comparison cell at 4x, 112 x 72 px (three cells stay under 1400 px)
SKYCELL = (0, 0, 112, 176)
WIDE = (0, 152, 320, 224)         # 1x strips show the whole screen width
SKYWIDE = (0, 0, 320, 192)


def main():
    scratch = sys.argv[sys.argv.index('--scratch') + 1] if '--scratch' in sys.argv else None
    rep = []
    base0 = v4.base_scene()
    masks = v4.light_masks(base0)
    order = ['H', 'V1', 'V2']

    # ---- sky
    bases = {'H': s6.sky2(base0, 'H')}
    hardb = {}
    oldhard = np.array(base0.convert('RGB')).astype(float)
    # round 2 reference: hard picture = same 5 shades without pattern is not stored there; measure pairs directly
    n, med, p10 = sky_pairs_old(bases['H'])
    rep.append('sky    H-old  dither px %6d  step median %5.1f  p10 %5.1f  colours %d  tiles %3d of 280'
               % (n, med, p10, len(s6.SKY5), sky_tiles(bases['H'])))
    for L in ('V1', 'V2'):
        bases[L] = sky3(base0, L)
        hardb[L] = sky3(base0, L, dith=False)
        n, med, p10 = pair_stats([(rgb(hardb[L]), rgb(bases[L]))])
        assert p10 >= MIN_STEP, ('sky', L, p10)
        new = s6.rgbset(bases[L]) - s6.rgbset(base0)
        assert new <= set(LV[L]['sky']), new
        cs = LV[L]['sky']
        rep.append('sky    %-5s  dither px %6d  step median %5.1f  p10 %5.1f  colours %d  tiles %3d of 280   ramp steps %s'
                   % (L, n, med, p10, len(cs), sky_tiles(bases[L]), ' '.join('%.0f' % (lum(b) - lum(a)) for a, b in zip(cs, cs[1:]))))
    s6.row_sheet([(LABEL[L], bases[L]) for L in order], SKYCELL, os.path.join(HERE, 'compare_sky_4x.png'), 4)
    s6.row_sheet([(LABEL[L], bases[L]) for L in order], SKYWIDE, os.path.join(HERE, 'strip_sky_1x.png'), 1)
    d2 = (rgb(bases['V2']) != rgb(hardb['V2'])).any(-1)
    x0, y0 = zoom_window(d2, range(0, 160, 8))
    up(bases['V2'], (x0, y0, x0 + 48, y0 + 32), 8).save(os.path.join(HERE, 'zoom_sky_8x.png'))
    rep.append('sky    zoom window x %d y %d' % (x0, y0))
    if scratch:
        for L in order:
            bases[L].crop((0, 0, 160, 192)).convert('RGB').save(os.path.join(scratch, 'sky_%s_1x.png' % L))

    # ---- hazards
    lc = s6.lava_coords()
    for key, name, pal0, fn in v4.HAZ:
        if key not in NAMES:
            continue
        frames0, extra = fn()
        tw = frames0[0].shape[1]
        lev = v4.light_levels(key, pal0, frames0) if key in v4.LIGHT_W else None
        ys = [r1.spike_y(f, tw) if key == 'A' else None for f in range(NF)]
        yy, xx = np.mgrid[0:H, 0:tw]
        opaque = int(sum((a != 0).sum() for a in frames0))
        raw = NF * (tw // 16) * (H // 16)

        def coords(f, anchor='grid'):
            c = {}
            if key == 'A':
                c['steel'] = (xx, ys[f])
            if key == 'D' and anchor != 'grid':
                c['crust'] = lc[anchor][f]
            return c

        def line(L, pal, hard, dith, mats):
            n, med, p10 = pair_stats([(pal.lut[a][..., :3].astype(float), pal.lut[b][..., :3].astype(float)) for a, b in zip(hard, dith)])
            ncol = len(set(np.unique(np.array(dith)).tolist()) - {0})
            rep.append('%-6s %-5s  dither px %6d (%4.1f%% of opaque)  step median %5.1f  p10 %5.1f  colours %2d  tiles %3d of %3d   ramp steps %s'
                       % (name, 'H-old' if L == 'H' else L, n, 100.0 * n / opaque, med, p10, ncol, v4.tile_count(dith), raw, ramp_steps(pal, mats)))
            return p10

        cells, wide = [], []
        set_level(None)
        fH = [s6.dither2(frames0[f], key, 'H', coords(f)) for f in range(NF)]
        line('H', pal0, frames0, fH, OLD[key]['mats'])
        sH = s6.scene(bases['H'], key, pal0, fH, extra, 2, masks, lev, 'H')
        cells.append((LABEL['H'], sH))
        for L in ('V1', 'V2'):
            cfg = LV[L][key]
            pal, mats = cfg['pal'], cfg['mats']
            assert len(pal.keys) <= 15
            remap = np.arange(len(pal.keys) + 1)
            for a, b in cfg['merge'].items():
                remap[pal[a]] = pal[b]
            fm = [remap[fr] for fr in frames0]
            fd = [dither3(fm[f], pal, mats, coords(f)) for f in range(NF)]
            assert all(((a == 0) == (b == 0)).all() for a, b in zip(fd, frames0)), (key, L)        # silhouette unchanged
            assert set(np.unique(np.array(fd)).tolist()) <= set(np.unique(np.array(fm)).tolist())  # no colour added
            p10 = line(L, pal, fm, fd, mats)
            assert p10 >= MIN_STEP, (name, L, p10)
            set_level(L)
            mode = 'H' if key == 'D' else 'M'        # cast light: heavy fade; lurker: medium
            sc = [s6.scene(bases[L], key, pal, fd, extra, f, masks, lev, mode) for f in range(NF)]
            if key in ('C', 'D'):                     # lurker sprite / cast light: same scene with the hard version
                sh = [s6.scene(bases[L], key, pal, fd, extra, f, masks, lev, 'S0') for f in range(NF)]
                n, med, p10 = pair_stats([(rgb(a), rgb(b)) for a, b in zip(sh, sc)])
                assert p10 >= MIN_STEP, (name, L, 'extra', p10)
                rep.append('%-6s %-5s  %s: dither px %5d per loop  step median %5.1f  p10 %5.1f'
                           % (name, L, 'lurker sprite' if key == 'C' else 'cast light', n, med, p10))
            if key == 'D':                            # crust flicker: dither-only motion on still crust, per anchor
                ids = [pal[k] for k in 'okKQH']
                for an in ('grid', 'surf', 'plate'):
                    fr = fd if an == 'grid' else [dither3(fm[f], pal, mats, coords(f, an)) for f in range(NF)]
                    chg, bl = s6.crawl(fr, fm, ids)
                    rep.append('lava   %-5s  crust anchor %-5s: changes on still art %4d, blinks %4d per loop' % (L, an, chg, bl))
            set_level(None)
            cells.append((LABEL[L], sc[2]))
            v4.save_gif(os.path.join(HERE, 'anim_%s_%s_4x.gif' % (L, name)), [up(s, CROP, 4) for s in sc],
                        int(round(v4.VFRAMES[key] * 1000 / 60 / 10)) * 10)
            if L == 'V2':
                hard2 = s6.scene(hardb[L], key, pal, fm, extra, 2, masks, lev, 'S0')
                d2 = (rgb(sc[2]) != rgb(hard2)).any(-1)
                d2[:, :] &= ~(rgb(bases[L]) != rgb(hardb[L])).any(-1)         # count hazard dither only, not the sky
                x0, y0 = zoom_window(d2, [v4.HAZ_Y])
                up(sc[2], (x0, y0, x0 + 48, y0 + 32), 8).save(os.path.join(HERE, 'zoom_%s_8x.png' % name))
                rep.append('%-6s zoom window x %d y %d' % (name, x0, y0))
            if scratch:
                sc[2].crop((64, 176, 224, 224)).convert('RGB').save(os.path.join(scratch, '%s_%s_1x.png' % (name, L)))
                up(sc[2], (64, 184, 192, 224), 4).save(os.path.join(scratch, '%s_%s_4x.png' % (name, L)))
        s6.row_sheet(cells, CELL, os.path.join(HERE, 'compare_%s_4x.png' % name), 4)
        s6.row_sheet(cells, WIDE, os.path.join(HERE, 'strip_%s_1x.png' % name), 1)
    for f in os.listdir(HERE):
        if f.startswith('compare_') and f.endswith('.png'):
            assert Image.open(os.path.join(HERE, f)).width <= 1400, f
    with open(os.path.join(HERE, 'numbers.txt'), 'w') as fh:
        fh.write('\n'.join(rep) + '\n')
    print('\n'.join(rep))
    write_html()


def sky_pairs_old(im):
    """Round 2 sky: every pixel sits between two neighbouring shades of SKY5; a dither pixel is one whose 4 x 4 block
    holds both shades, counted on the minority shade. Step = luminance difference of the two shades."""
    a = np.array(im.convert('RGB'))
    ix = np.full(a.shape[:2], -1)
    for i, c in enumerate(s6.SKY5):
        ix[(a == np.array(c, np.uint8)).all(-1)] = i
    steps = []
    for y in range(0, 224, 4):
        for x in range(0, 320, 4):
            b = ix[y:y + 4, x:x + 4]
            v = b[b >= 0]
            if len(v) == 0 or v.min() == v.max():
                continue
            lo, hi = int(v.min()), int(v.max())
            n = int(min((v == lo).sum(), (v == hi).sum()))
            steps += [lum(s6.SKY5[hi]) - lum(s6.SKY5[lo])] * n
    st = np.array(steps)
    return len(st), float(np.median(st)), float(np.percentile(st, 10))


def write_html():
    sec = []
    for name in ('sky', 'water', 'lava', 'spikes'):
        g = ''
        if name != 'sky':
            g = ''.join('<figure><img src="anim_%s_%s_4x.gif" alt=""><figcaption>%s, animation at 4x</figcaption></figure>' % (L, name, L)
                        for L in ('V1', 'V2'))
        sec.append('<section><h2>%s</h2>'
                   '<figure><img src="compare_%s_4x.png" alt=""><figcaption>Round 2 heavy, V1, V2 at 4x</figcaption></figure>'
                   '<figure><img src="strip_%s_1x.png" alt=""><figcaption>The same three at true size</figcaption></figure>'
                   '<figure><img src="zoom_%s_8x.png" alt=""><figcaption>V2 detail, 48 x 32 pixels at 8x</figcaption></figure>'
                   '%s</section>' % (name.capitalize(), name, name, name, g))
    html = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Bubblegum Brawl: visible dither, V1 and V2</title>'
            '<style>body{background:#14161c;color:#d8dce6;font-family:Helvetica,Arial,sans-serif;margin:24px}'
            'img{image-rendering:pixelated;max-width:none;display:block}h1{font-size:22px}h2{font-size:18px;margin-top:36px;'
            'border-top:1px solid #333a48;padding-top:16px}figure{margin:12px 0 20px 0}figcaption{font-size:13px;color:#9aa2b4;'
            'margin-top:4px}p{max-width:900px;line-height:1.45}</style></head><body>'
            '<h1>Bubblegum Brawl: visible dither, V1 and V2</h1>'
            '<p>View at 100 percent browser zoom. Each picture shows round 2 heavy (left), V1 (middle) and V2 (right). '
            'V1 mixes shades about 30 apart in brightness, V2 about 42 apart. Numbers and palettes are in README.md.</p>'
            + ''.join(sec) + '</body></html>\n')
    with open(os.path.join(HERE, 'index.html'), 'w') as fh:
        fh.write(html)


if __name__ == '__main__':
    main()
