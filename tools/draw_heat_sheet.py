#!/usr/bin/env python3
"""Draws the overheat bar tiles: assets/laser/heat_sheet.png + heat_sheet.json (python3.14 -I, Pillow).
Original pixel art, hand placed (no ramps, no dithering). Usage (repo root): python3.14 -I tools/draw_heat_sheet.py [outdir]

The bar is 16 cells of 8x8 px = 8 sprite tiles of 16x8. Frame index = pair * 3 + fill, where pair is
0..7 (two cells per tile) and fill is 0..2 cells lit in that tile. Cell tone by position: cells 0..8
green (safe), 9..12 orange (warm), 13..15 red (about to overheat). Each lit cell: ink outline, a body
colour, a 2 px light cluster top left and a shade row at the bottom. An unlit cell: ink outline and a
dim plum body with one lighter notch. No colour is shared with the hero, obstacle, city or laser
palettes (checked by tests/mame/check_laser_pixels.py through tolerance matching)."""
import json, os, sys
from PIL import Image

def snap(h):
    v = [round(int(h[i:i + 2], 16) * 31 / 255) for i in (1, 3, 5)]
    return tuple((x << 3) | (x >> 2) for x in v)

PAL = {
    "ink": "#07060f", "offB": "#2a1f45", "offN": "#4a3a72",
    "gB": "#2bd67b", "gH": "#a8ffc8", "gS": "#128a4c",
    "oB": "#ff8a1f", "oH": "#ffd08a", "oS": "#b34d0a",
    "rB": "#ff2a2a", "rH": "#ff9a8a", "rS": "#a00c1c",
}
P = {k: snap(v) for k, v in PAL.items()}

def cell(px, ox, cell_idx, lit):
    tone = "g" if cell_idx < 9 else ("o" if cell_idx < 13 else "r")
    for y in range(8):
        for x in range(8):
            edge = x in (0, 7) or y in (0, 7)
            if edge:
                c = P["ink"]
            elif lit:
                c = P[tone + "B"]
                if y == 6:
                    c = P[tone + "S"]
                if (x, y) in ((1, 1), (2, 1), (1, 2)):
                    c = P[tone + "H"]
            else:
                c = P["offB"]
                if (x, y) == (1, 1):
                    c = P["offN"]
            px[ox + x, y] = c + (255,)

def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "assets/laser"
    os.makedirs(out, exist_ok=True)
    W, H = 16, 8
    cols, rows = 3, 8
    im = Image.new("RGBA", (cols * (W + 2), rows * (H + 2)), (0, 0, 0, 0))
    frames = []
    for pair in range(rows):
        for fill in range(cols):
            fx, fy = fill * (W + 2), pair * (H + 2)
            sub = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            px = sub.load()
            for k in range(2):
                ci = pair * 2 + k
                cell(px, k * 8, ci, k < fill)
            im.paste(sub, (fx, fy))
            frames.append({"x": fx, "y": fy, "w": W, "h": H})
    im.save(os.path.join(out, "heat_sheet.png"))
    meta = {
        "source": "original pixel art drawn by tools/draw_heat_sheet.py (no external art)",
        "origin": "frame index = pair * 3 + fill; art bottom = frame bottom",
        "palette_policy": "merge",
        "animations": {"bar": frames},
    }
    with open(os.path.join(out, "heat_sheet.json"), "w") as f:
        json.dump(meta, f, indent=1)

main()
