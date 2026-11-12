/* Gum Trip core (plan T-B2, T-B3): scroll ramp, gum meter, streak score, run end, edge clamp.
 * Prints "DIGEST <n>" of a scripted run so a knob override can be shown to move the output. */
#include <stdio.h>
#include <stdint.h>
#include "../../src/core/trip.h"
#include "../../src/core/game.h"
#include "trip_steer.h"

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; if (failures <= 20) printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

static void fresh(Trip *t, Flier *f) {
    trip_init(t);
    flier_init(f, FL_PX(160), FL_PX(80), 2, 0);
}

/* Independent expected speed: floor(px * (MAX - START) / RAMP) added to START, in 64-bit. */
static uint32_t want_speed(uint32_t px) {
    if (px >= TRIP_RAMP_PX) return TRIP_SCROLL_MAX;
    return TRIP_SCROLL_START + (uint32_t)((uint64_t)px * (TRIP_SCROLL_MAX - TRIP_SCROLL_START) / TRIP_RAMP_PX);
}

static uint32_t digest;
static void mix(uint32_t v) { digest = (digest ^ v) * 16777619u; }

/* 1 when a hazard box of a held chunk lies within reach of the flier (loose bound: half sizes plus the sweep and 8 px). */
static int near_hazard(const Game *g) {
    int fx = (int)(g->trip.px + (uint32_t)(g->flier.x >> 16)), fy = (int)(g->flier.y >> 16), k, j;
    for (k = 0; k < TRIP_GEN_RING; k++) {
        const TripChunk *q = &g->trip_gen.ring[k];
        for (j = 0; j < q->n_haz; j++) {
            int dx = (int)(q->wx + (uint32_t)q->haz[j].x) - fx, dy = q->haz[j].y - fy;
            if (dx < 0) dx = -dx;
            if (dy < 0) dy = -dy;
            if (dx <= q->haz[j].hw + FLIER_HALF_W + 1 && dy <= q->haz[j].hh + q->haz[j].amp + 8) return 1;
        }
    }
    return 0;
}

int main(void) {
    Trip t; Flier f;
    uint32_t i, prev, sum;

    /* ---- scroll: start, cap, monotonic, ramp reaches the cap at TRIP_RAMP_PX ---- */
    fresh(&t, &f);
    CHECK(t.speed == 49152 || TRIP_SCROLL_START != 49152);
    CHECK(t.speed == (uint32_t)TRIP_SCROLL_START);
    CHECK(trip_speed_at(0) == (uint32_t)TRIP_SCROLL_START);
    prev = t.speed; sum = 0;
    for (i = 0; i < 40000; i++) {
        uint32_t px_before = t.px, fr_before = t.frac, step = t.speed;
        /* keep the flier alive and in range: gum topped up, position irrelevant for the scroll */
        t.gum = GUM_MAX;
        trip_step(&t, &f);
        sum += step;
        CHECK(t.speed >= prev);                   /* monotonic */
        CHECK(t.speed <= (uint32_t)TRIP_SCROLL_MAX); /* never above the cap */
        CHECK(t.px >= px_before);
        CHECK(((uint64_t)t.px << 16 | t.frac) == ((uint64_t)px_before << 16 | fr_before) + step);
        CHECK(t.speed == want_speed(t.px));       /* matches the closed form at every frame */
        if (t.px < TRIP_RAMP_PX) CHECK(t.speed < (uint32_t)TRIP_SCROLL_MAX);
        prev = t.speed;
        if (i % 1000 == 0) mix(t.speed);
    }
    CHECK(t.px > (uint32_t)TRIP_RAMP_PX && t.speed == (uint32_t)TRIP_SCROLL_MAX);
    CHECK(((uint64_t)t.px << 16 | t.frac) == sum);     /* scroll position is exactly the sum of the steps */
    CHECK(t.steps == 40000);
    CHECK(trip_speed_at(TRIP_RAMP_PX - 1) < (uint32_t)TRIP_SCROLL_MAX);
    CHECK(trip_speed_at(TRIP_RAMP_PX) == (uint32_t)TRIP_SCROLL_MAX);
    CHECK(trip_speed_at(4000000000u) == (uint32_t)TRIP_SCROLL_MAX);
    mix(t.px);

    /* first pixel exactly: at distance 0 the first frame advances 49152 raw */
    fresh(&t, &f);
    trip_step(&t, &f);
    CHECK(t.px == 0 && t.frac == (uint32_t)TRIP_SCROLL_START);

    /* ---- gum decay: GUM_START to 0 in exactly GUM_START * GUM_DECAY_FRAMES frames ---- */
    fresh(&t, &f);
    CHECK(t.gum == GUM_START);
    for (i = 0; i < (uint32_t)GUM_START * GUM_DECAY_FRAMES - 1; i++) trip_step(&t, &f);
    CHECK(t.gum == 1);
    CHECK(f.state == FLIER_ALIVE && f.balloons == 1);
    trip_step(&t, &f);
    CHECK(t.gum == 0);
    CHECK(f.state == FLIER_FALLING);                 /* the fall starts in the frame the gum hits 0 */
    CHECK(f.balloons == 0);
    CHECK(!trip_over(&f));
    mix(t.steps);
    for (i = 0; i < 400 && !trip_over(&f); i++) { FlierInput in = {0, 0}; flier_step(&f, &in, FLIER_NO_FLOOR); trip_step(&t, &f); }
    CHECK(trip_over(&f));                            /* run ends when the fall finishes (GONE) or water (DROWNED) */
    CHECK(t.gum == 0);
    mix(i);

    /* one tick before a unit: a decay counter, so frames per unit are exact */
    fresh(&t, &f);
    for (i = 0; i < (uint32_t)GUM_DECAY_FRAMES - 1; i++) trip_step(&t, &f);
    CHECK(t.gum == GUM_START);
    trip_step(&t, &f);
    CHECK(t.gum == GUM_START - 1);

    /* ---- balloons derived from gum: 2 at the half mark and above, 1 below, 0 at 0 ---- */
    CHECK(trip_gum_balloons(GUM_MAX) == 2);
    CHECK(trip_gum_balloons(GUM_MAX / 2) == 2);
    CHECK(trip_gum_balloons(GUM_MAX / 2 - 1) == 1);
    CHECK(trip_gum_balloons(1) == 1);
    CHECK(trip_gum_balloons(0) == 0);

    /* ---- pickup: adds exactly GUM_PICKUP, clamps at GUM_MAX ---- */
    fresh(&t, &f);
    t.gum = 100;
    CHECK(trip_pickup(&t, &f) == 1);
    CHECK(t.gum == 100 + GUM_PICKUP);
    mix(t.gum);
    t.gum = GUM_MAX - 1;
    trip_pickup(&t, &f);
    CHECK(t.gum == GUM_MAX);
    trip_pickup(&t, &f);
    CHECK(t.gum == GUM_MAX);
    CHECK(f.balloons == 2);
    mix(t.gum);
    /* a refill from below the half mark lifts the balloons back */
    fresh(&t, &f);
    t.gum = 10; trip_step(&t, &f);
    CHECK(f.balloons == 1);
    t.gum = GUM_MAX / 2 - 1; trip_pickup(&t, &f);
    CHECK(f.balloons == trip_gum_balloons(t.gum));

    /* ---- hit: removes the chunk, never below 0, breaks the streak, invincible window ---- */
    fresh(&t, &f);
    t.gum = GUM_MAX;
    trip_pickup(&t, &f); trip_pickup(&t, &f);
    CHECK(t.streak == 2);
    CHECK(trip_hit(&t, &f) == 1);
    CHECK(t.gum == GUM_MAX - GUM_HIT_CHUNK);
    CHECK(t.streak == 0);
    CHECK(f.invincible == FLIER_INVINCIBLE_POP);
    CHECK(trip_hit(&t, &f) == 0);                    /* second hit inside the window does nothing */
    CHECK(t.gum == GUM_MAX - GUM_HIT_CHUNK && t.hits == 1);
    mix(t.gum);
    for (i = 0; i < FLIER_INVINCIBLE_POP; i++) { FlierInput in = {0, 0}; flier_step(&f, &in, FLIER_NO_FLOOR); }
    CHECK(f.invincible == 0);
    CHECK(trip_hit(&t, &f) == 1);
    CHECK(t.gum == GUM_MAX - 2 * GUM_HIT_CHUNK);
    /* a hit that takes the gum to 0 starts the fall and does not underflow */
    fresh(&t, &f);
    t.gum = GUM_HIT_CHUNK - 1;
    CHECK(trip_hit(&t, &f) == 1);
    CHECK(t.gum == 0 && f.state == FLIER_FALLING);
    CHECK(trip_pickup(&t, &f) == 0 && t.gum == 0);   /* no pickups while falling */

    /* ---- streak: grows with no cap, scrolling past a pickup does not change it ---- */
    fresh(&t, &f);
    for (i = 0; i < 100; i++) { t.gum = GUM_MAX; trip_pickup(&t, &f); }
    CHECK(t.streak == 100);
    CHECK(t.bonus == (uint32_t)TRIP_PICKUP_POINTS * (100u * 101u / 2u));   /* 50 x (1+2+...+100) */
    for (i = 0; i < 200; i++) { t.gum = GUM_MAX; trip_step(&t, &f); }
    CHECK(t.streak == 100);
    for (i = 0; i < 200; i++) { t.gum = GUM_MAX; trip_pickup(&t, &f); }   /* 300 in a row: no cap on the multiplier */
    CHECK(t.streak == 300);
    CHECK(t.bonus == TRIP_SCORE_CAP);                                    /* the bonus saturates, it does not wrap */
    mix(t.bonus);

    /* ---- score: distance points plus bonus, clamps at 999999, never wraps ---- */
    fresh(&t, &f);
    t.px = 800;
    CHECK(trip_score(&t) == (800u >> TRIP_SCORE_PX_SHIFT));
    t.bonus = 5000;
    CHECK(trip_score(&t) == (800u >> TRIP_SCORE_PX_SHIFT) + 5000);
    t.bonus = 999990; t.px = 8000;
    CHECK(trip_score(&t) == 999999);
    t.px = 0xFFFFFFFFu; t.bonus = TRIP_SCORE_CAP;
    CHECK(trip_score(&t) == 999999);
    t.streak = 0xFFFFFFFEu; t.bonus = 0;
    t.gum = 0; f.state = FLIER_ALIVE;
    trip_pickup(&t, &f);
    CHECK(t.streak == 0xFFFFFFFFu && t.bonus == TRIP_SCORE_CAP);
    trip_pickup(&t, &f);
    CHECK(t.streak == 0xFFFFFFFFu && t.bonus == TRIP_SCORE_CAP && trip_score(&t) == 999999);
    mix(trip_score(&t));
    /* monotonic score along a run */
    fresh(&t, &f); prev = 0;
    for (i = 0; i < 20000; i++) {
        t.gum = GUM_MAX; trip_step(&t, &f);
        if (i % 700 == 0) trip_pickup(&t, &f);
        CHECK(trip_score(&t) >= prev);
        prev = trip_score(&t);
    }
    mix(prev);

    /* ---- edge clamp: no wrap, left edge pushes and keeps the life, right edge blocks ---- */
    fresh(&t, &f);
    for (i = 0; i < 2000; i++) {
        t.gum = GUM_MAX;
        trip_step(&t, &f);
        CHECK(f.x >= 0 && f.x <= FL_PX(319));
    }
    CHECK(f.x == 0 && f.state == FLIER_ALIVE);       /* pushed to the left edge and survives there */
    fresh(&t, &f);
    f.x = FL_PX(319); f.vx = 65536;
    t.gum = GUM_MAX; trip_step(&t, &f);
    CHECK(f.x <= FL_PX(319) && f.vx == 65536 && f.x == FL_PX(319) - (int32_t)TRIP_SCROLL_START);
    f.x = FL_PX(400); f.vx = 65536;                   /* outside on the right: blocked, vx zero on contact */
    trip_step(&t, &f);
    CHECK(f.x == FL_PX(319) && f.vx == 0);
    f.x = 10; f.vx = -65536;
    trip_step(&t, &f);
    CHECK(f.x == 0 && f.vx == 0);
    mix((uint32_t)f.x);

    /* ---- hazard density: 0 early, linear, capped ---- */
    CHECK(trip_density_at(0) == 0);
    CHECK(trip_density_at(TRIP_DENSITY_START_PX) == 0);
    CHECK(trip_density_at(TRIP_DENSITY_FULL_PX) == (uint32_t)TRIP_DENSITY_MAX * 256);
    CHECK(trip_density_at(TRIP_DENSITY_FULL_PX + 100000) == (uint32_t)TRIP_DENSITY_MAX * 256);
    prev = 0;
    for (i = 0; i < 9000; i++) { uint32_t d = trip_density_at(i); CHECK(d >= prev); prev = d; }
    CHECK(trip_density_at((TRIP_DENSITY_START_PX + TRIP_DENSITY_FULL_PX) / 2) ==
          (uint32_t)TRIP_DENSITY_MAX * 256 / 2);
    mix(trip_density_at(4000)); mix(trip_density_at(7000));

    /* ---- game level: game_step (the core entry the flow calls) in TRIP mode runs trip_step, ARENA mode never does ---- */
    {
        static Game g;
        uint32_t acc = 0;     /* expected scroll, 16.16, independent of Trip: sum of the closed-form speed */
        uint32_t n = 600, gum_model = GUM_START, pk_seen = 0;
        game_reset(&g, 7);
        game_set_mode(&g, GAME_MODE_TRIP);
        CHECK(g.mode == GAME_MODE_TRIP && g.flier.no_wrap && g.flier.balloons == 2 && g.trip.gum == GUM_START);
        CHECK(g.flier.spawn_inv == FLIER_SPAWN_INVINCIBLE);   /* SI: protected from the start of a run */
        /* frame budget: the mode switch builds no chunk; the run-start hold builds one chunk per game step and moves
         * nothing (no flier, scroll, camera, collision, frame count) until the first screen is covered */
        CHECK(g.trip_gen.made == 0 && g.trip_gen.count == 0 && !game_trip_ready(&g) && g.trip_hold == 0);
        {
            int32_t fx = g.flier.x, fy = g.flier.y, cam = g.camera.cam;
            uint32_t made_b;
            int hold_steps = 0;
            while (!game_trip_ready(&g) && hold_steps < 10) {
                made_b = g.trip_gen.made;
                game_step(&g, IN_A | IN_RIGHT);
                hold_steps++;
                CHECK(g.trip_gen.made - made_b == 1);
                CHECK(g.flier.x == fx && g.flier.y == fy && g.camera.cam == cam);
                CHECK(g.trip.px == 0 && g.trip.steps == 0 && g.flier_steps == 0 && g.frame == 0 && g.flaps == 0);
                CHECK(g.trip_events == 0 && !g.over);
            }
            CHECK(hold_steps >= 1 && hold_steps <= 3 && g.trip_hold == hold_steps);   /* hold length: 2 */
            CHECK(game_trip_ready(&g) && g.trip.px == 0);                    /* first screen covered before the first scroll */
        }
        for (i = 0; i < n; i++) {
            uint8_t in = trip_steer(&g, STEER_AVOID);
            uint32_t made_before = g.trip_gen.made;
            acc += want_speed(acc >> 16);
            CHECK(tripgen_covers(&g.trip_gen, g.trip.px));             /* the screen is covered before this step scrolls */
            game_step(&g, in);
            CHECK(g.trip_gen.made - made_before <= 1);
            if ((i + 1) % GUM_DECAY_FRAMES == 0) gum_model--;           /* trip_step: one unit per GUM_DECAY_FRAMES frames */
            if (g.trip.pickups != pk_seen) { pk_seen = g.trip.pickups; gum_model = gum_model + GUM_PICKUP > GUM_MAX ? GUM_MAX : gum_model + GUM_PICKUP; }
            CHECK(g.trip.gum == gum_model);
            CHECK(!g.over);
            CHECK(g.trip.steps == (uint32_t)(i + 1) && g.flier_steps == (uint32_t)(i + 1));
            CHECK(g.trip.px == (acc >> 16) && g.distance == g.trip.px);
            CHECK(g.score == trip_score(&g.trip));
            CHECK(g.flier.x >= 0 && g.flier.x <= FL_PX(319));
        }
        CHECK(g.trip.hits == 0 && g.trip.pickups >= 1);
        mix(g.trip.px); mix(g.score); mix(g.trip.gum);
        /* run end through game_step: gum to zero ends the run */
        g.trip.gum = 1;
        for (i = 0; i < 4000 && !g.over; i++) game_step(&g, trip_steer(&g, STEER_AVOID));
        CHECK(g.over && (g.flier.state == FLIER_DROWNED || g.flier.state == FLIER_GONE));
        /* arena: the trip core never runs and the flier wraps */
        game_reset(&g, 7);
        game_set_mode(&g, GAME_MODE_ARENA);
        for (i = 0; i < 300; i++) game_step(&g, 0);
        CHECK(g.mode == GAME_MODE_ARENA && g.trip.steps == 0 && g.trip.px == 0 && g.flier_steps == 300 && !g.flier.no_wrap);
        CHECK(g.distance == 300u * SPEED_BASE);
    }


    /* ---- reachability: game_step in TRIP mode runs the rivals (one trip_rivals_step per frame, cap, band kinds) ---- */
    {
        static Game g;
        uint32_t f, max_alive = 0, spawned_by_3000 = 0, first_variant_ok = 1, events = 0;
        int r, alive;
        game_reset(&g, 21);
        game_set_mode(&g, GAME_MODE_TRIP);
        for (f = 1; f <= 30000 && !g.over; f++) {
            uint32_t sp_before = g.trip_rivals.spawned;
            game_step(&g, trip_steer(&g, STEER_AVOID));
            alive = 0;
            for (r = 0; r < TRIP_RIVAL_MAX; r++) alive += g.trip_rivals.r[r].active;
            if ((uint32_t)alive > max_alive) max_alive = (uint32_t)alive;
            events |= g.trip_rival_events;
            if (g.trip_rivals.spawned > sp_before) {
                const TripRival *nv = &g.trip_rivals.r[0];
                for (r = 0; r < TRIP_RIVAL_MAX; r++) if (g.trip_rivals.r[r].active && g.trip_rivals.r[r].f.x > nv->f.x) nv = &g.trip_rivals.r[r];
                if (g.trip.px >= (uint32_t)TRIP_RIVAL_BAND_BRUISER_PX ? nv->variant != TRIP_RIVAL_BRUISER
                    : g.trip.px >= (uint32_t)TRIP_RIVAL_BAND_BONE_PX ? nv->variant != TRIP_RIVAL_BONE
                    : nv->variant != TRIP_RIVAL_HORNET) first_variant_ok = 0;
            }
            if (g.trip.px < 3000) spawned_by_3000 = g.trip_rivals.spawned;
        }
        CHECK(g.trip_rivals.steps == g.trip.steps && g.trip_hold > 0);  /* one rival step per scroll step, none on hold frames (sentinel) */
        CHECK(g.trip_rivals.spawned >= 1 && (events & TRIP_RIV_EV_SPAWN));
        CHECK(spawned_by_3000 >= 1);                       /* first rival at TRIP_RIVAL_FIRST_PX, well before 3000 px */
        CHECK(max_alive <= (uint32_t)TRIP_RIVAL_MAX);
        CHECK(first_variant_ok);                           /* kind follows the distance band at spawn */
        game_reset(&g, 21);
        game_set_mode(&g, GAME_MODE_ARENA);
        for (f = 0; f < 300; f++) game_step(&g, 0);
        CHECK(g.trip_rivals.steps == 0 && g.trip_rivals.spawned == 0);   /* arena never runs them */
    }

    /* ---- reachability: game_step in TRIP mode generates chunks, lands on islands, scores pickups, takes hazard hits ---- */
    {
        static Game g;
        uint32_t made_seen = 0, bonus_want = 0, streak_want = 0, ev_pick = 0, ev_hit = 0, hit_by_haz = 0, land_frames = 0;
        uint32_t landed_chunk_ok = 0, f, phase = 0, first_bonus = 0, first_score = 0;
        uint32_t px_prev = 0, pickups_prev = 0, hits_prev = 0, gum_prev;
        int saw_first = 0;
        game_reset(&g, 2024);
        game_set_mode(&g, GAME_MODE_TRIP);
        CHECK(g.trip_gen.made == 0);
        while (!game_trip_ready(&g) && g.trip_hold < 3) game_step(&g, 0);   /* run-start hold, at most 3 steps */
        CHECK(game_trip_ready(&g) && g.trip_gen.made >= 1 && tripgen_get(&g.trip_gen, 0) != 0 && !tripgen_get(&g.trip_gen, 0)->n_haz);
        gum_prev = g.trip.gum;
        for (f = 0; f < 40000 && !g.over; f++) {
            SteerMode m = phase == 0 ? STEER_AVOID : phase == 1 ? STEER_LAND : phase == 2 ? STEER_HIT : STEER_AVOID;
            uint32_t pk_before = g.trip.pickups, hit_before = g.trip.hits, pop_before = g.trip_rivals.popped, rh_before = g.trip_rivals.hits;
            /* This scripted run is about pickups, landing and hazards: rivals are cleared each frame so a rival that pops the hero's
             * gum (it does since the gum contact rule) cannot end the run before the hazard hit. Rival contact has its own tests. */
            for (int ri = 0; ri < TRIP_RIVAL_MAX; ri++) g.trip_rivals.r[ri].active = 0;
            game_step(&g, trip_steer(&g, m));
            bonus_want += (uint32_t)TRIP_RIVAL_POP_POINTS * (g.trip_rivals.popped - pop_before); /* a rival pop is a flat bonus, streak untouched */
            /* chunks follow the scroll: the ring always holds the chunk under the right screen edge plus the look-ahead */
            CHECK(tripgen_get(&g.trip_gen, (g.trip.px + 320u) / TRIP_CHUNK_PX) != 0);
            CHECK(g.trip_gen.overflow == 0 && g.trip_gen.made >= made_seen);
            made_seen = g.trip_gen.made;
            CHECK(g.trip.px >= px_prev); px_prev = g.trip.px;
            if (g.trip.pickups != pk_before) {
                streak_want++; bonus_want += (uint32_t)TRIP_PICKUP_POINTS * streak_want; ev_pick++;
                CHECK(g.trip.pickups == pk_before + 1 && (g.trip_events & TRIP_EV_PICKUP));
                if (!saw_first) { /* spec: first pickup is 50 x 1 */
                    saw_first = 1; first_bonus = g.trip.bonus; first_score = g.score;
                    CHECK(g.trip.bonus == (uint32_t)TRIP_PICKUP_POINTS * 1u && g.trip.streak == 1);
                    CHECK(g.score == (g.trip.px >> TRIP_SCORE_PX_SHIFT) + (uint32_t)TRIP_PICKUP_POINTS);
                }
            }
            if (g.trip_rivals.hits != rh_before) { /* rival contact is a hit that breaks the streak; its event is the rival one */
                streak_want = 0;
                CHECK(g.trip_rival_events & TRIP_RIV_EV_HIT);
            } else if (g.trip.hits != hit_before) {
                uint32_t lost = gum_prev - g.trip.gum;
                ev_hit++; streak_want = 0;
                CHECK(g.trip.hits == hit_before + 1 && (g.trip_events & TRIP_EV_HIT));
                if (!(g.trip_events & TRIP_EV_PICKUP) && gum_prev > (uint32_t)GUM_HIT_CHUNK + 1u)
                    CHECK(lost == (uint32_t)GUM_HIT_CHUNK || lost == (uint32_t)GUM_HIT_CHUNK + 1u); /* chunk, plus the decay unit of this frame */
                CHECK(g.trip.streak == 0 && g.flier.invincible > 0 || g.flier.state != FLIER_ALIVE);
                if (near_hazard(&g)) hit_by_haz++;
            }
            CHECK(g.trip.bonus == bonus_want);
            CHECK(g.score == trip_score(&g.trip));
            CHECK(g.trip.gum <= GUM_MAX);
            if (g.flier.on_ground) { land_frames++; if (trip_hit_floor_y(&g.trip, &g.trip_gen, &g.flier) != FLIER_NO_FLOOR) landed_chunk_ok++; }
            gum_prev = g.trip.gum; pickups_prev = g.trip.pickups; hits_prev = g.trip.hits;
            /* phases: collect 3 pickups, land once, take one hit, then drain */
            if (phase == 0 && g.trip.pickups >= 3 && g.trip.px > 700) phase = 1;
            else if (phase == 1 && land_frames > 20) phase = 2;
            else if (phase == 2 && hit_by_haz >= 1 && g.flier.invincible == 0) {
                phase = 3;   /* drain: leave one gum unit so the run ends by the decay, unless the hit already took the last of it */
                if (g.trip.gum > 0) g.trip.gum = 1;
                gum_prev = g.trip.gum;
            }
        }
        (void)pickups_prev; (void)hits_prev; (void)first_bonus; (void)first_score;
        CHECK(made_seen >= 4);                      /* chunks advanced */
        CHECK(ev_pick >= 3 && g.trip.pickups >= 3);  /* pickups scored */
        CHECK(land_frames > 20 && landed_chunk_ok == land_frames); /* landed on an island: on_ground only with an island floor */
        CHECK(ev_hit >= 1 && g.trip.hits >= 1);     /* hit taken */
        CHECK(phase == 3);
        CHECK(g.over && g.trip.gum == 0 && (g.flier.state == FLIER_DROWNED || g.flier.state == FLIER_GONE)); /* run ends at gum 0 */
        mix(made_seen); mix(ev_pick); mix(ev_hit);
        CHECK(hit_by_haz >= 1);                     /* the hit came from a hazard box, not only a strip */
    }

    printf("DIGEST %u\n", (unsigned)digest);
    printf("trip: %d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
