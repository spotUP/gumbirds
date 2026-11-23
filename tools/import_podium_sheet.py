#!/usr/bin/env python3
"""Cut the approved event result art (draft B Podium) into assets/podium/podium_sheet.png + .json (input of tools/build_podium_sprites.py).
Usage: python3 -I tools/import_podium_sheet.py
Every pixel comes from the hand-typed grids in thoughts/shared/drafts/2026-11-23-event-result/draw_event_result.py (imported, its
main() is not run); this file only lays the finished tiles side by side and writes the frame rectangles.
shortcut: the block team colours are the dusk ones in every mood, add per-mood palettes when the owner wants them."""
import importlib.util, json, os
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DRAFT = f"{ROOT}/thoughts/shared/drafts/2026-11-23-event-result/draw_event_result.py"
spec = importlib.util.spec_from_file_location("draw_event_result", DRAFT)
d = importlib.util.module_from_spec(spec); spec.loader.exec_module(d)


def digit(ch, p):
    """the 16 x 24 chunky digit at the top of a 16 x 32 cell (two whole tiles, so the pipeline adds no padding)"""
    im = Image.new("RGBA", (16, 32), (0, 0, 0, 0))
    im.alpha_composite(d.chunk(ch, p))
    return im


def team(i):
    return dict(d.STONE, t=d.DS.TEAM["dusk"][i][0], T=d.DS.TEAM["dusk"][i][1])


anims = {  # name -> list of PIL frames. block: top left, top middle, bottom left, bottom middle (the right column is the left one flipped)
    **{f"block{i}": [d.tile(g, team(i)) for g in (d.P_TL, d.P_TM, d.P_BL, d.P_BM)] for i in (0, 1)},
    "crown": [d.tile(d.CROWN, d.GOLD)],
    "digit_gold": [digit(str(n), d.CHP[0]) for n in range(10)],   # winner
    "digit_blue": [digit(str(n), d.CHP[1]) for n in range(10)],   # loser
}
x = 0
rects = {}
sheet = Image.new("RGBA", (sum(im.width for f in anims.values() for im in f), 32), (0, 0, 0, 0))
for name, frames in anims.items():
    rects[name] = []
    for im in frames:
        rects[name].append(dict(x=x, y=0, w=im.width, h=im.height)); sheet.paste(im, (x, 0))
        x += im.width
sheet.save(f"{ROOT}/assets/podium/podium_sheet.png")
meta = {"source": "thoughts/shared/drafts/2026-11-23-event-result/draw_event_result.py hand-typed grids (layout B Podium)", "animations": rects}
json.dump(meta, open(f"{ROOT}/assets/podium/podium_sheet.json", "w"), indent=1)
print({k: len(v) for k, v in rects.items()}, sheet.size)
