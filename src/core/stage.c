#include "stage.h"
#include "flier.h"
#include "arena.h"

/* Layout (x, y top, w, h): the accepted floating-island layout (art: thoughts/shared/drafts/2026-11-10-islands-final/numbers.txt).
 * Two shore islands (the pair meets the seam at different heights), a middle island, two side ledges, a top centre and two top
 * corners. The island sprites (src/island.c) draw from this same table, so the drawn line is the floor. Widths are 4..7 columns of 16. */
const StagePlatform stage_platforms[STAGE_PLATFORM_COUNT] = {
    {   0, 148,  80, STAGE_PLATFORM_H },
    { 304, 164,  80, STAGE_PLATFORM_H },
    { 136, 128, 112, STAGE_PLATFORM_H },
    {  32,  92,  80, STAGE_PLATFORM_H },
    { 280, 108,  80, STAGE_PLATFORM_H },
    { 144,  68,  96, STAGE_PLATFORM_H },
    {   0,  36,  64, STAGE_PLATFORM_H },
    { 320,  52,  64, STAGE_PLATFORM_H },
};

/* Centre y = platform top - 6 (box half height 5.5): the flier starts resting on the platform. */
const StageSpawn stage_spawns[STAGE_SPAWN_COUNT] = {
    {  67,  86 }, { 317, 102 }, { 192,  62 }, {  29,  30 }, { 355,  46 }, {  38, 142 },
};

int32_t stage_floor_y(int32_t x16, int32_t feet16) {
    int32_t best = FLIER_NO_FLOOR;
    int32_t hw = FL_PX(FLIER_HALF_W);
    for (int i = 0; i < STAGE_PLATFORM_COUNT; i++) {
        const StagePlatform *p = &stage_platforms[i];
        int32_t top = FL_PX(p->y);
        if (top < feet16) continue;
        /* The platform's copy nearest the flier: an island that meets the seam is found from both sides. */
        int32_t cx = FL_PX(p->x) + (FL_PX(p->w) >> 1), nx = arena_near_x(cx, x16);
        if (nx + hw <= FL_PX(p->x) || nx - hw >= FL_PX(p->x + p->w)) continue;
        if (top < best) best = top;
    }
    return best;
}
