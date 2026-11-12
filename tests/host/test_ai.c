/* Host test for src/core/ai.[ch] and the match logic in game_step_arena. */
#include <stdio.h>
#include "../../src/core/game.h"
#include "../../src/core/hazard_kind.h"
#include "../../src/core/ai.h"
#include "../../src/core/nameentry.h"
#include "../../src/core/stage.h"

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

static Flier mk(int x, int y, int balloons) {
    Flier f;
    flier_init(&f, FL_PX(x), FL_PX(y), (uint8_t)balloons, 0);
    return f;
}

int main(void) {
    Flier me, t;
    Rng r;
    Ai a;
    FlierInput in;
    int i, thinks, gaps_min = 999, gaps_max = 0, last = 0;

    /* ai_decide thresholds (screen px). Balloon-less: far = FILL, within AI_FILL_DIST = FLEE. */
    me = mk(100, 100, 0);
    t = mk(100 + AI_FILL_DIST + 1, 100, 2);
    CHECK(ai_decide(&me, &t) == AI_FILL);
    t = mk(100 + AI_FILL_DIST, 100, 2);
    CHECK(ai_decide(&me, &t) == AI_FLEE);
    /* With balloons: closer than AI_FLEE_DIST flees, at the distance chases. */
    me = mk(100, 100, 2);
    t = mk(100 + AI_FLEE_DIST - 1, 100, 2);
    CHECK(ai_decide(&me, &t) == AI_FLEE);
    t = mk(100 + AI_FLEE_DIST, 100, 2);
    CHECK(ai_decide(&me, &t) == AI_CHASE);
    /* Above the target by AI_ABOVE_MARGIN: chase even when close; one pixel less: flee. */
    t = mk(100, 100 + AI_ABOVE_MARGIN, 2);
    CHECK(ai_decide(&me, &t) == AI_CHASE);
    t = mk(100, 100 + AI_ABOVE_MARGIN - 1, 2);
    CHECK(ai_decide(&me, &t) == AI_FLEE);

    /* Think period: first think after the armed timer, then every AI_THINK_FRAMES +- jitter; counted from a.thinks. */
    rng_seed(&r, 5);
    ai_init(&a, &r);
    me = mk(100, 100, 2);
    t = mk(250, 100, 2);
    thinks = 0;
    for (i = 1; i <= 3000; i++) {
        uint32_t before = a.thinks;
        ai_step(&a, &r, &me, &t, &in);
        if (a.thinks != before) {
            int gap = i - last;
            thinks++;
            if (thinks > 1) { if (gap < gaps_min) gaps_min = gap; if (gap > gaps_max) gaps_max = gap; }
            last = i;
        }
    }
    CHECK(a.thinks == (uint32_t)thinks && thinks > 80);
    CHECK(gaps_min >= AI_THINK_FRAMES - AI_THINK_JITTER && gaps_max <= AI_THINK_FRAMES + AI_THINK_JITTER);
    CHECK(gaps_max > gaps_min); /* jitter is used */

    /* Chase steers toward a target on the right and flaps (target level: dir.y 0 < 0.5); dir held between thinks. */
    rng_seed(&r, 6);
    ai_init(&a, &r);
    for (i = 0; i < 60 && a.thinks == 0; i++) ai_step(&a, &r, &me, &t, &in);
    CHECK(a.state == AI_CHASE && in.dir == 1 && in.flap == 1);
    /* The flap decision runs every frame: still flapping a frame later, but never inside the cooldown or while the button is held. */
    ai_step(&a, &r, &me, &t, &in);
    CHECK(in.dir == 1 && in.flap == 1);
    me.flap_cd = 1;
    ai_step(&a, &r, &me, &t, &in);
    CHECK(in.dir == 1 && in.flap == 0);
    me.flap_cd = 0; me.flap_prev = 1;
    ai_step(&a, &r, &me, &t, &in);
    CHECK(in.dir == 1 && in.flap == 0);
    me.flap_prev = 0;
    /* Target far below (dir.y ~ 1) and only slightly right: no flap, no steer (|dir.x| <= 0.25). */
    t = mk(104, 170, 2);
    rng_seed(&r, 6);
    ai_init(&a, &r);
    for (i = 0; i < 60 && a.thinks == 0; i++) ai_step(&a, &r, &me, &t, &in);
    CHECK(a.thinks == 1 && in.dir == 0 && in.flap == 0);
    /* Flee negates: target on the right and close, flier flees left. */
    t = mk(110, 100, 2);
    rng_seed(&r, 6);
    ai_init(&a, &r);
    for (i = 0; i < 60 && a.thinks == 0; i++) ai_step(&a, &r, &me, &t, &in);
    CHECK(a.state == AI_FLEE && in.dir == -1);
    /* FILL: balloon-less and far: idle, no flap, no steer. */
    me = mk(100, 100, 0);
    t = mk(250, 100, 2);
    rng_seed(&r, 6);
    ai_init(&a, &r);
    for (i = 0; i < 60 && a.thinks == 0; i++) ai_step(&a, &r, &me, &t, &in);
    CHECK(a.state == AI_FILL && in.dir == 0 && in.flap == 0);
    /* No target: idle. */
    rng_seed(&r, 6);
    ai_init(&a, &r);
    for (i = 0; i < 60 && a.thinks == 0; i++) ai_step(&a, &r, &me, 0, &in);
    CHECK(in.dir == 0 && in.flap == 0);

    /* ai_nearest: picks the nearest live rival, skips self and the dead. */
    {
        Flier player = mk(0, 0, 2), cpus[3];
        cpus[0] = mk(100, 100, 2); cpus[1] = mk(30, 0, 2); cpus[2] = mk(10, 0, 2);
        CHECK(ai_nearest(&cpus[0], &player, cpus, 3) == &cpus[1]);
        cpus[1].state = FLIER_FALLING;
        CHECK(ai_nearest(&cpus[0], &player, cpus, 3) == &cpus[2]);
        cpus[1].state = FLIER_ALIVE;
        /* across the seam: a rival at x 380 is 4 px from a flier at x 0, nearer than one at x 100 */
        {
            Flier me = mk(0, 100, 2), rival[2], other;
            rival[0] = mk(100, 100, 2); rival[1] = mk(380, 100, 2);
            other = mk(200, 100, 2);
            CHECK(ai_nearest(&me, &other, rival, 2) == &rival[1]);
            CHECK(ai_decide(&me, &rival[1]) == AI_FLEE);   /* 4 px away: flee, not the 380 px a linear distance gives */
            {
                static Rng r; Ai a; FlierInput in;
                rng_seed(&r, 1); ai_init(&a, &r); a.timer = 1;
                ai_step(&a, &r, &me, &rival[1], &in);
                CHECK(in.dir == 1);   /* flee from a rival to the left across the seam: run right */
            }
        }
        CHECK(ai_nearest(&cpus[1], &player, cpus, 3) == &cpus[2]); /* self is excluded */
        cpus[2].state = FLIER_FALLING;
        CHECK(ai_nearest(&cpus[1], &player, cpus, 3) == &player);
        cpus[0].state = cpus[1].state = FLIER_DROWNED; player.state = FLIER_DROWNED;
        CHECK(ai_nearest(&cpus[1], &player, cpus, 3) == 0);
    }

    /* Hazard kill line through the game entry: game_set_hazard(kind) puts the player and every rival on that kind's
     * line (also after a rematch, tested below), and a flier with feet 1 px above the line lives while one on it drowns. */
    {
        static Game g;
        int k;
        uint32_t score0;
        for (k = 0; k < HAZARD_KINDS; k++) {
            int line = hazard_kill_px((uint8_t)k);
            game_reset(&g, 4);
            game_set_hazard(&g, (uint8_t)k);
            game_step_arena(&g, 0); /* match_start runs here: rivals spawn with the game's kind */
            CHECK(g.flier.kill_y == FL_PX(line) && g.cpu[0].kill_y == FL_PX(line) && g.cpu[CPU_MAX - 1].kill_y == FL_PX(line));
            g.flier.on_ground = 0; g.flier.vx = 0; g.flier.vy = 0;
            g.flier.x = FL_PX(100);
            g.flier.y = FL_PX(line) - flier_half_h(&g.flier) - FL_PX(1);
            g.cpu[0].on_ground = 0; g.cpu[0].vx = 0; g.cpu[0].vy = 0;
            g.cpu[0].x = FL_PX(300);
            g.cpu[0].y = FL_PX(line) - flier_half_h(&g.cpu[0]);
            score0 = g.score;
            game_step_arena(&g, 0);
            CHECK(g.flier.state == FLIER_ALIVE);
            CHECK(g.cpu[0].state == FLIER_DROWNED);
            CHECK(g.score == score0 + SCORE_CPU_DROWN); /* one rival drowned on the line: scored once */
            game_step_arena(&g, 0);
            CHECK(g.score == score0 + SCORE_CPU_DROWN); /* and not again while it stays drowned */
            g.flier.y = FL_PX(line) - flier_half_h(&g.flier);
            game_step_arena(&g, 0);
            /* behaviour change approved by the user (dead flier hazard hunt): touching the line starts the fall, the run ends when the body is GONE; was CHECK(DROWNED && g.over) at once */
            CHECK(g.flier.state == FLIER_DROWNED && !g.over);
            for (i = 0; i < 400 && !g.over; i++) game_step_arena(&g, 0);
            CHECK(g.flier.state == FLIER_GONE && g.over);
            /* Rematch: win match 1 under this kind; player_spawn and match_start must keep the kind's line. */
            game_reset(&g, 4);
            game_set_hazard(&g, (uint8_t)k);
            game_step_arena(&g, 0);
            for (i = 0; i < g.cpu_count; i++) g.cpu[i].state = FLIER_GONE;
            game_step_arena(&g, 0);
            CHECK(g.matches_won == 1 && g.cpu_alive == g.cpu_count);
            CHECK(g.flier.kill_y == FL_PX(line));
            for (i = 0; i < g.cpu_count; i++) CHECK(g.cpu[i].kill_y == FL_PX(line));
        }
    }

    /* DF6 (dead flier hazard hunt): the round ends only when the last body is GONE, and a drowned rival scores once */
    {
        static Game g;
        game_reset(&g, 11);
        game_step_arena(&g, 0);
        uint32_t score0 = g.score;
        for (i = 0; i < g.cpu_count; i++) { g.cpu[i].state = FLIER_DROWNED; g.cpu[i].y = FL_PX(100); g.cpu[i].vy = 0; g.cpu[i].vx = 0; g.cpu[i].on_ground = 0; }
        game_step_arena(&g, 0);
        CHECK(g.matches_won == 0);                                   /* bodies still falling: no round end */
        CHECK(g.score == score0);                                    /* entering the state by hand is not a drowning; a fall adds nothing */
        for (i = 0; i < 3; i++) game_step_arena(&g, 0);
        CHECK(g.matches_won == 0);
        for (i = 0; i < g.cpu_count; i++) g.cpu[i].state = FLIER_GONE;
        game_step_arena(&g, 0);
        CHECK(g.matches_won == 1);                                   /* the last body left: the round ends */
    }
    /* Match logic through the arena step: match 1 has CPU_START_COUNT fliers; removing them wins and starts
     * the next match with one more, capped at CPU_MAX, with the player's balloons reset. */
    {
        static Game g;
        int m;
        game_reset(&g, 9);
        game_step_arena(&g, 0);
        CHECK(g.cpu_count == CPU_START_COUNT && g.cpu_alive == CPU_START_COUNT && g.matches_won == 0);
        for (m = 1; m <= CPU_MAX; m++) {
            int expect = CPU_START_COUNT + m;
            if (expect > CPU_MAX) expect = CPU_MAX;
            g.flier.balloons = 1;
            for (i = 0; i < g.cpu_count; i++) g.cpu[i].state = FLIER_GONE;
            game_step_arena(&g, 0);
            CHECK(g.matches_won == (uint32_t)m);
            CHECK(g.cpu_count == expect && g.cpu_alive == expect);
            CHECK(g.flier.balloons == FLIER_START_BALLOONS);
            CHECK(!g.over);
        }
        CHECK(g.cpu_count == CPU_MAX);
        /* Player death ends the run, no respawn. */
        g.flier.state = FLIER_GONE; /* behaviour change approved by the user (dead flier hazard hunt): was FLIER_DROWNED; the run ends when the body is gone */
        game_step_arena(&g, 0);
        CHECK(g.over);
    }
    /* Computer fliers never pop each other (BR-D3): cpu 1 feet-on cpu 0's balloons is a bounce, no stomp, no balloon lost. */
    {
        static Game g;
        uint32_t before, bounces;
        game_reset(&g, 3);
        game_step_arena(&g, 0);
        g.cpu[1].x = g.cpu[0].x; g.cpu[1].y = g.cpu[0].y - FL_PX(26);
        g.cpu[1].vy = FL_PX(1);
        before = g.stomps; bounces = g.bounces;
        game_step_arena(&g, 0);
        CHECK(g.stomps == before && g.bounces > bounces && g.cpu[0].balloons == FLIER_START_BALLOONS);
    }
    /* Body contact kills a balloon-less flier. */
    {
        Flier v = mk(100, 100, 0), o = mk(101, 100, 2);
        CHECK(flier_body_kill(&v, &o) == 1 && v.state == FLIER_FALLING);
        v = mk(100, 100, 0); o = mk(130, 100, 2);
        CHECK(flier_body_kill(&v, &o) == 0);
        v = mk(100, 100, 1); o = mk(101, 100, 2);
        CHECK(flier_body_kill(&v, &o) == 0);
    }

    /* A computer flier under an island with the target above it must get out from under: without the overhead steer it
       flaps into the underside and bounces for ever (the island is solid). Island: top centre, x 144..240, y 68..80. */
    {
        Flier c = mk(192, 80 + 6 + 3, 2), tgt = mk(192, 30, 2);
        Rng r2; Ai a2; FlierInput ci;
        int top_seen = 0, hits0 = g_flier_solid_hits;
        rng_seed(&r2, 9);
        ai_init(&a2, &r2);
        for (i = 0; i < 600 && !top_seen; i++) {
            int32_t px = c.x, py = c.y;
            FlierSolid so[STAGE_SOLIDS_MAX];
            ai_step(&a2, &r2, &c, &tgt, &ci);
            flier_step(&c, &ci, stage_floor_y(c.x, c.y + flier_half_h(&c)));
            flier_collide_solids(&c, px, py, so, stage_solids_near(c.x, so, STAGE_SOLIDS_MAX));
            if (c.y + flier_half_h(&c) <= FL_PX(68)) top_seen = 1;
        }
        CHECK(top_seen && i < 200);                      /* with the steer: 86 frames, 2 bounces; without it: 355 and 13 */
        CHECK((int)g_flier_solid_hits - hits0 < 6);
    }

    printf("ai: %d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
