#!/usr/bin/env python3
"""Import of the approved trip cave art into assets/tripstrip/tripstrip_sheet.png + .json and the generated fade lookup
src/core/trip_cave_fade.h. Sources (repo root drafts): 2026-11-15-trip-cave-v3 (take 1 slate roof, floor F1 lip, eased S16/S32
curves), 2026-11-15-trip-cave-fade (flat fade rows: 1 fill row on the floor, 0 on the roof) and 2026-11-15-trip-cave-smoothfade
(sloped fade tiles under / above the curve pieces, fade_map lookup). Run by hand after a draft changes; the build only reads the
outputs.

The draft scripts are imported unchanged (build_smooth imports build_fade imports build_cave3), so the pixels are the drawn ones.
Two things are redirected while they load: the v3 script reads the gum palette, fill and rim from the shipped pre-cave sheet, which
is served from git (commit BASE), and draft-folder writes (build_cave3 rewrites its heights.json) go to os.devnull.
The sheet holds, in this animation order (palette 0 = gum floor, palette 1 = slate roof, merge policy):
  fill                 the shipped gum fill tile
  lip0..lip3           8-frame auto-animation groups: frame f = shipped t2_rim body frame (k + f) & 7 with F1 lip part k on rows 2-3
  floor_s16, floor_s32 8-frame groups of the rising floor curves (48x32, 48x48), the shipped fill composited under the band
  roof                 one animation so the slate shares one palette; frames: fill 64x16 (4 tiles), rim A 64x16, rim B 64x16,
                       solo 32x16 (2 tiles), falling curve S16 48x32, S32 48x48, fade A 64x16, fade B 64x16, black 16x16,
                       sloped fade tiles R0..Rn (one 16 px tile each, in a row)
  floor_fade           gum fade: fade A 32x16, fade B 32x16, solid darkest gum 16x16, sloped fade tiles F0..Fn in a row
Usage: python3 -I tools/import_trip_cave.py [--drafts DIR]"""
import argparse, builtins, io, json, os, subprocess, sys
from PIL import Image

BASE = "71724ee"   # commit whose assets/tripstrip sheet is the shipped pre-cave sheet the drafts were drawn against
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser()
ap.add_argument("--drafts", default=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(ROOT))), "thoughts/shared/drafts")
                if os.path.basename(os.path.dirname(ROOT)) == "worktrees" else os.path.join(ROOT, "thoughts/shared/drafts"))
a = ap.parse_args()
DRAFTS = os.path.realpath(a.drafts)
def git_blob(path): return subprocess.run(["git", "-C", ROOT, "show", "%s:%s" % (BASE, path)], check=True, capture_output=True).stdout
OLD_PNG, old = git_blob("assets/tripstrip/tripstrip_sheet.png"), json.loads(git_blob("assets/tripstrip/tripstrip_sheet.json"))

real_open, real_img_open = builtins.open, Image.open
def guarded_open(f, mode="r", *k, **kw):
    if isinstance(f, str) and any(c in mode for c in "wax+") and os.path.realpath(f).startswith(DRAFTS): f = os.devnull
    return real_open(f, mode, *k, **kw)
def sheet_open(f, *k, **kw):
    if isinstance(f, str) and f.endswith("assets/tripstrip/tripstrip_sheet.png"): return real_img_open(io.BytesIO(OLD_PNG))
    return real_img_open(f, *k, **kw)
builtins.open, Image.open = guarded_open, sheet_open
sys.path.insert(0, os.path.join(DRAFTS, "2026-11-15-trip-cave-smoothfade"))
try:
    import build_smooth as S
finally:
    builtins.open, Image.open = real_open, real_img_open
BF, B = S.BF, S.B
assert BF.N_FLOOR == 1 and BF.N_ROOF == 0 and BF.FADE_ROWS == 2   # the view code (trip_view.c) places these row counts

def strip(names, tiles, pal_img):
    """the sloped tiles F0..Fn / R0..Rn in a row, one 16 px tile each"""
    inv = {v: k for k, v in tiles.items()}
    out = Image.new("RGBA", (16 * len(names), 16), (0, 0, 0, 0))
    for n, nm in enumerate(names): out.paste(Image.frombytes("RGBA", (16, 16), inv[nm]), (16 * n, 0))
    return out
FN = ["F%d" % i for i in range(len(S.NEW["floor"]))]; RN = ["R%d" % i for i in range(len(S.NEW["roof"]))]
assert sorted(FN) == sorted(S.NEW["floor"].values()) and sorted(RN) == sorted(S.NEW["roof"].values())

sheet = B.sheet
t2 = old["animations"]["t2_rim"]
lip = B.img(B.V2.F1_LIP_ROWS, B.GUM)
anims, groups, place = {}, {}, []   # place: (image, x, y)
y = 0
def put(name, frames, group=None):
    global y
    rects, x = [], 0
    for im in frames:
        place.append((im, x, y)); rects.append({"x": x, "y": y, "w": im.width, "h": im.height}); x += im.width
    anims[name] = rects
    if group: groups[name] = group
    y += max(im.height for im in frames)

put("fill", [B.ffill])
for k in range(4):
    fr = []
    for f in range(8):
        r = t2[(k + f) & 7]
        t = sheet.crop((r["x"], r["y"], r["x"] + 16, r["y"] + 16)).copy()
        t.paste((0, 0, 0, 0), (0, 0, 16, 4))
        t.paste(lip.crop((16 * k, 0, 16 * k + 16, 2)), (0, 2))
        fr.append(t)
    put("lip%d" % k, fr, 8)
put("floor_s16", B.floor16, 8)
put("floor_s32", B.floor32, 8)
solo = Image.new("RGBA", (32, 16), (0, 0, 0, 0)); solo.alpha_composite(B.solo[0], (0, 0)); solo.alpha_composite(B.solo[1], (16, 0))
put("roof", [B.fillI, B.rimA, B.rimB, solo, B.roof16, B.roof32, BF.ra, BF.rb, Image.new("RGBA", (16, 16), BF.BLACK),
             strip(RN, S.NEW["roof"], None)])   # one animation = one palette (slot 1); black is its 11th colour
put("floor_fade", [BF.fa, BF.fb, Image.new("RGBA", (16, 16), BF.GUM0), strip(FN, S.NEW["floor"], None)])

w = max(x + im.width for im, x, _ in place)
out = Image.new("RGBA", (w, y), (0, 0, 0, 0))
for im, x, yy in place: out.alpha_composite(im, (x, yy))
out.save(os.path.join(ROOT, "assets/tripstrip/tripstrip_sheet.png"))
meta = {
    "source": "thoughts/shared/drafts/2026-11-15-trip-cave-v3, -fade, -smoothfade (take 1 slate roof, F1 lip, S16/S32 curves, sloped fade),"
              " assembled by tools/import_trip_cave.py",
    "palette_policy": "merge",
    "groups": groups,
    "palettes": {"gum": old["palettes"]["gum"]},   # read by tools/build_splash_sprites.py for the gum splat (no animation here has that name)
    "defines": {"STEP_TICKS": old["defines"]["STEP_TICKS"], "LOOP_FRAMES": 8},
    "animations": anims,
}
json.dump(meta, open(os.path.join(ROOT, "assets/tripstrip/tripstrip_sheet.json"), "w"), indent=1)

# ---------------------------------------------------------------- fade lookup header
PIECE, FILL, END = -1, -2, -3
def codes(side, lst, kind):
    """floor: rows down from the piece top; roof: rows up from the piece bottom (the map lists it top first, from 2 rows above)"""
    prow = 2 if kind == "S16" else 3
    if side == "roof":
        assert len(lst) == prow + 2 and all(v not in ("piece", "empty") for v in lst[:2]), lst
        lst = lst[::-1]
    endw = "solid" if side == "floor" else "black"
    n = lst.index(endw) if endw in lst else len(lst)
    assert all(v == endw for v in lst[n:]), lst   # solid / black only past the last fade row
    res = []
    for i, v in enumerate(lst[:n]):
        if v in ("piece", "empty"): assert i < prow, lst; res.append(PIECE)
        elif v == "fill": assert side == "floor", lst; res.append(FILL)
        elif v[0] == ("F" if side == "floor" else "R") and v[1:].isdigit(): res.append(int(v[1:]))
        else: raise SystemExit("[ERROR] fade_map %s %s: unexpected entry %s" % (side, kind, v))
    return res
W = 8
tab = {s: [[codes(s, S.MAP[s]["%s_col%d" % (k, c)], k) for c in range(3)] for k in ("S16", "S32")] for s in ("floor", "roof")}
assert max(len(l) for s in tab.values() for k in s for l in k) <= W
def c_rows(s): return ",\n".join("    { " + ", ".join("{ " + ", ".join(str(v) for v in l + [END] * (W - len(l))) + " }" for l in k) + " }" for k in tab[s])
hdr = """/* Generated by tools/import_trip_cave.py from thoughts/shared/drafts/2026-11-15-trip-cave-smoothfade/fade_map.json. Do not edit.
 * Sloped fade of the cave curve pieces: [kind S16 0 / S32 1][unflipped piece column 0..2][row]. Floor rows count down from the
 * piece top, roof rows up from the piece bottom. TRIP_FADE_PIECE = the curve piece tile of that row, TRIP_FADE_FILL = the gum fill
 * tile, TRIP_FADE_END = this row and all past it are solid darkest gum (floor) / black (roof), n >= 0 = sloped fade tile n
 * (floor_fade frame TRIP_FLOOR_SLOPED cell n, roof frame TRIP_ROOF_SLOPED cell n, trip_view.h), hflipped with the piece. */
#ifndef TRIP_CAVE_FADE_H
#define TRIP_CAVE_FADE_H
#define TRIP_FADE_PIECE (-1)
#define TRIP_FADE_FILL  (-2)
#define TRIP_FADE_END   (-3)
#define TRIP_FADE_ROWS  %d
#define TRIP_FADE_FLOOR_TILES %d
#define TRIP_FADE_ROOF_TILES  %d
static const signed char trip_fade_floor[2][3][TRIP_FADE_ROWS] = {
%s
};
static const signed char trip_fade_roof[2][3][TRIP_FADE_ROWS] = {
%s
};
#endif
""" % (W, len(FN), len(RN), c_rows("floor"), c_rows("roof"))
real_open(os.path.join(ROOT, "src/core/trip_cave_fade.h"), "w").write(hdr)
print("[OK] sheet %dx%d, %d animations, %d floor + %d roof sloped tiles" % (w, y, len(anims), len(FN), len(RN)))
