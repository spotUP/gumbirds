/* Host test for src/core/stage.[ch] and game_step_arena: floor lookup, layout bounds, and the arena step. */
#include <stdio.h>
#include <stdlib.h>
#include "../../src/core/game.h"
#include "../../src/core/stage.h"
#include "../../src/core/arena.h"
#include "../../src/core/island_layout.h"
#include "../../src/sprite_slots.h"
#include "../../src/core/nameentry.h"

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

int main(void) {
    int i;
    /* Layout stays inside the world and above the water. */
    for (i = 0; i < STAGE_PLATFORM_COUNT; i++) {
        const StagePlatform *p = &stage_platforms[i];
        CHECK(p->x >= 0 && p->x + p->w <= ARENA_W);
        CHECK(p->y > 0 && p->y + p->h <= FLIER_WATER_Y);
    }
    /* The accepted layout (numbers.txt of the islands art), slot for slot. */
    {
        static const int16_t want[STAGE_PLATFORM_COUNT][3] = {
            { 0, 148, 80 }, { 304, 164, 80 }, { 136, 128, 112 }, { 32, 92, 80 }, { 280, 108, 80 }, { 144, 68, 96 }, { 0, 36, 64 }, { 320, 52, 64 },
        };
        for (i = 0; i < STAGE_PLATFORM_COUNT; i++)
            CHECK(stage_platforms[i].x == want[i][0] && stage_platforms[i].y == want[i][1] && stage_platforms[i].w == want[i][2]);
    }
    /* The island sprites and the collision read one table: every width has a piece list and the columns fill ISLAND_COUNT. */
    for (i = 0; i < STAGE_PLATFORM_COUNT; i++) CHECK(island_columns(stage_platforms[i].w) == stage_platforms[i].w / 16);
    CHECK(island_total_columns() == ISLAND_COUNT);
    CHECK(ISLAND_COUNT == 41);
    /* Middle island (x 136..248, top 128): feet above it find it; feet below its top skip it. */
    CHECK(stage_floor_y(FL_PX(192), FL_PX(120)) == FL_PX(128));
    CHECK(stage_floor_y(FL_PX(192), FL_PX(128)) == FL_PX(128));
    CHECK(stage_floor_y(FL_PX(192), FL_PX(129)) == FLIER_NO_FLOOR); /* x 192 below the island: no shore island there */
    /* Highest platform at or below the feet wins: from y 50 over x 160 the top centre (68) beats the middle island (128). */
    CHECK(stage_floor_y(FL_PX(160), FL_PX(50)) == FL_PX(68));
    /* Gap between the left shore island (0..80, top 148) and the middle island (136..): x 105 below y 140 has nothing. */
    CHECK(stage_floor_y(FL_PX(105), FL_PX(140)) == FLIER_NO_FLOOR);
    /* Edge overlap uses the flier half width: centre at 80 + 1 still touches (box 79..81), centre 82 does not. */
    CHECK(stage_floor_y(FL_PX(81), FL_PX(140)) == FL_PX(148));
    CHECK(stage_floor_y(FL_PX(82), FL_PX(140)) == FLIER_NO_FLOOR);
    /* Seam: the shore islands (0..80 at top 148, 304..384 at top 164) meet across x 384 = 0 at different heights. Feet 150 is
       below the left island top, so only the right island counts: found from x 383, from one arena width out and from -4,
       and from x 1 (the right island's box reaches over the seam: centre 1 + 384 = 385, box 383..387 touches 304..384). */
    CHECK(stage_floor_y(FL_PX(383), FL_PX(150)) == FL_PX(164));
    CHECK(stage_floor_y(FL_PX(1), FL_PX(150)) == FL_PX(164));
    CHECK(stage_floor_y(FL_PX(5), FL_PX(150)) == FLIER_NO_FLOOR); /* clear of the right island: only the left one, above the feet */
    CHECK(stage_floor_y(FL_PX(ARENA_W + 10), FL_PX(150)) == FLIER_NO_FLOOR);
    CHECK(stage_floor_y(FL_PX(-4), FL_PX(150)) == FL_PX(164));
    /* From above both: the left island (148) is the higher floor over x 0..80; at x 383 its seam copy (384..464) is touched too,
       so the higher floor 148 wins over the right island's 164; at x 360 only the right island is in reach. */
    CHECK(stage_floor_y(FL_PX(40), FL_PX(140)) == FL_PX(148));
    CHECK(stage_floor_y(FL_PX(383), FL_PX(140)) == FL_PX(148));
    CHECK(stage_floor_y(FL_PX(360), FL_PX(140)) == FL_PX(164));
    /* Top corner islands (0..64 at top 36, 320..384 at top 52) meet across the seam at different heights. */
    CHECK(stage_floor_y(FL_PX(383), FL_PX(30)) == FL_PX(36)); /* seam copy of the 36 island is touched and higher than 52 */
    CHECK(stage_floor_y(FL_PX(360), FL_PX(30)) == FL_PX(52));
    CHECK(stage_floor_y(FL_PX(0), FL_PX(30)) == FL_PX(36));
    CHECK(stage_floor_y(FL_PX(383), FL_PX(40)) == FL_PX(52));
    /* No island at the edge strip below the shore top: no floor under feet lower than the shore. */
    CHECK(stage_floor_y(FL_PX(383), FL_PX(170)) == FLIER_NO_FLOOR);
    /* Spawns stand on a platform, and no spawn box touches any island: the box (4 px wide, 11 px tall with balloons) lies inside its own
       island's columns, clear of every other island's collision rectangle and drawn rows (sprite top = y - 4, 16 tall). */
    for (i = 0; i < STAGE_SPAWN_COUNT; i++) {
        int32_t f = stage_floor_y(FL_PX(stage_spawns[i].x), FL_PX(stage_spawns[i].y) + FL_PX(6));
        int sx0 = stage_spawns[i].x - FLIER_HALF_W, sx1 = stage_spawns[i].x + FLIER_HALF_W;
        int sy0 = stage_spawns[i].y - 6, sy1 = stage_spawns[i].y + 5, own = 0;
        CHECK(f == FL_PX(stage_spawns[i].y + 6));
        for (int k = 0; k < STAGE_PLATFORM_COUNT; k++) {
            const StagePlatform *p = &stage_platforms[k];
            int overlap = sx1 > p->x && sx0 < p->x + p->w && sy1 > p->y - 4 && sy0 < p->y + 12;
            if (stage_spawns[i].y + 6 == p->y && sx0 >= p->x && sx1 <= p->x + p->w) own++;
            else CHECK(!overlap);
        }
        CHECK(own == 1);
    }
    CHECK(FLIER_START_X == 192);

    /* Arena step: a fresh game falls onto the middle island and stays alive; sentinel counts every step. */
    Game g;
    game_reset(&g, 1);
    for (i = 0; i < 120; i++) game_step_arena(&g, 0);
    CHECK(g.flier_steps == 120);
    CHECK(g.flier.on_ground && g.flier.state == FLIER_ALIVE && !g.over);
    CHECK(g.matches_won == 0); /* survival time no longer scores (design 3.3) */
    /* Over the gap between islands (x 100 has no platform below): the flier falls into the water and the run ends. */
    g.flier.x = FL_PX(100);
    g.flier.y = FL_PX(100);
    g.flier.on_ground = 0;
    for (i = 0; i < 2000 && !g.over; i++) game_step_arena(&g, 0);
    CHECK(g.over);
    CHECK(g.flier.state == FLIER_DROWNED);
    {
        uint32_t n = g.flier_steps;
        game_step_arena(&g, 0);
        CHECK(g.flier_steps == n); /* no steps after the run ended */
    }
    /* Flap raises the flier. */
    game_reset(&g, 1);
    for (i = 0; i < 60; i++) game_step_arena(&g, 0);
    {
        int32_t y0 = g.flier.y;
        for (i = 0; i < 20; i++) game_step_arena(&g, (i & 1) ? 0 : IN_A);
        CHECK(g.flier.y < y0);
    }
    printf("stage: %d checks, %d failures\n", checks, failures);
    return failures != 0;
}
