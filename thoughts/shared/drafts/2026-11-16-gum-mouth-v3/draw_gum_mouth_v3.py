#!/usr/bin/env python3
"""Gum-in-mouth Sootling drafts, round 3 (2026-11-16). DRAFT ONLY, nothing here is imported by the game.

Every frame in frames_B.txt is a complete hand-typed 24 x 32 pixel grid (one body per pose, no layered
patches, no rotation or drawing code). This script only reads the grids, mirrors, palette-maps, places the accepted
in-game gum cells (assets/gum/gum_sheet.png) on the grip point, packs strips / GIFs and counts tiles.
Helpers (paint, bubble, tiles, on_bg) are reused from ../2026-11-16-gum-mouth/draw_gum_mouth.py.
Palette letters: k outline, 1..5 feathers dark to light, 6 7 8 beak / feet / wing, 9 a b CHEEK red ramp (was the
string ramp; the string is gone), c d gum pink (the bitten gum lip), e white. 15 colours + transparent.
Gum Trip distress = palette swap of 9 a b only.
Run: python3.14 -I draw_gum_mouth_v3.py [--check NAME ...]
"""
import os, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "../2026-11-16-gum-mouth"))
import draw_gum_mouth as v1

CHEEK = {0: [(165, 41, 57), (231, 90, 74), (255, 156, 123)], 1: [(181, 24, 33), (247, 57, 41), (255, 123, 90)],
         2: [(156, 8, 24), (231, 33, 24), (255, 99, 66)], 3: [(132, 0, 41), (214, 16, 33), (255, 74, 57)]}
assert all(v in v1.GRID for s in CHEEK.values() for c in s for v in c)
GRIP = (12, 2)          # cell pixel where the beak bites the gum: the bubble's bottom centre sits here in every frame
W, H, CX, CY = 48, 72, 12, 38


def palette(pal, stage=0):
    p = list(v1.PAL[pal])
    return p[:9] + CHEEK[stage] + [p[11], p[12], p[14]]


def load(take):
    """frames_<take>.txt: '= name @grip_column', then full 24-wide rows. Prints every bad row, then stops."""
    out, grip, name, rows, bad = {}, {}, None, [], []
    for line in open(os.path.join(HERE, "frames_%s.txt" % take)).read().split("\n") + ["="]:
        line = line.strip()
        if line.startswith("="):
            if name:
                if len(rows) > 32 or name in out: bad.append((name, "rows", len(rows)))
                bad += [(name, i, len(r), r) for i, r in enumerate(rows) if len(r) != 24 or not set(r) <= set(v1.CH + ".")]
                out[name] = tuple(rows + ["." * 24] * (32 - len(rows)))
            head, rows = line.strip("= ").split("@"), []
            name = head[0].strip()
            if len(head) > 1: grip[name] = int(head[1])
        elif line and not line.startswith("#"): rows.append(line)
    for b in bad: print("BAD", b)
    assert not bad
    return out, grip


F, G = {}, {}
for t in "AB":
    if os.path.exists(os.path.join(HERE, "frames_%s.txt" % t)): F[t], G[t] = load(t)
USED = {}
GX = 12                 # canvas column (inside the 24 box at CX) where the grip point always sits


def frame(take, name, level=10, wob=0, pal="p1", stage=0, flip=False, dx=0, dy=0, anim=None):
    """One picture: the in-game gum cell with its bottom centre on the grip point, the typed bird cell on top."""
    if anim and pal == "p1": USED.setdefault(anim, set()).add(name)
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bird = v1.paint(F[take][name], palette(pal, stage))
    g = G[take][name]
    if flip: bird = bird.transpose(Image.FLIP_LEFT_RIGHT); g = 23 - g
    if level:
        b = v1.bubble(level, wob, pal, stage)
        out.alpha_composite(b, (CX + GX + dx - b.width // 2, CY + dy + GRIP[1] + 2 - b.height))
    out.alpha_composite(bird, (CX + GX + dx - g, CY + dy))
    return out


def sheet(frames, path, scale):
    s = Image.new("RGBA", (W * len(frames), H), (0, 0, 0, 0))
    for i, f in enumerate(frames): s.alpha_composite(f, (W * i, 0))
    v1.on_bg(s, scale).save(path)


def gif(frames, path, scale=4):
    ims = [v1.on_bg(f, scale) for f, _ in frames]
    ims[0].save(path, save_all=True, append_images=ims[1:], duration=[max(20, round(t * 1000 / 60)) for _, t in frames], loop=0, disposal=1)


T = "B"
BL = ["in", "rest", "puff", "puff", "puff", "rest"]      # one breath of the constant blow loop
LV = [0, 0, 1, 2, 1, 0]                                   # bubble level pulse per breath
SWP = ["C", "R1", "R1", "R1", "R1", "C", "C", "L1", "L1", "L1", "L1", "C"]
POSE = {"C": {"in": "in", "rest": "rest", "puff": "puff"}, "R1": {"in": "R1", "rest": "R1", "puff": "R1p"},
        "L1": {"in": "L1", "rest": "L1", "puff": "L1p"}}


def a_idle(pal="p1", stage=0, flip=False, anim="idle", tick=6, names=BL, jit=(0,)):
    return [(frame(T, names[i % 6], 10 + LV[i % 6], i, pal, stage, flip, dx=jit[i % len(jit)], anim=anim), tick) for i in range(12)]


def a_fly(pal="p1", flip=False, anim="fly"):
    return [(frame(T, POSE[SWP[i]][BL[i % 6]], 10 + LV[i % 6], i, pal, 0, flip, anim=anim), 5) for i in range(12)]


def a_settle(first="R"):   # pushed to one side, then a damped pendulum: big, smaller, smaller, still
    o = {"R": "L", "L": "R"}[first]
    seq = [(first + "2", 5), (first + "1", 2), ("rest", 2), (o + "1", 2), (o + "2", 4), (o + "1", 2), ("rest", 2),
           (first + "1", 5), ("rest", 3), (o + "1", 4), ("rest", 4), (first + "1", 3), ("rest", 24)]
    return [(frame(T, n, 10, i, anim="settle"), t) for i, (n, t) in enumerate(seq)]


def a_flap():   # wings sweep up over four frames while it inhales, then snap down through two frames with the blow
    seq = [("f1", 10, 2, 0), ("f2", 10, 2, 0), ("f3", 10, 2, 1), ("f4", 10, 3, 1), ("f4", 10, 2, 2), ("d1", 11, 2, 0),
           ("d2", 12, 2, -2), ("blast", 13, 3, -4), ("puff", 12, 4, -5), ("puff", 11, 4, -4), ("rest", 10, 4, -2),
           ("rest", 10, 4, -1), ("rest", 10, 10, 0)]
    return [(frame(T, n, lv, i, dy=dy, anim="flap"), t) for i, (n, lv, t, dy) in enumerate(seq)]


def a_landing():
    out = []
    for k in range(5):
        out += [(frame(T, "stand_in", 1 + 2 * k, k, dy=2, anim="landing"), 6), (frame(T, "stand_puff", 2 + 2 * k, k, dy=2, anim="landing"), 4),
                (frame(T, "stand_blast", min(10, 3 + 2 * k), k, dy=2, anim="landing"), 5)]
    return out + [(frame(T, "rest", 10, i, dy=dy, anim="landing"), t) for i, (dy, t) in enumerate([(1, 4), (-1, 4), (-3, 5), (-4, 20)])]


def main():
    names = list(F[T])
    sv = lambda fr, n, sc: sheet([f for f, _ in fr] if isinstance(fr[0], tuple) else fr, os.path.join(HERE, n), sc)
    sv([frame(T, n, 4 if "stand" in n else 10) for n in names], "B_all_frames_4x.png", 4)
    sv([frame(T, n, 4 if "stand" in n else 10) for n in names], "B_all_frames_1x.png", 1)
    cur = []
    for i in (0, 62):
        c = Image.new("RGBA", (W, H), (0, 0, 0, 0)); c.alpha_composite(v1.current_frame(i), (CX, CY)); cur.append(c)
    sv(cur + [frame(T, n) for n in ("rest", "puff", "blast", "R2", "L2")], "B_compare_ingame_6x.png", 6)
    anims = {"idle": a_idle(), "fly": a_fly(), "settle_right": a_settle("R"), "settle_left": a_settle("L"), "flap": a_flap(),
             "landing": a_landing(), "distress1": a_idle(stage=1, anim="distress1", tick=5),
             "distress2": a_idle(stage=2, anim="distress2", tick=4, names=["in", "puff", "strain", "strain", "strain", "puff"]),
             "distress3": a_idle(stage=3, anim="distress3", tick=3, names=["strain", "burst", "burst", "burst", "burst", "strain"], jit=(0, 1, 0, -1)),
             "fly_mirrored": a_fly(flip=True, anim=None), "fly_cpu": a_fly("cpu", anim=None), "fly_p2": a_fly("p2", anim=None)}
    for n, fr in anims.items():
        gif(fr, os.path.join(HERE, "B_%s_4x.gif" % n)); sv(fr, "B_%s_2x.png" % n, 2)
    sv([frame(T, n, stage=s) for s in (0, 1, 2, 3) for n in ("rest", "puff")] + [frame(T, "strain", stage=2), frame(T, "burst", stage=3)],
       "B_distress_stages_6x.png", 6)
    tl = lambda ns: len(v1.tiles([F[T][n] for n in ns]))
    lines = ["Gum-mouth v3, round front hang (one take). Sprite box 24 x 32 = 4 tiles of 16 x 16 per frame.",
             "typed frames: %d   unique 16x16 tiles, all frames: %d (upper bound if no sharing: %d)" % (len(names), tl(names), 4 * len(names)),
             "mirrored facing (h-flip): 0 extra tiles", "distress stage 1-3 colour: palette swap of 3 entries (cheek ramp), 0 extra tiles", ""]
    lines += ["%-12s frames used: %-2d unique tiles: %-3d  (%s)" % (a, len(u), tl(u), " ".join(sorted(u))) for a, u in USED.items()]
    lines += ["", "cheek ramp per stage (palette entries 9 a b): " + str(CHEEK)]
    open(os.path.join(HERE, "numbers.txt"), "w").write("\n".join(lines) + "\n"); print("\n".join(lines))


if "--check" in sys.argv:   # quick look: named frames of every take next to the in-game flier
    names = sys.argv[sys.argv.index("--check") + 1:-1]
    fr = []
    for i in (0, 62):
        c = Image.new("RGBA", (W, H), (0, 0, 0, 0)); c.alpha_composite(v1.current_frame(i), (CX, CY)); fr.append(c)
    for t in F:
        fr += [frame(t, n, 10 if "stand" not in n else 4) for n in (names or F[t]) if n in F[t]]
    sheet(fr, sys.argv[-1], 6); sys.exit()

if __name__ == "__main__": main()
