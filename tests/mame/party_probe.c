/* Compiled with the 68000 compiler (-S) by make test-party; tests/mame/party_check.lua reads the party state from RAM with these
 * values (target ABI: int is 32 bit). Order is fixed:
 * 1 flow state, 2 Flow.party_rule (title choice), 3 Game.party_rule, 4 Game.twist, 5 Game.round_start, 6 Game.mode,
 * then FLOW_PLAYING, PARTY_ROUND, RS_ROUND, RS_GO, GAME_MODE_ARENA (7..11), 12 Flow.howto. */
#include <stddef.h>
#include "../../src/core/flow.h"
#define G(m) (offsetof(Flow, game) + offsetof(Game, m))
unsigned int probe[] = {
    offsetof(Flow, state), offsetof(Flow, party_rule), G(party_rule), G(twist), G(round_start), G(mode),
    FLOW_PLAYING, PARTY_ROUND, RS_ROUND, RS_GO, GAME_MODE_ARENA, offsetof(Flow, howto),
};
