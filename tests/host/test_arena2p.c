/* Host test for Arena two-player versus (game.c): P2 Start banked, P2 appears at the next round, a human stomp on a human scores,
 * the round ends when one flier is left (winner P1, P2 or computer), a dead human waits for the next round. */
#include <stdio.h>
#include "../../src/core/game.h"
#include "../../src/core/banner.h"
#include "../../src/core/stage.h"

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

static Game g;

static void start1(void) {
    int i;
    game_reset(&g, 7);
    game_set_mode(&g, GAME_MODE_ARENA);
    g.rounds = 1;
    for (i = 0; i < 600 && (g.cpu_count == 0 || g.round_start != RS_NONE); i++) game_step(&g, 0);
}

static void kill_cpus(void) {
    int i;
    for (i = 0; i < g.cpu_count; i++) g.cpu[i].state = FLIER_GONE;
}

static void next_round(void) { /* step through the hold, the pan and the round start text */
    int i;
    for (i = 0; i < 3000 && (g.round_end != RE_NONE || g.round_start != RS_NONE); i++) game_step(&g, 0);
}

static void ready(Flier *f, int x, int y, int vy) {
    f->x = FL_PX(x); f->y = FL_PX(y); f->vx = 0; f->vy = FL_PX(vy);
    f->invincible = 0; f->spawn_inv = 0;
}

static void start2(void) { /* banked join, round won by P1, P2 in at the next round */
    start1();
    game_join_p2(&g);
    kill_cpus();
    game_step(&g, 0);
    next_round();
}

int main(void) {
    uint32_t s1;
    start1();
    CHECK(g.players == 1 && game_can_join_p2(&g) && !game_lives_mode(&g));
    CHECK(game_join_p2(&g) == 1);
    CHECK(g.players == 1 && g.p2_pending && g.hero[1].state == FLIER_GONE); /* banked, not in play mid-round */
    CHECK(!game_can_join_p2(&g)); /* one bank at a time */
    kill_cpus();
    game_step(&g, 0);
    CHECK(g.round_end == RE_HOLD && g.round_winner == BANNER_P1 + 0 && g.players == 1);
    next_round();
    CHECK(g.players == 2 && !g.p2_pending && g.hero[1].state == FLIER_ALIVE && g.lives[1].lives == ARC_LIVES_START && g.cpu_count > 0);
    CHECK(!game_can_join_p2(&g) && game_lives_mode(&g));

    /* Gum Trip stays one player */
    game_reset(&g, 7);
    game_set_mode(&g, GAME_MODE_TRIP);
    g.rounds = 1;
    CHECK(!game_can_join_p2(&g));

    /* human on human stomp scores like a computer stomp (P2 lands on P1, then P1 lands on P2) */
    start2();
    g.cpu[0].x = FL_PX(20); g.cpu[0].y = FL_PX(20); g.cpu[0].vx = 0; g.cpu[0].vy = 0;
    ready(&g.hero[0], 192, 100, 0);
    ready(&g.hero[1], 192, 74, 1);
    s1 = g.lives[1].score;
    game_step(&g, 0);
    CHECK(g.hero[0].balloons == FLIER_START_BALLOONS - 1 && g.lives[1].score == s1 + SCORE_STOMP_POP);
    ready(&g.hero[1], 192, 100, 0);
    ready(&g.hero[0], 192, 74, 1);
    s1 = g.score;
    game_step(&g, 0);
    CHECK(g.hero[1].balloons == FLIER_START_BALLOONS - 1 && g.score == s1 + SCORE_STOMP_POP);

    /* round ends with one flier left; a dead human costs one life and waits for the next round */
    start2();
    game_step(&g, 0);
    CHECK(g.round_end == RE_NONE); /* P1 + P2 + computer fliers */
    g.hero[1].state = FLIER_GONE;
    game_step(&g, 0);
    CHECK(g.lives[1].lives == ARC_LIVES_START - 1 && g.round_end == RE_NONE); /* P1 + computer left: play on */
    game_step(&g, 0);
    CHECK(g.lives[1].lives == ARC_LIVES_START - 1 && g.hero[1].state == FLIER_GONE); /* charged once, no respawn mid-round */
    kill_cpus();
    game_step(&g, 0);
    CHECK(g.round_end == RE_HOLD && g.round_winner == BANNER_P1);
    next_round();
    CHECK(g.hero[1].state == FLIER_ALIVE && g.hero[0].state == FLIER_ALIVE);

    start2();
    g.hero[0].state = FLIER_GONE; /* P2 + the computer fliers left; then only P2 */
    game_step(&g, 0);
    CHECK(g.round_end == RE_NONE);
    kill_cpus();
    game_step(&g, 0);
    CHECK(g.round_end == RE_HOLD && g.round_winner == BANNER_P2);

    start2();
    g.hero[0].state = FLIER_GONE;
    g.hero[1].state = FLIER_GONE; /* no human left: the computer wins the round */
    game_step(&g, 0);
    CHECK(g.round_end == RE_HOLD && g.round_winner == BANNER_CPU);

    /* a continue in versus: P2 out of lives, Start with a credit takes it, back in at the next round only */
    start2();
    g.lives[1].lives = 1;
    g.hero[1].state = FLIER_GONE;
    game_step(&g, 0);
    game_step(&g, 0);
    CHECK(g.lives[1].state == ARC_LIFE_CONTINUE);
    g.credits = 1; g.start_in[1] = 1;
    game_step(&g, 0);
    g.start_in[1] = 0;
    CHECK(g.credits_spent == 1 && g.lives[1].state == ARC_LIFE_PLAY && g.hero[1].state == FLIER_GONE);
    kill_cpus();
    game_step(&g, 0);
    next_round();
    CHECK(g.hero[1].state == FLIER_ALIVE);

    printf("%d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
