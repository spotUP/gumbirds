/* Host test for the two-player rules in game.c (Phase 1 of the co-op plan): partner stomps, per-player score and lives,
 * the run going on while one player is out and ending when both are, the stage clear with one human alive, 8 fighters in the pair pass. */
#include <stdio.h>
#include "../../src/core/game.h"
#include "../../src/core/stage.h"

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

static Game g;

static void start2(int stage) {
    game_reset(&g, 7);
    game_set_mode(&g, GAME_MODE_ARCADE);
    g.arc.stage = stage;
    game_step(&g, 0); /* builds the match */
    game_start_p2(&g);
}

static void ready(Flier *f, int x, int y, int vy) {
    f->x = FL_PX(x); f->y = FL_PX(y); f->vx = 0; f->vy = FL_PX(vy);
    f->invincible = 0; f->spawn_inv = 0;
}

int main(void) {
    int i, ended;

    /* start state */
    start2(1);
    CHECK(g.players == 2 && g.lives[1].state == ARC_LIFE_PLAY && g.lives[1].lives == ARC_LIVES_START);
    CHECK(g.hero[1].state == FLIER_ALIVE && g.hero[1].x != g.hero[0].x);

    /* friendly stomp: P2 lands on P1, one balloon, nobody scores */
    start2(1);
    ready(&g.hero[0], 192, 100, 0);
    ready(&g.hero[1], 192, 74, 1);
    game_step(&g, 0);
    CHECK(g.hero[0].balloons == FLIER_START_BALLOONS - 1 && g.hero[1].balloons == FLIER_START_BALLOONS);
    CHECK(g.score == 0 && g.lives[1].score == 0);
    start2(1);
    ready(&g.hero[1], 192, 100, 0);
    ready(&g.hero[0], 192, 74, 1);
    game_step(&g, 0);
    CHECK(g.hero[1].balloons == FLIER_START_BALLOONS - 1 && g.hero[0].balloons == FLIER_START_BALLOONS);
    CHECK(g.score == 0 && g.lives[1].score == 0);

    /* each score goes to its own player: body contact with a rival pays its toucher */
    start2(1);
    ready(&g.hero[0], 192, 20, 0);
    g.hero[1].x = g.cpu[0].x - FL_PX(6); g.hero[1].y = g.cpu[0].y; g.hero[1].vx = FL_PX(1); g.hero[1].vy = 0; g.hero[1].spawn_inv = 0;
    game_step(&g, 0);
    CHECK(g.lives[1].score > 0 && g.score == 0);
    start2(1);
    ready(&g.hero[1], 192, 20, 0);
    g.hero[0].x = g.cpu[0].x - FL_PX(6); g.hero[0].y = g.cpu[0].y; g.hero[0].vx = FL_PX(1); g.hero[0].vy = 0; g.hero[0].spawn_inv = 0;
    game_step(&g, 0);
    CHECK(g.score > 0 && g.lives[1].score == 0);

    /* 8 fighters fit the pair pass */
    CHECK(HUMANS + STAGE_SPAWN_COUNT <= 8);

    /* P1 loses the last life: CONTINUE shows, P2 plays on (world not frozen), run not over */
    start2(1);
    g.lives[0].lives = 1;
    g.hero[0].state = FLIER_GONE;
    game_step(&g, 0);
    CHECK(g.lives[0].state == ARC_LIFE_CONTINUE && !g.over && g.lives[1].state == ARC_LIFE_PLAY);
    {
        uint32_t st = g.flier_steps;
        game_step(&g, 0);
        CHECK(g.flier_steps == st + 1 && g.hero[0].state == FLIER_GONE);
    }
    for (i = 0; i < 700 && g.lives[0].state != ARC_LIFE_ENDED; i++) game_step(&g, 0);
    CHECK(g.lives[0].state == ARC_LIFE_ENDED && !g.over && g.hero[0].state == FLIER_GONE && g.hero[1].state != FLIER_GONE);

    /* P1 out, P2 clears the stage: P2 gets the match bonus, P1 stays out, P2 lives on */
    {
        uint32_t s2 = g.lives[1].score, s1 = g.score;
        for (i = 0; i < g.cpu_count; i++) g.cpu[i].state = FLIER_GONE;
        g.cpu_alive = 0;
        game_step(&g, 0);
        CHECK(g.lives[1].score >= s2 + SCORE_MATCH_WIN && g.score == s1);
        for (i = 0; i < 400; i++) game_step(&g, 0);
        CHECK(g.arc.stage >= 2 && g.hero[0].state == FLIER_GONE && g.hero[1].state != FLIER_GONE && !g.over);
    }

    /* both out: over once the second countdown ends */
    g.lives[1].lives = 1;
    g.hero[1].state = FLIER_GONE;
    game_step(&g, 0);
    CHECK(g.lives[1].state == ARC_LIFE_CONTINUE && !g.over);
    ended = 0;
    for (i = 0; i < 700 && !g.over; i++) game_step(&g, 0);
    ended = g.lives[1].state == ARC_LIFE_ENDED;
    CHECK(g.over && ended && g.lives[0].state == ARC_LIFE_ENDED);

    /* a partner on the continue screen continues with its own Start while the other plays */
    start2(1);
    g.lives[0].lives = 1;
    g.hero[0].state = FLIER_GONE;
    game_step(&g, 0);
    g.start_in[0] = 1;
    game_step(&g, 0);
    g.start_in[0] = 0;
    CHECK(g.lives[0].state == ARC_LIFE_PLAY && g.hero[0].state != FLIER_GONE);

    printf("%d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
