#include "stadium.h"
#include "gen/stadium_motion.h"

static uint8_t side_of(int col) { return (uint8_t)(col >= STADIUM_SIDE_COLS); }

static int mod16(int v) { return ((v % 16) + 16) % 16; }

void stadium_reset(Stadium *s)
{
    int i;
    for (i = 0; i < 2; i++) { s->mode[i] = STADIUM_IDLE; s->t[i] = 0; s->score[i] = 0; }
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

/* near_state() of assets/stadium/draw_stadium.py: pose (0..5 = A..F) and dy of the bird at (row, col). */
static void near_state(uint8_t mode, int f, int r, int c, int type, signed char *pose, signed char *dy)
{
    int ph = ST_NP[r][c] - '0', team = side_of(c), q, lag = c * 2 + (2 - r) + ph % 2;
    const signed char *e = ST_IDLE[type][(f / 2 + ph) % 8];
    switch (mode) {
    case STADIUM_CHEER:
        q = f - ST_CHEER_AT[team] - ph % 4;
        if (q >= 0 && q < ST_CHEER_LEN[type]) e = ST_CHEER[type][q];
        break;
    case STADIUM_WAVE:
        q = f - 4 - lag;
        if (q >= 0 && q < ST_WAVE_LEN[type]) e = ST_WAVE[type][q];
        break;
    case STADIUM_WINNER:
        q = mod16(f - lag);
        if (q < ST_WAVE_LEN[type]) e = ST_WAVE[type][q];
        break;
    case STADIUM_LOSER:
        e = ST_SLUMP[0][(f / 8 + ph) % 4];
        break;
    default: break;
    }
    *pose = e[0];
    *dy = e[1];
}

static void far_state(uint8_t mode, int f, int row, int bc, int ph, signed char *pose, signed char *dy)
{
    int team = bc >= STADIUM_SIDE_COLS, bp = ST_FP[row][bc] - '0', q, lag = bc * 2 + 4 + (1 - row);
    const signed char *e = ST_IDLE_F[0][(f / 2 + ph + bp) % 8], rest[2] = {0, 0};   /* the slump: pose A, no hop */
    switch (mode) {
    case STADIUM_CHEER:
        q = f - ST_CHEER_AT[team] - bp % 3;
        if (q >= 0 && q < ST_CHEER_F_LEN[0]) e = ST_CHEER_F[0][q];
        break;
    case STADIUM_WAVE:
        q = f - 4 - lag;
        if (q >= 0 && q < ST_WAVE_F_LEN[0]) e = ST_WAVE_F[0][q];
        break;
    case STADIUM_WINNER:
        q = mod16(f - lag);
        if (q < ST_WAVE_F_LEN[0]) e = ST_WAVE_F[0][q];
        break;
    case STADIUM_LOSER:
        e = rest;
        break;
    default: break;
    }
    *pose = e[0];
    *dy = e[1];
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

StadiumCell stadium_far(const Stadium *s, int row, int col)
{
    char name = ST_FB[row][col];
    uint32_t key, lo = 0, hi = ST_FAR_N;
    int i;
    StadiumCell none = {0, 0};
    if (name == 'S') return cell(ST_AISLE);
    key = (uint32_t)(name - 'A');
    for (i = 0; i < 4; i++) {
        signed char pose, dy;
        if (ST_BLOCK[name - 'A'][i] == 255) continue;
        far_state(s->mode[side_of(col)], s->t[side_of(col)], row, col, ST_BLOCK[name - 'A'][i], &pose, &dy);
        key |= (uint32_t)((pose + 1) | ((dy + 8) << 3)) << (3 + 7 * i);
    }
    while (lo < hi) {
        uint32_t m = (lo + hi) / 2;
        if (ST_FAR_KEY[m] < key) lo = m + 1; else hi = m;
    }
    if (lo < ST_FAR_N && ST_FAR_KEY[lo] == key) return cell(ST_FAR_TILE[lo]);
    return none;
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
