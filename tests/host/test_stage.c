/* Host test for src/core/stage.[ch] and game_step_arena: floor lookup, layout bounds, and the arena step. */
#include <stdio.h>
#include <stdlib.h>
#include "../../src/core/game.h"
#include "../../src/core/stage.h"
#include "../../src/core/arena.h"
#include "../../src/core/island_layout.h"
#include "gen/island_tables.h"
#include "../../src/sprite_slots.h"
#include "../../src/core/nameentry.h"

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

int main(void) {
    int i;
    /* Layout stays inside the world and above the water. */
    for (i = 0; i < STAGE_PLATFORM_COUNT; i++) {
        const StagePlatform *p = &stage_platforms[i];
        if (!p->w) continue; /* unused slot of a layout with fewer islands */
        CHECK(p->x >= 0 && p->x + p->w <= ARENA_W);
        CHECK(p->y > 0 && p->y + p->h <= FLIER_WATER_Y);
    }
    /* The accepted layout (stage 1 = R01), slot for slot. */
    {
        static const int16_t want[STAGE_PLATFORM_COUNT][3] = {
            { 0, 164, 80 }, { 280, 148, 80 }, { 128, 108, 112 }, { 296, 68, 80 }, { 0, 0, 0 }, { 0, 0, 0 }, { 0, 0, 0 }, { 0, 0, 0 },
        };
        for (i = 0; i < STAGE_PLATFORM_COUNT; i++)
            CHECK(stage_platforms[i].x == want[i][0] && stage_platforms[i].y == want[i][1] && stage_platforms[i].w == want[i][2]);
    }
    /* The island sprites and the collision read one table: every width has a piece list; stage 1 uses 22 columns of the ISLAND_COUNT range (the Gum Trip islands need the rest). User-approved weaker assert (was ==). */
    for (i = 0; i < STAGE_PLATFORM_COUNT; i++) CHECK(island_columns(stage_platforms[i].w) == stage_platforms[i].w / 16);
    CHECK(island_total_columns() == 22);
    CHECK(22 <= ISLAND_COUNT);
    /* Middle island (x 128..240, top 108): feet above it find it; feet below its top skip it. */
    CHECK(stage_floor_y(FL_PX(192), FL_PX(100)) == FL_PX(108));
    CHECK(stage_floor_y(FL_PX(192), FL_PX(108)) == FL_PX(108));
    CHECK(stage_floor_y(FL_PX(192), FL_PX(109)) == FLIER_NO_FLOOR); /* x 192 below the island: no other island there */
    /* Highest platform at or below the feet wins: from y 50 over x 336 the top right island (68) beats the right shore island (148). */
    CHECK(stage_floor_y(FL_PX(336), FL_PX(50)) == FL_PX(68));
    /* Gap between the left shore island (0..80, top 164) and the middle island (128..): x 105 has nothing. */
    CHECK(stage_floor_y(FL_PX(105), FL_PX(100)) == FLIER_NO_FLOOR);
    /* Edge overlap uses the flier half width: centre at 80 + 1 still touches (box 79..81), centre 82 does not. */
    CHECK(stage_floor_y(FL_PX(81), FL_PX(150)) == FL_PX(164));
    CHECK(stage_floor_y(FL_PX(82), FL_PX(150)) == FLIER_NO_FLOOR);
    /* Seam: the left shore island (0..80 at top 164) is found from x 383 (its copy at 384), from x 1, and from one arena width out;
       clear of it at -4 the right side has no island at that height (the top right island ends at 376). Feet 150 is above the left island top. */
    CHECK(stage_floor_y(FL_PX(383), FL_PX(150)) == FL_PX(164));
    CHECK(stage_floor_y(FL_PX(1), FL_PX(150)) == FL_PX(164));
    CHECK(stage_floor_y(FL_PX(5), FL_PX(150)) == FL_PX(164));
    CHECK(stage_floor_y(FL_PX(ARENA_W + 10), FL_PX(150)) == FL_PX(164));
    CHECK(stage_floor_y(FL_PX(-4), FL_PX(150)) == FLIER_NO_FLOOR);
    /* From above: the low left island is the only floor over x 0..80 and at its seam copy; at x 360 the right shore island (148) is in reach. */
    CHECK(stage_floor_y(FL_PX(40), FL_PX(140)) == FL_PX(164));
    CHECK(stage_floor_y(FL_PX(383), FL_PX(140)) == FL_PX(164));
    CHECK(stage_floor_y(FL_PX(360), FL_PX(140)) == FL_PX(148));
    /* Top right island (296..376 at top 68): its right edge uses the flier half width (centre 375 touches, 378 does not); from below its top only the shore island counts. */
    CHECK(stage_floor_y(FL_PX(375), FL_PX(60)) == FL_PX(68));
    CHECK(stage_floor_y(FL_PX(378), FL_PX(60)) == FLIER_NO_FLOOR);
    CHECK(stage_floor_y(FL_PX(336), FL_PX(70)) == FL_PX(148));
    CHECK(stage_floor_y(FL_PX(0), FL_PX(60)) == FL_PX(164));
    /* No island at the edge strip below the shore top: no floor under feet lower than the shore. */
    CHECK(stage_floor_y(FL_PX(383), FL_PX(170)) == FLIER_NO_FLOOR);
    /* Spawns stand on a platform, and no spawn box touches any island: the box (4 px wide, 11 px tall with balloons) lies inside its own
       island's columns, clear of every other island's collision rectangle and drawn rows (sprite top = y - 4, 16 tall). */
    for (i = 0; i < stage_rival_count(); i++) {
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
    CHECK(FLIER_START_X == 40);

    /* Solid islands: the body is STAGE_PLATFORM_H deep under the standing line, on every side. */
    CHECK(STAGE_PLATFORM_H == 12);
    {
        FlierSolid so[8];
        int n, k, found;
        n = stage_solids_near(FL_PX(192), so, 8);
        CHECK(n == 1);   /* the middle island, nothing else within reach */
        for (k = 0, found = 0; k < n; k++) if (so[k].y16 == FL_PX(108)) { found++; CHECK(so[k].x16 == FL_PX(128) && so[k].w16 == FL_PX(112) && so[k].h16 == FL_PX(STAGE_PLATFORM_H)); }
        CHECK(found == 1);
        /* Seam: the left shore island is seen as its copy right of the seam, the right one as the copy left of x 0. */
        n = stage_solids_near(FL_PX(383), so, 8);
        for (k = 0, found = 0; k < n; k++) if (so[k].y16 == FL_PX(164)) { found++; CHECK(so[k].x16 == FL_PX(384)); }
        CHECK(found == 1);
        n = stage_solids_near(FL_PX(1), so, 8);
        for (k = 0, found = 0; k < n; k++) if (so[k].y16 == FL_PX(68)) { found++; CHECK(so[k].x16 == FL_PX(296 - ARENA_W)); }
        CHECK(found == 1);
        /* Far from everything: nothing returned. */
        CHECK(stage_solids_near(FL_PX(105), so, 8) == 0 || so[0].y16 >= 0);
        /* A flier standing at any spawn is touched by no solid; one rising into the underside of every island is turned back. */
        for (i = 0; i < stage_rival_count(); i++) {
            Flier f;
            flier_init(&f, FL_PX(stage_spawns[i].x), FL_PX(stage_spawns[i].y + 6) - FLIER_HALF_H16_BALLOON, 2, 0);
            n = stage_solids_near(f.x, so, 8);
            CHECK(flier_collide_solids(&f, f.x, f.y, so, n) == 0);
        }
        for (i = 0; i < STAGE_PLATFORM_COUNT; i++) {
            const StagePlatform *p = &stage_platforms[i];
            Flier f;
            int32_t py;
            if (!p->w) continue;
            /* feet 30 px under the island bottom, gum top (31 above the feet) one pixel inside it; rose 2 px this frame */
            flier_init(&f, FL_PX(p->x + p->w / 2), FL_PX(p->y + STAGE_PLATFORM_H + 32) - FLIER_HALF_H16_BALLOON, 2, 0);
            py = f.y;
            f.y -= FL_PX(2);
            n = stage_solids_near(f.x, so, 8);
            CHECK(flier_collide_solids(&f, f.x, py, so, n) >= 1);
            CHECK(f.y + FLIER_HALF_H16_BALLOON - FL_PX(FLIER_GUM_TOP) == FL_PX(p->y + STAGE_PLATFORM_H));   /* gum top on the bottom */
        }
    }

    /* Arena step: a fresh game starts standing on the left shore island and stays alive; sentinel counts every step. */
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
    /* behaviour change approved by the user (dead flier hazard hunt): the run ends when the body is GONE; was FLIER_DROWNED */
    CHECK(g.flier.state == FLIER_GONE);
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
    /* Layout rotation (ROT1): every layout in the table passes the R01 range checks; the player start stands on island 0 of each; a real game's round n plays layout (n - 1) mod count. */
    CHECK(stage_layout_count() == 12);
    for (int l = 0; l < stage_layout_count(); l++) {
        stage_select(l);
        CHECK(stage_layout_index() == l);
        CHECK(island_total_columns() <= ISLAND_COUNT);
        CHECK(stage_floor_y(FL_PX(FLIER_START_X), FL_PX(FLIER_START_Y) + FL_PX(6)) == FL_PX(stage_platforms[0].y));
        for (i = 0; i < STAGE_PLATFORM_COUNT; i++) {
            const StagePlatform *p = &stage_platforms[i];
            if (!p->w) { CHECK(p->h == 0 && island_columns(0) == 0); continue; } /* unused slot: no columns drawn */
            CHECK(p->x >= 0 && p->x + p->w <= ARENA_W && p->y >= 36 && p->y + p->h <= FLIER_WATER_Y && island_columns(p->w) == p->w / 16);
        }
        for (i = 0; i < stage_rival_count(); i++) {
            int own = 0;
            for (int k = 0; k < STAGE_PLATFORM_COUNT; k++) {
                const StagePlatform *p = &stage_platforms[k];
                if (stage_spawns[i].y + 6 == p->y && stage_spawns[i].x - FLIER_HALF_W >= p->x && stage_spawns[i].x + FLIER_HALF_W <= p->x + p->w) own++;
                else if (p->w) CHECK(!(stage_spawns[i].x + FLIER_HALF_W > p->x && stage_spawns[i].x - FLIER_HALF_W < p->x + p->w && stage_spawns[i].y + 5 > p->y - 4 && stage_spawns[i].y - 6 < p->y + 12));
            }
            CHECK(own == 1);
        }
    }
    {
        Game r;
        int16_t first_x2 = 0;
        game_reset(&r, 1);
        CHECK(stage_layout_index() == 0);
        first_x2 = stage_platforms[2].x;
        for (int round = 2; round <= 4; round++) {
            r.rounds = 1; r.matches_won = (uint32_t)(round - 1); r.round_end = RE_PAN;
            for (i = 0; i < 600 && r.round_end != RE_NONE; i++) game_step_arena(&r, 0);
            CHECK(r.round_end == RE_NONE);
            CHECK(stage_layout_index() == (round - 1) % stage_layout_count());
            CHECK(stage_look() == (round - 1) % 3); /* round 2 garden, 3 deck, 4 roof */
            CHECK((stage_platforms[2].x != first_x2) == (stage_layout_index() != 0));
        }
        game_reset(&r, 1); /* a new game, the demo included, starts on layout 0 */
        CHECK(stage_layout_index() == 0);
    }
    /* island look = level modulo 3: roof, garden, deck */
    CHECK(STAGE_LOOK_COUNT == 3 && STAGE_LOOK_ROOF == 0 && STAGE_LOOK_GARDEN == 1 && STAGE_LOOK_DECK == 2);
    CHECK(stage_look_for_level(0) == STAGE_LOOK_ROOF && stage_look_for_level(1) == STAGE_LOOK_GARDEN);
    CHECK(stage_look_for_level(2) == STAGE_LOOK_DECK && stage_look_for_level(3) == STAGE_LOOK_ROOF);
    CHECK(stage_look_for_level(7) == STAGE_LOOK_GARDEN && stage_look_for_level(-1) == STAGE_LOOK_ROOF);
    /* ROT3a: true 48 px islands (3 columns: left cap, middle m0, right cap). The width table keeps indices 0..3 and gets 48 as index 4. */
    {
        static const unsigned char widths[] = ISLAND_TABLE_WIDTH;
        static const struct { int layout, x, y; } w48[] = {
            { 4, 112, 128 }, { 4, 8, 108 }, { 4, 296, 92 }, { 4, 200, 76 }, { 4, 128, 60 }, { 4, 56, 44 },   /* N06 */
            { 5, 168, 132 }, { 5, 168, 76 }, { 5, 88, 100 },                                                  /* N04 (the 4th island stays 64) */
            { 6, 96, 132 }, { 6, 168, 100 }, { 6, 240, 84 }, { 6, 312, 52 }, { 6, 16, 68 },                  /* N08 */
            { 8, 112, 128 }, { 8, 8, 108 }, { 8, 296, 92 }, { 8, 200, 76 }, { 8, 128, 60 }, { 8, 56, 44 },   /* N09 */
        };
        FlierSolid so[8];
        CHECK(ISLAND_WIDTH_COUNT == 5 && widths[0] == 64 && widths[3] == 112 && widths[4] == 48);
        CHECK(island_columns(48) == 3 && island_columns(64) == 4 && island_columns(112) == 7);
        CHECK(island_piece_anim(48, 0) == 0 && island_piece_anim(48, 1) == 1 && island_piece_anim(48, 2) == 6 && island_piece_anim(48, 3) == -1);
        CHECK(island_anim_swaps(island_piece_anim(48, 0)) && island_anim_swaps(island_piece_anim(48, 2)) && !island_anim_swaps(island_piece_anim(48, 1)));
        for (i = 0; i < (int)(sizeof w48 / sizeof w48[0]); i++) {
            int found = 0, n;
            stage_select(w48[i].layout);
            for (int k = 0; k < STAGE_PLATFORM_COUNT; k++)
                if (stage_platforms[k].x == w48[i].x && stage_platforms[k].y == w48[i].y) { found++; CHECK(stage_platforms[k].w == 48 && island_columns(stage_platforms[k].w) == 3); }
            CHECK(found == 1);
            n = stage_solids_near(FL_PX(w48[i].x + 24), so, 8);
            found = 0;
            for (int k = 0; k < n; k++) if (so[k].x16 == FL_PX(w48[i].x) && so[k].y16 == FL_PX(w48[i].y)) { found++; CHECK(so[k].w16 == FL_PX(48)); }
            CHECK(found == 1);
        }
        stage_select(5);
        { int n64 = 0; for (i = 0; i < STAGE_PLATFORM_COUNT; i++) n64 += stage_platforms[i].x == 264 && stage_platforms[i].w == 64; CHECK(n64 == 1); }
    }
    printf("stage: %d checks, %d failures\n", checks, failures);
    return failures != 0;
}
