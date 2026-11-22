#include <string.h>
#include "stadium.h"
#include "gen/stadium_motion.h"

static uint8_t side_of(int col) { return (uint8_t)(col >= STADIUM_SIDE_COLS); }

#define FAR_NONE 255
static uint8_t g_far_idle[STADIUM_FAR_ROWS][STADIUM_COLS][8];
static uint8_t g_far_be[sizeof ST_BLOCK / sizeof ST_BLOCK[0]][128];   /* constant data: never cleared */

void stadium_reset(Stadium *s)
{
    int i;
    for (i = 0; i < 2; i++) { s->mode[i] = STADIUM_IDLE; s->t[i] = 0; s->score[i] = 0; }
    memset(g_far_idle, 0, sizeof g_far_idle);
}

void stadium_set_scores(Stadium *s, uint8_t p1, uint8_t p2)
{
    uint8_t n[2];
    int i;
    n[0] = p1 > 99 ? 99 : p1;
    n[1] = p2 > 99 ? 99 : p2;
    for (i = 0; i < 2; i++) {
        if (n[i] > s->score[i] && s->mode[i] != STADIUM_WINNER && s->mode[i] != STADIUM_LOSER) { s->mode[i] = STADIUM_CHEER; s->t[i] = ST_CHEER_AT[i]; }
        s->score[i] = n[i];
    }
}

void stadium_wave(Stadium *s)
{
    int i;
    for (i = 0; i < 2; i++) { s->mode[i] = STADIUM_WAVE; s->t[i] = 0; }
}

void stadium_finish(Stadium *s, int winner)
{
    int i;
    for (i = 0; i < 2; i++) {
        s->t[i] = 0;
        if (winner < 0) { s->mode[i] = STADIUM_CHEER; s->t[i] = ST_CHEER_AT[i]; }
        else s->mode[i] = (uint8_t)(i == winner ? STADIUM_WINNER : STADIUM_LOSER);
    }
}

void stadium_step(Stadium *s)
{
    int i;
    for (i = 0; i < 2; i++) {
        s->t[i]++;
        if (s->mode[i] == STADIUM_CHEER && s->t[i] >= 64) { s->mode[i] = STADIUM_IDLE; s->t[i] = 0; }
        else if (s->mode[i] == STADIUM_WAVE && s->t[i] >= 64) { s->mode[i] = STADIUM_IDLE; s->t[i] = 0; }
        else if (s->t[i] == 0xFFF0) s->t[i] = (uint16_t)(s->t[i] & 0x3F);   /* every period divides 64: the wrap is invisible */
    }
}

/* near_state() of assets/stadium/draw_stadium.py: pose (0..5 = A..F) and dy of the bird at (row, col). This runs for
 * a third of the stand each game frame on a 68000 without a 32-bit divide: f (the side's step count) is never negative,
 * so the % and / by powers of two are masks and shifts (a signed % went to a slow libgcc call). */
static void near_state(uint8_t mode, int f, int r, int c, int type, signed char *pose, signed char *dy)
{
    int ph = ST_NP[r][c] - '0', team = side_of(c), q, lag = c * 2 + (2 - r) + (ph & 1);
    const signed char *e = ST_IDLE[type][((f >> 1) + ph) & 7];
    switch (mode) {
    case STADIUM_CHEER:
        q = f - ST_CHEER_AT[team] - (ph & 3);
        if (q >= 0 && q < ST_CHEER_LEN[type]) e = ST_CHEER[type][q];
        break;
    case STADIUM_WAVE:
        q = f - 4 - lag;
        if (q >= 0 && q < ST_WAVE_LEN[type]) e = ST_WAVE[type][q];
        break;
    case STADIUM_WINNER:
        q = (f - lag) & 15;   /* mod16 of a negative value too */
        if (q < ST_WAVE_LEN[type]) e = ST_WAVE[type][q];
        break;
    case STADIUM_LOSER:
        e = ST_SLUMP[0][((f >> 3) + ph) & 3];
        break;
    default: break;
    }
    *pose = e[0];
    *dy = e[1];
}

/* far_state() of the exporter for one far block: the cheer, wave and win entries depend on the block only, so they are
 * looked up once; a bird whose entry is out of range (or idle) takes its own idle phase. Same result as one lookup per bird. */
static const signed char *far_block_entry(uint8_t mode, int f, int row, int bc, int bp)
{
    static const signed char rest[2] = {0, 0};   /* the slump: pose A, no hop */
    static const uint8_t mod3[10] = {0, 1, 2, 0, 1, 2, 0, 1, 2, 0};
    int q, lag = bc * 2 + 4 + (1 - row);
    switch (mode) {
    case STADIUM_CHEER:
        q = f - ST_CHEER_AT[bc >= STADIUM_SIDE_COLS] - mod3[bp];
        return q >= 0 && q < ST_CHEER_F_LEN[0] ? ST_CHEER_F[0][q] : 0;
    case STADIUM_WAVE:
        q = f - 4 - lag;
        return q >= 0 && q < ST_WAVE_F_LEN[0] ? ST_WAVE_F[0][q] : 0;
    case STADIUM_WINNER:
        q = (f - lag) & 15;
        return q < ST_WAVE_F_LEN[0] ? ST_WAVE_F[0][q] : 0;
    case STADIUM_LOSER:
        return rest;
    default: return 0;
    }
}

static StadiumCell cell(const unsigned short *p) { StadiumCell c; c.top = p[0]; c.bot = p[1]; return c; }

StadiumCell stadium_near(const Stadium *s, int row, int col, int storm)
{
    char t = ST_NT[row][col];
    signed char pose, dy;
    int type;
    if (t == 's') return cell(ST_AISLE);
    if (t == 'e') return cell(ST_EMPTY);
    type = t - 'a';
    near_state(s->mode[side_of(col)], s->t[side_of(col)], row, col, type, &pose, &dy);
    if (storm && ST_NU[row][col] == '1') return cell(ST_UMB[dy + 10]);     /* umbrella birds hop with the umbrella */
    return cell(ST_NEAR[type][pose][dy + 10]);
}

/* Far cell lookup: ST_FAR_TILE index + 1, or FAR_NONE. An idle far cell depends on (f >> 1) & 7 only, so its result
 * is kept per cell and phase (g_far_idle, 0 = not known yet): the 4 bird lookups and the key search ran for a third of
 * the stand every game frame and pushed Gum Fling to 30 Hz (thoughts/spot/2026-11-22-fling-card.md). */

static uint8_t far_index(int row, int col, int f, const signed char *be)
{
    const unsigned char *blk = ST_BLOCK[ST_FB[row][col] - 'A'];
    int i, bp = ST_FP[row][col] - '0';
    uint8_t lo = 0, hi = ST_FAR_N;
    uint32_t key = 0;
    /* key = block | bird i << (3 + 7 i), built from bird 3 down with constant shifts (a variable 32-bit shift is slow) */
    for (i = 3; i >= 0; i--) {
        key <<= 7;
        if (blk[i] != 255) {
            const signed char *e = be ? be : ST_IDLE_F[0][((f >> 1) + blk[i] + bp) & 7];
            key |= (uint32_t)((e[0] + 1) | ((e[1] + 8) << 3));
        }
    }
    key = (key << 3) | (uint32_t)(ST_FB[row][col] - 'A');
    while (lo < hi) {
        uint8_t m = (uint8_t)((lo + hi) >> 1);
        if (ST_FAR_KEY[m] < key) lo = (uint8_t)(m + 1); else hi = m;
    }
    return lo < ST_FAR_N && ST_FAR_KEY[lo] == key ? (uint8_t)(lo + 1) : FAR_NONE;
}

static StadiumCell far_cell(uint8_t k) { StadiumCell none = {0, 0}; return k == FAR_NONE ? none : cell(ST_FAR_TILE[k - 1]); }

StadiumCell stadium_far(const Stadium *s, int row, int col)
{
    int f;
    const signed char *be;
    uint8_t *m;
    if (ST_FB[row][col] == 'S') return cell(ST_AISLE);
    f = s->t[side_of(col)];
    be = far_block_entry(s->mode[side_of(col)], f, row, col, ST_FP[row][col] - '0');
    if (be) {   /* cheer, wave, winner, loser: every bird of the block takes be, so the result depends on block and be only */
        m = &g_far_be[ST_FB[row][col] - 'A'][(be[0] + 1) | ((be[1] + 8) << 3)];
        if (!*m) *m = far_index(row, col, f, be);
        return far_cell(*m);
    }
    m = &g_far_idle[row][col][(f >> 1) & 7];
    if (!*m) *m = far_index(row, col, f, 0);
    return far_cell(*m);
}

void stadium_far_warm(int row, int col)
{
    int p;
    if (ST_FB[row][col] == 'S') return;
    for (p = 0; p < 8; p++) if (!g_far_idle[row][col][p]) g_far_idle[row][col][p] = far_index(row, col, 2 * p, 0);
}

void stadium_digit_tiles(const Stadium *s, uint16_t out[STADIUM_DIGITS])
{
    out[0] = ST_DIGIT[s->score[0] / 10]; out[1] = ST_DIGIT[s->score[0] % 10];
    out[2] = ST_DIGIT[s->score[1] / 10]; out[3] = ST_DIGIT[s->score[1] % 10];
}

int stadium_fling_x(int field_scroll)
{
    if (field_scroll < 0) field_scroll = 0;
    if (field_scroll > STADIUM_FLING_SCROLL_MAX) field_scroll = STADIUM_FLING_SCROLL_MAX;
    return -(field_scroll >> STADIUM_FLING_SHIFT);
}

static uint32_t fnv(uint32_t h, uint16_t v) { return (h ^ v) * 16777619u; }

uint32_t stadium_golden_expected(void) { return (uint32_t)ST_GOLDEN; }

/* Same order as the exporter: mood, mode (idle cheer wave win), frame, near rows then far rows; win = side 0 winner, side 1 slump. */
uint32_t stadium_golden(void)
{
    static const uint8_t M[4][2] = {{STADIUM_IDLE, STADIUM_IDLE}, {STADIUM_CHEER, STADIUM_CHEER}, {STADIUM_WAVE, STADIUM_WAVE}, {STADIUM_WINNER, STADIUM_LOSER}};
    uint32_t h = 2166136261u;
    int mood, mode, f, r, c;
    for (mood = 0; mood < 3; mood++)
        for (mode = 0; mode < 4; mode++)
            for (f = 0; f < (mode ? 64 : 16); f++) {
                Stadium s;
                stadium_reset(&s);
                s.mode[0] = M[mode][0]; s.mode[1] = M[mode][1]; s.t[0] = s.t[1] = (uint16_t)f;
                for (r = 0; r < STADIUM_NEAR_ROWS; r++)
                    for (c = 0; c < STADIUM_COLS; c++) { StadiumCell x = stadium_near(&s, r, c, mood == 2); h = fnv(h, x.top); h = fnv(h, x.bot); }
                for (r = 0; r < STADIUM_FAR_ROWS; r++)
                    for (c = 0; c < STADIUM_COLS; c++) { StadiumCell x = stadium_far(&s, r, c); h = fnv(h, x.top); h = fnv(h, x.bot); }
            }
    return h;
}
