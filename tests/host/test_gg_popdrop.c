/* test_gg_popdrop.c - Gum Games Pop Drop (free fall): speed ramp, steering and facing, platform hit (stun, gum lost, shield soak), crash on the third hit,
 * score = depth + gums, 2P turns, game and flow wiring. */
#include <stdio.h>
#include "gg_popdrop.h"
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
    GgPop p; Flier h; int i; uint16_t s0;

    /* start: falling, speeds up, depth and score grow, no platform hit while the field is empty of platforms in reach */
    gp_init(&p, &h, 7);
    CHECK(p.phase == PD_FALL && p.hits == 0 && p.seq.players == 1 && p.seq.tickets[0] == 1);
    s0 = p.spd;
    for (i = 0; i < 100; i++) gp_step(&p, &h, 0);
    CHECK(p.spd > s0 && p.spd <= PD_SPEED_MAX && p.depth > 0 && p.score >= p.depth);

    /* steering and facing */
    gp_init(&p, &h, 7);
    { int32_t x0 = h.x; for (i = 0; i < 20; i++) gp_step(&p, &h, IN_LEFT); CHECK(h.x < x0 && p.flip == 1);
      for (i = 0; i < 40; i++) gp_step(&p, &h, IN_RIGHT); CHECK(h.x > x0 && p.flip == 0); }

    /* a hit: stun, one gum lost, bounce, speed loss; steering locked while stunned */
    gp_init(&p, &h, 7);
    p.gums = 3; p.spd = 100; plat_on_bird(&p, &h);
    gp_step(&p, &h, 0);
    CHECK(p.hits == 1 && p.stun > 0 && p.gums == 2 && p.spd < 100 && p.bounce < 0);
    { int32_t x0 = h.x; gp_step(&p, &h, IN_LEFT); CHECK(h.x >= x0 - FL_PX(1) && p.flip == 0); }

    /* a shield soaks the hit: no hit counted, no stun, shield gone */
    gp_init(&p, &h, 7);
    p.shield = 1; plat_on_bird(&p, &h);
    gp_step(&p, &h, 0);
    CHECK(p.hits == 0 && p.stun == 0 && p.shield == 0 && p.pop_t > 0);

    /* every 10 gums raise a shield */
    gp_init(&p, &h, 7);
    for (i = 0; i < (int)PD_SHIELD_EVERY; i++) {
        p.gum[0].x = (int16_t)(h.x >> 16); p.gum[0].y = PD_BIRD_Y; p.gum[0].live = 1;
        { int k; for (k = 0; k < PD_PLATS; k++) p.plat[k].live = 0; }
        gp_step(&p, &h, 0);
    }
    CHECK(p.gums == (uint16_t)PD_SHIELD_EVERY && p.shield == 1 && p.shield_count == 0);

    /* three hits crash; the attempt ends with the score, then the result, then done */
    gp_init(&p, &h, 7);
    for (i = 0; i < 3; i++) { p.stun = 0; plat_on_bird(&p, &h); gp_step(&p, &h, 0); }
    CHECK(p.hits == 3 && p.phase == PD_CRASH);
    { int ret = 0, n; for (n = 0; n < 400 && !ret; n++) ret = gp_step(&p, &h, 0);
      CHECK(ret == 1 && p.done && p.phase == PD_RESULT && p.seq.best[0] == p.last_score); }

    /* 2P: P2 joins, the turns alternate, the run is done after both crashed */
    gp_init(&p, &h, 7); gp_add_p2(&p);
    CHECK(p.seq.players == 2 && p.seq.tickets[1] == 1 && p.seq.turn == 0);
    for (i = 0; i < 3; i++) { p.stun = 0; plat_on_bird(&p, &h); gp_step(&p, &h, 0); }
    for (i = 0; i < 200 && p.phase != PD_FALL; i++) gp_step(&p, &h, 0);
    CHECK(p.phase == PD_FALL && p.seq.turn == 1 && p.hits == 0 && p.score == 0 && !p.done);
    for (i = 0; i < 3; i++) { p.stun = 0; plat_on_bird(&p, &h); gp_step(&p, &h, 0); }
    for (i = 0; i < 400 && !p.done; i++) gp_step(&p, &h, 0);
    CHECK(p.done && p.phase == PD_RESULT);

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
        gp_init(&p, &h, 7);
        for (i = 0; i < 30; i++) gp_step(&p, &h, 0);
        spd0 = p.spd; d0 = p.dist;
        gp_step(&p, &h, IN_A);
        CHECK(p.hop <= -PD_HOP_PX + 1 && p.flaps == PD_FLAP_MAX - 1 && p.brake_t == PD_BRAKE_FRAMES - 1);
        CHECK(p.dist - d0 <= (uint32_t)(spd0 >> 1) + 1 && p.spd == spd0);     /* slower, ramp speed untouched */
        gp_step(&p, &h, IN_A);                                              /* held A is not a new press */
        CHECK(p.flaps == PD_FLAP_MAX - 1);
        for (i = 0; i < PD_BRAKE_FRAMES; i++) gp_step(&p, &h, 0);
        d0 = p.dist; gp_step(&p, &h, 0);
        CHECK(p.dist - d0 >= p.spd);                                        /* full speed again */
        for (i = 0; i < PD_HOP_PX; i++) gp_step(&p, &h, 0);
        CHECK(p.hop == 0);
        /* 3 taps use the charges, the 4th does nothing */
        gp_init(&p, &h, 7);
        for (i = 0; i < 3; i++) { gp_step(&p, &h, IN_A); gp_step(&p, &h, 0); }
        CHECK(p.flaps == 0 || p.flaps == 1);                                /* 2 frames per tap, a refill may land late */
        p.flaps = 0; p.flap_t = 0; p.hop = 0; p.brake_t = 0;
        gp_step(&p, &h, IN_A);
        CHECK(p.hop == 0 && p.brake_t == 0 && p.flaps == 0);
        for (i = 0; i < (int)PD_FLAP_REFILL; i++) gp_step(&p, &h, 0);
        CHECK(p.flaps == 1);
        gp_step(&p, &h, IN_A);
        CHECK(p.hop < 0 && p.flaps == 0);
        /* no flap while stunned */
        gp_init(&p, &h, 7);
        p.stun = 5;
        gp_step(&p, &h, IN_A);
        CHECK(p.hop == 0 && p.flaps == PD_FLAP_MAX);
        /* the hop moves the hit box: a platform on the rest row misses a hopped bird */
        gp_init(&p, &h, 7);
        plat_on_bird(&p, &h); p.plat[0].y = PD_BIRD_Y + 8;   /* a hit unhopped (y < 86), a miss hopped (y > 74) */
        gp_step(&p, &h, IN_A);
        CHECK(p.hits == 0);
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
