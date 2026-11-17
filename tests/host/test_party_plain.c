/* PARTY_HOT has no rule code in this test and and must play exactly as plain arena: the match ends (1 and 2 players),
 * no roost island, no twist, same lives rule as plain arena. */
#include <stdio.h>
#include "../../src/core/game.h"

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

static Game g;

static int frames_to_over(uint8_t rule, int players) {
    int i;
    game_reset(&g, 5);
    game_set_mode(&g, GAME_MODE_ARENA);
    g.party_rule = rule;
    g.players = (uint8_t)players;
    g.rounds = 1;
    for (i = 0; i < 20000 && !g.over; i++) game_step(&g, 0);
    return g.over ? i : -1;
}

int main(void) {
    uint8_t rules[1] = { PARTY_HOT };
    int r, p, x, t, w;
    for (r = 0; r < 1; r++) {
        for (p = 1; p <= 2; p++) {
            CHECK(frames_to_over(rules[r], p) > 0); /* the match ends within 20000 frames */
            CHECK(g.twist == TWIST_NONE && !game_roost_rect(&g, &x, &t, &w));
            CHECK(game_lives_mode(&g) == (p == 2));
        }
    }
    printf("%d checks, %d failures\n", checks, failures);
    return failures != 0;
}
