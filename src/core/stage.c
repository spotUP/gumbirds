#include "stage.h"
#include "flier.h"
#include "arena.h"

/* Layout (x, y top, w, h): stage 1 = layout R01 (thoughts/spot/drafts/2026-11-12-arcade-layouts/gen3.py): two shore islands, a broad
 * middle shelf (index 2) and a top right island. The island sprites (src/island.c) draw from this same table, so the drawn line is the floor.
 * Widths are 5 or 7 columns of 16. The solid box hangs 12 px below the line (STAGE_PLATFORM_H, the drawn art depth). */
const StagePlatform stage_platforms[STAGE_PLATFORM_COUNT] = {
    {   0, 164,  80, STAGE_PLATFORM_H },
    { 280, 148,  80, STAGE_PLATFORM_H },
    { 128, 108, 112, STAGE_PLATFORM_H },
    { 296,  68,  80, STAGE_PLATFORM_H },
};

/* Centre y = platform top - 6 (box half height 5.5): the flier starts resting on the platform. */
const StageSpawn stage_spawns[STAGE_SPAWN_COUNT] = {
    { 160, 102 }, { 208, 102 }, { 336,  62 },
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

/* Reach of the solid list beyond the flier box: a flier moves a few pixels per frame, so a platform whose copy is this much
 * farther away than touching cannot be hit this frame. */
#define SOLID_REACH_PX 8

/* A flier that steers out from under a platform keeps going until its box is this far past the edge. */
#define OVERHEAD_CLEAR_PX 4

int stage_solids_near(int32_t x16, FlierSolid *out, int max) {
    int n = 0;
    for (int i = 0; i < STAGE_PLATFORM_COUNT && n < max; i++) {
        const StagePlatform *p = &stage_platforms[i];
        int32_t cx = arena_near_x(x16, FL_PX(p->x) + (FL_PX(p->w) >> 1));
        int32_t d = x16 > cx ? x16 - cx : cx - x16;
        if (d >= (FL_PX(p->w) >> 1) + FL_PX(FLIER_SOLID_MAX_HALF_W + SOLID_REACH_PX)) continue;
        /* The copy nearest the flier, so a platform at the seam is found from both sides. */
        out[n].x16 = cx - (FL_PX(p->w) >> 1);
        out[n].y16 = FL_PX(p->y);
        out[n].w16 = FL_PX(p->w);
        out[n].h16 = FL_PX(p->h);
        n++;
    }
    return n;
}

int stage_overhead_edge_dir(int32_t x16, int32_t top16) {
    for (int i = 0; i < STAGE_PLATFORM_COUNT; i++) {
        const StagePlatform *p = &stage_platforms[i];
        int32_t bottom = FL_PX(p->y + p->h);
        int32_t gap = top16 - bottom;
        int32_t cx, nx, hw;
        if (gap < 0 || gap > FL_PX(AI_OVERHEAD_PX)) continue;
        cx = FL_PX(p->x) + (FL_PX(p->w) >> 1);
        nx = arena_near_x(cx, x16);
        hw = FL_PX(FLIER_HALF_W + OVERHEAD_CLEAR_PX);
        if (nx + hw <= FL_PX(p->x) || nx - hw >= FL_PX(p->x + p->w)) continue;
        /* Leave by the nearer edge; a flier right of the centre goes right. */
        return nx >= cx ? 1 : -1;
    }
    return 0;
}
