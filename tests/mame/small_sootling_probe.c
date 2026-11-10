/* Compiled with the 68000 compiler (-S) by make test-small-sootling; tests/mame/small_sootling_check.lua compares the
 * values the ROM was built with against the small Sootling spec. Order is fixed: SOOTLING_ART_W, SOOTLING_ART_H,
 * SOOTLING_TILE_COUNT (generated from assets/flier/sootling_sheet.png), SOOT_SPRITE_W, SOOT_BOX_DX (src/vram_layout.h),
 * HERO_SPRITE, FLIER_HALF_W, FLIER_HALF_H16_BALLOON, ARENA_W, SCREEN_W. */
#include "gen/sootling_tables.h"
#include "../../src/core/camera.h"
#include "../../src/core/flier.h"
#include "../../src/core/tuning.h"
#include "../../src/sprite_slots.h"
#include "../../src/vram_layout.h"
unsigned int probe[] = {
    SOOTLING_ART_W, SOOTLING_ART_H, SOOTLING_TILE_COUNT, SOOT_SPRITE_W, SOOT_BOX_DX,
    HERO_SPRITE, FLIER_HALF_W, FLIER_HALF_H16_BALLOON, ARENA_W, SCREEN_W,
};
