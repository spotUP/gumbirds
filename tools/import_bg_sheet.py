#!/usr/bin/env python3
"""Import one mood of the wide parallax background into the city sprite set.
Run: /opt/homebrew/bin/python3.14 -I tools/import_bg_sheet.py [moon] [--drafts <dir>]   then `gmake`.

Reads <drafts>/plane_<mood>_<plane>_1x.png (transparent colour 255,0,255), stacks the planes into assets/city/city_sheet.png
and writes assets/city/city_sheet.json for tools/sprite_pipeline.py in tile_palettes mode (each tile picks its own palette).
Everything the game needs about the planes (parallax factor, top line, width in columns) is emitted as json "tables" and so
reaches C as CITY_TABLE_PLANE_* in build/gen/city_tables.h; no plane number is typed in C, Lua or tests.
A second mood is a MOODS entry (and its draft sheets), not new code: the ROM carries one mood's sheet at a time.
"""
import argparse, json, os, sys
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DRAFTS = os.path.join(ROOT, "thoughts/shared/drafts/2026-11-10-backgrounds-wide")
TRANSP = (255, 0, 255)
PAD = 64          # bit padding of the row masks: room for the largest negative plane x
SCREEN_W = 320
BG_CAM_MAX = 64   # camera range 0..64 px (ARENA_CAM_MAX in src/core/arena.h, asserted in src/bg.c)

# Plane order = sprite draw order, back to front. k is the parallax factor in sixteenths: plane x = cam_px * k / 16.
# top is the screen line of the sheet's first row (the draft slices rows of the 224 line scene). Sheet widths are whole
# tile columns: the plane is width / 16 sprites, one per column. Cloud and airship sheets keep their own drift, no factor
# applies, and they are not built yet (BG-2); they are not listed.
PLANES = [("sky", 0, 0), ("far", 4, 48), ("midA", 8, 80), ("midB", 12, 112), ("near", 16, 128)]
MOODS = {"moon": {"prefix": "plane_moon_"}}


def snap5(c):
    """Snap a colour to the nearest 5-bit expanded value, the only kind the Neo Geo palette holds exactly."""
    f = [round(v * 31 / 255) for v in c]
    return tuple((v << 3) | (v >> 2) for v in f)


def row_masks(im):
    """One int bitmask per sheet row, bit (x + PAD) set where the pixel is not transparent."""
    w, h = im.size
    px = im.load()
    return [sum(1 << (x + PAD) for x in range(w) if px[x, y] != TRANSP) for y in range(h)]


def needed_tiles(imgs):
    """Per plane, the set of (column, tile row) that can show a pixel at some camera position 0..BG_CAM_MAX. A tile is
    dropped when every one of its opaque pixels that lies on the 320 px screen is covered by an opaque pixel of a later
    plane (a plane in front) at every camera position, or lies off screen at every camera position. Exact, so the picture
    is unchanged. The LSPC counts a sprite on every line of its height, so a dropped tile row cuts the column's height
    (column_rows) and the sprite budget gets the line back."""
    masks = [row_masks(i) for i in imgs]
    screen = ((1 << SCREEN_W) - 1) << PAD
    need = [set() for _ in imgs]
    for cam in range(BG_CAM_MAX + 1):
        offs = [(cam * k) >> 4 for _, k, _ in PLANES]
        for k, im in enumerate(imgs):
            top = PLANES[k][2]
            cover = {}  # screen line -> bitmask of screen x covered by the planes in front
            for j in range(k + 1, len(imgs)):
                for r, m in enumerate(masks[j]):
                    y = PLANES[j][2] + r
                    cover[y] = cover.get(y, 0) | (m >> offs[j])  # plane x = -offset: bit x + PAD moves right to x - offset + PAD
            for r in range(im.size[1]):
                m = (masks[k][r] >> offs[k]) & screen
                if m & ~cover.get(top + r, 0):
                    # some visible pixel of this line is not covered: every tile of the row touching it is needed
                    for c in range(im.size[0] // 16):
                        tile_bits = (((1 << 16) - 1) << (c * 16 + PAD)) >> offs[k]
                        if m & ~cover.get(top + r, 0) & tile_bits:
                            need[k].add((c, r // 16))
    return need


def occlusion_trim(imgs):
    """Blank every tile that needed_tiles drops, then cut the empty bottom tile rows of each plane (the sheet keeps one row
    at least). Lossless for the picture; the sprite budget gets the lines back through column_rows."""
    out = []
    for im, need in zip(imgs, needed_tiles(imgs)):
        im = im.copy()
        for c in range(im.size[0] // 16):
            for r in range(im.size[1] // 16):
                if (c, r) not in need:
                    im.paste(TRANSP, (c * 16, r * 16, c * 16 + 16, r * 16 + 16))
        last = max([r for _, r in need] + [0])
        out.append(im.crop((0, 0, im.size[0], (last + 1) * 16)))
    return out


def column_rows(im):
    """Per 16 px column: (first tile row, tile row count) of the rows that hold any non-transparent pixel, from the
    first such row to the last one (rows between stay, they may be transparent tiles). An empty column is (0, 0).
    The LSPC counts a sprite on every line of its height, so empty rows above or below a column cost a slot for nothing."""
    px = im.load()
    out = []
    for c in range(im.size[0] // 16):
        used = [r for r in range(im.size[1] // 16)
                if any(px[c * 16 + dx, r * 16 + dy] != TRANSP for dy in range(16) for dx in range(16))]
        out.append((used[0], used[-1] - used[0] + 1) if used else (0, 0))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mood", nargs="?", default="moon", choices=sorted(MOODS))
    ap.add_argument("--drafts", default=DEFAULT_DRAFTS)
    a = ap.parse_args()
    imgs = []
    for name, k, top in PLANES:
        im = Image.open(os.path.join(a.drafts, "%s%s_1x.png" % (MOODS[a.mood]["prefix"], name))).convert("RGB")
        if im.size[0] % 16 or im.size[1] % 16:
            sys.exit("plane %s is %dx%d, not whole tiles" % (name, *im.size))
        imgs.append(im)
    imgs = occlusion_trim(imgs)
    sheet = Image.new("RGBA", (max(i.size[0] for i in imgs), sum(i.size[1] for i in imgs)), (0, 0, 0, 0))
    anims, y = {}, 0
    for (name, k, top), im in zip(PLANES, imgs):
        rgba = Image.new("RGBA", im.size, (0, 0, 0, 0))
        src, dst = im.load(), rgba.load()
        for yy in range(im.size[1]):
            for xx in range(im.size[0]):
                if src[xx, yy] != TRANSP:
                    dst[xx, yy] = snap5(src[xx, yy]) + (255,)
        sheet.paste(rgba, (0, y))
        anims[name] = [{"x": 0, "y": y, "w": im.size[0], "h": im.size[1]}]
        y += im.size[1]
    cols = [column_rows(i) for i in imgs]  # plane order, so the flat index is the sprite slot (src/sprite_slots.h)
    out = os.path.join(ROOT, "assets/city")
    sheet.save(os.path.join(out, "city_sheet.png"))
    defines = {"CAM_MAX": BG_CAM_MAX}  # CITY_CAM_MAX: src/bg.c asserts it equals ARENA_CAM_MAX
    for (n, _, top), i in zip(PLANES, imgs):
        defines["%s_COLS" % n.upper()] = i.size[0] // 16
        defines["%s_TOP" % n.upper()] = top
        defines["%s_BOTTOM" % n.upper()] = top + i.size[1]
    meta = {
        "source": "tools/import_bg_sheet.py %s from thoughts/shared/drafts/2026-11-10-backgrounds-wide/plane_%s_*_1x.png (wide parallax planes, frame 0 of the draft loop)" % (a.mood, a.mood),
        "backdrop": "#1a1238",
        "palette_policy": "merge",
        "tile_palettes": True,
        "animations": anims,
        # one scalar per plane too: the sprite slot map in src/sprite_slots.h is checked against these with static asserts
        "defines": defines,
        "tables": {
            "plane_k": [k for _, k, _ in PLANES],
            "plane_top": [t for _, _, t in PLANES],
            "plane_cols": [i.size[0] // 16 for i in imgs],
            # per column, all planes back to back: the first drawn tile row inside the plane sheet and the tile rows drawn
            # (0 rows: nothing to draw). Single source for src/bg.c and the sprite budget model.
            "col_row0": [r0 for plane in cols for r0, _ in plane],
            "col_rows": [n for plane in cols for _, n in plane],
        },
    }
    json.dump(meta, open(os.path.join(out, "city_sheet.json"), "w"), indent=1)
    print("imported mood %s: %s" % (a.mood, ", ".join("%s %dx%d" % (n, *i.size) for (n, _, _), i in zip(PLANES, imgs))))


if __name__ == "__main__":
    main()
