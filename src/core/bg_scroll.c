#include "bg_scroll.h"

uint32_t bg_scroll_px(uint32_t distance, BgLayer layer)
{
    switch (layer) {
    case BG_LAYER_FAR: return distance >> 10;
    case BG_LAYER_MID: return ((distance >> 4) * 9u) >> 8;
    case BG_LAYER_ROOF: return distance >> 8;
    default: return 0;
    }
}

uint32_t bg_first_col(uint32_t scroll_px) { return scroll_px / BG_COL_PX; }

uint32_t bg_ring_slot(uint32_t world_col) { return world_col % BG_RING; }

/* No `%` here: on the 68000 a 32-bit modulo is a libgcc __umodsi3 call (hundreds of cycles). The per-frame
 * loop in src/bg.c calls this 3 x BG_RING times; with two `%` per call it took about a third of the frame and
 * the main loop ran at 30 Hz (make test-vblank, frame step check). first_slot = bg_ring_slot(first), once per layer. */
uint32_t bg_slot_world_col_at(uint32_t first, uint32_t first_slot, uint32_t slot)
{
    uint32_t d = slot + BG_RING - first_slot;
    if (d >= BG_RING) d -= BG_RING;
    return first + d;
}

uint32_t bg_slot_world_col(uint32_t first, uint32_t slot)
{
    return bg_slot_world_col_at(first, bg_ring_slot(first), slot);
}

int32_t bg_slot_x(uint32_t scroll_px, uint32_t world_col)
{
    return (int32_t)(world_col * BG_COL_PX) - (int32_t)scroll_px;
}

uint32_t bg_art_col(uint32_t world_col) { return world_col % BG_ART_COLS; }

uint32_t bg_columns_to_write(uint32_t prev, uint32_t now, int prev_valid)
{
    if (!prev_valid) return BG_RING;
    if (now == prev) return 0;
    if (now == prev + 1) return 1;
    return BG_RING;
}
