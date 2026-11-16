/* Host test for the PARTY Roost Rule (game.c): the roost pick never repeats, a sole stander scores ticks, shared standing pays none,
 * a popped flier respawns by parachute, the round ends on the target or on time, and the first computer flier holds the island. */
#include <stdio.h>
#include "../../src/core/game.h"
#include "../../src/core/banner.h"
#include "../../src/core/stage.h"

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

static Game g;

static void start(void) {
    int i;
    game_reset(&g, 11);
    game_set_mode(&g, GAME_MODE_ARENA);
    g.party_rule = PARTY_ROOST;
    g.rounds = 1;
    for (i = 0; i < 600 && (g.cpu_count == 0 || g.round_start != RS_NONE); i++) game_step(&g, 0);
}

static void next_round(void) {
    int i;
    for (i = 0; i < 3000 && (g.round_end != RE_NONE || g.round_start != RS_NONE); i++) game_step(&g, 0);
}

/* Put fighter f standing on the roost, left of the platform centre by off pixels. */
static void stand(Flier *f, int off) {
    const StagePlatform *p = &stage_platforms[g.roost.idx];
    f->x = FL_PX(p->x + p->w / 2 + off);
    f->y = FL_PX(p->y) - flier_half_h(f);
    f->vx = 0; f->vy = 0; f->on_ground = 1; f->state = FLIER_ALIVE;
    f->invincible = 0; f->spawn_inv = 0;
}

static void away(Flier *f) { /* a computer flier out of play, not respawned */
    f->state = FLIER_ALIVE; f->x = 0; f->y = FL_PX(-200); f->vx = 0; f->vy = 0;
}

static void no_cpus(void) { /* cpu_count 0 would restart the match, so park every computer flier instead */
    int i;
    for (i = 0; i < g.cpu_count; i++) away(&g.cpu[i]);
}

int main(void) {
    int i, prev, ok, lives0;
    start();
    CHECK(g.mode == GAME_MODE_ARENA && g.party_rule == PARTY_ROOST);
    CHECK(stage_platforms[g.roost.idx].w > 0);
    CHECK(g.ai[0].hold == 1 && g.ai[1].hold == 0);
    CHECK(g.roost.timer == ROOST_ROUND_FRAMES);
    CHECK(game_round_start_text(&g, 1) != 0 && game_round_start_text(&g, 2) == 0);

    /* a sole human stander scores a tick every ROOST_TICK_FRAMES, and only through the tick */
    no_cpus();
    stand(&g.hero[0], 0);
    for (i = 0; i < ROOST_TICK_FRAMES * 3 + 5; i++) game_step(&g, 0);
    CHECK(g.roost.ticks[0] == 3 && g.score == 3 * SCORE_ROOST_TICK);
    CHECK(g.hero[0].state == FLIER_ALIVE && g.hero[0].on_ground);

    /* shared standing pays none: a computer flier joins the island */
    g.cpu_count = 1;
    stand(&g.cpu[0], 6);
    for (i = 0; i < ROOST_TICK_FRAMES * 3; i++) game_step(&g, 0);
    CHECK(g.roost.ticks[0] == 3 && g.roost.ticks[HUMANS] == 0 && g.score == 3 * SCORE_ROOST_TICK);

    /* a popped flier respawns by parachute */
    away(&g.cpu[0]);
    g.hero[0].state = FLIER_GONE;
    game_step(&g, 0);
    CHECK(g.hero[0].state == FLIER_PARACHUTE && g.hero[0].balloons == FLIER_START_BALLOONS);

    /* the target ends the round: P1 wins */
    start();
    no_cpus();
    g.roost.ticks[0] = ROOST_TARGET_TICKS - 1;
    stand(&g.hero[0], 0);
    for (i = 0; i < ROOST_TICK_FRAMES + 2 && g.round_end == RE_NONE; i++) game_step(&g, 0);
    CHECK(g.round_end == RE_HOLD && g.round_winner == BANNER_P1 && g.matches_won == 1);
    CHECK(game_banner_winner(&g) == BANNER_P1);

    /* a computer flier alone on the roost wins on target: the winner is the computer */
    start();
    g.cpu_count = 1;
    away(&g.hero[0]);
    g.roost.ticks[HUMANS] = ROOST_TARGET_TICKS - 1;
    stand(&g.cpu[0], 0);
    for (i = 0; i < ROOST_TICK_FRAMES + 2 && g.round_end == RE_NONE; i++) game_step(&g, 0);
    CHECK(g.round_end == RE_HOLD && g.round_winner == BANNER_CPU && g.score == 0);

    /* time ends the round: nobody scored, a draw */
    start();
    no_cpus();
    away(&g.hero[0]);
    g.roost.timer = 2;
    game_step(&g, 0); game_step(&g, 0);
    CHECK(g.round_end == RE_HOLD && g.round_winner == BANNER_DRAW);

    /* the roost never repeats back to back over many rounds */
    start();
    prev = g.roost.idx; ok = 1;
    for (i = 0; i < 12; i++) {
        no_cpus();
        away(&g.hero[0]);
        g.roost.timer = 1;
        game_step(&g, 0);
        next_round();
        if (g.roost.idx == prev) ok = 0;
        prev = g.roost.idx;
    }
    CHECK(ok);

    /* other score paths are shut in this rule: a human stomp on the computer flier pays nothing */
    start();
    {
        uint32_t before = g.score;
        g.cpu_count = 1;
        g.cpu[0].x = FL_PX(100); g.cpu[0].y = FL_PX(100); g.cpu[0].vx = 0; g.cpu[0].vy = 0;
        g.cpu[0].invincible = 0; g.cpu[0].spawn_inv = 0; g.cpu[0].balloons = 0; g.cpu[0].state = FLIER_FALLING;
        g.hero[0].x = FL_PX(100); g.hero[0].y = FL_PX(90); g.hero[0].vx = 0; g.hero[0].vy = FL_PX(1);
        for (i = 0; i < 20; i++) game_step(&g, 0);
        CHECK(g.score == before);
    }

    /* the match ends on the target score: over is set, the winner is the bird that reached it, no life is lost */
    start();
    lives0 = g.lives[0].lives;
    no_cpus();
    g.roost.total[0] = ROOST_TARGET_SCORE / SCORE_ROOST_TICK - 1;
    stand(&g.hero[0], 0);
    for (i = 0; i < ROOST_TICK_FRAMES + 2 && !g.over; i++) game_step(&g, 0);
    CHECK(g.over && g.round_winner == BANNER_P1 && g.lives[0].lives == lives0);
    {
        uint8_t frozen = g.roost.total[0];
        for (i = 0; i < ROOST_TICK_FRAMES * 2; i++) game_step(&g, 0);
        CHECK(g.over && g.roost.total[0] == frozen);
    }

    /* a computer-only race ends the match within a bounded stretch, and no life is lost */
    start();
    lives0 = g.lives[0].lives;
    for (i = 0; i < 60000 && !g.over; i++) { away(&g.hero[0]); game_step(&g, 0); }
    CHECK(g.over && g.round_winner == BANNER_CPU && g.lives[0].lives == lives0);

    printf("roost: %d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
