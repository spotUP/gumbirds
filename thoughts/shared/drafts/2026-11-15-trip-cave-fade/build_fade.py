"""Places the hand-typed fade rows of cave_fade_art.py into the v3 mock. Joins, palette-maps, places, scales, counts. No drawing happens here.
Run: python3.14 -I build_fade.py   (imports ../2026-11-15-trip-cave-v3/build_cave3.py, which rewrites its own heights.json with the same content)"""
import os, sys
from PIL import Image
D = os.path.dirname(os.path.abspath(__file__)); V3 = os.path.join(D, '..', '2026-11-15-trip-cave-v3')
sys.path.insert(0, D); sys.path.insert(0, V3)
import build_cave3 as B
import cave_fade_art as F

N_FLOOR, N_ROOF, FADE_ROWS = 1, 0, 2      # fill rows between lip/rim and the fade; fade rows of 16 px
PALR = dict(B.PAL, **{'0': (0, 0, 0)})    # roof palette + pure black
GUM0 = B.GUM['0'] + (255,); BLACK = (0, 0, 0, 255)
fa = B.img(B.check(B.join(F.FLOOR_FADE_A, 'floor A'), 32, 16, 'floor A'), B.GUM)
fb = B.img(B.check(B.join(F.FLOOR_FADE_B, 'floor B'), 32, 16, 'floor B'), B.GUM)
ra = B.img(B.check(B.join(F.ROOF_FADE_A, 'roof A'), 64, 16, 'roof A'), PALR)
rb = B.img(B.check(B.join(F.ROOF_FADE_B, 'roof B'), 64, 16, 'roof B'), PALR)
assert set(''.join(F.FLOOR_FADE_B[0][-1] + F.FLOOR_FADE_B[1][-1])) == {'0'}                    # floor ends solid
assert set(''.join(s[0] for s in F.ROOF_FADE_B)) == {'0'}                                      # roof ends solid black
FA, FB, RA, RB = B.cells(fa), B.cells(fb), B.cells(ra), B.cells(rb)

def floor_col(w, x, s, fixed=None):
    """s = top of the lip tile of this 16 px column: lip, N fill rows, fade A, fade B, darkest gum. fixed = alternative: fade A at one fixed row"""
    y = s + 16 + 16 * N_FLOOR if fixed is None else fixed
    for yy in range(s + 16, y, 16): w.paste(B.ffill, (x, yy))
    w.paste(FA[x // 16 % 2], (x, y)); w.paste(FB[x // 16 % 2], (x, y + 16)); w.paste(GUM0, (x, y + 32, x + 16, max(w.height, y + 32)))
def roof_col(w, x, s, fillrow=0):
    """s = top of the rim tile of this column: going up N fill rows, fade A, fade B, black"""
    for r in range(N_ROOF): w.paste(B.FILLT[(x // 16 + 2 * r + 2) % 4], (x, s - 16 - 16 * r))
    y = s - 16 - 16 * N_ROOF
    w.paste(RA[x // 16 % 4], (x, y)); w.paste(RB[x // 16 % 4], (x, y - 16)); w.paste(BLACK, (x, min(-64, y - 16), x + 16, y - 16))

def world(f, lift=0, fixed=None):
    """the v3 world with the fade rows placed per 16 px column. lift pushes the roof down (demo only) so its fade is on screen."""
    TOP = [t + lift for t in B.TOP]
    PAD = 64; w = Image.new('RGBA', (B.W, 224 + PAD), (0, 0, 0, 0))   # PAD rows above the screen so negative rows can be pasted
    for i in range(len(B.SEQ)):
        x0 = 192 * i; order = [t for k in B.RIM_ORDER[i] for t in B.RIMT[k]]
        rc = B.curve(TOP[i - 1], TOP[i]) if i else None; fc = B.curve(B.BOT[i - 1], B.BOT[i]) if i else None
        xr = x0
        if rc:
            blk = B.roof16 if rc == 'S16' else B.roof32
            if TOP[i] < TOP[i - 1]: blk = B.flip(blk)
            y0 = min(TOP[i], TOP[i - 1]) - 16; xr = x0 + 48
            if rc == 'S16':
                for k in range(3): roof_col(w, x0 + 16 * k, y0 + PAD)    # all six tiles are typed: the fade starts above the block
                w.alpha_composite(blk, (x0, y0 + PAD))
            else:                                                        # S32: the fade replaces the plain fill cells above the typed tiles, one 16 px stair per column
                fl = TOP[i] < TOP[i - 1]
                for k in range(3):
                    cx = 2 - k if fl else k; roof_col(w, x0 + 16 * k, y0 + 16 * min(c[1] for c in B.A.ROOF_S32 if c[0] == cx) + PAD)
                for (cx, cy), rows in B.A.ROOF_S32.items():
                    t = B.img(rows, B.PAL); w.alpha_composite(B.flip(t) if fl else t, (x0 + 16 * ((2 - cx) if fl else cx), y0 + 16 * cy + PAD))
        for k, t in enumerate(order):
            x = xr + 16 * k; roof_col(w, x, TOP[i] - 16 + PAD); w.alpha_composite(t, (x, TOP[i] - 16 + PAD))
        xs = x0
        if fc:
            blk = (B.floor16 if fc == 'S16' else B.floor32)[f]
            if B.BOT[i] > B.BOT[i - 1]: blk = B.flip(blk)
            y0 = min(B.BOT[i], B.BOT[i - 1]); xs = x0 + 48; top = B.floor_top(blk)
            for k in range(3):   # measured: the tile row that holds the lowest lip pixel of this column is the lip row
                floor_col(w, x0 + 16 * k, y0 + max(top[16 * k:16 * k + 16]) // 16 * 16 + PAD, fixed and fixed + PAD)
            keep = blk.copy()    # the typed curve stays above the fade: cut the block below each column's lip row + N fill rows
            for k in range(3):
                cut = max(top[16 * k:16 * k + 16]) // 16 * 16 + 16 + 16 * N_FLOOR if fixed is None else fixed - y0
                keep.paste((0, 0, 0, 0), (16 * k, cut, 16 * k + 16, blk.height))
            w.alpha_composite(keep, (x0, y0 + PAD))
        for x in range(xs, x0 + 192, 16):
            fx = (x // 16 + f) % 8 * 16
            floor_col(w, x, B.BOT[i] + PAD, fixed and fixed + PAD); w.alpha_composite(B.frim.crop((fx, 0, fx + 16, 16)), (x, B.BOT[i] + PAD))
    return w.crop((0, PAD, B.W, 224 + PAD))

if __name__ == '__main__':
    w0 = world(0); out = lambda n: os.path.join(D, n)
    for name, x in [('mock_a', 112), ('mock_b', 496), ('mock_c', 1072)]:
        m = B.screen(w0, x); m.save(out(name + '_1x.png')); B.sc(m, 3).save(out(name + '_3x.png'))
    B.sc(B.screen(world(0, 32), 112), 3).save(out('demo_deep_roof_3x.png'))          # roof 32 px lower than seed 6, to show both roof fade rows
    B.sc(B.screen(world(0, 0, 192), 1072), 3).save(out('alt_fixed_rows_mock_c_3x.png'))   # alternative: fade A always at screen row 192, B at 208
    B.sc(B.screen(world(3), 760), 3).save(out('scroll_still_3x.png'))                # lip frame 3 at scroll x 760
    # tile sheet: fade rows in their column order, twice side by side to show the left/right repeat
    sh = Image.new('RGBA', (148, 176), (90, 33, 90, 255))
    for k in range(8):   # floor: fill, A, B, darkest gum
        sh.paste(B.ffill, (4 + 16 * k, 4)); sh.paste(FA[k % 2], (4 + 16 * k, 20)); sh.paste(FB[k % 2], (4 + 16 * k, 36)); sh.paste(GUM0, (4 + 16 * k, 52, 20 + 16 * k, 60))
    for k in range(8):   # roof: black, B, A, fill, rim A
        sh.paste(BLACK, (4 + 16 * k, 68, 20 + 16 * k, 76)); sh.paste(RB[k % 4], (4 + 16 * k, 76)); sh.paste(RA[k % 4], (4 + 16 * k, 92))
        sh.alpha_composite(B.FILLT[(k + 2) % 4], (4 + 16 * k, 108)); sh.alpha_composite(B.RIMT['A'][k % 4], (4 + 16 * k, 124))
    for k in range(8):   # roof without the fill row (N = 0, as placed in the mock)
        sh.paste(RA[k % 4], (4 + 16 * k, 144)); sh.alpha_composite(B.RIMT['B'][k % 4], (4 + 16 * k, 160))
    sh.save(out('tiles_1x.png')); B.sc(sh, 3).save(out('tiles_3x.png'))
    uniq = lambda ims: len({c.tobytes() for c in ims})
    cu = lambda parts: ''.join(sorted(set(''.join(''.join(r) for p in parts for r in p))))
    num = [
     f"floor: lip band 16 px, N = {N_FLOOR} fill row, {FADE_ROWS} fade rows (A, B) of 16 px, then solid darkest gum. Lip top to solid = {16 + 16 * N_FLOOR + 32 - 2} px (the last 2 rows of B are solid)",
     f"roof: rim 16 px, N = {N_ROOF} fill rows, {FADE_ROWS} fade rows (A, B) of 16 px, then black. Curve blocks count as rim: the fade starts above the block top",
     f"floor fade tiles: {uniq(FA + FB)} (A 2 + B 2, 32 px repeat) + 1 solid darkest-gum tile = {uniq(FA + FB) + 1}; static",
     f"roof fade tiles: {uniq(RA + RB)} (A 4 + B 4, 64 px repeat) + 1 solid black tile = {uniq(RA + RB) + 1}; static",
     f"floor colours used: A '{cu(F.FLOOR_FADE_A)}', B '{cu(F.FLOOR_FADE_B)}' of the gum palette; no colour added. The gum palette has NO pure black: the floor ends in gum colour 0 {B.GUM['0']}",
     f"roof colours used: A '{cu(F.ROOF_FADE_A)}', B '{cu(F.ROOF_FADE_B)}'; '0' = pure black (0,0,0) is ADDED to the slate palette: 11 of 15 colours",
     f"new tiles: {uniq(FA + FB) + uniq(RA + RB) + 2} x 64 bytes per C-ROM file = {(uniq(FA + FB) + uniq(RA + RB) + 2) * 64} bytes per file",
     f"visible at 320x224 with seed 6: floor lip rows {sorted(set(B.BOT))} -> solid starts at lip + {16 + 16 * N_FLOOR + 30}; roof rim bottoms {sorted(set(B.TOP))} -> fade A is on screen only where the roof is 32 px deep",
    ]
    open(out('numbers.txt'), 'w').write('\n'.join(num) + '\n'); print('\n'.join(num))
