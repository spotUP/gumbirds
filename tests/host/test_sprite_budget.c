/* Host test for src/core/sprite_budget.[ch]: slot ranges do not overlap, draw order, fit in 381, <= 90 per line. */
#include <stdio.h>
#include "../../src/core/sprite_budget.h"
#include "../../src/sprite_slots.h"
#include "../../src/core/island_layout.h"
#include "../../src/core/stage.h"
#include "gen/logo_sprites.h"
#include "../../src/core/arcade.h"
#include "../../src/core/arc_view.h"
#include "../../src/core/obj_pool.h"
#include "../../src/core/gg_popdrop.h"
#include "gen/popdrop_sprites.h"
#include "gen/popdropsky_sprites.h"
#include "gen/popdropsky_tables.h"
#include "gen/popdrop_sprites.c"      /* frame widths of the Pop Drop slot map (data only) */
#include "gen/popdropsky_sprites.c"

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

static void test_slots(void) {
    for (int i = 0; i < SPRITE_BUDGET_COUNT; i++) {
        const SpriteBudgetEntry *a = &SPRITE_BUDGET[i];
        CHECK(a->first + a->count <= 381);
        CHECK(a->y0 < a->y1 && a->y1 <= SB_LINES);
        CHECK(a->per_line <= a->count);
        CHECK(a->first > SPRITE_RESERVED); /* no range includes sprite 0, which must never be visible (src/sprite_slots.h) */
        for (int j = i + 1; j < SPRITE_BUDGET_COUNT; j++) {
            const SpriteBudgetEntry *b = &SPRITE_BUDGET[j];
            CHECK(a->first + a->count <= b->first || b->first + b->count <= a->first);
        }
    }
    CHECK(BG_SKY_SPRITE == SPRITE_RESERVED + 1);
    CHECK(BG_SPRITE_END == 111 && BG_SPRITE_TOTAL == 110);
    /* draw order: planes behind the pool, hero above pool, hazard and foreground above hero */
    CHECK(BG_SPRITE_END <= GUM_SPRITE && GUM_SPRITE + GUM_COUNT <= ISLAND_SPRITE && GUM_COUNT >= 2);   /* the player gum bubble sits between the planes and the islands */
    CHECK(BG_SPRITE_END <= ISLAND_SPRITE);
    CHECK(GUM_SPRITE + GUM_COUNT <= SPLASH_SPRITE && SPLASH_SPRITE + SPLASH_COUNT <= ISLAND_SPRITE && SPLASH_COUNT == 3);   /* the splash draws behind the islands, pool and hazard strip */
    CHECK(SPLASH_SPRITE + SPLASH_COUNT <= HAZARD_SPRITE);
    CHECK(ISLAND_SPRITE + ISLAND_COUNT <= POOL_SPRITE_BASE);
    CHECK(island_total_columns() == 18 && 18 <= ISLAND_COUNT);   /* stage 1 uses 22 of the range; the Gum Trip islands need the rest (user-approved, was ==) */
    CHECK(POOL_SPRITE_BASE + POOL_SPRITE_COUNT <= HERO_SPRITE);
    CHECK(HERO_SPRITE + HERO_SPRITE_COUNT <= HAZARD_SPRITE);
    CHECK(HAZARD_SPRITE + HAZARD_COUNT <= FG_RAIN_SPRITE);
    CHECK(FG_SPRAY_SPRITE + FG_SPRAY_COUNT <= TRIP_STRIP_SPRITE);   /* Gum Trip kill strips come last (step V2) */
    CHECK(TRIP_STRIP_SPRITE + TRIP_STRIP_COUNT == TRIP_PICKUP_SPRITE);
    CHECK(TRIP_PICKUP_SPRITE + TRIP_PICKUP_COUNT == SPRITE_SLOT_END);
    /* DF3: a liquid body falls behind the hazard art (pool and hero slots are below the strip); a spike body draws from the
     * dead body slots, the last 4 hardware sprites, above every other range including the strip. */
    CHECK(POOL_SPRITE_BASE + POOL_SPRITE_COUNT <= HAZARD_SPRITE);
    CHECK(HERO_SPRITE + HERO_SPRITE_COUNT <= HAZARD_SPRITE);
    CHECK(DEAD_BODY_SPRITE == SPRITE_SLOT_END);
    CHECK(DEAD_BODY_SPRITE > HAZARD_SPRITE + HAZARD_COUNT - 1);
    CHECK(DEAD_BODY_SPRITE + DEAD_BODY_COUNT == 381);
    CHECK(DEAD_BODY_COUNT / DEAD_BODY_COLUMNS == 2);
}

/* The island row (plan I9): its count is the table's columns, its line range covers every island sprite, and the columns the
 * stage table really puts on each line (bands 4 lines above the platform top, 16 high) never exceed the row's per_line. */
static void test_islands(void) {
    const SpriteBudgetEntry *row = 0;
    for (int i = 0; i < SPRITE_BUDGET_COUNT; i++) if (SPRITE_BUDGET[i].first == ISLAND_SPRITE) row = &SPRITE_BUDGET[i];
    CHECK(row != 0);
    if (!row) return;
    int sum = 0;
    for (int i = 0; i < STAGE_PLATFORM_COUNT; i++) sum += stage_platforms[i].w / 16;
    CHECK(row->count == ISLAND_COUNT);
    CHECK(sum == 18);
    CHECK(18 <= ISLAND_COUNT);
    int worst = 0, wline = 0, lines_with_two = 0;
    for (int y = 0; y < SB_LINES; y++) {
        int cols = 0, islands = 0;
        for (int i = 0; i < STAGE_PLATFORM_COUNT; i++) {
            int top = stage_platforms[i].y - 4;
            if (stage_platforms[i].w && y >= top && y < top + 16) { cols += stage_platforms[i].w / 16; islands++; }
        }
        if (islands > 1) lines_with_two++;
        if (cols > worst) { worst = cols; wline = y; }
        CHECK(cols <= row->per_line);
        if (cols) CHECK(y >= row->y0 && y < row->y1);
    }
    CHECK(lines_with_two == 0);
    CHECK(worst <= row->per_line); /* arena gap change: the shorter islands peak at 6 columns, the 7 stays reserved */
    printf("islands: worst %d columns on one line (line %d), row per_line %d, lines %d..%d\n", worst, wline, row->per_line, row->y0, row->y1 - 1);
}

/* Every built mood is checked against the limit, with rain columns only in a mood that has rain. A mood that is not
 * built has no art to count: it is listed as pending, never passed. */
static void test_lines(void) {
    for (int m = 0; m < SPRITE_BUDGET_MOOD_COUNT; m++) {
        const SpriteBudgetMood *mood = &SPRITE_BUDGET_MOODS[m];
        if (!mood->built) {
            printf("PENDING mood %s: not built, sprite budget not checked\n", mood->name);
            continue;
        }
        for (int trip = 0; trip < 2; trip++) {
            int worst = 0, line0 = 0;
            for (int y = 0; y < SB_LINES; y++) {
                int n = sprite_budget_line(m, y, trip);
                if (n > worst) { worst = n; line0 = y; }
                CHECK(n <= SB_LIMIT);
            }
            printf("mood %s, %s: worst sprites per line %d at line %d (limit %d)\n", mood->name, trip ? "Gum Trip" : "arena", worst, line0, SB_LIMIT);
            CHECK(worst >= 1);
            /* the arena counts the stage platforms per line plus the gum row: the peak is 88 on lines 112..119 (86 plus the 2 Roost Rule marker sprites; was 90 on line 128,
             * flat 7 islands and no gum row), 79 on 120..127, 81 on 128..143. Moving a platform moves these pins on purpose.
             * 4 lower than before on every line: SB_GAMEPLAY_PER_LINE 18 -> 14 (budget-e, room for arcade stage elements). */
            if (!trip && !mood->rain) {
                CHECK(worst == 87);
                CHECK(line0 == 112);
                CHECK(sprite_budget_line(m, 119, 0) == 87);
                CHECK(sprite_budget_line(m, 120, 0) == 81);
                CHECK(sprite_budget_line(m, 128, 0) == 83);
                CHECK(sprite_budget_line(m, 143, 0) == 83);
            }
        }
    }
}

/* ROT2: every layout of the stage table against the line limit (islands per line come from the layout in RAM), in every built mood.
 * Layout 0 is pinned above; the others only have to fit. The worst layout and line are printed. */
static void test_layouts(void) {
    int wl = 0, wn = 0, wy = 0;
    for (int l = 0; l < stage_layout_count(); l++) {
        int worst = 0, line0 = 0, cols = 0;
        stage_select(l);
        for (int i = 0; i < STAGE_PLATFORM_COUNT; i++) cols += stage_platforms[i].w / 16;
        CHECK(cols <= ISLAND_COUNT);
        for (int m = 0; m < SPRITE_BUDGET_MOOD_COUNT; m++) {
            if (!SPRITE_BUDGET_MOODS[m].built) continue;
            for (int y = 0; y < SB_LINES; y++) {
                int n = sprite_budget_line(m, y, 0);
                if (n > worst) { worst = n; line0 = y; }
                CHECK(n <= SB_LIMIT);
            }
        }
        printf("layout %d: %d island columns, worst sprites per line %d at line %d (limit %d)\n", l, cols, worst, line0, SB_LIMIT);
        if (worst > wn) { wl = l; wn = worst; wy = line0; }
    }
    stage_select(0);
    printf("layouts: worst is layout %d with %d at line %d\n", wl, wn, wy);
}

/* The title screen: planes, the logo (worst frame) and the two title Sootlings; no gameplay, islands, hazard or spray there. */
static void test_title(void) {
    int worst = 0, line0 = 0;
    for (int m = 0; m < SPRITE_BUDGET_MOOD_COUNT; m++) {
        if (!SPRITE_BUDGET_MOODS[m].built) continue;
        for (int y = 0; y < SB_LINES; y++) {
            int n = sprite_budget_title_line(m, y);
            if (n > worst) { worst = n; line0 = y; }
            CHECK(n <= SB_LIMIT);
        }
    }
    printf("title (every built mood): worst sprites per line %d at line %d (limit %d), logo alone %d\n", worst, line0, SB_LIMIT, sprite_budget_logo_worst());
    CHECK(sprite_budget_logo_worst() == LOGO_WORST_LINE); /* the importer's own count, recomputed from the tables */
    CHECK(sprite_budget_logo_worst() <= LOGO_COUNT);
    CHECK(worst >= LOGO_WORST_LINE);
}

/* Arcade stage elements are drawn in sprite slots no budget row covers (ARC_ELEM_SPRITE, the unused rain and spray slots), so the
   test adds their columns to the arena's line sum: every arcade stage, every tick of a long run (vent phases, sparks, grabber), worst line. */
static void test_arcade_elements(void) {
    int worst = 0;
    /* Co-op: the P2 body and parachute are pool objects 30 and 31 and sit inside the gameplay reserve. */
    CHECK(POOL_SPRITE_BASE + POOL_MAX * POOL_COLS <= HERO_SPRITE);
    CHECK(sprite_budget_line(0, 100, 0) <= SB_LIMIT);
    CHECK(ARC_ELEM_SPRITE >= FG_RAIN_SPRITE && ARC_ELEM_SPRITE + ARC_ELEM_COUNT == TRIP_STRIP_SPRITE + 1); /* rain, spray and the first strip slot, idle in arcade stages */
    printf("arcade worst scanline per stage 1..12:");
    for (int st = 1; st <= 12; st++) {
        ArcElements a;
        ArcSprite s[ARC_VIEW_MAX];
        int sw = 0, peak = 0;
        stage_select(arc_stage_layout(st));
        arc_elements_init(&a, st - 1);
        for (int t = 0; t < 700; t++, arc_elements_step(&a)) {
            int n = arc_view_build(&a, (unsigned)t, s), cols = 0;
            for (int i = 0; i < n; i++) cols += ARC_VIEW_COLS[s[i].piece];
            CHECK(cols <= ARC_ELEM_COUNT); /* every block gets its columns, also the spark of the last vent */
            if (cols > peak) peak = cols;
            int killing = 0, sparks = 0;
            for (int i = 0; i < a.n; i++)
                if (a.el[i].kind == ARC_EL_VENT && a.el[i].timer >= ARC_VENT_LAUNCH && a.el[i].timer < ARC_VENT_LAUNCH + ARC_VENT_BURST_TICKS) killing++;
            for (int i = 0; i < n; i++) if (s[i].piece == ARCV_SPARK) sparks++;
            CHECK(sparks == killing); /* a plume that can kill always has its spark sprite (no invisible kill) */
            for (int y = 0; y < SB_LINES; y++) {
                int c = sprite_budget_line_arcade(0, y) + arc_view_line(s, n, y);
                if (c > sw) sw = c;
            }
        }
        printf(" %d", sw);
        CHECK(peak <= ARC_ELEM_COUNT); /* element columns of the stage fit the range (R10 needs exactly 15 of 15) */
        CHECK(st != 10 || peak == 15);
        CHECK(sw <= SB_LIMIT);
        if (sw > worst) worst = sw;
    }
    printf("\narcade worst scanline %d of %d\n", worst, SB_LIMIT);
    stage_select(0); /* the other tests expect the arena layout */
    CHECK(worst <= SB_LIMIT);
}

/* Pop Drop slot map. The slot numbers live in src/main.c (PD_*) and src/bg.c (pop_layout), not in a header, so they are mirrored here
 * (shortcut: a change there must be copied here; the MAME 2P check catches a drifted P2 slot). Ranges: sky 1..20, clouds 21..end,
 * trail gums on ISLAND_SPRITE (2 columns x PD_GUMS), then bird, platforms, shield, rag, P2 bird, shield, rag, puff, P2 puff from 323.
 * No two overlap, each fits its widest frame, all inside 1..380. */
#define T_PD_SPRITE 323
#define T_PD_PLAT_SLOT (T_PD_SPRITE + 2)
#define T_PD_SHIELD_SLOT (T_PD_PLAT_SLOT + PD_PLATS * 5)
#define T_PD_RAG_SLOT (T_PD_SHIELD_SLOT + 4)
#define T_PD_BIRD2_SLOT (T_PD_RAG_SLOT + 1)
#define T_PD_SHIELD2_SLOT (T_PD_BIRD2_SLOT + 2)
#define T_PD_RAG2_SLOT (T_PD_SHIELD2_SLOT + 4)
#define T_PD_PUFF_SLOT (T_PD_RAG2_SLOT + 1)
#define T_PD_PUFF2_SLOT (T_PD_PUFF_SLOT + 3)
#define T_PD_END (T_PD_PUFF2_SLOT + 3)
/* pool finish slots (src/main.c PD_BACK..): gags 2 x 5, fans + cards 2 x 3 x 3, flop 2 x 2, pool strips 20, ladder 1, splash 2 x 6 */
#define T_PD_GAG_SLOT POOL_SPRITE_BASE
#define T_PD_FAN_SLOT (T_PD_GAG_SLOT + 10)
#define T_PD_FLOP_SLOT (T_PD_FAN_SLOT + 18)
#define T_PD_POOLS_SLOT (T_PD_FLOP_SLOT + 4)
#define T_PD_LADDER_SLOT (T_PD_POOLS_SLOT + 20)
#define T_PD_SPL_SLOT (T_PD_LADDER_SLOT + 1)

static int anim_max_cols(int anim) {
    int m = 0;
    for (int f = 0; f < popdrop_anims[anim].frame_count; f++) {
        int w = popdrop_frames[popdrop_anims[anim].first_frame + f].tiles_w;
        if (w > m) m = w;
    }
    return m;
}

static void test_popdrop_slots(void) {
    /* cloud end: bg.c pop_layout (copies of a cloud until its layer period covers the 224 px screen plus 16) */
    static const unsigned period[3] = { 128, 256, 384 };
    static const unsigned char layer[POPDROPSKY_CLOUDS] = POPDROPSKY_TABLE_CL;
    int cloud_end = BG_SKY_SPRITE + BG_SKY_COUNT;
    for (int i = 0; i < POPDROPSKY_CLOUDS; i++) {
        unsigned copies = 1;
        while (copies * period[layer[i]] < 224 + 16) copies++;
        cloud_end += (int)copies * popdropsky_frames[1 + i].tiles_w;
    }
    struct { const char *name; int first, count; } r[] = {
        { "sky", BG_SKY_SPRITE, BG_SKY_COUNT },
        { "clouds", BG_SKY_SPRITE + BG_SKY_COUNT, cloud_end - (BG_SKY_SPRITE + BG_SKY_COUNT) },
        { "trail gums", ISLAND_SPRITE, PD_GUMS * 2 },
        { "bird", T_PD_SPRITE, 2 }, { "platforms", T_PD_PLAT_SLOT, PD_PLATS * 5 },
        { "shield", T_PD_SHIELD_SLOT, 4 }, { "rag", T_PD_RAG_SLOT, 1 },
        { "bird2", T_PD_BIRD2_SLOT, 2 }, { "shield2", T_PD_SHIELD2_SLOT, 4 }, { "rag2", T_PD_RAG2_SLOT, 1 },
        { "puff", T_PD_PUFF_SLOT, 3 }, { "puff2", T_PD_PUFF2_SLOT, 3 },
        { "gags", T_PD_GAG_SLOT, 10 }, { "fans", T_PD_FAN_SLOT, 18 }, { "flop", T_PD_FLOP_SLOT, 4 },
        { "pool strips", T_PD_POOLS_SLOT, 20 }, { "ladder", T_PD_LADDER_SLOT, 1 }, { "splash", T_PD_SPL_SLOT, 12 },
    };
    int n = (int)(sizeof r / sizeof r[0]);
    printf("pop drop slots: sky 1..20, clouds %d..%d, trail gums %d..%d, sprites %d..%d (Trip pickups from %d)\n",
           r[1].first, cloud_end - 1, ISLAND_SPRITE, ISLAND_SPRITE + PD_GUMS * 2 - 1, T_PD_SPRITE, T_PD_END - 1, TRIP_PICKUP_SPRITE);
    for (int i = 0; i < n; i++) {
        CHECK(r[i].first > SPRITE_RESERVED && r[i].first + r[i].count <= 381);
        for (int j = i + 1; j < n; j++) {
            int ok = r[i].first + r[i].count <= r[j].first || r[j].first + r[j].count <= r[i].first;
            CHECK(ok);
            if (!ok) printf("OVERLAP %s and %s\n", r[i].name, r[j].name);
        }
    }
    CHECK(cloud_end <= BG_SPRITE_END && cloud_end <= GUM_SPRITE);
    CHECK(ISLAND_SPRITE + PD_GUMS * 2 <= POOL_SPRITE_BASE);
    CHECK(T_PD_SPRITE >= FG_SPRAY_SPRITE + FG_SPRAY_COUNT && T_PD_END <= TRIP_PICKUP_SPRITE);
    /* each piece fits its allotment */
    /* pop_show_pieces draws frames kind*2 + 0/1, kind 0..2 (rng_range 3): the first 6; a wider spare frame is never drawn */
    for (int k = 0; k < 6; k++) CHECK(popdrop_frames[popdrop_anims[POPDROP_ANIM_PLAT].first_frame + k].tiles_w == 1);
    CHECK(anim_max_cols(POPDROP_ANIM_SHIELD) <= 4 && anim_max_cols(POPDROP_ANIM_POP) <= 4);
    CHECK(anim_max_cols(POPDROP_ANIM_RAG) <= 1 && anim_max_cols(POPDROP_ANIM_PUFF) <= 3);
    /* pool finish anims (batch 2; the pool surface, water and edge frames are 2 tile columns drawn as 2 alternating strips) are not 2-column birds; each fits the slots its draw layer gives it */
    struct { int anim; int cols; const char *name; } fit[] = {
        { POPDROP_ANIM_TUBBIRD, 2, "gag bird" }, { POPDROP_ANIM_TUB, 3, "gag tub" }, { POPDROP_ANIM_CHAIR, 5, "gag chair" },
        { POPDROP_ANIM_SNAIL, 5, "gag snail" }, { POPDROP_ANIM_FAN, 2, "fan" }, { POPDROP_ANIM_CARD, 1, "card" },
        { POPDROP_ANIM_FLOP, 2, "flop" }, { POPDROP_ANIM_SURF, 2, "pool surface" }, { POPDROP_ANIM_WATER, 2, "pool water" },
        { POPDROP_ANIM_EDGE, 2, "pool edge" }, { POPDROP_ANIM_LADDER, 1, "ladder" },
        { POPDROP_ANIM_SPLASH_S, 6, "splash small" }, { POPDROP_ANIM_SPLASH_M, 6, "splash medium" }, { POPDROP_ANIM_SPLASH_L, 6, "splash large" },
    };
    for (int i = 0; i < (int)(sizeof fit / sizeof fit[0]); i++) {
        int w = anim_max_cols(fit[i].anim);
        CHECK(w <= fit[i].cols);
        if (w > fit[i].cols) printf("%s anim %d is %d columns wide, slot gives %d\n", fit[i].name, fit[i].anim, w, fit[i].cols);
    }
    for (int a = 0; a < POPDROP_ANIM_COUNT; a++) {
        int other = a == POPDROP_ANIM_RAG || a == POPDROP_ANIM_FX || a == POPDROP_ANIM_PLAT || a == POPDROP_ANIM_SHIELD || a == POPDROP_ANIM_POP || a == POPDROP_ANIM_PUFF;
        for (int i = 0; i < (int)(sizeof fit / sizeof fit[0]); i++) if (fit[i].anim == a) other = 1;
        if (!other) { CHECK(anim_max_cols(a) <= 2); if (anim_max_cols(a) > 2) printf("bird anim %d is %d columns wide, slot gives 2\n", a, anim_max_cols(a)); }
    }
}

int main(void) {
    test_arcade_elements(); test_slots(); test_popdrop_slots();
    test_islands();
    test_lines();
    test_layouts();
    test_title();
    printf("%d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
