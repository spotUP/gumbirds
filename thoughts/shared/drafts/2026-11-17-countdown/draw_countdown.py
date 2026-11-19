#!/usr/bin/env python3
"""Gum Games countdown word drafts: GET SET / GO! in three styles (A gum tube, B neon sign, C molten slab).
Hand-placed pixel data only: every glyph is typed row by row (a repeated row is written as [row] * n).
Nothing is drawn from a shape, font or gradient formula. The GO! pop-in only moves and shrinks the finished
sprite (Neo Geo hardware shrink + position), it adds no tiles.
Writes PNGs, GIFs, index.html and README.md next to this script.
Run: python3.14 -I draw_countdown.py
"""
import os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PLATE = os.path.join(HERE, "..", "2026-11-10-backgrounds-final", "compare_dusk_2x.png")  # right half = final dusk scene at 2x

# ---------------- A: gum tube, 32 px high. Each stroke is a glossy tube lit from the top left ----------------
PAL_A = {"k": "1c0a30", "m": "7a1a78", "v": "a45ad8", "r": "c02a86", "p": "f0509c", "P": "ff86b8", "l": "ffb8cc",
         "w": "ffe6dc", "W": "ffffff"}
# same grids in the Hot Gum bubble colours (palette swap only, no new tiles)
PAL_A_HOT = {"k": "080818", "m": "8a1430", "v": "d42a7a", "r": "d8301e", "p": "ff7a1a", "P": "ffa922", "l": "ffdc4a",
             "w": "fff3b0", "W": "ffffff"}
A_O_TOP = [
 "......kkkkkkkkkkkk......",
 "....kkPPPPPPPPPPPPkk....",
 "...kPPllWWWwlllllPPpk...",
 "..kPPlWWwPPPPPPPPPPprk..",
 ".kPPlwwPPPPPPPPPPPPpprk.",
 ".kPllPPPpPpPppppprprrrk."]
A_O_BOTTOM = [
 "kPlPprmkkkkkkkkkkPlPprmk",
 "kPlPprPPPPPPPPPPPPlPprmk",
 "kPlPpPlllllllllllllPprmk",
 ".kPlPPPPPPPPPPPPPPPpprk.",
 ".kPPlPppppppppppppprrmk.",
 "..kPPpprrrrrrrrrrrrmmk..",
 "...kpprrmmmvvvvmmmmmk...",
 "....kkrmmmmvvvmmmmkk....",
 "......kkkkkkkkkkkk......"]
A = {
 "E": [
 "..kkkkkkkkkkkkkkkkkk..",
 ".kPPPPPPPPPPPPPPPPPPk.",
 "kPlllWWWwllllllllllPrk",
 "kPlPPwwPPPPPPPPPPPPprk",
 "kPlPpPpPppppppprprprrk",
 "kPlPprprrrrrrrrmrmrmmk",
 "kPlPprmmmmmmvvvvmmmmk.",
 "kPlPprmkkkkkkkkkkkkk.."] + ["kPlPprmk.............."] * 4 + [
 "kPlPprmkkkkkkkkkkk....",
 "kPlPprPPPPPPPPPPPPk...",
 "kPlPpPlllllllllllPrk..",
 "kPlPPPPPPPPPPPPPPprk..",
 "kPlPpppppppppppppprk..",
 "kPlPprrrrrrrrrrrrrmk..",
 "kPlPprmmmmvvvmmmmmk...",
 "kPlPprmkkkkkkkkkkk...."] + ["kPlPprmk.............."] * 4 + [
 "kPlPprmkkkkkkkkkkkkk..",
 "kPlPprPPPPPPPPPPPPPPk.",
 "kPlPpPlllllllllllllPrk",
 "kPlPPPPPPPPPPPPPPPPprk",
 "kPlPpppppppppppppppprk",
 "krPprrrrrrrrrrrrrrrrmk",
 ".krmmmvvvvmmmmmmvvmmk.",
 "..kkkkkkkkkkkkkkkkkk.."],
 "T": [
 "..kkkkkkkkkkkkkkkkkk..",
 ".kPPPPPPPPPPPPPPPPPPk.",
 "kPlllWWWwllllllllllPrk",
 "kPlPPwwPPPPPPPPPPPPprk",
 "kPPppppppppppppppppprk",
 "kPprrrrrPlPprrrrrrrrmk",
 ".krmvvmmPlPprmmmvvvmk.",
 "..kkkkkkPlPprmkkkkkk.."] + [".......kPWPprmk......."] * 3 + [".......kPlPprmk......."] * 9 + [
 ".......kPlpPrmk.......",
 ".......kPlPprmk.......",
 ".......kPlpprmk.......",
 ".......kPlpprmk.......",
 ".......kPlprpmk.......",
 ".......kPlpprmk.......",
 ".......kPPprrmk.......",
 ".......kPPprrmk.......",
 ".......kPPprrmk.......",
 ".......kPpprmmk.......",
 ".......krrmmvmk.......",
 "........kkkkkk........"],
 "O": A_O_TOP + [
 "kPPlPPpprrrrrrrrrpppprmk",
 "kPlPPprrmmmmmmmmmrPPprmk",
 "kPlPprmmkkkkkkkkmPlPprmk",
 "kPlPprmkk......kkPlPprmk"] + ["kPlPprmk........kPlPprmk"] * 12 + [
 "kPlPprmkk......kkPlPprmk"] + A_O_BOTTOM,
 "G": A_O_TOP + [
 "kPPlPPpprrrrrrrrrrrrrmmk",
 "kPlPPprrmmmmmmmmmmmmmmk.",
 "kPlPprmmkkkkkkkkkkkkkk..",
 "kPlPprmkk...............",
 "kPlPprmk................",
 "kPlPprmk................",
 "kPlPprmk................",
 "kPlPprmk..kkkkkkkkkkkk..",
 "kPlPprmk.kPPPPPPPPPPPPk.",
 "kPlPprmk.kPllllllllllPrk",
 "kPlPprmk.kPPWwPPPPPPPprk",
 "kPlPprmk.kpppppppPlPprmk",
 "kPlPprmk.krrrrrrrPlPprmk",
 "kPlPprmk..kmmmmmmPlPprmk",
 "kPlPprmk...kkkkkkPlPprmk",
 "kPlPprmk........kPlPprmk",
 "kPlPprmkk......kkPlPprmk"] + A_O_BOTTOM,
 "S": [
 "......kkkkkkkkkkkkkkk...",
 "....kkPPPPPPPPPPPPPPPkk.",
 "...kPPllWWWwlllllllllPrk",
 "..kPPlWWwPPPPPPPPPPPPprk",
 ".kPPlwwPPPPpppppppppprrk",
 ".kPllPPPpprrrrrrrrrrrrmk",
 "kPPlPPpprrmmmmmmmmmmmmk.",
 "kPlPPprrmkkkkkkkkkkkkk..",
 "kPlPprmkk...............",
 "kPlPprmk................",
 "kPlPprmk................",
 "kPlPprmkk...............",
 "kPlPPprmkkkkkkkkkkkk....",
 "kPPlPPpPPPPPPPPPPPPPkk..",
 ".kPPlPPlllllllllllllPPk.",
 ".kPPPllPPPPPPPPPPPPPPprk",
 "..kpPPPPpppppppppPlPprmk",
 "...kprrrrrrrrrrrrPlPprmk",
 "....kkrmmmmmmmmmmPlPprmk",
 "......kkkkkkkkkkkPlPprmk",
 "...............kkPlPprmk",
 "................kPlPprmk",
 "................kPlPprmk",
 "..kkkkkkkkkkkkkkkPlPprmk",
 ".kPPPPPPPPPPPPPPPPlPprmk",
 "kPPllllllllllllllllPprmk",
 "kPlWwPPPPPPPPPPPPPPpprk.",
 "kPPPpppppppppppppprrrmk.",
 ".kpprrrrrrrrrrrrrrrmmk..",
 ".krrmmmmvvvvmmmmmmmmk...",
 "..kkmmmmmmmmmmmmmmkk....",
 "....kkkkkkkkkkkkkk......"],
 "!": [
 "..kkkkkk..", ".kPPPPPPk.", "kPlWWwPprk", "kPlWwPPprk", "kPlwPPpprk", "kPlPPPprmk", "kPlPPpprmk", "kPlPPprrmk",
 "kPlPPprrmk", "kPlPpprrmk", "kPlPpprmmk", ".kPlPprmk.", ".kPlPprmk.", ".kPlpprmk.", ".kPlprrmk.", ".kPPprmmk.",
 "..kPprmk..", "..kPprmk..", "..kpprmk..", "..kprrmk..", "..krmvmk..", "...kkkk...", "..........", "..kkkkkk..",
 ".kPPPPPPk.", "kPlWwPPprk", "kPlwPPpprk", "kPlPPpprmk", "kPPppprrmk", "kpprrrmvmk", ".krmmvvmk.", "..kkkkkk.."],
}

# ---------------- B: neon sign tube, 32 px high. Same grids, cyan palette for GET SET, pink for GO! ----------------
PAL_B_CYAN = {"k": "0c0a24", "d": "0a5a90", "c": "22c0e8", "W": "e8ffff"}
PAL_B_PINK = {"k": "0c0a24", "d": "a01870", "c": "ff5cb0", "W": "fff0f8"}
B_O_TOP = [
 "....kkkkkkkkkkkk....",
 "..kkddddddddddddkk..",
 ".kddccccccccccccddk.",
 "kddccWWWWWWWWWWccddk",
 "kdccWWccccccccWWccdk",
 "kdcWWccddddddccWWcdk",
 "kdcWccddkkkkddccWcdk"]
B_O_BOTTOM = [
 "kdcWcddk....kddcWcdk",
 "kdcWccddkkkkddccWcdk",
 "kdcWWccddddddccWWcdk",
 "kdccWWccccccccWWccdk",
 "kddccWWWWWWWWWWccddk",
 ".kddccccccccccccddk.",
 "..kkddddddddddddkk..",
 "....kkkkkkkkkkkk...."]
B = {
 "E": [
 ".kkkkkkkkkkkkkkkkkk.",
 "kddddddddddddddddddk",
 "kdccccccccccccccccdk",
 "kdcWWWWWWWWWWWWWWcdk",
 "kdcWccccccccccccccdk",
 "kdcWcddddddddddddddk",
 "kdcWcdkkkkkkkkkkkkk."] + ["kdcWcdk............."] * 5 + [
 "kdcWcdkkkkkkkkkkk...",
 "kdcWcddddddddddddk..",
 "kdcWccccccccccccdk..",
 "kdcWWWWWWWWWWWWcdk..",
 "kdcWccccccccccccdk..",
 "kdcWcddddddddddddk..",
 "kdcWcdkkkkkkkkkkk..."] + ["kdcWcdk............."] * 6 + [
 "kdcWcdkkkkkkkkkkkkk.",
 "kdcWcddddddddddddddk",
 "kdcWccccccccccccccdk",
 "kdcWWWWWWWWWWWWWWcdk",
 "kdccccccccccccccccdk",
 "kddddddddddddddddddk",
 ".kkkkkkkkkkkkkkkkkk."],
 "T": [
 ".kkkkkkkkkkkkkkkkkkk.",
 "kdddddddddddddddddddk",
 "kdcccccccccccccccccdk",
 "kdcWWWWWWWWWWWWWWWcdk",
 "kdccccccccWccccccccdk",
 "kddddddddcWcddddddddk",
 ".kkkkkkkdcWcdkkkkkkk."] + [".......kdcWcdk......."] * 22 + [
 ".......kdcccdk.......",
 ".......kdddddk.......",
 "........kkkkk........"],
 "O": B_O_TOP + ["kdcWcddk....kddcWcdk"] + ["kdcWcdk......kdcWcdk"] * 16 + B_O_BOTTOM,
 "G": B_O_TOP + [
 "kdcWcddk....kddcccdk",
 "kdcWcdk......kdddddk",
 "kdcWcdk.......kkkkk."] + ["kdcWcdk............."] * 4 + [
 "kdcWcdk...kkkkkkkkk.",
 "kdcWcdk..kdddddddddk",
 "kdcWcdk..kdcccccccdk",
 "kdcWcdk..kdcWWWWWcdk",
 "kdcWcdk..kdcccccWcdk",
 "kdcWcdk..kdddddcWcdk",
 "kdcWcdk...kkkkdcWcdk"] + ["kdcWcdk......kdcWcdk"] * 3 + B_O_BOTTOM,
 "S": [
 "....kkkkkkkkkkkkkk..",
 "..kkddddddddddddddk.",
 ".kddcccccccccccccddk",
 "kddccWWWWWWWWWWWWcdk",
 "kdccWWcccccccccccddk",
 "kdcWWccdddddddddddk.",
 "kdcWccddkkkkkkkkkk..",
 "kdcWcddk............"] + ["kdcWcdk............."] * 3 + [
 "kdcWcddk............",
 "kdcWccddkkkkkkkkk...",
 "kdcWWccdddddddddkk..",
 "kdccWWccccccccccddk.",
 ".kddccWWWWWWWWWccddk",
 "..kddcccccccccWWccdk",
 "...kkddddddddccWWcdk",
 ".....kkkkkkkddccWcdk",
 "............kddcWcdk"] + [".............kdcWcdk"] * 4 + [
 "............kddcWcdk",
 "..kkkkkkkkkkddccWcdk",
 ".kdddddddddddccWWcdk",
 "kddcccccccccccWWccdk",
 "kdcWWWWWWWWWWWWccddk",
 "kddcccccccccccccddk.",
 ".kddddddddddddddkk..",
 "..kkkkkkkkkkkkkk...."],
 "!": [".kkkkkkk.", "kdddddddk", "kdcccccdk"] + ["kdcWWWcdk"] * 7 + ["kdccWccdk"] + [".kdcWcdk."] * 7 + [
 ".kdcccdk.", ".kdddddk.", "..kkkkk..", ".........", ".........", "..kkkkk..", ".kdddddk.", "kddcccddk", "kdccWccdk",
 "kdcWWWcdk", "kdccWccdk", "kddcccddk", ".kdddddk.", "..kkkkk.."],
}

# ---------------- C: molten slab, 40 px high. Hot Gum bubble palette (draft 2026-11-16-gum-bubble) ----------------
PAL_C = {"k": "080818", "m": "6b0f2e", "r": "b3182e", "R": "e63a1e", "o": "ff7a1a", "O": "ffa922", "y": "ffdc4a",
         "w": "fff3b0", "W": "ffffff"}
C_O_TOP = [
 "...kkkkkkkkkkkkkkkkkk...",
 "..kwwwwwwwwwwwwwwwwwwk..",
 ".kwyyWWyyyyyyyyyyyyyyOk.",
 "kwyyWWyyyyyyyyyyyyyyyyOk",
 "kwyyWyyyyyyyyyyyyyyyyyOk",
 "kwyyyyyyyyyOyyyyyyyOyyOk",
 "kwyyOyyOOOyyOOyOOyyyOyOk",
 "kyyOOOOOOOOOOOOOOOyOOOok",
 "kyOOOOOokkkkkkkkyOOOOOok"]
C_BOTTOM = [
 "koRRRRRRRRRRRRRRRRRRRRrk",
 "koRRRrRRRRrRRRRRrRRRRrrk",
 "kRRrrRrrRrrrRrrRrrRrrrmk",
 "kRrrrrrrrrrrrrrrrrrrrrmk",
 ".krrrrrrrrrrrrrrrrrrmmk.",
 "..kmmmmmmmmmmmmmmmmmmk..",
 "...kkkkkkkkkkkkkkkkkk..."]
C_O_LOW = [
 "kOooRooRk......kOoRoooRk",
 "koRRoRRrk......koRoRRRrk"] + ["koRRRRRrk......koRRRRRrk"] * 3 + [
 "koRRRRRrkkkkkkkkoRRRRRrk",
 "koRRRRRRooooooooRRRRRRrk"] + C_BOTTOM
C = {
 "E": [
 ".kkkkkkkkkkkkkkkkkkkk.",
 "kwwwwwwwwwwwwwwwwwwwwk",
 "kwyyyWWyyyyyyyyyyyyyOk",
 "kwyyWWyyyyyyyyyyyyyyOk",
 "kwyyyyyyyyyyyyyyyyyyOk",
 "kwyyyyyyyyyOyyyyyyOyOk",
 "kwyyyOyyyOOOyyOyOOOyOk",
 "kyyOOOOyOOOOOOOOOOOOok",
 "kyOOOOOokkkkkkkkkkkkk."] + ["kyOOOOOok............."] * 6 + [
 "kyOOOOOokkkkkkkkkkk...",
 "kyOOoOOOyyyyyyyyyyk...",
 "kyOoOooOOOOoOOOOOok...",
 "kOooOoooooOooooOoRk...",
 "kOoooooooooooooooRk...",
 "kOoooooooooooooooRk...",
 "kOoooooooooooooooRk...",
 "kOoooooooRRRRRRRRRk...",
 "kOoooooRkkkkkkkkkkk...",
 "kOoooooRk.............",
 "kOoooooRk.............",
 "kOooRooRk.............",
 "koRRoRRrk.............",
 "koRRRRRrk.............",
 "koRRRRRrk.............",
 "koRRRRRrk.............",
 "koRRRRRrkkkkkkkkkkkkk.",
 "koRRRRRRoooooooooooork",
 "koRRRRRRRRRRRRRRRRRRrk",
 "koRRRrRRRRrRRRRrRRRRrk",
 "kRRrrRrrRrrrRrrRrrrrmk",
 "kRrrrrrrrrrrrrrrrrrrmk",
 "kRrrrrrrrrrrrrrrrrrmmk",
 "krmmmmmmmmmmmmmmmmmmmk",
 ".kkkkkkkkkkkkkkkkkkkk."],
 "T": [
 ".kkkkkkkkkkkkkkkkkkkkk.",
 "kwwwwwwwwwwwwwwwwwwwwwk",
 "kwyyyWWyyyyyyyyyyyyyyOk",
 "kwyyWWyyyyyyyyyyyyyyyOk",
 "kwyyyyyyyyyyyyyyyyyyyOk",
 "kwyyyyOyyyyyyyyOyyyyyOk",
 "kwyOyOOOyyyOyyOOOyyOyOk",
 "kyOOOOOOOyOOOOOOOOOOOok",
 ".kkkkkkkyOOOOOokkkkkkk.",
 ".......kyWOOOOok.......",
 ".......kyWOOOOok.......",
 ".......kyyOOOOok......."] + [".......kyOOOOOok......."] * 4 + [
 ".......kyOOoOOok.......",
 ".......kOOoOooRk......."] + [".......kOoooooRk......."] * 8 + [
 ".......kOooRooRk.......",
 ".......koRRoRRrk......."] + [".......koRRRRRrk......."] * 6 + [
 ".......koRRrRRrk.......",
 ".......kRrrRrrmk.......",
 ".......kRrrrrrmk.......",
 ".......kRrrrrmmk.......",
 ".......krmmmmmmk.......",
 "........kkkkkkk........"],
 "O": C_O_TOP + ["kyOOOOOok......kyOOOOOok"] * 7 + [
 "kyOOoOOok......kyOoOOOok",
 "kOOoOooRk......kOoOOooRk"] + ["kOoooooRk......kOoooooRk"] * 8 + C_O_LOW,
 "G": C_O_TOP + [
 "kyOOOOOok......kyOOOOOok",
 "kyOOOOOok......kyOOOOook",
 "kyOOOOOok......koooooook",
 "kyOOOOOok.......kkkkkkk.",
 "kyOOOOOok...............",
 "kyOOOOOok...............",
 "kyOOOOOok...............",
 "kyOOoOOok...............",
 "kOOoOooRk...kkkkkkkkkkk.",
 "kOoooooRk..kOOOOOOOOOOOk",
 "kOoooooRk..kOoooooooooRk",
 "kOoooooRk..kOoooooooooRk",
 "kOoooooRk..kOoooooooooRk",
 "kOoooooRk..kORRROoooooRk",
 "kOoooooRk...kkkkOoooooRk",
 "kOoooooRk......kOoooooRk",
 "kOoooooRk......kOoooooRk"] + C_O_LOW,
 "S": [
 "...kkkkkkkkkkkkkkkkkkk..",
 "..kwwwwwwwwwwwwwwwwwwwk.",
 ".kwyyWWyyyyyyyyyyyyyyyOk",
 "kwyyWWyyyyyyyyyyyyyyyyOk",
 "kwyyWyyyyyyyyyyyyyyyyyOk",
 "kwyyyyyyyyyOyyyyyyyOyyOk",
 "kwyyOyyOOOyyOOyOOyyyOyOk",
 "kyyOOOOOOOOOOOOOOOyOOook",
 "kyOOOOOokkkkkkkkkkkkkkk."] + ["kyOOOOOok..............."] * 6 + [
 "kyOOOOOokkkkkkkkkkkkk...",
 "kyOOoOOOyyyyyyyyyyyyyk..",
 "kOOoOooOOOoOOOOoOOOOOOk.",
 "kOooooooooooooooooooooRk",
 ".kOoooooooooooooooooooRk",
 ".kOoooooooooooooooooooRk",
 "..kOooooooooooooOoooooRk",
 "...kRRRRRRRRRRRROoooooRk",
 "....kkkkkkkkkkkkOoooooRk",
 "...............kOoooooRk",
 "...............kOoooooRk",
 "...............kOoRoooRk",
 "...............koRoRRRrk",
 "...............koRRRRRrk",
 "...............koRRRRRrk",
 "...............koRRRRRrk",
 ".kkkkkkkkkkkkkkkoRRRRRrk",
 "koooooooooooooooRRRRRRrk"] + C_BOTTOM,
 "!": [
 ".kkkkkkkkk.", "kwwwwwwwwwk", "kwyWWyyyyOk", "kwyWWyyyyOk", "kwyWyyyyyOk", "kwyyyyyOyOk", "kwyOyOOyOOk",
 "kyOOOOyOOok"] + ["kyOOOOOOOok"] * 6 + [".kyOOOOOok.", ".kyOOOOOok.", ".kyOoOOook.", ".kOoOoooRk."] + [
 ".kOoooooRk."] * 4 + ["..kOoooRk..", "..kOoooRk..", "..kOoRoRk..", "..koRRRrk..", "..koRRRrk..", "..kRRrrmk..",
 "...kkkkk...", "...........", "...........", "..kkkkkkk..", ".koooooook.", "koRRRRRRRrk", "koRoRRRrRrk",
 "kRRrRrrRrmk", "kRrrrrrrrmk", "kRrrrrrrmmk", ".krmmmmmmk.", "..kkkkkkk.."],
}

OPTIONS = [  # key, title, glyphs, height, palette for GET SET, palette for GO!
 ("A", "A - Gum tube (pink, 32 px)", A, 32, PAL_A, PAL_A),
 ("A-hot", "A-hot - same grids as A in the Hot Gum colours (palette swap)", A, 32, PAL_A_HOT, PAL_A_HOT),
 ("B", "B - Neon sign (cyan GET SET, pink GO!, 32 px)", B, 32, PAL_B_CYAN, PAL_B_PINK),
 ("C", "C - Molten slab (40 px)", C, 40, PAL_C, PAL_C),
]
GAP, SPACE = 2, 12

def rgba(pal):
    return {c: tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (255,) for c, h in pal.items()}

def glyph(rows, pal):
    lut = rgba(pal)
    im = Image.new("RGBA", (len(rows[0]), len(rows)), (0, 0, 0, 0))
    for y, row in enumerate(rows):
        for x, c in enumerate(row):
            if c != ".":
                im.putpixel((x, y), lut[c])
    return im

def word(text, glyphs, pal):
    parts, w = [], 0
    for ch in text:
        if ch == " ":
            w += SPACE - GAP
            continue
        g = glyph(glyphs[ch], pal)
        parts.append((w, g))
        w += g.width + GAP
    im = Image.new("RGBA", (w - GAP, parts[0][1].height), (0, 0, 0, 0))
    for x, g in parts:
        im.paste(g, (x, 0))
    return im

def up(im, n):
    return im.resize((im.width * n, im.height * n), Image.NEAREST)

def on_dark(im, pad=6):
    bg = Image.new("RGBA", (im.width + pad * 2, im.height + pad * 2), (36, 18, 56, 255))
    bg.alpha_composite(im, (pad, pad))
    return bg

def plate():
    p = Image.open(PLATE).convert("RGBA").crop((656, 22, 1296, 470))
    return p.resize((320, 224), Image.NEAREST)

def check():  # self-check: every glyph is a full rectangle of known palette characters, palettes fit a Neo Geo palette
    for key, _, glyphs, h, pal1, pal2 in OPTIONS:
        assert set(glyphs) == set("GETSO!"), key
        for ch, rows in glyphs.items():
            assert len(rows) == h, (key, ch, len(rows))
            for y, row in enumerate(rows):
                assert len(row) == len(rows[0]), (key, ch, y, len(row))
                assert set(row) <= set(pal1) | {"."}, (key, ch, y, row)
        assert len(pal1) <= 15 and len(pal2) <= 15 and set(pal1) == set(pal2)

def main():
    check()
    html = ['<!doctype html><meta charset="utf-8"><title>Gum Games countdown drafts</title>',
            '<style>body{background:#14121c;color:#e6e2f0;font:15px/1.5 system-ui,sans-serif;margin:24px}'
            'img{image-rendering:pixelated;display:block;margin:6px 0 18px}h2{margin-top:36px;border-top:1px solid #3a3550;padding-top:16px}'
            '.row{display:flex;gap:24px;flex-wrap:wrap;align-items:flex-end}</style>',
            '<h1>Gum Games countdown: GET SET / GO!</h1><p>Hand-typed pixel grids (draw_countdown.py). Mock frames use the final dusk scene.</p>']
    readme = ["# Countdown word drafts (GET SET / GO!)", "",
              "Draft only, no game code. Run `python3.14 -I draw_countdown.py`; view `index.html`.", "",
              "| Option | Letter height | Colours (+ transparent) | Palettes | Unique 16x16 tiles (6 glyphs) | Sprite columns GET SET / GO! |",
              "|---|---|---|---|---|---|"]
    for key, title, glyphs, h, pal1, pal2 in OPTIONS:
        gs, go = word("GET SET", glyphs, pal1), word("GO!", glyphs, pal2)
        used = {c for rows in glyphs.values() for row in rows for c in row} - {"."}
        cols = {ch: -(-len(rows[0]) // 16) for ch, rows in glyphs.items()}
        tiles = sum(n * -(-h // 16) for n in cols.values())
        npal = 1 if pal1 == pal2 else 2
        readme.append("| %s | %d | %d | %d | %d | %d / %d |" % (
            key, h, len(used), npal, tiles, sum(cols[c] for c in "GETSET"), sum(cols[c] for c in "GO!")))
        html.append("<h2>%s</h2>" % title)
        for name, im in (("getset", gs), ("go", go)):
            on_dark(im).save(os.path.join(HERE, "%s_%s_1x.png" % (key, name)))
            up(on_dark(im), 3).save(os.path.join(HERE, "%s_%s_3x.png" % (key, name)))
            m = plate()
            m.alpha_composite(im, ((320 - im.width) // 2, 84 - im.height // 2))
            up(m, 2).save(os.path.join(HERE, "mock_%s_%s_2x.png" % (key, name)))
        html.append('<div class="row"><div>1x<img src="%s_getset_1x.png"><img src="%s_go_1x.png"></div>'
                    '<div>3x<img src="%s_getset_3x.png"></div><div>3x<img src="%s_go_3x.png"></div>'
                    '<div>GO! pop-in, 3x (hardware shrink + position only)<img src="anim_%s_go_3x.gif"></div></div>' % ((key,) * 5))
        html.append('<div class="row"><div>Mock frame 2x<img src="mock_%s_getset_2x.png"></div>'
                    '<div>Mock frame 2x<img src="mock_%s_go_2x.png"></div></div>' % (key, key))
        # GO! pop-in: (scale sixteenths, dy) per frame; the game would set sprite shrink and y, no extra tiles
        frames = []
        for s, dy in ((4, 0), (8, 0), (12, 0), (16, 0), (16, -4), (16, -2), (16, 1), (16, 0)):
            f = Image.new("RGBA", (go.width + 12, go.height + 16), (36, 18, 56, 255))
            g = go.resize((go.width * s // 16, go.height * s // 16), Image.NEAREST)
            f.alpha_composite(g, ((f.width - g.width) // 2, (f.height - g.height) // 2 + dy))
            frames.append(up(f, 3).convert("P", palette=Image.ADAPTIVE, colors=32))
        frames[0].save(os.path.join(HERE, "anim_%s_go_3x.gif" % key), save_all=True, append_images=frames[1:],
                       duration=[50] * 7 + [900], loop=0)
    readme += ["", "- A: each stroke shaded as a glossy gum tube (inset highlight, magenta to purple shade, violet bounce light).",
               "- A-hot: A's tiles with a second palette; costs one palette, no tiles.",
               "- B: neon tube like the GUM sign in the city; two 4-colour palettes on the same tiles.",
               "- C: 40 px slab in the Hot Gum bubble palette (yellow top to maroon foot, hand-broken band edges).",
               "- Tiles are counted per glyph cell (ceil(w/16) x ceil(h/16)), glyphs G E T S O ! stored once and reused.",
               "- GO! pop-in uses sprite shrink and y offset only.",
               "- Mock plate: ../2026-11-10-backgrounds-final/compare_dusk_2x.png (final half) scaled back to 320x224."]
    open(os.path.join(HERE, "index.html"), "w").write("\n".join(html) + "\n")
    open(os.path.join(HERE, "README.md"), "w").write("\n".join(readme) + "\n")
    print("\n".join(readme[4:4 + 2 + len(OPTIONS)]))

if __name__ == "__main__":
    main()
