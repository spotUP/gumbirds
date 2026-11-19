#!/opt/homebrew/bin/python3.14 -I
"""Sootling at 32 x 48 with the chosen gum design B (one membrane, two lobes, blown from the mouth).
Drafts for Bubblegum Brawl. Original art, drawn by this script. Nothing outside this directory is written.

Run: /opt/homebrew/bin/python3.14 -I draw_sootling_b.py [--nogif]

Frame box 32 x 48 (2 sprite columns, 3 tile rows), feet on row 47, hit box columns 14..17 (4 px, centred): the box the
physics uses does not change, only the art grows. One palette of 15 colours + transparent, player and computer share
the tiles (palette swap of the same indices).

Reused from ../2026-11-10-sootling-gum/draw_sootling_gum.py: palette logic (5 bit snap, luminance, dither pair check),
the fused membrane field, the tear front, the flap springs and ring-down, the sheet / GIF / gallery writers. The
backdrops are the cached clean renders of that round (bg_<mood>_1x.png: backgrounds-final plus placeholder islands).
"""
import os
import sys
import math
import importlib.util
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
PREV = os.path.join(HERE, '..', '2026-11-10-sootling-gum')
GAME_SHEET = os.path.join(HERE, '..', '..', '..', '..', 'assets', 'flier', 'sootling_sheet.png')
W, H = 32, 48
MAG = (255, 0, 255)
LX, LY = 0.6, -0.8            # key light from the upper right
PAGE = (22, 24, 30)
STATS = dict(clipped=0, edge=0)


def snap5(v):
    f = round(v * 31 / 255)
    return (f << 3) | (f >> 2)


def hexc(s):
    return tuple(snap5(int(s[i:i + 2], 16)) for i in (1, 3, 5))


def lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


# palette index 1..15 in this order (0 = transparent):
# 1 o keyline; 2..5 soot fur dark to light (keys 1 2 3 4); 6 r rim light and eye white; 7..9 e f g ember (wing, cap,
# lens, feet); 10 A gum deep line; 11..14 B C D E gum ramp dark to pale; 15 w hard white gloss
KEYS = 'o1234refgABCDEw'
PAL_P = {k: hexc(v) for k, v in dict(
    o='#0a0718', **{'1': '#1c1c48', '2': '#2c4480', '3': '#5490b8', '4': '#a0dcd8'}, r='#e8fff0',
    e='#7c1c40', f='#e45c28', g='#ffc458',
    A='#580c70', B='#b428a8', C='#ff54b8', D='#ffa4dc', E='#ffe0f4', w='#ffffff').items()}
PAL_C = {k: hexc(v) for k, v in dict(
    o='#100818', **{'1': '#3a1830', '2': '#742c38', '3': '#b45a3c', '4': '#e8a060'}, r='#fff0b4',
    e='#103c64', f='#1c94b4', g='#7cf0dc',
    A='#063c34', B='#148c4c', C='#54d44c', D='#b0f478', E='#e8ffc4', w='#ffffff').items()}
PALS = {'player': PAL_P, 'cpu': PAL_C}
OLD_GUM_P = [hexc('#f05ca4'), hexc('#ffa0c0')]      # previous round, gum mid and light (for the dusk distance number)


def grid():
    return [['.'] * W for _ in range(H)]


def put(g, x, y, k, only=None):
    if 0 <= x < W and 0 <= y < H and (only is None or g[y][x] in only):
        g[y][x] = k


def depths(mask):
    """1 = touches the outside, 2 = next ring, 3 = everything deeper"""
    d = {}
    for (x, y) in mask:
        if any((x + a, y + b) not in mask for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            d[(x, y)] = 1
    for (x, y) in mask:
        if (x, y) not in d and any(d.get((x + a, y + b)) == 1 for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            d[(x, y)] = 2
    for p in mask:
        d.setdefault(p, 3)
    return d


# ================================================================ the three takes
# body = (centre x, half width, half height); bottom of the fur is fixed at y 45.5, feet on rows 45..47.
# tufts = hand placed fur spikes (angle in degrees, 0 = right, -90 = up; length in px; half width in degrees)
TAKES = {
    'A': dict(name='Pilot: goggle on the eye, visor cap, candy gum',
              body=(15.5, 9.5, 7.5), membrane='candy', face='goggle',
              cap=dict(tilt=16, cut=0.38, visor=True, bobble=False, lenses=False),
              tufts=[(-158, 3.2, 13), (-176, 2.4, 11), (166, 3.0, 12), (146, 1.8, 11), (118, 1.3, 13), (64, 1.0, 12),
                     (22, 1.2, 9), (88, 0.9, 10)],
              idea='Widest, roundest body. One big ember goggle, strap round the head, visor cap. Gum drawn as solid '
                   'glossy candy: dark keyline all round, deep violet inner line on the shadow side, four pink bands, '
                   'arc highlight, bounce light at the lower left. Nothing shows through.'),
    'B': dict(name='Bright eyes: big eyes, goggles pushed up on the cap, glass gum',
              body=(15.5, 8.7, 8.4), membrane='glass', face='eyes',
              cap=dict(tilt=8, cut=0.50, visor=False, bobble=False, lenses=True),
              tufts=[(-150, 2.2, 12), (176, 2.8, 12), (156, 2.4, 11), (132, 1.6, 12), (-10, 1.6, 10), (30, 1.3, 10),
                     (100, 1.0, 12), (70, 0.9, 10)],
              idea='Tall ball body with two big white eyes (pupil, glint, lid), the goggles sit on the cap. Gum drawn as '
                   'glass: dark keyline only on the shadow half, coloured line and a pale inner rim on the lit half, a '
                   'see-through checker window at the lower left of each lobe where the backdrop shows.'),
    'C': dict(name='Fuzzball: glowing ember eyes, small tilted cap with bobble, thin-film gum',
              body=(15.5, 9.8, 7.9), membrane='film', face='glow',
              cap=dict(tilt=30, cut=0.46, visor=False, bobble=True, lenses=False),
              tufts=[(-165, 3.4, 10), (176, 3.6, 10), (158, 3.0, 9), (140, 2.6, 9), (-128, 2.4, 9), (-62, 2.2, 9),
                     (-34, 2.4, 9), (-8, 2.0, 8), (20, 1.8, 8), (48, 1.4, 9), (120, 1.8, 10), (92, 1.2, 9)],
              idea='Squat spiky soot ball, no whites: two glowing ember eyes in dark sockets, a small cap tilted to the '
                   'back with a bobble. Gum drawn as a thin film: thick saturated rim, pale dithered centre shifted '
                   'toward the light (the way a real gum bubble thins out), two small gloss ticks.'),
}
REST_ONE = (16.3, 16.6, 9.2, 9.6)
REST_TWO = ((9.9, 17.6, 7.2, 8.3), (22.0, 17.0, 7.2, 8.3))     # lobe 0 survives the first pop, lobe 1 pops first


def body_geom(T, dy=0, sq=0.0, puff=False):
    cx, rx0, ry0 = T['body']
    rx, ry = rx0 / (1 + sq), ry0 * (1 + sq)
    cy = 45.5 + dy - ry
    ma = math.radians(27)
    mouth = (cx + rx * math.cos(ma) + 0.6, cy + ry * math.sin(ma))
    return cx, cy, rx, ry, mouth


def mouth_of(T):
    return body_geom(T)[4]


# ---------------------------------------------------------------- ember wing (behind the body), bends with its speed
def draw_wing(g, root, ang_deg, bend, L=11.0):
    a0 = math.radians(ang_deg)
    pix = {}
    for y in range(H):
        for x in range(W):
            px, py = x + .5 - root[0], y + .5 - root[1]
            r = math.hypot(px, py)
            if r > L + 1 or r < 0.01:
                continue
            th = a0 + bend * min(1.0, r / L)
            ax, ay = -math.cos(th), -math.sin(th)
            u = (px * ax + py * ay) / L
            if u <= 0 or u > 1:
                continue
            v = px * ay - py * ax
            wl = 1.5 * math.sin(math.pi * u ** 0.55) + 0.35
            wt = 5.0 * math.sin(math.pi * u ** 0.75) * (0.60 + 0.40 * abs(math.cos(2.5 * math.pi * u))) + 0.35
            if -wl <= v <= wt:
                pix[(x, y)] = (u, v, wt)
    dp = depths(pix)
    for (x, y), (u, v, wt) in pix.items():
        if dp[(x, y)] == 1:
            k = 'o'
        elif v < 0.15 or u > 0.86:
            k = 'g'
        elif v < 0.55 * wt:
            k = 'f'
        else:
            k = 'e'
        g[y][x] = k


# ---------------------------------------------------------------- face parts
def lens_at(g, cx, cy, r, mode='open', only=None):
    ry = r * (0.42 if mode == 'squint' else 1.0)
    rr = r + (0.7 if mode == 'wide' else 0.0)
    if mode == 'wide':
        ry = rr
    for y in range(int(cy - rr - 2), int(cy + rr + 3)):
        for x in range(int(cx - rr - 2), int(cx + rr + 3)):
            px, py = x + .5 - cx, y + .5 - cy
            d = math.hypot(px / rr, py / ry)
            if d > 1.0:
                continue
            ring = math.hypot(px / (rr - 1.0), py / max(0.3, ry - 1.0)) > 1.0
            v = (px * LX + py * LY) / rr
            if ring:
                k = 'o'
            elif mode == 'shut':
                k = 'o' if abs(py) < 0.6 else ('4' if py < 0 else '3')
            elif v > 0.42:
                k = 'g' if math.hypot(px - 0.42 * rr, py + 0.42 * rr) > 1.15 else 'w'
            elif v > -0.30:
                k = 'g' if (v > 0.05) else 'f'
            else:
                k = 'e' if v < -0.62 else 'f'
            put(g, x, y, k, only)


def eye_at(g, cx, cy, rx, ry, mode='open', far=False):
    if mode == 'squint':
        ry *= 0.55
    if mode == 'wide':
        rx, ry = rx + 0.4, ry + 0.6
    if mode == 'shut':
        for i in range(-int(rx), int(rx) + 1):
            put(g, int(cx) + i, int(cy) + (0 if abs(i) < rx - 0.8 else -1), 'o')
            put(g, int(cx) + i, int(cy) - 1 - (0 if abs(i) < rx - 0.8 else 1), '4', '1234r')
        return
    for y in range(int(cy - ry - 2), int(cy + ry + 3)):
        for x in range(int(cx - rx - 2), int(cx + rx + 3)):
            px, py = x + .5 - cx, y + .5 - cy
            if math.hypot(px / rx, py / ry) > 1.0:
                continue
            ring = math.hypot(px / (rx - 1.0), py / max(0.3, ry - 1.0)) > 1.0
            k = 'o' if ring else ('4' if py < -ry * 0.45 and mode != 'wide' else 'r')     # lid shadow on the white
            put(g, x, y, k)
    pw = 1 if far or mode == 'wide' else 2
    px0 = int(cx + (0.2 if far else 0.4))
    for j in range(-1, 2 if mode != 'squint' else 1):
        for i in range(pw):
            put(g, px0 + i, int(cy) + j, 'o')
    if mode != 'squint':
        put(g, px0, int(cy) - 1, 'w')


def glow_at(g, cx, cy, rx, ry, mode='open'):
    if mode == 'squint':
        ry *= 0.5
    if mode == 'wide':
        rx, ry = rx + 0.5, ry + 0.6
    for y in range(int(cy - ry - 3), int(cy + ry + 4)):
        for x in range(int(cx - rx - 3), int(cx + rx + 4)):
            px, py = x + .5 - cx, y + .5 - cy
            d = math.hypot(px / rx, py / ry)
            if d > 1.0:
                if math.hypot(px / (rx + 1.0), py / (ry + 1.0)) <= 1.0:
                    put(g, x, y, '1' if py > -0.5 else 'o', '1234r')            # dark socket
                continue
            if mode == 'shut':
                k = 'o' if abs(py) < 0.6 else '1'
            elif d < 0.42 and py < 0.3:
                k = 'w'
            elif py > ry * 0.35:
                k = 'f'
            else:
                k = 'g'
            put(g, x, y, k)


def draw_body(g, T, wa=10, wb=0.0, lens='open', dy=0, sq=0.0, tuck=False, splat=None, puff=False, capdy=0, gumbit=False):
    cx, cy, rx, ry, mouth = body_geom(T, dy, sq)
    draw_wing(g, (cx - 0.50 * rx, cy - 0.45 * ry), wa, wb)
    rm = (rx + ry) / 2
    mask = {}
    for y in range(H):
        for x in range(W):
            px, py = x + .5 - cx, y + .5 - cy
            nx, ny = px / rx, py / ry
            d = math.hypot(nx, ny)
            a = math.degrees(math.atan2(ny, nx))
            R = 1.0
            for ta, tl, tw in T['tufts']:
                da = abs((a - ta + 180) % 360 - 180)
                if da < tw:
                    R += tl / rm * (1 - da / tw)
            inside = d <= R
            if puff and math.hypot((x + .5 - (mouth[0] - 2.6)) / 3.2, (y + .5 - (mouth[1] - 0.6)) / 2.7) <= 1.0:
                inside = True
            if inside:
                mask[(x, y)] = (nx, ny, d, math.radians(a))
    dp = depths(mask)
    for (x, y), (nx, ny, d, a) in mask.items():
        lit = (nx * LX + ny * LY) / max(1.0, d)
        t = 0.80 * lit + 0.40 * math.sqrt(max(0.0, 1 - min(d, 1.0) ** 2))
        t += 0.07 * math.sin(11 * a + 0.6) + 0.05 * math.sin(23 * a + d * 6.0)       # fur clumps break the bands
        ch = (x + y) % 2 == 0
        if dp[(x, y)] == 1:
            k = 'o'
        elif dp[(x, y)] == 2 and lit > 0.42:
            k = 'r'
        elif dp[(x, y)] == 2 and lit < -0.74:
            k = '2'                                         # bounce light under the belly and at the back
        elif t > 0.56:
            k = '4'
        elif t > 0.47:
            k = '4' if ch else '3'
        elif t > 0.13:
            k = '3'
        elif t > 0.04:
            k = '3' if ch else '2'
        elif t > -0.30:
            k = '2'
        elif t > -0.42:
            k = '2' if ch else '1'
        else:
            k = '1'
        g[y][x] = k
    # ---- cap
    C = T['cap']
    tau = math.radians(C['tilt'])
    cm = {}
    for y in range(H):
        for x in range(W):
            px, py = x + .5 - cx, y + .5 - (cy + capdy)
            nx, ny = px / (rx + 1.1), py / (ry + 1.1)
            if math.hypot(nx, ny) > 1.0:
                continue
            hgt = -ny * math.cos(tau) - nx * math.sin(tau)
            if hgt > C['cut']:
                cm[(x, y)] = (nx, ny, hgt)
    cd = depths(cm)
    for (x, y), (nx, ny, hgt) in cm.items():
        t = 0.9 * (nx * LX + ny * LY) + 0.35 * math.sqrt(max(0.0, 1 - nx * nx - ny * ny))
        if cd[(x, y)] == 1:
            k = 'o'
        elif hgt < C['cut'] + 0.13:
            k = 'e'                                         # hem band
        elif t > 0.62:
            k = 'g'
        elif t > 0.10:
            k = 'f'
        else:
            k = 'e'
        g[y][x] = k
    if cm:
        if C['visor']:
            hx, hy = max((p for p in cm if cm[p][2] < C['cut'] + 0.16), key=lambda p: (p[0], p[1]))
            for j, row in enumerate(("oooo.", "fggoo", "oooo.")):
                for i, k in enumerate(row):
                    if k != '.':
                        put(g, hx + i, hy - 1 + j, k)
        if C['bobble']:
            ty = min(p[1] for p in cm)
            xs = sorted(p[0] for p in cm if p[1] == ty)
            bx = xs[len(xs) // 2]
            for j, row in enumerate((".oo.", "ogwo", "offo")):
                for i, k in enumerate(row):
                    if k != '.':
                        put(g, bx - 2 + i, ty - 2 + j, k)
        if C['lenses']:
            lens_at(g, cx + 0.22 * rx, cy + capdy - 0.80 * ry, 2.5)
            lens_at(g, cx + 0.74 * rx, cy + capdy - 0.60 * ry, 2.1)
    # ---- face
    ey = cy - 0.10 * ry
    if T['face'] == 'goggle':
        ex = cx + 0.46 * rx
        for x in range(int(cx - rx) - 1, int(ex)):                          # strap round the head
            put(g, x, int(ey) - 1, 'e', '1234r')
            put(g, x, int(ey), 'o', '1234r')
        lens_at(g, ex + 4.6, ey + 0.3, 2.4, 'squint' if lens == 'shut' else lens, only='1234r')   # far lens, behind
        lens_at(g, ex, ey, 3.9, lens)
    elif T['face'] == 'eyes':
        eye_at(g, cx + 0.80 * rx, ey + 0.6, 1.6, 2.7, lens, far=True)
        eye_at(g, cx + 0.34 * rx, ey + 0.6, 2.7, 3.4, lens)
    else:
        glow_at(g, cx + 0.78 * rx, ey + 0.4, 1.6, 2.5, lens)
        glow_at(g, cx + 0.34 * rx, ey + 0.4, 2.5, 3.1, lens)
    # ---- lips (the gum leaves here)
    mx, my = int(mouth[0] - 1.2), int(mouth[1])
    put(g, mx, my, 'f', '1234ro')
    put(g, mx - 1, my, 'e', '1234r')
    put(g, mx, my + 1, 'o', '1234r')
    put(g, mx - 1, my - 1, 'o', '1234r')
    if gumbit:
        for x, y, k in ((mx + 1, my, 'C'), (mx + 2, my - 1, 'D'), (mx + 1, my - 1, 'A'), (mx + 2, my, 'A'), (mx + 2, my - 2, 'A')):
            put(g, x, y, k)
    # ---- feet
    fy = 45 + dy
    rows = ("...oo.....oo...", "..ofeo...ofeo..") if tuck else ("..oeo.....oeo..", ".offgoo..offgoo", ".oooooo..oooooo")
    for j, row in enumerate(rows):
        for i, k in enumerate(row):
            if k != '.':
                put(g, int(cx) - 7 + i, fy + j, k)
    # ---- gum stuck on the face after a pop
    if splat is not None:
        r = (3.9, 3.2, 2.3, 1.3)[splat]
        fx, fy2 = cx + 0.50 * rx, cy + 0.10 * ry
        for y in range(int(fy2 - r - 1), int(fy2 + r + 2)):
            for x in range(int(fx - r - 1), int(fx + r + 2)):
                px, py = x + .5 - fx, y + .5 - fy2
                d = math.hypot(px, py * 1.15)
                if d > r or not (0 <= x < W and 0 <= y < H) or g[y][x] == '.':
                    continue
                v = px * LX + py * LY
                g[y][x] = 'A' if d > r - 0.9 else ('E' if v > 0.45 * r else ('D' if v > 0.0 else 'C'))
        if splat == 0:
            put(g, int(fx + 0.3 * r), int(fy2 - 0.4 * r), 'w')
        for i in range((3, 5, 4, 0)[splat]):                                # drip
            put(g, int(fx + 1), int(fy2 + r) + i, 'C' if i % 2 else 'D', '1234ro')
        if splat < 3:
            put(g, int(fx + 1), int(fy2 + r) + (3, 5, 4)[splat], 'B', '1234ro')


# ================================================================ gum membrane
def shade_candy(dp, t, lit, d, nx, ny, ch):
    if dp == 1:
        return 'o'
    if dp == 2:
        return 'A' if t < 0.0 else ('B' if t < 0.36 else 'C')
    if 0.60 < d < 0.82 and lit < -0.74:
        return 'C'                                              # bounce light crescent
    if t > 0.79:
        return 'E'
    if t > 0.72:
        return 'E' if ch else 'D'
    if t > 0.48:
        return 'D'
    if t > 0.38:
        return 'D' if ch else 'C'
    if t > -0.10:
        return 'C'
    if t > -0.24:
        return 'C' if ch else 'B'
    return 'B'


def shade_glass(dp, t, lit, d, nx, ny, ch):
    if dp == 1:
        return 'o' if t < 0.30 else 'A'
    if dp == 2:
        return 'E' if t > 0.42 else ('A' if t < -0.20 else 'B')
    wd = math.hypot(nx + 0.27, ny - 0.25)
    if wd < 0.40:
        return None if ch else 'D'                              # see-through window: checker of holes
    if wd < 0.50 and lit < 0:
        return 'C'
    if t > 0.50:
        return 'D'
    if t > 0.40:
        return 'D' if ch else 'C'
    if t > -0.12:
        return 'C'
    if t > -0.26:
        return 'C' if ch else 'B'
    return 'B'


def shade_film(dp, t, lit, d, nx, ny, ch):
    if dp == 1:
        return 'o'
    if dp == 2:
        return 'A' if t < -0.22 else 'B'
    if dp == 3 and t < -0.22:
        return 'B'
    c = math.hypot(nx - 0.20, ny + 0.24)
    if c < 0.33:
        return 'E'
    if c < 0.45:
        return 'E' if ch else 'D'
    if c < 0.64:
        return 'D'
    if c < 0.77:
        return 'D' if ch else 'C'
    if t < -0.44:
        return 'B'
    if t < -0.30:
        return 'B' if ch else 'C'
    return 'C'


SHADE = dict(candy=shade_candy, glass=shade_glass, film=shade_film)
LIGHT_ANG = math.atan2(LY, LX)


def rag(ang, seed):
    return 0.9 * math.sin(3 * ang + seed) + 0.6 * math.sin(7 * ang + 2.1 * seed) + 0.4 * math.sin(11 * ang + 0.7 * seed)


def draw_gum(g, lobes, neck, style, tear=None):
    """lobes and neck circles: (cx, cy, rx, ry), fused into ONE membrane by a smooth union. tear = (lobe index, px, py,
    reach, seed): the membrane of that lobe is gone within reach px of the puncture; the retracting rim is thick and
    pale. The neck is never torn."""
    lobes = [b for b in lobes if b and b[2] > 0.5 and b[3] > 0.5]
    if not lobes:
        return
    blobs = lobes + list(neck)
    nl = len(lobes)
    K = 7.0
    mask = {}
    for y in range(H):
        for x in range(W):
            px, py = x + .5, y + .5
            ds = [math.hypot((px - cx) / rx, (py - cy) / ry) for cx, cy, rx, ry in blobs]
            f = ds[0] if len(ds) == 1 else -math.log(sum(math.exp(-K * d) for d in ds)) / K
            if f > 1.0:
                continue
            near = min(range(len(ds)), key=lambda i: ds[i])
            rimd = None
            if tear and near == tear[0]:
                _, tx, ty, reach, seed = tear
                dd = math.hypot(px - tx, py - ty)
                lim = reach + rag(math.atan2(py - ty, px - tx), seed)
                if dd < lim:
                    continue
                rimd = dd - lim
            mask[(x, y)] = (near, ds, rimd)
    if any(x in (0, W - 1) or y == 0 for (x, y) in mask):
        STATS['edge'] += 1
    dp = depths(mask)
    for (x, y), (near, ds, rimd) in mask.items():
        cx, cy, rx, ry = blobs[near]
        nx, ny = (x + .5 - cx) / rx, (y + .5 - cy) / ry
        d = ds[near]
        lit = nx * LX + ny * LY
        ch = (x + y) % 2 == 0
        p = dp[(x, y)]
        if near >= nl or rx < 2.8:                                  # neck and bubbles that are still tiny
            if p == 1:
                k = 'o' if lit < -0.15 else 'A'
            else:
                k = 'E' if lit > 0.55 else ('D' if lit > 0.05 else 'C')
        else:
            t = 0.75 * lit + 0.45 * math.sqrt(max(0.0, 1 - d * d))
            k = SHADE[style](p, t, lit, d, nx, ny, ch)
            if p > 1 and nl == 2 and lobes[0][2] >= 3 and lobes[1][2] >= 3 and max(ds[0], ds[1]) < 1.3:
                dd = abs(ds[0] - ds[1])                              # crease where the two lobes meet
                if dd < 0.085:
                    k = 'A' if p == 2 else ('B' if (dd < 0.04 or ch) else 'C')
                elif dd < 0.19 and ds[1] < ds[0] and k in ('C', 'B') and p > 2 and ny < 0.3:
                    k = 'D' if style != 'film' or ch else k         # light catches the lobe just right of the crease
            if rimd is not None and rimd < 2.2 and p > 1:
                k = 'w' if (rimd < 0.9 and ch) else 'E'
        if k is not None:
            g[y][x] = k
    for i in range(nl):                                             # hard gloss, kept clean
        cx, cy, rx, ry = lobes[i]
        if rx < 2.8:
            continue
        for (x, y), (near, ds, rimd) in mask.items():
            if near != i or rimd is not None or dp[(x, y)] < 3 or g[y][x] in ('.', 'A'):
                continue
            nx, ny = (x + .5 - cx) / rx, (y + .5 - cy) / ry
            d = ds[i]
            da = math.degrees((math.atan2(ny, nx) - LIGHT_ANG + math.pi) % math.tau - math.pi)
            if style == 'film':
                hit = (0.60 < d < 0.76 and abs(da) < 9) or (0.60 < d < 0.74 and abs(da - 30) < 5) or \
                      (rx > 5 and 0.62 < d < 0.74 and abs(abs(da) - 180) < 5)
            else:
                lo = 0.52 if rx > 5 else 0.40
                hit = (lo < d < 0.72 and abs(da + 4) < 23) or (0.56 < d < 0.72 and abs(da - 42) < 7 and rx > 5)
            if hit:
                g[y][x] = 'w'


def lerp(a, b, t):
    return a + (b - a) * t


def mixb(a, b, t):
    return tuple(lerp(u, v, t) for u, v in zip(a, b))


def grow(rest, s, mouth):
    """a bubble of inflation s (0..1.2) on its way from the lips to its rest place"""
    cx, cy, rx, ry = rest
    t = min(1.0, s) ** 0.8
    return (lerp(mouth[0] + 1.6, cx, t), lerp(mouth[1] - 1.2 - ry * s * 0.9, cy, t), rx * s, ry * s)


def layout(T, s0, s1):
    m = mouth_of(T)
    t = max(0.0, min(1.0, s1))
    b0 = grow(mixb(REST_ONE, REST_TWO[0], t), s0, m)
    b1 = grow(REST_TWO[1], s1, m) if s1 > 0 else None
    return b0, b1


def wob(b, q=0.0, dx=0.0, dy=0.0):
    """area preserving squash: ry * (1 + q), rx / (1 + q)"""
    cx, cy, rx, ry = b
    return (cx + dx, cy + dy, rx / (1 + q), ry * (1 + q))


def neck_for(T, lobes, sway=0.0, dy=0):
    """chain of circles from the lips to the underside of the membrane: thin and stretched at the lips, thicker where
    it runs into the membrane; the middle bows out to the right and sways with the membrane"""
    m = body_geom(T, dy)[4]
    lobes = [b for b in lobes if b]
    x0 = 21.5
    cover = [b for b in lobes if abs(x0 - b[0]) < 0.8 * b[2]]
    if not cover:
        b = max(lobes, key=lambda b: b[2])
        x0, cover = b[0] + 0.3 * b[2], [b]
    top = max(b[1] + b[3] * math.sqrt(max(0.0, 1 - ((x0 - b[0]) / b[2]) ** 2)) for b in cover) - 0.9
    dist = math.hypot(x0 - m[0], top - m[1])
    if dist < 3.0 or top > m[1]:
        return []
    bow = min(3.4, 0.24 * dist)
    c = (min(29.0, max(m[0], x0) + bow + sway), (m[1] + top) / 2 + 1.0)
    out = []
    n = max(4, int(dist / 1.6))
    for i in range(n + 1):
        t = i / n
        x = (1 - t) ** 2 * (m[0] + 0.4) + 2 * t * (1 - t) * c[0] + t * t * x0
        y = (1 - t) ** 2 * m[1] + 2 * t * (1 - t) * c[1] + t * t * top
        r = lerp(1.35, 2.5, t ** 1.5) - 0.25 * math.sin(math.pi * t)
        out.append((x, y, r, r))
    return out


def draw_bubbles(g, T, b0, b1, tear=None, sway=0.0, dy=0, neck=True):
    lobes = [b for b in (b0, b1) if b]
    ti = (len(lobes) - 1,) + tear if tear else None
    nk = neck_for(T, lobes, sway, dy) if neck else []
    draw_gum(g, lobes, nk, T['membrane'], ti)


def curve(a, c, b, n=40):
    pts = []
    for i in range(n + 1):
        t = i / n
        p = (int((1 - t) ** 2 * a[0] + 2 * t * (1 - t) * c[0] + t * t * b[0]),
             int((1 - t) ** 2 * a[1] + 2 * t * (1 - t) * c[1] + t * t * b[1]))
        if not pts or pts[-1] != p:
            pts.append(p)
    return pts


def strand(g, a, b, sag=1.2, keys='CD'):
    c = ((a[0] + b[0]) / 2 + sag, (a[1] + b[1]) / 2 + sag)
    for i, (x, y) in enumerate(curve(a, c, b)):
        if 1 <= x < W - 1 and 1 <= y < H and g[y][x] == '.':
            g[y][x] = keys[0] if i % 3 else keys[1]
            if g[y][x - 1] == '.' and i % 2:
                g[y][x - 1] = 'A'                                  # dark side so the strand reads on a bright sky


# ================================================================ motion: damped springs driven by the flap
FLAP_WA = [34, 62, 70, 22, -38, -52, -30, 4]                  # wing angle above the horizontal, degrees
FLAP_DY = [0, 0, 0, 0, -1, -1, -1, 0]
FLAP_SQ = [0.0, 0.03, 0.05, -0.03, -0.07, -0.03, 0.04, 0.02]  # body stretch (+) and squash (-)
FLAP_ACC = [0.0, 0.0, -0.25, 0.9, 1.0, 0.1, -0.55, -0.3]      # body acceleration seen by the bubble (up = positive)


def wing_bend(seq, f):
    return -0.0055 * (seq[f] - seq[f - 1])                     # the tip lags behind the root


def spring_loop(k, c, gain, loops=6, sub=4, phase=0):
    """steady state of x'' = -k x - c x' + gain * a(t) over the 8-frame flap; returns 8 samples"""
    x = vx = 0.0
    out = []
    for lp in range(loops):
        out = []
        for f in range(8):
            a = FLAP_ACC[(f + phase) % 8]
            for _ in range(sub):
                vx += (-k * x - c * vx + gain * a) / sub
                x += vx / sub
            out.append(x)
    return out


def ring(k, c, x0, v0, n, sub=4):
    """free ringing after a shock"""
    x, vx, out = x0, v0, []
    for f in range(n):
        out.append(x)
        for _ in range(sub):
            vx += (-k * x - c * vx) / sub
            x += vx / sub
    return out


def peak(v, a):
    m = max(abs(x) for x in v) or 1.0
    return [x * a / m for x in v]


def anim_flap(T, n):
    q0 = peak(spring_loop(0.95, 0.30, -0.115), 0.10)      # spring shapes kept, peaks set by hand
    y0 = peak(spring_loop(0.60, 0.35, 0.80), 1.3)
    q1 = peak(spring_loop(1.25, 0.28, -0.105, phase=7), 0.10)
    y1 = peak(spring_loop(0.75, 0.35, 0.72, phase=7), 1.2)
    sx = peak(spring_loop(0.80, 0.30, 0.50), 0.9)
    frs = []
    for f in range(8):
        g = grid()
        if n == 2:
            b0, b1 = layout(T, 1, 1)
            b0 = wob(b0, q0[f], -sx[f], y0[f])
            b1 = wob(b1, q1[f], sx[f], y1[f])
        else:
            b0, b1 = layout(T, 1, 0)
            b0 = wob(b0, q0[f] * 0.8, sx[f] * 0.8, y0[f])
        draw_bubbles(g, T, b0, b1, sway=sx[f] * 1.6, dy=FLAP_DY[f])
        draw_body(g, T, FLAP_WA[f], wing_bend(FLAP_WA, f), 'open', FLAP_DY[f], FLAP_SQ[f], tuck=FLAP_DY[f] < 0)
        frs.append(g)
    return frs


def particles(g, origin, f, seed, n=10):
    """gum droplets on ballistic paths with drag; a path that would leave the frame box is slowed until it fits"""
    for i in range(n):
        a = -math.pi / 2 + (i - (n - 1) / 2) * 0.33 + 0.25 * math.sin(seed + i * 1.7)
        sp = 2.3 + 1.5 * ((i * 37 + seed * 11) % 7) / 6
        life = 3 + i % 3
        vx, vy = sp * math.cos(a), sp * math.sin(a)

        def pos(t):
            return origin[0] + vx * t * (1 - 0.06 * t), origin[1] + vy * t + 0.30 * t * t
        for _ in range(10):
            if all(1 <= pos(t)[0] <= W - 3 and 1 <= pos(t)[1] <= H - 3 for t in range(life + 1)):
                break
            vx, vy = vx * 0.8, vy * 0.8
        else:
            STATS['clipped'] += 1
        if f > life:
            continue
        x, y = (int(v) for v in pos(f))
        if f <= 1:
            cells = ((0, 0, 'E'), (1, 0, 'C'), (0, 1, 'C'), (1, 1, 'A'))
        elif f <= 3:
            cells = ((0, 0, 'D'), (1, 0, 'B')) if i % 2 else ((0, 0, 'E'), (0, 1, 'B'))
        else:
            cells = ((0, 0, 'D'),)
        for ddx, ddy, k in cells:
            put(g, x + ddx, y + ddy, k, '.')


POP_LENS = ['wide', 'squint', 'squint', 'squint', 'shut', 'shut', 'shut', 'shut', 'squint', 'squint', 'open', 'open']
POP_WA = [10, 60, 66, 40, 10, -24, -46, -20, 8, 34, 12, 10]
POP_SPLAT = [None, None, None, None, None, 0, 0, 1, 1, 2, 3, None]
POP_SQ = [0.0, -0.08, -0.05, 0.03, 0.05, -0.06, -0.03, 0.02, 0.0, 0.0, 0.0, 0.0]


def anim_pop(T, n):
    """12 frames. n = lobes before the pop. Frame 0 swells with a white flash at the puncture; the tear front runs
    across the lobe (the membrane retracts into a thick pale rim); droplets fly; gum strands snap back to the lips; a
    glob lands on the face and drips off. With n = 2 the surviving lobe pulls round into one bubble and rings."""
    N = 12
    m = mouth_of(T)
    if n == 2:
        full0, full1 = layout(T, 1, 1)
        pb = full1
    else:
        full0, _ = layout(T, 1, 0)
        pb = full0
    pun = (pb[0] + 0.30 * pb[2], pb[1] - 0.82 * pb[3])                    # puncture from above
    diam = 2 * max(pb[2], pb[3])
    reach = [None, 0.30, 0.62, 0.92, 1.25]
    qk = ring(1.1, 0.26, 0.0, -0.20, N)                                   # survivor shock
    sk = ring(0.7, 0.30, 0.0, 1.5, N)
    anchor = (21.5, 24.0)
    ends = [(pb[0] - 0.9 * pb[2], pb[1] + 0.2 * pb[3]), (pb[0] + 0.1 * pb[2], pb[1] - 0.5 * pb[3]),
            (pb[0] + 0.8 * pb[2], pb[1] + 0.5 * pb[3])]
    frs = []
    for f in range(N):
        g = grid()
        merge = min(1.0, max(0.0, (f - 1) / 6.0))
        merge = merge * merge * (3 - 2 * merge)
        tear = None
        if n == 2:
            b0 = layout(T, 1, 1 - merge)[0]
            b0 = wob(b0, qk[f], -0.6 * sk[f], abs(qk[f]) * 3 if f else 0)
            b1 = None
            if f == 0:
                b1 = (full1[0], full1[1], full1[2] * 1.08, full1[3] * 1.08)
            elif f < len(reach):
                sh = 1 - 0.10 * f
                b1 = (lerp(full1[0], anchor[0], 0.12 * f), lerp(full1[1], anchor[1], 0.12 * f), full1[2] * sh, full1[3] * sh)
                tear = (pun[0], pun[1], reach[f] * diam, 1.3 + f)
            draw_bubbles(g, T, b0, b1, tear, sway=sk[f])
        else:
            if f == 0:
                draw_bubbles(g, T, (full0[0], full0[1], full0[2] * 1.06, full0[3] * 1.06), None)
            elif f < len(reach):
                sh = 1 - 0.10 * f
                b = (lerp(full0[0], anchor[0], 0.12 * f), lerp(full0[1], anchor[1], 0.12 * f), full0[2] * sh, full0[3] * sh)
                draw_bubbles(g, T, b, None, (pun[0], pun[1], reach[f] * diam, 1.3 + f), neck=f < 3)
        if f == 0:                                                         # puncture flash
            x, y = int(pun[0]), int(pun[1])
            for dx, dy in ((0, 0), (1, -1), (-1, 1), (1, 1), (-1, -1), (2, -2), (-2, 2), (0, -2), (0, 2), (2, 0), (-2, 0)):
                put(g, x + dx, y + dy, 'w')
        if 1 <= f <= 6:
            particles(g, pun, f - 1, 3 + n)
        if 3 <= f <= 7:                                                    # strands snap back to the lips
            t = (f - 3) / 4.0
            L = math.exp(-2.2 * t) * math.cos(4.2 * t)
            for i, e in enumerate(ends):
                p = (m[0] + (e[0] - m[0]) * L, m[1] + (e[1] - m[1]) * L + 3.0 * t * t)
                p = (min(W - 3, max(2, p[0])), max(2, p[1]))
                strand(g, p, m, sag=(1.5 - i) * (1.5 + 3 * t), keys='DC')
                for ddx, ddy, k in ((0, 0, 'E'), (1, 0, 'C'), (0, 1, 'C'), (1, 1, 'A')):
                    put(g, int(p[0]) + ddx, int(p[1]) + ddy, k)
        if n == 2 or f < 6:
            wa, wb = POP_WA[f], wing_bend(POP_WA, f)
        else:
            seq = (64, 44)
            wa, wb = seq[f % 2], -0.11 if f % 2 == 0 else 0.11
        draw_body(g, T, wa, wb, POP_LENS[f], 0, POP_SQ[f], splat=POP_SPLAT[f], gumbit=(n == 1 and f >= 5))
        frs.append(g)
    return frs


def anim_inflate(T):
    """16 frames, respawn: three breaths per lobe, the radius overshoots and rings, the first lobe makes room."""
    N = 16
    s0 = [0.14, 0.30, 0.46, 0.43, 0.66, 0.90, 1.08, 0.97, 1.02, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
    s1 = [0, 0, 0, 0, 0, 0, 0, 0.14, 0.30, 0.48, 0.45, 0.70, 0.94, 1.07, 0.96, 1.0]
    puff = [1, 1, 0, 0, 1, 1, 0, 1, 1, 0, 0, 1, 1, 0, 0, 0]
    q0 = [0.0] * 6 + ring(1.0, 0.30, 0.14, 0.0, N - 6)
    q1 = [0.0] * 13 + ring(1.2, 0.30, 0.14, 0.0, N - 13)
    wa = [8, 14, 20, 14, 8, 14, 20, 14, 8, 14, 20, 14, 8, 14, 20, 12]
    frs = []
    for f in range(N):
        g = grid()
        b0, b1 = layout(T, s0[f], s1[f])
        b0 = wob(b0, q0[f])
        if b1:
            b1 = wob(b1, q1[f])
        draw_bubbles(g, T, b0, b1)
        draw_body(g, T, wa[f], 0.0, 'squint' if puff[f] else 'open', 0, -0.05 if puff[f] else 0.02, puff=bool(puff[f]))
        frs.append(g)
    return frs


def anim_fall(T):
    """6 frames, no bubble: body stretched, wing streaming up and fluttering, cap lifting, a torn gum strand whips
    above the lips (travelling wave, amplitude grows toward the free end)."""
    m = mouth_of(T)
    wa = [70, 54, 72, 66, 50, 70]
    frs = []
    for f in range(6):
        g = grid()
        pts = []
        for i in range(10):
            a = 0.5 + 0.30 * i
            x = m[0] + 0.6 - 0.75 * i + a * math.sin(i * 0.9 - f * math.tau / 6)
            pts.append((min(W - 3, max(2, x)), m[1] - 1 - i * 2.1))
        n = 0
        for p0, p1 in zip(pts, pts[1:]):                     # connected strand, no loose pixels
            for x, y in curve(p0, ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2), p1, 8):
                if 1 <= x < W - 1 and 0 <= y < H and g[y][x] == '.':
                    g[y][x] = 'C' if n % 3 else 'D'
                    if g[y][x - 1] == '.':
                        g[y][x - 1] = 'A'
                    n += 1
        x, y = int(pts[-1][0]), int(pts[-1][1])
        for ddx, ddy, k in ((0, 0, 'E'), (1, 0, 'C'), (0, -1, 'D'), (1, -1, 'A'), (-1, 0, 'A')):
            put(g, x + ddx, y + ddy, k)
        draw_body(g, T, wa[f], wing_bend(wa, f), 'wide', 0, 0.07 if f % 2 else 0.04, tuck=f % 2 == 0, capdy=-1 if f % 3 == 1 else 0)
        frs.append(g)
    return frs


def glide0(T):
    g = grid()
    draw_body(g, T, 10, 0.0, 'wide', 0, gumbit=True)
    return g


def build(tk):
    T = TAKES[tk]
    A = dict(flap2=anim_flap(T, 2), flap1=anim_flap(T, 1), pop2=anim_pop(T, 2), pop1=anim_pop(T, 1),
             inflate=anim_inflate(T), fall=anim_fall(T))
    legacy = [A['flap2'][7], A['flap2'][1], A['flap2'][5], A['flap1'][7], A['flap1'][1], glide0(T), A['fall'][0]]
    return A, legacy


ORDER = ['flap2', 'flap1', 'pop2', 'pop1', 'inflate', 'fall']
LABEL = dict(flap2='flap, two lobes', flap1='flap, one lobe', pop2='first pop and pull-round', pop1='last pop',
             inflate='respawn blow-up', fall='fall')
GIF_MS = dict(flap2=70, flap1=70, pop2=85, pop1=85, inflate=90, fall=70)


# ================================================================ output
def render(g, pal):
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    p = im.load()
    for y in range(H):
        for x in range(W):
            if g[y][x] != '.':
                p[x, y] = pal[g[y][x]] + (255,)
    return im


def up(im, k):
    return im.resize((im.width * k, im.height * k), Image.NEAREST)


def sheet_build(legacy):
    im = Image.new('RGB', (7 * W, 2 * H), MAG)
    for r, pal in enumerate((PAL_P, PAL_C)):
        for i, g in enumerate(legacy):
            s = render(g, pal)
            im.paste(s, (i * W, r * H), s)
    return im


def sheet_ext(A):
    im = Image.new('RGB', (16 * W, 2 * len(ORDER) * H), MAG)
    for r, pal in enumerate((PAL_P, PAL_C)):
        for j, name in enumerate(ORDER):
            for i, g in enumerate(A[name]):
                s = render(g, pal)
                im.paste(s, (i * W, (r * len(ORDER) + j) * H), s)
    return im


def view(im1x, cols, rows, k):
    """presentation copy on the dark page colour with a slot frame per 32 x 48 box"""
    out = Image.new('RGB', (im1x.width * k + 8, im1x.height * k + 8), PAGE)
    d = ImageDraw.Draw(out)
    for r in range(rows):
        for c in range(cols):
            d.rectangle([4 + c * W * k + 1, 4 + r * H * k + 1, 4 + (c + 1) * W * k - 2, 4 + (r + 1) * H * k - 2], fill=(40, 44, 56))
    big = up(im1x.convert('RGB'), k)
    m = Image.eval(Image.merge('RGB', [c.point(lambda v, t=t: 255 if v == t else 0) for c, t in zip(big.split(), MAG)]).convert('L'),
                   lambda v: 0 if v == 255 else 255)
    out.paste(big, (4, 4), m)
    return out


def save_gif(path, frames, ms):
    cols = []
    for fr in frames:
        for _, c in fr.getcolors(1000000):
            if c not in cols:
                cols.append(c)
    if len(cols) > 256:
        q0 = Image.new('RGB', (frames[0].width * 2, frames[0].height))
        q0.paste(frames[0], (0, 0))
        q0.paste(frames[len(frames) // 2], (frames[0].width, 0))
        pal_im = q0.quantize(255, dither=Image.Dither.NONE)
    else:
        pal_im = Image.new('P', (1, 1))
        pal_im.putpalette([v for c in cols for v in c] + [0] * (768 - 3 * len(cols)))
    q = [fr.quantize(palette=pal_im, dither=Image.Dither.NONE) for fr in frames]
    q[0].save(path, save_all=True, append_images=q[1:], duration=ms, loop=0, disposal=1, optimize=False)


PANELS = [('player', 'dusk', (226, 34)), ('cpu', 'storm', (96, 40)), ('player', 'moon', (40, 40)), ('cpu', 'dusk', (60, 100))]


def gif_panels(path, frs, ms, bgs):
    """each frame on four crops of the real backdrops: player on the dusk sun, computer on storm, player on moon,
    computer on dusk buildings"""
    out = []
    for g in frs:
        im = Image.new('RGB', (len(PANELS) * 42 + 2, 60), PAGE)
        for i, (pn, mood, (x, y)) in enumerate(PANELS):
            im.paste(bgs[mood].crop((x, y, x + 40, y + 56)), (2 + i * 42, 2))
            s = render(g, PALS[pn])
            im.paste(s, (2 + i * 42 + 4, 6), s)
        out.append(up(im, 4))
    save_gif(path, out, ms)


def load_bgs():
    return {m: Image.open(os.path.join(PREV, 'bg_%s_1x.png' % m)).convert('RGB') for m in ('moon', 'storm', 'dusk')}


# (animation, frame, palette, centre x, feet y, flip): 8 fliers
CAST = [('flap2', 7, 'player', 50, 116, False),      # standing on the left island
        ('flap2', 4, 'cpu', 160, 50, True),
        ('flap1', 1, 'player', 250, 86, False),      # in front of the dusk sun
        ('pop2', 2, 'cpu', 96, 176, False),
        ('inflate', 5, 'player', 158, 84, False),    # respawn on the middle island
        ('flap2', 2, 'cpu', 262, 124, True),         # standing on the right island
        ('pop1', 3, 'player', 204, 190, False),      # just above the hazard strip
        ('fall', 1, 'cpu', 300, 200, True)]


def scene(bg, A):
    im = bg.copy().convert('RGBA')
    for name, f, pal, cx, fy, flip in CAST:
        s = render(A[name][f], PALS[pal])
        if flip:
            s = s.transpose(Image.FLIP_LEFT_RIGHT)
        im.alpha_composite(s, (cx - W // 2, fy - H))
    return im.convert('RGB')


def canon(t):
    h = tuple(r[::-1] for r in t)
    return min(t, h, t[::-1], h[::-1])


def tiles_unique(frames):
    """16 x 16 tiles (2 x 3 per frame): non-empty count, unique count, unique count when flips are allowed"""
    seen, seenf, raw = set(), set(), 0
    for g in frames:
        for ty in (0, 16, 32):
            for tx in (0, 16):
                t = tuple(''.join(g[y][tx:tx + 16]) for y in range(ty, ty + 16))
                if any(c != '.' for r in t for c in r):
                    raw += 1
                    seen.add(t)
                    seenf.add(canon(t))
    return raw, len(seen), len(seenf)


def keys_used(frames):
    s = set()
    for g in frames:
        for r in g:
            s |= set(r)
    s.discard('.')
    return s


def dither_count(frames):
    """pixels that sit in a checker: all four diagonal twins the same key, three or more 4-neighbours one other key"""
    n, steps = 0, {}
    for g in frames:
        for y in range(1, H - 1):
            for x in range(1, W - 1):
                c = g[y][x]
                if c == '.':
                    continue
                nb = [g[y][x - 1], g[y][x + 1], g[y - 1][x], g[y + 1][x]]
                dg = [g[y - 1][x - 1], g[y + 1][x + 1], g[y - 1][x + 1], g[y + 1][x - 1]]
                others = [k for k in nb if k != c and k != '.']
                if len(others) >= 3 and dg.count(c) >= 3 and len(set(others)) == 1:
                    n += 1
                    pr = tuple(sorted((c, others[0])))
                    steps[pr] = steps.get(pr, 0) + 1
    return n, steps


def outline_contrast(bg, g, pal, yband, gum_rows=27):
    """the sprite pixels of the gum (frame rows above gum_rows) that touch transparency, against the backdrop pixel
    right next to them, over a grid of positions. Returns (mean, 10th percentile, share under 24) of |luminance step|"""
    bp = bg.load()
    edge = []
    for y in range(gum_rows):
        for x in range(W):
            if g[y][x] == '.':
                continue
            for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                xx, yy = x + a, y + b
                if not (0 <= xx < W and 0 <= yy < H) or g[yy][xx] == '.':
                    edge.append((lum(pal[g[y][x]]), xx, yy))
    vals = []
    for oy in yband:
        for ox in range(4, 320 - W - 4, 20):
            for l, xx, yy in edge:
                X, Y = ox + xx, oy + yy
                if 0 <= X < 320 and 0 <= Y < 224:
                    vals.append(abs(l - lum(bp[X, Y])))
    vals.sort()
    return sum(vals) / len(vals), vals[len(vals) // 10], 100.0 * sum(1 for v in vals if v < 24) / len(vals)


def side_by_side(built, bgs):
    """old 16 x 32 art and the three new takes on the same dusk strip, same scale"""
    spec = importlib.util.spec_from_file_location('prevgum', os.path.join(PREV, 'draw_sootling_gum.py'))
    prev = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prev)
    pA, _ = prev.build('B')
    items = []
    if os.path.exists(GAME_SHEET):
        gs = Image.open(GAME_SHEET).convert('RGB')
        for row in (0, 1):
            c = gs.crop((0, row * 32, 16, row * 32 + 32)).convert('RGBA')
            px = c.load()
            key = px[0, 0][:3]                                 # the sheet's own background colour
            for y in range(32):
                for x in range(16):
                    if px[x, y][:3] in (MAG, key):
                        px[x, y] = (0, 0, 0, 0)
            items.append(c)
    else:
        items += [None, None]
    old = [items[0], items[1], prev.render(pA['flap2'][7], prev.PAL_P), prev.render(pA['flap2'][7], prev.PAL_C),
           prev.render(pA['flap1'][7], prev.PAL_P)]
    new = []
    for tk in TAKES:
        A = built[tk][0]
        new += [render(A['flap2'][7], PAL_P), render(A['flap2'][7], PAL_C), render(A['flap1'][7], PAL_P)]
    strip = Image.new('RGB', (4 + (len(old) + len(new)) * 36 + 12, 3 * 60 + 4), PAGE)
    for r, mood in enumerate(('dusk', 'moon', 'storm')):
        strip.paste(bgs[mood].crop((0, 30, 320, 30 + 56)), (2, 2 + r * 60))
        strip.paste(bgs[mood].crop((0, 30, strip.width - 324, 30 + 56)).transpose(Image.FLIP_LEFT_RIGHT), (322, 2 + r * 60))
        x = 6
        for s in old + [None] + new:
            if s is None:
                x += 8
                continue
            strip.paste(s, (x + (W - s.width) // 2, 2 + r * 60 + 4 + (H - s.height)), s)
            x += 36
    return up(strip, 4)


COMMON_WEAK = [
    'Body and membrane shapes come from formulas (ellipse, fused circles) with hand-placed tufts, face, cap and feet on top. '
    'The shading bands are computed, so the clusters are less hand-made than final art needs; a hand clean-up pass is still due.',
    'The body fills only the lower third of the 32 x 48 box (about 20 x 17 px); the membrane takes the rest.',
    'Tile cost is high: about 36 unique 16 x 16 tiles for the 7-frame build set and about 300 for the extended set. '
    'Flips save almost nothing because the light comes from one side.',
    'The dark keyline (luminance 10) still sits close to the darkest sky patches (luminance about 21): '
    'the weakest tenth of the outline has a step of 14 to 19 on clear night and storm.',
    'Pop frames 3 to 6 leave a few loose single pixels from the snapping strands. Fall has 6 frames only.',
    'The palette swap changes 14 of 15 indices (fur and ember change too, not only the gum).',
]
WEAK = {
    'A': ['The cap and the goggle cover most of the head: it reads as a pilot first and as a soot creature second.',
          'The far lens is a 2 px sliver and can read as noise.',
          'Candy gum is opaque: no translucency at all, the least gum-like material of the three.'],
    'B': ['The checker window can read as a grille or a speaker, not as see-through gum, most of all on the busy dusk city.',
          'The lit half of the membrane has no dark keyline: on the dusk sun and on the moon the pale rim is the only edge.',
          'The black eye ring is heavy at this size; the goggles on the cap are only a few orange pixels.'],
    'C': ['The ember eyes read as two orange blocks, the face has the least expression.',
          'The pale dithered centre flattens the lobe: it reads as a soft ball more than a glossy bubble.',
          'The D/E dither pair has a step of 31, close to the limit of 28. Most dither pixels of the three (about 600).',
          'The cap is a thin band; the bobble is 3 px.'],
}
for _k in WEAK:
    WEAK[_k] = WEAK[_k] + COMMON_WEAK


def main():
    out = []
    bgs = load_bgs()
    med, hz = {}, {}
    for m, im in bgs.items():
        ls = sorted(lum(p) for p in im.crop((0, 16, 320, 176)).get_flattened_data())
        med[m] = (ls[len(ls) // 20], ls[len(ls) // 2], ls[len(ls) * 19 // 20])
        ls = sorted(lum(p) for p in im.crop((0, 192, 320, 224)).get_flattened_data())
        hz[m] = ls[len(ls) // 2]
    out.append('Sootling 32 x 48 with gum design B: numbers (script output)')
    out.append('frame box 32 x 48 (2 sprite columns x 3 tile rows), feet row 47, hit box columns 14..17 (4 px, centred, unchanged physics)')
    out.append('palette index order 1..15: ' + ' '.join(KEYS) + '   (0 = transparent, magenta 255,0,255 in the sheets)')
    for pn, pal in PALS.items():
        out.append('palette %-6s: %s' % (pn, ' '.join('%s=%02x%02x%02x(%d)' % (k, *pal[k], round(lum(pal[k]))) for k in KEYS)))
        assert len(set(pal.values())) == 15, pn
    diff = [i + 1 for i, k in enumerate(KEYS) if PAL_P[k] != PAL_C[k]]
    out.append('palette swap player (pink gum) -> computer (lime gum): same tiles, indices that change colour: %s; gum = indices 10..14, '
               'soot fur = 2..6, ember = 7..9, keyline = 1; index 15 (white) is the same' % ' '.join(map(str, diff)))
    out.append('backdrop luminance, play area lines 16..175 (p5 / median / p95): ' +
               '  '.join('%s %d / %d / %d' % (m, *v) for m, v in med.items()))
    out.append('hazard strip median luminance (lines 192..223): ' + '  '.join('%s %d' % kv for kv in hz.items()))
    for pn, pal in PALS.items():
        for k, label in (('o', 'keyline (gum and soot)'), ('A', 'gum deep line'), ('C', 'gum mid'), ('D', 'gum light')):
            out.append('flat contrast %-6s %-22s (lum %3d) against median backdrop: ' % (pn, label, round(lum(pal[k]))) +
                       '  '.join('%s %d' % (m, round(abs(lum(pal[k]) - v[1]))) for m, v in med.items()) +
                       '   against hazard: ' + '  '.join('%s %d' % (m, round(abs(lum(pal[k]) - v))) for m, v in hz.items()))
    dq = bgs['dusk'].crop((0, 16, 320, 176)).quantize(8, dither=Image.Dither.NONE)
    dpal = dq.getpalette()[:24]
    dcols = [tuple(dpal[i * 3:i * 3 + 3]) for _, i in dq.getcolors()]

    def rgbd(c):
        return min(math.dist(c, d) for d in dcols)
    out.append('player pink against the 8 main dusk colours, smallest RGB distance: gum mid %.0f (previous round %.0f), gum light %.0f (previous round %.0f)'
               % (rgbd(PAL_P['C']), rgbd(OLD_GUM_P[0]), rgbd(PAL_P['D']), rgbd(OLD_GUM_P[1])))
    built = {}
    for tk, T in TAKES.items():
        STATS['clipped'] = STATS['edge'] = 0
        A, legacy = build(tk)
        built[tk] = (A, legacy)
        allf = [g for n in ORDER for g in A[n]] + [legacy[5]]
        ku = keys_used(allf)
        assert ku <= set(KEYS), ku
        raw, uniq, uniqf = tiles_unique(allf)
        lraw, luniq, luniqf = tiles_unique(legacy)
        dn, dsteps = dither_count(allf)
        out.append('== take %s: %s' % (tk, T['name']))
        out.append('  frames: build set 7 (glide2 up2 down2 glide1 up1 glide0 fall); extended ' +
                   ', '.join('%s %d' % (n, len(A[n])) for n in ORDER) + ' + glide0 = %d' % (sum(len(A[n]) for n in ORDER) + 1))
        out.append('  colours used %d of 15 (unused: %s)' % (len(ku), ' '.join(sorted(set(KEYS) - ku)) or 'none'))
        out.append('  16 x 16 tiles, build set: %d non-empty of %d, %d unique, %d unique with flips allowed' % (lraw, 7 * 6, luniq, luniqf))
        out.append('  16 x 16 tiles, extended set: %d non-empty of %d, %d unique, %d unique with flips allowed (both palettes share them)'
                   % (raw, len(allf) * 6, uniq, uniqf))
        st = {pr: min(abs(lum(PAL_P[pr[0]]) - lum(PAL_P[pr[1]])), abs(lum(PAL_C[pr[0]]) - lum(PAL_C[pr[1]]))) for pr in dsteps}
        out.append('  checker dither pixels over the extended set: %d; pairs (count, smaller luminance step of the two palettes): %s'
                   % (dn, ', '.join('%s/%s %d step %.0f' % (a, b, c, st[(a, b)]) for (a, b), c in sorted(dsteps.items()))))
        out.append('  minimum dither step: %.1f (rule: at least 28)%s' % (min(st.values()), '' if min(st.values()) >= 28 else '  [WARN] under 28'))
        out.append('  droplets cut by the frame box: %d; frames where the membrane touches the box edge (columns 0, 31 or row 0): %d'
                   % (STATS['clipped'], STATS['edge']))
        for pn, pal in PALS.items():
            parts = []
            for m in ('dusk', 'moon', 'storm'):
                mean, p10, low = outline_contrast(bgs[m], A['flap2'][0], pal, range(16, 130, 12))
                parts.append('%s mean %.0f p10 %.0f under24 %.0f%%' % (m, mean, p10, low))
            hparts = []
            for m in ('dusk', 'moon', 'storm'):
                mean, p10, low = outline_contrast(bgs[m], A['flap2'][0], pal, [188])
                hparts.append('%s mean %.0f p10 %.0f' % (m, mean, p10))
            out.append('  gum outline contrast %-6s (edge pixel against the backdrop pixel beside it, luminance step): %s' % (pn, '  '.join(parts)))
            out.append('  gum outline contrast %-6s over the hazard strip: %s' % (pn, '  '.join(hparts)))
        sb = sheet_build(legacy)
        sb.save(os.path.join(HERE, '%s_sheet_1x.png' % tk))
        view(sb, 7, 2, 4).save(os.path.join(HERE, '%s_sheet_4x.png' % tk))
        se = sheet_ext(A)
        se.save(os.path.join(HERE, '%s_ext_1x.png' % tk))
        view(se, 16, 12, 2).save(os.path.join(HERE, '%s_ext_2x.png' % tk))
        for m, bg in bgs.items():
            up(scene(bg, A), 2).save(os.path.join(HERE, '%s_scene_%s_2x.png' % (tk, m)))
        if '--nogif' not in sys.argv:
            for n in ORDER:
                gif_panels(os.path.join(HERE, '%s_anim_%s_4x.gif' % (tk, n)), A[n], GIF_MS[n], bgs)
    side_by_side(built, bgs).save(os.path.join(HERE, 'compare_old_new_4x.png'))
    print('\n'.join(out))
    open(os.path.join(HERE, 'numbers.txt'), 'w').write('\n'.join(out) + '\n')
    write_html(out)


def write_html(nums):
    css = ('body{background:#16181e;color:#d4d7de;font-family:Helvetica,Arial,sans-serif;margin:24px;line-height:1.45}'
           'h1{font-size:22px}h2{font-size:18px;margin-top:36px;border-top:1px solid #333842;padding-top:18px}h3{font-size:15px;margin:18px 0 6px}'
           'img{image-rendering:pixelated;image-rendering:crisp-edges;display:block;max-width:100%}'
           '.row{display:flex;flex-wrap:wrap;gap:16px;align-items:flex-start}.cell{background:#1d2028;padding:10px;border:1px solid #2c303a}'
           '.cell p{margin:6px 0 0;font-size:13px;color:#a9aebb;max-width:700px}ul{margin:6px 0;padding-left:20px;font-size:14px;max-width:700px}'
           'pre{background:#1d2028;padding:12px;font-size:12px;overflow-x:auto;color:#b9bdc9}p{max-width:980px;font-size:14px}')
    h = ['<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>Sootling 32 x 48, gum design B, drafts</title><style>',
         css, '</style></head><body><h1>Sootling at 32 x 48 with the two-lobed gum bubble (drafts, three takes on design B)</h1>',
         '<p>View at 100 percent browser zoom. Drafts only, nothing here is game data. All three takes are the same concept: one gum '
         'membrane with two lobes blown from the mouth; first pop pulls it round into one bubble; second pop: fall. They differ in '
         'body design and in how the membrane is drawn. Every animation runs on four crops of the real backdrops: player on the '
         'dusk sun, computer on storm, player on clear night, computer on dusk buildings.</p>',
         '<h2>Old 16 x 32 art beside the new 32 x 48 takes (same scale, 4x)</h2>'
         '<img src="compare_old_new_4x.png" alt="old and new side by side">'
         '<p>Left group: the sheet in the game now (player, computer), then the previous round design B at 16 x 32 (player, computer, '
         'one lobe). Right group: take A, B, C, each as player with two lobes, computer with two lobes, player with one lobe. '
         'Rows: ember dusk, clear night, storm.</p>']
    for tk, T in TAKES.items():
        h.append('<h2>Take %s: %s</h2><p>%s</p><div class="row">' % (tk, T['name'], T['idea']))
        for n in ORDER:
            h.append('<div class="cell"><img src="%s_anim_%s_4x.gif" width="680" height="240" alt="%s %s"><p>%s</p></div>'
                     % (tk, n, tk, n, LABEL[n].capitalize()))
        h.append('</div><p>Weak points:</p><ul>%s</ul>' % ''.join('<li>%s</li>' % w for w in WEAK[tk]))
    for m, label in (('dusk', 'Ember dusk'), ('moon', 'Clear night'), ('storm', 'Storm')):
        h.append('<h2>Scene with 8 fliers, %s (2x)</h2>' % label)
        for tk, T in TAKES.items():
            h.append('<h3>Take %s</h3><img src="%s_scene_%s_2x.png" width="640" height="448" alt="scene %s %s">' % (tk, tk, m, tk, m))
    h.append('<h2>Sheets</h2><p>Build set (7 frames: glide with two lobes, flap up, flap down, glide with one lobe, flap up with one, no '
             'bubble, fall; top row player, bottom row computer) at 4x, and the extended sheet at 2x (rows: flap with two lobes 8, flap '
             'with one 8, first pop 12, last pop 12, respawn 16, fall 6; player block then computer block). The 1x files with magenta '
             'background are next to them (<code>_sheet_1x.png</code>, <code>_ext_1x.png</code>).</p>')
    for tk in TAKES:
        h.append('<h3>Take %s</h3><div class="cell"><img src="%s_sheet_4x.png" alt="build sheet %s"><p>Build set, 4x</p></div>'
                 '<div class="cell" style="margin-top:10px"><img src="%s_ext_2x.png" alt="extended sheet %s"><p>Extended sheet, 2x</p></div>'
                 % (tk, tk, tk, tk, tk))
    h.append('<h2>Numbers</h2><pre>%s</pre></body></html>' % '\n'.join(nums).replace('<', '&lt;'))
    open(os.path.join(HERE, 'index.html'), 'w').write('\n'.join(h))


if __name__ == '__main__':
    main()
