/* Host test for TUG-GUM (gg_tug): pulls move the knot, D stumble window, best of 3, the computer rival is beatable but not by rolling fingers. */
#include <stdio.h>
#include "../../src/core/gg_tug.h"
#include "../../src/core/game.h"

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

static GgTug t;
static void press(uint8_t in1, uint8_t in2) { gg_tug_step(&t, in1, in2); gg_tug_step(&t, 0, 0); gg_tug_step(&t, 0, 0); }   /* a press, then two release frames (the pull cooldown is 3) */

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

    /* pull cooldown: a second press inside GTG_PULL_COOLDOWN frames shows but adds no force */
    gg_tug_start(&t, 1, 2);
    gg_tug_step(&t, IN_A, 0); gg_tug_step(&t, 0, 0); gg_tug_step(&t, IN_B, 0); CHECK(t.knot == -GTG_PULL_Q && t.press_n[0] == 2);

    /* 1P round 1: 15 presses/s (rolling fingers) is close, nobody wins within 4 s; 6 presses/s loses the round */
    { int seed, early = 0, lost = 0;
      for (seed = 1; seed <= 40; seed++) {
          gg_tug_start(&t, (uint32_t)seed, 1);
          for (i = 0; i < 60 * 4 && t.phase == GTG_PLAY; i++) gg_tug_step(&t, (i % 4 < 1) ? IN_A : 0, 0);
          early += t.phase != GTG_PLAY;
          gg_tug_start(&t, (uint32_t)seed, 1);
          for (i = 0; i < 60 * 40 && t.phase == GTG_PLAY; i++) gg_tug_step(&t, (i % 10 < 1) ? IN_A : 0, 0);
          lost += t.phase == GTG_SNAP && t.round_winner == 1;
      }
      CHECK(early == 0); CHECK(lost == 40); }
    /* the rival gets quicker for each round it lost, and never lets go while the human is not pulling */
    gg_tug_start(&t, 5, 1); t.wins[0] = 1; gg_tug_start(&t, 5, 1);
    { int n = 0; t.wins[0] = 1; for (i = 0; i < 600; i++) { gg_tug_step(&t, 0, 0); n += t.sfx & GTG_SFX_LETGO; t.sfx = 0; if (t.phase != GTG_PLAY) break; } CHECK(n == 0); }
    gg_tug_start(&t, 3, 1);
    for (i = 0; i < 60 * 40 && t.phase == GTG_PLAY; i++) gg_tug_step(&t, 0, 0);
    CHECK(t.phase == GTG_SNAP && t.round_winner == 1);
    /* 1P ignores the second input */
    gg_tug_start(&t, 3, 1);
    gg_tug_step(&t, 0, IN_A); CHECK(t.prev[1] == 0);

    printf("%s: %d checks, %d failures\n", failures ? "FAIL" : "PASS", checks, failures);
    return failures != 0;
}
