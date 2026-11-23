#include "gg_flapdash.h"
#include "arena.h"
#include "game.h"

void gumdash_init(GgDash *d, Flier *hero)
{
    d->mash.count = 0;
    d->prev_in = 0; d->laps = 0; d->done = 0; d->two = 0; d->winner = 0; d->p2_is_cpu = 0; d->mash2.count = 0; d->prev_in2 = 0; d->laps2 = 0; d->lap_dist2 = 0; d->end_t = 0; d->frames = 0; d->lap_dist = 0;
    flier_init(hero, 0, GD_FLOOR_Y, 2, 0);
    hero->y = GD_FLOOR_Y - FL_PX(16);
}

/* One bird for one frame: forced +1 direction, mash flap, speed clamp. Returns the 16.16 px it advanced this lap. */
static int32_t lane_step(GgMash *m, uint8_t *prev, Flier *hero, uint8_t in)
{
    FlierInput fi;
    fi.dir = 1;                                   /* the thrust needs a direction held (tuning.h); the dash runs rightward only */
    fi.flap = (uint8_t)gg_mash_step(m, in, *prev);
    *prev = in;
    flier_step(hero, &fi, GD_FLOOR_Y);
    if (hero->vx > GD_MAX_VX) {                   /* undo the excess so x and vx agree on the clamped speed */
        hero->x = arena_wrap_x(hero->x - (hero->vx - GD_MAX_VX));
        hero->vx = GD_MAX_VX;
    }
    return hero->vx > 0 ? hero->vx : 0;
}

/* Adds one step of progress; returns 1 when a lap completes the course. */
static int lane_lap(int32_t *dist, uint8_t *laps, int32_t step)
{
    *dist += step;
    if (*dist >= ARENA_W16) {
        *dist -= ARENA_W16;
        if (++*laps >= GD_LAPS) return 1;
    }
    return 0;
}

int gumdash_step(GgDash *d, Flier *hero, uint8_t in)
{
    if (d->done) return 0;
    int32_t step = lane_step(&d->mash, &d->prev_in, hero, in);
    d->frames++;
    if (lane_lap(&d->lap_dist, &d->laps, step)) { d->done = 1; d->winner = 1; return 1; }
    return 0;
}

void gumdash_add_p2(GgDash *d, const Flier *hero, Flier *hero2)
{
    d->two = 1;
    flier_init(hero2, arena_wrap_x(hero->x - FL_PX(GD_P2_GAP)), GD_FLOOR_Y, 2, 0);
    hero2->y = GD_FLOOR_Y - FL_PX(16);
}

/* Wrapped signed distance a - b on the ring, 16.16 px. */
static int32_t ring_dx(int32_t a, int32_t b)
{
    return arena_wrap_x(a - b + ARENA_W16 / 2) - ARENA_W16 / 2;
}

int gumdash_step2(GgDash *d, Flier hero[2], uint8_t in, uint8_t in2)
{
    int32_t s1, s2, dx, dy;
    int f1, f2;
    if (!d->two) return gumdash_step(d, &hero[0], in);
    if (d->done) return 0;
    s1 = lane_step(&d->mash, &d->prev_in, &hero[0], in);
    s2 = lane_step(&d->mash2, &d->prev_in2, &hero[1], in2);
    d->frames++;
    f1 = lane_lap(&d->lap_dist, &d->laps, s1);
    f2 = lane_lap(&d->lap_dist2, &d->laps2, s2);
    dx = ring_dx(hero[0].x, hero[1].x); dy = hero[0].y - hero[1].y;
    if (dx < 0) dx = -dx;
    if (dy < 0) dy = -dy;
    if (dx < FL_PX(GD_BUMP_DX) && dy < FL_PX(GD_BUMP_DY)) {   /* contact: both lose a little speed, nobody is pushed */
        if (hero[0].vx > 0) hero[0].vx -= hero[0].vx >> GD_BUMP_SHIFT;
        if (hero[1].vx > 0) hero[1].vx -= hero[1].vx >> GD_BUMP_SHIFT;
    }
    if (f1 || f2) {   /* the same frame: the bird further into the finishing lap wins, a dead heat goes to P1 */
        d->done = 1;
        d->winner = (f1 && (!f2 || d->lap_dist >= d->lap_dist2)) ? 1 : 2;
        return 1;
    }
    return 0;
}

uint32_t gumdash_mark(uint32_t loop)
{
    uint32_t m = GD_MARK_FRAMES;
    while (loop-- && m > GD_MARK_MIN) m = (m * 243u) >> 8;
    return m > GD_MARK_MIN ? m : GD_MARK_MIN;
}
