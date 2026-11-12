/* Gum Trip kill strips (plan step V2): rows, top and rim pattern of floor and ceiling columns, chunk lookup, ring slot continuity over a
 * long scroll, nothing read before the course is ready. Pure helpers of src/core/trip_view.c. */
#include <stdio.h>
#include <stdint.h>
#include "../../src/core/trip_view.h"
#include "../../src/core/trip_gen.h"
#include "../../src/core/camera.h"

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; if (failures <= 20) printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

int main(void) {
    TripGen g;
    TripStripCell cells[TRIP_VIEW_STRIP_MAX_ROWS];
    uint32_t seed, k, j;
    int top, rows, r;
    long columns = 0, loaded_floor = 0;

    for (seed = 1; seed <= 200; seed++) {
        TripStripRing ring = { 0, 0, 0 };
        uint32_t prev_j0 = 0;
        int slot_of[64];
        tripgen_init(&g, seed);
        for (k = 0; k < 400; k++) {
            uint32_t scroll = k * 24 + 1;   /* 1..2 columns scroll sometimes, none on others */
            uint32_t j0 = scroll >> 4;
            int jumped, i, on[TRIP_VIEW_STRIP_COLS];
            tripgen_advance(&g, scroll);
            CHECK(trip_view_strip_chunk(&g, j0, 0) == 0);   /* not ready: refused */
            jumped = trip_view_strip_advance(&ring, j0);
            CHECK(jumped == (k == 0));                       /* first call and nothing else is a jump (24 px per step < 22 columns) */
            for (i = 0; i < TRIP_VIEW_STRIP_COLS; i++) on[i] = trip_view_strip_slot(&ring, i);
            for (i = 0; i < TRIP_VIEW_STRIP_COLS; i++) {   /* a permutation of the 22 slots */
                int n2; for (n2 = i + 1; n2 < TRIP_VIEW_STRIP_COLS; n2++) CHECK(on[i] != on[n2]);
            }
            if (k > 0 && !jumped)   /* a column keeps its slot while it stays in the ring */
                for (j = j0; j < prev_j0 + TRIP_VIEW_STRIP_COLS; j++) CHECK(slot_of[j & 63] == on[j - j0]);
            for (i = 0; i < TRIP_VIEW_STRIP_COLS; i++) slot_of[(j0 + (uint32_t)i) & 63] = on[i];
            prev_j0 = j0;
            if (!tripgen_covers(&g, scroll)) continue;
            for (j = j0; j < j0 + TRIP_VIEW_STRIP_COLS; j++) {
                const TripChunk *ch = trip_view_strip_chunk(&g, j, 1);
                int ceil_;
                if (!ch) continue;
                CHECK(ch->wx <= (j << 4) && (j << 4) - ch->wx < TRIP_CHUNK_PX);
                for (ceil_ = 0; ceil_ < 2; ceil_++) {
                    int m = (int)(j & 3);
                    rows = trip_view_strip_column(ch, j, ceil_, cells, &top);
                    columns++;
                    CHECK(rows >= 0 && rows <= TRIP_VIEW_STRIP_MAX_ROWS);
                    if (!ceil_) {
                        int want = ch->win_bottom < TRIP_VIEW_STRIP_BOTTOM ? (TRIP_VIEW_STRIP_BOTTOM - (ch->win_bottom > 0 ? ch->win_bottom : 0) + 15) / 16 : 0;
                        if (want > TRIP_VIEW_STRIP_MAX_ROWS) want = TRIP_VIEW_STRIP_MAX_ROWS;
                        CHECK(rows == want && top == ch->win_bottom);
                        if (rows) { loaded_floor++; CHECK(top + 16 * rows >= TRIP_VIEW_STRIP_BOTTOM || rows == TRIP_VIEW_STRIP_MAX_ROWS); }
                    } else {
                        int want = ch->win_top > 0 ? (ch->win_top + 15) / 16 : 0;
                        if (want > TRIP_VIEW_STRIP_MAX_ROWS) want = TRIP_VIEW_STRIP_MAX_ROWS;
                        CHECK(rows == want);
                        if (rows) CHECK(top + 16 * rows == ch->win_top);
                    }
                    if (!rows) continue;
                    {   /* rim next to the window (floor row 0, ceiling last row), fill beyond; rim role and flip by column mod 4 */
                        const TripStripCell *rim = &cells[ceil_ ? rows - 1 : 0];
                        int expect_role = (m == 0 || m == 3) ? TRIP_STRIP_RIM_A : TRIP_STRIP_RIM_B;
                        int expect_flip = ((m & 1) ? TRIP_STRIP_HFLIP : 0) | (ceil_ ? TRIP_STRIP_VFLIP : 0);
                        CHECK(rim->role == expect_role && rim->flip == expect_flip);
                        for (r = 0; r < rows; r++) {
                            if (r == (ceil_ ? rows - 1 : 0)) continue;
                            CHECK(cells[r].role == TRIP_STRIP_FILL);
                            CHECK(cells[r].flip == ((((int)j + r) & 1) | (ceil_ ? TRIP_STRIP_VFLIP : 0)));
                        }
                    }
                }
            }
        }
    }
    CHECK(columns > 20000 && loaded_floor > 5000);
    printf("%s trip strip: %d checks, %d failures, %ld columns built, %ld floor columns with art\n", failures ? "FAIL" : "PASS", checks, failures, columns, loaded_floor);
    return failures ? 1 : 0;
}
