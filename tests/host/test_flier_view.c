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
    SOOTLING_CLIP_INFLATE, SOOTLING_CLIP_FALL, SOOTLING_CLIP_IDLE };

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

int main(void)
{
    Flier f;
    FlierAnim a;
    int flip, i, t;
    uint8_t fr;

    /* sheet facts */
    check(SOOTLING_FRAMES == 63, "frame count", SOOTLING_FRAMES, 63);
    check(SOOTLING_CLIP_COUNT == 7, "clip count", SOOTLING_CLIP_COUNT, 7);
    /* the pipeline pads art to whole 16 px tiles: 24 px art is still 2 strips (src/vram_layout.h SOOT_COLUMNS) */
    check((SOOTLING_ART_W + 15) / 16 == 2, "columns per frame", (SOOTLING_ART_W + 15) / 16, 2);
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

    /* on the ground flap clips rest on frame 0; in the air they advance by the frame ticks */
    f.on_ground = 1;
    fr = run(&a, &f, 30, &flip);
    check(fr == k_first[SOOTLING_CLIP_FLAP2], "ground rests on frame 0", fr, k_first[SOOTLING_CLIP_FLAP2]);
    f.on_ground = 0;
    run(&a, &f, 1, &flip);
    fr = run(&a, &f, k_ticks[k_first[SOOTLING_CLIP_FLAP2]], &flip);
    check(fr == k_first[SOOTLING_CLIP_FLAP2] + 1, "air advances to frame 1", fr, k_first[SOOTLING_CLIP_FLAP2] + 1);
    for (i = 0; i < 4 * clip_ticks(SOOTLING_CLIP_FLAP2); i++) {
        fr = flier_anim_step(&a, &f, &clips, &flip);
        if (fr < k_first[SOOTLING_CLIP_FLAP2] || fr >= k_first[SOOTLING_CLIP_FLAP2] + k_count[SOOTLING_CLIP_FLAP2]) {
            check(0, "flap2 loop stays in clip", fr, k_first[SOOTLING_CLIP_FLAP2]);
            break;
        }
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
    printf(bad ? "FAIL flier_view (%d)\n" : "PASS flier_view\n", bad);
    return bad != 0;
}
