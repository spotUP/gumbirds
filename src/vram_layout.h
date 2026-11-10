#ifndef VRAM_LAYOUT_H
#define VRAM_LAYOUT_H
/*
 * C-ROM tile bases and palette slots (bank 1). C-ROM order is the Makefile cat order:
 * logo (256 tiles), obstacles, city, Sootling (the fliers). Every base is derived from the generated headers,
 * never typed. Palette slots 0..1 are the fix layer.
 */
#include "gen/obs_sprites.h"
#include "gen/city_sprites.h"
#include "gen/sootling_sprites.h"

#define LOGO_TILE_COUNT 256
#define OBS_TILE_BASE LOGO_TILE_COUNT
#define CITY_TILE_BASE (OBS_TILE_BASE + OBS_TILE_COUNT)

#define SOOT_TILE_BASE (CITY_TILE_BASE + CITY_TILE_COUNT)

#define OBS_PAL_SLOT 2
#define CITY_PAL_SLOT (OBS_PAL_SLOT + OBS_PALETTE_COUNT)
#define SOOT_PAL_SLOT (CITY_PAL_SLOT + CITY_PALETTE_COUNT) /* palette 0: player, palette 1: computer fliers (red balloons) */

#endif
