/* Compiled with the 68000 compiler (-S) by make test-camera; tests/mame/camera_check.lua reads the slots and sizes it
 * compares the screen against through these values. Order is fixed: hero sprite slot, hazard sprite slot, sprites per
 * hazard bank, arena width, screen width, FLIER_HALF_W, ARENA_CAM_MAX, Sootling frame width, Sootling hit box offset
 * (SOOT_BOX_DX). The last two come from the generated frames.json numbers (build/gen/sootling_tables.h), the same
 * source src/main.c uses. */
#include "gen/sootling_tables.h"
#include "../../src/core/camera.h"
#include "../../src/core/flier.h"
#include "../../src/core/tuning.h"
#include "../../src/hazard.h"
#include "../../src/sprite_slots.h"
unsigned int probe[] = { HERO_SPRITE, HAZARD_SPRITE, HAZARD_STRIP_COLS, ARENA_W, SCREEN_W, FLIER_HALF_W, ARENA_CAM_MAX,
                        SOOTLING_ART_W, SOOTLING_BOX_FIRST_COL };
