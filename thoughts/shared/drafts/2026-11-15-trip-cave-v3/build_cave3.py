"""Assembles the hand-typed pixel data of cave_art3.py (new) and cave_art_v2.py (take 1 rim, fill, palette).
Joins, transposes, mirrors, palette-maps, places, packs, scales, measures heights and counts. No drawing happens here."""
import os, sys, json
from PIL import Image
D = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(D, '..', '..', '..', '..')
sys.path.insert(0, D)
import cave_art_v2 as V2
import cave_art3 as A
PAL = V2.PAL1
EMPTY = bytes(1024)

def join(parts, name):
    rows = [''.join(p[y] for p in parts) for y in range(16)]
    assert all(len(r) == len(rows[0]) for r in rows), name
    return rows
def check(rows, w, h, name):
    assert len(rows) == h and all(len(r) == w for r in rows), name
    return rows
def img(rows, pal):
    im = Image.new('RGBA', (len(rows[0]), len(rows)), (0, 0, 0, 0))
    for y, r in enumerate(rows):
        for x, c in enumerate(r):
            if c != '.': im.putpixel((x, y), pal[c] + (255,))
    return im
def cells(im): return [im.crop((x, y, x + 16, y + 16)) for y in range(0, im.height, 16) for x in range(0, im.width, 16)]
def sc(im, k): return im.resize((im.width * k, im.height * k), Image.NEAREST)
def flip(im): return im.transpose(Image.FLIP_LEFT_RIGHT)
def transpose(cols): return [''.join(c[y] for c in cols) for y in range(len(cols[0]))]
def stamp(rows, patches):
    g = [list(r) for r in rows]
    for p, x, y in patches:
        for j, pr in enumerate(p):
            for i, ch in enumerate(pr):
                if ch != '.': g[y + j][x + i] = ch
    return [''.join(r) for r in g]

# ---------------------------------------------------------------- roof pieces
for v in PAL.values(): assert all(c == (c >> 3 << 3 | c >> 5) for c in v), v
rimA = img(join(V2.T1_RIM, 'rim A'), PAL); fillI = img(join(V2.T1_FILL, 'fill'), PAL)
rimB = img(check(join(A.RIM_B, 'rim B'), 64, 16, 'rim B'), PAL)
solo = [img(check(s, 16, 16, 'solo'), PAL) for s in A.RIM_SOLO]
RIMT = {'A': cells(rimA), 'B': cells(rimB), 's': [solo[0]], 't': [solo[1]]}
FILLT = cells(fillI)
roof16 = img(check(A.ROOF_S16, 48, 32, 'roof S16'), PAL)
roof32 = Image.new('RGBA', (48, 48), (0, 0, 0, 0))
for (cx, cy) in [(1, 0), (2, 0), (2, 1)]: roof32.alpha_composite(FILLT[(cx + 2 * cy) % 4], (16 * cx, 16 * cy))
for (cx, cy), rows in A.ROOF_S32.items(): roof32.alpha_composite(img(check(rows, 16, 16, 'roof S32'), PAL), (16 * cx, 16 * cy))
used = set(''.join(''.join(r) for part in (V2.T1_RIM + V2.T1_FILL + A.RIM_B + A.RIM_SOLO + [A.ROOF_S16] + list(A.ROOF_S32.values())) for r in part)) - {'.'}
assert used <= set(PAL) and len(used) <= 15, used

# ---------------------------------------------------------------- floor pieces (gum palette read from the shipped sheet)
sheet = Image.open(os.path.join(R, 'assets/tripstrip/tripstrip_sheet.png')).convert('RGBA')
gcols = sorted({c[:3] for c in sheet.get_flattened_data() if c[3]}, key=lambda c: c[0] * 299 + c[1] * 587 + c[2] * 114)
GUM = {str(i): c for i, c in enumerate(gcols[:10])}
ffill = sheet.crop((0, 0, 16, 16))
frim = sheet.crop((0, 32, 128, 48)).copy(); frim.paste((0, 0, 0, 0), (0, 0, 128, 4))
lip = img(check(V2.F1_LIP_ROWS, 64, 2, 'lip'), GUM); frim.paste(lip, (0, 2)); frim.paste(lip, (64, 2))
f16rows = transpose(check(A.FLOOR_S16, 32, 48, 'floor S16')); f32rows = transpose(check(A.FLOOR_S32, 48, 48, 'floor S32'))
assert len(A.FLOOR_S16_ANIM) == 8 and len(A.FLOOR_S32_ANIM) == 8
def over_fill(rows):
    # the typed band plus 3 body rows stay; deeper down the shipped gum fill tile shows through, so the curve body matches the fill around it
    im = img(rows, GUM); out = Image.new('RGBA', im.size, (0, 0, 0, 0)); base = transpose(rows)
    for x, col in enumerate(base):
        top = len(col) - len(col.lstrip('.')); cut = col.index('111', top) + 3
        for y in range(top, im.height):
            out.putpixel((x, y), im.getpixel((x, y)) if y < cut else ffill.getpixel((x % 16, y % 16)))
    return out
floor16 = [over_fill(stamp(f16rows, p)) for p in A.FLOOR_S16_ANIM]
floor32 = [over_fill(stamp(f32rows, p)) for p in A.FLOOR_S32_ANIM]

# ---------------------------------------------------------------- measured height tables (per pixel column)
def roof_depth(im):   # rows of rock from the piece top down to the lowest rock pixel; 0 = no rock in that column
    a = im.getchannel('A'); return [max([y + 1 for y in range(im.height) if a.getpixel((x, y))] or [0]) for x in range(im.width)]
def floor_top(im):    # first gum row from the piece top; piece height = no gum in that column
    a = im.getchannel('A'); return [min([y for y in range(im.height) if a.getpixel((x, y))] or [im.height]) for x in range(im.width)]
def per_tile(v): return [v[i:i + 16] for i in range(0, len(v), 16)]
HEIGHTS = {
 'note': 'One list of 16 values per 16 px tile column, left to right. Roof: rock depth in px below the piece top row (piece top = rim tile top; flat rim lowest point is 16). '
         'Floor: first gum row in px below the piece top row (flat lip is 2). Pieces are drawn with the edge falling (roof) or rising (floor) to the right; hflip reverses both the tile column order and each list.',
 'roof_rim_A': per_tile(roof_depth(rimA)), 'roof_rim_B': per_tile(roof_depth(rimB)),
 'roof_rim_solo': [roof_depth(s) for s in solo],
 'roof_S16 (48x32, falls 16)': per_tile(roof_depth(roof16)), 'roof_S32 (48x48, falls 32)': per_tile(roof_depth(roof32)),
 'floor_flat': per_tile(floor_top(frim.crop((0, 0, 64, 16)))),
 'floor_S16 (48x32, rises 16)': per_tile(floor_top(img(f16rows, GUM))), 'floor_S32 (48x48, rises 32)': per_tile(floor_top(img(f32rows, GUM))),
}
for k in ('floor_S16 (48x32, rises 16)', 'floor_S32 (48x48, rises 32)'):   # floor surface must never step more than 2 px per pixel column
    v = sum(HEIGHTS[k], []); assert all(0 <= v[i] - v[i + 1] <= 2 for i in range(len(v) - 1)), (k, v)
json.dump(HEIGHTS, open(os.path.join(D, 'heights.json'), 'w'), indent=1)

# ---------------------------------------------------------------- world
SEQ = [(18, 162), (37, 157), (7, 143), (0, 120), (12, 156), (12, 148), (13, 133), (0, 144)]
TOP = [int(t / 16 + .5) * 16 for t, _ in SEQ]; BOT = [int(b / 16 + .5) * 16 for _, b in SEQ]
W = 192 * len(SEQ)
# hand-picked rim order per chunk: A/B = 64 px sets, s/t = solo tiles. 12 tiles without a curve, 9 after a curve.
RIM_ORDER = ['sAtBst', 'BtA', 'AsB', 'ABA', 'sBA', 'BAB', 'tAsBts', 'BsA']
TRIP = (90, 33, 90)   # dusk mood trip colour (tools/import_bg_sheet.py MOODS)
PLANES = []
for n, y, par in [('far', 52, 8), ('midB', 84, 4), ('midA', 104, 3)]:
    p = Image.open(os.path.join(D, '..', '2026-11-10-backgrounds-final', 'plane_dusk_%s_1x.png' % n)).convert('RGBA')
    key = p.getpixel((0, 0)); p.putdata([(0, 0, 0, 0) if c == key else c for c in p.get_flattened_data()])
    PLANES.append((p, y, par))

def curve(a, b):
    d = abs(a - b); return None if d == 0 else {16: 'S16', 32: 'S32'}[d]

def world(f):
    w = Image.new('RGBA', (W, 224), (0, 0, 0, 0))
    for i in range(len(SEQ)):
        x0 = 192 * i; order = [t for k in RIM_ORDER[i] for t in RIMT[k]]
        rc = curve(TOP[i - 1], TOP[i]) if i else None; fc = curve(BOT[i - 1], BOT[i]) if i else None
        assert len(order) == (9 if rc else 12), (i, len(order))
        # roof
        if rc:
            blk = roof16 if rc == 'S16' else roof32
            if TOP[i] < TOP[i - 1]: blk = flip(blk)
            y0 = min(TOP[i], TOP[i - 1]) - 16; w.alpha_composite(blk, (x0, y0)) if y0 + blk.height > 0 else None
            for k in range(3):
                for r, y in enumerate(range(y0 - 16, -16, -16)): w.alpha_composite(FILLT[(k + 2 * r + 1) % 4], (x0 + 16 * k, y))
        for k, t in enumerate(order):
            x = x0 + (48 if rc else 0) + 16 * k; y = TOP[i] - 16
            if y >= 0: w.alpha_composite(t, (x, y))
            for r, yy in enumerate(range(y - 16, -16, -16)): w.alpha_composite(FILLT[(x // 16 + 2 * r + 2) % 4], (x, yy))
        # floor
        xs = x0
        if fc:
            blk = (floor16 if fc == 'S16' else floor32)[f]
            if BOT[i] > BOT[i - 1]: blk = flip(blk)
            y0 = min(BOT[i], BOT[i - 1]); w.alpha_composite(blk, (x0, y0)); xs = x0 + 48
            for x in range(x0, xs, 16):
                for y in range(y0 + blk.height, 224, 16): w.alpha_composite(ffill, (x, y))
        for x in range(xs, x0 + 192, 16):
            fx = (x // 16 + f) % 8 * 16   # shortcut: frame-to-column mapping of the shipped rim is not verified, check in src/hazard.c before import
            w.alpha_composite(frim.crop((fx, 0, fx + 16, 16)), (x, BOT[i]))
            for y in range(BOT[i] + 16, 224, 16): w.alpha_composite(ffill, (x, y))
    return w

def screen(wd, x):
    s = Image.new('RGBA', (320, 224), TRIP + (255,))
    for p, y, par in PLANES:
        o = -((x // par) % p.width)
        s.alpha_composite(p, (o, y)); s.alpha_composite(p, (o + p.width, y))
    s.alpha_composite(wd.crop((x, 0, x + 320, 224)))
    return s

if __name__ == '__main__':
    worlds = [world(f) for f in range(8)]
    for name, x in [('mock_a', 112), ('mock_b', 496), ('mock_c', 1072)]:
        m = screen(worlds[0], x); m.save(os.path.join(D, name + '_1x.png')); sc(m, 3).save(os.path.join(D, name + '_3x.png'))
    # tile sheet
    sh = Image.new('RGBA', (360, 136), (40, 30, 60, 255))
    sh.alpha_composite(rimA, (4, 4)); sh.alpha_composite(rimB, (72, 4)); sh.alpha_composite(solo[0], (140, 4)); sh.alpha_composite(solo[1], (160, 4)); sh.alpha_composite(fillI, (180, 4))
    sh.alpha_composite(roof16, (4, 24)); sh.alpha_composite(roof32, (56, 24)); sh.alpha_composite(flip(roof16), (108, 24)); sh.alpha_composite(flip(roof32), (160, 24))
    sh.alpha_composite(floor16[0], (4, 80)); sh.alpha_composite(floor32[0], (56, 80)); sh.alpha_composite(flip(floor16[0]), (108, 80)); sh.alpha_composite(flip(floor32[0]), (160, 80))
    sh.alpha_composite(frim, (212, 24)); sh.alpha_composite(ffill, (212, 44))
    sh.save(os.path.join(D, 'tiles_1x.png')); sc(sh, 3).save(os.path.join(D, 'tiles_3x.png'))
    an = Image.new('RGBA', (8 * 52 + 4, 32 + 48 + 12), (40, 30, 60, 255))
    for f in range(8): an.alpha_composite(floor16[f], (4 + 52 * f, 4)); an.alpha_composite(floor32[f], (4 + 52 * f, 40))
    sc(an, 3).save(os.path.join(D, 'floor_anim_frames_3x.png'))
    k = 1   # 1x keeps each gif under 3 MB; the gallery scales it with pixelated rendering
    xs = list(range(0, W - 320, 4)); parts = 1
    while True:
        size = []; per = -(-len(xs) // parts)
        for p in range(parts):
            fr = [screen(worlds[(x // 4) % 8], x).convert('RGB').quantize(48, dither=Image.NONE) for x in xs[p * per:(p + 1) * per]]
            fn = os.path.join(D, 'scroll_%d.gif' % (p + 1)); fr[0].save(fn, save_all=True, append_images=fr[1:], duration=90, loop=0, optimize=False)
            size.append(os.path.getsize(fn))
        if max(size) < 3_000_000: break
        parts += 1
    for fno, x in [(28, 112), (124, 496), (268, 1072)]: sc(screen(worlds[fno % 8], x), 2).save(os.path.join(D, 'gif_frame_%d_2x.png' % fno))
    zz = Image.new('RGBA', (2 * 112 + 4, 2 * 96 + 4), (0, 0, 0, 255))   # close-ups of the curves in place, for the view passes
    for j, (x, y) in enumerate([(184, 0), (376, 0), (376, 112), (760, 112)]):
        zz.paste(screen(worlds[0], x - 104).crop((104, y, 216, y + 96)), (j % 2 * 116, j // 2 * 100))
    sc(zz, 5).save(os.path.join(D, 'closeup_5x.png'))
    # counts
    def uniq(ims, drop=()): return {c.tobytes() for im in ims for c in cells(im)} - {EMPTY} - set(drop)
    fillb = {c.tobytes() for c in FILLT}
    n = dict(rimA=len(uniq([rimA])), rimB=len(uniq([rimB])), solo=len(uniq(solo)), fill=len(fillb), s16=len(uniq([roof16], fillb)), s32=len(uniq([roof32], fillb)))
    roof_total = len(uniq([rimA, rimB, fillI, roof16, roof32] + solo))
    gfill = {ffill.tobytes()}
    f16 = len(uniq([floor16[0]], gfill)); f32 = len(uniq([floor32[0]], gfill))
    dedup = len(uniq(floor16 + floor32, gfill))
    gsz = size
    num = [
     f"roof (take 1 slate, v3): {roof_total} tiles = rim A {n['rimA']} + rim B {n['rimB']} + solo rim {n['solo']} + fill {n['fill']} + curve S16 {n['s16']} + curve S32 {n['s32']} (hflip for the other direction); colours {len(used)} of 15; 1 palette slot; static",
     f"floor curves: S16 {f16} tiles + S32 {f32} tiles = {f16 + f32} static (hflip for the other direction; cells equal to the plain gum fill tile are not counted)",
     f"floor curves animated: {(f16 + f32) * 8} tiles as 8 frame auto-animation runs ({f16 + f32} x 8); {dedup} if identical frames were shared (auto-animation cannot share them)",
     f"tripstrip sheet: 56 -> 32 after freeing roles t3..t6 (24 tiles), + {(f16 + f32) * 8} floor curve tiles = {32 + (f16 + f32) * 8}; roof sheet {roof_total}; sum of new tiles {roof_total + (f16 + f32) * 8}",
     f"C-ROM: {(roof_total + (f16 + f32) * 8)} new tiles x 64 bytes per file = {(roof_total + (f16 + f32) * 8) * 64} bytes per file on top of 305152 of 2097152 used",
     "curves: S16 = 4:1, 2:1, 4:1 over 48 px (16 px rise); S32 = 2:1, 1:1, 2:1 over 48 px (32 px rise); both start and end flat on the 16 px grid",
     "sequence (seed 6, snapped): TOP " + str(TOP) + " BOT " + str(BOT),
     "curves used in the mock: roof " + str([curve(TOP[i - 1], TOP[i]) for i in range(1, 8)]) + " floor " + str([curve(BOT[i - 1], BOT[i]) for i in range(1, 8)]),
     "height tables: heights.json (per piece, per tile column, 16 values each; measured from the typed pixels)",
     f"scroll gif: 4 px per 90 ms frame = 44.4 px/s (target 45), {k}x scale, lip frame steps once per gif frame, {parts} part(s), bytes {gsz}",
    ]
    open(os.path.join(D, 'numbers.txt'), 'w').write('\n'.join(num) + '\n'); print('\n'.join(num))
