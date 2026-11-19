#!/opt/homebrew/bin/python3.14 -I
"""Round clear banner for Gumbirds, second final: the panel has its full size (rows 10..17, cols 9..30) from frame 0.

Fix layer only: 8x8 tiles, 40x28 cells, one 16-colour palette per tile, no flip, no scaling.

Run: /opt/homebrew/bin/python3.14 -I draw_round_clear_banner_final2.py   (from any directory)

Reads (read only):
  assets/font/fix_font_sheet.png + fix_font.json   the Gumdrop fix font and its five palettes
  backdrop_<mood>_1x.png in this folder   arena mock-ups with the HUD (copies of hud2p_<mood>_1x.png of the HUD draft)
Writes into this folder: GIF and PNG files, index.html, numbers.txt, banner_spec.txt.

The banner is a grid of (tile index, palette name) cells per game frame, drawn the way the fix layer draws.
build(frame, case, round_no, last, split) is the single source of the layout: pictures, numbers and banner_spec.txt all come from it.
"""
import json
import os
from PIL import Image, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
SHEET = os.path.join(ROOT, "assets/font/fix_font_sheet.png")
META = os.path.join(ROOT, "assets/font/fix_font.json")
BACKDROP = os.path.join(HERE, "backdrop_%s_1x.png")
MOODS = ["dusk", "moon", "storm"]
COLS, ROWS = 40, 28
FREEZE_FRAMES = 120          # decided rule: play freezes 2 seconds
BACKED = 96                  # backed copy of a glyph tile = its index + 96
TALL_TOP, TALL_BOTTOM = 64, 80
PLATE_SLOT = 13              # palette slot of the navy plate in every backed tile
POP_BURST_INDEX = 75         # first empty slot of the fix sheet (right after s:rule = 74)

# ---- timeline (game frames, 0 = first frame of the freeze) ----
T_PLATE_A = 1                # split draw: interior cells of odd panel columns (10, 12, .. 28) arrive on frame 1
T_PLATE_B = 2                # split draw: interior cells of even panel columns (11, 13, .. 29) arrive on frame 2
T_HEAD = 4                   # first headline letter starts (the complete, waiting panel is alone on frames 0..3)
T_LETTER_STEP = 4            # letter n of the headline starts at frame T_HEAD + 4 * n (n = 0..9)
T_STAGE = 4                  # frames per stage: gum bubble, pop burst, white flash, then pink
T_WINNER = 56                # winner line appears, white palette
T_WINNER_COLOUR = 60         # winner line takes the winner's palette
T_ROUND = 68                 # ROUND nn (or MATCH OVER) appears, white
T_BLINK = 8                  # white / gold swap period
T_STEADY = 100               # steady gold from here to frame 119 (gold already since frame 92)
T_CLEAR = 120                # first frame after the freeze: the game clears every banner cell

# ---- layout (cells) ----
C0, C1 = 9, 30               # panel columns, frame included: 22 cells, 9 free cells on each side
R_TOP, R_HEAD, R_RULE, R_WIN, R_GAP, R_DIGIT_TOP, R_ROUND, R_BOTTOM = 10, 11, 12, 13, 14, 15, 16, 17
R_MATCH = 15                 # MATCH OVER sits on the middle row of the lower section (rows 14..16)
HEADLINE = "A L L  P O P P E D !"     # 20 cells: one blank between letters, two between the words
MATCH_TEXT = "MATCH OVER"
WAIT_COLS = (18, 19, 20, 21) # waiting mark of a text line: four dim dashes in the middle of its row

CASES = {
    "p1":   dict(label="Player 1 wins", text="PLAYER 1 WINS", pal="pink", icon=True),
    "p2":   dict(label="Player 2 wins", text="PLAYER 2 WINS", pal="lime", icon=True),
    "cpu":  dict(label="The computer bird wins", text="COMPUTER WINS", pal="white", icon=True),
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


def match_cells():
    """[(col, row, tile)] of MATCH OVER, the last-round replacement of ROUND nn: 10 cells, one row."""
    col = centred(len(MATCH_TEXT))
    return [(col + i, R_MATCH, NAMES["p:" + ch] + BACKED) for i, ch in enumerate(MATCH_TEXT) if ch != " "]


def third_cells(round_no, last):
    return match_cells() if last else round_cells(round_no)


def build(frame, case="p1", round_no=2, last=False, split=True):
    """Fix layer of the banner at a game frame (0..119). The outline (rows 10 and 17, cols 9 and 30) is there on
    every frame. split=True spreads the first draw over frames 0, 1, 2; split=False draws all 176 cells on frame 0."""
    f = Fix()
    S = lambda n: NAMES["s:" + n]
    dash, dot = NAMES["p:-"] + BACKED, NAMES["p:."] + BACKED
    for c in range(C0, C1 + 1):
        e = "l" if c == C0 else "r" if c == C1 else ""
        f.put(c, R_TOP, S("f_t" + e), "pink")
        f.put(c, R_BOTTOM, S("f_b" + e), "pink")
        for r in range(R_HEAD, R_BOTTOM):
            f.put(c, r, S("f_l") if c == C0 else S("f_r") if c == C1 else S("fill"), "pink")
    for c in range(C0 + 2, C1 - 1):
        f.put(c, R_RULE, S("rule"), "pink")
    for col, ch, k in headline_cells():
        age = frame - T_HEAD - k * T_LETTER_STEP
        if age < 0:
            f.put(col, R_HEAD, dot, "dim")                                    # waiting socket: dim dot
        elif age < T_STAGE:
            f.put(col, R_HEAD, NAMES["p:}"] + BACKED, "pink")                 # gum bubble icon, tile 145
        elif age < 2 * T_STAGE:
            f.put(col, R_HEAD, POP_BURST_INDEX, "pink")
        else:
            f.put(col, R_HEAD, NAMES["p:" + ch] + BACKED, "white" if age < 3 * T_STAGE else "pink", True)
    if frame >= T_WINNER:
        pal = "white" if frame < T_WINNER_COLOUR else CASES[case]["pal"]
        for col, tile, is_text in winner_cells(case):
            f.put(col, R_WIN, tile, pal, is_text)
    else:
        for col in WAIT_COLS:
            f.put(col, R_WIN, dash, "dim")
    if frame >= T_ROUND:
        pal = "gold" if frame >= T_STEADY or ((frame - T_ROUND) // T_BLINK) % 2 == 1 else "white"
        for col, row, tile in third_cells(round_no, last):
            f.put(col, row, tile, pal, True)
    else:
        for col in WAIT_COLS:
            f.put(col, R_MATCH if last else R_ROUND, dash, "dim")
    if split:
        for c in range(C0 + 1, C1):
            if frame < (T_PLATE_A if (c - C0) % 2 == 1 else T_PLATE_B):
                for r in range(R_HEAD, R_BOTTOM):
                    del f.cells[(c, r)]
                    f.text_cells.discard((c, r))
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


def save_gif(frames, path, ms):  # ms: one duration or a list, one per frame
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


def panel_bbox(back, fix):
    """Bounding box (x0, y0, x1, y1, inclusive) of every pixel of the composed frame that differs from the backdrop."""
    b = ImageChops.difference(compose(back, fix), back).getbbox()
    return (b[0], b[1], b[2] - 1, b[3] - 1)


def main():
    notes = []
    backs = {m: load_backdrop(m, notes) for m in MOODS}
    # (case, round number, last round of the match)
    shown = [("p1", 2, False), ("p2", 2, False), ("cpu", 2, False), ("draw", 2, False), ("p1", 12, False), ("p1", 2, True)]
    tag = lambda case, rn, last: "%s_matchover" % case if last else "%s_round%02d" % (case, rn)
    title = lambda case, rn, last: CASES[case]["label"] + (", last round: MATCH OVER" if last else ", round 12" if rn == 12 else "")
    for old in os.listdir(HERE):
        if old.startswith(("anim_", "still_", "key_", "first_", "centre_", "letter_")):
            os.remove(os.path.join(HERE, old))

    # ---- stills: last frame, every case on every mood ----
    for case, rn, last in shown:
        for m in MOODS:
            compose(backs[m], build(FREEZE_FRAMES - 1, case, rn, last)).save(os.path.join(HERE, "still_%s_%s_1x.png" % (tag(case, rn, last), m)))

    # ---- GIFs: player 1 on all moods, the other cases on one mood each. Game frames 0, 1, 2, then every 4th. ----
    gif_frames = [0, 1, 2] + list(range(4, FREEZE_FRAMES, 4))
    gif_ms = [20, 20, 30] + [70] * (len(gif_frames) - 3)
    gifs = [("p1", 2, False, m) for m in MOODS] + [("p2", 2, False, "moon"), ("cpu", 2, False, "storm"), ("draw", 2, False, "dusk"),
                                                    ("p1", 12, False, "moon"), ("p1", 2, True, "dusk")]
    for case, rn, last, m in gifs:
        frames = [compose(backs[m], build(fr, case, rn, last)) for fr in gif_frames]
        save_gif(frames, os.path.join(HERE, "anim_%s_%s_1x.gif" % (tag(case, rn, last), m)), gif_ms)

    # ---- key frames (banner area only, dusk), one column so the panel edges line up down the sheet ----
    y0, y1 = (R_TOP - 1) * 8, (R_BOTTOM + 2) * 8
    kh = y1 - y0 + 10

    def strip(items, path):
        sheet = Image.new("RGB", (320 + 4, len(items) * (kh + 1) + 3), (27, 28, 32))
        for i, (text, fix) in enumerate(items):
            lab = label_strip(text, 320)
            for x in (C0 * 8, (C1 + 1) * 8 - 1):              # tick = first and last pixel column of the panel
                for y in range(10):
                    lab.putpixel((x, y), (0, 255, 255))
            sheet.paste(lab, (2, 2 + i * (kh + 1)))
            sheet.paste(compose(backs["dusk"], fix).crop((0, y0, 320, y1)), (2, 12 + i * (kh + 1)))
        sheet.save(os.path.join(HERE, path))
        return sheet

    keys = [0, 4, 24, 48, 56, 72, 119]
    key_sheet = strip([("FRAME %d" % fr, build(fr, "p1", 2)) for fr in keys], "key_frames_dusk_1x.png")
    key_match = strip([("FRAME %d" % fr, build(fr, "p1", 2, True)) for fr in keys], "key_frames_matchover_dusk_1x.png")
    first_sheet = strip([("FRAME 0", build(0, "p1", 2)), ("FRAME 1", build(1, "p1", 2)), ("FRAME 2", build(2, "p1", 2)),
                         ("FRAME 0 UNSPLIT", build(0, "p1", 2, split=False))], "first_frames_dusk_1x.png")

    # ---- stages of one letter cell and the new tile, 8x ----
    stage = Image.new("RGB", (5 * 10 + 2, 12), (40, 40, 48))
    for i, (t, pal) in enumerate(((NAMES["p:."] + BACKED, "dim"), (NAMES["p:}"] + BACKED, "pink"), (POP_BURST_INDEX, "pink"),
                                  (NAMES["p:P"] + BACKED, "white"), (NAMES["p:P"] + BACKED, "pink"))):
        f = Fix()
        f.put(0, 0, t, pal)
        stage.paste(f.render().crop((0, 0, 8, 8)).convert("RGB"), (2 + i * 10, 2))
    stage = stage.resize((stage.width * 8, stage.height * 8), Image.NEAREST)
    stage.save(os.path.join(HERE, "letter_stages_8x.png"))

    # ---- centre line proof (2x, banner area, dusk): cyan = screen centre between x 159 and 160,
    #      yellow = first and last ink column of each line (shadow included) ----
    slots_ink = set(range(1, 16)) - {PLATE_SLOT}
    slots_face = {1, 2, 3, 4}
    centre_rows = []           # (case tag, line name, cells, first col, left, right, face left, face right)
    proof = Image.new("RGB", (640, len(shown) * (2 * (y1 - y0) + 4) - 4), (27, 28, 32))
    for i, (case, rn, last) in enumerate(shown):
        fix = build(FREEZE_FRAMES - 1, case, rn, last)
        im = compose(backs["dusk"], fix).crop((0, y0, 320, y1)).resize((640, 2 * (y1 - y0)), Image.NEAREST)
        px = im.load()
        for y in range(im.height):
            for x in (319, 320):
                px[x, y] = (0, 255, 255)
        third = ("match over", (R_MATCH,)) if last else ("round", (R_DIGIT_TOP, R_ROUND))
        for name, rows in (("headline", (R_HEAD,)), ("winner", (R_WIN,)), third):
            cells = line_cells(fix, rows)
            a, b = ink_extent(fix, cells, slots_ink)
            fa, fb = ink_extent(fix, cells, slots_face | ({14, 15, 12} if name == "winner" else set()))
            ncell = max(c for c, _ in cells) - min(c for c, _ in cells) + 1
            centre_rows.append((tag(case, rn, last), name, ncell, min(c for c, _ in cells), a, b, fa, fb))
            for r in rows:
                for y in range((r * 8 - y0) * 2, (r * 8 - y0) * 2 + 16):
                    for x in (a * 2 - 2, a * 2 - 1, b * 2 + 2, b * 2 + 3):
                        px[x, y] = (255, 230, 0)
        proof.paste(im, (0, i * (im.height + 4)))
    proof.save(os.path.join(HERE, "centre_proof_dusk_2x.png"))
    panel_left, panel_right = C0 * 8, COLS * 8 - (C1 + 1) * 8
    match_row = [r for r in centre_rows if r[1] == "match over"][0]

    # ---- panel size check: bounding box of (frame minus backdrop) on every one of the 120 frames ----
    want = (C0 * 8, R_TOP * 8, (C1 + 1) * 8 - 1, (R_BOTTOM + 1) * 8 - 1)
    box_runs, box_bad = 0, []
    for split in (True, False):
        for case, rn, last in shown:
            for m in MOODS:
                boxes = {panel_bbox(backs[m], build(fr, case, rn, last, split)) for fr in range(FREEZE_FRAMES)}
                box_runs += 1
                if boxes != {want}:
                    box_bad.append((tag(case, rn, last), m, split, sorted(boxes)))
    cell_counts = {fr: len(build(fr, "p1", 2).cells) for fr in range(FREEZE_FRAMES)}
    assert not box_bad, box_bad

    # ---- contrast: every 2nd frame and the last frame, every case, every mood ----
    con = {}
    for m in MOODS:
        worst = (999, None)
        for case, rn, last in shown:
            for fr in list(range(0, FREEZE_FRAMES, 2)) + [FREEZE_FRAMES - 1]:
                fix = build(fr, case, rn, last)
                for v, c, r in contrast(backs[m], fix):
                    if v < worst[0]:
                        worst = (v, "%s frame %d cell %d,%d tile %s palette %s" %
                                 (tag(case, rn, last), fr, c, r, INDEX_NAME[fix.cells[(c, r)][0]], fix.cells[(c, r)][1]))
        per_pal = {}
        for case in CASES:
            fx = build(FREEZE_FRAMES - 1, case, 2)
            per_pal[CASES[case]["pal"]] = min(v for v, c, r in contrast(backs[m], fx) if r == R_WIN)
        fx = build(FREEZE_FRAMES - 1, "p1", 2, True)
        match_con = min(v for v, c, r in contrast(backs[m], fx) if r == R_MATCH)
        con[m] = (worst, per_pal, match_con)

    # ---- cells written per frame (a write = a cell whose tile or palette differs from the frame before) ----
    def writes(case, rn, last, split):
        out, prev = {}, {}
        for fr in range(FREEZE_FRAMES):
            cur = build(fr, case, rn, last, split).cells
            out[fr] = sum(1 for k, v in cur.items() if prev.get(k) != v)
            prev = cur
        return out

    W = {(tag(*x), sp): writes(x[0], x[1], x[2], sp) for x in shown for sp in (True, False)}
    peak_split = max((max(w.values()), max(w, key=w.get), t) for (t, sp), w in W.items() if sp)
    peak_one = max((max(w.values()), max(w, key=w.get), t) for (t, sp), w in W.items() if not sp)
    peak_after = max((max(v for fr, v in w.items() if fr > T_PLATE_B), t) for (t, sp), w in W.items() if sp)
    total_cells = (C1 - C0 + 1) * (R_BOTTOM - R_TOP + 1)
    assert cell_counts[FREEZE_FRAMES - 1] == total_cells
    all_builds = [build(fr, c, rn, l) for c, rn, l in shown for fr in range(FREEZE_FRAMES)]
    used_tiles = sorted({t for b in all_builds for t, _ in b.cells.values()})
    used_pals = sorted({p for b in all_builds for _, p in b.cells.values()}, key=PAL_ORDER.index)
    new_tiles = [t for t in used_tiles if t not in NAMES.values() and not (TALL_TOP + BACKED <= t < TALL_BOTTOM + BACKED + 10)] + \
                [t for t in used_tiles if t == POP_BURST_INDEX]
    assert new_tiles == [POP_BURST_INDEX], new_tiles
    assert all(p in PAL_ORDER for p in used_pals)

    def write_rows(w):
        """Compress a frame -> writes map into 'frames: count' pieces, zero frames left out."""
        out, fr = [], 0
        frs = [f for f in sorted(w) if w[f]]
        return ", ".join("%d:%d" % (f, w[f]) for f in frs)

    # ---- banner_spec.txt ----
    P = lambda name: "%d %s" % (PAL_ORDER.index(name), name)
    n = NAMES
    dash, dot = n["p:-"] + BACKED, n["p:."] + BACKED
    S = []
    A = S.append
    A("GUMBIRDS ROUND CLEAR BANNER, SECOND FINAL, BUILD DATA (written by draw_round_clear_banner_final2.py, 10 November 2026)")
    A("")
    A("Change against the first final: the panel has its full size from frame 0 and never changes size. Nothing opens or grows.")
    A("Fix layer only. Cell = 8 x 8 px, col 0..39, row 0..27. Tile index = slot in assets/font/fix_font_sheet.png (16 per row).")
    A("Backed copy of a glyph = plain index + 96 (name b:X). Every banner cell is a backed tile: the navy plate is part of the tile.")
    A("Palette index = order in fix_font.json palette_order: " + ", ".join(P(x) for x in PAL_ORDER) + ".")
    A("Cost: 1 new tile (index %d), 0 new palettes, palettes used: %s. Distinct tiles used: %d. Banner cells: %d (22 x 8)." %
      (POP_BURST_INDEX, ", ".join(used_pals), len(used_tiles), total_cells))
    A("")
    A("== NEW TILE  n:pop_burst  sheet index %d (row 4, column 11 of the sheet; empty today). Unchanged from the first final." % POP_BURST_INDEX)
    A("   palette slot per pixel, hex, 0 = transparent. B = slot 11 (gum light), C = slot 12 (white), D = slot 13 (navy plate).")
    for r in POP_BURST_ROWS:
        A("   " + " ".join(r))
    A("   Always drawn with palette %s." % P("pink"))
    A("")
    A("== PANEL  columns %d..%d, rows %d..%d (22 x 8 = %d cells) on every frame 0..119. Pixel box x %d..%d, y %d..%d. Palette %s." %
      (C0, C1, R_TOP, R_BOTTOM, total_cells, want[0], want[2], want[1], want[3], P("pink")))
    A("   row %d: col %d s:f_tl %d | cols %d..%d s:f_t %d | col %d s:f_tr %d" % (R_TOP, C0, n["s:f_tl"], C0 + 1, C1 - 1, n["s:f_t"], C1, n["s:f_tr"]))
    A("   rows %d..%d: col %d s:f_l %d | cols %d..%d interior | col %d s:f_r %d" % (R_HEAD, R_ROUND, C0, n["s:f_l"], C0 + 1, C1 - 1, C1, n["s:f_r"]))
    A("   row %d: col %d s:f_bl %d | cols %d..%d s:f_b %d | col %d s:f_br %d" % (R_BOTTOM, C0, n["s:f_bl"], C0 + 1, C1 - 1, n["s:f_b"], C1, n["s:f_br"]))
    A("   interior: s:fill %d everywhere, except row %d cols %d..%d = s:rule %d (there from the start, stays), and the text cells below." %
      (n["s:fill"], R_RULE, C0 + 2, C1 - 2, n["s:rule"]))
    A("")
    A("== WAITING STATE  (what the complete panel shows before a line arrives; existing tiles, palette %s)" % P("dim"))
    A("   row %d headline: b:. %d palette %s in each of the 10 letter cells (cols %s) until that letter starts." %
      (R_HEAD, dot, P("dim"), " ".join(str(c) for c, _, _ in headline_cells())))
    A("   row %d winner:   b:- %d palette %s in cols %d..%d until frame %d." % (R_WIN, dash, P("dim"), WAIT_COLS[0], WAIT_COLS[-1], T_WINNER))
    A("   row %d round:    b:- %d palette %s in cols %d..%d until frame %d (row %d instead when the line is MATCH OVER)." %
      (R_ROUND, dash, P("dim"), WAIT_COLS[0], WAIT_COLS[-1], T_ROUND, R_MATCH))
    A("   When a line arrives, every waiting cell of its row that gets no glyph is written back to s:fill %d palette %s on the same frame" % (n["s:fill"], P("pink")))
    A("   (PLAYER n WINS: col 21. ROUND nn: col 21. MATCH OVER: col 20. The other waiting cells are overwritten by glyphs).")
    A("")
    A("== LINE 1  headline \"ALL POPPED!\"  row %d, cols %d..%d (20 cells: letters on even columns, word gap cols 15,16)" % (R_HEAD, C0 + 1, C1 - 1))
    A("   n   col  glyph  tile   start frame (bubble)  burst  white  pink from")
    for col, ch, k in headline_cells():
        s0 = T_HEAD + k * T_LETTER_STEP
        A("   %d   %2d   b:%s    %3d    %3d                   %3d    %3d    %3d" % (k, col, ch, n["p:" + ch] + BACKED, s0, s0 + T_STAGE, s0 + 2 * T_STAGE, s0 + 3 * T_STAGE))
    A("   Stage tiles in the letter's cell: waiting = b:. %d palette %s; bubble = b:} %d palette %s; burst = n:pop_burst %d palette %s;" %
      (dot, P("dim"), n["p:}"] + BACKED, P("pink"), POP_BURST_INDEX, P("pink")))
    A("   white = the glyph with palette %s; pink = the glyph with palette %s." % (P("white"), P("pink")))
    A("")
    A("== LINE 2  winner  row %d. Appears at frame %d with palette %s (icon cells too), takes its own palette at frame %d." %
      (R_WIN, T_WINNER, P("white"), T_WINNER_COLOUR))
    for case, c in CASES.items():
        cells = winner_cells(case)
        A("   case %-4s  %-22s \"%s\"  palette %s  cols %d..%d (%d cells%s)" %
          (case, c["label"], c["text"], P(c["pal"]), cells[0][0], cells[-1][0], cells[-1][0] - cells[0][0] + 1,
           ", icon b:~L b:~R then one blank" if c["icon"] else ", no icon"))
        A("      " + "  ".join("%d:%s=%d" % (col, INDEX_NAME[t], t) for col, t, _ in cells))
    A("")
    A("== LINE 3a  next round  \"ROUND nn\", always two digits, zero-padded (01..99), cols 16..23. Letters on row %d, tall digits on rows %d (top) and %d (bottom)." %
      (R_ROUND, R_DIGIT_TOP, R_ROUND))
    A("   letters: " + "  ".join("%d:%s=%d" % (col, INDEX_NAME[t], t) for col, row, t in round_cells(1) if row == R_ROUND and col < 22))
    A("   digits:  tens at col 22, ones at col 23; top tile = %d + digit (bt:d:0), bottom tile = %d + digit (bt:d:1)" % (TALL_TOP + BACKED, TALL_BOTTOM + BACKED))
    for rn in (2, 12):
        A("   round %2d:  " % rn + "  ".join("%d,%d:%s=%d" % (col, row, INDEX_NAME[t], t) for col, row, t in round_cells(rn) if col >= 22))
    mc = match_cells()
    A("== LINE 3b  last round of a match  \"%s\" replaces ROUND nn. Row %d, cols %d..%d (%d cells, blank at col %d), plain height letters." %
      (MATCH_TEXT, R_MATCH, mc[0][0], mc[-1][0], mc[-1][0] - mc[0][0] + 1, mc[0][0] + MATCH_TEXT.index(" ")))
    A("   " + "  ".join("%d:%s=%d" % (col, INDEX_NAME[t], t) for col, row, t in mc))
    A("   Cell box margins 120 px left and right; ink margins %d px left / %d px right (the 1 px gap is the right side of the last glyph cell)." %
      (match_row[4], 319 - match_row[5]))
    A("   Palette of line 3a and 3b: %s on frames %d..%d and %d..%d, %s on frames %d..%d and %d..%d (all cells of the line swap together)." %
      (P("white"), T_ROUND, T_ROUND + T_BLINK - 1, T_ROUND + 2 * T_BLINK, T_ROUND + 3 * T_BLINK - 1,
       P("gold"), T_ROUND + T_BLINK, T_ROUND + 2 * T_BLINK - 1, T_ROUND + 3 * T_BLINK, FREEZE_FRAMES - 1))
    A("")
    w12, wm = W[("p1_round12", True)], W[("p1_matchover", True)]
    A("== TIMELINE  (game frames; 0 = first frame of the 120 frame freeze). Writes are for case p1.")
    A("   frame      event                                                                   cells written that frame")
    A("   0          outline: rows %d and %d, cols %d and %d. The panel box has its final size.       %d" % (R_TOP, R_BOTTOM, C0, C1, w12[0]))
    A("   1          interior of cols 10, 12, .. 28 (rows %d..%d), waiting marks and rule included      %d" % (R_HEAD, R_ROUND, w12[1]))
    A("   2          interior of cols 11, 13, .. 29: the panel is complete, in its waiting state       %d" % w12[2])
    A("   %d + 4*n    headline letter n starts (n = 0..9): bubble 4 frames, burst 4, white 4, pink      at most %d on any frame %d..%d" %
      (T_HEAD, max(w12[f] for f in range(3, T_WINNER)), 3, T_WINNER - 1))
    A("   %d         last letter (!) turns pink                                                        %d" % (T_HEAD + 9 * T_LETTER_STEP + 3 * T_STAGE, w12[T_HEAD + 9 * T_LETTER_STEP + 3 * T_STAGE]))
    A("   %d         winner line appears, palette white (waiting dashes replaced)                      %d (draw case: %d)" %
      (T_WINNER, w12[T_WINNER], W[("draw_round02", True)][T_WINNER]))
    A("   %d         winner line takes the winner's palette                                            %d (computer: %d, already white)" %
      (T_WINNER_COLOUR, w12[T_WINNER_COLOUR], W[("cpu_round02", True)][T_WINNER_COLOUR]))
    A("   %d         ROUND nn or MATCH OVER appears, palette white (waiting dashes replaced)           %d (MATCH OVER: %d)" % (T_ROUND, w12[T_ROUND], wm[T_ROUND]))
    A("   %d, %d, %d  line 3 swaps palette: gold, white, gold                                         %d each (MATCH OVER: %d)" %
      (T_ROUND + T_BLINK, T_ROUND + 2 * T_BLINK, T_ROUND + 3 * T_BLINK, w12[T_ROUND + T_BLINK], wm[T_ROUND + T_BLINK]))
    A("   %d..%d    steady gold, nothing changes                                                       0" % (T_ROUND + 3 * T_BLINK + 1, FREEZE_FRAMES - 1))
    A("   %d        freeze over: clear the banner. Mirror of the draw so the box keeps its size until the end:" % T_CLEAR)
    A("              frame 120 interior of cols 11, 13, .. 29 (60), frame 121 interior of cols 10, 12, .. 28 (60), frame 122 the outline (56).")
    A("")
    A("== CELL WRITES PER FRAME  (frame:count, frames without a write left out; a write = cell whose tile or palette changes)")
    for x in shown:
        A("   %-13s split draw : %s" % (tag(*x), write_rows(W[(tag(*x), True)])))
    A("   %-13s single draw: %s" % ("p1_round02", write_rows(W[("p1_round02", False)])))
    A("   Peak, split draw (this spec): %d cells on frame %d. After frame 2 the peak is %d (%s)." % (peak_split[0], peak_split[1], peak_after[0], peak_after[1]))
    A("   Peak, single draw (all %d cells on frame 0, frames 1 and 2 idle): %d. Same picture from frame 2 on." % (total_cells, peak_one[0]))
    A("   Why the split does not read as growing: the outline on frame 0 already spans the final box, and the plate arrives as")
    A("   alternate columns over the whole box (no edge moves, no direction). Frames 0 and 1 last 16.7 ms each.")
    A("")
    for x, head in ((("p1", 12, False), "case p1, round 12"), (("p1", 2, True), "case p1, last round (MATCH OVER)")):
        A("== FULL CELL MAP, last frame (119), %s.  tile index / palette index per cell, rows %d..%d, cols %d..%d" % (head, R_TOP, R_BOTTOM, C0, C1))
        lastb = build(FREEZE_FRAMES - 1, *x)
        A("   col   " + " ".join("%5d" % c for c in range(C0, C1 + 1)))
        for r in range(R_TOP, R_BOTTOM + 1):
            A("   row %d " % r + " ".join("%3d/%d" % (lastb.cells[(c, r)][0], PAL_ORDER.index(lastb.cells[(c, r)][1])) for c in range(C0, C1 + 1)))
        A("")
    A("== FULL CELL MAP, waiting state (frame 2 and 3), ROUND case")
    wb = build(2, "p1", 2)
    A("   col   " + " ".join("%5d" % c for c in range(C0, C1 + 1)))
    for r in range(R_TOP, R_BOTTOM + 1):
        A("   row %d " % r + " ".join("%3d/%d" % (wb.cells[(c, r)][0], PAL_ORDER.index(wb.cells[(c, r)][1])) for c in range(C0, C1 + 1)))
    open(os.path.join(HERE, "banner_spec.txt"), "w").write("\n".join(S) + "\n")

    # ---- numbers.txt ----
    L = []
    N = L.append
    N("ROUND CLEAR BANNER, SECOND FINAL (full size panel from frame 0), 10 November 2026 (written by draw_round_clear_banner_final2.py)")
    N("")
    N("cost: new tiles 1 (pop burst, sheet index %d); new palettes 0; palettes used %d (%s); distinct tiles used %d; banner cells %d (22 x 8)." %
      (POP_BURST_INDEX, len(used_pals), ", ".join(used_pals), len(used_tiles), total_cells))
    N("cell writes per frame, split draw (specified): frame 0 = %d (outline), frame 1 = %d, frame 2 = %d; peak %d; after frame 2 at most %d (%s)." %
      (w12[0], w12[1], w12[2], peak_split[0], peak_after[0], peak_after[1]))
    N("cell writes per frame, single draw (alternative): frame 0 = %d, then the same as the split draw from frame 3 on." % peak_one[0])
    N("")
    N("PANEL SIZE CHECK (measured on the rendered frames, not on the cell table):")
    N("  method: bounding box of all pixels where the composed 320 x 224 frame differs from its backdrop, on each of the 120 frames.")
    N("  runs: %d (6 cases x 3 sky moods x split and single draw) x %d frames = %d frames measured." % (box_runs, FREEZE_FRAMES, box_runs * FREEZE_FRAMES))
    N("  result: %s. Box x %d..%d, y %d..%d (176 x 64 px = cols %d..%d, rows %d..%d) on every frame; distinct boxes found: 1." %
      ("PASS" if not box_bad else "FAIL", want[0], want[2], want[1], want[3], C0, C1, R_TOP, R_BOTTOM))
    N("  panel cells present, split draw: frame 0 = %d (outline), frame 1 = %d, frames 2..119 = %d. Single draw: %d on all frames." %
      (cell_counts[0], cell_counts[1], cell_counts[2], total_cells))
    assert all(cell_counts[f] == total_cells for f in range(2, FREEZE_FRAMES))
    N("")
    N("centring (screen is 320 px, centre between x 159 and 160). Left = first ink column, right margin = 319 - last ink column.")
    N("ink = every pixel that is not plate; face = glyph face without its 1 px drop shadow (icon: body colours).")
    N("  panel: 22 cells, left margin %d px, right margin %d px" % (panel_left, panel_right))
    N("  case            line        cells  first col  ink margins L/R   face margins L/R")
    for t, name, ncell, col, a, b, fa, fb in centre_rows:
        N("  %-15s %-11s %3d    %3d        %3d / %3d         %3d / %3d" % (t, name, ncell, col, a, 319 - b, fa, 319 - fb))
    N("  Every line has an even cell count, so every cell box is centred exactly. Ink differs from the box only by glyph shape:")
    N("  the face of a Gumdrop letter is 7 px wide with a 1 px shadow on the right, and the last headline glyph (!) and the digit 1 are narrow.")
    N("")
    N("contrast (0..255 luminance gap, text cell face against the brightest quarter of its surroundings; under 90 is hard to read at 1x)")
    for m in MOODS:
        worst, per_pal, match_con = con[m]
        N("  %-5s worst text cell %.0f  (%s)" % (m, worst[0], worst[1]))
        N("        winner line by palette, worst cell: " + ", ".join("%s %.0f" % (k, v) for k, v in per_pal.items()) + "; MATCH OVER gold %.0f" % match_con)
    N("  All text sits on the navy plate inside its own tile, so the text numbers do not depend on the sky.")
    N("  The waiting marks (dim dots and dashes) are not text and are not in these numbers; they are meant to be faint.")
    N("")
    N("notes:")
    for x in notes:
        N("  " + x)
    N("  Round 12 and MATCH OVER pictures keep the HUD mock-up at ROUND 1 (the mock-up has one round digit).")
    N("  Backdrops are HUD mock-ups (copied from 2026-11-10-hud-title-final), not MAME screenshots.")
    N("  GIF: game frames 0, 1, 2 at 20, 20, 30 ms (real 16.7, 16.7, 33.3), then one picture per 4 game frames at 70 ms (real 66.7).")
    open(os.path.join(HERE, "numbers.txt"), "w").write("\n".join(L) + "\n")

    # ---- index.html ----
    def img(name, w=640, h=448):
        return '<img src="%s" width="%d" height="%d" alt="%s">' % (name, w, h, name)

    H = ["""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Gumbirds: round clear banner, second final</title>
<style>
body { background: #e6e7ea; color: #23252b; font-family: Helvetica, Arial, sans-serif; margin: 24px; line-height: 1.45; }
h1 { font-size: 22px; margin: 0 0 6px; } h2 { font-size: 17px; margin: 34px 0 6px; color: #101114; }
p { margin: 4px 0 10px; max-width: 1300px; } .num { color: #4c4f59; font-size: 14px; }
img { image-rendering: pixelated; image-rendering: crisp-edges; image-rendering: pixelated; display: block; border: 1px solid #9a9ca6; background: #000; }
.row { display: flex; flex-wrap: wrap; gap: 14px; margin: 8px 0 4px; } .cell { font-size: 13px; color: #4c4f59; }
table { border-collapse: collapse; font-size: 14px; margin: 6px 0 12px; background: #f4f5f7; } td, th { border: 1px solid #b4b6be; padding: 4px 10px; text-align: left; }
th { color: #101114; font-weight: 600; }
</style></head><body>
<h1>Gumbirds: round clear banner, second final</h1>
<p>The panel now has its full size from the first frame and never changes size; text and icons arrive inside it.
Shown while play is frozen for 2 seconds (120 frames) after a round ends. Fix layer only, Gumdrop font, 320 x 224 shown at 2x.
Backdrops are the HUD mock-ups, not MAME screenshots. Build data: banner_spec.txt. Measurements: numbers.txt.</p>
<p class="num">Cost: 1 new tile (pop burst), 0 new palettes, %d fix cells. Most cell writes in one frame: %d (split draw).
Panel box measured on %d rendered frames: x %d to %d, y %d to %d on every one. Worst text cell contrast: %s.</p>
""" % (total_cells, peak_split[0], box_runs * FREEZE_FRAMES, want[0], want[2], want[1], want[3], ", ".join("%s %.0f" % (m, con[m][0][0]) for m in MOODS))]
    H.append('<h2>Player 1 wins, on the three sky moods (animated)</h2><div class="row">')
    for m in MOODS:
        H.append('<div class="cell">%s%s</div>' % (img("anim_p1_round02_%s_1x.gif" % m), m))
    H.append('</div>')
    H.append('<h2>Timeline</h2><table><tr><th>Frame</th><th>What happens</th></tr>'
             '<tr><td>0 to 2</td><td>The whole panel is drawn at its final size: outline on frame 0, navy plate on frames 1 and 2. '
             'It waits with a pink rule, a dim dot where each headline letter will land, and dim dashes where the two text lines will come.</td></tr>'
             '<tr><td>%d to %d</td><td>ALL POPPED! letter by letter, a new letter every 4 frames: gum bubble, pop burst, white flash, pink (4 frames each).</td></tr>'
             '<tr><td>%d</td><td>Winner line appears in white.</td></tr>'
             '<tr><td>%d</td><td>Winner line takes the winner colour.</td></tr>'
             '<tr><td>%d</td><td>ROUND and the zero-padded round number (or MATCH OVER after the last round) appear in white, then swap white and gold every %d frames.</td></tr>'
             '<tr><td>%d to 119</td><td>The line stays gold.</td></tr>'
             '<tr><td>120</td><td>Freeze over, banner cleared.</td></tr></table>' %
             (T_HEAD, T_HEAD + 9 * T_LETTER_STEP + 3 * T_STAGE, T_WINNER, T_WINNER_COLOUR, T_ROUND, T_BLINK, T_ROUND + 3 * T_BLINK))
    H.append('<h2>Constant panel size: key frames 0, 4, 24, 48, 56, 72, 119</h2>'
             '<p>Banner area, dusk. The light blue ticks in each label mark the first and last pixel column of the panel (x %d and %d): the same on every frame. '
             'Left: ROUND 02. Right: last round, MATCH OVER.</p>' % (want[0], want[2]))
    H.append('<div class="row"><div class="cell">%sROUND 02</div><div class="cell">%sMATCH OVER</div></div>' %
             (img("key_frames_dusk_1x.png", key_sheet.width * 2, key_sheet.height * 2), img("key_frames_matchover_dusk_1x.png", key_match.width * 2, key_match.height * 2)))
    H.append('<h2>The first three frames (split draw)</h2><p>Frame 0 writes the outline (%d cells), frame 1 every second column of the plate (%d), frame 2 the rest (%d). '
             'The box is the final size on all three; frames 0 and 1 last one sixtieth of a second each. Bottom picture: the alternative, all %d cells on frame 0.</p>' %
             (w12[0], w12[1], w12[2], total_cells))
    H.append('<div class="row"><div class="cell">%s</div><div class="cell">%sone headline cell at 8x: waiting dot, gum bubble, pop burst (the one new tile), white flash, pink</div></div>'
             % (img("first_frames_dusk_1x.png", first_sheet.width * 2, first_sheet.height * 2), img("letter_stages_8x.png", stage.width, stage.height)))
    H.append('<h2>The other cases (animated)</h2><div class="row">')
    for case, rn, last, m, text in (("p2", 2, False, "moon", "Player 2 wins, lime"), ("cpu", 2, False, "storm", "Computer bird wins: COMPUTER WINS, white"),
                                    ("draw", 2, False, "dusk", "No survivor: NO SURVIVORS, dim blue, no bird icon"),
                                    ("p1", 12, False, "moon", "Two-digit round: ROUND 12"), ("p1", 2, True, "dusk", "Last round of the match: MATCH OVER, gold")):
        H.append('<div class="cell">%s%s (%s)</div>' % (img("anim_%s_%s_1x.gif" % (tag(case, rn, last), m)), text, m))
    H.append('</div>')
    H.append('<h2>Last frame, every case on every sky mood</h2>')
    for case, rn, last in shown:
        H.append('<p>%s</p><div class="row">' % title(case, rn, last))
        for m in MOODS:
            H.append('<div class="cell">%s%s</div>' % (img("still_%s_%s_1x.png" % (tag(case, rn, last), m)), m))
        H.append('</div>')
    H.append('<h2>Centre line proof</h2><p>Light blue line: screen centre (between pixel 159 and 160). Yellow marks: first and last ink column of each line, '
             'shadow included. Every line has an even cell count, so every cell box is centred exactly. '
             'From top to bottom: player 1, player 2, computer, no survivors, round 12, match over.</p>')
    H.append('<div class="row"><div class="cell">%s</div></div>' % img("centre_proof_dusk_2x.png", proof.width, proof.height))
    H.append('<table><tr><th>Case</th><th>Line</th><th>Cells</th><th>Ink margin left / right (pixels)</th><th>Face margin left / right</th></tr>')
    for t, name, ncell, col, a, b, fa, fb in centre_rows:
        H.append('<tr><td>%s</td><td>%s</td><td>%d</td><td>%d / %d</td><td>%d / %d</td></tr>' % (t, name, ncell, a, 319 - b, fa, 319 - fb))
    H.append('</table>')
    H.append('<h2>Contrast per sky mood</h2><table><tr><th>Mood</th><th>Worst text cell</th><th>Winner line by colour (worst cell)</th><th>MATCH OVER, gold</th></tr>')
    for m in MOODS:
        worst, per_pal, match_con = con[m]
        H.append('<tr><td>%s</td><td>%.0f</td><td>%s</td><td>%.0f</td></tr>' % (m, worst[0], ", ".join("%s %.0f" % kv for kv in per_pal.items()), match_con))
    H.append('</table><p class="num">Scale 0 to 255; under 90 is hard to read at 1x. Text sits on the navy plate of its own tile, so the sky does not change it.</p>')
    H.append("</body></html>\n")
    open(os.path.join(HERE, "index.html"), "w").write("\n".join(H))
    print(open(os.path.join(HERE, "numbers.txt")).read())


if __name__ == "__main__":
    main()
