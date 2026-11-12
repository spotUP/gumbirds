#include "trip_rival.h"
#include "tuning.h"
#include "trip_hit.h"

#define RIVAL_HALF 12   /* half of the 24 px art: clearance used for the spawn y */

static const uint8_t k_think[TRIP_RIVAL_VARIANTS] = { TRIP_RIVAL_THINK_HORNET, TRIP_RIVAL_THINK_BONE, TRIP_RIVAL_THINK_BRUISER };
static const uint8_t k_balloons[TRIP_RIVAL_VARIANTS] = { 1, 1, 2 };

/* int16 x int16 -> int32 as one muls.w (see flier.c). */
__attribute__((noinline)) static int32_t m16(int16_t a, int16_t b) { return (int32_t)a * (int32_t)b; }

void trip_rivals_init(TripRivals *R, const Trip *t, uint32_t seed) {
    TripRivals z = {0};
    *R = z;
    rng_seed(&R->rng, seed);
    R->next_px = TRIP_RIVAL_FIRST_PX;
    R->last_px = t->px;
    R->last_frac = t->frac;
}

int trip_rivals_alive(const TripRivals *R) {
    int i, n = 0;
    for (i = 0; i < TRIP_RIVAL_MAX; i++) n += R->r[i].active;
    return n;
}

static void arm(TripRival *v, Rng *rng) {
    v->timer = (uint8_t)(k_think[v->variant] + ((rng_next(rng) >> 16) & 7u));
}

/* The chunk holding world x wx, scanned in ring order (no division). */
static const TripChunk *chunk_at(const TripGen *g, uint32_t wx) {
    int s = g->head, i;
    for (i = 0; i < g->count; i++) {
        const TripChunk *c = &g->ring[s];
        if (wx >= c->wx && wx - c->wx < TRIP_CHUNK_PX) return c;
        s = (s + 1 == TRIP_GEN_RING) ? 0 : s + 1;
    }
    return 0;
}

static unsigned try_spawn(TripRivals *R, const Trip *t, const TripGen *g) {
    int i, slot = -1;
    const TripChunk *c;
    TripRival *v;
    int lo, hi, y;
    uint32_t spacing, red;
    for (i = 0; i < TRIP_RIVAL_MAX; i++) if (!R->r[i].active) { slot = i; break; }
    c = chunk_at(g, t->px + (uint32_t)TRIP_RIVAL_SPAWN_X);
    if (slot < 0 || !c) { R->blocked++; return 0; }
    v = &R->r[slot];
    lo = c->band_top + RIVAL_HALF; hi = c->band_bottom - RIVAL_HALF;
    if (hi < lo) lo = hi = (c->band_top + c->band_bottom) >> 1;
    y = lo + (int)(m16((int16_t)((rng_next(&R->rng) >> 16) & 0xFFu), (int16_t)(hi - lo)) >> 8);
    {
        TripRival z = {0};
        *v = z;
    }
    /* variant by distance band (user 2026-11-11): Hornet below BONE_PX, Bone below BRUISER_PX, Bruiser from there */
    v->variant = (uint8_t)(t->px < (uint32_t)TRIP_RIVAL_BAND_BONE_PX ? TRIP_RIVAL_HORNET
                           : t->px < (uint32_t)TRIP_RIVAL_BAND_BRUISER_PX ? TRIP_RIVAL_BONE : TRIP_RIVAL_BRUISER);
    flier_init(&v->f, FL_PX(TRIP_RIVAL_SPAWN_X), FL_PX(y), k_balloons[v->variant], 0);
    v->f.no_wrap = 1;
    v->f.rival = 1;
    v->f.flap_cd = FLIER_FLAP_COOLDOWN;     /* a new rival settles for one cooldown before its first flap: it stays inside the band it spawned in */
    v->f.facing = 0;
    v->hold_y = (int16_t)y;
    v->active = 1;
    arm(v, &R->rng);
    R->spawned++;
    /* next spawn: the base spacing shortened by the density ramp (one division per spawn, in trip_density_at) */
    red = (uint32_t)(m16((int16_t)(trip_density_at(t->px) >> 2), (int16_t)TRIP_RIVAL_DENSITY_K) >> 6);
    spacing = red + TRIP_RIVAL_EVERY_MIN_PX > TRIP_RIVAL_EVERY_PX ? TRIP_RIVAL_EVERY_MIN_PX : TRIP_RIVAL_EVERY_PX - red;
    R->next_px = t->px + spacing;
    return TRIP_RIV_EV_SPAWN;
}

static void think(TripRival *v, TripRivals *R, const Flier *hero, int16_t hold_y, FlierInput *in) {
    in->flap = 0;
    if (v->timer > 0) v->timer--;
    if (v->timer == 0) {
        arm(v, &R->rng);
        v->thinks++;
        v->dir = 0;
        if (v->variant == TRIP_RIVAL_BONE) {
            /* patrol: ignores the hero; altitude is held below, every frame */
        } else if (hero->state == FLIER_ALIVE) {
            /* chase only (ai_step would flee when close; the plan wants contact): same angle maths and thresholds */
            uint8_t ang = flier_angle((hero->x - v->f.x) >> 16, (hero->y - v->f.y) >> 16);
            int16_t cx = flier_cos(ang);
            if (cx > AI_STEER_MIN) v->dir = 1;
            else if (cx < -AI_STEER_MIN) v->dir = -1;
        }
    }
    in->dir = v->dir;
    /* The flap decision runs every frame, gated by the flap cooldown and a released button (additive flight model).
     * Chasers press while the hero is above (same angle maths and threshold as the steering); Bone while below hold_y. */
    if (v->f.flap_cd == 0 && !v->f.flap_prev) {
        if (v->variant == TRIP_RIVAL_BONE) {
            if ((int16_t)(v->f.y >> 16) > hold_y) in->flap = 1;
        } else if (hero->state == FLIER_ALIVE) {
            uint8_t ang = flier_angle((hero->x - v->f.x) >> 16, (hero->y - v->f.y) >> 16);
            if (flier_sin(ang) < AI_FLAP_MAX) in->flap = 1;
        }
    }
}

unsigned trip_rivals_advance(TripRivals *R, const Trip *t, const TripGen *g, const Flier *hero) {
    unsigned ev = 0;
    int i;
    int32_t step = (int32_t)(((t->px - R->last_px) << 16) + t->frac - R->last_frac);
    R->last_px = t->px; R->last_frac = t->frac;
    R->steps++;
    if (t->px >= R->next_px) ev |= try_spawn(R, t, g);
    for (i = 0; i < TRIP_RIVAL_MAX; i++) {
        TripRival *v = &R->r[i];
        FlierInput in;
        if (!v->active) continue;
        /* Shift into this frame's scroll first: v->f.x and t->px are then in the same frame for the floor, the solids and
         * the window clamp (trip_step has already advanced px). */
        v->f.x -= step;
        {
            /* Bone holds hold_y, fixed at spawn inside its chunk's band; a later window can move off it. The target is
             * clamped into the window under the rival (hold_y itself stays, it recovers when the window moves back). */
            int16_t tgt = v->hold_y;
            int32_t lo, hi;
            if (v->variant == TRIP_RIVAL_BONE && trip_hit_window(t, g, &v->f, &lo, &hi)) {
                if (tgt < (int16_t)(lo >> 16)) tgt = (int16_t)(lo >> 16);
                if (tgt > (int16_t)(hi >> 16)) tgt = (int16_t)(hi >> 16);
            }
            think(v, R, hero, tgt, &in);
        }
        {
            int32_t px = v->f.x, py = v->f.y;
            FlierSolid so[TRIP_SOLIDS_MAX];
            flier_step(&v->f, &in, trip_hit_floor_y(t, g, &v->f));
            flier_collide_solids(&v->f, px, py, so, trip_hit_solids(t, g, &v->f, so, TRIP_SOLIDS_MAX));
            trip_hit_clamp_window_from(t, g, &v->f, py);
        }
        if (v->f.state == FLIER_GONE || v->f.x < FL_PX(TRIP_RIVAL_RETIRE_X)) {
            v->active = 0;
            R->retired++;
            ev |= TRIP_RIV_EV_RETIRE;
        }
    }
    return ev;
}

unsigned trip_rivals_resolve(TripRivals *R, Trip *t, const TripGen *g, Flier *hero) {
    unsigned ev = 0;
    int i;
    if (hero->state != FLIER_ALIVE) return 0;
    for (i = 0; i < TRIP_RIVAL_MAX; i++) {
        TripRival *v = &R->r[i];
        FlierPairAct act;
        if (!v->active || v->f.state != FLIER_ALIVE) continue;
        act = flier_pair(hero, &v->f);
        if (act != FLP_NONE) {
            /* A solid island between the two blocks the contact. Solids are listed around the pair midpoint (a gum-to-gum
               contact reaches 18 px, more than the broad phase around the hero alone covers). Rivals never meet each other,
               so the computer-never-pops rule of the arena has nothing to act on here. */
            FlierSolid so[TRIP_SOLIDS_MAX];
            Flier m = *hero;
            m.x = hero->x + ((v->f.x - hero->x) >> 1);
            if (flier_pair_blocked(hero, &v->f, so, trip_hit_solids(t, g, &m, so, TRIP_SOLIDS_MAX), 0)) continue;
        }
        if (act == FLP_POP_B) {
            /* a last balloon on the ground would leave a standing balloon-less rival: lift it so it falls */
            if (v->f.balloons == 1) v->f.on_ground = 0;
            if (flier_pair_apply(hero, &v->f, act)) {
                R->popped++;
                t->bonus = (t->bonus + TRIP_RIVAL_POP_POINTS > TRIP_SCORE_CAP) ? TRIP_SCORE_CAP : t->bonus + TRIP_RIVAL_POP_POINTS;
                ev |= TRIP_RIV_EV_POP;
            }
        } else if (act == FLP_POP_A) {
            /* The rival is higher: it pops the hero's gum (a gum chunk), and both bounce apart. */
            if (trip_hit(t, hero)) { R->hits++; ev |= TRIP_RIV_EV_HIT; }
            flier_pair_apply(hero, &v->f, FLP_BOUNCE);
        } else if (act == FLP_BOUNCE) {
            flier_pair_apply(hero, &v->f, act);
        }
    }
    return ev;
}

unsigned trip_rivals_step(TripRivals *R, Trip *t, const TripGen *g, Flier *hero) {
    unsigned ev = trip_rivals_advance(R, t, g, hero);
    return ev | trip_rivals_resolve(R, t, g, hero);
}
