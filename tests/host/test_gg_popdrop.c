/* test_gg_popdrop.c - Gum Games Pop Drop (free fall): speed ramp, steering and facing, platform hit (stun, gum lost, shield soak), crash on the third hit,
 * score = depth + gums, gum trail (clear of every platform, a follower at full speed never hits), 2P simultaneous fall (push apart, ghost, hop without brake, end when both crashed), game and flow wiring. */
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

/* Trail follower: steer toward the next uncaught trail gum at or below the bird. */
static uint8_t follow(const GgPop *p, const Flier *h, int k)
{
    int i, best = -1, by = PD_BIRD_Y + p->b[k].hop, d;
    for (i = 0; i < PD_GUMS; i++)
        if (p->gum[i].live && p->gum[i].y >= by - 8 && (best < 0 || p->gum[i].y < p->gum[best].y)) best = i;
    if (best < 0) return 0;
    d = arena_dx(p->gum[best].x, h[k].x >> 16);
    return (uint8_t)(d > 2 ? IN_RIGHT : d < -2 ? IN_LEFT : 0);
}

/* 1 when a bird box centred on any live gum would touch no live platform (the fall_step hit test). */
static int trail_clear(const GgPop *p)
{
    int i, j;
    for (i = 0; i < PD_GUMS; i++) {
        const PdGum *g = &p->gum[i];
        if (!g->live) continue;
        for (j = 0; j < PD_PLATS; j++) {
            const PdPlat *q = &p->plat[j];
            int half = 8 * (2 + q->mids), d;
            if (!q->live || q->y >= g->y + PD_BIRD_HALF_H || q->y + PD_PLAT_H <= g->y - PD_BIRD_HALF_H) continue;
            d = arena_dx(g->x, q->x + half); if (d < 0) d = -d;
            if (d < half + PD_BIRD_HALF_W) return 0;
        }
    }
    return 1;
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
        { int k; for (k = 1; k < PD_GUMS; k++) p.gum[k].live = 0; }   /* only the placed gum: no trail gum in reach */
        p.gum[0].bx = p.gum[0].x = (int16_t)(h[0].x >> 16); p.gum[0].ph = 16; p.gum[0].y = PD_BIRD_Y; p.gum[0].live = 1;
        { int k; for (k = 0; k < PD_PLATS; k++) p.plat[k].live = 0; }
        gp_step(&p, h, 0, 0);
    }
    CHECK(p.b[0].gums == (uint16_t)PD_SHIELD_EVERY && p.b[0].shield == 1 && p.b[0].shield_count == 0);

    /* gum trail: 1 gum per gap, every gum clear of every platform, a follower never hits at full speed or on the ramp; each gum counts */
    {
        int seed, spawned = 0, live_max = 0, unclear = 0, moved = 0, wob_bad = 0;
        for (seed = 1; seed <= 24; seed++) {
            gp_init(&p, h, (uint32_t)seed);
            if (seed & 1) p.spd = PD_SPEED_MAX;
            for (i = 0; i < 3000; i++) {
                int k, live = 0;
                gp_step(&p, h, follow(&p, h, 0), 0);
                for (k = 0; k < PD_GUMS; k++) live += p.gum[k].live;
                if (live > live_max) live_max = live;
                if (!trail_clear(&p)) unclear++;
                for (k = 0; k < PD_GUMS; k++) {   /* wobble: current x within +-PD_WOBBLE_PX of the spawn x, and it moves */
                    int dx = arena_dx(p.gum[k].x, p.gum[k].bx);
                    if (!p.gum[k].live) continue;
                    if (dx < 0) dx = -dx;
                    if (dx > PD_WOBBLE_PX) wob_bad++;
                    if (dx > 0) moved++;
                }
                if (p.phase != PD_FALL) break;   /* the pool ends the fall at PD_POOL_DEPTH */
            }
            CHECK(p.b[0].hits == 0 && p.phase == PD_POOL);
            CHECK(p.b[0].score == p.depth + p.b[0].gums + p.b[0].flop && p.b[0].shield && p.b[0].shield_count == p.b[0].gums % PD_SHIELD_EVERY);
            spawned += p.b[0].gums;
            CHECK(p.b[0].gums * 10 > ((p.depth * 8 - 216) / 72) / PD_GUM_EVERY_GAPS * PD_TRAIL_GUMS * 8);   /* over 80 % of the gums caught (was 90 %: a wobbling gum is sometimes missed by the follower's dead band): one gum per PD_GUM_EVERY_GAPS rows (a row every 72+ px, depth = px / 8; the last 216 px before the pool carry no rows) */
        }
        CHECK(unclear == 0 && live_max <= PD_GUMS && spawned > 0 && wob_bad == 0 && moved > 1000);
    }

    /* 2P trail: both birds follow the one trail (bumping each other) and both collect */
    gp_init(&p, h, 11); gp_add_p2(&p, &h[0], &h[1]);
    for (i = 0; i < 1500; i++) gp_step(&p, h, follow(&p, h, 0), follow(&p, h, 1));
    CHECK(p.b[0].gums > 10 && p.b[1].gums > 10);

    /* a bird with no input is hit on aimed rows: 3 hits crash it before the pool, 1P and 2P (both birds idle), over several seeds */
    {
        int seed, k;
        for (seed = 1; seed <= 12; seed++) {
            gp_init(&p, h, (uint32_t)seed);
            for (i = 0; i < 4000 && p.phase == PD_FALL; i++) gp_step(&p, h, 0, 0);
            CHECK(p.b[0].hits == 3 && p.b[0].crash && p.phase == PD_CRASH && p.depth < PD_POOL_DEPTH);
            gp_init(&p, h, (uint32_t)seed); gp_add_p2(&p, &h[0], &h[1]);
            for (i = 0; i < 4000 && p.phase == PD_FALL; i++) gp_step(&p, h, 0, 0);
            for (k = 0; k < 2; k++) CHECK(p.b[k].hits == 3 && p.b[k].crash);
            CHECK(p.phase == PD_CRASH && p.depth < PD_POOL_DEPTH);
        }
    }

    /* three hits crash; the attempt ends with the score, then the result, then done */
    gp_init(&p, h, 7);
    for (i = 0; i < 3; i++) { p.b[0].stun = 0; plat_on_bird(&p, h); gp_step(&p, h, 0, 0); }
    CHECK(p.b[0].hits == 3 && p.phase == PD_CRASH && p.b[0].land == 0);
    {   /* the crash pose lies on the hit island: the island scrolls on during the crash, depth and score stay frozen */
        int16_t y0 = p.plat[0].y; uint16_t d0 = p.depth, s0 = p.b[0].score;
        for (i = 0; i < 10; i++) gp_step(&p, h, 0, 0);
        CHECK(p.phase == PD_CRASH && p.plat[0].y < y0 && p.depth == d0 && p.b[0].score == s0);
    }
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
    p.gum[0].bx = p.gum[0].x = (int16_t)(h[0].x >> 16); p.gum[0].ph = 16; p.gum[0].y = PD_BIRD_Y; p.gum[0].live = 1;
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
    CHECK(p.b[0].crash && p.b[0].land == -1 && !p.b[1].crash && p.phase == PD_FALL && !p.done);   /* the first crash is a ghost, not on an island */
    for (i = 0; i < 20; i++) gp_step(&p, h, 0, 0);
    CHECK(p.b[1].score > p.b[0].score);                                    /* the live bird keeps scoring, the ghost's score stays */
    for (i = 0; i < 3; i++) { p.b[1].stun = 0; plat_on_bird(&p, &h[1]); gp_step(&p, h, 0, 0); }
    CHECK(p.b[1].crash && p.phase == PD_CRASH && p.b[1].land == 0 && p.b[0].land == -1);
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

    /* pool: no platform spawns inside the approach, the fall ends at PD_POOL_DEPTH with a flop (pose from B / C / D, size from speed, cards, points) */
    {
        int n, lowest_y = 0, pool_seen = 0;
        gp_init(&p, h, 7);
        for (n = 0; n < 4000 && p.phase == PD_FALL; n++) {
            int k;
            gp_step(&p, h, 0, 0);
            for (k = 0; k < PD_PLATS; k++) if (p.plat[k].live && p.plat[k].y + PD_PLAT_H + PD_POOL_CLEAR > p.pool_y && p.plat[k].y > lowest_y) lowest_y = p.plat[k].y;
            for (k = 0; k < PD_PLATS; k++) p.plat[k].live = 0;   /* a hit-free run: the pool test needs no platform luck */
            if (p.b[0].hits) break;
        }
        (void)pool_seen;
        CHECK(p.phase == PD_POOL && p.depth == PD_POOL_DEPTH && p.b[0].landed && lowest_y == 0);
        CHECK(p.b[0].pose == PD_POSE_BELLY && p.b[0].card[0] >= 1 && p.b[0].card[0] <= 10 && p.b[0].flop > 0);
        CHECK(p.b[0].score == PD_POOL_DEPTH + p.b[0].gums + p.b[0].flop);
        { uint16_t s = p.b[0].score; for (n = 0; n < (int)PD_POOL_FRAMES + 2; n++) gp_step(&p, h, 0, 0); CHECK(p.phase == PD_RESULT && p.b[0].score == s && p.seq.best[0] == s); }
        /* every platform ever spawned stays clear of the surface (checked on the real spawner, platforms kept) */
        gp_init(&p, h, 11);
        lowest_y = 0;
        for (n = 0; n < 4000 && p.phase == PD_FALL; n++) {
            int k;
            gp_step(&p, h, 0, 0);
            for (k = 0; k < PD_PLATS; k++) if (p.plat[k].live && p.plat[k].y + PD_PLAT_H + PD_POOL_CLEAR > p.pool_y && p.plat[k].y < p.pool_y + 8) lowest_y = 1;
            p.b[0].hits = 0; p.b[0].crash = 0; p.phase = p.phase == PD_CRASH ? PD_FALL : p.phase;
        }
        CHECK(lowest_y == 0 && p.phase == PD_POOL);
    }
    /* flop score: pose latch (last of B / C / D pressed), size by speed, cards deterministic and ordered */
    {
        uint16_t tot[3][3]; int pose, size;
        for (pose = 0; pose < 3; pose++) for (size = 0; size < 3; size++) {
            gp_init(&p, h, 7);
            p.dist = (uint32_t)(PD_POOL_DEPTH * 8u - 10) << 4;          /* 10 px above the pool */
            p.spd = size == 0 ? PD_SPEED_START : size == 1 ? PD_SIZE_MEDIUM : PD_SIZE_BIG;
            gp_step(&p, h, pose == 1 ? IN_B : pose == 2 ? IN_C : IN_D, 0);
            gp_step(&p, h, 0, 0);
            for (i = 0; i < 6 && p.phase == PD_FALL; i++) gp_step(&p, h, 0, 0);
            CHECK(p.phase == PD_POOL && p.b[0].pose == pose && p.b[0].size == size);
            tot[pose][size] = p.b[0].flop;
        }
        CHECK(tot[PD_POSE_BELLY][0] < tot[PD_POSE_BELLY][2] && tot[PD_POSE_FACE][2] > tot[PD_POSE_CANNON][2] && tot[PD_POSE_FACE][0] < tot[PD_POSE_BELLY][0]);
        gp_init(&p, h, 7); gp_step(&p, h, IN_C, 0); gp_step(&p, h, IN_B, 0); gp_step(&p, h, IN_B, 0); CHECK(p.b[0].pose_pick == PD_POSE_CANNON);   /* last press wins */
        CHECK(tot[PD_POSE_FACE][2] + 0u <= 90u && PD_FLOP_MULT * 10u * PD_JUDGES <= 90u);
    }
    /* splash frames advance and hold on the last; the world slows and the birds sink */
    {
        int n;
        gp_init(&p, h, 7); p.dist = (uint32_t)(PD_POOL_DEPTH * 8u - 10) << 4; p.spd = PD_SIZE_BIG;
        for (n = 0; n < 8 && p.phase == PD_FALL; n++) gp_step(&p, h, 0, 0);
        CHECK(p.phase == PD_POOL && p.b[0].size == PD_SPLASH_BIG && p.b[0].splash_f == 0);
        for (n = 0; n < 40; n++) gp_step(&p, h, 0, 0);
        CHECK(p.b[0].splash_f > 0 && p.b[0].splash_f < PD_SPLASH_LEN(PD_SPLASH_BIG) && p.spd == 0 && p.pool_y < PD_BIRD_Y + PD_BIRD_HALF_H);
        for (n = 0; n < 100; n++) gp_step(&p, h, 0, 0);
        CHECK(p.b[0].splash_f == PD_SPLASH_LEN(PD_SPLASH_BIG) - 1);
    }
    /* 2P: a ghost never flops, the survivor does; two survivors flop with their own pose */
    {
        Flier h2[2]; int n;
        gp_init(&p, h2, 7); gp_add_p2(&p, &h2[0], &h2[1]);
        p.dist = (uint32_t)(PD_POOL_DEPTH * 8u - 10) << 4; p.b[0].crash = 1; p.b[0].score = 40; p.spd = PD_SIZE_MEDIUM;
        for (n = 0; n < 10 && p.phase == PD_FALL; n++) gp_step(&p, h2, 0, n == 0 ? IN_B : 0);
        CHECK(p.phase == PD_POOL && !p.b[0].landed && p.b[1].landed && p.b[1].pose == PD_POSE_CANNON && p.b[0].score == 40);
        gp_init(&p, h2, 7); gp_add_p2(&p, &h2[0], &h2[1]);
        p.dist = (uint32_t)(PD_POOL_DEPTH * 8u - 10) << 4; p.spd = PD_SIZE_MEDIUM;
        for (n = 0; n < 10 && p.phase == PD_FALL; n++) gp_step(&p, h2, n == 0 ? IN_C : 0, n == 0 ? IN_B : 0);
        CHECK(p.b[0].landed && p.b[1].landed && p.b[0].pose == PD_POSE_FACE && p.b[1].pose == PD_POSE_CANNON);
        for (n = 0; n < (int)PD_POOL_FRAMES + 2; n++) gp_step(&p, h2, 0, 0);
        CHECK(p.phase == PD_RESULT && p.seq.best[0] == p.b[0].score && p.seq.best[1] == p.b[1].score);
    }
    /* 2P: splash size and flop score are per bird from its own hits; the shared scroll is untouched; qualify needs flop or gums */
    {
        Flier h2[2]; int n;
        gp_init(&p, h2, 7); gp_add_p2(&p, &h2[0], &h2[1]);
        p.dist = (uint32_t)(PD_POOL_DEPTH * 8u - 10) << 4; p.spd = PD_SPEED_MAX; p.b[1].hits = 2;
        for (n = 0; n < 10 && p.phase == PD_FALL; n++) gp_step(&p, h2, 0, 0);
        CHECK(p.phase == PD_POOL && p.b[0].size == PD_SPLASH_BIG && p.b[1].size == PD_SPLASH_MEDIUM && p.b[0].flop > p.b[1].flop && p.b[0].score > p.b[1].score);
        gp_init(&p, h2, 7);   /* 1P: the same rule, via the scroll speed the hits already cut */
        p.dist = (uint32_t)(PD_POOL_DEPTH * 8u - 10) << 4; p.spd = PD_SIZE_MEDIUM;
        for (n = 0; n < 10 && p.phase == PD_FALL; n++) gp_step(&p, h2, 0, 0);
        CHECK(p.b[0].size == PD_SPLASH_MEDIUM);
        CHECK(PD_POOL_DEPTH == 900u && PD_QUALIFY == PD_POOL_DEPTH + 45u && PD_POOL_DEPTH < PD_QUALIFY);
    }
    /* fallers: scheduled, deterministic, drift on, expire, and the platform layout is unchanged by them */
    {
        int n, seen = 0; PdFaller f0[PD_FALLERS]; GgPop q; Flier hq, hp;
        gp_init(&p, &hp, 7);
        for (n = 0; n < 400; n++) { gp_step(&p, &hp, 0, 0); p.b[0].hits = 0; }
        for (i = 0; i < PD_FALLERS; i++) { if (p.fall[i].live) { seen++; CHECK(p.fall[i].kind <= PD_FALLER_SNAIL); } f0[i] = p.fall[i]; }
        CHECK(seen >= 1);
        gp_init(&q, &hq, 7);
        for (n = 0; n < 400; n++) { gp_step(&q, &hq, 0, 0); q.b[0].hits = 0; }
        for (i = 0; i < PD_FALLERS; i++) CHECK(q.fall[i].live == f0[i].live && (!f0[i].live || (q.fall[i].x == f0[i].x && q.fall[i].y == f0[i].y)));
        for (i = 0; i < PD_PLATS; i++) CHECK(q.plat[i].y == p.plat[i].y && q.plat[i].x == p.plat[i].x);
    }

    /* flow: A, then Down three times from Big Blow picks Pop Drop, Start runs it, the best total is the record (either player's best fall, higher is better) */
    {
        Flow f;
        flow_init(&f, 0, 0);
        f.mode = GAME_MODE_PARTY;  /* merged PARTY list: sub_i 0 = Rule of the Round, 4 = Big Blow ... 10 = Poop the Man */
        flow_coin(&f);
        flow_step(&f, IN_A, 0, 0); flow_step(&f, 0, 0, 0); /* A opens the GUM GAMES list */
        for (i = 0; i < 7; i++) { flow_step(&f, IN_DOWN, 0, 0); flow_step(&f, 0, 0, 0); }
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
