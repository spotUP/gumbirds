#!/opt/homebrew/bin/python3.14 -I
"""Gum Trip drafts, fix round: rival C brows in all 63 frames, rival palette contrast, gum tube half mark.

Run from the repo root:
  /opt/homebrew/bin/python3.14 -I thoughts/shared/drafts/2026-11-10-gum-trip-rival-meter-fix/draw_rival_meter_fix.py
Reads (read only): assets/flier/sootling_sheet.png + .json, assets/font/fix_font.json,
thoughts/shared/drafts/2026-11-10-backgrounds-final/scene_<mood>_1x.png,
thoughts/shared/drafts/2026-11-10-hud-title-final/hud1p_storm_1x.png.
Writes every file of this folder except README.md. Pillow only. No code is imported from other draft folders;
load_sootling, the old brow rule and the old tube tile are copied from 2026-11-10-gum-trip-pickup-rival so that
the "old" side of every comparison is reproduced exactly.
"""
import sys
sys.dont_write_bytecode = True
import json, os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
KEY = (255, 0, 255)
PAGE = (27, 28, 31)
MOODS = ("dusk", "moon", "storm")
BAND = (16, 96)          # scene rows used as "sky band where fliers fly" (below the HUD rows, above the skyline)
STEP_MS = 67             # 4 ticks at 60 Hz


def P(*a):
    return os.path.join(HERE, *a)


def e5(v):
    """5 bit channel value to the 8 bit value the build uses (dark bit 0)."""
    return (v << 3) | (v >> 2)


def pal5(rows):
    return [tuple(e5(v) for v in c) for c in rows]


def up(im, s=3):
    return im.resize((im.width * s, im.height * s), Image.NEAREST)


def blit(dst, img, ox, oy):
    px = dst.load()
    for y, row in enumerate(img):
        for x, c in enumerate(row):
            if c is not None and 0 <= ox + x < dst.width and 0 <= oy + y < dst.height:
                px[ox + x, oy + y] = c


def colourise(fr, pal):
    return [[None if i == 0 else pal[i - 1] for i in row] for row in fr]


# ------------------------------------------------------------------ inputs
def load_sootling():
    meta = json.load(open(os.path.join(ROOT, "assets/flier/sootling_sheet.json")))
    im = Image.open(os.path.join(ROOT, "assets/flier/sootling_sheet.png")).convert("RGBA")
    pal = [tuple(c) for c in meta["palettes"]["player"]]
    cpu = [tuple(c) for c in meta["palettes"]["cpu"]]
    lut = {c: i + 1 for i, c in enumerate(pal)}
    px = im.load()
    frames = []
    for r in meta["animations"]["player"]:
        fr = []
        for y in range(r["h"]):
            row = []
            for x in range(r["w"]):
                p = px[r["x"] + x, r["y"] + y]
                row.append(0 if p[3] == 0 or p[:3] not in lut else lut[p[:3]])
            fr.append(row)
        frames.append(fr)
    return frames, pal, cpu, meta


def load_scenes():
    out = {}
    for m in MOODS:
        out[m] = Image.open(os.path.join(ROOT, "thoughts/shared/drafts/2026-11-10-backgrounds-final",
                                         "scene_%s_1x.png" % m)).convert("RGB")
    return out


# ------------------------------------------------------------------ colour measures
def lin(v):
    v /= 255.0
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def lum(c):
    return 0.2126 * lin(c[0]) + 0.7152 * lin(c[1]) + 0.0722 * lin(c[2])


def ratio(a, b):
    """Luminance contrast ratio (lighter + 0.05) / (darker + 0.05), 1.0 = none."""
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def lab(c):
    r, g, b = lin(c[0]), lin(c[1]), lin(c[2])
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    return 116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))


def de(a, b):
    """CIELAB colour distance (delta E 1976)."""
    return sum((p - q) ** 2 for p, q in zip(lab(a), lab(b))) ** 0.5


def band_stats(scene):
    px = sorted(scene.crop((0, BAND[0], scene.width, BAND[1])).get_flattened_data(), key=lum)
    n = len(px)
    return {"p10": px[n // 10], "med": px[n // 2], "p90": px[9 * n // 10]}


# ------------------------------------------------------------------ rival palettes
# index 1 keyline, 2..5 fur dark to light, 6 rim and eye white, 7..9 beak and feet, 10..14 gum, 15 white
OLD = {
    "A": [(8, 8, 16), (32, 24, 48), (64, 56, 88), (112, 104, 136), (176, 176, 200), (248, 232, 64),
          (96, 8, 24), (216, 32, 40), (248, 136, 72),
          (112, 48, 0), (184, 96, 0), (240, 168, 16), (248, 224, 96), (248, 248, 200), (248, 248, 248)],
    "B": [(16, 8, 32), (72, 56, 112), (136, 128, 176), (200, 200, 224), (240, 240, 248), (248, 56, 56),
          (24, 16, 48), (64, 56, 104), (144, 136, 184),
          (48, 16, 96), (96, 40, 168), (144, 88, 232), (192, 160, 248), (232, 224, 248), (248, 248, 248)],
    "C": [(16, 8, 32), (40, 16, 72), (88, 32, 136), (152, 64, 184), (216, 136, 232), (248, 248, 160),
          (16, 56, 40), (40, 160, 88), (160, 240, 120),
          (96, 0, 24), (168, 16, 32), (232, 48, 40), (248, 136, 88), (248, 216, 176), (248, 248, 248)],
}
# new palettes in 5 bit units per channel (0..31), dark bit 0
NEW5 = {
    # Hornet: charcoal-plum shadow, ochre body, yellow light; cream eye; gum pushed from amber to orange so that
    # the bubble does not merge with the now yellow body
    "A": [(1, 1, 2), (6, 4, 7), (21, 17, 6), (28, 24, 10), (31, 30, 20), (31, 31, 27),
          (12, 1, 3), (27, 4, 5), (31, 17, 9),
          (16, 5, 1), (24, 9, 1), (30, 15, 2), (31, 23, 10), (31, 30, 23), (31, 31, 31)],
    # Bone: unchanged, only expressed in 5 bit units
    "B": [(2, 1, 4), (9, 7, 14), (17, 16, 22), (25, 25, 28), (30, 30, 31), (31, 7, 7),
          (3, 2, 6), (8, 7, 13), (18, 17, 23),
          (6, 2, 12), (12, 5, 21), (18, 11, 29), (24, 20, 31), (29, 28, 31), (31, 31, 31)],
    # Bruiser: plum shadow, orchid body, lavender light (only the four fur colours change)
    "C": [(2, 1, 4), (11, 3, 17), (24, 12, 27), (28, 19, 30), (31, 27, 31), (31, 31, 20),
          (2, 7, 5), (5, 20, 11), (20, 30, 15),
          (12, 0, 3), (21, 2, 4), (29, 6, 5), (31, 17, 11), (31, 27, 22), (31, 31, 31)],
}
NEW = {k: pal5(v) for k, v in NEW5.items()}
NAMES = {"A": "Hornet", "B": "Bone", "C": "Bruiser"}
FUR_W = {2: 2505, 3: 6707, 4: 2588, 5: 1739}     # pixel use of the fur indices over the 63 source frames


# ------------------------------------------------------------------ brows
# old rule, copied (41 frames changed, 2 of them with one mirrored half brow, 22 without any)
def find_eyes(fr):
    h, w = len(fr), len(fr[0])
    seen = [[False] * w for _ in range(h)]
    comps = []
    for y in range(h):
        for x in range(w):
            if fr[y][x] == 6 and not seen[y][x]:
                st, pts = [(x, y)], []
                seen[y][x] = True
                while st:
                    cx, cy = st.pop()
                    pts.append((cx, cy))
                    for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                        if 0 <= nx < w and 0 <= ny < h and fr[ny][nx] == 6 and not seen[ny][nx]:
                            seen[ny][nx] = True
                            st.append((nx, ny))
                xs, ys = [p[0] for p in pts], [p[1] for p in pts]
                bw, bh = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
                if bw >= 3 and bh >= 4 and len(pts) >= 10 and len(pts) >= 0.45 * bw * bh and bw <= 12:
                    comps.append((len(pts), min(xs), max(xs), min(ys), max(ys)))
    comps.sort(reverse=True)
    return comps[:2]


def add_brows_old(fr):
    out = [r[:] for r in fr]
    eyes = find_eyes(fr)
    if not eyes:
        return out
    beak = [(x, y) for y, r in enumerate(fr) for x, i in enumerate(r) if i in (7, 8, 9)]
    for k, (_, x0, x1, y0, y1) in enumerate(eyes):
        if len(eyes) == 2:
            o = eyes[1 - k]
            inner_right = (o[1] + o[2]) > (x0 + x1)
        else:
            inner_right = (sum(p[0] for p in beak) / len(beak) > (x0 + x1) / 2) if beak else True
        for x in range(x0, x1 + 1):
            tt = (x - x0) / max(1, x1 - x0)
            if not inner_right:
                tt = 1 - tt
            cut = int(round(0.6 + tt * 2.2))
            for y in range(y0, min(y1, y0 + cut)):
                out[y][x] = 1 if y == y0 + cut - 1 else 2
    return out


# new rule: one fixed brow shape, placed by the eye socket of the frame.
# Columns are absolute (the socket never moves sideways: columns 14..24 in all 63 frames, asserted below).
# Rows are relative to T. K = keyline (index 1), A = darkest fur (index 2).
BROW = {
    0: {15: "K", 16: "K", 17: "A", 18: "A", 19: "A", 20: "K", 21: "K", 22: "K", 23: "K"},
    1: {17: "K", 18: "K", 19: "A", 20: "K", 21: "A", 22: "A", 23: "K"},
    2: {19: "K", 20: "K", 21: "A", 22: "K"},
    3: {21: "K"},
}
EYE1 = [(x, r) for r, row in BROW.items() for x in row if x <= 19]     # 9 pixels, near eye
EYE2 = [(x, r) for r, row in BROW.items() for x in row if x >= 20]     # 12 pixels, far eye and bridge


def brow_anchor(fr):
    """Returns (T, mode). Open eye: T = top row of the near eye white (columns 15..19).
    Squint or shut eye: T = lid row - 2, the lid being the only row with keyline on all of columns 14..19."""
    lids = [y for y in range(26, 40) if all(fr[y][x] == 1 for x in range(14, 20))]
    if lids:
        assert len(lids) == 1, lids
        return lids[0] - 2, "lid"
    tops = [y for y in range(26, 40) if all(fr[y - 1][x] == 1 for x in range(15, 20)) and fr[y - 1][14] != 1
            and fr[y][14] == 1 and fr[y][20] == 1 and (fr[y][19] == 6 or fr[y + 1][19] == 6)]
    assert tops, "no socket"
    return tops[0], "open"


def add_brows(fr):
    out = [r[:] for r in fr]
    T, mode = brow_anchor(fr)
    hidden = 0
    for r, row in BROW.items():
        for x, k in row.items():
            y = T + r
            cur = fr[y][x]
            if cur >= 7:                      # gum bubble (10..14) or beak (7..9) is in front of the brow
                hidden += 1
                continue
            if mode == "lid":
                if k == "A" and cur == 1:     # the lid line stays one unbroken keyline
                    continue
                if r == 3 and cur != 6:       # below the lid only eye white gives way (cheek fur stays)
                    continue
            out[y][x] = 1 if k == "K" else 2
    return out, T, mode, hidden


def frame_tiles(fr):
    return [tuple(tuple(fr[ty + y][tx:tx + 16]) for y in range(16)) for ty in range(0, 48, 16) for tx in range(0, 32, 16)]


# ------------------------------------------------------------------ meter (fix layer, 8x8 tiles)
OLD_M = {"k": (16, 8, 40), "e": (40, 32, 80), "E": (24, 16, 56), "d": (168, 32, 128), "p": (248, 80, 176),
         "h": (248, 168, 216), "w": (248, 248, 248), "r": (136, 144, 200), ".": None}
OLD_WARN = dict(OLD_M, d=(160, 24, 24), p=(240, 88, 32), h=(248, 184, 88))
ICON = ["........", "..kkkk..", ".khhppkk", "kwhppppk", "khpppppk", "kpppppdk", ".kpddkkk", "..kkkk.."]
# character -> slot (1..15) of the fix palette "white" in assets/font/fix_font.json
SLOT = {"k": 5, "d": 9, "p": 10, "h": 11, "w": 12, "e": 13, "r": 4, "g": 15, "D": 6, "P": 7, "H": 8}


def old_tube_tile(a, b):
    rows = []
    for y in range(8):
        r = ""
        for s in (a, b):
            if y in (1, 6):
                r += "kkkk"
            elif y in (0, 7):
                r += "...."
            elif s:
                r += {2: "whh", 3: "ppp", 4: "ppp", 5: "ddd"}[y] + "k"
            else:
                r += {2: "EEE", 3: "eee", 4: "eee", 5: "eer"}[y] + "k"
        rows.append(r)
    return rows


def tube_tile(state, mark=None, warn=False):
    """state: 0 empty, 1 first 4 px segment filled, 2 both. mark: 'L' = tile left of the half point
    (gold bar on its last column, cap on rows 0 and 7), 'R' = tile right of it (cap pixel on column 0)."""
    rows = []
    for y in range(8):
        r = ""
        for s in (state >= 1, state >= 2):
            if y in (1, 6):
                r += "kkkk"
            elif y in (0, 7):
                r += "...."
            elif s:
                r += {2: "whh", 3: "ppp", 4: "ppp", 5: "ddd"}[y] + "k"
            else:
                r += {2: "eee", 3: "eee", 4: "eee", 5: "eer"}[y] + "k"
        r = list(r)
        if mark == "L":
            r[7] = "g"
            if y in (0, 7):
                r[6] = "g"
        if mark == "R" and y in (0, 7):
            r[0] = "g"
        r = "".join(r)
        if warn:
            r = r.replace("d", "D").replace("p", "P").replace("h", "H")
        rows.append(r)
    return rows


def warn_icon():
    return [r.replace("d", "D").replace("p", "P").replace("h", "H") for r in ICON]


def meter_cells(step):
    """The 5 fix cells of the meter for a fill step 0..8, left to right."""
    warn = step <= 2
    cells = [warn_icon() if warn else ICON]
    for c in range(4):
        st = max(0, min(2, step - 2 * c))
        cells.append(tube_tile(st, {1: "L", 2: "R"}.get(c), warn and st > 0))
    return cells


def draw_tile(dst, rows, ox, oy, pal):
    px = dst.load()
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch != "." and pal[ch] is not None:
                px[ox + x, oy + y] = pal[ch]


# ------------------------------------------------------------------ gif
def save_gif(frames, path, scale=3):
    big = [up(f, scale) for f in frames]
    mos = Image.new("RGB", (big[0].width * 4, big[0].height * ((len(big) + 3) // 4)))
    for i, f in enumerate(big):
        mos.paste(f, ((i % 4) * f.width, (i // 4) * f.height))
    pal = mos.quantize(255, dither=Image.Dither.NONE)
    q = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in big]
    q[0].save(path, save_all=True, append_images=q[1:], duration=STEP_MS, loop=0, disposal=1)


def clip_steps(first, count, ticks, loop, period):
    """Frame index per 4 tick step over one period; a clip that does not loop holds its last frame."""
    seq, t = [], 0
    bounds = []
    for i in range(count):
        t += ticks[first + i]
        bounds.append(t)
    for s in range(period):
        tt = s * 4
        if loop:
            tt %= bounds[-1]
        k = next((i for i, b in enumerate(bounds) if tt < b), count - 1)
        seq.append(first + k)
    return seq


# ------------------------------------------------------------------ main
def main():
    soot, pal_p, pal_c, meta = load_sootling()
    scenes = load_scenes()
    tb = meta["tables"]
    num = []
    W = num.append

    # ---------------- 1. brows
    old_c = [add_brows_old(f) for f in soot]
    new_c, anchors = [], []
    for f in soot:
        o, T, mode, hidden = add_brows(f)
        new_c.append(o)
        anchors.append((T, mode, hidden))
    old_none = [i for i in range(63) if old_c[i] == soot[i]]
    old_half = [i for i in range(63) if old_c[i] != soot[i] and len(find_eyes(soot[i])) < 2]
    old_good = [i for i in range(63) if i not in old_none and i not in old_half]
    same_as_old = [i for i in old_good if new_c[i] == old_c[i]]
    assert same_as_old == old_good, "the new rule must reproduce the 39 accepted brow frames exactly"
    fixed = sorted(old_none + old_half)

    sheet_c = Image.new("RGB", (256, 384), KEY)
    for i, f in enumerate(new_c):
        blit(sheet_c, colourise(f, NEW["C"]), (i % 8) * 32, (i // 8) * 48)
    sheet_c.save(P("rival_c_sheet_1x.png"))
    for rid in ("A", "B"):
        sh = Image.new("RGB", (256, 384), KEY)
        for i, f in enumerate(soot):
            blit(sh, colourise(f, NEW[rid]), (i % 8) * 32, (i // 8) * 48)
        sh.save(P("rival_%s_sheet_1x.png" % rid.lower()))

    # check from the written sheet, not from memory
    back = Image.open(P("rival_c_sheet_1x.png")).convert("RGB")
    lut = {c: i + 1 for i, c in enumerate(NEW["C"])}
    assert len(set(NEW["C"])) == 15
    bpx = back.load()
    rows = []
    ok1 = ok2 = 0
    for i in range(63):
        fx, fy = (i % 8) * 32, (i // 8) * 48
        g = lambda x, y: 0 if bpx[fx + x, fy + y] == KEY else lut[bpx[fx + x, fy + y]]
        T, mode, hidden = anchors[i]
        n1 = sum(1 for x, r in EYE1 if g(x, T + r) == (1 if BROW[r][x] == "K" else 2))
        dark2 = sum(1 for x, r in EYE2 if g(x, T + r) in (1, 2))
        gum2 = sum(1 for x, r in EYE2 if g(x, T + r) >= 7)
        added = sum(1 for y in range(48) for x in range(32) if g(x, y) != soot[i][y][x])
        rows.append((i, T, mode, n1, dark2, gum2, added))
        ok1 += n1 == 9
        ok2 += dark2 + gum2 >= 11
    assert ok1 == 63, ok1

    W("== 1. Rival C brows")
    W("old rule: %d frames without brows %s" % (len(old_none), old_none))
    W("old rule: %d frames with one brow only, slanted the wrong way (far eye half behind the bubble) %s"
      % (len(old_half), old_half))
    W("new rule: frames redrawn %d (%d + %d); the other %d frames are pixel-identical to the accepted old brow frames"
      % (len(fixed), len(old_none), len(old_half), len(same_as_old)))
    W("brow shape: 21 pixels (near eye 9, far eye and bridge 12), same shape and same columns in every frame; "
      "row T follows the eye socket")
    W("check, read back from rival_c_sheet_1x.png: near-eye brow complete (9 of 9 pixels, exact index) in %d of 63 "
      "frames; far-eye brow dark or behind gum on at least 11 of 12 pixels in %d of 63 frames" % (ok1, ok2))
    W("frame: T, socket state, near-eye px of 9, far-eye dark px of 12, far-eye px behind gum, px changed vs source")
    for r in rows:
        W("  %2d: T %d, %-4s, %d, %2d, %2d, %2d%s" % (r + ("   (redrawn)" if r[0] in fixed else "",)))
    names = ["FLAP2", "FLAP1", "POP2", "POP1", "INFLATE", "FALL", "IDLE"]
    worst = 0
    for c, nm in enumerate(names):
        f0, n = tb["clip_first"][c], tb["clip_count"][c]
        ts = [anchors[i][0] for i in range(f0, f0 + n)]
        steps = [abs(a - b) for a, b in zip(ts, ts[1:])] + ([abs(ts[-1] - ts[0])] if tb["clip_loop"][c] else [])
        worst = max([worst] + steps)
        W("  clip %-7s frames %2d..%2d brow row T: %s  largest step %d px"
          % (nm, f0, f0 + n - 1, " ".join(str(t) for t in ts), max(steps) if steps else 0))
    W("largest brow move between neighbouring frames of a clip: %d px (the brow sits at a fixed offset from the "
      "socket, so it moves only when the eye does)" % worst)
    src_tiles = {t for f in soot for t in frame_tiles(f)}
    ch_frames = sum(1 for a, b in zip(soot, new_c) if a != b)
    ch_refs = sum(1 for a, b in zip(soot, new_c) for x, y in zip(frame_tiles(a), frame_tiles(b)) if x != y)
    new_tiles = {t for f in new_c for t in frame_tiles(f)} - src_tiles
    old_new_tiles = {t for f in old_c for t in frame_tiles(f)} - src_tiles
    W("tile cost versus the shared Sootling frames: %d of 63 frames differ, %d tile references differ, %d new unique "
      "16x16 tiles (old draft: 41 frames, 123 references, %d tiles)"
      % (ch_frames, ch_refs, len(new_tiles), len(old_new_tiles)))

    # ---------------- 2. contrast
    W("")
    W("== 2. Contrast (palette only)")
    W("sky band: scene rows %d..%d of scene_<mood>_1x.png, full width; median, 10th and 90th percentile pixel by "
      "luminance" % (BAND[0], BAND[1] - 1))
    stats = {m: band_stats(scenes[m]) for m in MOODS}
    for m in MOODS:
        s = stats[m]
        W("  %-5s median %s  p10 %s  p90 %s  (outline ceiling: a pure black outline gives %.2f against the median)"
          % (m, s["med"], s["p10"], s["p90"], ratio((0, 0, 0), s["med"])))
    W("contrast = (lighter luminance + 0.05) / (darker + 0.05); 1.00 is no contrast. Body = fur index 3 (most used "
      "fur colour, %d of %d fur pixels). Outline = index 1." % (FUR_W[3], sum(FUR_W.values())))
    tab = {}
    for rid in "ABC":
        for m in MOODS:
            s = stats[m]
            o, n = OLD[rid], NEW[rid]
            tab[(rid, m)] = (ratio(o[2], s["med"]), ratio(n[2], s["med"]), ratio(o[0], s["med"]), ratio(n[0], s["med"]),
                             de(o[2], s["med"]), de(n[2], s["med"]))
            W("  rival %s %-7s on %-5s: body vs median %.2f -> %.2f | body vs p10 %.2f -> %.2f | body vs p90 %.2f -> "
              "%.2f | outline vs median %.2f -> %.2f | colour distance body to median %.0f -> %.0f"
              % (rid, NAMES[rid], m, tab[(rid, m)][0], tab[(rid, m)][1], ratio(o[2], s["p10"]), ratio(n[2], s["p10"]),
                 ratio(o[2], s["p90"]), ratio(n[2], s["p90"]), tab[(rid, m)][2], tab[(rid, m)][3],
                 tab[(rid, m)][4], tab[(rid, m)][5]))
    for nm, pl in (("player 1", pal_p), ("computer", pal_c)):
        W("  for reference %-8s: body vs median %s | outline vs median %s"
          % (nm, " ".join("%s %.2f" % (m, ratio(pl[2], stats[m]["med"])) for m in MOODS),
             " ".join("%s %.2f" % (m, ratio(pl[0], stats[m]["med"])) for m in MOODS)))

    def fur_de(a, b):
        per = [de(a[i - 1], b[i - 1]) for i in (2, 3, 4, 5)]
        return per, sum(d * FUR_W[i] for d, i in zip(per, (2, 3, 4, 5))) / sum(FUR_W.values())

    W("colour distance between body tones (CIELAB delta E 1976; fur index 2, 3, 4, 5; then the mean weighted by "
      "pixel use). Under about 10 two colours are hard to tell apart at a glance.")
    dist = {}
    for rid in "ABC":
        for nm, pl in (("player 1", pal_p), ("computer", pal_c)):
            po, wo = fur_de(OLD[rid], pl)
            pn, wn = fur_de(NEW[rid], pl)
            dist[(rid, nm)] = (wo, wn, po[1], pn[1])
            W("  rival %s vs %-8s: old %s mean %.1f -> new %s mean %.1f"
              % (rid, nm, " ".join("%.0f" % d for d in po), wo, " ".join("%.0f" % d for d in pn), wn))
    W("  rival A body (index 3) vs its own gum (index 12): old %.0f -> new %.0f"
      % (de(OLD["A"][2], OLD["A"][11]), de(NEW["A"][2], NEW["A"][11])))
    W("  rival C body (index 3) vs player 1 gum (index 11, 12): old %.0f, %.0f -> new %.0f, %.0f; vs rival B gum "
      "(index 11, 12): old %.0f, %.0f -> new %.0f, %.0f"
      % (de(OLD["C"][2], pal_p[10]), de(OLD["C"][2], pal_p[11]), de(NEW["C"][2], pal_p[10]), de(NEW["C"][2], pal_p[11]),
         de(OLD["C"][2], OLD["B"][10]), de(OLD["C"][2], OLD["B"][11]),
         de(NEW["C"][2], NEW["B"][10]), de(NEW["C"][2], NEW["B"][11])))
    W("  body luminance (0..1): old A %.3f B %.3f C %.3f -> new A %.3f B %.3f C %.3f; player 1 %.3f, computer %.3f"
      % (lum(OLD["A"][2]), lum(OLD["B"][2]), lum(OLD["C"][2]), lum(NEW["A"][2]), lum(NEW["B"][2]), lum(NEW["C"][2]),
         lum(pal_p[2]), lum(pal_c[2])))
    for rid in "ABC":
        changed = [i + 1 for i in range(15) if tuple(v >> 3 for v in OLD[rid][i]) != NEW5[rid][i]]
        W("palette %s (%s), 15 colours + transparent, 5 bits per channel, dark bit 0; indices changed versus the old "
          "draft: %s" % (rid, NAMES[rid], changed if changed else "none (old values re-expressed in 5 bit units)"))
        W("  5 bit: %s" % " ".join("(%d,%d,%d)" % c for c in NEW5[rid]))
        W("  8 bit: %s" % " ".join("(%d,%d,%d)" % c for c in NEW[rid]))
        W("  old  : %s" % " ".join("(%d,%d,%d)" % c for c in OLD[rid]))
        assert len(set(NEW[rid])) == 15 and all(0 <= v <= 31 for c in NEW5[rid] for v in c)

    # ---------------- stills and gifs
    p1 = colourise(soot[0], pal_p)
    p2 = colourise(soot[0], pal_c)
    for m in MOODS:
        im = Image.new("RGB", (200, 2 * 58 + 2), PAGE)
        for r, (pals, cf) in enumerate(((OLD, old_c), (NEW, new_c))):
            row = scenes[m].crop((60, 22, 260, 80)).copy()
            blit(row, p1, 4, 5)
            blit(row, p2, 164, 5)
            for k, rid in enumerate("ABC"):
                blit(row, colourise((cf if rid == "C" else soot)[0], pals[rid]), 44 + 40 * k, 5)
            im.paste(row, (0, r * 60))
        up(im).save(P("compare_palette_%s_3x.png" % m))

    # squint frame line-up, new only, all moods (frame 17 has slit eyes)
    im = Image.new("RGB", (200, 3 * 60 - 2), PAGE)
    for r, m in enumerate(MOODS):
        row = scenes[m].crop((60, 22, 260, 80)).copy()
        blit(row, colourise(soot[17], pal_p), 4, 5)
        blit(row, colourise(soot[17], pal_c), 164, 5)
        for k, rid in enumerate("ABC"):
            blit(row, colourise((new_c if rid == "C" else soot)[17], NEW[rid]), 44 + 40 * k, 5)
        im.paste(row, (0, r * 60))
    im.save(P("lineup_new_squint_1x.png"))
    up(im).save(P("lineup_new_squint_3x.png"))

    # old versus new brows, the redrawn frames, whole frame
    n = len(fixed)
    per = 12
    im = Image.new("RGB", (per * 32, ((n + per - 1) // per) * 98), PAGE)
    for k, i in enumerate(fixed):
        ox, oy = (k % per) * 32, (k // per) * 98
        tile = Image.new("RGB", (32, 48), (58, 62, 74))
        blit(tile, colourise(old_c[i], OLD["C"]), 0, 0)
        im.paste(tile, (ox, oy))
        tile = Image.new("RGB", (32, 48), (58, 62, 74))
        blit(tile, colourise(new_c[i], NEW["C"]), 0, 0)
        im.paste(tile, (ox, oy + 48))
    up(im).save(P("compare_brows_3x.png"))

    # head close-ups at 6x: open, wide, squint, lower squint, shut, shut behind bubble, half hidden, fall
    pick = [0, 16, 17, 19, 20, 22, 24, 26, 52]
    im = Image.new("RGB", (len(pick) * 28 + 2, 2 * 17 + 2), PAGE)
    for k, i in enumerate(pick):
        for r, (cf, pl) in enumerate(((old_c, OLD["C"]), (new_c, NEW["C"]))):
            tile = Image.new("RGB", (26, 15), (58, 62, 74))
            T = anchors[i][0]
            blit(tile, [row[4:30] for row in colourise(cf[i], pl)[T - 5:T + 10]], 0, 0)
            im.paste(tile, (2 + k * 28, 2 + r * 17))
    up(im, 6).save(P("compare_brows_heads_6x.png"))

    periods = {0: 8, 1: 8, 2: 20, 3: 20, 4: 20, 5: 10, 6: 40}
    order = [6, 0, 1, 2, 3, 4, 5]
    seqs = {c: clip_steps(tb["clip_first"][c], tb["clip_count"][c], tb["frame_ticks"], tb["clip_loop"][c], periods[c])
            for c in order}
    gif_info = []
    for m in MOODS:
        gf = []
        for s in range(40):
            im = scenes[m].crop((34, 24, 34 + 7 * 36, 24 + 56)).copy()
            for k, c in enumerate(order):
                blit(im, colourise(new_c[seqs[c][s % periods[c]]], NEW["C"]), 2 + k * 36, 4)
            gf.append(im)
        save_gif(gf, P("rival_c_%s_3x.gif" % m))
        g = Image.open(P("rival_c_%s_3x.gif" % m))
        gif_info.append("rival_c_%s_3x.gif: %d frames, %dx%d, %d KB" % (m, g.n_frames, g.width, g.height,
                                                                  os.path.getsize(P("rival_c_%s_3x.gif" % m)) // 1024))
    # all three rivals flapping, new palettes, per mood
    for m in MOODS:
        gf = []
        for s in range(8):
            im = scenes[m].crop((60, 22, 260, 80)).copy()
            blit(im, colourise(soot[s], pal_p), 4, 5)
            blit(im, colourise(soot[s], pal_c), 164, 5)
            for k, rid in enumerate("ABC"):
                blit(im, colourise((new_c if rid == "C" else soot)[(s + 2 * k + 3) % 8], NEW[rid]), 44 + 40 * k, 5)
            gf.append(im)
        save_gif(gf, P("rivals_flap_%s_3x.gif" % m))

    # ---------------- 3. meter
    fix = json.load(open(os.path.join(ROOT, "assets/font/fix_font.json")))
    fpal = [tuple(c) for c in fix["palettes"]["white"]]
    MP = {ch: fpal[s - 1] for ch, s in SLOT.items()}
    hud = Image.open(os.path.join(ROOT, "thoughts/shared/drafts/2026-11-10-hud-title-final/hud1p_storm_1x.png")).convert("RGB")
    base = hud.crop((0, 0, 176, 16))
    base.paste(scenes["storm"].crop((64, 8, 176, 16)), (64, 8))     # removes the three life dots of the arena tag
    used = {}
    states = Image.new("RGB", (176, 9 * 18 - 2), PAGE)
    for row, step in enumerate(range(8, -1, -1)):
        im = base.copy()
        for c, t in enumerate(meter_cells(step)):
            used.setdefault(tuple(t), len(used))
            draw_tile(im, t, 72 + 8 * c, 8, MP)
        states.paste(im, (0, row * 18))
    states.save(P("meter_states_1x.png"))
    up(states).save(P("meter_states_3x.png"))
    # bare strips at 6x for the six states the brief names: full, 3/4, in-between (5 of 8), half, 1/4, empty
    named = [(8, "full"), (6, "3/4"), (5, "5 of 8"), (4, "half"), (2, "1/4"), (0, "empty")]
    im = Image.new("RGB", (40 + 4, len(named) * 12 + 2), (53, 72, 85))
    for r, (step, _) in enumerate(named):
        for c, t in enumerate(meter_cells(step)):
            draw_tile(im, t, 2 + 8 * c, 2 + r * 12, MP)
    up(im, 6).save(P("meter_named_states_6x.png"))
    # old versus new in the HUD, steps 8, 4, 0
    im = Image.new("RGB", (176 * 2 + 4, 3 * 18 - 2), PAGE)
    for r, step in enumerate((8, 4, 0)):
        o = base.copy()
        pal = OLD_WARN if step <= 2 else OLD_M
        draw_tile(o, ICON, 72, 8, pal)
        for t in range(4):
            draw_tile(o, old_tube_tile(int(step > 2 * t), int(step > 2 * t + 1)), 80 + 8 * t, 8, pal)
        nw = base.copy()
        for c, t in enumerate(meter_cells(step)):
            draw_tile(nw, t, 72 + 8 * c, 8, MP)
        im.paste(o, (0, r * 18))
        im.paste(nw, (180, r * 18))
    up(im).save(P("compare_meter_3x.png"))
    tiles = sorted(used, key=used.get)
    ts = Image.new("RGB", (8 * len(tiles), 8), KEY)
    for k, t in enumerate(tiles):
        draw_tile(ts, list(t), k * 8, 0, MP)
    ts.save(P("meter_tiles_1x.png"))
    up(ts, 6).save(P("meter_tiles_6x.png"))
    # read back
    tb_im = Image.open(P("meter_tiles_1x.png")).convert("RGB")
    cols = {c for c in tb_im.get_flattened_data() if c != KEY}
    assert cols <= set(fpal), cols - set(fpal)
    uniq = {tuple(tb_im.crop((x, 0, x + 8, 8)).get_flattened_data()) for x in range(0, tb_im.width, 8)}
    slots = sorted({fpal.index(c) + 1 for c in cols})
    W("")
    W("== 3. Meter A, gum tube with half mark (fix layer)")
    W("cells: 5 fix cells in one row (1 gum ball icon + 4 tube cells), 40x8 px; fill steps 8 (+ empty); each tube "
      "cell holds two 4 px segments, one step each")
    W("step -> cells: cell c (0..3 from the left) shows clamp(step - 2c, 0, 2) filled segments: 0 empty tile, "
      "1 half tile, 2 full tile")
    for step in range(8, -1, -1):
        W("  step %d (%s): icon %s | %s" % (step, {8: "full", 6: "3/4", 4: "half", 2: "1/4", 0: "empty"}.get(step, "in-between"),
                                          "warning" if step <= 2 else "normal",
                                          " ".join(str(max(0, min(2, step - 2 * c))) for c in range(4))))
    W("half mark: gold bar (slot 15) on the seam between tube cells 2 and 3, 8 px tall (2 px taller than the tube), "
      "3 px caps on rows 0 and 7; it is part of the tiles, always shown; at step 4 the fill ends exactly on it")
    W("unique tiles: %d read back from meter_tiles_1x.png (%d drawn): icon 2 (normal, warning); plain tube cell 5 "
      "(empty, half, full, warning half, warning full); cell left of the mark 3; cell right of the mark 3"
      % (len(uniq), len(tiles)))
    W("colours: %d, all from the fix palette 'white' of assets/font/fix_font.json, slots %s; no second palette "
      "(the old draft needed an orange palette for the warning; here the warning uses the red slots 6..8 as tiles)"
      % (len(cols), slots))
    W("sprites: 0")
    W("")
    W("== files")
    for g in gif_info:
        W(g)
    for fn in sorted(os.listdir(HERE)):
        if fn.endswith(".png"):
            im = Image.open(P(fn)).convert("RGB")
            c = {x for x in im.get_flattened_data()}
            W("%s: %dx%d, %d colours" % (fn, im.width, im.height, len(c)))
    for rid in "abc":
        im = Image.open(P("rival_%s_sheet_1x.png" % rid)).convert("RGB")
        c = {x for x in im.get_flattened_data()} - {KEY}
        assert len(c) <= 15 and c <= set(NEW[rid.upper()]), rid
        W("rival_%s_sheet_1x.png palette check: %d colours + transparent, all in palette %s" % (rid, len(c), rid.upper()))

    open(P("numbers.txt"), "w").write(
        "Gum Trip fix round: rival C brows, rival contrast, gum tube half mark.\n"
        "Written by draw_rival_meter_fix.py; every count below is measured by the script, most of them read back "
        "from the written PNG.\n\n" + "\n".join(num) + "\n")
    write_html(fixed, old_none, old_half, tab, dist, stats, len(uniq), len(cols), slots, ok1, ok2, worst,
               len(new_tiles), ch_refs)
    print("\n".join(num))


def write_html(fixed, old_none, old_half, tab, dist, stats, ntiles, ncols, slots, ok1, ok2, worst, new_tiles, refs):
    def fig(src, cap, w=None):
        return ('<figure><img src="%s"%s alt=""><figcaption>%s</figcaption></figure>'
                % (src, ' style="width:%dpx"' % w if w else "", cap))

    rows = ""
    for rid in "ABC":
        for m in MOODS:
            t = tab[(rid, m)]
            rows += ("<tr><td>%s %s</td><td>%s</td><td>%.2f</td><td>%.2f</td><td>%.2f</td><td>%.2f</td><td>%.0f</td>"
                     "<td>%.0f</td></tr>" % (rid, NAMES[rid], m, t[0], t[1], t[2], t[3], t[4], t[5]))
    drows = ""
    for (rid, nm), d in dist.items():
        drows += "<tr><td>%s %s</td><td>%s</td><td>%.1f</td><td>%.1f</td><td>%.0f</td><td>%.0f</td></tr>" % (
            rid, NAMES[rid], nm, d[0], d[1], d[2], d[3])
    html = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Gum Trip: rival and meter fix round</title>
<style>
body{background:#1b1c1f;color:#d9dce3;font-family:-apple-system,"Helvetica Neue",Arial,sans-serif;margin:28px 36px;line-height:1.45}
h1{font-size:24px;margin:0 0 6px;color:#fff}
h2{font-size:18px;margin:38px 0 8px;color:#fff;border-bottom:1px solid #3a3d45;padding-bottom:6px}
p{max-width:900px;margin:8px 0}
figure{margin:14px 0 22px}
img{image-rendering:pixelated;display:block;border:1px solid #3a3d45;max-width:100%%}
figcaption{font-size:14px;color:#aab0bd;margin-top:6px;max-width:900px}
table{border-collapse:collapse;font-size:14px;margin:10px 0 18px}
td,th{border:1px solid #3a3d45;padding:4px 10px;text-align:right}
td:first-child,th:first-child,td:nth-child(2),th:nth-child(2){text-align:left}
th{background:#26282d;color:#fff;font-weight:600}
.row{display:flex;flex-wrap:wrap;gap:18px}
</style></head><body>
<h1>Gum Trip: rival and meter fix round</h1>
<p>Three fixes on the accepted drafts: brows on every Bruiser frame, palette contrast for Hornet and Bruiser,
a half mark on the gum tube. All numbers are in numbers.txt; reasoning and doubts are in README.md.</p>

<h2>1. Rival C Bruiser: brows in all 63 frames</h2>
<p>%d frames redrawn: %d had no brows, %d had one brow slanted the wrong way. The other %d frames are
pixel-identical to the accepted brow frames. Read back from the sheet: the near-eye brow is complete in %d of 63
frames; the far-eye brow is dark or behind the gum bubble in %d of 63. Largest brow move between neighbouring frames
of a clip: %d px.</p>
%s
%s
%s
<div class="row">%s%s%s</div>

<h2>2. Contrast, palette only</h2>
<p>Old row on top, new row below. Order in each row: player 1, A Hornet, B Bone, C Bruiser, computer flier.</p>
<div class="row">%s%s%s</div>
<div class="row">%s%s%s</div>
%s
<table><tr><th>Rival</th><th>Mood</th><th>Body contrast old</th><th>new</th><th>Outline contrast old</th><th>new</th>
<th>Colour distance to sky old</th><th>new</th></tr>%s</table>
<p>Contrast is the luminance ratio against the median sky pixel of scene rows 16 to 95 (1.00 is none). Sky medians:
dusk %s, moon %s, storm %s.</p>
<table><tr><th>Rival</th><th>Against</th><th>Body distance old (weighted mean)</th><th>new</th>
<th>Mid tone old</th><th>new</th></tr>%s</table>

<h2>3. Meter A: gum tube with half mark</h2>
<p>%d fix cells in a row (icon plus four tube cells), %d unique tiles, %d colours, all from the HUD font palette
(slots %s). Eight fill steps and empty; the gold bar sits on the seam between tube cells 2 and 3.</p>
<div class="row">%s%s</div>
%s
%s
%s
</body></html>
""" % (
        len(fixed), len(old_none), len(old_half), 63 - len(fixed), ok1, ok2, worst,
        fig("compare_brows_heads_6x.png", "Head close-ups at 6x, old on top, new below. Frames 0 (open), 16 (wide), "
            "17 (squint), 19 (lower squint), 20 (shut), 22 (shut, bubble in front), 24 (squint, bubble over the far "
            "eye), 26 (old: one brow, wrong slant), 52 (fall). Old uses the old palette, new the new one."),
        fig("compare_brows_3x.png", "The %d redrawn frames at 3x, whole frame. In each block the upper bird is old, "
            "the lower bird is new. Frames: %s." % (len(fixed), ", ".join(str(i) for i in fixed))),
        fig("rival_c_sheet_1x.png", "Bruiser sheet at 1x, 63 frames of 32x48, 8 per row, new palette. Magenta is "
            "transparent. %d new unique 16x16 tiles, %d tile references differ from the shared Sootling frames."
            % (new_tiles, refs)),
        fig("rival_c_dusk_3x.gif", "Bruiser on dusk, 3x. Left to right: idle, flap (two lobes), flap (one lobe), "
            "pop (two lobes), pop (one lobe), inflate, fall. The idle clip is a single frame."),
        fig("rival_c_moon_3x.gif", "Bruiser on moon, same clips."),
        fig("rival_c_storm_3x.gif", "Bruiser on storm, same clips."),
        fig("compare_palette_dusk_3x.png", "Dusk."), fig("compare_palette_moon_3x.png", "Moon."),
        fig("compare_palette_storm_3x.png", "Storm."),
        fig("rivals_flap_dusk_3x.gif", "New palettes flapping, dusk."),
        fig("rivals_flap_moon_3x.gif", "New palettes flapping, moon."),
        fig("rivals_flap_storm_3x.gif", "New palettes flapping, storm."),
        fig("lineup_new_squint_3x.png", "New palettes on a squint frame (frame 17), dusk, moon, storm from top to "
            "bottom."),
        rows, stats["dusk"]["med"], stats["moon"]["med"], stats["storm"]["med"], drows,
        5, ntiles, ncols, ", ".join(str(s) for s in slots),
        fig("meter_named_states_6x.png", "At 6x, top to bottom: full, 3/4, in-between (5 of 8), half, 1/4, empty. "
            "At 1/4 and below the fill and the icon turn red."),
        fig("meter_tiles_6x.png", "The unique 8x8 tiles at 6x. Magenta is transparent."),
        fig("meter_states_3x.png", "All nine states in the HUD at 3x, steps 8 down to 0, under the PLAYER 1 tag on "
            "the storm mood."),
        fig("compare_meter_3x.png", "Old tube (left) and new tube (right) at steps 8, 4 and 0."),
        fig("rival_a_sheet_1x.png", "For reference: Hornet sheet at 1x with the new palette (frames unchanged). "
            "rival_b_sheet_1x.png holds Bone the same way."),
    )
    open(P("index.html"), "w").write(html)


if __name__ == "__main__":
    main()
