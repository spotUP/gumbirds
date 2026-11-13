/* Host test for the arcade stage islands: wider air between them (user report "the islands are too close", 2026-11-13).
 * Every arcade stage: the narrowest passage a flier must fly through (horizontal between islands whose heights meet, vertical between islands whose
 * widths meet, the arena seam counted) is at least the old narrowest + ARC_GAP_MORE; islands stay inside the 384 arena, above the hazard strip,
 * apart from each other and from flippers, the grate and the grabber range; vents stand on an island top; rival spawns stand on an island top. */
#include <stdio.h>
#include "../../src/core/stage.h"
#include "../../src/core/arcade.h"
#include "../../src/core/arc_elements.h"

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

#define ARC_GAP_MORE 16
#define ISLAND_X_MIN 0
#define ISLAND_Y_MIN 40     /* the lowest island top on the old data is 42 */
#define ISLAND_BOTTOM_MAX 176 /* the old ground island bottom (164 + 12); the water and hazard strip start below */
#define PASS_H 11           /* flier box height with balloons */
#define PASS_W 8            /* island columns closer than this count as stacked */
static const int old_narrowest[12] = { 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24 }; /* measured on the pre-2026-11-13 data: the seam gap between island 0 and island 1 */

static int sep(int a0, int a1, int b0, int b1) { int u = b0 - a1, v = a0 - b1; return u > v ? u : v; }

static int box_hit(int ax0, int ay0, int ax1, int ay1, int bx0, int by0, int bx1, int by1) { return ax0 < bx1 && bx0 < ax1 && ay0 < by1 && by0 < ay1; }

static int narrowest(void) {
    int best = 1000;
    for (int i = 0; i < STAGE_PLATFORM_COUNT; i++) for (int j = i + 1; j < STAGE_PLATFORM_COUNT; j++) {
        const StagePlatform *a = &stage_platforms[i], *b = &stage_platforms[j];
        if (!a->w || !b->w) continue;
        for (int sh = -384; sh <= 384; sh += 384) {
            int hs = sep(a->x, a->x + a->w, b->x + sh, b->x + sh + b->w), vs = sep(a->y, a->y + STAGE_PLATFORM_H, b->y, b->y + STAGE_PLATFORM_H);
            if (vs < PASS_H && hs > 0 && hs < best) best = hs;
            if (hs < PASS_W && vs > 0 && vs < best) best = vs;
            if (hs <= 0 && vs <= 0) best = -1;
        }
    }
    return best;
}

static void test_stage(int st) {
    ArcElements el;
    int n = 0;
    stage_select(arc_stage_layout(st));
    arc_elements_init(&el, st - 1);
    for (int i = 0; i < STAGE_PLATFORM_COUNT; i++) {
        const StagePlatform *p = &stage_platforms[i];
        if (!p->w) continue;
        n++;
        CHECK(p->x >= ISLAND_X_MIN && p->x + p->w <= 384 && p->y >= ISLAND_Y_MIN && p->y + STAGE_PLATFORM_H <= ISLAND_BOTTOM_MAX);
    }
    int g = narrowest();
    printf("stage %d: %d islands, narrowest passage %d (was %d)\n", st, n, g, old_narrowest[st - 1]);
    CHECK(g >= old_narrowest[st - 1] + ARC_GAP_MORE);
    for (int e = 0; e < el.n; e++) {
        const ArcElement *x = &el.el[e];
        int on_top = 0;
        for (int i = 0; i < STAGE_PLATFORM_COUNT; i++) {
            const StagePlatform *p = &stage_platforms[i];
            if (!p->w) continue;
            if (x->kind == ARC_EL_VENT && x->x >= p->x && x->x <= p->x + p->w && x->y == p->y) on_top = 1;
            int hit = 0;
            if (x->kind == ARC_EL_FLIPPER) hit = box_hit(x->x - ARC_FLIP_HALF, x->y - ARC_FLIP_HALF, x->x + ARC_FLIP_HALF, x->y + ARC_FLIP_HALF, p->x, p->y, p->x + p->w, p->y + STAGE_PLATFORM_H);
            if (x->kind == ARC_EL_GRATE) hit = box_hit(x->x - ARC_GRATE_HALF_W, x->y - ARC_GRATE_H, x->x + ARC_GRATE_HALF_W, x->y, p->x, p->y, p->x + p->w, p->y + STAGE_PLATFORM_H);
            if (x->kind == ARC_EL_GRABBER) hit = box_hit(x->x0 - ARC_GRAB_HALF_W, x->y - ARC_GRAB_HIT_H - 6, x->param + ARC_GRAB_HALF_W, x->y, p->x, p->y, p->x + p->w, p->y + STAGE_PLATFORM_H);
            CHECK(!hit);
        }
        if (x->kind == ARC_EL_VENT) CHECK(on_top);
    }
    for (int k = 0; k < stage_rival_count(); k++) {
        int ok = 0;
        for (int i = 0; i < STAGE_PLATFORM_COUNT; i++) {
            const StagePlatform *p = &stage_platforms[i];
            if (p->w && stage_spawns[k].x >= p->x && stage_spawns[k].x <= p->x + p->w && stage_spawns[k].y == p->y - 6) ok = 1;
        }
        CHECK(ok);
    }
}

int main(void) {
    for (int st = 1; st <= ARC_STAGE_COUNT; st++) test_stage(st);
    stage_select(0);
    printf("%d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
