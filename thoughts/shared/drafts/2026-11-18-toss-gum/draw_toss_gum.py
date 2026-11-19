#!/usr/bin/env python3.14 -I
"""Toss Gum drafts (2026-11-18). 320 x 224 native, shown 3x. Run: python3.14 -I draw_toss_gum.py
Reused, not redrawn: Sootling frames and palettes (assets/flier), gum levels, pop frames and warm/hot cue
palettes (assets/gum), the Gum Fling turf and the dusk city planes (2026-11-18-fling-field/draw_fling_field.py).
New in this draft, as hand-placed grids below: button tags, seat pads, 1P/2P chips, gum shreds, splats, flash, strain ticks.
Motion (toss arc, burst shreds, knocked carrier) is simulated: gravity, drag, bounce, stick."""
import importlib.util, json, os, random
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
spec = importlib.util.spec_from_file_location('ff', os.path.join(HERE, '..', '2026-11-18-fling-field', 'draw_fling_field.py'))
ff = importlib.util.module_from_spec(spec); spec.loader.exec_module(ff)
MOOD = 'dusk'
snap = ff.snap

# ---- reused sheets -------------------------------------------------------------------------------------------
SJ = json.load(open(os.path.join(REPO, 'assets', 'flier', 'sootling_sheet.json')))
SOOT = Image.open(os.path.join(REPO, 'assets', 'flier', 'sootling_sheet.png')).convert('RGBA')
GJ = json.load(open(os.path.join(REPO, 'assets', 'gum', 'gum_sheet.json')))
GUM = Image.open(os.path.join(REPO, 'assets', 'gum', 'gum_sheet.png')).convert('RGBA')
PLAYER = [tuple(c) for c in SJ['palettes']['player']]
GUMPAL = [tuple(c) for c in GJ['palettes']['level16']]
CLIP = dict(zip(('flap2', 'flap1', 'pop2', 'pop1', 'inflate', 'fall', 'idle', 'walk0', 'land0', 'breathe0'), SJ['tables']['clip_first']))

# Bird palettes, 15 entries in the sheet order: outline, body 5 dark to light, beak 3, gum 5, white.
# p1 and cpu1 are the game palettes. p2 and cpu2 are new picks for this draft (owner to confirm).
PAL = {
    'p1': PLAYER,
    'cpu1': [tuple(c) for c in SJ['palettes']['cpu']],
    'p2': [snap(c) for c in ((16, 8, 24), (99, 33, 24), (181, 90, 16), (239, 165, 24), (255, 222, 82), (255, 255, 198),
                             (123, 24, 66), (214, 49, 49), (255, 140, 99),
                             (107, 16, 132), (181, 41, 165), (255, 82, 181), (255, 165, 222), (255, 222, 247), (255, 255, 255))],
    'cpu2': [snap(c) for c in ((16, 8, 24), (49, 24, 90), (99, 49, 148), (156, 99, 206), (206, 165, 239), (247, 231, 255),
                               (90, 49, 16), (222, 140, 24), (255, 222, 99),
                               (8, 82, 66), (16, 140, 74), (82, 214, 74), (173, 247, 123), (231, 255, 198), (255, 255, 255))],
}
# out bird: body ramp swapped to the gum pinks (a palette swap on hardware, no new tiles)
PAL['gummed'] = [PLAYER[0], GUMPAL[1], GUMPAL[4], GUMPAL[6], GUMPAL[8], GUMPAL[9]] + [GUMPAL[2], GUMPAL[5], GUMPAL[8]] + PLAYER[9:]
PAL['white'] = [(255, 255, 255)] * 15


def recolour(im, src, dst):
    lut = dict(zip(src, dst))
    out = im.copy(); px = out.load()
    for y in range(out.height):
        for x in range(out.width):
            r, g, b, a = px[x, y]
            if a:
                assert (r, g, b) in lut, 'colour %r not in the source palette' % ((r, g, b),)   # self-check: sheet matches its palette
                px[x, y] = lut[(r, g, b)] + (255,)
    return out


_birds = {}
def bird(i, pal, flip=False):
    k = (i, pal, flip)
    if k not in _birds:
        r = SJ['animations']['player'][i]
        f = recolour(SOOT.crop((r['x'], r['y'], r['x'] + r['w'], r['y'] + r['h'])), PLAYER, PAL[pal])
        _birds[k] = f.transpose(Image.FLIP_LEFT_RIGHT) if flip else f
    return _birds[k]


CUE = {'calm': None}
for name in ('warm', 'hot'):
    CUE[name] = {GUMPAL[e - 1]: tuple(c) for e, c in zip(GJ['cue_palettes']['entries'], GJ['cue_palettes'][name])}
CUE['flash'] = {c: (255, 255, 255) for c in GUMPAL[1:]}

_gums = {}
def gum(level, k, cue='calm'):
    key = (level, k, cue)
    if key not in _gums:
        r = GJ['animations'][level][k]
        f = GUM.crop((r['x'], r['y'], r['x'] + r['w'], r['y'] + r['h']))
        if CUE[cue]:
            px = f.load()
            for y in range(f.height):
                for x in range(f.width):
                    c = px[x, y]
                    if c[3] and c[:3] in CUE[cue]:
                        px[x, y] = CUE[cue][c[:3]] + (255,)
        _gums[key] = f
    return _gums[key]


def put_gum(im, level, k, cue, x, y):          # (x, y) = knot, bottom centre of the sheet cell
    f = gum('level%d' % level if isinstance(level, int) else level, k, cue)
    b = f.getbbox()
    im.alpha_composite(f, (round(x) - f.width // 2, round(y) - (b[3] if b else f.height)))


# ---- new hand grids ------------------------------------------------------------------------------------------
def stamp(im, rows, cols, x, y, flipx=False, flipy=False):
    rows = rows[::-1] if flipy else rows
    for j, row in enumerate(rows):
        row = row[::-1] if flipx else row
        for i, ch in enumerate(row):
            if ch != '.' and 0 <= x + i < im.width and 0 <= y + j < im.height:
                im.putpixel((x + i, y + j), cols[ch] + (255,))


TAG = [
    ".KKKKKKKKK.",
    "KLLLLLLLLFK",
    "KLFFFFFFFFK",
    "KFFFFFFFFFK",
    "KFFFFFFFFFK",
    "KFFFFFFFFFK",
    "KFFFFFFFFFK",
    "KFFFFFFFFFK",
    "KFFFFFFFFDK",
    "KFFFFFFFFDK",
    "KFDDDDDDDDK",
    ".KKKFDDKKK.",
    "....KFK....",
    ".....K.....",
]
LETTER = {
    'A': [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    'B': ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."],
    'C': [".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."],
}
K = snap((8, 8, 24))
TAGCOL = {   # Neo Geo button colours: A red, B yellow, C green
    'A': {'K': K, 'L': snap((255, 148, 132)), 'F': snap((222, 41, 49)), 'D': snap((132, 16, 49)), '#': (255, 255, 255)},
    'B': {'K': K, 'L': snap((255, 239, 148)), 'F': snap((239, 165, 16)), 'D': snap((148, 82, 0)), '#': (255, 255, 255)},
    'C': {'K': K, 'L': snap((181, 255, 148)), 'F': snap((33, 173, 66)), 'D': snap((8, 99, 66)), '#': (255, 255, 255)},
}

def tag(im, letter, cx, top):
    c = TAGCOL[letter]
    stamp(im, TAG, c, cx - 5, top)
    stamp(im, LETTER[letter], {'#': c['D']}, cx - 1, top + 3)     # drop shadow, one pixel right and down
    stamp(im, LETTER[letter], c, cx - 2, top + 2)


PAD = [          # chalk seat ring with the bird's shadow inside (s = dark turf, checker dither)
    "....WWWWWWWWWWWW....",
    "..WWws.s.s.s.s.wWW..",
    ".Ww.s.s.s.s.s.s.swW.",
    ".Wws.s.s.s.s.s.s.wW.",
    "..WWw.s.s.s.s.swWW..",
    "....wWWWWWWWWWWw....",
]
CHIP = {'1': [".#.", "##.", ".#.", ".#.", "###"], '2': ["##.", "..#", ".#.", "#..", "###"], 'P': ["##.", "#.#", "##.", "#..", "#.."]}
SHRED = {
    'big': [".dmm..", "dpplm.", "mplhpm", "dpplpd", ".dmpd."],
    'med': [".mm.", "mplm", "dppd", ".dd."],
    'sml': ["ml", "dp"],
    'dot': ["p"],
    'streak': ["...h", "..l.", ".p..", "m..."],          # fast shred, flipped to its heading
    'long': ["mplh"],
    'splat_big': ["..mplm...", "dmpplppmd", ".d.dmd.d."],
    'splat_med': [".mplm.", "dmppmd"],
    'splat_sml': ["mpd"],
}
FLASH = [        # first two burst frames
    ".......W.......",
    ".......W.......",
    "..W...WWW...W..",
    "...W..WWW..W...",
    "....WWWhWWW....",
    "....WhhhhhW....",
    "..WWWhhhhhWWW..",
    "WWWWhhhhhhhWWWW",
    "..WWWhhhhhWWW..",
    "....WhhhhhW....",
    "....WWWhWWW....",
    "...W..WWW..W...",
    "..W...WWW...W..",
    ".......W.......",
    ".......W.......",
]
TICKS = [        # strain ticks around a frantic gum, two alternating sets, placed relative to the gum centre
    [(-13, -6, ["W.", ".W"]), (12, -7, [".W", "W."]), (-14, 4, ["WW"]), (13, 3, ["WW"])],
    [(-11, -11, ["W.", ".W"]), (10, -12, [".W", "W."]), (-15, -1, ["WW"]), (14, -2, ["WW"]), (0, -17, ["W", "W"])],
]
GC = {'d': GUMPAL[1], 'm': GUMPAL[4], 'p': GUMPAL[6], 'l': GUMPAL[8], 'h': GUMPAL[9], 'W': (255, 255, 255)}
GC_HOT = {k: CUE['hot'].get(v, v) for k, v in GC.items()}
CHALK = {'W': snap((247, 247, 231)), 'w': snap((165, 214, 148))}

# ---- field ---------------------------------------------------------------------------------------------------
_bg = {}
def ground(top):
    """Dusk city + Gum Fling turf. top 160: the Fling floor as is. top 128: two more turf rows (rows 1 and 2 again, shifted 64 px)."""
    if top not in _bg:
        sc = ff.scene(MOOD)
        t = ff.turf(MOOD, 448)
        rows = [0, 1, 2, 3] if top == 160 else [0, 1, 2, 1, 2, 3]
        for n, r in enumerate(rows):
            dx = 64 if (top != 160 and n in (3, 4)) else 0
            sc.alpha_composite(t.crop((dx, 16 * r, dx + 320, 16 * r + 16)), (0, top + 16 * n))
        dark = min((c for _, c in t.convert('RGB').getcolors(999)), key=lambda c: c[0] * 3 + c[1] * 6 + c[2])
        _bg[top] = (sc, dark)
    return _bg[top][0].copy(), _bg[top][1]


def chalk_px(im, x, y):
    if (x * 7 + y * 13) % 17:                    # worn gaps
        im.putpixel((x, y), CHALK['W'] + (255,))
        if y + 1 < 224:
            im.putpixel((x, y + 1), CHALK['w'] + (255,))


LAYOUT = {
    # seats clockwise seen from above: back, right, front, left. Feet points. A = seat+1, B = seat+2, C = seat+3
    'ellipse': {'top': 160, 'seats': [(128, 172), (262, 193), (192, 218), (58, 193)]},
    'diamond': {'top': 128, 'seats': [(160, 148), (250, 178), (160, 208), (70, 178)]},
}
WHO = ['cpu1', 'p2', 'cpu2', 'p1']               # back, right, front, left
FLIP = [False, True, True, False]                # everyone looks at the middle


def field(layout):
    L = LAYOUT[layout]
    im, dark = ground(L['top'])
    s = L['seats']
    if layout == 'ellipse':                      # shortcut: ring pixels come from the ellipse equation, not a hand grid; redraw by hand at pixel pass
        cx, cy, rx, ry = 160, 195, 102, 24
        for x in range(cx - rx, cx + rx + 1):
            dy = ry * (1 - ((x - cx) / rx) ** 2) ** 0.5
            for y in (round(cy - dy), round(cy + dy)):
                chalk_px(im, x, y)
        for y in range(cy - ry, cy + ry + 1):
            dx = rx * (1 - ((y - cy) / ry) ** 2) ** 0.5
            for x in (round(cx - dx), round(cx + dx)):
                chalk_px(im, x, y)
    else:                                        # diamond: 3 across, 1 down steps between the seats
        for (x0, y0), (x1, y1) in zip(s, s[1:] + s[:1]):
            n = abs(x1 - x0)
            for k in range(n + 1):
                chalk_px(im, x0 + (k if x1 > x0 else -k), y0 + (k // 3 if y1 > y0 else -(k // 3)))
    for x, y in s:
        stamp(im, PAD, {'W': CHALK['W'], 'w': CHALK['w'], 's': dark}, x - 10, y - 3)
    return im


def chip(im, text, pal, x, y):
    for n, ch in enumerate(text):
        stamp(im, CHIP[ch], {'#': K}, x + 4 * n + 1, y + 1)
        stamp(im, CHIP[ch], {'#': PAL[pal][5]}, x + 4 * n, y)


def hold(layout, seat):                          # gum knot when a bird holds it over its head
    x, y = LAYOUT[layout]['seats'][seat]
    return x, y - 20


def birds(im, layout, frame, out=(), dy=None, skip=()):
    s = LAYOUT[layout]['seats']
    for i in sorted(range(4), key=lambda i: s[i][1]):
        if i in out or i in skip:
            continue
        f = bird(CLIP['breathe0'] + (frame // 3 + i) % 4, WHO[i], FLIP[i])
        im.alpha_composite(f, (s[i][0] - 12, s[i][1] - 31 + (dy or {}).get(i, 0)))
    for i in (1, 3):
        if i not in out and i not in skip:
            chip(im, '1P' if WHO[i] == 'p1' else '2P', WHO[i], s[i][0] - 4, s[i][1] + 6)


def tags(im, layout, carrier, frame, out=()):
    s = LAYOUT[layout]['seats']
    for n, letter in enumerate('ABC'):
        t = (carrier + 1 + n) % 4
        if t not in out:
            tag(im, letter, s[t][0], s[t][1] - 47 - ((frame // 4 + n) % 2))


def scene(layout, carrier=3, frame=0, level=6, cue='calm'):
    im = field(layout)
    birds(im, layout, frame)
    put_gum(im, level, frame % 6, cue, *hold(layout, carrier))
    tags(im, layout, carrier, frame)
    return im


# ---- outputs -------------------------------------------------------------------------------------------------
def big(im, k=3):
    return im.resize((im.width * k, im.height * k), Image.NEAREST)


def save_gif(frames, name, ms):
    fr = [big(f).convert('RGB').quantize(colors=255, dither=Image.Dither.NONE) for f in frames]
    fr[0].save(os.path.join(HERE, name), save_all=True, append_images=fr[1:], duration=ms, loop=0, disposal=1)


def toss(layout='ellipse', src=3, dst=1):
    """Hold with tags, B pressed, arc to the bird across, catch, new tags."""
    frames, ms = [], []
    (x0, y0), (x1, y1) = hold(layout, src), hold(layout, dst)
    sx0, sx1 = LAYOUT[layout]['seats'][src], LAYOUT[layout]['seats'][dst]
    _, dark = ground(LAYOUT[layout]['top'])
    for f in range(6):
        frames.append(scene(layout, src, f)); ms.append(90)
    N = 14
    vy = -(4 * 52) / N                            # ballistic: constant x speed, gravity pulls the gum down (peak 52 px)
    g = -2 * vy / N
    for k in range(N + 1):
        f = 6 + k
        im = field(layout)
        gx = x0 + (x1 - x0) * k / N
        gy = y0 + (y1 - y0) * k / N + vy * k + 0.5 * g * k * k
        fx, fy = sx0[0] + (sx1[0] - sx0[0]) * k / N, sx0[1] + (sx1[1] - sx0[1]) * k / N
        stamp(im, ["s.s.s.", ".s.s.s"], {'s': dark}, round(fx) - 3, round(fy) - 1)      # gum shadow runs along the grass
        birds(im, layout, f, dy={src: -2 if k < 2 else 0, dst: 2 if k == N else 0})
        put_gum(im, 6, f % 6, 'calm', gx, gy)
        frames.append(im); ms.append(50)
    for f in range(8):
        frames.append(scene(layout, dst, 21 + f)); ms.append(90)
    save_gif(frames, 'toss_arc_3x.gif', ms)
    strip = Image.new('RGB', (320 * 4, 224))
    for n, k in enumerate((5, 10, 15, 22)):
        strip.paste(frames[k].convert('RGB'), (320 * n, 0))
    strip.save(os.path.join(HERE, 'toss_arc_keys_1x.png'))
    return len(frames)


FUSE = {   # per frame: (gum level, cue palette, shake x, strain tick set or None)
    'calm':    [(6, 'calm', 0, None)] * 6,
    'swell':   [(7, 'calm', 0, None), (8, 'warm', 0, None), (9, 'calm', 0, None), (10, 'warm', 0, None), (11, 'calm', 0, None), (12, 'warm', 0, None)],
    'frantic': [(13, 'hot', 1, 0), (13, 'warm', -1, None), (14, 'hot', 1, 1), (14, 'flash', -1, None), (15, 'hot', 1, 0), (16, 'flash', -1, 1)],
}

def fuse_cell(stage, k, w=48, h=72):
    lvl, cue, sh, tk = FUSE[stage][k]
    im = Image.new('RGBA', (w, h), snap((41, 99, 49)) + (255,))
    im.alpha_composite(bird(CLIP['breathe0'] + k % 4, 'p1'), (w // 2 - 12, h - 34 + (1 if stage == 'frantic' and k % 2 else 0)))
    kx, ky = w // 2 + sh, h - 3 - 20
    put_gum(im, lvl, k, cue, kx, ky)
    if tk is not None:
        b = gum('level%d' % lvl, k).getbbox()
        for dx, dy, rows in TICKS[tk]:
            stamp(im, rows, GC, kx + dx * (b[2] - b[0]) // 26, ky - (b[3] - b[1]) // 2 + dy * (b[3] - b[1]) // 30)
    return im

def fuse():
    sheet = Image.new('RGBA', (48 * 6 + 5, 72 * 3 + 2), (20, 22, 26, 255))
    for r, stage in enumerate(FUSE):
        for k in range(6):
            sheet.alpha_composite(fuse_cell(stage, k), (49 * k, 73 * r))
    sheet.convert('RGB').save(os.path.join(HERE, 'fuse_strip_1x.png'))
    big(sheet, 4).convert('RGB').save(os.path.join(HERE, 'fuse_strip_4x.png'))
    frames, ms = [], []
    for stage, reps, t in (('calm', 3, 130), ('swell', 3, 90), ('frantic', 5, 45)):     # blink rate rises with the stage
        for _ in range(reps):
            for k in range(6):
                frames.append(big(fuse_cell(stage, k), 2)); ms.append(t)
    save_gif(frames, 'fuse_cues_6x.gif', ms)


def burst(layout='ellipse', carrier=3):
    """Frantic gum bursts on the carrier. Shreds: position + velocity in (x, depth, height), gravity, drag, one weak bounce or stick."""
    rnd = random.Random(1118)
    s = LAYOUT[layout]['seats']
    cx, fy = s[carrier]
    _, dark = ground(LAYOUT[layout]['top'])
    G, DRAG = 0.42, 0.975
    shreds = []
    for n in range(40):
        kind = ('big', 'big', 'big', 'med', 'med', 'med', 'med', 'sml', 'sml', 'dot')[n % 10]
        sp = rnd.uniform(1.6, 5.2) * (0.8 if kind == 'big' else 1.0)
        az = rnd.uniform(0, 6.283)
        import math
        shreds.append({'kind': kind, 'x': float(cx), 'd': 0.0, 'h': 32.0,
                       'vx': sp * math.cos(az), 'vd': sp * math.sin(az), 'vh': rnd.uniform(1.0, 6.5),
                       'state': 'air', 'bounced': False, 'strand': n % 7 == 0})
    bird_ = {'x': float(cx), 'h': 0.0, 'vx': -1.5 if cx < 160 else 1.5, 'vh': 5.6}
    frames, ms = [], []
    for f in range(6):                                              # last heartbeats of the fuse
        lvl, cue, sh, tk = FUSE['frantic'][f]
        im = field(layout); birds(im, layout, f, dy={carrier: f % 2})
        kx, ky = hold(layout, carrier)
        put_gum(im, lvl, f, cue, kx + sh, ky)
        for dx, dy, rows in TICKS[tk] if tk is not None else ():
            stamp(im, rows, GC, kx + dx, ky - 14 + dy)
        tags(im, layout, carrier, f)
        frames.append(im); ms.append(45)
    T = 46
    for t in range(T):
        im = field(layout)
        air = []
        for p in shreds:                                            # landed splats lie under the birds
            if p['state'] == 'air':
                p['vh'] -= G
                for k in ('vx', 'vd'):
                    p[k] *= DRAG
                p['x'] += p['vx']; p['d'] += p['vd']; p['h'] += p['vh']
                if p['h'] <= 0:
                    p['h'] = 0
                    if not p['bounced'] and p['kind'] in ('sml', 'dot') :
                        p['bounced'] = True; p['vh'] *= -0.35; p['vx'] *= 0.5; p['vd'] *= 0.5
                    else:
                        p['state'] = 'stuck'
            gx, gy = round(p['x']), round(fy + p['d'] * 0.4)
            if p['state'] == 'stuck':
                rows = SHRED[{'big': 'splat_big', 'med': 'splat_med'}.get(p['kind'], 'splat_sml')]
                if gy >= LAYOUT[layout]['top'] + 3:
                    stamp(im, rows, GC, gx - len(rows[0]) // 2, gy - len(rows) + 1)
            else:
                air.append((p, gx, gy))
        jump = {i: -3 if t in (1, 2, 3) else (-1 if t in (4, 5) else 0) for i in range(4)}      # the others flinch
        birds(im, layout, 6 + t, dy=jump, skip=(carrier,))
        # carrier: white flash, then gummed and knocked out of the ring
        if t < 2:
            im.alpha_composite(bird(CLIP['idle'], 'white', FLIP[carrier]), (cx - 12, fy - 31))
        else:
            b = bird_
            if b['h'] > 0 or b['vh'] > 0:
                b['vh'] -= G; b['x'] += b['vx']; b['h'] = max(0.0, b['h'] + b['vh'])
                fr = CLIP['fall'] + (t // 2) % 10
            else:
                b['vh'] = 0
                fr = CLIP['land0'] + min(1, (t - 28) // 3) if t < 36 else CLIP['idle']
            if t < 36 or t % 2 == 0:                                # blinks away at the end
                im.alpha_composite(bird(fr, 'gummed', FLIP[carrier]), (round(b['x']) - 12, round(fy - 31 - b['h'])))
        for p, gx, gy in air:
            y = gy - round(p['h'])
            if p['strand'] and t < 9:                               # gum strand back to the burst point, thins then snaps
                n = max(abs(gx - cx), abs(y - (fy - 32)), 1)
                for k in range(0, n, 1 if t < 5 else 2):
                    px_, py_ = round(cx + (gx - cx) * k / n), round(fy - 32 + (y - (fy - 32)) * k / n + 6 * (k / n) * (1 - k / n) * t / 3)
                    if 0 <= px_ < 320 and 0 <= py_ < 224:
                        im.putpixel((px_, py_), (GC['p'] if k % 3 else GC['l']) + (255,))
            cols = GC_HOT if t < 3 else GC
            speed = (p['vx'] ** 2 + p['vh'] ** 2) ** 0.5
            if speed > 3.2 and p['kind'] != 'dot':
                rows = SHRED['streak'] if abs(p['vh']) > 1.2 else SHRED['long']
                stamp(im, rows, cols, gx - 2, y - 2, flipx=p['vx'] < 0, flipy=p['vh'] < 0)
            else:
                rows = SHRED[p['kind']]
                stamp(im, rows, cols, gx - len(rows[0]) // 2, y - len(rows) // 2)
        if t < 2:
            stamp(im, FLASH, {'W': (255, 255, 255), 'h': CUE['hot'][GUMPAL[9]]}, cx - 7, fy - 32 - 7)
        if t < 7:
            put_gum(im, 'pop_large', t, 'hot' if t < 3 else 'calm', cx, fy - 16)
        if t < 4:                                                   # screen kick
            k = Image.new('RGBA', im.size, (0, 0, 0, 255)); k.paste(im, (0, (2, -2, 1, -1)[t])); im = k
        frames.append(im); ms.append(40 if t < T - 1 else 900)
    save_gif(frames, 'burst_3x.gif', ms)
    strip = Image.new('RGB', (160 * 4, 224))
    for n, k in enumerate((5, 6, 7, 9, 12, 17, 24, 50)):
        strip.paste(frames[k].convert('RGB').crop((0, 112, 160, 224)), (160 * (n % 4), 112 * (n // 4)))
    strip.save(os.path.join(HERE, 'burst_keys_1x.png'))
    big(strip, 2).save(os.path.join(HERE, 'burst_keys_2x.png'))
    return len(frames)


def main():
    for layout in LAYOUT:
        im = scene(layout).convert('RGB')
        assert im.size == (320, 224)
        im.save(os.path.join(HERE, 'scene_%s_1x.png' % layout)); big(im).save(os.path.join(HERE, 'scene_%s_3x.png' % layout))
    ref = Image.open(os.path.join(HERE, '..', '2026-11-18-fling-field', 'ingame_dusk_runup.png')).convert('RGB')
    cmp_ = Image.new('RGB', (648, 224), (20, 22, 26)); cmp_.paste(ref, (0, 0)); cmp_.paste(scene('ellipse').convert('RGB'), (328, 0))
    big(cmp_, 2).save(os.path.join(HERE, 'cmp_ingame_vs_toss_2x.png'))
    pal = Image.new('RGBA', (4 * 40, 40), (20, 22, 26, 255))
    for n, w in enumerate(('p1', 'p2', 'cpu1', 'cpu2')):
        pal.alpha_composite(bird(CLIP['idle'], w), (40 * n + 8, 4))
    big(pal, 4).convert('RGB').save(os.path.join(HERE, 'birds_palettes_4x.png'))
    n1 = toss(); fuse(); n2 = burst()
    print('toss frames', n1, 'burst frames', n2)
    for f in sorted(os.listdir(HERE)):
        print('%8d %s' % (os.path.getsize(os.path.join(HERE, f)), f))


if __name__ == '__main__':
    main()
