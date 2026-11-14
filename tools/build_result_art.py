#!/usr/bin/env python3
"""Bonus result screen art (look C, owner pick 2026-11-14): everything is painted here, there is no source sheet.
Usage: python3.14 -I tools/build_result_art.py [--out build/gen]

Outputs in --out:
  result_scene.fix / result_scene.h   the still scene on the fix layer: gum machine, bubble cage, pipe, shelf, ticket slot and the
                                      striped night sky. 40x28 cell map, one fix palette per cell (assets/result/result_palettes.json).
                                      Cells left transparent are the windows the sprites show through (the fix layer is above sprites).
  result_paths.h                      baked bubble physics: one path per bubble from the pipe mouth into the pile (src/core/result.c).
  resfx.c1/.c2, resfx_sprites.c/.h    the moving parts as sprites (through tools/sprite_pipeline.py): bubble and its pop, counter
                                      wheels, crank, cage glass, ticket with its tray.
  result_preview.png                  scene and sprites composed (first frame), for the draft page only.

The S-ROM tile base of the scene is not known here: result_scene.h takes it from gen/attract_icons.h (the scene follows the icons).
"""
import json, math, os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image
import sprite_pipeline
import build_attract_icons as icons  # pack_fix

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H, COLS, ROWS = 320, 224, 40, 28
SKY0, SKY1, SKY2, METAL, BODY = range(5)
BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0

# Screen geometry shared with src/core/result_view.h (written into result_scene.h).
CAGE = (24, 48, 96, 80)       # cage window: x, y, w, h
WHEEL = (208, 72)             # first counter wheel; 5 wheels, 16 px apart, 16 px tall window
CRANK = (264, 96)             # crank window 32x32
TICKET = (64, 168, 192, 40)   # ticket window
# Windows in cells (col0, row0, col1, row1): only these may hold transparent pixels.
WINDOWS = [(3, 6, 14, 15), (26, 9, 35, 10), (33, 12, 36, 15), (8, 21, 31, 25)]

px = np.zeros((H, W), np.uint8)
cellpal = np.zeros((ROWS, COLS), np.uint8)


def region(pal, c0, r0, c1, r1):
    cellpal[r0:r1 + 1, c0:c1 + 1] = pal
    px[r0 * 8:r1 * 8 + 8, c0 * 8:c1 * 8 + 8] = 1


def fill(pal, x0, y0, x1, y1, v):
    """Inclusive pixel box; v = palette index, or f(xx, yy) -> index array. Dies when the box leaves the cells of pal."""
    if not (cellpal[y0 // 8:y1 // 8 + 1, x0 // 8:x1 // 8 + 1] == pal).all():
        sprite_pipeline.die("paint box %d,%d..%d,%d leaves palette %d" % (x0, y0, x1, y1, pal))
    if callable(v):
        yy, xx = np.mgrid[y0:y1 + 1, x0:x1 + 1]
        v = v(xx, yy)
    px[y0:y1 + 1, x0:x1 + 1] = v


def dots(pal, pts, v):
    for x, y in pts:
        fill(pal, x, y, x, y, v)


def hbar(pal, x0, y0, x1, ramp):
    """Horizontal bar: one palette index per row, top to bottom."""
    for i, v in enumerate(ramp):
        fill(pal, x0, y0 + i, x1, y0 + i, v)


def vbar(pal, x0, y0, y1, ramp):
    for i, v in enumerate(ramp):
        fill(pal, x0 + i, y0, x0 + i, y1, v)


def dither(colours, level):
    """level (float array, 0..len-1) -> palette indexes, ordered dither only in the half step around each change."""
    def f(xx, yy):
        l = np.clip(level(xx, yy), 0, len(colours) - 1)
        t = BAYER[yy & 3, xx & 3]
        i = np.floor(l + (t - 0.5) * 0.7 + 0.5).astype(int)
        return np.array(colours, np.uint8)[np.clip(i, 0, len(colours) - 1)]
    return f


def rivet(pal, x, y, hi, lo):
    dots(pal, [(x, y), (x + 1, y)], hi)
    dots(pal, [(x, y + 1), (x + 1, y + 1)], lo)
    dots(pal, [(x, y)], hi)


def paint_scene():
    yy, xx = np.mgrid[0:H, 0:W]
    # ---- night sky: diagonal stripes, 12 colours over 24 px; the half-pixel offset d breaks the stair edge into a hand-dither.
    cellpal[0:9] = SKY0
    cellpal[9:19] = SKY1
    cellpal[19:28] = SKY2
    d = (xx ^ (yy >> 1)) & 1
    px[:] = 1 + ((((xx + yy) % 24) + d) // 2) % 12
    # Stars, placed by hand in the open sky (x, y, kind): 0 dim dot, 1 mid dot, 2 bright dot, 3 small cross, 4 big cross.
    stars = [(12, 9, 3), (31, 21, 0), (52, 6, 1), (77, 13, 4), (92, 27, 0), (61, 30, 2), (241, 7, 1), (268, 19, 3), (289, 5, 0),
             (305, 28, 4), (226, 29, 0), (252, 33, 2), (22, 35, 1), (8, 61, 0), (5, 92, 3), (11, 121, 1), (9, 147, 0), (311, 52, 1),
             (314, 83, 0), (309, 110, 4), (315, 131, 2), (140, 41, 0), (163, 43, 3), (181, 37, 1), (150, 70, 2), (173, 77, 0),
             (136, 93, 4), (160, 104, 1), (185, 96, 0), (147, 121, 3), (176, 125, 2), (26, 150, 1), (71, 148, 0), (133, 150, 2),
             (214, 149, 0), (287, 148, 3), (13, 163, 0), (36, 171, 4), (21, 190, 1), (44, 201, 0), (15, 211, 2), (280, 166, 1),
             (301, 177, 4), (273, 192, 0), (294, 204, 3), (312, 216, 1), (60, 219, 0), (118, 220, 2), (187, 219, 1), (241, 220, 0)]
    star_px = []
    for x, y, k in stars:
        if k < 3:
            star_px.append((x, y, 13 + k))
        else:
            arm = 14 if k == 3 else 15
            star_px.append((x, y, 15))
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                star_px.append((x + dx, y + dy, arm - 1 if k == 3 else 14))
            if k == 4:
                for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2)):
                    star_px.append((x + dx, y + dy, 13))

    # ---- bubble cage: steel frame cols 2..15 rows 5..16 around the window
    region(METAL, 2, 5, 15, 16)
    hbar(METAL, 16, 40, 127, [1, 7, 6, 5, 4, 3, 2, 1])                       # top beam
    for x0 in (16, 120):                                                     # side posts
        vbar(METAL, x0, 48, 127, [1, 3, 5, 6, 5, 4, 2, 1])
    hbar(METAL, 16, 128, 127, [1, 6, 5, 4, 3, 3, 2, 1])                      # plinth
    for x in range(22, 124, 12):                                             # plinth grooves: dark cut, light lip
        fill(METAL, x, 130, x, 133, 2)
        fill(METAL, x + 1, 130, x + 1, 133, 6)
    for x in (16, 127):
        fill(METAL, x, 40, x, 135, 1)
    # beam: a worn sheen, clusters set by hand
    for x0, x1, y in ((30, 47, 42), (33, 41, 43), (70, 78, 42), (96, 109, 42), (99, 104, 43)):
        fill(METAL, x0, y, x1, y, 7)
    for x0, x1, y in ((52, 60, 45), (84, 92, 45), (112, 118, 44)):
        fill(METAL, x0, y, x1, y, 13)
    dots(METAL, [(17, 41), (126, 41), (17, 134), (126, 134)], 13)            # softened corners
    for x in (19, 123):
        for y in (43, 66, 90, 114, 131):
            rivet(METAL, x, y, 15, 1)
    # window: transparent, thin bars, inner shadow, a glint on the glass
    cx, cy, cw, ch = CAGE
    fill(METAL, cx, cy, cx + cw - 1, cy + ch - 1, 0)
    for k in range(6):
        fill(METAL, cx + 7 + 16 * k, cy, cx + 7 + 16 * k, cy + ch - 1, 5)
        fill(METAL, cx + 8 + 16 * k, cy, cx + 8 + 16 * k, cy + ch - 1, 3)
    for x in range(cx, cx + cw):
        if (x & 1) == 0: px[cy, x] = 1
        if (x & 3) == 1: px[cy + 1, x] = 1
    for y in range(cy, cy + ch):
        if (y & 1) == 0: px[y, cx] = 1
    for x in range(28, 37):
        px[84 - x, x] = 7
    for x in range(31, 36):
        px[89 - x, x] = 6
    for x in range(100, 104):
        px[222 - x, x] = 6
    # pipe port in the right post
    hbar(METAL, 120, 48, 127, [1, 10, 12, 12, 11, 10, 10, 9, 9, 9, 8, 8, 8, 8, 9, 1])
    vbar(METAL, 120, 48, 63, [1, 4])
    fill(METAL, 127, 48, 127, 63, 1)

    # ---- pipe: teal tube cols 16..23 rows 6..7, steel flanges
    region(METAL, 16, 6, 23, 7)
    hbar(METAL, 128, 48, 191, [1, 9, 11, 12, 12, 11, 10, 10, 10, 9, 9, 9, 8, 8, 9, 1])
    for x in range(128, 192):                                                # hand-dither between the bands
        if (x & 1): px[53, x] = 12
        if (x & 3) == 2: px[56, x] = 11
        if (x & 1) == 0: px[59, x] = 10
        if (x & 3) == 0: px[61, x] = 9
    for x0, x1 in ((135, 152), (166, 173), (178, 181)):                      # specular streak
        fill(METAL, x0, 51, x1, 51, 7)
    for x0, x1 in ((137, 147), (168, 171)):
        fill(METAL, x0, 50, x1, 50, 12)
    for x0 in (128, 158, 188):                                               # flanges
        hbar(METAL, x0, 48, x0 + 3, [1, 6, 7, 6, 5, 5, 4, 4, 4, 3, 3, 3, 2, 2, 2, 1])
        fill(METAL, x0, 48, x0, 63, 1)
        fill(METAL, x0 + 3, 49, x0 + 3, 62, 2)
        dots(METAL, [(x0 + 1, 52), (x0 + 1, 59)], 15)

    # ---- gum machine cols 24..37 rows 5..16
    region(BODY, 24, 5, 37, 16)
    hbar(BODY, 192, 40, 303, [1, 13, 12, 11, 10, 9, 8, 1])                   # brass cap
    for x0, x1, y in ((204, 226, 41), (208, 219, 42), (250, 262, 41), (280, 291, 41)):
        fill(BODY, x0, y, x1, y, 13 if y == 41 else 12)
    for x0 in (192, 296):                                                    # brass side trims
        vbar(BODY, x0, 48, 127, [1, 10, 12, 11, 10, 9, 8, 1])
    # crimson face: light from the upper left, dark toward the foot, two soft sheen bands across
    def face(xx, yy):
        u, v = (xx - 200) / 95.0, (yy - 48) / 79.0
        band = np.exp(-((u - v * 0.6 - 0.18) * 7.0) ** 2) * 0.9 + np.exp(-((u - v * 0.6 - 0.55) * 11.0) ** 2) * 0.5
        return 2.3 - 1.9 * v - 0.5 * u + band
    fill(BODY, 200, 48, 295, 127, dither([2, 3, 4, 5, 6], face))
    for x, y in ((213, 50), (214, 50), (215, 50), (212, 51), (213, 51), (211, 52), (236, 99), (237, 99), (235, 100)):
        px[y, x] = 7                                                         # sheen sparks
    # pipe port in the left trim
    hbar(BODY, 192, 48, 199, [1, 12, 13, 12, 11, 10, 10, 9, 9, 9, 8, 8, 8, 9, 10, 1])
    fill(BODY, 192, 48, 192, 63, 1)
    fill(BODY, 199, 48, 199, 63, 8)
    # counter bezel rows 8..11 cols 25..36, window cols 26..35 rows 9..10
    hbar(BODY, 200, 64, 295, [1, 13, 12, 11, 10, 9, 8, 1])
    hbar(BODY, 200, 88, 295, [1, 8, 9, 10, 11, 10, 9, 1])
    vbar(BODY, 200, 72, 87, [1, 12, 11, 10, 9, 8, 8, 1])
    vbar(BODY, 288, 72, 87, [1, 8, 9, 10, 11, 12, 10, 1])
    for x in (200, 295):
        fill(BODY, x, 64, x, 95, 1)
    for x, y in ((203, 67), (291, 67), (203, 91), (291, 91)):
        rivet(BODY, x, y, 13, 8)
    wx, wy = WHEEL
    fill(BODY, wx, wy, wx + 79, wy + 15, 0)
    fill(BODY, wx, wy, wx + 79, wy, 14)                                      # wheel shadow under the bezel, top and bottom
    fill(BODY, wx, wy + 15, wx + 79, wy + 15, 14)
    for x in range(wx, wx + 80):
        if (x & 1) == 0: px[wy + 1, x] = 14
        if (x & 1): px[wy + 14, x] = 14
    for k in range(5):
        fill(BODY, wx + 16 * k, wy, wx + 16 * k, wy + 15, 1)
    # vents rows 14..15 cols 25..31
    for y in (113, 117, 121):
        fill(BODY, 204, y, 251, y, 1)
        fill(BODY, 204, y + 1, 251, y + 1, 14)
        fill(BODY, 205, y + 2, 251, y + 2, 6)
        dots(BODY, [(203, y), (252, y + 1)], 2)
    # crank window cols 33..36 rows 12..15 (the crank sprite fills it)
    fill(BODY, CRANK[0], CRANK[1], CRANK[0] + 31, CRANK[1] + 31, 0)
    fill(BODY, 263, 96, 263, 127, 1)
    # foot
    hbar(BODY, 192, 128, 303, [1, 10, 11, 10, 9, 8, 14, 1])
    for x0 in (196, 286):
        fill(BODY, x0, 132, x0 + 13, 134, 14)
        fill(BODY, x0, 131, x0 + 13, 131, 15)
    for x in (192, 303):
        fill(BODY, x, 40, x, 135, 1)
    for x in (195, 299):
        for y in (70, 100, 122):
            rivet(BODY, x, y, 13, 8)

    # ---- shelf row 17 cols 1..38
    region(BODY, 1, 17, 38, 17)
    hbar(BODY, 8, 136, 311, [1, 12, 11, 10, 10, 9, 8, 1])
    for x in (8, 311):
        fill(BODY, x, 136, x, 143, 1)
    for x0, x1 in ((20, 58), (96, 110), (150, 201), (236, 249), (270, 300)):  # worn light on the edge
        fill(BODY, x0, 137, x1, 137, 13)
    for x0, x1 in ((40, 71), (120, 133), (180, 222), (260, 281)):             # grain
        fill(BODY, x0, 140, x1, 140, 9)
    for x in range(12, 308, 37):
        rivet(BODY, x, 139, 13, 8)

    # ---- ticket slot: bar row 20, rails cols 7 and 32, lip row 26, window cols 8..31 rows 21..25
    region(METAL, 7, 20, 32, 20)
    hbar(METAL, 56, 160, 263, [1, 6, 5, 4, 3, 2, 1, 1])
    for x0, x1 in ((66, 100), (130, 142), (176, 219), (236, 246)):
        fill(METAL, x0, 161, x1, 161, 7)
    for x in range(61, 262, 28):
        rivet(METAL, x, 162, 15, 1)
    for c, x0 in ((7, 56), (32, 256)):
        region(METAL, c, 21, c, 25)
        vbar(METAL, x0, 168, 207, [1, 3, 5, 6, 4, 3, 2, 1])
    region(METAL, 7, 26, 32, 26)
    hbar(METAL, 56, 208, 263, [1, 2, 4, 5, 6, 4, 2, 1])
    for x0, x1 in ((80, 121), (150, 159), (200, 240)):
        fill(METAL, x0, 212, x1, 212, 7)
    for x in (56, 263):
        fill(METAL, x, 160, x, 215, 1)
    tx, ty, tw, th = TICKET
    px[ty:ty + th, tx:tx + tw] = 0

    for x, y, v in star_px:
        if cellpal[y // 8, x // 8] > SKY2 or px[y, x] == 0:
            sprite_pipeline.die("star at %d,%d is not in the sky" % (x, y))
        px[y, x] = v

    # ---- checks: transparent pixels only inside the windows
    win = np.zeros((ROWS, COLS), bool)
    for c0, r0, c1, r1 in WINDOWS:
        win[r0:r1 + 1, c0:c1 + 1] = True
    for r in range(ROWS):
        for c in range(COLS):
            if (px[r * 8:r * 8 + 8, c * 8:c * 8 + 8] == 0).any() and not win[r, c]:
                sprite_pipeline.die("transparent pixel in cell %d,%d outside the windows" % (c, r))


def write_scene(out, pals):
    tiles, ids, cmap = [], {}, []
    for r in range(ROWS):
        for c in range(COLS):
            t = px[r * 8:r * 8 + 8, c * 8:c * 8 + 8]
            if not t.any():
                cmap.append(None)
                continue
            k = t.tobytes()
            if k not in ids:
                ids[k] = len(tiles)
                tiles.append(t.copy())
            cmap.append((int(cellpal[r, c]), ids[k]))
    n = len(tiles)
    atlas = np.zeros(((n + 15) // 16 * 8, 128), np.uint8)
    for i, t in enumerate(tiles):
        atlas[i // 16 * 8:i // 16 * 8 + 8, i % 16 * 8:i % 16 * 8 + 8] = t
    img = Image.fromarray(atlas, "P")
    img.putpalette(sum(([i * 17] * 3 for i in range(16)), []) + [0] * (240 * 3))
    ap = os.path.join(out, "result_scene_atlas.png")
    img.save(ap)
    icons.pack_fix(ap, n, os.path.join(out, "result_scene.fix"))
    with open(os.path.join(out, "result_scene.h"), "w") as h:
        h.write("/* Generated by tools/build_result_art.py: the still result scene on the fix layer. Do not edit. */\n"
                "#ifndef RESULT_SCENE_H\n#define RESULT_SCENE_H\n#include <stdint.h>\n#include \"gen/fix_font.h\"\n#include \"gen/attract_icons.h\"\n\n"
                "#define RESULT_SCENE_TILES %d\n"
                "#define RESULT_SCENE_BASE (ATTRACT_ICON_FIX_BASE + ATTRACT_ICON_TILES) /* S-ROM order: font, attract icons, this scene */\n"
                "/* Windows the sprites show through, in pixels. */\n"
                "#define RESULT_CAGE_X %d\n#define RESULT_CAGE_Y %d\n#define RESULT_WHEEL_X %d\n#define RESULT_WHEEL_Y %d\n"
                "#define RESULT_CRANK_X %d\n#define RESULT_CRANK_Y %d\n#define RESULT_TICKET_X %d\n#define RESULT_TICKET_Y %d\n"
                "#define RESULT_TICKET_H %d\n\n" % (n, CAGE[0], CAGE[1], WHEEL[0], WHEEL[1], CRANK[0], CRANK[1], TICKET[0], TICKET[1], TICKET[3]))
        h.write("#define RS(p, t) (uint16_t)(((FIXFONT_PAL_%s + (p)) << 12) | (RESULT_SCENE_BASE + (t)))\n#define RB FIXFONT_BLANK\n"
                % pals["palette_order"][0].upper())
        h.write("static const uint16_t result_scene_map[%d] = { /* row-major, 40 x 28 */\n" % (COLS * ROWS))
        for r in range(ROWS):
            h.write("    " + ",".join("RB" if v is None else "RS(%d,%d)" % v for v in cmap[r * COLS:(r + 1) * COLS]) + ",\n")
        h.write("};\n#undef RS\n#undef RB\n#endif\n")
    return n


# ------------------------------------------------------------------------------------------------ bubble physics
BUBBLES, RADIUS, GRAVITY, BOUNCE = 20, 7.0, 0.4, 0.4
START0, START_STEP, LAST_FRAME = 22, 4, 181   # the tally starts at frame 183 (tests/host/test_result.c): every bubble rests before
STARTS = [START0 + START_STEP * i for i in range(BUBBLES)]


def simulate(n):
    """n bubbles leave the pipe mouth (right wall, top) one after the other, each with its own speed, fall, bounce off the walls,
    the floor and each other (equal weights), and come to rest. Returns one list of whole-pixel centres per bubble, from its
    first frame to the frame it last moves. 4 substeps per frame, 4 contact passes per substep."""
    cw, ch, D = CAGE[2], CAGE[3], 2 * RADIUS
    x, y = [cw + 8.0] * n, [8.0] * n
    vx, vy = [-(2.9 + 1.5 * ((i * 7) % 10) / 9.0) for i in range(n)], [0.0] * n
    inside, paths, calm = [False] * n, [[] for _ in range(n)], 0
    for t in range(START0, START0 + 400):
        live = [i for i in range(n) if t >= STARTS[i]]
        for s in range(4):
            touch = set()
            for i in live:
                if x[i] <= cw - RADIUS: inside[i] = True
                if inside[i]: vy[i] += GRAVITY * 0.25
                x[i] += vx[i] * 0.25
                y[i] += vy[i] * 0.25
            for _ in range(4):
                for a in live:
                    if not inside[a]: continue                     # still in the pipe: no contact yet
                    for b in live:
                        if b <= a or not inside[b]: continue
                        dx, dy = x[a] - x[b], y[a] - y[b]
                        dist = math.hypot(dx, dy)
                        if not 0 < dist < D: continue
                        nx, ny, push = dx / dist, dy / dist, (D - dist) / 2
                        x[a] += nx * push; y[a] += ny * push
                        x[b] -= nx * push; y[b] -= ny * push
                        vn = (vx[a] - vx[b]) * nx + (vy[a] - vy[b]) * ny
                        if vn < 0:
                            imp = -(1 + (BOUNCE if vn < -0.6 else 0.0)) * vn / 2
                            vx[a] += imp * nx; vy[a] += imp * ny
                            vx[b] -= imp * nx; vy[b] -= imp * ny
                        touch.update((a, b))
                for i in live:
                    if x[i] < RADIUS:
                        x[i] = RADIUS
                        if vx[i] < 0: vx[i] = -vx[i] * BOUNCE if vx[i] < -0.6 else 0.0
                    if inside[i] and x[i] > cw - RADIUS:
                        x[i] = cw - RADIUS
                        if vx[i] > 0: vx[i] = -vx[i] * BOUNCE if vx[i] > 0.6 else 0.0
                    if y[i] > ch - RADIUS:
                        y[i] = ch - RADIUS
                        if vy[i] > 0: vy[i] = -vy[i] * BOUNCE if vy[i] > 0.6 else 0.0
                        touch.add(i)
            for i in touch:                                        # contact drag: the pile comes to rest
                drag = 0.97 if math.hypot(vx[i], vy[i]) > 0.3 else 0.8   # a slow bubble in contact sticks
                vx[i] *= drag
                vy[i] *= drag
        for i in live:
            paths[i].append((int(round(x[i])), int(round(y[i]))))
        calm = calm + 1 if len(live) == n and all(inside) and max(math.hypot(vx[i], vy[i]) for i in live) < 0.2 else 0
        if calm >= 6: break
    else:
        sprite_pipeline.die("%d bubbles never come to rest" % n)
    for i, p in enumerate(paths):
        while len(p) > 1 and p[-2] == p[-1]:
            p.pop()
        if STARTS[i] + len(p) > LAST_FRAME:
            sprite_pipeline.die("%d bubbles: bubble %d rests at frame %d, after %d" % (n, i, STARTS[i] + len(p), LAST_FRAME))
        ex, ey = p[-1]
        if not (RADIUS <= ex <= cw - RADIUS and RADIUS <= ey <= ch - RADIUS):
            sprite_pipeline.die("%d bubbles: bubble %d rests outside the cage" % (n, i))
        for j in range(i):
            if math.hypot(ex - paths[j][-1][0], ey - paths[j][-1][1]) < D - 1.5:
                sprite_pipeline.die("%d bubbles: %d and %d overlap at rest" % (n, i, j))
    return paths


def bake_paths():
    """One run per bubble count: a bubble pushes the ones before it, so a run with fewer bubbles is not a part of the full run."""
    return [simulate(n) for n in range(1, BUBBLES + 1)]


def write_paths(out, runs):
    lens, off, order, flat = [], [], [], []
    for q in runs:
        for p in q:
            lens.append(len(p))
            off.append(len(flat) // 2)
            for x, y in p:
                flat += [x, y]
        order += sorted(range(len(q)), key=lambda i: (q[i][-1][1], i))  # pop the top of the pile first
    if max(lens) > 255 or len(flat) // 2 > 65535 or max(flat) > 255 or min(flat) < 0:
        sprite_pipeline.die("bubble paths do not fit their table types")
    rest = max(STARTS[i] + len(p) for q in runs for i, p in enumerate(q))
    with open(os.path.join(out, "result_paths.h"), "w") as h:
        h.write("/* Generated by tools/build_result_art.py: baked bubble physics for the result cage. Do not edit.\n"
                " * One run per bubble count n (1..RESP_BUBBLES); the tables of run n start at index RESP_RUN(n). Bubble i appears at frame\n"
                " * resp_start[i] and follows resp_len[] points from resp_xy[2 * resp_off[]] (centre, in pixels inside the cage window),\n"
                " * then rests on the last one. resp_order[] = the bubbles of the run from the top of the pile down. */\n"
                "#ifndef RESULT_PATHS_H\n#define RESULT_PATHS_H\n#include <stdint.h>\n"
                "#define RESP_BUBBLES %d\n#define RESP_RADIUS %d\n#define RESP_CAGE_W %d\n#define RESP_CAGE_H %d\n#define RESP_REST_FRAME %d\n"
                "#define RESP_RUN(n) (((n) * ((n) - 1)) >> 1)\n" % (BUBBLES, int(RADIUS), CAGE[2], CAGE[3], rest))
        for name, typ, vals in (("resp_start", "uint8_t", STARTS), ("resp_len", "uint8_t", lens), ("resp_off", "uint16_t", off),
                                ("resp_order", "uint8_t", order), ("resp_xy", "uint8_t", flat)):
            h.write("static const %s %s[%d] = {" % (typ, name, len(vals)))
            for i in range(0, len(vals), 32):
                h.write("\n    " + ",".join(str(v) for v in vals[i:i + 32]) + ",")
            h.write("\n};\n")
        h.write("#endif\n")
    return rest, len(flat)


# ------------------------------------------------------------------------------------------------ sprites
def c5(r, g, b):
    return (sprite_pipeline.expand5(r), sprite_pipeline.expand5(g), sprite_pipeline.expand5(b), 255)


DIGITS = ["01110 10001 10011 10101 11001 10001 01110", "00100 01100 00100 00100 00100 00100 01110",
          "01110 10001 00001 00110 01000 10000 11111", "11110 00001 00001 01110 00001 00001 11110",
          "00010 00110 01010 10010 11111 00010 00010", "11111 10000 11110 00001 00001 10001 01110",
          "00110 01000 10000 11110 10001 10001 01110", "11111 00001 00010 00100 01000 01000 01000",
          "01110 10001 10001 01110 10001 10001 01110", "01110 10001 10001 01111 00001 00010 01100"]


def paint_sprites():
    sheet = np.zeros((240, 256, 4), np.uint8)
    anims = {}

    # ---- bubble 16x16: whole, then 3 pop frames. Light from the upper left, violet shade, peach rim light.
    B = {"o": c5(10, 2, 12), "1": c5(17, 4, 16), "2": c5(23, 7, 18), "3": c5(28, 11, 19), "4": c5(31, 16, 21), "5": c5(31, 21, 24),
         "6": c5(31, 26, 27), "w": c5(31, 31, 31), "r": c5(25, 12, 24)}
    bub = np.zeros((16, 16, 4), np.uint8)
    for y in range(16):
        for x in range(16):
            dx, dy = x - 7.5, y - 7.5
            r = math.hypot(dx, dy)
            if r > 7.3: continue
            if r > 6.2:
                bub[y, x] = B["o"]
                continue
            t = (dx * 0.6 + dy * 0.8) / 6.2          # -1 lit .. 1 shade
            k = "5" if t < -0.55 else "4" if t < -0.1 else "3" if t < 0.35 else "2" if t < 0.72 else "1"
            if r > 4.9 and t > 0.45: k = "r" if r > 5.5 else "2"   # rim light from the glass below
            bub[y, x] = B[k]
    for x, y, k in ((4, 3, "w"), (5, 3, "w"), (3, 4, "w"), (4, 4, "w"), (3, 5, "w"), (6, 3, "6"), (5, 4, "6"), (4, 5, "6"), (3, 6, "6"),
                    (5, 5, "5"), (10, 11, "4"), (11, 10, "4")):
        bub[y, x] = B[k]
    sheet[0:16, 0:16] = bub
    for f, (rad, gap, cols) in enumerate(((7.2, 0.0, "w6"), (7.4, 0.5, "65"), (7.4, 0.8, "43"))):
        fr = np.zeros((16, 16, 4), np.uint8)
        for y in range(16):
            for x in range(16):
                dx, dy = x - 7.5, y - 7.5
                r = math.hypot(dx, dy)
                a = (math.atan2(dy, dx) / (math.pi / 4) + 8.5) % 1.0     # 8 fragments around
                if abs(r - rad) < (1.1 if f == 0 else 0.8) and abs(a - 0.5) > gap / 2:
                    fr[y, x] = B[cols[0] if (x + y) & 1 else cols[1]]
                elif f == 0 and r < 5.5 and (x + y) % 3 == 0:
                    fr[y, x] = B["5"]
                elif f == 1 and 3.0 < r < 5.0 and (x * 3 + y * 5) % 7 == 0:
                    fr[y, x] = B["6"]
        if f == 2:
            for x, y in ((7, 7), (8, 8), (3, 8), (12, 6), (8, 2), (6, 13)):
                fr[y, x] = B["w"]
        sheet[0:16, 16 + 16 * f:32 + 16 * f] = fr
    anims["bubble"] = [{"x": 16 * i, "y": 0, "w": 16, "h": 16} for i in range(4)]

    # ---- counter wheel 16x32: digit k over digit k+1 on an ivory drum
    Wc = {"hi": c5(31, 30, 24), "mid": c5(28, 26, 19), "lo": c5(23, 20, 15), "ink": c5(4, 2, 8), "soft": c5(13, 9, 14), "cut": c5(17, 13, 12)}
    for k in range(10):
        fr = np.zeros((32, 16, 4), np.uint8)
        for half, dgt in ((0, k), (1, (k + 1) % 10)):
            y0 = half * 16
            fr[y0:y0 + 16, :] = Wc["hi"]
            fr[y0:y0 + 16, 0:2] = Wc["mid"]
            fr[y0:y0 + 16, 15] = Wc["mid"]
            fr[y0, :] = Wc["cut"]
            fr[y0 + 15, :] = Wc["lo"]
            fr[y0 + 1, 2:15] = Wc["mid"]
            rows = DIGITS[dgt].split()
            for gy in range(7):
                for gx in range(5):
                    if rows[gy][gx] == "1":
                        fr[y0 + 1 + gy * 2:y0 + 3 + gy * 2, 3 + gx * 2:5 + gx * 2] = Wc["ink"]
            for gy in range(7):                       # soften the stair corners of the doubled glyph
                for gx in range(5):
                    if rows[gy][gx] == "1": continue
                    for ox, oy, cx_, cy_ in ((-1, -1, 0, 0), (1, -1, 1, 0), (-1, 1, 0, 1), (1, 1, 1, 1)):
                        ax, ay = gx + ox, gy + oy
                        if 0 <= ax < 5 and 0 <= ay < 7 and rows[gy][ax] == "1" and rows[ay][gx] == "1":
                            fr[y0 + 1 + gy * 2 + cy_, 3 + gx * 2 + cx_] = Wc["soft"]
        sheet[16:48, 16 * k:16 * k + 16] = fr
    anims["wheel"] = [{"x": 16 * k, "y": 16, "w": 16, "h": 32} for k in range(10)]

    # ---- crank 32x32, 8 turns: dark recess, brass hub, steel arm, red knob
    C = {"o": c5(1, 0, 3), "b0": c5(3, 2, 7), "b1": c5(6, 4, 11), "g0": c5(9, 5, 2), "g1": c5(15, 9, 2), "g2": c5(22, 15, 3),
         "g3": c5(28, 22, 6), "g4": c5(31, 29, 14), "s0": c5(10, 12, 18), "s1": c5(18, 21, 26), "s2": c5(27, 29, 31),
         "k0": c5(13, 2, 7), "k1": c5(25, 7, 7), "k2": c5(31, 18, 14)}
    for k in range(8):
        a = k * math.pi / 4 - math.pi / 2
        ax, ay = math.cos(a), math.sin(a)
        kx, ky = 15.5 + ax * 9.5, 15.5 + ay * 9.5
        fr = np.zeros((32, 32, 4), np.uint8)
        for y in range(32):
            for x in range(32):
                dx, dy = x - 15.5, y - 15.5
                r = math.hypot(dx, dy)
                lit = (dx + dy) / max(r, 1.0)                     # -1.4 upper left .. 1.4 lower right
                v = C["b1"] if ((x + y) & 1 and y > 3 and r < 13.2) or (y > 9 and r < 12.0) else C["b0"]
                if r > 14.8: v = C["g1"] if lit < 0 else C["g0"]
                elif r > 13.6: v = C["g4"] if lit < -0.9 else C["g3"] if lit < 0.1 else C["g2"]
                elif r > 12.9: v = C["o"]
                along = dx * ax + dy * ay
                across = dx * -ay + dy * ax
                if 0 <= along <= 9.5 and abs(across) <= 2.2:
                    v = C["o"] if abs(across) > 1.6 else C["s2"] if across * (1 if ax + ay >= 0 else -1) < -0.5 else C["s1"] if abs(across) < 0.6 else C["s0"]
                if r <= 4.6:
                    v = C["o"] if r > 3.9 else C["g4"] if lit < -0.8 and r > 1.2 else C["g3"] if lit < 0.2 else C["g2"] if r > 1.0 else C["g1"]
                kr = math.hypot(x - kx, y - ky)
                if kr <= 4.1:
                    kl = ((x - kx) + (y - ky)) / max(kr, 1.0)
                    v = C["o"] if kr > 3.4 else C["k2"] if kl < -0.7 and kr > 0.9 else C["k1"] if kl < 0.6 else C["k0"]
                fr[y, x] = v
        fr[int(round(ky)) - 1, int(round(kx)) - 1] = C["s2"]       # knob spark
        sheet[48:80, 32 * k:32 * k + 32] = fr
    anims["crank"] = [{"x": 32 * k, "y": 48, "w": 32, "h": 32} for k in range(8)]

    # ---- cage glass 96x80: night glass, darker under the roof and at the floor, two slanted reflections
    G = [c5(1, 2, 6), c5(2, 4, 9), c5(3, 6, 12), c5(4, 9, 15), c5(6, 12, 18), c5(9, 16, 21), c5(14, 21, 25)]
    yy, xx = np.mgrid[0:80, 0:96]
    u, v = xx / 95.0, yy / 79.0
    lvl = 0.4 + 2.2 * np.sin(np.clip(v, 0, 1) * math.pi) ** 0.8 * (0.75 + 0.25 * u) \
        + 1.6 * np.exp(-((u + v * 0.55 - 0.42) * 9.0) ** 2) + 1.0 * np.exp(-((u + v * 0.55 - 0.63) * 16.0) ** 2) \
        + 1.3 * np.exp(-((v - 0.97) * 14.0) ** 2) - 1.2 * np.exp(-((v - 0.0) * 9.0) ** 2)
    t = BAYER[yy & 3, xx & 3]
    gi = np.clip(np.floor(lvl + (t - 0.5) * 0.8 + 0.5).astype(int), 0, 5)
    glass = np.array(G, np.uint8)[gi]
    for x, y in ((14, 9), (15, 9), (16, 9), (13, 10), (14, 10), (12, 11), (70, 60), (71, 60), (69, 61)):
        glass[y, x] = G[6]
    sheet[80:160, 0:96] = glass
    anims["glass"] = [{"x": 0, "y": 80, "w": 96, "h": 80}]

    # ---- ticket 192x80: rows 0..39 the ticket, rows 40..79 the tray it slides over (every tray column is one colour, so the
    # tray does not seem to move with the ticket)
    T = {"o": c5(2, 0, 5), "p0": c5(6, 2, 9), "p1": c5(9, 3, 13), "p2": c5(13, 6, 18), "p3": c5(18, 10, 23), "g0": c5(15, 9, 2),
         "g1": c5(22, 15, 3), "g2": c5(28, 22, 6), "g3": c5(31, 29, 14), "t0": c5(1, 1, 4), "t1": c5(3, 3, 8), "t2": c5(5, 5, 11),
         "t3": c5(8, 8, 15)}
    def tray(x):
        e = min(x, 191 - x)
        if e < 2: return T["t0"]
        m = x % 16
        return T["t0"] if m == 0 else T["t3"] if m == 1 else T["t2"] if m in (2, 9) else T["t1"]
    tk = np.zeros((80, 192, 4), np.uint8)
    for x in range(192):
        tk[:, x] = tray(x)
    for y in range(40):
        for x in range(4, 188):
            ex, ey = min(x - 4, 187 - x), min(y, 39 - y)
            e = min(ex, ey)
            if math.hypot(min(x - 4, 187 - x) + 0.5, y - 19.5) < 5.0: continue          # side notches show the tray
            if (ex < 3 and ey < 3) and ex + ey < 2: continue                             # clipped corners
            if e == 0 or math.hypot(min(x - 4, 187 - x) + 0.5, y - 19.5) < 6.0 or ((ex < 3 and ey < 3) and ex + ey == 2):
                v = T["o"]
            elif e == 1: v = T["p3"] if (y < 20) else T["p1"]
            elif e == 3: v = T["g3"] if (x + y) % 9 < 5 else T["g2"]
            elif e == 4: v = T["g1"] if (x + y) % 9 < 6 else T["g0"]
            elif ey < 8:
                v = T["p2"] if BAYER[y & 3, x & 3] < (0.75 if y < 20 else 0.3) else T["p1"]
            else:
                v = T["p0"] if BAYER[y & 3, x & 3] < 0.82 - 0.2 * (x / 191.0) else T["p1"]  # text area: flat and dark
            tk[y, x] = v
        for x in (24, 167):                                                               # perforation
            if y % 4 < 2 and 6 <= y <= 33: tk[y, x] = T["g1"]
    sheet[160:240, 0:192] = tk
    anims["ticket"] = [{"x": 0, "y": 160, "w": 192, "h": 80}]
    return sheet, anims


def preview(out, pals, sheet, q):
    """Scene with the sprites behind it: all bubbles at rest, wheels at 0, ticket in. For the draft page only."""
    rgb = np.zeros((H, W, 3), np.uint8)
    def blit(sx, sy, w, h, dx, dy):
        for y in range(h):
            for x in range(w):
                if 0 <= dy + y < H and 0 <= dx + x < W and sheet[sy + y, sx + x, 3]:
                    rgb[dy + y, dx + x] = sheet[sy + y, sx + x, :3]
    blit(0, 80, 96, 80, CAGE[0], CAGE[1])
    for p in q:
        blit(0, 0, 16, 16, CAGE[0] + p[-1][0] - 8, CAGE[1] + p[-1][1] - 8)
    for k in range(5):
        blit(0, 16, 16, 32, WHEEL[0] + 16 * k, WHEEL[1])
    blit(0, 48, 32, 32, CRANK[0], CRANK[1])
    blit(0, 160, 192, 80, TICKET[0], TICKET[1] - 40)
    names = pals["palette_order"]
    for r in range(ROWS):
        for c in range(COLS):
            pal = [(0, 0, 0)] + [tuple(v) for v in pals["palettes"][names[cellpal[r, c]]]]
            for y in range(r * 8, r * 8 + 8):
                for x in range(c * 8, c * 8 + 8):
                    if px[y, x]: rgb[y, x] = pal[px[y, x]]
    Image.fromarray(rgb, "RGB").save(os.path.join(out, "result_preview.png"))


if __name__ == "__main__":
    out = "build/gen"
    if "--out" in sys.argv: out = sys.argv[sys.argv.index("--out") + 1]
    os.makedirs(out, exist_ok=True)
    pals = json.load(open(os.path.join(ROOT, "assets/result/result_palettes.json")))
    if pals["palette_order"] != ["res_sky0", "res_sky1", "res_sky2", "res_metal", "res_body"]:
        sprite_pipeline.die("result palettes are not sky0, sky1, sky2, metal, body")
    paint_scene()
    n = write_scene(out, pals)
    runs = bake_paths()
    rest, size = write_paths(out, runs)
    sheet, anims = paint_sprites()
    preview(out, pals, sheet, runs[-1])
    sp, mp = os.path.join(out, "resfx_sheet.png"), os.path.join(out, "resfx_sheet.json")
    Image.fromarray(sheet, "RGBA").save(sp)
    json.dump({"animations": anims}, open(mp, "w"))
    print("result scene: %d fix tiles, bubble paths %d bytes, at rest by frame %d" % (n, size, rest))
    sys.argv += ["--sheet", sp, "--meta", mp]
    sprite_pipeline.main("resfx", sp, mp)
