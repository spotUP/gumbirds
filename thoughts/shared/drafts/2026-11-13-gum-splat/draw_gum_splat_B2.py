#!/usr/bin/env python3
"""FX-GUMSPLAT draft B2: polished variant B (elastic strands). Physics from draw_gum_splat.py (Strand, Bump, springs),
new setup (frame 0 = bare impact, strands launch later, taller) and a rule-based painter instead of gradient + Bayer.
Run: /opt/homebrew/opt/python@3.11/bin/python3.11 -I thoughts/shared/drafts/2026-11-13-gum-splat/draw_gum_splat_B2.py
Painter rules: mask from the metaball field; outline (1) on pixels whose right/below neighbour is outside;
light t = share of the up-left..down-right run that lies on the lit side -> bands 6 warm light / 5 body / 4 mid / 3 shade,
purple 9 as the cool core shadow just inside the outline; checker dither only within 0.06 of a band edge;
tip blobs get a 2 px glint (8 + 7). Rows 42..47 solid body colour 5.
"""
import importlib.util, os
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sp = importlib.util.spec_from_file_location("g", os.path.join(HERE, "draw_gum_splat.py"))
g = importlib.util.module_from_spec(sp); sp.loader.exec_module(g)
W, H, NF, STEP, SURF, PAL, TH = g.W, g.H, g.NF, g.STEP, g.SURF, g.PAL, g.TH
OUT, BODY, SH, MID, LIGHT, PURPLE, GLINT_HI, GLINT_LO = 1, 5, 3, 4, 6, 9, 8, 7
BANDS = [(0.74, LIGHT), (0.46, BODY), (0.22, MID)]   # t above edge -> colour; below last -> SH


def paint(prims, marks):
    fld = {}
    def ins(x, y):
        if x < 0 or x >= W or y < 0: return False
        if y >= SURF: return True
        if (x, y) not in fld: fld[(x, y)] = sum(p.f(x + .5, y + .5) for p in prims) >= TH
        return fld[(x, y)]
    def run(x, y, dx, dy):
        n = 0
        while n < 8 and ins(x + dx * (n + 1), y + dy * (n + 1)): n += 1
        return n
    img = Image.new("RGBA", (W, H), PAL[0]); px = img.load()
    for y in range(H):
        for x in range(W):
            if not ins(x, y): continue
            if y >= SURF: px[x, y] = PAL[BODY]; continue
            if not ins(x + 1, y) or (not ins(x, y + 1)):
                px[x, y] = PAL[OUT]; continue
            a, b = run(x, y, -1, -1), run(x, y, 1, 1)         # steps to the lit edge / to the shadow edge
            if b <= 1 and a >= 1: px[x, y] = PAL[PURPLE]; continue   # cool shadow band inside the outline
            t = (b + 0.5) / (a + b + 1.0)
            col, edge = SH, 1.0
            for e, c in BANDS:
                if t >= e: col = c; break
            for e, c in BANDS:                                     # dither only against the neighbouring band
                if abs(t - e) < 0.06 and (x + y) % 2:
                    col = [c2 for e2, c2 in BANDS + [(0, SH)] if (e2 < e)][0] if t >= e else c
            px[x, y] = PAL[col]
    for mx, my, big in marks:
        x, y = int(mx), int(my)
        for dx, dy, c in ([(0, 0, GLINT_HI), (1, 0, GLINT_LO)] if big else [(0, 0, GLINT_LO)]):
            if 0 <= x + dx < W and 0 <= y + dy < SURF and px[x + dx, y + dy][3] and px[x + dx, y + dy] != PAL[OUT]:
                px[x + dx, y + dy] = PAL[c]
    return img


class LStrand(g.Strand):             # same springs, but sleeps until its launch tick
    def __init__(s, delay, *a): super().__init__(*a); s.delay = delay


def setup():
    #            delay ax    vx    vy    n  rest kmax tipr snap
    sts = [LStrand(5, 18, -1.0, -5.4, 11, 3.0, 2.8, 3.2, 4), LStrand(4, 22, -0.3, -5.7, 13, 3.1, 2.9, 4.0, 7),
           LStrand(5, 25, 0.4, -5.6, 12, 3.0, 3.0, 3.4, 5), LStrand(6, 28, 1.0, -5.4, 11, 2.9, 2.7, 3.0, 5),
           LStrand(7, 32, 1.8, -4.2, 9, 2.6, 2.5, 2.6, 3)]
    return dict(st=sts, bumps=[g.Bump(24, 0.6, 5.0, 0.55)], peak=[99.0] * 5)


def tick(s, t):
    for b in s["bumps"]: b.step()
    for k, st in enumerate(s["st"]):
        if t < st.delay: continue
        was = list(st.dead); st.step()
        s["peak"][k] = min(s["peak"][k], st.py[-1])
        for i in range(st.n):
            if st.dead[i] and not was[i] and i == st.n - 1:
                s["bumps"].append(g.Bump(st.px[i], st.tipr * 0.9, st.tipr * 1.6, 1.0))


def prims(s, t):
    pr, marks = [b.prim() for b in s["bumps"]], []
    for st in s["st"]:
        if t < st.delay: continue
        for i in range(st.n - 1):
            if st.dead[i] and st.dead[i + 1] or st.cut[i]: continue
            L = g.math.hypot(st.px[i + 1] - st.px[i], st.py[i + 1] - st.py[i])
            w = max(0.8, min(2.1, 2.1 * g.math.sqrt(st.rest / max(L, 0.1))))
            pr.append(g.link(st.px[i], st.py[i], st.px[i + 1], st.py[i + 1], w))
        for i in range(st.n):
            if st.dead[i]: continue
            tip = i == st.n - 1
            pr.append(g.blob(st.px[i], st.py[i], st.tipr if tip else 1.2, st.vx[i], st.vy[i], 1.0))
            if tip: marks.append((st.px[i] - st.tipr * .35, st.py[i] - st.tipr * .4, st.tipr > 2.4))
    return pr, marks


if __name__ == "__main__":
    s = setup(); sheet = Image.new("RGBA", (W * NF, H), PAL[0])
    for t in range(NF * STEP):
        tick(s, t)
        if t % STEP == 0:
            pr, mk = prims(s, t); sheet.paste(paint(pr, mk), ((t // STEP) * W, 0))
    sheet.save(os.path.join(HERE, "gum_splat_B2.png"))
    used = {p[:3] for p in sheet.getdata() if p[3]}
    assert used <= {c[:3] for c in PAL[1:]}
    print("tip peaks above surface (px):", [round(SURF - 1 - p, 1) for p in s["peak"]])
    top = min(y for y in range(H) for x in range(W * NF) if sheet.getpixel((x, y))[3])
    print("highest painted row:", top, "-> height", SURF - top)
