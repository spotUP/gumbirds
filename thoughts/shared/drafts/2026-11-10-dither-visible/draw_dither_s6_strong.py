#!/usr/bin/env python3
# Bubblegum Brawl dither test, round 2: style 6 "mixed by material" at two stronger levels on hazards v4.
#   S0 = hazards v4, no dither.   S6 = round 1 style 6 (dither_round1.py, unchanged copy of draw_dither_variants.py).
#   M  = medium-strong: dither zone about half of each shade band, quarter steps (25 / 50 percent).
#   H  = heavy: dither zone up to the full band, eighth steps (12 / 25 / 37 / 50 percent), thin bands included.
# Same rule as round 1: only the transition between two NEIGHBOURING shades of one material ramp is redrawn; shapes,
# physics, animation, timing and hazard palettes are the v4 ones (hazards_v4_base.py, unchanged copy). New here:
#   - zone depth follows the local band thickness (M: half, H: all of it), density falls from 50 percent at the edge
#   - one threshold map per material: steel, crust, rock and melt are CHECKER-CLASS maps (50 percent is an exact
#     checker; lower densities thin that checker out in hand-placed clusters), water keeps the ripple dashes,
#     sky keeps the ordered 4 x 4 pattern
#   - steel: 2 px wide bands on blades, collars and sleeves are dithered too (round 1 needed 3 px)
#   - sky: 5 shades with a wide value spread instead of 3 close ones (+2 colours in the backdrop palette)
#   - lurker sprite (body shadow, fin) and the cast light (face band, rims) are dithered
#   - lava crust: pattern anchor is selectable (grid / plate / surf); the script measures all three, see README
# Fire is left out (owned elsewhere). Deterministic, no network.
# Run: /opt/homebrew/bin/python3.14 -I draw_dither_s6_strong.py            (about a minute; needs Pillow + numpy)
#   --scratch DIR   also writes inspection sheets (crust anchor frames, 1x scenes) into DIR
import os
import sys
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
from PIL import Image, ImageDraw
import hazards_v4_base as v4
import dither_round1 as r1

NF, H = v4.NF, v4.H
LEVELS = [('S0', 'S0: v4, no dither'), ('S6', 'S6 round 1'), ('M', 'M: medium-strong'), ('H', 'H: heavy')]
CRUST_ANCHOR = 'grid'        # chosen after the measurement below (README, section "Lava crust anchor")
SUBJ = {'A': 'spikes', 'C': 'water', 'D': 'lava'}


# ---------------------------------------------------------------- threshold maps (16 x 16, tile-grid periodic)
def checker_class(score):
    """50 percent = exact checker. Below that the checker is thinned out in the order of a hand-placed score map,
    above it the gaps fill in the same order: the dither stays a broken checker at every density."""
    y, x = np.mgrid[0:16, 0:16]
    chk = (x + y) % 2 == 0
    T = np.empty((16, 16))
    for cls, lo in ((True, 0.0), (False, 0.5)):
        m = chk == cls
        v = score[m]
        o = np.argsort(v, kind='stable')
        r = np.empty(len(v))
        r[o] = (np.arange(len(v)) + 0.5) / len(v)
        T[m] = lo + 0.5 * r
    return T


TM = {
    'water': r1.MAP['water'],                       # ripple dashes
    'melt': checker_class(r1.MAP['melt']),          # checker, thinned in molten blobs
    'crust': checker_class(r1.MAP['crust']),        # checker, thinned as grit stipple
    'rock': checker_class(r1.MAP['crust']),
    'steel': checker_class(r1.MAP['steel']),        # checker, thinned along the brushed grain
}
BAYER = r1.MAP['bayer']
SMALL = ('steel', 'crust', 'rock')
# which side must be a solid (2 x 2 or larger) patch: 'own' = the pixel that changes, 'src' = the shade it borrows
SOLID = {'M': {'steel': ('src',), 'crust': ('own',), 'rock': ('own',)},
         'H': {'steel': (), 'crust': (), 'rock': ()}}


def solid(m):
    """Pixels that belong to a 2 x 2 block of the mask (x wraps)."""
    r = m & np.roll(m, -1, 1)
    b = np.zeros_like(m)
    b[:-1] = r[:-1] & r[1:]
    o = b | np.roll(b, 1, 1)
    o2 = o.copy()
    o2[1:] |= o[:-1]
    return o2


def dither2(idx, key, L, coords=None):
    """coords: {kind: (X, Y)} pattern coordinates; default = tile grid."""
    pal = r1.PALS[key]
    h, w = idx.shape
    yy, xx = np.mgrid[0:h, 0:w]
    out = idx.copy()
    best = np.full(idx.shape, 99)
    q = 4 if L == 'M' else 8
    for kind, ramp in r1.MATS[key]:
        if kind == 'foam':
            continue                                 # foam stays hard
        X, Y = (coords or {}).get(kind, (xx, yy))
        T = TM[kind][Y % 16, X % 16]
        small = kind in SMALL
        rule = SOLID[L].get(kind, ())
        for ka, kb in zip(ramp, ramp[1:]):
            ia, ib = pal[ka], pal[kb]
            A, B = idx == ia, idx == ib
            if not A.any() or not B.any():
                continue
            As, Bs = (solid(A), solid(B)) if small else (A, B)
            sa, sb = (As, Bs) if 'src' in rule else (A, B)
            d = np.where(B, r1.dist(sa), r1.dist(sb))
            th = np.where(B, r1.thick(B), r1.thick(A))
            if small:
                own = (As | Bs) if 'own' in rule else (A | B)
                rows = np.clip(th, 1, 2) if L == 'M' else np.clip(th, 1, 4)   # steel bands are thin: zone depth in px
            else:
                own = (A | B) & (th >= 2)            # caustics, glints, crack glow (under 3 px) are left alone
                rows = np.maximum(1, np.round(th / 2.0).astype(int)) if L == 'M' else np.maximum(1, th)
            ok = own & (d <= rows) & (d <= 7) & (r1.dist(~(A | B)) >= d)
            dens = 0.5 * (1.0 - (d - 1.0) / rows)                    # share of the OTHER shade: 50 percent at the edge
            dens = np.maximum(1.0 / q, np.round(dens * q) / q)
            t = np.where(B, 1.0 - dens, dens)
            new = np.where(t > T, ib, ia)
            ch = ok & (new != idx) & (d < best)
            out[ch] = new[ch]
            best[ch] = d[ch]
    return out


# ---------------------------------------------------------------- lava crust: plate coordinates
def lava_coords():
    """Per frame: (X - nearest crack, Y - surface row) = coordinates that ride with the drifting plate, and
    (X, Y - surface row) = coordinates that only ride the wave."""
    v4.set_domain(128)
    W = v4.W
    agep, flanks = v4.crust_tables()
    ripple = v4.sim_lava_surface()
    plate, surf = [], []
    for f in range(NF):
        t = f / NF
        hh = 0.9 * np.cos(v4.TAU * (2 * v4.XS / W - t)) + 0.5 * np.cos(v4.TAU * (4 * v4.XS / W + t) + 1.0) + ripple[f]
        top = np.floor(v4.LY0 - hh + 0.5).astype(int)
        cr = []
        for (xs, tt, t0) in flanks:
            a0 = (t - t0) % 1.0
            for j in range(12):
                if a0 + j < tt[-1]:
                    cr.append(float(np.interp(a0 + j, tt, xs)) % W)
        cr = np.array(cr)
        xi = np.arange(W)
        dd = (xi[:, None] + 0.5 - cr[None, :] + W / 2) % W - W / 2
        Xp = xi - np.round(cr[np.abs(dd).argmin(1)]).astype(int)
        Yp = np.arange(H)[:, None] - top[None, :]
        plate.append((np.broadcast_to(Xp, (H, W)).copy(), Yp))
        surf.append((np.broadcast_to(xi, (H, W)).copy(), Yp))
    v4.set_domain(64)
    return {'plate': plate, 'surf': surf}


def crawl(frames, frames0, ids):
    """Dither-only motion: pixels that change although the undithered art holds still for three frames there.
    Returns (changes, blinks); a blink is a pixel that changes and is back one frame later."""
    F, F0 = np.array(frames), np.array(frames0)
    chg = blink = 0
    for f in range(NF):
        p, c, n = F[f - 1], F[f], F[(f + 1) % NF]
        still = (F0[f - 1] == F0[f]) & (F0[f] == F0[(f + 1) % NF]) & np.isin(F0[f], ids)
        chg += int(((c != p) & still).sum())
        blink += int(((c != p) & (n == p) & still).sum())
    return chg, blink


# ---------------------------------------------------------------- sky: 5 shades, wide value spread
SKY5 = [(4, 4, 18), (12, 14, 44), (20, 26, 66), (32, 34, 90), (54, 40, 108)]     # zenith to violet horizon glow
SKY_YB = [34, 76, 116, 152]
SKY_OFF = [r1.SKY_OFF[0], r1.SKY_OFF[1], r1.SKY_OFF[0][::-1], list(np.roll(r1.SKY_OFF[1], 7))]   # haze banks, by hand


def sky2(base, L):
    a = np.array(base.convert('RGB'))
    sky = np.zeros(a.shape[:2], bool)
    for c in r1.SKYC:
        sky |= (a == np.array(c, np.uint8)).all(-1)
    Y, X = np.mgrid[0:224, 0:320]
    bay = BAYER[Y % 16, X % 16]
    best = np.full(sky.shape, 1e9)
    out = a.copy()
    z = 10.0 if L == 'M' else 20.0                   # bands are about 40 px: M = half of each band, H = all of it
    for k, yb in enumerate(SKY_YB):
        off = np.round(np.interp(np.arange(320), np.arange(21) * 16, SKY_OFF[k])).astype(int)
        s = (Y + 0.5) - (yb + off[None, :])
        t = np.clip(0.5 + s / (2 * z), 0, 1)
        if L == 'M':
            tq = np.select([t <= 0, t < 1 / 3, t < 2 / 3, t < 1], [0, 0.25, 0.5, 0.75], 1.0)
        else:
            tq = np.select([t <= 0, t < 0.2, t < 0.4, t < 0.6, t < 0.8, t < 1], [0, 0.125, 0.25, 0.5, 0.75, 0.875], 1.0)
        light = tq > bay
        m = sky & (np.abs(s) < best)
        out[m] = np.where(light[m][:, None], np.array(SKY5[k + 1], np.uint8), np.array(SKY5[k], np.uint8))
        best[m] = np.abs(s)[m]
    return Image.fromarray(out, 'RGB').convert('RGBA')


# ---------------------------------------------------------------- lurker sprite, dithered
def put_lurker_d(im, f, top, sx, oy, L):
    """Body shadow fades out in ripple dashes (reads as a shape under water); fin: broken edge between its shades.
    Patterns are anchored to the sprite, so they ride with it."""
    px = im.load()
    water = {v4.PC.d[k] for k in 'nubBT'}
    x0 = sx % 64
    cols = [(x0 + i) % 64 for i in range(2, 13)]
    base = int(round(float(np.mean(top[cols])))) + 1
    cy = base + 8.5
    edge = 0.5 if L == 'M' else 0.85
    lst = v4.lurker(f, top, x0)
    fin = {(x, y): c for (x, y, c, m) in lst if c in 'gkG' and y < base}
    for (x, y, c, mode) in lst:
        X, Yc = x - x0 + sx, oy + y
        if not (0 <= X < im.width and 0 <= Yc < im.height):
            continue
        lx, ly = x - x0, y - base
        if mode == 'u':
            if px[X, Yc][:3] not in water:
                continue
            qq = ((lx - 7.5) / 17.0) ** 2 + ((y + 0.5 - cy) / 5.0) ** 2
            dens = (1 - qq) / edge
            if dens < 1 and dens <= r1.MAP['water'][ly % 16, lx % 16]:
                continue
        elif c == 'g' and y < base:
            if fin.get((x + 1, y)) == 'k' and (lx + ly) % 2 == 0:
                c = 'k'
            elif L == 'H' and fin.get((x + 2, y)) == 'k' and (lx + 2 * ly) % 4 == 0:
                c = 'k'
            elif L == 'H' and fin.get((x - 1, y)) == 'G' and (lx + ly) % 2 == 1:
                c = 'G'
        px[X, Yc] = v4.PLK.d[c] + (255,)


# ---------------------------------------------------------------- cast light, dithered
def cast_light_d(s, key, lev, masks, L):
    """v4 hard light first, then: the face band fades upward in ordered steps, the rims end in dashes."""
    v4.cast_light(s, key, lev, masks)
    bld, edge, under = masks
    px = s.load()
    ref = v4.LIGHT_REF[key]
    face, dim, hot = (v4.LIGHT_RGB[k] + (255,) for k in ('face', 'dim', 'hot'))
    fade = (0.5, 0.5, 0.25, 0.25) if L == 'M' else (0.75, 0.75, 0.5, 0.5, 0.25, 0.25, 0.125, 0.125)
    for x in range(320):
        col = (x // 16) % len(lev)
        Lv = int(lev[col])
        fh = v4.MOUND[col % 4][x % 16] + v4.FACE_ADD[Lv]
        for e, dens in enumerate(fade):
            y = ref - (fh + 1 + e)
            if 0 <= y < 224 and bld[y, x] and px[x, y][:3] == v4.BLD and dens > BAYER[y % 16, x % 16]:
                px[x, y] = face
        rh, rd = v4.RIM_HOT[Lv], v4.RIM_DIM[Lv]
        n = 2 if L == 'M' else 4
        for y in range(max(0, ref - rd - 2 * n - 1), ref):
            if not edge[y, x]:
                continue
            d = ref - y
            if rh and rh - n < d <= rh and (d + rh) % 2 == 1:
                px[x, y] = dim                                   # hot core breaks up into the dim rim
            elif rd - n < d <= rd and (d + rd) % 2 == 1 and d > rh:
                px[x, y] = face if d <= fh else v4.BLD + (255,)  # dim rim breaks up at its end
            elif rd < d <= rd + n and (d + rd) % 2 == 0:
                px[x, y] = dim
            elif L == 'H' and rd + n < d <= rd + 2 * n and (d - rd) % 4 == 0:
                px[x, y] = dim


# ---------------------------------------------------------------- output
CROP = (64, 112, 192, 224)        # GIF window, 128 x 112 px (same as round 1)
CELL = (64, 152, 192, 224)        # comparison cell, 128 x 72 px
SKYCELL = (0, 0, 128, 192)
PAGE = (20, 22, 28)
INK = (216, 220, 230)


def row_sheet(cells, cut, path, scale):
    cw, ch = (cut[2] - cut[0]) * scale, (cut[3] - cut[1]) * scale
    im = Image.new('RGB', (len(cells) * (cw + 8) + 8, ch + 26), PAGE)
    d = ImageDraw.Draw(im)
    for i, (lab, c) in enumerate(cells):
        x = 8 + i * (cw + 8)
        d.text((x, 5), lab if scale > 1 else lab.split(':')[0].split(' ')[0], fill=INK)
        im.paste(c.crop(cut).convert('RGB').resize((cw, ch), Image.NEAREST), (x, 20))
    im.save(path)


def scene(base, key, pal, frames, extra, f, masks, lev, L):
    hard = L in ('S0', 'S6')
    s = base.copy()
    if lev is not None:
        v4.cast_light(s, key, lev[f], masks) if hard else cast_light_d(s, key, lev[f], masks, L)
    ti = pal.img(frames[f])
    for x in range(0, 320, ti.width):
        s.alpha_composite(ti.crop((0, 0, min(ti.width, 320 - x), H)), (x, v4.HAZ_Y))
    if key == 'C':
        if hard:
            v4.put_lurker(s, f, extra['surf'][f], v4.LURK_X, v4.HAZ_Y)
        else:
            put_lurker_d(s, f, extra['surf'][f], v4.LURK_X, v4.HAZ_Y, L)
    return s


def rgbset(im):
    return set(map(tuple, np.array(im.convert('RGB')).reshape(-1, 3).tolist()))


def main():
    scratch = sys.argv[sys.argv.index('--scratch') + 1] if '--scratch' in sys.argv else None
    base0 = v4.base_scene()
    masks = v4.light_masks(base0)
    bases = {'S0': base0, 'S6': r1.dither_sky(base0, 6), 'M': sky2(base0, 'M'), 'H': sky2(base0, 'H')}
    n0 = len(rgbset(base0))
    report = ['sky ramp: S0/S6 3 colours, M/H %d colours; whole scene mock %d -> %d colours (M), %d (H)'
              % (len(SKY5), n0, len(rgbset(bases['M'])), len(rgbset(bases['H'])))]
    assert rgbset(bases['M']) - rgbset(base0) <= set(SKY5) and rgbset(bases['H']) - rgbset(base0) <= set(SKY5)
    row_sheet([(lab, bases[L]) for L, lab in LEVELS], SKYCELL, os.path.join(HERE, 'compare_sky_3x.png'), 3)
    row_sheet([(lab, bases[L]) for L, lab in LEVELS], SKYCELL, os.path.join(HERE, 'strip_sky_1x.png'), 1)
    lc = lava_coords()
    for key, name, pal, fn in v4.HAZ:
        if key not in SUBJ:
            continue
        frames0, extra = fn()
        tw = frames0[0].shape[1]
        used0 = set(np.unique(np.array(frames0)).tolist())
        lev = v4.light_levels(key, pal, frames0) if key in v4.LIGHT_W else None
        ys = [r1.spike_y(f, tw) if key == 'A' else None for f in range(NF)]
        yy, xx = np.mgrid[0:H, 0:tw]

        def coords(f, anchor=CRUST_ANCHOR, dbl=False):
            c = {}
            if key == 'A':
                c['steel'] = (xx, ys[f])
            if key == 'D' and anchor != 'grid':
                c['crust'] = lc[anchor][f]
            if dbl:
                c = {k: (np.hstack([X, X]), np.hstack([Y, Y])) for k, (X, Y) in c.items()}
            return c

        if key == 'D':       # crust anchor test: same art, three anchors, dither-only motion on crust pixels
            ids = [pal[k] for k in 'okKQH']
            for L in ('M', 'H'):
                for an in ('grid', 'plate', 'surf'):
                    fr = [dither2(frames0[f], key, L, coords(f, an)) for f in range(NF)]
                    chg, bl = crawl(fr, frames0, ids)
                    nd = int(sum((a != b).sum() for a, b in zip(fr, frames0)))
                    report.append('crust anchor %s %-5s: dither px per loop %5d, changes on still art %5d, blinks %5d' % (L, an, nd, chg, bl))
                    if scratch and L == 'H':
                        sh = Image.new('RGB', (128 * 4, 8 * 84), PAGE)
                        for f in range(8):
                            sh.paste(pal.img(fr[f]).crop((0, 0, 128, 20)).convert('RGB').resize((512, 80), Image.NEAREST), (0, f * 84))
                        sh.save(os.path.join(scratch, 'crust_%s.png' % an))
        cells = []
        for L, lab in LEVELS:
            if L == 'S0':
                frames = [fr.copy() for fr in frames0]
            elif L == 'S6':
                frames = [r1.dither(frames0[f], key, 6, ys[f]) for f in range(NF)]
            else:
                frames = [dither2(frames0[f], key, L, coords(f)) for f in range(NF)]
                # no new colours, transparency and silhouette unchanged
                assert set(np.unique(np.array(frames)).tolist()) <= used0 and len(pal.keys) <= 15, (key, L)
                assert all(((a == 0) == (b == 0)).all() for a, b in zip(frames, frames0)), (key, L)
                for f in (0, 5, 11):     # seamless in x: dithered alone = dithered inside a doubled strip
                    dbl = dither2(np.hstack([frames0[f]] * 2), key, L, coords(f, dbl=True))
                    assert (dbl[:, :tw] == frames[f]).all() and (dbl[:, tw:] == frames[f]).all(), (key, L, f)
            df = [int((frames[i] != frames[(i + 1) % NF]).sum()) for i in range(NF)]
            ncol = len(set(np.unique(np.array(frames)).tolist()) - {0})
            nd = int(sum((a != b).sum() for a, b in zip(frames, frames0)))
            report.append('%s %-6s %-2s unique tiles %3d of %3d raw, colours used %2d of %2d, dither px %6d (%.1f%% of opaque), px changed per step %d-%d, wrap %d'
                          % (key, name, L, v4.tile_count(frames), NF * (tw // 16) * (H // 16), ncol, len(pal.keys), nd,
                             100.0 * nd / max(1, int(sum((a != 0).sum() for a in frames0))), min(df[:-1]), max(df[:-1]), df[-1]))
            sc = [scene(bases[L], key, pal, frames, extra, f, masks, lev, L) for f in range(NF)]
            cells.append((lab, sc[2]))
            if L in ('M', 'H'):
                crop = [s.crop(CROP).resize(((CROP[2] - CROP[0]) * 4, (CROP[3] - CROP[1]) * 4), Image.NEAREST) for s in sc]
                v4.save_gif(os.path.join(HERE, 'anim_%s_%s_4x.gif' % (L, name)), crop, int(round(v4.VFRAMES[key] * 1000 / 60 / 10)) * 10)
                nv = tw // 64
                strip = Image.new('RGBA', (64 * NF, H * nv), (0, 0, 0, 0))
                for f in range(NF):
                    ti = pal.img(frames[f])
                    for vv in range(nv):
                        strip.alpha_composite(ti.crop((vv * 64, 0, vv * 64 + 64, H)), (f * 64, vv * H))
                strip.save(os.path.join(HERE, 'frames_%s_%s_1x.png' % (L, name)))
                if scratch:
                    for f in (2, 3, 4, 9):
                        sc[f].crop(CROP).convert('RGB').resize((512, 448), Image.NEAREST).save(os.path.join(scratch, 'f_%s_%s_%02d.png' % (name, L, f)))
        row_sheet(cells, CELL, os.path.join(HERE, 'compare_%s_3x.png' % name), 3)
        row_sheet(cells, CELL, os.path.join(HERE, 'strip_%s_1x.png' % name), 1)
    with open(os.path.join(HERE, 'numbers.txt'), 'w') as fh:
        fh.write('\n'.join(report) + '\n')
    print('\n'.join(report))
    write_html()


def write_html():
    sec = []
    notes = {
        'sky': 'Five shades instead of three, zenith near black to a violet horizon. M: three steps per edge over half of each band. H: five steps, bands meet.',
        'water': 'Ripple dashes between water shades; foam hard. Lurker: body shadow fades out in dashes, fin edge broken.',
        'lava': 'Checker blend in the melt, thinned in blobs; broken checker on the crust; the light on the buildings fades in ordered steps.',
        'spikes': 'Broken checker along every steel band of 2 px or more on blades, collars and sleeves, riding with the blade.',
    }
    for name in ('sky', 'water', 'lava', 'spikes'):
        g = ''
        if name != 'sky':
            g = ('<div class="row"><figure><img src="anim_M_%s_4x.gif" width="512" height="448" alt="M animation"><figcaption>M, animated, 4x</figcaption></figure>'
                 '<figure><img src="anim_H_%s_4x.gif" width="512" height="448" alt="H animation"><figcaption>H, animated, 4x</figcaption></figure></div>') % (name, name)
        sec.append('<section><h2>%s</h2><p>%s</p>'
                   '<div class="row"><figure><img src="compare_%s_3x.png" alt="%s at 3x"><figcaption>3x: S0, S6 round 1, M, H</figcaption></figure></div>'
                   '<div class="row"><figure><img src="strip_%s_1x.png" alt="%s at 1x"><figcaption>1x, true size: S0, S6, M, H</figcaption></figure></div>%s</section>'
                   % (name.capitalize(), notes[name], name, name, name, name, g))
    html = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Bubblegum Brawl: dither style 6, stronger levels</title><style>'
            'body{background:#14161c;color:#d8dce6;font-family:Helvetica,Arial,sans-serif;margin:24px;line-height:1.45}'
            'h1{font-size:22px;margin:0 0 4px}h2{font-size:18px;margin:36px 0 4px;border-top:1px solid #343846;padding-top:16px}'
            'p{margin:4px 0 12px;max-width:900px;color:#aab0c0}.warn{color:#ffd27a;font-weight:bold}'
            'img{image-rendering:pixelated;image-rendering:crisp-edges;display:block;max-width:none}'
            '.row{display:flex;gap:16px;overflow-x:auto;margin:0 0 12px}figure{margin:0}figcaption{font-size:13px;color:#8a90a2;margin-top:4px}'
            '</style></head><body><h1>Dither style 6 (mixed by material): stronger levels</h1>'
            '<p class="warn">View at 100 percent browser zoom. Any other zoom blurs or distorts the dither.</p>'
            '<p>S0 = hazards v4 without dither. S6 = round 1. M = medium-strong (half of each shade band). H = heavy (full band, extra steps). '
            'Fire is not part of this test. Numbers and the recommendation per material are in README.md.</p>'
            + ''.join(sec) + '</body></html>\n')
    with open(os.path.join(HERE, 'index.html'), 'w') as fh:
        fh.write(html)


if __name__ == '__main__':
    main()
