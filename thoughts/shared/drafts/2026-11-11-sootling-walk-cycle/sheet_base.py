#!/opt/homebrew/bin/python3.14 -I
"""Small Sootling, full 63-frame sheet at 24 x 32.

Started from draw_small.py of thoughts/shared/drafts/2026-11-10-sootling-small
(the 10 key frames). Hand-placed pixel grids for every part (body, tuft, eyes,
beak, five wing positions, gum shapes, bursts); each frame is a hand-written
row in the clip tables below that says which grid goes where, how far the body
is squashed or stretched and how the gum lags.

Palettes are read from assets/flier/sootling_sheet.json (15 colours, no new
ones). Run: /opt/homebrew/bin/python3.14 -I draw_sheet.py
"""
import json
import os
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
SHEET_JSON = os.path.join(ROOT, "assets", "flier", "sootling_sheet.json")

# k outline | a b c d e fur dark..light | r o y beak, wing, feet | p q m n h gum dark..light | w white
LETTERS = "kabcderoypqmnhw"
META = json.load(open(SHEET_JSON))
PALS = {name: [tuple(c) for c in cols] for name, cols in META["palettes"].items()}
FW, FH = 24, 32
COLS = 8

# ------------------------------------------------------------------ parts
# Fur ball, 16 x 16 with outline (fur 14 x 14). Light from the upper left.
BODY = [
    ".....kkkkkk.....",
    "...kkeeeddckk...",
    "..keeeeedddcck..",
    ".keeeedddddccck.",
    ".keeedddddcccck.",
    "kdeddcbbbbbbbaak",
    "kdddccbbbbbbbbak",
    "kddcccbbbbbbbbak",
    "kdccccbbbbbbbaak",
    "kcccbbbbbbbbaaak",
    "kccbbbbbbabbaaak",
    ".kcbbbbabbaaaak.",
    ".kbbbabbaaaaaak.",
    "..kbbabaaaaaak..",
    "...kkaaaaaakk...",
    ".....kkkkkk.....",
]
# Eyes: body rows 4..8, cols 7..13. No box: whites sit straight in the fur, pupils on
# the facing side, a mid-tone fur column between the eyes so the left pupil shows.
EYES = {
    "open":   ["dbbcbbc", "bwwcbww", "wwkcwwk", "wwkcwwk", "beecbee"],
    "up":     ["dbbcbbc", "bwkcbwk", "wwkcwwk", "wwwcwww", "beecbee"],
    "down":   ["dbbcbbc", "bwwcbww", "wwwcwww", "wwkcwwk", "bekcbek"],
    "shock":  ["bwwcwwb", "wwwcwww", "wkwcwkw", "wwwcwww", "beecbee"],
    "shut":   ["dddcccc", "cbbcbba", "kkkckkk", "beecbee", "bbbbbaa"],
    "squint": ["dccdccc", "kccacck", "ckcackc", "kccacck", "bbbbbaa"],
    "lids":   ["dddcccc", "bbbcbba", "wwkcwwk", "wwkcwwk", "beecbee"],
}
# Tuft: one swept-back quiff, a single shape (the two strands read as ears).
# Last row replaces body row 0.
TUFT = {
    "norm": ["..kkk...........",
             ".keedkk.........",
             "..kkeedk........",
             "....keedkkk....."],
    "flat": [".kkkkk..........",
             "keeeddkk........",
             ".kkkeedkkkk....."],
    "up":   [".....kk.........",
             "....kedk........",
             "....keedk.......",
             "....keedkkk....."],
}
BEAK = {
    "shut": ["kk..", "yyok", "ork.", "kk.."],
    "open": ["kkk.", "yyok", "kkk.", "ork.", "kk.."],
}
# Wings: (dx from frame col 4, dy from the body top, grid). Full outline all round.
WING = {
    "up": (-3, 1, ["kk.....",
                   "kyk....",
                   "kyok...",
                   ".kyok..",
                   ".kyork.",
                   "..kork.",
                   "..korrk",
                   "...kkk."]),
    "upmid": (-4, 4, ["kkk.....",
                      "kyykk...",
                      ".kyookk.",
                      "..koorrk",
                      "...krrrk",
                      "....kkk."]),
    "mid": (-3, 7, ["..kkkkk.",
                    ".kyyoork",
                    "kyooorrk",
                    ".korrrrk",
                    "..kkkkk."]),
    "downmid": (-4, 8, ["....kkk.",
                        "...kyork",
                        "..kyorrk",
                        ".kyorkk.",
                        "kyokk...",
                        "kkk....."]),
    "down": (-3, 8, ["...kkk.",
                     "..kyork",
                     "..kyork",
                     ".kyork.",
                     ".kyok..",
                     "kyok...",
                     "kok....",
                     "kk....."]),
}
# Gum: smooth clusters, no checker, no dither.
GUM = {  # name: (grid, default x, default y, string start dx, dy)
    "two": ([
        "..kkkkk...kkkkk..",
        ".knnnmmk.knnnmmk.",
        "knhwnnmmknhwnnmmk",
        "knhhnmmmmnhhnmmmk",
        "knnnmmmqmnnnmmmqk",
        "kmnmmmqqmmnmmmqqk",
        "kmmmmqqpkmmmmqqpk",
        ".kmqqqpk.kmqqqpk.",
        "..kkkkk...kkkkk..",
    ], 3, 1, 8, 7),
    "one": ([
        "..kkkkk..",
        ".knnnmmk.",
        "knhwnnmmk",
        "knhhnmmmk",
        "knhnnmmmk",
        "knnnmmmqk",
        "kmnmmmqqk",
        "kmmmmqqpk",
        ".kmqqqpk.",
        "..kkkkk..",
    ], 7, 1, 4, 9),
    "lobe": ([
        "..kkkkk..",
        ".knnnmmk.",
        "knhwnnmmk",
        "knhhnmmmk",
        "knnnmmmqk",
        "kmnmmmqqk",
        "kmmmmqqpk",
        ".kmqqqpk.",
        "..kkkkk..",
    ], 3, 1, 4, 8),
    "wide": ([
        "...kkkkkkk...",
        ".kknnnnmmmkk.",
        "knnhwnnnmmmmk",
        "knhhnnnmmmmmk",
        "knnnnmmmmmmqk",
        "kmnnmmmmmqqqk",
        "kmmmmmmqqqqpk",
        ".kkmmqqqqpkk.",
        "...kkkkkkk...",
    ], 5, 1, 6, 8),
    "b5": ([
        "..kkk..",
        ".knnmk.",
        "khwnmmk",
        "knnmmqk",
        "kmmmqqk",
        ".kmqpk.",
        "..kkk..",
    ], 14, 6, 3, 6),
    "b3": ([".kkk.", "khnmk", "knmmk", "kmmqk", ".kkk."], 19, 0, 2, 4),
    "b2": ([".kk.", "khnk", "knmk", ".kk."], 20, 0, 1, 3),
    "burst": ([
        ".k..k..k.",
        "k.hnnnh.k",
        "..nhwhn..",
        "knhwwwhnk",
        "..nhwhn..",
        "k.hnnnh.k",
        ".k..k..k.",
    ], 7, 2, 4, 6),
}
BITS = {
    1: [(-5, -1, "n"), (-3, -4, "m"), (0, -5, "h"), (3, -4, "n"), (5, -1, "m"), (4, 3, "n"), (0, 4, "m"),
        (-4, 3, "h"), (-1, -1, "w")],
    2: [(-6, 1, "m"), (-4, -4, "q"), (1, -5, "m"), (5, -3, "q"), (6, 2, "m"), (3, 5, "n"), (-3, 5, "m")],
    3: [(-6, 4, "q"), (5, 5, "q"), (1, 7, "m")],
    4: [(-5, 8, "q"), (4, 9, "q")],
}
LOOSE = {  # loose string, points relative to the knot at the brow
    "a": [(0, 0), (1, -3), (0, -6)],
    "b": [(0, 0), (2, -3), (2, -6)],
    "c": [(0, 0), (0, -3), (2, -6)],
    "curl": [(0, 0), (2, -3), (0, -6), (-3, -7)],
    "droop": [(0, 0), (3, -2), (4, 1)],
}
FEET = {  # per foot, relative to (foot col, first row under the body)
    "fly":   [(0, 0, "r"), (0, 1, "o"), (1, 1, "y")],
    "stand": [(0, 0, "r"), (-1, 1, "o"), (0, 1, "o"), (1, 1, "y")],
    "tuck":  [(0, 0, "o"), (1, 0, "y")],
    "trail": [(0, 0, "r"), (-1, 1, "o"), (0, 1, "y")],
}
FOOT_COLS = (9, 14)
BODY_H = {2: 14, 1: 15, 0: 16, -1: 17, -2: 18}


def body_grid(sq, eyes):
    rows = [list(r) for r in BODY]
    for i, er in enumerate(EYES[eyes]):
        rows[4 + i][7:14] = list(er)
    brow = 4
    if sq >= 1:
        del rows[12]
    if sq == 2:
        del rows[3]
        brow = 3
        rows = [r[:4] + [r[4]] + r[4:] for r in rows]
    if sq <= -1:
        rows.insert(11, list(rows[11]))
    if sq == -2:
        rows.insert(3, list(rows[3]))
        brow = 5
        rows = [r[:4] + r[5:] for r in rows]
    return rows, brow


def line(p0, p1):
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    out = []
    while True:
        out.append((x0, y0))
        if (x0, y0) == (x1, y1):
            return out
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def compose(gum="two", gpos=None, glift=0, gdx=0, sq=0, lift=0, wing="mid", eyes="open", beak="shut",
            feet="fly", feet2=None, tuft="norm", string="gum", bend=0, bits=None, wad=0, beakbub=None,
            cls="x", extra_gum=None):
    """returns (pixel dict {(x, y): letter}, info dict)"""
    px = {}
    clipped = []

    def dot(x, y, ch, over=True):
        if ch in ". ":
            return
        if not (0 <= x < FW and 0 <= y < FH):
            clipped.append((x, y, ch))
            return
        if over or (x, y) not in px:
            px[(x, y)] = ch

    def put(grid, x0, y0):
        for y, row in enumerate(grid):
            for x, ch in enumerate(row):
                dot(x0 + x, y0 + y, ch)

    rows, brow = body_grid(sq, eyes)
    h = len(rows)
    w = len(rows[0])
    top = 30 - lift - h
    bx = 4 + (16 - w)          # widened: 3, narrowed: 5; the face keeps its columns
    tshift = bx - 4 + (w - 16)  # tuft follows the columns right of the changed one
    vtop = top + brow - 4      # row the wing and beak offsets count from
    knot = (17 if sq == 2 else 18, top + 3)  # the brow, as in the approved key frames
    info = {"cls": cls, "body": (bx, top, bx + w - 1, top + h - 1)}

    # string first (gum and body cover its ends)
    def draw_string(pts):
        core = []
        for a, b in zip(pts, pts[1:]):
            core += line(a, b)
        for x, y in core:
            dot(x - 1, y, "k", over=False)
            dot(x + 1, y, "k", over=False)
        for x, y in core:
            dot(x, y, "n")
        return core

    gbox = None
    if gum:
        grid, gx, gy, ax, ay = GUM[gum]
        if gpos:
            gx, gy = gpos
        gx += gdx
        gy -= glift
        gbox = (gx, gy, gx + len(grid[0]) - 1, gy + len(grid) - 1)
        if string == "gum":
            s = (gx + ax, gy + ay)
            mid = (s[0] + (knot[0] - s[0]) // 3 + bend, s[1] + max(1, (knot[1] - s[1]) // 2))
            draw_string([s, mid, knot])
    if isinstance(string, str) and string in LOOSE:
        core = draw_string([(knot[0] + x, knot[1] + y) for x, y in LOOSE[string]])
        dot(core[-1][0], core[-1][1], "h")
    if gum:
        put(grid, gx, gy)
    if extra_gum:
        g2, x2, y2 = extra_gum
        put(GUM[g2][0], x2, y2)
    info["gum"] = gbox

    # body, tuft
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            dot(bx + x, top + y, ch)
    tg = TUFT[tuft]
    put(tg, 4 + tshift, top - (len(tg) - 1))
    if gum and string == "gum" or (isinstance(string, str) and string in LOOSE):
        dot(knot[0], knot[1], "n")
        dot(knot[0] + 1, knot[1] + 1, "m")
    # beak, wing
    put(BEAK[beak], 18, vtop + 8)
    if wad:
        dot(21, vtop + 9, "m")
        dot(22, vtop + 9, "n")
        if wad > 1:
            dot(22, vtop + 8, "h")
            dot(21, vtop + 10, "q")
    if beakbub:
        g = GUM[beakbub][0]
        put(g, 24 - len(g[0]) - (0 if beakbub != "b5" else 0), vtop + 9 - len(g) // 2)
    wx, wy, wg = WING[wing]
    put(wg, 4 + wx, vtop + wy)
    # feet
    fy = top + h
    fpts = []
    for col, kind in zip(FOOT_COLS, (feet, feet2 or feet)):
        for dx, dy, ch in FEET[kind]:
            dot(col + dx, fy + dy, ch)
            fpts.append((col + dx, fy + dy))
    info["feet"] = (min(p[0] for p in fpts), min(p[1] for p in fpts), max(p[0] for p in fpts), max(p[1] for p in fpts))
    if bits:
        n, cx, cy = bits
        for dx, dy, ch in BITS[n]:
            if 0 <= cx + dx < FW and 0 <= cy + dy < FH:
                dot(cx + dx, cy + dy, ch, over=False)
    info["clipped"] = clipped
    return px, info


def S(**kw):
    return kw


# ------------------------------------------------------------------ clips
def flap(gum, cls, gdx):
    wings = ["up", "upmid", "mid", "downmid", "down", "downmid", "mid", "upmid"]
    sq = [1, 0, -1, -1, 0, 0, 0, 1]
    lift = [0, 0, 1, 2, 2, 2, 1, 0]
    glift = [0, 0, 0, 1, 1, 1, 0, 0]
    tuft = ["norm", "norm", "flat", "flat", "norm", "norm", "norm", "up"]
    feet = ["tuck", "fly", "trail", "trail", "fly", "fly", "fly", "tuck"]
    bend = [0, 0, 1, 1, 0, 0, -1, 0]
    return [S(gum=gum, cls=cls, wing=wings[i], sq=sq[i], lift=lift[i], glift=glift[i], tuft=tuft[i],
              feet=feet[i], bend=bend[i], gdx=gdx[i]) for i in range(8)]


FLAP2 = flap("two", "2", [0] * 8)
FLAP1 = flap("one", "1", [0, 0, 0, -1, -1, 0, 0, 0])

POP2 = [
    S(gum="two", cls="2", eyes="shock", beak="open", wing="mid", lift=1),
    S(gum="lobe", extra_gum=("burst", 11, 2), eyes="squint", wing="up", sq=1, lift=1),
    S(gum="lobe", bits=(1, 15, 5), eyes="squint", wing="up", sq=2, tuft="up"),
    S(gum="lobe", gdx=1, bits=(2, 15, 6), eyes="squint", wing="upmid", sq=1, wad=2, bend=1),
    S(gum="lobe", gdx=2, bits=(3, 15, 7), eyes="down", wing="mid", wad=2, tuft="flat"),
    S(gum="one", gdx=-1, cls="1", bits=(4, 15, 8), eyes="up", wing="downmid", sq=-1, wad=2, tuft="flat"),
    S(gum="one", cls="1", eyes="up", wing="down", lift=1, wad=2),
    S(gum="one", cls="1", wing="downmid", lift=1, wad=1),
    S(gum="one", cls="1", wing="mid", lift=1, wad=1),
    S(gum="one", cls="1", eyes="shut", wing="upmid", sq=1, tuft="up"),
    S(gum="one", cls="1", wing="upmid"),
    dict(FLAP1[0]),
]
POP1 = [
    S(gum="one", cls="1", eyes="shock", beak="open", wing="mid", lift=1),
    S(gum="burst", eyes="squint", wing="up", sq=1, lift=1),
    S(gum=None, string="curl", bits=(1, 11, 6), eyes="squint", wing="up", sq=2, tuft="up"),
    S(gum=None, string="droop", bits=(2, 11, 7), eyes="shock", beak="open", wing="upmid", tuft="flat"),
    S(gum=None, string="c", bits=(3, 11, 8), eyes="down", wing="mid", sq=-1, cls="0"),
    S(gum=None, string="b", bits=(4, 11, 9), eyes="down", wing="downmid", sq=-2, tuft="up", cls="0",
      feet="fly", feet2="trail"),
    S(gum=None, string="a", eyes="shock", beak="open", wing="down", sq=-1, lift=1, tuft="up", cls="0",
      feet="trail", feet2="fly"),
    S(gum=None, string="b", eyes="down", wing="mid", sq=-2, tuft="up", cls="0", feet="fly", feet2="trail"),
    S(gum=None, string="c", eyes="down", wing="upmid", sq=-1, lift=1, tuft="up", cls="0", feet="trail", feet2="fly"),
    None,  # = fall frame 0, filled below
]
INFLATE = [
    S(gum=None, string=None, cls="0", sq=-1, wing="upmid", eyes="up", feet="stand"),
    S(gum=None, string=None, sq=1, wing="downmid", eyes="shut", beak="open", feet="stand", beakbub="b2"),
    S(gum=None, string=None, sq=2, wing="down", eyes="shut", beak="open", feet="stand", beakbub="b3"),
    S(gum=None, string=None, sq=2, wing="down", eyes="squint", beak="open", feet="stand", beakbub="b5",
      tuft="flat"),
    S(gum="b5", gpos=(14, 7), sq=1, wing="downmid", eyes="shut", feet="stand"),
    S(gum="lobe", gpos=(10, 3), wing="mid", eyes="up", feet="stand"),
    S(gum="one", gpos=(8, 1), cls="1", sq=-1, wing="upmid", eyes="up", feet="stand"),
    S(gum="wide", sq=-1, wing="up", eyes="up", feet="fly"),
    S(gum="two", cls="2", wing="upmid", lift=1, eyes="shock"),
    S(gum="two", cls="2", wing="mid", sq=-1, lift=1, glift=1, tuft="flat", feet="trail"),
    S(gum="two", cls="2", wing="downmid", lift=2, glift=1),
    dict(FLAP2[4]),
    dict(FLAP2[6]),
    dict(FLAP2[7]),
]
_fw = ["up", "mid", "down", "downmid", "upmid", "up", "mid", "down", "downmid", "upmid"]
_fs = [-2, -1, -1, -2, -2, -1, -1, -2, -2, -1]
_fl = [0, 0, 1, 1, 0, 0, 0, 1, 1, 0]
_fe = ["down", "down", "shock", "shock", "down", "down", "down", "shock", "shut", "down"]
_fst = ["a", "b", "c", "b", "a", "c", "b", "a", "b", "c"]
FALL = [S(gum=None, cls="0", string=_fst[i], wing=_fw[i], sq=_fs[i], lift=_fl[i], eyes=_fe[i],
          beak="open" if _fe[i] == "shock" else "shut", tuft="up",
          feet="trail" if (i // 2) % 2 == 0 else "fly", feet2="fly" if (i // 2) % 2 == 0 else "trail")
        for i in range(10)]
POP1[9] = dict(FALL[0])
IDLE = [S(gum=None, string=None, cls="0", wing="mid", feet="stand", wad=2)]

CLIPS = [("flap2", FLAP2), ("flap1", FLAP1), ("pop2", POP2), ("pop1", POP1), ("inflate", INFLATE),
         ("fall", FALL), ("idle", IDLE)]
SPECS = [s for _, c in CLIPS for s in c]
assert len(SPECS) == 63, len(SPECS)
assert [len(c) for _, c in CLIPS] == META["tables"]["clip_count"]
FIRST = META["tables"]["clip_first"]
TICKS = META["tables"]["frame_ticks"]


# ------------------------------------------------------------------ render
def render(px, pal):
    im = Image.new("RGBA", (FW, FH), (0, 0, 0, 0))
    for (x, y), ch in px.items():
        im.putpixel((x, y), pal[LETTERS.index(ch)] + (255,))
    return im


def up(im, n):
    return im.resize((im.width * n, im.height * n), Image.NEAREST)


def box_of(px, letters):
    pts = [p for p, ch in px.items() if ch in letters]
    if not pts:
        return None
    return (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))


def main():
    for g in list(GUM.values()):
        assert len({len(r) for r in g[0]}) == 1, g[0]
    for name, (_, _, g) in WING.items():
        assert len({len(r) for r in g}) == 1, name
    assert all(len(r) == 16 for r in BODY) and len(BODY) == 16
    assert all(len(r) == 7 for e in EYES.values() for r in e)
    assert all(len(r) == 16 for t in TUFT.values() for r in t)

    frames = [compose(**s) for s in SPECS]
    for i, (px, info) in enumerate(frames):
        if info["clipped"]:
            print("frame", i, "clipped", info["clipped"])

    rows = (63 + COLS - 1) // COLS
    sheet = Image.new("RGBA", (COLS * FW, rows * FH * 2), (0, 0, 0, 0))
    anims = {}
    for wi, who in enumerate(("player", "cpu")):
        rects = []
        for i, (px, _) in enumerate(frames):
            x, y = (i % COLS) * FW, (i // COLS) * FH + wi * rows * FH
            sheet.alpha_composite(render(px, PALS[who]), (x, y))
            rects.append({"x": x, "y": y, "w": FW, "h": FH})
        anims[who] = rects
    sheet.save(os.path.join(HERE, "sootling_small_sheet.png"))

    defines = dict(META["defines"])
    defines.update({"ART_W": FW, "ART_H": FH, "FEET_ROW": FH - 1, "BOX_FIRST_COL": 10, "BOX_LAST_COL": 13})
    out = {
        "source": "thoughts/shared/drafts/2026-11-10-sootling-small-sheet/draw_sheet.py (draft; same clips, frame "
                  "order and timing as assets/flier/sootling_sheet.json, frame size 24 x 32)",
        "animations": anims,
        "palettes": META["palettes"],
        "defines": defines,
        "tables": META["tables"],
    }
    json.dump(out, open(os.path.join(HERE, "sootling_small_sheet.json"), "w"), indent=1)

    # colours used
    used = set()
    for px, _ in frames:
        used |= set(px.values())
    unused = [c for c in LETTERS if c not in used]

    # contact sheet 4x, player on dark, rival on a bright sky tone
    lab = 64
    maxn = max(len(c) for _, c in CLIPS)
    cw, ch = FW * 4 + 4, FH * 4 + 4
    contact = Image.new("RGBA", (lab + maxn * cw + 4, len(CLIPS) * 2 * ch + 4), (22, 22, 30, 255))
    dr = ImageDraw.Draw(contact)
    for ci, (name, clip) in enumerate(CLIPS):
        for wi, who in enumerate(("player", "cpu")):
            y = (ci * 2 + wi) * ch + 4
            bg = (22, 22, 30, 255) if wi == 0 else (150, 190, 230, 255)
            dr.rectangle([lab, y - 2, lab + len(clip) * cw + 2, y + FH * 4 + 1], fill=bg)
            dr.text((4, y + 4), name, fill=(235, 235, 235, 255))
            dr.text((4, y + 18), who, fill=(150, 150, 160, 255))
            dr.text((4, y + 32), "%d..%d" % (FIRST[ci], FIRST[ci] + len(clip) - 1), fill=(150, 150, 160, 255))
            for fi in range(len(clip)):
                px, _ = frames[FIRST[ci] + fi]
                contact.alpha_composite(up(render(px, PALS[who]), 4), (lab + 2 + fi * cw, y))
    contact.save(os.path.join(HERE, "contact_4x.png"))

    # 1x strip on three grounds (dark, mid, bright) for the size check
    one = Image.new("RGBA", (COLS * FW * 2, rows * FH * 3), (0, 0, 0, 255))
    for bi, bg in enumerate([(16, 16, 28, 255), (58, 68, 110, 255), (236, 232, 200, 255)]):
        ImageDraw.Draw(one).rectangle([0, bi * rows * FH, one.width, (bi + 1) * rows * FH - 1], fill=bg)
        one.alpha_composite(sheet.crop((0, 0, COLS * FW, rows * FH)), (0, bi * rows * FH))
        one.alpha_composite(sheet.crop((0, rows * FH, COLS * FW, 2 * rows * FH)), (COLS * FW, bi * rows * FH))
    one.save(os.path.join(HERE, "sheet_on_grounds_1x.png"))

    # GIFs 3x: player on dark, rival on bright, side by side
    for name in ("flap2", "pop2", "pop1", "inflate", "fall"):
        ci = [n for n, _ in CLIPS].index(name)
        ims, durs = [], []
        for fi in range(len(CLIPS[ci][1])):
            px, _ = frames[FIRST[ci] + fi]
            f = Image.new("RGBA", (FW * 2 + 12, FH + 8), (22, 22, 30, 255))
            ImageDraw.Draw(f).rectangle([FW + 6, 0, f.width, f.height], fill=(150, 190, 230, 255))
            f.alpha_composite(render(px, PALS["player"]), (4, 4))
            f.alpha_composite(render(px, PALS["cpu"]), (FW + 8, 4))
            ims.append(up(f, 3).convert("P", palette=Image.ADAPTIVE, colors=48))
            durs.append(round(TICKS[FIRST[ci] + fi] * 1000 / 60))
        if not META["tables"]["clip_loop"][ci]:
            durs[-1] += 600
        ims[0].save(os.path.join(HERE, "anim_%s_3x.gif" % name), save_all=True, append_images=ims[1:],
                    duration=durs, loop=0, disposal=1)

    # ------------------------------------------------------------ measure
    def tiles(xoff):
        seen, non_empty = set(), 0
        for px, _ in frames:
            grid = [[" "] * 32 for _ in range(32)]
            for (x, y), c in px.items():
                grid[y][x + xoff] = c
            for ty in (0, 16):
                for tx in (0, 16):
                    t = tuple("".join(grid[ty + r][tx:tx + 16]) for r in range(16))
                    if any(c != " " for row in t for c in row):
                        non_empty += 1
                        seen.add(t)
        return non_empty, len(seen)

    def rng(boxes):
        boxes = [b for b in boxes if b]
        if not boxes:
            return "none"
        return "cols %d..%d, rows %d..%d" % (min(b[0] for b in boxes), max(b[2] for b in boxes),
                                             min(b[1] for b in boxes), max(b[3] for b in boxes))

    def one_box(b):
        return "none" if not b else "cols %d..%d, rows %d..%d (%d x %d)" % (b[0], b[2], b[1], b[3],
                                                                             b[2] - b[0] + 1, b[3] - b[1] + 1)

    L = ["Small Sootling sheet, measured by draw_sheet.py. Frame 24 x 32, 63 frames, frame pixels (col 0 left, row 0 top).",
         "Art centred on the line between columns 11 and 12 (hit box columns 10..13, the rest body is cols 4..19).",
         "Feet bottom on row 31 at lift 0 (tucked feet, flap frames 0 and 7: row 30); flight frames lift the body 1..2 px.",
         "fur body = bounding box of the five fur colours (tuft included); gum = the bubble grid as placed (string,",
         "wad and burst specks not counted); feet = the foot pixels as placed.",
         ""]
    rest = {"2": 1, "1": 9, "0": 62}
    names = {"2": "two gums", "1": "one gum", "0": "no gum"}
    for cls in "210":
        idx = [i for i, (_, info) in enumerate(frames) if info["cls"] == cls]
        px, info = frames[rest[cls]]
        L.append("%s: frames %s" % (names[cls], " ".join(str(i) for i in idx)))
        L.append("  reference frame %d: feet %s" % (rest[cls], one_box(info["feet"])))
        L.append("                      gum  %s" % one_box(info["gum"]))
        L.append("                      fur  %s" % one_box(box_of(px, "abcde")))
        fur_no_tuft = (info["body"][0] + 1, info["body"][1] + 1, info["body"][2] - 1, info["body"][3] - 1)
        L.append("                      fur without tuft %s" % one_box(fur_no_tuft))
        L.append("  over the class:     feet %s" % rng([frames[i][1]["feet"] for i in idx]))
        L.append("                      gum  %s" % rng([frames[i][1]["gum"] for i in idx]))
        L.append("                      fur  %s" % rng([box_of(frames[i][0], "abcde") for i in idx]))
        L.append("")
    tr = [i for i, (_, info) in enumerate(frames) if info["cls"] == "x"]
    L.append("transition frames (pop, inflate; not in a class): %s" % " ".join(str(i) for i in tr))
    L.append("")
    ne0, u0 = tiles(0)
    ne4, u4 = tiles(4)
    L.append("16 x 16 tiles, one palette (the rival reuses the tiles), frame padded to 32 x 32, 4 slots per frame, 252 slots:")
    L.append("  frame at x 0 (cols 0..23 of 32):  %d non-empty, %d unique" % (ne0, u0))
    L.append("  frame at x 4 (centred in 32):     %d non-empty, %d unique" % (ne4, u4))
    L.append("  current 32 x 48 sheet: 341 non-empty, 294 unique (numbers.txt of the key-frame draft)")
    L.append("  identical frames by design: 27 = 8, 37 = 52, 49 = 4, 50 = 6, 51 = 7")
    L.append("")
    L.append("palette entries not used by any frame: %s" % (" ".join(unused) if unused else "none (all 15 used)"))
    L.append("sheet %d x %d, player rows 0..%d, rival below" % (sheet.width, sheet.height, rows * FH - 1))
    open(os.path.join(HERE, "measure.txt"), "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
