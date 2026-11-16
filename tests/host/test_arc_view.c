/* Host test for src/core/arc_view.[ch]: which piece, frame and position each arcade stage element is drawn with. */
#include <stdio.h>
#include <string.h>
#include "../../src/core/arc_view.h"

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

static ArcElements one(int kind, int x, int y) {
    ArcElements a;
    memset(&a, 0, sizeof a);
    a.n = 1; a.el[0].kind = (uint8_t)kind; a.el[0].x = (int16_t)x; a.el[0].y = (int16_t)y;
    if (kind == ARC_EL_GRABBER) { a.el[0].x0 = (int16_t)x; a.el[0].param = (int16_t)(x + 100); }
    return a;
}

static void test_vent(void) {
    ArcSprite s[ARC_VIEW_MAX];
    ArcElements a = one(ARC_EL_VENT, 100, 80);
    CHECK(arc_view_build(&a, 0, s) == 1);
    CHECK(s[0].piece == ARCV_BODY && s[0].frame == 0 && s[0].x == 100 - ARC_VIEW_W[ARCV_BODY] / 2 && s[0].y == 80 - ARC_VIEW_H[ARCV_BODY]);
    a.el[0].timer = ARC_VENT_LOOP / 2 - 24; /* telegraph */
    CHECK(arc_view_build(&a, 0, s) == 1 && s[0].piece == ARCV_WARN && s[0].frame == 0); /* one sprite: the body with boil bubbles on its top */
    CHECK(s[0].x == 100 - ARC_VIEW_W[ARCV_BODY] / 2 && s[0].y + ARC_VIEW_H[ARCV_WARN] == 80 && ARC_VIEW_W[ARCV_WARN] == ARC_VIEW_W[ARCV_BODY]);
    CHECK(arc_view_heat(&a) == 1);
    CHECK(ARC_VENT_LAUNCH - ARC_VENT_TELEGRAPH == 72); /* the shake, boil and heat tables cover exactly the window rivals steer by */
    a.el[0].timer = ARC_VENT_TELEGRAPH - 1;
    CHECK(arc_view_build(&a, 0, s) == 1 && arc_view_heat(&a) == 0); /* no warning before the window rivals steer by */
    a.el[0].timer = ARC_VENT_LAUNCH - 1; /* last warning tick: violent shake (-2,-1), last boil hold (16 % 10), flicker step */
    CHECK(arc_view_build(&a, 0, s) == 1 && s[0].piece == ARCV_WARN && s[0].x == 100 - ARC_VIEW_W[ARCV_BODY] / 2 - 2 && s[0].y == 80 - ARC_VIEW_H[ARCV_WARN] - 1);
    CHECK(s[0].frame == 18 && arc_view_heat(&a) == 6); /* body frame 3 with boil grid 6: the last of the 19 warning frames */
    { /* tables vs the step lists they were generated from (old loop and modulo, old step_at walk) */
        static const uint8_t bs[] = { 0, 6, 12, 18, 23, 28, 33, 38, 42, 46, 50, 54, 57, 60, 63, 66, 69 };
        static const uint8_t ha[][2] = { {0,1},{14,2},{26,3},{36,4},{45,5},{53,6},{60,7},{66,6},{68,7},{70,6} }, ca[][2] = { {0,7},{40,5},{50,3},{60,1},{70,0} };
        unsigned w, k, ok = 1;
        for (w = 0; w < 72 + 75; w++) {
            unsigned h = 0, bf, bi, wf, i, hv = ha[0][1], cv = ca[0][1];
            for (i = 1; i < 10; i++) if (w >= ha[i][0]) hv = ha[i][1];
            for (i = 1; i < 5; i++) if (w >= ca[i][0]) cv = ca[i][1];
            while (h + 1 < sizeof bs && w >= bs[h + 1]) h++;
            for (k = 0; k < 2; k++) { /* k 0: warning window, k 1: after the launch */
                ArcElements v; ArcSprite o[ARC_VIEW_MAX];
                memset(&v, 0, sizeof v);
                v.n = 1; v.el[0].kind = ARC_EL_VENT; v.el[0].x = 100; v.el[0].y = 80;
                if (k == 0 && w < 72) {
                    v.el[0].timer = (uint16_t)(ARC_VENT_TELEGRAPH + w);
                    bf = 1 + w / 24; bi = h % 10; /* old body frame and boil frame; the warning frames hold the pairs in the order they show */
                    wf = bf == 1 ? bi : bf == 2 ? bi + 1 : bi == 9 ? 11 : 12 + bi;
                    ok &= bf != 1 || bi <= 4; ok &= bf != 2 || bi >= 4; ok &= bf != 3 || bi <= 6 || bi == 9;
                    ok &= arc_view_build(&v, 0, o) == 1 && o[0].piece == ARCV_WARN && o[0].frame == wf && arc_view_heat(&v) == (int)hv;
                } else if (k == 1) {
                    v.el[0].timer = (uint16_t)(ARC_VENT_LAUNCH + w);
                    ok &= arc_view_heat(&v) == (int)cv;
                }
            }
        }
        CHECK(ok);
    }
    a.el[0].timer = ARC_VENT_LAUNCH;
    CHECK(arc_view_build(&a, 0, s) == 2); /* body in launch frame, one spark above it */
    CHECK(s[0].frame == 4 && s[1].piece == ARCV_SPARK && s[1].y < s[0].y + ARC_VIEW_H[ARCV_BODY]);
    CHECK(s[0].x == 100 - ARC_VIEW_W[ARCV_BODY] / 2 && arc_view_heat(&a) == 7); /* shake over, hottest */
    a.el[0].timer = ARC_VENT_LAUNCH + ARC_VENT_BURST_TICKS;
    CHECK(arc_view_build(&a, 0, s) == 1 && s[0].frame == 0); /* burst over */
    CHECK(arc_view_heat(&a) == 5);
    a.el[0].timer = ARC_VENT_LAUNCH + 70;
    CHECK(arc_view_heat(&a) == 0); /* cooled down */
}

static void test_others(void) {
    ArcSprite s[ARC_VIEW_MAX];
    ArcElements f = one(ARC_EL_FLIPPER, 148, 72), g = one(ARC_EL_GRABBER, 104, 188), h = one(ARC_EL_GRATE, 248, 186);
    CHECK(arc_view_build(&f, 0, s) == 1 && s[0].piece == ARCV_FLIPPER && s[0].x == 148 - ARC_VIEW_W[ARCV_FLIPPER] / 2 && s[0].y == 72 - ARC_VIEW_H[ARCV_FLIPPER] / 2);
    CHECK(arc_view_build(&f, 4, s) == 1 && s[0].frame == 1); /* flipper turns one frame per ARC_VIEW_FLIP_TICKS */
    CHECK(arc_view_build(&g, 0, s) == 0); /* hidden (timer 0) */
    g.el[0].timer = 40; /* inside the grab frames */
    CHECK(arc_view_build(&g, 0, s) == 1 && s[0].piece == ARCV_GRABBER && s[0].frame < ARC_GRAB_FRAMES && s[0].y == 188 - ARC_VIEW_H[ARCV_GRABBER]);
    CHECK(arc_view_build(&h, 0, s) == 1 && s[0].piece == ARCV_HATCH && s[0].x == 248 - ARC_VIEW_W[ARCV_HATCH] / 2 && s[0].y == 186);
}

static void test_grab_frame(void) {
    CHECK(arc_elements_grab_frame(0) == -1 && arc_elements_grab_frame(1) == 0);
}

static void test_empty(void) {
    ArcSprite s[ARC_VIEW_MAX];
    ArcElements a;
    memset(&a, 0, sizeof a);
    CHECK(arc_view_build(&a, 0, s) == 0);
    CHECK(arc_view_line(s, 0, 100) == 0);
}

/* Invisible-kill guard: every tick the plume kills, the spark (not the body) must overlap the kill box by at least half its height. */
static void test_vent_kill_visible(void) {
    ArcElements a = one(ARC_EL_VENT, 100, 80);
    unsigned t;
    for (t = ARC_VENT_LAUNCH; t < ARC_VENT_LAUNCH + ARC_VENT_BURST_TICKS; t++) {
        ArcSprite s[ARC_VIEW_MAX];
        int n, i, best = 0, top = 80 - ARC_VENT_PLUME_H, bot = 80;
        a.el[0].timer = (uint16_t)t;
        CHECK(arc_elements_kill(&a, 100, 80 - ARC_VENT_PLUME_H / 2, 1, 1));
        n = arc_view_build(&a, 0, s);
        for (i = 0; i < n; i++) {
            int y0, y1, ov;
            if (s[i].piece != ARCV_SPARK) continue;
            y0 = s[i].y > top ? s[i].y : top; y1 = s[i].y + ARC_VIEW_H[ARCV_SPARK] < bot ? s[i].y + ARC_VIEW_H[ARCV_SPARK] : bot;
            ov = y1 - y0;
            if (s[i].x + ARC_VIEW_W[ARCV_SPARK] > 100 - ARC_VENT_HALF_W && s[i].x < 100 + ARC_VENT_HALF_W && ov > best) best = ov;
        }
        if (best < ARC_VIEW_H[ARCV_SPARK] / 2) printf("tick %u: spark overlap %d rows\n", t - ARC_VENT_LAUNCH, best);
        CHECK(best >= ARC_VIEW_H[ARCV_SPARK] / 2);
    }
}

int main(void) {
    test_vent(); test_vent_kill_visible(); test_others(); test_grab_frame(); test_empty();
    printf("%d checks, %d failures\n", checks, failures);
    return failures != 0;
}
