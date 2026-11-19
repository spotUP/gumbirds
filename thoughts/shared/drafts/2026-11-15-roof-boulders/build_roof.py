"""Places the hand-typed roof rows of roof_boulders_art.py over the v3 curve piece, cuts tiles, checks the lookup against the
smooth-fade fade_map.json (must be identical) and writes the gallery images. No drawing happens here.
Run: python3.14 -I build_roof.py"""
import os, sys, json
from PIL import Image
D = os.path.dirname(os.path.abspath(__file__)); SD = os.path.join(D, '..', '2026-11-15-trip-cave-smoothfade')
sys.path.insert(0, D); sys.path.insert(0, SD)
import build_smooth as M
import roof_boulders_art as A
B, BF = M.B, M.BF
OLD = dict(M.RBLK); OLDMAP = json.load(open(os.path.join(SD, 'fade_map.json')))
def rows(kind):
    pc = M.chars(B.roof16 if kind == 'S16' else B.roof32, BF.PALR); t = A.ROOF[kind]
    assert all(len(r) == 48 for r in t), [i for i, r in enumerate(t) if len(r) != 48]
    assert len(t) == (48 if kind == 'S16' else 64) and not any('.' in r for r in t[:32])
    assert set(''.join(t)) <= set('01234.'), 'typed rows use fade tones only'
    out = [''.join(pc[y - 32][x] if c == '.' else c for x, c in enumerate(r)) for y, r in enumerate(t)]
    return out + pc[len(t) - 32:]
NEWBLK = {k: B.img(rows(k), BF.PALR) for k in ('S16', 'S32')}
def roofmap(blk):
    new = {}; mp = {}
    for k in ('S16', 'S32'):
        g = M.grid(blk[k]); p = M.grid(B.roof16 if k == 'S16' else B.roof32)
        for c in range(3):
            mp[k + '_col%d' % c] = ['piece' if r >= 2 and g[c, r] == p[c, r - 2] and g[c, r] not in M.kr
                                    else M.kr.get(g[c, r]) or new.setdefault(g[c, r], 'R%d' % len(new)) for r in range(blk[k].height // 16)]
    return mp, new
MAP, NEW = roofmap(NEWBLK); OM, ONEW = roofmap(OLD)
assert OM == OLDMAP['map']['roof'], 'old map reproduces'
assert MAP == OLDMAP['map']['roof'] and len(NEW) == OLDMAP['new_tiles']['roof'] == 18, MAP
def colours(blks): return {px[:3] for b in blks.values() for px in b.getdata() if px[3]}
assert colours(NEWBLK) <= colours(OLD) | set(BF.PALR.values()) and colours(NEWBLK) <= set(BF.PALR.values())
def world(blk, f=0, lift=0):
    M.RBLK = blk
    try: return M.world(f, lift)
    finally: M.RBLK = OLD
def sheet(tiles, cols):
    n = len(tiles); im = Image.new('RGBA', (16 * cols, 16 * -(-n // cols)), (0, 0, 0, 0))
    for i, t in enumerate(tiles): im.alpha_composite(Image.frombytes('RGBA', (16, 16), t), (i % cols * 16, i // cols * 16))
    return im
if __name__ == '__main__':
    out = lambda n: os.path.join(D, n); bg = B.TRIP + (255,)
    def flat(im):
        o = Image.new('RGBA', im.size, bg); o.alpha_composite(im); return o
    for tag, blk in (('before', OLD), ('after', NEWBLK)):
        wd = world(blk, 0, 32)
        B.sc(B.screen(wd, 112), 3).save(out('demo_deep_roof_%s_3x.png' % tag))
        B.sc(flat(wd.crop((176, 0, 448, 96))), 3).save(out('strip_%s_3x.png' % tag))         # both sloped roof pieces and the flat run between
        B.sc(flat(wd.crop((176, 0, 256, 96))), 6).save(out('crop_gentle_%s_6x.png' % tag))   # gentle (16 px) slope
        B.sc(flat(wd.crop((368, 0, 448, 96))), 6).save(out('crop_steep_%s_6x.png' % tag))    # steep (32 px) slope
        B.sc(flat(wd.crop((176, 0, 256, 96))), 3).save(out('crop_gentle_%s_3x.png' % tag))
        B.sc(flat(wd.crop((368, 0, 448, 96))), 3).save(out('crop_steep_%s_3x.png' % tag))
        B.sc(B.screen(world(blk, 3), 760), 3).save(out('scroll_still_%s_3x.png' % tag))
        sh = Image.new('RGBA', (2 * 52 + 4, 88), (60, 60, 70, 255))
        for j, k in enumerate(('S16', 'S32')): sh.alpha_composite(blk[k], (4 + 52 * j, 4))
        B.sc(sh, 3).save(out('blocks_%s_3x.png' % tag))
    order = sorted(NEW.items(), key=lambda kv: int(kv[1][1:]))
    s = sheet([t for t, _ in order], 18); s.save(out('roof_tiles_R0-R17_1x.png')); B.sc(s, 3).save(out('roof_tiles_R0-R17_3x.png'))
    fl = sorted(M.NEW['floor'].items(), key=lambda kv: int(kv[1][1:]))
    s = sheet([t for t, _ in fl] + [t for t, _ in order], 37); s.save(out('sloped_tiles_F0-F18_R0-R17_1x.png'))
    oo = sorted(ONEW.items(), key=lambda kv: int(kv[1][1:]))
    changed = [n for (t, n), (t0, _) in zip(order, oo) if t != t0]
    fm = dict(OLDMAP); json.dump(fm, open(out('fade_map.json'), 'w'), indent=1)
    num = ['roof tiles: %d (R0-R17), changed against the smooth-fade draft: %s' % (len(NEW), ' '.join(changed)),
           'floor tiles: %d (F0-F18), unchanged' % len(fl), 'total sloped tiles: %d + 14 flat fade tiles, unchanged count' % (len(fl) + len(NEW)),
           'roof lookup identical to smooth-fade fade_map.json: yes (asserted)', 'colours used: %d, all in the roof palette (%d entries)' % (len(colours(NEWBLK)), len(BF.PALR)),
           'pixels that differ from the v3 piece inside restored rim boulders: outline row only (see README)']
    open(out('numbers.txt'), 'w').write('\n'.join(num) + '\n'); print('\n'.join(num))
