#!/usr/bin/env python3
"""FX-GUMSPLAT draft B3: lighter, rounder, smoother B2. Same setup/physics/frames as B2.
Changes: outline 1 px only on the shadow edge (right/below) of wide parts, thin strands use mid tone; thinner purple band
(only where the part is >= 3 px wide); light bands lifted; tip blobs are round discs (r 3..5) with sphere shading and a 2 px glint;
mask cleanup removes 1 px spikes and fills 1 px notches so strand silhouettes are smooth.
Run: /opt/homebrew/opt/python@3.11/bin/python3.11 -I thoughts/shared/drafts/2026-11-13-gum-splat/draw_gum_splat_B3.py
"""
import importlib.util, os
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sp = importlib.util.spec_from_file_location("b2", os.path.join(HERE, "draw_gum_splat_B2.py"))
b2 = importlib.util.module_from_spec(sp); sp.loader.exec_module(b2)
g = b2.g
W, H, NF, STEP, SURF, PAL, TH = b2.W, b2.H, b2.NF, b2.STEP, b2.SURF, b2.PAL, b2.TH
OUT, BODY, SH, MID, LIGHT, PURPLE, GLINT_HI, GLINT_LO = b2.OUT, b2.BODY, b2.SH, b2.MID, b2.LIGHT, b2.PURPLE, b2.GLINT_HI, b2.GLINT_LO
BANDS = [(0.58, LIGHT), (0.28, BODY), (0.10, MID)]


def prims3(s, t):
    pr, _ = b2.prims(s, t); tips = []
    for st in s["st"]:
        if t >= st.delay and not st.dead[-1]:
            tips.append((st.px[-1], st.py[-1], max(3.0, min(5.0, st.tipr + 0.8))))
    return pr, tips


def paint(prims, tips):
    m = {}
    for y in range(H):
        for x in range(W):
            m[x, y] = y >= SURF or sum(p.f(x + .5, y + .5) for p in prims) >= TH
    disc = {}
    for cx, cy, r in tips:
        for y in range(H):
            for x in range(W):
                if (x + .5 - cx) ** 2 + (y + .5 - cy) ** 2 <= r * r and y < SURF:
                    m[x, y] = True; disc[x, y] = (cx, cy, r)
    def ins(x, y): return 0 <= x < W and y >= 0 and (y >= SURF or m.get((x, y), False))
    for _ in range(2):                                   # smooth: drop spikes, fill notches
        for (x, y), v in list(m.items()):
            if y >= SURF or (x, y) in disc: continue
            n = sum(ins(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            if v and n <= 1 and y < SURF - 1: m[x, y] = False
            elif not v and n >= 3: m[x, y] = True
    def run(x, y, dx, dy):
        n = 0
        while n < 8 and ins(x + dx * (n + 1), y + dy * (n + 1)): n += 1
        return n
    img = Image.new("RGBA", (W, H), PAL[0]); px = img.load()
    for y in range(H):
        for x in range(W):
            if not ins(x, y): continue
            if y >= SURF: px[x, y] = PAL[BODY]; continue
            edge = not ins(x + 1, y) or not ins(x, y + 1)
            inner = ins(x - 1, y) or ins(x, y - 1)
            if (x, y) in disc:
                cx, cy, r = disc[x, y]
                u = -((x + .5 - cx) + (y + .5 - cy)) * 0.7071 / r      # +1 up-left, -1 down-right
                if edge and inner and u < -0.2: px[x, y] = PAL[OUT]; continue
                col = LIGHT if u > 0.4 else BODY if u > -0.05 else MID if u > -0.45 else SH
                if col == SH and u < -0.7 and (x + y) % 2 == 0: col = PURPLE
                px[x, y] = PAL[col]; continue
            if edge:
                px[x, y] = PAL[OUT] if (inner and run(x, y, -1, -1) >= 2) else PAL[MID]; continue
            a, b = run(x, y, -1, -1), run(x, y, 1, 1)
            if b <= 1 and a >= 3: px[x, y] = PAL[PURPLE]; continue
            tt = (b + 0.5) / (a + b + 1.0); col = SH
            for e, c in BANDS:
                if tt >= e: col = c; break
            px[x, y] = PAL[col]
    for cx, cy, r in tips:
        x, y = int(cx - r * .4), int(cy - r * .45)
        for dx, c in ((0, GLINT_HI), (1, GLINT_LO)):
            if px[x + dx, y][3] and px[x + dx, y] != PAL[OUT]: px[x + dx, y] = PAL[c]
    return img


if __name__ == "__main__":
    s = b2.setup(); sheet = Image.new("RGBA", (W * NF, H), PAL[0])
    for t in range(NF * STEP):
        b2.tick(s, t)
        if t % STEP == 0:
            pr, tp = prims3(s, t); sheet.paste(paint(pr, tp), ((t // STEP) * W, 0))
    sheet.save(os.path.join(HERE, "gum_splat_B3.png"))
    used = {p[:3] for p in sheet.getdata() if p[3]}
    assert used <= {c[:3] for c in PAL[1:]}
    top = min(y for y in range(H) for x in range(W * NF) if sheet.getpixel((x, y))[3])
    print("highest painted row:", top, "-> height", SURF - top)
