/* Gum Trip kill strips (plan step V2): rows, top and rim pattern of floor and ceiling columns, chunk lookup, ring slot continuity over a
 * long scroll, nothing read before the course is ready. Pure helpers of src/core/trip_view.c. */
#include <stdio.h>
#include <stdint.h>
#include "../../src/core/trip_view.h"
#include "../../src/core/trip_gen.h"
#include "../../src/core/camera.h"
#include "../../src/core/trip_cave.h"
#include "../../src/core/trip_cave_fade.h"

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; if (failures <= 20) printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

int main(void) {
    TripGen g;
    TripStripCell cells[TRIP_VIEW_STRIP_MAX_ROWS];
    uint32_t seed, k, j;
    int top, rows, r;
    long columns = 0, loaded_floor = 0, curves = 0, flat_fade = 0, sloped_fade = 0;

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
                    TripCavePiece p;
                    int prow, k = (int)((j << 4) - ch->wx) >> 4, want, edge;
                    trip_cave_piece(ch, k, ceil_, &p);
                    prow = trip_cave_piece_rows(p.kind);
                    if (p.kind) curves++;
                    edge = trip_cave_edge(ch, k, ceil_);
                    CHECK(ceil_ ? edge <= ch->win_top : edge >= ch->win_bottom);   /* rock never reaches into the window */
                    rows = trip_view_strip_column(ch, j, ceil_, cells, &top);
                    columns++;
                    CHECK(rows >= 0 && rows <= TRIP_VIEW_STRIP_MAX_ROWS);
                    if (!ceil_) {
                        want = p.y0 < TRIP_VIEW_STRIP_BOTTOM ? (TRIP_VIEW_STRIP_BOTTOM - (p.y0 > 0 ? p.y0 : 0) + 15) / 16 : 0;
                        if (want > TRIP_VIEW_STRIP_MAX_ROWS) want = TRIP_VIEW_STRIP_MAX_ROWS;
                        CHECK(rows == want && top == p.y0);
                        if (rows) { loaded_floor++; CHECK(top + 16 * rows >= TRIP_VIEW_STRIP_BOTTOM || rows == TRIP_VIEW_STRIP_MAX_ROWS); }
                    } else {
                        int bottom = p.y0 + 16 * prow;
                        want = bottom > 0 ? (bottom + 15) / 16 : 0;
                        if (want > TRIP_VIEW_STRIP_MAX_ROWS) want = TRIP_VIEW_STRIP_MAX_ROWS;
                        CHECK(rows == want);
                        if (rows) CHECK(top + 16 * rows == bottom);
                    }
                    for (r = 0; r < rows; r++) {   /* piece next to the window, then the flat or sloped fade, then solid / black */
                        int d = ceil_ ? rows - 1 - r : r;
                        const TripStripCell *e = &cells[r];
                        int end = ceil_ ? e->role == TRIP_STRIP_ROOF && e->frame == TRIP_ROOF_BLACK : e->role == TRIP_STRIP_FLOOR_FADE && e->frame == TRIP_FLOOR_SOLID;
                        if (p.kind == TRIP_CAVE_FLAT) {
                            CHECK(e->flip == 0);
                            if (d == 0) {
                                if (ceil_) CHECK(e->role == TRIP_STRIP_ROOF && (e->frame == TRIP_ROOF_RIM_A || e->frame == TRIP_ROOF_RIM_B) && e->cell == (j & 3));
                                else CHECK(e->role == TRIP_STRIP_LIP + (int)(j & 3));
                            } else if (ceil_) CHECK(d <= 2 ? e->role == TRIP_STRIP_ROOF && e->frame == (d == 1 ? TRIP_ROOF_FADE_A : TRIP_ROOF_FADE_B) && e->cell == (j & 3) : end);
                            else if (d <= TRIP_STRIP_FILL_ROWS) CHECK(e->role == TRIP_STRIP_FILL);
                            else if (d <= TRIP_STRIP_FILL_ROWS + 2) CHECK(e->role == TRIP_STRIP_FLOOR_FADE && e->frame == (d == TRIP_STRIP_FILL_ROWS + 1 ? TRIP_FLOOR_FADE_A : TRIP_FLOOR_FADE_B) && e->cell == (j & 1));
                            else CHECK(end);
                            if (d >= 1 && d <= (ceil_ ? 2 : TRIP_STRIP_FILL_ROWS + 2)) flat_fade++;
                        } else {
                            int v = d < TRIP_FADE_ROWS ? (ceil_ ? trip_fade_roof : trip_fade_floor)[p.kind - 1][p.pcol][d] : TRIP_FADE_END;
                            if (d == 0) CHECK(v == TRIP_FADE_PIECE);   /* the window edge is always the drawn curve */
                            if (d >= (ceil_ ? 5 : 6)) CHECK(v == TRIP_FADE_END);   /* the sloped fade ends 2 tile rows past the deepest piece row */
                            if (v == TRIP_FADE_PIECE) {
                                CHECK(d < prow);
                                if (ceil_) CHECK(e->role == TRIP_STRIP_ROOF && e->frame == (p.kind == TRIP_CAVE_S16 ? TRIP_ROOF_S16 : TRIP_ROOF_S32) && e->cell == p.pcol * prow + (prow - 1 - d));
                                else CHECK(e->role == (p.kind == TRIP_CAVE_S16 ? TRIP_STRIP_FS16 : TRIP_STRIP_FS32) && e->cell == p.pcol * prow + d);
                            } else if (v == TRIP_FADE_FILL) CHECK(!ceil_ && e->role == TRIP_STRIP_FILL);
                            else if (v == TRIP_FADE_END) CHECK(end && e->flip == 0);
                            else {
                                CHECK(v < (ceil_ ? TRIP_FADE_ROOF_TILES : TRIP_FADE_FLOOR_TILES) && e->cell == v);
                                CHECK(ceil_ ? e->role == TRIP_STRIP_ROOF && e->frame == TRIP_ROOF_SLOPED : e->role == TRIP_STRIP_FLOOR_FADE && e->frame == TRIP_FLOOR_SLOPED);
                                sloped_fade++;
                            }
                            if (v != TRIP_FADE_END) CHECK(e->flip == (p.hflip ? TRIP_STRIP_HFLIP : 0));
                        }
                    }
                }
            }
        }
    }
    CHECK(columns > 20000 && loaded_floor > 5000 && curves > 1000 && flat_fade > 5000 && sloped_fade > 1000);
    printf("%s trip strip: %d checks, %d failures, %ld columns built, %ld floor columns with art, %ld curve columns, %ld flat / %ld sloped fade cells\n", failures ? "FAIL" : "PASS", checks, failures, columns, loaded_floor, curves, flat_fade, sloped_fade);
    return failures ? 1 : 0;
}
