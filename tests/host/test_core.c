/* Host tests for the Roofline core. See run.sh. */
#include <stdio.h>
#include <string.h>
#include "../../src/core/game.h"
#include "../../src/core/hiscore.h"
#include "../../src/core/obstacle_view.h"

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

static void test_scripted_run(void)
{
    Game g;
    uint32_t f, prev_shots, prev_lives;
    uint16_t hit_frame_gap_min = 0xFFFF;
    uint32_t last_hit_frame = 0, lock_frames = 0, shots_in_lock = 0;
    game_reset(&g, 424242);
    CHECK(g.lives == LIVES_START);
    prev_lives = g.lives;
    for (f = 0; f < 60000 && !g.over; f++) {
        int locked = g.lockout > 1; /* at 1 the lockout ends inside this step */
        prev_shots = g.shots;
        game_step(&g, IN_A); /* hold fire, never dodge */
        if (locked) {
            lock_frames++;
            if (g.shots != prev_shots) shots_in_lock++;
        }
        CHECK(g.heat <= HEAT_MAX);
        if (g.lives != prev_lives) {
            CHECK(g.lives + 1 == prev_lives);
            if (last_hit_frame) {
                uint32_t gap = g.frame - last_hit_frame;
                if (gap < hit_frame_gap_min) hit_frame_gap_min = (uint16_t)gap;
            }
            last_hit_frame = g.frame;
            prev_lives = g.lives;
        }
    }
    CHECK(g.over);
    CHECK(g.lives == 0);
    CHECK(g.hits == LIVES_START);
    CHECK(g.kills > 0);
    CHECK(g.shots >= g.kills);
    CHECK(g.overheats > 0);
    CHECK(lock_frames > 0);
    CHECK(shots_in_lock == 0);
    CHECK(hit_frame_gap_min > INVULN_FRAMES);
    CHECK(g.score >= (uint32_t)KILL_SCORE * g.kills);
    CHECK(g.score == (g.distance >> (8 + DIST_SHIFT)) + g.bonus);
    {
        uint32_t s = g.score, fr = g.frame;
        game_step(&g, IN_A);
        CHECK(g.score == s && g.frame == fr); /* frozen after game over */
    }
    printf("run: frames=%u score=%u kills=%u shots=%u overheats=%u hits=%u spawned=%u\n",
           (unsigned)g.frame, (unsigned)g.score, (unsigned)g.kills, (unsigned)g.shots,
           (unsigned)g.overheats, (unsigned)g.hits, (unsigned)g.spawned);
}

static void test_mechanics(void)
{
    Game g;
    int x, y, w, h, i;
    /* jump, duck, hit boxes */
    game_reset(&g, 1);
    game_hero_box(&g, &x, &y, &w, &h);
    CHECK(y + h == GROUND_Y && h == HERO_H);
    game_step(&g, IN_C);
    game_hero_box(&g, &x, &y, &w, &h);
    CHECK(h == HERO_DUCK_H && y + h == GROUND_Y);
    game_step(&g, 0);
    game_step(&g, IN_B);
    CHECK(g.hero_h > 0);
    for (i = 0; i < 200 && g.hero_h > 0; i++) game_step(&g, 0);
    CHECK(g.hero_h == 0);
    /* a bolt kills a drone but passes through a vent */
    game_reset(&g, 1);
    g.obs[0] = (Obstacle){ (int32_t)(200 << 8), GROUND_Y - 46, 28, 20, OB_DRONE, 1, 0, 0 };
    g.obs[1] = (Obstacle){ (int32_t)(150 << 8), GROUND_Y - VENT_H, VENT_W, VENT_H, OB_VENT, 1, 0, 0 };
    g.spawn_acc = 0; g.next_gap = 60000;
    for (i = 0; i < 40; i++) game_step(&g, IN_A);
    CHECK(g.kills >= 1 && !g.obs[0].active);
    /* chain multiplier: second kill inside window scores 400 */
    game_reset(&g, 1);
    g.next_gap = 60000;
    g.bonus = 0;
    for (i = 0; i < 2; i++) {
        int k = g.kills;
        g.obs[i] = (Obstacle){ (int32_t)((130 + 60 * i) << 8), GROUND_Y - BOT_H, BOT_W, BOT_H, OB_BOT, 1, 0, 0 };
        (void)k;
    }
    for (i = 0; i < 40 && g.kills < 2; i++) game_step(&g, IN_A);
    CHECK(g.kills == 2 && g.bonus == (uint32_t)KILL_SCORE + (uint32_t)KILL_SCORE * (CHAIN_MAX >= 2 ? 2 : 1));
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

int main(int argc, char **argv)
{
    (void)argv;
    if (argc > 1) { /* digest mode: see knob_digest.c */
        return 2;
    }
    test_rng();
    test_hiscore();
    test_mechanics();
    test_scripted_run();
    test_obstacle_view();
    printf("test_core: %d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
