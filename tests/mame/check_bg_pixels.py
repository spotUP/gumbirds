"""Visual proof by pixels for the parallax background (python3.14 -I, Pillow).
Usage: check_bg_pixels.py city_sprites.c obs_sprites.c pre_start.png bg_a.png bg_b.png result.txt.bg
bg file (written by boot_check.lua at the two snapshot frames): "a x0 x1 x2 x3 x4 writes" / "b ..." (screen x of each
plane's first column as the game exported it, planes in draw order sky, far, mid A, mid B, near, and the plane write
counter g_bg_x_writes).
Checks, each independent of the hero and obstacle checks (only colours unique to one plane are counted; the colours of a
plane are the palettes of the tiles it draws, read from the generated city_frames and city_tile_pal):
  1. the sky plane fills the top band wherever the fix layer header text does not cover it, before start and during play
     (sky colours plus the backdrop; the header text is not background: its length must not move this check)
  2. each plane's tile colours (beyond the sky palette) appear in its y band during play
  3. the pixels moved the way the game exported: between the snapshots the plane's pixels match at the shift its exported
     x delta says (0 when the camera stood still)
  4. the plane write sentinel grew only when a plane moved
Exit 1 on failure."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pixel_common as pc
from PIL import Image

PLANES = ["sky", "far", "midA", "midB", "near"]
# Screen y band of each plane (CITY_TABLE_PLANE_TOP and bottom in build/gen/city_tables.h), read at run time.
HERO_MASK = (28, 112)
BACKDROP = (0x1a, 0x12, 0x38)
# Fix layer text palette PAL_TEXT as MAME draws it (src/main.c video_init: gfx_pal(1, 0x0fff), gfx_pal(2, 0x0555)).
FIX_TEXT = [(247, 247, 247), (79, 79, 79)]
MIN_BAND, MIN_SKY = 300, 0.9
MIN_MATCH = 0.9
FULL = (1 << 320) - 1


def load_bg(path):
    out = {}
    for line in open(path):
        t = line.split()
        if t:
            out[t[0]] = [int(v) for v in t[1:]]
    return out


def plane_colours(city_c, tables_h):
    """Per plane: (set of RGB colours of the palettes its tiles use, top y, bottom y)."""
    text = re.sub(r"/\*.*?\*/", "", open(city_c).read(), flags=re.S)
    frames = re.search(r"city_frames\[[^\]]*\]\s*=\s*\{(.*?)\n\};", text, re.S).group(1)
    rows = [[int(v) for v in r.split(",")] for r in re.findall(r"\{([\d, ]+)\}", frames)]
    tile_pal = [int(v) for v in re.search(r"city_tile_pal\[[^\]]*\]\s*=\s*\{(.*?)\};", text, re.S).group(1).replace("\n", " ").split(",") if v.strip()]
    tile_idx = [int(v, 16) if v.strip().startswith("0x") else int(v) for v in re.search(r"city_tile_index\[[^\]]*\]\s*=\s*\{(.*?)\};", text, re.S).group(1).replace("\n", " ").split(",") if v.strip()]
    pal = pc.palettes_rgb(city_c, "city")
    head = open(tables_h).read()
    tops = [int(v) for v in re.search(r"CITY_TABLE_PLANE_TOP \{([^}]*)\}", head).group(1).split(",")]
    bottoms = [int(re.search(r"CITY_%s_BOTTOM (\d+)" % n.upper(), head).group(1)) for n in PLANES]
    out = []
    for p, r in enumerate(rows):
        off, w, h = r[0], r[1], r[2]
        used = {tile_pal[i] for i in range(off, off + w * h) if tile_idx[i]}
        cols = set()
        for u in used:
            cols |= set(pal[u])
        out.append((cols, tops[p], bottoms[p]))
    return out


def rows_mask(im, cols, y0, y1):
    w, h = im.size
    px = im.load()
    rows = []
    for y in range(y0, y1):
        m = 0
        sy = min(h - 1, int(y * h / 224.0))
        for x in range(320):
            if HERO_MASK[0] <= x < HERO_MASK[1]:
                continue
            p = px[min(w - 1, int(x * w / 320.0)), sy]
            if any(pc.near(p, c) for c in cols):
                m |= 1 << x
        rows.append(m)
    return rows


def rot_left(m, d):
    """Bit x of result == bit (x + d) mod 320 of m."""
    return ((m >> d) | (m << (320 - d))) & FULL if d else m


def main():
    city_c, obs_c, pre, a_png, b_png, bg_txt = sys.argv[1:7]
    tables_h = os.path.join(os.path.dirname(city_c), "city_tables.h")
    bg = load_bg(bg_txt)
    others = set(pc.colours(obs_c, "obs"))
    planes = plane_colours(city_c, tables_h)
    ok = True

    def uniq(i):
        rest = set(others)
        for j, (c, _, _) in enumerate(planes):
            if j != i:
                rest |= c
        return pc.exclusive(sorted(planes[i][0]), sorted(rest))

    sky_cols = sorted(planes[0][0] | {BACKDROP})
    for tag, png in (("pre_start", pre), ("playing", b_png)):
        n, size = pc.count(png, sky_cols, (0, 0, 320, 28))
        text, _ = pc.count(png, FIX_TEXT, (0, 0, 320, 28))
        total = 320 * 28 * (size[0] / 320.0) * (size[1] / 224.0) - text
        frac = n / total
        good = frac >= MIN_SKY
        ok = ok and good
        print("%s sky plane colours share of top band outside header text (%s): %.2f (min %.2f)" % ("[OK]" if good else "[FAIL]", tag, frac, MIN_SKY))

    for i in range(1, 5):
        # Planes share palettes with each other and with the sky, so the band check counts every colour the plane's
        # tiles use (minus the obstacle colours); a plane that failed to draw leaves its band at sky colour only.
        cols = sorted(planes[i][0] - others - set(sky_cols))
        _, top, bottom = planes[i]
        if not cols:
            print("[OK] %s uses only sky palette colours: its columns are proved by make test-camera, not by colour" % PLANES[i])
            continue
        nin, _ = pc.count(b_png, cols, (0, top, 320, min(bottom, 190)))
        good = len(cols) >= 1 and nin >= MIN_BAND
        ok = ok and good
        print("%s %s colours (%d beyond the sky palette): %d pixels in band y %d..%d (min %d)"
              % ("[OK]" if good else "[FAIL]", PLANES[i], len(cols), nin, top, min(bottom, 190), MIN_BAND))

    a, b = bg["a"], bg["b"]
    ima = Image.open(a_png).convert("RGB")
    imb = Image.open(b_png).convert("RGB")
    moved = 0
    for i in range(1, 5):
        cols = uniq(i)
        _, top, bottom = planes[i]
        if not cols:
            print("[OK] %s shares every colour with another plane: its motion is proved by make test-camera" % PLANES[i])
            moved += 1 if a[i] != b[i] else 0
            continue
        # the hazard strip (src/hazard.c) animates over lines 192..223 in a match
        ra, rb = rows_mask(ima, cols, top + 2, min(bottom, 190)), rows_mask(imb, cols, top + 2, min(bottom, 190))
        total = sum(m.bit_count() for m in ra)
        delta = a[i] - b[i]  # the scene moves left by this many pixels when the exported x falls
        if delta:
            moved += 1
        hit = sum((rot_left(x, delta % 320) & y).bit_count() for x, y in zip(ra, rb))
        share = hit / float(total) if total else 0.0
        good = total > 0 and share >= MIN_MATCH
        ok = ok and good
        print("%s %s moved as exported: x delta %d, pixel match at that shift %.3f of %d (min %.2f)"
              % ("[OK]" if good else "[FAIL]", PLANES[i], -delta, share, total, MIN_MATCH))

    sky_still = a[0] == b[0] == 0
    ok = ok and sky_still
    print("%s sky plane x %d -> %d (want 0, the sky never scrolls)" % ("[OK]" if sky_still else "[FAIL]", a[0], b[0]))

    wr = b[5] - a[5]
    good = (wr == 0) == (moved == 0) and wr >= moved
    ok = ok and good
    print("%s plane write runs between snapshots: %d for %d moved planes (none when nothing moved, at least one per moved plane)"
          % ("[OK]" if good else "[FAIL]", wr, moved))
    sys.exit(0 if ok else 1)


main()
