/* test_gg_fling.c - Gum Games Gum Fling: angle mapping, fouls, ballistic landing, three attempts, best counts, qualifying mark, title pick. */
#include <stdio.h>
#include "game.h"
#include "flow.h"

static int fails;
#define CHECK(c) do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); fails++; } } while (0)

/* mash A/B for n frames, then hold C for hold frames, release; returns the event of the release frame */
static int shoot(GgFling *f, int mash, int hold)
{
    int i, ev = GF_EV_NONE;
    for (i = 0; i < mash; i++) gumfling_step(f, (uint8_t)((i & 1) ? IN_A : IN_B));
    gumfling_step(f, 0);
    for (i = 0; i < hold; i++) gumfling_step(f, IN_C);
    ev = gumfling_step(f, 0);
    return ev;
}

static void fly(GgFling *f) { int g; for (g = 0; g < 4000 && f->phase == GF_FLIGHT; g++) gumfling_fly(f); }

static void next(GgFling *f) { int g, ev = 0; for (g = 0; g < 1000 && ev != GF_EV_NEXT && f->phase != GF_END; g++) ev = gumfling_step(f, 0); }

int main(void)
{
    GgFling f;
    int i;

    CHECK(gumfling_deg(0) == 0 && gumfling_deg(GF_AIM_CAP) == 90 && gumfling_deg(1000) == 90);
    CHECK(gumfling_deg(GF_AIM_CAP / 2) == 45);

    /* a good shot launches, flies, lands at a positive distance */
    gumfling_init(&f);
    CHECK(shoot(&f, 30, 64) == GF_EV_LAUNCH && !f.foul && f.phase == GF_FLIGHT && f.vx > 0 && f.vy > 0);
    fly(&f);
    CHECK(f.phase == GF_LANDED && f.dist > 0 && f.seq.best[0] == f.dist);

    /* fouls: too flat, too steep, no launch before the clock runs out */
    gumfling_init(&f);
    shoot(&f, 20, 4);
    CHECK(f.foul && f.dist == 0 && f.phase == GF_LANDED);
    gumfling_init(&f);
    shoot(&f, 20, 120);
    CHECK(f.foul && f.dist == 0 && f.phase == GF_LANDED);
    gumfling_init(&f);
    for (i = 0; i < (int)GF_WINDUP_FRAMES + 5 && f.phase == GF_WINDUP; i++) gumfling_step(&f, 0);
    CHECK(f.foul && f.phase == GF_LANDED);

    /* more run-up power flies farther at the same angle */
    { GgFling a, b; gumfling_init(&a); gumfling_init(&b);
      shoot(&a, 2, 48); fly(&a); shoot(&b, 40, 48); fly(&b);
      CHECK(b.dist > a.dist); }

    /* three attempts, the best counts, then the end */
    gumfling_init(&f);
    shoot(&f, 4, 48); fly(&f); next(&f);
    CHECK(f.phase == GF_WINDUP);
    shoot(&f, 40, 48); fly(&f);
    { uint32_t best = f.dist; next(&f);
      shoot(&f, 2, 4);
      CHECK(f.foul);
      next(&f);
      CHECK(f.phase == GF_END && f.seq.best[0] == best); }

    /* flow: Left from Big Blow wraps to Gum Fling, Right from Gum Fling wraps to Big Blow; Start runs it */
    {
        Flow fl;
        flow_init(&fl, 0, 0);
        fl.mode = GAME_MODE_GUM; fl.gg_event = GG_BIG_BLOW;
        flow_coin(&fl);
        flow_step(&fl, IN_A, 0, 0); flow_step(&fl, 0, 0, 0); /* A opens the GUM GAMES list */
        flow_step(&fl, IN_UP, 0, 0); flow_step(&fl, 0, 0, 0);
        CHECK(fl.gg_event == GG_FLING);
        flow_step(&fl, IN_DOWN, 0, 0); flow_step(&fl, 0, 0, 0);
        CHECK(fl.gg_event == GG_BIG_BLOW);
        for (i = 0; i < 5; i++) { flow_step(&fl, IN_DOWN, 0, 0); flow_step(&fl, 0, 0, 0); }
        CHECK(fl.gg_event == GG_FLING);
        flow_step(&fl, 0, 1, 1);
        CHECK(fl.state == FLOW_PLAYING && fl.game.gg_fling && fl.game.players == 1);
    }

    puts(fails ? "FAIL test_gg_fling" : "PASS test_gg_fling");
    return fails != 0;
}
