#!/opt/homebrew/bin/python3.14 -I
"""Round clear banner drafts for Gumbirds (fix layer only: 8x8 tiles, 40x28 cells, one 16-colour palette per tile,
no flip, no scaling).

Run: /opt/homebrew/bin/python3.14 -I draw_round_clear_banner.py   (from any directory)

Reads (read only):
  assets/font/fix_font_sheet.png + fix_font.json   the Gumdrop fix font and its five palettes
  thoughts/shared/drafts/2026-11-10-hud-title-final/hud2p_<mood>_1x.png   arena mock-ups with the HUD, used as backdrop
Writes into this folder: variant PNG and GIF files, new_tiles_8x.png, index.html, numbers.txt.

Every banner is a grid of (tile index, palette name) cells, drawn the way the fix layer draws: nothing else is painted.
New tiles are listed in NEW_TILES and get the free sheet indices from 148 up.
"""
import json
import os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
SHEET = os.path.join(ROOT, "assets/font/fix_font_sheet.png")
META = os.path.join(ROOT, "assets/font/fix_font.json")
BACKDROP = os.path.join(ROOT, "thoughts/shared/drafts/2026-11-10-hud-title-final/hud2p_%s_1x.png")
MOODS = ["moon", "dusk", "storm"]
COLS, ROWS = 40, 28
FREEZE_FRAMES = 120          # decided rule: play freezes 2 seconds
BACKED = 96                  # backed copy of a glyph tile = its index + 96
TALL_TOP, TALL_BOTTOM = 64, 80
FREE_INDICES = list(range(148, 160)) + list(range(75, 80)) + list(range(90, 96)) + list(range(170, 176)) + \
    list(range(186, 192)) + list(range(192, 255))


def q5(c):
    """Round a colour to the Neo Geo 5-bit steps the font palettes use."""
    return tuple((v >> 3) * 8 + (v >> 3) // 4 for v in c)


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
    return meta["tiles"], tiles, pals


NAMES, TILES, PALS = load_font()
FONT_PALETTES = list(PALS)

# ---- new palettes (slot 1..15; slot 13 is the plate fill colour of every backed glyph) ----
# Band palettes turn the navy plate of the backed glyphs into gum pink: no new glyph tiles needed.
_base = PALS["white"]
def _pal(face, shadow, deep, mid, light, fill):
    p = list(_base)
    p[0:4] = face
    p[4] = shadow
    p[8], p[9], p[10] = deep, mid, light
    p[12] = fill
    return [q5(c) for c in p]

GUM_DEEP, GUM_MID, GUM_LIGHT = (181, 41, 165), (255, 82, 181), (255, 165, 222)
PLUM = (74, 8, 82)
PALS["band"] = _pal([(255, 255, 255), (255, 255, 255), (255, 239, 247), (255, 214, 239)], PLUM, GUM_DEEP, GUM_MID, GUM_LIGHT, GUM_MID)
PALS["bandgold"] = _pal([(255, 255, 214), (255, 247, 148), (255, 231, 115), (255, 206, 82)], PLUM, GUM_DEEP, GUM_MID, GUM_LIGHT, GUM_MID)
NEW_PALETTES = ["band", "bandgold"]

# ---- new tiles ----
NEW_TILES = {}      # name -> (index, pixels)


def add_tile(name, rows):
    assert len(rows) == 8 and all(len(r) == 8 for r in rows), name
    pix = tuple(tuple(".123456789ABCDEF".index(ch) for ch in r) for r in rows)
    for n, (idx, p) in NEW_TILES.items():
        if p == pix:
            NAMES["n:" + name] = idx
            return idx
    idx = FREE_INDICES[len(NEW_TILES)]
    NEW_TILES[name] = (idx, pix)
    TILES[idx] = pix
    NAMES["n:" + name] = idx
    return idx


def band_top(h):
    """Top edge of the gum band, edge h pixels lower than the thickest place. 5 outline, B highlight, D fill."""
    rows = []
    for y in range(8):
        rows.append("........" if y < 1 + h else "55555555" if y == 1 + h else "BBBBBBBB" if y == 2 + h else "DDDDDDDD")
    return rows


def band_bottom(h):
    rows = []
    for y in range(8):
        rows.append("........" if y > 6 - h else "55555555" if y == 6 - h else "99999999" if y == 5 - h else "DDDDDDDD")
    return rows


def band_bottom_drip(h):
    """Bottom edge with a drip neck (columns 2..5) that runs on into the cell below."""
    rows = band_bottom(h)
    return [r if y < 6 - h else "55D99D55" if y == 6 - h else ".5D99D5." for y, r in enumerate(rows)]


for _h in range(4):
    add_tile("band_top_%d" % _h, band_top(_h))
    add_tile("band_bottom_%d" % _h, band_bottom(_h))
add_tile("band_drip_neck_0", band_bottom_drip(0))
add_tile("band_drip_neck_1", band_bottom_drip(1))
add_tile("band_drip_long", [".5D99D5.", ".5D99D5.", ".5D99D5.", ".5DD9D5.", "5DDDD9D5", "5DCDD995", "5DDD9995", ".555555."])
add_tile("band_drip_short", [".5D99D5.", ".5DD995.", ".5D9995.", "..5555..", "........", "........", "........", "........"])
# pop burst on the navy plate (variant D): slot B gum mid, C gum light, D plate
add_tile("pop_burst", ["DDDBDDDD", "DBDBDBDD", "DDCDCDDD", "BBDDDBBD", "DDCDCDDD", "DBDBDBDD", "DDDBDDDD", "DDDDDDDD"])


# ---- fix layer model ----
class Fix:
    def __init__(self):
        self.cells = {}          # (col, row) -> (tile index, palette name)
        self.text_cells = set()

    def put(self, col, row, tile, pal, text=False):
        assert 0 <= col < COLS and 0 <= row < ROWS, (col, row)
        self.cells[(col, row)] = (tile, pal)
        if text:
            self.text_cells.add((col, row))

    def text(self, row, s, pal, backed=False, col=None, tall_digits=False):
        """Print s; col None = centred (odd lengths sit 4 px left of centre: the grid has 40 cells)."""
        if col is None:
            col = (COLS - len(s)) // 2
        for i, ch in enumerate(s):
            if ch == " ":
                if backed:
                    self.put(col + i, row, NAMES["s:fill"], pal)
                    if tall_digits:
                        self.put(col + i, row - 1, NAMES["s:fill"], pal)
                continue
            if tall_digits and ch.isdigit():
                off = BACKED if backed else 0
                self.put(col + i, row - 1, TALL_TOP + int(ch) + off, pal, True)
                self.put(col + i, row, TALL_BOTTOM + int(ch) + off, pal, True)
                continue
            self.put(col + i, row, NAMES["p:" + ch] + (BACKED if backed else 0), pal, True)
            if tall_digits and backed:
                self.put(col + i, row - 1, NAMES["s:fill"], pal)
        return col, col + len(s) - 1

    def plate(self, row, c0, c1, pal):
        self.put(c0 - 1, row, NAMES["s:capL"], pal)
        self.put(c1 + 1, row, NAMES["s:capR"], pal)

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

    def stats(self):
        new_idx = {idx for idx, _ in NEW_TILES.values()}
        used_new = sorted({t for t, _ in self.cells.values() if t in new_idx})
        pals = sorted({p for _, p in self.cells.values()})
        return {"cells": len(self.cells), "text_cells": len(self.text_cells), "new_tiles": used_new, "palettes": pals}


# ---- the four variants ----
LINE1_ROW, LINE2_ROW = 12, 14


def spaced(text):
    """Headline spacing: one blank cell between letters, three between words."""
    return "   ".join(" ".join(w) for w in text.split(" "))


def variant_a():
    f = Fix()
    f.text(LINE1_ROW, "ROUND CLEAR", "white")
    f.text(LINE2_ROW, "ROUND 2", "gold")
    return f


def band_h(col):
    """Edge offset per cell: 0 at the screen edges, 3 in the middle (the gum is stretched thin there).
    Steps fall on cell borders, so flat edge tiles are enough."""
    import math
    return round(3 * math.sin(math.pi * (col + 0.5) / COLS))


def variant_b():
    f = Fix()
    top, bottom = 11, 15
    for c in range(COLS):
        h = band_h(c)
        f.put(c, top, NAMES["n:band_top_%d" % h], "band")
        f.put(c, bottom, NAMES["n:band_bottom_%d" % h], "band")
        for r in range(top + 1, bottom):
            f.put(c, r, NAMES["s:fill"], "band")
    for c, kind in ((3, "long"), (5, "short"), (36, "long"), (34, "short")):
        h = band_h(c)
        assert h in (0, 1), (c, h)
        f.put(c, bottom, NAMES["n:band_drip_neck_%d" % h], "band")
        f.put(c, bottom + 1, NAMES["n:band_drip_%s" % kind], "band")
    f.text(LINE1_ROW, spaced("ROUND CLEAR"), "band", backed=True)
    f.text(LINE2_ROW, "ROUND 2", "bandgold", backed=True)
    return f


def variant_c():
    f = Fix()
    c0, c1, r0, r1 = 8, 30, 10, 17
    for c in range(c0, c1 + 1):
        for r in range(r0, r1 + 1):
            if r == r0:
                n = "f_tl" if c == c0 else "f_tr" if c == c1 else "f_t"
            elif r == r1:
                n = "f_bl" if c == c0 else "f_br" if c == c1 else "f_b"
            else:
                n = "f_l" if c == c0 else "f_r" if c == c1 else "fill"
            f.put(c, r, NAMES["s:" + n], "white")
    line = "PLAYER 1 WINS"
    col = (COLS - (len(line) + 6)) // 2
    for i, n in enumerate(("~L", "~R")):
        f.put(col + i, 12, NAMES["p:" + n] + BACKED, "pink", True)
        f.put(col + len(line) + 4 + i, 12, NAMES["p:" + n] + BACKED, "pink", True)
    f.text(12, line, "pink", backed=True, col=col + 3)
    for c in range(c0 + 2, c1 - 1):
        f.put(c, 13, NAMES["s:rule"], "white")
    f.text(15, "ROUND 2", "white", backed=True, tall_digits=True)
    return f


D_LINE1, D_LINE2 = spaced("ALL POPPED!"), "ROUND 2"
D_LETTER_STEP = 4      # game frames between two letters starting
D_STAGE = 4            # game frames per stage: bubble, burst, white flash, then pink
D_LINE2_AT = 60
D_BLINK = 8


def variant_d(frame=FREEZE_FRAMES - 1):
    """Fix layer of variant D at a game frame (0..119)."""
    f = Fix()
    col = (COLS - len(D_LINE1)) // 2
    c0, c1 = col - 1, col + len(D_LINE1)
    for c in range(c0, c1 + 1):
        e = "l" if c == c0 else "r" if c == c1 else ""
        f.put(c, LINE1_ROW - 1, NAMES["s:f_t" + e], "pink")
        f.put(c, LINE1_ROW + 1, NAMES["s:f_b" + e], "pink")
    f.put(c0, LINE1_ROW, NAMES["s:f_l"], "pink")
    f.put(c1, LINE1_ROW, NAMES["s:f_r"], "pink")
    k = 0
    for i, ch in enumerate(D_LINE1):
        if ch == " ":
            f.put(col + i, LINE1_ROW, NAMES["s:fill"], "pink")
            continue
        age = frame - k * D_LETTER_STEP
        k += 1
        if age < 0:
            f.put(col + i, LINE1_ROW, NAMES["s:fill"], "pink")
        elif age < D_STAGE:
            f.put(col + i, LINE1_ROW, NAMES["p:{"] + 1 + BACKED, "pink")       # gum bubble icon (tile 49 + 96)
        elif age < 2 * D_STAGE:
            f.put(col + i, LINE1_ROW, NAMES["n:pop_burst"], "pink")
        else:
            f.put(col + i, LINE1_ROW, NAMES["p:" + ch] + BACKED, "white" if age < 3 * D_STAGE else "pink", True)
    if frame >= D_LINE2_AT:
        pal = "white" if ((frame - D_LINE2_AT) // D_BLINK) % 2 == 0 and frame < FREEZE_FRAMES - 24 else "gold"
        a, b = f.text(LINE2_ROW + 1, D_LINE2, pal, backed=True)
        f.plate(LINE2_ROW + 1, a, b, pal)
    return f


def d_all_frames():
    return [variant_d(fr) for fr in range(0, FREEZE_FRAMES, D_STAGE)]


# ---- backdrop ----
def lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def load_backdrop(mood, notes):
    """Arena mock-up with HUD. Its HUD row says ROUND 3; set it to ROUND 2 so the screen agrees with the banner."""
    im = Image.open(BACKDROP % mood).convert("RGB")
    assert im.size == (320, 224)
    three, two = NAMES["p:3"] + BACKED, NAMES["p:2"] + BACKED
    px = im.load()
    done = False
    for r in range(ROWS):
        for c in range(COLS):
            for pal in FONT_PALETTES:
                p = PALS[pal]
                dee = NAMES["p:D"] + BACKED
                if c >= 2 and all(px[c * 8 + x, r * 8 + y] == p[TILES[three][y][x] - 1] and
                                  px[(c - 2) * 8 + x, r * 8 + y] == p[TILES[dee][y][x] - 1] for y in range(8) for x in range(8)):
                    # the cell left of it must be blank plate and two cells left a D (ROUND 3)
                    for y in range(8):
                        for x in range(8):
                            px[c * 8 + x, r * 8 + y] = p[TILES[two][y][x] - 1]
                    done = True
                    notes.append("backdrop %s: HUD digit 3 at cell %d,%d (palette %s) changed to 2" % (mood, c, r, pal))
                    break
            if done:
                break
        if done:
            break
    if not done:
        notes.append("backdrop %s: HUD round digit not found, HUD still says ROUND 3" % mood)
    return im


def darken(im, factor):
    return im.point(lambda v: ((int(v * factor)) >> 3) * 8 + (int(v * factor) >> 3) // 4)


def compose(back, fix):
    out = back.convert("RGBA")
    out.alpha_composite(fix.render())
    return out.convert("RGB")


def contrast(back, fix):
    """Per text cell: luminance of the two lightest face slots against what shows around the glyph in that cell
    (backdrop or plate). Returns (worst cell, mean over cells, share of cells under 90)."""
    comp = compose(back, fix).load()
    vals = []
    for (c, r) in fix.text_cells:
        t, pal = fix.cells[(c, r)]
        pix = TILES[t]
        face = [lum(comp[c * 8 + x, r * 8 + y]) for y in range(8) for x in range(8) if pix[y][x] in (1, 2)]
        # glyph body = slots 1..5 (face and its shadow); icons use other slots and are skipped here
        around = [lum(comp[c * 8 + x, r * 8 + y]) for y in range(8) for x in range(8) if pix[y][x] not in (1, 2, 3, 4, 5)]
        if not face or not around:
            continue
        # worst neighbour: brightest 25% of the surrounding pixels
        around.sort()
        hi = around[-max(1, len(around) // 4):]
        vals.append(sum(face) / len(face) - sum(hi) / len(hi))
    if not vals:
        return (0, 0, 0)
    return (min(vals), sum(vals) / len(vals), sum(1 for v in vals if v < 90) / len(vals))


def save_gif(frames, path, ms):
    # one shared palette so the frames do not shimmer
    w, h = frames[0].size
    strip = Image.new("RGB", (w, h * len(frames)))
    for i, fr in enumerate(frames):
        strip.paste(fr, (0, i * h))
    pal_im = strip.quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    out = [fr.quantize(palette=pal_im, dither=Image.Dither.NONE) for fr in frames]
    out[0].save(path, save_all=True, append_images=out[1:], duration=ms, loop=0, optimize=False, disposal=1)
    return len(set(strip.getdata()))


def new_tile_sheet(path):
    names = list(NEW_TILES)
    im = Image.new("RGB", (len(names) * 9 + 1, 10), (40, 40, 48))
    px = im.load()
    for i, n in enumerate(names):
        idx, pix = NEW_TILES[n]
        p = PALS["band"] if n.startswith("band") else PALS["pink"]
        for y in range(8):
            for x in range(8):
                px[1 + i * 9 + x, 1 + y] = p[pix[y][x] - 1] if pix[y][x] else (70, 70, 80)
    im.resize((im.width * 8, im.height * 8), Image.NEAREST).save(path)


def main():
    notes = []
    backs = {m: load_backdrop(m, notes) for m in MOODS}
    variants = {
        "a": ("A  Plain text", "Two centred lines, plain Gumdrop glyphs, white over gold. Nothing behind the letters.", variant_a()),
        "b": ("B  Gum band", "Same text on a gum pink band over the full width, thinner in the middle, with drips; headline letter-spaced.", variant_b()),
        "c": ("C  Winner call", "Navy panel from the results screen tiles, PLAYER 1 WINS in the player colour between two Sootling icons, tall round digit.", variant_c()),
        "d": ("D  All popped", "ALL POPPED! letter-spaced in a navy ribbon (panel tiles); each letter arrives as a gum bubble, pops, flashes white and settles pink; ROUND 2 blinks white and gold.", variant_d()),
    }
    lines = []
    stats = {}
    for key, (title, _, fix) in variants.items():
        for m in MOODS:
            compose(backs[m], fix).save(os.path.join(HERE, "variant_%s_%s_1x.png" % (key, m)))
        st = fix.stats()
        st["contrast"] = {m: contrast(backs[m], fix) for m in MOODS}
        stats[key] = st
    # A again on a darkened backdrop (needs a palette fade of every sprite palette: code cost, not fix layer)
    for m in MOODS:
        compose(darken(backs[m], 0.5), variants["a"][2]).save(os.path.join(HERE, "variant_a_dark_%s_1x.png" % m))
    stats["a_dark"] = {m: contrast(darken(backs[m], 0.5), variants["a"][2]) for m in MOODS}

    # D animation
    d_frames = d_all_frames()
    d_new = sorted({t for f in d_frames for t in f.stats()["new_tiles"]})
    d_pals = sorted({p for f in d_frames for p in f.stats()["palettes"]})
    d_cells = max(f.stats()["cells"] for f in d_frames)
    stats["d"]["new_tiles"], stats["d"]["palettes"], stats["d"]["cells"] = d_new, d_pals, d_cells
    gif_ms = round(D_STAGE * 1000 / 60 / 10) * 10
    gif_cols = {}
    for m in MOODS:
        frames = [compose(backs[m], f) for f in d_frames]
        gif_cols[m] = save_gif(frames, os.path.join(HERE, "variant_d_anim_%s_1x.gif" % m), gif_ms)
    # the four stages of one letter, enlarged
    stage = Image.new("RGB", (4 * 10 + 2, 12), (40, 40, 48))
    for i, (t, pal) in enumerate(((NAMES["p:{"] + 1 + BACKED, "pink"), (NAMES["n:pop_burst"], "pink"),
                                  (NAMES["p:P"] + BACKED, "white"), (NAMES["p:P"] + BACKED, "pink"))):
        f = Fix()
        f.put(0, 0, t, pal)
        stage.paste(f.render().crop((0, 0, 8, 8)).convert("RGB"), (2 + i * 10, 2))
    stage.resize((stage.width * 8, stage.height * 8), Image.NEAREST).save(os.path.join(HERE, "variant_d_stages_8x.png"))
    new_tile_sheet(os.path.join(HERE, "new_tiles_8x.png"))

    # ---- numbers.txt ----
    def fmt_con(c):
        return "worst %4.0f  mean %4.0f  cells under 90: %3.0f%%" % (c[0], c[1], c[2] * 100)

    idx_name = {idx: n for n, (idx, _) in NEW_TILES.items()}
    L = lines.append
    L("ROUND CLEAR BANNER DRAFTS, 10 November 2026 (written by draw_round_clear_banner.py)")
    L("")
    L("Fix layer only. Font and palettes: assets/font/fix_font_sheet.png + fix_font.json (Gumdrop, 192 sheet slots in use, 5 palettes).")
    L("New tiles go to free sheet indices from 148; the S-ROM has 256 slots, 98 free before these drafts.")
    L("New tiles drawn in total (all variants): %d.  New palettes in total: %d (%s).  Fix palettes in use today: 5." %
      (len(NEW_TILES), len(NEW_PALETTES), ", ".join(NEW_PALETTES)))
    L("Text cells = cells holding a glyph or icon tile. Fix cells = every cell the banner writes (and must clear after).")
    L("Contrast = per text cell, mean luminance of the two lightest face colours minus the brightest quarter of what shows")
    L("around the glyph in that cell (0..255 scale). Under 90 is hard to read at 1x.")
    L("")
    for key, (title, desc, _) in variants.items():
        st = stats[key]
        L("== %s" % title)
        L("  %s" % desc)
        L("  new unique tiles beyond the font: %d%s" % (len(st["new_tiles"]),
          "" if not st["new_tiles"] else "  (" + ", ".join("%d %s" % (i, idx_name[i]) for i in st["new_tiles"]) + ")"))
        newp = [p for p in st["palettes"] if p in NEW_PALETTES]
        L("  palettes: %d (%s); new: %d%s" % (len(st["palettes"]), ", ".join(st["palettes"]), len(newp), "" if not newp else " (" + ", ".join(newp) + ")"))
        L("  text cells: %d   fix cells written: %d" % (st["text_cells"], st["cells"]))
        for m in MOODS:
            L("  contrast %-5s %s" % (m, fmt_con(st["contrast"][m])))
        if key == "a":
            for m in MOODS:
                L("  contrast %-5s %s   (backdrop at half brightness: needs a fade of every sprite palette)" % (m, fmt_con(stats["a_dark"][m])))
        if key == "d":
            L("  animation: %d game frames. Letter n starts at frame %d * n; stages of %d frames each: gum bubble (tile 145), pop burst (new)," %
              (FREEZE_FRAMES, D_LETTER_STEP, D_STAGE))
            L("  letter in the white palette, letter in the pink palette. ROUND 2 appears at frame %d and swaps white / gold every %d frames," % (D_LINE2_AT, D_BLINK))
            L("  steady gold for the last 24 frames. Per frame at most 3 cells change tile or palette (plus 9 cells when line 2 appears, 69 for the ribbon at frame 0).")
            L("  GIF: %d frames of %d ms (one per %d game frames; real time would be %.1f ms), colours per mood: %s" %
              (len(d_frames), gif_ms, D_STAGE, D_STAGE * 1000 / 60, ", ".join("%s %d" % (m, gif_cols[m]) for m in MOODS)))
        L("")
    L("new palettes (slot 1..15, RGB at 5-bit steps):")
    for n in NEW_PALETTES:
        L("  %-8s %s" % (n, " ".join("%d,%d,%d" % c for c in PALS[n])))
    L("  band: slot 13 (the plate colour of every backed glyph) is gum pink, so the 52 backed glyph tiles are reused as they are.")
    L("  B with one palette only: print both lines with palette band (line 2 white instead of gold).")
    L("")
    L("notes:")
    for n in notes:
        L("  " + n)
    L("  Lines with an odd cell count (ROUND CLEAR 11 or 23 spaced, ROUND 2 7, ALL POPPED! 23 spaced) sit 4 px left of the screen centre: the grid")
    L("  has 40 cells and fix tiles cannot shift. All four variants keep both lines odd so they share one axis.")
    L("  Fix tiles cannot flip, so every band edge height is its own tile; steps fall on cell borders, no slope tiles.")
    L("  Backdrops are HUD mock-ups from 2026-11-10-hud-title-final, not MAME screenshots.")
    open(os.path.join(HERE, "numbers.txt"), "w").write("\n".join(lines) + "\n")

    # ---- index.html ----
    def cap(key):
        st = stats[key]
        newp = [p for p in st["palettes"] if p in NEW_PALETTES]
        worst = min(st["contrast"][m][0] for m in MOODS)
        return ("New tiles beyond the font: <b>%d</b>. Palettes: <b>%d</b> (%s), new: %d. Text cells: %d. Fix cells written: %d. "
                "Worst text cell contrast over the three moods: %.0f." %
                (len(st["new_tiles"]), len(st["palettes"]), ", ".join(st["palettes"]), len(newp), st["text_cells"], st["cells"], worst))

    def img(name, w=640, h=448):
        return '<img src="%s" width="%d" height="%d" alt="%s">' % (name, w, h, name)

    H = []
    H.append("""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Gumbirds: round clear banner drafts</title>
<style>
body { background: #1b1c20; color: #d6d7dc; font-family: Helvetica, Arial, sans-serif; margin: 24px; line-height: 1.45; }
h1 { font-size: 22px; margin: 0 0 6px; } h2 { font-size: 17px; margin: 34px 0 6px; color: #ffffff; }
p { margin: 4px 0 10px; max-width: 1300px; } .num { color: #a9abb6; font-size: 14px; }
img { image-rendering: pixelated; display: block; border: 1px solid #3a3c44; background: #000; }
.row { display: flex; flex-wrap: wrap; gap: 14px; margin: 8px 0 4px; } .cell { font-size: 13px; color: #a9abb6; }
.pick { border-left: 4px solid #ff52b5; padding-left: 12px; }
</style></head><body>
<h1>Gumbirds: round clear banner drafts</h1>
<p>Shown while play is frozen for 2 seconds (120 frames) after a round ends. Fix layer only, Gumdrop font, 320 x 224 at 2x.
Backdrops are the HUD mock-ups (not MAME screenshots). Numbers: numbers.txt in this folder.</p>
""")
    for key, (title, desc, _) in variants.items():
        H.append('<h2>%s</h2><p>%s</p>' % (title, desc))
        H.append('<div class="row">')
        if key == "d":
            H.append('<div class="cell">%sanimated, moon</div>' % img("variant_d_anim_moon_1x.gif"))
            H.append('<div class="cell">%slast frame, moon</div>' % img("variant_d_moon_1x.png"))
        elif key == "a":
            H.append('<div class="cell">%smoon</div>' % img("variant_a_moon_1x.png"))
            H.append('<div class="cell">%sdusk (the weak case)</div>' % img("variant_a_dusk_1x.png"))
        else:
            H.append('<div class="cell">%smoon</div>' % img("variant_%s_moon_1x.png" % key))
            H.append('<div class="cell">%sstorm</div>' % img("variant_%s_storm_1x.png" % key))
        H.append('</div><p class="num">%s</p>' % cap(key))
        if key == "d":
            H.append('<div class="row"><div class="cell">%sthe four stages of one letter cell (8x): bubble, pop burst (the one new tile), white flash, pink</div></div>'
                     % img("variant_d_stages_8x.png", 336, 96))
    H.append('<h2 class="pick">Recommended: D on all three sky moods</h2>')
    H.append('<p>Animated (top) and last frame (bottom). Moon, dusk, storm.</p><div class="row">')
    for m in MOODS:
        H.append('<div class="cell">%s%s, animated</div>' % (img("variant_d_anim_%s_1x.gif" % m), m))
    H.append('</div><div class="row">')
    for m in MOODS:
        H.append('<div class="cell">%s%s, last frame</div>' % (img("variant_d_%s_1x.png" % m), m))
    H.append('</div>')
    H.append('<h2>Runner-up B on all three sky moods</h2><div class="row">')
    for m in MOODS:
        H.append('<div class="cell">%s%s</div>' % (img("variant_b_%s_1x.png" % m), m))
    H.append('</div>')
    H.append('<h2>A with the backdrop at half brightness</h2><p>Plain text reads only if the arena is dimmed. '
             'That is a fade of every sprite palette (code cost), not a fix layer effect.</p><div class="row">')
    for m in MOODS:
        H.append('<div class="cell">%s%s</div>' % (img("variant_a_dark_%s_1x.png" % m), m))
    H.append('</div>')
    H.append('<h2>New tiles (8x)</h2><p>All %d new 8 x 8 tiles of the four variants: band edges at four heights, drip pieces, pop burst. '
             'Grey = transparent.</p><div class="row"><div class="cell">%s</div></div>' %
             (len(NEW_TILES), img("new_tiles_8x.png", (len(NEW_TILES) * 9 + 1) * 8, 80)))
    H.append("</body></html>\n")
    open(os.path.join(HERE, "index.html"), "w").write("\n".join(H))
    print(open(os.path.join(HERE, "numbers.txt")).read())


if __name__ == "__main__":
    main()
