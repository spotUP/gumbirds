#ifndef SPRITE_SLOTS_H
#define SPRITE_SLOTS_H

/*
 * Hardware sprite slot map (381 sprites). Single place that says who owns which range.
 * A lower index draws behind a higher one. Overlap is rejected by the static asserts in main.c.
 *   0..15    background stars (BG_STAR_COUNT)
 *   16..25   sky objects: moon with clouds (5 columns), left clouds (5 columns)
 *   26..46   far skyline ring (21)
 *   47..67   mid skyline ring (21)
 *   68..88   roof ring (21)
 *   96..191  object pool (POOL_SPRITE_COUNT = POOL_MAX x POOL_COLS, src/core/obj_pool.h): object i owns
 *            POOL_SPRITE_BASE + i * POOL_COLS; platforms and computer fliers draw through it
 *   192..194 hero (HERO_SPRITE_COUNT)
 */
#define BG_STAR_SPRITE 0
#define BG_STAR_COUNT 16
#define BG_SKY_SPRITE 16
#define BG_SKY_COUNT 10
#define BG_FAR_SPRITE 26
#define BG_MID_SPRITE 47
#define BG_ROOF_SPRITE 68
#define BG_RING_COUNT 21
#define BG_SPRITE_END 89
#define POOL_SPRITE_BASE 96
#define POOL_SPRITE_COUNT 96
#define HERO_SPRITE 192
#define HERO_SPRITE_COUNT 3
#endif
