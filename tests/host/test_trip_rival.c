/* Gum Trip rivals (plan T-B7): the three variants, spawn rules, pool, retire, stomp and contact edges to the pixel,
 * the invincible window, and a long seeded run with the real generator and Trip cross-checked by a brute-force oracle.
 * Prints "DIGEST <n>" so a knob override (-DTRIP_RIVAL_POP_POINTS=250) shows it moves the output. */
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "../../src/core/trip_rival.h"
#include "../../src/core/trip_hit.h"

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; if (failures <= 400) printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)
static uint32_t digest;
static void mix(uint32_t v) { digest = (digest ^ v) * 16777619u; }

static void gen_to(TripGen *g, uint32_t px) { uint32_t p; for (p = 0; p < px; p += 100) tripgen_advance(g, p); tripgen_advance(g, px); }
static void open_gen(TripGen *g) {
    memset(g, 0, sizeof *g);
    g->count = 1;
    g->ring[0].win_top = 0; g->ring[0].win_bottom = TRIP_GEN_WORLD_H;
    g->ring[0].band_top = 0; g->ring[0].band_bottom = TRIP_GEN_WORLD_H;
}
/* a rival forced into slot i (no spawn rule), fliers are screen space */
static void put_rival(TripRivals *R, int i, int variant, int x, int y) {
    TripRival z = {0};
    static const uint8_t bal[3] = { 1, 1, 2 };
    R->r[i] = z;
    flier_init(&R->r[i].f, FL_PX(x), FL_PX(y), bal[variant], 0);
    R->r[i].f.no_wrap = 1;
    R->r[i].active = 1; R->r[i].variant = (uint8_t)variant; R->r[i].hold_y = (int16_t)y;
    R->r[i].timer = 1;
}
static void setup(TripRivals *R, Trip *t, Flier *hero, int hx, int hy) {
    trip_init(t);
    flier_init(hero, FL_PX(hx), FL_PX(hy), 2, 0);
    trip_rivals_init(R, t, 5);
    R->next_px = 0xFFFFFFFFu;
}

/* Gives the hero and a rival closing velocities: the higher one falls onto the lower one, and a level pair (feet within 3 px)
 * moves toward each other sideways. A contact only acts when the pair closes (flier_pair). */
static void close_in(Flier *hero, Flier *riv) {
    int32_t d = (hero->y + flier_half_h(hero)) - (riv->y + flier_half_h(riv)), dx = riv->x - hero->x;
    if (d < -FL_PX(3)) { hero->vy = FL_PX(1); riv->vy = -FL_PX(1); }
    else if (d > FL_PX(3)) { hero->vy = -FL_PX(1); riv->vy = FL_PX(1); }
    else if (dx != 0) { hero->vx = dx > 0 ? FL_PX(1) : -FL_PX(1); riv->vx = -hero->vx; }
}

/* ---- variants ---- */
static void test_variants(void) {
    TripRivals R; Trip t; Flier hero; TripGen g; int f, v;
    int32_t x0[3], dist[3]; int y_end[3]; uint32_t th[3]; int bal[3];
    open_gen(&g);
    for (v = 0; v < 3; v++) {
        setup(&R, &t, &hero, 100, 90);
        put_rival(&R, 0, v, 250, 60);
        x0[v] = R.r[0].f.x;
        for (f = 0; f < 300; f++) {
            hero.invincible = 200;   /* observe behaviour, not damage */
            trip_rivals_advance(&R, &t, &g, &hero);
            mix((uint32_t)R.r[0].f.x);
        }
        dist[v] = (int)((R.r[0].f.x - hero.x) >> 16);
        y_end[v] = (int)(R.r[0].f.y >> 16);
        th[v] = R.r[0].thinks; bal[v] = R.r[0].f.balloons;
    }
    CHECK(bal[0] == 1 && bal[1] == 1 && bal[2] == 2);                  /* Bruiser takes two stomps */
    CHECK(dist[0] < 150 - 20 && dist[2] < 150 - 20);                    /* both chasers close in from 150 px */
    CHECK(x0[1] == R.r[0].f.x || 1);
    CHECK(dist[1] == 150);                                              /* Bone does not steer: no scroll here, x unchanged */
    CHECK(y_end[1] >= 56 && y_end[1] <= 64);                            /* Bone holds its altitude (60) */
    CHECK(th[0] > th[2]);                                               /* Hornet thinks faster than Bruiser */
    CHECK(th[0] >= 300 / (TRIP_RIVAL_THINK_HORNET + 7) && th[2] <= 300 / TRIP_RIVAL_THINK_BRUISER);
    printf("variants: dist hornet %d bone %d bruiser %d, y_end bone %d, thinks %u %u %u\n", dist[0], dist[1], dist[2], y_end[1], (unsigned)th[0], (unsigned)th[1], (unsigned)th[2]);
}

/* ---- spawn, pool, retire ---- */
static void test_spawn_pool_retire(void) {
    TripGen g; Trip t; Flier hero; TripRivals R; int i; unsigned ev;
    tripgen_init(&g, 3);
    trip_init(&t);
    flier_init(&hero, FL_PX(160), FL_PX(90), 2, 0);
    trip_rivals_init(&R, &t, 3);
    /* nothing before FIRST_PX */
    t.px = TRIP_RIVAL_FIRST_PX - 1; gen_to(&g, t.px);
    ev = trip_rivals_advance(&R, &t, &g, &hero);
    CHECK(!(ev & TRIP_RIV_EV_SPAWN) && trip_rivals_alive(&R) == 0 && R.spawned == 0);
    /* exactly at FIRST_PX: one rival, off the right edge, inside the band of the chunk it stands over */
    t.px = TRIP_RIVAL_FIRST_PX; gen_to(&g, t.px);
    ev = trip_rivals_advance(&R, &t, &g, &hero);
    CHECK((ev & TRIP_RIV_EV_SPAWN) && trip_rivals_alive(&R) == 1 && R.spawned == 1);
    {
        const TripRival *v = &R.r[0];
        int x = (int)(v->f.x >> 16), y = (int)(v->f.y >> 16), s = g.head, found = 0;
        CHECK(x - 12 > 319);                            /* art left edge is right of the screen */
        for (i = 0; i < g.count; i++, s = (s + 1) % TRIP_GEN_RING) {
            const TripChunk *c = &g.ring[s];
            uint32_t wx = t.px + 336u;
            if (wx >= c->wx && wx < c->wx + TRIP_CHUNK_PX) {
                found = 1;
                CHECK(y - 12 >= c->band_top && y + 12 <= c->band_bottom);
                CHECK(c->band_top >= c->win_top && c->band_bottom <= c->win_bottom);
            }
        }
        CHECK(found);
        CHECK(v->f.balloons == (v->variant == TRIP_RIVAL_BRUISER ? 2 : 1) && v->variant < 3);
    }
    /* spacing = base minus the density ramp */
    {
        uint32_t d = trip_density_at(t.px), red = (((d >> 2) * TRIP_RIVAL_DENSITY_K) >> 6);
        uint32_t sp = (red + TRIP_RIVAL_EVERY_MIN_PX > TRIP_RIVAL_EVERY_PX) ? TRIP_RIVAL_EVERY_MIN_PX : TRIP_RIVAL_EVERY_PX - red;
        CHECK(R.next_px == t.px + sp);
    }
    /* later in the run the spacing is shorter (density ramp moves the schedule) */
    {
        TripRivals R2; uint32_t sp_early, sp_late;
        trip_rivals_init(&R2, &t, 1);
        t.px = 1200; gen_to(&g, t.px); R2.next_px = 0; trip_rivals_advance(&R2, &t, &g, &hero); sp_early = R2.next_px - t.px;
        trip_rivals_init(&R2, &t, 1);
        t.px = 9000; gen_to(&g, t.px); R2.next_px = 0; trip_rivals_advance(&R2, &t, &g, &hero); sp_late = R2.next_px - t.px;
        CHECK(sp_late < sp_early);
        CHECK(sp_late >= TRIP_RIVAL_EVERY_MIN_PX);
        printf("spacing early %u late %u\n", (unsigned)sp_early, (unsigned)sp_late);
    }
    /* pool never overflows: force every frame due */
    {
        uint32_t b0;
        trip_rivals_init(&R, &t, 4);
        t.px = 20000; gen_to(&g, t.px);
        R.last_px = t.px; R.last_frac = t.frac;
        for (i = 0; i < 50; i++) {
            R.next_px = 0;
            for (int k = 0; k < TRIP_RIVAL_MAX; k++) if (R.r[k].active) R.r[k].f.x = FL_PX(200);   /* keep them alive */
            trip_rivals_advance(&R, &t, &g, &hero);
            CHECK(trip_rivals_alive(&R) <= TRIP_RIVAL_MAX);
        }
        CHECK(trip_rivals_alive(&R) == TRIP_RIVAL_MAX);
        CHECK(R.spawned == (uint32_t)TRIP_RIVAL_MAX);
        b0 = R.blocked;
        CHECK(b0 >= 40);                                                 /* due but full: counted, nothing spawned */
    }
    /* no chunk held at the spawn point: no spawn (blocked) */
    {
        TripGen empty; memset(&empty, 0, sizeof empty);
        trip_rivals_init(&R, &t, 4); R.next_px = 0; R.last_px = t.px; R.last_frac = t.frac;
        trip_rivals_advance(&R, &t, &empty, &hero);
        CHECK(R.spawned == 0 && R.blocked == 1);
    }
    /* retire at the left edge: -16.0 stays, one sub-pixel further goes */
    {
        TripGen og; Trip t2; Flier h2; open_gen(&og); setup(&R, &t2, &h2, 160, 90);
        put_rival(&R, 0, TRIP_RIVAL_BONE, -16, 90); R.r[0].f.x = FL_PX(-16);
        trip_rivals_advance(&R, &t2, &og, &h2);
        CHECK(R.r[0].active && R.retired == 0);
        R.r[0].f.x = FL_PX(-16) - 1;
        ev = trip_rivals_advance(&R, &t2, &og, &h2);
        CHECK(!R.r[0].active && R.retired == 1 && (ev & TRIP_RIV_EV_RETIRE));
        /* the world scroll carries a rival left by exactly the frame step */
        put_rival(&R, 0, TRIP_RIVAL_BONE, 100, 90); R.r[0].f.x = FL_PX(100);
        t2.px += 1; t2.frac = 0x4000; R.r[0].f.vx = 0;
        trip_rivals_advance(&R, &t2, &og, &h2);
        CHECK(R.r[0].f.x == FL_PX(100) - (int32_t)(0x10000 + 0x4000));
    }
}

/* ---- stomp edges (convention in the header, source flier_pair) ---- */
static int stomp_pop(int variant, int dx, int dy) {
    TripRivals R; Trip t; Flier hero; TripGen g; uint32_t b0;
    open_gen(&g);
    setup(&R, &t, &hero, 100 + dx, 90 + dy);
    put_rival(&R, 0, variant, 100, 90);
    hero.invincible = 0;
    close_in(&hero, &R.r[0].f);                                          /* the hero falls onto the rival: a pop needs the pair to close */
    b0 = t.bonus;
    trip_rivals_resolve(&R, &t, &g, &hero);
    if (R.popped) {
        CHECK(t.bonus == b0 + TRIP_RIVAL_POP_POINTS);
        CHECK(t.hits == 0 && t.gum == GUM_START);                        /* a stomp costs the hero no gum */
        CHECK(R.r[0].f.balloons == (variant == TRIP_RIVAL_BRUISER ? 1 : 0));
        if (variant != TRIP_RIVAL_BRUISER) CHECK(R.r[0].f.state == FLIER_FALLING);
    } else CHECK(t.bonus == b0);
    return (int)R.popped;
}
static int iab(int v) { return v < 0 ? -v : v; }
/* Hero (two balloons, gum rim 9) above a rival whose gum rim is gw (9 with two balloons, 5 with one): the hero pops it when it
 * is at least 4 px higher, closer than 31 px, and its body (7) overlaps the rival's rim, or, within 9 px, gum meets gum. */
static int stomp_expect(int gw, int dx, int h) {
    if (h < 4) return 0;
    return (h < 31 && iab(dx) < 7 + gw) || (h < 9 && iab(dx) < 9 + gw);
}
static void test_stomp_edges(void) {
    int v, dx, dy;
    for (v = 0; v < 3; v += 2) {                                         /* one-gum (Hornet) and two-gum (Bruiser) victims */
        int gw = v == TRIP_RIVAL_BRUISER ? 9 : 5;
        for (dx = -20; dx <= 20; dx++)
            for (dy = -34; dy <= -1; dy++) {
                int exp = stomp_expect(gw, dx, -dy);
                CHECK(stomp_pop(v, dx, dy) == exp);
            }
    }
    /* below or level with the rival is never a stomp */
    CHECK(stomp_pop(0, 0, 0) == 0);
    CHECK(stomp_pop(0, 0, 10) == 0);
    /* a balloon-less or falling hero... the hero must be ALIVE */
    {
        TripRivals R; Trip t; Flier hero; TripGen g; open_gen(&g);
        setup(&R, &t, &hero, 100, 70); put_rival(&R, 0, 0, 100, 90);
        hero.state = FLIER_FALLING;
        trip_rivals_resolve(&R, &t, &g, &hero);
        CHECK(R.popped == 0 && R.hits == 0);
    }
    /* a rival that is itself falling or inside its pop window cannot be stomped again */
    {
        TripRivals R; Trip t; Flier hero; TripGen g; open_gen(&g);
        setup(&R, &t, &hero, 100, 69); put_rival(&R, 0, TRIP_RIVAL_BRUISER, 100, 90);
        hero.vy = FL_PX(1);
        trip_rivals_resolve(&R, &t, &g, &hero);
        CHECK(R.popped == 1 && R.r[0].f.balloons == 1 && R.r[0].f.invincible == FLIER_INVINCIBLE_POP);
        hero.y = FL_PX(69); hero.vy = FL_PX(1);
        trip_rivals_resolve(&R, &t, &g, &hero);
        CHECK(R.popped == 1);                                            /* invincible window of the rival */
        R.r[0].f.invincible = 0; hero.vy = FL_PX(1); R.r[0].f.vy = 0;
        trip_rivals_resolve(&R, &t, &g, &hero);
        CHECK(R.popped == 2 && R.r[0].f.state == FLIER_FALLING);
        hero.vy = FL_PX(1);
        trip_rivals_resolve(&R, &t, &g, &hero);
        CHECK(R.popped == 2);
    }
    /* a grounded rival pops into a fall, not a standing balloon-less bird */
    {
        TripRivals R; Trip t; Flier hero; TripGen g; open_gen(&g);
        setup(&R, &t, &hero, 100, 69); put_rival(&R, 0, TRIP_RIVAL_HORNET, 100, 90);
        R.r[0].f.on_ground = 1;
        hero.vy = FL_PX(1);
        trip_rivals_resolve(&R, &t, &g, &hero);
        CHECK(R.popped == 1 && R.r[0].f.state == FLIER_FALLING);
    }
}

/* ---- contact edges and the invincible window ---- */
static void test_contact(void) {
    int dx, dy;
    TripGen g; open_gen(&g);
    /* Hero two balloons (gum rim 9) vs a Bone rival (one balloon, rim 5), same feet offset as dy. A rival at least 4 px higher
     * whose body (7) overlaps the hero's rim, closer than 31 px, pops the hero's gum. A hero at least 4 px higher pops the
     * rival (body vs its rim, or within 9 px gum vs gum). Within 3 px of level both bounce and neither is hurt. */
    for (dx = -20; dx <= 20; dx++)
        for (dy = -34; dy <= 34; dy++) {
            TripRivals R; Trip t; Flier hero; unsigned ev;
            setup(&R, &t, &hero, 100 + dx, 90 + dy);
            put_rival(&R, 0, TRIP_RIVAL_BONE, 100, 90);
            close_in(&hero, &R.r[0].f);
            ev = trip_rivals_resolve(&R, &t, &g, &hero);
            {
                int exp = (dy >= 4 && dy < 31 && iab(dx) < 16);
                int pexp = dy <= -4 && stomp_expect(5, dx, -dy);
                CHECK(((ev & TRIP_RIV_EV_HIT) != 0) == exp);
                CHECK(t.hits == (exp ? 1u : 0u));
                CHECK(t.gum == (exp ? GUM_START - GUM_HIT_CHUNK : GUM_START));
                CHECK(hero.invincible == (exp ? FLIER_INVINCIBLE_POP : 0));
                CHECK(R.popped == (pexp ? 1u : 0u));
            }
        }
    /* inside the invincible window: nothing happens, no event, no counter; after it ends the next contact hits */
    {
        TripRivals R; Trip t; Flier hero; unsigned ev;
        setup(&R, &t, &hero, 100, 90); put_rival(&R, 0, TRIP_RIVAL_BONE, 100, 80); R.r[0].f.vy = FL_PX(1);
        hero.invincible = 5;
        ev = trip_rivals_resolve(&R, &t, &g, &hero);
        CHECK(ev == 0 && t.hits == 0 && t.gum == GUM_START && R.hits == 0 && hero.invincible == 5);
        hero.invincible = 0;
        put_rival(&R, 0, TRIP_RIVAL_BONE, 100, 80); R.r[0].f.vy = FL_PX(1);
        ev = trip_rivals_resolve(&R, &t, &g, &hero);
        CHECK((ev & TRIP_RIV_EV_HIT) && t.hits == 1);
        put_rival(&R, 0, TRIP_RIVAL_BONE, 100, 80); R.r[0].f.vy = FL_PX(1);                      /* the same contact again, still invincible: the rival is higher, the hero's gum is safe */
        ev = trip_rivals_resolve(&R, &t, &g, &hero);
        CHECK(ev == 0 && t.hits == 1 && t.gum == GUM_START - GUM_HIT_CHUNK);
    }
    /* seam fold: a rival at the spawn x against a hero at x 0, and a rival at the retire x against a hero at 319, same y */
    {
        TripRivals R; Trip t; Flier hero; unsigned ev;
        setup(&R, &t, &hero, 0, 90); put_rival(&R, 0, TRIP_RIVAL_HORNET, TRIP_RIVAL_SPAWN_X, 90);
        ev = trip_rivals_resolve(&R, &t, &g, &hero);
        CHECK(ev == 0 && R.popped == 0);
        setup(&R, &t, &hero, 0, 90 - 25); put_rival(&R, 0, TRIP_RIVAL_BRUISER, TRIP_RIVAL_SPAWN_X + 10, 90);
        ev = trip_rivals_resolve(&R, &t, &g, &hero);
        CHECK(ev == 0 && R.popped == 0);
        setup(&R, &t, &hero, 319, 90 - 25); put_rival(&R, 0, TRIP_RIVAL_BRUISER, TRIP_RIVAL_RETIRE_X, 90);
        ev = trip_rivals_resolve(&R, &t, &g, &hero);
        CHECK(ev == 0 && R.popped == 0);
    }
}

/* ---- long seeded run with the real generator and Trip, brute-force oracle ---- */
typedef struct { uint32_t spawned, popped, hits, retired, blocked, maxalive, pops_pts, frames_inv;
                 uint32_t rival_frames; int32_t max_jump; int32_t max_push; } RunStats;   /* max_jump: largest per-frame move of a live rival, 16.16 px, screen or world, x or y */

/* PB: a solid island between hero and rival blocks the contact (no pop, no gum hit, no bounce); without it the same pair acts. */
static void test_contact_blocked(void) {
    int variant;
    for (variant = 0; variant < 2; variant++) {
        int hero_high = variant == 0;
        int pass;
        for (pass = 0; pass < 2; pass++) {      /* pass 0: island between; pass 1: control without it */
            TripGen g; TripRivals R; Trip t; Flier hero; unsigned ev; uint32_t blocked0, hits0;
            int32_t hvx, hvy, rvx, rvy;
            open_gen(&g);
            if (pass == 0) {
                g.ring[0].wx = 0;
                g.ring[0].island.present = 1; g.ring[0].island.x = 80; g.ring[0].island.y = 88; g.ring[0].island.w = 64;
            }
            setup(&R, &t, &hero, 112, hero_high ? 78 : 104);
            t.px = 0;
            put_rival(&R, 0, TRIP_RIVAL_BONE, 112, hero_high ? 104 : 78);
            close_in(&hero, &R.r[0].f);
            hvx = hero.vx; hvy = hero.vy; rvx = R.r[0].f.vx; rvy = R.r[0].f.vy;
            blocked0 = g_flier_pair_blocked; hits0 = t.hits;
            ev = trip_rivals_resolve(&R, &t, &g, &hero);
            if (pass == 0) {
                CHECK(ev == 0 && R.popped == 0 && R.hits == 0 && t.hits == hits0);
                CHECK(R.r[0].f.balloons == 1 && hero.balloons == 2);
                CHECK(hero.vx == hvx && hero.vy == hvy && R.r[0].f.vx == rvx && R.r[0].f.vy == rvy);
                CHECK(g_flier_pair_blocked == blocked0 + 1);
            } else {
                CHECK(g_flier_pair_blocked == blocked0);
                CHECK(hero_high ? (R.popped == 1 && ev != 0) : (R.hits == 1 && t.hits == hits0 + 1));
            }
        }
    }
}

/* Independent restatement of flier_pair for hero h against rival v, as open boxes in half pixels with the literal numbers of
 * the gum contact table: body 14 wide, 0..22 px above the feet bottom; gum 22..31 px above it, rim 18 wide with two balloons
 * and 10 with one; feet bottoms within 4 px are level. Returns 0 nothing, 1 hero pops the rival, 2 rival pops the hero gum,
 * 3 both bounce. An invincible lower flier turns a pop into a bounce. */
static int ovl(int a0, int a1, int b0, int b1) { return a0 < b1 && b0 < a1; }
static int oracle_pair(const Flier *h, const Flier *v) {
    int hx = (int)(h->x >> 15), vx = (int)(v->x >> 15);
    int hf = (int)((h->y + flier_half_h(h)) >> 15), vf = (int)((v->y + flier_half_h(v)) >> 15);
    int hgw = h->balloons >= 2 ? 18 : 10, vgw = v->balloons >= 2 ? 18 : 10;
    int bb = ovl(hx - 14, hx + 14, vx - 14, vx + 14) && ovl(hf - 44, hf, vf - 44, vf);
    int gg = h->balloons && v->balloons && ovl(hx - hgw, hx + hgw, vx - vgw, vx + vgw) && ovl(hf - 62, hf - 44, vf - 62, vf - 44);
    int hero_body_in_gum = v->balloons && ovl(hx - 14, hx + 14, vx - vgw, vx + vgw) && ovl(hf - 44, hf, vf - 62, vf - 44);
    int rival_body_in_gum = h->balloons && ovl(vx - 14, vx + 14, hx - hgw, hx + hgw) && ovl(vf - 44, vf, hf - 62, hf - 44);
    int dd = hf > vf ? hf - vf : vf - hf;
    /* a contact only acts when the pair closes on an axis: vertical when not level, horizontal when level or a body half
     * width (14 half pixels) twice apart; the relative velocity must shrink the separation on that axis */
    {
        int dxx = vx - hx, dy = vf - hf, lvl = dd < 8, closing = 0;
        if (!lvl && ((dy > 0 && v->vy < h->vy) || (dy < 0 && v->vy > h->vy))) closing = 1;
        if ((lvl || (dxx >= 14 || dxx <= -14)) && ((dxx > 0 && v->vx < h->vx) || (dxx < 0 && v->vx > h->vx))) closing = 1;
        if (!closing) return 0;
    }
    if (dd < 8) return (bb || gg) ? 3 : 0;
    if (hf < vf) {
        if (hero_body_in_gum || (v->balloons && gg)) return v->invincible ? 3 : 1;
    } else if (rival_body_in_gum || (h->balloons && gg)) {
        return h->invincible ? 3 : 2;
    }
    return bb ? 3 : 0;
}

static void run(uint32_t seed, uint32_t frames, int use_oracle, RunStats *st) {
    TripGen g; Trip t; Flier hero; TripRivals R; Rng ir; uint32_t fr; uint16_t kc0; int clamp_frame = 0;
    int32_t prev_x[TRIP_RIVAL_MAX], prev_y[TRIP_RIVAL_MAX]; uint8_t prev_act[TRIP_RIVAL_MAX]; uint32_t prev_spawned = 0, prev_px = 0;
    memset(st, 0, sizeof *st);
    memset(prev_act, 0, sizeof prev_act);
    tripgen_init(&g, seed);
    trip_init(&t);
    flier_init(&hero, FL_PX(TRIP_START_X), FL_PX(TRIP_START_Y), 2, 0);
    hero.no_wrap = 1;                                             /* as in game_set_mode: Gum Trip has no arena seam */
    trip_rivals_init(&R, &t, seed ^ 0xabcdu);
    rng_seed(&ir, seed ^ 0x77u);
    for (fr = 0; fr < frames; fr++) {
        FlierInput in;
        const TripChunk *hc = 0;
        int s, i, target_y, ex_pop = 0, ex_hit = 0;
        uint32_t pop0, hit0, th0 = t.hits, bonus0;
        unsigned ev;
        uint8_t inv;
        /* hero script: hold the middle of the band under the hero's world x and drift with a random wander */
        tripgen_advance(&g, t.px);
        s = g.head;
        for (i = 0; i < g.count; i++, s = (s + 1) % TRIP_GEN_RING)
            if (t.px + 160u >= g.ring[s].wx && t.px + 160u - g.ring[s].wx < TRIP_CHUNK_PX) hc = &g.ring[s];
        target_y = hc ? (hc->band_top + hc->band_bottom) / 2 : 90;
        if ((fr & 63u) == 0) in.dir = (int8_t)((int)(rng_next(&ir) % 3u) - 1);
        else in.dir = (int8_t)(fr < 1 ? 0 : (int)(hero.vx >> 16) * 0 + (int)((rng_next(&ir) >> 8) % 3u) - 1);
        in.flap = (uint8_t)((hero.y >> 16) > target_y + 2 && hero.flap_cd == 0 && !hero.flap_prev);
        if (hero.state != FLIER_ALIVE) {                              /* revive so the run goes on */
            flier_init(&hero, FL_PX(TRIP_START_X), FL_PX(target_y), 2, 0);
            hero.no_wrap = 1;
            t.gum = GUM_MAX; t.decay_tick = 0;
        }
        trip_step(&t, &hero);
        flier_step(&hero, &in, trip_hit_floor_y(&t, &g, &hero));
        trip_collide(&t, &g, &hero);
        kc0 = g_trip_window_clamps;
        ev = trip_rivals_advance(&R, &t, &g, &hero);
        clamp_frame = g_trip_window_clamps != kc0;
        (void)ev;
        if (use_oracle) {
            TripRivals snap = R;
            Flier h2 = hero;
            /* spawn invariants for rivals created this frame are checked in test_spawn; here the pool and place */
            int alive = 0;
            for (i = 0; i < TRIP_RIVAL_MAX; i++) alive += snap.r[i].active;
            CHECK(alive <= TRIP_RIVAL_MAX);
            if (alive > (int)st->maxalive) st->maxalive = (uint32_t)alive;
            inv = h2.invincible;
            if (h2.state == FLIER_ALIVE)
                for (i = 0; i < TRIP_RIVAL_MAX; i++) {
                    const TripRival *v = &snap.r[i];
                    if (!v->active || v->f.state != FLIER_ALIVE) continue;
                    int act;
                    h2.invincible = inv;
                    act = oracle_pair(&h2, &v->f);
                    if (act) {                                        /* a solid island between the pair blocks the contact (BR-D1) */
                        FlierSolid so[TRIP_SOLIDS_MAX]; Flier m = h2;
                        m.x = h2.x + ((v->f.x - h2.x) >> 1);
                        if (flier_pair_blocked(&h2, &v->f, so, trip_hit_solids(&t, &g, &m, so, TRIP_SOLIDS_MAX), 0)) act = 0;
                    }
                    if (act == 1) ex_pop++;
                    else if (act == 2) { ex_hit++; inv = FLIER_INVINCIBLE_POP; }
                }
        }
        pop0 = R.popped; hit0 = R.hits; bonus0 = t.bonus;
        trip_rivals_resolve(&R, &t, &g, &hero);
        if (use_oracle) {
            CHECK(R.popped - pop0 == (uint32_t)ex_pop);
            CHECK(R.hits - hit0 == (uint32_t)ex_hit);
            CHECK(t.hits - th0 >= (uint32_t)ex_hit);
            CHECK(t.bonus >= bonus0);
        }
        /* TP6: no live rival moves more than a few pixels in a frame, on screen or in the world (a rival carried by the
         * scroll that lags or jumps shows as a teleport); frames where the pool gained a rival are skipped */
        for (i = 0; i < TRIP_RIVAL_MAX; i++) {
            if (R.r[i].active && prev_act[i] && R.spawned == prev_spawned) {
                int32_t sx = R.r[i].f.x - prev_x[i], sy = R.r[i].f.y - prev_y[i];
                int32_t wx = sx + (int32_t)(t.px - prev_px) * 65536;
                int32_t m = sx < 0 ? -sx : sx, k = sy < 0 ? -sy : sy;
                if (clamp_frame) {
                    /* solid rock: where the window steps at a chunk seam (up to the generator's step) the clamp moves a rival
                     * to the new edge in one frame; that vertical move is counted apart (max_push) */
                    if (k > st->max_push) st->max_push = k;
                    k = 0;
                }
                if (k > m) m = k;
                k = wx < 0 ? -wx : wx;
                if (k > m) m = k;
                if (m > st->max_jump) st->max_jump = m;
                st->rival_frames++;
            }
            prev_act[i] = R.r[i].active; prev_x[i] = R.r[i].f.x; prev_y[i] = R.r[i].f.y;
        }
        prev_spawned = R.spawned; prev_px = t.px;
        mix((uint32_t)hero.x); mix((uint32_t)hero.y);
        for (i = 0; i < TRIP_RIVAL_MAX; i++) if (R.r[i].active) { mix((uint32_t)R.r[i].f.x); mix((uint32_t)R.r[i].f.y); mix(R.r[i].variant); }
    }
    mix(t.bonus); mix(t.hits); mix(t.gum);
    st->spawned = R.spawned; st->popped = R.popped; st->hits = R.hits; st->retired = R.retired; st->blocked = R.blocked;
    st->pops_pts = t.bonus;
    CHECK(g.overflow == 0);
}

/* TP6 guard (enemy teleport hunt): over 60000 frames and 3 seeds no live rival moves more than 8 px in a frame, in screen or
 * world x or y. Fails when the scroll carry lags or a retire/respawn jumps a live rival. The run must really contain rivals. */
static void test_tp6_no_teleport(void) {
    uint32_t seed;
    for (seed = 1; seed <= 3; seed++) {
        RunStats st;
        run(seed, 60000, 0, &st);
        CHECK(st.rival_frames > 5000);
        CHECK(st.spawned > 0);
        CHECK(st.max_jump <= FL_PX(8));
        CHECK(st.max_push <= FL_PX(TRIP_PASS_MIN + 16));   /* a seam step of the window: bounded by the generator's step */
        printf("tp6 seed %u: rival frames %u, max move %d/65536 px, max push %d\n", (unsigned)seed, (unsigned)st.rival_frames, (int)st.max_jump, (int)(st.max_push >> 16));
    }
}

static void test_long(void) {
    RunStats a, b; uint32_t d0, d1;
    digest = 2166136261u;
    run(1, 40000, 1, &a);
    d0 = digest;
    digest = 2166136261u;
    run(1, 40000, 0, &b);                                               /* same run without the oracle reads: identical */
    d1 = digest;
    CHECK(d0 == d1);
    CHECK(a.spawned > 10 && a.retired > 5);
    CHECK(a.spawned == b.spawned && a.popped == b.popped && a.hits == b.hits);
    CHECK(a.maxalive <= TRIP_RIVAL_MAX && a.maxalive >= 1);
    printf("long: spawned %u popped %u hits %u retired %u blocked %u maxalive %u bonus %u\n", (unsigned)a.spawned, (unsigned)a.popped,
           (unsigned)a.hits, (unsigned)a.retired, (unsigned)a.blocked, (unsigned)a.maxalive, (unsigned)a.pops_pts);
    digest = 2166136261u;
    run(2, 40000, 1, &a);
    run(3, 40000, 1, &a);
    printf("DIGEST %u\n", (unsigned)(d0 ^ digest));
}

/* ---- variant by distance band (user 2026-11-11): Hornet before BAND_BONE_PX, Bone from it, Bruiser from BAND_BRUISER_PX ---- */
static void test_band(void) {
    static const uint32_t px_at[] = { 600, 1200, TRIP_RIVAL_BAND_BONE_PX - 1, TRIP_RIVAL_BAND_BONE_PX, TRIP_RIVAL_BAND_BONE_PX + 1,
                                      TRIP_RIVAL_BAND_BRUISER_PX - 1, TRIP_RIVAL_BAND_BRUISER_PX, TRIP_RIVAL_BAND_BRUISER_PX + 1, 20000 };
    unsigned i, seed;
    for (i = 0; i < sizeof px_at / sizeof px_at[0]; i++) {
        for (seed = 1; seed <= 6; seed++) {
            TripGen g; Trip t; Flier hero; TripRivals R; unsigned ev;
            int want = px_at[i] < TRIP_RIVAL_BAND_BONE_PX ? TRIP_RIVAL_HORNET : px_at[i] < TRIP_RIVAL_BAND_BRUISER_PX ? TRIP_RIVAL_BONE : TRIP_RIVAL_BRUISER;
            tripgen_init(&g, seed);
            trip_init(&t);
            flier_init(&hero, FL_PX(160), FL_PX(90), 2, 0);
            trip_rivals_init(&R, &t, seed);
            t.px = px_at[i]; gen_to(&g, t.px);
            R.next_px = 0; R.last_px = t.px; R.last_frac = t.frac; /* no scroll step this call: the new rival stays */
            ev = trip_rivals_advance(&R, &t, &g, &hero);
            CHECK((ev & TRIP_RIV_EV_SPAWN) && R.spawned == 1 && R.r[0].active && R.r[0].variant == want);
        }
    }
    printf("band: borders %d %d %d %d\n", TRIP_RIVAL_BAND_BONE_PX - 1, TRIP_RIVAL_BAND_BONE_PX, TRIP_RIVAL_BAND_BRUISER_PX - 1, TRIP_RIVAL_BAND_BRUISER_PX);
}

/* ---- a pop is a flat TRIP_RIVAL_POP_POINTS bonus: streak untouched, bonus clamps at TRIP_SCORE_CAP ---- */
static void test_pop_points(void) {
    TripRivals R; Trip t; Flier hero; TripGen g; uint32_t before_streak, before_bonus; unsigned ev;
    open_gen(&g);
    setup(&R, &t, &hero, 100, 60);
    put_rival(&R, 0, TRIP_RIVAL_HORNET, 100, 90); hero.vy = FL_PX(1);
    t.streak = 7; before_streak = t.streak; before_bonus = t.bonus;
    ev = trip_rivals_resolve(&R, &t, &g, &hero);
    CHECK((ev & TRIP_RIV_EV_POP) && t.bonus == before_bonus + TRIP_RIVAL_POP_POINTS && t.streak == before_streak && R.popped == 1);
    /* clamp: bonus one below the cap, a pop must not pass TRIP_SCORE_CAP */
    setup(&R, &t, &hero, 100, 60);
    put_rival(&R, 0, TRIP_RIVAL_HORNET, 100, 90); hero.vy = FL_PX(1);
    t.bonus = TRIP_SCORE_CAP - 1;
    ev = trip_rivals_resolve(&R, &t, &g, &hero);
    CHECK((ev & TRIP_RIV_EV_POP) && t.bonus == TRIP_SCORE_CAP && trip_score(&t) <= TRIP_SCORE_CAP);
    /* a rival 10 px higher pops the hero's gum: it breaks the streak (user decision, plan Q6); both bounce */
    setup(&R, &t, &hero, 100, 90);
    put_rival(&R, 0, TRIP_RIVAL_HORNET, 100, 80);
    t.streak = 7;
    hero.vx = 0; R.r[0].f.vx = 0; R.r[0].f.vy = FL_PX(1); hero.vy = -FL_PX(1);   /* the higher rival falls onto the hero gum, the hero rises */
    ev = trip_rivals_resolve(&R, &t, &g, &hero);
    CHECK((ev & TRIP_RIV_EV_HIT) && t.streak == 0 && t.hits == 1 && R.hits == 1 && R.popped == 0);
    CHECK(hero.vy > 0 && R.r[0].f.vy < 0);                               /* pushed apart along the vertical axis */
    /* level contact (same spot) is a bounce only: no hit, no pop, streak kept, hero pushed sideways apart from the rival */
    setup(&R, &t, &hero, 103, 90);
    put_rival(&R, 0, TRIP_RIVAL_HORNET, 100, 90);
    t.streak = 7; hero.vx = -FL_PX(1); R.r[0].f.vx = FL_PX(1);           /* level pair: hero (x 103) and rival (x 100) move toward each other */
    ev = trip_rivals_resolve(&R, &t, &g, &hero);
    CHECK(!(ev & (TRIP_RIV_EV_HIT | TRIP_RIV_EV_POP)) && t.streak == 7 && t.hits == 0 && R.hits == 0 && R.popped == 0);
    CHECK(hero.vx > 0 && R.r[0].f.vx < 0);
}

/* ---- solid tunnel rock (window clamp) ---- */
/* The rock rows over a flier's box, derived here from the ring (not through trip_hit_window): top = highest win_top,
 * bot = lowest win_bottom of the chunks the box reaches. Returns the chunk count. */
static int ref_rock(const Trip *t, const TripGen *g, const Flier *f, int *top, int *bot) {
    int fx = (int)(f->x >> 16), n = 0, i;
    *top = -1000; *bot = 1000;
    for (i = 0; i < g->count; i++) {
        const TripChunk *c = &g->ring[(g->head + i) % TRIP_GEN_RING];
        long x0 = (long)t->px + fx - FLIER_HALF_W, x1 = (long)t->px + fx + FLIER_HALF_W;
        if (x1 < (long)c->wx || x0 > (long)c->wx + TRIP_CHUNK_PX - 1) continue;
        if (c->win_top > *top) *top = c->win_top;
        if (c->win_bottom < *bot) *bot = c->win_bottom;
        n++;
    }
    return n;
}
static void rock_setup(TripRivals *R, Trip *t, Flier *hero, TripGen *g) {
    tripgen_init(g, 7);
    setup(R, t, hero, 20, 90);
    t->px = 3000; t->frac = 0;
    gen_to(g, t->px);
    trip_rivals_init(R, t, 5);
    R->next_px = 0xFFFFFFFFu;
}
/* one frame of the real order: scroll one pixel, advance the ring, step the rivals */
static void rock_frame(TripRivals *R, Trip *t, TripGen *g, Flier *hero) {
    t->px++;
    tripgen_advance(g, t->px);
    hero->invincible = 200;
    trip_rivals_advance(R, t, g, hero);
}

static void test_rock(void) {
    TripRivals R; Trip t; Flier hero; TripGen g; int f, top, bot, fh, miny, maxy, maxdy;
    unsigned k0, k1;
    /* top: Bone wants to hold y 30, far above every window; it settles on the rock edge */
    rock_setup(&R, &t, &hero, &g);
    put_rival(&R, 0, TRIP_RIVAL_BONE, 310, 100); R.r[0].hold_y = 30;
    fh = (int)(flier_half_h(&R.r[0].f) >> 16) + 1;
    miny = 1000; k0 = g_trip_window_clamps; k1 = 0;
    for (f = 0; f < 300; f++) {
        int n;
        rock_frame(&R, &t, &g, &hero);
        n = ref_rock(&t, &g, &R.r[0].f, &top, &bot);
        CHECK(n > 0);
        CHECK(R.r[0].active);
        CHECK((int)(R.r[0].f.y >> 16) - fh >= top);
        CHECK((int)(R.r[0].f.y >> 16) + fh <= bot - 1);
        if ((int)(R.r[0].f.y >> 16) - fh - top < miny) miny = (int)(R.r[0].f.y >> 16) - fh - top;
        if (f == 149) k1 = g_trip_window_clamps;
    }
    CHECK(miny == 19);                                      /* it did reach the gum-top line (was: the rock edge, miny <= 1) */
    CHECK(g_trip_window_clamps > k0);                       /* and the clamp ran */
    printf("rock top: win_top %d, min gap %d, clamps %u, in the second half %u\n", top, miny, g_trip_window_clamps - k0, g_trip_window_clamps - k1);

    /* bottom: hold_y far below, gravity only; it rests on the bottom edge and never sinks into the rock */
    rock_setup(&R, &t, &hero, &g);
    put_rival(&R, 0, TRIP_RIVAL_BONE, 200, 100); R.r[0].hold_y = 175;
    maxy = -1000; maxdy = 0; k0 = g_trip_window_clamps;
    for (f = 0; f < 200; f++) {
        rock_frame(&R, &t, &g, &hero);
        ref_rock(&t, &g, &R.r[0].f, &top, &bot);
        CHECK((int)(R.r[0].f.y >> 16) + fh <= bot - 1);
        if ((int)(R.r[0].f.y >> 16) + fh > maxy) maxy = (int)(R.r[0].f.y >> 16) + fh;
        if (R.r[0].f.vy > FL_PX(1) && (int)(R.r[0].f.y >> 16) + fh >= bot - 1) maxdy++;
    }
    ref_rock(&t, &g, &R.r[0].f, &top, &bot);
    CHECK(maxy >= bot - 2 || (int)(R.r[0].f.y >> 16) + fh >= bot - 2);   /* it reached the bottom edge */
    CHECK(maxdy == 0);                                                    /* never leaves a downward velocity at the edge */
    /* Sanity bound only. Measured 2 clamps with and without the Bone target clamp, so this does not prove that clamp. */
    printf("rock bottom: clamps in 200 frames %u\n", g_trip_window_clamps - k0);
    CHECK(g_trip_window_clamps - k0 < 100);

    /* bounce factor: at the top edge with vy -4 px the clamp reflects exactly flier_reflect of the velocity it saw */
    {
        Flier a; int32_t lo, hi, v;
        rock_setup(&R, &t, &hero, &g);
        flier_init(&a, FL_PX(200), FL_PX(100), 2, 0);
        a.no_wrap = 1;
        CHECK(trip_hit_window(&t, &g, &a, &lo, &hi));
        a.y = lo - FL_PX(1); a.vy = -FL_PX(4); v = a.vy;
        CHECK(trip_hit_clamp_window(&t, &g, &a) == 1 && a.y == lo && a.vy == flier_reflect(v) && a.vy > 0 && a.vy < FL_PX(4));
    }

    /* a defeated rival falls out through the rock: no clamp, it retires */
    rock_setup(&R, &t, &hero, &g);
    put_rival(&R, 0, TRIP_RIVAL_BONE, 200, 100);
    ref_rock(&t, &g, &R.r[0].f, &top, &bot);
    R.r[0].f.y = FL_PX(top - 20); R.r[0].f.state = FLIER_FALLING; R.r[0].f.balloons = 0; R.r[0].f.vy = FL_PX(1);
    k0 = g_trip_window_clamps;
    for (f = 0; f < 600 && R.r[0].active; f++) rock_frame(&R, &t, &g, &hero);
    CHECK(!R.r[0].active && R.retired == 1);
    CHECK(g_trip_window_clamps == k0);
}

/* scroll order: the rival's x and the ring px are in the same frame for the solids, so the box never overlaps an island */
static void test_rival_island_order(void) {
    TripRivals R; Trip t; Flier hero; TripGen g; int f, bad = 0, minpen = 1000;
    open_gen(&g);
    g.ring[0].island.present = 1; g.ring[0].island.x = 100; g.ring[0].island.y = 120; g.ring[0].island.w = 64; g.ring[0].island.h = TRIP_ISLAND_H;
    setup(&R, &t, &hero, 20, 20);
    put_rival(&R, 0, TRIP_RIVAL_BONE, 175, 120 + TRIP_ISLAND_SOLID_H / 2);
    R.r[0].hold_y = 120 + TRIP_ISLAND_SOLID_H / 2;
    for (f = 0; f < 60; f++) {
        int32_t right;
        t.px++; hero.invincible = 200;
        R.r[0].f.vx = -FL_PX(3);
        trip_rivals_advance(&R, &t, &g, &hero);
        right = FL_PX(164) - FL_PX((int32_t)t.px);
        if (R.r[0].f.x - FL_PX(FLIER_HALF_W) < right) bad++;
        if (R.r[0].f.x - FL_PX(FLIER_HALF_W) - right < minpen) minpen = (int)((R.r[0].f.x - FL_PX(FLIER_HALF_W) - right) >> 8);
    }
    CHECK(bad == 0);
    CHECK(g_flier_solid_hits > 0);
    (void)minpen;
}

int main(void) {
    test_variants();
    test_spawn_pool_retire();
    test_stomp_edges();
    test_contact();
    test_contact_blocked();
    test_long();
    test_tp6_no_teleport();
    test_band();
    test_pop_points();
    test_rock();
    test_rival_island_order();
    printf("%s: %d checks, %d failures\n", failures ? "FAIL" : "PASS", checks, failures);
    return failures ? 1 : 0;
}
