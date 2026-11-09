/* Compiled with the 68000 compiler (-S) by make test-hit; tests/mame/hit_check.lua reads the game state
 * from RAM with these values (target ABI). Order is fixed: flow_state, invuln, lives, INVULN_FRAMES,
 * HIT_POSE_FRAMES, HIT_BLINK_FRAMES, HERO_ANIM_HIT, HERO_ANIM_RUN, POOL_MAX (vblank_check.lua). */
#include <stddef.h>
#include "../../src/core/flow.h"
#include "../../src/core/tuning.h"
#include "../../src/core/obj_pool.h"
#define G(m) (offsetof(Flow, game) + offsetof(Game, m))
unsigned int probe[] = {
    offsetof(Flow, state), G(invuln), G(lives), INVULN_FRAMES, HIT_POSE_FRAMES, HIT_BLINK_FRAMES, 9, 0, POOL_MAX,
};
