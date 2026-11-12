/* Gum Trip view quantities (plan T-B4): the ring camera follows the trip scroll, not the flier. Drives game_step in TRIP
 * mode and camera_scroll directly. Numbers from the plan: 0.75 px/frame at distance 0 (49152 raw), cap 1.0 px/frame. */
#include <stdio.h>
#include <stdint.h>
#include "../../src/core/camera.h"
#include "../../src/core/bg_scroll.h"
#include "../../src/core/game.h"
#include "../../src/core/trip.h"
#include "../../src/core/nameentry.h"
#include "trip_steer.h"

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; if (failures <= 20) printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

int main(void) {
    Game g;
    Camera c;
    uint32_t i, changed = 0, seams = 0;
    int prev;

    /* camera_scroll alone: sums exactly, wraps at 384, lap and unwrapped position advance by the whole pixels */
    camera_init(&c);
    c.cam = 0;
    for (i = 0; i < 4; i++) camera_scroll(&c, 49152);
    CHECK(c.cam == 3 * 65536 && camera_px(&c) == 3);               /* 4 x 0.75 px = 3 px exactly */
    camera_init(&c); c.cam = 0;
    {
        uint64_t total = 0;
        for (i = 0; i < 200000; i++) {
            uint32_t step = (i % 3 == 0) ? 49152u : (i % 3 == 1 ? 65536u : 60000u);
            int before = camera_px(&c);
            camera_scroll(&c, step);
            total += step;
            CHECK(camera_px(&c) == (int)((total >> 16) % ARENA_W));
            CHECK(c.cam >= 0 && c.cam < ARENA_W16);
            { int d = camera_px(&c) - before; if (d < 0) { d += ARENA_W; seams++; } CHECK(d == 0 || d == 1); } /* no jump at the seam */
        }
        CHECK(seams > 100);
    }

    /* game level: trip mode, camera equals the trip distance on the ring, flier does not steer it */
    game_reset(&g, 1234);
    game_set_mode(&g, GAME_MODE_TRIP);
    CHECK(camera_px(&g.camera) == 0 && game_camera_px(&g) == 0 && game_flier_cam_px(&g) == 0);
    prev = game_camera_px(&g);
    for (i = 0; i < 3000; i++) {
        uint8_t in = trip_steer(&g, STEER_AVOID); /* survives the strips and hazards now that game_step collides */
        uint32_t px_before = g.trip.px, speed = g.trip.speed;
        if (g.over) break;
        game_step(&g, in);
        if (i == 0) CHECK(speed == 49152 && g.trip.px == 0);        /* 0.75 px first frame, nothing whole yet */
        CHECK(speed <= 65536);
        CHECK(game_camera_px(&g) == (int)(g.trip.px % ARENA_W));    /* camera == scroll position on the ring */
        CHECK(game_flier_cam_px(&g) == 0);
        { int d = game_camera_px(&g) - prev; if (d < 0) d += ARENA_W; CHECK(d == (int)(g.trip.px - px_before)); }
        if (game_camera_px(&g) != prev) changed++;
        prev = game_camera_px(&g);
        CHECK(g.flier.x >= 0 && (g.flier.x >> 16) < SCREEN_W);
        CHECK(camera_unwrapped_px(&g.camera) % ARENA_W == game_camera_px(&g));
    }
    CHECK(g.trip.px > 1000);
    CHECK(changed >= g.trip.px / 2 && changed <= g.trip.px);

    /* speed at distance 0 and cap */
    CHECK(trip_speed_at(0) == 49152 && trip_speed_at(TRIP_RAMP_PX) == 65536 && trip_speed_at(1000000) == 65536);

    /* arena: camera still follows the flier (feed unchanged) */
    game_reset(&g, 99);
    CHECK(g.mode == GAME_MODE_ARENA && game_flier_cam_px(&g) == game_camera_px(&g));

    printf("test_trip_view: %d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
