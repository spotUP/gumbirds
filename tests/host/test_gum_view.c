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
    /* Anim numbers: level L wobbles in 16 - L, pop sets 16 / 17 by the last level. */
    for (k = 1; k <= GUM_VIEW_LEVELS; k++) {
        check(gum_view_anim((uint8_t)k, GUM_STATE_WOBBLE) == GUM_VIEW_LEVELS - k, "wobble anim", gum_view_anim((uint8_t)k, GUM_STATE_WOBBLE), GUM_VIEW_LEVELS - k);
        check(gum_view_anim((uint8_t)k, GUM_STATE_POP) == (k >= 8 ? 16 : 17), "pop anim", gum_view_anim((uint8_t)k, GUM_STATE_POP), k >= 8 ? 16 : 17);
    }
    check(gum_view_anim(0, GUM_STATE_WOBBLE) == 15, "level 0 acts as level 1", gum_view_anim(0, GUM_STATE_WOBBLE), 15);
    /* Timing: W game frames per wobble frame looping over 6, P per pop frame over 7, pop holds the last frame. */
    check(GUM_WOBBLE_FRAMES == 6 && GUM_POP_FRAMES == 3, "timing defaults", GUM_WOBBLE_FRAMES, 6);
    for (g = 0; g < 4 * GUM_VIEW_WOBBLE_SHEET * GUM_WOBBLE_FRAMES; g++) {
        int want = (g / GUM_WOBBLE_FRAMES) % GUM_VIEW_WOBBLE_SHEET;
        check(gum_view_frame(GUM_STATE_WOBBLE, (uint32_t)g) == want, "wobble frame", gum_view_frame(GUM_STATE_WOBBLE, (uint32_t)g), want);
    }
    check(gum_view_frame(GUM_STATE_WOBBLE, 0xFFFFFFFFu) < GUM_VIEW_WOBBLE_SHEET, "wobble frame at u32 max in range", gum_view_frame(GUM_STATE_WOBBLE, 0xFFFFFFFFu), 0);
    for (g = 0; g < GUM_VIEW_POP_SHEET * GUM_POP_FRAMES + 20; g++) {
        int want = g / GUM_POP_FRAMES < GUM_VIEW_POP_SHEET ? g / GUM_POP_FRAMES : GUM_VIEW_POP_SHEET - 1;
        check(gum_view_frame(GUM_STATE_POP, (uint32_t)g) == want, "pop frame", gum_view_frame(GUM_STATE_POP, (uint32_t)g), want);
        check(gum_view_pop_done((uint32_t)g) == (g >= GUM_VIEW_POP_SHEET * GUM_POP_FRAMES), "pop done", gum_view_pop_done((uint32_t)g), g >= GUM_VIEW_POP_SHEET * GUM_POP_FRAMES);
    }
    /* Offset table, real values from bubble_motion.json (subtle.dy.player, shows_bubble.player): FLAP2 0..7 dy [4,4,2,0,0,1,2,3],
     * WALK2 77..84 dy [2,1,1,1,2,1,1,1], bit 1 on 0..28, 0 on 29..42, 1 on 43..51, 0 on 52..76, 1 on 77..104. Index 55 is the only -1 (FALL). */
    {
        static const int flap[8] = { 4, 4, 2, 0, 0, 1, 2, 3 }, walk[8] = { 2, 1, 1, 1, 2, 1, 1, 1 };
        int shown = 0, hidden = 0;
        for (k = 0; k < 8; k++) {
            check(gum_view_offset((uint8_t)k, 0).dy == GUM_BIRD_ROW + flap[k], "flap dy", gum_view_offset((uint8_t)k, 0).dy, GUM_BIRD_ROW + flap[k]);
            check(gum_view_offset((uint8_t)(77 + k), 0).dy == GUM_BIRD_ROW + walk[k], "walk dy", gum_view_offset((uint8_t)(77 + k), 0).dy, GUM_BIRD_ROW + walk[k]);
        }
        check(gum_view_offset(55, 0).dy == GUM_BIRD_ROW - 1, "fall dy -1", gum_view_offset(55, 0).dy, GUM_BIRD_ROW - 1);
        for (k = 0; k < GUM_VIEW_BIRD_FRAMES; k++) {
            GumOffset o = gum_view_offset((uint8_t)k, 0), m = gum_view_offset((uint8_t)k, 1);
            int want = k <= 28 || (k >= 43 && k <= 51) || k >= 77;
            check(o.show == want, "show bit", o.show, want);
            check(o.dx == GUM_BIRD_DX && m.dx == GUM_BIRD_DX_FLIP && m.dy == o.dy && m.show == o.show, "flip changes dx only", m.dx, GUM_BIRD_DX_FLIP);
            check(o.dy >= GUM_BIRD_ROW - 1 && o.dy <= GUM_BIRD_ROW + 5, "dy in table range", o.dy, GUM_BIRD_ROW);
            if (o.show) shown++; else hidden++;
        }
        check(shown == 66 && hidden == 39, "66 frames with a string, 39 without", shown, 66);
    }
    /* Out of range is bounds safe: no bubble, no offset. */
    for (k = GUM_VIEW_BIRD_FRAMES; k < 256; k++) {
        GumOffset o = gum_view_offset((uint8_t)k, k & 1);
        check(o.dx == 0 && o.dy == 0 && o.show == 0, "out of range offset", o.dx + o.dy + o.show, 0);
    }
    printf(bad ? "FAIL gum_view (%d)\n" : "PASS gum_view\n", bad);
    return bad != 0;
}
