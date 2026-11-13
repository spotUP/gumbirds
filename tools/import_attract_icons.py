#!/usr/bin/env python3
"""Attract how-to-play icons: draft folder -> assets/attract/attract_icons.png + attract_icons.json.
Usage: python3.14 -I tools/import_attract_icons.py [--draft DIR] [--out DIR]
Tiles are deduplicated in first-seen order (frames in icons.json order, row-major); all-transparent cells are the blank
marker (-1), not a tile. The PNG is a palette image, 16 tiles per row; palette entry 0 is transparent, 1.. follow icons.json.
Self-check: every frame is rebuilt from the tiles and compared pixel for pixel with the draft sheet."""
import argparse, json, os, sys
sys.dont_write_bytecode = True
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sprite_pipeline as sp
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T, BLANK, PER_ROW = 8, -1, 16


def build(draft):
    meta = json.load(open(os.path.join(draft, "icons.json")))
    sheet = np.array(Image.open(os.path.join(draft, meta["sheet"])).convert("RGBA"))
    hexes = {p["hex"]: p["index"] for p in meta["palette_5bit"] if p["index"]}
    assert len(hexes) + 1 <= 16, "more than 15 colours plus transparent"
    idx = np.zeros(sheet.shape[:2], np.uint8)  # sheet as palette indices
    for y in range(sheet.shape[0]):
        for x in range(sheet.shape[1]):
            r, g, b, al = (int(v) for v in sheet[y, x])
            if al == 0:
                continue
            assert al == 255, "partial alpha at %d,%d" % (x, y)
            idx[y, x] = hexes["#%02x%02x%02x" % (r, g, b)]  # KeyError: colour outside the palette
    tiles, seen, frames = [], {}, {}
    for name, (fx, fy, w, h) in meta["frames"].items():
        assert w % T == 0 and h % T == 0 and fx % T == 0 and fy % T == 0, name
        grid = []
        for ty in range(h // T):
            row = []
            for tx in range(w // T):
                t = idx[fy + ty * T:fy + ty * T + T, fx + tx * T:fx + tx * T + T]
                if not t.any():
                    row.append(BLANK)
                    continue
                k = t.tobytes()
                if k not in seen:
                    seen[k] = len(tiles)
                    tiles.append(t)
                row.append(seen[k])
            grid.append(row)
        frames[name] = {"cols": w // T, "rows": h // T, "tiles": grid}
    # self-check: rebuild each frame from the tiles
    for name, (fx, fy, w, h) in meta["frames"].items():
        out = np.zeros((h, w), np.uint8)
        for ty, row in enumerate(frames[name]["tiles"]):
            for tx, k in enumerate(row):
                if k != BLANK:
                    out[ty * T:(ty + 1) * T, tx * T:(tx + 1) * T] = tiles[k]
        assert (out == idx[fy:fy + h, fx:fx + w]).all(), "rebuild differs: " + name
    pal = [{"index": 0, "name": "transparent"}] + [
        {k: p[k] for k in ("index", "name", "rgb5", "hex")} for p in meta["palette_5bit"] if p["index"]]
    return tiles, frames, pal, meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--draft", default=os.path.join(ROOT, "thoughts/spot/drafts/2026-11-13-attract-icons-polish"))
    ap.add_argument("--out", default=os.path.join(ROOT, "assets/attract"))
    a = ap.parse_args()
    tiles, frames, pal, meta = build(a.draft)
    assert len(tiles) == 59, "expected 59 unique tiles, got %d" % len(tiles)
    assert len(pal) <= 16
    rows = (len(tiles) + PER_ROW - 1) // PER_ROW
    atlas = np.zeros((rows * T, PER_ROW * T), np.uint8)
    for k, t in enumerate(tiles):
        atlas[k // PER_ROW * T:k // PER_ROW * T + T, k % PER_ROW * T:k % PER_ROW * T + T] = t
    img = Image.fromarray(atlas, "P")
    flat = [0, 0, 0] * 16
    for p in pal[1:]:
        flat[p["index"] * 3:p["index"] * 3 + 3] = [sp.expand5(v) for v in p["rgb5"]]  # 5-bit expanded, as the console shows it
    img.putpalette(flat)
    os.makedirs(a.out, exist_ok=True)
    img.save(os.path.join(a.out, "attract_icons.png"), transparency=0)
    json.dump({"source": "thoughts/spot/drafts/2026-11-13-attract-icons-polish/icons.json", "tile": T,
               "tile_count": len(tiles), "atlas": "attract_icons.png", "atlas_per_row": PER_ROW, "blank": BLANK,
               "palette": pal, "frames": frames, "states": meta["states"]},
              open(os.path.join(a.out, "attract_icons.json"), "w"), indent=1)
    # round trip: the saved PNG holds the same tiles
    back = np.array(Image.open(os.path.join(a.out, "attract_icons.png")))
    assert (back == atlas).all()
    print("[OK] attract icons: %d tiles, %d colours + transparent, %d frames; rebuild 0 mismatches" % (len(tiles), len(pal) - 1, len(frames)))


if __name__ == "__main__":
    main()
