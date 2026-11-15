#!/usr/bin/env python3
"""One-shot import of the approved trip cave art (thoughts/shared/drafts/2026-11-15-trip-cave-v3, take 1 slate roof, floor F1 lip,
eased S16/S32 curves) into assets/tripstrip/tripstrip_sheet.png + .json. Run by hand once; the build only reads the sheet.

The draft's own assembly code (build_cave3.py up to its height measuring section) is executed unchanged, so the pixels are the
drawn ones: no redraw. The sheet holds, in this animation order (palette 0 = gum floor, palette 1 = slate roof, merge policy):
  fill                 the shipped gum fill tile
  lip0..lip3           8-frame auto-animation groups: frame f = shipped t2_rim body frame (k + f) & 7 with F1 lip part k on rows 2-3
  floor_s16, floor_s32 8-frame groups of the rising floor curves (48x32, 48x48), the shipped fill composited under the band
  roof                 one animation so the slate shares one palette; frames: fill 64x16 (4 tiles), rim A 64x16, rim B 64x16,
                       solo 32x16 (2 tiles), falling curve S16 48x32, S32 48x48
  black                one palette-black tile (deep rows of both strips)
Usage: python3 tools/import_trip_cave.py [--draft DIR]"""
import argparse, json, os, sys
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser()
ap.add_argument("--draft", default=os.path.join(ROOT, "thoughts/shared/drafts/2026-11-15-trip-cave-v3"))
a = ap.parse_args()
src = open(os.path.join(a.draft, "build_cave3.py")).read()
cut = src.index("# ---------------------------------------------------------------- measured height")
ns = {"__file__": os.path.join(a.draft, "build_cave3.py"), "__name__": "cave3_import"}
exec(compile(src[:cut], "build_cave3.py", "exec"), ns)

old = json.load(open(os.path.join(ns["R"], "assets/tripstrip/tripstrip_sheet.json")))   # the shipped sheet, as the draft read it
sheet = ns["sheet"]
t2 = old["animations"]["t2_rim"]
lip = ns["img"](ns["V2"].F1_LIP_ROWS, ns["GUM"])

anims, groups, place = {}, {}, []   # place: (image, x, y)
y = 0
def put(name, frames, group=None):
    global y
    rects, x = [], 0
    for im in frames:
        place.append((im, x, y)); rects.append({"x": x, "y": y, "w": im.width, "h": im.height}); x += im.width
    anims[name] = rects
    if group: groups[name] = group
    y += max(im.height for im in frames)

put("fill", [ns["ffill"]])
for k in range(4):
    fr = []
    for f in range(8):
        r = t2[(k + f) & 7]
        t = sheet.crop((r["x"], r["y"], r["x"] + 16, r["y"] + 16)).copy()
        t.paste((0, 0, 0, 0), (0, 0, 16, 4))
        t.paste(lip.crop((16 * k, 0, 16 * k + 16, 2)), (0, 2))
        fr.append(t)
    put("lip%d" % k, fr, 8)
put("floor_s16", ns["floor16"], 8)
put("floor_s32", ns["floor32"], 8)
solo = Image.new("RGBA", (32, 16), (0, 0, 0, 0)); solo.alpha_composite(ns["solo"][0], (0, 0)); solo.alpha_composite(ns["solo"][1], (16, 0))
put("roof", [ns["fillI"], ns["rimA"], ns["rimB"], solo, ns["roof16"], ns["roof32"]])   # one animation = one palette (slot 1)
put("black", [Image.new("RGBA", (16, 16), (0, 0, 0, 255))])

w = max(x + im.width for im, x, _ in place)
out = Image.new("RGBA", (w, y), (0, 0, 0, 0))
for im, x, yy in place: out.alpha_composite(im, (x, yy))
out.save(os.path.join(ROOT, "assets/tripstrip/tripstrip_sheet.png"))
meta = {
    "source": "thoughts/shared/drafts/2026-11-15-trip-cave-v3 (take 1 slate roof, F1 lip, S16/S32 curves), assembled by tools/import_trip_cave.py",
    "palette_policy": "merge",
    "groups": groups,
    "defines": {"STEP_TICKS": old["defines"]["STEP_TICKS"], "LOOP_FRAMES": 8},
    "animations": anims,
}
json.dump(meta, open(os.path.join(ROOT, "assets/tripstrip/tripstrip_sheet.json"), "w"), indent=1)
print("[OK] sheet %dx%d, %d animations" % (w, y, len(anims)))
