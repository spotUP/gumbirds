/*
 * camera.h - the follow camera over the 384 px wrapping arena (plan thoughts/spot/2026-11-10-ring-camera-plan.md section 1).
 * The world is a ring and the camera runs round it without a stop: there is no clamp and no hold, so the hero never
 * drops into an off screen strip. State: `cam` is the world x of the left screen edge, 16.16, kept in [0, ARENA_W16);
 * `lap` counts whole laps in pixels (multiples of ARENA_W) so the UNWRAPPED position stays available to the
 * parallax planes. The view reads camera_px() (wrapped, 0..383) for every world object.
 * Target = midpoint of the shortest arc through the humans, taken as the copy nearest the screen centre (arena_near_x against
 * cam + 160 px), minus 160 px.
 * Two humans on opposite sides: the shortest arc decides, resolved against the current camera, so the camera never
 * snaps (it only changes which way it eases). Eases 1/2^CAM_EASE_SHIFT of the gap, at most CAM_MAX_STEP_PX per frame,
 * dead zone CAM_DEAD_ZONE_PX. No human: the camera holds. Pure C99, no divide, no modulo, no globals.
 */
#ifndef BRAWL_CAMERA_H
#define BRAWL_CAMERA_H

#include <stdint.h>
#include "arena.h"

/* Lap counter period, in pixels: 384 * 1771 = 680064 = the common period of the five background planes. A plane of
 * width W at parallax k/16 repeats when the camera moved P pixels with P*k/16 a multiple of W; for the widths 336,
 * 352, 368, 384 and k 4, 8, 12, 16 the least such P is lcm(1344, 704, 1472, 384) = 680064. Wrapping the lap counter at
 * this period therefore changes no plane position (and 680064 + 383 fits an int32 with a huge margin), so the unwrapped
 * value never overflows however long the match runs. No other consumer reads the lap count. */
#define CAM_LAP_PERIOD_PX 680064

typedef struct {
    int32_t cam;     /* 16.16 world x of the left screen edge, always in [0, ARENA_W16) */
    int32_t lap;     /* whole laps already run, in pixels: a multiple of ARENA_W in [0, CAM_LAP_PERIOD_PX) */
    uint8_t moving;  /* 1 while chasing a target outside the dead zone */
} Camera;

void camera_init(Camera *c);
/* One frame. human_x16: world x (16.16, wrapped) of each living human flier; n may be 0. */
void camera_step(Camera *c, const int32_t *human_x16, int n);
/* Camera x in whole screen pixels, 0..383 (wrapped): the value the view subtracts from a world x. */
int camera_px(const Camera *c);
/* Unwrapped camera x in whole pixels, 0 .. CAM_LAP_PERIOD_PX + 383: continuous while the camera runs, drops by
 * CAM_LAP_PERIOD_PX once per period (invisible to the planes, see above). For the parallax planes. */
int32_t camera_unwrapped_px(const Camera *c);
/* Target camera x (16.16, in the same unwrapped frame as cam16, so it may lie outside 0..ARENA_W16) for the given
 * humans: midpoint of their shortest arc, copy nearest cam16 + 160 px, minus 160 px. n <= 0 returns cam16 (hold). */
/* Forced scroll (Gum Trip): move the camera right by step16 (16.16 px, 0 <= step16 < ARENA_W16) and fold at the ring seam.
 * Fed the trip scroll speed each frame it keeps cam == trip distance mod ARENA_W (whole px) with no jump at the seam, and
 * camera_unwrapped_px advances by the same whole pixels. No divide, no modulo. */
void camera_scroll(Camera *c, uint32_t step16);
int32_t camera_target(int32_t cam16, const int32_t *human_x16, int n);
/* 1 when the camera is within CAM_DEAD_ZONE_PX of the target for these humans (n <= 0 holds, so it counts as arrived). */
int camera_arrived(const Camera *c, const int32_t *human_x16, int n);

/* World-to-screen: the ONE transform for every world object (fliers, platforms, effects). world_px is the sprite's left
 * edge in whole world pixels (any int, wrapped here), w its width in pixels. Result: screen x of the left edge,
 * normalised into [-w, ARENA_W - w) so an object slides in and out at both screen edges; two copies of a sprite
 * are ARENA_W apart, so never both on a 320 px screen. */
int camera_screen_x(int world_px, int cam_px, int w);
/* 1 when a sprite of width w at screen x sx shows any pixel of the 320 px screen. */
int camera_visible(int sx, int w);
/* Sentinel of camera_column_x: no pixel of the column shows (same value hazard.c uses for "no x sent yet"). */
#define CAMERA_COL_HIDDEN 0x7FFF
/* Screen x of the left edge of ONE 16 px column whose left edge is world_px (any int, wrapped), or CAMERA_COL_HIDDEN when no
 * pixel of it shows on the 320 px screen. Result in (-16, 320). Columns of one island may land on opposite screen edges. */
int camera_column_x(int world_px, int cam_px);
/* camera_column_x, but a hidden column returns SCREEN_W (320, just off the right edge) instead of CAMERA_COL_HIDDEN: for strips whose
 * columns cannot be hidden by height 0 (hazard.c: the bank swap rewrites every column height). */
int camera_parked_column_x(int world_px, int cam_px);
/* Strip placement, one add per sprite: a strip of 16 px columns whose first column has screen x sx0 =
 * camera_screen_x(world_px, cam_px, 16) (so sx0 is in [-16, ARENA_W - 16)) places column c at sx0 + 16 * c. camera_strip_x takes that
 * sum (callers add 16 per column) and wraps it with ONE test: for 0 <= c <= 23 the sum is below 2 * ARENA_W - 16, so one subtraction of
 * ARENA_W lands in [-16, ARENA_W - 16), the same value camera_screen_x gives the column on its own. Result: the screen x, or
 * CAMERA_COL_HIDDEN when no pixel shows (identical to camera_column_x(world_px + 16 * c, cam_px)). The parked variant returns
 * SCREEN_W instead of the sentinel (identical to camera_parked_column_x). */
static inline int camera_strip_x(int sx) {
    if (sx >= ARENA_W - 16) sx -= ARENA_W;
    return (sx > -16 && sx < SCREEN_W) ? sx : CAMERA_COL_HIDDEN;
}
static inline int camera_strip_parked_x(int sx) {
    if (sx >= ARENA_W - 16) sx -= ARENA_W;
    return (sx > -16 && sx < SCREEN_W) ? sx : SCREEN_W;
}
/* Off screen marker: -1 when the sprite is wholly off the left edge, +1 right, 0 when any part shows. */
int camera_edge_marker(int sx, int w);

#endif
