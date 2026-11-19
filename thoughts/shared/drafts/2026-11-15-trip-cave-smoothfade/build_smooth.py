"""Sloped fade for the TRIP-CAVE curve pieces. Joins, shifts pixel columns by the typed lip offset, stamps typed patches, palette-maps,
places, cuts into tiles, scales and counts. No drawing happens here.
Run: python3.14 -I build_smooth.py [dump.txt]   (imports ../2026-11-15-trip-cave-fade/build_fade.py and through it the v3 build script)"""
import os, sys, json
from PIL import Image
D = os.path.dirname(os.path.abspath(__file__)); FD = os.path.join(D, '..', '2026-11-15-trip-cave-fade')
sys.path.insert(0, D); sys.path.insert(0, FD)
import build_fade as BF
import cave_smooth_art as S
B, F = BF.B, BF.F
PAD = 64
def chars(im, pal):
    inv = {v: k for k, v in pal.items()}
    return [''.join(inv[im.getpixel((x, y))[:3]] if im.getpixel((x, y))[3] else '.' for x in range(im.width)) for y in range(im.height)]
FA_R, FB_R = B.join(F.FLOOR_FADE_A, 'a'), B.join(F.FLOOR_FADE_B, 'b'); RA_R, RB_R = B.join(F.ROOF_FADE_A, 'ra'), B.join(F.ROOF_FADE_B, 'rb')
FILL_R = chars(B.ffill, B.GUM)
for k, name in (('S16', 'floor_S16 (48x32, rises 16)'), ('S32', 'floor_S32 (48x48, rises 32)')):   # typed offsets must sit on the drawn lip
    m = sum(B.HEIGHTS[name], []); p = S.PROFILE[k]
    assert len(p) == 48 and all(abs(a - b) <= 1 for a, b in zip(m, p)) and all(0 <= p[i] - p[i + 1] <= 2 for i in range(47)), k
FDEPTH = 16 + 16 * BF.N_FLOOR - 2      # lip surface to fade A: 30 px, as in the flat columns
ROFF = 32                              # roof block starts 32 px above the piece top row

def floor_rows(kind, f):
    blk = (B.floor16 if kind == 'S16' else B.floor32)[f]; pc = chars(blk, B.GUM); H = blk.height + 80
    cols = []
    for x, p in enumerate(S.PROFILE[kind]):
        a = p + FDEPTH
        cols.append(''.join((pc[y][x] if y < blk.height else FILL_R[y % 16][x % 16]) if y < a else FA_R[y - a][x % 32] if y < a + 16
                            else FB_R[y - a - 16][x % 32] if y < a + 32 else '0' for y in range(H)))
    return B.stamp(B.transpose(cols), S.FLOOR_FIX[kind])
def roof_rows(kind):
    pc = chars(B.roof16 if kind == 'S16' else B.roof32, BF.PALR); p = S.PROFILE[kind]; cols = []
    for x in range(48):
        e = 16 + p[0] - p[x]          # nominal rock edge below the piece top: the floor curve upside down
        cols.append(''.join(pc[y][x] if y >= e - 16 else RA_R[y - e + 32][x % 64] if y >= e - 32 else RB_R[y - e + 48][x % 64] if y >= e - 48 else '0'
                            for y in range(-ROFF, len(pc))))
    return B.stamp(B.transpose(cols), S.ROOF_FIX[kind])
FBLK = {k: [B.img(floor_rows(k, f), B.GUM) for f in range(8)] for k in ('S16', 'S32')}
RBLK = {k: B.img(roof_rows(k), BF.PALR) for k in ('S16', 'S32')}

def world(f, lift=0):
    """build_fade.world with the curve blocks replaced by the sloped blocks; flat columns are unchanged"""
    TOP = [t + lift for t in B.TOP]
    w = Image.new('RGBA', (B.W, 224 + PAD), (0, 0, 0, 0))
    for i in range(len(B.SEQ)):
        x0 = 192 * i; order = [t for k in B.RIM_ORDER[i] for t in B.RIMT[k]]
        rc = B.curve(TOP[i - 1], TOP[i]) if i else None; fc = B.curve(B.BOT[i - 1], B.BOT[i]) if i else None
        xr = x0
        if rc:
            blk = RBLK[rc]; y0 = min(TOP[i], TOP[i - 1]) - 16 - ROFF + PAD; xr = x0 + 48
            w.paste(BF.BLACK, (x0, 0, x0 + 48, max(0, y0))); w.alpha_composite(B.flip(blk) if TOP[i] < TOP[i - 1] else blk, (x0, y0))
        for k, t in enumerate(order):
            x = xr + 16 * k; BF.roof_col(w, x, TOP[i] - 16 + PAD); w.alpha_composite(t, (x, TOP[i] - 16 + PAD))
        xs = x0
        if fc:
            blk = FBLK[fc][f]; y0 = min(B.BOT[i], B.BOT[i - 1]) + PAD; xs = x0 + 48
            w.alpha_composite(B.flip(blk) if B.BOT[i] > B.BOT[i - 1] else blk, (x0, y0)); w.paste(BF.GUM0, (x0, y0 + blk.height, x0 + 48, max(w.height, y0 + blk.height)))
        for x in range(xs, x0 + 192, 16):
            fx = (x // 16 + f) % 8 * 16
            BF.floor_col(w, x, B.BOT[i] + PAD); w.alpha_composite(B.frim.crop((fx, 0, fx + 16, 16)), (x, B.BOT[i] + PAD))
    return w.crop((0, PAD, B.W, 224 + PAD))

# ---------------------------------------------------------------- tiles and lookup
def solid(c): return Image.new('RGBA', (16, 16), c).tobytes()
def grid(im): return {(x // 16, y // 16): im.crop((x, y, x + 16, y + 16)).tobytes() for y in range(0, im.height, 16) for x in range(0, im.width, 16)}
NEW = {'floor': {}, 'roof': {}}; ANIM = set(); MAP = {'floor': {}, 'roof': {}}
def name(side, b, known):
    if b in known: return known[b]
    return NEW[side].setdefault(b, ('F' if side == 'floor' else 'R') + str(len(NEW[side])))
kf = {B.ffill.tobytes(): 'fill', solid(BF.GUM0): 'solid', B.EMPTY: 'empty'}
kf.update({c.tobytes(): 'A%d' % i for i, c in enumerate(BF.FA)}); kf.update({c.tobytes(): 'B%d' % i for i, c in enumerate(BF.FB)})
kr = {solid(BF.BLACK): 'black', B.EMPTY: 'empty'}
for n, cs in (('fill', B.FILLT), ('A', BF.RA), ('B', BF.RB)): kr.update({c.tobytes(): n + str(i) for i, c in enumerate(cs)})
for k in ('S16', 'S32'):
    gs = [grid(b) for b in FBLK[k]]; ps = [grid(b) for b in (B.floor16 if k == 'S16' else B.floor32)]
    for c in range(3):
        col = []
        for r in range(FBLK[k][0].height // 16):
            if (c, r) in ps[0] and all(gs[f][c, r] == ps[f][c, r] for f in range(8)) and gs[0][c, r] not in kf: col.append('piece')
            else:
                col.append(name('floor', gs[0][c, r], kf))
                if len({g[c, r] for g in gs}) > 1: ANIM.add(col[-1])
        MAP['floor'][k + '_col%d' % c] = col
    g = grid(RBLK[k]); p = grid(B.roof16 if k == 'S16' else B.roof32)
    for c in range(3):
        MAP['roof'][k + '_col%d' % c] = ['piece' if r >= 2 and g[c, r] == p[c, r - 2] and g[c, r] not in kr else name('roof', g[c, r], kr) for r in range(RBLK[k].height // 16)]

if __name__ == '__main__':
    out = lambda n: os.path.join(D, n); w0 = world(0)
    for nm, x in [('mock_a', 112), ('mock_b', 496), ('mock_c', 1072)]:
        m = B.screen(w0, x); m.save(out(nm + '_1x.png')); B.sc(m, 3).save(out(nm + '_3x.png'))
    wd = world(0, 32); B.sc(B.screen(wd, 112), 3).save(out('demo_deep_roof_3x.png'))
    B.sc(B.screen(world(3), 760), 3).save(out('scroll_still_3x.png'))
    cu = Image.new('RGBA', (272, 96 + 4 + 112), B.TRIP + (255,))       # close-ups for the view passes: deep roof curves, floor S16, floor S32
    cu.alpha_composite(wd.crop((176, 0, 448, 96))); cu.alpha_composite(w0.crop((352, 112, 464, 224)), (0, 100)); cu.alpha_composite(w0.crop((736, 112, 848, 224)), (116, 100))
    B.sc(cu, 3).save(out('closeup_3x.png'))
    sh = Image.new('RGBA', (4 * 52 + 4, 136), (60, 60, 70, 255))       # the four sloped blocks as typed (rising / falling to the right)
    for j, b in enumerate([FBLK['S16'][0], FBLK['S32'][0], RBLK['S16'], RBLK['S32']]): sh.alpha_composite(b, (4 + 52 * j, 4))
    B.sc(sh, 3).save(out('blocks_3x.png'))
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'w') as fh:
            for k in ('S16', 'S32'):
                fh.write('floor %s\n' % k + '\n'.join('%3d %s' % (y, r) for y, r in enumerate(floor_rows(k, 0))) + '\nroof %s\n' % k + '\n'.join('%3d %s' % (y, r) for y, r in enumerate(roof_rows(k))) + '\n')
    nf, nr = len(NEW['floor']), len(NEW['roof'])
    json.dump({'note': 'Per curve piece and piece tile column (piece drawn rising (floor) / falling (roof) to the right; hflip swaps columns 0 and 2 and flips each tile). '
               'floor: list index = tile row below the piece top row; below the list: solid. roof: list index 0 = tile row 2 above the piece top row; above the list: black. '
               'piece = the v3 curve tile unchanged, fill/fillN = plain fill tile, A*/B* = flat fade tiles, solid/black, F*/R* = new sloped tiles.',
               'row0_offset_tiles': {'floor': 0, 'roof': -2}, 'map': MAP, 'new_tiles': {'floor': nf, 'roof': nr}, 'floor_tiles_that_differ_per_lip_frame': sorted(ANIM)}, open(out('fade_map.json'), 'w'), indent=1)
    num = [f"sloped fade: fade A starts {FDEPTH} px under the lip surface in every pixel column (flat columns: the same {FDEPTH}); roof fade A starts 16 px above the nominal rock edge (the floor curve upside down)",
           f"new floor tiles: {nf} (static; tiles that hold a moving lip pixel: {sorted(ANIM) or 'none'})", f"new roof tiles: {nr} (static)",
           f"C-ROM: {nf + nr} new tiles x 64 bytes per file = {(nf + nr) * 64} bytes per file (on top of the 14 flat fade tiles, 896 bytes per file)",
           "lookup (rows top to bottom; floor row 0 = piece top row, roof row 0 = 2 tile rows above the piece top row):"]
    for side in ('floor', 'roof'):
        for k, col in MAP[side].items(): num.append(f"  {side} {k}: " + ' '.join(col))
    open(out('numbers.txt'), 'w').write('\n'.join(num) + '\n'); print('\n'.join(num))
