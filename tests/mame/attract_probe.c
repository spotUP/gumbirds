/* Compiled with the 68000 compiler (-S) by make test-attract; tests/mame/attract_check.lua reads the flow from RAM with these
 * values (target ABI: int is 32 bit). Order is fixed:
 * 1 flow state, 2 Flow.demo, 3 Flow.mode (title highlight), 4 Game.mode, then the values the script compares with:
 * 5 FLOW_ATTRACT_TITLE, 6 FLOW_ATTRACT_DEMO, 7 GAME_MODE_ARENA, 8 GAME_MODE_TRIP, 9 GAME_MODE_ARCADE. */
#include <stddef.h>
#include "../../src/core/flow.h"
unsigned int probe[] = {
    offsetof(Flow, state), offsetof(Flow, demo), offsetof(Flow, mode), offsetof(Flow, game) + offsetof(Game, mode),
    FLOW_ATTRACT_TITLE, FLOW_ATTRACT_DEMO, GAME_MODE_ARENA, GAME_MODE_TRIP, GAME_MODE_ARCADE,
};
