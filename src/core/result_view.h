/* Result screen look C "Gum machine" as a pure fix-layer cell function: every one of the 40 x 28 cells is opaque (it covers the
 * arena below). A cell value is (palette << 12) | tile, the form gfx_fix_tile takes. The region a RES_DIRTY_* bit covers
 * is given by result_region: the host redraws a region when its bit is set. Layout in cells:
 * title row 2; popped line row 4; cage 3..14 x 7..16 (5 x 4 bubbles of 2 x 2 cells), pipe, machine 25..36 x 7..16;
 * rule row 18; score row 19; ticket 7..32 x 21..25. */
#ifndef CORE_RESULT_VIEW_H
#define CORE_RESULT_VIEW_H
#include <stdint.h>
#include "result.h"

#define RESV_W 40
#define RESV_H 28

uint16_t result_cell(const Result *r, uint8_t col, uint8_t row);
/* Rows and columns (inclusive) of the region of one RES_DIRTY_* bit. */
void result_region(uint8_t bit, uint8_t *row0, uint8_t *row1, uint8_t *col0, uint8_t *col1);

#endif
