/* Host tests for the stadium crowd (src/core/stadium.c): the C motion port against the exporter's golden checksum, side logic, Fling scroll. */
#include <stdio.h>
#include <stdint.h>
#include "../../src/core/stadium.h"

static int failures, checks;
#define CHECK(c) do { checks++; if (!(c)) { failures++; printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

int main(void)
{
    Stadium s;
    uint16_t d[STADIUM_DIGITS];
    int i, r, c;
    CHECK(stadium_golden() == stadium_golden_expected());                     /* every cell of every mood/mode/frame equals the Python */
    stadium_reset(&s);
    for (r = 0; r < STADIUM_FAR_ROWS; r++) for (c = 0; c < STADIUM_COLS; c++) for (i = 0; i < 64; i++) {
        StadiumCell x;
        s.mode[0] = s.mode[1] = (uint8_t)(i & 1 ? STADIUM_WAVE : STADIUM_WINNER); s.t[0] = s.t[1] = (uint16_t)i;
        x = stadium_far(&s, r, c);
        CHECK(x.top != 0xFFFF && x.bot != 0xFFFF);
    }
    /* the idle far memo (filled by stadium_far and stadium_far_warm) returns what a fresh lookup returns */
    {
        StadiumCell a[STADIUM_FAR_ROWS][STADIUM_COLS][16];
        stadium_reset(&s);
        for (i = 0; i < 16; i++) for (r = 0; r < STADIUM_FAR_ROWS; r++) for (c = 0; c < STADIUM_COLS; c++) { s.t[0] = s.t[1] = (uint16_t)i; a[r][c][i] = stadium_far(&s, r, c); }
        stadium_reset(&s);
        for (r = 0; r < STADIUM_FAR_ROWS; r++) for (c = 0; c < STADIUM_COLS; c++) stadium_far_warm(r, c);
        for (i = 0; i < 48; i++) for (r = 0; r < STADIUM_FAR_ROWS; r++) for (c = 0; c < STADIUM_COLS; c++) {
            StadiumCell x;
            s.t[0] = s.t[1] = (uint16_t)i; x = stadium_far(&s, r, c);
            CHECK(x.top == a[r][c][i & 15].top && x.bot == a[r][c][i & 15].bot);
        }
    }
    /* stadium_column (idle memos, any mode, both storm looks, storm toggled) equals the per-cell lookups */
    for (i = 0; i < 4 * 48; i++) {
        StadiumCell v[STADIUM_FAR_ROWS + STADIUM_NEAR_ROWS];
        int storm = (i / 48) & 1;
        s.mode[0] = (uint8_t)(i < 96 ? STADIUM_IDLE : STADIUM_CHEER); s.mode[1] = (uint8_t)(i & 4 ? STADIUM_IDLE : STADIUM_WAVE);
        s.t[0] = s.t[1] = (uint16_t)(i % 48);
        for (c = 0; c < STADIUM_COLS; c++) {
            stadium_column(&s, c, storm, v);
            for (r = 0; r < STADIUM_FAR_ROWS; r++) { StadiumCell x = stadium_far(&s, r, c); CHECK(v[r].top == x.top && v[r].bot == x.bot); }
            for (r = 0; r < STADIUM_NEAR_ROWS; r++) { StadiumCell x = stadium_near(&s, r, c, storm); CHECK(v[STADIUM_FAR_ROWS + r].top == x.top && v[STADIUM_FAR_ROWS + r].bot == x.bot); }
        }
    }
    /* a score rise cheers its own side only, for a bounded time, then idles */
    stadium_reset(&s);
    stadium_set_scores(&s, 1, 0);
    CHECK(s.mode[0] == STADIUM_CHEER && s.mode[1] == STADIUM_IDLE);
    for (i = 0; i < 64; i++) stadium_step(&s);
    CHECK(s.mode[0] == STADIUM_IDLE);
    stadium_set_scores(&s, 1, 0);                                              /* no rise: no cheer */
    CHECK(s.mode[0] == STADIUM_IDLE);
    stadium_set_scores(&s, 1, 120);
    CHECK(s.mode[1] == STADIUM_CHEER && s.score[1] == 99);
    stadium_digit_tiles(&s, d);
    CHECK(d[2] == d[3]);                                                        /* 99: both digits are the 9 tile */
    /* finish: winner rolls forever, loser slumps, neither is overridden by a late score */
    stadium_finish(&s, 1);
    CHECK(s.mode[1] == STADIUM_WINNER && s.mode[0] == STADIUM_LOSER);
    for (i = 0; i < 5000; i++) stadium_step(&s);
    CHECK(s.mode[1] == STADIUM_WINNER && s.mode[0] == STADIUM_LOSER);
    stadium_set_scores(&s, 50, 99);
    CHECK(s.mode[0] == STADIUM_LOSER);
    stadium_wave(&s);
    CHECK(s.mode[0] == STADIUM_WAVE && s.mode[1] == STADIUM_WAVE);
    for (i = 0; i < 64; i++) stadium_step(&s);
    CHECK(s.mode[0] == STADIUM_IDLE && s.mode[1] == STADIUM_IDLE);
    /* Gum Fling: stand at 1/4 field speed, 48 px at most, and the 23 column plane covers it */
    CHECK(stadium_fling_x(0) == 0 && stadium_fling_x(192) == -48 && stadium_fling_x(500) == -48 && stadium_fling_x(-5) == 0);
    CHECK(STADIUM_FLING_COLS * 16 >= 320 - stadium_fling_x(STADIUM_FLING_SCROLL_MAX));
    printf("%d checks, %d failures\n", checks, failures);
    return failures != 0;
}
