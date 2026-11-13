/* Prints one digest of a long scripted run. run.sh builds this once per tuning knob with a
 * -D override and checks the digest differs from the baseline. Input comes from its own
 * generator so it does not depend on the game RNG. */
#include <stdio.h>
#include <string.h>
#include "../../src/core/flow.h"
#include "stomp_assist.h"
#include "trip_steer.h"
#include "../../src/core/trip_hit.h"
#include "../../src/core/flier_view.h"
#include "../../src/core/gum_view.h"
#include "../../src/core/splash_view.h"
#include "gen/sootling_tables.h"

static uint32_t h = 2166136261u;
static void mix(uint32_t v)
{
    int i;
    for (i = 0; i < 4; i++) { h ^= (v >> (8 * i)) & 0xFFu; h *= 16777619u; }
}

/* Flow part: a long scripted session driven only by the flow's public state. Covers attract
 * cycles, demo play, real runs, name entry (held direction, idle timeout, END) and the
 * operator reset, so every flow knob has a visible effect on the digest. */
static void flow_digest(void)
{
    static Flow f;
    uint32_t fr, title_visits = 0, entry_visits = 0, entry_frame = 0, in_state = 4242u;
    uint8_t prev_state = 255;
    int i, gapped = 0;
    uint32_t want_stomps = 0;
    flow_init(&f, 0, 0);
    for (fr = 1; fr <= 120000u; fr++) {
        uint8_t in = 0, start = 0;
        in_state = in_state * 1664525u + 1013904223u;
        if (f.state != prev_state) {
            if (f.state == FLOW_ATTRACT_TITLE) title_visits++;
            if (f.state == FLOW_NAME_ENTRY) { entry_visits++; entry_frame = 0; }
            if (f.state == FLOW_PLAYING && !f.demo) {
                /* Arena: stomp a few computer balloons (real score path), then drop over the gap so the run ends. */
                gapped = 0;
                want_stomps = 3u + ((in_state >> 20) & 3u);
            }
            prev_state = f.state;
        }
        switch (f.state) {
        case FLOW_ATTRACT_TITLE:
            if (title_visits % 5 == 1 && f.timer < 250) in = FLOW_RESET_COMBO;
            else if (title_visits % 5 == 3 && f.timer == 60) start = 1;
            break;
        case FLOW_ATTRACT_TABLE:
            if (f.timer == 30 && (in_state >> 28) < 3) start = 1;
            break;
        case FLOW_PLAYING:
            if (!f.demo) {
                if (f.game.stomps < want_stomps && f.game.frame < 600u) stomp_assist(&f.game);
                else if (!gapped) { f.game.flier.x = FL_PX(100); f.game.flier.y = FL_PX(100); gapped = 1; }
            }
            /* Arena: random flaps (1 in 16 frames) and steering so the flier eventually leaves the islands and drowns. */
            if (f.game.frame < 40u && ((in_state >> 8) & 15u) == 0u) in |= IN_A;   /* flaps only early, so the run ends */
            if (((in_state >> 20) & 3u) == 0u) in |= IN_LEFT;
            else if (((in_state >> 20) & 3u) == 1u) in |= IN_RIGHT;
            break;
        case FLOW_NAME_ENTRY:
            entry_frame++;
            if (entry_visits % 2 == 0) {            /* mash: hold up, confirm, down to END */
                if (entry_frame < 70) in = IN_UP;
                else if (entry_frame == 72) in = IN_A;
                else if (entry_frame == 75) in = IN_DOWN;
                else if (entry_frame == 78) in = IN_A;
            } else if (entry_frame == 5) {         /* one letter, then idle until timeout */
                in = IN_A;
            }
            break;
        default:
            break;
        }
        flow_step(&f, in, start, fr);
        if (f.dirty) { mix(0xD1u); f.dirty = 0; }
        mix(f.state); mix(f.timer); mix(f.game.score); mix(f.game.flier_steps); mix(f.game.flaps); mix((uint32_t)f.game.flier.x); mix((uint32_t)f.game.flier.y); mix((uint32_t)game_camera_px(&f.game)); mix((uint32_t)f.highlight);
        mix(f.reset_hold);
        mix(f.ov.key); mix(f.demo_in);                  /* the attract overlay state (ATTRACT_HOLD_FRAMES) */
        if (f.state == FLOW_ATTRACT_TABLE && (f.timer == 100u || f.timer == 200u)) { /* which mode's table the screen shows (SCORE_TABLE_SWAP_FRAMES) */
            FlowView v;
            flow_view(&f, &v);
            mix(v.table_mode); mix(v.table->score[0]); mix((uint32_t)v.highlight);
        }
        for (i = 0; i < NAME_LEN; i++) mix((uint32_t)f.entry.name[i]);
        mix(f.entry.pos); mix(f.entry.sym[0]);
    }
    for (i = 0; i < HISCORE_ENTRIES; i++) {
        int k, m;
        for (m = 0; m < 2; m++) {
            mix(f.tables.t[m].score[i]);
            for (k = 0; k < HISCORE_NAME_LEN; k++) mix((uint32_t)f.tables.t[m].name[i][k]);
        }
    }
    mix(title_visits); mix(entry_visits);
#ifdef KNOB_DEBUG
    fprintf(stderr, "title %u entry %u last %u\n", (unsigned)title_visits, (unsigned)entry_visits, (unsigned)f.last_score);
#endif
}

/* Arena part: computer fliers and matches. The player is kept alive; every 400 frames all computer fliers lose
 * their balloons (balloon-less AI states), every 1500 frames the rest are removed so the match is won and the next
 * one (one more flier, up to the cap) starts. */
static void arena_digest(void)
{
    static Game g;
    uint32_t f, in_state = 31337u;
    int i;
    game_reset(&g, 4242);
    for (f = 1; f <= 12000u; f++) {
        uint8_t in = 0;
        in_state = in_state * 1664525u + 1013904223u;
        if (((in_state >> 20) & 7u) < 2u) in |= IN_A;
        if (((in_state >> 12) & 3u) == 0u) in |= IN_LEFT;
        else if (((in_state >> 12) & 3u) == 1u) in |= IN_RIGHT;
        if (g.flier.state >= FLIER_FALLING) flier_init(&g.flier, FL_PX(FLIER_START_X), FL_PX(FLIER_START_Y), FLIER_START_BALLOONS, 0);
        g.over = 0;
        if (f % 700u < 40u) stomp_assist(&g);
        if (f % 400u == 0u) for (i = 0; i < g.cpu_count; i++) { g.cpu[i].invincible = 0; while (flier_lose_balloon(&g.cpu[i])) { g.cpu[i].invincible = 0; } if (g.cpu[i].state == FLIER_FALLING) { g.cpu[i].state = FLIER_ALIVE; g.cpu[i].vy = 0; } }
        if (f % 1500u == 0u) for (i = 0; i < g.cpu_count; i++) g.cpu[i].state = FLIER_GONE;
        game_step_arena(&g, in);
        mix(g.stomps); mix(g.score); mix(g.distance); mix(g.matches_won); mix(g.round_end); mix(g.round_timer); mix(g.round_start); mix(g.round_start_timer); mix(g.cpu_count); mix(g.cpu_alive);
        for (i = 0; i < g.cpu_count; i++) { mix((uint32_t)g.cpu[i].x); mix((uint32_t)g.cpu[i].y); mix(g.cpu[i].state); mix(g.cpu[i].balloons); mix(g.cpu[i].invincible); mix(g.ai[i].thinks); mix(g.ai[i].state); }
        mix((uint32_t)g.flier.x); mix(g.flier.balloons); mix(g.flier.invincible); mix((uint32_t)flier_view_visible(&g.flier, g.frame)); mix((uint32_t)game_camera_px(&g));
    }
}

/* Arcade part: a rank 2 stage with a flier left to fall, so the rank AI think period and the lives knob show; 600 frames per life.
 * A second pass on stage 4 (a platform overhead of the rivals) keeps AI_OVERHEAD_PX visible. */
static void arcade_pass(int stage)
{
    static Game g;
    uint32_t f;
    int i;
    game_reset(&g, 5150);
    game_set_mode(&g, GAME_MODE_ARCADE);
    g.arc.stage = stage;
    for (f = 1; f <= 3000u; f++) {
        game_step(&g, (f % 5u) < 2u ? IN_A : 0);
        mix(g.score); mix(g.lives.lives); mix(g.over); mix((uint32_t)g.flier.x); mix((uint32_t)g.flier.y);
        for (i = 0; i < g.cpu_count; i++) { mix((uint32_t)g.cpu[i].x); mix(g.ai[i].thinks); mix(g.pump[i].state); }
        if (g.over) { mix(f); game_reset(&g, 5150u + f); game_set_mode(&g, GAME_MODE_ARCADE); g.arc.stage = stage; }
    }
}

static void arcade_digest(void)
{
    arcade_pass(7);
    arcade_pass(4);
}

/* Spawn protection (FLIER_SPAWN_INVINCIBLE): the player idles for 700 frames after game_reset, then presses right, while the
 * computer fliers fly and pop. Balloons, spawn_inv and stomps follow the window length. */
static void spawn_digest(void)
{
    static Game g;
    uint32_t f;
    game_reset(&g, 777);
    for (f = 1; f <= 800u; f++) {
        g.over = 0;
        game_step_arena(&g, f > 700u ? IN_RIGHT : 0);
        mix(g.flier.balloons); mix(g.flier.spawn_inv); mix(g.stomps); mix(g.flier.state); mix((uint32_t)g.flier.y);
    }
}

/* Flier physics wave: a parachute drop, a no-gum fall, one-gum flaps and a walk with release and reversal, all in a long
 * open drop or on a flat floor, so the parachute cap, the no-gum cap, the one-gum impulse and the ground acceleration show. */
static void flier_physics_digest(void)
{
    Flier f;
    FlierInput in = {0, 0};
    int i;
    flier_init(&f, FL_PX(100), FL_PX(10), 1, 1);
    flier_lose_balloon(&f);
    for (i = 0; i < 120; i++) { flier_step(&f, &in, FLIER_NO_FLOOR); mix((uint32_t)f.y); mix((uint32_t)f.vy); }
    flier_init(&f, FL_PX(100), FL_PX(10), 0, 0);
    for (i = 0; i < 120; i++) { flier_step(&f, &in, FLIER_NO_FLOOR); mix((uint32_t)f.y); mix((uint32_t)f.vy); }
    flier_init(&f, FL_PX(100), FL_PX(10), 1, 0);
    for (i = 0; i < 90; i++) { in.flap = (uint8_t)(i % 11 == 0); in.dir = 1; flier_step(&f, &in, FLIER_NO_FLOOR); mix((uint32_t)f.y); mix((uint32_t)f.vy); mix((uint32_t)f.vx); }
    flier_init(&f, FL_PX(100), FL_PX(120) - FLIER_HALF_H16_BALLOON, 2, 0);
    for (i = 0; i < 140; i++) {
        in.flap = (uint8_t)(i == 70);
        in.dir = (int8_t)(i < 40 ? 1 : i < 80 ? 0 : i < 120 ? -1 : 0);
        flier_step(&f, &in, FL_PX(120));
        mix((uint32_t)f.x); mix((uint32_t)f.vx); mix((uint32_t)f.vy);
    }
}

/* Gum Trip island solids: a flier rises into the underside of a Gum Trip island from below and slides into its left side
 * (flier_collide_solids on trip_hit_solids), so TRIP_ISLAND_SOLID_H, the bounce restitution and the island box shape the digest. */
static void trip_island_digest(void)
{
    static TripGen tg;
    Trip t;
    Flier f;
    int y, side;
    for (side = 0; side < 2; side++)
        for (y = 96; y <= 140; y += 2) {
            int step;
            memset(&tg, 0, sizeof tg);
            tg.count = 1;
            tg.ring[0].win_top = 0; tg.ring[0].win_bottom = TRIP_GEN_WORLD_H;
            tg.ring[0].island.present = 1; tg.ring[0].island.x = 40; tg.ring[0].island.y = 100;
            tg.ring[0].island.w = 64; tg.ring[0].island.h = TRIP_ISLAND_H;
            trip_init(&t);
            if (side == 0) { flier_init(&f, FL_PX(72), FL_PX(y), 2, 0); f.vy = -FL_PX(3); }
            else { flier_init(&f, FL_PX(20), FL_PX(98 + (y - 96) / 4), 2, 0); f.vx = FL_PX(3); }
            f.no_wrap = 1;
            for (step = 0; step < 12; step++) {
                int32_t px = f.x, py = f.y;
                FlierInput in = {0, 0};
                FlierSolid so[TRIP_SOLIDS_MAX];
                flier_step(&f, &in, trip_hit_floor_y(&t, &tg, &f));
                mix((uint32_t)flier_collide_solids(&f, px, py, so, trip_hit_solids(&t, &tg, &f, so, TRIP_SOLIDS_MAX)));
                mix((uint32_t)f.x); mix((uint32_t)f.y); mix((uint32_t)f.vx); mix((uint32_t)f.vy);
            }
        }
}

/* Gum Trip part: a long scripted trip through game_step (TRIP mode), with gum pickups and hits at fixed intervals so the
 * gum, streak, score and speed ramp knobs all show; the pure curves (speed and density by distance) are sampled too. */
static void trip_digest(void)
{
    static Game g;
    uint32_t f, k;
    static const uint32_t probes[] = { 100u, 1000u, 3000u, 7000u, 9500u, 18000u };
    game_reset(&g, 99);
    game_set_mode(&g, GAME_MODE_TRIP);
    for (f = 1; f <= 60000u; f++) {
        /* a steered pilot (trip_steer.h) reading the live course: collects pickups, lands, flies into hazards in turn */
        uint8_t in = trip_steer(&g, (f % 4000u) < 2400u ? STEER_AVOID : (f % 4000u) < 3200u ? STEER_LAND : STEER_HIT);
        if (f % 90u == 0u) trip_pickup(&g.trip, &g.flier);
        if (f % 611u == 0u) trip_hit(&g.trip, &g.flier);
        game_step(&g, in);
        mix(g.trip.px); mix(g.trip.speed); mix(g.trip.gum); mix(g.trip.streak); mix(g.score); mix(g.over);
        mix((uint32_t)g.flier.x); mix(g.flier.balloons); mix((uint32_t)g.flier.y); mix(g.flier.invincible); mix((uint32_t)flier_view_visible(&g.flier, g.frame));
        mix(g.trip_rival_events); mix(g.trip_rivals.spawned); mix(g.trip_rivals.popped); mix(g.trip_rivals.hits); mix(g.trip_rivals.retired);
        { int r; for (r = 0; r < TRIP_RIVAL_MAX; r++) if (g.trip_rivals.r[r].active) { mix((uint32_t)g.trip_rivals.r[r].f.x); mix((uint32_t)g.trip_rivals.r[r].f.y); mix(g.trip_rivals.r[r].variant); mix(g.trip_rivals.r[r].f.balloons); mix(g.trip_rivals.r[r].thinks); } }
        mix(g.trip_events); mix(g.trip.pickups); mix(g.trip.hits); mix(g.trip_gen.made); mix(g.trip_gen.drops);
        if ((f & 63u) == 0u) { /* the live course: first chunk held and what it holds */
            const TripChunk *c = tripgen_get(&g.trip_gen, g.trip_gen.ring[g.trip_gen.head].index);
            mix(c->index); mix((uint32_t)c->win_top); mix((uint32_t)c->win_bottom); mix(c->n_haz); mix(c->island.present);
            mix((uint32_t)c->island.x); mix((uint32_t)c->pickup.x); mix(c->pickup.present); mix(c->haz[0].amp); mix(c->haz[0].kind);
        }
        if (g.over) { mix(f); game_reset(&g, 99 + f); game_set_mode(&g, GAME_MODE_TRIP); }
    }
    for (k = 0; k < sizeof probes / sizeof probes[0]; k++) { mix(trip_speed_at(probes[k])); mix(trip_density_at(probes[k])); }
}

/* Rival spawn probe: px sweeps the whole density ramp. The first half runs with the scroll frozen (last_px follows px) so
 * rivals stay alive and chase a parked hero: shows the overlap cap (TRIP_RIVAL_MAX). A frozen pool stays full for good, so
 * no spawn is ever due again and the spacing knobs would never matter; the second half lets the scroll carry (last_px
 * lags, step = 10 px a frame), the rivals retire off the left edge and every spacing knob moves the next spawn. */
static void rival_probe(void)
{
    static TripGen tg; static Trip t; static TripRivals R; Flier hero;
    uint32_t px;
    tripgen_init(&tg, 5);
    trip_init(&t);
    flier_init(&hero, FL_PX(160), FL_PX(90), 2, 0);
    trip_rivals_init(&R, &t, 5);
    for (px = 0; px < 24000u; px += 10u) {
        int r;
        t.px = px; tripgen_advance(&tg, px);
        if (px < 12000u) { R.last_px = px; R.last_frac = t.frac; }
        mix(trip_rivals_advance(&R, &t, &tg, &hero));
        mix(R.spawned); mix(R.blocked); mix(R.retired);
        for (r = 0; r < TRIP_RIVAL_MAX; r++) if (R.r[r].active) { mix((uint32_t)R.r[r].f.x); mix((uint32_t)R.r[r].f.y); mix(R.r[r].variant); mix(R.r[r].thinks); }
    }
}

/* AI decision probe: a balloon-less rival at a sweep of distances from its target. With the 4-island stage no scripted run
 * leaves a balloon-less rival 5..25 px from its target any more, so the fill/flee distance would never show in the digest. */
static void ai_probe(void)
{
    Flier self, target;
    int d;
    flier_init(&target, FL_PX(100), FL_PX(100), 2, 0);
    for (d = 0; d <= 40; d++) {
        flier_init(&self, FL_PX(100 + d), FL_PX(100), 0, 0);
        mix((uint32_t)ai_decide(&self, &target));
    }
}

/* Flier view part: scripted runs of flier_anim_step for 2, 1 and 0 balloons. Standing, walking at two speeds (one between
 * the default and the overridden walk threshold), a landing, and in the air one flap press with rest frames around it, so
 * the walk, landing, breathing, walk threshold and flap hold knobs all change a frame number. */
static void flier_view_digest(void)
{
    static const uint8_t k_first[] = SOOTLING_TABLE_CLIP_FIRST;
    static const uint8_t k_count[] = SOOTLING_TABLE_CLIP_COUNT;
    static const uint8_t k_loop[] = SOOTLING_TABLE_CLIP_LOOP;
    static const uint8_t k_ticks[] = SOOTLING_TABLE_FRAME_TICKS;
    static const FlierClips clips = { k_first, k_count, k_loop, k_ticks,
        SOOTLING_CLIP_FLAP2, SOOTLING_CLIP_FLAP1, SOOTLING_CLIP_POP2, SOOTLING_CLIP_POP1,
        SOOTLING_CLIP_INFLATE, SOOTLING_CLIP_FALL, SOOTLING_CLIP_IDLE,
        { SOOTLING_CLIP_WALK0, SOOTLING_CLIP_WALK1, SOOTLING_CLIP_WALK2 },
        { SOOTLING_CLIP_LAND0, SOOTLING_CLIP_LAND1, SOOTLING_CLIP_LAND2 },
        { SOOTLING_CLIP_BREATHE0, SOOTLING_CLIP_BREATHE1, SOOTLING_CLIP_BREATHE2 } };
    static const int32_t speeds[3] = { 0, 40000, 91750 }; /* 0, 0.61 and 1.4 px per frame */
    int b, seg, i, flip;
    for (b = 2; b >= 0; b--) {
        Flier f;
        FlierAnim a;
        flier_init(&f, 0, 0, (uint8_t)b, 1);
        flier_anim_init(&a);
        f.on_ground = 1;
        for (i = 0; i < 100; i++) flier_anim_step(&a, &f, &clips, &flip); /* past inflate */
        for (seg = 0; seg < 3; seg++) {
            f.vx = speeds[seg];
            for (i = 0; i < (seg == 0 ? 200 : 100); i++) mix(flier_anim_step(&a, &f, &clips, &flip));
        }
        f.on_ground = 0; f.vx = 0;
        mix(flier_anim_step(&a, &f, &clips, &flip));
        f.on_ground = 1;
        for (i = 0; i < 60; i++) mix(flier_anim_step(&a, &f, &clips, &flip)); /* landing, then standing */
        if (b == 0) continue;
        f.on_ground = 0;
        for (i = 0; i < 60; i++) mix(flier_anim_step(&a, &f, &clips, &flip));
        f.flapped = 1;
        mix(flier_anim_step(&a, &f, &clips, &flip));
        f.flapped = 0;
        for (i = 0; i < 40; i++) mix(flier_anim_step(&a, &f, &clips, &flip));
    }
}

/* Gum bubble knobs: timing (GUM_WOBBLE_FRAMES, GUM_POP_FRAMES) as sheet frames over a stretch of game frames, placement (GUM_BIRD_*) as the offsets of every bird frame. */
static void gum_view_digest(void)
{
    uint32_t t;
    for (t = 0; t < 200; t++) { mix(gum_view_frame(GUM_STATE_WOBBLE, t)); mix(gum_view_frame(GUM_STATE_POP, t)); mix((uint32_t)gum_view_pop_done(t)); }
    for (t = 0; t < GUM_VIEW_BIRD_FRAMES; t++) { GumOffset o = gum_view_offset((uint8_t)t, 0), m = gum_view_offset((uint8_t)t, 1); mix((uint32_t)(o.dx + 128)); mix((uint32_t)(o.dy + 128)); mix((uint32_t)(m.dx + 128)); }
}

/* Splash knobs: sheet frame per game frame for both liquids, and when each one ends. */
static void splash_view_digest(void)
{
    uint8_t k;
    for (k = HZ_WATER; k <= HZ_LAVA; k++) {
        Splash s = {0};
        int t;
        splash_step(&s, 1, k, 100);
        for (t = 0; t < 80; t++) { mix(s.active); mix(splash_frame(&s)); splash_step(&s, 0, k, 0); }
    }
}

int main(void)
{
    trip_island_digest();
    flow_digest();
    trip_digest();
    rival_probe();
    ai_probe();
    arena_digest();
    arcade_digest();
    spawn_digest();
    flier_physics_digest();
    flier_view_digest();
    gum_view_digest();
    splash_view_digest();
    printf("%08x\n", (unsigned)h);
    return 0;
}
