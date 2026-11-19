#!/usr/bin/env python3.14 -I
"""Toss Gum round 2 (2026-11-18): side-view throw and catch poses, hand ring, backed tags, fuller burst.
Run: python3.14 -I draw_toss_poses.py   (Pillow). Reuses ../draw_toss_gum.py (sheets, palettes, field, gum, stamp).
Every pixel grid below is typed by hand. The script only assembles, mirrors, palette-maps, simulates motion and counts tiles."""
import importlib.util, math, os, random
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OLD = os.path.dirname(HERE)
spec = importlib.util.spec_from_file_location('tg', os.path.join(OLD, 'draw_toss_gum.py'))
tg = importlib.util.module_from_spec(spec); spec.loader.exec_module(tg)
stamp, big, PAL, K = tg.stamp, tg.big, tg.PAL, tg.K
SEATS = tg.LAYOUT['ellipse']['seats']            # back, right, front, left (feet points)
TOP = 160
WHO, FLIP = tg.WHO, tg.FLIP
CH = 'KabcdeXYZ12345W'                            # sheet palette order: outline, body 5, beak/wing 3, gum 5, white

# ---- bird poses: 32 x 32 hand grids, feet centre at column 15/16, bird faces right ------------------------------
TAIL = [
    ".........KbbbabbaaaaaaK.........",
    "..........KbbabaaaaaaK..........",
    "...........KKaaaaaaKK...........",
    ".............KKKKKK.............",
    ".............X....X.............",
    "............YYZ..YYZ............",
]
SQUASH_TAIL = [                                    # wide low body, front foot lifted
    ".......KccbbbbbabbaaaaaYXK......",
    "........KcbbbabbaaaaaaaKK.......",
    ".........KbbabaaaaaaaaK.........",
    "..........KKKaaaaaaKKK..........",
    ".............KKKKKK.............",
    ".............X....YYZ...........",
    "............YYZ.................",
]
POSE = {
    # name: (first row, rows, wing-tip anchor for the gum knot or None)
    'throw0': (9, [                                # windup A = carry pose: wing straight up at the back
        "..KK............................",
        ".KZZK...........................",
        ".KZYK.....KKK...................",
        ".KZYYK...KeedKK.................",
        "..KYYK....KKeedK................",
        "..KZYXK.....KeedKKK.............",
        "...KYXK....KKeeeddcKK...........",
        "...KYXXK..KeeeeedddccK..........",
        "....KYXK.KeeeedddddcccK.........",
        "....KYXXKKeeedddbbcbbcK.........",
        ".....KYXKdeddcbbWWcbWWaK........",
        ".....KXXKdddccbWWKcWWKaK........",
        "......KKKdccccbWWKcWWKaK........",
        "........KcccccbbeecbeeKK..5.....",
        "........KcccbbbbbbbbaaZZY34.....",
        "........KccbbbbbbabbaaYXK2......",
        "........KcbbbbbabbaaaaKK........",
    ] + TAIL, (3, 10)),
    'throw1': (11, [                               # windup B: squash, lean back, wing cocked far back, front foot up
        "..........KK....................",
        ".........KedK...................",
        "..........KeedK.................",
        "...........KeedK................",
        "............KeedKKK.............",
        "..........KKKeeeddccKK..........",
        ".KK......KeeeeeeddddccK.........",
        "KZZKK...KeeeeedddddccccK........",
        "KZYYZKKKdeeeddddddcccccaK.......",
        ".KYYYYZKKeddcbbbbbcbbaaaK.......",
        "..KKXYYYYKKccbbWWKcWWKbaK.......",
        "....KKXXYXXKcbbWWKcWWKbaK..5....",
        "......KKXXXKbbbbeecbeeaKK.34....",
        ".......KKKKbbbbbbbabbaaZZY2.....",
    ] + SQUASH_TAIL, (1, 18)),
    'throw2': (5, [                                # release A: stretch and lunge, wing whipped up and forward, back foot off
        "................KK..............",
        "...............KZZK.............",
        "...............KZYK.............",
        "..............KZYYK.............",
        "..............KZYXK.............",
        ".............KZYYK..............",
        ".............KZYXK..............",
        "......KKKK..KZYYXK..............",
        ".....KeedKKKKYYXK...............",
        "......KKKedKZYYXKeddcKK.........",
        ".........KKKYYXXKedddccK........",
        "..........KYYXXKdddddcccK.......",
        "..........KYXXKdddbbcbbcK.......",
        "..........KXXKcbbWWcbWWaK.......",
        "..........KKKccbWWKcWWKaK.......",
        "..........KdcccbWWKcWWKaK.......",
        "..........KccccbWWKcWWKaK.......",
        "..........KccccbbeecbeeKK..5....",
        "..........KccbbbbbbbbaaZZY34....",
        "..........KcbbbbbbabbaaYXK2.....",
        "..........KcbbbbabbaaaaKK.......",
        "..........KbbbabbaaaaaaK........",
        "...........KbbabaaaaaaK.........",
        "............KKaaaaaaKK..........",
        "..............KKKKKK............",
        "...........YYZ.....X............",
        "..................YYZ...........",
    ], (17, 5)),
    'throw3': (11, [                               # release B: follow through, wing flat and forward over the head
        "...............KKKKKKK..........",
        "..........KKK.KZZZYYZZKKK.......",
        ".........KeedKKYYYYYYYYZZKK.....",
        "..........KKedKKKKKXXXYYYYZK....",
        ".............KKeeedKKKKXXXYK....",
        "............KeeeeedddccKKKK.....",
        "...........KeeeedddddcccK.......",
        "...........KeeedddbbcbbcK.......",
        "..........KdeddcbbWWcbWWaK......",
        "..........KdddccbWWKcWWKaK......",
        "..........KdccccbWWKcWWKaK......",
        "..........KcccccbbeecbeeKK..5...",
        "..........KcccbbbbbbbbaaZZY34...",
        "..........KccbbbbbbabbaaYXK2....",
        ".........KcbbbbbabbaaaaKK.......",
        "..........KbbbabbaaaaaaK........",
        "...........KbbabaaaaaaK.........",
        "............KKaaaaaaKK..........",
        "..............KKKKKK............",
        "..............X....X............",
        ".............YZ...YYZ...........",
    ], None),
    'catch0': (8, [                                # reach A: eyes up, wing up and forward
        ".............KK.................",
        "............KZZK................",
        "............KZYK................",
        "...........KZYYK................",
        ".......KKK.KZYXK................",
        "......KeedKKYYXK................",
        ".......KKeKZYYXK................",
        ".........KKYYXXKddcKK...........",
        ".........KYYXXKedddccK..........",
        ".........KYXXKdddddcccK.........",
        "........KYXXKdddbbcbbcK.........",
        "........KXXKdcbbWKcbWKaK........",
        "........KKKdccbWWKcWWKaK........",
        "........KdccccbWWWcWWWaK........",
        "........KcccccbbeecbeeKK..5.....",
        "........KcccbbbbbbbbaaZZY34.....",
        "........KccbbbbbbabbaaYXK2......",
        "........KcbbbbbabbaaaaKK........",
    ] + TAIL, (14, 8)),
    'catch1': (4, [                                # reach B: full stretch, wing at its highest
        "..............KK................",
        ".............KZZK...............",
        ".............KZYK...............",
        ".............KZYK...............",
        "............KZYYK...............",
        "............KZYXK...............",
        "............KZYXK...............",
        "...........KZYYXK...............",
        "......KKK..KYYXK................",
        ".....KeedK.KYYXK................",
        "......KKedKZYYXKeddcKK..........",
        "........KKKYYXXKedddccK.........",
        ".........KYYXXKdddddcccK........",
        ".........KYXXKdddbbcbbcK........",
        ".........KXXKcbbWKcbWKaK........",
        ".........KKKccbWWKcWWKaK........",
        ".........KdcccbWWKcWWKaK........",
        ".........KccccbWWWcWWWaK........",
        ".........KccccbbeecbeeKK..5.....",
        ".........KccbbbbbbbbaaZZY34.....",
        ".........KcbbbbbbabbaaYXK2......",
        ".........KcbbbbabbaaaaKK........",
    ] + TAIL, (15, 4)),
    'catch2': (13, [                               # absorb: hard squash, wing folded over the head under the gum, eyes shut
        "..........KKKKKKK...............",
        "........KKZZZYYZZKK.............",
        ".......KZYYYYYYYYYZK............",
        "......KZYYXXXXXXXXYK............",
        "......KYXXKKKKKKKKKKKKK.........",
        "......KXKeeeeedddddccccK........",
        "......KKdeeeddddddcccccaK.......",
        "........KeddcbbbbbcbbaaaK.......",
        "........KccccbbbbbcbbbbaK.......",
        "........KccccbbKKKcKKKbaK..5....",
        "........KccbbbbbeecbeeaKK.34....",
        "........KcbbbbbbbbabbaaZZY2.....",
        ".......KccbbbbbabbaaaaaYXK......",
        "........KcbbbabbaaaaaaaKK.......",
        ".........KbbabaaaaaaaaK.........",
        "..........KKKaaaaaaKKK..........",
        ".............KKKKKK.............",
        ".............X....X.............",
        "............YYZ..YYZ............",
    ], (13, 13)),
    'catch3': (9, [                                # recoil: pushed back, wing up with the gum, front foot up
        "....KK..........................",
        "...KZZK.........................",
        "...KZYK...KK....................",
        "...KZYYK.KedK...................",
        "....KYYK..KeedK.................",
        "....KZYXK..KeedK................",
        ".....KYXK...KeedKKK.............",
        ".....KYXXKKKKeeeddccKK..........",
        "......KYXKeeeeeeddddccK.........",
        "......KXKeeeeedddddccccK........",
        "......KKdeeeddddddcccccaK.......",
        "........KeddcbbbbbcbbaaaK.......",
        "........KccccbbWWKcWWKbaK.......",
        "........KccccbbWWKcWWKbaK..5....",
        "........KccbbbbbeecbeeaKK.34....",
        "........KcbbbbbbbbabbaaZZY2.....",
    ] + SQUASH_TAIL, (5, 10)),
}
for n, (top, rows, _) in POSE.items():            # self-check: grids are 32 x 32 and use sheet palette letters only
    assert top + len(rows) == 32, (n, top, len(rows))
    for r in rows:
        assert len(r) == 32 and set(r) <= set(CH + '.'), (n, r)

_pose = {}
def pose(name, pal, flip=False):
    k = (name, pal, flip)
    if k not in _pose:
        top, rows, _ = POSE[name]
        im = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
        stamp(im, rows, {c: PAL[pal][i] for i, c in enumerate(CH)}, 0, top)
        _pose[k] = im.transpose(Image.FLIP_LEFT_RIGHT) if flip else im
    return _pose[k]

def anchor(name, seat):                           # gum knot on the wing tip, in screen pixels
    ax, ay = POSE[name][2]
    sx, sy = SEATS[seat]
    return sx - 16 + (31 - ax if FLIP[seat] else ax), sy - 31 + ay

# ---- tag with a backing plate: white keyline, dark rim, bold 7 x 9 letter with a dark drop shadow ---------------------
TAG = [
    "..WWWWWWWWWWW..",
    ".WKKKKKKKKKKKW.",
    "WKLLLLLLLLLLFKW",
    "WKLFFFFFFFFFFKW",
    "WKFFFFFFFFFFFKW",
    "WKFFFFFFFFFFFKW",
    "WKFFFFFFFFFFFKW",
    "WKFFFFFFFFFFFKW",
    "WKFFFFFFFFFFFKW",
    "WKFFFFFFFFFFFKW",
    "WKFFFFFFFFFFDKW",
    "WKFFFFFFFFFFDKW",
    "WKFDDDDDDDDDDKW",
    ".WKKKKFFDKKKKW.",
    "..WWWWKFKWWWW..",
    ".....WKDKW.....",
    "......WKW......",
    ".......W.......",
]
LETTER = {
    'A': ["..###..", ".#####.", "##...##", "##...##", "#######", "#######", "##...##", "##...##", "##...##"],
    'B': ["######.", "##..###", "##...##", "##..##.", "######.", "##..###", "##...##", "##..###", "######."],
    'C': [".#####.", "###..##", "##.....", "##.....", "##.....", "##.....", "##.....", "###..##", ".#####."],
}
def tag(im, letter, cx, top):
    c = dict(tg.TAGCOL[letter], W=(255, 255, 255))
    stamp(im, TAG, c, cx - 7, top)
    stamp(im, LETTER[letter], {'#': K}, cx - 2, top + 4)          # drop shadow
    stamp(im, LETTER[letter], {'#': (255, 255, 255)}, cx - 3, top + 3)

def tags(im, carrier, frame, out=()):
    for n, letter in enumerate('ABC'):
        t = (carrier + 1 + n) % 4
        if t not in out:
            tag(im, letter, SEATS[t][0], SEATS[t][1] - 41 - ((frame // 4 + n) % 2))

# ---- chalk ring, hand-placed: one quadrant typed as row runs (dy from the top, first x, last x), mirrored four ways ---
RING = [(0, 0, 22), (1, 23, 36), (2, 37, 46), (3, 47, 54), (4, 55, 60), (5, 61, 66), (6, 67, 71), (7, 72, 75), (8, 76, 79),
        (9, 80, 82), (10, 83, 85), (11, 86, 88), (12, 89, 90), (13, 91, 92), (14, 93, 94), (15, 95, 96), (16, 97, 97),
        (17, 98, 98), (18, 99, 99), (19, 100, 100), (20, 100, 100), (21, 101, 101), (22, 101, 101), (23, 102, 102), (24, 102, 102)]
WORN = {   # worn gaps, typed per quadrant so the mirror does not show: (left/right, far/near) -> skipped x offsets
    (-1, -1): {7, 8, 31, 52, 53, 70, 88}, (1, -1): {14, 40, 41, 63, 79, 80, 95},
    (-1, 1): {11, 12, 36, 58, 74, 75, 93}, (1, 1): {5, 27, 28, 49, 66, 85, 86, 97},
}
SCUFF = [(-71, -19, "w.w"), (44, -24, "ww"), (97, -8, "w"), (-99, 6, "w"), (-52, 21, "w.ww"), (63, 20, "ww.w"), (12, 25, "w")]
RCX, RCY = 160, 195

def ring(im):
    W, w = tg.CHALK['W'], tg.CHALK['w']
    def px(x, y, c):
        if 0 <= x < 320 and TOP <= y < 224:
            im.putpixel((x, y), c + (255,))
    for dy, x0, x1 in RING:
        for x in range(x0, x1 + 1):
            for sx in (-1, 1):
                if x not in WORN[(sx, -1)]:                       # far arc: one pixel, soft under-edge
                    px(RCX + sx * x, RCY - 24 + dy, W)
                    if dy < 16 and x % 2:
                        px(RCX + sx * x, RCY - 23 + dy, w)
                if x not in WORN[(sx, 1)]:                        # near arc: two pixels thick (closer to the camera) + shade row
                    px(RCX + sx * x, RCY + 24 - dy, W)
                    px(RCX + sx * x, RCY + 23 - dy, W)
                    if dy >= 12:
                        px(RCX + sx * (x - 1), RCY + 24 - dy, W)
                    if dy < 16:
                        px(RCX + sx * x, RCY + 25 - dy, w)
    for dx, dy, row in SCUFF:
        stamp(im, [row], {'w': w}, RCX + dx, RCY + dy)

_field = []
def field():
    if not _field:
        im, dark = tg.ground(TOP)
        ring(im)
        for x, y in SEATS:
            stamp(im, tg.PAD, {'W': tg.CHALK['W'], 'w': tg.CHALK['w'], 's': dark}, x - 10, y - 3)
        _field.extend((im, dark))
    return _field[0].copy(), _field[1]

# ---- burst grids ----------------------------------------------------------------------------------------------------
SHRED = {
    'big': [["..KKKK...", ".KmplmK..", "KmplhpmKK", "KdpplppmK", "KdmpppmdK", ".KdmpmdK.", "..KddmK..", "...KKK..."],
            [".KKK......", "KplmKKKK..", "KphlppmmK.", "KmplpppmdK", ".KmppmmdK.", "..KdmddK..", "...KKKK..."]],
    'med': [[".KKKK.", "KplmmK", "KphpmK", "KmpmdK", ".KKKK."],
            ["..KKK.", ".KlpmK", "KplpdK", "KmpdK.", ".KKK.."]],
    'sml': [[".ml.", "mplm", ".dm."], ["ml.", "ppm", ".d."]],
    'dot': [["p"], ["l"]],
}
STREAK = {
    'h': ["..mmpp..", "dmpplllh", "..dmmp.."],
    'd': ["....lh", "...pll", "..mpp.", ".mpp..", "dmm...", "d....."],
    'v': [".h.", "lll", "plp", "mpp", "mpm", ".m.", ".d.", ".d."],
}
SPLAT = {   # landing sequence per size: impact, settle, rest
    'big': [["l..p........p..l", ".m...lpplm....m.", "..dmpplhlppmd...", "dmpppplllppppmd.", ".ddmmppppppmmdd.", "...dd.dmmd.dd..."],
            ["....mpplm.......", ".dmpplhllppmd...", "dmppppllpppppmd.", ".ddmmmppppmmddd."],
            ["..dmpplhlppmd...", "dmmpppplpppmmdd.", ".dddmmmmmmmddd.."]],
    'med': [["m...lp...m", ".dmplhpmd.", "dmpppppmmd"], [".dmplhpmd.", "ddmmppmmdd"], [".dmplhpmd.", "ddmmppmmdd"]],
    'sml': [[".pl.", "dmmd"], [".pl.", "dmmd"], [".pl.", "dmmd"]],
}
SPLAT['dot'] = [[["m"]]] * 3
PATCH = {'big': ["..mpl..", ".mplhp.", "dmpplpm", ".dmpmd.", "..d.d.."], 'med': ["..mpl..", ".mplhp.", "dmpplpm", ".dmpmd.", "..d.d.."],
         'sml': [".pl.", "mplm", ".dm."], 'dot': ["p"]}
SHADOW = {'big': [".s.s.s.s..", "s.s.s.s.s.", ".s.s.s.s.."], 'med': [".s.s.s", "s.s.s."], 'sml': ["s.s"], 'dot': ["s"]}
BEAD = {'thick': ["pl", "mp"], 'thin': ["p"], 'hair': ["l"]}
G, DRAG = 0.42, 0.975


def birds(im, frame, poses=None, dy=None, skip=(), patches=()):
    """poses: seat -> pose name; other seats breathe (sheet frames). patches: (seat, dx, dy, kind) gum stuck on a bird."""
    for i in sorted(range(4), key=lambda i: SEATS[i][1]):
        if i in skip:
            continue
        x, y = SEATS[i]
        o = (dy or {}).get(i, 0)
        if poses and i in poses:
            im.alpha_composite(pose(poses[i], WHO[i], FLIP[i]), (x - 16, y - 31 + o))
        else:
            im.alpha_composite(tg.bird(tg.CLIP['breathe0'] + (frame // 3 + i) % 4, WHO[i], FLIP[i]), (x - 12, y - 31 + o))
        for s, px_, py_, kind in patches:
            if s == i:
                rows = PATCH[kind]
                stamp(im, rows, GC, x + px_ - len(rows[0]) // 2, y + py_ + o - len(rows) // 2)
    for i in (1, 3):
        if i not in skip:
            tg.chip(im, '1P' if WHO[i] == 'p1' else '2P', WHO[i], SEATS[i][0] - 4, SEATS[i][1] + 6)


GC = dict(tg.GC, K=K)
GC_HOT = dict(tg.GC_HOT, K=K)


def scene(carrier=3, frame=0):
    im, _ = field()
    birds(im, frame, {carrier: 'throw0'})
    tg.put_gum(im, 6, frame % 6, 'calm', *anchor('throw0', carrier))
    tags(im, carrier, frame)
    return im


def save_gif(frames, name, ms, k=3):
    fr = [big(f, k).convert('RGB').quantize(colors=255, dither=Image.Dither.NONE) for f in frames]
    fr[0].save(os.path.join(HERE, name), save_all=True, append_images=fr[1:], duration=ms, loop=0, disposal=1)


def toss(src=3, dst=1):
    """Carry, windup, release, ballistic flight, reach, absorb, recoil, new carrier."""
    frames, ms = [], []
    _, dark = field()
    def add(f, poses, gum_at, tag_for, t, dy=None, shadow=None):
        im, _ = field()
        if shadow:
            stamp(im, SHADOW['med'], {'s': dark}, round(shadow[0]) - 3, round(shadow[1]) - 1)
        birds(im, f, poses, dy)
        if gum_at:
            tg.put_gum(im, 6, f % 6, 'calm', *gum_at)
        if tag_for is not None:
            tags(im, tag_for, f)
        frames.append(im); ms.append(t)
    f = 0
    for _ in range(6):
        add(f, {src: 'throw0'}, anchor('throw0', src), src, 90); f += 1
    for _ in range(3):
        add(f, {src: 'throw1'}, anchor('throw1', src), src, 60); f += 1
    add(f, {src: 'throw2'}, anchor('throw2', src), None, 50); f += 1
    (x0, y0), (x1, y1) = anchor('throw2', src), anchor('catch1', dst)
    N = 15
    vy = -(4 * 46) / N; g = -2 * vy / N                    # ballistic: constant side speed, gravity (peak 46 px above the chord)
    for k in range(1, N):
        gx = x0 + (x1 - x0) * k / N
        gy = y0 + (y1 - y0) * k / N + vy * k + 0.5 * g * k * k
        sh = (SEATS[src][0] + (SEATS[dst][0] - SEATS[src][0]) * k / N, SEATS[src][1] + (SEATS[dst][1] - SEATS[src][1]) * k / N)
        p = {}
        if k == 1: p[src] = 'throw2'
        elif k < 6: p[src] = 'throw3'
        if k >= N - 3: p[dst] = 'catch1'
        elif k >= N - 8: p[dst] = 'catch0'
        add(f, p, (gx, gy), None, 50, shadow=sh); f += 1
    add(f, {dst: 'catch1'}, anchor('catch1', dst), None, 50); f += 1
    for k in range(3):
        add(f, {dst: 'catch2'}, anchor('catch2', dst), None, 60, dy={dst: 1 if k == 1 else 0}); f += 1
    for _ in range(3):
        add(f, {dst: 'catch3'}, anchor('catch3', dst), dst, 70); f += 1
    for _ in range(8):
        add(f, {dst: 'throw0'}, anchor('throw0', dst), dst, 90); f += 1
    save_gif(frames, 'toss_3x.gif', ms)
    keys = (5, 8, 9, 13, 20, 24, 26, 29)
    strip = Image.new('RGB', (320 * 4, 224 * 2))
    for n, k in enumerate(keys):
        strip.paste(frames[k].convert('RGB'), (320 * (n % 4), 224 * (n // 4)))
    strip.save(os.path.join(HERE, 'toss_keys_1x.png'))
    return len(frames)


def burst(carrier=3):
    """Shreds: position and speed in (x, depth, height); gravity, drag, tumble, stretch at speed, one weak bounce for small ones,
    landing splat sequence with secondary droplets, sticking to other birds, verlet gum strands that sag, thin and snap."""
    rnd = random.Random(1118)
    cx, fy = SEATS[carrier]
    kx, ky = anchor('throw0', carrier)
    bx, by = kx, ky - 12                                            # burst point = middle of the swollen gum
    h0 = fy - by
    _, dark = field()
    shreds = []
    def spawn(kind, vx, vd, vh, drag=DRAG, x=None, d=0.0, h=None, strand=False):
        shreds.append({'kind': kind, 'shape': len(shreds) % 2, 'x': float(bx if x is None else x), 'd': d, 'h': float(h0 if h is None else h),
                       'vx': vx, 'vd': vd, 'vh': vh, 'drag': drag, 'state': 'air', 'bounced': False, 'age': 0, 'spin': rnd.choice((2, 3, 4)),
                       'strand': strand, 'landed': 0})
    for n in range(36):
        kind = ('big', 'med', 'sml', 'med', 'sml', 'big', 'med', 'sml', 'dot', 'sml', 'med', 'dot')[n % 12]
        sp = rnd.uniform(1.4, 5.0) * (0.75 if kind == 'big' else 1.0)
        az = rnd.uniform(0, 2 * math.pi)
        spawn(kind, sp * math.cos(az), sp * math.sin(az), rnd.uniform(0.5, 6.5), strand=(n % 6 == 0))
    for i, T in ((0, 15), (1, 24), (2, 19)):                        # one shred aimed at each other bird (no drag: exact ballistic solve)
        if i != carrier:
            sx, sy = SEATS[i]
            spawn('med', (sx - bx) / T, ((sy - fy) / 0.4) / T, (15 - h0 + G * T * (T + 1) / 2) / T, drag=1.0)
    ropes = []
    for p in shreds:
        if p['strand']:
            ropes.append({'p': p, 'n': [[float(bx), float(by)] for _ in range(8)], 'o': [[float(bx), float(by)] for _ in range(8)], 'snap': None})
    hero = {'x': float(cx), 'h': 0.0, 'vx': -1.5 if cx < 160 else 1.5, 'vh': 5.6}
    stuck = []                                                      # (seat, dx, dy, kind)
    flinch = {}
    frames, ms = [], []
    for f in range(6):                                              # last heartbeats of the fuse
        lvl, cue, sh, tk = tg.FUSE['frantic'][f]
        im, _ = field(); birds(im, f, {carrier: 'throw0'}, dy={carrier: f % 2})
        tg.put_gum(im, lvl, f, cue, kx + sh, ky + f % 2)
        for dx, dy, rows in tg.TICKS[tk] if tk is not None else ():
            stamp(im, rows, tg.GC, kx + dx, ky - 14 + dy)
        tags(im, carrier, f)
        frames.append(im); ms.append(45)
    T = 66
    for t in range(T):
        im, _ = field()
        air = []
        for p in list(shreds):
            if p['state'] == 'air':
                p['age'] += 1
                p['vh'] -= G
                p['vx'] *= p['drag']; p['vd'] *= p['drag']
                p['x'] += p['vx']; p['d'] += p['vd']; p['h'] += p['vh']
                gx, gy = p['x'], fy + p['d'] * 0.4
                for i in range(4):                                  # hits a seated bird: sticks to it
                    sx, sy = SEATS[i]
                    if i != carrier and p['kind'] != 'dot' and abs(gx - sx) < 8 and abs(gy - sy) < 4 and 5 <= p['h'] <= 22 and p['vh'] < 0:
                        p['state'] = 'onbird'; stuck.append((i, round(gx - sx), -round(p['h']), p['kind'])); flinch[i] = t
                        break
                if p['state'] == 'air' and p['h'] <= 0:
                    p['h'] = 0
                    if not p['bounced'] and p['kind'] in ('sml', 'dot'):
                        p['bounced'] = True; p['vh'] *= -0.35; p['vx'] *= 0.5; p['vd'] *= 0.5
                    else:
                        p['state'] = 'stuck'; p['landed'] = t
                        if p['kind'] in ('big', 'med'):             # secondary droplets thrown out by the impact
                            for s in (-1, 1):
                                spawn('dot', p['vx'] * 0.3 + s * rnd.uniform(0.6, 1.6), rnd.uniform(-1, 1), rnd.uniform(1.2, 2.6), x=p['x'], d=p['d'], h=1)
                                shreds[-1]['bounced'] = True
            gx, gy = round(p['x']), round(fy + p['d'] * 0.4)
            if p['state'] == 'stuck' and gy >= TOP + 3:
                rows = SPLAT[p['kind']][min(2, (t - p['landed']) // 2)]
                stamp(im, rows, GC, gx - len(rows[0]) // 2, gy - len(rows) + 1)
            elif p['state'] == 'air':
                air.append((p, gx, gy))
        for p, gx, gy in air:                                       # shadows on the grass, smaller when the shred is high
            if gy >= TOP + 2:
                kind = p['kind'] if p['h'] < 26 else {'big': 'med', 'med': 'sml'}.get(p['kind'], 'dot')
                rows = SHADOW[kind]
                stamp(im, rows, {'s': dark}, gx - len(rows[0]) // 2, gy - len(rows) // 2)
        poses = {i: 'catch3' for i in range(4) if i != carrier and (1 <= t <= 5 or (i in flinch and 0 <= t - flinch[i] <= 4))}
        jump = {i: (-3 if t in (1, 2, 3) else (-1 if t in (4, 5) else 0)) + (1 if i in flinch and t - flinch[i] in (0, 1) else 0) for i in range(4)}
        birds(im, 6 + t, poses, dy=jump, skip=(carrier,), patches=stuck)
        if t < 2:                                                   # carrier: white flash, then gummed and knocked out of the ring
            im.alpha_composite(pose('throw0', 'white', FLIP[carrier]), (cx - 16, fy - 31))
        else:
            b = hero
            if b['h'] > 0 or b['vh'] > 0:
                b['vh'] -= G; b['x'] += b['vx']; b['h'] = max(0.0, b['h'] + b['vh'])
                fr = tg.CLIP['fall'] + (t // 2) % 10
            else:
                b['vh'] = 0
                fr = tg.CLIP['land0'] + min(1, (t - 28) // 3) if t < 36 else tg.CLIP['idle']
            if t < 52 or t % 2 == 0:
                im.alpha_composite(tg.bird(fr, 'gummed', FLIP[carrier]), (round(b['x']) - 12, round(fy - 31 - b['h'])))
        for r in ropes:                                             # verlet strand from the burst point to its shred
            p = r['p']; n, o = r['n'], r['o']
            end = (p['x'], fy + p['d'] * 0.4 - p['h'])
            if r['snap'] is None and (t >= 7 + ropes.index(r) * 2 or p['state'] != 'air'):
                r['snap'] = t
            for i in range(8):
                vx_, vy_ = (n[i][0] - o[i][0]) * 0.96, (n[i][1] - o[i][1]) * 0.96
                o[i] = n[i][:]
                n[i] = [n[i][0] + vx_, n[i][1] + vy_ + 0.28]
            rest = (math.dist((bx, by), end) / 7) if r['snap'] is None else 1.2      # stretches with the shred, recoils once snapped
            for _ in range(4):
                if r['snap'] is None:
                    n[0] = [float(bx), float(by)]; n[7] = list(end)
                for i in range(7):
                    if r['snap'] is not None and i == 3:            # the snap point: middle link is gone
                        continue
                    dx_, dy_ = n[i + 1][0] - n[i][0], n[i + 1][1] - n[i][1]
                    L = math.hypot(dx_, dy_) or 1e-6
                    k = (L - rest) / L / 2
                    n[i][0] += dx_ * k; n[i][1] += dy_ * k; n[i + 1][0] -= dx_ * k; n[i + 1][1] -= dy_ * k
            if r['snap'] is None or t - r['snap'] < 9:
                bead = BEAD['thick'] if t < 4 else (BEAD['thin'] if r['snap'] is None else BEAD['hair'])
                for i in range(7):
                    if r['snap'] is not None and i == 3:
                        continue
                    m = int(max(abs(n[i + 1][0] - n[i][0]), abs(n[i + 1][1] - n[i][1]), 1))
                    for q in range(m):
                        stamp(im, bead, GC, round(n[i][0] + (n[i + 1][0] - n[i][0]) * q / m), round(n[i][1] + (n[i + 1][1] - n[i][1]) * q / m))
        for p, gx, gy in air:
            y = gy - round(p['h'])
            cols = GC_HOT if t < 3 else GC
            speed = math.hypot(p['vx'], p['vh'])
            if speed > 3.4 and p['kind'] in ('big', 'med'):         # stretched while fast, grid picked by heading
                ang = abs(math.degrees(math.atan2(abs(p['vh']), abs(p['vx']))))
                rows = STREAK['h'] if ang < 25 else (STREAK['v'] if ang > 65 else STREAK['d'])
                stamp(im, rows, cols, gx - len(rows[0]) // 2, y - len(rows) // 2, flipx=p['vx'] < 0, flipy=p['vh'] < 0)
            else:                                                   # tumble: four orientations of the hand grid
                rows = SHRED[p['kind']][p['shape']]
                o_ = (p['age'] // p['spin']) % 4
                stamp(im, rows, cols, gx - len(rows[0]) // 2, y - len(rows) // 2, flipx=o_ in (1, 2), flipy=o_ in (2, 3))
        if t < 2:
            stamp(im, tg.FLASH, {'W': (255, 255, 255), 'h': tg.CUE['hot'][tg.GUMPAL[9]]}, bx - 7, by - 7)
        if t < 7:
            tg.put_gum(im, 'pop_large', t, 'hot' if t < 3 else 'calm', bx, by + 16)
        if t < 4:                                                   # screen kick
            k_ = Image.new('RGBA', im.size, (0, 0, 0, 255)); k_.paste(im, (0, (2, -2, 1, -1)[t])); im = k_
        frames.append(im); ms.append(40 if t < T - 1 else 900)
    save_gif(frames, 'burst_3x.gif', ms)
    strip = Image.new('RGB', (320 * 4, 224 * 2))
    for n, k in enumerate((6, 8, 11, 15, 20, 27, 36, 71)):
        strip.paste(frames[k].convert('RGB'), (320 * (n % 4), 224 * (n // 4)))
    strip.save(os.path.join(HERE, 'burst_keys_1x.png'))
    return len(frames), len(shreds), len(stuck)


# ---- pose sheets and loops ---------------------------------------------------------------------------------------------
ORDER = ['throw0', 'throw1', 'throw2', 'throw3', 'catch0', 'catch1', 'catch2', 'catch3']
BG = tg.snap((41, 99, 49))

def sheet():
    rows = (('p1', False), ('p2', True), ('cpu1', False), ('cpu2', True))
    sh = Image.new('RGBA', (33 * 9 - 1, 33 * 4 - 1), (20, 22, 26, 255))
    for r, (pal, flip) in enumerate(rows):
        cell = Image.new('RGBA', (32, 32), BG + (255,)); cell.alpha_composite(tg.bird(tg.CLIP['idle'], pal, flip), (4, 0))
        sh.alpha_composite(cell, (0, 33 * r))                      # column 0: the game's idle frame, for comparison
        for n, name in enumerate(ORDER):
            cell = Image.new('RGBA', (32, 32), BG + (255,)); cell.alpha_composite(pose(name, pal, flip))
            sh.alpha_composite(cell, (33 * (n + 1), 33 * r))
    sh.convert('RGB').save(os.path.join(HERE, 'poses_sheet_1x.png'))
    big(sh, 4).convert('RGB').save(os.path.join(HERE, 'poses_sheet_4x.png'))


def loops():
    """Throw and catch on their own, 1P facing right beside 2P mirrored."""
    def cell(name, pal, flip, k, gum=None):
        im = Image.new('RGBA', (72, 64), BG + (255,))
        if name:
            im.alpha_composite(pose(name, pal, flip), (20, 30))
            a = POSE[name][2]
        else:
            im.alpha_composite(tg.bird(tg.CLIP['breathe0'] + k % 4, pal, flip), (24, 30)); a = None
        if gum == 'hold' and a:
            tg.put_gum(im, 6, k % 6, 'calm', 20 + (31 - a[0] if flip else a[0]), 30 + a[1])
        elif gum:
            tg.put_gum(im, 6, k % 6, 'calm', *gum)
        return im
    def pair(name, k, gum1, gum2):
        im = Image.new('RGBA', (146, 64), (20, 22, 26, 255))
        im.alpha_composite(cell(name, 'p1', False, k, gum1), (0, 0)); im.alpha_composite(cell(name, 'p2', True, k, gum2), (74, 0))
        return im
    seq = [('throw0', 'hold', 90)] * 4 + [('throw1', 'hold', 60)] * 3 + [('throw2', 'hold', 50)]
    fl = [(45, 24), (56, 16), (68, 12)]                              # gum leaving the frame after release
    seq += [('throw2', fl[0], 50), ('throw3', fl[1], 50), ('throw3', fl[2], 50), ('throw3', None, 50), (None, None, 90), (None, None, 90), (None, None, 90)]
    fr, ms = [], []
    for k, (name, gum, t) in enumerate(seq):
        g2 = (71 - gum[0], gum[1]) if isinstance(gum, tuple) else gum
        fr.append(pair(name, k, gum, g2)); ms.append(t)
    save_gif(fr, 'throw_3x.gif', ms)
    inn = [(70, 6), (60, 4), (50, 5), (42, 8), (37, 4 + 30 - 21)]   # gum arriving
    seq = [(None, None, 90), (None, inn[0], 50), ('catch0', inn[1], 50), ('catch0', inn[2], 50), ('catch1', inn[3], 50), ('catch1', 'hold', 50)]
    seq += [('catch2', 'hold', 60)] * 3 + [('catch3', 'hold', 70)] * 3 + [('throw0', 'hold', 90)] * 5
    fr2, ms2 = [], []
    for k, (name, gum, t) in enumerate(seq):
        g2 = (71 - gum[0], gum[1]) if isinstance(gum, tuple) else gum
        fr2.append(pair(name, k, gum, g2)); ms2.append(t)
    save_gif(fr2, 'catch_3x.gif', ms2)
    return len(fr), len(fr2)


# ---- tile budget: 16 x 16 tiles, empty ones skipped, duplicates and mirrored duplicates counted once ---------------------
def tiles(im, seen):
    n = 0
    for y in range(0, im.height, 16):
        for x in range(0, im.width, 16):
            t = im.crop((x, y, x + 16, y + 16))
            if t.getbbox() is None:
                continue
            n += 1
            keys = {v.tobytes() for v in (t, t.transpose(Image.FLIP_LEFT_RIGHT), t.transpose(Image.FLIP_TOP_BOTTOM), t.transpose(Image.ROTATE_180))}
            if not keys & seen:
                seen.add(t.tobytes())
    return n

def grid_img(rows, cols, w=16, h=16):
    im = Image.new('RGBA', (-(-len(rows[0]) // w) * w, -(-len(rows) // h) * h), (0, 0, 0, 0))
    stamp(im, rows, cols, 0, 0)
    return im

def budget():
    out = []
    def line(name, items):
        seen = set(); n = sum(tiles(i, seen) for i in items)
        out.append((name, n, len(seen)))
    line('bird poses, 8 frames (32 x 32 cells)', [pose(n, 'p1') for n in ORDER])
    anyc = {c: (1, 2, 3) for c in 'KLFDW#dmplhsw'}
    tagims = []
    for l in 'ABC':
        im = Image.new('RGBA', (16, 32), (0, 0, 0, 0)); tag(im, l, 7, 0); tagims.append(im)
    line('tags A B C (16 x 32 cells)', tagims)
    r = Image.new('RGBA', (320, 224), (0, 0, 0, 0)); ring(r)
    line('chalk ring (on the 16 px screen grid)', [r])
    line('seat pad + 1P/2P chips', [grid_img(tg.PAD, anyc, 32, 16), grid_img(tg.CHIP['1'] + tg.CHIP['P'], anyc), grid_img(tg.CHIP['2'] + tg.CHIP['P'], anyc)])
    line('shreds, streaks, beads', [grid_img(g, GC) for v in SHRED.values() for g in v] + [grid_img(g, GC) for g in STREAK.values()] + [grid_img(g, GC) for g in BEAD.values()])
    line('splats, patches', [grid_img(g, GC) for k in ('big', 'med', 'sml') for g in SPLAT[k]] + [grid_img(PATCH[k], GC) for k in ('big', 'sml')])
    line('shadows, flash', [grid_img(g, {'s': (1, 1, 1)}) for g in SHADOW.values()] + [grid_img(tg.FLASH, {'W': (9, 9, 9), 'h': (5, 5, 5)})])
    return out


def main():
    im = scene().convert('RGB'); assert im.size == (320, 224)
    im.save(os.path.join(HERE, 'scene_1x.png')); big(im).save(os.path.join(HERE, 'scene_3x.png'))
    ref = Image.open(os.path.join(OLD, '..', '2026-11-18-fling-field', 'ingame_dusk_runup.png')).convert('RGB')
    c = Image.new('RGB', (648, 224), (20, 22, 26)); c.paste(ref, (0, 0)); c.paste(im, (328, 0))
    big(c, 2).save(os.path.join(HERE, 'cmp_ingame_vs_toss_2x.png'))
    # tags: old against new over the same city crop (back bird, right bird)
    old = tg.field('ellipse'); new, _ = field()
    for n, l in enumerate('ABC'):
        t = (3 + 1 + n) % 4
        tg.tag(old, l, SEATS[t][0], SEATS[t][1] - 47); tag(new, l, SEATS[t][0], SEATS[t][1] - 41)
    box = (96, 112, 296, 200)
    c = Image.new('RGB', (404, 88), (20, 22, 26)); c.paste(old.convert('RGB').crop(box), (0, 0)); c.paste(new.convert('RGB').crop(box), (204, 0))
    c.save(os.path.join(HERE, 'cmp_tags_1x.png')); big(c, 4).save(os.path.join(HERE, 'cmp_tags_4x.png'))
    # ring: old computed against new hand-placed
    c = Image.new('RGB', (320, 2 * 64 + 4), (20, 22, 26))
    c.paste(tg.field('ellipse').convert('RGB').crop((0, 160, 320, 224)), (0, 0)); c.paste(field()[0].convert('RGB').crop((0, 160, 320, 224)), (0, 68))
    big(c, 3).save(os.path.join(HERE, 'cmp_ring_3x.png'))
    sheet()
    n_throw, n_catch = loops()
    n_toss = toss()
    n_burst, n_shreds, n_stuck = burst()
    lines = ['throw loop frames %d (4 poses)' % n_throw, 'catch loop frames %d (4 poses)' % n_catch, 'toss frames %d' % n_toss,
             'burst frames %d, shreds incl. droplets %d, stuck on birds %d' % (n_burst, n_shreds, n_stuck), 'tile budget (16 x 16): name, non-empty tiles, unique after mirror dedupe']
    tot = 0
    for name, n, u in budget():
        lines.append('  %-42s %3d %3d' % (name, n, u)); tot += u
    lines.append('  %-42s     %3d' % ('total new unique tiles', tot))
    open(os.path.join(HERE, 'numbers.txt'), 'w').write('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
