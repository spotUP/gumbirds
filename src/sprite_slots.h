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
 *   128..191 obstacles (OBSTACLE_SPRITE_COUNT slots)
 *   192..194 hero (HERO_SPRITE_COUNT)
 *   200..216 laser: 4 beams x 2 columns, kill flash, heat bar (8 pairs); in front of the hero
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
#define OBSTACLE_SPRITE_BASE 128
#define OBSTACLE_SPRITE_COUNT 64
#define HERO_SPRITE 192
#define HERO_SPRITE_COUNT 3
#define LASER_BEAM_SPRITE 200
#define LASER_BEAM_SLOTS 8
#define LASER_FLASH_SPRITE (LASER_BEAM_SPRITE + LASER_BEAM_SLOTS)
#define LASER_BAR_SPRITE (LASER_FLASH_SPRITE + 1)
#define LASER_BAR_SLOTS 8
#define LASER_SPRITE_END (LASER_BAR_SPRITE + LASER_BAR_SLOTS)

#endif
