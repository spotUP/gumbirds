/* Compiled with the 68000 compiler (-S) by make test-gum-burst-race-2p; tests/mame/gum_burst_race_2p_check.lua reads the Burst Race state from RAM with
 * these values (target ABI: int is 32 bit). Order is fixed:
 * 1 Flow.state, 2 Game.mode, 3 Game.gg_race, 4 GgRace.phase, 5 GgRace.size[0], 6 GgRace.size[1], 7 GgRace.winner, 8 Game.score,
 * 9 Game.players, 10 GgRace.players, then FLOW_PLAYING, GAME_MODE_GUM, GG_RACE_INTRO, GG_RACE_PLAY, GG_RACE_RESULT (11..15). */
#include <stddef.h>
#include "../../src/core/flow.h"
#define G(m) (offsetof(Flow, game) + offsetof(Game, m))
#define R(m) (G(race) + offsetof(GgRace, m))
unsigned int probe[] = {
    offsetof(Flow, state), G(mode), G(gg_race), R(phase), R(size), R(size) + 1, R(winner), G(score), G(players), R(players),
    FLOW_PLAYING, GAME_MODE_GUM, GG_RACE_INTRO, GG_RACE_PLAY, GG_RACE_RESULT, offsetof(Flow, gg_card),
};
