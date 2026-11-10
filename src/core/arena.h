/*
 * arena.h - the wrapping arena: 384 px wide, the screen shows 320 of it through the camera (src/core/camera.h).
 * Side edges wrap: x leaves 383 and arrives at 0. This header is the ONE source of the wrap maths; every reader of a
 * world x (collision, stomp angle, AI, broad phase, floor test) goes through it. Pure C99, no divide, no libm.
 * Design: thoughts/shared/plans/2026-11-10-wide-arena-camera.md sections 1-3.
 */
#ifndef BRAWL_ARENA_H
#define BRAWL_ARENA_H

#include <stdint.h>
#include "tuning.h"

#define ARENA_W       384                  /* world width in pixels (640 ref px x 0.6, user decision 2026-11-10) */
#define ARENA_W16     ((int32_t)ARENA_W * 65536)
#define ARENA_CAM_MAX (ARENA_W - SCREEN_W) /* camera travel 0..64 */

/* Fold a difference of two coordinates on a ring of `w` units into (-w/2, w/2]. */
static inline int32_t arena_fold(int32_t d, int32_t w) {
    if (d > w / 2) d -= w;
    else if (d <= -(w / 2)) d += w;
    return d;
}

/* Wrap a 16.16 world x into [0, ARENA_W). Velocities are far below one arena width per frame. */
static inline int32_t arena_wrap_x(int32_t x16) {
    while (x16 < 0) x16 += ARENA_W16;
    while (x16 >= ARENA_W16) x16 -= ARENA_W16;
    return x16;
}

/* Shortest signed distance a - b across the seam, whole pixels: arena_dx(383, 1) == -2. Result in (-192, 192]. */
static inline int arena_dx(int a, int b) { return (int)arena_fold(a - b, ARENA_W); }

/* The same in half pixels (x >> 15), the unit of the stomp feet box and the broad phase. */
static inline int32_t arena_dx_half(int32_t a, int32_t b) { return arena_fold(a - b, 2 * ARENA_W); }

/* The copy of x16 (16.16) nearest to ref16, i.e. x16 shifted by 0 or one arena width. Readers that compare
 * positions in their own units shift one operand with this and keep their maths unchanged. */
static inline int32_t arena_near_x(int32_t ref16, int32_t x16) { return ref16 + arena_fold(x16 - ref16, ARENA_W16); }

#endif
