/* gum_view: gum amount -> bubble level (sheet numbering), size class and pop set per level. Prints one FAIL line per miss
 * and a final PASS/FAIL line. */
#include <stdio.h>
#include "../../src/core/gum_view.h"

#define STEP (GUM_MAX / GUM_VIEW_LEVELS)

static int bad;
static void check(int ok, const char *what, int got, int want)
{
    if (!ok) { printf("FAIL %s: got %d, want %d\n", what, got, want); bad++; }
}

int main(void)
{
    int k, g, prev = 0;
    /* Pinned values (user sheet table: 705..768 is level 12, GUM_START 768 is level 12). */
    check(GUM_MAX == 1024 && GUM_START == 768, "tuning defaults", GUM_MAX, 1024);
    check(gum_view_level(0) == 0, "gum 0 shows no bubble", gum_view_level(0), 0);
    check(gum_view_level(1) == 1, "gum 1 is level 1", gum_view_level(1), 1);
    check(gum_view_level(64) == 1, "gum 64 is level 1", gum_view_level(64), 1);
    check(gum_view_level(65) == 2, "gum 65 is level 2", gum_view_level(65), 2);
    check(gum_view_level(GUM_START) == 12, "GUM_START is level 12", gum_view_level(GUM_START), 12);
    check(gum_view_level(GUM_MAX) == 16, "GUM_MAX is level 16", gum_view_level(GUM_MAX), 16);
    /* Every boundary: STEP * k is the last gum of level k, STEP * k + 1 the first of level k + 1. */
    for (k = 1; k <= 15; k++) {
        check(gum_view_level(STEP * k) == k, "last gum of a level", gum_view_level(STEP * k), k);
        check(gum_view_level(STEP * k + 1) == k + 1, "first gum of next level", gum_view_level(STEP * k + 1), k + 1);
    }
    /* Monotonic, steps by at most 1, over the whole meter. */
    for (g = 0; g <= GUM_MAX; g++) {
        int l = gum_view_level((uint16_t)g);
        check(l >= prev && l - prev <= 1 && l <= GUM_VIEW_LEVELS, "monotonic step", l, prev);
        prev = l;
    }
    /* Above the meter clamps. */
    check(gum_view_level(GUM_MAX + 1) == 16, "above max clamps", gum_view_level(GUM_MAX + 1), 16);
    check(gum_view_level(65535) == 16, "65535 clamps", gum_view_level(65535), 16);
    /* Size class and pop set. */
    for (k = 1; k <= 16; k++) {
        GumSize want = k >= 13 ? GUM_SIZE_LARGE : k >= 8 ? GUM_SIZE_MEDIUM : k >= 5 ? GUM_SIZE_SMALL : GUM_SIZE_TINY;
        GumPop pop = k >= 8 ? GUM_POP_LARGE : GUM_POP_SMALL;
        check(gum_view_size((uint8_t)k) == want, "size class", gum_view_size((uint8_t)k), want);
        check(gum_view_pop((uint8_t)k) == pop, "pop set", gum_view_pop((uint8_t)k), pop);
    }
    printf(bad ? "FAIL gum_view (%d)\n" : "PASS gum_view\n", bad);
    return bad != 0;
}
