/* Host test for src/core/sprite_budget.[ch]: slot ranges do not overlap, draw order, fit in 381, <= 90 per line. */
#include <stdio.h>
#include "../../src/core/sprite_budget.h"
#include "../../src/sprite_slots.h"
#include "../../src/core/island_layout.h"
#include "../../src/core/stage.h"
#include "gen/logo_sprites.h"
#include "../../src/core/arcade.h"
#include "../../src/core/arc_view.h"

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
    CHECK(island_total_columns() == 22 && 22 <= ISLAND_COUNT);   /* stage 1 uses 22 of the range; the Gum Trip islands need the rest (user-approved, was ==) */
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
    CHECK(sum == 22);
    CHECK(22 <= ISLAND_COUNT);
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
    CHECK(worst == row->per_line);
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
                int n = sprite_budget_line(y, mood->rain, trip);
                if (n > worst) { worst = n; line0 = y; }
                CHECK(n <= SB_LIMIT);
            }
            printf("mood %s, %s: worst sprites per line %d at line %d (limit %d)\n", mood->name, trip ? "Gum Trip" : "arena", worst, line0, SB_LIMIT);
            CHECK(worst >= 1);
            /* the arena counts the stage platforms per line plus the gum row: the peak is 86 on lines 112..119 (was 90 on line 128,
             * flat 7 islands and no gum row), 79 on 120..127, 81 on 128..143. Moving a platform moves these pins on purpose.
             * 4 lower than before on every line: SB_GAMEPLAY_PER_LINE 18 -> 14 (budget-e, room for arcade stage elements). */
            if (!trip && !mood->rain) {
                CHECK(worst == 86);
                CHECK(line0 == 112);
                CHECK(sprite_budget_line(119, mood->rain, 0) == 86);
                CHECK(sprite_budget_line(120, mood->rain, 0) == 79);
                CHECK(sprite_budget_line(128, mood->rain, 0) == 81);
                CHECK(sprite_budget_line(143, mood->rain, 0) == 81);
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
                int n = sprite_budget_line(y, SPRITE_BUDGET_MOODS[m].rain, 0);
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
    for (int y = 0; y < SB_LINES; y++) {
        int n = sprite_budget_title_line(y);
        if (n > worst) { worst = n; line0 = y; }
        CHECK(n <= SB_LIMIT);
    }
    printf("title: worst sprites per line %d at line %d (limit %d), logo alone %d\n", worst, line0, SB_LIMIT, sprite_budget_logo_worst());
    CHECK(sprite_budget_logo_worst() == LOGO_WORST_LINE); /* the importer's own count, recomputed from the tables */
    CHECK(sprite_budget_logo_worst() <= LOGO_COUNT);
    CHECK(worst >= LOGO_WORST_LINE);
}

/* Arcade stage elements are drawn in sprite slots no budget row covers (ARC_ELEM_SPRITE, the unused rain and spray slots), so the
   test adds their columns to the arena's line sum: every arcade stage, every tick of a long run (vent phases, sparks, grabber), worst line. */
static void test_arcade_elements(void) {
    int worst = 0;
    CHECK(ARC_ELEM_SPRITE >= FG_RAIN_SPRITE && ARC_ELEM_SPRITE + ARC_ELEM_COUNT <= FG_SPRAY_SPRITE + FG_SPRAY_COUNT);
    printf("arcade worst scanline per stage 1..12:");
    for (int st = 1; st <= 12; st++) {
        ArcElements a;
        ArcSprite s[ARC_VIEW_MAX];
        int sw = 0;
        stage_select(arc_stage_layout(st));
        arc_elements_init(&a, st - 1);
        for (int t = 0; t < 700; t++, arc_elements_step(&a)) {
            int n = arc_view_build(&a, (unsigned)t, s);
            for (int y = 0; y < SB_LINES; y++) {
                int c = sprite_budget_line(y, 0, 0) + arc_view_line(s, n, y);
                if (c > sw) sw = c;
            }
        }
        printf(" %d", sw);
        CHECK(sw <= SB_LIMIT);
        if (sw > worst) worst = sw;
    }
    printf("\narcade worst scanline %d of %d\n", worst, SB_LIMIT);
    stage_select(0); /* the other tests expect the arena layout */
    CHECK(worst <= SB_LIMIT);
}

int main(void) {
    test_arcade_elements(); test_slots();
    test_islands();
    test_lines();
    test_layouts();
    test_title();
    printf("%d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
