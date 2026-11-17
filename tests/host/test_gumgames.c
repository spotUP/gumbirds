/* test_gumgames.c - Gum Games event framework: mash, hold-release, power bar, sequencing. */
#include <stdio.h>
#include <string.h>
#include "gumgames.h"
#include "game.h"

static int fails;
#define CHECK(c) do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); fails++; } } while (0)

int main(void)
{
    GgMash m; GgHold h; GgBar b; GgSeq s;
    uint8_t out[16];
    int i;

    /* mash: only alternating A/B count; same button again, held button and both-at-once do not */
    gg_mash_reset(&m);
    CHECK(gg_mash_step(&m, IN_A, 0) == 1 && m.count == 1);
    CHECK(gg_mash_step(&m, IN_A, 0) == 0 && m.count == 1);          /* A again */
    CHECK(gg_mash_step(&m, IN_A | IN_B, IN_A) == 1 && m.count == 2); /* B newly pressed while A held */
    CHECK(gg_mash_step(&m, IN_B, IN_B) == 0 && m.count == 2);       /* held, no new press */
    CHECK(gg_mash_step(&m, IN_A | IN_B, 0) == 0 && m.count == 2);   /* both at once */
    CHECK(gg_mash_step(&m, IN_A, 0) == 1 && m.count == 3);
    CHECK(gg_mash_step(&m, IN_C, 0) == 0);

    /* hold C: charge grows to the cap, release returns it once */
    memset(&h, 0, sizeof h);
    for (i = 0; i < 10; i++) CHECK(gg_hold_step(&h, IN_C, 7) == 0);
    CHECK(h.charge == 7 && gg_hold_step(&h, 0, 7) == 7 && h.charge == 0 && gg_hold_step(&h, 0, 7) == 0);

    /* bar: only changed cells are reported, clamped to the width */
    b.width = 8; b.filled = 0;
    CHECK(gg_bar_set(&b, 3, out, 16) == 3 && out[0] == (0 | 0x80) && out[2] == (2 | 0x80));
    CHECK(gg_bar_set(&b, 3, out, 16) == 0);
    CHECK(gg_bar_set(&b, 1, out, 16) == 2 && out[0] == 1 && out[1] == 2);
    CHECK(gg_bar_set(&b, 99, out, 16) == 7 && b.filled == 8);

    /* sequencing, 1P: three attempts, best counts, qualifying mark sticks */
    gg_seq_start(&s, GG_BIG_BLOW, 1);
    CHECK(s.tickets[0] == GG_ATTEMPTS && s.tickets[1] == 0);
    CHECK(gg_seq_attempt(&s, 2, 2, 0) == 1 && s.turn == 0 && !s.qualified[0]);
    CHECK(gg_seq_attempt(&s, 3, 3, 1) == 1 && s.qualified[0] && s.best[0] == 3);
    CHECK(gg_seq_attempt(&s, 0, 0, 0) == 0 && s.best[0] == 3 && s.qualified[0]);   /* burst after best: best stays */
    CHECK(s.points[0] == gg_points(3, 1) && s.points[0] == 3 * GG_STAGE_POINTS + GG_QUALIFY_POINTS);

    /* sequencing, 2P: turns alternate, input byte follows the turn */
    gg_seq_start(&s, GG_BIG_BLOW, 2);
    CHECK(gg_seq_input(&s, 0x11, 0x22) == 0x11);
    gg_seq_attempt(&s, 1, 1, 0);
    CHECK(s.turn == 1 && gg_seq_input(&s, 0x11, 0x22) == 0x22);
    gg_seq_attempt(&s, 4, 4, 1);
    CHECK(s.turn == 0 && s.qualified[1] && !s.qualified[0]);
    for (i = 0; i < 3; i++) gg_seq_attempt(&s, 1, 1, 0);   /* P1 2nd, P2 2nd, P1 3rd */
    CHECK(s.tickets[0] == 0 && s.tickets[1] == 1 && s.turn == 1);   /* only P2 left: P2 keeps the turn */
    CHECK(gg_seq_attempt(&s, 1, 1, 0) == 0);                       /* last ticket spent: event over */

    printf("test_gumgames: %s\n", fails ? "FAILED" : "all checks passed");
    return fails ? 1 : 0;
}
