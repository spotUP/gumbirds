/* Host test for TOSS-GUM (gg_toss): target by seat, fuse shortens per round, burst removes the carrier, last bird wins. */
#include <stdio.h>
#include "../../src/core/gg_toss.h"
#include "../../src/core/game.h"

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

static GgToss t;

static void to_hold_free(void) { t.lead = 0; }

int main(void)
{
    uint8_t s, k;
    /* all four alive: A = next clockwise, B = across, C = the one before */
    for (s = 0; s < 4; s++) {
        CHECK(gg_toss_target(s, 0x0F, 0) == (s + 1) % 4);
        CHECK(gg_toss_target(s, 0x0F, 1) == (s + 2) % 4);
        CHECK(gg_toss_target(s, 0x0F, 2) == (s + 3) % 4);
    }
    /* seat 1 out: others of seat 0 are 2,3 -> A 2, B 2, C 3 */
    CHECK(gg_toss_target(0, 0x0D, 0) == 2 && gg_toss_target(0, 0x0D, 1) == 2 && gg_toss_target(0, 0x0D, 2) == 3);
    /* only one other: every button goes to it; never to an out bird or itself */
    for (k = 0; k < 3; k++) CHECK(gg_toss_target(0, 0x09, k) == 3);
    CHECK(gg_toss_target(0, 0x01, 0) == 0xFF);
    for (s = 0; s < 4; s++) for (k = 0; k < 3; k++) { uint8_t r = gg_toss_target(s, 0x0B, k); CHECK(r == 0xFF || (r != s && ((0x0B >> r) & 1))); }

    /* fuse shortens per round, floors */
    CHECK(gg_toss_fuse(1) < gg_toss_fuse(0));
    CHECK(gg_toss_fuse(2) < gg_toss_fuse(1));
    CHECK(gg_toss_fuse(50) == GT_FUSE_MIN);

    /* a human carrier tosses with A and the gum lands on the seat-relative target */
    gg_toss_start(&t, 5, 2);
    t.carrier = 0; t.alive = 0x0F; to_hold_free();
    gg_toss_step(&t, IN_C, 0);
    CHECK(t.phase == GT_FLIGHT && t.target == 3 && (t.sfx & GT_SFX_TOSS));
    { uint16_t left = t.fuse; int i; for (i = 0; i < GT_FLIGHT_FRAMES; i++) gg_toss_step(&t, 0, 0);
      CHECK(t.phase == GT_HOLD && t.carrier == 3 && t.fuse == left); }
    /* player 2 holds seat 2: B throws across to seat 0 */
    gg_toss_start(&t, 5, 2);
    t.carrier = 2; to_hold_free();
    gg_toss_step(&t, IN_A, 0);   /* P1 input must not toss for P2's bird */
    CHECK(t.phase == GT_HOLD);
    gg_toss_step(&t, 0, 0); gg_toss_step(&t, 0, IN_B);
    CHECK(t.phase == GT_FLIGHT && t.target == 0);

    /* a CPU carrier tosses on its own */
    gg_toss_start(&t, 9, 1);
    t.carrier = 1; to_hold_free(); t.think = 3;
    { int i; for (i = 0; i < 5; i++) gg_toss_step(&t, 0, 0); }
    CHECK(t.phase == GT_FLIGHT && t.target != 1);

    /* burst removes the carrier and passes the gum to a survivor with a shorter fuse */
    gg_toss_start(&t, 3, 1);
    t.carrier = 1; t.fuse = 2;
    gg_toss_step(&t, 0, 0); gg_toss_step(&t, 0, 0);
    CHECK(t.phase == GT_BURST && !((t.alive >> 1) & 1) && t.round == 1 && (t.sfx & GT_SFX_BURST));
    { int i; for (i = 0; i < GT_BURST_FRAMES; i++) gg_toss_step(&t, 0, 0);
      CHECK(t.phase == GT_HOLD && t.carrier != 1 && ((t.alive >> t.carrier) & 1));
      CHECK(t.fuse < GT_FUSE_BASE + GT_FUSE_JITTER); }

    /* last bird wins */
    gg_toss_start(&t, 3, 1);
    t.alive = 0x03; t.carrier = 1; t.fuse = 1;
    { int i; for (i = 0; i < GT_BURST_FRAMES + 3; i++) gg_toss_step(&t, 0, 0);
      CHECK(t.phase == GT_RESULT && t.winner == 0 && (t.sfx & GT_SFX_WIN));
      for (i = 0; i < GT_RESULT_FRAMES + 1; i++) gg_toss_step(&t, 0, 0);
      CHECK(t.phase == GT_END); }

    /* full CPU-only-style run always ends with exactly one survivor */
    gg_toss_start(&t, 77, 1);
    { int i; for (i = 0; i < 20000 && t.phase != GT_RESULT; i++) { gg_toss_step(&t, 0, 0); if (t.phase == GT_HOLD && t.carrier == 0 && !t.lead) gg_toss_step(&t, IN_A, 0); else gg_toss_step(&t, 0, 0); }
      CHECK(t.phase == GT_RESULT && gg_toss_count(&t) == 1); }

    /* poses: only the carrier and the target leave the standing body; windup, release, reach, catch, absorb in this order */
    gg_toss_start(&t, 5, 1);
    t.carrier = 0; t.lead = 0;
    CHECK(gg_toss_pose(&t, 0) == GT_POSE_CARRY && gg_toss_pose(&t, 1) == -1);
    gg_toss_step(&t, IN_A, 0);
    CHECK(t.phase == GT_FLIGHT);
    { int i, last_from = GT_POSE_CARRY, last_to = -1, ok = 1; uint8_t to = t.target;
      for (i = 0; i < GT_FLIGHT_FRAMES + 2 && t.phase == GT_FLIGHT; i++) {
          int a = gg_toss_pose(&t, 0), b = gg_toss_pose(&t, to), s;
          if (a >= 0 && a < last_from) ok = 0;
          if (b < last_to) ok = 0;
          if (a >= 0) last_from = a;
          last_to = b;
          if (t.t < GT_RELEASE_FRAME && a != GT_POSE_WINDUP && a != GT_POSE_RELEASE) ok = 0;   /* the gum is still on the wing */
          for (s = 0; s < (int)GT_SEATS; s++) if (s != 0 && s != to && gg_toss_pose(&t, (uint8_t)s) != -1) ok = 0;
          gg_toss_step(&t, 0, 0);
      }
      CHECK(ok && last_to == GT_POSE_CATCH);
      CHECK(t.phase == GT_HOLD && t.carrier == to && gg_toss_pose(&t, to) == GT_POSE_ABSORB && gg_toss_pose(&t, 0) == -1); }

    printf("%s: %d checks, %d failures\n", failures ? "FAIL" : "PASS", checks, failures);
    return failures != 0;
}
