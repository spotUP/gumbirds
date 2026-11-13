/* Host tests for the Bubblegum Brawl core. See run.sh. */
#include <stdio.h>
#include <string.h>
#include "../../src/core/game.h"
#include "../../src/core/hiscore.h"
#include "../../src/core/obstacle_view.h"
#include "../../src/core/nameentry.h"
#include "../../src/core/stage.h"
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
    g->pump[0].state = ARC_PUMP_FLYING; /* the spawn pump (a still, harmless rival) has its own tests; these start in flight */
    g->flier.spawn_inv = 0;             /* spawn protection (BR-D5) would turn every computer pop of the player into a bounce; its own tests keep it */
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
    /* broad phase across the seam: player at x 383, computer flier at x 1 (2 px apart) is a stomp pair */
    arena_one_cpu(&g);
    g.cpu[0].x = FL_PX(1); g.cpu[0].y = FL_PX(100); g.cpu[0].vx = 0; g.cpu[0].vy = 0;
    g.flier.x = FL_PX(383); g.flier.y = FL_PX(100 - 26); g.flier.vx = 0; g.flier.vy = FL_PX(1);
    before = g.stomps;
    game_step_arena(&g, 0);
    CHECK(g.stomps == before + 1);
    /* the last balloon: pop + defeat; the dead flier then falls out through the bottom, which pays nothing
       (fall points are for a living computer flier only, user decision 2026-11-10); match win, no balloon lost */
    arena_one_cpu(&g);
    g.cpu[0].balloons = 1;
    before = g.score;
    CHECK(stomp_assist(&g));
    game_step_arena(&g, 0);
    CHECK(g.cpu[0].state == FLIER_FALLING);
    CHECK(g.score - before == (uint32_t)(SCORE_STOMP_POP + SCORE_CPU_DEFEAT));
    g.cpu[0].x = FL_PX(120); g.cpu[0].y = FL_PX(100);   /* falling over the gap: into the water */
    flier_init(&g.flier, FL_PX(FLIER_START_X), FL_PX(FLIER_START_Y), FLIER_START_BALLOONS, 0);
    arena_run(&g, 3000);
    CHECK(g.matches_won == 1);
    CHECK(g.score - before == (uint32_t)(SCORE_STOMP_POP + SCORE_CPU_DEFEAT + SCORE_MATCH_WIN + SCORE_MATCH_CLEAN));
    /* the same match with a player balloon lost: no clean bonus */
    arena_one_cpu(&g);
    g.cpu[0].balloons = 0;
    g.cpu[0].x = FL_PX(120); g.cpu[0].y = FL_PX(100);   /* over the gap: falls into the water */
    flier_lose_balloon(&g.flier);
    arena_run(&g, 3000);
    CHECK(g.matches_won == 1);
    CHECK(g.score == (uint32_t)(SCORE_CPU_DROWN + SCORE_MATCH_WIN));
    /* body kill of a balloon-less standing computer flier by the player: defeat points */
    arena_one_cpu(&g);
    g.cpu[0].balloons = 0;
    g.flier.x = g.cpu[0].x; g.flier.y = g.cpu[0].y;
    g.flier.x += FL_PX(3); g.flier.vx = -FL_PX(1); g.flier.vy = 0;
    before = g.score;
    game_step_arena(&g, 0);
    CHECK(g.cpu[0].state == FLIER_FALLING && g.bounces > 0);
    CHECK(g.score - before == (uint32_t)SCORE_CPU_DEFEAT);
    /* a computer flier above another computer flier: a bounce, no pop, nothing scored (BR-D3; was: counted as a stomp) */
    game_reset(&g, 77);
    game_step_arena(&g, 0);
    g.cpu_count = 2;
    g.pump[0].state = g.pump[1].state = ARC_PUMP_FLYING;
    g.cpu[1].x = g.cpu[0].x; g.cpu[1].y = g.cpu[0].y - FL_PX(26);
    g.cpu[1].vx = 0; g.cpu[1].vy = 0;
    g.flier.x = FL_PX(100); g.flier.y = FL_PX(100);    /* player away over the gap */
    game_step_arena(&g, 0);
    CHECK(g.stomps == 0 && g.bounces >= 1 && g.score == 0);
}

/* BR-D3: computer fliers never pop each other, they bounce. Two computer fliers in the exact pop geometry of
 * test_ai (upper one 26 px above, closing); the control puts the player on top in the same geometry: that pops. */
static void test_arena_cpu_no_pop(void)
{
    static Game g;
    uint32_t b0;
    int32_t vy_before;
    arena_one_cpu(&g);
    g.cpu_count = 2; g.cpu_alive = 2;
    g.cpu[1] = g.cpu[0];
    g.pump[1] = g.pump[0];
    g.flier.x = FL_PX(300); g.flier.y = FL_PX(100);    /* player away, clear of every island (at x 100 the whole-flier island box shoves it 21 px into the pair) */
    g.cpu[0].x = FL_PX(120); g.cpu[0].y = FL_PX(100); g.cpu[0].vx = 0; g.cpu[0].vy = 0; g.cpu[0].on_ground = 0; g.cpu[0].invincible = 0;
    g.cpu[1].x = FL_PX(120); g.cpu[1].y = FL_PX(100 - 26); g.cpu[1].vx = 0; g.cpu[1].vy = FL_PX(1); g.cpu[1].on_ground = 0; g.cpu[1].invincible = 0;
    vy_before = g.cpu[1].vy;
    b0 = g.bounces;
    game_step_arena(&g, 0);
    CHECK(g.cpu[0].balloons == FLIER_START_BALLOONS && g.cpu[1].balloons == FLIER_START_BALLOONS);
    CHECK(g.stomps == 0 && g.bounces > b0);
    CHECK(g.cpu[1].vy < 0 && g.cpu[1].vy != vy_before);   /* reflected, not left falling through */
    /* control: the player in the cpu 1 spot, cpu 0 below, same numbers: a pop */
    arena_one_cpu(&g);
    g.cpu[0].x = FL_PX(120); g.cpu[0].y = FL_PX(100); g.cpu[0].vx = 0; g.cpu[0].vy = 0; g.cpu[0].on_ground = 0; g.cpu[0].invincible = 0;
    g.flier.x = FL_PX(120); g.flier.y = FL_PX(100 - 26); g.flier.vx = 0; g.flier.vy = FL_PX(1); g.flier.on_ground = 0;
    b0 = g.stomps;
    game_step_arena(&g, 0);
    CHECK(g.stomps == b0 + 1 && g.cpu[0].balloons == FLIER_START_BALLOONS - 1);
}

/* Rematch (design N1a): a match win starts a fresh match, so the player is back on the spawn point with the
 * start values; nothing of the last match carries over (regression: only the balloons were topped up). */
static void test_arena_rematch(void)
{
    static Game g;
    arena_one_cpu(&g);
    g.cpu[0].balloons = 0;
    g.cpu[0].x = FL_PX(120); g.cpu[0].y = FL_PX(100);   /* over the gap: falls into the water */
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
    CHECK(g.flier.spawn_inv == FLIER_SPAWN_INVINCIBLE);   /* the rematch spawn is protected again (BR-D5) */
    game_step_arena(&g, 0);
    CHECK(g.flier.spawn_inv == FLIER_SPAWN_INVINCIBLE - 1 && g.flier.invincible == 0);
    CHECK(g.cpu_count == CPU_START_COUNT + 1 && g.cpu[0].balloons == FLIER_START_BALLOONS);
}

/* Round end (real game, Game.rounds = 1): a win holds the banner (RE_HOLD) for MATCH_END_FRAMES, then pans (RE_PAN, flier hidden)
 * until the camera arrives, then the next round starts frozen on ROUND nn and GO!. Game.frame keeps counting. */
static void win_round(Game *g)
{
    g->cpu[0].balloons = 0;
    g->cpu[0].x = FL_PX(120); g->cpu[0].y = FL_PX(100);
    arena_run(g, 3000);
}

static void test_round_end(void)
{
    static Game g;
    int i, n;
    uint32_t score0, score1, frame0, steps0;
    game_reset(&g, 77);
    g.rounds = 1;
    game_step_arena(&g, 0);
    CHECK(g.round_start == RS_ROUND && game_hazards_frozen(&g) && game_round_number(&g) == 1);   /* round 1 is frozen too */
    for (i = 0; i < ROUND_START_TEXT_FRAMES + ROUND_GO_TEXT_FRAMES + 2 && g.round_start != RS_NONE; i++) {
        steps0 = g.flier_steps;
        game_step_arena(&g, IN_A | IN_RIGHT);
        CHECK(g.flier_steps == steps0 || g.round_start == RS_NONE);   /* input ignored while frozen */
    }
    CHECK(g.round_start == RS_NONE && !game_hazards_frozen(&g));
    g.cpu_count = 1; g.cpu_alive = 1; g.flier.spawn_inv = 0;
    /* ROUND exactly 60 frames, GO exactly 30: count them on a second reset */
    game_reset(&g, 78);
    g.rounds = 1;
    game_step_arena(&g, 0);
    for (n = 1; g.round_start == RS_ROUND; n++) game_step_arena(&g, 0);
    CHECK(n == ROUND_START_TEXT_FRAMES);                /* the first step above counts as frame 1 */
    for (n = 1; g.round_start == RS_GO; n++) game_step_arena(&g, 0);
    CHECK(n == ROUND_GO_TEXT_FRAMES + 1);
    g.cpu_count = 1; g.cpu_alive = 1; g.flier.spawn_inv = 0;
    score0 = g.score;
    win_round(&g);
    CHECK(g.matches_won == 1 && g.round_end == RE_HOLD && !g.over);
    CHECK(g.score >= score0 + SCORE_MATCH_WIN + SCORE_MATCH_CLEAN);                       /* win bonus counted at win time */
    score1 = g.score;
    CHECK(game_flier_visible(&g) && game_hazards_frozen(&g));                              /* HOLD: flier shown */
    g.flier.x = FL_PX(FLIER_START_X + 40);                                                /* away from the spawn */
    steps0 = g.flier_steps; frame0 = g.frame;
    for (i = 0; i < MATCH_END_FRAMES - 1; i++) game_step_arena(&g, 0);
    CHECK(g.round_end == RE_HOLD && g.round_timer == 1);
    game_step_arena(&g, 0);
    CHECK(g.round_end == RE_PAN && !game_flier_visible(&g));                                /* exactly MATCH_END_FRAMES steps */
    CHECK(g.flier.x == FL_PX(FLIER_START_X) && g.score == score1);                                      /* not counted again */
    for (i = 0; i < 2000 && g.round_end == RE_PAN; i++) game_step_arena(&g, 0);
    CHECK(g.round_end == RE_NONE && i < 2000);
    CHECK(g.flier_steps == steps0 && g.frame > frame0 + MATCH_END_FRAMES);               /* flier frozen, frame kept counting */
    CHECK(g.cpu_count == CPU_START_COUNT + 1 && g.round_start == RS_ROUND && game_round_number(&g) == 2);
    CHECK(g.flier.spawn_inv == FLIER_SPAWN_INVINCIBLE && game_flier_visible(&g));
}

/* BR-D1: a solid island between two fliers blocks the pop. The middle island {128, 108, 112} carries the player on top; a
 * computer flier hangs 26 px below its centre line, inside the island's x range, so the 26 px pop geometry of
 * test_arena_art_boxes would pop it if the island were not between them. Control: the same geometry at x 20, where no island
 * lies between the two centres, pops. */
static void test_arena_platform_block(void)
{
    static Game g;
    uint32_t pairs, blocked, b0;
    const StagePlatform *mid = &stage_platforms[2];
    arena_one_cpu(&g);
    /* The whole flier (gum included) is solid, so no flier can sit under the island within pop reach of one standing on it; the
     * only contact left across an island is at its corner: the player stands 4 px inside the left end, the computer flier hangs
     * beside the left face, 13 px away and about 22 px lower, and the line between their centres cuts the island corner. */
    g.cpu[0].x = FL_PX(mid->x - 9); g.cpu[0].y = FL_PX(mid->y + 16); g.cpu[0].vx = 0; g.cpu[0].vy = -FL_PX(1);   /* rising toward the island */ g.cpu[0].on_ground = 0; g.cpu[0].invincible = 0;
    g.flier.x = FL_PX(mid->x + 4); g.flier.y = FL_PX(mid->y - 6); g.flier.vx = 0; g.flier.vy = 0; g.flier.on_ground = 0;   /* standing on the island */
    pairs = g_flier_pair_calls; blocked = g_flier_pair_blocked; b0 = g.bounces;
    game_step_arena(&g, 0);
    CHECK(g_flier_pair_calls > pairs);                     /* the pair reached flier_pair: it is the block that stops the pop */
    CHECK(g_flier_pair_blocked > blocked);
    CHECK(g.stomps == 0 && g.bounces == b0);
    CHECK(g.cpu[0].balloons == FLIER_START_BALLOONS && g.flier.balloons == FLIER_START_BALLOONS);
    /* control: same offsets with no island between */
    arena_one_cpu(&g);
    g.cpu[0].x = FL_PX(20); g.cpu[0].y = FL_PX(100); g.cpu[0].vx = 0; g.cpu[0].vy = 0; g.cpu[0].on_ground = 0; g.cpu[0].invincible = 0;
    g.flier.x = FL_PX(20); g.flier.y = FL_PX(100 - 26); g.flier.vx = 0; g.flier.vy = FL_PX(1); g.flier.on_ground = 0;
    blocked = g_flier_pair_blocked;
    game_step_arena(&g, 0);
    CHECK(g.stomps == 1 && g.cpu[0].balloons == FLIER_START_BALLOONS - 1 && g_flier_pair_blocked == blocked);
}

/* BR-D5: the player starts protected. Idle, a computer flier above in pop geometry only bounces off; the first left, right or
 * flap press ends the protection at once. */
static void test_arena_spawn_invincible(void)
{
    static Game g;
    int i;
    uint32_t before;
    game_reset(&g, 77);
    game_step_arena(&g, 0);
    g.cpu_count = 1; g.cpu_alive = 1; g.pump[0].state = ARC_PUMP_FLYING;
    CHECK(g.flier.spawn_inv == FLIER_SPAWN_INVINCIBLE - 1);
    for (i = 0; i < 10; i++) {
        g.cpu[0].x = g.flier.x; g.cpu[0].y = g.flier.y - FL_PX(26); g.cpu[0].vx = 0; g.cpu[0].vy = FL_PX(1); g.cpu[0].on_ground = 0; g.cpu[0].invincible = 0;
        game_step_arena(&g, 0);
    }
    CHECK(g.flier.balloons == FLIER_START_BALLOONS && g.stomps == 0 && g.flier.spawn_inv == FLIER_SPAWN_INVINCIBLE - 11);
    before = g.stomps;
    g.cpu[0].x = g.flier.x; g.cpu[0].y = g.flier.y - FL_PX(26); g.cpu[0].vx = 0; g.cpu[0].vy = FL_PX(1); g.cpu[0].on_ground = 0; g.cpu[0].invincible = 0;
    game_step_arena(&g, IN_RIGHT);
    CHECK(g.flier.spawn_inv == 0 && g.stomps == before + 1 && g.flier.balloons == FLIER_START_BALLOONS - 1);   /* ends on the input frame, so the same frame's contact pops */
}

/* Gum contact table through the real game_step_arena: a player beside a computer flier, higher by 16 px, pops its balloon
 * (body into gum from the side, 12 px apart); level, the two bounce and nothing is lost. flier_pair must have run. */
static void test_arena_side_contact(void)
{
    static Game g;
    uint32_t before, calls, score;
    arena_one_cpu(&g);
    g.cpu[0].x = FL_PX(120); g.cpu[0].y = FL_PX(100); g.cpu[0].vx = 0; g.cpu[0].vy = 0; g.cpu[0].on_ground = 0;
    g.cpu[0].invincible = 0;
    g.flier.x = FL_PX(132); g.flier.y = FL_PX(100 - 16); g.flier.vx = 0; g.flier.vy = FL_PX(1); g.flier.invincible = 0;
    before = g.stomps; calls = g_flier_pair_calls; score = g.score;
    game_step_arena(&g, 0);
    CHECK(g_flier_pair_calls > calls);
    CHECK(g.stomps == before + 1 && g.cpu[0].balloons == FLIER_START_BALLOONS - 1);
    CHECK(g.score - score == (uint32_t)SCORE_STOMP_POP);
    /* level, 10 px apart: both bounce away from each other, no balloon changes, no score */
    arena_one_cpu(&g);
    g.cpu[0].x = FL_PX(120); g.cpu[0].y = FL_PX(100); g.cpu[0].vx = FL_PX(1); g.cpu[0].vy = 0; g.cpu[0].on_ground = 0;
    g.cpu[0].invincible = 0;
    g.flier.x = FL_PX(130); g.flier.y = FL_PX(100); g.flier.vx = -FL_PX(1); g.flier.vy = 0; g.flier.invincible = 0;
    before = g.stomps; calls = g_flier_pair_calls; score = g.score;
    game_step_arena(&g, 0);
    CHECK(g_flier_pair_calls > calls);
    CHECK(g.stomps == before && g.flier.balloons == FLIER_START_BALLOONS && g.cpu[0].balloons == FLIER_START_BALLOONS);
    CHECK(g.score == score);
    CHECK(g.flier.vx > 0 && g.cpu[0].vx < 0);
}

/* User decision 2026-11-10, B: the stomp boxes follow the drawn art, for player and computer alike, through the real
 * game_step_arena broad phase. The attacker's feet are 9 px beside the victim (18 half pixels): the old broad phase
 * (9 half pixels) skipped that pair; the drawn gum is 17 px wide (reach 20 half pixels), so it is a real stomp. */
static void test_arena_art_boxes(void)
{
    static Game g;
    uint32_t before;
    /* player attacker, computer victim */
    arena_one_cpu(&g);
    g.cpu[0].x = FL_PX(120); g.cpu[0].y = FL_PX(100); g.cpu[0].vx = 0; g.cpu[0].vy = 0; g.cpu[0].on_ground = 0;
    g.cpu[0].invincible = 0;
    g.flier.x = FL_PX(129); g.flier.y = FL_PX(100 - 26); g.flier.vx = 0; g.flier.vy = FL_PX(1);
    before = g.stomps;
    game_step_arena(&g, 0);
    CHECK(g.stomps == before + 1 && g.cpu[0].balloons == FLIER_START_BALLOONS - 1);
    /* the mirror: computer attacker, player victim, identical offsets */
    arena_one_cpu(&g);
    g.flier.x = FL_PX(120); g.flier.y = FL_PX(100); g.flier.vx = 0; g.flier.vy = 0; g.flier.on_ground = 0;
    g.flier.invincible = 0;
    g.cpu[0].x = FL_PX(129); g.cpu[0].y = FL_PX(100 - 26); g.cpu[0].vx = 0; g.cpu[0].vy = FL_PX(1); g.cpu[0].on_ground = 0;
    before = g.stomps;
    game_step_arena(&g, 0);
    CHECK(g.stomps == before + 1 && g.flier.balloons == FLIER_START_BALLOONS - 1);
    /* (both lowered and moved left to clear the islands, whose solid box now covers the gum) 16 px beside the victim: the attacker's body (7) is clear of the gum (9), no pop; 15 px still pops */
    arena_one_cpu(&g);
    g.cpu[0].x = FL_PX(60); g.cpu[0].y = FL_PX(136); g.cpu[0].vx = 0; g.cpu[0].vy = 0; g.cpu[0].on_ground = 0;
    g.flier.x = FL_PX(76); g.flier.y = FL_PX(136 - 26); g.flier.vx = 0; g.flier.vy = FL_PX(1);
    before = g.stomps;
    game_step_arena(&g, 0);
    CHECK(g.stomps == before);
    arena_one_cpu(&g);
    g.cpu[0].x = FL_PX(60); g.cpu[0].y = FL_PX(136); g.cpu[0].vx = 0; g.cpu[0].vy = 0; g.cpu[0].on_ground = 0;
    g.flier.x = FL_PX(75); g.flier.y = FL_PX(136 - 26); g.flier.vx = 0; g.flier.vy = FL_PX(1);
    before = g.stomps;
    game_step_arena(&g, 0);
    CHECK(g.stomps == before + 1);
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
    test_round_end();
    test_arena_art_boxes();
    test_arena_side_contact();
    test_arena_cpu_no_pop();
    test_arena_platform_block();
    test_arena_spawn_invincible();
    printf("test_core: %d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
