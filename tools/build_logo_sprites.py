#!/usr/bin/env python3
"""Title logo sprite set: assets/logo/ (logo_rim.json, logo_rim_frames_1x.png, logo_rim_pieces_1x.png,
logo_pieces.json) -> <out>/logo.c1, logo.c2, logo_sprites.h.
Usage: $PYTHON -I tools/build_logo_sprites.py [--out build/gen] [--assets assets/logo]

The logo is not a frame sheet in the sprite_pipeline.main() sense: it is one 336x128 layer of 16 px strips with 10
full frames plus loose 16x16 pieces, and its tiles are shared across flips. So this tool only takes the tile and
colour primitives from tools/sprite_pipeline.py (TILE, TILETOOL, to5, expand5, die) and the same atlas -> tiletool
step, and writes one header without includes (the form of <set>_tables.h), usable by the game and by host tests.

The art is approved: the tool reads palette indices from the indexed PNG and never changes one. It ends with a
self-check that decodes the written logo.c1/logo.c2 with tiletool, parses the written header and rebuilds every
frame and every piece from them; any pixel that differs from the source PNG exits non-zero.
"""
import argparse, json, os, re, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image
from sprite_pipeline import TILE, TILETOOL, to5, expand5, die

REF_TILE, REF_FLIP_X, REF_FLIP_Y = 0x0fff, 0x1000, 0x2000
SCREEN_H = 224
MOODS = ("moon", "dusk", "storm")


def flip_x(t):
    return b"".join(t[y * TILE:(y + 1) * TILE][::-1] for y in range(TILE))


def flip_y(t):
    return b"".join(t[y * TILE:(y + 1) * TILE] for y in reversed(range(TILE)))


def cut(img, x, y):
    return img.crop((x, y, x + TILE, y + TILE)).tobytes()


def ng_word(c):
    """Nearest Neo Geo colour word (dark bit 0), and the RGB it shows. sprite_pipeline.rgb_to_ng() refuses colours
    that are not 5-bit expanded; the mood rim colours are multiples of 8, so the nearest 5-bit step is taken here."""
    f = [to5(v) for v in c]
    lsb = ((f[0] & 1) << 2) | ((f[1] & 1) << 1) | (f[2] & 1)
    return (lsb << 12) | ((f[0] >> 1) << 8) | ((f[1] >> 1) << 4) | (f[2] >> 1), tuple(expand5(v) for v in f)


def table(src, name):
    m = re.search(r"#define LOGO_TABLE_%s \{ ([^}]*) \}" % name, src)
    return [int(v, 0) for v in m.group(1).split(", ")]


def define(src, name):
    return int(re.search(r"#define LOGO_%s (-?\w+)" % name, src).group(1), 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="build/gen")
    ap.add_argument("--assets", default="assets/logo")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    meta = json.load(open(os.path.join(a.assets, "logo_rim.json")))
    piece_meta = json.load(open(os.path.join(a.assets, "logo_pieces.json")))["frames"]
    sheet_path = os.path.join(a.assets, "logo_rim_frames_1x.png")
    sheet = Image.open(sheet_path)
    psheet = Image.open(os.path.join(a.assets, "logo_rim_pieces_1x.png"))
    fw, fh = meta["frame_size"]
    nf = meta["frames"]
    lx, ly = meta["layer_top_left_on_screen"]
    if sheet.mode != "P" or psheet.mode != "P" or sheet.size != (fw, fh * nf) or fw % TILE or fh % TILE:
        die("logo sheets must be indexed PNGs, frames %dx%d x %d" % (fw, fh, nf))
    if len(meta["frame_ms"]) != nf or len(piece_meta) != nf or psheet.size[0] % TILE or psheet.size[1] != TILE:
        die("frame_ms, logo_pieces.json or the pieces sheet do not fit %d frames" % nf)
    used = sorted(set(sheet.tobytes()) | set(psheet.tobytes()))
    ncol = len(meta["palettes"]["dusk"])
    if used[-1] >= ncol or ncol > 16:
        die("pixel index %d outside the %d entry palette" % (used[-1], ncol))
    if sheet.getpalette()[:3 * ncol] != [v for c in meta["palettes"]["dusk"] for v in c]:
        die("the PNG palette is not the dusk palette of logo_rim.json")
    cols, rows = fw // TILE, fh // TILE

    # ---- tiles: 0 = blank, then unique tiles in first-seen order; a flipped twin is a reference with flip bits
    blank = bytes(TILE * TILE)
    tiles, refs = [blank], {blank: 0}

    def ref(t):
        if t not in refs:
            refs[t] = len(tiles)
            tiles.append(t)
            fx = flip_x(t)
            for v, bits in ((fx, REF_FLIP_X), (flip_y(t), REF_FLIP_Y), (flip_y(fx), REF_FLIP_X | REF_FLIP_Y)):
                refs.setdefault(v, refs[t] | bits)
        return refs[t]

    grid = [[[ref(cut(sheet, c * TILE, f * fh + r * TILE)) for r in range(rows)] for c in range(cols)] for f in range(nf)]
    still = {grid[meta["still_frame"]][c][r] & REF_TILE for c in range(cols) for r in range(rows)} - {0}
    body_tiles = len(tiles) - 1

    # ---- strips: one per column that holds art in any frame; rows = the span that holds art in any frame
    strips = []  # (column, first row, height in tiles)
    for c in range(cols):
        rr = [r for r in range(rows) if any(grid[f][c][r] for f in range(nf))]
        if rr:
            strips.append((c, rr[0], rr[-1] - rr[0] + 1))
    strip_off = [sum(s[2] for s in strips[:n]) for n in range(len(strips))]
    per_frame = sum(s[2] for s in strips)
    frame_refs = [grid[f][c][r0 + k] for f in range(nf) for c, r0, h in strips for k in range(h)]

    # ---- free pieces, screen coordinates
    ptiles = [cut(psheet, x, 0) for x in range(0, psheet.size[0], TILE)]
    pieces = []  # per frame: (ref, screen x, screen y)
    for row in piece_meta:
        pieces.append([(ref(flip_x(ptiles[p["tile"]]) if p["flip_x"] else ptiles[p["tile"]]), p["x"] + lx, p["y"] + ly)
                       for p in row])
    flat = [p for row in pieces for p in row]
    piece_first = [sum(len(r) for r in pieces[:f]) for f in range(nf + 1)]
    unique = len(tiles) - 1
    while len(tiles) % 8:  # the next set in the C-ROM (cat order, src/vram_layout.h) keeps its alignment
        tiles.append(blank)

    # ---- sprites per scanline: a strip counts on every line of its height, drawn pixels or not (hardware rule)
    worst = []
    for f in range(nf):
        line = [0] * SCREEN_H
        spans = [(ly + r0 * TILE, h * TILE) for _, r0, h in strips] + [(y, TILE) for _, _, y in pieces[f]]
        for y0, hh in spans:
            for y in range(max(y0, 0), min(y0 + hh, SCREEN_H)):
                line[y] += 1
        worst.append((max(line), line.index(max(line))))

    # ---- atlas (palette-indexed, one 16 px row) -> tiletool --sprite -c, as sprite_pipeline.py and build.mk do
    atlas = Image.new("P", (TILE * len(tiles), TILE))
    pp = [0, 0, 0]
    for n in range(1, 16):
        pp += [n * 16, n * 16, n * 16]
    atlas.putpalette(pp + [0] * (768 - len(pp)))
    for n, t in enumerate(tiles):
        atlas.paste(Image.frombytes("P", (TILE, TILE), t), (n * TILE, 0))
    scratch = tempfile.mkdtemp()
    atlas_png = os.path.join(scratch, "logo_atlas.png")
    atlas.save(atlas_png)
    c1, c2 = os.path.join(a.out, "logo.c1"), os.path.join(a.out, "logo.c2")
    subprocess.run([TILETOOL, "--sprite", "-c", atlas_png, "-o", c1, c2], check=True)
    for p in (c1, c2):
        if os.path.getsize(p) != 64 * len(tiles):
            die("%s size %d != %d" % (p, os.path.getsize(p), 64 * len(tiles)))

    # ---- header
    def tab(name, vals, fmt="%d"):
        return "#define LOGO_TABLE_%s { %s }\n" % (name, ", ".join(fmt % v for v in vals))

    rounded = []
    hp = os.path.join(a.out, "logo_sprites.h")
    with open(hp, "w") as h:
        h.write("/* GENERATED by tools/build_logo_sprites.py from %s; do not edit. */\n" % sheet_path)
        h.write("#ifndef LOGO_SPRITES_H\n#define LOGO_SPRITES_H\n")
        h.write("#define LOGO_TILE_COUNT %d   /* tiles in logo.c1/logo.c2, padded to 8; tile 0 is blank */\n" % len(tiles))
        h.write("#define LOGO_TILES_USED %d   /* unique art tiles, flips reused, without the blank */\n" % unique)
        h.write("#define LOGO_FRAME_COUNT %d\n#define LOGO_STILL_FRAME %d\n" % (nf, meta["still_frame"]))
        h.write("#define LOGO_STRIP_COUNT %d   /* hardware sprites of the body */\n" % len(strips))
        h.write("#define LOGO_STRIP_MAX_H %d\n" % max(s[2] for s in strips))
        h.write("#define LOGO_FRAME_TILES %d   /* tile references per frame = sum of the strip heights */\n" % per_frame)
        h.write("#define LOGO_PIECE_MAX %d   /* most free pieces in one frame */\n" % max(len(r) for r in pieces))
        h.write("#define LOGO_PIECE_TOTAL %d\n" % len(flat))
        h.write("#define LOGO_LAYER_X %d\n#define LOGO_LAYER_Y %d\n" % (lx, ly))
        h.write("#define LOGO_WORST_LINE %d   /* most logo sprites on one scanline, any frame */\n" % max(w[0] for w in worst))
        h.write("/* A tile reference: tile number relative to the first logo tile in the C-ROM, plus flip bits. */\n")
        h.write("#define LOGO_REF_TILE 0x%04x\n#define LOGO_REF_FLIP_X 0x%04x\n#define LOGO_REF_FLIP_Y 0x%04x\n"
                % (REF_TILE, REF_FLIP_X, REF_FLIP_Y))
        h.write("/* Strips, left to right: screen x, screen y of the first tile, height in tiles, and the offset of the\n"
                "   strip's first reference inside one frame of LOGO_TABLE_FRAME_TILES (top tile first). */\n")
        h.write(tab("STRIP_X", [lx + c * TILE for c, _, _ in strips]))
        h.write(tab("STRIP_Y", [ly + r0 * TILE for _, r0, _ in strips]))
        h.write(tab("STRIP_H", [s[2] for s in strips]))
        h.write(tab("STRIP_OFFSET", strip_off))
        h.write("/* LOGO_FRAME_COUNT x LOGO_FRAME_TILES references: frame f starts at f * LOGO_FRAME_TILES. */\n")
        h.write(tab("FRAME_TILES", frame_refs, "0x%04x"))
        h.write("#define LOGO_FRAME_MS { %s }\n" % ", ".join(str(v) for v in meta["frame_ms"]))
        h.write("/* Free pieces (one 16x16 sprite each): frame f owns entries PIECE_FIRST[f] .. PIECE_FIRST[f + 1] - 1\n"
                "   of the three piece tables; x and y are screen coordinates. */\n")
        h.write(tab("PIECE_FIRST", piece_first))
        h.write(tab("PIECE_REF", [p[0] for p in flat], "0x%04x"))
        h.write(tab("PIECE_X", [p[1] for p in flat]))
        h.write(tab("PIECE_Y", [p[2] for p in flat]))
        h.write("/* Palette entries 1..15 as colour words (entry 0, transparent, is not in the table). */\n")
        for mood in MOODS:
            words = []
            for n, c in enumerate(meta["palettes"][mood][1:], 1):
                w, shown = ng_word(c)
                if shown != tuple(c):
                    rounded.append("%s entry %d: %s -> shown %s" % (mood, n, tuple(c), shown))
                words.append(w)
            h.write(tab("PALETTE_" + mood.upper(), words + [0] * (15 - len(words)), "0x%04x"))
        h.write("/* Most logo sprites (strips + free pieces) on one scanline, per frame. */\n")
        h.write(tab("WORST_LINE", [w[0] for w in worst]))
        h.write("#endif\n")

    # ---- self-check: shipped bytes only (c1/c2 through tiletool extract, tables parsed from the written header)
    dec = os.path.join(scratch, "decoded.png")
    subprocess.run([TILETOOL, "--sprite", "-x", c1, c2, "-o", dec, "-w", str(TILE * len(tiles))], check=True)
    got_atlas = Image.open(dec)
    src = open(hp).read()

    def shipped(r):
        assert (r & REF_TILE) < define(src, "TILE_COUNT"), "tile reference past LOGO_TILE_COUNT"
        t = cut(got_atlas, (r & REF_TILE) * TILE, 0)
        t = flip_x(t) if r & REF_FLIP_X else t
        return flip_y(t) if r & REF_FLIP_Y else t

    sx, sy, sh, so = (table(src, n) for n in ("STRIP_X", "STRIP_Y", "STRIP_H", "STRIP_OFFSET"))
    ft, n_ft = table(src, "FRAME_TILES"), define(src, "FRAME_TILES")
    assert len(ft) == nf * n_ft and len(sx) == define(src, "STRIP_COUNT")
    for f in range(nf):
        frame = Image.new("P", (fw, fh))
        for n in range(len(sx)):
            for k in range(sh[n]):
                frame.paste(Image.frombytes("P", (TILE, TILE), shipped(ft[f * n_ft + so[n] + k])),
                            (sx[n] - lx, sy[n] - ly + k * TILE))
        want = sheet.crop((0, f * fh, fw, (f + 1) * fh)).tobytes()
        bad = sum(x != y for x, y in zip(frame.tobytes(), want))
        assert not bad, "frame %d: %d pixels differ from %s" % (f, bad, sheet_path)
    pf, pr, pxs, pys = (table(src, n) for n in ("PIECE_FIRST", "PIECE_REF", "PIECE_X", "PIECE_Y"))
    for f in range(nf):
        for n, p in zip(range(pf[f], pf[f + 1]), piece_meta[f]):
            want = flip_x(ptiles[p["tile"]]) if p["flip_x"] else ptiles[p["tile"]]
            assert shipped(pr[n]) == want and (pxs[n], pys[n]) == (p["x"] + lx, p["y"] + ly), "piece %d of frame %d" % (n, f)
    for mood in MOODS:
        assert len(table(src, "PALETTE_" + mood.upper())) == 15
    for p in (atlas_png, dec):
        os.remove(p)
    os.rmdir(scratch)

    print("[OK] logo: tiles %d unique (still frame %d, body %d, free pieces add %d) + 1 blank, LOGO_TILE_COUNT %d"
          % (unique, len(still), body_tiles, unique - body_tiles, len(tiles)))
    print("     strips %d (%d tile references per frame), free pieces: most %d in one frame, %d in all"
          % (len(strips), per_frame, max(len(r) for r in pieces), len(flat)))
    print("     worst sprites per line %d; per frame (count at screen y): %s"
          % (max(w[0] for w in worst), " ".join("%d@%d" % w for w in worst)))
    print("     palette indices used: %d (%s)" % (len(used) - 1, used[1:]))
    for r in rounded:
        print("[INFO] not a 5-bit colour, nearest step taken: " + r)
    print("[OK] round-trip: %d frames of %dx%d and %d pieces rebuilt from logo.c1/c2 + logo_sprites.h, 0 pixels differ"
          % (nf, fw, fh, len(flat)))


if __name__ == "__main__":
    main()
