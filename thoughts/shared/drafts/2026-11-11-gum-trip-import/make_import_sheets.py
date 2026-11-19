#!/usr/bin/env python3
"""Gum Trip art import prep: converts the approved drafts into sheets + json in the layout
tools/sprite_pipeline.py expects. Reads the draft folders, never writes to them.

Run: /opt/homebrew/bin/python3.14 -I thoughts/shared/drafts/2026-11-11-gum-trip-import/make_import_sheets.py

Writes into this folder:
  tripstrip_sheet.png/.json   strip C unique tiles (one animation per tile, 16x16 frames)
  tripstrip_map.json          tile role, flip bits and the draft course map, measured rim gaps
  hazards_sheet.png/.json     final3 cloud, vent, coal stacked (animations cloud, vent, coal)
  pickup_sheet.png/.json      pickup A idle (16 x 24x24) and collect (8 x 32x32)
  meter_tiles_idx.png         13 meter tiles as palette-indexed 8x8 cells (white fix palette indices)
  meter_tiles.json            tile names, fix palette name, index data
  rival_palettes.json         Hornet, Bone, Bruiser palettes snapped to the 5-bit grid, with deltas
  report.txt                  numbers printed by this script
"""
import sys
sys.dont_write_bytecode = True
import importlib.util, json, os
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
DR = os.path.join(ROOT, "thoughts", "shared", "drafts")
OUT = []


def say(s=""):
    OUT.append(s)
    print(s)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def to5(v):
    return round(v * 31 / 255)


def expand5(f):
    return (f << 3) | (f >> 2)


def snap(c):
    return tuple(expand5(to5(v)) for v in c)


def on_grid(c):
    return tuple(c) == snap(c)


def save_json(name, obj):
    with open(os.path.join(HERE, name), "w") as f:
        json.dump(obj, f, indent=1)
        f.write("\n")


# ---------------------------------------------------------------- strip C
def strip_c():
    ks = load("kill_strip", os.path.join(DR, "2026-11-11-gum-trip-kill-strip", "draw_kill_strip.py"))
    G = ks.geometry(ks.CHUNKS)
    win = ~G["band"]
    F = ks.FRAMES["C"]
    frames = np.stack([ks.paint_C(G, f) for f in range(F)]).astype(np.uint8)
    frames[:, win] = 0
    tiles, tmap, first, rebuilt, _ = ks.cut(frames, G)
    assert (rebuilt == frames).all()
    pal = ks.PAL["C"]
    used = sorted(set(np.unique(frames)) - {0})
    cols = [tuple(int(v) for v in pal[i]) for i in range(1, max(used) + 1)]
    assert all(on_grid(c) for c in cols), "strip C palette off the 5-bit grid"
    say("strip C: %d colours used (indices %s), all on the 5-bit grid" % (len(used), [int(u) for u in used]))

    # tile kinds
    kind, role_of = [], {}
    for (r, c), (i, hf, vf) in tmap.items():
        role_of.setdefault(i, set()).add(ks.role(G, r, c).split()[1])
    for i, t in enumerate(tiles):
        anim = not all((t[k] == t[0]).all() for k in range(F))
        a4 = anim and all((t[k] == t[k + 4]).all() for k in range(4))
        kind.append(4 if a4 else (8 if anim else 1))
    anims, groups, rows = {}, {}, []
    sheet_w, sheet_h = 16 * 8, 16 * len(tiles)
    img = np.zeros((sheet_h, sheet_w, 4), np.uint8)
    names = []
    for i, t in enumerate(tiles):
        n = kind[i]
        rl = sorted(role_of[i])
        name = "t%d_%s" % (i, "_".join(rl))
        names.append(name)
        anims[name] = [{"x": 16 * k, "y": 16 * i, "w": 16, "h": 16} for k in range(n)]
        if n > 1:
            groups[name] = n
        for k in range(n):
            ix = t[k]
            for y in range(16):
                for x in range(16):
                    v = int(ix[y, x])
                    if v:
                        img[16 * i + y, 16 * k + x] = (*cols[v - 1], 255)
    Image.fromarray(img, "RGBA").save(os.path.join(HERE, "tripstrip_sheet.png"))
    cost = sum(kind)
    cost_all8 = sum(1 if k == 1 else 8 for k in kind)
    save_json("tripstrip_sheet.json", {
        "source": "thoughts/shared/drafts/2026-11-11-gum-trip-import/tripstrip_sheet.png, cut by make_import_sheets.py from draw_kill_strip.py variant C",
        "palette_policy": "merge",
        "groups": groups,
        "palettes": {"gum": [list(c) for c in cols]},
        "defines": {"STEP_TICKS": ks.TICKS["C"], "LOOP_FRAMES": F, "PERIOD_PX": 64, "TILE_COUNT": len(tiles)},
        "tables": {"tile_frames": kind},
        "animations": anims,
    })
    say("strip C: %d unique tiles, frames per tile %s, ROM tiles with mixed 4/8 groups = %d, all 8-frame = %d"
        % (len(tiles), kind, cost, cost_all8))
    say("strip C tile names: %s" % names)

    # measured rim gap per edge
    gaps = {"floor": [], "ceiling": []}
    ft, cb = G["ft"], G["cb"]
    for col in range(len(ft)):
        flat_f = all(0 <= k < len(ft) and ft[k] == ft[col] for k in (col - 1, col, col + 1))
        flat_c = all(0 <= k < len(cb) and cb[k] == cb[col] for k in (col - 1, col, col + 1))
        for x in range(16 * col, 16 * col + 16):
            for f in range(F):
                y0 = 16 * ft[col]
                if flat_f:
                    nz = np.nonzero(frames[f, y0:y0 + 16, x])[0]
                    gaps["floor"].append(int(nz[0]) if len(nz) else 16)
                y1 = 16 * cb[col]
                if flat_c:
                    nz = np.nonzero(frames[f, y1 - 16:y1, x])[0]
                    gaps["ceiling"].append(15 - int(nz[-1]) if len(nz) else 16)
    meas = {}
    for e, g in gaps.items():
        g = np.array(g)
        meas[e] = {"min": int(g.min()), "max": int(g.max()), "mean": round(float(g.mean()), 2), "samples": int(len(g))}
        say("strip C rim gap %s (rows of empty before first art row, flat columns, all frames): min %d max %d mean %.2f"
            % (e, g.min(), g.max(), g.mean()))
    gmin = {e: meas[e]["min"] for e in meas}
    save_json("tripstrip_map.json", {
        "note": "tile index = animation order in tripstrip_sheet.json; hflip/vflip are the LSPC tile flip bits used in the draft",
        "chunks_ceiling_floor_tile_rows": [list(c) for c in ks.CHUNKS],
        "tile_roles": {names[i]: sorted(role_of[i]) for i in range(len(tiles))},
        "frames_per_tile": kind,
        "draft_course_map": {"%d,%d" % rc: {"tile": v[0], "hflip": v[1], "vflip": v[2]} for rc, v in sorted(tmap.items())},
        "rim_gap": meas,
        "y_offset_rule": {
            "floor_sprite_y": "win_bottom - %d" % gmin["floor"],
            "ceiling_sprite_bottom": "win_top + %d" % gmin["ceiling"],
            "why": "hurt when flier bottom >= win_bottom (floor) or flier top <= win_top-1 (ceiling), src/core/trip_hit.c:44; shifting by the minimum gap puts the highest art row on the hurt line, no art enters the window",
        },
    })


# ---------------------------------------------------------------- hazards final3
def hazards():
    d = os.path.join(DR, "2026-11-10-gum-trip-moving-hazard-final3")
    names = {"a": "cloud", "b": "vent", "c": "coal"}
    ims = {k: Image.open(os.path.join(d, "sheet_%s_1x.png" % k)).convert("RGBA") for k in "abc"}
    js = {k: json.load(open(os.path.join(d, "sheet_%s.json" % k))) for k in "abc"}
    W = max(i.width for i in ims.values())
    H = sum(i.height for i in ims.values())
    sheet = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    y = 0
    anims, defines, tables, pals, boxes = {}, {}, {}, {}, {}
    for k in "abc":
        n = names[k]
        sheet.paste(ims[k], (0, y))
        src = js[k]
        an = src["animations"]
        assert len(an) == 1, list(an)
        fr = list(an.values())[0]
        anims[n] = [{"x": r["x"], "y": r["y"] + y, "w": r["w"], "h": r["h"]} for r in fr]
        for dk, dv in src["defines"].items():
            defines["%s_%s" % (n.upper(), dk)] = dv
        for tk, tv in src["tables"].items():
            tables["%s_%s" % (n, tk)] = tv
        for pn, pv in src["palettes"].items():
            if pn in pals:
                assert pals[pn] == pv
            pals[pn] = pv
        boxes[n] = src["hitbox"]
        a = np.array(ims[k])
        assert set(np.unique(a[:, :, 3])) <= {0, 255}
        y += ims[k].height
    sheet.save(os.path.join(HERE, "hazards_sheet.png"))
    save_json("hazards_sheet.json", {
        "source": "thoughts/shared/drafts/2026-11-10-gum-trip-moving-hazard-final3 sheet_a/b/c stacked by make_import_sheets.py",
        "palette_policy": "subset",
        "palettes": pals,
        "defines": defines,
        "tables": tables,
        "hitbox": boxes,
        "animations": anims,
    })
    say("hazards: sheet %dx%d, anims %s, palettes %s, hitboxes %s"
        % (W, H, {n: len(anims[n]) for n in anims}, {p: len(v) for p, v in pals.items()}, boxes))
    for p, v in pals.items():
        assert all(on_grid(c) for c in v), p


# ---------------------------------------------------------------- pickup A
def pickup():
    d = os.path.join(DR, "2026-11-10-gum-trip-pickup-rival")
    idle = np.array(Image.open(os.path.join(d, "pickup_a_sheet_1x.png")).convert("RGB"))
    coll = np.array(Image.open(os.path.join(d, "pickup_a_collect_sheet_1x.png")).convert("RGB"))
    key = np.array([255, 0, 255])
    W = max(idle.shape[1], coll.shape[1])
    H = idle.shape[0] + coll.shape[0]
    out = np.zeros((H, W, 4), np.uint8)
    cols = set()
    for im, oy in ((idle, 0), (coll, idle.shape[0])):
        mask = ~(im == key).all(axis=2)
        out[oy:oy + im.shape[0], :im.shape[1], :3][mask] = im[mask]
        out[oy:oy + im.shape[0], :im.shape[1], 3][mask] = 255
        cols |= {tuple(int(v) for v in c) for c in im[mask]}
    cols = sorted(cols, key=lambda c: sum(c))
    off = [c for c in cols if not on_grid(c)]
    say("pickup A: union %d colours (limit 15), %d off the 5-bit grid, snapped below" % (len(cols), len(off)))
    smap = {c: snap(c) for c in cols}
    delta = max(abs(a - b) for c, s in smap.items() for a, b in zip(c, s))
    for y in range(out.shape[0]):
        for x in range(out.shape[1]):
            if out[y, x, 3]:
                out[y, x, :3] = smap[tuple(int(v) for v in out[y, x, :3])]
    cols = sorted(set(smap.values()), key=lambda c: sum(c))
    say("pickup A: after 5-bit snap %d colours, max channel delta %d" % (len(cols), delta))
    Image.fromarray(out, "RGBA").save(os.path.join(HERE, "pickup_sheet.png"))
    save_json("pickup_sheet.json", {
        "source": "thoughts/shared/drafts/2026-11-10-gum-trip-pickup-rival pickup_a_sheet_1x + pickup_a_collect_sheet_1x, magenta key to alpha 0",
        "palette_policy": "subset",
        "palettes": {"pickup": [list(c) for c in cols]},
        "defines": {"PICKUP_IDLE_FRAMES": 16, "PICKUP_IDLE_TICKS": 4, "PICKUP_COLLECT_FRAMES": 8, "PICKUP_COLLECT_TICKS": 4},
        "animations": {
            "pickup_idle": [{"x": 24 * i, "y": 0, "w": 24, "h": 24} for i in range(16)],
            "pickup_collect": [{"x": 32 * i, "y": idle.shape[0], "w": 32, "h": 32} for i in range(8)],
        },
    })
    say("pickup A: sheet %dx%d, idle 16 x 24x24, collect 8 x 32x32 (collect ticks unverified, draft numbers.txt says 8 in plan, check)" % (W, H))


# ---------------------------------------------------------------- meter tiles
def meter():
    d = os.path.join(DR, "2026-11-10-gum-trip-rival-meter-fix")
    im = np.array(Image.open(os.path.join(d, "meter_tiles_1x.png")).convert("RGB"))
    fj = json.load(open(os.path.join(ROOT, "assets", "font", "fix_font.json")))
    white = [tuple(c) for c in fj["palettes"]["white"]]
    lut = {c: i + 1 for i, c in enumerate(white)}   # palette index 1..15 (0 transparent); first listed is index 1 (unverified)
    n = im.shape[1] // 8
    idx = np.zeros((8, 8 * n), np.uint8)
    miss = set()
    for y in range(8):
        for x in range(8 * n):
            c = tuple(int(v) for v in im[y, x])
            if c == (255, 0, 255):
                continue
            if c in lut:
                idx[y, x] = lut[c]
            else:
                miss.add(c)
    pal = [(0, 0, 0)] + [tuple(c) for c in white]
    p = Image.fromarray(idx, "P")
    flat = []
    for c in pal:
        flat += list(c)
    p.putpalette(flat + [0] * (768 - len(flat)))
    p.save(os.path.join(HERE, "meter_tiles_idx.png"))
    save_json("meter_tiles.json", {
        "fix_palette": "white",
        "tiles": ["meter_%d" % i for i in range(n)],
        "tile_count": n,
        "target_fix_sheet_slots": "157..%d (free per assets/font/fix_font.json: 157 names, sheet 192 slots)" % (156 + n),
        "colour_not_in_white_palette": [list(c) for c in sorted(miss)],
        "used_indices": sorted(int(v) for v in np.unique(idx) if v),
    })
    say("meter: %d tiles 8x8, indices used %s, colours not in white palette: %s"
        % (n, sorted(int(v) for v in np.unique(idx) if v), sorted(miss)))


# ---------------------------------------------------------------- rivals
def rivals():
    pr = load("pickup_rival", os.path.join(DR, "2026-11-10-gum-trip-pickup-rival", "draw_pickup_rival.py"))
    out = {}
    for rid, name, note, pal in pr.RIVALS:
        snapped = [snap(c) for c in pal]
        delta = max(abs(a - b) for c, s in zip(pal, snapped) for a, b in zip(c, s))
        dup = len(snapped) - len(set(snapped))
        out[name.lower()] = {"id": rid, "note": note, "draft": [list(c) for c in pal],
                             "snapped_5bit": [list(c) for c in snapped], "max_channel_delta": delta,
                             "duplicates_after_snap": dup}
        say("rival %s %s: %d colours, off-grid in draft %d, max channel delta after snap %d, duplicates after snap %d"
            % (rid, name, len(pal), sum(not on_grid(c) for c in pal), delta, dup))
    save_json("rival_palettes.json", out)


if __name__ == "__main__":
    strip_c()
    hazards()
    pickup()
    meter()
    rivals()
    with open(os.path.join(HERE, "report.txt"), "w") as f:
        f.write("\n".join(OUT) + "\n")
