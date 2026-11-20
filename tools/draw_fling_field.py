#!/usr/bin/env python3.14 -I
"""Gum Fling throwing field, art draft 2026-11-18, second pass (not game code). First pass: old/.

Every tile below is a hand-placed pixel grid (one character = one pixel, spaces are only visual separators).
Nothing is generated: the script only stamps the grids, swaps palettes per mood and builds the mock-ups.

Floor height: turf top = screen y 160, 4 tile rows (160..223). Source: the first Gum Trip chunk has gap
TRIP_GAP_START 144, win_top = ((180 - 144) / 2) & ~15 = 16, win_bottom = 160 (src/core/trip_gen.c), and a flat floor
column is drawn from that edge to TRIP_VIEW_STRIP_BOTTOM 224 = 4 rows of 16 (trip_view_strip_column).

Second pass changes: turf is 4 hand columns of 16 px (P Q R S) laid in the irregular order TURF_SEQ instead of one
32 px period; every tuft is lit from one side (tile H flip turns the light for a mood, LIGHT_LEFT); chalk lines have
one width from top to bottom; the puff is 6 frames of 32 x 32 dust with flying blades; gear has one palette per mood.

Run: python3.14 -I draw_fling_field.py
"""
import os
import re
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
BG = os.path.join(REPO, 'thoughts', 'shared', 'drafts', '2026-11-10-backgrounds-final')
BIRD = os.path.join(REPO, '.claude', 'worktrees', 'gum-games', 'assets', 'flier', 'sootling_sheet.png')
FLOOR_Y = 160
PX_PER_M = 3          # GF_PX_PER_M
MARK_M = 90           # GF_MARK_PX 270
MOODS = ('dusk', 'moon', 'storm')
LIGHT_LEFT = {'dusk': False, 'moon': False, 'storm': False}   # True: turf and shadow tiles are drawn H flipped


def snap(c):          # Neo Geo 5 bits per channel
    return tuple((v >> 3 << 3) | (v >> 5) for v in c)


# ---- palettes: 15 colours + transparent each, picked by hand per mood (hue shifts from blue-green shadow to yellow tip)
TURF = {
    'dusk':  dict(k=(16, 40, 56), e=(16, 64, 64), f=(24, 96, 56), g=(64, 136, 48), a=(32, 112, 56), b=(80, 160, 48), c=(144, 200, 56),
                  d=(216, 232, 96), h=(255, 208, 120), s=(72, 40, 40), t=(136, 88, 56), u=(200, 152, 96), w=(248, 232, 192),
                  m=(48, 128, 56), y=(248, 176, 56)),
    'moon':  dict(k=(8, 24, 64), e=(8, 48, 80), f=(16, 80, 88), g=(40, 120, 104), a=(24, 96, 96), b=(48, 136, 96), c=(104, 184, 128),
                  d=(168, 224, 168), h=(216, 248, 248), s=(40, 32, 64), t=(88, 72, 96), u=(144, 128, 144), w=(216, 224, 240),
                  m=(32, 112, 96), y=(200, 208, 128)),
    # storm, second pass: was olive and flat (f 40,88,64 .. c 136,176,96). Now a cold rain-wet green with a deeper shadow end and paler tips.
    'storm': dict(k=(8, 24, 40), e=(8, 48, 56), f=(16, 80, 64), g=(40, 120, 72), a=(24, 96, 72), b=(48, 136, 80), c=(104, 184, 104),
                  d=(176, 224, 152), h=(224, 248, 232), s=(48, 40, 48), t=(96, 80, 80), u=(152, 144, 128), w=(216, 224, 216),
                  m=(32, 112, 72), y=(216, 200, 96)),
}
# chalk, boards, poles: second pass has one gear palette per mood (still one on screen), so the boards sit in the mood's light
GEAR = {
    'dusk':  dict(W=(248, 248, 248), L=(208, 216, 232), M=(152, 168, 192), D=(88, 104, 136), K=(24, 24, 40), N=(32, 48, 104),
                  n=(64, 88, 160), Y=(248, 208, 56), O=(232, 136, 32), R=(224, 48, 48), r=(144, 24, 48), T=(120, 72, 40),
                  U=(184, 128, 72), G=(192, 224, 168), C=(255, 240, 176)),
    'moon':  dict(W=(208, 224, 248), L=(160, 184, 224), M=(112, 136, 184), D=(64, 80, 128), K=(16, 16, 40), N=(24, 40, 96),
                  n=(48, 72, 136), Y=(216, 200, 104), O=(168, 120, 72), R=(184, 56, 96), r=(112, 24, 72), T=(80, 56, 72),
                  U=(128, 96, 104), G=(128, 192, 168), C=(232, 232, 192)),
    'storm': dict(W=(224, 232, 224), L=(176, 192, 192), M=(128, 144, 152), D=(80, 96, 104), K=(16, 24, 32), N=(32, 48, 72),
                  n=(64, 88, 112), Y=(224, 200, 88), O=(184, 128, 56), R=(200, 64, 56), r=(120, 32, 40), T=(96, 72, 56),
                  U=(144, 112, 80), G=(152, 200, 144), C=(240, 232, 184)),
}


def grid(rows, w):
    out = [r.replace(' ', '') for r in rows]
    for i, r in enumerate(out):
        assert len(r) == w, 'row %d is %d wide, not %d: %s' % (i, len(r), w, r)
    return out


# ---- turf: 4 columns of 16 x 64 (4 tiles each). Mown bands at the same rows in every column, so any column fits beside any other.
# Light comes from the right: a tuft carries c d (h) on its right blades and a m (e k in the dark bands) on its left.
TURF_COL = {
    'P': grid([
        "...d.... ..c.....", ".c.dc... d.cd..c.", "dcbcdcdc cdcbdcdc", "cbccbcbb cbcdbcbc",
        "bbcbbabb bcbbbbcb", "bbbbabbc bbbbabbb", "bmbbbbbb abbmbbbb", "mbmbbmbm bbmbmbbm",
        "fmfmmfmf fmfmfmmf", "fffgffff efffffgf", "feffffgf ffffefff", "ffffefff ffgfffff",
        "fmffffmf fefffmff", "mfmbmfmb mfmbmmfm", "bmbbmbbb mbbmbbmb", "bbbbbcbb bbabbbbb",
        "babbbdcb bbbbbcbb", "bbabbbcb babbbdcb", "bbbbbbbb bbabbbbb", "bmbbbabb bbbbmbbb",
        "mbmbmbbm bmbmbmbm", "fmfmfmfm mfmfmffm", "ffffffef fffgffff", "fefffffg ffffffef",
        "fkefffgg fffeffff", "ffkeffgf ffkefgff", "ffffffff fffkeggf", "fgffefff ffffffff",
        "fmfmffmf mffmfmfm", "mbmbbmbm bmbmbbmb", "bbbbbbbb cbbbbbbb", "bbabbbbc dbbbbabb",
        "bbbabbcd cbbbbbbb", "bbaabbcd dcbbbbbb", "bbbaabbc dbbbcbbb", "bbbbabbb bbbadcbb",
        "bcbbbbbb bbabdcbb", "bbbbbmbb bbbabbbb", "mbbmbbmb mbbmbmbb", "fmfmfmff mfmfmfmf",
        "ffffffff gfffefff", "ffefffff ggffffff", "fkeffgff fgffffef", "fkkefggf ffffffkf",
        "ffkefggg ffffffke", "ffkkefgg fffgffff", "fffkeffg ffefggff", "ffffffff fkefgggf",
        "fmfffmff ffkeffgf", "mfmfmfmm fmfmfmfm", "bmbmbbmb mbmbmbbm", "bbbbbbbb bbbbdbbb",
        "bbbbbbbb bbbadcbb", "bbabbbbb bbamdcdb", "bbbbbbbb bbambdcd", "bbbbcbbb baambcdh",
        "bbbadbbb bbaabbcd", "bbamdcbb bbbabbbb", "bbambdcb bbbbbbbb", "baambcdb bbcbbabb",
        "bbaabbcb babbbbbb", "abbabbbb bbbbabba", "mabmaabm abmabamb", "emaemame maemeame",
    ], 16),
    'Q': grid([
        ".c.....d ....h...", "dcd..c.d c..cd.d.", "cdcdcbdc dccdcdbc", "bcbcbbcd bcbbcbcb",
        "bcbbbbcb babbbcbb", "bbabbbbb bcbbbbab", "bbbmbbba bbbbbmbb", "bmbbmbmb mbbmbmbm",
        "mfmffmfm fmmfmfmf", "ffefffff gffffeff", "fffffgff ffefffff", "gfffffff efffffgf",
        "ffmfeffm ffffmfff", "mbmfmbmf mbmfmbmf", "bbmbbmbb bmbbmbbm", "bbbbbbbb cbbbbbbb",
        "bbbcbbab dcbbbabb", "babdcbbb cbbbbbbb", "bbbcbbbb bbbbbabb", "bbbbbmbb abbbmbbb",
        "bmbmbmbm bmbbmbmb", "mfmfmfmf fmfmfmfm", "fffeffff ffffffgf", "ffffffff fefffggf",
        "ffgfffff fkefffgf", "fggfefff ffkeffff", "ffgfffff ffffffff", "ffffffef ffgfffef",
        "mffmfmff mfmffmfm", "bmbmbmbm bbmbmbmb", "bbbbbbbb bbbbbbcb", "bbbbbbbb bbabbbdc",
        "bcbbbabb bbbabbcd", "bdcbbbbb bbbaabbc", "bcdbbbbb bbbbabbb", "abcbbbbb bbbbbbbb",
        "babbbbwb bbbbbbbb", "bbbbbwyw bbbbcbbb", "bmbbmbwb mbbmbbmb", "mfmfmfmf mfmfmfmf",
        "ffffffff ffffffff", "fffgffff ffefffff", "ffggffef ffkeffgf", "fffgffff fffkefgg",
        "ffffffff fffkkfgg", "fefffffg ffffkefg", "fkeffggf ffffffff", "ffkefgff ffgfffff",
        "ffffffff mfffefmf", "fmfmmfmf mfmfmfmf", "mbmbbmbm bmbmbbmb", "bbbbbbbb bbbbbbbb",
        "bbdbbbbb bbbbbbbb", "badcbbbb bbbbbcbb", "amdcdbbb bbbbadbb", "ambdcdbb bbbamdcb",
        "aambcdhb bbbambdc", "baabbcdb bbaambcd", "bbabbbbb bbbaabbc", "bbbbbbbb bcbbabbb",
        "bbbabbbb bbbbbbbb", "babbbbab bbabbbba", "ambabmab mabmabam", "meamemae emaemaem",
    ], 16),
    'R': grid([
        "......c. .d......", ".d.c.dcd .dc..c.d", "cdbcdccd cdcdcbcd", "cbbcbcbb cbcbbcdb",
        "bbbcbbbb cbbabbbb", "abbbbcbb bbabbbbc", "bbmbbbbb bmbbbbab", "mbmbmbbm bmbmbbmb",
        "fmfmfmmf mffmfmfm", "fgffffef ffffgfff", "ffffefff gfffffef", "fffgffff ffefffff",
        "mfffffmf fffmfeff", "fmbmfmbm fmbmfmbm", "mbbmbbmb bmbbmbbb", "bbbbbbbb bbbbbbbb",
        "bbbbbbbc bbbbabbb", "bbbabbcd bbbbbbbb", "bbbbabbc bbbbbcbb", "bbmbbbbb bbabbdcb",
        "mbmbbmbm bbmbmbmb", "fmfmfmfm fmfmmfmf", "ffffgfff ffefffff", "fffggfff ffffffff",
        "fefffgff ffffgfff", "fkefffff fffgggff", "ffkkefff fkefggff", "fffffffg ffkeffff",
        "fmffmfmf mfmfmffm", "mbmbmbbm bmbbmbmb", "bbbbbbbb bbbbbbbb", "bbbcbbbb bbbbbbbb",
        "bbadcbbb bbbbbabb", "bbabdcbb bbbbbbbb", "bbbabcbb bbcbbbbb", "bbbbbbbb badcbbbb",
        "bbbbbbbb abdcdbbb", "bbabbbbb babbcbbb", "bmbbmbmb bmbbmbbm", "mfmfmfmf mfmfmfmf",
        "ffffffff ffffgfff", "ffffefff fffffggf", "ffffkeff fefffgff", "gffffkef fkefffff",
        "ggfffffe ffkkefff", "fgffffff fffkefgf", "ffffffff ffffffgg", "ffefffgf ffffffgf",
        "fmffffff fmfeffmf", "mfmfmfmf mfmmfmfm", "bmbmbmbb mbmbbmbm", "bbbbbbbb bbbbbbbb",
        "bbbbbbbb bbbbbbbb", "bbbbbcbb bbbbbbbb", "bbbbadbb bbwbbbbb", "bbbamdcb bwywbbbb",
        "bbambdcd bbwbbabb", "bbambbdc bbbbbbbb", "baaambcd bbbbdbbb", "bbaabbbc bbbadcbb",
        "bbbabbbb bbamdcdb", "abbbbbab baambcdb", "mabmabma mbaabamb", "emaemame amemaeme",
    ], 16),
    'S': grid([
        "..d..... ....c..d", ".cdc.d.. c.d.dcdc", "dccdcbcd dcbcdcdc", "bcbcdbcb bcbcbbcb",
        "cbbabbbc bbbbcbbb", "bbbbbbab bbbcbbbb", "bmbbbabb bbmbbbbb", "bbmbmbmb bmbmbmbb",
        "mffmfmfm fmfmmfmf", "ffffgfff feffffff", "gffffffe fffffgff", "ffefffff ffgfffef",
        "fffmffff mfffffmf", "bmfmbmfm bmfmbmfm", "bbmbbbmb bmbbmbbm", "bbbbcbbb bbbbbbbb",
        "bbbadcbb bbbbbbab", "bbbabcbb bbcbbbbb", "bbbbbbbb badcbbbb", "babbbbmb bbabbbmb",
        "bmbmbmbm bmbmbbmb", "mfmfmfmf mfmfmfmf", "ffffffff fffgffff", "ffefffff ffggffef",
        "fffkefff fffgffff", "ffffkefg ffffffff", "fffffffg gfffefff", "fgfffffg ffffkeff",
        "mfmffmfm ffmfmfmf", "bmbmbbmb mbmbmbbm", "bbbbbbbb bbbbbbbb", "bbbbbbab bbbbcbbb",
        "bbbbbbbb bbbadcbb", "bcbbbbbb bbaabdcb", "adcbbbbb bbbaabcb", "abdcbbbb bbbbabbb",
        "babcbbbb bbbbbbbb", "bbbbbbab bbbbbbbb", "mbbmbbmb bmbbmbmb", "fmfmfmfm fmfmfmfm",
        "ffffffff ffffffff", "ffgfffff ffffefff", "fgggffff fffffkef", "ffggfeff ffgfffke",
        "fffffkef fgggffff", "ffffffke ffggffff", "fffeffff ffffffef", "gfffffff ffgffffk",
        "ffmfffef fmffffmf", "fmfmfmfm fmfmfmmf", "mbbmbmbm bmbmbmbm", "bbbbbbbb bbbbbbbb",
        "bbbbbbbb bcbbbbbb", "bbbbbbbb adbbbbbb", "bbbdbbbb mdcbbbbb", "bbadcbbb mbdcbbab",
        "bamdcdbb abcdbbbb", "bambdcdb aabcbbbb", "aambcdhb babbbbbb", "baabbcdb bbbbbbcb",
        "bbabbbbb bbabbbbb", "babbbbba bbbbabba", "mabamabm abmabmab", "aemeamem eameamea",
    ], 16),
}
# hand-picked column order, 32 long, no column twice in a row; the game repeats it every 512 px (the run is 450 px + run-up)
TURF_SEQ = "PRQSQPSRPQRSRPSQSRQPRSPQSQRPQSPR"

# ---- landing puff: 6 frames of 32 x 32 (4 tiles each, empty tiles not stored), turf palette; bottom row sits 3 px into the turf.
# Dust: w lit top, u body, t only as sparse under-shade, no outline; edges and late frames broken by transparent dither.
# Blades and crumbs follow hand-computed throws (per frame f: x = x0 + vx f, y = 28 - vy f + f f): B1 vx 3 vy 6, B2 vx -2 vy 5,
# B3 vx 1.5 vy 8, B4 vx 6 vy 4, B5 vx -0.5 vy 7; a blade turns / - \ | / over frames 1..5.
E = "................................"


def frame(rows):         # rows: {row index: text}; the rest is empty
    return grid([rows.get(i, E) for i in range(32)], 32)


PUFF = [frame(f) for f in ({
    26: "........ ..ww.ww. ........ ........",
    27: "......w. wwwwwwww .w...... ........",
    28: ".....w.w wuwwuwwu w.w..... ........",
    29: "......u. u.u.u.u. u....... ........",
}, {
    20: "........ ....d... ........ ........",
    21: "........ .d..c... .d...... ........",
    22: "........ .c...... .c...... ........",
    23: ".....ww. ........ ..ww.... ........",
    24: "...wwwww w...c... wwwwww.. ........",
    25: "..wwwuww ww..d..w wwuwwww. ........",
    26: ".wwuwwuw wuw...ww uwwuwuww ........",
    27: ".wuwu.wu uwu..wuw u.uwuwuw ........",
    28: "..u.uu.u u.u...u. uu.u.uu. ........",
    29: "...u..u. .u.....u ..u..u.. ........",
}, {
    16: "........ ........ cd...... ........",
    18: "........ .cd..... ........ ........",
    19: "...ww... ........ ....ww.. ........",
    20: ".wwwwww. ........ ..wwwwww ........",
    21: "wwww.www w......w www.wwww w.......",
    22: "www.uwww wc.....w wwuw.www ww......",
    23: "wwuwww.w w.d...ww .wwwuwww w.cd....",
    24: ".wwwuwwu w......w wuwww.wu w.......",
    25: "w.uw.wuw .......u w.wuwwu. u.......",
    26: ".u.wu.u. u....... .wu.uw.u ........",
    27: "u..u.u.u ........ u..u.u.. u.......",
    28: "..u...u. ........ ..u...u. ........",
}, {
    13: "........ ........ .d...... ........",
    14: "........ ........ ..c..... ........",
    16: "........ d....... ........ ........",
    17: "..ww.... .c...... ....ww.. ........",
    18: ".w..ww.. ........ ..ww..w. w.......",
    19: "ww.w..w. ........ .w..ww.w ..w.....",
    20: ".w.uw.ww ........ w.wu..w. ww......",
    21: "w..w.u.. w....... ..w.wu.w ..w.....",
    22: ".wu..w.u ........ w.u..w.. u.w.....",
    23: "..w.u..w ........ .u.w.u.w ..u.....",
    24: "u..u.w.. ........ ..u..u.. w.......",
    25: ".u..u..u ........ u..u..u. .u......",
    26: "...u..u. ........ ..u..t.. ........",
    27: ".t...u.. ........ ....u..t ........",
}, {
    12: "........ ........ ...d.... ........",
    13: "........ ........ ...g.... ........",
    16: "........ d....... ........ ........",
    17: "..w..... g....... ......w. ........",
    18: ".....w.. ........ ...w.... .w......",
    19: "w...u... ........ ......u. ....w...",
    20: "...u...u ........ ..u..... d..u....",
    21: ".u...u.. ........ .....u.. g.......",
    22: "....u... ........ .u...... ..u..u..",
    23: "u..t...u ........ ....u..u ........",
    24: "...d.u.. ........ ..t..... .u..t...",
    25: ".t.g.... ........ ......t. ........",
    26: ".....t.. ........ ...u.... ..t.....",
}, {
    13: "........ ........ ....c... ........",
    14: "........ ........ ...g.... ........",
    16: "...w.... ........ ........ w.......",
    18: ".......c ........ .....u.. ........",
    19: "......g. ........ ........ ...u....",
    20: ".u...... ........ ..u..... ........",
    22: "......u. ........ ........ .u......",
    23: "........ ........ .....t.. ...c....",
    24: "..t..... ........ ........ ..g.....",
    26: "........ ........ ..t..... ......t.",
    28: ".g...... ........ ........ ........",
})]

# ---- chalk, GEAR palette, 16 x 16 tiles. Line tiles start at y 163 and repeat downward. Second pass: one width top to bottom
# (the first pass widened in steps), quieter colours (L body with a 1 px W core instead of solid W; the 10 M lines are L and M),
# grass gaps instead of a hard edge, and the top tile carries the post's cast shadow (K checker, falls away from the light).
FOUL_TOP = grid([
    "...K.KLWWL......", "..K.K.LWWL......", ".K.K.GLWWL......", "..K...LWLL......",
    "......LWWL......", "......LWWLG.....", "......LLWL......", ".....GLWWL......",
    "......LW.L......", "......LWWL......", "......LWWLG.....", "......LWLL......",
    "......LWWL......", ".....GLWWL......", "......LWWL......", "......L.WL......",
], 16)
FOUL_MID = grid([
    "......LWWL......", "......LWWLG.....", ".....GLWLL......", "......LWWL......",
    "......LWWL......", "......LLWL......", "......LWWLG.....", "......LW.L......",
    ".....GLWWL......", "......LWWL......", "......LWLL......", "......LWWL......",
    "......LWWLG.....", "......L.WL......", ".....GLWWL......", "......LWWL......",
], 16)
MARK_TOP = grid([
    "...K.KCYYO......", "..K.K.CYYO......", ".K.K.GCYYO......", "..K...CYOO......",
    "......CYYO......", "......CYYOG.....", "......YYYO......", ".....GCYYO......",
    "......CY.O......", "......CYYO......", "......CYYOG.....", "......CYOO......",
    "......CYYO......", ".....GCYYO......", "......YYYO......", "......C.YO......",
], 16)
MARK_MID = grid([
    "......CYYO......", "......CYYOG.....", ".....GCYOO......", "......CYYO......",
    "......YYYO......", "......CYYO......", "......CYYOG.....", "......CY.O......",
    ".....GCYYO......", "......CYYO......", "......CYOO......", "......YYYO......",
    "......CYYOG.....", "......C.YO......", ".....GCYYO......", "......CYYO......",
], 16)
TICK_TOP = grid([
    "....K.KLM.......", "...K.K.LM.......", "..K.K..LM.......", "...K...LL.......",
    ".......LM.......", ".......LM.......", ".......L........", ".......LM.......",
    ".......LM.......", ".......MM.......", ".......LM.......", "........M.......",
    ".......LM.......", ".......LM.......", ".......LL.......", ".......LM.......",
], 16)
TICK_MID = grid([
    ".......LM.......", ".......LM.......", ".......M........", ".......LM.......",
    ".......LL.......", ".......LM.......", ".......LM.......", "........M.......",
    ".......LM.......", ".......LM.......", ".......MM.......", ".......LM.......",
    ".......L........", ".......LM.......", ".......LM.......", ".......LL.......",
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
# 90 M mark board: pennant (2 flutter frames), gold framed red face, gold banded post. y 115..162
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
    ".KKKKKKKKKKKKKK.", "KCYYYYYYYYYYYYOK", "KYRRRRRRRRRRRRrK", "KYRRWWWRRRWWWRrK",
    "KYRWRRRWRWRRRWrK", "KYRWRRRWRWRRWWrK", "KYRRWWWWRWRWRWrK", "KYRRRRRWRWWRRWrK",
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
SHADOWED = (FOUL_TOP, MARK_TOP, TICK_TOP)     # tiles drawn H flipped when the mood's light comes from the left


def stamp(im, rows, pal, x, y, flip=False):
    px = im.load()
    for j, r in enumerate(rows):
        for i, ch in enumerate(r[::-1] if flip else r):
            if ch != '.' and 0 <= x + i < im.width and 0 <= y + j < im.height:
                px[x + i, y + j] = snap(pal[ch]) + (255,)


def column(im, tiles, mood, x, y):
    for k, t in enumerate(tiles):
        stamp(im, t, GEAR[mood], x, y + 16 * k, LIGHT_LEFT[mood] and any(t is s for s in SHADOWED))


def big(im, k):
    return im.resize((im.width * k, im.height * k), Image.NEAREST)


def bird(i):
    sheet = Image.open(BIRD).convert('RGBA')
    f = sheet.crop((24 * (i % 8), 32 * (i // 8), 24 * (i % 8) + 24, 32 * (i // 8) + 32))
    return f.crop(f.getbbox())


def scene(mood):
    """Sky and the four parallax planes only (build sheets, magenta = transparent). No arena props, clouds, airship or beams."""
    sc = Image.new('RGBA', (320, 224), (0, 0, 0, 255))
    for name, x, y in (('sky', 0, 0), ('far', 8, 48), ('midA', 8, 80), ('midB', 8, 112), ('near', 0, 128)):
        p = Image.open(os.path.join(BG, 'plane_%s_%s_1x.png' % (mood, name))).convert('RGBA')
        px = p.load()
        for yy in range(p.height):
            for xx in range(p.width):
                if px[xx, yy][:3] == (255, 0, 255):
                    px[xx, yy] = (0, 0, 0, 0)
        sc.alpha_composite(p.crop((x, 0, x + 320, p.height)), (0, y))
    return sc


def turf(mood, w=320):
    im = Image.new('RGBA', (w, 64), (0, 0, 0, 0))
    for i in range(-(-w // 16)):
        stamp(im, TURF_COL[TURF_SEQ[i % len(TURF_SEQ)]], TURF[mood], 16 * i, 0, LIGHT_LEFT[mood])
    return im


def field(mood, w=320, puff=None, flag=0):
    """Transparent layer w x 224: turf, lines, boards. Foul line centre at x = 56."""
    im = Image.new('RGBA', (w, 224), (0, 0, 0, 0))
    im.alpha_composite(turf(mood, w), (0, FLOOR_Y))
    x0 = 56 - 8
    column(im, [POLE, FOUL_TOP, FOUL_MID, FOUL_MID, FOUL_MID], mood, x0, FLOOR_Y + 3 - 16)
    for m in range(10, 160, 10):
        x = x0 + m * PX_PER_M
        if x >= w:
            break
        if m == MARK_M:
            column(im, [PENNANT[flag], MARK_FACE, MARK_POST, MARK_TOP, MARK_MID, MARK_MID, MARK_MID], mood, x, FLOOR_Y + 3 - 48)
        else:
            column(im, [FACES[m], POST, TICK_TOP, TICK_MID, TICK_MID, TICK_MID], mood, x, FLOOR_Y + 3 - 32)
    if puff is not None:
        stamp(im, PUFF[puff[0]], TURF[mood], puff[1] - 12, FLOOR_Y + 3 - 32)   # impact point is column 12 of the frame
    return im


def mock(mood):
    sc = scene(mood)
    sc.alpha_composite(field(mood))
    d = ImageDraw.Draw(sc)
    x0, x1, top = 56, 56 + 62 * PX_PER_M, 100     # throw of 62 M: dotted flight path, bird at the line and in flight
    for k in range(1, 12):
        t = k / 12
        x, y = round(x0 + (x1 - x0) * t), round(148 + 12 * t - 4 * top * t * (1 - t))
        if k != 7:
            d.rectangle((x - 1, y - 1, x + 2, y + 2), fill=snap(GEAR[mood]['K']))
            d.rectangle((x, y, x + 1, y + 1), fill=snap(GEAR[mood]['W']))
    b, fl = bird(0), bird(2)
    sc.alpha_composite(b, (x0 - 8 - b.width, FLOOR_Y - b.height + 1))
    t = 7 / 12
    sc.alpha_composite(fl, (round(x0 + (x1 - x0) * t) - fl.width // 2, round(148 + 12 * t - 4 * top * t * (1 - t)) - fl.height // 2))
    return sc


def stack(pairs, k):
    """Old above new, each with a caption line."""
    w = max(im.width for _, im in pairs) * k
    out = Image.new('RGB', (w, sum(im.height * k + 12 for _, im in pairs)), (20, 24, 31))
    d, y = ImageDraw.Draw(out), 0
    for cap, im in pairs:
        d.text((2, y), cap, fill=(223, 229, 238))
        out.paste(big(im.convert('RGB'), k), (0, y + 12))
        y += im.height * k + 12
    return out


def tiles_of(rows, w):
    return [tuple(r[x:x + 16] for r in rows[y:y + 16]) for y in range(0, len(rows), 16) for x in range(0, w, 16)]


def bg_lines():
    """Scenery sprites per scanline of the reused backgrounds, per 16 lines, from their numbers.txt."""
    out, mood = {}, None
    for ln in open(os.path.join(BG, 'numbers.txt')):
        m = re.match(r'== mood (\w+)', ln)
        if m:
            mood = m.group(1)
        if 'per 16 lines, trimmed count:' in ln:
            out[mood] = [int(v) for v in ln.split(':')[1].split()]
    return out


def main():
    out = lambda n: os.path.join(HERE, n)
    old = lambda n: Image.open(os.path.join(HERE, 'old', n)).convert('RGBA')
    cu = Image.new('RGBA', (3 * 100, 100), (0, 0, 0, 255))
    strips = []
    for i, mood in enumerate(MOODS):
        sc = mock(mood)
        sc.convert('RGB').save(out('mock_%s_1x.png' % mood))
        big(sc, 3).convert('RGB').save(out('mock_%s_3x.png' % mood))
        stack([('old (first pass)', old('mock_%s_1x.png' % mood)), ('new (second pass)', sc)], 2).save(out('cmp_mock_%s_2x.png' % mood))
        t = Image.new('RGBA', (64, 64), (255, 0, 255, 255))      # 1x build sheet: columns P Q R S in this mood's palette
        for j, c in enumerate('PQRS'):
            stamp(t, TURF_COL[c], TURF[mood], 16 * j, 0)
        t.save(out('sheet_turf_%s_1x.png' % mood))
        bgc = Image.new('RGBA', (320, 64), (0, 0, 0, 255))
        bgc.alpha_composite(turf(mood))
        strips.append((mood, bgc))
        plain = scene(mood)
        plain.alpha_composite(field(mood))
        cu.paste(plain.crop((150, 124, 246, 224)), (i * 100 + 2, 0))
    big(cu, 4).convert('RGB').save(out('closeup_moods_4x.png'))
    stack([('old', big(old('closeup_moods_4x.png'), 1)), ('new', big(cu, 4))], 1).save(out('cmp_closeup_4x.png'))
    stack(strips, 2).save(out('turf_strip_2x.png'))
    ot = old('sheet_turf_dusk_1x.png')
    os_ = Image.new('RGBA', (320, 64))
    for x in range(0, 320, 32):
        os_.paste(ot, (x, 0))
    stack([('old: 32 px period', os_), ('new: 4 columns, irregular order', strips[0][1])], 2).save(out('cmp_turf_2x.png'))
    # gear sheet per mood: one tile per cell, 8 per row
    gear = [('foul_top', FOUL_TOP), ('foul_mid', FOUL_MID), ('pole', POLE), ('tick_top', TICK_TOP), ('tick_mid', TICK_MID),
            ('mark_top', MARK_TOP), ('mark_mid', MARK_MID), ('post', POST), ('pennant_0', PENNANT[0]), ('pennant_1', PENNANT[1]),
            ('mark_face', MARK_FACE), ('mark_post', MARK_POST)] + [('face_%d' % m, FACES[m]) for m in BOARD_M]
    rows = -(-len(gear) // 8)
    g = Image.new('RGBA', (8 * 16, 3 * rows * 16), (255, 0, 255, 255))
    for k, mood in enumerate(MOODS):
        for i, (_, t) in enumerate(gear):
            stamp(g, t, GEAR[mood], i % 8 * 16, (k * rows + i // 8) * 16)
    g.save(out('sheet_gear_1x.png'))
    big(g, 4).save(out('sheet_gear_4x.png'))
    p = Image.new('RGBA', (32 * len(PUFF), 3 * 32), (255, 0, 255, 255))
    for k, mood in enumerate(MOODS):
        tile = Image.new('RGBA', (16, 16))
        stamp(tile, [r[:16] for r in TURF_COL['P'][16:32]], TURF[mood], 0, 0)     # frames shown over turf: the real backdrop
        for xx in range(0, p.width, 16):
            for yy in (0, 16):
                p.paste(tile, (xx, 32 * k + yy))
        for i, fr in enumerate(PUFF):
            stamp(p, fr, TURF[mood], 32 * i, 32 * k)
    p.save(out('sheet_puff_1x.png'))
    big(p, 4).save(out('sheet_puff_4x.png'))
    stack([('old: 5 frames of 32 x 16', old('sheet_puff_1x.png')), ('new: 6 frames of 32 x 32 (dusk, moon, storm), on turf', p)], 4).save(out('cmp_puff_4x.png'))
    # puff GIF: 3x, per mood, 6 frames then rest; the mark pennant flutters. 50 ms = 3 game frames per step.
    seq = [0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5] + [None] * 9
    for mood in MOODS:
        sc0, frames = scene(mood), []
        for i, s in enumerate(seq):
            sc = sc0.copy()
            sc.alpha_composite(field(mood, puff=None if s is None else (s, 242), flag=(i // 5) & 1))
            frames.append(big(sc.crop((176, 112, 304, 208)), 3).convert('RGB'))
        strip = Image.new('RGB', (384 * len(frames), 288))       # one shared palette for all frames, so no viewer shows wrong colours
        for i, f in enumerate(frames):
            strip.paste(f, (384 * i, 0))
        strip = strip.quantize(255)
        frames = [strip.crop((384 * i, 0, 384 * i + 384, 288)) for i in range(len(frames))]
        frames[0].save(out('puff_%s_3x.gif' % mood), save_all=True, append_images=frames[1:], duration=50, loop=0)
    # numbers
    turf_t = set(t for c in TURF_COL.values() for t in tiles_of(c, 16))
    blank = tuple(['.' * 16] * 16)
    puff_t = set(t for fr in PUFF for t in tiles_of(fr, 32)) - {blank}
    gear_t = set(tuple(t) for _, t in gear)
    used = lambda rows: sorted(set(''.join(rows)) - {'.'})
    turf_rows = [r for c in TURF_COL.values() for r in c]
    tu = used(turf_rows + [r for fr in PUFF for r in fr])
    gu = used([r for _, t in gear for r in t])
    assert len(TURF_SEQ) == 32 and all(a != b for a, b in zip(TURF_SEQ, TURF_SEQ[1:] + TURF_SEQ[0]))
    for mood in MOODS:
        assert set(tu) <= set(TURF[mood]) and len(TURF[mood]) <= 15 and len(GEAR[mood]) <= 15 and set(gu) <= set(GEAR[mood])
        assert len(set(snap(c) for c in TURF[mood].values())) == len(TURF[mood]), mood + ': two turf roles snap to one colour'
        assert len(set(snap(c) for c in GEAR[mood].values())) == len(GEAR[mood]), mood + ': two gear roles snap to one colour'
    for c in TURF_COL.values():     # seam self-check: the turf must be opaque from row 2 down
        assert all(ch != '.' for r in c[2:] for ch in r)
    # sprite budget. One hardware sprite = one 16 px column of tiles. Worst case on screen while scrolling:
    markers = -(-336 // (10 * PX_PER_M))     # boards + foul pole in 320 + 16 px at 30 px pitch, one sprite each (board, post and line chained)
    turf_n, bird_n, dots_n, puff_n = 21, 4, 10, 2     # turf 20 + 1 scroll; hero body 2 + chute 2; FLING_ARC_COUNT; puff 2 columns
    bg = bg_lines()
    with open(out('numbers.txt'), 'w') as fh:
        fh.write('Gum Fling field draft 2026-11-18, second pass (first pass: old/numbers.txt)\n')
        fh.write('floor: turf top y %d, 4 tile rows to 224 (first Trip chunk win_bottom 160, flat floor strip rows)\n' % FLOOR_Y)
        fh.write('turf: 4 columns of 16 x 64 px in a hand order of %d (512 px), %d unique tiles, roles used %d of 15, 3 mood palettes (swap only);\n'
                 % (len(TURF_SEQ), len(turf_t), len(used(turf_rows))))
        fh.write('  light side per mood by tile H flip: %s\n' % ', '.join('%s %s' % (m, 'left' if LIGHT_LEFT[m] else 'right') for m in MOODS))
        fh.write('puff: %d frames of 32 x 32, %d unique non-empty tiles, turf palette, roles used %d\n'
                 % (len(PUFF), len(puff_t), len(used([r for fr in PUFF for r in fr]))))
        fh.write('gear (chalk, pole, boards): %d unique tiles (%d number faces 10..150 M without 90), 3 mood palettes (swap only), %d colours each\n'
                 % (len(gear_t), len(BOARD_M), len(gu)))
        fh.write('total: %d unique tiles, 2 palettes on screen (turf + gear of the mood); 6 palettes in ROM (3 turf + 3 gear)\n'
                 % (len(turf_t) + len(puff_t) + len(gear_t)))
        fh.write('turf roles used: %s\ngear roles used: %s\n' % (' '.join(tu), ' '.join(gu)))
        fh.write('\nsprite budget (Neo Geo: 96 sprites per scanline, 381 sprites)\n')
        fh.write('field sprites: turf %d (20 + 1 scroll, 4 tiles, lines 160..223); markers %d worst case (336 px / 30 px pitch; board + post + line\n'
                 '  chained in one sprite of 6 tiles from line 131, the 90 M mark 7 tiles from line 115); puff %d (2 tiles, lines 131..162)\n'
                 % (turf_n, markers, puff_n))
        fh.write('others counted: bird %d (hero body 2 + parachute 2), aim pointer and dots %d (FLING_ARC_COUNT, all assumed on one line)\n' % (bird_n, dots_n))
        fh.write('background: per 16 lines, trimmed count from 2026-11-10-backgrounds-final/numbers.txt (near plane still drawn behind the turf)\n')
        for mood in MOODS:
            tot = []
            for i, n in enumerate(bg[mood]):
                y = 16 * i
                tot.append(n + (markers if y + 15 >= 115 else 0) + (turf_n if y >= 160 else 0) + bird_n + dots_n + (puff_n if 128 <= y < 176 else 0))
            fh.write('  %-5s per 16 lines, all of the above: %s  worst %d of 96 (lines %d..%d)\n'
                     % (mood, ' '.join(str(v) for v in tot), max(tot), 16 * tot.index(max(tot)), 16 * tot.index(max(tot)) + 15))
        fh.write('  cutting the near plane columns at line 160 (hidden by the turf) frees up to 20 more on lines 160..223\n')
        need = turf_n + markers
        fh.write('slots (src/sprite_slots.h, gum-games worktree): the field has no islands, hazard strip, Trip strips or pickups.\n')
        fh.write('  turf + markers = %d, behind the fliers: ISLAND_SPRITE 120..160 (%d slots, %d spare; pool 161.. and hero 257.. draw in front)\n' % (need, 41, 41 - need))
        fh.write('  puff %d, in front of the bird: TRIP_STRIP range 333..366 (44 - FLING_ARC_COUNT 10 = 34 free), hidden while aiming\n' % puff_n)
        fh.write('  also unused on the field: HAZARD_SPRITE 261..308 (48), TRIP_PICKUP 367..376 (10), 118..119 (2)\n')
    print(open(out('numbers.txt')).read())


if __name__ == '__main__':
    main()
