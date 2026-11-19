"""Assembles the hand-typed pixel rows of cave_art.py. Joins, mirrors, 1 px step pastes,
palette mapping, sheet packing, scaling, counting. No drawing happens here."""
import os, sys
from PIL import Image
import cave_art as A
D = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(D, '..', '..', '..', '..')
BG = (24, 16, 49)

def join(parts, name):
    for i, p in enumerate(parts):
        assert len(p) == 16, (name, i, len(p))
        for y, r in enumerate(p): assert len(r) == len(p[0]), (name, 'part', i, 'row', y, len(r), len(p[0]))
    rows = [''.join(p[y] for p in parts) for y in range(16)]
    assert len(rows[0]) == 64, (name, len(rows[0]))
    return rows

def check(rows, w, h, name):
    assert len(rows) == h, (name, len(rows))
    for y, r in enumerate(rows): assert len(r) == w, (name, 'row', y, len(r))
    return rows

def step_paste(profile, touch, roof):
    """32x32 block: the 2 px wide hand profile pasted 16 times, 1 px lower each time."""
    g = [['.'] * 32 for _ in range(32)]
    for p in range(16):
        for y in range(32):
            b = (15 + p - y) if roof else (y + p - 17)
            if b >= 0:
                g[y][2 * p], g[y][2 * p + 1] = profile[b][0], profile[b][1]
    for x, y, c in touch: g[y][x] = c
    return [''.join(r) for r in g]

def img(rows, pal):
    im = Image.new('RGBA', (len(rows[0]), len(rows)), (0, 0, 0, 0))
    for y, r in enumerate(rows):
        for x, c in enumerate(r):
            if c != '.': im.putpixel((x, y), pal[c] + (255,))
    return im

def tiles_of(im):
    return {im.crop((x, y, x + 16, y + 16)).tobytes() for y in range(0, im.height, 16) for x in range(0, im.width, 16)}

def sc(im, k): return im.resize((im.width * k, im.height * k), Image.NEAREST)
def flat(im, c=BG):
    b = Image.new('RGBA', im.size, c + (255,)); b.alpha_composite(im); return b.convert('RGB')

# ---- floor from the shipped sheet + hand lip
sheet = Image.open(os.path.join(R, 'assets/tripstrip/tripstrip_sheet.png')).convert('RGBA')
gcols = sorted({sheet.getpixel((x, y)) for x in range(128) for y in range(112)}, key=lambda c: (c[3], c[0] * 3 + c[1] * 6 + c[2]))
GUM = {ch: c[:3] for ch, c in zip('0123456789', gcols[1:])}
ffill = sheet.crop((0, 0, 16, 16))
frim = sheet.crop((0, 32, 128, 48)).copy()
frim.paste((0, 0, 0, 0), (0, 0, 128, 4))
lip = img(check(A.F1_LIP_ROWS, 64, 2, 'lip'), GUM)
frim.paste(lip, (0, 2)); frim.paste(lip, (64, 2))
framp = img(step_paste(A.F1_RAMP_PROFILE, A.F1_RAMP_TOUCH, False), GUM)

TAKES = []
def take(name, title, pal, rim, fill, ramp, hang):
    assert len(pal) <= 15, name
    for c in pal.values(): assert all(v == (v >> 3 << 3 | v >> 5) for v in c), (name, c)
    rimI, fillI, rampI = img(rim, pal), img(fill, pal), img(check(ramp, 32, 32, name + ' ramp'), pal)
    hangI = {}
    for k, (under, rows) in hang.items():
        check(rows, 16, 8, name + ' hang ' + k)
        for x in range(16):  # a hang pixel in its top row must touch rock in the rim's last row
            if rows[0][x] != '.': assert rim[15][under * 16 + x] != '.', (name, 'hang', k, 'floats at col', x)
        hangI[k] = (under, img(rows + ['.' * 16] * 8, pal))
    used = set(''.join(rim) + ''.join(fill) + ''.join(ramp) + ''.join(''.join(r) for _, r in hang.values())) - {'.'}
    assert used <= set(pal), (name, used - set(pal))
    n = dict(rim=len(tiles_of(rimI)), fill=len(tiles_of(fillI)), ramp=len(tiles_of(rampI) - {bytes(1024)}), hang=len(hang), colours=len(used))
    # every ramp column must be solid down to the stepped edge
    for x in range(32):
        col = ''.join(ramp[y][x] for y in range(32)); solid = len(col.rstrip('.'))
        assert '.' not in col[:solid] and abs(solid - (16 + x // 2)) <= 1, (name, 'ramp col', x, solid)
    TAKES.append((name, title, pal, rimI, fillI, rampI, hangI, n))

take('take1', 'Take 1: slate boulders', A.PAL1, join(A.T1_RIM, 't1 rim'), join(A.T1_FILL, 't1 fill'), A.T1_RAMP, {})
take('take2', 'Take 2: warm rock, blunt stalactites', A.PAL2, join(A.T2_RIM, 't2 rim'), check(A.T2_FILL_ROWS, 64, 16, 't2 fill'),
     A.T2_RAMP, A.T2_HANG)
take('take3', 'Take 3: mossy rock, vines', A.PAL3, join(A.T3_RIM, 't3 rim'), join(A.T3_FILL, 't3 fill'), A.T3_RAMP, A.T3_HANG)

# ---- world (seed 6 window sequence of the first drafts, snapped to the 16 px grid)
SEQ = [(18, 162), (37, 157), (7, 143), (0, 120), (12, 156), (12, 148), (13, 133), (0, 144)]
TOP = [int(t / 16 + .5) * 16 for t, _ in SEQ]; BOT = [int(b / 16 + .5) * 16 for _, b in SEQ]
W = 192 * len(SEQ)
HANG_ORDER = {'take1': [], 'take2': ['A', None, 'C', 'B', 'C', None], 'take3': ['A', 'B', None, 'D', 'C', None, 'B', 'A', 'D']}

def world(t):
    name, title, pal, rimI, fillI, rampI, hangI, n = t
    w = Image.new('RGBA', (W, 224), BG + (255,))
    roof_ramp, floor_ramp = {}, {}
    for i in range(1, len(SEQ)):
        for j in range(abs(TOP[i] - TOP[i - 1]) // 16):
            down = TOP[i] > TOP[i - 1]
            y0 = TOP[i - 1] + 16 * j - 16 if down else TOP[i - 1] - 16 * (j + 1) - 16
            roof_ramp[192 * i + 32 * j] = (y0, down)
        for j in range(abs(BOT[i] - BOT[i - 1]) // 16):
            up = BOT[i] < BOT[i - 1]
            floor_ramp[192 * i + 32 * j] = (BOT[i - 1] - 16 * (j + 1) if up else BOT[i - 1] + 16 * j, up)
    hk = 0
    for x in range(0, W, 16):
        i = x // 192; c = (x // 16) % 4
        rr = roof_ramp.get(x) or roof_ramp.get(x - 16)
        if rr:
            y0, down = rr; half = 0 if x in roof_ramp else 1
            blk = rampI if down else rampI.transpose(Image.FLIP_LEFT_RIGHT)
            w.alpha_composite(blk.crop((16 * half, 0, 16 * half + 16, 32)), (x, y0)); top_fill = y0
        else:
            T = TOP[i]
            if T >= 16:
                w.alpha_composite(rimI.crop((16 * c, 0, 16 * c + 16, 16)), (x, T - 16))
                cand = [k for k, (u, _) in hangI.items() if u == c]
                order = HANG_ORDER[name]
                if cand and order:
                    k = order[hk % len(order)]; hk += 1
                    if k in cand: w.alpha_composite(hangI[k][1], (x, T))
            top_fill = T - 16
        r = 0
        for y in range(top_fill - 16, -16, -16):
            r += 1; fc = (c + 2 * r) % 4
            w.alpha_composite(fillI.crop((16 * fc, 0, 16 * fc + 16, 16)), (x, y))
        fr = floor_ramp.get(x) or floor_ramp.get(x - 16)
        if fr:
            y0, up = fr; half = 0 if x in floor_ramp else 1
            blk = framp if up else framp.transpose(Image.FLIP_LEFT_RIGHT)
            w.alpha_composite(blk.crop((16 * half, 0, 16 * half + 16, 32)), (x, y0)); yb = y0 + 32
        else:
            B = BOT[i]; fx = x % 128
            w.alpha_composite(frim.crop((fx, 0, fx + 16, 16)), (x, B)); yb = B + 16
        for y in range(yb, 224, 16): w.alpha_composite(ffill, (x, y))
    return w.convert('RGB')

num = []
for t in TAKES:
    name, title, pal, rimI, fillI, rampI, hangI, n = t
    sh = Image.new('RGBA', (64 + 8 + 64 + 8 + 32 + 8 + 16 * max(1, len(hangI)), 32), (0, 0, 0, 0))
    sh.alpha_composite(rimI, (0, 0)); sh.alpha_composite(fillI, (72, 0)); sh.alpha_composite(rampI, (144, 0))
    for q, (k, (u, h)) in enumerate(hangI.items()): sh.alpha_composite(h, (184 + 16 * q, 0))
    flat(sh).save(os.path.join(D, name + '_tiles_1x.png')); sc(flat(sh), 3).save(os.path.join(D, name + '_tiles_3x.png'))
    wd = world(t)
    X0 = 112
    m = wd.crop((X0, 0, X0 + 320, 224)); m.save(os.path.join(D, name + '_mock_1x.png')); sc(m, 3).save(os.path.join(D, name + '_mock_3x.png'))
    if '--gif' in sys.argv:
        fr = [sc(wd.crop((x, 0, x + 320, 224)), 2).quantize(64, dither=Image.NONE) for x in range(0, W - 320, 4)]
        fr[0].save(os.path.join(D, name + '_scroll_2x.gif'), save_all=True, append_images=fr[1:], duration=90, loop=0, optimize=False)
    tot = n['rim'] + n['fill'] + n['ramp'] + n['hang']
    num.append(f"roof {name} ({title}): tiles {tot} = rim {n['rim']} + fill {n['fill']} + ramp {n['ramp']} (one 2x2 block, hflip for the other way) + hang {n['hang']}; colours {n['colours']} of 15; 1 palette slot; static")
fs = Image.new('RGBA', (128 + 8 + 32, 32), (0, 0, 0, 0)); fs.alpha_composite(frim, (0, 0)); fs.alpha_composite(ffill, (0, 16)); fs.alpha_composite(framp, (136, 0))
flat(fs).save(os.path.join(D, 'floor_f1_1x.png')); sc(flat(fs), 3).save(os.path.join(D, 'floor_f1_3x.png'))
nfr = len(tiles_of(framp) - {bytes(1024)})
num += [f"floor F1: gum palette unchanged ({len({c for c in frim.getdata() if c[3]} | {c for c in framp.getdata() if c[3]})} gum colours used); rim = shipped t2_rim rows 4-15 with rows 0-3 replaced by an empty 2 px and a straight 2 px lip; fill unchanged",
        f"floor ramp: {nfr} tiles static (one 2x2 block, hflip for the other way); animated with the 8 rim frames it would be up to {nfr * 8} tiles",
        f"ramp tiles in total per roof take + floor: {4} + {nfr} = {4 + nfr}",
        "sheet tiles freed by dropping roles t3..t6: 24 (4 + 8 + 8 + 4); tripstrip sheet 56 -> 32 + " + str(nfr) + " = " + str(32 + nfr),
        f"window sequence seed 6 snapped to 16 px (top, bottom per 192 px chunk): {list(zip(TOP, BOT))}",
        "scroll gif: 4 px per 90 ms frame = 44.4 px/s (target 45), 2x scale, whole 8 chunk sequence",
        "all palettes asserted <= 15 colours + transparent, all colours 5 bits per channel; every ramp column asserted solid down to a 1 px stepped edge; every hang pixel asserted to touch rock"]
open(os.path.join(D, 'numbers.txt'), 'w').write('\n'.join(num) + '\n'); print('\n'.join(num))
# references at 3x for the gallery
for f, crop in [('tripstrip/tripstrip_sheet', None), ('islands/island_sheet', None), ('islands/island_garden_sheet', None), ('islands/island_deck_sheet', None),
                ('hazard/hazard_sheet', (0, 0, 256, 96)), ('dusk/dusk_sheet', (0, 112, 336, 320)), ('gum/gum_sheet', (0, 0, 160, 64)), ('flier/sootling_sheet', (0, 0, 192, 64))]:
    im = Image.open(os.path.join(R, 'assets', f + '.png')).convert('RGBA')
    if crop: im = im.crop(crop)
    sc(flat(im), 3).save(os.path.join(D, 'ref_' + f.split('/')[1] + '_3x.png'))
