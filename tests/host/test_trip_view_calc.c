/* Gum Trip view maths (plan T-B9 step V0): meter cells, hazard screen position, and the sprites-per-line sweep.
 * Prints the maximum sprite columns per line (full strip and rim row only) over many seeds and scroll positions;
 * the figure is the deliverable, only the generator budgets are asserted. */
#include <stdio.h>
#include <stdint.h>
#include "../../src/core/trip_view.h"
#include "../../src/core/trip_hit.h"
#include "../../src/core/trip_gen.h"
#include "../../src/core/trip_rival.h"
#include "../../src/core/obj_pool.h"
#include "../../src/core/bg_scroll.h"
#include "../../src/core/sprite_budget.h"
#include "../../src/sprite_slots.h"
#include "gen/city_tables.h"
#include "gen/sootling_tables.h"
#define SOOTLING_MAX_COLUMNS ((SOOTLING_ART_W + 15) / 16)   /* art padded to whole tiles; main.c asserts SOOT_COLUMNS == the generated value */

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; if (failures <= 400) printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

#define SEEDS 1000
#define SCROLL_END 40000u
#define SCROLL_STEP 151u   /* prime, so the sweep does not alias with the 192 px chunks or 16 px columns */

static void meter_tests(void) {
    int gum, c;
    for (gum = 0; gum <= TRIP_VIEW_GUM_MAX; gum++) {
        int step = trip_view_meter_step(gum), sum = 0;
        CHECK((step == 0) == (gum == 0));
        CHECK(step >= 0 && step <= 8);
        for (c = 0; c < TRIP_VIEW_METER_CELLS; c++) {
            int v = trip_view_meter_cell(step, c);
            CHECK(v >= 0 && v <= 2);
            sum += v;
        }
        CHECK(sum == step);
        CHECK(trip_view_warning(step) == (step <= 2));
    }
    for (gum = 1; gum <= 128; gum++) CHECK(trip_view_meter_step(gum) == 1);
    CHECK(trip_view_meter_step(129) == 2);
    CHECK(trip_view_meter_step(512) == 4);
    CHECK(trip_view_meter_step(1024) == 8);
    CHECK(trip_view_meter_step(0) == 0);
    CHECK(trip_view_meter_step(1) == 1);
    CHECK(trip_view_meter_step(TRIP_VIEW_GUM_MAX - 1) == 8);
    CHECK(trip_view_meter_step(TRIP_VIEW_GUM_MAX + 100) == 8);
    CHECK(trip_view_meter_step(-5) == 0);
    for (gum = 1; gum <= 8; gum++) {   /* every step border: last gum of step s, first gum of step s + 1 */
        CHECK(trip_view_meter_step(128 * gum) == gum);
        CHECK(gum == 8 || trip_view_meter_step(128 * gum + 1) == gum + 1);
    }
    CHECK(trip_view_screen_x(100, 160) == -60);
    CHECK(trip_view_screen_x(160, 100) == 60);
    CHECK(trip_view_screen_x(0xFFFF0000u, 0xFFFE0000u) == 0x10000);
}

/* Advance until the held chunks cover the screen (the count after init is not assumed). */
static void cover(TripGen *g, uint32_t scroll) {
    int n;
    for (n = 0; n < 12; n++) {
        const TripChunk *last = 0;
        int i;
        tripgen_advance(g, scroll);
        for (i = 0; i < g->count; i++) {
            int s = g->head + i;
            if (s >= TRIP_GEN_RING) s -= TRIP_GEN_RING;
            last = &g->ring[s];
        }
        if (last && last->wx + TRIP_CHUNK_PX >= scroll + TRIP_VIEW_SCREEN_W) break;
    }
}

static void haz_y_tests(void) {
    uint32_t seed;
    for (seed = 1; seed <= SEEDS; seed++) {
        TripGen g;
        uint32_t scroll = (seed * 37u) & 1023u, f;
        int s;
        tripgen_init(&g, seed);
        cover(&g, scroll);
        for (s = 0; s < g.count; s++) {
            int idx = g.head + s, i;
            const TripChunk *c;
            if (idx >= TRIP_GEN_RING) idx -= TRIP_GEN_RING;
            c = &g.ring[idx];
            for (i = 0; i < c->n_haz; i++)
                for (f = 0; f < 256; f += 17) {
                    int x, y;
                    trip_view_haz_xy(c, i, scroll, f, &x, &y);
                    CHECK(y == trip_hit_haz_y(&c->haz[i], f));
                    CHECK(x == (int)(c->wx + (uint32_t)c->haz[i].x) - (int)scroll);
                }
        }
    }
}

typedef struct { int v; uint32_t seed, scroll; int y; TripViewLine r; } Max;
static void upd(Max *m, int v, uint32_t seed, uint32_t scroll, int y, TripViewLine r) {
    if (v > m->v) { m->v = v; m->seed = seed; m->scroll = scroll; m->y = y; m->r = r; }
}

/* Background planes still drawn in Gum Trip (sky, far, mid A, mid B; the near plane is hidden): sprite columns on line y.
 * Exact: src/bg.c writes one sprite per column with SCB3 height COL_ROWS[slot - BG_SKY_SPRITE] and top PLANE_TOP + 16 * COL_ROW0[slot - BG_SKY_SPRITE] (generated
 * tables, the same ones the ROM uses). A column counts only when its screen x lies in -15..319; slot c sits at x = plane_x + 16 c with
 * the plane phase (plane_x mod 16, -15..0) not modelled, so the bound takes the worst phase: plane columns 0..20 (columns 21 and up are never
 * on screen: 16 * 21 - 15 = 321). */
static const unsigned char k_col_row0[BG_SPRITE_TOTAL] = CITY_TABLE_COL_ROW0;
static const unsigned char k_col_rows[BG_SPRITE_TOTAL] = CITY_TABLE_COL_ROWS;
static const int k_plane_top[5] = CITY_TABLE_PLANE_TOP;
#define BG_MAX_VISIBLE_COLS 21
static int plane_cols_on_line_v(int p, int first, int count, int y, int drop, int clip) {
    int c, n = 0;
    if (drop & (1 << p)) return 0;
    if (clip && ((p == 1 && y >= 96) || (p == 2 && y >= 128))) return 0;   /* what-if: far plane ends at 96, mid A at 128 */
    for (c = 0; c < count && c < BG_MAX_VISIBLE_COLS; c++) {
        int slot = first + c - BG_SKY_SPRITE, top = k_plane_top[p] + 16 * k_col_row0[slot];
        if (y >= top && y < top + 16 * k_col_rows[slot]) n++;
    }
    return n;
}
static int bg_cols_on_line_v(int y, int drop, int clip) {
    return plane_cols_on_line_v(0, BG_SKY_SPRITE, BG_SKY_COUNT, y, drop, clip) + plane_cols_on_line_v(1, BG_FAR_SPRITE, BG_FAR_COUNT, y, drop, clip) +
           plane_cols_on_line_v(2, BG_MIDA_SPRITE, BG_MIDA_COUNT, y, drop, clip) + plane_cols_on_line_v(3, BG_MIDB_SPRITE, BG_MIDB_COUNT, y, drop, clip);
}
/* What Gum Trip really draws: the planes outside BG_TRIP_HIDDEN_MASK (the same mask src/bg.c hides with bg_trip_planes). */
static int bg_cols_on_line(int y) { return bg_cols_on_line_v(y, (int)BG_TRIP_HIDDEN_MASK, 0); }
static int bg_cols_on_line_all(int y) { return bg_cols_on_line_v(y, 0, 0); }

/* What-if: kill strip columns capped to `cap` rows (16 px each) next to the window instead of TRIP_VIEW_STRIP_MAX_ROWS. */
static int strip_cols_capped(const TripGen *g, uint32_t scroll, int y, int cap) {
    uint32_t base = scroll & ~15u;
    int k, s, n = 0;
    for (k = 0; k < TRIP_VIEW_STRIP_COLS; k++) {
        uint32_t wx = base + ((uint32_t)k << 4);
        if (wx + 16 <= scroll || wx >= scroll + TRIP_VIEW_SCREEN_W) continue;
        for (s = 0; s < g->count; s++) {
            int idx = g->head + s;
            const TripChunk *c;
            if (idx >= TRIP_GEN_RING) idx -= TRIP_GEN_RING;
            c = &g->ring[idx];
            if (wx + 16 > c->wx && wx < c->wx + TRIP_CHUNK_PX) {
                if (y < c->win_top && y >= c->win_top - 16 * cap) n++;
                else if (y >= c->win_bottom && y < c->win_bottom + 16 * cap) n++;
            }
        }
    }
    return n;
}
#define WHATIFS 6
static const char *k_whatif_name[WHATIFS] = { "drop far plane", "drop mid A plane", "drop mid B plane", "far ends at 96 and mid A at 128 (fewer overlapping rows)", "strip capped to 8 rows", "strip capped to 4 rows" };
/* Fliers: the hero and each rival draw SOOT_COLUMNS sprites (pool objects set exactly SOOT_COLUMNS in the chain, src/main.c). Their
 * height is at most 3 rows and they can be on any line, so the worst case counts them on every line. */
#define HERO_COLS SOOTLING_MAX_COLUMNS
#define RIVAL_COLS (TRIP_RIVAL_MAX * SOOTLING_MAX_COLUMNS)

static void sweep(void) {
    int whatif_worst[WHATIFS] = {0}, whatif_y[WHATIFS] = {0};
    int worst_untrimmed = 0, worst_untrimmed_y = 0;
    int worst_total = 0, worst_total_y = 0, worst_bg = 0, worst_rim_total = 0;
    uint32_t worst_seed = 0, worst_scroll = 0;
    TripViewLine worst_r = {0};
    Max mpl = {0}, mh = {0}, mp = {0}, mi = {0}, ms = {0}, mr = {0}, mt = {0}, mtr = {0};
    uint32_t seed;
    for (seed = 1; seed <= SEEDS; seed++) {
        TripGen g;
        uint32_t scroll;
        tripgen_init(&g, seed);
        for (scroll = 0; scroll <= SCROLL_END; scroll += SCROLL_STEP) {
            uint32_t steps = (scroll >> 1) + seed;
            int y;
            cover(&g, scroll);
            for (y = 0; y < TRIP_GEN_WORLD_H; y++) {
                TripViewLine r = trip_view_line_sprites(&g, scroll, steps, y);
                upd(&mpl, bg_cols_on_line(y), seed, scroll, y, r);
                upd(&mh, r.haz, seed, scroll, y, r);
                upd(&mp, r.pickup, seed, scroll, y, r);
                upd(&mi, r.island, seed, scroll, y, r);
                upd(&ms, r.strip, seed, scroll, y, r);
                upd(&mr, r.strip_rim, seed, scroll, y, r);
                upd(&mt, r.sum, seed, scroll, y, r);
                upd(&mtr, r.sum_rim, seed, scroll, y, r);
                {   /* hero and rival columns on every line (they can be anywhere), planes by their real row range per column */
                    int extra = HERO_COLS + bg_cols_on_line(y) + RIVAL_COLS;
                    if (r.sum + extra > 90) {   /* what-ifs only lower a count, so lines at or under 90 stay under 90 */
                        int w, fixed = HERO_COLS + RIVAL_COLS + r.haz + r.pickup + r.island;
                        int v[WHATIFS];
                        v[0] = fixed + r.strip + bg_cols_on_line_v(y, 2 | (int)BG_TRIP_HIDDEN_MASK, 0);
                        v[1] = fixed + r.strip + bg_cols_on_line_v(y, 4 | (int)BG_TRIP_HIDDEN_MASK, 0);
                        v[2] = fixed + r.strip + bg_cols_on_line_v(y, 8 | (int)BG_TRIP_HIDDEN_MASK, 0);
                        v[3] = fixed + r.strip + bg_cols_on_line_v(y, (int)BG_TRIP_HIDDEN_MASK, 1);
                        v[4] = fixed + strip_cols_capped(&g, scroll, y, 8) + bg_cols_on_line(y);
                        v[5] = fixed + strip_cols_capped(&g, scroll, y, 4) + bg_cols_on_line(y);
                        for (w = 0; w < WHATIFS; w++) if (v[w] > whatif_worst[w]) { whatif_worst[w] = v[w]; whatif_y[w] = y; }
                    }
                    if (r.sum + extra > worst_total) { worst_total = r.sum + extra; worst_total_y = y; worst_seed = seed; worst_scroll = scroll; worst_r = r; worst_bg = bg_cols_on_line(y); }
                    if (r.sum + extra - bg_cols_on_line(y) + bg_cols_on_line_all(y) > worst_untrimmed) { worst_untrimmed = r.sum + extra - bg_cols_on_line(y) + bg_cols_on_line_all(y); worst_untrimmed_y = y; }
                    if (r.sum_rim + extra > worst_rim_total) worst_rim_total = r.sum_rim + extra;
                }
            }
        }
        CHECK(g.overflow == 0);
    }
    printf("MAX planes alone %d at line %d (sky+far+midA+midB; near plane hidden)\n", mpl.v, mpl.y);
    printf("MAX hazards    %d  seed %u scroll %u line %d\n", mh.v, (unsigned)mh.seed, (unsigned)mh.scroll, mh.y);
    printf("MAX pickups    %d  seed %u scroll %u line %d\n", mp.v, (unsigned)mp.seed, (unsigned)mp.scroll, mp.y);
    printf("MAX islands    %d  seed %u scroll %u line %d\n", mi.v, (unsigned)mi.seed, (unsigned)mi.scroll, mi.y);
    printf("MAX strip full %d  seed %u scroll %u line %d\n", ms.v, (unsigned)ms.seed, (unsigned)ms.scroll, ms.y);
    printf("MAX strip rim  %d  seed %u scroll %u line %d\n", mr.v, (unsigned)mr.seed, (unsigned)mr.scroll, mr.y);
    printf("MAX SUM full strip %d  seed %u scroll %u line %d\n", mt.v, (unsigned)mt.seed, (unsigned)mt.scroll, mt.y);
    printf("MAX SUM rim strip  %d  seed %u scroll %u line %d\n", mtr.v, (unsigned)mtr.seed, (unsigned)mtr.scroll, mtr.y);
    printf("split full: haz %d pick %d isl %d strip %d\n", mt.r.haz, mt.r.pickup, mt.r.island, mt.r.strip);
    printf("split rim:  haz %d pick %d isl %d strip_rim %d\n", mtr.r.haz, mtr.r.pickup, mtr.r.island, mtr.r.strip_rim);
    printf("(hazards+pickups+islands+strip only; hero, rivals and background not included; plan limits 96 hardware, 90 SB_LIMIT)\n");
    printf("WORST LINE TOTAL %d (full strip) / %d (rim strip) at line %d seed %u scroll %u: hazards %d pickups %d islands %d strip %d + hero %d + planes %d + rivals %d (%d x %d); limit 96 hardware, 90 SB_LIMIT\n",
           worst_total, worst_rim_total, worst_total_y, (unsigned)worst_seed, (unsigned)worst_scroll, worst_r.haz, worst_r.pickup, worst_r.island, worst_r.strip, HERO_COLS, worst_bg, RIVAL_COLS, TRIP_RIVAL_MAX, SOOTLING_MAX_COLUMNS);
    printf("WITH FAR PLANE (not drawn in trip) worst line %d at line %d\n", worst_untrimmed, worst_untrimmed_y);
    printf("TRIP worst line %d at line %d (full strip), %d (rim strip); SB_LIMIT %d\n", worst_total, worst_total_y, worst_rim_total, SB_LIMIT);
    CHECK(worst_total <= SB_LIMIT);
    CHECK(worst_rim_total <= SB_LIMIT);
    {   int w;
        for (w = 0; w < WHATIFS; w++)
            printf("WHATIF %s: worst line %s%d (line %d)\n", k_whatif_name[w], whatif_worst[w] ? "" : "<= 90, ", whatif_worst[w], whatif_y[w]);
    }
    /* Certain bounds only: generator budgets */
    CHECK(mh.v <= TRIP_GEN_RING * TRIP_GEN_MAX_HAZ * 3);
    CHECK(mp.v <= TRIP_GEN_RING * TRIP_VIEW_PICKUP_COLS);
    CHECK(ms.v <= TRIP_VIEW_STRIP_COLS);
    CHECK(mr.v <= ms.v);
    CHECK(mtr.v <= mt.v);
}

int main(void) {
    meter_tests();
    haz_y_tests();
    sweep();
    printf("%s: %d checks, %d failures\n", failures ? "FAIL" : "PASS", checks, failures);
    return failures ? 1 : 0;
}
