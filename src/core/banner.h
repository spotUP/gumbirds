/* Round clear banner panel (fix layer), a pure per-frame cell function. Spec: thoughts/shared/drafts/
 * 2026-11-10-round-clear-banner-final2/banner_spec.txt. The panel is BANNER_W x BANNER_H cells at (BANNER_COL, BANNER_ROW) and
 * keeps that size the whole time; the host writes banner_cell only for the panel rows banner_dirty_rows says can have changed
 * since the previous frame (the vram queue shadow still keeps only the changes). A cell value is (palette << 12) | tile, the form gfx_fix_tile takes. Cells not drawn yet,
 * and cells outside the panel, are (FIXFONT_PAL_WHITE << 12) | FIXFONT_BLANK. */
#ifndef CORE_BANNER_H
#define CORE_BANNER_H
#include <stdint.h>

#define BANNER_COL 9
#define BANNER_ROW 10
#define BANNER_W 22
#define BANNER_H 8

#define BANNER_LAST 1
#define BANNER_STAGE 2
#define BANNER_BONUS 4

enum BannerWinner { BANNER_P1 = 0, BANNER_P2, BANNER_CPU, BANNER_DRAW };

typedef struct {
    uint8_t winner;  /* BannerWinner */
    uint16_t round;  /* the round that starts next, shown as ROUND nn (1..99) */
    uint8_t last;    /* BANNER_* flags: 0 = ROUND nn; BANNER_LAST: MATCH OVER replaces it; BANNER_STAGE / BANNER_BONUS: the 5 letter word is STAGE / BONUS (arcade) */
} BannerCtx;

/* Bit r (0..BANNER_H-1) set: some cell of panel row r can differ between frame - 1 and frame, for any BannerCtx.
 * A superset is allowed, a missing row is not. Frame 0 (and the interior reveal on frames 1 and 2) returns every row. */
uint8_t banner_dirty_rows(uint16_t frame);

uint16_t banner_cell(uint16_t frame, const BannerCtx *ctx, uint8_t col, uint8_t row);

#endif
