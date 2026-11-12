/* Compiled with the 68000 compiler (-S) by the test-score rule; tests/mame/score_check.lua reads the flow
 * state from RAM with these offsets (target ABI). Plain -std=c99, same as reach_probe.c. Order is fixed (1-based in Lua):
 *  1 Flow.state          2 Flow.last_score      3 Flow.last_mode     4 Flow.mode        5 Flow.timer
 *  6 tables.t[0].name    7 tables.t[0].score    8 sizeof(HiscoreTable)  (t[1] = t[0] + this)
 *  9 entry.name         10 entry.sym           11 entry.pos         12 entry.done      13 entry.idle
 * 14 Game.mode          15 Game.score          16 Game.over         17 Trip.bonus      18 hero flier state
 * then constants (values, not offsets):
 * 19 NAME_TIMEOUT_FRAMES  20 SCORE_IMAGE_SIZE  21 FLIER_DROWNED  22 GAME_MODE_TRIP  23 FLOW_PLAYING
 * 24 FLOW_GAME_OVER  25 FLOW_NAME_ENTRY  26 FLOW_SAVE_REMINDER  27 FLOW_ATTRACT_TABLE  28 FLOW_ATTRACT_TITLE */
#include <stddef.h>
#include "../../src/core/flow.h"
#define G(m) (offsetof(Flow, game) + offsetof(Game, m))
unsigned int probe[] = {
    offsetof(Flow, state), offsetof(Flow, last_score), offsetof(Flow, last_mode), offsetof(Flow, mode), offsetof(Flow, timer),
    offsetof(Flow, tables) + offsetof(ScoreTables, t) + offsetof(HiscoreTable, name),
    offsetof(Flow, tables) + offsetof(ScoreTables, t) + offsetof(HiscoreTable, score),
    sizeof(HiscoreTable),
    offsetof(Flow, entry) + offsetof(NameEntry, name), offsetof(Flow, entry) + offsetof(NameEntry, sym),
    offsetof(Flow, entry) + offsetof(NameEntry, pos), offsetof(Flow, entry) + offsetof(NameEntry, done),
    offsetof(Flow, entry) + offsetof(NameEntry, idle),
    G(mode), G(score), G(over), G(trip) + offsetof(Trip, bonus), G(flier) + offsetof(Flier, state),
    NAME_TIMEOUT_FRAMES, SCORE_IMAGE_SIZE, FLIER_DROWNED, GAME_MODE_TRIP, FLOW_PLAYING,
    FLOW_GAME_OVER, FLOW_NAME_ENTRY, FLOW_SAVE_REMINDER, FLOW_ATTRACT_TABLE, FLOW_ATTRACT_TITLE,
};
