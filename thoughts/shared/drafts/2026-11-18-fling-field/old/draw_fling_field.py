#!/usr/bin/env python3.14 -I
"""Gum Fling throwing field, art draft 2026-11-18 (not game code).

Every tile below is a hand-placed pixel grid (one character = one pixel, spaces are only visual separators).
Nothing is generated: the script only stamps the grids, swaps palettes per mood and builds the mock-ups.

Floor height: turf top = screen y 160, 4 tile rows (160..223). Source: the first Gum Trip chunk has gap
TRIP_GAP_START 144, win_top = ((180 - 144) / 2) & ~15 = 16, win_bottom = 160 (src/core/trip_gen.c), and a flat floor
column is drawn from that edge to TRIP_VIEW_STRIP_BOTTOM 224 = 4 rows of 16 (trip_view_strip_column). A flat field
keeps that one edge for the whole run-up, flight and landing.

Run: python3.14 -I draw_fling_field.py
"""
import os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
BG = os.path.join(REPO, 'thoughts', 'shared', 'drafts', '2026-11-10-backgrounds-final')
BIRD = os.path.join(REPO, '.claude', 'worktrees', 'gum-games', 'assets', 'flier', 'sootling_sheet.png')
FLOOR_Y = 160
PX_PER_M = 3          # GF_PX_PER_M
MARK_M = 50           # GF_MARK_PX 150
MOODS = ('dusk', 'moon', 'storm')


def snap(c):          # Neo Geo 5 bits per channel
    return tuple((v >> 3 << 3) | (v >> 5) for v in c)


# ---- palettes: 15 colours + transparent each, picked by hand per mood (hue shifts from blue-green shadow to yellow tip)
TURF = {
    #          k deep        e dark sh     f dark base   g dark hi      a light sh    b light base   c light hi      d tip
    'dusk':  dict(k=(16, 40, 56), e=(16, 64, 64), f=(24, 96, 56), g=(64, 136, 48), a=(32, 112, 56), b=(80, 160, 48), c=(144, 200, 56),
                  d=(216, 232, 96), h=(255, 208, 120), s=(72, 40, 40), t=(136, 88, 56), u=(200, 152, 96), w=(248, 232, 192),
                  m=(48, 128, 56), y=(248, 176, 56)),
    'moon':  dict(k=(8, 24, 64), e=(8, 48, 80), f=(16, 80, 88), g=(40, 120, 104), a=(24, 96, 96), b=(48, 136, 96), c=(104, 184, 128),
                  d=(168, 224, 168), h=(216, 248, 248), s=(40, 32, 64), t=(88, 72, 96), u=(144, 128, 144), w=(216, 224, 240),
                  m=(32, 112, 96), y=(200, 208, 128)),
    'storm': dict(k=(16, 32, 48), e=(24, 56, 64), f=(40, 88, 64), g=(72, 120, 72), a=(48, 104, 72), b=(88, 136, 72), c=(136, 176, 96),
                  d=(192, 216, 144), h=(232, 240, 224), s=(56, 40, 48), t=(104, 80, 72), u=(160, 136, 112), w=(224, 224, 216),
                  m=(64, 112, 72), y=(216, 192, 96)),
}
# chalk, boards, poles: one palette for all moods (the field furniture is floodlit)
GEAR = dict(W=(248, 248, 248), L=(208, 216, 232), M=(152, 168, 192), D=(88, 104, 136), K=(24, 24, 40), N=(32, 48, 104),
            n=(64, 88, 160), Y=(248, 208, 56), O=(232, 136, 32), R=(224, 48, 48), r=(144, 24, 48), T=(120, 72, 40),
            U=(184, 128, 72), G=(192, 224, 168), C=(255, 240, 176))


def grid(rows, w):
    out = [r.replace(' ', '') for r in rows]
    for i, r in enumerate(out):
        assert len(r) == w, 'row %d is %d wide, not %d: %s' % (i, len(r), w, r)
    return out


# ---- turf: 32 px period x 64 px (2 x 4 tiles). Mown bands run along the throw lane and get taller toward the viewer.
TURF_ROWS = grid([
    "..c..h.. d..c.... .d..c..d ..h..c.d",   # 160: blade tips against the sky
    "d.cd.dc. dc.cd.d. cd.dc.dd .cd.dcdd",
    "dcdcddcd ccdcdcdd dccdcdcd cddcdcdc",
    "cbccdcbc cdcbccdc bcdccbcc dcbccdcb",   # far light band
    "bcbbcbbc bbcbbabc bbbcbbcb bcbbabbc",
    "bbabbbcb bcbbbbbb abbcbbbb cbbbbcbb",
    "bmbbbbab bbmbbbbb bmbbabbb bbbbmbbb",
    "mbmbbmbm bmbmbbmb mbbmbmbm bmbmbbmb",
    "fmfmffmf mfmffmfm ffmfmfmf mffmfmfm",   # dark band
    "ffgfffff effffgff fffeffff ffgfffef",
    "fefffgff fffeffff gfffffef ffffgfff",
    "ffmfffef ffgfmfff ffmfffgf fmfffeff",
    "mfmffmfm fmfmmfmf mffmfmfm fmfmfmmf",
    "bmbmbbmb mbbmbmbb bmbmbbmb bbmbmbbm",   # light band
    "bcbbbabb bdcbbbbb bbabbcdb bbbbabbb",
    "bbbbadbb bbcabbbc bbbbbdab bcbbbbba",
    "cbbbbabc bbbbbbad bbcbbbab bbdcbbbb",
    "dabbbbbb bcbbbbba bbbbcbbb bbbabbbc",
    "babbmbbb bbbmbbbb bmbbbbbb mbbbbbmb",
    "mbmbmbmb mbmbbmbm bmmbmbbm bmbmbmbb",
    "fmffmfmf mfmfmffm fmfmffmf mfmffmfm",   # dark band
    "ffffefff gfffffef fffgffff effffgff",
    "fgfffeff fgffffff effffgfe ffffffgf",
    "fgeffffg feffffff ffefffge fffgffff",
    "ffeffffg efffgfff ffffffff efffgeff",
    "efffffff effffgef fffgffff fffffeff",
    "ffmfffef ffffmfff fefmffff ffmffffm",
    "mfmfmffm fmffmfmf mfmfmffm fmfmffmf",
    "bmbbmbmb mbmbbmbm bbmbmbmb bmbmbbmb",   # light band
    "bbbbbbcb bbbbbbbb cbbbbbbb bbbcbbbb",
    "bcbbbdcb bbabbbbd cbbbabbb bbdcbbba",
    "bdcbbadb bbbbcbad abbbbbcb bbadbbbb",
    "badabbab bbcdbbba bbbdcbbb bbbabbcb",
    "bbabbbbb bbadabbb bbbadabb cbbbbbdc",
    "cbbbbcbb bbbabbbb bbbbabbb dcbbbbad",
    "dcbbbbbb abbbbbcb bbbbbbba adabbbba",
    "adbbmbbb bbmbbbbb bmbbbbbb babmbbbb",
    "bambmbmb mbmbmbmb mbmbbmbm bmbmbmbm",
    "fmfmfmff mfmffmfm fmfmfmff mfmfmffm",   # dark band
    "ffffffgf ffefffff fffgffff ffffefff",
    "feffffgf fffffgff ffegffff gfffffef",
    "ffeffgge ffffggef fffggeff ggefffff",
    "fffefgek fefffgek ffffgeke fgekffff",
    "ffffeeef fffffeek fefffekf feekffef",
    "gfffffef fffgffff fffffeff ffffffgf",
    "ggefffff fefggeff ffgfffff fefffgge",
    "fgekffff fffgekff fggeffef ffffffge",
    "feefmfff fmffeeff mfgekfmf ffmfffee",
    "mfmffmfm fmfmfmmf mfmeemfm fmfmfmfm",
    "bmbmbbmb mbmbmbbm bmbbmbmb mbbmbmbm",   # near light band: big tufts
    "bbbbcbbb bbbbbbcb bbbbbbbb cbbbbbbb",
    "bcbbdcbb bbabbbdc bbbbcbbb dcbbabbb",
    "bdcbddab bbbbcbdd abbbdcbb ddabbbbc",
    "bddabdab bcbbdcad abbbddab adabbbbd",
    "hadabdab bdcbddaa bbcbadab aabbcbbd",
    "dadabaab bddabdab bbdcbaab bbbbdcba",
    "daabbabb hadabdab bbddabbb bcbbddab",
    "aabbbbbc dadabaab bbadabbb bdcbadab",
    "abbcbbbd aaabbabb cbbaabbb bddabaab",
    "bbbdcbba abbbbbbb dcbbbbbc badabbab",
    "abbaddab bbabbbab ddabbbbd caaabbbb",
    "aabbadab abbmabba adabbabb daabmabb",
    "maamaaab aamaamaa maaamaaa mamaaama",
    "emeamema emaeamae ameaemam eameamea",   # 223: screen edge
], 32)

# ---- landing puff: 5 frames of 32 x 16 (2 tiles each), turf palette; bottom row sits 3 px into the turf (y 163)
E = "................................"
PUFF = [grid(f, 32) for f in ([
    E, E, E, E, E, E, E, E, E,
    "..............d................."
    , ".............d..c..d............",
    "............uwwuuwu.............",
    "..........tuuwwwwuuut...........",
    ".........tuuwuuuwuuttt..........",
    ".........stuuuuuuuttts..........",
    "..........sstttttttss...........",
], [
    E, E, E, E,
    "...........g.........d..........",
    "..........gfk..................."
    , "...........ek...c....gf.........",
    "....................fek.........",
    ".......uwwu..............uu.....",
    ".....uwwwuuu...........uwwwu....",
    "....uwwuuuutt...d.....uwwuuut...",
    "....uwuuuutttt.......tuwuuuut...",
    "...tuuuuuttts..uwwu..tuuuuutts..",
    "...tuuuuttts..uwuuut.stuuuttts..",
    "...sttuttss..tuuuutts.sttuttss..",
    "....sstttss..sstttss...ssttss...",
], [
    "............g...................",
    "...........gfk.......d..........",
    "............ek..........gf......",
    "......c................gfek.....",
    "....................c...ek......",
    "...uwwu....................uwu..",
    "..uwwwuu..d..............uwwwuu.",
    ".uwwuuuut................uwwuuut",
    ".uwuuu.utt.....uwu......tuwu.uut",
    "tuwuuutuut....uwwuu.....tuuuuutt",
    "tuuu.uuttt...tuw.uut....tuu.uutt",
    ".tuuuut.ts...tuuuutt.....tutuutt",
    ".tt.uttts.....tu.tts.....st.utts",
    "..sttt.s.......ttts.......sttts.",
    "...st.ss........sts........st.s.",
    "....s.s..........s..........s...",
], [
    E, E, E,
    "..u.w....................u.w....",
    ".u.w.u..................u.w.u...",
    "u.w.u.u..........g.......u.u.u..",
    ".u.u.u.t........gfk.....u.u.u.t.",
    "u.u.u.t..........ek......t.u.t..",
    ".t.u.t.t....c...........t.u.t.t.",
    "t.u.t.t.........u.u......t.t.t..",
    ".t.t.t.s.......u.t.t....s.t.t.s.",
    "..s.t.s.........t.t......t.s.s..",
    ".s.s.s...........s.s......s.s...",
    "..s.s...........................",
    "......................gf........",
    ".........d...........fek........",
], [
    E, E, E, E, E,
    "..u...u...................u.....",
    ".....t.......................u..",
    "u...u...................t.......",
    "..t.......t..........u.....t....",
    "......s..................s......",
    "...s............................",
    E, E,
    "................g...............",
    "...............gfk.......gf.....",
    ".......d.......fek......fekk....",
])]

# ---- chalk and furniture, GEAR palette, 16 x 16 tiles. Line tiles start at y 163 and repeat downward.
FOUL_TOP = grid([
    ".....GWWWWG.....", ".....WWWWWL.....", "....GWWWWWL.....", ".....WWWWWLG....",
    ".....WWWWWL.....", "....GWWWWWLM....", "....WWWWWWL.....", "....WWWWWWLG....",
    "....WWWGWWL.....", "...GWWWWWWLM....", "....WWWWWWL.....", "....WWWWWWLG....",
    "....WWWWWWLL....", "...GWWWWWWWL....", "....WWWWWWWLM...", "....WWWWWWWL....",
], 16)
FOUL_MID = grid([
    "....WWWWWWWLG...", "...GWWWWWWWL....", "....WWWWWWWL....", "....WWWWWWWLM...",
    "...GWWWGWWWL....", "....WWWWWWWL....", "....WWWWWWWLG...", "....WWWWWWWL....",
    "...GWWWWWWWLM...", "....WWWWWWWL....", "....WWWWGWWL....", "....WWWWWWWLG...",
    "...GWWWWWWWL....", "....WWWWWWWLM...", "....WWWWWWWL....", "...GWWWWWWWLG...",
], 16)
MARK_TOP = grid([
    ".....GYYYYO.....", ".....CYYYYO.....", "....GCYYYYO.....", ".....RRRRRr.....",
    ".....RRRRRr.....", "....GRRRRRr.....", "....CYYYYYO.....", "....CYYYYYOG....",
    "....CYYYYYO.....", "...GRRRRRRr.....", "....RRRRRRr.....", "....RRRRRRrG....",
    "....CYYYYYYO....", "...GCYYYYYYO....", "....CYYYYYYO....", "....RRRRRRRr....",
], 16)
MARK_MID = grid([
    "....RRRRRRRrG...", "...GRRRRRRRr....", "....CYYYYYYO....", "....CYYYYYYO....",
    "...GCYYYYYYO....", "....CYYYYYYOG...", "....RRRRRRRr....", "....RRRRRRRr....",
    "...GRRRRRRRr....", "....RRRRRRRrG...", "....CYYYYYYO....", "....CYYYYYYO....",
    "...GCYYYYYYO....", "....CYYYYYYOG...", "....RRRRRRRr....", "...GRRRRRRRr....",
], 16)
TICK_TOP = grid([
    ".......W........", ".......WL.......", ".......WL.......", "......GWL.......",
    ".......WL.......", ".......WLG......", ".......WL.......", ".......WW.......",
    "......GWL.......", ".......WL.......", ".......WWL......", ".......WWL......",
    ".......WWLG.....", "......GWWL......", ".......WWL......", ".......WWL......",
], 16)
TICK_MID = grid([
    ".......WWL......", ".......WWLG.....", "......GWWL......", ".......WWL......",
    ".......WGL......", ".......WWL......", ".......WWLG.....", ".......WWL......",
    "......GWWL......", ".......WWL......", ".......WWL......", ".......WWLG.....",
    ".......WWL......", "......GWWL......", ".......WGL......", ".......WWL......",
], 16)
POLE = grid([           # foul line pole with flag, y 147..162
    "......KK........", ".....KWWKKK.....", ".....KWLKRRKK...", ".....KWLKRRRRK..",
    ".....KWLKRRrK...", ".....KRrKrK.....", ".....KRrKK......", ".....KWLK.......",
    ".....KWLK.......", ".....KRrK.......", ".....KRrK.......", ".....KWLK.......",
    ".....KWLK.......", ".....KRrK.......", "....KDRrDK......", "....KKKKKK......",
], 16)
FACE = [                # 10 M board face, y 131..146; digits stamped into rows 4..8
    "................", ".KKKKKKKKKKKKKK.", "KLnnnnnnnnnnnnNK", "KnNNNNNNNNNNNNNK",
    "KnNNNNNNNNNNNNNK", "KnNNNNNNNNNNNNNK", "KnNNNNNNNNNNNNNK", "KnNNNNNNNNNNNNNK",
    "KnNNNNNNNNNNNNNK", "KNNNNNNNNNNNNNDK", "KNDDDDDDDDDDDDDK", ".KKKKKKKKKKKKKK.",
    "......KTUK......", "......KTUK......", "......KTUK......", "......KTUK......",
]
POST = grid([           # board post, y 147..162
    "......KTUK......", "......KTUK......", "......KTUK......", "......KTTK......",
    "......KTUK......", "......KTUK......", "......KUUK......", "......KTUK......",
    "......KTUK......", "......KTUK......", "......KTTK......", "......KTUK......",
    "......KTUK......", ".....KKTUKK.....", "....KDTTUUDK....", "....KKKKKKKK....",
], 16)
DIGIT = {               # 3 x 5, hand-drawn
    '0': ("###", "#.#", "#.#", "#.#", "###"), '1': (".#.", "##.", ".#.", ".#.", "###"), '2': ("###", "..#", "###", "#..", "###"),
    '3': ("###", "..#", ".##", "..#", "###"), '4': ("#.#", "#.#", "###", "..#", "..#"), '5': ("###", "#..", "###", "..#", "###"),
    '6': ("###", "#..", "###", "#.#", "###"), '7': ("###", "..#", "..#", ".#.", ".#."), '8': ("###", "#.#", "###", "#.#", "###"),
    '9': ("###", "#.#", "###", "..#", "###"),
}
# 50 M mark board: pennant (2 flutter frames), gold framed red face, gold banded post. y 115..162
PENNANT = [grid(f, 16) for f in ([
    "................", "......KK........", ".....KCYK.......", ".....KYOK.......",
    "......KK........", "......KUKKK.....", "......KUKRRKKK..", "......KUKRRRRRKK",
    "......KUKRrRRRrK", "......KUKRRrrKK.", "......KUKrrKK...", "......KUKKK.....",
    "......KUK.......", "......KUK.......", "......KUK.......", "......KUK.......",
], [
    "................", "......KK........", ".....KCYK.......", ".....KYOK.......",
    "......KK........", "......KUKKKK....", "......KUKRRRKK..", "......KUKRRRRrK.",
    "......KUKRRrRRKK", "......KUKRrRRRrK", "......KUKrrKKKK.", "......KUKKK.....",
    "......KUK.......", "......KUK.......", "......KUK.......", "......KUK.......",
])]
MARK_FACE = grid([
    ".KKKKKKKKKKKKKK.", "KCYYYYYYYYYYYYOK", "KYRRRRRRRRRRRRrK", "KYRWWWWWRRWWWRrK",
    "KYRWRRRRRWRRRWrK", "KYRWWWWRRWRRWWrK", "KYRRRRRWRWRWRWrK", "KYRRRRRWRWWRRWrK",
    "KYRWRRRWRWRRRWrK", "KYRRWWWRRRWWWRrK", "KYrrrrrrrrrrrrrK", "KOOOOOOOOOOOOOOK",
    ".KKKKKKKKKKKKKK.", "......KTUK......", "......KYCK......", "......KTUK......",
], 16)
MARK_POST = grid([
    "......KTUK......", "......KTUK......", "......KOYK......", "......KTUK......",
    "......KTUK......", "......KTUK......", "......KOYK......", "......KTUK......",
    "......KTUK......", "......KTUK......", "......KOYK......", "......KTUK......",
    "......KTUK......", ".....KKOYKK.....", "....KDOYYCDK....", "....KKKKKKKK....",
], 16)


def face(n):
    rows = [list(r) for r in FACE]
    s = str(n)
    x = (16 - (4 * len(s) - 1)) // 2 + (1 if len(s) == 2 else 0)
    for i, ch in enumerate(s):
        for y, r in enumerate(DIGIT[ch]):
            for dx, p in enumerate(r):
                if p == '#':
                    rows[4 + y][x + 4 * i + dx] = 'W'
    return grid([''.join(r) for r in rows], 16)


BOARD_M = [m for m in range(10, 160, 10) if m != MARK_M]
FACES = {m: face(m) for m in BOARD_M}


def stamp(im, rows, pal, x, y):
    px = im.load()
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            if ch != '.' and 0 <= x + i < im.width and 0 <= y + j < im.height:
                px[x + i, y + j] = snap(pal[ch]) + (255,)


def column(im, tiles, x, y):
    for k, t in enumerate(tiles):
        stamp(im, t, GEAR, x, y + 16 * k)


def big(im, k):
    return im.resize((im.width * k, im.height * k), Image.NEAREST)


def bird():
    sheet = Image.open(BIRD).convert('RGBA')
    f = sheet.crop((0, 0, 24, 32))
    return f.crop(f.getbbox())


def field(mood, w=320, puff=None, flag=0):
    """Transparent layer w x 224: turf, lines, boards. Foul line centre at x = 56."""
    im = Image.new('RGBA', (w, 224), (0, 0, 0, 0))
    for x in range(0, w, 32):
        stamp(im, TURF_ROWS, TURF[mood], x, FLOOR_Y)
    x0 = 56 - 8
    column(im, [FOUL_TOP, FOUL_MID, FOUL_MID, FOUL_MID], x0, FLOOR_Y + 3)
    column(im, [POLE], x0, FLOOR_Y + 3 - 16)
    for m in range(10, 160, 10):
        x = x0 + m * PX_PER_M
        if x >= w:
            break
        if m == MARK_M:
            column(im, [MARK_TOP, MARK_MID, MARK_MID, MARK_MID], x, FLOOR_Y + 3)
            column(im, [PENNANT[flag], MARK_FACE, MARK_POST], x, FLOOR_Y + 3 - 48)
        else:
            column(im, [TICK_TOP, TICK_MID, TICK_MID, TICK_MID], x, FLOOR_Y + 3)
            column(im, [FACES[m], POST], x, FLOOR_Y + 3 - 32)
    if puff is not None:
        stamp(im, PUFF[puff[0]], TURF[mood], puff[1] - 16, FLOOR_Y + 3 - 16)
    return im


def tiles_of(rows, w):
    return [tuple(r[x:x + 16] for r in rows[y:y + 16]) for y in range(0, len(rows), 16) for x in range(0, w, 16)]


def main():
    out = lambda n: os.path.join(HERE, n)
    b = bird()
    # mock-ups: field over each mood, bird on the run-up, puff at 62 M
    for mood in MOODS:
        sc = Image.open(os.path.join(BG, 'scene_%s_1x.png' % mood)).convert('RGBA')
        f = field(mood, puff=(2, 48 + 8 + 62 * PX_PER_M))
        sc.alpha_composite(f)
        sc.alpha_composite(b, (22, FLOOR_Y - b.height))
        sc.convert('RGB').save(out('mock_%s_1x.png' % mood))
        big(sc, 3).convert('RGB').save(out('mock_%s_3x.png' % mood))
        # 1x build sheet of the turf in this mood's palette
        t = Image.new('RGBA', (32, 64), (255, 0, 255, 255))
        stamp(t, TURF_ROWS, TURF[mood], 0, 0)
        t.save(out('sheet_turf_%s_1x.png' % mood))
    # gear sheet: one tile per cell, 8 per row
    gear = [('foul_top', FOUL_TOP), ('foul_mid', FOUL_MID), ('pole', POLE), ('tick_top', TICK_TOP), ('tick_mid', TICK_MID),
            ('mark_top', MARK_TOP), ('mark_mid', MARK_MID), ('post', POST), ('pennant_0', PENNANT[0]), ('pennant_1', PENNANT[1]),
            ('mark_face', MARK_FACE), ('mark_post', MARK_POST)] + [('face_%d' % m, FACES[m]) for m in BOARD_M]
    g = Image.new('RGBA', (8 * 16, -(-len(gear) // 8) * 16), (255, 0, 255, 255))
    for i, (_, t) in enumerate(gear):
        stamp(g, t, GEAR, i % 8 * 16, i // 8 * 16)
    g.save(out('sheet_gear_1x.png'))
    big(g, 4).save(out('sheet_gear_4x.png'))
    p = Image.new('RGBA', (32 * 5, 16), (255, 0, 255, 255))
    for i, fr in enumerate(PUFF):
        stamp(p, fr, TURF['dusk'], 32 * i, 0)
    p.save(out('sheet_puff_1x.png'))
    big(p, 4).save(out('sheet_puff_4x.png'))
    # close-up of the three turf palettes side by side, 4x
    cu = Image.new('RGBA', (3 * 100, 100), (0, 0, 0, 255))
    for i, mood in enumerate(MOODS):
        sc = Image.open(os.path.join(BG, 'scene_%s_1x.png' % mood)).convert('RGBA')
        sc.alpha_composite(field(mood))
        cu.paste(sc.crop((150, 124, 246, 224)), (i * 100 + 2, 0))
    big(cu, 4).convert('RGB').save(out('closeup_moods_4x.png'))
    # puff GIF: 3x, dusk, 5 frames then rest; the mark pennant flutters
    frames = []
    seq = [0, 0, 1, 1, 2, 2, 2, 3, 3, 4, 4] + [None] * 9
    sc0 = Image.open(os.path.join(BG, 'scene_dusk_1x.png')).convert('RGBA')
    for i, s in enumerate(seq):
        sc = sc0.copy()
        sc.alpha_composite(field('dusk', puff=None if s is None else (s, 242), flag=(i // 5) & 1))
        frames.append(big(sc.crop((176, 112, 304, 208)), 3).convert('P', palette=Image.ADAPTIVE, colors=128))
    frames[0].save(out('puff_3x.gif'), save_all=True, append_images=frames[1:], duration=50, loop=0)
    # numbers
    turf_t = set(tiles_of(TURF_ROWS, 32))
    puff_t = set(t for fr in PUFF for t in tiles_of(fr, 32))
    gear_t = set(tuple(t) for _, t in gear)
    used = lambda rows: sorted(set(''.join(rows)) - {'.'})
    tu = used(TURF_ROWS + [r for fr in PUFF for r in fr])
    gu = used([r for _, t in gear for r in t])
    assert set(tu) <= set(TURF['dusk']) and len(TURF['dusk']) <= 15 and len(GEAR) <= 15 and set(gu) <= set(GEAR)
    for mood in MOODS:
        assert len(set(snap(c) for c in TURF[mood].values())) == len(TURF[mood]), mood + ': two turf roles snap to one colour'
    for x in range(32):     # seam self-check: the turf must be opaque from row 3 down
        assert all(TURF_ROWS[y][x] != '.' for y in range(3, 64))
    with open(out('numbers.txt'), 'w') as fh:
        fh.write('Gum Fling field draft 2026-11-18\n')
        fh.write('floor: turf top y %d, 4 tile rows to 224 (first Trip chunk win_bottom 160, flat floor strip rows)\n' % FLOOR_Y)
        fh.write('turf: 32 x 64 px period, %d unique tiles, palette roles used %d of %d defined (+ transparent), 3 mood palettes (swap only)\n'
                 % (len(turf_t), len(used(TURF_ROWS)), len(TURF['dusk'])))
        fh.write('puff: 5 frames of 32 x 16, %d unique tiles, turf palette, roles used %d\n' % (len(puff_t), len(used([r for fr in PUFF for r in fr]))))
        fh.write('gear (chalk, pole, boards): %d unique tiles (%d number faces 10..150 M without 50, 1 tile per extra 10 M), 1 palette, %d colours\n'
                 % (len(gear_t), len(BOARD_M), len(gu)))
        fh.write('total: %d unique tiles, 2 palettes on screen (turf of the mood + gear); 4 palettes in ROM (3 turf + gear)\n'
                 % (len(turf_t) + len(puff_t) + len(gear_t)))
        fh.write('sprites: turf 20 columns + 1 (scroll) of 4 tiles; per 10 M board 2 columns (board 2 tiles, line 4 tiles) or 1 column of 6;\n')
        fh.write('  11 boards on a 320 screen at 30 px pitch; mark board 3 tiles high; puff 2 columns of 1 tile\n')
        fh.write('turf roles used: %s\ngear roles used: %s\n' % (' '.join(tu), ' '.join(gu)))
    print(open(out('numbers.txt')).read())


if __name__ == '__main__':
    main()
