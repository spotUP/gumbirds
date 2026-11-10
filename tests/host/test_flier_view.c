/* flier_view_pose: frame choice per state. Prints one FAIL line per miss and a final PASS/FAIL line. */
#include <stdio.h>
#include "../../src/core/flier_view.h"

static int bad;
static void expect(const char *what, Flier f, FlierPose want, int want_flip)
{
    int flip;
    FlierPose got = flier_view_pose(&f, &flip);
    if (got != want || flip != want_flip) {
        printf("FAIL %s: pose %d flip %d, want %d flip %d\n", what, (int)got, flip, (int)want, want_flip);
        bad++;
    }
}

int main(void)
{
    Flier f;
    flier_init(&f, 0, 0, 2, 1);
    expect("2 balloons on ground", f, FV_GLIDE2, 0);
    f.on_ground = 0;
    expect("2 balloons hovering", f, FV_GLIDE2, 0);
    f.vy = -100;
    expect("2 balloons rising", f, FV_UP2, 0);
    f.vy = 100;
    expect("2 balloons sinking", f, FV_DOWN2, 0);
    f.flap_prev = 1;
    expect("2 balloons flapping while sinking", f, FV_UP2, 0);
    f.flap_prev = 0; f.on_ground = 1;
    expect("2 balloons standing (vy>0 ignored)", f, FV_GLIDE2, 0);
    f.on_ground = 0; f.balloons = 1; f.vy = -100;
    expect("1 balloon rising", f, FV_UP1, 0);
    f.vy = 100;
    expect("1 balloon sinking has no down frame", f, FV_GLIDE1, 0);
    f.on_ground = 1; f.vy = 0;
    expect("1 balloon standing", f, FV_GLIDE1, 0);
    f.balloons = 0; f.on_ground = 0; f.vy = -100; f.flap_prev = 1;
    expect("0 balloons always glide", f, FV_GLIDE0, 0);
    f.state = FLIER_PARACHUTE;
    expect("parachute (0 balloons) glide", f, FV_GLIDE0, 0);
    f.balloons = 2; f.state = FLIER_FALLING;
    expect("falling", f, FV_FALL, 0);
    f.state = FLIER_DROWNED;
    expect("drowned", f, FV_FALL, 0);
    f.state = FLIER_ALIVE; f.balloons = 2; f.vy = 0; f.flap_prev = 0; f.facing = 0;
    expect("facing left mirrors", f, FV_GLIDE2, 1);
    f.facing = 1;
    expect("facing right does not", f, FV_GLIDE2, 0);
    /* facing follows the last non-zero input dir and keeps it at dir 0 */
    {
        Flier g; FlierInput in = {0, 0};
        int flip;
        flier_init(&g, 160 << 16, 100 << 16, 2, 1);
        in.dir = -1; flier_step(&g, &in, 0x7FFFFFFF);
        in.dir = 0;  flier_step(&g, &in, 0x7FFFFFFF);
        flier_view_pose(&g, &flip);
        if (!flip) { printf("FAIL facing: left input then idle must stay mirrored\n"); bad++; }
        in.dir = 1;  flier_step(&g, &in, 0x7FFFFFFF);
        flier_view_pose(&g, &flip);
        if (flip) { printf("FAIL facing: right input must unmirror\n"); bad++; }
    }
    printf(bad ? "FAIL flier_view (%d)\n" : "PASS flier_view\n", bad);
    return bad != 0;
}
