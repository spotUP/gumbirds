#include "stage.h"
#include "flier.h"
#include "arena.h"

/* Layout (x, y top, w, h). Two shore islands at the water, a middle island, two side ledges, a top centre and two top corners. */
const StagePlatform stage_platforms[STAGE_PLATFORM_COUNT] = {
    {   0, 164,  80, STAGE_PLATFORM_H },
    { 304, 164,  80, STAGE_PLATFORM_H },
    { 136, 140, 112, STAGE_PLATFORM_H },
    {  32, 104,  80, STAGE_PLATFORM_H },
    { 280, 104,  80, STAGE_PLATFORM_H },
    { 144,  72,  96, STAGE_PLATFORM_H },
    {   0,  40,  56, STAGE_PLATFORM_H },
    { 328,  40,  56, STAGE_PLATFORM_H },
};

/* Centre y = platform top - 6 (box half height 5.5): the flier starts resting on the platform. */
const StageSpawn stage_spawns[STAGE_SPAWN_COUNT] = {
    {  67,  98 }, { 317,  98 }, { 192,  66 }, {  29,  34 }, { 355,  34 }, {  38, 158 },
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
