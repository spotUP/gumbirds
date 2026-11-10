/* Compiled with the 68000 compiler (-S) by make test-flier; tests/mame/flier_check.lua reads the game state from RAM
 * with these offsets (target ABI, not the host one). Order is fixed:
 * flow_state, game frame, flier_steps, over, score, then Flier x, y, vx, vy, state, balloons, on_ground. */
#include <stddef.h>
#include "../../src/core/flow.h"
#define G(m) (offsetof(Flow, game) + offsetof(Game, m))
#define F(m) (offsetof(Flow, game) + offsetof(Game, flier) + offsetof(Flier, m))
unsigned int probe[] = {
    offsetof(Flow, state), G(frame), G(flier_steps), G(over), G(score),
    F(x), F(y), F(vx), F(vy), F(state), F(balloons), F(on_ground),
};
