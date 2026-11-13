/*
 * gum_view.h - which gum bubble the Gum Trip flier blows. Pure, host tested (tests/host/test_gum_view.c); the Neo Geo glue
 * (src/gum.c, part of the wiring) turns the level into sprite registers. Level numbering is the sheet's (assets/gum/gum_sheet.json,
 * animations level16 .. level1, pop_large, pop_small): 0 = no bubble, 1 = smallest .. GUM_VIEW_LEVELS = full. The sheet animation
 * of a level is GUM_VIEW_LEVELS - level. Frame timing: wobble loops, GUM_WOBBLE_FRAMES game frames per sheet frame; pop plays once,
 * GUM_POP_FRAMES per sheet frame (tuning.h). The bubble follows the bird with a per bird frame offset (gum_view_offset).
 */
#ifndef BRAWL_GUM_VIEW_H
#define BRAWL_GUM_VIEW_H

#include <stdint.h>
#include "tuning.h"

#define GUM_VIEW_LEVELS 16
#define GUM_VIEW_WOBBLE_SHEET 6  /* sheet frames of a wobble loop (assets/gum/gum_sheet.json) */
#define GUM_VIEW_POP_SHEET    7  /* sheet frames of a pop */
#define GUM_VIEW_BIRD_FRAMES  105 /* frames of the player animation (sootling_anims[PLAYER]); src/gum.c asserts it */

typedef enum { GUM_SIZE_TINY, GUM_SIZE_SMALL, GUM_SIZE_MEDIUM, GUM_SIZE_LARGE } GumSize;
typedef enum { GUM_POP_LARGE, GUM_POP_SMALL } GumPop;

/* Level 0..16 for a gum amount: ceil(gum / (GUM_MAX / 16)), so any gum above 0 shows at least level 1; above GUM_MAX clamps to 16. */
uint8_t gum_view_level(uint16_t gum);
/* Size class of a level 1..16: large 16..13, medium 12..8, small 7..5, tiny 4..1. Level 0 (no bubble) returns tiny. */
GumSize gum_view_size(uint8_t level);
/* Pop set a level pops with: large and medium use pop_large, small and tiny use pop_small. */
GumPop gum_view_pop(uint8_t level);

typedef enum { GUM_STATE_WOBBLE, GUM_STATE_POP } GumState;
typedef struct { int8_t dx, dy; uint8_t show; } GumOffset; /* show: the bird frame carries a string, so the bubble is drawn */

/* Sheet animation number (GUM_ANIM_* order: level16 .. level1 = 0..15, pop_large 16, pop_small 17) for a level 1..16 in a state.
 * Level 0 is treated as level 1 (the glue hides the bubble at level 0). In a pop, level is the last level before the pop. */
uint8_t gum_view_anim(uint8_t level, GumState state);
/* Frame inside that animation after t game frames in the state: wobble loops, pop holds its last frame once it is over. */
uint8_t gum_view_frame(GumState state, uint32_t t);
/* 1 once t game frames have played the whole pop. */
int gum_view_pop_done(uint32_t t);
/* Bubble offset from the bird sprite's top centre for the bird's animation frame (0..GUM_VIEW_BIRD_FRAMES - 1), flip = the bird is mirrored:
 * dy = GUM_BIRD_ROW + the frame's bob, dx = GUM_BIRD_DX (GUM_BIRD_DX_FLIP mirrored). Out of range: 0, 0, show 0. */
GumOffset gum_view_offset(uint8_t bird_frame, int flip);

#endif
