/* Gum Trip pickup view (plan step V3): sprite left = centre x - 16, top = centre y - 20, hidden when collected, absent or off screen,
 * idle frame = steps / 4 mod 16. Pure helpers of src/core/trip_view.c. */
#include <stdio.h>
#include <stdint.h>
#include "../../src/core/trip_view.h"
#include "../../src/core/trip_gen.h"
#include "../../src/core/camera.h"

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; if (failures <= 20) printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

int main(void) {
    TripChunk c = {0};
    int seen = 0;
    uint32_t seed, k;
    c.wx = 640; c.pickup.present = 1; c.pickup.x = 100; c.pickup.y = 90;
    /* centre world x 740 at scroll 600 is screen 140: left 124, top 70 (fail-before: the old maths had the 24 px art box, top 78) */
    CHECK(trip_view_pickup_left(&c, 600) == 124);
    CHECK(trip_view_pickup_top(&c) == 70);
    /* edges: left -31 shows, -32 hides; 319 shows, 320 hides */
    CHECK(trip_view_pickup_left(&c, 740 - 16 + 31) == -31);
    CHECK(trip_view_pickup_left(&c, 740 - 16 + 32) == CAMERA_COL_HIDDEN);
    CHECK(trip_view_pickup_left(&c, 740 - 16 - 319) == 319);
    CHECK(trip_view_pickup_left(&c, 740 - 16 - 320) == CAMERA_COL_HIDDEN);
    c.pickup.present = 0;   /* collected */
    CHECK(trip_view_pickup_left(&c, 600) == CAMERA_COL_HIDDEN);
    /* idle frame: 4 steps per frame, wraps at 16 */
    CHECK(trip_view_pickup_frame(0) == 0 && trip_view_pickup_frame(3) == 0 && trip_view_pickup_frame(4) == 1);
    CHECK(trip_view_pickup_frame(63) == 15 && trip_view_pickup_frame(64) == 0);
    /* generated pickups: the sprite (32 tall) stays on the screen and covers the 24 px hit box */
    for (seed = 1; seed <= 200; seed++) {
        TripGen g;
        tripgen_init(&g, seed);
        for (k = 0; k < 60; k++) {
            int r;
            tripgen_advance(&g, k * 96);
            for (r = 0; r < TRIP_GEN_RING; r++) {
                const TripChunk *ch = trip_view_ring_chunk(&g, r, 1);
                if (!ch || !ch->pickup.present) continue;
                seen++;
                CHECK(trip_view_pickup_top(ch) <= ch->pickup.y - TRIP_PICKUP_HALF);
                CHECK(trip_view_pickup_top(ch) + TRIP_VIEW_PICKUP_SPRITE_H >= ch->pickup.y + TRIP_PICKUP_HALF);
                CHECK(trip_view_pickup_top(ch) > -TRIP_VIEW_PICKUP_SPRITE_H && trip_view_pickup_top(ch) < TRIP_VIEW_STRIP_BOTTOM); /* SCB3 wraps a negative top */
                /* with the idle bob (-2..+3) and the collect box (top = centre - 16) the sprite still stays on the screen */
                CHECK(trip_view_pickup_top(ch) + TRIP_VIEW_PICKUP_BOB_MIN > -TRIP_VIEW_PICKUP_SPRITE_H);
                CHECK(trip_view_pickup_top(ch) + TRIP_VIEW_PICKUP_BOB_MAX + TRIP_VIEW_PICKUP_SPRITE_H <= TRIP_VIEW_STRIP_BOTTOM + TRIP_VIEW_PICKUP_SPRITE_H);
                CHECK(ch->pickup.y - TRIP_VIEW_COLLECT_TOP_OFF >= 0 && ch->pickup.y - TRIP_VIEW_COLLECT_TOP_OFF + TRIP_VIEW_PICKUP_SPRITE_H <= 180);
            }
        }
    }
    CHECK(seen > 100);
    printf("pickups seen %d\n%s: %d checks, %d failed\n", seen, failures ? "FAIL" : "PASS", checks, failures);
    return failures != 0;
}
