#!/opt/homebrew/bin/python3.14 -I
"""Gum-carrying versions of the approved ground clips: walk C (8 frames), landing (2), idle breathing (4),
for both gum states the sheet uses on the ground (two bubbles = flap2 frame 0, one bubble = flap1 frame 0),
player and rival palette. 24 x 32 per frame.

Reuses draw_walk.py unchanged (compose_walk, the walk C / landing / breathing specs, render, GIF helpers,
tile counter) and sheet_base.py (GUM grids, line()). The gumless output of draw_walk.py is not touched.

The bubble is not pasted: per frame it gets its own lift (lags the body by one frame), a horizontal drift
(trails the walk by 1 px, sways with the steps), a 1-row squash (one frame after a touchdown) and, for the
pair, a 1-row tilt between the two lobes. Squash = the sheet's own trick: drop the middle row and repeat
one column (the sheet's "lobe" is exactly "one" with its middle row dropped). All pixels are sheet letters,
so palette indices, shading clusters and outline are the sheet's own.

String and knot are drawn the way sheet_base.compose draws them: string core "n" with "k" sides under the
gum, gum over it, body over both, knot "n" + tail "m" at the brow's right outline pixel. No gum wad at the
beak while gum is carried (the flap frames carry none either).

Run: /opt/homebrew/bin/python3.14 -I draw_walk_gum.py   (writes only into this directory)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sheet_base as sb  # noqa: E402
import draw_walk as dw  # noqa: E402
from PIL import Image  # noqa: E402

FW, FH = sb.FW, sb.FH
LOBE = sb.GUM["lobe"][0]   # 9 x 9, one lobe of the pair
ONE = sb.GUM["one"][0]     # 9 x 10, the single bubble
STATES = {  # name: (sheet clip, base x, base y) base = position in flap frame 0 of that clip
    "gum2": ("flap2", 3, 1),
    "gum1": ("flap1", 7, 1),
}


# ------------------------------------------------------------------ bubble grids
def squash(g, widen=True):
    """1 row shorter (drop the middle row) and, for the single bubble, 1 column wider (repeat column 4).
    The pair only loses the row: widened lobes read as a bow tie."""
    rows = [r for i, r in enumerate(g) if i != len(g) // 2]
    return [r[:5] + r[4:] for r in rows] if widen else rows


def pair(lobe, tilt):
    """two lobes, right one tilt rows lower; seam rows inside both outlines open up as in the sheet's 'two'"""
    w, h = len(lobe[0]), len(lobe)
    top = min(0, tilt)
    H = h + abs(tilt)
    grid = [["."] * (2 * w - 1) for _ in range(H)]
    ly, ry = -top, tilt - top
    for oy, ox in ((ly, 0), (ry, w - 1)):
        for y, r in enumerate(lobe):
            for x, ch in enumerate(r):
                if ch != ".":
                    grid[oy + y][ox + x] = ch

    def edge_k(oy, col, y):
        r = y - oy
        return 0 <= r < h and lobe[r][col] == "k"

    seam = w - 1
    for y in range(H):
        if all(edge_k(ly, w - 1, yy) and edge_k(ry, 0, yy) for yy in (y - 1, y, y + 1)):
            grid[y][seam] = "m"
    anchor = (seam, max(ly, ry) + h - 2)  # sheet: (8, 7) in 'two'
    return ["".join(r) for r in grid], anchor


assert pair(LOBE, 0)[0] == sb.GUM["two"][0] and pair(LOBE, 0)[1] == (8, 7), "pair() must rebuild 'two'"


def bubble(state, sq, tilt):
    """returns grid, string anchor (relative), bottom row offset so the bottom outline stays put"""
    if state == "gum2":
        g, a = pair(squash(LOBE, widen=False) if sq else LOBE, tilt)
        return g, a, len(g) - len(sb.GUM["two"][0]) - abs(tilt)
    g = squash(ONE) if sq else ONE
    return g, ((len(g[0]) - 1) // 2, len(g) - 1), len(g) - len(ONE)


# ------------------------------------------------------------------ compose
def compose_gum(state, walk, glift=0, gdx=0, sq=False, tilt=0, bend=0):
    """walk = a draw_walk spec. glift > 0 lifts the bubble's bottom, gdx moves it right."""
    px, info = dw.compose_walk(**dict(walk, wad=0))
    _, gx, gy = STATES[state]
    g, (ax, ay), dh = bubble(state, sq, tilt)
    gx += gdx
    gy = gy - glift - dh   # keep the bottom outline row where the unsquashed bubble has it
    # a tilt never raises a lobe: pair() keeps the higher lobe at the grid top and dips the other
    # knot: the brow's right outline pixel, as in the sheet (col 18, body row 3 on the rest body)
    grid, bx0 = dw.BODIES[walk.get("body", "rest")][:2]
    L, dx = walk.get("L", 0), walk.get("dx", 0)
    top = 29 - L - len(grid) + 1
    knot = (bx0 + dx + grid[3].rindex("k"), top + 3)
    lay, clipped = {}, []

    def dot(x, y, ch, over=True):
        if ch in ". ":
            return
        if not (0 <= x < FW and 0 <= y < FH):
            clipped.append((x, y, ch))
            return
        if over or (x, y) not in lay:
            lay[(x, y)] = ch

    s = (gx + ax, gy + ay)
    mid = (s[0] + (knot[0] - s[0]) // 3 + bend, s[1] + max(1, (knot[1] - s[1]) // 2))
    core = []
    for a, b in zip([s, mid], [mid, knot]):
        core += sb.line(a, b)
    for x, y in core:
        dot(x - 1, y, "k", over=False)
        dot(x + 1, y, "k", over=False)
    for x, y in core:
        dot(x, y, "n")
    gum_px = set()
    for y, row in enumerate(g):
        for x, ch in enumerate(row):
            dot(gx + x, gy + y, ch)
            if ch != ".":
                gum_px.add((gx + x, gy + y))
    out = dict(lay)
    covered = [p for p in gum_px if p in px]
    out.update(px)            # body, tuft, beak, wing, legs over string and gum
    out[knot] = "n"
    out[(knot[0] + 1, knot[1] + 1)] = "m"
    info = dict(info)
    info["clipped"] = info["clipped"] + clipped
    info["gum_box"] = (gx, gy, gx + len(g[0]) - 1, gy + len(g) - 1)
    info["gum_covered"] = covered
    info["knot"] = knot
    return out, info


# ------------------------------------------------------------------ clips
WALK_HOLDS, WALK_SPECS = dw.variant_c()
LAND_SPECS = dw.LAND[1]
BREATHE_SPECS = dw.BREATHE[1]
HOLDS = {"walk_C": [3] * 8, "land": [9, 12], "breathe": [36, 15, 21, 15]}

# Walk C body: f0 squash contact L0, f1 stretch push L1 dx1, f2 air L2 dx1, f3 descend L1, same for f4..7.
# Bubble one frame behind: still sinking at contact, lowest and squashed the frame after (string snaps
# taut), rising while the body is up, highest one frame after the body's peak. Trails the walk by 1 px,
# catches up one frame after the body's forward lean; the pair rocks one row per step (left / right foot).
WALK_GUM = dict(
    glift={"gum2": [0, -1, 0, 1] * 2, "gum1": [0, 0, 0, 1] * 2},  # single bubble hangs lower: no dip into the tuft
    sq=[False, True, False, False] * 2,
    gdx=[-1, -1, 0, 0] * 2,
    tilt={"gum2": [0, 0, 1, 1, 0, 0, -1, -1], "gum1": [0] * 8},
    sway={"gum2": [0] * 8, "gum1": [0, 0, 1, 0, 0, 0, -1, 0]},
    bend=[1, 0, 0, -1] * 2,
)
# Landing: f0 body squashes on contact, bubble still at flight height (string slack, bows);
# f1 body recovers, bubble arrives one frame late: dips one row and squashes.
LAND_GUM = dict(glift={"gum2": [1, -1], "gum1": [1, -1]}, sq=[False, True], gdx=[0, 0], tilt={"gum2": [0, 0], "gum1": [0, 0]},
                sway={"gum2": [0, 0], "gum1": [0, 0]}, bend=[1, 0])
# Breathing: body rises on f1, f2 and settles on f3, f0; the bubble follows one frame later.
BREATHE_GUM = dict(glift={"gum2": [0, 0, 1, 1], "gum1": [0, 0, 1, 1]}, sq=[False] * 4, gdx=[0, 0, 0, 0],
                   tilt={"gum2": [0, 0, 0, 0], "gum1": [0, 0, 0, 0]}, sway={"gum2": [0] * 4, "gum1": [0] * 4},
                   bend=[0, 0, 0, 1])
CLIPS = [("walk_C", "walk C hop-walk", WALK_SPECS, WALK_GUM),
         ("land", "landing pair", LAND_SPECS, LAND_GUM),
         ("breathe", "idle breathing loop", BREATHE_SPECS, BREATHE_GUM)]


def frames_for(state, specs, gm):
    out = []
    for i, w in enumerate(specs):
        out.append(compose_gum(state, w, glift=gm["glift"][state][i], gdx=gm["gdx"][i] + gm["sway"][state][i],
                               sq=gm["sq"][i], tilt=gm["tilt"][state][i], bend=gm["bend"][i]))
    return out


def rest_check():
    """at rest (idle pose, no offsets) the bubble, string and knot must land where flap frame 0 has them"""
    sheet = Image.open(dw.SHEET_PNG).convert("RGBA")
    res = []
    for state, (clip, _, _) in STATES.items():
        fi = sb.FIRST[[c for c, _ in sb.CLIPS].index(clip)]
        r = sb.META["animations"]["player"][fi]
        ref = sheet.crop((r["x"], r["y"], r["x"] + FW, r["y"] + FH))
        px, _ = compose_gum(state, dict(dw.IDLE_SPEC))
        mine = dw.render(px, "player")
        n = 8 if state == "gum2" else 10  # rows above the string's start
        same = sum(1 for y in range(n) for x in range(FW) if mine.getpixel((x, y)) == ref.getpixel((x, y)))
        res.append("  %s: rows 0..%d (bubble, above the string) match sheet frame %d (%s frame 0): %d of %d pixels"
                   " (the string below differs by design: flap frame 0 uses the 1-row squashed flight body)" % (
                       state, n - 1, fi, clip, same, n * FW))
    return res


# ------------------------------------------------------------------ main
def main():
    sheet = Image.open(dw.SHEET_PNG).convert("RGBA")
    old_frames = [sheet.crop((r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"]))
                  for r in sb.META["animations"]["player"]]
    old16 = set().union(*[dw.tiles_of(f, 16, (32, 32)) for f in old_frames])
    old8 = set().union(*[dw.tiles_of(f, 8) for f in old_frames])
    gumless16, gumless8 = set(), set()
    for specs in (WALK_SPECS, LAND_SPECS, BREATHE_SPECS):
        for s in specs:
            im = dw.render(dw.compose_walk(**s)[0], "player")
            gumless16 |= dw.tiles_of(im, 16, (32, 32))
            gumless8 |= dw.tiles_of(im, 8)
    base16, base8 = old16 | gumless16, old8 | gumless8

    L = ["Sootling ground clips WITH GUM, measured by draw_walk_gum.py. Frame 24 x 32, col 0 left, row 0 top.", ""]
    L += GUM_FACTS + [""]
    L.append("Rest check (idle pose, bubble offsets 0):")
    L += rest_check()
    L.append("")
    L.append("Tile method (same as measure.txt): render each frame with the player palette, pad it to 32 x 32 at x 0,"
             " cut 16 x 16 tiles,")
    L.append("drop empty tiles, compare raw RGBA bytes (no flip matching, as measure.txt). 'new' = not in the current"
             " sheet's 63 player frames")
    L.append("and not in the approved gumless walk C / landing / breathing drafts. The rival reuses the player tiles"
             " (palette swap). 8 x 8 counts beside them.")
    L.append("")
    rows, all16, all8, gallery = [], set(), set(), []
    for state in STATES:
        st16, st8 = set(), set()
        for name, desc, specs, gm in CLIPS:
            frames = frames_for(state, specs, gm)
            holds = HOLDS[name]
            L.append("%s %s (%s): %d frames, holds %s game frames (cycle %d ticks = %.3f s)" % (
                name, state, desc, len(frames), " ".join(map(str, holds)), sum(holds), sum(holds) / 60))
            t16, t8 = set(), set()
            for i, (px, info) in enumerate(frames):
                im = dw.render(px, "player")
                t16 |= dw.tiles_of(im, 16, (32, 32))
                t8 |= dw.tiles_of(im, 8)
                flags = []
                if info["clipped"]:
                    flags.append("CLIPPED %d px" % len(info["clipped"]))
                gb = info["gum_box"]
                if gb[1] < 0:
                    flags.append("BUBBLE ABOVE FRAME")
                if gb[1] == 0:
                    flags.append("bubble touches row 0")
                L.append("  frame %d: bubble box cols %d..%d rows %d..%d, %d bubble px under the body/tuft, "
                         "knot (%d, %d), feet row %d%s" % (
                             i, gb[0], gb[2], gb[1], gb[3], len(info["gum_covered"]), info["knot"][0],
                             info["knot"][1], info["feet_bottom"], ("  " + "; ".join(flags)) if flags else ""))
            L.append("  tiles 16x16: %d unique, %d new (%d not in the sheet alone); 8x8: %d unique, %d new" % (
                len(t16), len(t16 - base16), len(t16 - old16), len(t8), len(t8 - base8)))
            L.append("")
            st16 |= t16
            st8 |= t8
            for who, tag in (("player", "player"), ("cpu", "rival")):
                s = dw.strip(frames, who)
                s.save(os.path.join(HERE, "gum_%s_%s_%s.png" % (name, state, tag)))
                rows.append(s)
            dw.inplace_gif(frames, holds, os.path.join(HERE, "gum_%s_%s_4x.gif" % (name, state)),
                           loop=(name != "land"))
            if name == "walk_C":
                dw.move_gif(frames, holds, os.path.join(HERE, "gum_%s_%s_move_4x.gif" % (name, state)), 3)
        L.append("%s total over walk C + landing + breathing: 16x16 %d unique, %d new; 8x8 %d unique, %d new" % (
            state, len(st16), len(st16 - base16), len(st8), len(st8 - base8)))
        L.append("")
        all16 |= st16
        all8 |= st8
    L.append("ALL gum clips, both states, deduplicated together: 16x16 %d unique, %d new C-ROM tiles; "
             "8x8 %d unique, %d new" % (len(all16), len(all16 - base16), len(all8), len(all8 - base8)))
    L.append("(pools: sheet 16x16 %d, gumless drafts 16x16 %d, union %d)" % (len(old16), len(gumless16), len(base16)))
    w = max(r.width for r in rows)
    comb = Image.new("RGBA", (w, FH * len(rows)), (0, 0, 0, 0))
    for i, r in enumerate(rows):
        comb.alpha_composite(r, (0, i * FH))
    comb.save(os.path.join(HERE, "walk_gum_sheet_draft.png"))
    L.append("")
    L.append("walk_gum_sheet_draft.png: %d x %d, rows top to bottom (player, rival per clip): walk C two bubbles,"
             " landing two, breathing two, walk C one bubble, landing one, breathing one" % comb.size)
    open(os.path.join(HERE, "measure_gum.txt"), "w").write("\n".join(L) + "\n")
    print("\n".join(l for l in L if "tiles" in l or "total" in l or "ALL" in l or "CLIP" in l or "ABOVE" in l
                    or "match" in l))


GUM_FACTS = [
    "How the sheet draws gum (assets/flier/sootling_sheet.json + sheet_base.py, which rebuilds all 63 frames",
    "pixel-exact; checked):",
    "  Frame 24 x 32, 7 clips: flap2 (0..7, gum 'two'), flap1 (8..15, gum 'one'), pop2 (16..27, two -> one),",
    "  pop1 (28..37, one -> none), inflate (38..51, none -> two), fall (52..61, none, loose string), idle (62, none,",
    "  gum wad at the beak). Gum states: 2 bubbles, 1 bubble, 0 (no bubble; idle carries the beak wad instead).",
    "  Two bubbles: 17 x 9 joined pair (two 9 x 9 lobes sharing outline col 8, seam open on rows 3..5),",
    "    at x 3..19, y 1..9 in flap2 frame 0; string from (11, 8) to the knot.",
    "  One bubble: 9 x 10 at x 7..15, y 1..10 in flap1 frame 0; string from (11, 10) to the knot.",
    "  Knot: 'n' on the brow's right outline pixel (col 18, body row 3) plus an 'm' tail one down-right.",
    "  String: 'n' core, 'k' sides, 2 segments with a bend; bubble drawn over the string, body over both.",
    "  Gum letters: k outline, h / w highlight, n light, m mid, q dark, p deepest (palette 0, 13, 14, 12, 11, 10, 9",
    "  in the player palette, rival same indices). In flight the bubble lifts 0..1 row (glift), x fixed.",
    "  No wad at the beak while gum is carried (flap frames have none).",
    "src/core/flier_view.c steady_clip(): balloons == 0 -> idle, 1 -> flap1, 2 -> flap2; flier_anim_step()",
    "  holds frame 0 of flap1 / flap2 while f->on_ground. So on the ground today: two bubbles = sheet frame 0,",
    "  one bubble = sheet frame 8, none = frame 62. Gum clips are needed for 2 and 1 bubbles (gum2, gum1);",
    "  0 bubbles uses the approved gumless drafts.",
]

if __name__ == "__main__":
    main()
