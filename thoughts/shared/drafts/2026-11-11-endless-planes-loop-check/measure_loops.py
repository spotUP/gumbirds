"""Loop/seam measurement of parallax planes. Read-only; run: /opt/homebrew/bin/python3.14 -I measure_loops.py > numbers.txt
Pixel model: None = transparent (magenta 255,0,255 or alpha 0), else RGB tuple."""
import glob, json, os, re, statistics
from PIL import Image
ROOT = "/Users/spot/Code/ArcadeGame"
DR = ROOT + "/thoughts/shared/drafts/"
def load_draft(path):
    im = Image.open(path).convert("RGB"); w, h = im.size; px = im.load()
    return [[None if px[x, y] == (255, 0, 255) else px[x, y] for x in range(w)] for y in range(h)]
def load_rect(im, r):
    px = im.load()
    return [[None if px[x, y][3] == 0 else px[x, y][:3] for x in range(r["x"], r["x"] + r["w"])] for y in range(r["y"], r["y"] + r["h"])]
def col(g, x): return [row[x] for row in g]
def coldiff(a, b):  # (rows with any difference, rows where opacity differs = silhouette break)
    return sum(1 for p, q in zip(a, b) if p != q), sum(1 for p, q in zip(a, b) if (p is None) != (q is None))
def tiles(g, P):  # unique 16x16 tiles of columns 0..P-1, dedupe exact (transparency included); empty tiles not counted
    h = len(g); seen = set()
    for ty in range(0, h, 16):
        for tx in range(0, P, 16):
            t = tuple(tuple(g[y][tx:tx + 16]) if y < h else (None,) * 16 for y in range(ty, ty + 16))
            if any(p is not None for r in t for p in r): seen.add(t)
    return len(seen)
def analyse(name, g):
    W, H = len(g[0]), len(g)
    inter = [coldiff(col(g, x), col(g, x + 1))[0] for x in range(W - 1)]
    med = statistics.median(inter)
    res = []
    for P in range(16, W + 1, 16):
        d, s = coldiff(col(g, P - 1), col(g, 0))
        # 16 px bands each side: rows of the 16 columns before the join vs 16 after: differing adjacent-pair count over the 15+1 pairs crossing
        ov = None
        if P < W:
            n = (W - P); bad = sum(1 for x in range(n) for y in range(H) if g[y][x + P] != g[y][x]); ov = bad / float(n * H)
        res.append((P, d, s, ov))
    return W, H, med, inter, res
def bands(g, W):  # rows differing per 16-row band at the full-width wrap
    a, b = col(g, W - 1), col(g, 0); H = len(g)
    return [sum(1 for y in range(y0, min(y0 + 16, H)) if a[y] != b[y]) for y0 in range(0, H, 16)]
def band16(g, W):  # opaque pixels in the 16 px band each side of the join, and differing pixels of mirrored-pair columns across wrap
    H = len(g); L = sum(1 for y in range(H) for x in range(16) if g[y][x] is not None); R = sum(1 for y in range(H) for x in range(W - 16, W) if g[y][x] is not None)
    return L, R
sets = []
im = Image.open(ROOT + "/assets/city/city_sheet.png").convert("RGBA"); js = json.load(open(ROOT + "/assets/city/city_sheet.json"))
for n, rs in js["animations"].items(): sets.append(("IMPORTED(assets/city, moon, from backgrounds-wide)", "moon", n, load_rect(im, rs[0])))
for label, d, pat in (("WIDE drafts (arena planes)", "2026-11-10-backgrounds-wide", "plane_*_1x.png"), ("FINAL drafts (backgrounds-final)", "2026-11-10-backgrounds-final", "plane_*_1x.png"), ("RING drafts (gum-trip-endless-planes)", "2026-11-10-gum-trip-endless-planes", "plane_*_1x.png")):
    for f in sorted(glob.glob(DR + d + "/" + pat)):
        m = re.match(r"plane_(\w+?)_(\w+)_1x.png", os.path.basename(f))
        if m: sets.append((label, m.group(1), m.group(2), load_draft(f)))
ORDER = {"sky": 0, "far": 1, "midA": 2, "midB": 3, "near": 4}
sets.sort(key=lambda s: (s[0], s[1], ORDER.get(s[3] and s[2], 9), s[2]))
print("Loop/seam measure. Per plane: W x H; interior = rows differing between neighbouring columns (median over all interior pairs);")
print("seam at P = columns P-1 and 0 (rows differing / rows where opacity differs, i.e. a silhouette break = building cut). Single frame only (frame 0).")
print("excess = seam rows - interior median. ovl = mismatch fraction of columns P..W-1 against 0..W-P-1 (period test, P<W only).\n")
summary = []
cur = None
for label, mood, name, g in sets:
    if label != cur: print("=" * 8, label); cur = label
    W, H, med, inter, res = analyse(name, g)
    pct = sum(1 for v in inter if v >= res[-1][1]) / float(len(inter)) * 100
    print("%-5s %-9s W=%3d H=%3d interior median %4.1f max %2d | seam@W: diff %2d rows, silhouette %2d rows, bands(16 rows) %s, opaque px in 16px band left/right %s, %.0f%% of interior pairs differ as much" % (mood, name, W, H, med, max(inter), res[-1][1], res[-1][2], bands(g, W), band16(g, W), pct))
    cand = [r for r in res if r[0] >= 128] or res
    best = min(cand, key=lambda r: (r[1] + r[2], -r[0]))
    print("      candidate P (diff/sil/ovl): " + "  ".join("%d:%d/%d/%s" % (r[0], r[1], r[2], "-" if r[3] is None else "%.2f" % r[3]) for r in res))
    ut = tiles(g, W); utb = tiles(g, best[0])
    print("      best P>=128 (min diff+sil) = %d  seam %d/%d rows;  unique 16x16 tiles frame0: W=%d -> %d, bestP -> %d" % (best[0], best[1], best[2], W, ut, utb))
    summary.append((label, mood, name, W, res[-1][1], res[-1][2], med, best[0], best[1], best[2], ut, utb))
print("\nSUMMARY label|mood|plane|W|seamdiff@W|silhouette@W|interiorMedian|bestP|diff|sil|uniqueTiles@W|uniqueTiles@bestP")
for s in summary: print("|".join(str(x) for x in s))

# ---- edge anatomy: opaque rows at the first/last column, and distance to the nearest fully transparent column (an alley) from each end
print("\nEDGE ANATOMY label|mood|plane|W|opaque rows col0|opaque rows colW-1|first fully empty column from left|last fully empty column from right (distance from W-1)")
for label, mood, name, g in sets:
    if name in ("sky", "airship", "cloudsback", "cloudsfront", "beams"): continue
    W = len(g[0]); empty = [all(p is None for p in col(g, x)) for x in range(W)]
    fl = next((x for x in range(W) if empty[x]), None); lr = next((W - 1 - x for x in range(W - 1, -1, -1) if empty[x]), None)
    print("%s|%s|%s|%d|%d|%d|%s|%s" % (label, mood, name, W, sum(p is not None for p in col(g, 0)), sum(p is not None for p in col(g, W - 1)), fl, lr))
