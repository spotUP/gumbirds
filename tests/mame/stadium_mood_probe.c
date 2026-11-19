/* Compiled with the 68000 compiler (-S): the one .long is offsetof(Flow, game.mood) for tests/mame/stadium_snap.lua. */
#include <stddef.h>
#include "../../src/core/flow.h"
unsigned int probe[] = { offsetof(Flow, game) + offsetof(Game, mood) };
