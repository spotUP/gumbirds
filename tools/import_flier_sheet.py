#!/usr/bin/env python3
"""Flier art import: a final sheet + its frames.json -> assets/flier/sootling_sheet.png and .json (the repo source).
Usage: $PYTHON -I tools/import_flier_sheet.py DRAFT_DIR/frames.json
    (e.g. thoughts/shared/drafts/2026-11-10-sootling-final/frames.json; then `make`)
Input contract (frames.json of the sootling-final draft): "sheet" names an indexed PNG next to it, frames in
row-major order on a sheet_cols grid of frame_w x frame_h slots, index 0 transparent, indices 1..15 colour keys of
"palette_player" and "palette_cpu" (15 RGB entries each, already on the Neo Geo 5-bit grid), "animations" with
first / count / ticks (60 Hz) / loop per clip, "feet_row", "hit_box_columns".
Output sheet: the same grid twice, player palette in rows 0..R-1, computer palette (same indices, other colours) in
rows R..2R-1, so the build sees two animations "player" and "cpu" of N frames each. Because the indices match, the
build dedups the tile data of both palettes. The json written next to it carries: the frame rects, the two palettes in
index order ("palettes", so the build keeps index = draft index), the frame size, hit box offset and clip table as
"defines" / "tables" (emitted by tools/sprite_pipeline.py into build/gen/sootling_tables.h; src/main.c, the view
logic src/core/flier_view.c and tests/mame/camera_probe.c read the numbers from there, never retyped)."""
import json, os, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "..", "assets", "flier")


def snapped(c):
    for v in c:
        f = round(v * 31 / 255)
        if ((f << 3) | (f >> 2)) != v:
            sys.exit("[ERROR] colour %s is not on the 5-bit grid" % (c,))
    return tuple(c)


def main():
    meta_path = sys.argv[1]
    d = json.load(open(meta_path))
    src = Image.open(os.path.join(os.path.dirname(os.path.abspath(meta_path)), d["sheet"]))
    if src.mode != "P":
        sys.exit("[ERROR] %s must be an indexed PNG" % d["sheet"])
    fw, fh, cols, rows = d["frame_w"], d["frame_h"], d["sheet_cols"], d["sheet_rows"]
    total = sum(a["count"] for a in d["animations"])
    if src.size != (cols * fw, rows * fh) or total > cols * rows:
        sys.exit("[ERROR] sheet %s does not match %dx%d slots of %dx%d" % (src.size, cols, rows, fw, fh))
    grid_rows = -(-total // cols)
    pals = {"player": [snapped(c) for c in d["palette_player"]], "cpu": [snapped(c) for c in d["palette_cpu"]]}
    for k, p in pals.items():
        if len(set(p)) != len(p):
            sys.exit("[ERROR] palette %s has duplicate colours" % k)
    out = Image.new("RGBA", (cols * fw, 2 * grid_rows * fh), (0, 0, 0, 0))
    sp, op = src.load(), out.load()
    used = set()
    for n in range(total):
        sx, sy = (n % cols) * fw, (n // cols) * fh
        for y in range(fh):
            for x in range(fw):
                i = sp[sx + x, sy + y]
                if i == 0:
                    continue
                used.add(i)
                for r, key in enumerate(("player", "cpu")):
                    op[sx + x, sy + y + r * grid_rows * fh] = pals[key][i - 1] + (255,)
    rects = {key: [dict(x=(n % cols) * fw, y=(n // cols) * fh + r * grid_rows * fh, w=fw, h=fh) for n in range(total)]
             for r, key in enumerate(("player", "cpu"))}
    clips = d["animations"]
    ticks = [t for a in clips for t in a["ticks"]]
    defines = {"ART_W": fw, "ART_H": fh, "FEET_ROW": d["feet_row"], "BOX_FIRST_COL": d["hit_box_columns"][0],
               "BOX_LAST_COL": d["hit_box_columns"][1], "CLIP_COUNT": len(clips), "FRAMES": total, "TICK_HZ": d["tick_hz"]}
    for n, a in enumerate(clips):
        defines["CLIP_" + a["name"].upper()] = n
    meta = {
        "source": "%s, imported by tools/import_flier_sheet.py (do not edit; re-import)" % os.path.relpath(meta_path),
        "animations": rects,
        "palettes": {k: [list(c) for c in p] for k, p in pals.items()},
        "defines": defines,
        "tables": {"clip_first": [a["first"] for a in clips], "clip_count": [a["count"] for a in clips],
                   "clip_loop": [1 if a["loop"] else 0 for a in clips], "frame_ticks": ticks},
    }
    for a in clips:
        if len(a["ticks"]) != a["count"]:
            sys.exit("[ERROR] clip %s: %d ticks for %d frames" % (a["name"], len(a["ticks"]), a["count"]))
    out.save(os.path.join(OUT_DIR, "sootling_sheet.png"))
    with open(os.path.join(OUT_DIR, "sootling_sheet.json"), "w") as f:
        json.dump(meta, f, indent=1)
        f.write("\n")
    print("[OK] wrote assets/flier/sootling_sheet.png/.json: %d frames of %dx%d, %d clips, %d palette indices used"
          % (total, fw, fh, len(clips), len(used)))


if __name__ == "__main__":
    main()
