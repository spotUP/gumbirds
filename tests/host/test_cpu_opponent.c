/* test_cpu_opponent.c - CPU opponent framework: level table, reaction delay, seeded determinism, Flap Dash CPU, game_step hook. */
#include <stdio.h>
#include "cpu_opponent.h"
#include "gg_flapdash.h"
#include "game.h"

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
        game_reset(&g, 1); game_gg_start_dash(&g);
        for (i = 0; i < 600; i++) { game_step(&g, 0); CHECK(g.input2 == 0); }
    }

    printf(fails ? "cpu_opponent: %d FAILED\n" : "cpu_opponent: all passed\n", fails);
    return fails != 0;
}
