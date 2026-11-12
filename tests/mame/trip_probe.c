/* Compiled with the 68000 compiler (-S) by make test-trip; tests/mame/trip_check.lua reads these numbers instead of
 * copying them (target ABI). Order is fixed: Flow.state, Game.mode, Game.trip.px, .frac, .speed, .steps,
 * TRIP_SCROLL_START, TRIP_SCROLL_MAX, SCREEN_W, ARENA_W, Game.trip_hold, Game.trip_gen.made, then (step V1, generated islands)
 * Game.trip_gen.ring, sizeof(TripChunk), TripGen.head, .count, TripChunk.wx, island.present, island.x, island.y, island.w,
 * TRIP_VIEW_ISLAND_BLOCK, TRIP_GEN_RING, ISLAND_SPRITE, ISLAND_COUNT, ISLAND_LINE_ROW, TripGen.next_wx, then (step V2, kill strips)
 * TRIPSTRIP_TILE_BASE, TRIPSTRIP_TILE_COUNT, TRIPSTRIP_PAL_SLOT, TRIP_STRIP_SPRITE, TRIP_STRIP_COUNT, TRIPSTRIP_STEP_TICKS,
 * TripChunk.win_top, .win_bottom, TRIP_CHUNK_PX, TRIP_VIEW_STRIP_BOTTOM, TRIP_VIEW_STRIP_COLS, then (step V3, pickups) TRIPPICKUP_TILE_BASE, _TILE_COUNT, _PAL_SLOT, TRIP_PICKUP_SPRITE, _COUNT, pickup present/x/y offsets, left/top offsets, idle ticks, idle frames, then (step V4, hazards) TRIPHAZ tile base/count, palette slot/count, POOL_SPRITE_BASE, POOL_COLS, hazard layout offsets, BG_NEAR_SPRITE/COUNT, TRIP_SWEEP_STEP. */
#include <stddef.h>
#include "../../src/core/flow.h"
#include "../../src/core/arena.h"
#include "../../src/core/tuning.h"
#include "../../src/core/trip_view.h"
#include "../../src/core/obj_pool.h"
#include "../../src/sprite_slots.h"
#include "gen/island_tables.h"
#include "gen/tripstrip_tables.h"
#include "gen/trippickup_tables.h"
#include "gen/trippickup_sprites.h"
#include "gen/triphaz_tables.h"
#include "gen/tripmeter.h"
#include "../../src/vram_layout.h"
#define G(m) (offsetof(Flow, game) + offsetof(Game, m))
#define T(m) (offsetof(Flow, game) + offsetof(Game, trip) + offsetof(Trip, m))
unsigned int probe[] = {
    offsetof(Flow, state), G(mode), T(px), T(frac), T(speed), T(steps),
    TRIP_SCROLL_START, TRIP_SCROLL_MAX, SCREEN_W, ARENA_W,
    G(trip_hold), G(trip_gen) + offsetof(TripGen, made),
    G(trip_gen) + offsetof(TripGen, ring), sizeof(TripChunk), G(trip_gen) + offsetof(TripGen, head), G(trip_gen) + offsetof(TripGen, count),
    offsetof(TripChunk, wx), offsetof(TripChunk, island) + offsetof(TripGenIsland, present), offsetof(TripChunk, island) + offsetof(TripGenIsland, x),
    offsetof(TripChunk, island) + offsetof(TripGenIsland, y), offsetof(TripChunk, island) + offsetof(TripGenIsland, w),
    TRIP_VIEW_ISLAND_BLOCK, TRIP_GEN_RING, ISLAND_SPRITE, ISLAND_COUNT, ISLAND_LINE_ROW,
    G(trip_gen) + offsetof(TripGen, next_wx),
    TRIPSTRIP_TILE_BASE, TRIPSTRIP_TILE_COUNT, TRIPSTRIP_PAL_SLOT, TRIP_STRIP_SPRITE, TRIP_STRIP_COUNT, TRIPSTRIP_STEP_TICKS,
    offsetof(TripChunk, win_top), offsetof(TripChunk, win_bottom), TRIP_CHUNK_PX, TRIP_VIEW_STRIP_BOTTOM, TRIP_VIEW_STRIP_COLS,
    /* step V3, pickups: tile base, tile count, palette slot, first sprite, sprite count, TripChunk.pickup present/x/y, sprite left and top
     * offsets from the pickup centre, the idle animation ticks per frame and frame count */
    TRIPPICKUP_TILE_BASE, TRIPPICKUP_TILE_COUNT, TRIPPICKUP_PAL_SLOT, TRIP_PICKUP_SPRITE, TRIP_PICKUP_COUNT,
    offsetof(TripChunk, pickup) + offsetof(TripGenPickup, present), offsetof(TripChunk, pickup) + offsetof(TripGenPickup, x),
    offsetof(TripChunk, pickup) + offsetof(TripGenPickup, y), TRIP_VIEW_PICKUP_LEFT_OFF, TRIP_VIEW_PICKUP_TOP_OFF,
    TRIPPICKUP_PICKUP_IDLE_TICKS, TRIPPICKUP_PICKUP_IDLE_FRAMES,
    /* step V4, hazards and near plane: TRIPHAZ tile base, tile count, palette slot, palette count, POOL_SPRITE_BASE, POOL_COLS,
     * TripChunk.n_haz, .haz, sizeof(TripGenHazard), its kind/x/y/amp/phase offsets, BG_NEAR_SPRITE, BG_NEAR_COUNT, TRIP_SWEEP_STEP */
    TRIPHAZ_TILE_BASE, TRIPHAZ_TILE_COUNT, TRIPHAZ_PAL_SLOT, TRIPHAZ_PALETTE_COUNT, POOL_SPRITE_BASE, POOL_COLS,
    offsetof(TripChunk, n_haz), offsetof(TripChunk, haz), sizeof(TripGenHazard),
    offsetof(TripGenHazard, kind), offsetof(TripGenHazard, x), offsetof(TripGenHazard, y), offsetof(TripGenHazard, amp), offsetof(TripGenHazard, phase),
    BG_NEAR_SPRITE, BG_NEAR_COUNT, TRIP_SWEEP_STEP,
    /* gum meter: TRIPMETER_STEPS (68), Trip.gum offset (69), TRIPMETER_BASE (70), TRIPMETER_CELLS (71), FIXFONT_PAL_WHITE (72) */
    TRIPMETER_STEPS, T(gum), TRIPMETER_BASE, TRIPMETER_CELLS, FIXFONT_PAL_WHITE,
    /* pickup collect effect (step V6): sizeof(TrippickupFrame) (73), its tile_offset offset (74), collect frames (75), collect ticks per frame (76) */
    sizeof(TrippickupFrame), offsetof(TrippickupFrame, tile_offset), TRIPPICKUP_PICKUP_COLLECT_FRAMES, TRIPPICKUP_PICKUP_COLLECT_TICKS,
    /* mid B plane (option D, bottom row restored): BG_MIDB_SPRITE (77), BG_MIDB_COUNT (78) */
    BG_MIDB_SPRITE, BG_MIDB_COUNT,
    /* window clamp (T8): FLIER_HALF_H16_BALLOON (79), FLIER_HALF_H16_NOBAL (80), FLIER_HALF_W (81), FLIER_FALLING (82) */
    FLIER_HALF_H16_BALLOON, FLIER_HALF_H16_NOBAL, FLIER_HALF_W, FLIER_FALLING,
    /* top edge: FLIER_CEILING_FEET_Y (83), FLIER_RIVAL_CEILING_DROP (84) */
    FLIER_CEILING_FEET_Y, FLIER_RIVAL_CEILING_DROP,
};
