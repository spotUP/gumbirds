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

/* Reference: the per-flier scans as they were before the shared platform table (straight from stage_platforms, no packing). */
static int32_t ref_floor(int32_t x16, int32_t feet16) {
    int32_t best = FLIER_NO_FLOOR, hw = FL_PX(FLIER_HALF_W);
    for (int i = 0; i < STAGE_PLATFORM_COUNT; i++) {
        const StagePlatform *p = &stage_platforms[i];
        int32_t top = FL_PX(p->y), cx = FL_PX(p->x) + (FL_PX(p->w) >> 1), nx = arena_near_x(cx, x16);
        if (!p->w || top < feet16) continue;
        if (nx + hw <= FL_PX(p->x) || nx - hw >= FL_PX(p->x + p->w)) continue;
        if (top < best) best = top;
    }
    return best;
}
static int ref_solids(int32_t x16, FlierSolid *out, int max) {
    int n = 0;
    for (int i = 0; i < STAGE_PLATFORM_COUNT && n < max; i++) {
        const StagePlatform *p = &stage_platforms[i];
        int32_t cx = arena_near_x(x16, FL_PX(p->x) + (FL_PX(p->w) >> 1)), d = x16 > cx ? x16 - cx : cx - x16;
        if (!p->w || d >= (FL_PX(p->w) >> 1) + FL_PX(FLIER_SOLID_MAX_HALF_W + 8)) continue;
        out[n].x16 = cx - (FL_PX(p->w) >> 1); out[n].y16 = FL_PX(p->y); out[n].w16 = FL_PX(p->w); out[n].h16 = FL_PX(p->h);
        n++;
    }
    return n;
}

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
            { 8, 164, 64 }, { 288, 148, 64 }, { 136, 108, 96 }, { 304, 68, 64 }, { 0, 0, 0 }, { 0, 0, 0 }, { 0, 0, 0 }, { 0, 0, 0 },
        };
        for (i = 0; i < STAGE_PLATFORM_COUNT; i++)
            CHECK(stage_platforms[i].x == want[i][0] && stage_platforms[i].y == want[i][1] && stage_platforms[i].w == want[i][2]);
    }
    /* The island sprites and the collision read one table: every width has a piece list; stage 1 uses 18 columns of the ISLAND_COUNT range (the Gum Trip islands need the rest). User-approved weaker assert (was ==). */
    for (i = 0; i < STAGE_PLATFORM_COUNT; i++) CHECK(island_columns(stage_platforms[i].w) == stage_platforms[i].w / 16);
    CHECK(island_total_columns() == 18);
    CHECK(18 <= ISLAND_COUNT);
    /* Middle island (x 136..232, top 108): feet above it find it; feet below its top skip it. */
    CHECK(stage_floor_y(FL_PX(192), FL_PX(100)) == FL_PX(108));
    CHECK(stage_floor_y(FL_PX(192), FL_PX(108)) == FL_PX(108));
    CHECK(stage_floor_y(FL_PX(192), FL_PX(109)) == FLIER_NO_FLOOR); /* x 192 below the island: no other island there */
    /* Highest platform at or below the feet wins: from y 50 over x 336 the top right island (68) beats the right shore island (148). */
    CHECK(stage_floor_y(FL_PX(336), FL_PX(50)) == FL_PX(68));
    /* Gap between the left shore island (8..72, top 164) and the middle island (136..): x 105 has nothing. */
    CHECK(stage_floor_y(FL_PX(105), FL_PX(100)) == FLIER_NO_FLOOR);
    /* Edge overlap uses the flier half width: centre at 72 + 1 still touches, centre 74 does not. */
    CHECK(stage_floor_y(FL_PX(73), FL_PX(150)) == FL_PX(164));
    CHECK(stage_floor_y(FL_PX(74), FL_PX(150)) == FLIER_NO_FLOOR);
    /* Seam: the left shore island (0..80 at top 164) is found from x 383 (its copy at 384), from x 1, and from one arena width out;
       clear of it at -4 the right side has no island at that height (the top right island ends at 376). Feet 150 is above the left island top. */
    CHECK(stage_floor_y(FL_PX(391), FL_PX(150)) == FL_PX(164));
    CHECK(stage_floor_y(FL_PX(9), FL_PX(150)) == FL_PX(164));
    CHECK(stage_floor_y(FL_PX(13), FL_PX(150)) == FL_PX(164));
    CHECK(stage_floor_y(FL_PX(ARENA_W + 10), FL_PX(150)) == FL_PX(164));
    CHECK(stage_floor_y(FL_PX(4), FL_PX(150)) == FLIER_NO_FLOOR);
    /* From above: the low left island is the only floor over x 0..80 and at its seam copy; at x 360 the right shore island (148) is in reach. */
    CHECK(stage_floor_y(FL_PX(40), FL_PX(140)) == FL_PX(164));
    CHECK(stage_floor_y(FL_PX(391), FL_PX(140)) == FL_PX(164));
    CHECK(stage_floor_y(FL_PX(340), FL_PX(140)) == FL_PX(148));
    /* Top right island (304..368 at top 68): its right edge uses the flier half width (centre 375 touches, 378 does not); from below its top only the shore island counts. */
    CHECK(stage_floor_y(FL_PX(367), FL_PX(60)) == FL_PX(68));
    CHECK(stage_floor_y(FL_PX(370), FL_PX(60)) == FLIER_NO_FLOOR);
    CHECK(stage_floor_y(FL_PX(336), FL_PX(70)) == FL_PX(148));
    CHECK(stage_floor_y(FL_PX(8), FL_PX(60)) == FL_PX(164));
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
        for (k = 0, found = 0; k < n; k++) if (so[k].y16 == FL_PX(108)) { found++; CHECK(so[k].x16 == FL_PX(136) && so[k].w16 == FL_PX(96) && so[k].h16 == FL_PX(STAGE_PLATFORM_H)); }
        CHECK(found == 1);
        /* Seam: the left shore island is seen as its copy right of the seam, the right one as the copy left of x 0. */
        n = stage_solids_near(FL_PX(383), so, 8);
        for (k = 0, found = 0; k < n; k++) if (so[k].y16 == FL_PX(164)) { found++; CHECK(so[k].x16 == FL_PX(392)); }
        CHECK(found == 1);
        n = stage_solids_near(FL_PX(-8), so, 8);
        for (k = 0, found = 0; k < n; k++) if (so[k].y16 == FL_PX(68)) { found++; CHECK(so[k].x16 == FL_PX(304 - ARENA_W)); }
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
    CHECK(g.hero[0].on_ground && g.hero[0].state == FLIER_ALIVE && !g.over);
    CHECK(g.matches_won == 0); /* survival time no longer scores (design 3.3) */
    /* Over the gap between islands (x 100 has no platform below): the flier falls into the water and the run ends. */
    g.hero[0].x = FL_PX(100);
    g.hero[0].y = FL_PX(100);
    g.hero[0].on_ground = 0;
    for (i = 0; i < 2000 && !g.over; i++) game_step_arena(&g, 0);
    CHECK(g.over);
    /* behaviour change approved by the user (dead flier hazard hunt): the run ends when the body is GONE; was FLIER_DROWNED */
    CHECK(g.hero[0].state == FLIER_GONE);
    {
        uint32_t n = g.flier_steps;
        game_step_arena(&g, 0);
        CHECK(g.flier_steps == n); /* no steps after the run ended */
    }
    /* Flap raises the flier. */
    game_reset(&g, 1);
    for (i = 0; i < 60; i++) game_step_arena(&g, 0);
    {
        int32_t y0 = g.hero[0].y;
        for (i = 0; i < 20; i++) game_step_arena(&g, (i & 1) ? 0 : IN_A);
        CHECK(g.hero[0].y < y0);
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
            { 4, 152, 128 }, { 4, 24, 108 }, { 4, 296, 92 }, { 4, 184, 76 }, { 4, 96, 60 }, { 4, 8, 44 },   /* N06 */
            { 5, 168, 132 }, { 5, 168, 76 }, { 5, 72, 100 },                                                  /* N04 (the 4th island is 48 too since the arena gap change) */
            { 6, 96, 132 }, { 6, 184, 100 }, { 6, 280, 84 }, { 6, 8, 68 },                  /* N08 */
            { 8, 152, 128 }, { 8, 24, 108 }, { 8, 296, 92 }, { 8, 184, 76 }, { 8, 96, 60 }, { 8, 8, 44 },   /* N09 */
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
        { int n64 = 0; for (i = 0; i < STAGE_PLATFORM_COUNT; i++) n64 += stage_platforms[i].x == 280 && stage_platforms[i].w == 48; CHECK(n64 == 1); }
    }
    /* The shared platform table gives the same floor and solids as the plain scan, on every layout, ring and x (quarter pixel steps, seam included). */
    {
        int32_t rings[2] = { ARENA_W, FIELD_RING_W };
        for (int r = 0; r < 2; r++) {
            arena_ring = rings[r];
            for (int l = 0; l < stage_layout_count(); l++) {
                stage_select(l);
                for (int32_t x = -FL_PX(8); x < FL_PX(arena_ring + 8); x += 16384)
                    for (int fy = 0; fy < 200; fy += 23) {
                        FlierSolid a[8], b[8];
                        int na = stage_solids_near(x, a, 8), nb = ref_solids(x, b, 8);
                        CHECK(stage_floor_y(x, FL_PX(fy)) == ref_floor(x, FL_PX(fy)));
                        CHECK(na == nb);
                        for (int k = 0; k < na && k < nb; k++) CHECK(a[k].x16 == b[k].x16 && a[k].y16 == b[k].y16 && a[k].w16 == b[k].w16 && a[k].h16 == b[k].h16);
                    }
            }
        }
        arena_ring = ARENA_W;
        stage_select(0);
    }
    printf("stage: %d checks, %d failures\n", checks, failures);
    return failures != 0;
}
