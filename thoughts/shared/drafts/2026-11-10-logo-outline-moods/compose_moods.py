"""Per-mood outline palettes for the accepted GUMBIRDS logo. Run: /opt/homebrew/bin/python3.14 -I compose_moods.py
Composition and measure code is copied from ../2026-11-10-logo-three-skies/compose.py (sky(), place(), shift(), analyse(),
lum(), ratio(), up()); the only additions are recolour() (palette swap, no pixel moves), the candidate table, the
all-frames check, the gallery and the animated previews.
Sky = camera 0 crop of cams_<mood>_2x.png (a[20:468:2, 8:648:2]). Logo layer top left at screen x -13, y -8."""
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
QUIET = False

# logo palette roles (colours as they are in logo_a_still_1x.png)
OUT = (8, 8, 24)       # outer line, also the dark line between letters
SHD = (24, 8, 49)      # drop shadow, the other half of the outer ring
KEYL = (90, 16, 115)   # keyline / deepest gum
NAMES = {OUT: 'outer line', SHD: 'drop shadow', KEYL: 'keyline'}

# candidate table: mood -> list of (id, name, {old colour: new colour}, note). Every new channel is a multiple of 8.
CANDS = {
    'storm': [
        ('S1', 'pale grey-green rim, shadow kept', {OUT: (184, 216, 200)}, ''),
        ('S2', 'grey-green rim, black shadow', {OUT: (160, 200, 184), SHD: (0, 0, 0)}, ''),
        ('S3', 'lightning rim, pale shadow, deeper keyline', {OUT: (232, 248, 232), SHD: (168, 208, 192), KEYL: (64, 8, 88)}, ''),
    ],
    'moon': [
        ('M1', 'moonlight rim, shadow kept', {OUT: (168, 200, 248)}, ''),
        ('M2', 'moonlight rim, blue-black shadow', {OUT: (160, 192, 248), SHD: (0, 0, 16)}, ''),
        ('M3', 'ice rim, sky-blue shadow, deeper keyline', {OUT: (224, 240, 248), SHD: (152, 184, 248), KEYL: (72, 8, 104)}, ''),
    ],
    'dusk': [
        ('D1', 'apricot rim, shadow kept (optional)', {OUT: (248, 216, 168)}, ''),
    ],
}


def inner(logo, swap):
    """Contrast of the recoloured outer line against the logo colours it touches inside (4-neighbours)."""
    r = recolour(logo, swap)
    o = (logo == OUT).all(2)
    res = Counter()
    for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nb = shift(o, dy, dx) & ~o & (logo != KEY).any(2)
        res.update(map(tuple, r[nb].tolist()))
    new = swap.get(OUT, OUT)
    return [(c, k, float(ratio(new, c))) for c, k in res.most_common()]


def P(s):
    if QUIET:
        return
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
    outline = Counter(map(tuple, lay[edge])).most_common(1)[0]
    P('== %s' % mood)
    ti = lambda c: tuple(int(v) for v in c)
    P('  logo outline colour (most common on the outer ring) %s, %d of %d edge pixels' % (ti(outline[0]), outline[1], edge.sum()))
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


def recolour(logo, swap):
    """Palette swap only: every pixel of an old colour takes the new colour; no pixel moves."""
    r = logo.copy()
    for old, new in swap.items():
        assert all(v % 8 == 0 for v in new), new
        r[(logo == old).all(2)] = new
    return r


CROP = 136   # screen lines shown in the gallery crop (logo layer ends at line 120)


def main():
    global QUIET
    still = np.asarray(Image.open(os.path.join(LOGO, 'logo_a_still_1x.png')).convert('RGB'))
    strip = np.asarray(Image.open(os.path.join(LOGO, 'logo_a_frames_1x.png')).convert('RGB'))
    frames = [strip[i * 128:(i + 1) * 128] for i in range(10)]
    ncol = len({tuple(c) for c in still.reshape(-1, 3).tolist()} - {KEY})
    P('logo colours in the still: %d (palette indices unchanged by every candidate; only RGB values of existing indices move)' % ncol)
    P('measure: same as ../2026-11-10-logo-three-skies/numbers.txt (WCAG contrast ratio of each outer logo pixel against its sky 4-neighbours)')
    P('"frames" = weak-edge percent (under 1.5) over the 10 animation frames, lowest to highest; frame 0 is the widest stretch')
    rows = {}
    for mood in ('storm', 'moon', 'dusk'):
        bg = sky(mood)
        rows[mood] = []
        for cid, name, swap, note in [('REF', 'current logo', {}, '')] + CANDS[mood]:
            P('')
            P('#### %s %s: %s' % (mood, cid, name))
            ch = '; '.join('%s %s -> %s' % (NAMES[o], o, n) for o, n in swap.items()) or 'none'
            P('  changed palette entries: %s' % ch)
            lay, m = place(recolour(still, swap))
            comp, mean, mn, bad = analyse('%s %s still' % (mood, cid), bg, lay, m)
            QUIET = True
            fb, comps = [], []
            for f in frames:
                l2, m2 = place(recolour(f, swap))
                c2, _, _, b2 = analyse('', bg, l2, m2)
                fb.append(b2)
                comps.append(c2)
            QUIET = False
            for c, k, rr in inner(still, swap):
                P('  outer line vs inside neighbour %s: %d contacts, contrast %.2f%s' % (c, k, rr, '  (under 1.5)' if rr < 1.5 else ''))
            P('  frames: weak %.1f%% to %.1f%%; frame 0 (widest) %.1f%%; worst frame %d' % (min(fb), max(fb), fb[0], int(np.argmax(fb))))
            tag = '%s_%s' % (mood, cid)
            up(comp[:CROP], 3).save(os.path.join(HERE, 'title_%s_3x.png' % tag))
            up(comp, 3).save(os.path.join(HERE, 'full_%s_3x.png' % tag))
            ims = [up(c[:CROP], 3).convert('P', palette=Image.Palette.ADAPTIVE, colors=255) for c in comps]
            ims[0].save(os.path.join(HERE, 'anim_%s_3x.gif' % tag), save_all=True, append_images=ims[1:], duration=100, loop=0)
            rows[mood].append((cid, name, swap, mean, mn, bad, min(fb), max(fb), fb[0], comp))
    P('')
    P('#### summary (still): id, mean contrast, min contrast, weak edge % (under 1.5), frames range')
    for mood in rows:
        for cid, name, swap, mean, mn, bad, f0, f1, fw, _ in rows[mood]:
            P('  %-5s %-4s mean %.2f  min %.2f  weak %5.1f%%  frames %4.1f..%4.1f%%  %s' % (mood, cid, mean, mn, bad, f0, f1, name))
    open(os.path.join(HERE, 'numbers.txt'), 'w').write('\n'.join(out) + '\n')
    # contact sheet for judging (2 columns)
    for mood in rows:
        n = len(rows[mood])
        sh = np.zeros(((n + 1) // 2 * (CROP + 4), 644, 3), np.uint8) + 40
        for i, r in enumerate(rows[mood]):
            y, x = (i // 2) * (CROP + 4), (i % 2) * 324
            sh[y:y + CROP, x:x + 320] = r[-1][:CROP]
        up(sh, 3).save(os.path.join(HERE, 'contact_%s_3x.png' % mood))
    # frame check sheet: per recommended candidate the two frames that differ most from the still (frame 0 is the widest stretch)
    d = [int(((f != still).any(2)).sum()) for f in frames]
    far = sorted(set([0, int(np.argmax(d))]))
    P('')
    P('frame check: pixels that differ from the still per frame %s; sheet shows frames %s' % (d, far))
    tiles = []
    for mood, cid in RECOMMEND.items():
        swap = dict([(c[0], c[2]) for c in CANDS[mood]]).get(cid, {})
        for k in far:
            lay, m = place(recolour(frames[k], swap))
            c = sky(mood).copy()
            c[m] = lay[m]
            tiles.append(c[:CROP])
    sh = np.zeros(((len(tiles) + 1) // 2 * (CROP + 4), 644, 3), np.uint8) + 40
    for i, t in enumerate(tiles):
        y, x = (i // 2) * (CROP + 4), (i % 2) * 324
        sh[y:y + CROP, x:x + 320] = t
    up(sh, 3).save(os.path.join(HERE, 'contact_frames_3x.png'))
    html(rows)


def html(rows):
    rec = RECOMMEND
    h = ['<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Gumbirds logo outline per mood</title><style>',
         'body{background:#1b1c1f;color:#d6d7da;font:15px/1.45 -apple-system,"Helvetica Neue",Arial,sans-serif;margin:0;padding:28px 32px}',
         'h1{font-size:24px;font-weight:600;margin:0 0 6px}h2{font-size:19px;font-weight:600;margin:38px 0 4px;color:#fff}',
         'p{max-width:980px;margin:6px 0;color:#a9abb1}',
         '.row{display:flex;gap:20px;overflow-x:auto;padding:10px 0 16px;align-items:flex-start}',
         'figure{margin:0;flex:0 0 auto;width:960px;background:#24262a;border:1px solid #33363b;border-radius:4px}',
         'figure.pick{border-color:#e8b84a}',
         'figure img{display:block;width:960px;image-rendering:pixelated}',
         'figcaption{padding:10px 14px 12px}figcaption b{color:#fff;font-weight:600}',
         '.sw{display:inline-block;width:14px;height:14px;border:1px solid #666;vertical-align:-2px;margin-right:4px}',
         '.tag{color:#e8b84a;font-weight:600}a{color:#8fb4e8}',
         '</style></head><body>',
         '<h1>Gumbirds logo: outline colour per sky mood</h1>',
         '<p>Palette swap only: same pixels, same 10 palette entries, every changed channel a multiple of 8. '
         'Each picture is the top %d screen lines at 3x; the still is on top, the 10 frame animation under it. '
         'Scroll each row sideways. Weak edge = share of outer logo pixels with contrast ratio under 1.5 against the sky next to them.</p>' % CROP]
    for mood in rows:
        h.append('<h2>%s</h2><p>%s</p><div class="row">' % (mood.capitalize(), MOODNOTE[mood]))
        for cid, name, swap, mean, mn, bad, f0, f1, fw, _ in rows[mood]:
            tag = '%s_%s' % (mood, cid)
            pick = rec.get(mood) == cid
            sw = '<br>'.join('<span class="sw" style="background:rgb(%d,%d,%d)"></span>%s %d,%d,%d to <span class="sw" style="background:rgb(%d,%d,%d)"></span>%d,%d,%d'
                             % (o + (NAMES[o],) + o + n + n) for o, n in swap.items()) or 'No palette change.'
            h.append('<figure%s><img src="title_%s_3x.png" width="960" height="%d" alt="%s %s still">'
                     '<img src="anim_%s_3x.gif" width="960" height="%d" alt="%s %s animation"><figcaption>'
                     '<b>%s: %s</b>%s<br>%s<br>Mean contrast %.2f, lowest %.2f, weak edge %.1f%% (animation frames %.1f%% to %.1f%%, widest frame %.1f%%). '
                     '<a href="full_%s_3x.png">Full screen</a></figcaption></figure>'
                     % (' class="pick"' if pick else '', tag, CROP * 3, mood, cid, tag, CROP * 3, mood, cid,
                        cid, name, ' <span class="tag">recommended</span>' if pick else '', sw, mean, mn, bad, f0, f1, fw, tag))
        h.append('</div>')
    h.append('</body></html>')
    open(os.path.join(HERE, 'index.html'), 'w').write('\n'.join(h) + '\n')


RECOMMEND = {'storm': 'S2', 'moon': 'M2', 'dusk': 'REF'}
MOODNOTE = {
    'storm': 'Rim colour taken from the storm light (pale grey-green). The outer line colour also fills the letter counters and the lines between letters, so they turn pale with it.',
    'moon': 'Rim colour taken from the moonlight (cool blue).',
    'dusk': 'The current dark line already separates from the warm sky; the apricot rim is shown only for comparison.',
}

if __name__ == '__main__':
    main()
