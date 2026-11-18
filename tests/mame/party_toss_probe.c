/* Compiled with the 68000 compiler (-S) by make test-party-toss; tests/mame/party_toss_check.lua reads the Toss Gum state from RAM with these
 * values (target ABI: int is 32 bit). Order is fixed:
 * 1 flow state, 2 Game.mode, 3 Game.gg_toss, 4 Toss.phase, 5 Toss.alive, 6 Toss.carrier, 7 Toss.winner, 8 Toss.round, 9 Toss.humans,
 * then FLOW_PLAYING, GAME_MODE_GUM, GT_FLIGHT, GT_BURST, GT_RESULT (10..14), then Flow.mode, Flow.party_rule, GAME_MODE_PARTY, PARTY_TOSS (15..18). */
#include <stddef.h>
#include "../../src/core/flow.h"
#define G(m) (offsetof(Flow, game) + offsetof(Game, m))
#define T(m) (G(toss) + offsetof(GgToss, m))
unsigned int probe[] = {
    offsetof(Flow, state), G(mode), G(gg_toss), T(phase), T(alive), T(carrier), T(winner), T(round), T(humans),
    FLOW_PLAYING, GAME_MODE_GUM, GT_FLIGHT, GT_BURST, GT_RESULT,
    offsetof(Flow, mode), offsetof(Flow, party_rule), GAME_MODE_PARTY, PARTY_TOSS,
};
