#!/usr/bin/env python3
"""Import the Gumdrop fix font into assets/font/fix_font_sheet.png + fix_font.json.
Run: /opt/homebrew/bin/python3.14 -I tools/import_font_sheet.py   then `gmake`.

Source: assets/font/draw_hud_title_final.py (the final HUD/font drawing, copied from
thoughts/shared/drafts/2026-11-10-hud-title-final) and assets/font/numbers.txt (its measured numbers).
The sheet is 128 x 96 (16 tiles per row, tile index = row * 16 + column), palette-indexed: pixel value = colour index 0..15
(0 transparent). The json holds the five text palettes (white, pink, lime, gold, dim; 15 colours + transparent each) and
the tile index of every tile by name. tools/build_fix_font.py turns both into the S-ROM tiles and build/gen/fix_font.h.
Same shape as tools/import_islands_sheet.py (draw script loaded as a module, numbers.txt cross-check)."""
import importlib.util, json, os, re, sys
sys.dont_write_bytecode = True
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "assets/font")
PAL_ORDER = ["white", "pink", "lime", "gold", "dim"]
TILES_W, TILES_H = 16, 12


def load_draw():
    spec = importlib.util.spec_from_file_location("draw_hud_title_final", os.path.join(SRC, "draw_hud_title_final.py"))
    d = importlib.util.module_from_spec(spec)
    sys.modules["draw_hud_title_final"] = d
    spec.loader.exec_module(d)
    return d


def numbers_palettes():
    """{name: [(r,g,b) x 15]} from the 'palette text <name>' lines of numbers.txt."""
    out = {}
    for line in open(os.path.join(SRC, "numbers.txt")):
        m = re.match(r"palette text (\w+)\s*:\s*(.*)", line.strip())
        if m:
            v = [int(x) for x in re.findall(r"\d+", m.group(2))]
            out[m.group(1)] = [tuple(v[i:i + 3]) for i in range(0, len(v), 3)]
    return out


def main():
    d = load_draw()
    pals = {n: [tuple(int(v) for v in c) for c in d.FPAL[n][1:]] for n in PAL_ORDER}
    nums = numbers_palettes()
    assert nums == pals, "palettes of the draw script differ from numbers.txt"
    sheet = np.zeros((TILES_H * 8, TILES_W * 8), np.uint8)
    names = {}
    for key, i in d.TIDX.items():
        sheet[(i // 16) * 8:(i // 16) * 8 + 8, (i % 16) * 8:(i % 16) * 8 + 8] = d.TILE[key]
        names[":".join(str(k) for k in key)] = i
    assert len(names) == 157 and sheet.max() <= 15
    img = Image.fromarray(sheet, "P")
    pp = [0, 0, 0]
    for n in range(1, 16):
        pp += [n * 16] * 3
    img.putpalette(pp + [0] * (768 - len(pp)))
    img.save(os.path.join(SRC, "fix_font_sheet.png"))
    with open(os.path.join(SRC, "fix_font.json"), "w") as f:
        json.dump({"palette_order": PAL_ORDER, "palettes": pals, "tiles": names}, f, indent=1)
        f.write("\n")
    print("[OK] %d tiles, %d palettes -> assets/font/fix_font_sheet.png + fix_font.json" % (len(names), len(pals)))


if __name__ == "__main__":
    main()
