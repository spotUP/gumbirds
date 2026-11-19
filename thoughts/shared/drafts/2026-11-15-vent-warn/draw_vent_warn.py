#!/usr/bin/env python3
"""VENT-WARN drafts (2026-11-15). Run: /opt/homebrew/bin/python3.14 -I draw_vent_warn.py
Draft only: reads assets/arcade/arcade_sheet.png (current vent body_a + spark_a, storm palette), writes GIFs/PNGs here.
All new art is hand-placed below: palette-index grids (chars = storm palette index, hex, '.' = transparent),
hand-picked 5-bit colour steps, hand-written shake tables. No noise, no computed gradients."""
import json, os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "../../../.."))
SHEET = Image.open(os.path.join(ROOT, "assets/arcade/arcade_sheet.png")).convert("RGBA")
META = json.load(open(os.path.join(ROOT, "assets/arcade/arcade_sheet.json")))
STORM = [tuple(c) for c in META["palettes"]["storm"]]          # index 1..15 (0 = transparent)
LOOP, TELE, LAUNCH, BURST = 336, 144, 216, 40                  # src/core/arc_elements.h:15-17,60
assert META["defines"]["VENT_LOOP_TICKS"] == LOOP

def crop_idx(anim_i):
    """Asset frame -> rows of palette indices (0 transparent). Fails if a pixel is off the storm palette."""
    r = META["animations"]["storm"][anim_i]
    return [[0 if SHEET.getpixel((r["x"] + x, r["y"] + y))[3] == 0 else STORM.index(SHEET.getpixel((r["x"] + x, r["y"] + y))[:3]) + 1
             for x in range(r["w"])] for y in range(r["h"])]
p = META["pieces"]
BODY = [crop_idx(p["body_a"][1] + i) for i in range(5)]        # the game draws body_a / spark_a (src/main.c:558)
SPARK = [crop_idx(p["spark_a"][1] + i) for i in range(8)]

def grid(rows, w=16, h=16):
    """Hand grid, bottom aligned: rows missing at the top are empty."""
    assert all(len(r) == w for r in rows) and len(rows) <= h, rows
    rows = ["." * w] * (h - len(rows)) + rows
    return [[0 if c == "." else int(c, 16) for c in r] for r in rows]

c5 = lambda v: (v << 3) | (v >> 2)                             # Neo Geo 5-bit channel -> 8-bit
# Glow: hand-picked steps for vent palette entries 1..5 (outline, 3 metal shades, metal light). 5-bit RGB.
# Shadows drift purple -> maroon, lights drift orange -> yellow (hue shift, not a straight blend to red).
HEAT = [
    [(1, 1, 3), (3, 3, 7), (6, 6, 11), (10, 11, 15), (16, 16, 18)],   # 0 = storm colours, cold
    [(2, 1, 3), (5, 3, 7), (9, 6, 10), (13, 10, 13), (19, 15, 16)],
    [(3, 1, 3), (7, 3, 6), (12, 5, 9), (16, 9, 11), (22, 14, 13)],
    [(4, 1, 3), (9, 2, 5), (15, 4, 7), (20, 8, 8), (25, 14, 10)],
    [(5, 1, 2), (11, 2, 4), (18, 4, 5), (23, 8, 5), (28, 15, 8)],
    [(7, 1, 2), (13, 2, 3), (21, 4, 3), (26, 9, 3), (30, 18, 7)],
    [(9, 1, 1), (16, 2, 2), (24, 5, 2), (29, 12, 3), (31, 22, 8)],
    [(12, 2, 1), (19, 3, 1), (27, 7, 2), (31, 16, 4), (31, 27, 13)],  # 7 = white-hot rim
]
assert [tuple(c5(v) for v in c) for c in HEAT[0]] == STORM[:5], "step 0 must be the in-game storm colours"
# warn tick (0..71) -> heat step. Slow start, quick end, last 6 ticks flicker 7/6. Then cool-down after the burst.
HEAT_AT = [(0, 1), (14, 2), (26, 3), (36, 4), (45, 5), (53, 6), (60, 7), (66, 6), (68, 7), (70, 6)]
COOL_AT = [(0, 7), (40, 5), (50, 3), (60, 1), (70, 0)]        # ticks after LAUNCH (burst stays hot)
# Shake (dx, dy) tables, one entry per 2 ticks, hand written. Rattle grows in three stages over the warn window.
SHAKE = ([(0, 0), (0, 0), (1, 0), (0, 0), (0, 0), (-1, 0)] * 2          # warn 0..23: a tick now and then
         + [(1, 0), (0, 0), (-1, 0), (0, -1), (1, 0), (-1, 0)] * 2      # 24..47: steady rattle, small hops
         + [(2, 0), (-1, -1), (1, 0), (-2, 0), (1, -1), (-1, 0), (2, -1), (-2, 0), (1, 0), (-1, -1), (2, 0), (-2, -1)])  # 48..71
assert len(SHAKE) == 36

# B: boil strip, 10 frames 16x16, drawn with its bottom row on the vent's top outline row (sits behind the body,
# so no sprite-order change). Colours: 9 blue rim, a cyan, b pale, c white = the spark's own colours.
BOIL = [grid(r) for r in [
    [".....99.........", "....9ab9...9....", "....9aa9..9a9..."],
    [".....99.........", "....9ab9........", "...9abba9..99...", "...9aaaa9.9ab9.."],
    [".....999........", "....9abb9.......", "...9abcba9......", "...9abbaa9......", "...9aaaa99..99..", "....9aa99..9ab9.", ".....999...9aa9."],
    [".....99.........", "....9ab9........", "...9abcb9.......", "...9abba9.......", "...9abaa9.......", "...9aaaa9..99...", "....9aa9..9ab9..", "....9aa9.9abba9.", ".....99..9aaaa9."],
    ["....b...b.......", "..b...c....b....", ".....c.c........", "...a..c..a......", "....b...b.......", "..a.......99....", ".....a...9ab9...", ".........9bcb9..", "........9abbaa9.", "........9aaaa99."],
    ["...b......b.....", "................", ".b..............", "................", "......a.........", "..........99....", ".a.......9ab9...", "........9abcb9..", "........9abba9..", "........9aaaa9..", "....99...9aa9...", "...9ab9...99...."],
    ["..........99....", ".........9ab9...", ".........9bcb9..", "a........9abb9..", ".........9aba9..", "..........9a9...", "..a.......9a9...", "....99.....9....", "...9ab9.........", "..9abba9........"],
    [".......b...c...b", ".........c......", "........b.c.b...", "...........c....", ".......a.....a..", "..........b.....", "....99..........", "...9ab9......a..", "..9abcb9........", "..9abbaa9.......", "..9aaaa99......."],
    [".......b....b...", "................", "................", "...............a", "................", "................", "....999.........", "...9abb9........", "..9abcba9.......", "..9abbaa9....a..", "..9aaaa99.......", "...9aa99........", "....999........."],
    ["....99..........", "...9ab9.........", "...9ba9.........", "....99..........", "................", "................", "................", "................", "...............a", "...........9....", ".....9....9a9..."],
]]
BOIL_TICKS = [6] * 3 + [5] * 4 + [4] * 4 + [3] * 6    # warn 0..71 in 17 holds: boils faster as it heats (sum 72)
assert sum(BOIL_TICKS) == 72

# C: ember, 6 frames 16x16: streak, streak, round, apex, break, fall. c white, d yellow, e orange.
EMBER = [grid(r) for r in [
    [".......d........", ".......cd.......", "......dccd......", "......dccd......", ".......dce......", ".......dde......", ".......ed.......", ".......ee.......", "........e.......", ".......e........", "................", "........e.......", "................"],
    [".......d........", "......dcd.......", "......dccd......", "......dccd......", ".......ddce.....", ".......ede......", "........e.......", ".......e........", "................", "........e.......", "................", ".......e........", "................", "................"],
    [".......dd.......", "......dccd......", ".....edccde.....", "......eddd......", ".......ee.......", "........e.......", "................", ".......e........", "................", "................", "................", "................"],
    [".......d........", "......dcde......", "......eddd......", ".......ee.......", "................", ".........e......", "................", "................", "................", "................", "................"],
    [".....e..........", ".......d..e.....", "......ed........", "........de......", ".....e..........", ".........e......", ".......e........", "................", "................", "................", "................", "................"],
    ["....e......e....", "................", ".......e........", "..........e.....", ".....e..........", "................", "........e.......", "................", "................", "................", "................"],
]]
# Three spits, each thrown higher: (launch warn tick, apex px above the vent top). Gravity 0.12 px/tick^2;
# the last one tops out at the plume height on the launch tick. One ember alive at a time = 1 sprite.
SPITS = [(0, 16), (19, 28), (44, 48)]
G = 0.12
assert SPITS[-1][1] == 48                                      # ARC_VENT_PLUME_H

def ember_at(w):
    """warn tick -> (frame, height px) or None. Ballistic: h = v0*t - G*t*t/2."""
    for t0, apex in reversed(SPITS):
        if w >= t0:
            t = w - t0; v0 = (2 * G * apex) ** 0.5; v = v0 - G * t
            if v < -0.5: return None
            f = 0 if v > 2.2 else 1 if v > 1.3 else 2 if v > 0.5 else 3 if v > -0.1 else 4 if v > -0.3 else 5
            return f, v0 * t - G * t * t / 2
    return None

def step_at(table, t):
    s = 0
    for at, st in table:
        if t >= at: s = st
    return s

def pal(step):
    out = list(STORM)
    out[:5] = [tuple(c5(v) for v in c) for c in HEAT[step]]
    return out

SKY, LEDGE, LEDGE_HI = (20, 24, 52), (49, 49, 90), (82, 90, 123)   # flat backdrop for the draft only
PW, PH, VX, VY = 56, 80, 28, 70                                    # panel size; vent x centre and base line

def blit(im, g, x, y, palette):
    for yy, row in enumerate(g):
        for xx, c in enumerate(row):
            if c and 0 <= x + xx < im.width and 0 <= y + yy < im.height: im.putpixel((x + xx, y + yy), palette[c - 1])

def panel(im, ox, t, var):
    """One vent at loop tick t. var None = current game (src/core/arc_view.c:10-17, 41-50)."""
    for x in range(8, PW - 8):
        for y in range(VY, VY + 6): im.putpixel((ox + x, y), LEDGE_HI if y == VY else LEDGE)
    warn = t - TELE if TELE <= t < LAUNCH else None
    burst = t - LAUNCH if LAUNCH <= t < LAUNCH + BURST else None
    frame = 1 + (t - (LAUNCH - 72)) // 24 if warn is not None else 4 if burst is not None else 0
    step, dx, dy = 0, 0, 0
    if var:
        if warn is not None: step = step_at(HEAT_AT, warn); dx, dy = SHAKE[warn // 2]
        elif t >= LAUNCH: step = step_at(COOL_AT, t - LAUNCH)
    P = pal(step)
    if burst is not None: blit(im, SPARK[(burst // 4) & 7], ox + VX - 8, VY - 16 - burst * 13 // 5, P)
    if var == "C" and warn is not None and ember_at(warn):
        f, h = ember_at(warn); blit(im, EMBER[f], ox + VX - 8, VY - 16 - 8 - int(h), P)
    if var == "B" and warn is not None:
        k, acc = 0, 0
        while acc + BOIL_TICKS[k] <= warn: acc += BOIL_TICKS[k]; k += 1
        blit(im, BOIL[k % 10], ox + VX - 8 + dx, VY - 16 - 15 + dy, P)
    blit(im, BODY[frame], ox + VX - 16 + dx, VY - 16 + dy, P)

def gif(var):
    frames = []
    for t in range(0, LOOP, 2):                                # 2 ticks per GIF frame (browsers clamp delays under 20 ms)
        im = Image.new("RGB", (PW * 2, PH), SKY)
        panel(im, 0, t, None); panel(im, PW, t, var)
        for y in range(PH): im.putpixel((PW - 1, y), (8, 8, 24))
        frames.append(im.resize((PW * 6, PH * 3), Image.NEAREST))
    # 2 ticks = 33.3 ms; GIF delays are whole centiseconds, so 30/30/40 ms repeating keeps the 5.6 s loop exact
    frames[0].save(os.path.join(HERE, f"vent_warn_{var}_3x.gif"), save_all=True, append_images=frames[1:],
                   duration=[30, 30, 40] * (len(frames) // 3), loop=0, disposal=1)

def sheet(var, strip):
    """1x sheet: row per heat step with body frames 0..4, then the variant's own new strip (cold palette)."""
    im = Image.new("RGB", (max(5 * 32, len(strip) * 16), 8 * 16 + (16 if strip else 0)), SKY)
    for s in range(8):
        for f in range(5): blit(im, BODY[f], f * 32, s * 16, pal(s))
    for i, g in enumerate(strip): blit(im, g, i * 16, 8 * 16, pal(0))
    im.save(os.path.join(HERE, f"sheet_{var}_1x.png"))
    im.resize((im.width * 4, im.height * 4), Image.NEAREST).save(os.path.join(HERE, f"sheet_{var}_4x.png"))

for var, strip in (("A", []), ("B", BOIL), ("C", EMBER)): gif(var); sheet(var, strip)
# stills for a quick look: warn tick 30, 56, 70 of each variant, 4x
im = Image.new("RGB", (PW * 9, PH), SKY)
for i, var in enumerate("ABC"):
    for j, w in enumerate((30, 56, 70)): panel(im, (i * 3 + j) * PW, TELE + w, var)
im.resize((im.width * 4, im.height * 4), Image.NEAREST).save(os.path.join(HERE, "stills_4x.png"))
used = {c for g in BOIL + EMBER for r in g for c in r} - {0}
print("ok; new-art palette indices:", sorted(used), "max heat words per frame:", len(HEAT[0]))
