/* Compiled with the 68000 compiler (-S) by make test-camera; tests/mame/camera_check.lua reads the slots and sizes it
 * compares the screen against through these values. Order is fixed: hero sprite slot, hazard sprite slot, sprites per
 * hazard bank, arena width, screen width, FLIER_HALF_W, ARENA_CAM_MAX. The Sootling frame width (16) and SOOT_BOX_DX (6)
 * are file-local defines of src/main.c and are repeated in the Lua check. */
#include "../../src/core/camera.h"
#include "../../src/core/flier.h"
#include "../../src/core/tuning.h"
#include "../../src/hazard.h"
#include "../../src/sprite_slots.h"
unsigned int probe[] = { HERO_SPRITE, HAZARD_SPRITE, HAZARD_STRIP_COLS, ARENA_W, SCREEN_W, FLIER_HALF_W, ARENA_CAM_MAX };
