/*
 * gum_view.h - which gum bubble the Gum Trip flier blows. Pure, host tested (tests/host/test_gum_view.c); the Neo Geo glue
 * (src/gum.c, part of the wiring) turns the level into sprite registers. Level numbering is the sheet's (assets/gum/gum_sheet.json,
 * animations level16 .. level1, pop_large, pop_small): 0 = no bubble, 1 = smallest .. GUM_VIEW_LEVELS = full. The sheet animation
 * of a level is GUM_VIEW_LEVELS - level. Frame timing (wobble, pop cadence) is not here: it is still an open decision.
 */
#ifndef BRAWL_GUM_VIEW_H
#define BRAWL_GUM_VIEW_H

#include <stdint.h>
#include "tuning.h"

#define GUM_VIEW_LEVELS 16

typedef enum { GUM_SIZE_TINY, GUM_SIZE_SMALL, GUM_SIZE_MEDIUM, GUM_SIZE_LARGE } GumSize;
typedef enum { GUM_POP_LARGE, GUM_POP_SMALL } GumPop;

/* Level 0..16 for a gum amount: ceil(gum / (GUM_MAX / 16)), so any gum above 0 shows at least level 1; above GUM_MAX clamps to 16. */
uint8_t gum_view_level(uint16_t gum);
/* Size class of a level 1..16: large 16..13, medium 12..8, small 7..5, tiny 4..1. Level 0 (no bubble) returns tiny. */
GumSize gum_view_size(uint8_t level);
/* Pop set a level pops with: large and medium use pop_large, small and tiny use pop_small. */
GumPop gum_view_pop(uint8_t level);

#endif
