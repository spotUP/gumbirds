#ifndef VRAM_LAYOUT_H
#define VRAM_LAYOUT_H
/*
 * C-ROM tile bases and palette slots (bank 1). C-ROM order is the Makefile cat order:
 * logo (256 tiles), obstacles, city, Sootling (the fliers), hazard strip, floating islands. Every base is derived from the generated headers,
 * never typed. Palette slots 0..1 are the fix layer.
 */
#include "gen/obs_sprites.h"
#include "gen/city_sprites.h"
#include "gen/sootling_sprites.h"
#include "gen/hazard_sprites.h"
#include "gen/island_sprites.h"

#define LOGO_TILE_COUNT 256
#define OBS_TILE_BASE LOGO_TILE_COUNT
#define CITY_TILE_BASE (OBS_TILE_BASE + OBS_TILE_COUNT)

#define SOOT_TILE_BASE (CITY_TILE_BASE + CITY_TILE_COUNT)
#define HAZARD_TILE_BASE (SOOT_TILE_BASE + SOOTLING_TILE_COUNT)
/* Auto-animation replaces the low 3 bits of the tile number: the hazard base must be a multiple of 8. */
_Static_assert((HAZARD_TILE_BASE & 7) == 0, "hazard tile base is not 8-aligned");
/* The sprite pipeline pads every set to a multiple of 8 tiles, so the island base stays aligned; its swap groups are
   8-aligned inside the set (asserted by tests/host/test_islands.py). */
#define ISLAND_TILE_BASE (HAZARD_TILE_BASE + HAZARD_TILE_COUNT)
_Static_assert((ISLAND_TILE_BASE & 7) == 0, "island tile base is not 8-aligned");

#define OBS_PAL_SLOT 2
#define CITY_PAL_SLOT (OBS_PAL_SLOT + OBS_PALETTE_COUNT)
#define SOOT_PAL_SLOT (CITY_PAL_SLOT + CITY_PALETTE_COUNT) /* palette 0: player, palette 1: computer fliers (red balloons) */

#define HAZARD_PAL_SLOT (SOOT_PAL_SLOT + SOOTLING_PALETTE_COUNT) /* palette p = hazard p: spikes, fire, water, lava */
#define ISLAND_PAL_SLOT (HAZARD_PAL_SLOT + HAZARD_PALETTE_COUNT) /* one palette per look */
_Static_assert(ISLAND_PAL_SLOT + ISLAND_PALETTE_COUNT <= 256, "palette slots exceed the 256 the hardware has");

#endif
