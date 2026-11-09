/* Host tests for the city background scroll math (src/core/bg_scroll.c). */
#include <stdio.h>
#include "../../src/core/bg_scroll.h"

static int failures, checks;
#define CHECK(c) do { checks++; if (!(c)) { failures++; printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

int main(void)
{
    uint32_t d, slot, seen[BG_RING];
    /* rates: roof 1 px per 256 distance units, far quarter, mid 9/16 */
    d = 1000u << 8;
    CHECK(bg_scroll_px(d, BG_LAYER_ROOF) == 1000);
    CHECK(bg_scroll_px(d, BG_LAYER_FAR) == 250);
    CHECK(bg_scroll_px(d, BG_LAYER_MID) == 562);
    CHECK(bg_scroll_px(0, BG_LAYER_FAR) == 0 && bg_scroll_px(0, BG_LAYER_MID) == 0 && bg_scroll_px(0, BG_LAYER_ROOF) == 0);
    /* monotone, step at most 1 px per 8.8 pixel of travel */
    {
        uint32_t last[3] = {0, 0, 0};
        int l, ok = 1;
        for (d = 0; d < (4000u << 8); d += 77) {
            for (l = 0; l < 3; l++) {
                uint32_t s = bg_scroll_px(d, (BgLayer)l);
                if (s < last[l] || s - last[l] > 1) ok = 0;
                last[l] = s;
            }
        }
        CHECK(ok);
    }
    /* slot mapping: every ring slot gets a distinct world column in [first, first + 20] */
    for (d = 0; d < 100; d++) {
        int ok = 1;
        for (slot = 0; slot < BG_RING; slot++) seen[slot] = 0;
        for (slot = 0; slot < BG_RING; slot++) {
            uint32_t w = bg_slot_world_col(d, slot);
            if (w < d || w >= d + BG_RING || w % BG_RING != slot) ok = 0;
            seen[w - d]++;
        }
        for (slot = 0; slot < BG_RING; slot++) if (seen[slot] != 1) ok = 0;
        CHECK(ok);
    }
    /* x positions: first visible column starts at or left of 0, ring covers the 320 px screen */
    CHECK(bg_slot_x(0, 0) == 0);
    CHECK(bg_slot_x(5, 0) == -5);
    CHECK(bg_slot_x(16, 1) == 0);
    CHECK(bg_slot_x(31, bg_first_col(31) + BG_ART_COLS) == 305 && 305 + 16 >= 320);
    CHECK(bg_first_col(15) == 0 && bg_first_col(16) == 1 && bg_first_col(321) == 20);
    /* wrap at the 320 px period: art column repeats, x continues */
    CHECK(bg_art_col(0) == 0 && bg_art_col(19) == 19 && bg_art_col(20) == 0 && bg_art_col(41) == 1);
    CHECK(bg_art_col(bg_first_col(320 * 7) ) == 0);
    /* column writes: none while inside a column, one per crossing, all on a jump or first frame */
    CHECK(bg_columns_to_write(3, 3, 1) == 0);
    CHECK(bg_columns_to_write(3, 4, 1) == 1);
    CHECK(bg_columns_to_write(3, 5, 1) == BG_RING);
    CHECK(bg_columns_to_write(9, 2, 1) == BG_RING);
    CHECK(bg_columns_to_write(0, 0, 0) == BG_RING);
    printf("bg: %d checks, %d failed\n", checks, failures);
    return failures ? 1 : 0;
}
