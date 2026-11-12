/* Host test for src/core/camera.[ch]: ring camera (no clamp), dead zone, speed limit, seam crossing both ways, two humans on opposite
 * sides, unwrapped value, world-to-screen fold. */
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

/* Helpers for the ring cases. Sootling art: 32 px sprite, hit box columns SOOT_BOX_DX..+3 (14..17), drawn at
 * flier x - FLIER_HALF_W - 14 (src/main.c hero_show). The values are the ones main.c uses. */
#define SPR_W 32
#define BODY_DX 14
static int sprite_sx(const Camera *c, int32_t x16) {
    return camera_screen_x((int)(x16 >> 16) - 2 - BODY_DX, camera_px(c), SPR_W);
}
static int fold384(int d) { return (int)arena_fold(d, ARENA_W); }

int main(void) {
    Camera c;
    camera_init(&c);
    CHECK(camera_px(&c) == 32 && camera_unwrapped_px(&c) == 32);
    /* no human: the camera holds */
    for (int i = 0; i < 50; i++) camera_step(&c, 0, 0);
    CHECK(camera_px(&c) == 32);
    /* no clamp: a human far right pulls the camera past 64, one at the seam pulls it round to 0 */
    run(&c, PX(380), 400);
    CHECK(camera_px(&c) == 220);
    run(&c, PX(5), 400);
    CHECK(camera_px(&c) == ((5 - 160) % ARENA_W + ARENA_W) % ARENA_W);
    CHECK(camera_target(PX(100), &(int32_t){PX(5)}, 1) == PX(5 - 160 + 384)); /* nearest copy of 5 is 389: ring, not clamp */
    CHECK(camera_target(PX(32), &(int32_t){PX(200)}, 1) == PX(40));
    CHECK(camera_target(PX(32), 0, 0) == PX(32));
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
        CHECK(maxd == PX(CAM_MAX_STEP_PX));
    }
    /* two humans on opposite sides of the ring: shortest arc, both on screen, no snap, at and around distance 192 */
    for (int gap = 150; gap <= 230; gap += 7) {
        int32_t two[2];
        int prev_cam;
        camera_init(&c);
        two[0] = PX(10); two[1] = arena_wrap_x(PX(10 + gap));
        prev_cam = camera_px(&c);
        for (int f = 0; f < 300; f++) {
            camera_step(&c, two, 2);
            CHECK(abs(fold384(camera_px(&c) - prev_cam)) <= CAM_MAX_STEP_PX);
            prev_cam = camera_px(&c);
        }
        if (gap <= 190) { /* the shorter arc fits the screen: both bodies show */
            CHECK(sprite_sx(&c, two[0]) + BODY_DX >= 0 && sprite_sx(&c, two[0]) + BODY_DX + 3 < SCREEN_W);
            CHECK(sprite_sx(&c, two[1]) + BODY_DX >= 0 && sprite_sx(&c, two[1]) + BODY_DX + 3 < SCREEN_W);
        }
    }
    /* humans 40 px either side of the seam: midpoint is the seam, target 0 - 160 on the ring */
    {
        int32_t two[2] = { PX(344), PX(40) };
        camera_init(&c);
        for (int i = 0; i < 600; i++) camera_step(&c, two, 2);
        CHECK(camera_px(&c) == 384 - 160);
        CHECK(camera_target(c.cam, two, 2) - c.cam < PX(1) && c.cam - camera_target(c.cam, two, 2) < PX(1));
    }
    /* a human sweeping through the tie distance never makes the camera jump */
    {
        int32_t two[2] = { PX(0), PX(150) };
        camera_init(&c);
        int prev_cam = camera_px(&c);
        for (int f = 0; f < 3000; f++) {
            two[1] = arena_wrap_x(two[1] + 16384); /* quarter pixel per frame, round the whole ring */
            camera_step(&c, two, 2);
            CHECK(abs(fold384(camera_px(&c) - prev_cam)) <= CAM_MAX_STEP_PX);
            prev_cam = camera_px(&c);
        }
    }
    /* unwrapped value: matches camera_px modulo the arena, never negative, drops only by the lap period, no overflow */
    {
        int32_t x = PX(192), prev;
        int drops = 0;
        camera_init(&c);
        prev = camera_unwrapped_px(&c);
        for (int f = 0; f < 720000; f++) {
            x = arena_wrap_x(x + 65536);
            camera_step(&c, &x, 1);
            int32_t u = camera_unwrapped_px(&c);
            CHECK(u >= 0 && u < CAM_LAP_PERIOD_PX + ARENA_W);
            CHECK(u % ARENA_W == camera_px(&c));
            if (u < prev) { CHECK(prev - u >= CAM_LAP_PERIOD_PX - CAM_MAX_STEP_PX); drops++; }
            else CHECK(u - prev <= CAM_MAX_STEP_PX);
            prev = u;
        }
        CHECK(drops == 1);
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
        for (int cam = 0; cam < ARENA_W; cam++)
            for (int wx = -40; wx < ARENA_W + 40; wx++) {
                int sx = camera_screen_x(wx, cam, w);
                CHECK(sx >= -w && sx < ARENA_W - w);
                CHECK(((sx + cam - wx) % ARENA_W + ARENA_W) % ARENA_W == 0);
                /* a sprite with a visible pixel on screen is never hidden by the normalisation */
                int lin = (((wx % ARENA_W) + ARENA_W) % ARENA_W) - cam;
                if (lin > -w && lin < SCREEN_W) CHECK(camera_visible(sx, w) && sx == lin);
            }
        CHECK(camera_edge_marker(-16, 16) == -1 && camera_edge_marker(330, 16) == 1 && camera_edge_marker(100, 16) == 0);
    }
    printf("%d checks, %d failures\n", checks, failures);
    return failures != 0;
}
