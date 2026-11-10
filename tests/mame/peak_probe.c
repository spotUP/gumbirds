/* Compiled with the 68000 compiler (-S) by make test-sprite-peak; tests/mame/sprite_peak_check.lua reads the slot range
 * and the Flow/Game offsets from these values (target ABI). Order is fixed: gameplay first slot, gameplay end slot
 * (pool + hero), flow state, cpu_count, matches_won, player x, player y, cpu[0] x, cpu[0] y, sizeof(Flier), cpu_alive,
 * player balloons, player state, game frame, island first slot, island end slot. */
#include <stddef.h>
#include "../../src/core/flow.h"
#include "../../src/sprite_slots.h"
#define G(m) (offsetof(Flow, game) + offsetof(Game, m))
#define F(m) (offsetof(Flow, game) + offsetof(Game, flier) + offsetof(Flier, m))
unsigned int probe[] = {
    POOL_SPRITE_BASE, HERO_SPRITE + HERO_SPRITE_COUNT,
    offsetof(Flow, state), G(cpu_count), G(matches_won),
    F(x), F(y), G(cpu) + offsetof(Flier, x), G(cpu) + offsetof(Flier, y), sizeof(Flier),
    G(cpu_alive), F(balloons), F(state), G(frame),
    ISLAND_SPRITE, ISLAND_SPRITE + ISLAND_COUNT,
};
