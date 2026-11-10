"""Visual proof by pixels for the city background (python3.14 -I, Pillow).
Usage: check_bg_pixels.py city_sprites.c hero_sprites.c obs_sprites.c pre_start.png bg_a.png bg_b.png result.txt.bg
bg file (written by boot_check.lua at the two snapshot frames): "a far mid roof writes" / "b far mid roof writes"
(scroll px of each layer as the game exported it, and the column strip write counter).
Checks, each independent of the hero and obstacle checks (only colours unique to one layer are counted):
  1. the sky backdrop fills the top band, before start and during play
  2. each layer's own colours appear in its y band during play and not above it
  3. the city is still: the exported scroll delta of each layer between the snapshots is 0 and the layer's pixels
     match at shift 0 (arena slice: no scroll in play)
  4. the column write sentinel did not grow
Exit 1 on failure."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pixel_common as pc
from PIL import Image

LAYERS = ["far", "mid", "roof"]
Y_BAND = {"far": (64, 176), "mid": (96, 176), "roof": (176, 224)}
Y_MEASURE = {"far": (66, 108), "mid": (110, 174), "roof": (178, 222)}
HERO_MASK = (28, 112)
SKY = (0x1a, 0x12, 0x38)
# Colours the game writes into the far and mid palettes at run time (src/bg.c lamp_set): BG_LAMP_OFF,
# NG_RGB5(7, 4, 8). Shared by both layers, so never layer-unique; the far lamps in their off phase sit above
# the mid band and would otherwise count as mid pixels there.
RUNTIME_SHARED = [(57, 33, 66)]
MIN_BAND, MAX_ABOVE, MIN_SKY = 300, 5, 0.9
SKY_OBJ_X = (200, 296)         # moon and clouds overlap the far band; skipped when measuring far
MIN_STILL = 0.95
FULL = (1 << 320) - 1


def load_bg(path):
    out = {}
    for line in open(path):
        t = line.split()
        if t:
            out[t[0]] = [int(v) for v in t[1:]]
    return out


def rows_mask(im, cols, y0, y1, skip_x=None):
    w, h = im.size
    px = im.load()
    rows = []
    for y in range(y0, y1):
        m = 0
        sy = min(h - 1, int(y * h / 224.0))
        for x in range(320):
            if HERO_MASK[0] <= x < HERO_MASK[1] or (skip_x and skip_x[0] <= x < skip_x[1]):
                continue
            p = px[min(w - 1, int(x * w / 320.0)), sy]
            if any(pc.near(p, c) for c in cols):
                m |= 1 << x
        rows.append(m)
    return rows


def rot_left(m, d):
    """Bit x of result == bit (x + d) mod 320 of m."""
    return ((m >> d) | (m << (320 - d))) & FULL if d else m


def shift_scores(a_rows, b_rows):
    """Scene moves left by d: A[x] == B[x - d], so B rotated left... score = |A & rot_right(B)| ; computed as
    |rot_left(A, d) & B| since A[x + d] == B[x]."""
    out = []
    for d in range(320):
        out.append(sum((rot_left(a, d) & b).bit_count() for a, b in zip(a_rows, b_rows)))
    return out


def pixel_scores(ima, imb, y0, y1):
    """Per shift d: count of pixels where A[x + d] == B[x] (hero columns skipped), and the compared total."""
    w, h = ima.size
    sz = (320, 224)
    a, b = ima.resize(sz, Image.NEAREST).load(), imb.resize(sz, Image.NEAREST).load()
    xs = [x for x in range(320) if not HERO_MASK[0] <= x < HERO_MASK[1]]
    out = []
    for d in range(320):
        n = 0
        for y in range(y0, y1):
            for x in xs:
                if a[(x + d) % 320, y] == b[x, y]:
                    n += 1
        out.append(n)
    return out, len(xs) * (y1 - y0)


def main():
    city_c, hero_c, obs_c, pre, a_png, b_png, bg_txt = sys.argv[1:8]
    bg = load_bg(bg_txt)
    others = set(pc.colours(hero_c, "hero")) | set(pc.colours(obs_c, "obs")) | set(RUNTIME_SHARED)
    pal = pc.palettes_rgb(city_c, "city")
    layer_cols = {n: set(pal[i]) for i, n in enumerate(LAYERS + ["sky"])}
    ok = True

    def uniq(name, drop_sky=False):
        rest = set(others)
        for n, c in layer_cols.items():
            if n != name and not (drop_sky and n == "sky"):
                rest |= c
        return pc.exclusive(sorted(layer_cols[name]), sorted(rest))

    for tag, png in (("pre_start", pre), ("playing", b_png)):
        n, size = pc.count(png, [SKY], (0, 0, 320, 28))
        total = 320 * 28 * (size[0] / 320.0) * (size[1] / 224.0)
        frac = n / total
        good = frac >= MIN_SKY
        ok = ok and good
        print("%s backdrop #1a1238 share of top band (%s): %.2f (min %.2f)" % ("[OK]" if good else "[FAIL]", tag, frac, MIN_SKY))

    for name in LAYERS:
        cols = uniq(name)
        y0, y1 = Y_BAND[name]
        nin, _ = pc.count(b_png, cols, (0, y0, 320, y1))
        nab, _ = pc.count(b_png, cols, (0, 0, 320, max(0, y0 - 2)))
        good = len(cols) >= 1 and nin >= MIN_BAND and nab <= MAX_ABOVE
        ok = ok and good
        print("%s %s colours (%d layer-only): band y %d..%d %d (min %d), above %d (max %d)"
              % ("[OK]" if good else "[FAIL]", name, len(cols), y0, y1, nin, MIN_BAND, nab, MAX_ABOVE))

    a, b = bg["a"], bg["b"]
    delta = {n: b[i] - a[i] for i, n in enumerate(LAYERS)}
    imb = Image.open(b_png).convert("RGB")
    ima = Image.open(a_png).convert("RGB")
    for name in LAYERS:
        cols = uniq(name, drop_sky=(name == "far"))
        y0, y1 = Y_MEASURE[name]
        skip = SKY_OBJ_X if name == "far" else None
        if len(cols) >= 4:  # drop the most common colour (flat deck/wall fill): it correlates at every shift
            cnt = sorted(cols, key=lambda c: -pc.count(a_png, [c], (0, y0, 320, y1))[0])
            cols = cnt[1:]
        if name == "roof":  # flat deck dominates colour masks: compare whole pixels instead
            sc, total = pixel_scores(ima, imb, y0, y1)
        else:
            ra, rb = rows_mask(ima, cols, y0, y1, skip), rows_mask(imb, cols, y0, y1, skip)
            sc = shift_scores(ra, rb)
            total = sum(m.bit_count() for m in ra)
        # still city: the exported scroll never changes and the layer's pixels match at shift 0 (the flier moving over
        # the city is the only difference allowed, hence the share below 1.0)
        share = sc[0] / float(total) if total else 0.0
        good = delta[name] == 0 and share >= MIN_STILL
        ok = ok and good
        print("%s %s still: exported delta %d (want 0), unshifted pixel match %.3f of %d (min %.2f)"
              % ("[OK]" if good else "[FAIL]", name, delta[name], share, total, MIN_STILL))

    cross = sum((b[i] // 16) - (a[i] // 16) for i in range(3))
    wr = b[3] - a[3]
    good = wr == 0 and cross == 0
    ok = ok and good
    print("%s column strip writes between snapshots: %d (want 0), column boundaries crossed: %d (want 0)" % ("[OK]" if good else "[FAIL]", wr, cross))
    sys.exit(0 if ok else 1)


main()
