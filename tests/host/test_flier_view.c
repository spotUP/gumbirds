/* flier_anim_step: clip choice, timing and mirroring, driven by the numbers the build generates from the art's
 * frames.json (build/gen/sootling_tables.h). Prints one FAIL line per miss and a final PASS/FAIL line. */
#include <stdio.h>
#include "../../src/core/flier_view.h"
#include "gen/sootling_tables.h"

static const uint8_t k_first[] = SOOTLING_TABLE_CLIP_FIRST;
static const uint8_t k_count[] = SOOTLING_TABLE_CLIP_COUNT;
static const uint8_t k_loop[] = SOOTLING_TABLE_CLIP_LOOP;
static const uint8_t k_ticks[] = SOOTLING_TABLE_FRAME_TICKS;
static const FlierClips clips = { k_first, k_count, k_loop, k_ticks,
    SOOTLING_CLIP_FLAP2, SOOTLING_CLIP_FLAP1, SOOTLING_CLIP_POP2, SOOTLING_CLIP_POP1,
    SOOTLING_CLIP_INFLATE, SOOTLING_CLIP_FALL, SOOTLING_CLIP_IDLE,
    { SOOTLING_CLIP_WALK0, SOOTLING_CLIP_WALK1, SOOTLING_CLIP_WALK2 },
    { SOOTLING_CLIP_LAND0, SOOTLING_CLIP_LAND1, SOOTLING_CLIP_LAND2 },
    { SOOTLING_CLIP_BREATHE0, SOOTLING_CLIP_BREATHE1, SOOTLING_CLIP_BREATHE2 } };

static int bad;
static void check(int ok, const char *what, int got, int want)
{
    if (!ok) { printf("FAIL %s: got %d, want %d\n", what, got, want); bad++; }
}

/* Plays n steps and returns the frame of the last one. */
static uint8_t run(FlierAnim *a, const Flier *f, int n, int *flip)
{
    uint8_t fr = 0;
    while (n-- > 0) fr = flier_anim_step(a, f, &clips, flip);
    return fr;
}

/* Frames a one shot clip shows in total, by ticks. */
static int clip_ticks(int clip)
{
    int t = 0, i;
    for (i = 0; i < k_count[clip]; i++) t += k_ticks[k_first[clip] + i];
    return t;
}


/* Ground clips for balloon count b: breathing, walking, landing, leaving the ground. All numbers come from the knob
 * macros and the generated tables. */
static void ground_tests(int b)
{
    static const int breathe_hold[4] = { FLIER_BREATHE_HOLD_0, FLIER_BREATHE_HOLD_1, FLIER_BREATHE_HOLD_2, FLIER_BREATHE_HOLD_3 };
    const int walk = clips.walk[b], land = clips.land[b], breathe = clips.breathe[b];
    const int air = b == 0 ? SOOTLING_CLIP_IDLE : (b == 1 ? SOOTLING_CLIP_FLAP1 : SOOTLING_CLIP_FLAP2);
    char what[64];
    Flier f;
    FlierAnim a;
    int flip, i, k, cycle;
    uint8_t fr;

    flier_init(&f, 0, 0, (uint8_t)b, 1);
    f.on_ground = 1;
    flier_anim_init(&a);
    if (b) run(&a, &f, clip_ticks(SOOTLING_CLIP_INFLATE), &flip);

    /* standing: breathing frames with their holds, then wraps */
    for (cycle = 0; cycle < 2; cycle++)
        for (k = 0; k < 4; k++)
            for (i = 0; i < breathe_hold[k]; i++) {
                fr = flier_anim_step(&a, &f, &clips, &flip);
                sprintf(what, "b%d breathe frame %d step %d", b, k, i);
                check(fr == k_first[breathe] + k, what, fr, k_first[breathe] + k);
            }
    check(k_count[breathe] == 4, "breathe has 4 frames", k_count[breathe], 4);

    /* walking: 8 frames x FLIER_WALK_HOLD per cycle, in order, wraps */
    f.vx = 91750; /* 1.4 px per frame */
    check(k_count[walk] == 8, "walk has 8 frames", k_count[walk], 8);
    for (cycle = 0; cycle < 2; cycle++)
        for (k = 0; k < k_count[walk]; k++)
            for (i = 0; i < FLIER_WALK_HOLD; i++) {
                fr = flier_anim_step(&a, &f, &clips, &flip);
                sprintf(what, "b%d walk frame %d step %d", b, k, i);
                check(fr == k_first[walk] + k, what, fr, k_first[walk] + k);
            }

    /* take-off switches the ground clip to the air clip */
    f.on_ground = 0;
    fr = flier_anim_step(&a, &f, &clips, &flip);
    sprintf(what, "b%d take-off shows the air clip", b);
    check(fr == k_first[air], what, fr, k_first[air]);

    /* landing while still: land frame 0 for FLIER_LAND_HOLD_0, frame 1 for FLIER_LAND_HOLD_1, then breathing */
    f.on_ground = 1; f.vx = 0; f.facing = 0;
    for (i = 0; i < FLIER_LAND_HOLD_0; i++) {
        fr = flier_anim_step(&a, &f, &clips, &flip);
        sprintf(what, "b%d land frame 0 step %d", b, i);
        check(fr == k_first[land], what, fr, k_first[land]);
        check(flip == 1, "landing mirrors when facing left", flip, 1);
    }
    for (i = 0; i < FLIER_LAND_HOLD_1; i++) {
        fr = flier_anim_step(&a, &f, &clips, &flip);
        sprintf(what, "b%d land frame 1 step %d", b, i);
        check(fr == k_first[land] + 1, what, fr, k_first[land] + 1);
    }
    fr = flier_anim_step(&a, &f, &clips, &flip);
    sprintf(what, "b%d breathing after landing", b);
    check(fr == k_first[breathe], what, fr, k_first[breathe]);

    /* landing while moving ends into walk */
    f.on_ground = 0; f.vx = 91750;
    flier_anim_step(&a, &f, &clips, &flip);
    f.on_ground = 1;
    run(&a, &f, FLIER_LAND_HOLD_0 + FLIER_LAND_HOLD_1, &flip);
    fr = flier_anim_step(&a, &f, &clips, &flip);
    sprintf(what, "b%d walk after landing while moving", b);
    check(fr == k_first[walk], what, fr, k_first[walk]);

    /* leaving the ground during a landing cuts it */
    f.on_ground = 0;
    flier_anim_step(&a, &f, &clips, &flip);
    f.on_ground = 1; f.vx = 0;
    run(&a, &f, 3, &flip);
    f.on_ground = 0;
    fr = flier_anim_step(&a, &f, &clips, &flip);
    sprintf(what, "b%d leaving the ground cuts the landing", b);
    check(fr == k_first[air], what, fr, k_first[air]);
}

/* Flap clip for balloon count b (2 or 1): rest frame between presses, one play per press, a press restarts. */
static void flap_tests(int b)
{
    const int clip = b == 2 ? SOOTLING_CLIP_FLAP2 : SOOTLING_CLIP_FLAP1;
    const int H = FLIER_FLAP_HOLD, N = k_count[clip], F0 = k_first[clip];
    char what[64];
    Flier f;
    FlierAnim a;
    int flip, i, k;
    uint8_t fr;

    flier_init(&f, 0, 0, (uint8_t)b, 1);
    f.on_ground = 0;
    flier_anim_init(&a);
    run(&a, &f, clip_ticks(SOOTLING_CLIP_INFLATE), &flip);

    /* A: no press, rest frame forever */
    for (i = 0; i < 200; i++) {
        fr = flier_anim_step(&a, &f, &clips, &flip);
        if (fr != F0) { check(0, "A: rest frame without a press", fr, F0); break; }
    }
    /* B: one press plays the clip once, N frames of H steps (the press step is the first of frame 0), then rests */
    f.flapped = 1;
    for (k = 0; k < N; k++)
        for (i = 0; i < H; i++) {
            fr = flier_anim_step(&a, &f, &clips, &flip);
            f.flapped = 0;
            sprintf(what, "B b%d frame %d step %d", b, k, i);
            check(fr == F0 + k, what, fr, F0 + k);
        }
    for (i = 0; i < 50; i++) {
        fr = flier_anim_step(&a, &f, &clips, &flip);
        if (fr != F0) { check(0, "B: rest after the play", fr, F0); break; }
    }
    /* C: a press inside frame 3 restarts at the first frame */
    f.flapped = 1;
    flier_anim_step(&a, &f, &clips, &flip);
    f.flapped = 0;
    run(&a, &f, 3 * H, &flip);
    f.flapped = 1;
    fr = flier_anim_step(&a, &f, &clips, &flip);
    f.flapped = 0;
    check(fr == F0, "C: restart shows the first frame", fr, F0);
    for (i = 0; i < H - 1; i++) {
        fr = flier_anim_step(&a, &f, &clips, &flip);
        check(fr == F0, "C: restart holds the first frame", fr, F0);
    }
    fr = flier_anim_step(&a, &f, &clips, &flip);
    check(fr == F0 + 1, "C: restart then advances", fr, F0 + 1);
    run(&a, &f, N * H, &flip);
    /* E: a flap press comes at best every FLIER_FLAP_COOLDOWN ticks, a play lasts N * H, so a fast tapper cuts the
     * wingbeat (default cut frame FLIER_FLAP_COOLDOWN / H = 4). Accepted by the user; judged by eye, no assert. */

    /* D: a press during a one shot is ignored, not latched */
    if (b == 2) {
        flier_init(&f, 0, 0, 2, 1);
        f.on_ground = 0;
        flier_anim_init(&a);
        run(&a, &f, clip_ticks(SOOTLING_CLIP_INFLATE), &flip);
        f.balloons = 1;
        f.flapped = 1;
        for (k = 0; k < k_count[SOOTLING_CLIP_POP2]; k++)
            for (i = 0; i < k_ticks[k_first[SOOTLING_CLIP_POP2] + k]; i++) {
                fr = flier_anim_step(&a, &f, &clips, &flip);
                sprintf(what, "D pop2 frame %d step %d", k, i);
                check(fr == k_first[SOOTLING_CLIP_POP2] + k, what, fr, k_first[SOOTLING_CLIP_POP2] + k);
            }
        f.flapped = 0;
        for (i = 0; i < 30; i++) {
            fr = flier_anim_step(&a, &f, &clips, &flip);
            if (fr != k_first[SOOTLING_CLIP_FLAP1]) { check(0, "D: rest frame after pop2", fr, k_first[SOOTLING_CLIP_FLAP1]); break; }
        }
    }
}

/* The pump draws the inflate clip by progress: first frame at 0, last at ARC_PUMP_STAGES - 1, never backwards or outside the clip. */
static void pump_frame_tests(void)
{
    int p, last = -1, fr;
    const int first = k_first[SOOTLING_CLIP_INFLATE], n = k_count[SOOTLING_CLIP_INFLATE];
    check(flier_pump_frame(&clips, 0) == first, "pump frame 0", flier_pump_frame(&clips, 0), first);
    check(flier_pump_frame(&clips, ARC_PUMP_STAGES - 1) == first + n - 1, "pump frame last", flier_pump_frame(&clips, ARC_PUMP_STAGES - 1), first + n - 1);
    for (p = 0; p <= ARC_PUMP_STAGES; p++) {
        fr = flier_pump_frame(&clips, p);
        check(fr >= last && fr >= first && fr < first + n, "pump frame monotonic in clip", fr, last);
        last = fr;
    }
}

int main(void)
{
    Flier f;
    FlierAnim a;
    int flip, i, t;
    uint8_t fr;

    /* sheet facts */
    /* spec numbers that follow the deliberate art change of 2026-11-11 (walk, landing and breathing clips added) */
    check(SOOTLING_FRAMES == 105, "frame count", SOOTLING_FRAMES, 105);
    check(SOOTLING_CLIP_COUNT == 16, "clip count", SOOTLING_CLIP_COUNT, 16);
    /* the pipeline pads art to whole 16 px tiles: 24 px art is still 2 strips (src/vram_layout.h SOOT_COLUMNS) */
    check(SOOTLING_ART_W == 24 && SOOTLING_ART_H == 32, "art size", SOOTLING_ART_W, 24);
    /* SOOTLING_MAX_COLUMNS lives in the ngdevkit-typed sprites header, not in the host-includable tables header: 17..32 px is exactly 2 strips */
    check(SOOTLING_ART_W > 16 && SOOTLING_ART_W <= 32, "art width is 2 strips (17..32 px)", SOOTLING_ART_W, 24);
    check(SOOTLING_BOX_LAST_COL - SOOTLING_BOX_FIRST_COL + 1 == 2 * FLIER_HALF_W, "hit box width",
          SOOTLING_BOX_LAST_COL - SOOTLING_BOX_FIRST_COL + 1, 2 * FLIER_HALF_W);
    check(SOOTLING_FEET_ROW == SOOTLING_ART_H - 1, "feet on last row", SOOTLING_FEET_ROW, SOOTLING_ART_H - 1);

    /* a flier first shown with 2 balloons plays inflate to its end, then flap2 */
    flier_init(&f, 0, 0, 2, 1);
    flier_anim_init(&a);
    fr = run(&a, &f, 1, &flip);
    check(fr == k_first[SOOTLING_CLIP_INFLATE], "first sight starts inflate", fr, k_first[SOOTLING_CLIP_INFLATE]);
    check(flip == 0, "facing right unmirrored", flip, 0);
    t = clip_ticks(SOOTLING_CLIP_INFLATE);
    fr = run(&a, &f, t - 1, &flip);
    check(fr == k_first[SOOTLING_CLIP_INFLATE] + k_count[SOOTLING_CLIP_INFLATE] - 1, "inflate last frame", fr,
          k_first[SOOTLING_CLIP_INFLATE] + k_count[SOOTLING_CLIP_INFLATE] - 1);
    fr = run(&a, &f, 1, &flip);
    check(fr == k_first[SOOTLING_CLIP_FLAP2], "flap2 after inflate", fr, k_first[SOOTLING_CLIP_FLAP2]);

    /* in the air without a press the flap clip holds its rest frame (first frame) forever; see flap_tests for the press */
    f.on_ground = 0;
    fr = 0;
    for (i = 0; i < 200; i++) {
        fr = flier_anim_step(&a, &f, &clips, &flip);
        if (fr != k_first[SOOTLING_CLIP_FLAP2]) { check(0, "air without a press holds the rest frame", fr, k_first[SOOTLING_CLIP_FLAP2]); break; }
    }

    /* 2 -> 1 balloons plays pop2, then flap1 */
    f.balloons = 1;
    fr = run(&a, &f, 1, &flip);
    check(fr == k_first[SOOTLING_CLIP_POP2], "pop2 on 2 to 1", fr, k_first[SOOTLING_CLIP_POP2]);
    fr = run(&a, &f, clip_ticks(SOOTLING_CLIP_POP2) - 1, &flip);
    check(fr == k_first[SOOTLING_CLIP_POP2] + k_count[SOOTLING_CLIP_POP2] - 1, "pop2 last frame", fr,
          k_first[SOOTLING_CLIP_POP2] + k_count[SOOTLING_CLIP_POP2] - 1);
    fr = run(&a, &f, 1, &flip);
    check(fr == k_first[SOOTLING_CLIP_FLAP1], "flap1 after pop2", fr, k_first[SOOTLING_CLIP_FLAP1]);

    /* 1 -> 0 plays pop1, then idle */
    f.balloons = 0;
    fr = run(&a, &f, 1, &flip);
    check(fr == k_first[SOOTLING_CLIP_POP1], "pop1 on 1 to 0", fr, k_first[SOOTLING_CLIP_POP1]);
    fr = run(&a, &f, clip_ticks(SOOTLING_CLIP_POP1), &flip);
    check(fr == k_first[SOOTLING_CLIP_IDLE], "idle with no balloons", fr, k_first[SOOTLING_CLIP_IDLE]);

    /* 2 -> 0 plays pop1 */
    flier_init(&f, 0, 0, 2, 1);
    flier_anim_init(&a);
    run(&a, &f, clip_ticks(SOOTLING_CLIP_INFLATE) + 1, &flip);
    f.balloons = 0;
    fr = run(&a, &f, 1, &flip);
    check(fr == k_first[SOOTLING_CLIP_POP1], "pop1 on 2 to 0", fr, k_first[SOOTLING_CLIP_POP1]);

    /* a balloon gain plays inflate */
    f.balloons = 1;
    fr = run(&a, &f, 1, &flip);
    check(fr == k_first[SOOTLING_CLIP_INFLATE], "inflate on gain", fr, k_first[SOOTLING_CLIP_INFLATE]);

    /* falling cuts a one shot short and loops fall */
    f.state = FLIER_FALLING;
    fr = run(&a, &f, 1, &flip);
    check(fr == k_first[SOOTLING_CLIP_FALL], "falling cuts inflate", fr, k_first[SOOTLING_CLIP_FALL]);
    fr = run(&a, &f, 4 * clip_ticks(SOOTLING_CLIP_FALL) + 1, &flip);
    check(fr >= k_first[SOOTLING_CLIP_FALL] && fr < k_first[SOOTLING_CLIP_FALL] + k_count[SOOTLING_CLIP_FALL],
          "fall loops in clip", fr, k_first[SOOTLING_CLIP_FALL]);

    /* mirroring follows facing */
    f.state = FLIER_ALIVE; f.facing = 0;
    run(&a, &f, 1, &flip);
    check(flip == 1, "facing left mirrors", flip, 1);
    f.facing = 1;
    run(&a, &f, 1, &flip);
    check(flip == 0, "facing right does not", flip, 0);

    /* facing follows the last non-zero input dir and keeps it at dir 0 */
    {
        Flier g; FlierInput in = {0, 0};
        FlierAnim b;
        flier_init(&g, 160 << 16, 100 << 16, 2, 1);
        flier_anim_init(&b);
        in.dir = -1; flier_step(&g, &in, 0x7FFFFFFF);
        in.dir = 0;  flier_step(&g, &in, 0x7FFFFFFF);
        flier_anim_step(&b, &g, &clips, &flip);
        check(flip == 1, "left input then idle stays mirrored", flip, 1);
        in.dir = 1;  flier_step(&g, &in, 0x7FFFFFFF);
        flier_anim_step(&b, &g, &clips, &flip);
        check(flip == 0, "right input unmirrors", flip, 0);
    }
    /* The brief fixed these durations. The tests below follow the macros, so pin the defaults here: a changed default
     * fails this block (knob overrides are exercised by knob_digest, not here). */
    check(FLIER_WALK_HOLD == 3, "walk hold is 3", FLIER_WALK_HOLD, 3);
    check(FLIER_LAND_HOLD_0 == 9 && FLIER_LAND_HOLD_1 == 12, "landing holds are 9 and 12", FLIER_LAND_HOLD_0, 9);
    check(FLIER_BREATHE_HOLD_0 == 36 && FLIER_BREATHE_HOLD_1 == 15 && FLIER_BREATHE_HOLD_2 == 21 && FLIER_BREATHE_HOLD_3 == 15,
          "breathing holds are 36/15/21/15", FLIER_BREATHE_HOLD_0, 36);
    check(FLIER_FLAP_HOLD == 2, "flap hold is 2", FLIER_FLAP_HOLD, 2);
    for (i = 0; i < 3; i++) ground_tests(i);
    flap_tests(2);
    flap_tests(1);
    pump_frame_tests();
    printf(bad ? "FAIL flier_view (%d)\n" : "PASS flier_view\n", bad);
    return bad != 0;
}
