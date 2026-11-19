#!/opt/homebrew/bin/python3.14 -I
"""Final round clear banner for Gumbirds (variants D and C of the draft round combined).

Fix layer only: 8x8 tiles, 40x28 cells, one 16-colour palette per tile, no flip, no scaling.

Run: /opt/homebrew/bin/python3.14 -I draw_round_clear_banner_final.py   (from any directory)

Reads (read only):
  assets/font/fix_font_sheet.png + fix_font.json   the Gumdrop fix font and its five palettes
  thoughts/shared/drafts/2026-11-10-hud-title-final/hud2p_<mood>_1x.png   arena mock-ups with the HUD (backdrop)
Writes into this folder: GIF and PNG files, index.html, numbers.txt, banner_spec.txt.

The banner is a grid of (tile index, palette name) cells per game frame, drawn the way the fix layer draws.
build(frame, case, round_no) is the single source of the layout: pictures, numbers and banner_spec.txt all come from it.
"""
import json
import os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
SHEET = os.path.join(ROOT, "assets/font/fix_font_sheet.png")
META = os.path.join(ROOT, "assets/font/fix_font.json")
BACKDROP = os.path.join(ROOT, "thoughts/shared/drafts/2026-11-10-hud-title-final/hud2p_%s_1x.png")
MOODS = ["dusk", "moon", "storm"]
COLS, ROWS = 40, 28
FREEZE_FRAMES = 120          # decided rule: play freezes 2 seconds
BACKED = 96                  # backed copy of a glyph tile = its index + 96
TALL_TOP, TALL_BOTTOM = 64, 80
PLATE_SLOT = 13              # palette slot of the navy plate in every backed tile
POP_BURST_INDEX = 75         # first empty slot of the fix sheet (right after s:rule = 74)

# ---- timeline (game frames, 0 = first frame of the freeze) ----
T_LETTER_STEP = 4            # letter n of the headline starts at frame 4 * n (n = 0..9)
T_STAGE = 4                  # frames per stage: gum bubble, pop burst, white flash, then pink
T_PANEL = 48                 # ribbon opens downward into the panel (last letter turns pink on this frame)
T_WINNER = 52                # winner line appears, white palette
T_WINNER_COLOUR = 56         # winner line takes the winner's palette
T_ROUND = 64                 # ROUND nn appears, white
T_BLINK = 8                  # white / gold swap period
T_STEADY = 96                # steady gold from here to frame 119
T_CLEAR = 120                # first frame after the freeze: the game clears every banner cell

# ---- layout (cells) ----
C0, C1 = 9, 30               # panel columns, frame included: 22 cells, 9 free cells on each side
R_TOP, R_HEAD, R_RULE, R_WIN, R_GAP, R_DIGIT_TOP, R_ROUND, R_BOTTOM = 10, 11, 12, 13, 14, 15, 16, 17
HEADLINE = "A L L  P O P P E D !"     # 20 cells: one blank between letters, two between the words

CASES = {
    "p1":   dict(label="Player 1 wins", text="PLAYER 1 WINS", pal="pink", icon=True),
    "p2":   dict(label="Player 2 wins", text="PLAYER 2 WINS", pal="lime", icon=True),
    "cpu":  dict(label="A computer rival wins", text="COMPUTER WINS", pal="white", icon=True),
    "draw": dict(label="No survivor (draw)", text="NO SURVIVORS", pal="dim", icon=False),
}


def load_font():
    meta = json.load(open(META))
    im = Image.open(SHEET)
    assert im.mode == "P"
    px = im.load()
    tiles = {}
    for t in range((im.width // 8) * (im.height // 8)):
        x0, y0 = (t % 16) * 8, (t // 16) * 8
        tiles[t] = tuple(tuple(px[x0 + x, y0 + y] for x in range(8)) for y in range(8))
    pals = {k: [tuple(c) for c in v] for k, v in meta["palettes"].items()}
    return meta["tiles"], tiles, pals, meta["palette_order"]


NAMES, TILES, PALS, PAL_ORDER = load_font()
assert all(v == 0 for row in TILES[POP_BURST_INDEX] for v in row), "sheet slot %d is no longer empty" % POP_BURST_INDEX
# pop burst on the navy plate: slot B (11) gum light, C (12) white, D (13) plate. Same tile as draft D.
POP_BURST_ROWS = ["DDDBDDDD", "DBDBDBDD", "DDCDCDDD", "BBDDDBBD", "DDCDCDDD", "DBDBDBDD", "DDDBDDDD", "DDDDDDDD"]
TILES[POP_BURST_INDEX] = tuple(tuple(".123456789ABCDEF".index(ch) for ch in r) for r in POP_BURST_ROWS)
NAMES["n:pop_burst"] = POP_BURST_INDEX
INDEX_NAME = {}
for _n, _i in NAMES.items():
    INDEX_NAME.setdefault(_i, _n)
for _d in range(10):
    INDEX_NAME[TALL_TOP + _d + BACKED] = "bt:%d:0" % _d
    INDEX_NAME[TALL_BOTTOM + _d + BACKED] = "bt:%d:1" % _d


class Fix:
    def __init__(self):
        self.cells = {}          # (col, row) -> (tile index, palette name)
        self.text_cells = set()

    def put(self, col, row, tile, pal, text=False):
        assert 0 <= col < COLS and 0 <= row < ROWS, (col, row)
        self.cells[(col, row)] = (tile, pal)
        if text:
            self.text_cells.add((col, row))
        else:
            self.text_cells.discard((col, row))

    def render(self):
        im = Image.new("RGBA", (COLS * 8, ROWS * 8), (0, 0, 0, 0))
        px = im.load()
        for (c, r), (t, pal) in self.cells.items():
            p = PALS[pal]
            pix = TILES[t]
            for y in range(8):
                for x in range(8):
                    v = pix[y][x]
                    if v:
                        px[c * 8 + x, r * 8 + y] = p[v - 1] + (255,)
        return im


def centred(n):
    assert (COLS - n) % 2 == 0, "odd cell count %d cannot be centred on a 40 cell grid" % n
    return (COLS - n) // 2


def winner_cells(case):
    """[(col, tile, is_text)] of the winner line. Icon (2 cells) + blank + text, or text alone."""
    c = CASES[case]
    n = len(c["text"]) + (3 if c["icon"] else 0)
    col = centred(n)
    out = []
    if c["icon"]:
        out.append((col, NAMES["p:~L"] + BACKED, True))
        out.append((col + 1, NAMES["p:~R"] + BACKED, True))
        col += 3
    for i, ch in enumerate(c["text"]):
        if ch != " ":
            out.append((col + i, NAMES["p:" + ch] + BACKED, True))
    return out


def round_cells(round_no):
    """[(col, row, tile)] of ROUND nn: always two digits (01..99) so the line is 8 cells wide, tall digits."""
    assert 1 <= round_no <= 99
    s = "ROUND %02d" % round_no
    col = centred(len(s))
    out = []
    for i, ch in enumerate(s):
        if ch == " ":
            continue
        if ch.isdigit():
            out.append((col + i, R_DIGIT_TOP, TALL_TOP + int(ch) + BACKED))
            out.append((col + i, R_ROUND, TALL_BOTTOM + int(ch) + BACKED))
        else:
            out.append((col + i, R_ROUND, NAMES["p:" + ch] + BACKED))
    return out


def headline_cells():
    """[(col, letter, n)] with n = order of arrival."""
    col = centred(len(HEADLINE))
    assert col == C0 + 1 and col + len(HEADLINE) - 1 == C1 - 1
    out, k = [], 0
    for i, ch in enumerate(HEADLINE):
        if ch != " ":
            out.append((col + i, ch, k))
            k += 1
    return out


def build(frame, case="p1", round_no=2):
    """Fix layer of the banner at a game frame (0..119)."""
    f = Fix()
    S = lambda n: NAMES["s:" + n]
    open_panel = frame >= T_PANEL
    bottom = R_BOTTOM if open_panel else R_RULE
    for c in range(C0, C1 + 1):
        e = "l" if c == C0 else "r" if c == C1 else ""
        f.put(c, R_TOP, S("f_t" + e), "pink")
        f.put(c, bottom, S("f_b" + e), "pink")
        for r in range(R_HEAD, bottom):
            f.put(c, r, S("f_l") if c == C0 else S("f_r") if c == C1 else S("fill"), "pink")
    if open_panel:
        for c in range(C0 + 2, C1 - 1):
            f.put(c, R_RULE, S("rule"), "pink")
    for col, ch, k in headline_cells():
        age = frame - k * T_LETTER_STEP
        if age < 0:
            continue
        if age < T_STAGE:
            f.put(col, R_HEAD, NAMES["p:}"] + BACKED, "pink")                 # gum bubble icon, tile 145
        elif age < 2 * T_STAGE:
            f.put(col, R_HEAD, POP_BURST_INDEX, "pink")
        else:
            f.put(col, R_HEAD, NAMES["p:" + ch] + BACKED, "white" if age < 3 * T_STAGE else "pink", True)
    if frame >= T_WINNER:
        pal = "white" if frame < T_WINNER_COLOUR else CASES[case]["pal"]
        for col, tile, is_text in winner_cells(case):
            f.put(col, R_WIN, tile, pal, is_text)
    if frame >= T_ROUND:
        pal = "gold" if frame >= T_STEADY or ((frame - T_ROUND) // T_BLINK) % 2 == 1 else "white"
        for col, row, tile in round_cells(round_no):
            f.put(col, row, tile, pal, True)
    return f


# ---- backdrop, compose, measures ----
def lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def load_backdrop(mood, notes):
    """Arena mock-up with HUD. Its HUD says ROUND 3; set it to ROUND 1 so the banner's next round 02 agrees."""
    im = Image.open(BACKDROP % mood).convert("RGB")
    assert im.size == (320, 224)
    three, one, dee = NAMES["p:3"] + BACKED, NAMES["p:1"] + BACKED, NAMES["p:D"] + BACKED
    px = im.load()
    for r in range(ROWS):
        for c in range(2, COLS):
            for pal in PAL_ORDER:
                p = PALS[pal]
                if all(px[c * 8 + x, r * 8 + y] == p[TILES[three][y][x] - 1] and
                       px[(c - 2) * 8 + x, r * 8 + y] == p[TILES[dee][y][x] - 1] for y in range(8) for x in range(8)):
                    for y in range(8):
                        for x in range(8):
                            px[c * 8 + x, r * 8 + y] = p[TILES[one][y][x] - 1]
                    notes.append("backdrop %s: HUD round digit 3 at cell %d,%d changed to 1" % (mood, c, r))
                    return im
    notes.append("backdrop %s: HUD round digit not found, HUD still says ROUND 3" % mood)
    return im


def compose(back, fix):
    out = back.convert("RGBA")
    out.alpha_composite(fix.render())
    return out.convert("RGB")


def contrast(back, fix):
    """Per text cell: mean luminance of the two lightest face slots minus the brightest quarter of what shows
    around the glyph in that cell. Returns the list of (value, col, row)."""
    comp = compose(back, fix).load()
    vals = []
    for (c, r) in fix.text_cells:
        pix = TILES[fix.cells[(c, r)][0]]
        face = [lum(comp[c * 8 + x, r * 8 + y]) for y in range(8) for x in range(8) if pix[y][x] in (1, 2)]
        around = [lum(comp[c * 8 + x, r * 8 + y]) for y in range(8) for x in range(8) if pix[y][x] not in (1, 2, 3, 4, 5)]
        if not face or not around:
            continue                      # icon cells have no face slots
        around.sort()
        hi = around[-max(1, len(around) // 4):]
        vals.append((sum(face) / len(face) - sum(hi) / len(hi), c, r))
    return vals


def ink_extent(fix, row_cells, slots):
    """Leftmost and rightmost screen x of pixels with a slot in `slots` over the given cells."""
    xs = [c * 8 + x for (c, r) in row_cells for y in range(8) for x in range(8)
          if TILES[fix.cells[(c, r)][0]][y][x] in slots]
    return min(xs), max(xs)


def line_cells(fix, rows):
    return sorted((c, r) for (c, r) in fix.text_cells if r in rows)


def save_gif(frames, path, ms):
    w, h = frames[0].size
    strip = Image.new("RGB", (w, h * len(frames)))
    for i, fr in enumerate(frames):
        strip.paste(fr, (0, i * h))
    pal_im = strip.quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    out = [fr.quantize(palette=pal_im, dither=Image.Dither.NONE) for fr in frames]
    out[0].save(path, save_all=True, append_images=out[1:], duration=ms, loop=0, optimize=False, disposal=1)


def label_strip(text, width):
    """A label drawn with the Gumdrop font itself (plain glyphs, white palette) on dark grey."""
    im = Image.new("RGB", (width, 10), (40, 40, 48))
    px = im.load()
    p = PALS["white"]
    for i, ch in enumerate(text):
        if ch == " ":
            continue
        pix = TILES[NAMES["p:" + ch]]
        for y in range(8):
            for x in range(8):
                if pix[y][x]:
                    px[2 + i * 8 + x, 1 + y] = p[pix[y][x] - 1]
    return im


def main():
    notes = []
    backs = {m: load_backdrop(m, notes) for m in MOODS}
    shown = [("p1", 2), ("p2", 2), ("cpu", 2), ("draw", 2), ("p1", 12)]
    tag = lambda case, rn: "%s_round%02d" % (case, rn)

    # ---- stills: last frame, every case on every mood ----
    for case, rn in shown:
        for m in MOODS:
            compose(backs[m], build(FREEZE_FRAMES - 1, case, rn)).save(os.path.join(HERE, "still_%s_%s_1x.png" % (tag(case, rn), m)))

    # ---- GIFs: player 1 on all moods, the other cases on one mood each ----
    gif_ms = 70
    gifs = [("p1", 2, m) for m in MOODS] + [("p2", 2, "moon"), ("cpu", 2, "storm"), ("draw", 2, "dusk"), ("p1", 12, "moon")]
    for case, rn, m in gifs:
        frames = [compose(backs[m], build(fr, case, rn)) for fr in range(0, FREEZE_FRAMES, 4)]
        save_gif(frames, os.path.join(HERE, "anim_%s_%s_1x.gif" % (tag(case, rn), m)), gif_ms)

    # ---- key frames (banner area only, dusk) ----
    keys = [0, 6, 20, 47, 48, 52, 56, 64, 72, 119]
    y0, y1 = (R_TOP - 1) * 8, (R_BOTTOM + 2) * 8
    kh = y1 - y0 + 10
    sheet = Image.new("RGB", (2 * 320 + 6, 5 * kh + 8), (27, 28, 32))
    for i, fr in enumerate(keys):
        x, y = 2 + (i % 2) * 322, 2 + (i // 2) * (kh + 1)
        sheet.paste(label_strip("FRAME %d" % fr, 320), (x, y))
        sheet.paste(compose(backs["dusk"], build(fr, "p1", 2)).crop((0, y0, 320, y1)), (x, y + 10))
    sheet.save(os.path.join(HERE, "key_frames_dusk_1x.png"))

    # ---- stages of one letter cell and the new tile, 8x ----
    stage = Image.new("RGB", (4 * 10 + 2, 12), (40, 40, 48))
    for i, (t, pal) in enumerate(((NAMES["p:}"] + BACKED, "pink"), (POP_BURST_INDEX, "pink"),
                                  (NAMES["p:P"] + BACKED, "white"), (NAMES["p:P"] + BACKED, "pink"))):
        f = Fix()
        f.put(0, 0, t, pal)
        stage.paste(f.render().crop((0, 0, 8, 8)).convert("RGB"), (2 + i * 10, 2))
    stage.resize((stage.width * 8, stage.height * 8), Image.NEAREST).save(os.path.join(HERE, "letter_stages_8x.png"))

    # ---- centre line proof (2x, banner area, dusk): cyan = screen centre between x 159 and 160,
    #      yellow = first and last ink column of each line (shadow included) ----
    slots_ink = set(range(1, 16)) - {PLATE_SLOT}
    slots_face = {1, 2, 3, 4}
    centre_rows = []           # (case tag, line name, cells, left, right, face left, face right)
    proof = Image.new("RGB", (640, len(shown) * (2 * (y1 - y0) + 4) - 4), (27, 28, 32))
    for i, (case, rn) in enumerate(shown):
        fix = build(FREEZE_FRAMES - 1, case, rn)
        im = compose(backs["dusk"], fix).crop((0, y0, 320, y1)).resize((640, 2 * (y1 - y0)), Image.NEAREST)
        px = im.load()
        for y in range(im.height):
            for x in (319, 320):
                px[x, y] = (0, 255, 255)
        for name, rows in (("headline", (R_HEAD,)), ("winner", (R_WIN,)), ("round", (R_DIGIT_TOP, R_ROUND))):
            cells = line_cells(fix, rows)
            a, b = ink_extent(fix, cells, slots_ink)
            fa, fb = ink_extent(fix, cells, slots_face | ({14, 15, 12} if name == "winner" else set()))
            ncell = max(c for c, _ in cells) - min(c for c, _ in cells) + 1
            centre_rows.append((tag(case, rn), name, ncell, min(c for c, _ in cells), a, b, fa, fb))
            for r in rows:
                for y in range((r * 8 - y0) * 2, (r * 8 - y0) * 2 + 16):
                    for x in (a * 2 - 2, a * 2 - 1, b * 2 + 2, b * 2 + 3):
                        px[x, y] = (255, 230, 0)
        proof.paste(im, (0, i * (im.height + 4)))
    proof.save(os.path.join(HERE, "centre_proof_dusk_2x.png"))
    panel_left, panel_right = C0 * 8, COLS * 8 - (C1 + 1) * 8

    # ---- contrast: every 4th frame and the last frame, every case, every mood ----
    con = {}
    for m in MOODS:
        worst = (999, None)
        edge = 999
        for case, rn in shown:
            for fr in list(range(0, FREEZE_FRAMES, 2)) + [FREEZE_FRAMES - 1]:
                fix = build(fr, case, rn)
                for v, c, r in contrast(backs[m], fix):
                    if v < worst[0]:
                        worst = (v, "%s frame %d cell %d,%d tile %s palette %s" %
                                 (tag(case, rn), fr, c, r, INDEX_NAME[fix.cells[(c, r)][0]], fix.cells[(c, r)][1]))
        per_pal = {}
        fix = build(FREEZE_FRAMES - 1, "p1", 2)
        for case in CASES:
            fx = build(FREEZE_FRAMES - 1, case, 2)
            vals = [v for v, c, r in contrast(backs[m], fx) if r == R_WIN]
            per_pal[CASES[case]["pal"]] = min(vals)
        con[m] = (worst, per_pal, edge)

    # ---- cells written per frame ----
    changes = {}
    prev = {}
    for fr in range(FREEZE_FRAMES):
        cur = build(fr, "p1", 12).cells
        changes[fr] = sum(1 for k, v in cur.items() if prev.get(k) != v)
        prev = cur
    total_cells = len(prev)
    quiet = max(changes[fr] for fr in range(1, T_PANEL))
    blink_cells = changes[T_ROUND + T_BLINK]
    used_tiles = sorted({t for case, rn in shown for fr in range(FREEZE_FRAMES) for t, _ in build(fr, case, rn).cells.values()})
    used_pals = sorted({p for case, rn in shown for fr in range(FREEZE_FRAMES) for _, p in build(fr, case, rn).cells.values()},
                       key=PAL_ORDER.index)

    # ---- banner_spec.txt ----
    P = lambda name: "%d %s" % (PAL_ORDER.index(name), name)
    S = []
    A = S.append
    A("GUMBIRDS ROUND CLEAR BANNER, BUILD DATA (written by draw_round_clear_banner_final.py, 10 November 2026)")
    A("")
    A("Fix layer only. Cell = 8 x 8 px, col 0..39, row 0..27. Tile index = slot in assets/font/fix_font_sheet.png (16 per row).")
    A("Backed copy of a glyph = plain index + 96 (name b:X). Every banner cell is a backed tile: the navy plate is part of the tile.")
    A("Palette index = order in fix_font.json palette_order: " + ", ".join(P(n) for n in PAL_ORDER) + ".")
    A("Cost: 1 new tile (index %d), 0 new palettes, palettes used: %s. Distinct tiles used: %d. Cells written at most: %d." %
      (POP_BURST_INDEX, ", ".join(used_pals), len(used_tiles), total_cells))
    A("")
    A("== NEW TILE  n:pop_burst  sheet index %d (row 4, column 11 of the sheet; empty today)" % POP_BURST_INDEX)
    A("   palette slot per pixel, hex, 0 = transparent. B = slot 11 (gum light), C = slot 12 (white), D = slot 13 (navy plate).")
    for r in POP_BURST_ROWS:
        A("   " + " ".join(r))
    A("   Always drawn with palette %s." % P("pink"))
    A("")
    A("== PANEL  columns %d..%d (22 cells), 9 free cells left and right. All panel cells use palette %s." % (C0, C1, P("pink")))
    n = NAMES
    A("   Ribbon, frames 0..%d (3 rows, %d cells):" % (T_PANEL - 1, 3 * (C1 - C0 + 1)))
    A("     row %d: col %d s:f_tl %d | cols %d..%d s:f_t %d | col %d s:f_tr %d" % (R_TOP, C0, n["s:f_tl"], C0 + 1, C1 - 1, n["s:f_t"], C1, n["s:f_tr"]))
    A("     row %d: col %d s:f_l %d  | cols %d..%d s:fill %d | col %d s:f_r %d" % (R_HEAD, C0, n["s:f_l"], C0 + 1, C1 - 1, n["s:fill"], C1, n["s:f_r"]))
    A("     row %d: col %d s:f_bl %d | cols %d..%d s:f_b %d | col %d s:f_br %d" % (R_RULE, C0, n["s:f_bl"], C0 + 1, C1 - 1, n["s:f_b"], C1, n["s:f_br"]))
    A("   Open panel, frames %d..%d (8 rows, %d cells): rows %d and %d as above, then" % (T_PANEL, FREEZE_FRAMES - 1, total_cells, R_TOP, R_HEAD))
    A("     row %d: col %d s:f_l %d | col %d s:fill %d | cols %d..%d s:rule %d | col %d s:fill %d | col %d s:f_r %d" %
      (R_RULE, C0, n["s:f_l"], C0 + 1, n["s:fill"], C0 + 2, C1 - 2, n["s:rule"], C1 - 1, n["s:fill"], C1, n["s:f_r"]))
    A("     rows %d..%d: col %d s:f_l %d | cols %d..%d s:fill %d | col %d s:f_r %d" % (R_WIN, R_ROUND, C0, n["s:f_l"], C0 + 1, C1 - 1, n["s:fill"], C1, n["s:f_r"]))
    A("     row %d: col %d s:f_bl %d | cols %d..%d s:f_b %d | col %d s:f_br %d" % (R_BOTTOM, C0, n["s:f_bl"], C0 + 1, C1 - 1, n["s:f_b"], C1, n["s:f_br"]))
    A("")
    A("== LINE 1  headline \"ALL POPPED!\"  row %d, cols %d..%d (20 cells: letters on even columns, word gap cols 15,16)" % (R_HEAD, C0 + 1, C1 - 1))
    A("   n   col  glyph  tile   start frame (bubble)  burst  white  pink from")
    for col, ch, k in headline_cells():
        s = k * T_LETTER_STEP
        A("   %d   %2d   b:%s    %3d    %3d                   %3d    %3d    %3d" % (k, col, ch, n["p:" + ch] + BACKED, s, s + T_STAGE, s + 2 * T_STAGE, s + 3 * T_STAGE))
    A("   Stage tiles in the letter's cell: bubble = b:} %d palette %s; burst = n:pop_burst %d palette %s;" %
      (n["p:}"] + BACKED, P("pink"), POP_BURST_INDEX, P("pink")))
    A("   white = the glyph with palette %s; pink = the glyph with palette %s. Before its start frame the cell is s:fill." % (P("white"), P("pink")))
    A("")
    A("== LINE 2  winner  row %d. Appears at frame %d with palette %s (icon cells too), takes its own palette at frame %d." %
      (R_WIN, T_WINNER, P("white"), T_WINNER_COLOUR))
    for case, c in CASES.items():
        cells = winner_cells(case)
        A("   case %-4s  %-22s \"%s\"  palette %s  cols %d..%d (%d cells%s)" %
          (case, c["label"], c["text"], P(c["pal"]), cells[0][0], cells[-1][0], cells[-1][0] - cells[0][0] + 1,
           ", icon b:~L b:~R then one blank" if c["icon"] else ", no icon"))
        A("      " + "  ".join("%d:%s=%d" % (col, INDEX_NAME[t], t) for col, t, _ in cells))
    A("   Blank cells inside a line stay s:fill %d palette %s (already there from the panel)." % (n["s:fill"], P("pink")))
    A("")
    A("== LINE 3  next round  \"ROUND nn\", always two digits (01..99), cols 16..23. Letters on row %d, tall digits on rows %d (top) and %d (bottom)." %
      (R_ROUND, R_DIGIT_TOP, R_ROUND))
    A("   letters: " + "  ".join("%d:%s=%d" % (col, INDEX_NAME[t], t) for col, row, t in round_cells(1) if row == R_ROUND and col < 22))
    A("   digits:  tens at col 22, ones at col 23; top tile = %d + digit (bt:d:0), bottom tile = %d + digit (bt:d:1)" % (TALL_TOP + BACKED, TALL_BOTTOM + BACKED))
    for rn in (2, 12):
        A("   round %2d:  " % rn + "  ".join("%d,%d:%s=%d" % (col, row, INDEX_NAME[t], t) for col, row, t in round_cells(rn) if col >= 22))
    A("   Palette: %s on frames %d..%d and %d..%d, %s on frames %d..%d and %d..%d (all %d cells swap together)." %
      (P("white"), T_ROUND, T_ROUND + T_BLINK - 1, T_ROUND + 2 * T_BLINK, T_ROUND + 3 * T_BLINK - 1,
       P("gold"), T_ROUND + T_BLINK, T_ROUND + 2 * T_BLINK - 1, T_STEADY, FREEZE_FRAMES - 1, blink_cells))
    A("")
    A("== TIMELINE  (game frames; 0 = first frame of the 120 frame freeze)")
    A("   frame      event                                                        cells written that frame")
    A("   0          ribbon rows %d..%d; letter 0 (A) starts as a bubble             %d" % (R_TOP, R_RULE, changes[0]))
    A("   4*n        letter n starts (n = 0..9): bubble 4 frames, burst 4, white 4    at most %d on any frame 1..%d" % (quiet, T_PANEL - 1))
    A("   36..47     last letter (!): bubble 36, burst 40, white 44")
    A("   %d         last letter turns pink; ribbon opens into the panel (rows %d..%d)   %d" % (T_PANEL, R_RULE, R_BOTTOM, changes[T_PANEL]))
    A("   %d         winner line appears, palette white                              %d" % (T_WINNER, changes[T_WINNER]))
    A("   %d         winner line takes the winner's palette                          %d" % (T_WINNER_COLOUR, changes[T_WINNER_COLOUR]))
    A("   %d         ROUND nn appears, palette white                                 %d" % (T_ROUND, changes[T_ROUND]))
    A("   %d, %d, %d  ROUND nn swaps palette: gold, white, gold                       %d each" % (T_ROUND + T_BLINK, T_ROUND + 2 * T_BLINK, T_ROUND + 3 * T_BLINK, blink_cells))
    A("   %d..%d    steady gold, nothing changes" % (T_STEADY, FREEZE_FRAMES - 1))
    A("   %d        freeze over: clear all %d cells (cols %d..%d, rows %d..%d)" % (T_CLEAR, total_cells, C0, C1, R_TOP, R_BOTTOM))
    A("   If %d cell writes in one frame are too many, write rows %d..%d on frame %d and rows %d..%d on frame %d." %
      (changes[T_PANEL], R_RULE, R_GAP, T_PANEL, R_DIGIT_TOP, R_BOTTOM, T_PANEL + 1))
    A("")
    A("== FULL CELL MAP, last frame (119), case p1, round 12.  tile index / palette index per cell, rows %d..%d, cols %d..%d" % (R_TOP, R_BOTTOM, C0, C1))
    last = build(FREEZE_FRAMES - 1, "p1", 12)
    A("   col   " + " ".join("%5d" % c for c in range(C0, C1 + 1)))
    for r in range(R_TOP, R_BOTTOM + 1):
        A("   row %d " % r + " ".join("%3d/%d" % (last.cells[(c, r)][0], PAL_ORDER.index(last.cells[(c, r)][1])) for c in range(C0, C1 + 1)))
    open(os.path.join(HERE, "banner_spec.txt"), "w").write("\n".join(S) + "\n")

    # ---- numbers.txt ----
    L = []
    N = L.append
    N("ROUND CLEAR BANNER, FINAL (D and C combined), 10 November 2026 (written by draw_round_clear_banner_final.py)")
    N("")
    N("cost: new tiles 1 (pop burst, sheet index %d); new palettes 0; palettes used %d (%s); distinct tiles used %d;" %
      (POP_BURST_INDEX, len(used_pals), ", ".join(used_pals), len(used_tiles)))
    N("      fix cells written at most %d (22 x 8); most cell writes in one frame %d (frame %d), %d at frame 0, at most %d on frames 1 to 47, %d per ROUND blink swap." %
      (total_cells, max(changes.values()), max(changes, key=changes.get), changes[0], quiet, blink_cells))
    N("")
    N("centring (screen is 320 px, centre between x 159 and 160). Left = first ink column, right margin = 319 - last ink column.")
    N("ink = every pixel that is not plate; face = glyph face without its 1 px drop shadow (icon: body colours).")
    N("  panel: 22 cells, left margin %d px, right margin %d px" % (panel_left, panel_right))
    N("  case            line      cells  first col  ink margins L/R   face margins L/R")
    for t, name, ncell, col, a, b, fa, fb in centre_rows:
        N("  %-15s %-9s %3d    %3d        %3d / %3d         %3d / %3d" % (t, name, ncell, col, a, 319 - b, fa, 319 - fb))
    N("  Every line has an even cell count, so every cell box is centred exactly. Ink differs from the box only by glyph shape:")
    N("  the face of a Gumdrop letter is 7 px wide with a 1 px shadow on the right, and the last headline glyph (!) and the digit 1 are narrow.")
    N("")
    N("contrast (0..255 luminance gap, text cell face against the brightest quarter of its surroundings; under 90 is hard to read at 1x)")
    for m in MOODS:
        worst, per_pal, edge = con[m]
        N("  %-5s worst text cell %.0f  (%s)" % (m, worst[0], worst[1]))
        N("        winner line by palette, worst cell: " + ", ".join("%s %.0f" % (k, v) for k, v in per_pal.items()))
    N("  All text sits on the navy plate inside its own tile, so the text numbers do not depend on the sky.")
    N("")
    N("notes:")
    for x in notes:
        N("  " + x)
    N("  Round 12 pictures keep the HUD mock-up at ROUND 1 (the mock-up has one round digit).")
    N("  Backdrops are HUD mock-ups from 2026-11-10-hud-title-final, not MAME screenshots.")
    N("  GIF: 30 frames of %d ms, one per 4 game frames (real time 66.7 ms)." % gif_ms)
    open(os.path.join(HERE, "numbers.txt"), "w").write("\n".join(L) + "\n")

    # ---- index.html ----
    def img(name, w=640, h=448):
        return '<img src="%s" width="%d" height="%d" alt="%s">' % (name, w, h, name)

    H = ["""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Gumbirds: round clear banner, final</title>
<style>
body { background: #1b1c20; color: #d6d7dc; font-family: Helvetica, Arial, sans-serif; margin: 24px; line-height: 1.45; }
h1 { font-size: 22px; margin: 0 0 6px; } h2 { font-size: 17px; margin: 34px 0 6px; color: #ffffff; }
p { margin: 4px 0 10px; max-width: 1300px; } .num { color: #a9abb6; font-size: 14px; }
img { image-rendering: pixelated; display: block; border: 1px solid #3a3c44; background: #000; }
.row { display: flex; flex-wrap: wrap; gap: 14px; margin: 8px 0 4px; } .cell { font-size: 13px; color: #a9abb6; }
table { border-collapse: collapse; font-size: 14px; margin: 6px 0 12px; } td, th { border: 1px solid #3a3c44; padding: 4px 10px; text-align: left; }
th { color: #ffffff; font-weight: 600; }
</style></head><body>
<h1>Gumbirds: round clear banner, final</h1>
<p>Variants D and C combined. Shown while play is frozen for 2 seconds (120 frames) after a round ends. Fix layer only, Gumdrop font,
320 x 224 shown at 2x. Backdrops are the HUD mock-ups, not MAME screenshots. Build data: banner_spec.txt. Measurements: numbers.txt.</p>
<p class="num">Cost: 1 new tile (pop burst), 0 new palettes, %d fix cells at most. Worst text cell contrast: %s.</p>
""" % (total_cells, ", ".join("%s %.0f" % (m, con[m][0][0]) for m in MOODS))]
    H.append('<h2>Player 1 wins, on the three sky moods (animated)</h2><div class="row">')
    for m in MOODS:
        H.append('<div class="cell">%s%s</div>' % (img("anim_p1_round02_%s_1x.gif" % m), m))
    H.append('</div>')
    H.append('<h2>Timeline</h2><table><tr><th>Frame</th><th>What happens</th></tr>'
             '<tr><td>0</td><td>Navy ribbon appears (3 rows). First letter starts.</td></tr>'
             '<tr><td>0 to 47</td><td>ALL POPPED! letter by letter, a new letter every 4 frames: gum bubble, pop burst, white flash, pink (4 frames each).</td></tr>'
             '<tr><td>%d</td><td>Last letter is pink. The ribbon opens downward into the panel.</td></tr>'
             '<tr><td>%d</td><td>Winner line appears in white.</td></tr>'
             '<tr><td>%d</td><td>Winner line takes the winner colour.</td></tr>'
             '<tr><td>%d</td><td>ROUND and the next round number appear in white, then swap white and gold every %d frames.</td></tr>'
             '<tr><td>%d to 119</td><td>ROUND stays gold.</td></tr>'
             '<tr><td>120</td><td>Freeze over, banner cleared.</td></tr></table>' % (T_PANEL, T_WINNER, T_WINNER_COLOUR, T_ROUND, T_BLINK, T_STEADY))
    H.append('<div class="row"><div class="cell">%skey frames, banner area, dusk</div></div>' % img("key_frames_dusk_1x.png", sheet.width * 2, sheet.height * 2))
    H.append('<div class="row"><div class="cell">%sone letter cell at 8x: gum bubble, pop burst (the one new tile), white flash, pink</div></div>'
             % img("letter_stages_8x.png", 336, 96))
    H.append('<h2>The other cases (animated)</h2><div class="row">')
    for case, rn, m, text in (("p2", 2, "moon", "Player 2 wins, lime"), ("cpu", 2, "storm", "A computer rival wins: COMPUTER WINS, white"),
                              ("draw", 2, "dusk", "No survivor: NO SURVIVORS, dim blue, no bird icon"), ("p1", 12, "moon", "Two-digit round: ROUND 12")):
        H.append('<div class="cell">%s%s (%s)</div>' % (img("anim_%s_%s_1x.gif" % (tag(case, rn), m)), text, m))
    H.append('</div>')
    H.append('<h2>Last frame, every case on every sky mood</h2>')
    for case, rn in shown:
        H.append('<p>%s%s</p><div class="row">' % (CASES[case]["label"], ", round 12" if rn == 12 else ""))
        for m in MOODS:
            H.append('<div class="cell">%s%s</div>' % (img("still_%s_%s_1x.png" % (tag(case, rn), m)), m))
        H.append('</div>')
    H.append('<h2>Centre line proof</h2><p>Light blue line: screen centre (between pixel 159 and 160). Yellow marks: first and last ink column of each line, '
             'shadow included. Every line now has an even cell count, so every cell box is centred exactly; the old 4 pixel left offset is gone. '
             'From top to bottom: player 1, player 2, computer, no survivors, round 12.</p>')
    H.append('<div class="row"><div class="cell">%s</div></div>' % img("centre_proof_dusk_2x.png", proof.width, proof.height))
    H.append('<table><tr><th>Case</th><th>Line</th><th>Cells</th><th>Ink margin left / right (pixels)</th><th>Face margin left / right</th></tr>')
    for t, name, ncell, col, a, b, fa, fb in centre_rows:
        H.append('<tr><td>%s</td><td>%s</td><td>%d</td><td>%d / %d</td><td>%d / %d</td></tr>' % (t, name, ncell, a, 319 - b, fa, 319 - fb))
    H.append('</table>')
    H.append('<h2>Contrast per sky mood</h2><table><tr><th>Mood</th><th>Worst text cell</th><th>Winner line by colour (worst cell)</th></tr>')
    for m in MOODS:
        worst, per_pal, edge = con[m]
        H.append('<tr><td>%s</td><td>%.0f</td><td>%s</td></tr>' % (m, worst[0], ", ".join("%s %.0f" % kv for kv in per_pal.items())))
    H.append('</table><p class="num">Scale 0 to 255; under 90 is hard to read at 1x. Text sits on the navy plate of its own tile, so the sky does not change it.</p>')
    H.append("</body></html>\n")
    open(os.path.join(HERE, "index.html"), "w").write("\n".join(H))
    print(open(os.path.join(HERE, "numbers.txt")).read())


if __name__ == "__main__":
    main()
