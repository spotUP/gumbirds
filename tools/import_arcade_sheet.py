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
import argparse, json, os
from PIL import Image

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
# (bottom aligned in the image), the mouth puff (4 frames) and the floor tile (left 32 of 64). One unpinned "nozzle" group, so it
# gets its own palette appended after the pinned ones and no existing arcade palette index moves.
NOZZLE_DIR = os.path.join(ROOT, "thoughts/spot/drafts/2026-11-13-bonus-nozzles")
NOZZLE_X = [0, 36, 72, 108]; NOZZLE_W = 32; NOZZLE_H = [24, 40, 32, 36]
# animation -> palette it is pinned to (sources: triphaz storm, sootling player/cpu, island roof)
PINS = {"storm": ["body_a", "body_b", "spark_a", "spark_b", "smoke_light", "smoke_dark", "flash", "air", "hatch"],
        "player": ["flipper_a", "flipper_b", "grabber_a", "grabber_b", "drop_a"],
        "computer": ["blow", "caught"],
        "roof": ["island_a", "island_b"]}
META = {
    "defines": {"ISLAND48_ART_W": 48, "VENT_ART_W": 32, "VENT_FRAMES": 5, "SPARK_ART_W": 16, "SPARK_FRAMES": 8, "SPARK_HIT_X0": 3, "SPARK_HIT_Y0": 3, "SPARK_HIT_X1": 13, "SPARK_HIT_Y1": 13, "VENT_LOOP_TICKS": 336, "PARTICLE_ART_W": 16, "FLIPPER_ART_W": 40, "FLIPPER_FRAMES": 8, "FLIPPER_A_HIT_R": 14, "FLIPPER_B_HIT_R": 12, "GRABBER_ART_W": 40, "GRABBER_ART_H": 44, "GRABBER_FRAMES": 12, "BLOW_ART_W": 24, "BLOW_ART_H": 32, "DROP_ART_W": 16, "DROP_FRAMES": 6},
    "tables": {"grabber_frame_ticks": [7, 6, 4, 4, 8, 3, 4, 13, 5, 5, 5, 7], "spark_frame_ticks": [4], "caught_frame_ticks": [6, 10]},
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
    for f in ("nozzles_A_1x.png", "puff_A_1x.png", "floor_A_1x.png"):
        im = snap5(Image.open(os.path.join(NOZZLE_DIR, f)).convert("RGBA"))
        y = sheet.height
        grown = Image.new("RGBA", (max(sheet.width, im.width), y + im.height), (0, 0, 0, 0))
        grown.paste(sheet, (0, 0)); grown.paste(im, (0, y)); sheet = grown
        if f.startswith("nozzles"):
            assert im.size == (140, 40)
            for i in range(4):
                anims["nozzle%d" % i] = [{"x": NOZZLE_X[i], "y": y + 40 - NOZZLE_H[i], "w": NOZZLE_W, "h": NOZZLE_H[i]}]
        elif f.startswith("puff"):
            assert im.size == (128, 24)
            anims["puff"] = [{"x": i * 32, "y": y, "w": 32, "h": 24} for i in range(4)]
        else:
            assert im.size == (64, 16)
            anims["floor"] = [{"x": 0, "y": y, "w": 32, "h": 16}]
    pins = {**PINS, "nozzle": ["nozzle0", "nozzle1", "nozzle2", "nozzle3", "puff", "floor"]}
    pieces, groups = {}, {g: [] for g in pins}
    for g, names in pins.items():
        for a in names:
            pieces[a] = [g, len(groups[g]), len(anims[a])]
            groups[g] += anims[a]
    pal = {"storm": load_json("assets/triphaz/triphaz_sheet.json")["palettes"]["storm"],
           "player": load_json("assets/flier/sootling_sheet.json")["palettes"]["player"],
           "computer": load_json("assets/flier/sootling_sheet.json")["palettes"]["cpu"],
           "roof": island_roof()}
    meta = {"source": "tools/import_arcade_sheet.py: strips of thoughts/spot/drafts/2026-11-12-arcade-art/ stacked unchanged; picks in thoughts/spot/2026-11-12-arcade-art-final.md",
            "palette_policy": "subset", **META,
            "palettes": {g: pal[g] for g in PINS},   # "nozzle" has none: the pipeline derives it
            "pieces": pieces,
            "animations": groups}
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
