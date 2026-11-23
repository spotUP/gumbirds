/* Compiled with the 68000 compiler (-S) by make test-gum-join-p2; tests/mame/gum_join_p2_check.lua reads the join state with these offsets
 * (target ABI: int is 32 bit). Order: 1 Flow.state, 2 Game.mode, 3 Game.players, 4 Game.cpu_level, 5 Game.cd_t (u16), 6 Flow.gg_card,
 * 7..15 the event flags gg_toss, gg_tug, gg_gather, gg_fling, gg_poop, gg_dash, gg_pop, gg_race, and blow.seq.players,
 * then FLOW_PLAYING (16), GAME_MODE_GUM (17), CPU_OFF (18). */
#include <stddef.h>
#include "../../src/core/flow.h"
#define G(m) (offsetof(Flow, game) + offsetof(Game, m))
unsigned int probe[] = {
    offsetof(Flow, state), G(mode), G(players), G(cpu_level), G(cd_t), offsetof(Flow, gg_card),
    G(gg_toss), G(gg_tug), G(gg_gather), G(gg_fling), G(gg_poop), G(gg_dash), G(gg_pop), G(gg_race), G(blow) + offsetof(GgBlow, seq) + offsetof(GgSeq, players),
    FLOW_PLAYING, GAME_MODE_GUM, CPU_OFF,
};
