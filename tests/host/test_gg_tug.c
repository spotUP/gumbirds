/* Host test for TUG-GUM (gg_tug): pulls move the knot, D stumble window, best of 3, the computer rival is beatable. */
#include <stdio.h>
#include "../../src/core/gg_tug.h"
#include "../../src/core/game.h"

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

static GgTug t;
static void press(uint8_t in1, uint8_t in2) { gg_tug_step(&t, in1, in2); gg_tug_step(&t, 0, 0); }   /* a press, then a release frame */

int main(void)
{
    int i;
    /* pull balance: P1 pulls move the knot towards team 0 (negative), P2 pulls the other way, equal pulls cancel */
    gg_tug_start(&t, 1, 2);
    press(IN_A, 0); CHECK(t.knot == -GTG_PULL_Q);
    press(0, IN_B); CHECK(t.knot == 0);
    gg_tug_step(&t, IN_A, IN_B); CHECK(t.knot == 0);
    gg_tug_step(&t, IN_A, IN_B); CHECK(t.knot == 0);   /* held buttons are no new press */
    gg_tug_step(&t, 0, 0); gg_tug_step(&t, IN_B | IN_C, 0); CHECK(t.knot == -GTG_PULL_Q);   /* B and C on one frame count once */

    /* D with no recent rival pull: you lose ground, nobody stumbles */
    gg_tug_start(&t, 1, 2);
    press(0, IN_D); CHECK(t.knot == -GTG_LETGO_Q && t.stumble[0] == 0 && t.slide[1]);
    /* D right after the rival pulled: the rival stumbles and their pulls count for nothing */
    gg_tug_start(&t, 1, 2);
    press(IN_A, 0); press(0, IN_D);
    CHECK(t.stumble[0] > 0 && t.stumble[0] <= GTG_STUMBLE_FRAMES);
    { int16_t k = t.knot; press(IN_A, 0); CHECK(t.knot == k); }
    for (i = 0; i < (int)GTG_STUMBLE_FRAMES + 2; i++) gg_tug_step(&t, 0, 0);
    { int16_t k = t.knot; press(IN_A, 0); CHECK(t.knot == k - GTG_PULL_Q); }
    /* a pull older than the window does not stumble the rival */
    gg_tug_start(&t, 1, 2);
    press(IN_A, 0); for (i = 0; i < (int)GTG_LETGO_WINDOW + 2; i++) gg_tug_step(&t, 0, 0);
    press(0, IN_D); CHECK(t.stumble[0] == 0);

    /* crossing the win line takes the round, the strand snaps, best of 3 */
    gg_tug_start(&t, 1, 2);
    for (i = 0; i < GTG_WIN_Q / GTG_PULL_Q + 1 && t.phase == GTG_PLAY; i++) press(IN_A, 0);
    CHECK(t.phase == GTG_SNAP && t.round_winner == 0 && t.wins[0] == 1 && (t.sfx & GTG_SFX_SNAP));
    CHECK(gg_tug_pose(&t, 2) == GTG_POSE_SLAPPED && gg_tug_pose(&t, 3) == GTG_POSE_SLAPPED && gg_tug_pose(&t, 0) != GTG_POSE_SLAPPED);
    for (i = 0; i < (int)GTG_SNAP_FRAMES; i++) gg_tug_step(&t, 0, 0);
    CHECK(t.phase == GTG_PLAY && t.knot == 0 && t.wins[0] == 1);   /* round 2 starts with the knot in the middle */
    for (i = 0; i < GTG_WIN_Q / GTG_PULL_Q + 1 && t.phase == GTG_PLAY; i++) press(0, IN_C);
    CHECK(t.round_winner == 1 && t.wins[1] == 1);
    for (i = 0; i < (int)GTG_SNAP_FRAMES; i++) gg_tug_step(&t, 0, 0);
    for (i = 0; i < GTG_WIN_Q / GTG_PULL_Q + 1 && t.phase == GTG_PLAY; i++) press(0, IN_C);
    CHECK(t.wins[1] == 2);
    for (i = 0; i < (int)GTG_SNAP_FRAMES; i++) gg_tug_step(&t, 0, 0);
    CHECK(t.phase == GTG_RESULT && (t.sfx & GTG_SFX_WIN));
    for (i = 0; i < (int)GTG_RESULT_FRAMES; i++) gg_tug_step(&t, 0, 0);
    CHECK(t.phase == GTG_END);

    /* 1P: a player mashing at 10 presses per second beats the computer rival every time; idling loses to it */
    { int wins = 0, seed;
      for (seed = 1; seed <= 20; seed++) {
          gg_tug_start(&t, (uint32_t)seed, 1);
          for (i = 0; i < 60 * 40 && t.phase == GTG_PLAY; i++) gg_tug_step(&t, (i % 6 < 1) ? IN_A : 0, 0);
          wins += t.phase == GTG_SNAP && t.round_winner == 0;
      }
      CHECK(wins == 20); }
    gg_tug_start(&t, 3, 1);
    for (i = 0; i < 60 * 40 && t.phase == GTG_PLAY; i++) gg_tug_step(&t, 0, 0);
    CHECK(t.phase == GTG_SNAP && t.round_winner == 1);
    /* 1P ignores the second input */
    gg_tug_start(&t, 3, 1);
    gg_tug_step(&t, 0, IN_A); CHECK(t.prev[1] == 0);

    printf("%s: %d checks, %d failures\n", failures ? "FAIL" : "PASS", checks, failures);
    return failures != 0;
}
