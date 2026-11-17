/* Compiled with the 68000 compiler (-S) by make test-gum-big-blow; tests/mame/gum_big_blow_check.lua reads the Big Blow state from RAM with
 * these values (target ABI: int is 32 bit). Order is fixed:
 * 1 Flow.state, 2 Game.mode, 3 GgBlow.phase, 4 GgBlow.size, 5 GgBlow.last_size, 6 GgBlow.seq.tickets[0], 7 GgBlow.last_qualified, 8 Game.score,
 * then FLOW_PLAYING, GAME_MODE_GUM, GG_BLOW_INTRO, GG_BLOW_PLAY, GG_BLOW_RESULT (9..13). */
#include <stddef.h>
#include "../../src/core/flow.h"
#define G(m) (offsetof(Flow, game) + offsetof(Game, m))
#define B(m) (G(blow) + offsetof(GgBlow, m))
unsigned int probe[] = {
    offsetof(Flow, state), G(mode), B(phase), B(size), B(last_size), B(seq.tickets), B(last_qualified), G(score),
    FLOW_PLAYING, GAME_MODE_GUM, GG_BLOW_INTRO, GG_BLOW_PLAY, GG_BLOW_RESULT,
};
