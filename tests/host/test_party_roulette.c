/* Hazard Roulette (PARTY_ROULETTE): each round has one hazard, never the same twice in a row, every kind comes up, same seed gives the same
 * order, the banner names it, and world_hazard (what the strip shows) agrees with the kill line source. */
#include <stdio.h>
#include <string.h>
#include "../../src/core/game.h"
#include "../../src/core/world.h"

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

static Game g;

static void start(uint32_t seed) {
    game_reset(&g, seed);
    game_set_mode(&g, GAME_MODE_ARENA);
    g.party_rule = PARTY_ROULETTE;
    g.rounds = 1;
    game_begin(&g);
}

int main(void) {
    uint8_t seq[40], seq2[40], seen[HAZARD_KINDS];
    int i, k;
    memset(seen, 0, sizeof seen);
    start(7);
    for (i = 0; i < 40; i++) {
        uint8_t kind = game_roulette_kind(&g);
        seq[i] = kind;
        CHECK(kind < HAZARD_KINDS);
        CHECK(world_hazard(&g) == kind);
        if (i) CHECK(kind != seq[i - 1]);
        seen[kind] = 1;
        CHECK(game_round_start_text(&g, 0) && strstr(game_round_start_text(&g, 0), "FLOOR") && strlen(game_round_start_text(&g, 1)) <= 36);
        g.matches_won++;
    }
    for (k = 0; k < HAZARD_KINDS; k++) CHECK(seen[k]);
    start(7);
    for (i = 0; i < 40; i++) { seq2[i] = game_roulette_kind(&g); g.matches_won++; }
    CHECK(memcmp(seq, seq2, sizeof seq) == 0); /* same seed, same order */
    start(8);
    for (i = 0; i < 40 && game_roulette_kind(&g) == seq[i]; i++) g.matches_won++;
    CHECK(i < 40); /* another seed differs somewhere */
    /* other rules keep the fixed order */
    start(7); g.party_rule = PARTY_ROUND;
    CHECK(world_hazard(&g) == hazard_kind_for_round(0));
    printf("%d checks, %d failures\n", checks, failures);
    return failures != 0;
}
