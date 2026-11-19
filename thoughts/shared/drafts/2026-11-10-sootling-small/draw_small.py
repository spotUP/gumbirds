#!/opt/homebrew/bin/python3.14 -I
"""Small Sootling drafts: 24x32 (10 key frames) and 20x28 (4 key frames).

Hand-placed pixel grids, not a scaled copy of the 32x48 sheet. Palette is read
from assets/flier/sootling_sheet.json (15 colours per sprite palette).
Run from anywhere: /opt/homebrew/bin/python3.14 -I draw_small.py
Writes every PNG / GIF in this folder and numbers.txt.
"""
import json
import os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
SHEET = os.path.join(ROOT, "assets", "flier", "sootling_sheet.png")
SHEET_JSON = os.path.join(ROOT, "assets", "flier", "sootling_sheet.json")
BACKDROP = os.path.join(ROOT, "thoughts", "shared", "drafts", "2026-11-10-islands-final", "backdrop_moon_384_1x.png")
ISLANDS = os.path.join(ROOT, "assets", "islands", "sheet_roof_1x.png")
HAZARD = os.path.join(ROOT, "assets", "hazard", "frames_water_1x.png")

# palette index letters, same order as the sheet palette
#  k outline | a b c d e fur dark..light | r o y beak, wing, feet | p q m n h gum dark..light | w white
LETTERS = "kabcderoypqmnhw"

META = json.load(open(SHEET_JSON))
PALS = {name: [tuple(c) for c in cols] for name, cols in META["palettes"].items()}


def put(img, grid, x0, y0, pal):
    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            if ch in ". ":
                continue
            px, py = x0 + x, y0 + y
            if 0 <= px < img.width and 0 <= py < img.height:
                img.putpixel((px, py), pal[LETTERS.index(ch)] + (255,))


def dots(img, pts, pal):
    for x, y, ch in pts:
        if 0 <= x < img.width and 0 <= y < img.height:
            img.putpixel((x, y), pal[LETTERS.index(ch)] + (255,))


# ---------------------------------------------------------------- 24 x 32
BODY24 = [
    ".....k...k......",
    "....kek.kdk.....",
    "....kdkkkdkk....",
    "..kkeeedddcckk..",
    ".kdeeedddccccbk.",
    "kdeebkkkkbkkkkbk",
    "kdedbeeeebeeeeak",
    "kddcbeekebeekeak",
    "kdccbeekebeekeak",
    "kccbbdeeebdeeeak",
    "kcbbbkkkkakkkkak",
    "kbcbbbcbbbbabaak",
    "kbbbabbbabaaaaak",
    ".kbabbabaaaaaak.",
    "..kkaabaaaaakk..",
    "....kkkkkkkk....",
]
EYES24 = {  # rows 5..8, cols 5..13 of the body
    "open":  ["eeeebeeee", "eekebeeke", "eekebeeke", "deeebdeee"],
    "lids":  ["ccccbcccc", "ccccbcccc", "eekebeeke", "deeebdeee"],
    "shock": ["eeeebeeee", "ekeebekee", "eeeebeeee", "deeebdeee"],
    "down":  ["eeeebeeee", "eeeebeeee", "eekebeeke", "dekebdeke"],
}
BEAK24 = ["kk.", "yok", "rk."]
WING24 = {
    "up":   (2, 2, ["kk...", "kyyk.", "kyook", ".kork", "..kk."]),
    "mid":  (2, 7, [".kkkk", "kyyok", "kyork", ".kkk."]),
    "down": (2, 8, ["..kk.", ".kork", "kyook", "kyyk.", "kk..."]),
}
GUM2_24 = [
    "..kkkkk...kkkkk..",
    ".knnnmmk.knnnmmk.",
    "knhwnnmmknhwnnmmk",
    "knhhnmmmmnhhnmmmk",
    "knnnmmmqmnnnmmmqk",
    "kmnmmmqqmmnmmmqqk",
    "kmmmmqqpkmmmmqqpk",
    ".kmqqqpk.kmqqqpk.",
    "..kkkkk...kkkkk..",
]
GUM1_24 = [
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
]
BURST24 = [
    "..m.....n..",
    ".....h.....",
    "m..n...m..n",
    "...........",
    ".h...w...m.",
    "...........",
    "n..m...n..m",
    ".....m.....",
    "..n.....m..",
]
STRING2_24 = [(15, 10), (16, 11), (16, 12), (17, 13), (17, 14), (17, 15), (18, 16), (18, 17)]
STRING1_24 = [(13, 11), (14, 12), (15, 13), (16, 14), (17, 15), (17, 16), (18, 17)]


def frame24(pal, gum=2, wing="mid", eyes="open", feet="fly", squash=False, lift=0,
            burst=False, streak=False, wad=False, dust=False):
    im = Image.new("RGBA", (24, 32), (0, 0, 0, 0))
    bx, by = 4, 14 - lift
    gy = -lift
    # gum first, body covers the string end
    if gum == 2:
        put(im, GUM2_24, 3, 1 + gy, pal)
        for x, y in STRING2_24:
            dots(im, [(x, y + gy, "n"), (x + 1, y + gy, "p")], pal)
    elif gum == 1:
        put(im, GUM1_24, 7, 1 + gy, pal)
        for x, y in STRING1_24:
            dots(im, [(x, y + gy, "n"), (x + 1, y + gy, "p")], pal)
    if burst:
        put(im, BURST24, 6, 1, pal)
    body = list(BODY24)
    if squash:
        body = body[:11] + body[12:]
        by += 1
    put(im, body, bx, by, pal)
    by += 1  # offsets below count from the row under the tuft tips
    put(im, EYES24[eyes], bx + 5, by + 5, pal)
    put(im, BEAK24, bx + 15, by + 8, pal)
    wx, wy, wg = WING24[wing]
    put(im, wg, wx, by + wy, pal)
    if gum:
        dots(im, [(18, by + 3, "n"), (19, by + 4, "m")], pal)  # string end at the brow
    if wad:
        dots(im, [(21, by + 7, "m"), (22, by + 7, "n"), (22, by + 6, "h")], pal)
    if streak:  # fur pulled up while falling, loose string
        dots(im, [(bx + 5, by - 2, "k"), (bx + 5, by - 1, "e"), (bx + 9, by - 2, "k"), (bx + 9, by - 1, "d"),
                  (19, by + 2, "n"), (19, by + 1, "m"), (20, by, "m"), (20, by - 2, "q")], pal)
    fy = 30 - lift
    if feet == "fly":
        dots(im, [(bx + 5, fy, "r"), (bx + 5, fy + 1, "o"), (bx + 10, fy, "r"), (bx + 10, fy + 1, "o")], pal)
    elif feet == "stand":
        dots(im, [(bx + 5, fy, "r"), (bx + 4, fy + 1, "y"), (bx + 5, fy + 1, "o"), (bx + 6, fy + 1, "o"),
                  (bx + 10, fy, "r"), (bx + 9, fy + 1, "y"), (bx + 10, fy + 1, "o"), (bx + 11, fy + 1, "o")], pal)
    elif feet == "walk1":
        dots(im, [(bx + 4, fy, "r"), (bx + 3, fy + 1, "y"), (bx + 4, fy + 1, "o"),
                  (bx + 11, fy, "r"), (bx + 11, fy + 1, "y"), (bx + 12, fy + 1, "o"), (bx + 13, fy + 1, "o")], pal)
    elif feet == "walk2":
        dots(im, [(bx + 6, fy, "y"), (bx + 7, fy, "o"),
                  (bx + 9, fy, "r"), (bx + 8, fy + 1, "y"), (bx + 9, fy + 1, "o"), (bx + 10, fy + 1, "o")], pal)
    elif feet == "wide":
        dots(im, [(bx + 3, fy + 1, "y"), (bx + 4, fy + 1, "o"), (bx + 5, fy + 1, "o"),
                  (bx + 10, fy + 1, "y"), (bx + 11, fy + 1, "o"), (bx + 12, fy + 1, "o")], pal)
    if dust:
        dots(im, [(1, 31, "d"), (2, 30, "e"), (0, 29, "c"), (21, 31, "d"), (22, 30, "e"), (23, 28, "c")], pal)
    return im


FRAMES24 = [
    ("idle", dict(gum=0, wing="mid", feet="stand", wad=True)),
    ("flap up", dict(gum=2, wing="up")),
    ("flap down", dict(gum=2, wing="down", lift=1)),
    ("glide", dict(gum=2, wing="mid")),
    ("fall, no gum", dict(gum=0, wing="up", eyes="down", streak=True)),
    ("walk 1", dict(gum=2, wing="mid", feet="walk1")),
    ("walk 2", dict(gum=2, wing="mid", feet="walk2", lift=1)),
    ("one-gum float", dict(gum=1, wing="mid")),
    ("pop reaction", dict(gum=0, wing="up", eyes="shock", burst=True)),
    ("landing", dict(gum=2, wing="down", eyes="lids", feet="wide", squash=True, dust=True)),
]

# ---------------------------------------------------------------- 20 x 28
BODY20 = [
    "...k...k.....",
    "..kdkkkdkk...",
    ".kdeeddcccbk.",
    "kdebkkkbkkkak",
    "kddbeeebeeeak",
    "kdcbekebekeak",
    "kccbdeebdeeak",
    "kcbbkkkakkkak",
    "kbbcbbbabaaak",
    ".kbabbaaaaak.",
    "..kkkkkkkkk..",
]
EYES20 = {"open": ["eeebeee", "ekebeke", "deebdee"], "down": ["eeebeee", "eeebeee", "dkebdke"]}
WING20 = {
    "up":   (1, 1, ["kk..", "kyok", ".kok", "..k."]),
    "mid":  (1, 5, [".kkk", "kyok", ".kk."]),
    "down": (1, 6, ["..k.", ".kok", "kyok", "kk.."]),
}
GUM2_20 = [
    "..kkk...kkk..",
    ".knnmk.knnmk.",
    "knhnmmknhnmmk",
    "knnmmqmnnmmqk",
    "kmmmqqkmmmqqk",
    ".kmqpk.kmqpk.",
    "..kkk...kkk..",
]
STRING2_20 = [(12, 10), (13, 11), (13, 12), (14, 13), (14, 14), (14, 15), (15, 16)]


def frame20(pal, gum=2, wing="mid", eyes="open", feet="fly", lift=0, streak=False, wad=False):
    im = Image.new("RGBA", (20, 28), (0, 0, 0, 0))
    bx, by = 3, 15 - lift
    if gum == 2:
        put(im, GUM2_20, 3, 3 - lift, pal)
        for x, y in STRING2_20:
            dots(im, [(x, y - lift, "n"), (x + 1, y - lift, "p")], pal)
    put(im, BODY20, bx, by, pal)
    put(im, EYES20[eyes], bx + 4, by + 4, pal)
    put(im, BEAK24, bx + 12, by + 5, pal)
    wx, wy, wg = WING20[wing]
    put(im, wg, wx, by + wy, pal)
    if gum:
        dots(im, [(15, by + 2, "n")], pal)
    if wad:
        dots(im, [(18, by + 4, "m"), (18, by + 3, "h")], pal)
    if streak:
        dots(im, [(bx + 3, by - 1, "k"), (bx + 3, by, "e"), (bx + 7, by - 1, "k"), (bx + 7, by, "d"),
                  (16, by + 1, "n"), (16, by, "m"), (17, by - 2, "q")], pal)
    fy = 26 - lift
    if feet == "fly":
        dots(im, [(bx + 4, fy, "r"), (bx + 4, fy + 1, "o"), (bx + 8, fy, "r"), (bx + 8, fy + 1, "o")], pal)
    else:
        dots(im, [(bx + 4, fy, "r"), (bx + 3, fy + 1, "y"), (bx + 4, fy + 1, "o"),
                  (bx + 8, fy, "r"), (bx + 7, fy + 1, "y"), (bx + 8, fy + 1, "o")], pal)
    return im


FRAMES20 = [
    ("idle", dict(gum=0, wing="mid", feet="stand", wad=True)),
    ("flap up", dict(gum=2, wing="up")),
    ("flap down", dict(gum=2, wing="down", lift=1)),
    ("fall, no gum", dict(gum=0, wing="up", eyes="down", streak=True)),
]


# ---------------------------------------------------------------- helpers
def up(im, n):
    return im.resize((im.width * n, im.height * n), Image.NEAREST)


def cur_frame(sheet, i, who):
    r = META["animations"][who][i]
    return sheet.crop((r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"]))


def strip(frames, bg, gap=4):
    w = sum(f.width for f in frames) + gap * (len(frames) + 1)
    h = max(f.height for f in frames) + gap * 2
    out = Image.new("RGBA", (w, h), bg)
    x = gap
    for f in frames:
        out.alpha_composite(f, (x, h - gap - f.height))
        x += f.width + gap
    return out


def stack(rows, bg, gap=0):
    w = max(r.width for r in rows)
    out = Image.new("RGBA", (w, sum(r.height for r in rows) + gap * (len(rows) - 1)), bg)
    y = 0
    for r in rows:
        out.alpha_composite(r, (0, y))
        y += r.height + gap
    return out


def keyed(path):
    im = Image.open(path).convert("RGBA")
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            if px[x, y][:3] == (255, 0, 255):
                px[x, y] = (0, 0, 0, 0)
    return im


def body_box(im):
    """bounding box of fur pixels (palette entries 1..5) in a frame"""
    fur = set(PALS["player"][1:6]) | set(PALS["cpu"][1:6])
    xs, ys = [], []
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            if px[x, y][3] and px[x, y][:3] in fur:
                xs.append(x)
                ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


def unique_tiles(frames):
    seen = set()
    total = 0
    for f in frames:
        for ty in range(0, f.height, 16):
            for tx in range(0, f.width, 16):
                t = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
                t.alpha_composite(f.crop((tx, ty, min(tx + 16, f.width), min(ty + 16, f.height))))
                if t.getbbox() is None:
                    continue
                total += 1
                seen.add(t.tobytes())
    return total, len(seen)


def main():
    P, C = PALS["player"], PALS["cpu"]
    DARK = (24, 24, 30, 255)
    SKY = (60, 70, 110, 255)
    sheet = Image.open(SHEET).convert("RGBA")

    f24 = {who: [frame24(pal, **kw) for _, kw in FRAMES24] for who, pal in (("player", P), ("cpu", C))}
    f20 = {who: [frame20(pal, **kw) for _, kw in FRAMES20] for who, pal in (("player", P), ("cpu", C))}

    # sheets (transparent, 1x) and contact sheets on dark and on a sky tone
    for name, fr in (("small_24x32", f24), ("small_20x28", f20)):
        w, h = fr["player"][0].size
        sh = Image.new("RGBA", (w * len(fr["player"]), h * 2), (0, 0, 0, 0))
        for r, who in enumerate(("player", "cpu")):
            for i, f in enumerate(fr[who]):
                sh.alpha_composite(f, (i * w, r * h))
        sh.save(os.path.join(HERE, name + "_sheet_1x.png"))
        con = stack([strip(fr["player"], DARK), strip(fr["cpu"], DARK),
                     strip(fr["player"], SKY), strip(fr["cpu"], SKY)], DARK)
        con.save(os.path.join(HERE, name + "_contact_1x.png"))
        up(con, 6).save(os.path.join(HERE, name + "_contact_6x.png"))

    # same poses, three sizes: idle, flap up, flap down, fall
    cur_idx = [62, 0, 4, 52]
    s24_idx = [0, 1, 2, 4]
    rows = []
    for who in ("player", "cpu"):
        rows.append(strip([cur_frame(sheet, i, who) for i in cur_idx] + [f24[who][i] for i in s24_idx] + f20[who], SKY, 6))
    cmp_ = stack(rows, SKY)
    cmp_.save(os.path.join(HERE, "compare_sizes_1x.png"))
    up(cmp_, 5).save(os.path.join(HERE, "compare_sizes_5x.png"))

    # ------------------------------------------------ arena mock-ups, camera x 32
    CAM = 32
    back = Image.open(BACKDROP).convert("RGBA").crop((CAM, 0, CAM + 320, 224))
    isl = keyed(ISLANDS)
    thin_y = {64: 128, 80: 144, 96: 160, 112: 176}
    stage = [(0, 148, 80), (304, 164, 80), (136, 128, 112), (32, 92, 80),
             (280, 108, 80), (144, 68, 96), (0, 36, 64), (320, 52, 64)]  # src/core/stage.c
    for x, y, w in stage:
        piece = isl.crop((0, thin_y[w], w, thin_y[w] + 16))
        back.alpha_composite(piece, (x - CAM, y - 4)) if x - CAM > -w else None
        if x - CAM < 0:
            back.alpha_composite(piece.crop((CAM - x, 0, w, 16)), (0, y - 4))
    haz = keyed(HAZARD).crop((0, 0, 128, 32))
    for x in range(-(CAM % 128), 320, 128):
        back.alpha_composite(haz, (x, 192))  # HAZARD_STRIP_Y 192, src/hazard.h

    # flier spots: (centre world x, feet world y, palette, pose key, flip)
    spots = [(262, 100, "player", "flap", False),   # P1 between the two right islands
             (176, 128, "cpu", "idle", False),      # rival standing on the middle island
             (104, 156, "cpu", "one", True),        # rival on one gum, low over the water
             (318, 108, "cpu", "walk", True)]       # rival walking on the right island
    poses = {
        "now": {"flap": 0, "idle": 62, "one": 8, "walk": 62},
        "24": {"flap": 1, "idle": 0, "one": 7, "walk": 0},
        "20": {"flap": 1, "idle": 0, "one": 1, "walk": 0},
    }
    mocks = []
    for key in ("now", "24", "20"):
        m = back.copy()
        for cx, fy, who, pose, flip in spots:
            i = poses[key][pose]
            f = cur_frame(sheet, i, who) if key == "now" else (f24 if key == "24" else f20)[who][i]
            if flip:
                f = f.transpose(Image.FLIP_LEFT_RIGHT)
            m.alpha_composite(f, (cx - CAM - f.width // 2, fy - f.height))
        m.save(os.path.join(HERE, "mock_%s_1x.png" % key))
        up(m, 3).save(os.path.join(HERE, "mock_%s_3x.png" % key))
        mocks.append(m)
    side = Image.new("RGBA", (320 * 3 + 16, 224), DARK)
    for n, m in enumerate(mocks):
        side.alpha_composite(m, (n * 328, 0))
    side.save(os.path.join(HERE, "mock_side_by_side_1x.png"))
    up(side, 3).save(os.path.join(HERE, "mock_side_by_side_3x.png"))

    # ------------------------------------------------ flap GIF, current beside 24x32, 3x
    seq24 = [1, 1, 3, 2, 2, 2, 3, 1]  # up, up, glide, down, down, down, glide, up
    gif = []
    for t in range(8):
        can = Image.new("RGBA", (32 + 24 + 20 + 32 + 24 + 20, 56), SKY)
        x = 6
        for who in ("player", "cpu"):
            a = cur_frame(sheet, t, who)
            b = f24[who][seq24[t]]
            can.alpha_composite(a, (x, 52 - 48))
            can.alpha_composite(b, (x + 38, 52 - 32))
            x += 76
        gif.append(up(can, 3).convert("RGB").quantize(64))
    gif[0].save(os.path.join(HERE, "anim_flap_now_vs_24x32_3x.gif"), save_all=True,
                append_images=gif[1:], duration=67, loop=0)

    # ------------------------------------------------ numbers
    cur_frames = [cur_frame(sheet, i, "player") for i in range(63)]
    cb = body_box(cur_frames[62])
    b24 = body_box(f24["player"][0])
    b20 = body_box(f20["player"][0])
    tot_now, uniq_now = unique_tiles(cur_frames)
    t24, u24 = unique_tiles(f24["player"])
    t20, u20 = unique_tiles(f20["player"])
    L = []
    L.append("Small Sootling drafts, numbers measured by draw_small.py")
    L.append("Screen 320 x 224, world 384 x 180 (water line y 180, hazard strip drawn at y 192).")
    L.append("")
    L.append("size      frame    fur body (idle, measured)   body w / screen w   frame h / world h   frames stacked in world   fur h / world h")
    for name, (fw, fh), bb in (("now", (32, 48), cb), ("24x32", (24, 32), b24), ("20x28", (20, 28), b20)):
        bw, bh = bb[2] - bb[0] + 1, bb[3] - bb[1] + 1
        L.append("%-8s  %2dx%2d    %2d wide x %2d tall           %5.1f%% (%4.1f fit)    %5.1f%%              %4.2f                      %5.1f%%"
                 % (name, fw, fh, bw, bh, 100.0 * bw / 320, 320.0 / bw, 100.0 * fh / 180, 180.0 / fh, 100.0 * bh / 180))
    L.append("")
    L.append("Tiles (16 x 16 Neo Geo tiles, 63 frames, one palette; the rival reuses the tiles):")
    L.append("  now   32x48: 2 strips x 3 tiles = 6 per frame, 378 slots; measured on the real sheet: %d non-empty, %d unique" % (tot_now, uniq_now))
    r24 = uniq_now * 4.0 / 6.0
    L.append("  24x32      : 2 strips x 2 tiles = 4 per frame, 252 slots; estimate %d unique (real unique count x 4/6)" % round(r24))
    L.append("  20x28      : 2 strips x 2 tiles = 4 per frame, 252 slots; estimate %d unique. Same as 24x32: 20 px still needs" % round(r24))
    L.append("               two 16 px strips and 28 px still needs two tile rows. 20x28 saves no tiles and no sprites over 24x32.")
    L.append("  drafts only: 24x32 %d non-empty / %d unique in 10 frames; 20x28 %d / %d in 4 frames" % (t24, u24, t20, u20))
    L.append("  Sprites per flier: 2 strips at every size (per-scanline load is unchanged); only the height drops 3 -> 2 tiles.")
    L.append("")
    L.append("Headroom, stage table now: closest stacked standing lines are 56 px apart (islands at y 52 and 108).")
    L.append("  now 48 px frame leaves 8 px; 24x32 leaves 24 px; 20x28 leaves 28 px.")
    L.append("")
    L.append("Detail lost against the 32x48 sheet:")
    L.append("  eyes      now about 6x7 px each with a 2x3 pupil and a shaded lower lid; 24x32: 3x4 with a 1x2 pupil,")
    L.append("            one shade pixel; 20x28: 2x3 with a 1 px pupil, expressions reduce to open / looking down.")
    L.append("  brows     now a separate brow line that tilts; 24x32: gone, the eye box top edge stands in; lids only as a")
    L.append("            flat bar (landing). 20x28: none.")
    L.append("  fur       now 5 shades in dithered clusters with a rim; 24x32: 5 shades, clusters of 2-4 px, no dither;")
    L.append("            20x28: 5 entries used but only about 3 read (light cap, mid, dark belly).")
    L.append("  tufts     now 2 tufts of 3-4 px with light tips; 24x32: 2 tufts of 2 px; 20x28: 1-2 px bumps.")
    L.append("  wing      now a 9 px lozenge with 3 shades; 24x32: 4-5 px, yellow / orange / 1 px red; 20x28: 3 px, 2 shades.")
    L.append("  beak      now 3 shades; 24x32 and 20x28: 2x2 px, yellow / orange / red.")
    L.append("  feet      now 3 px toes with shadow; 24x32: leg pixel + 3 px foot; 20x28: leg pixel + 2 px foot.")
    L.append("  gum       now each lobe about 12 px with 5 shades + sparkle; 24x32: 9 px lobes, 5 shades + 1 white pixel;")
    L.append("            20x28: 7 px lobes, 4 shades read, the pinch between lobes is 1 px.")
    L.append("  string    now 2 px with outline; 24x32 and 20x28: 1 px light + 1 px dark, no outline.")
    open(os.path.join(HERE, "numbers.txt"), "w").write("\n".join(L) + "\n")
    print("\n".join(L[:8]))
    print("\n".join(L[9:16]))


if __name__ == "__main__":
    main()
