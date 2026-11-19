#!/opt/homebrew/bin/python3.14 -I
"""Gum Trip endless background planes (task T-B4b, step 1: art joins draft). Draft only, nothing here is game data.

Option A of thoughts/spot/2026-11-10-tb4b-endless-background-study.md: every parallax plane keeps its arena width
(far 336, midA 352, midB 368, near 384) and becomes a seamless ring; the sky (k 0) stays a still plane.

How the joins are made (no blending, no mirroring: the join is drawn by the same hand tables as the rest):
  far / midA / midB   the skyline is drawn on a canvas 64 px wider than the ring, with every building that reaches
                      over an end drawn a second time one ring width away (same seed, so the same art). The ring is
                      columns 0..W-1. The building tables are changed only at the right end so that the row of houses
                      closes (RING_TAB). The haze cluster strips are made periodic in W (periodic_pats).
  near                the roofs are drawn on a canvas whose rect and px wrap in x; the fifth roof is 4 px narrower so
                      that the ring has the same 4 px alley at the join as between the other roofs.
  clouds              the accepted strips already have empty end columns: taken as they are, shown as rings.

Run:  /opt/homebrew/bin/python3.14 -I draw_endless_planes.py [--nogif]
gt_base.py is a copy of ../2026-11-10-backgrounds-wide/draw_backgrounds_wide.py (the accepted look, palettes; one change:
RING_DX, so that a wrap copy of a far tower keeps the light side of its home position)
Nothing is imported from another draft folder.
"""
import os
import sys
from math import ceil, sin
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
from PIL import Image
import gt_base as B

H, W = B.H, B.W
PAD = 64                      # extra canvas to the right of a city ring: the continuation that must equal columns 0..63
WID = {'F': 336, 'A': 352, 'B': 368, 'N': 384}
KF = {'F': 4, 'A': 8, 'B': 12, 'N': 16, 'cb': 1, 'cf': 2}        # parallax factor in sixteenths of the trip scroll
ROWS = {'S': (0, 128), 'F': (48, 128), 'A': (80, 144), 'B': (112, 176), 'N': (128, 224)}
NAME = {'S': 'sky', 'F': 'far', 'A': 'midA', 'B': 'midB', 'N': 'near', 'cf': 'cloudsfront', 'cb': 'cloudsback'}
BG = (52, 56, 70)             # backdrop of the join proofs (not a game colour)

# ring building tables: the arena tables with the right end closed.
#   midA: the last house (338, 26 wide) ran 12 px past the ring end into the first house. Now a slim 16 px tower 336..351.
#   midB: the last two houses (336..359 and 356..383) ran 16 px past the end. Now one house 336..367.
#   far : unchanged, the row already ends at 336.
RING_TAB = {
    'F': list(B.FAR),
    'A': list(B.MIDA[:-1]) + [(336, 16, 98, 'step', 'deco')],
    'B': list(B.MIDB[:-2]) + [(336, 32, 129, 'tank', 'apt')],
}
RING_NB4 = (324, 380, 158, 15, 'block')       # near: fifth roof 324..379 (arena: 324..383)


def periodic_pats(pw, cw):
    """Hand cluster strips of the haze edge, cut to the ring width and repeated. Where the cut leaves a run of one or
    two pixels at an end, the run is given to its neighbour across the join (no sliver at the join)."""
    out = []
    for P in B.BANDPAT:
        Q = P[:, :pw].copy()
        for r in range(Q.shape[0]):
            a, b = Q[r, pw - 1], Q[r, 0]
            if a == b:
                continue
            ne = 1
            while ne < pw and Q[r, pw - 1 - ne] == a:
                ne += 1
            ns = 1
            while ns < pw and Q[r, ns] == b:
                ns += 1
            if ne < 3:
                Q[r, pw - ne:] = b
            elif ns < 3:
                Q[r, :ns] = a
        out.append(np.tile(Q, (1, 2))[:, :cw])
    return out


def ring_city(key, f):
    """city_plane of the base script on a canvas of W + PAD with wrap copies. Returns the full canvas (role indices)."""
    st = B.SPEC[key]
    R = B.Rl(key)
    pw = WID[key]
    cw = pw + PAD + 32          # 32 spare columns: nothing that is compared touches the canvas edge
    tab = RING_TAB[key]
    cv = B.Cv(H, cw)
    cv.rect(0, st.opq - 3, cw, st.y1, R.w2)
    okey = (lambda i: -tab[i][2]) if key != 'F' else (lambda i: (i * 7) % 5)
    items = [(i, dx) for i in range(len(tab)) for dx in (0, pw, -pw)
             if tab[i][0] + dx + tab[i][1] > -64 and tab[i][0] + dx < cw + 64]
    items.sort(key=lambda it: okey(it[0]))
    for i, dx in items:
        x, w, top, kind, ft = tab[i]
        x += dx
        B.RING_DX = dx
        seed = ord(key) * 100 + i
        B.furnish(cv, R, st, x, w, top, kind, seed, f, st.y0, ft)
        B.building(cv, R, st, x, w, top, st.y1, seed, f, ft=ft, kind=kind)
        if kind == 'sign':
            B.chevrons(cv, R, x + w - 12, top + 6, f)
    ya, yb, mx = st.haze
    yy, xx = B.grid(H, cw)
    B.RING_DX = 0
    pats = periodic_pats(pw, cw)
    for b in st.hz_on:
        base = B.rid(key + '.' + b)
        t = np.clip((yy - ya) / (yb - ya), 0, 1)
        if key == 'F':
            B.clus(cv, cv.a == base, B.band(t, 0.25, 0.5), base, R.hz, 3, pats=pats)
        else:
            B.clus(cv, cv.a == base, B.band(t, 0.3, 0.45), base, R.hz, 1 if key == 'A' else 6, pats=pats)
    cv.a[:st.y0] = 0
    cv.a[st.y1:] = 0
    assert (cv.a[st.opq:st.y1] > 0).all(), key
    return cv.a


BaseCv = B.Cv


class WrapCv(BaseCv):
    """Canvas whose rect and px wrap in x (the near ring)."""

    def rect(s, x0, y0, x1, y1, c):
        x0, x1 = int(x0), int(x1)
        if x1 <= x0:
            return
        if x0 < 0:
            BaseCv.rect(s, x0 + s.w, y0, s.w, y1, c)
            x0 = 0
        if x1 > s.w:
            BaseCv.rect(s, 0, y0, x1 - s.w, y1, c)
            x1 = s.w
        BaseCv.rect(s, x0, y0, x1, y1, c)

    def px(s, x, y, c):
        BaseCv.px(s, int(x) % s.w, y, c)


def ring_near():
    keep_cv, keep_nb = B.Cv, B.NB[4]
    B.Cv, B.NB[4] = WrapCv, RING_NB4
    try:
        return [B.near_plane(f).a for f in range(8)]
    finally:
        B.Cv, B.NB[4] = keep_cv, keep_nb


# ---------------------------------------------------------------- measures
def col_steps(a):
    """d[x] = rows in which column x differs from column x+1 (ring: the last entry is the join W-1 -> 0)."""
    return (a != np.roll(a, -1, 1)).sum(0)


def seam(a):
    d = col_steps(a)
    j = int(d[-1])
    inner = d[:-1]
    return j, int((inner >= j).sum()), int(np.median(inner)), int(inner.max())


def tile_set(frames, y0, y1):
    seen = set()
    w = frames[0].shape[1]
    for fr in frames:
        for ty in range(y0 // 16, ceil(y1 / 16)):
            for tx in range(w // 16):
                t = fr[ty * 16:ty * 16 + 16, tx * 16:tx * 16 + 16].tobytes()
                if any(t):
                    seen.add(t)
    return seen


def changed_cols(ring, arena):
    w = min(ring.shape[1], arena.shape[1])
    c = np.nonzero((ring[:, :w] != arena[:, :w]).any(0))[0]
    return list(c) + list(range(w, ring.shape[1]))


def runs(cols):
    out, cols = [], sorted(cols)
    for c in cols:
        if out and c == out[-1][1] + 1:
            out[-1][1] = c
        else:
            out.append([c, c])
    return ', '.join('%d' % a if a == b else '%d..%d' % (a, b) for a, b in out) or 'none'


def trip_lines(planes, trim=True):
    """Scenery sprites per 16-line band for a ring. planes: back to front, (key, frames (n,H,w)).
    Ring-valid trim: a tile row of a plane is dropped only where a plane in front is opaque across its whole ring in
    every frame. A column sprite spans its first to its last kept tile."""
    full = {}
    for k, fr in planes:
        op = fr > 0
        full[k] = {b for b in range(14) if op[:, b * 16:b * 16 + 16].all()}
    line = np.zeros(14, int)
    for i, (k, fr) in enumerate(planes):
        hidden = set().union(*[full[k2] for k2, _ in planes[i + 1:]]) if trim else set()
        op = (fr > 0).any(0)
        for c in range(fr.shape[2] // 16):
            bs = [b for b in range(14) if b not in hidden and op[b * 16:b * 16 + 16, c * 16:c * 16 + 16].any()]
            if bs:
                line[bs[0]:bs[-1] + 1] += 1
    return line


# ---------------------------------------------------------------- composition
def ring_view(a, off):
    return np.roll(a, -(off % a.shape[1]), 1)[:, :W]


def trip_frame(md, ring, haz, lev, s):
    """320x224 screen at trip scroll s px (1 px per 60 Hz frame, so s is also the frame count)."""
    f8, f4 = (s // 12) % 8, (s // 12) % 4
    hz16 = (s * 1000 // 60 // md.M['ms']) % 16
    lut = md.luts[0]
    d = np.zeros((H, W, 3), np.uint8)
    d[:] = lut[B.rid('N.w1')]
    B.over(d, md.sky[f4].a, lut)
    if md.mood == 'storm':
        B.over(d, md.beam[f8].a, lut)
    else:
        B.over(d, B.wrap_strip(md.cb[f4].a, -(s * KF['cb'] // 16)), lut)
        B.over(d, B.wrap_strip(md.cf[f4].a, -(s * KF['cf'] // 16)), lut)
    B.over(d, ring_view(ring['F'][f8], s * KF['F'] // 16), lut)
    if md.mood != 'storm':
        B.over(d, md.ship[f8].a, lut, 236 - s // 10, 54 + round(2 * sin(s / 48)))
    B.over(d, ring_view(ring['A'][f8], s * KF['A'] // 16), lut)
    B.over(d, ring_view(ring['B'][f8], s * KF['B'] // 16), lut)
    n = ring_view(ring['N'][f8], s)
    lm = ring_view(B.level_map(lev[hz16]), s)
    m = n > 0
    d[m] = md.luts[lm[m], n[m]]
    hz = np.roll(haz[hz16], -(s % 64), 1)[:, :W]
    hm = hz[..., 3] > 0
    d[B.HAZ_Y:][hm] = hz[..., :3][hm]
    if md.mood == 'storm':
        B.over(d, md.rain[(s * 1000 // 60 // 70) % 8].a, lut)
    return d


def trip_hazard(md):
    """One variant only, period 64 (study section 5)."""
    fn = {'water': 'frames_M_water_1x.png', 'lava': 'frames_M_lava_1x.png', 'spikes': 'frames_H_spikes_1x.png'}[md.M['hazard']]
    im = np.array(Image.open(os.path.join(B.HAZDIR, fn)).convert('RGBA'))
    return [np.tile(im[0:32, f * 64:f * 64 + 64], (1, 6, 1)) for f in range(16)]


def rgb_of(a, lut, bg):
    out = np.zeros(a.shape + (3,), np.uint8)
    out[:] = bg
    out[a > 0] = lut[a[a > 0]]
    return out


def join_png(a, lut, path):
    """The plane twice side by side at 2x: the join is the centre line, marked by ticks in the margins only."""
    rgb = rgb_of(np.concatenate([a, a], 1), lut, BG)
    big = B.up(rgb, 2)
    m = 10
    out = np.zeros((big.shape[0] + 2 * m, big.shape[1], 3), np.uint8)
    out[:] = (24, 26, 32)
    out[m:-m] = big
    cx = big.shape[1] // 2
    out[1:m - 2, cx - 1:cx + 1] = (255, 220, 90)
    out[-m + 2:-1, cx - 1:cx + 1] = (255, 220, 90)
    Image.fromarray(out, 'RGB').save(path)


GIF_STEP, GIF_MS, GIF_N = 3, 50, 192          # 3 px per 50 ms = 60 px per second = 1.0 px per 60 Hz frame; 9.6 s


def main():
    out, html = [], []
    P = out.append
    ring, m2, arena = {}, {}, {}
    for k in 'FAB':
        full = [ring_city(k, f) for f in range(8)]
        pw = WID[k]
        m2[k] = int(np.any([(c[:, pw:pw + PAD] != c[:, :PAD]).any(0) for c in full], 0).sum())
        ring[k] = [c[:, :pw] for c in full]
        arena[k] = [B.city_plane(k, f).a for f in range(8)]
    arena['N'] = [B.near_plane(f).a for f in range(8)]
    ring['N'] = ring_near()
    assert B.NB[4][1] == 384 and B.Cv is not WrapCv

    P('Gum Trip endless planes (T-B4b step 1). Ring = arena plane at its arena width with a redrawn join.')
    P('Seam measure 1 (all rings): rows in which the last column differs from the first column (the pair that touches at the')
    P('  wrap), next to the same count for every interior neighbour pair of the plane (how many interior pairs are at least')
    P('  as different, median, largest). A join at a house edge is as different as the other house edges, never 0.')
    P('Seam measure 2 (far, midA, midB): the skyline is drawn 64 px past the ring end; count of those 64 pixel columns, over')
    P('  all 8 animation frames, that differ from columns 0..63 of the ring. 0 = the picture continues across the join')
    P('  exactly as it continues anywhere else.')
    P('')
    P('== ring art (role indices, the same for the three moods; a mood is a palette set)')
    recs = {}
    tot_ring = tot_arena = tot_new = 0
    for k in 'FABN':
        y0, y1 = ROWS[k]
        rs, as_ = tile_set(ring[k], y0, y1), tile_set(arena[k], y0, y1)
        j, ge, med, mx = seam(ring[k][0][y0:y1])
        ja = seam(arena[k][0][y0:y1])[0]
        ch = changed_cols(ring[k][0][y0:y1], arena[k][0][y0:y1])
        ch8 = sorted(set().union(*[changed_cols(ring[k][f][y0:y1], arena[k][f][y0:y1]) for f in range(8)]))
        recs[k] = dict(w=WID[k], tiles=len(rs), arena=len(as_), new=len(rs - as_), gone=len(as_ - rs), j=j, ja=ja, ge=ge, med=med, mx=mx,
                       m2=m2.get(k), ch=runs(ch8))
        tot_ring += len(rs)
        tot_arena += len(as_)
        tot_new += len(rs - as_)
        P('  %-5s loop %3d px (%2d columns, k %2d/16, repeats every %6.1f px of scroll = %4.1f s at 1.0 px/frame)'
          % (NAME[k], WID[k], WID[k] // 16, KF[k], WID[k] * 16 / KF[k], WID[k] * 16 / KF[k] / 60))
        P('        unique 16x16 tiles %3d (arena plane %3d; %d not in the arena set, %d arena tiles no longer used)'
          % (len(rs), len(as_), len(rs - as_), len(as_ - rs)))
        P('        seam 1: join differs in %d of %d rows (arena plane before: %d); %d of %d interior pairs differ in at least as many rows; interior median %d, largest %d'
          % (j, y1 - y0, ja, ge, WID[k] - 1, med, mx))
        P('        seam 2: %s' % ('%d of %d columns differ' % (m2[k], PAD) if k in m2 else 'not measured (drawn on a wrapping canvas, see README)'))
        P('        columns that differ from the arena plane (any of 8 frames): %s' % runs(ch8))
    P('  totals for far, midA, midB, near: ring %d unique tiles, arena %d; %d ring tiles are not in the arena set' % (tot_ring, tot_arena, tot_new))
    P('  ROM figure: the study gives none ("ROM tile budget not read"); the build plan says ROM space is not the limit.')
    P('    If the arena adopts the ring planes (its two ends change slightly), the cost is %+d tiles.' % (tot_ring - tot_arena))
    P('    If the trip keeps its own copy of the four planes next to the arena planes, the cost is +%d tiles (only the tiles not shared).' % tot_new)

    mds = {}
    for mood in ('moon', 'storm', 'dusk'):
        md = B.Mood(mood)
        md.prep()
        mds[mood] = md
        lut0, lut3 = md.luts[0], md.luts[3]
        P('')
        P('== mood %s: %s' % (mood, md.M['title']))
        rows = []
        sky = np.stack([c.a for c in md.sky])
        pp = B.pack_palettes([c[:128] for c in sky], lut0)
        P('  sky          still plane 320 px, k 0, not a ring (never crosses a join); unique tiles %d; palettes %d, colours %s (%d distinct)'
          % (len(tile_set(sky, 0, 128)), pp[0], pp[1], pp[2]))
        rows.append(('sky', '320, still', len(tile_set(sky, 0, 128)), '%d (%d distinct)' % (pp[0], pp[2]), 'not a ring', '-', None))
        for k in 'FABN':
            y0, y1 = ROWS[k]
            r = recs[k]
            lut = lut3 if k == 'N' else lut0
            pp = B.pack_palettes([c[y0:y1] for c in ring[k]], lut)
            assert max(pp[1]) <= 15
            rgb = rgb_of(ring[k][0][y0:y1], lut, B.TRANSP)
            assert not ((rgb == B.TRANSP).all(2) & (ring[k][0][y0:y1] > 0)).any()
            Image.fromarray(rgb, 'RGB').save(os.path.join(HERE, 'plane_%s_%s_1x.png' % (mood, NAME[k])))
            jp = 'join_%s_%s_2x.png' % (mood, NAME[k])
            join_png(ring[k][0][y0:y1], lut, os.path.join(HERE, jp))
            P('  %-12s loop %3d px; unique tiles %3d; palettes %d, colours %s (%d distinct); seam 1: %d of %d rows (before %d); seam 2: %s'
              % (NAME[k], r['w'], r['tiles'], pp[0], pp[1], pp[2], r['j'], y1 - y0, r['ja'], '%d of %d columns' % (r['m2'], PAD) if r['m2'] is not None else 'n/a'))
            rows.append((NAME[k], '%d' % r['w'], r['tiles'], '%d (%d distinct)' % (pp[0], pp[2]),
                         '%d of %d rows (before %d); %d of %d interior pairs as large' % (r['j'], y1 - y0, r['ja'], r['ge'], r['w'] - 1),
                         '%d of %d' % (r['m2'], PAD) if r['m2'] is not None else 'n/a', jp))
        if mood != 'storm':
            for k, cvs, (y0, y1) in (('cf', md.cf, (16, 48)), ('cb', md.cb, (48, 80))):
                fr = [c.a for c in cvs]
                a = fr[0][y0:y1]
                j, ge, med, mx = seam(a)
                pp = B.pack_palettes([c[y0:y1] for c in fr], lut0)
                jp = 'join_%s_%s_2x.png' % (mood, NAME[k])
                join_png(a, lut0, os.path.join(HERE, jp))
                emp = int((a[:, 0] > 0).sum() + (a[:, -1] > 0).sum())
                P('  %-12s loop %3d px (accepted strip, unchanged, k %d/16); unique tiles %3d; palettes %d, colours %s; seam 1: %d of %d rows, opaque pixels in the two end columns: %d'
                  % (NAME[k], a.shape[1], KF[k], len(tile_set(fr, y0, y1)), pp[0], pp[1], j, y1 - y0, emp))
                rows.append((NAME[k], '%d (unchanged)' % a.shape[1], len(tile_set(fr, y0, y1)), '%d (%d distinct)' % (pp[0], pp[2]),
                             '%d of %d rows; end columns empty' % (j, y1 - y0), 'n/a', jp))
            P('  airship      screen-space object, drifts right to left at 0.1 px/frame, not a ring (accepted art, unchanged)')
        else:
            P('  beams, rain  screen-space, not rings (accepted art, unchanged)')
        # sprites per scanline
        planes = [('S', sky)] + [(k, np.stack(ring[k])) for k in 'FABN']
        ln, ln0 = trip_lines(planes), trip_lines(planes, trim=False)
        wb = int(ln.argmax())
        P('  scenery sprites per 16 lines, ring-valid trim: %s' % ' '.join('%d' % v for v in ln))
        P('    worst %d at lines %d..%d; with the gameplay reserve 24: %d of 90 (SB_LIMIT), hardware limit 96. Study: 65 and 89.'
          % (ln.max(), wb * 16, wb * 16 + 15, ln.max() + 24))
        P('    lines 192..223 with the 24 hazard strip sprites and the reserve: %d' % (ln[12:].max() + 48))
        P('    empty-row trim only (no occlusion trim): worst %d at lines %d..%d (study: 82)' % (ln0.max(), int(ln0.argmax()) * 16, int(ln0.argmax()) * 16 + 15))
        P('    not counted: stars, sky objects, clouds, airship, beams, rain, moving hazards (2 or 3 sprites each)')
        gp = 'trip_%s_3x.gif' % mood
        if '--nogif' not in sys.argv:
            haz = trip_hazard(md)
            lev = B.light_levels(haz, md.M['lbase'], md.M['lpc'])
            frs = [trip_frame(md, ring, haz, lev, g * GIF_STEP) for g in range(GIF_N)]
            nc = B.save_gif(os.path.join(HERE, gp), frs, GIF_MS)
            Image.fromarray(B.up(frs[0], 2), 'RGB').save(os.path.join(HERE, 'still_%s_2x.png' % mood))
            P('  gif: %d frames of %d ms = %.1f s, %d px of scroll, %d colours%s, %.1f MB'
              % (GIF_N, GIF_MS, GIF_N * GIF_MS / 1000, GIF_N * GIF_STEP, nc, '' if nc <= 255 else ' (reduced to 255)',
                 os.path.getsize(os.path.join(HERE, gp)) / 1e6))
        html.append((mood, md.M['title'], gp, rows, ln))
    P('')
    P('speeds in the GIFs, px per 60 Hz frame at the capped trip speed 1.0: sky 0, clouds back 0.0625, clouds front 0.125, far 0.25,')
    P('  midA 0.5, midB 0.75, near 1.0, hazard strip 1.0 (one variant, period 64), airship 0.1 leftward in screen space.')
    P('  GIF timing: %d px of scroll per %d ms frame (20 frames per second), so the speed is true and the motion is coarser than on hardware.' % (GIF_STEP, GIF_MS))
    print('\n'.join(out))
    if '--nogif' not in sys.argv:
        open(os.path.join(HERE, 'numbers.txt'), 'w').write('\n'.join(out) + '\n')
        write_html(html, recs, (tot_ring, tot_arena, tot_new))


def write_html(html, recs, tot):
    h = ['<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Gum Trip endless planes</title><style>',
         'body{background:#1a1c21;color:#d9dce3;font-family:Helvetica,Arial,sans-serif;font-size:15px;line-height:1.45;margin:24px 32px}',
         'h1{font-size:24px;font-weight:600;margin:0 0 8px}h2{font-size:19px;font-weight:600;margin:40px 0 10px;border-top:1px solid #3a3e48;padding-top:18px}',
         'h3{font-size:15px;font-weight:600;margin:22px 0 6px;color:#aeb4c2}',
         'img{image-rendering:pixelated;max-width:100%;height:auto;display:block;border:1px solid #3a3e48}',
         'table{border-collapse:collapse;margin:8px 0 14px}td,th{border:1px solid #3a3e48;padding:4px 10px;text-align:left;font-variant-numeric:tabular-nums}',
         'th{background:#252830;font-weight:600}p{max-width:980px;margin:6px 0}.cap{color:#aeb4c2;margin:14px 0 4px}',
         '</style></head><body>',
         '<h1>Gum Trip endless background planes</h1>',
         '<p>Draft for task T-B4b, step 1. Each parallax plane keeps its arena width and is redrawn at the join so that its right end '
         'continues into its left end. The sky does not move. Scroll is to the right at the capped speed of 1.0 pixel per frame.</p>',
         '<p>Speeds in pixels per frame: sky 0, clouds back 0.0625, clouds front 0.125, far 0.25, mid A 0.5, mid B 0.75, near 1.0, '
         'hazard strip 1.0, airship 0.1 leftward. The animations run at 20 frames per second with 3 pixels of scroll per frame: '
         'the speed is true, the motion is coarser than on the machine. They are 9.6 seconds long and jump back at the end '
         '(the planes repeat at different distances, so no short animation closes).</p>',
         '<p>Seam measure 1: rows in which the last and the first pixel column of a plane differ, compared with all neighbouring '
         'column pairs inside the plane. Seam measure 2 (far, mid A, mid B): the skyline is drawn 64 pixels past the end of the ring; '
         'count of those columns that differ from the first 64 columns of the ring, over all 8 animation frames.</p>',
         '<p>Unique 16 x 16 tiles for far, mid A, mid B and near together: ring %d, arena %d; %d ring tiles are not in the arena set. '
         'Columns changed against the arena planes: far %s; mid A %s; mid B %s; near %s.</p>'
         % (tot[0], tot[1], tot[2], recs['F']['ch'], recs['A']['ch'], recs['B']['ch'], recs['N']['ch'])]
    for mood, title, gp, rows, ln in html:
        h.append('<h2>%s</h2>' % title)
        h.append('<img src="%s" width="960" height="672" alt="%s trip scroll">' % (gp, mood))
        h.append('<table><tr><th>Plane</th><th>Loop width</th><th>Unique tiles</th><th>Palettes (colours)</th><th>Seam measure 1</th><th>Seam measure 2</th></tr>')
        for n, w, t, c, s1, s2, jp in rows:
            h.append('<tr><td>%s</td><td>%s</td><td>%d</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (n, w, t, c, s1, s2))
        h.append('</table>')
        h.append('<p>Scenery sprites per 16 lines from the top (ring-valid trim): %s. Worst %d, with the gameplay reserve of 24: %d of 90.</p>'
                 % (' '.join('%d' % v for v in ln), ln.max(), ln.max() + 24))
        for n, w, t, c, s1, s2, jp in rows:
            if jp:
                h.append('<p class="cap">%s, tiled twice at 2x. The join is at the centre, under the yellow ticks.</p><img src="%s" alt="%s join">' % (n, jp, n))
    h.append('<h2>All numbers</h2><p>See numbers.txt and README.md in this folder.</p></body></html>')
    open(os.path.join(HERE, 'index.html'), 'w').write('\n'.join(h) + '\n')


if __name__ == '__main__':
    main()
