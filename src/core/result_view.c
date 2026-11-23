#include "result_view.h"
#include "flow.h"
#include "gen/fix_font.h"
#include "gen/result_scene.h"

#define CELL(pal, tile) ((uint16_t)(((pal) << 12) | (tile)))

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

/* Text plates over the scene: the cell of string or blank plate. */
static uint16_t plate(uint8_t pal, int ch) { return text(pal, ch ? (char)ch : ' '); }

/* Podium screen of a Gum Games event (owner pick B 2026-11-23), fix layer part: event title, winner banner, player names, unit letter, record line.
 * Every glyph is transparent and every other cell is blank: the stadium and the podium sprites (main.c podium_step) show behind. Rows are the draft's rows. */
static int centered(const char *s, uint8_t col)
{
    uint8_t n = 0;
    while (s[n]) n++;
    return str_cell(s, (uint8_t)((RESV_W - n) / 2), col);
}

uint8_t resv_digits(uint32_t v)
{
    uint8_t n = 1;
    while (n < RESV_POD_DIGITS && v >= POW10[10 - n - 1]) n++;
    return n;
}

uint8_t resv_digit(uint32_t v, uint8_t w, uint8_t i) { return (uint8_t)(digit_at(v, w, i, 1) - '0'); }

static uint16_t glyph(uint8_t pal, int ch) { return ch && ch != ' ' ? CELL(pal, fixfont_map[(uint8_t)ch]) : CELL(0, FIXFONT_BLANK); }

static uint16_t podium_cell(const Result *r, uint8_t col, uint8_t row)
{
    static const char unit[3] = { 0, 'M', 'S' };
    uint8_t two = (uint8_t)(r->two || r->cpu);
    uint8_t tie = r->winner == RES_WIN_TIE;
    if (row == 1) return glyph(FIXFONT_PAL_WHITE, centered(r->ev ? flow_menu_name((uint8_t)(r->ev - 1)) : "RESULT", col));
    if (row == 3) return glyph(FIXFONT_PAL_GOLD, centered(tie ? "TIE" : r->winner == RES_WIN_P1 ? (two ? "PLAYER 1 WINS" : "WELL DONE") : r->cpu ? "THE COMPUTER WINS" : "PLAYER 2 WINS", col));
    if (row == 21) {
        int ch = str_cell("PLAYER 1", 3, col);
        if (ch) return glyph(tie || r->winner == RES_WIN_P1 ? FIXFONT_PAL_GOLD : FIXFONT_PAL_DIM, ch);
        if (two) return glyph(tie || r->winner == RES_WIN_P2 ? FIXFONT_PAL_GOLD : FIXFONT_PAL_DIM, str_cell(r->cpu ? "COMPUTER" : "PLAYER 2", 29, col));
    }
    if (row == 24 && unit[r->unit]) {   /* unit letter right after the sprite digits (centred on RESV_POD_CX1 / CX2) */
        if (col == RESV_POD_CX1 / 8 + resv_digits(r->score_shown)) return glyph(FIXFONT_PAL_WHITE, unit[r->unit]);
        if (two && col == RESV_POD_CX2 / 8 + resv_digits(r->score2)) return glyph(FIXFONT_PAL_WHITE, unit[r->unit]);
    }
    if (row == 26 && r->record != RES_REC_NONE) {
        char line[20] = "NEW RECORD";
        if (r->record == RES_REC_HELD) {
            uint8_t n = 0;
            for (const char *w = "RECORD "; *w; w++) line[n++] = *w;
            for (uint8_t k = 0; k < 6; k++) { char d = digit_at(r->record_val, 6, k, 0); if (d != ' ') line[n++] = d; }
            if (unit[r->unit]) { line[n++] = ' '; line[n++] = unit[r->unit]; }
            line[n] = 0;
        }
        return glyph(r->record == RES_REC_NEW ? FIXFONT_PAL_LIME : FIXFONT_PAL_WHITE, centered(line, col));
    }
    return CELL(0, FIXFONT_BLANK);
}

/* The scene (gen/result_scene.h) with the text plates on it. The cells of the four windows (cage, counter, crank, ticket)
 * are blank: the sprites behind the fix layer show there. The ticket text has no plate, the ticket sprite is its paper. */
uint16_t result_cell(const Result *r, uint8_t col, uint8_t row)
{
    if (r->podium) return podium_cell(r, col, row);
    int ch = 0;
    if (row == 2 && in(col, 13, 25)) {
        const char *t = r->ev ? flow_menu_name((uint8_t)(r->ev - 1)) : "BONUS STAGE";
        uint8_t len = 0;
        while (t[len]) len++;
        return plate(FIXFONT_PAL_GOLD, str_cell(t, (uint8_t)(13 + (len < 13 ? (13 - len) / 2 : 0)), col));  /* centred on the 13-cell plate */
    }
    if (row == 4 && in(col, 9, 30)) {
        if ((r->show & RES_SHOW_POPPED) && in(col, 10, 18)) {  /* "NN POPPED" */
            uint8_t i = (uint8_t)(col - 10);
            return i < 2 ? num_cell(FIXFONT_PAL_WHITE, r->caught, 2, i, 0) : text(FIXFONT_PAL_WHITE, " POPPED"[i - 2]);
        }
        if ((r->show & RES_SHOW_EACH) && in(col, 22, 29)) {  /* "MMM EACH" */
            uint8_t i = (uint8_t)(col - 22);
            return i < 3 ? num_cell(FIXFONT_PAL_WHITE, r->each, 3, i, 0) : text(FIXFONT_PAL_WHITE, " EACH"[i - 3]);
        }
        return plate(FIXFONT_PAL_WHITE, 0);
    }
    if (row == 7 && in(col, 27, 33)) return plate(FIXFONT_PAL_GOLD, r->ev ? 0 : str_cell("TOTAL", 28, col));  /* a minigame has no tally */
    if (row == 13 && in(col, 25, 32)) {  /* "NN X MMM" */
        uint8_t i = (uint8_t)(col - 25);
        if (!(r->show & RES_SHOW_TOTAL)) return plate(FIXFONT_PAL_PINK, 0);
        if (i < 2) return num_cell(FIXFONT_PAL_PINK, r->caught, 2, i, 0);
        if (i < 5) return plate(FIXFONT_PAL_PINK, i == 3 ? 'X' : 0);
        return num_cell(FIXFONT_PAL_PINK, r->each, 3, (uint8_t)(i - 5), 0);
    }
    if (row == 20 && r->two && in(col, 11, 27)) {
        if (in(col, 19, 26)) return num_cell(FIXFONT_PAL_PINK, r->score2, 8, (uint8_t)(col - 19), 1);
        return plate(FIXFONT_PAL_WHITE, str_cell("PLAYER 2", 11, col));
    }
    if (row == 19 && in(col, 11, 27)) {
        if (r->two && !in(col, 19, 26)) return plate(FIXFONT_PAL_WHITE, str_cell("PLAYER 1", 11, col));
        if (in(col, 19, 26)) return num_cell(FIXFONT_PAL_PINK, r->score_shown, 8, (uint8_t)(col - 19), 1);
        return plate(FIXFONT_PAL_WHITE, str_cell("SCORE", 12, col));
    }
    if (row == 22 && r->lines >= 1) ch = str_cell("PERFECT", 16, col);
    else if (row == 24 && r->lines >= 2) ch = str_cell("ALL 20 BUBBLES POPPED", 10, col);
    else if (row == 23 && r->ticket == 2) {
        ch = str_cell("BONUS", 14, col);
        if (in(col, 20, 24)) ch = digit_at(r->bonus, 5, (uint8_t)(col - 20), 0);
    }
    if (ch && ch != ' ') return CELL(row == 24 ? FIXFONT_PAL_WHITE : FIXFONT_PAL_GOLD, fixfont_map[(uint8_t)ch]);
    return result_scene_map[row * RESV_W + col];
}

void result_region(uint8_t bit, uint8_t *row0, uint8_t *row1, uint8_t *col0, uint8_t *col1)
{
    switch (bit) {
    case RES_DIRTY_POPPED: *row0 = *row1 = 4; *col0 = 10; *col1 = 29; break;
    case RES_DIRTY_MACHINE: *row0 = *row1 = 13; *col0 = 25; *col1 = 32; break;
    case RES_DIRTY_SCORE: *row0 = 19; *row1 = 20; *col0 = 11; *col1 = 26; break;
    default: *row0 = 22; *row1 = 24; *col0 = 10; *col1 = 30; break; /* ticket text (and the unused cage bit) */
    }
}
