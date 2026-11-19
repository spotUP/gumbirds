#!/usr/bin/env python3
"""Gum parachute drafts A/B/C for FLIER_PARACHUTE (src/core/flier.c). Hand-placed pixel data only: canopy grids are typed
row by row, strings are typed as one x per row ("6*4 7*5" = x 6 for 4 rows, then x 7 for 5 rows). No shapes from formulas.
Cell 32x32 (2 sprite columns x 2 tiles). Colours: the rival ("cpu") flier palette of assets/flier/sootling_sheet.json, so
the parachute needs no palette of its own. Anchor: cell drawn at flier cell (-4, -14); strings end on the rival's shoulders.
Run: /opt/homebrew/opt/python@3.11/bin/python3.11 -I draw_parachute.py
"""
import json, os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
FLIER = "/Users/spot/Code/ArcadeGame/.claude/worktrees/parachute-art/assets/flier/sootling_sheet"
CELL, NF, ANCHOR = 32, 8, (-4, -14)
# letter -> index into the cpu palette (0-based)
KEY = {"k": 0, "t": 6, "b": 7, "c": 8, "D": 9, "g": 10, "G": 11, "l": 12, "h": 13, "w": 14}

CANOPY = {}
# ---- A: deflated gum canopy, four sagging lobes, back rim seen through the notches ----
CANOPY["A"] = dict(x0=3, grids={
 "N": ["........kkkkkkkkkk........",
       ".....kkkhhhllllllGkkk.....",
       "...kklhhwhllllllGGGGGkk...",
       "..klhhwwhlllllGlGGGGGggk..",
       ".klhhhhlllllGlGGGGGGgGggk.",
       "klhhllllllGlGGGGGGGgGgggtk",
       "kllllllGlGGGGGGGGgGgggggtk",
       "klllGlGGGGGGGGgGgggggggttk",
       "kGlGGGGGGGgGgggggggggDgttk",
       "kGGGGGgGgggGgggggggDgDDttk",
       "kGGGggkkGgggkkggggDkkDDttk",
       ".kGggkttkggkttkgDDkttkDtk.",
       "..kkkttttkkttttkkkttttkk..",
       ".....kkkk..kkkk...kkkk...."],
 "L": ["......kkkkkkkkk...........",
       "...kkkhhhhllllGkkk........",
       "..klhhwwhllllllGGGGkkk....",
       ".klhhwhlllllGlGGGGGGggkk..",
       "klhhhllllllGlGGGGGGgGgggk.",
       "klhlllllGlGGGGGGGGgGggggtk",
       "kllllGlGGGGGGGGGgGgggggDtk",
       "klGlGGGGGGGGgGgggggggDgttk",
       "kGGGGGGgGgggGgggggDgDDDttk",
       "kGGGGggGGggggggggDkkkDDtk.",
       "kGGGggkkGgggkkgggDkttkkk..",
       ".kGggkttkggkttkgDk.kk.....",
       "..kkktttkkkkttkkk.........",
       ".....kkk....kk............"],
 "R": ["...........kkkkkkkkk......",
       "........kkkhhhlllllGkkk...",
       "....kkklhhwhllllllGGGGGk..",
       "..kklhhwwhlllllGlGGGGGggk.",
       ".klhhhhllllllGlGGGGGgGgggk",
       "klhhlllllllGlGGGGGGgGggggk",
       "klllllllGlGGGGGGGgGgggggtk",
       "kllGlGGGGGGGGgGgggggggDttk",
       "kGlGGGGGGgGgggggggggDgDttk",
       ".kGGGkkkGGGgggggggggDgDDtk",
       "..kkkttkGGggkkgggggDkkDDtk",
       ".....kk.kGgkttkgggDkttkDtk",
       ".........kkkttkkkkkktttkk.",
       "..............kk....kkk..."]})
# ---- B: torn bubble half-dome, glossy, jagged torn rim, two thick gum strands and loose shreds ----
CANOPY["B"] = dict(x0=4, grids={
 "N": ["........kkkkkkkk........",
       ".....kkkllhhhlllkkk.....",
       "...kkllhhwwhhlllGGGkk...",
       "..kllhwwwwhlllllGGGGgk..",
       ".kllhwwwhlllllGGGGGGggk.",
       ".klhhwhlllllGlGGGGGgGggk",
       "klhhhllllGlGGGGGGGgGgggk",
       "klhlllGlGGGGGGGGgGggggtk",
       "kllGlGGGGGGGGgGgggggcttk",
       "kGGGGGGGgGggggggggDcbttk",
       "kGGgkGGgGgkkgggkgggDkbtk",
       "kGgktkGggkttkgktkgDktktk",
       "kgk...kgk....k...kk...kk",
       ".k.....k................"],
 "L": ["......kkkkkkkk..........",
       "...kkkllhhhlllkkk.......",
       "..kllhhwwhhlllGGGkkk....",
       ".kllhwwwwhllllGGGGGgkk..",
       "kllhwwwhlllllGGGGGGgGggk",
       "klhhwhllllGlGGGGGGgGgggk",
       "klhhlllGlGGGGGGGgGggggtk",
       "klllGlGGGGGGGgGgggggcttk",
       "kGlGGGGGGgGgggggggDcbtk.",
       "kGGGGGgGggkkggggDkkbtk..",
       "kGGgkGGggktkgggkt.kkk...",
       "kGgktkGgk.tkgk..........",
       "kgk..kgk...k............",
       ".k....k................."],
 "R": ["..........kkkkkkkk......",
       ".......kkkllhhhlllkkk...",
       "....kkkllhhwwhlllGGGk...",
       "..kkllhhwwwhllllGGGGgk..",
       ".kllhhwwhlllllGGGGGGggk.",
       "kllhhhhllllGlGGGGGGgGggk",
       "klhhllllGlGGGGGGGgGgggtk",
       "klllGlGGGGGGGgGgggggcttk",
       ".kGlGGGGGGgGggggggDcbttk",
       "..kGGkkGGgGggkkgggDkbttk",
       "...kk.tkGGggktkggDk.kbtk",
       "........kGgk.tkgDk..kgtk",
       ".........kk...kgk....kgk",
       "...............k......k."]})
# ---- C: stretched gum ribbon wing, tips flap as it banks ----
CANOPY["C"] = dict(x0=1, grids={
 "N": ["..........kkkkkkkkkk..........",
       "......kkkklhhhhllllGkkkk......",
       "...kkklhhwwhlllllGlGGGGGkkk...",
       ".kklhwwhlllGlGGGGGGGGgGgggGkk.",
       "klhwhllGlGGGGggggggggGGgGggggk",
       "klhllGGGgggkkkkkkkkkkgggGgggtk",
       "kllGGggkkk..........kkkgggDttk",
       "kGGggDk................kgDDttk",
       "kGgDDk..................kDDtk.",
       ".kgDk....................kDtk.",
       "..kk......................kk.."],
 "L": ["............kkkkkkkkkkkk......",
       ".......kkkkklhhhhlllGGGGkkkk..",
       "....kkklhhwwhllllGlGGgggggGGkk",
       "..kklhwwhlllGlGGGGGkkkkkkgGggk",
       ".klhwhllGlGGGgggkkk.....kkgDtk",
       "klhllGGGggggkkk...........kkk.",
       "kllGGggkkkk...................",
       "kGGggDk.......................",
       "kGgDDk........................",
       "kgDDtk........................",
       ".kDtk.........................",
       "..kk.........................."],
 "R": ["......kkkkkkkkkkkk............",
       "..kkkklhhhhllllGGGGGkkkkk.....",
       "kkhhwwhlllllGlGGGGGGgGgggGkkk.",
       "klhwhlkkkkkkkGGGGgggggGgggGgkk",
       "klhlGk.......kkkkkkgggggGgggtk",
       ".kkkk..............kkkgggDgttk",
       "......................kkgDDttk",
       ".......................kgDDttk",
       "........................kDDttk",
       "........................kDDtk.",
       ".........................kDtk.",
       "..........................kk.."],
 "F": ["..............................",
       "........kkkkkkkkkkkkkk........",
       "...kkkkklhhhhhlllllGGGkkkkk...",
       "kkklhhwwwhllllGlGGGGGGGgGgggkk",
       "klhwwhllGlGGGGGgggggggGGgGggtk",
       "klllGGGggkkkkkkkkkkkkkkgggGDtk",
       ".kGGggkk..............kkgDDtk.",
       "..kgDk..................kDk...",
       "...kk....................k...."]})

# frame = (canopy key, dx, dy, strings); string = (colours left to right, first cell row, x per row down to row 31)
FRAMES = {
 "A": [
  ("N", 0, 0, [("l", 13, "6*4 7*5 8*5 9*5"), ("l", 13, "12*6 11*7 10*6"), ("G", 13, "19*6 20*7 21*6"), ("G", 13, "25*4 24*5 23*5 22*5")]),
  ("L", -1, 0, [("l", 13, "5*3 6*4 7*4 8*4 9*4"), ("l", 13, "11*9 10*10"), ("G", 13, "18*4 19*5 20*5 21*5"), ("G", 13, "24*6 23*7 22*6")]),
  ("L", -3, 1, [("l", 13, "3*2 4*3 5*3 6*3 7*3 8*3 9*2"), ("l", 13, "9*9 10*10"), ("G", 13, "16*3 17*3 18*3 19*3 20*3 21*4"), ("G", 13, "22*19")]),
  ("L", -2, 1, [("l", 13, "4*5 5*4 6*4 7*3 8*2 9*1"), ("l", 13, "10*3 9*10 10*6"), ("G", 13, "17*5 18*5 19*4 20*3 21*2"), ("G", 13, "23*2 22*7 21*5 22*5")]),
  ("N", 0, 0, [("l", 13, "6*6 7*5 8*4 9*4"), ("l", 13, "12*4 11*6 10*9"), ("G", 13, "19*8 20*6 21*5"), ("G", 13, "25*3 24*4 23*5 22*7")]),
  ("R", 1, 0, [("l", 13, "7*6 8*7 9*6"), ("l", 13, "13*4 12*5 11*5 10*5"), ("G", 13, "20*9 21*10"), ("G", 13, "26*3 25*4 24*4 23*4 22*4")]),
  ("R", 3, 1, [("l", 13, "9*19"), ("l", 13, "15*3 14*3 13*3 12*3 11*3 10*4"), ("G", 13, "22*9 21*10"), ("G", 13, "28*2 27*3 26*3 25*3 24*3 23*3 22*2")]),
  ("R", 2, 1, [("l", 13, "8*2 9*7 10*5 9*5"), ("l", 13, "14*5 13*5 12*4 11*3 10*2"), ("G", 13, "21*3 22*10 21*6"), ("G", 13, "27*5 26*4 25*4 24*3 23*2 22*1")]),
 ],
 "B": [
  ("N", 0, 0, [("Gg", 13, "5*4 6*5 7*5 8*3 9*2"), ("Gg", 13, "26*3 25*4 24*4 23*4 22*2 21*2"), ("l", 14, "11*6"), ("l", 13, "17*5")]),
  ("L", -1, 0, [("Gg", 13, "4*3 5*4 6*4 7*3 8*3 9*2"), ("Gg", 13, "25*4 24*5 23*4 22*3 21*3"), ("l", 14, "10*2 11*2 12*2"), ("l", 13, "16*2 17*2 18*1")]),
  ("L", -3, 1, [("Gg", 13, "2*2 3*2 4*2 5*3 6*3 7*3 8*2 9*2"), ("Gg", 13, "23*6 22*7 21*6"), ("l", 14, "8*2 9*2 10*2"), ("l", 13, "14*2 15*2 16*1")]),
  ("L", -2, 1, [("Gg", 13, "3*6 4*4 5*3 6*2 7*2 8*1 9*1"), ("Gg", 13, "24*3 23*3 22*3 21*4 20*3 21*3"), ("l", 14, "9*6"), ("l", 13, "15*5")]),
  ("N", 0, 0, [("Gg", 13, "5*6 6*5 7*4 8*2 9*2"), ("Gg", 13, "26*2 25*3 24*4 23*4 22*3 21*3"), ("l", 14, "11*2 10*2 9*2"), ("l", 13, "17*2 16*2 15*1")]),
  ("R", 1, 0, [("Gg", 13, "6*5 7*5 8*5 9*4"), ("Gg", 13, "27*3 26*3 25*3 24*3 23*3 22*2 21*2"), ("l", 14, "12*2 11*2 10*2"), ("l", 13, "18*2 17*2 16*1")]),
  ("R", 3, 1, [("Gg", 13, "8*9 9*10"), ("Gg", 13, "29*2 28*2 27*2 26*2 25*2 24*2 23*3 22*2 21*2"), ("l", 14, "14*2 13*2 12*2"), ("l", 13, "20*2 19*2 18*1")]),
  ("R", 2, 1, [("Gg", 13, "7*3 8*3 9*4 10*4 9*5"), ("Gg", 13, "28*5 27*4 26*3 25*2 24*2 23*1 22*1 21*1"), ("l", 14, "13*6"), ("l", 13, "19*5")]),
 ],
 "C": [
  ("N", 0, 0, [("l", 10, "3*3 4*3 5*3 6*3 7*3 8*3 9*4"), ("G", 10, "28*3 27*3 26*3 25*3 24*3 23*3 22*4"), ("g", 6, "10*8 11*10 10*8"), ("g", 6, "21*8 20*10 21*8")]),
  ("L", 0, 0, [("l", 11, "3*3 4*3 5*3 6*3 7*3 8*3 9*3"), ("G", 5, "28*4 27*4 26*4 25*4 24*4 23*4 22*3"), ("g", 6, "10*6 11*12 10*8"), ("g", 4, "22*12 21*16")]),
  ("L", -1, 1, [("l", 12, "2*2 3*3 4*3 5*3 6*3 7*2 8*2 9*2"), ("G", 6, "27*5 26*5 25*4 24*4 23*4 22*4"), ("g", 7, "9*10 10*15"), ("g", 5, "21*27")]),
  ("N", -1, 0, [("l", 10, "2*5 3*4 4*3 5*3 6*2 7*2 8*2 9*1"), ("G", 10, "27*2 26*2 25*3 24*3 23*3 22*4 21*3 22*2"), ("g", 6, "9*8 8*8 9*5 10*5"), ("g", 6, "20*12 19*6 20*4 21*4")]),
  ("F", 0, 0, [("l", 8, "4*4 5*4 6*4 7*4 8*4 9*4"), ("G", 8, "26*5 25*5 24*5 23*5 22*4"), ("g", 6, "11*13 10*13"), ("g", 6, "21*26")]),
  ("R", 0, 0, [("l", 5, "3*4 4*4 5*4 6*4 7*4 8*4 9*3"), ("G", 11, "28*3 27*3 26*3 25*3 24*3 23*3 22*3"), ("g", 4, "9*14 10*14"), ("g", 6, "21*6 20*12 21*8")]),
  ("R", 1, 1, [("l", 6, "4*5 5*5 6*4 7*4 8*4 9*4"), ("G", 12, "29*2 28*3 27*3 26*3 25*3 24*2 23*2 22*2"), ("g", 5, "10*27"), ("g", 7, "22*10 21*15")]),
  ("N", 1, 0, [("l", 10, "4*2 5*2 6*3 7*3 8*3 9*4 10*3 9*2"), ("G", 10, "29*5 28*4 27*3 26*3 25*2 24*2 23*2 22*1"), ("g", 6, "11*12 12*6 11*4 10*4"), ("g", 6, "22*8 23*8 22*5 21*5")]),
 ],
}
LABEL = {"A": "A: deflated gum canopy with strings", "B": "B: torn bubble half-dome", "C": "C: stretched gum ribbon wing"}


def xs(runs):
    out = []
    for r in runs.split():
        x, n = r.split("*"); out += [int(x)] * int(n)
    return out


def frame(v, i, pal):
    key, dx, dy, strings = FRAMES[v][i]
    im = Image.new("RGBA", (CELL, CELL), (0, 0, 0, 0))
    for cols, row0, runs in strings:  # strings first: the canopy covers their top ends; a run of 6 or less is a loose shred
        line = xs(runs)
        assert len(line) == CELL - row0 or len(line) <= 6, (v, i, runs, len(line), CELL - row0)
        assert all(abs(a - b) <= 1 for a, b in zip(line, line[1:])), (v, i, runs)  # a string never breaks
        for r, x in enumerate(line):
            for j, ch in enumerate(cols):
                im.putpixel((x + j, row0 + r), pal[KEY[ch]])
    g = CANOPY[v]["grids"][key]
    for y, row in enumerate(g):
        assert len(row) == len(g[0]), (v, key, y, len(row))
        for x, ch in enumerate(row):
            if ch != ".":
                im.putpixel((CANOPY[v]["x0"] + dx + x, dy + y), pal[KEY[ch]])
    return im


def up(im, n):
    return im.resize((im.width * n, im.height * n), Image.NEAREST)


def main():
    meta = json.load(open(FLIER + ".json"))
    pal = [tuple(c) + (255,) for c in meta["palettes"]["cpu"]]
    sheet = Image.open(FLIER + ".png").convert("RGBA")
    def cpu(fr):
        r = meta["animations"]["cpu"][fr]
        return sheet.crop((r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"]))
    t = meta["tables"]
    idle, flap = cpu(t["clip_first"][6]), cpu(t["clip_first"][1])  # CLIP_IDLE (shown on a parachute), CLIP_FLAP1 for scale

    def scene(v, i, bg):  # parachute cell over the idle rival, 40x48
        s = Image.new("RGBA", (40, 48), bg)
        s.alpha_composite(idle, (8, 16))
        s.alpha_composite(frame(v, i, pal), (8 + ANCHOR[0], 16 + ANCHOR[1]))
        return s

    for v in "ABC":
        fr = [frame(v, i, pal) for i in range(NF)]
        used = {p for f in fr for p in f.getdata() if p[3]}
        assert used <= set(pal) and len(used) <= 15, (v, len(used))
        sh = Image.new("RGBA", (CELL * NF, CELL), (0, 0, 0, 0))
        for i, f in enumerate(fr):
            sh.paste(f, (i * CELL, 0))
        sh.save(os.path.join(HERE, f"parachute_{v}_1x.png"))
        g = [up(scene(v, i, (40, 32, 72, 255)), 3).convert("P", palette=Image.ADAPTIVE, colors=32) for i in range(NF)]
        g[0].save(os.path.join(HERE, f"parachute_{v}_3x.gif"), save_all=True, append_images=g[1:], duration=110, loop=0)

    # comparison: per background, a rival with its gum balloon (scale reference), then A/B/C at centre and at both swing ends
    bgs = [(40, 32, 72, 255), (24, 40, 66, 255), (222, 148, 120, 255)]
    cmp_ = Image.new("RGBA", (40 * 10, 48 * len(bgs)), (0, 0, 0, 255))
    for row, bg in enumerate(bgs):
        ref = Image.new("RGBA", (40, 48), bg); ref.alpha_composite(flap, (8, 16)); cmp_.paste(ref, (0, row * 48))
        for n, v in enumerate("ABC"):
            for m, i in enumerate((0, 2, 6)):
                cmp_.paste(scene(v, i, bg), (40 * (1 + n * 3 + m), row * 48))
    cmp_.save(os.path.join(HERE, "compare_1x.png"))
    up(cmp_, 3).save(os.path.join(HERE, "compare_3x.png"))

    rows = "".join(
        f'<section><h2>{LABEL[v]}</h2><img src="parachute_{v}_3x.gif" alt="{v} sway"><br>'
        f'<img class="s" src="parachute_{v}_1x.png" style="width:768px" alt="{v} sheet"></section>' for v in "ABC")
    open(os.path.join(HERE, "index.html"), "w").write(
        '<!doctype html><meta charset="utf-8"><title>Gum parachute drafts</title><style>'
        'body{background:#1b1d2a;color:#e8eaf2;font:16px/1.5 system-ui,sans-serif;margin:32px}'
        'img{image-rendering:pixelated;margin:8px 0}img.s{background:#3a3f5c}h2{margin:32px 0 4px}</style>'
        '<h1>Gum parachute: three drafts</h1>'
        '<p>Each 8 frames, 32 x 32 cell, rival flier palette. Sheets shown 3x on a grey panel.</p>' + rows +
        '<section><h2>In place above the rival, game scale then 3x</h2>'
        '<p>Left column: rival with its gum, for scale. Then A, B, C, each at centre, far left, far right. '
        'Rows: dusk, moon, a light sky.</p>'
        '<img src="compare_1x.png" alt="comparison 1x"><br><img src="compare_3x.png" alt="comparison 3x"></section>')
    print("ok")


if __name__ == "__main__":
    main()
