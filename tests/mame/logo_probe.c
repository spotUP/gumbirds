/* Compiled with the 68000 compiler (-S) by make test-logo; tests/mame/logo_check.lua reads these numbers instead of copying them.
 * Order is fixed: Flow.state, Flow.select_open, (removed field, 0), Flow.mode (offsets), TRIPSTRIP_TILE_BASE, TRIPSTRIP_TILE_COUNT,
 * LOGO_TILE_BASE, LOGO_TILE_COUNT, LOGO_SPRITE, LOGO_COUNT, TRIP_STRIP_SPRITE, TRIP_STRIP_COUNT, TITLE_SOOT_SPRITE, TITLE_SOOT_COUNT,
 * GAME_MODE_TRIP, FLOW_PLAYING, LOGO_STRIP_COUNT. Same defines src/main.c uses. */
#include <stddef.h>
#include "../../src/core/flow.h"
#include "../../src/sprite_slots.h"
#include "../../src/vram_layout.h"
#include "gen/logo_sprites.h"
#include "gen/tripstrip_sprites.h"
unsigned int probe[] = {
    offsetof(Flow, state), offsetof(Flow, select_open), 0 /* former select_paid slot, kept so the Lua layout indices stay */, offsetof(Flow, mode),
    TRIPSTRIP_TILE_BASE, TRIPSTRIP_TILE_COUNT, LOGO_TILE_BASE, LOGO_TILE_COUNT, LOGO_SPRITE, LOGO_COUNT,
    TRIP_STRIP_SPRITE, TRIP_STRIP_COUNT, TITLE_SOOT_SPRITE, TITLE_SOOT_COUNT, GAME_MODE_TRIP, FLOW_PLAYING, LOGO_STRIP_COUNT };
