/* Compiled with the 68000 compiler (-S) by make test-gum-visible; tests/mame/gum_visible_check.lua reads these (int is 32 bit). Order is fixed:
 * 1 Flow.state, 2 Game.mode, 3 Game.gg_toss, 4 Game.hero[0].x, 5 Toss.phase, 6 GgBlow.phase, 7 Flow.mode, 8 Flow.party_rule,
 * then FLOW_PLAYING, GAME_MODE_GUM, GAME_MODE_PARTY, PARTY_TOSS, GT_HOLD, GT_FLIGHT, GG_BLOW_PLAY (9..15),
 * then sprite slots and palettes: HERO_SPRITE, GUM_SPRITE, GUM_COUNT, ROOST_SPRITE, GUMBUBBLE_PAL_SLOT, GUM_PAL_SLOT (16..21). */
#include <stddef.h>
#include "../../src/core/flow.h"
#include "../../src/sprite_slots.h"
#include "../../src/vram_layout.h"
#define G(m) (offsetof(Flow, game) + offsetof(Game, m))
unsigned int probe[] = {
    offsetof(Flow, state), G(mode), G(gg_toss), G(hero) + offsetof(Flier, x), G(toss) + offsetof(GgToss, phase), G(blow) + offsetof(GgBlow, phase),
    offsetof(Flow, mode), offsetof(Flow, party_rule),
    FLOW_PLAYING, GAME_MODE_GUM, GAME_MODE_PARTY, PARTY_TOSS, GT_HOLD, GT_FLIGHT, GG_BLOW_PLAY,
    HERO_SPRITE, GUM_SPRITE, GUM_COUNT, ROOST_SPRITE, GUMBUBBLE_PAL_SLOT, GUM_PAL_SLOT,
};
