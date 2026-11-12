/* Host test for src/core/obj_pool.[ch]: free list, sprite runs, hide-once mask, 16.16 motion, animation. */
#include <stdio.h>
#include "../../src/core/obj_pool.h"

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

static ObjPool P;

static void test_alloc_free(void) {
    obj_pool_init(&P, 96);
    uint8_t seen[POOL_MAX] = {0};
    for (int k = 0; k < POOL_MAX; k++) {
        uint8_t i = obj_pool_alloc(&P, (uint8_t)k, 0, 0, 0, 0);
        CHECK(i < POOL_MAX);
        if (i < POOL_MAX) { CHECK(!seen[i]); seen[i] = 1; CHECK(P.obj[i].type == (uint8_t)k); }
    }
    CHECK(P.live == POOL_MAX && P.peak == POOL_MAX);
    CHECK(obj_pool_alloc(&P, 0, 0, 0, 0, 0) == POOL_NONE); /* full: fails quietly */
    CHECK(P.live == POOL_MAX);

    obj_pool_free(&P, 5);
    obj_pool_free(&P, 5);         /* double free ignored */
    obj_pool_free(&P, POOL_MAX);  /* out of range ignored */
    CHECK(P.live == POOL_MAX - 1);
    CHECK(!obj_pool_is_live(&P, 5));
    CHECK(obj_pool_alloc(&P, 9, 0, 0, 0, 0) == 5); /* O(1) LIFO reuse */
    CHECK(obj_pool_alloc(&P, 9, 0, 0, 0, 0) == POOL_NONE);

    /* free everything, then every index comes back exactly once */
    for (uint8_t i = 0; i < POOL_MAX; i++) obj_pool_free(&P, i);
    CHECK(P.live == 0 && P.peak == POOL_MAX);
    uint8_t again[POOL_MAX] = {0};
    int n = 0;
    for (;;) {
        uint8_t i = obj_pool_alloc(&P, 1, 0, 0, 0, 0);
        if (i == POOL_NONE) break;
        CHECK(i < POOL_MAX && !again[i]);
        if (i < POOL_MAX) again[i] = 1;
        n++;
    }
    CHECK(n == POOL_MAX);
}

static void test_sprite_runs(void) {
    obj_pool_init(&P, 96);
    for (uint8_t i = 0; i < POOL_MAX; i++) {
        uint16_t s = obj_pool_sprite(&P, i);
        CHECK(s == 96 + i * POOL_COLS);
        CHECK(s + POOL_COLS <= 96 + POOL_SPRITES);
    }
    /* runs are disjoint and cover the range exactly */
    uint8_t used[POOL_SPRITES] = {0};
    for (uint8_t i = 0; i < POOL_MAX; i++)
        for (int c = 0; c < POOL_COLS; c++) used[obj_pool_sprite(&P, i) - 96 + c]++;
    int ok = 1;
    for (int s = 0; s < POOL_SPRITES; s++) ok &= used[s] == 1;
    CHECK(ok);
}

static void test_hide_once(void) {
    obj_pool_init(&P, 0);
    uint8_t a = obj_pool_alloc(&P, 0, 0, 0, 0, 0);
    uint8_t b = obj_pool_alloc(&P, 0, 0, 0, 0, 0);
    CHECK(obj_pool_take_hidden(&P) == 0);
    obj_pool_free(&P, a);
    obj_pool_free(&P, b);
    CHECK(obj_pool_take_hidden(&P) == (((uint32_t)1 << a) | ((uint32_t)1 << b)));
    CHECK(obj_pool_take_hidden(&P) == 0); /* once */
    uint8_t c = obj_pool_alloc(&P, 0, 0, 0, 0, 0);
    obj_pool_free(&P, c);
    uint8_t d = obj_pool_alloc(&P, 0, 0, 0, 0, 0); /* same index reused before the view ran */
    CHECK(c == d);
    CHECK(obj_pool_take_hidden(&P) == 0);
    obj_pool_free(&P, 31 < POOL_MAX ? 31 : 0); /* not live: no bit */
    CHECK(obj_pool_take_hidden(&P) == 0);
}

static void test_motion(void) {
    obj_pool_init(&P, 0);
    /* 80 px/s^2 = 1456 (design 1.2); integrate 60 frames from rest: v = 87360, about 1.333 px/frame */
    uint8_t i = obj_pool_alloc(&P, 0, obj_pool_fp(100), obj_pool_fp(-8), -98304 /* -1.5 px/f */, 0);
    uint8_t dead = obj_pool_alloc(&P, 0, obj_pool_fp(7), obj_pool_fp(7), 65536, 65536);
    obj_pool_free(&P, dead);
    for (int f = 0; f < 60; f++) { P.obj[i].vy += 1456; obj_pool_step(&P); }
    CHECK(P.obj[i].vy == 87360);
    CHECK(obj_pool_px(P.obj[i].x) == 10);            /* 100 - 90 */
    CHECK(P.obj[i].y == obj_pool_fp(-8) + 1456 * (60 * 61 / 2));
    CHECK(obj_pool_px(P.obj[i].y) == 32);            /* -8 + 2664480/65536 = -8 + 40.66 */
    CHECK(P.obj[dead].x == obj_pool_fp(7));          /* freed objects do not move */
    CHECK(obj_pool_px(obj_pool_fp(-1)) == -1 && obj_pool_px(-1) == -1 && obj_pool_px(65535) == 0);
}

static void test_anim(void) {
    PoolObj o = {0};
    int frames[24];
    for (int f = 0; f < 24; f++) { frames[f] = o.anim; obj_pool_anim(&o, 3, 4); }
    int ok = 1;
    for (int f = 0; f < 24; f++) ok &= frames[f] == (f / 3) % 4;  /* same as obstacle_view_frame(t=3, n=4) */
    CHECK(ok);
    obj_pool_anim(&o, 0, 4);
    CHECK(o.anim == 0);
    o.anim = 7;
    obj_pool_anim(&o, 1, 2);
    CHECK(o.anim < 2);
}

/* Objects spawned on the same frame must not change animation frame on the same frame. */
static void test_anim_stagger(void) {
    obj_pool_init(&P, 96);
    for (int k = 0; k < 16; k++) obj_pool_alloc(&P, 1, 0, 0, 0, 0);
    uint8_t prev[16];
    int worst = 0;
    for (int k = 0; k < 16; k++) prev[k] = P.obj[k].anim;
    for (int f = 0; f < 64; f++) {
        int changed = 0;
        for (int k = 0; k < 16; k++) {
            obj_pool_anim(&P.obj[k], 2, 2); /* drone: 2 frames per animation frame */
            if (P.obj[k].anim != prev[k]) changed++;
            prev[k] = P.obj[k].anim;
        }
        if (changed > worst) worst = changed;
    }
    printf("anim stagger: worst %d of 16 drones change frame on one frame\n", worst);
    CHECK(worst <= 8);
}

/* obj_pool_claim takes one named free object, leaves the others allocatable, refuses a live or out-of-range object. */
static void test_claim(void) {
    uint8_t i;
    obj_pool_init(&P, 96);
    CHECK(obj_pool_claim(&P, 7) == 1);
    CHECK(obj_pool_claim(&P, 7) == 0);
    CHECK(obj_pool_claim(&P, POOL_MAX) == 0);
    CHECK(P.live == 1 && (P.obj[7].flags & POOL_F_LIVE) != 0);
    for (int k = 0; k < POOL_MAX - 1; k++) {
        i = obj_pool_alloc(&P, 1, 0, 0, 0, 0);
        CHECK(i < POOL_MAX && i != 7);
    }
    CHECK(obj_pool_alloc(&P, 1, 0, 0, 0, 0) >= POOL_MAX);
    obj_pool_init(&P, 96);
    for (i = 0; i < 15; i++) CHECK(obj_pool_claim(&P, i) == 1);
    CHECK(obj_pool_alloc(&P, 1, 0, 0, 0, 0) == 15);
}

int main(void) {
    test_claim();
    test_alloc_free();
    test_sprite_runs();
    test_hide_once();
    test_motion();
    test_anim();
    test_anim_stagger();
    printf("obj_pool: %d checks, %d failures\n", checks, failures);
    return failures != 0;
}
