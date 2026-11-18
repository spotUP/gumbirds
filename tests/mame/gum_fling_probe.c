/* Compiled with the 68000 compiler (-S) by make test-gum-fling; tests/mame/gum_fling_check.lua reads the Gum Fling state from RAM with
 * these values (target ABI: int is 32 bit). Order is fixed:
 * 1 Flow.state, 2 Game.mode, 3 Game.gg_fling, 4 Game.fling.phase, 5 Game.fling.dist, 6 Game.score,
 * 7 Flow.tables.gg_record[GG_FLING], 8 Game.fling.foul, 9 Game.fling.seq.best[0],
 * then FLOW_PLAYING, GAME_MODE_GUM, GAME_MODE_TRIP, FLOW_GAME_OVER, GF_END, GF_WINDUP (10..15), 16 Flow.gg_card, 17 Game.mood (the snapshot run pokes it), 18 Game.fling.x (16.16 field scroll). */
#include <stddef.h>
#include "../../src/core/flow.h"
#define G(m) (offsetof(Flow, game) + offsetof(Game, m))
#define F(m) (G(fling) + offsetof(GgFling, m))
unsigned int probe[] = {
    offsetof(Flow, state), G(mode), G(gg_fling), F(phase), F(dist), G(score),
    offsetof(Flow, tables) + offsetof(ScoreTables, gg_record) + 4 * GG_FLING, F(foul), F(seq) + offsetof(GgSeq, best),
    FLOW_PLAYING, GAME_MODE_GUM, GAME_MODE_TRIP, FLOW_GAME_OVER, GF_END, GF_WINDUP, offsetof(Flow, gg_card), G(mood), F(x),
};
