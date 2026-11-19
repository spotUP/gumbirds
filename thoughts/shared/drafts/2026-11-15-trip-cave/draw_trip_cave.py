#!/opt/homebrew/bin/python3.14
"""Gum Trip cave roof / deadly floor / edge smoothing drafts (2026-11-15).
Run from anywhere: writes PNG/GIF/numbers.txt/index.html beside this file.
Draft only: reads assets/tripstrip/tripstrip_sheet.png, writes nothing outside this folder."""
import math, os, random
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "../../../.."))
VW, VH, CHUNK, WORLD_H = 384, 224, 192, 180
BAYER = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) + 0.5) / 16 - 0.5

def snap(c):  # Neo Geo 5 bits per channel
    return tuple(((v >> 3) << 3) | (v >> 5) for v in c)

# ---- roof palettes: index 0..8 = rock ramp dark->light (hue shifts), 9.. = accents
PALS = {
 "take1_slate": [(16,8,33),(33,24,57),(49,41,82),(66,66,107),(82,90,123),(107,115,140),(140,148,156),(181,181,165),(222,214,181),
                 (41,82,66),(74,123,74),(132,165,82),(90,57,74),(132,82,82)],
 "take2_stalactite": [(24,8,24),(49,24,41),(74,41,49),(107,57,57),(140,82,66),(173,115,82),(206,156,107),(231,198,140),(247,231,189),
                 (41,33,74),(66,57,107),(148,206,222),(222,247,255)],
 "take3_moss": [(8,16,33),(24,33,57),(33,57,74),(49,82,90),(74,107,99),(115,140,115),(165,173,132),(198,198,148),(231,231,181),
                 (24,66,41),(41,107,49),(90,156,57),(165,206,82),(255,222,132)],
}
PALS = {k: [snap(c) for c in v] for k, v in PALS.items()}
for k, v in PALS.items():
    assert len(set(v)) == len(v) <= 15, (k, len(v))

def rock(W, H, seeds, periodic_y, nlev, cmaps):
    """Weighted Voronoi boulders, lit from lower left, banded with Bayer dither only at band edges.
    seeds: (cx, cy, r, shift, cmap_name). Returns palette index array HxW."""
    Y, X = np.mgrid[0:H, 0:W].astype(float)
    dxs, dys, dns = [], [], []
    for cx, cy, r, _, _ in seeds:
        dx = ((X - cx + W / 2) % W) - W / 2
        dy = (((Y - cy + H / 2) % H) - H / 2) if periodic_y else (Y - cy)
        dxs.append(dx / r); dys.append(dy / r); dns.append(np.hypot(dx, dy) / r)
    dns = np.array(dns); i1 = dns.argmin(0); srt = np.sort(dns, 0)
    edge = (srt[1] - srt[0]) * 8
    nx = np.take_along_axis(np.array(dxs), i1[None], 0)[0]
    ny = np.take_along_axis(np.array(dys), i1[None], 0)[0]
    nz = np.sqrt(np.clip(1 - 0.7 * (nx * nx + ny * ny), 0, 1))
    l = -0.7 * nx + 0.9 * ny + 0.5 * nz
    shift = np.array([s[3] for s in seeds])[i1]
    lv = (l + 0.9) / 2.3 * (nlev - 2) + 1.4 + shift + BAYER[Y.astype(int) % 4, X.astype(int) % 4] * 0.6
    lv = np.clip(np.rint(lv), 2, nlev - 1).astype(int)
    lv[edge < 2.4] = 1
    lv[edge < 1.1] = 0
    out = np.zeros((H, W), int)
    for i, s in enumerate(seeds):
        m = i1 == i
        out[m] = np.array(cmaps[s[4]])[lv[m]]
    return out

def make_roof(name, seed):
    """Returns dict rim 16x64, hang 16x64 (or None), fill 32x64 as palette index arrays (-1 = transparent)."""
    rng = random.Random(seed)
    base = list(range(9))
    cmaps = {"rock": base, "warm": [0, 1, 2, 12, 13, 5, 6, 7, 8] if name != "take2_stalactite" else [0, 1, 9, 10, 4, 5, 6, 7, 8],
             "moss": [0, 1, 9, 9, 10, 10, 11, 11, 8] if name == "take1_slate" else base}
    kinds = ["rock", "rock", "warm", "rock", "moss", "rock"]
    fseeds = [((gx + 0.5) * 16 + rng.uniform(-5, 5), (gy + 0.5) * 32 / 3 + rng.uniform(-3, 3), rng.uniform(6.5, 10),
               rng.choice([-1, 0, 0, 1]), rng.choice(kinds)) for gy in range(3) for gx in range(4)]
    fill = rock(64, 32, fseeds, True, 6, cmaps)          # deeper rock: top three shades never used
    rseeds = [(6 + 12.8 * i + rng.uniform(-2, 2), rng.uniform(5.5, 7.5), rng.uniform(7, 8.4), rng.choice([0, 0, 1]),
               rng.choice(kinds)) for i in range(5)]
    canvas = np.full((32, 64), -1)
    body = rock(64, 16, rseeds, False, 9, cmaps)
    Y, X = np.mgrid[0:16, 0:64].astype(float)
    solid = Y <= 4
    for cx, cy, r, _, _ in rseeds:
        dx = ((X - cx + 32) % 64) - 32
        solid |= (dx / r) ** 2 + ((Y - cy) / min(r, 15 - cy)) ** 2 <= 1
    canvas[:16][solid] = body[solid]
    canvas[0, :] = 0                                        # crevice line: any fill row can sit on top
    canvas[1, :][canvas[1, :] > 1] = 1
    if name == "take2_stalactite":
        for cx, L, w in [(9, 17, 4), (25, 8, 3), (39, 21, 5), (54, 11, 3)]:
            for y in range(7, 7 + L):
                t = (y - 7) / L
                hw = max(0.6, w * (1 - t) ** 0.7)
                xs = [x for x in range(64) if abs(x - cx) <= hw]
                for x in xs:
                    s = (x - cx) / max(hw, 1)
                    c = 7 if s < -0.4 else 5 if s < 0.3 else 3
                    if (y + (x - cx) // 2) % 4 == 0: c -= 1   # growth rings
                    canvas[y, x] = c
                for x in (xs[0] - 1, xs[-1] + 1):
                    if canvas[y, x % 64] < 0: canvas[y, x % 64] = 0
            y = 7 + L                                          # blunt tip with a water drop
            canvas[y - 1, cx] = 12; canvas[y - 2, cx] = 11
            for x in (cx - 1, cx, cx + 1):
                if canvas[y, x] < 0: canvas[y, x] = 0
    if name == "take3_moss":
        for x in range(64):
            col = canvas[:, x]
            bot = max(y for y in range(16) if col[y] >= 0)
            depth = 3 + [0, 1, 2, 2, 1, 0, 1, 3, 2, 1][x % 10]
            for dd in range(depth):
                y = bot - dd
                col[y] = [9, 12, 11, 10, 10, 9][dd] if dd != 3 or BAYER[y % 4, x % 4] > 0 else 9
            if (x * 7) % 5 == 0:                               # short moss drips
                for k in range(1 + x % 3): col[bot + 1 + k] = 10
                col[bot + 1 + x % 3] = 11
        for vx, L, ph, flower in [(5, 13, 0.0, True), (20, 7, 1.3, False), (33, 15, 2.1, False), (46, 9, 0.7, True), (58, 5, 2.9, False)]:
            y0 = max(y for y in range(16) if canvas[y, vx] >= 0) + 1
            for k in range(L):
                x = (vx + round(math.sin(k / 3 + ph))) % 64
                canvas[y0 + k, x] = 10 if k % 2 else 9
                if k % 3 == 1: canvas[y0 + k, (x + (1 if (k // 3) % 2 else -1)) % 64] = 12   # leaf
            if flower:
                canvas[y0 + L, x] = 13; canvas[y0 + L - 1, x] = 12
    # dark outline where rock meets air (not for moss/vines/drops)
    rim = canvas.copy()
    for y in range(31):
        for x in range(64):
            if canvas[y, x] in range(2, 9) and (canvas[y + 1, x] < 0 or canvas[y, (x + 1) % 64] < 0 or canvas[y, x - 1] < 0):
                rim[y, x] = 0
    hang = rim[16:]
    return {"name": name, "rim": rim[:16], "hang": hang if (hang >= 0).any() else None, "fill": fill}

def to_rgba(idx, pal):
    lut = np.array([(0, 0, 0, 0)] + [c + (255,) for c in pal], np.uint8)
    return lut[idx + 1]

def tiles_of(rgba):
    h, w = rgba.shape[:2]
    return {rgba[y:y + 16, x:x + 16].tobytes() for y in range(0, h, 16) for x in range(0, w, 16)
            if rgba[y:y + 16, x:x + 16, 3].any()}

# ---- existing gum floor (colours unchanged)
SHEET = np.array(Image.open(os.path.join(REPO, "assets/tripstrip/tripstrip_sheet.png")).convert("RGBA"))
assert SHEET.shape == (112, 128, 4)
GUM = sorted({tuple(p) for p in SHEET.reshape(-1, 4) if p[3]})
assert len(GUM) == 10
def gtile(role, f): return SHEET[role * 16:role * 16 + 16, f * 16:f * 16 + 16]
def gum_floor(flat):
    rims = []
    for f in range(8):
        a, b = gtile(1, f).copy(), gtile(2, f).copy()
        if flat:  # F1: straight 2 px lip instead of the wavy silhouette, so a sheared or sliding rim has no notches
            for t in (a, b):
                t[0:2] = 0; t[2] = (255, 214, 198, 255); t[3] = (255, 140, 156, 255)
        rims.append(np.hstack([a, b[:, ::-1], b, a[:, ::-1]]))      # column rule: A B' B A'
    t = gtile(0, 0)
    fill = np.vstack([np.hstack([t, t[:, ::-1]]), np.hstack([t[:, ::-1], t])])   # (j+i)&1 hflip checkerboard
    return {"rims": rims, "fill": fill, "wedge": np.array((57, 8, 57, 255), np.uint8)}

# ---- window sequence like trip_gen: step -24..+24, gap >= 120, chunk 192
def windows(seed, n=8):
    rng = random.Random(seed); gap = 144; top = (WORLD_H - gap) // 2; out = [(top, top + gap)]
    for _ in range(n - 1):
        centre = out[-1][0] + (out[-1][1] - out[-1][0]) // 2
        gap = rng.choice([120, 128, 136, 144])
        top = min(max(centre - gap // 2 + rng.randint(-24, 24), 0), WORLD_H - gap)
        out.append((top, top + gap))
    return out

def edges(win, mode, ncols=6):
    """Per world pixel: roof edge E (rock above), floor edge B (gum below), rim u, ramp flag.
    Slopes always sit in the chunk with the wider window, so drawn rock never leaves killing air uncovered."""
    n = len(win); W = n * CHUNK
    if mode == "B": win = [(round(t / 16) * 16, round(b / 16) * 16) for t, b in win]   # generator would snap to the row grid
    res = []
    for side, sgn in ((0, 1), (1, -1)):        # roof: bigger = stricter; floor: smaller = stricter
        v = np.repeat([w[side] for w in win], CHUNK).astype(int)
        u = np.arange(W) % 64; ramp = np.zeros(W, bool)
        for k in range(n - 1):
            a, b = win[k][side], win[k + 1][side]; d = (b - a) * sgn; X = (k + 1) * CHUNK
            if d == 0 or mode == "today": continue
            lo, hi = (a, b) if d > 0 else (b, a)                 # lo = looser side value, hi = stricter
            if mode == "A":
                for i in range(ncols):
                    s = (1 - math.cos(math.pi * (i + 1) / (ncols + 1))) / 2
                    c0 = X - (ncols - i) * 16 if d > 0 else X + (ncols - 1 - i) * 16
                    val = round(lo + (hi - lo) * s)
                    seg = v[c0:c0 + 16]
                    seg[:] = np.maximum(seg, val) if sgn > 0 else np.minimum(seg, val)
            else:
                run = 2 * abs(d)
                for t in range(run):
                    x = X - run + t if d > 0 else X + run - 1 - t
                    if not 0 <= x < W: continue
                    val = lo + sgn * (t // 2 + 1)
                    v[x] = max(v[x], val) if sgn > 0 else min(v[x], val)
                    u[x] = (t % 32) if d > 0 else 31 - (t % 32); ramp[x] = True
        res += [v, u, ramp]
    return res

BG = np.zeros((VH, VW, 3), np.uint8)
for y in range(VH):   # placeholder backdrop, not the real Trip planes
    for x in range(VW):
        BG[y, x] = (24, 24, 57) if abs(y - 100) / 110 + BAYER[y % 4, x % 4] * 0.5 < 0.55 else (16, 16, 41)
BG_COLS = 2

def render(x0, frame, E, UE, RE, B, UB, RB, roof, floor, grid, bg=BG):
    img = bg.copy()
    rrim = roof["rim"][frame] if isinstance(roof["rim"], list) else roof["rim"]
    frim = floor["rims"][frame]; FW = roof["fill"].shape[1]
    for sx in range(VW):
        wx = x0 + sx; e = int(E[wx]); b = int(B[wx])
        fend = e - 16
        if grid and RE[wx]:
            fend = 16 * ((e + 15) // 16) - 32
            for y in range(max(fend, 0), e - 16):
                img[y, sx] = roof["wedge"][0 if BAYER[y % 4, wx % 4] > 0 else 1]
        if fend > 0:
            ys = np.arange(fend)
            img[ys, sx] = roof["fill"][(ys - (0 if grid else e)) % 32, wx % FW, :3]
        for tex, y0 in ((rrim, e - 16), (roof["hang"], e)):
            if tex is None: continue
            for y in range(max(y0, 0), min(y0 + 16, VH)):
                p = tex[y - y0, UE[wx]]
                if p[3]: img[y, sx] = p[:3]
        for y in range(max(b, 0), min(b + 16, VH)):
            p = frim[y - b, UB[wx]]
            if p[3]: img[y, sx] = p[:3]
        fstart = b + 16
        if grid and RB[wx]:
            fstart = 16 * (b // 16) + 32
            img[b + 16:min(fstart, VH), sx] = floor["wedge"][:3]
        if fstart < VH:
            ys = np.arange(fstart, VH)
            img[ys, sx] = floor["fill"][(ys - (0 if grid else b)) % 32, wx % 32, :3]
    return img

def save(arr, name):
    Image.fromarray(arr).save(os.path.join(HERE, name)); return name

def ncol(arr): return len({tuple(p) for p in arr.reshape(-1, arr.shape[-1])})

def main():
    num = []; shots = []
    F0, F1 = gum_floor(False), gum_floor(True)
    roofs = {}
    for name, seed in (("take1_slate", 11), ("take2_stalactite", 23), ("take3_moss", 37)):
        r = make_roof(name, seed); pal = PALS[name]
        used = {int(c) for part in (r["rim"], r["fill"]) + ((r["hang"],) if r["hang"] is not None else ()) for c in np.unique(part) if c >= 0}
        assert len(used) <= 15, name
        parts = [to_rgba(r["rim"], pal), to_rgba(r["hang"] if r["hang"] is not None else np.full((16, 64), -1), pal), to_rgba(r["fill"], pal)]
        sheet = np.vstack(parts); assert sheet.shape == (64, 64, 4)
        nt = len(tiles_of(sheet)); rimt = len(tiles_of(parts[0])); hangt = len(tiles_of(parts[1])); fillt = len(tiles_of(parts[2]))
        assert nt == rimt + hangt + fillt and rimt == 4 and fillt == 8 and 0 <= hangt <= 4, (name, rimt, hangt, fillt)
        assert not (parts[2][..., 3] == 0).any()            # fill is solid
        assert (parts[0][0, :, 3] == 255).all()             # rim top row solid: joins the fill
        roofs[name] = {"rim": parts[0], "hang": parts[1] if hangt else None, "fill": parts[2],
                       "wedge": np.array([pal[0], pal[1]], np.uint8), "tiles": nt, "cols": len(used)}
        save(sheet, f"roof_{name}_sheet_1x.png")
        num.append(f"roof {name}: tiles {nt} (rim {rimt} + hang {hangt} + fill {fillt}, static, no animation), "
                   f"colours {len(used)} of 15, palettes 1 (new slot, not the gum palette)")
    gumroof = {"rim": [r[::-1] for r in F0["rims"]], "hang": None, "fill": F0["fill"][::-1], "wedge": F0["wedge"][None].repeat(2, 0)}
    for nm, fl in (("F0_today", F0), ("F1_flat_lip", F1)):
        cols = {tuple(p) for r in fl["rims"] + [fl["fill"]] for p in r.reshape(-1, 4) if p[3]}
        assert cols <= set(GUM) and len(cols) <= 15
        num.append(f"floor {nm}: tiles drawn by the code 17 (fill 1 + two rim roles x 8 frames; the sheet also ships roles t3..t6 = 24 tiles, "
                   f"vertical wall and corner pieces the code never draws; TRIPSTRIP_TILE_COUNT is 56), colours {len(cols)} of 15, palettes 1 (gum, unchanged)")

    # window sequence: first seed whose first two boundaries both move the roof by 16 px or more
    for seed in range(1, 500):
        win = windows(seed)
        if all(abs(win[k + 1][0] - win[k][0]) >= 16 for k in (0, 1)) and (win[1][0] - win[0][0]) * (win[2][0] - win[1][0]) < 0: break
    for k in range(1, len(win)):
        assert win[k][1] - win[k][0] >= 120 and 0 <= win[k][0] and win[k][1] <= WORLD_H
    num.append(f"window sequence seed {seed} (top,bottom per 192 px chunk): {win}")
    X0 = 96
    T1 = roofs["take1_slate"]
    views = [("mock_today_1x.png", "today", gumroof, F0), ("mock_optionA_1x.png", "A", T1, F0), ("mock_optionB_1x.png", "B", T1, F0),
             ("mock_optionB_flatlip_1x.png", "B", T1, F1), ("mock_optionB_take2_1x.png", "B", roofs["take2_stalactite"], F1),
             ("mock_optionB_take3_1x.png", "B", roofs["take3_moss"], F1), ("mock_optionA_take3_1x.png", "A", roofs["take3_moss"], F1)]
    for fn, mode, rf, fl in views:
        img = render(X0, 0, *edges(win, mode), rf, fl, mode == "B")
        assert img.shape == (VH, VW, 3) and ncol(img) <= BG_COLS + 15 + 10, (fn, ncol(img))
        save(img, fn); shots.append(fn)
    for mode in ("A", "B"):
        E, _, _, B, _, _ = edges(win, mode)
        num.append(f"option {mode}: biggest edge move between neighbouring 16 px columns: roof {int(np.abs(np.diff(E[::16])).max())} px, "
                   f"floor {int(np.abs(np.diff(B[::16])).max())} px; biggest move between neighbouring pixels: "
                   f"roof {int(np.abs(np.diff(E)).max())} px, floor {int(np.abs(np.diff(B)).max())} px")
    E, _, _, B, _, _ = edges(win, "today")
    num.append(f"today: biggest edge jump at a chunk start: roof {int(np.abs(np.diff(E)).max())} px, floor {int(np.abs(np.diff(B)).max())} px")

    # option B ramp tiles: one 32x32 block (2:1 slope) per strip; the other direction is the hflip
    black = np.zeros((VH, VW, 3), np.uint8)
    two = [(32, 160), (48, 144)]
    for nm, rf in roofs.items():
        blk = render(0, 0, *edges(two, "B"), rf, F1, True, black)[16:48, 160:192]
        assert len({blk[y:y + 16, x:x + 16].tobytes() for y in (0, 16) for x in (0, 16)}) == 4
        save(blk, f"ramp_roof_{nm}_1x.png")
    fr = [render(0, f, *edges(two, "B"), T1, F1, True, black)[144:176, 160:192] for f in range(8)]
    ft = {b[y:y + 16, x:x + 16].tobytes() for b in fr for y in (0, 16) for x in (0, 16)}
    save(np.hstack(fr), "ramp_floor_flatlip_8frames_1x.png")
    num.append(f"option A new tiles: 0")
    num.append(f"option B new tiles: roof 4 (one 2x2 block, static; hang row not drawn on ramps) + floor {len(ft)} "
               f"(2x2 block x 8 rim frames, unique after dedupe; 4 if the ramp lip is left static) = {4 + len(ft)}")
    num.append(f"total with take 1 roof, option B, animated floor ramps: roof {T1['tiles']} + 4 ramp, floor 17 used + {len(ft)} ramp "
               f"(TRIPSTRIP_TILE_COUNT 56 today, of which 17 are drawn)")

    # roof take strips on the backdrop, flat edge
    flat = [(40, 152)] * 3
    for nm, rf in roofs.items():
        save(render(0, 0, *edges(flat, "today"), rf, F0, False)[:96], f"roof_{nm}_strip_1x.png")
    for nm, fl in (("F0_today", F0), ("F1_flat_lip", F1)):
        save(render(0, 0, *edges(flat, "today"), T1, fl, False)[136:], f"floor_{nm}_strip_1x.png")

    # scroll GIF: option B + take 1 roof + flat-lip floor, 3x, 50 fps, 0.9 px per GIF frame = 45 px/s (TRIP_SCROLL_START 0.75 px at 60 Hz)
    eb = edges(win, "B"); NF = 150
    allcols = [(24, 24, 57), (16, 16, 41)] + PALS["take1_slate"] + [c[:3] for c in GUM]
    palimg = Image.new("P", (1, 1)); palimg.putpalette([v for c in allcols for v in c] + [0] * (768 - 3 * len(allcols)))
    frames = []
    for f in range(NF):
        img = render(X0 + int(f * 0.9), (f * 60 // 50 // 5) % 8, *eb, T1, F1, True)
        frames.append(Image.fromarray(img).resize((VW * 3, VH * 3), Image.NEAREST).quantize(palette=palimg, dither=Image.Dither.NONE))
    frames[0].save(os.path.join(HERE, "anim_optionB_take1_3x.gif"), save_all=True, append_images=frames[1:], duration=20, loop=0)
    g = Image.open(os.path.join(HERE, "anim_optionB_take1_3x.gif"))
    assert 60 <= g.n_frames <= NF and g.size == (1152, 672)   # PIL merges identical neighbours (0.9 px steps repeat) into one longer frame
    num.append(f"gif: {NF} steps stored as {g.n_frames} frames (identical neighbours merged), 1152x672, 20 ms a frame, 0.9 px a frame = 45 px/s (real start speed 0.75 px at 60 Hz; max is 60 px/s), "
               f"{os.path.getsize(os.path.join(HERE, 'anim_optionB_take1_3x.gif')) // 1024} KB")
    num.append("all palettes asserted <= 15 colours + transparent; all colours 5 bits per channel")
    open(os.path.join(HERE, "numbers.txt"), "w").write("\n".join(num) + "\n")
    print("\n".join(num))
    # text peek at take 1 rim (no image viewing in this session)
    r = make_roof("take1_slate", 11)
    for row in list(r["rim"]) + list(r["fill"]): print("".join(".0123456789ABCDE"[c + 1] for c in row))

    def fig(fn, cap, w, scales=(1, 3)):
        ims = "".join(f'<img src="{fn}" width="{w * s}" alt="{cap}">' for s in scales)
        return f"<figure>{ims}<figcaption>{cap}</figcaption></figure>"
    h = ["<!doctype html><meta charset=utf-8><title>Gum Trip cave drafts</title>",
         "<style>body{background:#14141c;color:#d8d8e0;font:15px/1.5 system-ui,sans-serif;margin:24px}img{image-rendering:pixelated;"
         "margin:0 12px 8px 0;vertical-align:top;border:1px solid #333}figure{margin:0 0 28px}h2{margin-top:40px}"
         "figcaption{color:#a0a0b0;max-width:70em}</style>",
         "<h1>Gum Trip: cave roof, deadly floor, smooth edges (drafts, 2026-11-15)</h1>",
         "<p>Backdrop is a placeholder. Each picture is shown at 1x and 3x. Numbers are in numbers.txt.</p>",
         "<h2>1. Cave roof takes</h2>"]
    caps = {"take1_slate": "Take 1, slate boulders: round blue-grey stones, lumpy underside, nothing hanging.",
            "take2_stalactite": "Take 2, warm rock with blunt stalactites and water drops. Risk: points can still read as spikes.",
            "take3_moss": "Take 3, mossy rock with a soft green fringe, vines and two glow buds."}
    for nm in roofs:
        h += [fig(f"roof_{nm}_strip_1x.png", caps[nm] + f" {roofs[nm]['tiles']} tiles, {roofs[nm]['cols']} colours.", 384), fig(f"roof_{nm}_sheet_1x.png", "Tile sheet: rim row, hang row, two fill rows.", 64, (1, 4))]
    h += ["<h2>2. Floor (kill strip, gum colours unchanged)</h2>",
          fig("floor_F0_today_strip_1x.png", "F0: floor as it is today.", 384),
          fig("floor_F1_flat_lip_strip_1x.png", "F1: same gum with a straight bright lip instead of the wavy top, so it can slope without notches.", 384),
          "<h2>3. Edge smoothing, same window sequence in every picture</h2>",
          fig("mock_today_1x.png", "Today: gum on both sides, edge jumps at each 192 px chunk start.", 384),
          fig("mock_optionA_1x.png", "Option A: take 1 roof, edge eased over six 16 px columns, no new tiles. Small steps remain and the rock pattern breaks between columns.", 384),
          fig("mock_optionA_take3_1x.png", "Option A with take 3 roof and flat-lip floor.", 384),
          fig("mock_optionB_1x.png", "Option B: take 1 roof, ramp tiles with a 2:1 slope, today's floor rim sheared.", 384),
          fig("mock_optionB_flatlip_1x.png", "Option B with the flat-lip floor (F1). This is the combination in the animation.", 384),
          fig("mock_optionB_take2_1x.png", "Option B with take 2 roof.", 384),
          fig("mock_optionB_take3_1x.png", "Option B with take 3 roof.", 384),
          "<h2>Option B ramp tiles</h2>"]
    h += [fig(f"ramp_roof_{nm}_1x.png", f"Roof ramp block for {nm}: 4 tiles, mirrored for the other direction.", 32, (1, 4)) for nm in roofs]
    h += [fig("ramp_floor_flatlip_8frames_1x.png", "Floor ramp block, 8 animation frames side by side.", 256, (1, 3)),
          "<h2>4. Scroll, option B + take 1 roof + flat-lip floor</h2>",
          '<figure><img src="anim_optionB_take1_3x.gif" width="1152" alt="scroll"><figcaption>150 steps at 45 pixels a second (real start speed), already 3x.</figcaption></figure>']
    open(os.path.join(HERE, "index.html"), "w").write("\n".join(h) + "\n")

if __name__ == "__main__":
    main()
