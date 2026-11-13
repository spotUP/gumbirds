/* ATTRACT-DEMOS2: the attract overlay core (src/core/attract_overlay.c) and its feed from the flow (Flow.demo_in, Flow.ov).
 * The overlay shows FLAP while the demo presses A, otherwise STEER with the lever on the sweep direction; a state is held for at
 * least ATTRACT_HOLD_FRAMES frames so the word and icons do not flicker. */
#include <stdio.h>
#include <string.h>
#include "../../src/core/flow.h"
#include "../../src/core/attract_overlay.h"

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; if (failures <= 10) printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

static void test_hold(void)
{
    AttractOverlay o;
    int i, run;
    attract_overlay_reset(&o);
    CHECK(o.key == AO_NONE);
    attract_overlay_step(&o, IN_RIGHT);
    CHECK(o.key == AO_STEER_RIGHT);
    attract_overlay_step(&o, IN_A | IN_RIGHT);               /* A one frame after the state began: held, no switch yet */
    CHECK(o.key == AO_STEER_RIGHT);
    for (i = 2; i < ATTRACT_HOLD_FRAMES; i++) attract_overlay_step(&o, IN_A | IN_RIGHT);
    CHECK(o.key == AO_STEER_RIGHT);                            /* frame HOLD - 1: still the first state */
    attract_overlay_step(&o, IN_RIGHT);                        /* frame HOLD: switch allowed, wants STEER_RIGHT: stays */
    CHECK(o.key == AO_STEER_RIGHT);
    attract_overlay_step(&o, IN_A | IN_RIGHT);
    CHECK(o.key == AO_FLAP);
    /* the state lasts exactly HOLD frames under a flickering input, every time */
    for (run = 0; run < 3; run++) {
        int len = 0;
        uint8_t want = (uint8_t)(run & 1 ? IN_A : IN_LEFT);
        while (o.key == (run & 1 ? AO_STEER_LEFT : AO_FLAP) && len < 1000) { attract_overlay_step(&o, want); len++; }
        CHECK(len == ATTRACT_HOLD_FRAMES);
    }
}

static void test_steer_direction(void)
{
    AttractOverlay o;
    int i;
    attract_overlay_reset(&o);
    attract_overlay_step(&o, IN_LEFT);
    CHECK(o.key == AO_STEER_LEFT);
    for (i = 0; i < ATTRACT_HOLD_FRAMES; i++) attract_overlay_step(&o, IN_RIGHT);
    CHECK(o.key == AO_STEER_RIGHT);
}

/* In the demo the flow records the input it fed the game and steps the overlay with it. */
static void test_flow_feed(void)
{
    Flow f;
    uint32_t fr;
    int demo_frames = 0, flaps = 0, steers = 0, mismatch = 0;
    memset(&f, 0, sizeof f);
    flow_init(&f, NULL, 0);
    for (fr = 1; fr < 20000u && demo_frames < 900; fr++) {
        flow_step(&f, 0, 0, fr);
        if (f.state != FLOW_ATTRACT_DEMO) continue;
        demo_frames++;
        if (demo_frames == 1) { CHECK(f.ov.key == AO_NONE); continue; }   /* the entering frame has not stepped the demo yet */
        CHECK(((f.demo_in & IN_LEFT) != 0) != ((f.demo_in & IN_RIGHT) != 0));   /* the pilot always sweeps one way */
        if (f.ov.key == AO_FLAP) flaps++; else steers++;
        if (f.ov.key == AO_NONE) mismatch++;
    }
    CHECK(demo_frames > 800 && mismatch == 0);
    CHECK(flaps > 0 && steers > 0);                             /* both words appear in one demo */
}

int main(void)
{
    test_hold();
    test_steer_direction();
    test_flow_feed();
    printf("test_attract_overlay: %d checks, %d failures\n", checks, failures);
    return failures != 0;
}
