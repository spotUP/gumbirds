/* Round clear banner core (src/core/banner.c) against the spec thoughts/shared/drafts/2026-11-10-round-clear-banner-final2/
 * banner_spec.txt: per-frame changed-cell counts (split draw rows), the final cell maps, the waiting state, round digits. */
#include <stdio.h>
#include <stdint.h>
#include "../../src/core/banner.h"
#include "gen/fix_font.h"

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; if (failures <= 10) printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

/* expected maps and counts, transcribed from the spec: {tile, palette} per cell, rows 10..17, cols 9..30 */
#define GB FIXFONT_GAME_BASE /* the maps were written for the old font at tile 0; game tiles now start at GB */
static const uint16_t MAP_ROUND[8][22][2] = {
    {{GB+56,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+58,1}},
    {{GB+59,1}, {GB+96,1}, {GB+55,1}, {GB+107,1}, {GB+55,1}, {GB+107,1}, {GB+55,1}, {GB+55,1}, {GB+111,1}, {GB+55,1}, {GB+110,1}, {GB+55,1}, {GB+111,1}, {GB+55,1}, {GB+111,1}, {GB+55,1}, {GB+100,1}, {GB+55,1}, {GB+99,1}, {GB+55,1}, {GB+135,1}, {GB+60,1}},
    {{GB+59,1}, {GB+55,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+55,1}, {GB+60,1}},
    {{GB+59,1}, {GB+55,1}, {GB+55,1}, {GB+146,1}, {GB+147,1}, {GB+55,1}, {GB+111,1}, {GB+107,1}, {GB+96,1}, {GB+120,1}, {GB+100,1}, {GB+113,1}, {GB+55,1}, {GB+123,1}, {GB+55,1}, {GB+118,1}, {GB+104,1}, {GB+109,1}, {GB+114,1}, {GB+55,1}, {GB+55,1}, {GB+60,1}},
    {{GB+59,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+60,1}},
    {{GB+59,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+161,3}, {GB+162,3}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+60,1}},
    {{GB+59,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+113,3}, {GB+110,3}, {GB+116,3}, {GB+109,3}, {GB+99,3}, {GB+55,1}, {GB+177,3}, {GB+178,3}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+60,1}},
    {{GB+61,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+63,1}}
};
static const uint16_t MAP_LAST[8][22][2] = {
    {{GB+56,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+58,1}},
    {{GB+59,1}, {GB+96,1}, {GB+55,1}, {GB+107,1}, {GB+55,1}, {GB+107,1}, {GB+55,1}, {GB+55,1}, {GB+111,1}, {GB+55,1}, {GB+110,1}, {GB+55,1}, {GB+111,1}, {GB+55,1}, {GB+111,1}, {GB+55,1}, {GB+100,1}, {GB+55,1}, {GB+99,1}, {GB+55,1}, {GB+135,1}, {GB+60,1}},
    {{GB+59,1}, {GB+55,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+55,1}, {GB+60,1}},
    {{GB+59,1}, {GB+55,1}, {GB+55,1}, {GB+146,1}, {GB+147,1}, {GB+55,1}, {GB+111,1}, {GB+107,1}, {GB+96,1}, {GB+120,1}, {GB+100,1}, {GB+113,1}, {GB+55,1}, {GB+123,1}, {GB+55,1}, {GB+118,1}, {GB+104,1}, {GB+109,1}, {GB+114,1}, {GB+55,1}, {GB+55,1}, {GB+60,1}},
    {{GB+59,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+60,1}},
    {{GB+59,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+108,3}, {GB+96,3}, {GB+115,3}, {GB+98,3}, {GB+103,3}, {GB+55,1}, {GB+110,3}, {GB+117,3}, {GB+100,3}, {GB+113,3}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+60,1}},
    {{GB+59,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+60,1}},
    {{GB+61,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+63,1}}
};
static const uint16_t MAP_WAIT[8][22][2] = {
    {{GB+56,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+57,1}, {GB+58,1}},
    {{GB+59,1}, {GB+132,4}, {GB+55,1}, {GB+132,4}, {GB+55,1}, {GB+132,4}, {GB+55,1}, {GB+55,1}, {GB+132,4}, {GB+55,1}, {GB+132,4}, {GB+55,1}, {GB+132,4}, {GB+55,1}, {GB+132,4}, {GB+55,1}, {GB+132,4}, {GB+55,1}, {GB+132,4}, {GB+55,1}, {GB+132,4}, {GB+60,1}},
    {{GB+59,1}, {GB+55,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+74,1}, {GB+55,1}, {GB+60,1}},
    {{GB+59,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+137,4}, {GB+137,4}, {GB+137,4}, {GB+137,4}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+60,1}},
    {{GB+59,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+60,1}},
    {{GB+59,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+60,1}},
    {{GB+59,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+137,4}, {GB+137,4}, {GB+137,4}, {GB+137,4}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+55,1}, {GB+60,1}},
    {{GB+61,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+62,1}, {GB+63,1}}
};
static const uint8_t COUNT_P1_ROUND02[120] = {56,60,60,0,1,0,0,0,2,0,0,0,3,0,0,0,4,0,0,0,4,0,0,0,4,0,0,0,4,0,0,0,4,0,0,0,4,0,0,0,4,0,0,0,3,0,0,0,2,0,0,0,1,0,0,0,14,0,0,0,13,0,0,0,0,0,0,0,10,0,0,0,0,0,0,0,9,0,0,0,0,0,0,0,9,0,0,0,0,0,0,0,9,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0};
static const uint8_t COUNT_P2_ROUND02[120] = {56,60,60,0,1,0,0,0,2,0,0,0,3,0,0,0,4,0,0,0,4,0,0,0,4,0,0,0,4,0,0,0,4,0,0,0,4,0,0,0,4,0,0,0,3,0,0,0,2,0,0,0,1,0,0,0,14,0,0,0,13,0,0,0,0,0,0,0,10,0,0,0,0,0,0,0,9,0,0,0,0,0,0,0,9,0,0,0,0,0,0,0,9,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0};
static const uint8_t COUNT_CPU_ROUND02[120] = {56,60,60,0,1,0,0,0,2,0,0,0,3,0,0,0,4,0,0,0,4,0,0,0,4,0,0,0,4,0,0,0,4,0,0,0,4,0,0,0,4,0,0,0,3,0,0,0,2,0,0,0,1,0,0,0,14,0,0,0,0,0,0,0,0,0,0,0,10,0,0,0,0,0,0,0,9,0,0,0,0,0,0,0,9,0,0,0,0,0,0,0,9,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0};
static const uint8_t COUNT_DRAW_ROUND02[120] = {56,60,60,0,1,0,0,0,2,0,0,0,3,0,0,0,4,0,0,0,4,0,0,0,4,0,0,0,4,0,0,0,4,0,0,0,4,0,0,0,4,0,0,0,3,0,0,0,2,0,0,0,1,0,0,0,11,0,0,0,11,0,0,0,0,0,0,0,10,0,0,0,0,0,0,0,9,0,0,0,0,0,0,0,9,0,0,0,0,0,0,0,9,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0};
static const uint8_t COUNT_P1_MATCHOVER[120] = {56,60,60,0,1,0,0,0,2,0,0,0,3,0,0,0,4,0,0,0,4,0,0,0,4,0,0,0,4,0,0,0,4,0,0,0,4,0,0,0,4,0,0,0,3,0,0,0,2,0,0,0,1,0,0,0,14,0,0,0,13,0,0,0,0,0,0,0,10,0,0,0,0,0,0,0,9,0,0,0,0,0,0,0,9,0,0,0,0,0,0,0,9,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0};

static int map_matches(const uint16_t m[8][22][2], uint16_t frame, const BannerCtx *ctx)
{
    int r, c, bad = 0;
    for (r = 0; r < BANNER_H; r++) {
        for (c = 0; c < BANNER_W; c++) {
            uint16_t v = banner_cell(frame, ctx, (uint8_t)(BANNER_COL + c), (uint8_t)(BANNER_ROW + r));
            if (v != (uint16_t)((m[r][c][1] << 12) | m[r][c][0])) bad++;
        }
    }
    return bad;
}

/* Cells whose value differs from the previous frame, per frame 0..119; frame 0 compares against undrawn (blank) cells. */
static void count_changes(const BannerCtx *ctx, int out[120], int *after_93, uint16_t *last)
{
    uint16_t prev[BANNER_H][BANNER_W];
    int f, r, c;
    *after_93 = 0;
    for (r = 0; r < BANNER_H; r++) for (c = 0; c < BANNER_W; c++) prev[r][c] = banner_cell(0, ctx, 0, 0);
    for (f = 0; f < 120; f++) {
        out[f] = 0;
        for (r = 0; r < BANNER_H; r++) {
            for (c = 0; c < BANNER_W; c++) {
                uint16_t v = banner_cell((uint16_t)f, ctx, (uint8_t)(BANNER_COL + c), (uint8_t)(BANNER_ROW + r));
                if (v != prev[r][c]) { out[f]++; if (f >= 93) (*after_93)++; }
                prev[r][c] = v;
            }
        }
    }
    *last = prev[0][0];
}

static void expect_counts(const BannerCtx *ctx, const uint8_t want[120])
{
    int got[120], a93, f, bad = 0;
    uint16_t last;
    count_changes(ctx, got, &a93, &last);
    for (f = 0; f < 120; f++) if (got[f] != want[f]) bad++;
    CHECK(bad == 0);
    CHECK(a93 == 0);   /* frames 93..119 write nothing new */
}

/* Rows outside banner_dirty_rows(f) must equal the previous frame; the masks must also be tight (few writes). */
static void check_dirty_rows(void)
{
    static const uint16_t rounds[3] = {1, 2, 57};
    int w, l, k, f, r, c, zero = 0, fat = 0, miss = 0;
    for (f = 1; f < 120; f++) {
        uint8_t m = banner_dirty_rows((uint16_t)f);
        int bits = 0;
        for (r = 0; r < BANNER_H; r++) bits += (m >> r) & 1;
        if (!m) zero++;
        if (f > 2 && bits > 2) fat++;
        for (w = 0; w < 4; w++) for (l = 0; l < 2; l++) for (k = 0; k < 3; k++) {
            BannerCtx ctx; ctx.winner = (uint8_t)w; ctx.round = rounds[k]; ctx.last = (uint8_t)l;
            for (r = 0; r < BANNER_H; r++) {
                if ((m >> r) & 1) continue;
                for (c = 0; c < BANNER_W; c++) {
                    if (banner_cell((uint16_t)f, &ctx, (uint8_t)(BANNER_COL + c), (uint8_t)(BANNER_ROW + r)) !=
                        banner_cell((uint16_t)(f - 1), &ctx, (uint8_t)(BANNER_COL + c), (uint8_t)(BANNER_ROW + r))) miss++;
                }
            }
        }
    }
    CHECK(miss == 0);
    CHECK(zero >= 60);
    CHECK(fat == 0);
    CHECK(banner_dirty_rows(0) == (uint8_t)((1 << BANNER_H) - 1));
}

int main(void)
{
    BannerCtx p1 = {BANNER_P1, 2, 0}, p2 = {BANNER_P2, 2, 0}, cpu = {BANNER_CPU, 2, 0}, dr = {BANNER_DRAW, 2, 0};
    BannerCtx r12 = {BANNER_P1, 12, 0}, last = {BANNER_P1, 12, 1}, last_dr = {BANNER_DRAW, 3, 1};
    int r, c, inside_blank = 0;

    check_dirty_rows();
    expect_counts(&p1, COUNT_P1_ROUND02);
    expect_counts(&p2, COUNT_P2_ROUND02);
    expect_counts(&cpu, COUNT_CPU_ROUND02);
    expect_counts(&dr, COUNT_DRAW_ROUND02);
    expect_counts(&last, COUNT_P1_MATCHOVER);

    CHECK(map_matches(MAP_ROUND, 119, &r12) == 0);      /* "12" renders as tens 1, ones 2 */
    CHECK(map_matches(MAP_LAST, 119, &last) == 0);
    CHECK(map_matches(MAP_ROUND, 93, &r12) == 0);       /* steady from frame 93 */
    CHECK(map_matches(MAP_WAIT, 2, &p1) == 0 && map_matches(MAP_WAIT, 3, &p1) == 0);
    {
        /* round 2 renders "02": tens backed tall tile top/bottom + 0, ones + 2, gold palette 3 */
        CHECK(banner_cell(119, &p1, 22, 15) == (uint16_t)((3 << 12) | (FIXFONT_TALL_TOP + FIXFONT_TALL_BACKED + 0)));
        CHECK(banner_cell(119, &p1, 22, 16) == (uint16_t)((3 << 12) | (FIXFONT_TALL_BOTTOM + FIXFONT_TALL_BACKED + 0)));
        CHECK(banner_cell(119, &p1, 23, 15) == (uint16_t)((3 << 12) | (FIXFONT_TALL_TOP + FIXFONT_TALL_BACKED + 2)));
        CHECK(banner_cell(119, &p1, 23, 16) == (uint16_t)((3 << 12) | (FIXFONT_TALL_BOTTOM + FIXFONT_TALL_BACKED + 2)));
    }
    CHECK(banner_cell(0, &p1, 0, 0) == (uint16_t)FIXFONT_BLANK);   /* outside the panel */
    CHECK(banner_cell(119, &p1, 40, 27) == (uint16_t)FIXFONT_BLANK);
    CHECK(banner_cell(60, &last_dr, 14, 13) == (uint16_t)((FIXFONT_PAL_DIM << 12) | (FIXFONT_BACKED + FIXFONT_LETTER_A + 13))); /* draw case: N, dim */
    for (r = 0; r < BANNER_H; r++) for (c = 0; c < BANNER_W; c++)
        if (banner_cell(0, &p1, (uint8_t)(BANNER_COL + c), (uint8_t)(BANNER_ROW + r)) == FIXFONT_BLANK) inside_blank++;
    CHECK(inside_blank == 176 - 56);                      /* frame 0 draws exactly the outline */

    printf("test_banner: %d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
