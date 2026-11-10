#ifndef SPRITE_SLOTS_H
#define SPRITE_SLOTS_H

/*
 * Hardware sprite slot map (381 sprites). Single place that says who owns which range.
 * A lower index draws behind a higher one. Overlap is rejected by the static asserts in main.c, bg.c and the
 * host test tests/host/test_sprite_budget.c (which also checks the sprites per scanline from src/core/sprite_budget.c).
 * Plan: thoughts/shared/plans/2026-11-10-neo-geo-graphics-max.md, G1. Background planes 0..6 sit below the pool, the
 * hazard strip and the foreground above the hero.
 *   0..15    plane 1 background stars (BG_STAR_COUNT)
 *   16..25   plane 1 sky objects: moon with clouds (5 columns), left clouds (5 columns)
 *   26..35   plane 2 cloud bank (reserved, unbuilt)
 *   36..56   plane 3 far skyline ring (21)
 *   57..65   plane 4 airship (reserved, unbuilt)
 *   66..86   plane 5 mid skyline ring (21)
 *   87..95   plane 5 smoke and flags (reserved, unbuilt)
 *   96..116  plane 6 near rooftop ring, the roof (21)
 *   120..215 object pool (POOL_SPRITE_COUNT = POOL_MAX x POOL_COLS, src/core/obj_pool.h): object i owns
 *            POOL_SPRITE_BASE + i * POOL_COLS; platforms and computer fliers draw through it
 *   216..218 hero (HERO_SPRITE_COUNT)
 *   220..259 plane 7 hazard strip: two banks of 20 sprites (bank 0 at 220, bank 1 at 240), one visible at a time
 *   260..269 plane 8 rain columns (reserved), 270..273 spray, 274..275 edge cable
 */
#define BG_STAR_SPRITE 0
#define BG_STAR_COUNT 16
#define BG_SKY_SPRITE 16
#define BG_SKY_COUNT 10
#define BG_CLOUDBANK_SPRITE 26
#define BG_CLOUDBANK_COUNT 10
#define BG_FAR_SPRITE 36
#define BG_AIRSHIP_SPRITE 57
#define BG_AIRSHIP_COUNT 9
#define BG_MID_SPRITE 66
#define BG_SMOKE_SPRITE 87
#define BG_SMOKE_COUNT 9
#define BG_ROOF_SPRITE 96
#define BG_RING_COUNT 21
#define BG_SPRITE_END 117
#define POOL_SPRITE_BASE 120
#define POOL_SPRITE_COUNT 96
#define HERO_SPRITE 216
#define HERO_SPRITE_COUNT 3
#define HAZARD_SPRITE 220
#define HAZARD_COUNT 40
#define FG_RAIN_SPRITE 260
#define FG_RAIN_COUNT 10
#define FG_SPRAY_SPRITE 270
#define FG_SPRAY_COUNT 4
#define FG_EDGE_SPRITE 274
#define FG_EDGE_COUNT 2
#define SPRITE_SLOT_END 276
#endif
