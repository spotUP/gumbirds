/* Compiled with the 68000 compiler (-S) by make test-gum-flap-dash; tests/mame/gum_flap_dash_check.lua reads the Flap Dash state from RAM with
 * these values (target ABI: int is 32 bit). Order is fixed:
 * 1 Flow.state, 2 Game.mode, 3 Game.gg_dash, 4 GgDash.laps, 5 GgDash.done, 6 GgDash.frames, 7 Game.score, 8 Flow.tables.gg_record[GG_FLAP_DASH],
 * then FLOW_PLAYING, GAME_MODE_GUM, FLOW_GAME_OVER (9..11). */
#include <stddef.h>
#include "../../src/core/flow.h"
#define G(m) (offsetof(Flow, game) + offsetof(Game, m))
#define D(m) (G(dash) + offsetof(GgDash, m))
unsigned int probe[] = {
    offsetof(Flow, state), G(mode), G(gg_dash), D(laps), D(done), D(frames), G(score),
    offsetof(Flow, tables) + offsetof(ScoreTables, gg_record) + 4 * GG_FLAP_DASH,
    FLOW_PLAYING, GAME_MODE_GUM, FLOW_GAME_OVER,
};
