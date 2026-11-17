/* flier_anim_step: clip choice, timing and mirroring, driven by the numbers the build generates from the art's
 * frames.json (build/gen/sootling_tables.h). Prints one FAIL line per miss and a final PASS/FAIL line. */
#include <stdio.h>
#include "../../src/core/flier_view.h"
#include "gen/sootling_tables.h"

static const uint8_t k_first[] = SOOTLING_TABLE_CLIP_FIRST;
static const uint8_t k_count[] = SOOTLING_TABLE_CLIP_COUNT;
static const uint8_t k_loop[] = SOOTLING_TABLE_CLIP_LOOP;
static const uint8_t k_ticks[] = SOOTLING_TABLE_FRAME_TICKS;
static const uint8_t k_sway[] = SOOTLING_TABLE_SWAY;
static const FlierClips clips = { k_first, k_count, k_loop, k_ticks,
    SOOTLING_CLIP_FLAP, SOOTLING_CLIP_FLY, SOOTLING_CLIP_SETTLE, SOOTLING_CLIP_IDLE, SOOTLING_CLIP_PUMP,
    SOOTLING_CLIP_INFLATE, SOOTLING_CLIP_FALL, SOOTLING_CLIP_POP2, SOOTLING_CLIP_POP1,
    SOOTLING_CLIP_WALK, SOOTLING_CLIP_LAND, SOOTLING_CLIP_BREATHE,
    k_sway, SOOTLING_CLIP_FLAP_R, SOOTLING_CLIP_FLAP_L };

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

/* Steps through every frame of a clip with the sheet's own ticks, from its first step on; every frame must show for its ticks. */
static void play_through(FlierAnim *a, const Flier *f, int clip, const char *what)
{
    char msg[64];
    int flip, k, i;
    for (k = 0; k < k_count[clip]; k++)
        for (i = 0; i < k_ticks[k_first[clip] + k]; i++) {
            uint8_t fr = flier_anim_step(a, f, &clips, &flip);
            sprintf(msg, "%s frame %d step %d", what, k, i);
            check(fr == k_first[clip] + k, msg, fr, k_first[clip] + k);
        }
}

static int in_clip(int fr, int clip)
{
    return fr >= k_first[clip] && fr < k_first[clip] + k_count[clip];
}

/* A flier in the air with b balloons, past its first inflate. */
static void start_air(Flier *f, FlierAnim *a, int b)
{
    int flip;
    flier_init(f, 0, 0, (uint8_t)b, 1);
    f->on_ground = 0;
    flier_anim_init(a);
    if (b) run(a, f, clip_ticks(SOOTLING_CLIP_INFLATE), &flip);
}

/* Ground clips for balloon count b: breathing, walking, landing, leaving the ground. All numbers come from the knob
 * macros and the generated tables. */
static void ground_tests(int b)
{
    static const int breathe_hold[4] = { FLIER_BREATHE_HOLD_0, FLIER_BREATHE_HOLD_1, FLIER_BREATHE_HOLD_2, FLIER_BREATHE_HOLD_3 };
    const int walk = SOOTLING_CLIP_WALK, land = SOOTLING_CLIP_LAND, breathe = SOOTLING_CLIP_BREATHE;
    const int air = b == 0 ? SOOTLING_CLIP_IDLE : SOOTLING_CLIP_FLY;
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
    check(k_count[breathe] == 4, "breathe has 4 frames", k_count[breathe], 4);
    for (cycle = 0; cycle < 2; cycle++)
        for (k = 0; k < 4; k++)
            for (i = 0; i < breathe_hold[k]; i++) {
                fr = flier_anim_step(&a, &f, &clips, &flip);
                sprintf(what, "b%d breathe frame %d step %d", b, k, i);
                check(fr == k_first[breathe] + k, what, fr, k_first[breathe] + k);
            }

    /* walking: every frame FLIER_WALK_HOLD steps, in order, wraps */
    f.vx = 91750; /* 1.4 px per frame */
    check(k_count[walk] == 2, "walk has 2 frames", k_count[walk], 2);
    for (cycle = 0; cycle < 3; cycle++)
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
    check(k_count[land] == 2, "land has 2 frames", k_count[land], 2);
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

/* The constant blow loop (fly), the flap play on a press and the settle on a turn in the air. */
/* Frame of the flap clip that fr shows, on the centred or a swung body (flap, flap_r, flap_l), or -1. */
static int flap_off(uint8_t fr)
{
    static const uint8_t k[3] = { SOOTLING_CLIP_FLAP, SOOTLING_CLIP_FLAP_R, SOOTLING_CLIP_FLAP_L };
    int i;
    for (i = 0; i < 3; i++) if (in_clip(fr, k[i])) return fr - k_first[k[i]];
    return -1;
}

static void air_tests(void)
{
    const int N = k_count[SOOTLING_CLIP_FLAP], F0 = k_first[SOOTLING_CLIP_FLAP];
    Flier f;
    FlierAnim a;
    int flip, i, seen_first = 0;
    uint8_t fr;

    /* A: no press, the blow loop runs in the fly clip forever and visits every frame of it */
    start_air(&f, &a, 2);
    check(k_loop[SOOTLING_CLIP_FLY] == 1, "fly loops", k_loop[SOOTLING_CLIP_FLY], 1);
    for (i = 0; i < 4 * clip_ticks(SOOTLING_CLIP_FLY); i++) {
        fr = flier_anim_step(&a, &f, &clips, &flip);
        if (!in_clip(fr, SOOTLING_CLIP_FLY)) { check(0, "A: fly clip without a press", fr, k_first[SOOTLING_CLIP_FLY]); break; }
        if (fr == k_first[SOOTLING_CLIP_FLY] + k_count[SOOTLING_CLIP_FLY] - 1) seen_first++;
    }
    check(seen_first > 0, "A: fly loop reaches its last frame", seen_first, 1);

    /* B: one press plays the whole flap clip with the sheet's ticks (the press step is the first of frame 0), then fly again */
    start_air(&f, &a, 2);
    f.flapped = 1;
    fr = flier_anim_step(&a, &f, &clips, &flip);
    f.flapped = 0;
    check(flap_off(fr) == 0, "B: press shows the first flap frame", flap_off(fr), 0);
    {
        int k, t;
        for (t = 1; t < k_ticks[F0]; t++) check(flap_off(flier_anim_step(&a, &f, &clips, &flip)) == 0, "B: first flap frame holds", 0, 0);
        for (k = 1; k < N; k++)
            for (t = 0; t < k_ticks[F0 + k]; t++) {
                fr = flier_anim_step(&a, &f, &clips, &flip);
                check(flap_off(fr) == k, "B: flap frame", flap_off(fr), k);
            }
    }
    fr = flier_anim_step(&a, &f, &clips, &flip);
    check(in_clip(fr, SOOTLING_CLIP_FLY), "B: fly after the flap", fr, k_first[SOOTLING_CLIP_FLY]);

    /* C: a press inside the flap restarts it at the first frame */
    start_air(&f, &a, 1);
    f.flapped = 1;
    flier_anim_step(&a, &f, &clips, &flip);
    f.flapped = 0;
    run(&a, &f, k_ticks[F0] + 1, &flip);
    f.flapped = 1;
    fr = flier_anim_step(&a, &f, &clips, &flip);
    f.flapped = 0;
    check(flap_off(fr) == 0, "C: restart shows the first frame", flap_off(fr), 0);

    /* D: a turn in the air plays the settle clip once, mirrored by the flip, then fly; a press during it plays flap on the swung body */
    start_air(&f, &a, 2);
    f.facing = 0;
    fr = flier_anim_step(&a, &f, &clips, &flip);
    check(fr == k_first[SOOTLING_CLIP_SETTLE] && flip == 1, "D: turn starts settle, mirrored", fr, k_first[SOOTLING_CLIP_SETTLE]);
    check(k_loop[SOOTLING_CLIP_SETTLE] == 0, "D: settle is a one shot", k_loop[SOOTLING_CLIP_SETTLE], 0);
    run(&a, &f, k_ticks[k_first[SOOTLING_CLIP_SETTLE]] - 1, &flip);
    fr = flier_anim_step(&a, &f, &clips, &flip);
    check(fr == k_first[SOOTLING_CLIP_SETTLE] + 1, "D: settle advances", fr, k_first[SOOTLING_CLIP_SETTLE] + 1);
    f.flapped = 1;
    fr = flier_anim_step(&a, &f, &clips, &flip);
    f.flapped = 0;
    check(fr == k_first[SOOTLING_CLIP_FLAP_R], "D: a press during settle flaps on the swung body", fr, k_first[SOOTLING_CLIP_FLAP_R]);
    start_air(&f, &a, 2);
    f.facing = 0;
    run(&a, &f, clip_ticks(SOOTLING_CLIP_SETTLE), &flip);
    fr = flier_anim_step(&a, &f, &clips, &flip);
    check(in_clip(fr, SOOTLING_CLIP_FLY), "D: fly after settle", fr, k_first[SOOTLING_CLIP_FLY]);

    /* F: turn, then flap all through the sway: every step shows a flap frame on the body the sway has at that step
     * (b plays the same turn without a press), to both sides, and the fly loop sway goes on under the presses after it */
    {
        Flier g;
        FlierAnim b;
        int flip_b, side[3] = { 0, 0, 0 }, late[3] = { 0, 0, 0 }, n = clip_ticks(SOOTLING_CLIP_SETTLE) + 2 * clip_ticks(SOOTLING_CLIP_FLY);
        uint8_t ref;
        start_air(&f, &a, 2);
        start_air(&g, &b, 2);
        f.facing = g.facing = 0;
        run(&a, &f, 3, &flip);
        run(&b, &g, 3, &flip_b);
        for (i = 0; i < n; i++) {
            f.flapped = (uint8_t)(i % 9 == 0);
            fr = flier_anim_step(&a, &f, &clips, &flip);
            ref = flier_anim_step(&b, &g, &clips, &flip_b);
            if (flap_off(fr) < 0) { check(0, "F: a flap frame at every step", fr, F0); break; }
            if (k_sway[fr] != k_sway[ref]) { check(0, "F: the flap shows the sway of that step", k_sway[fr], k_sway[ref]); break; }
            side[k_sway[fr]]++;
            if (i >= clip_ticks(SOOTLING_CLIP_SETTLE)) late[k_sway[fr]]++;
        }
        check(side[1] > 0 && side[2] > 0, "F: the sway shows to both sides under the flaps", side[1], side[2]);
        check(late[1] > 0 && late[2] > 0, "F: the fly sway goes on under the flaps", late[1], late[2]);
        f.flapped = 0;
        run(&a, &f, clip_ticks(SOOTLING_CLIP_FLAP), &flip);
        run(&b, &g, clip_ticks(SOOTLING_CLIP_FLAP), &flip_b);
        fr = flier_anim_step(&a, &f, &clips, &flip);
        ref = flier_anim_step(&b, &g, &clips, &flip_b);
        check(fr == ref, "F: after the last flap the sway is where it would be without one", fr, ref);
    }

    /* E: a press during a pop is ignored, not latched */
    start_air(&f, &a, 2);
    f.balloons = 1;
    f.flapped = 1;
    play_through(&a, &f, SOOTLING_CLIP_POP2, "E pop2");
    f.flapped = 0;
    fr = flier_anim_step(&a, &f, &clips, &flip);
    check(in_clip(fr, SOOTLING_CLIP_FLY), "E: fly after pop2", fr, k_first[SOOTLING_CLIP_FLY]);
}

/* The pump draws the pump clip by progress: first frame at 0, last at ARC_PUMP_STAGES - 1, never backwards or outside the clip. */
static void pump_frame_tests(void)
{
    int p, last = -1, fr;
    const int first = k_first[SOOTLING_CLIP_PUMP], n = k_count[SOOTLING_CLIP_PUMP];
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

    /* sheet facts: the gum-mouth v4 sheet (14 clips, 95 frames: 12 clips plus flap_r / flap_l) replaced the 105 frame sootling sheet */
    check(SOOTLING_FRAMES == 95, "frame count", SOOTLING_FRAMES, 95);
    check(SOOTLING_CLIP_COUNT == 14, "clip count", SOOTLING_CLIP_COUNT, 14);
    /* the pipeline pads art to whole 16 px tiles: 24 px art is still 2 strips (src/vram_layout.h SOOT_COLUMNS) */
    check(SOOTLING_ART_W == 24 && SOOTLING_ART_H == 32, "art size", SOOTLING_ART_W, 24);
    /* SOOTLING_MAX_COLUMNS lives in the ngdevkit-typed sprites header, not in the host-includable tables header: 17..32 px is exactly 2 strips */
    check(SOOTLING_ART_W > 16 && SOOTLING_ART_W <= 32, "art width is 2 strips (17..32 px)", SOOTLING_ART_W, 24);
    check(SOOTLING_BOX_LAST_COL - SOOTLING_BOX_FIRST_COL + 1 == 2 * FLIER_HALF_W, "hit box width",
          SOOTLING_BOX_LAST_COL - SOOTLING_BOX_FIRST_COL + 1, 2 * FLIER_HALF_W);
    check(SOOTLING_FEET_ROW == SOOTLING_ART_H - 1, "feet on last row", SOOTLING_FEET_ROW, SOOTLING_ART_H - 1);

    /* a flier first shown with 2 balloons plays inflate to its end, then the fly loop */
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
    check(fr == k_first[SOOTLING_CLIP_FLY], "fly after inflate", fr, k_first[SOOTLING_CLIP_FLY]);

    /* 2 -> 1 balloons plays pop2, then fly */
    f.on_ground = 0;
    f.balloons = 1;
    fr = run(&a, &f, 1, &flip);
    check(fr == k_first[SOOTLING_CLIP_POP2], "pop2 on 2 to 1", fr, k_first[SOOTLING_CLIP_POP2]);
    fr = run(&a, &f, clip_ticks(SOOTLING_CLIP_POP2) - 1, &flip);
    check(fr == k_first[SOOTLING_CLIP_POP2] + k_count[SOOTLING_CLIP_POP2] - 1, "pop2 last frame", fr,
          k_first[SOOTLING_CLIP_POP2] + k_count[SOOTLING_CLIP_POP2] - 1);
    fr = run(&a, &f, 1, &flip);
    check(fr == k_first[SOOTLING_CLIP_FLY], "fly after pop2", fr, k_first[SOOTLING_CLIP_FLY]);

    /* 1 -> 0 plays pop1, then idle */
    f.balloons = 0;
    fr = run(&a, &f, 1, &flip);
    check(fr == k_first[SOOTLING_CLIP_POP1], "pop1 on 1 to 0", fr, k_first[SOOTLING_CLIP_POP1]);
    fr = run(&a, &f, clip_ticks(SOOTLING_CLIP_POP1), &flip);
    check(fr == k_first[SOOTLING_CLIP_IDLE], "idle with no balloons", fr, k_first[SOOTLING_CLIP_IDLE]);
    for (i = 0; i < 200; i++) {
        fr = flier_anim_step(&a, &f, &clips, &flip);
        if (!in_clip(fr, SOOTLING_CLIP_IDLE)) { check(0, "idle loops in clip", fr, k_first[SOOTLING_CLIP_IDLE]); break; }
    }

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
    check(in_clip(fr, SOOTLING_CLIP_FALL), "fall loops in clip", fr, k_first[SOOTLING_CLIP_FALL]);

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
    for (i = 0; i < 3; i++) ground_tests(i);
    air_tests();
    pump_frame_tests();
    printf(bad ? "FAIL flier_view (%d)\n" : "PASS flier_view\n", bad);
    return bad != 0;
}
