#!/usr/bin/env python3
"""Parachute sheet (variant C, owner pick 2026-11-16): assets/chute/chute_sheet.png + .json from the hand-pixeled rival strip.
The strip (thoughts/shared/drafts/2026-11-16-gum-parachute/parachute_C_1x.png, 8 frames of 32x32 in the rival palette) goes in row 0 as
animation "cpu"; row 1 is the same pixels with every rival palette colour swapped for the player palette colour of the same index
(assets/flier/sootling_sheet.json), so the pair shares tile data. No drawing happens here.
Usage: python3.14 -I tools/make_chute_sheet.py <parachute_C_1x.png>"""
import json, sys
from PIL import Image

src = Image.open(sys.argv[1]).convert("RGBA")
assert src.size == (256, 32), src.size
pal = json.load(open("assets/flier/sootling_sheet.json"))["palettes"]
swap = {tuple(c): tuple(p) for c, p in zip(pal["cpu"], pal["player"])}
sheet = Image.new("RGBA", (256, 64), (0, 0, 0, 0))
sheet.paste(src, (0, 0))
px = src.load()
out = Image.new("RGBA", src.size)
o = out.load()
for y in range(32):
    for x in range(256):
        r, g, b, a = px[x, y]
        if a:
            o[x, y] = swap[(r, g, b)] + (255,)
sheet.paste(out, (0, 32))
sheet.save("assets/chute/chute_sheet.png")
cells = lambda y: [{"x": 32 * i, "y": y, "w": 32, "h": 32} for i in range(8)]
with open("assets/chute/chute_sheet.json", "w") as f:
    json.dump({"source": "tools/make_chute_sheet.py", "animations": {"player": cells(32), "cpu": cells(0)},
               "palettes": {"player": pal["player"], "cpu": pal["cpu"]},
               "defines": {"FRAME_TICKS": 8}, "tables": {}}, f, indent=1)
