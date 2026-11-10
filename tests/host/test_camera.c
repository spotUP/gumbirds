/* Host test for src/core/camera.[ch]: clamp, dead zone, speed limit, seam pan without snap, split-human hold. */
#include <stdio.h>
#include <stdlib.h>
#include "../../src/core/camera.h"
#include "../../src/core/game.h"

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)
#define PX(n) ((int32_t)(n) * 65536)

static void run(Camera *c, int32_t x16, int frames) {
    for (int i = 0; i < frames; i++) camera_step(c, &x16, 1);
}

int main(void) {
    Camera c;
    camera_init(&c);
    CHECK(camera_px(&c) == 32);
    /* no human: stays at the centre */
    for (int i = 0; i < 50; i++) camera_step(&c, 0, 0);
    CHECK(camera_px(&c) == 32);
    /* clamp: human far right and far left */
    run(&c, PX(380), 200);
    CHECK(camera_px(&c) == 64); /* the snap makes the clamp reachable */
    run(&c, PX(5), 200);
    CHECK(camera_px(&c) <= 4);
    CHECK(camera_target(&(int32_t){PX(5)}, 1) == 0);
    CHECK(camera_target(&(int32_t){PX(380)}, 1) == PX(64));
    CHECK(camera_target(&(int32_t){PX(200)}, 1) == PX(40));
    /* dead zone: a resting camera ignores a target 3 px away, follows one 5 px away */
    camera_init(&c);
    run(&c, PX(160 + 32 + 3), 20);
    CHECK(c.cam == PX(32));
    run(&c, PX(160 + 32 + 5), 100);
    CHECK(camera_px(&c) >= 36 && camera_px(&c) <= 37);
    /* max 2 px per frame, and no frame goes backwards while chasing */
    camera_init(&c);
    {
        int32_t x = PX(300), prev = c.cam, maxd = 0;
        for (int i = 0; i < 60; i++) {
            camera_step(&c, &x, 1);
            int32_t d = c.cam - prev;
            if (d > maxd) maxd = d;
            CHECK(d >= 0);
            prev = c.cam;
        }
        CHECK(maxd <= PX(CAM_MAX_STEP_PX));
        CHECK(maxd >= PX(CAM_MAX_STEP_PX) - 1 || maxd > 0);
    }
    /* single human crosses the seam: 383 -> 0, the camera pans, never snaps */
    camera_init(&c);
    run(&c, PX(383), 100);
    CHECK(camera_px(&c) == 64);
    {
        int32_t x = PX(0), prev = c.cam, worst = 0;
        for (int i = 0; i < 60; i++) {
            camera_step(&c, &x, 1);
            int32_t d = prev - c.cam;
            if (d > worst) worst = d;
            prev = c.cam;
        }
        CHECK(worst <= PX(2));
        CHECK(camera_px(&c) <= 4);
    }
    /* two humans close: midpoint */
    camera_init(&c);
    {
        int32_t two[2] = { PX(150), PX(250) };
        CHECK(camera_target(two, 2) == PX(200 - 160));
    }
    /* two humans split across the seam: span > 304, hold */
    camera_init(&c);
    {
        int32_t two[2] = { PX(10), PX(375) };
        CHECK(camera_target(two, 2) == -1);
        int32_t before = c.cam;
        for (int i = 0; i < 100; i++) camera_step(&c, two, 2);
        CHECK(c.cam == before);
        /* hold also at the far end after moving there */
        run(&c, PX(380), 200);
        before = c.cam;
        for (int i = 0; i < 100; i++) camera_step(&c, two, 2);
        CHECK(c.cam == before);
    }
    /* Game owns and steps the camera every frame */
    {
        Game g;
        game_reset(&g, 1);
        CHECK(game_camera_px(&g) == 32);
        g.flier.x = PX(380); g.flier.y = PX(100);
        for (int i = 0; i < 60; i++) game_step_arena(&g, 0);
        CHECK(game_camera_px(&g) > 32);
    }
    /* world-to-screen: slides at both edges, one copy only, wraps across the seam */
    {
        int w = 16;
        CHECK(camera_screen_x(100, 0, w) == 100);
        CHECK(camera_screen_x(100, 64, w) == 36);
        CHECK(camera_screen_x(383, 64, w) == 319);
        CHECK(camera_screen_x(383, 0, w) == -1);          /* left edge of the arena seam: 1 px of its right end shows */
        CHECK(camera_screen_x(-5, 0, w) == -5);
        CHECK(camera_screen_x(2, 64, w) == 322);          /* just past the right screen edge, behind the seam */
        CHECK(camera_screen_x(10, 64, w) == 330);
        CHECK(camera_screen_x(370, 0, w) == -14);
        CHECK(!camera_visible(330, w) && camera_visible(319, w) && camera_visible(-15, w) && !camera_visible(-16, w));
        for (int cam = 0; cam <= ARENA_CAM_MAX; cam++)
            for (int wx = -40; wx < ARENA_W + 40; wx++) {
                int sx = camera_screen_x(wx, cam, w);
                CHECK(sx >= -w && sx < ARENA_W - w);
                CHECK(((sx + cam - wx) % ARENA_W + ARENA_W) % ARENA_W == 0);
                /* a sprite with a visible pixel on screen is never hidden by the normalisation */
                int lin = (((wx % ARENA_W) + ARENA_W) % ARENA_W) - cam;
                if (lin > -w && lin < SCREEN_W) CHECK(camera_visible(sx, w) && sx == lin);
            }
        CHECK(camera_edge_marker(-16, 16) == -1 && camera_edge_marker(330, 16) == 1 && camera_edge_marker(100, 16) == 0);
        CHECK(camera_hazard_x(0) == 0 && camera_hazard_x(64) == -64);
    }
    printf("%d checks, %d failures\n", checks, failures);
    return failures != 0;
}
