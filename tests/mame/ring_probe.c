/* Compiled with the 68000 compiler (-S) by make test-ring; tests/mame/ring_check.lua reads these numbers instead of
 * copying them. Order is fixed: SCREEN_W, ARENA_W, CAM_MAX_STEP_PX, HERO_SPRITE, FLIER_BLINK_HALF_PERIOD. Same defines src/main.c uses. */
#include "../../src/core/arena.h"
#include "../../src/core/tuning.h"
#include "../../src/sprite_slots.h"
unsigned int probe[] = { SCREEN_W, ARENA_W, CAM_MAX_STEP_PX, HERO_SPRITE, FLIER_BLINK_HALF_PERIOD };
