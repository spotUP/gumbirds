#include "trip.h"

/* 32-bit maths only (no libgcc 64-bit divide on the 68000): px < TRIP_RAMP_PX and px - START < FULL - START keep the products under 2^32
 * for the default knobs; the knob overrides in tests/host/knobs.txt stay under it too. */
/* Compile-time check (C99): the ramp accumulator needs MAX >= START. */
typedef char trip_ramp_needs_max_ge_start[(TRIP_SCROLL_MAX >= TRIP_SCROLL_START) ? 1 : -1];

#define GUM_HALF (GUM_MAX / 2)

void trip_init(Trip *t) {
    t->px = 0;
    t->frac = 0;
    t->speed = TRIP_SCROLL_START;
    t->ramp_acc = 0;
    t->gum = GUM_START;
    t->decay_tick = 0;
    t->streak = 0;
    t->bonus = 0;
    t->pickups = 0;
    t->hits = 0;
    t->steps = 0;
}

uint8_t trip_gum_balloons(uint16_t gum) {
    if (gum >= GUM_HALF) return 2;
    return gum > 0 ? 1 : 0;
}

uint32_t trip_speed_at(uint32_t px) {
    if (px >= TRIP_RAMP_PX) return TRIP_SCROLL_MAX;
    return TRIP_SCROLL_START + ((px * (TRIP_SCROLL_MAX - TRIP_SCROLL_START)) / TRIP_RAMP_PX);
}

uint32_t trip_density_at(uint32_t px) {
    if (px <= TRIP_DENSITY_START_PX) return 0;
    if (px >= TRIP_DENSITY_FULL_PX) return (uint32_t)TRIP_DENSITY_MAX * 256u;
    return ((px - TRIP_DENSITY_START_PX) * TRIP_DENSITY_MAX * 256u) /
           (TRIP_DENSITY_FULL_PX - TRIP_DENSITY_START_PX);
}

/* Advance the scroll one frame and the speed ramp by the whole pixels crossed (an accumulator, not a division). */
static void scroll(Trip *t) {
    uint32_t before = t->px;
    t->frac += t->speed;
    t->px += t->frac >> 16;
    t->frac &= 0xFFFF;
    if (t->px < TRIP_RAMP_PX) {
        t->ramp_acc += (t->px - before) * (uint32_t)(TRIP_SCROLL_MAX - TRIP_SCROLL_START);
        while (t->ramp_acc >= TRIP_RAMP_PX) {
            t->ramp_acc -= TRIP_RAMP_PX;
            t->speed++;
        }
    } else {
        t->speed = TRIP_SCROLL_MAX;
    }
}

/* Gum is the level, balloons are derived (plan spine 4). At 0 the last pod pops and the fall starts. */
static void sync_flier(const Trip *t, Flier *f) {
    uint8_t want;
    if (f->state != FLIER_ALIVE) return;
    want = trip_gum_balloons(t->gum);
    if (want > 0) {
        f->balloons = want;
    } else if (f->balloons > 0) {
        f->invincible = 0; /* flier_lose_balloon refuses while invincible or spawn protected; running out of gum always drops */
        f->spawn_inv = 0;
        f->balloons = 1;
        flier_lose_balloon(f);
    }
}

/* The world moves under the flier: carry it left by the scroll step, hold it inside 0..319 with no wrap. */
static void carry(Flier *f, uint32_t step) {
    if (f->state != FLIER_ALIVE && f->state != FLIER_PARACHUTE) return;
    f->x -= (int32_t)step;
    if (f->x < 0) {
        f->x = 0;
        if (f->vx < 0) f->vx = 0;
    }
    if (f->x > FL_PX(319)) {
        f->x = FL_PX(319);
        if (f->vx > 0) f->vx = 0;
    }
}

void trip_step(Trip *t, Flier *f) {
    uint32_t step = t->speed; /* the step this frame uses; scroll() may raise the speed after */
    t->steps++;
    scroll(t);
    carry(f, step);
    if (f->state == FLIER_ALIVE && t->gum > 0) {
        if (++t->decay_tick >= GUM_DECAY_FRAMES) {
            t->decay_tick = 0;
            t->gum--;
        }
    }
    sync_flier(t, f);
}

int trip_pickup(Trip *t, Flier *f) {
    uint32_t add;
    if (f->state != FLIER_ALIVE) return 0;
    t->pickups++;
    t->gum = (uint16_t)(t->gum + GUM_PICKUP > GUM_MAX ? GUM_MAX : t->gum + GUM_PICKUP);
    if (t->streak < 0xFFFFFFFFu) t->streak++;
    /* streak x points without overflow: anything past the cap saturates */
    if (t->streak > TRIP_SCORE_CAP / TRIP_PICKUP_POINTS) add = TRIP_SCORE_CAP;
    else add = t->streak * TRIP_PICKUP_POINTS;
    t->bonus = (t->bonus + add > TRIP_SCORE_CAP) ? TRIP_SCORE_CAP : t->bonus + add;
    sync_flier(t, f);
    return 1;
}

int trip_hit(Trip *t, Flier *f) {
    if (f->state != FLIER_ALIVE || f->invincible || f->spawn_inv) return 0;
    t->hits++;
    t->gum = t->gum > GUM_HIT_CHUNK ? (uint16_t)(t->gum - GUM_HIT_CHUNK) : 0;
    t->streak = 0;
    f->invincible = FLIER_INVINCIBLE_POP;
    sync_flier(t, f);
    return 1;
}

int trip_wall_kill(Trip *t, Flier *f) {
    if (f->state != FLIER_ALIVE) return 0;
    t->hits++;
    t->gum = 0;
    t->streak = 0;
    sync_flier(t, f);   /* gum 0: clears the protection and starts the fall through flier_lose_balloon */
    return 1;
}

int trip_over(const Flier *f) {
    return f->state == FLIER_GONE; /* the dead body has left the screen */
}

uint32_t trip_score(const Trip *t) {
    uint32_t s = (t->px >> TRIP_SCORE_PX_SHIFT) + t->bonus; /* both <= 2^29 + 999999: no u32 wrap */
    return s > TRIP_SCORE_CAP ? TRIP_SCORE_CAP : s;
}
