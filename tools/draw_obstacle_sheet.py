#!/usr/bin/env python3
"""Draws the four obstacle sprites (original art, hand-placed pixel clusters) to
assets/obstacles/obstacle_sheet.png + obstacle_sheet.json. Usage (repo root):
    /opt/homebrew/bin/python3.14 -I tools/draw_obstacle_sheet.py
Rect sizes equal the hit boxes in src/core/tuning.h (VENT 32x24, CABLE 48x16, DRONE 28x20,
BOT 28x28). Style: art direction v9 (docs: thoughts/shared/research/2026-11-09_art-direction.md):
1 px near-black outline, flat shade steps (top highlight, mid, shadow), cyan rim light on the
upper and right edges, hue-shifted accents (red lights, amber and cyan sparks). No gradients or
dithering. One shared 15-colour palette; every colour is snapped to a 5-bit-per-channel value.
Animations are in ObstacleType order (vent, cable, drone, bot): OBS_ANIM_* == OB_*.
"""
import json
import os
from PIL import Image

SRC = {  # props palette of the art direction page, plus a dark red, a cable highlight, amber, pink
    "ol": "#07060f", "vent": "#5d6584", "ventL": "#8b93b3", "ventD": "#3d4460",
    "body": "#3b3f55", "bodyL": "#6e7396", "rotor": "#a6acd0", "light": "#ff3355",
    "lightD": "#8a1d3a", "cable": "#1d1a2b", "cableL": "#4a4468", "cyan": "#48f0ff",
    "white": "#ffffff", "amber": "#ffd36b", "pink": "#ff3f9a",
}


def snap(h):
    v = [int(h[i:i + 2], 16) for i in (1, 3, 5)]
    f = [round(c * 31 / 255) for c in v]
    return tuple((x << 3) | (x >> 2) for x in f)


C = {k: snap(v) for k, v in SRC.items()}
assert len(set(C.values())) == len(C), "snapped colours collide"


class Canvas:
    def __init__(self, w, h):
        self.w, self.h, self.p = w, h, {}

    def px(self, x, y, c):
        assert 0 <= x < self.w and 0 <= y < self.h, (x, y, self.w, self.h)
        self.p[(x, y)] = c

    def rect(self, x0, y0, x1, y1, c):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.px(x, y, c)

    def outline(self):
        """1 px ol around everything drawn so far, inside the rect (borders get none)."""
        add = []
        for (x, y) in self.p:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                q = (x + dx, y + dy)
                if q not in self.p and 0 <= q[0] < self.w and 0 <= q[1] < self.h:
                    add.append(q)
        for q in add:
            self.p[q] = "ol"

    def cut(self, *pts):
        for q in pts:
            self.p.pop(q, None)


def vent(f):
    c = Canvas(32, 24)
    c.rect(5, 0, 12, 1, "vent"); c.rect(6, 2, 11, 4, "ventD")           # exhaust stack with cap
    c.rect(3, 4, 28, 16, "vent"); c.rect(3, 4, 28, 4, "ventL")            # housing, top highlight
    c.rect(3, 16, 28, 16, "ventD"); c.rect(26, 5, 28, 15, "ventD")        # bottom and right shadow
    for x in range(24, 29): c.px(x, 4, "cyan")                            # cyan rim, top right
    for y in range(5, 9): c.px(28, y, "cyan")
    c.rect(7, 7, 22, 14, "ventD")                                         # grille panel
    for y in ((8, 10, 12) if f == 0 else (9, 11, 13)): c.rect(8, y, 21, y, "ventL")
    c.px(4, 6, "bodyL"); c.px(4, 14, "bodyL")                             # bolts
    c.rect(0, 17, 31, 23, "body"); c.rect(0, 17, 31, 17, "bodyL"); c.rect(0, 23, 31, 23, "ventD")
    for x in range(26, 32): c.px(x, 17, "cyan")
    c.px(3, 20, "bodyL"); c.px(28, 20, "bodyL"); c.rect(8, 20, 17, 20, "ventD")
    c.rect(22, 19, 26, 22, "ventD")                                       # status lamp housing
    c.outline()
    c.rect(23, 20, 25, 21, "light" if f == 0 else "lightD")
    if f == 0: c.px(23, 20, "white")
    return c


def cable(f):
    c = Canvas(48, 16)
    c.rect(0, 0, 5, 5, "body"); c.rect(0, 0, 5, 0, "bodyL"); c.rect(42, 0, 47, 5, "body"); c.rect(42, 0, 47, 0, "bodyL")
    for y in (1, 2, 3): c.px(5, y, "cyan"); c.px(47, y, "cyan")
    c.px(2, 2, "bodyL"); c.px(44, 2, "bodyL")
    cy = lambda x: 3 + round(7 * (1 - ((x - 23.5) / 23.5) ** 2))
    for x in range(4, 44):
        if 22 <= x <= 25:
            continue                                                       # break in the cable
        y = cy(x)
        c.px(x, y - 1, "cableL"); c.px(x, y, "cable"); c.px(x, y + 1, "cable")
    for x in (21, 26):                                                     # bare copper ends
        for y in range(cy(x) - 1, cy(x) + 2): c.px(x, y, "amber")
    c.outline()
    mid = cy(23)
    arcs = [[(22, mid, "cyan"), (24, mid, "cyan"), (23, mid - 1, "white")],
            [(23, mid, "cyan"), (25, mid, "cyan"), (24, mid + 1, "white")],
            [(23, mid, "white"), (24, mid, "white"), (22, mid + 1, "cyan"), (25, mid - 1, "cyan")]]
    sparks = [[(23, 12, "white"), (22, 13, "cyan"), (25, 13, "amber"), (24, 15, "cyan"), (20, 12, "cyan")],
              [(24, 12, "white"), (23, 14, "amber"), (26, 12, "cyan"), (22, 12, "cyan"), (27, 14, "cyan"), (21, 15, "amber")],
              [(23, 11, "white"), (24, 13, "cyan"), (22, 14, "amber"), (26, 13, "amber"), (25, 15, "cyan"), (20, 13, "cyan")]]
    for x, y, col in arcs[f] + sparks[f]:
        c.px(x, y, col)
    return c


def drone(f):  # f 0..3: rotor wide/narrow x light on/off
    c = Canvas(28, 20)
    wide, on = f % 2 == 0, f < 2
    if wide:
        c.rect(2, 2, 25, 2, "rotor"); c.px(1, 3, "vent"); c.px(26, 3, "vent")
    else:
        c.rect(8, 2, 19, 2, "rotor")
    c.rect(12, 3, 15, 3, "vent")                                           # hub
    c.rect(12, 4, 15, 7, "vent"); c.rect(13, 4, 14, 4, "ventL")           # mast
    c.rect(7, 8, 20, 15, "body"); c.cut((7, 8), (20, 8), (7, 15), (20, 15))
    c.rect(8, 8, 19, 8, "bodyL"); c.rect(8, 15, 19, 15, "ventD"); c.rect(19, 9, 20, 14, "ventD")
    for x in range(14, 20): c.px(x, 8, "cyan")
    for y in range(10, 13): c.px(20, y, "cyan")
    c.rect(3, 9, 6, 12, "vent"); c.rect(21, 9, 24, 12, "vent")            # side thrusters
    c.rect(3, 9, 6, 9, "ventL"); c.rect(21, 9, 24, 9, "ventL")
    for y in (10, 11): c.px(24, y, "cyan")
    c.rect(9, 10, 12, 12, "ventD")                                         # eye socket (front is left)
    c.rect(16, 13, 18, 13, "ventD")
    for x in (8, 9, 18, 19): c.rect(x, 16, x, 18, "vent")                  # skids
    c.rect(7, 19, 10, 19, "ventD"); c.rect(17, 19, 20, 19, "ventD")
    c.outline()
    c.rect(10, 11, 11, 11, "light" if on else "lightD"); c.px(10, 10, "lightD")
    if on: c.px(10, 11, "white")
    c.rect(16, 13, 18, 13, "cyan")                                         # camera lens
    return c


def bot(f):
    c = Canvas(28, 28)
    c.rect(2, 22, 25, 27, "body"); c.cut((2, 22), (25, 22), (2, 27), (25, 27))
    c.rect(3, 22, 24, 22, "bodyL")
    for k in range(6):
        x = 3 + 4 * k + 2 * f
        if x <= 24: c.px(x, 27, "ventD"); c.px(x, 23, "ventD")           # tread marks move
    for x in (5, 11, 17, 22): c.rect(x, 24, x + 1, 25, "ventL")           # wheel hubs
    c.px(25, 23, "cyan"); c.px(25, 24, "cyan")
    c.rect(4, 10, 23, 21, "vent"); c.rect(4, 10, 23, 10, "ventL")         # torso
    c.rect(4, 21, 23, 21, "ventD"); c.rect(21, 11, 23, 20, "ventD")
    for x in range(16, 24): c.px(x, 10, "cyan")
    for y in range(11, 15): c.px(23, y, "cyan")
    c.rect(8, 13, 16, 18, "ventD")                                         # chest panel
    for x in (9, 11, 13, 15): c.px(x, 14, "amber")                        # hazard dashes
    c.px(9, 18, "bodyL"); c.px(15, 18, "bodyL")
    c.rect(10, 9, 15, 9, "ventD")                                          # neck
    c.rect(7, 3, 19, 8, "body"); c.cut((7, 3), (19, 3), (7, 8), (19, 8))   # head
    c.rect(8, 3, 18, 3, "bodyL"); c.rect(18, 4, 19, 7, "ventD")
    for x in range(13, 19): c.px(x, 3, "cyan")
    c.px(19, 4, "cyan")
    c.rect(7, 5, 12, 7, "ol"); c.cut((7, 5))                               # visor slit
    c.rect(17, 1, 17, 2, "ventD")                                          # antenna
    c.rect(0, 13, 3, 16, "vent"); c.rect(0, 13, 3, 13, "ventL")            # arm cannon
    c.outline()
    c.rect(8, 6, 11, 6, "light")
    if f == 0: c.px(8, 6, "white")
    else: c.px(11, 6, "lightD")
    c.rect(17, 0, 18, 0, "light" if f == 0 else "lightD")                  # antenna tip blinks
    c.px(0, 14, "light"); c.px(0, 15, "lightD")
    return c


SETS = [("vent", vent, 2), ("cable", cable, 3), ("drone", drone, 4), ("bot", bot, 2)]


def main():
    rows = []
    for name, fn, n in SETS:
        rows.append((name, [fn(f) for f in range(n)]))
    gut = 2
    width = max(sum(fr.w + gut for fr in frs) for _, frs in rows)
    height = sum(max(fr.h for fr in frs) + gut for _, frs in rows)
    im = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    meta = {"source": "original pixel art drawn by tools/draw_obstacle_sheet.py (no external art)",
            "origin": "rect = hit box (src/core/tuning.h); art bottom = box bottom; 1 px ink outline inside the rect",
            "palette_policy": "merge",
            "palette": {k: SRC[k] for k in SRC}, "animations": {}}
    y = 0
    for name, frs in rows:
        x = 0
        meta["animations"][name] = []
        for fr in frs:
            for (px_, py_), col in fr.p.items():
                im.putpixel((x + px_, y + py_), C[col] + (255,))
            meta["animations"][name].append({"x": x, "y": y, "w": fr.w, "h": fr.h})
            x += fr.w + gut
        y += max(f.h for f in frs) + gut
    out = os.path.join("assets", "obstacles")
    os.makedirs(out, exist_ok=True)
    im.save(os.path.join(out, "obstacle_sheet.png"))
    with open(os.path.join(out, "obstacle_sheet.json"), "w") as f:
        json.dump(meta, f, indent=1)
    print("[OK] obstacle sheet %dx%d, colours used: %d" % (width, height, len({c for _, fs in rows for fr in fs for c in fr.p.values()})))


if __name__ == "__main__":
    main()
