#!/usr/bin/env python3
"""Flier art import: one draft sheet PNG -> assets/flier/sootling_sheet.png (the repo source sheet).
Usage: $PYTHON -I tools/import_flier_sheet.py DRAFT_SHEET.png     (e.g. thoughts/shared/drafts/2026-11-10-flier/A_v4_sheet_1x.png)
Swapping the art is this one step, then `make`: the draft must keep the draft layout
(gen_v4.py sheet()): 7 frames per row at x = 2 + 20 * i, row 0 (player palette) at y = 2, row 1
(computer palette) at y = 38, each frame a 16x32 slot, feet on row 31; frame order glide2, up2, down2,
glide1, up1, glide0, fall. The draft background colours are keyed to transparent and every colour is
snapped to the 5-bit-per-channel grid the Neo Geo palette can hold (build fails on a collision).
Output sheet: 7 x 16 by 2 x 32 px, frame i of row r at (16 i, 32 r); assets/flier/sootling_sheet.json
(committed, not generated) lists those rects as the animations "player" and "cpu"."""
import os, sys
from PIL import Image

FRAMES, SLOT_W, SLOT_H, PITCH, X0, Y0, ROW_PITCH = 7, 16, 32, 20, 2, 2, 36
BACKGROUND = {(36, 40, 50), (26, 29, 36)}
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "flier", "sootling_sheet.png")


def snap5(v):
    f = round(v * 31 / 255)
    return (f << 3) | (f >> 2)


def main():
    src = Image.open(sys.argv[1]).convert("RGBA")
    need = (X0 + (FRAMES - 1) * PITCH + SLOT_W, Y0 + ROW_PITCH + SLOT_H)
    if src.width < need[0] or src.height < need[1]:
        sys.exit("[ERROR] draft sheet %s is smaller than the draft layout %s" % (src.size, need))
    sp = src.load()
    out = Image.new("RGBA", (FRAMES * SLOT_W, 2 * SLOT_H), (0, 0, 0, 0))
    op = out.load()
    seen = {}
    for r in range(2):
        for i in range(FRAMES):
            for y in range(SLOT_H):
                for x in range(SLOT_W):
                    p = sp[X0 + i * PITCH + x, Y0 + r * ROW_PITCH + y]
                    if p[3] == 0 or p[:3] in BACKGROUND:
                        continue
                    c = tuple(snap5(v) for v in p[:3])
                    if seen.setdefault(c, p[:3]) != p[:3]:
                        sys.exit("[ERROR] colours %s and %s collide after 5-bit snap" % (seen[c], p[:3]))
                    op[i * SLOT_W + x, r * SLOT_H + y] = c + (255,)
    out.save(OUT)
    print("[OK] wrote %s: %d colours" % (os.path.normpath(OUT), len(seen)))


if __name__ == "__main__":
    main()
