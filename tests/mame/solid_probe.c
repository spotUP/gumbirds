/* Compiled with the 68000 compiler (-S) by make test-solid; tests/mame/solid_check.lua reads these numbers instead of
 * copying them. Order is fixed: FLIER_HALF_W, FLIER_HALF_H16_BALLOON, STAGE_PLATFORM_H, STAGE_PLATFORM_COUNT. */
#include "../../src/core/flier.h"
#include "../../src/core/stage.h"
#include "../../src/core/tuning.h"
unsigned int probe[] = { FLIER_HALF_W, FLIER_HALF_H16_BALLOON, STAGE_PLATFORM_H, STAGE_PLATFORM_COUNT };
