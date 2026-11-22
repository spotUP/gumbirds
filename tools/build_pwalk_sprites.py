#!/usr/bin/env python3
"""Poop the Man walkway: assets/poop_walk/strip.png (320x64, screen rows 160..223, owner pick strip_2 2026-11-22) -> 20 column frames of 16x64
plus one contact shadow frame (16x16) -> build/gen/pwalk.c1/.c2, pwalk_sprites.h/.c, pwalk_tables.h (via tools/sprite_pipeline.py).
The strip is sampled from the moon backdrop: palette 0 is the moon palette; extra palettes dusk and storm are the same colours
shifted (same indices, so the tile data is shared). Frames: 0..19 strip columns, 20 shadow.
Usage: $PYTHON -I tools/build_pwalk_sprites.py [--out build/gen] [--no-verify]"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image
import sprite_pipeline

HERE = os.path.dirname(os.path.abspath(__file__))
SHADOW = ["..K.K.K.K.K...", ".K.KKKKKKK.K..", "..K.K.K.K.K.K."]   # dithered contact shadow (draft draw_walkway.py): sampled moon K = #000010
SH_X, SH_Y = 1, 13        # pattern offset in the 16x16 shadow cell: its top row sits 13 px down, so sprite y = feet - 1 - 13


def snap(c):          # Neo Geo 5 bits per channel
    return tuple((v >> 3 << 3) | (v >> 5) for v in c)


def dusk(c):          # warmer, red up and blue down
    r, g, b = c
    return snap((min(255, int(r * 1.2 + 14)), int(g * 0.95), int(b * 0.8)))


def storm(c):         # greyer and darker
    r, g, b = c
    l = (r * 3 + g * 5 + b * 2) // 10
    return snap((int((r + l) * 0.4), int((g + l) * 0.42), int((b + l) * 0.45)))


def main():
    out = "build/gen"
    for i, a in enumerate(sys.argv):
        if a == "--out" and i + 1 < len(sys.argv):
            out = sys.argv[i + 1]
    os.makedirs(out, exist_ok=True)
    strip = Image.open(os.path.join(HERE, "..", "assets", "poop_walk", "strip.png")).convert("RGBA")
    assert strip.size == (320, 64)
    sp = strip.load()
    cols = []
    for y in range(64):
        for x in range(320):
            if sp[x, y][:3] not in cols:
                cols.append(sp[x, y][:3])
    cols.sort()
    assert len(cols) <= 15 and all(sp[x, y][3] == 255 for y in range(64) for x in range(320))
    sheet = Image.new("RGBA", (320, 80), (0, 0, 0, 0))
    sheet.paste(strip, (0, 0))
    k = (0, 0, 16, 255)
    assert k[:3] in cols
    for r, row in enumerate(SHADOW):
        for c, ch in enumerate(row):
            if ch == "K":
                sheet.putpixel((SH_X + c, 64 + SH_Y + r), k)
    anims = {"strip": [dict(x=16 * i, y=0, w=16, h=64) for i in range(20)], "shadow": [dict(x=0, y=64, w=16, h=16)]}
    pal = lambda f: [list(f(c)) for c in cols]
    meta = dict(animations=anims, palettes=dict(strip=pal(lambda c: c), shadow=pal(lambda c: c)),
                extra_palettes={"dusk": pal(dusk), "storm": pal(storm)},
                defines=dict(strip_first=0, strip_columns=20, shadow_frame=20))
    shp, mp = os.path.join(out, "pwalk_sheet.png"), os.path.join(out, "pwalk_sheet.json")
    sheet.save(shp)
    json.dump(meta, open(mp, "w"))
    sys.argv = [a for a in sys.argv if a != "--out" and a != out] + ["--out", out]
    sprite_pipeline.main("pwalk", shp, mp)


if __name__ == "__main__":
    main()
