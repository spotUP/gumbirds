#!/opt/homebrew/bin/python3.14 -I
"""Sootling walk cycle drafts (A 6 frames, B 8 frames, C 8 frames hop-walk) plus extras
(landing pair, idle breathing loop), 24 x 32 per frame.

Built on sheet_base.py, a verbatim copy of
thoughts/shared/drafts/2026-11-10-sootling-small-sheet/draw_sheet.py (the script that drew
assets/flier/sootling_sheet.png). Reused from it unchanged: palettes (read from
assets/flier/sootling_sheet.json, no new colours), the rest BODY grid, EYES, TUFT, BEAK,
WING grids, render(). New here, all hand-placed grids: a squash body (18 x 15) and a
stretch body (15 x 17) drawn as poses (not row removal), two walk wing poses (back, fwd),
walk feet with legs that pivot from hips inside the body, near foot lit, far foot dark.

Run: /opt/homebrew/bin/python3.14 -I draw_walk.py
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sheet_base as sb  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

FW, FH = sb.FW, sb.FH
SPEED = 1.4  # px per game frame on the ground, 60 Hz
PALS = sb.PALS
ROOT = sb.ROOT
SHEET_PNG = os.path.join(ROOT, "assets", "flier", "sootling_sheet.png")
SCRATCH = os.environ.get("WALK_CHECK_DIR")  # optional: write 8x check sheets here

# ------------------------------------------------------------------ new body poses
# Squash: 2 wider, 1 shorter, flatter top and a wider seat; light still upper left.
SQUASH = [
    "......kkkkkk......",
    "...kkkeeeddcckk...",
    "..keeeeeeddddcck..",
    ".keeeeedddddcccck.",
    "kdeeedddddddccccak",
    "kdeddcbbbbbbbbbaak",
    "kdddccbbbbbbbbbbak",
    "kddcccbbbbbbbbbbak",
    "kdcccbbbbbbbbbbaak",
    "kcccbbbbbbbabbaaak",
    "kccbbbbbabbaaaaaak",
    ".kcbbbabbaaaaaaak.",
    "..kbbabaaaaaaaak..",
    "...kkkaaaaaakkk...",
    "......kkkkkk......",
]
# Stretch: 1 narrower (at the back, the face keeps its columns), 1 taller, egg shape.
STRETCH = [
    ".....kkkkk.....",
    "...kkeeddckk...",
    "..keeeeddddck..",
    ".keeeedddddcck.",
    ".keedddddddcck.",
    "kdeddcbbbbbbaak",
    "kdddcbbbbbbbbak",
    "kddccbbbbbbbbak",
    "kdcccbbbbbbbaak",
    "kdccbbbbbbbbaak",
    "kcccbbbbbbbaaak",
    "kccbbbbbabbaaak",
    ".kcbbbabbaaaak.",
    ".kbbbabaaaaaak.",
    "..kbbabaaaaak..",
    "...kkaaaaakk...",
    ".....kkkkk.....",
]
# name: (grid, body x, eye row, eye col, tuft x)
BODIES = {
    "rest": (sb.BODY, 4, 4, 7, 4),
    "squash": (SQUASH, 3, 4, 8, 4),
    "stretch": (STRETCH, 5, 4, 6, 5),
}
WALK_WING = dict(sb.WING)
WALK_WING["back"] = (-4, 6, ["kkk......",
                             "kyykkkk..",
                             ".kyyooork",
                             "..koorrrk",
                             "...kkkkk."])
WALK_WING["fwd"] = (-2, 8, ["...kkkk.",
                            "..kyyork",
                            ".kyoorrk",
                            "kyoorrk.",
                            ".kkkkk.."])

# foot shapes: (dx, dy from the foot bottom row, part) part f = sole, t = toe
FOOT = {
    "flat": [(-1, 0, "f"), (0, 0, "f"), (1, 0, "t")],
    "heel": [(-1, 0, "f"), (0, 0, "f"), (1, -1, "t")],   # contact, toe still up
    "toe": [(0, 0, "f"), (1, 0, "t"), (-1, -1, "f")],    # push off, heel up
    "tuck": [(0, 0, "f"), (1, 0, "t")],                  # swinging, toes pointed
}
NEAR = {"leg": "r", "f": "o", "t": "y"}
FAR = {"leg": "r", "f": "r", "t": "o"}
PLANTED = ("flat", "heel", "toe")


def compose_walk(body="rest", L=0, dx=0, eyes="open", tuft="norm", tdy=0, wing="mid", wdy=0, wad=2, wady=0,
                 beak="shut", far=(9, 0, "flat"), near=(14, 0, "flat"), far_dark=True):
    """L = body lift (body bottom row 29 - L). far / near = (ankle col, foot lift, shape).
    returns (pixel dict, info)"""
    grid, bx0, erow, ecol, tx = BODIES[body]
    rows = [list(r) for r in grid]
    for i, er in enumerate(sb.EYES[eyes]):
        rows[erow + i][ecol:ecol + 7] = list(er)
    h, w = len(rows), len(rows[0])
    bottom = 29 - L
    top = bottom - h + 1
    bx = bx0 + dx
    px, info, clipped = {}, {}, []

    def dot(x, y, ch):
        if ch in ". ":
            return
        if not (0 <= x < FW and 0 <= y < FH):
            clipped.append((x, y, ch))
            return
        px[(x, y)] = ch

    def put(g, x0, y0):
        for y, row in enumerate(g):
            for x, ch in enumerate(row):
                dot(x0 + x, y0 + y, ch)

    mask = set()
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != ".":
                mask.add((bx + x, top + y))
    foot_px = []

    def leg_and_foot(foot, hipx, cols):
        col, lift, shape = foot
        fy = 31 - lift
        ankle = (col, fy - 1)
        for x, y in sb.line((hipx, bottom - 2), ankle):
            if (x, y) not in mask and y < fy:
                dot(x, y, cols["leg"])
        for fx, fdy, part in FOOT[shape]:
            dot(col + fx, fy + fdy, cols[part])
            foot_px.append((col + fx, fy + fdy))
            if (col + fx, fy + fdy) in mask:
                info.setdefault("foot_in_body", []).append((col + fx, fy + fdy))

    # far leg behind the body, then body, face, wing, near leg in front
    leg_and_foot(far, 11 + dx, FAR if far_dark else NEAR)
    for (x, y) in mask:
        pass
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            dot(bx + x, top + y, ch)
    tg = sb.TUFT[tuft]
    put(tg, tx + dx, top - (len(tg) - 1) + tdy)
    eye_top = top + erow
    vtop = eye_top - 4
    beak_x, beak_y = bx + w - 2, vtop + 8
    put(sb.BEAK[beak], beak_x, beak_y)
    if wad:
        wy = beak_y + 1 + wady
        dot(beak_x + 3, wy, "m")
        dot(beak_x + 4, wy, "n")
        if wad > 1:
            dot(beak_x + 4, wy - 1, "h")
            dot(beak_x + 3, wy + 1, "q")
    wx, wyy, wg = WALK_WING[wing]
    put(wg, max(0, bx + wx), vtop + wyy + wdy)  # squash + swung wing: keep inside col 0
    leg_and_foot(near, 12 + dx, NEAR)
    info["clipped"] = clipped
    info["feet_bottom"] = max(p[1] for p in foot_px)
    info["eye_top"] = eye_top
    info["planted"] = [f[1] == 0 and f[2] in PLANTED for f in (far, near)]
    info["feet"] = (far, near)
    return px, info


def F(**kw):
    return kw


# ------------------------------------------------------------------ variants
# Feet: (ankle col, lift, shape). Planted columns come from the speed: a planted foot keeps its
# world x, so its frame col = contact col - round(1.4 * ticks since contact).
def variant_a():
    holds = [2] * 6
    L = [0, 1, 1, 0, 1, 1]
    tuft = ["up", "flat", "norm"] * 2
    wing = ["back", "mid", "fwd", "fwd", "mid", "back"]
    n = [(15, 0, "heel"), (12, 0, "flat"), (9, 0, "flat"), (7, 0, "toe"), (10, 2, "tuck"), (13, 1, "tuck")]
    f = n[3:] + n[:3]
    out = []
    for i in range(6):
        out.append(F(L=L[i], tuft=tuft[i], wing=wing[i], wady=max(-1, min(1, L[i] - L[i - 1])), near=n[i],
                     far=f[i]))
    return holds, out


def variant_b():
    holds = [2, 1] * 4
    body = ["rest", "squash", "rest", "rest"] * 2
    L = [0, 0, 1, 1] * 2
    tuft = ["up", "up", "flat", "norm"] * 2
    wady = [-1, -1, 1, 0] * 2
    wing = ["back", "back", "mid", "fwd", "fwd", "fwd", "mid", "back"]
    n = [(15, 0, "heel"), (12, 0, "flat"), (11, 0, "flat"), (8, 0, "flat"), (7, 0, "toe"),
         (9, 1, "tuck"), (11, 2, "tuck"), (14, 1, "tuck")]
    f = n[4:] + n[:4]
    return holds, [F(body=body[i], L=L[i], tuft=tuft[i], wing=wing[i], wady=wady[i], near=n[i], far=f[i])
                   for i in range(8)]


def variant_c():
    holds = [2] * 8
    body = ["squash", "stretch", "rest", "rest"] * 2
    L = [0, 1, 2, 1] * 2
    dx = [0, 1, 1, 0] * 2
    tuft = ["up", "flat", "flat", "up"] * 2
    eyes = ["lids", "open", "open", "open"] * 2
    wing = ["upmid", "downmid", "mid", "upmid"] * 2
    wady = [-1, 1, 1, -1] * 2
    n = [(15, 0, "flat"), (12, 0, "toe"), (10, 2, "tuck"), (9, 1, "tuck"),
         (10, 1, "tuck"), (12, 2, "tuck"), (14, 2, "tuck"), (15, 1, "heel")]
    f = n[4:] + n[:4]
    return holds, [F(body=body[i], L=L[i], dx=dx[i], tuft=tuft[i], eyes=eyes[i], wing=wing[i], wady=wady[i],
                     near=n[i], far=f[i]) for i in range(8)]


IDLE_SPEC = F(far_dark=False, wady=0)  # rest pose, feet 9 / 14, wing mid, wad 2: the sheet's idle frame


def extras():
    land = ([6, 8], [
        F(body="squash", eyes="lids", tuft="up", wing="upmid", wady=-1, far_dark=False),
        F(tuft="flat", wing="downmid", wady=1, far_dark=False),
    ])
    breathe = ([24, 10, 14, 10], [
        dict(IDLE_SPEC),
        F(body="stretch", wdy=-1, wady=1, far_dark=False),
        F(body="stretch", tuft="up", wdy=-1, far_dark=False),
        F(tuft="flat", wady=-1, far_dark=False),
    ])
    return land, breathe


VARIANTS = [("A", "6-frame grounded waddle", variant_a()),
            ("B", "8-frame full walk", variant_b()),
            ("C", "8-frame hop-walk", variant_c())]
LAND, BREATHE = extras()
EXTRAS = [("land", "landing pair (then idle)", LAND, False), ("breathe", "idle breathing loop", BREATHE, True)]


# ------------------------------------------------------------------ helpers
def render(px, who):
    return sb.render(px, PALS[who])


def up(im, n):
    return im.resize((im.width * n, im.height * n), Image.NEAREST)


def box_of(px, letters):
    pts = [p for p, ch in px.items() if ch in letters]
    return (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))


def gif_durations(holds):
    """cumulative rounding to 10 ms so 1-tick holds come out 20 ms, never the 10 ms browsers clamp"""
    out, t, prev = [], 0, 0
    for hd in holds:
        t += hd
        cs = round(t * 100 / 60)
        out.append(max(2, cs - prev) * 10)
        prev = cs
    return out


BG = (24, 24, 28, 255)
GROUND = (90, 90, 100, 255)
MARK = (150, 150, 160, 255)


def to_p(im):
    return im.convert("RGB").quantize(colors=64, method=Image.Quantize.MEDIANCUT)


def strip(frames, who):
    s = Image.new("RGBA", (FW * len(frames), FH), (0, 0, 0, 0))
    for i, (px, _) in enumerate(frames):
        s.alpha_composite(render(px, who), (i * FW, 0))
    return s


def inplace_gif(frames, holds, path, loop=True):
    ims = []
    for px, _ in frames:
        f = Image.new("RGBA", (FW * 2 + 12, FH + 6), BG)
        d = ImageDraw.Draw(f)
        for k, who in enumerate(("player", "cpu")):
            x = 4 + k * (FW + 4)
            f.alpha_composite(render(px, who), (x, 2))
            d.line([(x - 2, 2 + FH), (x + FW + 1, 2 + FH)], fill=GROUND)
        ims.append(to_p(up(f, 4)))
    durs = gif_durations(holds)
    if not loop:
        durs[-1] += 700
    ims[0].save(path, save_all=True, append_images=ims[1:], duration=durs, loop=0, disposal=1)


def move_gif(frames, holds, path, cycles):
    """one GIF frame per game tick (shown 20 ms: 0.83 x real speed), sprite x = floor(1.4 t)"""
    cyc = sum(holds)
    ticks = cyc * cycles
    seq = []
    for i, hd in enumerate(holds):
        seq += [i] * hd
    width = FW + int(SPEED * ticks) + 8
    ims = []
    for t in range(ticks):
        fi = seq[t % cyc]
        x = 4 + math.floor(SPEED * t)
        f = Image.new("RGBA", (width, 2 * (FH + 6)), BG)
        d = ImageDraw.Draw(f)
        for k, who in enumerate(("player", "cpu")):
            gy = 2 + FH + k * (FH + 6)
            d.line([(0, gy), (width, gy)], fill=GROUND)
            for mx in range(0, width, 4):
                d.point((mx, gy + 1), fill=MARK if mx % 8 == 0 else GROUND)
            f.alpha_composite(render(frames[fi][0], who), (x, gy - FH))
        ims.append(to_p(up(f, 4)))
    ims[0].save(path, save_all=True, append_images=ims[1:], duration=20, loop=0, disposal=1)


def slide_report(frames, holds):
    """per foot: runs of planted frames, world x at each frame start, max drift from the run's first frame"""
    cyc = sum(holds)
    starts = [sum(holds[:i]) for i in range(len(holds))]
    n = len(frames)
    lines = []
    worst = 0.0
    for k, name in enumerate(("far", "near")):
        planted = [fr[1]["planted"][k] for fr in frames]
        if all(planted):
            continue
        s = planted.index(False)
        i = s
        for _ in range(n):
            i = (i + 1) % n
            if planted[i] and not planted[i - 1]:
                run = []
                j = i
                while planted[j % n] and len(run) < n:
                    run.append(j)
                    j += 1
                wx = []
                for jj in run:
                    t = starts[jj % n] + cyc * (jj // n)
                    wx.append(frames[jj % n][1]["feet"][k][0] + SPEED * t)
                drift = max(abs(v - wx[0]) for v in wx)
                worst = max(worst, drift)
                lines.append("    %s foot planted frames %s, cols %s, world x drift max %.1f px" % (
                    name, " ".join(str(jj % n) for jj in run),
                    " ".join(str(frames[jj % n][1]["feet"][k][0]) for jj in run), drift))
    return lines, worst


# ------------------------------------------------------------------ tiles
def tiles_of(im, size, pad_to=None):
    if pad_to:
        p = Image.new("RGBA", pad_to, (0, 0, 0, 0))
        p.alpha_composite(im, (0, 0))
        im = p
    out = set()
    for ty in range(0, im.height, size):
        for tx in range(0, im.width, size):
            t = im.crop((tx, ty, tx + size, ty + size))
            if t.getbbox():
                out.add(t.tobytes())
    return out


def main():
    sheet = Image.open(SHEET_PNG).convert("RGBA")
    meta = sb.META
    old_frames = [sheet.crop((r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"])) for r in meta["animations"]["player"]]
    idle_rect = {w: meta["animations"][w][62] for w in ("player", "cpu")}
    idle_cur = {w: sheet.crop((r["x"], r["y"], r["x"] + FW, r["y"] + FH)) for w, r in idle_rect.items()}
    # the reused parts reproduce the sheet's idle frame exactly
    idle_px, idle_info = compose_walk(**IDLE_SPEC)
    for w in ("player", "cpu"):
        assert render(idle_px, w).tobytes() == idle_cur[w].tobytes(), "idle mismatch " + w
        idle_cur[w].save(os.path.join(HERE, "idle_current_%s.png" % ("rival" if w == "cpu" else w)))
    idle_top = min(p[1] for p in idle_px)
    old8 = set().union(*[tiles_of(f, 8) for f in old_frames])
    old16 = set().union(*[tiles_of(f, 16, (32, 32)) for f in old_frames])

    L = ["Sootling walk drafts, measured by draw_walk.py. Frame 24 x 32, col 0 left, row 0 top.",
         "Idle frame (sheet frame 62) reproduced pixel-exact from the reused parts: head top row %d, feet row 31,"
         % idle_top,
         "fur cols %d..%d. No gum bubble in idle (it carries the gum wad at the beak), so no bubble in any walk"
         % box_of(idle_px, "abcde")[0::2],
         "frame; every frame carries the wad. Limits checked: head top >= %d, feet bottom 31 on contact frames"
         % (idle_top - 1),
         "and >= 29 otherwise, fur covers cols 10..13 (collision band) in every frame, palette = sheet indices.",
         "feet row = lowest foot pixel; head = topmost pixel (tuft); body cols = fur colours a..e; colours = palette",
         "entries used. Ground speed %.1f px per game frame; tick = 1/60 s." % SPEED, ""]

    all_rows = []
    gallery = []
    for name, desc, (holds, specs) in VARIANTS + [(e[0], e[1], e[2]) for e in EXTRAS]:
        frames = [compose_walk(**s) for s in specs]
        is_walk = name in "ABC"
        cyc = sum(holds)
        L.append("%s: %s, %d frames, holds %s game frames (cycle %d ticks = %.3f s)" % (
            name, desc, len(frames), " ".join(map(str, holds)), cyc, cyc / 60))
        if is_walk:
            stride = SPEED * cyc
            L.append("  stride %.1f x %d = %.1f px per cycle, %.1f px per step" % (SPEED, cyc, stride, stride / 2))
        for i, (px, info) in enumerate(frames):
            top = min(p[1] for p in px)
            fb = box_of(px, "abcde")
            used = len(set(px.values()))
            flags = []
            if info["clipped"]:
                flags.append("CLIPPED %s" % info["clipped"])
            if info.get("foot_in_body"):
                flags.append("FOOT IN BODY %s" % info["foot_in_body"])
            if top < idle_top - 1:
                flags.append("HEAD TOO HIGH")
            if info["feet_bottom"] < 29:
                flags.append("FEET TOO HIGH")
            if any(info["planted"]) and info["feet_bottom"] != 31:
                flags.append("PLANTED NOT ON 31")
            if not (fb[0] <= 10 and fb[2] >= 13):
                flags.append("BOX OUTSIDE BODY")
            for c in range(10, 14):
                if not any(px.get((c, y), ".") in "abcde" for y in range(FH)):
                    flags.append("NO FUR IN COL %d" % c)
            L.append("  frame %d: feet row %d, head top row %d, body cols %d..%d (rows %d..%d), eyes top row %d, "
                     "colours %d%s" % (i, info["feet_bottom"], top, fb[0], fb[2], fb[1], fb[3], info["eye_top"], used,
                                       ("  " + "; ".join(flags)) if flags else ""))
        if is_walk:
            sl, worst = slide_report(frames, holds)
            L += sl
            L.append("  (within a hold the planted foot rides along with the sprite, up to %.1f px, then snaps back;"
                     " drift above is frame start to frame start)" % (SPEED * max(holds)))
        im8, im16 = set(), set()
        for px, _ in frames:
            im = render(px, "player")
            im8 |= tiles_of(im, 8)
            im16 |= tiles_of(im, 16, (32, 32))
        L.append("  tiles (player; rival reuses them): 8x8 %d unique, %d not in the current sheet; "
                 "16x16 (frame at x 0 in 32 x 32) %d unique, %d not in the current sheet" % (
                     len(im8), len(im8 - old8), len(im16), len(im16 - old16)))
        L.append("")
        for who, tag in (("player", "player"), ("cpu", "rival")):
            s = strip(frames, who)
            s.save(os.path.join(HERE, "%s_%s_%s.png" % ("walk" if is_walk else "extra", name, tag)))
            all_rows.append(s)
        inplace_gif(frames, holds, os.path.join(HERE, "%s_%s_4x.gif" % ("walk" if is_walk else "extra", name)),
                    loop=(name != "land"))
        if is_walk:
            move_gif(frames, holds, os.path.join(HERE, "walk_%s_move_4x.gif" % name), 4 if cyc <= 12 else 3)
        if SCRATCH:
            per = 4
            rows_n = (len(frames) + per - 1) // per
            chk = Image.new("RGBA", (per * (FW + 3), rows_n * (FH + 4)), BG)
            d = ImageDraw.Draw(chk)
            for i, (px, _) in enumerate(frames):
                x, y = (i % per) * (FW + 3), (i // per) * (FH + 4)
                d.line([(x, y + FH), (x + FW - 1, y + FH)], fill=GROUND)
                for c in (10, 13):
                    d.point((x + c, y + FH + 1), fill=(200, 60, 60, 255))
                chk.alpha_composite(render(px, "player"), (x, y))
            up(chk, 10).save(os.path.join(SCRATCH, "check_%s.png" % name))
        gallery.append((name, desc, len(frames), holds))

    w = max(r.width for r in all_rows)
    comb = Image.new("RGBA", (w, FH * len(all_rows)), (0, 0, 0, 0))
    for i, r in enumerate(all_rows):
        comb.alpha_composite(r, (0, i * FH))
    comb.save(os.path.join(HERE, "walk_sheet_draft.png"))
    L.append("walk_sheet_draft.png: %d x %d, rows top to bottom: A player, A rival, B player, B rival, C player,"
             " C rival, land player, land rival, breathe player, breathe rival" % comb.size)
    L.append("current sheet tile pool: 8x8 %d unique, 16x16 %d unique (player frames)" % (len(old8), len(old16)))
    open(os.path.join(HERE, "measure.txt"), "w").write("\n".join(L) + "\n")
    print("\n".join(l for l in L if "frame " in l and "  " in l and any(
        k in l for k in ("CLIP", "FOOT", "HEAD", "FEET", "PLANT", "BOX", "NO FUR"))) or "no flags")
    print("\n".join(l for l in L if "drift" in l or "tiles" in l or "stride" in l))


if __name__ == "__main__":
    main()
