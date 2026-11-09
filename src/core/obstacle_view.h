/*
 * obstacle_view.h - which sprite animation frame an obstacle shows. Pure, host tested; the
 * Neo Geo glue in src/main.c turns the result into sprite registers.
 *
 * The obstacle sheet lists its animations in ObstacleType order (vent, cable, drone, bot), so
 * the animation index of an obstacle is its type (main.c asserts OBS_ANIM_* == OB_*).
 */
#ifndef ROOFLINE_OBSTACLE_VIEW_H
#define ROOFLINE_OBSTACLE_VIEW_H

#include <stdint.h>

/* Game frames per animation frame for an obstacle type; 0 for an unknown type. */
uint8_t obstacle_view_ticks(uint8_t type);

/* Frame within the animation of `type` for game frame `frame`, 0..frame_count-1. */
uint8_t obstacle_view_frame(uint8_t type, uint32_t frame, uint8_t frame_count);

#endif
