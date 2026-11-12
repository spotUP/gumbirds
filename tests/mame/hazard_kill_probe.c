/* Compiled with the 68000 compiler (-S) by make test-hazard-kill; tests/mame/hazard_kill_check.lua compares the kill
 * lines the ROM was built with against the spec numbers. Order is fixed: HAZARD_KINDS, the built kill line of each kind
 * (hazard_kill_px 0..3: spikes, fire, water, lava), HAZARD_STRIP_TOP_Y, FLIER_HALF_H16_BALLOON, offsetof(Flier, kill_y)
 * in Flow, offsetof(Game, hazard_kind) in Flow, HERO_SPRITE, HERO_SPRITE_COUNT, HAZARD_SPRITE, HAZARD_STRIP_COLS, then for the dead fall: FLIER_HALF_H16_NOBAL, FLIER_REMOVE_FEET_Y, FLIER_ART_H, SCREEN_H, HAZARD_COUNT, DEAD_BODY_SPRITE, DEAD_BODY_COUNT. */
#include <stddef.h>
#include "../../src/core/flow.h"
#include "../../src/core/hazard_kind.h"
#include "../../src/hazard.h"
#include "../../src/sprite_slots.h"
unsigned int probe[] = {
    HAZARD_KINDS, HAZARD_KILL_SPIKES, HAZARD_KILL_FIRE, HAZARD_KILL_WATER, HAZARD_KILL_LAVA,
    HAZARD_STRIP_TOP_Y, FLIER_HALF_H16_BALLOON,
    offsetof(Flow, game) + offsetof(Game, flier) + offsetof(Flier, kill_y),
    offsetof(Flow, game) + offsetof(Game, hazard_kind),
    HERO_SPRITE, HERO_SPRITE_COUNT, HAZARD_SPRITE, HAZARD_STRIP_COLS,
    FLIER_HALF_H16_NOBAL, FLIER_REMOVE_FEET_Y, FLIER_ART_H, SCREEN_H, HAZARD_COUNT, DEAD_BODY_SPRITE, DEAD_BODY_COUNT,
};
