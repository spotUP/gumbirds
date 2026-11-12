/* Seam reachability test for the ring camera (plan thoughts/spot/2026-11-10-ring-camera-plan.md section 5). Drives the
 * camera and the world-to-screen transform exactly as src/main.c does, with a flier that walks round the whole ring both
 * ways, and asserts on every frame: the 4 px body of the 32 px Sootling sprite is wholly inside screen x 0..319, the
 * camera moves at most CAM_MAX_STEP_PX, camera_px stays 0..383, and the sprite's screen x is continuous (it jumps by a
 * whole ring only while the sprite is off screen). Uses only the API that exists in the old clamped camera too, so the
 * same file runs against the old src/core/camera.c to show it fails there. */
#include <stdio.h>
#include <stdlib.h>
#include "../../src/core/camera.h"

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; if (failures <= 10) printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

#define SPR_W 32  /* Sootling sprite width, SOOT_COLUMNS * 16 */
#define BODY_DX 14 /* hit box column 14..17 in the art (SOOT_BOX_DX) */

/* camera_arrived: false away from the target, true inside the dead zone, and true again once camera_step goes idle. */
static void test_arrived(void) {
    Camera c;
    int32_t x = 300 * 65536;
    int f;
    camera_init(&c);
    CHECK(camera_arrived(&c, &x, 0));           /* no human: holds, arrived */
    CHECK(!camera_arrived(&c, &x, 1));          /* 300 px away */
    for (f = 0; f < 600 && !camera_arrived(&c, &x, 1); f++) camera_step(&c, &x, 1);
    CHECK(f < 600 && camera_arrived(&c, &x, 1));
    {
        int32_t before = c.cam;
        camera_step(&c, &x, 1);
        CHECK(!c.moving || c.cam != before);    /* inside the dead zone and resting: no move; mid-move: still progressing */
    }
}

int main(void) {
    test_arrived();
    for (int dir = -1; dir <= 1; dir += 2) {
        int32_t x = 192 * 65536;
        int prev_sx = 0, prev_cam = 0, passes = 0;
        Camera c;
        camera_init(&c);
        for (int f = 0; f < 1600; f++) {
            x = arena_wrap_x(x + dir * 65536); /* 1 px per frame, faster than a walk */
            camera_step(&c, &x, 1);
            int cp = camera_px(&c);
            int sx = camera_screen_x((int)(x >> 16) - 2 - BODY_DX, cp, SPR_W); /* FLIER_HALF_W 2 */
            CHECK(cp >= 0 && cp < ARENA_W);
            CHECK(sx + BODY_DX >= 0 && sx + BODY_DX + 3 <= SCREEN_W - 1);
            if (f > 0) {
                CHECK(abs((int)arena_fold(cp - prev_cam, ARENA_W)) <= CAM_MAX_STEP_PX);
                int dsx = sx - prev_sx;
                if (abs(dsx) > ARENA_W / 2) CHECK(!camera_visible(sx, SPR_W) && !camera_visible(prev_sx, SPR_W));
                else CHECK(abs(dsx) <= 1 + CAM_MAX_STEP_PX);
                if (abs(cp - prev_cam) > 300) passes++; /* camera_px itself wrapped 383 <-> 0 */
            }
            prev_sx = sx; prev_cam = cp;
        }
        CHECK(passes >= 3); /* ran past the seam several times (a clamped camera never does) */
    }
    printf("%d checks, %d failures\n", checks, failures);
    return failures != 0;
}
