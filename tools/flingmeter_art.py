"""Gum Fling meter art: hand-placed pixel grids copied unchanged from thoughts/shared/drafts/2026-11-20-fling-meter/draw_fling_meter.py
(owner pick C, 2026-11-20: quadrant angle dial + glass gum tube). Letters are palette entries of PINK / HOT (tools/build_flingmeter_tiles.py)."""
# one fix palette, 15 colours + transparent. First 12 = countdown A2 gum-tube palette (owner pick), + lime pair + yellow.
PINK = {"k": "#160826", "d": "#3c1266", "m": "#681a7c", "r": "#9c2088", "R": "#c82e90", "p": "#ee4c9c", "P": "#ff86b8",
        "l": "#ffb4cc", "w": "#ffe2dc", "W": "#ffffff", "v": "#9a5ae0", "V": "#c8a0f6",
        "L": "#a8e62c", "g": "#1f8a4c", "y": "#fff06a"}
# full-power flash: same tiles, second palette (countdown A2 "hot" column)
HOT = dict(PINK, r="#c0201e", R="#e63a1e", p="#ff7a1a", P="#ffa922", l="#ffdc4a", w="#fff3b0")
assert len(PINK) == 15

def tube(top, body, bot):
    rows = ["........", "........", "kkkkkkkk", top] + body + [bot, "kkkkkkkk", "k.k.k.k.", "........"]
    assert len(rows) == 16 and all(len(r) == 8 for r in rows), rows
    return rows

# ---------- option A: gum tube ----------
GUM_A = tube("VVVVVVVV", ["PPPPPPPP", "llllllll", "wwlwwwlw", "PlPPlPPl", "pppppppp", "pRppRppp", "RRRrRRRr", "rmrrmrrv"], "vmvvmvvm")
GUM_B = tube("VWWVVVVV", ["PPPPPPPP", "llwlllll", "wWWwlwww", "lPPlPPlP", "pppppppp", "ppRppRpR", "RrRRRrRR", "mrrvmrrm"], "mvvmvvmv")
EMPTY = tube("vvvvvvvv", ["mmmmmmmm", "dddddddd", "dddkdddd", "kdkdkdkd", "kkkkkkkk", "kkdkkkdk", "dkdkdkdk", "dddmdddd"], "mmmmmmmm")
EMPTY_TICK = tube("vvvvvvvv", ["vmmmmmmm", "vddddddd", "vddkdddd", "kdkdkdkd", "kkkkkkkk", "kkdkkkdk", "dkdkdkdk", "dddmdddd"], "mmmmmmmm")
EMPTY_MAJOR = tube("Vvvvvvvv", ["Vmmmmmmm", "Vddddddd", "Vddkdddd", "Vdkdkdkd", "vkkkkkkk", "kkdkkkdk", "dkdkdkdk", "dddmdddd"], "mmmmmmmm")
FRONT8 = tube("VVVVVvvv", ["PPPPPrmm", "llllllPr", "wwlwwWlR", "PlPPlPPR", "pppppppR", "pRppRppr", "RRRrRrmd", "rmrrmmdd"], "vmvvmmmm")
FRONT4 = tube("VVvvvvvv", ["PPrmmmmm", "llPrdddd", "wWlRdddd", "PlPRkdkd", "pppRkkkk", "pRprkkdk", "Rrmdkdkd", "rmdddddd"], "vmmmmmmm")
CAP_L = ["........", "....kkk.", "..kkVWVk", ".kVVWVvk", ".kVWVvmk", "kVWVvvmk", "kVVvvmdk", "kVvvmmdk",
         "kvvmmddk", "kvmmdddk", "kvmmdmvk", ".kmddmvk", ".kmdmvVk", "..kkmvvk", "....kkk.", "........"]
CAP_R = ["........", ".kkk....", "kVVVkk..", "kVWVvvk.", "kVVvvmk.", "kVvvmmdk", "kvvmmddk", "kvmmdddk",
         "kvmddddk", "kmdddmdk", "kmddmvmk", "kmdmvvk.", "kdmvVvk.", "kkmvkk..", ".kkk....", "........"]
GUM_ORDER = "ABAABABBAABABAAB"   # hand order of the two gum cells
# angle rail in the same tube: safe zone lime, foul ends pink hazard hatch, chrome slider knob
# ---------- option C: angle dial (24 x 24, pivot bottom-left) ----------
DIAL = [
    "........................",
    ".kkkkkk.................",
    ".kPPPPPkkk..............",
    ".kRRRRRLLLkk............",
    ".kdddddgggLLkk..........",
    ".k" + "ddkddddd" + "ggLLk" + ".........",
    ".k" + "dddddkdddd" + "gLLk" + "........",
    ".k" + "dkddddddkdd" + "gLLk" + ".......",
    ".k" + "dddkdddddddd" + "gLLk" + "......",
    ".k" + "ddddddkdddkdd" + "gLLk" + ".....",
    ".k" + "dkdddddddddddd" + "gLLk" + "....",
    ".k" + "ddddkdddkdddddd" + "gLk" + "....",
    ".k" + "dddddddddddkdddd" + "gLk" + "...",
    ".k" + "ddkdddddkddddddd" + "gLk" + "...",
    ".k" + "dddddkddddddkdddd" + "gLk" + "..",
    ".k" + "ddddddddkdddddddd" + "gLk" + "..",
    ".k" + "dkddddddddddkdddd" + "gLk" + "..",
    ".k" + "ddddkddddddddddddd" + "RPk" + ".",
    ".k" + "dddddddkdddddkdddd" + "RPk" + ".",
    ".k" + "ddkddddddddddddddd" + "RPk" + ".",
    ".k" + "ddddddddddkddddkdd" + "RPk" + ".",
    ".k" + "dddddkdddddddddddd" + "RPk" + ".",
    "." + "k" * 22 + ".",
    "..k.k.k.k.k.k.k.k.k.k.k.",
]
assert len(DIAL) == 24 and all(len(r) == 24 for r in DIAL), [len(r) for r in DIAL]
# needle pixels (dx, dy) from the pivot, hand-placed pixel-art line runs; steeper four are the diagonal mirror
N = {
    0: [(1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0), (7, 0), (8, 0), (9, 0), (10, 0), (11, 0), (12, 0), (13, 0), (14, 0), (15, 0)],
    11: [(1, 0), (2, 0), (3, 0), (4, 1), (5, 1), (6, 1), (7, 1), (8, 2), (9, 2), (10, 2), (11, 2), (12, 3), (13, 3), (14, 3), (15, 3)],
    27: [(1, 0), (2, 1), (3, 1), (4, 2), (5, 2), (6, 3), (7, 3), (8, 4), (9, 4), (10, 5), (11, 5), (12, 6), (13, 6), (14, 7)],
    35: [(1, 1), (2, 1), (3, 2), (4, 3), (5, 3), (6, 4), (7, 5), (8, 5), (9, 6), (10, 7), (11, 7), (12, 8), (13, 9)],
    45: [(1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 6), (7, 7), (8, 8), (9, 9), (10, 10), (11, 11)],
}
for a, b in ((55, 35), (63, 27), (79, 11), (90, 0)):
    N[a] = [(y, x) for x, y in N[b]]
HUB = {(0, 0): "W", (1, 0): "V", (0, 1): "V", (1, 1): "v"}

# ---------- label plaques (5 px letters) ----------
FONT = {
    "P": ["www.", "w..w", "www.", "w...", "w..."], "O": [".ww.", "w..w", "w..w", "w..w", ".ww."],
    "W": ["w...w", "w...w", "w.w.w", "ww.ww", "w...w"], "E": ["wwww", "w...", "www.", "w...", "wwww"],
    "R": ["www.", "w..w", "www.", "w.w.", "w..w"], "A": [".ww.", "w..w", "wwww", "w..w", "w..w"],
    "N": ["w..w", "ww.w", "w.ww", "w..w", "w..w"], "G": [".www", "w...", "w.ww", "w..w", ".www"],
    "L": ["w...", "w...", "w...", "w...", "wwww"],
}
PLAQUE = ["................................", "................................", "................................",
          ".kkkkkkkkkkkkkkkkkkkkkkkkkkkkkk.", "kmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmk", "kddddddddddddddddddddddddddddddk",
          "kddddddddddddddddddddddddddddddk", "kddddddddddddddddddddddddddddddk", "kddddddddddddddddddddddddddddddk",
          "kddddddddddddddddddddddddddddddk", "kddddddddddddddddddddddddddddddk", "kdkdkdkdkdkdkdkdkdkdkdkdkdkdkdkk",
          ".kkkkkkkkkkkkkkkkkkkkkkkkkkkkkk.", "..k.k.k.k.k.k.k.k.k.k.k.k.k.k...", "................................", "................................"]
assert all(len(r) == 32 for r in PLAQUE) and len(PLAQUE) == 16

def blit(cv, x, y, rows):
    for j, r in enumerate(rows):
        for i, c in enumerate(r):
            if c != ".": cv[y + j][x + i] = c

def label(cv, x, y, word):
    blit(cv, x, y, PLAQUE)
    w = sum(len(FONT[c][0]) for c in word) + len(word) - 1
    cx = x + (32 - w) // 2
    for c in word:
        blit(cv, cx, y + 6, FONT[c]); cx += len(FONT[c][0]) + 1

