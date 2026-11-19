#!/usr/bin/env python3
"""Gum-in-mouth Sootling drafts (owner idea 2026-11-16). DRAFT ONLY, nothing here is imported by the game.

Hand-placed pixel data only: every body, wing, cheek, eye, feet, neck and sweat grid below is typed row by row.
The script only assembles (layers typed patches, places sprites at typed offsets), mirrors, palette-maps, packs
strips/GIFs and counts tiles. The gum bubbles are the accepted in-game cells of assets/gum/gum_sheet.png (reused).
Motion numbers (dx, dy, bubble level steps) are typed lists baked from a pendulum / spring by hand:
  swing dx = round(3.4 * sin(2 pi i / 12)), feet trail against the velocity, neck leans toward the bubble.
Palette letters: k outline, 1..5 body dark to light, 6..8 beak/feet/wing, 9 a b c d gum ramp (cheeks and the gum
neck use b c d, so a 3-entry palette swap reddens them), e white. 15 colours + transparent, same order as
assets/flier/sootling_sheet.json.
Run: python3.14 -I draw_gum_mouth.py
"""
import json, os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "../../../.."))
FL = json.load(open(os.path.join(REPO, "assets/flier/sootling_sheet.json")))
FLIM = Image.open(os.path.join(REPO, "assets/flier/sootling_sheet.png")).convert("RGBA")
GD = json.load(open(os.path.join(REPO, "assets/gum/gum_sheet.json")))
GIM = Image.open(os.path.join(REPO, "assets/gum/gum_sheet.png")).convert("RGBA")
BGP = os.path.join(REPO, "thoughts/shared/drafts/2026-11-10-backgrounds-final/scene_dusk_1x.png")
CH = "k123456789abcde"
GRID = {(v << 3) | (v >> 2) for v in range(32)}
hx = lambda h: tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
PAL = {"p1": [tuple(c) for c in FL["palettes"]["player"]], "cpu": [tuple(c) for c in FL["palettes"]["cpu"]],
       # owner pick 2026-11-16: sun yellow (thoughts/shared/drafts/2026-11-16-p2-colours/draw_p2_colours.py)
       "p2": [hx(h) for h in "180810 6b2118 b55a10 efa518 ffde42 ffffad 31186b 6342c6 ad94ff 8c3908 de8408 ffc621 ffef7b ffffd6 ffffff".split()]}
# Gum Trip distress: palette swap of entries b, c, d only (cheeks + gum neck). Stage 0 = normal.
STAGE = {1: [(231, 82, 99), (255, 140, 132), (255, 222, 214)],
         2: [(222, 41, 49), (255, 90, 74), (255, 165, 148)],
         3: [(189, 16, 33), (247, 49, 41), (255, 132, 115)]}
assert all(v in GRID for s in STAGE.values() for c in s for v in c)
GUMPAL = [tuple(c) for c in GD["palettes"]["level16"]]
CUE = GD["cue_palettes"]


def rows(first, text):
    out = {}
    for i, r in enumerate(text.strip("\n").split("\n")):
        assert len(r) <= 24, (first + i, len(r), r)
        assert set(r) <= set(CH + "."), r
        if len(r) < 24: print("short row", first + i, len(r), r)
        out[first + i] = r.ljust(24, ".")
    return out


# ---------------- take A: side view, head thrown back, beak up at one o'clock ----------------
BODY_A = rows(8, """
...............k8bk.....
...............k87ck....
....kkk.......k887bk....
...k554kk.....k8776k....
....kk554kkkkkk776kk....
......kk5555454kkk32k...
.....k55555454443332k...
....k555545eke43eke2k...
....k554544eee33eee2k...
....k454443eee32eee2ck..
.....k4434332553255cdck.
.....k343232222221bccbk.
..kk.k3232222121219bbk..
.k87kk322212121111kkk...
k877kk221212111113k.....
k8766k21211111113k......
.k766kk121111133k.......
..kkk..kk111133kk.......
.........kkkkkk.........
""")
# ---------------- take B: front view, head back, beak straight up, two cheeks ----------------
BODY_B = rows(8, """
.........k8b7k..........
.........k8c7k..........
...kk...k88b76k.........
..k55kkkk88776kkk.......
...kkkk55k876k433k......
.....k5554kkk44332k.....
....k5eek45443kee2k.....
....k5eee44443eee2k.....
...kc4eee44333eee2ck....
..kcdc44433332222ccbk...
..kbccb4333232222cbbk...
...kbb43232222121bbk....
.kk.k3232221212111k.kk..
k87kk3222121211113kk78k.
k877k2212121111113k778k.
.k766k212111111133k667k.
..kkk.k1211111133k.kkk..
.......kk1111133kk......
.........kkkkkkk........
""")
BODY = {"A": BODY_A, "B": BODY_B}
X0 = {"A": 16, "B": 10}                      # neck column base; the gum neck centre is X0 + 1
EYES = {"A": ((11, 15), (16, 15)), "B": ((6, 14), (14, 14))}
FEET = {"A": {"mid": [".........6....6.........", ".........7....7.........", "........78...78........."],
              "L": [".........6....6.........", "........7....7..........", "......78...78..........."],
              "R": [".........6....6.........", "..........7....7........", "..........78...78......."],
              "stand": [".........6....6.........", "........778..778........", "........................"]},
        "B": {"mid": [".........6...6..........", ".........7...7..........", "........787.787........."],
              "L": [".........6...6..........", "........7...7...........", "......787.787..........."],
              "R": [".........6...6..........", "..........7...7.........", "..........787.787......."],
              "stand": [".........6...6..........", ".......7787.7877........", "........................"]}}
# patches: (first row, first column, rows); a space keeps the pixel underneath
CHEEK = {"A": {"rest": None,
               "sunk": (17, 17, ["   k.  ", "  k... ", " 1k... ", " 1k..  ", "   .   "]),
               "puff1": (16, 17, ["   ck  ", "   cdck", "  cddck", " bcccbk", " 9bbbk ", "  kkk  "]),
               "puff2": (15, 17, ["    kk ", "   cddk", "  cdedk", "  cdddk", " bccdck", " 9bccbk", "  9bbbk", "   kkk "])},
         "B": {"rest": None,
               "sunk": (16, 0, ["   .k             k.    ", "  ..k4           2k..   ", "  ..k44          1k..   ",
                                "   .k3           1k.    "]),
               "puff1": (15, 0, ["  kk               kk   ", " kcdc             ccbk  ", "kcddcc           cccbbk ",
                                 "kbcccb           ccbbbk ", " kbbb              b9k  ", " kkk               kkk  "]),
               "puff2": (14, 0, [" kkk               kkk  ", "kcddc             cccbk ", "kdeddc            cdccbk",
                                 "kcdddc           ccccbbk", "kbccccb          cccbb9k", " kbbbb           bbb99k ",
                                 " kkk               kkkk "])}}
EYE = {"open": None, "wide": (["eee", "eke", "eee"], ["eee", "eke", "eee"]),
       "squint": (["kkk", "eke", "eee"], ["kkk", "eke", "eee"]),
       "shut": (["kk4", "44k", "kk4"], ["3kk", "k33", "3kk"])}
WING = {"A": {"down": None,
              "mid": (18, 0, ["kkk.. ", "k887k ", "k8776 ", ".k766 ", "..kkk ", "..... ", "......", "..... "]),
              "up": (13, 0, [".kk.  ", "k87k  ", "k877  ", "k876  ", ".k76  ", "..k66 ", "...kk ", "..... ", "..... ",
                             "..... ", "..... ", "......", "..... "])},
        "B": {"down": None,
              "mid": (20, 0, ["kkkk               kkkkk", "k887               7788k", ".k76               667k.",
                              "..kkk              kkk..", "......            ......"]),
              "up": (13, 0, ["kk                    kk", "k8k                  k8k", "k87k                k78k",
                             "k877               k778k", " k76                67k ", "  k6               6k   ",
                             "   k               k    ", "....               .....", "....               .....",
                             "....               .....", ".....              .....", "......            ......"])}}
# gum necks: typed rows, the bottom row sits on cell row 7. (rows, x offset from X0, top centre offset from X0)
NECK = {"S": (["..kck..", "..kbk..", "..kck.."], -2, 1), "L1": ([".kck...", "..kbk..", "..kck.."], -2, 0),
        "L2": (["kck....", ".kbck..", "..kck.."], -2, -1), "R1": (["...kck.", "..kbk..", "..kck.."], -2, 2),
        "R2": (["....kck", "..kcbk.", "..kck.."], -2, 3)}
LONG_S = ["...kck...", "...kbk...", "...kck...", "...kbk...", "...kck...", "...kbk...", "...kck...", "...kbk...",
          "...kck...", "...kbk...", "...kck..."]
LONG_L1 = ["..kck....", "..kbk....", "..kck....", "..kbk....", "...kck...", "...kbk...", "...kck...", "...kbk...",
           "...kck...", "...kbk...", "...kck..."]
LONG_L2 = ["kck......", "kbk......", ".kck.....", ".kbk.....", "..kck....", "..kbk....", "..kck....", "...kbk...",
           "...kck...", "...kbk...", "...kck..."]
mir = lambda rs: [r[::-1] for r in rs]
NECK.update({"LS": (LONG_S, -3, 1), "LL1": (LONG_L1, -3, 0), "LL2": (LONG_L2, -3, -2),
             "LR1": (mir(LONG_L1), -3, 2), "LR2": (mir(LONG_L2), -3, 4)})
VNECK = ["kck.....kck", ".kck...kck.", "..kbk.kbk..", "...kbkbk..."]   # two gums: sits on the neck top, tops at -4 / +4
SWEAT = [["..k..", ".k5k.", "k4e5k", "k445k", ".kkk."], [".k.", "k5k", "k4k", ".k."]]


def cell(take, cheek="rest", eyes="open", wing="down", feet="mid"):
    g = [["."] * 24 for _ in range(32)]
    for r, row in BODY[take].items(): g[r] = list(row)
    for r, row in zip((27, 28, 29), FEET[take][feet]): g[r] = list(row)

    def patch(p):
        if p:
            for j, row in enumerate(p[2]):
                for i, c in enumerate(row):
                    if c != " " and 0 <= p[1] + i < 24: g[p[0] + j][p[1] + i] = c
    patch(CHEEK[take][cheek]); patch(WING[take][wing])
    if EYE[eyes]:
        for (ex, ey), e in zip(EYES[take], EYE[eyes]): patch((ey, ex, e))
    return tuple("".join(r) for r in g)


def paint(grid, pal):
    im = Image.new("RGBA", (len(grid[0]), len(grid)), (0, 0, 0, 0))
    for y, r in enumerate(grid):
        for x, c in enumerate(r):
            if c != ".": im.putpixel((x, y), pal[CH.index(c)] + (255,))
    return im


def palette(pal, stage=0):
    p = list(PAL[pal])
    if stage: p[11:14] = STAGE[stage]
    return p


def bubble(level, wob, pal, stage=0):
    level = max(1, min(16, level))
    f = GD["animations"]["level%d" % level][wob % 6]
    im = GIM.crop((f["x"], f["y"], f["x"] + f["w"], f["y"] + f["h"]))
    im = im.crop(im.getbbox())
    m = {}
    if pal != "p1":   # mock-up only: the gum sheet recoloured with the flier palette's gum ramp
        P = PAL[pal]
        m = dict(zip(GUMPAL, [P[0], P[9], P[9], P[9], P[10], P[10], P[11], P[11], P[12], P[13], P[14], P[3]]))
    elif stage >= 2:  # the gum sheet's own cue palettes (warm, hot)
        m = {GUMPAL[e - 1]: tuple(c) for e, c in zip(CUE["entries"], CUE["warm" if stage == 2 else "hot"])}
    if m: im.putdata([(m.get(p[:3], p[:3]) + (255,)) if p[3] else p for p in im.getdata()])
    return im


W, H, CX, CY = 64, 80, 20, 46
USED = {}   # take -> anim -> set of bird cells (for the tile count)


def frame(take, anim, cheek="rest", eyes="open", wing="down", feet="mid", dx=0, dy=0, gums=(10,), wob=0,
          pal="p1", stage=0, flip=False, sweat=(), front=False, gx=0, canvas=None, at=None):
    """One frame: bird cell + gum neck + bubbles. gx = extra bubble sway (pixels)."""
    body = "B" if (take == "B" or front) else "A"
    long_ = take == "C"
    c = cell(body, cheek, eyes, wing, feet)
    if pal == "p1": USED.setdefault(take, {}).setdefault(anim, set()).add(c)
    P = palette(pal, stage)
    a = abs(dx)
    if long_: n = "LS" if a < 2 else ("L" + ("L" if dx > 0 else "R") + ("1" if a < 4 else "2"))
    else: n = "S" if a < 2 else (("L" if dx > 0 else "R") + ("1" if a < 3 else "2"))
    if len(gums) == 2 or gums == (): n = "LS" if long_ else "S"
    nrows, nx, ntop = NECK[n]
    layer = Image.new("RGBA", (40, 56), (0, 0, 0, 0))        # cell at (8, 20) inside the layer
    layer.alpha_composite(paint(c, P), (8, 20))
    x0 = X0[body]
    ny = 20 + 8 - len(nrows)
    layer.alpha_composite(paint(nrows, P), (8 + x0 + nx, ny))
    tx = 8 + x0 + ntop
    anchors = [(tx, ny)]
    if len(gums) == 2:
        layer.alpha_composite(paint(VNECK, P), (tx - 5, ny - 4))
        anchors = [(tx - 4, ny - 4), (tx + 4, ny - 4)]
    if flip:
        layer = layer.transpose(Image.FLIP_LEFT_RIGHT)
        anchors = [(39 - x, y) for x, y in anchors]
    # keep the single-gum anchor of the resting pose on canvas x = CX + 17 whatever the body is
    rest_tx = 8 + x0 + 1
    if flip: rest_tx = 39 - rest_tx
    ox, oy = (CX + 17 - rest_tx + dx, CY - 20 + dy)
    out = canvas if canvas is not None else Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if at: ox, oy = ox + at[0] - CX, oy + at[1] - CY
    for k, (lv, (ax, ay)) in enumerate(zip(gums, anchors)):
        if lv:
            b = bubble(lv, wob + 3 * k, pal, stage)
            out.alpha_composite(b, (ox + ax - b.width // 2 + gx, oy + ay + 1 - b.height))
    out.alpha_composite(layer, (ox, oy))
    for sx, sy, sf in sweat:
        out.alpha_composite(paint(SWEAT[sf], P), (ox + 8 + sx, oy + 20 + sy))
    return out


# ---------------- motion tables (typed; baked from a pendulum / spring by hand) ----------------
SW = {"A": [0, 2, 3, 3, 3, 2, 0, -2, -3, -3, -3, -2], "C": [0, 3, 4, 5, 4, 3, 0, -3, -4, -5, -4, -3]}
SW["B"] = SW["A"]
SWF = ["L", "L", "L", "mid", "R", "R", "R", "R", "R", "mid", "L", "L"]       # feet trail against the velocity
BLOW = ["sunk", "rest", "puff1", "puff1", "puff1", "rest"] * 2               # constant blow, two breaths per swing
BLV = [0, 0, 1, 2, 1, 0] * 2                                                # bubble level pulse per breath


def anim_fly(take, gums, pal="p1", anim="fly"):
    out = []
    for i in range(12):
        dx = SW[take][i] if len(gums) == 1 else (SW["A"][i] + 1) // 2      # two gums: stiffer, smaller swing
        out.append((frame(take, anim, cheek=BLOW[i], feet=SWF[i], dx=dx, dy=-1 if abs(dx) >= 3 else 0,
                          gums=tuple(g + BLV[i] for g in gums), wob=i, pal=pal,
                          gx=0 if len(gums) == 1 else dx), 6))
    return out


FLAP = [("up", "sunk", "wide", 1, 0, 4), ("up", "sunk", "wide", 1, 0, 3), ("mid", "puff1", "open", 0, 1, 3),
        ("down", "puff2", "squint", -2, 3, 3), ("down", "puff2", "squint", -3, 4, 4), ("mid", "puff1", "open", -2, 2, 4),
        ("down", "rest", "open", -1, 1, 5), ("down", "rest", "open", 0, 0, 6)]


def anim_flap(take, gums=(10,), pal="p1"):
    return [(frame(take, "flap", wing=w, cheek=c, eyes=e, dy=dy, feet="mid" if dy >= 0 else "L" if False else "mid",
                   gums=tuple(g + lv for g in gums), wob=i, pal=pal), t) for i, (w, c, e, dy, lv, t) in enumerate(FLAP)]


def anim_turn(take, pal="p1"):
    if take == "B": return []
    seq = [dict(), dict(cheek="puff1"), dict(front=True, eyes="wide"), dict(flip=True, cheek="puff1"), dict(flip=True)]
    return [(frame(take, "turn", wob=i, pal=pal, **k), 5 if i in (1, 2, 3) else 14) for i, k in enumerate(seq)]


# landing blow-up: three breaths, each one swells the bubble with a small overshoot (levels typed from a spring)
BUP = [("rest", "open", 0, 6), ("sunk", "wide", 0, 6), ("puff1", "squint", 1, 4), ("puff2", "shut", 2, 4),
       ("puff2", "shut", 4, 4), ("puff1", "squint", 3, 5), ("sunk", "wide", 3, 6), ("puff1", "squint", 4, 4),
       ("puff2", "shut", 6, 4), ("puff2", "shut", 8, 4), ("puff1", "squint", 7, 5), ("sunk", "wide", 7, 6),
       ("puff1", "squint", 8, 4), ("puff2", "shut", 10, 4), ("puff2", "shut", 12, 4), ("puff1", "open", 11, 5),
       ("rest", "open", 10, 6), ("rest", "open", 10, 8)]


def anim_blowup(take, two=False, pal="p1"):
    out = []
    for i, (c, e, lv, t) in enumerate(BUP):
        if two: g, lv2 = (7, 0), min(lv, 7)
        out.append((frame(take, "blowup", cheek=c, eyes=e, feet="stand", dy=1 if c == "sunk" else 0,
                          gums=(min(lv, 7), 0) if two else ((lv,) if lv else ()), wob=i, pal=pal), t))
    if two:
        for i, (c, e, lv, t) in enumerate(BUP[1:]):
            out.append((frame(take, "blowup", cheek=c, eyes=e, feet="stand", dy=1 if c == "sunk" else 0,
                              gums=(7, min(lv, 7)), wob=i, pal=pal), t))
    for dy in (-1, -3, -6):
        out.append((frame(take, "blowup", feet="mid", dy=dy, gums=(7, 7) if two else (10,), wob=dy, pal=pal), 5))
    return out


# sweat arcs (typed ballistic offsets, relative to the cell): up and out, then down
ARC = [(-1, -1), (-2, -3), (-3, -4), (-4, -4), (-5, -3), (-6, -1), (-6, 2), (-7, 6)]


def anim_distress(take, stage):
    """Gum Trip, gum running out. Stage 1 = palette swap only. 2 and 3 add eye frames and the sweat sprite."""
    lv = {1: 7, 2: 4, 3: 2}[stage]
    ch = (["rest", "puff1", "puff2", "puff1"] * 2) if stage < 3 else ["puff1", "puff2"] * 4
    sx = 6 if take != "B" else 3
    out = []
    for i in range(8):
        sw = []
        if stage >= 2: sw.append((sx + ARC[i][0], 12 + ARC[i][1], 0 if i < 5 else 1))
        if stage == 3:
            j = (i + 4) % 8
            sw.append((sx + 4 - ARC[j][0] if take == "B" else sx - 2 + ARC[j][0] // 2, 9 + ARC[j][1], 0 if j < 5 else 1))
        out.append((frame(take, "distress%d" % stage, cheek=ch[i], eyes=["open", "open", "squint", "shut"][stage],
                          feet=SWF[(i * 3) % 12] if stage == 3 else "mid", dx=(i % 2) * 2 - 1 if stage == 3 else 0,
                          gums=(lv + (1 if "puff" in ch[i] else 0),), wob=i, stage=stage, sweat=sw), {1: 5, 2: 4, 3: 3}[stage]))
    return out


FLAT = (44, 52, 86, 255)


def on_bg(im, scale):
    b = Image.new("RGBA", im.size, FLAT); b.alpha_composite(im)
    return b.resize((im.width * scale, im.height * scale), Image.NEAREST).convert("RGB")


def strip(frames, name):
    s = Image.new("RGBA", (W * len(frames), H), (0, 0, 0, 0))
    for i, (f, _) in enumerate(frames): s.alpha_composite(f, (W * i, 0))
    on_bg(s, 1).save(os.path.join(HERE, name + "_1x.png")); on_bg(s, 3).save(os.path.join(HERE, name + "_3x.png"))


def gif(frames, name, scale=3):
    ims = [on_bg(f, scale) if f.mode == "RGBA" and f.size == (W, H) else f for f, _ in frames]
    ims[0].save(os.path.join(HERE, name + ".gif"), save_all=True, append_images=ims[1:],
                duration=[max(20, round(t * 1000 / 60)) for _, t in frames], loop=0, disposal=1)


def tiles(cells):
    t = set()
    for c in cells:
        for ty in (0, 16):
            for tx in (0, 16):
                tile = tuple(r[tx:tx + 16].ljust(16, ".") for r in c[ty:ty + 16])
                if any(set(r) != {"."} for r in tile): t.add(tile)
    return t


def current_frame(i, pal="player"):
    f = FL["animations"][pal][i]
    return FLIM.crop((f["x"], f["y"], f["x"] + 24, f["y"] + 32))


def scene(take, i):
    bg = Image.open(BGP).convert("RGBA")
    f2, f1, bu = anim_fly(take, (7, 7), anim="x"), anim_fly(take, (10,), "p2", "x"), anim_blowup(take)
    fr = anim_fly(take, (7, 7), "cpu", "x")
    for seq, pos, kw in ((f2, (70, 96), 0), (f1, (190, 70), 0), (fr, (250, 130), 1), (bu, (128, 150), 0)):
        im = seq[i % len(seq)][0]
        if kw: im = im.transpose(Image.FLIP_LEFT_RIGHT)
        bg.alpha_composite(im, (pos[0] - 32, pos[1] - 60))
    # current in-game flier for scale (frame 0 of flap2 + one level 10 bubble on its string), bottom left
    cur = current_frame((i // 2) % 8); b = bubble(10, i, "p1")
    bg.alpha_composite(b, (22 + 12 - b.width // 2, 150 + 11 - b.height)); bg.alpha_composite(cur, (22, 150))
    return bg.convert("RGB")


def main():
    numbers = []
    for take in "ABC":
        A = {"fly1": anim_fly(take, (10,)), "fly2": anim_fly(take, (7, 7)), "flap": anim_flap(take),
             "flap2": anim_flap(take, (7, 7)), "turn": anim_turn(take), "blowup1": anim_blowup(take),
             "blowup2": anim_blowup(take, True), "distress1": anim_distress(take, 1),
             "distress2": anim_distress(take, 2), "distress3": anim_distress(take, 3)}
        for k, fr in A.items():
            if fr: strip(fr, "%s_%s" % (take, k)); gif(fr, "%s_%s_3x" % (take, k))
        for p in ("p2", "cpu"):
            gif(anim_fly(take, (7, 7), p, "x"), "%s_fly2_%s_3x" % (take, p)); gif(anim_flap(take, (10,), p), "%s_flap_%s_3x" % (take, p))
            gif(anim_blowup(take, False, p), "%s_blowup1_%s_3x" % (take, p))
        var = Image.new("RGBA", (W * 6, H), (0, 0, 0, 0))
        for n, p in enumerate(("p1", "p2", "cpu")):
            var.alpha_composite(frame(take, "x", cheek="puff1", gums=(7, 7), pal=p), (W * 2 * n, 0))
            var.alpha_composite(frame(take, "x", cheek="puff2", wing="mid", gums=(10,), pal=p), (W * 2 * n + W, 0))
        on_bg(var, 1).save(os.path.join(HERE, "%s_variants_1x.png" % take)); on_bg(var, 3).save(os.path.join(HERE, "%s_variants_3x.png" % take))
        sc = [scene(take, i) for i in range(24)]
        sc[2].resize((960, 672), Image.NEAREST).save(os.path.join(HERE, "%s_scene_dusk_3x.png" % take))
        sc[2].save(os.path.join(HERE, "%s_scene_dusk_1x.png" % take))
        gif([(s.resize((640, 448), Image.NEAREST), 6) for s in sc], "%s_scene_dusk_anim_2x" % take)
        # same-scale comparison: current in-game flier (flap2 frame 0, idle) next to this take
        cmp_ = Image.new("RGBA", (W * 4, H), (0, 0, 0, 0))
        for n, fi in enumerate((0, 62)):
            b = bubble(10, 0, "p1")
            cmp_.alpha_composite(b, (W * n + 20 + 12 - b.width // 2, CY + 11 - b.height) if fi == 0 else (W * n + 44, 90))
            cmp_.alpha_composite(current_frame(fi), (W * n + 20, CY))
        cmp_.alpha_composite(frame(take, "x", cheek="puff1"), (W * 2, 0))
        cmp_.alpha_composite(frame(take, "x", feet="stand", cheek="puff2", eyes="shut", gums=(4,)), (W * 3, 0))
        on_bg(cmp_, 1).save(os.path.join(HERE, "%s_compare_current_1x.png" % take)); on_bg(cmp_, 3).save(os.path.join(HERE, "%s_compare_current_3x.png" % take))
        U = USED[take]
        base = set().union(*(v for k, v in U.items() if not k.startswith("distress") and k != "x"))
        line = ["take %s: %d bird frames (24x32, 4 tiles each as imported today) = %d tiles; %d unique 16x16 tiles after dedupe"
                % (take, len(base), 4 * len(base), len(tiles(base)))]
        for k in ("fly", "flap", "turn", "blowup"):
            line.append("  %s: %d frames" % (k, len(U.get(k, ()))))
        seen = set(base)
        for s in (1, 2, 3):
            new = U["distress%d" % s] - seen; seen |= new
            line.append("  distress stage %d: +%d frames = +%d tiles (%d unique 16x16)%s" % (
                s, len(new), 4 * len(new), len(tiles(new) - tiles(seen - new)), "" if s == 1 else "; sweat sprite 2 cells = 1 tile shared by all stages" if s == 2 else ""))
        line.append("  gum neck sprite: %d cells of 16x16 (%s) + V for two gums = %d tiles" % (
            (3, "straight, lean 1, lean 2; mirrored by flip", 4) if take != "C" else (3, "long 11 px: straight, lean 1, lean 2; mirrored by flip", 4)))
        numbers += line
    numbers.append("current sheet for reference: flap2 8 + flap1 8 + inflate 14 = 30 frames = 120 tiles that these takes would replace")
    open(os.path.join(HERE, "numbers.txt"), "w").write("\n".join(numbers) + "\n")
    print("\n".join(numbers))


if __name__ == "__main__":
    main()
