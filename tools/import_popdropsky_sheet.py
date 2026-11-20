#!/usr/bin/env python3
"""Cut the approved Pop Drop summer sky (draft v3 take B, 2026-11-20) into assets/popdropsky/popdropsky_sheet.png + .json
(input of tools/build_popdropsky_sprites.py).
Usage: python3.14 -I tools/import_popdropsky_sheet.py [DRAFTS_DIR]   (DRAFTS_DIR default thoughts/shared/drafts)
Every pixel comes from the hand-typed grids and line strips of the drafts (imported, their main() is not run): the sky is v3
rows_v3("b_postcard") (one flat colour per line, 13 blues), the clouds are v1 cloud_img(). This file only lays the frames out.
Colours are re-snapped to the 5 bit values the pipeline accepts. Each cloud frame is one tile tall with the cloud on its top row:
the game moves the whole frame by whole pixels in y, so the cloud may sit on any line. Tables (see sprite_pipeline "tables"):
CX = left of the frame's first tile (16 multiple, may be negative), CY = cloud y inside its layer period, CL = layer."""
import importlib.util, json, os, sys
sys.dont_write_bytecode = True
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DR = sys.argv[1] if len(sys.argv) > 1 else f"{ROOT}/thoughts/shared/drafts"


def load(name, rel):
    s = importlib.util.spec_from_file_location(name, f"{DR}/{rel}")
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


v3 = load("v3", "2026-11-20-popdrop-sky-v3/draw_sky.py")
m = v3.m
T = m.TAKES["b_postcard"]


def n5(c):  # 8 bit -> the 5 bit value the pipeline round-trips: (f << 3) | (f >> 2)
    f = round(c * 31 / 255); return (f << 3) | (f >> 2)


def q(c): return tuple(n5(v) for v in c)


rows = [q(c) for c in v3.rows_v3("b_postcard")]
sky_cols = list(dict.fromkeys(rows))
sky = Image.new("RGBA", (m.W, m.H))
for y, c in enumerate(rows): sky.paste(c + (255,), (0, y, m.W, y + 1))

anims = {"sky": [sky]}
pals = {"sky": sky_cols}
tables = {"CX": [], "CY": [], "CL": []}
for li, (per, spd, pal, items) in enumerate(T["layers"]):
    p = [q(c) for c in T["pals"][pal]]
    pals[pal] = list(dict.fromkeys(p))
    anims[pal] = []
    for name, x, y, fl in items:
        cl = m.cloud_img(name, p, fl)
        ox = x % 16
        assert cl.height <= 16
        im = Image.new("RGBA", (-(-(ox + cl.width) // 16) * 16, 16), (0, 0, 0, 0)); im.paste(cl, (ox, 0))
        anims[pal].append(im)
        tables["CX"].append(x - ox); tables["CY"].append(y); tables["CL"].append(li)

W = 400; x = y = rowh = 0; rects = {}; placed = []
for name, frames in anims.items():
    rects[name] = []
    for im in frames:
        if x + im.width > W: x, y, rowh = 0, y + rowh, 0
        rects[name].append(dict(x=x, y=y, w=im.width, h=im.height)); placed.append((im, x, y))
        x += im.width; rowh = max(rowh, im.height)
sheet = Image.new("RGBA", (W, y + rowh), (0, 0, 0, 0))
for im, px, py in placed: sheet.paste(im, (px, py))
sheet.save(f"{ROOT}/assets/popdropsky/popdropsky_sheet.png")
meta = {"source": "thoughts/shared/drafts/2026-11-20-popdrop-sky-v3 (take B) and -popdrop-sky (clouds), hand-typed",
        "palette_policy": "subset", "palettes": {k: [list(c) for c in v] for k, v in pals.items()}, "animations": rects,
        "defines": {"clouds": len(tables["CX"])}, "tables": tables,
        "layers": [[per, spd] for per, spd, _, _ in T["layers"]]}
json.dump(meta, open(f"{ROOT}/assets/popdropsky/popdropsky_sheet.json", "w"), indent=1)
print({k: len(v) for k, v in rects.items()}, sheet.size, len(sky_cols), "sky colours", tables)
