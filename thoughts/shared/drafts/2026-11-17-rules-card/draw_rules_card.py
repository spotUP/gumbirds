#!/usr/bin/env python3
"""Gumbirds Gum Games rules card, three layout drafts (draft only, no game data).
Hand-placed pixel data only: every new icon, bar, needle and prop below is a typed character grid. The script only
assembles, mirrors, palette-maps and counts. Bird, background and font are the real game sheets.
Run: python3.14 -I draw_rules_card.py
"""
import json, os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
W, H = 320, 224

def snap(h):  # Neo Geo 5 bits per channel
    return tuple(((int(h[i:i + 2], 16) >> 3) << 3) | (int(h[i:i + 2], 16) >> 5) for i in (0, 2, 4)) + (255,)

# 14 colours + panel colour = 15 (one fix palette; the sprite props use the same colours as one sprite palette)
PAL = {k: snap(v) for k, v in {
    "k": "100828",                                   # outline
    "1": "7b1042", "2": "e63142", "3": "ff9c84",     # red: shade turns purple, light turns orange
    "4": "9c4a18", "5": "f7b521", "6": "ffef8c",     # yellow: shade turns brown-orange
    "7": "10636b", "8": "31c552", "9": "c6f77b",     # green: shade turns teal, light turns yellow
    "W": "ffffff",
    "g": "39396b", "G": "7384b5", "h": "c6d6f7",     # steel: violet shade, sky light
    "P": "ff73bd"}.items()}                          # gum pink (sprite palette only, replaces the panel colour)

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
LETTER = {
 "A": [".kkkk.", "kk..kk", "kk..kk", "kkkkkk", "kk..kk", "kk..kk"],
 "B": ["kkkkk.", "kk..kk", "kkkkk.", "kk..kk", "kk..kk", "kkkkk."],
 "C": [".kkkk.", "kk..kk", "kk....", "kk....", "kk..kk", ".kkkk."]}
STICK = [
 ".....kkkkkk.....",
 "....k3W3222k....",
 "...k3W322221k...",
 "...k33222211k...",
 "...k22222121k...",
 "....k221211k....",
 ".....kkhGkk.....",
 "......khGgk.....",
 "......khGgk.....",
 "......khGgk.....",
 "...kkkkhGgkkkk..",
 "..khhhGGGGGggk..",
 ".khGGGGGGGGGGggk",
 ".kGGGGGGGgGgGggk",
 ".kkgGgGgggggggkk",
 "...kkkkkkkkkkk.."]
BAR = {  # 8x8 bar segments, hand dither between the three steps of each ramp
 "empty": ["kkkkkkkk", "gggggggg", "gkgggkgg", "gggggggg", "ggkgggkg", "gggggggg", "kgkgkgkg", "kkkkkkkk"],
 "power": ["kkkkkkkk", "66666666", "65656566", "55555555", "55555555", "54545455", "44444444", "kkkkkkkk"],
 "safe":  ["kkkkkkkk", "99999999", "98989899", "88888888", "88888888", "87878788", "77777777", "kkkkkkkk"],
 "foul":  ["kkkkkkkk", "33333333", "32323233", "22222222", "22222222", "21212122", "11111111", "kkkkkkkk"]}
SPARK = ["6.......", ".66.....", "...6....", "........", "6666....", "........", "...6....", ".66....."]
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
for name, g in (("up", BTN_UP), ("down", BTN_DOWN), ("stick", STICK), ("slab", SLAB), ("n45", N45), ("n20", N20)):
    assert all(len(r) == 16 for r in g), name                      # self-check: typed rows are full width
for g in list(BAR.values()) + [SPARK, GUM, DOT]:
    assert len(g) == 8 and all(len(r) == 8 for r in g)

def img(grid, ramp=None):
    im = Image.new("RGBA", (len(grid[0]), len(grid)), (0, 0, 0, 0))
    for y, row in enumerate(grid):
        for x, c in enumerate(row):
            if c != ".":
                im.putpixel((x, y), PAL[ramp[c] if ramp and c in ramp else c])
    return im

RAMP = {"A": None, "B": dict(zip("123", "456")), "C": dict(zip("123", "789"))}
def button(letter, down):
    g = [list(r) for r in (BTN_DOWN if down else BTN_UP)]
    for y, row in enumerate(LETTER[letter]):
        for x, c in enumerate(row):
            if c == "k":
                g[y + (4 if down else 2)][x + 5] = "k"
    return img(["".join(r) for r in g], RAMP[letter])

N70 = [("".join(N20[15 - x][15 - y] for x in range(16))) for y in range(16)]   # mirror of N20 on the diagonal
NEEDLE = {20: img(N20), 45: img(N45), 70: img(N70)}

# ---- real game art ----
FJ = json.load(open(os.path.join(ROOT, "assets/font/fix_font.json")))
FSHEET = Image.open(os.path.join(ROOT, "assets/font/fix_font_sheet.png"))
SOOT = Image.open(os.path.join(ROOT, "assets/flier/sootling_sheet.png")).convert("RGBA")
SCENE = Image.open(os.path.join(HERE, "..", "2026-11-10-backgrounds-final", "scene_dusk_1x.png")).convert("RGBA")
assert SCENE.size == (W, H), SCENE.size
_cache = {}
def ftile(name, pal):
    if (name, pal) not in _cache:
        i = FJ["tiles"][name]
        src = FSHEET.crop((i % 16 * 8, i // 16 * 8, i % 16 * 8 + 8, i // 16 * 8 + 8))
        cols = FJ["palettes"][pal]
        t = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
        for y in range(8):
            for x in range(8):
                p = src.getpixel((x, y))
                if p:
                    t.putpixel((x, y), tuple(cols[p - 1]) + (255,))
        _cache[(name, pal)] = t
    return _cache[(name, pal)]
def bird(fx, fy):
    return SOOT.crop((fx, fy, fx + 24, fy + 32))

NEW_FIX, NEW_SPR = set(), set()
class Card:
    def __init__(self):
        self.fix = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        self.spr = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        self.cols = 0
    def cell(self, c, r, t):
        assert 0 <= c < 40 and 0 <= r < 28, (c, r)
        self.fix.paste(t, (c * 8, r * 8))
    def panel(self, c0, r0, c1, r1, pal="white"):
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                v = "t" if r == r0 else "b" if r == r1 else ""
                h = "l" if c == c0 else "r" if c == c1 else ""
                self.cell(c, r, ftile("s:f_" + v + h if v + h else "s:fill", pal))
    def hole(self, c0, r0, c1, r1):
        self.fix.paste((0, 0, 0, 0), (c0 * 8, r0 * 8, c1 * 8 + 8, r1 * 8 + 8))
    def text(self, c, r, s, pal="white", boxed=True):
        assert c >= 0 and c + len(s) <= 40, s
        for i, ch in enumerate(s):
            if ch != " ":
                self.cell(c + i, r, ftile(("b:" if boxed else "p:") + ch, pal))
    def centre(self, c0, c1, r, s, pal="white", boxed=True):
        assert len(s) <= c1 - c0 + 1, s
        self.text(c0 + (c1 - c0 + 1 - len(s)) // 2, r, s, pal, boxed)
    def icon(self, c, r, im):                       # new fix tiles, the panel colour is baked into the tile
        self.fix.alpha_composite(im, (c * 8, r * 8))
        for ty in range(0, im.height, 8):
            for tx in range(0, im.width, 8):
                NEW_FIX.add(im.crop((tx, ty, tx + 8, ty + 8)).tobytes())
    def sprite(self, x, y, im, new=True):
        self.spr.alpha_composite(im, (x, y))
        self.cols += (im.width + 15) // 16
        if new:
            p = Image.new("RGBA", ((im.width + 15) // 16 * 16, (im.height + 15) // 16 * 16), (0, 0, 0, 0))
            p.paste(im, (0, 0))
            for ty in range(0, p.height, 16):
                for tx in range(0, p.width, 16):
                    t = p.crop((tx, ty, tx + 16, ty + 16))
                    if t.getbbox():
                        NEW_SPR.add(t.tobytes())
    def bar(self, c, r, kinds):
        for i, k in enumerate(kinds):
            self.icon(c + i, r, img(BAR[k]))
    def render(self):
        out = SCENE.copy()
        out.alpha_composite(self.spr)
        out.alpha_composite(self.fix)
        return out

ANGLE = ["foul", "safe", "safe", "safe", "safe", "foul"]            # 6 segments of 15 degrees: 15 to 75 is safe
def power(n):
    return ["power"] * n + ["empty"] * (6 - n)
def step_text(card, c, r, lines, active):
    card.text(c, r, lines[0], "white" if active else "dim")
    card.text(c, r + 1, lines[1], "gold" if active else "dim")

# ---- Gum Fling demo pieces (shared by the drafts) ----
def fling_bars(card, c, r, pw, caret, label=True):
    if label:
        card.text(c, r, "POWER", "white")
        card.text(c, r + 2, "ANGLE", "white")
        c += 6
    card.bar(c, r, power(pw))
    card.bar(c, r + 2, ANGLE)
    if caret is not None:
        card.text(c + caret, r + 3, "^", "gold", boxed=False)
def fling_scene(card, bx, by, slabs, state, needle, gums):
    for i in range(slabs):
        card.sprite(bx - 12 + i * 16, by + 32, img(SLAB))
    frame = {"mash0": (0, 0), "mash1": (24, 0), "aim": (0, 64), "spit": (0, 160), "watch": (48, 0)}[state]
    card.sprite(bx, by, bird(*frame), new=False)
    if needle:
        card.sprite(bx + 24, by + 2, NEEDLE[needle])
    for i, (gx, gy) in enumerate(gums):
        card.sprite(bx + gx, by + gy, img(GUM if i == len(gums) - 1 else DOT))

FLING = [  # step, A mashed down, A held down (aim), power, caret, bird, needle
    (0, 1, 0, 2, None, "mash0", None), (0, 0, 0, 4, None, "mash1", None), (0, 1, 0, 6, None, "mash0", None),
    (1, 0, 1, 6, 1, "aim", 20), (1, 0, 1, 6, 3, "aim", 45),
    (2, 0, 0, 6, 3, "spit", None), (2, 0, 0, 6, 3, "watch", None)]
STEPS = [("A", ("MASH A", "BUILD POWER")), ("A", ("HOLD A", "RAISE ANGLE")), ("A", ("LET GO", "FLING IT!"))]
NOTE = "SAFE ANGLE: 15 TO 75 DEGREES"
TURNS = "TAKE TURNS: 3 THROWS EACH"   # two players alternate
GOAL = "FLING THE GUM AS FAR AS YOU CAN"
SKIP = "PRESS A TO SKIP"

def mash_sparks(card, c, r):
    card.icon(c - 1, r, img(SPARK))
    card.icon(c + 2, r, img([row[::-1] for row in SPARK]))

def draft_a(i):  # banner on top, control strip below, the example plays big in the open arena
    step, a, cdown, pw, caret, state, needle = FLING[i]
    k = Card()
    k.panel(1, 1, 38, 5, "pink"); k.centre(2, 37, 2, "GUM FLING", "pink"); k.centre(2, 37, 4, GOAL)
    k.panel(1, 18, 38, 26)
    for n, (col, (btn, lines)) in enumerate(zip((2, 15, 27), STEPS)):
        down = (a if n == 0 else cdown) if n < 2 else 0
        k.icon(col, 19, button(btn, down))
        short = (lines[0], ("FOR POWER", "TO AIM", "TO FLING")[n])
        step_text(k, col + 3, 19, short, n == step)
    k.centre(2, 37, 22, NOTE, "gold"); k.centre(2, 37, 23, TURNS); k.centre(2, 37, 25, SKIP, "dim")
    fling_bars(k, 4, 7, pw, caret)
    gums = {5: [(40, 2), (62, -14), (86, -26)], 6: [(40, 2), (62, -14), (86, -26), (112, -34), (140, -36), (168, -32), (196, -22)]}.get(i, [])
    fling_scene(k, 44, 104, 3, state, needle, gums)
    return k

def draft_b(i):  # one centred card: example window on the left, control list on the right
    step, a, cdown, pw, caret, state, needle = FLING[i]
    k = Card()
    k.panel(3, 3, 36, 27); k.centre(4, 35, 5, "GUM FLING", "pink"); k.centre(4, 35, 7, GOAL)
    k.hole(5, 9, 18, 19)
    for n, (btn, lines) in enumerate(STEPS):
        k.icon(21, 10 + n * 3, button(btn, (a if n == 0 else cdown) if n < 2 else 0))
        step_text(k, 25, 10 + n * 3, lines, n == step)
    if a:
        mash_sparks(k, 21, 10)
    k.centre(4, 35, 21, NOTE, "gold"); k.centre(4, 35, 23, TURNS); k.centre(4, 35, 25, SKIP, "dim")
    fling_bars(k, 6, 10, pw, caret)
    gums = {5: [(28, 8), (40, -2), (54, -10)], 6: [(28, 8), (40, -2), (54, -10), (68, -14), (82, -14)]}.get(i, [])
    fling_scene(k, 58, 112, 3, state, needle, gums)
    return k

def draft_c(i):  # three step windows side by side, all looping at once
    k = Card()
    k.panel(1, 1, 38, 26); k.centre(2, 37, 2, "GUM FLING", "pink"); k.centre(2, 37, 4, GOAL)
    short = (("MASH A", "POWER"), ("HOLD A", "AIM"), ("LET GO", "FLING!"))
    for n, col in enumerate((3, 15, 27)):
        k.hole(col, 6, col + 9, 15)
        down = (i % 2 == 0, True, i == 0)[n]
        k.icon(col, 17, button(STEPS[n][0], down))
        step_text(k, col + 3, 17, short[n], True)
        bx, by = col * 8 + 12, 88
        if n == 0:
            k.bar(col + 2, 7, power((2, 4, 6, 6)[i]))
            fling_scene(k, bx, by, 3, ("mash0", "mash1")[i % 2], None, [])
        elif n == 1:
            k.bar(col + 2, 7, ANGLE)
            k.text(col + 2 + (1, 2, 3, 2)[i], 8, "^", "gold", boxed=False)
            fling_scene(k, bx, by, 3, "aim", (20, 45, 45, 20)[i], [])
        else:
            gums = ([], [(28, 8)], [(28, 8), (40, -2), (54, -10)], [(28, 8), (40, -2), (54, -10), (66, -14)])[i]
            fling_scene(k, bx - 8, by, 3, ("aim", "spit", "watch", "watch")[i], 45 if i == 0 else None, gums)
    for col in (13, 25):
        k.text(col, 10, ">", "gold")
    k.centre(2, 37, 20, NOTE, "gold"); k.centre(2, 37, 22, TURNS); k.centre(2, 37, 24, SKIP, "dim")
    return k

def draft_b_dash(i):  # same card as B for Flap Dash
    k = Card()
    k.panel(3, 3, 36, 27); k.centre(4, 35, 5, "FLAP DASH", "pink"); k.centre(4, 35, 7, "FLY 3 LAPS AS FAST AS YOU CAN")
    k.hole(5, 9, 18, 19)
    k.icon(21, 10, button("A", i % 2 == 0)); step_text(k, 25, 10, ("TAP A", "ONE FLAP"), i % 2 == 0)
    k.icon(21, 13, button("B", i % 2 == 1)); step_text(k, 25, 13, ("THEN TAP B", "NEXT FLAP"), i % 2 == 1)
    mash_sparks(k, 21, 10 + 3 * (i % 2))
    k.text(21, 16, "KEEP SWAPPING", "white"); k.text(21, 17, "A, B, A, B", "gold")
    k.centre(4, 35, 21, "HOLDING A BUTTON DOES NOTHING", "gold"); k.centre(4, 35, 25, SKIP, "dim")
    k.text(7, 10, "LAP 1 OF 3", "white")
    bx, by = 44 + i * 18, (116, 108, 116, 108)[i]
    for d in range(1, 4):
        k.sprite(bx - d * 9, by + 14 + (d % 2) * 3, img(DOT))      # speed trail
    k.sprite(bx, by, bird((0, 24, 96, 120)[i], 0), new=False)
    return k

def build(name, fn, frames, ms):
    NEW_FIX.clear(); NEW_SPR.clear()
    cards = [fn(i) for i in range(frames)]
    ims = [c.render() for c in cards]
    ims[0].save(os.path.join(HERE, name + "_1x.png"))
    pal = Image.new("RGB", (W, H * frames))
    for n, im in enumerate(ims):
        pal.paste(im.convert("RGB"), (0, n * H))
    colours = len(pal.getcolors(1 << 20))
    q = pal.quantize(256, dither=Image.Dither.NONE)
    gif = [im.convert("RGB").quantize(palette=q, dither=Image.Dither.NONE) for im in ims]
    gif[0].save(os.path.join(HERE, "anim_" + name + ".gif"), save_all=True, append_images=gif[1:], duration=ms, loop=0)
    return "%s: frames %d, new fix tiles %d, new 16x16 sprite tiles %d, sprite columns max %d, screen colours %d" % (
        name, frames, len(NEW_FIX), len(NEW_SPR), max(c.cols for c in cards), colours)

if __name__ == "__main__":
    lines = [build("A_banner_strip", draft_a, 7, [260] * 6 + [700]),
             build("B_centre_card", draft_b, 7, [260] * 6 + [700]),
             build("C_three_steps", draft_c, 4, 300),
             build("B_centre_card_flap_dash", draft_b_dash, 4, 220)]
    NEW_FIX.clear()
    sheet = Card(); sheet.panel(0, 0, 25, 4)
    for n, (b, d) in enumerate((b, d) for b in "ABC" for d in (0, 1)):
        sheet.icon(1 + n * 3, 1, button(b, d))
    sheet.icon(19, 1, img(STICK)); sheet.text(18, 1, "<"); sheet.text(21, 1, ">"); sheet.text(22, 2, "^"); sheet.text(23, 2, "v")
    sheet.fix.crop((0, 0, 208, 40)).save(os.path.join(HERE, "icons_1x.png"))
    lines.append("icon sheet (A B C up and down, stick): %d unique fix tiles" % len(NEW_FIX))
    open(os.path.join(HERE, "numbers.txt"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))
