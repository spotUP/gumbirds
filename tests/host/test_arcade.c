/* Host test for src/core/arcade.[ch]: stage loop, ranks, gum rules, bonus stage, score clamp. */
#include <stdio.h>
#include <string.h>
#include "../../src/core/arcade.h"
#include "../../src/core/arena.h"
#include "../../src/core/flier.h"

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

static void clear_stage(ArcRun *r) { int n; arc_stage_cleared(r); for (n = 0; n < ARC_CLEAR_FRAMES + 2 && r->state == ARC_CLEAR; n++) arc_step(r); }

int main(void) {
    ArcRun r; int i, seen_bonus = 0;
    arc_start(&r);
    CHECK(r.stage == 1 && r.state == ARC_PLAY && r.gum == 2);
    CHECK(strcmp(arc_stage_name(1), "R01") == 0 && strcmp(arc_stage_name(12), "R12b") == 0);
    for (i = 1; i <= 12; i++) CHECK(arc_stage_layout(i) == ARC_LAYOUT_BASE + i - 1); /* the stage set is the stage.c table order */
    CHECK(arc_stage_layout(10) == ARC_LAYOUT_BASE + 9 && strcmp(arc_stage_name(10), "R10") == 0);
    /* Stage 1..3 then bonus 1, stage 4..6 then bonus 2, ... */
    for (i = 1; i <= 12; i++) {
        CHECK(r.stage == i && r.state == ARC_PLAY);
        arc_stage_cleared(&r);
        CHECK(r.state == ARC_CLEAR);
        clear_stage(&r);
        if (i % 3 == 0) { CHECK(r.state == ARC_BONUS && r.bonus_no == i / 3); seen_bonus++; arc_bonus_done(&r); }
        else CHECK(r.state == ARC_PLAY);
    }
    CHECK(seen_bonus == 4);
    CHECK(r.stage == 4 && r.loops == 1 && r.state == ARC_PLAY); /* stage 12 loops to stage 4 */
    CHECK(arc_next_stage(12) == 4 && arc_next_stage(5) == 6);
    /* The interstitial lasts ARC_CLEAR_FRAMES. */
    { int n = 0; arc_stage_cleared(&r); while (r.state == ARC_CLEAR) { arc_step(&r); n++; } CHECK(n == ARC_CLEAR_FRAMES); }
    /* Ranks. */
    CHECK(arc_rank_for(1, 0) == 1 && arc_rank_for(6, 0) == 2 && arc_rank_for(12, 0) == 3 && arc_rank_for(4, 1) == 2 && arc_rank_for(12, 5) == 3);
    for (i = 1; i < 12; i++) CHECK(arc_rank_for(i, 0) <= arc_rank_for(i + 1, 0));
    CHECK(arc_rank(1)->pump_frames == 150 && arc_rank(3)->pump_frames == 90 && arc_rank(2)->pump_frames == 120);
    CHECK(arc_rank(1)->pop_score == 500 && arc_rank(2)->pop_score == 750 && arc_rank(3)->pop_score == 1000);
    CHECK(arc_rank(1)->defeat_score == 1000 && arc_rank(2)->defeat_score == 1500 && arc_rank(3)->defeat_score == 2000);
    CHECK(arc_rank(0) == arc_rank(1) && arc_rank(9) == arc_rank(3));
    /* Gum. */
    CHECK(arc_gum_after_stage(1) == 1 && arc_gum_after_stage(0) == 0 && arc_gum_after_stage(7) == 2 && arc_gum_after_stage(-1) == 0);
    CHECK(arc_gum_on_bonus() == 2 && arc_gum_on_new_life() == 2);
    arc_start(&r); r.gum = 0; for (i = 0; i < 3; i++) clear_stage(&r); CHECK(r.state == ARC_BONUS && r.gum == 2);
    /* Clamp. */
    CHECK(arc_score_add(10, 5) == 15 && arc_score_add(999990, 20) == 999999 && arc_score_add(999999, 1) == 999999 && arc_score_add(5, 0xFFFFFFFFu) == 999999 && arc_score_add(0xFFFFFFFFu, 1) == 999999);
    /* Bonus tables (reference): speed per bonus number, value per bubble, perfect bonus; 5 and up repeat the last. */
    {
        static const int32_t sp[5] = { 32768, 36864, 38912, 40960, 43008 };
        static const int va[5] = { 300, 500, 700, 700, 700 }, pf[5] = { 10000, 15000, 20000, 25000, 30000 };
        for (i = 1; i <= 7; i++) {
            int k = i > 5 ? 4 : i - 1;
            CHECK(arc_bonus_speed16(i) == sp[k] && arc_bonus_value(i) == va[k] && arc_bonus_perfect(i) == pf[k]);
        }
    }
    /* Determinism: same seed, same run; different seed differs. */
    {
        ArcBonus a, b, c; int n;
        memset(&a, 0, sizeof a); memset(&b, 0, sizeof b); memset(&c, 0, sizeof c);
        arc_bonus_init(&a, 1, 1234); arc_bonus_init(&b, 1, 1234); arc_bonus_init(&c, 1, 99);
        for (n = 0; n < 300; n++) { arc_bonus_step(&a, 0, 0, 0, 0, 0); arc_bonus_step(&b, 0, 0, 0, 0, 0); arc_bonus_step(&c, 0, 0, 0, 0, 0); }
        CHECK(memcmp(&a, &b, sizeof a) == 0);
        CHECK(memcmp(&a, &c, sizeof a) != 0);
    }
    /* Perfect: a catcher that fills the whole world pops every bubble the frame it appears; no score on pop, the end waits for the frame wrap. */
    {
        ArcBonus a; int n = 0, popped = 0;
        arc_bonus_init(&a, 3, 7);
        while (!a.over && n++ < 6000) {
            popped += arc_bonus_step(&a, 1, 0, 0, ARC_BONUS_WORLD_W, 400);
            if (a.spawned == ARC_BONUS_BUBBLES && !a.nlive && !a.over) CHECK((a.frame & 255) != 0);
        }
        CHECK(a.over && a.perfect && a.caught == ARC_BONUS_BUBBLES && popped == ARC_BONUS_BUBBLES && (a.frame & 255) == 0);
        CHECK(arc_bonus_step(&a, 1, 0, 0, 400, 400) == 0);
    }
    /* Unarmed (no gum) pops nothing. */
    {
        ArcBonus a; int n = 0; arc_bonus_init(&a, 1, 7);
        while (!a.over && n++ < 6000) arc_bonus_step(&a, 0, 0, 0, ARC_BONUS_WORLD_W, 400);
        CHECK(a.over && !a.perfect && a.caught == 0);
    }
    /* Miss: a catcher far away catches nothing; bubbles escape, no perfect, the end lands on a frame wrap. */
    {
        ArcBonus a; int n = 0; arc_bonus_init(&a, 1, 7);
        while (!a.over && n++ < 6000) arc_bonus_step(&a, 1, 0, -500, 10, 10);
        CHECK(a.over && !a.perfect && a.caught == 0 && (a.frame & 255) == 0);
    }
    /* Pump-up per rank. */
    {
        int rk, n;
        for (rk = 1; rk <= 3; rk++) {
            ArcPump p; int last = 0, prog;
            arc_pump_start(&p, rk, 1);
            CHECK(arc_pump_in_window(&p) && arc_pump_progress(&p) == 0);
            for (n = 0; arc_pump_in_window(&p) && n < 1000; n++) {
                prog = arc_pump_progress(&p); CHECK(prog >= last && prog <= ARC_PUMP_STAGES); last = prog;
                arc_pump_step(&p);
            }
            CHECK(n == arc_rank(rk)->pump_frames && p.state == ARC_PUMP_FLYING && arc_pump_progress(&p) == ARC_PUMP_STAGES);
            CHECK(arc_pump_resolve(&p) == 0 && p.state == ARC_PUMP_FLYING); /* outside the window: no window defeat */
            arc_pump_step(&p); CHECK(p.state == ARC_PUMP_FLYING);
            arc_pump_start(&p, rk, 1); arc_pump_step(&p);
            CHECK(arc_pump_resolve(&p) == arc_rank(rk)->defeat_score && p.state == ARC_PUMP_DEFEATED && !arc_pump_in_window(&p));
            CHECK(arc_pump_resolve(&p) == 0); /* pays once */
        }
        { ArcPump p; arc_pump_start(&p, 2, 0); CHECK(!arc_pump_in_window(&p) && p.state == ARC_PUMP_FLYING && arc_pump_progress(&p) == 0 && arc_pump_resolve(&p) == 0); }
        { ArcPump p; arc_pump_start(&p, 1, 1); CHECK(arc_pump_resolve(&p) == 1000); arc_pump_start(&p, 2, 1); CHECK(arc_pump_resolve(&p) == 1500); arc_pump_start(&p, 3, 1); CHECK(arc_pump_resolve(&p) == 2000); }
    }
    /* Lives and continue. */
    {
        ArcLives l; int n;
        arc_lives_start(&l);
        CHECK(l.lives == 3 && l.state == ARC_LIFE_PLAY);
        l.gum = 0; arc_lose_life(&l); CHECK(l.lives == 2 && l.gum == 2 && l.state == ARC_LIFE_PLAY);
        arc_lose_life(&l); CHECK(l.lives == 1 && l.state == ARC_LIFE_PLAY);
        l.score = 12345; arc_lose_life(&l); CHECK(l.lives == 0 && l.state == ARC_LIFE_CONTINUE && arc_continue_seconds(&l) == 10);
        CHECK(arc_continue_step(&l, 1, 0) == 0 && l.state == ARC_LIFE_CONTINUE && l.countdown == ARC_CONTINUE_FRAMES - 1); /* Start without a credit counts down */
        CHECK(arc_continue_step(&l, 0, 1) == 0 && l.state == ARC_LIFE_CONTINUE);
        CHECK(arc_continue_step(&l, 1, 1) == 1 && l.state == ARC_LIFE_PLAY && l.lives == 3 && l.score == 0 && l.gum == 2);
        for (i = 0; i < 3; i++) arc_lose_life(&l);
        for (n = 0; l.state == ARC_LIFE_CONTINUE && n < 1000; n++) arc_continue_step(&l, 0, 5);
        CHECK(n == ARC_CONTINUE_FRAMES && l.state == ARC_LIFE_ENDED);
        arc_lose_life(&l); CHECK(l.state == ARC_LIFE_ENDED && arc_continue_step(&l, 1, 1) == 0);
    }
    /* Bonus reach: a bubble stays on screen long enough to be caught at every bonus number. */
    {
        int num;
        for (num = 1; num <= 6; num++) {
            int32_t visible = (int32_t)(((int64_t)(FLIER_WORLD_H + ARC_BONUS_BOX) << 16) / arc_bonus_speed16(num));
            CHECK(visible >= ARC_BONUS_MIN_VISIBLE);
        }
        CHECK(ARC_BONUS_WORLD_W == ARENA_W);
    }
    /* Nozzle bonus: at most 10 alive, 20 in all, spawn gap 40..103, straight rise 40 px then sway up to 16 px, ends on a frame wrap after all 20 are gone. */
    {
        int s, num, peak = 0, spawned = 0, sway_seen = 0, gap_min = 1000, gap_max = 0, col_seen[ARC_NOZZLE_COUNT] = { 0 };
        for (s = 0; s < 30; s++) for (num = 1; num <= 6; num++) {
            ArcBonus a; int n = 0, alive, last_spawn = 0, prev_live[ARC_BONUS_LIVE_MAX] = { 0 }, first = 1;
            arc_bonus_init(&a, num, (uint32_t)s * 104729u + 3);
            while (!a.over && n++ < 6000) {
                int k;
                arc_bonus_step(&a, 1, 0, -500, 10, 10); /* catches nothing */
                for (alive = 0, i = 0; i < ARC_BONUS_LIVE_MAX; i++) {
                    const ArcBubble *u = &a.b[i];
                    alive += u->live;
                    if (u->live && !prev_live[i]) {
                        int gap = a.frame - last_spawn;
                        spawned++; col_seen[u->nozzle] = 1;
                        CHECK(u->nozzle < ARC_NOZZLE_COUNT && u->x0 >= arc_nozzle_x(u->nozzle) && u->x0 + ARC_BONUS_BOX <= arc_nozzle_x(u->nozzle) + ARC_NOZZLE_W);
                        if (!first) { if (gap < gap_min) gap_min = gap; if (gap > gap_max) gap_max = gap; }
                        first = 0; last_spawn = a.frame;
                    }
                    prev_live[i] = u->live;
                    if (!u->live) continue;
                    k = arc_nozzle_top(u->nozzle) - (int)(u->y16 >> 16);
                    if (k <= ARC_BONUS_STRAIGHT) CHECK(u->x == u->x0);                         /* straight rise */
                    if (u->x != u->x0) { sway_seen = 1; CHECK(u->x >= u->x0 - 16 && u->x <= u->x0 + 16); }
                    CHECK(u->x >= 0 && u->x + ARC_BONUS_BOX <= ARENA_W);
                }
                CHECK(alive == a.nlive && alive <= ARC_BONUS_LIVE_MAX);
                if (alive > peak) peak = alive;
            }
            CHECK(a.over && !a.perfect && a.spawned == ARC_BONUS_BUBBLES && a.nlive == 0 && (a.frame & 255) == 0);
        }
        CHECK(peak >= 6 && peak <= ARC_BONUS_LIVE_MAX && sway_seen && spawned == 30 * 6 * ARC_BONUS_BUBBLES);
        CHECK(gap_min >= 40 && gap_max <= 103); /* skipped spawns (pool full) only lengthen a gap, never below 40 */
        CHECK(col_seen[0] && col_seen[1] && col_seen[2] && col_seen[3]);
        CHECK(ARC_BONUS_BUBBLES == 20 && ARC_BONUS_LIVE_MAX == 8);
        /* the 8 slot pool never skips a spawn: every bubble is gone before LIVE_MAX more spawns can follow it at the minimum gap */
        for (i = 0; i < ARC_NOZZLE_COUNT; i++) {
            int num;
            for (num = 1; num <= 6; num++) {
                int32_t y16 = (int32_t)arc_nozzle_top(i) * 65536; int f = 0;
                while ((int)(y16 >> 16) + ARC_BONUS_BOX > 0) { y16 -= arc_bonus_speed16(num); f++; }
                CHECK(f < ARC_BONUS_LIVE_MAX * ARC_BONUS_SPAWN_MIN);
            }
        }
        CHECK(arc_nozzle_x(0) == 48 && arc_nozzle_x(1) == 120 && arc_nozzle_x(2) == 240 && arc_nozzle_x(3) == 312);
        for (i = 0; i < ARC_NOZZLE_COUNT; i++) CHECK(arc_nozzle_x(i) >= 0 && arc_nozzle_x(i) + ARC_NOZZLE_W <= ARENA_W && arc_nozzle_top(i) > 0 && (i == 0 || arc_nozzle_x(i) >= arc_nozzle_x(i - 1) + ARC_NOZZLE_W));
    }
    printf("%d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
