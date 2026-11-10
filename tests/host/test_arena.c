/* Host test for src/core/arena.h: wrap and shortest distance across the 384 px seam. */
#include <stdio.h>
#include "../../src/core/arena.h"

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

int main(void) {
    CHECK(ARENA_W == 384 && ARENA_CAM_MAX == 64);
    /* wrap */
    CHECK(arena_wrap_x(0) == 0);
    CHECK(arena_wrap_x(ARENA_W16 - 1) == ARENA_W16 - 1);
    CHECK(arena_wrap_x(ARENA_W16) == 0);
    CHECK(arena_wrap_x(ARENA_W16 + 5) == 5);
    CHECK(arena_wrap_x(-1) == ARENA_W16 - 1);
    CHECK(arena_wrap_x(-ARENA_W16) == 0);
    /* dx across the seam */
    CHECK(arena_dx(383, 1) == -2);
    CHECK(arena_dx(1, 383) == 2);
    CHECK(arena_dx(100, 90) == 10);
    CHECK(arena_dx(90, 100) == -10);
    CHECK(arena_dx(0, 192) == 192);   /* tie goes positive: range (-192, 192] */
    CHECK(arena_dx(192, 0) == 192);
    CHECK(arena_dx(10, 10) == 0);
    CHECK(arena_dx_half(766, 2) == -4);   /* 383 px vs 1 px in half pixels */
    CHECK(arena_dx_half(2, 766) == 4);
    /* nearest copy */
    CHECK(arena_near_x(((int32_t)(1) * 65536), ((int32_t)(383) * 65536)) == ((int32_t)(-1) * 65536));
    CHECK(arena_near_x(((int32_t)(383) * 65536), ((int32_t)(1) * 65536)) == ((int32_t)(385) * 65536));
    CHECK(arena_near_x(((int32_t)(100) * 65536), ((int32_t)(150) * 65536)) == ((int32_t)(150) * 65536));
    printf("%d checks, %d failures\n", checks, failures);
    return failures != 0;
}
