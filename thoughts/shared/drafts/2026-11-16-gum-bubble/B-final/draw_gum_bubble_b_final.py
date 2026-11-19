#!/usr/bin/env python3
"""Hot Gum carrier bubble, option B final polish (owner pick 2026-11-16). 16x16, one sprite column, one tile per cell.
Hand-placed pixel data only: every cell is typed row by row, 16 characters per row. Nothing is drawn from a formula.
Motion offsets (dx, dy) are sprite position changes the game does, not new tiles. Timings are ticks at 60 Hz.
Every cell keeps its stem (row 15) on the same pixels, so squash and stretch happen against a pinned base.
Run: python3.14 -I draw_gum_bubble_b_final.py
"""
import json, os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "../../../../.."))
BG = os.path.join(REPO, "thoughts/shared/drafts/2026-11-10-backgrounds-final")
SUN = os.path.join(REPO, "thoughts/shared/drafts/2026-11-16-p2-colours/sheet_sun_1x.png")
# 10 colours + transparent, all on the Neo Geo 5-bit grid. Shadow turns plum, bounce light magenta, core white.
PAL = {"k": "100818", "m": "5a1042", "r": "ad1031", "R": "e73118", "o": "ff7310", "O": "ffa521", "y": "ffde4a",
       "w": "fff7b5", "W": "ffffff", "p": "ce217b"}
GRID = {(v << 3) | (v >> 2) for v in range(32)}
RGBA = {c: tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (255,) for c, h in PAL.items()}
assert all(v in GRID for c in RGBA.values() for v in c[:3]), "palette colour off the 5-bit grid"

E = "................"
CELLS = [
 [E, E,                        # 0 rest
  ".....kkkkkk.....",
  "...kkoyyyoRkk...",
  "..koywWWyoRRrk..",
  "..kywWWwyoRRrk..",
  ".koywWwyoRRRrrk.",
  ".koOyyooRRRRrmk.",
  ".kRkkooRRRkkrmk.",
  ".kRRokkRRkkrrmk.",
  ".kRRRWkRRkWrmpk.",
  "..krRRRRRrrmpk..",
  "..krRkWkWkrmpk..",
  "...kkrmmmppkk...",
  ".....kkkkkk.....",
  "......kpk......."],
 [E,                           # 1 swell
  ".....kkkkkk.....",
  "...kkoyyyyokk...",
  "..koywWWWyoRRk..",
  ".koywWWWWyoRRrk.",
  ".kywWWWWwyoRRrk.",
  "koywWWWwyoRRRRrk",
  "koOyywyyoRRRRrmk",
  "kRokkooRRRRkkrmk",
  "kRRookkRRRkkrrmk",
  "kRRRRWkRRRkWrmpk",
  ".kRRRRRRRRrrmpk.",
  ".krRRkWkWkrrmpk.",
  "..kkrrmmmmppkk..",
  "....kkkkkkkk....",
  "......kpk......."],
 ["....kkkkkkkk....",          # 2 strain: white hot, eyes shut, teeth bared
  "..kkywwwwwyokk..",
  ".kywWWWWWWwyoRk.",
  "kywWWWWWWWWwyoRk",
  "kywWWWWWWWWwyoRk",
  "kywWWWWWWWwwyoRk",
  "kyywWWWWwwyyoRRk",
  "kokkywwwyyookkRk",
  "koookkyyoRkkRRrk",
  "kRokkkoRRRkkkrrk",
  "kRRRRRRRRRRRrrmk",
  "kRRkkkkkkkkkrrmk",
  ".kRkWkWkWkWkrmk.",
  ".kkrkkkkkkkkrkk.",
  "...kkkkkkkkkk...",
  "......kpk......."],
 [E, E, E, E, E, E,            # 3 snap: squashed flat, eyes wide
  "...kkkkkkkkkk...",
  ".kkoyyyyooRRRkk.",
  "koywWWwyoRRRRrrk",
  "koOywwyooRRRRrmk",
  "kRokkkoRRRkkkrmk",
  "kRRRWkRRRRkWrmpk",
  "kRrRRRkkkkRrrmpk",
  ".kkrrrmmmmpppkk.",
  "...kkkkkkkkkk...",
  "......kpk......."],
 ["......kkkk......",          # 4 rebound: stretched tall, sides curve in at both ends (4,6,8,8,10..10,8,8,6,4 wide)
  ".....kyyoRk.....",
  "....kywWyoRk....",
  "....kwWWyoRk....",
  "...kywWWyoRrk...",
  "...kywWwyoRrk...",
  "...koywyoRRrk...",
  "...koOyoRRRrk...",
  "...kokkoRkkrk...",
  "...kRWkRRkWrk...",
  "...kRRRRRrrmk...",
  "....kRkkkrmk....",
  "....krRRrmpk....",
  ".....krmppk.....",
  "......kkkk......",
  "......kpk......."],
 [E, E, E,                     # 5 wide: anticipation dip and second bounce
  "....kkkkkkkk....",
  "..kkoyyyyoRRkk..",
  ".koywWWwyoRRRrk.",
  ".kywWWwyoRRRRrk.",
  "koOywyooRRRRRrmk",
  "kRokkooRRRRkkrmk",
  "kRRokkRRRRkkrrmk",
  "kRRRWkRRRRkWrmpk",
  ".kRRRRRRRRrrmpk.",
  ".krRRkWkWkrrmpk.",
  "..kkrrmmmmppkk..",
  "....kkkkkkkk....",
  "......kpk......."],
 [E,                           # 6 last small overshoot: one pixel taller and narrower than rest
  "......kkkk......",
  "....kkyyoRkk....",
  "...koywWyoRrk...",
  "..koywWWyoRRrk..",
  "..kywWWwyoRRrk..",
  "..kywWwyoRRRrk..",
  "..koOyyoRRRRmk..",
  "..kkkooRRRkkmk..",
  "..kRokkRRkkrmk..",
  "..kRRWkRRkWrpk..",
  "..krRRRRRrrmpk..",
  "...krkWkWkmpk...",
  "....kkrmmpkk....",
  "......kkkk......",
  "......kpk......."],
]
# (cell, dx, dy, ticks at 60 Hz). Slow in (hold, dip, swell), fast through the snap, slow out (damped tall/wide/tall).
SEQ = [(0, 0, 0, 14), (5, 0, 0, 4), (1, 0, 0, 5), (2, 0, 0, 4), (2, 1, 0, 2), (2, -1, 0, 2), (2, 1, 0, 2), (2, -1, 0, 2),
       (3, 0, 1, 3), (4, 0, -1, 4), (5, 0, 0, 5), (6, 0, 0, 6)]
MS = [round(t * 1000 / 60 / 10) * 10 for *_, t in SEQ]  # GIF steps are 10 ms, so 2 ticks show as 30 ms

def cell(rows):
    assert len(rows) == 16 and all(len(r) == 16 for r in rows), [len(r) for r in rows]
    assert rows[15] == "......kpk.......", "stem must stay pinned"
    im = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    for y, row in enumerate(rows):
        for x, c in enumerate(row):
            if c != ".":
                im.putpixel((x, y), RGBA[c])
    return im

def up(im, n):
    return im.resize((im.width * n, im.height * n), Image.NEAREST)

def gif(frames, name, colors):
    fr = [f.convert("RGB").convert("P", palette=Image.ADAPTIVE, colors=colors) for f in frames]
    fr[0].save(os.path.join(HERE, name), save_all=True, append_images=fr[1:], loop=0, duration=MS, disposal=1)

def main():
    cells = [cell(c) for c in CELLS]
    used = {p for c in cells for p in c.get_flattened_data() if p[3]}
    assert len(used) <= 15, len(used)
    print("cells", len(cells), "colours", len(used), "frames", len(SEQ), "ticks", sum(s[3] for s in SEQ))

    sheet = Image.new("RGBA", (16 * len(cells), 16), (0, 0, 0, 0))
    for i, c in enumerate(cells):
        sheet.paste(c, (i * 16, 0))
    sheet.save(os.path.join(HERE, "sheet_B_final_1x.png"))
    flat = Image.new("RGBA", sheet.size, (58, 63, 92, 255)); flat.alpha_composite(sheet)
    up(flat, 6).save(os.path.join(HERE, "sheet_B_final_6x.png"))
    strip = Image.new("RGBA", (24 * len(SEQ), 24), (58, 63, 92, 255))  # every frame of the loop side by side
    solo = []
    for i, (ci, dx, dy, _) in enumerate(SEQ):
        strip.alpha_composite(cells[ci], (i * 24 + 4 + dx, 4 + dy))
        f = Image.new("RGBA", (24, 24), (58, 63, 92, 255)); f.alpha_composite(cells[ci], (4 + dx, 4 + dy)); solo.append(up(f, 3))
    up(strip, 4).save(os.path.join(HERE, "frames_B_final_4x.png"))
    gif(solo, "anim_B_final_3x.gif", 32)
    gif([up(f, 2) for f in solo], "anim_B_final_6x.gif", 32)

    # ---- mockups: birds from the game sheet (P1, rival) and the sun yellow P2 draft sheet ----
    meta = json.load(open(os.path.join(REPO, "assets/flier/sootling_sheet.json")))
    game = Image.open(os.path.join(REPO, "assets/flier/sootling_sheet.png")).convert("RGBA")
    sun = Image.open(SUN).convert("RGBA")
    first = meta["tables"]["clip_first"][meta["defines"]["CLIP_FLAP2"]]
    def bird(who, n, flip):
        f = meta["animations"]["cpu" if who == "rival" else "player"][first + n]
        im = (sun if who == "P2" else game).crop((f["x"], f["y"], f["x"] + f["w"], f["y"] + f["h"]))
        return im.transpose(Image.FLIP_LEFT_RIGHT) if flip else im
    # crowded cluster: (who, x, y, flap frame, flip); the carrier is named per mockup
    cast = [("P1", 118, 92, 0, False), ("P2", 150, 104, 3, True), ("rival", 136, 78, 5, False), ("rival", 170, 84, 2, True)]
    def scene(mood, carrier, step):
        im = Image.open(os.path.join(BG, f"scene_{mood}_1x.png")).convert("RGBA")
        spot = None
        for i, (who, x, y, n, flip) in enumerate(cast):
            b = bird(who, n, flip)
            im.alpha_composite(b, (x, y))
            if i == carrier:
                l, t, r, _ = b.getbbox()
                spot = (x + (l + r) // 2 - 8, y + t - 14)  # stem two pixels into the top of the balloons, placed by eye
        ci, dx, dy, _ = SEQ[step]
        im.alpha_composite(cells[ci], (spot[0] + dx, spot[1] + dy))
        return im.crop((80, 40, 240, 150))
    names = {0: "P1", 1: "P2", 2: "rival"}
    for mood in ("moon", "dusk", "storm"):
        row = Image.new("RGBA", (160 * 3 + 8, 110 * 2), (0, 0, 0, 255))
        for c in names:
            row.paste(scene(mood, c, 0), (c * 164, 0)); row.paste(scene(mood, c, 3), (c * 164, 110))
        up(row, 3).save(os.path.join(HERE, f"mockup_{mood}_3x.png"))
        for c in names:
            gif([up(scene(mood, c, s), 3) for s in range(len(SEQ))], f"mockup_{mood}_{names[c]}_anim_3x.gif", 200)
    # close contrast card: every cell on each bird, flat mid grey, 6x
    card = Image.new("RGBA", (28 * len(cells), 50 * 3), (90, 96, 110, 255))
    for r, who in enumerate(("P1", "P2", "rival")):
        b = bird(who, 0, False); l, t, rr, _ = b.getbbox()
        for i, c in enumerate(cells):
            card.alpha_composite(b, (i * 28 + 2, r * 50 + 16)); card.alpha_composite(c, (i * 28 + 2 + (l + rr) // 2 - 8, r * 50 + 16 + t - 14))
    up(card, 6).save(os.path.join(HERE, "contrast_birds_6x.png"))

    h = ["<!doctype html><meta charset=utf-8><title>Gum bubble B final</title>",
         "<style>body{background:#1b1e2b;color:#e8e8f0;font:16px/1.5 system-ui,sans-serif;margin:24px;max-width:1500px}"
         "img{image-rendering:pixelated;display:block;margin:8px 0 24px;max-width:100%}h2{margin-top:32px}"
         ".row{display:flex;gap:16px;flex-wrap:wrap}</style>",
         "<h1>Hot Gum bubble, option B final</h1>",
         f"<p>16x16, one sprite column, {len(cells)} cells, {len(SEQ)} frames, {len(used)} colours, one palette. "
         f"Loop {sum(s[3] for s in SEQ)} ticks at 60 Hz.</p>",
         "<h2>Loop (6x) and cells (6x)</h2><div class=row><img src=anim_B_final_6x.gif><img src=sheet_B_final_6x.png></div>",
         "<h2>Every frame in order (4x)</h2><p>Ticks at 60 Hz: " + ", ".join(
             f"{('rest','swell','strain','snap','tall','wide','tall small')[ci]}{'' if not dx else ' shake'} {t}" for ci, dx, dy, t in SEQ)
         + "</p><img src=frames_B_final_4x.png>",
         "<h2>On player 1, sun yellow player 2 and a rival (6x)</h2><img src=contrast_birds_6x.png>"]
    for mood in ("moon", "dusk", "storm"):
        h.append(f"<h2>{mood.title()}: four birds crowded (3x)</h2><p>Columns: carried by player 1, player 2, rival. "
                 "Top rest, bottom strain.</p>" f"<img src=mockup_{mood}_3x.png><div class=row>"
                 + "".join(f"<img src=mockup_{mood}_{n}_anim_3x.gif>" for n in names.values()) + "</div>")
    open(os.path.join(HERE, "index.html"), "w").write("\n".join(h))

if __name__ == "__main__":
    main()
