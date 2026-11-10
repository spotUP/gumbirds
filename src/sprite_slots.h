#ifndef SPRITE_SLOTS_H
#define SPRITE_SLOTS_H

/*
 * Hardware sprite slot map (381 sprites). Single place that says who owns which range.
 * A lower index draws behind a higher one. Overlap is rejected by the static asserts in main.c, bg.c and the
 * host test tests/host/test_sprite_budget.c (which also checks the sprites per scanline from src/core/sprite_budget.c).
 * Plan: thoughts/shared/plans/2026-11-10-neo-geo-graphics-max.md, G1. The background sits below the pool, the
 * hazard strip and the foreground above the hero.
 *   0..109   parallax background planes, one sprite per 16 px column, back to front (BG_*_SPRITE, widths from
 *            CITY_TABLE_PLANE_COLS): sky 20, far 21, mid A 22, mid B 23, near 24 sprites
 *   110..119 free (clouds and airship drift, BG-2)
 *   120..160 floating islands (ISLAND_COUNT = the sprite columns of the stage platforms, 41): one sticky chain per platform in
 *            stage table order, drawn by src/island.c; they sit below the pool so fliers draw in front
 *   161..256 object pool (POOL_SPRITE_COUNT = POOL_MAX x POOL_COLS, src/core/obj_pool.h): object i owns
 *            POOL_SPRITE_BASE + i * POOL_COLS; computer fliers draw through it
 *   257..259 hero (HERO_SPRITE_COUNT)
 *   261..308 plane 7 hazard strip: two banks of 24 sprites (bank 0 at 261, bank 1 at 285), one visible at a time
 *   309..318 plane 8 rain columns (reserved), 319..322 spray
 */
#define BG_SKY_SPRITE 0
#define BG_SKY_COUNT 20
#define BG_SKY_Y0 0
#define BG_SKY_Y1 112
#define BG_FAR_SPRITE 20
#define BG_FAR_COUNT 21
#define BG_FAR_Y0 48
#define BG_FAR_Y1 128
#define BG_MIDA_SPRITE 41
#define BG_MIDA_COUNT 22
#define BG_MIDA_Y0 80
#define BG_MIDA_Y1 144
#define BG_MIDB_SPRITE 63
#define BG_MIDB_COUNT 23
#define BG_MIDB_Y0 112
#define BG_MIDB_Y1 176
#define BG_NEAR_SPRITE 86
#define BG_NEAR_COUNT 24
#define BG_NEAR_Y0 128
#define BG_NEAR_Y1 224
#define BG_SPRITE_END 110
#define ISLAND_SPRITE 120
#define ISLAND_COUNT 41
#define POOL_SPRITE_BASE 161
#define POOL_SPRITE_COUNT 96
#define HERO_SPRITE 257
#define HERO_SPRITE_COUNT 3
#define HAZARD_SPRITE 261
#define HAZARD_COUNT 48
#define FG_RAIN_SPRITE 309
#define FG_RAIN_COUNT 10
#define FG_SPRAY_SPRITE 319
#define FG_SPRAY_COUNT 4
#define SPRITE_SLOT_END 323
#endif
