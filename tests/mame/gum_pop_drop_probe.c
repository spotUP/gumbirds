/* Compiled with the 68000 compiler (-S) by make test-gum-pop-drop; tests/mame/gum_pop_drop_check.lua reads the Pop Drop state from RAM with
 * these values (target ABI: int is 32 bit). Order is fixed:
 * 1 Flow.state, 2 Game.mode, 3 Game.gg_pop, 4 pop.phase, 5 pop.hits, 6 pop.score, 7 pop.depth, 8 Flow.tables.gg_record[GG_POP_DROP],
 * 9 hero[0].x, 10 pop.plat[0] (PdPlat: x i16, y i16, kind, mids, live, hit), 11 Result.active, then FLOW_PLAYING, GAME_MODE_GUM, FLOW_GAME_OVER,
 * PD_FALL (12..15), 16 Game.cd_t (GET SET / GO! countdown, gg_countdown.h), 17 Game.score,
 * 25 pop.dist, 26 pop.pool_y, 27 b[0].landed, 28 b[0].card[0], 29 PD_POOL, 30 PD_RESULT,
 * 2P (gum_pop_drop_2p_check.lua): 18 Game.players, 19 pop.seq.players, 20 b[0].crash, 21 b[1].crash, 22 b[1].hits, 23 hero[1].x, 24 b[1].score. */
#include <stddef.h>
#include "../../src/core/flow.h"
#define G(m) (offsetof(Flow, game) + offsetof(Game, m))
#define P(m) (G(pop) + offsetof(GgPop, m))
#define B(i, m) (P(b) + (i) * sizeof(PdBird) + offsetof(PdBird, m))
unsigned int probe[] = {
    offsetof(Flow, state), G(mode), G(gg_pop), P(phase), B(0, hits), B(0, score), P(depth),
    offsetof(Flow, tables) + offsetof(ScoreTables, gg_record) + 4 * GG_POP_DROP,
    G(hero) + offsetof(Flier, x), P(plat), G(res) + offsetof(Result, active),
    FLOW_PLAYING, GAME_MODE_GUM, FLOW_GAME_OVER, PD_FALL, G(cd_t), G(score),
    G(players), P(seq) + offsetof(GgSeq, players), B(0, crash), B(1, crash), B(1, hits), G(hero) + sizeof(Flier) + offsetof(Flier, x), B(1, score),
    P(dist), P(pool_y), B(0, landed), B(0, card), PD_POOL, PD_RESULT,   /* 25..30 (the pool run, BRAWL_POOL=1) */
};
