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
    arc_view_build(&a, 0, s);
    CHECK(s[0].frame >= 1 && s[0].frame <= 3);
    a.el[0].timer = ARC_VENT_LAUNCH;
    CHECK(arc_view_build(&a, 0, s) == 2); /* body in launch frame, one spark above it */
    CHECK(s[0].frame == 4 && s[1].piece == ARCV_SPARK && s[1].y < s[0].y + ARC_VIEW_H[ARCV_BODY]);
    a.el[0].timer = ARC_VENT_LAUNCH + ARC_VENT_BURST_TICKS;
    CHECK(arc_view_build(&a, 0, s) == 1 && s[0].frame == 0); /* burst over */
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

int main(void) {
    test_vent(); test_others(); test_grab_frame(); test_empty();
    printf("%d checks, %d failures\n", checks, failures);
    return failures != 0;
}
