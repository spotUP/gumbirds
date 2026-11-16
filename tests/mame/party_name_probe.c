/* Compiled with the 68000 compiler (-S) by make test-party-name; tests/mame/party_name_check.lua reads the flow from RAM with these
 * values (target ABI). Order is fixed:
 * 1 state, 2 timer, 3 last_score, 4 last_players, 5 entry_h, 6 last_mode, 7 last_rule, 8 entry.pos, 9 entry.sym, 10 entry.done,
 * then GAME_MODE_PARTY, FLOW_PLAYING, FLOW_GAME_OVER, FLOW_NAME_ENTRY, FLOW_ATTRACT_TITLE (11..15), sizeof(HiscoreTable) (16). */
#include <stddef.h>
#include "../../src/core/flow.h"
unsigned int probe[] = {
    offsetof(Flow, state), offsetof(Flow, timer), offsetof(Flow, last_score), offsetof(Flow, last_players), offsetof(Flow, entry_h),
    offsetof(Flow, last_mode), offsetof(Flow, last_rule),
    offsetof(Flow, entry) + offsetof(NameEntry, pos), offsetof(Flow, entry) + offsetof(NameEntry, sym), offsetof(Flow, entry) + offsetof(NameEntry, done),
    GAME_MODE_PARTY, FLOW_PLAYING, FLOW_GAME_OVER, FLOW_NAME_ENTRY, FLOW_ATTRACT_TITLE, sizeof(HiscoreTable),
};
