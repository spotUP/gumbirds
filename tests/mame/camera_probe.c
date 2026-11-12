/* Compiled with the 68000 compiler (-S) by make test-camera; tests/mame/camera_check.lua reads the slots and sizes it
 * compares the screen against through these values. Order is fixed: hero sprite slot, hazard sprite slot, sprites per
 * hazard bank, arena width, screen width, FLIER_HALF_W, ARENA_CAM_MAX, Sootling sprite width (SOOT_SPRITE_W, the art padded to whole
 * tiles), Sootling hit box offset in the sprite (SOOT_BOX_DX). Both come from src/vram_layout.h, the same defines src/main.c uses. Then the five background planes in draw order: first sprite slots (5 values), parallax factors
 * (5 values, CITY_TABLE_PLANE_K), column counts (5 values, CITY_TABLE_PLANE_COLS). Last three values: first island sprite slot (ISLAND_SPRITE), island count
 * (STAGE_PLATFORM_COUNT), line row of the island art (ISLAND_LINE_ROW); the island columns are w / 16 for the widths of
 * stage_platforms, read by the script from the ROM symbol (BRAWL_STAGE_ADDR). Then the object pool (rival fliers, BRAWL_POOL_ADDR = g_pool):
 * first pool sprite slot, sprites per object, object count, sizeof(PoolObj), its x and flags offsets, POOL_F_LIVE, FLIER_PAIR_REACH_HALF. */
#include <stddef.h>
#include "../../src/core/obj_pool.h"
#include "gen/city_tables.h"
#include "gen/island_tables.h"
#include "gen/sootling_tables.h"
#include "../../src/core/camera.h"
#include "../../src/core/flier.h"
#include "../../src/core/tuning.h"
#include "../../src/hazard.h"
#include "../../src/sprite_slots.h"
#include "../../src/vram_layout.h"
/* One struct so the generated tables (brace lists) sit in the same symbol, in order: 14 scalars, then K, then COLS. */
struct { unsigned int scalar[14]; unsigned int k[5]; unsigned int cols[5]; unsigned int island[3]; unsigned int pool[8]; } probe = {
    { HERO_SPRITE, HAZARD_SPRITE, HAZARD_STRIP_COLS, ARENA_W, SCREEN_W, FLIER_HALF_W, ARENA_CAM_MAX,
      SOOT_SPRITE_W, SOOT_BOX_DX,
      BG_SKY_SPRITE, BG_FAR_SPRITE, BG_MIDA_SPRITE, BG_MIDB_SPRITE, BG_NEAR_SPRITE },
    CITY_TABLE_PLANE_K, CITY_TABLE_PLANE_COLS,
    { ISLAND_SPRITE, STAGE_PLATFORM_COUNT, ISLAND_LINE_ROW },
    { POOL_SPRITE_BASE, POOL_COLS, POOL_MAX, sizeof(PoolObj), offsetof(PoolObj, x), offsetof(PoolObj, flags), POOL_F_LIVE, FLIER_PAIR_REACH_HALF } };
