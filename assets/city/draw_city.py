#!/usr/bin/env python3
"""City background art: Python/Pillow port of the background drawing code of design/roofline-test-v5.html
(drawSky/Lights/Moon/Clouds/Far/Mid/Roof), original art, no external source. Differences from v5:
  * x is a 320 px torus (every layer wraps seamlessly; edge buildings were nudged to leave the v5 gaps),
  * the roof line is GROUND = 176 (game GROUND_Y), roof deck is continuous (no ledge drop) and its 16 px
    columns vary over the 320 px period so the scroll is visible and measurable,
  * lamps are baked into the layer as lampOn + white corner; the game blinks them by palette swap.
Writes assets/city/city_sheet.png (RGBA, alpha 0/255) and city_sheet.json for tools/sprite_pipeline.py.
Usage: python3.14 -I assets/city/draw_city.py   (run from the repo root; output is committed)"""
import json, os
from PIL import Image

W, H = 320, 224
GROUND = 176
HERE = os.path.dirname(os.path.abspath(__file__))


def q5(v):
    n = max(0, min(31, round(v * 31 / 255)))
    return (n << 3) | (n >> 2)


def C(h):
    n = int(h.lstrip("#"), 16)
    return (q5((n >> 16) & 255), q5((n >> 8) & 255), q5(n & 255))


class Buf:
    def __init__(self, w=W, h=H):
        self.w, self.h, self.d = w, h, [[None] * w for _ in range(h)]
    def set(self, x, y, c):
        x, y = int(x), int(y)
        if c is None or y < 0 or y >= self.h:
            return
        self.d[y][x % self.w] = c  # x wraps: 320 px torus
    def get(self, x, y):
        x, y = int(x), int(y)
        return None if y < 0 or y >= self.h else self.d[y][x % self.w]
    def rect(self, x, y, w, h, c):
        for j in range(int(y), int(y + h)):
            for i in range(int(x), int(x + w)):
                self.set(i, j, c)
    def blit(self, src, ox=0, oy=0):
        for j in range(src.h):
            for i in range(src.w):
                if src.d[j][i] is not None:
                    self.set(ox + i, oy + j, src.d[j][i])


def stamp(L, x, y, rows, m):
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch != "." and m.get(ch) is not None:
                L.set(x + i, y + j, m[ch])


def disc(L, cx, cy, r, c):
    import math
    for y in range(math.floor(cy - r), math.ceil(cy + r) + 1):
        for x in range(math.floor(cx - r), math.ceil(cx + r) + 1):
            if (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2 <= r * r:
                L.set(x, y, c)


def outline(L, c):
    s = [row[:] for row in L.d]
    for y in range(L.h):
        for x in range(L.w):
            if s[y][x] is not None:
                continue
            for j in (-1, 0, 1):
                Y = y + j
                if Y < 0 or Y >= L.h:
                    continue
                if any(s[Y][(x + i) % L.w] is not None for i in (-1, 0, 1)):
                    L.d[y][x] = c
                    break


P = dict(
    ink=C("#120a26"), white=C("#ffffff"), star=C("#8a98e8"), starW=C("#e0e8ff"),
    moonHi=C("#fff6c8"), moon=C("#f8d050"), moonSh=C("#e08a4a"), moonDk=C("#9a4a6e"), moonInk=C("#4a2048"),
    cloud=C("#34224e"), cloudHi=C("#523a6e"), cloudInk=C("#1e1236"),
    far=C("#22153a"), farSh=C("#1a1030"), farRim=C("#5a2e72"), farInk=C("#120a22"),
    farStrip=C("#7a2a6a"), farStripM=C("#a8406e"),
    mid=C("#28122f"), midSh=C("#1c0c25"), midHi=C("#3c1c48"), midRim=C("#c0508a"), midInk=C("#140a1e"),
    pipeD=C("#3a1a3a"), pipe=C("#6a2e5a"), pipeHi=C("#b05a8a"),
    glow=C("#a0287a"), glowCore=C("#f070b0"), warm=C("#b8642a"), warmCore=C("#e0a850"),
    roofGlow=C("#e04a8a"), roofGlowCore=C("#ffc0dc"), lampOn=C("#ff3a4a"),
    stQ=C("#e0c8d8"), stP=C("#9a7aa0"), stp=C("#5e3e6a"), stv=C("#4a2a30"),
)
SKY = "#1a1238"  # backdrop colour (palette RAM last entry, see plan B2)
STARS = [(12, 34, 1), (30, 70, 0), (52, 30, 0), (70, 84, 1), (96, 40, 1), (118, 66, 0), (134, 32, 0), (150, 56, 1),
         (172, 38, 0), (186, 74, 1), (200, 30, 1), (214, 58, 0), (292, 36, 1), (304, 80, 0), (8, 92, 0), (160, 86, 0)]
LAMPS = []


def lamp(L, x, y):
    L.rect(x, y, 2, 2, P["lampOn"])
    L.set(x, y, P["white"])


def bars(L, lst):
    for x, y, w, h in lst:
        L.rect(x + 2, y, w - 4, h, P["cloud"]); L.rect(x, y + 1, w, h - 2, P["cloud"]); L.rect(x + 3, y, w - 8, 1, P["cloudHi"])


def draw_moon_block():
    """Moon with the two right-hand cloud bars over it, crop x 208..288, y 32..80."""
    MX, MY, MR = 258, 54, 21
    L = Buf()
    disc(L, MX, MY, MR, P["moon"])
    for y in range(MY - MR, MY + MR + 1):
        for x in range(MX - MR, MX + MR + 1):
            if L.get(x, y) is None:
                continue
            a = (x + .5 - MX + 5) ** 2 + (y + .5 - MY + 5) ** 2
            b = (x + .5 - MX + 9) ** 2 + (y + .5 - MY + 9) ** 2
            if b > (MR + 1) ** 2: L.set(x, y, P["moonDk"])
            elif a > MR * MR: L.set(x, y, P["moonSh"])
            elif (x + .5 - MX + 7) ** 2 + (y + .5 - MY + 7) ** 2 < 49: L.set(x, y, P["moonHi"])
    for dx, dy, r in [(2, 2, 3.2), (-8, 6, 2.4), (9, -6, 2.2), (4, 11, 1.8)]:
        disc(L, MX + dx, MY + dy, r, P["moonSh"]); disc(L, MX + dx + .6, MY + dy + .6, r - 1, P["moonDk"])
    L.rect(MX - 11, MY - 13, 3, 2, P["white"]); L.set(MX - 13, MY - 10, P["white"])
    outline(L, P["moonInk"])
    K = Buf()
    bars(K, [(216, 62, 58, 5), (240, 70, 46, 4)])
    outline(K, P["cloudInk"])
    L.blit(K)
    return L


def draw_clouds_left():
    K = Buf()
    bars(K, [(20, 50, 64, 5), (44, 58, 40, 4)])
    outline(K, P["cloudInk"])
    return K


# Far towers: x, w, top, roof. Edge buildings moved so the 320 px torus keeps the v5 gaps (last ends at 318).
FAR = [(0, 30, 116, "flat"), (28, 18, 96, "spire"), (44, 34, 122, "step"), (76, 22, 92, "mast"), (96, 38, 110, "flat"),
       (132, 24, 100, "spire"), (154, 36, 112, "step"), (188, 26, 96, "mast"), (212, 36, 118, "flat"),
       (246, 22, 104, "step"), (266, 34, 94, "mast"), (296, 22, 112, "flat")]


def draw_far():
    L = Buf()
    lamps = []
    for b, (x, w, top, roof) in enumerate(FAR):
        L.rect(x, top, w, H - top, P["far"]); L.rect(x, top, 3, H - top, P["farSh"])
        if roof == "step":
            L.rect(x + 4, top - 6, w - 8, 6, P["far"]); L.rect(x + 4, top - 6, 3, 6, P["farSh"])
        if roof == "spire":
            for k in range(12):
                L.rect(x + w // 2 - 1 - k // 4, top - 12 + k, 2 + 2 * (k // 4), 1, P["far"])
        if roof == "mast":
            L.rect(x + w // 2 - 1, top - 14, 2, 14, P["farSh"]); lamps.append((x + w // 2 - 1, top - 16))
        L.rect(x + w - 1, top, 1, H - top, P["farRim"])
        j, wy = 0, top + 6
        while wy < GROUND:
            if (j + b) % 3 != 1:
                L.rect(x + 5, wy, w - 9, 1, P["farStripM"] if (j + b) % 5 == 0 else P["farStrip"])
            wy += 7; j += 1
    outline(L, P["farInk"])
    for lx, ly in lamps:
        lamp(L, lx, ly)
    return L


MID = [(2, 40, 140, "pipe"), (44, 30, 126, "mast"), (78, 46, 146, "pipe"), (128, 32, 132, "tank"), (164, 40, 150, "pipe"),
       (208, 30, 136, "mast"), (242, 44, 144, "pipe"), (286, 32, 130, "tank")]


def mid_building(x, w, top, extra, b):
    T = Buf()
    T.rect(x, top, w, H - top, P["mid"]); T.rect(x, top, 4, H - top, P["midSh"])
    T.rect(x - 1, top - 3, w + 2, 3, P["midHi"]); T.rect(x - 1, top - 3, 4, 3, P["mid"]); T.rect(x - 1, top - 1, w + 2, 1, P["midSh"])
    T.rect(x + w - 1, top - 3, 1, H - top + 3, P["midRim"])
    for py in range(top + 14, H, 14):
        T.rect(x + 4, py, w - 5, 1, P["midSh"]); T.set(x + 6, py + 2, P["midHi"]); T.set(x + w - 4, py + 2, P["midHi"])
    j, wy = 0, top + 5
    while wy + 3 < H:
        warm, off = (j + b) % 4 == 1, (j * 3 + b) % 5 == 4
        if off:
            T.rect(x + 7, wy, w - 13, 3, P["midSh"])
        else:
            T.rect(x + 7, wy, w - 13, 3, P["warm"] if warm else P["glow"])
            T.rect(x + 8, wy + 1, w - 15, 1, P["warmCore"] if warm else P["glowCore"])
            T.set(x + 8, wy, P["warmCore"] if warm else P["glowCore"])
        wy += 14; j += 1
    if extra == "pipe":
        px = x + w - 8
        T.rect(px, top, 3, H - top, P["pipe"]); T.rect(px, top, 1, H - top, P["pipeD"]); T.rect(px + 2, top, 1, H - top, P["pipeHi"])
        for by in range(top + 9, H, 14):
            T.rect(px - 1, by, 5, 2, P["midSh"])
    lamp_at = None
    if extra == "mast":
        T.rect(x + w // 2 - 1, top - 20, 2, 17, P["midSh"]); T.rect(x + w // 2, top - 20, 1, 17, P["midRim"])
        T.rect(x + w // 2 - 5, top - 13, 10, 1, P["midSh"]); lamp_at = (x + w // 2 - 1, top - 23)
    if extra == "tank":
        cx = x + w // 2
        T.rect(cx - 7, top - 7, 2, 4, P["midSh"]); T.rect(cx + 5, top - 7, 2, 4, P["midSh"])
        T.rect(cx - 8, top - 16, 16, 9, P["pipe"]); T.rect(cx - 8, top - 16, 4, 9, P["pipeD"]); T.rect(cx + 6, top - 16, 2, 9, P["pipeHi"])
        T.rect(cx - 8, top - 12, 16, 1, P["pipeD"]); T.rect(cx - 6, top - 15, 2, 1, P["pipeHi"])
    outline(T, P["midInk"])
    return T, lamp_at


def draw_mid():
    L = Buf()
    lamps = []
    for b, (x, w, top, extra) in enumerate(MID):
        T, la = mid_building(x, w, top, extra, b)
        L.blit(T)
        if la:
            lamps.append(la)
    for lx, ly in lamps:
        lamp(L, lx, ly)
    return L


CAP = ["KKKKKKKKKKKKKKKK", "QWWQQQQQQQQQQQQQ", "PPPPPPPPPPPPPPPP", "PPQPPPPPPPPPPQPP", "PPPPPPPPPPPPPPPP",
       "pppppppppppppppp", "vvvvvvvvvvvvvvvv", "KKKKKKKKKKKKKKKK"]
FACE_A = ["pPPPPPPPPPPPPPPK", "pQPPPPPPPPPPPQPK", "pPPPPPPPPPPPPPPK", "pPPPPPPPPPPPPPPK", "pppppppppppppppK",
          "KKKKKKKKKKKKKKKK", "vggggggggggggggv", "vgGGGGWGGGGGGGgv", "vggggggggggggggv", "KKKKKKKKKKKKKKKK",
          "pPPPPPPPPPPPPPPK", "pQPPPPPPPPPPPQPK", "pPPPPPPPPPPPPPPK", "pPPPPPPPPPPPPPPK", "pppppppppppppppK", "vvvvvvvvvvvvvvvK"]
FACE_B = ["pPPPPPPPPPPPPPPK", "pQPPPPPPPPPPPQPK", "pPPKKKKKKKKKPPPK", "pPPvvvvvvvvvQPPK", "pPPKKKKKKKKKPPPK",
          "pPPvvvvvvvvvQPPK", "pPPKKKKKKKKKPPPK", "pPPvvvvvvvvvQPPK", "pPPPPPPPPPPPPPPK", "pQPPPPPPPPPPPQPK",
          "pPPPPPPPPPPPPPPK", "pppppppppppppppK", "vvvvvvvvvvvvvvvK", "KKKKKKKKKKKKKKKK", "vvvvvvvvvvvvvvvK", "vvvvvvvvvvvvvvvK"]
FOOT = ["KKKKKKKKKKKKKKKK"] + ["vvvvvvvvvvvvvvvK"] * 7
# Column variants over the 20 column period: 0 = A over B (v5), 1 = B over A, 2 = A over A, 3 = B over B.
ROOF_COLS = [0, 2, 1, 1, 3, 0, 0, 2, 3, 1, 2, 0, 3, 3, 1, 0, 2, 2, 1, 3]


def draw_roof():
    L = Buf()
    m = dict(K=P["ink"], W=P["white"], Q=P["stQ"], P=P["stP"], p=P["stp"], v=P["stv"], g=P["roofGlow"], G=P["roofGlowCore"])
    for c, v in enumerate(ROOF_COLS):
        top, bot = {0: (FACE_A, FACE_B), 1: (FACE_B, FACE_A), 2: (FACE_A, FACE_A), 3: (FACE_B, FACE_B)}[v]
        x = c * 16
        stamp(L, x, GROUND, CAP, m); stamp(L, x, GROUND + 8, top, m)
        stamp(L, x, GROUND + 24, bot, m); stamp(L, x, GROUND + 40, FOOT, m)
    return L


def star_tiles():
    d, p = Buf(16, 16), Buf(16, 16)
    d.set(8, 8, P["star"])
    p.rect(7, 8, 3, 1, P["star"]); p.rect(8, 7, 1, 3, P["star"]); p.set(8, 8, P["starW"])
    return d, p


def main():
    far, mid, roof = draw_far(), draw_mid(), draw_roof()
    moon, cl = draw_moon_block(), draw_clouds_left()
    dot, plus = star_tiles()
    # (animation, name, source buffer, crop x, y, w, h, sheet x, y)
    FAR_Y0, MID_Y0, ROOF_Y0 = 64, 96, 176
    parts = [
        ("far", far, 0, FAR_Y0, 320, 112, 0, 0),
        ("mid", mid, 0, MID_Y0, 320, 80, 0, 112),
        ("roof", roof, 0, ROOF_Y0, 320, 48, 0, 192),
        ("sky", moon, 208, 32, 80, 48, 0, 240),
        ("sky", cl, 16, 48, 80, 16, 96, 240),
        ("sky", dot, 0, 0, 16, 16, 192, 240),
        ("sky", plus, 0, 0, 16, 16, 208, 240),
    ]
    sheet = Image.new("RGBA", (320, 288), (0, 0, 0, 0))
    px = sheet.load()
    anims = {}
    for name, buf, cx, cy, w, h, sx, sy in parts:
        for y in range(h):
            for x in range(w):
                c = buf.d[cy + y][cx + x]
                if c is not None:
                    px[sx + x, sy + y] = c + (255,)
        anims.setdefault(name, []).append(dict(x=sx, y=sy, w=w, h=h))
    # per-layer palette report (pipeline enforces <= 15 colours per animation and per tile)
    for name in ("far", "mid", "roof", "sky"):
        cols = set()
        for r in anims[name]:
            for y in range(r["y"], r["y"] + r["h"]):
                for x in range(r["x"], r["x"] + r["w"]):
                    if px[x, y][3]:
                        cols.add(px[x, y][:3])
        print("%s: %d colours" % (name, len(cols)))
        assert len(cols) <= 15, name
    sheet.save(os.path.join(HERE, "city_sheet.png"))
    meta = dict(
        source="original art, Python port of design/roofline-test-v5.html background drawing; assets/city/draw_city.py",
        origin="sheet rows: far y0..112 = screen y 64..176 (tile rows 4..10); mid y112..192 = screen y 96..176 (rows 6..10); "
               "roof y192..240 = screen y 176..224 (rows 11..13). All 320 px wide = 20 tile columns, torus period 320 px. "
               "sky frames: 0 moon+clouds (screen 208,32), 1 left clouds (screen 16,48), 2 star dot, 3 star plus (16x16, star pixel at 8,8).",
        backdrop=SKY, lamp_on=P["lampOn"], palette_policy="subset", animations=anims)
    meta["lamp_on"] = "#%02x%02x%02x" % P["lampOn"]
    json.dump(meta, open(os.path.join(HERE, "city_sheet.json"), "w"), indent=1)


main()
