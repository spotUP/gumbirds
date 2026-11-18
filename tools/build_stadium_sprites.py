#!/usr/bin/env python3
"""Stadium (ground events) sprite set: every unique 16 x 16 tile of the approved hand-pixeled stand art in
assets/stadium/ (draw_stadium.py + draw_polish.py) -> a one-frame-per-tile sheet + json in --out
-> build/gen/stadium.c1/.c2, stadium_sprites.h/.c, stadium_tables.h (via tools/sprite_pipeline.py).
Usage: $PYTHON -I tools/build_stadium_sprites.py [--out build/gen] [--report]
Tile data is drawn with ONE global char -> palette index map (sorted chars), so a tile is shared by every mood, team and
variant; the look is the palette: extra palette "<mood>_t<team>_v<var>_<near|far>" (S.pal). Owner decisions: the storm far
crowd has no umbrellas (S.FU empty), so storm far cells are the dry far cells with the storm palette.
Frame order: the tile list printed by --report (stand_tiles -> frame k = tile k). The stand tables (which frame sits in
which cell, per mood/mode/frame) are emitted into stadium_cells.h by this script too."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "assets", "stadium"))
import draw_fling_field as FF
FF.BIRD = os.path.join(os.path.dirname(HERE), "assets", "flier", "sootling_sheet.png")
import draw_stadium as S
import draw_polish as P
from PIL import Image
import sprite_pipeline

S.FU = set()                                   # owner decision: no far umbrellas
BL = P.BLANK


def grids(mood):
    """Every unique non-blank tile of one mood, by class."""
    near, far = set(), set()
    for mode in S.MODES:
        for f in range(S.NFR[mode]):
            for r in range(3):
                for c in range(21):
                    near |= set(P.near_tiles(mood, mode, f, r, c))
            for r in range(2):
                for c in range(21):
                    far |= set(P.far_tiles(mood, mode, f, r, c))
    S.USED.clear()
    P._STRUCT.pop(mood, None)
    P.struct_plane(mood)
    P.near_plane(mood, "idle", 0)
    struct = set().union(*(v for k, v in S.USED.items() if k[1] in ("struct", "digit")))
    for line in P.scoreboard():
        struct |= {g for g, _, _ in line}
    struct |= {S.HEAD, S.MAST} | {P.digit(n) for n in range(10)}
    light = (set(P.GLOW.values()) | set(P.SH.values())) if mood == "dusk" else set()
    return {"near": near - {BL}, "far": far - {BL}, "struct": struct - {BL} - light, "light": light}


def main():
    out = "build/gen"
    for i, a in enumerate(sys.argv):
        if a == "--out" and i + 1 < len(sys.argv):
            out = sys.argv[i + 1]
    per = {m: grids(m) for m in S.MOODS}
    # two char -> index maps (a palette is chosen per cell anyway): crowd tiles (near + far birds) and structure tiles
    crowd = sorted(set().union(*(m[k] for m in per.values() for k in ("near", "far"))))
    struct = sorted(set().union(*(m["struct"] for m in per.values())) - set(crowd))
    light = sorted(set().union(*(m["light"] for m in per.values())) - set(crowd) - set(struct))
    cch = sorted({c for g in crowd for r in g for c in r} - {"."})
    sch = sorted({c for g in struct for r in g for c in r} - {"."})
    lch = sorted({c for g in light for r in g for c in r} - {"."})
    for nm, cs in (("crowd", cch), ("struct", sch), ("light", lch)):
        if len(cs) > 15:
            raise SystemExit("[ERROR] %s tile art uses %d chars, hardware limit 15: %s" % (nm, len(cs), "".join(cs)))
    maps = {"crowd": {c: i + 1 for i, c in enumerate(cch)}, "struct": {c: i + 1 for i, c in enumerate(sch)},
            "light": {c: i + 1 for i, c in enumerate(lch)}}
    refc = [FF.snap((8 * (i + 1) % 256, 255 - 8 * i, 8 * (i * 7 % 31))) for i in range(15)]
    assert len(set(refc)) == 15
    allt = [(g, "crowd") for g in crowd] + [(g, "struct") for g in struct] + [(g, "light") for g in light]
    sheet = Image.new("RGBA", (16 * len(allt), 16), (0, 0, 0, 0))
    for k, (g, cl) in enumerate(allt):
        for j, row in enumerate(g):
            for i, ch in enumerate(row):
                if ch != ".":
                    sheet.putpixel((16 * k + i, j), refc[maps[cl][ch] - 1] + (255,))
    pal0 = [list(c) for c in refc]
    extra = {}
    for mood in S.MOODS:
        for team in (0, 1):
            for var in (0, 1, 2):
                for far in (False, True):
                    p = S.pal(mood, team, var, far)[0]
                    extra["%s_t%d_v%d_%s" % (mood, team, var, "far" if far else "near")] = [list(p[c]) for c in cch] + [[0, 0, 0]] * (15 - len(cch))
            for far in (False, True):
                p = S.pal(mood, team, 0, far)[0]
                extra["%s_t%d_struct_%s" % (mood, team, "far" if far else "near")] = [list(p[c]) for c in sch] + [[0, 0, 0]] * (15 - len(sch))
        if mood == "dusk":      # sun, glow and the long turf shadow; '#' is the shadow mesh, drawn in the dark outline colour
            p = S.pal(mood, 0, 0, False)[0]
            extra["dusk_light"] = [list(p.get(c, p["K"])) for c in lch] + [[0, 0, 0]] * (15 - len(lch))
    anims = {"stand": [dict(x=16 * k, y=0, w=16, h=16) for k in range(len(allt))]}
    meta = dict(animations=anims, palettes=dict(stand=pal0), extra_palettes=extra,
                defines=dict(stand_tiles=len(allt), crowd_tiles=len(crowd)))
    os.makedirs(out, exist_ok=True)
    sp, mp = os.path.join(out, "stadium_sheet.png"), os.path.join(out, "stadium_sheet.json")
    sheet.save(sp)
    json.dump(meta, open(mp, "w"))
    cls = lambda m, k: per[m][k]
    for m in S.MOODS:
        print("[INFO] %-5s struct %3d near %3d far %3d  total(unique) %3d" % (m, len(cls(m, "struct")), len(cls(m, "near")),
              len(cls(m, "far")), len(set().union(*per[m].values()))), file=sys.stderr)
    print("[INFO] all moods: %d crowd + %d struct = %d unique tiles; crowd chars %s struct chars %s" % (len(crowd), len(struct), len(allt), "".join(cch), "".join(sch)), file=sys.stderr)
    if "--report" in sys.argv:
        return
    sys.argv = [a for a in sys.argv if a not in ("--out", out, "--report")] + ["--out", out]
    sprite_pipeline.main("stadium", sp, mp)


if __name__ == "__main__":
    main()
