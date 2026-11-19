"""Logo over the three title skies. Run: /opt/homebrew/bin/python3.14 -I compose.py
Sky = camera 0 crop of cams_<mood>_2x.png (same crop the accepted title used: a[20:468:2, 8:648:2]), downsampled 2x.
Logo = accepted still (frame 3) and the widest frame of the 10-frame strip, layer top left at screen x -13, y -8."""
import os
from collections import Counter
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
DR = os.path.dirname(HERE)
LOGO = os.path.join(DR, '2026-11-10-hud-title-final')
WIDE = os.path.join(DR, '2026-11-10-backgrounds-wide')
LX, LY = -13, -8
KEY = (255, 0, 255)
out = []


def P(s):
    print(s)
    out.append(s)


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


def analyse(mood, bg, lay, m):
    comp = bg.copy()
    comp[m] = lay[m]
    n4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    # opaque pixels with a transparent 4-neighbour inside the screen
    edge = np.zeros_like(m)
    for dy, dx in n4:
        nb = shift(m, dy, dx)
        valid = shift(np.ones_like(m), dy, dx)
        edge |= m & ~nb & valid
    cols = Counter(map(tuple, lay[m]))
    keyl = lum(lay[m].astype(float))
    outline = Counter(map(tuple, lay[edge])).most_common(1)[0]
    P('== %s' % mood)
    ti = lambda c: tuple(int(v) for v in c)
    P('  logo outline colour (most common on the outer ring) %s, %d of %d edge pixels' % (ti(outline[0]), outline[1], edge.sum()))
    P('  darkest logo colour %s, lightest %s' % (ti(lay[m][keyl.argmin()]), ti(lay[m][keyl.argmax()])))
    per_edge, pairs, bad = [], [], Counter()
    ys, xs = np.nonzero(edge)
    for y, x in zip(ys, xs):
        cs = []
        for dy, dx in n4:
            yy, xx = y + dy, x + dx
            if 0 <= yy < 224 and 0 <= xx < 320 and not m[yy, xx]:
                r = float(ratio(lay[y, x], bg[yy, xx]))
                cs.append(r)
                pairs.append(r)
                if r < 1.5:
                    bad[tuple(bg[yy, xx])] += 1
        if cs:
            per_edge.append(np.mean(cs))
    per_edge = np.array(per_edge)
    pairs = np.array(pairs)
    P('  edge pixels %d, edge/sky pairs %d' % (len(per_edge), len(pairs)))
    P('  contrast edge vs sky outside: mean %.2f, min %.2f (per pair), mean per edge pixel %.2f' % (pairs.mean(), pairs.min(), per_edge.mean()))
    P('  edge pixels under 1.5: %.1f%%  under 1.2: %.1f%%' % (100 * (per_edge < 1.5).mean(), 100 * (per_edge < 1.2).mean()))
    if bad:
        c, k = bad.most_common(1)[0]
        P('  sky colour that collides most: %s (%d pairs under 1.5; of %d such pairs)' % (ti(c), k, sum(bad.values())))
    else:
        P('  sky colour that collides most: none (no pair under 1.5)')
    return comp, float(pairs.mean()), float(pairs.min()), 100 * float((per_edge < 1.5).mean())


def up(a, k):
    return Image.fromarray(a).resize((a.shape[1] * k, a.shape[0] * k), Image.NEAREST)


def main():
    still = np.asarray(Image.open(os.path.join(LOGO, 'logo_a_still_1x.png')).convert('RGB'))
    strip = np.asarray(Image.open(os.path.join(LOGO, 'logo_a_frames_1x.png')).convert('RGB'))
    frames = [strip[i * 128:(i + 1) * 128] for i in range(10)]
    wid = [(f != KEY).any(2).any(0).nonzero()[0] for f in frames]
    spans = [(w.max() - w.min() + 1) for w in wid]
    wf = int(np.argmax(spans))
    P('logo frame opaque widths over 10 frames: %s; widest frame %d' % ([int(v) for v in spans], wf))
    summary = {}
    for mood in ('moon', 'dusk', 'storm'):
        bg = sky(mood)
        for tag, logo in (('', still), ('_wide', frames[wf])):
            lay, m = place(logo)
            if tag:
                P('  (widest animation frame)')
            comp, mean, mn, bad = analyse(mood + tag, bg, lay, m)
            up(comp, 1).save(os.path.join(HERE, 'title_%s%s_1x.png' % (mood, tag)))
            up(comp, 3).save(os.path.join(HERE, 'title_%s%s_3x.png' % (mood, tag)))
            summary[mood + tag] = (mean, mn, bad)
    open(os.path.join(HERE, 'numbers.txt'), 'w').write('\n'.join(out) + '\n')


main()
