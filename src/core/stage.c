#include "stage.h"
#include "flier.h"

/* Layout (x, y top, w, h). Two shore islands at the water, a middle island, two side ledges, a top centre and two top corners. */
const StagePlatform stage_platforms[STAGE_PLATFORM_COUNT] = {
    {   0, 164,  64, STAGE_PLATFORM_H },
    { 256, 164,  64, STAGE_PLATFORM_H },
    { 112, 140,  96, STAGE_PLATFORM_H },
    {  24, 104,  64, STAGE_PLATFORM_H },
    { 232, 104,  64, STAGE_PLATFORM_H },
    { 120,  72,  80, STAGE_PLATFORM_H },
    {   0,  40,  48, STAGE_PLATFORM_H },
    { 272,  40,  48, STAGE_PLATFORM_H },
};

int32_t stage_floor_y(int32_t x16, int32_t feet16) {
    int32_t best = FLIER_NO_FLOOR;
    int32_t hw = FL_PX(FLIER_HALF_W);
    for (int i = 0; i < STAGE_PLATFORM_COUNT; i++) {
        const StagePlatform *p = &stage_platforms[i];
        int32_t top = FL_PX(p->y);
        if (top < feet16) continue;
        if (x16 + hw <= FL_PX(p->x) || x16 - hw >= FL_PX(p->x + p->w)) continue;
        if (top < best) best = top;
    }
    return best;
}
