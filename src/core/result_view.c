#include "result_view.h"
#include "gen/fix_font.h"

#define CELL(pal, tile) ((uint16_t)(((pal) << 12) | (tile)))
#define RT(k) (FIXFONT_RES_BASE + (k))
enum { T_STRIPE, T_CAGE_EDGE, T_CAGE_FILL, T_PIPE, T_MACH_EDGE, T_MACH_FILL, T_BUB, T_GHOST = T_BUB + 4 };

static uint16_t scene(int tile) { return CELL(FIXFONT_PAL_RES_SCENE, RT(tile)); }

/* Text cell on its navy plate; ' ' is the bare plate. */
static uint16_t text(uint8_t pal, char ch)
{
    return CELL(pal, ch == ' ' ? FIXFONT_PLATE_FILL : fixfont_map_backed[(uint8_t)ch]);
}

/* Right-aligned decimal of v in w chars, leading zeros blank unless zero_pad.
 * Digits by subtracting powers of ten (as put_number in main.c): this runs per cell per frame, and a
 * 32-bit `/` or `%` is a libgcc call (__udivsi3) on the 68000. More digits than w keep the low ones. */
static const uint32_t POW10[10] = { 1000000000u, 100000000u, 10000000u, 1000000u, 100000u, 10000u, 1000u, 100u, 10u, 1u };
static char digit_at(uint32_t v, uint8_t w, uint8_t i, uint8_t zero_pad)
{
    uint8_t want = (uint8_t)(10u - (w - i)); /* POW10 index of this cell's place */
    uint8_t k;
    char c = '0';
    if (!zero_pad && i + 1u < w && v < POW10[want]) return ' ';
    for (k = 0; k <= want; k++) {
        c = '0';
        while (v >= POW10[k]) { v -= POW10[k]; c++; }
    }
    return c;
}

static uint16_t num_cell(uint8_t pal, uint32_t v, uint8_t w, uint8_t i, uint8_t zero_pad) { return text(pal, digit_at(v, w, i, zero_pad)); }

static uint8_t in(uint8_t v, uint8_t a, uint8_t b) { return v >= a && v <= b; }

/* Text of fixed string s starting at column c0; 0 when the cell is outside. */
static int str_cell(const char *s, uint8_t c0, uint8_t col)
{
    uint8_t n = 0;
    while (s[n]) n++;
    return in(col, c0, (uint8_t)(c0 + n - 1)) ? s[col - c0] : 0;
}

static uint16_t cage_cell(const Result *r, uint8_t col, uint8_t row)
{
    uint8_t slot = (uint8_t)((row - 8) / 2 * 5 + (col - 4) / 2);
    uint8_t sub = (uint8_t)(((row - 8) & 1) * 2 + ((col - 4) & 1));
    if (slot >= r->caught) return CELL(FIXFONT_PAL_RES_DARK, RT(T_BUB + sub));
    if (r->ticket) return CELL(FIXFONT_PAL_RES_GOLD, RT(T_BUB + sub));
    if (r->vanished) return CELL(FIXFONT_PAL_RES_GHOST, RT(T_GHOST + sub));
    return CELL(FIXFONT_PAL_RES_PINK, RT(T_BUB + sub));
}

static uint16_t machine_cell(const Result *r, uint8_t col, uint8_t row)
{
    int ch;
    if (r->show & RES_SHOW_TOTAL) {
        uint32_t tot = r->total_left;
        if (in(row, 11, 12) && in(col, 28, 32)) {
            uint8_t i = (uint8_t)(col - 28);
            char d = digit_at(tot, 5, i, 0);
            if (d == ' ') return text(FIXFONT_PAL_GOLD, ' ');
            return CELL(FIXFONT_PAL_GOLD, (row == 11 ? FIXFONT_TALL_TOP : FIXFONT_TALL_BOTTOM) + FIXFONT_TALL_BACKED + (d - '0'));
        }
        if (row == 14 && in(col, 27, 34)) {  /* "NN X MMM" */
            uint8_t i = (uint8_t)(col - 27);
            if (i < 2) return num_cell(FIXFONT_PAL_PINK, r->caught, 2, i, 0);
            if (i == 2) return text(FIXFONT_PAL_PINK, ' ');
            if (i == 3) return text(FIXFONT_PAL_PINK, 'X');
            if (i == 4) return text(FIXFONT_PAL_PINK, ' ');
            return num_cell(FIXFONT_PAL_PINK, r->each, 3, (uint8_t)(i - 5), 0);
        }
    }
    ch = row == 9 ? str_cell("TOTAL", 28, col) : 0;
    if (ch) return text(FIXFONT_PAL_GOLD, (char)ch);
    return CELL(FIXFONT_PAL_RES_SCENE, RT(T_MACH_FILL));
}

static uint16_t ticket_cell(const Result *r, uint8_t col, uint8_t row)
{
    int ch;
    if (!r->ticket) return scene(T_STRIPE);
    if (row == 21 || row == 25 || col == 7 || col == 32) {
        uint16_t t = row == 21 ? (col == 7 ? FIXFONT_FRAME_TL : col == 32 ? FIXFONT_FRAME_TR : FIXFONT_FRAME_T)
                  : row == 25 ? (col == 7 ? FIXFONT_FRAME_BL : col == 32 ? FIXFONT_FRAME_BR : FIXFONT_FRAME_B)
                  : (col == 7 ? FIXFONT_FRAME_L : FIXFONT_FRAME_R);
        return CELL(FIXFONT_PAL_GOLD, t);
    }
    if (row == 22) ch = str_cell("PERFECT", 16, col);
    else if (row == 24) ch = str_cell("ALL 20 BUBBLES POPPED", 10, col);
    else {
        ch = str_cell("BONUS ", 14, col);
        if (!ch && in(col, 20, 24)) return num_cell(FIXFONT_PAL_GOLD, r->bonus, 5, (uint8_t)(col - 20), 0);
    }
    return text(row == 24 ? FIXFONT_PAL_WHITE : FIXFONT_PAL_GOLD, ch ? (char)ch : ' ');
}

uint16_t result_cell(const Result *r, uint8_t col, uint8_t row)
{
    int ch;
    if (row == 2) {
        ch = str_cell("BONUS STAGE", 14, col);
        if (ch) return text(FIXFONT_PAL_GOLD, (char)ch);
    } else if (row == 4) {
        if ((r->show & RES_SHOW_POPPED) && in(col, 10, 18)) {  /* "NN POPPED" */
            uint8_t i = (uint8_t)(col - 10);
            return i < 2 ? num_cell(FIXFONT_PAL_WHITE, r->caught, 2, i, 0) : text(FIXFONT_PAL_WHITE, " POPPED"[i - 2]);
        }
        if ((r->show & RES_SHOW_EACH) && in(col, 22, 29)) {  /* "MMM EACH" */
            uint8_t i = (uint8_t)(col - 22);
            return i < 3 ? num_cell(FIXFONT_PAL_WHITE, r->each, 3, i, 0) : text(FIXFONT_PAL_WHITE, " EACH"[i - 3]);
        }
    } else if (in(row, 7, 16)) {
        if (in(col, 3, 14)) {
            if (row == 7 || row == 16 || col == 3 || col == 14) return scene(T_CAGE_EDGE);
            return cage_cell(r, col, row);
        }
        if (in(col, 15, 24) && in(row, 11, 11)) return scene(T_PIPE);
        if (in(col, 25, 36)) {
            if (row == 7 || row == 16 || col == 25 || col == 36) return scene(T_MACH_EDGE);
            return machine_cell(r, col, row);
        }
    } else if (row == 18 && in(col, 6, 33)) {
        return scene(T_CAGE_EDGE);
    } else if (row == 19) {
        ch = str_cell("SCORE", 12, col);
        if (ch) return text(FIXFONT_PAL_WHITE, (char)ch);
        if (in(col, 19, 26)) return num_cell(FIXFONT_PAL_PINK, r->score_shown, 8, (uint8_t)(col - 19), 1);
    } else if (in(row, 21, 25) && in(col, 7, 32)) {
        return ticket_cell(r, col, row);
    }
    return scene(T_STRIPE);
}

void result_region(uint8_t bit, uint8_t *row0, uint8_t *row1, uint8_t *col0, uint8_t *col1)
{
    switch (bit) {
    case RES_DIRTY_POPPED: *row0 = *row1 = 4; *col0 = 10; *col1 = 29; break;
    case RES_DIRTY_CAGE: *row0 = 8; *row1 = 15; *col0 = 4; *col1 = 13; break;
    case RES_DIRTY_MACHINE: *row0 = 9; *row1 = 14; *col0 = 26; *col1 = 35; break;
    case RES_DIRTY_SCORE: *row0 = *row1 = 19; *col0 = 12; *col1 = 26; break;
    default: *row0 = 21; *row1 = 25; *col0 = 7; *col1 = 32; break;
    }
}
