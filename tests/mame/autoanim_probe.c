/* Compiled with the 68000 compiler (-S) by make test-autoanim; tests/mame/autoanim_check.lua reads the auto-animation
 * speed and the star pixel positions of stars 0 and 1 through these values. Order is fixed: frames per step,
 * star 0 x, y, star 1 x, y. */
#include "../../src/bg_stars.h"
static const unsigned short pos[][2] = { BG_STAR_POSITIONS };
unsigned int probe[] = { BG_STAR_STEP_FRAMES, pos[0][0], pos[0][1], pos[1][0], pos[1][1] };
