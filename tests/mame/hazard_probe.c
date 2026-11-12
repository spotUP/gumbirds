/* Compiled with the 68000 compiler (-S) by make test-hazard; tests/mame/hazard_check.lua reads the slot and palette
 * layout of the hazard strip through these values. Order is fixed: first hazard sprite slot, sprites per bank, first
 * hazard palette slot, hazard palette count, strip rows, strip top line. The per-hazard frames per step come from the
 * generated header (HAZARD_TABLE_STEP_FRAMES) through the Makefile. */
#include "../../src/core/hazard_kind.h"
#include "../../src/hazard.h"
#include "../../src/sprite_slots.h"
#include "../../src/vram_layout.h"
unsigned int probe[] = { HAZARD_SPRITE, HAZARD_STRIP_COLS, HAZARD_PAL_SLOT, HAZARD_PALETTE_COUNT, HAZARD_STRIP_ROWS, HAZARD_STRIP_TOP_Y,
                          HAZARD_ROUND_ORDER_LIST }; /* then the kind of rounds 0..3 */
