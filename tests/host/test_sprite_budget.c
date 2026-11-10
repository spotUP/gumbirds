/* Host test for src/core/sprite_budget.[ch]: slot ranges do not overlap, draw order, fit in 381, <= 90 per line. */
#include <stdio.h>
#include "../../src/core/sprite_budget.h"
#include "../../src/sprite_slots.h"

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

static void test_slots(void) {
    for (int i = 0; i < SPRITE_BUDGET_COUNT; i++) {
        const SpriteBudgetEntry *a = &SPRITE_BUDGET[i];
        CHECK(a->first + a->count <= 381);
        CHECK(a->y0 < a->y1 && a->y1 <= SB_LINES);
        CHECK(a->per_line <= a->count);
        for (int j = i + 1; j < SPRITE_BUDGET_COUNT; j++) {
            const SpriteBudgetEntry *b = &SPRITE_BUDGET[j];
            CHECK(a->first + a->count <= b->first || b->first + b->count <= a->first);
        }
    }
    /* draw order: planes behind the pool, hero above pool, hazard and foreground above hero */
    CHECK(BG_SPRITE_END <= POOL_SPRITE_BASE);
    CHECK(POOL_SPRITE_BASE + POOL_SPRITE_COUNT <= HERO_SPRITE);
    CHECK(HERO_SPRITE + HERO_SPRITE_COUNT <= HAZARD_SPRITE);
    CHECK(HAZARD_SPRITE + HAZARD_COUNT <= FG_RAIN_SPRITE);
    CHECK(FG_EDGE_SPRITE + FG_EDGE_COUNT == SPRITE_SLOT_END);
}

static void test_lines(void) {
    int worst = 0;
    for (int rain = 0; rain < 2; rain++)
        for (int y = 0; y < SB_LINES; y++) {
            int n = sprite_budget_line(y, rain);
            if (n > worst) worst = n;
            CHECK(n <= SB_LIMIT);
        }
    printf("worst sprites per line: %d (limit %d)\n", worst, SB_LIMIT);
    CHECK(worst >= 1);
}

int main(void) {
    test_slots();
    test_lines();
    printf("%d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
