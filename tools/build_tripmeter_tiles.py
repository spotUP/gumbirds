#!/usr/bin/env python3
"""Gum Trip gum meter fix tiles: assets/tripmeter/tripmeter_sheet.png + .json -> build/gen/tripmeter.fix, tripmeter.h.
Usage: $PYTHON -I tools/build_tripmeter_tiles.py [--out build/gen] [--base 186]
The sheet is 13 fix tiles (104 x 8, palette image, pixel value = slot of the fix palette `white`, 0 transparent).
tripmeter.fix is 13 tiles of 32 bytes (S-ROM format, packed by tiletool --fix like tools/build_fix_font.py); it belongs at
tile TRIPMETER_BASE of the S ROM, which build_fix_font.py does not use (see the check below). tripmeter.h holds the tile numbers
and the cell table for fill steps 0..8. The palette is NOT emitted: the tiles use FIXFONT_PAL_WHITE from build/gen/fix_font.h.
The role of each tile is found by redrawing the meter from the rules of
thoughts/shared/drafts/2026-11-10-gum-trip-rival-meter-fix/draw_rival_meter_fix.py (meter section) and comparing pixel-exact."""
import argparse, json, os, subprocess, sys, tempfile
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image
import sprite_pipeline as sp
from build_fix_font import GAME_BASE  # S-ROM tile of font atlas tile 0

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TILETOOL = os.environ.get("TILETOOL", "/opt/homebrew/bin/tiletool.py")
SLOT = {"k": 5, "d": 9, "p": 10, "h": 11, "w": 12, "e": 13, "r": 4, "g": 15, "D": 6, "P": 7, "H": 8}
ICON = ["........", "..kkkk..", ".khhppkk", "kwhppppk", "khpppppk", "kpppppdk", ".kpddkkk", "..kkkk.."]
STEPS = 9            # fill steps 0..8 (8 = full)
CELLS = 5            # icon + 4 tube cells
BACKED = 96


def warn(rows):
    return [r.replace("d", "D").replace("p", "P").replace("h", "H") for r in rows]


def tube(state, mark, w):
    """state 0 empty, 1 first segment, 2 both; mark 'L' left of the half mark, 'R' right of it, '' plain."""
    rows = []
    for y in range(8):
        r = ""
        for s in (state >= 1, state >= 2):
            if y in (1, 6):
                r += "kkkk"
            elif y in (0, 7):
                r += "...."
            elif s:
                r += {2: "whh", 3: "ppp", 4: "ppp", 5: "ddd"}[y] + "k"
            else:
                r += {2: "eee", 3: "eee", 4: "eee", 5: "eer"}[y] + "k"
        r = list(r)
        if mark == "L":
            r[7] = "g"
            if y in (0, 7):
                r[6] = "g"
        if mark == "R" and y in (0, 7):
            r[0] = "g"
        rows.append("".join(r))
    return warn(rows) if (w and state > 0) else rows


def cells(step):
    w = step <= 2
    out = [("icon_warn" if w else "icon", warn(ICON) if w else ICON)]
    for c in range(4):
        st = max(0, min(2, step - 2 * c))
        m = {1: "L", 2: "R"}.get(c, "")
        name = "cell%s_%d%s" % (m, st, "_warn" if (w and st > 0) else "")
        out.append((name, tube(st, m, w)))
    return out


def to_px(rows):
    return np.array([[0 if ch == "." else SLOT[ch] for ch in r] for r in rows], np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "build/gen"))
    ap.add_argument("--sheet", default=os.path.join(ROOT, "assets/tripmeter/tripmeter_sheet.png"))
    ap.add_argument("--meta", default=os.path.join(ROOT, "assets/tripmeter/tripmeter_sheet.json"))
    ap.add_argument("--font", default=os.path.join(ROOT, "assets/font/fix_font.json"))
    ap.add_argument("--base", type=int, default=186, help="first S-ROM tile of the meter")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    meta = json.load(open(a.meta))
    n = meta["tile_count"]
    sheet = Image.open(a.sheet)
    if sheet.mode != "P" or sheet.size != (8 * n, 8) or len(meta["tiles"]) != n:
        sp.die("meter sheet must be a %dx8 palette image with %d names" % (8 * n, n))
    px = np.array(sheet, np.uint8)
    if px.max() > 15:
        sp.die("sheet pixel value above 15")
    tiles = [px[:, i * 8:i * 8 + 8] for i in range(n)]
    # free-slot check from the font's own tile table: build_fix_font.py writes only the tiles named there, plus the backed copies
    font = json.load(open(a.font))
    used = set(font["tiles"].values())
    used |= {v + BACKED for k, v in font["tiles"].items() if k[:2] in ("p:",) and v < 96} | {255}
    want = set(range(a.base, a.base + n))
    if want & used:
        sp.die("S-ROM tiles %s are taken by the font" % sorted(want & used))
    if a.base + n > 255:
        sp.die("meter runs into the blank tile 255")
    # role of every tile: redraw every step, match pixel-exact
    roles, table = {}, []
    for step in range(STEPS):
        row = []
        for name, rows in cells(step):
            p = to_px(rows)
            hit = [i for i, t in enumerate(tiles) if (t == p).all()]
            if len(hit) != 1:
                sp.die("step %d cell %s matches %d sheet tiles" % (step, name, len(hit)))
            roles.setdefault(name, hit[0])
            if roles[name] != hit[0]:
                sp.die("role %s maps to two tiles" % name)
            row.append(hit[0])
        table.append(row)
    if sorted(set(roles.values())) != list(range(n)):
        sp.die("%d of %d tiles are used by the nine steps" % (len(set(roles.values())), n))
    # colours: at most 15 + transparent per tile, one palette in total
    per = [len(set(np.unique(t)) - {0}) for t in tiles]
    allidx = sorted(set(np.unique(px)) - {0})
    if max(per) > 15 or meta.get("fix_palette") != "white" or meta["colour_not_in_white_palette"]:
        sp.die("palette check failed")
    # pack: 16-slot atlas (128 wide), tile i at slot i; decode again and compare
    if n > 16:
        sp.die("more than 16 meter tiles")
    atlas = np.zeros((8, 128), np.uint8)
    for i, t in enumerate(tiles):
        atlas[:, i * 8:i * 8 + 8] = t
    img = Image.fromarray(atlas, "P")
    img.putpalette(sheet.getpalette())
    apng = os.path.join(a.out, "tripmeter_atlas.png")
    img.save(apng)
    full = os.path.join(a.out, "tripmeter_full.fix")
    subprocess.run([TILETOOL, "--fix", "-c", apng, "-o", full], check=True)
    blob = open(full, "rb").read()[:32 * n]
    os.remove(full)
    os.remove(apng)
    open(os.path.join(a.out, "tripmeter.fix"), "wb").write(blob)
    with tempfile.TemporaryDirectory() as tmp:
        f2 = os.path.join(tmp, "m.fix")
        open(f2, "wb").write(blob + bytes(32 * (16 - n)))
        dec = os.path.join(tmp, "d.png")
        subprocess.run([TILETOOL, "--fix", "-x", f2, "-o", dec, "-w", "128"], check=True)
        d = np.array(Image.open(dec))
        if d.shape != atlas.shape or not (d == atlas).all():
            sp.die("tripmeter.fix does not decode to the sheet")
    names = sorted(roles, key=roles.get)
    h = ["/* Generated by tools/build_tripmeter_tiles.py from assets/tripmeter/tripmeter_sheet.png. Do not edit. */",
         "#ifndef TRIPMETER_H", "#define TRIPMETER_H", "#include <stdint.h>", "",
         "/* S-ROM tiles TRIPMETER_BASE .. +TRIPMETER_TILES-1 hold tripmeter.fix. Palette: FIXFONT_PAL_WHITE (fix_font.h), no second palette. */",
         "#define TRIPMETER_TILES %d" % n, "#define TRIPMETER_BASE %d" % (GAME_BASE + a.base),
         "#define TRIPMETER_STEPS %d    /* fill steps 0..8; step 8 is full, step 4 ends on the half mark */" % STEPS,
         "#define TRIPMETER_CELLS %d    /* icon + 4 tube cells, left to right */" % CELLS,
         "#define TRIPMETER_WARN_MAX 2  /* red icon and fill at step <= this */", ""]
    for nm in names:
        h.append("#define TRIPMETER_T_%s %d" % (nm.upper(), GAME_BASE + a.base + roles[nm]))
    h += ["", "/* S-ROM tile number for [step][cell]. */", "static const uint16_t tripmeter_cell[TRIPMETER_STEPS][TRIPMETER_CELLS] = {"]
    for s, row in enumerate(table):
        h.append("    { %s }, /* step %d */" % (", ".join(str(GAME_BASE + a.base + v) for v in row), s))
    h += ["};", "", "#endif", ""]
    open(os.path.join(a.out, "tripmeter.h"), "w").write("\n".join(h))
    print("[OK] tripmeter: %d tiles at %d..%d, max %d colours per tile, palette indices %s (all in `white`), round-trip 0 mismatches"
          % (n, a.base, a.base + n - 1, max(per), allidx))


if __name__ == "__main__":
    main()
