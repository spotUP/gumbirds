#!/usr/bin/env python3
"""Splash sprite set: assets/splash/splash_{water,lava}_1x.png (+ splash.json) -> build/gen/splash.c1/.c2, splash_sprites.h/.c.
Usage: $PYTHON -I tools/build_splash_sprites.py [--out build/gen] [--no-verify]
Stacks the two 576 x 48 strips into one sheet (water y 0, lava y 48) and hands it to tools/sprite_pipeline.py: animations water, lava."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sprite_pipeline
from PIL import Image

def compose(out):
    meta = json.load(open("assets/splash/splash.json"))
    fw, fh, n = meta["frame_w"], meta["frame_h"], meta["frames"]
    names = ["water", "lava"]
    sheet = Image.new("RGBA", (fw * n, fh * len(names)), (0, 0, 0, 0))
    anims = {}
    for row, name in enumerate(names):
        im = Image.open("assets/splash/splash_%s_1x.png" % name).convert("RGBA")
        # The strips carry 8-bit colours; the pipeline wants 5-bit expanded ones (the hazard sheet's palette): snap each channel.
        im.putdata([tuple(sprite_pipeline.expand5(sprite_pipeline.to5(v)) for v in p[:3]) + (p[3],) if p[3] else p for p in im.getdata()])
        sheet.paste(im, (0, row * fh))
        anims[name] = [{"x": i * fw, "y": row * fh, "w": fw, "h": fh} for i in range(n)]
    os.makedirs(out, exist_ok=True)
    sp, mp = os.path.join(out, "splash_sheet.png"), os.path.join(out, "splash_sheet.json")
    sheet.save(sp)
    json.dump({"animations": anims}, open(mp, "w"))
    return sp, mp

if __name__ == "__main__":
    out = "build/gen"
    if "--out" in sys.argv: out = sys.argv[sys.argv.index("--out") + 1]
    sp, mp = compose(out)
    sys.argv += ["--sheet", sp, "--meta", mp]
    sprite_pipeline.main("splash", sp, mp)
