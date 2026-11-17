/* Compiled with the 68000 compiler (-S) by make test-gum-bubble-gather; tests/mame/gum_bubble_gather_check.lua reads the Bubble Gather state from RAM with
 * these values (target ABI: int is 32 bit). Order is fixed:
 * 1 Flow.state, 2 Game.mode, 3 Game.gg_gather, 4 ArcBonus.caught, 5 Game.score, 6 Flow.tables.gg_record[GG_BUBBLE_GATHER], 7 Result.active,
 * 8 hero[0].x, 9 hero[0].y, 10 bonus.b[0].live, 11 bonus.b[0].x, 12 bonus.b[0].y16, 13 sizeof(ArcBubble), 14 Game.bonus.spawned,
 * then FLOW_PLAYING, GAME_MODE_GUM, FLOW_GAME_OVER (15..17). */
#include <stddef.h>
#include "../../src/core/flow.h"
#define G(m) (offsetof(Flow, game) + offsetof(Game, m))
#define B(m) (G(bonus) + offsetof(ArcBonus, b) + offsetof(ArcBubble, m))
unsigned int probe[] = {
    offsetof(Flow, state), G(mode), G(gg_gather), G(bonus) + offsetof(ArcBonus, caught), G(score),
    offsetof(Flow, tables) + offsetof(ScoreTables, gg_record) + 4 * GG_BUBBLE_GATHER, G(res) + offsetof(Result, active),
    G(hero) + offsetof(Flier, x), G(hero) + offsetof(Flier, y), B(live), B(x), B(y16), sizeof(ArcBubble), G(bonus) + offsetof(ArcBonus, spawned),
    FLOW_PLAYING, GAME_MODE_GUM, FLOW_GAME_OVER,
};
