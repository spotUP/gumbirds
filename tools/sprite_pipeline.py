#!/usr/bin/env python3
"""Shared sprite pipeline: PNG sheet + json -> Neo Geo C-ROM sprite data. Used by the obstacle
set; the thin entry script tools/build_obstacle_sprites.py calls main() with its set name and
default inputs.

Outputs in --out (generated, not committed), for a set called NAME:
    NAME.c1 NAME.c2        C-ROM tile pairs (tiletool.py --sprite -c, same as build.mk)
    NAME_sprites.h/.c      palettes, frame table, column-major tile index lists
Then decodes NAME.c1/NAME.c2 back with `tiletool.py --sprite -x` and compares every frame
pixel-exact against the sheet. Any violation exits non-zero.

Palette policy (json key "palette_policy"): "subset" (default) shares a palette only when an
animation's colours are a subset of it; "merge" also grows an existing palette when the union
still fits 15 colours (used when several animations are drawn to share one palette).
"""
import argparse, json, os, re, subprocess, sys, tempfile
from PIL import Image

TILE = 16
MAX_COLOURS = 15  # plus transparent index 0
TILETOOL = os.environ.get("TILETOOL", "/opt/homebrew/bin/tiletool.py")


def die(msg):
    print("[ERROR] " + msg, file=sys.stderr)
    sys.exit(1)


def hex_rgb(s):
    return tuple(int(s[i:i + 2], 16) for i in (1, 3, 5))


def to5(v):
    return round(v * 31 / 255)


def expand5(f):
    return (f << 3) | (f >> 2)


def rgb_to_ng(c):
    """24-bit RGB -> Neo Geo DRGB word, exact for colours that are 5-bit expanded.
    Layout: bit15 dark, bits14/13/12 = LSB of R/G/B, bits 11-8 R hi4, 7-4 G hi4, 3-0 B hi4.
    Dark bit stays 0 (full brightness). paltool.py is not used: it derives the dark
    bit and LSBs from a 6-bit truncation and is lossy for this art."""
    f = [to5(v) for v in c]
    for v, fv in zip(c, f):
        if expand5(fv) != v:
            die("colour #%02x%02x%02x is not a 5-bit expanded value" % c)
    lsb = ((f[0] & 1) << 2) | ((f[1] & 1) << 1) | (f[2] & 1)
    return (lsb << 12) | ((f[0] >> 1) << 8) | ((f[1] >> 1) << 4) | (f[2] >> 1)


def ng_to_rgb(w):
    r5 = (((w >> 8) & 15) << 1) | ((w >> 14) & 1)
    g5 = (((w >> 4) & 15) << 1) | ((w >> 13) & 1)
    b5 = ((w & 15) << 1) | ((w >> 12) & 1)
    if w & 0x8000:
        die("dark bit set in palette word %04x" % w)
    return (expand5(r5), expand5(g5), expand5(b5))


class Namer:
    """Writes template text with @n@ (lower), @N@ (upper), @C@ (Capitalised) set name tokens and
    @src@ (source sheet) rewritten."""
    def __init__(self, f, name, src):
        self.f, self.m = f, {"@n@": name, "@N@": name.upper(), "@C@": name.capitalize(), "@src@": src}
    def write(self, t):
        for k, v in self.m.items():
            t = t.replace(k, v)
        self.f.write(t)
    def __enter__(self):
        return self
    def __exit__(self, *e):
        self.f.close()


def main(name, sheet, meta):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", default=sheet)
    ap.add_argument("--meta", default=meta)
    ap.add_argument("--out", default="build/gen")
    ap.add_argument("--scratch", default=None)
    ap.add_argument("--no-verify", action="store_true")
    a = ap.parse_args()
    a.name = name

    sheet = Image.open(a.sheet).convert("RGBA")
    meta = json.load(open(a.meta))
    px = sheet.load()
    os.makedirs(a.out, exist_ok=True)

    # ---- collect frames, validate alpha, gather colours per animation
    frames = []  # dict per frame
    for anim, fl in meta["animations"].items():
        for i, r in enumerate(fl):
            cols = set()
            for y in range(r["y"], r["y"] + r["h"]):
                for x in range(r["x"], r["x"] + r["w"]):
                    p = px[x, y]
                    if p[3] not in (0, 255):
                        die("%s[%d]: partial alpha at (%d,%d)" % (anim, i, x, y))
                    if p[3]:
                        cols.add(p[:3])
            tw = -(-r["w"] // TILE)
            th = -(-r["h"] // TILE)
            frames.append(dict(anim=anim, idx=i, r=r, cols=cols, tw=tw, th=th,
                               pad_left=(tw * TILE - r["w"]) // 2,
                               pad_top=th * TILE - r["h"]))

    # ---- palette assignment: whole animation shares one palette (greedy, JSON order)
    merge = meta.get("palette_policy", "subset") == "merge"
    pals = []  # list of ordered colour lists
    anim_pal = {}
    key_order = {}  # colour -> first appearance (frame order, row-major): stable index order
    for f in frames:
        r = f["r"]
        for y in range(r["y"], r["y"] + r["h"]):
            for x in range(r["x"], r["x"] + r["w"]):
                p = px[x, y]
                if p[3] and p[:3] not in key_order:
                    key_order[p[:3]] = len(key_order)
    for anim in meta["animations"]:
        need = set().union(*[f["cols"] for f in frames if f["anim"] == anim])
        if len(need) > MAX_COLOURS:
            die("animation %s needs %d colours, limit %d" % (anim, len(need), MAX_COLOURS))
        # policy: share a palette only if the colour set is a subset of it (no growth),
        # so hero body (14 colours) and effects (3 colours) stay separate palettes.
        for n, p in enumerate(pals):
            if need <= set(p):
                anim_pal[anim] = n
                break
            if merge and len(set(p) | need) <= MAX_COLOURS:
                p.extend(sorted(need - set(p), key=lambda c: key_order[c]))
                anim_pal[anim] = n
                break
        else:
            pals.append(sorted(need, key=lambda c: key_order[c]))
            anim_pal[anim] = len(pals) - 1
    # ---- cut tiles, per-tile colour check, dedup
    blank = bytes(256)
    tiles = [blank]  # tile 0 = blank, shared
    tile_ix = {blank: 0}
    groups = meta.get("groups", {})  # anim name -> frames per group (4 or 8): hardware auto-animation

    def cut_frame(f):
        """Tiles of frame f, column-major (top tile first), as palette-index bytes."""
        pal = pals[anim_pal[f["anim"]]]
        cmap = {c: n + 1 for n, c in enumerate(pal)}
        w, h = f["tw"] * TILE, f["th"] * TILE
        buf = [[0] * w for _ in range(h)]
        r = f["r"]
        for y in range(r["h"]):
            for x in range(r["w"]):
                p = px[r["x"] + x, r["y"] + y]
                if p[3]:
                    buf[f["pad_top"] + y][f["pad_left"] + x] = cmap[p[:3]]
        out = []
        for tx in range(f["tw"]):
            for ty in range(f["th"]):
                t = bytearray(256)
                for y in range(TILE):
                    for x in range(TILE):
                        t[y * TILE + x] = buf[ty * TILE + y][tx * TILE + x]
                used = set(t) - {0}
                if len(used) > MAX_COLOURS:
                    die("%s[%d] tile (%d,%d) uses %d colours" % (f["anim"], f["idx"], tx, ty, len(used)))
                out.append(bytes(t))
        return out

    for f in frames:
        f["pal"] = anim_pal[f["anim"]]
        if f["anim"] in groups:
            continue
        order = []
        for t in cut_frame(f):
            if t not in tile_ix:
                tile_ix[t] = len(tiles)
                tiles.append(t)
            order.append(tile_ix[t])
        f["tiles"] = order

    # ---- auto-animation groups: the LSPC replaces the low 2 (4 frames) or 3 (8 frames) bits of a tile number with a
    # frame counter, so each cell (column, row) of the sprite owns G consecutive tiles starting at a multiple of G, frame
    # k at +k. No dedup inside a group. The sprite strip holds the frame 0 tile number with the attribute bit set.
    for gname, g in groups.items():
        if g not in (4, 8):
            die("group %s: size %d, only 4 or 8 frames" % (gname, g))
        gf = [f for f in frames if f["anim"] == gname]
        if len(gf) != g or len({(f["tw"], f["th"]) for f in gf}) != 1:
            die("group %s: needs %d frames of one size" % (gname, g))
        while len(tiles) % g:
            tiles.append(blank)
        base, cells = len(tiles), gf[0]["tw"] * gf[0]["th"]
        tiles.extend([blank] * (cells * g))
        for k, f in enumerate(gf):
            ts = cut_frame(f)
            for c in range(cells):
                tiles[base + c * g + k] = ts[c]
            f["tiles"] = [base + c * g + k for c in range(cells)]
    # Pad the set to a multiple of 8 tiles so the next set (cat order, src/vram_layout.h) keeps the alignment.
    while len(tiles) % 8:
        tiles.append(blank)

    # ---- atlas (palette-indexed, one 16 px row) -> tiletool --sprite -c, as build.mk does
    atlas = Image.new("P", (TILE * len(tiles), TILE))
    pp = [0, 0, 0]
    for n in range(1, 16):
        pp += [n * 16, n * 16, n * 16]
    atlas.putpalette(pp + [0] * (768 - len(pp)))
    for n, t in enumerate(tiles):
        atlas.paste(Image.frombytes("P", (TILE, TILE), t), (n * TILE, 0))
    atlas_png = os.path.join(a.out, "%s_atlas.png" % name)
    atlas.save(atlas_png)
    c1, c2 = os.path.join(a.out, name + ".c1"), os.path.join(a.out, name + ".c2")
    subprocess.run([TILETOOL, "--sprite", "-c", atlas_png, "-o", c1, c2], check=True)
    for p in (c1, c2):
        if os.path.getsize(p) != 64 * len(tiles):
            die("%s size %d != %d" % (p, os.path.getsize(p), 64 * len(tiles)))

    # ---- generated C
    flat = []
    for f in frames:
        f["off"] = len(flat)
        flat += f["tiles"]
    hp = os.path.join(a.out, name + "_sprites.h")
    cp = os.path.join(a.out, name + "_sprites.c")
    anim_names = list(meta["animations"])
    with Namer(open(hp, "w"), name, a.sheet) as h:
        h.write("/* GENERATED by tools/sprite_pipeline.py from @src@; do not edit. */\n")
        h.write("#ifndef @N@_SPRITES_H\n#define @N@_SPRITES_H\n#include <ngdevkit/types.h>\n\n")
        h.write("#define @N@_TILE_COUNT %d   /* tiles in @n@.c1/@n@.c2 */\n" % len(tiles))
        h.write("#define @N@_PALETTE_COUNT %d\n#define @N@_FRAME_COUNT %d\n" % (len(pals), len(frames)))
        h.write("#define @N@_MAX_COLUMNS %d   /* widest frame in tiles = hardware sprites per object */\n\n"
                % max(f["tw"] for f in frames))
        h.write("/* Tile numbers in @n@_tile_index[] are relative to the first @n@ tile in the\n"
                "   C-ROM; add the tile base where @n@.c1/c2 are placed. Layout: column-major\n"
                "   (Neo Geo sprite columns), top tile first. Tile 0 of the set is blank. */\n")
        h.write("typedef struct {\n    u16 tile_offset;  /* index into @n@_tile_index */\n"
                "    u8 tiles_w, tiles_h;\n    u8 palette;       /* index into @n@_palettes */\n"
                "    u16 src_w, src_h;  /* opaque pixel box in the sheet */\n"
                "    u8 pad_left, pad_top; /* pixels from box edge to art; feet = bottom edge */\n"
                "} @C@Frame;\n\n")
        h.write("typedef struct { u8 first_frame, frame_count; } @C@Anim;\n\n")
        for n, an in enumerate(anim_names):
            h.write("#define @N@_ANIM_%s %d\n" % (an.upper(), n))
        h.write("#define @N@_ANIM_COUNT %d\n\n" % len(anim_names))
        # meta key "tables": {name: [ints]} -> `#define @N@_TABLE_NAME { a, b }`, data the game reads next to the frames
        for tn, tv in meta.get("tables", {}).items():
            h.write("#define @N@_TABLE_%s { %s }\n" % (tn.upper(), ", ".join(str(v) for v in tv)))
        h.write("\n")
        h.write("extern const u16 @n@_palettes[@N@_PALETTE_COUNT][16];\n"
                "extern const u16 @n@_tile_index[%d];\n"
                "extern const @C@Frame @n@_frames[@N@_FRAME_COUNT];\n"
                "extern const @C@Anim @n@_anims[@N@_ANIM_COUNT];\n\n#endif\n" % len(flat))
    with Namer(open(cp, "w"), name, a.sheet) as c:
        c.write("/* GENERATED by tools/sprite_pipeline.py; do not edit. */\n#include \"@n@_sprites.h\"\n\n")
        c.write("/* Entry 0 is the transparent colour; words are DRGB with dark bit 0. */\n")
        c.write("const u16 @n@_palettes[@N@_PALETTE_COUNT][16] = {\n")
        for p in pals:
            words = [0x8000] + [rgb_to_ng(col) for col in p]
            words += [0] * (16 - len(words))
            c.write("    { " + ", ".join("0x%04x" % w for w in words) + " },\n")
        c.write("};\n\nconst u16 @n@_tile_index[%d] = {\n" % len(flat))
        for f in frames:
            c.write("    /* %s %d */ " % (f["anim"], f["idx"]) + ", ".join(str(t) for t in f["tiles"]) + ",\n")
        c.write("};\n\nconst @C@Frame @n@_frames[@N@_FRAME_COUNT] = {\n")
        for f in frames:
            c.write("    { %d, %d, %d, %d, %d, %d, %d, %d }, /* %s %d */\n" % (
                f["off"], f["tw"], f["th"], f["pal"], f["r"]["w"], f["r"]["h"],
                f["pad_left"], f["pad_top"], f["anim"], f["idx"]))
        c.write("};\n\nconst @C@Anim @n@_anims[@N@_ANIM_COUNT] = {\n")
        fi = 0
        for an in anim_names:
            n = len(meta["animations"][an])
            c.write("    { %d, %d }, /* %s */\n" % (fi, n, an))
            fi += n
        c.write("};\n")

    print("[OK] frames=%d palettes=%d tiles=%d (unique, incl. 1 blank) tile-refs=%d"
          % (len(frames), len(pals), len(tiles), len(flat)))
    for n, p in enumerate(pals):
        print("     palette %d: %d colours + transparent; anims: %s" % (
            n, len(p), ", ".join(k for k, v in anim_pal.items() if v == n)))
    print("     max colours per tile checked <= %d" % MAX_COLOURS)

    if a.no_verify:
        return
    verify(a, frames, tiles, sheet, name)


def verify(a, frames, tiles, sheet, name):
    """Decode shipped bytes only: c1/c2 via tiletool --extract, palettes and tables
    by parsing the generated .c file. Compare to the sheet pixel-exact."""
    scratch = a.scratch or tempfile.mkdtemp()
    os.makedirs(scratch, exist_ok=True)
    c1, c2 = os.path.join(a.out, name + ".c1"), os.path.join(a.out, name + ".c2")
    dec = os.path.join(scratch, "decoded.png")
    subprocess.run([TILETOOL, "--sprite", "-x", c1, c2, "-o", dec, "-w", str(TILE * len(tiles))],
                   check=True)
    atlas = Image.open(dec)
    atlas_px = atlas.load()
    src = open(os.path.join(a.out, name + "_sprites.c")).read()
    pal_rows = re.findall(r"\{ (0x[0-9a-f]{4}(?:, 0x[0-9a-f]{4}){15}) \}", src)
    pals = [[int(w, 16) for w in row.split(", ")] for row in pal_rows]
    idx_block = src.split(name + "_tile_index")[1].split("};")[0]
    idx = [int(v) for v in re.findall(r"(?<![/\w*])\d+(?=,)", re.sub(r"/\*.*?\*/", "", idx_block))]
    ftab = src.split("%s_frames[%s_FRAME_COUNT] = {" % (name, name.upper()))[1].split("};")[0]
    rows = [[int(v) for v in m.split(",")] for m in re.findall(r"\{ ([\d, ]+) \}", ftab)]
    if len(rows) != len(frames):
        die("frame table rows %d != %d" % (len(rows), len(frames)))
    sp = sheet.load()
    checked = bad = 0
    for f, row in zip(frames, rows):
        off, tw, th, pal, sw, sh, pl, pt = row
        rgb_pal = [None] + [ng_to_rgb(w) for w in pals[pal][1:]]
        for y in range(th * TILE):
            for x in range(tw * TILE):
                t = idx[off + (x // TILE) * th + (y // TILE)]
                ci = atlas_px[t * TILE + x % TILE, y % TILE]
                got = None if ci == 0 else rgb_pal[ci]
                sx, sy = x - pl, y - pt
                if 0 <= sx < sw and 0 <= sy < sh:
                    p = sp[f["r"]["x"] + sx, f["r"]["y"] + sy]
                    want = p[:3] if p[3] else None
                else:
                    want = None
                checked += 1
                if got != want:
                    bad += 1
                    if bad <= 5:
                        print("  mismatch %s[%d] (%d,%d) got %s want %s" % (f["anim"], f["idx"], x, y, got, want))
    if bad:
        die("round-trip FAILED: %d of %d pixels differ" % (bad, checked))
    print("[OK] round-trip: %d frames, %d pixels compared, 0 mismatches (c1/c2 -> tiletool extract + generated palette/table vs sheet)"
          % (len(frames), checked))


