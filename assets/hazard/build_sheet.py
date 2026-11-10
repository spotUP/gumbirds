#!/usr/bin/env python3
"""Hazard sheet for the sprite pipeline: assets/hazard/frames_<name>_1x.png -> hazard_sheet.png + hazard_sheet.json.
Run: /opt/homebrew/bin/python3.14 -I assets/hazard/build_sheet.py   (the sheet and json are committed, like assets/city)

Each frames_ PNG holds 16 frames of 64 x 32 px per row; one row per tile variant (spikes, water: 1 variant;
fire: 3 variants A B C, lava: 2 variants A B; groups of 4 sprite columns cycle the variants: fire A B C A B (192 px period), lava A B A B A). The hardware auto-animation covers 8 frames, so every
variant row becomes two 8-frame groups, bank 0 (frames 0..7) and bank 1 (frames 8..15), one sheet row each
(tools/sprite_pipeline.py "groups"). Data the game reads (variant count, speed, first animation index per hazard)
comes out as "tables" in hazard_sprites.h, so a variant is a change of the frames PNG only.
"""
import json, os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
FW, FH, GROUP = 64, 32, 8
# (name, frames per auto-animation step). Order = rotation order, one hazard per match.
HAZARDS = [("spikes", 4), ("fire", 4), ("water", 6), ("lava", 8)]
VARIANT_LETTERS = "abcdefgh"

def q5(v):
    """Nearest Neo Geo colour step (5 bits per channel, expanded to 8 as tools/sprite_pipeline.py expand5): the draft
    palettes are 8-bit values, the hardware has 32 levels, so the build rounds here and the sheet is what ships."""
    f = round(v * 31 / 255)
    return (f << 3) | (f >> 2)


rows, anims, variants, first_anim = [], {}, [], []
for name, _ in HAZARDS:
    im = Image.open(os.path.join(HERE, "frames_%s_1x.png" % name)).convert("RGBA")
    lut = [q5(v) for v in range(256)]
    r, g, b, a = im.split()
    im = Image.merge("RGBA", (r.point(lut), g.point(lut), b.point(lut), a))
    assert im.size[0] == 16 * FW and im.size[1] % FH == 0, (name, im.size)
    nv = im.size[1] // FH
    variants.append(nv)
    first_anim.append(len(anims))
    for v in range(nv):
        for bank in range(2):
            row = im.crop((bank * GROUP * FW, v * FH, (bank + 1) * GROUP * FW, (v + 1) * FH))
            y = len(rows) * FH
            rows.append(row)
            anims["%s_%s_%d" % (name, VARIANT_LETTERS[v], bank)] = [
                {"x": k * FW, "y": y, "w": FW, "h": FH} for k in range(GROUP)]
sheet = Image.new("RGBA", (GROUP * FW, len(rows) * FH), (0, 0, 0, 0))
for i, r in enumerate(rows):
    sheet.paste(r, (0, i * FH))
sheet.save(os.path.join(HERE, "hazard_sheet.png"))
meta = {
    "source": "assets/hazard/frames_<name>_1x.png (final hazard set, thoughts/shared/drafts/2026-11-10-hazards-final), cut by assets/hazard/build_sheet.py",
    "palette_policy": "merge",
    "groups": {a: GROUP for a in anims},
    "tables": {"variants": variants, "step_frames": [s for _, s in HAZARDS], "first_anim": first_anim},
    "animations": anims,
}
json.dump(meta, open(os.path.join(HERE, "hazard_sheet.json"), "w"), indent=1)
print("hazard sheet: %d groups, variants %s" % (len(anims), variants))
