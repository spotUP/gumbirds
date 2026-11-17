/* Compiled with the 68000 compiler (-S) by make test-gum-pop-drop; tests/mame/gum_pop_drop_check.lua reads the Pop Drop state from RAM with
 * these values (target ABI: int is 32 bit). Order is fixed:
 * 1 Flow.state, 2 Game.mode, 3 Game.gg_pop, 4 pop.phase, 5 pop.pops, 6 pop.total, 7 pop.drop, 8 Game.score, 9 Flow.tables.gg_record[GG_POP_DROP],
 * 10 hero[0].x, 11 cpu[0].x, 12 Result.active, then FLOW_PLAYING, GAME_MODE_GUM, FLOW_GAME_OVER, GP_HANG, GP_FALL, GP_FALL (13..17). */
#include <stddef.h>
#include "../../src/core/flow.h"
#define G(m) (offsetof(Flow, game) + offsetof(Game, m))
#define P(m) (G(pop) + offsetof(GgPop, m))
unsigned int probe[] = {
    offsetof(Flow, state), G(mode), G(gg_pop), P(phase), P(pops), P(total), P(drop), G(score),
    offsetof(Flow, tables) + offsetof(ScoreTables, gg_record) + 4 * GG_POP_DROP,
    G(hero) + offsetof(Flier, x), G(cpu) + offsetof(Flier, x), G(res) + offsetof(Result, active),
    FLOW_PLAYING, GAME_MODE_GUM, FLOW_GAME_OVER, GP_HANG, GP_FALL,
};
