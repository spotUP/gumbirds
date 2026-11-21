#!/usr/bin/env python3
"""Gum Fling field sprite set: the approved hand-pixeled grids in tools/draw_fling_field.py -> a sheet + json in --out
-> build/gen/flfield.c1/.c2, flfield_sprites.h/.c, flfield_tables.h (via tools/sprite_pipeline.py).
Usage: $PYTHON -I tools/build_flfield_sprites.py [--out build/gen] [--no-verify]
Palettes (role order, so tile data is shared across moods): [0] turf dusk, [1] turf dusk again (puff anim), [2] gear dusk;
extra palettes turf_moon, turf_storm, gear_moon, gear_storm. Frame order: 0-3 turf P Q R S, 4-9 puff, 10 foul line,
11-24 boards (10..150 M without 90), 25.. the 90 M mark with one pennant frame each, then 3 Tug Gum chalk columns (L C R)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image
import draw_fling_field as art
import sprite_pipeline


def rgba(c):
    return art.snap(c) + (255,)


def main():
    out = "build/gen"
    for i, a in enumerate(sys.argv):
        if a == "--out" and i + 1 < len(sys.argv):
            out = sys.argv[i + 1]
    os.makedirs(out, exist_ok=True)
    tp, gp = art.TURF["dusk"], art.GEAR["dusk"]
    stacks = [("foul", [art.POLE, art.FOUL_TOP, art.FOUL_MID, art.FOUL_MID, art.FOUL_MID])]
    stacks += [("board%d" % m, [art.FACES[m], art.POST, art.TICK_TOP, art.TICK_MID, art.TICK_MID, art.TICK_MID]) for m in art.BOARD_M]
    stacks += [("mark%d" % i, [pen, art.MARK_FACE, art.MARK_POST, art.MARK_TOP, art.MARK_MID, art.MARK_MID, art.MARK_MID])
               for i, pen in enumerate(art.PENNANT)]
    W = 16 * len(stacks)
    sheet = Image.new("RGBA", (max(W, 32 * len(art.PUFF)), 64 + 32 + 7 * 16 + 64), (0, 0, 0, 0))
    anims = {"turf": [], "puff": [], "gear": [], "tug": []}
    for j, c in enumerate("PQRS"):
        art.stamp(sheet, art.TURF_COL[c], tp, 16 * j, 0)
        anims["turf"].append(dict(x=16 * j, y=0, w=16, h=64))
    for i, fr in enumerate(art.PUFF):
        art.stamp(sheet, fr, tp, 32 * i, 64)
        anims["puff"].append(dict(x=32 * i, y=64, w=32, h=32))
    for i, (_, tiles) in enumerate(stacks):
        for k, t in enumerate(tiles):
            art.stamp(sheet, t, gp, 16 * i, 96 + 16 * k)
        anims["gear"].append(dict(x=16 * i, y=96, w=16, h=16 * len(tiles)))
    for i, n in enumerate("LCR"):          # Tug Gum worn chalk columns: left win mark, centre line, right win mark
        art.stamp(sheet, art.TUG_COL[n], tp, 16 * i, 96 + 7 * 16)
        anims["tug"].append(dict(x=16 * i, y=96 + 7 * 16, w=16, h=64))
    px = sheet.load()
    for y in range(sheet.height):          # stamp() writes the snapped RGB at alpha 255; transparent stays (0,0,0,0)
        for x in range(sheet.width):
            if px[x, y][3] and px[x, y] != rgba(px[x, y][:3]):
                raise SystemExit("[ERROR] pixel not 5-bit")
    pal = lambda d: [list(art.snap(v)) for v in d.values()]
    meta = dict(animations=anims,
                palettes=dict(turf=pal(art.TURF["dusk"]), puff=pal(art.TURF["dusk"]), gear=pal(art.GEAR["dusk"])),
                extra_palettes={"turf_moon": pal(art.TURF["moon"]), "turf_storm": pal(art.TURF["storm"]),
                                "gear_moon": pal(art.GEAR["moon"]), "gear_storm": pal(art.GEAR["storm"])},
                defines=dict(turf_first=0, puff_first=4, puff_frames=len(art.PUFF), foul_frame=10, board_first=11,
                             board_count=len(art.BOARD_M), mark_first=11 + len(art.BOARD_M), mark_frames=len(art.PENNANT),
                             tug_first=11 + len(art.BOARD_M) + len(art.PENNANT)))
    sp, mp = os.path.join(out, "flfield_sheet.png"), os.path.join(out, "flfield_sheet.json")
    sheet.save(sp)
    json.dump(meta, open(mp, "w"))
    sys.argv = [a for a in sys.argv if a != "--out" and a != out] + ["--out", out]
    sprite_pipeline.main("flfield", sp, mp)


if __name__ == "__main__":
    main()
