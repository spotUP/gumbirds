/* Compiled with the 68000 compiler (-S) by make test-flier; tests/mame/flier_check.lua reads the game state from RAM
 * with these offsets (target ABI, not the host one). Order is fixed:
 * flow_state, game frame, flier_steps, over, score, then Flier x, y, vx, vy, state, balloons, on_ground, then the
 * computer flier sentinels: cpu_count, cpu_alive, stomps, matches_won, cpu[0].x, cpu[0].y, ai[0].thinks, cpu[1].x, then SCORE_STOMP_POP and SCORE_CPU_DEFEAT (knob values), cpu[0].state, cpu[0].balloons, player vx offset is F(vx) above. */
#include <stddef.h>
#include "../../src/core/flow.h"
#define G(m) (offsetof(Flow, game) + offsetof(Game, m))
#define F(m) (offsetof(Flow, game) + offsetof(Game, flier) + offsetof(Flier, m))
unsigned int probe[] = {
    offsetof(Flow, state), G(frame), G(flier_steps), G(over), G(score),
    F(x), F(y), F(vx), F(vy), F(state), F(balloons), F(on_ground),
    G(cpu_count), G(cpu_alive), G(stomps), G(matches_won),
    G(cpu) + offsetof(Flier, x), G(cpu) + offsetof(Flier, y), G(ai) + offsetof(Ai, thinks),
    G(cpu) + sizeof(Flier) + offsetof(Flier, x),
    SCORE_STOMP_POP, SCORE_CPU_DEFEAT,
    G(cpu) + offsetof(Flier, state), G(cpu) + offsetof(Flier, balloons),
};
