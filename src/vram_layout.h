#ifndef VRAM_LAYOUT_H
#define VRAM_LAYOUT_H
/*
 * C-ROM tile bases and palette slots (bank 1). C-ROM order is the Makefile cat order:
 * logo (256 tiles), hero, obstacles, city, heat bar. Every base is derived from the generated headers,
 * never typed. Palette slots 0..1 are the fix layer.
 */
#include "gen/hero_sprites.h"
#include "gen/obs_sprites.h"
#include "gen/city_sprites.h"
#include "gen/heat_sprites.h"

#define LOGO_TILE_COUNT 256
#define HERO_TILE_BASE LOGO_TILE_COUNT
#define OBS_TILE_BASE (HERO_TILE_BASE + HERO_TILE_COUNT)
#define CITY_TILE_BASE (OBS_TILE_BASE + OBS_TILE_COUNT)

#define HEAT_TILE_BASE (CITY_TILE_BASE + CITY_TILE_COUNT)

#define HERO_PAL_SLOT 2
#define OBS_PAL_SLOT (HERO_PAL_SLOT + HERO_PALETTE_COUNT)
#define CITY_PAL_SLOT (OBS_PAL_SLOT + OBS_PALETTE_COUNT)
#define HEAT_PAL_SLOT (CITY_PAL_SLOT + CITY_PALETTE_COUNT)

#endif
