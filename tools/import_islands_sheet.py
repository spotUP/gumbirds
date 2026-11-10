#!/usr/bin/env python3
"""Import one look of the floating islands (thin variant) into assets/islands/island_sheet.png + .json.
Run: /opt/homebrew/bin/python3.14 -I tools/import_islands_sheet.py [moon] [--out <dir>]   then `gmake`.

Source: assets/islands/draw_islands_final.py (the final island drawing, copied from thoughts/shared/drafts/2026-11-10-islands-final)
and assets/islands/sheet_<look>_1x.png (its frame 0 sheet; the importer asserts the pieces it draws equal that sheet, and that the
palette equals the look table in assets/islands/numbers.txt). Only the thin variant (one tile tall) is imported.
An island is a row of 16 px pieces: left cap, middles, right cap. The sheet holds each piece once; a piece whose tile changes
over the 8 animation frames (the shimmer) is a hardware auto-animation group of 8 frames, the others are one frame. The sprite
pipeline places every group on 8 consecutive tiles starting at a multiple of 8 (a look with fewer distinct frames, the garden
has 3, still takes all 8 slots). All the game needs about the layout is emitted as json "tables" and reaches C as ISLAND_TABLE_*
in build/gen/island_tables.h. A second look is a LOOKS entry, not new code: the ROM carries one look's sheet at a time.
Same shape as tools/import_bg_sheet.py (moods, snapped palette, json writer).
"""
import argparse, importlib.util, json, os, re, sys
sys.dont_write_bytecode = True
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "assets/islands")
TRANSP = (255, 0, 255)
PIECE = 16
STEP_FRAMES = 7  # hardware frames per animation step: 110 ms x 59.19 Hz = 6.51, rounded to 7 (plan 2026-11-10-islands-build-plan.md I8)
# mood (as in tools/import_bg_sheet.py MOODS) -> look of the island drawing. Only moon is in the game today.
LOOKS = {"moon": "roof", "dusk": "garden", "storm": "deck"}
PIECES = ["L", "0", "1", "2", "3", "4", "R"]  # sheet row order; middles are the draw script's m0..m4
NAMES = ["left", "m0", "m1", "m2", "m3", "m4", "right"]


def load_draw():
    spec = importlib.util.spec_from_file_location("draw_islands_final", os.path.join(SRC, "draw_islands_final.py"))
    d = importlib.util.module_from_spec(spec)
    sys.modules["draw_islands_final"] = d
    spec.loader.exec_module(d)
    return d


def numbers_palette(look_title):
    """The look table of numbers.txt: list of (r, g, b), index 1 first."""
    lines = open(os.path.join(SRC, "numbers.txt")).read().split("\n")
    i = next(n for n, l in enumerate(lines) if l.strip().endswith(look_title))
    out = []
    for l in lines[i + 1:]:
        m = re.match(r"\s+(\d+) \w+\s+(\d+),\s*(\d+),\s*(\d+)\s+luminance", l)
        if m:
            out.append(tuple(int(v) for v in m.groups()[1:]))
        elif out:
            break
    return out


def pieces_of(d, look):
    """{piece key: [rgb array per frame]} for the 7 thin pieces; arrays are 16x16x3."""
    return {k: [d.to_rgb(d.piece(look, k if k in "LR" else int(k), 1, f), look) for f in range(d.FRAMES)] for k in PIECES}


def build(mood, out):
    d = load_draw()
    look = LOOKS[mood]
    pal = d.pal_rgb(look)
    assert pal == numbers_palette(d.LOOKS[look]["title"]), "palette differs from numbers.txt"
    assert len(pal) == 15 and len(set(pal)) == 15
    pcs = pieces_of(d, look)
    # frame 0 of the drawing equals the committed sheet (thin row of each width)
    sheet0 = np.array(Image.open(os.path.join(SRC, "sheet_%s_1x.png" % look)).convert("RGB"))
    for i, w in enumerate(d.WIDTHS):
        want = d.to_rgb(d.island(look, w, 1, 0), look)
        assert (sheet0[48 * i + 32:48 * i + 48, :w] == want).all(), "frame 0 of %s width %d differs from its sheet" % (look, w)
    swap = [int(any((pcs[k][f] != pcs[k][0]).any() for f in range(1, d.FRAMES))) for k in PIECES]
    rows = [(NAMES[n], [pcs[k][f] for f in range(d.FRAMES)] if swap[n] else [pcs[k][0]]) for n, k in enumerate(PIECES)]
    sheet = Image.new("RGBA", (PIECE * d.FRAMES, PIECE * len(rows)), (0, 0, 0, 0))
    anims = {}
    for r, (name, frs) in enumerate(rows):
        anims[name] = []
        for f, a in enumerate(frs):
            rgba = np.zeros((PIECE, PIECE, 4), np.uint8)
            opaque = ~(a == np.array(TRANSP, np.uint8)).all(2)
            rgba[opaque, :3] = a[opaque]
            rgba[opaque, 3] = 255
            sheet.paste(Image.fromarray(rgba, "RGBA"), (f * PIECE, r * PIECE))
            anims[name].append({"x": f * PIECE, "y": r * PIECE, "w": PIECE, "h": PIECE})
    os.makedirs(out, exist_ok=True)
    sheet.save(os.path.join(out, "island_sheet.png"))
    seq = []
    for w in d.WIDTHS:
        seq.append([0] + [1 + m for m in d.SEQ[w]] + [6])  # anim indices: left, m0..m4, right
    meta = {
        "source": "tools/import_islands_sheet.py %s: look %s (%s), thin pieces of assets/islands/draw_islands_final.py" % (mood, look, d.LOOKS[look]["title"]),
        "look": look,
        "mood": mood,
        "palette_policy": "merge",
        "groups": {NAMES[n]: d.FRAMES for n in range(len(PIECES)) if swap[n]},
        "animations": anims,
        "defines": {"STEP_FRAMES": STEP_FRAMES, "LINE_ROW": d.LINE, "PIECE_W": PIECE, "WIDTH_COUNT": len(d.WIDTHS)},
        "tables": {
            "width": list(d.WIDTHS),
            "piece_count": [len(s) for s in seq],
            "pieces": [a for s in seq for a in s],  # per width back to back: anim index of each piece, left to right
            "swap": swap,  # per anim: 1 = auto-animated group of 8 tiles
        },
    }
    json.dump(meta, open(os.path.join(out, "island_sheet.json"), "w"), indent=1)
    return look, swap


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mood", nargs="?", default="moon", choices=sorted(LOOKS))
    ap.add_argument("--out", default=SRC)
    a = ap.parse_args()
    look, swap = build(a.mood, a.out)
    print("imported mood %s: look %s, %d pieces, swapping: %s" % (a.mood, look, len(PIECES), ", ".join(n for n, s in zip(NAMES, swap) if s)))


if __name__ == "__main__":
    main()
