#!/opt/homebrew/bin/python3.14 -I
"""Gum Trip drafts: gum pickup (3 candidates + collect effect), rival Sootling (3 variants), gum meter (2 variants).

Run from the repo root:  /opt/homebrew/bin/python3.14 -I thoughts/shared/drafts/2026-11-10-gum-trip-pickup-rival/draw_pickup_rival.py
Reads (read only): assets/flier/sootling_sheet.png + .json, the three scene_*_1x.png backdrops of
thoughts/shared/drafts/2026-11-10-backgrounds-final and hud1p_storm_1x.png of 2026-11-10-hud-title-final.
The crops it needs are copied into this folder once (sky_*.png, hud_tag_storm_1x.png); after that the script only
needs the Sootling sheet. Writes every other file of this folder except README.md.

Method: every sprite is a small analytic scene (ellipsoid, fan, box) sampled 5x5 per pixel, lit from the upper
left, then banded into a hand-chosen colour ramp per material (no dither, no checker), outlined with one keyline
colour and cleaned of single stray pixels. Motion comes from one joint spring simulation run to its periodic
steady state (see sim()).
"""
import sys
sys.dont_write_bytecode = True
import json, math, os, shutil
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
KEY = (255, 0, 255)
WHITE = (248, 248, 248)
SS = 5
N = 16            # frames per idle loop
FX = 8            # frames per collect effect
FPS_MS = 70       # gif frame time (game: 4 ticks per frame = 15 frames per second)
pi = math.pi


def P(*a):
    return os.path.join(HERE, *a)


# ------------------------------------------------------------------ physics
def pulse(t, c, w):
    d = ((t - c + 0.5) % 1.0) - 0.5
    return math.exp(-(d / w) ** 2)


def sim(n=N, sub=60, periods=14):
    """Joint spring system, time in loop units, driven by a periodic gust; the last period is recorded.

    y    bob: mass on a spring, lifted by the gust (natural frequency 1.25 per loop, damping 0.18)
    q    squash: surface tension spring (3 per loop, damping 0.12) driven by the bob acceleration (volume kept:
         x radius * (1+q), y radius / (1+q))
    th   tilt: torsion spring (1.1 per loop) driven by the side gust
    e1,e2 wrapper ears: two lighter springs (2.3 and 2.9 per loop) that chase the opposite of the tilt and the bob
         speed, so they lag and ring out of step
    spin angular speed under drag with one torque kick per loop; tw: twist spring driven by the angular acceleration
    """
    dt = 1.0 / (n * sub)
    W1, W2, W3, WA, WB, WT = 2 * pi * 1.25, 2 * pi * 3.0, 2 * pi * 1.1, 2 * pi * 2.3, 2 * pi * 2.9, 2 * pi * 2.0
    y = vy = q = vq = th = vth = e1 = ve1 = e2 = ve2 = w = tw = vtw = 0.0
    rec = {k: [] for k in ("y", "q", "th", "e1", "e2", "spin", "tw")}
    spin = 0.0
    for p in range(periods):
        last = p == periods - 1
        if last:
            spin = 0.0
        for i in range(n * sub):
            t = i * dt
            if last and i % sub == 0:
                for k, v in (("y", y), ("q", q), ("th", th), ("e1", e1), ("e2", e2), ("spin", spin), ("tw", tw)):
                    rec[k].append(v)
            gust = math.sin(2 * pi * t) + 0.5 * math.sin(4 * pi * t + 1.1) + 1.6 * pulse(t, 0.18, 0.05)
            side = math.cos(2 * pi * t + 0.6) - 0.4 * math.sin(4 * pi * t) + 0.9 * pulse(t, 0.55, 0.06)
            ay = 18 * gust - 2 * 0.18 * W1 * vy - W1 * W1 * y
            vy += ay * dt; y += vy * dt
            aq = -0.9 * ay - 2 * 0.12 * W2 * vq - W2 * W2 * q
            vq += aq * dt; q += vq * dt
            ath = 30 * side - 2 * 0.2 * W3 * vth - W3 * W3 * th
            vth += ath * dt; th += vth * dt
            a1 = -WA * WA * (e1 - (-0.05 * vy - th)) - 2 * 0.15 * WA * ve1
            ve1 += a1 * dt; e1 += ve1 * dt
            a2 = -WB * WB * (e2 - (-0.05 * vy + th)) - 2 * 0.15 * WB * ve2
            ve2 += a2 * dt; e2 += ve2 * dt
            aw = 1.0 + 2.2 * pulse(t, 0.3, 0.08) - 1.5 * w
            w += aw * dt; spin += w * dt
            atw = -WT * WT * tw - 2 * 0.15 * WT * vtw - 3.0 * aw
            vtw += atw * dt; tw += vtw * dt
    total = spin
    out = {}
    for k, v in rec.items():
        if k == "spin":
            out[k] = [x / total for x in v]
        else:
            m = sum(v) / len(v)
            v = [x - m for x in v]
            s = max(abs(x) for x in v) or 1.0
            out[k] = [x / s for x in v]
    return out


# ------------------------------------------------------------------ renderer
LX, LY, LZ = -0.50, -0.62, 0.60


def sphere_light(nx, ny, nz):
    d = nx * LX + ny * LY + nz * LZ
    l = 0.12 + 0.80 * max(0.0, d)
    if nx * 0.55 + ny * 0.65 - nz * 0.3 > 0.55:      # cool bounce light on the lower right rim
        l = max(l, 0.30)
    if d > 0.962:
        l = 0.999
    return min(0.999, max(0.0, l))


def ramp_pick(ramp, l):
    cols, thr = ramp
    if l >= 0.98:
        return WHITE
    i = 0
    for t in thr:
        if l >= t:
            i += 1
    return cols[i]


def render(w, h, fn, ramps, key):
    img = [[None] * w for _ in range(h)]
    for py in range(h):
        for px in range(w):
            acc = {}
            n = 0
            for sy in range(SS):
                for sx in range(SS):
                    r = fn(px + (sx + 0.5) / SS, py + (sy + 0.5) / SS)
                    if r:
                        n += 1
                        a = acc.setdefault(r[0], [0, 0.0])
                        a[0] += 1; a[1] += r[1]
            if n * 2 > SS * SS:
                m = max(acc, key=lambda k: acc[k][0])
                img[py][px] = ramp_pick(ramps[m], acc[m][1] / acc[m][0])
    # stray single pixels inside the shape take the commonest neighbour colour (white glints stay)
    for _ in range(2):
        for py in range(h):
            for px in range(w):
                c = img[py][px]
                if c is None or c == WHITE:
                    continue
                nb = [img[y][x] for x, y in ((px - 1, py), (px + 1, py), (px, py - 1), (px, py + 1))
                      if 0 <= x < w and 0 <= y < h and img[y][x] is not None]
                if len(nb) >= 3 and c not in nb:
                    img[py][px] = max(set(nb), key=nb.count)
    out = [row[:] for row in img]
    for py in range(h):
        for px in range(w):
            if img[py][px] is None:
                for x, y in ((px - 1, py), (px + 1, py), (px, py - 1), (px, py + 1)):
                    if 0 <= x < w and 0 <= y < h and img[y][x] is not None:
                        out[py][px] = key
                        break
    return out


def put(img, x, y, c):
    if 0 <= y < len(img) and 0 <= x < len(img[0]):
        img[y][x] = c


def star(img, cx, cy, n, cl, cw):
    """Hand-shaped four point glint: n 0 dot, 1 small plus, 2 long plus, 3 long plus with diagonals."""
    put(img, cx, cy, cw)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        if n >= 1:
            put(img, cx + dx, cy + dy, cl if n == 1 else cw)
        if n >= 2:
            put(img, cx + 2 * dx, cy + 2 * dy, cl)
        if n >= 3:
            put(img, cx + 3 * dx, cy + 3 * dy, cw)
            put(img, cx + 2 * dx, cy + 2 * dy, cw)
            put(img, cx + 4 * dx, cy + 4 * dy, cl)
    if n >= 3:
        for dx, dy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
            put(img, cx + dx, cy + dy, cl)


# ------------------------------------------------------------------ candidate A: wrapped gum drop (24x24)
A_KEY = (24, 8, 40)
A_RAMPS = {
    "body": ([(104, 16, 88), (176, 32, 120), (240, 72, 152), (248, 144, 192), (248, 216, 232)], [0.2, 0.42, 0.64, 0.84]),
    "stripe": ([(144, 96, 184), (208, 184, 232), WHITE], [0.34, 0.6]),
    "ear": ([(16, 80, 112), (32, 152, 176), (120, 224, 216), (224, 248, 240)], [0.3, 0.55, 0.8]),
}


def frame_a(s, i):
    q, th = 0.11 * s["q"][i], 0.20 * s["th"][i]
    pl, pr = 0.42 * s["e1"][i], 0.42 * s["e2"][i]
    ph = i / N
    a, b = 5.5 * (1 + q), 5.0 / (1 + q)
    ct, st = math.cos(th), math.sin(th)

    def fn(x, y):
        dx, dy = x - 12, y - 12
        u, v = dx * ct + dy * st, -dx * st + dy * ct
        e = (u / a) ** 2 + (v / b) ** 2
        if e <= 1:
            nx, ny, nz = u / a, v / b, math.sqrt(1 - e)
            l = sphere_light(nx, ny, nz)
            sc = (nx * 0.75 + ny * 0.65) * 1.7 + ph
            return ("stripe" if (sc % 1.0) < 0.38 else "body", l)
        for sd, phi in ((-1, pl), (1, pr)):
            du, dv = (u - sd * (a - 0.9)) * sd, v
            r = math.hypot(du, dv)
            if r < 0.05 or du < 0:
                continue
            d = math.atan2(dv, du) - phi
            if abs(d) < 0.60 and r < 5.0 + 0.45 * math.cos(d * 10):
                l = 0.52 + 0.36 * math.sin(d * 8.5 + 0.9 * sd) - 0.10 * math.sin(d)
                l *= min(1.0, 0.4 + r / 3.2)
                return ("ear", min(0.97, max(0.0, l)))
        return None

    img = render(24, 24, fn, A_RAMPS, A_KEY)
    tw = (i - 9) % N
    if tw < 3:
        star(img, 6, 5, (1, 2, 1)[tw], (248, 216, 232), WHITE)
    return img


# ------------------------------------------------------------------ candidate B: spinning gumball (16x16)
B_KEY = (16, 8, 40)
B_RAMPS = {
    0: ([(16, 48, 120), (24, 104, 200), (56, 168, 240), (144, 224, 248)], [0.25, 0.5, 0.75]),
    1: ([(128, 136, 200), (216, 224, 248), WHITE], [0.34, 0.62]),
    2: ([(120, 16, 96), (208, 40, 136), (248, 96, 168), (248, 176, 216)], [0.25, 0.5, 0.75]),
}


def _norm(v):
    m = math.sqrt(sum(c * c for c in v))
    return tuple(c / m for c in v)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


B_AX = _norm((0.34, -0.80, 0.50))
B_E1 = _norm(_cross(B_AX, (0, 0, 1)))
B_E2 = _cross(B_AX, B_E1)


def frame_b(s, i):
    q = 0.10 * s["q"][i]
    psi = s["spin"][i] * 2 * pi / 3
    rx, ry = 5.5 * (1 + q), 5.5 / (1 + q)

    def fn(x, y):
        u, v = x - 8, y - 8
        e = (u / rx) ** 2 + (v / ry) ** 2
        if e > 1:
            return None
        n = (u / rx, v / ry, math.sqrt(1 - e))
        l = sphere_light(*n)
        hgt = sum(n[k] * B_AX[k] for k in range(3))
        if hgt > 0.93:
            return (1, l)                                  # pale pole cap
        lon = math.atan2(sum(n[k] * B_E2[k] for k in range(3)), sum(n[k] * B_E1[k] for k in range(3)))
        lon += 0.35 * hgt                                   # wedges curl slightly, like a blown swirl
        return (int(((lon + psi) % (2 * pi)) / (pi / 3)) % 3, l)

    img = render(16, 16, fn, B_RAMPS, B_KEY)
    tw = (i - 10) % N
    if tw < 3:
        star(img, 4, 4, (0, 1, 0)[tw], (144, 224, 248), WHITE)
    return img


# ------------------------------------------------------------------ candidate C: twirling gum stick (24x24)
C_KEY = (24, 8, 40)
C_RAMPS = {
    "gum": ([(112, 16, 88), (192, 40, 128), (248, 96, 168), (248, 168, 208), (248, 224, 232)], [0.2, 0.4, 0.6, 0.8]),
    "foil": ([(40, 48, 128), (72, 112, 200), (136, 192, 240), (224, 248, 248)], [0.25, 0.5, 0.75]),
}


def frame_c(s, i):
    a = s["spin"][i] * pi + 0.35
    twist = 0.38 * s["tw"][i]
    th = 0.12 * s["th"][i]
    ct, st = math.cos(th), math.sin(th)
    HW, HD, HH = 4.3, 0.9, 9.0
    hl = math.hypot(-0.6, 1.7)
    hx, hz = -0.6 / hl, 1.7 / hl

    def fn(x, y):
        dx, dy = x - 12, y - 12
        u, v = dx * ct + dy * st, -dx * st + dy * ct
        if abs(v) > HH:
            return None
        t = v / HH
        ar = a + twist * t
        c, sn = math.cos(ar), math.sin(ar)
        C, sp = abs(c), (sn if c > 0 else -sn)
        left = -(HW * C + HD * abs(sp))
        if u < left or u > -left:
            return None
        if abs(v) > HH - 1 and (u < left + 1 or u > -left - 1):
            return None                                     # rounded corners
        sw = 2 * HD * abs(sp)
        if sp > 0:
            is_side, f0 = u < left + sw, left + sw
        else:
            is_side, f0 = u > -left - sw, left
        if is_side:
            l = 0.16 + 0.5 * max(0.0, (-C if sp > 0 else C) * -0.6 + abs(sp) * 0.7)
            return ("gum" if t < 0.05 else "foil", min(0.5, l))
        fx = (u - f0) / max(0.2, 2 * HW * C) * 2 - 1
        d = sp * -0.6 + C * 0.7
        l = 0.22 + 0.56 * max(0.0, d) - 0.10 * t
        flash = sp * hx + C * hz > 0.985
        tb = 0.05 + (0.11 if int((fx + 1) * 2.5) % 2 else -0.11)
        if t < tb:
            if -0.72 < t < -0.60 or -0.36 < t < -0.24:
                l -= 0.22                                    # score grooves
            if flash:
                l += 0.2
            return ("gum", min(0.97, max(0.0, l)))
        if 0.50 < t < 0.70:
            return ("gum", min(0.97, max(0.0, l)))          # label band on the wrapper
        if flash:
            return ("foil", 0.999)
        l += 0.12 * math.sin(fx * 5 + t * 9)
        return ("foil", min(0.97, max(0.0, l)))

    return render(24, 24, fn, C_RAMPS, C_KEY)


# ------------------------------------------------------------------ collect effects (32x32, 8 frames)
def discs_fn(discs, extra=None):
    def fn(x, y):
        for cx, cy, r, m in discs:
            u, v = x - cx, y - cy
            e = (u * u + v * v) / (r * r)
            if e <= 1:
                return (m, sphere_light(u / r, v / r, math.sqrt(1 - e)))
        return extra(x, y) if extra else None
    return fn


def burst(n, speed, drag, grav, rot=0.0, lift=0.0):
    """Particle paths: radial launch, air drag, gravity; returns per frame a list of (x, y)."""
    ps = []
    for k in range(n):
        ang = rot + 2 * pi * k / n
        ps.append([16.0, 16.0, speed * math.cos(ang), speed * math.sin(ang) - lift])
    frames = []
    for f in range(FX):
        frames.append([(p[0], p[1]) for p in ps])
        for _ in range(10):
            for p in ps:
                p[2] -= drag * p[2] * 0.1; p[3] += (grav - drag * p[3]) * 0.1
                p[0] += p[2] * 0.1; p[1] += p[3] * 0.1
    return frames


def fx_a():
    blobs = burst(6, 4.4, 0.42, 0.22, rot=0.3)
    scraps = burst(2, 3.2, 0.3, 0.30, rot=-0.5, lift=1.2)
    out = []
    for f in range(FX):
        r = 2.7 * (1 - f / FX) ** 0.8 + 0.45
        discs = [(x, y, r, "body") for x, y in blobs[f]]

        def scrap(x, y, f=f):
            for k, (sx, sy) in enumerate(scraps[f]):
                ang = 0.9 * f * (1 if k else -1) + k
                u = (x - sx) * math.cos(ang) + (y - sy) * math.sin(ang)
                v = -(x - sx) * math.sin(ang) + (y - sy) * math.cos(ang)
                wdt = 2.6 * abs(math.cos(0.8 * f + k)) + 0.7
                if abs(u) < wdt and abs(v) < 1.7 and f < FX - 1:
                    return ("ear", 0.35 + 0.5 * abs(math.cos(0.8 * f + k)) + 0.1 * u / wdt)
            return None
        img = render(32, 32, discs_fn(discs, scrap), A_RAMPS, A_KEY)
        if f < 3:
            star(img, 16, 16, 3 - f, (248, 216, 232), WHITE)
        if 2 <= f < 7:
            for k, (x, y) in enumerate(burst(3, 5.6, 0.3, 0.0, rot=1.4)[f]):
                star(img, int(x), int(y), (1, 2, 1, 1, 0)[f - 2] if k != 1 else (0, 1, 2, 1, 0)[f - 2], (248, 144, 192), WHITE)
        out.append(img)
    return out


def fx_b():
    blobs = burst(3, 3.6, 0.35, -0.12, rot=-pi / 2)
    out = []
    for f in range(FX):
        rr = 3.0 + 10.5 * (1 - math.exp(-0.45 * f))
        th = max(0.0, 2.6 - 0.36 * f)
        r = 2.4 * (1 - f / FX) + 0.5
        discs = [(x, y, r, k) for k, (x, y) in enumerate(blobs[f])] if f > 0 else []

        def ring(x, y, rr=rr, th=th):
            d = math.hypot(x - 16, y - 16)
            if th > 0.5 and abs(d - rr) < th / 2:
                ang = math.atan2(y - 16, x - 16)
                return (0, 0.5 - 0.4 * math.sin(ang + 0.9) + (0.2 if d < rr else 0))
            return None
        img = render(32, 32, discs_fn(discs, ring), B_RAMPS, B_KEY)
        if f < 3:
            star(img, 16, 16, 3 - f, (144, 224, 248), WHITE)
        if f >= 3:
            for k in range(8):
                ang = 2 * pi * k / 8 + 0.2
                x, y = 16 + rr * math.cos(ang), 16 + rr * math.sin(ang)
                star(img, int(round(x)), int(round(y)), (2, 1, 1, 0, 0)[f - 3] if k % 2 else (1, 2, 1, 1, 0)[f - 3],
                     (144, 224, 248) if k % 2 else (248, 176, 216), WHITE)
        out.append(img)
    return out


def fx_c():
    out = []
    for f in range(FX):
        discs = []
        pts = []
        for k in range(5):
            age = f - 0.5 * k
            if age < 0:
                continue
            yy = 18 - 2.6 * age + 0.12 * age * age
            xx = 16 + (2.0 + 1.3 * age) * math.sin(1.1 * age + 2 * pi * k / 5)
            r = max(0.0, 2.3 - 0.33 * age)
            if r > 0.7:
                discs.append((xx, yy, r, "gum"))
            pts.append((xx, yy, age))
        img = render(32, 32, discs_fn(discs), C_RAMPS, C_KEY)
        if f < 3:
            star(img, 16, 17, 3 - f, (248, 224, 232), WHITE)
        for xx, yy, age in pts:
            if 2.5 <= age < 6.5:
                star(img, int(round(xx)), int(round(yy - 3)), (1, 2, 1, 0)[int(age - 2.5)], (136, 192, 240), WHITE)
        out.append(img)
    return out


# ------------------------------------------------------------------ helpers: images, tiles, gifs
def to_pil(img, bg=KEY):
    h, w = len(img), len(img[0])
    im = Image.new("RGB", (w, h), bg)
    px = im.load()
    for y in range(h):
        for x in range(w):
            if img[y][x] is not None:
                px[x, y] = img[y][x]
    return im


def sheet(frames):
    w, h = len(frames[0][0]), len(frames[0])
    im = Image.new("RGB", (w * len(frames), h), KEY)
    for i, f in enumerate(frames):
        im.paste(to_pil(f), (i * w, 0))
    return im


def blit(dst, img, ox, oy):
    px = dst.load()
    for y, row in enumerate(img):
        for x, c in enumerate(row):
            if c is not None and 0 <= ox + x < dst.width and 0 <= oy + y < dst.height:
                px[ox + x, oy + y] = c


def colours(frames):
    return sorted({c for f in frames for row in f for c in row if c is not None})


def tiles_unique(frames):
    """Unique non-empty 16x16 tiles with flips reused; frames are padded and centred on a 16 px grid."""
    seen = set()
    for f in frames:
        h, w = len(f), len(f[0])
        W, H = (w + 15) // 16 * 16, (h + 15) // 16 * 16
        ox, oy = (W - w) // 2, (H - h) // 2
        g = [[None] * W for _ in range(H)]
        for y in range(h):
            for x in range(w):
                g[oy + y][ox + x] = f[y][x]
        for ty in range(0, H, 16):
            for tx in range(0, W, 16):
                t = [tuple(g[ty + y][tx:tx + 16]) for y in range(16)]
                if all(c is None for r in t for c in r):
                    continue
                var = [tuple(t), tuple(r[::-1] for r in t), tuple(t[::-1]), tuple(r[::-1] for r in t[::-1])]
                seen.add(min(var, key=repr))
    return len(seen)


def save_gif(frames, path, scale=3):
    big = [f.resize((f.width * scale, f.height * scale), Image.NEAREST) for f in frames]
    mos = Image.new("RGB", (big[0].width * 4, big[0].height * ((len(big) + 3) // 4)))
    for i, f in enumerate(big):
        mos.paste(f, ((i % 4) * f.width, (i // 4) * f.height))
    pal = mos.quantize(255, dither=Image.Dither.NONE)
    q = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in big]
    q[0].save(path, save_all=True, append_images=q[1:], duration=FPS_MS, loop=0, disposal=1)


def up(im, s=3):
    return im.resize((im.width * s, im.height * s), Image.NEAREST)


# ------------------------------------------------------------------ inputs
def ensure_inputs():
    bgd = os.path.join(ROOT, "thoughts/shared/drafts/2026-11-10-backgrounds-final")
    for sky in ("storm", "moon", "dusk"):
        if not os.path.exists(P("sky_%s_1x.png" % sky)):
            Image.open(os.path.join(bgd, "scene_%s_1x.png" % sky)).convert("RGB").crop((0, 0, 320, 96)).save(P("sky_%s_1x.png" % sky))
    if not os.path.exists(P("hud_tag_storm_1x.png")):
        hud = Image.open(os.path.join(ROOT, "thoughts/shared/drafts/2026-11-10-hud-title-final/hud1p_storm_1x.png")).convert("RGB")
        hud.crop((0, 0, 320, 16)).save(P("hud_tag_storm_1x.png"))


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


def colourise(fr, pal):
    return [[None if i == 0 else pal[i - 1] for i in row] for row in fr]


# ------------------------------------------------------------------ rival palettes (index 1..15, multiples of 8)
RIVALS = [
    ("A", "Hornet", "palette swap only: charcoal fur, yellow eyes and rim, red beak, amber gum", [
        (8, 8, 16), (32, 24, 48), (64, 56, 88), (112, 104, 136), (176, 176, 200), (248, 232, 64),
        (96, 8, 24), (216, 32, 40), (248, 136, 72),
        (112, 48, 0), (184, 96, 0), (240, 168, 16), (248, 224, 96), (248, 248, 200), (248, 248, 248)]),
    ("B", "Bone", "palette swap only: pale bone fur, red eyes and rim, dark beak, violet gum", [
        (16, 8, 32), (72, 56, 112), (136, 128, 176), (200, 200, 224), (240, 240, 248), (248, 56, 56),
        (24, 16, 48), (64, 56, 104), (144, 136, 184),
        (48, 16, 96), (96, 40, 168), (144, 88, 232), (192, 160, 248), (232, 224, 248), (248, 248, 248)]),
    ("C", "Bruiser", "palette swap plus angry brows (tile change): purple fur, pale yellow eyes, scarlet gum", [
        (16, 8, 32), (40, 16, 72), (88, 32, 136), (152, 64, 184), (216, 136, 232), (248, 248, 160),
        (16, 56, 40), (40, 160, 88), (160, 240, 120),
        (96, 0, 24), (168, 16, 32), (232, 48, 40), (248, 136, 88), (248, 216, 176), (248, 248, 248)]),
]


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


def add_brows(fr):
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


def frame_tiles(fr):
    return [tuple(tuple(fr[ty + y][tx:tx + 16]) for y in range(16)) for ty in range(0, 48, 16) for tx in range(0, 32, 16)]


# ------------------------------------------------------------------ meter (fix layer, 8x8 tiles)
M_PAL = {"k": (16, 8, 40), "e": (40, 32, 80), "E": (24, 16, 56), "d": (168, 32, 128), "p": (248, 80, 176),
         "h": (248, 168, 216), "w": (248, 248, 248), "r": (136, 144, 200), ".": None}
M_WARN = dict(M_PAL, d=(160, 24, 24), p=(240, 88, 32), h=(248, 184, 88))

M_ICON = ["........", "..kkkk..", ".khhppkk", "kwhppppk", "khpppppk", "kpppppdk", ".kpddkkk", "..kkkk.."]
LOBE = {
    2: [".kk..kk.", "kwhkkhpk", "khpppppk", "kppppppk", "kpppppdk", ".kpppdk.", "..kddk..", "...kk..."],
    1: [".kk..kk.", "kwhkkeEk", "khppkeEk", "kpppkeEk", "kppdkEEk", ".kpdkEk.", "..kdkk..", "...kk..."],
    0: [".kk..kk.", "keekkeEk", "keeeeeEk", "keeeeeEk", "keeeeEEk", ".keeEEk.", "..kEEk..", "...kk..."],
}


def tube_tile(a, b):
    """One 8x8 tube tile holding two 4 px segments; a, b: 1 filled, 0 empty."""
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


def draw_tile(dst, rows, ox, oy, pal):
    px = dst.load()
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if pal[ch] is not None:
                px[ox + x, oy + y] = pal[ch]


def meter_stills():
    tag = Image.open(P("hud_tag_storm_1x.png"))
    sky = Image.open(P("sky_storm_1x.png"))
    base = tag.crop((0, 0, 176, 16))
    base.paste(sky.crop((64, 8, 176, 16)), (64, 8))      # removes the three life dots of the arena tag
    info = {}
    for name in ("tube", "lobes"):
        out = Image.new("RGB", (176, 9 * 18 - 2), (20, 20, 24))
        used = set()
        for row, step in enumerate(range(8, -1, -1)):
            im = base.copy()
            pal = M_WARN if step <= 2 else M_PAL
            if name == "tube":
                draw_tile(im, M_ICON, 72, 8, pal); used.add(tuple(M_ICON))
                for t in range(4):
                    a, b = int(step > 2 * t), int(step > 2 * t + 1)
                    tt = tube_tile(a, b); used.add(tuple(tt))
                    draw_tile(im, tt, 80 + 8 * t, 8, pal)
            else:
                for t in range(4):
                    st = max(0, min(2, step - 2 * t))
                    used.add(tuple(LOBE[st]))
                    draw_tile(im, LOBE[st], 72 + 9 * 0 + 8 * t, 8, pal)
            out.paste(im, (0, row * 18))
        up(out).save(P("meter_%s_3x.png" % name))
        cols = {M_PAL[ch] for t in used for r in t for ch in r if M_PAL[ch]} | {M_WARN[ch] for t in used for r in t for ch in r if M_WARN[ch]}
        pcols = {M_PAL[ch] for t in used for r in t for ch in r if M_PAL[ch]}
        info[name] = (len(used), len(pcols), len(cols), 5 if name == "tube" else 4)
        strip = Image.new("RGB", (8 * len(used) + len(used) - 1, 8), (20, 20, 24))
        for k, t in enumerate(sorted(used)):
            draw_tile(strip, list(t), k * 9, 0, M_PAL)
        up(strip, 6).save(P("meter_%s_tiles_6x.png" % name))
    return info


# ------------------------------------------------------------------ main
def main():
    ensure_inputs()
    s = sim()
    soot, pal_p, pal_c, meta = load_sootling()
    skies = {k: Image.open(P("sky_%s_1x.png" % k)).convert("RGB") for k in ("storm", "moon", "dusk")}
    num = []
    bob = [int(round(3.0 * v)) for v in s["y"]]

    cands = [
        ("a", "Wrapped gum drop", 24, [frame_a(s, i) for i in range(N)], fx_a()),
        ("b", "Spinning gumball", 16, [frame_b(s, i) for i in range(N)], fx_b()),
        ("c", "Twirling gum stick", 24, [frame_c(s, i) for i in range(N)], fx_c()),
    ]
    flap = [colourise(soot[i], pal_p) for i in range(8)]
    for cid, name, size, idle, fx in cands:
        sheet(idle).save(P("pickup_%s_sheet_1x.png" % cid))
        sheet(fx).save(P("pickup_%s_collect_sheet_1x.png" % cid))
        up(sheet(idle + fx if size == 32 else idle), 3).save(P("pickup_%s_sheet_3x.png" % cid))
        up(sheet(fx), 3).save(P("pickup_%s_collect_sheet_3x.png" % cid))
        cols = colours(idle + fx)
        assert len(cols) <= 15, (cid, len(cols))
        assert all(v % 8 == 0 for c in cols for v in c)
        cw = (size + 15) // 16
        num.append("pickup %s (%s): size %dx%d; frames %d idle + %d collect (collect is 32x32); colours %d (idle %d); "
                   "16 px sprite columns %d idle, 2 collect; worst sprites per scanline added %d (two pickups level on "
                   "screen, one of them popping: %d + 2); unique 16x16 tiles %d idle + %d collect = %d; "
                   "bob offsets px per frame (applied by position, not drawn in the tile) %s"
                   % (cid.upper(), name, size, size, N, FX, len(cols), len(colours(idle)), cw, cw + 2, cw,
                      tiles_unique(idle), tiles_unique(fx), tiles_unique(idle) + tiles_unique(fx), bob))
        num.append("  palette %s: %s" % (cid.upper(), " ".join("(%d,%d,%d)" % c for c in cols)))
        # gif: storm sky, player Sootling for scale, two idle loops, fly-in, collect, pause
        gf = []
        crop = skies["storm"].crop((180, 4, 180 + 120, 4 + 72))
        px0, py0 = 84, 36
        for t in range(2 * N + FX + 8):
            im = crop.copy()
            if t < 2 * N - 8:
                sx = 6
            elif t < 2 * N:
                e = (t - (2 * N - 8)) / 8.0
                sx = 6 + int(round(40 * e * e * (3 - 2 * e)))
            elif t < 2 * N + FX:
                sx = 46
            else:
                e = (t - 2 * N - FX) / 8.0
                sx = 46 - int(round(40 * e * e * (3 - 2 * e)))
            blit(im, flap[t % 8], sx, 12 + (1 if t % 8 in (5, 6, 7) else 0))
            if t < 2 * N:
                blit(im, idle[t % N], px0 - size // 2, py0 - size // 2 + bob[t % N])
            elif t < 2 * N + FX:
                blit(im, fx[t - 2 * N], px0 - 16, py0 - 16)
            gf.append(im)
        save_gif(gf, P("pickup_%s_anim_3x.gif" % cid))

    # contact sheet for judging, written only with --contact (not a candidate asset)
    con = Image.new("RGB", (N * 26 + 2, 3 * 62 + 2), (56, 60, 72))
    for r, (cid, name, size, idle, fx) in enumerate(cands if "--contact" in sys.argv else []):
        for i, f in enumerate(idle):
            blit(con, f, 2 + i * 26 + (24 - size) // 2, 2 + r * 62 + (24 - size) // 2)
        for i, f in enumerate(fx):
            blit(con, f, 2 + i * 34, 2 + r * 62 + 27)
    if "--contact" in sys.argv:
        up(con, 3).save(P("pickup_contact_3x.png"))

    # ---- rivals
    f0 = soot[0]
    p1, p2 = colourise(f0, pal_p), colourise(f0, pal_c)
    browed = [add_brows(f) for f in soot]
    changed_frames = sum(1 for a, b in zip(soot, browed) if a != b)
    base_tiles = {t for f in soot for t in frame_tiles(f)}
    new_tiles = {t for f in browed for t in frame_tiles(f)} - base_tiles
    changed_refs = sum(1 for a, b in zip(soot, browed) for ta, tb in zip(frame_tiles(a), frame_tiles(b)) if ta != tb)
    for rid, name, note, pal in RIVALS:
        assert all(v % 8 == 0 for c in pal for v in c) and len(set(pal)) == 15
        src = browed if rid == "C" else soot
        riv = colourise(src[0], pal)
        for sky, bg in skies.items():
            im = bg.crop((100, 6, 100 + 120, 6 + 60)).copy()
            blit(im, p1, 4, 6); blit(im, riv, 44, 6); blit(im, p2, 84, 6)
            up(im).save(P("rival_%s_%s_3x.png" % (rid.lower(), sky)))
        extra = ("tile change: %d of 63 frames differ, %d tile references differ, %d new unique 16x16 tiles"
                 % (changed_frames, changed_refs, len(new_tiles))) if rid == "C" else "0 frames changed, 0 new tiles"
        num.append("rival %s (%s): %s; frames 63 (shared with the players); colours 15; 16 px sprite columns 2; "
                   "worst sprites per scanline added 4 (two rivals level, same as two computer fliers in the arena); %s"
                   % (rid, name, note, extra))
        num.append("  palette %s index 1..15: %s" % (rid, " ".join("(%d,%d,%d)" % c for c in pal)))
    num.append("  for reference, player 1 palette snapped to multiples of 8: %s"
               % " ".join("(%d,%d,%d)" % tuple(v & ~7 for v in c) for c in pal_p))
    num.append("  for reference, player 2 / computer palette snapped: %s"
               % " ".join("(%d,%d,%d)" % tuple(v & ~7 for v in c) for c in pal_c))
    # 1x line-up on the three skies and a flap gif on storm
    line = Image.new("RGB", (200, 3 * 58), (0, 0, 0))
    for r, (sky, bg) in enumerate(skies.items()):
        im = bg.crop((60, 6, 260, 64)).copy()
        blit(im, p1, 4, 5); blit(im, p2, 164, 5)
        for k, (rid, _, _, pal) in enumerate(RIVALS):
            blit(im, colourise((browed if rid == "C" else soot)[0], pal), 44 + 40 * k, 5)
        line.paste(im, (0, r * 58))
    line.save(P("rival_lineup_1x.png")); up(line).save(P("rival_lineup_3x.png"))
    gf = []
    for t in range(8):
        im = skies["storm"].crop((60, 6, 260, 64)).copy()
        blit(im, colourise(soot[t], pal_p), 4, 5); blit(im, colourise(soot[t], pal_c), 164, 5)
        for k, (rid, _, _, pal) in enumerate(RIVALS):
            blit(im, colourise((browed if rid == "C" else soot)[(t + 2 * k + 3) % 8], pal), 44 + 40 * k, 5)
        gf.append(im)
    save_gif(gf, P("rival_flap_storm_3x.gif"))
    sh = Image.new("RGB", (256, 384), KEY)
    for i, f in enumerate(browed):
        blit(sh, colourise(f, RIVALS[2][3]), (i % 8) * 32, (i // 8) * 48)
    sh.save(P("rival_c_sheet_1x.png"))
    head = Image.new("RGB", (68, 26), (40, 44, 56))
    blit(head, [r[:] for r in colourise(soot[0], RIVALS[2][3])[22:46]], 1, 1)
    blit(head, [r[:] for r in colourise(browed[0], RIVALS[2][3])[22:46]], 35, 1)
    up(head, 6).save(P("rival_c_brows_6x.png"))

    # ---- meter
    for name, (tiles, pc, allc, cells) in meter_stills().items():
        num.append("meter %s: fix layer cells %d (8x8); unique tiles %d; colours %d per palette (second palette for the "
                   "low warning at 2 steps or fewer: orange, same tiles; %d colours over both); 9 states shown "
                   "(8 fill steps and empty); sprites 0" % (name, cells, tiles, pc, allc))

    open(P("numbers.txt"), "w").write(
        "Gum Trip pickup / rival / meter drafts. Frame rate 15 per second (4 ticks per frame).\n"
        "Tile counts: non-empty 16x16 tiles, sprite centred on a 16 px grid, horizontal and vertical flips reused.\n\n"
        + "\n".join(num) + "\n")
    write_html(num)
    print("\n".join(num))


def write_html(num):
    def fig(src, cap, w=None):
        return '<figure><img src="%s"%s alt="%s"><figcaption>%s</figcaption></figure>' % (
            src, ' width="%d"' % w if w else "", cap, cap)
    def lines(prefix):
        out, keep = [], False
        for l in num:
            if not l.startswith("  "):
                keep = l.startswith(prefix)
            if keep:
                out.append("<p class='n'>%s</p>" % l.strip())
        return "".join(out)
    h = ["""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>Gum Trip: pickup, rival, meter drafts</title>
<style>
body{background:#17181b;color:#d6d8dc;font-family:-apple-system,"Helvetica Neue",Arial,sans-serif;margin:0;padding:28px 36px;line-height:1.45}
h1{font-size:24px;margin:0 0 4px;color:#fff}h2{font-size:20px;margin:40px 0 10px;color:#fff;border-bottom:1px solid #34363c;padding-bottom:6px}
h3{font-size:16px;margin:26px 0 8px;color:#f0f0f2}
img{image-rendering:pixelated;display:block;background:#000}
figure{display:inline-block;margin:0 16px 16px 0;vertical-align:top}figcaption{font-size:13px;color:#9a9da5;margin-top:5px;max-width:420px}
p{max-width:980px;margin:6px 0}p.n{font-size:13px;color:#b4b7be}
.card{background:#1f2125;border:1px solid #2e3036;border-radius:4px;padding:14px 18px;margin:0 0 18px}
</style></head><body>
<h1>Gum Trip: pickup, rival and gum meter drafts</h1>
<p>Three pickup candidates, three rival Sootling variants and two gum meter variants, for a pick. All sprites are shown at
3x unless a caption says otherwise. Details, ranking and doubts are in README.md; all numbers are in numbers.txt.</p>
<h2>Pickup</h2>"""]
    names = {"a": "A. Wrapped gum drop (24x24)", "b": "B. Spinning gumball (16x16)", "c": "C. Twirling gum stick (24x24)"}
    for cid in "abc":
        h.append('<div class="card"><h3>%s</h3>' % names[cid])
        h.append(fig("pickup_%s_anim_3x.gif" % cid, "In play on the storm sky with the player 1 Sootling for scale: two idle loops, then the collect effect"))
        h.append(fig("pickup_%s_sheet_3x.png" % cid, "Idle loop, 16 frames (1x sheet: pickup_%s_sheet_1x.png)" % cid))
        h.append(fig("pickup_%s_collect_sheet_3x.png" % cid, "Collect effect, 8 frames of 32x32 (1x sheet: pickup_%s_collect_sheet_1x.png)" % cid))
        h.append(lines("pickup %s" % cid.upper()) + "</div>")
    h.append("<h2>Rival</h2><p>Left to right in every still: player 1, the rival, player 2 (the computer palette of the arena).</p>")
    h.append('<div class="card"><h3>All five at 1x and 3x</h3>')
    h.append(fig("rival_lineup_1x.png", "1x: player 1, rival A, rival B, rival C, player 2 on storm, moon, dusk"))
    h.append(fig("rival_lineup_3x.png", "The same line-up at 3x"))
    h.append(fig("rival_flap_storm_3x.gif", "Flap loop on storm, same order") + "</div>")
    for rid, name, note, _ in RIVALS:
        h.append('<div class="card"><h3>%s. %s</h3><p>%s</p>' % (rid, name, note[0].upper() + note[1:]))
        for sky in ("storm", "moon", "dusk"):
            h.append(fig("rival_%s_%s_3x.png" % (rid.lower(), sky), sky.capitalize()))
        if rid == "C":
            h.append(fig("rival_c_brows_6x.png", "Head at 6x: accepted eyes (left), with brows (right)"))
        h.append(lines("rival %s" % rid) + "</div>")
    h.append("<h2>Meter</h2><p>Shown in the player 1 corner tag on the storm sky, in place of the three life dots: full (8) at the top down to empty at the bottom. At 2 steps or fewer the meter switches to a second, orange palette on the same tiles.</p>")
    for name, title in (("tube", "A. Gum tube: icon and eight segments"), ("lobes", "B. Four double lobes: each lobe is one step")):
        h.append('<div class="card"><h3>%s</h3>' % title)
        h.append(fig("meter_%s_3x.png" % name, "Nine states at 3x"))
        h.append(fig("meter_%s_tiles_6x.png" % name, "Unique 8x8 tiles at 6x"))
        h.append(lines("meter %s" % name) + "</div>")
    h.append("</body></html>")
    open(P("index.html"), "w").write("\n".join(h))


if __name__ == "__main__":
    main()
