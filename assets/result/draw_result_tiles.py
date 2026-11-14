#!/usr/bin/env python3
"""Fix-layer tiles and palettes of the bonus stage result screen (look C, Gum machine): writes result_tiles.png (14 tiles, 8 pixel rows,
overlay for tools/build_fix_font.py at atlas tile 199) and result_palettes.json (five fix palettes). Both outputs are checked in.
Usage: /opt/homebrew/bin/python3.14 -I assets/result/draw_result_tiles.py
Bubble art and colours: thoughts/shared/drafts/2026-11-13-bonus-result/draw_bonus_result.py (BUB, BUBCOL)."""
import json, os, sys
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "tools"))
import sprite_pipeline as sp
import numpy as np
from PIL import Image

BUB = ["....oooooo......", "...ooBBBBBBoo...", "..oBBlllBBBBBo..", ".oBBlwwlBBBBBBo.", ".oBlwwBBBBBBBBo.",
       "oBBlwBBBBBBBBBBo", "oBBlBBBBBBBBBBSo", "oBBBBBBBBBBBBSSo", "oBBBBBBBBBBBSSSo", "oBBBBBBBBBBSSSSo",
       "oSBBBBBBBBSSSSco", ".oSBBBBBBSSSScco.", ".oSSBBBSSSSSSco.", "..oSSSSSSSScco..", "...ooSSSSSoo....", ".....oooooo....."]
BUB = [r.ljust(16, ".")[:16] for r in BUB]
LETTER = {"o": 2, "S": 3, "B": 4, "l": 5, "w": 6, "c": 7}  # bubble palette index of each art letter; index 1 is the cage interior
INTERIOR = (16, 8, 41)
EDGE = (107, 115, 198)
BUBCOL = {
    "pink": dict(o=(132, 16, 49), S=(181, 41, 165), B=(255, 82, 181), l=(255, 165, 222), w=(255, 255, 255), c=(255, 198, 90)),
    "gold": dict(o=(132, 60, 16), S=(206, 123, 24), B=(255, 198, 90), l=(255, 231, 156), w=(255, 255, 255), c=(255, 140, 120)),
    "dark": dict(o=(16, 8, 41), S=(24, 24, 74), B=(49, 49, 107), l=(82, 82, 148), w=(107, 115, 198), c=(24, 24, 74)),
}
SCENE = [(24, 24, 74), (36, 28, 90), (49, 36, 107),  # 1..3 stripe tones
         INTERIOR, EDGE,                              # 4 cage interior, 5 cage edge
         (49, 49, 107), (82, 148, 181), (140, 200, 222),  # 6..8 pipe: outline, body, highlight
         (255, 198, 90), (132, 16, 80), (49, 12, 64)]     # 9 machine gold, 10 plum, 11 plum dark
TILES = ["stripe", "cage_edge", "cage_fill", "pipe", "mach_edge", "mach_fill", "bub_tl", "bub_tr", "bub_bl", "bub_br",
         "ghost_tl", "ghost_tr", "ghost_bl", "ghost_br"]


def snap(c):
    return tuple(sp.expand5(sp.to5(v)) for v in c)


def solid(i):
    return np.full((8, 8), i, np.uint8)


def bubble_tiles(ghost):
    out = []
    for ty in range(2):
        for tx in range(2):
            t = np.ones((8, 8), np.uint8)  # 1: the cage interior behind the bubble
            for y in range(8):
                for x in range(8):
                    ch = BUB[ty * 8 + y][tx * 8 + x]
                    if ch == ".":
                        continue
                    if ghost:
                        if ch == "o" and (tx * 8 + x + ty * 8 + y) % 2 == 0:
                            t[y, x] = 2
                    else:
                        t[y, x] = LETTER[ch]
            out.append(t)
    return out


def main():
    stripe = np.array([[(1, 1, 1, 2, 2, 3, 3, 2)[(x + y) & 7] for x in range(8)] for y in range(8)], np.uint8)
    pipe = np.array([[i] * 8 for i in (6, 7, 8, 8, 7, 7, 7, 6)], np.uint8)
    tiles = [stripe, solid(5), solid(4), pipe, solid(9), solid(10)] + bubble_tiles(False) + bubble_tiles(True)
    assert len(tiles) == len(TILES)
    img = Image.fromarray(np.concatenate(tiles, axis=1), "P")
    img.putpalette([c for i in range(256) for c in (i * 17 % 256,) * 3])
    img.save(os.path.join(HERE, "result_tiles.png"))
    pals = {"res_scene": SCENE}
    for k in ("pink", "gold", "dark"):
        pals["res_" + k] = [INTERIOR] + [BUBCOL[k][c] for c in "oSBlwc"]
    pals["res_ghost"] = [INTERIOR, EDGE]
    pals = {n: [list(snap(c)) for c in p] for n, p in pals.items()}
    json.dump({"tiles": TILES, "palette_order": list(pals), "palettes": pals}, open(os.path.join(HERE, "result_palettes.json"), "w"), indent=1)
    print("[OK] %d tiles, %d palettes" % (len(tiles), len(pals)))


main()
