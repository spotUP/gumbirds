/* Rule of the Round (PARTY_ROUND): each twist applied, no repeat in a row, deterministic with the seed, Mirror Stick on play input only. */
#include <stdio.h>
#include <string.h>
#include "../../src/core/game.h"
#include "../../src/core/tuning.h"
#include "../../src/core/nameentry.h" /* IN_LEFT */

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

static Game g;

static void start(uint32_t seed, uint8_t rule) {
    game_reset(&g, seed);
    game_set_mode(&g, GAME_MODE_ARENA);
    g.party_rule = rule;
    g.rounds = 1;
    game_begin(&g);
}

/* Force the next round: clear the cpus so match_start runs again. */
static void next_round(void) {
    int i;
    g.cpu_count = 0;
    for (i = 0; i < STAGE_SPAWN_COUNT; i++) g.cpu[i].state = FLIER_GONE;
    game_begin(&g);
    g.matches_won++;
}

static void air(Game *m) {
    m->round_start = RS_NONE;
    m->hero[0].y = FL_PX(40); m->hero[0].vy = 0; m->hero[0].vx = 0; m->hero[0].on_ground = 0;
}

int main(void) {
    uint8_t seq[40], seq2[40], seen[TWIST_COUNT];
    int i, k;
    memset(seen, 0, sizeof seen);
    start(7, PARTY_ROUND);
    for (i = 0; i < 40; i++) {
        seq[i] = g.twist;
        CHECK(g.twist > TWIST_NONE && g.twist < TWIST_COUNT);
        if (i) CHECK(seq[i] != seq[i - 1]);
        seen[g.twist] = 1;
        CHECK(game_round_start_text(&g, 0) == game_twist_name(g.twist) && game_round_start_text(&g, 1) == game_party_goal(PARTY_ROUND));
        next_round();
    }
    for (k = 1; k < TWIST_COUNT; k++) CHECK(seen[k]);
    start(7, PARTY_ROUND);
    for (i = 0; i < 40; i++) { seq2[i] = g.twist; next_round(); }
    CHECK(memcmp(seq, seq2, sizeof seq) == 0); /* same seed, same twists */
    start(8, PARTY_ROUND);
    for (i = 0; i < 40 && g.twist == seq[i]; i++) next_round();
    CHECK(i < 40); /* another seed differs somewhere */

    /* Twist effects at match start. */
    for (i = 0; i < 60; i++) {
        uint8_t t;
        start((uint32_t)(100 + i), PARTY_ROUND);
        t = g.twist;
        if (t == TWIST_ONE_GUM) CHECK(g.hero[0].balloons == 1 && g.cpu[0].balloons == 1);
        else CHECK(g.hero[0].balloons == FLIER_START_BALLOONS && g.cpu[0].balloons == FLIER_START_BALLOONS);
        CHECK(g.cpu_count == (t == TWIST_CROWDED ? CPU_MAX : CPU_START_COUNT));
        CHECK(g.ai[0].think_cut == (t == TWIST_SLOW ? -24 : t == TWIST_QUICK ? 18 : 0));
    }
    /* Other rules play as plain Arena and show name plus goal. */
    start(1, PARTY_ROOST);
    CHECK(g.twist == TWIST_NONE && g.cpu_count == CPU_START_COUNT && g.hero[0].balloons == FLIER_START_BALLOONS);
    CHECK(game_round_start_text(&g, 0) == game_party_name(PARTY_ROOST) && game_round_start_text(&g, 1) == game_party_goal(PARTY_ROOST));
    start(1, PARTY_NONE);
    CHECK(game_round_start_text(&g, 0) == 0);

    /* Mirror reverses left/right in play; the same input without the twist goes the other way. */
    for (i = 1; i < 200; i++) { start((uint32_t)i, PARTY_ROUND); if (g.twist == TWIST_MIRROR) break; }
    CHECK(g.twist == TWIST_MIRROR);
    {
        Game m = g, p;
        int32_t x0;
        air(&m);
        p = m; p.twist = TWIST_NONE;
        x0 = m.hero[0].x;
        for (k = 0; k < 20; k++) { game_step_arena(&m, IN_LEFT | IN_A); game_step_arena(&p, IN_LEFT | IN_A); }
        CHECK(m.hero[0].x > x0 && p.hero[0].x < x0);
    }
    /* Windy pushes an airborne flier with no input; no twist, no push. */
    for (i = 1; i < 300; i++) { start((uint32_t)i, PARTY_ROUND); if (g.twist == TWIST_WINDY) break; }
    CHECK(g.twist == TWIST_WINDY);
    {
        Game w = g, n;
        air(&w);
        n = w; n.twist = TWIST_NONE;
        for (k = 0; k < 10; k++) { game_step_arena(&w, 0); game_step_arena(&n, 0); }
        CHECK(w.hero[0].vx != 0 && n.hero[0].vx == 0);
    }
    printf("%d checks, %d failures\n", checks, failures);
    return failures != 0;
}
