/* Result screen (src/core/result.c, result_view.c): sequence timing, events, score total added once, every cell opaque, dirty regions. */
#include <stdio.h>
#include <stdint.h>
#include "../../src/core/result.h"
#include "../../src/core/result_view.h"
#include "../../src/core/arcade.h"
#include "gen/fix_font.h"

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; if (failures <= 10) printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

/* Runs a whole sequence: returns frames; fills first-frame of each event and the total added. */
static int run(int caught, int number, int perfect, uint32_t start, uint32_t *added, int *ev_frame, int *adds_before_tally)
{
    Result r;
    int f = 0, i, first_add = 0;
    uint32_t add;
    for (i = 0; i < 4; i++) ev_frame[i] = -1;
    *added = 0;
    res_start(&r, caught, number, perfect, start);
    while (r.active && f < 2000) {
        uint8_t ev = res_step(&r, &add);
        f++;
        for (i = 0; i < 4; i++) if ((ev & (1 << i)) && ev_frame[i] < 0) ev_frame[i] = f;
        if (add) { if (!first_add) first_add = f; *added += add; CHECK(add % 100 == 0); }
        CHECK(r.score_shown == start + *added);
    }
    *adds_before_tally = first_add;
    CHECK(r.total_left == 0);
    return f;
}

int main(void)
{
    static const int caught_set[] = { 0, 7, 20 };
    int ci, number, ev[4], first, f;
    uint32_t added;
    for (ci = 0; ci < 3; ci++) for (number = 1; number <= 5; number += 2) {
        int caught = caught_set[ci], perfect = caught == 20;
        uint32_t want = (uint32_t)caught * (uint32_t)arc_bonus_value(number) + (perfect ? (uint32_t)arc_bonus_perfect(number) : 0u);
        f = run(caught, number, perfect, 1234, &added, ev, &first);
        CHECK(added == want);
        CHECK(ev[0] == 40);  /* vanish: after the popped wait and the each wait (20 + 20 frames) */
        CHECK(f < 2000);
        if (caught) CHECK(first > 40 + 2 + 20 + (perfect ? 120 : 0));  /* no score before the tally starts */
        if (perfect) {
            CHECK(ev[2] == 62);  /* jingle after the total wait */
            CHECK(ev[3] > ev[2] + 120);                     /* bonus after the hold and the tally */
        } else CHECK(ev[2] < 0 && ev[3] < 0);
        if (caught) CHECK(ev[1] > 0);
    }
    /* exact timeline: caught 0: 20 + 20 + 2 + 20 + 120, one tally frame, wait 10 (the 120 hold also runs without a ticket) */
    f = run(0, 1, 0, 0, &added, ev, &first);
    CHECK(added == 0);
    CHECK(f == 20 + 20 + 2 + 20 + 120 + 1 + 10);
    f = run(20, 1, 1, 0, &added, ev, &first);  /* 20 * 300 = 6000: 60 steps of 2 frames */
    CHECK(f == 333 && ev[2] == 62 && ev[3] == 313);  /* jingle at 62, 60 tally steps from 183, bonus at 313, end 20 frames later */
    CHECK(added == 6000 + 10000);
    /* score added once: total_left plus the sum of adds equals the total at every frame */
    {
        Result r;
        uint32_t add, sum = 0;
        res_start(&r, 5, 2, 0, 0);
        while (r.active) { res_step(&r, &add); sum += add; CHECK(sum + r.total_left == 2500u); }
        CHECK(sum == 2500u);
    }
    /* view: every cell opaque, dirty bookkeeping */
    {
        Result r;
        uint32_t add;
        uint8_t c, row, d;
        int frames;
        res_start(&r, 20, 3, 1, 5000);
        for (frames = 0; frames < 800 && r.active; frames++) {
            for (row = 0; row < RESV_H; row++) for (c = 0; c < RESV_W; c++) {
                uint16_t v = result_cell(&r, c, row);
                if ((v & 0xfff) == FIXFONT_BLANK || (v >> 12) >= FIXFONT_PAL_COUNT) CHECK(0);
            }
            res_step(&r, &add);
        }
        /* the cell function changes only inside the regions of the dirty bits */
        res_start(&r, 7, 1, 0, 0);
        {
            uint16_t before[RESV_H][RESV_W];
            int bad = 0;
            for (frames = 0; frames < 800 && r.active; frames++) {
                for (row = 0; row < RESV_H; row++) for (c = 0; c < RESV_W; c++) before[row][c] = result_cell(&r, c, row);
                r.dirty = 0;
                res_step(&r, &add);
                for (row = 0; row < RESV_H; row++) for (c = 0; c < RESV_W; c++) {
                    if (result_cell(&r, c, row) == before[row][c]) continue;
                    for (d = 1; d <= RES_DIRTY_TICKET; d = (uint8_t)(d << 1)) {
                        uint8_t r0, r1, c0, c1;
                        result_region(d, &r0, &r1, &c0, &c1);
                        if ((r.dirty & d) && row >= r0 && row <= r1 && c >= c0 && c <= c1) break;
                    }
                    if (d > RES_DIRTY_TICKET) bad++;
                }
            }
            CHECK(bad == 0);
        }
    }
    printf("test_result: %d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
