#include "stage.h"
#include "flier.h"
#include "arena.h"

/* Layouts (x, y top, w, h) from thoughts/spot/drafts/2026-11-12-arcade-layouts/gen3.py, islands and rival spawns only, imported like R01: the player
 * start stays FLIER_START (island 0), rivals are the first `rivals` ground spawns of each layout (3 to STAGE_SPAWN_COUNT, own values, none on an island top above y 68 except old ones), spawn y = platform top - 6 (box half height 5.5: the
 * flier starts resting on the platform). The island sprites (src/island.c) draw from the current layout, so the drawn line is the floor.
 * Widths are the generated island pieces: 48, 64, 80, 96 or 112 (3 to 7 columns of 16). The solid box hangs 12 px below the line (STAGE_PLATFORM_H, the drawn art depth).
 * A layout with fewer than STAGE_PLATFORM_COUNT islands leaves the last slots zero (w 0: skipped by every loop, no sprite columns).
 * Left out of the data: air rivals, rivals past STAGE_SPAWN_COUNT, and the placed elements (posts, vents, flippers, drain, grates). */
typedef struct { StagePlatform plat[STAGE_PLATFORM_COUNT]; StageSpawn spawn[STAGE_SPAWN_COUNT]; int rivals; } StageLayout;
#define P(x, y, w) { x, y, w, STAGE_PLATFORM_H }
#define R01_PLAT { {   0, 164,  80, STAGE_PLATFORM_H }, { 280, 148,  80, STAGE_PLATFORM_H }, { 128, 108, 112, STAGE_PLATFORM_H }, { 296,  68,  80, STAGE_PLATFORM_H } }
#define R01_SPAWN { { 160, 102 }, { 208, 102 }, { 336,  62 } }
/* Order = the arcade stage set (src/core/arcade.c): R01 R02 N05 | N03 N06 N04 | N08 N02 N09 | R10 R07 R12b. */
static const StageLayout layouts[] = {
    { R01_PLAT, R01_SPAWN, 3 }, /* 0 R01 Lantern */
    { { P(0, 164, 80), P(280, 148, 80), P(112, 116, 96), P(232, 84, 64), P(48, 60, 80) },
      { { 136, 110 }, { 184, 110 }, { 264, 78 } }, 3 }, /* 1 R02 Shoulders */
    { { P(0, 164, 80), P(280, 148, 80), P(96, 116, 64), P(184, 92, 64), P(272, 68, 64), P(16, 52, 64) },
      { { 120, 110 }, { 224, 86 }, { 296, 62 }, { 320, 62 } }, 4 }, /* 2 N05 Wind chimes */
    { { P(0, 164, 80), P(280, 148, 80), P(264, 92, 112), P(16, 108, 64), P(120, 124, 80), P(152, 52, 64) },
      { { 140, 118 }, { 180, 118 }, { 184, 46 }, { 300, 86 } }, 4 }, /* 3 N03 Tunnel */
    { { P(0, 164, 80), P(280, 148, 80), P(112, 128, 48), P(8, 108, 48), P(296, 92, 48), P(200, 76, 48), P(128, 60, 48), P(56, 44, 48) },
      { { 136, 122 }, { 320, 86 }, { 224, 70 }, { 24, 102 } }, 4 }, /* 4 N06 Pebbles */
    { { P(0, 164, 80), P(280, 148, 80), P(168, 132, 48), P(168, 76, 48), P(88, 100, 48), P(264, 60, 64) },
      { { 98, 94 }, { 122, 94 }, { 192, 70 }, { 190, 126 } }, 4 }, /* 5 N04 Totem */
    { { P(0, 164, 80), P(280, 148, 80), P(96, 132, 48), P(168, 100, 48), P(240, 84, 48), P(312, 52, 48), P(16, 68, 48) },
      { { 120, 126 }, { 192, 94 }, { 264, 78 }, { 40, 62 } }, 4 }, /* 6 N08 Clothesline */
    { { P(0, 164, 80), P(280, 148, 80), P(136, 124, 80), P(32, 64, 80), P(264, 80, 80) },
      { { 152, 118 }, { 196, 118 }, { 88, 58 }, { 284, 74 }, { 316, 74 } }, 4 }, /* 7 N02 Gatekeeper */
    { { P(0, 164, 80), P(280, 148, 80), P(112, 128, 48), P(8, 108, 48), P(296, 92, 48), P(200, 76, 48), P(128, 60, 48), P(56, 44, 48) },
      { { 136, 122 }, { 320, 86 }, { 212, 70 }, { 24, 102 }, { 300, 86 } }, 3 }, /* 8 N09 Pebbles again */
    { { P(0, 164, 80), P(280, 148, 80), P(136, 108, 80), P(288, 72, 64) },
      { { 160, 102 }, { 192, 102 }, { 304, 66 }, { 320, 142 } }, 4 }, /* 9 R10 Open sky (air rivals dropped) */
    { { P(0, 164, 80), P(280, 148, 80), P(112, 132, 64), P(200, 116, 64), P(304, 84, 64), P(32, 100, 64), P(116, 68, 64) },
      { { 144, 126 }, { 224, 110 }, { 336, 78 }, { 86, 94 }, { 148, 62 } }, 4 }, /* 10 R07 Two stairs */
    { { P(0, 164, 80), P(280, 148, 80), P(132, 116, 96), P(24, 100, 64), P(272, 84, 64), P(148, 42, 64) },
      { { 72, 94 }, { 288, 78 }, { 160, 110 }, { 200, 110 }, { 40, 94 }, { 312, 78 } }, 4 }, /* 11 R12b Mirror crown */
    /* 12..23: the arcade copies of 0..11 with 16-24 px more air between islands (arcade.c ARC_LAYOUT_BASE); the arena (rounds) only ever plays 0..11. */
    { { P(0, 164, 80), P(264, 148, 80), P(128, 108, 112), P(296, 68, 80) },
      { { 160, 102 }, { 208, 102 }, { 336, 62 } }, 3 }, /* 12 R01 Lantern */
    { { P(0, 164, 80), P(264, 148, 80), P(112, 116, 96), P(232, 80, 64), P(48, 48, 80) },
      { { 136, 110 }, { 184, 110 }, { 267, 74 } }, 3 }, /* 13 R02 Shoulders */
    { { P(0, 164, 80), P(264, 148, 80), P(96, 116, 64), P(184, 92, 64), P(272, 68, 64), P(16, 52, 64) },
      { { 120, 110 }, { 224, 86 }, { 296, 62 }, { 320, 62 } }, 4 }, /* 14 N05 Wind chimes */
    { { P(0, 164, 80), P(264, 148, 80), P(264, 72, 112), P(16, 96, 64), P(120, 124, 80), P(152, 52, 64) },
      { { 140, 118 }, { 180, 118 }, { 189, 46 }, { 300, 66 } }, 4 }, /* 15 N03 Tunnel */
    { { P(0, 164, 80), P(264, 148, 80), P(112, 132, 48), P(8, 96, 48), P(296, 72, 48), P(192, 88, 48), P(128, 64, 48), P(64, 40, 48) },
      { { 136, 126 }, { 327, 66 }, { 225, 82 }, { 24, 90 } }, 4 }, /* 16 N06 Pebbles */
    { { P(0, 164, 80), P(264, 148, 80), P(160, 132, 48), P(160, 64, 48), P(88, 100, 48), P(264, 60, 64) },
      { { 131, 94 }, { 300, 142 }, { 184, 58 }, { 182, 126 } }, 4 }, /* 17 N04 Totem */
    { { P(0, 164, 80), P(264, 148, 80), P(96, 132, 48), P(168, 104, 48), P(240, 80, 48), P(312, 44, 48), P(16, 68, 48) },
      { { 120, 126 }, { 201, 98 }, { 273, 74 }, { 40, 62 } }, 4 }, /* 18 N08 Clothesline */
    { { P(0, 164, 80), P(264, 148, 80), P(136, 124, 80), P(32, 64, 80), P(264, 80, 80) },
      { { 152, 118 }, { 196, 118 }, { 88, 58 }, { 279, 74 }, { 316, 74 } }, 4 }, /* 19 N02 Gatekeeper */
    { { P(0, 164, 80), P(264, 148, 80), P(112, 128, 48), P(0, 96, 48), P(304, 72, 48), P(200, 76, 48), P(144, 52, 48), P(56, 44, 48) },
      { { 136, 122 }, { 335, 66 }, { 300, 142 }, { 16, 90 }, { 308, 66 } }, 3 }, /* 20 N09 Pebbles again */
    { { P(0, 164, 80), P(264, 148, 80), P(136, 108, 80), P(288, 72, 64) },
      { { 181, 102 }, { 205, 102 }, { 299, 66 }, { 304, 142 } }, 4 }, /* 21 R10 Open sky (air rivals dropped) */
    { { P(0, 164, 80), P(264, 148, 80), P(112, 136, 64), P(192, 112, 64), P(304, 72, 64), P(32, 96, 64), P(116, 68, 64) },
      { { 123, 130 }, { 201, 106 }, { 336, 66 }, { 86, 90 }, { 148, 62 } }, 4 }, /* 22 R07 Two stairs */
    { { P(0, 164, 80), P(264, 148, 80), P(132, 120, 96), P(24, 96, 64), P(272, 80, 64), P(148, 42, 64) },
      { { 72, 90 }, { 288, 74 }, { 160, 114 }, { 200, 114 }, { 40, 90 }, { 312, 74 } }, 4 }, /* 23 R12b Mirror crown */
    /* 24 bonus stage: a floor strip across the whole ring (island art is not drawn, island_layout.c) and the 4 gum nozzle tops
       (x, top = ARC_FLOOR_Y - height, 32 wide: arc_nozzle_x / arc_nozzle_top in arcade.c, checked in tests/host/test_arcade_game.c); no rivals. */
    { { P(0, 164, 192), P(192, 164, 192), P(58, 140, 32), P(130, 124, 32), P(250, 132, 32), P(322, 128, 32) },
      { { 176, 150 } }, 0 }, /* 24 Bonus */
};
#define LAYOUT_TOTAL ((int)(sizeof layouts / sizeof layouts[0]))
#define LAYOUT_COUNT 12 /* arena layouts; the rest belong to the arcade */

static int cur_layout;
/* The current layout, copied to RAM by stage_select (game_reset runs it before any use): the symbol stays a plain array, which the MAME checks read by address. */
StagePlatform stage_platforms[STAGE_PLATFORM_COUNT] = R01_PLAT; /* starts on layout 0 */
StageSpawn stage_spawns[STAGE_SPAWN_COUNT] = R01_SPAWN;

int stage_layout_count(void) { return LAYOUT_COUNT; }
int stage_layout_index(void) { return cur_layout; }
int stage_rival_count(void) { return layouts[cur_layout].rivals; }

static int cur_look;
int stage_look(void) { return cur_look; }
/* Subtraction, not '%': the 68000 has no 32 bit divide, and this runs once per round. */
int stage_look_for_level(int level) {
    while (level >= STAGE_LOOK_COUNT) level -= STAGE_LOOK_COUNT;
    return level < 0 ? STAGE_LOOK_ROOF : level;
}
void stage_set_level(int level) { cur_look = stage_look_for_level(level); }

void stage_select(int i) {
    cur_layout = i % LAYOUT_TOTAL;
    for (int k = 0; k < STAGE_PLATFORM_COUNT; k++) stage_platforms[k] = layouts[cur_layout].plat[k];
    for (int k = 0; k < STAGE_SPAWN_COUNT; k++) stage_spawns[k] = layouts[cur_layout].spawn[k];
}

int32_t stage_floor_y(int32_t x16, int32_t feet16) {
    int32_t best = FLIER_NO_FLOOR;
    int32_t hw = FL_PX(FLIER_HALF_W);
    for (int i = 0; i < STAGE_PLATFORM_COUNT; i++) {
        const StagePlatform *p = &stage_platforms[i];
        int32_t top = FL_PX(p->y);
        if (!p->w || top < feet16) continue;
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
        if (!p->w) continue;
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
        if (!p->w || gap < 0 || gap > FL_PX(AI_OVERHEAD_PX)) continue;
        cx = FL_PX(p->x) + (FL_PX(p->w) >> 1);
        nx = arena_near_x(cx, x16);
        hw = FL_PX(FLIER_HALF_W + OVERHEAD_CLEAR_PX);
        if (nx + hw <= FL_PX(p->x) || nx - hw >= FL_PX(p->x + p->w)) continue;
        /* Leave by the nearer edge; a flier right of the centre goes right. */
        return nx >= cx ? 1 : -1;
    }
    return 0;
}
