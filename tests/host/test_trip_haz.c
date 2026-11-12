/* Gum Trip hazard view (plan step V4): art offsets from the gameplay centre, visibility, hidden slots, animation frame wrap.
 * Pure helpers of src/core/trip_view.c; the expected numbers are written out from the sheet json, not read from the code. */
#include <stdio.h>
#include <stdint.h>
#include "../../src/core/trip_view.h"
#include "../../src/core/trip_gen.h"
#include "../../src/core/trip_hit.h"

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; if (failures <= 20) printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

/* cols, rows, cx, cy, frames per kind (coal, vent, cloud) */
static const int K[3][5] = { {2, 2, 13, 18, 24}, {2, 3, 16, 18, 16}, {3, 3, 25, 20, 24} };

int main(void) {
    TripChunk c = {0};
    TripViewHaz v;
    int kind, i;
    uint32_t steps, scroll = 1000;

    c.wx = 1000;
    c.n_haz = 3;
    for (kind = 0; kind < 3; kind++) {
        c.haz[0].kind = (uint8_t)kind; c.haz[0].x = 100; c.haz[0].y = 120; c.haz[0].amp = 0; c.haz[0].phase = 0;
        CHECK(trip_view_haz_art(&c, 0, scroll, 0, &v) == 1);
        CHECK(v.cols == K[kind][0] && v.rows == K[kind][1]);
        CHECK(v.left == 1000 + 100 - (int)scroll - K[kind][2]);
        CHECK(v.top == 120 - K[kind][3]);
        CHECK(v.kind == kind);
        CHECK(trip_view_haz_frame_count(kind) == K[kind][4]);
    }
    /* hidden: index past n_haz, null chunk, off screen on both sides */
    c.haz[0].kind = TRIP_HAZ_CLOUD; c.haz[0].x = 100; c.haz[0].y = 120;
    c.n_haz = 1;
    CHECK(trip_view_haz_art(&c, 1, scroll, 0, &v) == 0);
    CHECK(trip_view_haz_art(&c, 2, scroll, 0, &v) == 0);
    CHECK(trip_view_haz_art(0, 0, scroll, 0, &v) == 0);
    CHECK(trip_view_haz_art(&c, 0, 1123u, 0, &v) == 0);   /* left = -48 exactly: hidden */
    CHECK(trip_view_haz_art(&c, 0, 1122u, 0, &v) == 1);   /* left = -47: touches */
    CHECK(trip_view_haz_art(&c, 0, 756u, 0, &v) == 1 && v.left == 319);
    CHECK(trip_view_haz_art(&c, 0, 755u, 0, &v) == 0);
    /* the sweep moves the art with the same function the hit test uses */
    c.haz[0].amp = 40; c.haz[0].phase = 17;
    for (steps = 0; steps < 600; steps++) {
        if (trip_view_haz_art(&c, 0, scroll, steps, &v) != 1) { CHECK(0); break; }
        CHECK(v.top == trip_hit_haz_y(&c.haz[0], steps) - K[TRIP_HAZ_CLOUD][3]);
    }
    /* animation frame equals plain modulo of steps / 4 over a long run */
    for (kind = 0; kind < 3; kind++)
        for (steps = 0; steps < 20000; steps++) {
            int f = trip_view_haz_frame(kind, steps);
            CHECK(f == (int)((steps >> 2) % (uint32_t)K[kind][4]));
        }
    (void)i;
    printf("trip_haz: %d checks, %d failures\n", checks, failures);
    return failures != 0;
}
