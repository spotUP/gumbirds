/* Host test for src/core/arc_elements.[ch]: element cycles, hit/miss boxes, flipper bounce, grate zone, per-stage tables. */
#include <stdio.h>
#include "../../src/core/arc_elements.h"

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

static int count(const ArcElements *a, int k) { int i, n = 0; for (i = 0; i < a->n; i++) n += a->el[i].kind == k; return n; }
static void run(ArcElements *a, int n) { while (n-- > 0) arc_elements_step(a); }

int main(void) {
    ArcElements a; int32_t vx, vy; int s, t;
    /* Source: gen3.py. Per stage in order: kind, x, y, drain right end (grabber only; its left end is x). */
    static const struct { int kind, x, y, x1; } pos[12][ARC_ELEM_MAX] = {
        {{ARC_EL_VENT,184,108,0}},
        {{ARC_EL_VENT,160,116,0},{ARC_EL_VENT,246,80,0}},
        {{ARC_EL_VENT,196,92,0},{ARC_EL_VENT,60,52,0}},
        {{ARC_EL_VENT,322,72,0},{ARC_EL_VENT,168,52,0},{ARC_EL_GRABBER,112,188,224},{ARC_EL_GRATE,232,186,0}},
        {{ARC_EL_VENT,204,88,0},{ARC_EL_VENT,306,72,0},{ARC_EL_GRATE,248,186,0}},
        {{ARC_EL_VENT,110,100,0},{ARC_EL_VENT,296,60,0}},
        {{ARC_EL_VENT,180,104,0},{ARC_EL_VENT,252,80,0},{ARC_EL_FLIPPER,148,72,0},{ARC_EL_GRABBER,104,188,256}},
        {{ARC_EL_VENT,174,124,0},{ARC_EL_VENT,300,80,0},{ARC_EL_FLIPPER,176,76,0}},
        {{ARC_EL_VENT,224,76,0},{ARC_EL_VENT,314,72,0},{ARC_EL_GRATE,248,186,0},{ARC_EL_FLIPPER,252,122,0},{ARC_EL_FLIPPER,96,92,0}},
        {{ARC_EL_VENT,160,108,0},{ARC_EL_VENT,320,72,0},{ARC_EL_FLIPPER,36,84,0},{ARC_EL_FLIPPER,176,50,0},{ARC_EL_FLIPPER,252,110,0}},
        {{ARC_EL_VENT,144,136,0},{ARC_EL_VENT,222,112,0},{ARC_EL_FLIPPER,280,56,0}},
        {{ARC_EL_VENT,40,96,0},{ARC_EL_VENT,320,80,0}} };
    static const int want_n[12] = { 1,2,2,4,3,2,4,3,5,5,3,2 };
    for (s = 0; s < 12; s++) {
        int i;
        arc_elements_init(&a, s);
        CHECK(a.n == want_n[s]);
        for (i = 0; i < a.n && i < 4; i++) {
            CHECK(a.el[i].kind == pos[s][i].kind); CHECK(a.el[i].x == pos[s][i].x); CHECK(a.el[i].y == pos[s][i].y);
            if (pos[s][i].kind == ARC_EL_GRABBER) CHECK(a.el[i].x0 == pos[s][i].x && a.el[i].param == pos[s][i].x1);
        }
    }
    (void)count;
    arc_elements_init(&a, 12); CHECK(a.n == 0);

    /* vent (R01: x 184, top 108): harmless idle and telegraph, hurts from launch for the burst, only inside the plume */
    arc_elements_init(&a, 0);
    CHECK(!arc_elements_kill(&a, 184, 90, 2, 5));
    run(&a, ARC_VENT_LAUNCH - 1); CHECK(!arc_elements_kill(&a, 184, 100, 2, 5));
    run(&a, 1); CHECK(arc_elements_kill(&a, 184, 100, 2, 5));
    CHECK(!arc_elements_kill(&a, 184 + ARC_VENT_HALF_W + 2 + 1, 100, 2, 5));   /* beside */
    CHECK(!arc_elements_kill(&a, 184, 108 - ARC_VENT_PLUME_H - 5 - 1, 2, 5));  /* above */
    run(&a, ARC_VENT_BURST_TICKS - 1); CHECK(arc_elements_kill(&a, 184, 100, 2, 5));
    run(&a, 1); CHECK(!arc_elements_kill(&a, 184, 100, 2, 5));
    run(&a, ARC_VENT_LOOP - ARC_VENT_LAUNCH - ARC_VENT_BURST_TICKS + ARC_VENT_LAUNCH); CHECK(arc_elements_kill(&a, 184, 100, 2, 5)); /* next loop */

    /* flipper (R10 first: 36,84): bounce away, sign reversal on each axis, miss outside */
    arc_elements_init(&a, 9);
    CHECK(arc_elements_bounce(&a, 30, 80, 2, 5, &vx, &vy) && vx < 0 && vy < 0);
    CHECK(arc_elements_bounce(&a, 40, 90, 2, 5, &vx, &vy) && vx > 0 && vy > 0);
    vx = 7; vy = 9; CHECK(!arc_elements_bounce(&a, 36 + ARC_FLIP_HALF + 2 + 1, 84, 2, 5, &vx, &vy) && vx == 7 && vy == 9);
    CHECK(!arc_elements_bounce(&a, 100, 140, 2, 5, &vx, &vy));

    /* grabber (N03: range 112..224, water 188): hidden and patrolling without a target, rises only for a low flier at its x */
    {
        ArcElement *h; int x0, k, sum = 0;
        static const int ticks[ARC_GRAB_FRAMES] = { 7, 6, 4, 4, 8, 3, 4, 13, 5, 5, 5, 7 };
        for (k = 0; k < ARC_GRAB_FRAMES; k++) sum += ticks[k];
        CHECK(sum == ARC_GRAB_LOOP);
        for (k = 0, t = 0; k < 5; k++) t += ticks[k];
        CHECK(t == ARC_GRAB_RISE && ARC_GRAB_SINK_AT == 1 + ARC_GRAB_RISE + 3 + 4 + 13);
        arc_elements_init(&a, 3); h = &a.el[2];
        for (t = 0; t < 4000; t++) {   /* no flier: never rises, never hurts, patrols 1 px a tick inside its range */
            int px = h->x;
            arc_elements_step(&a);
            CHECK(h->timer == 0 && h->x >= 112 && h->x <= 224 && (h->x == px + ARC_GRAB_PATROL || h->x == 112));
            CHECK(!arc_elements_kill(&a, h->x, 160, 2, 5));
        }
        x0 = h->x;
        arc_elements_note_low(&a, h->x, 100); arc_elements_step(&a); CHECK(h->timer == 0);              /* high flier: no rise */
        arc_elements_note_low(&a, h->x + 40, 170); arc_elements_step(&a); CHECK(h->timer == 0);         /* low but elsewhere */
        arc_elements_note_low(&a, h->x, 188 - ARC_GRAB_LOW_DY - 1); arc_elements_step(&a); CHECK(h->timer == 0); /* 1 px above the trigger height: no rise */
        (void)x0;
        arc_elements_note_low(&a, h->x + ARC_GRAB_TRIG_DX + 2, 170); arc_elements_step(&a); CHECK(h->timer == 0); /* just outside the trigger */
        arc_elements_note_low(&a, h->x + 1 + 0, 170); arc_elements_step(&a); CHECK(h->timer == 1 && h->cycle == 1);   /* low at its x: rises */
        /* target stays low the whole rise: the hand closes in frames 5..7 (timer 30..49), then sinks, then hides */
        for (t = 0; t < ARC_GRAB_RISE; t++) { arc_elements_note_low(&a, h->x, 170); arc_elements_step(&a); }
        CHECK(h->timer == ARC_GRAB_RISE + 1 && arc_elements_grab_frame(h->timer) == 5 && arc_elements_kill(&a, h->x, 160, 2, 5));
        CHECK(!arc_elements_kill(&a, h->x + ARC_GRAB_HALF_W + 3, 160, 2, 5));
        run(&a, 19); CHECK(h->timer == ARC_GRAB_SINK_AT - 1 && arc_elements_kill(&a, h->x, 160, 2, 5));
        run(&a, 1); CHECK(h->timer == ARC_GRAB_SINK_AT && !arc_elements_kill(&a, h->x, 160, 2, 5));   /* sink */
        run(&a, ARC_GRAB_LOOP - ARC_GRAB_SINK_AT + 1); CHECK(h->timer == 0);
        /* the target leaves while the hand rises: it retreats at once, even on the last rise tick, and never closes */
        for (k = 1; k <= ARC_GRAB_RISE; k += 14) {
            int n;
            arc_elements_note_low(&a, h->x, 170); arc_elements_step(&a); CHECK(h->timer == 1);
            for (n = 1; n < k; n++) { arc_elements_note_low(&a, h->x, 170); arc_elements_step(&a); }
            arc_elements_step(&a);   /* nobody low */
            CHECK(h->timer == ARC_GRAB_SINK_AT + 1 && arc_elements_grab_frame(h->timer) == 8 && !arc_elements_kill(&a, h->x, 160, 2, 5));
            run(&a, ARC_GRAB_LOOP);
            CHECK(h->timer == 0);
        }
        /* a target that rises out of reach (high) counts as gone */
        arc_elements_note_low(&a, h->x, 170); arc_elements_step(&a);
        arc_elements_note_low(&a, h->x, 100); arc_elements_step(&a);
        CHECK(h->timer == ARC_GRAB_SINK_AT + 1);
        run(&a, ARC_GRAB_LOOP);
        /* follows the target x while rising, at most ARC_GRAB_FOLLOW a tick, and stays in its range */
        arc_elements_note_low(&a, h->x, 170); arc_elements_step(&a);
        { int tx = h->x + ARC_GRAB_TRIG_DX; for (k = 0; k < 4; k++) { int px = h->x; arc_elements_note_low(&a, tx, 170); arc_elements_step(&a); CHECK(h->x - px <= ARC_GRAB_FOLLOW && h->x <= tx); } CHECK(h->x == tx && h->timer == 5); }
        run(&a, ARC_GRAB_LOOP);
        h->x = 224; h->timer = 0;
        arc_elements_note_low(&a, 224, 170); arc_elements_step(&a);   /* patrol wrapped to 112 first, so no flier there: stays hidden */
        CHECK(h->x == 112 && h->timer == 0);
    }

    /* rival steering: vent in its telegraph and burst only, grabber hand near a low flier; R01 vent x 184, top 108 */
    arc_elements_init(&a, 0);
    a.el[0].timer = ARC_VENT_TELEGRAPH - 1; CHECK(arc_elements_avoid_dir(&a, 184 - 15, 100, 2, 5, 0) == 0);
    a.el[0].timer = ARC_VENT_TELEGRAPH;     CHECK(arc_elements_avoid_dir(&a, 184 - 15, 100, 2, 5, 0) == -1);
    a.el[0].timer = ARC_VENT_LAUNCH + ARC_VENT_BURST_TICKS - 1; CHECK(arc_elements_avoid_dir(&a, 184 - 15, 100, 2, 5, 0) == -1);
    a.el[0].timer = ARC_VENT_LAUNCH + ARC_VENT_BURST_TICKS;     CHECK(arc_elements_avoid_dir(&a, 184 - 15, 100, 2, 5, 0) == 0);
    a.el[0].timer = ARC_VENT_LAUNCH;
    CHECK(arc_elements_avoid_dir(&a, 184 + 15, 100, 2, 5, 0) == 1 && arc_elements_avoid_dir(&a, 184, 100, 2, 5, 0) == 1);
    CHECK(arc_elements_avoid_dir(&a, 184 + ARC_VENT_HALF_W + 2 + ARC_AVOID_LOOK, 100, 2, 5, 0) == 1 && arc_elements_avoid_dir(&a, 184 + ARC_VENT_HALF_W + 2 + ARC_AVOID_LOOK + 1, 100, 2, 5, 0) == 0);
    CHECK(arc_elements_avoid_dir(&a, 184, 108 + 5 + ARC_AVOID_PAD + 1 + 24 + 40, 2, 5, 0) == 0);   /* far below */
    /* the side is judged ARC_AVOID_AHEAD ticks ahead: left of centre but crossing it fast keeps going right */
    CHECK(arc_elements_avoid_dir(&a, 184 - 4, 100, 2, 5, 0x10000) == 1 && arc_elements_avoid_dir(&a, 184 - 40, 100, 2, 5, 0x10000) == -1);
    arc_elements_init(&a, 3);   /* N03: hand at x 112, water 188 */
    CHECK(arc_elements_avoid_dir(&a, 120, 175, 2, 5, 0) == 1 && arc_elements_avoid_dir(&a, 105, 175, 2, 5, 0) == -1);
    CHECK(arc_elements_avoid_dir(&a, 120, 100, 2, 5, 0) == 0 && arc_elements_avoid_dir(&a, 112 + 40, 175, 2, 5, 0) == 0);

    /* grate (N06: x 248, hatch top 186): lift only inside the zone */
    arc_elements_init(&a, 4);
    CHECK(arc_elements_lift(&a, 248, 170, 2, 5) == -ARC_GRATE_LIFT);
    CHECK(arc_elements_lift(&a, 248 + ARC_GRATE_HALF_W + 2 + 1, 170, 2, 5) == 0);
    CHECK(arc_elements_lift(&a, 248, 186 - ARC_GRATE_H - 5 - 1, 2, 5) == 0);
    CHECK(arc_elements_lift(&a, 248, 170, 2, 5) < 0 && arc_elements_kill(&a, 248, 170, 2, 5) == 0);
    arc_elements_init(&a, 0); CHECK(arc_elements_lift(&a, 184, 100, 2, 5) == 0);

    printf("test_arc_elements: %d checks, %d failures\n", checks, failures);
    return failures != 0;
}
