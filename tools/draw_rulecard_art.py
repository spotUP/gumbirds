#!/usr/bin/env python3
"""Gum Games rules card art (owner-picked layout A "banner and strip", draft thoughts/shared/drafts/2026-11-17-rules-card):
hand-typed pixel grids -> assets/rulecard/rulecard_fix.png (12 fix tiles, P mode, 128 px wide: button A up 0..3, down 4..7,
bar segments empty / power / safe / foul 8..11) and assets/rulecard/rulecard_sheet.png + .json (5 sprite tiles: slab, needle 20,
needle 45, gum, gum trail dot). Usage (repo root): python3.14 -I tools/draw_rulecard_art.py
The grids are the draft's, typed by hand; this script only places them, maps the palette and bakes the panel colour into the
button tiles (fix tiles have no layer under them but the sprites, so the card panel colour is the 15th colour)."""
import json, os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def snap(h):  # Neo Geo 5 bits per channel
    return tuple(((int(h[i:i + 2], 16) >> 3) << 3) | (int(h[i:i + 2], 16) >> 5) for i in (0, 2, 4))

NAMES = "k123456789WgGh"  # fix palette index = position + 1
PAL = {k: snap(v) for k, v in {
    "k": "100828",                                   # outline
    "1": "7b1042", "2": "e63142", "3": "ff9c84",     # red: shade turns purple, light turns orange
    "4": "9c4a18", "5": "f7b521", "6": "ffef8c",     # yellow: shade turns brown-orange
    "7": "10636b", "8": "31c552", "9": "c6f77b",     # green: shade turns teal, light turns yellow
    "W": "ffffff",
    "g": "39396b", "G": "7384b5", "h": "c6d6f7",     # steel: violet shade, sky light
    "P": "ff73bd"}.items()}                          # gum pink (sprite palette only)

BTN_UP = [
 "....kkkkkkkk....",
 "..kk33322222kk..",
 ".k3WW322222221k.",
 "k33W32222222211k",
 "k33222222222211k",
 "k32222222222121k",
 "k22222222221211k",
 "k22222222212111k",
 "k12222221211111k",
 ".k121212111111k.",
 ".Gkk11111111kkG.",
 "GhGGkkkkkkkkGGgG",
 "GhhGGGGGGGGGGggG",
 "kGGGGGGGGGGgGggk",
 ".kkgGgGggggggkk.",
 "...kkkkkkkkkk..."]
BTN_DOWN = [
 "................",
 "................",
 "....kkkkkkkk....",
 "..kk22222222kk..",
 ".k322222222221k.",
 "k32222222222211k",
 "k22222222221211k",
 "k22222222212111k",
 "k12222121211111k",
 "Gk121211111111kG",
 "Ghkk11111111kkgG",
 "GhhGkkkkkkkkGggG",
 "GhhGGGGGGGGGGggG",
 "kGGGGGGGGGGgGggk",
 ".kkgGgGggggggkk.",
 "...kkkkkkkkkk..."]
LETTER_A = [".kkkk.", "kk..kk", "kk..kk", "kkkkkk", "kk..kk", "kk..kk"]
BAR = {  # 8x8 bar segments, hand dither between the three steps of each ramp
 "empty": ["kkkkkkkk", "gggggggg", "gkgggkgg", "gggggggg", "ggkgggkg", "gggggggg", "kgkgkgkg", "kkkkkkkk"],
 "power": ["kkkkkkkk", "66666666", "65656566", "55555555", "55555555", "54545455", "44444444", "kkkkkkkk"],
 "safe":  ["kkkkkkkk", "99999999", "98989899", "88888888", "88888888", "87878788", "77777777", "kkkkkkkk"],
 "foul":  ["kkkkkkkk", "33333333", "32323233", "22222222", "22222222", "21212122", "11111111", "kkkkkkkk"]}
GUM = ["..kkkk..", ".kPPPPk.", "kPWPPP1k", "kPPPPP1k", "kPPPP11k", "kPP1111k", ".k1111k.", "..kkkk.."]
DOT = ["........", "........", "........", "...PP...", "...P1...", "........", "........", "........"]
SLAB = [
 "kkkkkkkkkkkkkkkk",
 "hhhhhhhhhhhhhhhh",
 "hGhGhGhGGhGGhGGG",
 "GGGGGGGGGGGgGGgG",
 "GgGgGgGggGgggggg",
 "gggggggggggggggg",
 "kgkgkgkgkkgkkkkk",
 ".k.k.k.kk.kkkkk."]
N45 = [
 "................", "..............WW", ".............66.", "............66..", "...........66...", "..........66....",
 ".........66.....", "........55......", ".......55.......", "......55........", ".....55.........", "....55..........",
 "...55...........", "..55............", ".55.............", "55.............."]
N20 = ["................"] * 10 + [
 "..............WW", "...........666..", "........666.....", ".....555........", "..555...........", "55.............."]
for name, g in (("up", BTN_UP), ("down", BTN_DOWN), ("slab", SLAB), ("n45", N45), ("n20", N20)):
    assert all(len(r) == 16 for r in g), name      # self-check: typed rows are full width
for g in list(BAR.values()) + [GUM, DOT]:
    assert len(g) == 8 and all(len(r) == 8 for r in g)

def button(down):  # the letter A sits on the cap, 2 px lower when the cap is down
    g = [list(r) for r in (BTN_DOWN if down else BTN_UP)]
    for y, row in enumerate(LETTER_A):
        for x, c in enumerate(row):
            if c == "k":
                g[y + (4 if down else 2)][x + 5] = "k"
    return ["".join(r) for r in g]

def panel_colour():  # the fill of the strip panel (font plate fill, white font palette) (font glyph s:fill): the button tiles sit on it
    fj = json.load(open(os.path.join(ROOT, "assets/font/fix_font.json")))
    sheet = Image.open(os.path.join(ROOT, "assets/font/fix_font_sheet.png"))
    i = fj["tiles"]["s:fill"]
    px = {sheet.getpixel((i % 16 * 8 + x, i // 16 * 8 + y)) for y in range(8) for x in range(8)}
    assert len(px) == 1 and 0 not in px, px
    return tuple(fj["palettes"]["white"][px.pop() - 1])

def main():
    out = os.path.join(ROOT, "assets/rulecard")
    os.makedirs(out, exist_ok=True)
    # fix atlas: tiles 0..3 button up (row-major 2x2), 4..7 button down, 8..11 bars
    fix = Image.new("P", (128, 8), 0)
    cols = [(255, 0, 255)] + [PAL[c] for c in NAMES] + [panel_colour()]
    assert len(cols) == 16 and len(set(cols)) == 16, "fix palette colours collide"
    fix.putpalette([v for c in cols for v in c] + [0] * (768 - 48))
    idx = {c: i + 1 for i, c in enumerate(NAMES)}
    idx["."] = 15
    t = 0
    for g in (button(0), button(1)):
        for ty in (0, 8):
            for tx in (0, 8):
                for y in range(8):
                    for x in range(8):
                        fix.putpixel((t * 8 + x, y), idx[g[ty + y][tx + x]])
                t += 1
    for name in ("empty", "power", "safe", "foul"):
        for y in range(8):
            for x in range(8):
                fix.putpixel((t * 8 + x, y), idx[BAR[name][y][x]])
        t += 1
    assert t == 12
    fix.save(os.path.join(out, "rulecard_fix.png"))
    # sprite sheet: one 16x16 cell per prop, art in the top-left of its cell
    props = [("slab", SLAB), ("n20", N20), ("n45", N45), ("gum", GUM), ("dot", DOT)]
    spr = Image.new("RGBA", (16 * len(props), 16), (0, 0, 0, 0))
    for n, (_, g) in enumerate(props):
        for y, row in enumerate(g):
            for x, c in enumerate(row):
                if c != ".":
                    spr.putpixel((n * 16 + x, y), PAL[c] + (255,))
    spr.save(os.path.join(out, "rulecard_sheet.png"))
    meta = {"source": "tools/draw_rulecard_art.py (owner-picked layout A, hand-typed grids). One 16x16 frame per prop, art in the "
                      "top-left of the cell: slab (16x8), needle at 20 degrees, needle at 45 degrees, gum (8x8), gum trail dot (8x8)",
            "animations": {"props": [{"x": n * 16, "y": 0, "w": 16, "h": 16} for n in range(len(props))]}}
    json.dump(meta, open(os.path.join(out, "rulecard_sheet.json"), "w"), indent=1)
    print("[OK] assets/rulecard: 12 fix tiles, %d sprite frames" % len(props))

if __name__ == "__main__":
    main()
