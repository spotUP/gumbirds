#ifndef BG_SCROLL_H
#define BG_SCROLL_H
/*
 * City background scroll math (pure, host tested). Each layer is a ring of BG_RING sprite columns
 * over an art strip of BG_ART_COLS columns (320 px period). World column w sits in ring slot
 * w % BG_RING and shows art column w % BG_ART_COLS at screen x = 16 * w - scroll.
 * Scroll is a pure function of distance (8.8 px). src/bg.c passes the distance of all runs so far, so the scroll
 * continues across runs (a jump back would redraw every column, more than one vblank flush).
 * Rates are fixed art ratios (far 1/4, mid 9/16, roof 1 of the ground speed), not gameplay knobs,
 * so they live here and not in tuning.h (written exemption, plan 2026-11-09-city-background.md).
 */
#include <stdint.h>

#define BG_ART_COLS 20
#define BG_RING 21         /* 20 columns + 1 so the entering column is written off screen */
#define BG_COL_PX 16

typedef enum { BG_LAYER_FAR = 0, BG_LAYER_MID = 1, BG_LAYER_ROOF = 2, BG_LAYER_COUNT = 3 } BgLayer;

/* Unreduced scroll in whole pixels. far = d/4, mid = d*9/16, roof = d (d in px). */
uint32_t bg_scroll_px(uint32_t distance, BgLayer layer);
/* First world column that touches the screen. */
uint32_t bg_first_col(uint32_t scroll_px);
/* World column that ring slot `slot` holds when `first` is the first visible column. */
uint32_t bg_slot_world_col(uint32_t first, uint32_t slot);
/* Ring slot of a world column (w % BG_RING). */
uint32_t bg_ring_slot(uint32_t world_col);
/* bg_slot_world_col with first_slot = bg_ring_slot(first) computed once by the caller (per-frame loop, no divide). */
uint32_t bg_slot_world_col_at(uint32_t first, uint32_t first_slot, uint32_t slot);
/* Screen x of world column w (may be negative for the partly hidden first column). */
int32_t bg_slot_x(uint32_t scroll_px, uint32_t world_col);
/* Art column (0..BG_ART_COLS-1) shown by world column w. */
uint32_t bg_art_col(uint32_t world_col);
/* Columns that must be (re)written when the first visible column goes from `prev` to `now`:
   0 = nothing, 1 = only world column now + BG_RING - 1, BG_RING = redraw all. */
uint32_t bg_columns_to_write(uint32_t prev, uint32_t now, int prev_valid);

#endif
