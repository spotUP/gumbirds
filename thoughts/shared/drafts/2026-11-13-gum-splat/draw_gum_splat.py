#!/usr/bin/env python3
"""FX-GUMSPLAT draft: 3 gum splat variants for Gum Trip, motion from small physics simulations.
Run: /opt/homebrew/opt/python@3.11/bin/python3.11 -I thoughts/shared/drafts/2026-11-13-gum-splat/draw_gum_splat.py
Writes <A|B|C>_gum_splat_1x.png (576 x 48 = 12 frames of 48 x 48, colour 0 transparent) next to itself (index.html is static).
Frame geometry = assets/splash/splash.json: anchor_x 24, surface_row 42 (gum floor rim row), rows 42..47 solid body colour.
Palette = the 10 gum colours of assets/tripstrip/tripstrip_sheet.json (asserted at the end).
Method: every tick the simulation moves blobs / strand nodes / bumps; each STEP ticks a frame is rendered as a metaball
field (Wyvill kernel), shaded from the field gradient with light from the upper left, 4x4 Bayer dither between ramp
steps, dark outline on the shadow side, hand-placed specular pixels (7, warm glint 9).
"""
import math, os, random
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
W = H = 48
NF, STEP = 12, 4                    # 12 frames, 4 ticks (1/60 s) per frame -> 0.8 s
SURF = 42
G = 0.12                            # px / tick^2
PAL = [(0, 0, 0, 0), (24, 0, 33), (57, 8, 57), (115, 24, 107), (181, 41, 123), (239, 74, 140),
       (255, 140, 156), (255, 214, 198), (255, 247, 247), (74, 24, 123), (255, 181, 82)]
# palette index names: 1 outline, 2 deep, 3 shade, 4 mid, 5 body, 6 light, 7 pale, 8 white, 9 purple shadow, 10 warm glint
RAMP = [9, 2, 3, 4, 5, 6]           # dark -> light; 9 is the hue-shifted shadow
OUT, BODY, SPEC, SPEC2, GLINT = 1, 5, 8, 7, 10
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]
TH = 0.3


def kernel(d2):                      # Wyvill; 0.3 threshold -> visible radius ~0.67 * R
    return (1 - d2) ** 2 if d2 < 1 else 0.0


class Prim:                          # ellipse (blob) or capsule (strand link) contributing to the field
    def __init__(self, kind, **k):
        self.kind = kind; self.__dict__.update(k)

    def f(s, x, y):
        if s.kind == "blob":
            dx, dy = x - s.x, y - s.y
            u = dx * s.c + dy * s.s; v = -dx * s.s + dy * s.c
            return s.k * kernel((u / s.a) ** 2 + (v / s.b) ** 2)
        ax, ay, bx, by = s.ax, s.ay, s.bx, s.by
        vx, vy = bx - ax, by - ay
        l2 = vx * vx + vy * vy or 1e-6
        t = max(0, min(1, ((x - ax) * vx + (y - ay) * vy) / l2))
        d2 = (x - ax - t * vx) ** 2 + (y - ay - t * vy) ** 2
        return kernel(d2 / (s.R * s.R))


def blob(x, y, r, vx=0.0, vy=0.0, stretch=1.0, k=1.0, ang=None, flat=1.0):
    """r = visible radius (area radius); stretch >1 elongates along the given/velocity direction, area kept."""
    sp = math.hypot(vx, vy)
    a = ang if ang is not None else math.atan2(vy, vx)
    s = stretch if stretch != 1.0 else 1 + min(0.9, sp * 0.22)
    R = r / 0.67
    return Prim("blob", x=x, y=y, a=R * math.sqrt(s) / math.sqrt(flat), b=R / math.sqrt(s) * math.sqrt(flat),
                c=math.cos(a), s=math.sin(a), k=k)


def link(ax, ay, bx, by, w):
    return Prim("link", ax=ax, ay=ay, bx=bx, by=by, R=w / 0.67)


def render(prims, film=False, marks=()):
    fld = [[0.0] * (W + 2) for _ in range(H + 2)]     # 1 px margin for gradients
    for yy in range(-1, H + 1):
        for xx in range(-1, W + 1):
            if yy >= SURF:
                fld[yy + 1][xx + 1] = 9.0; continue
            fld[yy + 1][xx + 1] = sum(p.f(xx + .5, yy + .5) for p in prims)
    F = lambda x, y: fld[y + 1][x + 1]
    ins = lambda x, y: F(x, y) >= TH
    out = Image.new("RGBA", (W, H), PAL[0])
    px = out.load()
    for y in range(H):
        for x in range(W):
            if not ins(x, y): continue
            if y >= SURF:
                px[x, y] = PAL[5 if (x + y) % 2 else 4]; continue
            f = F(x, y)
            gx = F(x + 1, y) - F(x - 1, y); gy = F(x, y + 1) - F(x, y - 1)
            n = math.hypot(gx, gy) or 1e-6
            lit = (gx + gy) / (n * 1.414)             # +1: surface faces upper left
            depth = min(1.0, (f - TH) / 0.45)
            sh = 0.50 + 0.34 * lit * min(1.0, n * 2.2) + 0.22 * depth - 0.12
            # outline on the shadow side (outside neighbour right / below), lit rim one ramp step darker
            edge_shadow = not ins(x + 1, y) or not ins(x, y + 1)
            edge_lit = not ins(x - 1, y) or not ins(x, y - 1)
            if edge_shadow and not (y == SURF - 1 and ins(x, y + 1)):
                px[x, y] = PAL[OUT]; continue
            if edge_lit:
                sh = max(sh, 0.62) if lit > 0.3 else sh - 0.1
            p = max(0.0, min(1.0, sh)) * (len(RAMP) - 1)
            i = int(p); fr = p - i
            if i < len(RAMP) - 1 and fr * 16 > BAYER[y & 3][x & 3] + 0.5 and 0.2 < fr < 0.8: i += 1
            elif i < len(RAMP) - 1 and fr >= 0.8: i += 1
            col = RAMP[i]
            if lit < -0.55 and depth > 0.35 and BAYER[y & 3][x & 3] < 3:
                col = GLINT                                  # warm bounce light on the lower right inside
            px[x, y] = PAL[col]
    for (mx, my, big) in marks:                                # hand-placed specular on bigger blobs
        for dx, dy, c in ([(0, 0, SPEC), (1, 0, SPEC2), (0, 1, SPEC2), (-1, 0, 6), (0, -1, 6)] if big else [(0, 0, SPEC2)]):
            x, y = int(mx) + dx, int(my) + dy
            if 0 <= x < W and 0 <= y < SURF and px[x, y][3] and px[x, y] != PAL[OUT] and ins(x, y):
                px[x, y] = PAL[c]
    return out


# ------------------------------------------------------------------ shared physics bits
class Bump:                          # gum mound on the floor: damped spring, one wobble
    def __init__(s, x, h, w, vh=0.0):
        s.x, s.h, s.w, s.vh = x, h, w, vh
    def step(s):
        s.vh += -0.075 * s.h * 0.55 - 0.085 * s.vh
        s.h += s.vh; s.w += (6 - s.w) * 0.0
    def prim(s):
        h = max(s.h, 0.0)
        return Prim("blob", x=s.x, y=SURF + 0.3, a=max(1.0, s.w) / 0.67 * 0.9, b=max(0.3, h) / 0.67, c=1.0, s=0.0, k=1.0)


def sim_frames(setup, tick, sample_marks):
    st = setup()
    frames = []
    for t in range(NF * STEP):
        tick(st, t)
        if t % STEP == 0:
            prims, marks = sample_marks(st, t)
            frames.append(render(prims, marks=marks))
    return frames


# ------------------------------------------------------------------ A: thick blob burst and drip
def a_setup():
    rnd = random.Random(7)
    bl = []
    # (vx, vy, r): a fan of fat blobs, the middle one is the big glob that sheds a drip
    for vx, vy, r in [(-1.5, -1.5, 3.4), (-0.7, -1.9, 3.8), (0.1, -2.35, 5.4), (0.9, -1.8, 4.0), (1.6, -1.4, 3.2), (-2.4, -0.8, 2.6), (2.4, -0.7, 2.8)]:
        bl.append(dict(x=24 + vx * 1.3, y=SURF - 2, vx=vx, vy=vy + rnd.uniform(-.1, .1), r=r, alive=True, drip=False))
    return dict(bl=bl, bumps=[Bump(24, 3.0, 8.5, 1.9)], drips=[], rnd=rnd)

def a_tick(s, t):
    for b in s["bumps"]: b.step()
    for b in s["bl"]:
        if not b["alive"]: continue
        b["vy"] += G; b["x"] += b["vx"]; b["y"] += b["vy"]; b["vx"] *= 0.995
        if b["r"] > 5 and not b["drip"] and b["vy"] > -0.3 and b["y"] < SURF - 10:   # big glob pinches a drip bead at its apex
            b["drip"] = True; b["r"] *= 0.82
            s["bl"].append(dict(x=b["x"], y=b["y"] + 4, vx=0.0, vy=0.15, r=2.3, alive=True, drip=True))
        if b["y"] > SURF - b["r"] * 0.3 and b["vy"] > 0:
            b["alive"] = False
            s["bumps"].append(Bump(b["x"], b["r"] * 1.15, b["r"] * 1.7, b["vy"] * 0.5))     # lands, splats flat, wobbles

def a_prims(s, t):
    pr, marks = [b.prim() for b in s["bumps"]], []
    for b in s["bl"]:
        if not b["alive"]: continue
        sp = math.hypot(b["vx"], b["vy"])
        pr.append(blob(b["x"], b["y"], b["r"], b["vx"], b["vy"], 1 + min(0.6, sp * 0.2)))
        if b["r"] > 2.3: marks.append((b["x"] - b["r"] * .35, b["y"] - b["r"] * .4, b["r"] > 3))
        # trailing sticky thread to the floor while the blob is low and fast (stretch tail)
        if b["y"] > SURF - 22 and b["vy"] < 0 and b["r"] > 2.3:
            tx = 24 + (b["x"] - 24) * 0.25
            pr.append(link(tx, SURF - 1, b["x"], b["y"] + b["r"] * 0.5, max(1.5, b["r"] * 0.55)))
    return pr, marks


# ------------------------------------------------------------------ B: elastic strands that snap back
class Strand:
    def __init__(s, ax, vx, vy, n, rest, kmax, tipr, snap_link):
        s.n = n; s.rest = rest; s.tipr = tipr; s.snap = snap_link; s.kmax = kmax; s.broken = False
        s.px = [ax + i * 0.01 for i in range(n)]; s.py = [SURF - 1 - i * 0.2 for i in range(n)]
        s.vx = [0.0] * n; s.vy = [0.0] * n
        s.vx[-1], s.vy[-1] = vx, vy
        s.cut = [False] * (n - 1); s.ax = ax; s.dead = [False] * n
    def step(s):
        for _ in range(2):
            fx = [0.0] * s.n; fy = [0.0] * s.n
            for i in range(s.n - 1):
                if s.cut[i]: continue
                dx, dy = s.px[i + 1] - s.px[i], s.py[i + 1] - s.py[i]
                L = math.hypot(dx, dy) or 1e-6
                if L / s.rest > s.kmax * (1.0 + 0.12 * (i % 2)) and i == s.snap: s.cut[i] = True; continue
                f = 0.42 * (L - s.rest) / 2
                ux, uy = dx / L, dy / L
                rvx, rvy = s.vx[i + 1] - s.vx[i], s.vy[i + 1] - s.vy[i]
                d = 0.10 * (rvx * ux + rvy * uy)
                fx[i] += (f + d) * ux; fy[i] += (f + d) * uy; fx[i + 1] -= (f + d) * ux; fy[i + 1] -= (f + d) * uy
            for i in range(s.n):
                if i == 0 or s.dead[i]: continue
                m = 3.0 if i == s.n - 1 else 1.0
                s.vx[i] += fx[i] / m; s.vy[i] += fy[i] / m + G / 2; s.vx[i] *= 0.992; s.vy[i] *= 0.992
                s.px[i] += s.vx[i] / 2; s.py[i] += s.vy[i] / 2
                if s.py[i] >= SURF - 0.5 and s.vy[i] > 0: s.dead[i] = True; s.py[i] = SURF + 1   # glued back into the floor

def b_setup():
    sts = [Strand(24 - 6, -1.2, -2.7, 7, 2.6, 2.6, 3.2, 3), Strand(24 - 2, -0.35, -3.5, 9, 2.8, 2.7, 4.0, 6),
           Strand(24 + 1, 0.45, -3.2, 9, 2.7, 2.9, 3.4, 3), Strand(24 + 4, 1.1, -2.8, 8, 2.5, 2.5, 3.0, 5),
           Strand(24 + 8, 2.0, -2.0, 6, 2.2, 2.4, 2.6, 2)]
    return dict(st=sts, bumps=[Bump(24, 3.2, 9.5, 1.5)])

def b_tick(s, t):
    for b in s["bumps"]: b.step()
    for st in s["st"]:
        was = list(st.dead); st.step()
        for i in range(st.n):
            if st.dead[i] and not was[i] and i == st.n - 1:
                s["bumps"].append(Bump(st.px[i], st.tipr * 0.9, st.tipr * 1.6, 1.0))     # tip lands: small plop

def b_prims(s, t):
    pr, marks = [b.prim() for b in s["bumps"]], []
    for st in s["st"]:
        for i in range(st.n - 1):
            if st.dead[i] and st.dead[i + 1]: continue
            L = math.hypot(st.px[i + 1] - st.px[i], st.py[i + 1] - st.py[i])
            if st.cut[i] and False: continue
            if st.cut[i]: continue
            w = max(0.8, min(2.1, 2.1 * math.sqrt(st.rest / max(L, 0.1))))     # volume kept: longer link, thinner
            pr.append(link(st.px[i], st.py[i], st.px[i + 1], st.py[i + 1], w))
        for i in range(st.n):
            if st.dead[i]: continue
            tip = i == st.n - 1
            pr.append(blob(st.px[i], st.py[i], st.tipr if tip else 1.2, st.vx[i], st.vy[i], 1.0))
            if tip: marks.append((st.px[i] - st.tipr * .35, st.py[i] - st.tipr * .4, st.tipr > 2.4))
    return pr, marks


# ------------------------------------------------------------------ C: bubble that inflates and pops into droplets
def c_setup():
    rnd = random.Random(11)
    return dict(rnd=rnd, bumps=[Bump(24, 2.0, 7, 0.4)], pts=None, drops=[], popped=False, ring=None)

POP = 28
def dome(t):
    e = min(1.0, t / POP); e = 1 - (1 - e) ** 2.2
    wob = 0.5 * math.sin(t * 0.55) * e
    return 3.5 + 8.5 * e, 2.0 + 14.5 * e + wob

def c_tick(s, t):
    for b in s["bumps"]: b.step()
    if t == POP and not s["popped"]:
        s["popped"] = True
        rx, ry = dome(t)
        s["pts"] = []
        for i in range(30):
            th = math.pi * (0.04 + 0.92 * i / 29)
            x, y = 24 - math.cos(th) * rx, SURF - math.sin(th) * ry
            nx, ny = -math.cos(th) / rx, -math.sin(th) / ry           # outward normal of the ellipse
            nl = math.hypot(nx, ny); nx, ny = nx / nl, ny / nl
            big = i % 3 == 1
            sp = s["rnd"].uniform(.4, 1.0) * (1.0 if big else 1.1)
            s["pts"].append(dict(x=x, y=y, vx=nx * sp + s["rnd"].uniform(-.2, .2), vy=ny * sp - 0.9 + s["rnd"].uniform(-.2, .1),
                                 r=(2.5 + s["rnd"].random() * .7) if big else 1.7, big=big, age=0, alive=True))
    if s["pts"]:
        for p in s["pts"]:
            if not p["alive"]: continue
            p["age"] += 1; p["vy"] += G; p["x"] += p["vx"]; p["y"] += p["vy"]
            if not p["big"]: p["r"] = max(0.0, p["r"] - 0.03)           # torn film shreds shrink away
            if p["r"] <= 0.3: p["alive"] = False
            if p["y"] > SURF - 0.4 and p["vy"] > 0:
                p["alive"] = False
                if p["big"]: s["bumps"].append(Bump(p["x"], p["r"] * 1.1, p["r"] * 1.5, p["vy"] * 0.4))

def c_prims(s, t):
    pr, marks = [], []
    if not s["popped"]:
        rx, ry = dome(t)
        pr.append(Prim("blob", x=24, y=SURF + 0.3, a=rx / 0.67 * 1.05, b=2.4 / 0.67, c=1.0, s=0.0, k=1.0))   # base lip
        for i in range(34):
            th = math.pi * i / 33
            x, y = 24 - math.cos(th) * rx, SURF - math.sin(th) * ry
            thick = 1.9 + 0.8 * (1 - math.sin(th))                       # film thicker at the foot than the crown
            pr.append(blob(x, y, thick, ang=0.0, stretch=1.0))
        marks += [(24 - rx * .55, SURF - ry * .8, True), (24 - rx * .72, SURF - ry * .55, False)]
    else:
        pr += [b.prim() for b in s["bumps"]]
        for p in s["pts"]:
            if not p["alive"]: continue
            pr.append(blob(p["x"], p["y"], max(0.5, p["r"]), p["vx"], p["vy"], 1 + min(0.5, math.hypot(p["vx"], p["vy"]) * 0.25)))
            if p["big"]: marks.append((p["x"] - .7, p["y"] - .8, False))
    return pr, marks


VARIANTS = [
    ("A", "Thick blob burst and drip", a_setup, a_tick, a_prims),
    ("B", "Stringy strands that snap back", b_setup, b_tick, b_prims),
    ("C", "Bubble that inflates and pops into droplets", c_setup, c_tick, c_prims),
]

if __name__ == "__main__":
    used = set()
    for key, name, setup, tick, prims in VARIANTS:
        frames = sim_frames(setup, tick, prims)
        sheet = Image.new("RGBA", (W * NF, H), PAL[0])
        for i, fr in enumerate(frames): sheet.paste(fr, (i * W, 0))
        sheet.save(os.path.join(HERE, "%s_gum_splat_1x.png" % key))
        used |= {p[:3] for p in sheet.getdata() if p[3]}
    allowed = {c[:3] for c in PAL[1:]}
    assert used <= allowed, used - allowed
    print("colours used: %d of %d" % (len(used), len(allowed)))
