/* Compiled with the 68000 compiler (-S) by make test-vblank; tests/mame/vblank_check.lua reads the queue field offsets
 * and the sprite slot ranges (src/sprite_slots.h) through these values, in this order (1-based in Lua). */
#include <stddef.h>
#include "../../src/core/vram_queue.h"
#include "../../src/sprite_slots.h"
unsigned int probe[] = {
    offsetof(VramQueue, scb_hw), offsetof(VramQueue, strip), sizeof(VqStripKey), VQ_SCB_WORDS, VQ_SPRITES, /* 1..5 */
    BG_SKY_SPRITE, BG_FAR_SPRITE, BG_MIDA_SPRITE, BG_MIDB_SPRITE, BG_NEAR_SPRITE, BG_SPRITE_END,           /* 6..11 */
    ISLAND_SPRITE, ISLAND_SPRITE + ISLAND_COUNT,                                                           /* 12 13 */
    POOL_SPRITE_BASE, POOL_SPRITE_BASE + POOL_SPRITE_COUNT,                                                /* 14 15 */
    HERO_SPRITE, HERO_SPRITE + HERO_SPRITE_COUNT,                                                          /* 16 17 */
    HAZARD_SPRITE, HAZARD_SPRITE + HAZARD_COUNT,                                                           /* 18 19 */
    FG_RAIN_SPRITE, FG_SPRAY_SPRITE, TRIP_STRIP_SPRITE, TRIP_PICKUP_SPRITE, SPRITE_SLOT_END,               /* 20..24 */
};
