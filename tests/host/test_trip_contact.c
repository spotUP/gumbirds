/* Gum Trip contact rules through game_step_trip (user approved):
 *  - hero, TOP wall: bounces down (vy reflected), keeps its gum, stays alive and fully visible.
 *  - hero, BOTTOM wall: dies on the contact frame (the fall starts at once, no bounce), through spawn protection too, plays the hit event.
 *  - hero, hazards (coal, vent, cloud): one gum chunk, cooldown, pushed out of the box, velocity away; pushed out again during the cooldown without a second loss.
 *  - boxes COAL 9/9, VENT 9/14, CLOUD 17/13 (half width / half height).
 *  - blink: flier_view_visible toggles while protected, steady otherwise.
 * Every case drives game_step_trip (not only the helpers) on a hand-made course: every held chunk gets window 40..140, no strips, no pickup,
 * and no hazard except the one a case places. */
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "../../src/core/game.h"
#include "../../src/core/flier_view.h"

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; if (failures <= 60) printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

static Game g;

/* Window 40..140 everywhere, nothing else on the course; keep_haz leaves the hazards alone. */
static void flatten(int keep_haz) {
    int i;
    for (i = 0; i < TRIP_GEN_RING; i++) {
        TripChunk *c = &g.trip_gen.ring[i];
        c->win_top = 40; c->win_bottom = 140; c->island.present = 0; c->pickup.present = 0;
        c->band_top = 40; c->band_bottom = 140;
        if (!keep_haz) c->n_haz = 0;
    }
    for (i = 0; i < TRIP_RIVAL_MAX; i++) g.trip_rivals.r[i].active = 0;
}
/* Fresh run on the flat course, hero at (x, y) px with the given velocity (px per frame), protection cleared. */
static void setup(int x, int y, int vx, int vy) {
    game_reset(&g, 11);
    game_set_mode(&g, GAME_MODE_TRIP);
    while (!game_trip_ready(&g)) game_step(&g, 0);
    flatten(0);
    g.flier.spawn_inv = 0; g.flier.invincible = 0;
    g.flier.x = FL_PX(x); g.flier.y = FL_PX(y); g.flier.vx = vx * 65536; g.flier.vy = vy * 65536;
}
static void step1(int keep_haz) { flatten(keep_haz); game_step(&g, 0); }
static int hero_fh(void) { return (int)(flier_half_h(&g.flier) >> 16) + 1; }
static TripGenHazard *put_haz(int chunk, int kind, int hw, int hh, int x_world, int y) {
    TripChunk *c = (TripChunk *)tripgen_get(&g.trip_gen, (uint32_t)chunk);
    TripGenHazard *h;
    if (!c) return 0;
    h = &c->haz[0];
    memset(h, 0, sizeof *h);
    h->kind = (uint8_t)kind; h->hw = (uint8_t)hw; h->hh = (uint8_t)hh;
    h->x = (int16_t)(x_world - (int)c->wx); h->y = (int16_t)y;
    c->n_haz = 1;
    return h;
}

static void test_bottom_wall(void) {
    unsigned i;
    for (i = 0; i < 2; i++) {   /* 0: unprotected, 1: spawn protected (the wall overrides protection) */
        setup(160, 132, 0, 3);
        g.flier.spawn_inv = i ? 30 : 0;
        step1(0);
        CHECK(g.flier.state == FLIER_FALLING);          /* dies on the contact frame */
        CHECK(g.trip.gum == 0 && g.trip.hits == 1);
        CHECK(g.flier.balloons == 0 && g.flier.vy == FLIER_FALL_START_VY);   /* the fall's own start velocity (a hop up), not a wall bounce */
        CHECK(g.trip_events & TRIP_EV_HIT);             /* the hit event reaches the sound path */
    }
    /* a dead hero is not clamped back into the window: it keeps falling through the bottom wall line */
    {
        int32_t y0;
        setup(160, 132, 0, 3); step1(0);
        y0 = g.flier.y;
        for (i = 0; i < 6; i++) step1(0);
        for (i = 0; i < 40; i++) step1(0);
        CHECK(g.flier.y > y0 && (g.flier.y >> 16) > 140);   /* past the wall line, never clamped back */
        CHECK(g.trip.hits == 1);                         /* one death, not one per frame */
    }
}

static void test_top_wall(void) {
    uint32_t gum0;
    setup(160, 66, 0, -3);
    gum0 = g.trip.gum;
    step1(0);
    CHECK(g.flier.state == FLIER_ALIVE && g.flier.balloons == 2);
    CHECK(g.trip.hits == 0 && gum0 - g.trip.gum <= 1u);   /* decay only, no gum loss */
    CHECK(g.flier.vy > 0);                              /* bounced down */
    CHECK((g.flier.y >> 16) >= 65);                     /* back on the gum-top line (65.5), not inside the rock */
    CHECK(!(g.trip_events & TRIP_EV_HIT));
    CHECK(flier_view_visible(&g.flier, g.frame));       /* fully visible: it got no protection */
}

static void test_hazards(void) {
    static const struct { uint8_t kind, hw, hh; } K[3] = { { 0, 9, 9 }, { 1, 9, 14 }, { 2, 17, 13 } };
    int k, from;
    for (k = 0; k < 3; k++) {
        CHECK(tripgen_haz_hw(K[k].kind) == K[k].hw && tripgen_haz_hh(K[k].kind) == K[k].hh);
        for (from = 0; from < 2; from++) {   /* 0: dropped onto the hazard from above, 1: flown into it from the left */
            int hy = 90, dx, dy, fh, hits0;
            uint32_t gum0;
            setup(160, 90, 0, 0);
            fh = hero_fh();
            if (from == 0) { g.flier.y = FL_PX(hy - K[k].hh - fh - 1); g.flier.vy = 3 * 65536; }
            else { g.flier.x = FL_PX(160 - K[k].hw - 2 - 2); g.flier.vx = 3 * 65536; }
            put_haz((int)((g.trip.px + 160u) / TRIP_CHUNK_PX), K[k].kind, K[k].hw, K[k].hh, 160, hy);
            gum0 = g.trip.gum; hits0 = (int)g.trip.hits;
            step1(1);
            CHECK((int)g.trip.hits == hits0 + 1);
            CHECK(gum0 - g.trip.gum >= (uint32_t)GUM_HIT_CHUNK && gum0 - g.trip.gum <= (uint32_t)GUM_HIT_CHUNK + 1u);
            CHECK(g.flier.invincible > 0);              /* the cooldown */
            CHECK(g.trip_events & TRIP_EV_HIT);
            dx = (int)(g.flier.x >> 16) - (160 - (int)g.trip.px); dy = (int)(g.flier.y >> 16) - hy;
            CHECK((dx < 0 ? -dx : dx) > K[k].hw + FLIER_HALF_W || (dy < 0 ? -dy : dy) > K[k].hh + fh);   /* outside the box */
            if (from == 0) CHECK(g.flier.vy < 0 && dy < 0);   /* away: up */
            else CHECK(g.flier.vx < 0 && dx < 0);             /* away: left */
            /* cooldown: shoved into the hazard again, pushed out again, no second loss */
            {
                uint32_t gum1 = g.trip.gum;
                g.flier.x = FL_PX(160 - (int)g.trip.px); g.flier.y = FL_PX(hy - 1); g.flier.vx = 0; g.flier.vy = 0;
                step1(1);
                dx = (int)(g.flier.x >> 16) - (160 - (int)g.trip.px); dy = (int)(g.flier.y >> 16) - hy;
                CHECK((int)g.trip.hits == hits0 + 1 && gum1 - g.trip.gum <= 1u);
                CHECK((dx < 0 ? -dx : dx) > K[k].hw + FLIER_HALF_W || (dy < 0 ? -dy : dy) > K[k].hh + hero_fh());
            }
        }
    }
}

/* Recorded outcomes, not rules: the user asked for the left-edge pin and the island edge to be reported. */
static void test_records(void) {
    int dx;
    /* left edge: a hazard right at the screen's left edge pushes the hero left; the x clamp at 0 leaves it inside the box. */
    setup(4, 90, -3, 0);
    put_haz(0, 0, 9, 9, 6, 90);
    step1(1);
    dx = (int)(g.flier.x >> 16) - 6;
    CHECK(g.flier.x >= 0 && g.flier.x <= FL_PX(319));
    printf("RECORD left-edge pin: hero x %d after the push, hazard x 6 hw 9, overlapping %d, hits %u\n",
           (int)(g.flier.x >> 16), (dx < 0 ? -dx : dx) <= 9 + FLIER_HALF_W, (unsigned)g.trip.hits);
    /* island edge: hero above an island with a hazard pushing it down into the island solid. */
    setup(100, 60, 0, 0);
    {   /* px is 0 at the start, so world x equals screen x for this step */
        TripChunk *c = (TripChunk *)tripgen_get(&g.trip_gen, 0);
        put_haz(0, 0, 9, 9, 100, 62);
        c->island.present = 1; c->island.x = 60; c->island.y = 80; c->island.w = 90;
        g.flier.y = FL_PX(70);
        c->island.present = 1;
        game_step(&g, 0);
        printf("RECORD island edge: hero y %d after the push (island top 80, hazard y 62 hh 9), state %d, hits %u\n",
               (int)(g.flier.y >> 16), g.flier.state, (unsigned)g.trip.hits);
    }
}

static void test_blink(void) {
    Flier f;
    uint32_t fr;
    int shown = 0, hidden = 0, prev = -1, toggles = 0;
    memset(&f, 0, sizeof f);
    f.state = FLIER_ALIVE;
    for (fr = 0; fr < 64; fr++) CHECK(flier_view_visible(&f, fr) == 1);   /* unprotected: always shown */
    f.invincible = 10;
    for (fr = 0; fr < 64; fr++) {
        int v = flier_view_visible(&f, fr);
        CHECK(v == (int)(((fr / FLIER_BLINK_HALF_PERIOD) & 1u) == 0));
        if (v) shown++; else hidden++;
        if (prev >= 0 && v != prev) toggles++;
        prev = v;
    }
    CHECK(shown == hidden && toggles == 63 / FLIER_BLINK_HALF_PERIOD);
    f.invincible = 0; f.spawn_inv = 5;
    CHECK(flier_view_visible(&f, FLIER_BLINK_HALF_PERIOD) == 0);   /* spawn protection blinks too */
    f.state = FLIER_FALLING;
    for (fr = 0; fr < 16; fr++) CHECK(flier_view_visible(&f, fr) == 1);   /* a falling body is never hidden */
    /* Trip: after a hazard hit the hero blinks for the whole cooldown and is steady after it */
    {
        int seen_hidden = 0, seen_shown = 0, i, steady = 1;
        setup(160, 80, 0, 3);
        put_haz(0, 0, 9, 9, 160, 90);
        step1(1);
        CHECK(g.trip.hits == 1 && g.flier.invincible > 0);
        while (g.flier.invincible > 0 && g.flier.state == FLIER_ALIVE) {
            if (flier_view_visible(&g.flier, g.frame)) seen_shown = 1; else seen_hidden = 1;
            flatten(0); g.flier.y = FL_PX(80); g.flier.vy = 0;
            game_step(&g, 0);
        }
        CHECK(seen_shown && seen_hidden);
        for (i = 0; i < 32; i++) {
            flatten(0); g.flier.y = FL_PX(80); g.flier.vy = 0; game_step(&g, 0);
            if (!flier_view_visible(&g.flier, g.frame)) steady = 0;
        }
        CHECK(steady);
    }
}

int main(void) {
    test_bottom_wall();
    test_top_wall();
    test_hazards();
    test_records();
    test_blink();
    printf("%s: %d checks, %d failures\n", failures ? "FAIL" : "PASS", checks, failures);
    return failures != 0;
}
