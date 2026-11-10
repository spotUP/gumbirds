/* Compiled with the 68000 compiler (-S) by make test-reach; tests/mame/hiscore_reach.lua reads the flow
 * state from RAM with these offsets (target ABI). Order is fixed:
 * flow_state, last_score, table.name, table.score, entry.name, entry.sym, entry.pos, entry.done,
 * then the laser_probe.c autoplay offsets: obstacles (array, sizeof, count, x, w, type, active),
 * hero_h, hero_vy, lockout, game.score, game.speed. */
#include <stddef.h>
#include "../../src/core/flow.h"
#define G(m) (offsetof(Flow, game) + offsetof(Game, m))
unsigned int probe[] = {
    offsetof(Flow, state), offsetof(Flow, last_score),
    offsetof(Flow, table) + offsetof(HiscoreTable, name), offsetof(Flow, table) + offsetof(HiscoreTable, score),
    offsetof(Flow, entry) + offsetof(NameEntry, name), offsetof(Flow, entry) + offsetof(NameEntry, sym),
    offsetof(Flow, entry) + offsetof(NameEntry, pos), offsetof(Flow, entry) + offsetof(NameEntry, done),
    offsetof(Flow, game) + offsetof(Game, flier) + offsetof(Flier, x),
    offsetof(Flow, game) + offsetof(Game, flier) + offsetof(Flier, vx),
    offsetof(Flow, game) + offsetof(Game, flier) + offsetof(Flier, on_ground),
    G(score),
};
