/* Compiled with the 68000 compiler (-S) by the vblank, scroll and sound checks; the Lua scripts read the game
 * state from RAM with these values (target ABI). Order is fixed: flow_state, POOL_MAX (vblank_check.lua). */
#include <stddef.h>
#include "../../src/core/flow.h"
#include "../../src/core/obj_pool.h"
unsigned int probe[] = {
    offsetof(Flow, state), POOL_MAX,
};
