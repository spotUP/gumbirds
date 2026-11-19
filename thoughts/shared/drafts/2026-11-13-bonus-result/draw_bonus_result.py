"""Three looks for the BONUS RESULT screen. Reuses fix font + palettes of the round banner draft, dusk backdrop, bubble colours of the gum art."""
import os, json, math
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
BANNER = os.path.join(ROOT, "thoughts/shared/drafts/2026-11-10-round-clear-banner-final2")
meta = json.load(open(os.path.join(ROOT, "assets/font/fix_font.json")))
sheet = Image.open(os.path.join(ROOT, "assets/font/fix_font_sheet.png")); spx = sheet.load()
NAMES, PALS = meta["tiles"], {k: [tuple(c) for c in v] for k, v in meta["palettes"].items()}
def tile(i):
    x0, y0 = (i % 16) * 8, (i // 16) * 8
    return [[spx[x0 + x, y0 + y] for x in range(8)] for y in range(8)]
W, H = 320, 224
CELLS = []   # fix cells used per image (reset per image)
SPR = []     # sprite tile counts

# ---- fix layer -------------------------------------------------------------
class Fix:
    def __init__(s): s.c = {}
    def put(s, col, row, name, pal): s.c[(col, row)] = (NAMES[name], pal)
    def text(s, col, row, t, pal, backed=False):
        for i, ch in enumerate(t):
            if ch != " ": s.put(col + i, row, ("b:" if backed else "p:") + ch, pal)
    def centre(s, row, t, pal, c0=0, c1=40): s.text(c0 + (c1 - c0 - len(t)) // 2, row, t, pal)
    def right(s, col_end, row, t, pal): s.text(col_end - len(t) + 1, row, t, pal)
    def tall(s, col, row, digits, pal):   # 8x16 digits, two cells high
        for i, ch in enumerate(digits):
            s.put(col + i, row, "pt:%s:0" % ch, pal); s.put(col + i, row + 1, "pt:%s:1" % ch, pal)
    def frame(s, c0, r0, c1, r1, pal, fill=True, hole=None):
        for c in range(c0, c1 + 1):
            for r in range(r0, r1 + 1):
                k = ("t" if r == r0 else "b" if r == r1 else "") 
                k2 = ("l" if c == c0 else "r" if c == c1 else "")
                if not k and not k2:
                    if fill and not (hole and hole[0] <= c <= hole[2] and hole[1] <= r <= hole[3]): s.put(c, r, "s:fill", pal)
                else: s.put(c, r, "s:f_" + (k + k2 if k and k2 else k or k2) if False else "s:f_" + {"tl":"tl","tr":"tr","bl":"bl","br":"br","t":"t","b":"b","l":"l","r":"r"}[k + k2] , pal)
    def render(s, im):
        px = im.load()
        for (c, r), (t, pal) in s.c.items():
            p, g = PALS[pal], tile(t)
            for y in range(8):
                for x in range(8):
                    if g[y][x]: px[c * 8 + x, r * 8 + y] = p[g[y][x] - 1] + (255,)
        CELLS.append(len(s.c))

# ---- sprite text (font glyphs scaled, banded colour, shadow) ---------------
def spr_text(im, x, y, t, scale, bands, shadow=(20, 6, 40), pitch=None):
    px = im.load(); pitch = pitch or 8 * scale
    for i, ch in enumerate(t):
        if ch == " ": continue
        g = tile(NAMES["p:" + ch]); SPR.append(math.ceil(8 * scale / 16) ** 2)
        for layer in (0, 1):
            for gy in range(8):
                for gx in range(8):
                    if not g[gy][gx]: continue
                    col = shadow if layer == 0 else bands[min(len(bands) - 1, gy * len(bands) // 8)]
                    o = 0 if layer else max(1, scale // 2)
                    for dy in range(scale):
                        for dx in range(scale):
                            X, Y = x + i * pitch + gx * scale + dx + o, y + gy * scale + dy + o
                            if 0 <= X < W and 0 <= Y < H: px[X, Y] = col + (255,)
def spr_w(t, scale): return len(t) * 8 * scale
def centred_x(t, scale): return (W - spr_w(t, scale)) // 2

# ---- bubble icon (hand-placed 16 x 16, hue-shifted: shade toward violet, light toward peach) ----
BUB = ["....oooooo......", "...ooBBBBBBoo...", "..oBBlllBBBBBo..", ".oBBlwwlBBBBBBo.", ".oBlwwBBBBBBBBo.",
       "oBBlwBBBBBBBBBBo", "oBBlBBBBBBBBBBSo", "oBBBBBBBBBBBBSSo", "oBBBBBBBBBBBSSSo", "oBBBBBBBBBBSSSSo",
       "oSBBBBBBBBSSSSco", ".oSBBBBBBSSSScco.", ".oSSBBBSSSSSSco.", "..oSSSSSSSScco..", "...ooSSSSSoo....", ".....oooooo....."]
BUB = [r.ljust(16, ".")[:16] for r in BUB]
BUBCOL = {  # name -> o, S, B, l, w, c
    "pink": dict(o=(132, 16, 49), S=(181, 41, 165), B=(255, 82, 181), l=(255, 165, 222), w=(255, 255, 255), c=(255, 198, 90)),
    "gold": dict(o=(132, 60, 16), S=(206, 123, 24), B=(255, 198, 90), l=(255, 231, 156), w=(255, 255, 255), c=(255, 140, 120)),
    "dark": dict(o=(16, 8, 41), S=(24, 24, 74), B=(49, 49, 107), l=(82, 82, 148), w=(107, 115, 198), c=(24, 24, 74)),
}
def bubble(im, x, y, kind):
    px = im.load()
    for yy, row in enumerate(BUB):
        for xx, ch in enumerate(row):
            if ch == ".": continue
            if kind == "ghost":
                if ch == "o" and (xx + yy) % 2 == 0: px[x + xx, y + yy] = (107, 115, 198, 255)
            else: px[x + xx, y + yy] = BUBCOL[kind][ch] + (255,)
    if kind != "ghost": SPR.append(1)

def dither_bands(stops, h, w=W):
    """Vertical gradient between colour stops [(y, rgb)], 4x4 Bayer dither between neighbours."""
    B = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]
    im = Image.new("RGBA", (w, h)); px = im.load()
    for y in range(h):
        for (y0, c0), (y1, c1) in zip(stops, stops[1:]):
            if y0 <= y < y1:
                t = (y - y0) / (y1 - y0)
                for x in range(w):
                    px[x, y] = (c1 if t * 16 > B[y % 4][x % 4] + 0.5 else c0) + (255,)
    return im

def ledger(state):  # shared numbers
    if state == "mid": return dict(n=14, each=500, total=4500, final=7000, score=88700, perfect=False, consumed=9)
    return dict(n=20, each=500, total=10000, final=10000, score=109200, perfect=True, consumed=0, bonus=15000)

def sc(v): return "%06d" % v

# ================= LOOK A : ledger plate on the dimmed arena =================
def look_a(state):
    d = ledger(state); CELLS.clear(); SPR.clear()
    im = Image.open(os.path.join(BANNER, "backdrop_dusk_1x.png")).convert("RGBA"); px = im.load()
    for y in range(H):
        for x in range(W):
            r, g, b, _ = px[x, y]; px[x, y] = (r * 3 // 10 + 6, g * 3 // 10 + 4, b * 3 // 10 + 24, 255)
    f = Fix(); f.frame(5, 2, 34, 25, "white", hole=(8, 8, 31, 12))  # fix layer sits above sprites: leave a window for the bubble sprites
    f.centre(3, "BONUS STAGE", "gold", 5, 35)
    f.text(8, 5, "BUBBLES POPPED", "white"); f.right(31, 5, str(d["n"]), "pink")
    f.text(8, 6, "POINTS EACH", "white"); f.right(31, 6, str(d["each"]), "gold")
    for i in range(20):
        x, y = 70 + (i % 10) * 18, 64 + (i // 10) * 18
        if state == "perfect": bubble(im, x, y, "gold")
        elif i < d["consumed"]: bubble(im, x, y, "ghost")
        elif i < d["n"]: bubble(im, x, y - (12 if i == d["consumed"] else 0), "pink")
        else: bubble(im, x, y, "dark")
    for c in range(8, 32): f.put(c, 13, "s:rule", "dim")
    f.text(8, 14, "%d X %d" % (d["n"], d["each"]), "white")
    f.text(8, 16, "TOTAL", "white")
    f.tall(31 - len(str(d["total"])) + 1, 14, str(d["total"]), "gold")
    if d["perfect"]:
        f.frame(9, 17, 30, 20, "gold", fill=True)
        f.centre(18, "PERFECT", "gold", 9, 31); f.centre(19, "BONUS %d" % d["bonus"], "white", 9, 31)
    for c in range(8, 32): f.put(c, 21, "s:rule", "dim")
    f.text(8, 22, "SCORE", "white"); f.tall(31 - 5, 22, sc(d["score"]), "pink")
    f.render(im); return im

# ================= LOOK B : big sprite lettering over a dithered dusk sky =================
def look_b(state):
    d = ledger(state); CELLS.clear(); SPR.clear()
    im = dither_bands([(0, (24, 8, 66)), (60, (82, 20, 120)), (120, (181, 41, 165)), (170, (255, 82, 140)),
                       (200, (255, 148, 110)), (224, (255, 198, 90))], H)
    px = im.load()
    for x in range(W):   # low candy hill line, two shades
        top = 206 + int(5 * math.sin(x / 31.0) + 3 * math.sin(x / 11.0))
        for y in range(max(top, 0), H): px[x, y] = (132, 16, 80, 255) if y > top + 2 else (206, 60, 120, 255)
    gold = [(255, 255, 214), (255, 231, 156), (255, 198, 90), (230, 150, 50)]
    white = [(255, 255, 255), (222, 231, 255), (165, 181, 239)]
    pink = [(255, 214, 236), (255, 165, 222), (255, 82, 181)]
    t = "BONUS STAGE"; spr_text(im, centred_x(t, 3), 10, t, 3, gold, shadow=(60, 8, 60))
    t = "%d BUBBLES POPPED" % d["n"]; spr_text(im, centred_x(t, 2) if spr_w(t, 2) <= W else centred_x(t, 1), 44, t, 2 if spr_w(t, 2) <= W else 1, white, shadow=(40, 8, 60))
    t = "%d POINTS EACH" % d["each"]; spr_text(im, centred_x(t, 2), 62, t, 2, pink, shadow=(40, 8, 60))
    for i in range(20):
        x, y = i * 16, 86
        if state == "perfect": bubble(im, x, y, "gold")
        elif i < d["consumed"]: bubble(im, x, y, "ghost")
        elif i < d["n"]: bubble(im, x, y - (10 if i == d["consumed"] else 0), "pink")
        else: bubble(im, x, y, "dark")
    t = "%d X %d" % (d["n"], d["each"]); spr_text(im, centred_x(t, 2), 110, t, 2, white, shadow=(40, 8, 60))
    t = str(d["total"]); spr_text(im, centred_x(t, 3), 130, t, 3, gold, shadow=(60, 8, 60))
    if d["perfect"]:
        cx, cy = 160, 176
        for k in range(24):   # starburst rays behind the stamp
            a = k * math.pi / 12
            for r in range(26, 90 if k % 2 == 0 else 62):
                X, Y = int(cx + r * math.cos(a) * 1.7), int(cy + r * math.sin(a) * 0.45)
                if 0 <= X < W and 0 <= Y < H and (X + Y) % 2 == 0: px[X, Y] = (255, 231, 156, 255)
        t = "PERFECT"; spr_text(im, centred_x(t, 3), 160, t, 3, [(255, 255, 255), (255, 214, 236), (255, 82, 181), (181, 41, 165)], shadow=(40, 0, 50))
        t = "BONUS %d" % d["bonus"]; spr_text(im, centred_x(t, 2), 187, t, 2, gold, shadow=(60, 8, 60))
    t = "SCORE " + sc(d["score"]); spr_text(im, (W - spr_w(t, 2)) // 2, 207, t, 2, white, shadow=(60, 8, 60))
    f = Fix(); f.render(im); return im

# ================= LOOK C : bubble grid feeds a gum machine through a pipe =================
def look_c(state):
    d = ledger(state); CELLS.clear(); SPR.clear()
    im = Image.new("RGBA", (W, H), (24, 24, 74, 255)); px = im.load()
    for y in range(H):   # dark candy stripes, diagonal, hand-picked 3 tones, dithered edge
        for x in range(W):
            s = (x + y) % 32
            px[x, y] = (24, 24, 74, 255) if s < 14 else (36, 28, 90, 255) if s < 15 or s > 30 else (49, 36, 107, 255) if s < 29 else (36, 28, 90, 255)
    # bubble cage (left): 5 x 4 grid, 20 slots, in a glass frame
    for y in range(52, 160):
        for x in range(14, 120):
            edge = x in (14, 119) or y in (52, 159)
            px[x, y] = (107, 115, 198, 255) if edge else (16, 8, 41, 255)
    for i in range(20):
        x, y = 22 + (i % 5) * 19, 58 + (i // 5) * 25
        if state == "perfect": bubble(im, x, y, "gold")
        elif i < d["consumed"]: bubble(im, x, y, "ghost")
        elif i < d["n"]: bubble(im, x, y, "pink")
        else: bubble(im, x, y, "dark")
    # pipe from cage to the machine (rows: dark tube with light top edge)
    for x in range(120, 176):
        for y in range(96, 112):
            px[x, y] = (82, 148, 181, 255) if y < 99 else (24, 24, 74, 255) if y > 107 else (49, 49, 107, 255) if y > 102 else (16, 8, 41, 255)
    if state == "mid":   # a bubble in the pipe, shrunk by the pipe: trail dots
        bubble(im, 138, 96, "pink")
        for k in range(3): px[128 - k * 4, 104] = (255, 165, 222, 255)
    # machine: counter window at right
    for y in range(52, 160):
        for x in range(176, 306):
            edge = x in (176, 305) or y in (52, 159)
            px[x, y] = (255, 198, 90, 255) if edge else (132, 16, 80, 255) if y > 150 else (49, 12, 64, 255)
    f = Fix(); SPR_NOTE = 0
    f.centre(2, "BONUS STAGE", "gold"); f.centre(4, "%d POPPED   %d EACH" % (d["n"], d["each"]), "white")
    f.text(23, 7, "TOTAL", "white")
    f.text(23, 8, "%d X %d" % (d["n"], d["each"]), "pink")
    f.tall(36 - len(str(d["total"])), 10, str(d["total"]), "gold")
    for c in range(23, 38): f.put(c, 13, "s:rule", "dim")
    f.text(23, 14, "SCORE", "white"); f.text(23, 15, sc(d["score"]), "pink")
    if d["perfect"]:
        f.frame(2, 21, 37, 25, "gold", fill=True)
        f.centre(22, "PERFECT", "gold"); f.centre(23, "BONUS " + str(d["bonus"]), "white")
        f.centre(24, "ALL 20 BUBBLES POPPED", "pink")
    f.render(im); return im

def save(name, im):
    im.save(os.path.join(HERE, name + "_1x.png"))
    im.resize((W * 3, H * 3), Image.NEAREST).save(os.path.join(HERE, name + "_3x.png"))

if __name__ == "__main__":
    lines = []
    for k, fn in (("a", look_a), ("b", look_b), ("c", look_c)):
        for st in ("mid", "perfect"):
            im = fn(st); save("look_%s_%s" % (k, st), im)
            lines.append("look %s %s: fix cells %d, sprite tiles %d" % (k, st, CELLS[-1], sum(SPR)))
    open(os.path.join(HERE, "numbers.txt"), "w").write("\n".join(lines) + "\n"); print("\n".join(lines))
