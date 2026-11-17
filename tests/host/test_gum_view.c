/* gum_view: gum amount -> bubble level (sheet numbering), size class and pop set per level. Prints one FAIL line per miss
 * and a final PASS/FAIL line. */
#include <stdio.h>
#include <stdint.h>
#include "../../src/core/gum_view.h"
#include "gen/sootling_tables.h"

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
    /* Offset table from the generated per frame tables (gum-mouth v4: grip column, row shift, bubble hidden in the pop poses). */
    {
        static const int8_t gdx[] = SOOTLING_TABLE_GUM_DX, gdy[] = SOOTLING_TABLE_GUM_DY;
        static const uint8_t gsh[] = SOOTLING_TABLE_GUM_SHOW;
        int hidden = 0;
        check((int)(sizeof gdx) == GUM_VIEW_BIRD_FRAMES && (int)sizeof gdy == GUM_VIEW_BIRD_FRAMES && (int)sizeof gsh == GUM_VIEW_BIRD_FRAMES,
              "tables cover every bird frame", (int)sizeof gdx, GUM_VIEW_BIRD_FRAMES);
        for (k = 0; k < GUM_VIEW_BIRD_FRAMES; k++) {
            GumOffset o = gum_view_offset((uint8_t)k, 0), m = gum_view_offset((uint8_t)k, 1);
            check(o.dx == GUM_BIRD_DX + gdx[k], "dx from table", o.dx, GUM_BIRD_DX + gdx[k]);
            check(m.dx == GUM_BIRD_DX_FLIP - gdx[k], "flipped dx mirrors the grip", m.dx, GUM_BIRD_DX_FLIP - gdx[k]);
            check(o.dy == GUM_BIRD_ROW + gdy[k] && m.dy == o.dy, "dy from table", o.dy, GUM_BIRD_ROW + gdy[k]);
            check(o.show == gsh[k] && m.show == o.show, "show from table", o.show, gsh[k]);
            if (!o.show) hidden++;
        }
        check(hidden > 0 && hidden < GUM_VIEW_BIRD_FRAMES, "some frames hide the bubble, most show it", hidden, 1);
    }
    /* Out of range is bounds safe: no bubble, no offset. */
    for (k = GUM_VIEW_BIRD_FRAMES; k < 256; k++) {
        GumOffset o = gum_view_offset((uint8_t)k, k & 1);
        check(o.dx == 0 && o.dy == 0 && o.show == 0, "out of range offset", o.dx + o.dy + o.show, 0);
    }
    /* Leak rule: arena / arcade at exactly 1 balloon (human or computer, same function); Trip below half with a bubble left. */
    for (k = 0; k <= 4; k++) check(gum_view_leaks_balloons((uint8_t)k) == (k == 1), "leak shows at exactly 1 balloon", k, k == 1);
    check(gum_view_leaks_gum(0) == 0, "no leak without a bubble", 0, 0);
    check(gum_view_leaks_gum(1) == 1 && gum_view_leaks_gum(GUM_MAX / 2 - 1) == 1, "leak below half", 1, 1);
    check(gum_view_leaks_gum(GUM_MAX / 2) == 0 && gum_view_leaks_gum(GUM_MAX) == 0, "no leak at or above half", GUM_MAX / 2, 0);
    for (k = 0; k < 4 * GUM_LEAK_FRAMES * GUM_LEAK_TICK; k++) {
        check(gum_view_leak_frame((uint32_t)k) == (k / GUM_LEAK_TICK) % GUM_LEAK_FRAMES, "leak frame clock", k, 0);
        check(gum_view_frame(GUM_STATE_WOBBLE, gum_view_wobble_clock((uint32_t)k, 1)) == gum_view_leak_frame((uint32_t)k) % GUM_VIEW_WOBBLE_SHEET, "damaged wobble follows the leak frame", k, 0);
        check(gum_view_wobble_clock((uint32_t)k, 0) == (uint32_t)k, "healthy wobble clock unchanged", k, k);
    }
    printf(bad ? "FAIL gum_view (%d)\n" : "PASS gum_view\n", bad);
    return bad != 0;
}
