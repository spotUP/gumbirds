/* Compiled with the 68000 compiler (-S) by make test-coop; tests/mame/coop_check.lua reads the join state from RAM with
 * these values (target ABI: int is 32 bit). Order is fixed:
 * 1 flow state, 2 Game.players, 3 hero[0].state, 4 hero[0].y, 5 sizeof(Flier), 6 sizeof(ArcLives), 7 lives.state,
 * 8 lives.lives, 9 Game.mode, 10 hero[0].x, 11 Game.camera.cam,
 * then FLOW_PLAYING, FLIER_ALIVE, FLIER_PARACHUTE, FLIER_GONE, ARC_LIFE_PLAY, GAME_MODE_ARCADE. */
#include <stddef.h>
#include "../../src/core/flow.h"
#define G(m) (offsetof(Flow, game) + offsetof(Game, m))
unsigned int probe[] = {
    offsetof(Flow, state), G(players), G(hero) + offsetof(Flier, state), G(hero) + offsetof(Flier, y), sizeof(Flier), sizeof(ArcLives),
    G(lives) + offsetof(ArcLives, state), G(lives) + offsetof(ArcLives, lives), G(mode), G(hero) + offsetof(Flier, x), 0,
    FLOW_PLAYING, FLIER_ALIVE, FLIER_PARACHUTE, FLIER_GONE, ARC_LIFE_PLAY, GAME_MODE_ARCADE,
};
