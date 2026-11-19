"""Merge the walk, landing and breathing drafts into the Sootling sheet (105 frames, 16 clips).

Run from the repo root: /opt/homebrew/bin/python3.14 -I thoughts/shared/drafts/2026-11-11-sootling-walk-cycle/merge_sheet.py
Reads assets/flier/sootling_sheet.png/.json (63 frames) and the two draft sheets, writes merged_sheet.png/.json
beside this script. Every check prints one line; any failure exits with status 1 before writing.
"""
import json
import os
import re
import sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OLD_PNG = "assets/flier/sootling_sheet.png"
OLD_JSON = "assets/flier/sootling_sheet.json"
FW, FH = 24, 32
COLS = 8
OLD_FRAMES = 63
NEW_FRAMES = 105
ROWS = (NEW_FRAMES + COLS - 1) // COLS
RIVAL_Y = FH * ROWS

# (define, first, count, loop, draft file, player row, rival row, first column)
GUMLESS = os.path.join(HERE, "walk_sheet_draft.png")
GUM = os.path.join(HERE, "walk_gum_sheet_draft.png")
CLIPS = [
    ("CLIP_WALK0", 63, 8, 1, GUMLESS, 4, 5),
    ("CLIP_LAND0", 71, 2, 0, GUMLESS, 6, 7),
    ("CLIP_BREATHE0", 73, 4, 1, GUMLESS, 8, 9),
    ("CLIP_WALK2", 77, 8, 1, GUM, 0, 1),
    ("CLIP_LAND2", 85, 2, 0, GUM, 2, 3),
    ("CLIP_BREATHE2", 87, 4, 1, GUM, 4, 5),
    ("CLIP_WALK1", 91, 8, 1, GUM, 6, 7),
    ("CLIP_LAND1", 99, 2, 0, GUM, 8, 9),
    ("CLIP_BREATHE1", 101, 4, 1, GUM, 10, 11),
]
STRIPS = {  # clip define -> strip base name in the draft dir
    "CLIP_WALK2": "gum_walk_C_gum2", "CLIP_LAND2": "gum_land_gum2", "CLIP_BREATHE2": "gum_breathe_gum2",
    "CLIP_WALK1": "gum_walk_C_gum1", "CLIP_LAND1": "gum_land_gum1", "CLIP_BREATHE1": "gum_breathe_gum1",
}
failed = []


def check(name, ok, detail=""):
    print(("[OK] " if ok else "[FAIL] ") + name + (" " + detail if detail else ""))
    if not ok:
        failed.append(name)


def cell(im, col, row):
    return im.crop((col * FW, row * FH, col * FW + FW, row * FH + FH))


old = Image.open(OLD_PNG).convert("RGBA")
oj = json.load(open(OLD_JSON))
gumless = Image.open(GUMLESS).convert("RGBA")
gum = Image.open(GUM).convert("RGBA")

out = Image.new("RGBA", (COLS * FW, 2 * RIVAL_Y), (0, 0, 0, 0))
old_rival_y = FH * ((OLD_FRAMES + COLS - 1) // COLS)
same = True
for i in range(OLD_FRAMES):
    c, r = i % COLS, i // COLS
    p = cell(old, c, r)
    q = cell(old, c, r + old_rival_y // FH)
    out.paste(p, (c * FW, r * FH))
    out.paste(q, (c * FW, RIVAL_Y + r * FH))
check("old frames 0..62 copied", True)

new_cells = {}  # frame -> (player, rival)
for (name, first, count, loop, src, prow, rrow) in CLIPS:
    im = gumless if src == GUMLESS else gum
    for k in range(count):
        pc, rc = cell(im, k, prow), cell(im, k, rrow)
        i = first + k
        new_cells[i] = (pc, rc)
        c, r = i % COLS, i // COLS
        out.paste(pc, (c * FW, r * FH))
        out.paste(rc, (c * FW, RIVAL_Y + r * FH))

# (1) old frames unchanged
ok = True
for i in range(OLD_FRAMES):
    c, r = i % COLS, i // COLS
    ok &= cell(old, c, r).tobytes() == out.crop((c * FW, r * FH, c * FW + FW, r * FH + FH)).tobytes()
    ok &= cell(old, c, r + old_rival_y // FH).tobytes() == out.crop((c * FW, RIVAL_Y + r * FH, c * FW + FW, RIVAL_Y + r * FH + FH)).tobytes()
check("(1) frames 0..62 pixel-identical, player and rival", ok)

# (3) every new frame equals its draft cell, read back from the merged image
ok = True
for i, (pc, rc) in new_cells.items():
    c, r = i % COLS, i // COLS
    ok &= pc.tobytes() == out.crop((c * FW, r * FH, c * FW + FW, r * FH + FH)).tobytes()
    ok &= rc.tobytes() == out.crop((c * FW, RIVAL_Y + r * FH, c * FW + FW, RIVAL_Y + r * FH + FH)).tobytes()
check("(3) 42 new frames equal their draft cells", ok and len(new_cells) == 42)

# strips equal the combined sheet rows
for define, base in STRIPS.items():
    first, count = [(c[1], c[2]) for c in CLIPS if c[0] == define][0]
    for who, idx in (("player", 0), ("rival", 1)):
        s = Image.open(os.path.join(HERE, base + "_" + who + ".png")).convert("RGBA")
        sized = s.size == (FW * count, FH)
        eq = sized and all(cell(s, k, 0).tobytes() == new_cells[first + k][idx].tobytes() for k in range(count))
        check("strip " + base + "_" + who, eq, "size %s" % (s.size,))

# (4) gumless breathe frame 0 == idle frame 62
c62 = cell(old, 62 % COLS, 62 // COLS)
check("(4) breathe0 frame 0 (sheet 73) equals idle 62", new_cells[73][0].tobytes() == c62.tobytes())

# (5) measure_gum.txt flags
txt = open(os.path.join(HERE, "measure_gum.txt")).read()
n_flag = len(re.findall(r"CLIPPED|ABOVE FRAME", txt))
check("(5) measure_gum.txt has no CLIPPED / ABOVE FRAME flag", n_flag == 0, "count %d" % n_flag)
# two-bubble frames: bubble pixels exist in the top 9 rows, columns 3..19
ok = True
for define in ("CLIP_WALK2", "CLIP_LAND2", "CLIP_BREATHE2"):
    first, count = [(c[1], c[2]) for c in CLIPS if c[0] == define][0]
    for k in range(count):
        for who in (0, 1):
            im = new_cells[first + k][who]
            top = [im.getpixel((x, y))[3] for y in range(0, 9) for x in range(3, 20)]
            ok &= sum(1 for a in top if a) > 10
check("(5b) gum2 frames show bubble pixels in rows 0..8 (weak check; measure_gum.txt is the source)", ok)

# (6) colours and fur
old_cols = set(old.getdata())
new_cols = set()
for pc, rc in new_cells.values():
    new_cols |= set(pc.getdata()) | set(rc.getdata())
extra = new_cols - old_cols
check("(6) new frames use only colours already in the old sheet", not extra, "extra %d" % len(extra))
ok = True
for i, (pc, rc) in new_cells.items():
    for im in (pc, rc):
        ok &= any(im.getpixel((x, y))[3] for x in range(10, 14) for y in range(FH))
check("(6b) every new frame has opaque pixels in columns 10..13", ok)

# JSON
j = json.loads(json.dumps(oj))
j["source"] = "thoughts/shared/drafts/2026-11-11-sootling-walk-cycle/merge_sheet.py (merged from the 2026-11-10 small sheet and the walk, landing and breathing drafts)"
for key in ("player", "cpu"):
    j["animations"][key] = []
for i in range(NEW_FRAMES):
    c, r = i % COLS, i // COLS
    j["animations"]["player"].append({"x": c * FW, "y": r * FH, "w": FW, "h": FH})
    j["animations"]["cpu"].append({"x": c * FW, "y": RIVAL_Y + r * FH, "w": FW, "h": FH})
d = j["defines"]
d["CLIP_COUNT"] = 16
d["FRAMES"] = NEW_FRAMES
t = j["tables"]
for n, (name, first, count, loop, *_rest) in enumerate(CLIPS):
    d[name] = 7 + n
    t["clip_first"].append(first)
    t["clip_count"].append(count)
    t["clip_loop"].append(loop)
t["frame_ticks"] += [1] * 42

cf, cc = t["clip_first"], t["clip_count"]
check("(2) frames/tables consistent",
      sum(cc) == NEW_FRAMES and all(cf[i] + cc[i] == cf[i + 1] for i in range(len(cf) - 1))
      and len(t["frame_ticks"]) == NEW_FRAMES and len(j["animations"]["player"]) == NEW_FRAMES
      and len(j["animations"]["cpu"]) == NEW_FRAMES and len(cf) == 16 == len(cc) == len(t["clip_loop"]))
check("sheet size", out.size == (192, 896), str(out.size))

if failed:
    print("FAILED:", failed)
    sys.exit(1)
out.save(os.path.join(HERE, "merged_sheet.png"))
json.dump(j, open(os.path.join(HERE, "merged_sheet.json"), "w"), indent=1)
print("[OK] wrote merged_sheet.png/.json")
