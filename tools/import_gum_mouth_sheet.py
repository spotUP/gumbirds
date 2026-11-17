#!/usr/bin/env python3
"""Gum-mouth bird v4 -> frames.json + indexed sheet for tools/import_flier_sheet.py. Assembles only: the hand-typed grids of
assets/flier/gum_mouth/frames_B.txt are copied, never redrawn. This script (1) shifts each grid down so its lowest art row
lands on FEET_ROW (the hanging poses end on row 21, the stand poses on row 18), (2) lays the frames out in the clip order
below, (3) writes the per frame gum offsets the bubble needs ("extra_tables" gum_dx / gum_dy / gum_show, see src/core/gum_view.c).
Usage: $PYTHON -I tools/import_gum_mouth_sheet.py && $PYTHON -I tools/import_flier_sheet.py assets/flier/gum_mouth/sheet/frames.json
Palettes (player, cpu, p2, distress1..3) come from assets/flier/gum_mouth/palettes.json. Palette letters of the grids:
"k123456789abcde" = palette indices 1..15 (9 a b = the cheek ramp, swapped for the three Gum Trip distress stages).
Clips (balloon-less model; the old balloon clips map onto these in src/main.c k_clips):
  flap    one shot per flap press         fly      steady flight loop (the sway)    settle  one shot on a turn in the air
  idle    steady with no balloons         pump     4 stages of the landing blow-up  inflate one shot on gaining a balloon
  fall / pop2 / pop1   dead and falling, balloon pops          walk / land / breathe  ground clips (stand poses)"""
import json, os, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "assets", "flier", "gum_mouth")
OUT = os.path.join(SRC, "sheet")
W, H, FEET = 24, 32, 31
CH = "k123456789abcde"
GRIP_COL = 12   # grid column the sprite centre (cx) sits on
BL = ["in", "rest", "puff", "puff", "puff", "rest"]
SWP = ["C", "R1", "R1", "R1", "R1", "C", "C", "L1", "L1", "L1", "L1", "C"]
POSE = {"C": {"in": "in", "rest": "rest", "puff": "puff"}, "R1": {"in": "R1", "rest": "R1", "puff": "R1p"},
        "L1": {"in": "L1", "rest": "L1", "puff": "L1p"}}


def settle():   # damped pendulum, first to the right; the facing flip mirrors it for a left turn (draw_gum_mouth_v4.py a_settle)
    first, o = "R", "L"
    a, b = "rest_f" + first.lower(), "rest_f" + o.lower()
    return [(first + "2", 5), (first + "1", 2), (a, 2), (o + "1", 2), (o + "2", 4), (o + "1", 2), (b, 2), (first + "1", 5),
            (a, 3), (o + "1", 4), (b, 4), (first + "1", 3), (a, 3), (b, 3), ("rest", 18)]


CLIPS = [  # (name, loop, [(frame, ticks)])
    ("flap", 0, [("f1", 2), ("f2", 2), ("f3", 2), ("f4", 3), ("f4", 2), ("d1", 2), ("d2", 2), ("blast", 3), ("puff", 4), ("puff", 4),
                 ("rest", 4), ("rest", 4), ("rest", 10)]),
    ("fly", 1, [(POSE[SWP[i]][BL[i % 6]], 5) for i in range(12)]),
    ("settle", 0, settle()),
    ("idle", 1, [(n, 6) for n in BL]),
    ("pump", 0, [("stand_in", 6), ("stand_puff", 4), ("stand_blast", 5), ("stand_puff", 5)]),
    ("inflate", 0, [("in", 4), ("puff", 4), ("blast", 4), ("puff", 4)]),
    ("fall", 1, [("strain", 6), ("burst", 6)]),
    ("pop2", 0, [("strain", 4), ("burst", 4)]),
    ("pop1", 0, [("strain", 4), ("burst", 4), ("burst", 6)]),
    ("walk", 1, [("stand_in", 6), ("stand_puff", 6)]),
    ("land", 0, [("stand_blast", 4), ("stand_puff", 4)]),
    ("breathe", 1, [("stand_in", 6), ("stand_puff", 4), ("stand_blast", 5), ("stand_puff", 4)]),
]


def load_frames():
    rows, grip, name = {}, {}, None
    for line in open(os.path.join(SRC, "frames_B.txt")):
        line = line.strip()
        if line.startswith("="):
            head = line.strip("= ").split("@")
            name = head[0].strip()
            rows[name], grip[name] = [], int(head[1])
        elif line and not line.startswith("#"):
            rows[name].append(line)
    for n, r in rows.items():
        if len(r) > H or any(len(x) != W or not set(x) <= set(CH + ".") for x in r):
            sys.exit("[ERROR] frame %s: bad grid" % n)
    return rows, grip


def main():
    rows, grip = load_frames()
    pals = json.load(open(os.path.join(SRC, "palettes.json")))
    seq = [(n, t) for _, _, fr in CLIPS for n, t in fr]
    cols = 8
    srows = -(-len(seq) // cols)
    img = Image.new("P", (cols * W, srows * H), 0)
    flat = []
    for p in pals["palettes"]["player"]:
        flat += p
    img.putpalette([0, 0, 0] + flat)
    px = img.load()
    gum_dx, gum_dy, gum_show = [], [], []
    hang_shift = FEET - max(i for i, r in enumerate(rows["rest"]) if set(r) - {"."})
    for n, (name, _) in enumerate(seq):
        r = rows[name]
        last = max(i for i, x in enumerate(r) if set(x) - {"."})
        shift = FEET - last
        ox, oy = (n % cols) * W, (n // cols) * H
        for y, line in enumerate(r):
            for x, c in enumerate(line):
                if c != ".":
                    px[ox + x, oy + y + shift] = CH.index(c) + 1
        gum_dx.append(grip[name] - GRIP_COL)
        gum_dy.append(shift - hang_shift)
        gum_show.append(0 if name in ("strain", "burst") else 1)   # the gum is gone in the pop poses
    img.save(os.path.join(OUT, "sheet.png"))
    anims, first = [], 0
    for name, loop, fr in CLIPS:
        anims.append(dict(name=name, first=first, count=len(fr), ticks=[t for _, t in fr], loop=bool(loop)))
        first += len(fr)
    meta = dict(sheet="sheet.png", frame_w=W, frame_h=H, sheet_cols=cols, sheet_rows=srows, tick_hz=60, feet_row=FEET,
                hit_box_columns=[10, 13], animations=anims,
                palette_player=pals["palettes"]["player"], palette_cpu=pals["palettes"]["cpu"],
                extra_palettes=pals["extra_palettes"], extra_tables={"gum_dx": gum_dx, "gum_dy": gum_dy, "gum_show": gum_show})
    json.dump(meta, open(os.path.join(OUT, "frames.json"), "w"), indent=1)
    print("[OK] %d frames, %d clips, hanging shift %d (GUM_BIRD_ROW = grip row 2 + shift + 2 = %d)" % (len(seq), len(CLIPS), hang_shift, hang_shift + 4))


if __name__ == "__main__":
    main()
