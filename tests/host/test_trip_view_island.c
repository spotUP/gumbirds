/* Gum Trip island view (plan step V1): generated island widths, columns per island, world to screen x per column, hidden when
 * off screen, and no chunk read before the course is ready. Pure helpers of src/core/trip_view.c. */
#include <stdio.h>
#include <stdint.h>
#include "../../src/core/trip_view.h"
#include "../../src/core/trip_gen.h"
#include "../../src/core/camera.h"
#include "../../src/core/island_layout.h"

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; if (failures <= 20) printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

int main(void) {
    TripGen g;
    uint32_t seed, k;
    int r, c, max_cols = 0, islands = 0, seen[3] = {0, 0, 0};

    /* column count of the three widths equals the art tables' count */
    CHECK(trip_view_island_cols(64) == island_columns(64) && trip_view_island_cols(64) == 4);
    CHECK(trip_view_island_cols(80) == island_columns(80) && trip_view_island_cols(80) == 5);
    CHECK(trip_view_island_cols(96) == island_columns(96) && trip_view_island_cols(96) == 6);
    CHECK(TRIP_VIEW_ISLAND_BLOCK == 6);

    for (seed = 1; seed <= 300; seed++) {
        tripgen_init(&g, seed);
        for (k = 0; k < 120; k++) {
            uint32_t scroll = k * 96;
            int on_screen = 0;
            tripgen_advance(&g, scroll);
            /* nothing is read before ready: every slot is refused */
            for (r = 0; r < TRIP_GEN_RING; r++) CHECK(trip_view_ring_chunk(&g, r, 0) == 0);
            if (!tripgen_covers(&g, scroll)) continue;
            {
                int live = 0;
                for (r = 0; r < TRIP_GEN_RING; r++) {
                    const TripChunk *ch = trip_view_ring_chunk(&g, r, 1);
                    if (!ch) continue;
                    live++;
                    CHECK(ch == tripgen_get(&g, ch->index));
                    if (!ch->island.present) {
                        for (c = 0; c < TRIP_VIEW_ISLAND_BLOCK; c++) CHECK(trip_view_island_col_x(ch, c, scroll) == CAMERA_COL_HIDDEN);
                        continue;
                    }
                    islands++;
                    CHECK(ch->island.w == 64 || ch->island.w == 80 || ch->island.w == 96);
                    seen[(ch->island.w - 64) >> 4]++;
                    CHECK(trip_view_island_cols(ch->island.w) <= TRIP_VIEW_ISLAND_BLOCK);
                    for (c = 0; c < TRIP_VIEW_ISLAND_BLOCK; c++) {
                        int want = (int)(ch->wx + (uint32_t)ch->island.x + (uint32_t)(16 * c)) - (int)scroll;
                        int got = trip_view_island_col_x(ch, c, scroll);
                        if (c >= trip_view_island_cols(ch->island.w) || want <= -16 || want >= 320) CHECK(got == CAMERA_COL_HIDDEN);
                        else { CHECK(got == want); on_screen++; }
                    }
                }
                CHECK(live == g.count);
            }
            if (on_screen > max_cols) max_cols = on_screen;
        }
    }
    CHECK(islands > 1000 && seen[0] > 100 && seen[1] > 100 && seen[2] > 100);
    CHECK(max_cols <= 18);
    /* a column at a very large distance still maps without wrap */
    {
        TripChunk ch = {0};
        ch.wx = 4000000000u; ch.island.present = 1; ch.island.x = 40; ch.island.w = 96;
        CHECK(trip_view_island_col_x(&ch, 0, 4000000000u + 40 + 15) == -15);
        CHECK(trip_view_island_col_x(&ch, 0, 4000000000u + 40 + 16) == CAMERA_COL_HIDDEN);
        CHECK(trip_view_island_col_x(&ch, 5, 4000000000u + 40 + 16) == 64);
        CHECK(trip_view_island_col_x(&ch, 6, 0) == CAMERA_COL_HIDDEN);
    }
    printf("test_trip_view_island: %d checks, %d failures, max island columns on screen %d, islands %d (64: %d, 80: %d, 96: %d)\n",
           checks, failures, max_cols, islands, seen[0], seen[1], seen[2]);
    return failures ? 1 : 0;
}
