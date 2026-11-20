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

T = f"{ROOT}/thoughts/shared/drafts/2026-11-20-popdrop-terror/draw_terror.py"  # take A "screaming flail": fall/lean faces
tspec = importlib.util.spec_from_file_location("draw_terror", T)
t = importlib.util.module_from_spec(tspec); tspec.loader.exec_module(t)

FUN = f"{ROOT}/thoughts/shared/drafts/2026-11-20-popdrop-fun/draw_fun.py"  # batch 1: brake hop, feather puff, half bald, bubble parachute A, ghost A
fspec = importlib.util.spec_from_file_location("draw_fun", FUN)
fu = importlib.util.module_from_spec(fspec); fspec.loader.exec_module(fu)

B, P, G = d.BIRD, d.PLAT, d.GUM
# Half bald: lit skin e would be green on the computer / player 2 palettes, so the bare skin is remapped to the salmon slots
# a, b, c (red to salmon in every bird palette) at import: e->c, c->b, b->a (owner pick 2026-11-20). Only the BALD base grid is
# remapped; the stamped eyes, wings, beak and hair keep their own colours.
fu.BALD = [r.translate(str.maketrans("ecb", "cba")) for r in fu.BALD]


def cell(w, h, parts):
    """a w x h grid (a whole number of tiles, so the pipeline adds no padding) with the parts stamped at their cell positions"""
    return fu.many(fu.blank(w, h), parts)


# Shield cell 32 x 48: the parachute bubble (24 px at bird art x 8, y -22) and the strand down to the beak (art x 19) -> cell x 4, y 0.
# The view places it at bird box x + 8, bird top - 22. The pop frames (48 x 48) already centre the bubble at (12, 12): view origin x + 0, top - 34.
SHIELD_CELL = cell(32, 48, [(fu.bubble(3, "a"), 4, 0), (fu.STRAND[-18:], 15, 24)])
anims = {  # name -> list of PIL frames, in draw order
    **{f"fall{s}": [d.img(t.take_a(0, s, k), B) for k in range(3)] for s in range(3)},
    **{f"lean{s}": [d.img(t.take_a(1, s, k), B) for k in range(2)] for s in range(3)},
    "bonk": [d.img(d.BONK, B)],
    "crash": [d.img(d.splat_frame(), B), d.img(d.daze_frame(0), B), d.img(d.daze_frame(1), B)],
    "rag": [d.img(r, B) for r in d.RAG2] + [d.img(d.RAG_LIMP, B)],
    "fx": [d.img(d.STAR_BIG, B), d.img(d.STAR_SMALL, B), d.img(d.FEATHER, B), d.img(d.flip(d.FEATHER), B), d.img(d.IMPACT, B)],
    "plat": [d.img(t, P) for k in ("rock", "girder", "plank") for t in d.PTYPES[k]]
            + [d.img(d.STREAK_A, P), d.img(d.STREAK_B, P), d.img(d.WISP, P)],
    "shield": [d.img(SHIELD_CELL, G)],
    "pop": [d.img(fu.pop(k, "a"), G) for k in range(6)],
    "hop": [d.img(fu.hop(k), B) for k in range(4)],       # frames 0..1 are the draft's strain frames, the view uses 2, 3 and 1
    "bald": [d.img(fu.bald(k), B) for k in range(2)],
    "hang": [d.img(fu.hang(k), B) for k in (2, 3)],       # hanging under the bubble, eyes up
    "puff": [d.img(cell(48, 48, [(fu.burst(k), 2, 2)]), B) for k in range(6)],   # 44 x 44 burst, centred in the tile box
    "ghost": [d.img(fu.ghost(k, "a"), fu.SPIRIT) for k in range(3)],
}
fixed = {"fall0": B, "plat": P, "shield": G, "ghost": fu.SPIRIT}  # the first user of each palette fixes its order; the rest share it by subset

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
