/*
 * camera.h - the follow camera over the 384 px wrapping arena (design 2026-11-10-wide-arena-camera.md section 2).
 * State is the world x of the left screen edge in 16.16. The view reads camera_px(): whole pixels in 0..64.
 * Follows the midpoint of the human fliers; eases 1/2^CAM_EASE_SHIFT of the gap, at most CAM_MAX_STEP_PX per frame,
 * dead zone CAM_DEAD_ZONE_PX. No human: centre (32). Humans split across the seam (linear span too wide for the
 * screen): the camera holds. Pure C99, no divide, no globals.
 */
#ifndef BRAWL_CAMERA_H
#define BRAWL_CAMERA_H

#include <stdint.h>
#include "arena.h"

typedef struct {
    int32_t cam;     /* 16.16 world x of the left screen edge, 0..ARENA_CAM_MAX */
    uint8_t moving;  /* 1 while chasing a target outside the dead zone */
} Camera;

void camera_init(Camera *c);
/* One frame. human_x16: world x (16.16, wrapped) of each living human flier; n may be 0. */
void camera_step(Camera *c, const int32_t *human_x16, int n);
/* Camera x in whole screen pixels, 0..ARENA_CAM_MAX: the value the view subtracts from a world x. */
int camera_px(const Camera *c);
/* Target camera x (16.16, clamped) for the given humans, or -1 when the span is too wide and the camera holds. */
int32_t camera_target(const int32_t *human_x16, int n);

/* World-to-screen: the ONE transform for every world object (fliers, platforms, effects). world_px is the sprite's left
 * edge in whole world pixels (any int, wrapped here), w its width in pixels. Result: screen x of the left edge,
 * normalised into [-w, ARENA_W - w) so an object slides in and out at both screen edges; two copies of a sprite
 * are ARENA_W apart, so never both on a 320 px screen. */
int camera_screen_x(int world_px, int cam_px, int w);
/* 1 when a sprite of width w at screen x sx shows any pixel of the 320 px screen. */
int camera_visible(int sx, int w);
/* Screen x of the hazard strip head sprite (the strip scrolls with the world at factor 1). */
int camera_hazard_x(int cam_px);
/* Off screen marker: -1 when the sprite is wholly off the left edge, +1 right, 0 when any part shows. */
int camera_edge_marker(int sx, int w);

#endif
