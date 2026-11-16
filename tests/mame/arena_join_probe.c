/* Compiled with the 68000 compiler (-S) by make test-arena-join; tests/mame/arena_join_check.lua reads the join state from RAM with these
 * values (target ABI: int is 32 bit). Order is fixed:
 * 1 flow state, 2 Game.players, 3 Game.mode, 4 Game.score, 5 Game.matches_won, 6 hero[0].state, 7 sizeof(Flier), 8 lives[0].score,
 * 9 sizeof(ArcLives), then FLOW_PLAYING, FLIER_ALIVE, GAME_MODE_ARENA (10..12). */
#include <stddef.h>
#include "../../src/core/flow.h"
#define G(m) (offsetof(Flow, game) + offsetof(Game, m))
unsigned int probe[] = {
    offsetof(Flow, state), G(players), G(mode), G(score), G(matches_won), G(hero) + offsetof(Flier, state), sizeof(Flier),
    G(lives) + offsetof(ArcLives, score), sizeof(ArcLives), FLOW_PLAYING, FLIER_ALIVE, GAME_MODE_ARENA,
};
