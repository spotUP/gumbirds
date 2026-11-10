#!/usr/bin/env python3
"""Island sprite set checks (plan 2026-11-10-islands-build-plan.md I1..I3). Run: $PYTHON -I tests/host/test_islands.py
For every look (moon/roof, dusk/garden, storm/deck) the importer writes a sheet into a scratch folder, the sprite pipeline builds it,
and the generated header and tables are checked: tile count, at most 15 colours plus transparent, swap groups of 8 tiles that start
on a multiple of 8, and the tile range of the island set (base derived like src/vram_layout.h) not overlapping the obstacle, city,
Sootling and hazard ranges. build/gen/*_sprites.h must exist (gmake first)."""
import json, os, re, subprocess, sys, tempfile
sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import import_islands_sheet as imp

FAILS = []


def check(ok, msg):
    print(("[OK] " if ok else "[FAIL] ") + msg)
    if not ok:
        FAILS.append(msg)


def define(path, name):
    return int(re.search(r"#define %s (\d+)" % name, open(path).read()).group(1))


def mood_table(sheet_json):
    """I12: the island sheet the ROM is built from names a mood and a look; the mood must be the one built in SPRITE_BUDGET_MOODS
    (src/core/sprite_budget.c, the table the budget test reads) and the look the importer's table maps it to."""
    meta = json.load(open(sheet_json))
    src = open(os.path.join(ROOT, "src", "core", "sprite_budget.c")).read()
    table = src[src.index("SPRITE_BUDGET_MOODS[]"):]
    table = table[:table.index("};")]
    built = re.findall(r'\{\s*"(\w+)",\s*1\s*,', table)
    check(built == [meta["mood"]], "island sheet mood %r is the built mood in SPRITE_BUDGET_MOODS %r" % (meta["mood"], built))
    check(imp.LOOKS.get(meta["mood"]) == meta["look"], "island sheet look %r is the importer look of mood %r" % (meta["look"], meta["mood"]))


def main():
    gen = os.path.join(ROOT, "build/gen")
    sets = [("obs", "OBS"), ("city", "CITY"), ("sootling", "SOOTLING"), ("hazard", "HAZARD")]
    base, ranges = 256, {}  # logo 256 tiles, then the Makefile cat order
    for n, u in sets:
        c = define(os.path.join(gen, n + "_sprites.h"), u + "_TILE_COUNT")
        ranges[n] = (base, base + c)
        base += c
    check(base % 8 == 0, "island tile base %d is 8-aligned" % base)
    pal_slot = 2 + define(os.path.join(gen, "obs_sprites.h"), "OBS_PALETTE_COUNT") + define(os.path.join(gen, "city_sprites.h"), "CITY_PALETTE_COUNT") \
        + define(os.path.join(gen, "sootling_sprites.h"), "SOOTLING_PALETTE_COUNT") + define(os.path.join(gen, "hazard_sprites.h"), "HAZARD_PALETTE_COUNT")
    for mood, look in imp.LOOKS.items():
        with tempfile.TemporaryDirectory() as t:
            imp.build(mood, t)
            subprocess.run([sys.executable, "-I", os.path.join(ROOT, "tools/build_island_sprites.py"), "--sheet", os.path.join(t, "island_sheet.png"),
                            "--meta", os.path.join(t, "island_sheet.json"), "--out", t], check=True, cwd=ROOT, stdout=subprocess.DEVNULL)
            h = os.path.join(t, "island_sprites.h")
            src = open(os.path.join(t, "island_sprites.c")).read()
            tiles = define(h, "ISLAND_TILE_COUNT")
            check(define(h, "ISLAND_PALETTE_COUNT") == 1, "%s: one palette" % look)
            words = re.findall(r"\{ (0x[0-9a-f]{4}(?:, 0x[0-9a-f]{4}){15}) \}", src)[0].split(", ")
            ncol = sum(1 for w in words[1:] if w != "0x0000")
            check(words[0] == "0x8000" and 1 <= ncol <= 15, "%s: palette has %d colours plus transparent (max 15)" % (look, ncol))
            check(tiles % 8 == 0, "%s: %d tiles (multiple of 8)" % (look, tiles))
            check(base + tiles <= 2097152 // 64, "%s: island tiles end at %d, inside the 2 MiB C-ROM" % (look, base + tiles))
            idx = {}
            for m in re.finditer(r"/\* (\w+) (\d+) \*/ ([\d, ]+),", src.split("island_tile_index")[1].split("};")[0]):
                idx.setdefault(m.group(1), []).append(int(m.group(3)))  # one tile per frame (thin pieces)
            meta = json.load(open(os.path.join(t, "island_sheet.json")))
            groups = meta["groups"]
            check(len(groups) == sum(meta["tables"]["swap"]) and len(groups) >= 1, "%s: %d swapping positions %s" % (look, len(groups), sorted(groups)))
            for g in groups:
                f = idx[g]
                check(len(f) == 8 and f[0] % 8 == 0 and f == list(range(f[0], f[0] + 8)), "%s: group %s is 8 tiles from %d (aligned)" % (look, g, f[0]))
            lo = base
            check(max(v for fl in idx.values() for v in fl) < tiles and not any(a < lo + tiles and lo < b for a, b in ranges.values()),
                  "%s: tiles %d..%d do not overlap obstacle/city/Sootling/hazard %s" % (look, lo, lo + tiles, ranges))
            if look == "roof":
                check(tiles == 24, "roof: exactly 24 tiles (blank + 5 static, pad to 8, 2 groups of 8)")
            print("     %s: tiles=%d groups=%s palette slot %d" % (look, tiles, sorted(groups), pal_slot))
    mood_table(os.path.join(ROOT, "assets", "islands", "island_sheet.json"))
    print("[FAIL] island checks failed" if FAILS else "[OK] island checks passed")
    sys.exit(1 if FAILS else 0)


main()
