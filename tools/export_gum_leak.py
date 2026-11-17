#!/usr/bin/env python3
"""Export the owner-picked leak (variant W: hole stamp + 32x16 air jet) to assets/gum_leak/.
Reads the hand-pixeled draft grids (thoughts/shared/drafts/2026-11-17-gum-leak-air) and writes the sheet png, json and the
per level / wobble anchor tables (tile origin relative to the gum sheet cell). No art is generated here.
Air pixels (letters a, c) are remapped to b (white): the hot cue palette turns a and c yellow-orange. Hole pixels keep their letters.
Usage: python3.14 -I tools/export_gum_leak.py [--drafts DIR]"""
import json, os, sys
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = sys.argv[sys.argv.index("--drafts") + 1] if "--drafts" in sys.argv else "/Users/spot/Code/ArcadeGame/thoughts/shared/drafts"
sys.path.insert(0, os.path.join(d, "2026-11-17-gum-leak-air"))
import draw_gum_leak_air as air
r1, r2, v1 = air.r1, air.r2, air.v4.v1
FR = air.VAR["W"]["n"]
gum = json.load(open(os.path.join(ROOT, "assets/gum/gum_sheet.json")))
sheet = Image.open(os.path.join(ROOT, "assets/gum/gum_sheet.png")).convert("RGBA")
out = Image.new("RGBA", (32 * FR, 16), (0, 0, 0, 0))
for f in range(FR):
    full, hole = air.tile("W", f), air.tile("W", f, hole_only=True)
    grid = ["".join(hc if hc != "." else ("b" if fc in "ac" else fc) for fc, hc in zip(fr, hr)) for fr, hr in zip(full, hole)]
    out.alpha_composite(r1.paint(grid), (32 * f, 0))
dx, dy = [], []
for lv in range(16, 0, -1):
    for w in range(6):
        b = v1.bubble(lv, w, "p1"); rx, ry = r2.rim(b, r2.SHOWN[16 - lv])
        c = gum["animations"]["level%d" % lv][w]
        bb = sheet.crop((c["x"], c["y"], c["x"] + c["w"], c["y"] + c["h"])).getbbox()
        dx.append(bb[0] + rx - 6); dy.append(bb[1] + ry - 11)
out.save(os.path.join(ROOT, "assets/gum_leak/gum_leak_sheet.png"))
meta = {"source": "tools/export_gum_leak.py from thoughts/shared/drafts/2026-11-17-gum-leak-air (variant W, owner-picked)",
        "animations": {"leak": [{"x": 32 * i, "y": 0, "w": 32, "h": 16} for i in range(FR)]},
        "palettes": {"leak": gum["palettes"]["level16"]},
        "defines": {"LEAK_FRAMES": FR, "LEAK_TICK": r2.TICK},
        "tables": {"anchor_dx": dx, "anchor_dy": dy}}
json.dump(meta, open(os.path.join(ROOT, "assets/gum_leak/gum_leak_sheet.json"), "w"), indent=1)
print("[OK] frames=%d anchors=%d dx %d..%d dy %d..%d" % (FR, len(dx), min(dx), max(dx), min(dy), max(dy)))
