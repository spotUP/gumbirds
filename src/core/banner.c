#include "banner.h"
#include "gen/fix_font.h"

/* Timeline constants are spec data (banner_spec.txt TIMELINE), not tuning knobs. */
#define LETTERS 10
#define LETTER_FIRST 4      /* headline letter n starts at 4 + 4n: bubble, burst, white, pink, 4 frames each */
#define LETTER_STEP 4
#define WINNER_WHITE 56     /* winner line appears white */
#define WINNER_OWN 60       /* ... and takes the winner's palette */
#define LINE3_START 68      /* ROUND nn / MATCH OVER appears */
#define LINE3_GOLD_A 76     /* palette swaps: white 68, gold 76, white 84, gold 92 on */
#define LINE3_WHITE_B 84
#define LINE3_GOLD_B 92
#define HEAD_ROW 11
#define RULE_ROW 12
#define WIN_ROW 13

#define CELL(pal, tile) ((uint16_t)(((pal) << 12) | (tile)))
#define BACKED_LETTER(ch) (FIXFONT_BACKED + FIXFONT_LETTER_A + ((ch) - 'A'))
#define BACKED_PUNCT(k) (FIXFONT_BACKED + FIXFONT_PUNCT_FIRST + (k))   /* k: 0 '.', 3 '!', 5 '-' */

static const uint8_t head_col[LETTERS] = {10, 12, 14, 17, 19, 21, 23, 25, 27, 29};
static const char head_text[LETTERS + 1] = "ALLPOPPED!";

/* Tile of one string character; ' ' is the plate. '<' '>' are the two Sootling icon halves. */
static uint16_t glyph(char ch)
{
    if (ch == '<') return FIXFONT_BACKED + FIXFONT_ICON_SOOT_LEFT;
    if (ch == '>') return FIXFONT_BACKED + FIXFONT_ICON_SOOT_RIGHT;
    if (ch == '!') return BACKED_PUNCT(3);
    if (ch >= '0' && ch <= '9') return (uint16_t)(FIXFONT_BACKED + FIXFONT_DIGIT_0 + (ch - '0'));
    if (ch >= 'A' && ch <= 'Z') return (uint16_t)BACKED_LETTER(ch);
    return FIXFONT_PLATE_FILL;
}

/* Character of text (drawn from column start) at col, or 0 outside it. */
static char text_at(const char *text, uint8_t start, uint8_t col)
{
    uint8_t i;
    if (col < start) return 0;
    for (i = 0; text[i]; i++) {
        if (i == col - start) return text[i];
    }
    return 0;
}

static uint16_t waiting_dash(uint8_t col)
{
    return (col >= 18 && col <= 21) ? CELL(FIXFONT_PAL_DIM, BACKED_PUNCT(5)) : CELL(FIXFONT_PAL_PINK, FIXFONT_PLATE_FILL);
}

static uint16_t headline(uint16_t frame, uint8_t col)
{
    uint8_t n, d;
    for (n = 0; n < LETTERS && head_col[n] != col; n++) {}
    if (n == LETTERS) return CELL(FIXFONT_PAL_PINK, FIXFONT_PLATE_FILL);
    if (frame < LETTER_FIRST + LETTER_STEP * n) return CELL(FIXFONT_PAL_DIM, BACKED_PUNCT(0));
    d = (uint8_t)((frame - (LETTER_FIRST + LETTER_STEP * n)) / LETTER_STEP);
    if (d == 0) return CELL(FIXFONT_PAL_PINK, FIXFONT_ICON_GUM + FIXFONT_BACKED);
    if (d == 1) return CELL(FIXFONT_PAL_PINK, FIXFONT_POP_BURST);
    return CELL(d == 2 ? FIXFONT_PAL_WHITE : FIXFONT_PAL_PINK, glyph(head_text[n]));
}

static uint16_t winner_line(uint16_t frame, const BannerCtx *ctx, uint8_t col)
{
    static const char *const text[4] = {"<> PLAYER 1 WINS", "<> PLAYER 2 WINS", "<> COMPUTER WINS", "NO SURVIVORS"};
    static const uint8_t pal[4] = {FIXFONT_PAL_PINK, FIXFONT_PAL_LIME, FIXFONT_PAL_WHITE, FIXFONT_PAL_DIM};
    uint8_t w = ctx->winner > BANNER_DRAW ? BANNER_DRAW : ctx->winner;
    char ch;
    if (frame < WINNER_WHITE) return waiting_dash(col);
    ch = text_at(text[w], w == BANNER_DRAW ? 14 : 12, col);
    if (!ch || ch == ' ') return CELL(FIXFONT_PAL_PINK, FIXFONT_PLATE_FILL);
    return CELL(frame < WINNER_OWN ? FIXFONT_PAL_WHITE : pal[w], glyph(ch));
}

/* Line 3: ROUND nn (letters on row 16, tall digits on rows 15 and 16) or MATCH OVER (row 15). */
static uint16_t line3(uint16_t frame, const BannerCtx *ctx, uint8_t col, uint8_t row)
{
    uint8_t pal = (frame < LINE3_GOLD_A || (frame >= LINE3_WHITE_B && frame < LINE3_GOLD_B)) ? FIXFONT_PAL_WHITE : FIXFONT_PAL_GOLD;
    uint8_t text_row = ctx->last ? 15 : 16;
    char ch;
    if (frame < LINE3_START) return row == text_row ? waiting_dash(col) : CELL(FIXFONT_PAL_PINK, FIXFONT_PLATE_FILL);
    if (ctx->last) {
        ch = row == 15 ? text_at("MATCH OVER", 15, col) : 0;
    } else if (col >= 22 && col <= 23 && (row == 15 || row == 16)) {
        uint16_t r = ctx->round < 1 ? 1 : ctx->round > 99 ? 99 : ctx->round;
        uint8_t digit = (uint8_t)(col == 22 ? r / 10 : r % 10);
        return CELL(pal, (row == 15 ? FIXFONT_TALL_BACKED + FIXFONT_TALL_TOP : FIXFONT_TALL_BACKED + FIXFONT_TALL_BOTTOM) + digit);
    } else {
        ch = row == 16 ? text_at("ROUND", 16, col) : 0;
    }
    if (!ch || ch == ' ') return CELL(FIXFONT_PAL_PINK, FIXFONT_PLATE_FILL);
    return CELL(pal, glyph(ch));
}

uint16_t banner_cell(uint16_t frame, const BannerCtx *ctx, uint8_t col, uint8_t row)
{
    uint8_t c, r;
    if (col < BANNER_COL || col >= BANNER_COL + BANNER_W || row < BANNER_ROW || row >= BANNER_ROW + BANNER_H) {
        return CELL(FIXFONT_PAL_WHITE, FIXFONT_BLANK);
    }
    c = (uint8_t)(col - BANNER_COL);
    r = (uint8_t)(row - BANNER_ROW);
    if (r == 0 || r == BANNER_H - 1 || c == 0 || c == BANNER_W - 1) {
        /* outline on frame 0 (corners, edges) */
        uint8_t top = (uint8_t)(r == 0 ? 0 : r == BANNER_H - 1 ? 2 : 1);
        uint8_t left = (uint8_t)(c == 0 ? 0 : c == BANNER_W - 1 ? 2 : 1);
        static const uint8_t tile[3][3] = {
            {FIXFONT_FRAME_TL, FIXFONT_FRAME_T, FIXFONT_FRAME_TR},
            {FIXFONT_FRAME_L, FIXFONT_PLATE_FILL, FIXFONT_FRAME_R},
            {FIXFONT_FRAME_BL, FIXFONT_FRAME_B, FIXFONT_FRAME_BR}};
        return CELL(FIXFONT_PAL_PINK, tile[top][left]);
    }
    if (frame < ((c - 1) % 2 == 0 ? 1 : 2)) return CELL(FIXFONT_PAL_WHITE, FIXFONT_BLANK); /* interior: even panel columns on frame 1, odd on 2 */
    if (row == HEAD_ROW) return headline(frame, col);
    if (row == RULE_ROW && col >= 11 && col <= 28) return CELL(FIXFONT_PAL_PINK, FIXFONT_RULE);
    if (row == WIN_ROW) return winner_line(frame, ctx, col);
    if (row == 15 || row == 16) return line3(frame, ctx, col, row);
    return CELL(FIXFONT_PAL_PINK, FIXFONT_PLATE_FILL);
}

/* Rows are named by the screen row constants above, so a timeline edit above is the only place to change. */
uint8_t banner_dirty_rows(uint16_t frame)
{
    uint8_t m = 0;
    if (frame < 3) return (uint8_t)((1 << BANNER_H) - 1);   /* outline on 0, interior reveal on 1 and 2 */
    if (frame >= LETTER_FIRST && frame <= LETTER_FIRST + LETTER_STEP * (LETTERS - 1) + 3 * LETTER_STEP &&
        (frame - LETTER_FIRST) % LETTER_STEP == 0) m |= 1 << (HEAD_ROW - BANNER_ROW);
    if (frame == WINNER_WHITE || frame == WINNER_OWN) m |= 1 << (WIN_ROW - BANNER_ROW);
    if (frame == LINE3_START || frame == LINE3_GOLD_A || frame == LINE3_WHITE_B || frame == LINE3_GOLD_B) {
        m |= 1 << (15 - BANNER_ROW);   /* line3 rows: 15 and 16 */
        m |= 1 << (16 - BANNER_ROW);
    }
    return m;
}
