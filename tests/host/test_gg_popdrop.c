/* test_gg_popdrop.c - Gum Games Pop Drop: hang and cut, nudge, centre pop vs edge pop, miss, five drops, game and flow wiring. */
#include <stdio.h>
#include "gg_popdrop.h"
#include "game.h"
#include "flow.h"

static int fails;
#define CHECK(c) do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); fails++; } } while (0)

/* Hold `hold` (stick bits) from the cut until the drop ends; returns the last_score of the first drop. */
static void first_drop(GgPop *p, Flier *h, Flier *t, uint8_t hold)
{
    int i;
    for (i = 0; i < 20; i++) gp_step(p, h, t, 0);
    gp_step(p, h, t, IN_C);
    for (i = 0; i < 600 && p->phase != GP_PAUSE; i++) gp_step(p, h, t, hold);
}

int main(void)
{
    GgPop p; Flier h, t; int i;

    /* hang: the chute carries the bird, nothing happens until C; C cuts it and the bird falls */
    gp_init(&p, &h, &t);
    for (i = 0; i < 30; i++) gp_step(&p, &h, &t, 0);
    CHECK(p.phase == GP_HANG && h.state == FLIER_PARACHUTE);
    gp_step(&p, &h, &t, IN_C);
    CHECK(p.phase == GP_FALL && h.state == FLIER_ALIVE && !h.has_parachute);

    /* an idle bird cuts itself loose */
    gp_init(&p, &h, &t);
    for (i = 0; i < (int)GP_HANG_MAX + 2; i++) gp_step(&p, &h, &t, 0);
    CHECK(p.phase != GP_HANG);

    /* the stick nudges the fall sideways, a small amount */
    gp_init(&p, &h, &t);
    gp_step(&p, &h, &t, IN_C);
    { int32_t x0 = h.x; for (i = 0; i < 10; i++) gp_step(&p, &h, &t, IN_RIGHT);
      CHECK(h.x > x0 && h.x - x0 < FL_PX(10)); }

    /* an untouched fall misses the balloon (it starts beside the hero) and scores 0 */
    gp_init(&p, &h, &t);
    first_drop(&p, &h, &t, 0);
    CHECK(p.phase == GP_PAUSE && !p.last_pop && p.last_score == 0 && p.pops == 0);

    /* a centred pop beats an edge pop: place the target under the hero by hand */
    gp_init(&p, &h, &t);
    gp_step(&p, &h, &t, IN_C);
    t.vx = 0; t.x = h.x;
    for (i = 0; i < 600 && p.phase == GP_FALL; i++) gp_step(&p, &h, &t, 0);
    CHECK(p.last_pop && p.last_off <= 1 && p.last_score >= GP_RING - 1 && p.pops == 1);
    { uint16_t centre = p.last_score;
      gp_init(&p, &h, &t);
      gp_step(&p, &h, &t, IN_C);
      t.vx = 0; t.x = h.x + FL_PX(8);
      for (i = 0; i < 600 && p.phase == GP_FALL; i++) gp_step(&p, &h, &t, 0);
      CHECK(p.last_pop && p.last_off >= 6 && p.last_score < centre); }

    /* five misses end the event with no pops */
    gp_init(&p, &h, &t);
    { int ended = 0;
      for (i = 0; i < 5000 && !ended; i++) ended = gp_step(&p, &h, &t, (uint8_t)(i % 100 == 20 ? IN_C : 0));
      CHECK(ended && p.drop == GP_DROPS && p.pops == 0 && p.total == 0); }

    /* game wiring: game_step runs it, the target is cpu[0], a finished event scores gg_points */
    { Game g; game_reset(&g, 1); game_set_mode(&g, GAME_MODE_GUM); game_gg_start_pop(&g);
      CHECK(g.gg_pop && g.cpu_count == 1 && g.players == 1);
      for (i = 0; i < 100; i++) game_step(&g, 0);
      CHECK(g.pop.timer == 100 && !g.over); }

    /* flow: Right three times from Big Blow picks Pop Drop, Start runs it, the best total is the record (higher is better) */
    {
        Flow f;
        flow_init(&f, 0, 0);
        f.mode = GAME_MODE_GUM; f.gg_event = GG_BIG_BLOW;
        flow_coin(&f);
        for (i = 0; i < 3; i++) { flow_step(&f, IN_RIGHT, 0, 0); flow_step(&f, 0, 0, 0); }
        CHECK(f.gg_event == GG_POP_DROP);
        f.tables.gg_record[GG_POP_DROP] = 20;
        flow_step(&f, 0, 1, 1);
        CHECK(f.state == FLOW_PLAYING && f.game.gg_pop);
        f.game.pop.total = 33; f.game.pop.pops = 4; f.game.pop.phase = GP_RESULT; f.game.pop.done = 1;
        for (i = 0; i < 4; i++) flow_step(&f, 0, 0, 0);
        CHECK(f.tables.gg_record[GG_POP_DROP] == 33);
    }

    if (fails) { printf("test_gg_popdrop: %d FAILED\n", fails); return 1; }
    printf("test_gg_popdrop: all passed\n");
    return 0;
}
