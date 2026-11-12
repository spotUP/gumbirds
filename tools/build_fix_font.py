#!/usr/bin/env python3
"""Fix-layer font: assets/font/fix_font_sheet.png + fix_font.json -> build/gen/fix_font.fix, fix_font.h.
Usage: $PYTHON -I tools/build_fix_font.py [--out build/gen]
The sheet is imported by tools/import_font_sheet.py. fix_font.fix is the whole S-ROM font: FIXFONT_SROM_TILES tiles of 32 bytes,
tile index = sheet index (gaps are blank), tile FIXFONT_BLANK stays transparent (gfx_cls fills with it). fix_font.h holds the
tile constants, the five fix palettes as Neo Geo words, and the char to tile maps (src/gfx.c prints through them).
Palette words reuse tools/sprite_pipeline.rgb_to_ng; the packed bytes are decoded again with tiletool --fix -x and compared."""
import argparse, json, os, subprocess, sys, tempfile
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image
import sprite_pipeline as sp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TILETOOL = os.environ.get("TILETOOL", "/opt/homebrew/bin/tiletool.py")
SROM_TILES = 256      # tiles in fix_font.fix; the last one (255) is the blank tile
BLANK = 255
BACKED = 96           # a backed copy of tile t (navy plate behind the glyph) is t + 96
TALL_TOP, TALL_BOTTOM = 64, 80
PUNCT = ".,:!?-'/<>"  # tiles 36..45 in this order
UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
DIGITS = "0123456789"


def char_maps(t):
    """name -> 256 tile numbers. Letters in either case map to the capital (the font has no lowercase)."""
    def plain():
        m = [BLANK] * 256
        for c in UPPER:
            m[ord(c)] = m[ord(c.lower())] = t["p:" + c]
        for c in DIGITS + PUNCT + "^":
            m[ord(c)] = t["p:" + c]
        m[ord("{")], m[ord("}")] = t["p:{"], t["p:}"]  # heart, gum bubble
        return m
    p = plain()
    maps = {"": p, "_backed": [BLANK if v == BLANK else v + BACKED for v in p]}
    for tag, k in (("tall_top", 0), ("tall_bottom", 1)):
        for suf, kind in (("", "pt"), ("_backed", "bt")):
            m = [BLANK] * 256
            for d in DIGITS:
                m[ord(d)] = t["%s:%s:%d" % (kind, d, k)]
            maps["_" + tag + suf] = m
    return maps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "build/gen"))
    ap.add_argument("--sheet", default=os.path.join(ROOT, "assets/font/fix_font_sheet.png"))
    ap.add_argument("--meta", default=os.path.join(ROOT, "assets/font/fix_font.json"))
    ap.add_argument("--overlay", action="append", default=[], metavar="PNG@TILE",
                    help="paste a palette image (8 pixel rows, width a multiple of 8) at tiles TILE.. of the atlas, left to right; "
                         "the target tiles must be transparent (all 0)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    meta = json.load(open(a.meta))
    t = meta["tiles"]
    sheet = Image.open(a.sheet)
    if sheet.mode != "P" or sheet.size != (128, 96):
        sp.die("font sheet must be a 128x96 palette image")
    px = np.array(sheet, np.uint8)
    if px.max() > 15:
        sp.die("sheet pixel value above 15")
    # atlas: 16 tiles per row, SROM_TILES tiles; tiles the sheet does not hold stay 0 (transparent)
    atlas = np.zeros((SROM_TILES // 16 * 8, 128), np.uint8)
    atlas[:px.shape[0]] = px
    for spec in a.overlay:
        path, _, at = spec.rpartition("@")
        if not path or not at.isdigit():
            sp.die("--overlay wants PNG@TILE, got %r" % spec)
        ov = Image.open(path)
        if ov.mode != "P" or ov.size[1] != 8 or ov.size[0] % 8:
            sp.die("%s must be a palette image 8 pixels high, width a multiple of 8" % path)
        o = np.array(ov, np.uint8)
        if o.max() > 15:
            sp.die("%s pixel value above 15" % path)
        for k in range(o.shape[1] // 8):
            tile = int(at) + k
            if tile >= SROM_TILES or tile == BLANK:
                sp.die("overlay tile %d is out of range or the blank tile" % tile)
            dst = atlas[(tile // 16) * 8:(tile // 16) * 8 + 8, (tile % 16) * 8:(tile % 16) * 8 + 8]
            if dst.any():
                sp.die("overlay tile %d is not transparent in the font atlas" % tile)
            dst[:] = o[:, k * 8:k * 8 + 8]
    if atlas[(BLANK // 16) * 8:, (BLANK % 16) * 8:(BLANK % 16) * 8 + 8].any():
        sp.die("tile %d must stay blank" % BLANK)
    img = Image.fromarray(atlas, "P")
    img.putpalette(sheet.getpalette())
    atlas_png = os.path.join(a.out, "fix_font_atlas.png")
    img.save(atlas_png)
    fix = os.path.join(a.out, "fix_font.fix")
    subprocess.run([TILETOOL, "--fix", "-c", atlas_png, "-o", fix], check=True)
    if os.path.getsize(fix) != 32 * SROM_TILES:
        sp.die("%s size %d != %d" % (fix, os.path.getsize(fix), 32 * SROM_TILES))
    with tempfile.TemporaryDirectory() as tmp:  # verify: decode the shipped bytes and compare pixel-exact
        dec = os.path.join(tmp, "dec.png")
        subprocess.run([TILETOOL, "--fix", "-x", fix, "-o", dec, "-w", "128"], check=True)
        d = np.array(Image.open(dec))
        if d.shape != atlas.shape or not (d == atlas).all():
            sp.die("fix_font.fix does not decode to the sheet")
    names = meta["palette_order"]
    pal_words = []
    for n in names:
        pal_words.append([0x8000] + [sp.rgb_to_ng(tuple(c)) for c in meta["palettes"][n]])
    maps = char_maps(t)
    h = ["/* Generated by tools/build_fix_font.py from assets/font/fix_font_sheet.png. Do not edit. */",
         "#ifndef FIX_FONT_H", "#define FIX_FONT_H", "#include <stdint.h>", "",
         "#define FIXFONT_TILE_COUNT %d   /* tiles the sheet draws */" % len(t),
         "#define FIXFONT_SROM_TILES %d   /* tiles in the packed font; the rest of the S-ROM is zero */" % SROM_TILES,
         "#define FIXFONT_BLANK %d        /* transparent tile: gfx_cls fill, space and unknown characters */" % BLANK,
         "#define FIXFONT_BACKED %d       /* backed copy of tile t = t + FIXFONT_BACKED */" % BACKED,
         "#define FIXFONT_TALL_TOP %d     /* tall digit d: top tile FIXFONT_TALL_TOP + d, bottom FIXFONT_TALL_BOTTOM + d */" % TALL_TOP,
         "#define FIXFONT_TALL_BOTTOM %d" % TALL_BOTTOM,
         "#define FIXFONT_TALL_BACKED %d  /* backed tall tile = tall tile + FIXFONT_BACKED */" % BACKED]
    for k, name in (("p:A", "LETTER_A"), ("p:0", "DIGIT_0"), ("p:.", "PUNCT_FIRST"), ("p:<", "GLYPH_LT"), ("p:>", "GLYPH_GT"),
                    ("p:^", "ARROW_UP"), ("p:v", "ARROW_DOWN"), ("p:{", "ICON_HEART"), ("p:}", "ICON_GUM"), ("p:~L", "ICON_SOOT_LEFT"),
                    ("p:~R", "ICON_SOOT_RIGHT"), ("s:capL", "PLATE_CAP_LEFT"), ("s:capR", "PLATE_CAP_RIGHT"), ("s:joint", "PLATE_JOINT"),
                    ("s:fill", "PLATE_FILL"), ("s:f_tl", "FRAME_TL"), ("s:f_t", "FRAME_T"), ("s:f_tr", "FRAME_TR"), ("s:f_l", "FRAME_L"),
                    ("s:f_r", "FRAME_R"), ("s:f_bl", "FRAME_BL"), ("s:f_b", "FRAME_B"), ("s:f_br", "FRAME_BR"), ("s:rule", "RULE"), ("s:pop_burst", "POP_BURST")):
        h.append("#define FIXFONT_%s %d" % (name, t[k]))
    h += ["", "/* Fix palette slots 0..FIXFONT_PAL_COUNT-1 (palette RAM entries slot * 16 + i), in this order. Entry 0 is transparent. */",
          "#define FIXFONT_PAL_COUNT %d" % len(names)]
    h += ["#define FIXFONT_PAL_%s %d" % (n.upper(), i) for i, n in enumerate(names)]
    h += ["static const uint16_t fixfont_palettes[FIXFONT_PAL_COUNT][16] = {"]
    for n, row in zip(names, pal_words):
        h.append("    { %s }, /* %s */" % (", ".join("0x%04x" % w for w in row), n))
    h += ["};", "", "/* Character to fix tile (index = unsigned char). _backed: with the navy plate behind; tall_*: digits only (two rows). */"]
    for suf, m in maps.items():
        h.append("static const uint16_t fixfont_map%s[256] = {" % suf)
        for i in range(0, 256, 16):
            h.append("    " + ", ".join(str(v) for v in m[i:i + 16]) + ",")
        h.append("};")
    h += ["", "#endif", ""]
    open(os.path.join(a.out, "fix_font.h"), "w").write("\n".join(h))
    print("[OK] fix font: %d tiles drawn, %d tiles packed, %d palettes; round-trip 0 mismatches" % (len(t), SROM_TILES, len(names)))


if __name__ == "__main__":
    main()
