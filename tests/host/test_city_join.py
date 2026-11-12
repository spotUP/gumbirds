#!/usr/bin/env python3
"""Join continuity of the looping background planes. Run: $PYTHON -I tests/host/test_city_join.py [sheet.png sheet.json]
A looping plane of width W shows column W-1 right next to column 0 once per lap, so the pixel columns on both sides of that seam
must read like any two neighbouring pixel columns of the same plane. For the moving planes (far, mid A, mid B, near) and every
screen line: the number of lines where only one side is opaque (silhouette step) and the mean colour step over the lines opaque
on both sides (sum of absolute RGB differences) must not exceed the worst value between two neighbouring pixel columns inside the
same plane (colour step with a 10 percent tolerance). Reads the sheet the
ROM is built from (assets/city/city_sheet.png and .json) unless two paths are given."""
import json, os, sys
sys.dont_write_bytecode = True
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PNG = sys.argv[1] if len(sys.argv) > 2 else os.path.join(ROOT, "assets/city/city_sheet.png")
JSON = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "assets/city/city_sheet.json")
FAILS = []


def check(ok, msg):
    print(("[OK] " if ok else "[FAIL] ") + msg)
    if not ok:
        FAILS.append(msg)


TOLERANCE = 1.10  # pixel art has hard building edges between neighbouring columns too: the seam may exceed the inner worst by 10 percent


def pair(px, xa, xb, y0, h):
    """(mean RGB distance over the lines opaque on both sides, lines where exactly one side is opaque) for two pixel columns."""
    total = both = holes = 0
    for y in range(y0, y0 + h):
        a, b = px[xa, y], px[xb, y]
        if (a[3] > 0) != (b[3] > 0):
            holes += 1
        elif a[3] > 0:
            total += sum(abs(a[i] - b[i]) for i in range(3))
            both += 1
    return (total / both if both else 0.0), holes


def plane_join(px, rect):
    """(worst mean step and worst hole count between inner neighbours, the same across the seam)."""
    x0, y0, w, h = rect["x"], rect["y"], rect["w"], rect["h"]
    inner = [pair(px, x0 + x, x0 + x + 1, y0, h) for x in range(w - 1)]
    return (max(i[0] for i in inner), max(i[1] for i in inner)), pair(px, x0 + w - 1, x0, y0, h)


def main():
    sheet = Image.open(PNG).convert("RGBA")
    px = sheet.load()
    anims = json.load(open(JSON))["animations"]
    for name in ("far", "midA", "midB", "near"):
        rect = anims[name][0]
        (inner_step, inner_holes), (seam_step, seam_holes) = plane_join(px, rect)
        check(seam_step <= inner_step * TOLERANCE and seam_holes <= inner_holes,
              "%s plane join: column %d next to column 0, seam step %.1f (inner worst %.1f, limit x%.2f), seam silhouette lines %d (inner worst %d)"
              % (name, rect["w"] - 1, seam_step, inner_step, TOLERANCE, seam_holes, inner_holes))
    print("[OK] city join checks passed" if not FAILS else "[FAIL] city join: %d failures" % len(FAILS))
    return 1 if FAILS else 0


sys.exit(main())
