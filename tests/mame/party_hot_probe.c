/* Compiled with the 68000 compiler (-S) by make test-party-hot; tests/mame/party_hot_check.lua reads the Hot Gum state from RAM with these
 * values (target ABI: int is 32 bit). Order is fixed:
 * 1 flow state, 2 Game.players, 3 Game.mode, 4 Game.party_rule, 5 Game.cpu_count, 6 Hot.carrier, 7 Hot.fuse, 8 Hot.cool,
 * then FLOW_PLAYING, GAME_MODE_ARENA, PARTY_HOT, HOT_FUSE_FRAMES (9..12), then Flow.mode, Flow.party_rule, GAME_MODE_PARTY (13..15). */
#include <stddef.h>
#include "../../src/core/flow.h"
#define G(m) (offsetof(Flow, game) + offsetof(Game, m))
unsigned int probe[] = {
    offsetof(Flow, state), G(players), G(mode), G(party_rule), G(cpu_count), G(hot) + offsetof(Hot, carrier),
    G(hot) + offsetof(Hot, fuse), G(hot) + offsetof(Hot, cool),
    FLOW_PLAYING, GAME_MODE_ARENA, PARTY_HOT, HOT_FUSE_FRAMES,
    offsetof(Flow, mode), offsetof(Flow, party_rule), GAME_MODE_PARTY,
};
