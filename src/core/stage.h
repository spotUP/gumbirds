/*
 * stage.h - the static arena stage: up to STAGE_PLATFORM_COUNT platform rectangles in world pixels.
 * Portable C99, no globals but the const table. Platforms are solid from above only.
 */
#ifndef BRAWL_STAGE_H
#define BRAWL_STAGE_H

#include <stdint.h>
#include "tuning.h"

typedef struct {
    int16_t x, y, w, h; /* world pixels; y is the top (the floor the flier stands on) */
} StagePlatform;

extern const StagePlatform stage_platforms[STAGE_PLATFORM_COUNT];

/* Computer flier spawn points (world pixels, flier centre), each just above a platform top. */
typedef struct { int16_t x, y; } StageSpawn;
extern const StageSpawn stage_spawns[STAGE_SPAWN_COUNT];

/*
 * Floor for flier_step: the top (16.16) of the highest platform that lies at or below the flier feet (feet16, 16.16)
 * and overlaps the flier box (centre x16, half width FLIER_HALF_W). FLIER_NO_FLOOR when none.
 */
int32_t stage_floor_y(int32_t x16, int32_t feet16);

#endif
