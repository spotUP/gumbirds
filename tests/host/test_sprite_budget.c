/* Host test for src/core/sprite_budget.[ch]: slot ranges do not overlap, draw order, fit in 381, <= 90 per line. */
#include <stdio.h>
#include "../../src/core/sprite_budget.h"
#include "../../src/sprite_slots.h"
#include "../../src/core/island_layout.h"
#include "../../src/core/stage.h"

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
    CHECK(BG_SPRITE_END <= ISLAND_SPRITE);
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
            if (y >= top && y < top + 16) { cols += stage_platforms[i].w / 16; islands++; }
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
        int worst = 0, line0 = 0;
        for (int y = 0; y < SB_LINES; y++) {
            int n = sprite_budget_line(y, mood->rain);
            if (n > worst) { worst = n; line0 = y; }
            CHECK(n <= SB_LIMIT);
        }
        printf("mood %s: worst sprites per line %d at line %d (limit %d)\n", mood->name, worst, line0, SB_LIMIT);
        CHECK(worst >= 1);
    }
}

int main(void) {
    test_slots();
    test_islands();
    test_lines();
    printf("%d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
