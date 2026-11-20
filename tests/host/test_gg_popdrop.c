/* test_gg_popdrop.c - Gum Games Pop Drop (free fall): speed ramp, steering and facing, platform hit (stun, gum lost, shield soak), crash on the third hit,
 * score = depth + gums, 2P simultaneous fall (push apart, ghost, hop without brake, end when both crashed), game and flow wiring. */
#include <stdio.h>
#include "gg_popdrop.h"
#include "arena.h"
#include "game.h"
#include "flow.h"

static int fails;
#define CHECK(c) do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); fails++; } } while (0)

/* Put one platform right on the bird (x centred on it) so the next step is a hit. */
static void plat_on_bird(GgPop *p, const Flier *h)
{
    int i;
    for (i = 0; i < PD_PLATS; i++) p->plat[i].live = 0;
    p->plat[0].kind = PD_ROCK; p->plat[0].mids = 1; p->plat[0].live = 1; p->plat[0].hit = 0;
    p->plat[0].x = (int16_t)((h->x >> 16) - 24); p->plat[0].y = PD_BIRD_Y;
}

int main(void)
{
    GgPop p; Flier h[2]; int i; uint16_t s0;

    /* start: falling, speeds up, depth and score grow, no platform hit while the field is empty of platforms in reach */
    gp_init(&p, h, 7);
    CHECK(p.phase == PD_FALL && p.b[0].hits == 0 && p.seq.players == 1 && p.seq.tickets[0] == 1);
    s0 = p.spd;
    for (i = 0; i < 100; i++) gp_step(&p, h, 0, 0);
    CHECK(p.spd > s0 && p.spd <= PD_SPEED_MAX && p.depth > 0 && p.b[0].score >= p.depth);

    /* steering and facing */
    gp_init(&p, h, 7);
    { int32_t x0 = h[0].x; for (i = 0; i < 20; i++) gp_step(&p, h, IN_LEFT, 0); CHECK(h[0].x < x0 && p.b[0].flip == 1);
      for (i = 0; i < 40; i++) gp_step(&p, h, IN_RIGHT, 0); CHECK(h[0].x > x0 && p.b[0].flip == 0); }

    /* a hit: stun, one gum lost, bounce, speed loss; steering locked while stunned */
    gp_init(&p, h, 7);
    p.b[0].gums = 3; p.spd = 100; plat_on_bird(&p, h);
    gp_step(&p, h, 0, 0);
    CHECK(p.b[0].hits == 1 && p.b[0].stun > 0 && p.b[0].gums == 2 && p.spd < 100 && p.b[0].bounce < 0);
    { int32_t x0 = h[0].x; gp_step(&p, h, IN_LEFT, 0); CHECK(h[0].x >= x0 - FL_PX(1) && p.b[0].flip == 0); }

    /* a shield soaks the hit: no hit counted, no stun, shield gone */
    gp_init(&p, h, 7);
    p.b[0].shield = 1; plat_on_bird(&p, h);
    gp_step(&p, h, 0, 0);
    CHECK(p.b[0].hits == 0 && p.b[0].stun == 0 && p.b[0].shield == 0 && p.b[0].pop_t > 0);

    /* every 10 gums raise a shield */
    gp_init(&p, h, 7);
    for (i = 0; i < (int)PD_SHIELD_EVERY; i++) {
        p.gum[0].x = (int16_t)(h[0].x >> 16); p.gum[0].y = PD_BIRD_Y; p.gum[0].live = 1;
        { int k; for (k = 0; k < PD_PLATS; k++) p.plat[k].live = 0; }
        gp_step(&p, h, 0, 0);
    }
    CHECK(p.b[0].gums == (uint16_t)PD_SHIELD_EVERY && p.b[0].shield == 1 && p.b[0].shield_count == 0);

    /* three hits crash; the attempt ends with the score, then the result, then done */
    gp_init(&p, h, 7);
    for (i = 0; i < 3; i++) { p.b[0].stun = 0; plat_on_bird(&p, h); gp_step(&p, h, 0, 0); }
    CHECK(p.b[0].hits == 3 && p.phase == PD_CRASH);
    { int ret = 0, n; for (n = 0; n < 400 && !ret; n++) ret = gp_step(&p, h, 0, 0);
      CHECK(ret == 1 && p.done && p.phase == PD_RESULT && p.seq.best[0] == p.last_score); }

    /* 2P: both birds fall at once, side by side, each with its own state */
    gp_init(&p, h, 7); gp_add_p2(&p, &h[0], &h[1]);
    CHECK(p.seq.players == 2 && p.seq.tickets[1] == 1 && arena_dx(h[1].x >> 16, h[0].x >> 16) == PD_P2_GAP && p.b[1].flip == 1);
    for (i = 0; i < 10; i++) gp_step(&p, h, IN_LEFT, IN_RIGHT);
    CHECK(p.b[0].flip == 1 && p.b[1].flip == 0 && arena_dx(h[1].x >> 16, h[0].x >> 16) > PD_P2_GAP);

    /* 2P push apart: overlapping birds separate, no damage; the faster mover hands the slower its speed (pushes harder) */
    gp_init(&p, h, 7); gp_add_p2(&p, &h[0], &h[1]);
    h[1].x = h[0].x + FL_PX(6); h[0].vx = PD_STEER; h[1].vx = 0;
    gp_step(&p, h, IN_RIGHT, 0);
    CHECK(arena_dx(h[1].x >> 16, h[0].x >> 16) > 6 && p.b[0].hits == 0 && p.b[1].hits == 0 && p.b[0].bump_t && p.b[1].bump_t);
    CHECK(h[1].vx > PD_PUSH_KICK && h[0].vx <= -PD_PUSH_KICK);

    /* 2P ghost: a crashed bird falls on with no collision (no platform hit, no gum, no push) while the other plays */
    gp_init(&p, h, 7); gp_add_p2(&p, &h[0], &h[1]);
    p.b[0].hits = PD_HITS_MAX; p.b[0].crash = 1;
    plat_on_bird(&p, h);
    p.gum[0].x = (int16_t)(h[0].x >> 16); p.gum[0].y = PD_BIRD_Y; p.gum[0].live = 1;
    gp_step(&p, h, 0, 0);
    CHECK(p.phase == PD_FALL && p.b[0].hits == PD_HITS_MAX && p.plat[0].hit == 0 && p.gum[0].live && p.b[0].gums == 0 && !p.b[1].crash);
    h[1].x = h[0].x + FL_PX(4);
    gp_step(&p, h, 0, 0);
    CHECK(p.b[0].bump_t == 0 && p.b[1].bump_t == 0);

    /* 2P hop: only that bird lifts PD_HOP_PX_2P, the shared scroll is not slowed */
    gp_init(&p, h, 7); gp_add_p2(&p, &h[0], &h[1]);
    for (i = 0; i < 30; i++) gp_step(&p, h, 0, 0);
    { uint16_t spd0 = p.spd; uint32_t d0 = p.dist;
      gp_step(&p, h, IN_A, 0);
      CHECK(p.b[0].hop <= -PD_HOP_PX_2P + 1 && p.b[0].hop < -PD_HOP_PX && p.b[1].hop == 0 && p.brake_t == 0 && p.dist - d0 >= spd0); }

    /* 2P hit: only the hit bird's bit is set on the platform (the rival can still hit it), shared scroll not slowed */
    gp_init(&p, h, 7); gp_add_p2(&p, &h[0], &h[1]);
    for (i = 0; i < 30; i++) gp_step(&p, h, 0, 0);
    plat_on_bird(&p, &h[0]);
    { uint16_t spd0 = p.spd;
      gp_step(&p, h, 0, 0);
      CHECK(p.b[0].hits == 1 && p.plat[0].hit == 1 && p.spd >= spd0); }

    /* 2P end: one crash leaves the fall running; the game ends only when both crashed, each score recorded */
    gp_init(&p, h, 7); gp_add_p2(&p, &h[0], &h[1]);
    for (i = 0; i < 3; i++) { p.b[0].stun = 0; plat_on_bird(&p, &h[0]); gp_step(&p, h, 0, 0); }
    CHECK(p.b[0].crash && !p.b[1].crash && p.phase == PD_FALL && !p.done);
    for (i = 0; i < 20; i++) gp_step(&p, h, 0, 0);
    CHECK(p.b[1].score > p.b[0].score);                                    /* the live bird keeps scoring, the ghost's score stays */
    for (i = 0; i < 3; i++) { p.b[1].stun = 0; plat_on_bird(&p, &h[1]); gp_step(&p, h, 0, 0); }
    CHECK(p.b[1].crash && p.phase == PD_CRASH);
    { int ret = 0, n; for (n = 0; n < 400 && !ret; n++) ret = gp_step(&p, h, 0, 0);
      CHECK(ret == 1 && p.done && p.phase == PD_RESULT && p.last_score == p.b[1].score && p.seq.best[0] == p.b[0].score && p.seq.best[1] == p.b[1].score); }

    /* game wiring: start sets 1P and no computer fliers, P2 may join before the first fall moves, the score follows seq.points */
    {
        Game g;
        game_reset(&g, 3); game_set_mode(&g, GAME_MODE_GUM);
        g.mode = GAME_MODE_GUM;
        game_gg_start_pop(&g);
        CHECK(g.gg_pop && g.players == 1 && g.cpu_count == 0);
        CHECK(game_can_join_p2(&g) && game_join_p2(&g) && g.players == 2 && g.pop.seq.players == 2);
        g.cd_t = GGCD_END;
        for (i = 0; i < 5; i++) game_step(&g, 0);
        CHECK(!game_can_join_p2(&g));
    }

    /* brake hop: A press raises the bird, slows the fall for PD_BRAKE_FRAMES, returns to rest; 3 stored, one refills per PD_FLAP_REFILL; none while stunned */
    {
        uint32_t d0; uint16_t spd0;
        gp_init(&p, h, 7);
        for (i = 0; i < 30; i++) gp_step(&p, h, 0, 0);
        spd0 = p.spd; d0 = p.dist;
        gp_step(&p, h, IN_A, 0);
        CHECK(p.b[0].hop <= -PD_HOP_PX + 1 && p.b[0].flaps == PD_FLAP_MAX - 1 && p.brake_t == PD_BRAKE_FRAMES - 1);
        CHECK(p.dist - d0 <= (uint32_t)(spd0 >> 1) + 1 && p.spd == spd0);     /* slower, ramp speed untouched */
        gp_step(&p, h, IN_A, 0);                                              /* held A is not a new press */
        CHECK(p.b[0].flaps == PD_FLAP_MAX - 1);
        for (i = 0; i < (int)PD_BRAKE_FRAMES; i++) gp_step(&p, h, 0, 0);
        d0 = p.dist; gp_step(&p, h, 0, 0);
        CHECK(p.dist - d0 >= p.spd);                                        /* full speed again */
        for (i = 0; i < PD_HOP_PX; i++) gp_step(&p, h, 0, 0);
        CHECK(p.b[0].hop == 0);
        /* 3 taps use the charges, the 4th does nothing */
        gp_init(&p, h, 7);
        for (i = 0; i < 3; i++) { gp_step(&p, h, IN_A, 0); gp_step(&p, h, 0, 0); }
        CHECK(p.b[0].flaps == 0 || p.b[0].flaps == 1);                                /* 2 frames per tap, a refill may land late */
        p.b[0].flaps = 0; p.b[0].flap_t = 0; p.b[0].hop = 0; p.brake_t = 0;
        gp_step(&p, h, IN_A, 0);
        CHECK(p.b[0].hop == 0 && p.brake_t == 0 && p.b[0].flaps == 0);
        for (i = 0; i < (int)PD_FLAP_REFILL; i++) gp_step(&p, h, 0, 0);
        CHECK(p.b[0].flaps == 1);
        gp_step(&p, h, IN_A, 0);
        CHECK(p.b[0].hop < 0 && p.b[0].flaps == 0);
        /* no flap while stunned */
        gp_init(&p, h, 7);
        p.b[0].stun = 5;
        gp_step(&p, h, IN_A, 0);
        CHECK(p.b[0].hop == 0 && p.b[0].flaps == PD_FLAP_MAX);
        /* the hop moves the hit box: a platform on the rest row misses a hopped bird */
        gp_init(&p, h, 7);
        plat_on_bird(&p, h); p.plat[0].y = PD_BIRD_Y + 8;   /* a hit unhopped (y < 86), a miss hopped (y > 74) */
        gp_step(&p, h, IN_A, 0);
        CHECK(p.b[0].hits == 0);
    }

    /* flow: A, then Down three times from Big Blow picks Pop Drop, Start runs it, the best total is the record (either player's best fall, higher is better) */
    {
        Flow f;
        flow_init(&f, 0, 0);
        f.mode = GAME_MODE_GUM; f.gg_event = GG_BIG_BLOW;
        flow_coin(&f);
        flow_step(&f, IN_A, 0, 0); flow_step(&f, 0, 0, 0); /* A opens the GUM GAMES list */
        for (i = 0; i < 3; i++) { flow_step(&f, IN_DOWN, 0, 0); flow_step(&f, 0, 0, 0); }
        CHECK(f.gg_event == GG_POP_DROP);
        f.tables.gg_record[GG_POP_DROP] = 20;
        flow_step(&f, 0, 1, 1);
        CHECK(f.state == FLOW_PLAYING && f.game.gg_pop);
        f.game.pop.seq.best[0] = 33; f.game.pop.phase = PD_RESULT; f.game.pop.done = 1;
        for (i = 0; i < (int)GGCD_SET_FRAMES + 4; i++) flow_step(&f, 0, 0, 0); /* frozen through GET SET first */
        CHECK(f.tables.gg_record[GG_POP_DROP] == 33);
    }

    if (fails) { printf("test_gg_popdrop: %d FAILED\n", fails); return 1; }
    printf("test_gg_popdrop: all passed\n");
    return 0;
}
