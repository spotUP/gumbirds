/* Compiled with the 68000 compiler (-S) by make test-reach; tests/mame/hiscore_reach.lua reads the flow
 * state from RAM with these offsets (target ABI). Order is fixed:
 * flow_state, last_score, table.name, table.score, entry.name, entry.sym, entry.pos, entry.done,
 * then the arena slice: flier x, vx, on_ground, game.score, then the stomp-teleport slice: flier y, flier vy, cpu[0].x, cpu[0].y, cpu[0].state, cpu[0].balloons (the test puts the player on a computer balloon so a real stomp scores),
 * then entry.idle and the NAME_TIMEOUT_FRAMES value (a constant, not an offset) for the countdown check. */
#include <stddef.h>
#include "../../src/core/flow.h"
#define G(m) (offsetof(Flow, game) + offsetof(Game, m))
unsigned int probe[] = {
    offsetof(Flow, state), offsetof(Flow, last_score),
    offsetof(Flow, tables) + offsetof(HiscoreTable, name), offsetof(Flow, tables) + offsetof(HiscoreTable, score),
    offsetof(Flow, entry) + offsetof(NameEntry, name), offsetof(Flow, entry) + offsetof(NameEntry, sym),
    offsetof(Flow, entry) + offsetof(NameEntry, pos), offsetof(Flow, entry) + offsetof(NameEntry, done),
    offsetof(Flow, game) + offsetof(Game, flier) + offsetof(Flier, x),
    offsetof(Flow, game) + offsetof(Game, flier) + offsetof(Flier, vx),
    offsetof(Flow, game) + offsetof(Game, flier) + offsetof(Flier, on_ground),
    G(score),
    G(flier) + offsetof(Flier, y), G(flier) + offsetof(Flier, vy),
    G(cpu) + offsetof(Flier, x), G(cpu) + offsetof(Flier, y),
    G(cpu) + offsetof(Flier, state), G(cpu) + offsetof(Flier, balloons),
    offsetof(Flow, entry) + offsetof(NameEntry, idle), NAME_TIMEOUT_FRAMES,
};
