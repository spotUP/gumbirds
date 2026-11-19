"""Rim redraw of the accepted GUMBIRDS logo: the outer rim gets its own palette index (11), everything else keeps its index.
Run: /opt/homebrew/bin/python3.14 -I redraw.py            (writes every output of this folder)
     /opt/homebrew/bin/python3.14 -I redraw.py explore DIR (variant sheet and diagnostics into DIR, nothing written here)

Input: the accepted frames, read from ../2026-11-10-hud-title-final/logo_a_frames_1x.png (10 frames of 336x128, body layer)
and the free pieces (16x16 tiles with positions) taken from that folder's generator by import (frames() only; nothing is
written there). Measure code (sky(), place(), shift(), analyse(), lum(), ratio(), up()) is copied from
../2026-11-10-logo-outline-moods/compose_moods.py; analyse() only lost its printing.
"""
import importlib.util
import json
import os
import sys
from collections import Counter
import numpy as np
from PIL import Image

sys.dont_write_bytecode = True   # the import of the generator must not leave a cache in its folder
HERE = os.path.dirname(os.path.abspath(__file__))
DR = os.path.dirname(HERE)
LOGO = os.path.join(DR, '2026-11-10-hud-title-final')
WIDE = os.path.join(DR, '2026-11-10-backgrounds-wide')
LX, LY = -13, -8
KEY = (255, 0, 255)
FH = 128
STILL_F = 3
TIMES = [110, 110, 110, 110, 110, 260, 90, 90, 110, 200]
CROP = 136

# index roles. 0..10 are the accepted logo palette, 11 is new.
ROLES = ['transparent', 'keyline plum', 'gum deep', 'gum mid', 'gum light', 'warm cream highlight', 'specular white',
         'under shadow', 'inner line and counters (was: outer line)', 'cool rim light', 'violet rim step', 'outer rim (new)']
BASE = [KEY, (90, 16, 115), (165, 33, 156), (255, 82, 181), (255, 156, 214), (255, 231, 189), (255, 255, 255), (24, 8, 49), (8, 8, 24),
        (99, 222, 255), (115, 90, 231)]
K, SH, LINE, RIM = 0, 7, 8, 11
# per mood: rim (index 11) and shadow (index 7). Dusk keeps both as accepted, so the logo is pixel identical there.
MOODPAL = {
    'dusk': {RIM: (8, 8, 24), SH: (24, 8, 49)},
    'storm': {RIM: (160, 200, 184), SH: (0, 0, 0)},
    'moon': {RIM: (160, 192, 248), SH: (0, 0, 16)},
}
START = {'storm': {RIM: (160, 200, 184), SH: (0, 0, 0)}, 'moon': {RIM: (160, 192, 248), SH: (0, 0, 16)}}

VARIANT = 'A'          # A: 4-neighbour 1 px, B: 8-neighbour 1 px, C: full line thickness (2 px)
POCKET_MIN = 8         # an enclosed see-through hole smaller than this many pixels gets no rim (it would be a pale speck)

# hand corrections on top of the rule. (frames, x, y, new index, why). x, y in frame coordinates (336x128). frames None = all.
SPECK_MAX = 4          # a rim run this short goes back to the dark line
HAND = []


def palette(mood):
    p = list(BASE) + [MOODPAL[mood][RIM]]
    p[SH] = MOODPAL[mood][SH]
    return p


def lum(c):
    v = np.asarray(c, float) / 255
    v = np.where(v <= 0.03928, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)
    return v @ np.array([0.2126, 0.7152, 0.0722])


def ratio(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = np.maximum(la, lb), np.minimum(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def sky(mood):
    a = np.asarray(Image.open(os.path.join(WIDE, 'cams_%s_2x.png' % mood)).convert('RGB'))
    return a[20:468:2, 8:648:2].copy()


def place(logo):
    """Return full-screen RGB layer and opaque mask for the logo at its title position."""
    lay = np.zeros((224, 320, 3), np.uint8)
    m = np.zeros((224, 320), bool)
    h, w = logo.shape[:2]
    x0, y0, x1, y1 = max(LX, 0), max(LY, 0), min(LX + w, 320), min(LY + h, 224)
    s = logo[y0 - LY:y1 - LY, x0 - LX:x1 - LX]
    sm = (s != KEY).any(2)
    lay[y0:y1, x0:x1] = s
    m[y0:y1, x0:x1] = sm
    return lay, m


def shift(m, dy, dx):
    r = np.zeros_like(m)
    H, W = m.shape
    r[max(dy, 0):H + min(dy, 0), max(dx, 0):W + min(dx, 0)] = m[max(-dy, 0):H + min(-dy, 0), max(-dx, 0):W + min(-dx, 0)]
    return r


def analyse(bg, lay, m):
    """Copied from compose_moods.py. Returns composite, mean pair contrast, min pair contrast, weak-edge % (<1.5), % under 1.2,
    edge pixel count."""
    comp = bg.copy()
    comp[m] = lay[m]
    n4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    edge = np.zeros_like(m)
    for dy, dx in n4:
        nb = shift(m, dy, dx)
        valid = shift(np.ones_like(m), dy, dx)
        edge |= m & ~nb & valid
    per_edge, pairs = [], []
    ys, xs = np.nonzero(edge)
    for y, x in zip(ys, xs):
        cs = []
        for dy, dx in n4:
            yy, xx = y + dy, x + dx
            if 0 <= yy < 224 and 0 <= xx < 320 and not m[yy, xx]:
                r = float(ratio(lay[y, x], bg[yy, xx]))
                cs.append(r)
                pairs.append(r)
        if cs:
            per_edge.append(np.mean(cs))
    per_edge = np.array(per_edge)
    pairs = np.array(pairs)
    return comp, float(pairs.mean()), float(pairs.min()), 100 * float((per_edge < 1.5).mean()), 100 * float((per_edge < 1.2).mean()), len(per_edge)


def up(a, k):
    return Image.fromarray(a).resize((a.shape[1] * k, a.shape[0] * k), Image.NEAREST)


# ------------------------------------------------------------------ input
def load():
    a = np.asarray(Image.open(os.path.join(LOGO, 'logo_a_frames_1x.png')).convert('RGB')).astype(int)
    code = a[..., 0] * 65536 + a[..., 1] * 256 + a[..., 2]
    idx = np.full(code.shape, 255, np.uint8)
    for i, c in enumerate(BASE):
        idx[code == c[0] * 65536 + c[1] * 256 + c[2]] = i
    assert (idx != 255).all(), 'a pixel is not one of the 10 colours or the key'
    frames = [idx[i * FH:(i + 1) * FH].copy() for i in range(10)]
    spec = importlib.util.spec_from_file_location('gen', os.path.join(LOGO, 'draw_hud_title_final.py'))
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    fr = gen.frames()
    _, ox, oy = gen.best_offset()
    pieces = []
    for f, (body, pcs) in enumerate(fr):
        L = gen.shifted(body, ox, oy)[:FH, :336]
        assert (L == frames[f]).all(), 'generator body differs from the accepted strip, frame %d' % f
        # piece position in frame (layer) coordinates
        pieces.append([(np.asarray(t, np.uint8).copy(), px + ox, py + oy) for t, px, py in pcs])
    assert (gen.A_X - gen.PADC - ox, gen.A_Y - gen.PADC - oy) == (LX, LY)
    return frames, pieces


# ------------------------------------------------------------------ the rule
def components(mask):
    lab = np.zeros(mask.shape, int)
    n = 0
    for y, x in zip(*np.nonzero(mask)):
        if lab[y, x]:
            continue
        n += 1
        st = [(y, x)]
        lab[y, x] = n
        while st:
            cy, cx = st.pop()
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                yy, xx = cy + dy, cx + dx
                if 0 <= yy < mask.shape[0] and 0 <= xx < mask.shape[1] and mask[yy, xx] and not lab[yy, xx]:
                    lab[yy, xx] = n
                    st.append((yy, xx))
    return lab, n


def outside_mask(I):
    """Key pixels that count as outside: everything the sky shows through, except enclosed holes under POCKET_MIN pixels."""
    key = np.pad(I == K, 1, constant_values=True)
    lab, n = components(key)
    out = np.zeros_like(key)
    pockets = []
    for i in range(1, n + 1):
        c = lab == i
        if c[0, 0] or c.sum() >= POCKET_MIN:
            out |= c
        if not c[0, 0]:
            ys, xs = np.nonzero(c)
            pockets.append((int(c.sum()), int(xs.min()) - 1, int(ys.min()) - 1, int(xs.max()) - 1, int(ys.max()) - 1))
    return out[1:-1, 1:-1], pockets


def near(mask, n8, reach=1):
    r = mask.copy()
    for _ in range(reach):
        s = r.copy()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if (dy or dx) and (n8 or not (dy and dx)):
                    s |= shift(r, dy, dx)
        r = s
    return r


def rim_rule(I, variant=None, outside=None):
    variant = variant or VARIANT
    if outside is None:
        outside, _ = outside_mask(I)
    line = I == LINE
    if variant == 'A':
        rim = line & near(outside, False)
    elif variant == 'B':
        rim = line & near(outside, True)
    else:
        rim = line & near(outside, True, 2)
    R = I.copy()
    R[rim] = RIM
    return R


def cleanup(R):
    """Rule-based join fixes, same on every frame. Returns (R, list of (x, y, old, new, kind))."""
    log = []
    n8 = [(dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx]
    H, W = R.shape
    P = np.pad(R, 1)
    # 1. a rim run of SPECK_MAX pixels or fewer (8-connected) is a pale speck, not an edge: back to the dark line.
    #    These sit where the drop shadow covers most of the outline and leaves 1 to 4 line pixels open to the sky.
    m = R == RIM
    seen = np.zeros_like(m)
    for y, x in zip(*np.nonzero(m)):
        if seen[y, x]:
            continue
        st = [(y, x)]
        seen[y, x] = True
        c = []
        while st:
            cy, cx = st.pop()
            c.append((cx, cy))
            for dy, dx in n8:
                yy, xx = cy + dy, cx + dx
                if 0 <= yy < H and 0 <= xx < W and m[yy, xx] and not seen[yy, xx]:
                    seen[yy, xx] = True
                    st.append((yy, xx))
        if len(c) <= SPECK_MAX:
            log += [(int(cx), int(cy), RIM, LINE, 'pale speck of %d px' % len(c)) for cx, cy in c]
    for x, y, _, new, _ in log:
        R[y, x] = new
    return R, log


def redraw(I):
    R = rim_rule(I)
    R, log = cleanup(R)
    return R, log


def apply_hand(R, f):
    done = []
    for fs, x, y, new, why in HAND:
        if fs is None or f in fs:
            if R[y, x] != new:
                done.append((x, y, int(R[y, x]), new, why))
                R[y, x] = new
    return done


def piece_redraw(t):
    """A free piece is a loose gum blob on the sky: its whole exposed line is rim, by the same rule."""
    P = np.pad(t, 2)
    R = rim_rule(P, outside=(P == K))
    return R[2:-2, 2:-2]


# ------------------------------------------------------------------ counting
def tiles_idx(L, uniq, flips=True):
    for ty in range(0, L.shape[0], 16):
        for tx in range(0, L.shape[1], 16):
            t = L[ty:ty + 16, tx:tx + 16]
            if t.any():
                uniq.add(min(t.tobytes(), t[:, ::-1].tobytes(), t[::-1].tobytes(), t[::-1, ::-1].tobytes()) if flips else t.tobytes())


def tile_counts(frames, pieces):
    s, b, p = set(), set(), set()
    tiles_idx(frames[STILL_F], s)
    for L in frames:
        tiles_idx(L, b)
    for pcs in pieces:
        for t, _, _ in pcs:
            tiles_idx(t, p)
    return len(s), len(b), len(p), len(b | p)


def rgb(I, pal):
    return np.array(pal, np.uint8)[I]


def layer(I, pcs):
    """Frame with its free pieces drawn in (frame coordinates), as the title shows it."""
    L = np.zeros((max(FH, 160), 336), np.uint8)
    L[:FH] = I
    for t, px, py in pcs:
        y0, x0 = max(py, 0), max(px, 0)
        y1, x1 = min(py + 16, L.shape[0]), min(px + 16, L.shape[1])
        if y1 <= y0 or x1 <= x0:
            continue
        s = t[y0 - py:y1 - py, x0 - px:x1 - px]
        d = L[y0:y1, x0:x1]
        d[s != 0] = s[s != 0]
    return L


def measure(mood, frames, pieces, pal):
    bg = sky(mood)
    res, comps = [], []
    for f in range(10):
        lay, m = place(rgb(frames[f], pal))                 # body only: the same input compose_moods.py measured
        _, mean, mn, weak, weak12, n = analyse(bg, lay, m)
        res.append((mean, mn, weak, weak12, n))
        l2, m2 = place(rgb(layer(frames[f], pieces[f]), pal))
        c = bg.copy()
        c[m2] = l2[m2]
        comps.append(c)
    return res, comps


def save_gif(path, comps):
    strip = Image.fromarray(np.concatenate([c[:CROP] for c in comps], 0)).quantize(255, dither=Image.Dither.NONE)
    ims = [up(c[:CROP], 3).quantize(palette=strip, dither=Image.Dither.NONE) for c in comps]
    ims[0].save(path, save_all=True, append_images=ims[1:], duration=TIMES, loop=0, disposal=1)


def main():
    explore = len(sys.argv) > 2 and sys.argv[1] == 'explore'
    frames, pieces = load()
    if explore:
        return do_explore(frames, pieces, sys.argv[2])
    out = []
    P = out.append
    new, logs, hands = [], [], []
    for f, I in enumerate(frames):
        R, log = redraw(I)
        hands.append(apply_hand(R, f))
        new.append(R)
        logs.append(log)
    npieces = [[(piece_redraw(t), px, py) for t, px, py in pcs] for pcs in pieces]

    # --- proofs
    dusk = palette('dusk')
    diff = sum(int((rgb(new[f], dusk) != rgb(frames[f], BASE)).any(2).sum()) for f in range(10))
    pdiff = sum(int((rgb(a[0], dusk) != rgb(b[0], BASE)).any(2).sum()) for pa, pb in zip(npieces, pieces) for a, b in zip(pa, pb))
    other = sum(int(((new[f] != frames[f]) & ~((frames[f] == LINE) & (new[f] == RIM))).sum()) for f in range(10))
    used = sorted(set(np.unique(np.concatenate([r.ravel() for r in new] + [t.ravel() for pcs in npieces for t, _, _ in pcs])).tolist()) - {0})
    tb, ta = tile_counts(frames, pieces), tile_counts(new, npieces)

    P('RIM REDRAW of the accepted GUMBIRDS logo: index change only, no pixel moved')
    P('')
    P('rule: variant %s. An inner-line pixel (index 8) that touches the outside becomes index 11 (rim). Outside = transparent key,'
      ' 4-neighbourhood for variant A (up, down, left, right), so the rim is 1 pixel and the second line pixel stays dark; an enclosed see-through hole under %d pixels does not count. Rim runs of %d pixels or fewer go back to the dark line. Then the hand list below.'
      % (VARIANT, POCKET_MIN, SPECK_MAX))
    P('index roles:')
    for i, r in enumerate(ROLES):
        P('  %2d %s' % (i, r))
    P('')
    P('palettes (index 1..11, RGB; only 7 and 11 differ between moods; new values are multiples of 8):')
    for mood in ('dusk', 'storm', 'moon'):
        P('  %-5s %s' % (mood, ' '.join('%d,%d,%d' % c for c in palette(mood)[1:])))
        P('        rim (11) %s  shadow (7) %s' % (MOODPAL[mood][RIM], MOODPAL[mood][SH]))
    P('palette entries used by the logo (body and free pieces): %d of 15 (indices %s); accepted logo: 10' % (len(used), used))
    P('')
    P('dusk proof: redraw rendered with the dusk palette against the accepted frames: %d differing pixels over the 10 body frames, '
      '%d over the free pieces' % (diff, pdiff))
    P('index proof: pixels whose index changed in any way other than 8 -> 11: %d' % other)
    P('')
    P('unique 16x16 tiles, flips reused (same count as the final folder: still, body over 10 frames, free pieces, total):')
    P('  before: still %d, body %d, pieces %d, total %d' % tb)
    P('  after : still %d, body %d, pieces %d, total %d' % ta)
    P('')
    P('pixels per frame: inner line kept (8), rim (11), join fixes by rule, hand corrections')
    for f in range(10):
        P('  frame %d: line %4d  rim %4d  rule fixes %d  hand %d' % (f, int((new[f] == LINE).sum()), int((new[f] == RIM).sum()), len(logs[f]), len(hands[f])))
    P('  free pieces: line %d  rim %d (all frames, with repeats)' % (sum(int((t == LINE).sum()) for pcs in npieces for t, _, _ in pcs),
                                                                      sum(int((t == RIM).sum()) for pcs in npieces for t, _, _ in pcs)))
    _, pockets = outside_mask(frames[STILL_F])
    P('enclosed see-through holes in the still (pixels, x0, y0, x1, y1): %s' % pockets)
    P('')
    P('join fixes by rule (x, y in frame coordinates, kind), frame %d: %s' % (STILL_F, [(x, y, k) for x, y, _, _, k in logs[STILL_F]] or 'none'))
    P('hand corrections (frames, x, y, new index, why): %d entries' % len(HAND))
    for h in HAND:
        P('  %s' % (h,))
    P('')
    P('MEASURE: copy of compose_moods.py analyse(): WCAG contrast of each outer logo pixel against its sky 4-neighbours, body layer,')
    P('weak = share of edge pixels under 1.5. still = frame %d. "frames" = lowest to highest over the 10 frames.' % STILL_F)
    summary = {}
    comps_all = {}
    for mood in ('dusk', 'storm', 'moon'):
        rb, cb = measure(mood, frames, pieces, BASE)
        ra, ca = measure(mood, new, npieces, palette(mood))
        comps_all[mood] = (cb, ca)
        summary[mood] = (rb, ra)
        for tag, r in (('before', rb), ('after ', ra)):
            s = r[STILL_F]
            P('  %-5s %s still: mean %.2f  min %.2f  weak %4.1f%%  under 1.2 %4.1f%%  edge pixels %d | frames weak %4.1f..%4.1f%%  mean %.2f..%.2f  min %.2f'
              % (mood, tag, s[0], s[1], s[2], s[3], s[4], min(x[2] for x in r), max(x[2] for x in r), min(x[0] for x in r), max(x[0] for x in r),
                 min(x[1] for x in r)))
        P('        per frame weak %% before: %s' % ' '.join('%.1f' % x[2] for x in rb))
        P('        per frame weak %% after : %s' % ' '.join('%.1f' % x[2] for x in ra))
        if mood in START and START[mood] != {k: MOODPAL[mood][k] for k in START[mood]}:
            keep = dict(MOODPAL[mood])
            MOODPAL[mood].update(START[mood])
            rs, _ = measure(mood, new, npieces, palette(mood))
            MOODPAL[mood].update(keep)
            P('        with the start values rim %s shadow %s: still weak %.1f%%, mean %.2f' % (START[mood][RIM], START[mood][SH], rs[STILL_F][2], rs[STILL_F][0]))
    P('')
    P('palette tuning, tried on the still (rim, shadow: weak %, mean). Kept the start values for both moods:')
    P('  storm 160,200,184 / 0,0,0: 5.2, 4.54 (kept) | 136,176,160: 6.4, 3.93 | 184,216,200: 4.8, 5.06 | 200,224,208: 4.8, 5.37 |'
      ' shadow 8,16,24: 6.7, 4.38 | 152,192,192 with 0,8,16: 6.0, 4.28')
    P('  moon  160,192,248 / 0,0,16: 4.8, 4.05 (kept) | 136,168,240: 5.2, 3.53 | 184,208,248: 6.1, 4.47 | 200,216,248: 6.1, 4.73 |'
      ' shadow 16,8,48: 5.1, 3.92 | 168,176,248 with 8,0,32: 4.8, 3.77')
    P('  storm: a paler rim gains 0.4 points and starts to read as a white sticker edge; a darker rim or a lifted shadow loses edge.')
    P('  moon: every other value measures the same or worse; a paler rim melts into the moon disc behind the D and S.')
    # rim against its inside neighbours
    P('')
    P('rim against what it touches inside (still, 4-neighbours): contacts and contrast per mood')
    R = new[STILL_F]
    for nb_i, cnt in Counter(int(R[y + dy, x + dx]) for y, x in zip(*np.nonzero(R == RIM)) for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1))
                             if 0 <= y + dy < FH and 0 <= x + dx < 336 and R[y + dy, x + dx] not in (RIM, K)).most_common():
        P('  rim vs %-12s %4d contacts: %s' % (ROLES[nb_i][:12], cnt, '  '.join('%s %.2f' % (m, float(ratio(palette(m)[RIM], palette(m)[nb_i])))
                                                                              for m in ('storm', 'moon'))))

    # --- outputs
    strip = np.concatenate(new, 0)
    im = Image.fromarray(strip, 'P')
    pal = palette('dusk')
    im.putpalette([v for c in pal for v in c] + [0] * (768 - 3 * len(pal)))
    im.save(os.path.join(HERE, 'logo_rim_frames_1x.png'), optimize=True)
    ptiles = []
    for pcs in npieces:
        for t, _, _ in pcs:
            if not any((t == q).all() or (t[:, ::-1] == q).all() for q in ptiles):
                ptiles.append(t)
    pim = Image.fromarray(np.concatenate(ptiles, 1), 'P')
    pim.putpalette([v for c in pal for v in c] + [0] * (768 - 3 * len(pal)))
    pim.save(os.path.join(HERE, 'logo_rim_pieces_1x.png'), optimize=True)
    json.dump({
        'note': 'logo_rim_frames_1x.png: 10 frames stacked top to bottom, 336x128 each, indexed PNG, pixel value = palette index. '
                'The PNG carries the dusk palette. logo_rim_pieces_1x.png: free piece tiles, 16x16 each, left to right.',
        'frame_size': [336, FH], 'frames': 10, 'still_frame': STILL_F, 'frame_ms': TIMES,
        'layer_top_left_on_screen': [LX, LY],
        'index_roles': {str(i): r for i, r in enumerate(ROLES)},
        'changes_per_mood': {'7': 'under shadow', '11': 'outer rim'},
        'palettes': {m: [list(c) for c in palette(m)] for m in ('dusk', 'storm', 'moon')},
    }, open(os.path.join(HERE, 'logo_rim.json'), 'w'), indent=1)
    for mood in ('dusk', 'storm', 'moon'):
        cb, ca = comps_all[mood]
        up(cb[STILL_F][:CROP], 3).save(os.path.join(HERE, 'accepted_%s_3x.png' % mood))
        up(ca[STILL_F][:CROP], 3).save(os.path.join(HERE, 'title_%s_3x.png' % mood))
        save_gif(os.path.join(HERE, 'anim_%s_3x.gif' % mood), ca)
    # zoom of the joins, storm and moon, 6x
    for mood in ('storm', 'moon'):
        c = comps_all[mood][1][STILL_F]
        up(np.concatenate([c[24:120, 0:160], c[24:120, 160:320]], 0), 6).save(os.path.join(HERE, 'zoom_%s_6x.png' % mood))
    open(os.path.join(HERE, 'numbers.txt'), 'w').write('\n'.join(out) + '\n')
    html(summary, diff, tb, ta, len(used))
    print('\n'.join(out))


def html(summary, diff, tb, ta, used):
    note = {
        'dusk': 'Rim keeps the dark line colour, shadow unchanged: the redraw is the accepted logo, pixel for pixel (%d differing pixels).' % diff,
        'storm': 'Rim takes the storm light, shadow goes black.',
        'moon': 'Rim takes the moonlight, shadow goes blue-black.',
    }
    h = ['<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Gumbirds logo: rim redraw</title><style>',
         'body{background:#1b1c1f;color:#d6d7da;font:15px/1.45 -apple-system,"Helvetica Neue",Arial,sans-serif;margin:0;padding:28px 32px}',
         'h1{font-size:24px;font-weight:600;margin:0 0 6px}h2{font-size:19px;font-weight:600;margin:38px 0 4px;color:#fff}',
         'p{max-width:980px;margin:6px 0;color:#a9abb1}',
         '.row{display:flex;gap:20px;overflow-x:auto;padding:10px 0 16px;align-items:flex-start}',
         'figure{margin:0;flex:0 0 auto;background:#24262a;border:1px solid #33363b;border-radius:4px}',
         'figure img{display:block;image-rendering:pixelated}',
         'figcaption{padding:10px 14px 12px;max-width:932px}figcaption b{color:#fff;font-weight:600}',
         '.sw{display:inline-block;width:14px;height:14px;border:1px solid #666;vertical-align:-2px;margin:0 4px 0 2px}',
         '</style></head><body>',
         '<h1>Gumbirds logo: rim redraw</h1>',
         '<p>The outer rim of the logo has its own palette entry now (index 11); letter counters and the lines between letters keep the dark '
         'line entry (index 8). No pixel moved and no gum colour changed. Per mood only two entries differ: rim and drop shadow. '
         'Each picture is the top %d screen lines at 3x. Scroll a row sideways. Weak edge = share of outer logo pixels with contrast '
         'ratio under 1.5 against the sky next to them.</p>' % CROP,
         '<p>Palette entries used: %d of 15 (was 10). Unique 16x16 tiles with flips reused: %d before, %d after (body %d to %d, free pieces %d to %d).</p>'
         % (used, tb[3], ta[3], tb[1], ta[1], tb[2], ta[2])]
    for mood in ('dusk', 'storm', 'moon'):
        rb, ra = summary[mood]
        sb, sa = rb[STILL_F], ra[STILL_F]
        rim, shd = MOODPAL[mood][RIM], MOODPAL[mood][SH]
        sw = ('Rim <span class="sw" style="background:rgb(%d,%d,%d)"></span>%d,%d,%d. Shadow <span class="sw" style="background:rgb(%d,%d,%d)"></span>%d,%d,%d.'
              % (rim + rim + shd + shd))
        h.append('<h2>%s</h2><p>%s</p><div class="row">' % (mood.capitalize(), note[mood]))
        h.append('<figure><img src="accepted_%s_3x.png" width="960" height="%d" alt="%s accepted logo"><figcaption><b>Accepted logo</b><br>'
                 'Weak edge %.1f%% (animation frames %.1f%% to %.1f%%). Mean contrast %.2f, lowest %.2f.</figcaption></figure>'
                 % (mood, CROP * 3, mood, sb[2], min(x[2] for x in rb), max(x[2] for x in rb), sb[0], sb[1]))
        h.append('<figure><img src="title_%s_3x.png" width="960" height="%d" alt="%s redraw still"><figcaption><b>Redraw, still</b><br>%s<br>'
                 'Weak edge %.1f%% (animation frames %.1f%% to %.1f%%). Mean contrast %.2f, lowest %.2f.</figcaption></figure>'
                 % (mood, CROP * 3, mood, sw, sa[2], min(x[2] for x in ra), max(x[2] for x in ra), sa[0], sa[1]))
        h.append('<figure><img src="anim_%s_3x.gif" width="960" height="%d" alt="%s redraw animation"><figcaption><b>Redraw, animation</b><br>'
                 '10 frames, timing of the final folder (%s ms), free gum pieces included.</figcaption></figure>'
                 % (mood, CROP * 3, mood, ' '.join(str(t) for t in TIMES)))
        h.append('</div>')
    h.append('<h2>Joins at 6x</h2><p>Still frame over storm and moon, left half above right half: where the lines between letters, '
             'the drip and the counters meet the rim.</p>')
    for mood in ('storm', 'moon'):
        h.append('<div class="row"><figure><img src="zoom_%s_6x.png" width="960" height="1152" alt="%s joins at 6x"></figure></div>' % (mood, mood))
    h.append('</body></html>')
    open(os.path.join(HERE, 'index.html'), 'w').write('\n'.join(h) + '\n')


def do_explore(frames, pieces, dst):
    I = frames[STILL_F]
    out, pockets = outside_mask(I)
    print('pockets (px, x0, y0, x1, y1):', pockets)
    bg = sky('storm')
    rows = []
    for v in 'ABC':
        R = rim_rule(I, v)
        lay, m = place(rgb(R, palette('storm')))
        comp, mean, mn, weak, w12, n = analyse(bg, lay, m)
        print(v, 'rim px', int((R == RIM).sum()), 'weak %.1f mean %.2f' % (weak, mean))
        rows.append(comp[26:116])
    up(np.concatenate(rows, 0), 3).save(os.path.join(dst, 'explore_variants_storm_3x.png'))
    # diagnostics for the chosen variant on all frames
    n8 = [(dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx]
    n4 = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    for f, F in enumerate(frames):
        R = rim_rule(F)
        Pd = np.pad(R, 1)
        stray = [(int(x), int(y)) for y, x in zip(*np.nonzero(R == RIM)) if not any(Pd[y + 1 + dy, x + 1 + dx] == RIM for dy, dx in n8)]
        # dark line pixels cut off from the gum side: all 4-neighbours are rim, key or shadow
        cut = [(int(x), int(y)) for y, x in zip(*np.nonzero(R == LINE)) if all(Pd[y + 1 + dy, x + 1 + dx] in (RIM, K, SH) for dy, dx in n4)]
        # rim pixel wedged inside: no key 4-neighbour and no rim 4-neighbour
        wedge = [(int(x), int(y)) for y, x in zip(*np.nonzero(R == RIM))
                 if not any(Pd[y + 1 + dy, x + 1 + dx] in (K, RIM) for dy, dx in n4)]
        lab, n = components(R == RIM)
        small = [(int(np.nonzero(lab == i)[1][0]), int(np.nonzero(lab == i)[0][0]), int((lab == i).sum())) for i in range(1, n + 1) if (lab == i).sum() <= 3]
        # rim pixels with a shadow 4-neighbour
        rs = sum(1 for y, x in zip(*np.nonzero(R == RIM)) if any(Pd[y + 1 + dy, x + 1 + dx] == SH for dy, dx in n4))
        print('frame', f, 'stray', stray, 'cut dark', cut, 'wedged rim', wedge, 'small rim comps (x,y,n)', small, 'rim next to shadow', rs)


if __name__ == '__main__':
    main()
