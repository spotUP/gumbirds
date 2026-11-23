/* Compiled with the 68000 compiler (-S) by the test-gum-poop target; tests/mame/gum_poop_check.lua reads the Poop the Man state from RAM with
 * these values (target ABI: int is 32 bit). Order is fixed:
 * 1 Flow.state, 2 Game.mode, 3 Game.gg_poop, 4 poop.phase, 5 poop.timer, 6 Game.score, 7 Flow.tables.gg_record[GG_POOP_MAN],
 * 8 poop.b[0].y (int16_t), 9 poop.b[0].score, 10 sizeof(PmBird), then FLOW_PLAYING, GAME_MODE_GUM, FLOW_GAME_OVER (11..13), 14 Flow.gg_card, 15 poop.splat_n, 16 poop.sfx_n,
 * 17 Game.res.active, 18 FLOW_ATTRACT_TITLE, 19 FLOW_NAME_ENTRY. */
#include <stddef.h>
#include "../../src/core/flow.h"
#define G(m) (offsetof(Flow, game) + offsetof(Game, m))
#define P(m) (G(poop) + offsetof(GgPoop, m))
unsigned int probe[] = {
    offsetof(Flow, state), G(mode), G(gg_poop), P(phase), P(timer), G(score),
    offsetof(Flow, tables) + offsetof(ScoreTables, gg_record) + 4 * GG_POOP_MAN,
    P(b) + offsetof(PmBird, y), P(b) + offsetof(PmBird, score), sizeof(PmBird),
    FLOW_PLAYING, GAME_MODE_GUM, FLOW_GAME_OVER, offsetof(Flow, gg_card), P(splat_n), P(sfx_n),
    G(res) + offsetof(Result, active), FLOW_ATTRACT_TITLE, FLOW_NAME_ENTRY, G(res) + offsetof(Result, podium),
};
