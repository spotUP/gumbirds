/* Compiled with the 68000 compiler (-S) by make test-gum-burst-race; tests/mame/gum_burst_race_check.lua reads the Burst Race state from RAM with
 * these values (target ABI: int is 32 bit). Order is fixed:
 * 1 Flow.state, 2 Game.mode, 3 Game.gg_race, 4 GgRace.phase, 5 GgRace.size[0], 6 GgRace.size[1], 7 GgRace.winner, 8 Game.score,
 * then FLOW_PLAYING, GAME_MODE_GUM, GG_RACE_INTRO, GG_RACE_PLAY, GG_RACE_RESULT (9..13), 14 first hardware sprite of the rival body
 * (pool object POOL_MAX - 2, P2_OBJ_BODY in src/main.c), 15 HERO_SPRITE, 16 GUM_SPRITE, 17 GUM_P2_SPRITE (the two gum bubbles), 18 Flow.gg_card. */
#include <stddef.h>
#include "../../src/core/flow.h"
#include "../../src/core/obj_pool.h"
#include "../../src/sprite_slots.h"
#define G(m) (offsetof(Flow, game) + offsetof(Game, m))
#define R(m) (G(race) + offsetof(GgRace, m))
unsigned int probe[] = {
    offsetof(Flow, state), G(mode), G(gg_race), R(phase), R(size), R(size) + 1, R(winner), G(score),
    FLOW_PLAYING, GAME_MODE_GUM, GG_RACE_INTRO, GG_RACE_PLAY, GG_RACE_RESULT,
    POOL_SPRITE_BASE + (POOL_MAX - 2) * POOL_COLS, HERO_SPRITE, GUM_SPRITE, GUM_P2_SPRITE, offsetof(Flow, gg_card),
};
