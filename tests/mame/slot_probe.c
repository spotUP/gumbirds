/* Compiled with the 68000 compiler (-S) by make test-slots; tests/mame/slot_order_check.lua reads the slot numbers
 * from src/sprite_slots.h through these values. Order is fixed: island first slot, island end slot (the sprites that stand still above the background; the pool now holds only moving fliers), a background plane
 * slot below the pool (near plane), a slot above the hero (rain column, unused by the game until BG-2; the hazard strip heads swap on their own). */
#include "../../src/sprite_slots.h"
#include "../../src/vram_layout.h"
unsigned int probe[] = {
    ISLAND_SPRITE, ISLAND_SPRITE + ISLAND_COUNT, BG_NEAR_SPRITE, FG_RAIN_SPRITE,
    ISLAND_PAL_SLOT, ISLAND_PALETTE_COUNT, /* first island palette slot and how many */
};
