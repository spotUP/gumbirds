#!/usr/bin/env python3
"""Hot Gum carrier bubble drafts A/B/C (party rule Hot Gum, thoughts/shared/plans/2026-11-16-party-modes.md decision 5).
Hand-placed pixel data only: every cell is typed row by row. Rows may omit trailing transparent pixels.
Option C rims are typed as one (x0, left pixels, right pixels) entry per row, mirrored end at 31 - x0; nothing is computed
from a formula. Motion offsets (dx, dy) in the sequences are sprite position changes the game would do, not new tiles.
One palette shared by all three options (13 colours + transparent).
Run: python3.14 -I draw_gum_bubble.py
"""
import os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "../../../.."))
PAL = {"k": "080818", "m": "6b0f2e", "r": "b3182e", "R": "e63a1e", "o": "ff7a1a", "O": "ffa922", "y": "ffdc4a",
       "w": "fff3b0", "W": "ffffff", "p": "d42a7a", "P": "ff6ab8", "s": "dfe9f2", "S": "9fb0cc"}
RGBA = {c: tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (255,) for c, h in PAL.items()}

def cell(w, h, rows, y0=0):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    assert len(rows) + y0 <= h, (len(rows), y0, h)
    for y, row in enumerate(rows):
        assert len(row) <= w, (y, row)
        for x, c in enumerate(row):
            if c != ".":
                im.putpixel((x, y + y0), RGBA[c])
    return im

# ---------------- B: angry bubble, 16x16, one sprite column, one tile ----------------
B = [
 ["", "",                      # 0 rest
  ".....kkkkkk.....",
  "...kkoOOOoRkk...",
  "..koOywyOooRrk..",
  "..kOywWyOooRRk..",
  ".koOywyOoooRRrk.",
  ".koOOooooRRRrrk.",
  ".kookkoRRRkkrrk.",
  ".kRRokkRRkkrrmk.",
  ".kRRRWkRRkWrmpk.",
  "..kRRRRRRrrmpk..",
  "..krRkWkWkrmpk..",
  "...kkrrmmmpkk...",
  ".....kkkkkk.....",
  "......kpk......."],
 ["",                          # 1 inflate
  ".....kkkkkk.....",
  "...kkoOOOOokk...",
  "..koOyywyOooRk..",
  ".koOywWWyOooRrk.",
  ".kOywWWyOoooRRk.",
  "koOyywyOoooRRRrk",
  "koOOOooooRRRRrrk",
  "kooOkkooRRRkkrrk",
  "kRRookkRRRkkrrmk",
  "kRRRRWkRRRkWrmpk",
  ".kRRRRRRRRrrmpk.",
  ".krRRkWkWkrrmpk.",
  "..kkrrrrmmmpkk..",
  "....kkkkkkkk....",
  "......kpk......."],
 ["....kkkkkkkk....",          # 2 strained, white hot, eyes shut
  "..kkOyyyyyOokk..",
  ".kOyywWWwyyOook.",
  "kOyywWWWWwyyOoRk",
  "kOywWWWWwyyOOoRk",
  "kOyywWWwyyOOooRk",
  "kOOyyyyyOOooRRRk",
  "kokkOOOOoooRkkRk",
  "koookkooRRkkRRrk",
  "kRokkkoRRRkkkrrk",
  "kRRRRRRRRRRRrrmk",
  "kRRkkkkkkkkkrrmk",
  ".kRkWkWkWkWkrmk.",
  ".kkrkkkkkkkkrkk.",
  "...kkkkkkkkkk...",
  "......kpk......."],
 ["", "", "", "", "",          # 3 snap back, squashed flat
  "...kkkkkkkkkk...",
  ".kkoOOOOOoooRkk.",
  "koOywwyOOoooRRrk",
  "koOOyyOoooRRRRrk",
  "kookkkoRRRkkkrrk",
  "kRRRWkRRRRkWrmpk",
  "kRRRRRkkkkRrrmpk",
  ".kkrrrrrrmmmpkk.",
  "...kkkkkkkkkk...",
  "......kpk......."],
 ["......kkkk......",          # 4 rebound, tall
  "....kkoOOokk....",
  "...koOywyOoRk...",
  "...kOywWyOoRk...",
  "...kOywWyOoRk...",
  "...kOyywOooRk...",
  "...koOyOooRRk...",
  "...koOOooRRrk...",
  "...kokkoRkkrk...",
  "...kRWkRRkWrk...",
  "...kRRRRRrrmk...",
  "...kRRkkkrmpk...",
  "...krRRRrrmpk...",
  "....krrrmmpk....",
  ".....kkkkkk.....",
  "......kpk......."],
 ["", "", "",                  # 5 settle, a little wide
  "....kkkkkkkk....",
  "..kkoOOOOooRkk..",
  ".koOywwyOoooRrk.",
  ".kOywWwyOoooRRk.",
  "koOOyyOooooRRRrk",
  "kookkooRRRRkkrrk",
  "kRRokkRRRRkkrrmk",
  "kRRRWkRRRRkWrmpk",
  ".kRRRRRRRRrrmpk.",
  ".krRRkWkWkrrmpk.",
  "..kkrrrrmmmpkk..",
  "....kkkkkkkk....",
  "......kpk......."],
]
# (cell, dx, dy, ms): swell, strain and tremble, snap, rebound, settle
B_SEQ = [(0, 0, 0, 130), (1, 0, 0, 110), (2, 0, -1, 70), (2, 1, -1, 50), (2, -1, -1, 50), (2, 1, -1, 50),
         (3, 0, 1, 70), (4, 0, -2, 80), (5, 0, 0, 90), (0, 0, 0, 160)]

# ---------------- A: molten wad on the head + steam, 16x32, one sprite column, two tiles ----------------
WAD = [
 ["", "", "",                  # 0 rest
  ".....kkkkk......",
  "...kkOyyOokk....",
  "..kOywWyOooRk...",
  ".kOywyOOooRRrk..",
  ".koOOOoooRRRrmk.",
  "koOoooRRRRRrrmpk",
  "kRoRRRRRrrrrmmpk",
  "kRRkrRRrkkrrmkpk",
  "kRk.krRk..krk.kk",
  ".k...kRk...k....",
  "......k........."],
 ["", "",                      # 1 a blister swells on the left
  "....kkkk........",
  "..kkOyyOkkk.....",
  ".kOywWyOoookk...",
  ".kOyWWyOooRRrk..",
  ".kOywyOOooRRrk..",
  ".koOOOoooRRRrmk.",
  "koOoooRRRRRrrmpk",
  "kRoRRRRRrrrrmmpk",
  "kRRkrRRrkkrrmkpk",
  "kRk.krRk..krk.kk",
  ".k...kRk...k....",
  "......kk........"],
 ["...kkkk.........",          # 2 blister at full stretch
  "..kywwyk........",
  ".kyWWwyOk.......",
  ".kywWwyOkkkk....",
  ".kOywyOOoooRkk..",
  ".kOOyOOoooRRrk..",
  ".koOOOoooRRRrk..",
  ".koOOooooRRRrmk.",
  "koOoooRRRRRrrmpk",
  "kRoRRRRRrrrrmmpk",
  "kRRkrRRrkkrrmkpk",
  "kRk.krRk..krk.kk",
  ".k...kRk...k....",
  "......kRk......."],
 [".y....w...y.....",          # 3 blister bursts, flecks fly
  "...y......O.....",
  "w...k..k...y....",
  "..kkOk.kOkk.....",
  ".kOyOOkOooRRkk..",
  ".kOywyOOooRRrk..",
  ".koOyOoooRRRrk..",
  ".koOOooooRRRrmk.",
  "koOoooRRRRRrrmpk",
  "kRoRRRRRrrrrmmpk",
  "kRRkrRRrkkrrmkpk",
  "kRk.krRk..krk.kk",
  ".k..krRk...k....",
  ".....kRk........"],
 ["", "", "", "",              # 4 sags, drips run long
  "....kkkkkkk.....",
  "..kkOyyOOookkk..",
  ".kOywwyOoooRRrk.",
  "koOOyOoooRRRRrmk",
  "koOoooRRRRRRrrmk",
  "kRoRRRRRRrrrrmpk",
  "kRRkrRRRrkkrmkpk",
  "kRk.krRRk.krk.kk",
  "kRk..kRrk..k....",
  ".k...kRk........"],
 ["", "",                      # 5 springs back up, narrow
  ".....kkkk.......",
  "....kOyyOkk.....",
  "...kOywWyOokk...",
  "..kOywWyOooRk...",
  "..kOywyOOoRRrk..",
  ".koOOOoooRRRrmk.",
  ".koOoooRRRRrrmk.",
  "kRoRRRRRrrrrmmpk",
  "kRRkrRRrkkrrmkpk",
  "kRk.krRk..krk.kk",
  ".k...kRk...k....",
  "......k........."],
]
# one steam puff through its life, {row: pixels}; a frame shows two puffs half a life apart
PUFF = [
 {15: "..........sS", 16: ".........sssS", 17: "..........sS"},
 {11: ".........ss", 12: "........ssssS", 13: "........sssSS", 14: ".........sSS"},
 {7: ".......sss", 8: "......ssssS", 9: "......sss.sS", 10: ".......sSsSS", 11: ".........S"},
 {4: ".....ss.s", 5: "....sss.sS", 6: "....ss...sS", 7: ".....sS.SS", 8: ".......S"},
 {1: "....s..s", 2: "...s.s..S", 3: "...s....S", 4: "....S..S"},
 {0: "...s...S", 1: "..s.....s", 2: ".....S"},
]
A_WADS = [0, 1, 1, 2, 2, 3, 4, 4, 5, 0, 0, 0]
A_MS = [90, 90, 90, 90, 110, 60, 80, 80, 80, 90, 90, 90]

def a_cell(i):
    im = Image.new("RGBA", (16, 32), (0, 0, 0, 0))
    for ph in (i % 6, (i + 3) % 6):
        rows = [PUFF[ph].get(y, "") for y in range(18)]
        im.alpha_composite(cell(16, 32, rows))
    im.alpha_composite(cell(16, 32, WAD[A_WADS[i]], 18))
    return im

# ---------------- C: see-through hot shell around the bird, 32x32, two sprite columns, two tiles ----------------
RIM0 = [(12, "kkkkkkkk", ""), (10, "kkyyyyooRRkk", ""), (8, "kkywwyy", "ooRRrkk"), (7, "kywwy", "oRrk"), (6, "kywy", "Rrk"),
        (5, "kywy", "Rrk"), (4, "kywy", "Rrk"), (4, "kyy", "rrk"), (3, "kyy", "Rrk"), (3, "kOy", "rrk"), (2, "kOy", "Rrk"),
        (2, "kOO", "rrk"), (2, "kOo", "rmk"), (2, "kOo", "rmk"), (2, "koo", "rmk"), (2, "koo", "mmk"), (2, "koR", "mmk"),
        (2, "kRR", "mpk"), (3, "kRR", "mpk"), (3, "kRr", "mpk"), (4, "kRr", "mpk"), (4, "kRrr", "mmpk"), (5, "kRrr", "mmpk"),
        (6, "kkrrr", "mmppk"), (7, "kkrrrm", "mmppkk"), (8, "kkrrmmmm", "mmpppPkk"), (10, "kkmmmpppPPkk", ""),
        (12, "kkkkkkkk", "")]
RIM_WIDE = [(11, "kkkkkkkkkk", ""), (8, "kkkyyyyy", "ooRRRkkk"), (6, "kkywwwy", "oRRrrkk"), (5, "kywwy", "oRrk"),
            (4, "kywy", "Rrk"), (3, "kywy", "Rrk"), (2, "kyy", "rrk"), (2, "kOy", "Rrk"), (1, "kOy", "rrk"), (1, "kOO", "rmk"),
            (1, "kOo", "rmk"), (1, "koo", "rmk"), (1, "koo", "mmk"), (1, "koR", "mmk"), (1, "kRR", "mpk"), (1, "kRR", "mpk"),
            (2, "kRr", "mpk"), (2, "kRrr", "mmpk"), (3, "kRrr", "mmpk"), (4, "kkrrr", "mmppk"), (5, "kkrrrm", "mmppkk"),
            (6, "kkkrrmmmmm", "mmmppPPkkk"), (8, "kkkmmmppppPPPkkk", ""), (11, "kkkkkkkkkk", "")]
RIM_TALL = [(12, "kkkkkkkk", ""), (10, "kkyyyyoRRRkk", ""), (9, "kkywwy", "oRRrkk"), (8, "kywwy", "oRrk"), (7, "kywwy", "Rrk"),
            (6, "kywy", "Rrk"), (6, "kywy", "Rrk"), (5, "kywy", "Rrk"), (5, "kyy", "rrk"), (4, "kyy", "Rrk"), (4, "kOy", "rrk"),
            (4, "kOy", "Rrk"), (3, "kOO", "rrk"), (3, "kOo", "rmk"), (3, "kOo", "rmk"), (3, "koo", "rmk"), (3, "koo", "mmk"),
            (3, "koR", "mmk"), (4, "kRR", "mpk"), (4, "kRR", "mpk"), (4, "kRr", "mpk"), (5, "kRr", "mpk"), (5, "kRrr", "mmpk"),
            (6, "kRrr", "mmpk"), (6, "kkrr", "mppk"), (7, "kkrrr", "mmppk"), (8, "kkrrrm", "mmppkk"), (9, "kkrrmmm", "mmppPkk"),
            (10, "kkmmmpppPPkk", ""), (12, "kkkkkkkk", "")]
# (rim, y0, inside marks (y, x, pixels): gloss top left, checker shade bottom right)
C = [
 (RIM0, 2, [(6, 9, "WW"), (7, 8, "WwW"), (8, 8, "Ww"), (9, 7, "w"), (11, 7, "w"), (19, 20, "r.r.r.r"), (20, 19, "r.r.r.r."),
            (21, 20, "r.r.r.r"), (22, 19, "r.r.r.r"), (23, 18, "r.r.r.r"), (24, 17, "r.r.r.r"), (25, 16, "r.r.r.r")]),
 (RIM_WIDE, 6, [(9, 8, "WWW"), (10, 7, "WwwW"), (11, 6, "Ww"), (13, 5, "w"), (20, 20, "r.r.r.r.r"), (21, 19, "r.r.r.r.r"),
                (22, 20, "r.r.r.r"), (23, 19, "r.r.r.r"), (24, 18, "r.r.r.r"), (25, 17, "r.r.r.r"), (26, 16, "r.r.r.r")]),
 (RIM_TALL, 1, [(5, 10, "WW"), (6, 9, "Ww"), (7, 9, "Ww"), (8, 8, "Ww"), (9, 8, "w"), (12, 7, "w"), (20, 19, "r.r.r."),
                (21, 18, "r.r.r.r"), (22, 19, "r.r.r."), (23, 18, "r.r.r.r"), (24, 17, "r.r.r.r"), (25, 16, "r.r.r.r"),
                (26, 15, "r.r.r.r")]),
 (RIM0, 2, [(5, 11, "WW"), (6, 10, "WwW"), (7, 10, "w"), (9, 8, "w"), (18, 21, "r.r.r."), (19, 20, "r.r.r.r"),
            (20, 21, "r.r.r."), (21, 20, "r.r.r.r"), (22, 19, "r.r.r.r"), (23, 18, "r.r.r.r"), (24, 17, "r.r.r.r")]),
]
C_SEQ = [(0, 0, 0, 120), (1, 0, 0, 80), (3, 0, -1, 70), (2, 0, 0, 90), (0, 0, 1, 70), (1, 0, 1, 70), (3, 0, 0, 80),
         (2, 0, 1, 70), (0, 0, 0, 140)]

def c_cell(i):
    rim, y0, marks = C[i]
    im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    def put(x, y, s):
        for j, ch in enumerate(s):
            if ch != ".":
                assert 0 <= x + j < 32 and 0 <= y < 32, (i, x, y, s)
                im.putpixel((x + j, y), RGBA[ch])
    for y, x, s in marks:
        put(x, y, s)
    for r, (x0, left, right) in enumerate(rim):
        assert len(left) + len(right) <= 32 - 2 * x0, (i, r)
        put(x0, y0 + r, left)
        put(32 - x0 - len(right), y0 + r, right)
    return im

# ---------------- output ----------------
def up(im, n):
    return im.resize((im.width * n, im.height * n), Image.NEAREST)

def main():
    cells = {"A": [a_cell(i) for i in range(12)], "B": [cell(16, 16, g) for g in B], "C": [c_cell(i) for i in range(4)]}
    seqs = {"A": [(i, 0, 0, A_MS[i]) for i in range(12)], "B": B_SEQ, "C": C_SEQ}
    # anchor of the cell against the 24x32 flier cell origin: A drips over the crown, B rides above the balloon, C wraps the body
    anchor = {"A": (4, -11), "B": (4, -42), "C": (-7, 4)}
    for k, cs in cells.items():
        used = set()
        for c in cs:
            used |= {p for p in c.get_flattened_data() if p[3]} if hasattr(c, "get_flattened_data") else {p for p in c.getdata() if p[3]}
        assert len(used) <= 15, (k, len(used))
        print(k, "cells", len(cs), "size", cs[0].size, "colours", len(used), "frames", len(seqs[k]))
        w, h = cs[0].size
        sheet = Image.new("RGBA", (w * len(cs), h), (0, 0, 0, 0))
        for i, c in enumerate(cs):
            sheet.paste(c, (i * w, 0))
        sheet.save(os.path.join(HERE, f"sheet_{k}_1x.png"))
        bg = Image.new("RGBA", sheet.size, (58, 63, 92, 255)); bg.alpha_composite(sheet)
        up(bg, 4).save(os.path.join(HERE, f"sheet_{k}_4x.png"))
        fr = []
        for ci, dx, dy, ms in seqs[k]:
            f = Image.new("RGBA", (w + 8, h + 8), (58, 63, 92, 255)); f.alpha_composite(cs[ci], (4 + dx, 4 + dy))
            fr.append(up(f, 3).convert("P", palette=Image.ADAPTIVE, colors=32))
        fr[0].save(os.path.join(HERE, f"anim_{k}_3x.gif"), save_all=True, append_images=fr[1:], loop=0,
                   duration=[s[3] for s in seqs[k]], disposal=1)

    snap = Image.open(os.path.join(REPO, "build/test-snap/playing.png")).convert("RGBA")
    bx, by = 148, 131  # flier cell origin in that snapshot, placed by eye (not probed)
    for k, cs in cells.items():
        ax, ay = anchor[k]
        fr = []
        for ci, dx, dy, ms in seqs[k]:
            f = snap.copy(); f.alpha_composite(cs[ci], (bx + ax + dx, by + ay + dy)); fr.append(f)
        up(fr[2], 2).save(os.path.join(HERE, f"mockup_{k}_2x.png"))
        crop = [up(f.crop((bx - 60, by - 70, bx + 84, by + 50)), 4).convert("P", palette=Image.ADAPTIVE, colors=128) for f in fr]
        crop[0].save(os.path.join(HERE, f"mockup_{k}_anim_4x.gif"), save_all=True, append_images=crop[1:], loop=0,
                     duration=[s[3] for s in seqs[k]], disposal=1)
        full = [up(f, 2).convert("P", palette=Image.ADAPTIVE, colors=200) for f in fr]
        full[0].save(os.path.join(HERE, f"mockup_{k}_anim_2x.gif"), save_all=True, append_images=full[1:], loop=0,
                     duration=[s[3] for s in seqs[k]], disposal=1)

if __name__ == "__main__":
    main()
