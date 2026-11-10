/* Compiled with the 68000 compiler (-S) by make test-slots; tests/mame/slot_order_check.lua reads the slot numbers
 * from src/sprite_slots.h through these values. Order is fixed: pool first slot, pool end slot, a background plane
 * slot below the pool (near plane), a slot above the hero (rain column, unused by the game until BG-2; the hazard strip heads swap on their own). */
#include "../../src/sprite_slots.h"
unsigned int probe[] = {
    POOL_SPRITE_BASE, POOL_SPRITE_BASE + POOL_SPRITE_COUNT, BG_NEAR_SPRITE, FG_RAIN_SPRITE,
};
