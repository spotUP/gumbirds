/*
 * hero_view.h - how the hero looks after a hit. Pure, host tested; the Neo Geo glue in src/main.c picks
 * the sprite frame and shows or hides the hero sprite from the results. Right after the hit the
 * knocked-back HIT pose shows for HIT_POSE_FRAMES; for the rest of the invulnerability the hero runs
 * (normal pose) and blinks, HIT_BLINK_FRAMES visible, HIT_BLINK_FRAMES hidden, starting visible.
 */
#ifndef ROOFLINE_HERO_VIEW_H
#define ROOFLINE_HERO_VIEW_H

#include "game.h"

typedef enum { HV_LOOK_NORMAL = 0, HV_LOOK_HIT } HeroLook;

/* Pose for the game state; *visible is 0 while the hero sprite must be hidden, else 1. */
HeroLook hero_view_look(const Game *g, int *visible);

#endif
