/* Host test for src/core/stage.[ch] and game_step_arena: floor lookup, layout bounds, and the arena step. */
#include <stdio.h>
#include <stdlib.h>
#include "../../src/core/game.h"
#include "../../src/core/stage.h"
#include "../../src/core/arena.h"
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
    /* Middle island (x 136..248, top 140): feet above it find it; feet below its top skip it. */
    CHECK(stage_floor_y(FL_PX(192), FL_PX(130)) == FL_PX(140));
    CHECK(stage_floor_y(FL_PX(192), FL_PX(140)) == FL_PX(140));
    CHECK(stage_floor_y(FL_PX(192), FL_PX(141)) == FLIER_NO_FLOOR); /* x 192 below the island: no shore island there */
    /* Highest platform at or below the feet wins: from y 50 over x 160 the top centre (72) beats the middle island (140). */
    CHECK(stage_floor_y(FL_PX(160), FL_PX(50)) == FL_PX(72));
    /* Gap between shore island (0..80) and middle island (136..): x 105 below y 164 has nothing. */
    CHECK(stage_floor_y(FL_PX(105), FL_PX(150)) == FLIER_NO_FLOOR);
    /* Edge overlap uses the flier half width: centre at 80 + 1 still touches (box 79..81), centre 82 does not. */
    CHECK(stage_floor_y(FL_PX(81), FL_PX(150)) == FL_PX(164));
    CHECK(stage_floor_y(FL_PX(82), FL_PX(150)) == FLIER_NO_FLOOR);
    /* Seam: the shore islands (0..80) and (304..384) join across x 384 = 0; found from both sides, and a flier
       position one arena width out (not yet wrapped) still finds the nearest copy. */
    CHECK(stage_floor_y(FL_PX(383), FL_PX(150)) == FL_PX(164));
    CHECK(stage_floor_y(FL_PX(1), FL_PX(150)) == FL_PX(164));
    CHECK(stage_floor_y(FL_PX(ARENA_W + 10), FL_PX(150)) == FL_PX(164));
    CHECK(stage_floor_y(FL_PX(-4), FL_PX(150)) == FL_PX(164));
    /* Top corner islands also join across the seam (y 40): a flier at either side stands on them. */
    CHECK(stage_floor_y(FL_PX(383), FL_PX(30)) == FL_PX(40));
    CHECK(stage_floor_y(FL_PX(0), FL_PX(30)) == FL_PX(40));
    /* No island at the edge strip below the shore top: no floor under feet lower than the shore. */
    CHECK(stage_floor_y(FL_PX(383), FL_PX(170)) == FLIER_NO_FLOOR);
    /* Spawns stand on a platform. */
    for (i = 0; i < STAGE_SPAWN_COUNT; i++) {
        int32_t f = stage_floor_y(FL_PX(stage_spawns[i].x), FL_PX(stage_spawns[i].y) + FL_PX(6));
        CHECK(f == FL_PX(stage_spawns[i].y + 6));
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
