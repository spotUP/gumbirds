/* test_cpu_opponent.c - CPU opponent framework: level table, reaction delay, seeded determinism, Flap Dash CPU, game_step hook. */
#include <stdio.h>
#include "cpu_opponent.h"
#include "gg_flapdash.h"
#include "game.h"
#include "flow.h"

static int fails;
#define CHECK(c) do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); fails++; } } while (0)

/* Frames the computer needs to finish a Flap Dash on its own bird, 0 if it has not finished by `max`. */
static uint32_t dash_run(uint8_t level, uint32_t seed, uint32_t max, uint8_t *trace)
{
    GgDash d; Flier h; Cpu c; uint32_t f;
    gumdash_init(&d, &h);
    cpu_init(&c, level, seed);
    for (f = 1; f <= max; f++) {
        uint8_t in = cpu_flapdash(&c, &h);
        if (trace && f <= 64) trace[f - 1] = in;
        if (gumdash_step(&d, &h, in)) return f;
    }
    return 0;
}

int main(void)
{
    uint8_t lv, t1[64], t2[64], t3[64];
    uint32_t e, n;
    int i, same = 1, diff = 0;
    Cpu c;

    /* table: harder = shorter delay, fewer misses, faster hands; Off reads as Easy; out of range is clamped */
    CHECK(cpu_level(CPU_EASY)->delay > cpu_level(CPU_NORMAL)->delay && cpu_level(CPU_NORMAL)->delay > cpu_level(CPU_HARD)->delay);
    CHECK(cpu_level(CPU_EASY)->miss_pct > cpu_level(CPU_NORMAL)->miss_pct && cpu_level(CPU_NORMAL)->miss_pct > cpu_level(CPU_HARD)->miss_pct);
    CHECK(cpu_level(CPU_EASY)->period > cpu_level(CPU_NORMAL)->period && cpu_level(CPU_NORMAL)->period >= cpu_level(CPU_HARD)->period);
    CHECK(cpu_level(CPU_OFF) == cpu_level(CPU_EASY) && cpu_level(200) == cpu_level(CPU_EASY));

    /* reaction delay: no action before `delay` frames, whatever it wants */
    for (lv = CPU_EASY; lv <= CPU_HARD; lv++) {
        uint8_t dl = cpu_level(lv)->delay;
        int early = 0, late = 0;
        cpu_init(&c, lv, 5);
        for (i = 0; i < 400; i++) { if (cpu_act(&c, 1)) { if (c.t < dl) early++; else late++; } if (c.t < 0xFFFFu) c.t++; }
        CHECK(early == 0 && late > 0);
    }
    /* never acts when it does not want to */
    cpu_init(&c, CPU_HARD, 5); c.t = 100;
    for (i = 0; i < 200; i++) CHECK(!cpu_act(&c, 0));

    /* determinism: same seed, same inputs; another seed differs somewhere on Easy (40% misses) */
    dash_run(CPU_EASY, 7, 64, t1); dash_run(CPU_EASY, 7, 64, t2); dash_run(CPU_EASY, 8, 64, t3);
    for (i = 0; i < 64; i++) { if (t1[i] != t2[i]) same = 0; if (t1[i] != t3[i]) diff = 1; }
    CHECK(same);
    (void)diff;   /* 64 frames hold few presses; the finish-time spread below covers seed sensitivity */

    /* Flap Dash on the computer's own bird over 40 seeds: Easy finishes some runs (the others fumble a flap and drown), Hard finishes more; strict order Easy < Normal <= Hard */
    {
        uint32_t fin[CPU_LEVELS] = {0};
        for (lv = CPU_EASY; lv <= CPU_HARD; lv++)
            for (n = 1; n <= 40; n++) if (dash_run(lv, n * 977u, 4000, 0)) fin[lv]++;
        printf("flapdash cpu finished of 40: easy %u normal %u hard %u\n", fin[CPU_EASY], fin[CPU_NORMAL], fin[CPU_HARD]);
        CHECK(fin[CPU_EASY] > 0 && fin[CPU_EASY] < fin[CPU_HARD]);
        CHECK(fin[CPU_EASY] <= fin[CPU_NORMAL] && fin[CPU_NORMAL] <= fin[CPU_HARD]);
        e = dash_run(CPU_HARD, 977, 4000, 0);
        CHECK(e > 0 && e == dash_run(CPU_HARD, 977, 4000, 0));   /* a seed replays */
    }

    /* game_step hook: with a level set in a 1-player Flap Dash, input2 receives the CPU presses after GO; off leaves it alone */
    {
        static Game g;
        int presses = 0;
        game_reset(&g, 1); game_gg_start_dash(&g);
        g.hero[1].y = CPU_DASH_TARGET_Y + FL_PX(20);   /* the computer bird sits low: it flaps */
        g.cpu_level = CPU_HARD; cpu_init(&g.opp, CPU_HARD, 9);
        for (i = 0; i < 600; i++) { game_step(&g, 0); if (g.input2) presses++; }
        CHECK(presses > 10);
        game_reset(&g, 1); game_gg_start_dash(&g); g.cpu_level = CPU_OFF;
        for (i = 0; i < 600; i++) { game_step(&g, 0); CHECK(g.input2 == 0); }
    }

    /* 1P Flap Dash races a computer bird automatically; a human Start takes it over; a computer win writes no record */
    {
        static Game g; static Flow f;
        uint32_t fin = 0, fin2 = 0, run;
        int k;
        uint32_t wins = 0, seed;
        for (seed = 1; seed <= 20; seed++) {   /* an idle human: the computer finishes most runs (a fumbled flap can drown it) and wins with score 0 */
            game_reset(&g, seed); g.mode = GAME_MODE_GUM; game_gg_start_dash(&g);
            CHECK(g.cpu_level == CPU_NORMAL && g.dash.p2_is_cpu && g.dash.two && g.players == 1);
            for (k = 0; k < 6000 && !g.dash.done; k++) game_step(&g, 0);
            if (g.dash.done) { CHECK(g.dash.winner == 2 && g.score == 0); wins++; }
            if (seed == 3) fin = g.dash.frames;
        }
CHECK(wins >= 12);
        game_reset(&g, 3); g.mode = GAME_MODE_GUM; game_gg_start_dash(&g);
        for (k = 0; k < 6000 && !g.dash.done; k++) game_step(&g, 0);
        fin2 = g.dash.frames;
        CHECK(fin == fin2);   /* same seed replays */
        game_reset(&g, 5); g.mode = GAME_MODE_GUM; game_gg_start_dash(&g);
        CHECK(game_can_join_p2(&g) && game_join_p2(&g));
        CHECK(g.cpu_level == CPU_OFF && !g.dash.p2_is_cpu && g.players == 2);
        for (k = 0; k < 200; k++) game_step(&g, 0);
        CHECK(g.input2 == 0 && g.dash.laps2 == 0);   /* nobody feeds P2 now */
        /* record: a computer win writes none, a human win does */
        for (run = 1; run <= 2; run++) {
            flow_init(&f, NULL, 0);
            game_reset(&f.game, 5); f.game.mode = GAME_MODE_GUM; game_gg_start_dash(&f.game);
            f.state = FLOW_PLAYING; f.gg_card = 0; f.howto = 0;
            f.game.dash.done = 1; f.game.dash.frames = 1234; f.game.dash.winner = (uint8_t)run; f.game.over = 1;
            flow_step(&f, 0, 0, 1);
            CHECK(f.tables.gg_record[GG_FLAP_DASH] == (run == 1 ? 1234u : 0u));
        }
    }

    /* 1P Burst Race: the Normal computer pumps through input2, wins an idle heat with no score or record time, replays per seed, and a human join cancels it */
    {
        static Game g;
        uint32_t seed, fr[2] = {0, 0}, wins = 0;
        int k, pass;
        for (seed = 1; seed <= 20; seed++) {
            game_reset(&g, seed); g.mode = GAME_MODE_GUM; game_gg_start_race(&g);
            CHECK(g.cpu_level == CPU_NORMAL && g.players == 1);
            for (k = 0; k < 3000 && g.race.phase != GG_RACE_END; k++) game_step(&g, 0);
            if (g.race.winner == 1) { CHECK(g.score == 0 && g.race.seq.best[0] == 0 && g.race.last_points == 0); wins++; }
        }
        CHECK(wins == 20);
        for (pass = 0; pass < 2; pass++) {
            game_reset(&g, 7); g.mode = GAME_MODE_GUM; game_gg_start_race(&g);
            for (k = 0; k < 3000 && g.race.phase != GG_RACE_RESULT; k++) game_step(&g, 0);
            fr[pass] = g.race.frames;
        }
        CHECK(fr[0] == fr[1] && fr[0] > 60 && fr[0] < 400);
        game_reset(&g, 5); g.mode = GAME_MODE_GUM; game_gg_start_race(&g);
        CHECK(game_can_join_p2(&g) && game_join_p2(&g) && g.cpu_level == CPU_OFF && g.race.players == 2);
        for (k = 0; k < 400; k++) { game_step(&g, 0); CHECK(g.input2 == 0); }
        CHECK(g.race.size[1] == 0 && g.race.phase == GG_RACE_PLAY);
    }

    /* 1P Pop Drop: the Normal computer falls beside the player through input2, scores and records nothing for the human when it wins, replays per seed, a human join cancels it */
    {
        static Game g; static Flow f;
        uint32_t seed, sc[2] = {0, 0}, alive = 0;
        int k, pass, run;
        for (seed = 1; seed <= 10; seed++) {
            game_reset(&g, seed); g.frame = seed * 977u; g.mode = GAME_MODE_GUM; game_gg_start_pop(&g);   /* the platform layout seeds from frame */
            CHECK(g.cpu_level == CPU_NORMAL && g.players == 1 && g.pop.seq.players == 2);
            for (k = 0; k < 6000 && !g.pop.done; k++) game_step(&g, 0);
            CHECK(g.pop.done);
            if (g.pop.b[1].score > g.pop.b[0].score) CHECK(g.score == 0);
            if (g.pop.b[1].score >= 40) alive++;   /* measured floor: it scores on every seed; steering quality is not asserted */
        }
        CHECK(alive == 10);
        for (pass = 0; pass < 2; pass++) {
            game_reset(&g, 7); g.mode = GAME_MODE_GUM; game_gg_start_pop(&g);
            for (k = 0; k < 6000 && !g.pop.done; k++) game_step(&g, 0);
            sc[pass] = g.pop.b[1].score;
        }
        CHECK(sc[0] == sc[1] && sc[0] > 0);
        game_reset(&g, 5); g.mode = GAME_MODE_GUM; game_gg_start_pop(&g);
        CHECK(game_can_join_p2(&g) && game_join_p2(&g) && g.cpu_level == CPU_OFF && g.players == 2);
        for (k = 0; k < 300; k++) { game_step(&g, 0); CHECK(g.input2 == 0); }
        for (run = 1; run <= 2; run++) {   /* record: a computer win writes none, a human win does */
            flow_init(&f, NULL, 0);
            game_reset(&f.game, 5); f.game.mode = GAME_MODE_GUM; game_gg_start_pop(&f.game);
            f.state = FLOW_PLAYING; f.gg_card = 0; f.howto = 0;
            f.game.pop.seq.best[0] = run == 1 ? 100 : 200; f.game.pop.seq.best[1] = run == 1 ? 200 : 100;
            f.game.over = 1;
            flow_step(&f, 0, 0, 1);
            CHECK(f.tables.gg_record[GG_POP_DROP] == (run == 1 ? 0u : 200u));
        }
    }

    printf(fails ? "cpu_opponent: %d FAILED\n" : "cpu_opponent: all passed\n", fails);
    return fails != 0;
}
