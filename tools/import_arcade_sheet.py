#!/usr/bin/env python3
"""Rebuild assets/arcade/arcade_sheet.png + .json from the picked draft strips.
Run: /opt/homebrew/bin/python3.14 -I tools/import_arcade_sheet.py [--out <dir>]   then `gmake`.

Source: thoughts/spot/drafts/2026-11-12-arcade-art/*_strip.png (picks: thoughts/spot/2026-11-12-arcade-art-final.md).
Strips are stacked top to bottom, pasted unchanged at x 0 (no redraw, no recolour). A strip holds frames side by side;
STRIPS says how many frames of which animation it holds. Animation rects, defines, tables, hitboxes and the pinned palettes
(storm, player, computer, island roof: same colours in the same index order as the sets that already load them, so the
pipeline shares tile data and the game adds no new palette for the pinned pieces) are written to the json.
The pipeline gives every animation its own palette entry, so pieces on one palette are joined into one pipeline animation
named after the palette (roof, storm, player, computer); json "pieces" says where each piece sits: [group, first frame, count].
Pattern: tools/import_islands_sheet.py."""
import argparse, json, os, sys
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sprite_pipeline import rgb_to_ng

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRAFTS = os.path.join(ROOT, "thoughts/spot/drafts/2026-11-12-arcade-art")
OUT = os.path.join(ROOT, "assets/arcade")
# (strip file, frame w, frame h, [(animation, frame count), ...]); order = sheet rows, top to bottom
STRIPS = [
    ("island_a_strip.png", 48, 16, [("island_a", 8)]),
    ("island_b_v2_strip.png", 48, 32, [("island_b", 1)]),
    ("vent_a_v2_body_strip.png", 32, 16, [("body_a", 5)]),
    ("vent_b_v2_body_strip.png", 32, 16, [("body_b", 5)]),
    ("spark_a_strip.png", 16, 16, [("spark_a", 8)]),
    ("spark_b_v2_strip.png", 16, 16, [("spark_b", 8)]),
    ("particle_v2_strip.png", 16, 16, [("smoke_light", 8), ("smoke_dark", 8), ("flash", 1), ("air", 8)]),
    ("flipper_a_v2_strip.png", 40, 40, [("flipper_a", 8)]),
    ("flipper_b_v2_strip.png", 40, 40, [("flipper_b", 8)]),
    ("grabber_a_v2_strip.png", 40, 44, [("grabber_a", 12)]),
    ("grabber_b_v2_strip.png", 40, 44, [("grabber_b", 12)]),
    ("grate_b_v2_hatch_strip.png", 32, 16, [("hatch", 1)]),
    ("blowup_b_v2_strip.png", 24, 32, [("blow", 8), ("caught", 2)]),
    ("drop_a_strip.png", 16, 16, [("drop_a", 6)]),
]
# Bonus stage nozzle art (thoughts/spot/drafts/2026-11-13-bonus-nozzles/, variant A): one image with 4 nozzles of different heights
# (bottom aligned in the image), the gum burst (13 frames) and the floor tile (left 32 of 64). One unpinned "nozzle" group, so it
# gets its own palette appended after the pinned ones and no existing arcade palette index moves.
NOZZLE_DIR = os.path.join(ROOT, "thoughts/spot/drafts/2026-11-13-bonus-nozzles")
# Gum burst (variant A "tight pop", picked 2026-11-15; draft thoughts/shared/drafts/2026-11-15-gum-burst/): 13 frames of 32x32, ticks per frame at 60 Hz.
BURST_DIR = os.path.join(ROOT, "assets/arcade")
BURST_TICKS = [3, 3, 2, 2, 2, 2, 3, 3, 3, 3, 3, 4, 4]
NOZZLE_X = [0, 36, 72, 108]; NOZZLE_W = 32; NOZZLE_H = [24, 40, 32, 36]
# animation -> palette it is pinned to (sources: triphaz storm, sootling player/cpu, island roof)
PINS = {"storm": ["body_b", "spark_a", "spark_b", "smoke_light", "smoke_dark", "flash", "air", "hatch"],
        "player": ["flipper_a", "flipper_b", "grabber_a", "grabber_b", "drop_a"],
        "computer": ["blow", "caught"],
        "roof": ["island_a", "island_b"]}
# Vent warning (variant B, picked 2026-11-15; draft thoughts/shared/drafts/2026-11-15-vent-warn/draw_vent_warn.py, grids copied unchanged).
# Boil bubbles: 10 hand-placed frames of 16x16, bottom aligned (rows missing at the top are empty). A digit is a storm palette entry:
# 9 blue rim, a cyan, b pale, c white (the spark's own colours). They are not a sprite of their own: each warning frame of the body
# ("warn", 32x32) holds a body frame with one boil grid on its top, so the warning costs no sprite. WARN lists the (body frame, boil grid)
# pairs the 72 warning ticks show, in the order they show (src/core/arc_view.c WARN_TAB).
BOIL = [
    [".....99.........", "....9ab9...9....", "....9aa9..9a9..."],
    [".....99.........", "....9ab9........", "...9abba9..99...", "...9aaaa9.9ab9.."],
    [".....999........", "....9abb9.......", "...9abcba9......", "...9abbaa9......", "...9aaaa99..99..", "....9aa99..9ab9.", ".....999...9aa9."],
    [".....99.........", "....9ab9........", "...9abcb9.......", "...9abba9.......", "...9abaa9.......", "...9aaaa9..99...", "....9aa9..9ab9..", "....9aa9.9abba9.", ".....99..9aaaa9."],
    ["....b...b.......", "..b...c....b....", ".....c.c........", "...a..c..a......", "....b...b.......", "..a.......99....", ".....a...9ab9...", ".........9bcb9..", "........9abbaa9.", "........9aaaa99."],
    ["...b......b.....", "................", ".b..............", "................", "......a.........", "..........99....", ".a.......9ab9...", "........9abcb9..", "........9abba9..", "........9aaaa9..", "....99...9aa9...", "...9ab9...99...."],
    ["..........99....", ".........9ab9...", ".........9bcb9..", "a........9abb9..", ".........9aba9..", "..........9a9...", "..a.......9a9...", "....99.....9....", "...9ab9.........", "..9abba9........"],
    [".......b...c...b", ".........c......", "........b.c.b...", "...........c....", ".......a.....a..", "..........b.....", "....99..........", "...9ab9......a..", "..9abcb9........", "..9abbaa9.......", "..9aaaa99......."],
    [".......b....b...", "................", "................", "...............a", "................", "................", "....999.........", "...9abb9........", "..9abcba9.......", "..9abbaa9....a..", "..9aaaa99.......", "...9aa99........", "....999........."],
    ["....99..........", "...9ab9.........", "...9ba9.........", "....99..........", "................", "................", "................", "................", "...............a", "...........9....", ".....9....9a9..."],
]
WARN = [(1, b) for b in range(5)] + [(2, b) for b in range(4, 10)] + [(3, 9)] + [(3, b) for b in range(7)]
# Glow: hand-picked 5-bit RGB steps for entries 1..5 of the vent palette line (outline, 3 metal shades, metal light). Step 0 is the storm
# colours (asserted in build). The game writes one row on a step change (table vent_heat, 8 x 5 palette words).
HEAT = [
    [(1, 1, 3), (3, 3, 7), (6, 6, 11), (10, 11, 15), (16, 16, 18)],
    [(2, 1, 3), (5, 3, 7), (9, 6, 10), (13, 10, 13), (19, 15, 16)],
    [(3, 1, 3), (7, 3, 6), (12, 5, 9), (16, 9, 11), (22, 14, 13)],
    [(4, 1, 3), (9, 2, 5), (15, 4, 7), (20, 8, 8), (25, 14, 10)],
    [(5, 1, 2), (11, 2, 4), (18, 4, 5), (23, 8, 5), (28, 15, 8)],
    [(7, 1, 2), (13, 2, 3), (21, 4, 3), (26, 9, 3), (30, 18, 7)],
    [(9, 1, 1), (16, 2, 2), (24, 5, 2), (29, 12, 3), (31, 22, 8)],
    [(12, 2, 1), (19, 3, 1), (27, 7, 2), (31, 16, 4), (31, 27, 13)],
]
c5 = lambda v: (v << 3) | (v >> 2)
META = {
    "defines": {"ISLAND48_ART_W": 48, "VENT_ART_W": 32, "VENT_FRAMES": 5, "SPARK_ART_W": 16, "SPARK_FRAMES": 8, "SPARK_HIT_X0": 3, "SPARK_HIT_Y0": 3, "SPARK_HIT_X1": 13, "SPARK_HIT_Y1": 13, "VENT_LOOP_TICKS": 336, "PARTICLE_ART_W": 16, "FLIPPER_ART_W": 40, "FLIPPER_FRAMES": 8, "FLIPPER_A_HIT_R": 14, "FLIPPER_B_HIT_R": 12, "GRABBER_ART_W": 40, "GRABBER_ART_H": 44, "GRABBER_FRAMES": 12, "BLOW_ART_W": 24, "BLOW_ART_H": 32, "DROP_ART_W": 16, "DROP_FRAMES": 6, "PUFF_TOTAL_TICKS": sum(BURST_TICKS)},
    "tables": {"grabber_frame_ticks": [7, 6, 4, 4, 8, 3, 4, 13, 5, 5, 5, 7], "spark_frame_ticks": [4], "caught_frame_ticks": [6, 10], "puff_frame_ticks": BURST_TICKS},
    "hitbox": {"spark": {"x": 3, "y": 3, "w": 10, "h": 10}, "flipper_a": {"x": 6, "y": 6, "w": 28, "h": 28}, "flipper_b": {"x": 8, "y": 8, "w": 24, "h": 24}, "grabber": {"x": 12, "y": 6, "w": 16, "h": 38}}}


def load_json(rel):
    return json.load(open(os.path.join(ROOT, rel)))


def island_roof():
    """Island roof palette in the order the pipeline gave it: first appearance over the island sheet frames."""
    j = load_json("assets/islands/island_sheet.json")
    px = Image.open(os.path.join(ROOT, "assets/islands/island_sheet.png")).convert("RGBA").load()
    out = []
    for fr in sum(j["animations"].values(), []):
        for y in range(fr["y"], fr["y"] + fr["h"]):
            for x in range(fr["x"], fr["x"] + fr["w"]):
                p = px[x, y]
                if p[3] and p[:3] not in out:
                    out.append(p[:3])
    return [list(c) for c in out]


def snap5(im):
    """The draft colours are 8 bit; the pipeline wants 5 bit expanded values (v5 << 3 | v5 >> 2). Alpha stays."""
    lut = [((round(v * 31 / 255) << 3) | (round(v * 31 / 255) >> 2)) for v in range(256)]
    r, g, b, a = im.split()
    return Image.merge("RGBA", (r.point(lut), g.point(lut), b.point(lut), a))


def build(out):
    strips = [(Image.open(os.path.join(DRAFTS, f)).convert("RGBA"), fw, fh, an) for f, fw, fh, an in STRIPS]
    width = max(im.width for im, *_ in strips)
    sheet = Image.new("RGBA", (width, sum(im.height for im, *_ in strips)), (0, 0, 0, 0))
    anims, y = {}, 0
    for im, fw, fh, an in strips:
        assert im.height == fh and im.width == fw * sum(n for _, n in an), "strip size differs from STRIPS"
        sheet.paste(im, (0, y))
        x = 0
        for name, n in an:
            anims[name] = [{"x": x + i * fw, "y": y, "w": fw, "h": fh} for i in range(n)]
            x += n * fw
        y += im.height
    storm = load_json("assets/triphaz/triphaz_sheet.json")["palettes"]["storm"]
    assert [[c5(v) for v in c] for c in HEAT[0]] == storm[:5], "heat step 0 must be the storm colours"
    y = sheet.height   # warn row: body frame in the lower half, its boil grid (storm colours) centred on the body top, 1 px into the body and behind it
    grown = Image.new("RGBA", (max(sheet.width, 32 * len(WARN)), y + 32), (0, 0, 0, 0))
    grown.paste(sheet, (0, 0)); sheet = grown
    for i, (bf, bi) in enumerate(WARN):
        rows = BOIL[bi]
        assert all(len(r) == 16 for r in rows) and len(rows) <= 16
        for ry, row in enumerate(rows):
            for rx, ch in enumerate(row):
                if ch != ".": sheet.putpixel((i * 32 + 8 + rx, y + 17 - len(rows) + ry), (*storm[int(ch, 16) - 1], 255))
        r = anims["body_a"][bf]
        body = sheet.crop((r["x"], r["y"], r["x"] + 32, r["y"] + 16))
        sheet.paste(body, (i * 32, y + 16), body)
    anims["warn"] = [{"x": i * 32, "y": y, "w": 32, "h": 32} for i in range(len(WARN))]
    for f in ("nozzles_A_1x.png", "gum_burst_a_strip.png", "floor_A_1x.png"):
        im = snap5(Image.open(os.path.join(BURST_DIR if f.startswith("gum_burst") else NOZZLE_DIR, f)).convert("RGBA"))
        y = sheet.height
        grown = Image.new("RGBA", (max(sheet.width, im.width), y + im.height), (0, 0, 0, 0))
        grown.paste(sheet, (0, 0)); grown.paste(im, (0, y)); sheet = grown
        if f.startswith("nozzles"):
            assert im.size == (140, 40)
            for i in range(4):
                anims["nozzle%d" % i] = [{"x": NOZZLE_X[i], "y": y + 40 - NOZZLE_H[i], "w": NOZZLE_W, "h": NOZZLE_H[i]}]
        elif f.startswith("gum_burst"):
            assert im.size == (32 * len(BURST_TICKS), 32)
            anims["puff"] = [{"x": i * 32, "y": y, "w": 32, "h": 32} for i in range(len(BURST_TICKS))]
        else:
            assert im.size == (64, 16)
            anims["floor"] = [{"x": 0, "y": y, "w": 32, "h": 16}]
    pins = {**PINS, "nozzle": ["nozzle0", "nozzle1", "nozzle2", "nozzle3", "puff", "floor"],
            "vent": ["body_a", "warn"]}   # the vent body on its own line (a copy of storm), so its glow cycle leaves sparks and the hatch alone; last, so no palette index moves
    pieces, groups = {}, {g: [] for g in pins}
    for g, names in pins.items():
        for a in names:
            pieces[a] = [g, len(groups[g]), len(anims[a])]
            groups[g] += anims[a]
    pal = {"storm": storm, "vent": storm,
           "player": load_json("assets/flier/sootling_sheet.json")["palettes"]["player"],
           "computer": load_json("assets/flier/sootling_sheet.json")["palettes"]["cpu"],
           "roof": island_roof()}
    meta = {"source": "tools/import_arcade_sheet.py: strips of thoughts/spot/drafts/2026-11-12-arcade-art/ stacked unchanged; picks in thoughts/spot/2026-11-12-arcade-art-final.md",
            "palette_policy": "subset", **META,
            "palettes": {g: pal[g] for g in (*PINS, "vent")},   # "nozzle" has none: the pipeline derives it
            "pieces": pieces,
            "animations": groups}
    meta["tables"] = {**META["tables"], "vent_heat": [rgb_to_ng(tuple(c5(v) for v in c)) for step in HEAT for c in step]}
    for a, (g, first, n) in pieces.items():   # group relative first frame and count: the game picks frames by piece
        meta["defines"]["PIECE_%s_FIRST" % a.upper()] = first
        meta["defines"]["PIECE_%s_COUNT" % a.upper()] = n
    os.makedirs(out, exist_ok=True)
    sheet.save(os.path.join(out, "arcade_sheet.png"))
    json.dump(meta, open(os.path.join(out, "arcade_sheet.json"), "w"), indent=1)
    return len(anims)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    print("imported %d animations" % build(ap.parse_args().out))
