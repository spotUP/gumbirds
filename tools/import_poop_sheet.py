#!/usr/bin/env python3
"""Cut the Poop the Man art into assets/poop/poop_sheet.png + .json (input of tools/build_poop_sprites.py).
Usage: python3 -I tools/import_poop_sheet.py
Every pixel comes from the hand-typed grids in thoughts/shared/drafts/2026-11-20-poop-the-man-v2/draw_poop_the_man.py (imported, its
main() is not run); this file only stamps the grids into transparent cells and writes the frame rectangles.
Cells: walker 32x48 (20 frames: walk 6, umbrella walk 6, hit 3, fist 2, throw 3), umbrella 36x64 (the walker cell plus 16 px above it; closed, half,
open, shaft included, drawn at the walker's x and top - 16), items 16x16 (poop 8x8 at 4,4; splats bottom aligned). Street plane, fix-layer pips
and rain are not imported yet."""
import importlib.util, json, os
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
spec = importlib.util.spec_from_file_location("draw_poop", f"{ROOT}/thoughts/shared/drafts/2026-11-20-poop-the-man-v2/draw_poop_the_man.py")
d = importlib.util.module_from_spec(spec); spec.loader.exec_module(d)
assert not d.ERR, d.ERR

def s5(c):
    return tuple(((f := round(v * 31 / 255)) << 3 | f >> 2) for v in c[:3])  # pipeline wants 5-bit expanded colours

def cell(w, h, parts, pal):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = im.load()
    for x0, y0, rows in parts:
        for j, r in enumerate(rows):
            for i, c in enumerate(r):
                if c != ".": px[x0 + i, y0 + j] = s5(pal[c]) + (255,)
    return im

UOFF = 16
UW = 36   # the open canopy spans x 4..36 of the walker cell (grip - 18 .. + 14), so the umbrella cell is 36 wide
anims, fixed, extra = {}, {}, {}
for tp in d.TYPES:
    fr = d.FR[tp]
    anims[tp] = [cell(32, 48, [(0, 0, c)], d.WPAL[tp]) for k in ("walk", "walk_umb", "hit", "fist", "throw") for c in fr[k]]
    fixed[tp] = [s5(c) for c in d.WPAL[tp].values()]
    blank = ["." * 32] * 48
    def umb(kind):
        im = Image.new("RGB", (UW, 48 + UOFF), (255, 0, 255)); d.draw_walker(im, 0, UOFF, tp, blank, umb=kind, ucol="red")
        px, out = im.load(), Image.new("RGBA", im.size, (0, 0, 0, 0)); op = out.load()
        for y in range(im.height):
            for x in range(im.width):
                if px[x, y] != (255, 0, 255): op[x, y] = s5(px[x, y]) + (255,)
        return out
    anims["umb_" + tp] = [umb(k) for k in ("closed", "half", "open")]
    fixed["umb_" + tp] = [s5(c) for c in d.UMB["red"].values()]
    extra["umb_" + tp + "_yellow"] = [list(s5(c)) for c in d.UMB["yellow"].values()]
    extra["umb_" + tp + "_teal"] = [list(s5(c)) for c in d.UMB["teal"].values()]
I = d.ITEMS
anims["poop"] = [cell(16, 16, [(4, 4, g)], I) for g in d.POOP]
anims["splat_head"] = [cell(16, 16, [(0, 8, g)], I) for g in d.SPLAT_HEAD]
anims["splat_pave"] = [cell(16, 16, [(0, 8, g)], I) for g in d.SPLAT_PAVE]
anims["bounce"] = [cell(16, 16, [(0, 8, g)], I) for g in d.BOUNCE]
anims["shoe"] = [cell(16, 16, [(0, 0, g)], I) for g in d.SHOE]
anims["berry"] = [cell(16, 16, [(0, 0, d.BERRY)], I), cell(16, 16, [(0, 0, d.BERRY), (11, 0, d.SPARK)], I)]
fixed["poop"] = [s5(c) for c in I.values()]

W, x, y, rowh = 512, 0, 0, 0
rects, placed = {}, []
for name, frames in anims.items():
    rects[name] = []
    for im in frames:
        if x + im.width > W: x, y, rowh = 0, y + rowh, 0
        rects[name].append(dict(x=x, y=y, w=im.width, h=im.height)); placed.append((im, x, y))
        x += im.width; rowh = max(rowh, im.height)
sheet = Image.new("RGBA", (W, y + rowh), (0, 0, 0, 0))
for im, px_, py_ in placed: sheet.paste(im, (px_, py_))
sheet.save(f"{ROOT}/assets/poop/poop_sheet.png")
# umbrella palettes: one fixed red set per walker type is wasteful, so only the hat set is shipped as palette and the other types share it by subset
meta = {"source": "thoughts/shared/drafts/2026-11-20-poop-the-man-v2/draw_poop_the_man.py hand-typed grids", "palette_policy": "subset",
        "palettes": {k: [list(c) for c in v] for k, v in fixed.items()}, "extra_palettes": extra, "animations": rects}
json.dump(meta, open(f"{ROOT}/assets/poop/poop_sheet.json", "w"), indent=1)
print({k: len(v) for k, v in rects.items()}, sheet.size)
