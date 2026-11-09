/*
 * laser_view.h - what the laser looks like for a game state. Pure, host tested; the Neo Geo glue in
 * src/main.c turns the results into sprite registers. The beam and the hit flash use the hero set
 * animations "laser" and "hit_flash"; the heat bar uses the "heat" set (assets/laser).
 */
#ifndef ROOFLINE_LASER_VIEW_H
#define ROOFLINE_LASER_VIEW_H

#include <stdint.h>
#include "game.h"

#define LV_BEAM_W 24         /* beam art width in pixels (hero sheet "laser") */
#define LV_BEAM_H 5
#define LV_FLASH_FRAMES 4    /* hit_flash frames */
#define LV_FLASH_TICKS 3     /* game frames per flash frame */
#define LV_BAR_CELLS 16      /* heat bar cells of 8 px */
#define LV_BAR_PAIRS (LV_BAR_CELLS / 2)  /* sprite tiles of 2 cells */
#define LV_BAR_BLINK 6       /* frames per blink phase while the light is dark */

typedef enum { LV_POSE_NONE = 0, LV_POSE_SHOOT, LV_POSE_RECOIL } LaserPose;

/* Beam `i` (0..MAX_BOLTS-1) active: top-left of the art in screen pixels, return 1. Else 0.
 * The art's right end sits on the right end of the bolt hit box. */
int laser_view_beam(const Game *g, int i, int *x, int *y);

/* Hit flash: centre of the last kill and frame 0..LV_FLASH_FRAMES-1 while it plays, return 1. Else 0. */
int laser_view_flash(const Game *g, int *cx, int *cy, int *frame);

/* Hero pose for the shot cycle: RECOIL right after a shot, SHOOT until the next shot is allowed. */
LaserPose laser_view_pose(const Game *g);

/* Lit cells 0..LV_BAR_CELLS for a heat value (any heat lights at least one cell). */
int laser_view_cells(uint16_t heat);

/* Heat bar tile `pair` (0..LV_BAR_PAIRS-1): frame index in the heat set's "bar" animation. */
int laser_view_bar_frame(const Game *g, int pair);

/* 0 while the bar is in the off phase of the overheat blink, else 1. */
int laser_view_bar_visible(const Game *g);

#endif
