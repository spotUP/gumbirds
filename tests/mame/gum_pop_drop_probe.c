/* Compiled with the 68000 compiler (-S) by make test-gum-pop-drop; tests/mame/gum_pop_drop_check.lua reads the Pop Drop state from RAM with
 * these values (target ABI: int is 32 bit). Order is fixed:
 * 1 Flow.state, 2 Game.mode, 3 Game.gg_pop, 4 pop.phase, 5 pop.hits, 6 pop.score, 7 pop.depth, 8 Flow.tables.gg_record[GG_POP_DROP],
 * 9 hero[0].x, 10 pop.plat[0] (PdPlat: x i16, y i16, kind, mids, live, hit), 11 Result.active, then FLOW_PLAYING, GAME_MODE_GUM, FLOW_GAME_OVER,
 * PD_FALL (12..15), 16 Game.cd_t (GET SET / GO! countdown, gg_countdown.h), 17 Game.score. */
#include <stddef.h>
#include "../../src/core/flow.h"
#define G(m) (offsetof(Flow, game) + offsetof(Game, m))
#define P(m) (G(pop) + offsetof(GgPop, m))
unsigned int probe[] = {
    offsetof(Flow, state), G(mode), G(gg_pop), P(phase), P(hits), P(score), P(depth),
    offsetof(Flow, tables) + offsetof(ScoreTables, gg_record) + 4 * GG_POP_DROP,
    G(hero) + offsetof(Flier, x), P(plat), G(res) + offsetof(Result, active),
    FLOW_PLAYING, GAME_MODE_GUM, FLOW_GAME_OVER, PD_FALL, G(cd_t), G(score),
};
