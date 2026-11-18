#!/usr/bin/env python3
"""Cut the approved Pop Drop free-fall art into assets/popdrop/popdrop_sheet.png + .json (input of tools/build_popdrop_sprites.py).
Usage: python3 -I tools/import_popdrop_sheet.py
Every pixel comes from the hand-typed grids in thoughts/shared/drafts/2026-11-18-popdrop-freefall/draw_popdrop.py (imported, its
main() is not run); this file only lays the finished frames side by side and writes the frame rectangles."""
import importlib.util, json, os
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DRAFT = f"{ROOT}/thoughts/shared/drafts/2026-11-18-popdrop-freefall/draw_popdrop.py"
spec = importlib.util.spec_from_file_location("draw_popdrop", DRAFT)
d = importlib.util.module_from_spec(spec); spec.loader.exec_module(d)

B, P, G = d.BIRD, d.PLAT, d.GUM
anims = {  # name -> list of PIL frames, in draw order
    **{f"fall{s}": [d.img(d.fall2(w, s, w == 1), B) for w in range(3)] for s in range(3)},
    **{f"lean{s}": [d.img(d.lean2(s, k), B) for k in range(2)] for s in range(3)},
    "bonk": [d.img(d.BONK, B)],
    "crash": [d.img(d.splat_frame(), B), d.img(d.daze_frame(0), B), d.img(d.daze_frame(1), B)],
    "rag": [d.img(r, B) for r in d.RAG2] + [d.img(d.RAG_LIMP, B)],
    "fx": [d.img(d.STAR_BIG, B), d.img(d.STAR_SMALL, B), d.img(d.FEATHER, B), d.img(d.flip(d.FEATHER), B), d.img(d.IMPACT, B)],
    "plat": [d.img(t, P) for k in ("rock", "girder", "plank") for t in d.PTYPES[k]]
            + [d.img(d.STREAK_A, P), d.img(d.STREAK_B, P), d.img(d.WISP, P)],
    "shield": [d.img(d.shield2(f), G) for f in range(2)],
    "pop": [d.img(d.shield_pop2(k), G) for k in range(4)],
}
fixed = {"fall0": B, "plat": P, "shield": G}  # the first user of each palette fixes its order; the rest share it by subset

W = 400
x = y = rowh = 0
rects = {}
placed = []
for name, frames in anims.items():
    rects[name] = []
    for im in frames:
        if x + im.width > W: x, y, rowh = 0, y + rowh, 0
        rects[name].append(dict(x=x, y=y, w=im.width, h=im.height)); placed.append((im, x, y))
        x += im.width; rowh = max(rowh, im.height)
sheet = Image.new("RGBA", (W, y + rowh), (0, 0, 0, 0))
for im, px, py in placed: sheet.paste(im, (px, py))
sheet.save(f"{ROOT}/assets/popdrop/popdrop_sheet.png")
meta = {"source": "thoughts/shared/drafts/2026-11-18-popdrop-freefall/draw_popdrop.py hand-typed grids",
        "palette_policy": "subset", "palettes": {k: [list(c) for c in v] for k, v in fixed.items()}, "animations": rects}
json.dump(meta, open(f"{ROOT}/assets/popdrop/popdrop_sheet.json", "w"), indent=1)
print({k: len(v) for k, v in rects.items()}, sheet.size)
