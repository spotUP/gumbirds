#!/usr/bin/env python3
"""Copy the approved garden and deck island sheets from the 2026-11-13 look drafts to assets/islands/island_<look>_sheet.png/.json
and check them against the roof sheet (same pieces, one 15 colour palette), printing tile counts.
Run: /opt/homebrew/bin/python3.14 -I tools/stage_island_looks.py [--scratch <dir>]   (--scratch also runs the sprite pipeline per look)"""
import json, os, shutil, subprocess, sys
sys.dont_write_bytecode = True
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRAFT = os.path.join(ROOT, "thoughts/spot/drafts/2026-11-13-island-looks")
OUT = os.path.join(ROOT, "assets/islands")
ROOF = (os.path.join(OUT, "island_sheet.png"), os.path.join(OUT, "island_sheet.json"))


def tiles(png):
    a = np.array(Image.open(png).convert("RGBA"))
    return {a[y:y + 16, x:x + 16].tobytes() for y in range(0, a.shape[0], 16) for x in range(0, a.shape[1], 16) if a[y:y + 16, x:x + 16, 3].any()}


def colours(png):
    a = np.array(Image.open(png).convert("RGBA"))
    return {tuple(p[:3]) for p in a.reshape(-1, 4) if p[3]}


def main():
    scratch = sys.argv[sys.argv.index("--scratch") + 1] if "--scratch" in sys.argv else None
    roof_meta = json.load(open(ROOF[1]))
    roof_img = Image.open(ROOF[0])
    roof_tiles = tiles(ROOF[0])
    print("roof: size %s colours %d unique tiles %d" % (roof_img.size, len(colours(ROOF[0])), len(roof_tiles)))
    for look in ("garden", "deck"):
        sp, sj = [os.path.join(DRAFT, look, "island_sheet" + e) for e in (".png", ".json")]
        dp, dj = [os.path.join(OUT, "island_%s_sheet%s" % (look, e)) for e in (".png", ".json")]
        meta = json.load(open(sj))
        assert Image.open(sp).size == roof_img.size, "sheet size"
        for k in ("animations", "groups", "tables"):
            assert meta[k] == roof_meta[k], "%s differs from roof" % k
        assert meta["look"] == look
        shutil.copyfile(sp, dp)
        meta["source"] = "tools/stage_island_looks.py: look %s from thoughts/spot/drafts/2026-11-13-island-looks/draw_island_looks.py" % look
        json.dump(meta, open(dj, "w"), indent=1)
        open(dj, "a").write("\n")
        t, c = tiles(dp), colours(dp)
        assert len(c) <= 15
        print("%s: pieces %d colours %d unique tiles %d new against roof %d" % (look, sum(map(len, meta["animations"].values())), len(c), len(t), len(t - roof_tiles)))
        if scratch:
            r = subprocess.run([sys.executable, "-I", "-c", "import sys; sys.path.insert(0,'tools'); import sprite_pipeline; sprite_pipeline.main('island_%s','%s','%s')" % (look, dp, dj),
                                "--out", os.path.join(scratch, look)], cwd=ROOT, capture_output=True, text=True)
            print(r.stdout[-600:], r.stderr[-600:])


main()
