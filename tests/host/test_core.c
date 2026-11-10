/* Host tests for the Roofline core. See run.sh. */
#include <stdio.h>
#include <string.h>
#include "../../src/core/game.h"
#include "../../src/core/hiscore.h"
#include "../../src/core/obstacle_view.h"
#include "stomp_assist.h"

static int failures;
static int checks;
#define CHECK(c) do { checks++; if (!(c)) { failures++; printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

static void test_rng(void)
{
    Rng a, b, c;
    int i, same = 0;
    rng_seed(&a, 1234); rng_seed(&b, 1234); rng_seed(&c, 1235);
    for (i = 0; i < 1000; i++) {
        uint32_t x = rng_next(&a);
        CHECK(x == rng_next(&b));
        if (x == rng_next(&c)) same++;
    }
    CHECK(same < 5);
    rng_seed(&a, 0);
    CHECK(a.s != 0);
    CHECK(rng_next(&a) != 0);
    CHECK(rng_range(&a, 0) == 0);
    for (i = 0; i < 1000; i++) CHECK(rng_range(&a, 7) < 7);
    rng_seed(&a, 1); /* known first value of xorshift32 13/17/5 from seed 1 */
    CHECK(rng_next(&a) == 270369u);
}

static void test_hiscore(void)
{
    HiscoreTable t, u;
    uint8_t img[HISCORE_IMAGE_SIZE + 4];
    int i;
    hiscore_defaults(&t);
    CHECK(hiscore_insert(&t, "AAA", 5500) == 5);
    CHECK(hiscore_serialise(&t, img, sizeof(img)) == HISCORE_IMAGE_SIZE);
    CHECK(hiscore_serialise(&t, img, 10) == 0);
    /* explicit big-endian layout */
    CHECK(img[0] == 'R' && img[1] == 'O' && img[2] == 'O' && img[3] == 'F');
    CHECK(img[4] == 0 && img[5] == 1);
    CHECK(img[6 + 8] == 0 && img[6 + 9] == 0 && img[6 + 10] == 0x27 && img[6 + 11] == 0x10); /* 10000 */
    CHECK(hiscore_load(&u, img, sizeof(img)) == 1);
    CHECK(memcmp(&t, &u, sizeof(t)) == 0);
    CHECK(memcmp(u.name[5], "AAA     ", 8) == 0);

    /* corrupt: every single byte flip must be rejected */
    for (i = 0; i < (int)HISCORE_IMAGE_SIZE; i++) {
        HiscoreTable d, def;
        img[i] ^= 0x40;
        CHECK(hiscore_load(&d, img, HISCORE_IMAGE_SIZE) == 0);
        hiscore_defaults(&def);
        CHECK(memcmp(&d, &def, sizeof(d)) == 0);
        img[i] ^= 0x40;
    }
    CHECK(hiscore_load(&u, img, HISCORE_IMAGE_SIZE - 1) == 0); /* short */
    CHECK(hiscore_load(&u, img, HISCORE_IMAGE_SIZE) == 1);

    /* insert ranks */
    hiscore_defaults(&t);
    CHECK(hiscore_insert(&t, "TOP", 99999) == 0);
    CHECK(t.score[0] == 99999 && t.score[1] == 10000 && t.score[9] == 2000);
    hiscore_defaults(&t);
    CHECK(hiscore_insert(&t, "LAST", 1001) == 9);
    CHECK(t.score[9] == 1001 && memcmp(t.name[9], "LAST    ", 8) == 0);
    hiscore_defaults(&t);
    CHECK(hiscore_insert(&t, "LOW", 1000) == -1); /* tie with last ranks below */
    CHECK(hiscore_insert(&t, "LOW", 999) == -1);
    CHECK(hiscore_insert(&t, "ZERO", 0) == -1);
    CHECK(t.score[9] == 1000);
    hiscore_defaults(&t);
    CHECK(hiscore_insert(&t, "TIE", 10000) == 1); /* below the equal score */
    for (i = 1; i < HISCORE_ENTRIES; i++) CHECK(t.score[i - 1] >= t.score[i]);
    CHECK(hiscore_insert(&t, "TOOLONGNAME", 20000) == 0);
    CHECK(memcmp(t.name[0], "TOOLONGN", 8) == 0);
}

static void test_obstacle_view(void)
{
    int type;
    uint32_t f;
    for (type = OB_VENT; type <= OB_BOT; type++) {
        uint8_t seen[8] = {0};
        int distinct = 0, i;
        CHECK(obstacle_view_ticks((uint8_t)type) > 0);
        for (f = 0; f < 200; f++) {
            uint8_t fr = obstacle_view_frame((uint8_t)type, f, 4);
            CHECK(fr < 4);
            seen[fr] = 1;
        }
        for (i = 0; i < 4; i++) distinct += seen[i];
        CHECK(distinct == 4);                       /* animation really cycles through every frame */
        CHECK(obstacle_view_frame((uint8_t)type, 0, 1) == 0);
        CHECK(obstacle_view_frame((uint8_t)type, 7, 0) == 0);
        CHECK(obstacle_view_frame((uint8_t)type, obstacle_view_ticks((uint8_t)type), 2) == 1);
    }
    CHECK(obstacle_view_ticks(99) == 0 && obstacle_view_frame(99, 5, 4) == 0);
}

/* Arena scoring (design 3.3): one computer flier, the others inert, events through game_step_arena. */
static void arena_one_cpu(Game *g)
{
    game_reset(g, 77);
    game_step_arena(g, 0);              /* starts the match: cpu_count slots filled */
    g->cpu_count = 1;
    g->cpu_alive = 1;
}

static void arena_run(Game *g, int steps)
{
    int i;
    for (i = 0; i < steps && !g->over && g->matches_won == 0; i++) {
        game_step_arena(g, 0);
    }
}

static void test_arena_score(void)
{
    static Game g;
    uint32_t before;
    /* a player stomp pops a computer balloon: pop points only */
    arena_one_cpu(&g);
    before = g.score;
    CHECK(stomp_assist(&g));
    game_step_arena(&g, 0);
    CHECK(g.stomps == 1 && g.cpu[0].balloons == FLIER_START_BALLOONS - 1);
    CHECK(g.score - before == (uint32_t)SCORE_STOMP_POP);
    /* the last balloon: pop + defeat; the dead flier then falls out through the bottom, which pays nothing
       (fall points are for a living computer flier only, user decision 2026-11-10); match win, no balloon lost */
    arena_one_cpu(&g);
    g.cpu[0].balloons = 1;
    before = g.score;
    CHECK(stomp_assist(&g));
    game_step_arena(&g, 0);
    CHECK(g.cpu[0].state == FLIER_FALLING);
    CHECK(g.score - before == (uint32_t)(SCORE_STOMP_POP + SCORE_CPU_DEFEAT));
    g.cpu[0].x = FL_PX(100); g.cpu[0].y = FL_PX(100);   /* falling over the gap: into the water */
    flier_init(&g.flier, FL_PX(FLIER_START_X), FL_PX(FLIER_START_Y), FLIER_START_BALLOONS, 0);
    arena_run(&g, 3000);
    CHECK(g.matches_won == 1);
    CHECK(g.score - before == (uint32_t)(SCORE_STOMP_POP + SCORE_CPU_DEFEAT + SCORE_MATCH_WIN + SCORE_MATCH_CLEAN));
    /* the same match with a player balloon lost: no clean bonus */
    arena_one_cpu(&g);
    g.cpu[0].balloons = 0;
    g.cpu[0].x = FL_PX(100); g.cpu[0].y = FL_PX(100);   /* over the gap: falls into the water */
    flier_lose_balloon(&g.flier);
    arena_run(&g, 3000);
    CHECK(g.matches_won == 1);
    CHECK(g.score == (uint32_t)(SCORE_CPU_DROWN + SCORE_MATCH_WIN));
    /* body kill of a balloon-less standing computer flier by the player: defeat points */
    arena_one_cpu(&g);
    g.cpu[0].balloons = 0;
    g.flier.x = g.cpu[0].x; g.flier.y = g.cpu[0].y;
    g.flier.vx = 0; g.flier.vy = 0;
    before = g.score;
    game_step_arena(&g, 0);
    CHECK(g.cpu[0].state == FLIER_FALLING && g.bounces > 0);
    CHECK(g.score - before == (uint32_t)SCORE_CPU_DEFEAT);
    /* a computer flier stomping another computer flier scores nothing */
    game_reset(&g, 77);
    game_step_arena(&g, 0);
    g.cpu_count = 2;
    g.cpu[1].x = g.cpu[0].x; g.cpu[1].y = g.cpu[0].y - FL_PX(14);
    g.cpu[1].vx = 0; g.cpu[1].vy = 0;
    g.flier.x = FL_PX(100); g.flier.y = FL_PX(100);    /* player away over the gap */
    game_step_arena(&g, 0);
    CHECK(g.stomps >= 1 && g.score == 0);
}

/* Rematch (design N1a): a match win starts a fresh match, so the player is back on the spawn point with the
 * start values; nothing of the last match carries over (regression: only the balloons were topped up). */
static void test_arena_rematch(void)
{
    static Game g;
    arena_one_cpu(&g);
    g.cpu[0].balloons = 0;
    g.cpu[0].x = FL_PX(100); g.cpu[0].y = FL_PX(100);   /* over the gap: falls into the water */
    g.flier.x = FL_PX(FLIER_START_X + 40);              /* away from the spawn point, moving, facing left, hurt */
    g.flier.vx = -FL_PX(1);
    g.flier.facing = -1;
    flier_lose_balloon(&g.flier);
    arena_run(&g, 3000);
    CHECK(g.matches_won == 1 && !g.over);
    CHECK(g.flier.x == FL_PX(FLIER_START_X) && g.flier.y == FL_PX(FLIER_START_Y));
    CHECK(g.flier.vx == 0 && g.flier.vy == 0);
    CHECK(g.flier.state == FLIER_ALIVE && g.flier.balloons == FLIER_START_BALLOONS);
    CHECK(g.flier.invincible == 0 && g.flier.facing == 1);
    CHECK(g.cpu_count == CPU_START_COUNT + 1 && g.cpu[0].balloons == FLIER_START_BALLOONS);
}

int main(int argc, char **argv)
{
    (void)argv;
    if (argc > 1) { /* digest mode: see knob_digest.c */
        return 2;
    }
    test_rng();
    test_hiscore();
    test_obstacle_view();
    test_arena_score();
    test_arena_rematch();
    printf("test_core: %d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
