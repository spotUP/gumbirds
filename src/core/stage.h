/*
 * stage.h - the static arena stage: up to STAGE_PLATFORM_COUNT platform rectangles in world pixels.
 * Portable C99, no globals but the const table. Platforms are solid on every side: a flier lands on top, and bounces off the underside and the sides (flier_collide_solids).
 */
#ifndef BRAWL_STAGE_H
#define BRAWL_STAGE_H

#include <stdint.h>
#include "tuning.h"
#include "flier.h"

typedef struct {
    int16_t x, y, w, h; /* world pixels; y is the top (the floor the flier stands on) */
} StagePlatform;

extern const StagePlatform stage_platforms[STAGE_PLATFORM_COUNT];

/* Computer flier spawn points (world pixels, flier centre), each just above a platform top. */
typedef struct { int16_t x, y; } StageSpawn;
extern const StageSpawn stage_spawns[STAGE_SPAWN_COUNT];

/*
 * Floor for flier_step: the top (16.16) of the highest platform that lies at or below the flier feet (feet16, 16.16)
 * and overlaps the flier box (centre x16, half width FLIER_HALF_W). x16 and the platforms live on the wrapping arena
 * (arena.h): a platform that meets the seam is found from both sides. FLIER_NO_FLOOR when none.
 */
int32_t stage_floor_y(int32_t x16, int32_t feet16);

/*
 * The solid boxes (flier_collide_solids) of the platforms that can touch a flier centred at x16 this frame, one per
 * platform, the copy nearest x16 (a platform at the seam is found from both sides). Writes at most max boxes, returns
 * the count. The box runs from the platform top (the standing line) down STAGE_PLATFORM_H.
 */
/* Most solids stage_solids_near can return for one position (the platforms are few and spread out). */
#define STAGE_SOLIDS_MAX 8
int stage_solids_near(int32_t x16, FlierSolid *out, int max);

/*
 * For the computer fliers: -1 or +1 when a platform lies directly above a flier whose box top is top16 (its underside
 * is at most AI_OVERHEAD_PX above, and the flier is within a few pixels of its span), the direction of the
 * nearer edge to leave by; 0 when the way up is clear.
 */
int stage_overhead_edge_dir(int32_t x16, int32_t top16);

#endif
