/* Compiled with the 68000 compiler (-S) by the test-party-tug target; tests/mame/party_tug_check.lua reads the Tug Gum state from RAM with
 * these values (target ABI: int is 32 bit). Order is fixed:
 * 1 flow state, 2 Game.mode, 3 Game.gg_tug, 4 Tug.phase, 5 Tug.humans, 6 Tug.wins, 7 Tug.knot,
 * then FLOW_PLAYING, GAME_MODE_GUM, GTG_PLAY, GTG_SNAP, GTG_RESULT (8..12), then Flow.mode, Flow.party_rule, GAME_MODE_PARTY, PARTY_TUG (13..16),
 * then Game.cpu_count, Game.cpu[0..2].state, Game.hero[1].state (17..21). */
#include <stddef.h>
#include "../../src/core/flow.h"
#define G(m) (offsetof(Flow, game) + offsetof(Game, m))
#define T(m) (G(tug) + offsetof(GgTug, m))
unsigned int probe[] = {
    offsetof(Flow, state), G(mode), G(gg_tug), T(phase), T(humans), T(wins), T(knot),
    FLOW_PLAYING, GAME_MODE_GUM, GTG_PLAY, GTG_SNAP, GTG_RESULT,
    offsetof(Flow, mode), offsetof(Flow, party_rule), GAME_MODE_PARTY, PARTY_TUG,
    G(cpu_count), G(cpu[0].state), G(cpu[1].state), G(cpu[2].state), G(hero[1].state),
};
